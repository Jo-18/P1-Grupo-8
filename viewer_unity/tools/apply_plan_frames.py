"""Correccion CANDIDATA del paquete VISUAL del marco de acero I'-J (P3/P4) y del
voladizo NORTE del Edificio I (P1/P2/P4).

INTEGRADO en el flujo de exportacion (se invoca al final de export_lab_data.py), de
modo que regenerar lab_data NO pierde la correccion. Idempotente (re-ejecutar no
dublica ni altera de nuevo: solo toca los IDs ya marcados).

Alcance (verificado contra los DXF de planta; NO se fabrica ninguna coordenada):
  * El plano P3/P4 NO dibuja diagonales en planta (solo existen en la elevacion de
    la lamina 800, ilegible para el modelo): las diagonales y miembros entre forjados
    quedan PENDIENTES.
  * Las "lineas paralelas RLE-VIGA" son caras de la misma viga (concreto V.60/80 /
    V.40/60, ya modeladas); NO se genera un elemento por cara ni se duplica.
  * P3: las columnas de acero IpJ(46.35)/J(48.7)/FS1(20.38)/GS2(30.4) son registros
    'RLE-TEXTO-1' (rotulo 'V.M. 300x300x5') PERO NO caen sobre huella fisica RLE-PILAR
    del plano P3 (verificado: las unicas huellas 70x70 del sector I'-J estan en la fila
    concreta u[44.65,45.35]; no hay huella en u~46.3 ni u~48.7 ni en la franja alta
    v=18.2-18.4). Se reclasifican como RefPendientes (mismo criterio P4: sin huella
    fisica ni geometria respaldada -> no se dibujan como columna estructural completa).
    Los candidatos 'P.M.I.' (JP1-6) ya son RefPendientes.
  * P4 (voladizo norte I'-J): NINGUNA columna de acero del paquete coincide con la
    huella fisica del plano (RLE-PILAR en u=44.92 Ip, 47.46 y 49.79). Todas (IpS1,
    JS2, JS3, JS4, JS5, JS8) proceden de texto (RLE-TEXTO-1) y quedan fuera de la
    geometria fisica: se reclasifican como RefPendientes (marcador visual) para no
    dibujarlas como columnas inventadas. Se les conserva la posicion para trazabilidad.
  * P4 (voladizo NORTE, eje G/H): GS6(21.5,21.03) y HS7(31.55,21.03) NO caen sobre
    huella; las huellas RLE-PILAR del plano P4 (2017_67-103) estan en
    u[19.85,20.15] v[20.30,20.60] y u[29.85,30.15] v[20.30,20.60] (centros
    (20.0,20.45) y (30.0,20.45), dims 0.30x0.30 = P.M. 300x300x20). Se REUBICAN
    sobre la huella (conservan seccion y estado 'confirmado').
  * P2 (voladizo norte): G3S1(18.96,14.79) sin huella; la huella RLE-PILAR del plano
    P2 (2017_67-102) mas cercana es u[17.34,17.64] v[20.12,20.42] (centro
    (17.5,20.27)). Se REUBICA. La segunda huella documentada del voladizo
    ((10.0,20.27)) NO tenia columna modelada: se incorpora por huella RLE-PILAR como
    COL_EI_CP2_RLE_PILAR_10.00_20.27 (ID trazable, ver P2_ADD).
  * P1 (lado norte, esquina E): las losas D_VOL_ESTE_OE/ES (u[33.73,45.35]
    v[16.5,28.84]) no tienen correspondencia en el plano P1 (2017_67-101): en ese
    sector el plano solo muestra la planta de OTRA estructura (pilares/vigas en
    v 18.5-26.4, ejes u 30/40/50 - otro edificio en el mismo plano), no un voladizo
    del Edificio I. Sin soporte fisico ni documento, se ELIMINAN del paquete.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "Assets" / "StreamingAssets" / "lab_data" / "edificios" / "I" / "geometry"

# Huella fisica de las columnas de acero del plano P4 (DXF piso4_103, RLE-PILAR),
# en frame comun (u,v). Una columna se considera respaldada solo si su u cae dentro
# de un intervalo de huella en cualquiera de los niveles. (v niveles ~0.28/9.13/16.35)
P4_PHYSICAL_FOOTPRINTS_U = [(44.57, 45.27), (47.31, 47.61), (49.64, 49.94)]

# Sufijo de IDs P4 del paquete (todas 'P.M. 300x300x20' desde RLE-TEXTO-1).
P4_STEEL = ["COL_EI_CP4_S_IpS1_45.97", "COL_EI_CP4_S_JS2_48.77", "COL_EI_CP4_S_JS5_48.73",
            "COL_EI_CP4_S_JS3_51.97", "COL_EI_CP4_S_JS4_52.11", "COL_EI_CP4_S_JS8_52.08"]

# Huella fisica de las columnas de acero del plano P3 (DXF 2017_67-102, banda P3,
# RLE-PILAR, frame comun u,v). En el sector voladizo I'-J la UNICA huella 70x70 es la
# fila concreta de apoyo Ip (u~45.0); no existe huella en u~46.3 (IpJ), u~48.7 (J) ni en
# la franja alta v=18.2-18.4 (FS1/GS2). Verificado numericamente con ezdxf.
P3_PHYSICAL_FOOTPRINTS_U = [(44.65, 45.35)]

# Sufijo de IDs P3 del paquete metalico RLE-TEXTO-1 sin huella fisica (todas
# 'V.M. 300x300x5' procedentes de rotulo de texto).
P3_STEEL = ["COL_EI_CP3_S_IpJ1_46.35", "COL_EI_CP3_S_IpJ2_46.36", "COL_EI_CP3_S_IpJ3_46.34",
            "COL_EI_CP3_S_J1_48.68", "COL_EI_CP3_S_J2_48.7", "COL_EI_CP3_S_J3_48.9",
            "COL_EI_CP3_S_FS1_20.38", "COL_EI_CP3_S_GS2_30.4"]

# --- Voladizo NORTE (P1/P2/P4) ------------------------------------------------ #
# Losas P1 construidas desde la planta de OTRO edificio (plano 2017_67-101): se
# eliminan del paquete (representacion; no existe voladizo P1 en u[33.7,45.4]).
P1_REMOVE_LOSAS = ["L_EI_CP1_D_VOL_ESTE_OE", "L_EI_CP1_D_VOL_ESTE_ES"]

# Reubicacion de columnas a la huella fisica RLE-PILAR (frame comun u,v).
# P2 (plano 2017_67-102): centro de la huella u[17.34,17.64] v[20.12,20.42].
P2_RELOC_COLS = {
    "COL_EI_CP2_S_G3S1_18.96": ((17.5, 20.27), "huella u[17.34,17.64] v[20.12,20.42]"),
}

# Columna P2 incorporada DESDE huella fisica RLE-PILAR (no existia en el paquete):
# centroid u[9.85,10.15] v[20.12,20.42] -> centro (10.0,20.27), 0.30x0.30 m, bajo la
# viga de borde v=20.57 (u[9.70,17.79]) del voladizo norte (plano 2017_67-102).
# Misma convencion vertical que el resto de columnas P2: base=forjado P1, top=P2.
P2_ADD = [
    {
        "id": "COL_EI_CP2_RLE_PILAR_10.00_20.27",
        "grid": "B",
        "seccion": "0.30 x 0.30 (huella RLE-PILAR 2017_67-102)",
        "ancho": 0.3,
        "peralte": 0.3,
        "estado_seccion": "confirmado",
        "posicion": [10.0, 3.91, 20.27],
        "nota": "Incorporada desde huella fisica RLE-PILAR (u[9.85,10.15] v[20.12,20.42]) "
                "del plano 2017_67-102.dxf. Seccion geometrica demostrada por la huella; "
                "material/perfil asumido por el modelo: sin perfil inventado, acero del "
                "voladizo norte (convencion de las demas columnas P2)".strip(),
    },
]

# Vigas del voladizo norte P2 agregadas SOLO como geometria de viewer, agrupando las
# caras paralelas RLE-VIGA del plano 2017_67-102 en un unico miembro prismatico de
# ancho 0.60 (eje = punto medio de las caras). Seccion adoptada del modelo ("V. 60/80",
# la etiqueta del plano no es legible). NO se incorporan al FE ni a tributaria
# (recibe_losa=false). Extremos tomados de las intersecciones del DXF (sin inventar).
P2_ADD_BEAMS = [
    {
        "id": "H_EI_CP2_y2027_10.30-17.79_PLA2017-102",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[10.30, 3.91, 20.27], [17.79, 3.91, 20.27]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P2",
        "nota": "Viga de borde norte voladizo P2, eje v=20.27 entre caras RLE-VIGA "
                "v=19.97 y v=20.57 (u[10.30,17.79]); geometria de viewer desde plano "
                "2017_67-102, sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP2_x1000_16.50-20.57_PLA2017-102",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[10.00, 3.91, 16.50], [10.00, 3.91, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P2",
        "nota": "Apoyo/cabeza de pilar OESTE del voladizo P2, eje u=10.00 entre caras "
                "RLE-VIGA u=9.70 y u=10.30 (v[16.50,20.57]); geometria de viewer desde "
                "plano 2017_67-102, sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP2_x1749_16.45-19.97_PLA2017-102",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[17.49, 3.91, 16.45], [17.49, 3.91, 19.97]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P2",
        "nota": "Apoyo/cabeza de pilar ESTE del voladizo P2, eje u=17.49 entre caras "
                "RLE-VIGA u=17.19 y u=17.79 (v[16.45,19.97]); geometria de viewer desde "
                "plano 2017_67-102, sin FE/tributaria. La pareja u=17.34/17.64 (0.30) es "
                "la propia columna G3S1, no una viga.",
    },
]
# P4 (plano 2017_67-103): centros de huella u[19.85,20.15]x v[20.30,20.60] y
# u[29.85,30.15]x v[20.30,20.60] (0.30x0.30 m = P.M. 300x300x20).
P4_RELOC_COLS = {
    "COL_EI_CP4_S_GS6_21.5": ((20.0, 20.45), "huella u[19.85,20.15] v[20.30,20.60]"),
    "COL_EI_CP4_S_HS7_31.55": ((30.0, 20.45), "huella u[29.85,30.15] v[20.30,20.60]"),
}


def _in_footprint(u):
    return any(lo <= u <= hi for lo, hi in P4_PHYSICAL_FOOTPRINTS_U)


def _reclasificar(cols, steel_ids, footprints, nivel, dxf_ref):
    """Reclasifica como 'por_resolver' (RefPendientes) las columnas metalicas del paquete
    cuyo id esta en `steel_ids` y cuya u no cae en ninguna huella fisica del plano.
    Idempotente: si ya es por_resolver no hace nada. Devuelve n_reclasificadas."""
    changed = 0
    for c in cols:
        if c.get("id") not in steel_ids:
            continue
        if c.get("estado_seccion") == "por_resolver":
            continue
        u = c.get("posicion", [0, 0, 0])[0] if c.get("posicion") else 0.0
        c["seccion"] = "P.M.I. (RLE-TEXTO-1, sin huella en planta)"
        c["ancho"] = 0.0
        c["peralte"] = 0.0
        c["estado_seccion"] = "por_resolver"
        footprint = any(lo <= u <= hi for lo, hi in footprints)
        c["nota"] = (c.get("nota", "") +
                     " | RECLASAFICADA (aplicacion planos): u=%.2f no cae en ninguna "
                     "huella fisica de columna de acero del plano %s (u en %s; RLE-PILAR %s). "
                     "Dentro_huella=%s." %
                     (u, nivel,
                      ", ".join("%.2f-%.2f" % t for t in footprints),
                      dxf_ref, footprint))
        changed += 1
    return changed


def _reubicar(cols, reloc, nivel, dxf_ref):
    """Reubica una columna existente sobre el centro de su huella fisica RLE-PILAR
    (mantiene seccion/estado y conserva cota). Idempotente."""
    changed = 0
    for c in cols:
        if c.get("id") not in reloc:
            continue
        (u_t, v_t), huella_s = reloc[c["id"]]
        pos = c.get("posicion") or [0, 0, 0]
        if abs((pos[0] or 0) - u_t) < 1e-6 and abs((pos[2] or 0) - v_t) < 1e-6:
            continue
        c["posicion"] = [round(u_t, 6), pos[1], round(v_t, 6)]
        c["nota"] = (c.get("nota", "") +
                     " | REUBICADA (%s): (%.2f,%.2f)->(%.2f,%.2f) sobre huella "
                     "RLE-PILAR %s (plano %s)." %
                     (nivel, pos[0], pos[2], u_t, v_t, huella_s, dxf_ref))
        changed += 1
    return changed


def _eliminar_losas(losas, ids):
    """Elimina losas del paquete por id. Idempotente. Devuelve n_eliminadas."""
    antes = len(losas)
    losas[:] = [l for l in losas if l.get("id") not in ids]
    return antes - len(losas)


def _agregar(cols, nuevos):
    """Inserta columnas nuevas (por id) si aun no existen en el paquete. Idempotente."""
    existing = {c.get("id") for c in cols}
    added = 0
    for n in nuevos:
        if n["id"] in existing:
            continue
        cols.append(dict(n))
        added += 1
    return added


def apply_correction(out: Path | str | None = None) -> dict:
    """Aplica las correcciones P1-P4 del paquete. Devuelve resumen {nivel: info}."""
    target = Path(out) if out else OUT
    summary = {}
    d4 = target / "P4.json"
    if not d4.exists():
        summary["P4"] = "SKIP (no existe P4.json)"
    else:
        d = json.load(open(d4, encoding="utf-8-sig"))
        n_mov = _reubicar(d.get("columnas", []), P4_RELOC_COLS, "P4", "2017_67-103.dxf")
        n_rec = _reclasificar(d.get("columnas", []), P4_STEEL, P4_PHYSICAL_FOOTPRINTS_U,
                              "P4", "piso4_103.dxf")
        json.dump(d, open(d4, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P4"] = {"reubicadas": n_mov, "reclasificadas": n_rec,
                         "total_columnas": len(d["columnas"])}
    d3 = target / "P3.json"
    if not d3.exists():
        summary["P3"] = "SKIP (no existe P3.json)"
    else:
        d = json.load(open(d3, encoding="utf-8-sig"))
        changed = _reclasificar(d.get("columnas", []), P3_STEEL, P3_PHYSICAL_FOOTPRINTS_U,
                                "P3", "2017_67-102.dxf (banda P3)")
        json.dump(d, open(d3, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P3"] = {"reclasificadas": changed, "total_columnas": len(d["columnas"])}
    d2 = target / "P2.json"
    if not d2.exists():
        summary["P2"] = "SKIP (no existe P2.json)"
    else:
        d = json.load(open(d2, encoding="utf-8-sig"))
        n_mov = _reubicar(d.get("columnas", []), P2_RELOC_COLS, "P2", "2017_67-102.dxf (banda P2)")
        n_add = _agregar(d.get("columnas", []), P2_ADD)
        n_b = _agregar(d.get("vigas", []), P2_ADD_BEAMS)
        json.dump(d, open(d2, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P2"] = {"reubicadas": n_mov, "agregadas": n_add,
                         "vigas_agregadas": n_b,
                         "total_columnas": len(d["columnas"]),
                         "total_vigas": len(d["vigas"])}
    d1 = target / "P1.json"
    if not d1.exists():
        summary["P1"] = "SKIP (no existe P1.json)"
    else:
        d = json.load(open(d1, encoding="utf-8-sig"))
        n_elim = _eliminar_losas(d.get("losas", []), P1_REMOVE_LOSAS)
        json.dump(d, open(d1, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P1"] = {"losas_eliminadas": n_elim, "total_losas": len(d["losas"])}
    return summary


if __name__ == "__main__":
    print(apply_correction())
