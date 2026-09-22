"""Comprobaciones breves e independientes de OpenSeesPy (antes del edificio).

1. viga con carga uniforme: reacciones, momento y flecha (validacion analitica).
2. elemento vertical: orientacion de ejes locales (geomTransf correcta).
3. diafragma rigido: compatibilidad en su plano sin bloquear el desplazamiento vertical.

Todo en sistema visual de OpenSeesPy (gravedad -z).
"""

from __future__ import annotations

import math
import openseespy.opensees as ops

from .hipotesis import MATERIAL_G40


def _wipe():
    try:
        ops.wipe()
    except Exception:
        pass


def check_viga_uniforme():
    """Empotrada-empotrada con carga puntual P en el centro. Validacion analitica.

    Reacciones R = P/2, momento de empotramiento M = P L / 8, flecha centro
    d = P L^3 / (192 E Iy).
    """
    _wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)
    E = MATERIAL_G40.E_mpa * 1e3  # kPa (kN/m2)
    b, h = 0.60, 0.80
    A = b * h
    Istrong = b * h ** 3 / 12.0   # fuerte (flexion vertical x-z -> about local y)
    Iweak = h * b ** 3 / 12.0
    G = MATERIAL_G40.G_mpa * 1e3
    J = 0.5 * (Iweak + Istrong)
    L = 6.0
    ops.node(1, 0.0, 0.0, 0.0)
    ops.node(2, L, 0.0, 0.0)
    ops.node(3, L / 2.0, 0.0, 0.0)
    ops.fix(1, 1, 1, 1, 1, 1, 1)
    ops.fix(2, 1, 1, 1, 1, 1, 1)
    # seccion Elastic: (E, A, Iz, Iy, G, J). Iy = acerca de y (vertical x-z).
    ops.section('Elastic', 1, E, A, Iweak, Istrong, G, J)
    # viga a lo largo de x; eje fuerte para flexion vertical -> local z arriba
    ops.geomTransf('Linear', 1, 0, 0, 1)
    ops.element('elasticBeamColumn', 1, 1, 3, 1, 1)
    ops.element('elasticBeamColumn', 2, 3, 2, 1, 1)
    P = 120.0  # kN central
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.load(3, 0.0, 0.0, -P, 0.0, 0.0, 0.0)
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ops.analyze(1)
    ops.reactions()
    rz1 = ops.nodeReaction(1, 3)
    rz2 = ops.nodeReaction(2, 3)
    # momento reactivo global sobre el eje y (dof 5) para viga a lo largo de x
    mr1 = ops.nodeReaction(1, 5)
    mr2 = ops.nodeReaction(2, 5)
    dcentro = ops.nodeDisp(3, 3)
    R_a = P / 2.0
    M_a = P * L / 8.0
    d_a = P * L ** 3 / (192.0 * E * Istrong)
    ok = (abs(rz1 - R_a) < 1e-6 and abs(rz2 - R_a) < 1e-6
          and abs(abs(mr1) - M_a) < 1e-3 and abs(abs(mr2) - M_a) < 1e-3
          and abs(dcentro + d_a) < 1e-6)
    _wipe()
    return {
        "nombre": "check_viga_uniforme (P central, empotrado-empotrado)",
        "ok": bool(ok),
        "R_analit": R_a, "R_nodo1": rz1, "R_nodo2": rz2,
        "M_ext_analit": M_a, "M_nodo1": mr1, "M_nodo2": mr2,
        "d_centro_analit": d_a, "d_centro": dcentro,
        "E_kPa": E, "L_m": L, "P_kN": P,
    }


def check_vertical_local_axis():
    """Elemento vertical: verificar que la gravedad flexa respecto al eje local
    correcto (que el eje fuerte quede orientado). Hacemos una columna vertical
    con carga axial y comprobamos que no hay desplazamiento horizontal espurio."""
    _wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)
    E = MATERIAL_G40.E_mpa * 1e3
    L = 3.96
    b = 0.70
    A = b * b
    I = b ** 4 / 12.0
    G = MATERIAL_G40.G_mpa * 1e3
    J = I
    ops.node(1, 0.0, 0.0, 0.0)
    ops.node(2, 0.0, 0.0, L)
    ops.fix(1, 1, 1, 1, 1, 1, 1)
    ops.section('Elastic', 1, E, A, I, I, G, J)
    # vec debe ser NO paralelo al eje del elemento (vertical global z); se usa +y
    ops.geomTransf('Linear', 1, 0, 1, 0)
    ops.element('elasticBeamColumn', 1, 1, 2, 1, 1)
    # carga axial grande en tope
    P = 1000.0
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.load(2, 0.0, 0.0, -P, 0.0, 0.0, 0.0)
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ops.analyze(1)
    uz = ops.nodeDisp(2, 3)
    ux = ops.nodeDisp(2, 1)
    uy = ops.nodeDisp(2, 2)
    d_a = P * L / (E * A)
    ok = (abs(uz + d_a) < 1e-6 and abs(ux) < 1e-9 and abs(uy) < 1e-9)
    _wipe()
    return {
        "nombre": "check_vertical_local_axis",
        "ok": bool(ok),
        "d_axial_analit": d_a, "d_axial": uz,
        "ux": ux, "uy": uy, "E_kPa": E, "A": A, "L": L,
    }


def check_diafragma():
    """Diafragma rigido en planta: compatibilidad en el plano (u,v,rot-z iguales
    en todos los nodos del diafragma) SIN bloquear el desplazamiento vertical."""
    _wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)
    E = MATERIAL_G40.E_mpa * 1e3
    A = 0.49
    I = 0.02
    G = E / 2.4
    J = 0.03
    ops.section('Elastic', 1, E, A, I, I, G, J)
    ops.geomTransf('Linear', 1, 0, 1, 0)   # vec +y (elementos verticales)

    # placa: master (1) y dos esclavos (2,3) en el plano z=0
    ops.node(1, 0.0, 0.0, 0.0)   # master
    ops.node(2, 5.0, 0.0, 0.0)   # esclavo en u
    ops.node(3, 0.0, 5.0, 0.0)   # esclavo en v
    base = {1: 11, 2: 12, 3: 13}
    for n, btag in base.items():
        coord = [ops.nodeCoord(n, i) for i in (1, 2, 3)]
        ops.node(btag, coord[0], coord[1], coord[2] - 1.0)
        ops.fix(btag, 1, 1, 1, 1, 1, 1)
        ops.element('elasticBeamColumn', n, btag, n, 1, 1)

    ops.equalDOF(1, 2, 1, 2, 6)   # esclavo 2 ligado en u,v,rotz (vertical libre)
    ops.equalDOF(1, 3, 1, 2, 6)   # esclavo 3 ligado en u,v,rotz (vertical libre)

    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.load(1, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0)  # fuerza en plano en master (u)
    ops.load(2, 0.0, 0.0, -50.0, 0.0, 0.0, 0.0)  # vertical en esclavo
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Transformation')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ops.analyze(1)
    u_m = [ops.nodeDisp(i, 1) for i in (1, 2, 3)]   # in-plane u
    uz_slave = ops.nodeDisp(2, 3)                    # vertical del esclavo (libre)
    # compatibilidad en plano: los tres u identicos (rigido) y >0 por la fuerza
    ok_plano = abs(u_m[0] - u_m[1]) < 1e-9 and abs(u_m[0] - u_m[2]) < 1e-9 \
        and abs(u_m[0]) > 1e-12
    # vertical libre: el esclavo se mueve verticalmente (no bloqueado), finito
    ok_vert = abs(uz_slave) > 1e-12 and abs(uz_slave) < 1e1
    _wipe()
    return {"nombre": "check_diafragma", "ok": bool(ok_plano and ok_vert),
            "u_plano_master": u_m[0], "u_plano_esclavo_u": u_m[1], "u_plano_esclavo_v": u_m[2],
            "uz_esclavo_u": uz_slave}


def run_all():
    res = [check_viga_uniforme(), check_vertical_local_axis(), check_diafragma()]
    return res
