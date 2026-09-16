import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.capacidad_rc.diagrama_pm import puntos_pm  # noqa: E402
from src.unity_esfuerzos.pm_capacidad_demanda_hitob import (  # noqa: E402
    MURO_EII_TAG, _cargar_perfil, _cargar_pm_columna, _concurrente,
    _evaluar, _mu_interp, _muro_pm,
)
_EDIFICIO_MURO = "II"


class TestDemandaConcurrente(unittest.TestCase):
    def test_concurrente_desde_fuerzas_de_perfil(self):
        p = _cargar_perfil("II")
        el = next(e for e in p["elementos"] if e["tipo"] == "columna"
                  and e["correspondencia"].get("viewer_id"))
        f = el["fuerzas"]["U1_GQ"]
        c = _concurrente(f)
        self.assertEqual(c["N_i_kN"], round(float(f[0]), 3))
        self.assertEqual(c["N_j_kN"], round(float(f[6]), 3))
        self.assertEqual(c["N_demanda_kN"], max(float(f[0]), float(f[6])))
        self.assertEqual(c["M_demanda_kN_m"],
                         max(abs(float(f[i])) for i in (4, 5, 10, 11)))

    def test_mu_interp_reproduce_curva(self):
        for edificio in ("I", "II"):
            pm = _cargar_pm_columna(edificio)
            for N, M in zip(pm["N_kN"], pm["M_kN_m"]):
                mu, modo = _mu_interp(N, pm["N_kN"], pm["M_kN_m"])
                self.assertAlmostEqual(mu, M, places=3)
                self.assertIn(modo, ("interpolado", "acotado_extremo_inferior",
                                     "acotado_extremo_superior"))
            # acotacion por extremos
            mu_sup, modo_sup = _mu_interp(pm["N_kN"][-1] * 1.5, pm["N_kN"],
                                          pm["M_kN_m"])
            self.assertEqual(modo_sup, "acotado_extremo_superior")
            self.assertAlmostEqual(mu_sup, pm["M_kN_m"][-1])

    def test_muro_pm_es_de_demostracion(self):
        pm = _muro_pm({"h_m": 1.0, "b_m": 0.25}, N_max_kN=5000.0)
        self.assertEqual(len(pm["N_kN"]), 15)
        self.assertEqual(len(pm["M_kN_m"]), 15)
        self.assertGreater(pm["M_kN_m"][0], 0.0)
        self.assertIn("HIPOTESIS", pm["clasificacion"])


class TestEvaluacionHitoB(unittest.TestCase):
    def test_columna_demostrada_es_real(self):
        for edificio in ("I", "II"):
            d = _evaluar(edificio)
            c = d["columna_critica"]
            self.assertTrue(c["viewer_id"], f"{edificio}: columna no real")
            self.assertNotIn("SIN_CORRESPONDENCIA",
                             (c["estado_correspondencia"] or ""))
            self.assertEqual(len(d["por_elemento"]), d["n_columnas_totales"])
            self.assertGreater(d["n_columnas_demostrables"], 0)
            # D/C = M/Mu(P) del mismo caso (concurrente)
            self.assertAlmostEqual(
                c["D_C"], c["M_demanda_kN_m"] / c["M_u_N_kN_m"], places=3)
            self.assertEqual(_cargar_pm_columna(edificio)["clasificacion"],
                             "HIPOTESIS_DEMOSTRACION")

    def test_muro_eii_demostrado(self):
        d = _evaluar(_EDIFICIO_MURO, caso_muro=MURO_EII_TAG)
        mur = d["muro_demostrado"]
        self.assertEqual(mur["demanda"]["elemento_demostrado"]["tag"], MURO_EII_TAG)
        el = next(e for e in _cargar_perfil(_EDIFICIO_MURO)["elementos"]
                  if e["tag"] == MURO_EII_TAG)
        caso = mur["demanda"]["demanda_concurrente"]["caso"]
        f = el["fuerzas"][caso]
        c = _concurrente(f)
        self.assertEqual(mur["demanda"]["demanda_concurrente"]["M_demanda_kN_m"],
                         c["M_demanda_kN_m"])
        mun = mur["demanda"]["M_u_N_kN_m"]
        self.assertGreater(mun, 0.0)
        self.assertEqual(mur["capacidad_pm"]["clasificacion"], "EVALUACION_HIPOTESIS_BLOQUEADA_ARMADURA")
        self.assertGreaterEqual(len(mur["capacidad_pm"]["N_kN"]), 10)


if __name__ == "__main__":
    unittest.main()