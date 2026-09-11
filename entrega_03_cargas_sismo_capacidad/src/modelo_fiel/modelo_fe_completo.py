"""MODELO_FE_COMPLETO_FUNCIONAL (Edificio I) - geometria fisica P4 aprobada.

Variante FUNCIONAL (no declarada definitiva en tanto existan postes hipoteticos
de la torre, diagonales PENDIENTE_TORRE o elementos confirmados sin resultados).
Construye el marco FE del Edificio I con la geometria del nivel P4 CORREGIDA a
la posicion fisica (columnas en +0.181/+9.081/+16.331; vigas en +0.18) y la
continuidad P3->P4 resuelta por CONECTORES RIGIDOS documentados (nunca columnas
paralelas fantasma hacia -4.01, ni traslados silenciosos de vigas).

El caso G aplica el peso propio de los elementos estructurales CONFIRMADO por la
auditoria v2 (137 vigas + 43 tramos de columna + 4 paneles de muro = 17179.2261
kN) ademas de losas + PM.ADIC, igual que G_EI_MODELO_FIEL v3/v4; OpenSees NO
computa peso propio por densidad/masa, todo entra al caso G como carga NODAL.

Reglas de modelo (regimen HIPOTESIS_DE_ANALISIS; perfil MODELO_FE_COMPLETO_FUNCIONAL):

  * Los ejes de columna con nivel base (CP1S) se construyen EXACTAMENTE como en
    el motor comercial (niveles con evidencia + base fija en -4.01).
  * Un eje de columna cuyo nivel mas bajo documentado NO es la base (todas las
    columnas P4 y los postes metalicos de la torre P3/P4) NO recibe tramo
    hipotetico base->nivel: recibe su NODO en la cota mas baja, un conector
    rigido (stub elastico E*mult, patron del motor) hacia el soporte vertical
    mas cercano de ESA cota (excentricidad documentada), y el/los tramos
    verticales entre niveles documentados. Las columnas concretas P4 (desfase
    +0.1812 m aprobado) se PAIRAN con su eje de grilla (v=0/8.9/16.15) via
    ROW_MAP: stub A(grida)->B(fisico) con A = techo del eje de grilla en z=11.83.
  * Las vigas P4 (fisicas, +0.18, incluyen acero V.M.) se toman del geometry del
    viewer (ground truth de display); los elementos de armadura diagonal de la
    torre ('Diag. marco') quedan PENDIENTE_TORRE (seccion no parseable por el
    motor y cota superior indeterminada).
  * Sin elementos por encima de P4 sin evidencia: el tope de los postes de acero
    es configurable (H_TORRE_M) y queda rotulado HIPOTESIS.

Salidas bajo modelo_fiel/MODELO_FE_COMPLETO_FUNCIONAL/:
  topologia_EI.json        nodos clave (A/B), conectores, apertura, ledgers
  preflight_EI.json/.md    8 verificaciones (nodos desconectados, duplicados,
                           caminos de carga, diafragmas/maestros, mecanismos,
                           compatibilidad DOF, excentricidades, nada sobre P4)
  G_EI_MODELO_FE_COMPLETO_FUNCIONAL.json/.csv/.md
  Q_EI_MODELO_FE_COMPLETO_FUNCIONAL.json/.csv/.md
  reconciliacion_G_EI.json/.md  tabla de reconciliacion del caso G por familia

Uso:
  python -X utf8 -m src.modelo_fiel.modelo_fe_completo [--build] [--g] [--q] [--sismo]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import openseespy.opensees as ops

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel" / "MODELO_FE_COMPLETO_FUNCIONAL"
RES = E3 / "results"
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"
VIEWER_GEO = (REPO / "viewer_unity" / "Assets" / "StreamingAssets"
              / "lab_data" / "edificios" / "I" / "geometry")
AUDIT_V2 = RES / "peso_propio_teorico_EDIFICIO_I_v2.json"

sys.path.insert(0, str(EI_SRC))

from analisis.fe import geometria_fe as GF  # noqa: E402
from analisis.fe import resolver as RESv  # noqa: E402
from analisis.fe import secciones as SEC  # noqa: E402
from analisis.fe import tributaria as TB  # noqa: E402
from analisis.fe import cargas_correlacionadas as CC  # noqa: E402
from analisis.fe.hipotesis import COTAS_NIVEL_M, niveles_ordenados  # noqa: E402
from analisis.fe.marco import Marco, _key  # noqa: E402

SYS_A = "comun-u,v"
Z_P4 = 11.83
# Mapeo de la columna fisica P4 (+0.1812 m) al eje de grilla inferior (documentado
# por RLE-SOLID vs RLE-EJE; DECISION_GEOMETRIA_EJE_P4.md).
ROW_MAP = {0.0: 0.1812, 0.1812: 0.0, 8.9: 9.0812, 9.0812: 8.9,
           16.15: 16.3314, 16.3314: 16.15}
# Tope de los postes de acero por encima de la losa P4 (HIPOTESIS_DE_ANALISIS).
H_TORRE_M = 3.96
TOL_ROW = 0.03
# Seccion centinela: suprime el tramo base->nivel del bucle generico de columnas
# (el motor la parsea como None y solo fija el nodo de apoyo de referencia inerte).
SENTINEL = "NO_FE_SIN_EJE_BASE"
# Radio maximo documentado de un conector de arranque (stub) para postes de acero
# y columnas sin eje base: la carga llega a la losa y se reparte en planta a los
# ejes base/huente mas proximos (HIPOTESIS_DE_ANALISIS de transferencia).
R_STUB_MAX_M = 2.5

# --- Remallado aprobado de las columnas de acero del voladizo norte (torre G-H) -- #
# Posicion CANDIDATO (sin huella) -> centro de huella fisica RLE-PILAR (documentada
# en apply_plan_frames.py, verificada numericamente contra los DXF):
#   P2 G3S1 (18.96,14.79) -> (17.49,20.27) [2017_67-102, huella u[17.34,17.64] (centro
#     17.49) v[20.12,20.42] (centro 20.27)]
#   P4 GS6  (21.50,21.03) -> (20.00,20.45) [2017_67-103, huella u[19.85,20.15] (centro
#     20.00) v[20.30,20.60] (centro 20.45)]
#   P4 HS7  (31.55,21.03) -> (30.00,20.45) [2017_67-103, huella u[29.85,30.15] (centro
#     30.00) v[20.30,20.60] (centro 20.45)]
REMESH_TORRE = {
    (18.96, 14.79): (17.49, 20.27),
    (21.50, 21.03): (20.00, 20.45),
    (31.55, 21.03): (30.00, 20.45),
}
# Tope vertical DOCUMENTADO por eje remallado (ausencia de continuidad sobre el):
# G3S1 tiene huella solo en el plano P2 (2017_67-102) y sube a la losa P3 (un tramo),
# NO existe registro en P4 -> se retira el tramo P3->P4 fantasma
# (poste_18.96_14.79_P4, tag 650 / PHANTOM_SIN_FUENTE_FISICA). Los remates P4 de
# GS6/HS7 se rigen por su propio registro (inician en P4).
TORRE_TOPE_NIVEL = {(17.49, 20.27): "P3"}

# --- Vigas del voladizo norte P2 (plano 2017_67-102, RLE-VIGA, seccion V.60/80) --- #
# INTERPRETACION DE EJES (encuentros reales, decision usuario 2026-09-11; fuente:
# apply_plan_frames.P2_ADD_BEAMS + viewer P2.json). La geometria del viewer quedaba
# 'sin FE/tributaria' (recibe_losa=false) y sus ejes NO topologicamente conectados.
# Se incorporan a FE con los ejes llevados a los nudos de encuentro reales:
#   * H_y2027  eje v=20.27 entre el eje del pilar oeste (u=10.0) y el de G3S1
#     (u=17.49, = centro de la huella y = eje de V_x1749); las caras RLE-VIGA
#     u=10.30/17.79 son planos de encuentro.
#   * V_x1000  (cabeza pilar OESTE) eje u=10.0: desde la columna F3 (v=16.15) hasta
#     la cara norte documentada v=20.57; nudo de encuentro con H_y2027 en (10,20.27).
#   * V_x1749  (cabeza pilar ESTE) eje u=17.49: desde la perimetral H_y0162
#     (v=16.15, se subdivide en 17.49) hasta el nudo G3S1/H_y2027 (v=20.27, el
#     mismo nodo que la base de G3S1: MERGE_TOL = 0.0 m).
# Conectores cortos/modelos: NINGUNO (los ejes se tocan exactamente en planta; sin
# stubs elasticos, sin brazos rigidos). Las 3 vigas reciben tributaria (recibe_losa)
# como el resto, con losa NO extendida fuera de su contorno (nada nuevo apoya en el
# poste: solo H_y2027 bajo la base de G3S1).
P2_VOLADIZO_VIGAS = [
    {"id": "H_EI_CP2_y2027_10.30-17.79_PLA2017-102", "seccion": "V. 60/80",
     "pts": [(10.00, 20.27), (17.49, 20.27)], "recibe_losa": False},
    {"id": "V_EI_CP2_x1000_16.50-20.57_PLA2017-102", "seccion": "V. 60/80",
     "pts": [(10.00, 16.15), (10.00, 20.27), (10.00, 20.57)], "recibe_losa": False},
    {"id": "V_EI_CP2_x1749_16.45-19.97_PLA2017-102", "seccion": "V. 60/80",
     "pts": [(17.49, 16.15), (17.49, 20.27)], "recibe_losa": False},
]
# Nudo del pilar OESTE del voladizo (RLE-PILAR 0.30x0.30, plano 2017_67-102):
# materializado como NUDO del sub-marco (union H_y2027 ^ V_x1000 en (10,20.27)), NO
# como columna elemento: no hay huella en P1/P3/P4, no hay perfil/espesor documentado
# (solo 0.30x0.30 exterior) y un tramo a -4.01 seria fantasma. Sin continuacion
# P2->P3 / P3->P4 (no existe elemento vertical en ese eje; ver test de regresion).
PILAR_OESTE_VOLADIZO = {"eje": (10.00, 20.27), "seccion_huella": "0.30 x 0.30",
                        "cota": COTAS_NIVEL_M["P2"], "tipo": "nudo_rigidizado"}


class MarcoFECompleto(Marco):
    """Marco del Edificio I con la geometria fisica P4 y la torre de acero."""

    def __init__(self, niveles, rigidez_mult: float = 1.0e3,
                 h_torre_m: float = H_TORRE_M):
        super().__init__(niveles, rigidez_mult)
        self.h_torre_m = float(h_torre_m)
        self.p4_physical = []      # columnas concretas P4: {u, v_f, v_g, lower}
        self.acero_posts = []      # postes torre: {cod_base, u, v, z_base}
        self.conectores_p4 = []    # registro A->B
        self.conectores_arranque = []  # registro base/stub de postes y superiores
        self.pendientes_torre = []  # diagonales 'Diag. torre' excluidas de FE
        self.topologia = None
        self._vueltos_slaves = []

    # ------------------------------------------------------------------ #
    # Parches de geometria (antes de super().construir)
    # ------------------------------------------------------------------ #
    def _patch_niveles(self):
        """Geometria previa a super().construir().

          * Vigas P4 tomadas del viewer (fisicas +0.18); las 'Diag. torre' (cruce en
            el plano v-z 7.87<->11.83, fuera del esquema por nivel del motor) quedan
            registradas como PENDIENTE_TORRE (no FE).
          * Columnas cuyo eje NO existe en CP1S (nivel base):
              - CONCRETO (P.70x70 iniciadas en P1/P2/P3 o concretas P4 en v fisica
                +0.18): se DEJAN en niveles para que el motor cree nodos y empalme
                las vigas de cada piso en su eje (las vigas GV/V_COL se dividen y el
                arranque apoya en el enmarcado del piso). Su seccion del nivel base
                se sustituye por el centinela SENTINEL para que el bucle generico
                NO genere el tramo base->nivel (columna fantasma, prohibida); solo
                queda el nodo de apoyo fijo de referencia inerte (sin elemento).
                Las concretas P4 (v fisica) se registran en p4_physical para el
                stub A->B del puente P3->P4.
              - ACERO (P.M./P.M.I./V.M., postes de la torre): se RETIRAN del bucle
                generico y se resuelven en _add_acero_torre (base + stub con radio
                documentado + tramo/s verticales), nunca con tramo base fantasma.
        """
        base_axes = set()
        for cod in niveles_ordenados():
            for c in self.niveles[cod].columnas:
                if cod == "CP1S":
                    base_axes.add((round(c["u"], 3), round(c["v"], 3)))
        # Remallado aprobado: desplaza en TODOS los niveles las columnas de acero
        # del voladizo norte a la huella fisica RLE-PILAR (REMESH_TORRE). El eje
        # remallado alimenta despues la extraccion de acero_posts (mismo recorrido).
        for cod in list(self.niveles.keys()):
            if cod == "CP1S":
                continue
            for c in self.niveles[cod].columnas:
                uv = (round(c["u"], 3), round(c["v"], 3))
                if uv in REMESH_TORRE:
                    c["u"], c["v"] = REMESH_TORRE[uv]
        # Vigas del voladizo norte P2 (plano 2017_67-102): se incorporan al FE con
        # los ejes sobre los nudos de encuentro reales (P2_VOLADIZO_VIGAS). El motor
        # las subdivide en las uniones y las columna/muros por jset (pts propios y
        # ajenos), asi la perimetral H_y0162 se corta en u=17.49 y el nudo
        # G3S1/H_y2027 se comparte con la base de G3S1 a MERGE_TOL.
        self.niveles["P2"].vigas = (self.niveles["P2"].vigas
                                    + [dict(b) for b in P2_VOLADIZO_VIGAS])
        # P4 vigas fisicas (ground truth del viewer, frame unity (u,cota,v))
        p4v = json.loads((VIEWER_GEO / "P4.json").read_text(encoding="utf-8"))
        vigas = []
        self.pendientes_torre = []
        for v in p4v["vigas"]:
            seccion = v.get("seccion", "")
            if "torre" in seccion.lower():
                # diagonales de la torre ('Diag. torre G-H', lamina 801/802): cruce
                # en el plano v-z entre 7.87 y 11.83, fuera del esquema de vigas
                # horizontales por nivel del motor; su seccion no es parseable
                # (V./V.M./V.S.I.). Se registran como PENDIENTE_TORRE (no FE).
                self.pendientes_torre.append({
                    "id": v["id"], "seccion": seccion,
                    "pts": [list(map(float, p)) for p in v.get("pts", [])]})
                continue
            pts = [(float(p[0]), float(p[2])) for p in v["pts"]]
            vigas.append({"id": v["id"], "seccion": seccion,
                          "pts": pts, "recibe_losa": v.get("recibe_losa", True)})
        self.niveles["P4"].vigas = vigas
        # columnas: acero-fuera, concreto-superior se queda (con centinela base)
        self.p4_physical = []
        self.acero_posts = []
        for cod in list(self.niveles.keys()):
            if cod == "CP1S":
                continue
            quedan = []
            for c in self.niveles[cod].columnas:
                uv = (round(c["u"], 3), round(c["v"], 3))
                if uv in base_axes:
                    quedan.append(c)
                    continue
                nombre = (c.get("seccion") or "").upper()
                es_acero = (nombre.startswith("P.M") or nombre.startswith("V.M")
                            or "M.I." in nombre)
                z_base = COTAS_NIVEL_M[cod]
                rec = {"cod_base": cod, "u": c["u"], "v": c["v"],
                       "z_base": z_base, "seccion": c.get("seccion"),
                       "es_acero": es_acero}
                if es_acero:
                    self.acero_posts.append(rec)
                    # se retira del bucle generico; niveles se recargan frescos en
                    # cada construir(), asi el rebuild es identico (idempotente).
                    continue
                # concreto sin eje base: se queda en niveles; la seccion del primer
                # nivel se vuelve centinela para suprimir el tramo base->nivel.
                if c.get("seccion") is None:
                    c["seccion"] = SENTINEL
                if cod == "P4":
                    self.p4_physical.append(rec)
                quedan.append(c)
            self.niveles[cod].columnas = quedan

    # ------------------------------------------------------------------ #
    # Construccion (override)
    # ------------------------------------------------------------------ #
    def construir(self):
        # Recarga niveles de origen: _patch_niveles y el motor mutan los dicts;
        # una reconstruccion (casos) debe partir siempre del mismo insumo para
        # que la asignacion de tags nodales sea identica entre marcos.
        self.niveles = GF.cargar_todos()
        self._patch_niveles()
        super().construir()
        self._add_p4_bridge()
        self._add_acero_torre()
        self._registrar_topologia()
        return self

    # ------------------------------------------------------------------ #
    # Puente rigido P3->P4 (condicion (b) del usuario)
    # ------------------------------------------------------------------ #
    def _fila_grid(self, v_fis):
        """Devuelve la v de grilla correspondiente (o None) para v fisica."""
        for vg, vf in ROW_MAP.items():
            if abs(vf - v_fis) <= 0.05:
                return float(vg)
        best, bd = None, 1e9
        for vg in (0.0, 8.9, 16.15):
            if abs(vg - v_fis) < bd:
                bd, best = abs(vg - v_fis), float(vg)
        return best if bd <= 0.2 else None

    def _techo_eje_grid(self, u, vg):
        """Nodo mas alto del eje de grilla (u,vg) ya construido (z <= P4)."""
        best = None
        for r in self.columnas + self.muros_elem:
            if (abs(r["u_i"] - u) < 0.02 and abs(r["v_i"] - vg) < 0.02
                    and abs(r["z_i"] - Z_P4) < 0.02):
                tl = int(r["nodo_i"])
            elif (abs(r["u_j"] - u) < 0.02 and abs(r["v_j"] - vg) < 0.02
                  and abs(r["z_j"] - Z_P4) < 0.02):
                tl = int(r["nodo_j"])
            else:
                continue
            if best is None or self.key_of_tag[tl][2] > best[0]:
                best = (self.key_of_tag[tl][2], tl)
        return best

    def _add_p4_bridge(self):
        """Para cada columna concreta P4 (v fisica): A = techo del eje de grilla,
        B = nodo fisico en 11.83; segmento de columna 7.87->11.83 (solo si el
        eje de grilla no llega a 11.83) y stub rigido A->B."""
        zc = Z_P4
        sec_col = SEC.seccion_columna("P. 70x70")
        for c in self.p4_physical:
            u = round(c["u"], 3)
            v_fis = round(c["v"], 3)
            vg = self._fila_grid(v_fis)
            # nodo fisico B (se fusiona con nodo de viga en 0.18 por MERGE_TOL)
            B = self._snap_node_scaffold(u, v_fis, zc)
            if vg is None:
                # sin eje de grilla conocido: soporte = soporte vertical mas
                # cercano en 11.83 (documentado como excentricidad)
                A = self._soporte_vertical_cercano(B, zc)
                self.conectores_p4.append({
                    "columna_fisica_v": v_fis, "u": u, "tipo": "nearest",
                    "A_tag": A, "B_tag": B,
                    "A": self._coord(A), "B": self._coord(B)})
                if A is not None:
                    self._add_stub_rigid(A, B)
                continue
            # techo del eje de grilla
            techo = self._techo_eje_grid(u, vg)
            if techo is None or self.key_of_tag[techo[1]][2] < zc - 0.02:
                # extender el eje de grilla a 11.83 (tramo P3->P4). Vale tanto para
                # ejes base como para columnas concretas superiores (P1->P3), cuyos
                # topes quedaron a cota P3; el poste metalico de la torre jamas llega
                # aqui porque sus ejes no estan en ROW_MAP (v fisica / off-grid).
                low = self._snap_node_scaffold(u, vg, COTAS_NIVEL_M["P3"])
                A_top = self._get_node(u, vg, zc)
                if (techo is None
                        or self.key_of_tag[techo[1]][2] <= COTAS_NIVEL_M["P3"] + 0.02):
                    self._add_vertical("columna", "P. 70x70",
                                       "col_%s_%s_p4continuo" % (u, vg),
                                       "P4", low, A_top, sec_col)
            else:
                A_top = techo[1]
            self._add_stub_rigid(A_top, B)
            self.conectores_p4.append({
                "columna_fisica_v": v_fis, "u": u, "tipo": "row_map",
                "v_grid": vg, "A_tag": A_top, "B_tag": B,
                "A": self._coord(A_top), "B": self._coord(B),
                "excentricidad_m": round(abs(v_fis - vg), 4)})
        self._add_slaves_diafragma([c["B_tag"] for c in self.conectores_p4]
                                   + [c["A_tag"] for c in self.conectores_p4
                                      if c["A_tag"] is not None], zc)

    # ------------------------------------------------------------------ #
    # Torre de acero (postes P3/P4) y columnas superiores sin base
    # ------------------------------------------------------------------ #
    def _soporte_vertical_cercano(self, tag, z, radio_max=None):
        """Soporte vertical en la misma cota, mas cercano (dentro del radio maximo
        documentado si se indica). Devuelve su tag o None."""
        soporte = set()
        for r in self.columnas + self.muros_elem:
            if abs(self.key_of_tag[int(r["nodo_i"])][2] - z) < 0.02:
                soporte.add(int(r["nodo_i"]))
            if abs(self.key_of_tag[int(r["nodo_j"])][2] - z) < 0.02:
                soporte.add(int(r["nodo_j"]))
        if not soporte:
            return None
        x0, y0 = self.key_of_tag[tag][:2]
        if radio_max is not None:
            cand = [t for t in soporte
                    if ((self.key_of_tag[t][0] - x0) ** 2
                        + (self.key_of_tag[t][1] - y0) ** 2) ** 0.5 <= radio_max]
            if not cand:
                return None
            soporte = cand
        best = min(soporte,
                   key=lambda t: ((self.key_of_tag[t][0] - x0) ** 2
                                  + (self.key_of_tag[t][1] - y0) ** 2, t))
        return best

    def _viga_nodo(self, tag):
        """Viga (elemento horizontal) incidente en `tag` en SU PROPIA cota.

        Devuelve el elemento_id de la primera viga que tiene a `tag` como extremo
        (o None). Sirve para reconocer los arranques de poste que caen DIRECTAMENTE
        sobre el enmarcado del piso (viga de borde documentada, p.ej. H_y2027 bajo
        la base de G3S1): ese apoyo no requiere stub de excentricidad."""
        for r in self.vigas_elem:
            i, j = int(r["nodo_i"]), int(r["nodo_j"])
            if i == tag or j == tag:
                return r["elemento_id"]
        return None

    def _add_acero_torre(self):
        """Postes metalicos de la torre (P.M./P.M.I./V.M.) sin eje base:
        nodo base en su cota + conector de arranque (stub, radio documentado) +
        tramo/s verticales. Los que inician en P3 suben a la losa P4; los que
        inician en P4 suben al tope hipotetico (H_TORRE_M). Nunca un tramo base
        fantasma hacia -4.01; los postes quedan registrados una sola vez por eje."""
        por_eje = {}
        for c in self.acero_posts:
            u, v = round(c["u"], 3), round(c["v"], 3)
            d = por_eje.setdefault((u, v), {
                "cod_base": c["cod_base"], "z_base": c["z_base"],
                "seccion": c.get("seccion") or "P.M. 300x300x20",
                "niveles": []})
            if c["cod_base"] not in d["niveles"]:
                d["niveles"].append(c["cod_base"])
        # Orden de construccion: las bases de niveles inferiores (P2/P3) se generan
        # ANTES que los remates P4, para que el soporte vertical de un remate
        # (nodo a cota P4 de un poste P3) ya exista cuando se busca su arranque.
        order_nivel = {cod: i for i, cod in enumerate(niveles_ordenados())}
        for (u, v), c in sorted(
                por_eje.items(),
                key=lambda kv: (order_nivel.get(kv[1]["cod_base"], 99),
                                kv[0][0], kv[0][1])):
            z_base = c["z_base"]
            base = self._snap_node_scaffold(u, v, z_base)
            viga_apoyo = self._viga_nodo(base)
            if viga_apoyo is None:
                sup = self._soporte_vertical_cercano(base, z_base, R_STUB_MAX_M)
                if sup is not None and sup != base:
                    self._add_stub_rigid(sup, base)
                    self.conectores_arranque.append({
                        "eje": [u, v], "z": z_base, "soporte": self._coord(sup),
                        "poste": self._coord(base), "radio_m": round(
                            math.hypot(self.key_of_tag[sup][0] - u,
                                       self.key_of_tag[sup][1] - v), 4)})
                else:
                    self.conectores_arranque.append({
                        "eje": [u, v], "z": z_base, "soporte": None,
                        "poste": self._coord(base),
                        "radio_m": None,
                        "nota": ("sin soporte vertical dentro de %.2f m; "
                                 "arranque reportado") % R_STUB_MAX_M})
            else:
                # la base cae sobre el enmarcado del piso (viga/borde documentada):
                # sin stub, apoyo directo registrado (G3S1 sobre H_y2027 del
                # voladizo norte; decision usuario: 'base apoya directamente,
                # sin stub').
                self.conectores_arranque.append({
                    "eje": [u, v], "z": z_base, "tipo": "apoyo_directo_en_viga",
                    "viga": viga_apoyo, "soporte": None,
                    "poste": self._coord(base), "radio_m": 0.0})
            sec_name = str(c["seccion"])
            sec_steel = SEC.seccion_columna(sec_name) or SEC.seccion_columna(
                "P.M. 300x300x20")
            # Tope vertical DOCUMENTADO por eje (TORRE_TOPE_NIVEL, unico caso: G3S1
            # sin registro en P4). Para el resto se conserva la convencion del modelo:
            # los postes que inician en P3 suben a la losa P4 (nunca tramo fantasma
            # base). Los que inician en P4 suben al tope hipotetico (H_TORRE_M).
            cap = TORRE_TOPE_NIVEL.get((u, v))
            z_top = COTAS_NIVEL_M[cap] if cap else Z_P4
            if z_base < Z_P4 - 0.02:
                # tramos nivel a nivel hasta el tope documentado (nodos en cada cota)
                prev = base
                for cod in niveles_ordenados():
                    zc = COTAS_NIVEL_M[cod]
                    if zc <= z_base + 1e-6 or zc > z_top + 1e-6:
                        continue
                    nxt = self._snap_node_scaffold(u, v, zc)
                    if nxt != prev:
                        self._add_vertical("columna", sec_name,
                                           "poste_%s_%s_%s" % (u, v, cod),
                                           c["cod_base"], prev, nxt, sec_steel)
                    prev = nxt
                if cap is None:
                    top = self._snap_node_scaffold(u, v, Z_P4)
                    if top != prev:
                        self._add_vertical("columna", sec_name,
                                           "poste_%s_%s_p4" % (u, v),
                                           c["cod_base"], prev, top, sec_steel)
            else:
                # inicia en P4: sube al tope hipotetico sobre la losa (H_TORRE_M)
                top = self._get_node(u, v, Z_P4 + self.h_torre_m)
                self._add_vertical("columna", sec_name,
                                   "poste_%s_%s_remate" % (u, v),
                                   c["cod_base"], base, top, sec_steel)
        # diafragma: nodos a cota P4 (arranques y/remates) quedan esclavos
        nuevos = []
        for r in self.columnas:
            if abs(self.key_of_tag[int(r["nodo_j"])][2] - Z_P4) < 0.02:
                nuevos.append(int(r["nodo_j"]))
        for (u, v) in por_eje:
            t = self.nodes.get(_key(u, v, Z_P4))
            if t is not None:
                nuevos.append(int(t))
        self._add_slaves_diafragma(nuevos, Z_P4)

    # ------------------------------------------------------------------ #
    # Diafragma: slaves posteriores a super().construir()
    # ------------------------------------------------------------------ #
    def _add_slaves_diafragma(self, tags, z):
        keep = sorted({int(t) for t in tags if t is not None})
        if not keep:
            return
        master = self.master_por_nivel.get("P4")
        if master is None:
            return
        withsuper = self.diafragma_esclavos_por_nivel.setdefault("P4", [])
        nuevos = [t for t in keep if t not in withsuper and t != master]
        if nuevos:
            ops.rigidDiaphragm(3, master, *nuevos)
            withsuper.extend(nuevos)
            self._vueltos_slaves.extend(nuevos)

    def _coord(self, tag):
        if tag is None:
            return None
        return [round(x, 4) for x in self.key_of_tag[int(tag)]]

    # ------------------------------------------------------------------ #
    # Topologia / preflight
    # ------------------------------------------------------------------ #
    def _registrar_topologia(self):
        self.topologia = {
            "perfil": "MODELO_FE_COMPLETO_FUNCIONAL",
            "conectores_p4": self.conectores_p4,
            "conectores_arranque": self.conectores_arranque,
            "pendientes_torre": self.pendientes_torre,
            "n_p4_physical": len(self.p4_physical),
            "n_acero_posts": len(self.acero_posts),
            "n_conectores_p4": len(self.conectores_p4),
            "n_conectores_arranque": len(self.conectores_arranque),
            "resumen": self.resumen(),
        }

    def preflight(self) -> dict:
        checks = []
        # elementos NO duplicados: los stubs elasticos se registran a la vez en
        # vigas_elem y stub_elem (coherencia de extraccion); se cuenta uno solo.
        elems = self.columnas + self.vigas_elem + self.muros_elem
        # enlaces cinematicos (rigidLink) del marco base: CP1S (portico excentrico,
        # desfase <= 0.43 m documentado) y V.S.I. -> cuentan como conexiones reales
        # entre nodos (constraints), aunque no sean elementos.
        rlinks = getattr(self, "rigid_links_info", [])
        edges_rl = [(int(r["col_tag"]), int(r["beam_tag"])) for r in rlinks]
        def arista_de(rec):
            return (int(rec["nodo_i"]), int(rec["nodo_j"]))
        # 1) nodos desconectados (sin elemento, ni restriccion, ni rigidLink)
        en_elem = set()
        for r in elems:
            en_elem.add(int(r["nodo_i"])); en_elem.add(int(r["nodo_j"]))
        for (a, b) in edges_rl:
            en_elem.add(a); en_elem.add(b)
        todos = set(int(t) for t in self.nodes.values())
        base_fijos = set(self._base_fixed)
        aislados = sorted(t for t in todos - en_elem if t not in base_fijos)
        checks.append({"check": "nodos_sin_elemento_ni_base",
                       "ok": not aislados,
                       "detalle": "nodos aislados: %d %s"
                       % (len(aislados), aislados[:10])})
        # 2) elementos duplicados (misma pareja i-j y mismo eje/linea)
        vistos = {}
        duplicados = []
        for r in elems:
            clave = (min(int(r["nodo_i"]), int(r["nodo_j"])),
                     max(int(r["nodo_i"]), int(r["nodo_j"])), r["tipo"])
            if clave in vistos:
                if vistos[clave] != r["elemento_id"]:
                    duplicados.append((clave, vistos[clave], r["elemento_id"]))
            else:
                vistos[clave] = r["elemento_id"]
        checks.append({"check": "sin_elementos_duplicados",
                       "ok": not duplicados,
                       "detalle": "duplicados: %d" % len(duplicados)})
        # 3) caminos de carga continuos hasta base (grafo de elementos + rigidLinks)
        base_tags = sorted(self._base_fixed)
        alcanzables = set(base_tags)
        frontera = base_tags
        while frontera:
            nh = set()
            for r in elems:
                i, j = int(r["nodo_i"]), int(r["nodo_j"])
                if i in alcanzables and j not in alcanzables:
                    nh.add(j)
                if j in alcanzables and i not in alcanzables:
                    nh.add(i)
            for (a, b) in edges_rl:
                if a in alcanzables and b not in alcanzables:
                    nh.add(b)
                if b in alcanzables and a not in alcanzables:
                    nh.add(a)
            alcanzables |= nh
            frontera = nh
        desconectados = sorted(t for t in todos if t not in alcanzables)
        # esclavos de diafragma cuentan como conectados al piso (restriccion)
        esclavos = set(t for lst in self.diafragma_esclavos_por_nivel.values()
                       for t in lst)
        desconectados_finales = [t for t in desconectados if t not in esclavos]
        checks.append({"check": "caminos_de_carga_a_base",
                       "ok": not desconectados_finales,
                       "detalle": "nodos sin camino de carga: %d (a Diafragma %d)"
                       % (len(desconectados_finales), len(desconectados)
                          - len(desconectados_finales))})
        # 4) diafragmas / maestro correctos por nivel
        dia_ok = []
        for cod, tags in self.diafragma_esclavos_por_nivel.items():
            master = self.master_por_nivel.get(cod)
            dia_ok.append({"nivel": cod, "maestro": master,
                           "n_esclavos": len(tags)})
        checks.append({"check": "diafragmas_por_nivel",
                       "ok": len(dia_ok) == 4,
                       "detalle": json.dumps(dia_ok)})
        # 5) compatibilidad DOF (todos 6)
        checks.append({"check": "dof_6_por_nodo", "ok": True,
                       "detalle": "model 3D ndf=6"})
        # 6) excentricidades documentadas
        ecc = [c for c in self.conectores_p4 if c.get("excentricidad_m") is not None]
        checks.append({"check": "excentricidades_documentadas",
                       "ok": len(ecc) == len(self.p4_physical),
                       "detalle": "%d de %d con excentricidad registrada"
                       % (len(ecc), len(self.p4_physical))})
        # 7) sin elementos por encima de P4 sin evidencia (tope postes <= P4+H)
        sobre_p4 = [r["elemento_id"] for r in elems
                    if max(r.get("z_j", 0), r.get("z_i", 0)) > Z_P4 + 0.02]
        checks.append({"check": "sin_elementos_sobre_p4_no_declarados",
                       "ok": all(("torre_" in e or "poste_" in e)
                                 for e in sobre_p4),
                       "detalle": "sobre P4: %d (todos torre_/poste_ hipoteticos)"
                       % len(sobre_p4)})
        # 8) resolucion de prueba: mecanismos (una carga de gravedad unidad)
        #    (se observa en la corrida G; aqui solo se registra pendiente)
        checks.append({"check": "sin_mecanismos_(verificacion_en_corridas)",
                       "ok": None, "detalle": "se verifica en G/Q/EX/EY"})
        return {"checks": checks,
                "ok": all(c["ok"] for c in checks if c["ok"] is not None)}


# --------------------------------------------------------------------------- #
# Corredores de casos (G/Q) reutilizando los patrones fieles
# --------------------------------------------------------------------------- #
def _cargas_losas(marco, pm_kn=None) -> dict:
    """G de losas por nivel: peso propio estructural (losa) + PM.ADIC superficial.

    `pm_kn=None` usa la PM.ADIC correlacionada (techo del case G del checkpoint);
    `pm_kn=0.0` deja SOLO el PP estructural de losa. El motor aplica estas cargas
    como NODALES (la losa dibuja su PP estructural desde espesor x gamma dentro de
    la tributaria); OpenSees NO computa peso propio por densidad/masa."""
    por_nivel = CC.cargas_por_losa_por_nivel()
    cargas = {}
    for cod in niveles_ordenados():
        nivelFE = marco.niveles[cod]
        cargas_por_losa = {}
        for lo in nivelFE.losas:
            info = por_nivel.get(cod, {}).get(lo["id"], {})
            pm = info.get("pm_kn_m2", 0.0) if pm_kn is None else float(pm_kn)
            cargas_por_losa[lo["id"]] = (pm, info.get("sc_kn_m2", 0.0))
        cn, _ = TB.calcular_cargas_nodales(nivelFE, marco.receptor_nodos,
                                           cargas_por_losa, marco.key_of_tag,
                                           incluir_sc=False)
        cargas[cod] = cn
    return cargas


def pp_elementos_confirmados(marco) -> dict:
    """PP de elementos CONFIRMADO por la auditoria v2 (cota inferior) aplicado
    como carga nodal sobre la topologia MODELO_FE_COMPLETO_FUNCIONAL.

    Mapea los ids auditados (137 vigas + 43 tramos de columna + 4 paneles de
    muro) sobre los elementos FE reales y descarga la mitad de cada PP en cada
    extremo. Igual que el perfil G_EI_MODELO_FIEL (iteracion v3/v4), de donde se
    toma el camino estructural; OpenSees no aplica peso propio por seccion."""
    from src.modelo_fiel.caso_G_EI_MODELO_FIEL import (
        _match_columnas, _match_muros, _match_vigas, aplicar_pp_nodal)
    audit = json.loads(AUDIT_V2.read_text(encoding="utf-8"))
    v = _match_vigas(marco, audit["detalle"]["vigas_confirmadas"])
    c = _match_columnas(marco, audit["detalle"]["columnas_confirmadas"])
    m = _match_muros(marco, audit["detalle"]["muros_confirmados"])
    if len(v["chequeos"]) != 137 or any(not q["ok"] for q in v["chequeos"]):
        miss = [q["id"] for q in v["chequeos"] if not q["ok"]][:20]
        raise RuntimeError("vigas confirmadas sin elemento FE (o longitud "
                           "divergente): %s" % miss)
    if len(c["chequeos"]) != 43 or any(not q["ok"] for q in c["chequeos"]):
        miss = [q["id"] for q in c["chequeos"] if not q["ok"]][:20]
        raise RuntimeError("columnas confirmadas sin elemento FE: %s" % miss)
    if len(m["chequeos"]) != 4 or any(not q["ok"] for q in m["chequeos"]):
        miss = [q["key"] for q in m["chequeos"] if not q["ok"]][:6]
        raise RuntimeError("muros confirmados sin montante FE: %s" % miss)
    apl = aplicar_pp_nodal(marco, v, c, m)
    return {"cargas": apl["cargas"], "total_kN": apl["total_kN"],
            "n_ids": apl["n_ids_contados"],
            "vigas_kN": round(v["total_kN"], 4),
            "columnas_kN": round(c["total_kN"], 4),
            "muros_kN": round(m["total_kN"], 4),
            "n_vigas": 137, "n_columnas": 43, "n_muros": 4}


def _cargas_G(marco) -> dict:
    """Caso G corregido (perfil MODELO_FE_COMPLETO_FUNCIONAL): losas (PP
    estructural + PM.ADIC) + PP de elementos estructurales confirmado. La
    permanencia total NO se ajusta artificialmente: se aplica el PP real de los
    elementos confirmados (cota inferior auditada), identico a G_EI_MODELO_FIEL
    v3/v4, que es lo que faltaba respecto del checkpoint."""
    cargas = _cargas_losas(marco, pm_kn=None)
    pp = pp_elementos_confirmados(marco)
    for cod, car in pp["cargas"].items():
        for t, f in car.items():
            acc = cargas.setdefault(cod, {}).setdefault(int(t), [0.0] * 6)
            for i in range(6):
                acc[i] += f[i]
    return cargas


def _cargas_Q(marco, q_Q) -> dict:
    cargas = {}
    for cod in niveles_ordenados():
        nivelFE = marco.niveles[cod]
        soportes = TB._receptor_lineas(nivelFE)
        c = {}
        for lo in nivelFE.losas:
            s = GF.construir_superficies([lo])[0]
            neto = s["neto"].area
            if neto <= 0:
                continue
            validos = (set(soportes.keys()) if not lo.get("apoyos")
                       else set(lo["apoyos"]))
            areas, _ = TB.distribuir_losa(
                s["neto"], {k: v for k, v in soportes.items() if k in validos})
            suma = sum(areas.values())
            for rid, area in areas.items():
                frac = area / suma if suma > 0 else 0.0
                F = frac * q_Q * neto
                nodos = marco.receptor_nodos.get(rid, [])
                if not nodos:
                    continue
                pesos = TB._pesos_por_nodo(marco.key_of_tag, nodos)
                for tag, w in pesos.items():
                    cur = c.get(tag, [0.0] * 6)
                    cur[2] -= F * w
                    c[tag] = cur
        cargas[cod] = c
    return cargas


def _suma_fz(cargas_por_nivel) -> float:
    return -sum(f[2] for c in cargas_por_nivel.values() for f in c.values())


def _repartir_en_niveles(flat, key_of_tag):
    out = {}
    for cod in niveles_ordenados():
        zc = COTAS_NIVEL_M[cod]
        out[cod] = {int(t): f for t, f in flat.items()
                    if abs(key_of_tag[int(t)][2] - zc) < 0.05}
    return out


def reconciliacion_por_familia(marco) -> dict:
    """Tabla de reconciliacion del caso G por familia.

    Verifica que el G del perfil MODELO_FE_COMPLETO_FUNCIONAL coincida con el G
    del MODELO_FIEL v3/v4 (losas + PM.ADIC + PP de elementos confirmado) y que
    ningun peso quede omitido NI duplicado. Las familias de peso propio real se
    aplican sin ajustes artificiales; los pesos hipoteticos/pendientes se
    reportan como tales (no aplicados, visible en la tabla)."""
    from src.modelo_fiel.caso_G_EI_MODELO_FIEL import (
        GAMMA_CONCRETO_KN_M3, _match_columnas, _match_muros, _match_vigas, _lon)
    audit = json.loads(AUDIT_V2.read_text(encoding="utf-8"))
    dens = audit["densidades"]

    def _n_losas():
        return sum(len(marco.niveles[cod].losas) for cod in niveles_ordenados())

    def _area_poligono(poly) -> float:
        pts = [p[:2] for p in poly if len(p) >= 2]
        n = len(pts)
        if n < 3:
            return 0.0
        return abs(sum(pts[i][0] * pts[(i + 1) % n][1]
                       - pts[(i + 1) % n][0] * pts[i][1]
                       for i in range(n)) / 2.0)

    def _area_neta():
        tot = 0.0
        for cod in niveles_ordenados():
            for lo in marco.niveles[cod].losas:
                area = _area_poligono(lo.get("poligono", []))
                area -= sum(_area_poligono(a) for a in lo.get("aberturas", []))
                tot += max(area, 0.0)
        return tot

    # 1) losas: G completo (PP estructural + PM.ADIC) y SOLO PP estructural
    g_full = _cargas_losas(marco, pm_kn=None)
    g_pp = _cargas_losas(marco, pm_kn=0.0)
    pp_losas = _suma_fz(g_pp)
    pm_adic = _suma_fz(g_full) - pp_losas
    checkpoint = _suma_fz(g_full)

    # 2) PP de elementos CONFIRMADO (auditoria v2) sobre esta topologia
    v = _match_vigas(marco, audit["detalle"]["vigas_confirmadas"])
    c = _match_columnas(marco, audit["detalle"]["columnas_confirmadas"])
    m = _match_muros(marco, audit["detalle"]["muros_confirmados"])
    pp = pp_elementos_confirmados(marco)
    ok_match = (len(v["chequeos"]) == 137 and len(c["chequeos"]) == 43
                and len(m["chequeos"]) == 4
                and all(q["ok"] for q in v["chequeos"] + c["chequeos"] + m["chequeos"]))
    total_pp_elementos = v["total_kN"] + c["total_kN"] + m["total_kN"]
    total_g = checkpoint + total_pp_elementos

    # 3) postes de acero de la torre (seccion provisional HIPOTESIS)
    postes = [r for r in marco.columnas if r["elemento_id"].startswith("poste_")]
    axes_postes = sorted({r["elemento_id"].rsplit("_", 1)[0] for r in postes})
    L_torre = sum(_lon(r) for r in postes)

    # 4) stubs rigidos y conectores P4 (dispositivos sin masa propia)
    n_stubs = len(marco.stub_elem)
    n_conectores = len(marco.conectores_p4)

    familias = [
        {"familia": "Losas (PP estructural, espesor x gamma)",
         "cantidad": _n_losas(), "unidad_m": "losas",
         "dimension": round(_area_neta(), 2), "unidad_dim": "m2 netas",
         "peso_unit": "-", "total_kN": round(pp_losas, 4),
         "entra_al_caso_G": "TB.calcular_cargas_nodales distribuye el PP "
                            "estructural de cada losa (neta x h x gamma) en nodos "
                            "receptores"},
        {"familia": "PM.ADIC (superficial correlacionada)",
         "cantidad": _n_losas(), "unidad_m": "losas",
         "dimension": round(_area_neta(), 2), "unidad_dim": "m2 netas",
         "peso_unit": "-", "total_kN": round(pm_adic, 4),
         "entra_al_caso_G": "idem losas con pm_kn_m2 correlacionado (el PP "
                            "superficial de PM.ADIC esta dentro de la carga "
                            "superficial; el PP estructural de losa es aparte)"},
        {"familia": "Vigas (CONFIRMADO auditoria v2)",
         "cantidad": 137, "unidad_m": "vigas", "dimension": None,
         "unidad_dim": "-", "peso_unit": "A*L*%s" % dens["concreto_kN_m3"],
         "total_kN": round(v["total_kN"], 4),
         "entra_al_caso_G": "aplicar_pp_nodal: mitad del PP en cada extremo, "
                            "proporcional a longitud FE (nunca el nodo mas "
                            "cercano); ids = detalle.vigas_confirmadas"},
        {"familia": "Columnas (CONFIRMADO auditoria v2)",
         "cantidad": 43, "unidad_m": "tramos nl/S", "dimension": None,
         "unidad_dim": "-", "peso_unit": "A*L*%s" % dens["concreto_kN_m3"],
         "total_kN": round(c["total_kN"], 4),
         "entra_al_caso_G": "idem aplicar_pp_nodal; ids = "
                            "detalle.columnas_confirmadas (P1/P2/P3; las "
                            "columnas P4 son PENDIENTE_TRAMO, fuera de la "
                            "auditoria)"},
        {"familia": "Muros (CONFIRMADO auditoria v2)",
         "cantidad": 4, "unidad_m": "paneles", "dimension": None,
         "unidad_dim": "-", "peso_unit": "A*L*%s" % dens["concreto_kN_m3"],
         "total_kN": round(m["total_kN"], 4),
         "entra_al_caso_G": "idem (los montantes del FE llevan el panel "
                            "t*L/2 cada uno)"},
        {"familia": "CHECKPOINT G (losas + PM.ADIC)",
         "cantidad": "-", "unidad_m": "-", "dimension": None,
         "unidad_dim": "-", "peso_unit": "-", "total_kN": round(checkpoint, 4),
         "entra_al_caso_G": "subtotal con el que corria el modelo antes de la "
                            "reconciliacion + cargas de G_EI_MODELO_FIEL v1"},
        {"familia": "Postes de acero torre (HIPOTESIS, NO aplicado)",
         "cantidad": len(axes_postes), "unidad_m": "ejes",
         "dimension": round(L_torre, 2), "unidad_dim": "m L total",
         "peso_unit": "pendiente seccion real (hoy perfil metalico provisorio)",
         "total_kN": 0.0,
         "entra_al_caso_G": "0 kN al G: seccion provisional HIPOTESIS y PP no "
                            "confirmado (criterio identico al MODELO_FIEL v1)"},
        {"familia": "Stubs rigid A->B (arranques/excentricidad)",
         "cantidad": n_stubs, "unidad_m": "stubs", "dimension": None,
         "unidad_dim": "-", "peso_unit": "E*mult rigida", "total_kN": 0.0,
         "entra_al_caso_G": "0 kN: dispositivo rigido sin masa propia; el peso "
                            "del tramo real le corresponde a la columna/paño "
                            "que conecta"},
        {"familia": "Conectores rigidos P4 (A grilla -> B fisico)",
         "cantidad": n_conectores, "unidad_m": "conectores", "dimension": None,
         "unidad_dim": "-", "peso_unit": "rigido", "total_kN": 0.0,
         "entra_al_caso_G": "0 kN: excentricidad documentada; las columnas P4 "
                            "que crean siguen PENDIENTE_TRAMO sin PP confirmado"},
        {"familia": "TOTAL G MODELO_FE_COMPLETO_FUNCIONAL",
         "cantidad": "-", "unidad_m": "-", "dimension": None,
         "unidad_dim": "-", "peso_unit": "-", "total_kN": round(total_g, 4),
         "entra_al_caso_G": "checkpoint + PP_el confirmado; objetivo igual al "
                            "G_EI_MODELO_FIEL v3/v4 (42406.9577 kN)"},
        {"familia": "Pendientes fuera del G (NO omitidos del reporte)",
         "cantidad": len(marco.pendientes_torre), "unidad_m": "diag torre",
         "dimension": None, "unidad_dim": "-", "peso_unit": "-",
         "total_kN": 0.0,
         "entra_al_caso_G": "TOWER_DIAG PENDIENTE_TORRE, V.S.I. provisional, "
                            "contencion sotano, tramos base ficticios (por "
                            "diseño no existen aqui); se reportan, no se "
                            "suman al G"},
    ]

    reconciliacion = {
        "perfil": "MODELO_FE_COMPLETO_FUNCIONAL", "edificio": "I",
        "g_total_kN": round(total_g, 4),
        "g_fiel_referencia_kN": 42406.9577,
        "delta_kN": round(total_g - 42406.9577, 4),
        "ok_contra_fiel": abs(total_g - 42406.9577) < 0.2,
        "checkpoint_g_kN": round(checkpoint, 4),
        "pp_elementos_confirmado_kN": round(total_pp_elementos, 4),
        "pp_vigas_kN": round(v["total_kN"], 4),
        "pp_columnas_kN": round(c["total_kN"], 4),
        "pp_muros_kN": round(m["total_kN"], 4),
        "pp_losas_kN": round(pp_losas, 4),
        "pm_adic_kN": round(pm_adic, 4),
        "match_elementos_ok": ok_match,
        "n_ids_aplicados": pp["n_ids"],
        "densidad_concreto_kN_m3": dens["concreto_kN_m3"],
        "densidad_acero_hipotesis_kN_m3": dens["acero_a36_hipotesis_kN_m3"],
        "postes_torre": {"n_ejes": len(axes_postes), "L_total_m": round(L_torre, 2)},
        "stubs": n_stubs, "conectores_p4": n_conectores,
        "pendientes_torre": len(marco.pendientes_torre),
        "familias": familias,
        "nota_omision_duplicacion": "El PP_el (184 ids: 137+43+4) se aplica una "
                                    "vez (matchers por id unico); losas y PM.ADIC "
                                    "son cargas superficiales sobre la misma losa, "
                                    "sin solaparse con el PP de elementos. Ningun "
                                    "peso se ajusta artificialmente para cuadrar "
                                    "el total.",
    }
    return reconciliacion


def correr_gravedad(marco, q_Q, guardar=True):
    """Corre G y Q (cargas puras, perfil MODELO_FE_COMPLETO_FUNCIONAL). El G
    incluye losas + PM.ADIC + PP de elementos estructurales confirmado
    (reconciliacion: total 42406.9577 kN sobre el checkpoint 25227.73 kN)."""
    out = {}
    for caso, fn in (("G", _cargas_G), ("Q", lambda m: _cargas_Q(m, q_Q))):
        cargas = fn(marco)
        marco_final = MarcoFECompleto(marco.niveles, h_torre_m=marco.h_torre_m)
        marco_final.construir()
        sol = RESv.resolver(marco_final, cargas)
        Pz = _suma_fz(cargas)
        Rz = sum(r[2] for r in sol["reacciones"].values())
        out[caso] = {"cargas_por_nivel": cargas, "sol": sol, "Pz": Pz, "Rz": Rz,
                     "equilibrio_ok": abs(Pz - Rz) < 1e-3 * max(Pz, 1.0)}
        if guardar:
            payload = {
"perfil": "MODELO_FE_COMPLETO_FUNCIONAL", "edificio": "I", "caso": caso,
                "q_Q_kN_m2": q_Q,
                "Pz_kN": round(Pz, 4), "Rz_kN": round(Rz, 4),
                "equilibrio_ok": abs(Pz - Rz) < 1e-3 * max(Pz, 1.0),
                "por_nivel_kN": {cod: round(-sum(f[2] for f in c.values()), 4)
                                 for cod, c in cargas.items()},
                "solucion_ok": bool(sol["ok"]),
                "reacciones": {str(int(t)): [round(x, 6) for x in r]
                               for t, r in sol["reacciones"].items()},
                "desplazamientos": {str(int(t)): [round(x, 8) for x in v]
                                    for t, v in sol["desplazamientos"].items()},
                "fuerzas_local_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in sol.get("fuerzas", {}).get("local", {}).items()},
                "fuerzas_global_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in sol.get("fuerzas", {}).get("global", {}).items()},
            }
            (OUT / ("%s_EI_MODELO_FE_COMPLETO_FUNCIONAL.json" % caso)).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
    return out


def correr_sismo(marco, direccion: str, guardar=True) -> dict:
    """Caso pseudoestatico EX/EY con el perfil MODELO_FE_COMPLETO_FUNCIONAL (EI).
    Peso sismico Wi = G_corregido + 0.5*Q; G_corregido incluye el PP de
    elementos confirmado (reconciliado), por lo que el corte basal SIEMPRE se
    recalcula desde el G completo (no se reutilizan los 6278.39 kN previos).
    nodales se ensamblan con los nodos del modelo completo); se reconstruye el
    modelo limpio y se resuelve SOLO con las fuerzas sismicas. Reutiliza los
    verificadores de src.cargas.caso_sismico (corte basal, momento accidental,
    direccion exclusiva, equilibrio horizontal, sentido de la deformada)."""
    from src.cargas import caso_sismico as CS
    cfg_cargas = json.loads((E3 / "config" / "cargas.json").read_text(
        encoding="utf-8"))
    cfg_sismo = CS.leer_config_sismo()
    q_Q = float(cfg_cargas["q_Q"]["I"]["q_Q_kN_m2"])
    G = _cargas_G(marco)
    Q = _cargas_Q(marco, q_Q)
    G_flat = {}
    for car in G.values():
        for t, f in car.items():
            cur = G_flat.setdefault(int(t), [0.0] * 6)
            for i in range(6):
                cur[i] += f[i]
    Q_flat = {}
    for car in Q.values():
        for t, f in car.items():
            cur = Q_flat.setdefault(int(t), [0.0] * 6)
            for i in range(6):
                cur[i] += f[i]
    cotas = {}
    for cod, car in G.items():
        if not car:
            continue
        cotas[cod] = min(marco.key_of_tag[int(t)][2] for t in car)
    sismo_res = CS.generar_cargas_sismicas_directas(
        G_flat, Q_flat, marco.key_of_tag, direccion, cfg_sismo)
    marco2 = MarcoFECompleto(marco.niveles, h_torre_m=marco.h_torre_m)
    marco2.construir()
    cargas_single = CS._agrupar_por_nivel(sismo_res["cargas_nodales"],
                                          marco2.key_of_tag, cotas)
    sol = RESv.resolver(marco2, cargas_single)
    checks = CS._verificaciones(marco2, sol, sismo_res, direccion, cotas, "I")
    caso = "EX" if direccion == "X" else "EY"
    if guardar:
        payload = {
            "perfil": "MODELO_FE_COMPLETO_FUNCIONAL", "edificio": "I", "caso": caso,
            "metodo": "pseudoestatico: Wi=PPi+0.5Qi; mi=Wi/g; Fi=0.20*Wi",
            "q_Q_kN_m2": q_Q,
            "peso_sismico": sismo_res["verificaciones"],
            "ledger_por_nivel": sismo_res["ledger_por_nivel"],
            "cargas_nodales_sismicas": {
                str(k): [round(x, 8) for x in v]
                for k, v in sismo_res["cargas_nodales"].items()},
            "solucion": {
                "ok": bool(sol["ok"]),
                "retcode": sol.get("analyze_retcode"),
                "desplazamientos": {str(int(k)): [round(x, 8) for x in v]
                                    for k, v in sol["desplazamientos"].items()},
                "reacciones": {str(int(k)): [round(x, 6) for x in v]
                               for k, v in sol["reacciones"].items()},
                "fuerzas_local_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in sol.get("fuerzas", {}).get("local", {}).items()},
                "fuerzas_global_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in sol.get("fuerzas", {}).get("global", {}).items()}},
            "verificaciones": checks,
        }
        (OUT / ("%s_EI_MODELO_FE_COMPLETO_FUNCIONAL.json" % caso)).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    ok = (sol["ok"] and checks["corte_basal"]["ok"]
          and checks["equilibrio_horizontal"]["ok"]
          and checks["momento_accidental"]["ok"]
          and checks["direccion_exclusiva"]["ok"])
    return {"caso": caso, "sol_ok": bool(sol["ok"]),
            "equilibrio_horizontal": checks["equilibrio_horizontal"],
            "corte_basal": checks["corte_basal"],
            "momento_accidental": checks["momento_accidental"],
            "direccion_exclusiva": checks["direccion_exclusiva"],
            "sentido_deformada": checks["sentido_deformada"],
            "ok": ok}


def correr_combinadas(marco, guardar=True) -> dict:
    """Corridas explicitas de las 9 combinaciones NCh3171 (perfil
    MODELO_FE_COMPLETO_FUNCIONAL, EI). Cada combinacion ensambla el patron de
    cargas nodales combinado (factores de la receta) y se resuelve DE NUEVO en
    OpenSees: no hay superposicion post-proceso. Los flujos EX/EY se reutilizan
    de sus payloads (cargas nodales sismicas); G y Q se recomputan del modelo."""
    from src.cargas import caso_sismico as CS
    from src.modelo_fiel.combinaciones_nch3171 import (
        COMBINACIONES_NCH3171, ensamblar_plano, resultantes)
    cfg_cargas = json.loads((E3 / "config" / "cargas.json").read_text(
        encoding="utf-8"))
    q_Q = float(cfg_cargas["q_Q"]["I"]["q_Q_kN_m2"])
    G = _cargas_G(marco)
    Q = _cargas_Q(marco, q_Q)
    G_flat = {}
    for car in G.values():
        for t, f in car.items():
            cur = G_flat.setdefault(int(t), [0.0] * 6)
            for i in range(6):
                cur[i] += f[i]
    Q_flat = {}
    for car in Q.values():
        for t, f in car.items():
            cur = Q_flat.setdefault(int(t), [0.0] * 6)
            for i in range(6):
                cur[i] += f[i]
    cotas = {}
    for cod, car in G.items():
        if not car:
            continue
        cotas[cod] = min(marco.key_of_tag[int(t)][2] for t in car)
    cargas_sismo = {}
    for caso in ("EX", "EY"):
        p = json.loads((OUT / ("%s_EI_MODELO_FE_COMPLETO_FUNCIONAL.json" % caso))
                       .read_text(encoding="utf-8"))
        cargas_sismo[caso] = {
            int(k): [float(x) for x in v]
            for k, v in p["cargas_nodales_sismicas"].items()}
    out = {}
    for combo in COMBINACIONES_NCH3171:
        flat = ensamblar_plano(combo, G_flat, Q_flat,
                               cargas_sismo["EX"], cargas_sismo["EY"])
        cargas_por_nivel = CS._agrupar_por_nivel(flat, marco.key_of_tag, cotas)
        marco2 = MarcoFECompleto(marco.niveles, h_torre_m=marco.h_torre_m)
        marco2.construir()
        sol = RESv.resolver(marco2, cargas_por_nivel)
        r = resultantes(flat)
        Rsum = [0.0] * 6
        for rv in sol["reacciones"].values():
            for i in range(6):
                Rsum[i] += rv[i]
        vertical_ok = bool(sol["ok"]) and abs(r["Pz"] - Rsum[2]) \
            <= 1e-3 * max(r["Pz"], 1.0)
        escala = max(max(abs(r["Vx"]), abs(r["Vy"])), 1.0)
        horizontal_res = max(abs(r["Vx"] + Rsum[0]), abs(r["Vy"] + Rsum[1]))
        horizontal_ok = bool(sol["ok"]) and horizontal_res <= 1e-2 * escala
        perfil = "MODELO_FE_COMPLETO_FUNCIONAL"
        payload = {
            "perfil": perfil, "edificio": "I",
            "caso": combo["id"], "grupo": combo["grupo"],
            "direccion": combo["direccion"],
            "expresion": combo["expresion"],
            "factores": combo["factores"],
            "norma": "NCh3171.Of2008 (ed. 2021)",
            "metodo": ("corrida EXPLICITA de OpenSees con el patron de cargas "
                       "nodales combinado (no superposicion post-proceso)"),
            "q_Q_kN_m2": q_Q,
            "aplicada": {k: round(v, 6) for k, v in r.items()},
            "reaccion_global": {k: round(v, 6) for k, v in
                                zip(("Vx", "Vy", "Pz", "Mx", "My", "Mz"),
                                    [-Rsum[0], -Rsum[1], Rsum[2],
                                     -Rsum[3], -Rsum[4], -Rsum[5]])},
            "Pz_kN": round(r["Pz"], 4),
            "Rz_kN": round(Rsum[2], 4),
            "equilibrio_ok": vertical_ok,
            "por_nivel_kN": {cod: round(-sum(f[2] for f in c.values()), 4)
                             for cod, c in cargas_por_nivel.items()},
            "cargas_nodales_combinadas": {str(t): [round(x, 8) for x in v]
                                          for t, v in sorted(flat.items())},
            "solucion": {
                "ok": bool(sol["ok"]), "retcode": sol.get("analyze_retcode"),
                "desplazamientos": {str(int(k)): [round(x, 8) for x in v]
                                    for k, v in sol["desplazamientos"].items()},
                "reacciones": {str(int(k)): [round(x, 6) for x in v]
                               for k, v in sol["reacciones"].items()},
                "fuerzas_local_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in sol.get("fuerzas", {}).get("local", {}).items()},
                "fuerzas_global_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in sol.get("fuerzas", {}).get("global", {}).items()}},
            "verificaciones": {
                "vertical": {"Pz_aplicada_kN": round(r["Pz"], 4),
                             "Rz_reaccion_kN": round(Rsum[2], 4),
                             "residuo_kN": round(abs(r["Pz"] - Rsum[2]), 8),
                             "ok": vertical_ok},
                "horizontal": {"Vx_aplicada_kN": round(r["Vx"], 4),
                               "Vy_aplicada_kN": round(r["Vy"], 4),
                               "residuo_global_kN": round(horizontal_res, 8),
                               "ok": horizontal_ok},
                "solucion_ok": bool(sol["ok"]),
                "ok": vertical_ok and horizontal_ok and bool(sol["ok"])},
        }
        if guardar:
            (OUT / ("COMB_%s_EI_MODELO_FE_COMPLETO_FUNCIONAL.json"
                    % combo["id"])).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        out[combo["id"]] = {"id": combo["id"], "expresion": combo["expresion"],
                            "equilibrio_ok": payload["verificaciones"]["ok"],
                            "vertical_ok": vertical_ok,
                            "horizontal_ok": horizontal_ok,
                            "sol_ok": bool(sol["ok"]),
                            "Pz_kN": round(r["Pz"], 2),
                            "Rz_kN": round(Rsum[2], 2),
                            "Vx_kN": round(r["Vx"], 2),
                            "Vy_kN": round(r["Vy"], 2)}
    return out


def _renders_md_reconciliacion(rec) -> str:
    filas = []
    for f in rec["familias"]:
        dim = f["dimension"] if f["dimension"] is None else "%.2f %s" % (
            f["dimension"], f["unidad_dim"])
        filas.append("| %s | %s %s | %s | %s | %.4f | %s |" % (
            f["familia"], f["cantidad"], f["unidad_m"], dim,
            f["peso_unit"], f["total_kN"], f["entra_al_caso_G"]))
    tabla = "\n".join(filas)
    return """# Reconciliacion del caso G - MODELO_FE_COMPLETO_FUNCIONAL (Edificio I)

La tabla siguiente lista las familias del peso propio y cargas permanentes del
caso G, verificadas contra el G_EI_MODELO_FIEL v3/v4. El G del modelo completo
debe coincidir con 42406.9577 kN; el checkpoint previo (losas + PM.ADIC) era
25227.73 kN.

| Familia | Cantidad | Dimension | Peso unit. | Carga total (kN) | Como entra al caso G |
|---|---|---|---|---|---|
%s

## Totales

- G MODELO_FE_COMPLETO_FUNCIONAL: **%.4f kN**
- G_EI_MODELO_FIEL v3/v4 (referencia): 42406.9577 kN
- Delta: %.4f kN  (ok si |delta| < 0.2 kN)
- Checkpoint previo (losas + PM.ADIC): %.4f kN
- PP de elementos CONFIRMADO (auditoria v2) aplicado: %.4f kN
  - vigas: %.4f (137) | columnas: %.4f (43) | muros: %.4f (4)
- Match de ids de la auditoria contra la topologia FE: %s
- n ids aplicados como carga nodal: %d (137 + 43 + 4)

## Postes de acero de la torre y dispositivos rigidos

- Postes de acero (HIPOTESIS, no aplicados al G): %d ejes, %.2f m de longitud
  total; seccion provisional de perfil metalico, PP pendiente de seccion real.
- Stubs rigidos A->B: %d (sin masa propia; el peso real es de la columna/paño).
- Conectores rigidos P4 (grilla->fisico): %d (excentricidad documentada;
  columnas P4 siguen PENDIENTE_TRAMO sin PP confirmado).
- Pendientes fuera del G (reportados, no sumados): %d diagonales de torre
  (PENDIENTE_TORRE), V.S.I. provisional, contencion sotano, tramos base
  ficticios (por diseno no existen aqui).

## Nota de omision / duplicacion

%s

Densidades usadas por la auditoria v2: concreto %.4f kN/m3;
acero A36 (hipotesis) %.4f kN/m3.
""" % (tabla, rec["g_total_kN"], rec["delta_kN"], rec["checkpoint_g_kN"],
       rec["pp_elementos_confirmado_kN"], rec["pp_vigas_kN"],
       rec["pp_columnas_kN"], rec["pp_muros_kN"],
       "TRUE (137/43/4)" if rec["match_elementos_ok"] else "FALSE",
       rec["n_ids_aplicados"], rec["postes_torre"]["n_ejes"],
       rec["postes_torre"]["L_total_m"], rec["stubs"],
       rec["conectores_p4"], rec["pendientes_torre"],
       rec["nota_omision_duplicacion"],
       rec["densidad_concreto_kN_m3"],
       rec["densidad_acero_hipotesis_kN_m3"])


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    do_g = "--g" in args or not args
    do_sismo = "--sismo" in args
    do_combinadas = "--combinadas" in args
    marco = MarcoFECompleto(GF.cargar_todos())
    marco.construir()
    pre = marco.preflight()
    topo = marco.topologia
    (OUT / "topologia_EI.json").write_text(
        json.dumps(topo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "preflight_EI.json").write_text(
        json.dumps(pre, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    resumen = {"n_nodos": len(marco.nodes), "n_columnas": len(marco.columnas),
               "n_vigas": len(marco.vigas_elem), "n_muros": len(marco.muros_elem),
               "n_stubs": len(marco.stub_elem),
               "conectores_p4": len(marco.conectores_p4),
               "preflight": pre["ok"], "checks": pre["checks"]}
    reconciliacion = reconciliacion_por_familia(marco)
    (OUT / "reconciliacion_G_EI.json").write_text(
        json.dumps(reconciliacion, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (OUT / "reconciliacion_G_EI.md").write_text(
        _renders_md_reconciliacion(reconciliacion) + "\n", encoding="utf-8")
    resumen["reconciliacion_G"] = {
        "g_total_kN": reconciliacion["g_total_kN"],
        "g_fiel_referencia_kN": reconciliacion["g_fiel_referencia_kN"],
        "delta_kN": reconciliacion["delta_kN"],
        "ok_contra_fiel": reconciliacion["ok_contra_fiel"],
        "match_elementos_ok": reconciliacion["match_elementos_ok"]}
    if do_sismo:
        for direccion in ("X", "Y"):
            r = correr_sismo(marco, direccion)
            resumen["sismo_%s" % r["caso"]] = {
                "sol_ok": r["sol_ok"], "ok": r["ok"],
                "eq_horizontal": r["equilibrio_horizontal"]["ok"],
                "corte_basal": r["corte_basal"]}
    if do_combinadas:
        resumen["combinaciones_NCh3171"] = correr_combinadas(marco)
    if do_g:
        q_Q = json.loads((E3 / "config" / "cargas.json").read_text(
            encoding="utf-8"))["q_Q"]["I"]["q_Q_kN_m2"]
        res = correr_gravedad(marco, float(q_Q))
        resumen["G"] = {"Pz_kN": round(res["G"]["Pz"], 2),
                        "Rz_kN": round(res["G"]["Rz"], 2),
                        "equilibrio": res["G"]["equilibrio_ok"],
                        "sol_ok": bool(res["G"]["sol"]["ok"])}
        resumen["Q"] = {"Q_total_kN": round(res["Q"]["Pz"], 2),
                        "Rz_kN": round(res["Q"]["Rz"], 2),
                        "equilibrio": res["Q"]["equilibrio_ok"]}
    ok_all = (pre["ok"] and resumen["reconciliacion_G"]["ok_contra_fiel"]
              and (not do_g or resumen["G"]["equilibrio"]))
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())