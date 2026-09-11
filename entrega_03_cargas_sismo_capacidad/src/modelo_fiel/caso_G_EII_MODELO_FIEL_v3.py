"""G_EII_MODELO_FIEL_v3 — caso G fiel del EII, iteracion MODELO_FIEL_3 (tarea 7).

Re-solve documentado con el artefacto reproducible del checkpoint
(`results/cargas/caso_G_EII_reproducible.json`, solver OpenSeesPy ya resuelto
y verificable; NO se regen crea en results/ por restriccion del usuario, pero
se exporta completo y se coteja contra las verificaciones del artefacto):

  * reacciones (147), desplazamientos (222), fuerzas local/global (264)
  * equilibrio vertical R_z == P_z == 25.970,9994 kN
  * integra MODELO_FIEL_3: mapeo_PMADIC_EII_plano700 (aplicada = 0, cobertura 0)
  * compara v3 vs v2 vs checkpoint.

Escribo en modelo_fiel/:
  EII/G_EII_MODELO_FIEL_v3.json
  EII/G_EII_MODELO_FIEL_v3.md
  EII/G_EII_MODELO_FIEL_v3_reacciones.csv
  EII/G_EII_MODELO_FIEL_v3_desplazamientos.csv
  EII/G_EII_MODELO_FIEL_v3_fuerzas.csv

Uso:
  python -X utf8 -m src.modelo_fiel.caso_G_EII_MODELO_FIEL_v3
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
OUT_EII = OUT / "EII"
RES = E3 / "results"
REPRO = RES / "cargas" / "caso_G_EII_reproducible.json"

G = 9.80665


def _csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _max_abs(d):
    m = 0.0
    if isinstance(d, dict):
        for v in d.values():
            m = max(m, _max_abs(v))
    elif isinstance(d, (list, tuple)):
        m = max((abs(c) for c in d), default=0.0)
    return m


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_EII.mkdir(parents=True, exist_ok=True)

    repro = json.loads(REPRO.read_text(encoding="utf-8"))
    v2 = json.loads((OUT / "G_EII_MODELO_FIEL_v2.json").read_text(encoding="utf-8"))
    mapeo = json.loads((OUT / "mapeo_PMADIC_EII_plano700.json").read_text(encoding="utf-8"))
    led = json.loads((OUT / "ledger_PP_PMADIC_Q.json").read_text(encoding="utf-8"))

    sol = repro["solucion"]
    verif = repro["verificaciones"]
    eq = verif["equilibrio_vertical"]
    Pz = eq["P_z_kN"]
    Rz = eq["R_z_kN"]
    residuo = eq["residuo_kN"]

    pp_losas = led["EII"]["totales"]["PP_losas_kN"]
    pp_el = led["EII"]["totales"]["PP_elementos_kN"]
    pm_adic = led["EII"]["totales"]["PM_ADIC_kN"]
    q = led["EII"]["totales"]["Q_total_kN"]
    pp_total = round(pp_losas + pp_el, 4)

    # export
    _csv(OUT_EII / "G_EII_MODELO_FIEL_v3_reacciones.csv",
         ["nodo", "direccion", "valor_kN"],
         [(k, "comp_%d" % i, c) for k, v in sol["reacciones"].items()
          for i, c in enumerate(v if isinstance(v, list) else [v])])
    _csv(OUT_EII / "G_EII_MODELO_FIEL_v3_desplazamientos.csv",
         ["nodo", "direccion", "desplazamiento_m"],
         [(k, "comp_%d" % i, c) for k, v in sol["desplazamientos"].items()
          for i, c in enumerate(v if isinstance(v, list) else [v])])
    rows_f = []
    for tipo_sol in ("fuerzas_local_por_elemento", "fuerzas_global_por_elemento"):
        for elem, vals in sol[tipo_sol].items():
            if isinstance(vals, dict):
                for nodo, v in vals.items():
                    for i, c in enumerate(v if isinstance(v, list) else [v]):
                        rows_f.append((tipo_sol.replace("fuerzas_", "").replace("_por_elemento", ""),
                                       elem, nodo, "comp_%d" % i, c))
            elif isinstance(vals, list):
                for i, c in enumerate(vals):
                    rows_f.append((tipo_sol.replace("fuerzas_", "").replace("_por_elemento", ""),
                                   elem, "-", "comp_%d" % i, c))
    _csv(OUT_EII / "G_EII_MODELO_FIEL_v3_fuerzas.csv",
         ["tipo", "elemento", "nodo", "componente", "valor"],
         rows_f)

    verifs_ok = all(v.get("ok", True) for v in verif.values()
                    if isinstance(v, dict)) if isinstance(verif, dict) else False
    vs_v2 = round(Pz - v2["componentes"]["permanente_aplicada_kN"], 4)

    payload = {
        "caso": "G", "edificio": "II", "iteracion": "MODELO_FIEL_3",
        "motor": "OpenSeesPy (artefacto reproducible del checkpoint, resuelto; "
                 "no regenerado en results/ por restriccion de usuario)",
        "clasificacion_fidelidad":
            {"etiq": "REPRODUCIBLE_FULL_EXPORT_PMADIC_PENDIENTE",
             "razon": ("export completo con verificaciones del artefacto; "
                       "PM.ADIC A-F mapeado=0 (cobertura 0) por ausencia de "
                       "DXF; sin nuevos PP aplicados")},
        "componentes": {
            "PP_losas_kN": pp_losas, "PP_total_kN": pp_total,
            "PM_ADIC_kN": 0.0, "permanente_aplicada_kN": round(Pz, 4),
            "Q_sobrecarga_kN": round(q, 4)},
        "PM_ADIC": {"aplicada_kN": mapeo["aplicacion"]["aplicada_al_FE_kN"],
                    "cobertura": mapeo["aplicacion"]["cobertura"],
                    "n_familias_catalogadas": mapeo["catalogo"]["n_familias"],
                    "pendientes": mapeo["pendiente"],
                    "ruta_mapeo": "mapeo_PMADIC_EII_plano700.json"},
        "solucion": {
            "P_z_kN": Pz, "R_z_kN": Rz, "residuo_kN": residuo,
            "equilibrio_vertical": "OK" if eq.get("ok") else "ERROR",
            "analyze_retcode": sol["analyze_retcode"],
            "n_reacciones": len(sol["reacciones"]),
            "n_desplazamientos": len(sol["desplazamientos"]),
            "max_abs_desplazamiento": round(_max_abs(sol["desplazamientos"]), 8),
            "n_fuerzas_local": len(sol["fuerzas_local_por_elemento"]),
            "n_fuerzas_global": len(sol["fuerzas_global_por_elemento"]),
            "max_abs_fuerza": round(max(_max_abs(sol["fuerzas_local_por_elemento"]),
                                        _max_abs(sol["fuerzas_global_por_elemento"])), 4)},
        "comparacion": {
            "checkpoint_kN": Pz, "vs_v2_kN": vs_v2,
            "estado": "IDENTICO_AL_v2" if abs(vs_v2) < 1e-6 else "DIFERENTE"},
        "verificaciones_artefacto": verif,
        "verificaciones_artefacto_ok": verifs_ok,
        "export": {"reacciones_csv": "EII/G_EII_MODELO_FIEL_v3_reacciones.csv",
                   "desplazamientos_csv": "EII/G_EII_MODELO_FIEL_v3_desplazamientos.csv",
                   "fuerzas_csv": "EII/G_EII_MODELO_FIEL_v3_fuerzas.csv"}}

    (OUT_EII / "G_EII_MODELO_FIEL_v3.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    l = []
    l.append("# G_EII_MODELO_FIEL_v3 (MODELO_FIEL_3 / tarea 7)")
    l.append("")
    l.append("Re-solve documentado (artefacto reproducible del checkpoint).")
    l.append("")
    l.append("- PP_total: **%.4f kN** (losas %.4f + elementos %.4f)"
             % (pp_total, pp_losas, pp_el))
    l.append("- PM.ADIC aplicada: **0.00 kN** (cobertura 0, mapeo AMBIGUO)")
    l.append("- Permanente aplicada: **%.4f kN**" % Pz)
    l.append("- Q: %.4f kN" % q)
    l.append("")
    l.append("## Solucion (artefacto)")
    l.append("")
    l.append("- P_z = %.4f ; R_z = %.4f ; residuo = %.6f ; %s"
             % (Pz, Rz, residuo, payload["solucion"]["equilibrio_vertical"]))
    l.append("- max|desplazamiento| = %.8f m ; max|fuerza| = %.4f"
             % (payload["solucion"]["max_abs_desplazamiento"],
                payload["solucion"]["max_abs_fuerza"]))
    l.append("- reacciones=%d, desplazamientos=%d, fuerzas local=%d, global=%d"
             % (payload["solucion"]["n_reacciones"],
                payload["solucion"]["n_desplazamientos"],
                payload["solucion"]["n_fuerzas_local"],
                payload["solucion"]["n_fuerzas_global"]))
    l.append("")
    l.append("## PM.ADIC (plancha 700, MODELO_FIEL_3)")
    l.append("")
    l.append("- aplicada al FE: **0.00 kN** ; cobertura %.1f%% ; catalogo %d "
             "familias ; pendientes %d"
             % (mapeo["aplicacion"]["cobertura"], mapeo["catalogo"]["n_familias"],
                mapeo["pendiente"]["n_pendiente"]))
    l.append("-%s" % mapeo["pendiente"]["motivo"])
    l.append("")
    l.append("## Verificaciones del artefacto")
    l.append("")
    for k, v in verif.items():
        if isinstance(v, dict):
            l.append("- %s: %s" % (k, "OK" if v.get("ok") else "ERROR"))
    l.append("")
    l.append("- vs v2: %.4f -> %s" % (vs_v2, payload["comparacion"]["estado"]))
    (OUT_EII / "G_EII_MODELO_FIEL_v3.md").write_text("\n".join(l) + "\n", encoding="utf-8")

    print(json.dumps({"G_EII_v3": True, "permanente_aplicada_kN": round(Pz, 4),
                      "R_z_kN": Rz, "vs_v2_kN": vs_v2,
                      "n_reacciones": len(sol["reacciones"]),
                      "n_desplazamientos": len(sol["desplazamientos"]),
                      "verificaciones_ok": verifs_ok},
                     ensure_ascii=False, indent=2))
    return 0 if (verifs_ok and payload["solucion"]["equilibrio_vertical"] == "OK"
                 and sol["analyze_retcode"] == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())