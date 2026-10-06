"""Solver de verificacion: replica en numpy/scipy de las funciones de OpenSeesPy que usa el proyecto.

NO es OpenSees. Reproduce elasticBeamColumn 3D (Euler-Bernoulli) y ElasticTimoshenkoBeam (con corte),
geomTransf Linear, fix, rigidDiaphragm (metodo de transformacion), cargas nodales y eleLoad -beamUniform,
analisis estatico lineal y modal (eigen). Se valido contra corridas reales de OpenSees del proyecto:
desplazamientos con diferencias del orden de 1e-10 m, fuerzas de 1e-4 kN y los mismos periodos.

Solo se usa si openseespy no se puede importar y el usuario lo pide (MCOC_REPLICA=1, que Unity
activa con la casilla "calcular con el solver de verificacion"). Los resultados quedan marcados con
motor = replica en la trazabilidad del JSON. La corrida oficial del proyecto se hace con OpenSees.
"""
import math
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import scipy.linalg as sla

__version__ = "0.0.0+replica.verificacion"
_S = {}


def wipe(*a):
    _S.clear()
    _S.update(nodes={}, fix={}, transf={}, elems={}, diaph=[], mass={}, nload={}, eload={}, res=None, eig=None)


wipe()


def model(*a, **k): pass
def constraints(*a, **k): pass
def numberer(*a, **k): pass
def system(*a, **k): pass
def integrator(*a, **k): pass
def algorithm(*a, **k): pass
def analysis(*a, **k): pass
def timeSeries(*a, **k): pass
def pattern(*a, **k): pass
def reactions(*a, **k): pass
def uniaxialMaterial(*a, **k): pass
def section(*a, **k): pass
def patch(*a, **k): pass
def layer(*a, **k): pass


def wipeAnalysis(*a):
    _S["res"] = None
    _S["eig"] = None


def node(tag, x, y, z, *a):
    _S["nodes"][int(tag)] = (float(x), float(y), float(z))


def fix(tag, *flags):
    old = _S["fix"].get(int(tag), [0] * 6)
    _S["fix"][int(tag)] = [max(int(o), int(f)) for o, f in zip(old, list(flags) + [0] * (6 - len(flags)))]


def geomTransf(kind, tag, *vec):
    _S["transf"][int(tag)] = tuple(float(v) for v in vec[:3])


def element(kind, tag, ni, nj, *args):
    if kind == "ElasticTimoshenkoBeam":      # E G A Jx Iy Iz Avy Avz transf
        E, G, A, J, Iy, Iz, Avy, Avz, transf = args[:9]
    else:                                    # elasticBeamColumn: A E G J Iy Iz transf
        A, E, G, J, Iy, Iz, transf = args[:7]; Avy = Avz = None
    _S["elems"][int(tag)] = (int(ni), int(nj), float(A), float(E), float(G), float(J), float(Iy), float(Iz), int(transf),
                             None if Avy is None else float(Avy), None if Avz is None else float(Avz))


def rigidDiaphragm(perp, master, *slaves):
    _S["diaph"].append((int(master), [int(s) for s in slaves]))


def mass(tag, *m):
    _S["mass"][int(tag)] = [float(v) for v in m] + [0.0] * (6 - len(m))


def load(tag, *vals):
    acc = _S["nload"].setdefault(int(tag), [0.0] * 6)
    for k, v in enumerate(vals[:6]):
        acc[k] += float(v)


def eleLoad(*args):
    a = list(args)
    i = a.index("-ele"); eids = []
    j = i + 1
    while j < len(a) and not (isinstance(a[j], str) and a[j].startswith("-")):
        eids.append(int(a[j])); j += 1
    t = a.index("-beamUniform")
    w = [float(v) for v in a[t + 1:t + 4]] + [0.0] * (3 - len(a[t + 1:t + 4]))
    for e in eids:
        acc = _S["eload"].setdefault(e, [0.0, 0.0, 0.0])
        for k in range(3):
            acc[k] += w[k]          # (wy, wz, wx)


def _axes(pi, pj, vecxz):
    d = np.array(pj) - np.array(pi); L = float(np.linalg.norm(d)); x = d / L
    v = np.array(vecxz)
    y = np.cross(v, x); y /= np.linalg.norm(y)
    z = np.cross(x, y)
    return np.array([x, y, z]), L


def _klocal(A, E, G, J, Iy, Iz, L, Avy=None, Avz=None):
    py = 12 * E * Iz / (G * Avy * L * L) if Avy else 0.0      # Timoshenko (0 = Euler-Bernoulli)
    pz = 12 * E * Iy / (G * Avz * L * L) if Avz else 0.0
    k = np.zeros((12, 12))
    a = E * A / L; t = G * J / L
    k[0, 0] = k[6, 6] = a; k[0, 6] = k[6, 0] = -a
    k[3, 3] = k[9, 9] = t; k[3, 9] = k[9, 3] = -t
    z1, z2 = 12 * E * Iz / (L**3 * (1 + py)), 6 * E * Iz / (L**2 * (1 + py))
    z3, z4 = (4 + py) * E * Iz / (L * (1 + py)), (2 - py) * E * Iz / (L * (1 + py))
    k[1, 1] = k[7, 7] = z1; k[1, 7] = k[7, 1] = -z1
    k[1, 5] = k[5, 1] = k[1, 11] = k[11, 1] = z2; k[7, 5] = k[5, 7] = k[7, 11] = k[11, 7] = -z2
    k[5, 5] = k[11, 11] = z3; k[5, 11] = k[11, 5] = z4
    y1, y2 = 12 * E * Iy / (L**3 * (1 + pz)), 6 * E * Iy / (L**2 * (1 + pz))
    y3, y4 = (4 + pz) * E * Iy / (L * (1 + pz)), (2 - pz) * E * Iy / (L * (1 + pz))
    k[2, 2] = k[8, 8] = y1; k[2, 8] = k[8, 2] = -y1
    k[2, 4] = k[4, 2] = k[2, 10] = k[10, 2] = -y2; k[8, 4] = k[4, 8] = k[8, 10] = k[10, 8] = y2
    k[4, 4] = k[10, 10] = y3; k[4, 10] = k[10, 4] = y4
    return k


def _ensamblar():
    ids = sorted(_S["nodes"]); idx = {n: i for i, n in enumerate(ids)}; nd = 6 * len(ids)
    r, c, v = [], [], []; info = {}
    for e, (ni, nj, A, E, G, J, Iy, Iz, tr, Avy, Avz) in _S["elems"].items():
        R, L = _axes(_S["nodes"][ni], _S["nodes"][nj], _S["transf"][tr])
        T = np.kron(np.eye(4), R); kl = _klocal(A, E, G, J, Iy, Iz, L, Avy, Avz); kg = T.T @ kl @ T
        dofs = [6 * idx[ni] + d for d in range(6)] + [6 * idx[nj] + d for d in range(6)]
        r += [a for a in dofs for _ in dofs]; c += dofs * 12; v += list(kg.ravel())
        info[e] = (dofs, T, kl, L, R)
    K = sp.csr_matrix((v, (r, c)), shape=(nd, nd))
    fixed = {6 * idx[n] + d for n, fl in _S["fix"].items() if n in idx for d in range(6) if fl[d]}
    slave = {}
    for m, ss in _S["diaph"]:
        for s in ss:
            slave[s] = m
    col = {}
    for n in ids:
        for d in range(6):
            g = 6 * idx[n] + d
            if g in fixed or (n in slave and d in (0, 1, 5)):
                continue
            col[g] = len(col)
    rr, cc, vv = list(col.keys()), list(col.values()), [1.0] * len(col)
    for s, m in slave.items():
        (xs, ys, _), (xm, ym, _) = _S["nodes"][s], _S["nodes"][m]
        gs, gm = 6 * idx[s], 6 * idx[m]
        rr += [gs, gs, gs + 1, gs + 1, gs + 5]
        cc += [col[gm], col[gm + 5], col[gm + 1], col[gm + 5], col[gm + 5]]
        vv += [1.0, -(ys - ym), 1.0, (xs - xm), 1.0]
    Tc = sp.csr_matrix((vv, (rr, cc)), shape=(nd, len(col)))
    return ids, idx, K, Tc, info, fixed


def analyze(n=1, *a):
    ids, idx, K, Tc, info, fixed = _ensamblar()
    nd = 6 * len(ids); F = np.zeros(nd); feq = {}
    for nn, vals in _S["nload"].items():
        if nn in idx:
            F[6 * idx[nn]:6 * idx[nn] + 6] += vals
    for e, (wy, wz, wx) in _S["eload"].items():
        if e not in info:
            continue
        dofs, T, kl, L, R = info[e]
        fe = np.array([wx * L / 2, wy * L / 2, wz * L / 2, 0, -wz * L**2 / 12, wy * L**2 / 12,
                       wx * L / 2, wy * L / 2, wz * L / 2, 0, wz * L**2 / 12, -wy * L**2 / 12])
        feq[e] = fe
        F[dofs] += T.T @ fe
    Kr = (Tc.T @ K @ Tc).tocsc()
    u = Tc @ spla.spsolve(Kr, Tc.T @ F)
    Rf = K @ u - F
    _S["res"] = dict(ids=ids, idx=idx, u=u, R=Rf, fixed=fixed, info=info, feq=feq)
    return 0


def nodeDisp(tag, dof=None):
    res = _S["res"]; i = res["idx"][int(tag)]
    vals = list(res["u"][6 * i:6 * i + 6])
    return vals if dof is None else vals[int(dof) - 1]


def nodeReaction(tag, dof=None):
    res = _S["res"]; i = res["idx"][int(tag)]
    vals = [float(res["R"][6 * i + d]) if (6 * i + d) in res["fixed"] else 0.0 for d in range(6)]
    return vals if dof is None else vals[int(dof) - 1]


def eleResponse(tag, *what):
    res = _S["res"]; dofs, T, kl, L, R = res["info"][int(tag)]
    f = kl @ (T @ res["u"][dofs]) - res["feq"].get(int(tag), 0)
    return list(f)


def eigen(*args):
    nmod = int(args[-1])
    ids, idx, K, Tc, info, fixed = _ensamblar()
    nd = 6 * len(ids); md = np.zeros(nd)
    for nn, m in _S["mass"].items():
        if nn in idx:
            md[6 * idx[nn]:6 * idx[nn] + 6] = m
    Kr = (Tc.T @ K @ Tc).tocsc(); Mr = (Tc.T @ sp.diags(md) @ Tc).tocsc()
    dg = np.abs(Mr.diagonal()); con = np.where(dg > 1e-14)[0]; sin = np.where(dg <= 1e-14)[0]
    Kcs = Kr[con][:, sin]; lu = spla.splu(Kr[sin][:, sin].tocsc()); X = lu.solve(Kcs.T.toarray())
    Kc = Kr[con][:, con].toarray() - Kcs @ X; Mc = Mr[con][:, con].toarray()
    lam, phi = sla.eigh(Kc, Mc, subset_by_index=[0, nmod - 1])
    vecs = []
    for k in range(nmod):
        vr = np.zeros(Kr.shape[0]); vr[con] = phi[:, k]; vr[sin] = -X @ phi[:, k]
        vecs.append(Tc @ vr)
    _S["eig"] = dict(idx=idx, vecs=vecs)
    return [float(x) for x in lam]


def nodeEigenvector(tag, mode, dof=None):
    e = _S["eig"]; i = e["idx"][int(tag)]
    vals = list(e["vecs"][int(mode) - 1][6 * i:6 * i + 6])
    return vals if dof is None else vals[int(dof) - 1]
