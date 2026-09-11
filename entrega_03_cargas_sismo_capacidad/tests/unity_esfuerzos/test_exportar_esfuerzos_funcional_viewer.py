import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.unity_esfuerzos.exportar_esfuerzos_funcional_para_viewer import (
    CASOS, CASOS_BASE, COMBINACIONES_NCH3171, GEOMETRIA_VIEWER,
    IDS_COMBINACIONES, INDICES_NOMBRES, MAX_STUB_LONG_M, NIVELES,
    RAZON_SIN_REGISTRO, STUB_TIPO, generar,
)

ESTADOS_VALIDOS = {"1A1", "CONTENIDO", "SIN_CORRESPONDENCIA_VIEWER"}
CAUSAS = {"PENDIENTE_DE_FUENTE", "SIN_CORRESPONDENCIA_FE"}
PREFIJO = {"I": "EI", "II": "EII"}


def _payload(edificio, caso):
    return json.loads(
        (Path(__file__).resolve().parents[2] / "modelo_fiel"
         / "MODELO_FE_COMPLETO_FUNCIONAL"
         / f"{caso}_{PREFIJO[edificio]}_MODELO_FE_COMPLETO_FUNCIONAL.json")
        .read_text(encoding="utf-8"))


def _payload_combo(edificio, cid):
    return json.loads(
        (Path(__file__).resolve().parents[2] / "modelo_fiel"
         / "MODELO_FE_COMPLETO_FUNCIONAL"
         / f"COMB_{cid}_{PREFIJO[edificio]}_MODELO_FE_COMPLETO_FUNCIONAL.json")
        .read_text(encoding="utf-8"))


def _fuerzas_fuente(edificio, caso):
    if caso in CASOS_BASE:
        p = _payload(edificio, caso)
    else:
        p = _payload_combo(edificio, caso)
    fl = p.get("fuerzas_local_por_elemento")
    if fl is None:
        fl = p["solucion"]["fuerzas_local_por_elemento"]
    return {int(k): [float(x) for x in v] for k, v in fl.items()}


class TestEstructuraContratoV1(unittest.TestCase):
    def _datos(self, edificio):
        d = generar(edificio, escribir=False)[0]
        self.assertEqual(d["formato"], "esfuerzos_FE_edificio_v1")
        return d

    def test_edificio_I_412(self):
        d = self._datos("I")
        self.assertEqual(d["edificio"], "I")
        self.assertEqual(d["n_elementos"], 412)
        tags = [e["tag"] for e in d["elementos"]]
        self.assertEqual(len(tags), len(set(tags)))
        self.assertEqual(tags, sorted(tags))
        self.assertEqual(set(tags), set(_fuerzas_fuente("I", "G")))

    def test_edificio_II_252(self):
        d = self._datos("II")
        self.assertEqual(d["n_elementos"], 252)
        tags = [e["tag"] for e in d["elementos"]]
        self.assertEqual(len(tags), len(set(tags)))
        self.assertEqual(set(tags), set(_fuerzas_fuente("II", "G")))

    def test_casos_base_sin_COMBINADA_y_combinaciones_calculadas(self):
        for edificio in ("I", "II"):
            d = generar(edificio, escribir=False)[0]
            self.assertEqual(d["casos_base"], list(CASOS_BASE))
            self.assertEqual(d["casos"], list(CASOS))
            self.assertNotIn("COMBINADA", d["casos"])
            for e in d["elementos"]:
                self.assertEqual(set(e["fuerzas"]), set(CASOS))
                self.assertEqual(list(e["fuerzas"]), list(CASOS))
                self.assertNotIn("COMBINADA", e["fuerzas"])
                for caso in CASOS:
                    self.assertEqual(len(e["fuerzas"][caso]), 12)
                self.assertEqual(len(e["envolvente_NCh3171"]), 12)
            esquema = d["combinaciones_normativas_NCh3171"]
            self.assertEqual(esquema["norma"], "NCh3171.Of2008 (ed. 2021)")
            self.assertTrue(esquema["estado"].startswith("CALCULADA"))
            self.assertEqual([c["id"] for c in esquema["combinaciones"]],
                             IDS_COMBINACIONES)
            by_id = {c["id"]: c for c in esquema["combinaciones"]}
            for c in COMBINACIONES_NCH3171:
                self.assertEqual(by_id[c["id"]]["expresion"], c["expresion"])
                self.assertEqual(by_id[c["id"]]["factores"], c["factores"])
            self.assertEqual(esquema["combinaciones_100_30"]["estado"],
                             "NO_NORMATIVA_PARA_ESTA_ENTREGA")
            self.assertEqual(esquema["envolvente"]["sobre"],
                             IDS_COMBINACIONES)

    def test_envolvente_respeta_maximo_abs_entre_combinaciones(self):
        for edificio in ("I", "II"):
            d = generar(edificio, escribir=False)[0]
            for e in d["elementos"]:
                for env in e["envolvente_NCh3171"]:
                    i = env["indice"]
                    valores = [e["fuerzas"][cid][i] for cid in IDS_COMBINACIONES]
                    self.assertAlmostEqual(float(env["valor"]),
                                           max(valores, key=abs), places=5)
                    self.assertIn(env["caso"], IDS_COMBINACIONES)
                    self.assertEqual(env["componente"],
                                     INDICES_NOMBRES[i])

    def test_geometria_y_convencion(self):
        for edificio in ("I", "II"):
            d = generar(edificio, escribir=False)[0]
            self.assertEqual(d["unidades"]["carga"], "kN")
            self.assertEqual(d["unidades"]["momento"], "kN*m")
            for e in d["elementos"]:
                a, b = e["p_i_unity"], e["p_j_unity"]
                self.assertEqual(len(a), 3)
                largo = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
                self.assertGreater(largo, 1e-6, f"elemento sin geometria: tag {e['tag']}")
                self.assertEqual(len(e["fuerzas"]["G"]), 12)


class TestFidelidadFuente(unittest.TestCase):
    """Los valores son copia (redondeo 6) de la fuente: no se recalculan."""

    def test_valores_iguales_a_payload(self):
        for edificio in ("I", "II"):
            d = generar(edificio, escribir=False)[0]
            for caso in CASOS:
                fuente = _fuerzas_fuente(edificio, caso)
                for e in d["elementos"]:
                    self.assertEqual(
                        e["fuerzas"][caso],
                        [round(float(v), 6) for v in fuente[e["tag"]]],
                        f"edificio {edificio} tag {e['tag']} caso {caso}")


class TestCorrespondenciaYCobertura(unittest.TestCase):
    def test_estados_validos(self):
        for edificio in ("I", "II"):
            d = generar(edificio, escribir=False)[0]
            for e in d["elementos"]:
                c = e["correspondencia"]
                self.assertIn(c["estado"], ESTADOS_VALIDOS)
                if c["estado"] == "SIN_CORRESPONDENCIA_VIEWER":
                    self.assertIsNone(c["viewer_id"])
                    self.assertIsNone(c["viewer_nivel"])
                else:
                    self.assertIsNotNone(c["viewer_id"])
                    self.assertIsNotNone(c["viewer_nivel"])
                    self.assertEqual(c["viewer_nivel"], e["nivel"])

    def test_cobertura_consistente(self):
        for edificio in ("I", "II"):
            d, _, cobertura = generar(edificio, escribir=False)
            for nivel, por_tipo in cobertura.items():
                self.assertIn(nivel, d["niveles_geometry_viewer"])
                for tipo, info in por_tipo.items():
                    self.assertEqual(info["con_fuente"] + len(info["sin_resultado"]),
                                     info["total"])
                    for s in info["sin_resultado"]:
                        self.assertIn(s["causa"], CAUSAS)
                        self.assertTrue(s["viewer_id"])

    def test_resumen_suma(self):
        for edificio in ("I", "II"):
            d = generar(edificio, escribir=False)[0]
            self.assertEqual(sum(d["resumen_por_tipo_estado"].values()),
                             d["n_elementos"])

    def test_niveles(self):
        for edificio in ("I", "II"):
            d = generar(edificio, escribir=False)[0]
            for e in d["elementos"]:
                if e["tipo"] == "stub_elastico_rigidez_elevada":
                    continue
                self.assertIn(e["nivel"], NIVELES[edificio])


class TestAuditoria(unittest.TestCase):
    def test_auditoria_ok(self):
        for edificio in ("I", "II"):
            d, auditoria, _ = generar(edificio, escribir=False)
            self.assertTrue(auditoria["ok"],
                            f"edificio {edificio}: " +
                            "; ".join(c["check"] for c in auditoria["checks"]
                                      if not c["ok"]))
            nombres = {c["check"] for c in auditoria["checks"]}
            self.assertIn("identidad_tags_casos_modelo", nombres)
            self.assertIn("equilibrio_vertical_G", nombres)
            self.assertIn("equilibrio_nodal_EX", nombres)
            self.assertIn("equilibrio_nodal_EY", nombres)
            self.assertIn("muestra_columnas_base_comprimidas", nombres)
            self.assertIn("stubs_documentados", nombres)
            self.assertIn("stub_sin_conector_gigante", nombres)
            self.assertIn("stub_sin_duplicados", nombres)
            self.assertIn("stub_sin_tramo_fantasma", nombres)
            self.assertIn("stub_equilibrio_local_bilateral", nombres)
            self.assertIn("stub_transmision_nodal_sismo", nombres)
            self.assertTrue(all(m["N_i_G_kN"] > 0 for m in auditoria["muestra"]))


class TestElementosAuxiliares(unittest.TestCase):
    """Los stubs del edificio I son auxiliares analiticos, no barra fisica del
    viewer: traen origen/destino/longitud/seccion/razon, se excluyen de la
    cobertura viewer<->FE y solo se ven en modo de diagnostico."""

    def test_stubs_en_elementos_documentados_y_sin_barra(self):
        d, _, _ = generar("I", escribir=False)
        stubs = [e for e in d["elementos"] if e.get("es_auxiliar_analitico")]
        self.assertEqual(len(stubs), 44)
        tags = set()
        for e in stubs:
            tags.add(e["tag"])
            self.assertEqual(e["tipo"], STUB_TIPO)
            a = e["auxiliar_analitico"]
            self.assertNotEqual(a["razon_existencia"], RAZON_SIN_REGISTRO)
            self.assertGreater(a["longitud_m"], 0.0)
            self.assertLessEqual(a["longitud_m"], MAX_STUB_LONG_M)
            self.assertEqual(a["seccion"], "RIGIDA")
            self.assertEqual(len(a["origen"]), 3)
            self.assertEqual(len(a["destino"]), 3)
            self.assertGreater(a["rigidez_mult"], 1.0)
            self.assertEqual(e["correspondencia"]["estado"],
                             "SIN_CORRESPONDENCIA_VIEWER")
            self.assertIsNone(e["correspondencia"]["viewer_id"])
            self.assertIsNone(e["correspondencia"]["viewer_nivel"])
        self.assertEqual(len(tags), 44)

    def test_II_sin_stubs(self):
        d, _, _ = generar("II", escribir=False)
        self.assertEqual(sum(1 for e in d["elementos"]
                             if e.get("es_auxiliar_analitico")), 0)
        self.assertEqual(d["documentacion_elementos_auxiliares"]["total"], 0)

    def test_documentacion_y_exclusion_de_cobertura(self):
        for edificio in ("I", "II"):
            d, _, cobertura = generar(edificio, escribir=False)
            doc = d["documentacion_elementos_auxiliares"]
            self.assertTrue(doc["excluido_de_cobertura_viewer_FE"])
            self.assertTrue(doc["no_asignados_a_barra_fisica"])
            vis = doc["visibilidad"]
            self.assertFalse(vis["modo_normal"]["visible"])
            self.assertFalse(vis["modo_normal"]["seleccionable"])
            self.assertTrue(vis["modo_diagnostico"]["visible"])
            stub_tags = {e["tag"] for e in d["elementos"]
                         if e.get("es_auxiliar_analitico")}
            for nivel, por_tipo in cobertura.items():
                for info in por_tipo.values():
                    for c in info.get("con_detalle", []):
                        self.assertTrue(set(c["tags"]).isdisjoint(stub_tags))


class TestSeleccionUnityPorNivel(unittest.TestCase):
    """Simula lo que hace Unity: seleccionar un objeto del viewer por nivel y
    recuperar los tags FE que lo representan con sus esfuerzos por caso."""

    def test_columnas_por_nivel_tag_y_valores_distintos(self):
        for edificio in ("I", "II"):
            d = generar(edificio, escribir=False)[0]
            por_eje = {}
            for e in d["elementos"]:
                c = e["correspondencia"]
                if e["tipo"] != "columna" or c["estado"] != "1A1":
                    continue
                # eje = posicion (u, v) de la columna (redondeo 1 dec para tolerar
                # desfases locales de modelacion entre tramos)
                eje = (round(e["p_j_unity"][0], 1), round(e["p_j_unity"][2], 1))
                por_eje.setdefault(eje, []).append(e)
            ejes_multiples = [els for els in por_eje.values() if len(els) >= 3]
            self.assertTrue(ejes_multiples, f"edificio {edificio}: sin ejes multi-nivel")
            for els in ejes_multiples[:1]:
                # tag unico por nivel (cada tramo de piso tiene su propio tag FE)
                niveles = [(e["nivel"], e["tag"]) for e in els]
                self.assertEqual(len({n for n, _ in niveles}), len(niveles),
                                 f"tag repetido por nivel en {edificio} {eje}")
                # valores distintos entre niveles y base a compresion
                axiales = {round(e["fuerzas"]["G"][0], 3) for e in els}
                self.assertGreater(len(axiales), 1,
                                   f"axial G identico entre niveles en {edificio} {eje}")
                base = min(els, key=lambda e: e["nivel"])
                self.assertGreater(base["fuerzas"]["G"][0], 0,
                                   f"base en traccion G en {edificio} {eje}")

    def test_vigas_por_nivel_tag_y_valores_distintos(self):
        for edificio in ("I", "II"):
            d = generar(edificio, escribir=False)[0]
            # vigas 1A1 agrupadas por linea (extremos en (u,cota,v), redondeo 1 dec)
            por_linea = {}
            for e in d["elementos"]:
                c = e["correspondencia"]
                if e["tipo"] != "viga" or c["estado"] != "1A1":
                    continue
                # clave = extremos en (u, v) del grid (sin cota: la misma viga
                # en pisos distintos comparte u,v y cambia solo la cota)
                pi = tuple(round(x, 1) for x in (e["p_i_unity"][0], e["p_i_unity"][2]))
                pj = tuple(round(x, 1) for x in (e["p_j_unity"][0], e["p_j_unity"][2]))
                linea = tuple(sorted((pi, pj)))
                por_linea.setdefault(linea, []).append(e)
            multi = [els for els in por_linea.values() if len(els) >= 2]
            self.assertTrue(multi, f"edificio {edificio}: sin lineas de viga multi-nivel")
            for els in multi[:1]:
                niveles = [(e["nivel"], e["tag"]) for e in els]
                self.assertEqual(len({n for n, _ in niveles}), len(niveles))
                # los cortes verticales de la viga (Vz en extremos) cambian por nivel
                vz = {(e["nivel"], round(e["fuerzas"]["Q"][2], 3),
                       round(e["fuerzas"]["Q"][8], 3)) for e in els}
                self.assertGreater(len(vz), 1, "Vz identico entre niveles")

    def test_fuerzas_orden_casos(self):
        d = generar("II", escribir=False)[0]
        keys = list(next(iter(d["elementos"]))["fuerzas"].keys())
        self.assertEqual(keys, list(CASOS))


if __name__ == "__main__":
    unittest.main()