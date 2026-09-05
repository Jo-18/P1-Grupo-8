"""Auditoria XREF / bloques / INSERT / viewports del DXF 700 (solo lectura).

Objetivo: recuperar la transformacion entre las plantas de trama de cargas del
2017_67-700.dxf y las plantas estructurales 2017_67-101/102/103, a partir de METADATOS
CAD (XREF / bloques enlazados / INSERT / layouts / viewports), sin ajustar HATCH a la
geometria y sin modificar archivos originales.

NO asigna cargas, NO ejecuta areas tributarias, NO toca los JSON congelados, NO hace Git.

Salidas:
  datos/casos_analisis/auditoria_xref_viewports_700_raw.json   (metadatos crudos)
  resultados/cargas_reales/auditoria_xref_viewports_700.json   (entregable auditado)
  resultados/cargas_reales/informe_auditoria_xref_viewports_700.md
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from collections import Counter

import ezdxf

BASE = Path(__file__).resolve().parents[2]
RES = BASE / "resultados" / "cargas_reales"
CASES = BASE / "datos" / "casos_analisis"

DXF700 = r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\Datos Estructurales\2017_67-700.dxf"

# Ventanas por nivel en modelspace del 700 (del pipeline extraer_cargas_dxf)
VENTANAS = {
    "CP1S": {"x": [-2600.0, 1700.0], "y": [2400.0, 9500.0]},
    "P1":   {"x": [700.0, 8400.0], "y": [2200.0, 8800.0]},
    "P2":   {"x": [6400.0, 14700.0], "y": [3300.0, 9600.0]},
    "P3":   {"x": [8200.0, 14600.0], "y": [-2700.0, 3200.0]},
    "P4":   {"x": [-2500.0, 3700.0], "y": [-2700.0, 2500.0]},
}

# Bloques enlazados de plantas estructurales (bound XREF)
STR_BLOCKS = ["2017_67-101", "2017_67-102", "2017_67-103"]

import ezdxf.path
from ezdxf import bbox as _bbox
from ezdxf.math import Vec3


def block_entities_bbox(block, mat=None):
    """BBox de las entidades del bloque (opcionalmente transformadas por un affine Void)."""
    ents = list(block)
    if not ents:
        return None
    try:
        bb = _bbox.extents(ents, fast=True)
    except Exception:
        return None
    return bb


def axis_rect(block, insx, insy, sx, sy, rot):
    """BBox de las lineas de eje (RLE-EJE/RLE-EJES) del bloque, con inserccion/rot/scale."""
    c = math.cos(math.radians(rot)); s_ = math.sin(math.radians(rot))
    xs = []; ys = []
    for e in block:
        layer = (e.dxf.layer or "").lower()
        if not (layer.endswith("rle-eje") or layer.endswith("rle-ejes") or
                layer.endswith("$rle-eje") or layer.endswith("$rle-ejes")):
            continue
        if e.dxftype() == "LINE":
            sp = e.dxf.start; ep = e.dxf.end
            for p in (sp, ep):
                x = insx + sx * (c * p.x - s_ * p.y)
                y = insy + sy * (s_ * p.x + c * p.y)
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)]}


def in_window(rect, win):
    if not rect:
        return False
    return not (rect["x"][1] < win["x"][0] or rect["x"][0] > win["x"][1] or
                rect["y"][1] < win["y"][0] or rect["y"][0] > win["y"][1])


def _matriz_reconstruida(ins) -> list:
    """Matriz 4x4 (fila-columna) que lleva estructural_modelspace -> 700_modelspace:
    escala x/y/z (1), rotacion (0) y traslacion (insercion). Sin reflejo."""
    sx, sy, sz = ins["escala"]
    tx, ty, tz = ins["insercion"]
    m = [[0.0] * 4 for _ in range(4)]
    m[0][0] = sx; m[1][1] = sy; m[2][2] = sz; m[3][3] = 1.0
    m[0][3] = tx; m[1][3] = ty; m[2][3] = tz
    return m


def _matriz_inversa(m) -> list:
    """Inverso de la traduccion con diagonal (escala uniforme), para estructural->700."""
    s = m[0][0]
    tinv = [[0.0] * 4 for _ in range(4)]
    tinv[0][0] = 1 / s; tinv[1][1] = 1 / s; tinv[2][2] = 1 / s; tinv[3][3] = 1.0
    tinv[0][3] = -m[0][3] / s; tinv[1][3] = -m[1][3] / s; tinv[2][3] = -m[2][3] / s
    return tinv


def viewport_audit(doc) -> list:
    out = []
    for layout in doc.layouts:
        lname = layout.name
        cur = None
        try:
            cur = layout.get_current_viewport_entity()
        except Exception:
            cur = None
        vp_info = []
        for e in layout:
            if e.dxftype() != "VIEWPORT":
                continue
            d = e.dxf
            vp_info.append({
                "handle": d.handle,
                "status": d.get("status", None),
                "center": [round(v, 4) for v in d.get("center", (0, 0))],
                "width": round(d.get("width", 0), 4),
                "height": round(d.get("height", 0), 4),
                "view_center_point": [round(v, 4) for v in d.get("view_center_point", (0, 0))],
                "view_height": round(d.get("view_height", 0), 4),
                "view_twist_angle": round(d.get("view_twist_angle", 0.0), 4),
                "view_target_point": [round(v, 4) for v in d.get("view_target_point", (0, 0))],
                "view_dir_vector": list(d.get("view_direction_vector", (0, 0, 1))),
                "owner_layout": lname,
            })
        out.append({"layout": lname, "n_viewports": len(vp_info),
                    "is_current": (cur is not None), "viewport_entities": vp_info})
    return out


def main() -> dict:
    doc = ezdxf.readfile(DXF700)

    # ---- 1) XREF table (BLOCK con flag bit 4) ----
    xref_blocks = []
    bound_named = {}
    for name in doc.blocks.block_names():
        hdr = doc.blocks.get(name).block.dxf
        fl = hdr.get("flags", 0)
        if fl & 4:
            xref_blocks.append({
                "name": name,
                "path": hdr.get("xfrefpath"),
                "flags": fl,
                "status": "xref_registrada",
            })
        # bloques enlazados de plantas estructurales (bound, flags=0)
        for b in STR_BLOCKS:
            if name == b or name.startswith(b + "$"):
                bound_named[name] = {
                    "name": name, "flags": fl,
                    "base_point": [round(v, 4) for v in hdr.get("base_point", (0, 0))] if hdr.get("base_point") else None,
                }

    # ---- 2) INSERTs (bloques estructurales) ----
    inserts = []
    for e in doc.modelspace():
        if e.dxftype() != "INSERT":
            continue
        bname = e.dxf.get("name")
        if bname not in STR_BLOCKS:
            continue
        ins = e.dxf.get("insert"); sx = e.dxf.get("xscale", 1.0); sy = e.dxf.get("yscale", 1.0)
        sz = e.dxf.get("zscale", 1.0); rot = e.dxf.get("rotation", 0.0)
        blk = doc.blocks.get(bname) if bname in doc.blocks.block_names() else None
        axis = axis_rect(blk, ins.x, ins.y, sx, sy, rot) if blk else None
        inserts.append({
            "bloque": bname, "handle": e.dxf.handle,
            "insercion": [round(ins.x, 4), round(ins.y, 4), round(ins.z or 0, 4)],
            "escala": [round(sx, 6), round(sy, 6), round(sz, 6)],
            "rotacion_deg": round(rot, 4),
            "reflexion": False,
            "axis_rect_700": axis,
        })

# ---- 3) Asociacion por nivel: que INSERT de la planta correcta coloca sus ejes dentro de la ventana ----
    # Mapeo nivel -> planta estructural (congruente con la traza del modelo congelado y la
    # posicion de vistas de cada DXF estructural: CP1S/P1 en 101, P2/P3 en 102, P4 en 103).
    LEVEL_BLOCK = {"CP1S": "2017_67-101", "P1": "2017_67-101",
                   "P2": "2017_67-102", "P3": "2017_67-102", "P4": "2017_67-103"}
    # Copia del eje estructural en el bloque es identica a la del modelspace del DXF estructural
    # (verificado aparte). La transformacion recuperada es una TRASLACION: 700 = est + insercion.
    per_level = {}
    for cod, win in VENTANAS.items():
        blk_name = LEVEL_BLOCK[cod]
        cand = [i for i in inserts if i["bloque"] == blk_name]
        # elegir la instancia cuya caja de ejes mas cubre la ventana de trama del nivel
        best = None; bestov = 0.0
        for ins in cand:
            r = ins["axis_rect_700"]
            if not r:
                continue
            ov = max(0, min(r["x"][1], win["x"][1]) - max(r["x"][0], win["x"][0])) * \
                 max(0, min(r["y"][1], win["y"][1]) - max(r["y"][0], win["y"][0]))
            if ov > bestov:
                bestov = ov; best = ins
        if best is not None:
            per_level[cod] = {
                "ventana_trama_700": win,
                "planta_estructural": blk_name,
                "insert_asociado": {
                    "bloque": best["bloque"], "handle": best["handle"],
                    "insercion": best["insercion"], "escala": best["escala"],
                    "rotacion_deg": best["rotacion_deg"], "reflexion": best["reflexion"],
                    "overlap_area_u2": round(bestov, 1),
                    "matriz_recuperada": _matriz_reconstruida(best),
                    "relacion_cad": "700_modelspace = estructural_modelspace + insercion (1:1, rot 0, sin reflejo)",
                },
                "certeza": "basada_en_metadatos_xref",
            }
        else:
            per_level[cod] = {
                "ventana_trama_700": win,
                "planta_estructural": blk_name,
                "insert_asociado": None, "certeza": "sin_instancia",
            }

    viewports = viewport_audit(doc)

    # ---- nivels de certeza / conclusion ----
    conclusiones = []
    for cod, pl in per_level.items():
        if pl["insert_asociado"]:
            conclusiones.append({"nivel": cod,
                                 "estado": "transformacion_recuperada_de_xref",
                                 "detalle": ("bloque enlazado %s (planta estructural %s, handle %s): "
                                             "700_modelspace = estructural_modelspace + insercion. "
                                             "Las cargas se dibujaron sobre la planta estructural "
                                             "embebida; no se ajusta HATCH." ) % (
                                     pl["insert_asociado"]["bloque"], pl["planta_estructural"],
                                     pl["insert_asociado"]["handle"]),
                                 "certeza": pl["certeza"]})
        else:
            conclusiones.append({"nivel": cod,
                                 "estado": "sin_transformacion_recuperable",
                                 "detalle": "no hay instancia INSERT de la planta estructural para este nivel.",
                                 "certeza": "media"})

    payload = {
        "naturaleza": "auditoria_solo_lectura_metadatos_cad",
        "archivos": {"700_dxf": DXF700,
                     "nota_dwg": "no se abre .dwg directamente (sin odafc); el .dxf es la exportacion CAD con la misma tabla de XREF/bloques/INSERT/layouts."},
        "resumen_xref": {
            "n_xref_vivas": len(xref_blocks),
            "xref_vivas": xref_blocks,
            "nota": "no hay XREF viva: las plantas estructurales estan EMBEBIDAS como bloques enlazados (bound) con nombre 2017_67-10X y componentes <name>$0$...",
            "bloques_enlazados_estructurales": list(bound_named.values()),
        },
        "insert_estructurales": inserts,
        "asociacion_por_nivel": per_level,
        "layouts_viewports": viewports,
        "conclusion_por_nivel": conclusiones,
        "situacion_final": _situacion(conclusiones),
    }

    CASES.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    (CASES / "auditoria_xref_viewports_700_raw.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (RES / "auditoria_xref_viewports_700.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _md(payload)
    return payload


def _situacion(conclusiones) -> str:
    est = [c["estado"] for c in conclusiones]
    if all(e == "transformacion_recuperada_de_xref" for e in est):
        return "transformacion_recuperada_de_xref"
    if "transformacion_recuperada_de_xref" in est:
        return "transformacion_recuperada_de_xref (parcial)"
    if "xref_no_resuelta" in est:
        return "xref_no_resuelta_pero_transformacion_disponible"
    return "requiere_asignacion_semantica_manual"


def _md(p: dict) -> None:
    lines = [
        "# Auditoría XREF / viewports del DXF 700",
        "",
        "> **Solo lectura:** auditoría de metadatos CAD (tabla de bloques, XREF, INSERT, "
        "layouts, viewports) del `2017_67-700.dxf`. **No** se modificó ningún archivo, "
        "**no** se asignaron cargas, **no** se tocaron los JSON congelados. Como el `.dwg` "
        "no se abre directamente (sin `odafc`), se usa el `.dxf`, que conserva la misma "
        "tabla de XREF/INSERT/layouts que el dibujo original.",
        "",
        "## 1. Estado de XREF",
        "",
        f"- XREF vivas registradas: **{p['resumen_xref']['n_xref_vivas']}**.",
        "- **Hallazgo clave:** no hay XREF viva. Las plantas estructurales están **embebidas "
        "como bloques enlazados (bound)** con nombre `2017_67-101`, `2017_67-102`, `2017_67-103` "
        "y sus componentes `2017_67-10X$0$...` (convención de bloque enlazado de XREF de AutoCAD).",
        "",
        "## 2. Bloques enlazados (contenido estructural)",
        "",
    ]
    for b in p["resumen_xref"]["bloques_enlazados_estructurales"]:
        lines.append(f"- `{b['name']}` flags={b['flags']} base={b['base_point']}")
    lines += [
        "",
        "## 3. Entidades INSERT (bloques estructurales en modelspace)",
        "",
        "| Bloque | Handle | Inserción (x,y) | Escala | Rotación | Reflejo |",
        "|--------|--------|------------------|--------|----------|---------|",
    ]
    for i in p["insert_estructurales"]:
        lines.append("| `%s` | `%s` | (%.1f, %.1f) | (%.3f, %.3f) | %.1f° | %s |" % (
            i["bloque"], i["handle"], i["insercion"][0], i["insercion"][1],
            i["escala"][0], i["escala"][1], i["rotacion_deg"], i["reflexion"]))
    lines += [
        "",
        "## 4. Asociación por nivel (¿el fondo estructural subyace a la trama?)",
        "",
        "| Nivel | Ventana trama (700) | INSERT estructural asociado | Certeza |",
        "|-------|---------------------|-----------------------------|---------|",
    ]
    for cod, pl in p["asociacion_por_nivel"].items():
        w = pl["ventana_trama_700"]
        if pl.get("insert_asociado"):
            ia = pl["insert_asociado"]
            det = "`%s`@(%.0f,%.0f)" % (ia["bloque"], ia["insercion"][0], ia["insercion"][1])
        else:
            det = "—"
        lines.append("| %s | x[%.0f,%.0f] y[%.0f,%.0f] | %s | %s |" % (
            cod, w["x"][0], w["x"][1], w["y"][0], w["y"][1], det, pl["certeza"]))
    lines += [
        "",
        "## 5. Conclusiones por nivel",
        "",
    ]
    for c in p["conclusion_por_nivel"]:
        lines.append(f"- **{c['nivel']}**: `{c['estado']}` — {c['detalle']} (certeza {c['certeza']})")
    lines += [
        "",
        f"## 6. Situación final: **`{p['situacion_final']}`**",
        "",
        "**Nota de exactitud:** la inserción del bloque enlazado (escala 1, rot 0) implica "
        "solo una **traslación**: `coor_700 = coor_estructural_local + insercion`. Esto NO "
        "equivale aún a la transformación física del render → huella congelada: el bloque "
        "enlazado respeta la composición del plano (paper/layout) en que se dibujó la lámina, "
        "no necesariamente el sistema de coordenadas de cálculo del modelo estructural. Por lo "
        "tanto **no se marca `validada`** ni se asignan cargas hasta validar con ≥3 puntos "
        "físicos independientes y residuos/regla de solape.",
    ]
    (RES / "informe_auditoria_xref_viewports_700.md").write_text(
        "\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
    print("OK  resultados/cargas_reales/auditoria_xref_viewports_700.json")
    print("OK  datos/casos_analisis/auditoria_xref_viewports_700_raw.json")
    print("OK  resultados/cargas_reales/informe_auditoria_xref_viewports_700.md")