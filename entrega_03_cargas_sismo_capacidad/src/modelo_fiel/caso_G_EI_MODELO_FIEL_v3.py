"""G_EI_MODELO_FIEL_v3 — caso G fiel del EI, iteracion MODELO_FIEL_3 (tarea 7).

RESUELVE realmente (no reusa un artefacto previo):
  * corre el solver OpenSeesPy del modulo v1 `caso_G_EI_MODELO_FIEL` (marco EI,
    cargas nodales G = PP + PM.ADIC sobre areas FE) y exporta:
      - reacciones
      - desplazamientos (324 grados)
      - fuerzas internas por elemento (local/global)
  * mantiene la separacion de MODELO_FIEL_2 (PP confirmado 17.179,23 + PM.ADIC
    EI 10.244,139) e integra MODELO_FIEL_3:
      - inventario_PP_pendiente_EI (PPP, tarea 2): NADA nuevo se aplica
        (las hipotesis base->nivel/contencion/V.S.I./tubulares/muros siguen
        PENDIENTE); AGGES nuevos aplicados = 0.
      - PMADIC_EI_aplicada (tarea 6): 10.244,139 kN en 99 losas.
  * compara v3 vs v2 vs checkpoint (25.227,73) vs publicado.
  * hipotesis abiertas HIPÓTESIS explicitas y sin evidencia.

Escribo en modelo_fiel/:
  EI/G_EI_MODELO_FIEL_v3.json             (reporte/contrato)
  EI/G_EI_MODELO_FIEL_v3.md
  EI/G_EI_MODELO_FIEL_v3_reacciones.csv
  EI/G_EI_MODELO_FIEL_v3_desplazamientos.csv
  EI/G_EI_MODELO_FIEL_v3_fuerzas.csv

Uso:
  python -X utf8 -m src.modelo_fiel.caso_G_EI_MODELO_FIEL_v3
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
OUT_EI = OUT / "EI"
RES = E3 / "results"

FIDELIDAD = "REPRODUCIBLE_FULL_EXPORT_SIN_PP_PENDIENTES_NUEVOS"


def _flatten(fu: dict, pref: str) -> list:
    """Aplana {clave: [vx,vy,vz]} o {clave: {...}} a filas csv."""
    rows = []
    if isinstance(fu, dict):
        for k, v in fu.items():
            if isinstance(v, (list, tuple)):
                for i, comp in enumerate(v):
                    rows.append((pref, k, "comp_%d" % i, comp))
            elif isinstance(v, dict):
                rows.extend(_flatten(v, "%s|%s" % (pref, k)))
            else:
                rows.append((pref, k, "", v))
    elif isinstance(fu, (list, tuple)):
        for i, comp in enumerate(fu):
            rows.append((pref, "-", "comp_%d" % i, comp))
    return rows


def _escritura_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _metricas_solucion(sol) -> dict:
    desp = sol.get("desplazamientos", {})
    fu = sol.get("fuerzas", {})
    def modulo(d):
        m = 0.0
        if isinstance(d, dict):
            for v in d.values():
                if isinstance(v, (list, tuple)):
                    for c in v:
                        m = max(m, abs(c))
                elif isinstance(v, dict):
                    m = max(m, modulo(v))
        elif isinstance(d, (list, tuple)):
            m = max((abs(c) for c in d), default=0.0)
        return m
    return {"n_desplazamientos": len(desp),
            "max_abs_desplazamiento": round(modulo(desp), 8),
            "max_abs_fuerza": round(modulo(fu), 4),
            "reacciones": sol.get("reacciones")}


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_EI.mkdir(parents=True, exist_ok=True)

    # 1) re-solve real
    import src.modelo_fiel.caso_G_EI_MODELO_FIEL as v1
    rc = v1.main()
    v1json = json.loads((OUT_EI / "G_EI_MODELO_FIEL.json").read_text(encoding="utf-8"))
    v2json = json.loads((OUT / "G_EI_MODELO_FIEL_v2.json").read_text(encoding="utf-8"))
    inventario = json.loads((OUT / "inventario_PP_pendiente_EI.json").read_text(encoding="utf-8"))
    pm_ei = json.loads((OUT / "PMADIC_EI_aplicada.json").read_text(encoding="utf-8"))
    led = json.loads((OUT / "ledger_PP_PMADIC_Q.json").read_text(encoding="utf-8"))

    ledger = v1json["ledger"]
    sol = v1json["solucion_despues"]
    sol_antes = v1json["solucion_antes"]
    comparacion = v1json["comparacion"]
    checks = [c for c in ledger["verificaciones"] if c["estado"] == "OK"]

    Pz = ledger["G_despues_kN"]
    Rz = comparacion["solucion_despues"]["R_z_kN"]
    vip = sold = None

    # ---- export completo ----
    reacc = sol.get("reacciones", {})
    desp = sol.get("desplazamientos", {})
    fuerzas = sol.get("fuerzas", {})
    _escritura_csv(OUT_EI / "G_EI_MODELO_FIEL_v3_reacciones.csv",
                   ["nodo", "direccion", "valor_kN"],
                   [(k, "comp_%d" % i, comp)
                    for k, v in reacc.items()
                    for i, comp in enumerate(v if isinstance(v, list) else [v])])
    _escritura_csv(OUT_EI / "G_EI_MODELO_FIEL_v3_desplazamientos.csv",
                   ["nodo", "direccion", "desplazamiento_m"],
                   [(k, "comp_%d" % i, comp)
                    for k, v in desp.items()
                    for i, comp in enumerate(v if isinstance(v, list) else [v])])
    _escritura_csv(OUT_EI / "G_EI_MODELO_FIEL_v3_fuerzas.csv",
                   ["tipo", "elemento", "componente", "valor_cache"],
                   _flatten(fuerzas, "fuerza"))

    metricas = _metricas_solucion(sol)
    metricas_antes = _metricas_solucion(sol_antes)

    pp_losas = led["EI"]["totales"]["PP_losas_kN"]
    pp_el = led["EI"]["totales"]["PP_elementos_kN"]
    pm_adic = led["EI"]["totales"]["PM_ADIC_kN"]
    q = led["EI"]["totales"]["Q_total_kN"]
    pp_total = round(pp_losas + pp_el, 4)

    g_ck = round(pp_losas + pm_adic, 4)
    vs_ck = round(Pz - g_ck, 4)
    vs_v2 = round(Pz - v2json["componentes"]["permanente_aplicada_kN"], 4)
    publicado = v2json["componentes"]["permanente_aplicada_kN"]

    payload = {
        "caso": "G", "edificio": "I", "iteracion": "MODELO_FIEL_3",
        "motor": "OpenSeesPy (re-solve real del marco EI)",
        "clasificacion_fidelidad": {
            "etiq": FIDELIDAD,
            "razon": ("re-solve real exportado completo (reacciones, "
                      "desplazamientos, fuerzas); ningun PP pendiente nuevo se "
                      "aplica (inventario MODELO_FIEL_3)")},
        "componentes": {
            "PP_losas_kN": pp_losas, "PP_vigas_columnas_muros_kN": pp_el,
            "PP_total_kN": pp_total, "PM_ADIC_kN": pm_adic,
            "permanente_aplicada_kN": round(Pz, 4), "Q_sobrecarga_kN": q},
        "PM_ADIC": {"aplicada_kN": pm_adic, "modo": "superficial (99 losas)",
                    "tabla": "PMADIC_EI_aplicada.json"},
        "inventario_PP_pendiente": {
            "nuevo_aplicado_kN": 0.0,
            "n_pendientes": inventario["conteo"]["pendientes"],
            "total_hipotesis_cuantificado_kN": inventario["revision_extra"]["total_hipotesis_cuantificado_kN"],
            "ruta": "inventario_PP_pendiente_EI.json"},
        "solucion": {
            "P_z_kN": round(Pz, 4), "R_z_kN": Rz,
            "residuo_kN": round(Rz - Pz, 6),
            "equilibrio_vertical": "OK" if abs(Rz - Pz) < 1.0 else "ERROR",
            "metricas": metricas, "metricas_antes": metricas_antes,
            "max_desp_z_m": comparacion["solucion_despues"]["max_desp_z_m"]},
        "comparacion": {
            "checkpoint_ku": g_ck,
            "vs_checkpoint_kN": vs_ck,
            "vs_v2_kN": vs_v2,
            "v2_permanente_kN": publicado,
            "estado": "IDENTICO_AL_v2" if abs(vs_v2) < 1e-6 else "DIFERENTE"},
        "export": {
            "reacciones_csv": "EI/G_EI_MODELO_FIEL_v3_reacciones.csv",
            "desplazamientos_csv": "EI/G_EI_MODELO_FIEL_v3_desplazamientos.csv",
            "fuerzas_csv": "EI/G_EI_MODELO_FIEL_v3_fuerzas.csv",
            "n_reacciones": len(reacc), "n_desplazamientos": len(desp)},
        "hipotesis_abiertas": [
            "tramos virtuales BASE->nivel (col 4223.82 + muro 3675.18) NO aplicados",
            "muros de contencion del sotano (554.54) HIPOTESIS_CIMENTACION",
            "V.S.I. 20/150 de CP1S pp~157 kN NO confirmada (D5)",
            "tubulares 300x300x20/5: seccion confirmada, tramo PENDIENTE",
            "P.M.I. sin dimensiones; hormigon P3->P4 desfase +0.1813 m"],
        "verificaciones_v1": {c["check"]: c["estado"] for c in ledger["verificaciones"]},
        "checks_ok": len(checks),
        "checks_total": len(ledger["verificaciones"]),
        "rc_solver": rc}

    (OUT_EI / "G_EI_MODELO_FIEL_v3.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    l = []
    l.append("# G_EI_MODELO_FIEL_v3 (MODELO_FIEL_3 / tarea 7)")
    l.append("")
    l.append("Re-solve real (OpenSeesPy, marco EI). Clasificacion: **%s**"
             % FIDELIDAD)
    l.append("")
    l.append("- PP_total aplicado: **%.4f kN** (= losas %.4f + elementos %.4f)"
             % (pp_total, pp_losas, pp_el))
    l.append("- PM.ADIC aplicada: **%.4f kN** (99 losas)" % pm_adic)
    l.append("- Permanente aplicada (G_despues): **%.2f kN**" % Pz)
    l.append("- Q: %.4f kN" % q)
    l.append("")
    l.append("## Solucion")
    l.append("")
    l.append("- P_z = %.4f ; R_z = %.4f ; residuo = %.6f ; %s"
             % (Pz, Rz, payload["solucion"]["residuo_kN"],
                payload["solucion"]["equilibrio_vertical"]))
    l.append("- max|desplazamiento| = %.8f m ; max|fuerza| = %.4f (unidad de "
             "fuerza del FE)" % (metricas["max_abs_desplazamiento"],
                                 metricas["max_abs_fuerza"]))
    l.append("- max_desp_z = %.8f m" % comparacion["solucion_despues"]["max_desp_z_m"])
    l.append("")
    l.append("## Comparacion")
    l.append("")
    l.append("- checkpoint (G_ck = losas + PM.ADIC): %.2f kN" % g_ck)
    l.append("- vs checkpoint: **+%.4f kN** (PP elementos)" % vs_ck)
    l.append("- vs v2: %.4f kN -> %s" % (vs_v2, payload["comparacion"]["estado"]))
    l.append("")
    l.append("## PP pendiente (inventario MODELO_FIEL_3)")
    l.append("")
    l.append("- Nuevo aplicado al FE: **0.00 kN**")
    l.append("- Pendientes: %d ; hipotesis cuantificadas (no aplicadas): %.2f kN"
             % (inventario["conteo"]["pendientes"],
                inventario["revision_extra"]["total_hipotesis_cuantificado_kN"]))
    for h in payload["hipotesis_abiertas"]:
        l.append("- %s" % h)
    l.append("")
    l.append("## Export")
    l.append("")
    l.append("- reacciones: %d ; desplazamientos: %d ; fuerzas por elemento: csv"
             % (len(reacc), len(desp)))
    l.append("- `EI/G_EI_MODELO_FIEL_v3_reacciones.csv`")
    l.append("- `EI/G_EI_MODELO_FIEL_v3_desplazamientos.csv`")
    l.append("- `EI/G_EI_MODELO_FIEL_v3_fuerzas.csv`")
    l.append("")
    l.append("Verificaciones v1: %d/%d OK ; rc solver=%d"
             % (payload["checks_ok"], payload["checks_total"], rc))
    (OUT_EI / "G_EI_MODELO_FIEL_v3.md").write_text("\n".join(l) + "\n", encoding="utf-8")

    print(json.dumps({
        "G_EI_v3": True, "permanente_aplicada_kN": round(Pz, 4),
        "R_z_kN": Rz, "vs_v2_kN": vs_v2, "vs_checkpoint_kN": vs_ck,
        "n_reacciones": len(reacc), "n_desplazamientos": len(desp),
        "checks_ok": payload["checks_ok"], "checks_total": payload["checks_total"],
        "rc_solver": rc}, ensure_ascii=False, indent=2))
    return 0 if (payload["checks_ok"] == payload["checks_total"]
                 and payload["solucion"]["equilibrio_vertical"] == "OK"
                 and rc == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())