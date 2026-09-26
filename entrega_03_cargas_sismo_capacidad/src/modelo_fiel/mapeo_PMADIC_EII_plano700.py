"""mapeo_PMADIC_EII_plano700 — auditoria y mapeo familia->viga del PM.ADIC
lineal del EII (plancha 2024_22-700), iteracion MODELO_FIEL_3 (tareas 3, 4 y 5).

Entradas (solo lectura):
  * data/externas/eii_viewer.json (copia interna del eii_viewer de
    analisis_estructural/edificio_II_casoG_PP_elementos/)
        - cargas.caso_G.PM_ADIC_lineal_kg_m (familias A..F)
        - nivele: losas (poligono), vigas (id+inicio/fin+seccion), muros
  * modelo_fiel/PM_ADIC_auditoria_EI_EII.json
        - EDIFICIO_II.familias (intensidad, conversion g, nivel_aplicabilidad,
          estado, motivo)

Salida:
  * Modelo de mapeo con 4 estados:
        MAPEO_CONFIRMADO / MAPEO_GEOMETRICO_DEFENDIBLE / AMBIGUO_NO_APLICADO /
        SIN_RECEPTOR
  * Tabla de mapeo + totales de cobertura (catalogada/mapeada/aplicada/pendiente)
  * Figuras de auditoria por nivel (plan de vigas/muros/losa + catalogo A-F con
    ambiguedad resaltada)

Escribo en modelo_fiel/:
  mapeo_PMADIC_EII_plano700.json / .md / .csv
  figuras_plano700/EII_<nivel>_plano700_auditoria.png

Uso:
  python -X utf8 -m src.modelo_fiel.mapeo_PMADIC_EII_plano700
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
FIG = OUT / "figuras_plano700"
EII_VIEWER = E3 / "data" / "externas" / "eii_viewer.json"
AUD = OUT / "PM_ADIC_auditoria_EI_EII.json"

G = 9.80665
G_KN_POR_KG = G / 1000.0

ESTADOS = ["MAPEO_CONFIRMADO", "MAPEO_GEOMETRICO_DEFENDIBLE",
           "AMBIGUO_NO_APLICADO", "SIN_RECEPTOR"]
AMBIGUO = "AMBIGUO_NO_APLICADO"


def leer_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fig = FIG.mkdir(parents=True, exist_ok=True) or None

    viewer = leer_json(EII_VIEWER)
    aud = leer_json(AUD)
    familias_raw = aud["EDIFICIO_II"]["familias"]
    cargas = viewer["cargas"]["caso_G"]
    q_kg_m = cargas["PM_ADIC_lineal_kg_m"]
    niveles = viewer["niveles"]

    # ---- tabla de mapeo por familia ----
    filas = []
    for f in familias_raw:
        fam = f["familia"]
        qkg = f["intensidad_original_kg_m"]
        qkn = round(qkg * G_KN_POR_KG, 6)
        filas.append({
            "segmento_plancha_700": "PM.ADIC-%s (%s)" % (fam, f["unidad_original"]),
            "familia": fam,
            "nivel_aplicabilidad_leyenda": f["nivel_aplicabilidad"],
            "intensidad_original": qkg,
            "unidad_original": f["unidad_original"],
            "naturaleza": f["naturaleza"],
            "q_kN_m": qkn,
            "factor_conversion": round(G / 1000.0, 6),
            "conversion_nota": f["conversion_nota"],
            "posicion_lamina_aprox": f["fuente"].split("bloque ")[-1]
            if "bloque " in f["fuente"] else None,
            "longitud_mapeada_m": f["longitud_confirmada_m"],
            "viga_FE_receptor": f["viga_receptor"],
            "carga_aplicada_kN": f["carga_total_kn"],
            "evidencia": f["fuente"],
            "estado": AMBIGUO,
            "motivo": f["motivo"]})

    n_cat = len(filas)
    n_mapeada = sum(1 for r in filas if r["estado"] in ("MAPEO_CONFIRMADO",
                                                        "MAPEO_GEOMETRICO_DEFENDIBLE"))
    n_pend = sum(1 for r in filas if r["estado"] not in ("MAPEO_CONFIRMADO",
                                                         "MAPEO_GEOMETRICO_DEFENDIBLE"))
    aplicada = 0.0
    cobertura = 0.0

    # contexto: receptores potenciales por nivel (solo informativo)
    receptores_por_nivel = []
    for nv in niveles:
        receptores_por_nivel.append({
            "nivel": nv["id"], "cota_m": nv["cota"], "n_vigas_fe": len(nv["vigas"]),
            "n_muros": len(nv["muros"])})
    n_vigas_total = sum(len(nv["vigas"]) for nv in niveles)

    payload = {
        "iteracion": "MODELO_FIEL_3",
        "tarea": "3_4_5_mapeo_PMADIC_EII_plano700",
        "gravedad_m_s2": G,
        "interpretacion_kg_m": ("Kg/m leido como masa lineal * g, o como kgf/m "
                                "esa misma unidad (1 kgf = 9.80665 N); ambos "
                                "dan el mismo q_kN/m. NO se asume kN/m directo."),
        "catalogo": {"n_familias": n_cat, "intensidades_kg_m": q_kg_m,
                     "total_intensidad_referencia_kn_m": round(
                         sum(f["q_kN_m"] for f in filas), 6)},
        "mapeo": {"n_mapeada": n_mapeada,
                  "criterios": ["nivel por leyenda", "posicion en lamina",
                                "eje modelo", "solape de tracing politlinas"],
                  "nota_criterios": ("la leyenda CP1S..CP3 no fija el elemento "
                                     "lineal receptor; el DXF no esta en el "
                                     "arbol; solo bloques de leyenda leidos"),
                  "filas": filas},
        "aplicacion": {"aplicada_al_FE_kN": aplicada,
                       "control_doble_conteo": "OK (aplicada=0; sin double counting)",
                       "cobertura": cobertura},
        "pendiente": {"n_pendiente": n_pend,
                      "motivo": "sin correspondencia familia->viga",
                      "requiere": ["DXF 2024_22-700 en el arbol",
                                   "coordenadas de estilo con unidad",
                                   "trazado de polilneas de la leyenda"]},
        "receptores_potenciales": {"por_nivel": receptores_por_nivel,
                                   "n_vigas_fe_total": n_vigas_total,
                                   "niveles_con_leyenda": "CP1S..CP3"},
        "resumen": {"catalogada": n_cat, "mapeada": n_mapeada,
                    "aplicada_kN": aplicada, "pendiente": n_pend,
                    "cobertura": cobertura}}

    (OUT / "mapeo_PMADIC_EII_plano700.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- CSV ----
    cols = ["segmento_plancha_700", "familia", "nivel_aplicabilidad_leyenda",
            "intensidad_original", "unidad_original", "q_kN_m",
            "conversion_nota", "posicion_lamina_aprox",
            "longitud_mapeada_m", "viga_FE_receptor", "carga_aplicada_kN",
            "evidencia", "estado", "motivo"]
    with open(OUT / "mapeo_PMADIC_EII_plano700.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in filas:
            w.writerow([r[c] for c in cols])

    # ---- MD ----
    l = []
    l.append("# mapeo_PMADIC_EII_plano700 (MODELO_FIEL_3 / t.3-4-5)")
    l.append("")
    l.append("Interpretacion de unidades: %s" % payload["interpretacion_kg_m"])
    l.append("")
    l.append("| familia | q (Kg/m) | q (kN/m) | leyenda | estado |")
    l.append("|---|---|---|---|---|")
    for r in filas:
        l.append("| %s | %s | %.6f | %s | **%s** |" % (
            r["familia"], r["intensidad_original"], r["q_kN_m"],
            r["nivel_aplicabilidad_leyenda"], r["estado"]))
    l.append("")
    l.append("Totales: catalogada=%d, mapeada=%d, aplicada_al_FE=**%.1f kN**, "
             "pendiente=%d, cobertura=%.1f%%" % (
                 n_cat, n_mapeada, aplicada, n_pend, cobertura * 100))
    l.append("")
    l.append("Motivo unico: %s" % filas[0]["motivo"] if filas else "-")
    l.append("")
    l.append("## Receptores potenciales (contexto, no mapeo)")
    l.append("")
    for rp in receptores_por_nivel:
        l.append("- %s (cota %.2f): %d vigas FE, %d muros" % (
            rp["nivel"], rp["cota_m"], rp["n_vigas_fe"], rp["n_muros"]))
    l.append("- Total vigas FE en el modelo: %d" % n_vigas_total)
    l.append("")
    l.append("Figuras por nivel en `modelo_fiel/figuras_plano700/`.")
    (OUT / "mapeo_PMADIC_EII_plano700.md").write_text(
        "\n".join(l) + "\n", encoding="utf-8")

    # ---- figuras por nivel ----
    for nv in niveles:
        figw = plt.figure(figsize=(13, 9.5))
        ax = figw.add_subplot(111)
        ax.set_title("EII %s (cota %.2f) — plan PM.ADIC plancha 700 | "
                     "ambiguedad: A-F sin receptor mapeable"
                     % (nv["id"], nv["cota"]))
        ax.set_aspect("equal")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")

        x_id = None
        for losa in nv["losas"]:
            pg = losa["poligono_exterior"]
            pg = pg + [pg[0]]
            xs, ys = zip(*pg)
            ax.plot(xs, ys, "-", color="#b0b8c8", lw=0.7, zorder=1)
        for viga in nv["vigas"]:
            (x0, y0), (x1, y1) = viga["inicio"], viga["fin"]
            ax.plot([x0, x1], [y0, y1], "-", color="#1f3f66", lw=1.6,
                    zorder=3)
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, viga["id"].split("_V_")[-1],
                    fontsize=5.5, color="#1f3f66", ha="center", va="center",
                    zorder=4)
            x_id = viga["id"]
        for muro in nv["muros"]:
            eje = muro["eje"]
            (x0, y0), (x1, y1) = eje["inicio"], eje["fin"]
            ax.plot([x0, x1], [y0, y1], "-", color="#6b1f1f", lw=3.0,
                    alpha=0.75, zorder=2)

        # caja de catalogo A-F
        txt = []
        for r in filas:
            txt.append("%s  q=%d Kg/m  = %.6f kN/m   [%s]"
                       % (r["familia"], r["intensidad_original"], r["q_kN_m"],
                          r["estado"]))
        txt.append("")
        txt.append("Posturas en lamina (approx.):")
        for r in filas:
            if r["posicion_lamina_aprox"]:
                txt.append("  %s -> %s" % (r["familia"],
                                           r["posicion_lamina_aprox"]))
        txt.append("")
        txt.append("PM.ADIC aplicada al FE = 0 kN (cobertura 0%)")
        ax.text(0.02, 0.98, "\n".join(txt), transform=ax.transAxes,
                fontsize=7, va="top", ha="left",
                bbox=dict(boxstyle="round", facecolor="#fff2cc",
                          edgecolor="#b8860b", alpha=0.92), zorder=5)

        ax.autoscale()
        s = 1.5
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        ax.set_xlim(xmin - s, xmax + s)
        ax.set_ylim(ymin - s, ymax + s)
        ax.grid(True, alpha=0.3)
        name = "EII_%s_plano700_auditoria.png" % nv["id"]
        figw.savefig(FIG / name, dpi=140, bbox_inches="tight")
        plt.close(figw)

    print(json.dumps({"mapeo_PMADIC_EII_plano700": True,
                      "familia_aplicada_kN": aplicada,
                      "resumen": payload["resumen"],
                      "n_vigas_fe_total": n_vigas_total,
                      "figuras": len(niveles)}, ensure_ascii=False, indent=2))
    return 0 if aplicada == 0.0 and cobertura == 0.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())