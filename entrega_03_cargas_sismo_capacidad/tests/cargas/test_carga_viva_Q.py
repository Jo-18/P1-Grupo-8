import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # entrega_03

from src.cargas.carga_viva_Q import (aplicar_Q, leer_config, leer_catalogo_sobrecarga)
from src.comun.geometria_tributaria import cargar_geometria_tributaria

CFG = leer_config()


class TestCargaVivaQ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geom_I = cargar_geometria_tributaria("I", CFG["geometria_tributaria"]["I"])
        cls.geom_II = cargar_geometria_tributaria("II", CFG["geometria_tributaria"]["II"])

    def test_q_Q_null_sin_demo_aborta(self):
        cfg = {"q_Q": {"I": {"q_Q_kN_m2": None, "estado": "PENDIENTE"}},
               "DEMOSTRACION_ARBITRARIA": {"q_Q_kN_m2": 2.0, "marcado": True},
               "aplicada_al_modelo_FE": False, "tolerancia_rel_sum_Q": 0.005}
        with self.assertRaises(SystemExit):
            aplicar_Q("I", self.geom_I, cfg, usar_demo=False)

    def test_demo_EI_verifica_por_nivel_y_global(self):
        rep = aplicar_Q("I", self.geom_I, CFG, usar_demo=True)
        self.assertEqual(rep["global"]["estado"], "OK")
        for nivel, blk in rep["por_nivel"].items():
            if blk["area_tributaria_m2"] > 0:
                self.assertEqual(blk["estado"], "OK")
                self.assertLessEqual(blk["diferencia_rel"], CFG["tolerancia_rel_sum_Q"])
        self.assertTrue(rep["global"]["diferencia_rel"] <= CFG["tolerancia_rel_sum_Q"])

    def test_demo_EII_solo_CP2_tiene_geometria(self):
        rep = aplicar_Q("II", self.geom_II, CFG, usar_demo=True)
        self.assertGreater(self.geom_II["por_nivel"]["EII_CP2"]["area_total_m2"], 0.0)
        for nv in ["EII_CP1S", "EII_CP1", "EII_CP3", "EII_CP4"]:
            self.assertEqual(rep["por_nivel"][nv]["estado_geometria"],
                             "PENDIENTE_SIN_GEOMETRIA_TRIBUTARIA")
        self.assertEqual(rep["por_nivel"]["EII_CP2"]["estado"], "OK")

    def test_no_doble_aplicacion_y_catalogo_separado(self):
        cfg = dict(CFG)
        antes = cfg["aplicada_al_modelo_FE"]
        rep = aplicar_Q("I", self.geom_I, cfg, usar_demo=True)
        self.assertEqual(rep["aplicada_al_modelo_FE"], antes)
        self.assertEqual(cfg["aplicada_al_modelo_FE"], antes)  # no muta el flag
        catalogo = rep["catalogo_sobrecarga_documentada"]
        self.assertIn("SC_por_nivel_kgf_m2", catalogo)
        self.assertEqual(rep["q_Q"]["q_Q_kN_m2"], 2.0)
        self.assertEqual(rep["q_Q"]["estado"], "PARAMETRO_ADOPTADO_POR_EL_GRUPO")

    def test_catalogo_eii_tiene_SC_lineal_no_uniforme(self):
        cat = leer_catalogo_sobrecarga("II")
        self.assertIn("SC_lineal_kg_m", cat)
        self.assertIn("pendiente", cat)


if __name__ == "__main__":
    unittest.main()