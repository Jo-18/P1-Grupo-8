"""Auditoria (Entrega 3): peso propio TEORICO de vigas, columnas y muros del Edificio I.

Modo LECTURA (no modifica el motor FE ni la geometria).

Metodo:
  - Columnas: se agrupan por clase (hormigon / metalico provisional) y posicion en
    planta con tolerancia de vecino 0.35 m, de modo que la MISMA columna fisica que
    aparece en borradores con leve desfase de coordenadas (p.ej. P4 usa v+0.181 m)
    NO se cuenta varias veces. Se conectan soles niveles consecutivos con evidencia;
    tramo base->primer nivel solo cuando no arranca en CP1S.
  - Muros: se agrupan por linea (ex1, ex2) con la misma tolerancia; PP = t x L x h
    (los 2 montantes t x L/2 del FE suman el area total t x L, sin duplicar).
  - Vigas: 1 registro por id en su nivel; longitud = polilinea de pts del candidato.
Densidades: concreto 2500 kg/m3 x 0.00980665 = 24.5166 kN/m3;
            acero provisional (P.M./V.M./V.S.I.) 7850 kg/m3 x 0.00980665 = 76.982 kN/m3
            (hipotesis de perfil, seccion provisional).
Salida: results/peso_propio_teorico_EDIFICIO_I.json
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FE_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"
sys.path.insert(0, str(FE_SRC))

from analisis.fe import config_edificios as CFG  # noqa: E402
from analisis.fe import geometria_fe as GF  # noqa: E402

DENSIDAD_CONCRETO_KGF_M3 = CFG.DENSIDAD_KGF_M3
GRAV = CFG.GRAV_KGF_TO_KN
GAMMA_CONCRETO = DENSIDAD_CONCRETO_KGF_M3 * GRAV      # 24.5166
GAMMA_ACERO = 7850.0 * GRAV


def _es_metalico(nombre: str) -> bool:
    n = (nombre or "").strip().upper()
    return (n.startswith("V.M") or n.startswith("P.M")
            or "V.S.I." in n or "M.I." in n)


def _parsecm(s, div):
    m = re.search(r"(\d+)\s*[/xX]\s*(\d+)", s.replace(" ", ""))
    if not m:
        return None
    return int(m.group(1)) / div, int(m.group(2)) / div


def seccion_viga(nombre: str):
    n = (nombre or "").strip().upper()
    if _es_metalico(n):
        bh = _parsecm(n, 1000.0)
        b, h = bh if bh else (CFG.EDIFICIO_I.v_s_i_provisional[0] / 100.0,
                              CFG.EDIFICIO_I.v_s_i_provisional[1] / 100.0)
        return b * h, b, h, True
    bh = _parsecm(n, 100.0)
    if not bh:
        return None
    b, h = bh
    return b * h, b, h, False


def seccion_columna(nombre: str):
    n = (nombre or "").strip().upper()
    metalico = _es_metalico(n)
    if metalico:
        m = re.search(r"(\d+)\s*[xX]\s*(\d+)", n.replace(" ", ""))
        b = int(m.group(1)) / 1000.0 if m else CFG.EDIFICIO_I.p_m_i_provisional_cm / 100.0
        return b * b, b, b, True
    m = re.search(r"(\d+)\s*[/xX]\s*(\d+)", n.replace(" ", ""))
    if not m:
        return None
    b = int(m.group(1)) / 100.0
    return b * b, b, b, False


def _dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def main():
    niveles = GF.cargar_todos()
    cotas = CFG.EDIFICIO_I.cotas_nivel
    base_z = cotas[CFG.EDIFICIO_I.nivel_base]
    orden = list(CFG.EDIFICIO_I.niveles_orden)
    tol = 0.35

    # ================= VIGAS por nivel =================
    vg = {}
    for cod in orden:
        acc = 0.0
        det = []
        for v in niveles[cod].vigas:
            if not v.get("recibe_losa", True):
                pass
            sv = seccion_viga(v["seccion"])
            if sv is None:
                continue
            A, b, h, metalico = sv
            pts = v.get("pts") or []
            L = sum(math.hypot(x2 - x1, y2 - y1)
                    for (x1, y1), (x2, y2) in zip(pts, pts[1:]))
            gam = GAMMA_ACERO if metalico else GAMMA_CONCRETO
            w = L * A * gam
            acc += w
            det.append({"id": v["id"], "seccion": v["seccion"],
                        "L_m": round(L, 4), "A_m2": round(A, 6),
                        "metalico": metalico, "pp_kN": round(w, 4)})
        vg[cod] = {"pp_kN": round(acc, 4), "n_vigas": len(det), "detalle": det}

    # ================= COLUMNAS (agrupacion por clase+vecino 0.35 m) =========
    grupos_col = []   # {pos, clase, sec_por_nivel, niveles}
    for cod in orden:
        for c in niveles[cod].columnas:
            pos = (c["u"], c["v"])
            clase = "metal" if _es_metalico(c["seccion"]) else "hormigon"
            hit = None
            for g in grupos_col:
                if g["clase"] != clase:
                    continue
                d = _dist(pos, g["pos"])
                if d <= tol:
                    if hit is not None and d < hit[0]:
                        hit = (d, g)
                    elif hit is None:
                        hit = (d, g)
            if hit is None:
                g = {"pos": pos, "clase": clase,
                     "sec_por_nivel": {cod: c["seccion"]}, "niveles": [cod]}
                grupos_col.append(g)
            else:
                g = hit[1]
                g["sec_por_nivel"][cod] = c["seccion"]
                if cod not in g["niveles"]:
                    g["niveles"].append(cod)

    col_total = 0.0
    col_por_nivel = {cod: {"pp_kN": 0.0, "n_tramos": 0} for cod in orden}
    col_hip_base = {"pp_kN": 0.0, "n_tramos": 0}
    col_metal_total = 0.0
    det_col = []
    n_grupos = 0
    for g in grupos_col:
        nive = sorted(g["niveles"], key=cotas.__getitem__)
        n_grupos += 1
        for a, b in zip(nive, nive[1:]):
            sc = seccion_columna(g["sec_por_nivel"][b])
            h = cotas[b] - cotas[a]
            gam = GAMMA_ACERO if sc[3] else GAMMA_CONCRETO
            w = h * sc[0] * gam
            col_total += w
            if sc[3]:
                col_metal_total += w
            col_por_nivel[b]["pp_kN"] += w
            col_por_nivel[b]["n_tramos"] += 1
            det_col.append({"pos": list(g["pos"]), "clase": g["clase"],
                            "tramo": f"{a}->{b}", "h_m": round(h, 4),
                            "seccion": g["sec_por_nivel"][b],
                            "A_m2": round(sc[0], 6), "pp_kN": round(w, 4)})
        if nive and nive[0] != CFG.EDIFICIO_I.nivel_base:
            sc = seccion_columna(g["sec_por_nivel"][nive[0]])
            h = cotas[nive[0]] - base_z
            gam = GAMMA_ACERO if sc[3] else GAMMA_CONCRETO
            w = h * sc[0] * gam
            col_total += w
            if sc[3]:
                col_metal_total += w
            col_hip_base["pp_kN"] += w
            col_hip_base["n_tramos"] += 1
            det_col.append({"pos": list(g["pos"]), "clase": g["clase"],
                            "tramo": f"BASE->{nive[0]}", "h_m": round(h, 4),
                            "seccion": g["sec_por_nivel"][nive[0]],
                            "A_m2": round(sc[0], 6), "pp_kN": round(w, 4),
                            "hipotesis": True})

    # ================= MUROS (agrupacion por linea + vecino 0.35 m) =========
    grupos_muro = []   # {e1, e2, espesor, niveles, espesores}
    for cod in orden:
        for m in niveles[cod].muros:
            if m["id"] in CFG.EDIFICIO_I.muros_contencion_sotano:
                continue
            e1, e2 = (m["ua"], m["va"]), (m["ub"], m["vb"])
            if _dist(e1, e2) > 0:  # ordenar por tupla
                if (e1 + e2) > (e2 + e1):
                    e1, e2 = e2, e1
            hit = None
            for g in grupos_muro:
                if _dist(e1, g["e1"]) <= tol and _dist(e2, g["e2"]) <= tol:
                    hit = g
                    break
            if hit is None:
                g = {"e1": e1, "e2": e2, "espesores": {cod: m["espesor"]},
                     "niveles": [cod]}
                grupos_muro.append(g)
            else:
                hit["espesores"][cod] = m["espesor"]
                if cod not in hit["niveles"]:
                    hit["niveles"].append(cod)

    mu_total = 0.0
    mu_por_nivel = {cod: {"pp_kN": 0.0, "n_paneles": 0} for cod in orden}
    mu_hip_base = {"pp_kN": 0.0, "n_paneles": 0}
    det_mu = []
    for g in grupos_muro:
        L = _dist(g["e1"], g["e2"])
        if L < 1e-6:
            continue
        nive = sorted(g["niveles"], key=cotas.__getitem__)
        for a, b in zip(nive, nive[1:]):
            t = g["espesores"].get(b, g["espesores"].get(a))
            h = cotas[b] - cotas[a]
            w = t * L * h * GAMMA_CONCRETO
            mu_total += w
            mu_por_nivel[b]["pp_kN"] += w
            mu_por_nivel[b]["n_paneles"] += 1
            det_mu.append({"linea": [list(g["e1"]), list(g["e2"])],
                           "tramo": f"{a}->{b}", "e_m": t, "L_m": round(L, 4),
                           "h_m": round(h, 4), "pp_kN": round(w, 4)})
        if nive and nive[0] != CFG.EDIFICIO_I.nivel_base:
            t = g["espesores"].get(nive[0])
            h = cotas[nive[0]] - base_z
            w = t * L * h * GAMMA_CONCRETO
            mu_total += w
            mu_hip_base["pp_kN"] += w
            mu_hip_base["n_paneles"] += 1
            det_mu.append({"linea": [list(g["e1"]), list(g["e2"])],
                           "tramo": f"BASE->{nive[0]}", "e_m": t,
                           "L_m": round(L, 4), "h_m": round(h, 4),
                           "pp_kN": round(w, 4), "hipotesis": True})

    # ================= MUROS DE CONTENCION =================
    cont = {}
    for mid, mc in CFG.EDIFICIO_I.muros_contencion_sotano.items():
        panel = 5.0
        for m in niveles[CFG.EDIFICIO_I.nivel_basamento_sin_diafragma].muros:
            if m["id"] == mid:
                panel = abs(m["vb"] - m["va"])
        h = cotas[CFG.EDIFICIO_I.nivel_base] \
            - (cotas[CFG.EDIFICIO_I.nivel_base] - CFG.EDIFICIO_I.h_sotano_hipotesis_m)
        z_cim = cotas[CFG.EDIFICIO_I.nivel_base] - CFG.EDIFICIO_I.h_sotano_hipotesis_m
        hp = cotas[CFG.EDIFICIO_I.nivel_base] - z_cim
        w = mc["e"] * panel * hp * GAMMA_CONCRETO
        cont[mid] = {"e_m": mc["e"], "panel_m": round(panel, 4),
                     "h_m": round(hp, 4), "pp_kN": round(w, 4), "hipotesis": True}
    cont_total = sum(v["pp_kN"] for v in cont.values())

    vigas_total = sum(v["pp_kN"] for v in vg.values())
    vigas_metal = sum(d["pp_kN"] for v in vg.values()
                      for d in v["detalle"] if d["metalico"])
    total = vigas_total + col_total + mu_total + cont_total

    out = {
        "edificio": "I", "modo": "auditoria (solo lectura; no aplicado al FE)",
        "densidades": {"concreto_kN_m3": GAMMA_CONCRETO,
                       "acero_provisional_kN_m3": GAMMA_ACERO},
        "tol_agrupacion_m": tol,
        "verificacion_no_duplicacion": (
            "Columnas: 1 grupo por clase+posicion fisica (tol 0.35 m). Esto evita que "
            "la misma columna contada en borradores con desfase de coordenadas (P4 "
            "v+0.181 m) se cuente en dos tramos base->P4 distintos: la altura total se "
            "reparte en los entrepisos consecutivos una sola vez. Muros: 1 grupo por "
            "linea; los 2 montantes del FE (t x L/2) suman t x L (area total, 1 vez). "
            "Vigas: 1 registro por id y nivel, longitud = polilinea del candidato."),
        "PP_vigas_kN": round(vigas_total, 4),
        "PP_columnas_kN": round(col_total, 4),
        "PP_muros_kN": round(mu_total, 4),
        "PP_muros_contencion_kN": round(cont_total, 4),
        "PP_elementos_TOTAL_kN": round(total, 4),
        "desglose_metalico": {
            "vigas_metalicas_provisionales_kN": round(vigas_metal, 4),
            "columnas_metalicas_provisionales_kN": round(col_metal_total, 4)},
        "n_vigas": sum(v["n_vigas"] for v in vg.values()),
        "n_grupos_columna": n_grupos,
        "n_grupos_muro": len(grupos_muro),
        "columna_tramo_base_hipotesis_kN": round(col_hip_base["pp_kN"], 4),
        "muro_tramo_base_hipotesis_kN": round(mu_hip_base["pp_kN"], 4),
        "por_nivel": {
            "vigas": {k: {"pp_kN": v["pp_kN"], "n": v["n_vigas"]}
                      for k, v in vg.items()},
            "columnas": {k: {"pp_kN": round(v["pp_kN"], 4), "n_tramos": v["n_tramos"]}
                         for k, v in col_por_nivel.items()},
            "muros": {k: {"pp_kN": round(v["pp_kN"], 4), "n_paneles": v["n_paneles"]}
                      for k, v in mu_por_nivel.items()},
        },
        "detalle": {"vigas": [d for v in vg.values() for d in v["detalle"]],
                    "columnas": det_col, "muros": det_mu,
                    "muros_contencion": cont},
    }
    out_dir = Path(__file__).resolve().parent.parent / "results"
    out_dir.mkdir(exist_ok=True)
    p = out_dir / "peso_propio_teorico_EDIFICIO_I.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "PP_vigas_kN": out["PP_vigas_kN"],
        "PP_columnas_kN": out["PP_columnas_kN"],
        "PP_muros_kN": out["PP_muros_kN"],
        "PP_muros_contencion_kN": out["PP_muros_contencion_kN"],
        "PP_elementos_TOTAL_kN": out["PP_elementos_TOTAL_kN"],
        "metalico_vigas_kN": round(vigas_metal, 4),
        "metalico_columnas_kN": round(col_metal_total, 4),
        "n_vigas": out["n_vigas"], "n_grupos_columna": n_grupos,
        "n_grupos_muro": len(grupos_muro),
        "por_nivel": out["por_nivel"],
        "hip_base_col_kN": out["columna_tramo_base_hipotesis_kN"],
        "hip_base_muro_kN": out["muro_tramo_base_hipotesis_kN"],
        "escrito_en": str(p),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()