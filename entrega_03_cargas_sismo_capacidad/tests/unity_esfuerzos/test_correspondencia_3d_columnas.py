"""Test anti-remap de la correspondencia 3D de columnas (SOLO LECTURA).

Garantiza que las barras FE analiticas flotantes de la torre P4-EI
(tags 607,611,615,619,623,627,631,635, z=11,83->15,79) NO vuelvan a mapearse
como correspondencia normal (1A1/CONTENIDO) contra las columnas fisicas del
viewer del nivel P4 (tramo [7,87;11,83]) ni contra ninguna otra columna:

  * su estado queda SIN_GEOMETRIA_FISICA_3D;
  * viewer_id/viewer_nivel quedan nulos (no se asignan a ninguna barra fisica);
  * conservan su geometria FE y sus resultados por caso en el JSON productivo.

Ademas, valida la invariante global: toda columna con correspondencia normal en
el JSON canonico coincide con el tramo fisico completo [cota(nivel), cota(nivel
siguiente)] del entrepiso correspondiente (comparacion 3D de extremos, centro,
longitud y orientacion), de modo que un intervalo [11,83;15,79] no puede volver
a ser 1A1/CONTENIDO sin romper el test.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.unity_esfuerzos.exportar_esfuerzos_para_viewer import (  # noqa: E402
    GEOMETRIA_VIEWER,
    TOL_3D,
    comparar_intervalo_3d,
    leer_geometria_viewer,
    tramo_fisico_columna,
)
from src.unity_esfuerzos.exportar_esfuerzos_funcional_para_viewer import (  # noqa: E402
    generar,
)

POSTES_P4_EI = {607, 611, 615, 619, 623, 627, 631, 635}
Z_INF_POSTE = 11.83
Z_SUP_POSTE = 15.79
ESTADO_ANALITICO = "SIN_GEOMETRIA_FISICA_3D"
NIVELES_EI = ["CP1S", "P1", "P2", "P3", "P4"]
NIVELES_EII = ["EII_CP1S", "EII_CP1", "EII_CP2", "EII_CP3", "EII_CP4"]


def _canonico(edificio: str) -> dict:
    p = (GEOMETRIA_VIEWER / edificio / "results"
         / f"esfuerzos_FE_EDIFICIO_{edificio}.json")
    return json.loads(p.read_text(encoding="utf-8"))


class TestAntiRemapPostesP4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonico = _canonico("I")
        cls.geo = leer_geometria_viewer("I")

    def test_poste_presente_y_con_estado_analitico(self):
        d = {e["tag"]: e for e in self.canonico["elementos"]}
        for tag in POSTES_P4_EI:
            self.assertIn(tag, d, f"poste {tag} ausente del JSON productivo")
            e = d[tag]
            self.assertEqual(e["correspondencia"]["estado"], ESTADO_ANALITICO,
                             f"poste {tag} con estado {e['correspondencia']['estado']}")
            self.assertIsNone(e["correspondencia"]["viewer_id"], f"poste {tag}")
            self.assertIsNone(e["correspondencia"]["viewer_nivel"], f"poste {tag}")
            zi, zj = e["p_i_unity"][1], e["p_j_unity"][1]
            self.assertEqual(sorted((zi, zj)), [Z_INF_POSTE, Z_SUP_POSTE],
                             f"poste {tag}: geometria FE alterada")
            self.assertTrue(e["fuerzas"], f"poste {tag}: sin resultados")
            casos = self.canonico["casos"]
            self.assertEqual(set(e["fuerzas"]), set(casos), f"poste {tag}")

    def test_poste_no_1A1_ni_CONTENIDO_con_seccion_fisica(self):
        d = {e["tag"]: e for e in self.canonico["elementos"]}
        for tag in POSTES_P4_EI:
            self.assertNotIn(d[tag]["correspondencia"]["estado"], {"1A1", "CONTENIDO"})

    def test_invariante_intervalo_completo_en_1A1(self):
        # ninguna columna con correspondencia normal puede tener intervalo
        # [11,83;15,79] -> equivaldria a re-mapear un poste contra la estructura.
        for e in self.canonico["elementos"]:
            if e["tipo"] != "columna" or \
                    e["correspondencia"]["estado"] not in ("1A1", "CONTENIDO"):
                continue
            zi = min(e["p_i_unity"][1], e["p_j_unity"][1])
            zj = max(e["p_i_unity"][1], e["p_j_unity"][1])
            self.assertNotEqual(
                [zi, zj], [Z_INF_POSTE, Z_SUP_POSTE],
                f"tag {e['tag']}: intervalo de poste P4 con correspondencia normal")
            tramo = tramo_fisico_columna(e["nivel"], self.geo)
            assert tramo is not None, f"tag {e['tag']} 1A1 sin tramo fisico"
            cmp = comparar_intervalo_3d(
                e["p_i_unity"], e["p_j_unity"], tramo[0], tramo[1], TOL_3D)
            self.assertTrue(cmp["ok"],
                            f"tag {e['tag']} 1A1 fuera del tramo fisico "
                            f"{tramo}: {cmp}")

    def test_conteos_universo_esperado(self):
        resumen = self.canonico["resumen_por_tipo_estado"]
        ncols = sum(v for k, v in resumen.items() if k.startswith("columna__"))
        self.assertEqual(ncols, 115)
        self.assertEqual(resumen.get(f"columna__{ESTADO_ANALITICO}"), 8)
        self.assertEqual(self.canonico["n_elementos"], 378)


class TestPostesEnMemoriaConsistentesConDisco(unittest.TestCase):
    def test_generar_memoria_y_canonico_coinciden(self):
        d_nuevo, _, _ = generar("I", escribir=False)
        canonico = _canonico("I")
        por_tag = {e["tag"]: e for e in canonico["elementos"]}
        for ne in d_nuevo["elementos"]:
            oe = por_tag[ne["tag"]]
            self.assertEqual(ne["correspondencia"], oe["correspondencia"],
                             f"tag {ne['tag']}: fuente regenerable != JSON productivo")
            self.assertEqual(ne["fuerzas"], oe["fuerzas"], f"tag {ne['tag']}")


class TestEIIInalterado(unittest.TestCase):
    def test_eii_sin_columnas_analiticas_nuevas(self):
        canonico = _canonico("II")
        resumen = canonico["resumen_por_tipo_estado"]
        for k in resumen:
            if k.startswith("columna__"):
                self.assertNotEqual(k, f"columna__{ESTADO_ANALITICO}",
                                    f"{k} no debe existir en EII")
        self.assertEqual(canonico["n_elementos"], 253)


if __name__ == "__main__":
    unittest.main()