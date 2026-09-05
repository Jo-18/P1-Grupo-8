"""
Modelo de datos - interpretacion del esquema canonico de entrada.

Lee el formato definido en `datos/geometria/esquema_entrada_areas_tributarias_v1.json`
y lo transforma en estructuras planas usadas por el modulo de areas tributarias.

Conceptos clave (alineados con el esquema):
  - ``Panel`` (una losa) con su contorno como Shapely Polygon (exterior + aberturas).
  - ``Receptor`` (una viga o muro, de borde o interior) = candidato que recibe
    area tributaria. Los receptores de una losa se toman de la LISTA EXPLICITA
    ``apoyos_validos`` de la losa (o, de forma automática, de vigas/muros con
    ``recibe_losa=true`` que intersectan la losa).
  - Los bordes libres y los bordes de abertura NO son receptores; solo contorno.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import LineString, Point, Polygon

Punto = Tuple[float, float]


@dataclass
class CargaSuperficial:
    id: str
    valor: float  # kN/m2
    unidad: str = "kN/m2"
    notas: str = ""


@dataclass
class Receptor:
    """Una viga o muro que recibe area tributaria (segmento finito)."""
    id: str
    tipo: str               # viga | muro
    inicio: Punto
    fin: Punto
    seccion: str = ""
    longitud: float = 0.0
    # geometria como LineString (de bordes o interior)
    linea: Optional[LineString] = None

    def __post_init__(self):
        self.longitud = float(
            ((self.fin[0] - self.inicio[0]) ** 2
             + (self.fin[1] - self.inicio[1]) ** 2) ** 0.5
        )
        if self.linea is None:
            self.linea = LineString([self.inicio, self.fin])

    @property
    def elemento_soporte(self) -> str:
        # interfaz retrocompatible: el receptor ES el elemento soporte
        return self.id


@dataclass
class Abertura:
    id: str
    tipo: str = ""
    poligono: List[Punto] = field(default_factory=list)


@dataclass
class Panel:
    """Una losa del nivel, con sus receptores y aberturas."""
    id: str
    tipo: str = "losa"
    espesor: float = 0.0
    poligono: List[Punto] = field(default_factory=list)
    exclusivo: Polygon = None             # poligono exterior (Shapely)
    dominio: Polygon = None               # exterior con aberturas recortadas
    receptores: List[Receptor] = field(default_factory=list)
    aberturas: List[Abertura] = field(default_factory=list)
    tipo_transferencia: str = "bidireccional"
    apoyos_validos: List[str] = field(default_factory=list)
    carga_superficial: str = ""

    @property
    def area_bruta(self) -> float:
        return float(self.exclusivo.area) if self.exclusivo is not None else 0.0

    @property
    def area_aberturas(self) -> float:
        return sum(float(Polygon(a.poligono).area) for a in self.aberturas)

    @property
    def area_neta(self) -> float:
        return float(self.dominio.area) if self.dominio is not None else 0.0

    def receptores_validos(self) -> List[Receptor]:
        return list(self.receptores)


@dataclass
class ConfigCalculo:
    representacion_inicial: str = ""
    tamano_celda_inicial: Optional[float] = None
    tolerancia_geometrica: Optional[float] = None
    tolerancia_relativa_area: float = 1e-6
    tolerancia_relativa_carga: float = 1e-6
    generar_trazabilidad_celdas: bool = False


class ModeloGeometria:
    """Modelo completo leido del esquema canonico."""

    def __init__(self):
        self.version_formato: str = ""
        self.estado: str = ""
        self.proyecto: dict = {}
        self.sistema_coordenadas: dict = {}
        self.nivel: dict = {}
        self.config: ConfigCalculo = ConfigCalculo()
        self.panels: List[Panel] = []
        self.vigas: List[dict] = []
        self.muros: List[dict] = []
        self.bordes_libres: List[dict] = []
        self.cargas: Dict[str, CargaSuperficial] = {}
        self.resultados_esperados: dict = {}
        self.notas: List[str] = []

    @classmethod
    def from_dict(cls, data: dict) -> "ModeloGeometria":
        m = cls()
        m.version_formato = data.get("version_formato", "")
        m.estado = data.get("estado", "")
        m.proyecto = data.get("proyecto", {})
        m.sistema_coordenadas = data.get("sistema_coordenadas", {})
        m.nivel = data.get("nivel", {})

        cfg = data.get("configuracion_calculo", {})
        m.config = ConfigCalculo(
            representacion_inicial=cfg.get("representacion_inicial", ""),
            tamano_celda_inicial=cfg.get("tamano_celda_inicial"),
            tolerancia_geometrica=cfg.get("tolerancia_geometrica", 1e-6),
            tolerancia_relativa_area=cfg.get("tolerancia_relativa_area", 1e-6),
            tolerancia_relativa_carga=cfg.get("tolerancia_relativa_carga", 1e-6),
            generar_trazabilidad_celdas=cfg.get("generar_trazabilidad_celdas", False),
        )

        m.vigas = data.get("vigas", [])
        m.muros = data.get("muros", [])
        m.bordes_libres = data.get("bordes_libres", [])
        m.resultados_esperados = data.get("resultados_esperados_benchmark", {})
        m.notas = data.get("notas", [])

        for cid, c in data.get("cargas_superficiales", {}).items():
            m.cargas[cid] = CargaSuperficial(
                id=cid, valor=float(c["valor"]),
                unidad=c.get("unidad", "kN/m2"), notas=c.get("notas", ""),
            )

        aberturas_globales = {
            a["id"]: a for a in data.get("aberturas_globales", [])
        }

        for losa in data.get("losas", []):
            panel = cls._losa_a_panel(losa, aberturas_globales, m)
            cls._asignar_receptores(panel, m)
            m.panels.append(panel)
        return m

    # ------------------------------------------------------------------ #
    @staticmethod
    def _segmento_de(v) -> Tuple[Punto, Punto]:
        return (tuple(float(x) for x in v["inicio"]),
                tuple(float(x) for x in v["fin"]))

    @classmethod
    def _losa_a_panel(cls, losa: dict, aberturas_globales: dict, m) -> Panel:
        poligono = [tuple(float(v) for v in pt) for pt in losa["poligono_exterior"]]

        # aberturas
        aberturas: List[Abertura] = []
        holes = []
        for a_ref in losa.get("aberturas", []):
            if isinstance(a_ref, str):
                ab = aberturas_globales.get(a_ref)
                if ab is None:
                    raise ValueError(
                        f"Losa '{losa['id']}': abertura '{a_ref}' no definida")
                poly = [tuple(float(v) for v in pt) for pt in ab["poligono"]]
                aberturas.append(Abertura(id=ab["id"], tipo=ab.get("tipo", ""),
                                          poligono=poly))
            elif isinstance(a_ref, dict):
                poly = [tuple(float(v) for v in pt) for pt in a_ref["poligono"]]
                aberturas.append(Abertura(id=a_ref.get("id", ""),
                                          tipo=a_ref.get("tipo", ""),
                                          poligono=poly))
            holes.append(Polygon(poly))

        exterior = Polygon(poligono)
        if not exterior.is_valid:
            exterior = exterior.buffer(0)
        dominio = exterior
        for h in holes:
            dominio = dominio.difference(h)

        panel = Panel(
            id=losa["id"], tipo="losa", espesor=float(losa.get("espesor") or 0.0),
            poligono=poligono, exclusivo=exterior, dominio=dominio,
            aberturas=aberturas,
            tipo_transferencia=losa.get("tipo_transferencia", "por_definir"),
            apoyos_validos=list(losa.get("apoyos_validos", [])),
        )
        if "carga_superficial" in losa and losa["carga_superficial"] in m.cargas:
            panel.carga_superficial = losa["carga_superficial"]
        elif len(m.cargas) == 1:
            panel.carga_superficial = next(iter(m.cargas))
        return panel

    # ------------------------------------------------------------------ #
    @classmethod
    def _asignar_receptores(cls, panel: Panel, m) -> None:
        """Resuelve la lista de receptores (vigas/muros) de la losa."""
        # catalogo de viga/muro -> Receptor
        catalogo: Dict[str, Receptor] = {}
        for v in m.vigas:
            ini, fin = cls._segmento_de(v)
            catalogo[v["id"]] = Receptor(id=v["id"], tipo="viga",
                                         inicio=ini, fin=fin,
                                         seccion=str(v.get("seccion", {}).get("nombre", "")))
        for mu in m.muros:
            ini, fin = cls._segmento_de(mu["eje"])
            catalogo[mu["id"]] = Receptor(id=mu["id"], tipo="muro",
                                          inicio=ini, fin=fin)

        ids = list(panel.apoyos_validos)
        if not ids:
            # fallback: vigas/muros con recibe_losa que intersectan la losa
            for v in m.vigas:
                if v.get("recibe_losa", False) and v["id"] in catalogo:
                    r = catalogo[v["id"]]
                    if r.linea.intersects(panel.exclusivo) or r.linea.within(panel.exclusivo):
                        ids.append(v["id"])
            for mu in m.muros:
                if mu.get("recibe_losa", False) and mu["id"] in catalogo:
                    r = catalogo[mu["id"]]
                    if r.linea.intersects(panel.exclusivo) or r.linea.within(panel.exclusivo):
                        ids.append(mu["id"])

        # deduplicar manteniendo orden
        seen = set()
        receptores = []
        for rid in ids:
            if rid in seen or rid not in catalogo:
                continue
            seen.add(rid)
            receptores.append(catalogo[rid])

        if not receptores:
            raise ValueError(
                f"Losa '{panel.id}': no se resolvieron receptores (apoyos_validos "
                f"{panel.apoyos_validos}) ni vigas/muros recibe_losa que la intersecten.")
        panel.receptores = receptores
