"""G_EI_MODELO_FIEL_v2 — caso G fiel del EI, iteracion MODELO_FIEL_2.

Reutiliza el modulo v1 `caso_G_EI_MODELO_FIEL` (mismo solver OpenSeesPy, misma
configuracion del marco). No cambia ningun numero de la solucion v1; anade el
reporte de MODELO_FIEL_2 con la separacion explicita de componentes:

  * PP_total          : losas PP + vigas + columnas + muros (+ otros = 0)
  * PM_ADIC           : aplicada (EI 10.244,14 kN, superficial on areas FE)
  * permanente aplicada : PP_total + PM_ADIC  (== G_despues de la v1)
  * pendientes        : tramos base, contencion, V.S.I., metalicos
  * reacciones / equilibrio vertical de la solucion v1
  * componentes no incluidos
  * nivel de fidelidad: REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES

Escribo en modelo_fiel/:
  G_EI_MODELO_FIEL_v2.json/.md

Uso:
  python -X utf8 -m src.modelo_fiel.caso_G_EI_MODELO_FIEL_v2
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
OUT_EI = E3 / "modelo_fiel" / "EI"
RES = E3 / "results"

PM_EI = OUT / "PM_ADIC_auditoria_EI_EII.json"
LEDGER = OUT / "ledger_PP_PMADIC_Q.json"

sys.path.insert(0, str(E3))

FIDELIDAD_EI = "REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # 1) regenerar el caso v1 (determinista) y leer su contrato
    import src.modelo_fiel.caso_G_EI_MODELO_FIEL as v1
    rc = v1.main()
    v1json = json.loads((OUT_EI / "G_EI_MODELO_FIEL.json").read_text(encoding="utf-8"))
    pm = json.loads(PM_EI.read_text(encoding="utf-8"))
    led = json.loads(LEDGER.read_text(encoding="utf-8"))

    ledger = v1json["ledger"]
    # v1 chequeos: 0 suma_pp_igual_audit, 1 identidad, 2 longitud, 3 cada_id,
    # 4 equilibrio_antes, 5 equilibrio_despues, 6 losas_y_pm_adic_intactas
    checks_ok = [c for c in ledger["verificaciones"] if c["estado"] == "OK"]
    Rz_despues = v1json["comparacion"]["solucion_despues"]["R_z_kN"]
    sol_d = v1json["solucion_despues"]
    Pz_despues = ledger["G_despues_kN"]

    pp_el = ledger["PP_por_nivel"]

    pp_losas = led["EI"]["totales"]["PP_losas_kN"]
    pp_el2 = led["EI"]["totales"]["PP_elementos_kN"]
    pm_adic = led["EI"]["totales"]["PM_ADIC_kN"]
    q = led["EI"]["totales"]["Q_total_kN"]
    pp_total = round(pp_losas + pp_el2, 4)

    pend = ledger["pendientes_explicitos"]
    componentes_no_incluidos = [
        {"componente": "tramos virtuales BASE->nivel",
         "estado": "PENDIENTE_HIPOTESIS_FE",
         "kn": {"columnas_base": pend["columnas_base_kN"],
                "muros_base": pend["muros_base_kN"]}},
        {"componente": "muros de contencion del sotano",
         "estado": "HIPOTESIS_CIMENTACION (no adoptados)",
         "kn": {"contencion": pend["contencion_kN"]}},
        {"componente": "V.S.I. 20/150 de CP1S",
         "estado": "PENDIENTE_SECCION (pp no cuantificado)", "kn": None},
        {"componente": "metalicos (V.M./P.M. y P.M.I.)",
         "estado": "PENDIENTE_TRAMO (seccion tubular confirmada)", "kn": None},
        {"componente": "desfase P4 +0.1813 m y cajas de ascensor de un plano",
         "estado": "PENDIENTE_TRAMO", "kn": None},
    ]

    payload = {
        "caso": "G", "edificio": "I", "iteracion": "MODELO_FIEL_2",
        "deriva_de": "G_EI_MODELO_FIEL (MODELO_FIEL_1)",
        "motor": "OpenSeesPy (mismo marco y configuracion)",
        "clasificacion_fidelidad": {
            "etiq": FIDELIDAD_EI,
            "razon": ("se reproduce el caso G (G checkpoint 25.227,73 + PP "
                      "elementos confirmados 17.179,23 = 42.406,96 kN aplicados "
                      "y en equilibrio), pero quedan componentes de PP por "
                      "cuantificar/confirmar (tramos base, contencion, V.S.I., "
                      "metalicos)")},
        "componentes": {
            "PP_losas_kN": pp_losas,
            "PP_vigas_columnas_muros_kN": pp_el2,
            "PP_otros_kN": 0.0,
            "PP_total_kN": pp_total,
            "PM_ADIC_kN": pm_adic,
            "permanente_aplicada_kN": round(pp_total + pm_adic, 4),
            "Q_sobrecarga_kN": q},
        "PM_ADIC": {
            "aplicada_kN": pm_adic,
            "modo": "superficial (kgf/m2 correlacionado) sobre area FE "
                    "(suma tributaria por losa = 10.244,139 kN)",
            "detalle": pm["EI"] if "EI" in pm else None},
        "pendientes_kN": {
            "columnas_base": pend["columnas_base_kN"],
            "muros_base": pend["muros_base_kN"],
            "contencion": pend["contencion_kN"],
            "quantificados_total_kN": round(pend["columnas_base_kN"]
                                            + pend["muros_base_kN"]
                                            + pend["contencion_kN"], 4)},
        "componentes_no_incluidos": componentes_no_incluidos,
        "solucion": {
            "P_z_kN": Pz_despues,
            "R_z_kN": Rz_despues,
            "residuo_kN": round(Rz_despues - Pz_despues, 6),
            "equilibrio_vertical": "OK" if abs(Rz_despues - Pz_despues) < 1.0
            else "ERROR",
            "max_desp_z_m": v1json["comparacion"]["solucion_despues"]["max_desp_z_m"],
            "n_reacciones": sol_d.get("n_reacciones"),
            "reacciones_csv": str(OUT_EI / "G_EI_MODELO_FIEL_reacciones.csv")},
        "verificaciones_v1": {c["check"]: c["estado"] for c in ledger["verificaciones"]},
        "checks_ok": len(checks_ok), "checks_total": len(ledger["verificaciones"]),
    }

    (OUT / "G_EI_MODELO_FIEL_v2.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(OUT / "G_EI_MODELO_FIEL_v2.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["componente", "kN"])
        for k in ("PP_losas_kN", "PP_vigas_columnas_muros_kN", "PP_otros_kN",
                  "PP_total_kN", "PM_ADIC_kN", "permanente_aplicada_kN"):
            w.writerow([k, payload["componentes"][k]])
        w.writerow(["Q_sobrecarga_kN", payload["componentes"]["Q_sobrecarga_kN"]])

    l = []
    l.append("# G_EI_MODELO_FIEL_v2 (MODELO_FIEL_2)")
    l.append("")
    l.append("Clasificacion: **%s**" % FIDELIDAD_EI)
    l.append("")
    l.append("- PP_losas: %.4f kN" % pp_losas)
    l.append("- PP vigas+columnas+muros: %.4f kN" % pp_el2)
    l.append("- PP_total: **%.4f kN**" % pp_total)
    l.append("- PM.ADIC aplicada: **%.4f kN** (superficial, areas FE)" % pm_adic)
    l.append("- Permanente aplicada (G_despues): **%.2f kN**"
             % payload["componentes"]["permanente_aplicada_kN"])
    l.append("- Q: %.4f kN" % q)
    l.append("")
    l.append("## Solucion")
    l.append("")
    l.append("- P_z = %.4f kN ; R_z = %.4f kN ; residuo = %.6f kN ; %s"
             % (Pz_despues, Rz_despues, payload["solucion"]["residuo_kN"],
                payload["solucion"]["equilibrio_vertical"]))
    l.append("")
    l.append("## Pendientes / no incluidos")
    l.append("")
    for c in componentes_no_incluidos:
        kn = json.dumps(c["kn"]) if c["kn"] else "-"
        l.append("- %s [%s]: %s" % (c["componente"], c["estado"], kn))
    l.append("- Total pendientes cuantificados: %.2f kN"
             % payload["pendientes_kN"]["quantificados_total_kN"])
    l.append("")
    l.append("Verificaciones v1: %d/%d OK" % (payload["checks_ok"],
                                              payload["checks_total"]))
    (OUT / "G_EI_MODELO_FIEL_v2.md").write_text("\n".join(l) + "\n", encoding="utf-8")

    print(json.dumps({"edificio": "I", "perfil": "G_EI_MODELO_FIEL_v2",
                      "permanente_aplicada_kN": payload["componentes"]["permanente_aplicada_kN"],
                      "PP_total_kN": pp_total, "PM_ADIC_kN": pm_adic,
                      "R_z_kN": Rz_despues, "P_z_kN": Pz_despues,
                      "clasificacion": FIDELIDAD_EI,
                      "checks_v1_ok": payload["checks_ok"],
                      "checks_v1_total": payload["checks_total"]},
                     ensure_ascii=False, indent=2))
    return 0 if (payload["checks_ok"] == payload["checks_total"]
                 and payload["solucion"]["equilibrio_vertical"] == "OK"
                 and rc == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())