"""Diagrama P-M (primeros puntos): para cada carga axial N (compresion positiva),
el maximo momento de la curva M-phi es la capacidad a flexion. Convencion:
N [kN] compresion positiva, M [kN*m] positivo con compresion en +y."""

from __future__ import annotations

import numpy as np

from src.capacidad_rc.momento_curvatura import curva_mphi


def puntos_pm(seccion, N_min_kN, N_max_kN, n_puntos: int = 21,
              kappa_max: float = 0.12, n_pasos_phi: int = 120,
              eps_su: float = 0.05) -> dict:
    Ns = np.linspace(N_min_kN, N_max_kN, n_puntos)
    Ms = np.zeros(n_puntos)
    criterios = []
    fallo = []
    for i, N in enumerate(Ns):
        try:
            cur = curva_mphi(seccion, N_kN=float(N), kappa_max=kappa_max,
                             n_pasos=n_pasos_phi, eps_su=eps_su)
            Mu_n = cur.get("M_u_kN_m")
            Ms[i] = float(Mu_n) if Mu_n is not None else float(np.max(cur["M"]))
            criterios.append(cur.get("criterio_falla", "?"))
        except Exception as exc:  # pragma: no cover - puntos extremos
            Ms[i] = np.nan
            criterios.append(None)
            fallo.append({"N_kN": float(N), "motivo": str(exc)})
    return {"N_kN": Ns.tolist(), "M_kN_m": Ms.tolist(),
            "criterios_falla": criterios,
            "fallos": fallo, "N_min_kN": N_min_kN, "N_max_kN": N_max_kN,
            "eps_cu": float(seccion.hormigon.epsu), "eps_su": float(eps_su)}