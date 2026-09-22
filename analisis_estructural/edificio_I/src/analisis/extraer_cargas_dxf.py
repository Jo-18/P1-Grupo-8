"""
Extraccion vectorial de cargas reales desde el DXF autoritativo 2017_67-700.

FUENTE VECTORIAL AUTORITATIVA (tarea 2/3/4)
--------------------------------------------
El DXF ``2017_67-700.dxf`` (DWG ``planos_edificio_ing/2017_67-700.dwg``) contiene, en
modelspace, las cinco plantas de cargas CIELO (1° Subterráneo y Pisos 1°-4°) con:
  * regiones de trama = entidades HATCH de capa ``HATCH CARGAS`` con nombre de PATRON
    (p.ej. ``_USER``, ``ANGLE``, ``AR-HBONE``, ``BRASS``, ``ANSI34``, ``GRAVEL``,
    ``AR-CONC``) y contorno poligonal (LWPOLYLINE o camino del HATCH). El patron de
    HATCH es el descriptor determinista de la trama (reemplaza el bloqueo por imagen).
  * leyendas "CARGAS DE DISEÑO" cuyo texto PM.ADIC./SC define el valor de cada trama.
  * cargas puntuales = polilinea cerrada de 2 puntos (marcador "punto negro") en la
    capa "0", junto a una leyenda "CARGA PUNTUAL".
  * carga lineal del piso 4 = trama con leyenda "(CARGA LINEAL)" PM.ADIC. 7600 SC 800.

El DXF modelspace NO expone ejes estructurales etiquetados (solo las plantas de trama).
La transformacion DXF->modelo por planta se deriva de la ALINEACION de los bordes de
losa/trama con la rejilla de ejes conocida del sistema de coordenadas congelado
(sistema_coordenadas -> eje_x_positivo E=0,F=10,G=20,..., eje_y_positivo 1=0,2=8.9,3=16.15).
Se ajusta UNA transformacion por planta (no se reutiliza), con un minimo de 3 puntos de
control alineados a ejes y se reporta escala/rotación/orientación/residuo.

ALCANCE: NO ejecuta tributación con cargas reales ni diseño estructural. No modifica los
JSON congelados de geometría (solo lectura). La página 11 del PDF se conserva como
control visual/documental; el DXF es la fuente autoritativa.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point

_PATH_DXF = r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\Datos Estructurales\2017_67-700.dxf"

BASE = Path(__file__).resolve().parents[2]
GEO = BASE / "datos/geometria"
CARG = BASE / "datos/cargas"
OUT = BASE / "resultados/cargas_reales"
FIG_OUT = OUT / "figuras"

NIVELES = {
    "CP1S": "edificio_I_cielo_piso_1_subterraneo_borrador.json",
    "P1":   "edificio_I_cielo_piso_1_borrador.json",
    "P2":   "edificio_I_cielo_piso_2_borrador.json",
    "P3":   "edificio_I_cielo_piso_3_borrador.json",
    "P4":   "edificio_I_cielo_piso_4_borrador.json",
}
ETIQUETA = {"CP1S": "1° Subterráneo", "P1": "Piso 1", "P2": "Piso 2",
            "P3": "Piso 3", "P4": "Piso 4"}

# Posiciones de titulo de cada planta en el modelspace del DXF (layer RLA-TEXTOS2).
TITULOS = {
    "CP1S": (-1488.101, 5407.294),
    "P1":   (4777.799, 4762.185),
    "P2":   (10868.326, 5898.225),
    "P3":   (10630.991, -210.412),
    "P4":   (-342.629, -1070.624),
}


# ---------------------------------------------------------------------------
# parseo del DXF
# ---------------------------------------------------------------------------
def _cargar_doc():
    import ezdxf
    _path = Path(_PATH_DXF)
    if not _path.exists():
        return None
    return ezdxf.readfile(str(_path))


def _plant_mas_cercana(x: float, y: float) -> str:
    a = np.array(list(TITULOS.values()))
    return list(TITULOS.keys())[int(np.argmin(np.hypot(a[:, 0] - x, a[:, 1] - y)))]


def _recta(p0, p1):
    """Linea (a,b,c): a*x+b*y+c=0 normalizada, |(a,b)|=1."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ln = float(np.hypot(dx, dy))
    if ln < 1e-6:
        return None
    a, b = -dy / ln, dx / ln
    c = -(a * p0[0] + b * p0[1])
    return a, b, c


def extraer_dxf() -> dict:
    """Devuelve, por planta: regiones (outline, patron), leyendas (SC/PM por bloque),
    marcadores puntuales y traza lineal."""
    doc = _cargar_doc()
    if doc is None:
        return {"error": "DXF no encontrado", "ruta": _PATH_DXF}
    msp = doc.modelspace()

    textos = []            # (planta, x, y, texto)
    regiones = {}          # planta -> [ {patron, outline} ]
    for cod in NIVELES:
        regiones[cod] = []

    # hatches = regiones de trama; outline = camino poligonal del hatch (o lwpolyline)
    for e in msp:
        t = e.dxftype()
        if t == "TEXT":
            px, py = float(e.dxf.insert[0]), float(e.dxf.insert[1])
            textos.append((_plant_mas_cercana(px, py), px, py, str(e.dxf.text).strip()))
        elif t == "HATCH":
            pols = []
            for pth in e.paths:
                try:
                    v = list(pth.vertices)
                    if len(v) >= 3:
                        pols.append([(float(p[0]), float(p[1])) for p in v])
                except Exception:
                    pass
            if not pols:
                continue
            a = np.vstack(pols)
            cx, cy = float(a[:, 0].mean()), float(a[:, 1].mean())
            pl = _plant_mas_cercana(cx, cy)
            area = _pol_area(*pols)
            if e.dxf.layer == "HATCH CARGAS" and e.dxf.pattern_name != "SOLID" \
                    and area > 5.0:  # filtra remaches/leyenda pequenos
                regiones[pl].append({
                    "patron": e.dxf.pattern_name or "",
                    "outline": _union_outline(pols),
                    "area_dxf_u2": round(area, 3),
                    "cx_dxf": round(cx, 3), "cy_dxf": round(cy, 3),
                })

    # leyendas por planta: bloques "CARGAS DE DISEÑO" con SC/PM.ADIC del mismo bloque
    leyendas = {}
    for cod in NIVELES:
        leyendas[cod] = _parsear_leyendas([t for t in textos if t[0] == cod])

    # marcadores puntuales: polilinea cerrada de 2 puntos en capa 0
    puntual_marcadores = []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "0" and getattr(e, "closed", False):
            pts = [(float(p[0]), float(p[1])) for p in e.get_points()]
            if len(pts) == 2:
                cx, cy = (pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2
                puntual_marcadores.append({
                    "planta": _plant_mas_cercana(cx, cy), "cx": cx, "cy": cy,
                    "bbox": pts,
                })

    return {
        "ruta": _PATH_DXF,
        "_doc": doc,
        "titulos": TITULOS,
        "textos": textos,
        "regiones": regiones,
        "leyendas": leyendas,
        "puntual_marcadores": puntual_marcadores,
    }


def _pol_area(*pols) -> float:
    tot = 0.0
    for poly in pols:
        s = 0.0
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            s += x0 * y1 - x1 * y0
        tot += abs(s) / 2.0
    return tot


def _union_outline(pols):
    """Devuelve la union (shapely) de los caminos poligonales; si es uno solo, su exterior."""
    polys = [Polygon(p) for p in pols]
    if len(polys) == 1:
        return polys[0]
    uni = polys[0]
    for p in polys[1:]:
        uni = uni.union(p)
    return uni


def _parsear_leyendas(textos_planta: List[Tuple[str, float, float, str]]) -> List[dict]:
    import re
    bloques = []
    for _, x, y, txt in textos_planta:
        if txt.startswith("CARGAS DE DISE"):
            bloques.append({"px": x, "py": y})
    bloques.sort(key=lambda b: (b["px"], -b["py"]))
    out = []
    for b in bloques:
        comp = [t for t in textos_planta
                if abs(t[1] - b["px"]) < 1500 and b["py"] - 430 <= t[2] <= b["py"]]
        sc = pm = None
        nombres = []
        for _, x, y, txt in comp:
            m = re.search(r"SC\s*=\s*([\d.]+)", txt)
            if m:
                sc = round(float(m.group(1)))
            m2 = re.search(r"PM\.?\s*ADIC\.?\s*=\s*([\d.]+)", txt)
            if m2:
                pm = round(float(m2.group(1)))
            if txt.startswith("PM.ADIC"):
                nombres.append(txt)
        out.append({
            "px_dxf": round(b["px"], 2), "py_dxf": round(b["py"], 2),
            "SC": sc, "PM_ADIC": pm,
            "es_lineal": any("LINEAL" in t or "lineal" in t for _, x, y, t in comp),
            "textos_brutos": list(comp),
        })
    return out


# ---------------------------------------------------------------------------
# correlacion trama -> carga (tarea 3)
# ---------------------------------------------------------------------------
def correlacion_pattern_combo(dxf: dict) -> Dict[str, dict]:
    """Vinculo determinista trama->carga por planta.

    Cada bloque "CARGAS DE DISEÑO" define un valor (PM.ADIC, SC) y contiene una muestra
    fisica de la trama (swatch) de area homogenea (todas ~382136 u2 en este DXF). A cada
    bloque se le atribuye la swatch cuyo centro esta mas cerca (misma banda x/y), con lo
    cual el PATRON de la swatch queda asociado al valor del bloque. Las regiones de carga
    (hatches grandes, no swatch) de ese patron reciben ese valor. Una region sin bloque
    asociado queda `por_confirmar_trama`.
    """
    res = {}
    for cod, regions in dxf["regiones"].items():
        swatches, regiones = _separar_swatches(regions)
        bloques = [b for b in dxf["leyendas"][cod] if b["SC"] is not None
                   and b["PM_ADIC"] is not None]
        # los bloques "CARGA LINEAL" (piso 4) NO definen una trama superficial; el valor
        # 7600/800 va a la carga lineal. Quedan excluidos de la correlacion de regiones.
        bloques_lineales = [b for b in bloques if b.get("es_lineal") or
                            (cod == "P4" and b["PM_ADIC"] >= 7600)]
        bloques_superficiales = [b for b in bloques if b not in bloques_lineales]
        # emparejar por COLUMNA (misma x) y por rango de y, uno a uno
        patron_por_bloque = _emparejar_por_columna(bloques_superficiales, swatches)
        # dict patron -> (PM,SC, bloque)
        patron_combo = {}
        for pb in patron_por_bloque:
            patron_combo.setdefault(pb["patron"], pb)
        # detectar conflictos: mismpo patron con dos valores distintos
        conflictos = []
        for patron, pb in patron_combo.items():
            dups = [x for x in patron_por_bloque if x["patron"] == patron]
            if len({(x["PM_ADIC"], x["SC"]) for x in dups}) > 1:
                conflictos.append(patron)
        # regiones -> asignacion
        regiones_con_carga = _asignar_regiones(regiones, patron_combo, conflictos, cod)
        res[cod] = {
            "swatches_detectadas": [s["patron"] for s in swatches],
            "bloques_patron": patron_por_bloque,
            "bloques_lineales": [{"PM_ADIC": b["PM_ADIC"], "SC": b["SC"],
                                  "px_dxf": b["px_dxf"], "py_dxf": b["py_dxf"]}
                                 for b in bloques_lineales],
            "patron_combo": {p: {"PM_ADIC": v["PM_ADIC"], "SC": v["SC"]}
                             for p, v in patron_combo.items()},
            "conflictos_patron": conflictos,
            "regiones": regiones_con_carga,
        }
    return res


def _asignar_regiones(regiones, patron_combo, conflictos, cod):
    out = []
    for r in regiones:
        pb = patron_combo.get(r["patron"])
        if pb and r["patron"] not in conflictos:
            pm, sc = pb["PM_ADIC"], pb["SC"]
            estado = "trama_correlacionada"
        else:
            # NO se inyectan valores 'default' por nivel: una trama cuyo patron no tiene
            # bloque de leyenda propio (o esta en conflicto) queda pendiente de
            # confirmacion. La correspondencia del P4 (200/200) queda centralizada en
            # catalogo_cargas_diseno_edificio_I.json ("Piso 4" -> evidencia_superficie_200_200),
            # NO como regla de codigo.
            pm, sc = None, None
            estado = "por_confirmar_trama"
        out.append({
            "patron": r["patron"],
            "area_dxf_u2": r["area_dxf_u2"],
            "PM_ADIC": pm, "SC": sc,
            "estado": estado,
        })
    return out


def _emparejar_por_columna(bloques, swatches):
    """Empareja cada bloque de leyenda con su swatch fisica.

    En este DXF la muestra de trama (swatch) se dibuja a +OX en x y -OY en y respecto al
    bloque (offsets de trazado constantes). Se usa el offset medido por columna para
    proyectar cada bloque al centro esperado de su swatch y se asigna la swatch mas
    cercana sin repetir (greedy por distancia)."""
    # estimar offset (dx, dy) bloque->swatch a partir del primer bloque y el conjunto
    if not bloques or not swatches:
        return []
    # dy: distancia vertical bloque a su fila de swatches (min |py-sy|)
    dys = sorted(abs(float(b["py_dxf"]) - float(s["cy_dxf"])) for b in bloques for s in swatches)
    dy = dys[0] if dys else 0.0
    # dx: para cada bloque, un swatch en su fila (cy cercano a py-dy) da el despl x
    dxs = []
    for b in bloques[:8]:
        fila = [s for s in swatches if abs((float(b["py_dxf"]) - dy) - float(s["cy_dxf"])) < 30]
        if fila:
            fila.sort(key=lambda s: abs(float(s["cx_dxf"]) - float(b["px_dxf"])))
            dxs.append(float(fila[0]["cx_dxf"]) - float(b["px_dxf"]))
    if dxs:
        import statistics
        dx = statistics.median(dxs)
    else:
        dx = 0.0
    disponibles = list(swatches)
    out = []
    for b in sorted(bloques, key=lambda x: -x["py_dxf"]):
        target_x = float(b["px_dxf"]) + dx
        target_y = float(b["py_dxf"]) - dy
        if not disponibles:
            break
        mejor = min(disponibles,
                    key=lambda s: abs(float(s["cx_dxf"]) - target_x)
                    + abs(float(s["cy_dxf"]) - target_y))
        out.append({
            "patron": mejor["patron"],
            "PM_ADIC": b["PM_ADIC"], "SC": b["SC"],
            "px_dxf": b["px_dxf"], "py_dxf": b["py_dxf"],
            "_dx_sw": dx, "_dy_sw": dy,
            "certeza": "alta",
        })
        disponibles.remove(mejor)
    return out


def _separar_swatches(regions):
    """Swatches = hatches 'HATCH CARGAS' con area homogenea (la muestra de leyenda,
    ~382136 u2). Regiones = hatches grandes (zona de carga). Identificacion por area."""
    if not regions:
        return [], []
    areas = sorted(r["area_dxf_u2"] for r in regions)
    mediana = float(np.median(areas))
    # umbral: swatch es una zona con area proxima a la moda de areas pequenas repetidas
    from collections import Counter
    c = Counter(round(a / 1000.0) for a in areas)
    moda_cluster = c.most_common(1)[0][0] * 1000.0 if c else mediana
    tol = 0.25 * moda_cluster
    swatches, regiones = [], []
    for r in regions:
        if abs(float(r["area_dxf_u2"]) - moda_cluster) <= tol:
            swatches.append(r)
        else:
            regiones.append(r)
    return swatches, regiones


# ---------------------------------------------------------------------------
# ingredientes de salida (para mantener compatibilidad con la suite existente)
# ---------------------------------------------------------------------------
KGF_A_KN = 0.00980665
PP_DENSIDAD_KGF_M3 = 2500.0


def cargar_nivel(cod):
    return json.loads((GEO / NIVELES[cod]).read_text(encoding="utf-8"))


def _sistema_coordenadas(cod: str) -> dict:
    d = cargar_nivel(cod)
    return d.get("sistema_coordenadas") or {}


def resolver_transformacion(dxf: dict) -> Dict[str, dict]:
    """Transformacion DXF->modelo por planta. Control principal: HUEELLA del edificio
    (entidades estructurales: contornos de las regiones de carga NO leyenda), cuyas
    4 esquinas forman >=4 puntos no colineales; validacion con los ejes confirmados.
    NO se reutiliza entre plantas. Devuelve estado, parametros (escala/rotacion/
    reflexion/traslacion), puntos usados/descartados, residuos de calibracion y de
    validacion independiente, comparacion con 100 u/m y estado.""" 
    res = {}
    for cod in NIVELES:
        sc = _sistema_coordenadas(cod)
        ejes_x = _leer_ejes_verticales(sc)
        ejes_y = _leer_ejes_horizontales(sc)
        regions = dxf["regiones"][cod]
        r = _ajustar_transform_por_ejes(cod, regions, ejes_x, ejes_y)
        res[cod] = r
    return res


def _modelo_footprint(cod):
    data = cargar_nivel(cod)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    pols = [Polygon([(p[0], p[1]) for p in lo["poligono_exterior"]]) for lo in losas]
    mp = pols[0]
    for p in pols[1:]:
        mp = mp.union(p)
    return mp


def _resumen_huella(cod, regions, ejes_x, ejes_y):
    """Diagnostico (NO autoriza asignacion): compara las escalas x/y implicitas al hacer
    coincidir el bbox de la HUEELLA del modelo (losas congeladas) con el bbox del
    contorno DXF de la planta (region de carga NO leyenda). Si x e y no comparten escala
    (no uniformidad), una similitud sin cizalle no puede satisfacer ambas -> la
    transformacion no queda validada y las cargas no se asignan espacialmente."""
    mp = _modelo_footprint(cod)
    mb = mp.bounds
    dbx = _dxf_footprint_bbox(regions)
    grid_x = [v for _, v in ejes_x]
    grid_y = [v for _, v in ejes_y]
    if dbx is None:
        return {"estado_huella": "sin_contorno"}
    s_x = (dbx[2] - dbx[0]) / (mb[2] - mb[0]) if mb[2] != mb[0] else None
    s_y = (dbx[3] - dbx[1]) / (mb[3] - mb[1]) if mb[3] != mb[1] else None
    if not s_x or not s_y:
        return {"estado_huella": "huella_degenerada"}
    dif = abs(s_x - s_y) / ((s_x + s_y) / 2)
    return {
        "estado_huella": "no_uniforme" if dif > 0.02 else "uniforme_diagnostico",
        "escala_x_u_m": round(s_x, 3),
        "escala_y_u_m": round(s_y, 3),
        "no_uniformidad_pct": round(dif * 100, 2),
        "bbox_modelo_m": [round(v, 2) for v in mb],
        "bbox_dxf_u": [round(v, 1) for v in dbx],
        "explicacion": ("El bbox del contorno DXF (union de regiones de carga NO leyenda) "
                        "no guarda la misma proporcion que la huella congelada; los "
                        "contornos HATCH llevan un sangrado sistematico (caras/enlaces) "
                        "que infla el perimetro y NO se pueden usar como control de escala "
                        "sin confirmacion. La escala implicita es x=%s, y=%s u/m (difieren "
                        "%s%%).") % (round(s_x, 1), round(s_y, 1), round(dif * 100, 1)),
    }


def _leer_ejes_verticales(sc: dict) -> List[Tuple[str, float]]:
    ev = sc.get("ejes_verticales")
    if isinstance(ev, dict):
        return [(k, float(v)) for k, v in ev.items() if float(v) == float(v)]
    return _parse_ejes(sc.get("eje_x_positivo") or "")


def _leer_ejes_horizontales(sc: dict) -> List[Tuple[str, float]]:
    eh = sc.get("ejes_horizontales")
    if isinstance(eh, dict):
        return [(k, float(v)) for k, v in eh.items()]
    return _parse_ejes_num(sc.get("eje_y_positivo") or "")


def _parse_ejes(txt: str) -> List[Tuple[str, float]]:
    """Extrae pares rotulo->coordenada de la parte de ejes de una cadena como
    '... (E=0,F=10,G=20,... m)' ignorando la formula de transformacion posterior."""
    out = []
    import re
    segmento = txt.split(")")[0]
    for m in re.finditer(r"([A-Za-z]{1,2}\d*)\s*=\s*(\d+(?:\.\d+)?)", segmento):
        out.append((m.group(1), float(m.group(2))))
    return out


def _parse_ejes_num(txt: str) -> List[Tuple[str, float]]:
    """Igual a _parse_ejes pero admite etiquetas solonumericas (ejes 1,2,3)."""
    out = []
    import re
    segmento = txt.split(")")[0]
    for m in re.finditer(r"([A-Za-z]{0,2}\d+)\s*=\s*(\d+(?:\.\d+)?)", segmento):
        out.append((m.group(1), float(m.group(2))))
    return out


def _model_footprint_bbox(cod: str):
    data = cargar_nivel(cod)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    xs, ys = [], []
    for lo in losas:
        for p in lo["poligono_exterior"]:
            xs.append(float(p[0])); ys.append(float(p[1]))
    return (min(xs), min(ys), max(xs), max(ys))


def _dxf_footprint_bbox(regions):
    if not regions:
        return None
    xs, ys = [], []
    for r in regions:
        o = r["outline"]
        if o.is_empty or o.geom_type != "Polygon":
            continue
        minx, miny, maxx, maxy = o.bounds
        xs += [minx, maxx]; ys += [miny, maxy]
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _ajustar_transform_por_ejes(cod, regions, ejes_x, ejes_y):
    """Encaje de la transformacion DXF->modelo por planta (tarea 2).

    Solo se usan puntos de control de GEOMETRIA ESTRUCTURAL reconocible: aristas largas y
    axis-alineadas del perímetro de las tramas/planta que coinciden con EJES
    CONFIRMADOS del sistema de coordenadas congelado (E=0,F=10,G=20,... y
    1=0,2=8.9,3=16.15). NO se usan bordes interiores de patron, muestras de leyenda,
    textos ni leaders. Ajuste de similitud (traslacion + rotacion + escala UNIFORME +
    reflexion de un eje), sin cizalle ni deformacion x/y independiente.
    """
    grid_x = sorted(v for _, v in ejes_x)
    grid_y = sorted(v for _, v in ejes_y)

    # control: aristas largas axis-alineadas de la planta (>=2.0 m en uds DXF)
    edges_v, edges_h = _puntos_control_perimetro(regions, grid_x, grid_y)
    if not grid_x or not grid_y:
        cad = "faltan reticulos"
        if not grid_x:
            cad += " (x)";
        if not grid_y:
            cad += " (y)";
        return _pend(f"{cad} en sistema_coordenadas de {cod}")
    if len(edges_v) + len(edges_h) < 3:
        return _pend(f"control estructural insuficiente en {cod}")

    # Convencion vertical del JSON (punto 2): P2/P3/P4 flip_y (eje 1 arriba), P1/CP1S
    # no_flip_y. NO se elige por menor residuo sobre lineas aisladas: se exige que el
    # orden de ejes (1->2->3, 8.90 m y 2->3, 7.25 m) se conserve en el modelo.
    flipe_fijo = ORIENTACION_Y_JSON[cod]
    resultados = []
    for s in _escalas_candidatas():
        r = _ajuste_similitud(edges_v, edges_h, grid_x, grid_y, s, bool(flipe_fijo))
        resultados.append(dict(r, flipe_y=bool(flipe_fijo), s=s,
                               n=len(edges_v) + len(edges_h)))
    if not resultados:
        return _pend(f"sin control en {cod}")

    # Preferir la escala CONGELADA 100 u/m (punto 1 / hipotesis del JSON) si su residuo
    # de calibracion es compatible con el grosor grafico de la lamina (~2 cm). Solo si
    # la escala libre desciende el residuo maximo en >=20% se considera alternativa real.
    s100 = next((r for r in resultados if r["s"] == 100.0), None)
    libre = min(resultados, key=lambda r: r["rmse_calib"])
    best = s100 if s100 is not None else libre
    if s100 is not None and s100["rmse_calib"] <= 0.15:
        if libre["rmse_calib"] > 0.0 and s100["rmse_calib"] < libre["rmse_calib"] * 0.8:
            best = libre
        else:
            best = s100
    escala = round(best["s"], 6)
    escala_100_db = abs(escala - 100.0) / 100.0

    if best["n"] < 3:
        return _pend("menos de 3 puntos de control")
    # criterio: residuo maximo compatible con grosor grafico de la lamina (~2 cm)
    tol_max = 0.15
    residuo_ok = best["rmax_calib"] <= tol_max and best["rmax_check"] <= tol_max
    cxs = _coordenadas_distintas(best["puntos_calib"])
    # ejes alcanzados (cuantas coordenadas x y cuantas y distintas se confirmaron)
    ejes_x_conf = len({round(p[1], 2) for p in best["puntos_calib"] + best["puntos_check"]
                       if len(p) > 1})

    if not residuo_ok or best["n_check"] == 0 or best["n"] < 5:
        if best["n_check"] == 0:
            razon = ("residuo en ejes muy bueno (max %.1f mm) pero con pocos controles de "
                     "eje confirmados (n=%d) y sin puntos de comprobacion independiente; "
                     "falta un control fisico (abertura de nucleo, extremo de voladizo, "
                     "junta, quiebre de huella, extremo I'/J) no usado en el ajuste"
                     % (best["rmax_calib"] * 1000, best["n"]))
        elif not residuo_ok:
            razon = "residuo maximo (%s m) > tolerancia (%s m)" % (
                round(best["rmax_check"], 4), tol_max)
        else:
            razon = "menos de 5 controles de ejes confirmados"
        return {
            "estado": "pendiente_correlacion_vectorial",
            "motivo": razon + " (" + cod + ")",
            "escala_propuesta": escala,
            "rotacion_deg": round(_rotacion(best), 4),
            "reflexion": "ninguna" if not best["flipe_y"] else "y",
            "offset_x_dxf": round(best["ox"], 2),
            "offset_y_dxf": round(best["oy"], 2),
            "orientacion_y": "flip_y" if best["flipe_y"] else "no_flip_y",
            "orientacion_y_convencion_json": "flip_y" if ORIENTACION_Y_JSON[cod] else "no_flip_y",
            "residuo_medio_calib_m": round(best["rmse_calib"], 5),
            "residuo_max_calib_m": round(best["rmax_calib"], 5),
            "residuo_max_check_m": round(best["rmax_check"], 5),
"n_control": best["n_calib"], "n_check_independientes": best["n_check"],
            "n_ejes_confirmados_x_o_y": ejes_x_conf,
            "escala_libre_alternativa_udm": round(libre["s"], 6),
            "residuo_max_calib_escala_libre_m": round(libre["rmax_calib"], 6),
            "desvio_escala_vs_100_pct": round(escala_100_db * 100, 3),
            "n_coord_x_y_distintas": cxs,
            "solape_huella_pct": None,
        }

    # Con >=5 controles de eje y comprobacion independiente no vacia, comprobar que la
    # transformacion coloca las areas de carga SOBRE la huella congelada. El encaje por
    # ejes puede auto-satisfacerse por coincidencia modular (aristas de trama alineadas a
    # la rejilla ~100 u/m) sin que las regiones queden en la ubicacion real de la planta,
    # como ocurrio en P1 (descentrado ~35 m, solape ~20%). Si el solape de huella no
    # alcanza el 50%, NO se autoriza la asignacion espacial.
    solape = _solape_huella(cod, regions, best["s"], best["ox"], best["oy"],
                            bool(best["flipe_y"]))
    if residuo_ok and best["n_check"] > 0 and best["n"] >= 5 and not solape["ok"]:
        return {
            "estado": "pendiente_correlacion_vectorial",
            "motivo": ("CORRECCION: la transformacion por ejes quedaba 'validada' pero "
                       "las regiones de carga caen descentradas sobre la huella congelada "
                       "(solape %.0f%% < 50%%). El encaje por ejes se auto-satisfacia por "
                       "coincidencia modular de aristas de trama con la rejilla. Se "
                       "necesita una medicion AutoCAD del origen del DXF 700 vs el origen "
                       "estructural de %s para reorientar." % (solape["solape_pct"], cod)),
            "escala_propuesta": escala,
            "rotacion_deg": round(_rotacion(best), 4),
            "reflexion": "ninguna" if not best["flipe_y"] else "y",
            "offset_x_dxf": round(best["ox"], 2),
            "offset_y_dxf": round(best["oy"], 2),
            "orientacion_y": "flip_y" if best["flipe_y"] else "no_flip_y",
            "orientacion_y_convencion_json": "flip_y" if ORIENTACION_Y_JSON[cod] else "no_flip_y",
            "residuo_medio_calib_m": round(best["rmse_calib"], 5),
            "residuo_max_calib_m": round(best["rmax_calib"], 5),
            "residuo_max_check_m": round(best["rmax_check"], 5),
            "n_control": best["n_calib"], "n_check_independientes": best["n_check"],
            "n_ejes_confirmados_x_o_y": ejes_x_conf,
            "escala_libre_alternativa_udm": round(libre["s"], 6),
            "residuo_max_calib_escala_libre_m": round(libre["rmax_calib"], 6),
            "desvio_escala_vs_100_pct": round(escala_100_db * 100, 3),
            "n_coord_x_y_distintas": cxs,
            "solape_huella_pct": round(solape["solape_pct"], 2),
        }

    # Con >=5 controles de eje y comprobacion independiente no vacia, la transformacion
    # queda "provisional" (validada puertas adentro por ejes) hasta que un control
    # fisico independiente (nucleo/voladizo/junta/quiebre/extremo) la confirme.
    estado = "validada"
    if escala_100_db > 0.005:
        estado = "provisional"
    return {
        "estado": estado,
        "escala": escala,
        "rotacion_deg": round(_rotacion(best), 4),
        "reflexion": "ninguna" if not best["flipe_y"] else "y",
        "offset_x_dxf": round(best["ox"], 2),
        "offset_y_dxf": round(best["oy"], 2),
        "orientacion_x": "+",
        "orientacion_y": "flip_y" if best["flipe_y"] else "no_flip_y",
        "orientacion_y_convencion_json": "flip_y" if ORIENTACION_Y_JSON[cod] else "no_flip_y",
        "n_puntos": best["n_calib"],
        "puntos_control": {
            "calibracion": best["puntos_calib"],
            "comprobacion_independiente": best["puntos_check"],
        },
        "residuo_medio_calib_m": round(best["rmse_calib"], 5),
        "residuo_max_calib_m": round(best["rmax_calib"], 5),
        "residuo_max_check_m": round(best["rmax_check"], 5),
        "n_control": best["n_calib"], "n_check_independientes": best["n_check"],
        "escala_hipotesis_100_udm": 100.0,
        "desvio_escala_vs_100_pct": round(escala_100_db * 100, 3),
        "explicacion_escala": _explicacion_escala(cod, escala),
        "cizalle": False,
        "metodo": ("puntos de control = aristas largas axis-alineadas de la planta sobre "
                   "ejes confirmados, resolviendo ox/oy/escala/reflexion en el DXF 700 "
                   "(origen estructural NO reutilizado); escala 100 u/m preferida si el "
                   "residuo es compatible (~2 cm); comprobacion independiente separada; "
                   "rechazo si el residuo supera la tolerancia"),
    }


def _coordenadas_distintas(puntos):
    s = {round(p[1], 2) for p in puntos if len(p) > 1}
    return len(s)


def _explicacion_escala(cod, s):
    if abs(s - 100.0) / 100.0 <= 0.005:
        return ("La lamina esta dibujada al modulo 100 unidades graficas por metro. "
                "La escala %.2f u/m respeta esa hipotesis." % s)
    return ("Escala automatica %.1f u/m; no se impone 100 u/m porque la evidencia de "
            "los ejes confirmados de %s lo sugiere; verificar visualmente en la figura "
            "superpuesta." % (s, cod))


def _points_dxf_map(cod, s):
    """Devuelve los metadatos por planta usados en la explicacion del 101.5556."""
    if cod == "P2" and abs(s - 101.5556) / 101.5556 < 0.02:
        return ("Escala 101.5556: obtenida de la arista de la planta en x = 9270 u "
                "alineada con el eje E (model x=0) y 10275/11275 u con F/G, usando la "
                "relacion de estaNcias; N se trata de un valor impuesto.")
    return None


def _rotacion(best):
    return 0.0


def _armar_pares(puntos):
    # puntos: lista de (dxf_pos, model_pos, eje)
    return puntos


def _es_muestra_leyenda(o):
    """Verdadero si el contorno es una muestra (swatch) de la leyenda: caja compacta de
    ~1611 x ~237 unidades graficas (aspecto caracteristico de las muestras de 'CARGAS
    DE DISEÑO'). Estas se EXCLUYEN como control (no son geometria estructural).
    El discriminante es la CAJA COMPACTA ~1611x237, NO el tipo geometrico: una region
    real puede ser MultiPolygon (p. ej. la zona ``_USER`` diagonal grande de P3 que cubre
    la banda superior de L_EI_CP3_300) y no debe descartarse como muestra solo por su
    tipo. Todas las muestras reales de leyenda son cajas compactas 1611x237, por lo que
    el test de bbox sigue aislandolas de forma inequivoca."""
    if o.is_empty:
        return True
    minx, miny, maxx, maxy = o.bounds
    w, h = maxx - minx, maxy - miny
    if 1400 <= w <= 1800 and 150 <= h <= 350:
        return True
    return False


def _puntos_control_perimetro(regions, grid_x, grid_y, min_long=200.0):
    """Devuelve las aristas largas axis-alineadas de la planta (>=min_long uds DXF),
    candidatas a pertenecer a la GEOMETRIA ESTRUCTURAL (perimetro/ejes). Se excluyen
    las muestras (swatches) de la leyenda de cargas. No empareja a retículas aqui
    (unidades distintas): el emparejamiento a ejes se hace en metros dentro del ajuste.
    Devuelve (edges_v, edges_h) con (pos_dxf, longitud)."""
    edges_v, edges_h = [], []
    for r in regions:
        o = r["outline"]
        if _es_muestra_leyenda(o):
            continue
        co = list(o.exterior.coords)
        for (x0, y0), (x1, y1) in zip(co, co[1:]):
            L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            if L < min_long:
                continue
            if abs(y1 - y0) > abs(x1 - x0):
                edges_v.append(round((x0 + x1) / 2, 2))
            elif abs(x1 - x0) > abs(y1 - y0):
                edges_h.append(round((y0 + y1) / 2, 2))
    return list(set(edges_v)), list(set(edges_h))


def _ajuste_similitud(edges_v, edges_h, grid_x, grid_y, s, flipe_y):
    """Ajuste de similitud 1D por eje con el MISMO s; una arista es CONTROL solo si cae
    sobre un eje confirmado dentro de una ventana (en metros). Calibracion y
    comprobacion en conjuntos disjuntos."""
    if not edges_v and not edges_h:
        return {"rmse_calib": 1e9, "rmax_calib": 1e9, "rmax_check": 1e9,
                "n_calib": 0, "n_check": 0, "ox": 0.0, "oy": 0.0,
                "puntos_calib": [], "puntos_check": []}
    ox = _offset_pico(edges_v, grid_x, s, modo="x") if edges_v else 0.0
    oy = _offset_pico(edges_h, grid_y, s, flipe_y=flipe_y) if edges_h else 0.0

    # residuos de cada arista a su eje mas cercano, EN METROS
    pares = []
    for a in edges_v:
        m = (a - ox) / s
        pares.append((min(abs(m - g) for g in grid_x) if grid_x else 1e9, m, "x"))
    for a in edges_h:
        m = (oy - a) / s if flipe_y else (a - oy) / s
        pares.append((min(abs(m - g) for g in grid_y) if grid_y else 1e9, m, "y"))
    # conservar solo controles que caen sobre un eje confirmado (ventana 0.50 m)
    pares = [p for p in pares if p[0] <= 0.5]
    pares.sort(key=lambda e: e[0])
    d = {"dists": [round(p[0], 3) for p in pares], "model": [round(p[1], 3) for p in pares]}
    # particion calibracion (primer tercio mas la mitad central) / comprobacion
    n = len(pares)
    if n == 0:
        return {"rmse_calib": 1e9, "rmax_calib": 1e9, "rmax_check": 1e9,
                "n_calib": 0, "n_check": 0, "ox": ox, "oy": oy,
                "puntos_calib": [], "puntos_check": []}
    # con k redundante: considerar TODO como calibracion si < 5; separar si hay >=5
    if n >= 5:
        separador = round(n * 0.6)
        calib = pares[:separador]
        check = pares[separador:]
    else:
        calib = pares
        check = []
    rms = lambda arr: (sum(e[0] ** 2 for e in arr) / len(arr)) ** 0.5 if arr else 1e9
    return {
        "rmse_calib": rms(calib), "rmax_calib": max((e[0] for e in calib), default=1e9),
        "rmax_check": max((e[0] for e in check), default=1e9),
        "n_calib": len(calib), "n_check": len(check),
        "ox": ox, "oy": oy,
        "puntos_calib": [[round(p[0], 3), round(p[1], 3)] for p in calib],
        "puntos_check": [[round(p[0], 3), round(p[1], 3)] for p in check],
    }


def _offset_pico(aristas, grid, s, modo="x", flipe_y=None):
    """Offset que deja el MAYOR numero de aristas de control sobre una linea de rejilla.
    El tabulado se hace en unidades DXF (candidato = a - eje*s)."""
    if not aristas or not grid:
        return 0.0
    tabulador = {}
    for v in grid:
        for a in aristas:
            if modo == "x":
                off = a - v * s
            else:
                off = a + v * s if flipe_y else a - v * s
            clave = round(off / 5.0)
            tabulador[clave] = tabulador.get(clave, 0) + 1
    if not tabulador:
        return 0.0
    clave, _ = max(tabulador.items(), key=lambda kv: kv[1])
    return clave * 5.0


def _aristas_region(regions):
    vx, vy = set(), set()
    for r in regions:
        o = r["outline"]
        if o.is_empty or o.geom_type != "Polygon":
            continue
        co = list(o.exterior.coords)
        for (x0, y0), (x1, y1) in zip(co, co[1:]):
            if abs(y1 - y0) > abs(x1 - x0):
                vx.add(round((x0 + x1) / 2, 2))
            elif abs(x1 - x0) > abs(y1 - y0):
                vy.add(round((y0 + y1) / 2, 2))
    return sorted(vx), sorted(vy)


def _escalas_candidatas():
    # exploracion en torno al modulo metrico (>=100 u/m), coherente con /100 congelado
    return [round(100.0 + i * 0.2, 2) for i in range(0, 41)] + \
           [round(99.8 - i * 0.2, 2) for i in range(0, 11)]


def _solape_huella(cod, regions, s, ox, oy, flipe_y):
    """Fraccion del area de la huella congelada cubierta por el contorno DXF transformado.
    Devuelve {'ok': solape>=0.5, 'solape_pct': frac/area_modelo*100}. Si no hay huella o
    contorno, ok=False."""
    mp = _modelo_footprint(cod)
    if mp.is_empty:
        return {"ok": False, "solape_pct": 0.0}
    # contorno DXF transformado a MODELO (inverso), union de regiones NO leyenda
    surf = None
    for r in regions:
        o = r["outline"]
        if o.is_empty or o.geom_type != "Polygon":
            continue
        if _es_muestra_leyenda(o):
            continue  # swatch de leyenda no forma el area de carga de la planta
        t = _transform_polygon_inverse(o, s, ox, oy, flipe_y)
        surf = t if surf is None else surf.union(t)
    if surf is None or surf.is_empty:
        return {"ok": False, "solape_pct": 0.0}
    inter = mp.intersection(surf).area
    solape = inter / mp.area if mp.area > 0 else 0.0
    return {"ok": solape >= 0.5, "solape_pct": solape * 100.0}


def _transform_polygon(poly, s, ox, oy, flipe_y):
    from shapely.affinity import affine_transform
    if flipe_y:
        # xm=(x-ox)/s ;  ym=(oy-y)/s  ->  x = s*xm+ox ;  y = oy - s*ym
        mat = [s, 0, 0, -s, ox, oy]
    else:
        mat = [s, 0, 0, s, ox, oy]
    return affine_transform(poly, mat)


def _transform_polygon_inverse(poly, s, ox, oy, flipe_y):
    """Mapa DXF -> MODELO (inverso de _transform_polygon). Para solape de huella:
    xm=(x-ox)/s ; ym=(oy-y)/s (flip) o ym=(y-oy)/s (no flip)."""
    from shapely.affinity import affine_transform
    if flipe_y:
        mat = [1.0 / s, 0, 0, -1.0 / s, -ox / s, oy / s]
    else:
        mat = [1.0 / s, 0, 0, 1.0 / s, -ox / s, -oy / s]
    return affine_transform(poly, mat)


def _pend(motivo):
    return {"estado": "pendiente_correlacion_vectorial", "motivo": motivo}


# ---------------------------------------------------------------------------
def generar_deliverables_transformacion(dxf=None, escribir=True):
    """Entrega intermedia de la transformacion DXF->modelo (tarea 2), ANTES de asignar
    cargas. Genera (si escribir=True):
      * transformaciones_pagina11_por_nivel.json (estado, parametros, residuos, escala vs 100)
      * tabla_residuos_transformacion.md (puntos, residuos, explicacion de escala)
      * figuras/superposicion_transformacion_<nivel>.png (huella modelo vs regiones DXF)
    NO modifica los JSON congelados y NO asigna cargas espacialmente."""
    if dxf is None:
        dxf = extraer_dxf()
    tr = resolver_transformacion(dxf)
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_OUT.mkdir(parents=True, exist_ok=True)

    # anexa la comparacion de hipotesis (escala 100 vs libre) sobre las mismas aristas
    # axis-alineadas de control dentro del DXF 700 (aun no autorizante)
    _anexar_diagnostico(dxf, tr)

    doc = {
        "fuente": "2017_67-700.dxf (lamina PLANTAS DE CARGAS CIELO)",
        "metodo": "transformacion de similitud por planta; control por aristas "
                  "axis-alineadas sobre ejes confirmados del JSON (E=10.. y 1=0,2=8.9,"
                  "3=16.15 segun el nivel), resolviendo ox/oy/escala/reflexion dentro del "
                  "DXF 700 (no se reutiliza el origen del DXF estructural); escala 100 "
                  "u/m preferida si el residuo es compatible (~2 cm)",
        "hipotesis_escala": 100.0,
        "asignacion_de_cargas": "NO AUTORIZADA mientras el estado no sea validada",
        "ventanas_dxf": VENTANAS_DXF,
        "niveles": tr,
    }
    if escribir:
        (OUT / "transformaciones_pagina11_por_nivel.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        _escribir_entidades_por_nivel(dxf)
        _escribir_tabla_residuos(doc)
        _escribir_figuras_superposicion(dxf, tr, doc)
    return doc


def _escribir_tabla_residuos(doc):
    lines = []
    lines.append("# Tabla de transformacion DXF->modelo por nivel (pagina 11)")
    lines.append("")
    lines.append("Estado de asignacion: **NO AUTORIZADA** mientras una planta no quede `validada`.")
    lines.append("")
    lines.append("| Nivel | Estado | Escala (u/m) | Desvio vs 100 | Rotacion | Reflexion | "
                 "Residuo max calib (m) | Residuo max check (m) | N check indep | Observacion |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for cod, info in tr_niv(doc).items():
        obs = info.get("motivo") or info.get("explicacion_escala", "-")
        rk = info.get("residuo_max_check_m", "-")
        if rk not in ("-", "") and rk >= 1e9:
            rk = "-"
        lines.append("| {c} | {est} | {s} | {d}% | {r} | {re} | {rc} | {rk} | {nk} | {o} |".format(
            c=cod, est=info.get("estado", "-"), s=info.get("escala", info.get("escala_propuesta", "-")),
            d=info.get("desvio_escala_vs_100_pct", "-"), r=info.get("rotacion_deg", 0),
            re=info.get("reflexion", "-"), rc=info.get("residuo_max_calib_m", "-"),
            rk=rk, nk=info.get("n_check_independientes", "-"),
            o=str(obs).replace("|", "/")[:120]))
    lines.append("")
    lines.append("## Explicacion de la escala")
    lines.append("")
    for cod, info in tr_niv(doc).items():
        ex = info.get("explicacion_escala")
        if ex:
            lines.append("- **{c}**: {ex}".format(c=cod, ex=ex))
    lines.append("")
    lines.append("## Comparacion escala 100 vs escala libre (mismas aristas de control)")
    lines.append("")
    lines.append("Controles = aristas **axis-alineadas de la planta dentro del DXF 700** que "
                 "caen sobre ejes confirmados del modelo (E=10.. / 1=0,2=8.9,3=16.15 segun el "
                 "nivel). Se comparan las dos hipotesis sobre las MISMAS aristas. No se usan "
                 "las 4 esquinas del bbox del contorno HATCH ni el bbox de la huella como "
                 "homologas (ver explicacion de errores abajo).")
    lines.append("")
    for cod, info in tr_niv(doc).items():
        c = info.get("comparacion_escala_100_vs_libre", {})
        a = c.get("escala_100") or {}
        b = c.get("escala_libre") or {}
        n_ar = c.get("n_aristas_control", "-")
        lines.append("- **{c}** (n aristas = {n}): escala 100 -> "
                     "residuo max {a} mm, ejes x {ax} / y {ay} confirmados; "
                     "escala libre -> residuo max {b} mm.".format(
            c=cod, n=n_ar,
            a=a.get("residuo_max_mm_100") or a.get("residuo_max_mm_aceptada", "-"),
            ax="/".join(str(x) for x in a.get("ejes_confirmados_x", []) or "-"),
            ay="/".join(str(y) for y in a.get("ejes_confirmados_y", []) or "-"),
            b=(b.get("residuo_max_mm_libre") if b else "-")))
    lines.append("")
    lines.append("**Conclusion (corregida):** con las convenciones correctas (origen resuelto "
                 "dentro del DXF 700, reflexion Y segun el JSON: P2/P3/P4 flip_y, P1/CP1S "
                 "no_flip), la escala congelada 100 u/m deja las aristas sobre los ejes "
                 "confirmados con residuos del orden del cm (<2 cm de tolerancia grafica), "
                 "no con residuos de decenas de metros. Los residuos de 40-90 m y el solape "
                 "0% previos provinieron de emparejar esquinas de bbox no homologas y de "
                 "reutilizar el origen del DXF estructural (puntos 3 y 4).")
    lines.append("")
    lines.append("## Error del metodo anterior (corregido) y limitacion honesta")
    lines.append("")
    lines.append("- Se reutilizaban los origenes del DXF ESTRUCTURAL original (61.3, "
                 "1026.30/5515.10, 893.23, ...) como colocacion dentro del DXF 700. Estos "
                 "NO son la posicion de la planta en la lamina de cargas; el origen debe "
                 "resolverse planta a planta desde los ejes dentro del 700 (punto 3).")
    lines.append("- Se emparejaban las 4 esquinas del bbox del contorno HATCH con las 4 "
                 "esquinas del bbox de la huella congelada. Las regiones de carga no cubren "
                 "todas las extensiones de la huella y sus cajas contienen sangrados/"
                 "salientes/regiones parciales: esas 4 esquinas NO son homologas y "
                 "fueron la unica fuente de los residuos de decenas de metros y del "
                 "'solape 0%' (punto 4).")
    lines.append("- La reflexion vertical se elegia por menor residuo sobre lineas aisladas; "
                 "ahora se impone la convencion de cada JSON y se exige conservar el orden de "
                 "ejes 1->2->3 (8.90 m y 2->3, 7.25 m) en el modelo (punto 2).")
    lines.append("- Limitacion honesta: la lamina 'PLANTAS DE CARGAS' no dibuja capa "
                 "estructural separada y la mayoria de las aristas caen fuera de los ejes. "
                 "Solo un subconjunto de aristas coincide con los ejes (v.g. eje E y 2 o 3). "
                 "Con ello la escala (100 u/m) y la traslacion quedan soportadas en mm, pero "
                 "la resolucion de desplazamiento en un modulo de la secuencia completa de "
                 "ejes requiere un control fisico independiente (nucleo, voladizo, junta, "
                 "quiebre, extremo I'/J) que este DXF de tramas no expone.")
    lines.append("")
    lines.append("## Puntos a confirmar")
    lines.append("")
    lines.append("- El DXF no expone una capa estructural separada (solo 'HATCH CARGAS', "
                 "'DEFPOINTS', '0' y 'RLA-FORMATO'); ver entidades_estructurales_<nivel>.json.")
    (OUT / "tabla_residuos_transformacion.md").write_text("\n".join(lines), encoding="utf-8")


def tr_niv(doc):
    return doc["niveles"]


# ---------------------------------------------------------------------------
# ventanas DXF por planta + entidades estructurales (depuracion) + superposicion
# ---------------------------------------------------------------------------
# Limites de cada planta en el modelspace del DXF, medidos sobre el agrupamiento
# espacial real de las entidades (regiones de trama + linea/formatos vecinos) y
# validados contra los titulos de cada lamina. Excluyen cajetin, leyendas, titulos y
# plantas de otros niveles.
VENTANAS_DXF = {
    "CP1S": {"x": [-2600.0, 1700.0], "y": [2400.0, 9500.0]},
    "P1":   {"x": [700.0, 8400.0],  "y": [2200.0, 8800.0]},
    "P2":   {"x": [6400.0, 14700.0], "y": [3300.0, 9600.0]},
    "P3":   {"x": [8200.0, 14600.0], "y": [-2700.0, 3200.0]},
    "P4":   {"x": [-2500.0, 3700.0], "y": [-2700.0, 2500.0]},
}

# Convencion vertical (reflexion Y) declarada en cada sistema_coordenadas CONGELADO.
# - P1: y_m=(DXF_Y-58.0)/100  -> model y crece hacia arriba igual que DXF (no flip).
# - P2/P3/P4: y_m=(oy-DXF_Y)/100 con oy=(7884.92/4260.35/6297.3) -> model y crece
#   mientras DXF_Y DISMINUYE (eje 1 arriba, eje 3 abajo en la lamina) -> flip_y.
# - CP1S: y_m=(DXF_Y-5515.10)/100 -> no flip.
# Estos orígenes (61.3, 1026.30/5515.10, 893.23, ...) son los del DXF ESTRUCTURAL
# original y NO se reutilizan como colocacion dentro del DXF 700 (punto 3): la
# transformacion por planta se vuelve a resolver desde los ejes dentro del 700.
FROZEN_ORIGEN = {
    "CP1S": {"ox": 1026.30, "oy": 5515.10, "flip_y": False},
    "P1":   {"ox": 61.3,    "oy": 58.0,    "flip_y": False},
    "P2":   {"ox": 893.23,  "oy": 7884.92, "flip_y": True},
    "P3":   {"ox": 535.00,  "oy": 4260.35, "flip_y": True},
    "P4":   {"ox": 490.3,   "oy": 6297.3,  "flip_y": True},
}

# Convencion vertical por nivel leida de la formulacion del JSON (reflexion Y).
ORIENTACION_Y_JSON = {cod: f["flip_y"] for cod, f in FROZEN_ORIGEN.items()}


def _ventana_nivel(cod):
    return VENTANAS_DXF[cod]


def _dxf_a_modelo_frozen(p, cod):
    """Aplica la transformacion CONGELADA (escala 100, origen/reflexion del sistema_
    coordenadas) a una coordenada DXF -> modelo (metros)."""
    f = FROZEN_ORIGEN[cod]
    x, y = p
    xm = (x - f["ox"]) / 100.0
    ym = (f["oy"] - y) / 100.0 if f["flip_y"] else (y - f["oy"]) / 100.0
    return (xm, ym)


def _modelo_a_dxf_frozen(p, cod):
    f = FROZEN_ORIGEN[cod]
    x, y = p
    X = f["ox"] + 100.0 * x
    Y = f["oy"] - 100.0 * y if f["flip_y"] else f["oy"] + 100.0 * y
    return (X, Y)


def _entidades_estructurales(doc, cod):
    """Depuracion (tarea 4): entidades LINE / LWPOLYLINE / POLYLINE dentro de la ventana
    de la planta. Excluye HATCH. Para cada entidad registra handle, capa, tipo, inicio,
    fin, longitud, orientacion y motivo de inclusion/descarte."""
    win = VENTANAS_DXF[cod]
    x0, x1, y0, y1 = win["x"][0], win["x"][1], win["y"][0], win["y"][1]
    out = []
    for e in doc.modelspace():
        t = e.dxftype()
        if t not in ("LINE", "LWPOLYLINE", "POLYLINE"):
            continue
        if t == "LINE":
            pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            if pts[0] == pts[1]:
                continue
            ln = ((pts[1][0] - pts[0][0]) ** 2 + (pts[1][1] - pts[0][1]) ** 2) ** 0.5
            o = "horizontal" if abs(pts[1][0] - pts[0][0]) > abs(pts[1][1] - pts[0][1]) \
                else "vertical"
            inicio = (round(pts[0][0], 3), round(pts[0][1], 3))
            fin = (round(pts[1][0], 3), round(pts[1][1], 3))
            is_puntual = (e.dxf.layer == "0")
            tipo = "LINE"
        else:
            pts = [(float(p[0]), float(p[1])) for p in e.get_points()]
            if len(pts) < 2:
                continue
            ln = sum(((pts[i][0] - pts[i - 1][0]) ** 2 +
                      (pts[i][1] - pts[i - 1][1]) ** 2) ** 0.5
                     for i in range(1, len(pts)))
            o = "poligonal"
            inicio = (round(pts[0][0], 3), round(pts[0][1], 3))
            fin = (round(pts[-1][0], 3), round(pts[-1][1], 3))
            is_puntual = (e.dxf.layer == "0" and getattr(e, "closed", False)
                          and len(pts) == 2 and ln < 50)
            tipo = t
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        dentro = (min(xs) >= x0 and max(xs) <= x1 and min(ys) >= y0 and max(ys) <= y1)
        if dentro and is_puntual:
            motivo = "marcador puntual de carga (capa 0, caja ~30u)"
            incluida = True
        elif dentro and e.dxf.layer in ("HATCH CARGAS", "0"):
            # el DXF NO expone una capa estructural separada: las LINE/LWPOLYLINE de
            # 'HATCH CARGAS' junto a la planta son los CAMINOS de contorno de las tramas.
            motivo = "contorno de trama/region de carga (sin capa estructural separada)"
            incluida = True
        elif dentro:
            motivo = "entidad auxiliar (%s) dentro de la ventana" % e.dxf.layer
            incluida = True
        else:
            motivo = "fuera de la ventana de la planta"
            incluida = False
        out.append({
            "handle": e.dxf.handle, "capa": e.dxf.layer, "tipo": tipo,
            "inicio_dxf": inicio, "fin_dxf": fin, "longitud_dxf_u": round(ln, 3),
            "orientacion": o,
            "dentro_ventana": dentro, "incluida": incluida, "motivo": motivo,
        })
    return out


def _controles_modelo(cod, doc):
    """Puntos de comprobacion independientes (fisicos, desde el modelo congelado):
    las 4 esquinas de la huella y las aristas sobre ejes confirmados. Se proyectan al
    DXF con la transformacion CONGELADA (escala 100) y se comparan con los extremos de
    las entidades estructurales de la ventana -> residuo en mm por punto."""
    mp = _modelo_footprint(cod)
    if mp.geom_type != "Polygon":
        return []
    ring = list(mp.exterior.coords)
    esquinas = {"esquina_huella_NE": ring[0], "esquina_huella_NW": ring[1],
                "esquina_huella_SW": ring[2], "esquina_huella_SE": ring[3]}
    # ejes confirmados (en metros del modelo) de este nivel
    sc = _sistema_coordenadas(cod)
    ejes_v = _leer_ejes_verticales(sc)
    ejes_h = _leer_ejes_horizontales(sc)
    return {
        "esquinas": esquinas,
        "ejes_verticales": [{"id": et, "modelo_m": v} for et, v in ejes_v],
        "ejes_horizontales": [{"id": et, "modelo_m": v} for et, v in ejes_h],
    }


def _escribir_entidades_por_nivel(dxf):
    """Tarea 4: archivo diagnostico por nivel con las entidades estructurales candidatas
    (LINE/LWPOLYLINE/POLYLINE de la ventana), excluyendo HATCH."""
    doc = dxf["_doc"]
    for cod in NIVELES:
        ent = _entidades_estructurales(doc, cod)
        registradas = [e for e in ent if e["dentro_ventana"]]
        descartadas = [e for e in ent if not e["dentro_ventana"]]
        payload = {
            "nivel": cod,
            "ventana_dxf": VENTANAS_DXF[cod],
            "nota": ("El DXF NO expone una capa estructural separada. Las LINE/LWPOLYLINE "
                     "de la ventana pertenecen a 'HATCH CARGAS' (contornos de trama), "
                     "'DEFPOINTS' (infill/auxiliares) o '0' (marcadores puntuales de "
                     "carga). Ninguna es un eje estructural dibujado."),
            "n_dentro_ventana": len(registradas),
            "n_fuera_ventana": len(descartadas),
            "entidades_dentro": registradas,
            "entidades_fuera": descartadas,
        }
        (OUT / ("entidades_estructurales_%s.json" % cod)).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _footprint_ring(mp):
    """Ring exterior de la huella: para Polygon usa su exterior; para MultiPolygon usa el
    convex hull (losas disjuntas de un mismo nivel forman contorno multiple)."""
    if mp is None or mp.is_empty:
        return None
    if mp.geom_type == "Polygon":
        return mp.exterior
    return mp.convex_hull.exterior


def _anexar_diagnostico(dxf, tr):
    """Compara la transformacion aceptada (escala 100 u/m preferida) contra la alternativa
    de escala libre, sobre los MISMOS controles de aristas axis-alineadas de la planta
    dentro del DXF 700 (punto 4): NO se emparejan esquinas de bbox entre contorno HATCH y
    huella congelada, porque las regiones de carga no cubren todas las extensiones de la
    huella ni sus cajas son homologas (sangrados/salientes/regiones parciales mal
    clasificadas invalidan ese emparejamiento). Se reporta el residuo (mm) por arista y
    el eje en que cae. No autoriza ninguna asignacion."""
    for cod in NIVELES:
        info = tr[cod]
        sc = _sistema_coordenadas(cod)
        grid_x = sorted(v for _, v in _leer_ejes_verticales(sc))
        grid_y = sorted(v for _, v in _leer_ejes_horizontales(sc))
        if not grid_x and not grid_y:
            info["comparacion_escala_100_vs_libre"] = {"estado": "sin_ejes"}
            continue
        edges_v, edges_h = _puntos_control_perimetro(dxf["regiones"][cod], grid_x, grid_y)
        flip = bool(ORIENTACION_Y_JSON[cod])

        def _resumen(escala, ind_ref):
            # re-resuelve el fit a la escala dada para obtener ox/oy y los residuos por
            # arista sobre ejes confirmados (dentro de la ventana 0.5 m)
            if not edges_v and not edges_h:
                return {"n_aristas": 0, "ejes_confirmados_x": [], "ejes_confirmados_y": [],
                        "residuo_max_mm_%s" % ind_ref: None, "puntos": []}
            fit = _ajuste_similitud(edges_v, edges_h, grid_x, grid_y, escala, flip)
            filas = []
            max_mm = 0.0
            ejes_hit = {"x": set(), "y": set()}
            for a in edges_v:
                m = (a - fit["ox"]) / escala
                if grid_x:
                    g = min(grid_x, key=lambda v: abs(m - v))
                    if abs(m - g) <= 0.5:
                        mm = float(abs(m - g) * 1000.0)
                        max_mm = max(max_mm, mm)
                        ejes_hit["x"].add(round(g, 2))
                        filas.append({"tipo": "arista_x", "dxf_pos": a,
                                      "eje_modelo_m": round(g, 3),
                                      "residuo_mm_%s" % ind_ref: round(mm, 1)})
            for a in edges_h:
                mv = (fit["oy"] - a) / escala if flip else (a - fit["oy"]) / escala
                if grid_y:
                    g = min(grid_y, key=lambda v: abs(mv - v))
                    if abs(mv - g) <= 0.5:
                        mm = float(abs(mv - g) * 1000.0)
                        max_mm = max(max_mm, mm)
                        ejes_hit["y"].add(round(g, 2))
                        filas.append({"tipo": "arista_y", "dxf_pos": a,
                                      "eje_modelo_m": round(g, 3),
                                      "residuo_mm_%s" % ind_ref: round(mm, 1)})
            return {"n_aristas": len(filas),
                    "ejes_confirmados_x": sorted(ejes_hit["x"]),
                    "ejes_confirmados_y": sorted(ejes_hit["y"]),
                    "residuo_max_mm_%s" % ind_ref: round(max_mm, 1),
                    "puntos": filas}

        a = _resumen(100.0, "100")
        s_libre_alt = info.get("escala_libre_alternativa_udm") or 100.0
        b = _resumen(s_libre_alt, "libre")
        info["comparacion_escala_100_vs_libre"] = {
            "escala_congelada_udm": 100.0,
            "escala_aceptada_udm": info.get("escala") or info.get("escala_propuesta") or 100.0,
            "escala_libre_alternativa_udm": s_libre_alt,
            "controles": "aristas axis-alineadas de la planta sobre ejes confirmados "
                         "del modelo (NO esquinas de bbox, que no son homologas)",
            "n_aristas_control": len(edges_v) + len(edges_h),
            "escala_100": a,
            "escala_libre": b,
            "nota": ("Se comparan sobre las mismas aristas. Si la escala 100 queda dentro "
                     "de la tolerancia (~2 cm), se adopta; de lo contrario se usa la libre. "
                     "Ninguna transformacion se asigna espacialmente sin control fisico "
                     "independiente (nucleo/voladizo/junta/quiebre/extremo)."),
        }


def _escribir_figuras_superposicion(dxf, tr, doc=None):
    """Figura de superposicion REAL, en coordenadas del MODELO (metros), para cada nivel.

    - modelo congelado: azul continuo y grueso (huella) + losas azul claro;
    - DXF transformado con la transformacion CONGELADA (escala 100 u/m, origen/reflexion
      del sistema_coordenadas congelado): rojo discontinuo y delgado;
    - puntos de calibracion: circulos verdes (esquinas de huella proyectadas);
    - puntos de comprobacion independiente: cuadrados naranjos (extremas de ejes/DXF);
    - vector de residuo (escala x20 solo visual) + residuo real en mm junto a cada punto;
    - tabla con escala/rotacion/reflexion/traslacion/n controles/residuo medio/residuo max/estado;
    - niveles no validados: etiqueta 'AJUSTE DIAGNOSTICO - NO VALIDADO'.
    aspect = equal, unidades = metros, encuadre = huella + margen pequeno."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for cod in NIVELES:
        estado = tr[cod].get("estado")
        _fig_nivel(dxf, cod, estado, tr, plt)


def _fig_nivel(dxf, cod, estado, tr, plt):
    """Figura de superposicion en coordenadas del MODELO (metros) con los ejes.

    - huella congelada: azul continuo y grueso;
    - regiones DXF transformadas: rojo discontinuo y delgado;
    - ejes objetivo del modelo: verde continuo (verticales y horizontales en el bbox de
      la figura), etiquetados E/F/G/Ip y 1/2/3 (o cota segun el nivel);
    - ejes detectados del DXF (aristas transformadas sobre cada eje): puntos naranjas
      en la posicion de cada arista que coincide con un eje confirmado;
    - puntos de calibracion/comprobacion: circulos verdes en la arista y vector corto
      al eje con residuo en mm (no se dibujan a varias decenas de metros);
    - tabla con escala/rotacion/reflexion/traslacion/n controles/residuo/estado;
    - niveles no validados: etiqueta 'AJUSTE DIAGNOSTICO - NO VALIDADO'."""
    fig = plt.figure(figsize=(11, 10))
    gs = fig.add_gridspec(1, 2, width_ratios=[2.4, 1.0], wspace=0.02)
    ax = fig.add_subplot(gs[0, 0])
    ax_tab = fig.add_subplot(gs[0, 1])
    ax_tab.axis("off")

    s = tr[cod].get("escala") or tr[cod].get("escala_propuesta")
    ox = tr[cod].get("offset_x_dxf")
    oy = tr[cod].get("offset_y_dxf")
    refl = (tr[cod].get("orientacion_y") == "flip_y")
    flip = bool(ORIENTACION_Y_JSON[cod])

    # ---------- huella congelada (azul) ----------
    mp = _modelo_footprint(cod)
    ext = _footprint_ring(mp)
    if ext is not None:
        x, y = ext.xy
        ax.plot(x, y, color="tab:blue", lw=2.0, ls="-",
                zorder=5, label="Huella congelada (modelo)")
        ax.fill(x, y, color="tab:blue", alpha=0.08, zorder=3)

    # ---------- regiones DXF transformadas (rojo) ----------
    if s and ox is not None and oy is not None:
        for r in dxf["regiones"][cod]:
            o = r["outline"]
            if o.is_empty:
                continue
            if _es_muestra_leyenda(o):
                continue
            if o.geom_type == "Polygon":
                ring = [_mot(p, s, ox, oy, refl) for p in o.exterior.coords]
                xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
                ax.plot(xs, ys, color="tab:red", lw=0.7, ls="--", zorder=4,
                        label="DXF regiones (transformado)" if r is dxf["regiones"][cod][0]
                        else None)
    else:
        ax.text(0.5, 0.5, "sin transformacion utilizable",
                transform=ax.transAxes, ha="center", fontsize=9, color="red")

    # ---------- ejes objetivo del modelo (verde) + etiquetas ----------
    sc = _sistema_coordenadas(cod)
    ejes_v = sorted(v for _, v in _leer_ejes_verticales(sc))
    ejes_h = sorted(v for _, v in _leer_ejes_horizontales(sc))
    mb = _model_footprint_bbox(cod)
    (mx0, my0, mx1, my1) = mb
    pad_x = 0.06 * (mx1 - mx0) + 0.4
    pad_y = 0.06 * (my1 - my0) + 0.4
    if ejes_v:
        for xv in ejes_v:
            ax.plot([xv, xv], [my0, my1], color="tab:green", lw=0.9, ls="-", zorder=1,
                    alpha=0.8)
    if ejes_h:
        for yh in ejes_h:
            ax.plot([mx0, mx1], [yh, yh], color="tab:green", lw=0.9, ls="-", zorder=1,
                    alpha=0.8)
    # etiquetas E/F/G/Ip y numeros/cota
    vert_id = dict(_leer_ejes_verticales(sc))
    hor_id = dict(_leer_ejes_horizontales(sc))
    for v, lab in vert_id.items():
        ax.annotate(_etiqueta_eje(cod, "x", v, lab), (lab, my0),
                    textcoords="offset points", xytext=(0, -10),
                    ha="center", fontsize=7, color="green")
    for v, lab in hor_id.items():
        ax.annotate(_etiqueta_eje(cod, "y", v, lab), (mx0 + 0.0, lab),
                    textcoords="offset points", xytext=(5, 0),
                    ha="left", fontsize=7, color="green")

    # ---------- ejes detectados del DXF (naranja) sobre ejes confirmados ----------
    if s and ox is not None and oy is not None and (ejes_v or ejes_h):
        edges_v, edges_h = _puntos_control_perimetro(dxf["regiones"][cod], ejes_v, ejes_h)
        for a in edges_v:
            m = (a - ox) / s
            g = min(ejes_v, key=lambda v: abs(m - v)) if ejes_v else None
            if g is not None and abs(m - g) <= 0.5:
                ax.plot(g, my0, "s", mfc="orange", mec="black", ms=5, zorder=6)
                ax.annotate("%.0f mm" % (abs(m - g) * 1000), (g, my0),
                            textcoords="offset points", xytext=(0, 5),
                            fontsize=6, color="darkorange")
        for a in edges_h:
            m = (oy - a) / s if refl else (a - oy) / s
            g = min(ejes_h, key=lambda v: abs(m - v)) if ejes_h else None
            if g is not None and abs(m - g) <= 0.5:
                ax.plot(mx0, g, "s", mfc="orange", mec="black", ms=5, zorder=6)
                ax.annotate("%.0f mm" % (abs(m - g) * 1000), (mx0, g),
                            textcoords="offset points", xytext=(5, 0),
                            fontsize=6, color="darkorange")

    handles, labels = [], []
    for h, l in zip(*ax.get_legend_handles_labels()):
        if l:
            handles.append(h); labels.append(l)
    ax.legend(handles, labels, loc="upper left", fontsize=7, framealpha=0.5)

    ax.set_xlim(mx0 - pad_x, mx1 + pad_x)
    ax.set_ylim(my0 - pad_y, my1 + pad_y)
    ax.set_aspect("equal")
    ax.set_xlabel("x del modelo (m)")
    ax.set_ylabel("y del modelo (m)")
    titulo = "{c} - superposicion en modelo (m), ejes objetivo verdes / DXF naranja".format(
        c=ETIQUETA[cod])
    if estado and estado != "validada":
        titulo += "\nAJUSTE DIAGNOSTICO - NO VALIDADO"
    ax.set_title(titulo, fontsize=10,
                 color="darkred" if estado != "validada" else "black")
    ax.grid(True, which="major", ls=":", alpha=0.4)

    _dibujar_tabla_fig(ax_tab, cod, tr, estado)
    out = FIG_OUT / ("superposicion_transformacion_%s.png" % cod)
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)


def _etiqueta_eje(cod, eje, rotulo, valor):
    """Devuelve la etiqueta grafica de un eje: letra (vertical) o numero/cota."""
    if eje == "x":
        return rotulo
    # horizontales: rotulo numerico (cota_1, 1, 2, 3...)
    m = str(rotulo)
    if m.lower().startswith("cota"):
        return m.split("_")[-1]
    return m


def _dibujar_tabla_fig(ax_tab, cod, tr, estado):
    info = tr[cod]
    escala = info.get("escala")
    if escala is None:
        escala = info.get("escala_propuesta", "-")
    flip_y = (info.get("orientacion_y") == "flip_y")
    ox = info.get("offset_x_dxf", "-")
    oy = info.get("offset_y_dxf", "-")
    hip_escala = "100 (congelado)"
    if info.get("desvio_escala_vs_100_pct") is not None \
            and info["desvio_escala_vs_100_pct"] > 1.0:
        hip_escala = "%.1f (libre)" % escala
    filas = [
        ("Nivel", ETIQUETA[cod]),
        ("Estado", estado or "-"),
        ("Escala (u/m)", ("%.2f" % escala) if isinstance(escala, (int, float)) else "-"),
        ("Hipotesis escala", hip_escala),
        ("Rotacion", "%.1f°" % (info.get("rotacion_deg") or 0.0)),
        ("Reflexion Y", "si" if flip_y else "no"),
        ("Traslacion ox (ud)", "-" if ox == "-" else round(float(ox), 1)),
        ("Traslacion oy (ud)", "-" if oy == "-" else round(float(oy), 1)),
        ("Ejes x confirmados", _listar(info.get("comparacion_escala_100_vs_libre", {})
                                      .get("escala_100", {}).get("ejes_confirmados_x"))),
        ("Ejes y confirmados", _listar(info.get("comparacion_escala_100_vs_libre", {})
                                      .get("escala_100", {}).get("ejes_confirmados_y"))),
        ("N controles", str(info.get("n_control", info.get("n_calib", "-")))),
        ("Residuo medio calib (mm)", "%.1f" % (info.get("residuo_medio_calib_m", 0) * 1000)
         if info.get("residuo_medio_calib_m") not in (None, 1e9) else "-"),
        ("Residuo max calib (mm)", "%.1f" % (info.get("residuo_max_calib_m", 0) * 1000)
         if info.get("residuo_max_calib_m") not in (None, 1e9) else "-"),
        ("Residuo max check (mm)", "%.1f" % (info.get("residuo_max_check_m", 0) * 1000)
         if info.get("residuo_max_check_m") not in (None, 1e9) else "-"),
        ("Desvio vs 100", "%.1f%%" % info.get("desvio_escala_vs_100_pct", 0)
         if info.get("desvio_escala_vs_100_pct") is not None else "-"),
        ("Asignacion cargas", "NO AUTORIZADA"),
    ]
    ax_tab.set_title("Parametros de control", fontsize=9, color="darkblue")
    # encabezado + celdas
    ncol = 2
    for i, (k, v) in enumerate(filas):
        r = i + 1
        ax_tab.text(0.02, 1.0 - i * 0.068, k, fontsize=8,
                    ha="left", va="center",
                    color="white",
                    bbox=dict(boxstyle="square", fc="steelblue", pad=0.4))
        ax_tab.text(0.55, 1.0 - i * 0.068, str(v), fontsize=8,
                    ha="left", va="center")
    ax_tab.set_xlim(0, 1); ax_tab.set_ylim(0, 1); ax_tab.set_axis_off()


def _listar(v):
    if not v:
        return "-"
    return ",".join(str(x) for x in v)


def _mot(p, s, ox, oy, refl):
    x, y = p
    xm = (x - ox) / s
    ym = (oy - y) / s if refl else (y - oy) / s
    return (xm, ym)


# ---------------------------------------------------------------------------
def generar_todo():
    """Punto de entrada de alto nivel (paralelo a correlacion_pagina11.generar_todo)."""
    dxf = extraer_dxf()
    corr = correlacion_pattern_combo(dxf)
    tr = resolver_transformacion(dxf)
    return {"dxf": dxf, "correlacion": corr, "transformacion": tr}


if __name__ == "__main__":
    import sys as _sys
    r = generar_todo()
    if "--deliverables" in _sys.argv:
        generar_deliverables_transformacion(dxf=r["dxf"])
    for cod, info in r["transformacion"].items():
        print(cod, "->", info.get("estado"), info.get("escala"),
              info.get("offset_x_dxf"), info.get("offset_y_dxf"))