"""Verificacion de superposicion COMPLETA (G + Q + EX + EY) por edificio (Entrega 3).

Para cada edificio (I y II) se ejecutan CINCO corridas FE sobre EXACTAMENTE el
mismo modelo lineal congelado:

   1. corrida G  : PP (+ losa) sola, sin SC.
   2. corrida Q  : SOBRECARGA uniforme q_Q sola, G ausente (caso base Q).
   3. corrida EX : sismo pseudoestatico en +X solo (Wi = PP + 0.5 Q; Fi = 0.20 Wi),
                   sin cargas gravitacionales (ver src/cargas/caso_sismico.py).
   4. corrida EY : idem en +Y.
   5. corrida EXPLICITA : lambda_G*G + lambda_Q*Q + lambda_EX*EX + lambda_EY*EY
                          en UN SOLO patron de carga (una sola corrida FE).

y compara la SUPERPOSICION
     R_sup = lambda_G*R_G + lambda_Q*R_Q + lambda_EX*R_EX + lambda_EY*R_EY
contra la corrida explicita (mismo modelo) en desplazamiento, reaccion, fuerza
axial y momento de extremo, con tolerancia relativa por magnitud.

Coeficientes del CONJUNTO DE DEMOSTRACION (config/superposicion.json):
     lambda_G=1.0, lambda_Q=0.7, lambda_EX=0.3, lambda_EY=-0.2
(NO es combinacion de diseno; solo demuestra que la superposicion es exacta.)

Controles previos (ABORTAN si fallan):
   * compatibilidad de los cinco casos base: mismos nodos/coordenadas/elementos/
     restricciones/DOF/materiales y mismas claves/convenciones de resultados.
   * el patron de carga EXPLICITO coincide con la suma ponderada de los cuatro
     patrones base (G, Q, EX, EY) en todos los nodos y componentes.

Salidas (por edificio `=`):
   results/superposicion/verificacion_superposicion_completa_{I,II}.json    (evidencia)
   results/superposicion/verificacion_superposicion_completa_{I,II}.csv     (tabla)
   results/superposicion/verificacion_superposicion_completa_{I,II}.md      (informe)
   figures/superposicion/verificacion_superposicion_completa_{I,II}.png     (figura)

Uso:
   python -X utf8 -m src.cargas.verificacion_superposicion_completa --edificio I
   python -X utf8 -m src.cargas.verificacion_superposicion_completa --edificio II

Estado: IMPLEMENTADO_Y_VERIFICADO_COMPLETO (sustituye al bloqueo previo por
parametros sismicos: EX/EY ya implementados con el metodo pseudoestatico de la
consigna).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
CONFIG_CARGAS = E3 / "config" / "cargas.json"
CONFIG_SUPER = E3 / "config" / "superposicion.json"
RES_DIR = E3 / "results" / "superposicion"
FIG_DIR = E3 / "figures" / "superposicion"
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"

sys.path.insert(0, str(E3))
sys.path.insert(0, str(EI_SRC))

from src.cargas.caso_sismico import (           # noqa: E402
    _agrupar_por_nivel, _flat_por_nivel, _marcos_y_cargas)
from src.cargas.peso_sismico import (           # noqa: E402
    generar_cargas_sismicas_directas, leer_config_sismo)

TOL_COMPARACION_REL = 1e-4
TOL_EQUILIBRIO_VERT = 0.05
FLOOR = {"m": 1e-6, "kN": 1e-3, "kN_m": 1e-2}
INDICES_MOMENTO = (4, 5, 10, 11)  # Mz_i, My_i, Mz_j, My_j en localForce(12)


def _lambdas() -> dict:
    d = json.loads(CONFIG_SUPER.read_text(encoding="utf-8"))["conjunto_demostracion"]
    return {"G": float(d["lambda_G"]), "Q": float(d["lambda_Q"]),
            "EX": float(d["lambda_EX"]), "EY": float(d["lambda_EY"]),
            "etiqueta": d["etiqueta"]}


def _nuevo_marco(edificio: str):
    if edificio == "I":
        from analisis.fe import geometria_fe as GF
        from analisis.fe.marco import Marco
        niveles = GF.cargar_todos()
        marco = Marco(niveles, rigidez_mult=1.0e3)
        marco.subdivision_vigas = 1
        marco.construir()
        return marco
    else:
        from src.cargas.pipeline_FE_EII import MarcoEII
        marco = MarcoEII(v031_seccion="V.60/80")
        marco.construir()
        return marco


def _resolver(marco, por_nivel):
    if type(marco).__name__ == "MarcoEII":
        return marco.resolver_caso(por_nivel)
    from analisis.fe import resolver as RESOL
    return RESOL.resolver(marco, por_nivel)


def _corrida(edificio: str, cargas_flat: dict, cotas: dict) -> tuple:
    """Modelo nuevo + resolver con las cargas planas agrupadas por nivel."""
    marco = _nuevo_marco(edificio)
    por_nivel = _agrupar_por_nivel(cargas_flat, marco.key_of_tag, cotas)
    sol = _resolver(marco, por_nivel)
    return marco, sol


def _combina(lam: dict, G: dict, Q: dict, EX: dict, EY: dict) -> dict:
    exp = {}
    for t in set(G) | set(Q) | set(EX) | set(EY):
        a = G.get(t, [0.0] * 6)
        b = Q.get(t, [0.0] * 6)
        c = EX.get(t, [0.0] * 6)
        d = EY.get(t, [0.0] * 6)
        exp[t] = [lam["G"] * a[i] + lam["Q"] * b[i]
                  + lam["EX"] * c[i] + lam["EY"] * d[i] for i in range(6)]
    return exp


def _firma(marco) -> dict:
    e_rec = []
    for r in list(marco.columnas) + list(marco.vigas_elem) + list(marco.muros_elem):
        sv = r.get("sec_valores")
        e_rec.append({"tipo": r.get("tipo"), "tag": int(r["tag"]),
                      "nodo_i": int(r["nodo_i"]), "nodo_j": int(r["nodo_j"]),
                      "seccion": r.get("seccion"),
                      "sec_valores": {k: float(sv[k])
                                      for k in ("E", "A", "Iy", "Iz", "G", "J")}
                      if isinstance(sv, dict) else None})
    stubs = []
    for r in getattr(marco, "stub_elem", []):
        d = {"tipo": r.get("tipo"), "tag": int(r.get("tag"))}
        for k in ("nodo_i", "nodo_j"):
            if k in r:
                d[k] = int(r[k])
        stubs.append(d)
    return {"n_nodos": len(marco.nodes),
            "orden_creacion_nodos": [int(t) for t in marco.key_of_tag],
            "coordenadas": {str(t): [round(float(x), 9) for x in k]
                            for t, k in marco.key_of_tag.items()},
            "elementos": sorted(e_rec, key=lambda x: x["tag"]),
            "stubs_rigidos": sorted(stubs, key=lambda x: x["tag"]),
            "base_fija": sorted(int(t) for t in getattr(marco, "_base_fixed", set())),
            "master_por_nivel": {k: int(v) for k, v in marco.master_por_nivel.items()},
            "diafragma_esclavos": {k: sorted(int(x) for x in v)
                                   for k, v in marco.diafragma_esclavos_por_nivel.items()},
            "rigid_links": sorted([{"col": int(l["col_tag"]), "beam": int(l["beam_tag"])}
                                   for l in getattr(marco, "rigid_links_info", [])],
                                  key=lambda x: x["beam"]),
            "rigid_links_franja": sorted(
                [[int(a), int(t)] for a, t in getattr(marco, "_strip_enlazados", [])],
                key=lambda x: x[1]),
            "v031_seccion": getattr(marco, "v031_seccion", None),
            "E_mpa": getattr(marco, "E_mpa", None)}


def _compatibilidad(sols, patrones, expl) -> dict:
    salida = {"matrices": {}, "claves_resultados": {}, "patron_explicito_consistente": None}
    firmas = {}
    for c, s in sols.items():
        firmas[c] = s.get("_firma")
    base = firmas["G"]
    difs = {c: [k for k in base if firmas[c].get(k) != base.get(k)]
            for c in firmas if c != "G"}
    if any(difs.values()):
        raise SystemExit("ABORTE_COMPATIBILIDAD: el modelo difiere entre corridas. "
                         "Discrepancias: %s" % json.dumps(difs, ensure_ascii=False))
    salida["matrices"] = {"n_nodos": {c: firmas[c]["n_nodos"] for c in firmas},
                          "firmas_iguales": True, "discrepancias": 0}

    claves = {}
    for c, s in sols.items():
        claves[c] = {"n_disp": len(s["desplazamientos"]),
                     "n_reacciones": len(s["reacciones"]),
                     "n_fuerzas": len(s["fuerzas"]["local"]),
                     "len_disp_6": all(len(v) == 6 for v in s["desplazamientos"].values()),
                     "len_fuerzas_12": all(len(v) == 12
                                           for v in s["fuerzas"]["local"].values())}
    claves["G"]["tags_disp_iguales"] = sorted(str(k) for k in sols["G"]["desplazamientos"]) == \
        sorted(str(k) for k in sols["EXPLICITA"]["desplazamientos"])
    ok_claves = (len({claves[c]["n_disp"] for c in claves}) == 1
                 and len({claves[c]["n_fuerzas"] for c in claves}) == 1
                 and all(claves[c]["len_disp_6"] and claves[c]["len_fuerzas_12"]
                         for c in claves)
                 and claves["G"]["tags_disp_iguales"])
    salida["claves_resultados"] = claves
    if not ok_claves:
        raise SystemExit("ABORTE_COMPATIBILIDAD: claves/convenciones difieren: %s"
                         % json.dumps(claves))

    max_dif = 0.0
    for t in set(patrones["G"]) | set(patrones["Q"]) | set(patrones["EX"]) \
             | set(patrones["EY"]) | set(expl):
        va = expl.get(t, [0.0] * 6)
        vb = (patrones["G"].get(t, [0.0] * 6))
        # el patron explicito DEBE ser la suma ponderada de los cuatro patrones
        lam = _lambdas()
        vb = [lam["G"] * patrones["G"].get(t, [0.0] * 6)[i]
              + lam["Q"] * patrones["Q"].get(t, [0.0] * 6)[i]
              + lam["EX"] * patrones["EX"].get(t, [0.0] * 6)[i]
              + lam["EY"] * patrones["EY"].get(t, [0.0] * 6)[i] for i in range(6)]
        for i in range(6):
            max_dif = max(max_dif, abs(va[i] - vb[i]))
    ok_p = max_dif <= 1e-9
    salida["patron_explicito_consistente"] = {"max_diferencia_kN": round(max_dif, 12),
                                              "ok": ok_p}
    if not ok_p:
        raise SystemExit("ABORTE_COMPATIBILIDAD: el patron EXPLICITO no coincide con "
                         "la suma ponderada de G/Q/EX/EY (max dif %.3e)." % max_dif)
    return salida


def _equilibrio(marco, cargas_nodales, sol, etiqueta) -> dict:
    Pz = -sol["F_total_kN"][2]
    R = sol["reacciones"]
    Rz = sum(r[2] for r in R.values())
    crit_v = abs(Rz - Pz) < TOL_EQUILIBRIO_VERT * max(abs(Pz), 1e-9)
    Fx = sum(f[0] for f in cargas_nodales.values())
    Fy = sum(f[1] for f in cargas_nodales.values())
    hor = {"Fx_kN": round(sum(r[0] for r in R.values()), 4),
           "Fy_kN": round(sum(r[1] for r in R.values()), 4),
           "Px_kN": round(Fx, 4), "Py_kN": round(Fy, 4)}
    ok_h = (abs(hor["Fx_kN"] + Fx) < 1e-4 and abs(hor["Fy_kN"] + Fy) < 1e-4)

    def _mom(x):
        mx = my = 0.0
        for t, f in x.items():
            u, v, _z = marco.key_of_tag[t][:3]
            mx += f[2] * v
            my += f[2] * u
        return mx, my

    mr = _mom(R)
    ml = _mom(cargas_nodales)
    tol_m = TOL_EQUILIBRIO_VERT * max(abs(Pz) * 30.0, 1e-9)
    ok_m = abs(mr[0] + ml[0]) < tol_m and abs(mr[1] + ml[1]) < tol_m
    return {"caso": etiqueta, "R_z_kN": round(Rz, 4), "P_z_kN": round(Pz, 4),
            "residuo_vertical_kN": round(Rz - Pz, 4),
            "ok_vertical": crit_v,
            "horizontal": hor, "ok_horizontal": ok_h,
            "res_momentos_kN_m": [round(mr[0] + ml[0], 3), round(mr[1] + ml[1], 3)],
            "ok_momentos": ok_m}


def _fuente(Rdic, familia, id_, idx):
    if familia == "desplazamiento":
        return Rdic["desplazamientos"][id_][idx]
    if familia == "reaccion":
        return Rdic["reacciones"][id_][idx]
    if familia in ("axial", "momento"):
        return Rdic["fuerzas"]["local"][id_][idx]
    raise KeyError(familia)


def _seleccion(R, marco) -> list:
    lam = _lambdas()
    disp = R["EXPLICITA"]["desplazamientos"]
    reac = R["EXPLICITA"]["reacciones"]
    fl = R["EXPLICITA"]["fuerzas"]["local"]
    beam_tags = {int(r["tag"]) for r in marco.vigas_elem}
    col_tags = {int(r["tag"]) for r in marco.columnas}
    raw = []
    t_uz = max(disp, key=lambda t: abs(disp[t][2]))
    raw.append((["desplazamiento", t_uz, 2, "uz", "m"],
                "Nodo %s | desplazamiento vertical" % t_uz,
                "global DOF3 (w); + = +Z"))
    m_h, t_h, i_h = -1.0, None, None
    for t in disp:
        for i in (0, 1):
            if abs(disp[t][i]) > m_h:
                m_h, t_h, i_h = abs(disp[t][i]), t, i
    raw.append((["desplazamiento", t_h, i_h, "ux" if i_h == 0 else "uy", "m"],
                "Nodo %s | desplazamiento horizontal" % t_h,
                "global DOF1/DOF2; + = +X/+Y"))
    for k, t in enumerate(sorted(reac, key=lambda t: -abs(reac[t][2]))[:2]):
        raw.append((["reaccion", t, 2, "Rz", "kN"],
                    "Nodo base %s | reaccion vertical" % t,
                    "global; + = hacia arriba"))
    e_ax = max(fl, key=lambda e: max(abs(fl[e][0]), abs(fl[e][6])))
    for i_ext in (0, 6):
        raw.append((["axial", e_ax, i_ext, "N_i" if i_ext == 0 else "N_j", "kN"],
                    "Elemento %s | fuerza axial extremo %s" % (e_ax, "i" if i_ext == 0 else "j"),
                    "localForce indice %d; + = compresion en el extremo" % i_ext))

    def _max_mom(keys):
        best = None
        for e in keys:
            for i in INDICES_MOMENTO:
                m = abs(fl[e][i])
                if best is None or m > best[0]:
                    best = (m, e, i)
        return best

    def _nom_mom(i):
        return "Mz_i" if i == 4 else "My_i" if i == 5 else \
            "Mz_j" if i == 10 else "My_j"

    best = _max_mom(col_tags)
    if best:
        _, e, i = best
        raw.append((["momento", e, i, _nom_mom(i), "kN_m"],
                    "Elemento %s (COLUMNA) | momento local de extremo" % e,
                    "localForce indice %d" % i))
    bbest = _max_mom(beam_tags)
    if bbest:
        _, e, i = bbest
        raw.append((["momento", e, i, _nom_mom(i), "kN_m"],
                    "Elemento %s (VIGA) | momento local de extremo" % e,
                    "localForce indice %d" % i))

    filas = []
    for (fam, id_, idx, comp, unidad), titulo, conv in raw:
        g = _fuente(R["G"], fam, id_, idx)
        q = _fuente(R["Q"], fam, id_, idx)
        x = _fuente(R["EX"], fam, id_, idx)
        y = _fuente(R["EY"], fam, id_, idx)
        e = _fuente(R["EXPLICITA"], fam, id_, idx)
        sup = lam["G"] * g + lam["Q"] * q + lam["EX"] * x + lam["EY"] * y
        escala = max(abs(e), FLOOR[unidad])
        err = abs(sup - e)
        rel = err / escala if escala > 0 else (0.0 if err == 0.0 else 1.0)
        filas.append({"familia": fam, "id": id_, "componente": comp,
                      "unidad": unidad, "titulo": titulo, "convencion": conv,
                      "G": round(g, 9), "Q": round(q, 9), "EX": round(x, 9),
                      "EY": round(y, 9), "superpuesto": sup, "explicito": e,
                      "error_abs": err, "error_rel": rel,
                      "tolerancia_rel": TOL_COMPARACION_REL,
                      "estado": "OK" if rel <= TOL_COMPARACION_REL else "ERROR"})
    return filas


def _max_errores(filas) -> dict:
    out = {}
    for fam in sorted({f["familia"] for f in filas}):
        fs = [f for f in filas if f["familia"] == fam]
        out[fam] = {"max_error_abs": max(f["error_abs"] for f in fs),
                    "max_error_rel": max(f["error_rel"] for f in fs),
                    "n": len(fs)}
    out["_all"] = {"max_error_abs": max(f["error_abs"] for f in filas),
                   "max_error_rel": max(f["error_rel"] for f in filas)}
    return out


def _escribir(payload, filas, eq, max_err, lam, edificio, compat):
    suf = "I" if edificio == "I" else "II"
    RES_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    jp = RES_DIR / ("verificacion_superposicion_completa_%s.json" % suf)
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")

    cp = RES_DIR / ("verificacion_superposicion_completa_%s.csv" % suf)
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["familia", "id", "componente", "unidad", "convencion",
                    "G", "Q", "EX", "EY", "superpuesto", "explicito",
                    "error_abs", "error_rel", "tol_rel", "estado"])
        for r in filas:
            w.writerow([r["familia"], r["id"], r["componente"], r["unidad"],
                        r["convencion"], f"{r['G']:.6f}", f"{r['Q']:.6f}",
                        f"{r['EX']:.6f}", f"{r['EY']:.6f}",
                        f"{r['superpuesto']:.6f}", f"{r['explicito']:.6f}",
                        f"{r['error_abs']:.3e}", f"{r['error_rel']:.3e}",
                        f"{r['tolerancia_rel']:.3e}", r["estado"]])

    lineas = []
    lineas.append("# Verificacion de superposicion COMPLETA - Edificio %s" % edificio)
    lineas.append("")
    lineas.append("R_sup = %.3g*G + %.3g*Q + %.3g*EX + %.3g*EY (conjunto %s) versus "
                  "la corrida EXPLICITA sobre el mismo modelo lineal."
                  % (lam["G"], lam["Q"], lam["EX"], lam["EY"], lam["etiqueta"]))
    lineas.append("")
    lineas.append("Caso Q: %s" % payload["caso_Q"]["etiqueta"])
    lineas.append("")
    lineas.append("## Tabla por magnitud (seleccion documentada, sobre EXPLICITO)")
    lineas.append("")
    lineas.append("| Familia | Descripcion | Convencion | G | Q | EX | EY | "
                  "Superpuesto | Explicito | |Error| | |err|/exp | Tol | Estado |")
    lineas.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in filas:
        conv = r["convencion"].replace("|", "/")
        lineas.append("| %s | %s | %s | %.6g | %.6g | %.6g | %.6g | %.6g | "
                      "%.6g | %.3e | %.3e | %.0e | %s |"
                      % (r["familia"], r["titulo"], conv, r["G"], r["Q"],
                         r["EX"], r["EY"], r["superpuesto"], r["explicito"],
                         r["error_abs"], r["error_rel"], r["tolerancia_rel"],
                         r["estado"]))
    lineas.append("")
    lineas.append("## Errores maximos por familia")
    lineas.append("")
    lineas.append("| Familia | Max |error abs| | Max error rel | n |")
    lineas.append("|---|---|---|---|")
    for fam, e in max_err.items():
        if fam == "_all":
            continue
        lineas.append("| %s | %.3e | %.3e | %d |" % (fam, e["max_error_abs"],
                                                     e["max_error_rel"], e["n"]))
    all_e = max_err["_all"]
    lineas.append("| **TODAS** | **%.3e** | **%.3e** | %d |"
                  % (all_e["max_error_abs"], all_e["max_error_rel"], len(filas)))
    lineas.append("")
    lineas.append("## Equilibrio global de la corrida EXPLICITA")
    lineas.append("")
    lineas.append("- vertical: R_z=%.4f vs P_z=%.4f, residuo=%.4f kN, %s"
                  % (eq["R_z_kN"], eq["P_z_kN"], eq["residuo_vertical_kN"],
                     "OK" if eq["ok_vertical"] else "ERROR"))
    lineas.append("- horizontal: R=(%.4f, %.4f) vs P=(%.4f, %.4f), %s"
                  % (eq["horizontal"]["Fx_kN"], eq["horizontal"]["Fy_kN"],
                     eq["horizontal"]["Px_kN"], eq["horizontal"]["Py_kN"],
                     "OK" if eq["ok_horizontal"] else "ERROR"))
    lineas.append("- momentos (origen): residuo Mx=%.3f, My=%.3f kN*m, %s"
                  % (eq["res_momentos_kN_m"][0], eq["res_momentos_kN_m"][1],
                     "OK" if eq["ok_momentos"] else "ERROR"))
    lineas.append("")
    lineas.append("## Compatibilidad de los casos base")
    lineas.append("")
    lineas.append("- matrices identicas entre las 5 corridas: %s"
                  % ("OK" if compat["matrices"]["firmas_iguales"] else "ERROR"))
    lineas.append("- claves/convenciones de resultados identicas: %s"
                  % ("OK" if compat["claves_resultados"] else "ERROR"))
    lineas.append("- patron EXPLICITO = suma ponderada de G/Q/EX/EY: %s (max dif %.3e)"
                  % ("OK" if compat["patron_explicito_consistente"]["ok"] else "ERROR",
                     compat["patron_explicito_consistente"]["max_diferencia_kN"]))
    lineas.append("")
    ok_all = (eq["ok_vertical"] and eq["ok_horizontal"] and eq["ok_momentos"]
              and all(r["estado"] == "OK" for r in filas)
              and compat["matrices"]["firmas_iguales"]
              and compat["patron_explicito_consistente"]["ok"])
    lineas.append("## Estado final")
    lineas.append("")
    lineas.append("- **%s**" % ("IMPLEMENTADO_Y_VERIFICADO_COMPLETO" if ok_all
                                else "ERROR_VERIFICACION"))
    lineas.append("- notas: EX/EY pseudoestaticos de la consigna (Wi=PP+0.5Q, "
                  "Fi=0.20Wi); conjunto de demostracion para la superposicion; "
                  "no es combinacion de diseno.")
    lineas.append("")
    mp = RES_DIR / ("verificacion_superposicion_completa_%s.md" % suf)
    mp.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return jp, cp, mp


def _figura(filas, lam, edificio):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    suf = "I" if edificio == "I" else "II"

    TITULO = {"desplazamiento": "Desplazamientos",
              "reaccion": "Reacciones",
              "axial": "Fuerzas axiales",
              "momento": "Momentos de extremo"}
    UNIDAD = {"desplazamiento": "m", "reaccion": "kN",
              "axial": "kN", "momento": "kN·m"}
    ORDEN = ["desplazamiento", "reaccion", "axial", "momento"]
    FLOOR_REL = 1e-16  # piso numerico documentado para errores exactamente 0

    def etiqueta(r):
        fam, comp, sid = r["familia"], r["componente"], r["id"]
        if fam == "desplazamiento":     # 'uz' -> 'u_z'
            nombre = "%s_%s" % (comp[0], comp[1:])
        elif fam == "reaccion":         # 'Rz' -> 'R_z'
            nombre = "%s_%s" % (comp[0], comp[1:])
        elif fam == "axial":            # 'N_i' / 'N_j'
            nombre = comp
        else:                           # 'Mz_j' -> 'M_z,j'
            nombre = "%s_%s,%s" % (comp[0], comp[1:-1], comp[-1])
        ref = "nodo %s" % sid if fam in ("desplazamiento", "reaccion") \
            else "elemento %s" % sid
        return "%s — %s" % (nombre, ref)

    celdas = [(0, 0), (0, 1), (1, 0), (1, 1)]
    fig = plt.figure(figsize=(16, 11.5), dpi=150)
    gs = fig.add_gridspec(3, 2, height_ratios=(1, 1, 1.3),
                          hspace=0.42, wspace=0.24)
    ax_mag = {}
    for fam, (i, j) in zip(ORDEN, celdas):
        ax_mag[fam] = fig.add_subplot(gs[i, j])
    ax_err = fig.add_subplot(gs[2, :])

    for fam, ax in ax_mag.items():
        rows = [r for r in filas if r["familia"] == fam]
        x = np.arange(len(rows))
        sup = [r["superpuesto"] for r in rows]
        expv = [r["explicito"] for r in rows]
        w = 0.4
        ax.bar(x - w / 2, sup, width=w, color="#2c7bb6", label="Superpuesto")
        ax.bar(x + w / 2, expv, width=w, color="#d7191c", label="Explícito")
        ax.set_xticks(x)
        ax.set_xticklabels([etiqueta(r) for r in rows], rotation=20,
                           ha="right", fontsize=7.5)
        ax.set_title("%s [%s]" % (TITULO[fam], UNIDAD[fam]), fontsize=10)
        ax.set_ylabel("magnitud [%s]" % UNIDAD[fam])
        ax.grid(axis="y", alpha=0.3)
        mrel = max(abs(r["error_rel"]) for r in rows)
        ylo, yhi = ax.get_ylim()
        ax.set_ylim(ylo, yhi + 0.22 * (yhi - ylo))
        ax.text(0.985, 0.92, "máx |error rel| = %.1e" % mrel,
                transform=ax.transAxes, ha="right", va="top",
                fontsize=7, color="#444444",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffffff",
                          edgecolor="#999999", lw=0.8, alpha=0.9))
        if fam == "desplazamiento":
            ax.legend(fontsize=8, loc="upper left")

    xall = np.arange(len(filas))
    labels = [etiqueta(r) for r in filas]
    rel = np.array([r["error_rel"] for r in filas], dtype=float)
    yplot = np.where(rel > 0.0, rel, FLOOR_REL)
    ax_err.set_yscale("log")
    ax_err.plot(xall, yplot, "o-", color="#1a9641", lw=1.2, ms=5)
    zeros = np.where(rel == 0.0)[0]
    for z in zeros:
        ax_err.plot([z], [FLOOR_REL], "x", color="#8b0000", ms=11,
                    mew=2, zorder=6)
        ax_err.annotate("≈0", (z, FLOOR_REL), xytext=(z, FLOOR_REL * 8),
                        ha="center", fontsize=9, color="#8b0000")
    ax_err.axhline(1e-4, color="#d7191c", ls="--", lw=1)
    ax_err.text(0.02, 3.0e-4, "tolerancia relativa 1e-4",
                color="#d7191c", fontsize=8)
    ax_err.axhline(FLOOR_REL, color="0.6", ls=":", lw=1)
    ax_err.text(0.02, FLOOR_REL * 1.6,
                "piso de representación 1e-16 (errores ≈ 0)",
                color="0.4", fontsize=7)
    ax_err.set_xticks(xall)
    ax_err.set_xticklabels(labels, rotation=45, ha="right", fontsize=7.5)
    ax_err.set_ylabel("error relativo (—)")
    ax_err.set_title("Error relativo por magnitud (escala logarítmica)",
                     fontsize=10)
    ax_err.grid(alpha=0.3, which="both")
    ax_err.set_ylim(FLOOR_REL / 2.0,
                    max(1e-3, float(np.max(yplot)) * 1.5))

    fig.suptitle("Verificación de superposición completa — Edificio %s"
                 % edificio, fontsize=13)
    fig.text(0.5, 0.925,
             "Combinación arbitraria de demostración: "
             "1,0G + 0,7Q + 0,3EX − 0,2EY   ·   "
             "respuesta superpuesta vs corrida explícita (mismo modelo)",
             ha="center", va="center", fontsize=9.5, color="#333333")
    fig.tight_layout(rect=(0, 0.02, 1, 0.90))
    fp = FIG_DIR / ("verificacion_superposicion_completa_%s.png" % suf)
    fig.savefig(fp, dpi=150)
    plt.close(fig)
    return fp


def run(edificio: str) -> int:
    if edificio not in ("I", "II"):
        raise SystemExit("edificio debe ser 'I' o 'II'")
    lam = _lambdas()
    cfg_cargas = json.loads(CONFIG_CARGAS.read_text(encoding="utf-8"))
    q_Q = float(cfg_cargas["q_Q"][edificio]["q_Q_kN_m2"])
    etiq_q = cfg_cargas["q_Q"][edificio].get("etiqueta_corrida",
                                             "Q_%s_ADOPTADA_2.0_kN_m2" % edificio)
    cfg_sismo = leer_config_sismo()

    # patrones base con el modelo de una sola corrida (solo geometria/cargas)
    marco_aux, G_flat, Q_flat, cotas = _marcos_y_cargas(edificio, q_Q)
    ex = generar_cargas_sismicas_directas(G_flat, Q_flat, marco_aux.key_of_tag,
                                          "X", cfg_sismo)
    ey = generar_cargas_sismicas_directas(G_flat, Q_flat, marco_aux.key_of_tag,
                                          "Y", cfg_sismo)
    EX_flat = ex["cargas_nodales"]
    EY_flat = ey["cargas_nodales"]
    EXPL_flat = _combina(lam, G_flat, Q_flat, EX_flat, EY_flat)
    patrones = {"G": G_flat, "Q": Q_flat, "EX": EX_flat, "EY": EY_flat}

    sols = {}
    for c, flat in [("G", G_flat), ("Q", Q_flat), ("EX", EX_flat),
                    ("EY", EY_flat), ("EXPLICITA", EXPL_flat)]:
        marco, sol = _corrida(edificio, flat, cotas)
        sol["_firma"] = _firma(marco)
        sols[c] = sol
        if not sol["ok"]:
            raise SystemExit("ABORTE: corrida %s fallo (retcode %s)"
                             % (c, sol.get("analyze_retcode")))

    compat = _compatibilidad(sols, patrones, EXPL_flat)
    R = sols
    filas = _seleccion(R, marco)
    max_err = _max_errores(filas)
    eq = _equilibrio(marco, EXPL_flat, sols["EXPLICITA"],
                     "EXPLICITA G+Q+EX+EY")

    info_q = {"etiqueta": etiq_q, "q_Q_kN_m2": q_Q}
    payload = {
        "verificacion": "superposicion_completa_%s" % edificio,
        "edificio": edificio,
        "etiqueta": "IMPLEMENTADO_Y_VERIFICADO_COMPLETO",
        "lambda": lam,
        "caso_Q": info_q,
        "corridas": {c: {"ok": bool(s["ok"]),
                         "retcode": s.get("analyze_retcode"),
                         "F_total_kN": [round(float(x), 6) for x in s["F_total_kN"]]}
                     for c, s in sols.items()},
        "resumen_peso_sismico": {"W_total_kN": ex["verificaciones"]["W_total_sismico_kN"],
                                 "F_EX_kN": ex["verificaciones"]["F_total_aplicada_kN"],
                                 "F_EY_kN": ey["verificaciones"]["F_total_aplicada_kN"],
                                 "momento_accidental_kN_m":
                                     ex["verificaciones"]["momento_accidental_total_kN_m"]},
        "modelo": marco.resumen(),
        "modelo_n_elementos": len(marco.columnas) + len(marco.vigas_elem)
                              + len(marco.muros_elem),
        "compatibilidad": compat,
        "equilibrio_explicito": eq,
        "comparacion": {"tolerancia_rel": TOL_COMPARACION_REL,
                        "filas": filas, "errores_maximos": max_err},
        "resultados_por_corrida": {
            c: {"desplazamientos": {str(k): [round(float(x), 9) for x in v]
                                    for k, v in s["desplazamientos"].items()},
                "reacciones": {str(k): [round(float(x), 6) for x in v]
                               for k, v in s["reacciones"].items()},
                "fuerzas_local": {str(k): [round(float(x), 6) for x in v]
                                  for k, v in s["fuerzas"]["local"].items()}}
            for c, s in sols.items()},
    }

    jp, cp, mp = _escribir(payload, filas, eq, max_err, lam, edificio, compat)
    fp = _figura(filas, lam, edificio)

    ok_all = (eq["ok_vertical"] and eq["ok_horizontal"] and eq["ok_momentos"]
              and all(r["estado"] == "OK" for r in filas)
              and compat["matrices"]["firmas_iguales"]
              and compat["patron_explicito_consistente"]["ok"])
    print(json.dumps({
        "verificacion": "superposicion_completa_%s" % edificio,
        "edificio": edificio,
        "estado": "IMPLEMENTADO_Y_VERIFICADO_COMPLETO" if ok_all
                  else "ERROR_VERIFICACION",
        "lambda": lam,
        "F_total_kN": {c: sols[c]["F_total_kN"] for c in sols},
        "resumen_peso_sismico": payload["resumen_peso_sismico"],
        "compatibilidad": {"firmas_identicas": True,
                           "patron_explicito_consistente":
                               compat["patron_explicito_consistente"]},
        "equilibrio_explicito": {"ok_vertical": eq["ok_vertical"],
                                 "ok_horizontal": eq["ok_horizontal"],
                                 "ok_momentos": eq["ok_momentos"]},
        "comparacion": {"n_magnitudes": len(filas),
                        "filas_OK": sum(1 for r in filas if r["estado"] == "OK"),
                        "errores_maximos": max_err},
        "escrito_en": [str(jp), str(cp), str(mp), str(fp)]}, ensure_ascii=False,
        indent=2))
    return 0 if ok_all else 1


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    edificio = "I"
    if "--edificio" in args:
        edificio = args[args.index("--edificio") + 1]
    return run(edificio)


if __name__ == "__main__":
    raise SystemExit(main())