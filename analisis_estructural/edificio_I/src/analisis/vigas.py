"""
Interfaz FUTURA para la clasificacion de vigas segun colaboracion de losa.

NO calcula esfuerzos, armaduras, perfiles, resistencia ni deformaciones. Tampoco
clasifica vigas L/T/rectangulares: esa clasificacion depende de geometria, continuidad,
material, ancho efectivo y norma de diseno y NO debe inferirse solo desde las areas
tributarias.

Este modulo deja preparado el contrato (tipos y registro) para que una futura fase de
diseno llene cada viga. Hasta entonces toda viga queda ``por_definir``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

# Clases de colaboracion de losa de una viga (identificacion topologica de las losas
# contiguas, NO la seccion final de diseno).
T_SECCION_NOTECNICA = "por_definir"
SECCION_POSIBLE_T = "posible_T"          # losa a ambos lados
SECCION_POSIBLE_L = "posible_L"          # losa a un solo lado (borde)
SECCION_RECTANGULAR = "rectangular"      # sin colaboracion de losa


@dataclass
class VigaPendiente:
    """Viga sin clasificar: se registra la geometria que se le CONOCE tal cual."""

    id: str
    nivel: str = ""
    edificio: str = "Edificio I"
    losas_lado_a: tuple = ()
    losas_lado_b: tuple = ()
    # Inputs que haran falta para clasificar (no se inventan):
    continuidad: Optional[str] = None
    material: Optional[str] = None
    ancho_efectivo_m: Optional[float] = None
    norma_diseno: Optional[str] = None

    @property
    def colaboracion_observada(self) -> str:
        """Solo si se tienen ambas caras se sugiere una posible seccion; nunca final."""
        if self.losas_lado_a and self.losas_lado_b:
            return SECCION_POSIBLE_T
        if self.losas_lado_a or self.losas_lado_b:
            return SECCION_POSIBLE_L
        return SECCION_RECTANGULAR

    @property
    def estado_clasificacion(self) -> str:
        # la clasificacion final depende de continuidad/material/b_efectivo/norma; hasta
        # tenerlos sigue por_definir aunque se observen losas a uno/dos lados.
        if not (self.continuidad and self.material and self.ancho_efectivo_m
                is not None and self.norma_diseno):
            return T_SECCION_NOTECNICA
        return self.colaboracion_observada


class RegistroVigasSinDiseno:
    """Registro de vigas con su estado de clasificacion (todo por_definir por ahora)."""

    def __init__(self) -> None:
        self.vigas: Dict[str, VigaPendiente] = {}

    def registrar(self, v: VigaPendiente) -> None:
        self.vigas[v.id] = v

    def todas_por_definir(self) -> bool:
        return all(v.estado_clasificacion == T_SECCION_NOTECNICA for v in self.vigas.values())