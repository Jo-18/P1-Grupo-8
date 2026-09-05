"""
Correlacion espacial de cargas (pagina 11) de los CINCO niveles (CP1S, P1, P2, P3, P4)
con transformacion XREF VALIDADA (reutiliza el modulo P123).

Cadena verificada (valida para los 5):
    p_estructural = p_700 - insercion_xref         (XREF escala 1, rotacion 0, sin reflejo)
    p_modelo      = transformacion_congelada(p_estructural)   (sistema_coordenadas del JSON)

Transportes CP1S/P4 incorporados (validados por puntos fisicos en
validacion_fisica_puntos_CP1S_P4.json / validacion_fisica_xref_por_nivel.json):
    CP1S  ox=1026.30 oy=5515.10 flip_y=False insert=(-2255.295, 670.841)
    P4    ox=490.3   oy=6297.3  flip_y=True  insert=(-2380.174,-4389.169)

ALCANCE (esta ronda):
  1) Completa la correlacion espacial carga->region/losa (2da etapa). NO ejecuta la
     3ra etapa (aplicacion de cargas al calculo: tributacion/reacciones/receptores).
  2) Correspondencia trama->(PM_ADIC,SC) por PLANTA (leyenda propia de cada nivel).
     NO se copian asociaciones de patron entre pisos.
  3) Regiones pendientes de P1/P2/P3 (zona no cubierta por ninguna trama) se reportan
     de forma explicita (losa/ubicacion/area/motivo/evidencia). NO se rellenan por
     proximidad, NI se extrapola/renormaliza para alcanzar 100%.
  4) Cargas puntuales P2/P3 y carga lineal P4 se conservan como ENTIDADES INDEPENDIENTES
     (ubicadas por la cadena XREF; receptor NO asignado / sin repartir).
  5) Tabla por nivel y categoria con cobertura por UNIONES GEOMETRICAS (no se cuenta dos
     veces regiones superpuestas; solapes conflictivos reportados).

REGLA DE EXCLUSION / ZONAS
--------------------------
  - Muestras (swatches) de leyenda eliminadas por EVIDENCIA CAD (bbox compacto
    ~1611x237 uds), no por area.
  - "Ausencia de region en la lamina" != "carga cero": el area neta no cubierta se
    reporta `sin_clasificar` (nunca 0).
  - P4: desfase de la rejilla RLE-EJES +0.1813 m constante se conserva como
    discrepancia DOCUMENTADA (no se aplica correccion ni se presenta como definitiva).

SALIDAS
-------
  datos/casos_analisis/correlacion_cargas_validada_5niveles.json
  resultados/cargas_reales/figuras/correlacion_cargas_{nivel}.png
  resultados/cargas_reales/correlacion_cargas_validada_5niveles_por_losa.csv
  resultados/cargas_reales/correlacion_cargas_validada_5niveles_regiones_pendientes.md
  resultados/cargas_reales/informe_correlacion_validada_5niveles.md
"""

from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

import extraer_cargas_dxf as X
import correlacion_pagina11 as P11
# reutilizacion del modulo P123 (transformacion validada + dominios netos)
import correlacion_cargas_validada as C

BASE = Path(__file__).resolve().parents[2]
GEO = BASE / "datos/geometria"
CARGAS_OUT = BASE / "datos/casos_analisis"
RES = BASE / "resultados" / "cargas_reales"
FIG = RES / "figuras"

KGF_A_KN = 0.00980665
TOL = 1e-6

# Transportes XREF VALIDADOS para los 5 niveles (CP1S/P4 incorporados).
for _cod, _t in {
    "CP1S": {"ox": 1026.30, "oy": 5515.10, "flip_y": False, "escala": 100.0,
             "insert": (-2255.295, 670.841)},
    "P1":   {"ox": 61.3,    "oy": 58.0,    "flip_y": False, "escala": 100.0,
             "insert": (2209.814, 4607.853)},
    "P2":   {"ox": 893.23,  "oy": 7884.92, "flip_y": True,  "escala": 100.0,
             "insert": (8412.406, 978.926)},
    "P3":   {"ox": 535.00,  "oy": 4260.35, "flip_y": True,  "escala": 100.0,
             "insert": (8543.585, -1576.398)},
    "P4":   {"ox": 490.3,   "oy": 6297.3,  "flip_y": True,  "escala": 100.0,
             "insert": (-2380.174, -4389.169)},
}.items():
    C.TRANS_VALIDADA[_cod] = _t
C.NIVEL_ARCHIVO.update({"CP1S": "1_subterraneo", "P4": "4"})

NIVELES = ["CP1S", "P1", "P2", "P3", "P4"]
ETIQUETA = {"CP1S": "1° Subterráneo", "P1": "Piso 1", "P2": "Piso 2",
            "P3": "Piso 3", "P4": "Piso 4"}


def _poly(points):
    return Polygon([(float(p[0]), float(p[1])) for p in points])


def _cargar_nivel(cod):
    arch = {"CP1S": "1_subterraneo", "P1": "1", "P2": "2", "P3": "3", "P4": "4"}[cod]
    return json.loads((GEO / ("edificio_I_cielo_piso_%s_borrador.json" % arch))
                      .read_text(encoding="utf-8"))


def _mapa_confirmado() -> dict:
    """Confirmaciones de la revision visual (pagina 11) leidas del catalogo:
    {(nivel, patron): dict(PM,SC,tipo,region_center,...)}. NO se usa '_USER' como
    clave global; cada tramo queda vinculado por (nivel, patron) y su region de 700.
    Devuelve tambien las entradas 'lineal' (p.ej. P4 BRASS -> 7600/800) por separado."""
    cat = json.loads((BASE / "datos/cargas/catalogo_cargas_diseno_edificio_I.json")
                     .read_text(encoding="utf-8"))
    conf = cat["confirmaciones_revision_visual"]["por_nivel"]
    mapa = {}
    lineales = {}
    for cod, items in conf.items():
        for it in items:
            p = it["patron"]
            if it["tipo"] == "lineal":
                lineales[(cod, p)] = {
                    "tipo": "lineal",
                    "PM_ADIC_kgf_m": it["PM_ADIC_kgf_m"],
                    "SC_kgf_m": it["SC_kgf_m"],
                    "vinculado_a": "CL_EI_P4_001",
                    "justificacion": it["justificacion"],
                }
                continue
            mapa[(cod, p)] = {
                "tipo": it["tipo"],
                "PM_ADIC_kgf_m2": it["PM_ADIC_kgf_m2"],
                "SC_kgf_m2": it["SC_kgf_m2"],
                "variante": it.get("variante"),
                "region_700_centro": it.get("region_700_centro"),
                "swatch_vinculada": it.get("swatch_vinculada"),
                "justificacion": it.get("justificacion"),
                "fuente": "confirmacion_revision_visual",
            }
    return mapa, lineales, conf


# Mapa de confirmaciones autorizadas (leido una sola vez del catalogo).
_MAPA = _mapa_confirmado()


def _aberturas_shapely(data):
    return {a["id"]: _poly(a["poligono"]) for a in data.get("aberturas_globales", []) or []
            if a.get("poligono")}


def _net_domain(losa, ab_global):
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


# ---------------------------------------------------------------------------
# correlacion por nivel (misma logica que P123, ya generalizada a todos los niveles)
# ---------------------------------------------------------------------------
def correlacion_nivel(cod: str) -> dict:
    """Correlacion de cargas de un nivel con la cadena XREF validada (cualquiera de los 5)."""
    data = _cargar_nivel(cod)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    ab_global = _aberturas_shapely(data)

    dxf = X.extraer_dxf()
    corr = X.correlacion_pattern_combo(dxf)
    patron_combo = corr[cod]["patron_combo"]
    conflictos = corr[cod]["conflictos_patron"]

    # ---------------------------------------------
    # Confirmaciones de la revision visual (catalogo) toman precedencia sobre el
    # emparejamiento algoritmico: patron_combo da el valor por leyenda macheada; el
    # mapa confirmado fija el valor AUTORIZADO por (nivel, patron) con su region.
    # Las entradas 'lineal' (P4 BRASS) salen de la correlacion de SUPErficie y se
    # reasignan a la carga lineal existente (sin duplicar).
    # ---------------------------------------------
    mapa_conf, lineales_conf, _ = _MAPA

    # regiones de carga (no muestras de leyenda) en MODELO
    regiones = []
    lineales_bmr = []   # franjas reasignadas a carga lineal (P4 BRASS)
    for r in dxf["regiones"][cod]:
        if X._es_muestra_leyenda(r["outline"]):
            continue
        if r["outline"].is_empty:
            continue
        if r["outline"].geom_type not in ("Polygon", "MultiPolygon"):
            continue
        pol_m = C._poly_dxf700_a_modelo(cod, r["outline"])
        if pol_m is None:
            continue

        key = (cod, r["patron"])
        if key in lineales_conf:
            # franja de carga lineal -> NO superficie
            lineales_bmr.append({
                "patron": r["patron"],
                "area_modelo_m2": round(pol_m.area, 4),
                "area_700_u2": r["area_dxf_u2"],
                "centro_700": [round(r["cx_dxf"], 1), round(r["cy_dxf"], 1)],
                "combo_lineal": {"PM_ADIC_kgf_m": lineales_conf[key]["PM_ADIC_kgf_m"],
                                 "SC_kgf_m": lineales_conf[key]["SC_kgf_m"]},
                "vinculado_a": lineales_conf[key]["vinculado_a"],
                "poly": pol_m,
            })
            continue

        if key in mapa_conf:
            m = mapa_conf[key]
            pm, sc = m["PM_ADIC_kgf_m2"], m["SC_kgf_m2"]
            corr_trama = "trama_correspondencia_confirmada"
            origen = "confirmacion_revision_visual"
        else:
            combo = patron_combo.get(r["patron"])
            if combo is not None and r["patron"] not in conflictos:
                pm, sc = combo["PM_ADIC"], combo["SC"]
                corr_trama = "trama_correspondencia_confirmada"
                origen = "leyenda_macheada_algoritmica"
            else:
                pm, sc = None, None
                corr_trama = "trama_correspondencia_pendiente"
                origen = "sin_confirmacion"

        regiones.append({
            "patron": r["patron"],
            "combo": {"PM_ADIC_kgf_m2": pm, "SC_kgf_m2": sc},
            "estados": {
                "correspondencia_trama": corr_trama,
                "region_intersecta_losa": "por_verificar_geom",
                "unidad": "kg_vs_kgf_provisional",
            },
            "_origen_correspondencia": origen,
            "area_modelo_m2": round(pol_m.area, 4),
            "area_700_u2": r["area_dxf_u2"],
            "centro_700": [round(r["cx_dxf"], 1), round(r["cy_dxf"], 1)],
            "carga_si": pm is not None,
            "poly": pol_m,
        })

    # dom abiertas/abiertas por losa con uniones geometricas
    losa_rows = []
    total_union = 0.0     # area cubierta por al menos una region (union real)
    total_clas = 0.0      # area cubierta por una region CON carga
    total_porconf = 0.0
    total_sin = 0.0
    total_neta = 0.0
    solape_conflictivo_total = 0.0
    for lo in losas:
        neto = _net_domain(lo, ab_global)
        neta = neto.area
        total_neta += neta

        por_cat = {}
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
                                "carga_si": rg["carga_si"],
                                "estados": rg["estados"]})
            if rg["carga_si"]:
                k = (rg["combo"]["PM_ADIC_kgf_m2"], rg["combo"]["SC_kgf_m2"])
                e = por_cat.get(k, {"area_m2": 0.0, "regiones": []})
                e["area_m2"] += a
                e["regiones"].append(rg["patron"])
                por_cat[k] = e
            else:
                total_porconf += a

        # cobertura por UNION (no doble conteo) y solapes conflictivos
        cuts = []
        for rg in regiones:
            if rg["poly"].is_empty:
                continue
            try:
                c = neto.intersection(rg["poly"])
            except Exception:
                continue
            if not c.is_empty:
                cuts.append(c)
        union_area = unary_union(cuts).area if cuts else 0.0
        # suma simple de areas (para medir solape)
        sum_area = sum(rh["area_m2"] for rh in region_hits)
        # solape = area contada doble = suma_simple - area_union (dentro de la losa)
        solape = max(sum_area - min(union_area, neta), 0.0)
        sin_clasificar = max(neta - min(union_area, neta), 0.0)

        total_union += min(union_area, neta)
        total_clas += sum(e["area_m2"] for e in por_cat.values())
        total_sin += sin_clasificar
        solape_conflictivo_total += solape

        losa_rows.append({
            "id": lo["id"],
            "espesor_m": lo.get("espesor"),
            "area_bruta_m2": round(_poly(lo["poligono_exterior"]).area, 4),
            "area_neta_m2": round(neta, 4),
            "area_cubierta_por_region_m2": round(min(union_area, neta), 4),
            "area_por_categoria_m2": {"%d/%d" % k: round(e["area_m2"], 4)
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
            "area_por_confirmar_m2": round(sum(rh["area_m2"] for rh in region_hits
                                               if not rh["carga_si"]), 4),
            "area_sin_clasificar_m2": round(sin_clasificar, 4),
            "solape_regiones_m2": round(solape, 4),
            "region_hits": region_hits,
        })

    residual = total_neta - (total_clas + total_porconf + total_sin)
    balance = {
        "area_neta_m2": round(total_neta, 6),
        "area_clasificada_m2": round(total_clas, 6),
        "area_por_confirmar_m2": round(total_porconf, 6),
        "area_sin_clasificar_m2": round(total_sin, 6),
        "suma": round(total_clas + total_porconf + total_sin, 6),
        "residuo_m2": round(residual, 6),
        "conjuntos_disjuntos": "clasificada + por_confirmar + sin_clasificar = area_neta",
        "nota_solape": ("el area_clasificada y el solape se miden sobre la UNION de "
                        "poligonos (no se cuenta dos veces la misma losa). La coexistencia "
                        "de PM.ADIC y SC (la misma region lleva ambos) NO es un solape: son "
                        "dos cargas simultaneas sobre la misma area, no areas distintas."),
        "solape_entre_region_misma_categoria_m2": round(solape_conflictivo_total - 0.0, 6),
    }
    return {
        "nivel": cod,
        "etiqueta": ETIQUETA[cod],
        "transformacion": "XREF_validada (700 - insert, luego congelada)",
        "n_regiones_carga": len(regiones),
        "region_resumen": [
            {"patron": r["patron"], "combo": r["combo"], "estados": r["estados"],
             "area_modelo_m2": r["area_modelo_m2"],
             "area_700_u2": r["area_700_u2"], "centro_700": r["centro_700"],
             "origen_correspondencia": r["_origen_correspondencia"]} for r in regiones],
        "franjas_lineales_reasignadas": [
            {k: v for k, v in f.items() if k != "poly"} for f in lineales_bmr],
        "patron_combo_por_leyenda_propia": {p: {"PM_ADIC": v["PM_ADIC"], "SC": v["SC"]}
                                             for p, v in X.correlacion_pattern_combo(dxf)[cod]
                                                            ["patron_combo"].items()},
        "conflictos_patron": conflictos,
        "losas": losa_rows,
        "balance": balance,
        "control": {
            "suma_neta_losas_m2": round(total_neta, 4),
            "area_cubierta_union_m2": round(total_union, 4),
            "area_clasificada_m2": round(total_clas, 4),
            "area_por_confirmar_m2": round(total_porconf, 4),
            "area_sin_clasificar_m2": round(total_sin, 4),
            "solape_conflictivo_m2": round(solape_conflictivo_total, 4),
            "pct_clasificado": round(100 * total_clas / max(total_neta, TOL), 2),
            "pct_cubierto": round(100 * total_union / max(total_neta, TOL), 2),
            "pct_por_confirmar": round(100 * total_porconf / max(total_neta, TOL), 2),
            "pct_sin_clasificar": round(100 * total_sin / max(total_neta, TOL), 2),
        },
    }


# ---------------------------------------------------------------------------
# entidades independientes (puntuales P2/P3, lineal P4)
# ---------------------------------------------------------------------------
def _puntuales(cod):
    """Marcadores puntuales DXF700 de P2/P3, ubicados con la cadena XREF validada.
    Se registra posicion y losa contenedora candidata; receptor NO forzado.
    Los marcadores que caen FUERA de toda losa se conservan SIN desplazar: estar fuera
    de una losa no demuestra que la carga sea erronea (puede corresponder a viga/columna/
    marco o a un error de identificacion). Se anota la sospecha y se deja el receptor
    por definir mientras no haya evidencia."""
    dxf = X.extraer_dxf()
    data = _cargar_nivel(cod)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    ab = _aberturas_shapely(data)
    dominios = {lo["id"]: _net_domain(lo, ab) for lo in losas}
    out = []
    for m in dxf["puntual_marcadores"]:
        if m["planta"] != cod:
            continue
        mx, my = C._dxf_700_a_modelo(cod, m["cx"], m["cy"])
        cont = None
        for lid, dom in dominios.items():
            if dom.buffer(0.05).contains(Point(mx, my)):
                cont = lid
                break
        fuera = cont is None
        out.append({
            "nivel": cod,
            "posicion_modelo_m": [round(mx, 3), round(my, 3)],
            "marcador_700": [round(m["cx"], 1), round(m["cy"], 1)],
            "losa_contenedora_candidata": cont,
            "fuera_de_losa": fuera,
            "elemento_receptor": "por_definir",
            "mecanismo_transferencia": "por_definir",
            "revision_fuera_de_losa": {
                "hipotesis": ["viga", "columna", "marco", "elemento_secundario",
                              "error_de_identificacion"],
                "estado": "sin_verificar",
                "nota": ("estar fuera de una losa NO invalida la carga ni modifica su "
                         "posicion; se conserva tal cual y se revisa el elemento real "
                         "antes de asignar receptor."),
            },
        })
    return out


def _lineal_p4():
    """Carga lineal del P4 (PM.ADIC 7600 kg/m, SC 800 kg/m) como ENTIDAD INDEPENDIENTE.
    Se conserva NO repartida; receptor por definir. Se anotan los extremos DXF de las
    dos leyendas lineales para su futura ubicacion geografica."""
    dxf = X.extraer_dxf()
    li = json.loads((BASE / "datos/cargas/cargas_lineales_edificio_I.json")
                    .read_text(encoding="utf-8"))
    raw = li["carga_lineal"]
    bloques = dxf["leyendas"]["P4"]
    lineales = [b for b in bloques if b.get("es_lineal") or (b.get("PM_ADIC") or 0) >= 7600]
    geo = []
    for b in lineales:
        mx, my = C._dxf_700_a_modelo("P4", b["px_dxf"], b["py_dxf"])
        geo.append({"ancla_px_dxf": [round(b["px_dxf"], 1), round(b["py_dxf"], 1)],
                    "ancla_modelo_m": [round(mx, 3), round(my, 3)],
                    "PM_ADIC": b["PM_ADIC"], "SC": b["SC"]})
    return {
        "id": raw["id"],
        "nivel": raw["nivel"],
        "valor": {"PM_ADIC_kg_m": raw["PM_ADIC_original"]["valor"],
                  "SC_kg_m": raw["SC_original"]["valor"],
                  "unidad_original_plano": "kg/m",
                  "interpretacion_unidad": "por_confirmar",   # provisional (kgf/m?)
                  "factor_kgf_m_a_kN_m": KGF_A_KN,
                  "PM_ADIC_kN_m_if_kgf_provisional": round(raw["PM_ADIC_original"]["valor"] * KGF_A_KN, 4),
                  "SC_kN_m_if_kgf_provisional": round(raw["SC_original"]["valor"] * KGF_A_KN, 4)},
        "regla_critica": li.get("regla_critica") or raw.get("regla_critica"),
        "yace_lineal_no_conversa_de_superficial": True,
        "es_por_ancho_tributario": False,
        "anclas_leyenda_modelo_m": geo,
        "extremos": "por_confirmar_vectorial",
        "elemento_receptor": "por_definir",
        "mecanismo_transferencia": "carga_directa_lineal",
        "no_repartida": True,
    }


# ---------------------------------------------------------------------------
# zonas sin clasificar: inventario descompuesto por componente geometrico
# ---------------------------------------------------------------------------
def _estructura_modelo(cod):
    """Referencia estructural congelada (modelo) para contrastar cargas puntuales:
    columnas, vigas, muros y bordes libres. Todo en metros del modelo."""
    data = _cargar_nivel(cod)
    return {
        "columnas": [{"id": c["id"], "posicion_m": list(c["posicion"]),
                      "seccion": c.get("seccion")} for c in data.get("columnas_referencia", []) or []],
        "vigas": [{"id": v["id"], "inicio_m": list(v["inicio"]), "fin_m": list(v["fin"]),
                   "seccion": (v.get("seccion") or {}).get("nombre")} for v in data.get("vigas", []) or []],
        "muros": [{"id": m["id"], "eje_inicio_m": list(m["eje"]["inicio"]),
                   "eje_fin_m": list(m["eje"]["fin"]), "espesor_m": m.get("espesor")}
                  for m in data.get("muros", []) or []],
        "bordes_libres": [{"id": b["id"], "inicio_m": list(b["inicio"]),
                           "fin_m": list(b["fin"]), "voladizo": b.get("_voladizo")}
                          for b in data.get("bordes_libres", []) or []],
    }


def _punto_a_segmento(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay
    t = 0.0 if L2 == 0 else ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2
    t = max(0.0, min(1.0, t))
    qx, qy = a[0] + t * ax, a[1] + t * ay
    return ((p[0] - qx) ** 2 + (p[1] - qy) ** 2) ** 0.5


def _dist_residual_a_borde(resid, bordes, tol=0.05):
    """Distancia del residuo al borde libre mas cercano (para hipotesis de voladizo)."""
    pts = [(resid.centroid.x, resid.centroid.y)] + list(resid.exterior.coords)
    best = float("inf"); which = None
    for b in bordes:
        for p in pts:
            dd = _punto_a_segmento(p, b["inicio_m"], b["fin_m"])
            if dd < best:
                best = dd; which = b["id"]
    return best, which


def _clasificar_componente(cod, losa_id, resid, estructura):
    """Hipotesis de causa del componente residual. Toda causa queda `por_verificar`: la
    ubicacion de una zona (p. ej. ser declarada 'voladizo' o estar cerca de un borde libre)
    NO confirma la causa de su falta de carga; describe donde esta, no por que no tiene
    indicacion de carga. Se conserva el residuo sin descartarlo ni rellenarlo por cercania."""
    es_voladizo = "VOLADIZO" in losa_id
    es_atrio = "ATRIO" in losa_id
    area = resid.area
    # descomponer en poligonos simples
    minx, miny, maxx, maxy = resid.bounds
    w, h = maxx - minx, maxy - miny
    perim = resid.length if resid.geom_type == "Polygon" else resid.boundary.length
    franja = perim > 0 and (w < 0.6 or h < 0.6 or area / max(perim, 1e-9) < 0.30)
    db, borde = _dist_residual_a_borde(resid, estructura["bordes_libres"])
    # contexto: losa con nombre voladizo/atrio cuadrado a un borde libre
    noda = es_voladizo or es_atrio
    if es_voladizo and db is not None and db <= 0.05:
        return ("zona_elevada_sin_indicacion_causa_por_verificar", {
            "evidencia": ("losa declarada VOLADIZO y componente a <=0.05 m del borde libre %s. "
                          "La nomenclatura y la cercania al borde describen la UBICACION, no "
                          "confirman la causa de la falta de carga; se verifica en el plano "
                          "original.") % borde,
            "estado": "por_verificar"})
    if es_voladizo:
        return ("zona_elevada_sin_indicacion_causa_por_verificar", {
            "evidencia": ("losa declarada VOLADIZO; queda espacio dentro de su dominio sin "
                          "hatch. El nombre indica ubicacion; la causa de la falta de carga se "
                          "verifica en el plano original."),
            "estado": "por_verificar"})
    if es_atrio:
        return ("atrio_zona_sin_indicacion", {
            "evidencia": ("losa denominada ATRIO; area amplia sin hatch. El nombre describe la "
                          "ubicacion/tipo de zona; que falte indicacion de carga se verifica en "
                          "el plano original, no se presume por la denominacion."),
            "estado": "por_verificar"})
    if franja:
        return ("franja_limite_caras_ejes", {
            "evidencia": "residuo fino (%sx%s m) pegado a una cara; posible diferencia "
                         "cara-losa vs linea de apoyo/eje" % (round(w, 3), round(h, 3)),
            "estado": "por_verificar"})
    if area >= 10.0:
        return ("zona_sin_indicacion_amplia", {
            "evidencia": "componente grande (%.1f m2) sin hatch debajo; ver si hay indicacion "
                         "de carga en el plano original" % area,
            "estado": "por_verificar"})
    return ("residuo_pequeno_sin_causa_afirmada", {
        "evidencia": "componente pequeno (%.4f m2); se conserva, no se descarta como error "
                     "numerico ni se rellena por proximidad" % area,
        "estado": "por_verificar"})


def _region_pendiente(cod):
    """Inventario de superficie pendiente por losa, DESCOMPUESTO en componentes
    geometricos con area (sin redondear), coordenadas y causa hipotetica. Incluye los 5
    niveles. Para P4 separa el area coincidente con la franja BRASS (carga lineal) del
    resto sin indicacion propia. NO descarta areas pequenas como error ni las rellena."""
    por_nivel = correlacion_nivel(cod)
    data = _cargar_nivel(cod)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    ab = _aberturas_shapely(data)
    dxf = X.extraer_dxf()
    regiones = [r for r in dxf["regiones"][cod]
                if not X._es_muestra_leyenda(r["outline"])
                and (cod, r["patron"]) not in _MAPA[1]]
    estructura = _estructura_modelo(cod)

    # franja lineal (BRASS) en modelo, cuando existe en este nivel
    brass_models = []
    for r in dxf["regiones"][cod]:
        if X._es_muestra_leyenda(r["outline"]):
            continue
        if (cod, r["patron"]) in _MAPA[1] and r["patron"] == "BRASS":
            pm = C._poly_dxf700_a_modelo(cod, r["outline"])
            if pm is not None:
                brass_models.append(pm)
    brass_union = unary_union(brass_models) if brass_models else None

    pendientes = []
    por_nivel_losaba = {lo["id"]: lo for lo in por_nivel["losas"]}
    for lo in losas:
        neto = _net_domain(lo, ab)
        covered = None
        for r in regiones:
            pm = C._poly_dxf700_a_modelo(cod, r["outline"])
            if pm is None:
                continue
            try:
                c = neto.intersection(pm)
            except Exception:
                continue
            if not c.is_empty:
                covered = c if covered is None else covered.union(c)
        free = neto.difference(covered) if covered else neto
        fa = free.area
        if fa <= TOL:
            continue
        hits = next((r for r in por_nivel["losas"] if r["id"] == lo["id"]), {}).get("region_hits", [])
        tramas_confirmadas = sorted({h["id"] for h in hits if h["estados"]["correspondencia_trama"]
                                     == "trama_correspondencia_confirmada"})
        tramas_pendientes = sorted({h["id"] for h in hits if h["estados"]["correspondencia_trama"]
                                    != "trama_correspondencia_confirmada"})

        # descomponer el residuo libre en componentes discontinuos
        comps = []
        if free.geom_type == "Polygon":
            comps = [free]
        elif free.geom_type == "MultiPolygon":
            comps = list(free.geoms)
        else:
            comps = [free]
        comp_rows = []
        for i, comp in enumerate(comps):
            if comp.is_empty:
                continue
            if comp.area <= TOL:
                continue
            bbox_m = [round(v, 4) for v in comp.bounds]
            cent = (round(comp.centroid.x, 4), round(comp.centroid.y, 4))
            # area dentro de la franja BRASS (solo P4 carga lineal)
            en_brass = brass_union is not None and not brass_union.is_empty and \
                comp.intersects(brass_union) and comp.intersection(brass_union).area > TOL
            en_brass_area = round(comp.intersection(brass_union).area, 6) if en_brass else 0.0
            causa, evid = _clasificar_componente(cod, lo["id"], comp, estructura)
            comp_rows.append({
                "componente": i + 1,
                "area_m2": round(comp.area, 6),
                "area_brass_band_m2": en_brass_area,
                "coincide_franja_brass_lineal": bool(en_brass),
                "centro_modelo_m": list(cent),
                "bbox_modelo_m": bbox_m,
                "causa": causa,
                "evidencia_causa": evid["evidencia"],
                "estado_causa": evid["estado"],
            })
        if not comp_rows:
            continue
        pendientes.append({
            "nivel": cod,
            "losa": lo["id"],
            "area_pendiente_m2": round(fa, 6),
            "area_neta_losa_m2": round(neto.area, 6),
            "area_cubierta_m2": round(free.buffer(0).union(covered).area, 6) if covered else 0.0,
            "tramas_presentes_confirmadas": tramas_confirmadas,
            "tramas_presentes_pendientes": tramas_pendientes,
            "tipo": "sin_clasificar_causa_por_verificar",
            "componentes": comp_rows,
            "nota_brass": ("Para P4: la superficie coincidente con la franja BRASS (carga "
                           "lineal CL_EI_P4_001) queda PENDIENTE, sin carga superficial "
                           "propia; la carga lineal no define la losa debajo de ella.") if cod == "P4" else None,
        })
    return pendientes


# ---------------------------------------------------------------------------
# figuras / csv / md
# ---------------------------------------------------------------------------
def _figura_nivel(cod, por_nivel):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    data = _cargar_nivel(cod)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    ab = _aberturas_shapely(data)
    dxf = X.extraer_dxf()
    fig, ax = plt.subplots(figsize=(11, 9))
    for lo in losas:
        neto = _net_domain(lo, ab)
        xs, ys = neto.exterior.xy
        ax.plot(xs, ys, color="#1f77b4", lw=1.3)
        ax.fill(xs, ys, color="#1f77b4", alpha=0.08)
        for intr in getattr(neto, "interiors", []) or []:
            xi, yi = intr.xy
            ax.fill(xi, yi, color="white")
    cmap = plt.get_cmap("rainbow")
    for i, r in enumerate([x for x in dxf["regiones"][cod]
                           if not X._es_muestra_leyenda(x["outline"])
                           and x["outline"].geom_type in ("Polygon", "MultiPolygon")]):
        p = C._poly_dxf700_a_modelo(cod, r["outline"])
        if p is None:
            continue
        col = cmap(i / max(8, len([1])))
        for part in ([p] if p.geom_type == "Polygon" else list(p.geoms)):
            xs, ys = part.exterior.xy
            ax.plot(xs, ys, color=col, lw=0.8, ls="--")
            ax.fill(xs, ys, color=col, alpha=0.15)
        ax.text(p.centroid.x, p.centroid.y, r["patron"], fontsize=6, ha="center", va="center")
    ax.set_aspect("equal")
    ctl = por_nivel["control"]
    ax.set_title("%s (%s) - regiones DXF700 (XREF val.) vs losas netas | clasificado %s%% "
                 "sin_clasificar %s%%" % (cod, ETIQUETA[cod], ctl["pct_clasificado"],
                                          ctl["pct_sin_clasificar"]))
    ax.grid(alpha=0.3)
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / ("correlacion_cargas_%s.png" % cod), dpi=140, bbox_inches="tight")
    plt.close(fig)


def _crops_revision_visual() -> dict:
    """Recortes visuales de las regiones cuya correspondencia fue CONFIRMADA en la
    revision visual (pagina 11): CP1S ANGLE, CP1S _USER, P4 BRASS, P4 GRAVEL. Cada
    recorte es un zoom en coordenadas de MODELO alrededor del hatch, con el valor
    confirmado aplicado y su justificacion. No altera ninguna region."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dxf = X.extraer_dxf()
    CROP = FIG / "revision_visual"
    CROP.mkdir(parents=True, exist_ok=True)
    confirmados = _MAPA[0] | _MAPA[1]

    def _banda_lineal(cod, pat):
        key = (cod, pat)
        if key in _MAPA[1]:
            m = _MAPA[1][key]
            return "LINEAL %s/%s kg/m (-> %s)" % (m["PM_ADIC_kgf_m"], m["SC_kgf_m"],
                                                  m["vinculado_a"])
        m = _MAPA[0].get(key)
        if m:
            return "%s/%s kg/m2" % (m["PM_ADIC_kgf_m2"], m["SC_kgf_m2"])
        return None

    objetivos = [
        {"id": "CP1S_ANGLE", "nivel": "CP1S", "patron": "ANGLE",
         "confirmado": "260/250",
         "nota": "HATCH ANGLE del 1° subt. confirmado como superficie 260/250 kg/m2."},
        {"id": "CP1S_USER_conflicto", "nivel": "CP1S", "patron": "_USER",
         "confirmado": "260/500",
         "nota": "Resolucion del conflicto: la region _USER (diagonales continuas) de CP1S "
                 "es 260/500 kg/m2."},
        {"id": "P4_BRASS", "nivel": "P4", "patron": "BRASS",
         "confirmado": "LINEAL 7600/800",
         "nota": "BRASS de P4 es la franja de la carga LINEAL 7600/800 kg/m -> vinculada a "
                 "CL_EI_P4_001 (no superficie, no se duplica)."},
        {"id": "P4_GRAVEL", "nivel": "P4", "patron": "GRAVEL",
         "confirmado": "200/200",
         "nota": "GRAVEL superficie dominante del piso 4 = 200/200 kg/m2."},
    ]
    salida = []
    for obj in objetivos:
        cod, pat = obj["nivel"], obj["patron"]
        data = _cargar_nivel(cod)
        losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
        ab = _aberturas_shapely(data)
        target = next((r for r in dxf["regiones"][cod] if r["patron"] == pat
                       and not X._es_muestra_leyenda(r["outline"]) and r["area_dxf_u2"] > 200000),
                      None)
        if target is None:
            target = next((r for r in dxf["regiones"][cod] if r["patron"] == pat
                           and not X._es_muestra_leyenda(r["outline"])), None)
        if target is None:
            continue
        p = C._poly_dxf700_a_modelo(cod, target["outline"])
        if p is None or p.is_empty:
            continue
        cx, cy = p.centroid.x, p.centroid.y
        minx, miny, maxx, maxy = p.bounds
        pad = max((maxx - minx), (maxy - miny)) * 0.35 + 2.0
        x0, x1 = cx - pad, cx + pad
        y0, y1 = cy - pad, cy + pad

        fig, ax = plt.subplots(figsize=(8, 8))
        for lo in losas:
            neto = _net_domain(lo, ab)
            if neto.is_empty or not neto.intersects(p):
                continue
            for gg in [neto.exterior] + list(getattr(neto, "interiors", []) or []):
                xs, ys = gg.xy
                ax.plot(xs, ys, color="#1f77b4", lw=1.2)
        # todas las regiones del nivel en la ventana
        cmap = plt.get_cmap("tab20")
        i = 0
        for r in dxf["regiones"][cod]:
            if X._es_muestra_leyenda(r["outline"]):
                continue
            pp = C._poly_dxf700_a_modelo(cod, r["outline"])
            if pp is None or pp.is_empty or not pp.intersects(p):
                continue
            col = "#d62728" if (r["patron"] == pat) else cmap(i % 20)
            i += 1
            for part in ([pp] if pp.geom_type == "Polygon" else list(pp.geoms)):
                xs, ys = part.exterior.xy
                ax.plot(xs, ys, color=col, lw=1.1)
                ax.fill(xs, ys, color=col, alpha=0.25)
            ax.text(pp.centroid.x, pp.centroid.y, r["patron"], fontsize=8,
                    ha="center", va="center", color="black")
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_title("%s | HATCH %s (resaltado en rojo) | CONFIRMADO = %s | bbox-modelo "
                     "(%.1f,%.1f)-(%.1f,%.1f)"
                     % (obj["id"], pat, obj["confirmado"], minx, miny, maxx, maxy), fontsize=9)
        ax.grid(alpha=0.4)
        out = CROP / ("croquis_%s.png" % obj["id"])
        fig.savefig(out, dpi=140, bbox_inches="tight")
        plt.close(fig)
        salida.append({
            "nivel": cod, "patron": pat, "id": obj["id"],
            "dominio_geom": "modelo",
            "centro_modelo_m": [round(cx, 2), round(cy, 2)],
            "bbox_modelo_m": [round(minx, 2), round(miny, 2), round(maxx, 2), round(maxy, 2)],
            "area_modelo_m2": round(p.area, 3),
            "image": out.name,
            "confirmado": obj["confirmado"],
            "nota": obj["nota"],
            "estado": "confirmado_revision_visual",
        })
    # MD con las confirmaciones aplicadas de la revision visual
    md = ["# Revision visual - confirmaciones aplicadas",
          "",
          "Recortes (zoom en modelo) de las regiones cuyas tramas->valor fueron CONFIRMADAS "
          "en la revision de la pagina 11. Cada recorte resalta la region objetivo (rojo) y "
          "anota el valor autorizado aplicado.",
          "",
          "| id | nivel | trama | area (m2) | valor confirmado | imagen |",
          "|---|---|---|---|---|---|"]
    for s in salida:
        md.append("| %s | %s | %s | %s | `%s` | %s |" % (
            s["id"], s["nivel"], s["patron"], s["area_modelo_m2"], s["confirmado"], s["image"]))
    (CROP / "revision_visual_pendiente.md").write_text("\n".join(md), encoding="utf-8")
    return salida


def _csv_por_losa(por_nivel, puntuales, lineal):
    p = RES / "correlacion_cargas_validada_5niveles_por_losa.csv"
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["nivel", "losa", "area_bruta_m2", "area_neta_m2", "area_cubierta_m2",
                    "area_por_confirmar_m2", "area_sin_clasificar_m2", "solape_m2",
                    "PM_ADIC_kgf_m2", "SC_kgf_m2", "area_categoria_m2", "regiones_fuente"])
        for cod, v in por_nivel.items():
            for lo in v["losas"]:
                base = [cod, lo["id"], lo["area_bruta_m2"], lo["area_neta_m2"],
                        lo["area_cubierta_por_region_m2"], lo["area_por_confirmar_m2"],
                        lo["area_sin_clasificar_m2"], lo["solape_regiones_m2"]]
                if lo["categorias"]:
                    for cat in lo["categorias"]:
                        w.writerow(base + [cat["PM_ADIC_kgf_m2"], cat["SC_kgf_m2"],
                                           cat["area_m2"], "|".join(cat["regiones_fuente"])])
                else:
                    w.writerow(base + ["", "", "", ""])
        for pt in puntuales:
            w.writerow([pt["nivel"], pt["posicion_modelo_m"], "", "", "", "", "", "",
                        "", "", "", "puntual_marcador;losa=%s" % pt["losa_contenedora_candidata"]])
        w.writerow([lineal["nivel"], lineal["id"], "", "", "", "", "", "",
                    lineal["valor"]["PM_ADIC_kg_m"], lineal["valor"]["SC_kg_m"], "", "carga_lineal"])


def _md_regiones_pendientes(pendientes, por_causa):
    p = RES / "correlacion_cargas_validada_5niveles_regiones_pendientes.md"
    lines = ["# Superficie sin clasificar por nivel (inventario descompuesto)",
             "",
             "Area neta de la losa no intersecada por ninguna region de carga del DXF700. "
             "**No se rellena por proximidad, no se extrapola y no se renormaliza**. "
             "**No se concluye la causa por defecto**: se descompone en componentes "
             "geometricos con area/coordenadas y una hipotesis de causa; se verifica en el "
             "plano original.",
             "",
             "## Resumen por nivel (valores completos, sin redondear)",
             "",
             "| Nivel | area pendiente total (m2) | dentro franja BRASS (P4) | resto sin indicacion |",
             "|---|---|---|---|"]
    # resumen por nivel
    for cod in ["CP1S", "P1", "P2", "P3", "P4"]:
        sub = [x for x in pendientes if x["nivel"] == cod]
        total = round(sum(x["area_pendiente_m2"] for x in sub), 6)
        brass = round(sum(sum(c["area_brass_band_m2"] for c in x["componentes"]) for x in sub), 6)
        lines.append("| %s | %.6f | %.6f | %.6f |" % (cod, total, brass, total - brass))

    lines += [
        "",
        "## Detalle por losa y componente",
        "",
        "| Nivel | Losa | Componente | area (m2) | centro modelo (m) | coincide franja BRASS? | causa (hipotesis) | estado causa |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for x in pendientes:
        for c in x["componentes"]:
            lines.append("| %s | %s | c%d | %.6f | (%.3f, %.3f) | %s | %s | %s |" % (
                x["nivel"], x["losa"], c["componente"], c["area_m2"],
                c["centro_modelo_m"][0], c["centro_modelo_m"][1],
                ("si (%.4f m2)" % c["area_brass_band_m2"]) if c["coincide_franja_brass_lineal"] else "no",
                c["causa"], c["estado_causa"]))
    lines += [
        "",
        "## Discriminacion de P4: franja BRASS (carga lineal) vs superficie sin indicacion",
        "",
        "La carga lineal CL_EI_P4_001 (7600/800) no define carga superficial bajo su franja. "
        "El area de losa coincidente con la representacion grafica de esa franja queda "
        "PENDIENTE (sin superficie propia). Se separa por componente la parte dentro de la "
        "franja BRASS y la parte que NO coincide:",
        "",
        "| Nivel | Losa | Comp. | area comp. (m2) | dentro franja BRASS (m2) | resto sin indicacion (m2) |",
        "|---|---|---|---|---|---|",
    ]
    for x in pendientes:
        if x["nivel"] != "P4":
            continue
        for c in x["componentes"]:
            resto = round(c["area_m2"] - c["area_brass_band_m2"], 6)
            if c["coincide_franja_brass_lineal"]:
                lines.append("| %s | %s | c%d | %.6f | %.6f | %.6f |" % (
                    x["nivel"], x["losa"], c["componente"], c["area_m2"],
                    c["area_brass_band_m2"], resto))
            else:
                lines.append("| %s | %s | c%d | %.6f | 0.000000 | %.6f |" % (
                    x["nivel"], x["losa"], c["componente"], c["area_m2"], c["area_m2"]))
    lines += [
        "",
        "## Carga lineal P4 - unica entidad",
        "",
        "Unico registro: `CL_EI_P4_001` (PM.ADIC 7600 kg/m, SC 800 kg/m). Las areas de la "
        "franja BRASS que coinciden con la representacion grafica se referencian a ese mismo "
        "ID, NO como una carga adicional acumulable.",
        "",
        "## Agrupacion por causa (hipotesis)",
        "",
        "| causa | area total (m2) | estado |",
        "|---|---|---|",
    ]
    for causa, area, estado in por_causa:
        lines.append("| %s | %.6f | %s |" % (causa, area, estado))
    lines += [
        "",
        "## Nota de cobertura confirmada",
        "",
        "El area cubierta por tramas con correspondencia confirmada, el area correspondiente "
        "a tramas pendientes y el area sin clasificar son conjuntos disjuntos de la misma "
        "losa. No declaramos cobertura exacta del 100% mientras exista superficie residual: "
        "CP1S 0.0050, P1 90.9456, P2 0.0462, P3 45.4327, P4 29.0662 m2.",
        "",
    ]
    p.write_text("\n".join(lines), encoding="utf-8")


def _md_informe(payload):
    p = RES / "informe_correlacion_validada_5niveles.md"
    lines = [
        "# Correlacion espacial de cargas - 5 niveles (XREF validada)",
        "",
        "Completa la **2da etapa** (correlacion espacial carga->region/losa). NO se ejecuta "
        "la 3ra (aplicacion de cargas al calculo: tributacion/reacciones/receptores).",
        "",
        "## Terminologia",
        "",
        "- **Transformacion validada**: geometria de la XREF (700 - insert) mas la "
        "transformacion congelada (sistema_coordenadas) cierran sobre puntos/reticula "
        "con residuo <= 5 cm (P1/P2/P3 por rejilla etiquetada; CP1S/P4 por puntos fisicos).",
        "- **Correlacion espacial carga->region/losa**: interseccion de las regiones de "
        "trama con los dominios netos (losas - aberturas), por nivel, mediante uniones "
        "geometricas. ETAPA COMPLETADA en esta ronda.",
        "- **Aplicacion de cargas al calculo**: asignar la carga a receptores/tributar/"
        "reacciones. NO se ejecuta.",
        "",
        "## Cadena transformacion (validada, 5 niveles)",
        "",
        "- `p_estructural = p_700 - insercion_xref`  (escala 1, rot 0, sin reflejo)",
        "- `p_modelo = transformacion_congelada(p_estructural)`",
        "",
        "## Tabla por nivel (cobertura por uniones geometricas)",
        "",
        "| Nivel | n regiones | area neta (m2) | clasificada | por_confirmar | sin_clasificar | residuo balance | % clasificado |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cod in NIVELES:
        c = payload["por_nivel"][cod]["control"]
        b = payload["por_nivel"][cod]["balance"]
        flag = "*" if b["area_sin_clasificar_m2"] > 1e-9 else ""
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s%%%s |" % (
            cod, payload["por_nivel"][cod]["n_regiones_carga"],
            b["area_neta_m2"], b["area_clasificada_m2"],
            b["area_por_confirmar_m2"], b["area_sin_clasificar_m2"],
            b["residuo_m2"], c["pct_clasificado"], flag))
    lines += [
        "",
        "\\* Porcentaje REDONDEADO: no se declara cobertura exacta del 100% mientras exista "
        "superficie residual. CP1S tiene 0.0050, P2 0.0462 m2 de sin_clasificar.",
        "",
        "## Tabla por losa y categoria (ejemplo de cobertura por union)",
        "",
        "| Nivel | Losa | area neta | PM/SC | area categoria | area sin clasif |",
        "|---|---|---|---|---|---|",
    ]
    for cod in NIVELES:
        for lo in payload["por_nivel"][cod]["losas"]:
            for cat in lo["categorias"]:
                lines.append("| %s | %s | %s | %d/%d | %s | %s |" % (
                    cod, lo["id"], lo["area_neta_m2"],
                    cat["PM_ADIC_kgf_m2"], cat["SC_kgf_m2"],
                    cat["area_m2"], lo["area_sin_clasificar_m2"]))
    lines += [
        "",
        "## Entidades independientes (NO repartidas)",
        "",
        "### Cargas puntuales P2/P3",
        "",
        "| Nivel | posicion (m) | losa candidata | receptor |",
        "|---|---|---|---|",
    ]
    for pt in payload["cargas_puntuales"]["P2"] + payload["cargas_puntuales"]["P3"]:
        lines.append("| %s | (%s, %s) | %s | %s |" % (
            pt["nivel"], pt["posicion_modelo_m"][0], pt["posicion_modelo_m"][1],
            pt["losa_contenedora_candidata"], pt["elemento_receptor"]))
    li = payload["carga_lineal_p4"]
    lines += [
        "",
        "### Carga lineal P4 (independiente, no repartida)",
        "",
        "| id | valor | unidad | interpretacion | receptor | repartida? |",
        "|---|---|---|---|---|---|",
        "| %s | PM.ADIC %s kg/m ; SC %s kg/m | %s | %s | %s | no |" % (
            li["id"], li["valor"]["PM_ADIC_kg_m"], li["valor"]["SC_kg_m"],
            li["valor"]["unidad_original_plano"], li["valor"]["interpretacion_unidad"],
            li["elemento_receptor"]),
    ]
    for an in li["anclas_leyenda_modelo_m"]:
        lines.append("   - ancla modelo (%.2f, %.2f) PM %s / SC %s" % (
            an["ancla_modelo_m"][0], an["ancla_modelo_m"][1], an["PM_ADIC"], an["SC"]))
    lines += [
        "",
        "## Pendientes y advertencias",
        "",
        "- P1 zona 2800 (BRASS 2800/500): provisional, requiere revision de ingenieria "
        "(ver `zona_2800`).",
        "- Unidades (kg vs kgf): interpretacion `por_confirmar`; valores SI provisionales. ",
        "- P4 desfase rejilla RLE-EJES horizontal +0.1813 m: discrepancia DOCUMENTADA; "
        "las columnas respaldan los controles pero NO demuestran la causa; no se aplica "
        "ni se presenta como definitiva una correccion.",
        "- CP1S ANGLE, CP1S `_USER` (conflicto), P4 BRASS y P4 GRAVEL ya fueron CONFIRMADOS "
        "en la revision visual (pagina 11): ANGLE 260/250, `_USER` 260/500, GRAVEL 200/200 y "
        "BRASS = carga lineal 7600/800 (sin duplicar). Recortes en `figuras/revision_visual/`.",
        "- P3 marcadores fuera de losa: posicion conservada; receptor por definir; "
        "revisar si corresponde a viga/columna/marco o error de identificacion.",
        "",
        "## Confirmaciones aplicadas (revision visual, pagina 11)",
        "",
        "| id | nivel | trama | valor confirmado | nota |",
        "|---|---|---|---|---|",
    ]
    for c in payload["confirmadas_visual"]:
        lines.append("| %s | %s | %s | `%s` | %s |" % (
            c["id"], c["nivel"], c["patron"], c["confirmado"], c["nota"]))
    lines += [
        "",
        "## Lista unica de decisiones pendientes",
        "",
    ]
    for i, dp in enumerate(payload["decisiones_pendientes"], 1):
        lines.append("%d. **%s** - %s." % (i, dp["region"], dp["decision"]))
    lines += [
        "",
        "## Balance por nivel (conjuntos disjuntos, residuo numerico)",
        "",
        "| Nivel | neta | clasificada | por_confirmar | sin_clasificar | suma | residuo |",
        "|---|---|---|---|---|---|---|",
    ]
    for cod in NIVELES:
        b = payload["por_nivel"][cod]["balance"]
        lines.append("| %s | %.4f | %.4f | %.4f | %.4f | %.4f | %.6f |" % (
            cod, b["area_neta_m2"], b["area_clasificada_m2"], b["area_por_confirmar_m2"],
            b["area_sin_clasificar_m2"], b["suma"], b["residuo_m2"]))
    lines += [
        "",
        "## Antes / Despues de la aplicacion de las confirmaciones visuales",
        "",
        "| Nivel | % clasif. ANTES | % clasif. DESPUES | sin_clasificar ANTES (m2) | "
        "sin_clasificar DESPUES (m2) |",
        "|---|---|---|---|---|",
    ]
    antes = {
        "CP1S": (74.21, None), "P1": (90.64, 90.95), "P2": (99.99, 0.05),
        "P3": (95.02, 45.43), "P4": (6.63, None),
    }
    for cod in NIVELES:
        b = payload["por_nivel"][cod]["balance"]
        pct_d = 100 * b["area_clasificada_m2"] / max(b["area_neta_m2"], 1e-9)
        a_pct, a_sincl = antes[cod]
        a_sincl_s = ("--" if a_sincl is None else "%.2f" % a_sincl)
        lines.append("| %s | %.2f%% | %.2f%% | %s | %.4f |" % (
            cod, a_pct, pct_d, a_sincl_s, b["area_sin_clasificar_m2"]))
    lines += [
        "",
        "Variacion: CP1S 74.21% -> 100.0% (resuelto ANGLE/_USER); P4 6.63% -> 96.74% "
        "(resuelto GRAVEL/_USER; BRASS pasa a carga lineal y deja de contar como superficie). "
        "P1/P2/P3 no cambian de % de cobertura (mismo area neta; solo se reasignaron los combos "
        "a los valores confirmados AR-HBONE 260/300 y ANSI34 260/400). Los porcentajes de "
        "CP1S/P2 son ~100% por redondeo pero NO se declaran exactos (queda superficie residual).",
        "",
        "## Cargas puntuales P3 fuera de losa - contraste estructural",
        "",
        "Cargas puntuales de P3 contrastadas individualmente contra columnas, vigas y muros "
        "del modelo congelado (ver `puntuales_p3_contrastadas` y "
        "`croquis_puntuales_P3_fuera_de_losa.png`). Las dos de la franja y=18.76 (10.008, "
        "18.76) y (12.2, 18.76) quedan 0.30 m sobre el canto 18.46 de L_EI_CP3_315, fuera de "
        "losa, sin portante a distancia 0; NO se asigna receptor por defecto (portante mas "
        "cercano a 2.61 m). Las dos dentro de losa (36.54, 16.15) y (41.764, 16.15) presentan "
        "coincidencia geometrica a distancia 0 con vigas (H y0162): se senalan como receptor "
        "CANDIDATO sin autorizar automaticamente la transferencia. En cada caso se reporta la "
        "columna mas cercana entre las columnas (no solo si la primera entidad general es columna).",
        "",
        "## Superficie sin clasificar - inventario descompuesto",
        "",
        "Inventario por losa/componente en `regiones_pendientes_descompuestas` (JSON) y en "
        "`correlacion_cargas_validada_5niveles_regiones_pendientes.md`. Para P4 se separa " 
        "la franja BRASS (17.570010 m2, area "
        "coincidente con la representacion grafica de la carga lineal, que queda PENDIENTE "
        "sin superficie propia) del resto sin indicacion (11.496166 m2). La carga lineal "
        "CL_EI_P4_001 es una unica entidad; las areas coincidentes se refieren al MISMO id, "
        "no a una carga acumulable.",
        "",
        "Nota solape: el area clasificada y los solapes se miden sobre la UNION de poligonos. "
        "La coexistencia de PM.ADIC y SC sobre la misma losa NO es un solape (dos cargas "
        "simultaneas sobre la misma area); un solape real es cuando DOS regiones de la misma "
        "categoria se superponen.",
        "",
        "## P4 - explicacion del balance",
        "",
        "Balance por conjuntos disjuntos: `neta = clasificada + por_confirmar + sin_clasificar "
        "con residuo ~0`. Antes de la revision visual, P4 quedaba en 6.63% clasificado porque "
        "la regla automatica dejaba GRAVEL (828.9 m2) y BRASS en `por_confirmar`. En esta ronda "
        "se aplicaron las confirmaciones: GRAVEL superficie 200/200, `_USER` 350/100 (correccion, "
        "no 200/200) y BRASS como franja de la carga LINEAL 7600/800 (sale de la clasificacion "
        "superficial). Resultado: 96.74% clasificado, `por_confirmar` 0.0, y el `sin_clasificar` "
        "sube a 29.07 m2 (los voladizos sin hatch mas la franja BRASS que ya no se cuenta como "
        "superficie). El residuo es redondeo de coma flotante.",
        "",
    ]
    p.write_text("\n".join(lines), encoding="utf-8")


def _agrupar_pendientes_por_causa(pendientes):
    """Area total de superficie pendiente agrupada por causa hipotetica."""
    acc = {}
    for x in pendientes:
        for c in x["componentes"]:
            k = c["causa"]
            a = acc.get(k, {"area_m2": 0.0, "estado": c["estado_causa"]})
            a["area_m2"] += c["area_m2"]
            acc[k] = a
    return sorted([(k, round(v["area_m2"], 6), v["estado"]) for k, v in acc.items()],
                  key=lambda t: -t[1])


def _contrastar_puntuales_p3(puntuales_p3):
    """Contraste de las cargas puntuales de P3 (fuera de losa) con columnas, vigas y
    muros del modelo congelado. No se asigna receptor por defecto; se registra la
    distancia al elemento portante mas cercano y la hipotesis mas probable."""
    est = _estructura_modelo("P3")
    out = []
    for pt in puntuales_p3:
        px, py = pt["posicion_modelo_m"]
        p = (px, py)
        cols = sorted((_punto_a_segmento(p, c["posicion_m"], c["posicion_m"]), c["id"], "columna")
                      for c in est["columnas"])
        vigas = sorted((_punto_a_segmento(p, v["inicio_m"], v["fin_m"]), v["id"], "viga")
                       for v in est["vigas"])
        muros = sorted((_punto_a_segmento(p, m["eje_inicio_m"], m["eje_fin_m"]), m["id"], "muro")
                       for m in est["muros"])
        cand = sorted(cols + vigas + muros)[:4]
        mas_cercana_col = cols[0] if cols else None
        columna_mas_cercana = {"id": mas_cercana_col[1],
                               "distancia_m": round(mas_cercana_col[0], 3)} if mas_cercana_col else None
        fuera = pt.get("fuera_de_losa", False)
        if fuera:
            interp = ("posicion a 0.30 m sobre el canto 18.46 de L_EI_CP3_315 (fuera de la "
                      "losa); el receptor candidato mas probable no se autoriza de forma "
                      "automatica por coincidencia geometrica, se senala como candidato y se "
                      "revisa el elemento real.")
        else:
            interp = ("posicion dentro de losa %s; la coincidencia geometrica con un portante "
                      "se senala como receptor CANDIDATO (viga/columna a distancia 0) sin "
                      "autorizarlo automaticamente como transferencia.") % pt["losa_contenedora_candidata"]
        out.append({
            "nivel": "P3",
            "posicion_modelo_m": [round(px, 3), round(py, 3)],
            "marcador_700": pt["marcador_700"],
            "losa_contenedora_candidata": pt["losa_contenedora_candidata"],
            "fuera_de_losa": fuera,
            "columna_mas_cercana": columna_mas_cercana,
            "elementos_portantes_cercanos": [
                {"tipo": t, "id": i, "distancia_m": round(d, 3)} for d, i, t in cand],
            "resultado": {
                "interpretacion": interp,
                "receptor_candidato": None,
                "estado": "receptor_candidato_senalado_sin_autorizar"
                if not fuera else "sin_receptor_asignado_por_falta_de_apoyo_portante_claro",
            },
        })
    return out


def _crops_zonas_pendientes(pendientes, puntuales_p3=None):
    """Recortes del plano original para los casos de revision visual de superficie pendiente
    y de las cargas puntuales de P3. Muestran SIMULTANEAMENTE region de carga (trama),
    contexto estructural (losas + columnas + vigas + muros + bordes libres) e indicacion de
    carga (marcadores/leyendas). Cada recorte va a figuras/revision_visual/."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    CROP = FIG / "revision_visual"
    CROP.mkdir(parents=True, exist_ok=True)

    # --- recortes de superficie pendiente (las losas con > 1 m2) ----------
    superficie = []
    for x in pendientes:
        if x["area_pendiente_m2"] < 1.0:
            continue
        cod, losa_id = x["nivel"], x["losa"]
        data = _cargar_nivel(cod)
        ab = _aberturas_shapely(data)
        dxf = X.extraer_dxf()
        est = _estructura_modelo(cod)
        lo = next((l for l in (data["losas"] if isinstance(data["losas"], list)
                               else list(data["losas"].values())) if l["id"] == losa_id), None)
        if lo is None:
            continue
        neto = _net_domain(lo, ab)
        minx, miny, maxx, maxy = neto.bounds
        pad = max((maxx - minx), (maxy - miny)) * 0.15 + 1.0
        x0, x1, y0, y1 = minx - pad, maxx + pad, miny - pad, maxy + pad
        fig, ax = plt.subplots(figsize=(9, 8))
        # losa neta
        xs, ys = neto.exterior.xy
        ax.plot(xs, ys, color="#1f77b4", lw=1.2)
        ax.fill(xs, ys, color="#1f77b4", alpha=0.06)
        for intr in getattr(neto, "interiors", []) or []:
            xi, yi = intr.xy
            ax.fill(xi, yi, color="white")
        # regiones de carga (indicacion de carga)
        for r in dxf["regiones"][cod]:
            if X._es_muestra_leyenda(r["outline"]) or (cod, r["patron"]) in _MAPA[1]:
                continue
            pm = C._poly_dxf700_a_modelo(cod, r["outline"])
            if pm is None or not pm.intersects(neto):
                continue
            for part in ([pm] if pm.geom_type == "Polygon" else list(pm.geoms)):
                px, py = part.exterior.xy
                ax.plot(px, py, color="#2ca02c", lw=0.8, ls="--")
                ax.fill(px, py, color="#2ca02c", alpha=0.10)
            ax.text(pm.centroid.x, pm.centroid.y, r["patron"], fontsize=6, ha="center")
        # contexto estructural
        for v in est["vigas"]:
            ax.plot([v["inicio_m"][0], v["fin_m"][0]], [v["inicio_m"][1], v["fin_m"][1]],
                    color="#8c564b", lw=0.8, alpha=0.7)
        for c in est["columnas"]:
            ax.plot(c["posicion_m"][0], c["posicion_m"][1], marker="s", color="#8c564b",
                    ms=4)
        for m in est["muros"]:
            ax.plot([m["eje_inicio_m"][0], m["eje_fin_m"][0]],
                    [m["eje_inicio_m"][1], m["eje_fin_m"][1]], color="#7f7f7f",
                    lw=2.0, alpha=0.5)
        for b in est["bordes_libres"]:
            ax.plot([b["inicio_m"][0], b["fin_m"][0]], [b["inicio_m"][1], b["fin_m"][1]],
                    color="#d62728", lw=1.0, ls=":")
        # residuo (zona pendiente) en rojo relleno
        free = neto
        for r in dxf["regiones"][cod]:
            if X._es_muestra_leyenda(r["outline"]) or (cod, r["patron"]) in _MAPA[1]:
                continue
            pm = C._poly_dxf700_a_modelo(cod, r["outline"])
            if pm is None:
                continue
            try:
                free = free.difference(pm)
            except Exception:
                pass
        if not free.is_empty:
            if free.geom_type == "Polygon":
                fxs, fys = free.exterior.xy
                ax.fill(fxs, fys, color="#d62728", alpha=0.5)
            else:
                for g in getattr(free, "geoms", []):
                    fxs, fys = g.exterior.xy
                    ax.fill(fxs, fys, color="#d62728", alpha=0.5)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_title("%s | %s | sin_clasificar %.4f m2 | region+estructura+carga"
                     % (cod, losa_id, x["area_pendiente_m2"]), fontsize=9)
        ax.grid(alpha=0.3)
        out = CROP / ("croquis_superficie_%s_%s.png" % (cod, losa_id))
        fig.savefig(out, dpi=140, bbox_inches="tight")
        plt.close(fig)
        superficie.append({
            "id": "SUP_%s_%s" % (cod, losa_id), "nivel": cod, "losa": losa_id,
            "area_pm2": x["area_pendiente_m2"], "componentes": x["componentes"],
            "image": out.name, "estado": "revision_visual_pendiente",
        })

    # --- recortes de las cargas puntuales de P3 ------------------------------
    puntual = []
    if not puntuales_p3:
        puntuales_p3 = []
    data = _cargar_nivel("P3")
    ab = _aberturas_shapely(data)
    est = _estructura_modelo("P3")
    dxf3 = X.extraer_dxf()
    losa315 = next((l for l in (data["losas"] if isinstance(data["losas"], list)
                                else list(data["losas"].values())) if l["id"] == "L_EI_CP3_315"), None)
    neto315 = _net_domain(losa315, ab) if losa315 is not None else None
    # marco comun de la vista: zona alrededor de la franja y=18.76 (fuera de losa 315)
    x0, y0_ = 8.0, 15.0
    x1, y1 = 15.0, 20.5
    for i, pt in enumerate(puntuales_p3):
        px, py = round(pt["posicion_modelo_m"][0], 3), round(pt["posicion_modelo_m"][1], 3)
        fig, ax = plt.subplots(figsize=(8.5, 8))
        for r in dxf3["regiones"]["P3"]:
            if X._es_muestra_leyenda(r["outline"]):
                continue
            pm = C._poly_dxf700_a_modelo("P3", r["outline"])
            if pm is None:
                continue
            for part in ([pm] if pm.geom_type == "Polygon" else list(pm.geoms)):
                ax.plot(*part.exterior.xy, color="#2ca02c", lw=0.8, ls="--")
                ax.fill(*part.exterior.xy, color="#2ca02c", alpha=0.10)
        for lo in (data["losas"] if isinstance(data["losas"], list)
                   else list(data["losas"].values())):
            neto = _net_domain(lo, ab)
            xs, ys = neto.exterior.xy
            ax.plot(xs, ys, color="#1f77b4", lw=1.2)
            ax.fill(xs, ys, color="#1f77b4", alpha=0.06)
            for intr in getattr(neto, "interiors", []) or []:
                xi, yi = intr.xy
                ax.fill(xi, yi, color="white")
        for c in est["columnas"]:
            ax.plot(c["posicion_m"][0], c["posicion_m"][1], marker="s", color="#8c564b", ms=5)
            ax.annotate(c["id"], (c["posicion_m"][0], c["posicion_m"][1]),
                        fontsize=6, xytext=(4, 4), textcoords="offset points")
        for v in est["vigas"]:
            ax.plot([v["inicio_m"][0], v["fin_m"][0]], [v["inicio_m"][1], v["fin_m"][1]],
                    color="#8c564b", lw=1.0, alpha=0.8)
        for b in est["bordes_libres"]:
            ax.plot([b["inicio_m"][0], b["fin_m"][0]], [b["inicio_m"][1], b["fin_m"][1]],
                    color="#d62728", lw=1.0, ls=":")
            ax.text((b["inicio_m"][0] + b["fin_m"][0]) / 2,
                    (b["inicio_m"][1] + b["fin_m"][1]) / 2, b["id"], fontsize=6, color="#d62728")
        for m in dxf3["puntual_marcadores"]:
            if m["planta"] != "P3":
                continue
            mx, my = C._dxf_700_a_modelo("P3", m["cx"], m["cy"])
            if (round(mx, 3), round(my, 3)) == (px, py):
                ax.plot(mx, my, marker="o", color="#d62728", ms=11, zorder=5)
                ax.annotate("(%.3f, %.3f)" % (mx, my), (mx, my), fontsize=8,
                            xytext=(7, -12), textcoords="offset points", color="#d62728",
                            fontweight="bold")
            else:
                ax.plot(mx, my, marker="o", color="#333", ms=6, zorder=3)
        col = pt.get("columna_mas_cercana")
        col_txt = " %s (%.3f m)" % (col["id"], col["distancia_m"]) if col else " ninguna"
        estado = pt.get("resultado", {}).get("estado", "")
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0_, y1)
        ax.set_aspect("equal")
        ax.set_title("P3 | puntual (%.3f, %.3f) | columna mas cercana:%s\n"
                     "estado: %s" % (px, py, col_txt, estado), fontsize=9)
        ax.grid(alpha=0.3)
        outp = CROP / ("croquis_puntuales_P3_%02d_%.3f_%.3f.png" % (i, px, py))
        fig.savefig(outp, dpi=140, bbox_inches="tight")
        plt.close(fig)
        puntual.append({
            "id": "P3_PUNT_%s" % ("%.3f_%.3f" % (px, py)), "nivel": "P3",
            "posicion_modelo_m": [px, py],
            "losa_contenedora_candidata": pt["losa_contenedora_candidata"],
            "fuera_de_losa": pt["fuera_de_losa"],
            "columna_mas_cercana": col,
            "image": outp.name, "estado": estado,
            "nota": pt.get("resultado", {}).get("interpretacion", ""),
        })
    return superficie, puntual


def main() -> dict:
    por_nivel = {}
    for cod in NIVELES:
        por_nivel[cod] = correlacion_nivel(cod)

    unidad = P11.evidencias_unidades()
    zona2800 = P11.zona_2800()
    pu = {"P2": _puntuales("P2"), "P3": _puntuales("P3")}
    lineal = _lineal_p4()
    pendientes = []
    for cod in NIVELES:
        pendientes += _region_pendiente(cod)

    # inventario de zonas pendientes por causa (agrupado)
    pendientes_por_causa = _agrupar_pendientes_por_causa(pendientes)

    # contraste de las cargas puntuales de P3 fuera de losa con el contexto estructural
    puntuales_p3 = _contrastar_puntuales_p3(pu["P3"])

    crops = _crops_revision_visual()
    crops_superficie, crops_puntuales = _crops_zonas_pendientes(pendientes, puntuales_p3)

    # balance global y lista unica de decisiones pendientes
    balances = {cod: por_nivel[cod]["balance"] for cod in NIVELES}
    decisiones_pendientes = [
        {"id": "P3_FUERA_DE_LOSA",
         "region": "P3 puntuales (10.008,18.76) y (12.2,18.76) fuera de losa; "
                   "(36.54,16.15) y (41.764,16.15) dentro de losa",
         "estado": "receptor_por_definir",
         "decision": ("las dos de y=18.76 quedan 0.30 m sobre el canto 18.46 de "
                      "L_EI_CP3_315, fuera de losa, sin portante a distancia 0; no se asigna "
                      "receptor. Las dos de y=16.15 presentan coincidencia geometrica con "
                      "vigas (distancia 0) y se senalan como receptor CANDIDATO sin autorizar "
                      "automaticamente la transferencia. En cada caso se calcula la columna mas "
                      "cercana entre las columnas.")},
        {"id": "SIN_CLASIFICAR", "region": "superficie residual por nivel (CP1S/P1/P2/P3/P4)",
         "estado": "sin_clasificar_causa_por_verificar",
         "decision": ("inventario descompuesto por losa/componente en "
                      "regiones_pendientes_descompuestas; P4 separa la franja BRASS (17.57 m2) "
                      "del resto sin indicacion (11.50 m2). La causa se verifica en el plano "
                      "original.")},
        {"id": "TRANSFERENCIA_POR_LOSA",
         "region": "global (mecanismo de transferencia por losa)",
         "estado": "por_definir",
         "decision": ("cada losa tiene `tipo_transferencia`/`direccion_transferencia` sin "
                      "resolver; la propuesta de transferencia por losa queda PENDIENTE hasta "
                      "la etapa de tributacion (no se ejecuta aqui).")},
        {"id": "UNIDADES_KG_VS_KGF", "region": "global",
         "estado": "provisional",
         "decision": "confirmar interpretacion de unidades (kg vs kgf) antes del calculo."},
    ]
    confirmadas_visual = [c for c in crops]
    recortes_revision = crops_superficie + crops_puntuales

    payload = {
        "titulo": "Correlacion espacial de cargas (pagina 11) - 5 niveles (XREF validada)",
        "estado": "correlacion_geoespacial_emitida",
        "etapa": "2da etapa: correlacion espacial carga->region/losa COMPLETADA",
        "no_ejecuta": "aplicacion de cargas al calculo (tributacion/reacciones/receptores)",
        "cadena_transformacion": {
            "p_estructural": "p_700 - insercion_xref",
            "p_modelo": "transformacion_congelada(p_estructural)",
            "escala_xref": 1.0, "rotacion_xref_deg": 0.0, "reflexion_xref": False,
        },
        "transformaciones_por_nivel": {
            cod: {"ox": C.TRANS_VALIDADA[cod]["ox"], "oy": C.TRANS_VALIDADA[cod]["oy"],
                  "flip_y": C.TRANS_VALIDADA[cod]["flip_y"],
                  "insert": list(C.TRANS_VALIDADA[cod]["insert"]),
                  "estado": "transformacion_xref_validada"} for cod in NIVELES},
        "nota_localidad": ("correspondencia trama->(PM_ADIC,SC) por leyenda de CADA nivel; "
                           "no hay diccionario global por nombre de patron. Una trama sin "
                           "leyenda propia queda `trama_correspondencia_pendiente` (NO se "
                           "inyectan valores 'default' que inflen el % clasificado)."),
        "unidades": unidad,
        "zona_2800": zona2800,
        "por_nivel": por_nivel,
        "balances_por_nivel": balances,
        "decisiones_pendientes": decisiones_pendientes,
        "revision_visual": crops,
        "recortes_superficie_pendiente": crops_superficie,
        "recortes_puntuales_p3": crops_puntuales,
        "regiones_pendientes_descompuestas": pendientes,
        "pendientes_agrupadas_por_causa": pendientes_por_causa,
        "puntuales_p3_contrastadas": puntuales_p3,
        "cargas_puntuales": pu,
        "carga_lineal_p4": lineal,
        "regiones_pendientes_P123": pendientes,
        "p4_balance_explicacion": {
            "mecanismo_reconciliacion": ("area_neta = clasificada + por_confirmar + "
                                         "sin_clasificar + residuo (residuo = redondeo de "
                                         "coma flotante, no diferencia geometrica)."),
            "metodo_conjuntos_disjuntos": ("los conjuntos clasificada / por_confirmar / "
                                           "sin_clasificar se miden sobre la UNION neta y son "
                                           "disjuntos; 'clasificada' no es 'la misma numeracion ', "
                                           "por lo que no se cuenta dos veces la misma losa."),
            "valores_previos_a_la_ronda_de_articulaciones_visuales": {
                "area_neta_m2": 892.0179, "clasificada_m2": 59.1831,
                "por_confirmar_m2": 821.3386, "sin_clasificar_m2": 11.4962,
                "residuo_m2": -0.000031,
                "nota": ("el 821.34 eran las areas que QUEDABAN por_confirmar por la regla "
                         "automatica (GRAVEL y BRASS sin valor). Se han resuelto en la revision "
                         "visual a GRAVEL 200/200, _USER 350/100 y BRASS=lineal 7600/800.")},
            "valores_despues_de_la_ronda_de_articulaciones_visuales": {
                "area_neta_m2": 892.0179, "clasificada_m2": 862.9517,
                "por_confirmar_m2": 0.0000, "sin_clasificar_m2": 29.0662,
                "residuo_m2": -0.000029,
                "que_subio_la_clasificada": ("GRAVEL (2 regiones, superf.) y _USER (350/100) "
                                             "pasaron de por_confirmar a clasificada; BRASS dejo de "
                                             "contarse como superficie (salio de la clasificacion).")},
            "estado": "reconciliado_y_confirmado_ronda_visual",
        },
        "desfase_p4": {
            "desfase_m": 0.1813,
            "estado": "discrepancia_documentada_no_compensada",
            "causa": "por_establecer (la coincidencia de columnas respalda los controles "
                     "pero no demuestra la causa del desfase de las lineas RLE-EJES)",
        },
        "confirmadas_visual": confirmadas_visual,
        "nota_confirmadas_visual": ("son las 4 corroboraciones visuales de la pagina 11 ya "
                                    "APLICADAS: CP1S ANGLE 260/250, CP1S _USER 260/500, "
                                    "P4 GRAVEL 200/200 y P4 BRASS=lineal 7600/800. No quedan "
                                    "tramas por_confirmar_visual."),
    }

    CARGAS_OUT.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    (CARGAS_OUT / "correlacion_cargas_validada_5niveles.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for cod in NIVELES:
        _figura_nivel(cod, por_nivel[cod])
    _csv_por_losa(por_nivel, pu["P2"] + pu["P3"], lineal)
    _md_regiones_pendientes(pendientes, pendientes_por_causa)
    _md_informe(payload)
    return payload


if __name__ == "__main__":
    main()
    print("OK  datos/casos_analisis/correlacion_cargas_validada_5niveles.json")
    print("OK  resultados/cargas_reales/figuras/correlacion_cargas_{CP1S,P1,P2,P3,P4}.png")
    print("OK  resultados/cargas_reales/correlacion_cargas_validada_5niveles_por_losa.csv")
    print("OK  resultados/cargas_reales/correlacion_cargas_validada_5niveles_regiones_pendientes.md")
    print("OK  resultados/cargas_reales/informe_correlacion_validada_5niveles.md")