"""Discretizacion en fibras tipo 'Fiber Section' de OpenSees.

`fibras()` replica el patron de ops.section('Fiber') + ops.fiber(): una malla de
fibras de hormigon mas fibras puntuales de acero. `seccion_opensees()` construye la
misma seccion dentro de OpenSees (opcional) para cross-check de areas.
"""

from __future__ import annotations

import numpy as np


def fibras(seccion):
    """-> (ys, zs, areas, tags): fibras de hormigon (tag=1) y acero (tag=2)."""
    yc, zc, ac = seccion.fibra_concreto()
    ya, za, aa = seccion.fibra_acero()
    ys = np.concatenate([yc, ya])
    zs = np.concatenate([zc, za])
    areas = np.concatenate([ac, aa])
    tags = np.concatenate([np.ones_like(yc, dtype=int),
                           np.full_like(ya, 2, dtype=int)])
    return ys, zs, areas, tags


def area_total_fibras(seccion) -> float:
    _, _, areas, _ = fibras(seccion)
    return float(areas.sum())


def seccion_opensees(seccion, ops):
    """Construye la seccion en openseespy con la misma discretizacion de fibras.
    Devuelve el tap de seccion y los modelos de material creados."""
    import openseespy.opensees as ops  # noqa: F401 (import local)
    sec_tag = 1
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    ys, zs, areas, tags = fibras(seccion)
    # materiales: hormigon (tag 1) y acero (tag 2) con familias Concrete01/Steel02
    ops.uniaxialMaterial("Concrete01", 1,
                         -seccion.hormigon.fc, -seccion.hormigon.eps0,
                         -seccion.hormigon.fcu, -seccion.hormigon.epsu)
    epsy = seccion.acero.fy / seccion.acero.Es
    Ep = seccion.acero.Ep
    b = Ep / seccion.acero.Es  # relacion de endurecimiento (Steel01)
    fy = seccion.acero.fy
    ops.uniaxialMaterial("Steel01", 2, fy, seccion.acero.Es, b)
    ops.section("Fiber", sec_tag)
    for y, z, a, t in zip(ys, zs, areas, tags):
        ops.fiber(y, z, a, int(t))
    return sec_tag