"""conservar_G_EII_peso_MODELO_FIEL_v4 - tarea 4 de MODELO_FIEL_4.

Decision: como el plano 700 con posiciones A-F NO esta versionado en el repo
(ver BLOQUEO_PMADIC_EII_plano700), NO existe mapeo documental -> NO se regenera
ninguna cantidad. Se CONSERVAN los valores inmutables v3 verificandolos contra
los artefactos existentes:

  G_EI  P_z          = 42406.9577 kN
  G_EII P_z          = 25970.9994 kN
  PM.ADIC EII aplicada = 0 kN (cobertura 0, 6 familias AMBIGUO_NO_APLICADO)
  peso sismico EI  W_A = 36272.2911 kN ; W_B = 46516.4301 kN
  peso sismico EII W_A = 28600.7138 kN ; W_B = 28600.7138 kN (A==B)

No se tocan EX/EY, superposicion ni D/C. Sin regenerar results/ ni el modelo.

Escribe en modelo_fiel/:
  CONSERVACION_G_EII_peso_sismico_v4.json
  CONSERVACION_G_EII_peso_sismico_v4.md
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
MF = E3 / "modelo_fiel"

REF = {
    "G_EI_P_z_kN": 42406.9577,
    "G_EII_P_z_kN": 25970.9994,
    "peso_EI_W_A_kN": 36272.2911,
    "peso_EI_W_B_kN": 46516.4301,
    "peso_EII_W_A_kN": 28600.7138,
    "peso_EII_W_B_kN": 28600.7138,
}


def _round4(v: float) -> float:
    return round(v, 4)


def main() -> dict:
    g_ei = json.loads((MF / "EI/G_EI_MODELO_FIEL_v3.json").read_text(encoding="utf-8"))
    g_eii = json.loads((MF / "EII/G_EII_MODELO_FIEL_v3.json").read_text(encoding="utf-8"))
    peso = json.loads((MF / "peso_sismico_MODELO_FIEL_v3.json").read_text(encoding="utf-8"))

    medido = {
        "G_EI_P_z_kN": _round4(g_ei["solucion"]["P_z_kN"]),
        "G_EII_P_z_kN": _round4(g_eii["solucion"]["P_z_kN"]),
        "peso_EI_W_A_kN": _round4(sum(v["W_A_kN"] for v in peso["EI"]["por_banda"].values())),
        "peso_EI_W_B_kN": _round4(sum(v["W_B_kN"] for v in peso["EI"]["por_banda"].values())),
        "peso_EII_W_A_kN": _round4(sum(v["W_A_kN"] for v in peso["EII"]["por_banda"].values())),
        "peso_EII_W_B_kN": _round4(sum(v["W_B_kN"] for v in peso["EII"]["por_banda"].values())),
    }

    controles = {}
    ok_all = True
    for k, ref in REF.items():
        med = medido[k]
        ok = abs(med - ref) < 1e-4
        ok_all = ok_all and ok
        controles[k] = {"referencia_v3": ref, "verificado": med, "ok": ok, "diferencia": round(med - ref, 4)}

    pmadic_eii = g_eii.get("PM_ADIC", {})
    aplicada_eii = pmadic_eii.get("aplicada_kN", 0.0)
    cobertura_eii = pmadic_eii.get("cobertura", 0.0)
    ok_pmadic = (abs(aplicada_eii) < 1e-9) and (abs(cobertura_eii) < 1e-9)

    ok_eii_a_eq_b = abs(medido["peso_EII_W_A_kN"] - medido["peso_EII_W_B_kN"]) < 1e-9

    cons = {
        "iteracion": "MODELO_FIEL_4",
        "tarea": "4_conservar_G_EII_peso_sismico",
        "decision": "NO_REGENERAR",
        "motivo": "sin mapeo documental del PM.ADIC EII (plano 700 no versionado en el repo; ver BLOQUEO_PMADIC_EII_plano700)",
        "clasificacion_pendiente": "G_EII y peso sismico conservados como pendientes documentadas (PM.ADIC EII cobertura 0)",
        "verificados_v3": controles,
        "controles": {
            "todo_ok": ok_all,
            "G_EI_equilibrio_vertical": g_ei["solucion"].get("equilibrio_vertical"),
            "G_EII_equilibrio_vertical": g_eii["solucion"].get("equilibrio_vertical"),
            "pmadic_EII_aplicada_kN": aplicada_eii,
            "pmadic_EII_cobertura": cobertura_eii,
            "pmadic_EII_ok": ok_pmadic,
            "peso_EII_A_eq_B": ok_eii_a_eq_b,
        },
        "sin_regenerar": ["G_EI", "G_EII", "peso_sismico", "EX/EY", "superposicion", "D/C"],
    }

    (MF / "CONSERVACION_G_EII_peso_sismico_v4.json").write_text(
        json.dumps(cons, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Conservacion G_EII y peso sismico - MODELO_FIEL_4", "",
        f"**Decision:** `{cons['decision']}` -- `{cons['motivo']}`", "",
        "| Cantidad | Referencia v3 (kN) | Verificado (kN) | OK |",
        "|---|---|---|---|",
    ]
    for k, v in cons["verificados_v3"].items():
        md.append(f"| {k} | {v['referencia_v3']} | {v['verificado']} | {v['ok']} |")
    md += [
        "",
        "| Control | Valor |",
        "|---|---|",
        f"| todo_ok | {ok_all} |",
        f"| G_EI equilibrio vertical | {cons['controles']['G_EI_equilibrio_vertical']} |",
        f"| G_EII equilibrio vertical | {cons['controles']['G_EII_equilibrio_vertical']} |",
        f"| PM.ADIC EII aplicada (kN) | {aplicada_eii} |",
        f"| PM.ADIC EII cobertura | {cobertura_eii} |",
        f"| peso EII A==B | {ok_eii_a_eq_b} |",
        "",
        "Sin regenerar: G_EI, G_EII, peso sismico, EX/EY, superposicion, D/C.",
    ]
    (MF / "CONSERVACION_G_EII_peso_sismico_v4.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"estado": "CONSERVADO_SIN_REGENERAR" if ok_all and ok_pmadic and ok_eii_a_eq_b else "FALLO",
                      "todo_ok": ok_all, "pmadic_EII_ok": ok_pmadic,
                      "peso_EII_A_eq_B": ok_eii_a_eq_b}, ensure_ascii=False, indent=2))
    return cons


if __name__ == "__main__":
    main()