"""Cierre de las 4 islas (apoyos artificiales) del perfil MODELO_FE_COMPLETO_FUNCIONAL
(EI). Tras la regularizacion fisica (hito 2026-09-15):

  * islas 206/209/212 (vigas del portico del cielo del subterraneo H_y0601, H_y1625,
    V_x0060): apoyo real documentado = enlace excentrico corto a columnas de la
    reticula que bajan a cimentacion (desfase 0.30-0.43 m, dentro del pie de columna);
  * isla 457 (grillaje de la torre sobre la losa P4): apoyo real documentado = patas de
    la torre V.E.I. y columnas P4 (G3/H3/GS7/HS7), conectadas con el mismo conector
    corto elastico de rigidez elevada (desfase 0.23-0.42 m).

Verificaciones (por cada isla se retira la restriccion artificial y se aplica una carga
vertical unitaria de 1 kN SOBRE esa isla; debe llegar a los apoyos reales de base):

  - cero apoyos artificiales (marco.apoyos_losa == []);
  - ninguna componente queda sin camino a la cimentacion (adyacencia de elementos +
    enlaces rigidos reales);
  - 1 kN en cada nodo representativo de isla -> suma de reacciones en base = 1.0 kN.

Ejecutar:  python -X utf8 -m tests.islas.test_cierre_islas
"""
import sys
import os
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "..", "analisis_estructural", "edificio_I", "src"))

from src.modelo_fiel import modelo_fe_completo as M  # noqa: E402
from analisis.fe import resolver as RESv            # noqa: E402

# (tag isla, nivel de carga, descripcion, registro de enlace esperado)
ISLAS = [
    (206, "CP1S", "viga H_y0601 (portico cielo sotano)",  "cp1s_eccentric_links"),
    (209, "CP1S", "viga H_y1625 (portico cielo sotano)",  "cp1s_eccentric_links"),
    (212, "CP1S", "viga V_x0060 (portico cielo sotano)",  "cp1s_eccentric_links"),
    (457, "P4",   "grillaje torre sobre losa P4",         "p4_grillaje_links"),
]
COORDS = {206: (0.35, 15.9, -4.01), 209: (0.35, 0.25, -4.01),
          212: (0.25, 15.8, -4.01), 457: (20.3, 20.15, 11.83)}


class TestCierreIslas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.marco = M.MarcoFECompleto(M.GF.cargar_todos())
        cls.marco.construir()

    def _componentes_sin_base(self):
        m = self.marco
        base = set(m._base_fixed)
        adj = {int(t): set() for t in m.nodes.values()}
        for r in list(m.muros_elem) + list(m.columnas) + list(m.vigas_elem):
            i, j = int(r["nodo_i"]), int(r["nodo_j"])
            adj.setdefault(i, set()).add(j)
            adj.setdefault(j, set()).add(i)
        for r in m.enlaces_rigidos_reales:
            adj[r["master"]].add(r["esclavo"])
            adj[r["esclavo"]].add(r["master"])
        flotando = []
        vistos = set()
        for t in adj:
            if t in vistos or (t in base and adj[t]):
                continue
            comp = set()
            pila = [t]
            while pila:
                x = pila.pop()
                if x in comp:
                    continue
                comp.add(x)
                pila.extend(adj.get(x, ()))
            vistos |= comp
            if not (base & comp):
                flotando.append(comp)
        return flotando

    def test_cero_apoyos_artificiales(self):
        self.assertEqual(len(self.marco.apoyos_losa), 0,
                         "deben retirarse las restricciones artificiales (w-fix)")

    def test_cero_componentes_sin_camino_a_base(self):
        flotando = self._componentes_sin_base()
        self.assertEqual(len(flotando), 0,
                         [sorted(c) for c in flotando])

    def test_aislados_y_preflight(self):
        pre = self.marco.preflight()
        self.assertTrue(pre["ok"])

    def test_enlaces_documentados_presentes(self):
        self.assertEqual(len(self.marco.cp1s_eccentric_links), 6)
        self.assertEqual(len(self.marco.p4_grillaje_links), 10)
        for rl in self.marco.p4_grillaje_links:
            self.assertLessEqual(rl["desfase_m"], 0.45,
                                 "enlace del grillaje dentro del pie del elemento")

    def test_carga_unitaria_por_isla(self):
        """1 kN vertical sobre cada antigua isla -> reaccion total en base = 1.0 kN
        (lapso sin apoyo artificial: el camino es la conexion fisica real documentada)."""
        for tag, nivel, desc, registro in ISLAS:
            with self.subTest(isla=tag, nivel=nivel):
                self.assertIn(tag, [int(t) for t in self.marco.nodes.values()] or [],
                              "nodo isla debe existir")
                m = M.MarcoFECompleto(M.GF.cargar_todos())
                m.construir()
                cargas = {nivel: {tag: [0.0, 0.0, -1.0, 0.0, 0.0, 0.0]}}
                sol = RESv.resolver(m, cargas)
                self.assertTrue(sol["ok"], desc + " -> analyze ok")
                # la isla NO es apoyo: libre de fijacion artificial y de fijacion de
                # base; la carga viaja por su conexion fisica real hasta la base.
                self.assertNotIn(tag, m._apoyos_losa_fixed,
                                 desc + " -> sin w-fix artificial")
                self.assertNotIn(tag, m._base_fixed,
                                 desc + " -> sin fijacion de base en el nodo isla")
                Rz = sum(r[2] for r in sol["reacciones"].values())
                self.assertAlmostEqual(Rz, 1.0, places=3,
                                       msg=desc + f" (Rz suma base = {Rz:.6f})")


def _main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCierreIslas)
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    res = runner.run(suite)
    raise SystemExit(0 if res.wasSuccessful() else 1)


if __name__ == "__main__":
    _main()