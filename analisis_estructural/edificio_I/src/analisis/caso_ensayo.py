"""
Carga de un caso DERIVADO de ensayo del Edificio I.

El caso referencia la geometria congelada por archivo (solo lectura) y aplica
exclusivamente hipotesis de ENSAYO (carga unitaria, tipo de transferencia por losa,
resultado_utilizable_para_diseno=false). Nunca modifica el archivo base.

Requisitos:
  - tipo_caso == "ensayo_geometrico";
  - carga_superficial_kN_m2 presente;
  - resultado_no_utilizable_para_diseno == true;
  - cada losa del nivel tiene una hipotesis explicita de tipo_transferencia;
  - ninguna losa queda en ``por_definir`` (de lo contrario se detiene).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from areas_tributarias.io import leer_geometria
from areas_tributarias.modelo import ModeloGeometria, Panel

from .validadores import (
    TIPOS_ADMISIBLES_ENSAYO,
    ErrorEntrada,
    ProblemaEntrada,
    elevar_si_error,
    validar_para_ensayo,
)


@dataclass
class HipotesisLosa:
    id: str
    tipo_transferencia: str
    origen: str = "hipotesis_ensayo_NO_diseno"
    notas: str = ""


@dataclass
class CasoEnsayo:
    tipo_caso: str
    carga_kN_m2: float
    resultado_utilizable_para_diseno: bool
    archivo_geometria: str
    hash_geometria_al_cargar: str
    modelo: ModeloGeometria
    hipotesis: Dict[str, HipotesisLosa] = field(default_factory=dict)

    @property
    def es_ensayo(self) -> bool:
        return not self.resultado_utilizable_para_diseno

    def transferencia_de(self, panel_id: str) -> str:
        return self.hipotesis[panel_id].tipo_transferencia


def _sha256(ruta: str) -> str:
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def cargar_caso(caso_ruta: str) -> CasoEnsayo:
    """Carga y valida un caso de ensayo contra la geometria congelada (solo lectura)."""
    caso_ruta = Path(caso_ruta)
    with open(caso_ruta, "r", encoding="utf-8") as f:
        caso = json.load(f)

    problemas: List[ProblemaEntrada] = []
    if caso.get("tipo_caso") != "ensayo_geometrico":
        problemas.append(
            ProblemaEntrada("TIPO_CASO_INVALIDO", "error", "tipo_caso",
                            "debe ser 'ensayo_geometrico'")
        )
    if "carga_superficial_kN_m2" not in caso:
        problemas.append(
            ProblemaEntrada("SIN_CARGA", "error", "carga_superficial_kN_m2",
                            "el caso debe definir la carga superficial del ensayo")
        )
    if caso.get("resultado_no_utilizable_para_diseno") is not True:
        problemas.append(
            ProblemaEntrada("ENSAYO_NO_MARCADO", "error", "resultado_no_utilizable_para_diseno",
                            "un ensayo geomtrico no es utilizable para diseno")
        )

    archivo = caso.get("archivo_geometria")
    if not archivo:
        problemas.append(
            ProblemaEntrada("SIN_GEOMETRIA", "error", "archivo_geometria",
                            "el caso debe referenciar el archivo congelado")
        )

    if problemas:
        elevar_si_error(problemas)

    base_ruta = Path(archivo)
    if not base_ruta.is_absolute():
        # ruta relativa al directorio del caso; si no existe, relativa a la raiz del
        # repo (proyecto_edificio_ingenieria), que es parent.parent del caso.
        candidatos = [caso_ruta.parent / base_ruta,
                      caso_ruta.parent.parent / base_ruta,
                      caso_ruta.parent.parent.parent / base_ruta]
        for c in candidatos:
            if c.exists():
                base_ruta = c.resolve()
                break
        else:
            base_ruta = candidatos[0].resolve()

    modelo = leer_geometria(str(base_ruta))
    q = float(caso["carga_superficial_kN_m2"])

    # hipotesis por losa: deben cubrir TODAS las losas del nivel
    casos_ids = [h["id"] for h in caso.get("losas_hipotesis", [])]
    modelo_ids = [p.id for p in modelo.panels]
    faltantes = [i for i in modelo_ids if i not in casos_ids]
    extra = [i for i in casos_ids if i not in modelo_ids]

    hipotesis: Dict[str, HipotesisLosa] = {}
    for h in caso.get("losas_hipotesis", []):
        lid = h["id"]
        hipotesis[lid] = HipotesisLosa(
            id=lid,
            tipo_transferencia=h.get("tipo_transferencia", "por_definir"),
            origen=h.get("origen", "hipotesis_ensayo_NO_diseno"),
            notas=h.get("notas", ""),
        )
    for lid in faltantes:
        hipotesis[lid] = HipotesisLosa(
            id=lid, tipo_transferencia="por_definir",
            origen="hipotesis_ensayo_NO_diseno",
            notas="faltante en el caso -> por_definir (detiene la ejecucion)",
        )
    for lid in extra:
        problemas.append(
            ProblemaEntrada("HIPOTESIS_LOSA_INEXISTENTE", "error",
                            f"losas.{lid}",
                            "hipotesis referencia una losa que no existe en el nivel")
        )

    # aplicar hipotesis a una copia del modelo (no toca el dict base)
    for p in modelo.panels:
        tt = hipotesis[p.id].tipo_transferencia
        p.tipo_transferencia = tt

    if problemas:
        elevar_si_error(problemas)

    # exigir que ninguna losa quede por_definir -> se asigna y valida
    pendientes = [p.id for p in modelo.panels
                  if p.tipo_transferencia not in TIPOS_ADMISIBLES_ENSAYO]
    if pendientes:
        problemas.append(
            ProblemaEntrada(
                "LOSA_SIN_TRANSFERENCIA_ENSAYO", "error",
                "ensayo",
                "faltan decisiones de transferencia por losa (quedan por_definir): "
                + ", ".join(pendientes),
            )
        )
        elevar_si_error(problemas)

    return CasoEnsayo(
        tipo_caso=caso["tipo_caso"],
        carga_kN_m2=q,
        resultado_utilizable_para_diseno=False,
        archivo_geometria=str(base_ruta.resolve()),
        hash_geometria_al_cargar=_sha256(str(base_ruta.resolve())),
        modelo=modelo,
        hipotesis=hipotesis,
    )