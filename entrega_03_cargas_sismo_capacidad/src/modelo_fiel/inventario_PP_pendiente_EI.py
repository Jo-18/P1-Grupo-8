"""inventario_PP_pendiente_EI â€” inventario por elemento del PP PENDIENTE del EI
(iteracion MODELO_FIEL_3, tarea 2).

Cruce read-only de `results/peso_propio_teorico_EDIFICIO_I_v2.json`
(pendientes, no_incluidas, hipotesis_tramos_base_kN, muros_contencion_sotano,
densidades, decisiones_usuario, alcance_PP_confirmado) para producir el
inventario de 11 columnas:

  id | nivel | tipo | longitud/area/volumen | seccion rotulada | material conocido |
  material pendiente | motivo de exclusion | peso potencial | documentos
  revisados | decision

Reglas (decisiones_usuario v2, vigentes):
  * D3  : sin tramos sinteticos BASE->nivel (solo extremos reales).
  * D2  : muro de un solo plano NO se vuelve continuo automaticamente.
  * D4  : desfase P4 +0.1813 m en Y -> PENDIENTE (no implementado en el FE).
  * D5  : V.S.I. 20/150 = hipotesis de grupo (gran canto HA 0.20x1.50, pp~157 kN),
          NO confirmada.
  * D6  : V_EI_CP1S_x1010 M.H.A. e=30 = muro del eje F (no viga adicional).
  * D7  : banda de sensibilidad 20.3-21.2 MN NO adoptada como PP.
  * Sec. 300x300x20 / 300x300x5 = SECCION_CONFIRMADA_TUBULAR; falta tramo real.
  * P.M.I. sin dimensiones BxHxt en el QA -> PENDIENTE_SECCION (pp no cuantificable).
  * Hormigon P3->P4 -> PENDIENTE_TRAMO (desfase; el FE no instancia el tramo).

Escribo en modelo_fiel/:
  inventario_PP_pendiente_EI.json / .md / .csv

Uso:
  python -X utf8 -m src.modelo_fiel.inventario_PP_pendiente_EI
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
RES = E3 / "results"

SRC = RES / "peso_propio_teorico_EDIFICIO_I_v2.json"


def leer_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fila(id_, nivel, tipo, seccion, area_m2, L_m, material_ok, material_pdte,
         pp_m_unit, motivo, estado, decision, docs):
    return {
        "id": id_, "nivel": nivel, "tipo": tipo, "seccion": seccion,
        "area_m2": area_m2, "L_m": L_m,
        "volumen_m3": (round(L_m * area_m2, 6)
                       if (L_m and area_m2) else None),
        "pp_m_unit_kN_m": round(pp_m_unit, 4) if pp_m_unit else None,
        "pp_potencial_kN": (round(L_m * pp_m_unit, 4)
                            if (L_m and pp_m_unit) else None),
        "material_conocido": material_ok, "material_pendiente": material_pdte,
        "motivo": motivo, "estado": estado, "decision": decision,
        "documentos_revisados": docs}


def main(argv=None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    v2 = leer_json(SRC)
    dec = v2["decisiones_usuario"]
    dens = v2["densidades"]
    gam_h = dens["concreto_kN_m3"]
    gam_a = dens["acero_a36_hipotesis_kN_m3"]
    fuentes = v2["fuentes"]
    docs_base = list(fuentes) + [
        "results/peso_propio_teorico_EDIFICIO_I_v2.json (objeto)"] 

    rows = []
    p = v2["pendientes"]

    # ---- vigas pendientes ----
    for it in p["vigas"]:
        rows.append(fila(
            it["id"], it["nivel"], "viga", it["seccion"], None, it.get("L_m"),
            "pendiente (V.S.I. no fija hormigon/acero)", "tipo+seccion",
            None,
            it["motivo"], "PENDIENTE_SECCION",
            dec["v_s_i_20_150"], docs_base))

    # ---- columnas pendientes ----
    for it in p["columnas"]:
        sec = it["seccion"]
        if sec in ("P.M. 300x300x20", "V.M. 300x300x5"):
            area = it.get("area_m2")
            rows.append(fila(
                it["id"], it["nivel"], "columna metalica (tubular)", sec, area,
                it.get("L_m"), "acero (seccion tubular confirmada)",
                "tramo real documentado (base->nivel real, no hipotesis)",
                area * gam_a, it["motivo"], it["estado"],
                dec[("perfiles_300x300x20_y_300x300x5" if False
                     else "metalicos_tramo_simple")], docs_base))
        elif sec == "P.M.I.":
            rows.append(fila(
                it["id"], it["nivel"], "columna metalica (P.M.I.)", sec, None,
                None, "acero (perfil metalico)", "dimensiones BxHxt",
                None, it["motivo"], "PENDIENTE_SECCION",
                dec["p_m_i_sin_dimension"], docs_base))
        elif sec == "P. 70x70":
            area = it.get("area_m2")
            rows.append(fila(
                it["id"], it["nivel"], "columna de hormigon", sec, area, None,
                "hormigon armado", "tramo P3->P4 (desfase por implementar)",
                area * gam_h, it["motivo"], "PENDIENTE_TRAMO",
                dec["hormigon_p3_p4"], docs_base))
        else:
            rows.append(fila(
                it["id"], it["nivel"], "columna", sec, it.get("area_m2"), None,
                "pendiente", "material/tramo", None, it["motivo"],
                it["estado"], "revisar", docs_base))

    # ---- muros pendientes ----
    for it in p["muros"]:
        rows.append(fila(
            None, it["nivel"], "muro (1 sola planta documentada)",
            "sin seccion/espesor/cotas confirmados", None, it.get("L_m"),
            "presumible concreto (M.H.A.)", "espesor + cotas + niveles reales",
            None, it["motivo"], "PENDIENTE_TRAMO", dec["D2_cajas_ascensor"],
            docs_base))

    # ---- no incluidas ----
    for it in v2["no_incluidas"]["vigas"]:
        rows.append(fila(
            it["id"], it["nivel"], "no viga (muro e=30 eje F)", it["seccion"],
            None, it.get("L_m"), "muro M.H.A. e=30", "-",
            None, it["motivo"], "NO_INCLUIDA",
            dec["D6_M_H_A_e30"], docs_base))

    # ---- revision extra: hipotesis y elementos no confirmables -----------
    extra = []
    base = v2["hipotesis_tramos_base_kN"]
    extra.append(fila(
        "hyp_base_columnas", "P1..base", "hipotesis FE base->nivel (columnas)",
        "P. 70x70 (FE)", None, None, "hormigon", "cimentacion no documentada",
        None,
        "hipotesis FE base->nivel (z=-4.01); cimentacion no documentada",
        "PENDIENTE_HIPOTESIS_FE", dec["D3_tramos_a_la_base"], docs_base))
    extra.append(fila(
        "hyp_base_muros", "CP1S..base",
        "hipotesis FE base->nivel (muros)", "segun FE", None, None,
        "concreto", "cimentacion no documentada", None,
        "hipotesis FE base->nivel; fuera del total confirmado",
        "PENDIENTE_HIPOTESIS_FE", dec["D3_tramos_a_la_base"], docs_base))
    for mid, mt in v2["muros_contencion_sotano"].items():
        extra.append(fila(
            mid, "sotano (-7.01)", "muro de contencion del sotano",
            "e=%.1f m (panel %.2f m)" % (mt["e_m"], mt["panel_m"]),
            mt["panel_m"] * mt["e_m"], None, "concreto",
            "h real del sotano (hipotesis h=3.0 m)",
            None, mt["nota"], mt["estado"], "HIPOTESIS_CIMENTACION", docs_base))
    rows_principales = list(rows)
    rows = rows + extra

    # ---- consolidado ----
    n_pend = v2["n_pendientes"]
    n_conf = v2["n_confirmadas"]
    n_noinc = v2["n_no_incluidas"]
    rango_cuantificado = (
        base["columnas"] + base["muros"]
        + sum(m["pp_kN"] for m in v2["muros_contencion_sotano"].values()))

    per_metro = {}
    for r in rows_principales:
        if r["pp_m_unit_kN_m"] and r["pp_m_unit_kN_m"] not in [
                x for x in per_metro.values()]:
            pass
    fam = {}
    for r in rows_principales:
        if r["pp_m_unit_kN_m"]:
            fam.setdefault(r["seccion"], r["pp_m_unit_kN_m"])
    per_metro = [{"seccion": k, "pp_m_unit_kN_m": v} for k, v in fam.items()]

    payload = {
        "iteracion": "MODELO_FIEL_3", "tarea": "2_inventario_PP_pendiente_EI",
        "fuente": str(SRC),
        "densidades": dens,
        "alcance_PP_confirmado": v2["alcance_PP_confirmado"],
        "PP_confirmado_kN": v2["PP_confirmado_kN"],
        "PP_provisional_kN": v2["PP_provisional_kN"],
        "PP_pendiente_kN": v2["PP_pendiente_kN"],
        "PP_no_incluido_por_falta_de_evidencia_kN":
            v2["PP_no_incluido_por_falta_de_evidencia_kN"],
        "conteo": {"pendientes": n_pend, "no_incluidas": n_noinc,
                   "confirmadas_viga": n_conf["vigas"],
                   "confirmadas_columna": n_conf["tramos_columna"],
                   "confirmadas_muro": n_conf["paneles_muro"]},
        "revision_extra": {
            "hipotesis_tramos_base_kN": base,
            "muros_contencion_sotano": v2["muros_contencion_sotano"],
            "total_hipotesis_cuantificado_kN": round(rango_cuantificado, 4),
            "nota": ("rango superior SOLO si se confirmaran tramos reales y "
                     "cimentacion; NO se aplica (D3/D7)")},
        "pp_por_metro_por_familia_kN_m": per_metro,
        "total_filas_principal": len(rows_principales),
        "total_filas_con_extra": len(rows),
        "aplicado_al_FE_kN": 0.0,
        "observacion": ("no se convierte ninguna hipotesis en elemento "
                        "confirmado; ningun pendiente se aplica en v3"),
        "filas": rows}

    (OUT / "inventario_PP_pendiente_EI.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    cols = ["id", "nivel", "tipo", "seccion", "area_m2", "L_m", "volumen_m3",
            "pp_m_unit_kN_m", "pp_potencial_kN", "material_conocido",
            "material_pendiente", "motivo", "estado", "decision",
            "documentos_revisados"]
    with open(OUT / "inventario_PP_pendiente_EI.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])

    l = []
    l.append("# inventario_PP_pendiente_EI (MODELO_FIEL_3 / tarea 2)")
    l.append("")
    l.append("PP confirmado (cota inferior): **%.4f kN**" % v2["PP_confirmado_kN"])
    l.append("PP provisional: %.4f kN ; PP pendiente: %s ; no incluido: %s"
             % (v2["PP_provisional_kN"], v2["PP_pendiente_kN"],
                v2["PP_no_incluido_por_falta_de_evidencia_kN"]))
    l.append("")
    l.append("Pendientes: vigas %d, columnas %d, muros %d ; no incluidas %d."
             % (len(p["vigas"]), len(p["columnas"]), len(p["muros"]),
                len(v2["no_incluidas"]["vigas"])))
    l.append("")
    l.append("## Por metro (familias con seccion+densidad documentadas)")
    l.append("")
    for x in per_metro:
        l.append("- %s : %.4f kN/m" % (x["seccion"], x["pp_m_unit_kN_m"]))
    l.append("")
    l.append("## Revisados y NO aplicados (hipotesis/falta de evidencia)")
    l.append("")
    l.append("- Tramso base->nivel columnas: %.4f kN (hipotesis FE)"
             % base["columnas"])
    l.append("- Tramos base->nivel muros: %.4f kN (hipotesis FE)" % base["muros"])
    for mid, mt in v2["muros_contencion_sotano"].items():
        l.append("- %s contencion: %.4f kN [%s]" % (mid, mt["pp_kN"],
                                                    mt["estado"]))
    l.append("- Total hipotesis cuantificadas (rango superior SI se confirmara "
             "la cimentacion): **%.2f kN**" % rango_cuantificado)
    l.append("")
    l.append("## Tabla")
    l.append("")
    for i, r in enumerate(rows_principales, start=1):
        l.append("%d. `%s` %s nivel=%s %s L=%.2f | estado=%s | decision=%s"
                 % (i, r["id"] or "(muro)", r["tipo"], r["nivel"],
                    r["seccion"], r["L_m"] if r["L_m"] else 0.0,
                    r["estado"], r["decision"]))
    (OUT / "inventario_PP_pendiente_EI.md").write_text(
        "\n".join(l) + "\n", encoding="utf-8")

    print(json.dumps({"inventario_PP_pendiente_EI": True,
                      "pendientes": {"vigas": len(p["vigas"]),
                                     "columnas": len(p["columnas"]),
                                     "muros": len(p["muros"])},
                      "no_incluidas": len(v2["no_incluidas"]["vigas"]),
                      "PP_confirmado_kN": v2["PP_confirmado_kN"],
                      "total_hipotesis_cuantificado_kN": round(rango_cuantificado, 4),
                      "pp_por_metro_kN_m": per_metro,
                      "aplicado_al_FE_kN": 0.0}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
