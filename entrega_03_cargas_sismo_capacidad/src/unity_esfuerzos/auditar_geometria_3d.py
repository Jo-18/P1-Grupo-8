"""Auditoria geometrica 3D de la correspondencia viewer<->FE (solo lectura).

Verifica que toda VIGA y COLUMNA del paquete de esfuerzos con correspondencia
1A1 o CONTENIDO coincide con el tramo fisico del objeto del viewer que la
representa, comparando EXTREMOS (directa o invertida), CENTRO, LONGITUD y
ORIENTACION dentro de una tolerancia explicita y documentada (TOL_3D = 2 mm).

Objetivo (hito flotantes P4-EI): que barras FE analiticas sin tramo fisico en el
viewer (postes P4-EI 607..635, z=11,83->15,79) NO conserven correspondencia
normal contra una columna fisica P4 [7,87;11,83]. La auditoria reporta, para
todas las vigas y columnas de EI y EII, las metricas agregadas (max, RMS, media)
y la lista individual fuera de tolerancia.

Salida (NO toca los JSON productivos del viewer):
  entrega_03_cargas_sismo_capacidad/docs/AUDITORIA_GEOMETRIA_3D_{I,II}.json
  entrega_03_cargas_sismo_capacidad/docs/AUDITORIA_GEOMETRIA_3D_{I,II}.md

Uso: python -m src.unity_esfuerzos.auditar_geometria_3d [I II]
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.unity_esfuerzos.exportar_esfuerzos_para_viewer import (
    GEOMETRIA_VIEWER,
    TOL_3D,
    barra_vertical,
    cercano,
    leer_geometria_viewer,
    tramo_fisico_columna,
)

DOCS = Path(__file__).resolve().parents[2] / "docs"


def _medidas_barra(a, b):
    """-> (longitud, centro, vector_unitario) de la barra 3D a->b."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    if L < 1e-12:
        return 0.0, None, None
    return L, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2), \
        (dx / L, dy / L, dz / L)


def _orientacion_paralela(u, v, inv):
    """1 - |dot| = 0.0 si u == +-v."""
    dot = u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
    return 1.0 - abs(dot)


def _comparar_barra_contra(pi, pj, a, b, tol):
    """Compara la barra FE pi->pj contra el tramo a->b del objeto viewer.
    Extremos directa o invertida; centro, longitud y orientacion derivadas."""
    L_f, c_f, n_f = _medidas_barra(pi, pj)
    L_o, c_o, n_o = _medidas_barra(a, b)
    if L_f is None or L_f < 1e-12 or L_o is None:
        return {"ok": False, "d_extremo_m": float("inf"), "d_centro_m": float("inf"),
                "d_longitud_m": float("inf"), "d_orientacion": 1.0}
    d_extr_dir = max(math.dist(pi, a), math.dist(pj, b))
    d_extr_inv = max(math.dist(pi, b), math.dist(pj, a))
    d_extremo = min(d_extr_dir, d_extr_inv)
    ok_extremos = d_extremo <= tol
    d_centro = math.dist(c_f, c_o)
    d_longitud = abs(L_f - L_o)
    d_orientacion = (_orientacion_paralela(n_f, n_o, inv=False)
                     if n_o is not None else 1.0)
    orientacion = ("directa" if d_extr_dir <= d_extr_inv else "invertida") \
        if ok_extremos else "no_coincide"
    ok = ok_extremos and d_centro <= tol and d_longitud <= tol \
        and d_orientacion <= tol / max(L_o, 1e-12)
    return {
        "ok": ok,
        "d_extremo_m": round(d_extremo, 6),
        "d_centro_m": round(d_centro, 6),
        "d_longitud_m": round(d_longitud, 6),
        "d_orientacion": round(d_orientacion, 6),
        "orientacion": orientacion,
        "L_barra_m": round(L_f, 6),
        "L_tramo_m": round(L_o, 6),
    }


def auditar(edificio: str) -> dict:
    payload = (GEOMETRIA_VIEWER / edificio / "results"
               / f"esfuerzos_FE_EDIFICIO_{edificio}.json")
    data = json.loads(payload.read_text(encoding="utf-8"))
    geo = leer_geometria_viewer(edificio)
    items, fuera, metricas = [], [], []

    for el in sorted(data["elementos"], key=lambda e: e["tag"]):
        est = el["correspondencia"]["estado"]
        if el["tipo"] not in ("columna", "viga") or est not in ("1A1", "CONTENIDO"):
            continue
        pi, pj = el["p_i_unity"], el["p_j_unity"]
        vid = el["correspondencia"]["viewer_id"]
        nivel = el["correspondencia"]["viewer_nivel"]
        if not vid or nivel not in geo:
            continue
        if el["tipo"] == "columna":
            tramo = tramo_fisico_columna(nivel, geo)
            if tramo is None:
                medidas = {"ok": False, "d_extremo_m": float("inf"),
                           "d_centro_m": float("inf"), "d_longitud_m": float("inf"),
                           "d_orientacion": 1.0, "nota": "sin tramo fisico superior"}
            else:
                a, b = (pi[0], tramo[0], pi[2]), (pj[0], tramo[1], pj[2])
                medidas = _comparar_barra_contra(pi, pj, a, b, TOL_3D)
        else:
            pts = geo[nivel]["vigas"].get(vid)
            if not pts:
                continue
            medidas = _comparar_barra_contra(pi, pj, pts[0], pts[-1], TOL_3D)
        items.append({
            "edificio": edificio, "tag": el["tag"], "tipo": el["tipo"],
            "nivel": nivel, "viewer_id": vid, "estado": est,
            "medidas": medidas,
        })
        if est == "1A1" and not medidas["ok"]:
            fuera.append({"edificio": edificio, "tag": el["tag"],
                          "tipo": el["tipo"], "nivel": nivel, "viewer_id": vid,
                          "medidas": medidas})

    # metricas agregadas (solo elementos 1A1 -> su tramo debe coincidir)
    de, dc, dl, dor = [], [], [], []
    for it in items:
        if it["estado"] != "1A1":
            continue
        m = it["medidas"]
        if any(not math.isfinite(x) for x in
               (m["d_extremo_m"], m["d_centro_m"], m["d_longitud_m"])):
            continue
        de.append(m["d_extremo_m"]); dc.append(m["d_centro_m"])
        dl.append(m["d_longitud_m"]); dor.append(m["d_orientacion"])

    def agg(vals):
        return {"n": len(vals),
                "max": round(max(vals), 9) if vals else None,
                "rms": round(math.sqrt(sum(v * v for v in vals) / len(vals)), 9)
                if vals else None,
                "media": round(sum(vals) / len(vals), 9) if vals else None,
                "fuera_tolerancia": sum(1 for v in vals if v > TOL_3D)}

    return {
        "edificio": edificio,
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tolerancia_m": TOL_3D,
        "nota": ("comparacion de extremos (directa o invertida), centro, "
                 "longitud y orientacion de la barra FE contra el tramo fisico "
                 "del objeto viewer (columna: [cota(nivel), cota(nivel+1)]; "
                 "viga: polilinea del objeto). Fuera de tolerancia solo afecta "
                 "a elementos 1A1."),
        "n_elementos_1A1_CONTENIDO": sum(1 for it in items),
        "n_fuera_tolerancia": len(fuera),
        "metricas_agregadas": {
            "d_extremo_m": agg(de), "d_centro_m": agg(dc),
            "d_longitud_m": agg(dl), "d_orientacion": agg(dor),
        },
        "fuera_tolerancia": sorted(fuera, key=lambda x: (x["tipo"], x["nivel"], x["tag"])),
        "items": sorted(items, key=lambda x: (x["tipo"], x["nivel"], x["tag"])),
    }


def _formato_md(reporte: dict) -> str:
    L = []
    e = reporte["edificio"]
    L.append(f"AUDITORIA GEOMETRICA 3D CORRESPONDENCIA VIEWER<->FE — EDIFICIO {e}\n")
    L.append(f"Tolerancia: {reporte['tolerancia_m']} m (extremos/centro/longitud/orientacion)")
    L.append("")
    L.append("METRICAS AGREGADAS (elementos 1A1, n=%d):" %
             reporte["metricas_agregadas"]["d_extremo_m"]["n"])
    cab = f"{'metrica':<18}{'max':>14}{'rms':>14}{'media':>14}{'>tol':>8}"
    L.append(cab)
    for k in ("d_extremo_m", "d_centro_m", "d_longitud_m", "d_orientacion"):
        a = reporte["metricas_agregadas"][k]
        L.append(f"{k:<18}{a['max']:>14}{a['rms']:>14}{a['media']:>14}{a['fuera_tolerancia']:>8}")
    L.append("")
    L.append(f"FUERA DE TOLERANCIA (1A1): {reporte['n_fuera_tolerancia']}")
    for it in reporte["fuera_tolerancia"]:
        m = it["medidas"]
        L.append(f"  tag {it['tag']:>4} {it['tipo']:<8} {it['nivel']:<6} "
                 f"{it['viewer_id']:<44} d_ext={m['d_extremo_m']} "
                 f"d_cen={m['d_centro_m']} d_L={m['d_longitud_m']} "
                 f"orient={m['d_orientacion']}")
    return "\n".join(L)


def main(argv=None) -> int:
    edificios = argv[1:] or ["I", "II"]
    for ed in edificios:
        rep = auditar(ed)
        (DOCS / f"AUDITORIA_GEOMETRIA_3D_{ed}.json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        (DOCS / f"AUDITORIA_GEOMETRIA_3D_{ed}.md").write_text(
            _formato_md(rep), encoding="utf-8")
        print(f"[{ed}] 1A1/CONTENIDO auditados={rep['n_elementos_1A1_CONTENIDO']} "
              f"fuera de tolerancia={rep['n_fuera_tolerancia']}")
        for k, a in rep["metricas_agregadas"].items():
            print(f"    {k:<16} max={a['max']} rms={a['rms']} media={a['media']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))