# -*- coding: utf-8 -*-
"""Aceptacion Semana 4 del viewer: extremos Vy/Vz SIN AMPLITUD y P-M del muro.

Usa el payload RUNTIME del viewer (StreamingAssets/lab_data) que es el mismo
que lee EsfuerzosController en Unity. Verifica T2 (los ceros de Vy/Vz en
celosias/grillage son ceros REALES del modelo y hay vigas con corte real no
nulo para demostrar el diagrama) y T3/T5 (identidad del muro demo por
viewer_id EII_CP1S_M_001, seccion FE "M 0.25x3.97x2", D/C real ~1.1684 sin
ajustar capacidad).
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

CASOS_BASE = ("G", "Q", "EX", "EY")
_RUTA = (Path(__file__).resolve().parents[3] / "viewer_unity" / "Assets"
         / "StreamingAssets" / "lab_data" / "edificios")


def _payload(edificio):
    return json.loads((_RUTA / edificio / "results"
                       / f"esfuerzos_FE_EDIFICIO_{edificio}.json")
                      .read_text(encoding="utf-8"))


def _por_tag(edificio):
    return {e["tag"]: e for e in _payload(edificio)["elementos"]}


def _v(edificio, tag, caso):
    """Vector local FE de 12 valores: 0..5 extremo i, 6..11 extremo j."""
    return [float(x) for x in _por_tag(edificio)[tag]["fuerzas"][caso][:12]]


class TestVyVzConCorteReal(unittest.TestCase):
    """T2: hay vigas con Vy/Vz NO nulos (el mapeo indice<->componente es
    correcto) y se usan como candidatas de las capturas de aceptacion."""

    def test_EI_tag202_Vz_real(self):
        f = _v("I", 202, "G")
        self.assertAlmostEqual(f[2], 225.81, places=2)   # Vz_i
        self.assertAlmostEqual(f[8], -225.81, places=2)  # Vz_j
        self.assertAlmostEqual(f[4], -2619.34, places=2)  # My_i

    def test_EII_tag228_Vz_real(self):
        f = _v("II", 228, "G")
        self.assertAlmostEqual(f[2], 295.9, places=2)    # Vz_i
        self.assertAlmostEqual(f[4], -1772.43, places=2)  # My_i

    def test_EII_tag229_y_226_tambien_reales(self):
        self.assertAlmostEqual(_v("II", 229, "G")[2], 146.4, places=2)
        self.assertAlmostEqual(_v("II", 226, "G")[2], 108.67, places=2)

    def test_la_celosia_no_es_cero_en_todo(self):
        # En la misma celosia hay vigas con corte real: el cero de las vigas
        # grillage es un dato real del modelo, no un fallo de mapeo.
        f = _v("II", 228, "G")
        self.assertGreater(max(abs(f[i]) for i in range(12)), 100.0)


class TestVyVzSinAmplitud(unittest.TestCase):
    """T2: las vigas grillage/celosia del EII traen los 12 valores a 0 en las
    cuatro cargas base. El viewer debe mostrar "SIN AMPLITUD" y NO dibujar
    curva ni inventar valores."""

    GRILIAGE_EII = (211, 213, 219, 220, 250)

    def test_ceros_reales_las_4_cargas_base(self):
        for tag in self.GRILIAGE_EII:
            for caso in CASOS_BASE:
                for x in _v("II", tag, caso):
                    self.assertAlmostEqual(x, 0.0, places=6,
                                           msg=f"II tag{tag} {caso}")

    def test_son_vigas_con_geometria(self):
        for tag in self.GRILIAGE_EII:
            e = _por_tag("II")[tag]
            self.assertEqual(e["tipo"], "viga")
            self.assertTrue(e["correspondencia"].get("viewer_id"))


class TestMuroPMAceptacion(unittest.TestCase):
    """T3/T5: el muro demostrado P-M se identifica por viewer_id
    (EII_CP1S_M_001) y ambos segmentos FE (tags 76 y 85) comparten ese viewer,
    por lo que la comparacion por viewer_id en C# muestra el bloque P-M en los
    dos segmentos del contenido."""

    def test_muro_demostrado_viewer_id(self):
        pm = json.loads((_RUTA / "II" / "results"
                         / "pm_capacidad_demanda_II.json")
                        .read_text(encoding="utf-8"))
        dem = pm["muro_demostrado"]["demanda"]
        self.assertEqual(dem["elemento_demostrado"]["viewer_id"],
                         "EII_CP1S_M_001")
        self.assertEqual(dem["elemento_demostrado"]["tag"], 76)
        sec = pm["muro_demostrado"]["capacidad_pm"]["seccion"]
        self.assertEqual(sec["etiqueta"],
                         "M 0.25x3.97 (b=0.25 espesor, h=3.97 largo)")
        self.assertAlmostEqual(dem["D_C"], 1.1684, places=3)  # se muestra tal cual
        self.assertIn("HIPOTESIS", pm["muro_demostrado"]["capacidad_pm"]
                      .get("clasificacion", ""))

    def test_ambos_segmentos_muro_por_viewer(self):
        por = _por_tag("II")
        for tag in (76, 85):
            e = por[tag]
            self.assertEqual(e["tipo"], "muro")
            self.assertEqual(e["nivel"], "EII_CP1S")
            self.assertEqual(e["correspondencia"]["viewer_id"],
                             "EII_CP1S_M_001")
            self.assertEqual(e["seccion"], "M 0.25x3.97x2")

    def test_demanda_concurrente_case_ey(self):
        pm = json.loads((_RUTA / "II" / "results"
                         / "pm_capacidad_demanda_II.json")
                        .read_text(encoding="utf-8"))
        cc = pm["muro_demostrado"]["demanda"]["demanda_concurrente"]
        self.assertEqual(cc["caso"], "U3_EY_NEG")
        self.assertAlmostEqual(cc["M_demanda_kN_m"], 8661.169553, places=2)
        self.assertAlmostEqual(cc["P_u_kN"], 550.444724, places=2)


if __name__ == "__main__":
    unittest.main()