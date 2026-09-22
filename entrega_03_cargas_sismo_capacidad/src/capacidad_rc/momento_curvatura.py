"""Curva momento-curvatura (M-phi) por integracion de fibras.

Metodo: deformaciones compatibles eps(y) = eps_ct + kappa*y (y en [-h/2,+h/2],
compresion positiva en +y). Para cada curvatura kappa se resuelve la deformacion en
el centro eps_ct tal que la resultante axial de las fibras N_int = N (carga axial
aplicada, compresion positiva). Con eps_ct definido, M = sum(sigma*A*y) alrededor
del eje centroidal (y=0). Unidades: kappa [1/m], M [kN*m], N [kN].

Criterios de terminacion (se evaluan SOBRE LAS FIBRAS DE LA MALLA, compresion + en +y):

  1. APLASTAMIENTO del hormigon: la fibra extrema de hormigon comprimida (extremo
     fisico de la seccion y=+h/2) alcanza eps >= eps_cu (eps_cu = deformacion de
     aplastamiento del hormigon; por defecto el epsu del material Concrete01 = 0.004).
  2. FRACTURA del acero: UNA fibra de acero alcanza abs(eps) >= eps_su (eps_su =
     deformacion ultima supuesta del acero; 0.05 por defecto, documentado como
     supuesto). Se comprueba la deformacion REAL de cada fibra de acero (no la fibra
     extrema de hormigon).
  3. Si la malla de curvaturas termina sin alcanzar ninguno de los anteriores, el
     punto se marca `CAP_MALLA_SIN_FALLA` y M_u = max(M) (tope del barrido; NO es
     capacidad ultima confirmada).

Se identifica por separado el PRIMER criterio alcanzado (menor indice); en empate
indice ==, se reporta el aplastamiento (criterio 1) como convencion de seccion RC.
"""

from __future__ import annotations

import numpy as np


def _resultante(seccion, eps_ct, kappa, MPa_a_kN_m2=1000.0):
    """N_int (kN) y M (kN*m) para la distribucion eps = eps_ct + kappa*y."""
    ys, _, areas, tags = _fibras_del(seccion)
    eps = eps_ct + kappa * ys
    sigma = np.zeros_like(eps, dtype=float)
    conc = tags == 1
    acero = tags == 2
    sigma[conc] = seccion.hormigon.stress(eps[conc])
    sigma[acero] = seccion.acero.stress(eps[acero])
    f = sigma * MPa_a_kN_m2 * areas  # kN por fibra (1 MPa = 1000 kN/m2)
    N = float(f.sum())
    M = float((f * ys).sum())
    return N, M


def _fibras_del(seccion):
    from src.capacidad_rc.fibra import fibras
    return fibras(seccion)


def curva_mphi(seccion, N_kN: float, kappa_max: float = 0.08,
               n_pasos: int = 200, eps_ct_lim: tuple[float, float] = (-0.20, 0.08),
               eps_cu: float | None = None, eps_su: float = 0.05):
    """Devuelve dict con arreglos kappa, M, eps_top, eps_bottom, eps_acero_max,
    y_neutra y los puntos de falla (`M_u_kN_m`, `kappa_u_1_m`, `criterio_falla`,
    `indice_falla`, `indice_aplastamiento`, `indice_fractura_acero`).

    eps_cu: deformacion de aplastamiento del hormigon (default: hormigon.epsu).
    eps_su: deformacion ultima supuesta del acero (check sobre fibras de acero).
    """
    eps_cu = float(eps_cu) if eps_cu is not None else float(seccion.hormigon.epsu)
    h = seccion.h
    ys, _, _, tags = _fibras_del(seccion)
    ys_acero = ys[tags == 2]
    lo, hi = eps_ct_lim
    ks = np.linspace(0.0, kappa_max, n_pasos)
    Ms = np.zeros(n_pasos)
    et = np.zeros(n_pasos)          # fibra extrema de hormigon en y=+h/2 (compresion)
    eb = np.zeros(n_pasos)          # fibra extrema de hormigon en y=-h/2
    es = np.zeros(n_pasos)          # max abs(eps) en las fibras de ACERO
    yn = np.zeros(n_pasos)
    for i, kap in enumerate(ks):
        # bisection sobre eps_ct para N_int = N
        c0, c1 = lo, hi
        lo_ok = _resultante(seccion, c0, kap)[0] <= N_kN
        hi_ok = _resultante(seccion, c1, kap)[0] >= N_kN
        if not (lo_ok and hi_ok):
            # amplia el intervalo hasta cubrir la carga axial pedida
            for _ in range(80):
                c0 -= 0.05
                if _resultante(seccion, c0, kap)[0] <= N_kN:
                    break
            for _ in range(80):
                c1 += 0.02
                if _resultante(seccion, c1, kap)[0] >= N_kN:
                    break
        for _ in range(90):
            cm = 0.5 * (c0 + c1)
            Nm = _resultante(seccion, cm, kap)[0]
            if abs(Nm - N_kN) < 1e-7 * max(1.0, abs(N_kN)):
                break
            if Nm < N_kN:
                c0 = cm
            else:
                c1 = cm
        eps_ct = 0.5 * (c0 + c1)
        _, M = _resultante(seccion, eps_ct, kap)
        Ms[i] = M
        et[i] = eps_ct + kap * (+h / 2.0)   # extremo fisico comprimido de la seccion
        eb[i] = eps_ct + kap * (-h / 2.0)
        es[i] = float(np.abs(eps_ct + kap * ys_acero).max())
        yn[i] = -eps_ct / kap if kap > 0 else 0.0

    # ---- punto de falla: primer criterio alcanzado (indice menor) ----
    i_cr = next((i for i in range(n_pasos) if et[i] >= eps_cu), None)
    i_st = next((i for i in range(n_pasos) if es[i] >= eps_su), None)
    if i_cr is None and i_st is None:
        i_f = int(np.argmax(Ms))
        criterio = "CAP_MALLA_SIN_FALLA"
    elif i_st is None or (i_cr is not None and i_cr <= i_st):
        i_f = i_cr
        criterio = "APLASTAMIENTO_HORMIGON_eps_ext_fibra>=eps_cu"
    else:
        i_f = i_st
        criterio = "FRACTURA_ACERO_FIBRA_abs_eps>=eps_su"

    return {"kappa": ks, "M": Ms, "eps_top": et, "eps_bottom": eb,
            "eps_acero_max": es, "y_neutra_m": yn, "N_kN": N_kN,
            "M_u_kN_m": float(Ms[i_f]), "kappa_u_1_m": float(ks[i_f]),
            "indice_falla": i_f, "criterio_falla": criterio,
            "indice_aplastamiento": i_cr, "indice_fractura_acero": i_st,
            "eps_cu": float(eps_cu), "eps_su": float(eps_su)}


def esfuerzos_fibras_punto(seccion, kappa: float, N_kN: float) -> dict:
    """Estado de fibras en un punto concreto (para figura/trazabilidad)."""
    lo, hi = (-0.20, 0.08)
    c0, c1 = lo, hi
    for _ in range(150):
        cm = 0.5 * (c0 + c1)
        if abs(_resultante(seccion, cm, kappa)[0] - N_kN) < 1e-7 * max(1.0, abs(N_kN)):
            break
        if _resultante(seccion, cm, kappa)[0] < N_kN:
            c0 = cm
        else:
            c1 = cm
    ys, zs, areas, tags = _fibras_del(seccion)
    eps_ct = 0.5 * (c0 + c1)
    eps = eps_ct + kappa * ys
    sigma = np.zeros_like(eps)
    conc = tags == 1
    ste = tags == 2
    sigma[conc] = seccion.hormigon.stress(eps[conc])
    sigma[ste] = seccion.acero.stress(eps[ste])
    return {"ys": ys.tolist(), "zs": zs.tolist(), "areas_m2": areas.tolist(),
            "tags": tags.tolist(), "eps": eps.tolist(),
            "sigma_MPa": sigma.tolist(), "eps_ct": eps_ct}