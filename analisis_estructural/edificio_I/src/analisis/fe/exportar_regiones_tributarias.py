"""Exporta la GEOMETRIA REAL de las regiones tributarias del Edificio I para el
viewer Unity.

NO resuelve ni modifica la solucion FE: re-ejecuta UNICAMENTE el reparto
geometrico determinista documentado (misma geometria comun, mismos parametros,
mismo mallado y mismo "soporte mas cercano") que produjo `por_viga.json`, y
conserva las CELDAS de la malla (centroide + area + poligono) asignadas a cada
receptor. La carga/area por losa se tomma de `por_viga.json` (autoritativo) para
que las celdas de una misma losa repartan la carga de forma PROPORCIONAL al area
(descarga superficial uniforme).

Salida: <viewer>/Assets/StreamingAssets/lab_data/edificios/I/tributary/
        regiones_tributarias.json
        + verificacion_resumen_por_viga.csv  (celdas vs por_viga por receptor)

Convencion de salida: receptores en coordenadas COMUNES (u,v); Unity usa
(X,Y,Z)=(u,cota,v) con la transformacion central del edificio.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

from . import geometria_fe as GF
from .tributaria import _receptor_lineas, distribuir_losa
from .hipotesis import niveles_ordenados

_LAB = Path(__file__).resolve().parents[3]
_PV = _LAB / ".." / "viewer_unity" / "Assets" / "StreamingAssets" / "lab_data" / "edificios" / "I" / "tributary" / "por_viga.json"
_OUT_DIR = _PV.parent
COTA = {"CP1S": -4.01, "P1": -0.05, "P2": 3.91, "P3": 7.87, "P4": 11.83}
MALLADO = 0.25


def _neto(losa) -> Polygon:
    from .geometria_fe import construir_superficies
    return construir_superficies([losa])[0]["neto"]


def _celdas_poligonos(celdas, neto):
    """Reconstruye el poligono de cada celda de la malla cuadrada (side=mallado)
    clipado al dominio neto, a partir de los centroides canonicos de la malla.

    Cada celda se emite como UN registro por pieza (el clip al neto puede partir
    una celda en varias piezas al bordear una abertura); cada pieza guarda su area
    proporcional para que la suma de areas de las piezas = area total de la celda
    y la carga por losa se reparta de forma consistente con por_viga."""
    if not celdas:
        return []
    minx, miny, maxx, maxy = neto.bounds
    nx = max(int((maxx - minx) / MALLADO), 1)
    ny = max(int((maxy - miny) / MALLADO), 1)
    sx = (maxx - minx) / nx
    sy = (maxy - miny) / ny
    out = []
    for c in celdas:
        cx, cy = c["x"], c["y"]
        sq = Polygon([(cx - sx / 2, cy - sy / 2), (cx + sx / 2, cy - sy / 2),
                      (cx + sx / 2, cy + sy / 2), (cx - sx / 2, cy + sy / 2)])
        clip = sq.intersection(neto)
        if clip.is_empty or clip.area <= 0:
            continue
        polys = list(clip.geoms) if clip.geom_type == "MultiPolygon" else [clip]
        for p in polys:
            coords = list(p.exterior.coords)
            ring = [[round(x, 4), round(y, 4)] for (x, y) in coords[:-1]]
            if len(ring) < 3:
                continue
            area_piece = round(p.area / clip.area * c["area_m2"], 5) if clip.area else 0.0
            out.append({"u": round(cx, 4), "v": round(cy, 4),
                        "area_m2": area_piece, "poligono": [ring]})
    return out


def _por_viga_cargas():
    """Cargas por losa por receptor desde por_viga.json (autoritativo)."""
    doc = json.loads(_PV.read_text(encoding="utf-8"))
    out = {}
    for lvl, beans in doc["por_nivel"].items():
        out[lvl] = {}
        for b in beans:
            rid = b["receptor"]
            per_losa = {}
            for lp in b.get("losas", []):
                per_losa[lp["losa"]] = {"area_m2": lp.get("area_m2"),
                                        "carga_kN": lp.get("carga_kN")}
            out[lvl][rid] = {"area_total_m2": b.get("area_tributaria_m2"),
                             "carga_total_kN": b.get("carga_total_kN"),
                             "por_losa": per_losa}
    return out


def main():
    niveles = GF.cargar_todos()
    pvv = _por_viga_cargas()
    por_nivel = {}
    diffs = []

    for cod in niveles_ordenados():
        n = niveles[cod]
        if cod not in pvv:
            continue  # sin receptores en por_viga para este nivel
        nivel_out = {"cota": COTA[cod], "receptores": {}}
        # agregar celdas por losa -> por receptor (misma geometria que la corrida FE)
        recep_tot = {}
        for lo in n.losas:
            neto = _neto(lo)
            ss = _receptor_lineas(n)
            validos = set(ss.keys())
            if lo.get("apoyos"):
                validos = set(lo["apoyos"])
            sop = {k: v for k, v in ss.items() if k in validos}
            if neto.area <= 0:
                continue
            _, celdas = distribuir_losa(neto, sop, MALLADO)
            for rid, celllist in celdas.items():
                polys = _celdas_poligonos(celllist, neto)
                # area/carga proporcionales desde por_viga para esta losa
                info = pvv.get(cod, {}).get(rid, {}).get("por_losa", {}).get(lo["id"])
                if info is None:
                    continue
                reg = recep_tot.setdefault(rid, {"area_m2": 0.0, "carga_kN": 0.0,
                                                 "celdas": []})
                for cell in polys:
                    cell["losa"] = lo["id"]
                    cell["carga_kN"] = 0.0
                    if info["area_m2"]:
                        carga_cell = cell["area_m2"] / info["area_m2"] * (info["carga_kN"] or 0.0)
                        cell["carga_kN"] = round(carga_cell, 5)
                        reg["carga_kN"] += carga_cell
                    reg["celdas"].append(cell)
        # empaquetar
        for rid, reg in recep_tot.items():
            nivel_out["receptores"][rid] = {
                "area_total_m2": round(sum(c["area_m2"] for c in reg["celdas"]), 4),
                "carga_total_kN": round(reg["carga_kN"], 4),
                "n_losas": len({c["losa"] for c in reg["celdas"]}),
                "celdas": reg["celdas"],
            }
        por_nivel[cod] = nivel_out
        # verificacion contra por_viga
        for rid, rec in nivel_out["receptores"].items():
            ref = pvv[cod].get(rid)
            if ref is None:
                continue
            da = abs(rec["area_total_m2"] - (ref["area_total_m2"] or 0.0))
            diffs.append([cod, rid, rec["area_total_m2"], ref["area_total_m2"], da,
                          len(rec["celdas"])])

    out = {
        "ejecucion": "primera_ejecucion",
        "mallado_m": MALLADO,
        "frame": "comun (u,v); Unity (X,Y,Z)=(u,cota,v)",
        "advertencia": ("Representacion academica provisional de las regiones "
                        "tributarias del reparto geometrico (celdas). No sustituye "
                        "la solucion FE ni datos de diseno."),
        "por_nivel": por_nivel,
    }
    out_path = _OUT_DIR / "regiones_tributarias.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # resumen csv
    csv_path = _OUT_DIR / "verificacion_resumen_por_viga.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nivel", "receptor", "area_celdas_m2", "area_por_viga_m2", "diff_m2", "n_celdas"])
        w.writerows(diffs)

    n_rec = sum(len(p["receptores"]) for p in por_nivel.values())
    maxd = max((d[4] for d in diffs), default=0.0)
    print(f"[regiones] escrito: {out_path}")
    print(f"[regiones] receptores totales: {n_rec}; max_delta_area_vs_por_viga: {maxd:.4f} m2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
