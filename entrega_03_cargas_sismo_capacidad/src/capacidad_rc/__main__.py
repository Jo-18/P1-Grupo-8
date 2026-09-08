"""Runner independiente de capacidad RC (demo DEMOSTRACION_ARBITRARIA).

Uso:  python -m src.capacidad_rc   (desde entrega_03_cargas_sismo_capacidad/)
Salidas en results/capacidad_rc/ y figures/capacidad_rc/.
La seccion de la demo NO es de ningun edificio real.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.capacidad_rc import fibra as fibra_mod
from src.capacidad_rc.diagrama_pm import puntos_pm
from src.capacidad_rc.momento_curvatura import curva_mphi
from src.capacidad_rc.seccion import seccion_demo

REPO = Path(__file__).resolve().parents[3]
RES = REPO / "entrega_03_cargas_sismo_capacidad" / "results" / "capacidad_rc"
FIG = REPO / "entrega_03_cargas_sismo_capacidad" / "figures" / "capacidad_rc"


def plot_seccion(seccion, ax) -> None:
    import numpy as np
    ys, zs, areas, tags = fibra_mod.fibras(seccion)
    ax.add_patch(plt.Rectangle((-seccion.b / 2, -seccion.h / 2), seccion.b, seccion.h,
                               fill=False, color="black", lw=1.2))
    conc = tags == 1
    ste = tags == 2
    ax.scatter(ys[conc], zs[conc], s=1.5, color="0.75", label="fibra hormigon")
    ax.scatter(ys[ste], zs[ste], s=22, color="crimson",
               marker="o", facecolors="none", edgecolors="crimson", label="acero")
    for b in seccion.barras:
        ax.scatter([b.y], [b.z], s=8, color="crimson")
    ax.set_xlabel("y [m] (eje de flexion)")
    ax.set_ylabel("z [m]")
    ax.set_aspect("equal", "box")
    ax.set_title(f"seccion {seccion.etiqueta} - fibras")
    ax.legend(loc="upper right", fontsize=7)


def plot_mphi(cur, ax, color, label) -> None:
    ax.plot(cur["kappa"], cur["M"], color=color, lw=1.8, label=label)
    ax.set_xlabel("curvatura kappa [1/m]")
    ax.set_ylabel("momento M [kN*m]")
    ax.grid(alpha=0.3)


def plot_pm(pm, ax) -> None:
    ax.plot(pm["M_kN_m"], pm["N_kN"], "o--", color="#1f77b4", ms=4)
    ax.set_xlabel("M [kN*m] (capacidad a flexion)")
    ax.set_ylabel("N [kN] (compresion +)")
    ax.grid(alpha=0.3)
    ax.set_title("Diagrama P-M (primeros puntos)")


def main(argv=None) -> int:
    _ = argv if argv is not None else sys.argv[1:]
    RES.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    seccion = seccion_demo()
    resumen = seccion.resumen()
    area_fibras = fibra_mod.area_total_fibras(seccion)

    N_casos = [0.0, 0.2 * seccion.hormigon.fc * 1000.0 * seccion.area_bruta]  # N=0 y 20% fc*Ag
    KAPPA_MAX_ANALISIS = 0.24
    curvas = {f"N={n:.0f}": curva_mphi(seccion, N_kN=n, kappa_max=KAPPA_MAX_ANALISIS,
                                       n_pasos=320)
              for n in N_casos}
    c0 = curvas["N=0"]
    Mu0 = float(c0["M_u_kN_m"])
    kappa_u = float(c0["kappa_u_1_m"])
    key_comp = [k for k in curvas if k != "N=0"][0]


    fc_kPa = seccion.hormigon.fc * 1000.0
    pm = puntos_pm(seccion, N_min_kN=-0.3 * fc_kPa * seccion.area_bruta,
                   N_max_kN=1.0 * fc_kPa * seccion.area_bruta, n_puntos=21,
                   kappa_max=KAPPA_MAX_ANALISIS, n_pasos_phi=160)

    # ---- salidas de datos ----
    resumen["verificacion_area_fibras"] = {
        "area_bruta_m2": resumen["area_bruta_m2"],
        "area_fibras_m2": round(area_fibras, 6),
        "diferencia_m2": round(resumen["area_bruta_m2"] - area_fibras, 9)}
    protocolo = {
        "carga": "por curva M-phi: carga axial CONSTANTE N (compresion +) y curvatura "
                 "controlada kappa creciente con LoadControl de un solo paso por punto",
        "convergencia": ("en cada kappa se resuelve eps_ct por biseccion (<=90 iters) "
                         "hasta que |N_int - N| < 1e-7 rel; tolerancia de biseccion "
                         "independiente del analisis FE"),
        "criterio_falla": ("PRIMER episodio (indice menor) de: (1) APLASTAMIENTO: la "
                           "fibra extrema de HORMIGON comprimida alcanza eps >= eps_cu "
                           "por defecto hormigon.epsu=0.004; o (2) FRACTURA: UNA fibra "
                           "de ACERO alcanza abs(eps) >= eps_su=0.05 (supuesto "
                           "documentado); si ninguno se alcanza en kappa_max, "
                           "CAP_MALLA_SIN_FALLA"),
        "eps_cu": c0["eps_cu"],
        "eps_su": c0["eps_su"],
        "check_fractura_acero": "sobre las fibras de acero reales (abs(eps)>=eps_su), "
                                "NO sobre la fibra extrema de hormigon",
        "kappa_max_analisis_1_m": KAPPA_MAX_ANALISIS,
        "M_u_definicion": "M en el paso de falla por criterio (NO maximo sobre la malla)",
    }
    resultados = {
        "DEMOSTRACION_ARBITRARIA": True,
        "nota": "Ejemplo arbitrario; no es una seccion real de los edificios.",
        "seccion": resumen,
        "protocolo_analisis": protocolo,
        "M_u_N0_kN_m": round(Mu0, 2),
        "kappa_u_N0_1_m": round(kappa_u, 5),
        "criterio_falla_N0": c0["criterio_falla"],
        "M_referencia_cap_malla_KAPPA0.24_N0_kN_m": round(float(max(c0["M"])), 2),
        "N_casos": N_casos,
        "diagrama_pm": pm,
        "convencion": ("strain compresion + en +y; M>0 con compresion en +y; "
                       "N>0 compresion; kappa>0 con compresion en +y; "
                       "unidades kN, kN*m, m"),
    }
    (RES / "seccion_demo.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with open(RES / "m_phi.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["N_kN", "kappa_1_m", "M_kN_m", "eps_top_hormigon",
                    "eps_bottom_hormigon", "eps_acero_max_abs", "y_neutra_m"])
        for nombre, cur in curvas.items():
            for kp, m, et, eb, eac, yn in zip(cur["kappa"], cur["M"], cur["eps_top"],
                                              cur["eps_bottom"], cur["eps_acero_max"],
                                              cur["y_neutra_m"]):
                w.writerow([cur["N_kN"], f"{kp:.6f}", f"{m:.4f}",
                            f"{et:.6f}", f"{eb:.6f}", f"{eac:.6f}", f"{yn:.6f}"])
    with open(RES / "p_m.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["N_kN", "M_capacidad_kN_m"])
        for n, mcap in zip(pm["N_kN"], pm["M_kN_m"]):
            w.writerow([f"{n:.3f}", f"{mcap:.3f}"])

    # ---- figuras ----
    fig, ax = plt.subplots(figsize=(5.2, 5.2), dpi=150)
    plot_seccion(seccion, ax)
    fig.tight_layout()
    fig.savefig(FIG / "seccion_fibras.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=150)
    plot_mphi(curvas["N=0"], ax, "tab:blue", "N = 0")
    plot_mphi(curvas[key_comp], ax, "tab:red", f"N = {curvas[key_comp]['N_kN']:.0f} kN (compresion)")
    ax.set_title("Curva M-phi (Fiber Section)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "m_phi.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.6), dpi=150)
    plot_pm(pm, ax)
    fig.tight_layout()
    fig.savefig(FIG / "diagrama_pm.png")
    plt.close(fig)

    print(json.dumps({
        "seccion": seccion.etiqueta,
        "DEMOSTRACION_ARBITRARIA": True,
        "M_u_N0_kN_m": round(Mu0, 2),
        "kappa_u_1_m": round(kappa_u, 5),
        "criterio_falla_N0": c0["criterio_falla"],
        "n_fibras": {"concreto": resumen["n_fibras_concreto"],
                     "acero": resumen["n_fibras_acero"]},
        "area_fibras_vs_bruta": resumen["verificacion_area_fibras"],
        "puntos_PM_de_N_kN": [round(pm["N_kN"][0], 1), round(pm["N_kN"][-1], 1)],
        "escrito_en": [str(RES), str(FIG)]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())