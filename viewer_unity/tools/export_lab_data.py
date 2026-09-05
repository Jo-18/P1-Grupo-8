"""Exporta un paquete de datos AUTOCONTENIDO (JSON) para el viewer Unity del
lab FE (Edificio I + Edificio II).

SOLO LEE datos existentes del laboratorio; NO ejecuta analisis estructural ni
reconstruye un modelo independiente. Aplica de forma UNICA la cadena de
transformacion documentada:
    common (u,v,cota) -> Unity (X,Y,Z)=(u,cota,v)
y los multiplicadores local->comun de cada nivel (solo Edificio I, cuyo archivo
esta en frame local; Edificio II ya esta en su frame comun).

Salida: <viewer>/Assets/StreamingAssets/lab_data/
   manifest.json           lista de archivos, unidades, transform, ejecucion fuente,
                           estados de validacion e hipotesis
   placement.json          colocacion global (junta provisional documentada)
   edificios/<id>/geometry/<level>.json
   edificios/<id>/tributary/<level>.json   (solo Edificio I; II sin valores reales)
   edificios/<id>/results/<name>.json      (solo Edificio I, ejecucion primaria)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Rutas (relativas al laboratorio). El viewer vive junto a laboratorio_semana2.
# --------------------------------------------------------------------------- #
LAB = Path(__file__).resolve().parents[2] / "laboratorio_semana2"
OUT = Path(__file__).resolve().parents[1] / "Assets" / "StreamingAssets" / "lab_data"

EI_LEVELS = ["CP1S", "P1", "P2", "P3", "P4"]
EI_COTA = {"CP1S": -4.01, "P1": -0.05, "P2": 3.91, "P3": 7.87, "P4": 11.83}
EI_ARCHIVO = {
    "CP1S": "edificio_I_cielo_piso_1_subterraneo_candidata_unity.json",
    "P1": "edificio_I_cielo_piso_1_borrador.json",
    "P2": "edificio_I_cielo_piso_2_borrador.json",
    "P3": "edificio_I_cielo_piso_3_borrador.json",
    "P4": "edificio_I_cielo_piso_4_candidata_vigas_corregidas.json",
}

EII_LEVELS = ["EII_CP1S", "EII_CP1", "EII_CP2", "EII_CP3", "EII_CP4"]
EII_COTA = {"EII_CP1S": -4.01, "EII_CP1": -0.05, "EII_CP2": 3.91, "EII_CP3": 7.87, "EII_CP4": 11.83}
EII_ADAPT = {
    "EII_CP1S": "resultados/modelo_estructural/edificio_II_geometria_adaptada/EII_CP1S_cielo_piso1S_borrador_adaptado_contrato_comun.json",
    "EII_CP1": "resultados/modelo_estructural/edificio_II_geometria_adaptada/EII_CP1_cielo_piso1_borrador_adaptado_contrato_comun.json",
    "EII_CP2": "resultados/modelo_estructural/edificio_II_geometria_adaptada/EII_CP2_cielo_piso2_borrador_adaptado_contrato_comun.json",
    "EII_CP3": "resultados/modelo_estructural/edificio_II_geometria_adaptada/EII_CP3_cielo_piso3_borrador_adaptado_contrato_comun.json",
    "EII_CP4": "resultados/modelo_estructural/edificio_II_geometria_adaptada/EII_CP4_cielo_piso4_borrador_adaptado_contrato_comun.json",
}

# --------------------------------------------------------------------------- #
# Transformaciones (fuente: matrices_transformacion_unity.json)
# --------------------------------------------------------------------------- #
EI_LOCAL_TO_COMMON = {
    "P1":   {"u": lambda x: x - 10.0,            "v": lambda y: 35.0 - y},
    "P2":   {"u": lambda x: x,                    "v": lambda y: y},
    "P3":   {"u": lambda x: x,                    "v": lambda y: y},
    "P4":   {"u": lambda x: x,                    "v": lambda y: y},
    "CP1S": {"u": lambda x: x - 0.35022726894,    "v": lambda y: 16.5005345365 - y},
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-lab", default=str(LAB), help="raiz de laboratorio_semana2")
    p.add_argument("--out", default=str(OUT), help="carpeta de salida del paquete")
    return p.parse_args()


def _json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_unity(u, v, cota):
    """common (u,v,cota) -> Unity (X,Y,Z)=(u,cota,v). Aplicacion UNICA."""
    return [round(u, 6), round(cota, 6), round(v, 6)]


def xf2d(x, y, level, building):
    """Devuelve (u, v) en el frame comun del edificio."""
    if building == "I":
        t = EI_LOCAL_TO_COMMON.get(level, {})
        u = t.get("u", lambda x: x)(x)
        v = t.get("v", lambda y: y)(y)
        return u, v
    # Edificio II: su frame comun ES su local (adaptado por el laboratorio)
    return x, y


def xf_ring(ring, level, building, cota):
    return [to_unity(*xf2d(pt[0], pt[1], level, building), cota) for pt in ring]


def _warn(msg):
    print("WARN:", msg, file=sys.stderr)


import re as _re

# --------------------------------------------------------------------------- #
# Parsing de seccion de columna -> (ancho_m, peralte_m, estado_seccion)
#
# Convenciones de unidades de las fuentes EI (conservadas tal cual):
#   - Concreto "P. 70x70"  -> plan en CENTIMETROS (70x70 cm = 0.70 x 0.70 m)
#   - Metalico "P.M. 300x300x20" / "V.M. 300x300x5" -> plan en MILIMETROS
#       (tubo 300x300 mm = 0.30 x 0.30 m; el tercer numero es espesor y no altera
#        las dimensiones exteriores del cubo visual).
#   - Perfil "P.M.I." (viga/perfil metalico I) sin dimensiones simples -> se marca
#       pendiente (estado_seccion="por_resolver") y no se inventa dimension.
#
# Si la seccion no es parseable se devuelve (0, 0, "por_resolver"): el viewer la
# dibuja marcada como PENDIENTE en lugar de forzarla a 70x70.
# --------------------------------------------------------------------------- #
def _parse_col_section(sec_name):
    if not sec_name:
        return 0.0, 0.0, "por_resolver"

    txt = str(sec_name)
    m = _re.search(r"(\d+)\s*[xX×]\s*(\d+)", txt)
    if not m:
        return 0.0, 0.0, "por_resolver"

    n1 = float(m.group(1))
    n2 = float(m.group(2))
    is_metal = ("M." in txt) or (" M " in txt) or txt.upper().startswith("PM")
    if is_metal:
        # milimetros
        w = round(n1 / 1000.0, 6)
        h = round(n2 / 1000.0, 6)
        estado = "confirmado" if (w > 0 and h > 0) else "por_resolver"
        return w, h, estado
    # concreto -> centimetros
    w = round(n1 / 100.0, 6)
    h = round(n2 / 100.0, 6)
    estado = "confirmado" if (w > 0 and h > 0) else "por_resolver"
    return w, h, estado


# --------------------------------------------------------------------------- #
# Seccion de VIGA (Edificio I). Las vigas EI se etiquetan con diagonal, p. ej.
# "V. 60/80" (60x80 cm = 0.60 x 0.80 m) o "V.S.I. 20/150". La fuente NO entrega
# campos "ancho"/"peralte" en la mayoria de niveles (None), por lo que el ancho y
# el peralte se resuelven AQUI a partir de la etiqueta autoritativa, de modo que el
# viewer no caiga en sus values por defecto (0.5/0.8). Si la etiqueta no es
# parseable (p. ej. "M.H.A. e=30") se devuelve None y NO se fabrica dimension.
# --------------------------------------------------------------------------- #
def _parse_beam_section(sec_name):
    if not sec_name:
        return None
    # viga de concreto "V. 60/80" / "V.S.I. 20/150" -> cm
    m = _re.search(r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)", str(sec_name))
    if not m:
        return None
    n1 = float(m.group(1).replace(",", "."))
    n2 = float(m.group(2).replace(",", "."))
    if n1 <= 0 or n2 <= 0:
        return None
    return round(n1 / 100.0, 6), round(n2 / 100.0, 6)


# --------------------------------------------------------------------------- #
# Edificio I
# --------------------------------------------------------------------------- #
def export_ei(level, file):
    d = _json(file)
    cota = d["nivel"]["cota"]
    out = {
        "edificio": "I", "nivel": level, "cota": cota, "unidades": "m",
        "frame": "unity (X,Y,Z)=(u,cota,v)",
        "columnas": [], "vigas": [], "muros": [], "losas": [],
        "aberturas_globales": [],
    }
    # Marcador de candidata P4 (traslacion de vigas +0.18 m en v) para el inspector.
    if level == "P4":
        out["candidata"] = {
            "tipo": "candidata_con_traslacion_vigas",
            "shift_v_m": 0.18,
            "fuente": "2017_67-103.dxf",
            "ejes_vigas": {"sur": 0.18, "interior": 9.08, "norte": 16.33},
            "nota": ("Geometria candidata: grid de vigas trasladado +0.18 m en v a los ejes "
                     "de plano (alineado con columnas). Las areas tributarias y resultados FE "
                     "previos corresponden a la geometria anterior y NO estan revalidados."),
        }
    # aberturas globales
    ag_map = {}
    for ab in d.get("aberturas_globales", []):
        pts = xf_ring(ab["poligono"], level, "I", cota) if ab.get("poligono") else []
        rec = {"id": ab["id"], "tipo": ab.get("tipo"), "poligono": pts,
               "edificio": "I", "nivel": level}
        out["aberturas_globales"].append(rec)
        ag_map[ab["id"]] = ab.get("poligono")
    # losas
    for l in d.get("losas", []):
        poly = xf_ring(l["poligono_exterior"], level, "I", cota)
        ab_ids = l.get("aberturas", [])
        aberturas = []
        for aid in ab_ids:
            if aid in ag_map:
                aberturas.append(xf_ring(ag_map[aid], level, "I", cota))
            else:
                # abertura referenciada pero sin poligono global
                if isinstance(aid, dict) and aid.get("poligono"):
                    aberturas.append(xf_ring(aid["poligono"], level, "I", cota))
                else:
                    aberturas.append(None)
        out["losas"].append({
            "id": l["id"], "espesor": l.get("espesor"),
            "poligono": poly, "aberturas": aberturas,
            "apoyos_validos": l.get("apoyos_validos", []),
            "tipo_transferencia": l.get("tipo_transferencia"),
            "direccion_transferencia": l.get("direccion_transferencia"),
            "edificio": "I", "nivel": level,
        })
    # vigas
    for v in d.get("vigas", []):
        p0 = v.get("inicio") or (v.get("eje", {}) or {}).get("inicio")
        p1 = v.get("fin") or (v.get("eje", {}) or {}).get("fin")
        if p0 is None or p1 is None:
            pts = []
        else:
            pts = [to_unity(*xf2d(p0[0], p0[1], level, "I"), cota),
                   to_unity(*xf2d(p1[0], p1[1], level, "I"), cota)]
        sec_name = (v.get("seccion") or {}).get("nombre")
        ancho_src = v.get("ancho")
        parsed = _parse_beam_section(sec_name)
        # ancho: usa el explicito de la fuente si existe; si no, el de la etiqueta.
        # peralte: la fuente EI no lo entrega (None); se resuelve de la etiqueta.
        ancho_m = ancho_src if ancho_src is not None else (parsed[0] if parsed else None)
        peralte_m = parsed[1] if parsed else None
        out["vigas"].append({
            "id": v["id"], "seccion": sec_name,
            "ancho": ancho_m, "peralte": peralte_m, "pts": pts,
            "recibe_losa": v.get("recibe_losa", True),
            "edificio": "I", "nivel": level,
        })
    # muros
    for m in d.get("muros", []):
        eje = m.get("eje") or {}
        p0 = eje.get("inicio"); p1 = eje.get("fin")
        pts = [] if (p0 is None or p1 is None) else [
            to_unity(*xf2d(p0[0], p0[1], level, "I"), cota),
            to_unity(*xf2d(p1[0], p1[1], level, "I"), cota)]
        out["muros"].append({
            "id": m["id"], "espesor": m.get("espesor"),
            "pts": pts, "recibe_losa": m.get("recibe_losa", True),
            "edificio": "I", "nivel": level,
        })
    # columnas
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # EI guarda sus registros de columna indistintamente en "columnas" (todos los niveles
    # candidatos) o en "columnas_referencia" (CP1S/P2/P3/P4). Se admite cualquiera de
    # las dos claves. Si AMBAS aparecen con contenido, se informa el conflicto y se usa
    # "columnas" (clave primaria); NO se concatenan ni se duplican registros.
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    cols_main = d.get("columnas") or []
    cols_ref = d.get("columnas_referencia") or []
    if cols_main and cols_ref:
        _warn(f"[EI {level}] Conflicto de columnas: ambas claves 'columnas' ({len(cols_main)}) "
              f"y 'columnas_referencia' ({len(cols_ref)}) tienen contenido. Se usa 'columnas'; "
              "no se concatenan ni se duplican registros.")
        cols = cols_main
    else:
        cols = cols_main if cols_main else cols_ref

    seen_col_ids = set()
    for c in cols:
        cid = c.get("id")
        if cid is None:
            continue
        if cid in seen_col_ids:
            _warn(f"[EI {level}] ID de columna duplicado omitido: {cid}")
            continue
        seen_col_ids.add(cid)

        pos = c.get("posicion") or c.get("punto")
        if pos is None or len(pos) < 2:
            _warn(f"[EI {level}] Columna {cid} sin posicion valida; se omite.")
            continue
        up = to_unity(*xf2d(pos[0], pos[1], level, "I"), cota)

        sec = c.get("seccion")
        sec_name = sec if isinstance(sec, str) else (sec or {}).get("nombre")
        ancho_m, peralte_m, estado_sec = _parse_col_section(sec_name)

        out["columnas"].append({
            "id": cid,
            "seccion": sec_name,
            "ancho": ancho_m,
            "peralte": peralte_m,
            "estado_seccion": estado_sec,
            "posicion": up,
            "eje": c.get("eje"),
            "nota": c.get("nota"),
            "edificio": "I", "nivel": level,
        })
    return out


# --------------------------------------------------------------------------- #
# Edificio II
# --------------------------------------------------------------------------- #
def export_eii(level, file):
    d = _json(file)
    cota = d.get("cota_nivel") or EII_COTA[level]
    out = {
        "edificio": "II", "nivel": level, "cota": cota, "unidades": "m",
        "frame": "unity (X,Y,Z)=(u,cota,v)",
        "columnas": [], "vigas": [], "muros": [], "losas": [],
        "aberturas_globales": [],
    }
    ag_map = {}
    for ab in d.get("aberturas_globales", []):
        poly = xf_ring(ab.get("poligono") or [], level, "II", cota)
        rec = {"id": ab["id"], "tipo": ab.get("tipo"), "poligono": poly,
               "edificio": "II", "nivel": level}
        out["aberturas_globales"].append(rec)
        ag_map[ab["id"]] = ab.get("poligono")
    for l in d.get("losas", []):
        poly = xf_ring(l.get("poligono_exterior") or [], level, "II", cota)
        aberturas = []
        for aid in l.get("aberturas", []) or []:
            if isinstance(aid, dict) and aid.get("poligono"):
                aberturas.append(xf_ring(aid["poligono"], level, "II", cota))
            elif isinstance(aid, str) and aid in ag_map:
                aberturas.append(xf_ring(ag_map[aid] or [], level, "II", cota))
            elif aid is None:
                aberturas.append(None)
            # aberturas por id no encontradas se omiten (se conserva la referencia)
        out["losas"].append({
            "id": l["id"], "espesor": l.get("espesor"),
            "poligono": poly, "aberturas": aberturas,
            "abertura_ids": [a if isinstance(a, str) else (a.get("id") if isinstance(a, dict) else None)
                             for a in (l.get("aberturas") or [])],
            "apoyos_validos": l.get("apoyos_validos", []),
            "tipo_transferencia": l.get("tipo_transferencia"),
            "direccion_transferencia": l.get("direccion_transferencia"),
            "edificio": "II", "nivel": level,
        })
    for v in d.get("vigas", []):
        pts = v.get("pts")
        if not pts and v.get("inicio") and v.get("fin"):
            pts = [v["inicio"], v["fin"]]
        sec = v.get("seccion") or {}
        out["vigas"].append({
            "id": v["id"],
            "seccion": sec.get("nombre"),
            "ancho": sec.get("ancho"), "peralte": sec.get("peralte"),
            "estado_seccion": sec.get("estado"),
            "pts": xf_ring(pts or [], level, "II", cota),
            "recibe_losa": v.get("recibe_losa", True),
            "nota_seccion": v.get("nota_seccion"),
            "eje_reticula": v.get("eje_reticula"),
            "edificio": "II", "nivel": level,
        })
    for m in d.get("muros", []):
        eje = m.get("eje") or {}
        p0 = eje.get("inicio"); p1 = eje.get("fin")
        pts = [] if (p0 is None or p1 is None) else xf_ring([p0, p1], level, "II", cota)
        out["muros"].append({
            "id": m["id"], "espesor": m.get("espesor"),
            "pts": pts, "recibe_losa": m.get("recibe_losa", True),
            "edificio": "II", "nivel": level,
        })
    cols = d.get("columnas") or d.get("columnas_referencia") or []
    for c in cols:
        pos = c.get("posicion") or c.get("punto")
        up = to_unity(*xf2d(pos[0], pos[1], level, "II"), cota)
        sec = c.get("seccion") or {}
        out["columnas"].append({
            "id": c["id"],
            "seccion": sec.get("nombre") if isinstance(sec, dict) else sec,
            "ancho": sec.get("ancho") if isinstance(sec, dict) else None,
            "peralte": sec.get("peralte") if isinstance(sec, dict) else None,
            "posicion": up, "grid": c.get("grid") or c.get("eje"),
            "rol": (c.get("rol") or {}).get("rol") if isinstance(c.get("rol"), dict) else c.get("rol"),
            "nota": c.get("nota"), "edificio": "II", "nivel": level,
        })
    return out


# --------------------------------------------------------------------------- #
# Resultados / tributaria Edificio I (ejecucion PRIMARIA de referencia)
# --------------------------------------------------------------------------- #
def export_ei_results(base):
    """Tributary (por viga) y resumen estructural de la ejecucion primaria."""
    paquete = _json(base / "resultados" / "modelo_estructural" / "paquete_entrega_edificio_I.json")
    res = _json(base / "resultados" / "modelo_estructural" / "resultado_primera_ejecucion.json")
    cruda = _json(base / "resultados" / "modelo_estructural" / "solucion_cruda_primera_ejecucion.json")

    tributary = {}
    av = paquete.get("area_y_carga_por_viga", {})
    for lvl in EI_LEVELS:
        beans = []
        for b in av.get(lvl, []):
            beans.append({
                "receptor": b["receptor"],
                "area_tributaria_m2": b.get("area_tributaria_m2"),
                "carga_total_kN": b.get("carga_total_kN"),
                "n_nodos_fe": b.get("n_nodos_fe"),
                "losas": [{"losa": x["losa"], "area_m2": x.get("area_trib_m2"),
                           "carga_kN": x.get("carga_kN")} for x in b.get("losas", [])],
            })
        tributary[lvl] = beans

    # resumen de equilibrio y modelo de la ejecucion primaria
    ver = res.get("verificaciones", {})
    modelo = res.get("modelo", {})
    structure = {
        "ejecucion": "primera_ejecucion",
        "mult": 1000.0,
        "subdivision_vigas": 1,
        "estado": res.get("estado"),
        "modelo": {
            "n_nodos": modelo.get("n_nodos"), "n_columnas": modelo.get("n_columnas"),
            "n_vigas": modelo.get("n_vigas"), "n_muros": modelo.get("n_muros"),
            "master_por_nivel": modelo.get("master_por_nivel"),
        },
        "solucion": res.get("solucion"),
        "cargas_nodales_total_kN": res.get("cargas_nodales_total_kN"),
        "equilibrio_vertical": ver.get("equilibrio_vertical"),
        "equilibrio_horizontal": ver.get("equilibrio_horizontal"),
        "equilibrio_momentos": ver.get("equilibrio_momentos"),
        "diafragmas": ver.get("diafragmas"),
        "areas_y_carga_por_nivel": ver.get("areas_y_carga_por_nivel"),
        "balance_carga_casoG_vs_aplicada": ver.get("balance_carga_casoG_vs_aplicada"),
        "balance_carga_aplicada_vs_reacciones": ver.get("balance_carga_aplicada_vs_reacciones"),
        "hipotesis": res.get("hipotesis"),
        "tiempos_s": res.get("tiempos_s"),
        # campos para etapa posterior de deformada/diagramas (sin mostrar por defecto)
        "solucion_cruda_disponible": True,
        "n_desplazamientos": len(cruda.get("desplazamientos", {})),
        "n_reacciones": len(cruda.get("reacciones", {})),
        "max_disp_documentado_m": 0.10772,
        "nota_limite": ("Analisis de laboratorio NO utilizable para diseno. La seccion "
                        "y respuesta de la V.S.I. es provisional (refinado subdiv4 "
                        "presenta desplazamiento anomalo 12.68 m no validado)."),
        # tramos de columna reales del modelo FE (ejecucion primaria), en metros.
        # Cada tramo: (u,z_i,z_j,v) en convencion comun -> Unity (X,Y,Z)=(u,cota,v).
        # z_i = base (nodo inicial), z_j = cota superior (nodo final). NO se fabrica
        # prolongacion del ultimo nivel: solo existen tramos con columna documentada.
        "columnas_tramos": _load_column_tramos(base),
    }
    return tributary, structure


def _load_column_tramos(base):
    """Lee los tramos de columna FE del Edificio I (columna_tramos_ei.json) y los
    entrega en convencion Unity (u, z, v). Si falta el archivo devuelve [] (el visor
    entonces marca la extension como pendiente en lugar de inventar altura)."""
    p = base / "resultados" / "modelo_estructural" / "columnas_tramos_ei.json"
    if not p.exists():
        _warn("[EI results] No se hallo columnas_tramos_ei.json; sin tramos FE.")
        return []
    try:
        doc = _json(p)
    except Exception as e:  # noqa: BLE001
        _warn(f"[EI results] columna_tramos_ei.json ilegible: {e}")
        return []
    out = []
    for t in doc.get("tramos", []):
        out.append({
            "elemento_id": t.get("elemento_id"),
            "nivel": t.get("nivel"),
            "u": t.get("u"), "z_i": t.get("z_i"), "z_j": t.get("z_j"), "v": t.get("v"),
        })
    return out


def _with_tributary_regions(out: Path, files):
    """Asegura que el paquete liste las regiones tributarias reales (generadas por
    exportar_regiones_tributarias.py). Si el archivo existe en disco aun cuando este
    exportador no lo re-escribe, se incluye en el manifest para no perderlo."""
    p = "edificios/I/tributary/regiones_tributarias.json"
    if (out / p).exists() and p not in files:
        files.append(p)
    return files


def main():
    args = parse_args()
    base = Path(args.base_lab)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    manifest_files = []

    # ---- Edificio I: geometry por nivel ----
    for lvl in EI_LEVELS:
        rec = export_ei(lvl, base / "datos" / "candidatos" / EI_ARCHIVO[lvl])
        p = out / "edificios" / "I" / "geometry" / f"{lvl}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest_files.append(str(p.relative_to(out)).replace("\\", "/"))
        print(f"  EI {lvl}: {len(rec['columnas'])} col | {len(rec['vigas'])} vig | "
              f"{len(rec['muros'])} muro | {len(rec['losas'])} losa")

    # ---- Edificio II: geometry por nivel ----
    for lvl in EII_LEVELS:
        rec = export_eii(lvl, base / EII_ADAPT[lvl])
        p = out / "edificios" / "II" / "geometry" / f"{lvl}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest_files.append(str(p.relative_to(out)).replace("\\", "/"))
        print(f"  EII {lvl}: {len(rec['columnas'])} col | {len(rec['vigas'])} vig | "
              f"{len(rec['muros'])} muro | {len(rec['losas'])} losa")

    # ---- Edificio I: tributaria + resultados (ejecucion primaria) ----
    trib, structure = export_ei_results(base)
    p = out / "edificios" / "I" / "tributary" / "por_viga.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"ejecucion": "primera_ejecucion", "por_nivel": trib},
                            ensure_ascii=False, indent=1), encoding="utf-8")
    manifest_files.append(str(p.relative_to(out)).replace("\\", "/"))
    p = out / "edificios" / "I" / "results" / "primera_ejecucion.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(structure, ensure_ascii=False, indent=1), encoding="utf-8")
    manifest_files.append(str(p.relative_to(out)).replace("\\", "/"))

    # ---- placement (colocacion provisional documentada) ----
    placement = {
        "convencion": "unity (X,Y,Z)=(u,cota,v); metros",
        "frame_geometria_exportada": "cada edificio exportado en su propio frame comun local",
        "frame_unity": "X=u, Y=cota, Z=v (aplicada UNA vez en el exportador)",
        "junta": {
            "id": "JD_EI_EII_10CM",
            "ancho_m": 0.10,
            "cara_EII_x_local": 27.85,
            "cara_EI": "por_correlacionar (fuera del JSON EII)",
            "ejes": "D-D' Fase 2",
            "estado": "por_correlacionar",
        },
        "colocacion_global": "provisional",
        "dato_necesario_para_resolver": (
            "Coordenada de la cara/limite este del Edificio I en el sistema comun del "
            "Edificio II a lo largo del eje de la junta (correlacionar eje D-D' de EI "
            "con la cara x=27.85 de EII via captura/medicion conjunta de las paginas "
            "19/20). Con ese valor se fija la traslacion relativa EI->EII y se deja de "
            "ser provisional."),
        "edificios": {
            "II": {"posicion_unity": [0.0, 0.0, 0.0], "rotacion_unity": [0, 0, 0],
                   "nota": "oriigen en su propio frame comun (A x 1 en [0,0])"},
            "I": {
                "posicion_unity": [60.0, 0.0, 0.0],  # PROVISIONAL (comparativa, sin traslacion validada)
                "rotacion_unity": [0, 0, 0],
                "nota": ("PROVISIONAL: traslacion de comparacion para que ambos edificios "
                         "no se solapen hasta correlacionar la junta. NO representa el "
                         "desplazamiento fisico real EI<->EII (por_correlacionar)."),
            },
        },
        "no_union_estructural": True,
    }
    p = out / "placement.json"
    p.write_text(json.dumps(placement, ensure_ascii=False, indent=1), encoding="utf-8")
    manifest_files.append("placement.json")

    # ---- manifest ----
    manifest = {
        "nombre": "paquete_visual_edificios_I_II",
        "version": "1.0",
        "generado_por": "tools/export_lab_data.py (lab FE, sin re-ejecutar analisis)",
        "unidades": {"longitud": "m", "carga": "kN", "carga_superficial": "kN/m2"},
        "cadena_transformacion": "comun(u,v,cota) -> unity(X,Y,Z)=(u,cota,v); aplicada una sola vez",
        "ejecucion_fuente_Edificio_I": {
            "id": "primera_ejecucion",
            "mult": 1000.0, "subdivision_vigas": 1,
            "n_nodos": structure["modelo"]["n_nodos"],
            "nota": ("Referencia de resultados del edificio I. La ejecucion subdiv4 es "
                     "PROVISIONAL (V.S.I. pendiente, max_disp 12.68 m no validado) y NO se "
                     "usa como dato definitivo."),
        },
        "Edificio_II": {
            "stado": "geometria_adaptada_sin_solucion_FE",
            "nota": ("Solo geometria/adaptaciones respaldadas; sin tributaria real ni "
                     "resultados estructurales. Se visualiza igual aunque el analisis este "
                     "pendiente. El ensayo CP2 1 kPa es unitario y NO se usa como dato."),
        },
        "estados_validacion": {
            "I": "completo_para_ensayo / solucion laboratorio no utilizable para diseno",
            "II": "geometria revisada / solucion FE PENDIENTE",
        },
        # Candidatas por nivel (solo identificacion; geometrica_NOTA en cada archivo)
        "candidatas": {
            "I/P4": {
                "tipo": "candidata con traslacion de vigas +0.18 m en v",
                "fuente": "2017_67-103.dxf",
                "archivo_fuente": EI_ARCHIVO["P4"],
                "ejes_vigas": {"sur": 0.18, "interior": 9.08, "norte": 16.33},
                "vigas_trasladadas": 41,
                "nota": ("Las areas tributarias y resultados FE (execucion primaria) "
                         "corresponden a la GEOMETRIA PREVIA de P4 (vigas en v=0/8.9/16.15) "
                         "y NO estan revalidados para esta candidata."),
            }
        },
        "archivos": sorted(_with_tributary_regions(out, manifest_files)),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print("\nPaquete escrito en:", out)
    print("n_archivos:", len(manifest_files))

    # Correccion candidata del marco de acero I'-J (ver tools/apply_plan_frames.py):
    # se aplica SIEMPRE despues de exportar para que regenerar lab_data no la pierda.
    from apply_plan_frames import apply_correction
    print("\nAplicando correccion de plano (marco acero I'-J):")
    print(" ", apply_correction(out / "edificios" / "I" / "geometry"))


if __name__ == "__main__":
    sys.exit(main())
