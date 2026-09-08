"""Superposicion de casos de carga (Entrega 3).

    R = lambda_G*G + lambda_Q*Q + lambda_EX*EX + lambda_EY*EY

Los coeficientes viven en `config/superposicion.json` (PENDIENTE -> no se usan de
forma silenciosa; se usa el valor demostrativo solo si se pide, marcado como
DEMOSTRACION). La verificacion final para comparar R contra una corrida explicita
equivalente de OpenSees en desplazamiento, reaccion y fuerza interna; NO se da por
implementada mientras no existan los cuatro casos base compatibles (G, Q, EX, EY).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONFIG = REPO / "entrega_03_cargas_sismo_capacidad" / "config" / "superposicion.json"
CASOS_BASE = ["G", "Q", "EX", "EY"]


class CasosBaseIncompletosError(RuntimeError):
    pass


def leer_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def coeficientes(cfg: dict | None = None, usar_demo: bool = False) -> dict:
    cfg = cfg or leer_config()
    lambdas = {}
    for caso in CASOS_BASE:
        ent = cfg["coeficientes"][caso]
        val = ent["lambda"]
        if val is None:
            if not usar_demo:
                raise CasosBaseIncompletosError(
                    f"lambda de {caso} es null (PENDIENTE). Use usar_demo=True para "
                    "aplicar el valor demostrativo marcado DEMOSTRACION_ARBITRARIA.")
            val = ent["demostracion_arbitraria"]
            lambdas[caso] = {"valor": val, "estado": "DEMOSTRACION_ARBITRARIA"}
        else:
            lambdas[caso] = {"valor": val, "estado": "DEFINIDO"}
    return lambdas


def check_casos_base(respuestas: dict) -> None:
    """Exige los cuatro casos compatibles antes de combinar."""
    faltan = [c for c in CASOS_BASE if c not in respuestas]
    if faltan:
        raise CasosBaseIncompletosError(
            "Superposicion NO implementada: faltan casos base compatibles: "
            + ", ".join(faltan) + ". Solo se combina cuando existan G, Q, EX y EY.")


def combinar(respuestas: dict, lambdas: dict) -> dict:
    """Combina respuestas por familia (desplazamiento, reaccion, fuerza_interna).

    Cada respuesta de caso: {"desplazamiento": [...], "reaccion": [...], "fuerza_interna": [...]}
    """
    check_casos_base(respuestas)
    familias = {f: [] for f in ("desplazamiento", "reaccion", "fuerza_interna")}
    for caso in CASOS_BASE:
        r = respuestas[caso]
        for f in familias:
            if f not in r:
                raise KeyError(f"respuesta de {caso} sin familia '{f}'")
            familias[f].append(r[f])
    R = {}
    detalle = []
    for f, listas in familias.items():
        n = len(listas[0])
        comp = [0.0] * n
        for caso, vals in zip(CASOS_BASE, listas):
            lam = lambdas[caso]["valor"]
            for i in range(n):
                comp[i] += lam * vals[i]
        R[f] = comp
        detalle.append({"familia": f, "n": n,
                        "lambdas": {c: lambdas[c]["valor"] for c in CASOS_BASE}})
    return {"respuesta_combinada": R, "coeficientes_usados": detalle}


def verificar_contra_opensees(R_combinado: dict, R_explicito_opensees: dict,
                              tolerancia_rel=0.01) -> dict:
    """Compara la superposicion con una corrida explicita equivalente de OpenSees."""
    resultados = {}
    global_ok = True
    for f in ("desplazamiento", "reaccion", "fuerza_interna"):
        a = R_combinado[f]
        b = R_explicito_opensees[f]
        if len(a) != len(b):
            resultados[f] = {"estado": "ERROR(LONGITUD_DISTINTA)"}
            global_ok = False
            continue
        dmax = max((abs(x - y) for x, y in zip(a, b)), default=0.0)
        escala = max((abs(y) for y in b), default=1.0)
        drel = dmax / escala if escala else (1.0 if dmax else 0.0)
        ok = drel <= tolerancia_rel
        global_ok = global_ok and ok
        resultados[f] = {"dmax": dmax, "drel": drel, "estado": "OK" if ok else "ERROR"}
    return {"comparacion": resultados, "estado": "OK" if global_ok else "ERROR"}