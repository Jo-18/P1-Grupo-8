"""Combinaciones normativas NCh3171 del perfil MODELO_FE_COMPLETO_FUNCIONAL.

Cada combinacion se materializa como una CORRIDA EXPLICITA de OpenSees: se ensambla
el patron de cargas nodales combinado (factores NCh3171 sobre los flujos planos de
G, Q, EX y EY) y se resuelve de nuevo el modelo; NO se superpone post-proceso.

Receta exacta de entrega (9 combinaciones; sin variantes 100%/30% entre las
normativas; la antigua COMBINADA arbitraria queda eliminada por completo):

  U1_GQ     = 1.2*G + 1.6*Q
  U2_EX_POS = 1.2*G + Q + 1.4*EX
  U2_EX_NEG = 1.2*G + Q - 1.4*EX
  U3_EY_POS = 1.2*G + Q + 1.4*EY
  U3_EY_NEG = 1.2*G + Q - 1.4*EY
  U4_EX_POS = 0.9*G + 1.4*EX
  U4_EX_NEG = 0.9*G - 1.4*EX
  U4_EY_POS = 0.9*G + 1.4*EY
  U4_EY_NEG = 0.9*G - 1.4*EY
"""

from __future__ import annotations

NOMBRE_NORMA = "NCh3171.Of2008 (ed. 2021)"

COMBINACIONES_NCH3171 = [
    {"id": "U1_GQ", "expresion": "1.2*G + 1.6*Q",
     "factores": {"G": 1.2, "Q": 1.6, "EX": 0.0, "EY": 0.0},
     "grupo": "gravedad", "direccion": None,
     "aplica": "permanente + sobrecarga, sin sismo"},
    {"id": "U2_EX_POS", "expresion": "1.2*G + Q + 1.4*EX",
     "factores": {"G": 1.2, "Q": 1.0, "EX": 1.4, "EY": 0.0},
     "grupo": "sismico", "direccion": "X",
     "aplica": "sismo X en sentido positivo"},
    {"id": "U2_EX_NEG", "expresion": "1.2*G + Q - 1.4*EX",
     "factores": {"G": 1.2, "Q": 1.0, "EX": -1.4, "EY": 0.0},
     "grupo": "sismico", "direccion": "X",
     "aplica": "sismo X en sentido negativo"},
    {"id": "U3_EY_POS", "expresion": "1.2*G + Q + 1.4*EY",
     "factores": {"G": 1.2, "Q": 1.0, "EX": 0.0, "EY": 1.4},
     "grupo": "sismico", "direccion": "Y",
     "aplica": "sismo Y en sentido positivo"},
    {"id": "U3_EY_NEG", "expresion": "1.2*G + Q - 1.4*EY",
     "factores": {"G": 1.2, "Q": 1.0, "EX": 0.0, "EY": -1.4},
     "grupo": "sismico", "direccion": "Y",
     "aplica": "sismo Y en sentido negativo"},
    {"id": "U4_EX_POS", "expresion": "0.9*G + 1.4*EX",
     "factores": {"G": 0.9, "Q": 0.0, "EX": 1.4, "EY": 0.0},
     "grupo": "sismico", "direccion": "X",
     "aplica": "descompresion/volteo con sismo X positivo"},
    {"id": "U4_EX_NEG", "expresion": "0.9*G - 1.4*EX",
     "factores": {"G": 0.9, "Q": 0.0, "EX": -1.4, "EY": 0.0},
     "grupo": "sismico", "direccion": "X",
     "aplica": "descompresion/volteo con sismo X negativo"},
    {"id": "U4_EY_POS", "expresion": "0.9*G + 1.4*EY",
     "factores": {"G": 0.9, "Q": 0.0, "EX": 0.0, "EY": 1.4},
     "grupo": "sismico", "direccion": "Y",
     "aplica": "descompresion/volteo con sismo Y positivo"},
    {"id": "U4_EY_NEG", "expresion": "0.9*G - 1.4*EY",
     "factores": {"G": 0.9, "Q": 0.0, "EX": 0.0, "EY": -1.4},
     "grupo": "sismico", "direccion": "Y",
     "aplica": "descompresion/volteo con sismo Y negativo"},
]

IDS_COMBINACIONES = [c["id"] for c in COMBINACIONES_NCH3171]

NOTA_100_30 = (
    "Las variantes ortogonales combinadas 100%/30% (EX + 0.3*EY o 0.3*EX + EY) NO "
    "son combinaciones normativas de esta entrega: por decision de entrega no se "
    "mezclan con las requeridas ni entran en la envolvente. Si se estudiaran, se "
    "rotularian NO_NORMATIVA_PARA_ESTA_ENTREGA, sin mezclarlas con las normativas "
    "ni con la envolvente.")


def ensamblar_plano(combo: dict, G: dict, Q: dict, EX: dict,
                    EY: dict) -> dict:
    """-> flat {tag: [6]} = suma de factor*vector sobre los casos con factor != 0.

    Fuentes: dicts planos {int tag: [6 fuerzas nodales]}. Cualquier tag ausente en
    una fuente se ignora (no aplica) y el resto conserva sus 6 componentes."""
    ff = combo["factores"]
    out: dict = {}
    for nombre, fuente in (("G", G), ("Q", Q), ("EX", EX), ("EY", EY)):
        factor = ff[nombre]
        if not factor:
            continue
        for t, v in fuente.items():
            cur = out.setdefault(int(t), [0.0] * 6)
            for i in range(6):
                cur[i] += factor * v[i]
    return out


def resultantes(flat: dict) -> dict:
    """Resultante del patron combinado aplicado (suma de las 6 componentes)."""
    m = [0.0] * 6
    for v in flat.values():
        for i in range(6):
            m[i] += v[i]
    return {"Vx": m[0], "Vy": m[1], "Pz": -m[2], "Mx": m[3], "My": m[4], "Mz": m[5]}