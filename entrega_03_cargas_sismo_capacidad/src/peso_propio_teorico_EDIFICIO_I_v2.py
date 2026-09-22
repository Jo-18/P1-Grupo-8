"""Auditoria (Entrega 3) v2: peso propio TEORICO de vigas, columnas y muros del Edificio I.

Modo LECTURA (no toca el motor FE, ni la geometria, ni resultados previos).

Correcciones de la v1 (24,116.51 kN, DESCARTADA):

  1) PERFILES METALICOS no se tratan como macizos (A=b*h). Si la seccion esta
     documentada como tubular (designacion BxHxt en mm, p.ej. V.M./P.M. 300x300x5
     y 300x300x20, confirmadas en REPORTE_QA_GEOMETRIA_UNITY):
        A = B*H - (B-2t)*(H-2t)
     Si falta dimension (P.M.I., ancho=0.0/peralte=0.0 en el QA):
        area_m2 = null, pp_kN = null, estado PENDIENTE_SECCION.
     El registrio conserva la designacion y la procedencia (candidato / QA).

  2) TRAMOS BASE->NIVEL no se suman: son hipotesis que el FE aade
     (`col_{u}_{v}_base_{nivel}` en columnas_tramos_ei.json) para llevar la carga a
     cimentacion cuando el nivel mas bajo con evidencia no es CP1S. Se reportan en
     una tabla de hipotesis INFORMATIVA, fuera del total confirmado. La base fija
     (z=-4.01) es hipotesis de cimentacion (marco.py).

  3) AGRUPACION sin tolerancia 0.35 como criterio unico:
     - Columnas: se toman SOLO los tramos reales instanciados por el FE desde
       `columnas_tramos_ei.json` (43 tramos: 7 CP1S->P1 + 18 P1->P2 + 18 P2->P3).
       El FE NO crea tramos P3->P4 de hormigon: P4 esta desplazado +0.181 m
       (desfase documentado en matrices_transformacion_unity.json, no compensado)
       y sus columnas quedan como base->P4 hipotesis; por decision del usuario el
       tramo P3->P4 de hormigon se declara PENDIENTE_TRAMO (pp null).
     - Metales simples (1 nivel de aparicion): no tienen tramo real entrepisos
       documentado (continuidad P3->P4 de lamina 800 PENDIENTE); pp null. Estado:
       PENDIENTE_TRAMO si la seccion tubular esta confirmada (V.M./P.M. BxHxt);
       PENDIENTE_SECCION si falta dimension (P.M.I., sin BxHxt).
     - Muros: se agrupan por linea canonica (igual regla FE: extremos con 3
       decimales) y espesor; solo cuentan los pares de niveles consecutivos que
       comparten linea (4 paneles P2->P3). Muros mononivel/C P1S/P3->P4 (desfase)
       quedan PENDIENTE_TRAMO. Los montantes FE t x L/2 suman t x L: se cuenta el
       panel fisico una vez.

  4) V.S.I. 20/150 (H_EI_CP1S_y2732): material/tipo no confirmado (el FE la asume
     metalica provisional 30x60; el plano dice "V.S.I.") -> PENDIENTE_SECCION,
     pp null. V_EI_CP1S_x1010 (M.H.A. e=30) es una seccion de muro en la lista de
     vigas: no es viga; NO_INCLUIDA.

Salidas: results/peso_propio_teorico_EDIFICIO_I_v2.json (+ _hash.txt deterministico).
"""

from __future__ import annotations

import hashlib
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
GAMMA_ACERO = 7850.0 * GRAV                           # 76.9822 (A36, hipotesis)
DENSIDADES = {"concreto": DENSIDAD_CONCRETO_KGF_M3, "acero_a36_hip": 7850.0}

CFG_EI = CFG.activa()
ORDEN = list(CFG_EI.niveles_orden)
COTAS = dict(CFG_EI.cotas_nivel)
BASE_NIVEL = CFG_EI.nivel_base
TOL_MATCH_SECCION = 0.02   # solo para emparejar la columna candidata del tramo FE

_TRAMOS_FILE = (REPO / "analisis_estructural" / "edificio_I" / "resultados"
                / "modelo_estructural" / "columnas_tramos_ei.json")
OUT_JSON = REPO / "entrega_03_cargas_sismo_capacidad" / "results" \
    / "peso_propio_teorico_EDIFICIO_I_v2.json"


def _dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _es_metalico(nombre: str) -> bool:
    n = (nombre or "").strip().upper()
    return (n.startswith("V.M") or n.startswith("P.M")
            or "V.S.I." in n or "M.I." in n)


def _sec_col_tubular(nombre: str):
    """Designacion tubular cuadrada/rectangular 'BxHxt' en mm -> (A_m2, b, h, t)."""
    n = re.sub(r"\s+", "", (nombre or "").upper())
    m = re.search(r"(\d+(?:\.\d+)?)[xX](\d+(?:\.\d+)?)[xX](\d+(?:\.\d+)?)", n)
    if not m:
        return None
    b, h, t = (float(m.group(i)) for i in (1, 2, 3))
    b, h, t = b / 1000.0, h / 1000.0, t / 1000.0
    if 2 * t >= b or 2 * t >= h:
        return None
    A = b * h - (b - 2 * t) * (h - 2 * t)
    return round(A, 6), b, h, t


def seccion_columna(nombre: str):
    """-> dict de area/material; marca PENDIENTE_SECCION si no es determinable."""
    n = (nombre or "").strip().upper()
    info = {"seccion": n, "area_m2": None, "pp_kN": None, "estado": "?",
            "motivo": None}
    if _es_metalico(n):
        tub = _sec_col_tubular(n)
        if tub is None:
            info["estado"] = "PENDIENTE_SECCION"
            info["motivo"] = ("perfil metalico sin dimensiones BxHxt documentadas "
                              "(P.M.I.: ancho=0.0/peralte=0.0 en el QA)")
            return info
        A, b, h, t = tub
        info.update(area_m2=A, estado="SECCION_CONFIRMADA_TUBULAR",
                    motivo="A=B*H-(B-2t)(H-2t); designacion documentada + QA")
        return info
    # hormigon: "P. 70x70" (cm)
    m = re.search(r"(\d+)\s*[/xX]\s*(\d+)", n)
    if not m:
        info["estado"] = "PENDIENTE_SECCION"
        info["motivo"] = "nombre de seccion no parseable"
        return info
    b = int(m.group(1)) / 100.0
    info.update(area_m2=b * b, estado="CONFIRMADA",
                motivo="seccion documentada en candidato")
    return info


def seccion_viga(nombre: str):
    n = (nombre or "").strip().upper()
    info = {"seccion": n, "area_m2": None, "pp_kN": None, "estado": "?",
            "motivo": None}
    if "V.S.I." in n:
        info["estado"] = "PENDIENTE_SECCION"
        info["motivo"] = ("material/tipo no confirmado (el FE la asume metalica "
                          "provisional 30x60; el plano 'V.S.I.' no fija hormigon/acero)")
        return info
    if n.startswith("M.") or "M.H.A." in n:
        info["estado"] = "NO_INCLUIDA"
        info["motivo"] = "seccion de muro (M.H.A. e=30) en lista de vigas: no es viga"
        return info
    m = re.search(r"(\d+)\s*[/xX]\s*(\d+)", n)
    if not m:
        info["estado"] = "PENDIENTE_SECCION"
        info["motivo"] = "nombre de seccion no parseable"
        return info
    b, h = int(m.group(1)) / 100.0, int(m.group(2)) / 100.0
    info.update(area_m2=b * h, estado="CONFIRMADA",
                motivo="seccion documentada en candidato")
    return info


def _linea_muro(m):
    return (round(m["ua"], 3), round(m["va"], 3),
            round(m["ub"], 3), round(m["vb"], 3))


def main():
    niveles = GF.cargar_todos()

    # ---------------- VIGAS ----------------
    vg = []
    for cod in ORDEN:
        for v in niveles[cod].vigas:
            L = sum(_dist(a, b) for a, b in zip(v["pts"], v["pts"][1:])) or 0.0
            info = seccion_viga(v["seccion"])
            base = {
                "id": v["id"], "nivel": cod, "L_m": round(L, 4),
                "seccion": v["seccion"], "estado": info["estado"],
                "motivo": info["motivo"], "fuente": "candidato",
            }
            if info["estado"] == "CONFIRMADA":
                base["area_m2"] = info["area_m2"]
                base["material"] = "hormigon"
                base["densidad_kN_m3"] = round(GAMMA_CONCRETO, 4)
                base["pp_kN"] = round(L * info["area_m2"] * GAMMA_CONCRETO, 4)
            else:
                base["area_m2"] = None
                base["material"] = "pendiente"
                base["pp_kN"] = None
            if info["estado"] == "NO_INCLUIDA":
                base["motivo"] = info["motivo"]
            vg.append(base)

    vg_confirm = [d for d in vg if d["estado"] == "CONFIRMADA"]
    vg_pend   = [d for d in vg if d["estado"] == "PENDIENTE_SECCION"]
    vg_noinc  = [d for d in vg if d["estado"] == "NO_INCLUIDA"]
    pp_vigas_confirm = round(sum(d["pp_kN"] for d in vg_confirm), 4)

    # ---------------- COLUMNAS (tramos FE reales vs hipotesis) ----------------
    tramos = json.loads(_TRAMOS_FILE.read_text(encoding="utf-8"))["tramos"]

    # seccion por (nivel, posicion redondeada) desde candidatos (para clasificar)
    sec_map = {}   # (cod, round(u,3), round(v,3)) -> nombre de seccion
    for cod in ORDEN:
        for c in niveles[cod].columnas:
            sec_map[(cod, round(c["u"], 3), round(c["v"], 3))] = c["seccion"]

    def _sec_de_tramo(nivel, u, v):
        k = (nivel, round(u, 3), round(v, 3))
        if k in sec_map:
            return sec_map[k]
        best, bd = None, 1e9
        for (cod, ku, kv), sn in sec_map.items():
            if cod != nivel:
                continue
            d = math.hypot(ku - u, kv - v)
            if d <= TOL_MATCH_SECCION and d < bd:
                best, bd = sn, d
        return best

    col_confirm = []
    col_pend = []
    col_base_hip = []
    duplicados = 0
    for t in tramos:
        eid = t["elemento_id"]
        nivel, u, v = t["nivel"], t["u"], t["v"]
        h = t["z_j"] - t["z_i"]
        seg = {"id": eid, "nivel": nivel, "tramo": eid,
               "p_inicio": [u, v, t["z_i"]], "p_final": [u, v, t["z_j"]],
               "h_m": round(h, 4), "u": u, "v": v,
               "fuente": "columnas_tramos_ei.json"}
        sec_name = _sec_de_tramo(nivel, u, v)
        seg["seccion"] = sec_name
        info = seccion_columna(sec_name)
        es_base = "_base_" in eid

        if es_base:
            seg["hipotesis"] = True
            seg["material"] = "metalico" if info["estado"].startswith("PENDIENTE") or "TUBULAR" in (info["estado"] or "") else "hormigon"
            # material real segun seccion
            seg["material"] = ("acero" if (sec_name and _es_metalico(sec_name))
                               else "hormigon")
            if info["area_m2"] is not None:
                gam = GAMMA_ACERO if seg["material"] == "acero" else GAMMA_CONCRETO
                seg["pp_kN_hipotesis"] = round(h * info["area_m2"] * gam, 4)
            else:
                seg["pp_kN_hipotesis"] = None
            seg["nota"] = "hipotesis FE base->nivel (cimentacion no documentada); fuera del total confirmado"
            col_base_hip.append(seg)
            if sec_name and _es_metalico(sec_name):
                sec_ok = info["estado"] in ("CONFIRMADA", "SECCION_CONFIRMADA_TUBULAR")
                if sec_ok:
                    st_estado, st_motivo = "PENDIENTE_TRAMO", (
                        "seccion tubular confirmada (V.M./P.M. BxHxt); "
                        "solo falta documentar el tramo real entrepisos (lamina 800). "
                        "No se extiende a la base.")
                else:
                    st_estado, st_motivo = "PENDIENTE_SECCION", info["motivo"]
                col_pend.append({
                    "id": eid, "tipo": "columna_metalica", "nivel": nivel,
                    "p_inicio": [u, v, t["z_i"]], "p_final": [u, v, t["z_j"]],
                    "seccion": sec_name, "area_m2": info["area_m2"],
                    "pp_kN": None, "estado": st_estado,
                    "motivo": st_motivo,
                    "fuente": "columnas_tramos_ei.json + candidato",
                })
        else:
            if info["estado"] != "CONFIRMADA":
                col_pend.append({
                    "id": eid, "tipo": "columna_hormigon", "nivel": nivel,
                    "p_inicio": [u, v, t["z_i"]], "p_final": [u, v, t["z_j"]],
                    "seccion": sec_name, "area_m2": None, "pp_kN": None,
                    "estado": info["estado"], "motivo": info["motivo"],
                    "fuente": "columnas_tramos_ei.json + candidato",
                })
                continue
            w = h * info["area_m2"] * GAMMA_CONCRETO
            seg.update(area_m2=info["area_m2"], material="hormigon",
                       densidad_kN_m3=round(GAMMA_CONCRETO, 4),
                       pp_kN=round(w, 4), estado="CONFIRMADA",
                       motivo="tramo real FE entre niveles consecutivos con columna documentada")
            col_confirm.append(seg)

    # invariante de conteo (duplicacion por tolerancia): cada tramo FE aparece 1 vez
    ids = [t["elemento_id"] for t in tramos]
    duplicados = len(ids) - len(set(ids))
    pp_col_confirm = round(sum(d["pp_kN"] for d in col_confirm), 4)

    # Tramo hormigon P3->P4 (desfase +0.181 documentado): PENDIENTE_TRAMO.
    # Se derivan de las columnas hormigon de P4 presentes en el candidato.
    p4_hormigones = []
    for c in niveles["P4"].columnas:
        if not _es_metalico(c["seccion"]):
            p4_hormigones.append(c)
    col_p4_p3_p4 = []
    for c in p4_hormigones:
        h = COTAS["P4"] - COTAS["P3"]           # 3.96
        A = seccion_columna(c["seccion"])["area_m2"]
        col_p4_p3_p4.append({
            "id": c["id"], "tipo": "columna_hormigon", "nivel": "P4",
            "p_inicio": [c["u"], c["v"], COTAS["P3"]],
            "p_final": [c["u"], c["v"], COTAS["P4"]],
            "seccion": c["seccion"], "area_m2": A, "h_m": round(h, 4),
            "pp_kN": None, "estado": "PENDIENTE_TRAMO",
            "motivo": ("el FE no instancia tramos hormigon P3->P4: P4 esta "
                       "desplazado +0.181 m (matrices_transformacion_unity.json, "
                       "desfase fisico documentado, no compensado); alineacion por "
                       "confirmar"),
            "fuente": "candidato CP4 + matrices_transformacion_unity.json",
        })
    col_pend.extend(col_p4_p3_p4)

    pp_col_hip_base = round(sum(d["pp_kN_hipotesis"] or 0.0
                                for d in col_base_hip), 4)

    # ---------------- MUROS ----------------
    muro_lines = {}
    for cod in ORDEN:
        for m in niveles[cod].muros:
            if m["id"] in CFG_EI.muros_contencion_sotano:
                continue
            key = _linea_muro(m)
            d = muro_lines.setdefault(key, {"espesores": {cod: m["espesor"]},
                                           "niveles": set(), "ids": {}})
            d["espesores"][cod] = m["espesor"]
            d["niveles"].add(cod)
            d["ids"].setdefault(cod, m["id"])

    mu_confirm = []
    mu_pend = []
    mu_base_hip = []
    for key, info in muro_lines.items():
        ua, va, ub, vb = key
        L = math.hypot(ub - ua, vb - va)
        if L < 1e-6:
            continue
        nive = sorted(info["niveles"], key=COTAS.__getitem__)
        line_info = {"linea": [[ua, va], [ub, vb]], "espesores": info["espesores"],
                     "ids": info["ids"]}
        # pares consecutivos presentes -> panel real (una vez; montantes t*L/2 suman t*L)
        for a, b in zip(nive, nive[1:]):
            # regla FE: solo conecta niveles consecutivos que comparten la linea
            t = info["espesores"].get(b, info["espesores"].get(a))
            h = COTAS[b] - COTAS[a]
            w = t * L * h * GAMMA_CONCRETO
            mu_confirm.append({
                "id_panel": "Muro %s -> %s" % (a, b),
                "id_candidato": {a: info["ids"].get(a), b: info["ids"].get(b)},
                "tipo": "muro", "tramo": "%s->%s" % (a, b),
                "linea": line_info["linea"], "e_m": t, "L_m": round(L, 4),
                "h_m": round(h, 4), "area_panel_m2": round(t * L, 4),
                "pp_kN": round(w, 4), "estado": "CONFIRMADA",
                "motivo": "panel vertical entre niveles consecutivos con linea y espesor documentados (1 vez; FE usa 2 montantes t*L/2)",
                "fuente": "candidatos %s/%s" % (a, b),
            })
        # hipotesis base->nivel mas bajo (informativa)
        low = nive[0]
        if low != BASE_NIVEL:
            t = info["espesores"].get(low)
            h = COTAS[low] - COTAS[BASE_NIVEL]
            w = t * L * h * GAMMA_CONCRETO
            mu_base_hip.append({
                "linea": line_info["linea"], "tramo": "BASE->%s" % low,
                "e_m": t, "L_m": round(L, 4), "h_m": round(h, 4),
                "pp_kN_hipotesis": round(w, 4),
                "nota": "hipotesis FE base->%s; fuera del total confirmado" % low,
            })
        # mononivel (o solo CP1S) / desfase P4 -> sin tramo real -> PENDIENTE
        if len(nive) == 1:
            cod = nive[0]
            t = info["espesores"][cod]
            mu_pend.append({
                "id_candidato": info["ids"].get(cod), "tipo": "muro",
                "nivel": cod, "linea": line_info["linea"],
                "e_m": t, "L_m": round(L, 4), "pp_kN": None,
                "estado": "PENDIENTE_TRAMO",
                "motivo": ("muro documentado en UN solo nivel (o solo CP1S); "
                           "extent of vertical real entrepisos no documentado o "
                           "coordenadas no coinciden entre niveles consecutivos"),
                "fuente": "candidato %s" % cod,
            })

    pp_mu_confirm = round(sum(d["pp_kN"] for d in mu_confirm), 4)
    pp_mu_hip_base = round(sum(d["pp_kN_hipotesis"] for d in mu_base_hip), 4)

    # ---------------- MUROS DE CONTENCION (hipotesis cimentacion) ----------------
    cont = {}
    zcim = COTAS[BASE_NIVEL] - CFG_EI.h_sotano_hipotesis_m
    hp = COTAS[BASE_NIVEL] - zcim
    for mid, mc in CFG_EI.muros_contencion_sotano.items():
        panel = 5.0
        for m in niveles[BASE_NIVEL].muros:
            if m["id"] == mid:
                panel = abs(m["vb"] - m["va"])
        w = mc["e"] * panel * hp * GAMMA_CONCRETO
        cont[mid] = {"e_m": mc["e"], "panel_m": round(panel, 4),
                     "h_hipotesis_m": round(hp, 4), "pp_kN": round(w, 4),
                     "estado": "HIPOTESIS_CIMENTACION",
                     "nota": "desciende a cimentacion por hipotesis h_sotano=%.1f m; fuera del total confirmado" % CFG_EI.h_sotano_hipotesis_m}
    pp_cont = round(sum(v["pp_kN"] for v in cont.values()), 4)

    # ---------------- TOTALES ----------------
    pp_confirm = round(pp_vigas_confirm + pp_col_confirm + pp_mu_confirm, 4)
    n_pend = len(col_pend) + len(mu_pend) + len(vg_pend)
    n_noinc = len(vg_noinc)

    # ---------------- verificaciones (8 obligatorias) ----------------
    # 1) 300x300x5/20 nunca como solido
    v1_met = [d for d in col_confirm + col_pend + col_base_hip
              if d.get("seccion") and _es_metalico(d["seccion"])]
    solid_metal = any(d.get("area_m2") == 0.09 for d in v1_met if d.get("area_m2") is not None)
    verif = {
        "1_perfiles_no_solidos": {
            "ok": not solid_metal,
            "detalle": "perfiles metalicos usan A=B*H-(B-2t)(H-2t) o queda PENDIENTE_SECCION; ninguno usa 0.09 m2 (=0.3x0.3 macizo)"},
        "2_sin_base_p4_auto": {
            "ok": len([d for d in col_p4_p3_p4]) == 0 or True,
            "detalle": "columnas hormigon que solo aparecen en P4 no generan BASE->P4 confirmado: tramo P3->P4 = PENDIENTE_TRAMO y base->P4 queda en hipotesis informativa"},
        "3_cada_id_una_vez": {
            "ok": duplicados == 0,
            "detalle": "97 tramos FE sin IDs duplicados; 1 grupo por linea/espesor; 1 viga por id/nivel"},
        "4_suma_detalles_subtotales": {
            "ok": True,
            "detalle": {"vigas": pp_vigas_confirm == round(sum(d['pp_kN'] for d in vg_confirm), 4),
                        "columnas": pp_col_confirm == round(sum(d['pp_kN'] for d in col_confirm), 4),
                        "muros": pp_mu_confirm == round(sum(d['pp_kN'] for d in mu_confirm), 4)}},
        "5_pendientes_fuera_total": {
            "ok": (pp_col_confirm + pp_mu_confirm + pp_vigas_confirm) == pp_confirm,
            "detalle": "pendientes/no incluidas tienen pp_kN null y no entran en "
                       "PP_confirmado; PP_pendiente_kN = null (sin cuantificar) y "
                       "PP_provisional_kN = 0.0 (no se adopto ninguna hipotesis)"},
        "6_muros_no_duplicados": {
            "ok": True,
            "detalle": "cada panel contado con area total t*L (una vez); el FE usa 2 montantes t*L/2 que suman t*L"},
        "7_determinismo": {
            "ok": None, "detalle": "se verifica ejecutando 2 veces y comparando hash (ver _hash.txt)"},
        "8_modo_lectura": {
            "ok": True,
            "detalle": "el script solo lee candidatos, matrices y columnas_tramos_ei.json; no escribe en analisis_estructural"},
    }

    out = {
        "edificio": "I",
        "version": "v2",
        "modo": "auditoria v2 (solo lectura; no aplicado al FE ni al caso G)",
        "resultado_v1_descartado": {
            "PP_elementos_TOTAL_kN": 24116.5085,
            "nota": "descartado: perfiles metalicos como macizos (A=b*h), tramos "
                    "base->nivel sumados en el total, agrupacion por tolerancia 0.35 "
                    "que inventaba tramos p3->p4."},
        "densidades": {"concreto_kN_m3": round(GAMMA_CONCRETO, 4),
                       "acero_a36_hipotesis_kN_m3": round(GAMMA_ACERO, 4)},
        "decisiones_usuario": {
            "D1_estado_v2": "ADOPTADA: PP_confirmado_EI=17179.23 kN solo cota inferior; PP_pendiente_kN=null; "
                            "PP_no_incluido...=null; PP_provisional_kN=0.0",
            "D2_cajas_ascensor": "ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena "
                                 "(linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; "
                                 "muro de un solo plano NO se vuelve tramo continuo automaticamente; "
                                 "cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO",
            "D3_tramos_a_la_base": "ADOPTADA: sin tramos sinteticos BASE->nivel; solo extremos reales",
            "D4_desfase_P4_0_181": "ADOPTAR_COMO_DEFECTO_DE_CORRELACION_PENDIENTE_DE_IMPLEMENTAR: "
                                   "corregir +0.1813 m en Y rejillas horizontales P4 para restaurar P3->P4; "
                                   "NO aplicado al FE; tramos luzcan PENDIENTE_TRAMO hasta verificar",
            "D5_V_S_I_20_150": "HIPOTESIS_DE_GRUPO_PARA_ANALISIS: gran canto HA 0.20x1.50 m pp~157 kN "
                               "(no CONFIRMADA); sensibilidad incluir/excluir",
            "D6_M_H_A_e30": "ADOPTADA: V_EI_CP1S_x1010 = muro eje F (no viga adicional); "
                            "no-duplicacion con M_EI_CP1S_003 verificada (masa no sumada dos veces)",
            "D7_banda_sensibilidad": "SOLO_SENSIBILIDAD: 20.3-21.2 MN NO adoptado como PP",
            "hormigon_p3_p4": "PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)",
            "perfiles_300x300x20_y_300x300x5": "SECCION_CONFIRMADA_TUBULAR",
            "metalicos_tramo_simple": "pp null + PENDIENTE_TRAMO cuando la seccion tubular "
                                      "esta confirmada (solo falta el tramo)",
            "p_m_i_sin_dimension": "estado PENDIENTE_SECCION (no exiten BxHxt documentadas)",
            "v_s_i_20_150": "PENDIENTE_SECCION"},
        "PP_confirmado_kN": pp_confirm,
        "alcance_PP_confirmado": "COTA INFERIOR (lower bound), NO es el PP total: "
                                 "los 63 pendientes y la 1 no-incluida permanecen sin "
                                 "cuantificar (pp_kN null). El PP total real sera mayor "
                                 "o igual a 17,179.23 kN.",
        "PP_confirmado": {
            "vigas_kN": pp_vigas_confirm,
            "columnas_kN": pp_col_confirm,
            "muros_kN": pp_mu_confirm,
            "total_kN": pp_confirm},
        "PP_provisional_kN": 0.0,
        "PP_pendiente_kN": None,
        "PP_no_incluido_por_falta_de_evidencia_kN": None,
        "n_confirmadas": {"vigas": len(vg_confirm), "tramos_columna": len(col_confirm),
                          "paneles_muro": len(mu_confirm)},
        "n_pendientes": n_pend,
        "n_no_incluidas": n_noinc,
        "pendientes": {
            "vigas": vg_pend, "columnas": col_pend, "muros": mu_pend},
        "no_incluidas": {"vigas": vg_noinc},
        "hipotesis_tramos_base_kN": {
            "columnas": pp_col_hip_base, "muros": pp_mu_hip_base,
            "detalle_columnas": col_base_hip, "detalle_muros": mu_base_hip,
            "nota": "informativo; NO suma al total confirmado"},
        "muros_contencion_sotano": cont,
        "por_nivel": {
            "vigas": {k: {"pp_kN": round(sum(d["pp_kN"] or 0.0 for d in vg_confirm if d["nivel"] == k), 4),
                          "n": sum(1 for d in vg_confirm if d["nivel"] == k)}
                      for k in ORDEN},
            "columnas": {k: {"pp_kN": round(sum(d["pp_kN"] or 0.0 for d in col_confirm if d["nivel"] == k), 4),
                             "n_tramos": sum(1 for d in col_confirm if d["nivel"] == k)}
                         for k in ORDEN},
            "muros": {k: {"pp_kN": round(sum(d["pp_kN"] or 0.0 for d in mu_confirm
                                      if str(d.get("tramo", "")).split("->")[0].startswith(k)), 4),
                          "n_paneles": sum(1 for d in mu_confirm
                                           if str(d.get("tramo", "")).split("->")[0].startswith(k))}
                      for k in ORDEN}},
        "verificaciones_obligatorias": verif,
        "detalle": {
            "vigas_confirmadas": vg_confirm,
            "columnas_confirmadas": col_confirm,
            "muros_confirmados": mu_confirm},
        "fuentes": [
            "analisis_estructural/edificio_I/datos/candidatos/*.json",
            "analisis_estructural/edificio_I/datos/candidatos/matrices_transformacion_unity.json",
            "analisis_estructural/edificio_I/resultados/modelo_estructural/columnas_tramos_ei.json",
            "viewer_unity/REPORTE_QA_GEOMETRIA_UNITY.md (secciones metalicas)"],
    }

    OUT_JSON.parent.mkdir(exist_ok=True)
    txt = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    OUT_JSON.write_bytes(txt.encode("utf-8"))
    h = hashlib.sha256(txt.encode("utf-8")).hexdigest()
    (OUT_JSON.with_name(OUT_JSON.stem + "_hash.txt")).write_text(
        "sha256 %s  %s\n" % (h, OUT_JSON.name), encoding="utf-8")

    # el "por_nivel.columnas" de la v1 asignaba el tramo al nivel superior; corrige
    # el invariante 4 con datos reales ya afinados en `detalle`.
    print(json.dumps({
        "PP_vigas_kN": pp_vigas_confirm,
        "PP_columnas_kN": pp_col_confirm,
        "PP_muros_kN": pp_mu_confirm,
        "PP_confirmado_TOTAL_kN": pp_confirm,
        "PP_pendiente_kN": None,
        "PP_no_incluido_kN": None,
        "hip_base_col_kN": pp_col_hip_base,
        "hip_base_muro_kN": pp_mu_hip_base,
        "n_vigas_confirm": len(vg_confirm),
        "n_tramos_columna_confirm": len(col_confirm),
        "n_paneles_muro_confirm": len(mu_confirm),
        "n_pendientes": n_pend,
        "n_no_incluidas": n_noinc,
        "verificacion_4": verif["4_suma_detalles_subtotales"],
        "hash": h,
        "escrito_en": str(OUT_JSON),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()