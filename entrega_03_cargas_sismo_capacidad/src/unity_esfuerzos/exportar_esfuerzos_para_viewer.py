"""Exporta esfuerzos internos FE (G, Q, EX, EY, COMBINADA) como paquete para el viewer Unity.

Funcionamiento:
  - Lee las corridas FE de:
      results/superposicion/verificacion_superposicion_completa_{I,II}.json
    donde `resultados_por_corrida[CASO]["fuerzas_local"][tag]` es un vector de 12
    componentes (convencion localForce confirmada en `nota_extremos`).
  - La caso COMBINADA es la corrida FE EXPLICITA (1.0*G + 0.7*Q + 0.3*EX + (-0.2)*EY,
    config/superposicion.json). NO se recalcula: se copia tal cual de la fuente.
  - Metadata geometrica por tag:
      * Edificio I : esfuerzos_elementos_edificio_I.csv (nivel, tipo, seccion, nodos, coords).
      * Edificio II: results/cargas/caso_G_EII_reproducible.json (id builder, nivel, nodos,
        coords desde modelo.nodos_coords con orden [u, v, cota]).
  - Correspondencia con la geometria del viewer (solo REFERENCIA, nunca se recolorea):
      * 1A1     : match exacto unico (extremos/posicion dentro de tolerancia).
      * CONTENIDO: el elemento FE queda contenido en un unico objeto del viewer.
      * SIN_CORRESPONDENCIA_VIEWER: sin referencia segura.
    Regla unica por coordenadas para ambos edificios (los ids de EII son ambiguos):
    se empareja contra las geometrias lab_data/edificios/{I,II}/geometry/*.json.
  - No inventa resultados: los valores se copian tal cual de la fuente (redondeo 6/9
    documentado en salida).

Salida (2 archivos):
  viewer_unity/Assets/StreamingAssets/lab_data/edificios/{I,II}/results/esfuerzos_FE_EDIFICIO_{I,II}.json
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
FUENTE_SUPERPOSICION = RAIZ / "entrega_03_cargas_sismo_capacidad" / "results" / "superposicion"
FUENTE_CSV_I = (
    RAIZ
    / "analisis_estructural"
    / "edificio_I"
    / "resultados"
    / "modelo_estructural"
    / "esfuerzos_elementos_edificio_I.csv"
)
FUENTE_BUILDER_II = (
    RAIZ
    / "entrega_03_cargas_sismo_capacidad"
    / "results"
    / "cargas"
    / "caso_G_EII_reproducible.json"
)
GEOMETRIA_VIEWER = RAIZ / "viewer_unity" / "Assets" / "StreamingAssets" / "lab_data" / "edificios"

CASOS = ["G", "Q", "EX", "EY", "COMBINADA"]
INDICES = {
    "N_i": 0, "Vy_i": 1, "Vz_i": 2, "T_i": 3, "My_i": 4, "Mz_i": 5,
    "N_j": 6, "Vy_j": 7, "Vz_j": 8, "T_j": 9, "My_j": 10, "Mz_j": 11,
}
TOL = 2e-3  # m (mismo criterio que la auditoria de emparejamiento)
# Columnas: el eje FE del pilar queda en el centro de la huella (u_centro),
# mientras el viewer registra posicion discreta de la huella (borde/canto
# REUBICADA) que puede diferir ~1 cm. La auditoria de emparejamiento coloca la
# posicion de columna con tolerancia 2 cm; se replica aqui (queda muy por debajo
# de la separacion entre ejes del grid, evita emparejes cruzados).
TOL_COLUMNA = 0.02  # m (u, v)
# Tolerancia 3D de emparejamiento de barras (m): misma que TOL (2 mm). Se aplica a
# la comparacion de extremos (directa o invertida), centro, longitud y orientacion
# de la barra FE contra el tramo fisico del viewer en el eje de la barra.
TOL_3D = TOL
# Estado de correspondencia de una barra FE analitica (postes, conectores) que
# SOLO coincide en planta con una columna del viewer pero NO en el tramo fisico
# completo del entrepiso (extremos/centro/longitud/orientacion 3D fuera de
# tolerancia, o sin tramo fisico por encima del ultimo forjado). Conserva sus
# resultados, sigue en el JSON y solo se muestra en modo de diagnostico.
SIN_GEOMETRIA_FISICA_3D = "SIN_GEOMETRIA_FISICA_3D"
# Muros: el eje FE de la franja de muro puede quedar descentrado respecto a la
# polilinea central del panel del viewer hasta ~0.31 m (observado en planos EI:
# 0.125-0.31 m, excentricidad de la franja respecto al eje del panel), por lo que
# la contencion estricta de 2 mm no basta. Se empareja por distancia al poligono
# del panel con esta tolerancia (cubre las excentricidades documentadas y queda
# muy por debajo de la separacion entre muros, evita emparejes cruzados).
TOL_MURO = 0.35  # m
# Para resolver la pertenencia de un elemento FE vertical cuyo pie cae en la
# union de dos paneles (esquina de nucleo): se prefiere el panel cuya longitud en
# su eje dominante es multiplo de la longitud de franja del elemento (seccion
# "M <t>x<L>x..."). Holgura relativa documentada.
TOL_COLIN = 0.05  # relativo a la longitud de franja L

FORMATO = "esfuerzos_FE_edificio_v1"
CONVENCION = (
    "12 componentes por extremo "
    "[N_i, Vy_i, Vz_i, T_i, My_i, Mz_i, N_j, Vy_j, Vz_j, T_j, My_j, Mz_j] "
    "(kN / kN*m); +N = compresion en el extremo (convencion localForce de la fuente)"
)


def leer_superposicion(edificio: str) -> dict:
    """-> {caso: {int tag: [12 floats]}}"""
    path = FUENTE_SUPERPOSICION / f"verificacion_superposicion_completa_{edificio}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    corridas = data["resultados_por_corrida"]
    out: dict = {}
    for caso in CASOS:
        src = "EXPLICITA" if caso == "COMBINADA" else caso
        fl = corridas[src]["fuerzas_local"]
        out[caso] = {int(k): list(v) for k, v in fl.items()}
    for caso in CASOS:
        assert len(out[caso]) == data["modelo_n_elementos"], (
            f"edificio {edificio} caso {caso}: {len(out[caso])} elementos"
        )
    return out


def leer_metadata_I() -> dict:
    """-> {tag: dict(nodo_i, nodo_j, nivel, tipo, seccion, p_i_unity, p_j_unity)}"""
    out: dict = {}
    with open(FUENTE_CSV_I, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            tag = int(row["elementTag_FE"])
            nivel = row["nivel"].strip()
            z_i = float(row["z_i_m"])
            z_j = float(row["z_j_m"])
            out[tag] = {
                "tipo": row["tipo_elemento"].strip(),
                "nivel": nivel,
                "seccion": row["seccion"].strip(),
                "nodo_i": row["nodo_i"].strip(),
                "nodo_j": row["nodo_j"].strip(),
                "cota_i": z_i,
                "cota_j": z_j,
                "p_i_unity": [float(row["u_i_m"]), z_i, float(row["v_i_m"])],
                "p_j_unity": [float(row["u_j_m"]), z_j, float(row["v_j_m"])],
            }
    return out


def leer_metadata_II() -> dict:
    """-> {tag: dict(...)}; nodos_coords con orden [u, v, cota]."""
    data = json.loads(FUENTE_BUILDER_II.read_text(encoding="utf-8"))
    nodos = data["modelo"]["nodos_coords"]

    def coord(nodo: int) -> list:
        try:
            u, v, cota = nodos[str(nodo)]
        except (KeyError, ValueError):
            raise KeyError(f"nodo {nodo} sin coordenada")
        return [float(u), float(cota), float(v)]  # unity (u, cota, v)

    out: dict = {}
    for tipo, elems in data["elementos"].items():
        for el in elems:
            tag = int(el["tag"])
            z_i = nodos[str(el["nodo_i"])][2]
            z_j = nodos[str(el["nodo_j"])][2]
            if tag in out:
                raise AssertionError(f"tag repetido en EII: {tag}")
            out[tag] = {
                "tipo": el["tipo"],
                "nivel": el["nivel"],
                "seccion": el["seccion"],
                "nodo_i": str(el["nodo_i"]),
                "nodo_j": str(el["nodo_j"]),
                "cota_i": float(z_i),
                "cota_j": float(z_j),
                "p_i_unity": coord(el["nodo_i"]),
                "p_j_unity": coord(el["nodo_j"]),
                "id_builder": el["id"],
            }
    return out


def leer_geometria_viewer(edificio: str) -> dict:
    """-> {nivel: {"cota": float, "columnas": {id: (u,cota,v)}, "vigas": {id: [(u,cota,v),...]},
                   "muros": {id: [(u,cota,v),...]}}}"""
    out: dict = {}
    for path in sorted((GEOMETRIA_VIEWER / edificio / "geometry").glob("*.json")):
        nivel = path.stem
        data = json.loads(path.read_text(encoding="utf-8"))
        cols = {c["id"]: [float(x) for x in c["posicion"]] for c in data.get("columnas", [])}
        vigas = {v["id"]: [[float(x) for x in p] for p in v["pts"]] for v in data.get("vigas", [])}
        muros = {m["id"]: [[float(x) for x in p] for p in m["pts"]] for m in data.get("muros", [])}
        cotas = [c[1] for c in cols.values()] or [p[1] for p in vigas.values()] or [p[1] for p in muros.values()]
        out[nivel] = {
            "cota": float(min(cotas)),
            "columnas": cols,
            "vigas": vigas,
            "muros": muros,
        }
    return out


def cercano(a, b, tol=TOL):
    return abs(a - b) <= tol


def punto_en_segmento(p, a, b, tol=TOL):
    """p dentro de la caja 2D del segmento [a,b] en (u,cota) -> para vigas/muros."""
    return (
        min(a[0], b[0]) - tol <= p[0] <= max(a[0], b[0]) + tol
        and min(a[1], b[1]) - tol <= p[1] <= max(a[1], b[1]) + tol
    )


def dist_punto_segmento(p, a, b):
    """Distancia euclidiana 2D de p al segmento [a,b]."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return _d2(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    return _d2(p, (a[0] + t * dx, a[1] + t * dy))


def _d2(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def dist_punto_polilinea(p, pts):
    """Distancia de p (u,v) a la polilinea del panel (pts en (u,cota,v))."""
    uv = [(pt[0], pt[2]) for pt in pts]
    if len(uv) == 1:
        return _d2(p, uv[0])
    return min(dist_punto_segmento(p, uv[i], uv[i + 1]) for i in range(len(uv) - 1))


def _largo_seccion(seccion):
    """-> largo de franja L de una seccion 'M <t>x<L>x<c>' (o None)."""
    if not seccion:
        return None
    try:
        t, resto = seccion.split("x", 1)
        largo, _ = resto.split("x", 1)
        return float(largo)
    except ValueError:
        return None


def _resolver_esquina(el, cands):
    """Emparejamiento determinista de un muro FE cuyo pie cae en la union de dos
    paneles (>= 2 candidatos a la misma distancia minima, p. ej. esquina de un
    nucleo en forma de C o L). Reglas documentadas, en orden de prioridad:
      1) Colinealidad de franja: el elemento FE es una franja vertical de largo L
         (seccion 'M <t>x<L>x...'); se asigna al panel cuyo largo en su eje
         dominante (eje u si el panel es horizontal, eje v si es vertical) es
         multiplo de L con holgura relativa TOL_COLIN. Validada con las esquinas
         EII (franjas 0.3x1.32x2 = panel horizontal 2.64 m ≈ 2.645 m; franjas
         0.25x1.49x2 = pier vertical 2.97≈2.98 m) y las esquinas EI P2 (franjas
         0.2x1.72x2 = panel horizontal 3.45 = 2*1.72 m).
      2) Interioridad de la proyeccion: el panel cuyo eje dominante contiene el
         pie del elemento en su interior (parametro de proyeccion t lejos de los
         extremos) cuando la regla 1 no distingue (p. ej. pier en el medio de una
         pierna vertical con extension extra).
      3) Panel de mayor extension; 4) id lexicograficamente menor (regla de cierre
         determinista, nunca aleatoria)."""
    largo = _largo_seccion(el.get("seccion") or "")
    paneles = []
    for _, mid, pts in cands:
        us = [pt[0] for pt in pts]
        vs = [pt[2] for pt in pts]
        span_u = max(us) - min(us)
        span_v = max(vs) - min(vs)
        if span_u >= span_v:
            extent, coord = span_u, el["p_i_unity"][0]
            p0, p1 = min(us), max(us)
        else:
            extent, coord = span_v, el["p_i_unity"][2]
            p0, p1 = min(vs), max(vs)
        t = (coord - p0) / extent if extent > 0 else 0.0
        paneles.append({"id": mid, "extent": extent, "coord": coord,
                        "p0": p0, "p1": p1, "t": t, "interior": min(t, 1 - t)})

    if largo:
        candidatos = []
        for k in range(1, 6):
            for p in paneles:
                candidatos.append((abs(p["extent"] - k * largo), k, p["id"]))
        mejor = min(candidatos, key=lambda x: (x[0], x[2]))
        if mejor[0] <= TOL_COLIN * largo:
            return mejor[2]

    # reglas 2-4: mayor interioridad de la proyeccion; desempate por mayor
    # extension y luego por id lexicograficamente menor (cierre determinista).
    ordenados = sorted(paneles,
                       key=lambda p: (-round(p["interior"], 6), -round(p["extent"], 6),
                                      p["id"]))
    return ordenados[0]["id"]


def tramo_fisico_columna(nivel, geo):
    """Tramo vertical fisico al que debe corresponder una columna del viewer del
    nivel `nivel`: [cota(nivel), cota(nivel siguiente)]. Devuelve None si el nivel
    no tiene cota superior documentada (ultimo forjado: no existe columna física
    dibujada por encima, p. ej. torre EI sobre P4)."""
    if nivel not in geo:
        return None
    cz = float(geo[nivel]["cota"])
    cotas = sorted({float(gr["cota"]) for gr in geo.values()})
    ups = [c for c in cotas if c > cz + TOL]
    if not ups:
        return None
    return (cz, ups[0])


def barra_vertical(pi, pj, tol):
    """La barra es vertical (eje cota/Unity-Y): u y v constantes en sus extremos."""
    return abs(pi[0] - pj[0]) <= tol and abs(pi[2] - pj[2]) <= tol


def comparar_intervalo_3d(pi, pj, zA, zB, tol):
    """Compara la barra 3D pi->pj contra el tramo vertical fisico [zA,zB].
    Devuelve dict con 'ok' (coincidencia de extremos directa O invertida, lo que
    implica coincidencia de centro, longitud y orientacion vertical) y las
    metricas solicitadas por la auditoria 3D:
      d_extremo   = maxima desviacion de cada extremo a la cota del tramo
                    (elegida por el orden que minimiza extremo a extremo)
      d_centro    = (c_barra - c_tramo)
      d_longitud  = (L_barra - L_tramo)
      d_orientacion = 1 - |dot(n_unitario_barra, (0,+-1,0))| (0 = colineal vertical)
      orientacion = 'directa' | 'invertida' | 'no_coincide'
    """
    L_tramo = abs(zB - zA)
    z_i, z_j = pi[1], pj[1]
    L_barra = abs(z_j - z_i)
    d_extr_dir = max(abs(z_i - zA), abs(z_j - zB))
    d_extr_inv = max(abs(z_i - zB), abs(z_j - zA))
    dir_ok = barra_vertical(pi, pj, tol) and d_extr_dir <= tol
    inv_ok = barra_vertical(pi, pj, tol) and d_extr_inv <= tol
    d_centro = (z_i + z_j) / 2.0 - (zA + zB) / 2.0
    d_longitud = L_barra - L_tramo
    # desviacion de la direccion de la barra respecto a la vertical (asignada por
    # el orden de extremos: signo de (z_j - z_i) vs signo de (zB - zA))
    if L_barra > 1e-12:
        nz = (z_j - z_i) / L_barra
        d_orientacion = 1.0 - abs(nz)
    else:
        d_orientacion = 1.0
    if dir_ok:
        orientacion = "directa"
    elif inv_ok:
        orientacion = "invertida"
    else:
        orientacion = "no_coincide"
    return {
        "ok": dir_ok or inv_ok,
        "d_extremo_m": min(d_extr_dir, d_extr_inv),
        "d_centro_m": d_centro,
        "d_longitud_m": d_longitud,
        "d_orientacion": d_orientacion if dir_ok or inv_ok else 1.0,
        "orientacion": orientacion,
    }


def emparejar(meta: dict, geo: dict) -> dict:
    """-> {tag: {"estado": ..., "viewer_id": str|None, "viewer_nivel": str|None}}
    Reglas (una sola para I y II):
      * columna : el objeto columna del nivel del extremo inferior con posicion == (u,v,cota).
      * viga    : 1A1 = extremos iguales a los pts de un objeto viga; CONTENIDO = ambos
                  extremos dentro de un unico objeto viga (caja 2D en el plano del nivel).
      * muro    : eje vertical (u,v) contenido en un unico objeto muro del nivel (caja 2D
                  en (u,cota) del panel) -> CONTENIDO (el FE es 1D vertical, el viewer panel).
      * stub    : no hay objeto equivalente -> SIN.
    """
    def nivel_viewer(meta_elem):
        cotas = [(nivel, g["cota"]) for nivel, g in geo.items()]
        for nivel, cz in cotas:
            if cercano(meta_elem["cota_i"], cz):
                return nivel
        # elemento con base por debajo del nivel mas bajo (penetracion de
        # fundacion: contenciones M_001/M_002 que descienden de la cota del
        # sotano). Se asigna al nivel mas bajo si el extremo superior alcanza
        # la cota de ese nivel.
        niveles_cotas = [(nivel, g["cota"]) for nivel, g in geo.items()]
        niveles_cotas.sort(key=lambda x: x[1])
        if niveles_cotas and meta_elem["cota_i"] < niveles_cotas[0][1] - TOL:
            nivel_bajo, cz_bajo = niveles_cotas[0]
            if cercano(meta_elem["cota_j"], cz_bajo):
                return nivel_bajo
        return None

    out: dict = {}
    for tag, el in meta.items():
        tipo = el["tipo"]
        estado, vid, vnivel = "SIN_CORRESPONDENCIA_VIEWER", None, None
        if tipo not in ("columna", "viga", "muro"):
            out[tag] = {"estado": estado, "viewer_id": None, "viewer_nivel": None}
            continue

        nivel = nivel_viewer(el)
        if nivel is None:
            out[tag] = {"estado": estado, "viewer_id": None, "viewer_nivel": None}
            continue
        g = geo[nivel]
        x_i, z_i, y_i = el["p_i_unity"]
        x_j, z_j, y_j = el["p_j_unity"]

        if tipo == "columna":
            # 1A1 3D-COMPLETO (columna): ademas de la coincidencia en planta
            # (u,v), la barra FE debe coincidir con el TRAMO FISICO COMPLETO del
            # entrepiso: extremo inferior en la cota del nivel y extremo superior
            # en la cota del nivel siguiente (comparacion directa o invertida de
            # extremos -> centro, longitud y orientacion vertical dentro de
            # TOL_3D). NO basta coincidencia en planta ni que solo un extremo caiga
            # en la cota del nivel. EJEMPLO persistido (P4-EI, tags 607-635): la
            # barra FE corre z=11,83->15,79 (L=3,96 m) y la columna fisica del
            # viewer P4 es 7,87->11,83 (L=3,96 m): NO comparten extremos; la FE
            # queda FLOTANTE un entrepiso hacia arriba y no tiene tramo fisico
            # por encima del forjado P4 -> SIN_GEOMETRIA_FISICA_3D (analitica,
            # conserva sus resultados, no se asigna a la columna fisica P4).
            p_i = (x_i, z_i, y_i)
            p_j = (x_j, z_j, y_j)
            z_inf = min(z_i, z_j)
            # nivel = forjado del extremo inferior (tolerante a orientacion
            # invertida de la barra); respeta la misma cota que posicion.y.
            nivel_col = nivel
            for n_col_, gr_col in geo.items():
                if cercano(z_inf, float(gr_col["cota"])):
                    nivel_col = n_col_
                    break
            tramo = tramo_fisico_columna(nivel_col, geo)
            g_col = geo[nivel_col]
            cands = [cid for cid, pos in g_col["columnas"].items()
                     if cercano(pos[0], x_i, TOL_COLUMNA)
                     and cercano(pos[2], y_i, TOL_COLUMNA)
                     and cercano(pos[1], z_inf)]
            if len(cands) == 0:
                # sin objeto columna coincidente ni siquiera en planta -> se
                # conserva el estado previo SIN_CORRESPONDENCIA_VIEWER
                pass
            elif tramo is None or len(cands) > 1:
                estado, vid, vnivel = SIN_GEOMETRIA_FISICA_3D, None, None
            else:
                comparacion = comparar_intervalo_3d(
                    p_i, p_j, tramo[0], tramo[1], TOL_3D)
                if comparacion["ok"]:
                    estado, vid, vnivel = "1A1", cands[0], nivel_col
                else:
                    estado, vid, vnivel = SIN_GEOMETRIA_FISICA_3D, None, None

        elif tipo == "viga":
            p_i = (x_i, z_i, y_i)
            p_j = (x_j, z_j, y_j)
            egy = [(a, b) for a, b in
                   [(p[0], p[1]) for p in (p_i, p_j)]]
            one2one = []
            contenida = []
            for bid, pts in g["vigas"].items():
                a, b = pts[0], pts[-1]
                extremos_iguales = (
                    (cercano(a[0], p_i[0]) and cercano(a[1], p_i[1]) and cercano(a[2], p_i[2])
                     and cercano(b[0], p_j[0]) and cercano(b[1], p_j[1]) and cercano(b[2], p_j[2]))
                    or
                    (cercano(a[0], p_j[0]) and cercano(a[1], p_j[1]) and cercano(a[2], p_j[2])
                     and cercano(b[0], p_i[0]) and cercano(b[1], p_i[1]) and cercano(b[2], p_i[2]))
                )
                if extremos_iguales:
                    one2one.append(bid)
                elif (punto_en_segmento((p_i[0], p_i[2]), (a[0], a[2]), (b[0], b[2]))
                      and punto_en_segmento((p_j[0], p_j[2]), (a[0], a[2]), (b[0], b[2]))):
                    contenida.append(bid)
            if len(one2one) == 1:
                estado, vid, vnivel = "1A1", one2one[0], nivel
            elif len(contenida) == 1:
                estado, vid, vnivel = "CONTENIDO", contenida[0], nivel

        elif tipo == "muro":
            # El FE es un elemento vertical 1D en (u,v); el viewer dibuja el muro como
            # panel (segmento en el plano (u,v) a la cota del nivel). Referencia por
            # contencion: el eje (u,v) del muro FE dentro de la zona de un panel.
            # 1) candidatos por distancia a la polilinea del panel (TOL_MURO cubre la
            #    excentricidad de la franja respecto al eje del panel, 0.125-0.31 m).
            # 2) unico candidato -> CONTENIDO; >1 -> esquina compartida por paneles:
            #    resolucion determinista por colinealidad del largo de franja.
            p_uv = (x_i, y_i)
            cands = []
            for mid, pts in g["muros"].items():
                d = dist_punto_polilinea(p_uv, pts)
                if d <= TOL_MURO:
                    cands.append((d, mid, pts))
            if len(cands) == 1:
                estado, vid, vnivel = "CONTENIDO", cands[0][1], nivel
            elif len(cands) > 1:
                # pie en union de paneles (esquina); se prefiere la menor distancia
                cands.sort(key=lambda c: c[0])
                d_min = cands[0][0]
                # mismo panel si el mas cercano esta claramente mas cerca
                if len(cands) == 1 or cands[1][0] - d_min > TOL_MURO / 2:
                    estado, vid, vnivel = "CONTENIDO", cands[0][1], nivel
                else:
                    vid = _resolver_esquina(el, cands)
                    if vid is not None:
                        estado, vnivel = "CONTENIDO", nivel

        out[tag] = {"estado": estado, "viewer_id": vid, "viewer_nivel": vnivel}

    return out


def generar(edificio: str) -> dict:
    fuerzas = leer_superposicion(edificio)
    if edificio == "I":
        meta = leer_metadata_I()
        fuente_meta = str(FUENTE_CSV_I.relative_to(RAIZ))
        niveles = ["CP1S", "P1", "P2", "P3", "P4"]
    else:
        meta = leer_metadata_II()
        fuente_meta = str(FUENTE_BUILDER_II.relative_to(RAIZ))
        niveles = ["EII_CP1S", "EII_CP1", "EII_CP2", "EII_CP3", "EII_CP4"]

    assert set(meta) == set(fuerzas["G"]), (
        f"edificio {edificio}: tags metadata ({len(meta)}) != tags superposicion ({len(fuerzas['G'])})"
    )
    geo = leer_geometria_viewer(edificio)
    emparejado = emparejar(meta, geo)

    elementos = []
    for tag in sorted(fuerzas["G"]):
        el = meta[tag]
        elementos.append({
            "tag": tag,
            "tipo": el["tipo"],
            "nivel": el["nivel"],
            "seccion": el["seccion"],
            "nodo_i": el["nodo_i"],
            "nodo_j": el["nodo_j"],
            "p_i_unity": [round(v, 9) for v in el["p_i_unity"]],
            "p_j_unity": [round(v, 9) for v in el["p_j_unity"]],
            "correspondencia": {
                "estado": emparejado[tag]["estado"],
                "viewer_id": emparejado[tag]["viewer_id"],
                "viewer_nivel": emparejado[tag]["viewer_nivel"],
            },
            "fuerzas": {caso: [round(float(v), 6) for v in fuerzas[caso][tag]] for caso in CASOS},
        })

    resumen: dict = {}
    for el in elementos:
        key = (el["tipo"], el["correspondencia"]["estado"])
        resumen[key] = resumen.get(key, 0) + 1

    return {
        "formato": FORMATO,
        "edificio": edificio,
        "generado_por": str(Path(__file__).name),
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fuente": str((FUENTE_SUPERPOSICION / f"verificacion_superposicion_completa_{edificio}.json").relative_to(RAIZ)),
        "fuente_metadata": fuente_meta,
        "unidades": {"carga": "kN", "momento": "kN*m", "longitud": "m"},
        "frame": {"nota": "Unity (X, Y, Z) = (u, cota, v); posiciones LOCALES del edificio (sin Placement)",
                  "api": "agregar Position del edificio para posicionar en el mundo"},
        "convencion_localForce": CONVENCION,
        "indices_componentes": INDICES,
        "casos": CASOS,
        "caso_COMBINADA": {
            "orrigen": "corrida FE EXPLICITA (NO recalculada)",
            "dicta": "1.0*G + 0.7*Q + 0.3*EX + (-0.2)*EY (config/superposicion.json, DEMOSTRACION_ARBITRARIA)",
        },
        "redondeo": {"fuerzas": 6, "coordenadas": 9,
                     "nota": "valores copiados tal cual de la fuente; no se recalculan"},
        "n_elementos": len(elementos),
        "lista_niveles": niveles,
        "niveles_geometry_viewer": sorted(geo),
        "resumen_por_tipo_estado": {f"{k[0]}__{k[1]}": v for k, v in sorted(resumen.items())},
        "elementos": elementos,
    }


def escribir(edificio: str) -> Path:
    data = generar(edificio)
    salida = (
        GEOMETRIA_VIEWER / edificio / "results" / f"esfuerzos_FE_EDIFICIO_{edificio}.json"
    )
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return salida


def main(argv=None) -> int:
    edificios = argv[1:] or ["I", "II"]
    total = {"n": 0, "fuerzas": 0}
    for edificio in edificios:
        salida = escribir(edificio)
        data = json.loads(salida.read_text(encoding="utf-8"))
        n = data["n_elementos"]
        f = sum(len(el["fuerzas"]) for el in data["elementos"])
        total["n"] += n
        total["fuerzas"] += f
        print(f"{salida.relative_to(RAIZ)}: {n} elementos, {f} vectores de 12 componentes")
        resumen = data["resumen_por_tipo_estado"]
        print("   resumen:", "; ".join(f"{k}={v}" for k, v in resumen.items()))
    print(f"TOTAL: {total['n']} elementos, {total['fuerzas']} vectores")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))