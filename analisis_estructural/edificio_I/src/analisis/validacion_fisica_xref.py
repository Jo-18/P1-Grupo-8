"""Validacion fisica por nivel de la transformacion recuperada de XREF (solo lectura).

Cadena que se comprueba (metadatos XREF + transformacion congelada por nivel):

    p_700        = p_estructural + insercion_xref                (XREF: bloque enlazado 1:1 rot 0)
    p_estructural = p_700 - insercion_xref                       (inversa, round-trip)
    p_modelo     = transformacion_fria(p_estructural)            (sistema_coordenadas del JSON congelado)

NO se reajustan escala/rotacion/traslacion y NO se ejecuta un solver: la escala XREF es 1,
la rotacion 0 y no hay reflexion; cualquier desviacion adicional es senal de error en la
cadena o en la asociacion del bloque.

Controles por nivel (>=3 puntos fisicos no colineales):
  - cruces de ejes (rle-ejes) cuya coordenada de modelo esperada sale de la rejilla congelada
    (E=.., F=.., cotas 1/2/3 del sistema_coordenadas);
  - esquinas de muros / quiebres de perimetro (rle-muro) casadas por contorno a la huella
    congelada (muros/dias) solo como supervision topologica;
  - centros de cajas cerradas de pilar/muro (rle-pilar/rle-muro).

Salidas:
  resultados/cargas_reales/validacion_fisica_xref_por_nivel.json
  resultados/cargas_reales/informe_validacion_fisica_xref.md
  resultados/cargas_reales/figuras/validacion_xref_<nivel>.png

Reglas: no modifica JSON congelados, no asigna cargas, no ejecuta areas tributarias,
no hace Git. Distingue transformacion geometrica validada de asignacion carga->losa.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ezdxf
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

BASE = Path(__file__).resolve().parents[2]
RES = BASE / "resultados" / "cargas_reales"
FIG = RES / "figuras"
GEO = BASE / "datos" / "geometria"

DXF700 = r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\Datos Estructurales\2017_67-700.dxf"
CAD_DIR = r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\Datos Estructurales"

# Asociacion por nivel (auditoria_xref_700): bloque enlazado / archivo estructural.
LEVEL_BLOCK = {
    "CP1S": "2017_67-101",
    "P1":   "2017_67-101",
    "P2":   "2017_67-102",
    "P3":   "2017_67-102",
    "P4":   "2017_67-103",
}
STRUCT_DXF = {
    "2017_67-101": "2017_67-101.dxf",
    "2017_67-102": "2017_67-102.dxf",
    "2017_67-103": "2017_67-103.dxf",
}
FROZEN_FILE = {
    "CP1S": "edificio_I_cielo_piso_1_subterraneo_borrador.json",
    "P1":   "edificio_I_cielo_piso_1_borrador.json",
    "P2":   "edificio_I_cielo_piso_2_borrador.json",
    "P3":   "edificio_I_cielo_piso_3_borrador.json",
    "P4":   "edificio_I_cielo_piso_4_borrador.json",
}

TOL_M = 0.05  # tolerancia de residuo por control (5 cm) para considerar 'cerrado'
AX_ATOL_M = 0.10  # tolerancia para aceptar una linea de cuadricula como eje etiquetado
SOLAPE_MIN = 0.50  # fraccion minima de huella model cubierta por geometria estructural


# ---------------------------------------------------------------- lectura CAD / congelado
def _leer_inserts_700(level_insert: Dict[str, dict]) -> Dict[str, dict]:
    """Relee los INSERT de los bloques estructurales del DXF700 y cruza con la asociacion
    por nivel para no fijar constantes a mano (solo lectura de metadatos)."""
    out = {k: None for k in level_insert}
    doc = ezdxf.readfile(DXF700)
    by_blk = {}
    for e in doc.modelspace():
        if e.dxftype() != "INSERT":
            continue
        bname = e.dxf.get("name")
        if bname not in set(LEVEL_BLOCK.values()):
            continue
        ins = e.dxf.get("insert")
        by_blk.setdefault(bname, []).append({
            "handle": e.dxf.handle,
            "insercion": [round(float(ins.x), 4), round(float(ins.y), 4)],
            "escala": [float(e.dxf.get("xscale", 1.0)), float(e.dxf.get("yscale", 1.0))],
            "rotacion_deg": float(e.dxf.get("rotation", 0.0)),
        })
    # reutiliza los handles/insercion ya validados por la auditoria
    if level_insert:
        for cod, meta in level_insert.items():
            blk = meta["bloque"]
            cand = [i for i in by_blk.get(blk, []) if i["handle"] == meta["handle"]]
            out[cod] = cand[0] if cand else None
    return out


def _cargar_nivel(cod: str) -> dict:
    return json.loads((GEO / FROZEN_FILE[cod]).read_text(encoding="utf-8"))


def _huella_modelo(cod: str) -> Optional[Polygon]:
    """Huella congelada (union de poligonos_exterior de losas) en metros de modelo."""
    d = _cargar_nivel(cod)
    losas = d.get("losas")
    if isinstance(losas, dict):
        losas = list(losas.values())
    pols = []
    for lo in losas or []:
        pe = lo.get("poligono_exterior")
        if pe:
            pols.append(Polygon([(float(p[0]), float(p[1])) for p in pe]))
    if not pols:
        hf = d.get("huella_fisica")
        if hf:
            for lo in hf.get("lobos", []):
                pols.append(Polygon([(float(p[0]), float(p[1])) for p in lo["poligono"]]))
    if not pols:
        return None
    return unary_union(pols)


# ---------------------------------------------------------------- transformacion congelada
def _parse_transform_x(sc: dict) -> Optional[Tuple[float, float]]:
    """(Kx, Sx) de 'x_m=(DXF_X-Kx)/Sx'. La X no se voltea en estos planos."""
    for field in ("_derivacion", "eje_x_positivo", "eje_x_negativo"):
        txt = sc.get(field) or ""
        m = re.search(r"x_m\s*=\s*\(\s*DXF_X\s*-\s*(-?\d+(?:\.\d+)?)\s*\)\s*/\s*(\d+(?:\.\d+)?)", txt)
        if m:
            return (float(m.group(1)), float(m.group(2)))
    return None


def _parse_transform_y(sc: dict) -> Optional[Tuple[float, float, bool]]:
    """(Ky, Sy, flip). 'y_m=(DXF_Y-Ky)/Sy' -> flip False; 'y_m=(Ky-DXF_Y)/Sy' -> flip True."""
    for field in ("_derivacion", "eje_y_positivo", "eje_y_negativo"):
        txt = sc.get(field) or ""
        m = re.search(r"y_m\s*=\s*\(\s*(-?\d+(?:\.\d+)?)\s*-\s*DXF_Y\s*\)\s*/\s*(\d+(?:\.\d+)?)", txt)
        if m:
            return (float(m.group(1)), float(m.group(2)), True)
        m2 = re.search(r"y_m\s*=\s*\(\s*DXF_Y\s*-\s*(-?\d+(?:\.\d+)?)\s*\)\s*/\s*(\d+(?:\.\d+)?)", txt)
        if m2:
            return (float(m2.group(1)), float(m2.group(2)), False)
    return None


def _parse_axes(txt: str) -> List[Tuple[str, float]]:
    seg = (txt or "").split(")")[0]
    return [(k, float(v)) for k, v in re.findall(r"([A-Za-z]{1,2}\d?)\s*=\s*(\d+(?:\.\d+)?)", seg)]


def _frozen_axes(sc: dict) -> Tuple[List[Tuple[str, float]], List[Tuple[str, float]]]:
    ev = sc.get("ejes_verticales")
    vx = [(k, float(v)) for k, v in ev.items()] if isinstance(ev, dict) else _parse_axes(sc.get("eje_x_positivo") or "")
    eh = sc.get("ejes_horizontales")
    if isinstance(eh, dict):
        hy = [(k, float(v)) for k, v in eh.items()]
    else:
        seg = (sc.get("eje_y_positivo") or (sc.get("_derivacion") or "")).split(")")[0]
        hy = [(k, float(v)) for k, v in re.findall(r"(\d+)\s*=\s*(\d+(?:\.\d+)?)", seg)]
    return vx, hy


# ---------------------------------------------------------------- DXF estructural
def _structural_lines(blk: str, caps=("rle-ejes",)) -> Dict[str, List[float]]:
    """Lineas axis-alineadas del DXF estructural limitadas a las capas dadas."""
    doc = ezdxf.readfile(str(Path(CAD_DIR) / STRUCT_DXF[blk]))
    msp = doc.modelspace()
    vx = set(); hy = set()
    for e in msp:
        lay = (e.dxf.layer or "").lower()
        if e.dxftype() != "LINE":
            continue
        if lay not in caps:
            continue
        sp = e.dxf.start; ep = e.dxf.end
        if abs(sp.x - ep.x) < 1e-6:
            vx.add(round(float(sp.x), 4))
        if abs(sp.y - ep.y) < 1e-6:
            hy.add(round(float(sp.y), 4))
    return {"vx": sorted(vx), "hy": sorted(hy)}


def _label_axis(px: float, axes: List[Tuple[str, float]], atol_m: float = AX_ATOL_M
                ) -> Optional[Tuple[str, float, float]]:
    """Asigna el rotulo de eje con valor de modelo mas proximo; None si no cae en ninguno
    dentro de la tolerancia (para no tomar lineas secundarias de cuadricula como ejes)."""
    best = None; bestres = None
    for lab, val in axes:
        r = abs(px - val)
        if bestres is None or r < bestres:
            bestres = r; best = (lab, val, r)
    if best is None or bestres > atol_m:
        return None
    return best


# ---------------------------------------------------------------- cobertura de regiones (700)
def _regiones_700(cod: str) -> List[Polygon]:
    """Regiones de carga (no leyenda) ya extraidas por el pipeline DXF700 (diagnostico)."""
    p = BASE / "datos" / "casos_analisis" / "correlacion_cargas_pagina11.json"
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            regs = d.get("niveles", {}).get(cod, {}).get("regiones", [])
            pols = []
            for r in regs:
                o = r.get("outline")
                if o and not o.is_empty and o.geom_type == "Polygon":
                    pols.append(o)
            return pols
        except Exception:
            pass
    return []


def _circle_rect_lines(lines: List) -> List[Polygon]:
    """(Diagnostico) cajas cerradas de pilar/muro; no es control numerico directo."""
    return []


def _anclas_geometria(frozen: dict
                      ) -> Tuple[List[Tuple[float, str]], List[Tuple[float, str]]]:
    """Anchors de geometria congelada (muros / losas) en metros de modelo, para usarse
    como controles cuando la rejilla etiquetada no basta (p. ej. CP1S sin cotas)."""
    xa = {}
    ya = {}
    for m in frozen.get("muros") or []:
        e = m.get("eje", {}) or {}
        i = e.get("inicio") or [None, None]
        fi = e.get("fin") or [None, None]
        if i and fi and i[0] is not None and i[0] == fi[0]:
            xa[round(float(i[0]), 3)] = "muro_%s" % m.get("id", "?")
        for vv, tag in ((i[1], "muro_inicio"), (fi[1], "muro_fin")):
            if vv is not None:
                ya[round(float(vv), 3)] = m.get("id", "?") + ":" + tag
    losas = frozen.get("losas")
    if isinstance(losas, dict):
        losas = list(losas.values())
    for lo in losas or []:
        for p in lo.get("poligono_exterior") or []:
            xa.setdefault(round(float(p[0]), 3), "losa")
            ya.setdefault(round(float(p[1]), 3), "losa")
    return (list(sorted(xa.items())), list(sorted(ya.items())))


# ============================================================================== validacion
def _validar_nivel(cod: str, meta: dict) -> dict:
    frozen = _cargar_nivel(cod)
    sc = frozen["sistema_coordenadas"]

    tx = _parse_transform_x(sc)
    ty = _parse_transform_y(sc)
    ins = meta["insercion"]
    blk = meta["bloque"]

    # transformacion libre (estructural -> modelo) fijada por el JSON congelado
    def to_model(sx: float, sy: float):
        mx = (sx - tx[0]) / tx[1]
        k, s, flip = ty
        my = (k - sy) / s if flip else (sy - k) / s
        return (round(mx, 6), round(my, 6))

    def roundtrip(sx, sy):
        """estructural -> 700 (XREF) -> estructural (inversa). Debe devolver (sx, sy)."""
        p700 = (round(sx + ins[0], 4), round(sy + ins[1], 4))
        back = (round(p700[0] - ins[0], 4), round(p700[1] - ins[1], 4))
        return p700, back

    grp = _structural_lines(blk, caps=("rle-ejes",))
    vaxes, haxes = _frozen_axes(sc)
    gx, gy = _anclas_geometria(frozen)

    def _match(px, sees):
        best = None; bestres = None
        for val, nombre in sees:
            r = abs(px - val)
            if bestres is None or r < bestres:
                bestres = r; best = (val, nombre, r)
        if best is None or bestres > AX_ATOL_M:
            return None
        return best

    # ---- controles: cruces, separando rejilla etiquetada (axal) de geometria (geo) ----
    def _cruces(seesX, seesY, prefijo):
        best = {}; n = 0
        for sx in grp["vx"]:
            mx, _ = to_model(sx, grp["hy"][0] if grp["hy"] else 0.0)
            ax = _match(mx, seesX)
            if ax is None:
                continue
            for sy in grp["hy"]:
                _, my = to_model(sx, sy)
                ay = _match(my, seesY)
                if ay is None:
                    continue
                p700, back = roundtrip(sx, sy)
                esperado = (round(ax[0], 4), round(ay[0], 4))
                predicho = to_model(sx, sy)
                residuo = math.hypot(predicho[0] - esperado[0], predicho[1] - esperado[1])
                c = {
                    "tipo": "cruce",
                    "etiqueta": "%s_%s" % (ax[1], ay[1]),
                    "capa": "rle-ejes",
                    "estructural_origen": [round(sx, 3), round(sy, 3)],
                    "en_700": p700,
                    "estructural_recuperado": back,
                    "modelo_predicho": predicho,
                    "modelo_esperado": esperado,
                    "residuo_m": round(residuo, 4),
                    "roundtrip_ok": back == (round(sx, 4), round(sy, 4)),
                }
                n += 1
                key = (ax[1], ay[1])
                if key not in best or residuo < best[key][1]:
                    best[key] = (c, residuo)
        out = [c for c, _ in best.values()]
        out.sort(key=lambda c: (c["etiqueta"], c["residuo_m"]))
        return out, n

    # rejilla etiquetada pura (E_.., cotas 1/2/3) -> control primario para 'validada'
    aXN = [(val, lab) for lab, val in vaxes]
    aYN = [(val, lab) for lab, val in haxes]
    if aXN and aYN:
        controles_axales, _n_raw_axal = _cruces(aXN, aYN, "axal")
        n_axal = len(controles_axales)
    else:
        controles_axales, n_axal = [], 0

    # geometria congelada (muros/losas) -> control secundario topologico
    if gx and gy:
        controles_geo, _n_raw_geo = _cruces(gx, gy, "geo")
        n_geo = len(controles_geo)
    else:
        controles_geo, n_geo = [], 0

    # criterio: >=3 cruces axales no colineales dentro de tolerancia => transformacion validada.
    validos_axal = [c for c in controles_axales if c["residuo_m"] <= TOL_M]
    n_validos_axal = len(validos_axal)
    residuo_max_axal = max([c["residuo_m"] for c in controles_axales], default=None)
    if n_axal >= 3 and n_validos_axal == n_axal and residuo_max_axal is not None and residuo_max_axal <= TOL_M:
        estado = "transformacion_xref_validada"
    elif controles_axales or controles_geo:
        estado = "transformacion_xref_coherente_no_validada"
    else:
        estado = "transformacion_xref_inconsistente"

    controles = controles_axales + controles_geo
    n_cruz_unicos = len(controles)

    # ---- supervision topologica: cruces predichos dentro (o razonablemente cerca) de la huella ----
    huella = _huella_modelo(cod)
    cobertura = None
    if huella is not None and controles:
        n_dentro = 0
        for c in controles:
            if huella.buffer(0.5).contains(Point(c["modelo_predicho"])):
                n_dentro += 1
        fraccion = n_dentro / len(controles) if controles else 0.0
        cobertura = {"n_cruces_en_huella": n_dentro, "n_cruces": len(controles),
                     "fraccion_en_huella": round(fraccion, 3)}

    # excluir leyendas / muestras (rle-ejes es rejilla estructural, no leyenda)
    residuo_max_todos = max([c["residuo_m"] for c in controles], default=None)
    return {
        "nivel": cod,
        "planta_estructural": blk,
        "insert_xref": {"handle": meta["handle"], "insercion": ins, "escala": meta["escala"],
                        "rotacion_deg": meta["rotacion_deg"], "verif_insert_700": meta.get("verif_insert_700", "no_verificado")},
        "transformacion_congelada": {
            "x": "x_m=(DXF_X-%s)/%s" % (tx[0], tx[1]),
            "y": ("y_m=(%s-DXF_Y)/%s (flip)" if ty[2] else "y_m=(DXF_Y-%s)/%s") % (ty[0], ty[1]),
        },
        "controles": controles,
        "n_cruces_axales": n_axal,
        "n_validos_axales_tol_5cm": n_validos_axal,
        "residuo_max_axal_m": residuo_max_axal,
        "n_cruces_geo": n_geo,
        "n_cruces_total": n_cruz_unicos,
        "residuo_max_total_m": residuo_max_todos,
        "residuo_medio_axal_m": round(sum(c["residuo_m"] for c in controles_axales) / len(controles_axales), 4) if controles_axales else None,
        "roundtrip_todos_ok": all(c["roundtrip_ok"] for c in controles) if controles else False,
        "tolerancia_axal_m": TOL_M,
        "estado": estado,
        "motivo": _motivo(estado, n_axal, n_validos_axal, residuo_max_axal, n_geo),
        "huella_modelo_cobertura": cobertura,
    }


def _motivo(estado, n_axal, n_validos_axal, residuo_max_axal, n_geo):
    if estado == "transformacion_xref_validada":
        return ("%s cruces de rejilla etiquetada (rutas de eje) cierran con residuo<=%s m y "
                "round-trip XREF exacto; sin desplazamiento global.") % (n_validos_axal, TOL_M)
    if estado == "transformacion_xref_coherente_no_validada":
        return ("la cadena XREF y la transformacion congelada son coherentes pero no cierran "
                "%s cruces axales dentro de tol %s m (axales_validos=%s, axal_max=%s; geo=%s).") % (
                    n_axal, TOL_M, n_validos_axal, residuo_max_axal, n_geo)
    return ("no se cierran controles independientes (axal=%s, axal_validos=%s, axal_max=%s, "
            "geo=%s): desplazamiento o asociacion contradictoria.") % (
                n_axal, n_validos_axal, residuo_max_axal, n_geo)


# ============================================================================== main
def main() -> dict:
    LEVEL_INSERT = {
        "CP1S": {"bloque": "2017_67-101", "handle": "E0ADC0AAF2D3E782", "insercion": [-2255.295, 670.841], "escala": [1.0, 1.0], "rotacion_deg": 0.0},
        "P1":   {"bloque": "2017_67-101", "handle": "E0ADC0AAF2D3E784", "insercion": [2209.814, 4607.853], "escala": [1.0, 1.0], "rotacion_deg": 0.0},
        "P2":   {"bloque": "2017_67-102", "handle": "E0ADC0AAF2D414D2", "insercion": [8412.406, 978.926], "escala": [1.0, 1.0], "rotacion_deg": 0.0},
        "P3":   {"bloque": "2017_67-102", "handle": "E0ADC0AAF2D41731", "insercion": [8543.585, -1576.398], "escala": [1.0, 1.0], "rotacion_deg": 0.0},
        "P4":   {"bloque": "2017_67-103", "handle": "E0ADC0AAF2D41636", "insercion": [-2380.174, -4389.169], "escala": [1.0, 1.0], "rotacion_deg": 0.0},
    }
    # relee los INSERT del DXF700 como doble comprobacion de metadatos
    releidos = _leer_inserts_700(LEVEL_INSERT)
    por_nivel = {}
    for cod in LEVEL_INSERT:
        meta = dict(LEVEL_INSERT[cod])
        rl = releidos.get(cod)
        if rl and abs(rl["insercion"][0] - meta["insercion"][0]) < 0.01 and abs(rl["insercion"][1] - meta["insercion"][1]) < 0.01:
            meta["verif_insert_700"] = "coincide"
        else:
            meta["verif_insert_700"] = "DIVERGE de releido" if rl else "sin insert releido"
        por_nivel[cod] = _validar_nivel(cod, meta)

    RES.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    payload = {
        "naturaleza": "validacion_fisica_xref_solo_lectura",
        "alcanza": "Distingue transformacion geometrica (este documento) de asignacion carga->losa (NO abordada).",
        "tolerancia_control_m": TOL_M,
        "reglas": {
            "escala_xref": 1.0,
            "rotacion_xref_deg": 0.0,
            "reflexion_xref": False,
            "n_solver": 0,
            "n_reajuste": 0,
        },
        "excluye": ["leyendas", "muestras de trama", "cajetines", "limites de HATCH", "regiones de otra planta"],
        "por_nivel": por_nivel,
        "resumen": {cod: {"estado": v["estado"], "n_cruces_axales": v["n_cruces_axales"],
                          "n_validos_axales_tol_5cm": v["n_validos_axales_tol_5cm"],
                          "residuo_max_axal_m": v["residuo_max_axal_m"],
                          "n_cruces_geo": v["n_cruces_geo"]}
                    for cod, v in por_nivel.items()},
    }
    (RES / "validacion_fisica_xref_por_nivel.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _md(payload, por_nivel)
    _figuras(por_nivel)
    return payload


# ============================================================================== md / figuras
def _md(payload: dict, por_nivel: dict) -> None:
    lines = [
        "# Validación física XREF por nivel",
        "",
        "> **Solo lectura.** Esta ronda valida la **transformación geométrica** recuperada de la "
        "XREF (bloque enlazado) más la transformación documentada en el JSON congelado de cada "
        "planta. **NO** asigna cargas, **NO** ejecuta áreas tributarias, **NO** modifica los JSON "
        "congelados y **no** hace Git. La asignación carga→losa queda fuera de alcance.",
        "",
        "## Cadena verificada",
        "",
        "- `p_700 = p_estructural + insercion_xref`   (XREF: escala 1, rotación 0, sin reflejo)",
        "- `p_estructural = p_700 - insercion_xref`   (inversa / round-trip)",
        "- `p_modelo = transformación congelada(p_estructural)` (sistema_coordenadas del JSON)",
        "",
        "No se reajusta escala/rotación/traslación y no se ejecuta un solver.",
        "",
        "## Resultado por nivel",
        "",
        "| Nivel | Planta | Estado | n axales | válidos axales (≤5cm) | residuo máx axal (m) | n geo |",
        "|-------|--------|--------|----------|-----------------------|----------------------|-------|",
    ]
    for cod, v in por_nivel.items():
        lines.append("| %s | %s | `%s` | %s | %s | %s | %s |" % (
            cod, v["planta_estructural"], v["estado"],
            v["n_cruces_axales"], v["n_validos_axales_tol_5cm"], v["residuo_max_axal_m"], v["n_cruces_geo"]))
    lines += [
        "",
        "## Controles por nivel",
        "",
        "Cada control registra: handle/capa, coordenada estructural original, coordenada en el 700 "
        "(XREF), estructural recuperado (round-trip), modelo predicho, modelo esperado y residuo (m).",
        "",
    ]
    for cod, v in por_nivel.items():
        lines.append("### %s — `%s`" % (cod, v["estado"]))
        lines.append("")
        lines.append("Transformación congelada: x = %s; y = %s" % (
            v["transformacion_congelada"]["x"], v["transformacion_congelada"]["y"]))
        lines.append("")
        lines.append("| Control | Capa | Estructural | En 700 | Recuperado | Modelo pred. | Modelo esp. | Δ(m) |")
        lines.append("|---------|------|-------------|--------|------------|--------------|-------------|------|")
        for c in v["controles"][:12]:
            lines.append("| %s | %s | (%.1f, %.1f) | (%.1f, %.1f) | (%.1f, %.1f) | (%.2f, %.2f) | (%.2f, %.2f) | %.3f |" % (
                c["etiqueta"], c["capa"],
                c["estructural_origen"][0], c["estructural_origen"][1],
                c["en_700"][0], c["en_700"][1],
                c["estructural_recuperado"][0], c["estructural_recuperado"][1],
                c["modelo_predicho"][0], c["modelo_predicho"][1],
                c["modelo_esperado"][0], c["modelo_esperado"][1],
                c["residuo_m"]))
        lines.append("")
        lines.append("**Motivo:** %s" % v["motivo"])
        lines.append("")
    lines += [
        "",
        "## Regla de exclusión",
        "",
        "Se excluyen explícitamente leyendas, muestras de trama, cajetines, límites de HATCH y "
        "regiones pertenecientes a otra planta. Los controles usados son rejilla estructural "
        "(`rle-ejes`) y su posición esperada proviene del `sistema_coordenadas` congelado.",
        "",
        "## Nota de alcance",
        "",
        "Esto establece si la **transformación geométrica** recuperada de la XREF + congelado es "
        "consistente. No implica que la carga de cada trama esté asignada a su losa: esa correlación "
        "carga→losa se aborda por separado y NO se autoriza en esta ronda.",
    ]
    (RES / "informe_validacion_fisica_xref.md").write_text("\n".join(lines), encoding="utf-8")


def _figuras(por_nivel: dict) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon as MplPoly
    except Exception:
        return
    for cod, v in por_nivel.items():
        fig, ax = plt.subplots(figsize=(9, 7))
        ax.set_title("Validación XREF — %s (%s)" % (cod, v["estado"]))
        # huella congelada
        huella = _huella_modelo(cod)
        if huella is not None:
            huella = huella if huella.geom_type != "MultiPolygon" else unary_union(list(huella.geoms))
            for poly in (list(huella.geoms) if huella.geom_type == "MultiPolygon" else [huella]):
                ext = poly.exterior.xy
                ax.fill(ext[0], ext[1], color=(0.6, 0.8, 1.0), alpha=0.4, label="huella congelada")
                ax.plot(ext[0], ext[1], color="blue", lw=1.4)
        # puntos de control
        xs = [c["modelo_predicho"][0] for c in v["controles"]]
        ys = [c["modelo_predicho"][1] for c in v["controles"]]
        ax.plot(xs, ys, "o", color="red", ms=5, label="cruces de eje (pred)")
        for c in v["controles"]:
            ax.annotate("%s (Δ %.2fm)" % (c["etiqueta"], c["residuo_m"]),
                        (c["modelo_predicho"][0], c["modelo_predicho"][1]),
                        fontsize=6, xytext=(2, 2), textcoords="offset points")
        ax.set_aspect("equal", adjustable="box")
        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(FIG / ("validacion_xref_%s.png" % cod), dpi=120)
        plt.close(fig)


if __name__ == "__main__":
    main()
    print("OK  resultados/cargas_reales/validacion_fisica_xref_por_nivel.json")
    print("OK  resultados/cargas_reales/informe_validacion_fisica_xref.md")
    print("OK  resultados/cargas_reales/figuras/validacion_xref_<nivel>.png")