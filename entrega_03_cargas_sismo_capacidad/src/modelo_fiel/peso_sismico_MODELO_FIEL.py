"""Peso sismico actualizado por piso (W_i = PP_fiel + 0.5*Q, q=2.0 kN/m2).

Usa la visualizacion de carga muerta del punto 9 (G_MODELO_FIEL):

  * EI : G_fiel = losas+PM.ADIC (checkpoint) + PP confirmado de la auditoria v2
         (vigas+columnas+muros). Pendientes explicitos: tramos BASE->nivel,
         contencion, V.S.I. y metalicos (no cuantificados) -> rango W_max.
  * EII : G_fiel = reproducible (25.970,999 kN, sin cambios). Pendientes:
         muros 3.328,79 + losas 6,27 + ruteo 417,85 kN -> rango W_max.

Por piso se agrupa la carga NODAL (tag) por cota del nivel, igual que el
checkpoint (`caso_sismico_*`). El CM se obtiene como promedio ponderado de las
coordenadas (x,y) de los nodos cargados por su fraccion de W.

Salidas en modelo_fiel/:
  peso_sismico_MODELO_FIEL.json   contrato por piso y por edificio (con CM)
  peso_sismico_MODELO_FIEL.csv    tabla por piso (EI y EII)
  peso_sismico_MODELO_FIEL.md     resumen legible con rangos
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
Q_EI = RES / "cargas" / "caso_Q_EI_FE.json"
Q_EII = RES / "cargas" / "caso_Q_EII_FE.json"
G_EII = RES / "cargas" / "caso_G_EII_reproducible.json"
AUDIT_EI = RES / "peso_propio_teorico_EDIFICIO_I_v2.json"
LEDGER_EI = OUT / "EI" / "G_EI_MODELO_FIEL_ledger.json"

sys.path.insert(0, str(E3))
sys.path.insert(0, str(REPO / "analisis_estructural" / "edificio_I" / "src"))

from src.modelo_fiel.caso_G_EI_MODELO_FIEL import (  # noqa: E402
    aplicar_pp_nodal,
    cargas_G_actual,
    construir_marco_EI,
    _match_columnas,
    _match_muros,
    _match_vigas,
)
from src.cargas.pipeline_FE_EII import MarcoEII  # noqa: E402

FRACCION_Q = 0.5
TOL = 0.01


def _flat(cargas_por_nivel) -> dict:
    out = {}
    for c in cargas_por_nivel.values():
        for t, f in c.items():
            out[int(t)] = out.get(int(t), [0.0] * 6)
            for i in range(6):
                out[int(t)][i] += f[i]
    return out


def _grupo_z(loads: dict, key_of_tag, cotas=None, tol_z=0.1):
    """loads: {tag: vec}. Devuelve {z_banda: {tag:f}} con cota reportable."""
    if cotas is None:
        cotas = sorted({round(key_of_tag[t][2] / 1e-2) * 1e-2
                        for t in loads})
    grupos = {}
    for t, f in loads.items():
        t = int(t)
        try:
            z = key_of_tag[t][2]
        except KeyError:
            continue
        band = min(cotas, key=lambda c: abs(c - z))
        if abs(band - z) > tol_z:
            band = round(z, 2)
        grupos.setdefault(band, {})[t] = f
    return grupos


def _resumen_grupo(grupos, key_of_tag, etiquetas) -> list:
    """filas por piso: carga total, CM (x,y) del piso y etiqueta."""
    filas = []
    for z, loads in sorted(grupos.items()):
        F = sum(-f[2] for f in loads.values())          # carga total (PP+...)
        wx = sum(-f[2] * key_of_tag[t][0] for t, f in loads.items())
        wy = sum(-f[2] * key_of_tag[t][1] for t, f in loads.items())
        cm = (wx / F, wy / F) if F > 0 else (None, None)
        filas.append({"z_m": z, "n_nodos": len(loads),
                      "carga_total_kN": round(F, 4),
                      "CM_x_m": round(cm[0], 6) if cm[0] is not None else None,
                      "CM_y_m": round(cm[1], 6) if cm[1] is not None else None,
                      "etiqueta": etiquetas.get(z, "nivel z=%.2f" % z)})
    return filas


def _etiq_ei():
    return {-7.01: "sotano nucleo (z -7.01)", -4.01: "CP1S",
            -0.05: "P1", 3.91: "P2", 7.87: "P3", 11.83: "P4"}


def _etiq_eii():
    return {-4.01: "EII_CP1S", -0.05: "EII_CP1", 3.91: "EII_CP2",
            7.87: "EII_CP3", 11.83: "EII_CP4"}


def _merge_pisos(*mapas, etiquetas, frac_Q=FRACCION_Q):
    """fusiona filas de peso por cota usando la union de claves (ceros si falta)."""
    keys = set()
    for mp in mapas:
        keys.update(mp.keys())
    por_piso = {}
    for z in sorted(keys):
        gck = mapas[0].get(z, {})
        gpp = mapas[1].get(z, {})
        gfi = mapas[2].get(z, {})
        qr = mapas[3].get(z, {})
        def _cm(row, key):
            return row.get("CM_%s_m" % key, None)
        g_t = gfi.get("carga_total_kN", 0.0)
        q_t = qr.get("carga_total_kN", 0.0)
        W = g_t + frac_Q * q_t
        Fw = W
        gx, gy = _cm(gfi, "x"), _cm(gfi, "y")
        qx, qy = _cm(qr, "x"), _cm(qr, "y")
        wx = gx * g_t + qx * frac_Q * q_t if gx is not None and qx is not None else None
        wy = gy * g_t + qy * frac_Q * q_t if gy is not None and qy is not None else None
        cm_w = (wx / Fw, wy / Fw) if wx is not None else (None, None)
        por_piso[z] = {
            "nivel": etiquetas.get(z, "nivel z=%.2f" % z), "z_m": z,
            "PP_checkpoint_kN": round(gck.get("carga_total_kN", 0.0), 4),
            "PP_confirmado_nuevo_kN": round(gpp.get("carga_total_kN", 0.0), 4),
            "PP_fiel_kN": round(g_t, 4),
            "Q_total_kN": round(q_t, 4),
            "W_fiel_kN": round(W, 4),
            "CM_G_x_m": gx, "CM_G_y_m": gy,
            "CM_Q_x_m": qx, "CM_Q_y_m": qy,
            "CM_W_x_m": round(cm_w[0], 6) if cm_w[0] is not None else None,
            "CM_W_y_m": round(cm_w[1], 6) if cm_w[1] is not None else None,
        }
    return por_piso


def peso_EI(marco, audit) -> dict:
    g_antes = cargas_G_actual(marco)                       # losas+PM.ADIC
    v = _match_vigas(marco, audit["detalle"]["vigas_confirmadas"])
    c = _match_columnas(marco, audit["detalle"]["columnas_confirmadas"])
    m = _match_muros(marco, audit["detalle"]["muros_confirmados"])
    pp = aplicar_pp_nodal(marco, v, c, m)["cargas"]          # por nivel
    g_fiel_nivel = {}
    for cod in g_antes:
        g_fiel_nivel[cod] = {}
        for t, f in g_antes[cod].items():
            g_fiel_nivel[cod][t] = list(f)
    for cod, cl in pp.items():
        base = g_fiel_nivel.setdefault(cod, {})
        for t, f in cl.items():
            acc = base.setdefault(int(t), [0.0] * 6)
            for i in range(6):
                acc[i] += f[i]
    q = json.loads(Q_EI.read_text(encoding="utf-8"))["cargas_nodales_Q"]
    k = marco.key_of_tag
    et = _etiq_ei()
    map_ck = {r["z_m"]: r for r in _resumen_grupo(_grupo_z(_flat(g_antes), k), k, et)}
    map_pp = {r["z_m"]: r for r in _resumen_grupo(_grupo_z(_flat(pp), k), k, et)}
    map_pp = {z: {"carga_total_kN": 0.0, "n_nodos": 0, "CM_x_m": None, "CM_y_m": None,
                  "z_m": z, "etiqueta": et.get(z, "nivel z=%.2f" % z)}
              for z in map_ck if z not in map_pp} | map_pp
    map_pp = {z: map_pp[z] for z in map_ck}
    map_fi = {r["z_m"]: r for r in _resumen_grupo(_grupo_z(_flat(g_fiel_nivel), k), k, et)}
    map_fi = {z: map_fi.get(z, map_ck[z]) for z in map_ck}
    cotas_g = sorted(map_ck)
    map_q = {r["z_m"]: r for r in _resumen_grupo(_grupo_z(_flat(q), k, cotas_g), k, et)}
    por_piso = _merge_pisos(map_ck, map_pp, map_fi, map_q, etiquetas=et)
    W_total = sum(p["W_fiel_kN"] for p in por_piso.values())
    return {"por_piso": por_piso, "W_total_kN": round(W_total, 4)}


def peso_EII() -> dict:
    marco = MarcoEII(v031_seccion="V.60/80")      # solo lectura de artefactos
    k = marco.key_of_tag
    g = json.loads(G_EII.read_text(encoding="utf-8"))["cargas_nodales"]["G"]
    q = json.loads(Q_EII.read_text(encoding="utf-8"))["cargas_nodales_Q"]["EII"]
    et = _etiq_eii()
    g_int = {int(t): f for t, f in g.items() if int(t) in k}
    cotas_g = sorted({round(k[t][2] / 1e-2) * 1e-2 for t in g_int})
    map_g = {r["z_m"]: r for r in _resumen_grupo(_grupo_z(g_int, k, cotas_g), k, et)}
    map_q = {r["z_m"]: r for r in _resumen_grupo(
        _grupo_z({int(t): f for t, f in q.items() if int(t) in k}, k, cotas_g),
        k, et)}
    map_gg = {z: {"carga_total_kN": 0.0, "n_nodos": 0, "CM_x_m": None, "CM_y_m": None,
                  "z_m": z, "etiqueta": et.get(z, "nivel z=%.2f" % z)}
              for z in map_q if z not in map_g} | map_g
    map_g = {z: map_gg[z] for z in map_q}
    por_piso = _merge_pisos(map_g, map_g, map_g, map_q, etiquetas=et)
    for z, p in por_piso.items():
        p["PP_fiel_kN"] = p["PP_checkpoint_kN"]
        p["PP_confirmado_nuevo_kN"] = p["PP_checkpoint_kN"]
    return {"por_piso": por_piso,
            "W_total_kN": round(sum(p["W_fiel_kN"] for p in por_piso.values()), 4)}


def _rangos(ei, eii) -> dict:
    pend_eii = 3328.79 + 6.27 + 417.85
    pend_ei = 4223.82 + 3675.18 + 554.54   # tramos base (col+muro) + contencion
    return {
        "EI": {
            "W_inferior_kN": ei["W_total_kN"],
            "pendientes_cuantificados_kN": round(pend_ei, 2),
            "W_rango_superior_kN": round(ei["W_total_kN"] + pend_ei, 2),
            "nota": ("no incluye V.S.I. 20/150 ni metalicos (PP no cuantificado); "
                     "son el limite del rango solo con lo cuantificado")},
        "EII": {
            "W_inferior_kN": eii["W_total_kN"],
            "pendientes_cuantificados_kN": round(pend_eii, 2),
            "W_rango_superior_kN": round(eii["W_total_kN"] + pend_eii, 2),
            "nota": "muros 3328.79 + losas 6.27 + ruteo 417.85"},
    }


def _markdown(ei, eii, rangos) -> str:
    l = []
    l.append("# Peso sismico MODELO_FIEL (W_i = PP_fiel + 0.5*Q, q_Q = 2.0 kN/m2)")
    l.append("")
    l.append("- EI : W_total = **%.2f kN** (%.1f MN)" % (ei["W_total_kN"],
                                                         ei["W_total_kN"] / 1e3))
    l.append("- EII: W_total = **%.2f kN** (%.1f MN)" % (eii["W_total_kN"],
                                                         eii["W_total_kN"] / 1e3))
    l.append("- Total (EI+EII) = **%.2f kN** (%.1f MN)"
             % (ei["W_total_kN"] + eii["W_total_kN"],
                (ei["W_total_kN"] + eii["W_total_kN"]) / 1e3))
    l.append("")
    l.append("## EI por piso")
    l.append("| nivel | z (m) | PP_ck (kN) | PP_nuevo (kN) | PP_fiel (kN) | Q (kN) | W (kN) | CM_W x/y (m) |")
    l.append("|---|---|---|---|---|---|---|---|")
    for p in ei["por_piso"].values():
        l.append("| %s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %s / %s |"
                 % (p["nivel"], p["z_m"], p["PP_checkpoint_kN"],
                    p["PP_confirmado_nuevo_kN"], p["PP_fiel_kN"],
                    p["Q_total_kN"], p["W_fiel_kN"],
                    p["CM_W_x_m"], p["CM_W_y_m"]))
    l.append("")
    l.append("## EII por piso")
    l.append("| nivel | z (m) | PP_fiel (kN) | Q (kN) | W (kN) | CM_W x/y (m) |")
    l.append("|---|---|---|---|---|---|")
    for p in eii["por_piso"].values():
        l.append("| %s | %.2f | %.2f | %.2f | %.2f | %s / %s |"
                 % (p["nivel"], p["z_m"], p["PP_fiel_kN"], p["Q_total_kN"],
                    p["W_fiel_kN"], p["CM_W_x_m"], p["CM_W_y_m"]))
    l.append("")
    l.append("## Rango posible")
    l.append("")
    for ed in ("EI", "EII"):
        r = rangos[ed]
        l.append("- %s: W = [%.2f , %.2f] kN (pendientes cuantificados +%.2f)"
                 % (ed, r["W_inferior_kN"], r["W_rango_superior_kN"],
                    r["pendientes_cuantificados_kN"]))
        l.append("  - %s" % r["nota"])
    return "\n".join(l) + "\n"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    audit = json.loads(AUDIT_EI.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_EI.read_text(encoding="utf-8"))
    marco = construir_marco_EI()
    ei = peso_EI(marco, audit)
    eii = peso_EII()
    rangos = _rangos(ei, eii)

    checks = [
        {"check": "equil_g_ei_fiel", "estado": "OK" if abs(
            ei["W_total_kN"] - 0.5 * sum(p["Q_total_kN"]
            for p in ei["por_piso"].values()) - sum(p["PP_fiel_kN"]
            for p in ei["por_piso"].values())) < 0.05 else "ERROR",
         "detalle": "W == PP_fiel + 0.5 Q"},
        {"check": "q_ei_total", "estado": "OK" if abs(
            sum(p["Q_total_kN"] for p in ei["por_piso"].values()) - 8218.94463)
            < TOL else "ERROR",
         "detalle": "Q EI 8218.94463"},
        {"check": "q_eii_total", "estado": "OK" if abs(
            sum(p["Q_total_kN"] for p in eii["por_piso"].values()) - 5259.42883)
            < TOL else "ERROR",
         "detalle": "Q EII 5259.42883"},
        {"check": "pp_eii_total", "estado": "OK" if abs(
            sum(p["PP_fiel_kN"] for p in eii["por_piso"].values()) - 25970.9994)
            < TOL else "ERROR",
         "detalle": "PP EII 25970.9994"},
        {"check": "pp_ei_fiel_total", "estado": "OK" if abs(
            sum(p["PP_fiel_kN"] for p in ei["por_piso"].values()) - 42406.9577)
            < 0.05 else "ERROR",
         "detalle": "PP EI fiel 42406.9577"},
        {"check": "rango_maqueta",
         "estado": "OK" if rangos["EII"]["W_rango_superior_kN"]
         > rangos["EII"]["W_inferior_kN"] else "ERROR",
         "detalle": "W_max > W_min"},
    ]

    payload = {"caso": "peso_sismico", "iteracion": "MODELO_FIEL_1",
               "q_Q_kN_m2": 2.0, "fraccion_Q": 0.5,
               "EI": ei, "EII": eii, "rangos": rangos,
               "pendientes_excluidos": {
                   "EI": "tramos BASE->nivel, contencion, V.S.I. sin material, "
                         "metalicos (no cuantificados)",
                   "EII": "muros/losas/ruteo (cuantificados, ver G_EII_MODELO_FIEL)"},
               "verificaciones": checks}
    (OUT / "peso_sismico_MODELO_FIEL.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(OUT / "peso_sismico_MODELO_FIEL.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["edificio", "nivel", "z_m", "PP_fiel_kN", "Q_kN",
                    "W_kN", "CM_W_x_m", "CM_W_y_m"])
        for ed, d in (("EI", ei), ("EII", eii)):
            for p in d["por_piso"].values():
                w.writerow([ed, p["nivel"], p["z_m"], p["PP_fiel_kN"],
                            p["Q_total_kN"], p["W_fiel_kN"],
                            p["CM_W_x_m"], p["CM_W_y_m"]])
    (OUT / "peso_sismico_MODELO_FIEL.md").write_text(
        _markdown(ei, eii, rangos), encoding="utf-8")

    print(json.dumps({
        "W_total_EI_kN": ei["W_total_kN"],
        "W_total_EII_kN": eii["W_total_kN"],
        "W_total_ambos_kN": round(ei["W_total_kN"] + eii["W_total_kN"], 4),
        "rango_EI_kN": [rangos["EI"]["W_inferior_kN"],
                        rangos["EI"]["W_rango_superior_kN"]],
        "rango_EII_kN": [rangos["EII"]["W_inferior_kN"],
                         rangos["EII"]["W_rango_superior_kN"]],
        "checks_ok": sum(1 for c in checks if c["estado"] == "OK"),
        "checks_total": len(checks)},
        ensure_ascii=False, indent=2))
    return 0 if all(c["estado"] == "OK" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())