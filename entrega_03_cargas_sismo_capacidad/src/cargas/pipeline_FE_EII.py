"""Pipeline FE reproducible del Edificio II (EII) — adaptador.

Reconstruye el modelo de elementos finitos del EII a partir de los artefactos
PUBLICADOS de `analisis_estructural/edificio_II_casoG_PP_elementos/` (solo
lectura) y resuelve casos con el MISMO motor OpenSeesPy que el Edificio I:

  - MODELO_FE_GEOMETRIA_NODOS.json  -> nodos (tags+coordenadas), columnas_fe,
                                       muros_fe, vigas_fe, cota_nivel.
  - eii_viewer.json                 -> materiales (hormigon G35_10, E=27805.6 MPa),
                                       espesores y ejes de muros, poligonos/espesores
                                       de losas.

NO se modifica el FE original, NO se copian resultados del EI, NO se calibran
factores. Cada decision de modelo sin fuente definitiva queda registrada en
`HISTORIAL_HIPOTESIS` y en el campo `hipotesis` del modelo (para JSON).

Contrato de salida (igual que el EI y que el artefacto publicado):
  - nodos/coordenadas, elementos/conectividad, restricciones,
    materiales/secciones, cargas nodales (por componente), desplazamientos,
    reacciones, fuerzas internas (local y global por elemento) y
    metadata (unidades, convencion de signos).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import openseespy.opensees as ops

REPO = Path(__file__).resolve().parents[3]
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"
ARTIFACT_DIR = REPO / "analisis_estructural" / "edificio_II_casoG_PP_elementos"
MODELO_JSON = ARTIFACT_DIR / "MODELO_FE_GEOMETRIA_NODOS.json"
VIEWER_JSON = ARTIFACT_DIR / "eii_viewer.json"

import sys  # noqa: E402

sys.path.insert(0, str(EI_SRC))
from analisis.fe import resolver as RES  # noqa: E402
from analisis.fe import geometria_fe as GF  # noqa: E402
from analisis.fe import tributaria as TB  # noqa: E402

# --------------------------------------------------------------------------- #
# Parametros documentados / hipotesis del pipeline EII
# --------------------------------------------------------------------------- #
ORDEN_NIVELES = ["EII_CP1S", "EII_CP1", "EII_CP2", "EII_CP3", "EII_CP4"]
NIVEL_BASE = "EII_CP1S"
JUNTA_X_EI_EII = 27.85                 # x de la junta entre edificios (no se unen)
GAMMA_CONCRETO_KN_M3 = 24.5166          # resumen_PP_ELEMENTOS.txt (viewer 24.517)
NU_CONCRETO = 0.2                        # hipotesis de laboratorio (no documentada)
V031_SECCION_POR_DEFECTO = "V.60/80"     # escenario canonical (eii_esfuerzos)
V031_SECCIONES = {                       # hipotesis: V_031 seccion por_resolver
    "V.60/80": (0.6, 0.8),
    "V.30/80": (0.3, 0.8),
}
# Camino vertical para los nodos de la franja D-D' (x=-3.35/-0.3) sin apoyo.
# Rigidez axial equivalente de un montante de muro: E*A/l con el montante
# representativo M_003/M_004 (A=0.6*2.92/2=0.876 m2, l=3.96 m) ->
# k = 27805.6e3(kPa) * 0.876 / 3.96 = 6.15e6 kN/m.
K_FRANJA_VERTICAL_KN_M = 6.15e6


def _fmt(x):
    """Formato de numero publicado (miles con separador, 2 decimales)."""
    return ("%d" % round(x) if abs(x) >= 1e5
            else ("%.2f" % x if abs(x) >= 1 else "%.4E" % x))

HISTORIAL_HIPOTESIS = [
    {
        "id": "material_E_G35",
        "valor": "E=27805.6 MPa, fc=35 MPa (G35_10)",
        "fuente": "eii_viewer.json materiales / solucion_FE_* material.E_mpa",
        "estado": "IMPLEMENTADO_Y_VERIFICADO (documentado)"},
    {
        "id": "poisson_nu",
        "valor": "nu=0.2",
        "fuente": "hipotesis de laboratorio (convencion del motor EI; no documentada para EII)",
        "estado": "HIPOTESIS"},
    {
        "id": "base_fija_cp1s",
        "valor": "apoyos base completos (6 DOF) en EII_CP1S (cota -4.01)",
        "fuente": "cota_nivel / reacciones 45 del artefacto eii_esfuerzos; cimentacion no documentada",
        "estado": "HIPOTESIS"},
    {
        "id": "diafragma_rigido_pisos",
        "valor": "diafragma rigido en plano x-y para EII_CP1..EII_CP4 (CP1S excluido)",
        "fuente": "convencion del motor EI; coincide con n_reacciones=222 del publicador",
        "estado": "HIPOTESIS"},
    {
        "id": "seccion_muro_elemento",
        "valor": "cada muro_fe del MODELO usa la seccion t x L del muro del nivel_inf (eje continuo)",
        "fuente": "MODELO_FE_GEOMETRIA_NODOS.json muros_fe.ids + eii_viewer niveles[*].muros",
        "estado": "HIPOTESIS (verificado contra PP directo de muros del auditoria v1)"},
    {
        "id": "seccion_v031",
        "valor": "V_031 seccion candidata: se conserva el escenario V.60/80 (default) o V.30/80",
        "fuente": "AUDITORIA_PP_EII_v1.md (dos escenarios simultaneos sin eleccion)",
        "estado": "HIPOTESIS_MODELO (sin eleccion definitiva)"},
    {
        "id": "peso_propio_losas",
        "valor": "reparto losa->receptor->nodos FE por algoritmo del motor EI (tributacion "
                 "fina CARGAS_POR_RECEPTOR, malla 0.25 m, soporte mas cercano)",
        "fuente": "eii_viewer losas + analisis/fe/tributaria.py (motor EI)",
        "estado": "IMPLEMENTADO_Y_VERIFICADO (componente losas del auditoria v1)"},
    {
        "id": "peso_propio_elementos",
        "valor": "PP geomatri = A_seccion x L_elemento x gamma (24.5166 kN/m3), bajar a sus "
                 "2 nodos extremos a partes iguales",
        "fuente": "MODELO_FE_GEOMETRIA_NODOS.json + resumen_PP_ELEMENTOS.txt",
        "estado": "IMPLEMENTADO_Y_VERIFICADO (columnas/vigas; muros PENDIENTE_ORIGEN_PIPELINE)"},
    {
        "id": "pm_adic_y_sc",
        "valor": "PM.ADIC y SC del catalogo NO se aplican al caso G (G_EII = PP solo)",
        "fuente": "AUDITORIA_PP_EII_v1.md (NO_INCLUIDO). El caso Q se trata por separado",
        "estado": "DOCUMENTADO"},
]


def cargar_artefactos():
    """Carga (solo lectura) MODELO y viewer. Aborta si falta un dato esencial."""
    for p in (MODELO_JSON, VIEWER_JSON):
        if not p.exists():
            raise FileNotFoundError("ABORTE: falta artefacto publicado del EII: %s" % p)
    modelo = json.loads(MODELO_JSON.read_text(encoding="utf-8"))
    viewer = json.loads(VIEWER_JSON.read_text(encoding="utf-8"))
    for k in ("nodos_por_nivel", "columnas_fe", "muros_fe", "vigas_fe", "cota_nivel"):
        if k not in modelo:
            raise KeyError("ABORTE: MODELO_FE_GEOMETRIA_NODOS sin campo esencial %r" % k)
    return modelo, viewer


class MarcoEII:
    """Ensambla el modelo OpenSees del EII y expone el contrato del motor EI."""

    def __init__(self, v031_seccion: str = V031_SECCION_POR_DEFECTO):
        self.modelo, self.viewer = cargar_artefactos()
        if v031_seccion not in V031_SECCIONES:
            raise ValueError("seccion V_031 no soportada: %r" % v031_seccion)
        self.v031_seccion = v031_seccion
        self.historial_hipotesis = list(HISTORIAL_HIPOTESIS)

        self.nodes = {}
        self.key_of_tag = {}
        self.columna_tramos = []
        self.muros_elem = []
        self.vigas_elem = []
        self.columnas = []
        self.receptor_nodos = {}
        self.master_por_nivel = {}
        self.diafragma_esclavos_por_nivel = {}
        self._base_fixed = set()
        self._next = 1
        self._transf = {}

        self._index_viewer()
        self._cargar_nodos()
        self._cargar_elementos()
        self._receptores_por_nivel()

    # ---------------- datos del viewer ----------------
    def _index_viewer(self):
        mat = self.viewer["materiales"]
        self.E_mpa = float(mat["E_c_MPa"])
        self.E_kpa = self.E_mpa * 1e3
        self.G_kpa = self.E_kpa / (2.0 * (1.0 + NU_CONCRETO))
        self.secciones_sp = dict()
        self.ejes_muro = {}
        for lv in self.viewer["niveles"]:
            for w in lv["muros"]:
                (x0, y0) = w["eje"]["inicio"]
                (x1, y1) = w["eje"]["fin"]
                L = math.hypot(x1 - x0, y1 - y0)
                self.ejes_muro[(lv["id"], w["id"])] = {
                    "t": float(w["espesor"]), "L": L,
                    "inicio": (x0, y0), "fin": (x1, y1)}

    # ---------------- nodos ----------------
    def _cargar_nodos(self):
        for cod, lista in self.modelo["nodos_por_nivel"].items():
            items = lista.items() if isinstance(lista, dict) else lista
            for tag_s, coords in items:
                tag = int(tag_s)
                x, y, z = coords
                self.nodes[tag] = tag
                self.key_of_tag[tag] = (x, y, z)

    def _pos(self, tag):
        return self.key_of_tag[int(tag)]

    def _cota(self, cod):
        return float(self.modelo["cota_nivel"][cod])

    # ---------------- secciones ----------------
    def _sec_rectl(self, b, h, tipo):
        A = b * h
        Iy = b * h ** 3 / 12.0        # fuerte (vertical)
        Iz = h * b ** 3 / 12.0        # debil
        if tipo == "columna":
            bm = max(b, h)
            J = 2.25 * (bm ** 4) / 12.0
            Iy = Iz = bm ** 4 / 12.0
        elif tipo == "viga":
            J = 0.5 * (Iy + Iz)
        else:                          # muro
            J = 0.5 * (Iy + Iz)
        return {"E": self.E_kpa, "G": self.G_kpa, "A": A, "Iz": Iz, "Iy": Iy,
                "J": J, "b": b, "h": h, "hipotesis": False}

    def _ensure_section(self, tag, sec):
        ops.section("Elastic", tag, sec["E"], sec["A"], sec["Iz"], sec["Iy"],
                    sec["G"], sec["J"])

    def _ensure_transf(self, vec):
        key = tuple(round(x, 4) for x in vec)
        if key not in self._transf:
            t = self._next
            self._next += 1
            ops.geomTransf("Linear", t, *vec)
            self._transf[key] = t
        return self._transf[key]

    def _elem(self, tipo, eid, seccion_nombre, nivel, ti, tj, sec):
        """Registra el elemento en memoria (llamada del __init__, sin OpenSees)."""
        ti, tj = int(ti), int(tj)
        (xa, ya, za) = self._pos(ti)
        (xb, yb, zb) = self._pos(tj)
        dx, dy, dz = xb - xa, yb - ya, zb - za
        if abs(dz) > 1e-3:
            vec = (0.0, 1.0, 0.0)
        elif abs(dx) < 1e-6 and abs(dy) < 1e-6:
            vec = (0.0, 1.0, 0.0)
        else:
            vec = (0.0, 0.0, 1.0)
        rec = {"elemento_id": eid, "tipo": tipo, "seccion": seccion_nombre,
               "nivel": nivel, "nodo_i": ti, "nodo_j": tj, "tag": None,
               "transf": None, "vec": vec, "sec_valores": dict(sec),
               "u_i": xa, "v_i": ya, "u_j": xb, "v_j": yb,
               "z_i": za, "z_j": zb}
        if tipo == "columna":
            self.columnas.append(rec)
        elif tipo == "muro":
            self.muros_elem.append(rec)
        else:
            self.vigas_elem.append(rec)
        self.receptor_nodos.setdefault(eid, []).extend([ti, tj])
        return rec

    def _cargar_elementos(self):
        for c in self.modelo["columnas_fe"]:
            b = float(c["seccion"].split("x")[0])
            h = float(c["seccion"].split("x")[1])
            sec = self._sec_rectl(b, h, "columna")
            self._elem("columna", c["id"], c["seccion"], c["nivel_inf"],
                       c["nodo_inf"], c["nodo_sup"], sec)

        for v in self.modelo["vigas_fe"]:
            if v.get("por_resolver"):
                b, h = V031_SECCIONES[self.v031_seccion]
                nombre = self.v031_seccion
                sec = self._sec_rectl(b, h, "viga")
                sec["hipotesis"] = True
            else:
                b, h = v["seccion_geom"]
                nombre = v["seccion_nombre"]
                sec = self._sec_rectl(b, h, "viga")
            self._elem("viga", v["id"], nombre, v["nivel"],
                       v["nodo_i"], v["nodo_j"], sec)

        for w in self.modelo["muros_fe"]:
            wall_id = w["ids"][0][0]
            geom = self.ejes_muro.get((w["nivel_inf"], wall_id))
            if geom is None:
                for cod in (w["nivel_inf"], w["nivel_sup"]):
                    for wid in (w["ids"][0] or []):
                        if (cod, wid) in self.ejes_muro:
                            geom = self.ejes_muro[(cod, wid)]
                            wall_id = wid
                            break
                    if geom is not None:
                        break
            if geom is None:
                raise KeyError(
                    "ABORTE: META del elemento muro %s sin geometria en el viewer "
                    "(ids=%r)" % (w["tag"], w["ids"]))
            # CADA muro_fe es un MONTANTE en un extremo del eje (el panel se modela
            # con 2 montantes t x (L/2) que suman t x L, sin duplicar rigidez).
            sec = self._sec_rectl(geom["t"], geom["L"] / 2.0, "muro")
            self._elem("muro", "M:%s" % wall_id,
                       "%sx%.3f/2" % (geom["t"], geom["L"]),
                       w["nivel_inf"], w["nodo_inf"], w["nodo_sup"], sec)

    def _receptores_por_nivel(self):
        """Por nivel: id de receptor (viga/muro) -> nodos FE de ESE nivel."""
        for v in self.modelo["vigas_fe"]:
            self.receptor_nodos.setdefault(v["id"], [])
        # muros continuos: un elemento contribuye el nodo del nivel al que pertenece
        for w in self.modelo["muros_fe"]:
            wid_inf = w["ids"][0][0]
            wid_sup = w["ids"][0][1] if len(w["ids"][0]) > 1 else wid_inf
            self.receptor_nodos.setdefault(wid_inf, []).append(int(w["nodo_inf"]))
            self.receptor_nodos.setdefault(wid_sup, []).append(int(w["nodo_sup"]))
        for k, v in self.receptor_nodos.items():
            self.receptor_nodos[k] = list(dict.fromkeys(v))

    # ---------------- construccion / restricciones ----------------
    def construir(self):
        ops.wipe()
        ops.model("basic", "-ndm", 3, "-ndf", 6)
        self._next = 1
        self._transf = {}
        for tag in self.nodes:
            x, y, z = self.key_of_tag[tag]
            ops.node(int(tag), x, y, z)
        for rec in (self.columnas + self.vigas_elem + self.muros_elem):
            etag = self._next
            self._next += 1
            rec["tag"] = etag
            sec = rec["sec_valores"]
            self._ensure_section(etag, sec)
            tf = self._ensure_transf(tuple(rec["vec"]))
            rec["transf"] = tf
            ops.element("elasticBeamColumn", etag, int(rec["nodo_i"]),
                        int(rec["nodo_j"]), etag, tf)
        # base fija en CP1S
        z_base = self._cota(NIVEL_BASE)
        for tag in self.nodes:
            if abs(self.key_of_tag[tag][2] - z_base) < 1e-6:
                ops.fix(int(tag), 1, 1, 1, 1, 1, 1)
                self._base_fixed.add(int(tag))
        # diafragma rigido en pisos superiores
        vert = set()
        for rec in self.columnas + self.muros_elem:
            vert.add(int(rec["nodo_i"]))
            vert.add(int(rec["nodo_j"]))
        self._strip_enlazados = []
        for cod in [c for c in ORDEN_NIVELES if c != NIVEL_BASE]:
            zc = self._cota(cod)
            tags = sorted([int(t) for t in self.nodes
                           if abs(self.key_of_tag[t][2] - zc) < 1e-6])
            if not tags:
                continue
            master = tags[0]
            self.master_por_nivel[cod] = master
            strip = [t for t in tags if self._es_nodo_franja_dd(t, vert)]
            esclavos = [t for t in tags if t != master and t not in strip]
            self.diafragma_esclavos_por_nivel[cod] = esclavos
            if esclavos:
                ops.rigidDiaphragm(3, master, *esclavos)
            # FRANJA D-D': nodos de las vigas de franja sin camino vertical
            # (x=-3.35 y x=-0.3). Se excluyen del diafragma (su u,v queda libre
            # dentro de la losa) y se les da camino vertical rigidamente al nodo
            # con camino vertical mas cercano del mismo nivel (0.15 m: montantes
            # de M_003_B/M_004_B). Se evita ligar el nodo al master del piso:
            # acoplaria la rotacion rx/ry del diafragma al w del nodo (artefacto
            # de max_desp_z).
            for t in strip:
                anchor = min((a for a in vert
                              if abs(self.key_of_tag[a][2] - zc) < 1e-6),
                             key=lambda a: ((self.key_of_tag[a][0]
                                             - self.key_of_tag[t][0]) ** 2
                                            + (self.key_of_tag[a][1]
                                               - self.key_of_tag[t][1]) ** 2, a))
                ops.rigidLink("beam", anchor, t)
                self._strip_enlazados.append((anchor, t))
        if self._strip_enlazados:
            self.historial_hipotesis.append({
                "id": "franja_DD_rigidLink_apoyo",
                "valor": ("nodos de la franja D-D' sin camino vertical (x=-3.35 y "
                          "x=-0.3; %d en total) reciben camino vertical con "
                          "rigidLink('beam') al nodo con camino vertical mas "
                          "cercano del mismo nivel (0.15 m hacia montantes de "
                          "M_003_B/M_004_B); se excluyen de los esclavos del "
                          "diafragma. Referencia publicada: n_springs_vert=88")
                          % len(self._strip_enlazados),
                "estado": "HIPOTESIS (documentada, sin calibracion)"})
        self.historial_hipotesis.append({
            "id": "diafragma_aplicado",
            "valor": "CP1S excluido; master por nivel aplicado",
            "estado": "EJECUTADO"})

    def _es_nodo_franja_dd(self, tag, vert):
        """Nodo de piso de la franja D-D' (x=-3.35 o x=-0.3) sin camino vertical."""
        if tag in vert:
            return False
        x = self.key_of_tag[tag][0]
        return abs(x - (-3.35)) < 1e-3 or abs(x - (-0.3)) < 1e-3

    # ---------------- niveles tributarios (adaptador EI) ----------------
    def nivelFE_adaptado(self, cod):
        """NivelFE en el formato del motor EI desde el viewer del EII."""
        lv = next(l for l in self.viewer["niveles"] if l["id"] == cod)
        vigas = [{"id": v["id"], "pts": [v["inicio"], v["fin"]]} for v in lv["vigas"]]
        muros = [{"id": w["id"], "ua": w["eje"]["inicio"][0],
                  "va": w["eje"]["inicio"][1], "ub": w["eje"]["fin"][0],
                  "vb": w["eje"]["fin"][1]} for w in lv["muros"]]
        losas = []
        for lo in lv["losas"]:
            losas.append({
                "id": lo["id"], "espesor": float(lo["espesor"]),
                "poligono": lo["poligono_exterior"],
                "aberturas": lo.get("aberturas_poligonos", []),
                "apoyos": lo.get("apoyos_validos") or None})
        return type("NivelFE_EII", (), {
            "id": cod, "vigas": vigas, "muros": muros, "losas": losas})

    def receptor_nodos_de_nivel(self, cod):
        """Receptores del nivel `cod` con sus nodos FE de ese nivel (mismo plano)."""
        zc = self._cota(cod)
        out = {}
        for rid, tags in self.receptor_nodos.items():
            tags_z = [int(t) for t in tags if abs(self.key_of_tag[t][2] - zc) < 1e-6]
            if tags_z:
                out[rid] = tags_z
        return out

    # ---------------- cargas ----------------
    def peso_propio_nodal(self):
        """PP de elementos (geometria x gamma) repartido a nodos con camino
        vertical (columnas/muros) y a los enlazados de la franja D-D'.

        Cada peso W se parte en 2 mitades; una mitad que caiga en un nodo sin
        camino vertical se deriva al nodo con camino vertical mas cercano del
        mismo nivel (receptor), de modo que las cargas queden sobre apoyos
        (equivalente a la tributacion por receptor del artefacto publicado).
        La suma total de W se conserva exactamente.
        """
        soporte = self._nodos_soporte_vertical()
        cargas = {}
        if not getattr(self, "_pp_ruteado_registrado", False):
            self._pp_ruteado_registrado = True
            self.historial_hipotesis.append({
                "id": "pp_elementos_ruteado_a_receptor",
                "valor": ("el PP de cada elemento se entrega por mitades a nodos "
                          "con camino vertical (columna/muro) o a los enlazados "
                          "de la franja D-D'; mitades sobre nodos de viga sin "
                          "apoyo se deriva al receptor vertical mas cercano del "
                          "mismo nivel (tributacion por receptor, igual que la "
                          "losa). Total conservado."),
                "estado": "HIPOTESIS (documentada)"})
        for rec in self.columnas + self.vigas_elem + self.muros_elem:
            sec = rec["sec_valores"]
            A = sec["A"]
            (xa, ya, za) = (rec["u_i"], rec["v_i"], rec["z_i"])
            (xb, yb, zb) = (rec["u_j"], rec["v_j"], rec["z_j"])
            L = math.hypot(xb - xa, yb - ya, zb - za)
            W = A * L * GAMMA_CONCRETO_KN_M3
            ends = [int(rec["nodo_i"]), int(rec["nodo_j"])]
            cod = self._nivel_de_z(rec["z_i"]) if abs(rec["z_i"] - rec["z_j"]) < 1e-6 else None
            for e in ends:
                if e in soporte:
                    tag = e
                else:
                    tag = self._receptor_mas_cercano(
                        e, [t for t in soporte
                            if abs(self.key_of_tag[t][2]
                                   - self.key_of_tag[e][2]) < 1e-6])
                    if cod is not None:
                        r2 = self._registrar_ruteo("PP_elemento", e, tag, W / 2.0,
                                                   cod, rec["elemento_id"])
                        if r2 is None:
                            tag = e
                cur = cargas.setdefault(tag, [0.0] * 6)
                cur[2] -= W / 2.0
        return cargas

    def _receptor_mas_cercano(self, nodo, candidatos):
        """Nodo con camino vertical mas cercano en el mismo nivel, por distancia."""
        if not candidatos:
            return nodo
        x0, y0 = self.key_of_tag[nodo][:2]
        return min(candidatos,
                   key=lambda c: ((self.key_of_tag[c][0] - x0) ** 2
                                  + (self.key_of_tag[c][1] - y0) ** 2, c))

    # ---------------- auditoria de ruteo ----------------
    def _voids_del_nivel(self, cod):
        """Poligonos de vano (aberturas) de las losas del nivel `cod`."""
        nf = self.nivelFE_adaptado(cod)
        out = []
        for lo in nf.losas:
            for ab in (lo.get("aberturas") or []):
                out.append({"losa": lo["id"], "poligono": ab})
        return out

    def _clasificar_ruteo(self, nodo, receptor, cod, elem_id=None):
        """Clasifica una transferencia nodo->receptor del mismo nivel.

        - DOCUMENTADA: el par comparte el mismo elemento (camino por el eje de
          la pieza) o existe un rigidLink explicito.
        - SIN_CAMINO_ESTRUCTURAL_CONFIRMADO: el segmento recto cruza un vano de
          losa o sale del edificio (junta) => NO hay continuidad de tablero;
          esta carga queda PENDIENTE.
        - HIPOTESIS_GEOMETRICA_DEFENDIBLE: resto (tablero continuo sin vanos que
          interrumpen el paso; hipotesis geometrica de proximidad).
        """
        if receptor == nodo:
            return "DOCUMENTADA", "carga aplicada en su propio nodo"
        pares = self._pares_mismo_elemento(nodo, receptor)
        if pares:
            return "DOCUMENTADA", ("el receptor es un extremo del mismo elemento "
                                   "(%s): camino por el eje de la pieza" % pares)
        if self._segmento_cruza_void(nodo, receptor, cod):
            return ("SIN_CAMINO_ESTRUCTURAL_CONFIRMADO",
                    "el segmento recto cruza un vano de losa (patio/hueco): sin "
                    "continuidad de tablero confirmada")
        if abs(self.key_of_tag[receptor][0]) > JUNTA_X_EI_EII:
            return ("SIN_CAMINO_ESTRUCTURAL_CONFIRMADO",
                    "el receptor queda al otro lado de la junta EI/EII")
        return ("HIPOTESIS_GEOMETRICA_DEFENDIBLE",
                "tablero continuo plausible entre el nodo y el soporte vertical "
                "mas cercano del mismo nivel (proximidad geometrica; no hay vano "
                "que interrumpa el paso)")

    def _segmento_cruza_void(self, a, b, cod):
        from shapely.geometry import LineString
        pa = self.key_of_tag[a]
        pb = self.key_of_tag[b]
        seg = LineString([(pa[0], pa[1]), (pb[0], pb[1])])
        for v in self._voids_del_nivel(cod):
            try:
                from shapely.geometry import Polygon
                if seg.intersects(Polygon(v["poligono"]).buffer(1e-6)):
                    return True
            except Exception:
                continue
        return False

    def _pares_mismo_elemento(self, a, b):
        """Id del/los elementos que comparten a sus dos extremos en `a` y `b`."""
        ids = []
        for rec in self.columnas + self.vigas_elem + self.muros_elem:
            ni, nj = int(rec["nodo_i"]), int(rec["nodo_j"])
            if set((ni, nj)) == set((a, b)):
                ids.append(rec["elemento_id"])
        return ids[0] if ids else None

    def _tipo_receptor(self, t):
        if t in self._nodos_columnas():
            return "columna"
        if t in {int(x) for x in self._nodos_soporte_vertical()} - self._nodos_columnas():
            return "muro"
        return "enlazado_franja_DD"

    def _nivel_de_z(self, z):
        for cod in ORDEN_NIVELES:
            if abs(self._cota(cod) - z) < 1e-6:
                return cod
        return "?"

    def _registrar_ruteo(self, origen, nodo, receptor, carga_kN, cod, elem_id=None):
        if not hasattr(self, "cargas_redirigidas"):
            self.cargas_redirigidas = []
        p = self.key_of_tag[nodo]
        if receptor == nodo:
            return None
        clase, razon = self._clasificar_ruteo(nodo, receptor, cod, elem_id)
        q = self.key_of_tag[receptor]
        dist = math.hypot(q[0] - p[0], q[1] - p[1], q[2] - p[2])
        pendiente = clase.startswith("SIN")
        self.cargas_redirigidas.append({
            "origen": origen, "elemento_id": elem_id,
            "nivel": self._nivel_de_z(p[2]),
            "nodo_original": nodo,
            "nodo_original_xyz": [round(v, 3) for v in p],
            "receptor": receptor,
            "receptor_xyz": [round(v, 3) for v in q],
            "tipo_receptor": self._tipo_receptor(receptor),
            "distancia_m": round(dist, 6),
            "carga_efectiva_kN": round(carga_kN, 6),
            "carga_transferida_kN": 0.0 if pendiente else round(carga_kN, 6),
            "clasificacion": clase,
            "razon": razon,
            "estado": ("PENDIENTE" if pendiente
                       else "TRANSFERIDA" if clase == "HIPOTESIS_GEOMETRICA_DEFENDIBLE"
                       else "APLICADA"),
        })
        return None if pendiente else receptor

    def losa_tributaria_nodal(self, incluir_sc=False, mallado=0.25):
        """Cargas de losa (PP; G) por el algoritmo tributario del motor EI.

        La carga que el algoritmo entrega a nodos sin camino vertical descendente
        (columnas; nodos cuyo peso se vierte a traves de una pila de columnas)
        se redirige al nodo de columna mas cercano del mismo nivel: en el
        artefacto publicado cada losa descarga sobre los RECEPTORES portantes
        (columnas/muros axialmente), no sobre las vigas.
        """
        cargas = {}
        repartos = {}
        soporte = self._nodos_columnas()
        soporte |= {int(t) for _, t in getattr(self, "_strip_enlazados", [])}
        if not getattr(self, "_losa_ruteada_registrado", False):
            self._losa_ruteada_registrado = True
            self.historial_hipotesis.append({
                "id": "losa_ruteada_a_receptor",
                "valor": ("la carga de losa en nodos sin pila de columnas se deriva "
                          "al nodo de columna mas cercano del mismo nivel (los nodos "
                          "de la franja D-D' enlazados conservan su parte); total "
                          "conservado."),
                "estado": "HIPOTESIS (documentada)"})
        for cod in ORDEN_NIVELES:
            nf = self.nivelFE_adaptado(cod)
            nodos = self.receptor_nodos_de_nivel(cod)
            cargas_por_losa = {lo["id"]: (0.0, 0.0) for lo in nf.losas}
            c, r = TB.calcular_cargas_nodales(nf, nodos, cargas_por_losa,
                                              self.key_of_tag,
                                              incluir_sc=incluir_sc,
                                              mallado=mallado)
            for tag, f in c.items():
                tag = int(tag)
                if tag not in soporte:
                    receptor_r = self._receptor_mas_cercano(
                        tag, [t for t in soporte
                              if abs(self.key_of_tag[t][2]
                                     - self.key_of_tag[tag][2]) < 1e-6])
                    r2 = self._registrar_ruteo("losa", tag, receptor_r, f[2],
                                               cod, elem_id=None)
                    if r2 is not None:
                        tag = r2
                cur = cargas.setdefault(tag, [0.0] * 6)
                for i in range(6):
                    cur[i] += f[i]
            repartos[cod] = r
        return cargas, repartos

    def losa_Q_nodal(self, q_Q_kN_m2, mallado=0.25):
        """Sobrecarga Q (q_Q uniforme en kN/m2) distribuida a nodos sin G.

        Mismo flujo tributario que `losa_tributaria_nodal` (mismas losas netas,
        mismos receptores en planta, mismo `distribuir_losa`, mismos pesos por
        nodo y el mismo re-ruteo a nodos con camino vertical), pero con
        PP=0 y PM.ADIC=0: la unica carga es Q = q_Q * area_neta_geometrica por
        losa. La suma por nivel y global queda EXACTA (Q = q_Q * area_neta).
        """
        cargas = {}
        repartos = {}
        soporte = self._nodos_columnas()
        soporte |= {int(t) for _, t in getattr(self, "_strip_enlazados", [])}
        if not getattr(self, "_losa_Q_registrado", False):
            self._losa_Q_registrado = True
            self.historial_hipotesis.append({
                "id": "losa_Q_uniforme_a_receptor",
                "valor": ("Q = q_Q * area_neta de cada losa repartida con el "
                          "mismo algoritmo tributario que el caso G (mismos "
                          "receptores, pesos y re-ruteo a soporte vertical); "
                          "PP=0, PM.ADIC=0 => G ausente. Total Q por nivel y "
                          "global = q_Q * area_neta (exacto)."),
                "estado": "EJECUTADO (Q sin G)"})
        area_total_neto = 0.0
        for cod in ORDEN_NIVELES:
            nf = self.nivelFE_adaptado(cod)
            nodos = self.receptor_nodos_de_nivel(cod)
            soportes = TB._receptor_lineas(nf)
            cargas_por_losa_q = {}
            area_nivel = 0.0
            nivel_sin_fe = []
            por_losa = {}
            for lo in nf.losas:
                s = GF.construir_superficies([lo])[0]
                neto = s["neto"].area
                cargas_por_losa_q[lo["id"]] = neto
                area_nivel += neto
                validos = (set(soportes.keys()) if not lo.get("apoyos")
                           else set(lo["apoyos"]))
                areas, _ = TB.distribuir_losa(
                    s["neto"], {k: v for k, v in soportes.items()
                                if k in validos}, mallado)
                suma = sum(areas.values())
                info = {"area_neta_m2": round(neto, 4),
                        "Q_total_kN": round(q_Q_kN_m2 * neto, 4),
                        "receptores": {}}
                for rid, area in areas.items():
                    frac = area / suma if suma > 0 else 0.0
                    F = frac * q_Q_kN_m2 * neto
                    nl = nodos.get(rid, [])
                    if not nl:
                        nivel_sin_fe.append({"receptor": rid, "losa": lo["id"],
                                              "area_m2": round(area, 4),
                                              "Q_kN": round(F, 4)})
                        continue
                    info["receptores"][rid] = {
                        "area_m2": round(area, 4), "Q_kN": round(F, 4),
                        "n_nodos_fe": len(nl)}
                    pesos = TB._pesos_por_nodo(self.key_of_tag, nl)
                    for tag, w in pesos.items():
                        cur = cargas.get(tag, [0.0] * 6)
                        cur[2] -= F * w
                        cargas[tag] = cur
                por_losa[lo["id"]] = info
            # re-ruteo identico al caso G (nodo sin camino vertical -> soporte
            # mas cercano; SIN_CAMINO queda PENDIENTE en su nodo original)
            for tag in list(cargas.keys()):
                if tag in soporte:
                    continue
                tag = int(tag)
                if abs(self.key_of_tag[tag][2] - self._cota(cod)) > 1e-6:
                    continue
                receptor_r = self._receptor_mas_cercano(
                    tag, [t for t in soporte
                          if abs(self.key_of_tag[t][2]
                                 - self.key_of_tag[tag][2]) < 1e-6])
                fprev = cargas.pop(tag)
                r2 = self._registrar_ruteo("losa_Q", tag, receptor_r,
                                           fprev[2], cod, elem_id=None)
                destino = r2 if r2 is not None else tag
                cur = cargas.setdefault(destino, [0.0] * 6)
                for i in range(6):
                    cur[i] += fprev[i]
            area_total_neto += area_nivel
            repartos[cod] = {
                "por_losa": por_losa,
                "receptores_sin_fe": nivel_sin_fe,
                "area_neta_total_m2": round(area_nivel, 4),
                "area_neta_total_m2_exacta": float(area_nivel)}
        verificacion = {
            "q_Q_kN_m2": q_Q_kN_m2,
            "area_neta_total_m2": round(area_total_neto, 4),
            "Q_esperada_kN": round(q_Q_kN_m2 * area_total_neto, 6),
            "Q_aplicada_kN": round(sum(-f[2] for f in cargas.values()), 6),
        }
        return cargas, repartos, verificacion

    def _nodos_columnas(self):
        """Nodos con camino vertical descendente propio (pila de columnas)."""
        cols = set()
        for rec in self.columnas:
            cols.add(int(rec["nodo_i"]))
            cols.add(int(rec["nodo_j"]))
        return cols

    def _nodos_soporte_vertical(self):
        """Nodos con camino vertical (columna/muro) o enlazados de la franja."""
        vert = set()
        for rec in self.columnas + self.muros_elem:
            vert.add(int(rec["nodo_i"]))
            vert.add(int(rec["nodo_j"]))
        enl = {int(t) for _, t in getattr(self, "_strip_enlazados", [])}
        return vert | enl

    def resolver_caso(self, cargas_nodales_plano: dict):
        """Resuelve con el motor EI. `cargas_nodales_plano`: {nivel: {tag: vec}}."""
        return RES.resolver(self, cargas_nodales_plano)

    def resumen(self):
        return {
            "n_nodos": len(self.nodes),
            "n_columnas": len(self.columnas),
            "n_vigas": len(self.vigas_elem),
            "n_muros": len(self.muros_elem),
            "master_por_nivel": self.master_por_nivel,
            "v031_seccion": self.v031_seccion,
            "E_mpa": self.E_mpa,
        }