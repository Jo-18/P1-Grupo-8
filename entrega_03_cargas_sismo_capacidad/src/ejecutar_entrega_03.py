"""Ejecutor unico de la Entrega 3: cargas, sismo, superposicion y capacidad RC.

Orden de ejecucion (cada paso = un modulo verificado de la entrega):
  1. casos Q  : caso_Q_EI  y  caso_Q_EII         (q_Q=3.0 kN/m2 NCh1537 Tabla 4)
  2. sismo    : EX/EY para EI y EII              (pseudoestatico de la consigna)
  3. verificacion INTERMEDIA G+Q de ambos edificios (regresion)
  4. superposicion COMPLETA (G,Q,EX,EY,EXPLICITA) por edificio
  5. capacidad RC por edificio: DEMO_RC_EI / DEMO_RC_EII (M-phi, P-M, resumen)
  6. demanda/capacidad (D/C) por edificio con seleccion trazable

Estado por paso: OK (returncode 0) o FALLO. Genera:
  results/ejecutor_entrega_03/estado.json  y  estado.md

Uso:
  python -X utf8 -m src.ejecutar_entrega_03
  (opcional: --solo pasos separados por coma, p.ej. 1,4)
"""

from __future__ import annotations

import io
import json
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
RES = E3 / "results" / "ejecutor_entrega_03"
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"

sys.path.insert(0, str(E3))
sys.path.insert(0, str(EI_SRC))

PASOS = {
    "1": "casos_Q",
    "2": "casos_sismicos_EX_EY",
    "3": "verificacion_intermedia_G_Q",
    "4": "superposicion_completa",
    "5": "capacidad_RC_edificios",
    "6": "demanda_capacidad",
}


def _run(nombre: str, fn, *args, **kwargs) -> dict:
    buf = io.StringIO()
    t0 = time.time()
    try:
        with redirect_stdout(buf):
            rc = fn(*args, **kwargs)
        ok = (rc == 0)
    except BaseException as exc:  # noqa: BLE001 - el ejecutor registra y continua
        ok = False
        buf.write("\nEXCEPCION: %r\n" % exc)
        rc = -1
    dt = round(time.time() - t0, 1)
    return {"paso": nombre, "ok": bool(ok), "returncode": rc,
            "segundos": dt, "salida": buf.getvalue()}


def _paso_flags(args) -> set:
    if "--solo" in args:
        return {x.strip() for x in args[args.index("--solo") + 1].split(",")}
    return set()


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    solo = _paso_flags(args)
    RES.mkdir(parents=True, exist_ok=True)

    from src.cargas import caso_Q_EI, caso_Q_EII
    from src.cargas import caso_sismico
    from src.cargas import verificacion_intermedia_G_Q_EI, \
        verificacion_intermedia_G_Q_EII
    from src.cargas import verificacion_superposicion_completa
    from src.capacidad_rc import demanda_capacidad, edificios

    resultados = {}

    def _hacer(nombre, clave, fn, *a, **k):
        if solo and clave not in solo:
            return
        print(">> paso %s (%s) ..." % (clave, nombre), flush=True)
        key = nombre
        resultados[key] = _run(nombre, fn, *a, **k)
        resultados[key]["paso_clave"] = clave
        estado = "OK" if resultados[key]["ok"] else "FALLO"
        print("   -> %s en %ss" % (estado, resultados[key]["segundos"]),
              flush=True)

    _hacer("casos_Q_EI", "1", caso_Q_EI.main)
    _hacer("casos_Q_EII", "1", caso_Q_EII.main)
    _hacer("sismo_EX_EI", "2", caso_sismico.run_caso, "I", "X")
    _hacer("sismo_EY_EI", "2", caso_sismico.run_caso, "I", "Y")
    _hacer("sismo_EX_EII", "2", caso_sismico.run_caso, "II", "X")
    _hacer("sismo_EY_EII", "2", caso_sismico.run_caso, "II", "Y")
    _hacer("intermedia_G_Q_EI", "3", verificacion_intermedia_G_Q_EI.main)
    _hacer("intermedia_G_Q_EII", "3", verificacion_intermedia_G_Q_EII.main)
    _hacer("superposicion_completa_EI", "4",
           verificacion_superposicion_completa.run, "I")
    _hacer("superposicion_completa_EII", "4",
           verificacion_superposicion_completa.run, "II")
    _hacer("capacidad_RC_edificios", "5", edificios.main)
    _hacer("demanda_capacidad", "6", demanda_capacidad.main)

    vers = {}
    for k, reg in resultados.items():
        paso = PASOS[reg["paso_clave"]]
        vers.setdefault(paso, {"ok": True, "corridas": 0, "nombres": []})
        vers[paso]["ok"] = vers[paso]["ok"] and reg["ok"]
        vers[paso]["corridas"] += 1
        vers[paso]["nombres"].append(k)
    for k in PASOS.values():
        vers.setdefault(k, {"ok": False, "corridas": 0, "no_ejecutado": True})

    ok_total = all(vers[p]["ok"] for p, r in vers.items() if not r.get("no_ejecutado"))
    payload = {"titulo": "Ejecutor unico Entrega 3",
               "estado_global": "OK" if ok_total else "FALLO",
               "pasos": {k: {"ok": v["ok"], "corridas": v["corridas"],
                             "nombres": v.get("nombres", []),
                             "no_ejecutado": v.get("no_ejecutado", False)}
                         for k, v in vers.items()},
               "corridas": {k: {"ok": r["ok"], "returncode": r["returncode"],
                                "segundos": r["segundos"]}
                            for k, r in resultados.items()}}
    jp = RES / "estado.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")

    lineas = ["# Ejecutor unico - Entrega 3", ""]
    for k, v in vers.items():
        lineas.append("- paso %-8s : %s (%d corrida/s)"
                      % (k, "OK" if v["ok"] else "FALLO", v["corridas"]))
    lineas.append("")
    lineas.append("## Estado global: **%s**" % payload["estado_global"])
    md = RES / "estado.md"
    md.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    print(json.dumps({
        "estado_global": payload["estado_global"],
        "pasos": {k: {"ok": v["ok"], "corridas": v["corridas"]} for k, v in vers.items()},
        "escrito_en": [str(jp), str(md)]}, ensure_ascii=False, indent=2))
    return 0 if ok_total else 1


if __name__ == "__main__":
    raise SystemExit(main())