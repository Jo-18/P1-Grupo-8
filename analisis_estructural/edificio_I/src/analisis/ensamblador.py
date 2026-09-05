"""
Ensamblador estructural modular del Edificio I (MARCO, sin analisis real).

En esta fase el ensamblador NO ejecuta analisis estructural: registra nodos, vigas,
columnas, muros, niveles, conectividad vertical, masas, restricciones y cargas, y
verifica la consistencia interna. Los datos estructurales ausentes (materiales,
secciones, apoyos reales, continuidad vertical, cargas reales, combinaciones,
definicion sismica) se reportan como ENTRADA PENDIENTE y bloquean el analisis real.

El marco garantiza las reglas de la junta global: no cruzar la interfaz, no emparejar
nodos entre edificios, no compartir receptores y no volver a sumar el ancho.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .validadores import ProblemaEntrada


@dataclass
class Nodo:
    id: str
    x: float
    y: float
    z: float = 0.0

    def coincide_con(self, otro: "Nodo", tol: float = 1e-6) -> bool:
        return (abs(self.x - otro.x) <= tol and abs(self.y - otro.y) <= tol
                and abs(self.z - otro.z) <= tol)


@dataclass
class ElementoLineal:
    id: str
    tipo: str              # viga | columna
    nodo_i: str
    nodo_j: str
    nivel: str = ""
    seccion: str = ""

    def otros_nodos(self) -> List[str]:
        return [self.nodo_i, self.nodo_j]


@dataclass
class MuroEnsamblador:
    id: str
    nodo_a: str
    nodo_b: str
    nivel: str = ""


@dataclass
class Restriccion:
    nodo: str
    grados: str            # p.ej. "xyz", "xyz_rot" (marcador), "x", "vinc"
    tipo: str = "cstruct"


@dataclass
class CargaLinealDisponible:
    receptor_id: str
    nivel: str
    w_max_kNm: float = 0.0
    w_min_kNm: float = 0.0


class ModeloEnsamblador:
    """Marco del Edificio I. No ejecuta analisis real."""

    def __init__(self):
        self.nodos: Dict[str, Nodo] = {}
        self.elementos: List[ElementoLineal] = []
        self.muros: List[MuroEnsamblador] = []
        self.restricciones: List[Restriccion] = []
        self.cargas: Dict[str, CargaLinealDisponible] = {}
        self.columnas_continuidad: Dict[str, List[str]] = {}  # id_columna -> niveles
        self.niveles: List[str] = []
        self.junta_global = {
            "id_interfaz_global": "JD_EI_EII_10CM",
            "ancho_total_m": 0.10,
            "ancho_por_lado_m": None,
            "contabilizacion": "una_sola_vez_en_modelo_conjunto",
            "transferencia_entre_edificios": False,
            "estado_correlacion": "por_correlacionar",
            "estado_barrera_geometrica": "pendiente_correlacion_geometrica",
        }
        # registro DOCUMENTAL de la interfaz global: no demuestra por si mismo que
        # funcione como barrera; en control_barrera_junta() se aplican los controles
        # espaciales, que devuelven pendiente_correlacion_geometrica mientras no existan
        # las caras correlacionadas del Edificio II.
        self._barrera_linea = None
        self._receptores = []      # receptores de carga registrados (EI actualmente)
        self._nodos_lado: Dict[str, str] = {}  # nodo_id -> "Edificio I" | "Edificio II"

    # ------------------------------------------------------------------ #
    def registrar_nodo(self, n: Nodo) -> None:
        self.nodos[n.id] = n

    def registrar_viga(self, e: ElementoLineal) -> None:
        if e.tipo not in ("viga", "columna"):
            raise ValueError(f"tipo de elemento '{e.tipo}' no soportado")
        self.elementos.append(e)

    def registrar_muro(self, m: MuroEnsamblador) -> None:
        self.muros.append(m)

    def registrar_restriccion(self, r: Restriccion) -> None:
        self.restricciones.append(r)

    def registrar_carga(self, c: CargaLinealDisponible) -> None:
        self.cargas[c.receptor_id] = c

    # ------------------------------------------------------------------ #
    # Control de la barrera de la junta global (JD_EI_EII_10CM)
    # ------------------------------------------------------------------ #
    def set_barrera_junta_linea(self, linea) -> None:
        """Registra la linea de la interfaz (eje/caras) SI esta correlacionada."""
        self._barrera_linea = linea

    def marcar_nodo_lado(self, nodo_id: str, lado: str) -> None:
        """Registra a que edificio pertenece un nodo (para prohibir union entre lados)."""
        if lado not in ("Edificio I", "Edificio II"):
            raise ValueError(f"lado '{lado}' no valido")
        self._nodos_lado[nodo_id] = lado

    def registrar_receptor_lado(self, receptor_id: str, lado: str) -> None:
        self._receptores.append((receptor_id, lado))

    def control_barrera_junta(self) -> dict:
        """Ejecuta los controles de barrera de la junta global.

        Devuelve un dict con 'estado', 'problemas' y 'detalles'. El control espacial
        (cruces de elementos, union de nodos entre lados) solo puede resolverse cuando
        existen las caras correlacionadas del Edificio II; mientras tanto el estado es
        ``pendiente_correlacion_geometrica`` y NO se afirma que la barrera este validada.
        """
        from shapely.geometry import LineString  # noqa: F401 (uso futuro en cruce con cara correlacionada)

        problemas: List[ProblemaEntrada] = []
        # hay datos de Edificio II (nodos/receptores marcados) solo cuando existan las
        # caras correlacionadas. Si no, el control espacial queda pendiente.
        hay_caras_edificio_ii = any(
            lado == "Edificio II" for _, lado in self._nodos_lado.items()) or \
            any(lado == "Edificio II" for _, lado in self._receptores)

        # 1) transferencia de carga entre edificios (siempre comprobable por metadata)
        if self.junta_global.get("transferencia_entre_edificios") in (True, None):
            problemas.append(ProblemaEntrada(
                "TRANSFERENCIA_ENTRE_EDIFICIOS", "error", "junta_global",
                "no puede existir transferencia de carga hacia el Edificio II"))
        # 2) duplicacion del ancho total (0.10 una sola vez)
        if self.junta_global.get("ancho_total_m") != 0.10:
            problemas.append(ProblemaEntrada(
                "ANCHO_JUNTA_INVALIDO", "error", "junta_global",
                "ancho_total_m debe ser 0.10 m; los anchos por lado no se suman"))
        if self.junta_global.get("ancho_por_lado_m") is not None:
            problemas.append(ProblemaEntrada(
                "ANCHO_POR_LADO_INVALIDO", "error", "junta_global",
                "ancho_por_lado_m debe ser null (una sola vez, no por lado)"))

        # 3) union de nodos entre lados distintos (requiere caras correlacionadas)
        #    Solo puede comprobarse si tenemos nodos de ambos edificios.
        if hay_caras_edificio_ii:
            # elementos con ambos extremos en lados distintos = union prohibida
            for e in self.elementos:
                lado_i = self._nodos_lado.get(e.nodo_i)
                lado_j = self._nodos_lado.get(e.nodo_j)
                if lado_i and lado_j and lado_i != lado_j:
                    problemas.append(ProblemaEntrada(
                        "NODO_FUSIONADO_ENTRE_LADOS", "error", f"elementos.{e.id}",
                        "elemento une nodos de Edificio I y Edificio II"))

        # 4) receptores compartidos entre EI y EII (requiere correlacion)
        if hay_caras_edificio_ii:
            receptores_EI = {rid for rid, lado in self._receptores if lado == "Edificio I"}
            receptores_EII = {rid for rid, lado in self._receptores if lado == "Edificio II"}
            compartidos = receptores_EI & receptores_EII
            if compartidos:
                problemas.append(ProblemaEntrada(
                    "RECEPTOR_COMPARTIDO_EI_EII", "error", "receptores",
                    "no pueden compartirse receptores entre Edificio I y Edificio II: "
                    + ", ".join(sorted(compartidos))))

        # 5) elementos que cruzan la interfaz: se completa cuando exista la cara
        #    correlacionada del Edificio II (coordenadas para el cruce geometrico).
        #    Mientras tanto queda en estado pendiente_correlacion_geometrica.

        # estado final de la barrera
        if not hay_caras_edificio_ii:
            estado = "pendiente_correlacion_geometrica"
        elif problemas:
            estado = "barrera_violada"
        else:
            estado = "validada"

        self.junta_global["estado_barrera_geometrica"] = estado
        errores = [p for p in problemas if p.nivel == "error"]
        return {
            "estado": estado,
            "ok": not errores,
            "n_problemas": len(problemas),
            "problemas": [p.codigo for p in problemas],
            "exige_caras_Edificio_II": not hay_caras_edificio_ii,
            "detalle": ("Cuando existan las caras correlacionadas del Edificio II se "
                        "completaran los controles espaciales de cruce y union de nodos."),
        }

    # ------------------------------------------------------------------ #
    def validar_consistencia(self) -> List[ProblemaEntrada]:
        problemas: List[ProblemaEntrada] = []
        ids = set(self.nodos)

        # IDs unicos de elementos
        vistos = set()
        for e in self.elementos:
            if e.id in vistos:
                problemas.append(ProblemaEntrada(
                    "ELEMENTO_ID_DUPLICADO", "error", f"elementos.{e.id}",
                    "identificador de elemento repetido"))
            vistos.add(e.id)

        # nodos referenciados existen
        for e in self.elementos:
            for nid in (e.nodo_i, e.nodo_j):
                if nid not in ids:
                    problemas.append(ProblemaEntrada(
                        "NODO_INEXISTENTE", "error", f"elementos.{e.id}",
                        f"el elemento referencia al nodo '{nid}' no registrado"))
        for m in self.muros:
            for nid in (m.nodo_a, m.nodo_b):
                if nid not in ids:
                    problemas.append(ProblemaEntrada(
                        "NODO_INEXISTENTE", "error", f"muros.{m.id}",
                        f"el muro referencia al nodo '{nid}' no registrado"))
        for r in self.restricciones:
            if r.nodo not in ids:
                problemas.append(ProblemaEntrada(
                    "NODO_INEXISTENTE", "error", f"restricciones.{r.nodo}",
                    "restriccion sobre nodo no registrado"))

        # elementos desconectados (mismo nodo i==j) - geometria degenerada
        for e in self.elementos:
            if e.nodo_i == e.nodo_j:
                problemas.append(ProblemaEntrada(
                    "ELEMENTO_DEGENERADO", "warning", f"elementos.{e.id}",
                    "elemento con los dos extremos en el mismo nodo"))

        # columnas sin continuidad vertical (sin datos de niveles aun -> warning)
        if self.niveles:
            col_niveles = [e.nivel for e in self.elementos if e.tipo == "columna"]
            if len(set(col_niveles)) != len(col_niveles):
                problemas.append(ProblemaEntrada(
                    "COLUMNA_SIN_CONTINUIDAD", "warning", "columnas",
                    "no se confirmo continuidad vertical (identidad nodo a nodo entre niveles)"))

        return problemas

    def reportar_pendientes(self) -> List[ProblemaEntrada]:
        """Datos estructurales ausentes que bloquean el analisis real."""
        pendientes = [
            ("propiedades_materiales", "materiales de concreto/aceros (fc, fy, modulos)"),
            ("secciones_completas", "secciones de vigas, columnas, muros y losas"),
            ("condiciones_apoyo", "condiciones de apoyo/vinculacion reales del Edificio I"),
            ("continuidad_vertical", "continuidad vertical confirmada de columnas/muros"),
            ("cargas_reales", "cargas muertas y sobrecargas de uso reales"),
            ("combinaciones", "combinaciones de carga"),
            ("definicion_sismica", "definicion sismica (espectro, masa sismica)"),
        ]
        return [
            ProblemaEntrada("ENTRADA_PENDIENTE", "warning", codigo_,
                            f"falta {descripcion} -> no se ejecuta analisis real")
            for codigo_, descripcion in pendientes
        ]

    def resumen(self) -> dict:
        return {
            "junta_global": self.junta_global,
            "n_nodos": len(self.nodos),
            "n_elementos": len(self.elementos),
            "n_muros": len(self.muros),
            "n_restricciones": len(self.restricciones),
            "n_cargas_registradas": len(self.cargas),
            "niveles": list(self.niveles),
        }