"""
Geometria plana - utilidades de poligonos convexos.

Funciones numpy-only para poligonos, usadas por el modulo de areas tributarias:
area, centroide, orientacion, pertenencia, recorte por semiplano e interseccion
de poligonos convexos.

Convenciones:
- Un poligono es una lista de puntos [(x0,y0), (x1,y1), ...] o un arreglo numpy (n,2).
- El area es positiva para vertices en sentido ANTIHORARIO (CCW).
"""

from __future__ import annotations

from typing import List, Sequence

import numpy as np

Pt = Sequence[float]
Poly = List[Pt]


# --------------------------------------------------------------------------- #
# Operaciones basicas
# --------------------------------------------------------------------------- #
def to_array(poly: Sequence[Pt]) -> np.ndarray:
    return np.asarray(poly, dtype=float)


def polygon_area(poly: Sequence[Pt]) -> float:
    """Area (con signo) por shoelace. CCW -> positiva."""
    p = to_array(poly)
    if len(p) < 3:
        return 0.0
    x = p[:, 0]
    y = p[:, 1]
    # formula shoelace: 0.5 * sum(x_i*y_{i+1} - x_{i+1}*y_i)
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def polygon_area_abs(poly: Sequence[Pt]) -> float:
    return abs(polygon_area(poly))


def polygon_centroid(poly: Sequence[Pt]) -> Pt:
    """Centroide de poligono simple (funciona para convexo/concavo simple)."""
    p = to_array(poly)
    if len(p) < 3:
        return (float(np.mean(p[:, 0])), float(np.mean(p[:, 1])))
    x = p[:, 0]
    y = p[:, 1]
    cross = x * np.roll(y, -1) - np.roll(x, -1) * y
    a = 0.5 * float(np.sum(cross))
    if abs(a) < 1e-15:
        return (float(np.mean(x)), float(np.mean(y)))
    cx = float(np.sum((x + np.roll(x, -1)) * cross)) / (6.0 * a)
    cy = float(np.sum((y + np.roll(y, -1)) * cross)) / (6.0 * a)
    return (cx, cy)


def is_ccw(poly: Sequence[Pt]) -> bool:
    return polygon_area(poly) >= 0.0


def ensure_ccw(poly: Sequence[Pt]) -> Poly:
    pts = [tuple(float(v) for v in pp) for pp in poly]
    if polygon_area(pts) < 0.0:
        pts = pts[::-1]
    return pts


def is_convex(poly: Sequence[Pt], tol: float = 1e-9) -> bool:
    """True si el poligono es estrictamente convexo (sin colinealidades)."""
    p = to_array(poly)
    n = len(p)
    if n < 3:
        return False
    signs = []
    for i in range(n):
        a = p[i]
        b = p[(i + 1) % n]
        c = p[(i + 2) % n]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        signs.append(cross)
    if all(abs(s) > tol for s in signs):
        return all(s > 0 for s in signs) or all(s < 0 for s in signs)
    return False


def point_in_convex(poly: Sequence[Pt], pt: Pt, tol: float = 1e-9) -> bool:
    """Test de pertenencia a poligono convexo (asume CCW)."""
    p = to_array(poly)
    q = np.asarray(pt, dtype=float)
    n = len(p)
    for i in range(n):
        a = p[i]
        b = p[(i + 1) % n]
        cross = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
        if cross < -tol:
            return False
    return True


# --------------------------------------------------------------------------- #
# Recorte por semiplano y por poligono (Sutherland-Hodgman)
# --------------------------------------------------------------------------- #
def clip_convex_halfplane(
    poly: Poly, a: Pt, b: float, tol: float = 1e-12
) -> Poly:
    """Recorta un poligono convexo por el semiplano {a . p <= b}.

    a: (ax, ay). Conserva puntos que cumplen ax*x + ay*y <= b.
    Devuelve el poligono resultante (posiblemente vacio).
    """
    a = np.asarray(a, dtype=float)
    out: List[Pt] = []

    def inside(p):
        return float(a[0] * p[0] + a[1] * p[1]) <= b + tol

    def intersect(s, e):
        # interseccion del segmento s-e con la recta a.p = b
        ds = a[0] * s[0] + a[1] * s[1] - b
        de = a[0] * e[0] + a[1] * e[1] - b
        t = ds / (ds - de)
        return (s[0] + t * (e[0] - s[0]), s[1] + t * (e[1] - s[1]))

    pts = [tuple(float(v) for v in pp) for pp in poly]
    if not pts:
        return []
    n = len(pts)
    for i in range(n):
        s = pts[i]
        e = pts[(i + 1) % n]
        if inside(s):
            out.append(s)
            if not inside(e):
                out.append(intersect(s, e))
        else:
            if inside(e):
                out.append(intersect(s, e))
    return out


def convex_intersection(p1: Poly, p2: Poly) -> Poly:
    """Interseccion de dos poligonos convexos (CCW cada uno)."""
    result = [tuple(float(v) for v in pp) for pp in p1]
    clip_poly = to_array(p2)
    m = len(clip_poly)
    if not result:
        return []
    for i in range(m):
        a = clip_poly[i]
        b = clip_poly[(i + 1) % m]
        normal = (a[1] - b[1], b[0] - a[0])  # normal hacia el interior (CCW)
        cval = normal[0] * a[0] + normal[1] * a[1]
        result = clip_convex_halfplane(result, normal, cval)
        if not result:
            return []
    return result


def convex_intersection_area(p1: Poly, p2: Poly) -> float:
    return polygon_area_abs(convex_intersection(p1, p2))
