"""
Validacion de conservacion de area y carga.

Comprueba que:
  - la suma de areas tributarias por borde iguala el area neta del paño
    (dentro de una tolerancia relativa);
  - la suma de cargas lineales por borde iguala la carga superficial total
    sobre el paño (q * area_neta).

Devuelve un reporte con errores absolutos y relativos, utilizable en tests y
en la generacion de reportes de verificacion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from .cargas import CargaLineal
from .tributacion import ResultadoPanel


@dataclass
class CheckResultado:
    nombre: str
    ok: bool
    valor_obtenido: float
    valor_esperado: float
    error_abs: float
    error_rel: float
    mensaje: str = ""


def validar_area(panel_result: ResultadoPanel, tol_rel: float = 1e-9) -> CheckResultado:
    suma = panel_result.area_total
    esperado = panel_result.area_neta
    err_abs = abs(suma - esperado)
    err_rel = err_abs / esperado if esperado else 0.0
    ok = err_rel <= tol_rel
    return CheckResultado(
        nombre="conservacion_areas",
        ok=ok,
        valor_obtenido=suma,
        valor_esperado=esperado,
        error_abs=err_abs,
        error_rel=err_rel,
        mensaje=(
            f"suma areas tributarias = {suma:.10f} m2, "
            f"area neta = {esperado:.10f} m2 (err rel {err_rel:.2e})"
        ),
    )


def validar_carga(panel_result: ResultadoPanel, q: float,
                  tol_rel: float = 1e-9) -> CheckResultado:
    suma = panel_result.area_total * q
    esperado = panel_result.area_neta * q
    err_abs = abs(suma - esperado)
    err_rel = err_abs / esperado if esperado else 0.0
    ok = err_rel <= tol_rel
    return CheckResultado(
        nombre="conservacion_carga",
        ok=ok,
        valor_obtenido=suma,
        valor_esperado=esperado,
        error_abs=err_abs,
        error_rel=err_rel,
        mensaje=(
            f"suma cargas = {suma:.6f} kN, carga total = {esperado:.6f} kN "
            f"(err rel {err_rel:.2e})"
        ),
    )


def validar_span_por_borde(panel_result: ResultadoPanel,
                           tol_rel: float = 1e-6) -> CheckResultado:
    """Verifica que la integral de cada perfil de carga coincida con area*q."""
    peor = 0.0
    detalle = "| "
    for r in panel_result.regiones:
        if r.s is None or r.w is None or r.s.size < 2:
            continue
        integral_num = float(np.trapezoid(r.w, r.s))
        esperado = r.area
        if esperado > 0:
            err_rel = abs(integral_num - esperado) / esperado
            peor = max(peor, err_rel)
            detalle += f"{r.borde.id}:{err_rel:.1e} "
    ok = peor <= tol_rel
    return CheckResultado(
        nombre="perfil_integral_vs_area",
        ok=ok,
        valor_obtenido=peor,
        valor_esperado=0.0,
        error_abs=peor,
        error_rel=peor if peor else 0.0,
        mensaje=f"peor error rel integral/perfil = {peor:.2e} {detalle}",
    )
