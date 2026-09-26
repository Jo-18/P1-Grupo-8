"""informe_MODELO_FIEL_v3 — informe de cierre de la iteracion MODELO_FIEL_3.

Compila los artefactos v3 y sus verificaciones en:
  modelo_fiel/INFORME_MODELO_FIEL_v3.json / .md
  modelo_fiel/MANIFIESTO_MODELO_FIEL_v3.csv   (archivos de la iteracion)

Uso:
  python -X utf8 -m src.modelo_fiel.informe_MODELO_FIEL_v3
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    def lj(name):
        return json.loads((OUT / name).read_text(encoding="utf-8"))

    inv = lj("inventario_PP_pendiente_EI.json")
    mp = lj("mapeo_PMADIC_EII_plano700.json")
    pmei = lj("PMADIC_EI_aplicada.json")
    gei3 = lj("EI" / Path("G_EI_MODELO_FIEL_v3.json"))
    geii3 = lj("EII" / Path("G_EII_MODELO_FIEL_v3.json"))
    peso3 = lj("peso_sismico_MODELO_FIEL_v3.json")
    reg3 = lj("regresiones_MODELO_FIEL_v3.json")

    checks = reg3["checks"]
    ok = sum(1 for c in checks if c["estado"] == "OK")
    n = len(checks)

    payload = {
        "iteracion": "MODELO_FIEL_3",
        "gravedad_m_s2": 9.80665,
        "reglas_rebeldia": ["no git ops hasta revision",
                            "laboratorio_semana2 solo lectura",
                            "results/ y checkpoint sin regenerar"],
        "EI": {
            "PP_confirmado_kN": inv["PP_confirmado_kN"],
            "PP_pendientes": inv["conteo"],
            "pendientes_cuantificados_INO_aplicado_kN":
                inv["revision_extra"]["total_hipotesis_cuantificado_kN"],
            "PM_ADIC_aplicada_kN": pmei["total_aplicada_kN"],
            "G_fiel_kN": gei3["solucion"]["P_z_kN"],
            "equilibrio_vertical": gei3["solucion"]["equilibrio_vertical"],
            "comparacion": gei3["comparacion"],
            "export": gei3["export"]},
        "EII": {
            "PP_confirmado_kN": round(9670.7583 + 16300.241, 4),
            "PM_ADIC_catalogo": mp["catalogo"]["n_familias"],
            "PM_ADIC_aplicada_kN": mp["aplicacion"]["aplicada_al_FE_kN"],
            "PM_ADIC_cobertura": mp["aplicacion"]["cobertura"],
            "mapeo_pendientes": mp["pendiente"]["n_pendiente"],
            "G_fiel_kN": geii3["solucion"]["P_z_kN"],
            "equilibrio_vertical": geii3["solucion"]["equilibrio_vertical"]},
        "peso_sismico": {
            "EI_scB_PRINCIPAL_kN": peso3["EI"]["resumen"]["W_B_kN"],
            "EI_scA_sensibilidad_kN": peso3["EI"]["resumen"]["W_A_kN"],
            "EII_scB_kN": peso3["EII"]["resumen"]["W_B_kN"],
            "EII_scA_kN": peso3["EII"]["resumen"]["W_A_kN"],
            "rango_EI_kN": peso3["rangos_por_pendientes"]["EI"]["pendientes_cuantificadas_kN"]},
        "regresiones": {"ok": ok, "total": n,
                        "estado": "OK" if ok == n else "ERROR"},
        "clasificacion": {"EI": gei3["clasificacion_fidelidad"]["etiq"],
                          "EII": geii3["clasificacion_fidelidad"]["etiq"]}}

    (OUT / "INFORME_MODELO_FIEL_v3.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artefactos = [
        "inventario_PP_pendiente_EI", "PMADIC_EI_aplicada",
        "mapeo_PMADIC_EII_plano700", "peso_sismico_MODELO_FIEL_v3",
        "regresiones_MODELO_FIEL_v3",
        "EI/G_EI_MODELO_FIEL_v3", "EI/G_EI_MODELO_FIEL_v3_reacciones",
        "EI/G_EI_MODELO_FIEL_v3_desplazamientos", "EI/G_EI_MODELO_FIEL_v3_fuerzas",
        "EII/G_EII_MODELO_FIEL_v3", "EII/G_EII_MODELO_FIEL_v3_reacciones",
        "EII/G_EII_MODELO_FIEL_v3_desplazamientos",
        "EII/G_EII_MODELO_FIEL_v3_fuerzas",
    ]
    rows = []
    for base in artefactos:
        for ext in (".json", ".md", ".csv"):
            p = OUT / (base + ext)
            if p.exists():
                rows.append((str(p.relative_to(OUT)).replace("\\", "/"),
                             p.stat().st_size))
    for png in sorted((OUT / "figuras_plano700").glob("*.png")):
        rows.append(("figuras_plano700/" + png.name, png.stat().st_size))

    with open(OUT / "MANIFIESTO_MODELO_FIEL_v3.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "bytes"])
        for r in sorted(rows):
            w.writerow(r)

    l = []
    l.append("# INFORME MODELO_FIEL_3 (cierre de iteracion)")
    l.append("")
    l.append("Clasificacion: %s (EI) / %s (EII)"
             % (payload["clasificacion"]["EI"], payload["clasificacion"]["EII"]))
    l.append("")
    l.append("## EDIFICIO I (G)")
    l.append("- PP confirmado: **%.4f kN** ; pendientes: %d; ipotesis "
             "cuantificadas NO aplicadas: %.2f kN"
             % (inv["PP_confirmado_kN"], inv["conteo"]["pendientes"],
                inv["revision_extra"]["total_hipotesis_cuantificado_kN"]))
    l.append("- PM.ADIC aplicada: **%.4f kN** (99 losas)" % pmei["total_aplicada_kN"])
    l.append("- G fiel v3: **%.2f kN** ; %s ; vs v2 %.4f ; vs checkpoint %+.4f"
             % (gei3["solucion"]["P_z_kN"], gei3["solucion"]["equilibrio_vertical"],
                gei3["comparacion"]["vs_v2_kN"], gei3["comparacion"]["vs_checkpoint_kN"]))
    l.append("")
    l.append("## EDIFICIO II (G)")
    l.append("- PP confirmado: %.4f kN ; PM.ADIC catalogo %d familias, aplicada "
             "**%.1f kN** (cobertura %.1f%%)"
             % (round(9670.7583 + 16300.241, 4), mp["catalogo"]["n_familias"],
                mp["aplicacion"]["aplicada_al_FE_kN"], mp["aplicacion"]["cobertura"]))
    l.append("- G fiel v3: **%.2f kN** ; %s"
             % (geii3["solucion"]["P_z_kN"], geii3["solucion"]["equilibrio_vertical"]))
    l.append("")
    l.append("## Peso sismico")
    l.append("")
    l.append("- EI: B_PRINCIPAL = **%.2f kN** ; A_sensibilidad = %.2f kN"
             % (peso3["EI"]["resumen"]["W_B_kN"], peso3["EI"]["resumen"]["W_A_kN"]))
    l.append("- EII: B = %.2f kN ; A = %.2f kN (PM.ADIC 0)"
             % (peso3["EII"]["resumen"]["W_B_kN"], peso3["EII"]["resumen"]["W_A_kN"]))
    l.append("- Rango EI si se confirmara cimentacion: +%.2f kN"
             % payload["peso_sismico"]["rango_EI_kN"])
    l.append("")
    l.append("## Verificaciones")
    l.append("")
    l.append("- regresiones MODELO_FIEL_3: **%d/%d OK** (%s)" % (ok, n,
                                                                 payload["regresiones"]["estado"]))
    for c in checks:
        l.append("- [%s] %s" % (c["estado"], c["check"]))
    l.append("")
    l.append("Manifiesto: `MANIFIESTO_MODELO_FIEL_v3.csv` (%d archivos)."
             % len(rows))
    (OUT / "INFORME_MODELO_FIEL_v3.md").write_text("\n".join(l) + "\n", encoding="utf-8")

    print(json.dumps({"INFORME_MODELO_FIEL_v3": True,
                      "G_EI_kN": gei3["solucion"]["P_z_kN"],
                      "G_EII_kN": geii3["solucion"]["P_z_kN"],
                      "W_B_EI_kN": peso3["EI"]["resumen"]["W_B_kN"],
                      "W_A_EI_kN": peso3["EI"]["resumen"]["W_A_kN"],
                      "regresiones": "%d/%d" % (ok, n),
                      "archivos_manifest": len(rows)},
                     ensure_ascii=False, indent=2))
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())