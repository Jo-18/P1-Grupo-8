# -*- coding: utf-8 -*-
"""
S05 - Evidencia 1: SUPERPOSICION LINEAL EXACTA con los sliders (G,Q,EX,EY).

El viewer (Semana 5) evalua la combinacion en vivo C = lamG*G + lamQ*Q + lamEX*EX
+ lamEY*EY por superposicion sobre los casos base del paquete. Como el modelo FE es
lineal elastico, esa combinacion DEBE reproducir exactamente la corrida explicita
exportada (U1_GQ, U2_*, U3_*, U4_*). Este script lo verifica para TODOS los
elementos y TODAS las componentes 12, y tambien sobre la deformada por nodo.

Tolerancia: |diff| <= atol (los JSON estan redondeados a ~1e-3/1e-5).
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PATH = os.path.join(ROOT, "viewer_unity", "Assets", "StreamingAssets", "lab_data",
                    "edificios", "I", "results", "esfuerzos_FE_EDIFICIO_I.json")

# Coeficientes (lamG, lamQ, lamEX, lamEY) identicos a CoefDePreset del viewer.
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

def combinar(fuerzas, lam):
    """Vector 12 = sum lam_i * f_base_i (None para elementos sin todas las bases)."""
    r = None
    for i, b in enumerate(BASES):
        l = lam[i]
        f = fuerzas.get(b)
        if f is None:
            return None
        if r is None:
            r = [x * l for x in f]
        else:
            r = [r[k] + f[k] * l for k in range(12)]
    return r

def main():
    d = json.load(open(PATH, encoding="utf-8"))
    elementos = d["elementos"]
    n_elem = len(elementos)
    print("[S05-1] Archivo: " + os.path.relpath(PATH, ROOT))
    print("[S05-1] Elementos: %d  |  bases: %s  |  combos: %d"
          % (n_elem, BASES, len(PRESETS)))
    print("-" * 72)

    total_max = 0.0
    fallos = 0
    for nombre, lam in sorted(PRESETS.items()):
        max_abs = 0.0
        max_rel = 0.0
        n_comp = 0
        n_fail = 0
        for e in elementos:
            fuerzas = e.get("fuerzas")
            if not fuerzas or nombre not in fuerzas:
                continue
            combo = combinar(fuerzas, lam)
            if combo is None:
                continue
            explicito = fuerzas[nombre]
            for k in range(12):
                diff = abs(combo[k] - explicito[k])
                n_comp += 1
                max_abs = max(max_abs, diff)
                rel = abs(diff / explicito[k]) if abs(explicito[k]) > 1e-9 else 0.0
                max_rel = max(max_rel, rel)
                if diff > 1e-2:
                    n_fail += 1
                    fallos += 1
        total_max = max(total_max, max_abs)
        estado = "OK" if n_fail == 0 else "FALLO(%d)" % n_fail
        print("  %-10s max|diff| = %.3e  max rel = %.3e  comps=%d  %s"
              % (nombre, max_abs, max_rel, n_comp, estado))

    # ---- verificacion sobre la DEFORMADA (por nodo, 6 comps) ----
    desp_caso = d["deformada"]["desplazamientos_por_caso"]
    max_desp = 0.0
    n_fail_d = 0
    n_comp_d = 0
    for nombre, lam in sorted(PRESETS.items()):
        if nombre not in desp_caso:
            continue
        for nodo, vd in desp_caso[nombre].items():
            acc = None
            for i, b in enumerate(BASES):
                l = lam[i]
                vb = desp_caso.get(b, {}).get(nodo)
                if vb is None:
                    acc = None
                    break
                if acc is None:
                    acc = [x * l for x in vb]
                else:
                    acc = [acc[k] + vb[k] * l for k in range(6)]
            if acc is None:
                continue
            for k in range(6):
                diff = abs(acc[k] - vd[k])
                n_comp_d += 1
                max_desp = max(max_desp, diff)
                if diff > 1e-5:
                    n_fail_d += 1
    estado_d = "OK" if n_fail_d == 0 else "FALLO(%d)" % n_fail_d
    print("-" * 72)
    print("[S05-1] Deformada por nodo: max|diff| = %.3e comps=%d %s"
          % (max_desp, n_comp_d, estado_d))

    ok = fallos == 0 and n_fail_d == 0
    print("-" * 72)
    print("[S05-1] RESULTADO: " + ("SUPERPOSICION LINEAL EXACTA -> "
                                   "los sliders reproducen las combinaciones NCh3171"
                                   if ok else "HAY DESVIACIONES, revisar tol/redondeo"))
    print("[S05-1] max|diff| global (fuerzas) = %.3e" % total_max)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()