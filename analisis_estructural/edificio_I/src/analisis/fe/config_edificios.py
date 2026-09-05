"""Configuracion por edificio del motor FE (laboratorio semana 2).

Separa lo que es especifico de cada edificio (identificadores de planos, cotas de
nivel, secciones, apoyos, vigas/muros de caso, rutas de datos) del motor comun.
El motor (`marco.py`, `secciones.py`, `geometria_fe.py`, `cargas_correlacionadas.py`,
`main_fe.py`) lee la configuracion ACTIVA (`activa()`), NO constantes literales.

Se conserva una configuracion `EDIFICIO_I` que reproduce EXACTAMENTE el
comportamiento actual (instantánea reproducible, verificado por hash). No se
introduce aqui ningún dato inventado del Edificio II: la config `EDIFICIO_II`
esta declarada como PENDIENTE (sin geometria, sin cotas, sin hipotesis propias),
a la espera de los JSON de la compañera. NO se reutilizan valores del I.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

# --------------------------------------------------------------------------- #
# Materiales (hipotesis de laboratorio, no utilizable para diseno)
# --------------------------------------------------------------------------- #
FC_MPA = 40.0
E_C_MPA = 4700.0 * (FC_MPA ** 0.5)          # ~29725.5 MPa
NU = 0.2
G_C_MPA = E_C_MPA / (2.0 * (1.0 + NU))
DENSIDAD_KGF_M3 = 2500.0
GRAV_KGF_TO_KN = 0.00980665

MATERIAL_METALICO_E_MPA = 200000.0          # Acero A36
MATERIAL_METALICO_G_MPA = 77200.0
P_M_I_PROVISIONAL_CM = 30.0
V_S_I_PROVISIONAL = (30.0, 60.0)


@dataclass
class ConfigEdificio:
    """Configuracion especifica de UN edificio para el motor FE comun."""

    id: str                                   # "I"
    nombre: str
    # orden y cotas de nivel (z en m). La clave es el codigo de nivel usado en IDs.
    niveles_orden: List[str]
    cotas_nivel: Dict[str, float]
    # nivel de base fija (apoyo de cimentacion), y nivel del basamento (sin diafragma)
    nivel_base: str
    nivel_basamento_sin_diafragma: str
    # geometria: nivel -> archivo candidato; y ruta de matrices de transformacion
    nivel_archivo: Dict[str, str]
    ruta_matrices_unity: str
    # carga superficial correlacionada (JSON)
    ruta_correlacion_cargas: str
    # hipotesis de cimentacion del sotano (si aplica)
    h_sotano_hipotesis_m: Optional[float] = None
    # secciones y materiales activos (por edificio)
    concreto_fc_mpa: float = FC_MPA
    material_metalico_E_mpa: float = MATERIAL_METALICO_E_MPA
    material_metalico_G_mpa: float = MATERIAL_METALICO_G_MPA
    p_m_i_provisional_cm: float = P_M_I_PROVISIONAL_CM
    v_s_i_provisional: Tuple[float, float] = V_S_I_PROVISIONAL
    # ---- especificos del caso real del edificio (datos de plano del caso) ----
    # muros de contencion del sotano que descienden a la cimentacion: id -> cfg
    muros_contencion_sotano: Dict[str, dict] = field(default_factory=dict)
    # id de la viga metalica de soporte interior (V.S.I.) del cielo del sotano
    vsi_beam_id: Optional[str] = None
    vsi_v: Optional[float] = None
    vsi_u: Tuple[float, float] | None = None
    vsi_muro_izq: Optional[str] = None
    vsi_muro_der: Optional[str] = None
    # viga perimetral excentrica (P1) -> columnas de anclaje (u: etiqueta)
    viga_excentrica_p1_id: Optional[str] = None
    viga_excentrica_p1_nivel: Optional[str] = None
    viga_excentrica_p1_v: Optional[float] = None
    viga_excentrica_p1_grid: Dict[float, str] = field(default_factory=dict)
    # portico del cielo del subterraneo (vigas excentricas a re-anclar)
    cp1s_frame_beams: List[str] = field(default_factory=list)
    cp1s_frame_col_u: Tuple[float, ...] = ()
    # bandera: geometria/hipotesis reales disponibles (I=True, II pendiente)
    geometria_disponible: bool = False

    # --- datos respaldados del Edificio II (geometria/areas/cargas por etapa) ---
    # Seccion de pilares respaldada (0.70x0.70, fuente RLE-PILAR/informes EII).
    # Unica seccion documentada en los niveles EII (sin rotaciones ni tamanos
    # distintos). Se usa para evaluar la geometria de columnas; el material/grado
    # de concreto para la solucion FE se declara aparte (hipotesis academica).
    seccion_columna: Optional[dict] = None
    # Peso propio de servicio respaldado (Contrato: 0.15 m x 2500 kg/m3).
    # NO incluye sobrecarga (SC) ni PM.ADIC: esos valores en el plano son LINEALES
    # (kg/m) de vigas/escaleras y su mapeo a la carga superficial de losa de CP2
    # no esta fijado; no se adoptan como carga real de losa sin fuente/permiso.
    pp_losa_kpa: Optional[float] = None
    # Datos de materiales declarados con su fuente (solo lectura). Distingue
    # hormigon, acero de armadura y acero de perfiles. `fuente` indica la lamina/
    # informe que respalda cada valor (o `hipotesis academia` + motivo si no hay
    # evidencia directa en la copia de planos disponible).
    materiales: Optional[dict] = None
    # Casos de carga declarados (G=PP+PM.ADIC priorizado; SC separada). Las cargas
    # superficiales, lineales y puntuales se conservan como entidades distintas y
    # se referencian por id en cada caso. `estado` distingue lo listo de lo pendiente.
    casos_carga: Optional[dict] = None
    # Condicion de base declarada (hipotesis academica si no hay cimentacion en los
    # JSON). No se prolongan columnas a la base sin registro (p. ej. A1 solo en CP4).
    condicion_base: Optional[dict] = None

    @property
    def cota_base(self) -> float:
        return self.cotas_nivel[self.nivel_base]

    @property
    def cota_cimentacion_sotano(self) -> Optional[float]:
        if self.h_sotano_hipotesis_m is None:
            return None
        return self.cotas_nivel[self.nivel_base] - self.h_sotano_hipotesis_m


# --------------------------------------------------------------------------- #
# EDIFICIO I (configuracion real; reproduce el comportamiento actual)
# --------------------------------------------------------------------------- #
EDIFICIO_I = ConfigEdificio(
    id="I",
    nombre="Edificio I (Fase 1)",
    niveles_orden=["CP1S", "P1", "P2", "P3", "P4"],
    cotas_nivel={"CP1S": -4.01, "P1": -0.05, "P2": 3.91, "P3": 7.87, "P4": 11.83},
    nivel_base="CP1S",
    nivel_basamento_sin_diafragma="CP1S",
    nivel_archivo={
        "CP1S": "edificio_I_cielo_piso_1_subterraneo_candidata_unity.json",
        "P1": "edificio_I_cielo_piso_1_borrador.json",
        "P2": "edificio_I_cielo_piso_2_borrador.json",
        "P3": "edificio_I_cielo_piso_3_borrador.json",
        "P4": "edificio_I_cielo_piso_4_candidata_unity.json",
    },
    ruta_matrices_unity="datos/candidatos/matrices_transformacion_unity.json",
    ruta_correlacion_cargas=(
        "datos/casos_analisis/correlacion_cargas_validada_5niveles.json"),
    h_sotano_hipotesis_m=3.0,
    muros_contencion_sotano={
        "M_EI_CP1S_001": {"u": -0.35, "e": 0.20},
        "M_EI_CP1S_002": {"u": 21.25, "e": 0.30},
    },
    vsi_beam_id="H_EI_CP1S_y2732_0.200-21.600",
    vsi_v=-10.8195,
    vsi_u=(-0.15, 21.25),
    vsi_muro_izq="M_EI_CP1S_001",
    vsi_muro_der="M_EI_CP1S_002",
    viga_excentrica_p1_id="GV_CP1_GE_este",
    viga_excentrica_p1_nivel="P1",
    viga_excentrica_p1_v=-0.2,
    viga_excentrica_p1_grid={30.0: "H", 45.0: "Ip"},
    cp1s_frame_beams=[
        "V_EI_CP1S_x0060_0.700-16.150",
        "H_EI_CP1S_y0601_0.700-10.000",
        "H_EI_CP1S_y1625_0.700-10.000",
    ],
    cp1s_frame_col_u=(0.0, 10.0),
    geometria_disponible=True,
)

# --------------------------------------------------------------------------- #
# EDIFICIO II (Fase 2)
#
# Respaldado por los JSON recibidos de la compañera (2026-09-03,
# `datos/entradas_recibidas/edificio_II/2026-09-03`) + consulta a `Datos
# Estructurales`. NO se rellenan valores del I.
#
# CONFIRMADO (respaldo documentado):
#   - Niveles y cotas: EII_CP1S=-4.01, EII_CP1=-0.05, EII_CP2=3.91, EII_CP3=7.87,
#     EII_CP4=11.83.
#   - Sistema comun INTERNO del II: los 5 niveles comparten la misma cuadrícula
#     local (A1=[0,0], B1=[7.5,0], C1=[17.5,0], D1=[27.5,0], A2=[0,8.9], ...; la
#     comprobacion A x 1/B x 1/A x 2 es identica). CP4 (DXF 102, origen DWG distinto)
#     ya esta normalizado a esta misma cuadrícula; NO se desplaza por el origen.
#     Esto permitiria ensamblaje interno del II usando la coordenada local como
#     marco propio del II (independiente de la colocacion junto al I por la junta).
#   - Pilares 0.70x0.70 (cajas RLE-PILAR; sumario_eii_cp1s.md; informe CP4) en los
#     niveles; sin rotacion ni tamanos distintos documentados. Solo CP4 incluye A1.
#   - PP losa de servicio = 0.15 m x 2500 kg/m3 = 3.68 kN/m2 (fuente 700.dxf+101.dxf).
#
# AUN PENDIENTE para habilitar la SOLUCION FE (etapas posteriores; no es un bloqueo
# global de la geometria/areas):
#   - Nivel base de cimentacion (apoyos) y esquema de conexion vertical entre
#     niveles del II (marco FE lo necesita).
#   - Material concreto/acerero del II: NO documentado en el proyecto EII; se usara
#     la hipotesis academica configurable (G40, E_c por ACI) marcada como tal.
#   - Cargas reales: solo PP confirmado; SC y PM.ADIC estan como LINEALES (kg/m) de
#     vigas/escaleras y su mapeo al paño de losa de CP2 no esta fijado (no se adoptan
#     como carga superficial real). El ensayo CP2 1 kPa es SOLO un ensayo unitario.
#   - `ruta_matrices_unity` propia de EII (para colocar junto al I en Unity): la
#     junta JD_EI_EII_10CM sigue `pendiente_json_edificio_II`; NO bloquea el
#     ensamblaje interno del II.
# Por eso `nivel_archivo` se deja vacio (el FE leeria candidatos Unity desde
# `datos/candidatos`; para EII el ensamblaje interno usa la localidad directamente,
# en preparacion de etapas) y `geometria_disponible=False`: no se corre la solucion
# FE con datos de soporte/conexion/materiales inventados.
# --------------------------------------------------------------------------- #
EDIFICIO_II = ConfigEdificio(
    id="II",
    nombre="Edificio II (Fase 2) -- geometria/areas respaldadas, solucion FE PENDIENTE",
    niveles_orden=["EII_CP1S", "EII_CP1", "EII_CP2", "EII_CP3", "EII_CP4"],
    cotas_nivel={"EII_CP1S": -4.01, "EII_CP1": -0.05,
                 "EII_CP2": 3.91, "EII_CP3": 7.87, "EII_CP4": 11.83},
    nivel_base="EII_CP1S",     # hipotesis academica explicita: queda PENDIENTE que la
                               # companera cataloge la cimentacion; se declara como base
                               # de ensamblaje el cielo mas bajo modelado (EII_CP1S, -4.01),
                               # NO como cimentacion real verificada.
    nivel_basamento_sin_diafragma="",
    nivel_archivo={},            # pendiente: candidatos consumibles por el FE
    ruta_matrices_unity="",      # pendiente: matrices local->comun/Unity de EII
    ruta_correlacion_cargas="",
    h_sotano_hipotesis_m=None,
    seccion_columna={
        "nombre": "0.70x0.70",
        "ancho": 0.70,
        "peralte": 0.70,
        "fuente": ("Cajas RLE-PILAR (CP1S notas y sumario_eii_cp1s.md 'cajas 0.70') "
                   "e informe_pendientes_EII_CP4.md '0.7x0.7'; unica seccion "
                   "documentada, sin rotaciones/tamanos distintos en EII. Los 5 "
                   "niveles tienen 28 losas de espesor 0.15 m (confirmado por losa "
                   "en los JSON; ascensor e=0.20 en CP1S/CP4)."),
    },
    pp_losa_kpa=3.68,
    materiales={
        "hormigon": {
            "grado": "G40 (f'c=40 MPa)",
            "fc_mpa": 40.0,
            "densidad_kgf_m3": 2500.0,
            "fuente": ("Grado: hipotesis academica del grupo (G40). La lamina "
                       "'calidad de hormigon' esta en el dibujo 2024_22-300..305/000 "
                       "(raster en nuestra copia; no OCR-eable) -> no se pudo "
                       "contrastar de forma independiente en nuestra copia de planos. "
                       "Densidad 2500 kg/m3: `2024_22-700.dxf` PLANTAS CARGAS "
                       "`PP. LOSA = e(m)x2500 Kg/m`; ETOG LT2_CAL_E.T.O.G: diseno ACI "
                       "318S-08, NCh433.Of96/DS117."),
            "E_c_mpa": round(4700.0 * (40.0 ** 0.5), 1),  # ~29725.5 via ACI 318
        },
        "acero_armadura": {
            "grado": "pendiente (hipotesis A630-42H / fy=420 MPa, no confirmada)",
            "fuente": ("Refuerzo documentado como campo ortogonal 0/90 en "
                       "`2024_22-201I/201S.dxf` (PLANTA ARMADURA INFERIOR/SUPERIOR), "
                       "pero el grado del acero (fy) no esta en texto de la copia; "
                       "pendiente de lamina o confirmacion."),
        },
        "acero_perfiles": {
            "grado": "No aplica a la estructura principal del II",
            "fuente": ("ETOG LT2_CAL_E.T.O.G: edificio de muros/columnas/vigas de "
                       "hormigon armado + zapatas aisladas/corridas; sin perfiles de "
                       "acero como elementos principales. Columnas = cajas RLE-PILAR "
                       "de concreto."),
        },
        "notas": {
            "densidad_conversion": "gam=2500 kg/m3; PP(kPa)=e(m)x2500x9.80665e-3: "
                                   "0.15x2500x0.00980665=3.6775 kPa (no 0.15x2500 suelto).",
        },
    },
    casos_carga={
        "G": {
            "descripcion": "permanente = PP losa (superficial) + PM.ADIC (lineal, pendiente de mapeo)",
            "prioridad": 1,
            "cargas": {
                "superficiales": ["Q_PP_LOSA"],   # 3.68 kPa, una sola vez por losa
                "lineales": ["Q_CC_*"],           # PM.ADIC (Kg/m) del 700; mapeo al panio pendiente
                "puntuales": [],
            },
            "estado": "parcial (solo PP superficial listo; PM.ADIC lineal por mapear)",
        },
        "SC": {
            "descripcion": "sobrecarga de uso; en el plano 700 es LINEAL (Kg/m) de vigas/escaleras",
            "prioridad": 2,
            "cargas": {"superficiales": [], "lineales": ["Q_SC_*"], "puntuales": []},
            "estado": "identificada por separado; no bloquea G; pendiente de mapeo al panio",
        },
    },
    condicion_base={
        "hipotesis": ("academica explicita: en el estado actual NO hay cimentacion ni "
                      "nivel_base catalogado en los JSON (solo 'zapatas aisladas bajo "
                      "pilares y corridas bajo muros' citado en ETOG). Para el ensamblaje "
                      "FE se fija base en EII_CP1S (cota -4.01), apoyando (encastre) los "
                      "pilares/muros que demuestran descender a ese nivel. Regla A1: la "
                      "columna A1 (0.70x0.70) existe SOLO en CP4 ([0,0]) y no desciende "
                      "a la base ni a los cielos inferiores -> NO se prolonga ni recibe "
                      "apoyo de base (sin camino de carga vertical verificado). NO se "
                      "anaden apoyos para eliminar singularidades numericamente."),
        "fuente": ("ETOG: sistema de fundaciones = zapatas (mencion textal). Sin "
                   "catalogo de fundaciones en los JSON recibidos."),
    },
    geometria_disponible=False,
)

_CONFIGS = {"I": EDIFICIO_I, "II": EDIFICIO_II}
_ACTIVA_ID = "I"


def configs() -> Dict[str, ConfigEdificio]:
    return _CONFIGS


def config_edificio(id_edificio: str) -> ConfigEdificio:
    if id_edificio not in _CONFIGS:
        raise KeyError("configuracion de edificio desconocida: %r" % id_edificio)
    return _CONFIGS[id_edificio]


def activa() -> ConfigEdificio:
    """Configuracion activa (por defecto Edificio I: reproduce el comportamiento actual)."""
    return _CONFIGS[_ACTIVA_ID]


def set_activa(id_edificio: str) -> None:
    global _ACTIVA_ID
    if id_edificio not in _CONFIGS:
        raise KeyError("configuracion de edificio desconocida: %r" % id_edificio)
    _ACTIVA_ID = id_edificio
