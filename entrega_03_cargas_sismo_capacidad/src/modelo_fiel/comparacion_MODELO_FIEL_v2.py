"""Comparacion G v1/v2 (MODELO_FIEL_1 -> MODELO_FIEL_2) + clasificacion corregida.

Entregables 5 y 6 de MODELO_FIEL_2:
  5) comparacion del caso G y del peso sismico entre la iteracion v1 y la v2.
  6) clasificacion corregida de fidelidad (los casos v1 NO se llaman "fieles"):

     EI : REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES
     EII: REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES

La numeracion v1 ("MODELO_FIEL") se mantiene en los artefactos historicos de
las iteraciones 1, pero en la v2 la nomenclatura oficial de la clasificacion es
la provisional citada (ver INFORME_MODELO_FIEL_v2.md).

Lee: ledger_PP_PMADIC_Q.json, peso_sismico_MODELO_FIEL.json (v1) y _v2,
G_EI_MODELO_FIEL_v2.json, G_EII_MODELO_FIEL_v2.json.
Salidas en modelo_fiel/:
  comparacion_MODELO_FIEL_v2.json/.md
  clasificacion_MODELO_FIEL_v2.json/.md
Uso:
  python -X utf8 -m src.modelo_fiel.comparacion_MODELO_FIEL_v2
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"

LED = OUT / "ledger_PP_PMADIC_Q.json"
PESO1 = OUT / "peso_sismico_MODELO_FIEL.json"
PESO2 = OUT / "peso_sismico_MODELO_FIEL_v2.json"
GEI2 = OUT / "G_EI_MODELO_FIEL_v2.json"
GEII2 = OUT / "G_EII_MODELO_FIEL_v2.json"

CLAS = {
    "EI": "REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES",
    "EII": "REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES",
}

CLAS_RANGO = {
    "0_BLOQUEADO": "datos incompletos o con conflicto sin resolver",
    "1_REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES":
        "el caso se reproduce y esta en equilibrio; el recorte de componentes "
        "de PP (losas entrega, metalicos, V.S.I., muros de contencion, tramos "
        "base) puede subir el peso, manteniendo identidad de cargas",
    "2_REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES":
        "el caso se reproduce con hipotesis de modelo documentadas (secciones, "
        "rigidLinks, convencion de muros) y con cargas pendientes (PM.ADIC "
        "catalogada sin mapeo, losas/ruteo) que pueden cambiar el peso",
    "3_FIEL":
        "no usar hasta resolver PP y PM.ADIC y cerrar las hipotesis; los "
        "artefactos 'MODELO_FIEL_1' NO son fieles",
}


def _tabla_ei() -> list:
    led = json.loads(LED.read_text(encoding="utf-8"))["EI"]
    p1 = json.loads(PESO1.read_text(encoding="utf-8"))
    p2 = json.loads(PESO2.read_text(encoding="utf-8"))
    g2 = json.loads(GEI2.read_text(encoding="utf-8"))
    w1 = p1["EI"]["W_total_kN"]
    wA, wB = p2["EI"]["resumen"]["W_A_kN"], p2["EI"]["resumen"]["W_B_kN"]
    filas = [
        {"concepto": "G antes (checkpoint: PP_losas + PM.ADIC) kN",
         "v1": 25227.7316, "v2": round(g2["componentes"]["PP_losas_kN"]
                                        + g2["componentes"]["PM_ADIC_kN"], 4),
         "nota": "sin cambios (identidad preservada)"},
        {"concepto": "PP elementos confirmados (vigas+col+muros) kN",
         "v1": 17179.2261, "v2": g2["componentes"]["PP_vigas_columnas_muros_kN"],
         "nota": "sin cambios"},
        {"concepto": "G despues (permanente aplicada) kN",
         "v1": 42406.9577, "v2": g2["componentes"]["permanente_aplicada_kN"],
         "nota": "PP_total + PM.ADIC"},
        {"concepto": "PM.ADIC aplicada kN",
         "v1": "incluida en G (no separada)", "v2": g2["componentes"]["PM_ADIC_kN"],
         "nota": "NUEVO: separada del PP (10.244,14 superficial)"},
        {"concepto": "PP_total (sin PM.ADIC) kN",
         "v1": "no reportado", "v2": g2["componentes"]["PP_total_kN"],
         "nota": "NUEVO: 14.983,59 losas + 17.179,23 elementos"},
        {"concepto": "Peso sismico total kN (v1 = 46.516,43)",
         "v1": round(w1, 4), "v2": "%s (A) / %s (B)" % (round(wA, 4), round(wB, 4)),
         "nota": "el 46.516,43 v1 == escenario B (PP_total+PM.ADIC+0.5Q)"},
        {"concepto": "Diferencia A-B kN",
         "v1": "-", "v2": round(p2["EI"]["resumen"]["diferencia_A_minus_B_kN"], 4),
         "nota": "= PM.ADIC 10.244,15"},
    ]
    return filas


def _tabla_eii() -> list:
    p1 = json.loads(PESO1.read_text(encoding="utf-8"))
    p2 = json.loads(PESO2.read_text(encoding="utf-8"))
    g2 = json.loads(GEII2.read_text(encoding="utf-8"))
    w1 = p1["EII"]["W_total_kN"]
    wA, wB = p2["EII"]["resumen"]["W_A_kN"], p2["EII"]["resumen"]["W_B_kN"]
    return [
        {"concepto": "G confirmado (reproducible) kN",
         "v1": 25970.9994, "v2": g2["componentes"]["permanente_aplicada_kN"],
         "nota": "sin cambios; sin re-solve"},
        {"concepto": "PP_total kN", "v1": "no separado",
         "v2": g2["componentes"]["PP_total_kN"],
         "nota": "losas 9.670,75 + elementos 16.300,25"},
        {"concepto": "PM.ADIC aplicada kN", "v1": "0 (no incluida)",
         "v2": g2["componentes"]["PM_ADIC_kN"],
         "nota": "catálogo A-F completo, todo PM_ADIC_PENDIENTE"},
        {"concepto": "Peso sismico total kN",
         "v1": round(w1, 4), "v2": "%s (A) == %s (B)" % (round(wA, 4), round(wB, 4)),
         "nota": "A == B por PM.ADIC=0"},
        {"concepto": "Pendientes cuantificados kN",
         "v1": "3.752,91", "v2": g2["pendientes_kN"]["quantificados_total_kN"],
         "nota": "muros 3.328,79 + losas 6,27 + ruteo 417,85"},
    ]


def _clasificacion_payload() -> dict:
    led = json.loads(LED.read_text(encoding="utf-8"))
    return {
        "criterio_rango": CLAS_RANGO,
        "edificios": {
            "EI": {
                "clasificacion_v2": CLAS["EI"],
                "clasificacion_v1": "MODELO_FIEL_1 (se llamo 'fiel' en v1; "
                                    "denominacion RETIRADA en v2)",
                "por_que_no_es_fiel": [
                    "PM.ADIC separada del PP solo en v2 (interpretacion de "
                    "'peso propio' pendiente de confirmacion)",
                    "tramos virtuales BASE->nivel (4.223,82 col + 3.675,18 muro)",
                    "muros de contencion del sotano (554,54 kN, hipotesis)",
                    "V.S.I. 20/150 y metalicos: PP no cuantificado"],
                "referencia": "ledger_PP_PMADIC_Q + G_EI_MODELO_FIEL_v2"},
            "EII": {
                "clasificacion_v2": CLAS["EII"],
                "clasificacion_v1": "MODELO_FIEL_1 (se llamo 'fiel' en v1; "
                                    "denominacion RETIRADA en v2)",
                "por_que_no_es_fiel": [
                    "PM.ADIC catálogo A-F (lineal Kg/m) sin mapeo familia->viga "
                    "(aplicada = 0)",
                    "muros: identidad A=t*(L/2) vs publicado (3.328,79 kN)",
                    "losas publicadas vs aplicadas (+6,27 kN)",
                    "ruteo sin camino estructural (417,85 kN, 14 cargas)",
                    "V_031 (seccion alternativa) y rigidLinks franja D-D' "
                    "(hipotesis documentadas)"],
                "referencia": "ledger_PP_PMADIC_Q + G_EII_MODELO_FIEL_v2"},
        }}


def _markdown(ei, eii, clas) -> str:
    l = []
    l.append("# Comparacion G v1/v2 y clasificacion corregida (MODELO_FIEL_2)")
    l.append("")
    l.append("## EI")
    l.append("| concepto | v1 | v2 | nota |")
    l.append("|---|---|---|---|")
    for r in ei:
        l.append("| %s | %s | %s | %s |" % (r["concepto"], r["v1"], r["v2"],
                                            r["nota"]))
    l.append("")
    l.append("## EII")
    l.append("| concepto | v1 | v2 | nota |")
    l.append("|---|---|---|---|")
    for r in eii:
        l.append("| %s | %s | %s | %s |" % (r["concepto"], r["v1"], r["v2"],
                                            r["nota"]))
    l.append("")
    l.append("## Clasificacion corregida")
    l.append("")
    for ed, c in clas["edificios"].items():
        l.append("### %s -> **%s**" % (ed, c["clasificacion_v2"]))
        l.append("")
        l.append("- v1: %s" % c["clasificacion_v1"])
        l.append("- Motivos:")
        for m in c["por_que_no_es_fiel"]:
            l.append("  - %s" % m)
        l.append("")
    l.append("## Rango de clasificacion")
    l.append("")
    for k, v in clas["criterio_rango"].items():
        l.append("- %s: %s" % (k, v))
    return "\n".join(l) + "\n"


def main(argv=None) -> int:
    ei = _tabla_ei()
    eii = _tabla_eii()
    clas = _clasificacion_payload()
    payload = {"caso": "comparacion_y_clasificacion", "iteracion": "MODELO_FIEL_2",
               "EI": ei, "EII": eii, "clasificacion": clas}
    (OUT / "comparacion_MODELO_FIEL_v2.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "comparacion_MODELO_FIEL_v2.md").write_text(
        _markdown(ei, eii, clas), encoding="utf-8")
    (OUT / "clasificacion_MODELO_FIEL_v2.json").write_text(
        json.dumps(clas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    l = ["# Clasificacion de fidelidad MODELO_FIEL_2 (corregida)", ""]
    for ed, c in clas["edificios"].items():
        l.append("- **%s**: %s" % (ed, c["clasificacion_v2"]))
    l.append("")
    l.append("Denominacion v1 ('fiel') RETIRADA; los casos v1 quedan como "
             "artefactos historicos.")
    (OUT / "clasificacion_MODELO_FIEL_v2.md").write_text("\n".join(l) + "\n",
                                                         encoding="utf-8")
    print(json.dumps({"iteracion": "MODELO_FIEL_2",
                      "clasificacion": {k: v for k, v in CLAS.items()},
                      "escrito": ["comparacion_MODELO_FIEL_v2.json",
                                  "clasificacion_MODELO_FIEL_v2.json"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())