"""Peso sismico MODELO_FIEL_2: escenarios A y B por piso con masa y CM.

Escenarios (q_Q = 2.0 kN/m2, fraccion 0.5):
  * Escenario A: W_A = PP_total + 0.50*Q                  (excluye PM.ADIC)
  * Escenario B: W_B = PP_total + PM_ADIC + 0.50*Q        (= G completa + 0.5Q)

Reutiliza el contrato de `ledger_PP_PMADIC_Q.escenarios_EI/EII` (reparto nodal
por banda z, mismo criterio que el checkpoint: EI 6 bandas, EII 5 bandas).
Para EI la banda -7.01 'sotano nucleo' queda dentro de CP1S en la vista de 5
pisos; aqui se reporta la vista de bandas (igual a los artefactos del
checkpoint y al peso v1) y el rollup a 5 pisos.

Incluye por escenario: peso (kN), masa (Mg = kN/9.80665), CM (x,y) por piso,
rango posible por pendientes cuantificadas y diferencia vs checkpoint y vs
peso v1 (EI: W_B = 46.516,43 coincide con v1; W_A difiere en PM.ADIC
10.244,15; EII: A == B == 28.600,71 = v1).

Salidas en modelo_fiel/:
  peso_sismico_MODELO_FIEL_v2.json/.csv/.md

Uso:
  python -X utf8 -m src.modelo_fiel.peso_sismico_MODELO_FIEL_v2
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

from src.cargas.pipeline_FE_EII import MarcoEII          # noqa: E402
from src.modelo_fiel.caso_G_EI_MODELO_FIEL import (      # noqa: E402
    construir_marco_EI,
)
from src.modelo_fiel.ledger_PP_PMADIC_Q import (         # noqa: E402
    GRAV, escenarios_EI, escenarios_EII,
)

TOL = 0.05
PEND_EI = 4223.82 + 3675.18 + 554.54      # tramos base (col+muro) + contencion
PEND_EII = 3328.79 + 6.27 + 417.85        # muros + losas + ruteo (v1)
WEB1 = 46516.43                           # peso v1 EI (escenario B)
WEII1 = 28600.71                          # peso v1 EII


def _bandas_esc(marcos, audit) -> dict:
    ei = escenarios_EI(marcos["EI"], audit)
    eii = escenarios_EII(marcos["EII"])
    out = {"EI": ei, "EII": eii}

    # vista por banda con masa y diffs
    for ed, esc in (("EI", ei), ("EII", eii)):
        bandas = []
        for z, b in sorted(esc["por_banda"].items(), key=lambda kv: float(kv[0])):
            t = b["Q_total_kN"]
            wa, wb = b["W_A_kN"], b["W_B_kN"]
            fila = dict(b)
            fila["masa_A_Mg"] = round(wa / GRAV, 4)
            fila["masa_B_Mg"] = round(wb / GRAV, 4)
            if ed == "EI":
                g_ck = b["PP_losas_kN"] + b["PM_ADIC_kN"]         # checkpoint
                w_ck = g_ck + 0.5 * t
                fila["W_checkpoint_kN"] = round(w_ck, 4)
                fila["diff_B_vs_checkpoint_kN"] = round(wb - w_ck, 4)
                fila["diff_A_vs_checkpoint_kN"] = round(wa - w_ck, 4)
                fila["diff_A_vs_B_kN"] = round(wa - wb, 4)
            else:
                fila["W_checkpoint_kN"] = b["G_aplicada_kN"]
                fila["diff_B_vs_checkpoint_kN"] = 0.0
                fila["diff_A_vs_checkpoint_kN"] = 0.0
                fila["diff_A_vs_B_kN"] = 0.0
            bandas.append(fila)
        esc["bandas"] = bandas

    # totales por escenario
    for ed, esc in (("EI", ei), ("EII", eii)):
        t = esc["totales"]
        wa, wb = t["W_A_total_kN"], t["W_B_total_kN"]
        ck = wa if ed == "EII" else None
        esc["resumen"] = {
            "W_A_kN": round(wa, 4),
            "W_B_kN": round(wb, 4),
            "masa_A_Mg": round(wa / GRAV, 4),
            "masa_B_Mg": round(wb / GRAV, 4),
            "diferencia_A_minus_B_kN": round(wa - wb, 4),
            "diferencia_B_minus_v1_kN": round(wb - (WEB1 if ed == "EI" else WEII1), 4),
            "diferencia_A_minus_v1_kN": round(wa - (WEB1 if ed == "EI" else WEII1), 4),
        }
    return out


def _rangos(esc) -> dict:
    ei, eii = esc["EI"], esc["EII"]
    return {
        "EI": {
            "escenario_A_kN": [round(ei["resumen"]["W_A_kN"], 2),
                               round(ei["resumen"]["W_A_kN"] + PEND_EI, 2)],
            "escenario_B_kN": [round(ei["resumen"]["W_B_kN"], 2),
                               round(ei["resumen"]["W_B_kN"] + PEND_EI, 2)],
            "pendientes_cuantificadas_kN": round(PEND_EI, 2),
            "nota": ("tramos virtuales BASE->nivel (columnas 4.223,82) + muros "
                     "base 3.675,18 + contencion 554,54; NO incluye V.S.I. 20/150 "
                     "ni metalicos (PP no cuantificado)")},
        "EII": {
            "escenario_A_kN": [round(eii["resumen"]["W_A_kN"], 2),
                               round(eii["resumen"]["W_A_kN"] + PEND_EII, 2)],
            "escenario_B_kN": [round(eii["resumen"]["W_B_kN"], 2),
                               round(eii["resumen"]["W_B_kN"] + PEND_EII, 2)],
            "pendientes_cuantificadas_kN": round(PEND_EII, 2),
            "nota": "muros 3.328,79 + losas 6,27 + ruteo 417,85 kN"},
    }


def _verificaciones(esc) -> list:
    ei, eii = esc["EI"], esc["EII"]
    rows = [
        {"check": "ei_wb_v1", "ok": abs(ei["resumen"]["W_B_kN"] - WEB1) < TOL,
         "detalle": "EI escenario B == v1 (46.516,43)"},
        {"check": "ei_wa_minus_wb_pm", "ok": abs(
            eii["totales"]["PM_ADIC_kN"]) < 1e-9 or abs(
            ei["resumen"]["diferencia_A_minus_B_kN"]
            + ei["totales"]["PM_ADIC_kN"]) < TOL,
         "detalle": "EI W_A = W_B - PM.ADIC"},
        {"check": "eii_ab_v1", "ok": abs(eii["resumen"]["W_A_kN"] - WEII1) < TOL
         and abs(eii["resumen"]["W_B_kN"] - WEII1) < TOL,
         "detalle": "EII A == B == v1 (28.600,71)"},
        {"check": "eii_cm_eq", "ok": all(
            abs(b["CM_A_x_m"] - b["CM_B_x_m"]) < 1e-9 and
            abs(b["CM_A_y_m"] - b["CM_B_y_m"]) < 1e-9 for b in eii["bandas"]),
         "detalle": "EII CM_A == CM_B (PM.ADIC 0)"},
        {"check": "masa_recompute", "ok": all(
            abs(b["masa_A_Mg"] - b["W_A_kN"] / GRAV) < 1e-3
            for b in list(ei["bandas"]) + list(eii["bandas"])),
         "detalle": "masa = W / 9.80665"},
        {"check": "ei_diff_ck_el", "ok": abs(
            sum(b["diff_B_vs_checkpoint_kN"] for b in ei["bandas"])
            - ei["totales"]["PP_elementos_kN"]) < TOL,
         "detalle": "EI diff vs checkpoint (escenario B) = PP_elementos"},
        {"check": "eii_diff_ck", "ok": all(
            abs(b["diff_B_vs_checkpoint_kN"]) < TOL for b in eii["bandas"]),
         "detalle": "EII diff vs checkpoint = 0"},
    ]
    return rows


def _markdown(esc, rangos, checks) -> str:
    l = []
    l.append("# Peso sismico MODELO_FIEL_2: escenarios A y B por piso")
    l.append("")
    l.append("- Escenario A: W_A = PP_total + 0.50*Q (excluye PM.ADIC)")
    l.append("- Escenario B: W_B = PP_total + PM_ADIC + 0.50*Q (= G completa + 0.5Q)")
    l.append("")
    for ed, lbl in (("EI", "EDIFICIO I"), ("EII", "EDIFICIO II")):
        r = esc[ed]["resumen"]
        l.append("## %s" % lbl)
        l.append("- A: %.2f kN (%.2f Mg)   B: %.2f kN (%.2f Mg)"
                 % (r["W_A_kN"], r["masa_A_Mg"], r["W_B_kN"], r["masa_B_Mg"]))
        l.append("- Diferencia A-B: %.2f kN (PM.ADIC)" % r["diferencia_A_minus_B_kN"])
        l.append("- vs peso v1: B %.2f / A %.2f kN"
                 % (r["diferencia_B_minus_v1_kN"], r["diferencia_A_minus_v1_kN"]))
        l.append("- Rango por pendientes (A): [%.2f, %.2f] kN"
                 % tuple(rangos[ed]["escenario_A_kN"]))
        l.append("- Rango por pendientes (B): [%.2f, %.2f] kN"
                 % tuple(rangos[ed]["escenario_B_kN"]))
        l.append("  - pendientes cuantificadas: +%.2f kN (%s)"
                 % (rangos[ed]["pendientes_cuantificadas_kN"],
                    rangos[ed]["nota"]))
        l.append("")
        l.append("| nivel | z (m) | G (kN) | Q (kN) | W_A (kN) | W_B (kN) | "
                 "masa_A (Mg) | masa_B (Mg) | CM_A x/y (m) | CM_B x/y (m) |")
        l.append("|---|---|---|---|---|---|---|---|---|---|")
        for b in esc[ed]["bandas"]:
            l.append("| %s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | "
                     "%s / %s | %s / %s |"
                     % (b["nivel"], b["z_m"], b["G_aplicada_kN"], b["Q_total_kN"],
                        b["W_A_kN"], b["W_B_kN"], b["masa_A_Mg"], b["masa_B_Mg"],
                        b["CM_A_x_m"], b["CM_A_y_m"], b["CM_B_x_m"], b["CM_B_y_m"]))
        l.append("")
    if ed == "EI":
        pass
    l.append("## Verificaciones")
    l.append("")
    for c in checks:
        l.append("- [%s] %s: %s" % ("OK" if c["ok"] else "ERROR",
                                    c["check"], c["detalle"]))
    return "\n".join(l) + "\n"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    audit = json.loads(AUDIT_EI.read_text(encoding="utf-8"))
    marcos = {"EI": construir_marco_EI(),
              "EII": (lambda m: (m.construir(), m)[1])(MarcoEII(v031_seccion="V.60/80"))}
    esc = _bandas_esc(marcos, audit)
    rangos = _rangos(esc)
    checks = _verificaciones(esc)

    payload = {"caso": "peso_sismico_escenarios_A_B",
               "iteracion": "MODELO_FIEL_2",
               "q_Q_kN_m2": 2.0, "fraccion_Q": 0.5, "g_m_s2": GRAV,
               "escenario_A": "PP_total + 0.5*Q",
               "escenario_B": "PP_total + PM_ADIC + 0.5*Q",
               "EI": esc["EI"], "EII": esc["EII"],
               "rangos_por_pendientes": rangos,
               "referencia_peso_v1_kN": {"EI": WEB1, "EII": WEII1},
               "verificaciones": checks}
    (OUT / "peso_sismico_MODELO_FIEL_v2.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(OUT / "peso_sismico_MODELO_FIEL_v2.csv", "w", encoding="utf-8",
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
                            b["CM_A_x_m"], b["CM_A_y_m"], b["CM_B_x_m"], b["CM_B_y_m"]])
    (OUT / "peso_sismico_MODELO_FIEL_v2.md").write_text(
        _markdown(esc, rangos, checks), encoding="utf-8")

    print(json.dumps({
        "EI_scA_kN": esc["EI"]["resumen"]["W_A_kN"],
        "EI_scB_kN": esc["EI"]["resumen"]["W_B_kN"],
        "EII_scA_kN": esc["EII"]["resumen"]["W_A_kN"],
        "EII_scB_kN": esc["EII"]["resumen"]["W_B_kN"],
        "rango_EI_A_kN": rangos["EI"]["escenario_A_kN"],
        "rango_EI_B_kN": rangos["EI"]["escenario_B_kN"],
        "checks_ok": sum(1 for c in checks if c["ok"]),
        "checks_total": len(checks)},
        ensure_ascii=False, indent=2))
    return 0 if all(c["ok"] for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())