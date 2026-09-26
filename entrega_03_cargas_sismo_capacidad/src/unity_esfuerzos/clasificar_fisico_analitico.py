"""Clasifica los elementos FE SIN_CORRESPONDENCIA_VIEWER por naturaleza.

El encargo de cobertura: separar los "huecos" de la correspondencia viewer<->FE
en (a) auxiliares analiticos, (b) segmentos FE de una barra fisica ya mapeada,
(c) fisicos con mapeo pendiente (existen en viewer y plano), (d) fisicos
ausentes del viewer (existen en el plano, no en el viewer), (e) errores o
duplicados, (f) pendiente de fuente (sin evidencia conclusiva).

Taxonomia de salida por elemento SIN:
  AUX_STUB                         : stub_elastico_rigidez_elevada (aux analitico, excluido)
  AUX_SEGMENTO_VERTICAL            : FE subdivide en tramos una columna/muro ya mapeado
                                     (comparte nodo y huella con un FE 1A1/CONTENIDO)
  FISICO_MAPEO_PENDIENTE           : existe <tipo, nivel, huella> en el viewer y en el
                                     plano (candidato), pero el exportador no lo enlazo
  FISICO_AUSENTE_VIEWER            : existe en el plano (candidato), no en el viewer
   FISICO_FE_DESPLAZADO             : el objeto fisico existe en el viewer (huella DXF
                                      REUBICADA) y en el FE, pero la posicion FE (candidato)
                                      esta desplazada 1.5 m de la huella DXF; requiere
                                      correccion del mallado FE (re-mesh)
  AUX_SIN_PLANO                    : sin objeto equivalente en plano ni viewer
  ERROR_DUPLICADO                  : misma huella fisica duplicada dentro del FE
  PENDIENTE_DE_FUENTE              : sin fuente concluyente; se registra que propiedad
                                     falta exactamente

Uso: python -m unity_esfuerzos.clasificar_fisico_analitico
Genera docs/cobertura_planes/CLASIFICACION_SIN_<I|II>.{json,md}
"""

from __future__ import annotations

import json
import sys
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
LAB = RAIZ / "viewer_unity" / "Assets" / "StreamingAssets" / "lab_data" / "edificios"
CAND = RAIZ / "analisis_estructural" / "edificio_I" / "datos" / "candidatos"
DOCS = RAIZ / "entrega_03_cargas_sismo_capacidad" / "docs" / "cobertura_planes"

TOL_EJE = 0.03       # m: igualdad de huella (u,v) columna
TOL_PT = 0.45        # m: distancia punto FE a polilinea viewer (muros)
TOL_PORTAL = 1.00    # m: coincidencia de cota vertical para segmentos

TIPOS = ("columna", "viga", "muro")


def distancia(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def dist_punto_segmento(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return distancia(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return distancia(p, (a[0] + t * dx, a[1] + t * dy))


def dist_punto_polilinea(p, pts):
    pts2 = [(pt[0], pt[2]) for pt in pts]
    return min(dist_punto_segmento(p, pts2[i], pts2[i + 1]) for i in range(len(pts2) - 1))


def carga_viewer(edificio: str) -> dict:
    pisos = {}
    for p in sorted((LAB / edificio / "geometry").glob("*.json")):
        g = json.loads(p.read_text(encoding="utf-8"))
        pisos[g["nivel"]] = g
    return pisos


def carga_fe(edificio: str) -> list[dict]:
    p = LAB / edificio / "results" / f"esfuerzos_FE_EDIFICIO_{edificio}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    return d["elementos"]


def carga_candidatos_el(edificio: str) -> dict:
    if edificio != "I":
        return {}
    meses = {
        "CP1S": "edificio_I_cielo_piso_1_subterraneo_candidata_unity.json",
        "P1": "edificio_I_cielo_piso_1_borrador.json",
        "P2": "edificio_I_cielo_piso_2_borrador.json",
        "P3": "edificio_I_cielo_piso_3_borrador.json",
        "P4": "edificio_I_cielo_piso_4_candidata_unity.json",
    }
    out = {}
    for nivel, fn in meses.items():
        p = CAND / fn
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        out[nivel] = {
            "columnas": d.get("columnas", d.get("columnas_referencia", [])),
            "vigas": d.get("vigas", []),
            "muros": d.get("muros", []),
        }
    return out


def huella_col(elemento) -> tuple:
    pos = elemento.get("posicion")
    if pos:
        return (pos[0], pos[2])
    return (float(elemento["p_i_unity"][0]), float(elemento["p_i_unity"][2]))


def z_range(fe) -> tuple:
    zi, zj = fe["p_i_unity"][1], fe["p_j_unity"][1]
    return (min(zi, zj), max(zi, zj))


def se_cruzan(a, b, tol=0.15):
    return not (a[1] < b[0] - tol or b[1] < a[0] - tol)


def nodos_compartidos(fe, por_nodo, tags_mapeados):
    """True si fe comparte nodos con algun elemento ya mapeado a viewer."""
    for nido in (fe["nodo_i"], fe["nodo_j"]):
        for e2 in por_nodo.get(nido, []):
            if e2["tag"] in tags_mapeados:
                return True
    return False


def clasificar_edificio(edificio: str, fe: list, pisos: dict, plan: dict) -> dict:
    por_nodo = defaultdict(list)
    for e in fe:
        por_nodo[e["nodo_i"]].append(e)
        por_nodo[e["nodo_j"]].append(e)

    tags_mapeados = {
        e["tag"] for e in fe
        if e["correspondencia"].get("estado") not in ("SIN_CORRESPONDENCIA_VIEWER",)
    }
    viewer = {}
    for nivel, g in pisos.items():
        for tipo in TIPOS:
            for el in g.get(tipo + "s", []):
                viewer[(nivel, tipo, el["id"])] = el

    vueltas = {nivel: {"columna": g.get("columnas", []), "viga": g.get("vigas", []),
                       "muro": g.get("muros", [])} for nivel, g in pisos.items()}

    def busca_viewer(fe_elem):
        nivel = fe_elem["nivel"]
        tipo = fe_elem["tipo"]
        lista = vueltas.get(nivel, {}).get(tipo, [])
        if tipo == "columna":
            u, v = huella_col(fe_elem)
            hits = [el for el in lista
                    if abs(u - el["posicion"][0]) < TOL_EJE and abs(v - el["posicion"][2]) < TOL_EJE]
            if hits:
                return min(hits, key=lambda el: abs(el["posicion"][0] - u) + abs(el["posicion"][2] - v))
            return None
        if tipo == "muro":
            zmin, zmax = z_range(fe_elem)
            for el in lista:
                z0 = float(el["pts"][0][1])
                if abs(z0 - zmin) > TOL_PORTAL * 2 and abs(z0 - zmax) > TOL_PORTAL * 2:
                    continue
                p1 = (fe_elem["p_i_unity"][0], fe_elem["p_i_unity"][2])
                p2 = (fe_elem["p_j_unity"][0], fe_elem["p_j_unity"][2])
                d1 = dist_punto_polilinea(p1, el["pts"])
                d2 = dist_punto_polilinea(p2, el["pts"])
                if min(d1, d2) <= TOL_PT:
                    return el
            return None
        return None

    def busca_plan(fe_elem):
        nivel = fe_elem["nivel"]
        tipo = fe_elem["tipo"]
        lista = plan.get(nivel, {}).get(tipo + "s", []) if plan else []
        if tipo == "columna":
            u, v = huella_col(fe_elem)
            for el in lista:
                pos = el.get("posicion")
                if pos and abs(u - pos[0]) < TOL_EJE and abs(v - pos[1]) < TOL_EJE:
                    return el
            return None
        if tipo == "muro":
            zmin, zmax = z_range(fe_elem)
            for el in lista:
                pts = el.get("pts")
                if not pts:
                    continue
                pol = [(pt[0], pt[2] if len(pt) > 2 else pt[1]) for pt in pts]
                p1 = (fe_elem["p_i_unity"][0], fe_elem["p_i_unity"][2])
                p2 = (fe_elem["p_j_unity"][0], fe_elem["p_j_unity"][2])
                if min(dist_punto_polilinea(p1, [list(x) + [0.0, x[1]] for x in pol]) if False else 0, TOL_PT) == 0:
                    pass
                if min(dist_punto_polilinea(p1, pts), dist_punto_polilinea(p2, pts)) <= TOL_PT:
                    return el
            return None
        return None

    def desfase_fe_plan(fe_elem):
        """FE columna P.M. sin enlace: la unica columna P.M. del mismo nivel en el
        viewer es su contraparte fisica (pozo a base de P.M.), desplazada del
        candidato/FE. Devuelve el viewer_id o None."""
        if fe_elem["tipo"] != "columna" or "P.M." not in (fe_elem.get("seccion") or ""):
            return None
        for el in pisos.get(fe_elem["nivel"], {}).get("columnas", []):
            if "P.M." not in (el.get("seccion") or ""):
                continue
            d = math.hypot(fe_elem["p_i_unity"][0] - el["posicion"][0],
                           fe_elem["p_i_unity"][2] - el["posicion"][2])
            if d > TOL_EJE:
                return el, d
        return None

    cls = defaultdict(list)
    resumen = defaultdict(int)
    for e in fe:
        est = e["correspondencia"].get("estado")
        if est != "SIN_CORRESPONDENCIA_VIEWER":
            continue
        tag = e["tag"]
        tipo = e["tipo"]
        if tipo == "stub_elastico_rigidez_elevada":
            cls["AUX_STUB"].append({"tag": tag, "tipo": tipo, "nivel": e["nivel"], "seccion": e["seccion"], "evidencia": "dispositivo analitico (conector rigido); excluido de cobertura fisica."})
            resumen["AUX_STUB"] += 1
            continue
        aux_seg = nodos_compartidos(e, por_nodo, tags_mapeados)
        vw = busca_viewer(e)
        pl = busca_plan(e)
        if aux_seg:
            clave = "AUX_SEGMENTO_VERTICAL"
            ev = "comparte nodo con FE ya mapeado; huella del mismo objeto vertical."
        elif vw is not None:
            clave = "FISICO_MAPEO_PENDIENTE"
            ev = f"existe en viewer ({vw['id']}) y no tiene enlace; geometria coincidente."
        elif pl is not None:
            dv = desfase_fe_plan(e)
            if dv is not None:
                dv_el, dv_d = dv
                clave = "FISICO_FE_DESPLAZADO"
                ev = (f"existe en viewer ({dv_el['id']}) y en candidato ({pl.get('id', '?')}); "
                      f"posicion FE = ({e['p_i_unity'][0]:.2f},{e['p_i_unity'][2]:.2f}) vs "
                      f"huella DXF REUBICADA viewer = ({dv_el['posicion'][0]:.2f},{dv_el['posicion'][2]:.2f}); "
                      f"desfase {dv_d:.2f} m (ver nota REUBICADA del viewer); requiere re-mesh FE.")
            else:
                clave = "FISICO_AUSENTE_VIEWER"
                ev = f"existe en candidato del plano ({pl.get('id', '?')}) y no en el viewer."
        else:
            clave = "PENDIENTE_DE_FUENTE"
            ev = "sin objeto equivalente en viewer ni en candidato; se requiere verificacion de lamina."
        cls[clave].append({"tag": tag, "tipo": tipo, "nivel": e["nivel"], "seccion": e["seccion"], "evidencia": ev})
        resumen[clave] += 1

    return {"resumen": dict(resumen), "detalle": {k: v for k, v in cls.items()}}


def main(argv=None) -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    edificios = argv[1:] or ["I", "II"]
    for ed in edificios:
        fe = carga_fe(ed)
        pisos = carga_viewer(ed)
        plan = carga_candidatos_el(ed)
        rep = clasificar_edificio(ed, fe, pisos, plan)
        doc = {
            "edificio": ed,
            "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fuente": ("candidatos EI (planos DXF 101/102/103) para plan; "
                       "EII sin DXF: la referencia de plano es la geometria recibida del viewer."),
            "resumen": rep["resumen"],
            "detalle": rep["detalle"],
        }
        (DOCS / f"CLASIFICACION_SIN_{ed}.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        md = [f"# Clasificacion de elementos FE SIN_CORRESPONDENCIA_VIEWER — Edificio {ed}\n",
              f"_Generado {doc['fecha']} UTC_\n",
              f"Fuente de la referencia de plano: {doc['fuente']}\n",
              "| clase | cuenta |", "|---|---|"]
        for k, n in sorted(rep["resumen"].items()):
            md.append(f"| {k} | {n} |")
        md.append("\n## Detalle\n")
        for k in ("AUX_STUB", "AUX_SEGMENTO_VERTICAL", "FISICO_MAPEO_PENDIENTE",
                  "FISICO_AUSENTE_VIEWER", "FISICO_FE_DESPLAZADO", "PENDIENTE_DE_FUENTE"):
            if not rep["detalle"].get(k):
                continue
            md.append(f"### {k} ({len(rep['detalle'][k])})\n")
            for it in sorted(rep["detalle"][k], key=lambda x: (x["nivel"], x["tag"])):
                md.append(f"- {it['nivel']} {it['tipo']} tag={it['tag']} sec={it['seccion']} — {it['evidencia']}")
            md.append("")
        out = "\n".join(md)
        (DOCS / f"CLASIFICACION_SIN_{ed}.md").write_text(out, encoding="utf-8")
        print(f"=== Edificio {ed} === resumen:", json.dumps(rep["resumen"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))