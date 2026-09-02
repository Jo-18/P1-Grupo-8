"""
Modulo de lecturas de geometria - Edificio de Ingenieria (publicacion minima).

Exposicion publica: lector del JSON canonico y el modelo de datos, sin
acoplar los modulos de calculo de areas tributarias.
"""

from .modelo import ModeloGeometria
from .io import leer_geometria

__all__ = ["ModeloGeometria", "leer_geometria"]