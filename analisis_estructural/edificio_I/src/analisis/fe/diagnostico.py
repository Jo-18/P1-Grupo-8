"""Diagnostico independiente de mecanismos: ensambla K 3D del marco (scipy) y
aplica las mismas restricciones que OpenSees (base fija, rigidDiaphragm,
rigidLink beam) por sustitucion, para identificar el espacio nulo (mecanismos)
en terminos de nodos y grados de libertad fisicos.

NO se usan apoyos artificiales: solo base fija + diafragma rigido + enlace rigido
excentrico documentado. Sirve para responder "cual componente/grado de libertad
es singular" de forma independiente de OpenSees.
"""

from __future__ import annotations

import math

import numpy as np

from . import geometria_fe as GF
from .marco import Marco
from . import secciones as SEC


def local_K(sec, L):
    E = sec["E"]; A = sec["A"]; Iz = sec["Iz"]; Iy = sec["Iy"]
    G = sec["G"]; J = sec["J"]
    eal = E * A / L; gj = G * J / L
    k = np.zeros((12, 12))
    k[0, 0] = eal; k[0, 6] = -eal; k[6, 0] = -eal; k[6, 6] = eal
    k[3, 3] = gj; k[3, 9] = -gj; k[9, 3] = -gj; k[9, 9] = gj
    # bending about local z (in-plane x-y): DOFs y(1,7) rot z(5,11)
    vz = 6 * E * Iz / L ** 2
    k[1, 1] = 12 * E * Iz / L ** 3; k[1, 5] = vz; k[1, 7] = -12 * E * Iz / L ** 3; k[1, 11] = vz
    k[5, 1] = vz; k[5, 5] = 4 * E * Iz / L; k[5, 7] = -vz; k[5, 11] = 2 * E * Iz / L
    k[7, 1] = -12 * E * Iz / L ** 3; k[7, 5] = -vz; k[7, 7] = 12 * E * Iz / L ** 3; k[7, 11] = -vz
    k[11, 1] = vz; k[11, 5] = 2 * E * Iz / L; k[11, 7] = -vz; k[11, 11] = 4 * E * Iz / L
    # bending about local y (out-of-plane x-z): DOFs z(2,8) rot y(4,10)
    voy = 6 * E * Iy / L ** 2
    k[2, 2] = 12 * E * Iy / L ** 3; k[2, 4] = -voy; k[2, 8] = -12 * E * Iy / L ** 3; k[2, 10] = -voy
    k[4, 2] = -voy; k[4, 4] = 4 * E * Iy / L; k[4, 8] = voy; k[4, 10] = 2 * E * Iy / L
    k[8, 2] = -12 * E * Iy / L ** 3; k[8, 4] = voy; k[8, 8] = 12 * E * Iy / L ** 3; k[8, 10] = voy
    k[10, 2] = -voy; k[10, 4] = 2 * E * Iy / L; k[10, 8] = voy; k[10, 10] = 4 * E * Iy / L
    return k


def global_T(vec, xa, xb):
    L = np.linalg.norm(xb - xa)
    if L < 1e-9:
        return np.eye(3)
    xAxis = (xb - xa) / L
    ref = np.array(vec, float)
    if abs(np.dot(xAxis, ref)) > 0.9999:
        ref = np.array([0, 1, 0]) if abs(xAxis[1]) > 0.9999 else np.array([0, 0, 1])
    zAxis = np.cross(xAxis, ref)
    zAxis = zAxis / np.linalg.norm(zAxis)
    yAxis = np.cross(zAxis, xAxis)
    return np.vstack([xAxis, yAxis, zAxis])


def _vec_for(rec):
    dx = rec["u_j"] - rec["u_i"]; dy = rec["v_j"] - rec["v_i"]; dz = rec["z_j"] - rec["z_i"]
    if abs(dz) > 1e-3 or (abs(dx) < 1e-6 and abs(dy) < 1e-6):
        return (0, 1, 0)
    return (0, 0, 1)


def _resolver_seccion(rec):
    # preferir la seccion EXACTA que uso OpenSees (E,A,Iz,Iy,G,J almacenadas en el
    # registro por marco._elem al construir). Evita el bug de resolver por el
    # rotulo 'V'/'C' que NO trae la dimension -> rigidez nula espuria.
    if rec.get("sec_valores") is not None:
        return rec["sec_valores"]
    import re
    if rec["tipo"] == "viga":
        return SEC.seccion_viga(rec["seccion"])
    if rec["tipo"] == "columna":
        return SEC.seccion_columna(rec["seccion"])
    mm = re.search(r"M ([0-9.]+)x([0-9.]+)x2", str(rec["elemento_id"]))
    if mm:
        return SEC.seccion_muro(float(mm.group(1)), float(mm.group(2)))
    return None


def ensamblar_K(marco):
    tags = sorted(marco.nodes.values())
    idx = {t: i for i, t in enumerate(tags)}
    nd = len(tags)
    K = np.zeros((nd * 6, nd * 6))
    for rec in marco.columnas + marco.vigas_elem + marco.muros_elem:
        i = int(rec["nodo_i"]); j = int(rec["nodo_j"])
        xi = np.array([rec["u_i"], rec["v_i"], rec["z_i"]])
        xj = np.array([rec["u_j"], rec["v_j"], rec["z_j"]])
        L = np.linalg.norm(xj - xi)
        sec = _resolver_seccion(rec)
        if sec is None or L < 1e-9:
            continue
        kl = local_K(sec, L)
        C = global_T(_vec_for(rec), xi, xj)
        Z = np.zeros((3, 3))
        Tbig = np.block([[C, Z, Z, Z], [Z, C, Z, Z], [Z, Z, C, Z], [Z, Z, Z, C]])
        Kg = Tbig.T @ kl @ Tbig
        ii = idx[i]; jj = idx[j]
        K[ii*6:ii*6+6, ii*6:ii*6+6] += Kg[0:6, 0:6]
        K[ii*6:ii*6+6, jj*6:jj*6+6] += Kg[0:6, 6:12]
        K[jj*6:jj*6+6, ii*6:ii*6+6] += Kg[6:12, 0:6]
        K[jj*6:jj*6+6, jj*6:jj*6+6] += Kg[6:12, 6:12]
    return K, tags, idx


def mecanismos(marco, max_report=25):
    K, tags, idx = ensamblar_K(marco)
    nd = len(tags)
    full_grid = {}
    for t in tags:
        for d in range(6):
            full_grid[(t, d)] = t * 0  # placeholder

    # Columna de DOFs independientes: todos salvo base fija.
    fixed = set(marco._base_fixed)
    all_dofs = [(t, d) for t in tags for d in range(6)]
    independent = [(t, d) for t in tags for d in range(6) if t not in fixed]

    full_dof = nd * 6
    flist = [(t, d) for t in tags for d in range(6)]
    fmap = {dof: i for i, dof in enumerate(flist)}

    def coords(t):
        x, y, z = marco.key_of_tag[t]
        return np.array([x, y, z])

    # 1) Diafragma rigido: us = um - thz*dy ; vs = vm + thz*dx ; rotz igual.
    #    Se usan LOS MISMOS esclavos que el modelo ejecutado
    #    (marco.diafragma_esclavos_por_nivel), que EXCLUYE los extremos excentricos
    #    P1 (429/430). Esos extremos NO son esclavos de diafragma en el modelo
    #    resuelto: su acoplamiento al piso se modela con conectores rigidos de barra
    #    (ya incluidos en K via marco.vigas_elem), por lo que NO llevan restriccion
    #    rigidLink anidada (representacion corregida, compatible con Transformation).
    #
    # 2) Enlaces rigidos REALES que aun existen en el modelo resuelto (conectores
    #    del portico del cielo del subterraneo CP1S): sus esclavos conservan la
    #    restriccion rigidLink('beam', columna, extremo) porque su maestro es una
    #    columna ordinaria (CP1S NO tiene diafragma, luego no hay cadena anidada).
    #    Los pares registrados como "stub_elastico_rigidez_elevada" (P1) NO generan
    #    restriccion: el conector corto elastico ya esta dentro de K (ensamblar_K lo
    #    incluye via marco.vigas_elem con las propiedades EFECTIVAS E*mult, G*mult
    #    guardadas en sec_valores).
    constrains = []
    for cod, master in marco.master_por_nivel.items():
        for s in marco.diafragma_esclavos_por_nivel.get(cod, []):
            xm, ym, _ = coords(master)
            xs, ys, _ = coords(s)
            dx, dy = xs - xm, ys - ym
            for (sd, terms) in [(0, [(master, 1.0, 0), (master, -dy, 5)]),
                                (1, [(master, 1.0, 1), (master, dx, 5)]),
                                (5, [(master, 1.0, 5)])]:
                constrains.append((s, sd, terms))

    for link in getattr(marco, "rigid_links_info", []):
        if link.get("tipo") in ("stub_elastico_rigido", "stub_elastico_rigidez_elevada"):
            continue  # P1: representado por conector corto en K (sin restriccion)
        ms = int(link["col_tag"]); sl = int(link["beam_tag"])
        msub = marco.key_of_tag.get(ms)
        ssub = marco.key_of_tag.get(sl)
        if msub is None or ssub is None:
            continue
        xm, ym, zm = msub
        xs, ys, zs = ssub
        rx, ry, rz = xs - xm, ys - ym, zs - zm
        constrains.append((sl, 0, [(ms, 1.0, 0), (ms, rz, 4), (ms, -ry, 5)]))
        constrains.append((sl, 1, [(ms, 1.0, 1), (ms, rx, 5), (ms, -rz, 3)]))
        constrains.append((sl, 2, [(ms, 1.0, 2), (ms, ry, 3), (ms, -rx, 4)]))
        constrains.append((sl, 3, [(ms, 1.0, 3)]))
        constrains.append((sl, 4, [(ms, 1.0, 4)]))
        constrains.append((sl, 5, [(ms, 1.0, 5)]))

    Q, n_free = reducir(marco, constrains, flist, fmap)
    if n_free == 0:
        # todos los DOFs estan fijos o restringidos: sistema trivialmente estable
        return {"n_dof_total": full_dof, "n_independientes": 0,
                "n_fijos": len(fixed), "rank": 0, "nullity": 0, "modos_top": []}
    Kr = Q.T @ K @ Q
    Kr = (Kr + Kr.T) / 2
    # Escalado de Jacobi: se divide fila/columna por la raiz del termino diagonal
    # para anular el efecto del contraste de rigidez (miembros muy rigidos vs muy
    # flexibles) en la tolerancia de rango. Los mecanismos verdaderos dan un valor
    # singular ~0 RELATIVO a 1 de la matriz escalada; el resto (deformaciones
    # pequenas pero no nulas) quedan lejos de cero.
    d = np.diag(Kr)
    d_safe = np.where(d > 0, d, 1.0)
    scale = np.sqrt(d_safe)
    Dinv = np.diag(1.0 / scale)
    Krn = Dinv @ Kr @ Dinv
    s = np.linalg.svd(Krn, compute_uv=False)
    tol = 1e-8 * max(s.max(), 1.0e-12)
    rank = int(np.sum(s > tol))
    nullity = Krn.shape[0] - rank

    resumen_modos = []
    if nullity > 0 and nullity <= max_report:
        ns = np.linalg.svd(Kr)[0][:, rank:]
        for m in range(ns.shape[1]):
            qv = ns[:, m]
            full = Q @ qv
            mag = np.zeros(nd)
            for (t, d), fi in fmap.items():
                mag[idx[t]] += full[fi] ** 2
            top = np.argsort(-mag)[:4]
            det = [{"tag": int(tags[ti]), "coord": [round(x, 3) for x in marco.key_of_tag[tags[ti]]],
                    "mag": round(float(math.sqrt(mag[ti])), 4)} for ti in top]
            resumen_modos.append(det)
    return {"n_dof_total": full_dof, "n_independientes": n_free,
            "n_fijos": len(fixed), "rank": rank, "nullity": nullity,
            "modos_top": resumen_modos}


def reducir(marco, constrains, flist, fmap):
    """DOFs restringidos -> combinacion lineal de los maestros; se ELIMINAN las
    columnas de los DOFs esclavos (quedan solo los independientes libres), de modo
    que Q es 'alta' (full_dof x n_free) y Kr = Q^T K Q tiene el rango correcto."""
    tags = sorted(marco.nodes.values())
    fixed = set(marco._base_fixed)
    # DOF que se dejan como incognitas libres: todos salvo base fija y esclavos.
    slave_set = set((sn, sd) for (sn, sd, _) in constrains)
    free = [(t, d) for t in tags for d in range(6)
            if t not in fixed and (t, d) not in slave_set]
    fcol = {dof: i for i, dof in enumerate(free)}
    n_free = len(free)
    full_dof = len(flist)
    Q = np.zeros((full_dof, n_free))
    for (t, d), i in fcol.items():
        Q[fmap[(t, d)], i] = 1.0
    # filas de esclavos: combinacion lineal de las filas de sus maestros (ya en Q).
    for (sn, sd, terms) in constrains:
        row = np.zeros(n_free)
        for (ts, coef, td) in terms:
            row += coef * Q[fmap[(ts, td)], :]
        Q[fmap[(sn, sd)], :] = row
    return Q, n_free
