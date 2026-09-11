import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.unity_esfuerzos.exportar_esfuerzos_para_viewer import (
    CASOS, FUENTE_SUPERPOSICION, RAIZ, generar, leer_metadata_I,
    leer_metadata_II, leer_superposicion,
)

ESTADOS_VALIDOS = {"1A1", "CONTENIDO", "SIN_CORRESPONDENCIA_VIEWER"}


class TestExportacionEstructura(unittest.TestCase):
    def _datos(self, edificio):
        d = generar(edificio)
        self.assertEqual(d["formato"], "esfuerzos_FE_edificio_v1")
        return d

    def test_estructura_edificio_I(self):
        d = self._datos("I")
        self.assertEqual(d["edificio"], "I")
        self.assertEqual(d["n_elementos"], 349)
        self.assertEqual(set(d["casos"]), set(CASOS))
        self.assertEqual(len(d["indices_componentes"]), 12)
        tags = [e["tag"] for e in d["elementos"]]
        self.assertEqual(len(tags), 349)
        self.assertEqual(tags, sorted(tags))
        fuente_tags = set(leer_superposicion("I")["G"])
        self.assertEqual(len(fuente_tags), 349)
        self.assertEqual(set(tags), fuente_tags)

    def test_estructura_edificio_II(self):
        d = self._datos("II")
        self.assertEqual(d["edificio"], "II")
        self.assertEqual(d["n_elementos"], 264)
        tags = [e["tag"] for e in d["elementos"]]
        self.assertEqual(len(tags), 264)
        self.assertEqual(tags, sorted(tags))
        fuente_tags = set(leer_superposicion("II")["G"])
        self.assertEqual(len(fuente_tags), 264)
        self.assertEqual(set(tags), fuente_tags)

    def test_cada_elemento_tiene_5_casos_x_12(self):
        for edificio in ("I", "II"):
            d = generar(edificio)
            for e in d["elementos"]:
                self.assertEqual(set(e["fuerzas"]), set(CASOS))
                for caso in CASOS:
                    self.assertEqual(len(e["fuerzas"][caso]), 12)

    def test_geometria_fisica_y_unidades(self):
        for edificio in ("I", "II"):
            d = generar(edificio)
            self.assertEqual(d["unidades"]["carga"], "kN")
            for e in d["elementos"]:
                a, b = e["p_i_unity"], e["p_j_unity"]
                self.assertEqual(len(a), 3)
                largo = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
                self.assertGreater(largo, 1e-6, f"elemento sin geometria: tag {e['tag']}")
                self.assertTrue(all(isinstance(v, (int, float)) for v in a + b))


class TestFidelidadFuente(unittest.TestCase):
    """Los valores del paquete deben ser identicos a la fuente (redondeo 6)."""

    def _fuente(self, edificio):
        return leer_superposicion(edificio)

    def test_valores_iguales_a_superposicion(self):
        for edificio in ("I", "II"):
            d = generar(edificio)
            fuente = self._fuente(edificio)
            for e in d["elementos"]:
                tag = e["tag"]
                for caso in CASOS:
                    esperado = [round(v, 6) for v in fuente[caso][tag]]
                    self.assertEqual(e["fuerzas"][caso], esperado,
                                     f"edificio {edificio} tag {tag} caso {caso}")

    def test_combinada_es_explicita(self):
        for edificio in ("I", "II"):
            d = generar(edificio)
            fuente = leer_superposicion(edificio)
            explicita = fuente["COMBINADA"]
            for e in d["elementos"]:
                self.assertEqual(e["fuerzas"]["COMBINADA"],
                                 [round(v, 6) for v in explicita[e["tag"]]])


class TestMetadataFuente(unittest.TestCase):
    def test_tags_metadata_I_iguales_csv(self):
        meta = leer_metadata_I()
        d = generar("I")
        self.assertEqual(set(meta), {e["tag"] for e in d["elementos"]})

    def test_coords_I_iguales_csv(self):
        meta = leer_metadata_I()
        d = generar("I")
        import csv
        camino = RAIZ / "analisis_estructural" / "edificio_I" / "resultados" / "modelo_estructural" / "esfuerzos_elementos_edificio_I.csv"
        esperado = {}
        with open(camino, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                t = int(row["elementTag_FE"])
                esperado[t] = [float(row["u_i_m"]), float(row["z_i_m"]), float(row["v_i_m"])]
        for e in d["elementos"]:
            self.assertEqual(e["p_i_unity"], [round(v, 9) for v in esperado[e["tag"]]])

    def test_coords_II_iguales_builder(self):
        d = generar("II")
        meta = leer_metadata_II()
        for e in d["elementos"]:
            self.assertEqual(e["p_i_unity"], [round(v, 9) for v in meta[e["tag"]]["p_i_unity"]])
            self.assertEqual(e["p_j_unity"], [round(v, 9) for v in meta[e["tag"]]["p_j_unity"]])

    def test_niveles_por_edificio(self):
        dI = generar("I")
        self.assertEqual(dI["lista_niveles"], ["CP1S", "P1", "P2", "P3", "P4"])
        self.assertTrue(all(
            e["nivel"] in dI["lista_niveles"] or e["tipo"].startswith("stub")
            for e in dI["elementos"]))
        dII = generar("II")
        self.assertTrue(all(e["nivel"] in dII["lista_niveles"] for e in dII["elementos"]))
        self.assertTrue(all(e["nivel"].startswith("EII_") for e in dII["elementos"]))


class TestCorrespondencia(unittest.TestCase):
    def test_estados_validos(self):
        for edificio in ("I", "II"):
            d = generar(edificio)
            for e in d["elementos"]:
                c = e["correspondencia"]
                self.assertIn(c["estado"], ESTADOS_VALIDOS)
                if c["estado"] == "SIN_CORRESPONDENCIA_VIEWER":
                    self.assertIsNone(c["viewer_id"])
                    self.assertIsNone(c["viewer_nivel"])
                else:
                    self.assertIsNotNone(c["viewer_id"])
                    self.assertIsNotNone(c["viewer_nivel"])

    def test_edificios_separados(self):
        dI, dII = generar("I"), generar("II")
        self.assertEqual(dI["edificio"], "I")
        self.assertEqual(dII["edificio"], "II")
        # cada edificio sale de su propia fuente de tags (la numeracion local no
        # tiene por que ser disjunta entre I y II; la separacion real es por edificio)
        tags_I = {e["tag"] for e in dI["elementos"]}
        tags_II = {e["tag"] for e in dII["elementos"]}
        self.assertEqual(tags_I, set(leer_superposicion("I")["G"]))
        self.assertEqual(tags_II, set(leer_superposicion("II")["G"]))
        self.assertNotIn("EII_", {e["nivel"] for e in dI["elementos"]})
        self.assertTrue(all(e["nivel"].startswith("EII_") for e in dII["elementos"]))


if __name__ == "__main__":
    unittest.main()