"""
Modulo de Areas Tributarias - Edificio de Ingenieria.

Módulo independiente que, a partir de la geometria canonica de un nivel
(losas, vigas, muros, aberturas, bordes libres y cargas superficiales),
calcula areas tributarias, anchos tributarios y cargas lineales distribuidas
sobre los elementos de soporte, validando conservacion de area y carga.
"""

from .modelo import (
    ModeloGeometria,
    Panel,
    Receptor,
    Abertura,
    CargaSuperficial,
    ConfigCalculo,
)
from .tributacion import (
    ResultadoPanel,
    RegionTributaria,
    calcular_paneles,
)
from .cargas import CargaLineal, transformar
from . import validacion
from . import viz
from .io import leer_geometria

__all__ = [
    "ModeloGeometria",
    "Panel",
    "Receptor",
    "Abertura",
    "CargaSuperficial",
    "ConfigCalculo",
    "ResultadoPanel",
    "RegionTributaria",
    "CargaLineal",
    "calcular_paneles",
    "transformar",
    "validacion",
    "viz",
    "leer_geometria",
]
