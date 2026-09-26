"""Carga viva Q (sobrecarga de uso) por edificio, manteniendo resultados separados.

Flujo:
  1. Lee `config/cargas.json`: q_Q por edificio (null si no documentado), tolerancia,
     modo DEMOSTRACION_ARBITRARIA y paths de la geometria tributaria.
  2. Reutiliza la geometria tributaria de Semana 2 (src/comun/geometria_tributaria.py).
  3. Aplica  Q_transferida = q_Q * area_tributaria  por receptor (= elemento receptor).
  4. Verifica por nivel y global:
       sum(Q_transferida) == q_Q * A   (dif absoluta y relativa <= tolerancia -> OK/ERROR).
  5. Distingue SIEMPRE el catalogo de sobrecargas documentado (no aplicado) de la carga
     efectivamente aplicada. Se evita dar doble aplicacion (aplicada_al_modelo_FE=false).

Normas de honestidad:
  - q_Q_kN_m2 = null -> NO se inventa ningun valor; solo se permite el modo
    DEMOSTRACION_ARBITRARIA con el flag marcado en config.
  - la unidad kgf->kN usa 0.00980665 (regla catalogada).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from src.comun.geometria_tributaria import cargar_geometria_tributaria

REPO = Path(__file__).resolve().parents[3]
CONFIG = REPO / "entrega_03_cargas_sismo_capacidad" / "config" / "cargas.json"
KGF_A_KN = 0.00980665


def leer_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def leer_catalogo_sobrecarga(edificio: str) -> dict:
    """Catalogo documentado (fuentes versionadas), NO aplicado. Se separa del aplicado."""
    if edificio == "I":
        p = REPO / "entrega_03_cargas_sismo_capacidad" / "data" / "externas" \
            / "catalogo_cargas_diseno_edificio_I.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        cat = {"fuente": str(p), "unidad": "kgf/m2 (1 kgf/m2 = 0.00980665 kN/m2)",
               "SC_por_nivel_kgf_m2": {}, "PM_ADIC_referencia": {}}
        for nivel, blk in d["catalogo_por_nivel"].items():
            sc = [cu["SC_kgf_m2"] for cu in blk.get("cuadros_superficiales", [])]
            pa = [cu["PM_ADIC_kgf_m2"] for cu in blk.get("cuadros_superficiales", [])]
            cat["SC_por_nivel_kgf_m2"][nivel] = sc
            cat["PM_ADIC_referencia"][nivel] = pa
        cat["pendiente"] = ("trama_id 'por_definir_trama_*' sin mapeo a regiones geometricas "
                            "(no se aplica Q por zona todavia)")
        return cat
    if edificio == "II":
        p = REPO / "analisis_estructural" / "edificio_II_casoG_PP_elementos" / "eii_viewer.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        cg = d["cargas"]["caso_G"]
        return {"fuente": str(p),
                "unidad": "kgf/m lineal (1 kgf/m = 0.00980665 kN/m) y kPa (PP losa)",
                "SC_lineal_kg_m": cg["SC_lineal_kg_m"],
                "Q_PP_LOSA_kPa": cg["Q_PP_LOSA_kPa"],
                "Q_PP_LOSA_020_kPa": cg["Q_PP_LOSA_020_kPa"],
                "pendiente": ("no hay sobrecarga uniforme (kPa) documentada para EII; "
                              "solo SC lineal por zona A-F")}
    raise ValueError(f"edificio desconocido: {edificio}")


def _q_efectivo(edificio: str, cfg: dict, usar_demo: bool) -> tuple[float, dict]:
    q = cfg["q_Q"][edificio]["q_Q_kN_m2"]
    estado = cfg["q_Q"][edificio]["estado"]
    if q is not None:
        return float(q), {"q_Q_kN_m2": q, "estado": estado, "demostracion": False}
    if not usar_demo:
        raise SystemExit(
            "ABORTE: q_Q del edificio %s es null (no esta documentado). "
            "No se inventa un valor. Ejecute con --demo para usar el valor "
            "DEMOSTRACION_ARBITRARIA de config/cargas.json." % edificio)
    demo = cfg["DEMOSTRACION_ARBITRARIA"]
    return float(demo["q_Q_kN_m2"]), {
        "q_Q_kN_m2": demo["q_Q_kN_m2"],
        "estado": "DEMOSTRACION_ARBITRARIA",
        "demostracion": bool(demo["marcado"]),
        "nota": demo["nota"]}


def aplicar_Q(edificio: str, geom: dict, cfg: dict, usar_demo: bool,
              tolerancia_rel: float | None = None) -> dict:
    q, info_q = _q_efectivo(edificio, cfg, usar_demo)
    tol = cfg["tolerancia_rel_sum_Q"] if tolerancia_rel is None else tolerancia_rel

    por_nivel = {}
    global_trans = 0.0
    global_teor = 0.0
    global_ok = True
    for nivel, blk in geom["por_nivel"].items():
        area = blk["area_total_m2"]
        teor = q * area
        trans = sum(r["area_tributaria_m2"] for r in blk.get("receptores", [])) * q
        dif = abs(trans - teor)
        drel = (dif / teor) if teor != 0.0 else 0.0
        ok = drel <= tol
        global_trans += trans
        global_teor += teor
        global_ok = global_ok and ok
        por_nivel[nivel] = {
            "area_tributaria_m2": round(area, 4),
            "q_Q_kN_m2": q,
            "carga_teorica_q_A_kN": round(teor, 4),
            "carga_transferida_sum_kN": round(trans, 4),
            "diferencia_abs_kN": round(dif, 6),
            "diferencia_rel": round(drel, 8),
            "tolerancia_rel": tol,
            "estado": ("OK" if ok else "ERROR"),
            "estado_geometria": blk.get(
                "estado", "CONFIRMADO" if area > 0 else "SIN_GEOMETRIA"),
            "n_receptores": blk.get("n_receptores", 0),
            "metodo_transferencia": geom["metodo"],
        }

    dg = abs(global_trans - global_teor)
    dgr = (dg / global_teor) if global_teor != 0.0 else 0.0
    report = {
        "edificio": edificio,
        "q_Q": info_q,
        "catalogo_sobrecarga_documentada": leer_catalogo_sobrecarga(edificio),
        "aplicada_al_modelo_FE": cfg["aplicada_al_modelo_FE"],
        "nota_aplicacion": ("Q aplicada solo sobre geometria tributaria de Semana 2; "
                            "AI catalogada no se mezcla con aplicada"),
        "por_nivel": por_nivel,
        "niveles_pendientes_geometria": [
            n for n, v in por_nivel.items() if v["estado_geometria"] != "CONFIRMADO"],
        "global": {
            "area_total_m2": round(global_teor / q if q else 0.0, 4),
            "carga_teorica_q_A_kN": round(global_teor, 4),
            "carga_transferida_sum_kN": round(global_trans, 4),
            "diferencia_abs_kN": round(dg, 6),
            "diferencia_rel": round(dgr, 8),
            "tolerancia_rel": tol,
            "estado": "OK" if global_ok and dgr <= tol else "ERROR"},
    }
    return report


def reparar_por_receptor(edificio: str, geom: dict, cfg: dict,
                         usar_demo: bool) -> list[dict]:
    q, _ = _q_efectivo(edificio, cfg, usar_demo)
    filas = []
    for nivel, blk in geom["por_nivel"].items():
        for r in blk.get("receptores", []):
            filas.append({
                "edificio": edificio, "nivel": nivel, "receptor": r["id"],
                "area_tributaria_m2": round(r["area_tributaria_m2"], 6),
                "q_Q_kN_m2": q, "Q_kN": round(q * r["area_tributaria_m2"], 6)})
    return filas


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    usar_demo = "--demo" in args
    edificios = ["I", "II"]
    cfg = leer_config()
    resumen = {"configuracion": str(CONFIG), "demo": usar_demo, "edificios": {}}
    for ed in edificios:
        geom = cargar_geometria_tributaria(
            ed, cfg["geometria_tributaria"][ed])
        report = aplicar_Q(ed, geom, cfg, usar_demo=usar_demo)
        resumen["edificios"][ed] = report
        _escribir(ed, report, geom, cfg, usar_demo)
        _imprimir(ed, report, geom)
    out = REPO / "entrega_03_cargas_sismo_capacidad" / "results" / "cargas" \
        / "carga_viva_Q_resumen.json"
    out.write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print("escrito:", out)
    return 0 if all(
        r["global"]["estado"] == "OK" for r in resumen["edificios"].values()) else 1


def _escribir(ed: str, report: dict, geom: dict, cfg: dict, demo: bool) -> None:
    base = REPO / "entrega_03_cargas_sismo_capacidad" / "results" / "cargas"
    base.mkdir(parents=True, exist_ok=True)
    jp = base / f"carga_viva_Q_{ed}.json"
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")
    filas = reparar_por_receptor(ed, geom, cfg, demo)
    cp = base / f"carga_viva_Q_{ed}_por_receptor.csv"
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["edificio", "nivel", "receptor",
                                          "area_tributaria_m2", "q_Q_kN_m2", "Q_kN"])
        w.writeheader()
        w.writerows(filas)
    print("escrito:", jp, "|", cp)


def _imprimir(ed: str, report: dict, geom: dict) -> None:
    g = report["global"]
    print("=" * 72)
    print(f"[Edificio {ed}] Q  q_Q={report['q_Q']['q_Q_kN_m2']} kN/m2 "
          f"({report['q_Q']['estado']})")
    print(f"  A_total = {g['area_total_m2']} m2 | teorica = {g['carga_teorica_q_A_kN']} "
          f"| transferida = {g['carga_transferida_sum_kN']} kN "
          f"| dif_abs = {g['diferencia_abs_kN']} | dif_rel = {g['diferencia_rel']} "
          f"| tol = {g['tolerancia_rel']} | {g['estado']}")
    print("  aplicada_al_modelo_FE =", report["aplicada_al_modelo_FE"])
    print("  niveles:", ", ".join(f"{k}({v['estado']})"
                                  for k, v in report["por_nivel"].items()))


if __name__ == "__main__":
    raise SystemExit(main())