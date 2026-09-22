"""
Correlacion espacial de cargas de la pagina 11 SOLO para Piso 1 (P1).

CONTEXTO
--------
CORRECCION (hallazgo de la ronda): la transformacion de P1 antes declarada `validada`
se auto-satisfacia alinear aristas de trama con la rejilla modular (~100 u/m), pero las
regiones de carga del DXF 700 caen descentradas ~35 m en x sobre la huella congelada
(solape ~20%). Por tanto la correlacion espacial region(page11)->losa NO esta autorizada.
Este script produce un DIAGNOSTICO honesto (sin tablas de areas) declarando P1 como
`pendiente_correlacion_vectorial`, no una asignacion de cargas.

ALCANCE
-------
Para P1 se calcula, en coordenadas del MODELO (m):
  * area neta por losa (bruta - aberturas);
  * area de interseccion de cada REGION de carga (trama) del DXF 700 con cada losa;
  * area por categoria de carga (PM_ADIC/SC) por losa;
  * area `por_confirmar_trama` (regiones sin combo) y `sin_clasificar` (losa sin region);
  * solapes de region dentro de una misma losa (en m2) y suma de control;
  * coordenadas (modelo) de las cargas puntuales VALIDADAS (ninguna en P1: las
    puntuales estan en P2/P3 -> se registran, no se ubican);

El desplazamiento del origen del DXF 700 respecto del origen estructural de P1 se
documenta; se requiere medicion AutoCAD para reorientar antes de autorizar la correlacion.

SALIDAS
-------
  datos/casos_analisis/correlacion_cargas_P1.json
  resultados/cargas_reales/correlacion_cargas_P1_areas.csv
  resultados/cargas_reales/figuras/correlacion_cargas_P1.png
"""

from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

import extraer_cargas_dxf as X

BASE = Path(__file__).resolve().parents[2]
GEO = BASE / "datos/geometria"
CARGAS_OUT = BASE / "datos/casos_analisis"
RES = BASE / "resultados" / "cargas_reales"
FIG = RES / "figuras"

P1_FILE = "edificio_I_cielo_piso_1_borrador.json"
TRANS_P1 = {"escala": 100.0, "ox": 5645.0, "oy": 4630.0, "flip_y": False}

KGF_A_KN = 0.00980665


def _p(pt):
    return (float(pt[0]), float(pt[1]))


def _poly(points):
    return Polygon([_p(p) for p in points])


def _dxf_a_modelo(x: float, y: float) -> Tuple[float, float]:
    t = TRANS_P1
    return ((x - t["ox"]) / t["escala"], (y - t["oy"]) / t["escala"])


def _poly_dxf_a_modelo(poly: Polygon) -> Polygon:
    t = TRANS_P1
    ring = list(poly.exterior.coords)
    out = Polygon([_dxf_a_modelo(x, y) for x, y in ring])
    return out


def main() -> dict:
    # --- cargas congeladas P1 ---
    data = json.loads((GEO / P1_FILE).read_text(encoding="utf-8"))
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    ab_global = {a["id"]: _poly(a["poligono"]) for a in data.get("aberturas_globales", [])
                 if a.get("poligono")}

    # --- lectura DXF 700 + correlacion de patrones ---
    dxf = X.extraer_dxf()
    corr = X.correlacion_pattern_combo(dxf)
    p1 = corr["P1"]["regiones"]
    # regiones grandes del DXF con su combo y poligono en modelo
    regiones = []
    by_patron = {r["patron"]: r for r in p1}
    for r in dxf["regiones"]["P1"]:
        if X._es_muestra_leyenda(r["outline"]):
            continue  # swatch de leyenda, no region de carga
        if r["outline"].geom_type != "Polygon" or r["outline"].is_empty:
            continue
        pol_m = _poly_dxf_a_modelo(r["outline"])
        cr = by_patron.get(r["patron"])
        regiones.append({
            "patron": r["patron"],
            "combo": {"PM_ADIC": (cr["PM_ADIC"] if cr else None),
                      "SC": (cr["SC"] if cr else None)},
            "estado": (cr["estado"] if cr else "por_confirmar_trama"),
            "carga_si": bool(cr and cr["PM_ADIC"] is not None),
            "poly": pol_m,
        })

    # --- resultados por losa ---
    losa_rows = []
    total_neta = 0.0
    for lo in losas:
        sp = _poly(lo["poligono_exterior"])
        # neto de aberturas
        neto = sp
        for aid in lo.get("aberturas", []) or []:
            ap = ab_global.get(aid if isinstance(aid, str) else aid.get("id"))
            if ap is not None and not ap.is_empty and sp.is_valid:
                try:
                    neto = neto.difference(ap)
                except Exception:
                    pass
        bruta = sp.area
        neta = neto.area
        total_neta += neta

        # resultados por categoria
        por_cat = {}   # (PM,SC) -> m2
        por_confirmar = 0.0
        solapes = 0.0   # area de doble cobertura de regiones sobre esta losa
        cobertura_total = 0.0
        region_hits = []
        for rg in regiones:
            if not rg["poly"].is_valid or rg["poly"].is_empty:
                continue
            try:
                inter = neto.intersection(rg["poly"])
            except Exception:
                continue
            a = inter.area if not inter.is_empty else 0.0
            if a <= 1e-6:
                continue
            region_hits.append({"patron": rg["patron"], "area_m2": round(a, 6),
                                "carga_si": rg["carga_si"]})
            cobertura_total += a
            if rg["carga_si"]:
                key = (rg["combo"]["PM_ADIC"], rg["combo"]["SC"])
                por_cat[key] = por_cat.get(key, 0.0) + a
            else:
                por_confirmar += a
        # solape bruto = suma de cobertura - area efectivamente cubierta (union)
        try:
            un = unary_union([rg["poly"].intersection(neto) for rg in regiones
                              if not rg["poly"].is_empty])
            union_area = un.area if not un.is_empty else 0.0
        except Exception:
            union_area = cobertura_total
        solapes = max(cobertura_total - min(union_area, neta), 0.0)
        sin_clasificar = max(neta - union_area, 0.0)

        losa_rows.append({
            "id": lo["id"],
            "espesor_m": lo.get("espesor"),
            "area_bruta_m2": round(bruta, 6),
            "area_neta_m2": round(neta, 6),
            "area_por_categoria_m2": {"{}/{}".format(k[0], k[1]): round(v, 6)
                                      for k, v in por_cat.items()},
            "PM_ADIC_SC_por_categoria_kgf_m2": [
                {"PM_ADIC": k[0], "SC": k[1], "area_m2": round(v, 6),
                 "carga_PM_ADIC_kN": round(v * k[0] * KGF_A_KN, 6),
                 "carga_SC_kN": round(v * k[1] * KGF_A_KN, 6)}
                for k, v in sorted(por_cat.items())],
            "area_por_confirmar_m2": round(por_confirmar, 6),
            "area_sin_clasificar_m2": round(sin_clasificar, 6),
            "solape_regiones_m2": round(solapes, 6),
            "region_hits": region_hits,
            "cobertura_total_m2": round(cobertura_total, 6),
        })

    # control entero: suma area neta == suma neta modelos
    suma_neta = round(sum(r["area_neta_m2"] for r in losa_rows), 6)
    control = {
        "suma_area_neta_losas_m2": suma_neta,
        "total_modelo_neta_m2": round(total_neta, 6),
        "verificado": abs(suma_neta - total_neta) < 1e-6,
    }

    # cargas puntuales: ninguna en P1 (estan en P2/P3); se documenta su estado
    puntuales = _puntuales()

    payload = {
        "titulo": "DIAGNOSTICO - Correlacion espacial de cargas (pagina 11) PISO 1: NO AUTORIZADA",
        "nivel": "P1",
        "estado": "pendiente_correlacion_vectorial",
        "asignacion_autorizada": False,
        "motivo": ("Las regiones de carga del DXF 700, colocadas con la transformacion antes "
                   "declarada 'validada' (escala 100, offset ox=5645, oy=4630, no_flip), caen "
                   "descentradas ~30 m en x sobre la huella congelada del Piso 1: el solape es "
                   "solo ~21%. La etiqueta 'validada' previa se auto-satisfizo alineando aristas "
                   "de TRAMA con la rejilla modular (coincidencia ~100 u/m), sin confirmar la "
                   "ubicacion real de las areas de carga sobre la planta estructural. Por ello "
                   "la correlacion region->losa NO es utilizable; NO se reportan areas por "
                   "categoria y NO se asigna ninguna carga."),
        "transformacion_previa_considerada": TRANS_P1,
        "diagnostico_aliniacion": _diagnostico_aliniacion(data),
        "regiones_dxf_P1": [{"patron": r["patron"], "combo": r["combo"],
                             "estado": r["estado"]} for r in regiones],
        # NO se incluyen tablas de areas por losa/categoria: la correlacion no esta
        # autorizada por el desalineamiento; incluir areas seria un resultado enganoso.
        "control_total": None,
        "cargas_puntuales": puntuales,
        "accion_requerida": ("Medir en AutoCAD/DXF el desplazamiento real entre el origen "
                             "del DXF 700 y el origen estructural de P1 (ver solicitud de "
                             "mediciones al final de la ronda)."),
    }

    CARGAS_OUT.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    (CARGAS_OUT / "correlacion_cargas_P1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # NOTA: NO se escribe CSV de areas por categoria: la correlacion no esta autorizada.
    _figura_diagnostico(payload, regiones)

    return payload


def _puntuales() -> list:
    # Coords de puntuales validadas: no hay en P1 (las puntuales del plano estan en P2/P3)
    return [{
        "nivel": "P1", "existen_cargas_puntuales": False,
        "nota": "Las cargas puntuales de la lamina pagina 11 estan en Piso 2 y Piso 3, no en P1.",
    }]


def _diagnostico_aliniacion(data: dict) -> dict:
    """Mide el solape real regiones(DXF700 transform)->huella congelada de P1.
    Devuelve areas y porcentajes; el resultado decide la autorizacion."""
    import sys
    sys.path.insert(0, str(BASE / "src" / "analisis"))
    import extraer_cargas_dxf as X
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    dxf = X.extraer_dxf()
    t = TRANS_P1

    def dm(x, y):
        return ((x - t["ox"]) / t["escala"], (y - t["oy"]) / t["escala"])
    pols = []
    for r in dxf["regiones"]["P1"]:
        if X._es_muestra_leyenda(r["outline"]):
            continue
        if r["outline"].geom_type != "Polygon" or r["outline"].is_empty:
            continue
        pols.append(Polygon([dm(x, y) for x, y in r["outline"].exterior.coords]))
    union_r = unary_union(pols) if pols else Polygon()
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    foot = unary_union([Polygon([(p[0], p[1]) for p in lo["poligono_exterior"]])
                        for lo in losas])
    inter = union_r.intersection(foot).area if not (union_r.is_empty or foot.is_empty) else 0.0
    return {
        "area_regiones_dxf_modelo_m2": round(union_r.area, 1),
        "area_huella_congelada_m2": round(foot.area, 1),
        "area_solape_m2": round(inter, 2),
        "solape_pct_sobre_huella": round(100 * inter / max(foot.area, 1e-9), 2),
        "bbox_regiones_modelo": tuple(round(v, 1) for v in union_r.bounds),
        "bbox_huella_modelo": tuple(round(v, 1) for v in foot.bounds),
        "desplazamiento_observado_m_aprox_x": round(foot.centroid.x - union_r.centroid.x, 1),
        "conclusion": "NO AUTORIZADA" if inter / max(foot.area, 1e-9) < 0.5 else "OK",
    }


def _figura_diagnostico(payload: dict, regiones: list) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    data = json.loads((GEO / P1_FILE).read_text(encoding="utf-8"))
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    fig, ax = plt.subplots(figsize=(11, 9))
    for lo in losas:
        p = _poly(lo["poligono_exterior"])
        xs, ys = p.exterior.xy
        ax.plot(xs, ys, color="#1f77b4", lw=1.2)
        ax.fill(xs, ys, color="#1f77b4", alpha=0.10)
        ax.text(np.mean(xs), np.mean(ys), lo["id"].split("_")[-1],
                fontsize=5, ha="center", va="center")
    cmap = plt.get_cmap("rainbow")
    for i, rg in enumerate(regiones):
        if rg["poly"].is_empty:
            continue
        col = cmap(i / max(len(regiones) - 1, 1))
        c = rg["poly"].exterior.xy
        ax.plot(*c, color=col, lw=0.7, ls="--")
        ax.fill(*c, color=col, alpha=0.15)
        ax.text(np.mean(c[0]), np.mean(c[1]), rg["patron"], fontsize=6,
                ha="center", va="center", color="black")
    ax.set_aspect("equal")
    ax.set_title("P1 - DIAGNOSTICO: regiones DXF700 (lineas) vs huella congelada (azul)\n"
                 "Se observa descentrado ~30 m en x -> correlacion NO AUTORIZADA")
    ax.grid(alpha=0.3)
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "correlacion_cargas_P1.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
    print("OK  datos/casos_analisis/correlacion_cargas_P1.json  (DIAGNOSTICO NO AUTORIZADA)")
    print("OK  resultados/cargas_reales/figuras/correlacion_cargas_P1.png")