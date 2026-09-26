"""Seccion de columna RC arbitraria: geometria, materiales y armadura.

Ejes y convenciones usadas en TODO el modulo:
  - y: eje de flexion (profundidad h). Comprende y en [-h/2, +h/2]; compresion en +y.
  - z: eje perpendicular a la flexion (ancho b).
  - N positivo = compresion (kN). M_z positivo con compresion en +y.
  - esfuerzos en MPa; areas en m2; unidades finales kN y kN*m.
"""

from __future__ import annotations

from src.capacidad_rc.materiales import (Concrete01, Steel02Simpl)

DEMOSTRACION_ARBITRARIA = True
NOTA_DEMO = ("Seccion de demostracion ARBITRARIA: NO corresponde a ninguna seccion "
             "real del Edificio I ni del Edificio II.")


class Barra:
    def __init__(self, y: float, z: float, As: float):
        self.y = float(y)
        self.z = float(z)
        self.As = float(As)  # m2


class SeccionRC:
    def __init__(self, h: float, b: float, rec: float, barras: list[Barra],
                 hormigon: Concrete01, acero: Steel02Simpl,
                 n_celdas_y: int = 14, n_celdas_z: int = 14,
                 etiqueta: str = "DEMOSTRACION"):
        self.h = float(h)
        self.b = float(b)
        self.rec = float(rec)
        self.barras = barras
        self.hormigon = hormigon
        self.acero = acero
        self.n_celdas_y = int(n_celdas_y)
        self.n_celdas_z = int(n_celdas_z)
        self.etiqueta = etiqueta
        self.As_total = sum(bar.As for bar in barras)
        self.area_bruta = self.h * self.b

    def fibra_concreto(self):
        """Malla de fibras de hormigon (patron de Fiber Section). Devuelve
        arreglos y (m), area (m2), y descuenta el acero de la fibra mas cercana."""
        import numpy as np
        ny, nz = self.n_celdas_y, self.n_celdas_z
        ys = np.linspace(-self.h / 2 + self.h / (2 * ny), self.h / 2 - self.h / (2 * ny), ny)
        zs = np.linspace(-self.b / 2 + self.b / (2 * nz), self.b / 2 - self.b / (2 * nz), nz)
        yv, zv = np.meshgrid(ys, zs, indexing="ij")
        area_celda = (self.h / ny) * (self.b / nz)
        areas = np.full_like(yv, area_celda, dtype=float)
        # descuento del acero en la fibra mas cercana a cada barra (evita doble conteo)
        for bar in self.barras:
            i = int(np.argmin(np.abs(ys - bar.y)))
            j = int(np.argmin(np.abs(zs - bar.z)))
            areas[i, j] -= bar.As
            if areas[i, j] < 0.0:
                raise RuntimeError("Area de fibra negativa: reducir celdas o dimensiones")
        return yv.ravel(), zv.ravel(), areas.ravel()

    def fibra_acero(self):
        import numpy as np
        return (np.array([bar.y for bar in self.barras]),
                np.array([bar.z for bar in self.barras]),
                np.array([bar.As for bar in self.barras]))

    def resumen(self) -> dict:
        yc, zc, ac = self.fibra_concreto()
        ya, za, aa = self.fibra_acero()
        return {
            "etiqueta": self.etiqueta,
            "DEMOSTRACION_ARBITRARIA": DEMOSTRACION_ARBITRARIA,
            "nota": NOTA_DEMO,
            "h_m": self.h, "b_m": self.b, "recubrimiento_m": self.rec,
            "n_barras": len(self.barras), "As_total_m2": round(self.As_total, 6),
            "area_bruta_m2": round(self.area_bruta, 6),
            "area_concreto_fibras_m2": round(float(ac.sum()), 6),
            "area_acero_fibras_m2": round(float(aa.sum()), 6),
            "n_fibras_concreto": int(len(ac)), "n_fibras_acero": int(len(aa)),
            "materiales": {
                "hormigon": {"tipo": self.hormigon.nombre, "fc_MPa": self.hormigon.fc,
                             "fcu_MPa": self.hormigon.fcu,
                             "eps0": round(self.hormigon.eps0, 6),
                             "eps_cu": self.hormigon.epsu},
                "acero": {"tipo": self.acero.nombre, "fy_MPa": self.acero.fy,
                          "Es_MPa": self.acero.Es}},
            "barras": [{"y_m": b.y, "z_m": b.z, "As_m2": round(b.As, 6)}
                       for b in self.barras]}


def seccion_con_armado(h, b, rec, diam_m, n_cn, n_en_medio_cn_Y, n_en_medio_cn_Z,
                       fc_mpa, fy_mpa) -> SeccionRC:
    """Constructor generico con distribucion simetrica de barras:
    esquinas (4) + n_en_medio_cn_Y barras centradas en caras +y/-y +
    n_en_medio_cn_Z en caras +z/-z."""
    As = 3.141592653589793 * (diam_m / 2.0) ** 2
    horm = Concrete01(fc=fc_mpa, fcu=0.85 * fc_mpa, eps0=0.002, epsu=0.004)
    acero = Steel02Simpl(fy=fy_mpa, Es=200000.0, Ep=2000.0)
    yp = h / 2 - rec
    zp = b / 2 - rec
    barras = [Barra(yp, zp, As), Barra(yp, -zp, As),
              Barra(-yp, zp, As), Barra(-yp, -zp, As)]
    paso_y = (2 * zp) / (n_en_medio_cn_Y + 1)
    for k in range(1, n_en_medio_cn_Y + 1):
        z = -zp + k * paso_y
        barras += [Barra(yp, z, As), Barra(-yp, z, As)]
    paso_z = (2 * yp) / (n_en_medio_cn_Z + 1)
    for k in range(1, n_en_medio_cn_Z + 1):
        y = -yp + k * paso_z
        barras += [Barra(y, zp, As), Barra(y, -zp, As)]
    return SeccionRC(h, b, rec, barras, horm, acero, etiqueta=f"{h}x{b}m")