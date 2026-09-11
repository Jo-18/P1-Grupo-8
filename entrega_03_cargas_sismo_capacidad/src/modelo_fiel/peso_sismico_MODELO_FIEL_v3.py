"""Peso sismico MODELO_FIEL_3: escenarios por piso con masa/CM y componentes
integrando inventarios v3 (tarea 8).

Reutiliza el contrato del ledger y el modulo v2 (mismo reparto nodal por banda
z); recalcula TODO el escenario en ejecucion (re-solve aritmetico) y agrega:
  * W_B (PRINCIPAL) = PP + PM_ADIC + 0.5*Q
  * W_A (sensibilidad) = PP + 0.5*Q  (sin PM.ADIC)
  * componentes v3 desde los inventarios:
      - PP_EI confirmado 17.179,23 con inventario de pendientes (rango
        cuantificado 8.453,55 kN NO aplicado)
      - PM.ADIC EI 10.244,139 kN (99 losas)
      - PM.ADIC EII 0 (mapeo 0, cobertura 0) + catalogo A-F solo referencia
  * verificacion: v3 == v2 == v1 (no se confirma ningun PP/P.M. nuevo).

Escribo en modelo_fiel/:
  peso_sismico_MODELO_FIEL_v3.json/.csv/.md

Uso:
  python -X utf8 -m src.modelo_fiel.peso_sismico_MODELO_FIEL_v3
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
AUDIT_EI = RES / "peso_propio_teorico_EDIFICIO_I_v2.json"

sys.path.insert(0, str(E3))
sys.path.insert(0, str(REPO / "analisis_estructural" / "edificio_I" / "src"))

import src.modelo_fiel.peso_sismico_MODELO_FIEL_v2 as v2mod  # noqa: E402
from src.cargas.pipeline_FE_EII import MarcoEII                          # noqa: E402
from src.modelo_fiel.caso_G_EI_MODELO_FIEL import construir_marco_EI     # noqa: E402
from src.modelo_fiel.ledger_PP_PMADIC_Q import GRAV                       # noqa: E402

PEND_EII = 3328.79 + 6.27 + 417.85
TOL = 0.05


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    audit = json.loads(AUDIT_EI.read_text(encoding="utf-8"))
    inventario = json.loads((OUT / "inventario_PP_pendiente_EI.json").read_text(
        encoding="utf-8"))
    pm_ei = json.loads((OUT / "PMADIC_EI_aplicada.json").read_text(
        encoding="utf-8"))
    mapeo = json.loads((OUT / "mapeo_PMADIC_EII_plano700.json").read_text(
        encoding="utf-8"))
    led = json.loads((OUT / "ledger_PP_PMADIC_Q.json").read_text(
        encoding="utf-8"))

    marcos = {"EI": construir_marco_EI(),
              "EII": (lambda m: (m.construir(), m)[1])(MarcoEII(v031_seccion="V.60/80"))}
    esc = v2mod._bandas_esc(marcos, audit)
    ei, eii = esc["EI"], esc["EII"]

    rango_EI = inventario["revision_extra"]["total_hipotesis_cuantificado_kN"]
    wb_ei, wa_ei = ei["resumen"]["W_B_kN"], ei["resumen"]["W_A_kN"]
    wb_eii, wa_eii = eii["resumen"]["W_B_kN"], eii["resumen"]["W_A_kN"]

    checks = v2mod._verificaciones(esc)
    checks.append({
        "check": "v3_sin_nuevos_componentes",
        "ok": abs(wb_ei - v2mod.WEB1) < TOL and abs(wb_eii - v2mod.WEII1) < TOL,
        "detalle": ("v3 == v1/v2 (EI 46.516,43 ; EII 28.600,71): ningun PP/P.M.ADIC "
                    "nuevo confirmado (inventario/mapeo MODELO_FIEL_3)")})
    checks.append({
        "check": "eii_pmadic_0",
        "ok": mapeo["aplicacion"]["aplicada_al_FE_kN"] == 0.0,
        "detalle": "EII PM.ADIC aplicada = 0 (mapeo AMBIGUO, cobertura 0)"})
    checks.append({
        "check": "pm_ei_total_documentado",
        "ok": abs(pm_ei["total_aplicada_kN"] - led["EI"]["totales"]["PM_ADIC_kN"]) < 0.1,
        "detalle": "PM.ADIC EI tabla v3 (10.244,139) == ledger (10.244,13...)"})

    rangos = {
        "EI": {"escenario_B_PRINCIPAL_kN": [wb_ei, round(wb_ei + rango_EI, 2)],
               "escenario_A_sensibilidad_kN": [wa_ei, round(wa_ei + rango_EI, 2)],
               "pendientes_cuantificadas_kN": round(rango_EI, 2),
               "nota": inventario["revision_extra"]["nota"]},
        "EII": {"escenario_B_PRINCIPAL_kN": [wb_eii, round(wb_eii + PEND_EII, 2)],
                "escenario_A_sensibilidad_kN": [wa_eii, round(wa_eii + PEND_EII, 2)],
                "pendientes_cuantificadas_kN": round(PEND_EII, 2),
                "nota": "muros 3.328,79 + losas 6,27 + ruteo 417,85 kN"},
    }

    payload = {"caso": "peso_sismico_escenarios_A_B",
               "iteracion": "MODELO_FIEL_3",
               "q_Q_kN_m2": 2.0, "fraccion_Q": 0.5, "g_m_s2": GRAV,
               "escenario_B_PRINCIPAL": "PP + PM_ADIC + 0.5*Q",
               "escenario_A_sensibilidad": "PP + 0.5*Q",
               "componentes_v3": {
                   "PP_EI_confirmado_kN": aud_total_pp if False else round(
                       led["EI"]["totales"]["PP_losas_kN"]
                       + led["EI"]["totales"]["PP_elementos_kN"], 4),
                   "PM_ADIC_EI_kN": pm_ei["total_aplicada_kN"],
                   "PP_EII_confirmado_kN": round(
                       led["EII"]["totales"]["PP_losas_kN"]
                       + led["EII"]["totales"]["PP_elementos_kN"], 4),
                   "PM_ADIC_EII_kN": 0.0},
               "EI": ei, "EII": eii,
               "rangos_por_pendientes": rangos,
               "referencia_v1_kN": {"EI": v2mod.WEB1, "EII": v2mod.WEII1},
               "inventario_PP_pendiente_EI": inventario["conteo"],
               "mapeo_PMADIC_EII": mapeo["resumen"],
               "verificaciones": checks}

    (OUT / "peso_sismico_MODELO_FIEL_v3.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with open(OUT / "peso_sismico_MODELO_FIEL_v3.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["edificio", "nivel", "z_m", "G_kN", "Q_kN", "W_A_kN",
                    "W_B_kN", "masa_A_Mg", "masa_B_Mg",
                    "CM_A_x_m", "CM_A_y_m", "CM_B_x_m", "CM_B_y_m"])
        for ed in ("EI", "EII"):
            for b in esc[ed]["bandas"]:
                w.writerow([ed, b["nivel"], b["z_m"], b["G_aplicada_kN"],
                            b["Q_total_kN"], b["W_A_kN"], b["W_B_kN"],
                            b["masa_A_Mg"], b["masa_B_Mg"],
                            b["CM_A_x_m"], b["CM_A_y_m"],
                            b["CM_B_x_m"], b["CM_B_y_m"]])

    l = []
    l.append("# Peso sismico MODELO_FIEL_3 (tarea 8)")
    l.append("")
    l.append("- B (PRINCIPAL): W_B = PP + PM_ADIC + 0.5*Q")
    l.append("- A (sensibilidad): W_A = PP + 0.5*Q")
    l.append("")
    for ed, lbl in (("EI", "EDIFICIO I"), ("EII", "EDIFICIO II")):
        r = esc[ed]["resumen"]
        l.append("## %s" % lbl)
        l.append("- B_PRINCIPAL: %.2f kN (%.2f Mg) ; A_sensibilidad: %.2f kN (%.2f Mg)"
                 % (r["W_B_kN"], r["masa_B_Mg"], r["W_A_kN"], r["masa_A_Mg"]))
        l.append("- vs v1: B %.2f / A %.2f kN" % (r["diferencia_B_minus_v1_kN"],
                                                  r["diferencia_A_minus_v1_kN"]))
        rng = rangos[ed]
        l.append("- Rango B principal: [%.2f, %.2f] ; A sensibilidad: [%.2f, %.2f]"
                 % (rng["escenario_B_PRINCIPAL_kN"][0],
                    rng["escenario_B_PRINCIPAL_kN"][1],
                    rng["escenario_A_sensibilidad_kN"][0],
                    rng["escenario_A_sensibilidad_kN"][1]))
        l.append("  - pendientes cuantificadas: +%.2f kN (%s)"
                 % (rng["pendientes_cuantificadas_kN"], rng["nota"]))
        l.append("")
        l.append("| nivel | z (m) | G (kN) | Q (kN) | W_A (kN) | W_B (kN) | "
                 "masa_B (Mg) | CM_B x/y (m) |")
        l.append("|---|---|---|---|---|---|---|---|")
        for b in esc[ed]["bandas"]:
            l.append("| %s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %s / %s |"
                     % (b["nivel"], b["z_m"], b["G_aplicada_kN"], b["Q_total_kN"],
                        b["W_A_kN"], b["W_B_kN"], b["masa_B_Mg"],
                        b["CM_B_x_m"], b["CM_B_y_m"]))
        l.append("")
    l.append("## Verificaciones")
    l.append("")
    for c in checks:
        l.append("- [%s] %s: %s" % ("OK" if c["ok"] else "ERROR", c["check"],
                                    c["detalle"]))
    (OUT / "peso_sismico_MODELO_FIEL_v3.md").write_text(
        "\n".join(l) + "\n", encoding="utf-8")

    print(json.dumps({
        "peso_sismico_v3": True,
        "EI_B_PRINCIPAL_kN": wb_ei, "EI_A_kN": wa_ei,
        "EII_B_PRINCIPAL_kN": wb_eii, "EII_A_kN": wa_eii,
        "rango_EI_kN": rango_EI,
        "checks_ok": sum(1 for c in checks if c["ok"]),
        "checks_total": len(checks)}, ensure_ascii=False, indent=2))
    return 0 if all(c["ok"] for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())