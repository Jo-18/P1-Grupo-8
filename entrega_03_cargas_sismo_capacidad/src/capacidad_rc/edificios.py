"""Capacidad RC por edificio: DEMO_RC_EI y DEMO_RC_EII (Entrega 3).

Configuraciones con GEOMETRIA DOCUMENTADA (columnas reales hormigon 0.70x0.70):
  - Edificio I : fc=40 MPa (G40) -> HIPOTESIS del grupo (sin fuente independiente).
  - Edificio II: fc=35 MPa (G35) -> DOCUMENTADO (eii_viewer.json).
Armado (fy, recubrimiento, barras): BLOQUEADO -> patron de DEMOSTRACION simetrico
(12 #25, rec=0.04, fy=420 MPa). La seccion resultante se clasifica
HIPOTESIS_DEMOSTRACION y NO es capacidad real de diseno.

Para cada edificio se obtiene: curva M-phi (N=0 y N=0.20*fc*Ag), diagrama P-M,
resumen de seccion/fibra con verificacion de areas, y figuras. Se agrega un
resumen comparativo EI vs EII junto al protocolo y criterios de falla.

Salidas:
  results/capacidad_rc/DEMO_RC_EI.json|.csv  (y DEMO_RC_EII)
  results/capacidad_rc/resumen_DEMO_RC_EI_EII.json
  figures/capacidad_rc/DEMO_RC_{EI,EII}_*.png

Uso:
  python -X utf8 -m src.capacidad_rc.edificios
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
from src.capacidad_rc.seccion import SeccionRC, seccion_con_armado

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
CONFIG = E3 / "config" / "capacidad_rc.json"
RES = E3 / "results" / "capacidad_rc"
FIG = E3 / "figures" / "capacidad_rc"


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def seccion_edificio(edificio: str) -> SeccionRC:
    cfg = _config()
    arm = cfg["armado_de_demostracion"]
    fc = cfg["soporte_fuentes"]["EII_fc"]["valor"] if edificio == "II" \
        else cfg["soporte_fuentes"]["EI_fc"]["valor"]
    # 0.70 (h) x 0.70 (b); 12 #25 simetricos, rec=0.04, fy=420
    sec = seccion_con_armado(
        h=0.70, b=0.70, rec=arm["recubrimiento_m"],
        diam_m=arm["diametro_barras_m"], n_cn=4,
        n_en_medio_cn_Y=2, n_en_medio_cn_Z=2,
        fc_mpa=fc, fy_mpa=arm["fy_MPa"])
    sec.etiqueta = "DEMO_RC_%s" % ("EII" if edificio == "II" else "EI")
    return sec


def _clasificacion(edificio: str) -> dict:
    cfg = _config()
    fu = cfg["soporte_fuentes"]
    return {
        "edificio": edificio,
        "seccion": fu["EII_seccion"] if edificio == "II" else fu["EI_seccion"],
        "fc_MPa": fu["EII_fc"] if edificio == "II" else fu["EI_fc"],
        "armadura": fu["armadura"],
        "clasificacion": "HIPOTESIS_DEMOSTRACION",
        "nota": ("geometria documentada (0.70x0.70 hormigon) + material "
                 "(documentado o hipotesis) + armado de demostracion; NO es "
                 "capacidad real de diseno."),
    }


def _advertencia_demo(fig) -> None:
    fig.text(
        0.5, 0.015,
        "DEMOSTRACIÓN — SECCIÓN HIPOTÉTICA, NO VÁLIDA PARA DISEÑO",
        ha="center", va="bottom", fontsize=10, fontweight="bold",
        color="#8b0000",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#fff2f2",
                  edgecolor="#8b0000", lw=1.4))


def _plot_seccion(sec, ax) -> None:
    import numpy as np
    ys, zs, areas, tags = fibra_mod.fibras(sec)
    ax.add_patch(plt.Rectangle((-sec.b / 2, -sec.h / 2), sec.b, sec.h,
                               fill=False, color="black", lw=1.2))
    conc = tags == 1
    ste = tags == 2
    ax.scatter(ys[conc], zs[conc], s=1.5, color="0.75", label="fibra hormigón")
    ax.scatter(ys[ste], zs[ste], s=22, color="crimson", marker="o",
               facecolors="none", edgecolors="crimson", label="acero")
    for b in sec.barras:
        ax.scatter([b.y], [b.z], s=8, color="crimson")
    ax.set_xlabel("y [m] (eje de flexión)")
    ax.set_ylabel("z [m]")
    ax.set_aspect("equal", "box")
    ax.set_title("Discretización de la sección por fibras\n%s"
                 % sec.etiqueta, fontsize=11)
    ax.legend(loc="upper right", fontsize=7)


def _analizar(edificio: str) -> dict:
    cfg = _config()
    an = cfg["analisis"]
    sec = seccion_edificio(edificio)
    resumen = sec.resumen()
    area_fibras = fibra_mod.area_total_fibras(sec)
    resumen["verificacion_area_fibras"] = {
        "area_bruta_m2": resumen["area_bruta_m2"],
        "area_fibras_m2": round(area_fibras, 6),
        "diferencia_m2": round(resumen["area_bruta_m2"] - area_fibras, 9)}

    fc_kPa = sec.hormigon.fc * 1000.0
    N_casos = [0.0, an["N_compresion_factor_fc_Ag"] * fc_kPa * sec.area_bruta]
    KAPPA_MAX = an["kappa_max_1_m"]
    N_PASOS = an["n_pasos_mphi"]
    EPS_SU = an["eps_su"]
    curvas = {f"N={n:.0f}": curva_mphi(sec, N_kN=n, kappa_max=KAPPA_MAX,
                                       n_pasos=N_PASOS, eps_su=EPS_SU)
              for n in N_casos}
    c0 = curvas["N=0"]
    key_comp = [k for k in curvas if k != "N=0"][0]

    pm = puntos_pm(sec, N_min_kN=an["N_min_factor_fc_Ag"] * fc_kPa * sec.area_bruta,
                   N_max_kN=an["N_max_factor_fc_Ag"] * fc_kPa * sec.area_bruta,
                   n_puntos=an["n_puntos_PM"], kappa_max=KAPPA_MAX,
                   n_pasos_phi=an["n_pasos_phi_PM"], eps_su=EPS_SU)

    protocolo = {
        "carga": "por curva M-phi: carga axial CONSTANTE N (compresion +) y curvatura "
                 "controlada kappa creciente (biseccion eps_ct por paso)",
        "criterio_falla": ("PRIMER episodio (indice menor) de: (1) APLASTAMIENTO "
                           "hormigon eps_fibra_extrema >= eps_cu=0.004; o "
                           "(2) FRACTURA: una fibra de ACERO abs(eps)>=eps_su=0.05; "
                           "si ninguno en kappa_max, CAP_MALLA_SIN_FALLA"),
        "eps_cu": c0["eps_cu"], "eps_su": c0["eps_su"],
        "kappa_max_1_m": KAPPA_MAX, "n_pasos_mphi": N_PASOS,
        "M_u_definicion": "M en el paso de falla por criterio (no el maximo de la malla)",
    }

    return {"seccion": resumen, "clasificacion": _clasificacion(edificio),
            "protocolo": protocolo, "fc_kPa": fc_kPa,
            "N_casos_kN": N_casos, "curvas": curvas, "pm": pm,
            "c0": c0, "key_comp": key_comp, "KAPPA_MAX": KAPPA_MAX,
            "seccion_obj": sec}


def _escribir_json(edificio: str, datos: dict) -> Path:
    RES.mkdir(parents=True, exist_ok=True)
    key = "EII" if edificio == "II" else "EI"
    curvas_ser = {}
    for nombre, cur in datos["curvas"].items():
        d = {"N_kN": cur["N_kN"]}
        for k in ("kappa", "M", "eps_top", "eps_bottom", "eps_acero_max", "y_neutra_m"):
            d[k] = [round(float(x), 8) for x in cur[k]]
        d["M_u_kN_m"] = round(float(cur["M_u_kN_m"]), 4)
        d["kappa_u_1_m"] = round(float(cur["kappa_u_1_m"]), 6)
        d["indice_falla"] = int(cur["indice_falla"])
        d["criterio_falla"] = cur["criterio_falla"]
        d["indice_aplastamiento"] = (int(cur["indice_aplastamiento"])
                                     if cur["indice_aplastamiento"] is not None else None)
        d["indice_fractura_acero"] = (int(cur["indice_fractura_acero"])
                                      if cur["indice_fractura_acero"] is not None else None)
        curvas_ser[nombre] = d
    pm = datos["pm"]
    payload = {
        "seccion_demo": "DEMO_RC_%s" % key,
        "edificio": edificio,
        "HIPOTESIS_DEMOSTRACION": True,
        "seccion": datos["seccion"],
        "clasificacion": datos["clasificacion"],
        "protocolo_analisis": datos["protocolo"],
        "curvas_mphi": curvas_ser,
        "M_u_N0_kN_m": round(float(datos["c0"]["M_u_kN_m"]), 4),
        "kappa_u_N0_1_m": round(float(datos["c0"]["kappa_u_1_m"]), 6),
        "criterio_falla_N0": datos["c0"]["criterio_falla"],
        "M_u_Ncomp_kN_m": round(float(datos["curvas"][datos["key_comp"]]["M_u_kN_m"]), 4),
        "N_compresion_kN": round(datos["N_casos_kN"][1], 2),
        "diagrama_pm": {"N_kN": [round(float(x), 3) for x in pm["N_kN"]],
                        "M_kN_m": [round(float(x), 3) for x in pm["M_kN_m"]]},
        "convencion": ("strain compresion + en +y; M>0 con compresion en +y; "
                       "N>0 compresion; unidades kN, kN*m, m"),
        "configuracion_usada": json.loads(CONFIG.read_text(encoding="utf-8")),
    }
    jp = RES / ("DEMO_RC_%s.json" % key)
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")
    return jp


def _escribir_csv(edificio: str, datos: dict) -> Path:
    RES.mkdir(parents=True, exist_ok=True)
    key = "EII" if edificio == "II" else "EI"
    with open(RES / ("DEMO_RC_%s_m_phi.csv" % key), "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["N_kN", "kappa_1_m", "M_kN_m", "eps_top_hormigon",
                    "eps_bottom_hormigon", "eps_acero_max_abs", "y_neutra_m"])
        for nombre, cur in datos["curvas"].items():
            for kp, m, et, eb, eac, yn in zip(cur["kappa"], cur["M"], cur["eps_top"],
                                              cur["eps_bottom"], cur["eps_acero_max"],
                                              cur["y_neutra_m"]):
                w.writerow([cur["N_kN"], f"{kp:.6f}", f"{m:.4f}",
                            f"{et:.6f}", f"{eb:.6f}", f"{eac:.6f}", f"{yn:.6f}"])
    with open(RES / ("DEMO_RC_%s_p_m.csv" % key), "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["N_kN", "M_capacidad_kN_m"])
        pm = datos["pm"]
        for n, mcap in zip(pm["N_kN"], pm["M_kN_m"]):
            w.writerow([f"{n:.3f}", f"{mcap:.3f}"])
    return RES / ("DEMO_RC_%s" % key)


def _figuras(edificio: str, datos: dict) -> list:
    import numpy as np
    FIG.mkdir(parents=True, exist_ok=True)
    key = "EII" if edificio == "II" else "EI"
    etiq = "DEMO_RC_%s" % key
    out = []

    fig, ax = plt.subplots(figsize=(5.4, 5.4), dpi=150)
    _plot_seccion(datos["seccion_obj"], ax)
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    _advertencia_demo(fig)
    p = FIG / ("DEMO_RC_%s_seccion_fibras.png" % key)
    fig.savefig(p)
    plt.close(fig)
    out.append(p)

    curvas = datos["curvas"]
    fig, ax = plt.subplots(figsize=(7.0, 4.6), dpi=150)
    for nombre, cur in curvas.items():
        color = "tab:blue" if nombre == "N=0" else "tab:red"
        if nombre == "N=0":
            label = "N = 0"
        else:
            label = "N = %.0f kN (compresión)" % cur["N_kN"]
        i_f = int(cur["indice_falla"]) if cur["indice_falla"] is not None \
            else len(cur["kappa"]) - 1
        kk = np.asarray(cur["kappa"])[:i_f + 1]
        MM = np.asarray(cur["M"])[:i_f + 1]
        ax.plot(kk, MM, color=color, lw=1.8, label=label)
        ku = float(cur["kappa_u_1_m"])
        Mu = float(cur["M_u_kN_m"])
        ax.plot([ku], [Mu], marker="*", markersize=15, mfc="white",
                mec=color, mew=1.6, ls="none", zorder=6)
        ax.axvline(ku, color=color, ls=":", lw=1.0, alpha=0.55, zorder=4)
        if "APLASTAMIENTO" in cur["criterio_falla"]:
            crit = "aplastamiento del hormigón (ε_ext ≥ ε_cu = 0,004)"
        elif "FRACTURA" in cur["criterio_falla"]:
            crit = "fractura del acero (|ε| ≥ ε_su = 0,05)"
        else:
            crit = "fin de malla sin falla (solo indicativo)"
        va = "bottom" if nombre == "N=0" else "top"
        dy = 60.0 if nombre == "N=0" else -80.0
        dx = 0.004 if nombre == "N=0" else 0.002
        ax.annotate("κ_u = %.5f 1/m\nM_u = %.4f kN·m\n%s" % (ku, Mu, crit),
                    xy=(ku, Mu), xytext=(ku + dx, Mu + dy),
                    va=va, fontsize=7.5, color=color,
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.8))
    ax.set_xlabel("curvatura κ [1/m]")
    ax.set_ylabel("momento M [kN·m]")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout(rect=(0, 0.06, 1, 0.86))
    fig.text(0.5, 0.975, "Curva momento–curvatura — %s" % etiq,
             ha="center", va="top", fontsize=11)
    fig.text(0.5, 0.918,
             "curvas truncadas en el primer criterio de falla; "
             "M_u marcado (no el máximo de la malla)",
             ha="center", va="top", fontsize=7.5, color="0.3")
    _advertencia_demo(fig)
    p = FIG / ("DEMO_RC_%s_m_phi.png" % key)
    fig.savefig(p)
    plt.close(fig)
    out.append(p)

    fig, ax = plt.subplots(figsize=(6.8, 4.9), dpi=150)
    pm = datos["pm"]
    ax.plot(pm["M_kN_m"], pm["N_kN"], "o-", color="#1f77b4", ms=4, lw=1.4,
            label="envolvente P–M (M_u por carga axial)")
    for nom, cur, c in (("N=0", datos["c0"], "#2ca02c"),
                        (datos["key_comp"], datos["curvas"][datos["key_comp"]],
                         "#d62728")):
        mm = float(cur["M_u_kN_m"])
        nn = float(cur["N_kN"])
        ax.plot([mm], [nn], marker="o", ms=9, mfc="white", mec=c, mew=1.8,
                ls="none", zorder=6)
        ax.annotate("M_u(%s) = %.2f kN·m" % (nom, mm),
                    xy=(mm, nn), xytext=(mm + 60.0, nn), fontsize=7.5,
                    color=c)
    ax.set_xlabel("M [kN·m] (capacidad a flexión)")
    ax.set_ylabel("N [kN] (compresión +)")
    ax.set_title("Diagrama de interacción P–M\n%s" % etiq, fontsize=11)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    _advertencia_demo(fig)
    p = FIG / ("DEMO_RC_%s_diagrama_pm.png" % key)
    fig.savefig(p)
    plt.close(fig)
    out.append(p)
    return out


def resumen_comparativo(data_I: dict, data_II: dict, escritos: dict) -> Path:
    RES.mkdir(parents=True, exist_ok=True)
    filas = {}
    for edificio, datos, key in (("I", data_I, "EI"), ("II", data_II, "EII")):
        filas[key] = {
            "edificio": edificio,
            "fc_MPa": datos["seccion"]["materiales"]["hormigon"]["fc_MPa"],
            "n_barras": datos["seccion"]["n_barras"],
            "As_total_m2": datos["seccion"]["As_total_m2"],
            "area_bruta_m2": datos["seccion"]["area_bruta_m2"],
            "n_fibras_concreto": datos["seccion"]["n_fibras_concreto"],
            "n_fibras_acero": datos["seccion"]["n_fibras_acero"],
            "verificacion_area_fibras": datos["seccion"]["verificacion_area_fibras"],
            "M_u_N0_kN_m": round(float(datos["c0"]["M_u_kN_m"]), 4),
            "kappa_u_N0_1_m": round(float(datos["c0"]["kappa_u_1_m"]), 6),
            "criterio_falla_N0": datos["c0"]["criterio_falla"],
            "M_u_Ncomp_kN_m": round(float(datos["curvas"][datos["key_comp"]]["M_u_kN_m"]), 4),
            "N_compresion_kN": round(datos["N_casos_kN"][1], 2),
            "clasificacion": datos["clasificacion"]["clasificacion"],
        }
    payload = {
        "titulo": "Resumen comparativo DEMO_RC_EI vs DEMO_RC_EII",
        "nota": ("Ambas secciones comparten geometria documentada 0.70x0.70 "
                 "hormigon y el MISMO armado de demostracion; se diferencian solo "
                 "en fc (EI=40 MPa hipotesis del grupo; EII=35 MPa documentado). "
                 "HIPOTESIS_DEMOSTRACION, NO capacidad real de diseno."),
        "secciones": filas,
        "diferencia_Mu_N0_pct":
            round(100 * (filas["EI"]["M_u_N0_kN_m"] - filas["EII"]["M_u_N0_kN_m"])
                  / filas["EII"]["M_u_N0_kN_m"], 2),
        "escrito_en": {k: [str(p) for p in v] for k, v in escritos.items()},
    }
    jp = RES / "resumen_DEMO_RC_EI_EII.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")
    return jp


def main(argv=None) -> int:
    _ = argv if argv is not None else sys.argv[1:]
    out = {}
    all_datos = {}
    for edificio in ("I", "II"):
        RES.mkdir(parents=True, exist_ok=True)
        FIG.mkdir(parents=True, exist_ok=True)
        datos = _analizar(edificio)
        key = "EII" if edificio == "II" else "EI"
        jp = _escribir_json(edificio, datos)
        cp = _escribir_csv(edificio, datos)
        figs = _figuras(edificio, datos)
        out[key] = [jp, cp] + figs
        all_datos[edificio] = datos
        print(json.dumps({
            "seccion": "DEMO_RC_%s" % key,
            "edificio": edificio,
            "clasificacion": "HIPOTESIS_DEMOSTRACION",
            "fc_MPa": datos["seccion"]["materiales"]["hormigon"]["fc_MPa"],
            "M_u_N0_kN_m": round(float(datos["c0"]["M_u_kN_m"]), 4),
            "criterio_falla_N0": datos["c0"]["criterio_falla"],
            "escrito_en": [str(p) for p in out[key]]}, ensure_ascii=False, indent=2))
    sj = resumen_comparativo(all_datos["I"], all_datos["II"], out)
    print(json.dumps({"resumen_comparativo": str(sj)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())