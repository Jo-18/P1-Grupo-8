import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.superposicion.combinacion import (CasosBaseIncompletosError, check_casos_base,
                                           coeficientes, combinar,
                                           verificar_contra_opensees, leer_config)


def respuestas_sinteticas():
    return {
        "G": {"desplazamiento": [1.0, 2.0], "reaccion": [10.0, 20.0],
              "fuerza_interna": [5.0, 7.0]},
        "Q": {"desplazamiento": [0.5, 1.0], "reaccion": [4.0, 5.0],
              "fuerza_interna": [2.0, 3.0]},
        "EX": {"desplazamiento": [2.0, 4.0], "reaccion": [8.0, 9.0],
               "fuerza_interna": [3.0, 1.0]},
        "EY": {"desplazamiento": [1.0, 3.0], "reaccion": [5.0, 6.0],
               "fuerza_interna": [1.5, 2.5]},
    }


class TestSuperposicion(unittest.TestCase):
    def test_coeficientes_null_requiere_demo(self):
        cfg = leer_config()
        with self.assertRaises(CasosBaseIncompletosError):
            coeficientes(cfg, usar_demo=False)
        lambdas = coeficientes(cfg, usar_demo=True)
        for c in ["G", "Q", "EX", "EY"]:
            self.assertEqual(lambdas[c]["estado"], "DEMOSTRACION_ARBITRARIA")

    def test_check_casos_base_incompleto(self):
        with self.assertRaises(CasosBaseIncompletosError):
            check_casos_base({"G": {}, "Q": {}, "EY": {}})

    def test_combinar_matricial_coincide_con_suma_explicita(self):
        cfg = leer_config()
        lamb = {c: {"valor": l["demostracion_arbitraria"],
                    "estado": "DEMOSTRACION_ARBITRARIA"} for c, l in
                cfg["coeficientes"].items()}
        R = combinar(respuestas_sinteticas(), lamb)
        for f in ("desplazamiento", "reaccion", "fuerza_interna"):
            manual = [0.0, 0.0]
            for caso in ["G", "Q", "EX", "EY"]:
                lam = lamb[caso]["valor"]
                for i in range(2):
                    manual[i] += lam * respuestas_sinteticas()[caso][f][i]
            for a, b in zip(R["respuesta_combinada"][f], manual):
                self.assertAlmostEqual(a, b)

    def test_verificar_contra_opensees(self):
        R = {"desplazamiento": [1.0, 2.0], "reaccion": [10.0, 20.0],
             "fuerza_interna": [5.0, 7.0]}
        R_ops = {"desplazamiento": [1.001, 2.0], "reaccion": [10.0, 19.99],
                 "fuerza_interna": [4.99, 7.0]}
        v = verificar_contra_opensees(R, R_ops, tolerancia_rel=0.01)
        self.assertEqual(v["estado"], "OK")


if __name__ == "__main__":
    unittest.main()