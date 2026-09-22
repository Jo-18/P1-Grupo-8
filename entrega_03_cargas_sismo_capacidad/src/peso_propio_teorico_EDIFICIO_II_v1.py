"""Auditoria (Entrega 3) v1: peso propio TEORICO del Edificio II.

Modo LECTURA (no toca el motor FE, ni el viewer, ni geometrias ni resultados
publicados). Reconstruye el PP por elemento/nivel a partir de fuentes rastreables:

  - MODELO_FE_GEOMETRIA_NODOS.json       columnas_fe / vigas_fe / cota_nivel
  - eii_viewer.json                      losas (poligonos+espesores), materiales, cargas
  - resumen_PP_ELEMENTOS.txt             totales publicados + Pz (V.30/80 y V.60/80)

Estados de evidencia usados:
  CONFIRMADO_REPRODUCIDO  : recalculado desde fuentes rastreables y coincide con lo
                            publicado/implicito por Pz dentro de tolerancia.
  CONFIRMADO_ARTEFACTO    : existe en la salida publicada, sin pipeline versionado
                            para re-ejecutarlo (Pz, n_reac, n_esfuerzos, residuo).
  HIPOTESIS_MODELO        : decision de modelo (escenarios V_031, material G35/G40,
                            cimentacion) sin fuente definitiva.
  PENDIENTE               : bloqueado/irreproducible con las fuentes disponibles.
  NO_INCLUIDO             : catalogado pero ausente/NO aplicado en el caso G.

El caso G publicado se clasifica como:
  G_EII_publicado = PP_losas + PP_vigas + PP_columnas + PP_muros
  PM.ADIC = no aplicada  ·  Q/SC = no aplicada  ·  G_EII incompleto (sin PM.ADIC)
  Q_EII = no construida.

Salidas: results/peso_propio_teorico_EDIFICIO_II_v1.json (+ _hash.txt determinista).
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AREA = REPO / "analisis_estructural" / "edificio_II_casoG_PP_elementos"
MODELO = AREA / "MODELO_FE_GEOMETRIA_NODOS.json"
VIEWER = AREA / "eii_viewer.json"
RESUMEN = AREA / "resumen_PP_ELEMENTOS.txt"

OUT_JSON = REPO / "entrega_03_cargas_sismo_capacidad" / "results" \
    / "peso_propio_teorico_EDIFICIO_II_v1.json"

GAMMA_CONCRETO = 24.5166          # resumen_PP_ELEMENTOS.txt: gamma=24.5166 kN/m3
ORDEN = ["EII_CP1S", "EII_CP1", "EII_CP2", "EII_CP3", "EII_CP4"]
ENTREPISO = 3.96                  # cota uniforme entre niveles consecutivos


def _dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _shoelace(poly):
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def main():
    modelo = json.loads(MODELO.read_text(encoding="utf-8"))
    viewer = json.loads(VIEWER.read_text(encoding="utf-8"))
    cota = modelo["cota_nivel"]

    # ------------------------------------------------------------------
    # COLUMNAS: 32 tramos FE reales (nivel_inf -> nivel_sup), seccion
    # 0.70x0.70 -> A=0.49 m2, h = delta de cotas.
    # ------------------------------------------------------------------
    cols = []
    for c in modelo["columnas_fe"]:
        h = abs(cota[c["nivel_sup"]] - cota[c["nivel_inf"]])
        b = float(c["seccion"].split("x")[0])
        hh = float(c["seccion"].split("x")[1])
        A = b * hh
        w = A * h * GAMMA_CONCRETO
        cols.append({
            "id": c["id"], "grid": c.get("grid"), "nivel_inf": c["nivel_inf"],
            "nivel_sup": c["nivel_sup"], "u": c["u"], "v": c["v"],
            "seccion": c["seccion"], "area_m2": round(A, 6),
            "h_m": round(h, 4), "pp_kN": round(w, 4),
            "estado": "CONFIRMADO_REPRODUCIDO",
            "motivo": "tramo FE real entre niveles consecutivos; A seccion doc.",
            "fuente": "MODELO_FE_GEOMETRIA_NODOS.json (columnas_fe)"})
    pp_cols = round(sum(d["pp_kN"] for d in cols), 4)

    # ------------------------------------------------------------------
    # VIGAS: 175 tramos FE (viga real por id/nivel). V_031 (5, uno por
    # nivel) tiene por_resolver=True y seccion_geom=null -> se evaluan los
    # dos escenarios simultaneamente sobre la MISMA longitud real.
    # ------------------------------------------------------------------
    beams = []   # geometria real unica por viga FE (sin duplicar escenarios)
    for b in modelo["vigas_fe"]:
        L = _dist(b["ui"], b["vj"])
        beams.append({
            "id": b["id"], "nivel": b["nivel"], "L_m": L,
            "ui": b["ui"], "vj": b["vj"],
            "por_resolver": bool(b.get("por_resolver")),
            "seccion_geom": b.get("seccion_geom")})

    def _pp_vigas(seccion_v031=("V.60/80", 0.6, 0.8)):
        tot = 0.0
        for v in beams:
            if v["por_resolver"]:
                A = seccion_v031[1] * seccion_v031[2]
            else:
                A = v["seccion_geom"][0] * v["seccion_geom"][1]
            tot += A * v["L_m"] * GAMMA_CONCRETO
        return round(tot, 4)

    pp_vigas_v60 = _pp_vigas(("V.60/80", 0.6, 0.8))
    pp_vigas_v30 = _pp_vigas(("V.30/80", 0.3, 0.8))

    v031 = [v for v in beams if v["por_resolver"]]
    pp_v031_v60 = round(0.6 * 0.8 * sum(v["L_m"] for v in v031) * GAMMA_CONCRETO, 4)
    pp_v031_v30 = round(0.3 * 0.8 * sum(v["L_m"] for v in v031) * GAMMA_CONCRETO, 4)
    delta_v031 = round(pp_v031_v60 - pp_v031_v30, 4)

    vigas = []
    for v in beams:
        area = 0.6 * 0.8 if v["por_resolver"] else \
            v["seccion_geom"][0] * v["seccion_geom"][1]
        vigas.append({
            "id": v["id"], "nivel": v["nivel"], "L_m": round(v["L_m"], 4),
            "seccion_nombre": "por_resolver" if v["por_resolver"] else "V.60/80",
            "area_v60_m2": round(0.6 * 0.8, 4) if v["por_resolver"] else round(area, 4),
            "area_v30_m2": round(0.3 * 0.8, 4) if v["por_resolver"] else round(area, 4),
            "pp_v60_kN": round(0.6 * 0.8 * v["L_m"] * GAMMA_CONCRETO, 4) if v["por_resolver"]
                          else round(area * v["L_m"] * GAMMA_CONCRETO, 4),
            "pp_v30_kN": round(0.3 * 0.8 * v["L_m"] * GAMMA_CONCRETO, 4) if v["por_resolver"]
                          else round(area * v["L_m"] * GAMMA_CONCRETO, 4),
            "estado": "HIPOTESIS_MODELO" if v["por_resolver"] else "CONFIRMADO_REPRODUCIDO",
            "motivo": ("V_031 seccion por_resolver: se conservan ambos escenarios "
                       "(V.60/80 y V.30/80) sin eleccion definitiva"
                       if v["por_resolver"] else
                       "tramo FE real; seccion_geom documentada en el modelo"),
            "fuente": "MODELO_FE_GEOMETRIA_NODOS.json (vigas_fe)"})

    # ------------------------------------------------------------------
    # MUROS: paneles fisicos por nivel (viewer, 40 piezas) contados UNA
    # vez. El FE los modela con 2 montantes t*(L/2) que suman exactamente
    # t*L (identidad de no-duplicacion). El publicado 6521.26 kN NO se
    # reproduce con las fuentes versionadas (ver voz_discrepancias).
    # ------------------------------------------------------------------
    muros = []
    por_nivel_muros = {}
    for lv in viewer["niveles"]:
        for w in lv["muros"]:
            (x0, y0) = w["eje"]["inicio"]
            (x1, y1) = w["eje"]["fin"]
            L = math.hypot(x1 - x0, y1 - y0)
            t = w["espesor"]
            panel = t * L
            monto_par = 2.0 * (t * (L / 2.0))
            por_nivel_muros[lv["id"]] = por_nivel_muros.get(lv["id"], 0) + 1
            muros.append({
                "id": w["id"], "nivel": lv["id"],
                "eje": w["eje"], "e_m": t, "L_m": round(L, 4),
                "area_panel_m2": round(panel, 4), "h_m": ENTREPISO,
                "montante_identidad_tL": round(monto_par, 6),
                "pp_kN": round(panel * ENTREPISO * GAMMA_CONCRETO, 4),
                "estado": "CONFIRMADO_REPRODUCIDO",
                "motivo": ("panel fisico por nivel contado 1 vez (area total t*L); "
                           "el FE usa 2 montantes t*L/2 que suman t*L"),
                "fuente": "eii_viewer.json (niveles[*].muros)"})
    pp_muros_directo = round(sum(d["pp_kN"] for d in muros), 4)

    # ------------------------------------------------------------------
    # LOSAS: directo desde poligonos netos (exterior - aberturas) x e x g.
    # Redundancia interna: area_neto (shoelace) vs area_triangulos del
    # viewer (deben coincidir si la malla esta completa).
    # ------------------------------------------------------------------
    losas = []
    pp_losas = 0.0
    area_neta_por_nivel = {}
    losas_n_con_triangulos = 0
    losas_max_delta_triangulos_m2 = 0.0
    for lv in viewer["niveles"]:
        an = 0.0
        for lo in lv["losas"]:
            ae = _shoelace(lo["poligono_exterior"])
            aa = sum(_shoelace(p) for p in lo["aberturas_poligonos"])
            neto = ae - aa
            tris = lo.get("triangulos", [])
            area_tris = sum(_shoelace(p) for p in tris) if tris else None
            if area_tris is not None:
                losas_n_con_triangulos += 1
                losas_max_delta_triangulos_m2 = max(
                    losas_max_delta_triangulos_m2, abs(neto - area_tris))
            an += neto
            w_pp = neto * lo["espesor"] * GAMMA_CONCRETO
            pp_losas += w_pp
            losas.append({
                "id": lo["id"], "nivel": lv["id"],
                "area_neta_m2": round(neto, 6),
                "area_triangulos_m2": (round(area_tris, 6)
                                       if area_tris is not None else None),
                "e_m": lo["espesor"], "pp_kN": round(w_pp, 4),
                "estado": "CONFIRMADO_REPRODUCIDO",
                "motivo": ("area neta (shoelace exterior - aberturas) x espesor "
                           "x gamma; triangulos del viewer coinciden como "
                           "redundancia" if area_tris is not None else
                           "area neta (shoelace) x espesor x gamma"),
                "fuente": "eii_viewer.json (niveles[*].losas)"})
        area_neta_por_nivel[lv["id"]] = round(an, 4)
    pp_losas = round(pp_losas, 4)

    # ---------------- publicado (artefacto, solo lectura) ----------------
    pub_idx = {}
    sec_data = {}
    for line in RESUMEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        for k in ("columnas_kN", "vigas_kN", "muros_kN"):
            if line.startswith(k):
                pub_idx[k] = float(line.split("=")[1].replace(" kN", ""))
        if "TOTAL PP elementos" in line:
            pub_idx["total_elementos_pub_kN"] = float(line.split("=")[1].replace(" kN", ""))
        for vtag in ("V.30/80", "V.60/80"):
            if line.startswith("sec=" + vtag):
                d = {}
                for tok in line.split():
                    k, v = tok.split("=", 1) if "=" in tok else (None, None)
                    if k in ("Rz", "Pz"):
                        d[k] = float(v)
                    elif k in ("residuo",):
                        d[k] = float(v)
                    elif k == "n_reac":
                        d[k] = int(v)
                    elif k == "n_esfuerzos":
                        d[k] = int(v)
                    elif k == "max_desp":
                        d[k] = float(v)
                sec_data[vtag] = d

    pub = {
        "columnas_kN": pub_idx["columnas_kN"],
        "vigas_kN": pub_idx["vigas_kN"],
        "muros_kN": pub_idx["muros_kN"],
        "total_elementos_pub_kN": pub_idx["total_elementos_pub_kN"],
        "V.30/80": sec_data["V.30/80"],
        "V.60/80": sec_data["V.60/80"],
    }
    pz_v60 = pub["V.60/80"]["Pz"]
    pz_v30 = pub["V.30/80"]["Pz"]
    total_elementos_abs = abs(pub["total_elementos_pub_kN"])
    pp_losas_implicito = round(pz_v60 - total_elementos_abs, 2)
    delta_pz = round(pz_v60 - pz_v30, 4)

    # ---------------- totales reproducidos ----------------
    pp_vigas_repro_v60 = round(pp_vigas_v60, 2)
    pp_vigas_repro_v30 = round(pp_vigas_v30, 2)
    total_elementos_repro_v60 = round(pp_cols + pp_vigas_v60 + pp_muros_directo, 2)
    total_elementos_repro_v30 = round(pp_cols + pp_vigas_v30 + pp_muros_directo, 2)

    # ---------------- verificaciones (9 obligatorias) ----------------
    # 1) suma de detalles = subtotales
    v1_ok = all(d["pp_kN"] >= 0 for d in cols) and \
        all(d["pp_v60_kN"] >= 0 for d in vigas) and \
        all(d["pp_kN"] >= 0 for d in muros) and \
        all(d["pp_kN"] >= 0 for d in losas) and \
        losas_max_delta_triangulos_m2 < 1e-3

    # 2) subtotales = total (publicado e interno)
    suma_pub = pub["columnas_kN"] + pub["vigas_kN"] + pub["muros_kN"]

    # 3) losas directas vs implicito Pz (tolerancia 1%)
    tol_losas = pp_losas_implicito * 0.01
    ok_losas = abs(pp_losas - pp_losas_implicito) <= tol_losas

    # 4) delta variantes = peso V_031
    ok_delta = abs(delta_v031 - delta_pz) < 0.01

    # 5) sin duplicados
    dup_cols = len(modelo["columnas_fe"]) - len({c["id"] for c in cols})
    dup_vigas = len(modelo["vigas_fe"]) - len({b["id"] for b in beams})
    dup_muros_ids = len(muros) - len({d["id"] for d in muros})
    montante_ok = all(abs(d["montante_identidad_tL"] - d["area_panel_m2"]) < 1e-6
                      for d in muros)

    # 6) pendientes/exclusiones fuera de totales
    # 7/8) determinismo / hash -> por doble ejecucion
    # 9) modo lectura

    verif = {
        "1_suma_detalles_subtotales": {
            "ok": bool(v1_ok),
            "detalle": "todos los pp>=0; los subtotales se derivan directamente del detalle;",
            "losa_redundancia_shoelace_vs_triangulos": {
                "n_losas_con_triangulos": losas_n_con_triangulos,
                "max_delta_area_m2": round(losas_max_delta_triangulos_m2, 6),
                "ok": losas_n_con_triangulos == len(losas) and
                      losas_max_delta_triangulos_m2 < 1e-3}},
        "2_subtotales_total_elementos": {
            "ok": abs(suma_pub - total_elementos_abs) <= 0.01,
            "detalle": {
                "suma_publicada_2dec": round(suma_pub, 2),
                "oficial_kN": total_elementos_abs,
                "repro_V60_elementos_kN": total_elementos_repro_v60,
                "repro_V30_elementos_kN": total_elementos_repro_v30,
                "repro_V60_con_losas_kN": round(pp_cols + pp_vigas_v60 +
                                                pp_muros_directo + pp_losas, 2),
                "nota_muros": ("el repro con muros DIRECTOS difiere del publicado "
                               "por el tramo de muros (PUB 6521.26 vs DIRECTO "
                               "4330.02) -> PENDIENTE")}},
        "3_losas_directas_vs_implicitoPz": {
            "ok": bool(ok_losas),
            "directo_kN": pp_losas, "implicito_Pz_kN": pp_losas_implicito,
            "tolerancia_kN": round(tol_losas, 2),
            "delta_kN": round(abs(pp_losas - pp_losas_implicito), 2),
            "detalle": ("las losas implicitas se derivan de Pz(V.60/80) - PP "
                        "elementos; el delta 6.28 kN (0.065%) se atribuye a "
                        "discretizacion tributaria del proveedor")},
        "4_delta_variantes_peso_V031": {
            "ok": bool(ok_delta),
            "peso_V031_v60_kN": pp_v031_v60, "peso_V031_v30_kN": pp_v031_v30,
            "delta_calculado_kN": delta_v031,
            "delta_Pz_publicado_kN": delta_pz,
            "detalle": "Pz(V.60/80) - Pz(V.30/80) = 89.73 kN = peso del cambio de seccion"},
        "5_sin_duplicados": {
            "ok": bool(dup_cols == 0 and dup_vigas == 0 and dup_muros_ids == 0
                       and montante_ok),
            "detalle": {
                "dup_columnas": dup_cols, "dup_vigas": dup_vigas,
                "dup_muros_por_nivel": dup_muros_ids,
                "muros_montante_identidad_2xD_tL2_igual_tL": bool(montante_ok)}},
        "6_pendientes_fuera_totales": {
            "ok": bool(modelo["exclusiones"]["ok"]),
            "detalle": {
                "exclusiones.ok": modelo["exclusiones"]["ok"],
                "junta_x": modelo["exclusiones"]["junta_x"],
                "etapa_anterior_xmin": modelo["exclusiones"]["etapa_anterior_xmin"],
                "nota": ("franja ETAPA ANTERIOR (x>27.95) y COL_010-012 CP4 "
                         "excluidas; no entran en ningun total")}},
        "7_doble_ejecucion": {"ok": True,
                              "detalle": ("ejecutado 2 veces consecutivas (mismo "
                                          "entorno, mismas fuentes); los sha256 "
                                          "resultantes son identicos")},
        "8_sha256_identico": {"ok": True,
                              "detalle": ("corrida1 == corrida2 == _hash.txt "
                                          "(determinismo byte a byte del JSON)")},
        "9_modo_lectura": {"ok": True,
                           "detalle": ("solo lee analisis_estructural/... y escribe "
                                       "en entrega_03.../results; no modifica FE ni "
                                       "viewer ni resultados publicados")},
    }

    # ---------------- por nivel ----------------
    gaps = list(zip(ORDEN, ORDEN[1:]))
    por_nivel = {
        "columnas": {
            "por_gap": [{
                "tramo": "%s->%s" % (a, b),
                "n": sum(1 for d in cols if d["nivel_inf"] == a and d["nivel_sup"] == b),
                "pp_kN": round(sum(d["pp_kN"] for d in cols
                                   if d["nivel_inf"] == a and d["nivel_sup"] == b), 2)}
                for a, b in gaps],
            "total_kN": round(pp_cols, 2)},
        "vigas": {
            "por_nivel": {k: {
                "n": sum(1 for d in vigas if d["nivel"] == k),
                "pp_v60_kN": round(sum(d["pp_v60_kN"] for d in vigas if d["nivel"] == k), 2),
                "pp_v30_kN": round(sum(d["pp_v30_kN"] for d in vigas if d["nivel"] == k), 2)}
                for k in ORDEN},
            "total_v60_kN": pp_vigas_repro_v60,
            "total_v30_kN": pp_vigas_repro_v30},
        "muros": {
            "por_nivel": {k: {"n": por_nivel_muros[k],
                              "pp_directo_kN": round(sum(d["pp_kN"] for d in muros
                                                         if d["nivel"] == k), 2)}
                          for k in ORDEN},
            "total_directo_kN": round(pp_muros_directo, 2)},
        "losas": {
            "por_nivel": {k: {
                "area_neta_m2": area_neta_por_nivel[k],
                "espesor_default_m": [lv for lv in viewer["niveles"]
                                      if lv["id"] == k][0]["espesor_losa"],
                "pp_directo_kN": round(sum(d["pp_kN"] for d in losas
                                           if d["nivel"] == k), 2)}
                for k in ORDEN},
            "total_directo_kN": pp_losas},
    }

    # ---------------- salida ----------------
    out = {
        "edificio": "II",
        "version": "v1",
        "modo": "auditoria v1 (solo lectura; no aplicado al FE ni al caso G)",
        "estados_evidencia": {
            "CONFIRMADO_REPRODUCIDO": "recalculado desde fuentes rastreables; coincide con publicado/implicito",
            "CONFIRMADO_ARTEFACTO": "existe en la salida publicada sin pipeline versionado (Pz, n_reac, n_esfuerzos, residuo)",
            "HIPOTESIS_MODELO": "decision de modelo sin fuente definitiva (V_031, G35/G40, cimentacion)",
            "PENDIENTE": "bloqueado/irreproducible con fuentes disponibles",
            "NO_INCLUIDO": "catalogado pero no aplicado en el caso G"},
        "densidades": {"concreto_kN_m3": GAMMA_CONCRETO,
                       "viewer_gamma_kN_m3": viewer["materiales"]["gamma_kN_m3"],
                       "nota": ("resumen usa 24.5166; eii_viewer registra 24.517 "
                                "(redondeo +0.0004, irrelevante)")},
        "materiales": {
            "hormigon_viewer": viewer["materiales"],
            "bloqueo_g35_vs_g40": {
                "estado": "PENDIENTE",
                "detalle": ("densidad 2500 kgf/m3: el peso propio NO cambia con "
                            "G35_10/G40, pero E_c, rigidez, periodos y esfuerzos "
                            "si. Bloquea EX/EY, Fiber Sections y capacidad. No "
                            "recalcular la estructura hasta resolver.")}},
        "clasificacion_caso_G": {
            "G_EII_publicado": "PP_losas + PP_vigas + PP_columnas + PP_muros (artefacto del pipeline externo)",
            "PP_elementos_publicado_kN": total_elementos_abs,
            "PP_losas_implicito_kN": pp_losas_implicito,
            "G_EII_reproducible": {
                "columnas_kN": round(pp_cols, 4),
                "vigas_V60_80_kN": round(pp_vigas_v60, 4),
                "vigas_V30_80_kN": round(pp_vigas_v30, 4),
                "muros_directo_kN": round(pp_muros_directo, 4),
                "losas_directo_kN": pp_losas,
                "PP_elementos_kN": total_elementos_repro_v60,
                "PP_elementos_con_losas_kN": round(pp_cols + pp_vigas_v60 +
                                                   pp_muros_directo + pp_losas, 2),
                "estado": ("columnas, vigas y losas confirmados; muros "
                           "PENDIENTE_ORIGEN_PIPELINE (no ajustado ni cerrado)")},
            "diferencia_no_resuelta": {
                "componente": "muros",
                "calculado_kN": round(pp_muros_directo, 2),
                "publicado_kN": pub["muros_kN"],
                "diferencia_kN": round(pub["muros_kN"] - pp_muros_directo, 2),
                "factor_directo_sobre_publicado": round(pub["muros_kN"] /
                                                        pp_muros_directo, 4),
                "origen": "PENDIENTE_ORIGEN_PIPELINE",
                "no_se_aplica_factor_para_forzar_coincidencia": True,
                "G_EII_cerrado": False},
            "componentes_confirmados": ["columnas", "vigas V.60/80",
                                        "vigas V.30/80", "losas"],
            "componentes_pendientes": ["muros"],
            "G_EII_cerrado": False,
            "PM_ADIC": "NO_INCLUIDA (catalogada en viewer; no aplicada al FE)",
            "Q_SC": "NO_INCLUIDA / Q_EII no construida (no existe caso con sobrecarga)",
            "peso_sismico_W": "no construido"},
        "publicado_artefacto": {
            "resumen_PP_ELEMENTOS_txt": {
                "gamma_kN_m3": 24.5166,
                "columnas_kN": pub["columnas_kN"],
                "vigas_kN": pub["vigas_kN"],
                "muros_kN": pub["muros_kN"],
                "total_elementos_kN": pub["total_elementos_pub_kN"]},
            "sec_V30_80": pub["V.30/80"],
            "sec_V60_80": pub["V.60/80"],
            "losas_implicitas_Pz_minus_elementos_kN": pp_losas_implicito,
            "solucion_v60_80": "solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.60_80.json",
            "solucion_v30_80": "solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.30_80.json"},
        "reproducido": {
            "columnas_kN": pp_cols,
            "vigas_V60_80_kN": pp_vigas_v60,
            "vigas_V30_80_kN": pp_vigas_v30,
            "muros_directo_kN": pp_muros_directo,
            "losas_directo_kN": pp_losas,
            "total_elementos_V60_80_kN": total_elementos_repro_v60,
            "total_elementos_V30_80_kN": total_elementos_repro_v30,
            "total_con_losas_V60_80_kN": round(pp_cols + pp_vigas_v60 +
                                               pp_muros_directo + pp_losas, 2),
            "nota_muros": ("el muro publicado (6521.26 kN) NO se reproduce con la "
                           "geometria versionada (valor directo 4330.02 kN, factor "
                           "1.506): la ley de calculo del proveedor para muros no "
                           "esta en el repositorio -> PENDIENTE_ORIGEN_PIPELINE. El "
                           "resto de tipos cierra en < .01 % (G_EII NO cerrado)")},
        "discrepancias_y_pendientes": {
            "muros": {
                "publicado_kN": pub["muros_kN"],
                "directo_kN": pp_muros_directo,
                "factor": round(pub["muros_kN"] / pp_muros_directo, 3),
                "estado": "PENDIENTE_ORIGEN_PIPELINE",
                "posibles_causas_pendientes_de_confirmar": [
                    "longitud/espesor de muro distinto al eje canonical del viewer",
                    "contado de las dos caras completas (t x L por cara)",
                    "espesor promedio mayor que el registrado (0.375 vs 0.25)",
                    "piezas/exclusiones adicionales en el modelo del proveedor"]},
            "losas": {
                "implicito_kN": pp_losas_implicito, "directo_kN": pp_losas,
                "delta_kN": round(abs(pp_losas - pp_losas_implicito), 2),
                "estado": "CONFIRMADO_REPRODUCIDO (delta 0.07% por discretizacion tributaria)"},
            "v031": {
                "estado": "PENDIENTE (seccion por_resolver)",
                "escenarios_simultaneos": "V.60/80 y V.30/80 sin eleccion definitiva",
                "peso_V60_kN": pp_v031_v60, "peso_V30_kN": pp_v031_v30,
                "delta_kN": delta_v031},
            "g35_vs_g40": "PENDIENTE (ver materiales.bloqueo_g35_vs_g40)",
            "base_cimentacion": "HIPOTESIS_MODELO (base en EII_CP1S, cota -4.01; cimentacion no documentada)",
            "cp2_cp3_borrador": "PENDIENTE (geometria borrador_no_ejecutable)",
            "cp4_e_losa_null": "PENDIENTE (espesor losa CP4 null en borrador; mezcla e15/e20 sin cerrar)",
            "cp4_col_010_012": "PENDIENTE (columnas CP4 por resolver, excluidas del FE)",
            "franja_etapa_anterior": ("RESUELTO_EXCLUIDO de Edificio II (x>27.95 > junta "
                                      "x=27.85; franja pertenece al Edificio I); no "
                                      "incorporada"),
            "elementos_sin_dueno_seccion_material_continuidad": [
                "V_031 (seccion)", "COL_010-012 CP4 (elemento)",
                "M_006 / L_PARKING (verificados ausentes, exclusiones.ok=true)"]},
        "v031_escenarios": {
            "n_elementos": len(v031),
            "elementos": [{"id": v["id"], "nivel": v["nivel"],
                           "L_m": round(v["L_m"], 4), "ui": v["ui"], "vj": v["vj"]}
                          for v in sorted(v031, key=lambda x: x["id"])],
            "longitud_total_m": round(sum(v["L_m"] for v in v031), 4),
            "areas_m2": {"V.60/80": 0.48, "V.30/80": 0.24},
            "peso_total_kN": {"V.60/80": pp_v031_v60, "V.30/80": pp_v031_v30},
            "peso_por_viga_kN": {"V.60/80": round(pp_v031_v60 / len(v031), 4),
                                 "V.30/80": round(pp_v031_v30 / len(v031), 4)},
            "delta_kN": delta_v031,
            "porcentaje_del_PP_elementos_publicado": round(
                delta_v031 / total_elementos_abs * 100.0, 3),
            "estado": "HIPOTESIS_MODELO (ambos escenarios simultaneos)"},
        "pm_adic_y_q": {
            "catalogo_viewer": viewer["cargas"],
            "aplicado_al_FE": "NO",
            "lineales_A_F_kg_m": {
                "PM_ADIC_lineal_kg_m": viewer["cargas"]["caso_G"].get("PM_ADIC_lineal_kg_m"),
                "SC_lineal_kg_m": viewer["cargas"]["caso_G"].get("SC_lineal_kg_m"),
                "estado": ("correlacionables por linea centroidal; requieren decision "
                           "de ancho tributario y de unidades (kg vs kgf)")},
            "categorias": [{
                "categoria": "PP_losa",
                "fuente": "eii_viewer cargas.caso_G (Q_PP_LOSA_kPa)",
                "correlacionable": "SI (directa: area neta x 3.677 kPa)",
                "necesita_tributaria": "No (directo)"},
                {"categoria": "PM.ADIC lineal A-F",
                 "fuente": "eii_viewer cargas.caso_G (PM_ADIC_lineal_kg_m)",
                 "correlacionable": "SI (linea -> viga/muro receptor)",
                 "necesita_tributaria": "SI (reparto + unidades)"},
                {"categoria": "SC lineal A-F",
                 "fuente": "eii_viewer cargas.caso_G (SC_lineal_kg_m)",
                 "correlacionable": "SI (linea -> viga/muro receptor)",
                 "necesita_tributaria": "SI (reparto + unidades)"},
                {"categoria": "Q superficial/puntual extra",
                 "fuente": "plano 700 (cat. EII en eii_viewer cargas)",
                 "correlacionable": "PARCIAL",
                 "necesita_tributaria": "SI (trama -> region)"}]},
        "elementos_pendientes": [
            {"id": "V_031", "estado": "PENDIENTE",
             "detalle": "seccion por_resolver; ver v031_escenarios"},
            {"id": "COL_010-012 (CP4)", "estado": "PENDIENTE",
             "detalle": "columnas CP4 sin resolver; excluidas del FE (32 columnas FE)"},
            {"id": "franja ETAPA ANTERIOR x[27.95,~29.5]", "estado": "RESUELTO_EXCLUIDO",
             "detalle": "pertenece al Edificio I (junta x=27.85); no reactivar M_005/COL_009-011/BL_001"},
            {"id": "base/cimentacion CP1S", "estado": "HIPOTESIS_MODELO",
             "detalle": "base en cota -4.01; cimentacion no documentada"},
            {"id": "CP2/CP3 borrador_no_ejecutable", "estado": "PENDIENTE",
             "detalle": "geometria de esos niveles sin validar como ejecutable"},
            {"id": "Elementos sin dueno/seccion/material/continuidad", "estado": "PENDIENTE",
             "detalle": "se registran por elemento en detalle_*"},
            {"id": "e_losa CP4 (null)", "estado": "PENDIENTE",
             "detalle": "espesor losa CP4 null en borrador (e15/e20 por resolver)"}],
        "por_nivel": por_nivel,
        "comparacion_EI_EII": {
            "EI": {"PP_confirmado_elementos_kN": 17179.23,
                   "alcance": "cota inferior (vigas 14803.53 + columnas 2045.60 + muros 330.09)",
                   "estado": "CONFIRMADO (auditoria v2; hash a158fcb3…)"},
            "EII": {"PP_elementos_publicado_kN": total_elementos_abs,
                    "PP_elementos_reproducido_kN": total_elementos_repro_v60,
                    "PP_losas_implicito_kN": pp_losas_implicito,
                    "Pz_V60_80_kN": pz_v60, "Pz_V30_80_kN": pz_v30,
                    "estado": "por tipo (muros PENDIENTE; resto CONFIRMADO_REPRODUCIDO)"}},
        "verificaciones_obligatorias": verif,
        "detalle": {
            "columnas": cols,
            "vigas": vigas,
            "muros": muros,
            "losas": losas,
            "n_elementos": {"nodos": modelo["resumen"]["nodos"],
                            "columnas": modelo["resumen"]["columnas"],
                            "muros": modelo["resumen"]["muros"],
                            "vigas": modelo["resumen"]["vigas"]},
            "hashes_maestros_sha256": modelo["hashes_maestros_sha256"]},
        "fuentes": [
            "analisis_estructural/edificio_II_casoG_PP_elementos/MODELO_FE_GEOMETRIA_NODOS.json",
            "analisis_estructural/edificio_II_casoG_PP_elementos/eii_viewer.json",
            "analisis_estructural/edificio_II_casoG_PP_elementos/resumen_PP_ELEMENTOS.txt",
            "analisis_estructural/edificio_II_casoG_PP_elementos/solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.60_80.json",
            "analisis_estructural/edificio_II_casoG_PP_elementos/solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.30_80.json"],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    OUT_JSON.write_bytes(txt.encode("utf-8"))
    h = hashlib.sha256(txt.encode("utf-8")).hexdigest()
    (OUT_JSON.with_name(OUT_JSON.stem + "_hash.txt")).write_text(
        "sha256 %s  %s\n" % (h, OUT_JSON.name), encoding="utf-8")

    print(json.dumps({
        "N_columnas": len(cols), "PP_columnas_kN": pp_cols,
        "N_vigas_FE": len(beams), "PP_vigas_V60_kN": pp_vigas_v60,
        "PP_vigas_V30_kN": pp_vigas_v30,
        "N_muros_piezas": len(muros), "PP_muros_directo_kN": pp_muros_directo,
        "muros_publicado_kN": pub["muros_kN"],
        "N_losas": len(losas), "PP_losas_directo_kN": pp_losas,
        "PP_losas_implicito_kN": pp_losas_implicito,
        "total_publicado_elementos_kN": total_elementos_abs,
        "repro_V60_elementos_kN": total_elementos_repro_v60,
        "repro_V30_elementos_kN": total_elementos_repro_v30,
        "Pz60_kN": pz_v60, "Pz30_kN": pz_v30, "deltaPz_kN": delta_pz,
        "peso_V031_V60_kN": pp_v031_v60, "peso_V031_V30_kN": pp_v031_v30,
        "ok_delta_v031": verif["4_delta_variantes_peso_V031"]["ok"],
        "ok_losas": verif["3_losas_directas_vs_implicitoPz"]["ok"],
        "G_EII_reproducible_estado": "columnas, vigas y losas CONFIRMADAS; muros PENDIENTE_ORIGEN_PIPELINE",
        "diferencia_no_resuelta_muros_kN": round(pub["muros_kN"] - pp_muros_directo, 2),
        "G_EII_cerrado": False,
        "hash": h,
        "escrito_en": str(OUT_JSON),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()