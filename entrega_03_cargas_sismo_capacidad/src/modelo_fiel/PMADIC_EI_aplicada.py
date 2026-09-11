"""PMADIC_EI_aplicada — tabla por losa del PM.ADIC SUPERFICIAL aplicado del EI
(iteracion MODELO_FIEL_3, tarea 6).

Cruce read-only de `modelo_fiel/PM_ADIC_auditoria_EI_EII.json`
(EDIFICIO_I.por_losa con 99 losas y por_nivel) para producir la tabla:

  fuente | nivel | losa | superficie FE (m2) | intensidad (kgf/m2) |
  intensidad (kN/m2) | receptor (losa FE / tributaria) | carga (kN) |
  control de doble conteo (PM.ADIC vs PP de losa)

Reglas:
  * PM.ADIC es CARGA PERMANENTE ADICIONAL (pavimento/acabados/uso, pagina 11
    de correlacion), SEPARADA del PP de la losa (no se suma al PP estructural).
  * La intensidad del manual es kgf/m2 (pag. 11); se convierte con
    g = 9.80665 m/s2 -> kN/m2 (mismo valor si se leyera como masa).
  * Receptor real: losas FE / areas tributarias (suma por losa = 10.244,139 kN).
  * No doble conteo: PP_losa y PM.ADIC son conceptos distintos y verificados
    por separado en la auditoria.

Escribo en modelo_fiel/:
  PMADIC_EI_aplicada.json / .md / .csv

Uso:
  python -X utf8 -m src.modelo_fiel.PMADIC_EI_aplicada
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
AUD = OUT / "PM_ADIC_auditoria_EI_EII.json"

G = 9.80665


def leer_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    aud = leer_json(AUD)
    ei = aud["EDIFICIO_I"]

    filas = []
    for it in ei["por_losa"]:
        filas.append({
            "fuente": ei["fuente"],
            "nivel": it["nivel"],
            "losa_id": it["losa_id"],
            "area_neta_fe_m2": it["area_neta_fe_m2"],
            "area_neta_correlacion_m2": it["area_neta_correlacion_m2"],
            "intensidad_kgf_m2": it["pm_kgf_m2"],
            "intensidad_kN_m2": it["pm_kn_m2"],
            "receptor": "losa FE / tributaria",
            "pm_adic_aplicada_kN": it["pm_adic_kn"],
            "pp_losa_kN": it["pp_losa_kn"],
            "espesor_losa_m": it["espesor_m"],
            "control_no_doble_conteo": ("PP de losa y PM.ADIC separados "
                                        "(pp_losa_kN vs pm_adic_kn)")})

    por_nivel = {k: v["pm_adic_kn"] for k, v in ei["por_nivel"].items()}
    total = ei["total_pm_adic_kn"]
    checks = {c["check"]: c for c in aud["verificaciones"]}
    v = checks.get("pm_adic_ei_total", {})
    delta = v.get("detalle", {}).get("delta_kN")

    payload = {
        "iteracion": "MODELO_FIEL_3", "tarea": "6_PMADIC_EI_aplicada",
        "tipo": ei["tipo"], "fuente": ei["fuente"],
        "gravedad_m_s2": G,
        "conversion_nota": ("intensidad del manual en kgf/m2 (pag. 11); "
                            "kN/m2 = kgf/m2 * g/1000 (mismo valor si masa)"),
        "por_nivel_kN": por_nivel,
        "total_aplicada_kN": total,
        "n_losas": len(filas),
        "verificacion_referencia": v.get("detalle"),
        "delta_referencia_kN": delta,
        "no_doble_conteo": ei["no_doble_conteo"],
        "tabla": filas}

    (OUT / "PMADIC_EI_aplicada.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cols = ["fuente", "nivel", "losa_id", "area_neta_fe_m2",
            "area_neta_correlacion_m2", "intensidad_kgf_m2",
            "intensidad_kN_m2", "receptor", "pm_adic_aplicada_kN",
            "pp_losa_kN", "espesor_losa_m", "control_no_doble_conteo"]
    with open(OUT / "PMADIC_EI_aplicada.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in filas:
            w.writerow([r[c] for c in cols])

    l = []
    l.append("# PMADIC_EI_aplicada (MODELO_FIEL_3 / tarea 6)")
    l.append("")
    l.append("Tipo: %s ; fuente: %s" % (ei["tipo"], ei["fuente"]))
    l.append("")
    l.append("Total aplicada al FE: **%.4f kN** (99 losas)" % total)
    l.append("")
    l.append("| nivel | PM.ADIC (kN) |")
    l.append("|---|---|")
    for k, vv in por_nivel.items():
        l.append("| %s | %.4f |" % (k, vv))
    l.append("")
    if delta is not None:
        l.append("Verificacion vs referencia (pg. 11): delta = %.4f kN (%s)"
                 % (delta, "OK" if checks["pm_adic_ei_total"]["ok"] else "ERROR"))
    l.append("")
    l.append("No doble conteo: %s" % ei["no_doble_conteo"])
    (OUT / "PMADIC_EI_aplicada.md").write_text("\n".join(l) + "\n", encoding="utf-8")

    print(json.dumps({"PMADIC_EI_aplicada": True, "tipo": ei["tipo"],
                      "n_losas": len(filas),
                      "total_aplicada_kN": total,
                      "por_nivel": por_nivel,
                      "delta_referencia_kN": delta},
                     ensure_ascii=False, indent=2))
    return 0 if total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())