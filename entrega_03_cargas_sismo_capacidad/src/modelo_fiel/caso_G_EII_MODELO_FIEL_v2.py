"""G_EII_MODELO_FIEL_v2 — caso G fiel del EII, iteracion MODELO_FIEL_2.

SIN re-solve: reutiliza exactamente los numeros del pipeline reproducible
V.60/80 (25.970,999 kN) y el contrato de la iteracion v1. Anade el reporte de
MODELO_FIEL_2 con la separacion explicita de componentes:

  * PP_total          : losas aplicadas 9.670,75 + elementos 16.300,25
  * PM_ADIC           : 0 aplicada (catálogo A-F lineal, todo PM_ADIC_PENDIENTE)
  * permanente aplicada : 25.970,999 kN (== reproducible)
  * pendientes        : muros 3.328,79 + losas 6,27 + ruteo 417,85 + V_031 +
                        rigidLinks franja D-D'
  * reacciones / equilibrio del artefacto reproducible del checkpoint
  * componentes no incluidos
  * nivel de fidelidad: REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES

Escribo en modelo_fiel/:
  G_EII_MODELO_FIEL_v2.json/.md

Uso:
  python -X utf8 -m src.modelo_fiel.caso_G_EII_MODELO_FIEL_v2
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
OUT_EII = E3 / "modelo_fiel" / "EII"
RES = E3 / "results"
REPRO = RES / "cargas" / "caso_G_EII_reproducible.json"
PM = OUT / "PM_ADIC_auditoria_EI_EII.json"
LEDGER = OUT / "ledger_PP_PMADIC_Q.json"

FIDELIDAD_EII = "REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    v1 = json.loads((OUT_EII / "G_EII_MODELO_FIEL.json").read_text(encoding="utf-8"))
    repro = json.loads(REPRO.read_text(encoding="utf-8"))
    pm = json.loads(PM.read_text(encoding="utf-8"))
    led = json.loads(LEDGER.read_text(encoding="utf-8"))

    ledger = v1["ledger"]
    solres = v1["solucion_resumen"]
    Rz = solres["R_z_kN"]
    Pz = ledger["G_confirmado_kN"]
    checks_ok = [c for c in ledger.get("verificaciones", []) if c["estado"] == "OK"]

    # equilibrio/identidad del artefacto reproducible del checkpoint
    ck_verif = repro.get("verificaciones", {})
    ck_equil = None
    if isinstance(ck_verif, dict):
        for k, v in ck_verif.items():
            if isinstance(v, dict) and "R_z" in str(v) or isinstance(v, dict) and "residuo" in str(v):
                ck_equil = v
                break

    pp_losas = led["EII"]["totales"]["PP_losas_kN"]
    pp_el = led["EII"]["totales"]["PP_elementos_kN"]
    pm_adic = led["EII"]["totales"]["PM_ADIC_kN"]
    q = led["EII"]["totales"]["Q_total_kN"]

    componentes_no_incluidos = [
        {"componente": "PM.ADIC (catálogo A-F del plano 2024_22-700)",
         "estado": "PM_ADIC_PENDIENTE",
         "detalle": "lineal Kg/m A=260 B=260 C=200 D=1500 E=260 F=260; sin "
                    "mapeo familia->viga (DXF no incluido en la copia) -> "
                    "aplicada = 0"},
        {"componente": "muros (publicado vs pipeline)",
         "estado": "PENDIENTE_ORIGEN_PIPELINE",
         "kn": 3328.79,
         "detalle": "publicado 6521.26 vs pipeline A=t*(L/2) por montante "
                    "3192.47; identidad A=t*L por panel 4330.02"},
        {"componente": "losas (publicado vs aplicada)", "estado": "PENDIENTE",
         "kn": 6.27},
        {"componente": "ruteo sin camino estructural",
         "estado": "PENDIENTE (14 cargas, no transferidas)", "kn": 417.85},
        {"componente": "V_031 seccion alternativa", "estado": "HIPOTESIS_MODELO",
         "kn": None},
        {"componente": "rigidLinks franja D-D'", "estado": "HIPOTESIS (documentada)",
         "kn": None},
    ]

    payload = {
        "caso": "G", "edificio": "II", "iteracion": "MODELO_FIEL_2",
        "deriva_de": "G_EII_MODELO_FIEL (MODELO_FIEL_1) + "
                     "caso_G_EII_reproducible.json (checkpoint)",
        "motor": "OpenSeesPy (pipeline reproducible EII, mismo que checkpoint)",
        "v031_seccion_escenario": "V.60/80",
        "clasificacion_fidelidad": {
            "etiq": FIDELIDAD_EII,
            "razon": ("se reproduce el caso G (25.970,999 kN, artefacto del "
                      "checkpoint) sin re-resolver, pero con hipotesis de modelo "
                      "documentadas (V_031, rigidLinks franja D-D', muros "
                      "A=t*(L/2)) y cargas pendientes (PM.ADIC catálogo A-F sin "
                      "mapeo, losas +6,27, ruteo 417,85)")},
        "componentes": {
            "PP_losas_kN": round(pp_losas, 4),
            "PP_vigas_kN": ledger["G_por_componente_confirmado_kN"]["vigas_incl_V031"],
            "PP_columnas_kN": ledger["G_por_componente_confirmado_kN"]["columnas"],
            "PP_muros_kN": ledger["G_por_componente_confirmado_kN"]["muros_pipeline_directo"],
            "PP_otros_kN": 0.0,
            "PP_total_kN": round(pp_losas + pp_el, 4),
            "PM_ADIC_kN": 0.0,
            "permanente_aplicada_kN": round(Pz, 4),
            "Q_sobrecarga_kN": round(q, 4)},
        "PM_ADIC": {
            "aplicada_kN": 0.0,
            "modo": "catálogo lineal Kg/m (plano 700); conversion x g=0.00980665 "
                    "-> kN/m; sin mapeo familia->viga (applied=0)",
            "detalle": pm.get("EII") if "EII" in pm else None},
        "pendientes_kN": {
            "muros": 3328.79, "losas": 6.27, "ruteo": 417.85,
            "quantificados_total_kN": round(3328.79 + 6.27 + 417.85, 4),
            "no_cuantificados": ["V_031 (alternativa)", "rigidLinks franja D-D'"]},
        "componentes_no_incluidos": componentes_no_incluidos,
        "solucion": {
            "P_z_kN": round(Pz, 4),
            "R_z_kN": Rz,
            "residuo_kN": round(Rz - Pz, 6),
            "equilibrio_vertical": "OK" if abs(Rz - Pz) <= 1e-6 else "ERROR",
            "max_desp_z_m": solres["max_desp_z_m"],
            "n_reacciones": solres.get("n_reacciones"),
            "n_esfuerzos": None,
            "checkpoint_verificacion_equilibrio": ck_equil},
        "verificaciones_v1": {c["check"]: c["estado"]
                              for c in ledger.get("verificaciones", [])},
        "checks_ok": len(checks_ok), "checks_total": len(ledger.get("verificaciones", [])),
    }

    (OUT / "G_EII_MODELO_FIEL_v2.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    l = []
    l.append("# G_EII_MODELO_FIEL_v2 (MODELO_FIEL_2)")
    l.append("")
    l.append("Clasificacion: **%s**" % FIDELIDAD_EII)
    l.append("")
    l.append("Sin re-solve: reutiliza el pipeline reproducible V.60/80 = "
             "**%.3f kN**." % Pz)
    l.append("")
    l.append("- PP_losas: %.4f kN" % pp_losas)
    l.append("- PP columnas: %.4f kN" % payload["componentes"]["PP_columnas_kN"])
    l.append("- PP vigas (incl. V_031): %.4f kN" % payload["componentes"]["PP_vigas_kN"])
    l.append("- PP muros (pipeline): %.4f kN" % payload["componentes"]["PP_muros_kN"])
    l.append("- PP_total: **%.4f kN**" % payload["componentes"]["PP_total_kN"])
    l.append("- PM.ADIC aplicada: **0.00 kN** (catálogo A-F, todo PM_ADIC_PENDIENTE)")
    l.append("- Permanente aplicada: **%.2f kN** = reproducible" % Pz)
    l.append("- Q: %.4f kN" % q)
    l.append("")
    l.append("## Solucion (artefacto checkpoint)")
    l.append("")
    l.append("- P_z = %.4f kN ; R_z = %.4f kN ; residuo = %.6f kN ; %s"
             % (Pz, Rz, payload["solucion"]["residuo_kN"],
                payload["solucion"]["equilibrio_vertical"]))
    l.append("")
    l.append("## Pendientes / no incluidos")
    l.append("")
    for c in componentes_no_incluidos:
        kn = "%.2f" % c["kn"] if c.get("kn") else "-"
        l.append("- %s [%s]: %s kN | %s"
                 % (c["componente"], c["estado"], kn, c.get("detalle", "")))
    l.append("")
    l.append("Total pendientes cuantificados: %.2f kN"
             % payload["pendientes_kN"]["quantificados_total_kN"])
    l.append("")
    l.append("Verificaciones v1: %d/%d OK" % (payload["checks_ok"],
                                              payload["checks_total"]))
    (OUT / "G_EII_MODELO_FIEL_v2.md").write_text("\n".join(l) + "\n", encoding="utf-8")

    print(json.dumps({"edificio": "II", "perfil": "G_EII_MODELO_FIEL_v2",
                      "permanente_aplicada_kN": payload["componentes"]["permanente_aplicada_kN"],
                      "PP_total_kN": payload["componentes"]["PP_total_kN"],
                      "PM_ADIC_kN": 0.0, "R_z_kN": Rz, "P_z_kN": round(Pz, 4),
                      "clasificacion": FIDELIDAD_EII,
                      "checks_v1_ok": payload["checks_ok"],
                      "checks_v1_total": payload["checks_total"]},
                     ensure_ascii=False, indent=2))
    return 0 if (payload["checks_ok"] == payload["checks_total"]
                 and payload["solucion"]["equilibrio_vertical"] == "OK") else 1


if __name__ == "__main__":
    raise SystemExit(main())