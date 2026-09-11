"""Exporta esfuerzos internos FE del perfil MODELO_FE_COMPLETO_FUNCIONAL (G, Q,
EX, EY + 9 combinaciones NCh3171) como paquete con el CONTRATO V1
(`esfuerzos_FE_edificio_v1`) que ya consume el viewer Unity.

Diferencias respecto a `exportar_esfuerzos_para_viewer.py` (pipeline superposicion):
  - Fuente: los artefactos reconciliados del perfil nuevo
      modelo_fiel/MODELO_FE_COMPLETO_FUNCIONAL/{G,Q,EX,EY}_{EI,EII}_MODELO_FE_COMPLETO_FUNCIONAL.json
      y COMB_{U1_GQ,U2_EX_*,U3_EY_*,U4_*}_{EI,EII}_MODELO_FE_COMPLETO_FUNCIONAL.json
    (`fuerzas_local_por_elemento` = 12 componentes por extremo, convencion
    localForce de la fuente; NO se recalcula nada).
  - Casos exportados: G, Q, EX, EY y las 9 combinaciones normativas NCh3171
    (U1_GQ, U2_EX_POS/NEG, U3_EY_POS/NEG, U4_EX_POS/NEG, U4_EY_POS/NEG), cada
    una proveniente de una corrida EXPLICITA de OpenSees del patron combinado.
    NO se exporta la COMBINADA arbitraria antigua (eliminada por completo).
  - Elementos auxiliares analiticos (stubs del edificio I, `stub_elastico_rigidez_elevada`):
    conectores elasticos de rigidez elevada sin objeto equivalente en el viewer.
    Viajan con `es_auxiliar_analitico` + `auxiliar_analitico` (razon de existencia,
    origen, destino, longitud, seccion) y estan documentados en
    `documentacion_elementos_auxiliares` (excluidos de cobertura viewer<->FE, no
    asignados a una barra fisica, visibles solo en modo de diagnostico).
  - El emparejamiento con la geometria del viewer reutiliza las reglas V1
    (`emparejar`/`leer_geometria_viewer` del exporter importable).
  - Validaciones previas a reemplazar el JSON del viewer:
      1. cantidad e identidad de elementos (tags identicos entre casos y modelo);
      2. unicidad e integridad (12 componentes, finitos);
      3. equilibrio por reacciones y resultantes (G/Q vertical; EX/EY mediante el
         equilibrio nodal de la fuerza GLOBAL por nodo, `globalForce` de OpenSees,
         contra la ecuacion de nodo: sum(globalForce extremos) - aplicada - reaccion
         = 0, que ejercita unidades, signos y extremos i/j en cada elemento);
      4. muestra representativa (columnas de base comprimidas en G);
      5. cobertura viewer<->FE con SIN_RESULTADO con causa documentada.
  - Copia de seguridad del JSON anterior antes de reemplazar.
  - `nivel` de cada elemento = nivel del extremo inferior (nivel de su cota_i),
    igual semantica que los JSON V1 anteriores del viewer.
  - Frame de mando identico al V1: Unity (X, Y, Z) = (u, cota, v).

Salida:
  viewer_unity/Assets/StreamingAssets/lab_data/edificios/{I,II}/results/esfuerzos_FE_EDIFICIO_{I,II}.json

CLI:
  python src/unity_esfuerzos/exportar_esfuerzos_funcional_para_viewer.py [I|II] [--dry-run]
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
E3 = RAIZ / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel" / "MODELO_FE_COMPLETO_FUNCIONAL"
GEOMETRIA_VIEWER = RAIZ / "viewer_unity" / "Assets" / "StreamingAssets" / "lab_data" / "edificios"
EI_SRC = RAIZ / "analisis_estructural" / "edificio_I" / "src"

sys.path.insert(0, str(EI_SRC))

from src.unity_esfuerzos.exportar_esfuerzos_para_viewer import (  # noqa: E402
    emparejar,
    leer_geometria_viewer,
)

FORMATO = "esfuerzos_FE_edificio_v1"
CASOS_BASE = ["G", "Q", "EX", "EY"]

from src.modelo_fiel.combinaciones_nch3171 import (  # noqa: E402
    COMBINACIONES_NCH3171, IDS_COMBINACIONES, NOMBRE_NORMA, NOTA_100_30,
)

CASOS = CASOS_BASE + list(IDS_COMBINACIONES)
INDICES = {
    "N_i": 0, "Vy_i": 1, "Vz_i": 2, "T_i": 3, "My_i": 4, "Mz_i": 5,
    "N_j": 6, "Vy_j": 7, "Vz_j": 8, "T_j": 9, "My_j": 10, "Mz_j": 11,
}
INDICES_NOMBRES = [n for n, _ in sorted(INDICES.items(), key=lambda kv: kv[1])]
CONVENCION = (
    "12 componentes por extremo "
    "[N_i, Vy_i, Vz_i, T_i, My_i, Mz_i, N_j, Vy_j, Vz_j, T_j, My_j, Mz_j] "
    "(kN / kN*m); +N = compresion en el extremo (convencion localForce de la fuente)"
)
TOL = 2e-3  # m (mismo criterio que la auditoria de emparejamiento V1)
TOL_EQ = 1e-3
TOL_STUB_BILATERAL = 1e-3  # relativo: fuerzas locales i+j ~ 0 en el stub
TOL_STUB_NODAL = 1e-2      # kN: equilibrio nodal en extremos de stub (EX/EY)
NIVELES = {
    "I": ["CP1S", "P1", "P2", "P3", "P4"],
    "II": ["EII_CP1S", "EII_CP1", "EII_CP2", "EII_CP3", "EII_CP4"],
}
PREFIJO = {"I": "EI", "II": "EII"}

# Elementos auxiliares analiticos (stubs): conectores elasticos de rigidez elevada
# del edificio I (E*rigidez_mult). Reemplazan rigidLink para el acoplamiento
# excentrico (ver _add_stub_rigid del motor). NO tienen objeto equivalente en el
# viewer: quedan SIN_CORRESPONDENCIA_VIEWER, excluidos de la cobertura viewer<->FE
# y visibles solo en el modo de diagnostico del modelo (no en el modo normal).
STUB_TIPO = "stub_elastico_rigidez_elevada"
N_STUBS_EI = 44
# Longitud maxima documentada: radio maximo de arranque del poste de acero
# (R_STUB_MAX_M = 2.5 m, vease modelo_fe_completo) + holgura 0.5 m.
R_STUB_ARRANQUE_M = 2.5
MAX_STUB_LONG_M = R_STUB_ARRANQUE_M + 0.5  # un stub mas largo = "conector gigante"
LONG_MIN_STUB_M = 0.005  # un stub por debajo seria un "tramo fantasma" de longitud nula
RAZON_P4 = "puente_rigido_a_columna_fisica_P4"
RAZON_ARRANQUE = "conector_arranque_poste_acero_sin_eje_base"
RAZON_P1 = "conector_excentrico_viga_P1"
RAZON_SIN_REGISTRO = "SIN_REGISTRO_DOCUMENTADO"


# --------------------------------------------------------------------------- #
# Construccion del modelo (metadata por tag)
# --------------------------------------------------------------------------- #
def _construir(edificio: str):
    """Reconstruye el modelo FE del perfil (tags deterministicos) para metadata."""
    if edificio == "I":
        from src.modelo_fiel import modelo_fe_completo as MEI

        marco = MEI.MarcoFECompleto(MEI.GF.cargar_todos())
        marco.construir()
        return marco
    from src.modelo_fiel import modelo_fe_completo_eii as MEII

    return MEII._construir_fresco(MEII.cargar_todos())


def _cotas(edificio: str) -> dict:
    if edificio == "I":
        from analisis.fe.hipotesis import COTAS_NIVEL_M

        return {cod: float(COTAS_NIVEL_M[cod]) for cod in NIVELES["I"]}
    from src.modelo_fiel import modelo_fe_completo_eii as MEII

    return dict(MEII.EII_COTAS)


def _nivel_de_cota(cotas: dict, z: float):
    for cod, cota in cotas.items():
        if abs(z - cota) <= 1e-3:
            return cod
    return None


def _leer_secciones_viewer(edificio: str) -> dict:
    """-> {nivel: {"columnas": {id: seccion}, "vigas": {id: seccion},
                   "muros": {id: seccion}"""
    out: dict = {}
    for path in sorted((GEOMETRIA_VIEWER / edificio / "geometry").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out[path.stem] = {
            "columnas": {c["id"]: str(c.get("seccion") or "")
                         for c in data.get("columnas", [])},
            "vigas": {v["id"]: str(v.get("seccion") or "")
                      for v in data.get("vigas", [])},
            "muros": {m["id"]: str(m.get("seccion") or "")
                      for m in data.get("muros", [])},
        }
    return out


def _metadata(edificio: str):
    """-> (cotas, {tag: rec_meta}, geo_viewer, secciones_viewer, marco)"""
    marco = _construir(edificio)
    cotas = _cotas(edificio)
    geo = leer_geometria_viewer(edificio)
    secciones = _leer_secciones_viewer(edificio)
    # index columnas del viewer por (nivel, u, v) para seccion
    col_pos = {}
    for nivel, g in geo.items():
        for cid, pos in g["columnas"].items():
            col_pos[(nivel, round(pos[0], 3), round(pos[2], 3))] = (
                secciones[nivel]["columnas"].get(cid) or "")

    recs: dict = {}
    todos = marco.columnas + marco.vigas_elem + marco.muros_elem
    for rec in todos:
        tag = int(rec["tag"])
        if tag in recs:
            raise AssertionError(f"tag {tag} duplicado en {edificio}")
        nivel = _nivel_de_cota(cotas, float(rec["z_i"])) or str(rec.get("nivel"))
        sec = ""
        if rec["tipo"] == "viga":
            sec = secciones[nivel]["vigas"].get(rec["elemento_id"], "") \
                if nivel in secciones else ""
        elif rec["tipo"] == "columna":
            sec = col_pos.get((nivel, round(rec["u_i"], 3), round(rec["v_i"], 3)), "")
        if not sec:
            sec = str(rec.get("seccion") or "")
        p_i = [float(rec["u_i"]), float(rec["z_i"]), float(rec["v_i"])]
        p_j = [float(rec["u_j"]), float(rec["z_j"]), float(rec["v_j"])]
        recs[tag] = {
            "tag": tag,
            "tipo": rec["tipo"],
            "nivel": nivel,
            "seccion": sec,
            "elemento_id": rec["elemento_id"],
            "nodo_i": str(rec["nodo_i"]),
            "nodo_j": str(rec["nodo_j"]),
            "cota_i": float(rec["z_i"]),
            "cota_j": float(rec["z_j"]),
            "u_i": float(rec["u_i"]), "v_i": float(rec["v_i"]), "z_i": float(rec["z_i"]),
            "u_j": float(rec["u_j"]), "v_j": float(rec["v_j"]), "z_j": float(rec["z_j"]),
            "rigidez_mult": float(rec.get("rigidez_mult") or 0.0),
            "p_i_unity": p_i,
            "p_j_unity": p_j,
        }
    _auxiliar_stubs(marco, recs)
    return cotas, recs, geo, marco


def _auxiliar_stubs(marco, recs: dict) -> None:
    """Etiqueta los stubs (SIN_CORRESPONDENCIA_VIEWER) como elementos auxiliares
    analiticos: origen, destino, longitud, seccion y razon de existencia, obtenidas
    de los registros del propio modelo (conectores de arranque de postes, puentes
    P3->P4 y enlaces excentricos de la viga P1). Si un stub no queda explicado por
    ningun registro se marca RAZON_SIN_REGISTRO y lo detecta la auditoria.
    """
    stubs = {t for t, r in recs.items() if r["tipo"] == STUB_TIPO}
    if not stubs:
        return

    def near(p, q, tol=0.05):
        return all(abs(a - b) <= tol for a, b in zip(p, q))

    def coord3(tag):
        return [round(float(x), 4) for x in marco.key_of_tag[int(tag)]]

    p4 = [{"A": coord3(c["A_tag"]), "B": coord3(c["B_tag"])}
          for c in getattr(marco, "conectores_p4", ())
          if c.get("A_tag") is not None and c.get("B_tag") is not None]
    arranques = [{"soporte": [float(x) for x in c["soporte"]],
                  "poste": [float(x) for x in c["poste"]]}
                 for c in getattr(marco, "conectores_arranque", ())
                 if c.get("soporte") is not None and c.get("poste") is not None]
    enlaces_p1 = [{"col": coord3(c["col_tag"]), "beam": coord3(c["beam_tag"])}
                  for c in getattr(marco, "rigid_links_info", ())
                  if c.get("tipo") == STUB_TIPO]

    for tag, rec in recs.items():
        if rec["tipo"] != STUB_TIPO:
            continue
        pi = [rec["u_i"], rec["v_i"], rec["z_i"]]
        pj = [rec["u_j"], rec["v_j"], rec["z_j"]]
        L = (sum((pi[k] - pj[k]) ** 2 for k in range(3))) ** 0.5
        origen, destino, razon = list(pi), list(pj), None
        for c in p4:
            if (near(pi, c["A"]) or near(pj, c["A"])) \
                    and (near(pi, c["B"]) or near(pj, c["B"])):
                razon = RAZON_P4
                if near(pi, c["B"]):
                    origen, destino = c["A"], c["B"]
                break
        if razon is None:
            for c in arranques:
                if (near(pi, c["soporte"]) or near(pj, c["soporte"])) \
                        and (near(pi, c["poste"]) or near(pj, c["poste"])):
                    razon = RAZON_ARRANQUE
                    if near(pi, c["poste"]):
                        origen, destino = c["soporte"], c["poste"]
                    break
        if razon is None:
            for c in enlaces_p1:
                if (near(pi, c["col"]) or near(pj, c["col"])) \
                        and (near(pi, c["beam"]) or near(pj, c["beam"])):
                    razon = RAZON_P1
                    if near(pi, c["beam"]):
                        origen, destino = c["col"], c["beam"]
                    break
        rec["auxiliar_analitico"] = {
            "etiqueta": STUB_TIPO,
            "razon_existencia": razon or RAZON_SIN_REGISTRO,
            "explicacion": _EXPLICACION_STUB.get(razon or RAZON_SIN_REGISTRO, ""),
            "origen": [round(float(x), 4) for x in origen],
            "destino": [round(float(x), 4) for x in destino],
            "longitud_m": round(L, 6),
            "seccion": rec["seccion"] or "RIGIDA",
            "rigidez_mult": float(rec.get("rigidez_mult") or 0.0),
        }


_EXPLICACION_STUB = {
    RAZON_ARRANQUE: ("Poste de acero de la torre (P.M./P.M.I./V.M.) sin eje base: "
                     "el stub conecta el nodo base del poste con el soporte vertical "
                     "mas proximo (dentro del radio documentado) para transferir la "
                     "accion horizontal a la planta sin un tramo base fantasma."),
    RAZON_P4: ("Columna concreta P4 en la v fisica (+0.18) sin eje de grilla en "
               "11.83: el stub conecta el techo del eje de grilla con el nodo "
               "fisico en P4, conservando la excentricidad (0.181 m)."),
    RAZON_P1: ("Enlace excentrico de la viga excéntrica del eje P1 (columnas "
               "H/Ip): conecta la cabeza de columna del grid con el extremo de la "
               "viga en la fachada, conservando el desfase fisico."),
    RAZON_SIN_REGISTRO: "Stub sin correspondencia en los registros del modelo (la auditoria lo rechaza).",
}


# --------------------------------------------------------------------------- #
# Lectura de esfuerzos desde los payloads del perfil
# --------------------------------------------------------------------------- #
def _leer_payload(edificio: str, caso: str) -> dict:
    return json.loads((OUT / f"{caso}_{PREFIJO[edificio]}_MODELO_FE_COMPLETO_FUNCIONAL.json")
                      .read_text(encoding="utf-8"))


def _leer_payload_combo(edificio: str, combo_id: str) -> dict:
    return json.loads(
        (OUT / f"COMB_{combo_id}_{PREFIJO[edificio]}_MODELO_FE_COMPLETO_FUNCIONAL.json")
        .read_text(encoding="utf-8"))


def _fuerzas_de(payload: dict) -> dict:
    fl = payload.get("fuerzas_local_por_elemento")
    if fl is None:
        fl = payload["solucion"]["fuerzas_local_por_elemento"]
    return {int(k): [float(x) for x in v] for k, v in fl.items()}


def _fuerzas_de_global(payload: dict) -> dict:
    fg = payload.get("fuerzas_global_por_elemento")
    if fg is None:
        fg = payload["solucion"]["fuerzas_global_por_elemento"]
    return {int(k): [float(x) for x in v] for k, v in fg.items()}


def _leer_fuerzas(edificio: str):
    """-> (local, global): {caso: {tag: [12 floats]}} desde los payloads."""
    local = {}
    global_ = {}
    for caso in CASOS:
        if caso in CASOS_BASE:
            p = _leer_payload(edificio, caso)
        else:
            p = _leer_payload_combo(edificio, caso)
        local[caso] = _fuerzas_de(p)
        global_[caso] = _fuerzas_de_global(p)
    return local, global_


# --------------------------------------------------------------------------- #
# Validaciones previas a la escritura
# --------------------------------------------------------------------------- #
def _auditar(edificio: str, cotas: dict, recs: dict, fuerzas: dict,
             fuerzas_global: dict) -> dict:
    """Chequeos obligatorios. Lanza AssertionError si identidad/integridad fallan."""
    auditoria = {"edificio": edificio, "checks": [], "muestra": []}

    def check(nombre, ok, detalle):
        auditoria["checks"].append({"check": nombre, "ok": bool(ok),
                                    "detalle": detalle})
        return bool(ok)

    tags_modelo = set(recs)
    # dataset de stubs para los checks 6..11 (solo edificio I en el perfil)
    stubs = {t: r for t, r in recs.items() if r["tipo"] == STUB_TIPO}
    longitudes = {}
    extremos = {}
    grado = {}
    dup_segmento = []
    reales = set()
    seg_stubs = set()
    for tag, rec in recs.items():
        ki = (round(rec["u_i"], 6), round(rec["v_i"], 6), round(rec["z_i"], 6))
        kj = (round(rec["u_j"], 6), round(rec["v_j"], 6), round(rec["z_j"], 6))
        seg = tuple(sorted((ki, kj)))
        L = (sum((ki[k] - kj[k]) ** 2 for k in range(3))) ** 0.5
        longitudes[tag] = L
        ni, nj = int(rec["nodo_i"]), int(rec["nodo_j"])
        extremos[tag] = (ni, nj)
        grado.setdefault(ni, 0)
        grado.setdefault(nj, 0)
        if rec["tipo"] == STUB_TIPO:
            if seg in seg_stubs:
                dup_segmento.append(("duplicado_stub", tag))
            seg_stubs.add(seg)
        else:
            reales.add(seg)
    for t in stubs:
        ki = (round(recs[t]["u_i"], 6), round(recs[t]["v_i"], 6), round(recs[t]["z_i"], 6))
        kj = (round(recs[t]["u_j"], 6), round(recs[t]["v_j"], 6), round(recs[t]["z_j"], 6))
        if tuple(sorted((ki, kj))) in reales:
            dup_segmento.append(("coincide_elemento_real", t))
    for tag, rec in recs.items():
        if rec["tipo"] == STUB_TIPO:
            continue
        for n in (int(rec["nodo_i"]), int(rec["nodo_j"])):
            if n in grado:
                grado[n] += 1
    nodos_stub = set()
    for t in stubs:
        nodos_stub.add(extremos[t][0])
        nodos_stub.add(extremos[t][1])
    # 1) cantidad e identidad de tags entre casos y modelo
    sets_casos = {c: set(fuerzas[c]) for c in CASOS}
    ok_id = all(s == tags_modelo for s in sets_casos.values())
    check("identidad_tags_casos_modelo", ok_id,
          f"modelo={len(tags_modelo)}; " + "; ".join(
              f"{c}={len(sets_casos[c])}" for c in CASOS)
          + f"; coalescen={ok_id}")

    # 2) integridad de vectores (12 finitos por tag)
    mal = [(caso, tag) for caso in CASOS for tag, v in fuerzas[caso].items()
           if len(v) != 12 or not all(np.isfinite(x) for x in v)]
    mal_g = [(caso, tag) for caso in CASOS if caso in fuerzas_global
             for tag, v in fuerzas_global[caso].items()
             if len(v) != 12 or not all(np.isfinite(x) for x in v)]
    ok_int = (not mal) and (not mal_g) and ok_id
    check("vectores_12_finitos", ok_int,
          f"instancias invalidas local={len(mal)}, global={len(mal_g)}")

    if not (ok_id and ok_int):
        raise AssertionError(
            f"esfuerzos {edificio}: identidad o integridad invalidas; no se escribe")

    # 3) equilibrios G/Q (resultante Pz vs reaccion Rz)
    for caso in ("G", "Q"):
        p = _leer_payload(edificio, caso)
        Pz, Rz, eq = float(p["Pz_kN"]), float(p["Rz_kN"]), bool(p["equilibrio_ok"])
        residuo = abs(Pz - Rz)
        ok = eq and residuo <= TOL_EQ * max(Pz, 1.0)
        check(f"equilibrio_vertical_{caso}", ok,
              f"Pz={Pz:.4f} kN, Rz={Rz:.4f} kN, |Pz-Rz|={residuo:.6f}")

    # 3b) combinaciones NCh3171: corridas EXPLICITAS de OpenSees -> cada payload
    #     trae su propio equilibrio vertical y horizontal verificado al correr.
    for cid in IDS_COMBINACIONES:
        p = _leer_payload_combo(edificio, cid)
        Pz, Rz = float(p["Pz_kN"]), float(p["Rz_kN"])
        residuo = abs(Pz - Rz)
        ver = p["verificaciones"]
        hor = ver["horizontal"]
        hor_res = float(hor["residuo_global_kN"])
        ok = bool(ver["ok"]) and residuo <= TOL_EQ * max(Pz, 1.0)
        check(f"equilibrio_{cid}", ok,
              f"Pz={Pz:.4f} kN, Rz={Rz:.4f} kN, |Pz-Rz|={residuo:.6f}; "
              f"Vx={float(hor['Vx_aplicada_kN']):.2f}, "
              f"Vy={float(hor['Vy_aplicada_kN']):.2f}, residuo_global={hor_res:.3e}; "
              f"sol_ok={bool(ver['solucion_ok'])}")

    # 4) sismo: equilibria entre la fuerza global POR NODO (salida real de
    #    OpenSees, `globalForce`) y (carga nodal aplicada + reaccion). Convencion
    #    verificada con los datos: `globalForce` es la fuerza que el NODO aplica
    #    al elemento (node->element), luego por NODO se cumple
    #        sum(globalForce de los extremos) - carga aplicada - reaccion = 0
    #    (a) POR NODO en los dof NO restringidos por diafragma rigido
    #        (uz, rx, ry): en esos grados la ecuacion de nodo se satisface sin
    #        fuerzas de restriccion -> ejercita unidades, signos, ejes locales y
    #        extremos i/j de una vez en cada elemento.
    #    (b) IDENTIDAD GLOBAL (6 dof): sum(internos) - sum(aplicada) - sum(reac)
    #        ~ 0 (las fuerzas de restriccion diafragma se anulan globalmente).
    nodos = set()
    for rec in recs.values():
        nodos.add(int(rec["nodo_i"]))
        nodos.add(int(rec["nodo_j"]))
    dof_libres = [2, 3, 4]
    residuo_stub_sismo = 0.0
    for caso in ("EX", "EY"):
        p = _leer_payload(edificio, caso)
        sol = p["solucion"]
        reacc = {int(k): v for k, v in sol["reacciones"].items()}
        aplicada = {int(k): v for k, v in p["cargas_nodales_sismicas"].items()}
        gsum = {n: np.zeros(6) for n in nodos}
        for tag, rec in recs.items():
            fg = np.array(fuerzas_global[caso][tag])
            gsum[int(rec["nodo_i"])] += fg[:6]
            gsum[int(rec["nodo_j"])] += fg[6:]
        residuo_max = 0.0
        escala = 0.0
        for n in nodos:
            r = gsum[n][dof_libres] - np.array(aplicada.get(n, [0.0] * 6))[dof_libres] \
                - np.array(reacc.get(n, [0.0] * 6))[dof_libres]
            residuo_max = max(residuo_max, float(np.max(np.abs(r))))
            escala = max(escala, float(np.max(np.abs(gsum[n][dof_libres]))))
        for n in nodos_stub:
            r = gsum[n][dof_libres] - np.array(aplicada.get(n, [0.0] * 6))[dof_libres] \
                - np.array(reacc.get(n, [0.0] * 6))[dof_libres]
            residuo_stub_sismo = max(residuo_stub_sismo, float(np.max(np.abs(r))))
        total_fg = sum(gsum.values())
        total_apl = sum((np.array(v) for v in aplicada.values()), np.zeros(6))
        total_reac = sum((np.array(v) for v in reacc.values()), np.zeros(6))
        residuo_global = float(np.max(np.abs(total_fg - total_apl - total_reac)))
        ver = p["verificaciones"]
        corte_ok = bool(ver["corte_basal"]["ok"])
        hor_ok = bool(ver["equilibrio_horizontal"]["ok"])
        tol_libre = 1e-2
        tol_global = 1e-2
        ok = residuo_max <= tol_libre and residuo_global <= tol_global and corte_ok
        check(f"equilibrio_nodal_{caso}", ok,
              f"residuo_por_nodo(dof uz,rx,ry)={residuo_max:.3e} (tol {tol_libre}); "
              f"identidad_global={residuo_global:.3e} (tol {tol_global}); "
              f"corte_basal={corte_ok}, horizontal={hor_ok}, n_reacc={len(reacc)}")

    # 5) muestra representativa: columnas de base comprimidas en G (+N compresion)
    base_z = cotas[NIVELES[edificio][0]]
    base_cols = sorted(
        (t for t, r in recs.items()
         if r["tipo"] == "columna" and abs(r["cota_i"] - base_z) <= 1e-3),
        key=lambda t: (recs[t]["u_i"], recs[t]["v_i"]))
    muestras = [{"tag": t, "tipo": "columna_base",
                 "u": recs[t]["u_i"], "v": recs[t]["v_i"],
                 "N_i_G_kN": round(float(fuerzas["G"][t][0]), 4),
                 "nota": "axial en extremo inferior (base); +N = compresion"}
                for t in base_cols[:5]]
    ok_muestra = bool(muestras) and all(m["N_i_G_kN"] > 1.0 for m in muestras)
    check("muestra_columnas_base_comprimidas", ok_muestra,
          "; ".join(f"tag{m['tag']}N={m['N_i_G_kN']}" for m in muestras) or "sin columnas base")
    auditoria["muestra"] = muestras

    # 6) stubs documentados: cantidad esperada y razon de existencia conocida
    esperado = N_STUBS_EI if edificio == "I" else 0
    sin_registro = [t for t in stubs
                    if recs[t]["auxiliar_analitico"]["razon_existencia"]
                    == RAZON_SIN_REGISTRO]
    ok_stubs = len(stubs) == esperado and not sin_registro
    check("stubs_documentados", ok_stubs,
          f"n_stubs={len(stubs)} (esperado {esperado}); en los registros del modelo, "
          f"sin_razon={len(sin_registro)}")

    # 7) ningun stub es un conector gigante (longitud dentro del maximo documentado)
    l_stub = {t: longitudes[t] for t in stubs}
    gig = [t for t, L in l_stub.items() if L > MAX_STUB_LONG_M]
    check("stub_sin_conector_gigante", not gig,
          f"max_longitud={max(l_stub.values(), default=0.0):.4f} m "
          f"(limite {MAX_STUB_LONG_M} m: arranque maximo documentado "
          f"{R_STUB_ARRANQUE_M} m + holgura); gigantes={len(gig)}")

    # 8) ningun stub duplicado (dos stubs con el mismo segmento, o un stub que
    #    coincide con un elemento real ya modelado)
    check("stub_sin_duplicados", not dup_segmento,
          "; ".join(f"{k} tag={t}" for k, t in dup_segmento[:5]) or
          "segmentos unicos dentro de stubs y sin coincidencia con elementos reales")

    # 9) ningun tramo fantasma: longitud fisica positiva y ambos extremos conectados
    #    a, al menos, un elemento real (no solo a otros stubs)
    fantasma = [t for t in stubs
                if l_stub[t] <= LONG_MIN_STUB_M
                or any(grado[n] < 1 for n in extremos[t])]
    check("stub_sin_tramo_fantasma", not fantasma,
          f"min_longitud={min(l_stub.values(), default=0.0):.6f} m; "
          f"fantasmas={len(fantasma)}")

    # 10) equilibrio local bilateral de fuerzas (sin carga interna absorbida):
    #     N, Vy, Vz, T del extremo i + extreme j ~ 0 en cada caso
    bil = 0.0
    for t in stubs:
        for caso in CASOS:
            v = np.array(fuerzas[caso][t])
            bil = max(bil, float(np.max(np.abs(v[:4] + v[6:10])))
                      / max(float(np.max(np.abs(v))), 1.0))
    ok_bil = bil <= TOL_STUB_BILATERAL
    check("stub_equilibrio_local_bilateral", ok_bil,
          f"residuo_fuerzas_i+j (rel)={bil:.3e} (tol {TOL_STUB_BILATERAL})")

    # 11) transmision de acciones: en cada extremo del stub el equilibrio nodal de
    #     EX/EY (dof libres) se satisface con las fuerzas GLOBALES del propio stub
    #     participando -> el conector transfiere las acciones a la estructura.
    ok_stub_nodal = residuo_stub_sismo <= TOL_STUB_NODAL
    check("stub_transmision_nodal_sismo", ok_stub_nodal,
          f"residuo_por_nodo(dof uz,rx,ry) en extremos de stub, "
          f"EX/EY={residuo_stub_sismo:.3e} (tol {TOL_STUB_NODAL})")

    auditoria["ok"] = all(c["ok"] for c in auditoria["checks"])
    return auditoria


# --------------------------------------------------------------------------- #
# Cobertura viewer <-> FE (SIN_RESULTADO documentado)
# --------------------------------------------------------------------------- #
def _pendientes_ids(edificio: str) -> set:
    ids = set()
    try:
        topo = json.loads(
            (OUT / f"topologia_{PREFIJO[edificio]}.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ids
    pila = [topo]
    while pila:
        obj = pila.pop()
        if isinstance(obj, dict):
            if isinstance(obj.get("id"), str):
                ids.add(obj["id"])
            pila.extend(obj.values())
        elif isinstance(obj, list):
            pila.extend(obj)
    return ids


def _cobertura(recs: dict, emparejado: dict, geo: dict,
               secciones_viewer: dict, pend_ids: set) -> dict:
    """-> {nivel: {tipo: {total, con_fuente, con_detalle, sin_resultado:[{viewer_id,causa}]}}}"""
    out: dict = {}
    for nivel, g in geo.items():
        out[nivel] = {}
        for tipo in ("columnas", "vigas", "muros"):
            con = []
            sin = []
            for vid in g[tipo]:
                tags = sorted(t for t, info in emparejado.items()
                              if info["estado"] != "SIN_CORRESPONDENCIA_VIEWER"
                              and info["viewer_id"] == vid and info["viewer_nivel"] == nivel)
                if tags:
                    con.append({"viewer_id": vid, "tags": tags})
                else:
                    causa = "PENDIENTE_DE_FUENTE" if vid in pend_ids \
                        else "SIN_CORRESPONDENCIA_FE"
                    sin.append({"viewer_id": vid, "causa": causa})
            out[nivel][tipo] = {
                "total": len(g[tipo]),
                "con_fuente": len(con),
                "con_detalle": con,
                "sin_resultado": sin,
            }
    return out


# --------------------------------------------------------------------------- #
# Esquema calculado de combinaciones normativas NCh3171
# --------------------------------------------------------------------------- #
def _esquema_nch3171(edificio: str) -> dict:
    """Las 9 combinaciones se CALCULARON como corridas explicitas de OpenSees
    (cada una con su payload COMB_*_MODELO_FE_COMPLETO_FUNCIONAL.json y sus 12
    componentes por elemento). Cada fuerza por elemento de estos casos proviene
    de la solucion del patron combinado, no de superposicion post-proceso."""
    prefijo = PREFIJO[edificio]
    return {
        "norma": NOMBRE_NORMA,
        "estado": "CALCULADA (9 corridas explicitas de OpenSees por combinacion; "
                  "los casos U1..U4 viajan como casos propios por elemento en "
                  "'fuerzas' y alimentan la 'envolvente_NCh3171')",
        "combinaciones": [
            {"id": c["id"], "expresion": c["expresion"],
             "factores": c["factores"], "grupo": c["grupo"],
             "direccion": c["direccion"], "aplica": c["aplica"],
             "archivo": f"COMB_{c['id']}_{prefijo}_MODELO_FE_COMPLETO_FUNCIONAL.json"}
            for c in COMBINACIONES_NCH3171
        ],
        "combinaciones_100_30": {
            "estado": "NO_NORMATIVA_PARA_ESTA_ENTREGA",
            "nota": NOTA_100_30,
        },
        "envolvente": {
            "sobre": list(IDS_COMBINACIONES),
            "regla": ("por elemento y componente: el caso con mayor |valor| entre "
                      "las combinaciones normativas; se conserva el caso y el "
                      "signo del valor gobernante."),
            "excluye": ["G", "Q", "EX", "EY", "NO_NORMATIVA_PARA_ESTA_ENTREGA"],
        },
        "insumos": sorted(
            [f"{c}_{prefijo}_MODELO_FE_COMPLETO_FUNCIONAL.json"
             for c in CASOS_BASE]
            + [f"COMB_{cid}_{prefijo}_MODELO_FE_COMPLETO_FUNCIONAL.json"
               for cid in IDS_COMBINACIONES]),
    }


def _envolvente(fuerzas: dict, tag: int) -> list:
    """Envolvente NCh3171 por elemento y componente (12): el caso de las 9
    combinaciones normativas con mayor |valor|; se conserva caso y signo."""
    env = []
    for i in range(12):
        mejor = None
        mejor_valor = None
        for cid in IDS_COMBINACIONES:
            v = float(fuerzas[cid][tag][i])
            if mejor_valor is None or abs(v) > abs(mejor_valor):
                mejor_valor = v
                mejor = cid
        env.append({"indice": i, "componente": INDICES_NOMBRES[i],
                    "caso": mejor, "valor": round(float(mejor_valor), 6)})
    return env


# --------------------------------------------------------------------------- #
# Generacion del paquete V1
# --------------------------------------------------------------------------- #
def _documentacion_stubs(elementos: list) -> dict:
    """Registro de los elementos auxiliares analiticos (stubs) que viajan en el
    paquete: razon de existencia, origen/destino, longitud, seccion y las reglas
    de visibilidad para el viewer (solo modo de diagnostico)."""
    stubs = [el for el in elementos if el.get("es_auxiliar_analitico")]
    return {
        "etiqueta": STUB_TIPO,
        "total": len(stubs),
        "excluido_de_cobertura_viewer_FE": True,
        "nota_exclusion": (
            "Los stubs son dispositivos analiticos del modelo FE (conectores "
            "elasticos de rigidez elevada que reemplazan rigidLink). No tienen "
            "objeto equivalente en la geometria del viewer, por lo que NO "
            "participan en las tablas de cobertura viewer<->FE ni en los conteos "
            "por objeto del viewer."),
        "no_asignados_a_barra_fisica": True,
        "nota_no_asignacion": (
            "El emparejamiento V1 no asigna bars fisicas del viewer: para este "
            "tipo el estado es SIN_CORRESPONDENCIA_VIEWER con viewer_id=None; "
            "nunca se les inventa una barra."),
        "visibilidad": {
            "modo_normal": {
                "visible": False,
                "seleccionable": False,
                "nota": "el viewer no los instancia ni permite seleccionarlos en "
                        "el modo normal."},
            "modo_diagnostico": {
                "visible": True,
                "seleccionable": True,
                "nota": "se cargan solo bajo el modo de diagnostico (QA del "
                        "modelo), con geolocalizador origen->destino y fuerzas "
                        "por caso."},
        },
        "registro": [
            {"tag": el["tag"], **el["auxiliar_analitico"]}
            for el in stubs
        ],
    }


def generar(edificio: str, escribir: bool = True, destino: Path | None = None):
    cotas, recs, geo, marco = _metadata(edificio)
    fuerzas, fuerzas_global = _leer_fuerzas(edificio)

    if set(fuerzas["G"]) != set(recs):
        raise AssertionError(
            f"{edificio}: tags difieren entre modelo ({len(recs)}) y esfuerzos "
            f"({len(fuerzas['G'])})")

    auditoria = _auditar(edificio, cotas, recs, fuerzas, fuerzas_global)
    emparejado = emparejar(recs, geo)
    pend_ids = _pendientes_ids(edificio)
    secciones_viewer = _leer_secciones_viewer(edificio)
    cobertura = _cobertura(recs, emparejado, geo, secciones_viewer, pend_ids)

    elementos = []
    for tag in sorted(fuerzas["G"]):
        rec = recs[tag]
        info = emparejado[tag]
        con_estado = info["estado"] != "SIN_CORRESPONDENCIA_VIEWER"
        es_stub = rec["tipo"] == STUB_TIPO
        el = {
            "tag": tag,
            "tipo": rec["tipo"],
            "nivel": rec["nivel"],
            "seccion": rec["seccion"],
            "nodo_i": rec["nodo_i"],
            "nodo_j": rec["nodo_j"],
            "p_i_unity": [round(v, 9) for v in rec["p_i_unity"]],
            "p_j_unity": [round(v, 9) for v in rec["p_j_unity"]],
            "correspondencia": {
                "estado": info["estado"],
                "viewer_id": info["viewer_id"] if con_estado else None,
                "viewer_nivel": info["viewer_nivel"] if con_estado else None,
            },
            "fuerzas": {caso: [round(float(v), 6) for v in fuerzas[caso][tag]]
                        for caso in CASOS},
            "envolvente_NCh3171": _envolvente(fuerzas, tag),
        }
        if es_stub:
            el["es_auxiliar_analitico"] = True
            el["auxiliar_analitico"] = rec["auxiliar_analitico"]
        elementos.append(el)

    resumen: dict = {}
    for el in elementos:
        key = f"{el['tipo']}__{el['correspondencia']['estado']}"
        resumen[key] = resumen.get(key, 0) + 1

    data = {
        "formato": FORMATO,
        "edificio": edificio,
        "generado_por": str(Path(__file__).name),
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fuente": {
            "perfil": "MODELO_FE_COMPLETO_FUNCIONAL",
            "archivos": (
                [f"{caso}_{PREFIJO[edificio]}_MODELO_FE_COMPLETO_FUNCIONAL.json"
                 for caso in CASOS_BASE]
                + [f"COMB_{cid}_{PREFIJO[edificio]}_MODELO_FE_COMPLETO_FUNCIONAL.json"
                   for cid in IDS_COMBINACIONES]),
            "ruta": str(OUT.relative_to(RAIZ)),
        },
        "fuente_metadata": "modelo_fe_completo(_eii).py (tags deterministicos del perfil)",
        "unidades": {"carga": "kN", "momento": "kN*m", "longitud": "m"},
        "frame": {"nota": "Unity (X, Y, Z) = (u, cota, v); posiciones LOCALES del "
                          "edificio (sin Placement)",
                  "api": "agregar Position del edificio para posicionar en el mundo"},
        "convencion_localForce": CONVENCION,
        "indices_componentes": dict(INDICES),
        "casos": list(CASOS),
        "casos_base": list(CASOS_BASE),
        "combinaciones_normativas_NCh3171": _esquema_nch3171(edificio),
        "redondeo": {"fuerzas": 6, "coordenadas": 9,
                     "nota": "valores copiados tal cual de la fuente; no se recalculan"},
        "n_elementos": len(elementos),
        "lista_niveles": list(NIVELES[edificio]),
        "niveles_geometry_viewer": sorted(geo),
        "nivel_por_elemento": "nivel del extremo inferior (nivel de cota_i)",
        "resumen_por_tipo_estado": dict(sorted(resumen.items())),
        "documentacion_elementos_auxiliares": _documentacion_stubs(elementos),
        "elementos": elementos,
    }

    if not escribir:
        return data, auditoria, cobertura

    objetivo = destino or (
        GEOMETRIA_VIEWER / edificio / "results"
        / f"esfuerzos_FE_EDIFICIO_{edificio}.json")
    objetivo.parent.mkdir(parents=True, exist_ok=True)
    if objetivo.exists():
        respaldo = objetivo.with_name(
            f"esfuerzos_FE_EDIFICIO_{edificio}_ANTERIOR_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")
        shutil.copy2(objetivo, respaldo)
        data["respaldo_anterior"] = str(respaldo.relative_to(RAIZ))
    objetivo.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    return data, auditoria, cobertura


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv
    edificios = [a for a in args if a in ("I", "II")] or ["I", "II"]
    dry = "--dry-run" in args
    total_n = 0
    total_f = 0
    ok_all = True
    for edificio in edificios:
        data, auditoria, cobertura = generar(edificio, escribir=not dry)
        n = data["n_elementos"]
        f = sum(len(el["fuerzas"]) for el in data["elementos"])
        total_n += n
        total_f += f
        sin_total = sum(len(tc["sin_resultado"])
                        for nivel in cobertura.values() for tc in nivel.values())
        estado = "OK" if auditoria["ok"] else "FALLIDA"
        print(f"[{edificio}] {estado}: {n} elementos, {f} vectores; "
              f"checks {sum(1 for c in auditoria['checks'] if c['ok'])}/"
              f"{len(auditoria['checks'])}; SIN_RESULTADO={sin_total}")
        print("   resumen: " + "; ".join(
            f"{k}={v}" for k, v in data["resumen_por_tipo_estado"].items()))
        if dry:
            print(f"   (dry-run: {edificio} no escrito)")
        ok_all = ok_all and auditoria["ok"]
    print(f"TOTAL: {total_n} elementos, {total_f} vectores de 12 componentes")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))