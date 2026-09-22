"""Comparacion de perfiles por edificio: checkpoint vs MODELO_FIEL vs publicado.

EI:
    checkpoint  = G del checkpoint (losas + PM.ADIC) por nivel (25.227,73 kN)
    PP_fiel     = PP confirmado por nivel desde la auditoria v2 (17.179,23 kN)
    fiel        = G_despues por nivel (24.406,96... 42.406,96 kN)
    publicado   = auditoria v2 (42.406,96 kN con componentes por familia)

EII:
    checkpoint/fiel = reproducible (25.970,999 kN) con componentes (filas)
    publicado = circulado en la publicacion oficial (29.306,07 kN)

Salidas: modelo_fiel/comparacion_MODELO_FIEL.json y .md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
LEDGER_EI = OUT / "EI" / "G_EI_MODELO_FIEL_ledger.json"
FIEL_EII = OUT / "EII" / "G_EII_MODELO_FIEL.json"
PESO = OUT / "peso_sismico_MODELO_FIEL.json"

sys.path.insert(0, str(E3))


def comparar_ei():
    l = json.loads(LEDGER_EI.read_text(encoding="utf-8"))
    peso = json.loads(PESO.read_text(encoding="utf-8"))["EI"]["por_piso"]
    filas = []
    for z, p in sorted(peso.items(), key=lambda kv: float(kv[0])):
        filas.append({"nivel": p["nivel"], "z_m": p["z_m"],
                      "checkpoint_kN": p["PP_checkpoint_kN"],
                      "pp_fiel_kN": p["PP_confirmado_nuevo_kN"],
                      "fiel_kN": p["PP_fiel_kN"]})
    pend = l["pendientes_explicitos"]
    return {
        "edificio": "EI", "por_nivel": filas,
        "totales_kN": {"checkpoint": round(l["G_antes_kN"], 4),
                       "pp_fiel": round(l["PP_confirmado_kN"], 4),
                       "fiel": round(l["G_despues_kN"], 4)},
        "publicado_componentes_kN": {
            "vigas": 14803.534, "columnas": 2045.6003, "muros": 330.0918,
            "total_publicado": round(l["G_despues_kN"], 4)},
        "pendientes_no_cuantificados_kN": {
            "tramos_base_col+col_adic": pend["columnas_base_kN"],
            "tramos_base_muros": pend["muros_base_kN"],
            "contencion_sotano": pend["contencion_kN"],
            "v_s_i_200": "sin cuantificar (PENDIENTE_SECCION)",
            "metalicos": "sin cuantificar"},
    }


def comparar_eii():
    d = json.loads(FIEL_EII.read_text(encoding="utf-8"))
    led = d["ledger"]
    peso = json.loads(PESO.read_text(encoding="utf-8"))["EII"]["por_piso"]
    por_nivel = [{"nivel": p["nivel"], "z_m": p["z_m"],
                  "checkpoint_kN": p["PP_fiel_kN"],
                  "fiel_kN": p["PP_fiel_kN"]}
                 for z, p in sorted(peso.items(), key=lambda kv: float(kv[0]))]
    return {
        "edificio": "EII", "por_nivel": por_nivel,
        "totales_kN": {"checkpoint": led["G_confirmado_kN"],
                       "pp_fiel": led["G_confirmado_kN"],
                       "fiel": led["G_confirmado_kN"]},
        "publicado_componentes_kN": {
            "losas": 9677.0267, "vigas": 11585.48, "columnas": 1522.31,
            "muros": 6521.26, "total_publicado": 29306.0667},
        "componentes_comparacion": led["filas_componente"],
        "pendientes_cuantificados_kN": led["pendientes_explicitos"],
    }


def _markdown(ei, eii) -> str:
    l = []
    l.append("# Comparacion de perfiles por edificio (checkpoint vs MODELO_FIEL vs publicado)")
    l.append("")
    for d in (ei, eii):
        l.append("## %s" % d["edificio"])
        l.append("")
        l.append("| nivel | checkpoint (kN) | PP fiel (kN) | fiel (kN) |")
        l.append("|---|---|---|---|")
        for r in d["por_nivel"]:
            ck = r.get("checkpoint_kN", 0.0)
            fiel = r.get("fiel_kN", 0.0)
            l.append("| %s | %.2f | %.2f | %.2f |" % (
                r["nivel"], ck, r.get("pp_fiel_kN", ck), fiel))
        t = d["totales_kN"]
        l.append("| **TOTAL** | **%.2f** | **%.2f** | **%.2f** |" % (
            t["checkpoint"], t["pp_fiel"], t["fiel"]))
        l.append("")
        l.append("Publicado (componentes):")
        for k, v in d["publicado_componentes_kN"].items():
            l.append("- %s: %s kN" % (k, v))
        l.append("")
    return "\n".join(l) + "\n"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ei = comparar_ei()
    eii = comparar_eii()
    checks = [
        {"check": "ck_ei", "estado": "OK" if abs(
            ei["totales_kN"]["checkpoint"] - 25227.7316) < 0.01 else "ERROR",
         "detalle": "checkpoint EI 25227.7316"},
        {"check": "fiel_ei", "estado": "OK" if abs(
            ei["totales_kN"]["fiel"] - 42406.9577) < 0.05 else "ERROR",
         "detalle": "fiel EI 42406.9577"},
        {"check": "suma_pp_por_nivel", "estado": "OK" if abs(
            sum(r["pp_fiel_kN"] for r in ei["por_nivel"]) - 17179.2261) < 0.05
            else "ERROR", "detalle": "PP EI tributario por nivel 17179.2261"},
        {"check": "paridad_por_nivel", "estado": "OK" if all(
            abs(r["checkpoint_kN"] + r["pp_fiel_kN"] - r["fiel_kN"]) < 0.1
            for r in ei["por_nivel"]) else "ERROR",
         "detalle": "checkpoint+PP = fiel en todos los pisos (tributario)"},
        {"check": "eii_publicado_vs_fiel",
         "estado": "OK" if eii["publicado_componentes_kN"]["total_publicado"] >
         0 and eii["totales_kN"]["fiel"] > 0 else "ERROR",
         "detalle": "ambos totales EII cuantificados"},
    ]
    payload = {"caso": "comparacion_perfiles",
               "iteracion": "MODELO_FIEL_1", "EI": ei, "EII": eii,
               "verificaciones": checks}
    (OUT / "comparacion_MODELO_FIEL.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "comparacion_MODELO_FIEL.md").write_text(
        _markdown(ei, eii), encoding="utf-8")
    print(json.dumps({"EI": ei["totales_kN"], "EII": eii["totales_kN"],
                      "checks_ok": sum(1 for c in checks if c["estado"] == "OK"),
                      "checks_total": len(checks)},
                     ensure_ascii=False, indent=2))
    return 0 if all(c["estado"] == "OK" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())