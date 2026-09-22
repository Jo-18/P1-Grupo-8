"""Preparacion de los casos sismicos EX/EY (Entrega 3).

No se inventa ningun parametro sismico: todos estan en `config/sismo.json` en null.
Cualquier ejecucion que intente usar un parametro null ABORTA con un mensaje claro
listando que falta. Quedan preparados los verificadores de:

  - carga lateral total       (suma de fuerzas por nivel)
  - corte basal               (suma de fuerzas laterales vs corte en base)
  - sentido de la deformada   (signo del desplazamiento vs sentido del caso)
  - torsion de piso           (si corresponde a partir de pares de piso)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONFIG = REPO / "entrega_03_cargas_sismo_capacidad" / "config" / "sismo.json"

PARAMETROS_REQUERIDOS = [
    "zona_sismica", "suelo_clasificacion", "importancia", "amortiguamiento",
    "factor_R", "peso_sismico_W_kN", "distribucion_vertical", "torsion_accidental",
    "espectro_o_coeficiente_sismico",
]


def leer_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def requeridos_faltantes(cfg: dict | None = None) -> list[str]:
    cfg = cfg or leer_config()
    return [k for k in PARAMETROS_REQUERIDOS if cfg.get(k) is None]


def check_requisitos(cfg: dict | None = None) -> dict:
    """Aborta si faltan parametros; si estan, devuelve la config lista para ejecutar."""
    cfg = cfg or leer_config()
    faltantes = requeridos_faltantes(cfg)
    if faltantes:
        raise SystemExit(
            "ABORTE EX/EY: faltan parametros sismicos sin documentar (config/sismo.json): "
            + ", ".join(faltantes) + ".\nNo se ejecuta ningun caso sismico con null.")
    return cfg


def verificar_carga_lateral_total(fuerzas_por_nivel, tolerancia=1e-6) -> dict:
    """Suma de fuerzas laterales por nivel (kN) y su total."""
    total = sum(fuerzas_por_nivel)
    return {"total_lateral_kN": total, "sum_ok": abs(total) > 0}


def verificar_corte_basal(fuerzas_por_nivel, corte_basal, tolerancia_rel=0.005) -> dict:
    """Corte basal (kN) == suma de fuerzas laterales por nivel."""
    total = sum(fuerzas_por_nivel)
    drel = (abs(total - corte_basal) / abs(corte_basal)) if corte_basal else float("inf")
    return {
        "suma_lateral_kN": total, "corte_basal_kN": corte_basal,
        "diferencia_rel": drel, "estado": "OK" if drel <= tolerancia_rel else "ERROR"}


def verificar_sentido_deformada(fuerzas_por_nivel, desplazamientos_signo, 
                                tolerancia=1e-3) -> dict:
    """El producto escalar fuerza*desplazamiento debe ser positivo (deformada en el
    sentido del caso). `desplazamientos_signo`: lista con el signo del desplazamiento
    dominante por nivel (1.0 o -1.0)."""
    parejas = [f * d for f, d in zip(fuerzas_por_nivel, desplazamientos_signo)]
    ok = all(pp > -tolerancia for pp in parejas)
    return {"productos_fuera_desplazamiento": parejas,
            "estado": "OK" if ok else "ERROR(SENTIDO_INVERSO)"}


def verificar_torsion_piso(excentricidades_por_nivel, limite, tolerancia_rel=0.05) -> dict:
    """Torsion de piso: excentricidad calculada vs limite admisible (si corresponde).
    Si no hay datos de torsion, devuelve N/D (no es error)."""
    if not excentricidades_por_nivel:
        return {"estado": "N/D_SIN_DATOS_DE_TORSION"}
    malos = [e for e in excentricidades_por_nivel
             if e > limite * (1 + tolerancia_rel)]
    return {"excentricidades_por_nivel": excentricidades_por_nivel,
            "limite": limite, "niveles_fuera": len(malos),
            "estado": "OK" if not malos else "ERROR(TORSION_FUERA_LIMITE)"}


def main(argv=None) -> int:
    _ = argv if argv is not None else sys.argv[1:]
    cfg = leer_config()
    try:
        check_requisitos(cfg)
    except SystemExit as e:
        print(e)
        return 1
    print("EX/EY: parametros completos (aun no ejecutado). "
          "Verificadores listos: corte basal, sentido deformada, torsion de piso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())