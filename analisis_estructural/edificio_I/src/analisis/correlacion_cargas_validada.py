"""
Correlacion espacial de cargas (pagina 11) usando las transformaciones XREF VALIDADAS.

ALCANCE
-------
Solo P1, P2 y P3 (los tres niveles con `transformacion_xref_validada`). La cadena
coordinada VERIFICADA es:

    p_estructural = p_700 - insercion_xref          (XREF: escala 1, rotacion 0, sin reflejo)
    p_modelo      = transformacion_congelada(p_estructural)   (sistema_coordenadas del JSON)

que cierra sobre la rejilla etiquetada con residuos <= 5 cm (ver
validacion_fisica_xref_por_nivel.json). Sobre esa base se intersectan las regiones de
carga del DXF 700 contra los dominios netos (losas menos aberturas) y se reporta, por
losa y categoria: region fuente, area de interseccion, valor literal, unidad,
interpretacion provisional de unidades, certeza y transformacion utilizada.

REGLA DE EXCLUSION
------------------
Las muestras (swatches) de la leyenda "CARGAS DE DISEÑO" se identifican por EVIDENCIA
CAD (caja compacta ~1611 x ~237 uds graficas, bbox de hatch), mediante
`extraer_cargas_dxf._es_muestra_leyenda`; NO por parecido de area. Cualquier region con
esa huella pero que NO sea muestra de leyenda no se excluye si no cumple el bbox.

LOCALIDAD DE LA CORRESPONDENCIA TRAMA->CARGA
--------------------------------------------
La correspondencia patron->(PM_ADIC, SC) es ESPECIFICA DE CADA NIVEL (se lee de la
leyenda de cada planta). No hay diccionario global por nombre de patron; para `_USER`
se valida contra la muestra de leyenda de cada nivel (puede no denotar una carga unica).

SALIDAS
-------
  datos/casos_analisis/correlacion_cargas_validada_P123.json
  resultados/cargas_reales/correlacion_cargas_P123.png
  resultados/cargas_reales/informe_correlacion_validada_P123.md
  resultados/cargas_reales/correlacion_cargas_validada_P123_por_losa.csv
"""

from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

import extraer_cargas_dxf as X
import correlacion_pagina11 as P11

BASE = Path(__file__).resolve().parents[2]
GEO = BASE / "datos/geometria"
CARGAS_OUT = BASE / "datos/casos_analisis"
RES = BASE / "resultados" / "cargas_reales"
FIG = RES / "figuras"

KGF_A_KN = 0.00980665
TOL = 1e-6

# transformaciones VALIDADAS en la ronda de validacion fisica XREF (ver JSON).
TRANS_VALIDADA = {
    "P1": {"ox": 61.3, "oy": 58.0, "flip_y": False, "escala": 100.0,
           "insert": (2209.814, 4607.853)},
    "P2": {"ox": 893.23, "oy": 7884.92, "flip_y": True, "escala": 100.0,
           "insert": (8412.406, 978.926)},
    "P3": {"ox": 535.00, "oy": 4260.35, "flip_y": True, "escala": 100.0,
           "insert": (8543.585, -1576.398)},
}

NIVEL_ARCHIVO = {"P1": "1", "P2": "2", "P3": "3"}


def _p(pt):
    return (float(pt[0]), float(pt[1]))


def _poly(points):
    return Polygon([_p(p) for p in points])


def _dxf_700_a_modelo(cod: str, x: float, y: float) -> Tuple[float, float]:
    """Cadena verificada: estructural = 700 - insert; modelo = congelada(estructural)."""
    t = TRANS_VALIDADA[cod]
    insx, insy = t["insert"]
    sx, sy = x - insx, y - insy
    mx = (sx - t["ox"]) / t["escala"]
    my = (t["oy"] - sy) / t["escala"] if t["flip_y"] else (sy - t["oy"]) / t["escala"]
    return mx, my


def _poly_dxf700_a_modelo(cod: str, poly):
    """Cadena validada 700->modelo; devuelve Polygon/MultiPolygon o None si degenera.
    Admite Polygon y MultiPolygon (una region real puede tener varias partes o vacios,
    p. ej. la zona ``_USER`` diagonal grande de P3)."""
    if poly is None or poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        parts = [g for g in poly.geoms if g.geom_type == "Polygon"]
    elif poly.geom_type == "Polygon":
        parts = [poly]
    else:
        return None
    out = []
    for g in parts:
        coords = [_dxf_700_a_modelo(cod, x, y) for x, y in g.exterior.coords]
        if len(coords) < 4:
            continue
        interiors = [[_dxf_700_a_modelo(cod, x, y) for x, y in ir.coords]
                     for ir in g.interiors]
        try:
            p = Polygon(coords, interiors)
        except Exception:
            continue
        if p.is_valid and not p.is_empty and p.area > 1e-4:
            out.append(p)
    if not out:
        return None
    if len(out) == 1:
        return out[0]
    return MultiPolygon(out)


def _cargar_nivel(cod: str) -> dict:
    return json.loads((GEO / ("edificio_I_cielo_piso_%s_borrador.json" % NIVEL_ARCHIVO[cod]))
                      .read_text(encoding="utf-8"))


def _aberturas_shapely(data: dict):
    ab = {}
    for a in data.get("aberturas_globales", []) or []:
        if a.get("poligono"):
            ab[a["id"]] = _poly(a["poligono"])
    return ab


def _net_domain(losa, ab_global):
    """Dominio neto = losa menos sus aberturas referenciadas. Junta de edificios NO se
    descuenta aqui: los poligonos congelados ya la respetan (interfaz entre edificios),
    y no se convierten interfaces de ancho desconocido en huecos."""
    sp = _poly(losa["poligono_exterior"])
    neto = sp
    for aid in losa.get("aberturas", []) or []:
        key = aid if isinstance(aid, str) else aid.get("id")
        ap = ab_global.get(key)
        if ap is not None and not ap.is_empty and sp.is_valid:
            try:
                neto = neto.difference(ap)
            except Exception:
                pass
    return neto


def _leyenda_cad_evidencia(regiones_dxf) -> dict:
    """Devuelve, por planta, la lista de muestras de leyenda detectadas por EVIDENCIA CAD
    (bbox ~1611x237) con su posicion, para documentar que la exclusion no es por area."""
    out = {}
    for cod, regs in regiones_dxf.items():
        muestras = []
        for r in regs:
            o = r["outline"]
            if X._es_muestra_leyenda(o):
                minx, miny, maxx, maxy = o.bounds
                muestras.append({
                    "patron": r["patron"],
                    "bbox_ud": [round(minx, 1), round(miny, 1), round(maxx, 1), round(maxy, 1)],
                    "ancho_x_alto_ud": [round(maxx - minx, 1), round(maxy - miny, 1)],
                })
        out[cod] = muestras
    return out


def correlacion_nivel(cod: str) -> dict:
    """Correlacion de cargas de un nivel validado (P1/P2/P3) usando la cadena XREF."""
    data = _cargar_nivel(cod)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    ab_global = _aberturas_shapely(data)

    dxf = X.extraer_dxf()
    corr = X.correlacion_pattern_combo(dxf)
    # correspondencia patron->(PM,SC) por NIVEL, construida por emparejamiento por COLUMNA
    # de los bloques "CARGAS DE DISEÑO" con su muestra fisica (EVIDENCIA CAD de leyenda).
    # NO se usa la lista `regiones` de correlacion_pattern_combo porque esa separa por AREA
    # (_separar_swatches) y descartaria regiones reales cuyo area es cercana a la de la muestra
    # (p. ej. P1 GRAVEL 36.7 m2 y BRASS 29.5 m2 = zona 2800). Aqui se filtran las muestras
    # SOLO por bbox de leyenda (_es_muestra_leyenda), no por area.
    patron_combo = corr[cod]["patron_combo"]

    # regiones de carga (no muestras de leyenda) -> en MODELO (m)
    regiones = []
    for r in dxf["regiones"][cod]:
        if X._es_muestra_leyenda(r["outline"]):
            continue                    # leyenda: exclusion por evidencia CAD (bbox)
        if r["outline"].geom_type != "Polygon" or r["outline"].is_empty:
            continue
        pol_m = _poly_dxf700_a_modelo(cod, r["outline"])
        if pol_m is None:
            continue
        combo = patron_combo.get(r["patron"])
        if combo is not None:
            pm, sc, estado = combo["PM_ADIC"], combo["SC"], "trama_correlacionada"
        else:
            pm, sc, estado = None, None, "por_confirmar_trama"
        regiones.append({
            "patron": r["patron"],
            "combo": {"PM_ADIC_kgf_m2": pm, "SC_kgf_m2": sc},
            "estado_trama": estado,
            "area_modelo_m2": round(pol_m.area, 4),
            "carga_si": pm is not None,
            "poly": pol_m,
        })

    # ---- por losa ----
    losa_rows = []
    total_neta = 0.0; total_clas = 0.0; total_porconf = 0.0; total_sin = 0.0
    for lo in losas:
        neto = _net_domain(lo, ab_global)
        bruta = _poly(lo["poligono_exterior"]).area
        neta = neto.area
        total_neta += neta

        por_cat = {}            # (PM,SC) -> {area, regiones}
        por_confirmar = 0.0
        region_hits = []
        for rg in regiones:
            if rg["poly"].is_empty or not rg["poly"].is_valid:
                continue
            try:
                inter = neto.intersection(rg["poly"])
            except Exception:
                continue
            a = inter.area if not inter.is_empty else 0.0
            if a <= TOL:
                continue
            region_hits.append({"id": rg["patron"], "area_m2": round(a, 6),
                                "carga_si": rg["carga_si"]})
            if rg["carga_si"]:
                k = (rg["combo"]["PM_ADIC_kgf_m2"], rg["combo"]["SC_kgf_m2"])
                e = por_cat.get(k, {"area_m2": 0.0, "regiones": []})
                e["area_m2"] += a
                e["regiones"].append(rg["patron"])
                por_cat[k] = e
            else:
                por_confirmar += a

        # solape dentro de la misma losa (cobertura sumada vs union efectiva)
        union_area = 0.0
        try:
            cuts = [rg["poly"].intersection(neto) for rg in regiones if not rg["poly"].is_empty]
            cuts = [c for c in cuts if not c.is_empty]
            if cuts:
                union_area = unary_union(cuts).area
        except Exception:
            union_area = sum(rh["area_m2"] for rh in region_hits)
        cobertura_total = sum(rh["area_m2"] for rh in region_hits)
        solapes = max(cobertura_total - min(union_area, neta), 0.0)
        sin_clasificar = max(neta - union_area, 0.0)
        total_clas += sum(e["area_m2"] for e in por_cat.values())
        total_porconf += por_confirmar
        total_sin += sin_clasificar

        losa_rows.append({
            "id": lo["id"],
            "espesor_m": lo.get("espesor"),
            "area_bruta_m2": round(bruta, 4),
            "area_neta_m2": round(neta, 4),
            "area_por_categoria_m2": {
                "%d/%d" % k: round(e["area_m2"], 4)
                for k, e in sorted(por_cat.items())},
            "categorias": [
                {"PM_ADIC_kgf_m2": k[0], "SC_kgf_m2": k[1],
                 "area_m2": round(e["area_m2"], 4),
                 "regiones_fuente": e["regiones"],
                 "PM_ADIC_carga_kgf": round(e["area_m2"] * k[0], 2),
                 "SC_carga_kgf": round(e["area_m2"] * k[1], 2),
                 "PM_ADIC_carga_kN_provisional": round(e["area_m2"] * k[0] * KGF_A_KN, 4),
                 "SC_carga_kN_provisional": round(e["area_m2"] * k[1] * KGF_A_KN, 4)}
                for k, e in sorted(por_cat.items())],
            "area_por_confirmar_m2": round(por_confirmar, 4),
            "area_sin_clasificar_m2": round(sin_clasificar, 4),
            "solape_regiones_m2": round(solapes, 4),
            "region_hits": region_hits,
        })

    suma_neta = round(sum(r["area_neta_m2"] for r in losa_rows), 4)
    return {
        "nivel": cod,
        "transformacion": "XREF_validada (700 - insert, luego congelada)",
        "n_regiones_carga": len(regiones),
        "region_resumen": [
            {"patron": r["patron"], "combo": r["combo"], "estado_trama": r["estado_trama"],
             "area_modelo_m2": r["area_modelo_m2"]} for r in regiones],
        "losas": losa_rows,
        "control": {
            "suma_neta_losas_m2": suma_neta,
            "area_clasificada_m2": round(total_clas, 4),
            "area_por_confirmar_m2": round(total_porconf, 4),
            "area_sin_clasificar_m2": round(total_sin, 4),
            "pct_clasificado": round(100 * total_clas / max(suma_neta, TOL), 2),
            "pct_por_confirmar": round(100 * total_porconf / max(suma_neta, TOL), 2),
            "pct_sin_clasificar": round(100 * total_sin / max(suma_neta, TOL), 2),
        },
    }


def _puntuales(cod: str) -> list:
    """Marcadores puntuales del DXF 700 para P2/P3, colocados con la cadena XREF validada.
    Se registra posicion y elemento candidato (losa contenedora); NO se fuerza receptor."""
    dxf = X.extraer_dxf()
    data = _cargar_nivel(cod)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    ab_global = _aberturas_shapely(data)
    dominios = {lo["id"]: _net_domain(lo, ab_global) for lo in losas}
    out = []
    for m in dxf["puntual_marcadores"]:
        if m["planta"] != cod:
            continue
        mx, my = _dxf_700_a_modelo(cod, m["cx"], m["cy"])
        # losa contenedora / elemento candidato
        cont = None
        for lid, dom in dominios.items():
            if dom.buffer(0.05).contains(Point(mx, my)):
                cont = lid
                break
        out.append({
            "nivel": cod,
            "posicion_modelo_m": [round(mx, 3), round(my, 3)],
            "marcador_700": [round(m["cx"], 1), round(m["cy"], 1)],
            "losa_contenedora_candidata": cont,
            "elemento_receptor": "por_definir",
            "mecanismo_transferencia": "por_definir",
        })
    return out


def main() -> dict:
    NIVELES = ["P1", "P2", "P3"]
    dxf = X.extraer_dxf()
    corr_combo = X.correlacion_pattern_combo(dxf)
    por_nivel = {}
    for cod in NIVELES:
        por_nivel[cod] = correlacion_nivel(cod)
    muestras_leyenda = _leyenda_cad_evidencia(dxf["regiones"])

    unidades = P11.evidencias_unidades()
    zona2800 = P11.zona_2800()
    puntuales_p2 = _puntuales("P2")
    puntuales_p3 = _puntuales("P3")

    payload = {
        "titulo": "Correlacion espacial de cargas (pagina 11) - P1/P2/P3 con transformacion XREF validada",
        "estado": "correlacion_geoespacial_emitida",
        "alcanza": "Transformacion geometrica validada (P1/P2/P3). NO ejecuta areas tributarias, "
                   "ni reacciones, ni cargas sobre receptores.",
        "cadena_transformacion": {
            "p_estructural": "p_700 - insercion_xref",
            "p_modelo": "transformacion_congelada(p_estructural)",
            "escala_xref": 1.0, "rotacion_xref_deg": 0.0, "reflexion_xref": False,
        },
        "transformaciones_por_nivel": {cod: TRANS_VALIDADA[cod] for cod in NIVELES},
        "nota_localidad": ("La correspondencia trama->(PM_ADIC,SC) y la posicion de las muestras "
                           "de leyenda se leen por PLANTA; no hay diccionario global por nombre "
                           "de patron. Para `_USER` se valida por muestra de leyenda de cada nivel."),
        "leyenda_muestras_por_evidencia_cad": muestras_leyenda,
        "unidades": unidades,
        "zona_2800": zona2800,
        "por_nivel": por_nivel,
        "cargas_puntuales": {"P2": puntuales_p2, "P3": puntuales_p3},
    }

    CARGAS_OUT.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    (CARGAS_OUT / "correlacion_cargas_validada_P123.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    _figura_superposicion(por_nivel, dxf)
    _csv_por_losa(por_nivel, puntuales_p2 + puntuales_p3)
    _md_informe(payload)

    return payload


# ============================================================================== figura
def _figura_superposicion(por_nivel: dict, dxf: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import Polygon, box

    fig, axes = plt.subplots(1, 3, figsize=(24, 8))
    for ax, cod in zip(axes, ["P1", "P2", "P3"]):
        data = _cargar_nivel(cod)
        losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
        ab = _aberturas_shapely(data)
        for lo in losas:
            neto = _net_domain(lo, ab)
            xs, ys = neto.exterior.xy
            ax.plot(xs, ys, color="#1f77b4", lw=1.2)
            ax.fill(xs, ys, color="#1f77b4", alpha=0.10)
            for intr in getattr(neto, "interiors", []) or []:
                xs, ys = intr.xy
                ax.fill(xs, ys, color="white")
        cmap = plt.get_cmap("rainbow")
        # plot regiones (reconvertidas con la cadena XREF validada)
        for i, r in enumerate([x for x in dxf["regiones"][cod]
                               if not X._es_muestra_leyenda(x["outline"])
                               and x["outline"].geom_type in ("Polygon", "MultiPolygon")]):
            p = _poly_dxf700_a_modelo(cod, r["outline"])
            if p is None:
                continue
            col = cmap(i / max(16, 1))
            for part in ([p] if p.geom_type == "Polygon" else list(p.geoms)):
                xs, ys = part.exterior.xy
                ax.plot(xs, ys, color=col, lw=0.7, ls="--")
                ax.fill(xs, ys, color=col, alpha=0.15)
            ax.text(np.mean([c[0] for c in (p.exterior if p.geom_type == "Polygon" else p.geoms[0].exterior).coords]),
                    np.mean([c[1] for c in (p.exterior if p.geom_type == "Polygon" else p.geoms[0].exterior).coords]),
                    r["patron"], fontsize=6, ha="center", va="center")
        ax.set_aspect("equal")
        ax.set_title("%s - regiones DXF700 (validadas por XREF) vs losas netas (azul)" % cod)
        ax.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(FIG / "correlacion_cargas_P123.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


# ============================================================================== csv / md
def _csv_por_losa(por_nivel: dict, puntuales: list) -> None:
    p = RES / "correlacion_cargas_validada_P123_por_losa.csv"
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["nivel", "losa", "area_bruta_m2", "area_neta_m2", "area_por_confirmar_m2",
                    "area_sin_clasificar_m2", "solape_m2", "PM_ADIC_kgf_m2", "SC_kgf_m2",
                    "area_categoria_m2", "regiones_fuente", "trama_estado"])
        for cod, v in por_nivel.items():
            for lo in v["losas"]:
                if lo["categorias"]:
                    base_area = [lo["id"], lo["area_bruta_m2"], lo["area_neta_m2"],
                                 lo["area_por_confirmar_m2"], lo["area_sin_clasificar_m2"],
                                 lo["solape_regiones_m2"]]
                    for cat in lo["categorias"]:
                        w.writerow([cod, lo["id"], lo["area_bruta_m2"], lo["area_neta_m2"],
                                    lo["area_por_confirmar_m2"], lo["area_sin_clasificar_m2"],
                                    lo["solape_regiones_m2"],
                                    cat["PM_ADIC_kgf_m2"], cat["SC_kgf_m2"],
                                    cat["area_m2"], "|".join(cat["regiones_fuente"]), ""])
                else:
                    w.writerow([cod, lo["id"], lo["area_bruta_m2"], lo["area_neta_m2"],
                                lo["area_por_confirmar_m2"], lo["area_sin_clasificar_m2"],
                                lo["solape_regiones_m2"], "", "", "", "", "sin_categoria"])
        for pt in puntuales:
            w.writerow([pt["nivel"], pt["posicion_modelo_m"], "", "", "", "", "", "", "",
                        "", pt["losa_contenedora_candidata"] or "", "puntual_marcador"])


def _md_informe(payload: dict) -> None:
    lines = [
        "# Correlacion espacial de cargas - P1/P2/P3 (XREF validada)",
        "",
        payload["titulo"],
        "",
        "> **Solo lectura / correlacion geoespacial.** No asigna cargas sobre receptores ni "
        "ejecuta areas tributarias. La correspondencia trama->carga y las muestras de leyenda "
        "se leen por PLANTA (no global por nombre de patron).",
        "",
        "## Cadena transformacion (validada)",
        "",
        "- `p_estructural = p_700 - insercion_xref`  (XREF escala 1, rot 0, sin reflejo)",
        "- `p_modelo = transformacion_congelada(p_estructural)` (sistema_coordenadas)",
        "",
        "## Tabla por nivel (porcentaje clasificado / pendiente)",
        "",
        "| Nivel | n regiones | area neta (m2) | clasificado | por_confirmar | sin_clasificar | solape (m2) |",
        "|-------|-----------|----------------|-------------|---------------|----------------|-------------|",
    ]
    for cod, v in payload["por_nivel"].items():
        c = v["control"]
        lines.append("| %s | %s | %s | %s%% | %s%% | %s%% | - |" % (
            cod, v["n_regiones_carga"], c["suma_neta_losas_m2"],
            c["pct_clasificado"], c["pct_por_confirmar"], c["pct_sin_clasificar"]))
    lines += [
        "",
        "## Zona excepcional 2800 (P1, provisional)",
        "",
        "- " + payload["zona_2800"]["nota"],
        "",
        "## Unidades (provisional)",
        "",
    ]
    for u in payload["unidades"].get("evidencia_interna_buscada", [])[:4]:
        lines.append("- " + u)
    lines += [
        "",
        "## Cargas puntuales P2/P3 (posicion con XREF validada; receptor no forzado)",
        "",
        "| Nivel | posicion (m) | losa candidata | receptor |",
        "|-------|--------------|----------------|----------|",
    ]
    for cod2 in ["P2", "P3"]:
        for pt in payload["cargas_puntuales"][cod2]:
            lines.append("| %s | (%s, %s) | %s | %s |" % (
                cod2, pt["posicion_modelo_m"][0], pt["posicion_modelo_m"][1],
                pt["losa_contenedora_candidata"], pt["elemento_receptor"]))
    lines += [
        "",
        "## Regla de exclusion de leyenda",
        "",
        "Las muestras `CARGAS DE DISEÑO` se excluyen por EVIDENCIA CAD (bbox compacto ~1611x237 "
        "uds). Ver `leyenda_muestras_por_evidencia_cad` en el JSON.",
        "",
    ]
    (RES / "informe_correlacion_validada_P123.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
    print("OK  datos/casos_analisis/correlacion_cargas_validada_P123.json")
    print("OK  resultados/cargas_reales/figuras/correlacion_cargas_P123.png")
    print("OK  resultados/cargas_reales/correlacion_cargas_validada_P123_por_losa.csv")
    print("OK  resultados/cargas_reales/informe_correlacion_validada_P123.md")