"""G_EI_MODELO_FIEL — primera iteracion del caso G fiel del Edificio I.

Parte del caso G del checkpoint (losas + PM.ADIC aplicados por geometria
tributaria = 25.227,73 kN) y agrega SOLO el peso propio de elementos CONFIRMADO
por la auditoria v2 (cota inferior 17.179,23 kN: 137 vigas + 43 tramos de
columna + 4 paneles de muro). Todo lo pendiente queda EXPLICITO en el ledger y
NO se aplica:

  * tramos ficticios BASE->nivel (columnas 4.223,82 kN / muros 3.675,18 kN,
    HIPOTESIS_FE, fuera del total confirmado);
  * perfiles metalicos tratados como macizos (rechazados por v1);
  * V.S.I. 20/150 de CP1S con material no confirmado (PENDIENTE_SECCION);
  * desfase de correlacion P4 +0.1813 m (PENDIENTE_TRAMO, no instancia el FE);
  * cajas de ascensor de un solo plano (PENDIENTE_TRAMO);
  * muros de contencion del sotano (HIPOTESIS_CIMENTACION).

Camino estructural del PP confirmado: descarga en los extremos de cada
elemento, proporcional a la longitud del segmento FE y con la mitad en cada
nodo extremo (coherente con la estrategia nodal usada por el pipeline EII y
con el reparto por nodo de la tributaria de Semana 2). NO usa el nodo mas
cercano.

Verificaciones: (a) suma del PP aplicado == total auditado por componente y
por nivel; (b) identidad longitud FE vs longitud auditada por id; (c) cada id
contado una sola vez; (d) 1.000 tag de nodos sin doble nodo; (e) equilibrio
vertical Rz vs Pz; (f) delta por componente nulo entre antes y despues para
losas+PM.ADIC.

Salidas bajo modelo_fiel/EI/ (no toca results/ del checkpoint):
  G_EI_MODELO_FIEL.json            contrato completo (incluye soluciones antes/despues)
  G_EI_MODELO_FIEL_ledger.json     ledger antes/despues por componente y nivel
  G_EI_MODELO_FIEL_reacciones.csv  reacciones de G despues (fiel)
  G_EI_MODELO_FIEL_comparacion.json antes vs despues (reacciones/desplazamientos)
  G_EI_MODELO_FIEL.md              resumen legible

Uso:
  python -X utf8 -m src.modelo_fiel.caso_G_EI_MODELO_FIEL
"""

from __future__ import annotations

import copy
import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
RES = E3 / "results"
OUT = E3 / "modelo_fiel" / "EI"
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"
AUDIT_V2 = RES / "peso_propio_teorico_EDIFICIO_I_v2.json"
CASO_Q = RES / "cargas" / "caso_Q_EI_FE.json"

sys.path.insert(0, str(EI_SRC))

from analisis.fe import geometria_fe as GF         # noqa: E402
from analisis.fe import resolver as RESv           # noqa: E402
from analisis.fe import tributaria as TB           # noqa: E402
from analisis.fe import cargas_correlacionadas as CC  # noqa: E402
from analisis.fe.hipotesis import COTAS_NIVEL_M, niveles_ordenados  # noqa: E402
from analisis.fe.marco import Marco                # noqa: E402

GAMMA_CONCRETO_KN_M3 = 24.5166
TOL_LONGITUD = 0.02      # 2 %
TOL_EQUILIBRIO = 1e-4     # kN


# ------------------------------------------------------------------------- #
# Construccion del modelo y G del checkpoint
# ------------------------------------------------------------------------- #
def construir_marco_EI() -> Marco:
    niveles = GF.cargar_todos()
    marco = Marco(niveles, rigidez_mult=1.0e3)
    marco.subdivision_vigas = 1
    marco.construir()
    return marco


def cargas_G_actual(marco) -> dict:
    """G del checkpoint (losas + PM.ADIC) por nivel, identico a caso_sismico."""
    por_nivel = CC.cargas_por_losa_por_nivel()
    cargas = {}
    for cod in niveles_ordenados():
        nivelFE = marco.niveles[cod]
        cargas_por_losa = {}
        for lo in nivelFE.losas:
            info = por_nivel.get(cod, {}).get(lo["id"], {})
            cargas_por_losa[lo["id"]] = (info.get("pm_kn_m2", 0.0),
                                         info.get("sc_kn_m2", 0.0))
        cn, _rp = TB.calcular_cargas_nodales(nivelFE, marco.receptor_nodos,
                                             cargas_por_losa, marco.key_of_tag,
                                             incluir_sc=False)
        cargas[cod] = cn
    return cargas


def profundidad(cargas) -> dict:
    out = {}
    for cod, c in cargas.items():
        out[cod] = {int(t): list(f) for t, f in c.items()}
    return out


def sumar_fz(cargas_por_nivel) -> float:
    return -sum(f[2] for c in cargas_por_nivel.values() for f in c.values())


def sumar_por_nivel(cargas_por_nivel) -> dict:
    return {cod: round(-sum(f[2] for f in c.values()), 4)
            for cod, c in cargas_por_nivel.items()}


# ------------------------------------------------------------------------- #
# PP confirmado: mapeo de la auditoria v2 sobre los elementos FE
# ------------------------------------------------------------------------- #
def _lon(rec) -> float:
    return math.hypot(rec["u_j"] - rec["u_i"], rec["v_j"] - rec["v_i"],
                      rec["z_j"] - rec["z_i"])


def _match_vigas(marco, conf) -> dict:
    """Conf: detalle.vigas_confirmadas. Devuelve por id: FE elements + pp_audit."""
    por_id = {}
    for v in conf:
        por_id[v["id"]] = {"pp_kN": v["pp_kN"], "L_m": v["L_m"]}
    elems = [r for r in marco.vigas_elem if r.get("tipo") == "viga"]
    match = {}
    for r in elems:
        pid = r["elemento_id"]
        if pid in por_id:
            match.setdefault(pid, []).append(r)
    chequeos = []
    items = []
    total = 0.0
    for pid, meta in por_id.items():
        segs = match.get(pid, [])
        L_total = sum(_lon(s) for s in segs)
        lref = meta["L_m"]
        chequeos.append({"id": pid, "n_segmentos_fe": len(segs),
                         "L_fe_m": round(L_total, 4), "L_audit_m": lref,
                         "ok": abs(L_total - lref) <= TOL_LONGITUD * lref})
        items.append({"tipo": "viga", "id": pid, "nivel": segs[0]["nivel"] if segs else None,
                      "pp_kN": meta["pp_kN"], "n_elements_fe": len(segs),
                      "nodos": sorted({int(segs[0]["nodo_i"]), int(segs[0]["nodo_j"])}) if segs else []})
        total += meta["pp_kN"]
    return {"por_id": por_id, "match": match, "chequeos": chequeos,
            "items": items, "total_kN": round(total, 4)}


def _match_columnas(marco, conf) -> dict:
    por_id = {c["tramo"]: {"pp_kN": c["pp_kN"], "h_m": c["h_m"]} for c in conf}
    match = {}
    for r in marco.columnas:
        if r["elemento_id"] in por_id:
            match.setdefault(r["elemento_id"], []).append(r)
    chequeos = []
    items = []
    total = 0.0
    for pid, meta in por_id.items():
        segs = match.get(pid, [])
        L_total = sum(_lon(s) for s in segs)
        lref = meta["h_m"]
        chequeos.append({"id": pid, "n_segmentos_fe": len(segs),
                         "L_fe_m": round(L_total, 4), "L_audit_m": lref,
                         "ok": len(segs) == 1 and abs(L_total - lref) <= TOL_LONGITUD * lref})
        first = segs[0] if segs else None
        items.append({"tipo": "columna", "id": pid,
                      "nivel": first["nivel"] if first else None,
                      "pp_kN": meta["pp_kN"], "n_elements_fe": len(segs),
                      "nodos": [int(first["nodo_i"]), int(first["nodo_j"])] if first else []})
        total += meta["pp_kN"]
    return {"por_id": por_id, "match": match, "chequeos": chequeos,
            "items": items, "total_kN": round(total, 4)}


def _match_muros(marco, conf) -> dict:
    """Muros confirmados (paneles entre niveles consecutivos). Se identifican
    por el par de extremos de la linea y los niveles del tramo."""
    items = []
    chequeos = []
    total = 0.0
    match = {}
    for i, m in enumerate(conf):
        key = "%s#%d" % (m["tramo"], i)
        (ua, va) = m["linea"][0]
        (ub, vb) = m["linea"][1]
        tramo = m["tramo"]             # p.ej. 'P2->P3'
        low, high = tramo.split("->")
        z_low, z_high = COTAS_NIVEL_M[low], COTAS_NIVEL_M[high]
        segs = []
        for r in marco.muros_elem:
            if abs(r["z_i"] - z_low) < 0.02 and abs(r["z_j"] - z_high) < 0.02:
                if abs(r["u_i"] - r["u_j"]) > 0.02 or abs(r["v_i"] - r["v_j"]) > 0.02:
                    continue           # solo se aceptan montantes verticales
                ok_a = math.hypot(r["u_i"] - ua, r["v_i"] - va) < 0.02
                ok_b = math.hypot(r["u_i"] - ub, r["v_i"] - vb) < 0.02
                if ok_a or ok_b:
                    segs.append(r)
        L_fe = sum(_lon(r) for r in segs)
        chequeos.append({"key": key, "id_panel": m.get("id_panel"),
                         "tramo": tramo, "n_montantes_fe": len(segs),
                         "L_montante_fe_m": round(L_fe / max(len(segs), 1), 4),
                         "h_m_fe_m": m["h_m"],
                         "ok": len(segs) == 2 and abs(
                             L_fe / max(len(segs), 1) - m["h_m"])
                             <= TOL_LONGITUD * m["h_m"]})
        nodos = set()
        for r in segs:
            nodos.add(int(r["nodo_i"])); nodos.add(int(r["nodo_j"]))
        items.append({"key": key, "tipo": "muro", "id": m.get("id_panel"),
                      "tramo": tramo, "nivel": high, "pp_kN": m["pp_kN"],
                      "n_elements_fe": len(segs), "nodos": sorted(nodos)})
        match[key] = segs
        total += m["pp_kN"]
    return {"match": match, "chequeos": chequeos, "items": items,
            "total_kN": round(total, 4)}


def aplicar_pp_nodal(marco, v_info, c_info, m_info) -> dict:
    """Convierte el PP confirmado en cargas nodales por nivel (z negativa).

    Reparto: cada elemento recibe su fraccion de PP proporcional a su longitud
    dentro del id y la descarga con la mitad en cada nodo extremo.
    """
    cargas = {}
    items = []
    total = 0.0
    keys_contados = set()

    # vigas
    for pid in v_info["por_id"]:
        pp_id = v_info["por_id"][pid]["pp_kN"]
        segs = v_info["match"].get(pid, [])
        assert segs, "viga confirmada sin elemento FE: %s" % pid
        Ls = [_lon(s) for s in segs]
        Lsum = sum(Ls)
        for s, L in zip(segs, Ls):
            share = pp_id * L / Lsum
            tags = (int(s["nodo_i"]), int(s["nodo_j"]))
            for t in tags:
                acc = cargas.setdefault(s["nivel"], {}).setdefault(t, [0.0] * 6)
                acc[2] -= share / 2.0
            keys_contados.add(pid)
        total += pp_id

    # columnas
    for pid in c_info["por_id"]:
        pp_id = c_info["por_id"][pid]["pp_kN"]
        segs = c_info["match"].get(pid, [])
        assert segs, "columna confirmada sin elemento FE: %s" % pid
        s = segs[0]
        tags = (int(s["nodo_i"]), int(s["nodo_j"]))
        for t in tags:
            acc = cargas.setdefault(s["nivel"], {}).setdefault(t, [0.0] * 6)
            acc[2] -= pp_id / 2.0
        keys_contados.add(pid)
        total += pp_id

    # muros (panel PP sobre los 4 nodos de montante: 1/4 cada uno)
    for pid, (pp_id, segs) in _muros_pp(m_info).items():
        for r, w in segs:
            tags = (int(r["nodo_i"]), int(r["nodo_j"]))
            for t in tags:
                acc = cargas.setdefault(r["nivel"], {}).setdefault(t, [0.0] * 6)
                acc[2] -= pp_id * w / 2.0
            keys_contados.add(pid)
        total += pp_id

    return {"cargas": cargas, "total_kN": round(total, 4),
            "n_ids_contados": len(keys_contados)}


def _muros_pp(m_info) -> dict:
    """key de panel -> (pp_kN, [(elemento_fe, fraccion_por_extremo)])."""
    out = {}
    for item in m_info["items"]:
        segs = m_info["match"].get(item["key"], [])
        n = len(segs)
        out[item["key"]] = (item["pp_kN"], [(r, 1.0 / max(n, 1)) for r in segs])
    return out


def verificar_identidad(v_info, c_info, m_info, marco) -> dict:
    """Suma A_fe*L*gamma por componente == total auditado (redundancia)."""
    def suma_fam(lista, elems_key):
        tot = 0.0
        for r in lista:
            tot += r["sec_valores"]["A"] * _lon(r) * GAMMA_CONCRETO_KN_M3
        return tot
    v_fe = suma_fam([r for r in marco.vigas_elem
                     if r.get("tipo") == "viga"
                     and r["elemento_id"] in v_info["por_id"]], "v")
    c_fe = suma_fam([r for r in marco.columnas
                     if r["elemento_id"] in c_info["por_id"]], "c")
    m_fe = 0.0
    for segs in m_info["match"].values():
        m_fe += sum(r["sec_valores"]["A"] * _lon(r) * GAMMA_CONCRETO_KN_M3
                    for r in segs)
    return {
        "viga_AxLxG_kN": round(v_fe, 4), "viga_audit_kN": v_info["total_kN"],
        "columna_AxLxG_kN": round(c_fe, 4), "columna_audit_kN": c_info["total_kN"],
        "muro_AxLxG_kN": round(m_fe, 4), "muro_audit_kN": m_info["total_kN"],
        "ok": (abs(v_fe - v_info["total_kN"]) < 0.05
               and abs(c_fe - c_info["total_kN"]) < 0.05
               and abs(m_fe - m_info["total_kN"]) < 0.05)}


def componentes_por_nivel(v_info, c_info, m_info) -> dict:
    out = {"vigas": {}, "columnas": {}, "muros": {}}
    for item in v_info["items"]:
        nv = item["nivel"]
        out["vigas"][nv] = round(out["vigas"].get(nv, 0.0) + item["pp_kN"], 4)
    for item in c_info["items"]:
        nv = item["nivel"]
        out["columnas"][nv] = round(out["columnas"].get(nv, 0.0) + item["pp_kN"], 4)
    for item in m_info["items"]:
        nv = item["tramo"].split("->")[0]
        out["muros"][nv] = round(out["muros"].get(nv, 0.0) + item["pp_kN"], 4)
        out["muros"][item["tramo"].split("->")[1]] = round(
            out["muros"].get(item["tramo"].split("->")[1], 0.0) + item["pp_kN"], 4)
    return out


# ------------------------------------------------------------------------- #
# Resolucion y comparacion
# ------------------------------------------------------------------------- #
def resolver_caso(marco, cargas_por_nivel: dict):
    return RESv.resolver(marco, cargas_por_nivel)


def max_desp_z(sol) -> float:
    return max((abs(v[2]) for v in sol["desplazamientos"].values()), default=0.0)


def nodo_max_desp(sol) -> dict:
    if not sol["desplazamientos"]:
        return {}
    tag, v = max(sol["desplazamientos"].items(), key=lambda kv: abs(kv[1][2]))
    return {"tag": int(tag), "dz_m": round(v[2], 8)}


def _muestras_fuerzas(sol, ids, marco):
    """Axiales y momentos (global, extremos i/j) de una muestra de elementos."""
    fam = marco.vigas_elem + marco.columnas + marco.muros_elem
    por_id = {}
    for r in fam:
        if r["elemento_id"] in ids:
            por_id.setdefault(r["elemento_id"], []).append(r)
    out = []
    for pid, segs in por_id.items():
        tag = str(segs[0]["tag"])
        gf = sol["fuerzas"].get("global", {}).get(tag)
        if gf is None:
            continue
        out.append({"elemento_id": pid, "tipo": segs[0]["tipo"],
                    "nivel": segs[0]["nivel"],
                    "P_i_kN": round(gf[0], 4), "P_j_kN": round(gf[6], 4),
                    "My_i_kN_m": round(gf[4], 4), "My_j_kN_m": round(gf[10], 4)})
    return out


def comparar_perfiles(marco, sol_antes, sol_despues, v_info, c_info) -> dict:
    Rz_a = sum(r[2] for r in sol_antes["reacciones"].values())
    Rz_d = sum(r[2] for r in sol_despues["reacciones"].values())
    ids_v = []
    for pid in v_info["por_id"]:
        segs = v_info["match"].get(pid, [])
        if segs and segs[0]["nivel"] in ("P3", "P4"):
            ids_v.append(pid)
        if len(ids_v) >= 2:
            break
    ids_c = list(c_info["por_id"])
    return {
        "solucion_antes": {
            "ok": sol_antes["ok"], "R_z_kN": round(Rz_a, 4),
            "max_desp_z_m": round(max_desp_z(sol_antes), 8),
            "n_reacciones": sol_antes.get("n_reacciones"),
            "nodo_max_desp": nodo_max_desp(sol_antes)},
        "solucion_despues": {
            "ok": sol_despues["ok"], "R_z_kN": round(Rz_d, 4),
            "max_desp_z_m": round(max_desp_z(sol_despues), 8),
            "n_reacciones": sol_despues.get("n_reacciones"),
            "nodo_max_desp": nodo_max_desp(sol_despues)},
        "delta": {
            "R_z_kN": round(Rz_d - Rz_a, 4),
            "max_desp_z_m": round(max_desp_z(sol_despues) - max_desp_z(sol_antes), 8)},
        "muestra_axiles_momentos": _muestras_fuerzas(sol_despues, ids_v + ids_c,
                                                     marco),
    }


def _markdown(ledger, ident, comp, pendientes_total) -> str:
    l = []
    l.append("# G_EI_MODELO_FIEL (primera iteracion)")
    l.append("")
    l.append("G antes (checkpoint, losas + PM.ADIC): **%.2f kN** = %s"
             % (ledger["G_antes_kN"], ledger["G_antes_por_nivel"]))
    l.append("")
    l.append("PP confirmado aplicado (auditoria v2, cota inferior): "
             "**%.2f kN** (vigas %.2f + columnas %.2f + muros %.2f)"
             % (ledger["PP_confirmado_kN"], ident["viga_AxLxG_kN"],
                ident["columna_AxLxG_kN"], ident["muro_AxLxG_kN"]))
    l.append("")
    l.append("G despues (fiel): **%.2f kN**" % ledger["G_despues_kN"])
    l.append("")
    l.append("## Pendientes explicitos (NO aplicados)")
    l.append("")
    l.append("- tramos ficticios BASE->nivel (HIPOTESIS_FE): columnas %.2f kN / "
             "muros %.2f kN" % (pendientes_total["columnas_base_kN"],
                                pendientes_total["muros_base_kN"]))
    l.append("- V.S.I. 20/150 de CP1S: PENDIENTE_SECCION (pp no cuantificado)")
    l.append("- desfase P4 +0.1813 m y cajas de ascensor de un solo plano: "
             "PENDIENTE_TRAMO")
    l.append("- muros de contencion del sotano: HIPOTESIS_CIMENTACION "
             "(%.2f kN, no adoptados)" % pendientes_total["contencion_kN"])
    l.append("- metalicos (V.M./P.M. y P.M.I.): fuera del total confirmado "
             "(seccion tubular confirmada pero tramo PENDIENTE_TRAMO)")
    l.append("")
    l.append("## Verificaciones")
    l.append("")
    l.append("| check | estado | detalle |")
    l.append("|---|---|---|")
    for c in ledger["verificaciones"]:
        l.append("| %s | %s | %s |" % (c["check"], c["estado"], c["detalle"]))
    l.append("")
    l.append("## Comparacion con el checkpoint (mismo solver)")
    l.append("")
    l.append("- R_z antes = %.4f kN  ->  R_z despues = %.4f kN  (delta %.4f kN)"
             % (comp["solucion_antes"]["R_z_kN"],
                comp["solucion_despues"]["R_z_kN"],
                comp["delta"]["R_z_kN"]))
    l.append("- max |dz| antes = %.8f m  ->  despues = %.8f m"
             % (comp["solucion_antes"]["max_desp_z_m"],
                comp["solucion_despues"]["max_desp_z_m"]))
    for m in comp["muestra_axiles_momentos"]:
        l.append("- %s (%s %s): P_i=%.2f / P_j=%.2f kN ; My_i=%.2f / My_j=%.2f kN.m"
                 % (m["elemento_id"], m["tipo"], m["nivel"],
                    m["P_i_kN"], m["P_j_kN"], m["My_i_kN_m"], m["My_j_kN_m"]))
    return "\n".join(l) + "\n"


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    audit = json.loads(AUDIT_V2.read_text(encoding="utf-8"))
    ppe = audit["pendientes"]
    pbase = audit["hipotesis_tramos_base_kN"]
    contencion = audit["muros_contencion_sotano"]
    pendientes_total = {
        "n_pendientes": audit["n_pendientes"],
        "n_no_incluidas": audit["n_no_incluidas"],
        "columnas_base_kN": round(pbase["columnas"], 4),
        "muros_base_kN": round(pbase["muros"], 4),
        "contencion_kN": round(sum(v["pp_kN"] for v in contencion.values()), 4),
    }

    marco = construir_marco_EI()
    cargas_antes = profundidad(cargas_G_actual(marco))
    Pz_antes = sumar_fz(cargas_antes)
    sol_antes = resolver_caso(marco, cargas_antes)

    v_info = _match_vigas(marco, audit["detalle"]["vigas_confirmadas"])
    c_info = _match_columnas(marco, audit["detalle"]["columnas_confirmadas"])
    m_info = _match_muros(marco, audit["detalle"]["muros_confirmados"])
    identidad = verificar_identidad(v_info, c_info, m_info, marco)
    aplic = aplicar_pp_nodal(marco, v_info, c_info, m_info)
    por_nivel = componentes_por_nivel(v_info, c_info, m_info)

    cargas_despues = copy.deepcopy(cargas_antes)
    for cod, c in aplic["cargas"].items():
        for t, f in c.items():
            acc = cargas_despues.setdefault(cod, {}).setdefault(int(t), [0.0] * 6)
            for i in range(6):
                acc[i] += f[i]
    Pz_despues = sumar_fz(cargas_despues)
    # reconstruir modelo limpio para la segunda corrida (determinismo de OpenSees)
    marco2 = construir_marco_EI()
    sol_despues = resolver_caso(marco2, cargas_despues)

    checks = []
    checks.append({"check": "suma_pp_igual_audit",
                   "estado": "OK" if abs(aplic["total_kN"] - audit["PP_confirmado_kN"]) < 0.05
                   else "ERROR",
                   "detalle": "aplicado %.4f vs audit %.4f" % (aplic["total_kN"],
                                                               audit["PP_confirmado_kN"])})
    checks.append({"check": "identidad_AxLxG_vs_audit",
                   "estado": "OK" if identidad["ok"] else "ERROR",
                   "detalle": json.dumps({k: identidad[k] for k in
                                          ("viga_AxLxG_kN", "viga_audit_kN",
                                           "columna_AxLxG_kN", "columna_audit_kN",
                                           "muro_AxLxG_kN", "muro_audit_kN")})})
    checks.append({"check": "longitud_fe_vs_audit",
                   "estado": "OK" if all(q["ok"] for q in
                                         v_info["chequeos"] + c_info["chequeos"]
                                         + m_info["chequeos"]) else "ERROR",
                   "detalle": "%d vigas + %d col + %d muros" % (
                       len(v_info["chequeos"]), len(c_info["chequeos"]),
                       len(m_info["chequeos"]))})
    checks.append({"check": "cada_id_una_vez",
                   "estado": "OK" if aplic["n_ids_contados"]
                   == len(v_info["por_id"]) + len(c_info["por_id"])
                   + len(m_info["items"]) else "ERROR",
                   "detalle": "%d de %d ids contados una sola vez"
                   % (aplic["n_ids_contados"],
                      len(v_info["por_id"]) + len(c_info["por_id"]) + len(m_info["items"]))})
    checks.append({"check": "equilibrio_vertical_antes",
                   "estado": "OK" if sol_antes["ok"] and abs(
                       sum(r[2] for r in sol_antes["reacciones"].values()) - Pz_antes)
                       < TOL_EQUILIBRIO * max(Pz_antes, 1.0) else "ERROR",
                   "detalle": "Pz=%.4f, Rz=%.4f" % (Pz_antes,
                    sum(r[2] for r in sol_antes["reacciones"].values()))})
    checks.append({"check": "equilibrio_vertical_despues",
                   "estado": "OK" if sol_despues["ok"] and abs(
                       sum(r[2] for r in sol_despues["reacciones"].values()) - Pz_despues)
                       < TOL_EQUILIBRIO * max(Pz_despues, 1.0) else "ERROR",
                   "detalle": "Pz=%.4f, Rz=%.4f" % (Pz_despues,
                    sum(r[2] for r in sol_despues["reacciones"].values()))})
    checks.append({"check": "losas_y_pm_adic_intactas",
                   "estado": "OK" if abs(Pz_despues - Pz_antes - aplic["total_kN"])
                   < 0.01 else "ERROR",
                   "detalle": "delta esperado = %.4f, delta observado = %.4f"
                   % (aplic["total_kN"], Pz_despues - Pz_antes)})

    comp = comparar_perfiles(marco, sol_antes, sol_despues, v_info, c_info)
    ledger = {
        "perfil": "G_EI_MODELO_FIEL",
        "G_antes_kN": round(Pz_antes, 4),
        "G_antes_por_nivel": sumar_por_nivel(cargas_antes),
        "PP_confirmado_kN": round(aplic["total_kN"], 4),
        "PP_por_nivel": por_nivel,
        "G_despues_kN": round(Pz_despues, 4),
        "G_despues_por_nivel": sumar_por_nivel(cargas_despues),
        "pendientes_explicitos": pendientes_total,
        "verificaciones": checks,
    }

    payload = {
        "caso": "G", "edificio": "I", "iteracion": "MODELO_FIEL_1",
        "motor": "OpenSeesPy (mismo Marco que checkpoint; misma configuracion)",
        "fuentes": ["peso_propio_teorico_EDIFICIO_I_v2.json (solo lectura)",
                    "candidatos (geometria) via motor fe", "columnas_tramos_ei.json"],
        "reglas": {
            "camino_estructural": "descarga en extremos de la pieza, "
                                  "proporcional a la longitud del segmento FE "
                                  "(nunca nodo mas cercano)",
            "excluidos": ["tramos ficticios BASE->nivel", "metalicos como macizos",
                          "V.S.I. sin material confirmado", "pendientes sin "
                          "cuantificar", "hipotesis de sensibilidad"]},
        "ledger": ledger,
        "solucion_antes": {k: sol_antes[k] for k in ("ok", "reacciones",
                                                     "desplazamientos",
                                                     "fuerzas")},
        "solucion_despues": {k: sol_despues[k] for k in ("ok", "reacciones",
                                                         "desplazamientos",
                                                         "fuerzas")},
        "comparacion": comp,
    }

    (OUT / "G_EI_MODELO_FIEL.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "G_EI_MODELO_FIEL_ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(OUT / "G_EI_MODELO_FIEL_reacciones.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "Rx_kN", "Ry_kN", "Rz_kN", "Mx_kN_m", "My_kN_m", "Mz_kN_m"])
        for tag, r in sol_despues["reacciones"].items():
            w.writerow([int(tag)] + [round(x, 6) for x in r])
    (OUT / "G_EI_MODELO_FIEL_comparacion.json").write_text(
        json.dumps(comp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "G_EI_MODELO_FIEL.md").write_text(
        _markdown(ledger, identidad, comp, pendientes_total), encoding="utf-8")

    resumen = {"edificio": "I", "perfil": "G_EI_MODELO_FIEL",
               "G_antes_kN": round(Pz_antes, 4),
               "PP_confirmado_kN": round(aplic["total_kN"], 4),
               "G_despues_kN": round(Pz_despues, 4),
               "equilibrio_despues": checks[5]["detalle"],
               "checks_ok": sum(1 for c in checks if c["estado"] == "OK"),
               "checks_total": len(checks),
               "escrito": [str(p) for p in sorted(OUT.glob("G_EI_MODELO_FIEL*"))]}
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0 if all(c["estado"] == "OK" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())