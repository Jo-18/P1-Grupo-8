"""Evaluacion demanda/capacidad (D/C) por edificio con seccion HIPOTESIS_DEMOSTRACION.

ALCANCE (leer antes de interpretar numeros): la capacidad usada NO es la real de
diseno. Procede de las secciones DEMO_RC_EI / DEMO_RC_EII (armado de DEMOSTRACION
12#25, marcado HIPOTESIS_DEMOSTRACION porque la armadura real esta BLOQUEADA en
parametros_pendientes.json). Por tanto el resultado de este modulo es una:

    EVALUACION_ALGORITMICA_CON_SECCION_DEMO

- columnas evaluadas MEDIANTE EL PROCEDIMIENTO (no "aprobadas");
- capacidad de DEMOSTRACION (no capacidad real);
- resultado NO VALIDO como comprobacion de diseno;
- NO representa aprobacion estructural de las columnas reales.
- D/C = max(D/C) es la demostracion de integracion demanda->capacidad->seleccion,
  no una comprobacion normativa. Mientras la armadura y materiales reales no esten
  documentados NO se usan los verbos "cumple", "segura" ni "aprobada".

Demanda: desde la corrida EXPLICITA verificada de la superposicion completa
(results/superposicion/verificacion_superposicion_completa_{I,II}.json,
resultados_por_corrida.EXPLICITA.fuerzas_local), que ya es la combinacion
R = 1.0*G + 0.7*Q + 0.3*EX - 0.2*EY (conjunto de demostracion, no normativa).

Capacidad: diagrama P-M de la seccion DEMO_RC_{I,II}
(results/capacidad_rc/DEMO_RC_{I,II}.json) con M_u(N) interpolado linealmente
entre los puntos P-M (N compresion positiva; fuera de rango se acota al extremo
mas cercano y queda marcado).

Seleccion TRACEABLE de la demanda:
  1) por cada columna real del modelo (marco reconstruido IDENTICO al de la
     verificacion) se lee de localForce(12): N = axial (indices 0 y 6, + =
     compresion comprobada para columnas) y M = el mayor de |Mz_i|,|My_i|,
     |Mz_j|,|My_j| (indices 4,5,10,11). Se registra cual extremo/index manda.
  2) se interpola M_u(N) del diagrama P-M.
  3) D/C = M_demanda / M_u(N_demanda); columna CRITICA = max(D/C) de todas las
     columnas (regla documentada), con tag, nivel, extremo y los parametros de
     la seccion y su procedencia.

Salidas:
  results/capacidad_rc/demanda_capacidad_{I,II}.json
  results/capacidad_rc/demanda_capacidad_{I,II}.csv
  results/capacidad_rc/resumen_demanda_capacidad.txt

Uso: python -X utf8 -m src.capacidad_rc.demanda_capacidad
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
RES = E3 / "results" / "capacidad_rc"
SUP = E3 / "results" / "superposicion"
EI_SRC = REPO / "analisis_estructural" / "edificio_I" / "src"

sys.path.insert(0, str(E3))
sys.path.insert(0, str(EI_SRC))

INDICES_MOMENTO = (4, 5, 10, 11)  # Mz_i, My_i, Mz_j, My_j en localForce(12)
NOMBRE_INDICES_MOMENTO = {4: "Mz_i", 5: "My_i", 10: "Mz_j", 11: "My_j"}

CLASIFICACION_EVAL = "EVALUACION_ALGORITMICA_CON_SECCION_DEMO"
NOTA_NO_DISENO = ("capacidad de DEMOSTRACION (armado 12#25 BLOQUEADO); resultado "
                  "NO valido como comprobacion de diseno; NO representa aprobacion "
                  "estructural de las columnas reales.")

CONVENCION_NOTA = ("localForce OpenSees 12: indices 0/6 = N_i/N_j, + = compresion "
                   "(verificado para columnas); N_demanda = max(N_i, N_j) en kN de "
                   "compresion (compresion positiva, igual que el diagrama P-M). "
                   "M_dem = max(|Mz_i|,|My_i|,|Mz_j|,|My_j|) de los indices 4/5/10/11.")


def _marco(edificio: str):
    from src.cargas.verificacion_superposicion_completa import _nuevo_marco
    return _nuevo_marco(edificio)


def _cargar_demanda_explicita(edificio: str) -> dict:
    suf = "I" if edificio == "I" else "II"
    d = json.loads((SUP / ("verificacion_superposicion_completa_%s.json" % suf))
                   .read_text(encoding="utf-8"))
    return d["resultados_por_corrida"]["EXPLICITA"]["fuerzas_local"]


def _cargar_capacidad(edificio: str) -> dict:
    key = "EII" if edificio == "II" else "EI"
    d = json.loads((RES / ("DEMO_RC_%s.json" % key)).read_text(encoding="utf-8"))
    pm = d["diagrama_pm"]
    return {"M_u_N0_kN_m": d["M_u_N0_kN_m"], "N_kN": pm["N_kN"],
            "M_kN_m": pm["M_kN_m"], "clasificacion": d["clasificacion"],
            "fc_MPa": d["seccion"]["materiales"]["hormigon"]["fc_MPa"],
            "seccion_demo": d["seccion"]}


def _extremos_demanda(lf) -> dict:
    """Identifica el extremo/index que manda en N y en M (trazabilidad)."""
    n_i, n_j = float(lf[0]), float(lf[6])
    idx_m = max(INDICES_MOMENTO, key=lambda i: abs(float(lf[i])))
    extremo = "i" if idx_m in (4, 5) else "j"
    return {"N_i_kN": n_i, "N_j_kN": n_j,
            "extremo_N": "i" if n_i >= n_j else "j",
            "indice_M_dominante": NOMBRE_INDICES_MOMENTO[idx_m],
            "extremo_M": extremo}


def _M_u_interp(N_kN, Ns, Ms) -> dict:
    if N_kN <= Ns[0]:
        return {"M_u_kN_m": Ms[0], "modo": "acotado_extremo_inferior"}
    if N_kN >= Ns[-1]:
        return {"M_u_kN_m": Ms[-1], "modo": "acotado_extremo_superior"}
    i = next(i for i in range(len(Ns) - 1) if Ns[i] <= N_kN <= Ns[i + 1])
    t = (N_kN - Ns[i]) / (Ns[i + 1] - Ns[i])
    return {"M_u_kN_m": Ms[i] + t * (Ms[i + 1] - Ms[i]), "modo": "interpolado"}


def _evaluar(edificio: str) -> dict:
    marco = _marco(edificio)
    col_meta = {int(c["tag"]): c for c in marco.columnas}
    col_tags = sorted(col_meta)
    fl = _cargar_demanda_explicita(edificio)
    cap = _cargar_capacidad(edificio)
    Ns, Ms = cap["N_kN"], cap["M_kN_m"]

    filas = []
    for tag in col_tags:
        lf = fl.get(str(tag))
        if lf is None:
            raise SystemExit("ABORTE: la columna %d no esta en las fuerzas de la "
                             "verificacion de superposicion (modelo distinto)." % tag)
        ext = _extremos_demanda(lf)
        N_axial = max(ext["N_i_kN"], ext["N_j_kN"])   # peor extremo, + = compresion
        M_dem = max(abs(float(lf[i])) for i in INDICES_MOMENTO)
        interp = _M_u_interp(N_axial, Ns, Ms)
        M_u = interp["M_u_kN_m"]
        dc = M_dem / M_u if M_u > 0 else float("inf")
        meta = col_meta[tag]
        filas.append({"tag": tag, "nivel": meta.get("nivel"),
                      "N_i_kN": round(ext["N_i_kN"], 3),
                      "N_j_kN": round(ext["N_j_kN"], 3),
                      "N_demanda_kN": round(N_axial, 3),
                      "M_demanda_kN_m": round(M_dem, 4),
                      "indice_M_dominante": ext["indice_M_dominante"],
                      "extremo_M": ext["extremo_M"],
                      "M_u(N)_kN_m": round(M_u, 4),
                      "interp": interp["modo"],
                      "D/C": round(dc, 4),
                      "comparacion_cuota_aritmetica":
                          "D/C <= 1" if dc <= 1.0 else "D/C > 1"})

    critico = max(filas, key=lambda f: f["D/C"])
    n_dentro = sum(1 for f in filas if f["comparacion_cuota_aritmetica"] == "D/C <= 1")
    n_fuera = len(filas) - n_dentro
    filas.sort(key=lambda f: -f["D/C"])

    selected = [f for f in filas if f["D/C"] == critico["D/C"]]
    detalles = []
    for f in selected:
        meta = col_meta[f["tag"]]
        lf = fl.get(str(f["tag"]))
        detalles.append({
            "edificio": edificio,
            "elemento": {"tag": f["tag"], "nivel": f.get("nivel"),
                         "elemento_id": meta.get("elemento_id"),
                         "nodo_i": int(meta["nodo_i"]),
                         "nodo_j": int(meta["nodo_j"]),
                         "cota_z_i_m": meta.get("z_i"), "cota_z_j_m": meta.get("z_j")},
            "combinacion": "1.0*G + 0.7*Q + 0.3*EX - 0.2*EY "
                           "(conjunto de demostracion, NO normativa)",
            "P_u_kN": f["N_demanda_kN"], "M_demanda_kN_m": f["M_demanda_kN_m"],
            "indice_M_dominante": f["indice_M_dominante"],
            "extremo_M": f["extremo_M"],
            "capacidad_interpolada_kN_m": f["M_u(N)_kN_m"],
            "interpolacion": {"modo": f["interp"],
                              "rango_PM_N_kN": [Ns[0], Ns[-1]]},
            "D/C": f["D/C"],
            "seccion_utilizada": {"etiqueta": cap["seccion_demo"]["etiqueta"],
                                  "h_m": cap["seccion_demo"]["h_m"],
                                  "b_m": cap["seccion_demo"]["b_m"],
                                  "As_total_m2": cap["seccion_demo"]["As_total_m2"],
                                  "n_barras": cap["seccion_demo"]["n_barras"]},
            "procedencia_parametros": cap["clasificacion"],
            "estado": CLASIFICACION_EVAL,
            "nota": NOTA_NO_DISENO})
        _ = lf

    return {"edificio": edificio,
            "seccion": "DEMO_RC_%s" % ("EII" if edificio == "II" else "EI"),
            "clasificacion": {"evaluacion": CLASIFICACION_EVAL,
                              "seccion": cap["clasificacion"]},
            "demanda": {"fuente": "corrida EXPLICITA superposicion completa "
                                  "(R=1.0G+0.7Q+0.3EX-0.2EY, conjunto demostracion)",
                        "convencion": CONVENCION_NOTA},
            "capacidad": {"fuente": "DEMO_RC_%s.json (diagrama P-M)" %
                          ("EII" if edificio == "II" else "EI"),
                          "M_u_N0_kN_m": cap["M_u_N0_kN_m"],
                          "fc_MPa": cap["fc_MPa"]},
            "n_columnas_evaluadas": len(filas),
            "seleccion_demanda": {"regla": "columna CRITICA = max(D/C) sobre todas "
                                           "las columnas; M_dem = max(|M| extremos 4/5/10/11)",
                                  "columna_critica": critico,
                                  "detalle_columna_critica": detalles},
            "filas": filas,
            "resumen": {"n_dentro_cuota_aritmetica": n_dentro,
                        "n_fuera_cuota_aritmetica": n_fuera,
                        "max_D/C": critico["D/C"],
                        "columna_critica_tag": critico["tag"],
                        "clasificacion": CLASIFICACION_EVAL}}


def _escribir(edificio: str, data: dict) -> list:
    RES.mkdir(parents=True, exist_ok=True)
    suf = "I" if edificio == "I" else "II"
    jp = RES / ("demanda_capacidad_%s.json" % suf)
    jp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")
    cp = RES / ("demanda_capacidad_%s.csv" % suf)
    with open(cp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "nivel", "N_i_kN", "N_j_kN", "N_demanda_kN",
                    "M_demanda_kN_m", "indice_M_dominante", "extremo_M",
                    "M_u_N_kN_m", "modo_interp", "D_C",
                    "comparacion_cuota_aritmetica"])
        for r in data["filas"]:
            w.writerow([r["tag"], r["nivel"], r["N_i_kN"], r["N_j_kN"],
                        r["N_demanda_kN"], r["M_demanda_kN_m"],
                        r["indice_M_dominante"], r["extremo_M"],
                        r["M_u(N)_kN_m"], r["interp"], r["D/C"],
                        r["comparacion_cuota_aritmetica"]])
    return [jp, cp]


def main(argv=None) -> int:
    _ = argv if argv is not None else sys.argv[1:]
    resumenes = {}
    escritos = []
    for edificio in ("I", "II"):
        data = _evaluar(edificio)
        resumenes[edificio] = {
            "seccion": data["seccion"],
            "clasificacion": data["resumen"]["clasificacion"],
            "n_columnas_evaluadas": data["n_columnas_evaluadas"],
            "n_dentro_cuota_aritmetica": data["resumen"]["n_dentro_cuota_aritmetica"],
            "n_fuera_cuota_aritmetica": data["resumen"]["n_fuera_cuota_aritmetica"],
            "max_D_C": data["resumen"]["max_D/C"],
            "columna_critica": data["resumen"]["columna_critica_tag"]}
        escritos += _escribir(edificio, data)
        crit = data["seleccion_demanda"]["detalle_columna_critica"][0]
        print(json.dumps({
            "edificio": edificio,
            "seccion": data["seccion"],
            "clasificacion": data["resumen"]["clasificacion"],
            "columnas": "%d/%d por debajo de D/C<=1 (aritmetico, sin validez de diseno)"
                        % (data["resumen"]["n_dentro_cuota_aritmetica"],
                           data["n_columnas_evaluadas"]),
            "columna_critica": {
                "tag": crit["elemento"]["tag"],
                "nivel": crit["elemento"]["nivel"],
                "extremo_M": crit["extremo_M"],
                "D/C": crit["D/C"]},
            "nota": NOTA_NO_DISENO},
            ensure_ascii=False, indent=2))

    tp = RES / "resumen_demanda_capacidad.txt"
    lineas = ["RESUMEN DEMANDA/CAPACIDAD",
              "CLASIFICACION: %s" % CLASIFICACION_EVAL,
              "(" + NOTA_NO_DISENO + ")",
              "=" * 40, ""]
    for editag, r in resumenes.items():
        lineas.append("Edificio %s (%s):" % (editag, r["seccion"]))
        lineas.append("  columnas evaluadas (procedimiento) : %d" % r["n_columnas_evaluadas"])
        lineas.append("  dentro de D/C<=1 (aritmetico)     : %d" % r["n_dentro_cuota_aritmetica"])
        lineas.append("  fuera de D/C<=1 (aritmetico)      : %d" % r["n_fuera_cuota_aritmetica"])
        lineas.append("  max D/C (demo)                    : %.3f" % r["max_D_C"])
        lineas.append("  columna critica                   : %s" % r["columna_critica"])
        lineas.append("")
    lineas.append("ADVERTENCIA: secciones de DEMOSTRACION (armado 12#25). El resultado")
    lineas.append("NO es valido como comprobacion de diseno ni aprobacion estructural.")
    lineas.append("D/C <= 1 es una comparacion ARITMETICA M_dem/M_u(N) con capacidad demo.")
    lineas.append("Regla de seleccion: columna critica = max(D/C) sobre todas las ")
    lineas.append("columnas; M_dem = max(|M| extremos).")
    tp.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    escritos.append(tp)
    print(json.dumps({"clasificacion": CLASIFICACION_EVAL,
                      "resumen": resumenes,
                      "escrito_en": [str(p) for p in escritos]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())