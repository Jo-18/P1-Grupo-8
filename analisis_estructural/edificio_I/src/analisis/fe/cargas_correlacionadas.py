"""Cargas superficiales por losa a partir de la correlacion de cargas validada.

Lee `datos/casos_analisis/correlacion_cargas_validada_5niveles.json` (regenerado) y
produce, por nivel y por losa, una carga gravitacional media (PM_ADIC + SC, en kgf/m2
y kN/m2) ponderada por el area de cada categoria correlacionada.

El area sin clasificar y por confirmar NO recibe carga superficial correlacionada
(se deja en 0; hipotesis documentada: solo se cargan las zonas correlacionadas).
"""

from __future__ import annotations

import json
from pathlib import Path

from .hipotesis import GRAV_KGF_TO_KN
from . import config_edificios as CFG

_LAB = Path(__file__).resolve().parents[3]


def _corr_path() -> Path:
    ruta = CFG.activa().ruta_correlacion_cargas
    if not ruta:
        raise RuntimeError(
            "El edificio activo no define ruta de correlacion de cargas (PENDIENTE).")
    p = Path(ruta)
    return p if p.is_absolute() else (_LAB / p)


def _cat_to_pm_sc(key: str):
    # "260/300" -> (260, 300) kgf/m2
    try:
        a, b = key.split("/")
        return float(a), float(b)
    except Exception:
        return 0.0, 0.0


def cargas_por_losa_por_nivel() -> dict:
    """{nivel: {losa_id: {"pm_kgf_m2":..,"sc_kgf_m2":..,"neta_m2":..,"q_kn_m2":..}}}"""
    d = json.loads(_corr_path().read_text(encoding="utf-8"))
    nivel_out = {}
    for cod, pn in d["por_nivel"].items():
        losas_out = {}
        for lo in pn.get("losas", []):
            neta = lo.get("area_neta_m2") or 0.0
            cat = lo.get("area_por_categoria_m2") or {}
            tot_pm = 0.0
            tot_sc = 0.0
            tot_area = 0.0
            for key, area in cat.items():
                pm, sc = _cat_to_pm_sc(key)
                tot_pm += pm * area
                tot_sc += sc * area
                tot_area += area
            pm_avg = tot_pm / neta if neta > 0 else 0.0
            sc_avg = tot_sc / neta if neta > 0 else 0.0
            q_kn = (pm_avg + sc_avg) * GRAV_KGF_TO_KN
            losas_out[lo["id"]] = {
                "pm_kgf_m2": pm_avg,
                "sc_kgf_m2": sc_avg,
                "pm_kn_m2": pm_avg * GRAV_KGF_TO_KN,
                "sc_kn_m2": sc_avg * GRAV_KGF_TO_KN,
                "neta_m2": neta,
                "q_superficial_kn_m2": q_kn,
            }
        nivel_out[cod] = losas_out
    return nivel_out
