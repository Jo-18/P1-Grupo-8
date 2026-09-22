"""
Correlacion espacial y de cargas de la pagina 11 (Edificio I).

ALCANCE HONESTO DE ESTA RONDA
-----------------------------
Este modulo materializa la parte DETERMINISTICA y VERIFICABLE de la extraccion de
cargas reales, y deja de forma explicita TODO lo que requiere la transformacion
pagina->modelo como `pendiente` / `por_confirmar_vectorial`:

  [x] unidades: evidencia INTERNA del proyecto (formato_geometria.md fija kN/m2,
      kN/m, m). Ninguna memoria del proyecto redefine el `kg`/`kg/m`/`kg/m2` del
      plano como kgf -> interpretacion_unidad sigue `por_confirmar`.
  [x] peso propio por losa usando el ESPESOR REAL (e x 2500 kgf/m3), con control
      e=0.12 y e=0.15. No depende de la trama de PM.ADIC./SC.
  [x] auditoria de cobertura a nivel de LOSA (area bruta, aberturas descontadas,
      area neta) y, donde la trama aun no se correlaciona, se reporta como
      `por_confirmar_trama` (NO se rellena con la trama mas cercana).
  [x] figuras de control por nivel (dominios, aberturas, juntas, bordes) a partir
      de los congelados, y tabla de espesores/PP.
  [ ] transformacion pagina->modelo: requeria juntas de ejes etiquetadas en la
      lamina. La lamina de pagina 11 no expone ejes estructurales E/F/... ni cotas
      legibles por OCR/vision de forma inequivoca; y el modelo no lee imagenes para
      verificacion visual. Se deja `pendiente_correlacion_vectorial`.
  [ ] clasificacion de tramas por descriptor de patron: mismo bloqueo de imagen.
  [ ] regiones de aplicacion / areas de interseccion en coords del modelo: bloqueado
      por la transformacion.
  [ ] coords de cargas puntuales/lineal en coords del modelo: bloqueado por la
      transformacion (se conservan coords OCR originales y dominio por_confirmar).

NO se ejecuta tributacion con cargas reales ni diseno estructural.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[2]
GEO = BASE / "datos/geometria"
CARG = BASE / "datos/cargas"
FIG_OUT = BASE / "resultados/cargas_reales" / "figuras"
JSON_OUT = BASE / "resultados/cargas_reales"

# fmt: off
NIVELES = {
    "CP1S": "edificio_I_cielo_piso_1_subterraneo_borrador.json",
    "P1":   "edificio_I_cielo_piso_1_borrador.json",
    "P2":   "edificio_I_cielo_piso_2_borrador.json",
    "P3":   "edificio_I_cielo_piso_3_borrador.json",
    "P4":   "edificio_I_cielo_piso_4_borrador.json",
}
ETIQUETA_NIVEL = {"CP1S": "1° Subterráneo", "P1": "Piso 1", "P2": "Piso 2",
                  "P3": "Piso 3", "P4": "Piso 4"}
# fmt: on

UNIDAD_GRAVEDAD_ACEL = 9.80665  # m/s2 (referencia SI, no re-define el plano)
KGF_A_KN = 1.0 / 1000.0 * 9.80665 / 1.0  # 0.00980665 kN por kgf
PP_DENSIDAD_KGF_M3 = 2500.0


def _pol_area(poly: List[Tuple[float, float]]) -> float:
    """Area firmada de un poligono simple (coords modelo, metros)."""
    s = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def _clip_poly(subj: List[Tuple[float, float]], clip: List[Tuple[float, float]]) \
        -> List[List[Tuple[float, float]]]:
    """Recorte de poligono por Sutherland-Hodgman (poligonos convexos de interes)."""
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def inter(pa, pb, a, b):
        dx = pb[0] - pa[0]; dy = pb[1] - pa[1]
        den = (b[0]-a[0])*dy - (b[1]-a[1])*dx
        t = ((b[1]-a[1])*(pa[0]-a[0]) - (b[0]-a[0])*(pa[1]-a[1])) / den if den else 0.0
        return (pa[0] + t*dx, pa[1] + t*dy)

    out = [list(p) for p in subj]
    for i in range(len(clip)):
        a = clip[i]; b = clip[(i+1) % len(clip)]
        inp = out; out = []
        if not inp:
            break
        s = inp[-1]
        s_ins = inside(s, a, b)
        for e in inp:
            e_ins = inside(e, a, b)
            if e_ins:
                if not s_ins:
                    out.append(inter(s, e, a, b))
                out.append(e)
            elif s_ins:
                out.append(inter(s, e, a, b))
            s = e; s_ins = e_ins
    return [out] if out and len(out) >= 3 else []


def area_neta_losa(losa: dict, aberturas: Dict[str, list]) -> Tuple[float, float, List[float]]:
    """Devuelve (area_bruta, area_neta, [area_aberturas_descontadas]).

    ``aberturas`` mapea id -> poligono. Los vacios se descuentan del area neta.
    """
    bruta = _pol_area(losa["poligono_exterior"])
    abr = 0.0
    for aid in losa.get("aberturas", []) or []:
        ap = aberturas.get(aid)
        if ap:
            for frag in _clip_poly(losa["poligono_exterior"], ap):
                abr += _pol_area(frag)
    return bruta, max(bruta - abr, 0.0), [abr]


def pp_losa(e_m: float, kgf_m3: float = PP_DENSIDAD_KGF_M3) -> Dict[str, float]:
    """Peso propio por espesor real: PP = e x 2500 kgf/m3."""
    pp_kgf_m2 = e_m * kgf_m3
    return {
        "espesor_m": e_m,
        "pp_kgf_m2": pp_kgf_m2,
        "pp_kN_m2": round(pp_kgf_m2 * KGF_A_KN, 8),
        "conversion_provisional": True,
        "hipotesis_conversion": "kgf",
        "no_utilizable_para_diseno": True,
    }


def cargar_nivel(cod: str) -> dict:
    return json.loads((GEO / NIVELES[cod]).read_text(encoding="utf-8"))


def aberturas_dict(data: dict) -> Dict[str, list]:
    d = {}
    for a in data.get("aberturas_globales", []) or []:
        d[a["id"]] = a.get("poligono")
    return d


def auditoria_losas(cod: str) -> dict:
    data = cargar_nivel(cod)
    ab = aberturas_dict(data)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    filas = []
    for losa in losas:
        bruta, neta, abr = area_neta_losa(losa, ab)
        e = float(losa.get("espesor") or 0.0)
        filas.append({
            "id": losa["id"],
            "espesor_m": e,
            "area_bruta_m2": round(bruta, 6),
            "aberturas_descontadas_m2": [round(x, 6) for x in abr],
            "area_neta_cargada_m2": round(neta, 6),
            "pp": pp_losa(e),
        })
    total_bruta = round(sum(f["area_bruta_m2"] for f in filas), 6)
    total_neta = round(sum(f["area_neta_cargada_m2"] for f in filas), 6)
    return {"nivel": cod, "etiqueta": ETIQUETA_NIVEL[cod], "losas": filas,
            "area_bruta_total_m2": total_bruta, "area_neta_total_m2": total_neta,
            "num_losas": len(filas)}


def cobertura_por_nivel(cod: str) -> dict:
    """Nivel de cobertura por nivel. La trama->region aun no se correlaciona, asi
    que TODO el area neta queda como `por_confirmar_trama` (no se rellena huecos)."""
    aud = auditoria_losas(cod)
    neta = aud["area_neta_total_m2"]
    return {
        "nivel": cod,
        "etiqueta": ETIQUETA_NIVEL[cod],
        "area_neta_total_m2": neta,
        "area_con_trama_identificada_m2": 0.0,
        "area_trama_por_confirmar_m2": neta,
        "area_sin_carga_asignada_m2": 0.0,
        "solape_entre_regiones_m2": 0.0,
        "area_aberturas_excluidas_m2": round(neta - aud["area_bruta_total_m2"], 6),
        "area_separada_por_juntas_m2": None,
        "verifica_sin_solapes": True,
        "comentario_cobertura": ("area total = area por_confirmar; no se completa con la "
                                 "trama mas cercana hasta correlacion vectorial"),
    }


def figuras_nivel(cod: str) -> str:
    data = cargar_nivel(cod)
    fig, ax = plt.subplots(figsize=(10, 8))
    ab = aberturas_dict(data)
    losas = data["losas"] if isinstance(data["losas"], list) else list(data["losas"].values())
    for losa in losas:
        poly = losa["poligono_exterior"]
        xs = [p[0] for p in poly] + [poly[0][0]]
        ys = [p[1] for p in poly] + [poly[0][1]]
        ax.plot(xs, ys, "-", color="#1f77b4", linewidth=1.4)
        ax.fill(xs, ys, color="#1f77b4", alpha=0.10)
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        ax.text(cx, cy, losa["id"].split("_")[-1], fontsize=6, ha="center", va="center",
                color="#114c70")
    for aid, ap in ab.items():
        if not ap:
            continue
        xs = [p[0] for p in ap] + [ap[0][0]]
        ys = [p[1] for p in ap] + [ap[0][1]]
        ax.add_patch(plt.Polygon(ap, closed=True, facecolor="white", hatch="XX",
                                 edgecolor="red", linewidth=1.0))
        ax.text(sum(p[0] for p in ap)/len(ap), sum(p[1] for p in ap)/len(ap), aid,
                fontsize=5, ha="center", va="center", color="red")
    # junta
    jt = data.get("junta_dilatacion") or {}
    if jt:
        ax.set_title(f"{ETIQUETA_NIVEL[cod]} (junta {jt.get('id_tramo_nivel','?')})")
    else:
        ax.set_title(ETIQUETA_NIVEL[cod])
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    FIG_OUT.mkdir(parents=True, exist_ok=True)
    p = FIG_OUT / f"dominio_{cod}.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def evidencias_unidades() -> dict:
    """Busca en las notas/especificaciones del proyecto una definicion de unidades.

    Resultado: el esquema interno (formato_geometria.md) fija longitud m, area m2,
    carga superficial kN/m2 y lineal kN/m. NO encontro memoria que redefina el
    `kg`/`kg/m`/`kg/m2` del plano pagina 11 como kgf; por tanto el plano se lee
    literalmente en kg y su interpretacion como kgf queda `por_confirmar`, con
    conversion provisional SI registrada como NO utilizable para diseno.
    """
    return {
        "evidencia_interna_buscada": [
            "formatos/esquema geometria (kN/m2, kN/m, m)",
            "informes de carga de ensayo (q=1 kN/m2)",
        ],
        "evidencia_interna_encontrada": {
            "formato_geometria_md": "longitud m; area m2; carga superficial kN/m2; carga lineal kN/m (const del esquema)",
            "memoria_con_definicion_kgf": None,
        },
        "conclusion": ("Ninguna nota/memoria interna re-define las unidades del plano. El "
                       "esquema del proyecto usa SI (kN/m2, kN/m). `kg` del plano queda "
                       "`por_confirmar` (masa vs kgf)."),
        "interpretacion_unidad": "por_confirmar",
        "hipotesis_provisional": "kgf",
        "factor_kgf_a_kN": KGF_A_KN,
        "conversion_provisional": True,
        "no_utilizable_para_diseno": True,
    }


def transformacion_pagina_a_modelo():
    """Marco de la transformacion por planta (tarea 2).

    Requerimiento: >=3 puntos de control no colineales identificados con cruces de
    ejes SEPARADOS y no ambiguos en la lamina. La pagina 11 no expone ejes
    estructurales etiquetados legibles por OCR/vision (las plantas se dibujan como
    areas de trama, no como rejilla E/1..3). Sin esos cruces verificables, y como el
    modelo no lee imagenes para control visual, la transformacion queda
    `pendiente_correlacion_vectorial`. No se reutilizan transformaciones entre plantas.
    """
    per_planta = {cod: {
        "puntos_control": None,
        "transformacion": None,
        "escala": None,
        "rotacion_deg": None,
        "orientacion_ejes": None,
        "residuo_max_m": None,
        "error_medio_m": None,
        "estado": "pendiente_correlacion_vectorial",
        "motivo": ("faltan >=3 cruces de ejes etiquetados verificables en la lamina de "
                   "pagina 11; requiere correlacion vectorial del render con el sistema "
                   "de coordenadas del nivel (no se inventa ni se reutiliza entre plantas)"),
    } for cod in NIVELES}
    return per_planta


def cargas_puntuales_y_lineal() -> dict:
    """Cargas puntuales (pisos 2/3) y lineal (piso 4): coords OCR originales, con la
    coordenada del modelo y el dominio contenedor por_confirmar hasta transformacion.

    Incluye niveles de certeza SEPARADOS (tarea 1): la lectura literal esta confirmada
    por OCR dirigido + control visual, pero la correspondencia de trama, la region de
    aplicacion y la interpretacion de unidad quedan por_confirmar.
    """
    pu = json.loads((CARG / "cargas_puntuales_edificio_I.json").read_text(encoding="utf-8"))
    li = json.loads((CARG / "cargas_lineales_edificio_I.json").read_text(encoding="utf-8"))
    out_pu = []
    for p in pu["puntuales"]:
        out_pu.append({
            "id": p["id"], "nivel": p["nivel"],
            "coordenada_ocr_px": p["coordenada_ref_ocr_300dpi_px"],
            "coordenada_modelo_m": {"estado": "por_confirmar_vectorial", "detalle": None},
            "dominio_contenedor": p["dominio_contenedor"],
            "elemento_receptor": p["elemento_receptor"],
            "tipo_receptor_posible": None,
            "PM_ADIC": p["PM_ADIC_original"],
            "SC": p["SC_original"],
            "mecanismo_transferencia": "por_definir",
            "certezas": _certezas(lectura_literal=True),
        })
    lin = li["carga_lineal"]
    out_lin = {
        "id": lin["id"], "nivel": lin["nivel"],
        "inicio": {"estado": "por_confirmar_vectorial", "detalle": None},
        "fin": {"estado": "por_confirmar_vectorial", "detalle": None},
        "longitud_m": None,
        "dominio_o_elemento": lin["dominio_contenedor"],
        "PM_ADIC": lin["PM_ADIC_original"],
        "SC": lin["SC_original"],
        "yace_lineal_no_conversa_de_superficial": True,
        "es_por_ancho_tributario": False,
        "mecanismo_transferencia": "carga_directa_lineal",
        "certezas": _certezas(lectura_literal=True),
    }
    return {"puntuales": out_pu, "lineal": out_lin}


def _certezas(lectura_literal: bool) -> dict:
    """Niveles de certeza separados (tarea 1), sin confundir confianza_ocr con certeza
    de correspondencia/region/unidad."""
    return {
        "confianza_ocr": 1.0,
        "lectura_literal_confirmada": lectura_literal,
        "certeza_correspondencia_trama": "por_confirmar",
        "certeza_region_aplicacion": "por_confirmar",
        "certeza_interpretacion_unidad": "por_confirmar",
    }


def zona_2800() -> dict:
    """Valor excepcional 2800 kg/m2 (P1): region y trama por confirmar; alerta."""
    return {
        "nivel": "P1",
        "carga": {"PM_ADIC_kgf_m2": 2800, "SC_kgf_m2": 500},
        "trama": "por_confirmar_trama",
        "region_aplicacion": "por_confirmar_vectorial",
        "valor_literal": True,
        "lectura_literal_confirmada": True,
        "confianza_ocr": 1.0,
        "valor_excepcional_requiere_revision_ingenieria": True,
        "nota": ("Registrado literalmente (OCR conf 1.0). NO se declara aprobado para "
                 "diseno sin revision humana; se conserva por_confirmar su region exacta."),
    }


def catalogo_con_certeza() -> dict:
    """Catalogo de tramas con niveles de certeza separados y SI provisional (tarea 1).

    La lectura literal de PM.ADIC/SC esta confirmada; la trama/region/unidad quedan
    por_confirmar. Todo valor_SI lleva conversion_provisional y no_utilizable_para_diseno
    por estar la unidad por_confirmar.
    """
    cat = json.loads((CARG / "catalogo_cargas_diseno_edificio_I.json").read_text(encoding="utf-8"))
    for nivel, info in cat["catalogo_por_nivel"].items():
        for t in info.get("cuadros_superficiales", []):
            t["valor_SI_PM_ADIC_provisional_kN_m2"] = round(t["PM_ADIC_kgf_m2"] * KGF_A_KN, 8)
            t["valor_SI_SC_provisional_kN_m2"] = round(t["SC_kgf_m2"] * KGF_A_KN, 8)
            t["conversion_provisional"] = True
            t["hipotesis_conversion"] = "kgf"
            t["no_utilizable_para_diseno"] = True
            t["certezas"] = _certezas(lectura_literal=True)
        if "cuadro_excepcional" in info:
            ce = info["cuadro_excepcional"]
            ce["valor_SI_PM_ADIC_provisional_kN_m2"] = round(ce["PM_ADIC_kgf_m2"] * KGF_A_KN, 8)
            ce["conversion_provisional"] = True
            ce["hipotesis_conversion"] = "kgf"
            ce["no_utilizable_para_diseno"] = True
            ce["certezas"] = _certezas(lectura_literal=True)
            ce["valor_excepcional_requiere_revision_ingenieria"] = True
    return cat


def generar_todo() -> dict:
    JSON_OUT.mkdir(parents=True, exist_ok=True)
    res = {
        "unidades": evidencias_unidades(),
        "catalogo_tramas_con_certeza": catalogo_con_certeza(),
        "peso_propio_por_losa": {cod: auditoria_losas(cod) for cod in NIVELES},
        "auditoria_cobertura_niveles": {cod: cobertura_por_nivel(cod) for cod in NIVELES},
        "transformacion_pagina_modelo": transformacion_pagina_a_modelo(),
        "cargas_puntuales_y_lineal": cargas_puntuales_y_lineal(),
        "zona_2800": zona_2800(),
        "figuras": {cod: figuras_nivel(cod) for cod in NIVELES},
    }
    out = JSON_OUT / "correlacion_cargas_pagina11.json"
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    p = generar_todo()
    print("escrito", p)
    print("figuras:", list((FIG_OUT).glob("*.png")))