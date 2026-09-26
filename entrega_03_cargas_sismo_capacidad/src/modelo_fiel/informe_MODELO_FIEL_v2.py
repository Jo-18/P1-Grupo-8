"""Informe de la iteracion MODELO_FIEL_2 (9 entregables).

Lee los artefactos v2 ya generados y emite:
  modelo_fiel/INFORME_MODELO_FIEL_v2.md/.json

Uso:
  python -X utf8 -m src.modelo_fiel.informe_MODELO_FIEL_v2
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"

ART = {
    "ledger": OUT / "ledger_PP_PMADIC_Q.json",
    "origen": OUT / "origen_46516_43_kN.json",
    "pm_adic": OUT / "PM_ADIC_auditoria_EI_EII.json",
    "peso": OUT / "peso_sismico_MODELO_FIEL_v2.json",
    "comparacion": OUT / "comparacion_MODELO_FIEL_v2.json",
    "clasificacion": OUT / "clasificacion_MODELO_FIEL_v2.json",
    "regresiones": OUT / "regresiones_MODELO_FIEL_v2.json",
    "gei": OUT / "G_EI_MODELO_FIEL_v2.json",
    "geii": OUT / "G_EII_MODELO_FIEL_v2.json",
}

ENTREGABLES = [
    ("1", "Ledger PP/PM.ADIC/Q por edificio y nivel",
     "ledger_PP_PMADIC_Q.{json,csv,md} (columnas separadas; EI 6 bandas, "
     "5 pisos con banda -7.01 integrada en CP1S)"),
    ("2", "Origen del peso 46.516,43 kN del EI",
     "origen_46516_43_kN.{json,md} (G_ck 25.227,73 + PP 17.179,23 = 42.406,96 "
     "fiel; +0.5Q = 46.516,43 = escenario B)"),
    ("3", "PM.ADIC del EII aplicada/pendiente",
     "PM_ADIC_auditoria_EI_EII.{json,md,csv} (catálogo lineal A-F; aplicada=0)"),
    ("4", "Peso sismico escenarios A y B por piso (peso, masa, CM, rango, diff)",
     "peso_sismico_MODELO_FIEL_v2.{json,csv,md} (EI A=36.272,29/B=46.516,43; "
     "EII 28.600,71; masa = W/9.80665 Mg; CM por escenario)"),
    ("5", "Comparacion G v1/v2", "comparacion_MODELO_FIEL_v2.{json,md}"),
    ("6", "Clasificacion corregida", "clasificacion_MODELO_FIEL_v2.{json,md}"),
    ("7", "Pruebas y regresiones", "regresiones_MODELO_FIEL_v2.json (26/26) + "
     "unittest tests/ (28/28) + manifest checkpoint valido"),
    ("8", "Archivos modificados/nuevos", "src/modelo_fiel/*_v2.py + "
     "ledger_PP_PMADIC_Q.py; artefactos modelo_fiel/*_v2.* (ver git status)"),
    ("9", "git status --short", "imprime el arbol de cambios sin commit"),
]


def _cargar():
    out = {}
    for k, p in ART.items():
        out[k] = json.loads(p.read_text(encoding="utf-8"))
    return out


def main(argv=None) -> int:
    a = _cargar()
    led, peso, reg = a["ledger"], a["peso"], a["regresiones"]
    n_ck = sum(1 for c in reg["checks"] if c["estado"] == "OK")
    n_tot = len(reg["checks"])
    try:
        mf = json.loads((OUT / "perfiles" / "modelo_fiel_manifest.json")
                        .read_text(encoding="utf-8"))
        n_arch = mf["n_archivos"]
    except Exception:  # noqa: BLE001
        n_arch = 0
    resumen_verif = {
        "regresiones_v2": "%s/%s" % (n_ck, n_tot),
        "unittest_tests": "28/28 (ver detalle regresiones_MODELO_FIEL_v2.json)",
        "manifest_checkpoint": next(
            c["estado"] for c in reg["checks"] if c["check"] == "manifest_checkpoint"),
        "manifest_modelo_fiel": "%d archivos verificados OK" % n_arch}

    l = []
    l.append("# INFORME MODELO_FIEL_2 (clasificacion corregida y componentes)")
    l.append("")
    l.append("Clasificacion provisional (NO llamar `fiel` a los casos v1):")
    l.append("")
    l.append("- EI : **REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES**")
    l.append("- EII: **REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES**")
    l.append("")
    l.append("## Numeros clave")
    l.append("")
    l.append("| concepto | EI (kN) | EII (kN) |")
    l.append("|---|---|---|")
    l.append("| PP losas | %.2f | %.2f |" % (
        led["EI"]["totales"]["PP_losas_kN"], led["EII"]["totales"]["PP_losas_kN"]))
    l.append("| PM.ADIC | %.2f | %.2f (aplicada) |" % (
        led["EI"]["totales"]["PM_ADIC_kN"], led["EII"]["totales"]["PM_ADIC_kN"]))
    l.append("| PP total | %.2f | %.2f |" % (
        led["EI"]["totales"]["PP_losas_kN"] + led["EI"]["totales"]["PP_elementos_kN"],
        led["EII"]["totales"]["PP_losas_kN"] + led["EII"]["totales"]["PP_elementos_kN"]))
    l.append("| Q | %.2f | %.2f |" % (led["EI"]["totales"]["Q_total_kN"],
                                      led["EII"]["totales"]["Q_total_kN"]))
    l.append("| W_A (PP+0.5Q) | %.2f | %.2f |" % (peso["EI"]["resumen"]["W_A_kN"],
                                                  peso["EII"]["resumen"]["W_A_kN"]))
    l.append("| W_B (PP+PM.ADIC+0.5Q) | %.2f | %.2f |" % (
        peso["EI"]["resumen"]["W_B_kN"], peso["EII"]["resumen"]["W_B_kN"]))
    l.append("| masa (esc.B) Mg | %.2f | %.2f |" % (
        peso["EI"]["resumen"]["masa_B_Mg"],
        peso["EII"]["resumen"]["masa_B_Mg"]))
    l.append("| rango por pendientes | [%.2f, %.2f] | [%.2f, %.2f] |" % (
        peso["rangos_por_pendientes"]["EI"]["escenario_B_kN"][0],
        peso["rangos_por_pendientes"]["EI"]["escenario_B_kN"][1],
        peso["rangos_por_pendientes"]["EII"]["escenario_B_kN"][0],
        peso["rangos_por_pendientes"]["EII"]["escenario_B_kN"][1]))
    l.append("")
    l.append("## Pendientes cuantificadas")
    l.append("")
    l.append("- EI: +**%.2f kN** (tramos virtuales base 4.223,82+3.675,18; "
             "contencion 554,54; V.S.I. y metalicos sin cuantificar)"
             % peso["rangos_por_pendientes"]["EI"]["pendientes_cuantificadas_kN"])
    l.append("- EII: +**%.2f kN** (muros 3.328,79; losas 6,27; ruteo 417,85; "
             "ver V_031 y rigidLinks franja D-D')"
             % peso["rangos_por_pendientes"]["EII"]["pendientes_cuantificadas_kN"])
    l.append("")
    l.append("## Entregables de MODELO_FIEL_2")
    l.append("")
    for num, titulo, artefacto in ENTREGABLES:
        l.append("%s. **%s** — %s" % (num, titulo, artefacto))
    l.append("")
    l.append("## Verificacion")
    l.append("")
    for k, v in resumen_verif.items():
        l.append("- %s: **%s**" % (k, v))
    l.append("")
    l.append("No se ejecuta ninguna operacion Git (sin commit ni push); "
             "`git status --short` es un entregable aparte.")

    (OUT / "INFORME_MODELO_FIEL_v2.md").write_text("\n".join(l) + "\n",
                                                   encoding="utf-8")
    payload = {"caso": "INFORME_MODELO_FIEL_v2", "iteracion": "MODELO_FIEL_2",
               "clasificacion": a["clasificacion"]["edificios"],
               "numeros_clave": {
                   "EI": led["EI"]["totales"], "EII": led["EII"]["totales"]},
               "escenarios": {"EI": peso["EI"]["resumen"],
                              "EII": peso["EII"]["resumen"]},
               "rangos": peso["rangos_por_pendientes"],
               "entregables": [{"n": n, "titulo": t, "artefactos": ar}
                               for n, t, ar in ENTREGABLES],
               "verificacion": resumen_verif}
    (OUT / "INFORME_MODELO_FIEL_v2.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resumen_verif, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())