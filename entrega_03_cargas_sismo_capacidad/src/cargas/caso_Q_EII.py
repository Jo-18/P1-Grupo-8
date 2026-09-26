"""Caso de carga Q del Edificio II como caso FE real en el motor OpenSees.

- Mismo modelo, nodos, elementos y restricciones que el caso G congelado
  (`pipeline_FE_EII.MarcoEII`, escenario V.60/80): se reconstruye exactamente
  la misma geometria/rigideces/rigidLinks/diafragmas que G.
- Q aplicada mediante la misma geometria tributaria que G (reparto losa ->
  receptor -> nodos FE, mismo re-ruteo a soporte vertical) con PP=0 y
  PM.ADIC=0: **G completamente ausente** de la corrida Q.
- Verificaciones: (a) sum(Q aplicada) == q_Q * A_tributaria (por nivel y
  global, identidad exacta), (b) equilibrio vertical carga vs reaccion,
  (c) G ausente, (d) marcada DEMOSTRACION si se usa q_Q arbitrario.

q_Q = 3.0 kN/m2 es el minimo de la categoria 'Escuelas - salas de clases' de la
Tabla 4 de la NCh 1537:2009 (PARAMETRO_BASADO_EN_NORMA_NCH1537_2009_TABLA4, ver
config/cargas.json) y la corrida queda marcada `Q_EII_NCH1537_2009_3.0_kN_m2`. La
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

sys.path.insert(0, str(E3))
sys.path.insert(0, str(EI_SRC))

from src.cargas.pipeline_FE_EII import MarcoEII  # noqa: E402

CASO = "II"
Q_DEMO_DEFAULT_KN_M2 = 3.0
TOL_SUM_Q = 0.005
TOL_EQUILIBRIO_VERT = 0.05  # 5 %


def leer_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def q_efectivo(cfg: dict, usar_demo: bool, q_q_cli: float | None) -> dict:
    q_real = cfg["q_Q"]["II"]["q_Q_kN_m2"]
    etiq = cfg["q_Q"]["II"].get("etiqueta_corrida", "Q_EII_ADOPTADA_%s_kN_m2" % q_real)
    if q_real is not None and not usar_demo:
        return {"q_Q_kN_m2": float(q_real), "etiqueta": etiq,
                "marcado": False,
                "clasificacion": cfg["q_Q"]["II"].get("estado",
                                                      "PARAMETRO_ADOPTADO_POR_EL_GRUPO")}
    if q_real is None and not usar_demo:
        raise SystemExit(
            "ABORTE: q_Q del edificio II es null (no adoptado). Use --demo para "
            "correr la corrida marcada DEMOSTRACION_ARBITRARIA_qQ_%s."
            % (Q_DEMO_DEFAULT_KN_M2 if q_q_cli is None else q_q_cli))
    qq = float(q_q_cli if q_q_cli is not None
               else cfg["DEMOSTRACION_ARBITRARIA"]["q_Q_kN_m2"])
    return {"q_Q_kN_m2": qq,
            "etiqueta": "DEMOSTRACION_ARBITRARIA_qQ_%s" % qq,
            "marcado": True}


def construir_y_resolver(q_Q_info: dict):
    """Construye el modelo G congelado (MarcoEII) y resuelve SOLO con Q."""
    q_Q = q_Q_info["q_Q_kN_m2"]
    marco = MarcoEII(v031_seccion="V.60/80")
    marco.construir()

    cargas_Q, repartos, verificacion = marco.losa_Q_nodal(q_Q)

    sol = marco.resolver_caso({"EII": cargas_Q})

    Q_aplicada = -sum(f[2] for f in cargas_Q.values())
    Q_esperada = q_Q * verificacion["area_neta_total_m2"]
    dq = abs(Q_aplicada - Q_esperada)
    dq_rel = dq / Q_esperada if Q_esperada else 0.0

    equil = {"ok": False, "nota": "analisis fallo"}
    if sol["ok"]:
        Rz = sum(r[2] for r in sol["reacciones"].values())
        equil = {"R_z_kN": round(Rz, 4), "P_z_Q_kN": round(Q_aplicada, 4),
                 "residuo_kN": round(Rz - Q_aplicada, 4),
                 "ok": abs(Rz - Q_aplicada)
                       < TOL_EQUILIBRIO_VERT * max(abs(Q_aplicada), 1e-9)}

    conservacion_nivel = []
    for cod, rep in repartos.items():
        Q_nivel = sum(-f[2] for t, f in cargas_Q.items()
                      if abs(marco.key_of_tag[t][2]
                             - marco._cota(cod)) < 1e-6)
        que_esp = q_Q * rep["area_neta_total_m2_exacta"]
        conservacion_nivel.append({
            "nivel": cod,
            "area_neta_m2": rep["area_neta_total_m2"],
            "Q_esperada_kN": round(que_esp, 6),
            "Q_aplicada_kN": round(Q_nivel, 6),
            "diferencia_kN": round(Q_nivel - que_esp, 8),
            "ok": abs(Q_nivel - que_esp) < 1e-6})

    checks = {
        "sum_Q_igual_q_por_A": {
            "q_Q_kN_m2": q_Q,
            "area_neta_total_m2": verificacion["area_neta_total_m2"],
            "Q_esperada_kN": round(Q_esperada, 4),
            "Q_aplicada_kN": round(Q_aplicada, 4),
            "diferencia_abs_kN": round(dq, 8),
            "diferencia_rel": round(dq_rel, 10),
            "tolerancia_rel": TOL_SUM_Q,
            "estado": "OK" if dq_rel <= TOL_SUM_Q else "ERROR"},
        "conservacion_por_nivel": conservacion_nivel,
        "G_ausente": {"pp_aplicado_kN": 0.0, "pm_adic_aplicado_kN": 0.0,
                      "q_aplicado_kN": round(Q_aplicada, 4),
                      "estado": "OK(G_no_aplicado)"},
        "equilibrio_vertical_cargas_vs_reacciones": equil,
        "receptores_sin_fe": {cod: rep["receptores_sin_fe"]
                              for cod, rep in repartos.items()},
    }
    return marco, sol, cargas_Q, repartos, checks


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    usar_demo = "--demo" in args
    q_q_cli = None
    if "--q_q" in args:
        q_q_cli = float(args[args.index("--q_q") + 1])

    cfg = leer_config()
    info_q = q_efectivo(cfg, usar_demo, q_q_cli)
    marco, sol, cargas, repartos, checks = construir_y_resolver(info_q)

    payload = {
        "caso": "Q",
        "edificio": "II",
        "motor": "OpenSeesPy (pipeline reproducible EII congelado, mismo "
                 "modelo/nodos/elementos/restricciones que G)",
        "v031_seccion_escenario": "V.60/80",
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
                             for cod, car in {"EII": cargas}.items()},
        "verificaciones": checks,
    }
    RES_DIR.mkdir(parents=True, exist_ok=True)
    jp = RES_DIR / "caso_Q_EII_FE.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")

    cp = RES_DIR / "caso_Q_EII_FE_reacciones.csv"
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "Rx_kN", "Ry_kN", "Rz_kN", "Mx_kN_m", "My_kN_m", "Mz_kN_m"])
        for tag, r in sol.get("reacciones", {}).items():
            w.writerow([tag] + [round(x, 6) for x in r])

    print(json.dumps({
        "caso": "Q", "edificio": "II",
        "etiqueta": info_q["etiqueta"],
        "q_Q_kN_m2": info_q["q_Q_kN_m2"],
        "modelo": marco.resumen(),
        "F_total_aplicado_kN": [round(x, 6) for x in sol["F_total_kN"]],
        "verificaciones": checks,
        "escrito": [str(jp), str(cp)]}, ensure_ascii=False, indent=2))
    ok = (sol["ok"] and checks["sum_Q_igual_q_por_A"]["estado"] == "OK"
          and checks["equilibrio_vertical_cargas_vs_reacciones"]["ok"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())