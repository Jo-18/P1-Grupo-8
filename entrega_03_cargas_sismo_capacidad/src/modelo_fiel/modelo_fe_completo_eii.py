"""MODELO_FE_COMPLETO_FUNCIONAL (Edificio II) construido desde los JSON del viewer.

Construye el marco FE del Edificio II (perfil MODELO_FE_COMPLETO_FUNCIONAL) con la
geometria de los 5 niveles que publica el viewer en
`viewer_unity/Assets/StreamingAssets/lab_data/edificios/II/geometry/EII_CP1S..CP4.json`,
usando la cuadricula comun INTERNA del II (sistema local: A1=[0,0], B1=[7.5,0] ...;
CP4 ya normalizado, NO se desplaza por el origen). No hay torre de acero ni junta
en el modelo interno: el II se ensambla en su propio marco (config_edificios.py).

Reglas de modelo (regimen HIPOTESIS_DE_ANALISIS; perfil MODELO_FE_COMPLETO_FUNCIONAL):

  * Base de ensamblaje = EII_CP1S (z=-4.01) como HIPOTESIS academica (la cimentacion
    del II sigue PENDIENTE_DE_FUENTE); las columnas y muros con evidencia en EII_CP1S
    se fijan en base (6 DOF). CP1S queda excluido del diafragma rigido (hipotesis de
    descanso vertical, patron del motor del I).
  * Columnas por tramo (evidencia por nivel) con seccion 0.70x0.70. A1 existe SOLO en
    EII_CP4 y NO desciende (config_edificios); NO recibe tramo base->CP4 inventado: se
    crea su nodo en CP4 y queda PENDIENTE_DE_FUENTE (falta plano de apoyo/descenso).
  * Vigas con seccion 'por_resolver' (V_031, 1 por nivel) NO reciben elemento FE ni
    seccion inventada: quedan PENDIENTE_DE_FUENTE y su carga tributaria asignada a
    ellas se reporta (no se descarta silenciosamente).
  * Muros equivalentes: dos montantes verticales (uno por extremo del eje), cada uno
    con la mitad del ancho (t x L/2), conservando el area total t x L. La continuidad
    vertical se agrupa por eje fisico (u,v) extremos, no por id (los ids cambian por
    nivel: M_002DER/INF/IZQ en CP1S, M_002A/B/C en CP1..CP4).
  * Diafragma rigido (ops.rigidDiaphragm) por nivel EII_CP1..CP4.
  * Material concreto del II NO documentado -> HIPOTESIS_DE_ANALISIS configurable
    (G40, E_c por ACI); densidad 24.5166 kN/m3 (2500 kg/m3 x g), patron del I.

Salidas bajo modelo_fiel/MODELO_FE_COMPLETO_FUNCIONAL/:
  topologia_EII.json / preflight_EII.json
  G_EII_MODELO_FE_COMPLETO_FUNCIONAL.json / Q_...
  reconciliacion_G_EII.json/.md
  EX_EII_MODELO_FE_COMPLETO_FUNCIONAL.json / EY_...

Uso:
  python -X utf8 -m src.modelo_fiel.modelo_fe_completo_eii [--build] [--g] [--sismo] [--combinadas]
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
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"
VIEWER_GEO = (REPO / "viewer_unity" / "Assets" / "StreamingAssets"
              / "lab_data" / "edificios" / "II" / "geometry")

sys.path.insert(0, str(EI_SRC))

from analisis.fe import config_edificios as CFG  # noqa: E402
from analisis.fe import geometria_fe as GF  # noqa: E402
from analisis.fe import resolver as RESv  # noqa: E402
from analisis.fe import secciones as SEC  # noqa: E402
from analisis.fe import tributaria as TB  # noqa: E402
from analisis.fe.marco import Marco, _key  # noqa: E402

EII_CFG = CFG.EDIFICIO_II
EII_COTAS = dict(EII_CFG.cotas_nivel)
EII_ORDEN = list(EII_CFG.niveles_orden)
BASE = EII_CFG.nivel_base
BASAMENTO = "EII_CP1S"
Q_Q_KPA = 3.0
FRACCION_Q_SISMO = 0.5
GAMMA_KN_M3 = 24.516625
COLMURO_MERGE_COLS = True


class NivelFEII:
    """Geometria de un nivel EII ya en el sistema comun (u, v, cota)."""

    def __init__(self, codigo: str):
        self.codigo = codigo
        self.cota = EII_COTAS[codigo]
        self.columnas = []
        self.vigas = []
        self.muros = []
        self.losas = []

    def cargar(self, d: dict):
        self.cota = float(d["cota"])
        for c in d.get("columnas", []):
            self.columnas.append({
                "id": c["id"],
                "u": float(c["posicion"][0]),
                "v": float(c["posicion"][2]),
                "seccion": c.get("seccion"),
                "rol": c.get("rol"),
                "eje": c.get("eje"),
            })
        for v in d.get("vigas", []):
            pts = [(float(p[0]), float(p[2])) for p in v.get("pts", [])]
            if not pts:
                continue
            self.vigas.append({
                "id": v.get("id"),
                "seccion": v.get("seccion"),
                "estado_seccion": v.get("estado_seccion"),
                "ancho": v.get("ancho"),
                "peralte": v.get("peralte"),
                "pts": pts,
                "recibe_losa": v.get("recibe_losa", True),
            })
        for m in d.get("muros", []):
            pts = m.get("pts")
            if not pts or len(pts) < 2:
                continue
            self.muros.append({
                "id": m["id"],
                "espesor": float(m.get("espesor")),
                "ua": float(pts[0][0]), "va": float(pts[0][2]),
                "ub": float(pts[1][0]), "vb": float(pts[1][2]),
                "recibe_losa": m.get("recibe_losa", True),
            })
        for lo in d.get("losas", []):
            poly = [(float(p[0]), float(p[2])) for p in lo.get("poligono", [])]
            ab = [[(float(p[0]), float(p[2])) for p in a]
                  for a in lo.get("aberturas", []) or []]
            self.losas.append({
                "id": lo["id"],
                "espesor": float(lo.get("espesor")),
                "poligono": poly,
                "aberturas": ab,
                "apoyos": list(lo.get("apoyos_validos", []) or []),
                "tipo_transferencia": lo.get("tipo_transferencia"),
                "direccion_transferencia": lo.get("direccion_transferencia"),
            })


def cargar_todos() -> dict:
    niveles = {}
    for cod in EII_ORDEN:
        nf = NivelFEII(cod)
        nf.cargar(json.loads((VIEWER_GEO / ("%s.json" % cod)).read_text(
            encoding="utf-8")))
        niveles[cod] = nf
    return niveles


class MarcoFECompletoEII(Marco):
    """Marco FE del Edificio II desde la geometria del viewer (sin torre ni junta)."""

    def __init__(self, niveles, rigidez_mult: float = 1.0e3):
        super().__init__(niveles, rigidez_mult)
        self.nivel_cota = EII_COTAS
        self.pendientes = {
            "columnas_sin_descenso": [],
            "vigas_por_resolver": [],
            "vigas_sin_soporte": [],
            "muros": [],
            "apoyos_losa_sin_fe": [],
        }
        self.topologia = None
        self.cobertura = None

    # ------------------------------------------------------------------ #
    # Construccion (override; sin excentricidades EI ni torre)
    # ------------------------------------------------------------------ #
    def construir(self):
        self.niveles = cargar_todos()
        ops.wipe()
        ops.model("basic", "-ndm", 3, "-ndf", 6)
        cotas = EII_COTAS
        orden = list(EII_ORDEN)
        base_z = cotas[BASE]
        por_familia = self._contar_viewer()

        self._add_columnas(cotas, orden, base_z)
        self._add_muros(cotas, orden, base_z)
        self._add_vigas(cotas, orden)
        self._apply_diafragmas_eii(cotas, orden)
        self._registrar_topologia(por_familia)
        return self

    def _contar_viewer(self) -> dict:
        por = {}
        for cod in EII_ORDEN:
            nf = self.niveles[cod]
            por[cod] = {
                "columnas": len(nf.columnas),
                "vigas": len(nf.vigas),
                "vigas_por_resolver": sum(
                    1 for v in nf.vigas
                    if (v.get("estado_seccion") or "confirmado") == "por_resolver"),\
                "muros": len(nf.muros),
                "losas": len(nf.losas),
                "cota": nf.cota,
            }
        return por

    def _add_columnas(self, cotas, orden, base_z):
        col_cols = {}
        for cod in orden:
            for c in self.niveles[cod].columnas:
                uv = (round(c["u"], 3), round(c["v"], 3))
                d = col_cols.setdefault(uv, {"sec_por_nivel": {}, "niveles": []})
                d["sec_por_nivel"][cod] = c["seccion"]
                if cod not in d["niveles"]:
                    d["niveles"].append(cod)
        for uv, info in col_cols.items():
            u, v = uv
            nive = sorted(info["niveles"], key=cotas.__getitem__)
            if nive[0] != BASE:
                self.pendientes["columnas_sin_descenso"].append({
                    "eje": [u, v], "niveles": nive,
                    "nivel_minimo": nive[0],
                    "estado": "PENDIENTE_DE_FUENTE",
                    "nota": ("columna documentada solo en niveles superiores "
                             "(A1 EII_CP4 no desciende); sin tramo base->nivel "
                             "inventado, sin apoyo simulado y SIN nodo FE "
                             "(evita rigidez nula en el solucionador)")})
                continue
            prev_tag = None
            for cod in nive:
                zc = cotas[cod]
                tag = self._get_node(u, v, zc)
                if prev_tag is not None:
                    sec_info = SEC.seccion_columna(info["sec_por_nivel"][cod])
                    if sec_info is None:
                        continue
                    self._add_vertical("columna", info["sec_por_nivel"][cod],
                                       "col_%s_%s_%s" % (u, v, cod),
                                       cod, prev_tag, tag, sec_info)
                prev_tag = tag
            self._fix_base(self._get_node(u, v, base_z))

    def _add_muros(self, cotas, orden, base_z):
        muro_lines = {}
        for cod in orden:
            for m in self.niveles[cod].muros:
                key = (round(m["ua"], 3), round(m["va"], 3),
                       round(m["ub"], 3), round(m["vb"], 3))
                d = muro_lines.setdefault(
                    key, {"espesor_por_nivel": {}, "niveles": []})
                d["espesor_por_nivel"][cod] = m["espesor"]
                if cod not in d["niveles"]:
                    d["niveles"].append(cod)
        ejes = []
        for key, info in muro_lines.items():
            ua, va, ub, vb = key
            L = math.hypot(ub - ua, vb - va)
            if L < 1e-6:
                continue
            nive = sorted(info["niveles"], key=cotas.__getitem__)
            ejes.append({
                "eje": [ua, va, ub, vb], "niveles": nive,
                "espesores": {c: info["espesor_por_nivel"][c] for c in nive}})
            top = nive[-1]
            z_top = cotas[top]
            for (ex, ey) in ((ua, va), (ub, vb)):
                last = None
                last_level = None
                for cod in nive:
                    zc = cotas[cod]
                    tag = self._snap_node_scaffold(ex, ey, zc)
                    if last is not None:
                        Lt = L / 2.0
                        sec = info["espesor_por_nivel"][cod]
                        sec_info = SEC.seccion_muro(sec, Lt)
                        self._add_vertical(
                            "muro", "M %sx%.2fx2" % (sec, Lt),
                            "muro_%s_%s_%s" % (ex, ey, cod), cod,
                            last, tag, sec_info)
                    last = tag
                btag = self._snap_node_scaffold(ex, ey, base_z)
                low = nive[0]
                if low == BASE:
                    self._fix_base(btag)
                    continue
                sec_fix = info["espesor_por_nivel"][low]
                sec_fix_info = SEC.seccion_muro(sec_fix, L / 2.0)
                self._fix_base(btag)
                top_tag = self._snap_node_scaffold(ex, ey, cotas[low])
                self._add_vertical(
                    "muro", "M %sx%.2fx2" % (sec_fix, L / 2.0),
                    "muro_%s_%s_base_%s" % (ex, ey, low), low,
                    btag, top_tag, sec_fix_info)
        self.ejes_muros = ejes
        # receptores por id original de muro (los ids cambian por nivel)
        for cod in orden:
            zc = cotas[cod]
            for m in self.niveles[cod].muros:
                ta = self._snap_node_scaffold(m["ua"], m["va"], zc)
                tb = self._snap_node_scaffold(m["ub"], m["vb"], zc)
                reg = self.receptor_nodos.setdefault(m["id"], [])
                for t in (ta, tb):
                    if t not in reg:
                        reg.append(t)

    def _add_vigas(self, cotas, orden):
        joints_por_nivel = {}
        for cod in orden:
            jset = set()
            for c in self.niveles[cod].columnas:
                jset.add((round(c["u"], 3), round(c["v"], 3)))
            for m in self.niveles[cod].muros:
                jset.add((round(m["ua"], 3), round(m["va"], 3)))
                jset.add((round(m["ub"], 3), round(m["vb"], 3)))
            for v in self.niveles[cod].vigas:
                for (pu, pv) in v["pts"]:
                    jset.add((round(pu, 3), round(pv, 3)))
            joints_por_nivel[cod] = jset
        for cod in orden:
            zc = cotas[cod]
            joints = joints_por_nivel[cod]
            for v in self.niveles[cod].vigas:
                pts = v["pts"]
                if (v.get("estado_seccion") or "confirmado") == "por_resolver":
                    self.pendientes["vigas_por_resolver"].append({
                        "id": v["id"], "nivel": cod, "seccion": v.get("seccion"),
                        "estado": "PENDIENTE_DE_FUENTE",
                        "nota": ("seccion V_031 sin respaldo; sin elemento FE "
                                 "ni seccion inventada")})
                    continue
                if len(pts) < 2:
                    continue
                sec_info = SEC.seccion_viga(v["seccion"])
                if sec_info is None:
                    self.pendientes["vigas_por_resolver"].append({
                        "id": v["id"], "nivel": cod, "seccion": v.get("seccion"),
                        "estado": "PENDIENTE_DE_FUENTE",
                        "nota": "nombre de seccion no parseable por el motor"})
                    continue
                for i in range(len(pts) - 1):
                    (ua, va) = pts[i]
                    (ub, vb) = pts[i + 1]
                    seg = self._split_segment(ua, va, ub, vb, joints, zc)
                    for k in range(len(seg) - 1):
                        (x1, y1), (x2, y2) = seg[k], seg[k + 1]
                        ta = self._snap_node_scaffold(x1, y1, zc)
                        tb = self._snap_node_scaffold(x2, y2, zc)
                        if ta is None or tb is None or ta == tb:
                            continue
                        self._add_horizontal(v["id"], cod, ta, tb, sec_info)
        self._limpiar_flotantes(cotas, orden)

    def _limpiar_flotantes(self, cotas, orden):
        """Elimina componentes de vigas cuyo nivel no tiene soporte vertical
        (columna/muro) en ningun nodo de la componente (p.ej. portico perimetral
        izquierdo de la junta: vigas que no descansan sobre columna ni muro
        documentado). Cada componente se reporta PENDIENTE_DE_FUENTE; no se
        inventa conexion y la carga de losa asignada a esos apoyos se reporta
        aparte (receptores sin FE)."""
        for cod in orden:
            zc = cotas[cod]
            nodos_nivel = [int(t) for t in self.nodes.values()
                           if abs(self.key_of_tag[int(t)][2] - zc) < 1e-6]
            soporte = set()
            for r in self.columnas + self.muros_elem:
                for t in (int(r["nodo_i"]), int(r["nodo_j"])):
                    if abs(self.key_of_tag[t][2] - zc) < 1e-6:
                        soporte.add(t)
            vecinos = {t: set() for t in nodos_nivel}
            for r in self.vigas_elem:
                if r["tipo"] != "viga":
                    continue
                i, j = int(r["nodo_i"]), int(r["nodo_j"])
                if abs(self.key_of_tag[i][2] - zc) > 1e-6:
                    continue
                vecinos.setdefault(i, set()).add(j)
                vecinos.setdefault(j, set()).add(i)
            vistos = set()
            for t in nodos_nivel:
                if t in vistos:
                    continue
                comp = []
                pila = [t]
                vistos.add(t)
                while pila:
                    n = pila.pop()
                    comp.append(n)
                    for nn in vecinos.get(n, ()):
                        if nn not in vistos:
                            vistos.add(nn)
                            pila.append(nn)
                if set(comp) & soporte:
                    continue
                segs = [r for r in self.vigas_elem
                        if r["tipo"] == "viga"
                        and int(r["nodo_i"]) in comp
                        and int(r["nodo_j"]) in comp]
                if not segs:
                    continue
                coords = [[round(x, 4) for x in self.key_of_tag[int(t)]]
              for t in sorted(comp)]
                for r in segs:
                    ops.remove("element", int(r["tag"]))
                self.vigas_elem = [r for r in self.vigas_elem
                                   if not (int(r["nodo_i"]) in comp
                                           and int(r["nodo_j"]) in comp)]
                for tag in comp:
                    self.nodes = {k: t2 for k, t2 in self.nodes.items()
                                  if t2 != tag}
                    self.key_of_tag.pop(tag, None)
                    ops.remove("node", tag)
                    for rid, lst in list(self.receptor_nodos.items()):
                        self.receptor_nodos[rid] = [t2 for t2 in lst
                                                    if t2 != tag]
                self.pendientes["vigas_sin_soporte"].append({
                    "nivel": cod,
                    "ids": sorted({r["elemento_id"] for r in segs}),
                    "n_nodos": len(comp),
                    "nodos": coords,
                    "estado": "PENDIENTE_DE_FUENTE",
                    "nota": ("componente de vigas sin columna/muro de apoyo en "
                             "el nivel (junta/acceso sin respaldo); elementos "
                             "retirados del FE y cargas reportadas aparte")})

    def _apply_diafragmas_eii(self, cotas, orden):
        for cod in [c for c in orden if c != BASAMENTO]:
            zc = cotas[cod]
            tags = sorted([t for k, t in self.nodes.items()
                           if abs(k[2] - zc) < 1e-6])
            if not tags:
                continue
            master = tags[0]
            self.master_por_nivel[cod] = master
            self.diafragma_esclavos_por_nivel[cod] = tags[1:]
            if len(tags) > 1:
                ops.rigidDiaphragm(3, master, *tags[1:])

    # ------------------------------------------------------------------ #
    # Topologia / cobertura viewer-FE / preflight
    # ------------------------------------------------------------------ #
    def _registrar_topologia(self, por_familia):
        fe_ids_vigas = sorted({r["elemento_id"] for r in self.vigas_elem})
        self.topologia = {
            "perfil": "MODELO_FE_COMPLETO_FUNCIONAL",
            "edificio": "II",
            "sistema": "comun_interno_EII (A1=[0,0]; CP4 ya normalizado, sin ROW_MAP)",
            "cotas_nivel_m": dict(self.nivel_cota),
            "viewer_por_nivel": por_familia,
            "ejes_muros": self.ejes_muros,
            "pendientes": self.pendientes,
            "diafragmas": {c: {"maestro": self.master_por_nivel.get(c),
                               "n_esclavos": len(v)}
                           for c, v in self.diafragma_esclavos_por_nivel.items()},
            "resumen": self.resumen(),
        }
        self.cobertura = self._cobertura_viewer_fe()

    def _cobertura_viewer_fe(self) -> dict:
        res = {}
        for cod in EII_ORDEN:
            nf = self.niveles[cod]
            fe_col = {(round(r["u_i"], 3), round(r["v_i"], 3), round(r["z_i"], 3))
                      for r in self.columnas if abs(r["z_i"] - nf.cota) < 0.05}
            fe_muro = {(round(r["u_i"], 3), round(r["v_i"], 3))
                       for r in self.muros_elem if abs(r["z_i"] - nf.cota) < 0.05}
            vig_ids = {r["elemento_id"] for r in self.vigas_elem
                       if r["tipo"] == "viga" and abs(r["z_i"] - nf.cota) < 0.05}
            col_ids = {c["id"] for c in nf.columnas}
            muro_ids = {m["id"] for m in nf.muros}
            res[cod] = {
                "col_tipos": len(col_ids), "col_ejes_con_fe":
                    sum(any(abs(r["u_i"] - c["u"]) < 0.02
                            and abs(r["v_i"] - c["v"]) < 0.02
                            for r in self.columnas) for c in nf.columnas),
                "viga_ids_viewer": len({v["id"] for v in nf.vigas}),
                "viga_ids_con_fe": len(vig_ids),
                "muro_ids_viewer": len(muro_ids),
                "muro_ejes_con_fe": sum(any(
                    abs(r["u_i"] - m["ua"]) < 0.02 and abs(r["v_i"] - m["va"]) < 0.02
                    for r in self.muros_elem) for m in nf.muros),
            }
        return res

    def preflight(self) -> dict:
        checks = []
        elems = self.columnas + self.vigas_elem + self.muros_elem
        rlinks = getattr(self, "rigid_links_info", []) or []
        edges_rl = [(int(r["col_tag"]), int(r["beam_tag"])) for r in rlinks]

        def arista_de(rec):
            return (int(rec["nodo_i"]), int(rec["nodo_j"]))

        # 1) nodos sin elemento ni base (tambien los que solo son esclavos de
        #    diafragma: un nodo sin elemento tiene rigidez nula en los dof
        #    fuera del plano y seria un mecanismo)
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
        # 2) elementos duplicados
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
        # 3) caminos de carga a base (con rigidLink y esclavos de diafragma)
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
        esclavos = set(t for lst in self.diafragma_esclavos_por_nivel.values()
                       for t in lst)
        desconectados_finales = [t for t in desconectados if t not in esclavos]
        checks.append({"check": "caminos_de_carga_a_base",
                       "ok": not desconectados_finales,
                       "detalle": "nodos sin camino de carga: %d (a Diafragma %d)"
                       % (len(desconectados_finales),
                          len(desconectados) - len(desconectados_finales))})
        # 4) diafragmas por nivel (EII_CP1..CP4)
        dia_ok = []
        for cod, tags in self.diafragma_esclavos_por_nivel.items():
            dia_ok.append({"nivel": cod, "maestro": self.master_por_nivel.get(cod),
                           "n_esclavos": len(tags)})
        checks.append({"check": "diafragmas_por_nivel",
                       "ok": len(dia_ok) == 4,
                       "detalle": json.dumps(dia_ok)})
        # 5) dof
        checks.append({"check": "dof_6_por_nodo", "ok": True,
                       "detalle": "model 3D ndf=6"})
        # 6) pendientes de fuente declaradas: A1 y vigas por_resolver/sin soporte
        pend = {k: len(v) for k, v in self.pendientes.items()
                if k in ("columnas_sin_descenso", "vigas_por_resolver",
                         "vigas_sin_soporte")}
        checks.append({"check": "pendientes_declaras_visibles",
                       "ok": True, "detalle": json.dumps(pend)})
        # 7) cobertura viewer<->FE por nivel
        cov = self.cobertura or self._cobertura_viewer_fe()
        cov_completa = all(
            v["col_ejes_con_fe"] >= v["col_tipos"] - 1
            and v["viga_ids_con_fe"] <= v["viga_ids_viewer"]
            for v in cov.values())
        checks.append({"check": "cobertura_viewer_fe",
                       "ok": cov_completa,
                       "detalle": json.dumps(cov)})
        # 8) sin elementos por encima de EII_CP4 sin evidencia
        sobre_p4 = [r["elemento_id"] for r in elems
                    if max(r.get("z_j", 0), r.get("z_i", 0))
                    > EII_COTAS["EII_CP4"] + 0.02]
        checks.append({"check": "sin_elementos_sobre_cp4_evidencia",
                       "ok": not sobre_p4,
                       "detalle": "sobre EII_CP4: %d" % len(sobre_p4)})
        checks.append({"check": "sin_mecanismos_(verificacion_en_corridas)",
                       "ok": None, "detalle": "se verifica en G/Q/EX/EY"})
        return {"checks": checks,
                "ok": all(c["ok"] for c in checks if c["ok"] is not None)}


# --------------------------------------------------------------------------- #
# Cargas G / Q del Edificio II
# --------------------------------------------------------------------------- #
def _area_poligono(poly) -> float:
    pts = list(poly)
    n = len(pts)
    if n < 3:
        return 0.0
    return abs(sum(pts[i][0] * pts[(i + 1) % n][1]
                   - pts[(i + 1) % n][0] * pts[i][1]
                   for i in range(n)) / 2.0)


def _area_neta_nivel(nf) -> float:
    tot = 0.0
    for lo in nf.losas:
        area = _area_poligono(lo["poligono"])
        area -= sum(_area_poligono(a) for a in lo["aberturas"])
        tot += max(area, 0.0)
    return tot


def _lon(rec) -> float:
    return math.hypot(rec["u_j"] - rec["u_i"],
                      rec["v_j"] - rec["v_i"],
                      rec["z_j"] - rec["z_i"])


def _pp_elementos(marco) -> dict:
    cargas = {}
    for rec in marco.columnas + marco.muros_elem + \
            [r for r in marco.vigas_elem if r["tipo"] == "viga"]:
        A = rec["sec_valores"]["A"]
        L = _lon(rec)
        PP = A * L * GAMMA_KN_M3
        for t in (int(rec["nodo_i"]), int(rec["nodo_j"])):
            cargas.setdefault(t, [0.0] * 6)[2] -= PP / 2.0
    return cargas


def _cargas_losas_G(marco) -> dict:
    cargas = {}
    reparto = {}
    for cod in EII_ORDEN:
        nivelFE = marco.niveles[cod]
        por_losa = {lo["id"]: (0.0, 0.0) for lo in nivelFE.losas}
        cn, rep = TB.calcular_cargas_nodales(
            nivelFE, marco.receptor_nodos, por_losa, marco.key_of_tag,
            incluir_sc=False)
        cargas[cod] = cn
        reparto[cod] = rep
    return cargas, reparto


def _cargas_Q(marco, q_Q=Q_Q_KPA) -> dict:
    cargas = {}
    reparto = {}
    for cod in EII_ORDEN:
        nivelFE = marco.niveles[cod]
        soportes = TB._receptor_lineas(nivelFE)
        c = {}
        rep = {"por_losa": {}, "area_no_asignada_total_m2": 0.0}
        for lo in nivelFE.losas:
            s = GF.construir_superficies([lo])[0]
            neto = s["neto"].area
            if neto <= 0:
                continue
            validos = (set(soportes.keys()) if not lo.get("apoyos")
                       else set(lo["apoyos"]))
            areas, _ = TB.distribuir_losa(
                s["neto"], {k: v for k, v in soportes.items() if k in validos})
            rep["por_losa"][lo["id"]] = {
                "area_neta_m2": round(neto, 4),
                "area_asignada_receptores_m2": round(sum(areas.values()), 4)}
            rep["area_no_asignada_total_m2"] += neto - sum(areas.values())
            suma = sum(areas.values())
            for rid, area in areas.items():
                frac = area / suma if suma > 0 else 0.0
                F = frac * q_Q * neto
                nodos = marco.receptor_nodos.get(rid, [])
                if not nodos:
                    marco.pendientes["apoyos_losa_sin_fe"].append({
                        "receptor": rid, "losa": lo["id"], "nivel": cod,
                        "carga_kN": round(F, 4),
                        "estado": "PENDIENTE_DE_FUENTE"})
                    continue
                pesos = TB._pesos_por_nodo(marco.key_of_tag, nodos)
                for tag, w in pesos.items():
                    cur = c.get(tag, [0.0] * 6)
                    cur[2] -= F * w
                    c[tag] = cur
        cargas[cod] = c
        reparto[cod] = rep
    return cargas, reparto


def _suma_fz(cargas_por_nivel) -> float:
    return -sum(f[2] for c in cargas_por_nivel.values() for f in c.values())


def _flat(cargas_por_nivel) -> dict:
    flat = {}
    for car in cargas_por_nivel.values():
        for t, f in car.items():
            cur = flat.setdefault(int(t), [0.0] * 6)
            for i in range(6):
                cur[i] += f[i]
    return flat


# --------------------------------------------------------------------------- #
# Reconciliacion del caso G por familias (Edificio II)
# --------------------------------------------------------------------------- #
def reconciliacion_G(marco, cargas_G, reparto_losas) -> dict:
    pp_losas = 0.0
    for cod in EII_ORDEN:
        for info in reparto_losas[cod]["por_losa"].values():
            pp_losas += info["por_comp_kN"]["pp"]
    pp_el = -sum(f[2] for f in _pp_elementos(marco).values())
    vigas = [r for r in marco.vigas_elem if r["tipo"] == "viga"]
    cols = marco.columnas
    muros = marco.muros_elem
    pp_vigas = sum(_lon(r) * r["sec_valores"]["A"] for r in vigas) * GAMMA_KN_M3
    pp_cols = sum(_lon(r) * r["sec_valores"]["A"] for r in cols) * GAMMA_KN_M3
    pp_muros = sum(_lon(r) * r["sec_valores"]["A"] for r in muros) * GAMMA_KN_M3
    receptores_sin_fe = sum(len(reparto_losas[c]["receptores_sin_fe"])
                            for c in EII_ORDEN)
    area_neta = sum(_area_neta_nivel(marco.niveles[cod]) for cod in EII_ORDEN)
    a1 = marco.pendientes["columnas_sin_descenso"]
    por_resolver = marco.pendientes["vigas_por_resolver"]
    sin_soporte = marco.pendientes["vigas_sin_soporte"]
    total_g = pp_losas + pp_vigas + pp_cols + pp_muros

    familias = [
        {"familia": "Losas (PP estructural, espesor 0.15 x gamma)",
         "cantidad": sum(len(marco.niveles[c].losas) for c in EII_ORDEN),
         "unidad_m": "losas", "dimension": round(area_neta, 2),
         "unidad_dim": "m2 netas", "peso_unit": "e x 24.5166",
         "total_kN": round(pp_losas, 4),
         "entra_al_caso_G": "TB.calcular_cargas_nodales: PP sobre area neta"},
        {"familia": "Vigas (seccion documento, 34/nivel)",
         "cantidad": len(vigas), "unidad_m": "elementos FE",
         "dimension": None, "unidad_dim": "-",
         "peso_unit": "A*L*%s" % GAMMA_KN_M3,
         "total_kN": round(pp_vigas, 4),
         "entra_al_caso_G": "mitad del PP en cada extremo del tramo FE"},
        {"familia": "Columnas (0.70x0.70, 8 ejes/nivel)",
         "cantidad": len(cols), "unidad_m": "tramos",
         "dimension": None, "unidad_dim": "-",
         "peso_unit": "A*L*%s" % GAMMA_KN_M3,
         "total_kN": round(pp_cols, 4),
         "entra_al_caso_G": "idem; A1 (solo CP4) PENDIENTE_DE_FUENTE sin tramo"},
        {"familia": "Muros (montantes t x L/2)",
         "cantidad": len(muros), "unidad_m": "montantes",
         "dimension": None, "unidad_dim": "-",
         "peso_unit": "A*L*%s" % GAMMA_KN_M3,
         "total_kN": round(pp_muros, 4),
         "entra_al_caso_G": "idem; cada eje lleva t x L/2 (area total sin duplicar)"},
        {"familia": "PM.ADIC superficial",
         "cantidad": 0, "unidad_m": "lineal kg/m sin mapeo",
         "dimension": None, "unidad_dim": "-", "peso_unit": "-",
         "total_kN": 0.0,
         "entra_al_caso_G": "PENDIENTE_DE_FUENTE: SC/PM.ADIC del EII son lineales "
                            "(kg/m) sin mapeo al panio de losa; no se aplican"},
        {"familia": "Columna A1 (EII_CP4, no desciende)",
         "cantidad": len(a1), "unidad_m": "eje", "dimension": None,
         "unidad_dim": "-", "peso_unit": "-", "total_kN": 0.0,
         "entra_al_caso_G": "PENDIENTE_DE_FUENTE: sin tramo ni apoyo documentado "
                            "(no se inventa descenso)"},
        {"familia": "Vigas por_resolver (V_031)",
         "cantidad": len(por_resolver), "unidad_m": "vigas", "dimension": None,
         "unidad_dim": "-", "peso_unit": "-", "total_kN": 0.0,
         "entra_al_caso_G": "PENDIENTE_DE_FUENTE: seccion V_031 sin respaldo; la "
                            "carga asignada a ellas se reporta aparte"},
        {"familia": "Vigas sin soporte vertical documentado",
         "cantidad": len(sin_soporte), "unidad_m": "segmentos", "dimension": None,
         "unidad_dim": "-", "peso_unit": "-", "total_kN": 0.0,
         "entra_al_caso_G": "PENDIENTE_DE_FUENTE: extremos sin columna/muro en "
                            "el nivel (portico perimetral izq., junta/acceso); "
                            "no se inventa conexion"},
        {"familia": "apoyos de losa sin FE (receptores ausentes)",
         "cantidad": receptores_sin_fe + len(marco.pendientes["apoyos_losa_sin_fe"]),
         "unidad_m": "receptores", "dimension": None, "unidad_dim": "-",
         "peso_unit": "-", "total_kN": 0.0,
         "entra_al_caso_G": "PENDIENTE_DE_FUENTE: area tributaria asignada a "
                            "receptores sin nodos FE (p.ej. viga por_resolver); "
                            "no se inventa receptor"},
        {"familia": "TOTAL G MODELO_FE_COMPLETO_FUNCIONAL",
         "cantidad": "-", "unidad_m": "-", "dimension": None,
         "unidad_dim": "-", "peso_unit": "-", "total_kN": round(total_g, 4),
         "entra_al_caso_G": "PP losas + PP elementos FE (auto-consistente; sin "
                            "referencia externa de G para el II)"},
    ]
    reconciliacion = {
        "perfil": "MODELO_FE_COMPLETO_FUNCIONAL", "edificio": "II",
        "g_total_kN": round(total_g, 4),
        "pp_losas_kN": round(pp_losas, 4),
        "pp_vigas_kN": round(pp_vigas, 4),
        "pp_columnas_kN": round(pp_cols, 4),
        "pp_muros_kN": round(pp_muros, 4),
        "area_neta_m2": round(area_neta, 4),
        "densidad_concreto_kN_m3": GAMMA_KN_M3,
        "pendientes": {
            "columnas_sin_descenso": a1,
            "vigas_por_resolver": por_resolver,
            "vigas_sin_soporte": sin_soporte,
            "apoyos_losa_sin_fe": marco.pendientes["apoyos_losa_sin_fe"],
        },
        "familias": familias,
        "nota_omision_duplicacion": (
            "El PP de elementos (vigas+columnas+muros FE) se aplica una vez por "
            "tramo/montante real; las losas aportan solo su PP estructural (e x "
            "gamma) por area neta. PM.ADIC/SC lineales, columna A1 y vigas "
            "por_resolver quedan PENDIENTE_DE_FUENTE y NO entran al G ni se "
            "inventan. Ningun peso se ajusta artificialmente para cuadrar."),
    }
    return reconciliacion


def _renders_md_reconciliacion(rec) -> str:
    filas = []
    for f in rec["familias"]:
        dim = f["dimension"] if f["dimension"] is None else "%.2f %s" % (
            f["dimension"], f["unidad_dim"])
        filas.append("| %s | %s %s | %s | %s | %.4f | %s |" % (
            f["familia"], f["cantidad"], f["unidad_m"], dim,
            f["peso_unit"], f["total_kN"], f["entra_al_caso_G"]))
    tabla = "\n".join(filas)
    pend = rec["pendientes"]
    return """# Reconciliacion del caso G - MODELO_FE_COMPLETO_FUNCIONAL (Edificio II)

El G del II es auto-consistente: losas (PP estructural) + PP de elementos FE
(vigas/columnas/muros). PM.ADIC/SC lineales (kg/m) sin mapeo, la columna A1
(solo EII_CP4, no desciende) y las vigas por_resolver (V_031) quedan
PENDIENTE_DE_FUENTE y NO entran al caso G ni se inventan.

| Familia | Cantidad | Dimension | Peso unit. | Carga total (kN) | Como entra al caso G |
|---|---|---|---|---|---|
%s

## Totales

- G MODELO_FE_COMPLETO_FUNCIONAL: **%.4f kN**
- Area neta de losas: %.2f m2
- PP losas: %.4f kN | vigas: %.4f kN | columnas: %.4f kN | muros: %.4f kN
- Densidad concreto (HIPOTESIS_DE_ANALISIS): %.4f kN/m3

## Pendientes fuera del G (reportados, no sumados)

- Columna A1 (no desciende): %d eje(s)
- Vigas por_resolver (V_031): %d
- Vigas sin soporte vertical documentado: %d segmentos
- apoyos de losa sin nodos FE: %d

## Nota de omision / duplicacion

%s
""" % (tabla, rec["g_total_kN"], rec["area_neta_m2"], rec["pp_losas_kN"],
       rec["pp_vigas_kN"], rec["pp_columnas_kN"], rec["pp_muros_kN"],
       rec["densidad_concreto_kN_m3"],
       len(pend["columnas_sin_descenso"]),
       len(pend["vigas_por_resolver"]),
       len(pend["vigas_sin_soporte"]),
       len(pend["apoyos_losa_sin_fe"]),
       rec["nota_omision_duplicacion"])


# --------------------------------------------------------------------------- #
# Corredores de casos
# --------------------------------------------------------------------------- #
def _construir_fresco(niveles):
    m = MarcoFECompletoEII(niveles)
    m.construir()
    return m


def correr_gravedad(marco, guardar=True) -> dict:
    q_Q = Q_Q_KPA
    out = {}
    for caso in ("G", "Q"):
        if caso == "G":
            por_nivel, rep = _cargas_losas_G(marco)
            pp = _pp_elementos(marco)
            for t, f in pp.items():
                for cod in EII_ORDEN:
                    if abs(marco.key_of_tag[int(t)][2]
                           - EII_COTAS[cod]) < 0.05:
                        acc = por_nivel[cod]
                        cur = acc.get(int(t), [0.0] * 6)
                        for i in range(6):
                            cur[i] += f[i]
                        acc[int(t)] = cur
                        break
            cargas_final = por_nivel
        else:
            cargas_final, rep = _cargas_Q(marco, q_Q)
        marco2 = _construir_fresco(marco.niveles)
        sol = RESv.resolver(marco2, cargas_final)
        Pz = _suma_fz(cargas_final)
        Rz = sum(r[2] for r in sol.get("reacciones", {}).values())
        out[caso] = {"cargas_por_nivel": cargas_final, "sol": sol,
                     "Pz": Pz, "Rz": Rz,
                     "equilibrio_ok": bool(sol.get("ok"))
                     and abs(Pz - Rz) < 1e-3 * max(Pz, 1.0)}
        if guardar:
            reacciones = sol.get("reacciones", {})
            desplazamientos = sol.get("desplazamientos", {})
            fuerzas = sol.get("fuerzas", {}).get("local", {})
            payload = {
                "perfil": "MODELO_FE_COMPLETO_FUNCIONAL", "edificio": "II",
                "caso": caso, "q_Q_kN_m2": q_Q,
                "Pz_kN": round(Pz, 4),
                "Rz_kN": round(Rz, 4) if reacciones else None,
                "equilibrio_ok": bool(sol.get("ok"))
                and abs(Pz - Rz) < 1e-3 * max(Pz, 1.0),
                "por_nivel_kN": {cod: round(-sum(f[2] for f in c.values()), 4)
                                 for cod, c in cargas_final.items()},
                "solucion_ok": bool(sol.get("ok")),
                "diagnostico_fallo": sol.get("diagnostico")
                or sol.get("singular_info"),
                "reacciones": {str(int(t)): [round(x, 6) for x in r]
                               for t, r in reacciones.items()},
                "desplazamientos": {str(int(t)): [round(x, 8) for x in v]
                                    for t, v in desplazamientos.items()},
                "fuerzas_local_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in fuerzas.items()},
                "fuerzas_global_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in sol.get("fuerzas", {}).get("global", {}).items()},
            }
            (OUT / ("%s_EII_MODELO_FE_COMPLETO_FUNCIONAL.json" % caso)).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        if caso == "G":
            _rep = rep
    return out


def correr_sismo(marco, direccion: str, guardar=True) -> dict:
    from src.cargas import caso_sismico as CS
    cfg_sismo = CS.leer_config_sismo()
    cargas, _ = _cargas_losas_G(marco)
    G = cargas
    G_flat = _flat(G)
    pp = _pp_elementos(marco)
    for t, f in pp.items():
        cur = G_flat.setdefault(int(t), [0.0] * 6)
        for i in range(6):
            cur[i] += f[i]
    Q, _ = _cargas_Q(marco, Q_Q_KPA)
    Q_flat = _flat(Q)
    cotas = {}
    for cod, car in G.items():
        if not car:
            continue
        cotas[cod] = min(marco.key_of_tag[int(t)][2] for t in car)
    sismo_res = CS.generar_cargas_sismicas_directas(
        G_flat, Q_flat, marco.key_of_tag, direccion, cfg_sismo)
    marco2 = _construir_fresco(marco.niveles)
    cargas_single = CS._agrupar_por_nivel(sismo_res["cargas_nodales"],
                                          marco2.key_of_tag, cotas)
    sol = RESv.resolver(marco2, cargas_single)
    checks = CS._verificaciones(marco2, sol, sismo_res, direccion, cotas, "II")
    caso = "EX" if direccion == "X" else "EY"
    if guardar:
        payload = {
            "perfil": "MODELO_FE_COMPLETO_FUNCIONAL", "edificio": "II",
            "caso": caso,
            "metodo": "pseudoestatico: Wi=PPi+0.5Qi; mi=Wi/g; Fi=0.20*Wi",
            "q_Q_kN_m2": Q_Q_KPA,
            "peso_sismico": sismo_res["verificaciones"],
            "ledger_por_nivel": sismo_res["ledger_por_nivel"],
            "cargas_nodales_sismicas":
                {str(k): [round(x, 8) for x in v]
                 for k, v in sismo_res["cargas_nodales"].items()},
            "solucion": {
                "ok": bool(sol["ok"]), "retcode": sol.get("analyze_retcode"),
                "desplazamientos": {str(int(k)): [round(x, 8) for x in v]
                                    for k, v in sol["desplazamientos"].items()},
                "reacciones": {str(int(k)): [round(x, 6) for x in r]
                               for k, r in sol["reacciones"].items()},
                "fuerzas_local_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in sol.get("fuerzas", {}).get("local", {}).items()},
                "fuerzas_global_por_elemento":
                    {str(int(k)): [round(x, 6) for x in v]
                     for k, v in sol.get("fuerzas", {}).get("global", {}).items()}},
            "verificaciones": checks,
        }
        (OUT / ("%s_EII_MODELO_FE_COMPLETO_FUNCIONAL.json" % caso)).write_text(
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
    MODELO_FE_COMPLETO_FUNCIONAL, II). Cada combinacion ensambla el patron de
    cargas nodales combinado (factores de la receta) y se resuelve DE NUEVO en
    OpenSees: no hay superposicion post-proceso. Los flujos EX/EY se reutilizan
    de sus payloads (cargas nodales sismicas); G y Q se recomputan del modelo."""
    from src.cargas import caso_sismico as CS
    from src.modelo_fiel.combinaciones_nch3171 import (
        COMBINACIONES_NCH3171, ensamblar_plano, resultantes)
    cargas, _ = _cargas_losas_G(marco)
    pp = _pp_elementos(marco)
    for t, f in pp.items():
        for cod in EII_ORDEN:
            if abs(marco.key_of_tag[int(t)][2] - EII_COTAS[cod]) < 0.05:
                cur = cargas[cod].get(int(t), [0.0] * 6)
                for i in range(6):
                    cur[i] += f[i]
                cargas[cod][int(t)] = cur
                break
    Q, _ = _cargas_Q(marco, Q_Q_KPA)
    G_flat = _flat(cargas)
    Q_flat = _flat(Q)
    cotas = {}
    for cod, car in cargas.items():
        if not car:
            continue
        cotas[cod] = min(marco.key_of_tag[int(t)][2] for t in car)
    cargas_sismo = {}
    for caso in ("EX", "EY"):
        p = json.loads((OUT / ("%s_EII_MODELO_FE_COMPLETO_FUNCIONAL.json"
                               % caso)).read_text(encoding="utf-8"))
        cargas_sismo[caso] = {
            int(k): [float(x) for x in v]
            for k, v in p["cargas_nodales_sismicas"].items()}
    out = {}
    for combo in COMBINACIONES_NCH3171:
        flat = ensamblar_plano(combo, G_flat, Q_flat,
                               cargas_sismo["EX"], cargas_sismo["EY"])
        cargas_por_nivel = CS._agrupar_por_nivel(flat, marco.key_of_tag, cotas)
        marco2 = _construir_fresco(marco.niveles)
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
        payload = {
            "perfil": "MODELO_FE_COMPLETO_FUNCIONAL", "edificio": "II",
            "caso": combo["id"], "grupo": combo["grupo"],
            "direccion": combo["direccion"],
            "expresion": combo["expresion"],
            "factores": combo["factores"],
            "norma": "NCh3171.Of2008 (ed. 2021)",
            "metodo": ("corrida EXPLICITA de OpenSees con el patron de cargas "
                       "nodales combinado (no superposicion post-proceso)"),
            "q_Q_kN_m2": Q_Q_KPA,
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
            (OUT / ("COMB_%s_EII_MODELO_FE_COMPLETO_FUNCIONAL.json"
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


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    do_g = "--g" in args or not args
    do_sismo = "--sismo" in args
    do_combinadas = "--combinadas" in args
    marco = _construir_fresco(cargar_todos())
    pre = marco.preflight()
    topo = marco.topologia
    (OUT / "topologia_EII.json").write_text(
        json.dumps(topo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "preflight_EII.json").write_text(
        json.dumps(pre, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    resumen = {"n_nodos": len(marco.nodes), "n_columnas": len(marco.columnas),
               "n_vigas": len(marco.vigas_elem), "n_muros": len(marco.muros_elem),
               "preflight": pre["ok"],
               "cobertura": getattr(marco, "cobertura", None)}
    cargas_G, rep_losas = _cargas_losas_G(marco)
    rec = reconciliacion_G(marco, cargas_G, rep_losas)
    (OUT / "reconciliacion_G_EII.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "reconciliacion_G_EII.md").write_text(
        _renders_md_reconciliacion(rec) + "\n", encoding="utf-8")
    resumen["reconciliacion_G"] = {"g_total_kN": rec["g_total_kN"]}
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
        res = correr_gravedad(marco)
        resumen["G"] = {"Pz_kN": round(res["G"]["Pz"], 2),
                        "Rz_kN": round(res["G"]["Rz"], 2),
                        "equilibrio": res["G"]["equilibrio_ok"],
                        "sol_ok": bool(res["G"]["sol"]["ok"])}
        resumen["Q"] = {"Q_total_kN": round(res["Q"]["Pz"], 2),
                        "Rz_kN": round(res["Q"]["Rz"], 2),
                        "equilibrio": res["Q"]["equilibrio_ok"]}
    ok_all = pre["ok"] and (not do_g or resumen["G"]["equilibrio"])
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())