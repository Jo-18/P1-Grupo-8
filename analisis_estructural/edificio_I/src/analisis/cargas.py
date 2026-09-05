"""
Capa independiente de conversion de cargas para el Edificio I.

Entrada: regiones tributarias por panel (ResultadoPanel) y carga superficial q.
Salida:
  - aporte de cada losa (area_tributaria por receptor x q);
  - carga total por receptor (agregando sus contribuciones de todas las losas);
  - contribuciones de receptores compartidos (un receptor con su lista de losas);
  - carga sin asignar (debe ser 0 en el motor de produccion por renormalizacion);
  - verificacion de conservacion:  sum(cargas aplicadas) == sum(area_neta_i) * q.

Conservacion garantizada: cada area se asigna una unica vez en el motor; aqui solo se
agrega y no se renormariza en silencio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from areas_tributarias.tributacion import ResultadoPanel

# Categorias de carga superficial registrables (por ahora SIN valores reales).
# Solo se registran: no se les asigna ningun dato para que un analisis de diseno
# pueda ejecutarse. El unico valor permitido para pruebas es q=1.0 kN/m2 (ensayo).
CATEGORIAS_CARGA_REGISTRABLES = {
    "peso_propio",
    "carga_muerta_adicional",
    "sobrecarga_uso",
    "nieve",
    "otra_superficial",
}

# Metodo de calculo del ancho/carga tributaria.
METODO_CAMINO_MINIMO = "camino_minimo_distancia"
METODO_VISIBILIDAD = "visibilidad_camino"

# Condicion de normalizacion del resultado.
CONDICION_CRUDA = "cruda_no_renormalizada"
CONDICION_RENORMALIZADA = "renormalizada"


@dataclass(frozen=True)
class CategoriaCargaRegistrada:
    """Registro de una categoria de carga (trazabilidad), sin valor asignado."""
    categoria: str
    edificio: str
    nivel: str
    caso_carga: str
    asignada: bool = False
    nota: str = "sin_valor_hasta_decision_de_diseno"


@dataclass(frozen=True)
class CombinacionRegistrada:
    """Registro de una combinacion de carga (trazabilidad), sin factores."""
    id_combinacion: str
    categorias_incluidas: Tuple[str, ...]
    factores: Tuple[Optional[float], ...] = ()
    asignada: bool = False
    nota: str = "sin_factores_hasta_decision_de_diseno"


@dataclass(frozen=True)
class AporteLineal:
    """Traza una losa -> receptor con su carga lineal equivalente y origenes."""
    edificio: str
    nivel: str
    losa: str
    caso_carga: str
    receptor: str
    area_tributaria_m2: float
    carga_superficial_kN_m2: float
    carga_lineal_kN_m: float
    ancho_tributario_m: float
    longitud_receptor_m: float
    metodo_calculo: str
    condicion: str
    carga_puntual_equivalente_kN: float
    es_ensayo: bool
    notas: str = ""


@dataclass
class AporteLosaReceptor:
    panel_id: str
    receptor_id: str
    area_tributaria_m2: float
    carga_kN: float


@dataclass
class CargaReceptor:
    receptor_id: str
    carga_total_kN: float
    area_tributaria_total_m2: float
    aportes: List[AporteLosaReceptor] = field(default_factory=list)

    @property
    def losas_aportantes(self) -> List[str]:
        return sorted({a.panel_id for a in self.aportes})


@dataclass
class InformeCargas:
    q_kN_m2: float
    area_neta_total_m2: float
    carga_total_aplicada_kN: float
    carga_total_asignada_kN: float
    carga_sin_asignar_kN: float
    error_rel_conservacion: float
    receptores: Dict[str, CargaReceptor] = field(default_factory=dict)

    def tabla(self) -> List[dict]:
        filas = []
        for rid, r in sorted(self.receptores.items()):
            filas.append({
                "receptor": rid,
                "carga_total_kN": round(r.carga_total_kN, 6),
                "area_tributaria_m2": round(r.area_tributaria_total_m2, 6),
                "losas_aportantes": ";".join(r.losas_aportantes),
            })
        return filas

    def tabla_aportes(self) -> List[dict]:
        filas = []
        for rid, r in sorted(self.receptores.items()):
            for a in r.aportes:
                filas.append({
                    "receptor": rid,
                    "losa": a.panel_id,
                    "area_tributaria_m2": round(a.area_tributaria_m2, 6),
                    "carga_kN": round(a.carga_kN, 6),
                })
        return filas


def convertir_cargas(paneles_result: List[ResultadoPanel], q: float) -> InformeCargas:
    """Convierte areas tributarias en cargas y agrega por receptor sin duplicar area."""
    area_neta_total = 0.0
    carga_aplicada = 0.0
    receptores: Dict[str, CargaReceptor] = {}
    carga_sin_asignar = 0.0

    for pr in paneles_result:
        area_neta = pr.area_neta
        area_neta_total += area_neta
        carga_aplicada += area_neta * q
        # area asignada del panel = suma de regiones (produccion la renormaliza)
        asignado = pr.area_total
        carga_sin_asignar += (area_neta - asignado) * q
        for r in pr.regiones:
            area_r = r.area
            cr = receptores.setdefault(
                r.receptor.id, CargaReceptor(receptor_id=r.receptor.id,
                                              carga_total_kN=0.0,
                                              area_tributaria_total_m2=0.0))
            cr.area_tributaria_total_m2 += area_r
            cr.carga_total_kN += area_r * q
            cr.aportes.append(
                AporteLosaReceptor(panel_id=pr.panel.id,
                                   receptor_id=r.receptor.id,
                                   area_tributaria_m2=area_r,
                                   carga_kN=area_r * q)
            )

    carga_total_asignada = sum(r.carga_total_kN for r in receptores.values())
    error = (abs(carga_total_asignada - carga_aplicada) / carga_aplicada
             if carga_aplicada else 0.0)

    return InformeCargas(
        q_kN_m2=q,
        area_neta_total_m2=area_neta_total,
        carga_total_aplicada_kN=carga_aplicada,
        carga_total_asignada_kN=carga_total_asignada,
        carga_sin_asignar_kN=carga_sin_asignar,
        error_rel_conservacion=error,
        receptores=receptores,
    )


class RegistroCargas:
    """Registra categorias de carga y combinaciones SIN asignar valores reales.

    Permite dejar preparada la trazabilidad de peso propio, carga muerta adicional,
    sobrecarga, nieve y otras cargas superficiales, asi como las combinaciones. Ninguno
    asigna valores (asignada=False); un analisis de diseno se detiene si intenta usarlos.
    """

    def __init__(self) -> None:
        self.categorias: Dict[str, CategoriaCargaRegistrada] = {}
        self.combinaciones: Dict[str, CombinacionRegistrada] = {}

    def registrar_categoria(self, categoria: str, edificio: str = "Edificio I",
                            nivel: str = "", caso_carga: str = "default") -> None:
        if categoria not in CATEGORIAS_CARGA_REGISTRABLES:
            raise ValueError(f"categoria '{categoria}' no registrable")
        clave = (edificio, str(nivel), caso_carga, categoria)
        self.categorias["|".join(clave)] = CategoriaCargaRegistrada(
            categoria=categoria, edificio=edificio, nivel=nivel, caso_carga=caso_carga)

    def registrar_combinacion(self, id_combinacion: str,
                              categorias: Tuple[str, ...],
                              factores: Tuple[Optional[float], ...] = ()) -> None:
        self.combinaciones[id_combinacion] = CombinacionRegistrada(
            id_combinacion=id_combinacion, categorias_incluidas=tuple(categorias),
            factores=tuple(factores))

    def todas_sin_valor(self) -> bool:
        return all(not c.asignada for c in self.categorias.values()) and \
            all(not c.asignada for c in self.combinaciones.values())

    def bloquear_si_por_definir(self) -> List[str]:
        """Devuelve los ids de categorias/combinaciones que siguen ``por_definir``
        (sin valor/factores). Un analisis de DISENO debe detenerse si los necesita."""
        pendientes = []
        for k, c in self.categorias.items():
            if not c.asignada:
                pendientes.append(f"categoria:{c.edificio}|{c.nivel}|{c.caso_carga}|{c.categoria}")
        for k, c in self.combinaciones.items():
            if not c.asignada or any(f is None for f in c.factores):
                pendientes.append(f"combinacion:{c.id_combinacion}")
        return pendientes


def _flottar(v, nombre: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{nombre}' no es numerico: {v!r}") from exc


def cargas_lineales_receptor(
    paneles_result: List[ResultadoPanel],
    q: float,
    edificio: str = "Edificio I",
    nivel: str = "",
    caso_carga: str = "ensayo_1kpa",
    metodo_calculo: str = METODO_CAMINO_MINIMO,
    condicion: str = CONDICION_RENORMALIZADA,
    es_ensayo: bool = True,
) -> List[AporteLineal]:
    """Transforma cargas superficiales en cargas lineales sobre cada receptor.

    Formula:  carga_lineal_receptor = carga_superficial x ancho_tributario
    con       ancho_tributario = area_tributaria / longitud_receptor.

    Conserva trazabilidad por edificio, nivel, losa, caso de carga, receptor, area
    tributaria, carga superficial, carga lineal equivalente, ancho tributario, metodo de
    calculo y condicion (cruda/renormalizada). `area_tributaria` es la ya asignada por el
    motor (renormalizada o cruda segun `condicion`).
    """
    q = _flottar(q, "q")
    aportes: List[AporteLineal] = []
    for pr in paneles_result:
        for r in pr.regiones:
            area_r = float(r.area)
            L = float(r.receptor.longitud) if r.receptor.longitud else 0.0
            ancho = area_r / L if L > 0 else 0.0
            w_lineal = q * ancho
            aportes.append(AporteLineal(
                edificio=edificio,
                nivel=nivel,
                losa=pr.panel.id,
                caso_carga=caso_carga,
                receptor=r.receptor.id,
                area_tributaria_m2=area_r,
                carga_superficial_kN_m2=q,
                carga_lineal_kN_m=w_lineal,
                ancho_tributario_m=ancho,
                longitud_receptor_m=L,
                metodo_calculo=metodo_calculo,
                condicion=condicion,
                carga_puntual_equivalente_kN=area_r * q,
                es_ensayo=es_ensayo,
            ))
    return aportes


def resumen_aportes_lineales(aportes: List[AporteLineal]) -> dict:
    """Agrega por receptor para reporte: ancho y carga lineal total."""
    por_receptor: Dict[str, dict] = {}
    for a in aportes:
        r = por_receptor.setdefault(a.receptor, {
            "receptor": a.receptor,
            "losas": set(),
            "area_tributaria_total_m2": 0.0,
            "carga_lineal_eq_kN_m": 0.0,
            "carga_puntual_equiv_kN": 0.0,
        })
        r["losas"].add(a.losa)
        r["area_tributaria_total_m2"] += a.area_tributaria_m2
        r["carga_lineal_eq_kN_m"] += a.carga_lineal_kN_m
        r["carga_puntual_equiv_kN"] += a.carga_puntual_equivalente_kN
    for r in por_receptor.values():
        r["losas"] = sorted(r["losas"])
        for k in ("area_tributaria_total_m2", "carga_lineal_eq_kN_m", "carga_puntual_equiv_kN"):
            r[k] = round(r[k], 6)
    return {"aportes": len(aportes),
            "receptores": sorted(por_receptor.values(), key=lambda x: x["receptor"])}