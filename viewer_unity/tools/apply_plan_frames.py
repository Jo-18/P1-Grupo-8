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
  * P3: las columnas de acero IpJ(46.35)/J(48.7) estan VALIDADAS POR ETIQUETA
    'V.M. 300x300x5' y ya son 'confirmado'; los candidatos 'P.M.I.' (JP1-6) ya son
    RefPendientes. No se toca P3.
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


def _in_footprint(u):
    return any(lo <= u <= hi for lo, hi in P4_PHYSICAL_FOOTPRINTS_U)


def apply_correction(out: Path | str | None = None) -> dict:
    """Aplica la reclasificacion P4. Devuelve resumen {nivel: info}."""
    target = Path(out) if out else OUT
    summary = {}
    p = target / "P4.json"
    if not p.exists():
        summary["P4"] = "SKIP (no existe P4.json)"
        return summary
    d = json.load(open(p, encoding="utf-8-sig"))
    changed = 0
    for c in d.get("columnas", []):
        if c.get("id") in P4_STEEL:
            u = c.get("posicion", [0, 0, 0])[0] if c.get("posicion") else 0.0
            if c.get("estado_seccion") != "por_resolver":  # idempotente
                c["seccion"] = "P.M.I. (RLE-TEXTO-1, sin huella en planta)"
                c["ancho"] = 0.0
                c["peralte"] = 0.0
                c["estado_seccion"] = "por_resolver"
                footprint = any(lo <= u <= hi for lo, hi in P4_PHYSICAL_FOOTPRINTS_U)
                c["nota"] = (c.get("nota", "") +
                             " | RECLASAFICADA (aplicacion planos): u=%.2f no cae en ninguna "
                             "huella fisica de columna de acero del plano P4 (u en %.2f-%.2f, "
                             "%.2f-%.2f, %.2f-%.2f; RLE-PILAR piso4_103). Dentro_huella=%s." %
                             (u, *[x for tup in P4_PHYSICAL_FOOTPRINTS_U for x in tup], footprint))
                changed += 1
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    summary["P4"] = {"reclasificadas": changed, "total_columnas": len(d["columnas"])}
    return summary


if __name__ == "__main__":
    print(apply_correction())
