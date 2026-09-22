# -*- coding: utf-8 -*-
"""
S05 - Evidencia 2: DEMANDA-CAPACIDAD DINAMICA bajo superposicion.

El punto P-M del panel (Semana 5) se recalcula EN VIVO con la misma convencion del
paquete: P = max(compresion N_i, N_j) (+), M = max(|My_i|,|Mz_i|,|My_j|,|Mz_j|),
M_u(P) interpolada en la curva de capacidad y D/C = M/M_u. Este script lo replica
sobre el vector superpuesto (lam del caso gobernante) y lo compara contra la fila
exportada de pm_capacidad_demanda_I.json para TODOS los elementos demostrables.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
RES = os.path.join(ROOT, "viewer_unity", "Assets", "StreamingAssets", "lab_data",
                   "edificios", "I", "results")
P_E = os.path.join(RES, "esfuerzos_FE_EDIFICIO_I.json")
P_PM = os.path.join(RES, "pm_capacidad_demanda_I.json")

PRESETS = {
    "U1_GQ":     (1.2, 1.6, 0.0, 0.0),
    "U2_EX_POS": (1.2, 1.0, 1.4, 0.0),
    "U2_EX_NEG": (1.2, 1.0, -1.4, 0.0),
    "U3_EY_POS": (1.2, 1.0, 0.0, 1.4),
    "U3_EY_NEG": (1.2, 1.0, 0.0, -1.4),
    "U4_EX_POS": (0.9, 0.0, 1.4, 0.0),
    "U4_EX_NEG": (0.9, 0.0, -1.4, 0.0),
    "U4_EY_POS": (0.9, 0.0, 0.0, 1.4),
    "U4_EY_NEG": (0.9, 0.0, 0.0, -1.4),
}
BASES = ["G", "Q", "EX", "EY"]

def mu_para_n(curva, p):
    n_list = curva["N_kN"]
    m_list = curva["M_kN_m"]
    if p <= n_list[0]:
        return m_list[0]
    if p >= n_list[-1]:
        return m_list[-1]
    for a in range(1, len(n_list)):
        n0, n1 = n_list[a - 1], n_list[a]
        if n0 <= p <= n1:
            t = (p - n0) / (n1 - n0) if n1 != n0 else 0.0
            return m_list[a - 1] + t * (m_list[a] - m_list[a - 1])
    return float("nan")

def main():
    d = json.load(open(P_E, encoding="utf-8"))
    pm = json.load(open(P_PM, encoding="utf-8"))
    curva = pm["capacidad"]
    por_tag = {}
    for e in d["elementos"]:
        por_tag[str(e["tag"])] = e

    filas = list(pm["por_elemento"].values())
    compat = 0
    n_elem = 0
    max_dP = max_dM = max_dDC = 0.0
    n_fail = 0
    print("[S05-2] Archivo pm: " + os.path.relpath(P_PM, ROOT))
    print("[S05-2] Curva: N [%.0f..%.0f] kN, M [%.2f..%.2f] kN*m, seccion %s"
          % (curva["N_kN"][0], curva["N_kN"][-1],
             min(curva["M_kN_m"]), max(curva["M_kN_m"]), curva.get("seccion", "?")))
    print("-" * 72)
    for fila in filas:
        tag = str(fila["tag"])
        e = por_tag.get(tag)
        if e is None:
            continue
        caso = fila.get("caso")
        if caso not in PRESETS:
            continue
        n_elem += 1
        lam = PRESETS[caso]
        f = None
        for i, b in enumerate(BASES):
            fb = e["fuerzas"].get(b)
            if fb is None:
                break
            if f is None:
                f = [x * lam[i] for x in fb]
            else:
                f = [f[k] + fb[k] * lam[i] for k in range(12)]
        if f is None:
            continue

        # convencion del paquete sobre el vector superpuesto
        P = max(-f[0], -f[6], 0.0)                 # compresion (+) = -N cuando tension+ 
        M = max(abs(f[4]), abs(f[5]), abs(f[10]), abs(f[11]))
        Mu = mu_para_n(curva, P)
        DC = M / Mu if Mu > 0 else float("nan")

        dP = abs(P - fila["P_u_kN"])
        dM = abs(M - fila["M_demanda_kN_m"])
        dDC = abs(DC - fila["D_C"])
        max_dP = max(max_dP, dP)
        max_dM = max(max_dM, dM)
        max_dDC = max(max_dDC, dDC)
        ok = dP < 1e-2 and dM < 1e-1 and dDC < 1e-2
        if ok:
            compat += 1
        else:
            n_fail += 1
            print("  MISMATCH tag=%s caso=%s P %.2f/%.2f M %.2f/%.2f DC %.4f/%.4f"
                  % (tag, caso, P, fila["P_u_kN"], M, fila["M_demanda_kN_m"],
                     DC, fila["D_C"]))

    ok = n_fail == 0
    print("-" * 72)
    print("[S05-2] Elementos verificados: %d  (compatibles: %d, fallos: %d)"
          % (n_elem, compat, n_fail))
    print("[S05-2] max|diff| P=%.3e  M=%.3e  D/C=%.3e" % (max_dP, max_dM, max_dDC))
    print("[S05-2] RESULTADO: " +
          ("D/C DINAMICO == pm_capacidad_demanda para toda la curva "
           "(convencion de paquete replicada)" if ok else "DESVIACIONES"))
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()