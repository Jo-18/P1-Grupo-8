"""Carga la geometria estructual real de los candidatos y la lleva al sistema comun.

Cadena (documentada en `datos/candidatos/matrices_transformacion_unity.json`):
    DXF -> JSON local (procedencia; NO se aplica aqui) -> COMUN (se aplica aqui) -> Unity.

Los candidatos ya estan en metros (JSON local). Aqui se aplica SOLO local -> comun,
conservando IDs y procedencia. z (cota) se toma de las cotas de nivel documentadas.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

from . import config_edificios as CFG
from .hipotesis import COTAS_NIVEL_M, niveles_ordenados

_LAB = Path(__file__).resolve().parents[3]          # analisis_estructural/edificio_I
_CAND = _LAB / "datos" / "candidatos"


def _edificio_cfg() -> CFG.ConfigEdificio:
    return CFG.activa()


def _nivel_archivo() -> dict:
    return dict(_edificio_cfg().nivel_archivo)


def _trans_path() -> Path:
    ruta = _edificio_cfg().ruta_matrices_unity
    p = Path(ruta)
    return p if p.is_absolute() else (_LAB / p)


def _cargar_matrices() -> dict:
    return json.loads(_trans_path().read_text(encoding="utf-8"))


def _apply_m4(m: List[List[float]], x, y, z):
    """Aplica matriz homogenea 4x4 a (x,y,z,1); devuelve (ux,uy,uz)."""
    w = m[3][0] * x + m[3][1] * y + m[3][2] * z + m[3][3]
    ux = (m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3]) / w
    uy = (m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3]) / w
    uz = (m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3]) / w
    return ux, uy, uz


class NivelFE:
    """Geometria de un nivel ya en el sistema comun (u, v, cota)."""

    def __init__(self, codigo: str):
        self.codigo = codigo
        self.cota = COTAS_NIVEL_M[codigo]
        self.columnas: List[dict] = []   # {id, u, v, seccion, eje}
        self.vigas: List[dict] = []      # {id, seccion, pts:[(u,v)..], recibe_losa}
        self.muros: List[dict] = []      # {id, espesor, ua,va, ub,vb, recibe_losa}
        self.losas: List[dict] = []      # {id, espesor, poligono:[(u,v)..], aberturas, apoyos}
        self.cota_doc = COTAS_NIVEL_M.get(codigo)

    def load(self, transformes: dict):
        d = json.loads((_CAND / _nivel_archivo()[self.codigo]).read_text(
            encoding="utf-8"))
        M = transformes["local_json_to_common"][self.codigo]["matriz"]
        cota = self.cota

        cols = d.get("columnas") or d.get("columnas_referencia") or []
        for c in cols:
            x, y = c["posicion"][0], c["posicion"][1]
            u, v, _ = _apply_m4(M, x, y, cota)
            self.columnas.append({
                "id": c["id"], "u": u, "v": v,
                "seccion": c.get("seccion"), "eje": c.get("eje"),
            })

        for v in d.get("vigas", []):
            pts = []
            for p in v.get("pts") or (v.get("inicio"), v.get("fin")):
                if p is None:
                    continue
                px, py = p[0], p[1]
                u, vv, _ = _apply_m4(M, px, py, cota)
                pts.append((u, vv))
            if not pts:
                continue
            self.vigas.append({
                "id": v.get("id"), "seccion": v.get("seccion", {}).get("nombre", ""),
                "pts": pts, "recibe_losa": v.get("recibe_losa", True),
            })

        for m in d.get("muros", []):
            ej = m.get("eje", {})
            ia, ib = ej.get("inicio"), ej.get("fin")
            if not ia or not ib:
                continue
            ua, va, _ = _apply_m4(M, ia[0], ia[1], cota)
            ub, vb, _ = _apply_m4(M, ib[0], ib[1], cota)
            self.muros.append({
                "id": m["id"], "espesor": m.get("espesor"),
                "ua": ua, "va": va, "ub": ub, "vb": vb,
                "recibe_losa": m.get("recibe_losa", True),
            })

        for lo in d.get("losas", []):
            poly = lo.get("poligono_exterior", [])
            poly_c = [_apply_m4(M, x, y, cota)[:2] for (x, y) in poly]
            ab = []
            for a in lo.get("aberturas", []) or []:
                ap = a.get("poligono") if isinstance(a, dict) else None
                if ap:
                    ab.append([_apply_m4(M, x, y, cota)[:2] for (x, y) in ap])
            self.losas.append({
                "id": lo["id"], "espesor": lo.get("espesor"),
                "poligono": poly_c, "aberturas": ab,
                "apoyos": lo.get("apoyos_validos", []),
            })


def cargar_todos() -> Dict[str, NivelFE]:
    cfg = _edificio_cfg()
    if not cfg.geometria_disponible:
        raise RuntimeError(
            "El edificio %r no tiene geometria/hipotesis reales disponibles "
            "(PENDIENTE). No se ejecuta con datos inventados. Config: %s"
            % (cfg.id, cfg.nombre))
    matrices = _cargar_matrices()
    out = {}
    for codigo in niveles_ordenados():
        n = NivelFE(codigo)
        n.load(matrices)
        out[codigo] = n
    return out


def construir_superficies(losas: List[dict]):
    """Construye poligonos Shapely netos (exterior - aberturas) por losa."""
    from shapely.geometry import Polygon
    out = []
    for lo in losas:
        ext = Polygon(lo["poligono"])
        neto = ext
        for ab in lo["aberturas"]:
            neto = neto.difference(Polygon(ab))
        out.append({"id": lo["id"], "espesor": lo["espesor"], "neto": neto,
                    "bruto": ext})
    return out
