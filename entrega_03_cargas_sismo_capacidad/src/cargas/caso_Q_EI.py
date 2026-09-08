"""Caso de carga Q del Edificio I como caso FE real en el motor OpenSees existente.

- Mismo modelo, nodos, elementos y restricciones que el caso G (se reconstruye el
  mismo `Marco` con la misma configuracion de `analisis_estructural/edificio_I`).
- Q aplicada mediante la geometria tributaria de Semana 2 (reparto losa -> receptor
  -> nodos FE) con PP=0 y PM.ADIC=0: **G completamente ausente** de la corrida Q.
- Resultados separados para desplazamientos, reacciones y fuerzas internas
  (local y global por elemento).
- Verificaciones: (a) sum(Q aplicada) == q_Q * A_tributaria, (b) equilibrio
  vertical carga aplicada vs reaccion vertical, (c) identificacion del q_Q.

q_Q fue adoptado por el grupo en 2.0 kN/m2 (PARAMETRO_ADOPTADO_POR_EL_GRUPO, ver
config/cargas.json) y la corrida queda marcada `Q_EI_ADOPTADA_2.0_kN_m2`. La
bandera --demo sigue disponible para forzar un valor arbitrario de respaldo.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
CONFIG = E3 / "config" / "cargas.json"
RES_DIR = E3 / "results" / "cargas"
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"

sys.path.insert(0, str(EI_SRC))

from analisis.fe import geometria_fe as GF          # noqa: E402
from analisis.fe import resolver as RES             # noqa: E402
from analisis.fe import tributaria as TB            # noqa: E402
from analisis.fe.hipotesis import niveles_ordenados  # noqa: E402
from analisis.fe.marco import Marco                 # noqa: E402

CASO = "I"
Q_DEMO_DEFAULT_KN_M2 = 2.0
TOL_SUM_Q = 0.005
TOL_EQUILIBRIO_VERT = 0.05  # 5 %


def leer_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def q_efectivo(cfg: dict, usar_demo: bool, q_q_cli: float | None) -> dict:
    q_real = cfg["q_Q"]["I"]["q_Q_kN_m2"]
    etiq = cfg["q_Q"]["I"].get("etiqueta_corrida", "Q_EI_ADOPTADA_%s_kN_m2" % q_real)
    if q_real is not None and not usar_demo:
        return {"q_Q_kN_m2": float(q_real), "etiqueta": etiq,
                "marcado": False,
                "clasificacion": cfg["q_Q"]["I"].get("estado",
                                                     "PARAMETRO_ADOPTADO_POR_EL_GRUPO")}
    if q_real is None and not usar_demo:
        raise SystemExit(
            "ABORTE: q_Q del edificio I es null (no adoptado). Use --demo para "
            "correr la corrida marcada DEMOSTRACION_ARBITRARIA_qQ_%s."
            % (Q_DEMO_DEFAULT_KN_M2 if q_q_cli is None else q_q_cli))
    # --demo: fuerza el valor arbitrario (respaldo) explicitamente marcado
    qq = float(q_q_cli if q_q_cli is not None
               else cfg["DEMOSTRACION_ARBITRARIA"]["q_Q_kN_m2"])
    return {"q_Q_kN_m2": qq,
            "etiqueta": "DEMOSTRACION_ARBITRARIA_qQ_%s" % qq,
            "marcado": True}


def construir_y_resolver(q_Q_info: dict):
    """Construye el modelo G identico (Marco) y resuelve SOLO con cargas Q."""
    q_Q = q_Q_info["q_Q_kN_m2"]
    niveles = GF.cargar_todos()
    marco = Marco(niveles, rigidez_mult=1.0e3)
    marco.subdivision_vigas = 1
    marco.construir()

    cargas_nodales = {}
    repartos = {}
    area_net_total = 0.0
    for cod in niveles_ordenados():
        nivelFE = niveles[cod]
        soportes = TB._receptor_lineas(nivelFE)
        cargas = {}
        rep = {"por_losa": {}, "receptores_sin_fe": [], "area_neta_total_m2": 0.0}
        for lo in nivelFE.losas:
            s = GF.construir_superficies([lo])[0]
            neto = s["neto"].area
            rep["area_neta_total_m2"] += neto
            validos = (set(soportes.keys()) if not lo.get("apoyos")
                       else set(lo["apoyos"]))
            areas, _ = TB.distribuir_losa(
                s["neto"], {k: v for k, v in soportes.items() if k in validos})
            suma_area = sum(areas.values())
            info = {"area_neta_m2": round(neto, 4),
                    "area_asignada_receptores_m2": round(suma_area, 4),
                    "Q_total_kN": round(q_Q * neto, 4), "receptores": {}}
            for rid, area in areas.items():
                frac = area / suma_area if suma_area > 0 else 0.0
                F = frac * q_Q * neto
                nodos = marco.receptor_nodos.get(rid, [])
                if not nodos:
                    rep["receptores_sin_fe"].append(
                        {"receptor": rid, "losa": lo["id"], "area_m2": round(area, 4),
                         "Q_kN": round(F, 4)})
                    continue
                info["receptores"][rid] = {
                    "area_m2": round(area, 4), "Q_kN": round(F, 4),
                    "n_nodos_fe": len(nodos)}
                pesos = TB._pesos_por_nodo(marco.key_of_tag, nodos)
                for tag, w in pesos.items():
                    cur = cargas.get(tag, [0.0] * 6)
                    cur[2] -= F * w
                    cargas[tag] = cur
            rep["por_losa"][lo["id"]] = info
        cargas_nodales[cod] = cargas
        repartos[cod] = rep
        area_net_total += rep["area_neta_total_m2"]

    sol = RES.resolver(marco, cargas_nodales)

    # verificaciones
    Q_aplicada = -sum(f[2] for c in cargas_nodales.values() for f in c.values())
    Q_esperada = q_Q * area_net_total
    dq = abs(Q_aplicada - Q_esperada)
    dq_rel = dq / Q_esperada if Q_esperada else 0.0
    # referencia externa (por_viga.json) del flujo Q manual
    ref_manual = None
    man = E3 / "results" / "cargas" / "carga_viva_Q_resumen.json"
    if man.exists():
        try:
            ref_manual = json.loads(man.read_text(encoding="utf-8"))["edificios"]["I"]["global"]
        except Exception:
            ref_manual = None

    equil = {"ok": False, "nota": "analisis fallo"}
    if sol["ok"]:
        Rz = sum(r[2] for r in sol["reacciones"].values())
        equil = {"R_z_kN": round(Rz, 4), "P_z_Q_kN": round(Q_aplicada, 4),
                 "residuo_kN": round(Rz - Q_aplicada, 4),
                 "ok": abs(Rz - Q_aplicada) < TOL_EQUILIBRIO_VERT * max(abs(Q_aplicada), 1e-9)}

    checks = {
        "sum_Q_igual_q_por_A": {
            "q_Q_kN_m2": q_Q, "area_neta_total_m2": round(area_net_total, 4),
            "Q_esperada_kN": round(Q_esperada, 4),
            "Q_aplicada_kN": round(Q_aplicada, 4),
            "diferencia_abs_kN": round(dq, 4),
            "diferencia_rel": round(dq_rel, 8),
            "tolerancia_rel": TOL_SUM_Q,
            "estado": "OK" if dq_rel <= TOL_SUM_Q else "ERROR"},
        "G_ausente": {"pp_aplicado_kN": 0.0, "pm_adic_aplicado_kN": 0.0,
                      "q_aplicado_kN": round(Q_aplicada, 4),
                      "estado": "OK(solo_sc)"},
        "equilibrio_vertical_cargas_vs_reacciones": equil,
        "referencia_global_flujo_manual_Q": ref_manual,
        "receptores_sin_fe": {cod: rep["receptores_sin_fe"] for cod, rep in repartos.items()},
    }
    return marco, sol, cargas_nodales, repartos, checks


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    usar_demo = "--demo" in args
    q_q_cli = None
    if "--q_q" in args:
        q_q_cli = float(args[args.index("--q_q") + 1])

    cfg = leer_config()
    info_q = q_efectivo(cfg, usar_demo, q_q_cli)
    marco, sol, cargas_nodales, repartos, checks = construir_y_resolver(info_q)

    payload = {
        "caso": "Q",
        "edificio": "I",
        "motor": "OpenSeesPy (mismo modelo/nodos/elementos/restricciones que G)",
        "q_Q": info_q,
        "etiqueta_corrida": info_q["etiqueta"],
        "modelo": marco.resumen(),
        "n_nodos_cargados": sol["n_nodos_cargados"],
        "F_total_aplicado_kN": [round(x, 6) for x in sol["F_total_kN"]],
        "solucion": {
            "ok": sol["ok"],
            "analyze_retcode": sol.get("analyze_retcode"),
            "n_reacciones": sol.get("n_reacciones"),
            "desplazamientos": {str(k): [round(x, 8) for x in v]
                                for k, v in sol.get("desplazamientos", {}).items()},
            "reacciones": {str(k): [round(x, 6) for x in v]
                           for k, v in sol.get("reacciones", {}).items()},
            "fuerzas_local_por_elemento": {str(k): [round(x, 6) for x in v]
                                           for k, v in sol.get("fuerzas", {}).get("local", {}).items()},
            "fuerzas_global_por_elemento": {str(k): [round(x, 6) for x in v]
                                            for k, v in sol.get("fuerzas", {}).get("global", {}).items()},
        },
        "cargas_nodales_Q": {cod: {str(k): [round(x, 6) for x in v]
                                   for k, v in car.items()}
                             for cod, car in cargas_nodales.items()},
        "verificaciones": checks,
    }
    RES_DIR.mkdir(parents=True, exist_ok=True)
    jp = RES_DIR / "caso_Q_EI_FE.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")

    # CSV de reacciones
    cp = RES_DIR / "caso_Q_EI_FE_reacciones.csv"
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "Rx_kN", "Ry_kN", "Rz_kN", "Mx_kN_m", "My_kN_m", "Mz_kN_m"])
        for tag, r in sol.get("reacciones", {}).items():
            w.writerow([tag] + [round(x, 6) for x in r])

    print(json.dumps({
        "caso": "Q", "edificio": "I",
        "etiqueta": info_q["etiqueta"],
        "q_Q_kN_m2": info_q["q_Q_kN_m2"],
        "modelo_nodos": marco.resumen(),
        "F_total_aplicado_kN": [round(x, 6) for x in sol["F_total_kN"]],
        "verificaciones": checks,
        "escrito": [str(jp), str(cp)]}, ensure_ascii=False, indent=2))
    ok = (sol["ok"] and checks["sum_Q_igual_q_por_A"]["estado"] == "OK"
          and checks["equilibrio_vertical_cargas_vs_reacciones"]["ok"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())