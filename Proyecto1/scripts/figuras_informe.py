"""Figuras del informe final (reports/img/) a partir de los resultados vigentes.

Lee el JSON que usa Unity (edificio_G8/Assets/Resources/estructura_p1l4_unity.json)
y recalcula la curva M-phi de la COL70/70 con el mismo integrador de fibras que
usa el QA (carga_viva_sismo._fiber_moment_curvature, P = 0, 300 pasos hasta
phi = 0.12 1/m). No necesita OpenSees: solo numpy y matplotlib.

Figuras:
  mphi_col70.png       M-phi de la COL70/70 con mallas 10x10, 20x20 y 40x40
  pm_columna.png       P-M de diseno de la COL70/70 tipo con las demandas C1 a C3 (y las otras armaduras)
  pm_muros.png         envolvente P-M del muro de referencia (fibras) y la del muro mas exigido
  sismo_pisos.png      fuerzas sismicas por piso (NCh433) de cada edificio
  dcr_elementos.png    distribucion del factor de uso (DCR) de vigas y columnas

Uso (desde la raiz del repositorio):
    python -X utf8 Proyecto1/scripts/figuras_informe.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent                  # Proyecto1
REPO = ROOT.parent
sys.path.insert(0, str(SCRIPTS))
import carga_viva_sismo as cvm  # noqa: E402
import qa_semana06 as qa  # noqa: E402

UNITY_JSON = ROOT / "edificio_G8" / "Assets" / "Resources" / "estructura_p1l4_unity.json"
OUT = REPO / "reports" / "img"

# Colores de la paleta "Arrebol" (los mismos de Assets/Scripts/Paleta.cs)
INDIGO = "#6B5CF2"
VIOLETA = "#A84DD9"
ROSA = "#F26194"
DURAZNO = "#FF9959"
JADE = "#2EBD8C"
CORAL = "#FF6685"
CIRUELA = "#5C2648"
LILA = "#B394FF"
GRIS = "#8C7F94"
EX_COLOR = "#33B89E"
EY_COLOR = "#737AFF"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E6DCE8", "grid.linewidth": 0.6,
    "axes.edgecolor": "#5E4669", "axes.labelcolor": "#33233A", "xtick.color": "#33233A", "ytick.color": "#33233A",
})


def guardar(fig, nombre):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / nombre)
    plt.close(fig)
    print(f"  {OUT / nombre}")


def fig_mphi():
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    resumen = {}
    for n, color in ((10, DURAZNO), (20, ROSA), (40, INDIGO)):
        curv, m = cvm._fiber_moment_curvature(0.0, n, 0.12, 300)
        mmax = max(m)
        phi = curv[m.index(mmax)]
        resumen[n] = (mmax, phi)
        ax.plot(curv, m, color=color, lw=1.6, label=f"malla {n}x{n}: Mmax = {mmax:.0f} kN·m")
        ax.plot([phi], [mmax], "o", color=color, ms=4)
    dif = abs(resumen[20][0] - resumen[40][0]) / resumen[40][0] * 100.0
    ax.set_xlabel("curvatura φ [1/m]")
    ax.set_ylabel("momento M [kN·m]")
    n_barras = len(cvm.make_column_fibers()["rebar_xy"])
    ax.set_title(f"M-φ COL70/70 ({n_barras}φ{cvm.BAR_DIAMETER_MM:g}, G35, P = 0) · diferencia 20x20 vs 40x40: {dif:.2f} %", fontsize=9)
    ax.legend(frameon=False, loc="lower right")
    guardar(fig, "mphi_col70.png")
    return resumen, dif


def fig_pm_columna(u):
    curvas = {c["sectionId"]: c for c in u["p1l4"]["pmCurves"]}
    usos = {}
    for e in u["elements"]:
        if e["type"] == "columna" and e.get("pmCurveId"):
            usos[e["pmCurveId"]] = usos.get(e["pmCurveId"], 0) + 1
    tipo = max(usos, key=usos.get)                       # la armadura de la mayoria de las columnas
    dis = curvas[tipo]["points"]
    nom = curvas["COL70/70_FIBER"]["points"]
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.plot([p["M_kN_m"] for p in nom], [p["P_kN"] for p in nom], "--", color=GRIS, lw=1.0, marker="s", ms=3,
            label="nominal (Mn, Pn), 5 puntos")
    ax.plot([p["M_kN_m"] for p in dis], [p["P_kN"] for p in dis], color=JADE, lw=2.0,
            label=f"diseño {tipo.split('_', 1)[1].replace('f', 'φ')} ({usos[tipo]} columnas)")
    for otra, estilo in zip([k for k in sorted(usos) if k != tipo], ("-.", ":")):
        pts = curvas[otra]["points"]
        ax.plot([p["M_kN_m"] for p in pts], [p["P_kN"] for p in pts], estilo, color=CIRUELA, lw=1.1,
                label=f"diseño {otra.split('_', 1)[1].replace('f', 'φ')} ({usos[otra]})")
    colores = {"C1": INDIGO, "C2": CORAL, "C3": DURAZNO}
    peor = None
    for e in u["elements"]:
        cap = e.get("capacidad")
        if e["type"] != "columna" or e.get("pmCurveId") != tipo or not isinstance(cap, dict):
            continue
        for d in cap.get("porCombo", []):
            ax.plot(d["Mu"], d["Pu"], ".", color=colores.get(d["combo"], GRIS), ms=3, alpha=0.75)
            if peor is None or d["DCR_PM"] > peor[0]:
                peor = (d["DCR_PM"], e["elementTag"], d)
    for combo, color in colores.items():
        ax.plot([], [], ".", color=color, ms=6, label=f"demanda {combo}")
    if peor:
        dcr, tag, d = peor
        ax.plot(d["Mu"], d["Pu"], "o", mfc="none", mec=CIRUELA, ms=9, mew=1.6)
        ax.annotate(f"{tag} ({d['combo']}): Pu = {d['Pu']:.0f} kN, Mu = {d['Mu']:.0f} kN·m\nφMn = {d['phiMn_at_Pu']:.0f} kN·m → DCR = {dcr:.2f}",
                    (d["Mu"], d["Pu"]), xytext=(0.55, 0.12), textcoords="axes fraction", fontsize=8, color=CIRUELA,
                    arrowprops={"arrowstyle": "->", "color": CIRUELA, "lw": 0.8})
    ax.axhline(0, color="#5E4669", lw=0.6)
    ax.set_xlabel("momento M [kN·m]")
    ax.set_ylabel("axial P [kN] (compresión +)")
    ax.set_title("P-M de diseño de las columnas COL70/70 (documento de armaduras)", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    guardar(fig, "pm_columna.png")
    return peor


def fig_pm_muros(u):
    curvas = {c["sectionId"]: c for c in u["p1l4"]["pmCurves"]}
    ref = curvas["W_DPRIME_OPENING_TO_3"]
    # muro mas exigido: mayor C = M / phiMn(P), con la misma interpolacion del QA
    muros = u["p1l4"]["wallRegistry"]
    peor = None
    for w in muros:
        curva = curvas.get(w.get("pmSectionId"))
        if not curva:
            continue
        for d in w["demands"]:
            cap = qa.wall_capacity_at(curva["points"], d["P_kN"])
            c = abs(d["M_kN_m"]) / cap if cap > 0 else 99.0
            if peor is None or c > peor[0]:
                peor = (c, w, curva)
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.9))
    ax = axes[0]
    pts = ref["points"]
    ax.plot([p["M_kN_m"] for p in pts], [p["P_kN"] for p in pts], color=JADE, lw=2.0, marker="o", ms=2.5)
    ax.axhline(0, color="#5E4669", lw=0.6)
    ax.set_title("Muro de referencia, fibras (t = 0,25 m, L = 7,60 m)", fontsize=8.5)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
    ax.set_xlabel("M en el plano [kN·m]")
    ax.set_ylabel("P [kN] (compresión +)")
    ax = axes[1]
    c_max, w, curva = peor
    pts = curva["points"]
    ax.plot([p["M_kN_m"] for p in pts], [p["P_kN"] for p in pts], color=JADE, lw=2.0, label=f"diseño {curva['sectionId']}")
    colores = {"C1": INDIGO, "C2": CORAL, "C3": DURAZNO}
    for d in w["demands"]:
        ax.plot(abs(d["M_kN_m"]), d["P_kN"], "o", color=colores.get(d["combo"], GRIS), ms=6, label=f"demanda {d['combo']}")
    ax.axhline(0, color="#5E4669", lw=0.6)
    ax.set_title(f"MURO-{w['index']:03d} (t = {w['grosor']:.2f} m, L = {w['longitud']:.2f} m) · C máx = {c_max:.2f}", fontsize=8.5)
    ax.set_xlabel("M en el plano [kN·m]")
    ax.set_ylabel("P [kN] (compresión +)")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    guardar(fig, "pm_muros.png")
    return w, curva


def fig_sismo(u):
    pisos = ["CIELO_1S", "CIELO_1", "CIELO_2", "CIELO_3", "CIELO_4"]
    datos = {(d["edificio"], d["piso"]): d for d in u["diafragmasSismo"]}
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4), sharey=True)
    for ax, edificio, titulo in ((axes[0], "edificio_1", "Edificio 1"), (axes[1], "edificio_2", "Edificio 2")):
        y = range(len(pisos))
        fx = [datos[(edificio, p)]["F_EX_kN"] for p in pisos]
        fy = [datos[(edificio, p)]["F_EY_kN"] for p in pisos]
        ax.barh([i + 0.2 for i in y], fx, height=0.38, color=EX_COLOR, label=f"EX (Σ = {sum(fx):,.0f} kN)".replace(",", " "))
        ax.barh([i - 0.2 for i in y], fy, height=0.38, color=EY_COLOR, label=f"EY (Σ = {sum(fy):,.0f} kN)".replace(",", " "))
        ax.set_yticks(list(y))
        ax.set_yticklabels(pisos)
        ax.set_xlabel("fuerza en el nodo maestro [kN]")
        ax.set_title(titulo, fontsize=9)
        ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    guardar(fig, "sismo_pisos.png")


def fig_dcr(u):
    vigas = [e["capacidad"]["DCR"] for e in u["elements"] if e["type"] == "viga" and isinstance(e.get("capacidad"), dict)]
    cols = [e["capacidad"]["DCR"] for e in u["elements"] if e["type"] == "columna" and isinstance(e.get("capacidad"), dict)]
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    bins = [i * 0.05 for i in range(0, 30)]
    ax.hist(vigas, bins=bins, color=LILA, alpha=0.85, label=f"vigas ({len(vigas)}; {sum(d > 1 for d in vigas)} con DCR > 1)")
    ax.hist(cols, bins=bins, color=JADE, alpha=0.85, label=f"columnas HA ({len(cols)}; máx. {max(cols):.2f})")
    ax.axvline(1.0, color=CIRUELA, lw=1.2, ls="--")
    ax.text(1.01, ax.get_ylim()[1] * 0.92, "DCR = 1", color=CIRUELA, fontsize=8)
    ax.set_xlabel("DCR = demanda / capacidad (gobernante entre C1, C2 y C3)")
    ax.set_ylabel("número de elementos")
    ax.legend(frameon=False, fontsize=7.5)
    guardar(fig, "dcr_elementos.png")
    return len(vigas), sum(d > 1 for d in vigas), len(cols), max(cols)


def main():
    u = json.loads(UNITY_JSON.read_text(encoding="utf-8"))
    print("Figuras del informe:")
    mphi, dif = fig_mphi()
    peor_col = fig_pm_columna(u)
    muro, curva = fig_pm_muros(u)
    fig_sismo(u)
    nv, nv1, nc, cmax = fig_dcr(u)
    print("\nValores usados en el informe:")
    for n, (m, phi) in mphi.items():
        print(f"  M-phi {n}x{n}: Mmax = {m:.1f} kN·m en phi = {phi:.4f} 1/m")
    print(f"  diferencia 20x20 vs 40x40 = {dif:.2f} %")
    print(f"  columna mas exigida: {peor_col[1]} {peor_col[2]['combo']} DCR = {peor_col[0]:.3f}")
    print(f"  muro mas exigido: MURO-{muro['index']:03d} con {curva['sectionId']}")
    print(f"  vigas: {nv} ({nv1} con DCR > 1); columnas HA: {nc} (DCR max {cmax:.3f})")


if __name__ == "__main__":
    main()
