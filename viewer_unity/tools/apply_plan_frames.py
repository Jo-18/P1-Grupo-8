"""Correccion CANDIDATA del paquete VISUAL del marco de acero I'-J (P3/P4).

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
  * P4: NINGUNA columna de acero del paquete coincide con la huella fisica del plano
    (RLE-PILAR en u=44.92 Ip, 47.46 y 49.79). Todas (IpS1, JS2, JS3, JS4, JS5, JS8)
    proceden de texto (RLE-TEXTO-1) y quedan fuera de la geometria fisica: se
    reclasifican como RefPendientes (marcador visual) para no dibujarlas como
    columnas inventadas. Se les conserva la posicion para trazabilidad.
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


def apply_correction(out: Path | str | None = None) -> dict:
    """Aplica la reclasificacion P4 y P3. Devuelve resumen {nivel: info}."""
    target = Path(out) if out else OUT
    summary = {}
    d4 = target / "P4.json"
    if not d4.exists():
        summary["P4"] = "SKIP (no existe P4.json)"
    else:
        d = json.load(open(d4, encoding="utf-8-sig"))
        changed = _reclasificar(d.get("columnas", []), P4_STEEL, P4_PHYSICAL_FOOTPRINTS_U,
                                "P4", "piso4_103.dxf")
        json.dump(d, open(d4, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P4"] = {"reclasificadas": changed, "total_columnas": len(d["columnas"])}
    d3 = target / "P3.json"
    if not d3.exists():
        summary["P3"] = "SKIP (no existe P3.json)"
    else:
        d = json.load(open(d3, encoding="utf-8-sig"))
        changed = _reclasificar(d.get("columnas", []), P3_STEEL, P3_PHYSICAL_FOOTPRINTS_U,
                                "P3", "2017_67-102.dxf (banda P3)")
        json.dump(d, open(d3, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P3"] = {"reclasificadas": changed, "total_columnas": len(d["columnas"])}
    return summary


if __name__ == "__main__":
    print(apply_correction())
