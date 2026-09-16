"""Ensamblaje y solucion del marco 3D del Edificio I con OpenSeesPy.

Modelo de laboratorio (no utilizable para diseno):
  - 6 DOF por nodo; elementos elasticBeamColumn (axial, flexion, torsion).
  -     Diafragma rigido por nivel (P1..P4) via ops.rigidDiaphragm (relacion de cuerpo
    rigido en el plano, con rotacion y distancia al maestro); el desplazamiento
    vertical (w) y los giros fuera de plano quedan libres. CP1S queda excluido.
  - Muros equivalentes: dos montantes verticales, uno por extremo del eje, cada uno
    con la mitad del ancho (t x L/2), conservando el area total t x L (sin duplicar).
  - Columnas por tramo (evidencia por nivel): se modelan solo los segmentos entre
    niveles consecutivos con columna documentada; NO se prolongan a los 5 niveles.
    La llegada a cimentacion en z=-4.01 es HIPOTESIS senalada.
  - Sotano: el cielo del subterraneo (CP1S) recibe solo restriccion vertical (w)
    como hipotesis de descanso sobre la cimentacion; no se fijan traslaciones
    horizontales ni rotaciones.
  - Apoyo de base (HIPOTESIS): base fija completa de columnas/muros en z=-4.01.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import openseespy.opensees as ops

from .hipotesis import COTAS_NIVEL_M, niveles_ordenados
from . import config_edificios as CFG
from . import secciones as SEC

TOL = 1e-4
# Tolerancia de fusion de nodos por misma posicion fisica (documentada como limpieza
# de incoherencias numericas del JSON/DXF, p.ej. 16.501 vs 16.5). 1-2 cm: NO cubre
# diferencias de 5 cm; los casos entre MERGE_TOL y NEAR_TOL se registran y quedan sin
# fusionar para identificacion especifica. Los desfases de 0.2 m (excentricidad real)
# NO se fusionan (se tratan por enlace rigido en el caso P1 documentado).
MERGE_TOL = 0.015
NEAR_TOL = 0.15


def _key(u, v, z):
    return (round(u, 3), round(v, 3), round(z, 3))


class Marco:
    def __init__(self, niveles: Dict[str, object], rigidez_mult: float = 1.0e3):
        # rigidez_mult: multiplicador de E y G del conector corto que modela la union
        # rigida excentrica P1. Es una IDEALIZACION ELASTICA DE RIGIDEZ ELEVADA (no un
        # vinculo rigido exacto). Se parametriza para estudiar sensibilidad.
        self.rigidez_mult = float(rigidez_mult)
        # subdivision_vigas: subdivide cada viga en ese numero de sub-elementos entre
        # sus nodos de tramo (default 1 = comportamiento actual). Se usa para
        # DEMOSTRAR convergencia en el modelo real (refinamiento de malla de vigas)
        # manteniendo la descarga nodal consistente via _pesos_por_nodo.
        self.subdivision_vigas = 1
        self.niveles = niveles          # codigo -> NivelFE (geometria comun)
        self.nodes = {}                 # key -> tag
        self.key_of_tag = {}
        self.columnas = []              # {id, nivel, key_i, key_j, sec, u,v}
        self.vigas_elem = []            # {id, nivel, key_i, key_j, sec}
        self.muros_elem = []            # {id, nivel, key_i, key_j, sec}
        self.ejes_muros = []            # ejes fisicos (familia) para diagnostico
        self.pendientes = {"muros": [], "columnas": [], "vigas": []}
        self.master_por_nivel = {}      # nivel -> tag maestro
        self.diafragma_esclavos_por_nivel = {}  # nivel -> [tags esclavos del diafragma]
        self.diafragma_excluidos_rigidlink = {} # nivel -> [tags excluidos por rigidLink]
        self.receptor_nodos = {}        # receptor_id -> [tag_i, tag_j]
        self.nivel_cota = COTAS_NIVEL_M
        self._next = 1
        self._base_fixed = set()
        self._apoyos_losa_fixed = set()
        self.merges = []                 # registro fusiones por misma posicion fisica
        self.casi_encuentros = []        # casi-encuentros (no fusionados) para revisar
        self._componentes_excluidos_apoyo = []  # cuerdas excluidas sin apoyo fisico
        self.p1_eccentric_links = []     # enlaces rigidos de la viga excentrica P1
        self.rigid_links_info = []       # pares (col_tag, beam_tag) de enlaces rigidos
        self.stub_elem = []              # conectores cortos rigidos (reemplazan rigidLink)
        self.cp1s_eccentric_links = []   # enlaces rigidos del portico del cielo del subterraneo
        self.p4_grillaje_links = []      # grillaje torre P4 -> montantes reales (conector corto)
        self._p4_links_seen = []         # pares ya enlazados del grillaje (evita duplicados)
        self.enlaces_rigidos_reales = [] # pares rigidLink (col,extremo) registrados (constraints)
        self.defer_anclar_apoyos = False # subclases con geometria posterior (torre) difieren
                                         # _anclar_apoyos_losa hasta completar el ensamble

    # ---------------- nodos ----------------
    def _get_node(self, u, v, z):
        k = _key(u, v, z)
        if k in self.nodes:
            return self.nodes[k]
        tag = self._next; self._next += 1
        self.nodes[k] = tag
        self.key_of_tag[tag] = k
        ops.node(tag, u, v, z)
        return tag

    def _node_pos(self, tag):
        return [ops.nodeCoord(tag, i) for i in (1, 2, 3)]

    # ---------------- construccion ----------------
    def construir(self):
        ops.wipe()
        ops.model('basic', '-ndm', 3, '-ndf', 6)

        cotas = COTAS_NIVEL_M
        cfg = CFG.activa()
        base_z = cotas[cfg.nivel_base]
        orden = niveles_ordenados()

        self._registrar_hipotesis_muros_contencion()

        # 1) columnas por tramo (evidencia por nivel): posicion (u,v) -> niveles donde
        #    existe columna documentada. Se crean nodos SOLO en los niveles con evidencia
        #    y se conectan niveles consecutivos presentes. NO se prolonga a los 5 niveles.
        col_cols = {}   # (u,v) -> {"seccion_por_nivel": {cod: seccion}, "niveles":[cod...]}
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
            # nodos en los niveles con evidencia + elemento entre consecutivos
            prev_tag = None
            for cod in nive:
                zc = cotas[cod]
                tag = self._get_node(u, v, zc)
                if prev_tag is not None:
                    sec_info = SEC.seccion_columna(info["sec_por_nivel"][cod])
                    if sec_info is None:
                        continue
                    self._add_vertical("columna", info["sec_por_nivel"][cod],
                                       f"col_{u}_{v}_{cod}", cod, prev_tag, tag, sec_info)
                prev_tag = tag
            # HIPOTESIS (senalada): la columna llega a la cimentacion en z=base.
            # Si el nivel mas bajo documentado es CP1S, coincide con base (fijo).
            # Si arranca en un nivel superior (p.ej. P1), se anade un tramo hipotetico
            # base -> nivel mas bajo para llevar la carga a cimentacion.
            btag = self._get_node(u, v, base_z)
            if nive and nive[0] == cfg.nivel_base:
                # la base coincide con el nodo CP1S ya creado; solo fijarla una vez
                self._fix_base(self._get_node(u, v, base_z))
            else:
                # tramo hipotetico base -> nivel mas bajo con evidencia
                sec_info = SEC.seccion_columna(info["sec_por_nivel"][nive[0]])
                self._fix_base(btag)
                if sec_info is not None:
                    top_tag = self._get_node(u, v, cotas[nive[0]])
                    self._add_vertical("columna", info["sec_por_nivel"][nive[0]],
                                       f"col_{u}_{v}_base_{nive[0]}", nive[0],
                                       btag, top_tag, sec_info)

        # 2) muros equivalentes por niveles con evidencia (SE CREAN ANTES QUE LAS
        #    VIGAS para que los extremos de viga encuentren nodos de muro/columna
        #    y puedan fusionarse por misma posicion fisica). Ensamblaje por FAMILIA
        #    fisica de muro: nunca un puente que salte un piso sin conexion.
        self._add_muros(cotas, orden, base_z)

        # 3) vigas por nivel: divididas en las uniones/columnas/muros ortopogo.
        #    Cada tramo se engancha a los nodos existentes (columna/muro) por misma
        #    posicion fisica (fusion por tolerancia pequena documentada).
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
                if len(pts) < 2:
                    continue
                sec_info = SEC.seccion_viga(v["seccion"])
                if sec_info is None:
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

        # 4) conexion excentrica real (documentada en DXF): la viga perimetral P1
        #    'GV_CP1_GE_este' a v=-0.2 atraviesa longitudinalmente las columnas de la
        #    fila (desfase 0.2 m dentro del ancho 0.7 m). Se conecta por enlace rigido
        #    cinematico (rigidLink beam) al nodo de columna del nivel, preservando su
        #    posicion v=-0.2 (NO se traslada la viga a v=0).
        self._add_p1_eccentric_beam_links(cotas)

        # 4b) portico del cielo del subterraneo (CP1S): las vigas del portico
        #     (V_x0060, H_y0601, H_y1625) estan desfasadas ~0.3-0.43 m respecto a las
        #     columnas de la retícula publica (u=0/10) que bajan a cimentacion. El
        #     desfase cae dentro del pie de columna P.70x70 -> conexiones reales
        #     perdidas al sustituir muros por barras (no se incluyo el nucleo eje F
        #     M_EI_CP1S_003). Se re-anclan por enlace rigido cinematico documentado.
        self._add_cp1s_eccentric_beam_links(cotas)

        # 4c) soporte real de la V.S.I. H_y2732: muros de contencion del sotano que
        #     descienden a la cimentacion y subida del cielo; la viga se apoya en el
        #     extremo superior (cota CP1S) del muro, no en un pie fijado.
        self._add_muros_contencion_sotano(cotas)

        # 5) diafragmas rigidos por nivel (P1..P4) con relacion cinematia que incluye
        #    rotacion y distancias al maestro (rigidDiaphragm en el plano x-y).
        self._apply_diafragmas(cotas, orden)

        # 5b) apoyo en losa de las cadenas sin camino vertical a cimentacion:
        #     rodillo vertical (w fijo) en el nodo mas bajo de la cadena.
        if not self.defer_anclar_apoyos:
            self._anclar_apoyos_losa()

    def _add_muros(self, cotas, orden, base_z):
        """Ensamblaje por FAMILIA fisica de muro (misma linea y rango con
        solape), no por id ni por (ua,va,ub,vb) completos: el mismo muro puede
        cambiar de extremos entre niveles. Se crean montantes en las cotas de
        DEMARCACION (union de extremos de la familia) con nodo en CADA nivel en
        que la familia cubre esa cota, y un elemento vertical solo entre niveles
        consecutivos cubiertos de la MISMA serie contigua (nunca un puente que
        salte un piso ausente: si el muro falta en un nivel intermedio se
        desconecta en series independientes, segun evidencia fisica). Cada
        montante lleva la tributaria de longitud del muro en ese nivel
        (t x L_local/2 por particion de rango), conservando el area total t x L
        una sola vez. No se inventan tramos hacia cimentacion para cuerdas que
        arrancan sobre el nivel base (se apoyan en el diafragma del nivel);
        solo se fijan en base los montantes cuya serie comienza en el nivel
        base."""
        cfg = CFG.activa()
        E = 1e-3
        excluidos = set(cfg.muros_contencion_sotano)
        lineas = {}
        for cod in orden:
            for m in self.niveles[cod].muros:
                if m.get("id") in excluidos:
                    continue
                ua, va, ub, vb = m["ua"], m["va"], m["ub"], m["vb"]
                if abs(ua - ub) < E:
                    linea = ("V", round(ua, 3))
                    a, b = round(min(va, vb), 3), round(max(va, vb), 3)
                elif abs(va - vb) < E:
                    linea = ("H", round(va, 3))
                    a, b = round(min(ua, ub), 3), round(max(ua, ub), 3)
                else:
                    self.pendientes["muros"].append({
                        "id": m["id"], "nivel": cod,
                        "estado": "PENDIENTE_DE_FUENTE",
                        "nota": "muro no axis-alineado (no agrupable por linea)"})
                    continue
                lineas.setdefault(linea, []).append({
                    "cod": cod, "id": m["id"], "espesor": m["espesor"],
                    "a": a, "b": b})
        familias = []
        for linea, ints in lineas.items():
            n = len(ints)
            padre = list(range(n))

            def find(x):
                while padre[x] != x:
                    padre[x] = padre[padre[x]]
                    x = padre[x]
                return x

            def union(x, y):
                rx, ry = find(x), find(y)
                if rx != ry:
                    padre[ry] = rx

            for i in range(n):
                for j in range(i + 1, n):
                    if min(ints[i]["b"], ints[j]["b"]) \
                       - max(ints[i]["a"], ints[j]["a"]) > E:
                        union(i, j)
            grupos = {}
            for i in range(n):
                grupos.setdefault(find(i), []).append(ints[i])
            for members in grupos.values():
                demark = sorted({m["a"] for m in members}
                                | {m["b"] for m in members})
                familias.append({
                    "linea": linea, "demarcacion": demark,
                    "por_nivel": {m["cod"]: m for m in members}})

        def _tributaria(a, b, demark, E1):
            """Reparto de longitud del muro a cada montante (cota de
            demarcacion presente en el rango [a,b] del nivel): la mitad de cada
            tramo adyacente. Conserva el area total t x (b-a) por nivel."""
            pts = [q for q in demark if a - E1 <= q <= b + E1]
            if not pts:
                return {}
            out = {}
            for k, q in enumerate(pts):
                previo = pts[k - 1] if k > 0 else None
                nxt = pts[k + 1] if k < len(pts) - 1 else None
                izq = (q - previo) / 2.0 if previo is not None else 0.0
                der = (nxt - q) / 2.0 if nxt is not None else 0.0
                out[q] = izq + der
            return out

        def _tramos_contiguos(nive_cubre):
            """Divide los niveles cubiertos en series consecutivas (sin saltos)."""
            ind = {c: i for i, c in enumerate(orden)}
            runs = []
            cur = [nive_cubre[0]]
            for c in nive_cubre[1:]:
                if ind[c] == ind[cur[-1]] + 1:
                    cur.append(c)
                else:
                    runs.append(cur)
                    cur = [c]
            runs.append(cur)
            return runs

        self.ejes_muros = []
        for fam in familias:
            linea, demark = fam["linea"], fam["demarcacion"]
            por_nivel = fam["por_nivel"]
            nive = sorted(por_nivel, key=cotas.__getitem__)
            self.ejes_muros.append({
                "linea": {"tipo": linea[0], "coordenada": linea[1]},
                "demarcacion": demark, "niveles": nive,
                "por_nivel": {c: {"espesor": por_nivel[c]["espesor"],
                                  "rango": [por_nivel[c]["a"],
                                            por_nivel[c]["b"]],
                                  "id": por_nivel[c]["id"]}
                              for c in nive}})
            for p in demark:
                cubre = [c for c in nive
                         if por_nivel[c]["a"] - E <= p <= por_nivel[c]["b"] + E]
                if not cubre:
                    continue

                def coords(q):
                    if linea[0] == "V":
                        return linea[1], q
                    return q, linea[1]

                ex, ey = coords(p)
                for run in _tramos_contiguos(cubre):
                    if len(run) < 2:
                        if run[0] == cfg.nivel_base:
                            # muro SOLO en el nivel base (p.ej. sotano): nodo fijo
                            # de apoyo SIN elemento (la cuerda no sube).
                            self._fix_base(
                                self._snap_node_scaffold(ex, ey, cotas[run[0]]))
                        else:
                            # muro de UN solo nivel fuera del nivel base: NO se
                            # crea nodo ni tramo (evita DOF vertical libre en un
                            # nodo sin elemento incidente ni fijacion). Queda
                            # PENDIENTE_DE_FUENTE: el dato faltante es la cota
                            # superior (altura no confirmada en fuentes). El
                            # receptor 2b tampoco lo vincula: sin nodo no se
                            # registra (TB reporta la consiguiente tributaria
                            # como sin FE en vez de trasladarla a un vecino).
                            ids_que_cubren = sorted({
                                mm["id"] for mm in por_nivel.values()
                                if mm["cod"] == run[0]
                                and mm["a"] - E <= p <= mm["b"] + E})
                            self.pendientes["muros"].append({
                                "linea": linea, "cota_demarcacion": p,
                                "nivel": run[0],
                                "espesor": por_nivel[run[0]]["espesor"],
                                "ids": ids_que_cubren,
                                "estado": "PENDIENTE_DE_FUENTE",
                                "dato_faltante": "cota_superior",
                                "nota": ("muro de un solo nivel documentado "
                                         "fuera del nivel base: sin elemento FE, "
                                         "sin nodo ni tramo inventado hacia el "
                                         "siguiente nivel; la altura no tiene "
                                         "fuente")})
                        continue
                    if run[0] != cfg.nivel_base:
                        # Exclusion documentada del modelo definitivo: la cuerda
                        # multi-nivel ARRANCA sobre el nivel base sin camino fisico
                        # de apoyo hacia cimentacion. Clasificada por planos y
                        # topologia como apoyo sobre LOSA DE TRANSFERENCIA del nivel
                        # de arranque: no hay viga ni columna de apoyo directo ni
                        # continuidad de muro alineada en los niveles inferiores
                        # (P1 no dibuja el nucleo; CP1S lo dibuja en ejes
                        # desplazados). La rigidez fuera del plano de la losa NO esta
                        # modelada (diafragma rigido solo en plano), asi que NO se
                        # puede cerrar el camino vertical con un elemento FE real.
                        # Por tanto el componente queda FUERA del modelo definitivo:
                        # sin nodo, sin elemento vertical, sin restriccion artificial
                        # (no se fuerza estabilidad). La tributaria del receptor se
                        # reporta como sin FE (TB) y su peso pasa a G pendiente.
                        ids_que_cubren = sorted({
                            mm["id"] for mm in por_nivel.values()
                            if mm["cod"] in run
                            and mm["a"] - E <= p <= mm["b"] + E})
                        self.pendientes["muros"].append({
                            "linea": linea, "cota_demarcacion": p,
                            "nivel": run[0],
                            "espesor": por_nivel[run[0]]["espesor"],
                            "ids": ids_que_cubren,
                            "estado": "PENDIENTE_DE_FUENTE",
                            "dato_faltante": "apoyo_fisico_inferior",
                            "nota": ("cuerda de muro multi-nivel que arranca sobre "
                                     "el nivel base SIN apoyo fisico documentado: sin "
                                     "viga, columna ni muro alineado en niveles "
                                     "inferiores (planos); apoyo por losa de "
                                     "transferencia cuya rigidez fuera del plano NO "
                                     "esta modelada. Componente EXCLUIDO del modelo "
                                     "definitivo y limitacion declarada; no se fuerza "
                                     "estabilidad con restriccion artificial")})
                        self._componentes_excluidos_apoyo.append({
                            "linea": linea, "cota_demarcacion": p,
                            "nivel_arranque": run[0],
                            "ids": ids_que_cubren})
                        continue
                    last = None
                    for c in run:
                        zc = cotas[c]
                        tag = self._snap_node_scaffold(ex, ey, zc)
                        if last is not None:
                            sec = por_nivel[c]["espesor"]
                            trib_reparto = _tributaria(
                                por_nivel[c]["a"], por_nivel[c]["b"],
                                demark, E)
                            Lt = trib_reparto.get(p)
                            if Lt is None or Lt <= 0:
                                Lt = (por_nivel[c]["b"]
                                      - por_nivel[c]["a"]) / 2.0
                            sec_info = SEC.seccion_muro(sec, Lt)
                            self._add_vertical(
                                "muro", "M %sx%.2fx2" % (sec, Lt),
                                "muro_%s_%s_%s" % (ex, ey, c), c,
                                last, tag, sec_info)
                        last = tag
        # 2b) vinculo de los IDENTIFICADORES originales de muro a sus nodos
        #     montante reales por nivel (para el reparto tributario por id).
        for cod in orden:
            zc = cotas[cod]
            for m in self.niveles[cod].muros:
                if m.get("id") in excluidos:
                    continue
                ta = self._nodo_existente(m["ua"], m["va"], zc)
                tb = self._nodo_existente(m["ub"], m["vb"], zc)
                reg = self.receptor_nodos.setdefault(m["id"], [])
                for t in (ta, tb):
                    if t is not None and t not in reg:
                        reg.append(t)

    def _nodo_existente(self, u, v, z):
        """Devuelve el tag de un nodo existente en (u,v,z) dentro de MERGE_TOL
        (reuso por misma posicion fisica), SIN CREAR ningun nodo. None si la
        posicion no tiene nodo: se usa en el vinculo 2b de muros para NO
        materializar nodos de muros pendientes sin elemento (si el extremo no
        coincide con un montante real ya creado, el receptor queda sin nodos y
        TB reporta su tributaria como sin FE en vez de trasladarla a un
        vecino)."""
        target = _key(u, v, z)
        if target in self.nodes:
            return self.nodes[target]
        best_tag, best_d = None, None
        for (k, tag) in self.nodes.items():
            if abs(k[2] - z) > 1e-6:
                continue
            d = math.hypot(k[0] - u, k[1] - v)
            if d <= MERGE_TOL and (best_tag is None or d < best_d):
                best_tag, best_d = tag, d
        return best_tag

    def _fix_base(self, tag):
        if tag not in self._base_fixed:
            ops.fix(tag, 1, 1, 1, 1, 1, 1)
            self._base_fixed.add(tag)

    def _anclar_apoyos_losa(self):
        """Idealizacion documentada (NO inventa estructura): los montantes cuya
        cadena vertical NO tiene camino a la cimentacion (sin nodo con apoyo de
        base ni columna continua por debajo, p.ej. nucleos que arrancan en P2 con
        evidencia pero sin columna en esa posicion) se apoyan en la LOSA del
        nivel: se fija el desplazamiento vertical (w) del nodo mas bajo de cada
        cadena (rodillo vertical). No se traslada carga a montantes vecinos ni se
        crean tramos: solo se cierra el camino vertical que en obra aporta la
        losa. Las cadenas con nodo fijo en base, o conectadas por columnas/vigas
        a una de ellas, se consideran ancladas y no se tocan."""
        ap = []
        base = set(self._base_fixed)
        adj = {int(t): set() for t in self.nodes.values()}
        for r in list(self.muros_elem) + list(self.columnas) + list(self.vigas_elem):
            i, j = int(r["nodo_i"]), int(r["nodo_j"])
            adj.setdefault(i, set()).add(j)
            adj.setdefault(j, set()).add(i)
        # Enlaces rigidos REALES ya aplicados al modelo (rigidLink ['beam'] del portico
        # del cielo CP1S y restricciones contencion): el nodo esclavo sigue al maestro,
        # que es una columna/muro con camino a cimentacion. Se incluyen como aristas de
        # la componente para NO forzar un apoyo artificial sobre elementos ya soportados
        # por conexion real documentada (las cadenas se consideran ancladas). Los
        # conectores elasticos cortos (stub) ya estan en vigas_elem (adyacencia real).
        constr = []
        for r in getattr(self, "rigid_links_info", []):
            if r.get("tipo") == "stub_elastico_rigidez_elevada":
                continue
            a, b = int(r.get("col_tag")), int(r.get("beam_tag"))
            if a in adj and b in adj:
                adj[a].add(b)
                adj[b].add(a)
                constr.append({"master": a, "esclavo": b})
        self.enlaces_rigidos_reales = constr
        vistos_g = set()
        for t in adj:
            if t in vistos_g or (t in base and adj[t]):
                continue
            visto = set([t])
            pila = [t]
            while pila:
                x = pila.pop()
                for y in adj.get(x, ()):
                    if y not in visto:
                        visto.add(y)
                        pila.append(y)
            vistos_g |= visto
            if base & visto:
                continue
            lower = min(visto, key=lambda x: (self.key_of_tag[x][2], x))
            if lower not in self._apoyos_losa_fixed:
                ops.fix(lower, 0, 0, 1, 0, 0, 0)
                self._apoyos_losa_fixed.add(lower)
            ap.append({
                "tag": lower, "u": self.key_of_tag[lower][0],
                "v": self.key_of_tag[lower][1], "z": self.key_of_tag[lower][2],
                "n_nodos_cadena": len(visto),
                "nodos": sorted(visto)})
        self.apoyos_losa = ap

    def _snap_node_scaffold(self, u, v, z):
        """Crea (o reusa) nodo en (u,v,z). Fusiona por misma posicion fisica con una
        tolerancia pequena documentada (MERGE_TOL) para corregir incoherencias
        numericas del JSON/DXF (p.ej. 16.501 vs 16.5): si existe un nodo estructural
        al mismo nivel dentro de MERGE_TOL, se reusa SU tag (conservando sus coords),
        de modo que el elemento que llega queda conectado. Se registra el merge.
        Los casos fuera de MERGE_TOL pero dentro de NEAR_TOL NO se fusionan: se
        registran como 'casi encuentro' para identificacion especifica (p.ej. 5 cm).
        NO se fusionan desplazamientos de 0.2 m (excentricidad real, ver P1).
        """
        target = _key(u, v, z)
        if target in self.nodes:
            return self.nodes[target]
        best_tag, best_d = None, None
        near = []
        for (k, tag) in self.nodes.items():
            if abs(k[2] - z) > 1e-6:
                continue
            d = math.hypot(k[0] - u, k[1] - v)
            if d <= MERGE_TOL:
                if best_tag is None or d < best_d:
                    best_tag, best_d = tag, d
            elif d <= NEAR_TOL:
                near.append((d, tag, k))
        if best_tag is not None:
            self.merges.append({"u": u, "v": v, "z": round(z, 3),
                                "tag_reusado": best_tag, "dist_m": round(best_d, 4)})
            return best_tag
        for (d, tag, k) in near:
            self.casi_encuentros.append({"u": u, "v": v, "z": round(z, 3),
                                         "cerca_de": list(k), "dist_m": round(d, 4)})
        return self._get_node(u, v, z)

    def _add_p1_eccentric_beam_links(self, cotas):
        """Conexion excentrica real de la viga P1 'GV_CP1_GE_este' (a v=-0.2, pasando
        longitudinalmente sobre las columnas de la fila, desfase 0.2 m dentro del ancho
        0.7 m). Verificado en DXF 101: la viga se dibuja como segmentos contiguos
        rotos exactamente en cada columna de esa fila. Se une por enlace rigido
        cinematico (rigidLink 'beam') ANCLANDO LOS DOS EXTREMOS de la viga a las
        columnas H (u=30) e Ip (u=45) del nivel P1, preservando la excentricidad
        v=-0.2 (no se traslada la viga). Con ambos extremos enlazados a columnas la
        viga queda soportada en v=y no requiere enlace en la columna central I.
        Idealizacion de union rigida = hipotesis de laboratorio (no hay detalle
        constructivo). Se registran los pares (columna, viga) para el diagnostico."""
        cfg = CFG.activa()
        p1 = cfg.viga_excentrica_p1_nivel
        if p1 is None or p1 not in cotas:
            self.p1_eccentric_links = []
            self.rigid_links_info = []
            return
        zc = cotas[p1]
        beam = cfg.viga_excentrica_p1_id
        beam_v = cfg.viga_excentrica_p1_v
        beam_tags = set()
        for r in self.vigas_elem:
            if r["elemento_id"] == beam:
                beam_tags.add(int(r["nodo_i"]))
                beam_tags.add(int(r["nodo_j"]))
        beam_tags = [t for t in beam_tags
                     if abs(self.key_of_tag[t][2] - zc) < 1e-6
                     and abs(self.key_of_tag[t][1] - beam_v) < 0.05]
        if not beam_tags:
            self.p1_eccentric_links = []
            self.rigid_links_info = []
            return
        # extremos de la viga (min/max x)
        extr_min = min(beam_tags, key=lambda t: self.key_of_tag[t][0])
        extr_max = max(beam_tags, key=lambda t: self.key_of_tag[t][0])
        cols = dict(cfg.viga_excentrica_p1_grid)
        applied = []
        rlinks = []
        for cu, col in cols.items():
            if cu not in (30.0, 45.0):
                continue
            col_tag = self.nodes.get(_key(cu, 0.0, zc))
            beam_tag = extr_min if cu == 30.0 else extr_max
            if col_tag is None:
                continue
            self._add_stub_rigid(col_tag, beam_tag)
            applied.append({"columna": col, "coord_col": [round(x, 3) for x in self.key_of_tag[col_tag][:2]],
                            "viga_nodo": [round(x, 3) for x in self.key_of_tag[beam_tag][:2]],
                            "desfase_m": round(abs(self.key_of_tag[col_tag][1] - self.key_of_tag[beam_tag][1]), 4)})
            rlinks.append({"col_tag": int(col_tag), "beam_tag": int(beam_tag),
                           "tipo": "stub_elastico_rigidez_elevada",
                           "rigidez_mult": self.rigidez_mult})
        self.p1_eccentric_links = applied
        self.rigid_links_info = rlinks

    def _add_stub_rigid(self, col_tag, beam_tag):
        """Conector corto de rigidez elevada entre la cabeza de la columna y el extremo
        excentrico de la viga (IDEALIZACION ELASTICA, NO un vinculo rigido exacto).

        Reemplaza al rigidLink 'beam' (antes usado aqui) cuyo MAESTRO era a su vez
        esclavo del diafragma del piso. Esa cadena anidada (rigidLink sobre un nodo
        cuya restriccion rigidDiaphragm se impone con el manejador Transformation)
        NO se compone correctamente: el esclavo no segua al maestro (verificado con
        un test minimo en 3D). Se sustituye por un elasticBeamColumn muy corto y de
        rigidez elevada (E*mult, G*mult) que reproduce el acoplamiento excentrico de
        forma compatible con Transformation, conservando la excentricidad fisica.
        El multiplicador es parametrizable (rigidez_mult) para estudiar sensibilidad.
        El conector se registra en stub_elem y en vigas_elem para que participe en la
        extraccion y en el diagnostico.

        IMPORTANTE (coherencia fe/diagnostico): sec_valores guarda las propiedades
        EFECTIVAMENTE utilizadas por OpenSees (E*mult, G*mult), de modo que el
        diagnostico (ensamblar_K) monte exactamente los mismos conectores que el
        modelo resuelto. Tambien se anota el multiplicador para trazabilidad."""
        sr = SEC.seccion_viga("V. 60/80")
        prof = dict(sr)
        E, A, Iz, Iy, G, J = sr["E"], sr["A"], sr["Iz"], sr["Iy"], sr["G"], sr["J"]
        mult = self.rigidez_mult
        tag = self._next
        self._next += 1
        ops.section("Elastic", tag, E * mult, A, Iz, Iy, G * mult, J)
        (xa, ya, za) = self.key_of_tag[int(col_tag)]
        (xb, yb, zb) = self.key_of_tag[int(beam_tag)]
        dx, dy, dz = xb - xa, yb - ya, zb - za
        if abs(dz) > 1e-3 or (abs(dx) < 1e-6 and abs(dy) < 1e-6):
            vec = (0.0, 1.0, 0.0)
        else:
            vec = (0.0, 0.0, 1.0)
        tf = self._ensure_transf(vec)
        ops.element("elasticBeamColumn", tag, int(col_tag), int(beam_tag), tag, tf)
        rec = {"elemento_id": "STUB_RIGID_%s_%s" % (col_tag, beam_tag),
               "tipo": "stub_elastico_rigidez_elevada", "seccion": "RIGIDA",
               "nivel": za,
               "nodo_i": int(col_tag), "nodo_j": int(beam_tag), "tag": tag,
               "transf": tf, "u_i": xa, "v_i": ya, "u_j": xb, "v_j": yb,
               "z_i": za, "z_j": zb,
               "rigidez_mult": mult,
               "sec_valores": dict(prof, E=E * mult, G=G * mult)}
        self.stub_elem.append(rec)
        self.vigas_elem.append(rec)

    def _add_cp1s_eccentric_beam_links(self, cotas):
        """Portico del cielo del subterraneo (z=CP1S). Las vigas V_x0060 / H_y0601 /
        H_y1625 (secciones V. 60/80, definidas en la candidata del subterraneo) forman
        un portico cuyo apoyo derecho era el nucleo eje F (muro M.E.H.A. e=70 =
        M_EI_CP1S_003) y cuyos apoyos izquierdos son las columnas P.70x70 de la linea
        u=0/10 que bajan a cimentacion. Al sustituir muros por barras y no modelar las
        columnas explicitas del subterraneo, estos extremos quedaron a 0.30-0.43 m de
        las columnas publicas (u=0/10), dentro del pie de columna 0.7 m -> conexiones
        reales perdidas. Se re-anclan por enlace rigido cinematico (rigidLink 'beam')
        documentado, conservando la excentricidad (no se trasladan las vigas).
        V_S.I. H_y2732 (20/150) NO se enlaza: no tiene columna/muro documentado en su
        linea (candidatos y DXF no lo muestran) -> se reporta como dato faltante."""
        cfg = CFG.activa()
        frame = list(cfg.cp1s_frame_beams)
        if not frame or not cfg.nivel_basamento_sin_diafragma:
            self.cp1s_eccentric_links = []
            return
        zc = cotas[cfg.nivel_basamento_sin_diafragma]
        col_us = tuple(cfg.cp1s_frame_col_u)
        # columnas publicas del basamento disponibles como apoyo (tag)
        col_tags = [t for t in self.nodes.values()
                    if abs(self.key_of_tag[t][2] - zc) < 1e-6
                    and any(abs(self.key_of_tag[t][0] - cu) < 0.02
                            for cu in col_us)]
        applied = []
        rlinks = []
        for r in self.vigas_elem:
            if r["elemento_id"] not in frame:
                continue
            i, j = int(r["nodo_i"]), int(r["nodo_j"])
            if abs(self.key_of_tag[i][2] - zc) > 1e-6:
                continue
            for bn in (i, j):
                bx, by, _ = self.key_of_tag[bn]
                # ya enlazado?
                best = None
                for ct in col_tags:
                    ck = self.key_of_tag[ct]
                    d = math.hypot(ck[0] - bx, ck[1] - by)
                    if d <= 0.45 and (best is None or d < best[0]):
                        best = (d, ct, ck)
                if best is None:
                    continue
                d, ct, ck = best
                already = any(rl["beam_tag"] == bn for rl in rlinks)
                if already:
                    continue
                ops.rigidLink("beam", int(ct), int(bn))
                applied.append({"viga": r["elemento_id"],
                                "viga_nodo": [round(x, 3) for x in (bx, by)],
                                "columna": [round(x, 3) for x in ck[:2]],
                                "desfase_m": round(d, 3)})
                rlinks.append({"col_tag": int(ct), "beam_tag": int(bn)})
        self.cp1s_eccentric_links = applied
        self.rigid_links_info.extend(p for p in rlinks
                                     if p not in self.rigid_links_info)

    def _add_p4_grillaje_links(self, cotas):
        """Grillaje de la torre sobre la losa P4 (anillo de vigas V.E.I. de la candidata
        de la torre, 10 nodos en z=CP4). Apoyo fisico real DOCUMENTADO: los nodos del
        anillo caen dentro del pie (<0.45 m) de los montantes que bajan a cimentacion
        (patas de la torre V.E.I. y columnas de la reticula P4 G3/H3/GS6/HS7). La losa
        fuera del plano no esta modelada, asi que cada nodo del anillo se conecta a su
        montante mas cercano con el MISMO conector corto elastico de rigidez elevada que
        P1 y la reticula P4 (nunca rigidLink anidado bajo el diafragma de P4). NO se
        traslada el anillo, NO se crea viga ni columna, NO se inventa apoyo: se restaura
        la union real pie-a-pie que el plano documenta. Registro en p4_grillaje_links."""
        p4 = cotas.get("P4", cotas.get("CP4"))
        if p4 is None:
            self.p4_grillaje_links = []
            return
        # Centroides del grillaje de la torre documentados en el plano del nivel P4
        # (anillo de vigas V.E.I.): solo estas coordenadas son del anillo; las columnas
        # P4 (v fisica 16.331) y las patas de la torre SON soporte, no parte del anillo.
        RING = [(19.7, 16.45), (20.3, 16.45), (29.7, 16.45), (30.3, 16.45),
                (19.7, 20.57), (20.3, 20.57), (29.7, 20.57), (30.3, 20.57),
                (20.3, 20.15), (29.7, 20.15)]
        ring_seen = {}
        for t in self.nodes.values():
            u, v, z = self.key_of_tag[t]
            if abs(z - p4) > 1e-6:
                continue
            for (ru, rv) in RING:
                if abs(u - ru) <= 0.011 and abs(v - rv) <= 0.011:
                    if (ru, rv) not in ring_seen:
                        ring_seen[(ru, rv)] = t
                    break
        ring = list(ring_seen.values())
        pool = sorted(t for t in self.nodes.values()
                      if t not in ring
                      and abs(self.key_of_tag[t][2] - p4) < 1e-6
                      and 17.5 <= self.key_of_tag[t][0] <= 31.5)
        applied = []
        for bn in sorted(ring):
            bx, by, _ = self.key_of_tag[bn]
            best = None
            for ct in pool:
                ck = self.key_of_tag[ct]
                d = math.hypot(ck[0] - bx, ck[1] - by)
                if 1e-6 < d <= 0.45 and (best is None or d < best[0]):
                    best = (d, ct, ck)
            if best is None:
                continue
            d, ct, ck = best
            if any(rl.get("beam_tag") == bn for rl in self._p4_links_seen):
                continue
            self._add_stub_rigid(ct, bn)
            self._p4_links_seen.append({"col_tag": int(ct), "beam_tag": int(bn)})
            applied.append({"nodo": int(bn),
                            "viga_nodo": [round(x, 3) for x in (bx, by)],
                            "soporte": [round(x, 3) for x in ck[:2]],
                            "desfase_m": round(d, 3)})
        self.p4_grillaje_links = applied

    def _registrar_hipotesis_muros_contencion(self):
        """Registra la hipotesis de laboratorio de los muros de contencion del sotano:
        descienden desde el cielo del sotano hasta la cimentacion (HIPOTESIS academica
        configurable; el plano no documenta la elevacion de cimentacion). No modifica
        la geometria en planta de los candidatos."""
        cfg = CFG.activa()
        muros = cfg.muros_contencion_sotano
        self.hipotesis_muros_contencion = []
        if not muros:
            return
        z_cielo = COTAS_NIVEL_M[cfg.nivel_basamento_sin_diafragma]
        z_cim = cfg.cota_cimentacion_sotano
        self.hipotesis_muros_contencion = [
            {"muro": mid, "u": mc["u"], "e": mc["e"],
             "z_cielo": z_cielo, "z_cimentacion": z_cim}
            for mid, mc in muros.items()]

    def _add_muros_contencion_sotano(self, cotas):
        """Soporte real de la V.S.I. H_y2732 (viga del cielo del subterraneo, z=CP1S).

        Los muros de contencion M_001 (u=-0.35, e=0.2) y M_002 (u=21.25, e=0.3)
        descienden desde el cielo del subterraneo (z=CP1S) hasta la cimentacion
        COTA_CIMENTACION_SOTANO_M (HIPOTESIS academica configurable, hipotesis.py).
        Se modelan como muros verticales reales (seccion espesor x panel/2), fijados en
        base SOLO en la cota de cimentacion. La V.S.I. se apoya en el extremo SUPERIOR
        del muro (a cota CP1S, un nodo interior libre del muro): el apoyo es la rigidez
        axial/flexional real del muro, NUNCA un pie fijado en el plano del cielo.

        Conexion excentrica real (documentada): el extremo u=-0.15 de la viga queda a
        0.2 m de la cara interior de M_001 (eje u=-0.35), dentro del espesor; se une por
        enlace rigido cinematico (rigidLink 'beam') con master = nodo del muro (apoyo
        real), NO se traslada la viga. El extremo derecho u=21.25 coincide con el eje de
        M_002 (mismo nodo). Ambas paredes se registran como receptoras (sus nodos) para
        que su carga de losa no se descarte."""
        cfg = CFG.activa()
        muros = cfg.muros_contencion_sotano
        vsi_id = cfg.vsi_beam_id
        vsi_v = cfg.vsi_v
        vsi_u = cfg.vsi_u
        muro_izq = cfg.vsi_muro_izq
        muro_der = cfg.vsi_muro_der
        z_fund = cfg.cota_cimentacion_sotano
        self.vsi_h_y2732_links = []
        if not muros or z_fund is None or vsi_id is None or vsi_u is None:
            return
        basamento = cfg.nivel_basamento_sin_diafragma
        z_cielo = cotas[basamento]
        wall_top = {}
        panel_len = {mid: 5.0 for mid in muros}
        # longitud de panel equivalente de cada muro (extremo documentado hasta la
        # cota del cielo en el plano de la candidata)
        for mid, mc in muros.items():
            for m in self.niveles[basamento].muros:
                if m["id"] == mid:
                    panel_len[mid] = abs(m["vb"] - m["va"])
        for mid, mc in muros.items():
            u = mc["u"]
            e = mc["e"]
            etag = self._snap_node_scaffold(u, vsi_v, z_fund)   # pie en la cimentacion
            self._fix_base(etag)
            ttag = self._snap_node_scaffold(u, vsi_v, z_cielo)  # extremo superior (cielo)
            if etag == ttag:
                raise ValueError("montante de muro de contencion degenerado (base==cielo)")
            sec = SEC.seccion_muro(e, panel_len[mid] / 2.0)
            # elemento real del muro de contencion: cimentacion -> cielo del sotano
            self._add_vertical("muro", f"M {e}x{panel_len[mid]/2:.2f}x2",
                               f"{mid}_contencion", basamento, etag, ttag, sec)
            wall_top[vsi_u[0] if mid == muro_izq else vsi_u[1]] = ttag
            # registrar los nodos del muro como receptores (no se descarta su carga)
            self.receptor_nodos.setdefault(mid, []).append(etag)
            self.receptor_nodos.setdefault(mid, []).append(ttag)

        # anclar los extremos de la V.S.I. al extremo superior de los muros (apoyo real)
        beam_tags = sorted(set(
            int(t) for r in self.vigas_elem
            if r["elemento_id"] == vsi_id
            and abs(self.key_of_tag[int(r["nodo_i"])][2] - z_cielo) < 1e-6
            for t in (int(r["nodo_i"]), int(r["nodo_j"]))))
        applied = []
        if beam_tags:
            left = min(beam_tags, key=lambda t: self.key_of_tag[t][0])
            right = max(beam_tags, key=lambda t: self.key_of_tag[t][0])
            # extremo izquierdo -> muro de contencion izquierdo: enlace rigido excentrico
            wall_tag = wall_top[vsi_u[0]]
            if wall_tag is not None and left != wall_tag:
                ops.rigidLink("beam", int(wall_tag), int(left))
                applied.append({
                    "viga": vsi_id,
                    "viga_nodo": [round(x, 3) for x in self.key_of_tag[left][:2]],
                    "muro": muro_izq,
                    "muro_nodo": [round(x, 3) for x in self.key_of_tag[wall_tag][:2]],
                    "desfase_m": round(math.hypot(
                        self.key_of_tag[wall_tag][0] - self.key_of_tag[left][0],
                        self.key_of_tag[wall_tag][1] - self.key_of_tag[left][1]), 4),
                })
            # extremo derecho == eje del muro de contencion derecho: mismo nodo, sin enlace
            wall_tag2 = wall_top[vsi_u[1]]
            if wall_tag2 is not None and right == wall_tag2:
                applied.append({
                    "viga": vsi_id,
                    "viga_nodo": [round(x, 3) for x in self.key_of_tag[right][:2]],
                    "muro": muro_der,
                    "muro_nodo": [round(x, 3) for x in self.key_of_tag[wall_tag2][:2]],
                    "desfase_m": 0.0,
                })
        self.vsi_h_y2732_links = applied

    def _split_segment(self, x1, y1, x2, y2, joints, zc, tol=1e-3):
        """Divide [P1,P2] en las uniones (u,v) que caen sobre el segmento (tol m)."""
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            return [(x1, y1), (x2, y2)]
        pts = [(0.0, x1, y1), (1.0, x2, y2)]
        for (jx, jy) in joints:
            # proyeccion parametrica
            t = ((jx - x1) * dx + (jy - y1) * dy) / L2
            if t <= 1e-6 or t >= 1 - 1e-6:
                continue
            px, py = x1 + t * dx, y1 + t * dy
            if math.hypot(jx - px, jy - py) <= tol:
                pts.append((t, float(jx), float(jy)))
        pts.sort()
        out = []
        for t, u, v in pts:
            if not out or math.hypot(u - out[-1][0], v - out[-1][1]) > 1e-9:
                out.append((u, v))
        return out

    def _add_vertical(self, tipo, seccion, eid, nivel, ti, tj, sec_info):
        self._elem(tipo, eid, seccion, nivel, ti, tj, sec_info)

    def _add_horizontal(self, eid, nivel, ti, tj, sec_info):
        self._elem("viga", eid, "V", nivel, ti, tj, sec_info)

    def _add_subdivided_viga(self, eid, tipo, seccion, nivel, ti, tj, sec_info, transf_tag):
        """Subdivide una viga en `subdivision_vigas` sub-elementos entre sus nodos de
        tramo, creando nodos intermedios y registrando TODOS los nodos del tramo en
        `receptor_nodos[eid]`. De este modo `_pesos_por_nodo` reparte la carga
        tributaria como carga nodal CONSISTENTE sobre la malla refinada, permitiendo
        demostrar convergencia en el modelo real. Con subdivision_vigas==1 NO se
        invoca (comportamiento identico al dia)."""
        k = self.subdivision_vigas
        (ua, va, za) = (ops.nodeCoord(ti, 1), ops.nodeCoord(ti, 2), ops.nodeCoord(ti, 3))
        (ub, vb, zb) = (ops.nodeCoord(tj, 1), ops.nodeCoord(tj, 2), ops.nodeCoord(tj, 3))
        tags = [int(ti)]
        for m in range(1, k):
            tt = m / float(k)
            ntag = self._get_node(round(ua + tt * (ub - ua), 6),
                                  round(va + tt * (vb - va), 6),
                                  round(za + tt * (zb - za), 6))
            tags.append(ntag)
        tags.append(int(tj))
        for m in range(k):
            a = tags[m]; b = tags[m + 1]
            tag = self._next; self._next += 1
            self._ensure_section(tag, sec_info)
            ops.element('elasticBeamColumn', tag, a, b, tag, transf_tag)
            (xai, yai, zai) = (ops.nodeCoord(a, 1), ops.nodeCoord(a, 2), ops.nodeCoord(a, 3))
            (xbi, ybi, zbi) = (ops.nodeCoord(b, 1), ops.nodeCoord(b, 2), ops.nodeCoord(b, 3))
            self.vigas_elem.append({
                "elemento_id": eid, "tipo": tipo, "seccion": seccion, "nivel": nivel,
                "nodo_i": a, "nodo_j": b, "tag": tag, "transf": transf_tag,
                "u_i": xai, "v_i": yai, "u_j": xbi, "v_j": ybi,
                "z_i": zai, "z_j": zbi, "sec_valores": dict(sec_info),
                "subsegmento": m + 1})
        self.receptor_nodos.setdefault(eid, []).extend(tags)

    def _elem(self, tipo, eid, seccion, nivel, ti, tj, sec_info):
        tag = self._next; self._next += 1
        self._ensure_section(tag, sec_info)
        # transf: elementos horizontales (x-y): vec = +z (0,0,1); verticales: +y
        lt = [ti, tj]
        (ua, va, za) = ops.nodeCoord(ti, 1), ops.nodeCoord(ti, 2), ops.nodeCoord(ti, 3)
        (ub, vb, zb) = ops.nodeCoord(tj, 1), ops.nodeCoord(tj, 2), ops.nodeCoord(tj, 3)
        dx, dy, dz = ub - ua, vb - va, zb - za
        if abs(dz) > 1e-3:
            vec = (0.0, 1.0, 0.0)   # vertical: +y como vector de referencia
        elif abs(dx) < 1e-6 and abs(dy) < 1e-6:
            vec = (0.0, 1.0, 0.0)
        else:
            vec = (0.0, 0.0, 1.0)   # horizontal: +z
        transf_tag = self._ensure_transf(vec)
        if tipo == "viga" and self.subdivision_vigas > 1:
            self._add_subdivided_viga(eid, tipo, seccion, nivel, ti, tj, sec_info,
                                      transf_tag)
            return
        ops.element('elasticBeamColumn', tag, int(ti), int(tj), tag, transf_tag)
        rec = {"elemento_id": eid, "tipo": tipo, "seccion": seccion, "nivel": nivel,
               "nodo_i": ti, "nodo_j": tj, "tag": tag, "transf": transf_tag,
               "u_i": ua, "v_i": va, "u_j": ub, "v_j": vb,
               "z_i": za, "z_j": zb,
               "sec_valores": dict(sec_info)}
        if tipo == "columna":
            self.columnas.append(rec)
        elif tipo == "muro":
            self.muros_elem.append(rec)
        else:
            self.vigas_elem.append(rec)
        self.receptor_nodos.setdefault(eid, []).append(ti)
        self.receptor_nodos.setdefault(eid, []).append(tj)

    def _ensure_section(self, tag, sec_info):
        ops.section('Elastic', tag, sec_info["E"], sec_info["A"],
                    sec_info["Iz"], sec_info["Iy"], sec_info["G"], sec_info["J"])

    def _ensure_transf(self, vec):
        # transformaciones precargadas sencillas: Linear
        key = tuple(round(x, 4) for x in vec)
        if not hasattr(self, "_transf") or self._transf is None:
            self._transf = {}
        if key not in self._transf:
            tag = self._next; self._next += 1
            ops.geomTransf('Linear', tag, *vec)
            self._transf[key] = tag
        return self._transf[key]

    def _apply_diafragmas(self, cotas, orden):
        # por nivel (P1..P4): un master y esclavos del diafragma.
        # CP1S (basamento) queda EXCLUIDO del diafragma rigido (sus nodos ya tienen
        # apoyo vertical de la hipotesis de cimentacion y las bases fijas).
        # Se usa ops.rigidDiaphragm(3, master, *slaves): restringe en el plano x-y
        # (DOF 1 y 2) de cada esclavo al maestro con la relacion cinematia de cuerpo
        # rigido (incluye la rotacion y la distancia al maestro); el desplazamiento
        # vertical (w) y los giros fuera de plano quedan libres.
        # IMPORTANTE (cadena diafragma -> columna -> rigidLink bajo Transformation):
        # los nodos esclavos de rigidLink (extremos de vigas excentricas, p.ej. los
        # extremos a v=-0.2 de GV_CP1_GE_este) NO se incluyen como esclavos del
        # diafragma. Su vinculo al piso es por el rigidLink a una columna que SI es
        # esclava del diafragma (cadena transitiva); un doble vinculo (rigidDiaphragm
        # + rigidLink sobre el mismo nodo) crea restricciones redundantes que el
        # manejador Transformation resuelve de forma inconsistente (residuo cinemico
        # espurio). Cada nodo tiene EXACTAMENTE una restriccion cinematica limpia.
        rigid_slaves = set()
        for link in getattr(self, "rigid_links_info", []) or []:
            bt = link.get("beam_tag")
            if bt is not None:
                rigid_slaves.add(int(bt))
        basamento = CFG.activa().nivel_basamento_sin_diafragma
        for cod in [c for c in orden if c != basamento]:
            zc = cotas[cod]
            tags = sorted([t for k, t in self.nodes.items()
                           if abs(k[2] - zc) < 1e-6 and t not in rigid_slaves])
            if not tags:
                continue
            master = tags[0]
            self.master_por_nivel[cod] = master
            self.diafragma_esclavos_por_nivel[cod] = tags[1:]
            self.diafragma_excluidos_rigidlink[cod] = sorted(
                t for t in self.nodes.values()
                if abs(self.key_of_tag[t][2] - zc) < 1e-6 and t in rigid_slaves)
            if len(tags) > 1:
                ops.rigidDiaphragm(3, master, *tags[1:])

    def resumen(self):
        return {
            "n_nodos": len(self.nodes),
            "n_columnas": len(self.columnas),
            "n_vigas": len(self.vigas_elem),
            "n_muros": len(self.muros_elem),
            "master_por_nivel": self.master_por_nivel,
        }
