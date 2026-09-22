"""Reproduccion FE del caso G (peso propio) del Edificio II.

Corre el pipeline reproducible (`pipeline_FE_EII.MarcoEII`) construyendo el
mismo modelo losa->receptor->nodos que el publicado y resuelve con OpenSeesPy.
Compara contra el artefacto publicado `solucion_FE_EII_completo_*.json`
(solo lectura) manteniendo separadas: solucion reproducible, solucion
publicada, diferencia de muros (2.191,24 kN, PENDIENTE_ORIGEN_PIPELINE),
componentes confirmados y pendientes.

Uso:
  python -X utf8 -m src.cargas.caso_G_EII [--seccion V.60/80|V.30/80]

Salidas (entrega_03.../results/cargas/):
  caso_G_EII_reproducible.json   contrato completo del modelo reproducible
  caso_G_EII_reproducible_reacciones.csv
  caso_G_EII_comparacion.json    reproducible vs publicado
  caso_G_EII_comparacion.md      resumen legible
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
RES_DIR = E3 / "results" / "cargas"
ARTIFACT_DIR = REPO / "analisis_estructural" / "edificio_II_casoG_PP_elementos"

from .pipeline_FE_EII import (  # noqa: E402
    GAMMA_CONCRETO_KN_M3,
    MarcoEII,
    V031_SECCIONES,
)


def cargar_publicado(v031_seccion: str):
    """Artefacto publicado (solo lectura) del FE EII para el escenario elegido."""
    suf = "V.60_80" if v031_seccion == "V.60/80" else "V.30_80"
    p = ARTIFACT_DIR / ("solucion_FE_EII_completo_casoG_PP_ELEMENTOS_%s.json" % suf)
    if not p.exists():
        return None, str(p)
    return json.loads(p.read_text(encoding="utf-8")), str(p)


def max_desp_z(desplazamientos):
    return max((abs(v[2]) for v in desplazamientos.values()), default=0.0)


def _L(rec):
    return math.hypot(rec["u_j"] - rec["u_i"], rec["v_j"] - rec["v_i"],
                      rec["z_j"] - rec["z_i"])


def _componentes(marco):
    def suma(it):
        tot = 0.0
        for rec in it:
            tot += rec["sec_valores"]["A"] * _L(rec) * GAMMA_CONCRETO_KN_M3
        return round(tot, 4)

    def area_neto(lo):
        def shoelace(poly):
            a = 0.0
            n = len(poly)
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % n]
                a += x1 * y2 - x2 * y1
            return abs(a) / 2.0
        neto = shoelace(lo["poligono_exterior"])
        for ab in lo.get("aberturas_poligonos", []):
            neto -= shoelace(ab)
        return neto

    losas_directo = round(sum(area_neto(lo) * lo["espesor"] * GAMMA_CONCRETO_KN_M3
                              for lv in marco.viewer["niveles"] for lo in lv["losas"]), 4)
    return {"columnas_kN": suma(marco.columnas),
            "vigas_kN": suma(marco.vigas_elem),
            "muros_directo_kN": suma(marco.muros_elem),
            "losas_directo_kN": losas_directo}


def _el(r):
    return {"id": r["elemento_id"], "tipo": r["tipo"], "seccion": r["seccion"],
            "nivel": r["nivel"], "nodo_i": r["nodo_i"], "nodo_j": r["nodo_j"],
            "tag": r["tag"],
            "seccion_valores": {k: (round(v, 6) if isinstance(v, float) else v)
                                for k, v in r["sec_valores"].items()}}


def _verificaciones(marco, sol, cargas, Rz, Pz, repartos):
    comp = _componentes(marco)
    total_elem = comp["columnas_kN"] + comp["vigas_kN"] + comp["muros_directo_kN"]
    total_con_losas = total_elem + comp["losas_directo_kN"]
    eq_ok = abs(Rz - Pz) <= 1e-6
    return {
        "suma_componentes_pp": {
            "columnas_kN": comp["columnas_kN"],
            "vigas_V60_80_kN": comp["vigas_kN"],
            "muros_directo_kN": comp["muros_directo_kN"],
            "losas_directo_kN": comp["losas_directo_kN"],
            "total_elementos_kN": round(total_elem, 4),
            "total_con_losas_kN": round(total_con_losas, 4)},
        "identidad_cargas_vs_geometria": {
            "P_z_aplicada_kN": round(Pz, 4),
            "P_z_geometria_kN": round(total_con_losas, 4),
            "diferencia_kN": round(Pz - total_con_losas, 4),
            "ok": abs(Pz - total_con_losas) < 0.05},
        "equilibrio_vertical": {
            "R_z_kN": round(Rz, 4), "P_z_kN": round(Pz, 4),
            "residuo_kN": round(Rz - Pz, 6), "ok": bool(eq_ok)},
        "receptores_sin_fe": {cod: r["receptores_sin_fe"]
                              for cod, r in repartos.items()},
        "area_no_asignada_total_m2": round(
            sum(r["area_no_asignada_total_m2"] for r in repartos.values()), 4)}


def _comparar(public, public_path, sol, Rz, Pz, seccion):
    """Reproducible vs publicado; mantiene separada la discrepancia de muros."""
    if public is None:
        return {"estado": "SIN_PUBLICADO",
                "motivo": "no existe solucion_FE publicada para %s" % public_path,
                "resumen": None}
    pub_Rz = public["equilibrio_vertical"]["R_z_kN"]
    pub_max = public["max_desp_z_m"]
    pub_nreac = public["n_reacciones"]
    my_max = max_desp_z(sol["desplazamientos"])
    dRz = pub_Rz - Rz
    return {
        "estado": "COMPARACION_REALIZADA",
        "caso": "G", "edificio": "II", "v031_seccion": seccion,
        "solucion_reproducible": {
            "R_z_kN": round(Rz, 4), "P_z_kN": round(Pz, 4),
            "n_reacciones": sol["n_reacciones"],
            "max_desp_z_m": round(my_max, 8)},
        "solucion_publicada": {
            "R_z_kN": pub_Rz, "n_reacciones": pub_nreac,
            "max_desp_z_m": pub_max, "ruta": public_path},
        "resumen": {
            "delta_Rz_kN": round(dRz, 4),
            "delta_max_desp_z_m": round(my_max - pub_max, 8),
            "muros_kN_reproducible": None,
        },
        "diferencia_de_muros": {
            "estado": "PENDIENTE_ORIGEN_PIPELINE",
            "publicado_kN": 6521.26,
            "directo_reproducible_kN": _componentes(MarcoEII(seccion))["muros_directo_kN"],
            "diferencia_kN": None,
            "no_se_aplica_factor": True},
        "componentes": {
            "confirmados": ["columnas", "vigas V.60/80", "losas"],
            "pendientes": ["muros (2.191,24 kN)"],
            "G_EII_cerrado": False}}


def _markdown(cmp):
    if cmp["estado"] != "COMPARACION_REALIZADA":
        return "# G_EII comparacion\n\nSin artefacto publicado.\n"
    r = cmp["resumen"]
    lines = [
        "# Comparacion G_EII reproducido vs publicado",
        "",
        "- escenario V_031: %s" % cmp["v031_seccion"],
        "- R_z reproducible = %.4f kN" % cmp["solucion_reproducible"]["R_z_kN"],
        "- R_z publicado = %.4f kN" % cmp["solucion_publicada"]["R_z_kN"],
        "- delta R_z = %.4f kN" % r["delta_Rz_kN"],
        "- max_desp_z reproducible = %.8f m" % cmp["solucion_reproducible"]["max_desp_z_m"],
        "- max_desp_z publicado = %.8f m" % cmp["solucion_publicada"]["max_desp_z_m"],
        "- n_reacciones reproducible = %d / publicado = %d"
        % (cmp["solucion_reproducible"]["n_reacciones"],
           cmp["solucion_publicada"]["n_reacciones"]),
        "",
        "## Muros",
        "",
        "La diferencia de muros (publicado 6.521,26 kN vs directo %.2f kN)"
        % cmp["diferencia_de_muros"]["directo_reproducible_kN"],
        "permanece **PENDIENTE_ORIGEN_PIPELINE**. No se aplica factor.",
        "",
        "## Componentes",
        "",
        "- confirmados: %s" % ", ".join(cmp["componentes"]["confirmados"]),
        "- pendientes: %s" % ", ".join(cmp["componentes"]["pendientes"]),
        "- `G_EII` cerrado: **NO**",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    seccion = "V.60/80"
    if "--seccion" in args:
        seccion = args[args.index("--seccion") + 1]
    if seccion not in V031_SECCIONES:
        raise SystemExit("seccion no soportada: %s" % seccion)

    marco = MarcoEII(v031_seccion=seccion)
    marco.construir()

    pp_elem = marco.peso_propio_nodal()
    cargas_losa, repartos = marco.losa_tributaria_nodal(incluir_sc=False)

    cargas = {}
    for agg in (pp_elem, cargas_losa):
        for tag, f in agg.items():
            cur = cargas.setdefault(int(tag), [0.0] * 6)
            for i in range(6):
                cur[i] += f[i]

    sol = marco.resolver_caso({"EII": cargas})
    if not sol["ok"]:
        print(json.dumps({"estado": "FALLO",
                          "diagnostico": sol.get("diagnostico")},
                         ensure_ascii=False, indent=2))
        return 1

    Rz = sum(r[2] for r in sol["reacciones"].values())
    Pz = -sum(f[2] for f in cargas.values())
    public, public_path = cargar_publicado(seccion)

    payload = {
        "caso": "G",
        "edificio": "II",
        "motor": "OpenSeesPy (pipeline reproducible EII, adaptador entrega_03)",
        "v031_seccion_escenario": seccion,
        "modo": ("IMPLEMENTADO_Y_VERIFICADO donde aplica; muros "
                 "PENDIENTE_ORIGEN_PIPELINE (no ajustado)"),
        "metadata": {
            "unidades": "kN, m, kN/m3",
            "convencion_signos": ("nodos: [fx,fy,fz,mx,my,mz] en ejes globales "
                                  "(z+ arriba); elementos: localForce/globalForce "
                                  "12 por extremo [P,Vy,Vz,T,My,Mz]"),
            "gamma_kN_m3": GAMMA_CONCRETO_KN_M3,
            "E_mpa": marco.E_mpa,
            "fuentes": [
                "MODELO_FE_GEOMETRIA_NODOS.json (nodos/elementos/conectividad)",
                "eii_viewer.json (materiales, muros, losas)",
                "motor EI: tributaria.py (reparto losa) y resolver.py (OpenSeesPy)",
            ]},
        "hipotesis": marco.historial_hipotesis,
        "modelo": {
            "resumen": marco.resumen(),
            "nodos_coords": {str(t): [round(x, 6) for x in c]
                             for t, c in marco.key_of_tag.items()},
            "restricciones": {
                "base_fija_cp1s_6dof": sorted(marco._base_fixed),
                "diafragma_rigido_pisos": {
                    cod: {"master": mm,
                          "n_esclavos": len(
                              marco.diafragma_esclavos_por_nivel.get(cod, []))}
                    for cod, mm in marco.master_por_nivel.items()}},
            "material": {"E_mpa": marco.E_mpa, "nu": 0.2,
                         "fc_mpa": marco.viewer["materiales"]["fc_MPa"],
                         "grado": marco.viewer["materiales"]["hormigon"]},
            "secciones": {"E_kPa": round(marco.E_kpa, 3),
                          "G_kPa": round(marco.G_kpa, 3),
                          "convencion": ("Elastic [E,A,Iz,Iy,G,J]; "
                                         "Iz=debil, Iy=fuerte")}},
        "elementos": {
            "columnas": [_el(r) for r in marco.columnas],
            "vigas": [_el(r) for r in marco.vigas_elem],
            "muros": [_el(r) for r in marco.muros_elem]},
        "cargas_nodales": {"G": {str(k): [round(x, 6) for x in v]
                                 for k, v in cargas.items()}},
        "solucion": {
            "ok": sol["ok"], "analyze_retcode": sol["analyze_retcode"],
            "F_total_aplicado_kN": [round(x, 6) for x in sol["F_total_kN"]],
            "desplazamientos": {str(k): [round(x, 8) for x in v]
                                for k, v in sol["desplazamientos"].items()},
            "reacciones": {str(k): [round(x, 6) for x in v]
                           for k, v in sol["reacciones"].items()},
            "fuerzas_local_por_elemento": {str(k): [round(x, 6) for x in v]
                                           for k, v in sol["fuerzas"].get("local", {}).items()},
            "fuerzas_global_por_elemento": {str(k): [round(x, 6) for x in v]
                                            for k, v in sol["fuerzas"].get("global", {}).items()}},
        "verificaciones": _verificaciones(marco, sol, cargas, Rz, Pz, repartos),
    }

    RES_DIR.mkdir(parents=True, exist_ok=True)
    jp = RES_DIR / "caso_G_EII_reproducible.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")

    cp = RES_DIR / "caso_G_EII_reproducible_reacciones.csv"
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "Rx_kN", "Ry_kN", "Rz_kN", "Mx_kN_m", "My_kN_m", "Mz_kN_m"])
        for tag, r in sol["reacciones"].items():
            w.writerow([tag] + [round(x, 6) for x in r])

    comparacion = _comparar(public, public_path, sol, Rz, Pz, seccion)
    if comparacion["estado"] == "COMPARACION_REALIZADA":
        dm = comparacion["diferencia_de_muros"]
        dm["diferencia_kN"] = round(dm["publicado_kN"] - dm["directo_reproducible_kN"], 2)
        comparacion["resumen"]["delta_Rz_kN"] = round(
            comparacion["solucion_publicada"]["R_z_kN"] - Rz, 4)
    cpj = RES_DIR / "caso_G_EII_comparacion.json"
    cpj.write_text(json.dumps(comparacion, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    md = RES_DIR / "caso_G_EII_comparacion.md"
    md.write_text(_markdown(comparacion), encoding="utf-8")

    print(json.dumps({
        "edificio": "II", "caso": "G", "v031_seccion": seccion,
        "modelo": marco.resumen(),
        "F_total_aplicado_kN": [round(x, 4) for x in sol["F_total_kN"]],
        "R_z_kN": round(Rz, 4), "P_z_kN": round(Pz, 4),
        "residuo_kN": round(Rz - Pz, 4),
        "n_reacciones": sol["n_reacciones"],
        "max_desp_z_m": round(max_desp_z(sol["desplazamientos"]), 8),
        "comparacion": comparacion.get("resumen"),
        "escrito": [str(jp), str(cp), str(cpj), str(md)]},
        ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())