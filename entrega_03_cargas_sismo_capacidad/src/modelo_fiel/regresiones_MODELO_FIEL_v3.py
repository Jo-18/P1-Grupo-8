"""Regresiones y verificaciones de la iteracion MODELO_FIEL_3 (tarea 9).

Verifica (sin tocar results/ ni laboratorio_semana2/):
  1. suite completa del repositorio (tests/: 28 pruebas) con unittest discover.
  2. regresiones MODELO_FIEL_1 (17 checks) y MODELO_FIEL_2 (26 checks).
  3. inventario_PP_pendiente_EI (conteo, rango, pp/m, aplicado=0).
  4. mapeo_PMADIC_EII_plano700 (6 familias, aplicada 0, cobertura 0, conversiones).
  5. PMADIC_EI_aplicada (99 losas, total 10.244,139, delta -0.011).
  6. casos G v3 EI (re-solve real) y EII (artefacto): equilibrio e identidades.
  7. peso_sismico_MODELO_FIEL_v3 vs v1/v2 y vs inventarios.
  8. conservacion PP/PM.ADIC, no doble conteo y unidades (masa = W/9.80665).

Salida: modelo_fiel/regresiones_MODELO_FIEL_v3.json
Uso:
  python -X utf8 -m src.modelo_fiel.regresiones_MODELO_FIEL_v3 [--skip-tests]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _r(ok, check, detalle):
    return {"check": check, "estado": "OK" if ok else "ERROR", "detalle": detalle}


REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
OUT_EI = OUT / "EI"
OUT_EII = OUT / "EII"

LEDGER = OUT / "ledger_PP_PMADIC_Q.json"
INV = OUT / "inventario_PP_pendiente_EI.json"
MAPEO = OUT / "mapeo_PMADIC_EII_plano700.json"
PMEI = OUT / "PMADIC_EI_aplicada.json"
G_EI3 = OUT_EI / "G_EI_MODELO_FIEL_v3.json"
G_EII3 = OUT_EII / "G_EII_MODELO_FIEL_v3.json"
PESO3 = OUT / "peso_sismico_MODELO_FIEL_v3.json"
V2R = OUT / "regresiones_MODELO_FIEL_v2.json"
V1R = OUT / "regresiones_MODELO_FIEL.json"

GRAV = 9.80665
G_KN_POR_KG = GRAV / 1000.0


def main(argv=None) -> int:
    skip = "--skip-tests" in (argv or sys.argv[1:])
    out = []
    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    inv = json.loads(INV.read_text(encoding="utf-8"))
    mp = json.loads(MAPEO.read_text(encoding="utf-8"))
    pmei = json.loads(PMEI.read_text(encoding="utf-8"))
    gei3 = json.loads(G_EI3.read_text(encoding="utf-8"))
    geii3 = json.loads(G_EII3.read_text(encoding="utf-8"))
    peso3 = json.loads(PESO3.read_text(encoding="utf-8"))

    ei_t = led["EI"]["totales"]
    eii_t = led["EII"]["totales"]

    # --- 3) inventario EI ---
    n_p = inv["conteo"]["pendientes"]
    out.append(_r(n_p == 63, "inventario_n_pendientes",
                  "pendientes=%d (vigas 1 + columnas 43 + muros 19)" % n_p))
    rango = inv["revision_extra"]["total_hipotesis_cuantificado_kN"]
    out.append(_r(abs(rango - (4223.8204 + 3675.1844 + 554.5440)) < 0.001,
                  "inventario_rango_cuantificado",
                  "%.4f kN (tramos base col+muro + contencion)" % rango))
    fam = {f["seccion"]: f["pp_m_unit_kN_m"] for f in inv["pp_por_metro_por_familia_kN_m"]}
    out.append(_r(abs(fam.get("P.M. 300x300x20", 0) - 0.0224 * 76.9822) < 1e-3,
                  "inventario_pp_m_tubular_20", "%.4f kN/m" % fam.get(
                      "P.M. 300x300x20")))
    out.append(_r(abs(fam.get("V.M. 300x300x5", 0) - 0.0059 * 76.9822) < 1e-3,
                  "inventario_pp_m_tubular_5", "%.4f kN/m" % fam.get(
                      "V.M. 300x300x5")))
    out.append(_r(abs(fam.get("P. 70x70", 0) - 0.49 * 24.5166) < 1e-3,
                  "inventario_pp_m_hormigon_70", "%.4f kN/m" % fam.get(
                      "P. 70x70")))
    out.append(_r(inv["aplicado_al_FE_kN"] == 0.0,
                  "inventario_aplicado_0", "ningun pendiente confirmado"))

    # --- 4) mapeo EII ---
    out.append(_r(mp["catalogo"]["n_familias"] == 6,
                  "mapeo_6_familias", "A..F catalogadas"))
    out.append(_r(mp["aplicacion"]["aplicada_al_FE_kN"] == 0.0 and
                  mp["aplicacion"]["cobertura"] == 0.0,
                  "mapeo_aplicada_0", "cobertura 0"))
    out.append(_r(all(f["estado"] == "AMBIGUO_NO_APLICADO" for f in mp["mapeo"]["filas"]),
                  "mapeo_todo_ambiguo", "sin DXF en el arbol"))
    conv = {f["familia"]: f["q_kN_m"] for f in mp["mapeo"]["filas"]}
    out.append(_r(abs(conv.get("A", 0) - 260.0 * G_KN_POR_KG) < 1e-6,
                  "mapeo_conversion_A", "260 Kg/m -> %.6f kN/m" % conv.get("A")))
    out.append(_r(abs(conv.get("D", 0) - 1500.0 * G_KN_POR_KG) < 1e-6,
                  "mapeo_conversion_D", "1500 Kg/m -> %.6f kN/m" % conv.get("D")))

    # --- 5) PM.ADIC EI ---
    out.append(_r(pmei["n_losas"] == 99, "pm_ei_99_losas", "99 losas"))
    out.append(_r(abs(pmei["total_aplicada_kN"] - ei_t["PM_ADIC_kN"]) < 0.05,
                  "pm_ei_total_ledger", "%.4f vs ledger %.4f"
                  % (pmei["total_aplicada_kN"], ei_t["PM_ADIC_kN"])))
    out.append(_r(abs(pmei["delta_referencia_kN"] + 0.011) < 1e-9,
                  "pm_ei_delta_referencia", "delta %.4f vs referencia 10.244,15"
                  % pmei["delta_referencia_kN"]))
    out.append(_r(abs(sum(pmei["por_nivel_kN"].values()) - pmei["total_aplicada_kN"])
                  < 1e-6, "pm_ei_suma_por_nivel", "sum por_nivel == total"))

    # --- 6) casos G v3 ---
    out.append(_r(gei3["solucion"]["equilibrio_vertical"] == "OK",
                  "gei_v3_equilibrio", "residuo=%.6f" % gei3["solucion"]["residuo_kN"]))
    Pz = gei3["solucion"]["P_z_kN"]
    ident = round(ei_t["PP_losas_kN"] + ei_t["PM_ADIC_kN"]
                  + ei_t["PP_elementos_kN"], 4)
    out.append(_r(abs(Pz - ident) < 0.01, "gei_v3_identidad_pp_pm",
                  "P_z %.2f == PP_losas+PM.ADIC+PP_el %.2f" % (Pz, ident)))
    out.append(_r(gei3["comparacion"]["vs_v2_kN"] == 0.0,
                  "gei_v3_vs_v2_0", "identico al v2"))
    out.append(_r(abs(gei3["comparacion"]["vs_checkpoint_kN"] - ei_t["PP_elementos_kN"])
                  < 0.01, "gei_v3_vs_checkpoint_pp_el",
                  "+%.4f kN (PP elementos)" % gei3["comparacion"]["vs_checkpoint_kN"]))
    out.append(_r(gei3["checks_ok"] == gei3["checks_total"] == 7,
                  "gei_v3_checks_v1", "%d/%d" % (gei3["checks_ok"], gei3["checks_total"])))

    out.append(_r(geii3["solucion"]["equilibrio_vertical"] == "OK",
                  "geii_v3_equilibrio", "residuo=%.6f" % geii3["solucion"]["residuo_kN"]))
    out.append(_r(abs(geii3["solucion"]["P_z_kN"] - 25970.9994) < 1e-3,
                  "geii_v3_identidad",
                  "P_z %.4f == reproducible" % geii3["solucion"]["P_z_kN"]))
    out.append(_r(geii3["comparacion"]["vs_v2_kN"] == 0.0,
                  "geii_v3_vs_v2_0", "identico al v2"))
    out.append(_r(geii3["verificaciones_artefacto_ok"] is True,
                  "geii_v3_artefacto_ok", "verificaciones del artefacto OK"))

    # --- 7) peso sismico v3 ---
    p3 = peso3
    out.append(_r(abs(p3["EI"]["resumen"]["W_B_kN"] - 46516.4301) < 0.05,
                  "peso3_EI_WB_v1", "%.4f == v1 46.516,43" % p3["EI"]["resumen"]["W_B_kN"]))
    out.append(_r(abs(p3["EI"]["resumen"]["W_A_kN"] - 36272.2911) < 0.05,
                  "peso3_EI_WA_sensibilidad",
                  "%.4f == v2 36.272,29" % p3["EI"]["resumen"]["W_A_kN"]))
    out.append(_r(abs(p3["EII"]["resumen"]["W_B_kN"] - 28600.7138) < 0.05 and
                  abs(p3["EII"]["resumen"]["W_A_kN"] - 28600.7138) < 0.05,
                  "peso3_EII_AB_v1",
"%.4f == v1 28.600,71" % p3["EII"]["resumen"]["W_B_kN"]))
    out.append(_r(abs(p3["rangos_por_pendientes"]["EI"]["pendientes_cuantificadas_kN"]
                      - rango) < 0.011,
                  "peso3_rango_EI_inventario",
                  "rango %.2f == inventario" % rango))
    out.append(_r(p3["EI"]["resumen"]["masa_B_Mg"] - p3["EI"]["resumen"]["W_B_kN"] / GRAV
                  < 1e-3, "unidades_masa_EI_B",
                  "%.4f Mg" % p3["EI"]["resumen"]["masa_B_Mg"]))

    # --- 8) no doble conteo / conservacion ---
    out.append(_r(eii_t["PM_ADIC_kN"] == 0.0 and geii3["PM_ADIC"]["aplicada_kN"] == 0.0,
                  "no_doble_conteo_EII_PMADIC",
                  "PM.ADIC EII aplicada=0 en ledger y caso G v3"))
    out.append(_r(abs(led["EI"]["totales"]["PM_ADIC_kN"] - pmei["total_aplicada_kN"])
                  < 0.05, "pm_ei_ledger_vs_tabla",
                  "ledger %.4f == tabla %.4f" % (led["EI"]["totales"]["PM_ADIC_kN"],
                                                 pmei["total_aplicada_kN"])))
    out.append(_r(abs(led["EI"]["totales"]["PP_elementos_kN"]
                      - inv["PP_confirmado_kN"]) < 0.01,
                  "conservacion_PP_confirmado",
                  "PP elementos %.4f == confirmado %.4f (PM.ADIC separado)"
                  % (led["EI"]["totales"]["PP_elementos_kN"],
                     inv["PP_confirmado_kN"])))

    # --- 9) export completo ---
    for f in (OUT_EI / "G_EI_MODELO_FIEL_v3_reacciones.csv",
              OUT_EI / "G_EI_MODELO_FIEL_v3_desplazamientos.csv",
              OUT_EI / "G_EI_MODELO_FIEL_v3_fuerzas.csv",
              OUT_EII / "G_EII_MODELO_FIEL_v3_reacciones.csv",
              OUT_EII / "G_EII_MODELO_FIEL_v3_desplazamientos.csv",
              OUT_EII / "G_EII_MODELO_FIEL_v3_fuerzas.csv"):
        out.append(_r(f.exists(), "export_presente", f.name))

    # --- figuras plano 700 ---
    fig = OUT / "figuras_plano700"
    pngs = sorted(fig.glob("EII_*_plano700_auditoria.png")) if fig.exists() else []
    out.append(_r(len(pngs) == 5, "figuras_plano700_5_niveles",
                  "PNG por nivel: %d" % len(pngs)))

    cycles = []
    for mod, jf in (("regresiones_MODELO_FIEL", V1R),
                    ("regresiones_MODELO_FIEL_v2", V2R)):
        pr = subprocess.run([sys.executable, "-X", "utf8", "-m",
                             "src.modelo_fiel.%s" % mod, "--skip-tests"],
                            capture_output=True, text=True, cwd=str(E3))
        ok = pr.returncode == 0
        extra = ""
        jp = Path(jf)
        if jp.exists():
            j = json.loads(jp.read_text(encoding="utf-8"))
            checks = j.get("checks", []) if isinstance(j, dict) else []
            states = [c.get("estado") for c in checks if isinstance(c, dict)]
            ok1 = ok and states and all(s == "OK" for s in states)
            extra = "%d checks, %d OK" % (len(states),
                                          states.count("OK")) if states else jf.name
        else:
            ok1 = ok
            extra = "sin json de %s, rc=%d" % (jf.name, pr.returncode)
        cycles.append(_r(ok1, "regresiones_%s" % mod.split("_")[-1]
                         if mod != "regresiones_MODELO_FIEL" else "regresiones_v1",
                         extra + (" (rc=%d)" % pr.returncode)))

    checks_v3 = out

    # --- 1) suite completa ---
    unittest = {"check": "unittest_tests", "estado": "SKIP", "detalle": "saltado"}
    if not skip:
        pr = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest",
                             "discover", "-s", "tests", "-p", "test_*.py"],
                            capture_output=True, text=True, cwd=str(E3))
        m = "OK" if pr.returncode == 0 else "FAILED"
        unittest = _r(pr.returncode == 0, "unittest_tests",
                      "discover tests/: %s" % m)
    checks = checks_v3 + cycles + [unittest]

    payload = {"iteracion": "MODELO_FIEL_3", "gravedad_m_s2": GRAV,
               "n_checks_v3": len(checks_v3), "checks": checks}
    (OUT / "regresiones_MODELO_FIEL_v3.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"regresiones_v3": True,
                      "checks_ok": sum(1 for c in checks if c["estado"] == "OK"),
                      "checks_total": len(checks),
                      "estado": "OK" if all(c["estado"] == "OK" for c in checks)
                      else "ERROR"}, ensure_ascii=False, indent=2))
    return 0 if all(c["estado"] == "OK" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
