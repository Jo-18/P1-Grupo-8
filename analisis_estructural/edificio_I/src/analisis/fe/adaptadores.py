"""Adaptadores de entrada para el motor FE (multi-edificio).

Objetivo: ingerir los archivos de geometria de un edificio (incluido el futuro
Edificio II, cuyo formato puede diferir del contrato actual) y llevarlos al
contrato comun del motor, SIN modificar los archivos de origen.

Flujo recomendado cuando lleguen los JSON del Edificio II:
  1. `inspeccionar_formato(ruta)` -> ver que esquema trae.
  2. `adaptar_geometria(ruta, id_edificio)` -> devuelve dict en el contrato comun
     (en memoria) o escribe a `output` si se indica. Nunca toca el original.
  3. Si el formato es irreconocible o faltan datos indispensables, se reporta
     SOLO lo indispensable que falte (nada mas), sin rellenar con valores del I.

Contrato comun (lo que entiende `geometria_fe.NivelFE.load`):
  - columnas | columnas_referencia: [{id, posicion:[u,v], seccion, eje}]
  - vigas: [{id, seccion:{nombre}, pts:[[u,v],...] | inicio|fin, recibe_losa}]
  - muros: [{id, espesor, eje:{inicio,fin}, recibe_losa}]
  - losas: [{id, espesor, poligono_exterior, aberturas, apoyos_validos}]
  - nivel.cota (m), proyecto.unidades.longitud = 'm'
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CAMPOS_INDISPENSABLES = [
    "unidad_longitud(m)", "cota_nivel", "id_vigas", "id_columnas",
    "id_muros", "secciones_vigas", "secciones_columnas", "espesores_muros",
    "espesores_losa", "coordenadas", "apoyos_validos",
]


def _finito(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def inspeccionar_formato(ruta) -> dict:
    """Detecta de forma superficial el esquema de un archivo de geometria."""
    p = Path(ruta)
    if not p.exists():
        return {"ruta": str(p), "ok": False, "motivo": "no existe"}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ruta": str(p), "ok": False, "motivo": "JSON invalido: %s" % exc}
    claves = list(d.keys())
    tiene_contrato = any(k in d for k in
                         ("losas", "vigas", "muros", "columnas", "columnas_referencia"))
    version = d.get("version_formato")
    proy = d.get("proyecto") or {}
    nivel = d.get("nivel") or {}
    return {
        "ruta": str(p),
        "ok": True,
        "claves_top": claves,
        "version_formato": version,
        "proyecto": proy.get("nombre") if isinstance(proy, dict) else None,
        "edificio": proy.get("edificio") if isinstance(proy, dict) else None,
        "nivel_id": nivel.get("id") if isinstance(nivel, dict) else None,
        "cota_nivel": nivel.get("cota") if isinstance(nivel, dict) else None,
        "n_columnas": len(d.get("columnas") or d.get("columnas_referencia") or []),
        "n_vigas": len(d.get("vigas") or []),
        "n_muros": len(d.get("muros") or []),
        "n_losas": len(d.get("losas") or []),
        "es_contrato_comun": bool(tiene_contrato),
    }


def adaptar_geometria(ruta, id_edificio: Optional[str] = None) -> dict:
    """Devuelve la geometria en el contrato comun (en memoria).

    - Si el archivo ya cumple el contrato comun, se devuelve tal cual (normalizado
      en claves menores) sin modificar el original.
    - Si NO se reconoce el esquema o faltan datos indispensables, se devuelve
      {ok:False, faltan: [...]} sin inventar valores.
    No ejecuta analisis y no rellena campos ausentes con datos del Edificio I.
    """
    p = Path(ruta)
    info = inspeccionar_formato(p)
    if not info["ok"]:
        return {"ok": False, "falta": ["archivo legible"], "detalle": info}

    d = json.loads(p.read_text(encoding="utf-8"))
    faltan = _faltantes_indispensables(d)
    if faltan:
        return {"ok": False, "falta": faltan,
                "detalle": ("No se rellena con datos del Edificio I. "
                            "Se reportan solo los campuntos indispensables ausentes.")}

    if info["es_contrato_comun"]:
        return {"ok": True, "schema": "contrato_comun", "geometria": d,
                "ruta_origen": str(p)}

    # Formato alternativo no reconocido: no se fuerza un mapeo heuristico.
    return {"ok": False, "schema": "desconocido",
            "falta": ["mapeo a contrato comun no implementado para este esquema"],
            "claves": info["claves_top"], "ruta_origen": str(p)}


# --------------------------------------------------------------------------- #
# Seccion documentada de pilares Edificio II
#
# Respaldada por el levantamiento de la compañera (NO deducida de `ancho` a secas):
#   - Notas RLE-PILAR de CP1S (cajas físicas con ambas dimensiones): p.ej.
#     COL_001 B1 caja x[7.15,7.85] y[-0.35,0.35] -> 0.70 x 0.70; COL_004 A2
#     x[-0.35,0.35] y[8.55,9.25] -> 0.70 x 0.70. Todos los cajones 0.70.
#   - `04_auditorias_y_decisiones/inventario/sumario_eii_cp1s.md:20`:
#     "COL_001-008 = 8 pilares RLE-PILAR verificados (cajas 0.70)".
#   - `01_niveles/CP4/informes/informe_pendientes_EII_CP4.md` (125):
#     "9 columnas (A1,B1,C1,D1,A2,B2,C2,B3,C3 (0.7×0.7))".
#   - Verificación de cuadrícula desde pares de caras ±0.30 (retícula) y pilares
#     0.70×0.70 (informe CP4:39-46).
# No se documenta ningún pilar rotado ni de tamaño distinto en los niveles EII.
# --------------------------------------------------------------------------- #
COL_ANCHO_DOC = 0.70
COL_SECCION_NOMBRE = "0.70x0.70"
_FUENTE_SECCION_COL = (
    "Pilares 0.70x0.70 respaldados por cajas RLE-PILAR (CP1S notas: x[..] y[..] "
    "ambas 0.70), sumario_eii_cp1s.md:20 ('cajas 0.70') e informe_pendientes_"
    "EII_CP4.md ('0.7×0.7'). No se deduce de 'ancho' a secas; se copia la caja "
    "documentada. Material/grado de concreto NO documentado para EII (se usara "
    "hipotesis academica G40 marcada como tal cuando se habilite la solucion FE).")


def seccion_columna_documentada(c: dict) -> dict:
    """Devuelve la seccion de columna respaldada (0.70x0.70) con trazabilidad.

    Conserva el `ancho` del registro como origen de la comprobacion y anade las
    dos dimensiones documentadas. Devuelve la seccion por registro (no global).
    """
    nota = c.get("nota", "")
    evidencia = ""
    if "caja" in nota.lower() and ("x[" in nota or "y[" in nota):
        evidencia = "caja RLE-PILAR de la nota (%s)" % nota
    else:
        evidencia = "caja RLE-PILAR (mismos handles que CP1S/CP4) e informe CP4/sumario"
    return {
        "nombre": COL_SECCION_NOMBRE,
        "ancho": COL_ANCHO_DOC,
        "peralte": COL_ANCHO_DOC,
        "estado": "confirmado",
        "fuente": _FUENTE_SECCION_COL,
        "evidencia_registro": evidencia,
        "ancho_origen": c.get("ancho"),
    }


def _rol_columna_eii(c: dict, nivel_id: str, grid_label: str) -> dict:
    """Clasifica el rol de una columna: referencia vs receptor nodal documentado.

    Distingue "columna de referencia / no receptor activo de losa" de "columna
    inexistente". Todas las columnas EII existen fisicamente (cajas RLE-PILAR);
    la mayoria son solo referencia. Las excepciones de receptor nodal documentadas
    (enseño CP2 FASE 4A/4B) se conservan aqui y NO se pierden al adaptar.
    Se devuelve {rol, detalle, nodo_salida, paneles}.
    """
    por_defecto = {
        "rol": "referencia_no_receptor_losa",
        "detalle": ("Columna fisica presente (caja RLE-PILAR); no es receptor "
                    "activo de losa en este nivel."),
        "nodo_salida": list(c.get("punto") or c.get("posicion") or []),
        "paneles": [],
    }
    # Excepciones documentadas de receptor nodal (ensayo de CP2 / notas CP3).
    # Segun FASE 4A/4B del ensayo CP2 (y notas CP3):
    #   COL_002 (C1, nodo [17.5,0]) -> receptor nodal activo para S5;
    #   COL_003 (D1, nodo [27.5,0]) -> receptor nodal activo para S6.
    es_c1 = grid_label == "C1"
    es_d1 = grid_label == "D1"
    nota = (c.get("nota") or "").lower()
    if es_c1 and ("receptor nodal activo" in nota or "s5" in nota):
        return {"rol": "receptor_nodal_activo", "detalle": "Receptor nodal activo (S5) segun FASE4A/4B ensayo CP2; nodo C1 [17.5,0].",
                "nodo_salida": list(c.get("punto") or c.get("posicion") or []),
                "paneles": ["S5"]}
    if es_d1 and ("receptor nodal activo" in nota or "s6" in nota):
        return {"rol": "receptor_nodal_activo", "detalle": "Receptor nodal activo (S6) segun FASE4A/4B ensayo CP2; nodo D1 [27.5,0].",
                "nodo_salida": list(c.get("punto") or c.get("posicion") or []),
                "paneles": ["S6"]}
    if es_c1 or es_d1:
        # Presentes en todos los niveles, receptor solo en ensayo CP2.
        por_defecto["detalle"] += (" Excepcion de receptor nodal documentada en el ensayo "
                                   "CP2 (C1->S5, D1->S6) para " + grid_label + "; no activa aqui.")
    return por_defecto


def _grid_label_eii(c: dict) -> str:
    """Extrae la etiqueta de cuadricula (ej. 'B1') de la nota de la columna."""
    nota = c.get("nota") or ""
    # La nota suele empezar por 'B1 - ...' o contener 'B1;'
    import re
    m = re.search(r"\b([A-Z]\d)\b", nota)
    return m.group(1) if m else ""


def adaptar_geometria_eii(ruta, nivel_id: str = "") -> dict:
    """Adapta un JSON de geometri�a de Edificio II al contrato comun del FE.

    Correcciones frente a la version generica:
      - Mapea `point` -> `posicion` preservando los valores y la trazabilidad
        (nota, handles, grid, rol). NO reporta esas posiciones como faltantes:
        son formato (key `point`) y no ausencia de dato.
      - Asigna la seccion de pilares respaldada (0.70x0.70) con su fuente por
        registro, sin asumir cuadrado solo por `ancho`.
      - Conserva el rol de cada columna (referencia vs receptor nodal) y las
        excepciones de receptores nodales documentadas.
    No modifica el archivo de origen. Si falta un campo realmente indispensable
    (sin unidad, sin cota), se reporta SOLO eso, sin rellenar del edificio I.
    """
    from pathlib import Path as _P
    p = _P(ruta)
    if not p.exists():
        return {"ok": False, "falta": ["archivo legible"], "tabla_nivel": nivel_id}
    d = json.loads(p.read_text(encoding="utf-8"))
    faltan = _faltantes_indispensables(d)
    if faltan:
        return {"ok": False, "falta": faltan, "tabla_nivel": nivel_id,
                "detalle": "No se rellena con datos del Edificio I."}

    cols = d.get("columnas") or d.get("columnas_referencia") or []
    cols_adaptadas = []
    for c in cols:
        pos = c.get("punto", c.get("posicion"))
        label = _grid_label_eii(c)
        rol = _rol_columna_eii(c, nivel_id, label)
        cols_adaptadas.append({
            "id": c["id"],
            "posicion": [pos[0], pos[1]] if pos else None,
            "punto_original": pos,     # trazabilidad: el campo fuente
            "seccion": seccion_columna_documentada(c),
            "rol": rol,
            "grid": label or None,
            "nota": c.get("nota") or None,
            "handles": c.get("handles") or None,
            "ancho": c.get("ancho"),
        })
    vigas_adaptadas = []
    for v in d.get("vigas", []):
        vigas_adaptadas.append({
            "id": v.get("id"), "seccion": v.get("seccion"),
            "pts": [v.get("inicio"), v.get("fin")],
            "recibe_losa": v.get("recibe_losa", True),
            "nota_seccion": v.get("nota_seccion"),
            "eje_reticula": v.get("eje_reticula"),
        })
    return {
        "ok": True,
        "schema": "contrato_comun_eii",
        "edificio": "II",
        "tabla_nivel": nivel_id or (d.get("nivel") or {}).get("id"),
        "cota_nivel": (d.get("nivel") or {}).get("cota"),
        "sistema_coordenadas": d.get("sistema_coordenadas"),
        "sistema_coordenadas_fuente": ((d.get("_trazabilidad") or {}).
                                        get("sistema_coordenadas_fuente")),
        "columnas": cols_adaptadas,
        "vigas": vigas_adaptadas,
        "muros": d.get("muros", []),
        "losas": d.get("losas", []),
        "aberturas_globales": d.get("aberturas_globales", []),
        "configuracion_calculo": d.get("configuracion_calculo", {}),
        "cargas_superficiales": d.get("cargas_superficiales", {}),
        "ruta_origen": str(p),
    }


def _faltantes_indispensables(d: dict) -> List[str]:
    """Devuelve SOLO los campos indispensables ausentes (ni rellena ni infiere)."""
    ausentes = []
    proy = d.get("proyecto") or {}
    if not (isinstance(proy, dict) and isinstance(proy.get("unidades"), dict)
            and str((proy["unidades"] or {}).get("longitud", "")).strip() == "m"):
        ausentes.append("unidad_longitud(m) declarada")
    nivel = d.get("nivel") or {}
    if not (isinstance(nivel, dict) and _finito(nivel.get("cota"))):
        ausentes.append("cota_nivel")
    cols = d.get("columnas") or d.get("columnas_referencia") or []
    vigas = d.get("vigas") or []
    muros = d.get("muros") or []
    losas = d.get("losas") or []
    if not vigas:
        ausentes.append("vigas (con id, seccion y coordenadas)")
    if not cols:
        ausentes.append("columnas (con id, posicion y seccion)")
    if not muros:
        ausentes.append("muros (con id, eje, espesor)")
    if not losas:
        ausentes.append("losas (con poligono y espesor)")
    for vi in vigas:
        if not (isinstance(vi.get("seccion"), dict) and
                str(vi["seccion"].get("nombre", "")).strip()):
            ausentes.append("seccion de viga (%s)" % vi.get("id"))
            break
    for mu in muros:
        if not _finito(mu.get("espesor")):
            ausentes.append("espesor de muro (%s)" % mu.get("id"))
            break
    for lo in losas:
        if not _finito(lo.get("espesor")):
            ausentes.append("espesor de losa (%s)" % lo.get("id"))
            break
    return sorted(set(ausentes))
