"""G_EII_MODELO_FIEL — caso G fiel (primera iteracion) del Edificio II.

El caso G del EII ya esta resuelto por el pipeline reproducible (V.60/80):
PP de elementos + PP de losas entregados a nodos con camino vertical
= 25.970,999 kN. G_EII_MODELO_FIEL NO cambia numeros: documenta EXACTAMENTE
lo confirmado y lo pendiente, con las diferencias identidad por componente y
la tabla de los 14 ruteos SIN camino estructural confirmado:

  * confirmados  : columnas 1.522,30 ; vigas (incl. V_031) 11.585,48 ;
                   muros DIRECTOS del pipeline 3.192,47 ; losas aplicadas
                   9.670,75  =>  25.970,999 kN (verificado contra el
                   caso_G_EII_reproducible.json del checkpoint).
  * pendientes   : muros - 3.328,79 kN (publicado 6.521,26 - directo
                   3.192,47; A=t*(L/2) por montante en vez de A=t*L);
                   losas +6,27 kN (publicado 9.677,03 vs aplicada 9.670,75,
                   por discretizacion mallado/receptores sin FE);
                   ruteo no transferido 417,85 kN (14 cargas SIN camino);
                   V_031 V.30/80 (escenario alternativo, hipotesis de seccion
                   sin eleccion); rigidLinks de la franja D-D' (hipotesis
                   documentada, no resorte publicado).
  * total publi  : 29.306,07 kN ; brecha global 3.335,07 kN.

Salidas bajo modelo_fiel/EII/ (sin tocar results/ del checkpoint):
  G_EII_MODELO_FIEL.json            contrato (ledger + solucion resumida)
  G_EII_MODELO_FIEL_ledger.json     identidad de diferencias por componente
  G_EII_MODELO_FIEL_ruteos_14.csv   tabla de los 14 ruteos pendientes
  G_EII_MODELO_FIEL.md              resumen legible

Uso:
  python -X utf8 -m src.modelo_fiel.caso_G_EII_MODELO_FIEL
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
RES = E3 / "results"
OUT = E3 / "modelo_fiel" / "EII"
RUTEO_AUDIT = RES / "cargas" / "ruteo_G_EII_auditoria.json"
REPRO = RES / "cargas" / "caso_G_EII_reproducible.json"

sys.path.insert(0, str(E3))
sys.path.insert(0, str(REPO / "analisis_estructural" / "edificio_I" / "src"))

from src.cargas.pipeline_FE_EII import (  # noqa: E402
    GAMMA_CONCRETO_KN_M3,
    MarcoEII,
    ORDEN_NIVELES,
    V031_SECCIONES,
)

PUBLICADO_EII = {
    "columnas": 1522.31, "vigas": 11585.48, "muros": 6521.26,
    "total_elementos": 19629.04, "total": 29306.0667}


def _L(rec):
    return math.hypot(rec["u_j"] - rec["u_i"], rec["v_j"] - rec["v_i"],
                      rec["z_j"] - rec["z_i"])


def _componentes(marco):
    tot = {}
    v031 = 0.0
    for rec in marco.columnas + marco.vigas_elem + marco.muros_elem:
        W = rec["sec_valores"]["A"] * _L(rec) * GAMMA_CONCRETO_KN_M3
        if rec in marco.muros_elem:
            key = "muros"
        elif rec in marco.columnas:
            key = "columnas"
        else:
            key = "vigas"
        if "V_031" in rec.get("elemento_id", ""):
            v031 += W
        tot[key] = tot.get(key, 0.0) + W
    ev = tot["columnas"] + tot["vigas"] + tot["muros"]
    return {"columnas": tot.get("columnas", 0.0), "vigas": tot.get("vigas", 0.0),
            "v_031": v031, "muros": tot.get("muros", 0.0),
            "total_elementos": ev}


def _losas_directo(marco):
    from shapely.geometry import Polygon
    area_pp = 0.0
    for lv in marco.viewer["niveles"]:
        for lo in lv["losas"]:
            p = Polygon(lo["poligono_exterior"])
            for ab in lo.get("aberturas_poligonos", []):
                p = p.difference(Polygon(ab))
            area_pp += p.area * float(lo["espesor"]) * GAMMA_CONCRETO_KN_M3
    return area_pp


def max_desp_z(sol):
    return max((abs(v[2]) for v in sol["desplazamientos"].values()), default=0.0)


def _tabla_ruteos_pendientes(marco):
    """Las transferencias SIN camino estructural confirmado (estado PENDIENTE)."""
    rows = [x for x in getattr(marco, "cargas_redirigidas", [])
            if x["estado"] == "PENDIENTE"]
    rows.sort(key=lambda r: (r["nivel"], r["nodo_original"]))
    pend_kN = sum(abs(x["carga_efectiva_kN"]) for x in rows)
    return rows, pend_kN


def _build_ledger(marco, sol, cargas, ruteo_rows, pend_kN, repro_total) -> dict:
    comp = _componentes(marco)
    losa_directa = _losas_directo(marco)
    elems = comp["total_elementos"]
    losa_aplicada = repro_total - elems
    Pz = -sum(f[2] for f in cargas.values())
    Rz = sum(r[2] for r in sol["reacciones"].values())

    pub_losas = PUBLICADO_EII["total"] - PUBLICADO_EII["total_elementos"]
    filas = [
        {"componente": "losas (aplicada via mallado)",
         "publicado_kN": round(pub_losas, 4),
         "reproducible_kN": round(losa_aplicada, 6),
         "diferencia_pub_repro_kN": round(pub_losas - losa_aplicada, 8)},
        {"componente": "losas (directa geometria publicada)",
         "publicado_kN": None, "reproducible_kN": round(losa_directa, 6),
         "diferencia_pub_repro_kN": None},
        {"componente": "vigas (incluye V_031)",
         "publicado_kN": PUBLICADO_EII["vigas"],
         "reproducible_kN": round(comp["vigas"], 6),
         "diferencia_pub_repro_kN": round(PUBLICADO_EII["vigas"] - comp["vigas"], 8)},
        {"componente": "V_031 (subconjunto de vigas)",
         "publicado_kN": "incluido en vigas",
         "reproducible_kN": round(comp["v_031"], 6),
         "diferencia_pub_repro_kN": "no publicado por separado"},
        {"componente": "columnas",
         "publicado_kN": PUBLICADO_EII["columnas"],
         "reproducible_kN": round(comp["columnas"], 6),
         "diferencia_pub_repro_kN": round(PUBLICADO_EII["columnas"] - comp["columnas"], 8)},
        {"componente": "muros (pipeline A=t*(L/2) por montante)",
         "publicado_kN": PUBLICADO_EII["muros"],
         "reproducible_kN": round(comp["muros"], 6),
         "diferencia_pub_repro_kN": round(PUBLICADO_EII["muros"] - comp["muros"], 8)},
    ]
    gap = PUBLICADO_EII["total"] - repro_total
    return {
        "nombre_estado": "G_EII_MODELO_FIEL_1",
        "G_confirmado_kN": round(repro_total, 6),
        "G_por_componente_confirmado_kN": {
            "columnas": round(comp["columnas"], 4),
            "vigas_incl_V031": round(comp["vigas"], 4),
            "V_031": round(comp["v_031"], 4),
            "muros_pipeline_directo": round(comp["muros"], 4),
            "losas_aplicada": round(losa_aplicada, 4)},
        "pendientes_explicitos": {
            "muros_kN": round(PUBLICADO_EII["muros"] - comp["muros"], 4),
            "muros_explicacion": ("publicado 6521.26 vs pipeline 3192.47: "
                                  "A=t*(L/2) por montante (3.192,47); la identidad "
                                  "A=t*L por panel daria 4.330,02; deficit = 2.191,24 "
                                  "+ 1.137,55 = 3.328,79"),
            "losas_kN": round(pub_losas - losa_aplicada, 4),
            "ruteo_no_transferido_kN": round(pend_kN, 4),
            "n_ruteos_sin_camino": len(ruteo_rows),
            "ruteo_explicacion": ("14 cargas SIN camino estructural confirmado "
                                  "(cruce de vano o salida por junta); se dejan en "
                                  "su nodo original (no transferidas)"),
            "v_031_seccion_alternativa": {
                "escenario": "V.30/80", "estado": "HIPOTESIS_MODELO (sin eleccion)",
                "V60_80_kN": round(comp["vigas"], 4)},
            "rigidLinks_franja_DD": {
                "n": len(marco._strip_enlazados),
                "estado": "HIPOTESIS (documentada, no resorte publicado)",
                "nota": "16 rigidLink('beam'); 8 a 0.15 m sobre M_003_B/M_004_B "
                        "(defensible) y 8 a 1.61-4.14 m (HIPOTESIS_ESTRUCTURAL)"}},
        "total_publicado_kN": PUBLICADO_EII["total"],
        "diferencia_global_kN": round(gap, 4),
        "identidad_componentes": {
            "suma_componentes_mas_losas_kN": round(elems + losa_aplicada, 6),
            "P_z_aplicada_kN": round(Pz, 6),
            "ok": abs(Pz - (elems + losa_aplicada)) < 0.05},
        "equilibrio_vertical": {"R_z_kN": round(Rz, 4),
                                "P_z_kN": round(Pz, 4),
                                "residuo_kN": round(Rz - Pz, 8),
                                "ok": abs(Rz - Pz) <= 1e-6},
        "coincide_con_checkpoint": {
            "caso_G_EII_reproducible_Fz_kN": round(repro_total, 6),
            "G_MODELO_FIEL_Fz_kN": round(Pz, 6),
            "ok": abs(repro_total - Pz) < 0.01},
        "filas_componente": filas,
        "residuo_identidad_NOTAS": (
            "losas publicadas = 29306.0667 - 19629.04 = 9677.03 kN; aplicadas "
            "aprox 9670.75 => +6.27. Muros +3.328,79. Redondeo publicado +0.01 "
            "=> brecha global 3335.07 (29306.0667 - 25970.999)."),
    }


def _tabla_csv(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "origen", "elemento_id", "nivel",
                    "nodo_original", "nodo_original_xyz",
                    "receptor", "receptor_xyz", "tipo_receptor",
                    "distancia_m", "carga_efectiva_kN", "carga_pendiente_kN",
                    "clasificacion", "razon"])
        for i, r in enumerate(rows, start=1):
            w.writerow([i, r["origen"], r.get("elemento_id"), r["nivel"],
                        r["nodo_original"], r["nodo_original_xyz"],
                        r["receptor"], r["receptor_xyz"], r["tipo_receptor"],
                        r["distancia_m"], r["carga_efectiva_kN"],
                        r["carga_transferida_kN"], r["clasificacion"],
                        r["razon"]])


def _markdown(ledger, ruteo_rows) -> str:
    l = []
    l.append("# G_EII_MODELO_FIEL (primera iteracion)")
    l.append("")
    l.append("Estado congelado: **%s**" % ledger["nombre_estado"])
    l.append("")
    l.append("G confirmado (reproducible V.60/80) = **%.3f kN**"
             % ledger["G_confirmado_kN"])
    l.append("")
    l.append("| componente | publicado (kN) | reproducible (kN) | dif (pub-pro) |")
    l.append("|---|---|---|---|")
    for r in ledger["filas_componente"]:
        l.append("| %s | %s | %s | %s |" % (r["componente"], r["publicado_kN"],
                                            r["reproducible_kN"],
                                            r["diferencia_pub_repro_kN"]))
    l.append("")
    l.append("## Pendientes explicitos (NO aplicados)")
    l.append("")
    l.append("- muros **%.2f kN** (%s)" % (ledger["pendientes_explicitos"]["muros_kN"],
                                           ledger["pendientes_explicitos"]["muros_explicacion"]))
    l.append("- losas **%.2f kN** (discretizacion mallado/receptores sin FE)"
             % ledger["pendientes_explicitos"]["losas_kN"])
    l.append("- ruteo sin camino **%.2f kN** (%d cargas, tabla abajo)"
             % (ledger["pendientes_explicitos"]["ruteo_no_transferido_kN"],
                ledger["pendientes_explicitos"]["n_ruteos_sin_camino"]))
    l.append("- V_031 V.30/80 alternativo: %r"
             % ledger["pendientes_explicitos"]["v_031_seccion_alternativa"])
    l.append("- rigidLinks franja D-D': %s" % str(
        ledger["pendientes_explicitos"]["rigidLinks_franja_DD"]))
    l.append("")
    l.append("## Verificaciones")
    l.append("")
    for k in ("identidad_componentes", "equilibrio_vertical",
              "coincide_con_checkpoint"):
        v = ledger[k]
        l.append("- **%s**: %s" % (k, "OK" if v["ok"] else "ERROR"))
    l.append("")
    l.append("Brecha global: publicado %.2f - fiel %.2f = **%.2f kN**"
             % (ledger["total_publicado_kN"], ledger["G_confirmado_kN"],
                ledger["diferencia_global_kN"]))
    l.append("")
    l.append("## Tabla de los %d ruteos SIN camino estructural confirmado"
             % len(ruteo_rows))
    l.append("")
    l.append("| n | origen | nivel | nodo | receptor | dist (m) | carga efe. (kN) | motivo |")
    l.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(ruteo_rows, start=1):
        l.append("| %d | %s | %s | %d | %d | %.4f | %.3f | %s |"
                 % (i, r["origen"], r["nivel"], r["nodo_original"],
                    r["receptor"], r["distancia_m"], r["carga_efectiva_kN"],
                    r["razon"][:60]))
    l.append("")
    l.append("Total no transferido: **%.4f kN**" % sum(
        r["carga_efectiva_kN"] for r in ruteo_rows) * -1)
    return "\n".join(l) + "\n"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    marco = MarcoEII(v031_seccion="V.60/80")
    marco.construir()
    pp = marco.peso_propio_nodal()
    losas, repartos = marco.losa_tributaria_nodal(incluir_sc=False)
    cargas = {}
    for agg in (pp, losas):
        for tag, f in agg.items():
            cur = cargas.setdefault(int(tag), [0.0] * 6)
            for i in range(6):
                cur[i] += f[i]
    sol = marco.resolver_caso({"EII": cargas})
    if not sol["ok"]:
        print(json.dumps({"estado": "FALLO", "diagnostico": sol.get("diagnostico")},
                         ensure_ascii=False, indent=2))
        return 1

    repro_total = abs(sol["F_total_kN"][2])
    checkpoint = json.loads(REPRO.read_text(encoding="utf-8"))
    repro_ck = abs(checkpoint["solucion"]["F_total_aplicado_kN"][2])

    ruteo_rows, pend_kN = _tabla_ruteos_pendientes(marco)
    ledger = _build_ledger(marco, sol, cargas, ruteo_rows, pend_kN, repro_total)
    ledger["coincide_con_checkpoint"] = {
        "caso_G_EII_reproducible_Fz_kN": round(repro_ck, 6),
        "G_MODELO_FIEL_Fz_kN": round(repro_total, 6),
        "ok": abs(repro_ck - repro_total) < 0.01}
    # cruce contra el ruteo canonico del checkpoint
    audit_ruteo = json.loads(RUTEO_AUDIT.read_text(encoding="utf-8"))
    pend_ck = audit_ruteo["carga_pendiente_no_transferida_kN"]
    n_loop = audit_ruteo["pendientes"]

    checks = [
        {"check": "G_igual_checkpoint", "estado": "OK" if ledger
         ["coincide_con_checkpoint"]["ok"] else "ERROR",
         "detalle": "fiel %.4f vs checkpoint %.4f" % (repro_total, repro_ck)},
        {"check": "equilibrio_vertical", "estado": "OK" if ledger
         ["equilibrio_vertical"]["ok"] else "ERROR",
         "detalle": ledger["equilibrio_vertical"]["residuo_kN"]},
        {"check": "identidad_cargas_vs_geometria", "estado": "OK" if ledger
         ["identidad_componentes"]["ok"] else "ERROR",
         "detalle": ledger["identidad_componentes"]},
        {"check": "ruteo_pendientes_14",
         "estado": "OK" if len(ruteo_rows) == n_loop == 14 else "ERROR",
         "detalle": "fiel %d vs checkpoint %d" % (len(ruteo_rows), n_loop)},
        {"check": "carga_pendiente_ruteo", "estado": "OK" if abs(
            pend_kN - pend_ck) < 1e-3 and abs(pend_ck - 417.850839) < 1e-3
            else "ERROR",
         "detalle": "fiel %.6f vs checkpoint %.6f vs nota 417.850839"
         % (pend_kN, pend_ck)},
        {"check": "no_doble_conteo_pares_ruteo",
         "estado": "OK" if len({(r["origen"], r.get("elemento_id"),
                                 r["nodo_original"], r["receptor"],
                                 r["carga_efectiva_kN"]) for r in ruteo_rows})
         == len(ruteo_rows) else "ERROR",
         "detalle": "14 filas unicas por (origen, elemento, nodo, receptor, carga)"},
    ]
    ledger["verificaciones"] = checks

    payload = {
        "caso": "G", "edificio": "II", "iteracion": "MODELO_FIEL_1",
        "motor": "OpenSeesPy (pipeline reproducible EII, mismo que checkpoint)",
        "v031_seccion_escenario": "V.60/80",
        "fuentes": ["solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.60_80.json "
                    "(solo lectura, via pipeline)",
                    "ruteo_G_EII_auditoria.json (cruce canonical del checkpoint)"],
        "reglas": {
            "camino_estructural": ("PP de elementos a sus 2 nodos extremos por "
                                   "mitades; mitades en nodos de viga sin apoyo "
                                   "se derivan al receptor vertical mas cercano "
                                   "del mismo nivel; las que cruzan vano o junta "
                                   "quedan PENDIENTES en su nodo original"),
            "convencion_muro": "A = t*(L/2) por montante (2 montantes por panel)"},
        "ledger": ledger,
        "solucion_resumen": {
            "ok": sol["ok"], "n_reacciones": sol.get("n_reacciones"),
            "F_total_aplicado_kN": [round(x, 6) for x in sol["F_total_kN"]],
            "R_z_kN": round(sum(r[2] for r in sol["reacciones"].values()), 6),
            "max_desp_z_m": round(max_desp_z(sol), 8),
            "reacciones": {str(k): [round(x, 6) for x in v]
                           for k, v in sol["reacciones"].items()}},
        "nota_solucion_completa": str(REPRO),
    }

    (OUT / "G_EII_MODELO_FIEL.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "G_EII_MODELO_FIEL_ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _tabla_csv(ruteo_rows, OUT / "G_EII_MODELO_FIEL_ruteos_14.csv")
    (OUT / "G_EII_MODELO_FIEL.md").write_text(_markdown(ledger, ruteo_rows),
                                              encoding="utf-8")

    resumen = {"edificio": "II", "perfil": "G_EII_MODELO_FIEL",
               "G_confirmado_kN": round(repro_total, 4),
               "pendientes_kN": {"muros": ledger["pendientes_explicitos"]["muros_kN"],
                                 "losas": ledger["pendientes_explicitos"]["losas_kN"],
                                 "ruteo": round(pend_kN, 4)},
               "n_ruteos_sin_camino": len(ruteo_rows),
               "checks_ok": sum(1 for c in checks if c["estado"] == "OK"),
               "checks_total": len(checks),
               "escrito": [str(p) for p in sorted(OUT.glob("G_EII_MODELO_FIEL*"))]}
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0 if all(c["estado"] == "OK" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())