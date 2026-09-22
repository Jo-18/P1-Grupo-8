"""
Transformacion de cargas superficiales a cargas lineales distribuidas.

Para cada borde soportado de una losa, la carga superficial q (kN/m2) sobre el
area tributaria del borde produce una carga lineal equivalente distribuida a lo
largo del borde (kN/m). El perfil de esta carga (triangular, trapezoidal o
uniforme) se reconstruye a partir del ancho tributario w(s) a lo largo del borde.

Resultado por borde:
    - perfil w_lineal(s) = q * ancho(s)   [kN/m]
    - integral = area_tributaria * q      [kN]
    - clasificacion del perfil (triangular/trapezoidal/uniforme)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .tributacion import RegionTributaria, ResultadoPanel


@dataclass
class CargaLineal:
    borde_id: str
    elemento_soporte: str
    tipo_perfil: str            # triangular | trapezoidal | uniforme
    longitud: float             # m
    w_max: float                # kN/m (maximo)
    w_min: float                # kN/m (minimo)
    integral: float             # kN (area * q)
    zona_constante: float = 0.0 # m de w_max (para trapezoidal)
    q: float = 0.0              # kN/m2 aplicada


def _clasificar_perfil(w: np.ndarray, q: float, tol: float = 1e-6) -> Tuple[str, float, float]:
    """Clasifica el perfil y devuelve (tipo, w_max, w_min).

    Reglas:
      - uniforme:      el ancho es (casi) constante a lo largo del borde
      - trapezoidal:   existe una meseta (zona central) cerca del ancho maximo
      - triangular:    el maximo se alcanza en un unico pico (sin meseta)
    """
    if w.size < 3:
        return ("uniforme", 0.0, 0.0)
    w = np.asarray(w, dtype=float)
    wmax = float(np.max(w))
    wmin = float(np.min(w))
    if wmax <= tol:
        return ("uniforme", 0.0, 0.0)
    if (wmax - wmin) <= tol * max(1.0, wmax):
        return ("uniforme", wmax, wmax)
    # fraccion de la longitud con ancho "en meseta" (>= 99% del maximo)
    meseta = float(np.mean(w >= 0.99 * wmax))
    if meseta >= 0.02:
        return ("trapezoidal", wmax, wmin)
    return ("triangular", wmax, 0.0)


def transformar(panel_result: ResultadoPanel, q: float) -> List[CargaLineal]:
    """Convierte las regiones tributarias de un panel en cargas lineales por borde."""
    cargas: List[CargaLineal] = []
    for r in panel_result.regiones:
        w_lineal = r.carga(q)  # r.w * q
        tipo, _, _ = _clasificar_perfil(w_lineal, q)
        # w_max exacto a partir del ancho tributario maximo de la region
        w_max = float(r.ancho_max) * q
        w_min = 0.0 if tipo == "triangular" else (
            float(np.min(w_lineal)) if w_lineal.size else 0.0
        )
        # zona constante (donde w ~ wmax) para trapezoidales
        zona_const = 0.0
        if tipo == "trapezoidal" and w_lineal.size > 2:
            mask = w_lineal >= (w_max - 1e-9)
            zona_const = float(np.sum(mask)) / max(1, w_lineal.size - 1) * r.borde.longitud
        cargas.append(
            CargaLineal(
                borde_id=r.borde.id,
                elemento_soporte=r.borde.elemento_soporte,
                tipo_perfil=tipo,
                longitud=r.borde.longitud,
                w_max=w_max,
                w_min=w_min,
                integral=r.area * q,
                zona_constante=zona_const,
                q=q,
            )
        )
    return cargas
