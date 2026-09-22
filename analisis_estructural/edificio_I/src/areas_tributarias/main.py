"""
Pipeline de areas tributarias:
  leer geometria canonica -> calcular regiones -> cargas lineales ->
  validar conservacion -> escribir resultados (tablas) y figuras.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cargas import transformar
from .io import (
    leer_geometria,
    resultados_a_dict,
    escribir_tabla_bordes,
    escribir_reporte_validacion,
)
from . import io
from . import validacion as val
from . import viz
from .tributacion import calcular_paneles


def ejecutar_caso(ruta_caso: str, directorio_resultados: str,
                  n_samples: int = 200) -> int:
    ruta_caso = Path(ruta_caso)
    modelo = leer_geometria(str(ruta_caso))

    # carga superficial por defecto de cada panel
    por_panel = {}
    cargas = {}
    validaciones = []
    for panel in modelo.panels:
        q = 0.0
        if panel.carga_superficial:
            q = modelo.cargas[panel.carga_superficial].valor
        pr = calcular_paneles(panel, q, tamano_celda=modelo.config.tamano_celda_inicial,
                              n_samples=n_samples)
        por_panel[panel.id] = pr
        cargas[panel.id] = transformar(pr, q)

        validaciones.append(val.validar_area(
            pr, modelo.config.tolerancia_relativa_area))
        validaciones.append(val.validar_carga(
            pr, q, modelo.config.tolerancia_relativa_carga))
        validaciones.append(val.validar_span_por_borde(pr))

    d = Path(directorio_resultados)
    d.mkdir(parents=True, exist_ok=True)

    res = resultados_a_dict(modelo, por_panel, cargas, validaciones)
    io.escribir_resultados_json(str(d / "resultados.json"), res)

    io.escribir_tabla_bordes(str(d / "tablas" / "areas_tributarias.csv"),
                             modelo, por_panel)
    todos_ok = io.escribir_reporte_validacion(
        str(d / "validaciones" / "reporte_validacion.txt"), validaciones)

    viz.graficar_planta(modelo, por_panel, str(d / "figuras" / "planta.png"))
    viz.graficar_perfiles(modelo, por_panel, str(d / "figuras" / "perfiles.png"))

    # consola
    print(f"Proyecto: {modelo.proyecto.get('nombre','')} | "
          f"Nivel: {modelo.nivel.get('id','')}")
    for panel in modelo.panels:
        q = modelo.cargas[panel.carga_superficial].valor if panel.carga_superficial else 0.0
        print(f"\nPanel {panel.id}: area neta = {panel.area_neta:.4f} m2 | "
              f"q = {q} kN/m2 | tipo = {panel.tipo_transferencia}")
        for c in cargas[panel.id]:
            print(f"  {c.elemento_soporte:10s} L={c.longitud:.3f}m "
                  f"A={por_panel[panel.id].regiones[_idx(por_panel,panel,c)].area:.4f}m2 "
                  f"perfil={c.tipo_perfil:11s} w_max={c.w_max:.4f} "
                  f"integral={c.integral:.4f} kN")
    print("\n" + ("[OK] Validaciones: PASA" if todos_ok else "[FAIL] Validaciones: FALLA"))
    print(f"Resultados en: {d.resolve()}")
    return 0 if todos_ok else 1


def _idx(por_panel, panel, carga):
    for i, r in enumerate(por_panel[panel.id].regiones):
        if r.borde.id == carga.borde_id:
            return i
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Calcula areas tributarias y cargas lineales de un nivel.")
    parser.add_argument("--caso", required=True,
                        help="Ruta al JSON canonico de geometria/casos_prueba")
    parser.add_argument("--resultados", default="resultados",
                        help="Directorio donde guardar resultados")
    parser.add_argument("--n_samples", type=int, default=200,
                        help="Puntos por borde para el perfil de ancho")
    args = parser.parse_args(argv)
    return ejecutar_caso(args.caso, args.resultados, args.n_samples)


if __name__ == "__main__":
    sys.exit(main())
