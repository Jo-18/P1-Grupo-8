"""Regresiones de la iteracion MODELO_FIEL sobre el checkpoint.

Verifica (sin tocar results/):
  1. Todos los checks de los archivos MODELO_FIEL generados pasan.
  2. Invariantes cruzados entre ledgers, peso sismico y comparacion.
  3. El manifest del checkpoint (perfiles/checkpoint_semana3) sigue valido.
  4. (opcional) pytest de tests/cargas del checkpoint, en subproceso.

Salida: modelo_fiel/regresiones_MODELO_FIEL.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
PERFILES = OUT / "perfiles"

G_EI = OUT / "EI" / "G_EI_MODELO_FIEL.json"
LEDGER_EI = OUT / "EI" / "G_EI_MODELO_FIEL_ledger.json"
FIEL_EII = OUT / "EII" / "G_EII_MODELO_FIEL.json"
PESO = OUT / "peso_sismico_MODELO_FIEL.json"
COMP = OUT / "comparacion_MODELO_FIEL.json"

sys.path.insert(0, str(E3))


def _checks_of(nm: str, d: dict) -> list:
    if nm in ("G_EI", "G_EII"):
        return d.get("ledger", {}).get("verificaciones", [])
    return d.get("verificaciones", [])


def _checks_ok(nm: str, d: dict) -> bool:
    return all(c["estado"] == "OK" for c in _checks_of(nm, d))


def artefactos() -> dict:
    res = {}
    for nm, p in (("G_EI", G_EI), ("LEDGER_EI", LEDGER_EI),
                  ("G_EII", FIEL_EII), ("PESO", PESO), ("COMP", COMP)):
        if not p.exists():
            res[nm] = {"check": "artefacto_%s" % nm, "estado": "ERROR",
                       "detalle": "no existe: %s" % p}
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        vv = _checks_of(nm, d)
        ok = _checks_ok(nm, d)
        res[nm] = {"check": "artefacto_%s" % nm,
                   "estado": "OK" if ok else "ERROR",
                   "detalle": "verificaciones %s/%s"
                   % (sum(1 for c in vv if c["estado"] == "OK"), len(vv))}
    return res


def invariantes() -> list:
    led = json.loads(LEDGER_EI.read_text(encoding="utf-8"))
    peso = json.loads(PESO.read_text(encoding="utf-8"))
    comp = json.loads(COMP.read_text(encoding="utf-8"))
    out = []

    # Peso EI == ledger totals
    ok = abs(peso["EI"]["W_total_kN"]
             - (sum(p["PP_fiel_kN"] for p in peso["EI"]["por_piso"].values())
                + 0.5 * sum(p["Q_total_kN"]
                            for p in peso["EI"]["por_piso"].values()))) < 0.05
    out.append({"check": "peso_EI_W=PP+05Q",
                "estado": "OK" if ok else "ERROR",
                "detalle": peso["EI"]["W_total_kN"]})

    ok = abs(sum(p["PP_fiel_kN"] for p in peso["EI"]["por_piso"].values())
             - led["G_despues_kN"]) < 0.05
    out.append({"check": "peso_EI_PP==G_despues",
                "estado": "OK" if ok else "ERROR",
                "detalle": "PR fiel %.4f vs G_despues %.4f"
                % (sum(p["PP_fiel_kN"] for p in peso["EI"]["por_piso"].values()),
                   led["G_despues_kN"])})

    ok = abs(sum(p["Q_total_kN"] for p in peso["EI"]["por_piso"].values())
             - 8218.94463) < 0.01
    out.append({"check": "peso_EI_Q_total",
                "estado": "OK" if ok else "ERROR",
                "detalle": "Q EI por piso"})

    # EII invariantes
    for p in peso["EII"]["por_piso"].values():
        ok = abs(p["PP_fiel_kN"] - p["PP_checkpoint_kN"]) < 1e-9
        out.append({"check": "peso_EII_ck==fiel_%s" % p["nivel"],
                    "estado": "OK" if ok else "ERROR",
                    "detalle": "%.4f" % p["PP_fiel_kN"]})

    # Comparacion con ledgers
    ok = abs(comp["EI"]["totales_kN"]["fiel"] - led["G_despues_kN"]) < 0.05
    out.append({"check": "comparacion_EI_fiel==ledger",
                "estado": "OK" if ok else "ERROR",
                "detalle": comp["EI"]["totales_kN"]["fiel"]})
    eii_libro = json.loads(FIEL_EII.read_text(encoding="utf-8"))["ledger"]
    ok = abs(eii_libro["G_confirmado_kN"] - comp["EII"]["totales_kN"]["fiel"]) < 0.01
    out.append({"check": "comparacion_EII_fiel==ledger",
                "estado": "OK" if ok else "ERROR",
                "detalle": comp["EII"]["totales_kN"]["fiel"]})
    return out


def manifest_checkpoint() -> dict:
    m = PERFILES / "checkpoint_semana3_manifest.json"
    if not m.exists():
        return {"check": "manifest_checkpoint", "estado": "ERROR",
                "detalle": "no existe %s" % m}
    r = subprocess.run([sys.executable, "-X", "utf8", "-m",
                        "src.modelo_fiel.perfiles", "--verificar",
                        "checkpoint_semana3"], capture_output=True, text=True,
                       cwd=str(E3))
    estado = "OK" if r.returncode == 0 else "ERROR"
    return {"check": "manifest_checkpoint",
            "estado": estado,
            "detalle": r.stdout.strip().splitlines()[-1]
            if r.stdout.strip() else r.stderr.strip()}


def unittest_checkpoint() -> dict:
    r = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest",
                        "discover", "-s", "tests/cargas", "-p", "test_*.py"],
                       capture_output=True, text=True, cwd=str(E3))
    return {"check": "unittest_tests_cargas",
            "estado": "OK" if r.returncode == 0 else "ERROR",
            "detalle": (r.stdout or r.stderr).strip().splitlines()[-1]}


def main(argv=None) -> int:
    skip_tests = "--skip-tests" in (argv or [])
    checks = list(invariantes())
    checks += artefactos().values()
    checks.append(manifest_checkpoint())
    if not skip_tests:
        checks.append(unittest_checkpoint())
    (OUT / "regresiones_MODELO_FIEL.json").write_text(
        json.dumps({"caso": "regresiones_MODELO_FIEL_1", "checks": checks},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = all(c["estado"] == "OK" for c in checks)
    print(json.dumps({"checks_ok": sum(1 for c in checks
                                       if c["estado"] == "OK"),
                      "checks_total": len(checks),
                      "fallidos": [c["check"] for c in checks
                                   if c["estado"] != "OK"]},
                     ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())