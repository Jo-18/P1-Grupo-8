"""Armaduras y capacidad de vigas y columnas de hormigon armado (ACI 318-19).

Las armaduras se leen de data/armaduras.json (tipo por seccion + excepciones
por elemento, editable en VS Code o desde Unity). Con las fuerzas del analisis
se calcula para cada elemento:

  Vigas     phiMn+ (armadura inferior), phiMn- (superior + suple de apoyo),
            phiVn = 0.75 (Vc + Vs) con los estribos de apoyo; demanda Mu+, Mu-, Vu
  Columnas  curva P-M de diseno (compatibilidad de deformaciones, phi 0.65-0.90,
            Pmax = 0.80 phi P0) y phiVn con Vc segun el axial; demanda (Pu, Mu), Vu

y el factor de uso DCR = demanda / capacidad (el mayor de flexion y corte).

Notacion de barras: "4φ22", "4f22", "4x22" o "2φ22+2φ25"; estribos "Eφ10a10"
(1 estribo = 2 ramas), "EDφ10a10" (estribo doble = 4 ramas) o "φ10a20".
Unidades: kN, m, MPa.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMADURAS_PATH = ROOT / "data" / "armaduras.json"

FC_MPA = 35.0      # G35
FY_MPA = 420.0     # A630-420H
ES_MPA = 200000.0
EPS_CU = 0.003


# ----------------------------------------------------------------------
# Lectura de armaduras
# ----------------------------------------------------------------------
_BARS = re.compile(r"(\d+)\s*(?:φ|ø|Ø|f|x|%%[cC])\s*(\d{1,2})", re.IGNORECASE)
_STIRRUP = re.compile(r"(ED|ET|E)?\s*(?:φ|ø|Ø|f|%%[cC])?\s*(\d{1,2})\s*(?:a|@)\s*(\d{1,3})", re.IGNORECASE)


def bars_area_mm2(text):
    """Area total [mm2] y lista de diametros de un texto como '4φ22+2φ25'."""
    area, diams = 0.0, []
    for n, d in _BARS.findall(text or ""):
        n, d = int(n), int(d)
        area += n * math.pi * d * d / 4.0
        diams += [d] * n
    return area, diams


def stirrup(text, legs_default=2):
    """(Av [mm2], s [mm], diametro) de un texto 'EDφ10a10' (ED = 4 ramas, E = 2)."""
    m = _STIRRUP.search(text or "")
    if not m:
        return 0.0, 0.0, 0
    kind, d, s_cm = (m.group(1) or "").upper(), int(m.group(2)), int(m.group(3))
    legs = 4 if kind == "ED" else 3 if kind == "ET" else legs_default
    return legs * math.pi * d * d / 4.0, s_cm * 10.0, d


def load_armaduras(path=ARMADURAS_PATH, overrides=None):
    """Armaduras por seccion y por elemento; overrides (mismo formato) tiene prioridad."""
    data = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}
    secciones = dict(data.get("secciones", {}))
    elementos = dict(data.get("elementos", {}))
    muros = dict(data.get("muros") or {})
    muros["secciones"] = dict(muros.get("secciones") or {})
    if overrides:
        for k, v in (overrides.get("secciones") or {}).items():
            secciones[k] = {**secciones.get(k, {}), **v}
        for k, v in (overrides.get("elementos") or {}).items():
            elementos[k] = {**elementos.get(k, {}), **v}
        ov_muros = overrides.get("muros") or {}
        for k, v in ov_muros.items():
            if k != "secciones":
                muros[k] = v
        for k, v in (ov_muros.get("secciones") or {}).items():
            muros["secciones"][k] = {**muros["secciones"].get(k, {}), **v}
    return {"recubrimiento_m": float(data.get("recubrimiento_m", 0.04)), "secciones": secciones, "elementos": elementos,
            "muros": muros}


def armadura_de(element, arm):
    """Armadura efectiva del elemento: la de su seccion con las excepciones del elemento."""
    base = arm["secciones"].get(element.get("sectionId"), {})
    extra = arm["elementos"].get(element.get("elementTag"), {}) or arm["elementos"].get(str(element.get("id")), {})
    return {**base, **extra}


# ----------------------------------------------------------------------
# Vigas
# ----------------------------------------------------------------------
def phi_flexion(eps_t):
    """ACI 318-19 tabla 21.2.2 (estribos): 0.65 controlada por compresion -> 0.90 por traccion."""
    if eps_t >= 0.005:
        return 0.90
    if eps_t <= FY_MPA / ES_MPA:
        return 0.65
    return 0.65 + 0.25 * (eps_t - FY_MPA / ES_MPA) / (0.005 - FY_MPA / ES_MPA)


def flexion_rectangular(b_mm, d_mm, as_mm2):
    """phiMn [kN m] de seccion rectangular con armadura de traccion (sin aporte de compresion)."""
    if as_mm2 <= 0 or d_mm <= 0:
        return 0.0, 0.0, 0.0
    a = as_mm2 * FY_MPA / (0.85 * FC_MPA * b_mm)
    c = a / 0.80                                   # beta1 = 0.80 para f'c = 35 MPa
    eps_t = EPS_CU * (d_mm - c) / c
    mn = as_mm2 * FY_MPA * (d_mm - a / 2.0) / 1e6
    phi = phi_flexion(eps_t)
    return phi * mn, mn, eps_t


def corte(b_mm, d_mm, av_mm2, s_mm, nu_kn=0.0, ag_mm2=None):
    """phiVn [kN] ACI 22.5: Vc = 0.17 (1 + Nu/(14 Ag)) sqrt(f'c) b d; Vs = Av fy d / s <= 0.66 sqrt(f'c) b d."""
    factor_n = 1.0
    if ag_mm2 and nu_kn > 0:
        factor_n = 1.0 + (nu_kn * 1000.0) / (14.0 * ag_mm2)
    vc = 0.17 * factor_n * math.sqrt(FC_MPA) * b_mm * d_mm / 1000.0
    vs = (av_mm2 * FY_MPA * d_mm / s_mm / 1000.0) if s_mm > 0 else 0.0
    vs = min(vs, 0.66 * math.sqrt(FC_MPA) * b_mm * d_mm / 1000.0)
    return 0.75 * (vc + vs), vc, vs


def capacidad_viga(element, a, recub):
    b, h = float(element["width_m"]) * 1000.0, float(element["height_m"]) * 1000.0
    as_inf, d_inf = bars_area_mm2(a.get("inferior"))
    as_sup, d_sup = bars_area_mm2(a.get("superior"))
    as_sup_apoyo, d_sa = bars_area_mm2(a.get("supleApoyo"))
    av, s, d_est = stirrup(a.get("estribosApoyo"))
    av_t, s_t, _ = stirrup(a.get("estribosTramo"))
    db_inf = max(d_inf) if d_inf else 20
    db_sup = max(d_sup + d_sa) if (d_sup or d_sa) else 20
    d_pos = h - recub * 1000.0 - d_est - db_inf / 2.0
    d_neg = h - recub * 1000.0 - d_est - db_sup / 2.0
    phi_mp, mn_p, et_p = flexion_rectangular(b, d_pos, as_inf)
    phi_mn_apoyo, mn_n, et_n = flexion_rectangular(b, d_neg, as_sup + as_sup_apoyo)
    phi_v, vc, vs = corte(b, d_pos, av, s)
    phi_v_t, _, _ = corte(b, d_pos, av_t, s_t) if s_t > 0 else (phi_v, 0, 0)
    return {
        "phiMn_pos_kN_m": phi_mp, "phiMn_neg_kN_m": phi_mn_apoyo, "phiVn_apoyo_kN": phi_v, "phiVn_tramo_kN": phi_v_t,
        "As_inf_mm2": as_inf, "As_sup_apoyo_mm2": as_sup + as_sup_apoyo, "d_mm": d_pos,
        "eps_t_pos": et_p, "eps_t_neg": et_n, "Vc_kN": vc, "Vs_kN": vs,
    }


# ----------------------------------------------------------------------
# Columnas: curva P-M de diseno por compatibilidad de deformaciones
# ----------------------------------------------------------------------
def barras_perimetro(b_mm, h_mm, n, recub_c_mm):
    """n barras repartidas en el perimetro de un rectangulo (4 esquinas + intermedias)."""
    xs, ys = b_mm / 2.0 - recub_c_mm, h_mm / 2.0 - recub_c_mm
    pts = [(-xs, -ys), (xs, -ys), (xs, ys), (-xs, ys)]
    resto = max(0, n - 4)
    # reparte las intermedias entre las 4 caras en proporcion a su largo
    caras = [((-xs, -ys), (xs, -ys)), ((xs, -ys), (xs, ys)), ((xs, ys), (-xs, ys)), ((-xs, ys), (-xs, -ys))]
    por_cara = [resto // 4 + (1 if k < resto % 4 else 0) for k in range(4)]
    for (p0, p1), k in zip(caras, por_cara):
        for i in range(1, k + 1):
            t = i / (k + 1)
            pts.append((p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1])))
    return pts[:max(n, 4)] if n >= 4 else pts[:n]


def curva_pm_barras(b_mm, h_mm, barras, n_puntos=40):
    """Curva de diseno (phiPn, phiMn) ACI 318-19 de una seccion rectangular b x h por compatibilidad de
    deformaciones, flexion en la direccion de h (simetrica). barras = [(y_mm, area_mm2)] con y medido desde
    el centroide. P compresion +. Sirve para columnas (h = lado) y muros en su plano (h = largo L)."""
    ast = sum(a for _, a in barras)
    ag = b_mm * h_mm
    p0 = (0.85 * FC_MPA * (ag - ast) + FY_MPA * ast) / 1000.0
    pmax = 0.80 * 0.65 * p0
    puntos = []
    d_t = h_mm / 2.0 + max(abs(y) for y, _ in barras)
    for k in range(n_puntos + 1):
        # c desde 0.05 h (traccion) hasta 3 h (compresion)
        c = h_mm * (0.05 + 2.95 * (k / n_puntos) ** 1.6)
        a = min(0.80 * c, h_mm)
        cc = 0.85 * FC_MPA * a * b_mm / 1000.0
        pn = cc
        mn = cc * (h_mm / 2.0 - a / 2.0) / 1000.0
        for y, a_bar in barras:
            dist = h_mm / 2.0 - y            # desde la fibra comprimida
            eps = EPS_CU * (c - dist) / c
            fs = max(-FY_MPA, min(FY_MPA, eps * ES_MPA))
            if dist <= a:                    # barra dentro del bloque: descontar hormigon desplazado
                fs -= 0.85 * FC_MPA
            f = fs * a_bar / 1000.0
            pn += f
            mn += f * y / 1000.0               # brazo: y desde el centroide (= h/2 - dist)
        eps_t = EPS_CU * (d_t - c) / c
        phi = phi_flexion(eps_t)
        puntos.append({"P_kN": min(phi * pn, pmax), "M_kN_m": phi * abs(mn), "Pn_kN": pn, "Mn_kN_m": abs(mn), "phi": phi})
    # traccion pura
    puntos.append({"P_kN": -0.9 * FY_MPA * ast / 1000.0, "M_kN_m": 0.0, "Pn_kN": -FY_MPA * ast / 1000.0, "Mn_kN_m": 0.0, "phi": 0.9})
    puntos.append({"P_kN": pmax, "M_kN_m": 0.0, "Pn_kN": p0, "Mn_kN_m": 0.0, "phi": 0.65})
    puntos.sort(key=lambda q: q["P_kN"])
    return {"puntos": puntos, "P0_kN": p0, "phiPmax_kN": pmax, "Ast_mm2": ast, "n_barras": len(barras)}


def curva_pm_columna(b_mm, h_mm, n_barras, diam_mm, recub_m=0.04, d_estribo=10, n_puntos=40, diametros=None):
    """Curva de diseno (phiPn, phiMn) en flexion sobre el eje fuerte (simetrica). P compresion +.
    diametros: diametro de cada barra en el orden de barras_perimetro (primero las 4 esquinas, luego las
    intermedias cara por cara); asi '4φ28+16φ36' deja φ28 en las esquinas y φ36 en las caras. Sin
    diametros todas las barras son de diam_mm. El centro de las barras queda a recubrimiento + estribo +
    el radio de la barra mayor."""
    diams = list(diametros) if diametros and len(diametros) == n_barras else [diam_mm] * n_barras
    recub_c = recub_m * 1000.0 + d_estribo + max(diams) / 2.0
    pos = barras_perimetro(b_mm, h_mm, n_barras, recub_c)
    barras = [(y, math.pi * d * d / 4.0) for (_, y), d in zip(pos, diams)]
    return curva_pm_barras(b_mm, h_mm, barras, n_puntos)


# ----------------------------------------------------------------------
# Muros: curva P-M en su plano con la armadura de borde y la malla central
# ----------------------------------------------------------------------
def barras_muro(t_mm, l_mm, n_borde, d_borde=40, d_malla=10, s_malla_mm=200.0, s_filas_mm=100.0,
                recub_m=0.04, d_estribo=10):
    """Barras de un muro t x L en su plano: [(y_mm desde el centro del muro, area_mm2)].
    En cada extremo hay n_borde barras de borde en filas de 2 (una por cara) separadas s_filas_mm; la
    primera fila queda a recubrimiento + estribo + radio de la barra del borde del muro. Entre las dos
    zonas de borde va la malla doble (2 barras por posicion) cada s_malla_mm como maximo."""
    filas = max(1, int(n_borde) // 2)
    a_borde = math.pi * d_borde * d_borde / 4.0
    a_malla = math.pi * d_malla * d_malla / 4.0
    c = recub_m * 1000.0 + d_estribo + d_borde / 2.0
    xs_borde = [c + k * s_filas_mm for k in range(filas)]
    barras = []
    for x in xs_borde:
        barras.append((l_mm / 2.0 - x, 2 * a_borde))          # extremo 1
        barras.append((-(l_mm / 2.0 - x), 2 * a_borde))       # extremo 2
    x_a, x_b = xs_borde[-1], l_mm - xs_borde[-1]
    if x_b - x_a > s_malla_mm:
        n_m = int(math.ceil((x_b - x_a) / s_malla_mm)) - 1
        for j in range(1, n_m + 1):
            x = x_a + (x_b - x_a) * j / (n_m + 1)
            barras.append((l_mm / 2.0 - x, 2 * a_malla))
    return barras


def curva_pm_muro(t_mm, l_mm, n_borde, d_borde=40, d_malla=10, s_malla_mm=200.0, s_filas_mm=100.0,
                  recub_m=0.04, d_estribo=10, n_puntos=40):
    """Curva de diseno ACI 318-19 del muro en su plano (misma formulacion que las columnas)."""
    barras = barras_muro(t_mm, l_mm, n_borde, d_borde, d_malla, s_malla_mm, s_filas_mm, recub_m, d_estribo)
    curva = curva_pm_barras(t_mm, l_mm, barras, n_puntos)
    curva["n_barras_borde"] = 2 * (int(n_borde) // 2) * 2
    curva["n_barras_malla"] = len(barras) * 2 - curva["n_barras_borde"]
    return curva


def _clave_muro(t_m, l_m):
    return "{:.2f}x{:.3f}".format(float(t_m), float(l_m))


def armadura_muro(t_m, l_m, arm):
    """Armadura del muro t x L segun armaduras.json (seccion 'muros'): exacta por clave 't x L' o, si la
    seccion no esta, la del muro definido de igual espesor y largo mas parecido (o de cualquier espesor)."""
    muros = arm.get("muros") or {}
    secciones = muros.get("secciones") or {}
    base = {"malla": muros.get("malla", "2φ10a20"), "separacionFilasBorde_m": muros.get("separacionFilasBorde_m", 0.10)}
    a = secciones.get(_clave_muro(t_m, l_m))
    if a is None and secciones:
        def dist(k):
            tk, lk = (float(v) for v in k.split("x"))
            return (0 if abs(tk - float(t_m)) < 0.005 else 1, abs(lk - float(l_m)))
        k = min(secciones, key=dist)
        a = {**secciones[k], "fuente": f"sin dato: se usa la del muro {k} (largo mas parecido)"}
    return {**base, **(a or {})}


def curvas_muros(walls, arm, recub=None):
    """Curvas P-M de diseno de los muros del modelo con su armadura real.
    Devuelve (curvas en el formato pmCurves del JSON de Unity, {indice de muro (1..n): sectionId})."""
    recub = arm.get("recubrimiento_m", 0.04) if recub is None else recub
    curvas, por_muro = {}, {}
    for i, w in enumerate(walls or []):
        t, L = float(w.get("grosor", 0.0)), float(w.get("longitud", 0.0))
        if t <= 0 or L <= 0:
            continue
        a = armadura_muro(t, L, arm)
        _, d_borde = bars_area_mm2(a.get("bordes", ""))
        n_borde = len(d_borde)
        db = max(d_borde) if d_borde else 40
        av, s_malla, d_malla = stirrup(a.get("malla", "2φ10a20").replace("2φ", "Eφ").replace("2f", "Ef"))
        s_filas = float(a.get("separacionFilasBorde_m", 0.10)) * 1000.0
        sid = "W_{:d}x{:d}_{:d}f{:d}".format(int(round(t * 1000)), int(round(L * 1000)), n_borde, int(db))
        por_muro[i + 1] = sid
        if sid in curvas:
            continue
        cur = curva_pm_muro(t * 1000.0, L * 1000.0, n_borde, db, d_malla or 10, s_malla or 200.0, s_filas, recub, 10)
        ag = t * L * 1e6
        curvas[sid] = {
            "sectionId": sid, "elementType": "muro", "b_m": t, "h_m": L, "fc_MPa": FC_MPA, "fy_MPa": FY_MPA,
            "steelBars": cur["n_barras_borde"] + cur["n_barras_malla"], "barDiameter_mm": float(db),
            "Ast_mm2": round(cur["Ast_mm2"], 1), "rho_percent": 100.0 * cur["Ast_mm2"] / ag, "Po_kN": cur["P0_kN"],
            "interpretation": f"Curva de DISENO (phiPn, phiMn) ACI 318-19 del muro t={t:.2f} m, L={L:.3f} m en su plano: "
                              f"{n_borde}φ{int(db)} en cada extremo (filas de 2 cada {s_filas:.0f} mm) y malla doble "
                              f"φ{int(d_malla or 10)}a{int((s_malla or 200) / 10)}; phi 0.65-0.90, phiPmax = 0.80 phi P0. "
                              f"Armadura: {a.get('fuente', 'armaduras.json')}.",
            "points": [{"label": "", "P_kN": round(q["P_kN"], 1), "M_kN_m": round(q["M_kN_m"], 1)} for q in cur["puntos"]],
        }
    return list(curvas.values()), por_muro


def m_capacidad(puntos, p):
    """Mayor phiMn de la envolvente para la carga axial p (0 si p queda fuera)."""
    best = 0.0
    pts = sorted(puntos, key=lambda q: q["P_kN"])
    if p < pts[0]["P_kN"] or p > pts[-1]["P_kN"]:
        return 0.0
    for q0, q1 in zip(pts, pts[1:]):
        if q0["P_kN"] <= p <= q1["P_kN"] and q1["P_kN"] > q0["P_kN"]:
            t = (p - q0["P_kN"]) / (q1["P_kN"] - q0["P_kN"])
            best = max(best, q0["M_kN_m"] + t * (q1["M_kN_m"] - q0["M_kN_m"]))
    return best


def capacidad_columna(element, a, recub):
    b, h = float(element["width_m"]) * 1000.0, float(element["height_m"]) * 1000.0
    _, diams = bars_area_mm2(a.get("barras"))
    av, s, d_est = stirrup(a.get("estribos"), legs_default=2)
    n = len(diams)
    diam = max(diams) if diams else 25
    curva = curva_pm_columna(b, h, n, diam, recub, d_est or 10, diametros=diams or None)
    d = h - recub * 1000.0 - (d_est or 10) - diam / 2.0
    return {"curva": curva, "b_mm": b, "h_mm": h, "d_mm": d, "Av_mm2": av, "s_mm": s, "Ag_mm2": b * h}


# ----------------------------------------------------------------------
# Demanda y factor de uso
# ----------------------------------------------------------------------
def evaluar(element, forces_by_combo, w_by_combo, length, arm):
    """Capacidad y factor de uso del elemento con las fuerzas del analisis (12 componentes locales).
    w_by_combo: carga repartida vertical del tramo [kN/m] por combo (para el momento al centro)."""
    a = armadura_de(element, arm)
    if not a:
        return None
    recub = arm["recubrimiento_m"]
    tipo = element.get("type")
    out = {"armadura": a, "porCombo": []}
    if tipo == "viga":
        cap = capacidad_viga(element, a, recub)
        out.update({k: round(v, 3) for k, v in cap.items()})
        worst = None
        for combo, f in forces_by_combo.items():
            w = w_by_combo.get(combo, 0.0)
            mu_pos = mu_neg = vu = 0.0
            for i in range(21):
                t = i / 20.0
                my = -(1 - t) * f[4] + t * f[10] - w * length * length * t * (1 - t) / 2.0
                vz = -(1 - t) * f[2] + t * f[8]
                # convencion de diseno: My local < 0 = traccion abajo (M+)
                mu_pos = max(mu_pos, -my)
                mu_neg = max(mu_neg, my)
                vu = max(vu, abs(vz))
            dcr_f = max(mu_pos / cap["phiMn_pos_kN_m"] if cap["phiMn_pos_kN_m"] > 0 else 9.99,
                        mu_neg / cap["phiMn_neg_kN_m"] if cap["phiMn_neg_kN_m"] > 0 else 9.99)
            dcr_v = vu / cap["phiVn_apoyo_kN"] if cap["phiVn_apoyo_kN"] > 0 else 9.99
            row = {"combo": combo, "Mu_pos": round(mu_pos, 2), "Mu_neg": round(mu_neg, 2), "Vu": round(vu, 2),
                   "DCR_flexion": round(dcr_f, 3), "DCR_corte": round(dcr_v, 3)}
            out["porCombo"].append(row)
            if worst is None or max(dcr_f, dcr_v) > max(worst["DCR_flexion"], worst["DCR_corte"]):
                worst = row
    elif tipo == "columna" and element.get("material") != "acero":
        cap = capacidad_columna(element, a, recub)
        out.update({"P0_kN": round(cap["curva"]["P0_kN"], 1), "phiPmax_kN": round(cap["curva"]["phiPmax_kN"], 1),
                    "Ast_mm2": round(cap["curva"]["Ast_mm2"], 1), "curvaPM": [
                        {"P_kN": round(q["P_kN"], 1), "M_kN_m": round(q["M_kN_m"], 1)} for q in cap["curva"]["puntos"]]})
        worst = None
        for combo, f in forces_by_combo.items():
            pu = 0.5 * (f[0] - f[6])                 # compresion +
            mu = max(math.hypot(f[4], f[5]), math.hypot(f[10], f[11]))
            vu = max(math.hypot(f[1], f[2]), math.hypot(f[7], f[8]))
            mcap = m_capacidad(cap["curva"]["puntos"], pu)
            phi_v, _, _ = corte(cap["b_mm"], cap["d_mm"], cap["Av_mm2"], cap["s_mm"], max(pu, 0.0), cap["Ag_mm2"])
            dcr_pm = mu / mcap if mcap > 0 else 9.99
            dcr_v = vu / phi_v if phi_v > 0 else 9.99
            row = {"combo": combo, "Pu": round(pu, 1), "Mu": round(mu, 1), "phiMn_at_Pu": round(mcap, 1), "Vu": round(vu, 1),
                   "phiVn": round(phi_v, 1), "DCR_PM": round(dcr_pm, 3), "DCR_corte": round(dcr_v, 3)}
            out["porCombo"].append(row)
            if worst is None or max(dcr_pm, dcr_v) > max(worst["DCR_PM"], worst["DCR_corte"]):
                worst = row
    else:
        return None
    if worst:
        out["DCR"] = round(max(v for k, v in worst.items() if k.startswith("DCR")), 3)
        out["comboGobernante"] = worst["combo"]
    return out


def merge_into_file(overrides_path, path=ARMADURAS_PATH):
    """Agrega los cambios (mismo formato) a data/armaduras.json conservando descripcion y origen."""
    base = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {"secciones": {}, "elementos": {}}
    ov = json.loads(Path(overrides_path).read_text(encoding="utf-8"))
    for key in ("secciones", "elementos"):
        base.setdefault(key, {})
        for k, v in (ov.get(key) or {}).items():
            base[key][k] = {**base[key].get(k, {}), **v}
    Path(path).write_text(json.dumps(base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return base


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Armaduras ACI 318: fusionar cambios en data/armaduras.json")
    parser.add_argument("--merge", type=Path, required=True, help="JSON con cambios {secciones, elementos}")
    parser.add_argument("--out", type=Path, default=None, help="(lo usa PythonJob) archivo de confirmacion")
    a = parser.parse_args()
    merged = merge_into_file(a.merge)
    print(f"armaduras.json: {len(merged['secciones'])} secciones, {len(merged['elementos'])} excepciones por elemento")
    if a.out:
        Path(a.out).write_text("ok", encoding="utf-8")
