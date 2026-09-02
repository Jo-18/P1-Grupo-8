"""
Entrada de la geometria canonica (publicacion minima).

Expone unicamente la lectura del JSON canonico hacia ``ModeloGeometria``.
No escribe resultados ni diccionarios de salida; para eso existe el pipeline
de calculo, que no forma parte de esta publicacion.
"""

from __future__ import annotations

import json

from .modelo import ModeloGeometria


def leer_geometria(ruta: str) -> ModeloGeometria:
    """Lee un archivo JSON canonico y devuelve el ModeloGeometria.

    Conserva las secciones del contrato (losas, vigas, muros, columnas,
    aberturas, bordes, juntas, interfaces y metadatos) sin ejecutar calculo
    estructural.

    Lanza ValueError si una losa referencia una abertura inexistente o un
    apoyo inexistente (no se descarta silenciosamente).
    """
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ModeloGeometria.from_dict(data)