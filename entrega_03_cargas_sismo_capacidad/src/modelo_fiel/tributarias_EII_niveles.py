"""Motor de areas tributarias EII v5.

Replica el metodo validado en el ensayo EII_CP2 FASE4B:
 - malla regular de celdas (tamano_celda) sobre el dominio neto de cada panel;
 - paneles unidireccionales (corredores S/N): rayo p+lambda*u sobre segmentos
   receptores perpendiculares a u=(0,1), primer cruce en la direccion de la carga;
 - paneles por_definir: celda -> receptor (segmento finito viga/muro) MAS CERCANO,
   considerando SOLO los `apoyos_validos` declarados del panel;
 - renormalizacion por panel: factor = A_neta / Sigma(area_asignada);
 - por panel y receptor: area_tributaria_m2, ancho_promedio_m.

Solo vigas/muros; las columnas NO son receptores de losa en este modelo.

Genera (offline): data/externas/areas_tributarias_EII_todos_niveles.json
"""
from __future__ import annotations
import hashlib, json
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.prepared import prep
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
EX = E3 / "data" / "externas"
EII = EX / "eii_viewer.json"
CSV_CP2 = EX / "areas_tributarias.csv"
OUT = EX / "areas_tributarias_EII_todos_niveles.json"

TAMANO_CELDA = 0.05
RENORMALIZAR = True
GL = 1e-12


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def to_polygon(outer):
    return Polygon(outer)


def area_neta(losa_outer, aberturas):
    p = to_polygon(losa_outer)
    for a in aberturas:
        if p.intersects(a):
            p = p.difference(a)
    return p


def dist_seg(p, A, B):
    """|p-(A+t(B-A))|, t=clamp en [0,1], vectorizado sobre filas de p."""
    ab = B - A
    L2 = float(ab[0] ** 2 + ab[1] ** 2)
    t = (p[:, 0] * ab[0] + p[:, 1] * ab[1] - (A[0] * ab[0] + A[1] * ab[1])) / L2
    t = np.clip(t, 0.0, 1.0)
    q = A + t[:, None] * ab
    return np.hypot(p[:, 0] - q[:, 0], p[:, 1] - q[:, 1])


def es_unidireccional(pid):
    """Paneles corredor S/N: usan direccion de transferencia (0,1) segun FASE4B."""
    s = pid.split("_L_")[-1]
    return len(s) >= 2 and s[0] in ("S", "N") and s[1].isdigit()


def asignar_panel(pid, poligono_neta, apoyos, cell):
    """Celda -> apoyo. Si el panel es unidireccional (S/N): rayo p+lambda*u sobre
    segmentos perpendiculares a u=(0,1), primero que cruza. Si no: mas cercano."""
    minx, miny, maxx, maxy = poligono_neta.bounds
    xs = np.arange(minx or 0, maxx, cell) + cell / 2
    ys = np.arange(miny or 0, maxy, cell) + cell / 2
    P = np.array([[x, y] for y in ys for x in xs])
    pr = prep(poligono_neta)
    mask = np.array([pr.contains(Point(px, py)) for px, py in P])
    Pc = P[mask]
    n = Pc.shape[0]
    if n == 0:
        return {}
    ids = [a[0] for a in apoyos]
    segs = [a[1] for a in apoyos]
    if es_unidireccional(pid):
        u = np.array([0.0, 1.0])
        usigs = []
        for (A, B) in segs:
            d = np.array(B, float) - np.array(A, float)
            L = float(np.hypot(*d))
            d = d / L if L > 0 else d
            usigs.append(abs(d @ u))
        # compatibles: segmentos perpendiculares a u
        idx = np.where(np.array(usigs) <= 0.10)[0]
        if idx.size == 0:
            # sin apoyo alcanzable por el rayo: caida a mas cercano (reportado)
            D = np.stack([dist_seg(Pc, np.array(s[0], float), np.array(s[1], float)) for s in segs], axis=1)
            j = np.argmin(D, axis=1)
        else:
            best = np.full(n, -1, dtype=int)
            lam = np.full(n, np.inf)
            rec = [segs[jj] for jj in idx]
            for jj in idx:
                (A, B) = segs[jj]
                A = np.array(A, float); B = np.array(B, float)
                d = B - A
                # interseccion rayo p + lambda*u con segmento A+mu*d
                # sistema: p + lambda*u = A + mu*d  ->  u*lambda - d*mu = A-p
                M = np.stack([u, -d], axis=1)
                sol = np.linalg.solve(M, (A - Pc).T).T  # (n,2): lambda, mu
                lamj = sol[:, 0]; muj = sol[:, 1]
                ok = (lamj >= -1e-9) & (muj >= -1e-6) & (muj <= 1 + 1e-6)
                better = ok & (lamj < lam)
                lam[better] = lamj[better]
                best[better] = jj
            unresolved = best < 0
            if unresolved.any():
                D = np.stack([dist_seg(Pc, np.array(s[0], float), np.array(s[1], float)) for s in segs], axis=1)
                best[unresolved] = np.argmin(D[unresolved], axis=1)
            j = best
    else:
        D = np.stack([dist_seg(Pc, np.array(s[0], float), np.array(s[1], float)) for s in segs], axis=1)
        j = np.argmin(D, axis=1)
    areas = {}
    for k in range(len(apoyos)):
        areas[k] = int(np.sum(j == k)) * cell * cell
    return areas


def apoyos_ampliados(pid, poligono_neta, apoyos, receptores):
    """Corredores S/N: los apoyos_validos del modelo omiten los receptores
    secundarios (p. ej. S0 -> V_022 en FASE4B). Para ser fiel al ensayo se
    suman los receptores cuya traza toca el borde del panel."""
    if not es_unidireccional(pid):
        return apoyos
    ya = {rid for rid, _ in apoyos}
    out = list(apoyos)
    bnd = poligono_neta.boundary
    from shapely.geometry import LineString
    for rid, seg in receptores.items():
        if rid in ya:
            continue
        ls = LineString(seg)
        if bnd.distance(ls) <= 1e-6:
            out.append((rid, seg))
    return out


def main():
    d = json.loads(EII.read_text(encoding="utf-8"))
    out = {
        "version_formato": "1.0",
        "metodo": "bidireccional_FASE4B",
        "tamano_celda_m": TAMANO_CELDA,
        "renormalizar": RENORMALIZAR,
        "unidad_longitud": "m",
        "receptores": "vigas_y_muros_con_recibe_losa (columnas NO receptoras)",
        "fuente_geometria": {"archivo": EII.name, "sha256": sha256(EII)},
        "regresion_referencia": CSV_CP2.name,
        "niveles": [],
    }
    for nv in d["niveles"]:
        receptores = {}
        for v in nv["vigas"]:
            if v.get("recibe_losa"):
                receptores[v["id"]] = (v["inicio"], v["fin"])
        for m in nv["muros"]:
            if m.get("recibe_losa"):
                receptores[m["id"]] = (m["eje"]["inicio"], m["eje"]["fin"])
        aberturas = [to_polygon(ab["poligono"]) for ab in nv.get("aberturas_globales", [])]
        filas = []
        for losa in nv["losas"]:
            pid = losa["id"]
            outer = losa["poligono_exterior"]
            lap = [a for a in aberturas if to_polygon(outer).intersects(a)]
            neta = area_neta(outer, lap)
            A_neta = neta.area
            aps = losa.get("apoyos_validos", [])
            apoyos = [(rid, receptores[rid]) for rid in aps if rid in receptores]
            apoyos = apoyos_ampliados(pid, neta, apoyos, receptores)
            areas = asignar_panel(pid, neta, apoyos, TAMANO_CELDA)
            suma = sum(areas.values())
            factor = (A_neta / suma) if (RENORMALIZAR and suma > 0) else 1.0
            for j, (rid, _) in enumerate(apoyos):
                a = areas.get(j, 0.0) * factor
                if a <= 1e-9:
                    continue
                A_, B_ = receptores[rid]
                L = float(np.hypot(B_[0] - A_[0], B_[1] - A_[1]))
                filas.append({
                    "panel": pid, "borde": rid, "soporte": rid,
                    "tipo": "viga" if rid.startswith("V") else "muro",
                    "longitud_m": round(L, 6), "area_tributaria_m2": round(a, 6),
                    "ancho_max_m": None,
                    "ancho_promedio_m": round(a / L, 6) if L > 0 else None,
                    "area_neta_panel_m2": round(A_neta, 6),
                })
        netas_unicas = {r["panel"]: r["area_neta_panel_m2"] for r in filas}
        check = {
            "n_paneles": len(nv["losas"]),
            "suma_area_neta_m2": round(sum(netas_unicas.values()), 6),
            "suma_area_asignada_m2": round(sum(r["area_tributaria_m2"] for r in filas), 6),
        }
        per_panel = {}
        for r in filas:
            per_panel.setdefault(r["panel"], 0.0)
            per_panel[r["panel"]] += r["area_tributaria_m2"]
        check["n_paneles_conservados"] = int(sum(
            1 for p in netas_unicas if abs(per_panel[p] - netas_unicas[p]) < 1e-5))
        out["niveles"].append({"nivel": nv["id"], "checks": check, "filas": filas})
        print(f"{nv['id']}: {check}")

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OK", OUT)


if __name__ == "__main__":
    main()