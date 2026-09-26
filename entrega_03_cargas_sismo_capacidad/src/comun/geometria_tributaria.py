"""Geometria tributaria canonica. Reutiliza EXACTAMENTE las copias internas mínimas:

  - Edificio I : `data/externas/por_viga.json`
                 (copia interna de viewer_unity/Assets/StreamingAssets/lab_data/
                 edificios/I/tributary/por_viga.json; area tributaria por
                 receptor/viga por nivel; pesos nodales por longitud de segmento).
  - Edificio II: `data/externas/areas_tributarias.csv`
                 (copia interna del ensayo CP2 FASE4B; nivel EII_CP2; los demas
                 niveles del EII no tienen geometria tributaria versionada).

Las rutas se resuelven SIEMPRE relativo a la raiz de la copia (sin rutas
absolutas): si la entrega se corre desde el repo o desde una copia temporal
aislada, `REPO` apunta a la carpeta que contiene `entrega_03_...`.

Nada de esto modifica fuentes: solo lectura.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

NIVELES_EII = ["EII_CP1S", "EII_CP1", "EII_CP2", "EII_CP3", "EII_CP4"]


def _resolver(rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else REPO / rel


def cargar_tributaria_EI(ruta: str | Path) -> dict:
    """por_viga.json -> {por_nivel: {nivel: {area_total, n_receptores, receptores[]}}}."""
    p = _resolver(ruta)
    d = json.loads(p.read_text(encoding="utf-8"))
    por_nivel = {}
    for nivel, reces in d["por_nivel"].items():
        lista = []
        tot = 0.0
        for r in reces:
            a = float(r["area_tributaria_m2"])
            tot += a
            lista.append({
                "id": r["receptor"],
                "area_tributaria_m2": a,
                "n_nodos_fe": r.get("n_nodos_fe"),
                "n_losas": len(r.get("losas", [])),
            })
        por_nivel[nivel] = {
            "area_total_m2": round(tot, 4),
            "n_receptores": len(lista),
            "receptores": lista,
        }
    return {
        "edificio": "I",
        "fuente": str(p),
        "metodo": ("linea a receptores (vigas/muros) con pesos nodales por longitud de "
                   "segmento (Semana 2: tributacion.py)"),
        "por_nivel": por_nivel,
    }


def cargar_tributaria_EII(ruta: str | Path) -> dict:
    """areas_tributarias.csv (nivel EII_CP2) -> canonical; resto de niveles sin geometria."""
    p = _resolver(ruta)
    with open(p, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    por_receptor = {}
    tot = 0.0
    for r in rows:
        soporte = r["soporte"].strip()
        a = float(r["area_tributaria_m2"])
        tot += a
        ent = por_receptor.setdefault(soporte, {
            "id": soporte, "area_tributaria_m2": 0.0, "tipo": r.get("tipo", "").strip(),
            "n_segmentos": 0})
        ent["area_tributaria_m2"] += a
        ent["n_segmentos"] += 1
    por_nivel = {
        "EII_CP2": {
            "area_total_m2": round(tot, 4),
            "n_receptores": len(por_receptor),
            "receptores": list(por_receptor.values()),
        }
    }
    # niveles sin geometria tributaria versionada
    for nv in NIVELES_EII:
        por_nivel.setdefault(nv, {
            "area_total_m2": 0.0, "n_receptores": 0,
            "estado": "PENDIENTE_SIN_GEOMETRIA_TRIBUTARIA", "receptores": []})
    return {
        "edificio": "II",
        "fuente": str(p),
        "metodo": ("paneles -> soportes (vigas/columnas) por areas tributarias "
                   "(ensayo CP2 FASE4B, 1 kPa; nivel EII_CP2)"),
        "area_total_paneles_CP2_m2": round(tot, 4),
        "por_nivel": por_nivel,
    }


def cargar_geometria_tributaria(edificio: str, ruta: str | Path) -> dict:
    edificio = edificio.strip().upper()
    if edificio == "I":
        return cargar_tributaria_EI(ruta)
    if edificio == "II":
        return cargar_tributaria_EII(ruta)
    raise ValueError(f"edificio desconocido: {edificio} (valores validos: I, II)")