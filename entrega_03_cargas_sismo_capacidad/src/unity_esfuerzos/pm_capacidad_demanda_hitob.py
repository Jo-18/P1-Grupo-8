"""P-M (capacidad) + demanda concurrente NCh3171 por elemento, para el Hito B.

Lee el perfil de esfuerzos que consume Unity
(`viewer_unity/.../edificios/{I,II}/results/esfuerzos_FE_EDIFICIO_{I,II}.json`,
emitido por `exportar_esfuerzos_funcional_para_viewer.py`) y, SIN recalcular los
resultados estructurales, deriva para cada columna real (y para UN muro fisico
demostrado) el par (P, M) CONCURRENTE de cada combinacion U1..U4 y el D/C contra
el diagrama P-M de la seccion.

Capacidad:
  - Columna: diagrama P-M DEMO_RC_{EI,EII} (armadura 12#25 de DEMOSTRACION,
    HIPOTESIS_DEMOSTRACION, BLOQUEADA por parametros). D/C aritmetico M_dem/M_u(N).
  - Muro: seccion fisica documentada del muro elegido (EII_CP1S_M_001, tag FE 76,
    `M 0.25x3.97x2`) con armadura DECLARADA COMO HIPOTESIS (dos capas; la armadura
    real está BLOQUEADA en parametros_pendientes.json) -> capacidad P-M de
    DEMOSTRACION, NO valida como comprobacion de diseno.

Convencion localForce (12): N en indices 0/6 (+ = compresion), M en 4/5/10/11
(My_i, Mz_i, My_j, Mz_j). P_demanda = max(N_i, N_j) (peor compresion);
M_demanda = max(|M|) del MISMO caso (demanda concurrente).
El caso demostrado por elemento = el que maximiza D/C (regla documentada).

Salidas:
  results/unity_hitob/pm_capacidad_demanda_{I,II}.json   (trazabilidad)
  results/unity_hitob/resumen_pm_demanda_hitob.txt
  viewer_unity/.../results/pm_capacidad_demanda_{I,II}.json (consumido por Unity)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
RES_HITOB = E3 / "results" / "unity_hitob"
PERFIL = (REPO / "viewer_unity" / "Assets" / "StreamingAssets" / "lab_data"
          / "edificios")
RISK = E3 / "results" / "capacidad_rc"

sys.path.insert(0, str(E3))

INDICES_N = (0, 6)
INDICES_M = (4, 5, 10, 11)
NOMBRE_INDICES_M = {4: "My_i", 5: "Mz_i", 10: "My_j", 11: "Mz_j"}
COMBOS_DC = ["U1_GQ", "U2_EX_POS", "U2_EX_NEG", "U3_EY_POS", "U3_EY_NEG",
             "U4_EX_POS", "U4_EX_NEG", "U4_EY_POS", "U4_EY_NEG"]

MURO_EII_TAG = 76  # EII_CP1S_M_001, seccion 'M 0.25x3.97x2' (fisica documentada)
MURO_EII_SECCION = {"etiqueta": "M 0.25x3.97 (b=0.25 espesor, h=3.97 largo)",
                    "b_m": 0.25, "h_m": 3.97,
                    "fuente": "seccion FE del muro EII_CP1S_M_001"}

NOTA_MURO_ARMADURA = (
    "Armadura REAL del muro BLOQUEADA en parametros_pendientes.json; se declara "
    "una HIPOTESIS de demostracion (dos capas ~3.2 cm2/m en cada cara, diam "
    "16 mm @ 0.20). La capacidad resultante es de DEMOSTRACION, NO valida como "
    "comprobacion de diseno.")

CLASIF_EVAL = "EVALUACION_HIPOTESIS_BLOQUEADA_ARMADURA"


def _cargar_perfil(edificio: str) -> dict:
    p = json.loads((PERFIL / edificio / "results"
                    / ("esfuerzos_FE_EDIFICIO_%s.json" % edificio))
                   .read_text(encoding="utf-8"))
    return p


def _cargar_pm_columna(edificio: str) -> dict:
    key = "EII" if edificio == "II" else "EI"
    d = json.loads((RISK / ("DEMO_RC_%s.json" % key)).read_text(encoding="utf-8"))
    pm = d["diagrama_pm"]
    sec = d["seccion"]
    clasif = d.get("clasificacion")
    if isinstance(clasif, dict):
        clasif = clasif.get("clasificacion", "")
    return {"N_kN": pm["N_kN"], "M_kN_m": pm["M_kN_m"],
            "M_u_N0_kN_m": d["M_u_N0_kN_m"], "fc_MPa": sec["materiales"]["hormigon"]["fc_MPa"],
            "seccion": {"etiqueta": sec["etiqueta"], "h_m": sec.get("h_m"),
                        "b_m": sec.get("b_m"), "n_barras": sec.get("n_barras"),
                        "As_total_m2": sec.get("As_total_m2")},
            "clasificacion": clasif, "estado_armadura": (sec.get("armadura") or {}).get("estado")
            if isinstance(sec.get("armadura"), dict) else None}


def _mu_interp(N_kN: float, Ns, Ms):
    """M_u(N) lineal entre puntos (igual regla que demanda_capacidad)."""
    if N_kN <= Ns[0]:
        return Ms[0], "acotado_extremo_inferior"
    if N_kN >= Ns[-1]:
        return Ms[-1], "acotado_extremo_superior"
    i = next(i for i in range(len(Ns) - 1) if Ns[i] <= N_kN <= Ns[i + 1])
    t = (N_kN - Ns[i]) / (Ns[i + 1] - Ns[i])
    return Ms[i] + t * (Ms[i + 1] - Ms[i]), "interpolado"


def _concurrente(forces: list) -> dict:
    """P y M CONCURRENTES dentro del mismo caso (fuerzas de 12 componentes)."""
    n_i, n_j = float(forces[0]), float(forces[6])
    idx = max(INDICES_M, key=lambda i: abs(float(forces[i])))
    return {"N_i_kN": round(n_i, 3), "N_j_kN": round(n_j, 3),
            "N_demanda_kN": max(n_i, n_j),
            "M_demanda_kN_m": abs(float(forces[idx])),
            "indice_M_dominante": NOMBRE_INDICES_M[idx],
            "extremo_M": "i" if idx in (4, 5) else "j"}


def _muro_pm(seccion: dict, N_max_kN: float) -> dict:
    """P-M del muro con armadura HIPOTESIS (NO valida como diseno)."""
    from src.capacidad_rc.diagrama_pm import puntos_pm
    from src.capacidad_rc.seccion import seccion_con_armado
    h = seccion["h_m"]
    b = seccion["b_m"]
    fc = 35.0  # G35 documentado en eii_viewer.json (mismo que DEMO_RC_EII)
    # hipotesis: dos capas ~3.2 cm2/m/cara (diam 16 @ 0.20) distribuidas
    capas = int(round(h / 0.20))
    n_cn = 4
    sec = seccion_con_armado(h=h, b=b, rec=0.04, diam_m=0.016,
                             n_cn=n_cn, n_en_medio_cn_Y=0,
                             n_en_medio_cn_Z=max(0, capas - 2),
                             fc_mpa=fc, fy_mpa=420.0)
    sec.etiqueta = "MURO_EII_CP1S_M_001_HIPOTESIS"
    pm = puntos_pm(sec, N_min_kN=0.0, N_max_kN=N_max_kN, n_puntos=15)
    return {"N_kN": pm["N_kN"], "M_kN_m": pm["M_kN_m"],
            "fc_MPa": fc, "seccion": dict(seccion),
            "armadura_hipotesis": NOTA_MURO_ARMADURA,
            "clasificacion": CLASIF_EVAL}


def _evaluar(edificio: str, caso_muro: str | None = None) -> dict:
    perfil = _cargar_perfil(edificio)
    pm_col = _cargar_pm_columna(edificio)
    cols = [e for e in perfil["elementos"] if e["tipo"] == "columna"]
    por_elemento = {}
    filas = []
    for el in cols:
        f = el["fuerzas"]
        corr = el["correspondencia"]
        vid = corr.get("viewer_id")
        mejor = None
        for caso in COMBOS_DC:
            c = _concurrente(f[caso])
            mu, modo = _mu_interp(c["N_demanda_kN"], pm_col["N_kN"],
                                  pm_col["M_kN_m"])
            dc = c["M_demanda_kN_m"] / mu if mu > 0 else float("inf")
            fila = {"tag": el["tag"], "nivel": el["nivel"],
                    "viewer_id": vid,
                    "estado_correspondencia": corr.get("estado"),
                    "caso": caso, "expresion": _expresion(caso),
                    "P_u_kN": c["N_demanda_kN"], "N_i_kN": c["N_i_kN"],
                    "N_j_kN": c["N_j_kN"],
                    "M_demanda_kN_m": c["M_demanda_kN_m"],
                    "indice_M_dominante": c["indice_M_dominante"],
                    "extremo_M": c["extremo_M"],
                    "M_u_N_kN_m": round(mu, 4), "modo_mu": modo,
                    "D_C": round(dc, 4)}
            if mejor is None or dc > mejor["D_C"]:
                mejor = fila
        por_elemento[str(el["tag"])] = mejor
        filas.append(mejor)

    if not filas:
        raise SystemExit(f"{edificio}: sin columnas reales en el perfil")
    demostrables = [r for r in filas if r["viewer_id"]]
    pool = demostrables or filas
    critico = max(pool, key=lambda r: r["D_C"])

    result = {
        "edificio": edificio,
        "tipo_demostrado": "columna",
        "perfil_fuente": perfil["fecha"],
        "capacidad": pm_col,
        "demanda_convencion": ("P = max(N_i,N_j) compresion (+); M = max(|M| "
                               "indices 4/5/10/11) del MISMO caso (concurrente); "
                               "D/C = M_dem/M_u(P) aritmetico (sin validez de diseno)"),
        "regla_seleccion": "caso demostrado por elemento = max(D/C) entre U1..U4; "
                           "columna demostrada = max(D/C) entre columnas reales "
                           "con viewer_id (1A1)",
        "n_columnas_totales": len(filas),
        "n_columnas_demostrables": len(demostrables),
        "columna_critica": critico,
        "por_elemento": por_elemento,
    }
    if caso_muro is not None:
        mur = perfil["elementos"]
        el = next((e for e in mur if e["tag"] == caso_muro
                   and e["tipo"] == "muro"), None)
        if el is None:
            raise SystemExit(f"{edificio}: muro tag {caso_muro} no existe")
        best = None
        for caso in COMBOS_DC:
            c = _concurrente(el["fuerzas"][caso])
            fila = {"caso": caso, "expresion": _expresion(caso),
                    "P_u_kN": c["N_demanda_kN"],
                    "M_demanda_kN_m": c["M_demanda_kN_m"],
                    "indice_M_dominante": c["indice_M_dominante"],
                    "extremo_M": c["extremo_M"]}
            if best is None or c["M_demanda_kN_m"] > best["M_demanda_kN_m"]:
                best = fila
        n_max = max(1.0, best["P_u_kN"] * 2.0)
        pm_mur = _muro_pm(MURO_EII_SECCION, N_max_kN=max(15000.0, n_max))
        mu, modo = _mu_interp(best["P_u_kN"], pm_mur["N_kN"], pm_mur["M_kN_m"])
        demand = {"elemento_demostrado": {"tag": caso_muro,
                                          "nivel": el["nivel"],
                                          "viewer_id": el["correspondencia"].get("viewer_id")},
                  "demanda_concurrente": best,
                  "M_u_N_kN_m": round(mu, 4), "modo_mu": modo,
                  "D_C": round(best["M_demanda_kN_m"] / mu, 4) if mu > 0 else None}
        result["muro_demostrado"] = {
            "seccion": MURO_EII_SECCION,
            "capacidad_pm": pm_mur,
            "demanda": demand,
            "nota_armadura": NOTA_MURO_ARMADURA}
    return result


def _expresion(caso: str) -> str:
    from src.modelo_fiel.combinaciones_nch3171 import COMBINACIONES_NCH3171
    for c in COMBINACIONES_NCH3171:
        if c["id"] == caso:
            return c["expresion"]
    return caso


def _escribir(edificio: str, data: dict) -> list:
    RES_HITOB.mkdir(parents=True, exist_ok=True)
    jp = RES_HITOB / ("pm_capacidad_demanda_%s.json" % edificio)
    jp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                  encoding="utf-8")
    dest = PERFIL / edificio / "results" / ("pm_capacidad_demanda_%s.json"
                                            % edificio)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    return [jp, dest]


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    edificios = [a for a in args if a in ("I", "II")] or ["I", "II"]
    escritos = []
    resumen = {}
    for edificio in edificios:
        caso_muro = MURO_EII_TAG if edificio == "II" else None
        data = _evaluar(edificio, caso_muro)
        escritos += _escribir(edificio, data)
        crit = data["columna_critica"]
        resumen[edificio] = {
            "columna_critica": {"tag": crit["tag"], "nivel": crit["nivel"],
                                "caso": crit["caso"], "P_u_kN": crit["P_u_kN"],
                                "M_demanda_kN_m": crit["M_demanda_kN_m"],
                                "M_u_N_kN_m": crit["M_u_N_kN_m"], "D_C": crit["D_C"]},
            "n_columnas": len(data["por_elemento"]),
            "capacidad": data["capacidad"]["clasificacion"]}
        if "muro_demostrado" in data:
            mur = data["muro_demostrado"]["demanda"]
            resumen[edificio]["muro_demostrado"] = {
                "tag": mur["elemento_demostrado"]["tag"], "caso": mur["demanda_concurrente"]["caso"],
                "P_u_kN": mur["demanda_concurrente"]["P_u_kN"],
                "M_demanda_kN_m": mur["demanda_concurrente"]["M_demanda_kN_m"],
                "M_u_N_kN_m": mur["M_u_N_kN_m"], "D_C": mur["D_C"]}
        print(json.dumps({"edificio": edificio, **resumen[edificio]},
                         ensure_ascii=False, indent=2))
    (RES_HITOB / "resumen_pm_demanda_hitob.txt").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"escrito_en": [str(p) for p in escritos]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())