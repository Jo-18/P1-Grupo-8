"""Genera la tabla CSV de esfuerzos (fuerzas internas por elemento) del Edificio I.

Fuente: solucion_cruda_primera_ejecucion.json -> fuerzas_local_por_elemento
(llave = tag de elemento FE). La identidad de cada elemento (nivel, tipo, id,
nodos y coordenadas) se reconstruye de forma DETERMINISTA re-ensamblando el marco
3D (Marco.construir, SIN resolver: no se ejecuta analyze y no se modifica ningun
dato de entrada ni resultado existente).

Convencion de localForce de OpenSees (elasticBeamColumn 3D), por extremo:
  [N, Vy, Vz, T, My, Mz]  (kN y kN.m)
Los 12 valores desenrollados son: N_i, Vy_i, Vz_i, T_i, My_i, Mz_i,
                               N_j, Vy_j, Vz_j, T_j, My_j, Mz_j
(extremo i = nodo_i, extremo j = nodo_j).

Ademas se agregan columnas de envolvente por elemento (maximos en valor absoluto
a lo largo de la pieza usando ambos extremos) para facil lectura en la defensa:
  N_mx, Vy_mx, Vz_mx, T_mx, My_mx, Mz_mx, |M|_mx_abs (kN o kN.m).

ADVERTENCIA (coherencia con el proyecto): la ejecucion es de laboratorio,
"no utilizable para diseno" (estado del paquete); solo Edificio I tiene solucion
FE. El Edificio II NO tiene solucion estructural (geometria_adaptada_sin_solucion).
"""

from __future__ import annotations

import csv, json
from pathlib import Path

from . import geometria_fe as GF
from .marco import Marco

_LAB = Path(__file__).resolve().parents[3]
RESULT = _LAB / "resultados" / "modelo_estructural"

EJECUCION = "primera_ejecucion"
SOL = RESULT / f"solucion_cruda_{EJECUCION}.json"
CSV_OUT = RESULT / f"esfuerzos_por_elemento_{EJECUCION}.csv"

LOCAL_FIELDS = [
    "N_i", "Vy_i", "Vz_i", "T_i", "My_i", "Mz_i",
    "N_j", "Vy_j", "Vz_j", "T_j", "My_j", "Mz_j",
]


def _reconstruir_identidad():
    niveles = GF.cargar_todos()
    marco = Marco(niveles)
    marco.construir()
    ident = {}
    for rec in marco.columnas + marco.vigas_elem + marco.muros_elem:
        tag = int(rec["tag"])
        ident[tag] = {
            "nivel": rec.get("nivel") or "",
            "tipo": rec.get("tipo") or "",
            "seccion": rec.get("seccion") or "",
            "elemento_id": rec.get("elemento_id") or "",
            "nodo_i": int(rec["nodo_i"]),
            "nodo_j": int(rec["nodo_j"]),
            "u_i": rec.get("u_i"), "v_i": rec.get("v_i"), "z_i": rec.get("z_i"),
            "u_j": rec.get("u_j"), "v_j": rec.get("v_j"), "z_j": rec.get("z_j"),
        }
    return ident


def _envelope(loc):
    """loc: lista 12 -> envolventes por pieza (max abs entre ambos extremos)."""
    ni, vyi, vzi, ti, myi, mzi = loc[0], loc[1], loc[2], loc[3], loc[4], loc[5]
    nj, vyj, vzj, tj, myj, mzj = loc[6], loc[7], loc[8], loc[9], loc[10], loc[11]
    return {
        "N_mx": max(abs(ni), abs(nj)),
        "Vy_mx": max(abs(vyi), abs(vyj)),
        "Vz_mx": max(abs(vzi), abs(vzj)),
        "T_mx": max(abs(ti), abs(tj)),
        "My_mx": max(abs(myi), abs(myj)),
        "Mz_mx": max(abs(mzi), abs(mzj)),
        "M_mx_abs": max(abs(myi), abs(myj), abs(mzi), abs(mzj)),
    }


def generar(csv_out: Path = CSV_OUT) -> Path:
    cruda = json.loads(SOL.read_text(encoding="utf-8"))
    fuerzas = cruda["fuerzas_local_por_elemento"]
    ident = _reconstruir_identidad()

    ident_keys = set(ident.keys())
    fuerza_keys = set(int(k) for k in fuerzas.keys())
    sin_identidad = sorted(fuerza_keys - ident_keys)
    sin_fuerza = sorted(ident_keys - fuerza_keys)

    rows = []
    for tag in sorted(fuerza_keys):
        if tag not in ident:
            continue
        info = ident[tag]
        loc = fuerzas[str(tag)]
        rows.append({
            "edificio": "I",
            "ejecucion": EJECUCION,
            "nivel": info["nivel"],
            "tipo": info["tipo"],
            "seccion": info["seccion"],
            "elemento_id": info["elemento_id"],
            "tag": tag,
            "nodo_i": info["nodo_i"],
            "nodo_j": info["nodo_j"],
            "u_i_m": info["u_i"], "v_i_m": info["v_i"], "z_i_m": info["z_i"],
            "u_j_m": info["u_j"], "v_j_m": info["v_j"], "z_j_m": info["z_j"],
        })
        for name, val in zip(LOCAL_FIELDS, loc):
            rows[-1][name] = round(val, 6)
        for name, val in _envelope(loc).items():
            rows[-1][name] = round(val, 6)

    cols = (["edificio", "ejecucion", "nivel", "tipo", "seccion", "elemento_id",
             "tag", "nodo_i", "nodo_j",
             "u_i_m", "v_i_m", "z_i_m", "u_j_m", "v_j_m", "z_j_m"]
            + LOCAL_FIELDS
            + ["N_mx", "Vy_mx", "Vz_mx", "T_mx", "My_mx", "Mz_mx", "M_mx_abs"])
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    print("CSV escrito:", csv_out)
    print("filas:", len(rows))
    print("elementos con fuerza y sin identidad:", sin_identidad)
    print("elementos FE sin fuerza (stub/conector):", sin_fuerza)
    return csv_out


if __name__ == "__main__":
    generar()
