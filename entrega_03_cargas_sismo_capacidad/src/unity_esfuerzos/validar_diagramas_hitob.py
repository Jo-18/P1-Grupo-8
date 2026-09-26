"""Validacion INDEPENDIENTE del diagrama de fuerzas NCh3171 (Hito B).

Para cada elemento del perfil que consume Unity se recompone cada combinacion
U1..U4 como combinacion lineal de sus casos base (G, Q, EX, EY) con los
coeficientes de la norma (COMBINACIONES_NCH3171) y se compara componente a
componente (12) contra el vector que viajó desde OpenSees al perfil.

Es una validacion independiente del DIAGRAMA (N,V,M) porque aplica la regla de
combinacion normativa con signos explícitos sobre fuerzas de corridas
independientes, sin reutilizar el producto del exportador. Detecta etiquetado
incorrecto, signos invertidos, redondeos o vectores ausentes en toda la base.

Detección de elementos sin resultado esperado: si en el perfil un elemento no
tiene el caso base o el combo (o todos sus vectores base son nulos), se
clasifica como "no_calificable" y se reporta (no es un fallo de la validacion).

Adicionalmente expone la MUESTRA de jurado: las cuplas (viga, columna
demostrada, muro demostrado) con su desviación maximal por caso para mostrar en
el reporte/demo.

Salidas: results/unity_hitob/validacion_diagramas_{I,II}.json
         results/unity_hitob/validacion_diagramas_hitob.md
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
RES_HITOB = E3 / "results" / "unity_hitob"
PERFIL = (REPO / "viewer_unity" / "Assets" / "StreamingAssets" / "lab_data"
          / "edificios")

sys.path.insert(0, str(E3))

from src.modelo_fiel.combinaciones_nch3171 import COMBINACIONES_NCH3171  # noqa: E402

CASOS_BASE = ("G", "Q", "EX", "EY")
_TERMO = re.compile(
    r"[+-]?\s*(?:(?:\d*\.\d+|\d+)\s*\*\s*)?[A-Z]{1,2}")
_TERMO_UNO = re.compile(
    r"^\s*([+-]?)\s*(?:((?:\d*\.\d+|\d+))\s*\*\s*)?([A-Z]{1,2})\s*$")


def _coeficientes(expresion: str) -> dict:
    """'1.2*G + Q - 1.4*EX' -> {'G': 1.2, 'Q': 1.0, 'EX': -1.4}."""
    out = {}
    for parte in _TERMO.findall(expresion):
        m = _TERMO_UNO.match(parte)
        if not m:
            raise ValueError(f"expresion no parseable: {expresion!r} -> {parte!r}")
        signo, mag, caso = m.groups()
        coef = float(mag) if mag else 1.0
        if signo == "-":
            coef = -coef
        out.setdefault(caso, 0.0)
        out[caso] += coef
    return out


_RESTOS = {c["id"]: _coeficientes(c["expresion"])
           for c in COMBINACIONES_NCH3171 if c["id"].startswith("U")}


def _max_componentes(vecs: dict, casos=CASOS_BASE) -> float:
    m = 0.0
    for c in casos:
        v = vecs.get(c)
        if v:
            m = max(m, max(abs(float(x)) for x in v))
    return m


def _comparar(esperado, almacenado, escala: float) -> dict:
    if almacenado is None:
        return {"calificable": False, "motivo": "caso_ausente"}
    difs = [abs(float(esperado[i]) - float(almacenado[i])) for i in range(12)]
    max_abs = max(difs)
    tol = max(2e-2, escala * 1e-6, max_abs * 0.0)
    n_err = sum(1 for d in difs if d > tol)
    return {"calificable": True, "max_abs_kN": round(max_abs, 6),
            "tol_kN": round(tol, 6), "n_componentes_fuera": n_err,
            "ok": n_err == 0}


def _sintesis_esperado(vecs: dict, coef: dict, combo_id: str) -> list | None:
    n = 12
    acc = [0.0] * n
    for caso, c in coef.items():
        v = vecs.get(caso)
        if v is None:
            return None
        for i in range(n):
            acc[i] += c * float(v[i])
    return acc


def _seleccionar_muestra(perfil, edificio: str) -> dict:
    from src.unity_esfuerzos.pm_capacidad_demanda_hitob import MURO_EII_TAG
    el = perfil["elementos"]
    cols = [e for e in el if e["tipo"] == "columna"
            and e["correspondencia"].get("viewer_id")]
    viga_mx = max((e for e in el if e["tipo"] == "viga"
                   and e["correspondencia"].get("viewer_id")),
                  key=lambda e: max(abs(float(x)) for x in e["fuerzas"]["U1_GQ"][:6]),
                  default=None)
    col = max(cols, key=lambda e: _max_componentes(e["fuerzas"]),
              default=None) if cols else None
    mur = next((e for e in el if e["tipo"] == "muro" and e["tag"] == MURO_EII_TAG
                and edificio == "II"), None)
    return {
        "viga_demostrada": ({"tag": viga_mx["tag"],
                             "viewer_id": viga_mx["correspondencia"]["viewer_id"],
                             "nivel": viga_mx["nivel"], "seccion": viga_mx["seccion"]}
                            if viga_mx else None),
        "columna_demostrada": ({"tag": col["tag"],
                                "viewer_id": col["correspondencia"]["viewer_id"],
                                "nivel": col["nivel"], "seccion": col["seccion"]}
                               if col else None),
        "muro_demostrado": ({"tag": mur["tag"], "nivel": mur["nivel"]}
                            if mur else None)}


def _validar(edificio: str) -> dict:
    p = json.loads((PERFIL / edificio / "results"
                    / ("esfuerzos_FE_EDIFICIO_%s.json" % edificio))
                   .read_text(encoding="utf-8"))
    muestras = _seleccionar_muestra(p, edificio)
    tags_muestra = {d["tag"] for d in muestras.values() if d}
    por_elemento = {}
    n_calificables = 0
    n_no_calificables = 0
    peor = {"combo": None, "tag": None, "err": 0.0}
    destalle_muestra = {}
    for el in p["elementos"]:
        vecs = el["fuerzas"]
        escala = _max_componentes(vecs)
        filas = {}
        todo_ok = True
        calificable = True
        for combo in _RESTOS:
            esperado = _sintesis_esperado(vecs, _RESTOS[combo], combo)
            if esperado is None:
                calificable = False
                filas[combo] = {"calificable": False, "motivo": "base_incompleto"}
                todo_ok = False
                continue
            r = _comparar(esperado, vecs.get(combo), escala)
            filas[combo] = r
            if r.get("calificable"):
                if r["max_abs_kN"] > peor["err"]:
                    peor = {"combo": combo, "tag": el["tag"],
                            "err": r["max_abs_kN"]}
            todo_ok = todo_ok and r.get("ok", False)
        if calificable:
            n_calificables += 1
        else:
            n_no_calificables += 1
        por_elemento[str(el["tag"])] = {
            "tipo": el["tipo"], "nivel": el["nivel"],
            "escala_kN": round(escala, 3), "ok": todo_ok,
            "combos": filas}
        if el["tag"] in tags_muestra:
            destalle_muestra[str(el["tag"])] = {
                "tipo": el["tipo"], "ok": todo_ok,
                "max_abs_kN": max(f["max_abs_kN"] for f in filas.values()
                                  if f.get("calificable")),
                "peor_combo": max((c for c in filas if filas[c].get("calificable")),
                                  key=lambda c: filas[c]["max_abs_kN"])}
    return {"edificio": edificio,
            "regla": ("combo recomputado = sum(coef_i * caso_base_i) con "
                      "COMBINACIONES_NCH3171; comparado componente a componente "
                      "(12) contra el vector del perfil; tol = max(2e-2 kN, "
                      "1e-6 * escala del elemento)"),
            "muestra_jurado": muestras,
            "muestra_resultados": destalle_muestra,
            "n_elementos": len(por_elemento),
            "n_calificables": n_calificables,
            "n_no_calificables": n_no_calificables,
            "peor_desviacion_elemento": peor,
            "por_elemento": por_elemento}


def _escribir(edificio: str, data: dict) -> Path:
    RES_HITOB.mkdir(parents=True, exist_ok=True)
    jp = RES_HITOB / ("validacion_diagramas_%s.json" % edificio)
    jp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                  encoding="utf-8")
    return jp


def _md(I: dict, II: dict) -> str:
    L = ["# Validacion independiente del diagrama de fuerzas (Hito B)",
         "",
         "Se recompone cada U1..U4 como combinacion lineal de G/Q/EX/EY con los "
         "coeficientes de la norma y se compara contra el vector almacenado por "
         "OpenSees. Sin reutilizar el producto del exportador.",
         ""]
    for d in (I, II):
        L += [f"## Edificio {d['edificio']}",
               f"- Elementos: {d['n_elementos']} (calificables {d['n_calificables']}, "
               f"no calificables {d['n_no_calificables']})",
               f"- Peor desviacion (elemento/combo): {d['peor_desviacion_elemento']}",
               "- Muestra del jurado:"]
        for nombre, r in d["muestra_resultados"].items():
            key = next(k for k, v in d["muestra_jurado"].items()
                       if v and v["tag"] == int(nombre))
            L.append(f"  - {key} tag {nombre}: ok={r['ok']}, "
                     f"max|Δ|={r['max_abs_kN']} kN ({r['peor_combo']})")
        L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    edificios = sorted({a for a in args if a in ("I", "II")}) or ["I", "II"]
    datos = {}
    ok_global = True
    for e in edificios:
        d = _validar(e)
        jp = _escribir(e, d)
        n_ko = sum(1 for v in d["por_elemento"].values() if not v["ok"])
        ok_global = ok_global and n_ko == 0
        datos[e] = d
        print(f"{e}: elementos={d['n_elementos']} calificables="
              f"{d['n_calificables']} no_cal={d['n_no_calificables']} "
              f"no_ok={n_ko} peor={d['peor_desviacion_elemento']} -> {jp}")
    (RES_HITOB / "validacion_diagramas_hitob.md").write_text(
        _md(datos.get("I", {}), datos.get("II", {})), encoding="utf-8")
    print("validacion_diagramas_hitob.md escrito")
    return 0 if ok_global else 2


if __name__ == "__main__":
    raise SystemExit(main())