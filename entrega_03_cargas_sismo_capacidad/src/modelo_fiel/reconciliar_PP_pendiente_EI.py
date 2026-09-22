"""reconciliar_PP_pendiente_EI — auditoria ID por ID del PP no cuantificado del EI.

Iteracion MODELO_FIEL_4 (tarea 2). Parte del inventario ya cerrado en v3
(modelo_fiel/inventario_PP_pendiente_EI.*) y reabre la fuente determinista
results/peso_propio_teorico_EDIFICIO_I_v2.json (con su seed de hash) para:

  * Clasificar los 63 pendientes + 1 no-incluida + hipotesis informativas en
    6 categorias objetivas:
      C1_real_FE_seccion_pendiente        : elemento real con unidad FE pero
                                            seccion/material pendiente
      C2_seccion_confirmada_tramo_pendiente : P. 70x70 hormigon P4 (P3->P4)
      C3_hipotesis_base_nivel             : hipotesis FE base->nivel + contencion
                                            (informativo; NO aplica)
      C4_metalico_tubular_confirmado      : P.M./V.M. 300x300, seccion tubular
                                            confirmada, tramo real pendiente
      C5_muro_una_sola_planta             : muros con una sola planta documentada
      C6_no_incluida                      : excluida por falta de evidencia
  * Tabla ID por ID (json/md/csv) con simbolo, nivel, seccion, pp/m, L y estado.
  * Verificaciones:
      - conteos 63/1 y 68 filas;
      - ningun id confirmado->pendiente repetido (sin doble conteo);
      - las P. 70x70 pendientes de P4 son continuacion (u, v-0.181) de una
        columna de hormigon confirmada en P1..P3;
      - conciliacion numerica vs 17 179,23 kN (cota inferior confirmada) y
        rango superior informativo 8 453,55 kN;
      - determinismo (hash del v2 verificado).
  * No convierte ninguna hipotesis en carga aplicada.

Escribe en modelo_fiel/:
  reconciliacion_PP_pendiente_EI.json / .md / .csv

Uso:
  python -X utf8 -m src.modelo_fiel.reconciliar_PP_pendiente_EI
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
V2 = E3 / "results" / "peso_propio_teorico_EDIFICIO_I_v2.json"
V2_HASH = E3 / "results" / "peso_propio_teorico_EDIFICIO_I_v2_hash.txt"
INV = OUT / "inventario_PP_pendiente_EI.json"

CATEGORIAS = [
    ("C1_real_FE_seccion_pendiente",
     "elemento real con unidad FE pero seccion/material pendiente"),
    ("C2_seccion_confirmada_tramo_pendiente",
     "seccion confirmada pero tramo continuado pendiente"),
    ("C3_hipotesis_base_nivel",
     "hipotesis FE base->nivel / contencion (informativo, no aplica)"),
    ("C4_metalico_tubular_confirmado",
     "metalico tubular con seccion confirmada (tramo real pendiente)"),
    ("C5_muro_una_sola_planta",
     "muro con una sola planta documentada"),
    ("C6_no_incluida",
     "no incluida por falta de evidencia"),
]

PP_CONFIRMADO = 17179.2261
HIPOTESIS_TOTAL = 8453.5488


def _norm(seccion: str) -> str:
    return seccion.replace(" ", "")


def _es_p70(fila_seccion: str) -> bool:
    return "P.70x70" in _norm(fila_seccion)


def _categoria(pend: dict) -> str:
    seccion = pend.get("seccion", "")
    if pend["estado"] == "PENDIENTE_SECCION":
        return "C1_real_FE_seccion_pendiente"
    if pend["estado"] != "PENDIENTE_TRAMO":
        return "C6_no_incluida"
    if _es_p70(seccion):
        return "C2_seccion_confirmada_tramo_pendiente"
    if "300x300" in _norm(seccion):
        return "C4_metalico_tubular_confirmado"
    if "muro" in (pend.get("tipo") or ""):
        return "C5_muro_una_sola_planta"
    return "C1_real_FE_seccion_pendiente"


def _col_p70_continuacion(pend, columnas_confirmadas) -> bool:
    u = pend["p_inicio"][0]
    v = pend["p_inicio"][1]
    for c in columnas_confirmadas:
        if not _es_p70(c["seccion"]):
            continue
        if abs(c["u"] - u) < 0.05 and abs((c["v"] + 0.181) - v) < 0.05:
            return True
    return False


def _pp_m_por_seccion(seccion: str):
    """pp por metro por familia conocida (kN/m)."""
    mapa = {"P.M.300x300x20": 1.7244,
            "V.M.300x300x5": 0.4542,
            "P.70x70": 12.0131}
    return mapa.get(_norm(seccion))


def _construir(d: dict) -> tuple[list[dict], list[dict], dict]:
    rows: list[dict] = []
    cheques: dict = {}

    columnas_confirmadas = d["detalle"]["columnas_confirmadas"]
    ids_conf_col = {c["id"] for c in columnas_confirmadas}
    ids_conf_viga = {v["id"] for v in d["detalle"]["vigas_confirmadas"]}
    ids_conf_muro = {v for m in d["detalle"]["muros_confirmados"]
                     for k, v in m["id_candidato"].items()}

    for pend in d["pendientes"]["columnas"]:
        cat = _categoria(pend)
        cont = (_col_p70_continuacion(pend, columnas_confirmadas)
                if cat == "C2_seccion_confirmada_tramo_pendiente" else None)
        pp_m = _pp_m_por_seccion(pend["seccion"])
        rows.append({
            "categoria": cat, "simbolo": pend["seccion"], "id": pend["id"],
            "nivel": pend["nivel"], "tipo": pend["tipo"],
            "pp_m_unit_kN_m": pp_m, "L_m": None, "pp_kN": pend.get("pp_kN"),
            "continuacion_tramo_confirmado": cont,
            "estado": pend["estado"], "motivo": pend.get("motivo", "")[:120],
        })
    for pend in d["pendientes"]["vigas"]:
        rows.append({
            "categoria": _categoria(pend), "simbolo": pend["seccion"],
            "id": pend["id"], "nivel": pend["nivel"], "tipo": "viga",
            "pp_m_unit_kN_m": _pp_m_por_seccion(pend["seccion"]),
            "L_m": pend.get("L_m"),
            "pp_kN": pend.get("pp_kN"), "continuacion_tramo_confirmado": None,
            "estado": pend["estado"], "motivo": pend.get("motivo", "")[:120],
        })
    for pend in d["pendientes"]["muros"]:
        simbolo = f"e={pend.get('e_m')} m" if pend.get("e_m") else "sin seccion/espesor/cotas"
        rows.append({
            "categoria": _categoria(pend), "simbolo": simbolo,
            "id": pend["id_candidato"], "nivel": pend.get("nivel"),
            "tipo": pend["tipo"],
            "pp_m_unit_kN_m": None, "L_m": pend.get("L_m"),
            "pp_kN": pend.get("pp_kN"), "continuacion_tramo_confirmado": None,
            "estado": pend["estado"], "motivo": pend.get("motivo", "")[:120],
        })
    for no in d["no_incluidas"].get("vigas", []):
        rows.append({
            "categoria": "C6_no_incluida", "simbolo": no["seccion"],
            "id": no["id"], "nivel": no["nivel"], "tipo": "no viga (muro M.H.A. e=30)",
            "pp_m_unit_kN_m": None, "L_m": no.get("L_m"),
            "pp_kN": no.get("pp_kN"), "continuacion_tramo_confirmado": None,
            "estado": no["estado"], "motivo": no.get("motivo", "")[:120],
        })

    hip = d["hipotesis_tramos_base_kN"]
    rows.append({
        "categoria": "C3_hipotesis_base_nivel", "simbolo": "segun FE",
        "id": "HIPOTESIS_columnas_base_nivel",
        "nivel": "BASE->nivel", "tipo": "hipotesis FE base->nivel (columnas)",
        "pp_m_unit_kN_m": None, "L_m": None,
        "pp_kN": round(hip["columnas"], 4),
        "continuacion_tramo_confirmado": None,
        "estado": "PENDIENTE_HIPOTESIS_FE",
        "motivo": hip["nota"],
    })
    rows.append({
        "categoria": "C3_hipotesis_base_nivel", "simbolo": "segun FE",
        "id": "HIPOTESIS_muros_base_nivel",
        "nivel": "BASE->nivel", "tipo": "hipotesis FE base->nivel (muros)",
        "pp_m_unit_kN_m": None, "L_m": None,
        "pp_kN": round(hip["muros"], 4),
        "continuacion_tramo_confirmado": None,
        "estado": "PENDIENTE_HIPOTESIS_FE",
        "motivo": hip["nota"],
    })
    for clave, blk in d["muros_contencion_sotano"].items():
        rows.append({
            "categoria": "C3_hipotesis_base_nivel",
            "simbolo": f"e={blk.get('e_m')} m, panel={blk.get('panel_m')} m",
            "id": clave, "nivel": "CP1S", "tipo": "muro de contencion del sotano",
            "pp_m_unit_kN_m": None, "L_m": blk.get("panel_m"),
            "pp_kN": round(blk["pp_kN"], 4),
            "continuacion_tramo_confirmado": None,
            "estado": blk["estado"], "motivo": blk["nota"],
        })

    ids_pend_col = {r["id"] for r in rows if r["categoria"].startswith(("C1", "C2", "C4"))}
    ids_pend_viga = {r["id"] for r in rows if r["categoria"] == "C1_real_FE_seccion_pendiente"
                     and r["tipo"] == "viga"}
    ids_pend_muro = {r["id"] for r in rows if r["categoria"] == "C5_muro_una_sola_planta"}

    pend_por_cat = {}
    for cat, _ in CATEGORIAS:
        pend_por_cat[cat] = (sum(1 for r in rows if r["categoria"] == cat),
                             sum((r["pp_kN"] or 0.0) for r in rows
                                 if r["categoria"] == cat))

    n_p70 = sum(1 for r in rows
                if r["categoria"] == "C2_seccion_confirmada_tramo_pendiente")
    n_p70_continuas = sum(1 for r in rows
                          if r["categoria"] == "C2_seccion_confirmada_tramo_pendiente"
                          and r["continuacion_tramo_confirmado"])

    hash_ok = True
    try:
        v2_actual = hashlib.sha256(V2.read_bytes()).hexdigest().upper()
        v2_ref = V2_HASH.read_text(encoding="utf-8").split()[1].upper()
        hash_ok = v2_actual == v2_ref
    except FileNotFoundError:
        hash_ok = False

    cheques = {
        "1_conteo_pendientes_63": {
            "ok": len(d["pendientes"]["columnas"]) + len(d["pendientes"]["vigas"])
                  + len(d["pendientes"]["muros"]) == 63,
            "detalle": f"columnas {len(d['pendientes']['columnas'])} + "
                       f"vigas {len(d['pendientes']['vigas'])} + "
                       f"muros {len(d['pendientes']['muros'])}",
        },
        "2_conteo_no_incluidas_1": {
            "ok": len(d["no_incluidas"].get("vigas", [])) == 1,
            "detalle": str(len(d["no_incluidas"].get("vigas", []))),
        },
        "3_total_filas_68": {
            "ok": len(rows) == 68,
            "detalle": f"{len(rows)} filas (63 pendientes + 1 no incl + 2 hipotesis + 2 contencion)",
        },
        "4_sin_id_repetido_confirmado_pendiente": {
            "ok": not (ids_conf_col & ids_pend_col)
                  and not (ids_conf_viga & ids_pend_viga)
                  and not (ids_conf_muro & ids_pend_muro),
            "detalle": {"conf_col": sorted(ids_conf_col & ids_pend_col),
                        "conf_viga": sorted(ids_conf_viga & ids_pend_viga),
                        "conf_muro": sorted(ids_conf_muro & ids_pend_muro)},
        },
        "5_P70_P4_continuacion_de_hormigon_confirmado": {
            "ok": n_p70 == 18 and n_p70_continuas == 18,
            "detalle": f"{n_p70_continuas}/{n_p70} continuaciones en P1..P3 confirmadas",
        },
        "6_P70_no_tiene_doble_conteo_interno": {
            "ok": len(ids_pend_col & {r["id"] for r in rows
                                      if r["categoria"] == "C2_seccion_confirmada_tramo_pendiente"})
                  == len([r for r in rows
                          if r["categoria"] == "C2_seccion_confirmada_tramo_pendiente"]),
            "detalle": "cada P. 70x70 pendiente P4 tiene un unico id",
        },
        "7_conciliacion_numerica": {
            "ok": abs(d["PP_confirmado"]["total_kN"] - PP_CONFIRMADO) < 1e-6,
            "detalle": {"PP_confirmado": round(d["PP_confirmado"]["total_kN"], 4),
                        "vigas": round(d["PP_confirmado"]["vigas_kN"], 4),
                        "columnas": round(d["PP_confirmado"]["columnas_kN"], 4),
                        "muros": round(d["PP_confirmado"]["muros_kN"], 4)},
        },
        "8_hipotesis_solo_informativo_no_aplica": {
            "ok": abs(hip["columnas"] + hip["muros"]
                      + sum(m["pp_kN"] for m in d["muros_contencion_sotano"].values())
                      - HIPOTESIS_TOTAL) < 1e-6,
            "detalle": {"columnas": round(hip["columnas"], 4),
                        "muros": round(hip["muros"], 4),
                        "contencion": round(sum(m["pp_kN"]
                                                for m in d["muros_contencion_sotano"].values()), 4),
                        "total_rango": round(HIPOTESIS_TOTAL, 4)},
        },
        "9_determinismo_hash_v2": {
            "ok": hash_ok,
            "detalle": f"sha256 v2 {'coincide con el seed' if hash_ok else 'NO verificado'}",
        },
    }

    total_ok = all(c["ok"] for c in cheques.values())
    resumen_cat = []
    for cat, nombre in CATEGORIAS:
        conteo, pp = pend_por_cat[cat]
        resumen_cat.append({"categoria": cat, "nombre": nombre, "conteo": conteo,
                            "pp_cuantificado_kN": round(pp, 4)})

    return rows, resumen_cat, {
        "iteracion": "MODELO_FIEL_4",
        "tarea": "2_reconciliacion_PP_pendiente_EI",
        "fuente": str(V2),
        "referencia_v3": str(INV),
        "margen": {
            "PP_confirmado_kN": round(d["PP_confirmado"]["total_kN"], 4),
            "PP_confirmado_redondeado_kN": round(d["PP_confirmado"]["total_kN"], 2),
            "pendientes_cuantificados_kN": 0.0,
            "hipotesis_rango_superiorinformativo_kN": round(HIPOTESIS_TOTAL, 4),
            "PP_rango_inferior_real_posible_kN": round(d["PP_confirmado"]["total_kN"], 4),
            "PP_rango_superior_posible_kN": round(d["PP_confirmado"]["total_kN"] + HIPOTESIS_TOTAL, 4),
            "nota": ("17 179,23 kN = COTA INFERIOR confirmada; las hipotesis base->nivel"
                     " suman adicional 8 453,55 kN SOLO si se confirmaran tramos reales y"
                     " cimentacion; no convertidas en carga aplicada"),
        },
        "por_categoria": resumen_cat,
        "aplicado_al_FE_kN": 0.0,
        "chequeos": cheques,
        "total_chequeos_ok": total_ok,
        "estado": "OK" if total_ok else "NO_OK",
    }


def _escribir(rows: list[dict], resumen_cat: list[dict], salida: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reconciliacion_PP_pendiente_EI.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# Reconciliacion PP pendiente del Edificio I (MODELO_FIEL_4)",
          "",
          salida["margen"]["nota"],
          "",
          "## Resumen por categoria", "",
          "| Categoria | Conteo | PP cuantificado (kN) |",
          "|---|---|---|"]
    for c in resumen_cat:
        md.append(f"| {c['nombre']} | {c['conteo']} | {c['pp_cuantificado_kN']} |")
    md += ["", "## Conciliacion numerica", "",
           "| Concepto | kN |", "|---|---|",
           f"| PP confirmado (viga+columna+muro) | {salida['margen']['PP_confirmado_kN']} |",
           f"| Pendientes cuantificados | {salida['margen']['pendientes_cuantificados_kN']} |",
           f"| Hipotesis base->nivel (informativo) | {salida['margen']['hipotesis_rango_superiorinformativo_kN']} |",
           f"| Rango real posible | {salida['margen']['PP_rango_inferior_real_posible_kN']} .. {salida['margen']['PP_rango_superior_posible_kN']} |",
           "", "## Chequeos", ""]
    for k, c in salida["chequeos"].items():
        md.append(f"- {k}: **{'OK' if c['ok'] else 'NO OK'}** (`{c['detalle']}`)")
    md += ["", "## Tabla ID por ID (68 filas)", "",
           "| # | Categoria | Simbolo / seccion | ID | Nivel | Tipo | pp/m (kN/m) | L (m) | pp (kN) | Continuacion | Estado |",
           "|---|-----------|------|-----|-------|------|-------------|-------|---------|--------------|--------|"]
    for i, r in enumerate(rows, 1):
        cont = "-" if r["continuacion_tramo_confirmado"] is None else (
            "SI" if r["continuacion_tramo_confirmado"] else "NO")
        md.append(f"| {i} | {r['categoria']} | {r['simbolo']} | {r['id']} | "
                  f"{r['nivel']} | {r['tipo']} | {r['pp_m_unit_kN_m']} | {r['L_m']} | "
                  f"{r['pp_kN']} | {cont} | {r['estado']} |")
    (OUT / "reconciliacion_PP_pendiente_EI.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")

    with open(OUT / "reconciliacion_PP_pendiente_EI.csv", "w", newline="",
              encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["#", "categoria", "simbolo_seccion", "id", "nivel", "tipo",
                    "pp_m_unit_kN_m", "L_m", "pp_kN", "continuacion", "estado",
                    "motivo"])
        for i, r in enumerate(rows, 1):
            cont = "" if r["continuacion_tramo_confirmado"] is None else (
                "SI" if r["continuacion_tramo_confirmado"] else "NO")
            w.writerow([i, r["categoria"], r["simbolo"], r["id"], r["nivel"],
                        r["tipo"], r["pp_m_unit_kN_m"], r["L_m"], r["pp_kN"],
                        cont, r["estado"], r["motivo"]])


def main() -> None:
    d = json.loads(V2.read_text(encoding="utf-8"))
    rows, resumen_cat, salida = _construir(d)
    _escribir(rows, resumen_cat, salida)
    print(json.dumps({"checks_ok": sum(c["ok"] for c in salida["chequeos"].values()),
                      "checks_total": len(salida["chequeos"]),
                      "pendientes": sum(1 for r in rows
                                        if r["estado"] == "PENDIENTE_TRAMO"
                                        or r["estado"] == "PENDIENTE_SECCION"),
                      "pp_confirmado": salida["margen"]["PP_confirmado_kN"],
                      "estado": salida["estado"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()