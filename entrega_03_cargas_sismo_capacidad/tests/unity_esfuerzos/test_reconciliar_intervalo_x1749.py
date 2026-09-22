import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.unity_esfuerzos.reconciliar_intervalo_x1749 import (  # noqa: E402
    TAG_FE, TOL_REDONDEO, VISTA_V0, VISTA_V1, _residuos, reconciliar,
)


class TestReconciliacionIntervaloX1749(unittest.TestCase):
    def test_intervalo_rotulado_completo(self):
        d = reconciliar()
        self.assertTrue(d["reconciliado"])
        self.assertEqual(d["fe_cubre"]["tag"], TAG_FE)
        self.assertTrue(d["fe_cubre"]["contenido_en_fe"])
        self.assertIn("FE_COMPLETO", d["rotulo"])

    def test_intervalo_fisico_contenido_en_fe(self):
        d = reconciliar()
        v = d["fe_cubre"]["intervalo_v_m"]
        self.assertTrue(v[0] <= VISTA_V0 + TOL_REDONDEO)
        self.assertTrue(v[1] >= VISTA_V1 - TOL_REDONDEO)
        self.assertGreaterEqual(d["fe_cubre"]["L_m"], VISTA_V1 - VISTA_V0)

    def test_diagrama_lineal_residuos_nulos(self):
        d = reconciliar()
        ver = d["verificacion_linealidad"]
        self.assertTrue(ver["ok_axial"])
        self.assertLess(ver["peor_residual_kN"], TOL_REDONDEO)
        for c, r in ver["por_caso"].items():
            for k in ("N", "Vy", "Vz", "T"):
                self.assertLess(abs(r[k]), TOL_REDONDEO, c)

    def test_no_inventa_correspondencia(self):
        d = reconciliar()
        self.assertEqual(d["fe_cubre"]["correspondencia"]["estado"],
                         "SIN_CORRESPONDENCIA_VIEWER")
        self.assertIn("PENDIENTE_DE_FUENTE", d["pendiente_conservado"])

    def test_rotulo_consistente_con_contenido(self):
        d = reconciliar()
        self.assertEqual(d["rotulo"],
                         ("FE_COMPLETO: el intervalo fisico V_x1749 [16.45,19.97] "
                          "esta contenido en el FE tag 317 [16.15,20.27] y su diagrama "
                          "interno es lineal (residuos nulos). "
                          "No se inventa correspondencia."))


if __name__ == "__main__":
    unittest.main()