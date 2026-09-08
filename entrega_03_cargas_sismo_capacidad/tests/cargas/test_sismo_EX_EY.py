import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class TestSismoEXEY(unittest.TestCase):
    def test_parametros_null_bloquean(self):
        from src.cargas import sismo_EX_EY as s
        cfg = s.leer_config()
        faltantes = s.requeridos_faltantes(cfg)
        self.assertGreaterEqual(len(faltantes), 5)  # nada documentado aun
        self.assertIn("zona_sismica", faltantes)
        self.assertIn("factor_R", faltantes)
        self.assertIn("peso_sismico_W_kN", faltantes)

    def test_ejecucion_aborta_con_parametros_null(self):
        from src.cargas import sismo_EX_EY as s
        with self.assertRaises(SystemExit):
            s.check_requisitos()

    def test_verificador_carga_lateral_total(self):
        from src.cargas import sismo_EX_EY as s
        r = s.verificar_carga_lateral_total([100.0, 200.0, 150.0])
        self.assertAlmostEqual(r["total_lateral_kN"], 450.0)

    def test_verificador_corte_basal(self):
        from src.cargas import sismo_EX_EY as s
        r = s.verificar_corte_basal([100.0, 200.0, 150.0], corte_basal=450.0)
        self.assertEqual(r["estado"], "OK")
        r2 = s.verificar_corte_basal([100.0, 200.0, 150.0], corte_basal=999.0)
        self.assertEqual(r2["estado"], "ERROR")

    def test_verificador_sentido_deformada(self):
        from src.cargas import sismo_EX_EY as s
        r = s.verificar_sentido_deformada([100.0, 200.0], [1.0, 1.0])
        self.assertEqual(r["estado"], "OK")
        r2 = s.verificar_sentido_deformada([100.0, 200.0], [1.0, -1.0])
        self.assertEqual(r2["estado"], "ERROR(SENTIDO_INVERSO)")

    def test_verificador_torsion(self):
        from src.cargas import sismo_EX_EY as s
        r = s.verificar_torsion_piso([0.02, 0.04], limite=0.05)
        self.assertEqual(r["estado"], "OK")
        r2 = s.verificar_torsion_piso([0.09], limite=0.05)
        self.assertEqual(r2["estado"], "ERROR(TORSION_FUERA_LIMITE)")
        self.assertEqual(s.verificar_torsion_piso([], 0.05)["estado"], "N/D_SIN_DATOS_DE_TORSION")


if __name__ == "__main__":
    unittest.main()