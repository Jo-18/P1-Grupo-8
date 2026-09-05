"""Cargas gravitacionales de losa -> descarga sobre vigas/muros (nodos FE).

Para cada losa se separan los componentes de carga:
  - PP      = peso propio real (area_neta_geometrica * e * rho)
  - PM.ADIC = cargas superficiales permanentes (sobre el area neta de carga)
  - SC      = carga variable (solo si el caso la incluye; el caso G del laboratorio
              aplica PP + PM.ADIC, sin SC salvo indicacion).

La carga de cada componente se reparte entre los receptores portantes documentados
(`apoyos_validos` de viga/muro) mediante reparto por soporte mas cercano sobre una
malla uniforme del dominio neto (se conserva la geometria de las regiones tributarias
para visualizacion en Unity). La carga de cada receptor se vierte a sus nodos FE con
pesos PROPORCIONALES a la longitud de segmento (descarga distribuida sobre la viga),
NO a partes iguales entre los extremos. Un receptor con carga pero sin nodos FE se
reporta como error, NO se descarta silenciosamente.

Unidades: kN. Peso propio (coherente con el proyecto) PP = e(m) * 2500 kgf/m3
= e*24.5166 kN/m3.
"""

from __future__ import annotations

import math
from typing import Dict, List

from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union

from .hipotesis import GRAV_KGF_TO_KN
from .geometria_fe import construir_superficies

DENSIDAD_KGF_M3 = 2500.0
PP_NM3 = DENSIDAD_KGF_M3 * GRAV_KGF_TO_KN   # ~24.5166 kN/m3


def _receptor_lineas(nivelFE):
    """Devuelve {receptor_id: LineString} de vigas y muros del nivel en planta."""
    out = {}
    for v in nivelFE.vigas:
        pts = [(p[0], p[1]) for p in v["pts"]]
        if len(pts) >= 2:
            out[v["id"]] = LineString(pts)
    for m in nivelFE.muros:
        out[m["id"]] = LineString([(m["ua"], m["va"]), (m["ub"], m["vb"])])
    return out


def _carga_superficial_por_losa(nivelFE, cargas_por_losa):
    """cargas_por_losa: {losa_id: (pm_adic_kn_m2, sc_kn_m2)} ya en kN/m2.

    Devuelve por losa PP (peso propio, sobre el AREA NETA geometrica real de la losa),
    y PM.ADIC / SC (superficiales correlacionadas, sobre el area neta de carga de la
    correlacion). PP es un componente distinto de PM.ADIC/SC y NO se mezcla con ellos:
    el caso G del laboratorio aplica PP + PM.ADIC (sin SC a menos que se indique)."""
    res = {}
    for lo in nivelFE.losas:
        pm, sc = cargas_por_losa.get(lo["id"], (0.0, 0.0))
        res[lo["id"]] = {"pm_adic_kn_m2": pm, "sc_kn_m2": sc,
                         "pp_kn_m2": lo["espesor"] * PP_NM3}
    return res


def distribuir_losa(losa_neto, soportes: Dict[str, LineString], mallado=0.25):
    """Reparte el area del dominio neto entre soportes por distancia mas cercana.

    Devuelve (bins_area, bins_cells):
      - bins_area: {receptor_id: area_m2} (suma = area neta geometrica).
      - bins_cells: {receptor_id: [cuadricula de area_neto asignada a este soporte]},
        conserva la GEOMETRIA de cada region tributaria (para visualizacion en Unity).
    Cada celda de la malla se intersecta con el dominio neto y se asigna al soporte
    mas cercano por su centroide. La geometria conservada no se renormaliza (lo que la
    malla asigna es lo que se reporta); el area total asignada = area neta (dentro del
    error de discretizacion de borde).
    """
    if soportes is None or not soportes or losa_neto.area <= 0:
        return {}, {}
    minx, miny, maxx, maxy = losa_neto.bounds
    areas = {}
    cells = {}
    nx = max(int((maxx - minx) / mallado), 1)
    ny = max(int((maxy - miny) / mallado), 1)
    step_x = (maxx - minx) / nx
    step_y = (maxy - miny) / ny
    ids = list(soportes.keys())
    for i in range(nx):
        for j in range(ny):
            cx = minx + (i + 0.5) * step_x
            cy = miny + (j + 0.5) * step_y
            cell = Polygon([(cx - step_x/2, cy - step_y/2),
                            (cx + step_x/2, cy - step_y/2),
                            (cx + step_x/2, cy + step_y/2),
                            (cx - step_x/2, cy + step_y/2)])
            cell = cell.intersection(losa_neto)
            if cell.area <= 0:
                continue
            p = Point(cx, cy)
            best = min(ids, key=lambda rid: soportes[rid].distance(p))
            areas[best] = areas.get(best, 0.0) + cell.area
            cells.setdefault(best, []).append({"x": round(cx, 3), "y": round(cy, 3),
                                               "area_m2": round(cell.area, 5)})
    return areas, cells


def _pesos_por_nodo(key_of_tag, nodos):
    """Pesos de descarga de un receptor a sus nodos FE, PROPORCIONALES a la longitud
    de cada segmento entre nodos consecutivos (misma filosofia que cargas nodales
    consistentes de una distribucion uniforme sobre el receptor). La carga total del
    receptor (F = area_tributaria x q) se reparte entre sus nodos con peso = semi-
    longitud propia: extremos 0.5*L_seg, interior 0.5*(L_izq+L_der). De este modo un
    receptor con muchos nodos intermedios recibe carga distribuida y no puntual en
    sus extremos. `key_of_tag` -> coord (u,v,z); `nodos` = tags del receptor en orden."""
    nodos = list(dict.fromkeys(nodos))
    if len(nodos) == 0:
        return {}
    if len(nodos) == 1:
        return {nodos[0]: 1.0}
    def ll(t):
        return key_of_tag[t][:2]
    orden = sorted(nodos, key=lambda t: (ll(t)[0], ll(t)[1]))
    segs = [math.dist(ll(orden[i]), ll(orden[i + 1])) for i in range(len(orden) - 1)]
    Ltot = sum(segs)
    if Ltot <= 0:
        return {t: 1.0 / len(nodos) for t in orden}
    w = {}
    for k, t in enumerate(orden):
        acc = 0.0
        if k > 0:
            acc += 0.5 * segs[k - 1]
        if k < len(segs):
            acc += 0.5 * segs[k]
        w[t] = acc / Ltot
    return w


def calcular_cargas_nodales(nivelFE, nodos_por_receptor, cargas_por_losa, key_of_tag,
                            incluir_sc=True, mallado=0.25):
    """Descarga de losa -> receptor -> nodos FE, con componentes separados.

    Para cada losa:
      PP_total     = area_neta_geometrica * e * rho  (peso propio real de la losa)
      PM_adic_total= pm_kn_m2 * area_superficial_carga
      SC_total     = sc_kn_m2 * area_superficial_carga  (solo si incluir_sc=True)

    (PP es un componente distinto de PM.ADIC/SC; el caso G del laboratorio aplica
    PP + PM.ADIC, con SC solo si incluir_sc -- ver llamada en main_fe.)

    Cada componente se reparte por area tributaria (celdas mas cercanas a un receptor;
    _distribuir_losa conserva la geometria) y la carga de cada receptor se vierte a sus
    nodos FE con pesos PROPORCIONALES a la longitud de segmento (_pesos_por_nodo), NO a
    partes iguales entre nodos (descarga distribuida sobre la viga). Un receptor con
    carga pero SIN nodos FE se reporta como error (receptores_sin_fe), no se descarta.

    Devuelve (cargas_nodales, reparto):
      cargas_nodales: {tag: [0,0,-F,0,0,0]}
      reparto: {"por_losa": {losa_id: {...}}, "geometry": {losa_id: {receptor_id:[celdas]}},
                "receptores_sin_fe": [...], "area_no_asignada_total_m2": ...}
    """
    soportes = _receptor_lineas(nivelFE)
    surf = _carga_superficial_por_losa(nivelFE, cargas_por_losa)
    from .geometria_fe import construir_superficies as _cs
    geometria = {}
    for lo in nivelFE.losas:
        s = _cs([lo])[0]
        geometria[lo["id"]] = {"neto": s["neto"], "bruto": s["bruto"],
                               "poligono": lo["poligono"], "aberturas": lo["aberturas"],
                               "area_neta_m2": s["neto"].area}

    cargas = {}
    por_losa = {}
    todas_celdas = {}
    receptores_sin_fe = []

    for lo in nivelFE.losas:
        g = geometria[lo["id"]]
        neto = g["area_neta_m2"]
        s = surf[lo["id"]]
        pp_dens = s["pp_kn_m2"]
        pm_k = s["pm_adic_kn_m2"]
        sc_k = s["sc_kn_m2"]
        pm_total = pm_k * neto
        pp_total = neto * pp_dens
        sc_total = sc_k * neto if incluir_sc else 0.0

        validos = set(soportes.keys())
        if lo.get("apoyos"):
            validos = set(lo["apoyos"])
        ss = {k: v for k, v in soportes.items() if k in validos}
        areas, celdas = distribuir_losa(g["neto"], ss, mallado)

        info_losa = {"area_neta_geometrica_m2": round(neto, 4),
                     "area_superficial_carga_m2": round(neto, 4),
                     "area_asignada_receptores_m2": round(sum(areas.values()), 4),
                     "area_no_asignada_m2": round(neto - sum(areas.values()), 4),
                     "por_comp_kN": {"pp": round(pp_total, 4),
                                     "pm_adic": round(pm_total, 4),
                                     "sc": round(sc_total, 4),
                                     "total": round(pp_total + pm_total + sc_total, 4)},
                     "receptores": {}}
        para_componentes = (pp_total, pm_total, sc_total)
        suma_area = sum(areas.values())
        for rid, area in areas.items():
            frac = area / suma_area if suma_area > 0 else 0.0
            F = sum(frac * c for c in para_componentes)
            nodos = nodos_por_receptor.get(rid, [])
            if not nodos:
                receptores_sin_fe.append({"receptor": rid, "losa": lo["id"],
                                          "area_m2": round(area, 4),
                                          "carga_kN": round(F, 4)})
                continue
            pesos = _pesos_por_nodo(key_of_tag, nodos)
            info_losa["receptores"][rid] = {
                "area_m2": round(area, 4), "carga_total_kN": round(F, 4),
                "n_nodos_fe": len(nodos)}
            for tag, w in pesos.items():
                cur = cargas.get(tag, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                cur[2] -= F * w
                cargas[tag] = cur
        por_losa[lo["id"]] = info_losa
        todas_celdas[lo["id"]] = celdas
    return cargas, {"por_losa": por_losa, "geometry": todas_celdas,
                    "receptores_sin_fe": receptores_sin_fe,
                    "area_no_asignada_total_m2":
                        round(sum(v["area_no_asignada_m2"] for v in por_losa.values()), 4)}
