"""
Paquete de analisis estructural del Edificio I.

Reutiliza el motor de areas tributarias de ``areas_tributarias`` (produccion) y
``ensayo_visibilidad`` (experimental) y anade la capa de casos de ensayo,
validacion, conversion de cargas y ensamblador estructural.

Nada aqui modifica los JSON congelados de ``datos/geometria``.
"""

from .caso_ensayo import CasoEnsayo, cargar_caso
from .validadores import ErrorEntrada, ProblemaEntrada
from .cargas import convertir_cargas, InformeCargas
from .ensamblador import ModeloEnsamblador

__all__ = [
    "CasoEnsayo",
    "cargar_caso",
    "ErrorEntrada",
    "ProblemaEntrada",
    "convertir_cargas",
    "InformeCargas",
    "ModeloEnsamblador",
]