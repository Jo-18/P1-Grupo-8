"""Auditoria PM.ADIC — Edificio I (aplicado en checkpoint) y Edificio II (catalogo).

Solo lectura de fuentes; salidas bajo modelo_fiel/PM_ADIC_auditoria_EI_EII.*

Edificio I (PM.ADIC APLICADA = 10.244,15 kN, dentro del G del checkpoint):
  * fuente: `datos/casos_analisis/correlacion_cargas_validada_5niveles.json`
    (sombreas correlacionadas de la pagina 11 por nivel; categorias "260/300" etc.
    en kgf/m2 -> pm_avg -> pm_kn_m2 = pm_kgf_m2 * 0.00980665).
  * aplicacion: `tributaria.calcular_cargas_nodales` -> pm_kn_m2 * area_neta
    (componente PM_ADIC), repartida por la misma malla tributaria que el PP de
    losa pero como componente SEPARADO (por_comp_kN.pp vs por_comp_kN.pm_adic) =>
    sin doble conteo oculto.
  * GTG = PP_losas + PM_ADIC = 25.227,73 kN (checkpoint G). No hay lineales:
    el PM.ADIC del EI es SUPERFICIAL (kgf/m2), no kg/m.

Edificio II (PM.ADIC PENDIENTE = catalogo completo):
  * fuente: `eii_viewer.json cargas.caso_G.PM_ADIC_lineal_kg_m` + bloques
    CARGAS DE DISEÑO del plano `2024_22-700.dxf` (inventario ezdxf) y
    `results/peso_propio_teorico_EDIFICIO_II_v1.json`.
  * son cargas LINEALES (Kg/m) de vigas/escaleras; la leyenda no fija
    correspondencia familia -> viga/eje -> sin longitud confirmada -> todo
    `PM_ADIC_PENDIENTE`. Unidades: el plano expresa "Kg/m"; se documenta la
    conversion masa lineal -> kN/m con g = 9.80665 m/s^2 (mismo valor numerico
    si se leyera kgf/m, pues 1 kgf = 9.80665 N).

Uso:
  python -X utf8 -m src.modelo_fiel.auditoria_PM_ADIC
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
RES = E3 / "results"
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"
EII_VIEWER = REPO / "entrega_03_cargas_sismo_capacidad" / "data" / "externas" / "eii_viewer.json"
EII_PP = RES / "peso_propio_teorico_EDIFICIO_II_v1.json"

sys.path.insert(0, str(EI_SRC))

from analisis.fe import cargas_correlacionadas as CC   # noqa: E402
from analisis.fe import geometria_fe as GF             # noqa: E402
from analisis.fe import tributaria as TB               # noqa: E402
from analisis.fe.hipotesis import niveles_ordenados    # noqa: E402
from analisis.fe.marco import Marco                    # noqa: E402

GRAV = 0.00980665
TOL_REF = 0.1  # kN contra el valor publicado por nivel


def conocer_correlacion(marco) -> tuple:
    """por_nivel y por_losa desde lo APLICADO por tributaria (area geometrica FE).

    `pm_kn_m2` se aplica sobre el area NETA GEOMETRICA del FE (igual que TB en el
    checkpoint); la correlacion publica su propio `neta_m2` (correlacionado), que
    difiere para alcune lasas -> aqui se usa el area FE y se guarda la CC como
    documentacion. Componentes separados por_losa: pm_adic y pp (e*rho*area).
    """
    por_nivel = CC.cargas_por_losa_por_nivel()
    info_nivel = {}
    filas = []
    for cod in niveles_ordenados():
        nivelFE = marco.niveles[cod]
        cargas_por_losa = {
            lo["id"]: (por_nivel.get(cod, {}).get(lo["id"], {}).get("pm_kn_m2", 0.0),
                       por_nivel.get(cod, {}).get(lo["id"], {}).get("sc_kn_m2", 0.0))
            for lo in nivelFE.losas}
        _cn, rp = TB.calcular_cargas_nodales(nivelFE, marco.receptor_nodos,
                                             cargas_por_losa, marco.key_of_tag,
                                             incluir_sc=False)
        for lo in nivelFE.losas:
            por = rp["por_losa"][lo["id"]]["por_comp_kN"]
            inf = por_nivel.get(cod, {}).get(lo["id"], {})
            neta_fe = rp["por_losa"][lo["id"]]["area_neta_geometrica_m2"]
            neta_cc = inf.get("neta_m2", 0.0)
            filas.append({
                "nivel": cod, "losa_id": lo["id"],
                "area_neta_fe_m2": neta_fe, "area_neta_correlacion_m2": round(neta_cc, 4),
                "pm_kgf_m2": round(inf.get("pm_kgf_m2", 0.0), 6),
                "pm_kn_m2": round(inf.get("pm_kn_m2", 0.0), 6),
                "pm_adic_kn": round(por["pm_adic"], 6),
                "pp_losa_kn": round(por["pp"], 6),
                "espesor_m": lo.get("espesor", 0.0),
            })
            acc = info_nivel.setdefault(cod, {"pm_adic_kn": 0.0, "pp_losa_kn": 0.0,
                                              "n_losas": 0, "area_fe_m2": 0.0,
                                              "pm_kgf_m2_pond": 0.0})
            acc["pm_adic_kn"] += por["pm_adic"]
            acc["pp_losa_kn"] += por["pp"]
            acc["n_losas"] += 1
            acc["area_fe_m2"] += neta_fe
            acc["pm_kgf_m2_pond"] += inf.get("pm_kgf_m2", 0.0) * neta_fe
    for acc in info_nivel.values():
        acc["pm_kgf_m2_pond"] = (acc["pm_kgf_m2_pond"] / acc["area_fe_m2"]
                                 if acc["area_fe_m2"] else 0.0)
    return info_nivel, filas


def verificar_contra_checkpoint(info_nivel) -> dict:
    """Referencias de AUDITORIA_INICIAL.md (per nivel) y totals."""
    ref_por_nivel = {"CP1S": 1073.85, "P1": 2814.78, "P2": 2143.66,
                     "P3": 2344.61, "P4": 1867.23}
    ref_total = 10244.15
    checks = []
    tots = []
    for cod, ref in ref_por_nivel.items():
        v = info_nivel.get(cod, {}).get("pm_adic_kn", 0.0)
        tots.append(v)
        checks.append({"nivel": cod, "pm_adic_calculada_kn": round(v, 4),
                       "pm_adic_referencia_kn": ref,
                       "delta_kN": round(v - ref, 4),
                       "ok": abs(v - ref) <= TOL_REF})
    total = sum(tots)
    checks.append({"nivel": "TOTAL", "pm_adic_calculada_kn": round(total, 4),
                   "pm_adic_referencia_kn": ref_total,
                   "delta_kN": round(total - ref_total, 4),
                   "ok": abs(total - ref_total) <= 0.1})
    return {"referencia_fuente": "docs/AUDITORIA_INICIAL.md (tabla 2.1)",
            "checks": checks,
            "total_calculado_kn": round(total, 4),
            "total_referencia_kn": ref_total}


def catalogar_EII() -> list:
    viewer = json.loads(EII_VIEWER.read_text(encoding="utf-8"))
    pm = viewer["cargas"]["caso_G"]["PM_ADIC_lineal_kg_m"]
    sc = viewer["cargas"]["caso_G"]["SC_lineal_kg_m"]
    pp_ii = json.loads(EII_PP.read_text(encoding="utf-8"))
    bloques_plan = {
        "A": {"bloque": "A (x≈1140, y≈2399/2546)", "SC": 500, "PM_ADIC": 260},
        "B": {"bloque": "B (x≈2251, y≈2399)", "SC": 300, "PM_ADIC": 260},
        "C": {"bloque": "C (x≈6083, y≈2399/2546)", "SC": 200, "PM_ADIC": 200},
        "D": {"bloque": "D (x≈7193, y≈2399/2546, CARGA LINEAL)", "SC": 100, "PM_ADIC": 1500},
        "E": {"bloque": "E (x≈1141, y≈1702/1849)", "SC": 200, "PM_ADIC": 260},
        "F": {"bloque": "F (x≈2251, y≈1702/1849)", "SC": 500, "PM_ADIC": 260},
    }
    filas = []
    for fam in sorted(pm):
        q_kn_m = pm[fam] * GRAV
        filas.append({
            "familia": fam,
            "intensidad_original_kg_m": pm[fam],
            "unidad_original": "Kg/m (lineal)",
            "naturaleza": "lineal (vigas/escaleras/elementos lineales)",
            "SC_lineal_kg_m": sc.get(fam),
            "conversion_a_kn_m": q_kn_m,
            "conversion_nota": ("masa lineal * g (9.80665 m/s2); el mismo valor "
                                "numerico si la unidad se leyera kgf/m (1 kgf = "
                                "9.80665 N). No se asume kN/m automaticamente."),
            "longitud_confirmada_m": None,
            "viga_receptor": None,
            "carga_total_kn": None,
            "fuente": ("eii_viewer cargas.caso_G.PM_ADIC_lineal_kg_m; plano "
                       "2024_22-700.dxf bloque %s" % bloques_plan[fam]["bloque"]),
            "nivel_aplicabilidad": "CP1S..CP3 (leyenda PLANTA DE CARGAS 'CIELO "
                                   "1ºSUBTERRANEO a CIELO PISO 3º'); CP4 sin "
                                   "cubrir por la leyenda",
            "estado": "PM_ADIC_PENDIENTE",
            "motivo": ("sin correspondencia familia->viga/eje disponible en los "
                       "datos recibidos: la leyenda del plano no fija sobre que "
                       "elemento lineal actua cada bloque y el DXF 2024_22-700 no "
                       "esta incluido en la copia (solo se leyeron los bloques de "
                       "leyenda). Longitud y receptor sin confirmar -> no se "
                       "aplica."),
        })
    total_ref = sum(f["conversion_a_kn_m"] for f in filas)
    return filas, round(total_ref, 6)


def _md(ei_dir, ei_rows, ei_nivel, eii_filas, total_ref_kn_m) -> str:
    l = []
    l.append("# Auditoria PM.ADIC — EI (aplicada) y EII (catalogo pendiente)")
    l.append("")
    l.append("## Edificio I — PM.ADIC aplicada en el checkpoint G")
    l.append("")
    l.append("Fuente: `%s`" % CC.ruta() if hasattr(CC, "ruta") else
             "`datos/casos_analisis/correlacion_cargas_validada_5niveles.json`")
    l.append("")
    l.append("Tipo: **superficial** (kgf/m2 correlacionadas, pm_avg -> kN/m2 con "
             "g=0.00980665). No hay cargas lineales en el EI.")
    l.append("")
    l.append("| nivel | n losas | area neta (m2) | PM.ADIC (kN) | PP losa (kN) |")
    l.append("|---|---|---|---|---|")
    for cod in sorted(ei_nivel):
        v = ei_nivel[cod]
        l.append("| %s | %d | %.2f | %.4f | %.4f |" % (
            cod, v["n_losas"], v["area_fe_m2"], v["pm_adic_kn"], v["pp_losa_kn"]))
    l.append("")
    for c in ei_dir["checks"]:
        l.append("- %s: calculada %.4f vs referencia %.2f -> %s"
                 % (c["nivel"], c["pm_adic_calculada_kn"], c["pm_adic_referencia_kn"],
                    "OK" if c["ok"] else "ERROR"))
    l.append("")
    l.append("PP losas total: %.2f kN; PM.ADIC total: %.4f kN; "
             "GTG (PP losas + PM.ADIC): %.2f kN." % (
                 sum(v["pp_losa_kn"] for v in ei_nivel.values()),
                 ei_dir["total_calculado_kn"],
                 sum(v["pp_losa_kn"] for v in ei_nivel.values())
                 + ei_dir["total_calculado_kn"]))
    l.append("")
    l.append("No doble conteo: `tributaria.calcular_cargas_nodales` mantiene "
             "`por_comp_kN.pp` (e*rho*area) y `por_comp_kN.pm_adic` (pm_kn_m2*"
             "area) como componentes separados; ambos se reparten por la misma "
             "malla pero nunca se suman dentro de un componente.")
    l.append("")
    l.append("## Edificio II — PM.ADIC lineal catalogada (pendiente de mapeo)")
    l.append("")
    l.append("| familia | PM.ADIC orig (Kg/m) | SC (Kg/m) | conv (kN/m) | estado | motivo |")
    l.append("|---|---|---|---|---|---|")
    for f in eii_filas:
        l.append("| %s | %s | %s | %.6f | %s | %s |" % (
            f["familia"], f["intensidad_original_kg_m"], f["SC_lineal_kg_m"],
            f["conversion_a_kn_m"], f["estado"], f["motivo"][:80]))
    l.append("")
    l.append("Checks EII:")
    l.append("- sum(PM_ADIC_aplicada) = 0.0000 kN (ninguna carga correlacionable "
             "con recepto confirmado).")
    l.append("- sum(q_lineal x longitud_confirmada) = 0.0000 kN (0 longitudes "
             "confirmadas).")
    l.append("- equilibrio de reacciones: N/A (carga aplicada nula).")
    l.append("- intensidad unitaria total del catalogo: %.6f kN/m (referencia; "
             "NO se multiplica por longitudes no confirmadas)." % total_ref_kn_m)
    return "\n".join(l) + "\n"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    marco = Marco(GF.cargar_todos(), rigidez_mult=1.0e3)
    marco.subdivision_vigas = 1
    marco.construir()
    info_nivel, filas_ei = conocer_correlacion(marco)
    dir_ck = verificar_contra_checkpoint(info_nivel)
    eii_filas, total_ref_kn_m = catalogar_EII()

    pp_losas_total = round(sum(v["pp_losa_kn"] for v in info_nivel.values()), 4)
    checks = []
    checks.append({"check": "pm_adic_ei_total", "ok": dir_ck["checks"][-1]["ok"],
                   "detalle": dir_ck["checks"][-1]})
    checks.append({"check": "pm_adic_ei_por_nivel",
                   "ok": all(c["ok"] for c in dir_ck["checks"][:-1]),
                   "detalle": dir_ck["checks"][:-1]})
    checks.append({"check": "pp_losas_ei", "ok": abs(pp_losas_total - 14983.58) < 0.2,
                   "detalle": "pp losas %.4f vs referencia 14983.58"
                   % pp_losas_total})
    checks.append({"check": "eii_pm_adic_aplicada_cero",
                   "ok": all(f["carga_total_kn"] is None for f in eii_filas),
                   "detalle": "ninguna longitud/receptor confirmado"})
    checks.append({"check": "eii_unidades_lineales_documentadas",
                   "ok": all(f["unidad_original"] == "Kg/m (lineal)"
                             and f["estado"] == "PM_ADIC_PENDIENTE" for f in eii_filas),
                   "detalle": "6 familias A-F catalogadas, todas PENDIENTE"})

    payload = {
        "caso": "auditoria_PM_ADIC", "iteracion": "MODELO_FIEL_2",
        "gravedad_m_s2_documentada": {"masa_lineal_a_carga": "x 0.00980665 (kN/m)",
                                      "gf_a_kN": "x 0.00980665"},
        "EDIFICIO_I": {
            "tipo": "superficial (kgf/m2 correlacionadas)",
            "fuente": str(CC._corr_path()) if hasattr(CC, "_corr_path") else
                      "datos/casos_analisis/correlacion_cargas_validada_5niveles.json",
            "por_nivel": {k: {kk: (round(v, 4) if isinstance(v, float) else v)
                              for kk, v in vv.items()}
                          for k, vv in info_nivel.items()},
            "por_losa": filas_ei,
            "total_pm_adic_kn": dir_ck["total_calculado_kn"],
            "total_pp_losas_kn": pp_losas_total,
            "verificacion": dir_ck,
            "no_doble_conteo": ("por_comp_kN.pp (e*rho*area) y por_comp_kN.pm_adic "
                                "(pm_kn_m2*area) separados en tributaria; misma "
                                "malla, componentes independientes"),
        },
        "EDIFICIO_II": {
            "tipo": "lineal (Kg/m), por metro lineal de vigas/escaleras",
            "familias": eii_filas,
            "total_intensidad_referencia_kn_m": total_ref_kn_m,
            "aplicada_al_FE_kN": 0.0,
            "pendiente_motivo": ("legenda del plano 2024_22-700 sin mapeo "
                                 "familia->viga; DXF no incluido en la copia"),
        },
        "verificaciones": checks,
    }
    (OUT / "PM_ADIC_auditoria_EI_EII.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with open(OUT / "PM_ADIC_auditoria_EI_EII.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["edificio", "nivel", "losa_id", "area_neta_fe_m2",
                    "area_neta_correlacion_m2", "pm_kgf_m2",
                    "pm_kn_m2", "pm_adic_kn", "pp_losa_kn", "espesor_m"])
        for f2 in filas_ei:
            w.writerow(["EI", f2["nivel"], f2["losa_id"], f2["area_neta_fe_m2"],
                        f2["area_neta_correlacion_m2"],
                        f2["pm_kgf_m2"], f2["pm_kn_m2"], f2["pm_adic_kn"],
                        f2["pp_losa_kn"], f2["espesor_m"]])
        for f2 in eii_filas:
            w.writerow(["EII", f2["nivel_aplicabilidad"], f2["familia"], "", "",
                        f2["conversion_a_kn_m"], "", "", ""])

    md = _md(dir_ck, filas_ei, info_nivel, eii_filas, total_ref_kn_m)
    (OUT / "PM_ADIC_auditoria_EI_EII.md").write_text(md, encoding="utf-8")

    print(json.dumps({
        "EI_pm_adic_total_kn": dir_ck["total_calculado_kn"],
        "EI_pp_losas_total_kn": pp_losas_total,
        "EI_referencia_10244_15_kN": dir_ck["checks"][-1]["ok"],
        "EII_familias": len(eii_filas),
        "EII_aplicada_kn": 0.0,
        "EII_pendiente": "todas (sin mapeo familia->viga)",
        "checks_ok": sum(1 for c in checks if c["ok"]),
        "checks_total": len(checks),
        "escrito": [str(p) for p in sorted(OUT.glob("PM_ADIC_auditoria_EI_EII.*"))]},
        ensure_ascii=False, indent=2))
    return 0 if all(c["ok"] for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())