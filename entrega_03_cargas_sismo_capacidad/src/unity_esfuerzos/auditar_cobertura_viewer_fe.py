"""Auditoria bidireccional de cobertura viewer<->FE.

viewer -> FE : clasifica cada columna/viga/muro VISIBLE del viewer como
   1A1 | CONTENIDO (lista de segmentos FE) | MULTIPLE | SIN_RESULTADO_FE.
FE -> viewer : clasifica cada elemento FE con la misma taxonomia:
   1A1 | CONTENIDO | MULTIPLE | SIN_RESULTADO_FE.

Estado MULTIPLE: cobertura geometrica real con al menos un elemento FE, pero
sin enlace por correspondencia.viewer_id (el mapeo del exportador no lo resolvio).
Estado SIN_RESULTADO_FE: no hay (o no se muestra) elemento FE equivalente.

Salida: JSON + Markdown en entrega_03_cargas_sismo_capacidad/docs.
Uso: python -m src.unity_esfuerzos.auditar_cobertura_viewer_fe
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

RAIZ = Path(__file__).resolve().parents[3]
LAB = RAIZ / "viewer_unity" / "Assets" / "StreamingAssets" / "lab_data" / "edificios"
DOCS = RAIZ / "entrega_03_cargas_sismo_capacidad" / "docs"

TOL_AXIS = 5e-3      # m: igualdad de ejes (u,v)
TOL_PLANAR = 0.03    # m: distancia de un punto FE a la polilinea del viewer
TOL_Z = 0.40         # m: coincidencia de cota para vigas planas

TIPOS = ("columna", "viga", "muro")


def cerca(a, b, tol=TOL_AXIS):
    return abs(a - b) <= tol


def dist_punto_segmento(p, a, b):
    import math
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dist_punto_polilinea(p, pts):
    d = float("inf")
    for i in range(len(pts) - 1):
        d = min(d, dist_punto_segmento(p, (pts[i][0], pts[i][2]), (pts[i + 1][0], pts[i + 1][2])))
    return d


class Viewer:
    def __init__(self, edificio: str):
        self.edificio = edificio
        self.pisos: dict[str, dict] = {}   # nivel -> {"cota": float, "columnas": [...], "vigas": [...], "muros": [...]}
        for p in sorted((LAB / edificio / "geometry").glob("*.json")):
            g = json.loads(p.read_text(encoding="utf-8"))
            self.pisos[g["nivel"]] = {
                "cota": float(g.get("cota", 0.0)),
                "columnas": g.get("columnas", []),
                "vigas": g.get("vigas", []),
                "muros": g.get("muros", []),
            }
        self.orden = [n for n, _ in sorted(self.pisos.items(), key=lambda kv: kv[1]["cota"])]
        self.top = self.pisos[self.orden[-1]]["cota"] if self.orden else 0.0


def carga_fe(edificio: str) -> list[dict]:
    p = LAB / edificio / "results" / f"esfuerzos_FE_EDIFICIO_{edificio}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return d["elementos"]


def seg2d(e) -> tuple:
    return ((e["p_i_unity"][0], e["p_i_unity"][2]), (e["p_j_unity"][0], e["p_j_unity"][2]))


def fe_cubre_elemento(fe, elemento, viewer, nivel) -> bool:
    """Coincidencia geometrica FE<->elemento viewer del mismo tipo."""
    tipo = elemento.get("tipo")
    if fe["tipo"] != tipo:
        return False
    pi, pj = fe["p_i_unity"], fe["p_j_unity"]
    zi, zj = min(pi[1], pj[1]), max(pi[1], pj[1])
    if tipo == "columna":
        pos = elemento["posicion"]
        if not (cerca(pos[0], fe["p_i_unity"][0], 0.02) and cerca(pos[2], fe["p_i_unity"][2], 0.02)):
            return False
        base = float(pos[1])
        # la columna del viewer sube desde su base hacia el techo del edificio
        seg = zi <= base <= zj or (zj >= base and (zj - max(zi, base)) > 0.05)
        return seg and zj > base - TOL_Z * 0.25
    if tipo == "viga":
        pts = elemento["pts"]
        z = float(pts[0][1])
        if abs(z - pi[1]) > TOL_Z:
            return False
        d1 = dist_punto_polilinea((pi[0], pi[2]), pts)
        d2 = dist_punto_polilinea((pj[0], pj[2]), pts)
        return (d1 <= TOL_PLANAR and d2 <= TOL_PLANAR) or d1 <= TOL_PLANAR or d2 <= TOL_PLANAR
    if tipo == "muro":
        pts = elemento["pts"]
        z = float(pts[0][1])
        if abs(z - pi[1]) > TOL_Z:
            return False
        d = dist_punto_polilinea((pi[0], pi[2]), pts)
        return d <= TOL_PLANAR
    return False


def audit(edificio: str) -> dict:
    vw = Viewer(edificio)
    fe = carga_fe(edificio)

    fe_por_viewer: dict[str, list[dict]] = defaultdict(list)
    for e in fe:
        vid = e["correspondencia"].get("viewer_id")
        if vid and e["correspondencia"].get("estado") not in ("SIN_CORRESPONDENCIA_VIEWER",):
            fe_por_viewer[vid].append(e)

    viewer_res = {}   # (nivel, tipo, id) -> estado
    viewer_det = {}   # estado -> detalles
    for nivel, piso in vw.pisos.items():
        aparejos = {"columna": piso["columnas"], "viga": piso["vigas"], "muro": piso["muros"]}
        for tipo, lista in aparejos.items():
            for el in lista:
                eid = el["id"]
                matches = fe_por_viewer.get(eid, [])
                if len(matches) == 1:
                    estado = "1A1" if matches[0]["correspondencia"]["estado"] == "1A1" else "CONTENIDO"
                    det = {"tags": [matches[0]["tag"]]}
                elif len(matches) > 1:
                    estado = "CONTENIDO"
                    det = {"tags": sorted(e["tag"] for e in matches)}
                else:
                    # cobertura geometrica real sin enlace -> MULTIPLE
                    cubre = [e for e in fe if fe_cubre_elemento(e, el, vw, nivel)]
                    if cubre:
                        estado = "MULTIPLE"
                        det = {"tags": sorted(e["tag"] for e in cubre[:40])}
                    else:
                        estado = "SIN_RESULTADO_FE"
                        det = {"tags": []}
                sec = el.get("seccion", "")
                viewer_res[(nivel, tipo, eid)] = estado
                viewer_det.setdefault(estado, []).append({
                    "edificio": edificio, "nivel": nivel, "tipo": tipo, "id": eid,
                    "seccion": sec, "tags": det.get("tags", []) if estado != "1A1" else det["tags"],
                })

    fe_res = {}
    fe_det = {}
    PLURAL = {"columna": "columnas", "viga": "vigas", "muro": "muros"}

    for e in fe:
        est = e["correspondencia"]["estado"]
        if est == "SIN_CORRESPONDENCIA_VIEWER":
            # ? existe un objeto viewer cubriendo su geometria?
            vista = None
            for nivel, piso in vw.pisos.items():
                for tipo in TIPOS:
                    for el in piso[PLURAL[tipo]]:
                        if fe_cubre_elemento(e, el, vw, nivel):
                            vista = (nivel, tipo, el["id"])
                            break
                    if vista:
                        break
                if vista:
                    break
            estado = "MULTIPLE" if vista else "SIN_RESULTADO_FE"
        else:
            estado = est
        fe_res[e["tag"]] = estado
        fe_det.setdefault(estado, []).append({
            "edificio": edificio, "tag": e["tag"], "tipo": e["tipo"], "nivel": e["nivel"],
            "seccion": e["seccion"], "estado_fuente": est,
        })

    # ---- matrices ----
    niveles = [n for n in vw.orden if n in vw.pisos]
    matriz = []
    for nivel in niveles:
        for tipo in TIPOS:
            v_ids = list(vw.pisos[nivel][PLURAL[tipo]])
            n_v = len(v_ids)
            n_v_1a1 = sum(1 for k in v_ids if viewer_res[(nivel, tipo, k["id"])] == "1A1")
            n_v_con = sum(1 for k in v_ids if viewer_res[(nivel, tipo, k["id"])] == "CONTENIDO")
            n_v_mul = sum(1 for k in v_ids if viewer_res[(nivel, tipo, k["id"])] == "MULTIPLE")
            n_v_sin = sum(1 for k in v_ids if viewer_res[(nivel, tipo, k["id"])] == "SIN_RESULTADO_FE")
            f = [e for e in fe if e["nivel"] == nivel and e["tipo"] == tipo]
            n_f = len(f)
            n_f_1a1 = sum(1 for e in f if fe_res[e["tag"]] == "1A1")
            n_f_con = sum(1 for e in f if fe_res[e["tag"]] == "CONTENIDO")
            n_f_mul = sum(1 for e in f if fe_res[e["tag"]] == "MULTIPLE")
            n_f_sin = sum(1 for e in f if fe_res[e["tag"]] == "SIN_RESULTADO_FE")
            cov_v = (n_v_1a1 + n_v_con + n_v_mul) / n_v * 100 if n_v else 0.0
            cov_f = (n_f_1a1 + n_f_con + n_f_mul) / n_f * 100 if n_f else 0.0
            matriz.append({
                "nivel": nivel, "tipo": tipo,
                "viewer": {"total": n_v, "1A1": n_v_1a1, "CONTENIDO": n_v_con, "MULTIPLE": n_v_mul, "SIN_RESULTADO": n_v_sin, "cobertura_pct": round(cov_v, 1)},
                "FE": {"total": n_f, "1A1": n_f_1a1, "CONTENIDO": n_f_con, "MULTIPLE": n_f_mul, "SIN_RESULTADO": n_f_sin, "cobertura_pct": round(cov_f, 1)},
            })

    return {
        "edificio": edificio,
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "viewer_a_fE": viewer_det,
        "FE_a_viewer": fe_det,
        "matriz": matriz,
        "totales": {
            "viewer": {"total": len(viewer_res), "1A1": sum(1 for s in viewer_res.values() if s == "1A1"),
                       "CONTENIDO": sum(1 for s in viewer_res.values() if s == "CONTENIDO"),
                       "MULTIPLE": sum(1 for s in viewer_res.values() if s == "MULTIPLE"),
                       "SIN_RESULTADO": sum(1 for s in viewer_res.values() if s == "SIN_RESULTADO_FE")},
            "FE": {"total": len(fe_res), "1A1": sum(1 for s in fe_res.values() if s == "1A1"),
                   "CONTENIDO": sum(1 for s in fe_res.values() if s == "CONTENIDO"),
                   "MULTIPLE": sum(1 for s in fe_res.values() if s == "MULTIPLE"),
                   "SIN_RESULTADO": sum(1 for s in fe_res.values() if s == "SIN_RESULTADO_FE")},
        },
        "_nota_estados": {
            "1A1": "enlace viewer_id directo a un unico FE",
            "CONTENIDO": "enlace viewer_id a >=2 segmentos FE dentro del objeto",
            "MULTIPLE": "cobertura geometrica real (>=1 FE) pero el mapeo por viewer_id NO lo resolvio",
            "SIN_RESULTADO_FE": "sin elemento FE equivalente (ni por id ni por geometria)",
        },
    }


def formato_tabla(reporte: dict) -> str:
    L = []
    e = reporte["edificio"]
    L.append(f"AUDITORIA DE COBERTURA VIEWER<->FE — EDIFICIO {e}\n")
    L.append("Estados: 1A1 | CONTENIDO | MULTIPLE (cobertura geo sin enlace) | SIN_RESULTADO_FE\n")
    L.append("Matriz por nivel y tipo (viewer = objetos visibles; FE = elementos del paquete):\n")
    hdr = f"{'nivel':<8}{'tipo':<9}" + "".join(f"{c:>10}" for c in ("v_total", "v_1A1", "v_CON", "v_MUL", "v_SIN", "v_cov%", "f_total", "f_1A1", "f_CON", "f_MUL", "f_SIN", "f_cov%"))
    L.append(hdr)
    L.append("-" * len(hdr))
    for m in reporte["matriz"]:
        v, f = m["viewer"], m["FE"]
        L.append(f"{m['nivel']:<8}{m['tipo']:<9}"
                 + "".join(f"{x:>10}" for x in (v["total"], v["1A1"], v["CONTENIDO"], v["MULTIPLE"], v["SIN_RESULTADO"], v["cobertura_pct"],
                                                f["total"], f["1A1"], f["CONTENIDO"], f["MULTIPLE"], f["SIN_RESULTADO"], f["cobertura_pct"])))
    t = reporte["totales"]
    L.append("")
    L.append(f"TOTALES  viewer: {t['viewer']['total']}  -> 1A1={t['viewer']['1A1']} CONTENIDO={t['viewer']['CONTENIDO']} MULTIPLE={t['viewer']['MULTIPLE']} SIN_RESULTADO={t['viewer']['SIN_RESULTADO']}")
    L.append(f"TOTALES  FE    : {t['FE']['total']}  -> 1A1={t['FE']['1A1']} CONTENIDO={t['FE']['CONTENIDO']} MULTIPLE={t['FE']['MULTIPLE']} SIN_RESULTADO={t['FE']['SIN_RESULTADO']}")
    L.append("")
    for dirs, clave in (("VIEWER -> FE", "viewer_a_fE"), ("FE -> VIEWER", "FE_a_viewer")):
        L.append(f"=== {dirs} ===")
        for est in ("SIN_RESULTADO_FE", "MULTIPLE"):
            items = reporte[clave].get(est, [])
            if not items:
                L.append(f"  {est}: (ninguno)")
                continue
            L.append(f"  {est}: {len(items)}")
            if clave == "viewer_a_fE":
                for it in sorted(items, key=lambda x: (x["nivel"], x["tipo"], x["id"])):
                    L.append(f"    {it['nivel']:<5} {it['tipo']:<8} {it['id']:<44} sec={it['seccion']:<22} tags={it['tags']}")
            else:
                for it in sorted(items, key=lambda x: (x["nivel"], x["tipo"], x["tag"])):
                    L.append(f"    {it['nivel']:<8} {it['tipo']:<8} tag={it['tag']:<4} sec={it['seccion']:<22} fuente={it['estado_fuente']}")
        L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    edificios = argv[1:] or ["I", "II"]
    DOCS.mkdir(parents=True, exist_ok=True)
    reportes = {}
    for ed in edificios:
        rep = audit(ed)
        reportes[ed] = rep
        (DOCS / f"AUDITORIA_COBERTURA_VIEWER_FE_{ed}.json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        txt = formato_tabla(rep)
        (DOCS / f"AUDITORIA_COBERTURA_VIEWER_FE_{ed}.md").write_text(txt, encoding="utf-8")
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))