"""Hipotesis de laboratorio explicitas y configurables para el modelo FE.

Toda hipotesis de laboratorio queda aqui, marcada `no_utilizable_para_diseno`.
Los datos documentados del edificio (geometria, secciones de vigas/columnas/muros,
espesores de losa, cotas de nivel) se toman de los candidatos congelados y NO se
sustituyen aqui.

La configuracion por edificio se lee de `config_edificios.py`. Por defecto la
configuracion ACTIVA es la del Edificio I (reproduce identicamente el
comportamiento actual). Este modulo expone esas constantes por nombre para
compatibilidad con el resto del motor y con los tests; NO contienen literales de
un edificio concreto.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config_edificios as CFG

# --------------------------------------------------------------------------- #
# Materiales (hipotesis de laboratorio: concreto "G40", sin aplicar a diseno)
# --------------------------------------------------------------------------- #
# G40 = concreto de 400 kgf/cm2 = 40 MPa (nomenclatura usada en el proyecto).
# E_c segun ACI 318-19 Eq. 19.2.2.1: E_c = 4700*sqrt(f'c) [MPa] con f'c en MPa.
FC_MPA = CFG.FC_MPA
E_C_MPA = CFG.E_C_MPA          # ~ 29725.5 MPa ~ 29.73 GPa
NU = CFG.NU
G_C_MPA = CFG.G_C_MPA          # modulo cortante
DENSIDAD_KGF_M3 = CFG.DENSIDAD_KGF_M3
GRAV_KGF_TO_KN = CFG.GRAV_KGF_TO_KN


@dataclass
class MaterialConcreto:
    """Material hipotetico de laboratorio (no utilizable para diseno)."""
    nombre: str
    fc_mpa: float
    E_mpa: float
    nu: float
    G_mpa: float
    densidad_kgf_m3: float
    fuente: str
    no_utilizable_para_diseno: bool = True


MATERIAL_G40 = MaterialConcreto(
    nombre="Hormigon G40",
    fc_mpa=FC_MPA,
    E_mpa=E_C_MPA,
    nu=NU,
    G_mpa=G_C_MPA,
    densidad_kgf_m3=DENSIDAD_KGF_M3,
    fuente=("Hipotesis de laboratorio: f'c=40 MPa (G40). "
            "E_c=4700*sqrt(f'c)= %.1f MPa segun ACI 318-19 eq. 19.2.2.1. "
            "No es dato del plano; no utilizable para diseno." % E_C_MPA),
)

# --------------------------------------------------------------------------- #
# Elementos metalicos (P.M.I. / V.S.I.): seccion PROVISIONAL (hipotesis)
#
# No se dispone del perfil metalico real del plano (faltante concreto a consultar
# en DXF 101/102/103, pendiente). Para que la primera ejecucion gravitacional sea
# estable se asigna PROVISIONALMENTE una seccion metalica cuadrada de 30 cm (P.M.I.)
# y una viga metalica 30x60 (V.S.I.) con material Acero A36 (E=200 GPa, G=77.2 GPa).
# Esta seccion es UNA HIPOTESIS DE LABORATORIO que debe sustituirse por el perfil
# real del DXF. NO ES GEOMETRIA DEL PLANO ni utilizable para diseno.
# --------------------------------------------------------------------------- #
MATERIAL_METALICO_E_MPA = CFG.MATERIAL_METALICO_E_MPA   # Acero A36, E ~ 200 GPa
MATERIAL_METALICO_G_MPA = CFG.MATERIAL_METALICO_G_MPA
P_M_I_PROVISIONAL_CM = CFG.P_M_I_PROVISIONAL_CM
V_S_I_PROVISIONAL = CFG.V_S_I_PROVISIONAL


# --------------------------------------------------------------------------- #
# Secciones documentadas en el plano (no son hipotesis: se toman del candidato)
# --------------------------------------------------------------------------- #
def _seccion_viga(nombre: str):
    import re
    m = re.search(r"(\d+)\s*[/xX]\s*(\d+)", nombre.replace(" ", ""))
    if not m:
        raise ValueError("seccion de viga no parseable: %r" % nombre)
    a, b2 = int(m.group(1)), int(m.group(2))
    return a / 100.0, b2 / 100.0


def _seccion_columna(nombre: str):
    import re
    m = re.search(r"(\d+)\s*[/xX]\s*(\d+)", nombre.replace(" ", ""))
    if not m:
        raise ValueError("seccion de columna no parseable: %r" % nombre)
    a, b2 = int(m.group(1)), int(m.group(2))
    return a / 100.0, b2 / 100.0


# --------------------------------------------------------------------------- #
# Apoyos / cimentacion (hipotesis de laboratorio): nivel de base del edificio activo
# --------------------------------------------------------------------------- #
BASE_FIJA_NIVEL = CFG.activa().nivel_base
BASE_FIJA_Z = None          # se fija en main con la cota del nivel base
APOYO_BASE = "fijo_completo_6dof"


# --------------------------------------------------------------------------- #
# Muros de contencion del sotano y soporte de la V.S.I. (caso Edificio I)
# Se leen de la configuracion activa; en Edificio II quedan vacios (pendiente).
# --------------------------------------------------------------------------- #
_ACT = CFG.activa()
V_S_I_CP1S_H_Y2732 = _ACT.vsi_beam_id
V_S_I_H_Y2732_V = _ACT.vsi_v
V_S_I_H_Y2732_U = _ACT.vsi_u
MUROS_CONTENCION_SOTANO = _ACT.muros_contencion_sotano

# --------------------------------------------------------------------------- #
# Torre: cotas de nivel documentadas (del edificio activo)
# --------------------------------------------------------------------------- #
COTAS_NIVEL_M = dict(_ACT.cotas_nivel)


# --------------------------------------------------------------------------- #
# Cimentacion del sotano (hipotesis academica configurable)
# --------------------------------------------------------------------------- #
H_SOTANO_HIPOTESIS_M = _ACT.h_sotano_hipotesis_m
COTA_CIMENTACION_SOTANO_M = _ACT.cota_cimentacion_sotano


def niveles_ordenados():
    """Niveles en orden descendente a ascendente? ; devuelve el orden de la config."""
    return list(_ACT.niveles_orden)


def altura_entrepiso() -> float:
    c = COTAS_NIVEL_M
    o = niveles_ordenados()
    diffs = unique_diffs([c[o[i + 1]] - c[o[i]] for i in range(len(o) - 1)])
    return diffs[0] if len(diffs) == 1 else None


def unique_diffs(vals):
    out = []
    for v in vals:
        if not any(abs(v - x) < 1e-9 for x in out):
            out.append(round(v, 6))
    return out
