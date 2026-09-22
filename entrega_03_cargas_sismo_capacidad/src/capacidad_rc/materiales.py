"""Materiales uniaxiales: hormigon (Concrete01) y acero (Steel02 simplificado).

Convencion: deformacion POSITIVA = compresion; esfuerzos en MPa.
Stress(fuerza)/strain: eps es compresion positiva.
"""

from __future__ import annotations

import numpy as np


class Concrete01:
    """Hormigon no confinado (descendente). fc en MPa (compresion), fcu en MPa.

    Ascenso parabolico (Hognestad) hasta fc en eps0; luego rama lineal hasta
    fcu en epsu; al pasar epsu queda fcu (plastico residual conservador).
    En traccion (eps<0) no toma esfuerzo.
    """

    def __init__(self, fc: float, eps0: float | None = None,
                 epsu: float = 0.004, fcu: float | None = None):
        self.fc = float(fc)
        self.fcu = float(fcu) if fcu is not None else 0.85 * float(fc)
        self.eps0 = float(eps0) if eps0 is not None else (2.0 * abs(fc) / 21538.0)
        self.epsu = float(epsu)
        self.nombre = "Concrete01"

    def stress(self, eps) -> np.ndarray:
        eps = np.asarray(eps, dtype=float)
        s = np.zeros_like(eps)
        m1 = (eps > 0.0) & (eps < self.eps0)
        m2 = (eps >= self.eps0) & (eps <= self.epsu)
        m3 = eps > self.epsu
        s[m1] = self.fc * (2.0 * eps[m1] / self.eps0 - (eps[m1] / self.eps0) ** 2)
        s[m2] = self.fc - (self.fc - self.fcu) * (eps[m2] - self.eps0) / \
            (self.epsu - self.eps0)
        s[m3] = self.fcu
        return s

    def a_cm_escala(self):
        return self.stress


class Steel02Simpl:
    """Acero elastoplastico con endurecimiento lineal (simplificacion de Steel02).

    fy en MPa, Es en MPa, Ep = rigidez post-fluencia (Ep > 0). Simetrico en
    traccion/compresion (convencion: la funcion devuelve con signo; el llamador
    usa la propia convencion de compresion positiva para el hormigon).
    """

    def __init__(self, fy: float, Es: float = 200000.0, Ep: float = 2000.0):
        self.fy = float(fy)
        self.Es = float(Es)
        self.Ep = float(Ep)
        self.epsy = float(fy) / self.Es
        self.nombre = "Steel02Simpl"

    def stress(self, eps) -> np.ndarray:
        eps = np.asarray(eps, dtype=float)
        s = np.zeros_like(eps, dtype=float)
        el = np.abs(eps) <= self.epsy
        s[el] = self.Es * eps[el]
        pl = ~el
        s[pl] = np.sign(eps[pl]) * (self.fy + self.Ep * (np.abs(eps[pl]) - self.epsy))
        return s


def modulo_concreto_secante(fc_mpa: float) -> float:
    """Ec = 4700*sqrt(fc) segun ACI en MPa (referencia de trabajo)."""
    return 4700.0 * np.sqrt(abs(fc_mpa))