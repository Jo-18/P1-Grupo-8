"""Comando preparado para la verificacion estructural FINAL de la superposicion.

R = lambda_G*G + lambda_Q*Q + lambda_EX*EX + lambda_EY*EY.

La verificacion final (por la rubrica) compara R contra UNA CORRIDA EXPLICITA
equivalente de OpenSees en desplazamiento, reaccion y fuerza interna. Para poder
hacerla se necesitan los CUATRO casos base compatibles (mismo modelo, mismas
unidades) y la corrida 5 con todas las cargas escaladas.

Este modulo NO ejecuta la verificacion estructural (aun no existen EX/EY); deja
preparado el protocolo de 5 corridas y el comando que la realizara, y escribe el
plan en `results/superposicion/comando_verificacion.json`.

Uso (cuando existan los 4 casos base):
    python -X utf8 -m src.superposicion.verificar_explicita \
        --respuesta G path_g --respuesta Q path_q --respuesta EX path_ex \
        --respuesta EY path_ey --explicita path_r_explicito
    (o, sin argumentos, se documenta el plan y se aborta con estado
     BLOQUEADO_POR_PARAMETROS_SISMICOS).

NOTA de estado: la verificacion INTERMEDIA G+Q del Edificio I ya esta verificada
(src/cargas/verificacion_intermedia_G_Q_EI.py, IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO);
este modulo cubre la verificacion COMPLETA de 5 corridas, que permanece bloqueada
por la falta de los casos sismicos EX/EY.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.superposicion.combinacion import (CasosBaseIncompletosError,
                                           leer_config, verificar_contra_opensees)

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
RES_DIR = E3 / "results" / "superposicion"


def _leer_respuesta(path: Path) -> dict:
    """Lee un JSON de caso con familias desplazamiento/reaccion/fuerza_interna."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    sol = d.get("solucion") or d.get("respuesta_combinada") or d
    out = {}
    for f, key in (("desplazamiento", "desplazamientos"),
                   ("reaccion", "reacciones"),
                   ("fuerza_interna", "fuerzas_local_por_elemento")):
        raw = sol.get(key) if isinstance(sol, dict) else None
        if raw is None:
            out[f] = []
        elif isinstance(raw, dict):
            flat = []
            for k in sorted(raw, key=int):
                flat.extend(raw[k])
            out[f] = flat
        else:
            out[f] = list(raw)
    return out


def protocolo_5_corridas(cfg: dict) -> dict:
    lamb = {c: cfg["coeficientes"][c]["demostracion_arbitraria"]
            for c in ("G", "Q", "EX", "EY")}
    return {
        "protocolo": [
            "1. corrida_G   : cargas solo G (peso propio + PM.ADIC), mismo modelo.",
            "2. corrida_Q   : cargas solo Q (q_Q via geometria tributaria), mismo modelo.",
            "3. corrida_EX  : cargas solo EX (sismo +X), mismo modelo.",
            "4. corrida_EY  : cargas solo EY (sismo +Y), mismo modelo.",
            "5. corrida_R_explicito : TODAS las cargas en un solo patron escaladas por "
            "los lambda (1.0, 0.7, 0.3, -0.2) del conjunto de demostracion."],
        "comparacion": [
            "R = lambda_G*R_G + lambda_Q*R_Q + lambda_EX*R_EX + lambda_EY*R_EY versus ",
            "R_explicito (corrida 5), para las familias desplazamiento, reaccion y ",
            "fuerza interna; tolerancia por configurar (ver PREGUNTAS_PROFESOR_MIERCOLES)."],
        "lambda_conjunto_demostracion": lamb,
        "fuerte_condicion": ("Los 4 casos base deben ser compatibles: mismo modelo, "
                             "mismos nodos/elementos/restricciones, mismas unidades, "
                             "sin cambios de rigidez entre casos."),
    }


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    cfg = leer_config()
    plan = protocolo_5_corridas(cfg)
    RES_DIR.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--respuesta", action="append", nargs=2, metavar=("CASO", "PATH"))
    parser.add_argument("--explicita", metavar="PATH")
    try:
        opts, _ = parser.parse_known_args(args)
    except SystemExit:
        opts = None

    estado = "BLOQUEADO_POR_PARAMETROS_SISMICOS"
    if opts and opts.respuesta and opts.explicita:
        respuestas = {}
        for caso, path in opts.respuesta:
            respuestas[caso] = _leer_respuesta(Path(path))
        from src.superposicion.combinacion import check_casos_base, combinar, coeficientes
        check_casos_base(respuestas)
        lamb = coeficientes(cfg, usar_demo=True)
        R = combinar(respuestas, lamb)
        R_ex = _leer_respuesta(Path(opts.explicita))
        comp = verificar_contra_opensees(R["respuesta_combinada"], R_ex)
        estado = comp["estado"]
        plan["resultado_verificacion"] = comp
    else:
        faltan = ([] if opts is None else
                  [f for f in ("G", "Q", "EX", "EY")
                   if not args or f not in [p[0] for p in (opts.respuesta or [])]])
        plan["faltan_casos_base"] = (["EX", "EY"] if estado == "BLOQUEADO_POR_PARAMETROS_SISMICOS"
                                     else faltan)

    plan["estado"] = estado
    out = RES_DIR / "comando_verificacion.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    print(json.dumps({
        "estado": estado,
        "lambda_demostracion": plan["lambda_conjunto_demostracion"],
        "protocolo": plan["protocolo"],
        "comando_preparado": ("python -X utf8 -m src.superposicion.verificar_explicita "
                              "--respuesta G <rG> --respuesta Q <rQ> "
                              "--respuesta EX <rEX> --respuesta EY <rEY> "
                              "--explicita <rR>"),
        "escrito": str(out)}, ensure_ascii=False, indent=2))
    if estado == "BLOQUEADO_POR_PARAMETROS_SISMICOS":
        print("(No se ejecuta la verificacion estructural completa: faltan EX/EY.)")
    return 0 if estado != "BLOQUEADO_POR_PARAMETROS_SISMICOS" else 1


if __name__ == "__main__":
    raise SystemExit(main())