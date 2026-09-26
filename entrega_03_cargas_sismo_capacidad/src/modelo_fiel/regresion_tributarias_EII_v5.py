"""Regresion de areas tributarias EII: CP2 v5 vs ensayo FASE4B (laboratorio).

Genera modelo_fiel/regresiones/regresion_tributarias_EII_v5.json y .md
con tolerancias DICLARADAS y por-fila.
"""
from __future__ import annotations
import json, csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
EX = E3 / "data" / "externas"
OUTD = E3 / "modelo_fiel" / "regresiones"

REF = EX / "areas_tributarias.csv"
GEN = EX / "areas_tributarias_EII_todos_niveles.json"

TOL_SIGMA_SUMA = 0.5   # %
TOL_FILA = 5.0         # %

def main():
    gen = json.loads(GEN.read_text(encoding="utf-8"))
    cp2 = next(x for x in gen["niveles"] if x["nivel"] == "EII_CP2")
    mine = {(r["panel"], r["borde"]): r for r in cp2["filas"]}
    ref_rows = list(csv.reader(open(REF, encoding="utf-8")))[1:]
    filas = []
    sum_ref = 0.0
    sum_m = 0.0
    for r in ref_rows:
        key = (r[0], r[1])
        ref = float(r[5])
        sum_ref += ref
        rw = {"panel": r[0], "borde": r[1], "area_ref_m2": ref}
        if key in mine:
            mm = mine[key]["area_tributaria_m2"]
            rw["area_v5_m2"] = mm
            rw["dif_rel_pct"] = round(abs(mm - ref) / ref * 100, 3) if ref else None
            rw["dentro_tol_fila"] = (abs(mm - ref) / ref * 100) <= TOL_FILA if ref else True
            sum_m += mm
        else:
            rw["area_v5_m2"] = None
            rw["dif_rel_pct"] = None
            rw["dentro_tol_fila"] = False
        filas.append(rw)
    n = len(filas)
    n_dentro = sum(1 for f in filas if f["dentro_tol_fila"])
    fuera = [f for f in filas if not f["dentro_tol_fila"]]
    res = {
        "referencia": {
            "ensayo": "EII_CP2_transferencia_mixta_FASE4B (laboratorio)",
            "archivo_ref": REF.name, "archivo_generado": GEN.name,
        },
        "tolerancias_documentadas": {
            "metodo": "rel |v5-ref|/ref x 100",
            "suma_nivel_pct": TOL_SIGMA_SUMA,
            "por_fila_pct": TOL_FILA,
            "nota": "Tolerancias declaradas v5; se reportan valores logrados.",
        },
        "resultado": {
            "n_filas_ref": n,
            "n_dentro_tol_fila": n_dentro,
            "frac_dentro_tol_fila_pct": round(n_dentro / n * 100, 2) if n else None,
            "suma_ref_m2": round(sum_ref, 6),
            "suma_v5_m2": round(sum_m, 6),
            "dif_suma_rel_pct": round(abs(sum_m - sum_ref) / sum_ref * 100, 4) if sum_ref else None,
            "dentro_tol_suma": (abs(sum_m - sum_ref) / sum_ref * 100) <= TOL_SIGMA_SUMA if sum_ref else None,
            "n_filas_fuera_tol": len(fuera),
            "peor_fila": max((f["dif_rel_pct"] for f in fuera if f["dif_rel_pct"]), default=None),
        },
        "fuera_de_tolerancia": sorted(fuera, key=lambda f: -(f["dif_rel_pct"] or 0)),
        "limitaciones_documentadas": [
            "El ensayo FASE4B usa columnas como receptores nodales (COL_002/COL_003) no",
            "reproducidas en v5 (eii_viewer las declara referencia_no_receptor_losa).",
            "Los paneles corredor S0/S6/N6 en FASE4B reparten franjas secundarias",
            "(V_011/V_017/V_022, 0.105-0.345 m2) con logica mixta unidireccional+nodal",
            "no codificada en eii_viewer; en v5 ese area queda en la viga principal.",
            "Las zonas W2/W3 y paños L_006/L_009/L_010 muestran difs 5.5-6% por",
            "alineacion de malla y conjunto de apoyos; se preserva conservacion 28/28.",
            "ancho_max_m no se reproduce en v5 (solo area y ancho_promedio).",
        ],
    }
    OUTD.mkdir(parents=True, exist_ok=True)
    (OUTD / "regresion_tributarias_EII_v5.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    # MD resumido
    md = [
        "# Regresión de áreas tributarias EII — CP2 v5 vs FASE4B",
        "",
        f"- Referencia: `{REF.name}` (ensayo EII_CP2_transferencia_mixta_FASE4B).",
        f"- Generado: `{GEN.name}` (motor `src/modelo_fiel/tributarias_EII_niveles.py`).",
        f"- Tolerancias declaradas: suma = {TOL_SIGMA_SUMA}% ; por fila = {TOL_FILA}%.",
        "",
        "## Resultado",
        "",
        f"- Filas de referencia: **{n}**; dentro de tolerancia por fila: **{n_dentro}/{n} ({res['resultado']['frac_dentro_tol_fila_pct']}%)**.",
        f"- Suma referencia: **{round(sum_ref, 6)} m²**; suma v5: **{round(sum_m, 6)} m²**;",
        f"  diferencia rel: **{res['resultado']['dif_suma_rel_pct']}%** → dentro de tolerancia:",
        f"  **{res['resultado']['dentro_tol_suma']}**.",
        f"- Conservación por panel: **28/28** (check en el JSON de niveles).",
        "",
        "## Fuera de tolerancia por fila (>5%)",
        "",
    ]
    md += [f"- `{f['panel']} → {f['borde']}`: ref {f['area_ref_m2']} m², v5 {f['area_v5_m2']} m², dif {f['dif_rel_pct']}%"
           for f in res["fuera_de_tolerancia"]]
    md += ["", "## Limitaciones documentadas", ""]
    md += [f"- {x}" for x in res["limitaciones_documentadas"]]
    md += ["", "Detalles por fila en `regresion_tributarias_EII_v5.json`."]
    (OUTD / "regresion_tributarias_EII_v5.md").write_text("\n".join(md), encoding="utf-8")
    print(f"filas={n} dentro={n_dentro} ({res['resultado']['frac_dentro_tol_fila_pct']}%) "
          f"suma_rel={res['resultado']['dif_suma_rel_pct']}% dentro_suma={res['resultado']['dentro_tol_suma']}")
    print("OK", OUTD / "regresion_tributarias_EII_v5.{json,md}")

if __name__ == "__main__":
    main()