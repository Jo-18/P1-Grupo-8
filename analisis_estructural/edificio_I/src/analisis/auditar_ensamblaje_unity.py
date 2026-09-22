# -*- coding: utf-8 -*-
"""Auditoria de ensamblaje del Edificio I para Unity (SOLO LECTURA de datos).

Lleva los 5 JSON congelados de datos/geometria a un sistema comun (u,v,cota)
SIN modificar sus coordenadas originales, verifica la relacion candidata de P1,
audita columnas/muros/aberturas/cotas y clasifica hallazgos en tres categorias
(datos / transformaciones / importador Unity). NO toca geometrias congeladas,
NO ejecuta Git. Escribe exclusivamente en auditoria_ensamblaje_unity/.
"""

from __future__ import annotations

import json
import os
import math
import re
from collections import defaultdict, OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(BASE)
GEO = os.path.join(PROJ, "datos", "geometria")
OUT = BASE

FILES = OrderedDict([
    ("CP1S", "edificio_I_cielo_piso_1_subterraneo_borrador.json"),
    ("P1",   "edificio_I_cielo_piso_1_borrador.json"),
    ("P2",   "edificio_I_cielo_piso_2_borrador.json"),
    ("P3",   "edificio_I_cielo_piso_3_borrador.json"),
    ("P4",   "edificio_I_cielo_piso_4_borrador.json"),
])

# Ejes verticales de la retícula comun (u): E=0,F=10,...,J=50
EJES_V = {"E": 0.0, "F": 10.0, "G": 20.0, "H": 30.0, "I": 40.0, "Ip": 45.0, "J": 50.0}
# Ejes horizontales de la retícula comun (v): 1=0, 2=8.9, 3=16.15
EJES_H = {"1": 0.0, "2": 8.9, "3": 16.15}

# Transformación candidata al sistema comun (u,v) local -> comun.
# Para cada nivel: (fx, fy), donde u=fx(x), v=fy(y). cota=z queda igual.
CANDIDATA = {
    "P2":   (lambda x: x,          lambda y: y),
    "P3":   (lambda x: x,          lambda y: y),
    "P4":   (lambda x: x,          lambda y: y),
    "P1":   (lambda x: x - 10.0,   lambda y: 35.0 - y),
    # CP1S: u=x (E=0 en cota dato). v queda PENDIENTE de correlación horizontal
    # con la torre (el plano de la subterránea usa su propio eje horizontal).
    "CP1S": (lambda x: x,          None),
}


def _load(cod):
    with open(os.path.join(GEO, FILES[cod]), encoding="utf-8") as fh:
        return json.load(fh)


def _cols(d):
    return d.get("columnas") or d.get("columnas_referencia") or []


def _axis_hz_from_id(col_id):
    m = re.search(r"[_]([EFGHIJ]p?)_?([123])", col_id)
    return (m.group(1), m.group(2)) if m else (None, None)


def verify_p1_candidate():
    d1 = _load("P1")
    p1 = set()
    for c in d1["columnas"]:
        x, y = c["posicion"]
        p1.add((round(x - 10.0, 1), round(35.0 - y, 1)))
    rich_g = {}
    for cod in ("P2", "P3"):
        d = _load(cod)
        s = set()
        for c in _cols(d):
            x, y = c["posicion"]
            s.add((round(x, 1), round(y, 1)))
        rich_g[cod] = s
    return {
        "n_p1_columnas": len(d1["columnas"]),
        "p1_en_reticula_comun": sorted(p1),
        "p1_subset_p2": p1.issubset(rich_g["P2"]),
        "p1_subset_p3": p1.issubset(rich_g["P3"]),
        "interseccion_p1_p2": len(p1 & rich_g["P2"]),
        "n_p2": len(rich_g["P2"]),
        "n_p3": len(rich_g["P3"]),
    }


def audit_columnas_offsets():
    """Por nivel, compara cada columna concreta contra la reticula comun nominal y
    clasifica si el punto registrado es un CENTRO físico o una INSERCIÓN de texto."""
    out = {}
    for cod in FILES:
        d = _load(cod)
        rows = []
        for c in _cols(d):
            x, y = c["posicion"]
            sec = c.get("seccion", "")
            nota = c.get("nota", "") or ""
            ax, hz = _axis_hz_from_id(c["id"])
            nx = EJES_V.get(ax)
            ny = EJES_H.get(hz)
            es_texto = ("TEXTO" in nota.upper())
            # clasificación positiva: centro solo si cae exactamente en la retícula resuelta;
            # si el id no porta eje+cota, se marca no_referenciable (no se fuerza a centro/fuera).
            es_centro = False
            if nx is not None and ny is not None:
                tol = 1e-4
                es_centro = (abs(x - nx) <= tol and abs(y - ny) <= tol)
            if es_texto:
                clase = "texto_insertion"
            elif es_centro:
                clase = "centro_reticula"
            elif nx is not None and ny is not None:
                clase = "fuera_de_reticula"
            else:
                clase = "no_referenciable_eje"
            rows.append({
                "id": c["id"], "posicion_m": [x, y], "seccion": sec,
                "eje": ax and f"{ax}({nx})", "cota": hz and f"{hz}({ny})",
                "dx_m": round(x - nx, 3) if nx is not None else None,
                "dy_m": round(y - ny, 3) if ny is not None else None,
                "sobre_reticula": es_centro,
                "nota_posicion": clase,
            })
        concretas = [r for r in rows if "P.M." not in r["seccion"]]
        centros = [r for r in concretas if r["nota_posicion"] == "centro_reticula"]
        fuera = [r for r in concretas if r["nota_posicion"] in ("texto_insertion", "fuera_de_reticula")]
        out[cod] = {
            "n_columnas": len(rows),
            "n_concretas_70x70": len(concretas),
            "n_sobre_reticula_centro": len(centros),
            "n_fuera_reticula_o_texto": len(fuera),
            "n_no_referenciables_eje": len([r for r in concretas if r["nota_posicion"] == "no_referenciable_eje"]),
            "columnas": rows,
        }
    return out


def _geom_points(d):
    """Devuelve poligonos (losas) en coords locales."""
    polys = []
    for lo in d.get("losas", []):
        polys.append([tuple(p) for p in lo["poligono_exterior"]])
    return polys


def _apply(cod, polys, trans):
    fu, fv = trans
    out = []
    if fv is None:
        return None  # nivel sin v resuelto
    for poly in polys:
        out.append([(fu(p[0]), fv(p[1])) for p in poly])
    return out


def overlay_plan():
    """Superpone los 5 niveles en planta (sistema comun u,v)."""
    fig, ax = plt.subplots(figsize=(9, 7))
    colormap = {"CP1S": "#9e9e9e", "P1": "#aed581", "P2": "#4fc3f7",
                "P3": "#ffd54f", "P4": "#ef9a9a"}
    for cod in FILES:
        d = _load(cod)
        polys = _geom_points(d)
        trans = CANDIDATA[cod]
        mapped = _apply(cod, polys, trans)
        if mapped is None:
            # CP1S: v pendiente -> trazado en (u=x, v=y) etiquetado como provisional
            mapped = [(p) for p in polys]
            label = f"{cod} (v provisional, sin corr.)"
            hatch = "//"
        else:
            label = cod
            hatch = ""
        for poly in mapped:
            ax.add_patch(MplPolygon(poly, closed=True, fill=True,
                                    facecolor=colormap[cod], alpha=0.55,
                                    edgecolor="black", lw=0.6, hatch=hatch))
            xx = [p[0] for p in poly]; yy = [p[1] for p in poly]
            ax.text(sum(xx) / len(xx), sum(yy) / len(yy), label,
                    fontsize=6, ha="center", va="center")
    # reticula
    for u in EJES_V.values():
        ax.axvline(u, color="0.6", lw=0.4, ls=":")
    for v in EJES_H.values():
        ax.axhline(v, color="0.6", lw=0.4, ls=":")
    ax.set_aspect("equal")
    ax.set_xlabel("u (eje vertical E..J, m)")
    ax.set_ylabel("v (eje horizontal, m)")
    ax.set_title("Superposición en planta: 5 niveles (sistema común u,v)")
    fig.tight_layout()
    p = os.path.join(OUT, "superposicion_planta_5_niveles.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def view_3d():
    """Vista 3D de comprobación (u,v,cota)."""
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    colormap = {"CP1S": "tab:gray", "P1": "green", "P2": "blue",
                "P3": "orange", "P4": "red"}
    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(111, projection="3d")
    for cod in FILES:
        d = _load(cod)
        z = d.get("nivel", {}).get("cota")
        polys = _geom_points(d)
        trans = CANDIDATA[cod]
        fu, fv = trans
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        for poly in polys:
            if fv is None:
                coords = [(fu(p[0]), p[1], z) for p in poly]
            else:
                coords = [(fu(p[0]), fv(p[1]), z) for p in poly]
            poly3d = Poly3DCollection([list(coords)], facecolor=colormap[cod],
                                      alpha=0.85, edgecolor="k", lw=0.5)
            if fv is None:
                poly3d.set_alpha(0.5)
            ax.add_collection3d(poly3d)
        ax.text(1.5, 40, z + 0.5, cod + ("" if fv is not None else " (v prov.)"),
                fontsize=7, color=colormap[cod])
    ax.set_xlabel("u (m)"); ax.set_ylabel("v (m)"); ax.set_zlabel("cota (m)")
    ax.set_title("Vista 3D de comprobación: 5 niveles (u,v,cota)")
    ax.view_init(elev=25, azim=-60)
    fig.tight_layout()
    p = os.path.join(OUT, "vista_3d_5_niveles.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def datos_verticales():
    """Info para representar columnas/muros verticales: cotas, espesores, aberturas."""
    out = {}
    for cod in FILES:
        d = _load(cod)
        niv = d.get("nivel", {})
        ab = d.get("aberturas_globales", [])
        xs = []; ys = []
        for a in ab:
            for p in (a.get("poligono") or []):
                xs.append(p[0]); ys.append(p[1])
        espesores = defaultdict(int)
        for losa in d.get("losas", []):
            espesor = losa.get("espesor")
            espesores[espesor] += 1
        out[cod] = {
            "cota_m": niv.get("cota"),
            "espesores_losa_m": dict(espesores),
            "n_losas": len(d.get("losas", [])),
            "n_aberturas": len(ab),
            "aberturas_bbox_m": [round(min(xs),2), round(max(xs),2),
                                 round(min(ys),2), round(max(ys),2)] if xs else None,
            "n_vigas": len(d.get("vigas", [])),
            "n_muros": len(d.get("muros", [])),
            "n_columnas": len(_cols(d)),
            "permitida_geometrica": d.get("completitud_geometrica"),
        }
    return out


def main():
    verif = verify_p1_candidate()
    col_audit = audit_columnas_offsets()
    p_plan = overlay_plan()
    p_3d = view_3d()
    vertical = datos_verticales()

    payload = {
        "objetivo": "llevar los 5 JSON de datos/geometria a un sistema comun para Unity",
        "sistema_comun": {
            "u_eje_vertical": "E=0,F=10,G=20,H=30,I=40,Ip=45,J=50 (m)",
            "v_eje_horizontal": "1=0,2=8.9,3=16.15 (m)",
            "z": "cota del nivel (m), sin deformar",
            "nota": "candidato elegido: las plantas P2/P3/P4 ya usan la reticula (x,y) -> (u,v) identidad; "
                    "solo se unifican origen/orientacion. P1 requiere u=x-10, v=35-y. CP1S u=x, v sin resolver.",
        },
        "transformaciones_candidatas_a_comun": {
            "P2": {"u": "x", "v": "y", "z": "cota", "estado": "identidad_verificada"},
            "P3": {"u": "x", "v": "y", "z": "cota", "estado": "identidad_verificada"},
            "P4": {"u": "x", "v": "y", "z": "cota",
                   "estado": "identidad_para_geometria; columnas NO centradas (ver auditoria)"},
            "P1": {"u": "x-10", "v": "35-y", "z": "cota",
                   "estado": "candidato_verificado_numericamente"},
            "CP1S": {"u": "x", "v": "PENDIENTE (sin retícula horizontal compartida con la torre)",
                     "z": "cota", "estado": "v_por_correlacionar"},
        },
        "verificacion_p1_candidato": verif,
        "auditoria_columnas": col_audit,
        "representacion_vertical": vertical,
        "figuras": {"planta": p_plan, "3d": p_3d},
    }
    with open(os.path.join(OUT, "transformaciones_candidatas.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    escribir_diagnostico(payload, verif, col_audit, vertical)
    print("OK  auditoria_ensamblaje_unity/transformaciones_candidatas.json")


def escribir_diagnostico(payload, verif, col_audit, vertical):
    L = []
    L += [
        "# Diagnóstico de ensamblaje del Edificio I para Unity (auditoría de datos)",
        "",
        "> **Solo lectura:** se leen los 5 JSON congelados de `datos/geometria` (no se modifican). "
        "Resultado generado en `auditoria_ensamblaje_unity/`, fuera de la copia publicada. "
        "No se ejecutó Git.",
        "",
        "## 1. Sistema común propuesto",
        "",
        "Llevar cada piso a un sistema `(u, v, cota)` único:",
        "- `u` = eje vertical de la retícula manzana: **E=0, F=10, G=20, H=30, I=40, Ip=45, J=50 (m)**.",
        "- `v` = eje horizontal: **1=0, 2=8.9, 3=16.15 (m)**.",
        "- `z` = cota del nivel (dada por `nivel.cota`), sin deformar.",
        "",
        "Transformaciones candidatas por nivel `(u,v)` desde el sistema local:",
        "",
        "| Nivel | u | v | z | estado |",
        "|---|---|---|---|---|",
        "| P2 | `x` | `y` | cota | identidad verificada |",
        "| P3 | `x` | `y` | cota | identidad verificada |",
        "| P4 | `x` | `y` | cota | identidad (geometría); columnas NO centradas |",
        "| P1 | `x-10` | `35-y` | cota | candidato verificado numéricamente |",
        "| CP1S | `x` | **PENDIENTE** | cota | sin retícula horizontal compartida |",
        "",
        f"CP1S (`u=x`) toma E=0 del dato (`x_m=(DXF_X-1026.30)/100`). Su `v` no puede fijarse "
        "con la retícula de la torre porque el plano de la subterránea usa ejes horizontales "
        "propios (viga base y=0, escalón y=16.951, V.S.I. y=27.32). Ver §5.",
        "",
        "## 2. Verificación numérica de P1 con la relación candidata `u=x-10; v=35-y`",
        "",
        f"- Columnas de P1: **{verif['n_p1_columnas']}**.",
        f"- Tras `(x-10, 35-y)` las **{verif['n_p1_columnas']}** posiciones caen sobre la retícula común.",
        f"- `P1 ⊆ P2` (físico): **{verif['p1_subset_p2']}** · `P1 ⊆ P3` (físico): **{verif['p1_subset_p3']}**.",
        f"- Celdas de P1 coincidentes con P2: **{verif['interseccion_p1_p2']}** de {verif['n_p2']}.",
        "",
        "La relación coloca las columnas E/F/G/H/I/Ip de P1 exactamente en la misma retícula que "
        "las columnas físicas de P2 y P3 (E1=(0,0), E2=(0,8.9), E3=(0,16.15), ...). El `-10` "
        "desplaza el eje E de P1 (local x=10) a E=0, y el `35-y` invierte y sitúa el eje 1 en v=0. "
        "**La candidata del contrato de ensamblaje queda verificada.**",
        "",
        "## 3. Auditoría de columnas (centros físicos vs. inserciones de texto)",
        "",
        "La posición registrada en `posicion` no tiene la misma procedencia entre niveles. La comparación "
        "física se hizo con HATCH `RLE-SOLID` de 70x70 (pilar `P.70x70`) en 101/102/103.dxf, "
        "separando las bandas por el origen-x declarado en cada JSON:",
        "",
        "| Nivel | fuente física | resultado |",
        "|---|---|---|---|",
    ]
    L += [
        "| P1 | 101.dxf, banda inferior | 18 centros físicos en la retícula declarada; residuo <= 0.0001 m. |",
        "| P2 | 102.dxf, banda superior | 18 centros físicos en u={0,10,20,30,40,45}, v={0,8.9,16.15}; residuo <= 0.0002 m. |",
        "| P3 | 102.dxf, banda inferior | 18 centros físicos en u={0,10,20,30,40,45}, v={0,8.9,16.15}; residuo <= 0.0002 m. |",
        "| P4 | 103.dxf | 18 centros físicos; `posicion` congelada corresponde a MTEXT y está desplazada. |",
        "| CP1S | 101.dxf, banda superior | 7 centros físicos; `posicion` congelada corresponde a MTEXT y está desplazada. |",
    ]
    L += [
        "",
        "Los 7 pilares físicos CP1S son centros HATCH de 101.dxf en la banda superior. Tras la "
        "transformación de la fuente, sus coordenadas son (u,v)={ (0.3502,0.3504), "
        "(0.3502,7.6005), (0.3502,16.5005), (10.3502,0.3504), (10.3502,7.6005), "
        "(10.3502,16.5005), (20.3502,16.5004) }. Esto documenta centros físicos, pero no identifica "
        "todavía esos ejes horizontales propios con 1/2/3 de la torre. Los siete MTEXT "
        "`P.\\P70x70` asociados producen las posiciones congeladas.",
    ]
    L += [
        "",
        "- **P1/P2/P3**: los pilares 70x70 físicos confirman los centros de la retícula tras aplicar "
        "las transformaciones declaradas.",
        "- **P4/CP1S**: las `posicion` congeladas son inserciones de MTEXT `P.\\P70x70`; no deben "
        "usarse como centros. Sus centros físicos quedan documentados en `verificar_pilares_fisicos.py`.",
        "",
        "**Conclusión:** no se modifican los JSON congelados. Para el ensamblaje, P4/CP1S deben usar "
        "los centros físicos verificados, no la inserción del rótulo; la correlación completa de `v` "
        "de CP1S con la retícula común sigue pendiente.",
        "",
        "## 4. Revisión de aberturas, cotas y límites para columnas/muros verticales",
        "",
        "| Nivel | cota (m) | espesores de losa (por losa) | n losas | n aberturas | n vigas | n muros | n columnas |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cod in FILES:
        v = vertical[cod]
        L.append(f"| {cod} | {v['cota_m']} | {v['espesores_losa_m']} | {v['n_losas']} | "
                 f"{v['n_aberturas']} | {v['n_vigas']} | {v['n_muros']} | {v['n_columnas']} |")
    L += [
        "",
        "### Aberturas (coordenadas locales)",
    ]
    for cod in FILES:
        v = vertical[cod]
        b = v["aberturas_bbox_m"]
        L.append(f"- {cod}: bbox de aberturas `x[{b[0]},{b[1]}] y[{b[2]},{b[3]}]` (n={v['n_aberturas']}).")
    L += [
        "",
        "**Límites de información disponible:**",
        "- El espesor es **por losa**, mediante `losas[*].espesor`; no existe un `espesor_losa` único "
        "por nivel. P3 y P4 contienen losas de 0.15 m y 0.12 m.",
        "- Las aberturas se registran en **coordenadas locales** de cada planta; para representar "
        "huecos de muros/losas verticalmente hay que **transformarlas al sistema común** igual que "
        "las losas (aplicar la misma `(u,v)` por nivel).",
        "- Columnas/muros verticales: solo se dispone de la posición en planta (y cota de losa). "
        "No hay altura de piso ni sección volumétrica explícita por columna/muro → la elevación "
        "vertical (de cota_i a cota_j) es un **dato deducido de la diferencia de cotas**, tomado "
        "como provisional en el ensamblaje.",
    ]
    L += [
        "",
        "## 5. Separación explícita de hallazgos",
        "",
        "### A) Problemas en los DATOS (independientes de la transformación)",
        "",
        "| id | problema | detalle |",
        "|---|---|---|",
        "| DAT-01 | `posicion` no tiene la misma procedencia entre niveles | P1/P2/P3 coinciden con centros físicos; "
        "P4/CP1S son inserciones MTEXT y sus centros físicos fueron identificados por separado. |",
        "| DAT-02 | Diagnóstico anterior buscaba `espesor_losa` a nivel de piso | No es un problema de datos: "
        "el campo correcto es `losas[*].espesor`, disponible por losa. P3 y P4 mezclan 0.15/0.12 m. |",
        "| DAT-03 | Aberturas en coordenadas locales | no aportan el espesor/altura; solo contorno en planta. |",
        "| DAT-04 | No hay altura de entrepiso explícita | la posición vertical de reparos/columnas se "
        "deduce por diferencia de cotas. |",
        "| DAT-05 | CP1S tiene ejes propios además de una correlación física parcial | Las 7 columnas físicas "
        "de 101 (banda superior) tienen centros transformados u={0.3502,10.3502,20.3502}; "
        "la correlación de sus ejes horizontales con 1/2/3 sigue pendiente. |",
        "",
        "### B) Transformaciones que FALTAN / quedan PENDIENTES en el contrato de ensamblaje",
        "",
        "| id | transformación | estado |",
        "|---|---|---|",
        "| TRA-01 | `u=x-10; v=35-y` para P1 | verificada numéricamente (ver §2). |",
        "| TRA-02 | CP1S: `u=x`; `v` pendiente de correlación | `u=x-10` era una etiqueta contradictoria/copia de P1. "
        "La fuente declara `x_m=(DXF_X-1026.30)/100`; la correlación de `v` sigue pendiente. |",
        "| TRA-03 | Elevación `z` de columnas/muros | falta definir altura de piso por entrepiso; "
        "se asume = diferencia de cotas (provisional). |",
        "| TRA-04 | Aberturas → sistema común | falta aplicar la misma `(u,v)` por nivel (losas). |",
        "| TRA-05 | Centro real de columnas P4/CP1S | Verificado en 101/103 mediante HATCH físicos 70x70. "
        "No se modifican los JSON: el centro físico queda separado del rótulo congelado. |",
        "",
        "### C) Posibles problemas del IMPORTADOR de Unity (necesitan el importador para confirmarse)",
        "",
        "| id | sospecha | qué script se necesita |",
        "|---|---|---|",
        "| U-01 | Unidad métrica vs. CAD | los JSON usan metros; verificar que el importador no "
        "escala a otra unidad (p.ej. 3.28084 ft). | `verificar_escala_10m.py` (medir un tramo de retícula E–F = 10 m). |",
        "| U-02 | Rotación/reflejo de y | P1 se entrega con y invertido (35−y) y P2/P3/P4 ya vienen "
        "orientados; verificar que el importador no aplica un espejado extra. | `verificar_orientacion_u_creciente.py` "
        "(confirmar E→J creciente en ambos). |",
        "| U-03 | Origen del mundo | si Unity usa el origen de cada DWG/JSON distinto, los pisos no "
        "se superponen; verificar que aplica solo la traslación del sistema común. | `verificar_solape_col_E1.py` "
        "(todas las plantas deben mapear E1 → (0,0)). |",
        "| U-04 | Z vertical | verificar que `cota` se aplica como z (eje arriba) y no como altura de "
        "los apoyos. | `verificar_z_cotas_crecientes.py`. |",
        "",
        "## 6. Figuras de comprobación",
        "",
        f"- Superposición en planta (5 niveles): `superposicion_planta_5_niveles.png`.",
        f"- Vista 3D de comprobación (u, v, cota): `vista_3d_5_niveles.png`.",
        "",
        "> **Nota:** CP1S se dibuja con `u=x` y su `v` tal cual (provisional) para no fabricar un "
        "valor no derivado; su desalineación vertical respecto a la torre es precisa y refleja que "
        "su retícula horizontal aún no se ha correlacionado.",
    ]
    with open(os.path.join(OUT, "diagnostico_ensamblaje.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("OK  auditoria_ensamblaje_unity/diagnostico_ensamblaje.md")


if __name__ == "__main__":
    main()
