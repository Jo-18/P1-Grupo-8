"""Aceptacion geometrica del overlay de esfuerzos FE frente a la geometria del viewer.

Mide que las tuberias del overlay se superpongan a las barras estructurales reales
del viewer (misma esencia que el chequeo envelope/centroide en C#, pero en Python
contra las fuentes lab_data/edificios/{I,II}/geometry/*.json).

Base documentada:
  * frame de coords           : p_i_unity = (u, cota, v) local, sin Placement
  * tolerancia emparejamiento : TOL = 2e-3 m (mismo criterio del exportador)
  * envolvente                : bbox del viewer inflado (0.5 m horizontal, 3.5 m
                                vertical; los "stub" descienden hasta cota -7.01
                                vs nivel base CP1S -4.01, por eso el margen Y).
"""

import json
import math
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.unity_esfuerzos.exportar_esfuerzos_para_viewer import (
    generar,
    leer_geometria_viewer,
)

TOL = 2e-3          # m, tolerancia documentada de emparejamiento (exportador)
MARGEN_H = 0.5      # m, inflado horizontal de la envolvente
MARGEN_V = 3.5      # m, inflado vertical de la envolvente (stubs bajo CP1S)


def dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def dist2d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def bbox(puntos):
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    zs = [p[2] for p in puntos]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def extremos_overlay_vs_viewer(edificio):
    """-> lista de (error_m, RMS_acum) por elemento 1A1.

    Para columna: la posicion del viewer es la base; se compara el plano (u,v) de
    AMBOS extremos FE y la cota_i con la base (el extremo j es el tope de la columna,
    su altura NO es error).
    Para viga: se comparan los extremos 3D FE contra pts[0]/pts[-1] del viewer.
    """
    d = generar(edificio)
    geo = leer_geometria_viewer(edificio)
    for e in d["elementos"]:
        c = e["correspondencia"]
        if c["estado"] != "1A1":
            continue
        g = geo[c["viewer_nivel"]]
        pi, pj = e["p_i_unity"], e["p_j_unity"]
        if e["tipo"] == "columna":
            pos = g["columnas"][c["viewer_id"]]
            yield max(dist2d((pi[0], pi[2]), (pos[0], pos[2])),
                      dist2d((pj[0], pj[2]), (pos[0], pos[2]))), 1
            yield abs(pi[1] - pos[1]), 1
        else:
            pts = g["vigas"][c["viewer_id"]]
            a, b = pts[0], pts[-1]
            yield min(dist(pi, a), dist(pi, b)), 1
            yield min(dist(pj, a), dist(pj, b)), 1


class TestExtremosYCorrespondencia(unittest.TestCase):
    """1A1: extremos del overlay == extremos del elemento del viewer (tolerancia documentada)."""

    def test_extremos_1A1_coinciden_con_viewer(self):
        errores = []
        total = 0
        for edificio in ("I", "II"):
            for er, n in extremos_overlay_vs_viewer(edificio):
                errores.append(er)
                total += n
        self.assertGreater(total, 100, "no hay correspondencias 1A1 suficientes")
        max_err = max(errores)
        rms = math.sqrt(sum(er * er for er in errores) / len(errores))
        # Los puntos FE copian las coords fuente; las vigas/columnas del viewer se
        # construyen de la misma fuente, asi que la coincidencia es subcentimetrica.
        self.assertLessEqual(max_err, 5 * TOL, f"max error {max_err:.4f} m > {5 * TOL} m")
        self.assertLessEqual(rms, 2 * TOL, f"RMS {rms:.4f} m > {2 * TOL} m")

    def test_error_1A1_reportado(self):
        # Reporte del error maximo y RMS en metros para el informe antes/despues.
        acc = []
        total = 0
        for edificio in ("I", "II"):
            for er, n in extremos_overlay_vs_viewer(edificio):
                acc.append(er)
                total += n
        rms = math.sqrt(sum(er * er for er in acc) / len(acc))
        max_err = max(acc)
        print(f"\n[geom-overlay] 1A1: {total} extremos, max={max_err:.4f} m, RMS={rms:.4f} m")
        self.assertTrue(max_err <= 5 * TOL)


class TestEnvolventeYCentroide(unittest.TestCase):
    @staticmethod
    def _puntos_viewer(geo):
        pts = []
        for g in geo.values():
            for pos in g["columnas"].values():
                pts.append(pos)
            for v in g["vigas"].values():
                pts.extend(v)
            for m in g["muros"].values():
                pts.extend(m)
        return pts

    def test_bbox_centroide_FE_vs_viewer(self):
        for edificio in ("I", "II"):
            d = generar(edificio)
            geo = leer_geometria_viewer(edificio)
            vpts = self._puntos_viewer(geo)
            fpts = [p for e in d["elementos"] for p in (e["p_i_unity"], e["p_j_unity"])]
            vb = bbox(vpts)
            fb = bbox(fpts)
            for etiqueta, i in (("U(X)", 0), ("cota(Y)", 1), ("V(Z)", 2)):
                vc = (vb[2 * i] + vb[2 * i + 1]) / 2
                fc = (fb[2 * i] + fb[2 * i + 1]) / 2
                self.assertLessEqual(abs(vc - fc), 1.5,
                                     f"{edificio} centroide {etiqueta}: FE={fc:.3f} viewer={vc:.3f}")
            print(f"\n[geom-overlay] {edificio}: centroides FE/viewer OK")

    def test_envolvente_espacial_no_fuera(self):
        # Criterio minimo: ninguna tuberia del overlay fuera de la envolvente del edificio
        # (inflada); si la doble transformacion estuviera activa, los prismas volarian fuera.
        for edificio in ("I", "II"):
            d = generar(edificio)
            geo = leer_geometria_viewer(edificio)
            vb = bbox(self._puntos_viewer(geo))
            lim = (
                vb[0] - MARGEN_H, vb[1] + MARGEN_H,
                vb[2] - MARGEN_V, vb[3] + MARGEN_V,
                vb[4] - MARGEN_H, vb[5] + MARGEN_H,
            )
            fuera = []
            for e in d["elementos"]:
                for p in (e["p_i_unity"], e["p_j_unity"]):
                    if not (lim[0] <= p[0] <= lim[1] and lim[2] <= p[1] <= lim[3]
                            and lim[4] <= p[2] <= lim[5]):
                        fuera.append((e["tag"], e["tipo"], tuple(p)))
            self.assertEqual(fuera, [], f"{edificio}: elementos fuera de envolvente {fuera[:5]}")

    def test_sin_correspondencia_en_posicion_real(self):
        # Elementos SIN_CORRESPONDENCIA_VIEWER se dibujan como overlay independiente
        # pero deben quedar en su posicion REAL dentro del edificio (ninguna nube flotante).
        for edificio in ("I", "II"):
            d = generar(edificio)
            geo = leer_geometria_viewer(edificio)
            vb = bbox(self._puntos_viewer(geo))
            lim = (
                vb[0] - MARGEN_H, vb[1] + MARGEN_H,
                vb[2] - MARGEN_V, vb[3] + MARGEN_V,
                vb[4] - MARGEN_H, vb[5] + MARGEN_H,
            )
            for e in d["elementos"]:
                if e["correspondencia"]["estado"] != "SIN_CORRESPONDENCIA_VIEWER":
                    continue
                for p in (e["p_i_unity"], e["p_j_unity"]):
                    self.assertTrue(
                        lim[0] <= p[0] <= lim[1] and lim[2] <= p[1] <= lim[3]
                        and lim[4] <= p[2] <= lim[5],
                        f"{edificio} tag {e['tag']} ({e['tipo']}) fuera de escala real: {p}")


class TestFormaEstructural(unittest.TestCase):
    """Columna FE vertical; viga FE descansando en la cota del piso y sobre una viga del viewer."""

    def test_columnas_verticales(self):
        malos = []
        for edificio in ("I", "II"):
            d = generar(edificio)
            for e in d["elementos"]:
                if e["tipo"] != "columna":
                    continue
                pi, pj = e["p_i_unity"], e["p_j_unity"]
                dh = math.hypot(pj[0] - pi[0], pj[2] - pi[2])  # (u, v) plano
                if dh > TOL:
                    malos.append((edificio, e["tag"], dh))
        self.assertEqual(malos, [], f"columnas FE con deriva horizontal > {TOL} m: {malos[:5]}")

    def test_vigas_en_cota_del_piso(self):
        malos = []
        for edificio in ("I", "II"):
            d = generar(edificio)
            geo = leer_geometria_viewer(edificio)
            for e in d["elementos"]:
                if e["tipo"] != "viga":
                    continue
                cota_nivel = geo[e["nivel"]]["cota"] if e["nivel"] in geo else None
                if cota_nivel is None:
                    continue
                cota_i = e["p_i_unity"][1]
                cota_j = e["p_j_unity"][1]
                if abs(cota_i - cota_nivel) > 0.1 or abs(cota_j - cota_nivel) > 0.1:
                    malos.append((edificio, e["tag"], e["nivel"], cota_i, cota_j, cota_nivel))
        self.assertEqual(
            malos, [],
            f"vigas FE fuera de la cota de su piso (tol 0.1 m): {malos[:5]}")

    def test_vigas_FE_descansan_sobre_viga_viewer(self):
        # La viga FE 1A1 comparte extremos con la viga del viewer (ya verificado en el
        # test de extremos). Aqui se confirma ademas alineacion: el par de extremos FE
        # debe caer dentro de la caja 2D (u,v) de la viga del viewer (inflanada TOL).
        desalineadas = []
        total = 0
        for edificio in ("I", "II"):
            d = generar(edificio)
            geo = leer_geometria_viewer(edificio)
            for e in d["elementos"]:
                if e["tipo"] != "viga" or e["correspondencia"]["estado"] != "1A1":
                    continue
                total += 1
                g = geo[e["correspondencia"]["viewer_nivel"]]
                pts = g["vigas"][e["correspondencia"]["viewer_id"]]
                a, b = pts[0], pts[-1]
                for p in (e["p_i_unity"], e["p_j_unity"]):
                    caja = (
                        min(a[0], b[0]) - TOL, max(a[0], b[0]) + TOL,
                        min(a[2], b[2]) - TOL, max(a[2], b[2]) + TOL,
                    )
                    if not (caja[0] <= p[0] <= caja[1] and caja[2] <= p[2] <= caja[3]):
                        desalineadas.append((edificio, e["tag"], tuple(p)))
        self.assertGreater(total, 50, "pocas vigas 1A1 para este chequeo")
        self.assertEqual(desalineadas, [], f"vigas 1A1 desalineadas de su viga: {desalineadas[:5]}")


if __name__ == "__main__":
    unittest.main()