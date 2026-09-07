"""Correccion CANDIDATA del paquete VISUAL del marco de acero I'-J (P3/P4) y del
voladizo NORTE del Edificio I (P1/P2/P4), recorte del LATERAL ESTE (P3/P4) y
ELIMINACION de las FRANJAS SUR continuas (v<0, P1/P2/P3/P4).

INTEGRADO en el flujo de exportacion (se invoca al final de export_lab_data.py), de
modo que regenerar lab_data NO pierde la correccion. Idempotente (re-ejecutar no
dublica ni altera de nuevo: solo toca los IDs ya marcados).

Alcance (verificado contra los DXF de planta; NO se fabrica ninguna coordenada):
  * MARCO I'-J (elev lamina 800, entre +7.87 P3 y +11.83 P4): nodos aprobados con
    'adoptar huellas exactas' (RLE-PILAR piso4_103): I'=44.9190, M=47.4558,
    J=49.7935, filas de eje v=0.2811/9.1348/16.3472. Horizonales +7.87/+11.83 = vigas
    de piso ya modeladas (B1-B4, V.60/80); vertical I' = C_Ip existente (hormigon).
    Se agregaron SOLO los miembros sin representacion (12): columnas montante M (3)
    y vertical J (3) desde huella fisica, mas diagonales D1/D2 por eje (6) desde la
    elevacion 800. Geometria de viewer (recibe_losa=false), sin FE/tributaria.
  * El plano P3/P4 NO dibuja diagonales en planta (solo existen en la elevacion de
    la lamina 800, ilegible para el modelo): las diagonales y miembros entre forjados
    quedan PENDIENTES.
  * TORRE G-H (u=20-30): las losas aisladas L_EI_CP3_324 (e=15cm) y L_EI_CP4_426
    (e=12cm) son losas estructurales reales (rotulos/espesores de plano); se agrega
    el marco RLE-VIGA documentado de 4 lados + anillo + verticales como geometria de
    viewer (recibe_losa=false, patron P2_ADD_BEAMS). Decision del usuario
    2026-09-06 ('mantener + anadir marco'). Ver TORRE_G_H_P3/TORRE_G_H_P4.
    Marco vertical del voladizo lateral (tramo +7.87 P3 -> +11.83 P4): cruces X en
    las dos caras laterales (OESTE u=19.70 y ESTE u=30.30) segun las laminas de
    detalle 801/802: panel RECTANGULAR 4.12 x 3.96 m, |m|=0.961 (angulo 43.87/136.13
    verificado con ezdxf). El forjado P4 fue corregido al plano vertical de P3
    (v=16.45->20.57) porque las elevaciones NO documentan el desplazamiento +0.18 m
    del plano (solo existe en planta); asi la cara es un rectangulo y la diagonal
    respeta 0.961. Extremos anclados a los nodos del marco TORRE_G_H_P3/P4; 4
    diagonales TOWER_DIAG_P3_P4_* en P4 (recibe_losa=false, sin FE). No copia D1/D2
    del marco I'-J (L800) ni las inferiores de L800. Ver TORRE_G_H_P34_DIAGS.
  * Las "lineas paralelas RLE-VIGA" son caras de la misma viga (concreto V.60/80 /
    V.40/60, ya modeladas); NO se genera un elemento por cara ni se duplica.
  * FRANJAS SUR (v<0) ELIMINADAS COMPLETAS: decision del usuario (2026-09-06). En el
    lateral sur el edificio termina en las vigas perimetrales; las bandas continuas
    v[-1.15,0] (P4 v[-0.97,0]) NO son voladizos reales a pesar de su nombre:
      P1 L_EI_CP1_D_SUP_OESTE_VOL, P2 L_EI_CP2_D_VOLADIZO_EXTERIOR_EJE_1,
      P3 L_EI_CP3_D_VOLADIZO_BAJO, P4 L_EI_CP4_D_VOLADIZO_BAJO.
    Se ELIMINAN (no como bandas menores) y su '_DIAF' derivado desaparece con la losa
    (ver FRANJAS_SUR_ELIMINAR).
  * PIEZAS AISLADAS FUERA DE LA HUELLA PRINCIPAL ELIMINADAS COMPLETAS (validacion
    visual, 2026-09-06): P2 L_EI_CP2_221, P3 L_EI_CP3_315 y
    L_EI_CP3_D_VOLADIZO_ALTO_LENGUA, P4 L_EI_CP4_D_VOLADIZO_ALTO_ESTE. No tocan el
    marco metalico I'-J (columnas/diagonales). Ver PIEZAS_FUERA_ELIMINAR.
  * EAST_RECORTE quedo VACIO: las losas norte que antes se recortaban al lateral este
    ahora se ELIMINAN completas (ver PIEZAS_FUERA_ELIMINAR); no queda nada a recortar.
  * P3: las columnas de acero IpJ(46.35)/J(48.7)/FS1(20.38)/GS2(30.4) son registros
    'RLE-TEXTO-1' (rotulo 'V.M. 300x300x5') PERO NO caen sobre huella fisica RLE-PILAR
    del plano P3 (verificado: las unicas huellas 70x70 del sector I'-J estan en la fila
    concreta u[44.65,45.35]; no hay huella en u~46.3 ni u~48.7 ni en la franja alta
    v=18.2-18.4). Se reclasifican como RefPendientes (mismo criterio P4: sin huella
    fisica ni geometria respaldada -> no se dibujan como columna estructural completa).
    Los candidatos 'P.M.I.' (JP1-6) ya son RefPendientes.
  * P4 (voladizo norte I'-J): NINGUNA columna de acero del paquete coincide con la
    huella fisica del plano (RLE-PILAR en u=44.92 Ip, 47.46 y 49.79). Todas (IpS1,
    JS2, JS3, JS4, JS5, JS8) proceden de texto (RLE-TEXTO-1) y quedan fuera de la
    geometria fisica: se reclasifican como RefPendientes (marcador visual) para no
    dibujarlas como columnas inventadas. Se les conserva la posicion para trazabilidad.
  * P4 (voladizo NORTE, eje G/H): GS6(21.5,21.03) y HS7(31.55,21.03) NO caen sobre
    huella; las huellas RLE-PILAR del plano P4 (2017_67-103) estan en
    u[19.85,20.15] v[20.30,20.60] y u[29.85,30.15] v[20.30,20.60] (centros
    (20.0,20.45) y (30.0,20.45), dims 0.30x0.30 = P.M. 300x300x20). Se REUBICAN
    sobre la huella (conservan seccion y estado 'confirmado').
  * P2 (voladizo norte): G3S1(18.96,14.79) sin huella; la huella RLE-PILAR del plano
    P2 (2017_67-102) mas cercana es u[17.34,17.64] v[20.12,20.42] (centro
    (17.5,20.27)). Se REUBICA. La segunda huella documentada del voladizo
    ((10.0,20.27)) NO tenia columna modelada: se incorpora por huella RLE-PILAR como
    COL_EI_CP2_RLE_PILAR_10.00_20.27 (ID trazable, ver P2_ADD).
  * P1 (lado norte, esquina E): las losas D_VOL_ESTE_OE/ES (u[33.73,45.35]
    v[16.5,28.84]) no tienen correspondencia en el plano P1 (2017_67-101): en ese
    sector el plano solo muestra la planta de OTRA estructura (pilares/vigas en
    v 18.5-26.4, ejes u 30/40/50 - otro edificio en el mismo plano), no un voladizo
    del Edificio I. Sin soporte fisico ni documento, se ELIMINAN del paquete.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "Assets" / "StreamingAssets" / "lab_data" / "edificios" / "I" / "geometry"

# Huella fisica de las columnas de acero del plano P4 (DXF piso4_103, RLE-PILAR),
# en frame comun (u,v). Una columna se considera respaldada solo si su u cae dentro
# de un intervalo de huella en cualquiera de los niveles. (v niveles ~0.28/9.13/16.35)
P4_PHYSICAL_FOOTPRINTS_U = [(44.57, 45.27), (47.31, 47.61), (49.64, 49.94)]

# Sufijo de IDs P4 del paquete (todas 'P.M. 300x300x20' desde RLE-TEXTO-1).
P4_STEEL = ["COL_EI_CP4_S_IpS1_45.97", "COL_EI_CP4_S_JS2_48.77", "COL_EI_CP4_S_JS5_48.73",
            "COL_EI_CP4_S_JS3_51.97", "COL_EI_CP4_S_JS4_52.11", "COL_EI_CP4_S_JS8_52.08"]

# Huella fisica de las columnas de acero del plano P3 (DXF 2017_67-102, banda P3,
# RLE-PILAR, frame comun u,v). En el sector voladizo I'-J la UNICA huella 70x70 es la
# fila concreta de apoyo Ip (u~45.0); no existe huella en u~46.3 (IpJ), u~48.7 (J) ni en
# la franja alta v=18.2-18.4 (FS1/GS2). Verificado numericamente con ezdxf.
P3_PHYSICAL_FOOTPRINTS_U = [(44.65, 45.35)]

# Sufijo de IDs P3 del paquete metalico RLE-TEXTO-1 sin huella fisica (todas
# 'V.M. 300x300x5' procedentes de rotulo de texto).
P3_STEEL = ["COL_EI_CP3_S_IpJ1_46.35", "COL_EI_CP3_S_IpJ2_46.36", "COL_EI_CP3_S_IpJ3_46.34",
            "COL_EI_CP3_S_J1_48.68", "COL_EI_CP3_S_J2_48.7", "COL_EI_CP3_S_J3_48.9",
            "COL_EI_CP3_S_FS1_20.38", "COL_EI_CP3_S_GS2_30.4"]

# --- Voladizo NORTE (P1/P2/P4) ------------------------------------------------ #
# Losas P1 construidas desde la planta de OTRO edificio (plano 2017_67-101): se
# eliminan del paquete (representacion; no existe voladizo P1 en u[33.7,45.4]).
P1_REMOVE_LOSAS = ["L_EI_CP1_D_VOL_ESTE_OE", "L_EI_CP1_D_VOL_ESTE_ES"]

# Reubicacion de columnas a la huella fisica RLE-PILAR (frame comun u,v).
# P2 (plano 2017_67-102): centro de la huella u[17.34,17.64] v[20.12,20.42].
P2_RELOC_COLS = {
    "COL_EI_CP2_S_G3S1_18.96": ((17.5, 20.27), "huella u[17.34,17.64] v[20.12,20.42]"),
}

# Columna P2 incorporada DESDE huella fisica RLE-PILAR (no existia en el paquete):
# centroid u[9.85,10.15] v[20.12,20.42] -> centro (10.0,20.27), 0.30x0.30 m, bajo la
# viga de borde v=20.57 (u[9.70,17.79]) del voladizo norte (plano 2017_67-102).
# Misma convencion vertical que el resto de columnas P2: base=forjado P1, top=P2.
P2_ADD = [
    {
        "id": "COL_EI_CP2_RLE_PILAR_10.00_20.27",
        "grid": "B",
        "seccion": "0.30 x 0.30 (huella RLE-PILAR 2017_67-102)",
        "ancho": 0.3,
        "peralte": 0.3,
        "estado_seccion": "confirmado",
        "posicion": [10.0, 3.91, 20.27],
        "nota": "Incorporada desde huella fisica RLE-PILAR (u[9.85,10.15] v[20.12,20.42]) "
                "del plano 2017_67-102.dxf. Seccion geometrica demostrada por la huella; "
                "material/perfil asumido por el modelo: sin perfil inventado, acero del "
                "voladizo norte (convencion de las demas columnas P2)".strip(),
    },
]

# --- Marco de acero I'-J entre forjados (+7.87 P3 / +11.83 P4), elevacion 800 ---------- #
# Nodos aprobados por el usuario con "adoptar huellas exactas" (RLE-PILAR piso4_103):
#   I'=44.9190 (viga de piso existente + columna C_Ip de hormigon -> NO se duplican)
#   M =47.4558 (montante: NUEVA columna por eje)
#   J =49.7935 (vertical extremo: NUEVA columna por eje)
#   filas de eje v = 0.2811 / 9.1348 / 16.3472 (RLE-EJES piso4_103).
# Topologia elev 800: vigas +7.87 y +11.83 = vigas de piso ya modeladas (V.60/80) en
# P3/P4 (usa B1-B4 existentes); vertical I' = C_Ip existente; se añaden SOLO los
# miembros sin representacion: columnas M (montante) y J (vertical) + diagonales
# D1: [I' inf -> M sup] y D2: [J inf -> M sup]. Geometria de viewer, recibe_losa=false,
# sin FE/tributaria (mismo patron P2_ADD_BEAMS).
P4_FRAME_AXES_V = [0.2811, 9.1348, 16.3472]
P4_FRAME_U = {"I": 44.9190, "M": 47.4558, "J": 49.7935}
P4_FRAME_COTA_INF = 7.87
P4_FRAME_COTA_SUP = 11.83

P4_ADD_MARCO_COLS = [
    {
        "id": "COL_EI_CP4_S_M%d_47.4558" % (i + 1),
        "seccion": "P.M. 300x300x20 (huella piso4_103)",
        "ancho": 0.3,
        "peralte": 0.3,
        "estado_seccion": "confirmado",
        "posicion": [P4_FRAME_U["M"], P4_FRAME_COTA_SUP, v],
        "eje": "M-%d" % (i + 1),
        "nota": "Montante intermedio del marco I'-J (elev 800, entre +7.87 y +11.83). "
                "Huella fisica RLE-PILAR piso4_103 u[47.3066,47.6050] centro 47.4558, "
                "v=%.4f. Geometria de viewer respaldada por huella; sin FE/tributaria." % v,
        "edificio": "I",
        "nivel": "P4",
    }
    for (i, v) in enumerate(P4_FRAME_AXES_V)
]

P4_ADD_MARCO_COLS += [
    {
        "id": "COL_EI_CP4_S_J%d_49.7935" % (i + 1),
        "seccion": "P.M. 300x300x20 (huella piso4_103)",
        "ancho": 0.3,
        "peralte": 0.3,
        "estado_seccion": "confirmado",
        "posicion": [P4_FRAME_U["J"], P4_FRAME_COTA_SUP, v],
        "eje": "J-%d" % (i + 1),
        "nota": "Vertical extremo J del marco I'-J (elev 800, entre +7.87 y +11.83). "
                "Huella fisica RLE-PILAR piso4_103 u[49.6443,49.9428] centro 49.7935, "
                "v=%.4f. Geometria de viewer respaldada por huella; sin FE/tributaria." % v,
        "edificio": "I",
        "nivel": "P4",
    }
    for (i, v) in enumerate(P4_FRAME_AXES_V)
]

P4_ADD_MARCO_DIAGS = [
    {
        "id": "D_EI_CP4_L800_D1_EJ%d_44.919-47.456" % (i + 1),
        "seccion": "Diag. marco I'-J (elev 800)",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[P4_FRAME_U["I"], P4_FRAME_COTA_INF, v],
                [P4_FRAME_U["M"], P4_FRAME_COTA_SUP, v]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Diagonal D1 del marco I'-J (elev 800): nudo inferior I' (u=44.9190, "
                "+7.87) -> nudo superior intermedio M (u=47.4558, +11.83), eje v=%.4f. "
                "Geometria de viewer desde elevacion lamina 800 (sin huella en planta); "
                "sin FE/tributaria." % v,
    }
    for (i, v) in enumerate(P4_FRAME_AXES_V)
]

P4_ADD_MARCO_DIAGS += [
    {
        "id": "D_EI_CP4_L800_D2_EJ%d_49.793-47.456" % (i + 1),
        "seccion": "Diag. marco I'-J (elev 800)",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[P4_FRAME_U["J"], P4_FRAME_COTA_INF, v],
                [P4_FRAME_U["M"], P4_FRAME_COTA_SUP, v]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Diagonal D2 del marco I'-J (elev 800): nudo inferior J (u=49.7935, "
                "+7.87) -> nudo superior intermedio M (u=47.4558, +11.83), eje v=%.4f. "
                "Geometria de viewer desde elevacion lamina 800 (sin huella en planta); "
                "sin FE/tributaria." % v,
    }
    for (i, v) in enumerate(P4_FRAME_AXES_V)
]

# Vigas del voladizo norte P2 agregadas SOLO como geometria de viewer, agrupando las
# caras paralelas RLE-VIGA del plano 2017_67-102 en un unico miembro prismatico de
# ancho 0.60 (eje = punto medio de las caras). Seccion adoptada del modelo ("V. 60/80",
# la etiqueta del plano no es legible). NO se incorporan al FE ni a tributaria
# (recibe_losa=false). Extremos tomados de las intersecciones del DXF (sin inventar).
P2_ADD_BEAMS = [
    {
        "id": "H_EI_CP2_y2027_10.30-17.79_PLA2017-102",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[10.30, 3.91, 20.27], [17.79, 3.91, 20.27]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P2",
        "nota": "Viga de borde norte voladizo P2, eje v=20.27 entre caras RLE-VIGA "
                "v=19.97 y v=20.57 (u[10.30,17.79]); geometria de viewer desde plano "
                "2017_67-102, sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP2_x1000_16.50-20.57_PLA2017-102",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[10.00, 3.91, 16.50], [10.00, 3.91, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P2",
        "nota": "Apoyo/cabeza de pilar OESTE del voladizo P2, eje u=10.00 entre caras "
                "RLE-VIGA u=9.70 y u=10.30 (v[16.50,20.57]); geometria de viewer desde "
                "plano 2017_67-102, sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP2_x1749_16.45-19.97_PLA2017-102",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[17.49, 3.91, 16.45], [17.49, 3.91, 19.97]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P2",
        "nota": "Apoyo/cabeza de pilar ESTE del voladizo P2, eje u=17.49 entre caras "
                "RLE-VIGA u=17.19 y u=17.79 (v[16.45,19.97]); geometria de viewer desde "
                "plano 2017_67-102, sin FE/tributaria. La pareja u=17.34/17.64 (0.30) es "
                "la propia columna G3S1, no una viga.",
    },
]
# P4 (plano 2017_67-103): centros de huella u[19.85,20.15]x v[20.30,20.60] y
# u[29.85,30.15]x v[20.30,20.60] (0.30x0.30 m = P.M. 300x300x20).
P4_RELOC_COLS = {
    "COL_EI_CP4_S_GS6_21.5": ((20.0, 20.45), "huella u[19.85,20.15] v[20.30,20.60]"),
    "COL_EI_CP4_S_HS7_31.55": ((30.0, 20.45), "huella u[29.85,30.15] v[20.30,20.60]"),
}

# --- Torre G-H (losas L_EI_CP3_324 / L_EI_CP4_426, u=20-30): marco documentado ----- #
# Aprobado por el usuario (2026-09-06, 'mantener + anadir marco'). Las losas aisladas
# del sector norte u[20,30] son losas estructurales reales (rotulos/espesores 324=15cm
# y 426=12cm en los planos) y el plano dibuja el marco RLE-VIGA cerrado de 4 lados mas
# anillo y verticales que las envuelve exactamente (P3 2017_67-102 banda inferior:
# v=16.45 sur, v=19.97 norte, anillo v=20.57, verticales u=19.70/20.30/29.70/30.30;
# P4 2017_67-103: v=16.63, v=20.15, anillo v=20.75, mismas verticales). RLE-PROYECCION
# confirma las 4 lineas de columna de acero (u=19.85/20.15/29.85/30.15, v=16.50-20.12
# P3 / v=16.68 P4) y las huellas P.M. en las esquinas de la torre. Se agregan SOLO los
# miembros sin representacion como geometria de viewer (recibe_losa=false, sin
# FE/tributaria, mismo patron P2_ADD_BEAMS): viga norte, anillo y las 4 verticales.
# Apoyos sur (H_..._y0162 + columnas u=20/30) ya existen en los JSON; las columnas
# P.M. GS6/HS7 de P4 ya estan modeladas (no se duplican sus vanos 19.85/20.15/...).
TORRE_G_H_P3 = [
    {
        "id": "H_EI_CP3_y1997_20.30-29.70",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[20.30, 7.87, 19.97], [29.70, 7.87, 19.97]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P3",
        "nota": "Viga de borde NORTE de la losa torre L_EI_CP3_324, eje v=19.97 entre "
                "caras RLE-VIGA (u[20.30,29.70]); geometria de viewer desde plano "
                "2017_67-102 (banda P3), sin FE/tributaria.",
    },
    {
        "id": "H_EI_CP3_y2057_19.70-30.30",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[19.70, 7.87, 20.57], [30.30, 7.87, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P3",
        "nota": "Anillo superior de la torre (cubierta L_EI_CP3_324), eje v=20.57 "
                "(u[19.70,30.30]); geometria de viewer desde plano 2017_67-102 "
                "(banda P3), sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP3_x1970_16.45-20.57",
        "seccion": "V.M. 300x300x5",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[19.70, 7.87, 16.45], [19.70, 7.87, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P3",
        "nota": "Vertical OESTE cierre torre (perimetro caja G-H), eje u=19.70 entre "
                "v=16.45 y el anillo v=20.57; geometria de viewer desde plano "
                "2017_67-102 (banda P3), sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP3_x2030_16.45-20.57",
        "seccion": "V.M. 300x300x5",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[20.30, 7.87, 16.45], [20.30, 7.87, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P3",
        "nota": "Vertical interior G de la torre, eje u=20.30 entre v=16.45 y el "
                "anillo v=20.57; geometria de viewer desde plano 2017_67-102 "
                "(banda P3), sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP3_x2970_16.45-20.57",
        "seccion": "V.M. 300x300x5",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[29.70, 7.87, 16.45], [29.70, 7.87, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P3",
        "nota": "Vertical interior H de la torre, eje u=29.70 entre v=16.45 y el "
                "anillo v=20.57; geometria de viewer desde plano 2017_67-102 "
                "(banda P3), sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP3_x3030_16.45-20.57",
        "seccion": "V.M. 300x300x5",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[30.30, 7.87, 16.45], [30.30, 7.87, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P3",
        "nota": "Vertical ESTE cierre torre (perimetro caja G-H), eje u=30.30 entre "
                "v=16.45 y el anillo v=20.57; geometria de viewer desde plano "
                "2017_67-102 (banda P3), sin FE/tributaria.",
    },
]

TORRE_G_H_P4 = [
    {
        "id": "H_EI_CP4_y2015_20.30-29.70",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[20.30, 11.83, 20.15], [29.70, 11.83, 20.15]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Viga de borde NORTE de la losa torre L_EI_CP4_426, eje v=20.15 entre "
                "caras RLE-VIGA (u[20.30,29.70]); geometria de viewer desde plano "
                "2017_67-103, sin FE/tributaria.",
    },
    {
        "id": "H_EI_CP4_y2057_19.70-30.30",
        "seccion": "V. 60/80",
        "ancho": 0.6,
        "peralte": 0.8,
        "pts": [[19.70, 11.83, 20.57], [30.30, 11.83, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Anillo superior de la torre (cubierta L_EI_CP4_426), eje v=20.57 "
                "(u[19.70,30.30]); nivel P4 corregido al plano vertical de P3 "
                "(1946-09-07, lamina 801/802: el +0.18 m del plano no es del marco "
                "vertical), geometria de viewer, sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP4_x1970_16.45-20.57",
        "seccion": "V.M. 300x300x5",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[19.70, 11.83, 16.45], [19.70, 11.83, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Vertical OESTE cierre torre (perimetro caja G-H), eje u=19.70 entre "
                "v=16.45 y el anillo v=20.57; nivel P4 corregido al plano vertical de "
                "P3 (lamina 801/802, sin desplazamiento +0.18 en elevacion), geometria "
                "de viewer, sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP4_x2030_16.45-20.57",
        "seccion": "V.M. 300x300x5",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[20.30, 11.83, 16.45], [20.30, 11.83, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Vertical interior G de la torre, eje u=20.30 entre v=16.45 y el "
                "anillo v=20.57; nivel P4 corregido al plano vertical de P3 (lamina "
                "801/802), geometria de viewer, sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP4_x2970_16.45-20.57",
        "seccion": "V.M. 300x300x5",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[29.70, 11.83, 16.45], [29.70, 11.83, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Vertical interior H de la torre, eje u=29.70 entre v=16.45 y el "
                "anillo v=20.57; nivel P4 corregido al plano vertical de P3 (lamina "
                "801/802), geometria de viewer, sin FE/tributaria.",
    },
    {
        "id": "V_EI_CP4_x3030_16.45-20.57",
        "seccion": "V.M. 300x300x5",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[30.30, 11.83, 16.45], [30.30, 11.83, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Vertical ESTE cierre torre (perimetro caja G-H), eje u=30.30 entre "
                "v=16.45 y el anillo v=20.57; nivel P4 corregido al plano vertical de "
                "P3 (lamina 801/802), geometria de viewer, sin FE/tributaria.",
    },
]

# --- Torre G-H: cruces X del marco vertical entre +7.87 y +11.83 (L801/L802) --- #
# Marco vertical del voladizo lateral de la torre (u=20-30). Las laminas de detalle
# 801 y 802 dibujan los paneles X (arriostramiento) del tramo entre forjados
# P3(+7.87) y P4(+11.83): vano lateral RECTANGULAR 4.12 m x 3.96 m, diagonal con
# pendiente |m|=0.961 (angulo 43.87/136.13 en el DXF: m=3.96/4.12 y su inversa 1.040,
# que es 1/0.961). Verificado con ezdxf en 2017_67-801.dxf / 2017_67-802.dxf.
# Se modelan SOLO las dos caras laterales (OESTE u=19.70 y ESTE u=30.30) como cruces X
# (2 diagonales por cara, 4 totales), como geometria de viewer (recibe_losa=false,
# mismo patron P4_ADD_MARCO_DIAGS / P2_ADD_BEAMS). Los extremos se anclan EXACTAMENTE a
# los nodos del marco TORRE_G_H_P3/P4 ya modelado:
#   P3 (+7.87): verticales V_EI_CP3_x1970/x3030 entre v=16.45(apoyo sur) y v=20.57(anillo).
#   P4 (+11.83): V_EI_CP4_x1970/x3030 entre v=16.45(apoyo sur) y v=20.57(anillo),
#                 CORREGIDOS al plano vertical de P3 (el plano 103 del forjado P4 esta
#                 desplazado +0.18 m en v, pero las elevaciones 801/802 NO muestran ese
#                 desplazamiento: el panel es un rectangulo 4.12x3.96 m, |m|=0.961).
# Por ello las dos diagonales del X son identicas en pendiente |m|=0.961 (una '/' y una
# '\'), L=5.714 m = sqrt(4.12^2+3.96^2). No se copian las diagonales D1/D2 del marco
# I'-J (L800) ni las inferiores de L800; no se tocan losas 324/426, columnas, marcos
# horizontales ni FE.
TORRE_G_H_P34_DIAGS = [
    {
        "id": "TOWER_DIAG_P3_P4_WEST_1970_1645-2057_D1",
        "seccion": "Diag. torre G-H (lamina 801/802)",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[19.70, 7.87, 16.45], [19.70, 11.83, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Diagonal '/' del panel X de la cara lateral OESTE de la torre G-H "
                "(L801/L802): nudo P3 apoyo sur v=16.45 (+7.87, inicio V_EI_CP3_x1970) -> "
                "nudo P4 anillo v=20.57 (+11.83, final V_EI_CP4_x1970 / inicio "
                "H_EI_CP4_y2057). L=5.714 m, m=0.961 (panel RECTANGULAR 4.12x3.96 m "
                "segun laminas 801/802; marco P4 corregido al plano de P3, sin el +0.18 m "
                "del plano en elevacion; DXF m=0.961/1.040). "
                "Geometria de viewer, sin FE/tributaria.",
    },
    {
        "id": "TOWER_DIAG_P3_P4_WEST_1970_1645-2057_D2",
        "seccion": "Diag. torre G-H (lamina 801/802)",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[19.70, 11.83, 16.45], [19.70, 7.87, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Diagonal '\\' del panel X de la cara lateral OESTE de la torre G-H "
                "(L801/L802): nudo P4 apoyo sur v=16.45 (+11.83, inicio V_EI_CP4_x1970) -> "
                "nudo P3 anillo v=20.57 (+7.87, final V_EI_CP3_x1970 / inicio "
                "H_EI_CP3_y2057). L=5.714 m, m=-0.961 (panel RECTANGULAR 4.12x3.96 m "
                "segun laminas 801/802; marco P4 corregido al plano de P3). "
                "Geometria de viewer, sin FE/tributaria.",
    },
    {
        "id": "TOWER_DIAG_P3_P4_EAST_3030_1645-2057_D1",
        "seccion": "Diag. torre G-H (lamina 801/802)",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[30.30, 7.87, 16.45], [30.30, 11.83, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Diagonal '/' del panel X de la cara lateral ESTE de la torre G-H "
                "(L801/L802): nudo P3 apoyo sur v=16.45 (+7.87, inicio V_EI_CP3_x3030) -> "
                "nudo P4 anillo v=20.57 (+11.83, final V_EI_CP4_x3030 / inicio "
                "H_EI_CP4_y2057). L=5.714 m, m=0.961 (panel RECTANGULAR 4.12x3.96 m "
                "segun laminas 801/802; marco P4 corregido al plano de P3). "
                "Geometria de viewer, sin FE/tributaria.",
    },
    {
        "id": "TOWER_DIAG_P3_P4_EAST_3030_1645-2057_D2",
        "seccion": "Diag. torre G-H (lamina 801/802)",
        "ancho": 0.3,
        "peralte": 0.3,
        "pts": [[30.30, 11.83, 16.45], [30.30, 7.87, 20.57]],
        "recibe_losa": False,
        "edificio": "I",
        "nivel": "P4",
        "nota": "Diagonal '\\' del panel X de la cara lateral ESTE de la torre G-H "
                "(L801/L802): nudo P4 apoyo sur v=16.45 (+11.83, inicio V_EI_CP4_x3030) -> "
                "nudo P3 anillo v=20.57 (+7.87, final V_EI_CP3_x3030 / inicio "
                "H_EI_CP3_y2057). L=5.714 m, m=-0.961 (panel RECTANGULAR 4.12x3.96 m "
                "segun laminas 801/802; marco P4 corregido al plano de P3). "
                "Geometria de viewer, sin FE/tributaria.",
    },
]

# Marco y diagonales de la torre P4 generados en una corrida previa con el forjado P4
# desplazado +0.18 m (v=16.63->20.75). Reemplazados por TORRE_G_H_P4 / 
# TORRE_G_H_P34_DIAGS corregidos al plano vertical de P3 (v=16.45->20.57, |m|=0.961).
# Se eliminan por id para que no queden piezas huerfanas/duplicadas (idempotente).
TORRE_G_H_P4_RETIRAR = [
    "H_EI_CP4_y2075_19.70-30.30",
    "V_EI_CP4_x1970_16.63-20.75",
    "V_EI_CP4_x2030_16.63-20.75",
    "V_EI_CP4_x2970_16.63-20.75",
    "V_EI_CP4_x3030_16.63-20.75",
]
TORRE_G_H_P34_DIAGS_RETIRAR = [
    "TOWER_DIAG_P3_P4_WEST_1970_1645-2075",
    "TOWER_DIAG_P3_P4_WEST_1970_1663-2057",
    "TOWER_DIAG_P3_P4_EAST_3030_1645-2075",
    "TOWER_DIAG_P3_P4_EAST_3030_1663-2057",
]

# --- Lateral ESTE: recorte de losas a la cara exterior de la viga perimetral ---- #
# Decision del usuario (2026-09-06), respaldo DXF:
#   * P3/P4: el contorno RLE-LOSA del plano llega a u=51.15/51.037 pero la viga
#     perimetral este (concreto) termina en u=50.20 (P3) / 50.09 (P4, RLE-VIGA
#     piso4_103). La franja u~51 es la PROYECCION del marco metalico I'-J (ya
#     aprobado como estructura, no como losa de piso). Se RECORTA la losa a la
#     cara exterior de la viga este: P3 50.20, P4 50.09.
#   * P1/P2: se RESPETA el contorno del plano (RLE-LOSA 45.35); no se recorta.
#   * Solo lateral este: este paso no toca bandas oeste/sur/norte; las bandas SUR
#     continuas v<0 se ELIMINAN completas en FRANJAS_SUR_ELIMINAR (no aqui).
# Umbral de la verificacion automatica: falla si una losa (no voladizo documentado)
# supera la cara exterior de la viga perimetral este en > 0.01 m.
EAST_RECORTE = {
    # nivel: {id_losa: (limite_u_nuevo, dxf_ref)}
    # 2026-09-06: vacio. Las losas que antes se recortaban al lateral este
    # (P3 D_VOLADIZO_ALTO_LENGUA, P4 D_VOLADIZO_ALTO_ESTE) ahora se ELIMINAN COMPLETAS
    # por validacion visual (ver PIEZAS_FUERA_ELIMINAR); no queda ninguna a recortar.
}

# Limite de la cara exterior de la viga perimetral este por nivel (frame comun u),
# para la verificacion automatica. SOLO se verifica P3/P4, donde la geometria fue
# corregida contra la cara de la viga este: 
#   * P1/P2 respetan el contorno del plano (RLE-LOSA 45.35); no se recortan y quedan
#     fuera del chequeo (D_ATRIO_ESTE de P1 es un alero respaldado por CONTORNOS DXF).
#   * CP1S no tiene bandas este; sus losas de ancho completo (p.ej. D_SUPERIOR a
#     u=21.25) son losa de piso del sector sur, no franjas de fachada este.
EAST_FACE_LIMIT = {"P3": 50.20, "P4": 50.09}

# Excepciones a la verificacion (de solo lectura): aleros respaldados por el plano
# que exceden la viga perimetral este pero NO son franjas artificiales. Ejemplo
# D_ATRIO_ESTE de P1: el CONTORNOS DXF (u=45.545, v[-11.5,-3.5]) muestra el contorno
# del alero del atrio este, apoyado en muros M_EI_CP1_003/004.
EAST_VERIFY_SKIP = {
    "L_EI_CP1_D_ATRIO_ESTE": "atrio este alero (CONTORNOS DXF u=45.545)",
}

# --- FRANJAS SUR CONTINUAS (v<0): ELIMINACION COMPLETA -------------------------- #
# Correccion de criterio del usuario (2026-09-06): en el lateral sur el edificio
# termina en las vigas perimetrales (v=0 en P1/P2/P3, v=0 en P4 al 0.18 de la viga).
# Las bandas continuas v[-1.15,0] (P4 v[-0.97,0]) NO son voladizos reales: no forman
# parte de la geometria a representar a pesar de su nombre 'VOLADIZO' heredado/generado.
# Se ELIMINAN COMPLETAS (no se recorta ni se reduce a una banda menor). Su diafragma
# derivado '*_DIAF' se genera en el viewer a partir de la losa (LabLoader.BuildSlabs,
# id = refr.Id + '_DIAF'), por lo que desaparece en cascada al eliminar la losa.
FRANJAS_SUR_ELIMINAR = {
    "P1": ["L_EI_CP1_D_SUP_OESTE_VOL"],
    "P2": ["L_EI_CP2_D_VOLADIZO_EXTERIOR_EJE_1"],
    "P3": ["L_EI_CP3_D_VOLADIZO_BAJO"],
    "P4": ["L_EI_CP4_D_VOLADIZO_BAJO"],
}

# --- PIEZAS AISLADAS FUERA DE LA HUELLA PRINCIPAL: ELIMINACION COMPLETA ---------- #
# Validacion visual del usuario (2026-09-06): cuatro piezas quedan aisladas fuera de
# la huella principal (v>16.15, sector norte) y NO representan voladizos reales.
# Se ELIMINAN COMPLETAS (no recorte a banda menor). Su '*_DIAF' derivado desaparece
# en cascada (se genera en runtime desde la losa). No se toca el marco metalico
# I'-J (columnas/diagonales: elementos VIGA/COLUMNA, no losas).
PIEZAS_FUERA_ELIMINAR = {
    "P2": ["L_EI_CP2_221", "L_EI_CP2_220"],
    "P3": ["L_EI_CP3_315", "L_EI_CP3_D_VOLADIZO_ALTO_LENGUA"],
    "P4": ["L_EI_CP4_D_VOLADIZO_ALTO_ESTE"],
}


def _in_footprint(u):
    return any(lo <= u <= hi for lo, hi in P4_PHYSICAL_FOOTPRINTS_U)


def _reclasificar(cols, steel_ids, footprints, nivel, dxf_ref):
    """Reclasifica como 'por_resolver' (RefPendientes) las columnas metalicas del paquete
    cuyo id esta en `steel_ids` y cuya u no cae en ninguna huella fisica del plano.
    Idempotente: si ya es por_resolver no hace nada. Devuelve n_reclasificadas."""
    changed = 0
    for c in cols:
        if c.get("id") not in steel_ids:
            continue
        if c.get("estado_seccion") == "por_resolver":
            continue
        u = c.get("posicion", [0, 0, 0])[0] if c.get("posicion") else 0.0
        c["seccion"] = "P.M.I. (RLE-TEXTO-1, sin huella en planta)"
        c["ancho"] = 0.0
        c["peralte"] = 0.0
        c["estado_seccion"] = "por_resolver"
        footprint = any(lo <= u <= hi for lo, hi in footprints)
        c["nota"] = (c.get("nota", "") +
                     " | RECLASAFICADA (aplicacion planos): u=%.2f no cae en ninguna "
                     "huella fisica de columna de acero del plano %s (u en %s; RLE-PILAR %s). "
                     "Dentro_huella=%s." %
                     (u, nivel,
                      ", ".join("%.2f-%.2f" % t for t in footprints),
                      dxf_ref, footprint))
        changed += 1
    return changed


def _reubicar(cols, reloc, nivel, dxf_ref):
    """Reubica una columna existente sobre el centro de su huella fisica RLE-PILAR
    (mantiene seccion/estado y conserva cota). Idempotente."""
    changed = 0
    for c in cols:
        if c.get("id") not in reloc:
            continue
        (u_t, v_t), huella_s = reloc[c["id"]]
        pos = c.get("posicion") or [0, 0, 0]
        if abs((pos[0] or 0) - u_t) < 1e-6 and abs((pos[2] or 0) - v_t) < 1e-6:
            continue
        c["posicion"] = [round(u_t, 6), pos[1], round(v_t, 6)]
        c["nota"] = (c.get("nota", "") +
                     " | REUBICADA (%s): (%.2f,%.2f)->(%.2f,%.2f) sobre huella "
                     "RLE-PILAR %s (plano %s)." %
                     (nivel, pos[0], pos[2], u_t, v_t, huella_s, dxf_ref))
        changed += 1
    return changed


def _eliminar_losas(losas, ids):
    """Elimina losas del paquete por id. Idempotente. Devuelve n_eliminadas."""
    antes = len(losas)
    losas[:] = [l for l in losas if l.get("id") not in ids]
    return antes - len(losas)


def _eliminar_vigas(vigas, ids):
    """Elimina vigas del paquete por id. Idempotente. Devuelve n_eliminadas."""
    antes = len(vigas)
    vigas[:] = [v for v in vigas if v.get("id") not in ids]
    return antes - len(vigas)


def _agregar(cols, nuevos):
    """Inserta columnas nuevas (por id) si aun no existen en el paquete. Idempotente."""
    existing = {c.get("id") for c in cols}
    added = 0
    for n in nuevos:
        if n["id"] in existing:
            continue
        cols.append(dict(n))
        added += 1
    return added


def _recortar_este(losas, limite):
    """Recorta una losa del lateral este a la cara exterior de la viga perimetral:
    mueve cualquier vertice con u > limite a u = limite (los poligonos son
    rectangulos; los dos vertices del borde este comparten u_max). Idempotente:
    si ya todos los u <= limite no cambia nada. Devuelve (recortadas, vertices).
    """
    changed = 0
    moves = 0
    for l in losas:
        if any(p[0] > limite + 1e-6 for p in l.get("poligono", [])):
            for p in l["poligono"]:
                if p[0] > limite:
                    old = p[0]
                    p[0] = round(limite, 6)
                    if abs(old - p[0]) > 1e-9:
                        moves += 1
            changed += 1
    return changed, moves


def verify_lateral_este(out: Path, eps: float = 0.01) -> list:
    """Verifica que ninguna losa supere la cara exterior de la viga perimetral
    este por mas de `eps` metros. Devuelve lista de fallos (id, u_max, limite).
    Idempotente y de solo lectura: no modifica los JSON."""
    fails = []
    for lvl, limite in EAST_FACE_LIMIT.items():
        fn = out / ("%s.json" % lvl)
        if not fn.exists():
            continue
        d = json.load(open(fn, encoding="utf-8-sig"))
        for l in d.get("losas", []):
            if l.get("id") in EAST_VERIFY_SKIP:
                continue
            umax = max(p[0] for p in l["poligono"])
            if umax > limite + eps:
                fails.append((lvl, l.get("id"), umax, limite))
    return fails


def verify_franjas_sur(out: Path) -> dict:
    """Verificacion de solo lectura: confirma que ninguna losa de FRANJAS_SUR_ELIMINAR
    permanece en los JSON (ni derivada '*_DIAF', que en el viewer se genera desde la
    losa). Devuelve {nivel: ids_todavia_presentes}. Vacia => correcto."""
    return _residual_franjas(out, FRANJAS_SUR_ELIMINAR)


def verify_piezas_fuera(out: Path) -> dict:
    """Verificacion de solo lectura de PIEZAS_FUERA_ELIMINAR (mismas reglas:
    losa base o su '*_DIAF' derivado no deben permanecer en los JSON)."""
    return _residual_franjas(out, PIEZAS_FUERA_ELIMINAR)


def _residual_franjas(out: Path, elim: dict) -> dict:
    """Busca en cada nivel si algun id de `elim` (o su derivado '<id>_DIAF') sigue
    presente entre las losas. Devuelve {nivel: [ids_presentes]}."""
    present = {}
    for lvl, ids in elim.items():
        fn = out / ("%s.json" % lvl)
        if not fn.exists():
            continue
        d = json.load(open(fn, encoding="utf-8-sig"))
        residual = []
        for i in ids:
            if any(l.get("id") in (i, i + "_DIAF") for l in d.get("losas", [])):
                residual.append(i)
        if residual:
            present[lvl] = residual
    return present


def apply_correction(out: Path | str | None = None) -> dict:
    """Aplica las correcciones P1-P4 del paquete. Devuelve resumen {nivel: info}."""
    target = Path(out) if out else OUT
    summary = {}
    d4 = target / "P4.json"
    if not d4.exists():
        summary["P4"] = "SKIP (no existe P4.json)"
    else:
        d = json.load(open(d4, encoding="utf-8-sig"))
        n_losas_antes = len(d.get("losas", []))
        n_fr = _eliminar_losas(d.get("losas", []), FRANJAS_SUR_ELIMINAR.get("P4", []))
        n_pf = _eliminar_losas(d.get("losas", []), PIEZAS_FUERA_ELIMINAR.get("P4", []))
        n_mov = _reubicar(d.get("columnas", []), P4_RELOC_COLS, "P4", "2017_67-103.dxf")
        n_rec = _reclasificar(d.get("columnas", []), P4_STEEL, P4_PHYSICAL_FOOTPRINTS_U,
                              "P4", "piso4_103.dxf")
        n_mc = _agregar(d.get("columnas", []), P4_ADD_MARCO_COLS)
        n_md = _agregar(d.get("vigas", []), P4_ADD_MARCO_DIAGS)
        n_ret_torre = _eliminar_vigas(d.get("vigas", []), TORRE_G_H_P4_RETIRAR)
        n_ret_diag = _eliminar_vigas(d.get("vigas", []), TORRE_G_H_P34_DIAGS_RETIRAR)
        n_tu = _agregar(d.get("vigas", []), TORRE_G_H_P4)
        n_td = _agregar(d.get("vigas", []), TORRE_G_H_P34_DIAGS)
        rec_no = rec_pasos = 0
        for lid, (lim, _dxf) in EAST_RECORTE.get("P4", {}).items():
            losa = next((l for l in d.get("losas", []) if l.get("id") == lid), None)
            if losa is not None:
                cnt, mv = _recortar_este([losa], lim)
                rec_no += cnt
                rec_pasos += mv
                if cnt:
                    losa["nota"] = (losa.get("nota", "") +
                                    " | RECORTADA lateral este: u_max -> %.3f (%s)." % (lim, _dxf))
        json.dump(d, open(d4, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P4"] = {"reubicadas": n_mov, "reclasificadas": n_rec,
                         "marco_columnas": n_mc, "marco_diagonales": n_md,
                         "torre_retiradas": n_ret_torre,
                         "torre_diag_retiradas": n_ret_diag,
                         "torre_vigas": n_tu, "torre_diagonales_X": n_td,
                         "lateral_este_recortadas": rec_no,
                         "lateral_este_vertices": rec_pasos,
                         "franjas_sur_eliminadas": n_fr,
                         "piezas_fuera_eliminadas": n_pf,
                         "losas_antes": n_losas_antes,
                         "losas_despues": len(d["losas"]),
                         "total_columnas": len(d["columnas"]),
                         "total_vigas": len(d["vigas"])}
    d3 = target / "P3.json"
    if not d3.exists():
        summary["P3"] = "SKIP (no existe P3.json)"
    else:
        d = json.load(open(d3, encoding="utf-8-sig"))
        n_losas_antes = len(d.get("losas", []))
        n_fr = _eliminar_losas(d.get("losas", []), FRANJAS_SUR_ELIMINAR.get("P3", []))
        n_pf = _eliminar_losas(d.get("losas", []), PIEZAS_FUERA_ELIMINAR.get("P3", []))
        n_tor = _agregar(d.get("vigas", []), TORRE_G_H_P3)
        changed = _reclasificar(d.get("columnas", []), P3_STEEL, P3_PHYSICAL_FOOTPRINTS_U,
                                "P3", "2017_67-102.dxf (banda P3)")
        rec_no = rec_pasos = 0
        for lid, (lim, _dxf) in EAST_RECORTE.get("P3", {}).items():
            losa = next((l for l in d.get("losas", []) if l.get("id") == lid), None)
            if losa is not None:
                cnt, mv = _recortar_este([losa], lim)
                rec_no += cnt
                rec_pasos += mv
                if cnt:
                    losa["nota"] = (losa.get("nota", "") +
                                    " | RECORTADA lateral este: u_max -> %.3f (%s)." % (lim, _dxf))
        json.dump(d, open(d3, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P3"] = {"reclasificadas": changed,
                         "torre_vigas": n_tor,
                         "lateral_este_recortadas": rec_no,
                         "lateral_este_vertices": rec_pasos,
                         "franjas_sur_eliminadas": n_fr,
                         "piezas_fuera_eliminadas": n_pf,
                         "losas_antes": n_losas_antes,
                         "losas_despues": len(d["losas"]),
                         "total_columnas": len(d["columnas"])}
    d2 = target / "P2.json"
    if not d2.exists():
        summary["P2"] = "SKIP (no existe P2.json)"
    else:
        d = json.load(open(d2, encoding="utf-8-sig"))
        n_losas_antes = len(d.get("losas", []))
        n_fr = _eliminar_losas(d.get("losas", []), FRANJAS_SUR_ELIMINAR.get("P2", []))
        n_pf = _eliminar_losas(d.get("losas", []), PIEZAS_FUERA_ELIMINAR.get("P2", []))
        n_mov = _reubicar(d.get("columnas", []), P2_RELOC_COLS, "P2", "2017_67-102.dxf (banda P2)")
        n_add = _agregar(d.get("columnas", []), P2_ADD)
        n_b = _agregar(d.get("vigas", []), P2_ADD_BEAMS)
        json.dump(d, open(d2, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P2"] = {"reubicadas": n_mov, "agregadas": n_add,
                         "vigas_agregadas": n_b,
                         "franjas_sur_eliminadas": n_fr,
                         "piezas_fuera_eliminadas": n_pf,
                         "losas_antes": n_losas_antes,
                         "losas_despues": len(d["losas"]),
                         "total_columnas": len(d["columnas"]),
                         "total_vigas": len(d["vigas"])}
    d1 = target / "P1.json"
    if not d1.exists():
        summary["P1"] = "SKIP (no existe P1.json)"
    else:
        d = json.load(open(d1, encoding="utf-8-sig"))
        n_losas_antes = len(d.get("losas", []))
        n_elim = _eliminar_losas(d.get("losas", []), P1_REMOVE_LOSAS)
        n_fr = _eliminar_losas(d.get("losas", []), FRANJAS_SUR_ELIMINAR.get("P1", []))
        json.dump(d, open(d1, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary["P1"] = {"losas_eliminadas": n_elim, "franjas_sur_eliminadas": n_fr,
                         "losas_antes": n_losas_antes,
                         "losas_despues": len(d["losas"]),
                         "total_columnas": len(d["columnas"])}
    # Verificacion automatica del lateral este: falla si alguna losa supera la cara
    # exterior de la viga perimetral este por mas de 0.01 m (salvo P1/P2 45.35 del plano).
    fails = verify_lateral_este(target)
    summary["verify_lateral_este"] = ("OK (%d niveles)" % len(EAST_FACE_LIMIT)) if not fails else \
        "\n".join("FALLO %s %s u_max=%.3f > limite %.2f+0.01" % f for f in fails)
    # Verificacion de que ninguna franja sur permanece (ni su '_DIAF' derivada).
    residual = verify_franjas_sur(target)
    summary["verify_franjas_sur"] = ("OK (4 niveles, franjas ausentes)") if not residual else \
        ("PRESENTES: " + "; ".join("%s=%s" % (k, v) for k, v in residual.items()))
    # Verificacion de que ninguna pieza aislada permanece (ni su '_DIAF' derivada).
    residual_pf = verify_piezas_fuera(target)
    summary["verify_piezas_fuera"] = ("OK (3 niveles, piezas ausentes)") if not residual_pf else \
        ("PRESENTES: " + "; ".join("%s=%s" % (k, v) for k, v in residual_pf.items()))
    return summary


if __name__ == "__main__":
    print(apply_correction())
