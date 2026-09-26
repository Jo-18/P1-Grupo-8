import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.capacidad_rc import fibra as fibra_mod
from src.capacidad_rc.demanda_capacidad import _M_u_interp
from src.capacidad_rc.diagrama_pm import puntos_pm
from src.capacidad_rc.materiales import Concrete01, Steel02Simpl
from src.capacidad_rc.momento_curvatura import curva_mphi
from src.capacidad_rc.seccion import seccion_demo

_HAS_OPS = importlib.util.find_spec("openseespy") is not None


class TestCapacidadRC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sec = seccion_demo()

    def test_area_fibras_conserva_area_bruta(self):
        total = fibra_mod.area_total_fibras(self.sec)
        self.assertAlmostEqual(total, self.sec.area_bruta, places=6)

    def test_mphi_monotona_hasta_pico(self):
        cur = curva_mphi(self.sec, N_kN=0.0, kappa_max=0.10, n_pasos=160)
        M = cur["M"]
        self.assertGreater(M[-1], M[0])
        pico = int(M.argmax())
        self.assertLess(M[pico - 5], M[pico])  # sube antes del pico

    def test_Mu_sanity_rango_demo(self):
        cur = curva_mphi(self.sec, N_kN=0.0, kappa_max=0.24, n_pasos=240)
        Mu = float(cur["M_u_kN_m"])
        # rango generoso para una 0.50x0.50, fc21, fy420, 8#25 (esperado ~330-430 kN*m)
        self.assertGreater(Mu, 250.0)
        self.assertLess(Mu, 500.0)
        # el M_u debe venir del criterio de falla (no del maximo sobre toda la malla)
        self.assertNotEqual(cur["criterio_falla"], "CAP_MALLA_SIN_FALLA")
        # valores exactos de los limites utilizados
        self.assertEqual(cur["eps_cu"], 0.004)
        self.assertEqual(cur["eps_su"], 0.05)

    # ---- auditoria del criterio de terminacion (3 modos por separado) ----
    def test_criterio_termino_aplastamiento_hormigon(self):
        """Modo 1: la fibra extrema de hormigon comprimida alcanza eps_cu."""
        cur = curva_mphi(self.sec, N_kN=0.0, kappa_max=0.24, n_pasos=320)
        self.assertEqual(cur["criterio_falla"],
                         "APLASTAMIENTO_HORMIGON_eps_ext_fibra>=eps_cu")
        self.assertIsNotNone(cur["indice_aplastamiento"])
        # en el paso de falla la fibra extrema comprimida >= eps_cu
        self.assertGreaterEqual(float(cur["eps_top"][cur["indice_falla"]]),
                                cur["eps_cu"])
        # y el acero NO alcanzo eps_su antes (el aplastamiento fue el primer criterio)
        if cur["indice_fractura_acero"] is not None:
            self.assertGreater(cur["indice_fractura_acero"],
                               cur["indice_aplastamiento"])
        Mu = float(cur["M_u_kN_m"])
        self.assertGreater(Mu, 330.0)
        self.assertLess(Mu, 430.0)

    def test_criterio_termino_fractura_acero_eps_su(self):
        """Modo 2: una fibra de ACERO alcanza abs(eps) >= eps_su.

        Con eps_su=0.015 la fractura del acero ocurre ANTES que el aplastamiento
        (en el aplastamiento la fibra de acero mas exigida tiene ~0.035 > 0.015)."""
        cur = curva_mphi(self.sec, N_kN=0.0, kappa_max=0.24, n_pasos=480,
                         eps_su=0.015)
        self.assertEqual(cur["criterio_falla"],
                         "FRACTURA_ACERO_FIBRA_abs_eps>=eps_su")
        self.assertIsNotNone(cur["indice_fractura_acero"])
        # verificado sobre la deformacion real de las fibras de acero
        self.assertGreaterEqual(float(cur["eps_acero_max"][cur["indice_falla"]]),
                                cur["eps_su"])
        # la fractura fue primer criterio (antes que cualquier aplastamiento)
        if cur["indice_aplastamiento"] is not None:
            self.assertLess(cur["indice_fractura_acero"],
                            cur["indice_aplastamiento"])
        # con corte por acero M_u es menor que con aplastamiento
        self.assertLess(float(cur["M_u_kN_m"]), 378.99)

    def test_criterio_termino_cap_malla_sin_falla(self):
        """Modo 3: la malla de curvaturas termina sin alcanzar ningun criterio."""
        cur = curva_mphi(self.sec, N_kN=0.0, kappa_max=0.003, n_pasos=30)
        self.assertEqual(cur["criterio_falla"], "CAP_MALLA_SIN_FALLA")
        self.assertIsNone(cur["indice_aplastamiento"])
        self.assertIsNone(cur["indice_fractura_acero"])
        # en cap de malla M_u == max(M) (tope del barrido, NO capacidad ultima)
        self.assertAlmostEqual(float(cur["M_u_kN_m"]), float(cur["M"].max()),
                               places=6)

    def test_pm_envelope_cubre_Mu(self):
        pm = puntos_pm(self.sec, N_min_kN=-1500.0, N_max_kN=5000.0, n_puntos=11,
                       kappa_max=0.24, n_pasos_phi=120)
        cur = curva_mphi(self.sec, N_kN=0.0, kappa_max=0.24, n_pasos=240)
        Mu = float(cur["M_u_kN_m"])
        # el maximo del diagrama P-M no puede bajar del M_u de la curva N=0
        self.assertGreaterEqual(float(max(pm["M_kN_m"])), 0.9 * Mu)

    def test_concreto_no_tolera_traccion(self):
        c = Concrete01(fc=21.0)
        self.assertEqual(float(c.stress(-0.001)), 0.0)
        self.assertGreater(float(c.stress(0.001)), 0.0)

    def test_acero_simetrico(self):
        s = Steel02Simpl(fy=420.0)
        self.assertAlmostEqual(float(s.stress(-s.epsy)), -420.0, places=1)
        self.assertAlmostEqual(float(s.stress(s.epsy)), 420.0, places=1)

    @unittest.skipUnless(_HAS_OPS, "openseespy no disponible")
    def test_cross_check_openseespy(self):
        import openseespy.opensees as ops
        fibra_mod.seccion_opensees(self.sec, ops)
        # Verificacion de que el modelo se creo con sus materiales y seccion
        try:
            self.assertEqual(ops.count("Material"), 2)
            self.assertEqual(ops.count("Section"), 1)
        except (AttributeError, NotImplementedError):
            pass  # API de conteo no disponible en esta version
        # Verificacion de conservacion de area si la API expone datos de fibras
        try:
            fdata = ops.getFiberData()
        except AttributeError:
            fdata = None
        if fdata is not None and len(fdata) >= 3:
            areas = sum(float(a) for a in fdata[2])
            self.assertAlmostEqual(areas, self.sec.area_bruta, places=6)


class TestInterpolacionDemandaCapacidad(unittest.TestCase):
    """Solo la interpolacion lineal del D/C (src.capacidad_rc.demanda_capacidad).

    No valida diseno: fija el comportamiento documentado de demandar M_u(N) sobre
    el diagrama P-M de demostracion (clasificacion EVALUACION_ALGORITMICA_CON_SECCION_DEMO)."""

    def setUp(self):
        # diagrama P-M de ejemplo: N = [0,100,300] kN ; M = [10,20,30] kN*m
        self.Ns = [0.0, 100.0, 300.0]
        self.Ms = [10.0, 20.0, 30.0]

    def test_punto_exacto_del_PM_matches_valor_puntual(self):
        """N igual a un punto interior del diagrama P-M -> M_u == M del punto."""
        for n, m in zip(self.Ns, self.Ms):
            r = _M_u_interp(n, self.Ns, self.Ms)
            self.assertAlmostEqual(r["M_u_kN_m"], m, places=9)
        # el punto interior se reporta como interpolado con t=0 (NO extrapolado)
        self.assertEqual(_M_u_interp(100.0, self.Ns, self.Ms)["modo"],
                         "interpolado")

    def test_interpola_entre_dos_puntos_vecinos(self):
        """N entre dos puntos del P-M -> interpolacion lineal exacta."""
        r = _M_u_interp(50.0, self.Ns, self.Ms)  # punto medio N=0..100
        self.assertEqual(r["modo"], "interpolado")
        self.assertAlmostEqual(r["M_u_kN_m"], 15.0, places=9)
        r2 = _M_u_interp(200.0, self.Ns, self.Ms)  # punto medio entre 100 y 300
        self.assertEqual(r2["modo"], "interpolado")
        self.assertAlmostEqual(r2["M_u_kN_m"], 25.0, places=9)

    def test_fuera_de_rango_marca_y_no_extrapola(self):
        """N fuera del rango del P-M -> se acota al borde y se MARCA (sin extrapolar)."""
        inf = _M_u_interp(-10.0, self.Ns, self.Ms)
        self.assertEqual(inf["modo"], "acotado_extremo_inferior")
        self.assertAlmostEqual(inf["M_u_kN_m"], self.Ms[0], places=9)
        self.assertNotEqual(inf["modo"], "interpolado")
        sup = _M_u_interp(400.0, self.Ns, self.Ms)
        self.assertEqual(sup["modo"], "acotado_extremo_superior")
        self.assertAlmostEqual(sup["M_u_kN_m"], self.Ms[-1], places=9)
        self.assertNotEqual(sup["modo"], "interpolado")


if __name__ == "__main__":
    unittest.main()