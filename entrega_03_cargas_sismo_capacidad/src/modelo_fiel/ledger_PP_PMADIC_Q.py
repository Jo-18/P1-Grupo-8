"""Ledger PP/PM.ADIC/Q por edificio y nivel + escenarios de peso sismico A y B.

Iteracion MODELO_FIEL_2: separa EXPLICITAMENTE los componentes de la carga
permanente (PP_losas, PP_vigas, PP_columnas, PP_muros, PP_otros) de la
PM.ADIC y de Q, con columnas independientes por nivel. Nunca se etiqueta como
"PP" una suma que incluya PM.ADIC.

Escenarios de peso sismico (q_Q = 2.0 kN/m2, fraccion 0.5):
  * Escenario A: W_A = PP_total + 0.50*Q      (mm=EN: excluye PM.ADIC)
  * Escenario B: W_B = PP_total + PM_ADIC + 0.50*Q  (= G completa + 0.50*Q)

El valor previo de la iteracion 1 del EI (46.516,43 kN) corresponde a W_B:
  25.227,73 (G checkpoint = PP_losas + PM.ADIC)
  + 17.179,23 (PP elementos confirmado por auditoria v2) = 42.406,96 (G fiel)
  + 0.5*8218,94463 (4.109,47) = 46.516,43 kN.
W_A = 36.272,28 kN (46.516,43 - PM_ADIC 10.244,15). La interpretacion de
"peso propio" para el peso sismico queda para confirmacion del profesor.

El reparto por banda z sigue el artefacto del checkpoint (EI: banda -7.01
"nucleo/sotano" atribuida dentro de CP1S; EI 6 bandas, EII 5 bandas). Se
publican ademas los 5 pisos canonicos (CP1S..P4) con la banda -7.01
integrada en CP1S (sin duplicar).

Salidas en modelo_fiel/:
  ledger_PP_PMADIC_Q.json          contrato por edificio y nivel + escenarios
  ledger_PP_PMADIC_Q.csv           por-nivel (CP1S..P4)
  ledger_PP_PMADIC_Q.md            resumen legible + verificaciones
  origen_46516_43_kN.md/.json      trazabilidad del valor 46.516,43 kN del EI

Uso:
  python -X utf8 -m src.modelo_fiel.ledger_PP_PMADIC_Q
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
RES = E3 / "results"
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"

AUDIT_EI = RES / "peso_propio_teorico_EDIFICIO_I_v2.json"
Q_EI = RES / "cargas" / "caso_Q_EI_FE.json"
Q_EII = RES / "cargas" / "caso_Q_EII_FE.json"
G_EII = RES / "cargas" / "caso_G_EII_reproducible.json"

sys.path.insert(0, str(EI_SRC))
sys.path.insert(0, str(E3))

from analisis.fe import geometria_fe as GF            # noqa: E402
from analisis.fe import tributaria as TB              # noqa: E402
from analisis.fe import cargas_correlacionadas as CC  # noqa: E402
from analisis.fe.marco import Marco                   # noqa: E402

from src.modelo_fiel.caso_G_EI_MODELO_FIEL import (   # noqa: E402
    _match_columnas, _match_muros, _match_vigas,
    aplicar_pp_nodal,
    cargas_G_actual,
    construir_marco_EI,
)
from src.cargas.pipeline_FE_EII import (              # noqa: E402
    GAMMA_CONCRETO_KN_M3, MarcoEII,
)

FRACCION_Q = 0.5
GRAV = 9.80665  # m/s2 (para masa)

ETIQ_EI = {-7.01: "sotano nucleo (z -7.01)", -4.01: "CP1S",
           -0.05: "P1", 3.91: "P2", 7.87: "P3", 11.83: "P4"}
ETIQ_EII = {-4.01: "EII_CP1S", -0.05: "EII_CP1", 3.91: "EII_CP2",
            7.87: "EII_CP3", 11.83: "EII_CP4"}
COTAS_EI = sorted(ETIQ_EI)
COTAS_EII = sorted(ETIQ_EII)


def _flat(cargas_por_nivel) -> dict:
    out = {}
    for c in cargas_por_nivel.values():
        for t, f in c.items():
            out[int(t)] = out.get(int(t), [0.0] * 6)
            for i in range(6):
                out[int(t)][i] += f[i]
    return out


def _grupo_z(loads, key_of_tag, cotas, tol_z=0.1) -> dict:
    grupos = {}
    for t, f in loads.items():
        t = int(t)
        if t not in key_of_tag:
            continue
        z = key_of_tag[t][2]
        band = min(cotas, key=lambda c: abs(c - z))
        if abs(band - z) > tol_z:
            band = round(z, 2)
        grupos.setdefault(band, {})[t] = f
    return grupos


def _resumen(loads, key_of_tag) -> dict:
    F = sum(-f[2] for f in loads.values())
    wx = sum(-f[2] * key_of_tag[t][0] for t, f in loads.items())
    wy = sum(-f[2] * key_of_tag[t][1] for t, f in loads.items())
    cm = (wx / F, wy / F) if F > 0 else (None, None)
    return {"carga_kN": round(F, 6), "n_nodos": len(loads),
            "CM_x_m": round(cm[0], 6) if cm[0] is not None else None,
            "CM_y_m": round(cm[1], 6) if cm[1] is not None else None}


def _sum_fz(cargas_por_nivel) -> float:
    return -sum(f[2] for c in cargas_por_nivel.values() for f in c.values())


def _g_losas_solo_pm(marco, por_nivel_cc, pm_kn=0.0) -> dict:
    """G por nivel con PM.ADIC forzado a `pm_kn` (0 -> solo PP losa)."""
    cargas = {}
    for cod in ("CP1S", "P1", "P2", "P3", "P4"):
        nivelFE = marco.niveles[cod]
        cargas_por_losa = {
            lo["id"]: (por_nivel_cc.get(cod, {}).get(lo["id"], {}).get("pm_kn_m2", 0.0)
                       if pm_kn is None else pm_kn,
                       por_nivel_cc.get(cod, {}).get(lo["id"], {}).get("sc_kn_m2", 0.0))
            for lo in nivelFE.losas}
        cn, _rp = TB.calcular_cargas_nodales(nivelFE, marco.receptor_nodos,
                                             cargas_por_losa, marco.key_of_tag,
                                             incluir_sc=False)
        cargas[cod] = cn
    return cargas


def escenarios_EI(marco, audit) -> dict:
    """Escenarios A y B por banda z del EI (misma vista que el checkpoint)."""
    k = marco.key_of_tag
    por_nivel_cc = CC.cargas_por_losa_por_nivel()
    g_full = cargas_G_actual(marco)                    # losas PP + PM.ADIC
    g_pp = _g_losas_solo_pm(marco, por_nivel_cc, pm_kn=0.0)   # solo PP losa
    pm_nodal = {}
    for cod in g_full:
        pm_nodal[cod] = {}
        for t in g_full[cod]:
            a = g_full[cod][t]; b = g_pp[cod].get(t, [0.0] * 6)
            pm_nodal[cod][t] = [a[i] - b[i] for i in range(6)]
    v = _match_vigas(marco, audit["detalle"]["vigas_confirmadas"])
    c = _match_columnas(marco, audit["detalle"]["columnas_confirmadas"])
    m = _match_muros(marco, audit["detalle"]["muros_confirmados"])
    pp_el = aplicar_pp_nodal(marco, v, c, m)["cargas"]   # vigas+cols+muros

    q = json.loads(Q_EI.read_text(encoding="utf-8"))["cargas_nodales_Q"]

    def _comb(*listas):
        out = {}
        for lista in listas:
            for t, f in lista.items():
                acc = out.setdefault(int(t), [0.0] * 6)
                for i in range(6):
                    acc[i] += f[i]
        return out

    combinadas = {}
    for band in COTAS_EI:
        gz = _grupo_z(_flat(g_full), k, COTAS_EI)
        ppz = _grupo_z(_flat(g_pp), k, COTAS_EI)
        pmz = _grupo_z(_flat(pm_nodal), k, COTAS_EI)
        elz = _grupo_z(_flat(pp_el), k, COTAS_EI)
        qz = _grupo_z(_flat(q), k, COTAS_EI)
        a_nodal = _comb(ppz.get(band, {}), elz.get(band, {}),
                        {t: [x * FRACCION_Q for x in f] for t, f in qz.get(band, {}).items()})
        b_nodal = _comb(gz.get(band, {}), elz.get(band, {}),
                        {t: [x * FRACCION_Q for x in f] for t, f in qz.get(band, {}).items()})
        ra, rb = _resumen(a_nodal, k), _resumen(b_nodal, k)
        combinadas[band] = {
            "nivel": ETIQ_EI[band], "z_m": band,
            "PP_losas_kN": round(-sum(f[2] for f in ppz.get(band, {}).values()), 6),
            "PM_ADIC_kN": round(-sum(f[2] for f in pmz.get(band, {}).values()), 6),
            "PP_elementos_kN": round(-sum(f[2] for f in elz.get(band, {}).values()), 6),
            "G_aplicada_kN": round(-sum(f[2] for f in gz.get(band, {}).values())
                                   + round(-sum(f[2] for f in elz.get(band, {}).values()), 6),
                                   6),
            "Q_total_kN": round(-sum(f[2] for f in qz.get(band, {}).values()), 6),
            "W_A_kN": round(ra["carga_kN"], 6),
            "W_B_kN": round(rb["carga_kN"], 6),
            "CM_A_x_m": ra["CM_x_m"], "CM_A_y_m": ra["CM_y_m"],
            "CM_B_x_m": rb["CM_x_m"], "CM_B_y_m": rb["CM_y_m"],
        }

    # vista canonica de 5 pisos (banda -7.01 integrada en CP1S sin duplicar)
    por_piso = {}
    for cod in ("CP1S", "P1", "P2", "P3", "P4"):
        z = {"CP1S": -4.01, "P1": -0.05, "P2": 3.91, "P3": 7.87, "P4": 11.83}[cod]
        full = dict(combinadas[z])
        if cod == "CP1S":
            for campo in ("PP_losas_kN", "PM_ADIC_kN", "PP_elementos_kN",
                          "G_aplicada_kN", "Q_total_kN", "W_A_kN", "W_B_kN"):
                full[campo] = round(full[campo] + combinadas[-7.01][campo], 6)
        full["nivel"] = cod
        full["z_m"] = z
        por_piso[cod] = full

    tot_wa = round(sum(f["W_A_kN"] for f in combinadas.values()), 4)
    tot_wb = round(sum(f["W_B_kN"] for f in combinadas.values()), 4)
    return {"por_banda": {str(b): combinadas[b] for b in sorted(combinadas)},
            "por_piso_5": por_piso,
            "totales": {
                "PP_losas_kN": round(sum(f["PP_losas_kN"] for f in por_piso.values()), 4),
                "PM_ADIC_kN": round(sum(f["PM_ADIC_kN"] for f in por_piso.values()), 4),
                "PP_elementos_kN": round(sum(f["PP_elementos_kN"] for f in por_piso.values()), 4),
                "Q_total_kN": round(sum(f["Q_total_kN"] for f in por_piso.values()), 4),
                "W_A_total_kN": tot_wa, "W_B_total_kN": tot_wb}}


def _componentes_EII_por_nivel(marco) -> dict:
    por = {"EII_CP1S": {"columnas": 0.0, "vigas": 0.0, "muros": 0.0},
           "EII_CP1": {"columnas": 0.0, "vigas": 0.0, "muros": 0.0},
           "EII_CP2": {"columnas": 0.0, "vigas": 0.0, "muros": 0.0},
           "EII_CP3": {"columnas": 0.0, "vigas": 0.0, "muros": 0.0},
           "EII_CP4": {"columnas": 0.0, "vigas": 0.0, "muros": 0.0}}
    for rec in marco.columnas + marco.vigas_elem + marco.muros_elem:
        W = rec["sec_valores"]["A"] * math.hypot(
            rec["u_j"] - rec["u_i"], rec["v_j"] - rec["v_i"], rec["z_j"] - rec["z_i"]) \
            * GAMMA_CONCRETO_KN_M3
        nv = rec.get("nivel")
        if nv not in por:
            por[nv] = {"columnas": 0.0, "vigas": 0.0, "muros": 0.0}
        if rec in marco.muros_elem:
            por[nv]["muros"] += W
        elif rec in marco.columnas:
            por[nv]["columnas"] += W
        else:
            por[nv]["vigas"] += W
    return {k: {kk: round(vv, 6) for kk, vv in v.items()} for k, v in por.items()}


def escenarios_EII(marco) -> dict:
    """Escenarios A y B por banda z del EII (PM.ADIC = 0 -> A == B)."""
    k = marco.key_of_tag
    g = json.loads(G_EII.read_text(encoding="utf-8"))["cargas_nodales"]["G"]
    losas, _rp = marco.losa_tributaria_nodal(incluir_sc=False)
    q = json.loads(Q_EII.read_text(encoding="utf-8"))["cargas_nodales_Q"]["EII"]
    g_int = {int(t): f for t, f in g.items() if int(t) in k}
    los_int = {int(t): f for t, f in losas.items() if int(t) in k}
    q_int = {int(t): f for t, f in q.items() if int(t) in k}
    cotas = sorted({round(k[t][2] / 1e-2) * 1e-2 for t in g_int})
    gz = _grupo_z(g_int, k, cotas)
    lz = _grupo_z(los_int, k, cotas)
    qz = _grupo_z(q_int, k, cotas)
    comp = _componentes_EII_por_nivel(marco)
    cinv = {z: comp.get(ETIQ_EII[z], {"columnas": 0.0, "vigas": 0.0, "muros": 0.0})
            for z in cotas}
    combinadas = {}
    for band in cotas:
        a_nodal = {t: [f[0], f[1], f[2] + FRACCION_Q * qz.get(band, {}).get(t, [0.0] * 6)[2],
                       f[3], f[4], f[5]] for t, f in gz.get(band, {}).items()}
        ra = _resumen(a_nodal, k)
        GL = -sum(f[2] for f in lz.get(band, {}).values())
        GE = -sum(f[2] for f in gz.get(band, {}).values()) - GL
        combinadas[band] = {
            "nivel": ETIQ_EII[band], "z_m": band,
            "PP_losas_kN": round(GL, 6),
            "PM_ADIC_kN": 0.0,
            "PP_columnas_kN": cinv[band]["columnas"],
            "PP_vigas_kN": cinv[band]["vigas"],
            "PP_muros_kN": cinv[band]["muros"],
            "PP_elementos_kN": round(GE, 6),
            "G_aplicada_kN": round(-sum(f[2] for f in gz.get(band, {}).values()), 6),
            "Q_total_kN": round(-sum(f[2] for f in qz.get(band, {}).values()), 6),
            "W_A_kN": round(ra["carga_kN"], 6),
            "W_B_kN": round(ra["carga_kN"], 6),
            "CM_A_x_m": ra["CM_x_m"], "CM_A_y_m": ra["CM_y_m"],
            "CM_B_x_m": ra["CM_x_m"], "CM_B_y_m": ra["CM_y_m"],
        }
    tot_wa = round(sum(f["W_A_kN"] for f in combinadas.values()), 4)
    return {"por_banda": {str(b): combinadas[b] for b in sorted(combinadas)},
            "por_piso_5": {ETIQ_EII[z]: combinadas[z] for z in combinadas},
            "totales": {
                "PP_losas_kN": round(sum(f["PP_losas_kN"] for f in combinadas.values()), 4),
                "PM_ADIC_kN": 0.0,
                "PP_elementos_kN": round(sum(f["PP_elementos_kN"] for f in combinadas.values()), 4),
                "Q_total_kN": round(sum(f["Q_total_kN"] for f in combinadas.values()), 4),
                "W_A_total_kN": tot_wa, "W_B_total_kN": tot_wa}}


def origen_46516_43(ei) -> dict:
    t = ei["totales"]
    pm = t["PM_ADIC_kN"]
    return {
        "valor_en_cuestion_kN": 46516.43,
        "ecuacion": "25.227,73 (G checkpoint = PP_losas + PM_ADIC) + 17.179,23 "
                    "(PP elementos confirmado auditoria v2) = 42.406,96 (G fiel) "
                    "+ 0.5*8218,94463 (4.109,47) = 46.516,43",
        "estructura_componentes_kN": {
            "PP_losas": 14983.58, "PM_ADIC": round(pm, 4),
            "PP_elementos": 17179.23,
            "G_checkpoint": 25227.73, "G_fiel": 42406.96,
            "0_5_Q": round(t["Q_total_kN"] * FRACCION_Q, 4),
            "W_B_igual_46516_43": round(t["W_B_total_kN"], 4)},
        "conclusion": ("46.516,43 kN = PP_total + PM_ADIC + 0.5*Q (escenario B); "
                       "NO es PP_total + 0.5*Q. Su lectura como 'peso propio' exige "
                       "decisión del profesor. El escenario A (PP_total + 0.5*Q) da "
                       "%.2f kN (diferencia = PM_ADIC %.2f kN)."
                       % (round(t["W_A_total_kN"], 4), round(pm, 4)))}


def _ledger_md(ei, eii, origen) -> str:
    l = []
    l.append("# Ledger PP / PM.ADIC / Q por edificio y nivel (MODELO_FIEL_2)")
    l.append("")
    l.append("Regla: `PP` = peso propio de elementos (losas, vigas, columnas, "
             "muros, otros) SIN PM.ADIC. `PM.ADIC` y `Q` en columnas separadas.")
    l.append("")
    for ed, esc, claves in (("EDIFICIO I", ei, ("PP_losas_kN", "PM_ADIC_kN",
                                                 "PP_elementos_kN")),
                            ("EDIFICIO II", eii, ("PP_losas_kN", "PM_ADIC_kN",
                                                  "PP_columnas_kN", "PP_vigas_kN",
                                                  "PP_muros_kN"))):
        l.append("## %s" % ed)
        l.append("| %s |" % " | ".join(("nivel",) + claves + ("Q", "0.5Q",
                                                              "W_A", "W_B")))
        l.append("|" + "---|" * (len(claves) + 5))
        for cod, p in esc["por_piso_5"].items():
            cs = " | ".join("%.4f" % p[c] for c in claves)
            l.append("| %s | %s | %.4f | %.4f | %.4f | %.4f |" % (
                p.get("nivel", cod), cs, p["Q_total_kN"],
                p["Q_total_kN"] * FRACCION_Q, p["W_A_kN"], p["W_B_kN"]))
        t = esc["totales"]
        totes = ["%.4f" % sum(p[c] for p in esc["por_piso_5"].values())
                 for c in claves]
        l.append("| **TOTAL** | %s | %.4f | %.4f | %.4f | %.4f |" % (
            " | ".join(totes), t["Q_total_kN"],
            t["Q_total_kN"] * FRACCION_Q, t["W_A_total_kN"], t["W_B_total_kN"]))
        l.append("")
        if ed == "EDIFICIO II":
            l.append("Nota EII: PM.ADIC = 0 aplicada (catálogo A-F completo en "
                     "PM_ADIC_auditoria_EI_EII.*, todo PM_ADIC_PENDIENTE por "
                     "falta de mapeo familia->viga). Por eso W_A == W_B.")
            l.append("Nota EII (conciliacion): las columnas `PP_columnas/PP_vigas/"
                     "PP_muros` asignan cada elemento completo a su nivel (rec-nivel, "
                     "igual que el ledger v1). La `G_aplicada_kN` reparte en nodos "
                     "50/50 a los extremos, por lo que en un piso `G != losas+col+"
                     "vig+muros` (columnas/muros atraviesan el piso). Las sumas "
                     "totales de ambos criterios coinciden (los 25.970,999 kN).")
        l.append("")
    l.append("## Origen de los 46.516,43 kN del EI")
    l.append("")
    l.append(origen["ecuacion"])
    l.append("")
    l.append("**%s**" % origen["conclusion"])
    return "\n".join(l) + "\n"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    audit = json.loads(AUDIT_EI.read_text(encoding="utf-8"))
    marco = construir_marco_EI()
    ei = escenarios_EI(marco, audit)
    marcoEII = MarcoEII(v031_seccion="V.60/80")
    marcoEII.construir()
    eii = escenarios_EII(marcoEII)
    origen = origen_46516_43(ei)

    checks = []
    checks.append({"ok": abs(ei["totales"]["PP_losas_kN"] - 14983.58) < 0.2,
                   "detalle": "EI PP_losas %.4f vs 14983.58" % ei["totales"]["PP_losas_kN"]})
    checks.append({"ok": abs(ei["totales"]["PM_ADIC_kN"] - 10244.15) < 0.2,
                   "detalle": "EI PM_ADIC %.4f vs 10244.15" % ei["totales"]["PM_ADIC_kN"]})
    checks.append({"ok": abs(ei["totales"]["PP_elementos_kN"] - 17179.23) < 0.2,
                   "detalle": "EI PP_elementos %.4f vs 17179.23" % ei["totales"]["PP_elementos_kN"]})
    checks.append({"ok": abs(ei["totales"]["W_B_total_kN"] - 46516.43) < 0.5,
                   "detalle": "EI W_B %.4f vs 46516.43" % ei["totales"]["W_B_total_kN"]})
    checks.append({"ok": abs(ei["totales"]["W_A_total_kN"]
                             - (ei["totales"]["W_B_total_kN"] - ei["totales"]["PM_ADIC_kN"])) < 0.01,
                   "detalle": "EI W_A = W_B - PM_ADIC"})
    checks.append({"ok": abs(eii["totales"]["W_B_total_kN"] - 28600.71) < 0.5,
                   "detalle": "EII W %.4f vs 28600.71" % eii["totales"]["W_B_total_kN"]})
    checks.append({"ok": abs(eii["totales"]["PM_ADIC_kN"]) < 1e-9,
                   "detalle": "EII PM_ADIC aplicada = 0"})
    checks.append({"ok": abs(sum(f["Q_total_kN"] for f in eii["por_piso_5"].values())
                             - 5259.42883) < 0.05,
                   "detalle": "EII Q total 5259.42883"})
    checks.append({"ok": abs(sum(f["Q_total_kN"] for f in ei["por_piso_5"].values())
                             - 8218.94463) < 0.05,
                   "detalle": "EI Q total 8218.94463"})

    # redondeos para no duplicar la banda -7.01 al integrarla en CP1S
    piso = {cod: {kk: (round(vv, 6) if isinstance(vv, float) else vv)
                  for kk, vv in p.items()} for cod, p in ei["por_piso_5"].items()}
    ei = dict(ei); ei["por_piso_5"] = piso

    payload = {"caso": "ledger_PP_PMADIC_Q", "iteracion": "MODELO_FIEL_2",
               "q_Q_kN_m2": 2.0, "fraccion_Q": 0.5, "g_m_s2": GRAV,
               "EI": ei, "EII": eii,
               "origen_46516_43_kN": origen,
               "clasificacion": {
                   "EI": "REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES",
                   "EII": "REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES"},
               "verificaciones": [{"check": "ck%d" % (i + 1), "ok": c["ok"],
                                   "detalle": c["detalle"]}
                                  for i, c in enumerate(checks)]}
    (OUT / "ledger_PP_PMADIC_Q.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(OUT / "ledger_PP_PMADIC_Q.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["edificio", "nivel", "z_m", "PP_losas_kn", "PM_ADIC_kn",
                    "PP_columnas_kn", "PP_vigas_kn", "PP_muros_kn",
                    "PP_elementos_kn", "Q_kn", "Q50_kn", "W_A_kn", "W_B_kn"])
        for ed, esc, pl in (("EI", ei, ei["por_piso_5"]), ("EII", eii, eii["por_piso_5"])):
            for cod, p in pl.items():
                w.writerow([ed, p.get("nivel", cod), p["z_m"],
                            p.get("PP_losas_kN", 0), p.get("PM_ADIC_kN", 0),
                            p.get("PP_columnas_kN", 0), p.get("PP_vigas_kN", 0),
                            p.get("PP_muros_kN", 0), p.get("PP_elementos_kN", 0),
                            p["Q_total_kN"], round(p["Q_total_kN"] * FRACCION_Q, 6),
                            p["W_A_kN"], p["W_B_kN"]])
    (OUT / "ledger_PP_PMADIC_Q.md").write_text(_ledger_md(ei, eii, origen), encoding="utf-8")
    (OUT / "origen_46516_43_kN.json").write_text(
        json.dumps(origen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "origen_46516_43_kN.md").write_text(
        "# Origen de los 46.516,43 kN del Edificio I\n\n%s\n\n%s\n"
        % (origen["ecuacion"], origen["conclusion"]), encoding="utf-8")

    print(json.dumps({
        "EI_PP_losas_kn": ei["totales"]["PP_losas_kN"],
        "EI_PM_ADIC_kn": ei["totales"]["PM_ADIC_kN"],
        "EI_PP_elementos_kn": ei["totales"]["PP_elementos_kN"],
        "EI_W_A_kn": ei["totales"]["W_A_total_kN"],
        "EI_W_B_kn": ei["totales"]["W_B_total_kN"],
        "EII_W_kn": eii["totales"]["W_B_total_kN"],
        "checks_ok": sum(1 for c in checks if c["ok"]),
        "checks_total": len(checks)},
        ensure_ascii=False, indent=2))
    return 0 if all(c["ok"] for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())