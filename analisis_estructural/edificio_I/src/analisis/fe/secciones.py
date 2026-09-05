"""Propiedades de seccion a partir de los rotulos documentados del plano.

Secciones documentadas (reales, se toman del candidato, no son hipotesis):
  V. b/h  -> viga: ancho b, peralte h -> A=b*h, I_strong=b*h^3/12, I_weak=h*b^3/12
  P. bxb  -> pilar cuadrado b x b
  V.S.I.  -> viga metalica (elemento metalico recogido como pendiente; hipotesis)
Los muros usan espesor x longitud (peralte = longitud del eje).

Nota: la nomenclatura V. 60/80 se interpreta b=0.60, h=0.80 (ancho x peralte).
"""

from __future__ import annotations

import re


def parse_viga(nombre: str):
    """Devuelve (b, h) en metros para una viga 'V. 60/80'."""
    m = re.search(r"(\d+)\s*[/xX]\s*(\d+)", nombre.replace(" ", ""))
    if not m:
        return None
    return int(m.group(1)) / 100.0, int(m.group(2)) / 100.0


def parse_columna(nombre: str):
    m = re.search(r"(\d+)\s*[/xX]\s*(\d+)", nombre.replace(" ", ""))
    if not m:
        return None
    return int(m.group(1)) / 100.0, int(m.group(2)) / 100.0


def seccion_viga(nombre: str):
    """Retorna (E, A, Iz, Iy, G, J) para OpenSees 'section Elastic' con E en kPa."""
    from .hipotesis import (MATERIAL_G40, MATERIAL_METALICO_E_MPA,
                            MATERIAL_METALICO_G_MPA, V_S_I_PROVISIONAL)
    n = nombre.strip().upper()
    if n.startswith("V.M") or "V.S.I." in n or "V.M.I." in n:
        # viga metalica PROVISIONAL (hipotesis). Etiqueta con dim (mm) o provisional.
        m = re.search(r"(\d+)\s*[/xX]\s*(\d+)", n.replace(" ", ""))
        if m:
            b, h = int(m.group(1)) / 1000.0, int(m.group(2)) / 1000.0
        else:
            b, h = V_S_I_PROVISIONAL[0] / 100.0, V_S_I_PROVISIONAL[1] / 100.0
        E = MATERIAL_METALICO_E_MPA * 1e3
        G = MATERIAL_METALICO_G_MPA * 1e3
        hipotesis = True
    else:
        bh = parse_viga(nombre)
        if not bh:
            return None
        b, h = bh
        E = MATERIAL_G40.E_mpa * 1e3
        G = MATERIAL_G40.G_mpa * 1e3
        hipotesis = False
    A = b * h
    Istrong = b * h ** 3 / 12.0   # flexion vertical (x-z) -> about local y -> Iy
    Iweak = h * b ** 3 / 12.0
    J = 0.5 * (Istrong + Iweak)
    return {"E": E, "A": A, "Iz": Iweak, "Iy": Istrong, "G": G, "J": J,
            "b": b, "h": h, "hipotesis": hipotesis}


def seccion_columna(nombre: str):
    from .hipotesis import (MATERIAL_G40, MATERIAL_METALICO_E_MPA,
                            MATERIAL_METALICO_G_MPA, P_M_I_PROVISIONAL_CM)
    n = nombre.strip().upper()
    if n.startswith("P.M") or n.startswith("V.M") or "M.I." in n:
        # pilar metalico (P.M./P.M.I./V.M.): seccion PROVISIONAL (hipotesis).
        # Etiquetas con dimension (mm), p.ej. "P.M. 300x300x20" -> 0.30 m.
        m = re.search(r"(\d+)\s*[xX]\s*(\d+)", n.replace(" ", ""))
        b = int(m.group(1)) / 1000.0 if m else P_M_I_PROVISIONAL_CM / 100.0
        E = MATERIAL_METALICO_E_MPA * 1e3
        G = MATERIAL_METALICO_G_MPA * 1e3
        hipotesis = True
    else:
        bh = parse_columna(nombre)
        if not bh:
            return None
        b, _ = bh
        E = MATERIAL_G40.E_mpa * 1e3
        G = MATERIAL_G40.G_mpa * 1e3
        hipotesis = False
    A = b * b
    I = b ** 4 / 12.0
    J = 2.25 * I
    return {"E": E, "A": A, "Iz": I, "Iy": I, "G": G, "J": J, "b": b,
            "hipotesis": hipotesis}


def seccion_muro(espesor: float, longitud: float):
    """Muro equivalente: seccion rectangular espesor x longitud."""
    from .hipotesis import MATERIAL_G40
    t, L = espesor, longitud
    A = t * L
    # peralte L => fuerte en su plano
    Istrong = t * L ** 3 / 12.0
    Iweak = L * t ** 3 / 12.0
    E = MATERIAL_G40.E_mpa * 1e3
    G = MATERIAL_G40.G_mpa * 1e3
    J = 0.5 * (Istrong + Iweak)
    return {"E": E, "A": A, "Iz": Iweak, "Iy": Istrong, "G": G, "J": J, "b": t, "h": L}
