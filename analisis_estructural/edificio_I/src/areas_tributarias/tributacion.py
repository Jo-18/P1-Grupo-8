"""
Nucleo del algoritmo de areas tributarias (metodo de celdas + segmento finito).

METODO
------
Se discretiza el dominio de cada losa (poligono exterior menos aberturas) en una
malla regular de celdas. Cada celda se asigna al receptor (viga o muro) cuya
distancia al SEGMENTO FINITO es minima:

    d(p, seg) = |p - (A + t*(B-A))|   con  t = clamp( ((p-A).(B-A)) / |B-A|^2 , 0, 1 )

Usar la distancia al segmento (no a la recta infinita) evita asignar celdas a la
prolongacion imaginaria de una viga/muro fuera de su longitud fisica. El metodo es
totalmente general: admite paños convexos o concavos, aberturas (que solo quitan
area, nunca son receptores), bordes libres (que no reciben) y receptores interiores
o de borde.

CONSERVACION
------------
La suma de las areas asignadas se renormaliza para que coincida exactamente con el
area neta del dominio. De ahi surge la conservacion de area; y como cada receptor
recibe q * area_tributaria, la suma de cargas es q * A_neta.

ANCHOS Y CARGAS
---------------
Para cada receptor se reconstruye el ancho tributario b_trib(s) a lo largo de su
longitud (extension perpendicular del area asignada en cada posicion s). La carga
lineal distribuida es  w(s) = q * b_trib(s). El perfil se renormaliza para que su
integral coincida con la carga del receptor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import Point, Polygon

from .modelo import Panel, Receptor


@dataclass
class RegionTributaria:
    receptor: Receptor
    area: float                  # m2
    ancho_max: float             # m  (ancho tributario maximo)
    ancho_promedio: float        # m
    celdas: np.ndarray = None    # (n,2) centros de celdas asignadas
    s: np.ndarray = None         # posicion a lo largo del receptor (m)
    btrib: np.ndarray = None     # ancho tributario b_trib(s) (m)
    w: np.ndarray = None         # ancho tributario (m); alias de btrib

    @property
    def borde(self):
        # interfaz retrocompatible: el receptor actuaba como "borde"
        return self.receptor

    def carga(self, q: float) -> np.ndarray:
        if self.btrib is not None:
            return self.btrib * q
        return self.w * q if self.w is not None else None

    def carga_integral(self, q: float) -> float:
        return self.area * q


@dataclass
class ResultadoPanel:
    panel: Panel
    area_neta: float
    area_total_asignada: float
    regiones: List[RegionTributaria] = field(default_factory=list)

    def area_por_borde(self) -> Dict[str, float]:
        return {r.receptor.id: r.area for r in self.regiones}

    def carga_por_borde(self, q: float) -> Dict[str, float]:
        return {r.receptor.id: r.area * q for r in self.regiones}

    @property
    def area_total(self) -> float:
        return sum(r.area for r in self.regiones)

    def receptor_info(self) -> Dict[str, dict]:
        return {
            r.receptor.id: {
                "tipo": r.receptor.tipo,
                "longitud": r.receptor.longitud,
                "area_tributaria_m2": r.area,
                "ancho_max_m": r.ancho_max,
                "ancho_promedio_m": r.ancho_promedio,
            }
            for r in self.regiones
        }


# --------------------------------------------------------------------------- #
# Distancia punto-segmento
# --------------------------------------------------------------------------- #
def _distancia_punto_segmento(px, py, ax, ay, bx, by):
    """Distancia euclidiana del punto (px,py) al segmento finito A-B."""
    dx = bx - ax
    dy = by - ay
    L2 = dx * dx + dy * dy
    if L2 <= 0.0:
        return float(np.hypot(px - ax, py - ay))
    t = ((px - ax) * dx + (py - ay) * dy) / L2
    t = min(1.0, max(0.0, t))
    qx = ax + t * dx
    qy = ay + t * dy
    return float(np.hypot(px - qx, py - qy))


# --------------------------------------------------------------------------- #
# Generacion de celdas dentro del dominio
# --------------------------------------------------------------------------- #
def _generar_celdas(dominio: Polygon, tamano_celda: float) -> np.ndarray:
    """Centros de celdas dentro del dominio (exterior - aberturas)."""
    minx, miny, maxx, maxy = dominio.bounds
    nx = int(np.ceil((maxx - minx) / tamano_celda)) + 1
    ny = int(np.ceil((maxy - miny) / tamano_celda)) + 1
    xs = np.linspace(minx + tamano_celda / 2, maxx - tamano_celda / 2, nx)
    ys = np.linspace(miny + tamano_celda / 2, maxy - tamano_celda / 2, ny)
    gx, gy = np.meshgrid(xs, ys)
    centros = np.column_stack([gx.ravel(), gy.ravel()])
    # filtro por contencion en el dominio (excluye aberturas y exterior)
    puntos = [Point(c) for c in centros]
    dentro = [dominio.covers(p) for p in puntos]
    return centros[np.array(dentro, dtype=bool)]


# --------------------------------------------------------------------------- #
# Calculo completo por panel
# --------------------------------------------------------------------------- #
def calcular_paneles(
    panel: Panel,
    q: float,
    tamano_celda: Optional[float] = None,
    n_samples: int = 300,
    renormalizar: bool = True,
) -> ResultadoPanel:
    """Calcula areas tributarias por celdas para una losa.

    q: carga superficial [kN/m2].
    tamano_celda: tamano de celda [m]. Si es None, se usa 0.05 (o menor si el
        dominio es pequeno).
    """
    if panel.tipo_transferencia not in ("bidireccional", "por_definir"):
        raise ValueError(
            f"Panel '{panel.id}': tipo_transferencia '{panel.tipo_transferencia}' "
            "aun no soportado en esta fase (solo bidireccional/por_definir)."
        )

    receptores = panel.receptores_validos()
    if not receptores:
        raise ValueError(f"Panel '{panel.id}' no tiene receptores.")

    if tamano_celda is None:
        tamano_celda = 0.05

    dominio = panel.dominio
    area_neta = float(dominio.area)

    centros = _generar_celdas(dominio, tamano_celda)
    area_celda = tamano_celda * tamano_celda

    # asignacion: matriz de distancias (ncells, nrec)
    dist = np.zeros((len(centros), len(receptores)))
    for j, r in enumerate(receptores):
        ax, ay = r.inicio
        bx, by = r.fin
        dist[:, j] = [
            _distancia_punto_segmento(px, py, ax, ay, bx, by)
            for px, py in centros
        ]
    asignacion = np.argmin(dist, axis=1)

    areas = np.zeros(len(receptores))
    for j in range(len(receptores)):
        areas[j] = float(np.sum(asignacion == j)) * area_celda

    if renormalizar and areas.sum() > 1e-12:
        factor = area_neta / areas.sum()
        areas = areas * factor

    # perfiles por receptor
    regiones = []
    for j, r in enumerate(receptores):
        mask = asignacion == j
        c_celdas = centros[mask]
        area_j = float(areas[j])
        s_arr, btrib, w_arr = _perfil_receptor(
            r, c_celdas, tamano_celda, n_samples, area_j
        )
        # ancho promedio = area / longitud
        ancho_prom = area_j / r.longitud if r.longitud > 0 else 0.0
        ancho_max = float(np.max(btrib)) if btrib.size else 0.0
        regiones.append(
            RegionTributaria(
                receptor=r, area=area_j, ancho_max=ancho_max,
                ancho_promedio=ancho_prom, celdas=c_celdas,
                s=s_arr, btrib=btrib, w=w_arr,
            )
        )

    return ResultadoPanel(
        panel=panel, area_neta=area_neta,
        area_total_asignada=area_neta, regiones=regiones,
    )


# --------------------------------------------------------------------------- #
# Perfil de ancho/carga por receptor
# --------------------------------------------------------------------------- #
def _perfil_receptor(receptor, celdas, cell, n_samples, area):
    """Reconstruye b_trib(s) y w(s) a lo largo del receptor a partir de sus celdas."""
    ax, ay = receptor.inicio
    bx, by = receptor.fin
    L = receptor.longitud
    if L <= 0:
        s = np.array([0.0]); btrib = np.array([0.0])
        return s, btrib, np.zeros_like(btrib)

    dx = (bx - ax) / L
    dy = (by - ay) / L
    # normal perpendicular
    nx, ny = -dy, dx

    if len(celdas) == 0:
        s = np.linspace(0.0, L, n_samples)
        btrib = np.zeros(n_samples)
        return s, btrib, np.zeros(n_samples)

    # proyeccion a lo largo y distancia perpendicular de cada celda
    rel = celdas - np.array([ax, ay])
    s_proj = rel[:, 0] * dx + rel[:, 1] * dy          # coordenada a lo largo
    s_proj = np.clip(s_proj, 0.0, L)
    d_perp = np.abs(rel[:, 0] * nx + rel[:, 1] * ny)   # distancia perpendicular

    s_vals = np.linspace(0.0, L, n_samples)
    btrib = np.zeros(n_samples)
    media = cell / 2.0
    for k, sk in enumerate(s_vals):
        banda = np.abs(s_proj - sk) <= max(cell, media) + 1e-9
        if np.any(banda):
            btrib[k] = float(np.max(d_perp[banda]))

    # renormalizar para que la integral del perfil iguale el area asignada
    integ = float(np.trapezoid(btrib, s_vals))
    if integ > 1e-15 and area > 0:
        btrib = btrib * (area / integ)

    return s_vals, btrib, btrib  # w (=ancho) == btrib
