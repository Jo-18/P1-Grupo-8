"""Genera columnas_tramos_ei.json con los TRAMOS de columna reales del Edificio I.

Reconstruye el marco 3D FE de la ejecucion primaria (Marco.construir, SIN resolver:
no se llama a analyze ni se modifica ningun dato de entrada/resultado) y vuelca los
tramos de columna con sus nodos inicial/final y cotas reales (z_i, z_j).

Cada tramo es el segmento `col_{u}_{v}_{nivel}` del modelo FE, donde `nivel` es la
cota superior del tramo y `z_i`/`z_j` son las cotas de los nodos reales. NO se crea
ningun tramo P4 si no existe columna documentada (ninguna prolongacion fabricada).

Uso en el visor: para Edificio I, la columna en planta (u,v) de cada nivel se dibuja
desde z_i hasta z_j segun este archivo (reemplaza la altura de piso fabricada).
Salida: analisis_estructural/edificio_I/resultados/modelo_estructural/columnas_tramos_ei.json
"""

from __future__ import annotations

import json
from pathlib import Path

from . import geometria_fe as GF
from .marco import Marco

_LAB = Path(__file__).resolve().parents[3]
RESULT = _LAB / "resultados" / "modelo_estructural"
OUT = RESULT / "columnas_tramos_ei.json"


def generar(out: Path = OUT) -> Path:
    niveles = GF.cargar_todos()
    marco = Marco(niveles)
    marco.construir()
    tramos = []
    for rec in marco.columnas:
        tramos.append({
            "elemento_id": rec.get("elemento_id"),
            "nivel": rec.get("nivel"),
            "tipo": "columna",
            "tag": int(rec["tag"]),
            "nodo_i": int(rec["nodo_i"]),
            "nodo_j": int(rec["nodo_j"]),
            "u": rec.get("u_i"),
            "v": rec.get("v_i"),
            "z_i": rec.get("z_i"),
            "z_j": rec.get("z_j"),
        })
    # unificar la posicion en planta por nodo inicial (coordenadas FE = u,v reales)
    doc = {
        "edificio": "I",
        "ejecucion": "primera_ejecucion",
        "fuente": "reconstruccion determinista del marco FE (sin re-ejecutar analisis)",
        "convencion": "cotas en metros; z_i = base del tramo, z_j = cota superior",
        "nota": ("NO se fabrica prolongacion del ultimo nivel: solo se incluyen tramos "
                 "con columna documentada en el modelo FE. Si falta tramo P4, la "
                 "columna termina en su cota documentada y la extension se marca pendiente."),
        "n_tramos": len(tramos),
        "tramos": tramos,
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("escrito:", out)
    print("n_tramos:", len(tramos))
    niveles_presentes = sorted({t["nivel"] for t in tramos}, key=lambda s: s)
    print("niveles con tramos:", niveles_presentes)
    return out


if __name__ == "__main__":
    generar()
