"""Verificaciones post-remesh para Tarea 1.

Ejecutar:  python -X utf8 tests\verif_remesh_t1.py
"""
import sys, math
sys.path.insert(0, r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\P1\analisis_estructural\edificio_I\src")
sys.path.insert(0, r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\P1\entrega_03_cargas_sismo_capacidad")
import src.modelo_fiel.modelo_fe_completo as M
from analisis.fe.hipotesis import COTAS_NIVEL_M as COTAS

F = []
def check(name, ok, msg=""):
    F.append((name, bool(ok), msg)); print(("OK  " if ok else "FAIL") + " " + name + (f"  ({msg})" if msg else ""))

TOL = 0.02
def near(u, v, z, nodes):
    return [t for t in nodes
            if abs(t[0]-u)<=TOL and abs(t[1]-v)<=TOL and abs(t[2]-z)<=TOL]

marco = M.MarcoFECompleto(M.GF.cargar_todos())
marco.construir()
pre = marco.preflight()
nodes = marco.nodes          # _key -> tag
key = marco.key_of_tag       # tag -> coord

# --- 0. Preflight completo ---
check("preflight_ok", pre["ok"])

# --- 1. Sin fantasma poste_18.96_14.79_P4 (ni nodo ni elemento en P4) ---
check("sin_phantom_nodo", len(near(18.96, 14.79, COTAS["P4"], nodes)) == 0)
sur = [r for r in marco.columnas if "18.96_14.79" in r["elemento_id"]]
check("sin_phantom_elem", len(sur) == 0, str([r["elemento_id"] for r in sur]))

# --- 2. G3S1 remeshed: base y tope en (17.49,20.27) ---
g3base = near(17.49, 20.27, COTAS["P2"], nodes)
g3top  = near(17.49, 20.27, COTAS["P3"], nodes)
check("g3s1_base", len(g3base) == 1)
check("g3s1_tope_p3", len(g3top) == 1)
g3_col = [r for r in marco.columnas
          if "17.49_20.27" in r["elemento_id"] and "P3" in r["elemento_id"]]
check("g3s1_tramo_p2_p3", len(g3_col) == 1, g3_col[0]["elemento_id"] if g3_col else "")
check("g3s1_sin_p4", len(near(17.49, 20.27, COTAS["P4"], nodes)) == 0)

# --- 3. H_y2027: unico segmento (10,20.27)->(17.49,20.27) (encuentros) ---
e2027 = [r for r in marco.vigas_elem if "y2027" in r["elemento_id"]]
check("h_y2027_1_elem", len(e2027) == 1, f"n={len(e2027)}")
if e2027:
    a = key[int(e2027[0]["nodo_i"])]; b = key[int(e2027[0]["nodo_j"])]
    check("h_y2027_extremos", (a[0], b[1] if len(b)>1 else 0, b[2]) >= (0,0,0))
    check("h_y2027_a_10_20.27", abs(a[0]-10.0)<=TOL and abs(a[1]-20.27)<=TOL, str(a))
    check("h_y2027_b_17.49_20.27", abs(b[0]-17.49)<=TOL and abs(b[1]-20.27)<=TOL, str(b))
    check("h_y2027_vertical_cota", abs(a[2]-COTAS["P2"])<=TOL and abs(b[2]-COTAS["P2"])<=TOL)

# --- 4. V_x1749: (17.49,16.15)->(17.49,20.27); base subdivide la perimetral ---
check("perim_subdiv_node", len(near(17.49, 16.15, COTAS["P2"], nodes)) == 1)
v1749 = [r for r in marco.vigas_elem if "x1749" in r["elemento_id"]]
check("v_x1749_1_elem", len(v1749) == 1, f"n={len(v1749)}")
if v1749:
    a = key[int(v1749[0]["nodo_i"])]; b = key[int(v1749[0]["nodo_j"])]
    check("v_x1749_base", (abs(a[0]-17.49)<=TOL and abs(a[1]-16.15)<=TOL) or
                          (abs(b[0]-17.49)<=TOL and abs(b[1]-16.15)<=TOL), f"{a} {b}")
    check("v_x1749_topo_g3", (abs(a[0]-17.49)<=TOL and abs(a[1]-20.27)<=TOL) or
                             (abs(b[0]-17.49)<=TOL and abs(b[1]-20.27)<=TOL), f"{a} {b}")
# perimetral H_y0162 contiene nodo en u=17.49 (subdivision)
pe = [r for r in marco.vigas_elem if "y0162" in r["elemento_id"]]
pe_has = any(abs(key[int(r["nodo_i"])][0]-17.49)<=TOL or abs(key[int(r["nodo_j"])][0]-17.49)<=TOL for r in pe)
check("perimetral_subdividida_17.49", pe_has)

# --- 5. V_x1000 (10,16.15)->(10,20.27)->(10,20.57), toca F3 ---
tag_f3 = near(10.0, 16.15, COTAS["P2"], nodes)
check("v_x1000_f3_node", len(tag_f3) == 1)
v1000 = [r for r in marco.vigas_elem if "x1000" in r["elemento_id"]]
check("v_x1000_2_elems", len(v1000) == 2, f"n={len(v1000)}")
touch = any(int(r["nodo_i"]) in {nodes[k] for k in tag_f3}
            or int(r["nodo_j"]) in {nodes[k] for k in tag_f3} for r in v1000)
check("v_x1000_toca_f3", touch)
check("v_x1000_norte_2017", any(abs(key[int(r["nodo_i"])][1]-20.57)<=TOL
                                or abs(key[int(r["nodo_j"])][1]-20.57)<=TOL for r in v1000))

# --- 6. Pilar oeste = NODO (10,20.27): sin columna elemento en ese eje ---
col10 = [r for r in marco.columnas
         if abs(key[int(r["nodo_i"])][0]-10.0)<=TOL and abs(key[int(r["nodo_i"])][1]-20.27)<=TOL]
check("pilar_oeste_sin_columna", len(col10) == 0, str([r["elemento_id"] for r in col10]))
check("pilar_oeste_nodo_rigid", len(near(10.0, 20.27, COTAS["P2"], nodes)) == 1)

# --- 7. Sin stubs > 2.5 m ---
longs = max((math.dist(key[int(r["nodo_i"])], key[int(r["nodo_j"])])) for r in marco.stub_elem)
check("stubs_le_2.5m", longs <= 2.5 + 1e-6, f"max={longs:.3f}")

# --- 8. G3S1 apoyo directo en viga (sin stub), radio 0 ---
arr = [c for c in marco.conectores_arranque if tuple(c.get("eje")) == (17.49, 20.27)]
check("g3s1_apoyo_directo", len(arr) == 1 and arr[0].get("tipo") == "apoyo_directo_en_viga",
      str(arr))

# --- 9. 25 conectores_arranque ---
check("25_arranques", len(marco.conectores_arranque) == 25)

# --- 10. Remeshed P4 posts GS6/HS7 ---
for (uc, vc), vtgt in M.REMESH_TORRE.items():
    if vc == 21.03:
        check(f"remesh_p4_{uc}", len(near(*vtgt, COTAS["P4"], nodes)) == 1, str(vtgt))
        rem = [r for r in marco.columnas if "%s_%s_remate" % vtgt in r["elemento_id"]]
        check(f"remate_p4_{uc}", len(rem) == 1)

# --- 11. Sin continuacion P2->P3 / P3->P4 en el eje del pilar oeste ---
west = [r for r in marco.columnas
        if abs(key[int(r["nodo_i"])][0]-10.0)<=TOL and abs(key[int(r["nodo_i"])][1]-20.27)<=TOL]
check("oeste_sin_tramo", len(west) == 0, str([r["elemento_id"] for r in west]))

print("\nSUMMARY:", sum(1 for _, ok, _ in F if not ok), "failures /", len(F))