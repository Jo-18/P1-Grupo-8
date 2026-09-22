"""
Entrada/salida del modulo de areas tributarias:
  - lectura del JSON canonico de entrada;
  - escritura de resultados numericos (tablas JSON/CSV) en resultados/tablas;
  - escritura del reporte de validacion en resultados/validaciones.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

from .cargas import CargaLineal
from .modelo import ModeloGeometria
from .tributacion import ResultadoPanel
from .validacion import CheckResultado


def leer_geometria(ruta: str) -> ModeloGeometria:
    """Lee un archivo JSON canonico y devuelve el ModeloGeometria."""
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ModeloGeometria.from_dict(data)


def resultados_a_dict(
    modelo: ModeloGeometria,
    por_panel: Dict[str, ResultadoPanel],
    cargas: Dict[str, List[CargaLineal]],
    validaciones: List[CheckResultado],
) -> dict:
    """Arma un dict serializable con todos los resultados por panel."""
    panels_out = []
    for panel in modelo.panels:
        pr = por_panel[panel.id]
        lc = cargas[panel.id]
        panels_out.append(
            {
                "id": panel.id,
                "tipo_transferencia": panel.tipo_transferencia,
                "espesor": panel.espesor,
                "area_bruta_m2": panel.area_bruta,
                "area_aberturas_m2": panel.area_aberturas,
                "area_neta_m2": panel.area_neta,
                "area_asignada_m2": pr.area_total,
                "bordes": [_borde_dict(r) for r in pr.regiones],
                "cargas_lineales": [_carga_dict(c) for c in lc],
            }
        )
    return {
        "proyecto": modelo.proyecto,
        "nivel": modelo.nivel,
        "version_formato": modelo.version_formato,
        "paneles": panels_out,
        "validaciones": [
            {
                "nombre": v.nombre,
                "ok": v.ok,
                "valor_obtenido": v.valor_obtenido,
                "valor_esperado": v.valor_esperado,
                "error_abs": v.error_abs,
                "error_rel": v.error_rel,
                "mensaje": v.mensaje,
            }
            for v in validaciones
        ],
    }


def _borde_dict(region) -> dict:
    return {
        "borde_id": region.borde.id,
        "elemento_soporte": region.borde.elemento_soporte,
        "tipo": region.borde.tipo,
        "longitud_m": region.borde.longitud,
        "area_tributaria_m2": region.area,
        "ancho_max_m": region.ancho_max,
        "ancho_promedio_m": region.ancho_promedio,
    }


def _carga_dict(c: CargaLineal) -> dict:
    return {
        "borde_id": c.borde_id,
        "elemento_soporte": c.elemento_soporte,
        "tipo_perfil": c.tipo_perfil,
        "longitud_m": c.longitud,
        "w_max_kNm": c.w_max,
        "w_min_kNm": c.w_min,
        "integral_kN": c.integral,
        "zona_constante_m": c.zona_constante,
    }


def escribir_resultados_json(
    ruta: str, resultados: dict, indent: int = 2
) -> None:
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=indent)


def escribir_tabla_bordes(ruta_csv: str, modelo: ModeloGeometria,
                          por_panel: Dict[str, ResultadoPanel]) -> None:
    _crear_dir(ruta_csv)
    filas = []
    for panel in modelo.panels:
        pr = por_panel[panel.id]
        for r in pr.regiones:
            filas.append(
                {
                    "panel": panel.id,
                    "borde": r.borde.id,
                    "soporte": r.borde.elemento_soporte,
                    "tipo": r.borde.tipo,
                    "longitud_m": round(r.borde.longitud, 6),
                    "area_tributaria_m2": round(r.area, 6),
                    "ancho_max_m": round(r.ancho_max, 6),
                    "ancho_promedio_m": round(r.ancho_promedio, 6),
                }
            )
    if filas:
        claves = list(filas[0].keys())
        with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=claves)
            w.writeheader()
            w.writerows(filas)


def escribir_reporte_validacion(ruta_txt: str, validaciones: List[CheckResultado]) -> None:
    _crear_dir(ruta_txt)
    lineas = ["REPORTE DE VALIDACION - AREAS TRIBUTARIAS", "=" * 50, ""]
    todos_ok = True
    for v in validaciones:
        estado = "[OK]" if v.ok else "[FAIL]"
        if not v.ok:
            todos_ok = False
        lineas.append(
            f"{estado} {v.nombre}: {v.mensaje}"
        )
    lineas.append("")
    lineas.append("RESULTADO GLOBAL: " + ("PASA" if todos_ok else "FALLA"))
    _crear_dir(ruta_txt)
    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    return todos_ok


def escribir_resultados_por_panel_json(ruta: str, resultados: dict) -> None:
    escribir_resultados_json(ruta, resultados)


def _crear_dir(ruta: str) -> None:
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
