"""Recalcula la armadura y la capacidad ACI 318-19 en el JSON de Unity sin volver a correr OpenSees.

La armadura no cambia la rigidez del modelo (secciones brutas con factores de fisuracion), asi que las
fuerzas, los desplazamientos y las reacciones del JSON siguen valiendo. Este script toma esas fuerzas y
vuelve a calcular, con data/armaduras.json:

  - la capacidad y el DCR de vigas y columnas (capacidad_ha.evaluar, igual que el exportador);
  - las curvas P-M de diseno de columnas (una por seccion + armadura) y de muros (armadura real);
  - las curvas de las secciones de fibras: COL70/70_FIBER y el muro de referencia (data/part_e_wall.json);
  - el resumen de armadura y el registro de muros.

exportar_resultados_unity.py hace lo mismo al final de una corrida completa con OpenSees; este script
sirve para actualizar la capacidad sin OpenSees (por ejemplo, despues de editar data/armaduras.json).

Uso (desde la raiz del repositorio):
    python -X utf8 Proyecto1/scripts/actualizar_armadura.py
    python -X utf8 Proyecto1/scripts/actualizar_armadura.py --armaduras cambios.json --out prueba.json
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import capacidad_ha as cha  # noqa: E402
import carga_viva_sismo as cvm  # noqa: E402
import exportar_resultados_unity as exp  # noqa: E402

ARMADURAS = exp.ROOT_DIR / "data" / "armaduras.json"
PART_E_WALL = exp.ROOT_DIR / "data" / "part_e_wall.json"


def _sha(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
    except (OSError, TypeError):
        return None


def capacidad_elementos(u, arm):
    """Capacidad y DCR de vigas y columnas con las fuerzas guardadas en el JSON (mismo calculo que el exportador)."""
    nodes = {n["id"]: n for n in u["nodes"]}
    combos = {c["name"]: {k: c.get(k, 0.0) for k in ("G", "Q", "EX", "EY")} for c in u["p1l4"]["combinations"]}
    fuerzas = {(int(f["id"]), f["combo"]): f["f"] for f in u["p1l4"]["elementForces"]}
    col_curves = {}
    resumen = {"vigas": 0, "columnas": 0, "vigas_DCR_mayor_1": 0, "columnas_DCR_mayor_1": 0,
               "DCR_max_viga": 0.0, "DCR_max_columna": 0.0, "peorViga": "", "peorColumna": ""}
    for el in u["elements"]:
        if el.get("type") not in ("viga", "columna"):
            continue
        el.pop("capacidad", None)
        el.pop("pmCurveId", None)
        if el.get("removed") or el.get("nodeI") not in nodes or el.get("nodeJ") not in nodes:
            continue
        length = cvm.element_length(el, nodes)
        fbc, wbc = {}, {}
        for name, lambdas in combos.items():
            f = fuerzas.get((int(el["id"]), name))
            if f:
                fbc[name] = f
                wbc[name] = cvm.gravity_w(el, nodes, lambdas) if el.get("type") == "viga" else 0.0
        cap = cha.evaluar(el, fbc, wbc, length, arm)
        if not cap:
            continue
        if "curvaPM" in cap:
            cid = "{}_{}".format(el.get("sectionId"), cap["armadura"].get("barras", "")).replace("φ", "f")
            col_curves[cid] = {"puntos": cap.pop("curvaPM"), "P0": cap.get("P0_kN", 0.0), "arm": dict(cap["armadura"]),
                               "b": el.get("width_m"), "h": el.get("height_m")}
            el["pmCurveId"] = cid
        el["capacidad"] = cap
        key = "vigas" if el["type"] == "viga" else "columnas"
        resumen[key] += 1
        dcr = cap.get("DCR", 0.0)
        if dcr > 1.0:
            resumen[key + "_DCR_mayor_1"] += 1
        tag_key, max_key = ("peorViga", "DCR_max_viga") if key == "vigas" else ("peorColumna", "DCR_max_columna")
        if dcr > resumen[max_key]:
            resumen[max_key] = dcr
            resumen[tag_key] = el.get("elementTag", "")
    return col_curves, resumen


def curvas_pm(u, arm, col_curves):
    """Lista pmCurves en el mismo orden y formato que el exportador."""
    anteriores = {c["sectionId"]: c for c in u["p1l4"].get("pmCurves", [])}
    curvas = []
    # Seccion de fibras de la columna (5 puntos nominales)
    sec = cvm.make_column_fibers()
    ag = sec["b"] * sec["h"]
    ast = len(sec["rebar_xy"]) * sec["bar_area_m2"]
    po = 0.85 * sec["fc"] * (ag - ast) + sec["fy"] * ast
    raw = cvm.simplified_pm_points(sec, po)
    curvas.append({
        "sectionId": "COL70/70_FIBER", "elementType": "columna", "b_m": 0.70, "h_m": 0.70,
        "fc_MPa": sec["fc"] / 1000.0, "fy_MPa": sec["fy"] / 1000.0,
        "steelBars": len(sec["rebar_xy"]), "barDiameter_mm": float(cvm.BAR_DIAMETER_MM),
        "Ast_mm2": round(ast * 1e6, 1), "rho_percent": round(100.0 * ast / ag, 2), "Po_kN": po,
        "interpretation": f"Diagrama P-M COL70/70 (5 puntos manuales: compresion pura, balance, falla ductil, flexion pura, "
                          f"traccion pura), fc=G35 (35 MPa), {len(sec['rebar_xy'])} phi{cvm.BAR_DIAMETER_MM:g}.",
        "points": [{"label": p["estado"], "P_kN": p["Pn_kN"], "M_kN_m": p["Mn_kN_m"]} for p in raw],
    })
    # Pilar metalico: no depende de la armadura
    if "PM300x300x20" in anteriores:
        curvas.append(anteriores["PM300x300x20"])
    # Muro de referencia por fibras (data/part_e_wall.json)
    if PART_E_WALL.exists():
        w = exp.load_json(PART_E_WALL)
        a = w.get("armadura") or {}
        pts = [{"label": f'P/Pn0={p["P_frac"]:.2f}', "P_kN": p["P_kN"], "M_kN_m": p["Mmax_kNm"]} for p in w.get("interaccion_PM", [])]
        curvas.append({
            "sectionId": "W_DPRIME_OPENING_TO_3", "elementType": "muro", "b_m": 0.25, "h_m": 7.60, "fc_MPa": 35.0, "fy_MPa": 420.0,
            "steelBars": int(a.get("n_barras_total", 0)), "barDiameter_mm": float(a.get("diametro_mm", 0.0)),
            "Ast_mm2": round(float(a.get("As_total_m2", 0.0)) * 1e6, 1), "rho_percent": round(100.0 * float(a.get("cuantia_vertical", 0.0)), 2),
            "Po_kN": float(w.get("Pn0_kN", 0.0)),
            "interpretation": f"Envolvente P-M W_DPRIME_OPENING_TO_3 por fibras (t=0.25m, L=7.60m, {a.get('bordes', '')}, "
                              f"malla {a.get('malla', '')}). {len(pts)} puntos de la envolvente.",
            "points": pts,
        })
    # Muros con su armadura real
    curvas_muro, por_muro = cha.curvas_muros(u.get("walls", []), arm)
    curvas.extend(curvas_muro)
    # Columnas: una curva de diseno por seccion + armadura
    for cid, cc in col_curves.items():
        ast_c, diams = cha.bars_area_mm2(cc["arm"].get("barras", ""))
        ag_c = float(cc["b"] or 0.0) * float(cc["h"] or 0.0) * 1e6
        curvas.append({
            "sectionId": cid, "elementType": "columna", "b_m": cc["b"], "h_m": cc["h"], "fc_MPa": 35.0, "fy_MPa": 420.0,
            "Po_kN": cc["P0"], "Ast_mm2": ast_c, "barDiameter_mm": float(max(diams)) if diams else 0.0, "steelBars": len(diams),
            "rho_percent": 100.0 * ast_c / ag_c if ag_c > 0 else 0.0,
            "interpretation": f"Curva de DISENO (phiPn, phiMn) ACI 318-19 por compatibilidad de deformaciones: "
                              f"{cc['arm'].get('barras', '')}, estribos {cc['arm'].get('estribos', '')}; phi 0.65-0.90, phiPmax = 0.80 phi P0.",
            "points": [{"label": "", "P_kN": q["P_kN"], "M_kN_m": q["M_kN_m"]} for q in cc["puntos"]],
        })
    return curvas, por_muro, (sec, po, raw)


def semana3(sec, po, raw):
    """Mismo archivo de capacidad COL70/70_FIBER que regenera el exportador."""
    bar_area = sec["bar_area_m2"]
    ast = len(sec["rebar_xy"]) * bar_area
    return {
        "capacityTitle": "Parte D - Capacidad HA COL70/70_FIBER", "sectionId": "COL70/70_FIBER",
        "b_m": sec["b"], "h_m": sec["h"], "fc_MPa": sec["fc"] / 1000.0, "fy_MPa": sec["fy"] / 1000.0,
        "steelBars": len(sec["rebar_xy"]), "barArea_m2": bar_area, "barArea_mm2": bar_area * 1e6,
        "barDiameter_mm": (2.0 * (bar_area / 3.141592653589793) ** 0.5) * 1000.0,
        "Ast_m2": ast, "Ast_mm2": ast * 1e6, "rho_percent": 100.0 * (ast / (sec["b"] * sec["h"])), "Po_kN": po,
        "interpretation": "Diagrama P-M COL70/70 (5 puntos manuales), fc=G35 (35 MPa). Regenerado por actualizar_armadura.py.",
        "pmPoints": [{"label": p["estado"], "P_kN": p["Pn_kN"], "M_kN_m": p["Mn_kN_m"], "phiP_kN": p["phiPn_kN"],
                      "phiM_kN_m": p["phiMn_kN_m"], "phi_1_m": 0.0} for p in raw],
    }


def actualizar(u, arm):
    col_curves, resumen = capacidad_elementos(u, arm)
    curvas, por_muro, fibra = curvas_pm(u, arm, col_curves)
    u["p1l4"]["pmCurves"] = curvas
    for r in u["p1l4"].get("wallRegistry", []):
        if r.get("index") in por_muro:
            r["pmSectionId"] = por_muro[r["index"]]
            r["hasCurve"] = True
    u["p1l4"]["sectionMaterials"] = exp.SECTION_MATERIALS
    u["resumenAnalisis"]["armadura"] = resumen
    return resumen, fibra


def main():
    ap = argparse.ArgumentParser(description="Recalcula armadura y capacidad en el JSON de Unity sin OpenSees")
    ap.add_argument("--armaduras", type=Path, default=None, help="cambios sobre data/armaduras.json (mismo formato)")
    ap.add_argument("--json", type=Path, default=exp.JSON_OUT, help="JSON de Unity de entrada")
    ap.add_argument("--out", type=Path, default=None, help="escribir en otro archivo (no toca los datos del proyecto)")
    a = ap.parse_args()
    overrides = exp.load_json(a.armaduras) if a.armaduras else None
    arm = cha.load_armaduras(overrides=overrides)
    u = exp.load_json(a.json)
    resumen, (sec, po, raw) = actualizar(u, arm)
    corrida = u.setdefault("corrida", {})
    corrida.setdefault("entradas_sha256", {})["armaduras"] = _sha(ARMADURAS)
    corrida["entradas_sha256"]["armaduras_cambios"] = _sha(a.armaduras) if a.armaduras else None
    corrida["capacidad"] = {"script": "python -X utf8 Proyecto1/scripts/actualizar_armadura.py",
                            "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
                            "nota": "capacidad y curvas P-M recalculadas con data/armaduras.json sobre las fuerzas de la corrida de OpenSees"}
    out = a.out or a.json
    exp.write_json(out, u, compact=True)
    if a.out is None:
        exp.write_json(exp.P1L2_RESOURCES / "semana3_resultados_unity.json", semana3(sec, po, raw))
    print(f"Armadura/capacidad: {resumen}")
    print(f"JSON escrito en {out}")


if __name__ == "__main__":
    main()
