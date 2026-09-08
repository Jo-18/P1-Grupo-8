"""Verificacion intermedia de superposicion G + Q del Edificio I (Entrega 3).

Ejecuta TRES casos FE sobre EXACTAMENTE el mismo modelo lineal del Edificio I
(mismo `Marco`, mismas geometrias/restricciones/materiales, rigidez_mult=1e3,
subdivision_vigas=1, mismo orden de DOF):

  1. corrida G          : PP + PM.ADIC (sin SC)          -> F_total_G   ~ PP + PM.
  2. corrida Q          : SOBRECARGA q_Q (SC) sola, G ausente (caso base Q).
  3. corrida EXPLICITA  : G + lambda_Q*Q en UN solo patron de carga (resolve el
                          sistema K*u = F_G + lambda_Q*F_Q en una unica corrida).

y compara la SUPERPOSICION  R_sup = lambda_G*R_G + lambda_Q*R_Q  contra la corrida
explicita (mismo modelo) en desplazamiento, reaccion, fuerza axial y momento de
extremo, con tolerancia relativa por magnitud.

Controles previos (ABORTAN si fallan):
  * compatibilidad de los tres casos base: mismos nodos y coordenadas, mismos
    elementos y conectividad (con secciones/materiales), mismas restricciones
    (base fija, diafragma, enlaces rigidos), mismo orden de creacion de DOF,
    mismas claves y convenciones de resultados.
  * las cargas Q del patron explicito coinciden con la corrida Q separada.

Salidas (con un unico comando):
  results/superposicion/verificacion_intermedia_G_Q_EI.json  (evidencia completa)
  results/superposicion/verificacion_intermedia_G_Q_EI.csv   (tabla por magnitud)
  results/superposicion/verificacion_intermedia_G_Q_EI.md    (informe legible)
  figures/superposicion/verificacion_intermedia_G_Q_EI.png   (figura sup vs explicito)

Uso:
  python -X utf8 -m src.cargas.verificacion_intermedia_G_Q_EI --demo
  (--demo usa q_Q=2.0 kN/m2 marcada DEMOSTRACION_ARBITRARIA; --q_q X personaliza)

Estado: la verificacion FINAL completa (G+Q+EX+EY) sigue bloqueada por
BLOQUEADO_POR_PARAMETROS_SISMICOS; esta es la verificacion INTERMEDIA con los
dos casos base disponibles (G y Q), marcada IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO.
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
sys.path.insert(0, str(EI_SRC))

from src.cargas.caso_Q_EI import leer_config, q_efectivo  # noqa: E402,F401

from analisis.fe import geometria_fe as GF                 # noqa: E402
from analisis.fe import resolver as RESOL                  # noqa: E402
from analisis.fe import tributaria as TB                   # noqa: E402
from analisis.fe import cargas_correlacionadas as CC       # noqa: E402
from analisis.fe.hipotesis import niveles_ordenados        # noqa: E402
from analisis.fe.marco import Marco                        # noqa: E402

TOL_COMPARACION_REL = 1e-4       # error relativo maximo por magnitud (sup vs expl)
TOL_EQUILIBRIO_VERT = 0.05       # 5 %
FLOOR = {"m": 1e-6, "kN": 1e-3, "kN_m": 1e-2}
INDICES_MOMENTO = (4, 5, 10, 11)  # Mz_i, My_i, Mz_j, My_j en localForce(12)


def _lambdas() -> dict:
    """lambda_G y lambda_Q del conjunto de demostracion (config/superposicion.json)."""
    d = json.loads(CONFIG_SUPER.read_text(encoding="utf-8"))["conjunto_demostracion"]
    return {"G": float(d["lambda_G"]), "Q": float(d["lambda_Q"]),
            "etiqueta": d["etiqueta"]}


def _nuevo_marco():
    niveles = GF.cargar_todos()
    marco = Marco(niveles, rigidez_mult=1.0e3)
    marco.subdivision_vigas = 1
    marco.construir()
    return marco


def _cargas_G(marco) -> dict:
    """PP + PM.ADIC por nivel (mismo flujo que el caso G del laboratorio)."""
    por_nivel = CC.cargas_por_losa_por_nivel()
    cargas_nodales = {}
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
        cargas_nodales[cod] = cn
    return cargas_nodales


def _cargas_Q(marco, q_Q) -> dict:
    """SOBRECARGA uniforme q_Q sola (PP=0, PM=0) sobre la geometria tributaria.

    Replica exacta del reparto del caso Q (mismas losas netas, mismos soportes,
    mismo `distribuir_losa` y mismos pesos por nodo que la corrida G), para que la
    combinacion explicita G + lambda_Q*Q sea exactamente consistente."""
    cargas_nodales = {}
    for cod in niveles_ordenados():
        nivelFE = marco.niveles[cod]
        soportes = TB._receptor_lineas(nivelFE)
        cargas = {}
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
                    cur = cargas.get(tag, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                    cur[2] -= F * w
                    cargas[tag] = cur
        cargas_nodales[cod] = cargas
    return cargas_nodales


def _corrida_G():
    marco = _nuevo_marco()
    cargas = _cargas_G(marco)
    sol = RESOL.resolver(marco, cargas)
    return marco, sol, cargas


def _corrida_Q(info_q):
    """Reutiliza el caso Q verificado (caso_Q_EI): mismo modelo, G ausente, checks."""
    from src.cargas.caso_Q_EI import construir_y_resolver
    marco, sol, cargas, _repartos, checks = construir_y_resolver(info_q)
    return marco, sol, cargas, checks


def _corrida_explicita(info_q):
    """G + lambda_Q*Q en un UNICO patron de carga (una sola corrida FE)."""
    lam = _lambdas()
    marco = _nuevo_marco()
    G = _cargas_G(marco)
    Q = _cargas_Q(marco, info_q["q_Q_kN_m2"])
    exp = {}
    for cod in niveles_ordenados():
        g, q = G[cod], Q[cod]
        d = {}
        for t in set(g) | set(q):
            a = g.get(t, [0.0] * 6)
            b = q.get(t, [0.0] * 6)
            d[t] = [a[i] + lam["Q"] * b[i] for i in range(6)]
        exp[cod] = d
    sol = RESOL.resolver(marco, exp)
    return marco, sol, exp, G, Q


def _firma(marco) -> dict:
    """Firma determinista del modelo: nodos, DOF, elementos, restricciones,
    materiales/secciones que deben coincidir entre corridas."""
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
            "rigidez_mult": float(marco.rigidez_mult),
            "subdivision_vigas": int(marco.subdivision_vigas)}


def _compatibilidad(sols, cargas_q_corrida, cargas_q_explicita, firmas) -> dict:
    """Compatibilidad entre los tres casos base con ABORTE si hay discrepancia."""
    salida = {"matrices": {}, "claves_resultados": {}, "cargas_Q_consistentes": None}
    base = firmas["G"]
    difs = {c: [k for k in base if firmas[c].get(k) != base.get(k)]
            for c in firmas if c != "G"}
    if any(difs.values()):
        raise SystemExit("ABORTE_COMPATIBILIDAD: el modelo difiere entre corridas. "
                         "Discrepancias: %s"
                         % json.dumps(difs, ensure_ascii=False))
    salida["matrices"] = {"n_nodos": {c: firmas[c]["n_nodos"] for c in firmas},
                          "firmas_iguales": True,
                          "discrepancias": 0}

    # mismas claves y convenciones de resultados (secuencia de DOF 1..6 por nodo)
    claves = {}
    for c in ("G", "Q", "explicita"):
        s = sols[c]
        claves[c] = {"n_disp": len(s["desplazamientos"]),
                     "n_reacciones": len(s["reacciones"]),
                     "n_fuerzas": len(s["fuerzas"]["local"]),
                     "tags_disp_iguales": None,
                     "len_disp_6": all(len(v) == 6 for v in s["desplazamientos"].values()),
                     "len_fuerzas_12": all(len(v) == 12 for v in s["fuerzas"]["local"].values())}
    claves["G"]["tags_disp_iguales"] = sorted(str(k) for k in sols["G"]["desplazamientos"]) == \
        sorted(str(k) for k in sols["explicita"]["desplazamientos"])
    ok_claves = (claves["G"]["n_disp"] == claves["Q"]["n_disp"] == claves["explicita"]["n_disp"]
                 and claves["G"]["n_fuerzas"] == claves["Q"]["n_fuerzas"]
                 == claves["explicita"]["n_fuerzas"]
                 and all(claves[c]["len_disp_6"] and claves[c]["len_fuerzas_12"]
                         for c in claves)
                 and claves["G"]["tags_disp_iguales"])
    salida["claves_resultados"] = claves
    if not ok_claves:
        raise SystemExit("ABORTE_COMPATIBILIDAD: claves/convenciones de resultados "
                         "difieren entre corridas: %s" % json.dumps(claves))

    # las cargas Q del patron explicito deben coincidir con la corrida Q separada
    max_dif = 0.0
    for cod in niveles_ordenados():
        a = cargas_q_corrida.get(cod, {})
        b = cargas_q_explicita.get(cod, {})
        for t in set(a) | set(b):
            va = a.get(t, [0.0] * 6)
            vb = b.get(t, [0.0] * 6)
            for i in range(6):
                max_dif = max(max_dif, abs(va[i] - vb[i]))
    ok_q = max_dif <= 1e-9
    salida["cargas_Q_consistentes"] = {"max_diferencia_kN": round(max_dif, 12),
                                       "ok": ok_q}
    if not ok_q:
        raise SystemExit("ABORTE_COMPATIBILIDAD: el patron Q explicito no coincide "
                         "con la corrida Q separada (max dif %.3e)." % max_dif)
    return salida


def _equilibrio(marco, cargas_nodales, sol, etiqueta) -> dict:
    Pz = -sol["F_total_kN"][2]
    R = sol["reacciones"]
    Rz = sum(r[2] for r in R.values())
    crit_v = abs(Rz - Pz) < TOL_EQUILIBRIO_VERT * max(abs(Pz), 1e-9)
    hor = {"Fx_kN": round(sum(r[0] for r in R.values()), 4),
           "Fy_kN": round(sum(r[1] for r in R.values()), 4)}
    ok_h = abs(hor["Fx_kN"]) < 1e-4 and abs(hor["Fy_kN"]) < 1e-4
    flat = {int(t): f for car in cargas_nodales.values() for t, f in car.items()}

    def _mom(x):
        mx = my = 0.0
        for t, f in x.items():
            u, v, _z = marco.key_of_tag[t][:3]
            mx += f[2] * v
            my += f[2] * u
        return mx, my

    mr = _mom(R)
    ml = _mom(flat)
    tol_m = TOL_EQUILIBRIO_VERT * max(abs(Pz) * 30.0, 1e-9)
    ok_m = abs(mr[0] + ml[0]) < tol_m and abs(mr[1] + ml[1]) < tol_m
    return {"caso": etiqueta, "R_z_kN": round(Rz, 4), "P_z_kN": round(Pz, 4),
            "residuo_vertical_kN": round(Rz - Pz, 4),
            "ok_vertical": crit_v,
            "horizontal": hor, "ok_horizontal": ok_h,
            "res_momentos_kN_m": [round(mr[0] + ml[0], 3), round(mr[1] + ml[1], 3)],
            "ok_momentos": ok_m}


def _fuente(Rdic, familia, id_, idx):
    if familia in ("desplazamiento",):
        return Rdic["desplazamientos"][id_][idx]
    if familia in ("reaccion",):
        return Rdic["reacciones"][id_][idx]
    if familia in ("axial", "momento"):
        return Rdic["fuerzas"]["local"][id_][idx]
    raise KeyError(familia)


def _seleccion(R, marco) -> list:
    """Seleccion documentada (>=1 de cada familia) sobre el caso EXPLICITO."""
    lam = _lambdas()
    disp = R["E"]["desplazamientos"]
    reac = R["E"]["reacciones"]
    fl = R["E"]["fuerzas"]["local"]
    beam_tags = {int(r["tag"]) for r in marco.vigas_elem}
    col_tags = {int(r["tag"]) for r in marco.columnas}
    raw = []
    # desplazamiento vertical (mayor |uz|, no trivial)
    t_uz = max(disp, key=lambda t: abs(disp[t][2]))
    raw.append((["desplazamiento", t_uz, 2, "uz", "m"],
                "Nodo %s | desplazamiento vertical" % t_uz,
                "global DOF3 (w); + = +Z (hacia arriba)"))
    # desplazamiento horizontal (mayor |ux|/|uy| de todo el modelo)
    m_h, t_h, i_h = -1.0, None, None
    for t in disp:
        for i in (0, 1):
            if abs(disp[t][i]) > m_h:
                m_h, t_h, i_h = abs(disp[t][i]), t, i
    raw.append((["desplazamiento", t_h, i_h, "ux" if i_h == 0 else "uy", "m"],
                "Nodo %s | desplazamiento horizontal" % t_h,
                "global DOF1/DOF2; + = +X/+Y"))
    # reacciones verticales (las 2 mayores |Rz|, soportes base)
    for k, t in enumerate(sorted(reac, key=lambda t: -abs(reac[t][2]))[:2]):
        raw.append((["reaccion", t, 2, "Rz", "kN"],
                    "Nodo base %s | reaccion vertical" % t,
                    "global; + = hacia arriba (equilibra la carga)"))
    # fuerza axial (elemento con mayor |N| en cualquiera de sus extremos)
    e_ax = max(fl, key=lambda e: max(abs(fl[e][0]), abs(fl[e][6])))
    for i_ext in (0, 6):
        raw.append((["axial", e_ax, i_ext, "N_i" if i_ext == 0 else "N_j", "kN"],
                    "Elemento %s | fuerza axial extremo %s" %
                    (e_ax, "i" if i_ext == 0 else "j"),
                    "localForce OpenSees indice %d; + = compresion en el extremo "
                    "(verificado: columna comprimida da + en extremo i)" % i_ext))
    # momento de extremo: el mayor de Mz_i/My_i/Mz_j/My_j (global) y el mayor de viga
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
                    "localForce indice %d; Mz/My en extremo i/j del elemento" % i))
    bbest = _max_mom(beam_tags)
    if bbest:
        _, e, i = bbest
        raw.append((["momento", e, i, _nom_mom(i), "kN_m"],
                    "Elemento %s (VIGA) | momento local de extremo" % e,
                    "localForce indice %d; Mz/My en extremo i/j del elemento" % i))

    filas = []
    for (fam, id_, idx, comp, unidad), titulo, conv in raw:
        g = _fuente(R["G"], fam, id_, idx)
        q = _fuente(R["Q"], fam, id_, idx)
        e = _fuente(R["E"], fam, id_, idx)
        sup = lam["G"] * g + lam["Q"] * q
        escala = max(abs(e), FLOOR[unidad])
        err = abs(sup - e)
        rel = err / escala if escala > 0 else (0.0 if err == 0.0 else 1.0)
        filas.append({"familia": fam, "id": id_, "componente": comp,
                      "unidad": unidad, "titulo": titulo, "convencion": conv,
                      "g": g, "q": q, "superpuesto": sup, "explicito": e,
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


def _escribir(payload, filas, eq, max_err, lam, info_q, compat):
    RES_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    jp = RES_DIR / "verificacion_intermedia_G_Q_EI.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")

    cp = RES_DIR / "verificacion_intermedia_G_Q_EI.csv"
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["familia", "id", "componente", "unidad", "convencion",
                    "G", "Q", "superpuesto", "explicito",
                    "error_abs", "error_rel", "tol_rel", "estado"])
        for r in filas:
            w.writerow([r["familia"], r["id"], r["componente"], r["unidad"],
                        r["convencion"], f"{r['g']:.6f}", f"{r['q']:.6f}",
                        f"{r['superpuesto']:.6f}", f"{r['explicito']:.6f}",
                        f"{r['error_abs']:.3e}", f"{r['error_rel']:.3e}",
                        f"{r['tolerancia_rel']:.3e}", r["estado"]])

    lineas = []
    lineas.append("# Verificacion intermedia de superposicion G + Q - Edificio I")
    lineas.append("")
    lineas.append("R_sup = lambda_G*G + lambda_Q*Q  (lambda_G=%.3g, lambda_Q=%.3g, "
                  "conjunto %s) versus la corrida EXPLICITA G + lambda_Q*Q sobre el "
                  "mismo modelo lineal." % (lam["G"], lam["Q"], lam["etiqueta"]))
    lineas.append("")
    lineas.append("caso_Q: %s (q_Q=%.3f kN/m2)" % (info_q["etiqueta"],
                                                    info_q["q_Q_kN_m2"]))
    lineas.append("")
    lineas.append("## Tabla por magnitud (seleccion documentada)")
    lineas.append("")
    lineas.append("| Familia | Descripcion | Convencion de signo | G | Q | "
                  "Superpuesto | Explicito | |Error| | Err.rel | Tol | Estado |")
    lineas.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in filas:
        conv = r["convencion"].replace("|", "/")
        lineas.append("| %s | %s | %s | %.6g | %.6g | %.6g | %.6g | %.3e | %.3e "
                      "| %.0e | %s |"
                      % (r["familia"], r["titulo"], conv, r["g"], r["q"],
                         r["superpuesto"], r["explicito"], r["error_abs"],
                         r["error_rel"], r["tolerancia_rel"], r["estado"]))
    lineas.append("")
    lineas.append("## Errores maximos por familia")
    lineas.append("")
    lineas.append("| Familia | Max |error absoluto| | Max error relativo | n |")
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
    lineas.append("## Equilibrio global de la corrida explicita")
    lineas.append("")
    lineas.append("- vertical: R_z=%.4f kN vs P_z=%.4f kN, residuo=%.4f kN, %s"
                  % (eq["R_z_kN"], eq["P_z_kN"], eq["residuo_vertical_kN"],
                     "OK" if eq["ok_vertical"] else "ERROR"))
    lineas.append("- horizontal: Fx=%.4f, Fy=%.4f, %s" % (eq["horizontal"]["Fx_kN"],
                  eq["horizontal"]["Fy_kN"], "OK" if eq["ok_horizontal"] else "ERROR"))
    lineas.append("- momentos (origen): residuo Mx=%.3f, My=%.3f kN*m, %s"
                  % (eq["res_momentos_kN_m"][0], eq["res_momentos_kN_m"][1],
                     "OK" if eq["ok_momentos"] else "ERROR"))
    lineas.append("")
    lineas.append("## Compatibilidad de los casos base")
    lineas.append("")
    lineas.append("- matrices (firmas nodos/elementos/restricciones/DOF/materiales) "
                  "identicas entre corridas: %s"
                  % ("OK" if compat["matrices"]["firmas_iguales"] else "ERROR"))
    lineas.append("- claves y convenciones de resultados identicas: %s"
                  % ("OK" if compat["claves_resultados"] else "ERROR"))
    lineas.append("- patron Q del explicito consistente con la corrida Q: %s (max "
                  "dif %.3e)"
                  % ("OK" if compat["cargas_Q_consistentes"]["ok"] else "ERROR",
                     compat["cargas_Q_consistentes"]["max_diferencia_kN"]))
    lineas.append("")
    ok_all = (eq["ok_vertical"] and eq["ok_horizontal"] and eq["ok_momentos"]
              and all(r["estado"] == "OK" for r in filas)
              and compat["matrices"]["firmas_iguales"]
              and compat["cargas_Q_consistentes"]["ok"])
    lineas.append("## Estado final")
    lineas.append("")
    lineas.append("- **%s**" % ("IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO" if ok_all
                                else "ERROR_VERIFICACION"))
    lineas.append("- notas: verificacion intermedia con los casos base G y Q "
                  "compatibles; la verificacion FINAL (G+Q+EX+EY) permanece "
                  "BLOQUEADO_POR_PARAMETROS_SISMICOS (sin parametros sismicos).")
    lineas.append("")
    mp = RES_DIR / "verificacion_intermedia_G_Q_EI.md"
    mp.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return jp, cp, mp


def _figura(filas, lam):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    n = len(filas)
    etiq = ["%s %s %s" % (r["familia"][:4], r["id"], r["componente"]) for r in filas]
    sup = [r["superpuesto"] for r in filas]
    exp = [r["explicito"] for r in filas]
    rel = [r["error_rel"] for r in filas]
    x = np.arange(n)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    ax1.bar(x - 0.2, sup, width=0.4,
            label="Superpuesto %.3gG+%.3gQ" % (lam["G"], lam["Q"]), color="#2c7bb6")
    ax1.bar(x + 0.2, exp, width=0.4, label="Explicito", color="#d7191c")
    ax1.set_xticks(x)
    ax1.set_xticklabels(etiq, rotation=45, ha="right", fontsize=7)
    ax1.set_ylabel("Magnitud (m / kN / kN*m)")
    ax1.set_title("Superposicion vs corrida explicita (mismo modelo)")
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.3)
    ax2.plot(x, rel, "o-", color="#1a9641")
    ax2.axhline(1e-4, color="#d7191c", ls="--", lw=1)
    ax2.text(0.02, 1.4e-4, "tolerancia 1e-4", color="#d7191c", fontsize=8)
    ax2.set_xticks(x)
    ax2.set_xticklabels(etiq, rotation=45, ha="right", fontsize=7)
    ax2.set_yscale("log")
    ax2.set_ylabel("Error relativo")
    ax2.set_title("Error relativo por magnitud")
    ax2.grid(alpha=0.3)
    fig.suptitle("VERIFICACION_INTERMEDIA_G_Q_EI - Edificio I", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fp = FIG_DIR / "verificacion_intermedia_G_Q_EI.png"
    fig.savefig(fp, dpi=150)
    plt.close(fig)
    return fp


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    usar_demo = "--demo" in args
    q_cli = None
    if "--q_q" in args:
        q_cli = float(args[args.index("--q_q") + 1])
    info_q = q_efectivo(leer_config(), usar_demo, q_cli)
    lam = _lambdas()

    marco_g, sol_g, cargas_g = _corrida_G()
    marco_q, sol_q, cargas_q, checks_q = _corrida_Q(info_q)
    marco_e, sol_e, cargas_e, _g2, _q2 = _corrida_explicita(info_q)
    if not (sol_g["ok"] and sol_q["ok"] and sol_e["ok"]):
        raise SystemExit(
            "ABORTE: alguna corrida fallo (analyze != 0). G=%s Q=%s EXPLICITA=%s"
            % (sol_g.get("analyze_retcode"), sol_q.get("analyze_retcode"),
               sol_e.get("analyze_retcode")))

    firmas = {"G": _firma(marco_g), "Q": _firma(marco_q), "explicita": _firma(marco_e)}
    compat = _compatibilidad({"G": sol_g, "Q": sol_q, "explicita": sol_e},
                             cargas_q, _q2, firmas)

    R = {"G": sol_g, "Q": sol_q, "E": sol_e}
    filas = _seleccion(R, marco_e)
    max_err = _max_errores(filas)
    eq = _equilibrio(marco_e, cargas_e, sol_e, "EXPLICITA G+lambda_Q*Q")

    payload = {
        "verificacion": "intermedia_G_Q_EI",
        "edificio": "I",
        "etiqueta": "IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO",
        "lambda_G": lam["G"], "lambda_Q": lam["Q"],
        "etiqueta_lambdas": lam["etiqueta"],
        "caso_Q": info_q,
        "corridas": {"G_ok": bool(sol_g["ok"]), "Q_ok": bool(sol_q["ok"]),
                     "EXPLICITA_ok": bool(sol_e["ok"])},
        "checks_caso_Q": checks_q,
        "modelo": marco_e.resumen(),
        "modelo_n_elementos": len(marco_e.columnas) + len(marco_e.vigas_elem)
                              + len(marco_e.muros_elem),
        "F_total_kN": {"G": [round(x, 6) for x in sol_g["F_total_kN"]],
                       "Q": [round(x, 6) for x in sol_q["F_total_kN"]],
                       "EXPLICITA": [round(x, 6) for x in sol_e["F_total_kN"]]},
        "compatibilidad": compat,
        "equilibrio_explicito": eq,
        "comparacion": {"tolerancia_rel": TOL_COMPARACION_REL,
                        "filas": filas, "errores_maximos": max_err},
    }

    def _redondeados(s, cargas):
        return {"desplazamientos": {str(k): [round(float(x), 9) for x in v]
                                    for k, v in s["desplazamientos"].items()},
                "reacciones": {str(k): [round(float(x), 6) for x in v]
                               for k, v in s["reacciones"].items()},
                "fuerzas_local": {str(k): [round(float(x), 6) for x in v]
                                  for k, v in s["fuerzas"]["local"].items()},
                "cargas_nodales": {cod: {str(k): [round(float(x), 6) for x in v]
                                         for k, v in car.items()}
                                   for cod, car in cargas.items()}}
    payload["resultados_por_corrida"] = {
        "G": _redondeados(sol_g, cargas_g),
        "Q": _redondeados(sol_q, cargas_q),
        "EXPLICITA": _redondeados(sol_e, cargas_e),
    }

    jp, cp, mp = _escribir(payload, filas, eq, max_err, lam, info_q, compat)
    fp = _figura(filas, lam)

    ok_all = (eq["ok_vertical"] and eq["ok_horizontal"] and eq["ok_momentos"]
              and all(r["estado"] == "OK" for r in filas)
              and compat["matrices"]["firmas_iguales"]
              and compat["cargas_Q_consistentes"]["ok"])
    print(json.dumps({
        "verificacion": "intermedia_G_Q_EI",
        "estado": "IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO" if ok_all
                  else "ERROR_VERIFICACION",
        "lambda_G": lam["G"], "lambda_Q": lam["Q"],
        "caso_Q": info_q["etiqueta"],
        "F_total_kN": payload["F_total_kN"],
        "compatibilidad": {"firmas_identicas": True,
                           "cargas_Q_consistentes": compat["cargas_Q_consistentes"]},
        "equilibrio_explicito_vertical": {"R_z_kN": eq["R_z_kN"],
                                          "P_z_kN": eq["P_z_kN"],
                                          "ok": eq["ok_vertical"]},
        "comparacion": {"n_magnitudes": len(filas),
                        "filas_OK": sum(1 for r in filas if r["estado"] == "OK"),
                        "errores_maximos": max_err},
        "escrito_en": [str(jp), str(cp), str(mp), str(fp)]}, ensure_ascii=False,
        indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())