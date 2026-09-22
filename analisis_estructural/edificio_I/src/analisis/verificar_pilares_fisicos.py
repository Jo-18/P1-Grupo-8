"""Verifica los pilares fisicos (HATCH 70x70) de los DXFs contra las columnas congeladas.

Separa por banda mediante el origen-x declarado en cada JSON (huella del transform),
NO por proximidad. Aplica el transform documentado y reporta residuos de precision completa.

Niveles/DXF:
  P1     2017_67-101.dxf  (banda inferior, N.R.=-0.05)   x_m=(X-61.3)/100   y_m=(Y-58.0)/100
  P2     2017_67-102.dxf  (banda superior)               x_m=(X-893.23)/100  y_m=(7884.92-Y)/100
  P3     2017_67-102.dxf  (banda inferior)               x_m=(X-535.00)/100  y_m=(4260.35-Y)/100
  P4     2017_67-103.dxf                                 x_m=(X-490.3)/100   y_m=(6297.3-Y)/100
  CP1S   2017_67-101.dxf  (banda superior)               x_m=(X-1026.30)/100 y_m=(Y-5515.10)/100

Los centros fisicos se obtienen de los HATCH de capa RLE-SOLID de 70x70 (=0.7m), que son
los pilares de concreto P.70x70. Solo lectura (no modifica JSON ni DXFs).
"""
import ezdxf, json
from ezdxf import bbox
from collections import defaultdict
import math

DXF = r"C:/Users/josef/OneDrive/Universidad/10mo Semestre/MCOC/Proyecto 1/Datos Estructurales/"
GEO = r"C:/Users/josef/OneDrive/Universidad/10mo Semestre/MCOC/Proyecto 1/P1/Proyecto_Edificio_Ingenieria/datos/geometria/"

def pilares_70(f):
    doc = ezdxf.readfile(f)
    msp = doc.modelspace()
    out = []
    for e in msp:
        if e.dxftype() != "HATCH":
            continue
        bb = bbox.extents([e])
        if bb is None:
            continue
        dx = bb.extmax.x - bb.extmin.x
        dy = bb.extmax.y - bb.extmin.y
        # pilares de concreto P.70x70 -> contorno 70x70 (1 unidad = 1 cm), tolerancia de hatch
        if abs(dx - 70) < 0.6 and abs(dy - 70) < 0.6:
            out.append(((bb.extmin.x + bb.extmax.x) / 2.0, (bb.extmin.y + bb.extmax.y) / 2.0))
    return out

def cargar_cols(lev):
    with open(GEO + "edificio_I_cielo_piso_%s_borrador.json" % lev, encoding="utf-8") as fh:
        d = json.load(fh)
    if "columnas" in d and isinstance(d["columnas"], list):
        return d["columnas"]
    return d["columnas_referencia"]

# huella de banda: cluster por cercania a origen-x (multiple de 1000 cm de la retricula ~10m)
def cluster_banda(ps, ox, tol=55):
    res = []
    for x, y in ps:
        # Incluye Ip, que esta a 4.5 m del eje E, no a un multiplo entero de 10 m.
        dist = min(abs(x - (ox + dx)) for dx in (0, 1000, 2000, 3000, 4000, 4500, 5000, 5500))
        if dist < tol:
            res.append((x, y))
    return res

TRANSF = {
    # lev: (dxf, ox, oy, invertida_y, banda)
    "1":         ("2017_67-101.dxf",  61.3,   58.0,   False, "inferior"),
    "2":         ("2017_67-102.dxf", 893.23, 7884.92, True,  "superior"),
    "3":         ("2017_67-102.dxf", 535.00, 4260.35, True,  "inferior"),
    "4":         ("2017_67-103.dxf", 490.3,  6297.3,  True,  None),
    "1_subterraneo": ("2017_67-101.dxf", 1026.30, 5515.10, False, "superior"),
}

def filtrar_banda(ps, band):
    if band == "superior":
        return [p for p in ps if p[1] > 4600]
    if band == "inferior":
        return [p for p in ps if p[1] < 4600]
    return ps

def main():
    report = []
    for lev in ["1", "2", "3", "4", "1_subterraneo"]:
        dxf, ox, oy, inv, band = TRANSF[lev]
        ps = pilares_70(DXF + dxf)
        if band:
            ps = filtrar_banda(ps, band)
        # usar huella x-origen dentro de la banda ya filtrada
        psb = cluster_banda(ps, ox)
        if not psb:
            report.append((lev, dxf, "SIN PILARES", []))
            continue
        # transform
        def tr(x, y):
            u = (x - ox) / 100.0
            v = (oy - y) / 100.0 if inv else (y - oy) / 100.0
            return u, v
        axess = sorted(set(round(tr(x, y)[0], 3) for x, y in psb))
        vss   = sorted(set(round(tr(x, y)[1], 3) for x, y in psb))  # v values
        report.append((lev, dxf, "ok", (axess, vss, tr)))

    print("=" * 78)
    print("RESULTADO: pilares fisicos 70x70 -> coordenadas por transform documentado")
    print("=" * 78)
    for lev, dxf, status, det in report:
        print("\n### Nivel CP%s   (dxf=%s, estado=%s)" % (lev, dxf, status))
        if status == "SIN PILARES":
            print("   No se hallaron pilares 70x70.")
            continue
        axess, vss, tr = det
        print("   ejes-u hallados (m):       %s" % [round(a,3) for a in axess])
        print("   cotas-v halladas (m):      %s" % [round(v,6) for v in vss])
        # comparar contra columnas congeladas concretas (70x70)
        cols = [c for c in cargar_cols(lev) if "70x70" in (c.get("seccion") or "")]
        grid_axes = sorted(set(round(c["posicion"][0],2) for c in cols))
        grid_v    = sorted(set(round(c["posicion"][1],2) for c in cols))
        print("   columnas congeladas (seccion 70x70) n=%d  ejes-u: %s" % (len(cols), grid_axes))
        print("   columnas congeladas  cotas-v:        %s" % grid_v)
        # residuo eje a eje entre fisico y grid nominal (0,10,..,45)
        nominal_u = ([10, 20, 30, 40, 50, 55] if lev == "1" else
                     [0, 10, 20, 30, 40, 45, 50])
        res_u = []
        for a in axess:
            best = min(nominal_u, key=lambda n: abs(n-a))
            res_u.append(abs(a-best))
        print("   residuo|u| vs ret. nominal E=0,F=10,...:  max=%.5f m" % (max(res_u) if res_u else 0))

if __name__ == "__main__":
    main()
