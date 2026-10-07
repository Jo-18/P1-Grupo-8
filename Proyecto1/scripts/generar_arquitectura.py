"""Genera la capa de arquitectura del viewer (SOLO VISUAL).

Escribe edificio_G8/Assets/Resources/arquitectura_visual.json con cajas y prismas que
Unity dibuja como mallas sin collider (StructureViewer.Arquitectura.cs). Nada de esto entra
al modelo de OpenSees: no se modifican estructura_completo_unity.json, parametros, cargas ni
resultados, y los elementos no se pueden seleccionar.

Contenido, a partir de las fotos del edificio:
  - terreno en dos niveles: la entrada principal esta en el extremo este, a la altura del
    2.o piso (z = 3,96), en una plaza con taludes de pasto; la planta baja queda enterrada
    por ese lado. La cafeteria y sus terrazas (sur y norte) estan un piso mas abajo (z = 0);
  - fachada sur de vidrio con las dos cajas en voladizo (la inferior es la sala de Metodos
    Computacionales); fachada norte con ventanas de marco blanco, aletas naranjas y bandas
    blancas de piso (igual en los dos edificios); extremo este con la caja naranja del piso 4
    y las puertas de la entrada principal;
  - escalera naranja de la fachada sur: descanso L99 (piso 4) -> tramo sobre la sala ->
    terraza L100/L101 bajo la caja superior -> tramo que llega a la plataforma del 2.o piso
    (nivel de la plaza). Desde la plataforma, la escalinata ancha baja hacia el oeste hasta la
    terraza de la cafeteria;
  - lado norte: escalera de dos tramos con descanso a media altura, desde la plaza de la
    entrada hasta la terraza norte (con mesas y quitasoles);
  - sala de Metodos Computacionales: 6 mesas cuadradas altas con taburetes y una pantalla;
  - cafeteria: solo el rectangulo de la planta baja bajo la sala (x 0..7,51), de fachada a
    fachada, con 18 mesas y una barra.

Coordenadas del modelo: x a lo largo del edificio (este +), y hacia el norte, z hacia arriba (m).

Uso:  python -X utf8 Proyecto1/scripts/generar_arquitectura.py [--preview carpeta]
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SALIDA = ROOT / "edificio_G8" / "Assets" / "Resources" / "arquitectura_visual.json"
MODELO = ROOT / "edificio_G8" / "Assets" / "Resources" / "estructura_p1l4_unity.json"

MATERIALES = {
    "vidrio":        (0.55, 0.74, 0.86, 0.22),
    "vidrio_oscuro": (0.24, 0.32, 0.42, 0.80),
    "montante":      (0.16, 0.18, 0.20, 1.0),
    "banda":         (0.93, 0.91, 0.86, 1.0),
    "terracota":     (0.84, 0.43, 0.28, 1.0),
    "marco_blanco":  (0.96, 0.96, 0.94, 1.0),
    "naranja":       (0.92, 0.38, 0.14, 1.0),
    "hormigon":      (0.70, 0.70, 0.68, 1.0),
    "pavimento":     (0.86, 0.82, 0.73, 1.0),
    "piso_interior": (0.78, 0.77, 0.74, 1.0),
    "mesa_blanca":   (0.95, 0.95, 0.93, 1.0),
    "metal_oscuro":  (0.18, 0.18, 0.20, 1.0),
    "turquesa":      (0.18, 0.60, 0.64, 1.0),
    "madera":        (0.63, 0.46, 0.31, 1.0),
    "piso_madera":   (0.80, 0.71, 0.57, 1.0),
    "quitasol":      (0.90, 0.90, 0.88, 1.0),
    "pantalla":      (0.05, 0.05, 0.07, 1.0),
    "equipos":       (0.62, 0.64, 0.66, 1.0),
    "contencion":    (0.80, 0.77, 0.70, 1.0),
    "talud":         (0.30, 0.46, 0.20, 1.0),
}

# ---------------------------------------------------------------- geometria de referencia
PISOS = [0.0, 3.96, 7.92, 11.88, 15.84]          # niveles (z) de piso de los 4 pisos sobre terreno
NIVEL_TERRENO = -0.03                              # pasto en la vista arquitectonica (nivel inferior)
Z_INF = 0.0                                        # terrazas de la cafeteria (1.er piso)
Z_SUP = 3.96                                       # plaza de la entrada y plataforma (2.o piso)

# fachadas (planos fuera de columnas, muros y bordes de losa del modelo)
E1_SUR, E1_NORTE, E1_ESTE, E1_ESTE_TOP = -7.70, 10.02, 35.50, 41.30
E2_SUR, E2_NORTE, E2_OESTE = -8.79, 10.20, -42.02
JUNTA = -10.0
CAJA_SUR = -11.55                                  # cara sur de las cajas en voladizo (columnas en y = -11,37)
CAJA_INF = (-0.25, 7.76, 3.96, 7.92)               # sala: x0, x1, z0, z1
CAJA_SUP = (9.75, 20.25, 11.88, 15.84)
CAJA_ESTE_SUR = -8.73                              # caja terracota del piso 4 (losas VOL04/VOL07 hasta y = -8,58)
PASO_VENTANAS = 2.5

# sala de Metodos Computacionales (voladizo inferior + crujia interior, losas L95, L22 y L23)
SALA = dict(x0=0.0, x1=7.51, y0=-11.37, y1=0.0, z=3.96)
# cafeteria: rectangulo de la planta baja bajo la sala, mismo ancho (x 0..7,51), de fachada a fachada
CAFE = dict(x0=0.35, x1=7.51, y0=-6.90, y1=8.55, z=0.0)

# entorno en dos niveles (ver fotos): plaza alta al este y plataforma al sur del extremo este
PLAZA_ESTE = (E1_ESTE, 50.0, -16.5, 18.0)          # x0, x1, y0, y1: relleno hasta Z_SUP
TALUD = 8.0                                        # ancho de los taludes de pasto (este y norte de la plaza)
PLATAFORMA = (28.12, E1_ESTE, -16.5, E1_SUR)       # losa sobre pilares a Z_SUP, abierta debajo
ESCALINATA = dict(x_alto=28.12, y0=-16.25, y1=-10.60)        # baja hacia el oeste hasta Z_INF
ESC_NORTE = dict(x_alto=E1_ESTE, y0=10.44, y1=12.44)         # dos tramos + descanso hacia el oeste
PUERTA_ESTE = (-1.30, 1.10)                        # y0, y1 de la entrada principal (fachada este, 2.o piso)
PUERTA_SUR = (31.30, 33.10)                        # x0, x1 de la puerta a la plataforma (fachada sur, 2.o piso)
SITIO_OESTE, SITIO_SUR, SITIO_NORTE = -45.5, -18.0, 18.0     # bordes de los pavimentos del nivel inferior

# escalera naranja
ESC_Y = (-9.70, -8.20)                             # ancho libre de los tramos angostos
ESC_PARAPETO = 0.12


class Capa:
    def __init__(self):
        self.grupos = {}

    def caja(self, capa, piso, mat, x0, x1, y0, y1, z0, z1):
        g = self._g(capa, piso, mat)
        g["cajas"] += [min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1)]

    def hexa(self, capa, piso, mat, esquinas):
        assert len(esquinas) == 8
        g = self._g(capa, piso, mat)
        for p in esquinas:
            g["hexas"] += [round(float(c), 4) for c in p]

    def _g(self, capa, piso, mat):
        k = (capa, piso, mat)
        if k not in self.grupos:
            self.grupos[k] = {"nombre": f"Arq_{capa}_{piso or 'todos'}_{mat}", "capa": capa, "piso": piso,
                              "material": mat, "cajas": [], "hexas": []}
        return self.grupos[k]


A = Capa()


# ---------------------------------------------------------------- utilidades
def rampa_x(capa, piso, mat, xa, xb, y0, y1, za0, za1, zb0, zb1):
    """Prisma inclinado a lo largo de x: en x = xa va de za0 a za1 y en x = xb de zb0 a zb1."""
    A.hexa(capa, piso, mat, [(xa, y0, za0), (xb, y0, zb0), (xb, y1, zb0), (xa, y1, za0),
                             (xa, y0, za1), (xb, y0, zb1), (xb, y1, zb1), (xa, y1, za1)])


def rampa_y(capa, piso, mat, ya, yb, x0, x1, za0, za1, zb0, zb1):
    A.hexa(capa, piso, mat, [(x0, ya, za0), (x1, ya, za0), (x1, yb, zb0), (x0, yb, zb0),
                             (x0, ya, za1), (x1, ya, za1), (x1, yb, zb1), (x0, yb, zb1)])


def modulos(a, b, paso):
    n = max(1, round((b - a) / paso))
    return [a + (b - a) * i / n for i in range(n + 1)]


def intervalos_sin(a, b, huecos):
    """[a, b] menos los huecos [(h0, h1), ...]."""
    tramos = [(a, b)]
    for h0, h1 in huecos:
        nuevos = []
        for t0, t1 in tramos:
            if h1 <= t0 or h0 >= t1:
                nuevos.append((t0, t1))
                continue
            if h0 > t0:
                nuevos.append((t0, h0))
            if h1 < t1:
                nuevos.append((h1, t1))
        tramos = nuevos
    return [t for t in tramos if t[1] - t[0] > 0.05]


# ---------------------------------------------------------------- fachadas
def muro_cortina(eje, coord, a, b, z0, z1, hacia_afuera, banda_sup=True, paso=1.6, capa="fachada"):
    """Vidrio con montantes en el plano eje = coord ('y' o 'x'), entre a y b, de z0 a z1.
    hacia_afuera: +1 o -1 (lado exterior) para las bandas blancas."""
    t = 0.02
    if eje == "y":
        A.caja(capa, "", "vidrio", a, b, coord - t / 2, coord + t / 2, z0, z1)
        for x in modulos(a, b, paso):
            A.caja(capa, "", "montante", x - 0.03, x + 0.03, coord, coord + 0.10 * hacia_afuera, z0, z1)
        A.caja(capa, "", "montante", a, b, coord, coord + 0.08 * hacia_afuera, z0 + 1.02, z0 + 1.08)
        if banda_sup:
            A.caja(capa, "", "banda", a, b, coord + 0.02 * hacia_afuera, coord + 0.16 * hacia_afuera, z1 - 0.35, z1 + 0.20)
    else:
        A.caja(capa, "", "vidrio", coord - t / 2, coord + t / 2, a, b, z0, z1)
        for y in modulos(a, b, paso):
            A.caja(capa, "", "montante", coord, coord + 0.10 * hacia_afuera, y - 0.03, y + 0.03, z0, z1)
        A.caja(capa, "", "montante", coord, coord + 0.08 * hacia_afuera, a, b, z0 + 1.02, z0 + 1.08)
        if banda_sup:
            A.caja(capa, "", "banda", coord + 0.02 * hacia_afuera, coord + 0.16 * hacia_afuera, a, b, z1 - 0.35, z1 + 0.20)


def muro_ventanas(eje, coord, a, b, z0, z1, hacia_afuera, ancho_v=1.5, paso=PASO_VENTANAS):
    """Muro terracota de 0,20 m con ventanas de marco blanco en grilla (fachada norte y oeste)."""
    e0, e1 = sorted((coord, coord + 0.20 * hacia_afuera))
    alfeizar, dintel = z0 + 0.90, z0 + 2.60
    bordes = modulos(a, b, paso)

    def caja_plano(u0, u1, w0, w1, zz0, zz1, mat):
        if eje == "y":
            A.caja("fachada", "", mat, u0, u1, w0, w1, zz0, zz1)
        else:
            A.caja("fachada", "", mat, w0, w1, u0, u1, zz0, zz1)

    caja_plano(a, b, e0, e1, z0, alfeizar, "terracota")
    caja_plano(a, b, e0, e1, dintel, z1, "terracota")
    for i in range(len(bordes) - 1):
        u0, u1 = bordes[i], bordes[i + 1]
        um = (u0 + u1) / 2
        v0, v1 = um - ancho_v / 2, um + ancho_v / 2
        caja_plano(u0, v0, e0, e1, alfeizar, dintel, "terracota")
        caja_plano(v1, u1, e0, e1, alfeizar, dintel, "terracota")
        # vidrio retranqueado y marco blanco (4 lados + parteluz)
        g0, g1 = sorted((coord + 0.05 * hacia_afuera, coord + 0.07 * hacia_afuera))
        f0, f1 = sorted((coord + 0.07 * hacia_afuera, coord + 0.17 * hacia_afuera))
        caja_plano(v0, v1, g0, g1, alfeizar, dintel, "vidrio_oscuro")
        caja_plano(v0, v1, f0, f1, alfeizar, alfeizar + 0.08, "marco_blanco")
        caja_plano(v0, v1, f0, f1, dintel - 0.08, dintel, "marco_blanco")
        caja_plano(v0, v0 + 0.08, f0, f1, alfeizar, dintel, "marco_blanco")
        caja_plano(v1 - 0.08, v1, f0, f1, alfeizar, dintel, "marco_blanco")
        caja_plano(um - 0.03, um + 0.03, f0, f1, alfeizar, dintel, "marco_blanco")


def aletas_norte(coord, xs, z0, z1, saltar=()):
    """Aletas naranjas inclinadas por fuera del muro norte (la zona 'mas naranja' de las fotos),
    entre las ventanas, de banda a banda de piso."""
    w0, w1 = coord + 0.20, coord + 1.05
    t, s = 0.24, -0.45                                 # espesor y desplazamiento de la punta hacia el oeste
    zb, zt = (z0 + 0.12 if z0 > 0 else z0), z1 - 0.12
    for u in xs:
        if any(a <= u <= b for a, b in saltar):
            continue
        A.hexa("fachada", "", "naranja", [(u - t / 2, w0, zb), (u + t / 2, w0, zb), (u + t / 2 + s, w1, zb), (u - t / 2 + s, w1, zb),
                                          (u - t / 2, w0, zt), (u + t / 2, w0, zt), (u + t / 2 + s, w1, zt), (u - t / 2 + s, w1, zt)])


def banda_piso_norte(coord, a, b, z):
    """Borde blanco de losa por fuera del muro norte."""
    A.caja("fachada", "", "banda", a, b, coord + 0.20, coord + 0.44, z - 0.12, z + 0.12)


def fachadas():
    pisos = list(zip(PISOS[:-1], PISOS[1:]))
    x_n1 = modulos(JUNTA, E1_ESTE, PASO_VENTANAS)                   # grilla de ventanas del norte (edificio 1)
    x_n1_top = modulos(E1_ESTE, E1_ESTE_TOP, PASO_VENTANAS)         # caja del piso 4 sobre la plaza
    x_n2 = modulos(E2_OESTE, JUNTA, PASO_VENTANAS)
    for i, (z0, z1) in enumerate(pisos):
        top = i == 3
        x_este = E1_ESTE_TOP if top else E1_ESTE
        # ---- edificio 1, sur (vidrio) con huecos para las cajas en voladizo
        huecos = []
        if (z0, z1) == (CAJA_INF[2], CAJA_INF[3]):
            huecos.append((CAJA_INF[0], CAJA_INF[1]))
        if (z0, z1) == (CAJA_SUP[2], CAJA_SUP[3]):
            huecos.append((CAJA_SUP[0], CAJA_SUP[1]))
        for a, b in intervalos_sin(JUNTA, E1_ESTE, huecos):
            muro_cortina("y", E1_SUR, a, b, z0, z1, -1)
        if top:
            # caja terracota del piso 4 en el extremo este (voladizo naranja de las fotos)
            muro_ventanas("y", CAJA_ESTE_SUR, E1_ESTE, E1_ESTE_TOP, z0, z1, -1, ancho_v=0.8)
            muro_ventanas("x", E1_ESTE, CAJA_ESTE_SUR, E1_SUR, z0, z1, -1, ancho_v=0.6, paso=1.0)
            for x in modulos(E1_ESTE, E1_ESTE_TOP, 1.45):
                A.caja("fachada", "", "terracota", x - 0.15, x + 0.15, CAJA_ESTE_SUR - 0.55, CAJA_ESTE_SUR, z0, z1)
            A.caja("fachada", "", "terracota", E1_ESTE, E1_ESTE_TOP, CAJA_ESTE_SUR, E1_NORTE, 10.90, 11.00)   # cielo del voladizo
        # ---- edificio 1, norte: ventanas, aletas naranjas y bandas blancas de piso
        muro_ventanas("y", E1_NORTE, JUNTA, E1_ESTE, z0, z1, +1)
        xs = x_n1[1:-1]
        if top:
            muro_ventanas("y", E1_NORTE, E1_ESTE, E1_ESTE_TOP, z0, z1, +1)
            xs = xs + [E1_ESTE] + x_n1_top[1:-1]
        # en la planta baja no hay aletas detras de la escalera norte
        aletas_norte(E1_NORTE, xs, z0, z1, saltar=[(ESC_NORTE["x_alto"] - 9.6, 1e9)] if i == 0 else ())
        if i > 0:
            banda_piso_norte(E1_NORTE, JUNTA, x_este, z0)
        # ---- edificio 1, este: la planta baja queda bajo la plaza de la entrada (2.o piso)
        if top:
            muro_ventanas("x", E1_ESTE_TOP, CAJA_ESTE_SUR, E1_NORTE, z0, z1, +1, ancho_v=0.8)
        elif i > 0:
            muro_cortina("x", E1_ESTE, E1_SUR, E1_NORTE, z0, z1, +1)
            for y in modulos(E1_SUR, E1_NORTE, 2.5):
                if i == 1 and PUERTA_ESTE[0] - 0.3 < y < PUERTA_ESTE[1] + 0.3:
                    continue                                       # sin aleta frente a la entrada principal
                A.caja("fachada", "", "naranja", E1_ESTE, E1_ESTE + 0.60, y - 0.15, y + 0.15, z0, z1)
        # ---- edificio 2: sur vidrio, norte igual al edificio 1, oeste terracota
        muro_cortina("y", E2_SUR, E2_OESTE, JUNTA, z0, z1, -1)
        muro_ventanas("y", E2_NORTE, E2_OESTE, JUNTA, z0, z1, +1)
        aletas_norte(E2_NORTE, x_n2[1:-1], z0, z1)
        if i > 0:
            banda_piso_norte(E2_NORTE, E2_OESTE, JUNTA, z0)
        muro_ventanas("x", E2_OESTE, E2_SUR, E2_NORTE, z0, z1, -1)
        # retornos en la junta (las fachadas de los dos edificios no estan alineadas)
        muro_cortina("x", JUNTA, E2_SUR, E1_SUR, z0, z1, -1, paso=0.6)
        A.caja("fachada", "", "terracota", JUNTA - 0.10, JUNTA + 0.10, E1_NORTE, E2_NORTE + 0.20, z0, z1)

    # ---- cajas de vidrio en voladizo (sala abajo, caja superior arriba)
    for x0, x1, z0, z1 in (CAJA_INF, CAJA_SUP):
        muro_cortina("y", CAJA_SUR, x0, x1, z0, z1, -1, paso=1.3)
        muro_cortina("x", x0, CAJA_SUR, E1_SUR, z0, z1, -1, paso=1.3)
        muro_cortina("x", x1, CAJA_SUR, E1_SUR, z0, z1, +1, paso=1.3)
        # banda inferior (borde de la losa del voladizo)
        A.caja("fachada", "", "banda", x0 - 0.16, x1 + 0.16, CAJA_SUR - 0.16, CAJA_SUR, z0 - 0.35, z0 + 0.15)
        A.caja("fachada", "", "banda", x0 - 0.16, x0, CAJA_SUR, E1_SUR, z0 - 0.35, z0 + 0.15)
        A.caja("fachada", "", "banda", x1, x1 + 0.16, CAJA_SUR, E1_SUR, z0 - 0.35, z0 + 0.15)

    puertas()

    # ---- cornisa blanca en todo el borde del techo y equipos de clima
    zc0, zc1 = PISOS[-1] - 0.10, PISOS[-1] + 0.65
    for (x0, x1, y0, y1) in ((JUNTA, E1_ESTE_TOP, E1_SUR, E1_NORTE), (E2_OESTE, JUNTA, E2_SUR, E2_NORTE)):
        A.caja("fachada", "", "banda", x0, x1, y0 - 0.25, y0, zc0, zc1)
        A.caja("fachada", "", "banda", x0, x1, y1, y1 + 0.45, zc0, zc1)
    A.caja("fachada", "", "banda", E1_ESTE_TOP, E1_ESTE_TOP + 0.25, CAJA_ESTE_SUR, E1_NORTE, zc0, zc1)
    A.caja("fachada", "", "banda", E2_OESTE - 0.25, E2_OESTE, E2_SUR, E2_NORTE, zc0, zc1)
    A.caja("fachada", "", "banda", CAJA_SUP[0], CAJA_SUP[1], CAJA_SUR - 0.25, CAJA_SUR, zc0, zc1)
    zr = PISOS[-1]
    for (x0, x1, y0, y1, h) in ((3, 8, 1, 5, 1.1), (14, 18, 2, 6, 1.1), (24, 28, 1, 5, 1.1),
                                (-36, -32, 1, 5, 1.1), (-24, -20, 2, 6, 1.1)):
        A.caja("fachada", "", "equipos", x0, x1, y0, y1, zr, zr + h)
    A.caja("fachada", "", "banda", -8.0, -4.0, -3.0, 1.0, zr, zr + 2.4)       # sala de maquinas del ascensor

    # ---- pisos interiores de la planta baja (losa sobre terreno, no esta en el modelo)
    A.caja("fachada", "", "piso_interior", JUNTA, E1_ESTE, E1_SUR, E1_NORTE, -0.04, -0.01)
    A.caja("fachada", "", "piso_interior", E2_OESTE, JUNTA, E2_SUR, E2_NORTE, -0.04, -0.01)


def puertas():
    """Entrada principal en la fachada este (2.o piso, nivel de la plaza) y puerta de la fachada
    sur hacia la plataforma de la escalera."""
    z0, z1 = Z_SUP, Z_SUP + 2.45
    # este: hoja doble de vidrio oscuro con marco blanco y alero
    x, (y0, y1) = E1_ESTE, PUERTA_ESTE
    ym = (y0 + y1) / 2
    A.caja("fachada", "", "vidrio_oscuro", x + 0.10, x + 0.13, y0 + 0.10, y1 - 0.10, z0, z1 - 0.10)
    for (a, b) in ((y0, y0 + 0.10), (y1 - 0.10, y1), (ym - 0.03, ym + 0.03)):
        A.caja("fachada", "", "marco_blanco", x + 0.10, x + 0.18, a, b, z0, z1)
    A.caja("fachada", "", "marco_blanco", x + 0.10, x + 0.18, y0, y1, z1 - 0.10, z1)
    A.caja("fachada", "", "banda", x + 0.10, x + 1.90, y0 - 0.80, y1 + 0.80, z1 + 0.20, z1 + 0.38)
    # sur: puerta a la plataforma
    y, (x0, x1) = E1_SUR, PUERTA_SUR
    xm = (x0 + x1) / 2
    A.caja("fachada", "", "vidrio_oscuro", x0 + 0.10, x1 - 0.10, y - 0.13, y - 0.10, z0, z1 - 0.10)
    for (a, b) in ((x0, x0 + 0.10), (x1 - 0.10, x1), (xm - 0.03, xm + 0.03)):
        A.caja("fachada", "", "marco_blanco", a, b, y - 0.18, y - 0.10, z0, z1)
    A.caja("fachada", "", "marco_blanco", x0, x1, y - 0.18, y - 0.10, z1 - 0.10, z1)


# ---------------------------------------------------------------- escalera naranja (fachada sur)
def tramo(xa, za, xb, zb, y0=ESC_Y[0], y1=ESC_Y[1]):
    """Tramo recto a lo largo de x (de za a zb), con peldanos de hormigon y antepechos naranjas."""
    n = max(1, round(abs(zb - za) / 0.18))
    contra = (zb - za) / n
    corrida = (xb - xa) / n
    for k in range(n):
        x0, x1 = xa + k * corrida, xa + (k + 1) * corrida
        ztop = za + (k + 1) * contra
        A.caja("entorno", "", "hormigon", x0, x1, y0, y1, ztop - 0.30, ztop)
    p = ESC_PARAPETO
    for (q0, q1) in ((y0 - p, y0), (y1, y1 + p)):
        rampa_x("entorno", "", "naranja", xa, xb, q0, q1, za - 0.50, za + 1.10, zb - 0.50, zb + 1.10)
    rampa_x("entorno", "", "naranja", xa, xb, y0, y1, za - 0.50, za - 0.30, zb - 0.50, zb - 0.30)   # losa inferior


def escalera():
    """Escalera naranja de la fachada sur. Los tramos arrancan y terminan justo fuera de las
    caras de las vigas de borde V60/80 de los descansos (E1_207 en x = 2,2; E1_218 en x = 10;
    E1_220 en x = 20) y los antepechos van por fuera de las vigas E1_206, E1_208 y E1_221.
    El ultimo tramo llega a la plataforma del 2.o piso (nivel de la plaza de la entrada)."""
    p = ESC_PARAPETO
    media = 0.30 + 0.02                                            # media viga V60/80 + holgura
    x_f1a, x_f1b, x_f2a = 2.2 + media, 10.0 - media, 20.0 + media
    # descanso superior L99 (losa del modelo, z = 11,88, x 0..2,2): antepechos por fuera de las vigas
    A.caja("entorno", "", "naranja", -media, 2.2, -9.86 - media - p, -9.86 - media, 11.08, 12.98)
    A.caja("entorno", "", "naranja", -media - p, -media, -9.86 - media - p, E1_SUR, 11.08, 12.98)
    tramo(x_f1a, 11.88, x_f1b, 7.92)                                # pasa sobre la sala
    # terraza L100/L101 bajo la caja superior: antepecho por fuera de la viga de borde E1_221 (V30/45)
    A.caja("entorno", "", "naranja", 10.0 - media, 20.0 + media, -9.71 - 0.17 - p, -9.71 - 0.17, 7.47, 9.02)
    x_f2b = PLATAFORMA[0]
    tramo(x_f2a, 7.92, x_f2b, Z_SUP)                                # baja a la plataforma
    # pilar delgado bajo el tramo colgado de la fachada
    xm = (x_f2a + x_f2b) / 2
    A.caja("entorno", "", "hormigon", xm - 0.12, xm + 0.12, -9.07, -8.83, Z_INF, (7.92 + Z_SUP) / 2 - 0.50)


# ---------------------------------------------------------------- entorno en dos niveles
def pavimentos():
    """Nivel inferior (z = 0): terraza sur de la cafeteria, bajo la plataforma, vereda oeste y
    terraza norte. Quedan 2 cm sobre el pasto."""
    z0, z1 = Z_INF - 0.02, Z_INF
    x_plat, _, y_plat, _ = PLATAFORMA
    A.caja("entorno", "", "pavimento", SITIO_OESTE, x_plat, SITIO_SUR, E2_SUR, z0, z1)             # terraza sur
    A.caja("entorno", "", "pavimento", JUNTA, x_plat, E2_SUR, E1_SUR, z0, z1)
    A.caja("entorno", "", "pavimento", x_plat, E1_ESTE, y_plat, E1_SUR, z0, z1)                     # bajo la plataforma
    A.caja("entorno", "", "pavimento", x_plat, PLAZA_ESTE[1], SITIO_SUR, y_plat, z0, z1)
    A.caja("entorno", "", "pavimento", SITIO_OESTE, E2_OESTE, E2_SUR, E2_NORTE, z0, z1)             # vereda oeste
    A.caja("entorno", "", "pavimento", SITIO_OESTE, JUNTA, E2_NORTE, SITIO_NORTE, z0, z1)           # terraza norte
    A.caja("entorno", "", "pavimento", JUNTA, E1_ESTE, E1_NORTE, SITIO_NORTE, z0, z1)


def plataforma():
    """Plataforma del 2.o piso al sur del extremo este: losa sobre pilares, abierta debajo, con
    antepecho naranja. Recibe el tramo naranja y desde ella baja la escalinata."""
    x0, x1, y0, y1 = PLATAFORMA
    pe = ESC_PARAPETO
    A.caja("entorno", "", "hormigon", x0, x1, y0 + pe, y1, Z_SUP - 0.30, Z_SUP - 0.02)
    A.caja("entorno", "", "pavimento", x0, x1, y0 + pe, y1, Z_SUP - 0.02, Z_SUP)
    for x in (30.0, 33.0):
        for y in (-16.1, -12.3, -9.0):
            A.caja("entorno", "", "hormigon", x - 0.18, x + 0.18, y - 0.18, y + 0.18, Z_INF, Z_SUP - 0.30)
    # antepecho y canto naranjas del borde sur (sigue por el borde de la plaza)
    A.caja("entorno", "", "naranja", x0, x1, y0, y0 + pe, Z_SUP - 0.60, Z_SUP + 1.04)
    A.caja("entorno", "", "naranja", x1, PLAZA_ESTE[1], y0, y0 + pe, Z_SUP, Z_SUP + 1.04)
    # borde oeste: entre la escalinata y el tramo naranja, y entre el tramo y la fachada
    y_esc = ESCALINATA["y1"] + 0.25
    for (a, b) in ((y_esc, ESC_Y[0] - pe), (ESC_Y[1] + pe, E1_SUR)):
        A.caja("entorno", "", "naranja", x0, x0 + pe, a, b, Z_SUP, Z_SUP + 1.04)


def escalinata():
    """Escalinata ancha: baja desde la plataforma (z = 3,96) hacia el oeste hasta la terraza de
    la cafeteria (z = 0), con peldanos macizos y muros laterales naranjas inclinados."""
    xa, y0, y1 = ESCALINATA["x_alto"], ESCALINATA["y0"], ESCALINATA["y1"]
    n = round((Z_SUP - Z_INF) / 0.18)                               # 22 contrahuellas de 0,18 m
    contra, huella = (Z_SUP - Z_INF) / n, 0.35
    for k in range(1, n):                                           # la ultima contrahuella llega a la terraza
        A.caja("entorno", "", "hormigon", xa - k * huella, xa - (k - 1) * huella, y0, y1, Z_INF - 0.02, Z_SUP - k * contra)
    x_pie = xa - (n - 1) * huella - 0.30
    zb = Z_INF - 0.02
    for (q0, q1) in ((y0 - 0.25, y0), (y1, y1 + 0.25)):
        A.hexa("entorno", "", "naranja", [(x_pie, q0, zb), (xa, q0, zb), (xa, q1, zb), (x_pie, q1, zb),
                                          (x_pie, q0, Z_INF + 0.95), (xa, q0, Z_SUP + 1.04), (xa, q1, Z_SUP + 1.04), (x_pie, q1, Z_INF + 0.95)])


def plaza():
    """Plaza de la entrada principal a la altura del 2.o piso: relleno con muro de contencion,
    taludes de pasto hacia el nivel inferior y faroles."""
    x0, x1, y0, y1 = PLAZA_ESTE
    zb = NIVEL_TERRENO - 0.05
    A.caja("entorno", "", "contencion", x0, x1, y0, y1, zb, Z_SUP - 0.02)
    A.caja("entorno", "", "pavimento", x0, x1, y0, y1, Z_SUP - 0.02, Z_SUP)
    zt, zp = Z_SUP - 0.01, NIVEL_TERRENO + 0.01
    rampa_x("entorno", "", "talud", x1, x1 + TALUD, y0, y1, zb, zt, zb, zp)                       # talud este
    rampa_y("entorno", "", "talud", y1, y1 + TALUD * 0.75, x0, x1, zb, zt, zb, zp)                # talud norte
    xe, yn = x1 + TALUD, y1 + TALUD * 0.75                                                         # esquina noreste
    A.hexa("entorno", "", "talud", [(x1, y1, zb), (xe, y1, zb), (xe, yn, zb), (x1, yn, zb),
                                    (x1, y1, zt), (xe, y1, zp), (xe, yn, zp), (x1, yn, zp)])
    # antepecho blanco sobre el muro de contencion al norte de la escalera norte
    y_esc = ESC_NORTE["y1"] + 0.20
    A.caja("entorno", "", "banda", x0, x0 + 0.20, y_esc, y1, Z_SUP, Z_SUP + 0.95)
    # faroles
    for y in (-12.0, -4.0, 4.0, 12.0):
        A.caja("entorno", "", "metal_oscuro", x1 - 2.55, x1 - 2.45, y - 0.05, y + 0.05, Z_SUP, Z_SUP + 4.6)
        A.caja("entorno", "", "metal_oscuro", x1 - 3.15, x1 - 2.45, y - 0.08, y + 0.08, Z_SUP + 4.5, Z_SUP + 4.62)


def escalera_norte():
    """Escalera del lado norte (zona naranja): dos tramos rectos con un descanso a media altura,
    desde la plaza de la entrada (z = 3,96) hacia el oeste hasta la terraza norte (z = 0),
    pegada a la fachada, con muros blancos a ambos lados."""
    xa, y0, y1 = ESC_NORTE["x_alto"], ESC_NORTE["y0"], ESC_NORTE["y1"]
    n_tramo, huella, largo_descanso = 11, 0.35, 1.80
    contra = (Z_SUP - Z_INF) / (2 * n_tramo)                       # 0,18 m
    z_desc = Z_SUP - n_tramo * contra                               # 1,98 m
    zb = Z_INF - 0.02
    for k in range(1, n_tramo):                                     # tramo 1 (la contrahuella 11 llega al descanso)
        A.caja("entorno", "", "hormigon", xa - k * huella, xa - (k - 1) * huella, y0, y1, zb, Z_SUP - k * contra)
    x_d1 = xa - (n_tramo - 1) * huella
    x_d0 = x_d1 - largo_descanso
    A.caja("entorno", "", "hormigon", x_d0, x_d1, y0, y1, zb, z_desc)
    for k in range(1, n_tramo):                                     # tramo 2 (la ultima llega a la terraza)
        A.caja("entorno", "", "hormigon", x_d0 - k * huella, x_d0 - (k - 1) * huella, y0, y1, zb, z_desc - k * contra)
    x_pie = x_d0 - (n_tramo - 1) * huella - 0.30
    h = 0.95
    for (q0, q1) in ((y0 - 0.20, y0), (y1, y1 + 0.20)):
        A.hexa("entorno", "", "banda", [(x_d1, q0, zb), (xa, q0, zb), (xa, q1, zb), (x_d1, q1, zb),
                                        (x_d1, q0, z_desc + h), (xa, q0, Z_SUP + h), (xa, q1, Z_SUP + h), (x_d1, q1, z_desc + h)])
        A.caja("entorno", "", "banda", x_d0, x_d1, q0, q1, zb, z_desc + h)
        A.hexa("entorno", "", "banda", [(x_pie, q0, zb), (x_d0, q0, zb), (x_d0, q1, zb), (x_pie, q1, zb),
                                        (x_pie, q0, Z_INF + h), (x_d0, q0, z_desc + h), (x_d0, q1, z_desc + h), (x_pie, q1, Z_INF + h)])


def entorno():
    pavimentos()
    escalera()
    plataforma()
    escalinata()
    plaza()
    escalera_norte()


# ---------------------------------------------------------------- mobiliario
def mesa_alta_y_taburetes(x, y, z):
    piso = "CIELO_1"
    A.caja("mobiliario", piso, "mesa_blanca", x - 0.60, x + 0.60, y - 0.60, y + 0.60, z + 0.95, z + 1.00)
    A.caja("mobiliario", piso, "metal_oscuro", x - 0.06, x + 0.06, y - 0.06, y + 0.06, z, z + 0.95)
    A.caja("mobiliario", piso, "metal_oscuro", x - 0.30, x + 0.30, y - 0.30, y + 0.30, z, z + 0.03)
    for (dx, dy, bx, by) in ((-0.30, -0.85, 0, -1), (0.30, -0.85, 0, -1), (-0.30, 0.85, 0, 1), (0.30, 0.85, 0, 1),
                             (-0.85, 0.0, -1, 0), (0.85, 0.0, 1, 0)):
        sx, sy = x + dx, y + dy
        A.caja("mobiliario", piso, "turquesa", sx - 0.18, sx + 0.18, sy - 0.18, sy + 0.18, z + 0.70, z + 0.76)
        for (lx, ly) in ((-0.14, -0.14), (0.14, -0.14), (0.14, 0.14), (-0.14, 0.14)):
            A.caja("mobiliario", piso, "metal_oscuro", sx + lx - 0.015, sx + lx + 0.015, sy + ly - 0.015, sy + ly + 0.015, z, z + 0.70)
        # respaldo bajo, del lado opuesto a la mesa
        if bx:
            A.caja("mobiliario", piso, "turquesa", sx + bx * 0.16, sx + bx * 0.20, sy - 0.17, sy + 0.17, z + 0.76, z + 1.00)
        else:
            A.caja("mobiliario", piso, "turquesa", sx - 0.17, sx + 0.17, sy + by * 0.16, sy + by * 0.20, z + 0.76, z + 1.00)


def mesa_cafe(x, y, z, piso, capa="mobiliario", lado=0.40, quitasol=False):
    A.caja(capa, piso, "madera", x - lado, x + lado, y - lado, y + lado, z + 0.72, z + 0.76)
    A.caja(capa, piso, "metal_oscuro", x - 0.04, x + 0.04, y - 0.04, y + 0.04, z, z + 0.72)
    A.caja(capa, piso, "metal_oscuro", x - 0.22, x + 0.22, y - 0.22, y + 0.22, z, z + 0.03)
    d = lado + 0.22
    for (dx, dy) in ((0, -d), (0, d), (-d, 0), (d, 0)):
        sx, sy = x + dx, y + dy
        A.caja(capa, piso, "metal_oscuro", sx - 0.20, sx + 0.20, sy - 0.20, sy + 0.20, z + 0.43, z + 0.47)
        for (lx, ly) in ((-0.17, -0.17), (0.17, -0.17), (0.17, 0.17), (-0.17, 0.17)):
            A.caja(capa, piso, "metal_oscuro", sx + lx - 0.015, sx + lx + 0.015, sy + ly - 0.015, sy + ly + 0.015, z, z + 0.43)
        ox = 0.18 if dx > 0 else (-0.18 if dx < 0 else 0)
        oy = 0.18 if dy > 0 else (-0.18 if dy < 0 else 0)
        if ox:
            A.caja(capa, piso, "metal_oscuro", sx + ox - 0.02, sx + ox + 0.02, sy - 0.19, sy + 0.19, z + 0.47, z + 0.88)
        else:
            A.caja(capa, piso, "metal_oscuro", sx - 0.19, sx + 0.19, sy + oy - 0.02, sy + oy + 0.02, z + 0.47, z + 0.88)
    if quitasol:
        A.caja(capa, piso, "metal_oscuro", x - 0.03, x + 0.03, y - 0.03, y + 0.03, z + 0.76, z + 2.45)
        b, t = 1.30, 0.12
        A.hexa(capa, piso, "quitasol", [(x - b, y - b, z + 2.15), (x + b, y - b, z + 2.15), (x + b, y + b, z + 2.15), (x - b, y + b, z + 2.15),
                                        (x - t, y - t, z + 2.55), (x + t, y - t, z + 2.55), (x + t, y + t, z + 2.55), (x - t, y + t, z + 2.55)])


def sala():
    z = SALA["z"]
    for x in (1.95, 5.55):
        for y in (-9.40, -5.70, -2.00):
            mesa_alta_y_taburetes(x, y, z)
    # pantalla en el muro interior (norte) de la sala
    A.caja("mobiliario", "CIELO_1", "metal_oscuro", 2.45, 5.05, -0.36, -0.30, z + 1.00, z + 2.50)
    A.caja("mobiliario", "CIELO_1", "pantalla", 2.52, 4.98, -0.40, -0.36, z + 1.06, z + 2.44)


def cafeteria():
    """Cafeteria: solo el rectangulo de la planta baja bajo la sala, de fachada a fachada."""
    z, piso = CAFE["z"], "CIELO_1S"
    A.caja("mobiliario", piso, "piso_madera", CAFE["x0"], CAFE["x1"], CAFE["y0"], CAFE["y1"], z - 0.01, z)
    for x in (1.55, 3.80, 6.05):
        for y in (-5.70, -3.45, -1.20, 1.05, 3.30, 5.55):
            mesa_cafe(x, y, z, piso)
    # barra con cubierta blanca, repisa y taburetes en el extremo norte
    A.caja("mobiliario", piso, "madera", 1.30, 6.30, 7.30, 7.90, z, z + 1.05)
    A.caja("mobiliario", piso, "mesa_blanca", 1.20, 6.40, 7.22, 7.98, z + 1.05, z + 1.10)
    A.caja("mobiliario", piso, "madera", 1.00, 6.60, 8.15, 8.45, z, z + 2.00)
    for x in (2.0, 3.1, 4.2, 5.3):
        A.caja("mobiliario", piso, "turquesa", x - 0.17, x + 0.17, 6.78, 7.12, z + 0.70, z + 0.76)
        A.caja("mobiliario", piso, "metal_oscuro", x - 0.03, x + 0.03, 6.92, 6.98, z, z + 0.70)


def terraza():
    """Mesas exteriores en el nivel inferior: bajo la sala en voladizo, terraza sur con quitasoles
    y terraza norte al pie de la escalera norte."""
    z, capa = Z_INF, "mobiliario_exterior"
    for x in (1.6, 3.9, 6.2):                     # bajo la caja de la sala (cubierto, sin quitasol)
        mesa_cafe(x, -9.60, z, "", capa=capa, lado=0.45)
    for x in (-8.0, -3.0, 2.0, 7.0, 12.0, 17.0):
        mesa_cafe(x, -12.60, z, "", capa=capa, lado=0.45, quitasol=True)
    for x in (-5.5, -0.5, 4.5, 9.5, 14.5):
        mesa_cafe(x, -16.00, z, "", capa=capa, lado=0.45, quitasol=True)
    for x in (20.0, 14.0, 8.0, 2.0, -4.0):
        mesa_cafe(x, 14.60, z, "", capa=capa, lado=0.45, quitasol=True)


# ---------------------------------------------------------------- verificacion contra la estructura
def cajas_estructura():
    """Elementos del modelo como cajas (columnas, vigas y muros) o segmentos (diagonales)."""
    U = json.loads(MODELO.read_text(encoding="utf-8"))
    N = {n["id"]: n for n in U["nodes"]}
    cajas, segmentos = [], []
    for e in U["elements"]:
        if e["type"] == "rigido":
            continue
        a, b = N[e["nodeI"]], N[e["nodeJ"]]
        w, h = float(e.get("width_m") or 0.3), float(e.get("height_m") or 0.3)
        if e["type"] == "muro":
            t, L = w, h
            if e.get("wallInPlaneAxis") == "X":
                caja = (a["x"] - L / 2, a["x"] + L / 2, a["y"] - t / 2, a["y"] + t / 2)
            else:
                caja = (a["x"] - t / 2, a["x"] + t / 2, a["y"] - L / 2, a["y"] + L / 2)
            cajas.append((e["elementTag"], caja + (min(a["z"], b["z"]), max(a["z"], b["z"]))))
            continue
        dx, dy, dz = b["x"] - a["x"], b["y"] - a["y"], b["z"] - a["z"]
        if abs(dz) > 0.9 * math.sqrt(dx * dx + dy * dy + dz * dz) and abs(dx) < 1e-6 and abs(dy) < 1e-6:     # columna
            cajas.append((e["elementTag"], (a["x"] - w / 2, a["x"] + w / 2, a["y"] - h / 2, a["y"] + h / 2,
                                            min(a["z"], b["z"]), max(a["z"], b["z"]))))
        elif abs(dz) < 1e-6 and (abs(dx) < 1e-6 or abs(dy) < 1e-6):                                        # viga recta
            if abs(dy) < 1e-6:
                cajas.append((e["elementTag"], (min(a["x"], b["x"]), max(a["x"], b["x"]), a["y"] - w / 2, a["y"] + w / 2, a["z"] - h, a["z"])))
            else:
                cajas.append((e["elementTag"], (a["x"] - w / 2, a["x"] + w / 2, min(a["y"], b["y"]), max(a["y"], b["y"]), a["z"] - h, a["z"])))
        else:
            segmentos.append((e["elementTag"], a, b, max(w, h) / 2))
    return cajas, segmentos


def _puntos_hexa(h, n=5):
    """n x n x n puntos dentro de un prisma de 8 esquinas (interpolacion trilineal)."""
    P = [h[3 * k:3 * k + 3] for k in range(8)]
    pts = []
    for i in range(n):
        u = i / (n - 1)
        for j in range(n):
            v = j / (n - 1)
            pesos = ((1 - u) * (1 - v), u * (1 - v), u * v, (1 - u) * v)
            abajo = [sum(pesos[q] * P[q][c] for q in range(4)) for c in range(3)]
            arriba = [sum(pesos[q] * P[4 + q][c] for q in range(4)) for c in range(3)]
            for k in range(n):
                w = k / (n - 1)
                pts.append(tuple((1 - w) * abajo[c] + w * arriba[c] for c in range(3)))
    return pts


def _dist_segmento(p, a, b):
    ab = [b[c] - a[c] for c in range(3)]
    ap = [p[c] - a[c] for c in range(3)]
    L2 = sum(v * v for v in ab) or 1e-12
    t = max(0.0, min(1.0, sum(ap[c] * ab[c] for c in range(3)) / L2))
    return math.sqrt(sum((ap[c] - t * ab[c]) ** 2 for c in range(3)))


def choques(tol=0.02):
    """Cajas y prismas de mobiliario, escaleras y entorno que se cruzan con la estructura
    (mas de tol en cada eje). La fachada va por fuera de la estructura y no se revisa."""
    estr, segs = cajas_estructura()
    hallados = []
    for (capa, piso, mat), g in A.grupos.items():
        if capa == "fachada":
            continue
        c = g["cajas"]
        for i in range(0, len(c), 6):
            b = c[i:i + 6]
            for tag, s in estr:
                if (min(b[1], s[1]) - max(b[0], s[0]) > tol and min(b[3], s[3]) - max(b[2], s[2]) > tol
                        and min(b[5], s[5]) - max(b[4], s[4]) > tol):
                    hallados.append((capa, mat, tag, [round(v, 2) for v in b]))
            for tag, p, q, r in segs:
                for k in range(21):
                    t = k / 20
                    x, y, z = (p["x"] + t * (q["x"] - p["x"]), p["y"] + t * (q["y"] - p["y"]), p["z"] + t * (q["z"] - p["z"]))
                    if b[0] - r + tol < x < b[1] + r - tol and b[2] - r + tol < y < b[3] + r - tol and b[4] - r + tol < z < b[5] + r - tol:
                        hallados.append((capa, mat, tag, [round(v, 2) for v in b]))
                        break
        h = g["hexas"]
        for i in range(0, len(h), 24):
            hx = h[i:i + 24]
            xs, ys, zs = hx[0::3], hx[1::3], hx[2::3]
            bb = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
            pts = None
            for tag, s in estr:
                if not (min(bb[1], s[1]) - max(bb[0], s[0]) > tol and min(bb[3], s[3]) - max(bb[2], s[2]) > tol
                        and min(bb[5], s[5]) - max(bb[4], s[4]) > tol):
                    continue
                pts = pts or _puntos_hexa(hx)
                if any(s[0] + tol < x < s[1] - tol and s[2] + tol < y < s[3] - tol and s[4] + tol < z < s[5] - tol for x, y, z in pts):
                    hallados.append((capa, mat, tag, [round(v, 2) for v in bb]))
            for tag, p, q, r in segs:
                pa, pb = (p["x"], p["y"], p["z"]), (q["x"], q["y"], q["z"])
                if (max(pa[0], pb[0]) + r < bb[0] or min(pa[0], pb[0]) - r > bb[1] or max(pa[1], pb[1]) + r < bb[2]
                        or min(pa[1], pb[1]) - r > bb[3] or max(pa[2], pb[2]) + r < bb[4] or min(pa[2], pb[2]) - r > bb[5]):
                    continue
                pts = pts or _puntos_hexa(hx)
                if any(_dist_segmento(pt, pa, pb) < r - tol for pt in pts):
                    hallados.append((capa, mat, tag, [round(v, 2) for v in bb]))
    return hallados


# ---------------------------------------------------------------- salida
def generar():
    A.grupos.clear()
    fachadas()
    entorno()
    sala()
    cafeteria()
    terraza()
    datos = {
        "version": 2,
        "nota": "Capa SOLO VISUAL generada por scripts/generar_arquitectura.py. No es parte del modelo de OpenSees "
                "ni cambia ningun resultado; Unity la dibuja sin collider (no se selecciona).",
        "nivelTerreno": NIVEL_TERRENO,
        "materiales": [{"nombre": k, "r": v[0], "g": v[1], "b": v[2], "a": v[3]} for k, v in MATERIALES.items()],
        "grupos": [dict(g, cajas=[round(v, 4) for v in g["cajas"]]) for g in A.grupos.values()],
    }
    return datos


def preview(carpeta):
    """Vistas previas (matplotlib) de los mismos datos que dibuja Unity. No son capturas de Unity."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    U = json.loads(MODELO.read_text(encoding="utf-8"))
    N = {n["id"]: n for n in U["nodes"]}
    caras = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    luz = np.array([0.35, -0.55, 0.75])
    luz = luz / np.linalg.norm(luz)

    def objetos(g, lim):
        """Prismas del grupo dentro de la vista: las cajas se recortan al rectangulo de la vista."""
        c, h = g["cajas"], g["hexas"]
        out = []
        for i in range(0, len(c), 6):
            x0, x1, y0, y1, z0, z1 = c[i:i + 6]
            x0, x1, y0, y1 = max(x0, lim[0]), min(x1, lim[1]), max(y0, lim[2]), min(y1, lim[3])
            if x1 - x0 < 1e-6 or y1 - y0 < 1e-6:
                continue
            out.append([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
        for i in range(0, len(h), 24):
            o = [tuple(h[i + 3 * k:i + 3 * k + 3]) for k in range(8)]
            if all(lim[0] - 1 <= q[0] <= lim[1] + 1 and lim[2] - 1 <= q[1] <= lim[3] + 1 for q in o):
                out.append(o)
        return out

    def render(nombre, lim, elev, azim, zmax, filtro, pasto=True, estructura=True):
        fig = plt.figure(figsize=(14, 8), dpi=110)
        ax = fig.add_subplot(111, projection="3d")
        ax.computed_zorder = False          # el pasto siempre atras; la estructura (lineas) encima, como rayos X
        if pasto:
            zp = NIVEL_TERRENO - 0.01
            suelo = Poly3DCollection([np.array([(lim[0], lim[2], zp), (lim[1], lim[2], zp), (lim[1], lim[3], zp), (lim[0], lim[3], zp)])],
                                     facecolors=[(0.33, 0.50, 0.22, 1)], edgecolors="none")
            suelo.set_zorder(0)
            ax.add_collection3d(suelo)
        P, C = [], []
        for (capa, piso, mat), g in A.grupos.items():
            if not filtro(capa, mat):
                continue
            r, gg, b, a = MATERIALES[mat]
            for o in objetos(g, lim):
                cen = np.mean(o, axis=0)
                for f in caras:
                    Q = np.array([o[i] for i in f])
                    n = np.cross(Q[1] - Q[0], Q[2] - Q[0])
                    if np.linalg.norm(n) < 1e-9:
                        n = np.cross(Q[2] - Q[0], Q[3] - Q[0])
                    if np.linalg.norm(n) < 1e-9:
                        continue
                    n = n / np.linalg.norm(n)
                    if np.dot(n, Q.mean(axis=0) - cen) < 0:
                        n = -n
                    s = 0.55 + 0.45 * max(0.0, float(np.dot(n, luz)))
                    P.append(Q)
                    C.append((r * s, gg * s, b * s, max(a, 0.12)))
        if estructura:
            for e in U["elements"]:
                if e["type"] == "rigido":
                    continue
                a, b = N[e["nodeI"]], N[e["nodeJ"]]
                if not (lim[0] <= a["x"] <= lim[1] and lim[2] <= a["y"] <= lim[3]) or min(a["z"], b["z"]) < -0.05:
                    continue
                col = {"columna": "#3f356e", "viga": "#6d5fb0", "muro": "#9d8fd0", "arriostre": "#ff6f8e"}.get(e["type"], "#888")
                ax.plot([a["x"], b["x"]], [a["y"], b["y"]], [a["z"], b["z"]], color=col, lw=0.8, alpha=0.45, zorder=2)
        arq = Poly3DCollection(P, facecolors=C, edgecolors="none")
        arq.set_zorder(1)
        ax.add_collection3d(arq)
        ax.set_xlim(lim[0], lim[1]); ax.set_ylim(lim[2], lim[3]); ax.set_zlim(-0.5, zmax)
        ax.set_box_aspect((lim[1] - lim[0], lim[3] - lim[2], zmax + 0.5), zoom=1.35)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(carpeta / nombre)
        plt.close(fig)
        print("vista previa:", carpeta / nombre)

    carpeta.mkdir(parents=True, exist_ok=True)
    todo = lambda c, m: True
    render("arquitectura_sureste.png", (-14, 52, -22, 14), 18, -58, 18, todo)
    render("arquitectura_este.png", (16, 60, -22, 24), 20, 8, 18, todo)
    render("arquitectura_norte.png", (-44, 60, -8, 28), 16, 62, 18, todo)
    render("arquitectura_noreste.png", (12, 59, -18, 27), 22, 50, 16, todo)
    render("arquitectura_sala_escalera.png", (-3, 40, -20, 14), 26, -64, 16,
           lambda c, m: (c != "fachada" or m == "banda") and m not in ("pavimento", "contencion", "talud"), pasto=False)
    render("arquitectura_planta.png", (-12, 40, -19, 18), 89, -90, 6,
           lambda c, m: c in ("mobiliario", "mobiliario_exterior") and m != "piso_madera"
           or (c == "entorno" and m in ("hormigon", "naranja", "banda")), pasto=False, estructura=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--preview", type=Path, default=None, help="carpeta para guardar vistas previas (PNG)")
    ap.add_argument("--salida", type=Path, default=SALIDA)
    args = ap.parse_args()
    datos = generar()
    args.salida.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n_cajas = sum(len(g["cajas"]) // 6 for g in datos["grupos"])
    n_hexas = sum(len(g["hexas"]) // 24 for g in datos["grupos"])
    print(f"arquitectura visual: {len(datos['grupos'])} grupos, {n_cajas} cajas, {n_hexas} prismas -> {args.salida}")
    ch = choques()
    print(f"choques de mobiliario/escaleras/entorno con la estructura: {len(ch)}")
    for c in ch[:30]:
        print("  ", c)
    if args.preview:
        preview(args.preview)


if __name__ == "__main__":
    main()
