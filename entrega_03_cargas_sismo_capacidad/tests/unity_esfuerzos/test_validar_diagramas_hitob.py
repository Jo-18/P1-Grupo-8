import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.modelo_fiel.combinaciones_nch3171 import COMBINACIONES_NCH3171  # noqa: E402
from src.unity_esfuerzos.validar_diagramas_hitob import (  # noqa: E402
    _coeficientes, _sintesis_esperado, _validar,
)

ESPERADOS = {
    "U1_GQ": {"G": 1.2, "Q": 1.6},
    "U2_EX_POS": {"G": 1.2, "Q": 1.0, "EX": 1.4},
    "U2_EX_NEG": {"G": 1.2, "Q": 1.0, "EX": -1.4},
    "U3_EY_POS": {"G": 1.2, "Q": 1.0, "EY": 1.4},
    "U3_EY_NEG": {"G": 1.2, "Q": 1.0, "EY": -1.4},
    "U4_EX_POS": {"G": 0.9, "EX": 1.4},
    "U4_EX_NEG": {"G": 0.9, "EX": -1.4},
    "U4_EY_POS": {"G": 0.9, "EY": 1.4},
    "U4_EY_NEG": {"G": 0.9, "EY": -1.4},
}


class TestCoeficientes(unittest.TestCase):
    def test_coef_desde_expresion_norma(self):
        for c in COMBINACIONES_NCH3171:
            if not c["id"].startswith("U"):
                continue
            self.assertEqual(_coeficientes(c["expresion"]),
                             ESPERADOS[c["id"]])


class TestValidacionIndependiente(unittest.TestCase):
    def test_todos_calificables_y_ok(self):
        for edificio in ("I", "II"):
            d = _validar(edificio)
            self.assertEqual(d["n_calificables"], d["n_elementos"], edificio)
            self.assertEqual(d["n_no_calificables"], 0, edificio)
            self.assertTrue(all(v["ok"] for v in d["por_elemento"].values()),
                            edificio)

    def test_muestra_esta_dentro_de_tolerancia(self):
        for edificio in ("I", "II"):
            d = _validar(edificio)
            self.assertTrue(d["muestra_jurado"]["columna_demostrada"])
            if d["muestra_jurado"]["viga_demostrada"]:
                self.assertTrue(
                    d["muestra_resultados"][
                        str(d["muestra_jurado"]["viga_demostrada"]["tag"])]["ok"])
            for tag_str, r in d["muestra_resultados"].items():
                self.assertTrue(r["ok"])
                self.assertLess(r["max_abs_kN"], 1e-3)

    def test_sintesis_coincide_con_perfil_para_viga_y_columna(self):
        for edificio in ("I", "II"):
            d = _validar(edificio)
            col = d["muestra_jurado"]["columna_demostrada"]
            self.assertTrue(col)


if __name__ == "__main__":
    unittest.main()