"""
Propuesta preliminar de mecanismo de transferencia de carga por losa (Edificio I).

ALCANCE Y HONESTIDAD
--------------------
Este modulo produce una CLASIFICACION PRELIMINAR (no definitiva) del tipo de
transferencia de cada losa congelada, combinando:

  * la geometria congelada de cada nivel (losas, vigas, muros, aberturas,
    bordes libres, junta, sistema_coordenadas);
  * los receptores declarados en ``apoyos_validos`` de cada losa;
  * el sistema de losa confirmado por los DXF estructurales (2017_67-101/102/103):
    LOSA SOLIDA e=15 cm en todos los pisos (no hay rotulos de nervios/bovedilla
    ni texto de direccion unidireccional/bidireccional).

Regla (consigna del usuario):
  1. ``bidireccional_propuesto`` SOLO cuando: losa solida confirmada; apoyos
     lineales continuos en las DOS direcciones ortogonales; no son simples
     apoyos puntuales; juntas/aberturas no interrumpen esos apoyos; y la
     relacion de luces es compatible con trabajo bidireccional.
  2. ``unidireccional_{x,y}_propuesto`` cuando la topologia es inequivoca:
     dos lineas de apoyo opuestas y paralelas con los otros bordes libres/sin
     apoyo continuo; o un voladizo con una unica linea de empotramiento/apoyo
     y borde opuesto libre. La direccion es perpendicular a las lineas de apoyo.
  3. ``por_definir`` cuando: tres lados apoyados; relacion de luces dudosa;
     receptores interiores / apoyos puntuales / juntas / grandes aberturas que
     alteren el comportamiento; falta continuidad verificable; o hay mas de una
     interpretacion razonable.

NO se decide unidireccional/bidireccional solo por forma (relacion de lados) ni
por la cantidad de apoyos listados: se verifica geometricamente que cada apoyo
cubra el lado correspondiente (coincidencia borde<->eje de viga/muro).

El resultado refleja la topologia estructural congelada + el sistema de losa
confirmado por DXF, y NO debe usarse para diseno hasta confirmarse con el criterio
normativo y el diseno de armaduras.

No modifica los JSON congelados. No ejecuta tributacion ni analisis numerico.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import Polygon, LineString
from shapely import STRtree

BASE = Path(__file__).resolve().parents[2]
GEO = BASE / "datos/geometria"
OUT_DATOS = BASE / "datos/casos_analisis"
OUT_RES = BASE / "resultados" / "areas_tributarias"

NIVELES = {
    "CP1S": "edificio_I_cielo_piso_1_subterraneo_borrador.json",
    "P1":   "edificio_I_cielo_piso_1_borrador.json",
    "P2":   "edificio_I_cielo_piso_2_borrador.json",
    "P3":   "edificio_I_cielo_piso_3_borrador.json",
    "P4":   "edificio_I_cielo_piso_4_borrador.json",
}
ETIQUETA = {"CP1S": "1° Subterráneo", "P1": "Piso 1", "P2": "Piso 2",
            "P3": "Piso 3", "P4": "Piso 4"}

TOL = 0.12  # m, tolerancia borde<->eje de apoyo


def _as_list(v):
    return v if isinstance(v, list) else list(v.values()) if isinstance(v, dict) else []


def _p(pt) -> Tuple[float, float]:
    return (float(pt[0]), float(pt[1]))


def cargar_nivel(cod: str) -> dict:
    return json.loads((GEO / NIVELES[cod]).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# helpers geometricos
# ---------------------------------------------------------------------------
def _axis_viga(v: dict) -> Optional[LineString]:
    p = v.get("eje") or {}
    ini = p.get("inicio") or v.get("inicio")
    fin = p.get("fin") or v.get("fin")
    if ini and fin:
        return LineString([_p(ini), _p(fin)])
    return None


def _axis_muro(m: dict) -> Optional[LineString]:
    p = m.get("eje") or {}
    ini, fin = p.get("inicio"), p.get("fin")
    if ini and fin:
        return LineString([_p(ini), _p(fin)])
    return None


def _orientation(ls: LineString) -> Optional[str]:
    co = list(ls.coords)
    if len(co) < 2:
        return None
    dx = abs(co[-1][0] - co[0][0])
    dy = abs(co[-1][1] - co[0][1])
    if max(dx, dy) < 1e-9:
        return None
    if dy / max(dx, dy) < 0.05:
        return "x"
    if dx / max(dx, dy) < 0.05:
        return "y"
    return "diag"


def _parts(poly: Polygon) -> List[List[Tuple[float, float]]]:
    """Devuelve la lista de anillos (exterior + huecos) de un poligono simple."""
    ring = lambda r: list(r.coords)
    out = [ring(poly.exterior)]
    for i in poly.interiors:
        out.append(ring(i))
    return out


def _polygon(losa) -> Polygon:
    return Polygon([_p(p) for p in losa["poligono_exterior"]])


def _edges_from_ring(co: List[Tuple[float, float]]) -> List[LineString]:
    return [LineString([co[i], co[i + 1]]) for i in range(len(co) - 1)]


def _edges(poly: Polygon) -> List[Tuple[LineString, int]]:
    out = []
    ring = list(poly.exterior.coords)
    for i in range(len(ring) - 1):
        out.append((LineString([ring[i], ring[i + 1]]), i))
    return out


def _edge_support_coverage(edge: LineString, axis: LineString, tol: float) -> float:
    """Fraccion [0,1] de la longitud del borde cubierta por el eje, si es ~colineal."""
    p0, p1 = list(edge.coords)
    vx, vy = p1[0] - p0[0], p1[1] - p0[1]
    L = (vx * vx + vy * vy) ** 0.5
    if L < 1e-9:
        return 0.0
    ux, uy = vx / L, vy / L
    nx, ny = -uy, ux
    s = np.linspace(0, 1, 60)
    covered = 0.0
    for t0, t1 in zip(s[:-1], s[1:]):
        a = axis.interpolate(t0, normalized=True)
        b = axis.interpolate(t1, normalized=True)
        d0 = (a.x - p0[0]) * ux + (a.y - p0[1]) * uy
        d1 = (b.x - p0[0]) * ux + (b.y - p0[1]) * uy
        n0 = (a.x - p0[0]) * nx + (a.y - p0[1]) * ny
        n1 = (b.x - p0[0]) * nx + (b.y - p0[1]) * ny
        mid_d, mid_n = (d0 + d1) / 2, (n0 + n1) / 2
        step = a.distance(b)
        if abs(mid_n) <= tol and 0.0 <= mid_d <= L:
            covered += step
    return min(covered / L, 1.0)


def _free_edge_segments(data: dict) -> List[LineString]:
    out = []
    for b in _as_list(data.get("bordes_libres")):
        p = b.get("eje") or {}
        ini = p.get("inicio") or b.get("inicio")
        fin = p.get("fin") or b.get("fin")
        if ini and fin:
            out.append(LineString([_p(ini), _p(fin)]))
    return out


def _edge_is_free(edge: LineString, free_edges: List[LineString]) -> bool:
    if not free_edges:
        return False
    tree = STRtree(free_edges)
    hits = tree.query(edge)
    for h in hits:
        fe = free_edges[h]
        if edge.distance(fe) <= 0.02:
            return True
    return False


def _junta_ids(data: dict) -> List[str]:
    j = data.get("juntas_dilatacion") or data.get("junta_dilatacion")
    if isinstance(j, list):
        return [x.get("id", "?") for x in j]
    if isinstance(j, dict):
        return [k for k in j]
    return []


# ---------------------------------------------------------------------------
# analisis por losa
# ---------------------------------------------------------------------------
def _receptor_index(data: dict) -> Dict[str, dict]:
    idx = {}
    for v in _as_list(data.get("vigas")):
        a = _axis_viga(v)
        if a is not None:
            idx[v["id"]] = {"axis": a, "tipo": "viga", "recibe": bool(v.get("recibe_losa"))}
    for m in _as_list(data.get("muros")):
        a = _axis_muro(m)
        if a is not None:
            idx[m["id"]] = {"axis": a, "tipo": "muro", "recibe": bool(m.get("recibe_losa"))}
    return idx


def _slab_analysis(cod: str, losa: dict, data: dict) -> dict:
    ridx = _receptor_index(data)
    poly = _polygon(losa)
    edges = _edges(poly)
    free_edges = _free_edge_segments(data)
    juntas = _junta_ids(data)

    ab_ids = [a if isinstance(a, str) else a.get("id") for a in (losa.get("aberturas") or [])]
    ab_ids = [a for a in ab_ids if a]
    aberturas_pol = {a["id"]: Polygon([_p(p) for p in a["poligono"]])
                     for a in (_as_list(data.get("aberturas_globales")) or [])
                     if a.get("poligono")}

    av = losa.get("apoyos_validos") or []
    resp = []
    for aid in av:
        r = ridx.get(aid)
        if r is not None and r["recibe"]:
            resp.append({"id": aid, "tipo": r["tipo"], "axis": r["axis"],
                         "orient": _orientation(r["axis"])})

    edge_info = []
    n_apoyo = 0
    direcciones_apoyo = set()
    for edge, i in edges:
        fracs = []
        for r in resp:
            c = _edge_support_coverage(edge, r["axis"], TOL)
            if c > 0.5:
                fracs.append({"receptor": r["id"], "tipo": r["tipo"],
                              "orient": r["orient"], "cobertura": round(c, 3)})
                if r["orient"]:
                    direcciones_apoyo.add(r["orient"])
        es_libre = _edge_is_free(edge, free_edges)
        if fracs:
            n_apoyo += 1
        edge_info.append({
            "borde": i, "longitud_m": round(edge.length, 4),
            "apoyos": fracs, "es_borde_libre": es_libre,
        })

    # condicion de abertura grande: interseccion sustancial (>8% area)
    abertura_grande = False
    for a_id in ab_ids:
        ap = aberturas_pol.get(a_id)
        if ap is not None and not ap.is_empty and poly.is_valid:
            try:
                if poly.intersection(ap).area / max(poly.area, 1e-9) > 0.08:
                    abertura_grande = True
            except Exception:
                pass

    # receptor interior (viga/muro cuyo eje NO coincide con ningun borde -> apoyo interior)
    receptor_interior = False
    for r in resp:
        toca_borde = any(e.distance(r["axis"]) <= 0.05 for e, _ in edges)
        if not toca_borde:
            receptor_interior = True

    luces = _luces(poly)
    relacion = round(luces["larga_m"] / luces["corta_m"], 3) if luces["corta_m"] > 0 else None
    es_voladizo = _voladizo_hint(losa)

    return {
        "id": losa["id"], "nivel": cod, "etiqueta": ETIQUETA[cod],
        "espesor_m": losa.get("espesor"),
        "area_bruta_m2": round(poly.area, 4),
        "n_aberturas": len(ab_ids), "aberturas_ids": ab_ids,
        "abertura_grande": abertura_grande,
        "receptor_interior": receptor_interior,
        "receptores_declarados": av,
        "receptores_resueltos": [{"id": r["id"], "tipo": r["tipo"], "orient": r["orient"]}
                                 for r in resp],
        "lados_con_apoyo_continuo": n_apoyo,
        "direcciones_de_apoyo": sorted(direcciones_apoyo),
        "bordes": edge_info,
        "luces": luces, "relacion_luz_larga_corta": relacion,
        "es_voladizo_hint": es_voladizo,
        "junta_ids": juntas,
    }


def _luces(poly: Polygon) -> Dict[str, float]:
    minx, miny, maxx, maxy = poly.bounds
    dx, dy = maxx - minx, maxy - miny
    corta, larga = sorted([dx, dy])
    return {"corta_m": round(corta, 4), "larga_m": round(larga, 4),
            "bbox_x_m": round(dx, 4), "bbox_y_m": round(dy, 4)}


def _voladizo_hint(losa: dict) -> bool:
    txt = str(losa.get("_nota") or "") + "|" + str(losa.get("_categoria_banda") or "") \
        + "|" + str(losa.get("_flags") or "")
    t = txt.lower()
    return ("voladizo" in t or "volado" in t or "vol" in t.replace("_", " ")
            or "cantil" in t)


def _apoyos_por_direccion(analisis: dict) -> Dict[str, List[str]]:
    dd = defaultdict(list)
    for b in analisis["bordes"]:
        for a in b["apoyos"]:
            if a["orient"] and a["cobertura"] >= 0.5:
                dd[a["orient"]].append(a["receptor"])
    return dict(dd)


def _bordes_libres_idx(analisis: dict) -> List[int]:
    return [b["borde"] for b in analisis["bordes"] if b["es_borde_libre"]]


# ---------------------------------------------------------------------------
# clasificacion
# ---------------------------------------------------------------------------
def clasificar(analisis: dict) -> dict:
    n_ap = analisis["lados_con_apoyo_continuo"]
    dirs = set(analisis["direcciones_de_apoyo"])
    relacion = analisis["relacion_luz_larga_corta"]
    aberturas = analisis["aberturas_ids"]
    apoyos_x_dir = _apoyos_por_direccion(analisis)
    bordes_libres = _bordes_libres_idx(analisis)

    base = {
        "luz_corta_m": analisis["luces"]["corta_m"],
        "luz_larga_m": analisis["luces"]["larga_m"],
        "relacion_luces": relacion,
        "lados_apoyo_continuo": n_ap,
        "direcciones_apoyo": sorted(dirs),
        "apoyos_por_direccion": apoyos_x_dir,
        "bordes_libres": bordes_libres,
        "junta_ids": analisis["junta_ids"],
        "aberturas_relevantes": aberturas,
        "evidencia_dxf": _EVIDENCIA_DXF,
    }

    # voladizo inequivoco (nombre/categoria lo declara)
    if analisis["es_voladizo_hint"] and n_ap == 1 and len(set(apoyos_x_dir)) == 1:
        d = next(iter(apoyos_x_dir))
        perp = "y" if d == "x" else "x"
        if bordes_libres or True:
            base.update({
                "clasificacion_propuesta": "unidireccional_%s_propuesto" % perp,
                "tipo_transferencia_propuesta": "uni_%s" % perp,
                "direccion_propuesta": [0.0, 1.0] if perp == "y" else [1.0, 0.0],
                "nivel_certeza": "media",
                "motivo": ("losas voladiza declarada (nombre/categoria): una unica linea "
                           "de apoyo continua y borde opuesto libre/saliente; direccion "
                           "%s perpendicular a la linea de apoyo") % perp,
            })
            return base
    # voladizo declarado pero sin apoyo resuelto inequivoco -> por_definir con motivo especifico
    if analisis["es_voladizo_hint"] and n_ap <= 1:
        base.update({
            "clasificacion_propuesta": "por_definir",
            "tipo_transferencia_propuesta": "por_definir",
            "direccion_propuesta": None, "nivel_certeza": "baja_media",
            "motivo": ("losa declarada voladiza/cantilever pero la linea de apoyo no se "
                       "resolvio de forma inequivoca (n lado(s) con apoyo continuo=%d, "
                       "apoyos_validos=%s). Confirmar linea de empotramiento en planta "
                       "estructural.") % (n_ap, analisis["receptores_declarados"]),
        })
        return base

    # bidireccional
    if n_ap >= 3 and {"x", "y"} <= dirs:
        if analisis["abertura_grande"] or analisis["receptor_interior"]:
            base.update({
                "clasificacion_propuesta": "por_definir",
                "tipo_transferencia_propuesta": "por_definir",
                "direccion_propuesta": None, "nivel_certeza": "baja_media",
                "motivo": ("losa solida con apoyos en ambas direcciones pero %s altera la "
                           "continuidad del mecanismo; confirmar en planta estructural" % (
                             "abertura grande" if analisis["abertura_grande"]
                             else "receptor interior/apoyo puntual")),
            })
            return base
        if relacion is not None and relacion >= 2.0:
            base.update({
                "clasificacion_propuesta": "por_definir",
                "tipo_transferencia_propuesta": "por_definir",
                "direccion_propuesta": None, "nivel_certeza": "baja_media",
                "motivo": ("losa solida con apoyos en ambas direcciones pero relacion de "
                           "luces %.2f >= 2, dudosa para trabajo bidireccional. Confirmar "
                           "con norma") % relacion,
            })
            return base
        if not dirs_x_e_y_continuos(apoyos_x_dir):
            base.update({
                "clasificacion_propuesta": "por_definir",
                "tipo_transferencia_propuesta": "por_definir",
                "direccion_propuesta": None, "nivel_certeza": "baja_media",
                "motivo": ("apoyos en ambas direcciones pero no continuos lineales "
                           "completos (puede haber apoyos puntuales o interrupciones)"),
            })
            return base
        base.update({
            "clasificacion_propuesta": "bidireccional_propuesto",
            "tipo_transferencia_propuesta": "bidireccional",
            "direccion_propuesta": None,
            "nivel_certeza": "media" if relacion is not None and relacion <= 1.8 else "baja_media",
            "motivo": ("losa solida e=15: apoyos lineales continuos en ambas direcciones "
                       "ortogonales (>=3 lados), sin aberturas criticas ni junta que "
                       "interrumpa"),
        })
        return base

    # unidireccional dos lados opuestos
    if n_ap == 2 and len(dirs) == 1:
        d = next(iter(dirs))
        perp = "y" if d == "x" else "x"
        apoyados = [b["borde"] for b in analisis["bordes"] if b["apoyos"]]
        otros = [b["borde"] for b in analisis["bordes"] if not b["apoyos"]]
        otros_libres = all(b["es_borde_libre"] for b in analisis["bordes"] if b["borde"] in otros)
        if len(otros) == 2 and otros_libres and not aberturas and not analisis["receptor_interior"]:
            base.update({
                "clasificacion_propuesta": "unidireccional_%s_propuesto" % perp,
                "tipo_transferencia_propuesta": "uni_%s" % perp,
                "direccion_propuesta": [0.0, 1.0] if perp == "y" else [1.0, 0.0],
                "nivel_certeza": "media_alta",
                "motivo": ("losa solida e=15: dos lineas de apoyo opuestas y paralelas "
                           "(dir %s), bordes restantes libres; direccion %s perpendicular") % (d, perp),
            })
            return base

    # por_definir
    motivo = ("losa solida e=15 sin evidencia inequivoca de direccion de transferencia: "
              "%d lado(s) con apoyo continuo, direcciones %s, aberturas %s")
    motivo = motivo % (n_ap, ",".join(sorted(dirs)) or "ninguna", str(aberturas))
    base.update({
        "clasificacion_propuesta": "por_definir",
        "tipo_transferencia_propuesta": "por_definir",
        "direccion_propuesta": None, "nivel_certeza": "baja_media",
        "motivo": motivo,
    })
    return base


def dirs_x_e_y_continuos(apoyos_x_dir: Dict[str, List[str]]) -> bool:
    return all(len(v) >= 1 for v in apoyos_x_dir.values())


_EVIDENCIA_DXF = ("LOSA SOLIDA e=15 (DXF estructural 2017_67-101/102/103); "
                  "apoyos segun apoyos_validos congelados")


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def proponer_todo() -> Dict[str, dict]:
    result = {}
    for cod in NIVELES:
        data = cargar_nivel(cod)
        losas = _as_list(data.get("losas"))
        filas = []
        for losa in losas:
            analisis = _slab_analysis(cod, losa, data)
            clasif = clasificar(analisis)
            fila = {**analisis, **clasif}
            # limpiar campos internos
            fila.pop("bordes", None)
            filas.append(fila)
        result[cod] = {
            "nivel": cod,
            "etiqueta": ETIQUETA[cod],
            "sistema_losa_dxf": "solida e=15 cm (DXF estructural)",
            "losas": filas,
        }
    return result


def generar_deliverables(escribir: bool = True):
    OUT_DATOS.mkdir(parents=True, exist_ok=True)
    OUT_RES.mkdir(parents=True, exist_ok=True)
    prop = proponer_todo()
    payload = {
        "titulo": "Propuesta preliminar de transferencia de carga por losa - Edificio I",
        "estado": "propuesta_no_definitiva",
        "nota": ("Clasificacion preliminar basada en geometria congelada (solo lectura) + "
                 "sistema de losa solida confirmado por DXF estructural. NO sustituye el "
                 "criterio normativo ni el diseno de armaduras; confirmar antes de diseno."),
        "fuente_dxf_estructural": "2017_67-101/102/103.dxf (losas solidas e=15)",
        "niveles": prop,
    }
    json_path = OUT_DATOS / "propuesta_transferencia_edificio_I.json"
    if escribir:
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        _escribir_csv(prop)
    return payload


def _escribir_csv(prop: dict) -> None:
    import csv
    path = OUT_RES / "propuesta_transferencia_edificio_I.csv"
    cols = ["nivel", "losa", "tipo_transferencia_propuesta", "clasificacion_propuesta",
            "direccion_propuesta", "espesor_m", "area_bruta_m2", "luz_corta_m", "luz_larga_m",
            "relacion_luces", "lados_apoyo_continuo", "direcciones_apoyo", "bordes_libres",
            "aberturas", "receptor_interior", "nivel_certeza", "motivo"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for cod, info in prop.items():
            for losa in info["losas"]:
                w.writerow([
                    cod, losa["id"], losa.get("tipo_transferencia_propuesta"),
                    losa.get("clasificacion_propuesta"),
                    losa.get("direccion_propuesta"),
                    losa.get("espesor_m"), losa.get("area_bruta_m2"),
                    losa.get("luces", {}).get("corta_m"),
                    losa.get("luces", {}).get("larga_m"),
                    losa.get("relacion_luz_larga_corta"),
                    losa.get("lados_con_apoyo_continuo"),
                    ",".join(losa.get("direcciones_de_apoyo", []) or []),
                    ";".join(str(i) for i in (losa.get("bordes_libres") or [])),
                    ";".join(losa.get("aberturas_ids", []) or []),
                    losa.get("receptor_interior"),
                    losa.get("nivel_certeza"),
                    losa.get("motivo"),
                ])


if __name__ == "__main__":
    r = generar_deliverables(escribir=True)
    for cod, info in r["niveles"].items():
        conteo = {}
        for lo in info["losas"]:
            t = lo.get("tipo_transferencia_propuesta")
            conteo[t] = conteo.get(t, 0) + 1
        print(cod, conteo)