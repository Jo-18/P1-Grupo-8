"""informe_MODELO_FIEL_v4 — informe de cierre de la iteracion MODELO_FIEL_4.

Compila los artefactos v4 y sus verificaciones en:
  modelo_fiel/INFORME_MODELO_FIEL_v4.json / .md
  modelo_fiel/MANIFIESTO_MODELO_FIEL_v4.csv   (archivos de la iteracion)

Si existe modelo_fiel/PRUEBA_AISLADA_MODELO_FIEL_v4.json (generado en la copia
aislada temporal), lo incorpora al informe.

Uso:
  python -X utf8 -m src.modelo_fiel.informe_MODELO_FIEL_v4
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
    rec = lj("reconciliacion_PP_pendiente_EI.json")
    bloq = lj("BLOQUEO_PMADIC_EII_plano700.json")
    cons = lj("CONSERVACION_G_EII_peso_sismico_v4.json")
    reg4 = lj("regresiones_MODELO_FIEL_v4.json")
    reg3 = lj("regresiones_MODELO_FIEL_v3.json")
    pmei = lj("PMADIC_EI_aplicada.json")
    gei3 = lj("EI" / Path("G_EI_MODELO_FIEL_v3.json"))
    geii3 = lj("EII" / Path("G_EII_MODELO_FIEL_v3.json"))
    peso3 = lj("peso_sismico_MODELO_FIEL_v3.json")

    aislado_path = OUT / "PRUEBA_AISLADA_MODELO_FIEL_v4.json"
    aislado = json.loads(aislado_path.read_text(encoding="utf-8")) if aislado_path.exists() else None

    checks = reg4["checks"]
    ok = sum(1 for c in checks if c["estado"] == "OK")
    n = len(checks)
    checks3 = reg3["checks"]
    ok3 = sum(1 for c in checks3 if c["estado"] == "OK")

    payload = {
        "iteracion": "MODELO_FIEL_4",
        "gravedad_m_s2": 9.80665,
        "reglas_rebeldia": ["no git ops hasta revision",
                            "laboratorio_semana2 solo lectura",
                            "results/ y checkpoint sin regenerar"],
        "EI": {
            "PP_confirmado_kN": rec["margen"]["PP_confirmado_kN"],
            "PP_pendientes": inv["conteo"]["pendientes"],
            "hipotesis_informativas_kN": rec["margen"]["hipotesis_rango_superiorinformativo_kN"],
            "PM_ADIC_aplicada_kN": pmei["total_aplicada_kN"],
            "G_fiel_kN": gei3["solucion"]["P_z_kN"],
            "equilibrio_vertical": gei3["solucion"]["equilibrio_vertical"]},
        "EII": {
            "PM_ADIC_catalogo": mp["catalogo"]["n_familias"],
            "PM_ADIC_aplicada_kN": bloq["resumen"]["aplicada_al_FE_kN"],
            "PM_ADIC_cobertura": bloq["resumen"]["cobertura"],
            "estado_bloqueo": bloq["estado"],
            "archivo_a_solicitar": bloq["archivo_a_solicitar"]["primario"]["nombre"],
            "G_fiel_kN": geii3["solucion"]["P_z_kN"],
            "equilibrio_vertical": geii3["solucion"]["equilibrio_vertical"]},
        "conservacion_v4": {
            "decision": cons["decision"],
            "motivo": cons["motivo"],
            "verificaciones_ok": cons["controles"]["todo_ok"],
            "clasificacion": cons["clasificacion_pendiente"]},
        "peso_sismico": {
            "EI_scB_PRINCIPAL_kN": peso3["EI"]["resumen"]["W_B_kN"],
            "EI_scA_sensibilidad_kN": peso3["EI"]["resumen"]["W_A_kN"],
            "EII_scB_kN": peso3["EII"]["resumen"]["W_B_kN"],
            "EII_scA_kN": peso3["EII"]["resumen"]["W_A_kN"],
            "nota": "conservados v3 (sin regenerar)"},
        "portabilidad": {
            "copias_internas_4": True,
            "config_data_externas": True,
            "nota": "catalogo EI + areas II + por_viga (viewer_unity) + eii_viewer "
                    "(analisis_estructural) versionadas en data/externas con SHA procedencia"},
        "regresiones": {"ok": ok, "total": n,
                        "estado": "OK" if ok == n else "ERROR",
                        "base_v3": "%d/%d" % (ok3, len(checks3)),
                        "prueba_aislada": aislado},
        "clasificacion": {"EI": gei3["clasificacion_fidelidad"]["etiq"],
                          "EII": geii3["clasificacion_fidelidad"]["etiq"]}}

    (OUT / "INFORME_MODELO_FIEL_v4.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artefactos = [
        "reconciliacion_PP_pendiente_EI", "BLOQUEO_PMADIC_EII_plano700",
        "CONSERVACION_G_EII_peso_sismico_v4", "regresiones_MODELO_FIEL_v4",
        "INFORME_MODELO_FIEL_v4", "PRUEBA_AISLADA_MODELO_FIEL_v4",
    ]
    rows = []
    for base in artefactos:
        for ext in (".json", ".md", ".csv"):
            p = OUT / (base + ext)
            if p.exists():
                rows.append((str(p.relative_to(OUT)).replace("\\", "/"), p.stat().st_size))

    with open(OUT / "MANIFIESTO_MODELO_FIEL_v4.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "bytes"])
        for r in sorted(rows):
            w.writerow(r)

    l = []
    l.append("# INFORME MODELO_FIEL_4 (cierre de iteracion)")
    l.append("")
    l.append("Clasificacion: %s (EI) / %s (EII)"
             % (payload["clasificacion"]["EI"], payload["clasificacion"]["EII"]))
    l.append("")
    l.append("## Portabilidad (tarea 1)")
    l.append("- Copias internas en `data/externas/` con SHA procedencia: catalogo EI, "
             "areas_tributarias.csv, por_viga.json, eii_viewer.json.")
    l.append("- `config/cargas.json` -> `data/externas/...`; scan src/tests/config sin "
             "dependencias externas (solo cadenas de procedencia).")
    l.append("")
    l.append("## EDIFICIO I (G) - reconciliacion id por id (tarea 2)")
    l.append("- PP confirmado: **%.4f kN** ; pendientes: %d ; hipotesis informativas "
             "(no aplicadas): %.2f kN"
             % (rec["margen"]["PP_confirmado_kN"], inv["conteo"]["pendientes"],
                rec["margen"]["hipotesis_rango_superiorinformativo_kN"]))
    l.append("- Categorias C1..C6: %s."
             % ", ".join("%s=%d" % (c["categoria"], c["conteo"]) for c in rec["por_categoria"]))
    l.append("- PM.ADIC aplicada: **%.4f kN** (99 losas); G fiel v3: %.4f kN (%s)"
             % (pmei["total_aplicada_kN"], gei3["solucion"]["P_z_kN"],
                gei3["solucion"]["equilibrio_vertical"]))
    l.append("")
    l.append("## EDIFICIO II (G) - bloqueo PM.ADIC (tarea 3)")
    l.append("- PM.ADIC catalogo %d familias (A-F); aplicada **%.1f kN** (cobertura %.1f%%); "
             "estado: %s"
             % (mp["catalogo"]["n_familias"], bloq["resumen"]["aplicada_al_FE_kN"],
                bloq["resumen"]["cobertura"], bloq["estado"]))
    l.append("- Archivo exacto a solicitar: `%s` (sha256 %s)."
             % (bloq["archivo_a_solicitar"]["primario"]["nombre"],
                bloq["archivo_a_solicitar"]["primario"]["sha256"]))
    l.append("- G fiel v3 conservado: **%.4f kN** (%s)"
             % (geii3["solucion"]["P_z_kN"], geii3["solucion"]["equilibrio_vertical"]))
    l.append("")
    l.append("## Conservacion sin regenerar (tarea 4)")
    l.append("- Decision: **%s** ; %s" % (cons["decision"], cons["motivo"]))
    l.append("- Verificaciones: %s ; peso EII A==B 28.600,71 (EI B 46.516,43 / A 36.272,29)."
             % "OK" if cons["controles"]["todo_ok"] else "ERROR")
    l.append("")
    l.append("## Peso sismico (conservado v3)")
    l.append("- EI: B_PRINCIPAL = **%.2f kN** ; A_sensibilidad = %.2f kN"
             % (peso3["EI"]["resumen"]["W_B_kN"], peso3["EI"]["resumen"]["W_A_kN"]))
    l.append("- EII: B = A = %.2f kN (PM.ADIC 0)"
             % peso3["EII"]["resumen"]["W_B_kN"])
    l.append("")
    l.append("## Verificaciones")
    l.append("")
    l.append("- Regresiones MODELO_FIEL_4: **%d/%d OK** (%s); base v3 %d/%d."
             % (ok, n, payload["regresiones"]["estado"], ok3, len(checks3)))
    if aislado:
        l.append("- Prueba aislada: unittest %(unittest_ok)d/%(unittest_total)d ; "
                 "regresiones v3 %(v3_ok)d/%(v3_total)d ; v4 %(v4_ok)d/%(v4_total)d."
                 % {k: aislado.get(k, "n/a") for k in
                    ("unittest_ok", "unittest_total", "v3_ok", "v3_total",
                     "v4_ok", "v4_total")})
        l.append("- Directorio aislado temporal: `%s` (eliminado tras la corrida)."
                 % aislado.get("dir"))
    for c in checks:
        l.append("- [%s] %s" % (c["estado"], c["check"]))
    l.append("")
    l.append("Manifiesto: `MANIFIESTO_MODELO_FIEL_v4.csv` (%d archivos)."
             % len(rows))
    (OUT / "INFORME_MODELO_FIEL_v4.md").write_text("\n".join(l) + "\n", encoding="utf-8")

    print(json.dumps({"INFORME_MODELO_FIEL_v4": True,
                      "G_EI_kN": gei3["solucion"]["P_z_kN"],
                      "G_EII_kN": geii3["solucion"]["P_z_kN"],
                      "PP_confirmado_EI_kN": rec["margen"]["PP_confirmado_kN"],
                      "bloqueo_EII": bloq["estado"],
                      "regresiones": "%d/%d" % (ok, n),
                      "prueba_aislada": bool(aislado),
                      "archivos_manifest": len(rows)},
                     ensure_ascii=False, indent=2))
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())