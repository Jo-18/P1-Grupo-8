"""Primera ejecucion gravitacional completa del Edificio I (laboratorio semana 2).

Flujo: geometria real (candidatos, comun) -> marco 3D OpenSeesPy -> areas
tributarias -> cargas gravitacionales -> solucion estatica lineal -> verificaciones
independientes -> (exportacion Unity en exportar_unity.py).

Norma (directiva del usuario):
  - Exito SOLO si analyze()==0. Si falla, se conserva el diagnostico y NO se
    publican desplazamientos/reacciones/esfuerzos como solucion valida.
  - Verificaciones independientes (no "OK" constantes): areas netas vs tributarias,
    carga integrada vs aplicada, equilibrio de fuerzas/momentos, y compatibilidad del
    diafragma rigido (relacion cinematia con rotacion, no igualdad u==v).
"""

from __future__ import annotations

import json, sys, time
from pathlib import Path

from . import geometria_fe as GF
from .marco import Marco
from . import cargas_correlacionadas as CC
from . import tributaria as TB
from . import resolver as RES
from .hipotesis import COTAS_NIVEL_M, niveles_ordenados

_LAB = Path(__file__).resolve().parents[3]
RESULT = _LAB / "resultados" / "modelo_estructural"


def ensamblar_y_resolver(verbose=True, rigidez_mult=1.0e3, subdivision_vigas=1):
    t0 = time.time()
    niveles = GF.cargar_todos()
    marco = Marco(niveles, rigidez_mult=rigidez_mult)
    marco.subdivision_vigas = int(subdivision_vigas)
    marco.construir()
    r0 = marco.resumen()

    # --- cargas: correlacionadas por losa -> descarga sobre receptores (nodos FE) ---
    por_nivel_carga = CC.cargas_por_losa_por_nivel()
    cargas_nodales = {}
    repartos = {}
    for cod in niveles_ordenados():
        nivelFE = niveles[cod]
        cargas_por_losa = {}
        for lo in nivelFE.losas:
            info = por_nivel_carga.get(cod, {}).get(lo["id"], {})
            cargas_por_losa[lo["id"]] = (
                info.get("pm_kn_m2", 0.0), info.get("sc_kn_m2", 0.0))
        # caso G del laboratorio: PP + PM.ADIC (sin SC salvo indicacion explicita).
        cn, rp = TB.calcular_cargas_nodales(nivelFE, marco.receptor_nodos,
                                            cargas_por_losa, marco.key_of_tag,
                                            incluir_sc=False)
        cargas_nodales[cod] = cn
        repartos[cod] = rp

    sol = RES.resolver(marco, cargas_nodales)

    checks = _verificaciones(marco, sol, cargas_nodales, repartos, por_nivel_carga)

    payload = {
        "estado": ("resuelto_laboratorio_no_utilizable_para_diseno" if sol["ok"]
                   else "FALLO_singular_no_resuelto"),
        "modelo": r0,
        "solucion": {
            "ok": sol["ok"],
            "success": sol["success"],
            "analyze_retcode": sol.get("analyze_retcode"),
            "diagnostico": sol.get("diagnostico"),
            "singular_info": sol.get("singular_info"),
        },
        "hipotesis": {
            "material": "Hormigon G40, E=29725.5 MPa (ACI 318-19 19.2.2.1, f'c=40 MPa)",
            "continuidad_vertical": ("HIPOTESIS senalada: pilar/muro como continuo "
                                     "base->cota superior; columnas solo en tramos "
                                     "con evidencia por nivel"),
            "apoyo_base": "base fija 6DOF en z=CP1S (-4.01 m) (hipotesis de cimentacion)",
            "diafragma": ("rigido en plano (u,v) con relacion de cuerpo rigido "
                          "(rigidDiaphragm, incluye rotacion y distancia al maestro); "
                          "vertical libre; CP1S excluido"),
            "sotano": ("cielo del subterraneo (CP1S): solo restriccion vertical (w) "
                       "como hipotesis de descanso sobre la cimentacion"),
            "muros": ("dos montantes por extremo, cada uno con la mitad del ancho "
                      "(area total t x L conservada; sin duplicar rigidez)"),
            "carga_sin_clasificar": "0 carga superficial correlacionada (hipotesis)",
            "conector_excentrico_P1": (
                "union excentrica (v=-0.2) modelada con conector corto ELASTICO de "
                "rigidez elevada (E*mult, G*mult, mult=rigidez_mult), NO un vinculo "
                "rigido exacto. La deformacion propia del conector tiende a cero al "
                "subir el multiplicador pero NO es identicamente cero."),
        },
        "rigidez_mult_conector_excentrico_P1": marco.rigidez_mult,
        "cargas_nodales_total_kN": [round(x, 3) for x in sol["F_total_kN"]],
        "verificaciones": checks,
        "tiempos_s": round(time.time() - t0, 2),
    }
    RESULT.mkdir(parents=True, exist_ok=True)
    # Nombre por parametros de ejecucion (rigidez_mult, subdivision_vigas) para NO
    # sobrescribir evidencia entre corridas. La corrida de referencia (default
    # rigidez_mult=1e3, subdivision_vigas=1) conserva el nombre canonico.
    if rigidez_mult == 1.0e3 and subdivision_vigas == 1:
        _rerun_name = "resultado_primera_ejecucion.json"
    else:
        sfx = []
        if rigidez_mult != 1.0e3:
            sfx.append("mult%g" % rigidez_mult)
        if subdivision_vigas != 1:
            sfx.append("subdiv%s" % subdivision_vigas)
        _rerun_name = "resultado_%s.json" % ("_".join(sfx) if sfx else "ad_hoc")
    _run_tag = _rerun_name.replace("resultado_", "").replace(".json", "")
    (RESULT / _rerun_name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if sol["ok"]:
        sol_guardar = {
            "desplazamientos": {str(k): [round(x, 8) for x in v]
                                for k, v in sol["desplazamientos"].items()},
            "reacciones": {str(k): [round(x, 6) for x in v]
                           for k, v in sol["reacciones"].items()},
            "fuerzas_local_por_elemento": {str(k): [round(x, 6) for x in v]
                                           for k, v in sol["fuerzas"]["local"].items()},
            "fuerzas_global_por_elemento": {str(k): [round(x, 6) for x in v]
                                            for k, v in sol["fuerzas"]["global"].items()},
            "cargas_nodales": {cod: {str(k): [round(x, 6) for x in v]
                                     for k, v in car.items()}
                               for cod, car in cargas_nodales.items()},
        }
        (RESULT / ("solucion_cruda_%s.json" % _run_tag)).write_text(
            json.dumps(sol_guardar, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        (RESULT / ("diagnostico_fallo_%s.json" % _run_tag)).write_text(
            json.dumps({"solucion": payload["solucion"],
                        "modelo": r0,
                        "verificaciones": checks},
                       ensure_ascii=False, indent=2), encoding="utf-8")

    if verbose:
        if sol["ok"]:
            print(json.dumps({"modelo": r0,
                              "F_total_kN": payload["cargas_nodales_total_kN"],
                              "n_reacciones": sol["n_reacciones"],
                              "verificaciones": checks,
                              "tiempos_s": payload["tiempos_s"]},
                             ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"estado": "FALLO", "modelo": r0,
                              "analyze_retcode": sol.get("analyze_retcode"),
                              "diagnostico": sol.get("diagnostico"),
                              "singular_info": sol.get("singular_info"),
                              "tiempos_s": payload["tiempos_s"]},
                             ensure_ascii=False, indent=2))
    return payload, marco, sol


def _verificaciones(marco, sol, cargas_nodales, repartos, por_nivel_carga):
    out = {}

    def _gen(x_ref):
        for tag, f in x_ref.items():
            yield int(tag), f

    # 1) AREAS por losa y por nivel: neta geometrica, neta de carga (correlacion),
    #    asignada a receptores, no asignada. Se reporta la discrepancia por ID (no se
    #    renomaliza ni se amplia tolerancia para aprobar).
    out["areas_y_carga_por_nivel"] = {}
    for cod, rp in repartos.items():
        pl = rp.get("por_losa", {})
        n_geom = 0.0
        n_asig = 0.0
        n_corr = 0.0
        losas_det = {}
        for lo_id, info in pl.items():
            g = info["area_neta_geometrica_m2"]
            a = info["area_asignada_receptores_m2"]
            corr = info["area_superficial_carga_m2"]
            n_geom += g
            n_asig += a
            n_corr += corr
            losas_det[lo_id] = {
                "area_neta_geometrica_m2": g,
                "area_superficial_carga_correlacion_m2": corr,
                "area_asignada_receptores_m2": a,
                "area_no_asignada_m2": info["area_no_asignada_m2"],
                "por_comp_kN": info["por_comp_kN"],
                "n_receptores": len(info["receptores"]),
            }
        out["areas_y_carga_por_nivel"][cod] = {
            "area_neta_geometrica_m2": round(n_geom, 4),
            "area_superficial_carga_correlacion_m2": round(n_corr, 4),
            "area_asignada_receptores_m2": round(n_asig, 4),
            "area_no_asignada_m2": round(n_geom - n_asig, 4),
            "receptores_sin_fe": rp.get("receptores_sin_fe", []),
            "losas": losas_det,
            "ok_area": round(n_asig, 2) == round(n_geom, 2),
        }

    # 2) EQUILIBRIO global de FUERZAS y MOMENTOS (solo si solucion OK)
    if sol["ok"]:
        R = sol["reacciones"]
        Rz = sum(r[2] for r in R.values())
        Pz = -sol["F_total_kN"][2]
        out["equilibrio_vertical"] = {
            "R_z_kN": round(Rz, 4), "P_z_kN": round(Pz, 4),
            "residuo_kN": round(Rz - Pz, 4),
            "ok": abs(Rz - Pz) < 0.05 * max(abs(Pz), 1e-9),
        }
        out["equilibrio_horizontal"] = {
            "F_x_kN": round(sum(r[0] for r in R.values()), 4),
            "F_y_kN": round(sum(r[1] for r in R.values()), 4),
            "ok": (abs(sum(r[0] for r in R.values())) < 1e-6
                   and abs(sum(r[1] for r in R.values())) < 1e-6),
        }
        # MOMENTOS respecto al origen: Mx = Sigma Fz*y ; My = Sigma Fz*x (Fz<0 carga).
        def _mom(x_cargas):
            mx = my = 0.0
            for tag in x_cargas:
                u, v, z = marco.key_of_tag[tag]
                fz = x_cargas[tag][2]
                mx += fz * v
                my += fz * u
            return mx, my
        mom_reac = _mom(R)
        flat_load = {int(t): f for car in cargas_nodales.values()
                     for t, f in car.items()}
        mom_load = _mom(flat_load)
        # Equilibrio: las reacciones (Fz>0) equilibran las cargas (Fz<0), por lo que
        # el residuo cinematicos es M_reac + M_load ~= 0 (signos opuestos).
        tol_m = 0.05 * max(abs(Pz) * 30.0, 1e-9)   # ~ brazo max 30 m, 5 %
        out["equilibrio_momentos"] = {
            "Mx_reacciones_kN_m": round(mom_reac[0], 3),
            "Mx_cargas_kN_m": round(mom_load[0], 3),
            "My_reacciones_kN_m": round(mom_reac[1], 3),
            "My_cargas_kN_m": round(mom_load[1], 3),
            "res_Mx_kN_m": round(mom_reac[0] + mom_load[0], 3),
            "res_My_kN_m": round(mom_reac[1] + mom_load[1], 3),
            "ok": (abs(mom_reac[0] + mom_load[0]) < tol_m
                   and abs(mom_reac[1] + mom_load[1]) < tol_m),
        }
    else:
        for k in ("equilibrio_vertical", "equilibrio_horizontal", "equilibrio_momentos"):
            out[k] = {"ok": False, "nota": "no disponible (analisis fallo)"}

    # 3) DIAGRAGMA rigido (relacion cinematia con rotacion y distancia al maestro)
    #    Cadena completa verificada SIN redondear y SIN excluir nodos:
    #      (a) cada esclavo del diafragma -> su master (en el plano).
    #      (b) cada extremo excentrico de viga (esclavo del enlace rigido) -> el
    #          cuerpo rigido del piso, via su columna (esclava del diafragma) y el
    #          conector rigido. Con la representacion corregida (conector corto rigido
    #          compatible con Transformation, en vez del rigidLink anidado) el extremo
    #          excentrico sigue al piso en el plano con exactitud de maquina.
    if sol["ok"]:
        dia = {}
        rigid_links = getattr(marco, "rigid_links_info", []) or []
        excentricos = [int(lk["beam_tag"]) for lk in rigid_links if "beam_tag" in lk]
        for cod, master in marco.master_por_nivel.items():
            um, vm, wm = sol["desplazamientos"][master][:3]
            thz = sol["desplazamientos"][master][5]
            xu, yu = marco.key_of_tag[master][:2]
            # esclavos del diafragma segun el modelo construido
            slaves = marco.diafragma_esclavos_por_nivel.get(cod, [])
            excl = [t for t in slaves
                    if t in marco.diafragma_excluidos_rigidlink.get(cod, [])]
            checked = [t for t in slaves if t not in excl]
            max_err = 0.0
            worst = None
            for t in checked:
                ux, uy = sol["desplazamientos"][t][:2]
                dx, dy = marco.key_of_tag[t][0] - xu, marco.key_of_tag[t][1] - yu
                e_ux = um - thz * dy
                e_uy = vm + thz * dx
                err = max(abs(ux - e_ux), abs(uy - e_uy))
                if err > max_err:
                    max_err = err
                    worst = (t, round(dx, 3), round(dy, 3),
                             round(abs(ux - e_ux), 9), round(abs(uy - e_uy), 9))
            # extremos excentricos del nivel: siguen el cuerpo rigido del piso
            max_ecc_err = 0.0
            worst_ecc = None
            ecc_checked = 0
            for t in excentricos:
                if abs(marco.key_of_tag[t][2] - COTAS_NIVEL_M[cod]) > 1e-6:
                    continue
                ecc_checked += 1
                ux, uy = sol["desplazamientos"][t][:2]
                dx, dy = marco.key_of_tag[t][0] - xu, marco.key_of_tag[t][1] - yu
                e_ux = um - thz * dy
                e_uy = vm + thz * dx
                err = max(abs(ux - e_ux), abs(uy - e_uy))
                if err > max_ecc_err:
                    max_ecc_err = err
                    worst_ecc = (t, round(dx, 3), round(dy, 3),
                                 round(abs(ux - e_ux), 9), round(abs(uy - e_uy), 9))
            dia[cod] = {"n_esclavos_diafragma": len(slaves),
                        "n_esclavos_rigidlink_excl_por_nivel": len(excl),
                        "n_comprobados_diafragma": len(checked),
                        "n_extremos_excentricos_comprobados": ecc_checked,
                        "max_derr_cinematico_m": round(max_err, 9),
                        "peor_nodo": worst,
                        "max_derr_extremo_excentrico_m": round(max_ecc_err, 9),
                        "peor_extremo_excentrico": worst_ecc,
                        "ok": (max_err < 1e-4 and max_ecc_err < 1e-4)}
        # relacion vertical de cada extremo excentrico con su columna (conector corto
        # de rigidez elevada). Se diferencia:
        #   * dif_uz_conector_m : desplazamiento vertical relativo CRUDO (w_b - w_c).
        #   * rigid_body_uz_m   : movimiento vertical que el extremo hereda por ROTACION
        #                         de la columna (w_c + ry_c*dx - rx_c*dy). Es cinematica
        #                         de cuerpo rigido, NO deformacion del conector.
        #   * def_uz_conector_m : DEFORMACION VERTICAL REAL del conector = crudo menos
        #                         el cuerpo rigido. Solo esta magnitud es "deformacion
        #                         del conector" y debe compararse con su rigidez axial.
        # Con un conector elasticamente rigido (E*mult) la deformacion real es pequena
        # pero NO es cero; documentar esa aproximacion (no declarar equivalencia exacta).
        stub_det = {}
        for lk in rigid_links:
            ct, bt = lk.get("col_tag"), lk.get("beam_tag")
            if ct is None or bt is None or bt not in excentricos:
                continue
            dc = sol["desplazamientos"][int(ct)]
            db = sol["desplazamientos"][int(bt)]
            (uc, vc, _) = marco.key_of_tag[int(ct)]
            (ub, vb, _) = marco.key_of_tag[int(bt)]
            dxp, dyp = ub - uc, vb - vc
            rigid_w = dc[2] + dc[4] * dxp - dc[3] * dyp
            stub_det[int(bt)] = {
                "columna": int(ct),
                "dx_m": round(dxp, 4),
                "dy_m": round(dyp, 4),
                "dif_uz_conector_m": round(db[2] - dc[2], 9),
                "rigid_body_uz_m": round(rigid_w - dc[2], 9),
                "def_uz_conector_m": round(db[2] - rigid_w, 9),
                "err_rx": round(abs(db[3] - dc[3]), 9),
                "err_ry": round(abs(db[4] - dc[4]), 9),
            }
        dia["_conectores_estructurales_vertical"] = stub_det
        out["diafragmas"] = dia
    else:
        out["diafragmas"] = {"ok": False, "nota": "no disponible (analisis fallo)"}

    # ================= BALANCES INDEPENDIENTES (directiva: dos distintos) =========
    # Recoger carga total integrada del caso G y la carga de receptores sin nodos FE.
    integrada = 0.0
    sin_fe_total = 0.0
    sin_fe_det = {}
    for cod, rp in repartos.items():
        pl = rp.get("por_losa", {})
        for lo_id, info in pl.items():
            integrada += info["por_comp_kN"]["total"]
        for s in rp.get("receptores_sin_fe", []):
            sin_fe_total += s["carga_kN"]
            sin_fe_det.setdefault(cod, []).append({
                "receptor": s["receptor"], "losa": s["losa"],
                "area_m2": round(s["area_m2"], 3),
                "carga_no_aplicada_kN": round(s["carga_kN"], 3),
            })
    total_aplicada = -sum(f[2] for car in cargas_nodales.values()
                          for f in car.values())

    # BALANCE A: carga total del caso G (integrada sobre las losas) vs carga
    # realmente aplicada al modelo FE. DEBE FALLAR mientras exista carga omitida
    # (receptores sin nodos FE); con la correspondencia resuelta ambos coinciden.
    rel_A = (abs(integrada - total_aplicada) / max(abs(total_aplicada), 1e-9))
    out["balance_carga_casoG_vs_aplicada"] = {
        "carga_casoG_integrada_kN": round(integrada, 4),
        "carga_aplicada_nodal_total_kN": round(total_aplicada, 4),
        "carga_omitida_receptores_sin_fe_kN": round(sin_fe_total, 4),
        "residuo_kN": round(integrada - total_aplicada, 4),
        "rel_dif": round(rel_A, 6),
        "ok": (sin_fe_total == 0.0 and rel_A < 0.05),
        "nota": "caso G = PP + PM.ADIC (sin SC). Falla si existe carga tributaria "
                "omitida (receptores sin nodos FE).",
    }

    # BALANCE B: carga aplicada al modelo FE vs reacciones de apoyo (equilibrio).
   #    Se reporta explicitamente (ademas de equilibrio_vertical) como balance B.
    out["balance_carga_aplicada_vs_reacciones"] = {
        "carga_aplicada_total_kN": round(total_aplicada, 4),
        "reacciones_total_kN": round(
            sum(r[2] for r in sol["reacciones"].values()), 4)
        if sol["ok"] else None,
        "ok": bool(out.get("equilibrio_vertical", {}).get("ok", False)),
        "nota": "ver equilibrio_vertical (R_z vs P_z) y equilibrio_momentos.",
    }

    # Receptores con carga pero sin nodos FE: inconsistencia real a resolver (P2/P3).
    out["carga_no_aplicada_por_receptores_sin_fe"] = {
        "carga_total_no_aplicada_kN": round(sin_fe_total, 4),
        "por_nivel": sin_fe_det,
        "ok": sin_fe_total == 0.0,
        "nota": ("receptores con carga tributaria asignada pero sin nodos FE en el "
                 "modelo; su carga NO se aplica. Debe resolverse, no descartarse."),
    }
    return out


if __name__ == "__main__":
    mult = 1.0e3
    if len(sys.argv) > 1:
        mult = float(sys.argv[1])
    payload, marco, sol = ensamblar_y_resolver(rigidez_mult=mult)
    print("OK  mult=%g -> resultados/modelo_estructural/resultado_%s" % (
        mult, ("primera_ejecucion.json" if mult == 1.0e3 else "mult_%g.json" % mult)))
