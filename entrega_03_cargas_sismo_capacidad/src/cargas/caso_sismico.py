"""Casos sismicos pseudoestaticos EX/EY para Edificio I y Edificio II (Entrega 3).

Metodologia (consigna del profesor, clasificacion PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA):
  Wi  = PPi + fraccion_Q * Qi     (peso sismico por piso; fraccion_Q = 0.50)
  mi  = Wi / g
  Fi  = a * mi = coef_a * Wi      (coef_a = 0.20)
  fn  = Fi * wn / Wi              (distribucion proporcional al peso tributario del nodo)

Paso a paso para cada (edificio, direccion):
  1. Construir el modelo FE congelado (igual que el caso G).
  2. Ensamblar cargas G y Q (igual que los casos G y Q) y, con ellas, el peso
     tributario por nodo (wn = |Gz| + fraccion_Q*|Qz|).
  3. Calcular CM por nivel (pesos distribuidos, NO centro geometrico) y Fi.
  4. Generar las fuerzas nodales horizontales (solo X para EX, solo Y para EY).
  5. Reconstruir el modelo limpio y resolverlo SOLO con las fuerzas sismicas
     (sin cargas gravitacionales dentro del caso sismico independiente).
  6. Verificar: sum fn = Fi por nivel; resultante en CM; momento accidental ~ 0;
     direccion exclusiva; corte basal = sum F; equilibrio horizontal de reacciones;
     sentido de la deformada; retcode.

No hay union estructural entre EI y EII. No se calibra el PP pendiente (muros EII):
queda visible pero NO se suma al peso sismico.

Salidas (results/cargas/):
  caso_sismico_{EX|EY}_EI.json / .csv
  caso_sismico_{EX|EY}_EII.json / .csv

Uso:
  python -X utf8 -m src.cargas.caso_sismico --edificio I --direccion X
  python -X utf8 -m src.cargas.caso_sismico --edificio II --direccion Y
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
CONFIG_CARGAS = E3 / "config" / "cargas.json"
CONFIG_SISMO = E3 / "config" / "sismo.json"
RES_DIR = E3 / "results" / "cargas"
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"

sys.path.insert(0, str(E3))
sys.path.insert(0, str(EI_SRC))

from src.cargas.peso_sismico import (  # noqa: E402
    generar_cargas_sismicas_directas, leer_config_sismo)

TOL_CORTE_BASAL = 0.01
TOL_MOM_ACC = 1e-6


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _marco_EI():
    from analisis.fe import geometria_fe as GF
    from analisis.fe.marco import Marco
    niveles = GF.cargar_todos()
    marco = Marco(niveles, rigidez_mult=1.0e3)
    marco.subdivision_vigas = 1
    marco.construir()
    return marco


def _cargas_G_EI(marco):
    from analisis.fe import cargas_correlacionadas as CC
    from analisis.fe import tributaria as TB
    from analisis.fe.hipotesis import niveles_ordenados
    por_nivel = CC.cargas_por_losa_por_nivel()
    cargas = {}
    for cod in niveles_ordenados():
        nivelFE = marco.niveles[cod]
        cargas_por_losa = {}
        for lo in nivelFE.losas:
            info = por_nivel.get(cod, {}).get(lo["id"], {})
            cargas_por_losa[lo["id"]] = (info.get("pm_kn_m2", 0.0),
                                         info.get("sc_kn_m2", 0.0))
        cn, _rp = TB.calcular_cargas_nodales(nivelFE, marco.receptor_nodos,
                                             cargas_por_losa, marco.key_of_tag,
                                             incluir_sc=False)
        cargas[cod] = cn
    return cargas


def _cargas_Q_EI(marco, q_Q):
    from analisis.fe import geometria_fe as GF
    from analisis.fe import tributaria as TB
    from analisis.fe.hipotesis import niveles_ordenados
    cargas = {}
    for cod in niveles_ordenados():
        nivelFE = marco.niveles[cod]
        soportes = TB._receptor_lineas(nivelFE)
        c = {}
        for lo in nivelFE.losas:
            s = GF.construir_superficies([lo])[0]
            neto = s["neto"].area
            if neto <= 0:
                continue
            validos = (set(soportes.keys()) if not lo.get("apoyos")
                       else set(lo["apoyos"]))
            areas, _ = TB.distribuir_losa(
                s["neto"], {k: v for k, v in soportes.items() if k in validos})
            suma = sum(areas.values())
            for rid, area in areas.items():
                frac = area / suma if suma > 0 else 0.0
                F = frac * q_Q * neto
                nodos = marco.receptor_nodos.get(rid, [])
                if not nodos:
                    continue
                pesos = TB._pesos_por_nodo(marco.key_of_tag, nodos)
                for tag, w in pesos.items():
                    cur = c.get(tag, [0.0] * 6)
                    cur[2] -= F * w
                    c[tag] = cur
        cargas[cod] = c
    return cargas


def _marco_EII():
    from src.cargas.pipeline_FE_EII import MarcoEII
    marco = MarcoEII(v031_seccion="V.60/80")
    marco.construir()
    return marco


def _cargas_G_EII(marco):
    pp = marco.peso_propio_nodal()
    losa, _ = marco.losa_tributaria_nodal(incluir_sc=False)
    cargas = {}
    for agg in (pp, losa):
        for tag, f in agg.items():
            cur = cargas.setdefault(int(tag), [0.0] * 6)
            for i in range(6):
                cur[i] += f[i]
    return cargas


def _cargas_Q_EII(marco, q_Q):
    cargas, _rep, _ver = marco.losa_Q_nodal(q_Q)
    return cargas


def _flat_por_nivel(cargas_por_nivel):
    flat = {}
    for car in cargas_por_nivel.values():
        for t, f in car.items():
            flat.setdefault(int(t), [0.0] * 6)
            for i in range(6):
                flat[int(t)][i] += f[i]
    return flat


def _marcos_y_cargas(edificio, q_Q):
    """Construye el modelo, ensambla G y Q (flat) y las cotas de nivel."""
    if edificio == "I":
        marco = _marco_EI()
        G = _cargas_G_EI(marco)
        Q = _cargas_Q_EI(marco, q_Q)
        G_flat = _flat_por_nivel(G)
        Q_flat = _flat_por_nivel(Q)
        # cota de nivel = z minimo de los nodos cargados en ese nivel
        cotas = {}
        for cod, car in G.items():
            if not car:
                continue
            zs = [marco.key_of_tag[int(t)][2] for t in car]
            cotas[cod] = min(zs)
        return marco, G_flat, Q_flat, cotas
    else:
        marco = _marco_EII()
        G_flat = _cargas_G_EII(marco)
        Q_flat = _cargas_Q_EII(marco, q_Q)
        cotas = {cod: float(zc) for cod, zc in marco.modelo["cota_nivel"].items()}
        return marco, G_flat, Q_flat, cotas


def _agrupar_por_nivel(flat, key_of_tag, cotas):
    por_nivel = {}
    for t, f in flat.items():
        z = key_of_tag[t][2]
        cod = None
        for c, zc in cotas.items():
            if abs(z - zc) < 0.05:
                cod = c
                break
        if cod is None:
            cod = "NIVEL_?"
        por_nivel.setdefault(cod, {})[int(t)] = f
    return por_nivel


# --------------------------------------------------------------------------- #
# Verificaciones
# --------------------------------------------------------------------------- #
def _verificaciones(marco, sol, sismo_res, direccion, cotas, edificio):
    ledger = sismo_res["ledger_por_nivel"]
    cargas_sismo = sismo_res["cargas_nodales"]
    verif_sismo = sismo_res["verificaciones"]
    idx = 0 if direccion == "X" else 1
    otro = 1 if direccion == "X" else 0

    # 1) sum fn = Fi por nivel
    por_nivel = _agrupar_por_nivel(cargas_sismo, marco.key_of_tag, cotas)
    corte_basal = 0.0
    sum_check = []
    for fl in ledger:
        z = fl["z_m"]
        fi = fl["F_lateral_kN"]
        corte_basal += fi
        f_aplic = 0.0
        for cod, car in por_nivel.items():
            fc = cotas.get(cod)
            if fc is None or abs(fc - z) > 0.05:
                continue
            for f in car.values():
                f_aplic += f[idx]
        sum_check.append({"z_m": z, "F_esperada_kN": round(fi, 6),
                          "F_aplicada_kN": round(f_aplic, 6),
                          "ok": abs(f_aplic - fi) < 1e-6 * max(abs(fi), 1e-9)})

    check_corte = {
        "sum_F_por_nivel_kN": round(corte_basal, 6),
        "corte_basal_kN": round(verif_sismo["F_total_aplicada_kN"], 6),
        "ok": abs(corte_basal - verif_sismo["F_total_aplicada_kN"])
              < TOL_CORTE_BASAL * max(abs(corte_basal), 1e-9)}

    check_mom = {
        "momento_accidental_total_kN_m": verif_sismo["momento_accidental_total_kN_m"],
        "ok": abs(verif_sismo["momento_accidental_total_kN_m"]) < TOL_MOM_ACC}

    max_otro = max((abs(f[otro]) for f in cargas_sismo.values()), default=0.0)
    check_dir = {"direccion": direccion,
                 "max_componente_opuesta_kN": round(max_otro, 12),
                 "ok": max_otro < 1e-9}

    max_z = max((abs(f[2]) for f in cargas_sismo.values()), default=0.0)
    check_grav = {"max_carga_vertical_kN": round(max_z, 12), "ok": max_z < 1e-9}

    equil = {"ok": False}
    if sol["ok"]:
        Rx = sum(r[0] for r in sol["reacciones"].values())
        Ry = sum(r[1] for r in sol["reacciones"].values())
        Fx = verif_sismo["F_total_aplicada_kN"] if direccion == "X" else 0.0
        Fy = verif_sismo["F_total_aplicada_kN"] if direccion == "Y" else 0.0
        err_x = abs(Rx + Fx)
        err_y = abs(Ry + Fy)
        equil = {"Rx_kN": round(Rx, 4), "Ry_kN": round(Ry, 4),
                 "F_x_kN": round(Fx, 4), "F_y_kN": round(Fy, 4),
                 "residuo_x_kN": round(err_x, 8),
                 "residuo_y_kN": round(err_y, 8),
                 "ok": err_x < 1e-4 and err_y < 1e-4}

    sentido = {"estado": "N/D"}
    if sol["ok"]:
        prod_pos = 0.0
        prod_neg = 0.0
        n_neg = 0
        for t, f in cargas_sismo.items():
            v = sol["desplazamientos"].get(int(t), [0.0] * 6)
            p = f[idx] * v[idx]
            if p > 0:
                prod_pos += p
            elif p < 0:
                prod_neg += p
                n_neg += 1
        # signo dominante: nodo con max |u_idx|
        maxu = max(((v[idx], t) for t, v in sol["desplazamientos"].items()),
                   default=(0.0, None))
        sentido_dominante = 1 if maxu[0] > 0 else (-1 if maxu[0] < 0 else 0)
        opuesto = maxu[0] * (1 if direccion == "X" else 1) < 0 and maxu[0] != 0
        proporcion_neg = (abs(prod_neg) / prod_pos
                          if prod_pos > 1e-12 else 1.0)
        estado = "OK"
        observaciones = []
        if opuesto:
            estado = "ERROR(SENTIDO_INVERSO)"
            observaciones.append("El desplazamiento dominante es opuesto a la fuerza")
        if n_neg > 0:
            observaciones.append(
                "%d nodo(s) cargado(s) con producto f*u local opuesto (%.2e de %.2e, "
                "fraccion=%.4f); dominio global positivo" % (
                    n_neg, prod_neg, prod_pos, proporcion_neg))
        sentido = {
            "n_productos": len(cargas_sismo),
            "sum_fd_positivos_kN_m": round(prod_pos, 10),
            "sum_fd_negativos_kN_m": round(prod_neg, 10),
            "n_opuestos": n_neg,
            "nodo_max_u": maxu[1],
            "ux_max_m": round(maxu[0], 10),
            "proporcion_opuesta": round(proporcion_neg, 6),
            "estado": estado,
            "notas": observaciones}

    deriva = {"estado": "N/D"}
    if sol["ok"]:
        # desplazamiento maximo por nivel
        por_nivel_disp = {}
        for t, v in sol["desplazamientos"].items():
            z = marco.key_of_tag[int(t)][2]
            cod = None
            for c, zc in cotas.items():
                if abs(z - zc) < 0.05:
                    cod = c
                    break
            if cod is None:
                cod = "?"
            por_nivel_disp.setdefault(cod, []).append(abs(v[idx]))
        despl_max = {c: max(l) for c, l in por_nivel_disp.items() if l}
        niveles = [c for c in cotas.keys()]
        filas = []
        prev_val = None
        prev_z = None
        for c in niveles:
            z = cotas[c]
            val = despl_max.get(c, 0.0)
            if prev_val is not None and abs(z - prev_z) > 1e-6:
                derr = (val - prev_val) / (z - prev_z)
                filas.append({"nivel": c, "desp_max_m": round(val, 8),
                              "deriva": round(abs(derr), 8)})
            prev_val, prev_z = val, z
        deriva = {"desplazamiento_maximo_por_nivel": despl_max,
                  "deriva_por_piso": filas}

    return {
        "sum_por_nivel": sum_check,
        "corte_basal": check_corte,
        "momento_accidental": check_mom,
        "direccion_exclusiva": check_dir,
        "gravitatorias_ausentes": check_grav,
        "equilibrio_horizontal": equil,
        "sentido_deformada": sentido,
        "deriva": deriva,
        "retcode": sol.get("analyze_retcode"),
        "sol_ok": bool(sol["ok"]),
    }


def run_caso(edificio: str, direccion: str) -> int:
    if edificio not in ("I", "II"):
        raise SystemExit("edificio debe ser 'I' o 'II'")
    if direccion not in ("X", "Y"):
        raise SystemExit("direccion debe ser 'X' o 'Y'")

    cfg_cargas = json.loads(CONFIG_CARGAS.read_text(encoding="utf-8"))
    cfg_sismo = leer_config_sismo()
    q_Q = float(cfg_cargas["q_Q"][edificio]["q_Q_kN_m2"])
    etiq_q = cfg_cargas["q_Q"][edificio].get("etiqueta_corrida",
                                             "Q_%s_NCH1537_2009_3.0_kN_m2" % edificio)

    # Construir modelo una vez para ensamblar cargas y pesos
    marco, G_flat, Q_flat, cotas = _marcos_y_cargas(edificio, q_Q)

    # Peso sismico + fuerzas (usando key_of_tag/coords del primer marco)
    sismo_res = generar_cargas_sismicas_directas(G_flat, Q_flat,
                                                 marco.key_of_tag,
                                                 direccion, cfg_sismo)

    # Reconstruir modelo limpio y resolver SOLO con las cargas sismicas
    if edificio == "I":
        from analisis.fe import resolver as RES
        marco2 = _marco_EI()
        cargas_single = _agrupar_por_nivel(sismo_res["cargas_nodales"],
                                           marco2.key_of_tag, cotas)
        sol = RES.resolver(marco2, cargas_single)
        marco_final = marco2
    else:
        marco2 = _marco_EII()
        cargas_single = _agrupar_por_nivel(sismo_res["cargas_nodales"],
                                           marco2.key_of_tag, cotas)
        sol = marco2.resolver_caso(cargas_single)
        marco_final = marco2

    checks = _verificaciones(marco_final, sol, sismo_res, direccion, cotas,
                             edificio)

    caso = "EX" if direccion == "X" else "EY"
    etiq = "%s_%s" % (caso, edificio)

    payload = {
        "caso": caso,
        "edificio": edificio,
        "direccion": direccion,
        "etiqueta": etiq,
        "clasificacion": sismo_res["clasificacion"],
        "metodo": "pseudoestatico: Wi=PPi+0.5Qi; mi=Wi/g; Fi=0.20*Wi",
        "q_Q_kN_m2": q_Q,
        "etiqueta_q_Q": etiq_q,
        "modelo": marco_final.resumen() if hasattr(marco_final, "resumen") else None,
        "peso_sismico": {
            "ledger_por_nivel": [
                {k: (round(v, 6) if isinstance(v, float) else v)
                 for k, v in fl.items()} for fl in sismo_res["ledger_por_nivel"]],
            "resumen": sismo_res["verificaciones"]},
        "cargas_nodales_sismicas": {
            str(k): [round(x, 6) for x in v]
            for k, v in sismo_res["cargas_nodales"].items()},
        "solucion": {
            "ok": sol["ok"],
            "analyze_retcode": sol.get("analyze_retcode"),
            "desplazamientos": {str(k): [round(x, 8) for x in v]
                                for k, v in sol.get("desplazamientos", {}).items()},
            "reacciones": {str(k): [round(x, 6) for x in v]
                           for k, v in sol.get("reacciones", {}).items()},
            "fuerzas_local_por_elemento": {str(k): [round(x, 6) for x in v]
                                           for k, v in sol.get("fuerzas", {}).get("local", {}).items()}},
        "verificaciones": checks,
    }

    RES_DIR.mkdir(parents=True, exist_ok=True)
    jp = RES_DIR / ("caso_sismico_%s_%s.json" % (caso, edificio))
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")

    cp = RES_DIR / ("caso_sismico_%s_%s_reacciones.csv" % (caso, edificio))
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "Rx_kN", "Ry_kN", "Rz_kN", "Mx_kN_m", "My_kN_m", "Mz_kN_m"])
        for tag, r in sol.get("reacciones", {}).items():
            w.writerow([tag] + [round(x, 6) for x in r])

    print(json.dumps({
        "caso": caso, "edificio": edificio, "etiqueta": etiq, "direccion": direccion,
        "F_total_sismica_kN": sismo_res["verificaciones"]["F_total_aplicada_kN"],
        "W_total_sismico_kN": sismo_res["verificaciones"]["W_total_sismico_kN"],
        "coeficiente_a": sismo_res["verificaciones"]["coeficiente_a"],
        "momento_accidental_kN_m":
            sismo_res["verificaciones"]["momento_accidental_total_kN_m"],
        "sol_ok": bool(sol["ok"]),
        "retcode": sol.get("analyze_retcode"),
        "verificaciones": {
            "corte_basal": checks["corte_basal"],
            "equilibrio_horizontal": checks["equilibrio_horizontal"],
            "momento_accidental": checks["momento_accidental"],
            "direccion_exclusiva": checks["direccion_exclusiva"],
            "sentido_deformada": checks["sentido_deformada"],
            "sol_ok": checks["sol_ok"]},
        "escrito": [str(jp), str(cp)]}, ensure_ascii=False, indent=2))
    ok = (sol["ok"] and checks["corte_basal"]["ok"]
          and checks["equilibrio_horizontal"]["ok"]
          and checks["momento_accidental"]["ok"]
          and checks["direccion_exclusiva"]["ok"])
    return 0 if ok else 1


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    edificio = "I"
    direccion = "X"
    if "--edificio" in args:
        edificio = args[args.index("--edificio") + 1]
    if "--direccion" in args:
        direccion = args[args.index("--direccion") + 1]
    return run_caso(edificio, direccion)


if __name__ == "__main__":
    raise SystemExit(main())
