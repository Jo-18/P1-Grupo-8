"""Regresiones y verificaciones de la iteracion MODELO_FIEL_2.

Verifica (sin tocar results/):
  1. suite completa del repositorio (tests/: 28 pruebas) con unittest discover, en subproceso.
  2. Manifest del checkpoint (perfiles/checkpoint_semana3) sigue valido.
  3. Artefactos v2 presentes y con todos sus checks OK.
  4. Invariantes cruzados entre artefactos v2 (ledger, pesos A/B, casos G v2,
     auditoria PM.ADIC) y contra el checkpoint.
  5. Conservacion PP/PM.ADIC, no doble conteo, unidades y equilibrio.

Salida: modelo_fiel/regresiones_MODELO_FIEL_v2.json
Uso:
  python -X utf8 -m src.modelo_fiel.regresiones_MODELO_FIEL_v2 [--skip-tests]
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
PERFILES = OUT / "perfiles"
RES = E3 / "results"

AUD_PM = OUT / "PM_ADIC_auditoria_EI_EII.json"
LEDGER = OUT / "ledger_PP_PMADIC_Q.json"
PESO2 = OUT / "peso_sismico_MODELO_FIEL_v2.json"
G_EI2 = OUT / "G_EI_MODELO_FIEL_v2.json"
G_EII2 = OUT / "G_EII_MODELO_FIEL_v2.json"
LEDGER_V1 = OUT / "EI" / "G_EI_MODELO_FIEL.json"
FIEL_EII_V1 = OUT / "EII" / "G_EII_MODELO_FIEL.json"
REPRO = RES / "cargas" / "caso_G_EII_reproducible.json"

GRAV = 9.80665


def _r(ok, check, detalle):
    return {"check": check, "estado": "OK" if ok else "ERROR", "detalle": detalle}


def invariantes_v2(led, peso2, aud, gei2, geii2) -> list:
    out = []
    ei_aud = aud["EDIFICIO_I"]; eii_aud = aud["EDIFICIO_II"]
    # --- conservacion de componentes EI (auditoria == ledger == caso G v2) ---
    eil = led["EI"]["totales"]
    eic = gei2["componentes"]
    out.append(_r(abs(eil["PP_losas_kN"] - ei_aud["total_pp_losas_kn"]) < 0.01,
                  "conservacion_EI_PP_losas",
                  "ledger %.4f / audit %.4f" % (eil["PP_losas_kN"],
                                                ei_aud["total_pp_losas_kn"])))
    out.append(_r(abs(eil["PM_ADIC_kN"] - ei_aud["total_pm_adic_kn"]) < 0.01,
                  "conservacion_EI_PM_ADIC",
                  "ledger %.4f / audit %.4f" % (eil["PM_ADIC_kN"],
                                                ei_aud["total_pm_adic_kn"])))
    out.append(_r(abs(eil["PM_ADIC_kN"] - eic["PM_ADIC_kN"]) < 0.01 and
                  abs(eil["PP_losas_kN"] - eic["PP_losas_kN"]) < 0.01,
                  "conservacion_EI_ledger_vs_casoG_v2",
                  "PM.ADIC %.4f/%.4f ; PP_losas %.4f/%.4f"
                  % (eil["PM_ADIC_kN"], eic["PM_ADIC_kN"],
                     eil["PP_losas_kN"], eic["PP_losas_kN"])))

    # --- EII: PM.ADIC aplicada = 0 y catálogo intacto ---
    out.append(_r(abs(led["EII"]["totales"]["PM_ADIC_kN"]) < 1e-9,
                  "conservacion_EII_PM_ADIC_0",
                  "ledger EII PM.ADIC %.6f" % led["EII"]["totales"]["PM_ADIC_kN"]))
    out.append(_r(len(eii_aud["familias"]) == 6 and
                  abs(eii_aud.get("aplicada_al_FE_kN", 0.0)) < 1e-9,
                  "catalogo_EII_6_familias_aplicada0",
                  json.dumps(eii_aud)))

    # --- no doble conteo: vista 5 pisos == vista bandas ---
    eib = led["EI"]
    out.append(_r(abs(sum(p["W_B_kN"] for p in eib["por_piso_5"].values())
                      - sum(b["W_B_kN"] for b in
                            [eib["por_banda"][k] for k in eib["por_banda"]])) < 0.02,
                  "no_doble_conteo_EI_banda_minus701",
                  "sum 5 pisos %.4f vs bandas %.4f"
                  % (sum(p["W_B_kN"] for p in eib["por_piso_5"].values()),
                     sum(eib["por_banda"][k]["W_B_kN"] for k in eib["por_banda"]))))
    eii = led["EII"]
    out.append(_r(abs(sum(p["W_B_kN"] for p in eii["por_piso_5"].values())
                      - sum(eii["por_banda"][k]["W_B_kN"] for k in eii["por_banda"]))
                  < 0.02,
                  "no_doble_conteo_EII_pisos_vs_bandas",
                  "sum 5 pisos %.4f vs bandas %.4f"
                  % (sum(p["W_B_kN"] for p in eii["por_piso_5"].values()),
                     sum(eii["por_banda"][k]["W_B_kN"] for k in eii["por_banda"]))))

    # --- pesos v2 == ledger ---
    ei2 = peso2["EI"]; eii2 = peso2["EII"]
    out.append(_r(abs(ei2["resumen"]["W_B_kN"] - eil["W_B_total_kN"]) < 0.02,
                  "peso_v2_EI_WB==ledger",
                  "%.4f vs %.4f" % (ei2["resumen"]["W_B_kN"],
                                    eil["W_B_total_kN"])))
    out.append(_r(abs(ei2["resumen"]["W_A_kN"] - eil["W_A_total_kN"]) < 0.02,
                  "peso_v2_EI_WA==ledger",
                  "%.4f vs %.4f" % (ei2["resumen"]["W_A_kN"],
                                    eil["W_A_total_kN"])))
    out.append(_r(abs(eii2["resumen"]["W_B_kN"] - led["EII"]["totales"]["W_B_total_kN"])
                  < 0.02,
                  "peso_v2_EII_W==ledger", "%.4f" % eii2["resumen"]["W_B_kN"]))

    # --- unidades masa ---
    out.append(_r(abs(ei2["resumen"]["masa_B_Mg"] -
                      ei2["resumen"]["W_B_kN"] / GRAV) < 1e-3,
                  "unidades_masa_EI_B", "%.4f Mg" % ei2["resumen"]["masa_B_Mg"]))

    # --- equilibrio casos G v2 ---
    out.append(_r(gei2["solucion"]["equilibrio_vertical"] == "OK",
                  "equilibrio_EI_v2", "%s residuo=%.6f" % (
                      gei2["solucion"]["equilibrio_vertical"],
                      gei2["solucion"]["residuo_kN"])))
    out.append(_r(geii2["solucion"]["equilibrio_vertical"] == "OK",
                  "equilibrio_EII_v2", "%s residuo=%.6f" % (
                      geii2["solucion"]["equilibrio_vertical"],
                      geii2["solucion"]["residuo_kN"])))

    # --- G v2 == checkpoint + conservacion PP ---
    gck_EI = gei2["componentes"]["PP_losas_kN"] + gei2["componentes"]["PM_ADIC_kN"]
    out.append(_r(abs(gck_EI - 25227.73) < 0.05, "G_checkpoint_EI_reproducido",
                  "PP_losas+PM.ADIC = %.4f vs 25227.73" % gck_EI))
    out.append(_r(abs(geii2["componentes"]["permanente_aplicada_kN"]
                      - 25970.999) < 0.05,
                  "G_checkpoint_EII_reproducido",
                  "%.4f" % geii2["componentes"]["permanente_aplicada_kN"]))

    # --- origen 46.516,43 ---
    origen = led["origen_46516_43_kN"]
    out.append(_r(abs(origen["estructura_componentes_kN"]["W_B_igual_46516_43"]
                      - 46516.43) < 0.5,
                  "origen_46516_43_WB",
                  origen["estructura_componentes_kN"]))
    return out


def artefactos_v2() -> list:
    out = []
    for nm, p in (("PM_ADIC", AUD_PM), ("LEDGER", LEDGER), ("PESO_v2", PESO2),
                  ("G_EI_v2", G_EI2), ("G_EII_v2", G_EII2)):
        if not p.exists():
            out.append(_r(False, "artefacto_%s" % nm, "no existe %s" % p))
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d.get("verificaciones"), list):
            vv = d["verificaciones"]
            ok = all(c["ok"] for c in vv if "ok" in c)
            n_ok = sum(1 for c in vv if c.get("ok"))
            out.append(_r(ok, "artefacto_%s_checks" % nm,
                          "%s/%s" % (n_ok, len(vv))))
        elif isinstance(d.get("checks_ok"), int):
            out.append(_r(d["checks_ok"] == d["checks_total"],
                          "artefacto_%s_checks" % nm,
                          "%s/%s" % (d["checks_ok"], d["checks_total"])))
        else:
            vv = d.get("verificaciones_v1", {})
            all_ok = all(v == "OK" for v in vv.values())
            out.append(_r(all_ok, "artefacto_%s_checks" % nm,
                          str(vv)))
    return out


def invariant_casos_v1() -> list:
    v1ei = json.loads(LEDGER_V1.read_text(encoding="utf-8"))["ledger"]
    v1eii = json.loads(FIEL_EII_V1.read_text(encoding="utf-8"))["ledger"]
    return [
        _r(abs(v1ei["G_antes_kN"] - 25227.7316) < 0.05,
           "caso_v1_EI_G_antes", "%.4f" % v1ei["G_antes_kN"]),
        _r(abs(v1ei["G_despues_kN"] - 42406.9577) < 0.05,
           "caso_v1_EI_G_despues", "%.4f" % v1ei["G_despues_kN"]),
        _r(abs(v1eii["G_confirmado_kN"] - 25970.9994) < 0.05,
           "caso_v1_EII_G", "%.4f" % v1eii["G_confirmado_kN"]),
    ]


def manifest_checkpoint() -> list:
    if not (PERFILES / "checkpoint_semana3_manifest.json").exists():
        return [_r(False, "manifest_checkpoint", "no existe")]
    r = subprocess.run([sys.executable, "-X", "utf8", "-m",
                        "src.modelo_fiel.perfiles", "--verificar",
                        "checkpoint_semana3"], capture_output=True, text=True,
                       cwd=str(E3))
    return [_r(r.returncode == 0, "manifest_checkpoint",
               (r.stdout or r.stderr).strip().splitlines()[-1])]


def unittest_todo() -> list:
    """Pruebas con el runner portable del checkpoint: unittest discover."""
    r = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest",
                        "discover", "-s", "tests", "-p", "test_*.py"],
                       capture_output=True, text=True, cwd=str(E3))
    last = (r.stdout or r.stderr).strip().splitlines()[-1]
    return [_r(r.returncode == 0, "unittest_tests", last)]


def main(argv=None) -> int:
    skip_tests = "--skip-tests" in (argv or [])
    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    peso2 = json.loads(PESO2.read_text(encoding="utf-8"))
    aud = json.loads(AUD_PM.read_text(encoding="utf-8"))
    gei2 = json.loads(G_EI2.read_text(encoding="utf-8"))
    geii2 = json.loads(G_EII2.read_text(encoding="utf-8"))

    checks = []
    checks += artefactos_v2()
    checks += invariantes_v2(led, peso2, aud, gei2, geii2)
    checks += invariant_casos_v1()
    checks += manifest_checkpoint()
    if not skip_tests:
        checks += unittest_todo()

    (OUT / "regresiones_MODELO_FIEL_v2.json").write_text(
        json.dumps({"caso": "regresiones_MODELO_FIEL_2",
                    "checks": checks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    ok = all(c["estado"] == "OK" for c in checks)
    print(json.dumps({"checks_ok": sum(1 for c in checks if c["estado"] == "OK"),
                      "checks_total": len(checks),
                      "fallidos": [c["check"] for c in checks
                                   if c["estado"] != "OK"]},
                     ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())