"""Genera los diagramas internos reales (exactos) del elemento FE 489 del
Edificio II, caso G, con las estaciones entre x=0 y x=L, a partir del paquete
canonico que consume el viewer (`esfuerzos_FE_EDIFICIO_II.json`).

Metodo: equilibrio exacto para un `elasticBeamColumn` sin cargas interiores
(las cargas del perfil MODELO_FE_COMPLETO_FUNCIONAL son nodales). La forma
exacta de los 6 resultantes en ejes locales del FE es:

    N(x)  = N_i
    Vy(x) = Vy_i
    Vz(x) = Vz_i
    T(x)  = T_i
    My(x) = My_i + Vz_i*x
    Mz(x) = Mz_i - Vy_i*x

con los valores del extremo i tomados del vector `localForce` del caso G del
elemento (indices segun `indices_componentes` del propio payload). No se
interpola valor_i -> valor_j con los signos nodales del vector; el extremo j se
controla por equilibrio en x=L (N/Vy/Vz/T/My/Mz ~= -valores del extremo j).

Antes de escribir valida el payload (SHA256 de los bytes, edificio, n_elementos,
unicidad del tag 489, tipo, viewer_id, nodos, longitud 3.05 m, seccion,
indices, vector de 12 comps finitos, caso G). Si falla cualquier condicion, o
falla una comprobacion de extremos/equilibrio con la tolerancia explicita,
ABORTA sin escribir (escribe via temporal + os.replace en el mismo directorio).
La salida es determinista: no lleva marca de generacion, solo la fecha y el
SHA256 del payload fuente.

Salida:
  viewer_unity/Assets/StreamingAssets/lab_data/edificios/II/results/
  diagramas_FE_tag489_G.json   (formato diagrama_interno_FE_v1)

CLI:
  python src/unity_esfuerzos/exportar_diagrama_ar_tag489.py
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
RESULTADOS = (RAIZ / "viewer_unity" / "Assets" / "StreamingAssets"
              / "lab_data" / "edificios" / "II" / "results")
PAYLOAD = RESULTADOS / "esfuerzos_FE_EDIFICIO_II.json"
SALIDA = RESULTADOS / "diagramas_FE_tag489_G.json"

FORMATO = "diagrama_interno_FE_v1"
VERSION = 1
TAG = 489
EDIFICIO = "II"
N_ELEMENTOS_ESPERADO = 258
VIEWER_ID = "EII_CP2_V_029"
CASO = "G"
SECCION = "V.30/80"
LONGITUD_ESPERADA_M = 3.05
N_STATIONS = 51

INDICES_ESPERADOS = {
    "N_i": 0, "Vy_i": 1, "Vz_i": 2, "T_i": 3, "My_i": 4, "Mz_i": 5,
    "N_j": 6, "Vy_j": 7, "Vz_j": 8, "T_j": 9, "My_j": 10, "Mz_j": 11,
}

# Tolerancia explicita y pequena: 6 decimales del payload (1e-6) + 1 ulp del
# producto Vz*L en el redondeo interior (~1e-7); la comparacion de extremos y
# equilibrio usa la misma.
TOL = 1e-5

CONVENCION = (
    "Resultantes internas sobre el corte, en ejes locales del FE (x local = eje "
    "u de i a j; y local = v; z local = cota, arriba). El diagrama en x=0 "
    "coincide con los 6 primeros componentes del vector localForce del caso G "
    "del elemento (indices_componentes del payload). Forma exacta sin cargas "
    "interiores: N(x)=N_i; Vy(x)=Vy_i; Vz(x)=Vz_i; T(x)=T_i; "
    "My(x)=My_i+Vz_i*x; Mz(x)=Mz_i-Vy_i*x. +N = compresion en el extremo. "
    "Unidades: kN y kN*m. El extremo j del vector reporta las fuerzas NODALES "
    "(opuestas por convencion al corte interior en x=L); por eso en x=L se "
    "verifica diagrama ~= -extremo_j."
)

ADVERTENCIA = {
    "es_snapshot_FE_258_elementos": True,
    "nota": (
        "Los diagramas corresponden al snapshot FE del Edificio II de 258 "
        "elementos que consume la aplicacion (esfuerzos_FE_EDIFICIO_II.json, "
        "fecha y SHA256 en payload_fuente). El generador general actual del "
        "repositorio todavia NO reproduce esa topologia: el modelo regenerado "
        "hoy tiene 253 elementos y excluye la viga de junta EII_CP2_V_029 "
        "como PENDIENTE_DE_FUENTE. NO presentar este JSON como resultado de "
        "una regeneracion actual del modelo completo."),
    "no_presentar_como": "regeneracion_actual_modelo_completo",
}

UNIDADES = {"fuerza": "kN", "momento": "kN*m", "longitud": "m"}

FUENTE_METODOLOGICA = (
    "Equilibrio exacto de un elasticBeamColumn sin cargas interiores (todas "
    "las cargas G del perfil son nodales via ops.load). La forma exacta de los "
    "diagramas se dedujo de la mecanica del elemento y se verifico en T31A "
    "reproduciendo el localForce del tag 489 con OpenSeesPy desde los "
    "desplazamientos publicados en el propio payload (max|diff| ~ 1e-3, por el "
    "redondeo de los desplazamientos). No se interpola valor_i -> valor_j.")
SIN_CARGAS_INTERIORES_NOTA = (
    "sin_cargas_interiores = True: el elemento 489 no tiene eleLoad; su "
    "distribucion interna proviene solo de las fuerzas nodales de extremo "
    "(Vz y T constantes, My lineal).")


def _finito(v: list) -> bool:
    return len(v) == 12 and all(isinstance(x, (int, float)) and math.isfinite(x)
                                for x in v)


def _f6(x: float) -> float:
    r = round(float(x), 6)
    return 0.0 if r == 0 else r


def _determinado(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def main():
    if not PAYLOAD.is_file():
        sys.exit(f"ABORTA: no existe el payload canónico: {PAYLOAD}")

    bytes_payload = PAYLOAD.read_bytes()
    sha256_payload = hashlib.sha256(bytes_payload).hexdigest().upper()
    p = json.loads(bytes_payload.decode("utf-8"))

    def falla(mensaje):
        sys.exit(f"ABORTA (no se escribe {SALIDA.name}): {mensaje}")

    if p.get("formato") != "esfuerzos_FE_edificio_v1":
        falla("formato inesperado: %r" % p.get("formato"))
    if p.get("edificio") != EDIFICIO:
        falla(f"edificio != {EDIFICIO}: {p.get('edificio')!r}")
    if p.get("n_elementos") != N_ELEMENTOS_ESPERADO:
        falla("n_elementos != 258: %r" % p.get("n_elementos"))
    fecha = p.get("fecha")
    if not isinstance(fecha, str) or not fecha:
        falla("payload sin fecha")
    indices = p.get("indices_componentes")
    if indices != INDICES_ESPERADOS:
        falla("indices_componentes inesperados: %r" % (indices,))

    elementos = p.get("elementos")
    if not isinstance(elementos, list) or len(elementos) != N_ELEMENTOS_ESPERADO:
        falla(f"lista de elementos con {len(elementos)} entradas (esperado "
              f"{N_ELEMENTOS_ESPERADO})")

    match = [e for e in elementos if e.get("tag") == TAG]
    if len(match) != 1:
        falla(f"se esperaba EXACTAMENTE un elemento tag {TAG}; se hallaron "
              f"{len(match)}")
    el = match[0]

    if el.get("tipo") != "viga":
        falla(f"tipo != viga: {el.get('tipo')!r}")
    if (el.get("correspondencia") or {}).get("viewer_id") != VIEWER_ID:
        falla(f"viewer_id != {VIEWER_ID}: "
              f"{(el.get('correspondencia') or {}).get('viewer_id')!r}")
    if el.get("nodo_i") != "487" or el.get("nodo_j") != "488":
        falla(f"nodos != 487->488: {el.get('nodo_i')!r}->{el.get('nodo_j')!r}")
    if el.get("seccion") != SECCION:
        falla(f"seccion != {SECCION}: {el.get('seccion')!r}")

    pi, pj = el.get("p_i_unity"), el.get("p_j_unity")
    if not (isinstance(pi, list) and isinstance(pj, list)
            and len(pi) == 3 and len(pj) == 3
            and all(math.isfinite(x) for x in pi + pj)):
        falla(f"coordenadas invalidas: p_i={pi}, p_j={pj}")
    L = sum((a - b) ** 2 for a, b in zip(pi, pj)) ** 0.5
    if abs(L - LONGITUD_ESPERADA_M) > 1e-6:
        falla(f"longitud != {LONGITUD_ESPERADA_M} m: {L:.6f} m")

    fuerzas = el.get("fuerzas")
    if not isinstance(fuerzas, dict) or CASO not in fuerzas:
        falla(f"caso {CASO} ausente en las fuerzas del elemento")
    v = [float(x) for x in fuerzas[CASO]]
    if not _finito(v):
        falla("vector de caso G sin 12 componentes finitas")

    inx = INDICES_ESPERADOS
    N_i, Vy_i, Vz_i, T_i, My_i, Mz_i = (v[inx[c]] for c in
                                        ("N_i", "Vy_i", "Vz_i", "T_i",
                                         "My_i", "Mz_i"))
    N_j, Vy_j, Vz_j, T_j, My_j, Mz_j = (v[inx[c]] for c in
                                        ("N_j", "Vy_j", "Vz_j", "T_j",
                                         "My_j", "Mz_j"))

    stations = []
    for k in range(N_STATIONS):
        x = k * L / (N_STATIONS - 1)
        stations.append({
            "k": k,
            "xi": round(k / (N_STATIONS - 1), 6),
            "x_m": round(x, 6),
            "N_kN": _f6(N_i),
            "Vy_kN": _f6(Vy_i),
            "Vz_kN": _f6(Vz_i),
            "T_kN_m": _f6(T_i),
            "My_kN_m": _f6(My_i + Vz_i * x),
            "Mz_kN_m": _f6(Mz_i - Vy_i * x),
        })

    s0, sL = stations[0], stations[-1]
    checks = []

    def add(nombre, ok, detalle):
        checks.append({"check": nombre, "ok": bool(ok), "detalle": detalle})
        return bool(ok)

    add("x_inicio_0", abs(s0["x_m"]) <= 1e-9, {"x_m": s0["x_m"]})
    add("x_fin_L", abs(sL["x_m"] - L) <= 1e-6,
        {"x_m": sL["x_m"], "L_m": round(L, 6)})
    add("n_stations_51", len(stations) == N_STATIONS,
        {"n": len(stations)})
    add("sin_nan_inf",
        all(math.isfinite(s[c]) for s in stations
            for c in ("N_kN", "Vy_kN", "Vz_kN", "T_kN_m", "My_kN_m", "Mz_kN_m")),
        {"stations": len(stations)})

    add("equilibrio_fuerzas_N", abs(N_i + N_j) <= TOL, {"N_i+N_j": _f6(N_i + N_j)})
    add("equilibrio_fuerzas_Vy", abs(Vy_i + Vy_j) <= TOL,
        {"Vy_i+Vy_j": _f6(Vy_i + Vy_j)})
    add("equilibrio_fuerzas_Vz", abs(Vz_i + Vz_j) <= TOL,
        {"Vz_i+Vz_j": _f6(Vz_i + Vz_j)})
    add("equilibrio_torsor", abs(T_i + T_j) <= TOL, {"T_i+T_j": _f6(T_i + T_j)})
    add("equilibrio_momento_local_y_sobre_i",
        abs(-(My_i + My_j) + L * Vz_j) <= TOL,
        {"residuo_kN_m": _f6(-(My_i + My_j) + L * Vz_j)})
    add("equilibrio_momento_local_z_sobre_i",
        abs(-(Mz_i + Mz_j) - L * Vy_j) <= TOL,
        {"residuo_kN_m": _f6(-(Mz_i + Mz_j) - L * Vy_j)})

    add("extremo_L_N", abs(sL["N_kN"] + N_j) <= TOL,
        {"diagrama_N(L)": sL["N_kN"], "-N_j": _f6(-N_j)})
    add("extremo_L_Vy", abs(sL["Vy_kN"] + Vy_j) <= TOL,
        {"diagrama_Vy(L)": sL["Vy_kN"], "-Vy_j": _f6(-Vy_j)})
    add("extremo_L_Vz", abs(sL["Vz_kN"] + Vz_j) <= TOL,
        {"diagrama_Vz(L)": sL["Vz_kN"], "-Vz_j": _f6(-Vz_j)})
    add("extremo_L_T", abs(sL["T_kN_m"] + T_j) <= TOL,
        {"diagrama_T(L)": sL["T_kN_m"], "-T_j": _f6(-T_j)})
    add("extremo_L_My", abs(sL["My_kN_m"] + My_j) <= TOL,
        {"diagrama_My(L)": sL["My_kN_m"], "-My_j": _f6(-My_j)})
    add("extremo_L_Mz", abs(sL["Mz_kN_m"] + Mz_j) <= TOL,
        {"diagrama_Mz(L)": sL["Mz_kN_m"], "-Mz_j": _f6(-Mz_j)})

    dMy = sL["My_kN_m"] - s0["My_kN_m"]
    add("relacion_diferencial_dMy_dx_igual_Vz",
        abs(dMy / L - Vz_i) <= TOL,
        {"dMy/dx_kN": _f6(dMy / L), "Vz_kN": Vz_i})
    add("Vz_constante",
        all(s["Vz_kN"] == s0["Vz_kN"] for s in stations),
        {"Vz_kN": s0["Vz_kN"]})
    add("T_constante",
        all(s["T_kN_m"] == s0["T_kN_m"] for s in stations),
        {"T_kN_m": s0["T_kN_m"]})
    add("cero_N_Vy_Mz",
        all(s["N_kN"] == 0.0 and s["Vy_kN"] == 0.0 and s["Mz_kN_m"] == 0.0
            for s in stations),
        {"max_abs": max(max(abs(s["N_kN"]), abs(s["Vy_kN"]), abs(s["Mz_kN_m"]))
                        for s in stations)})

    if not all(c["ok"] for c in checks):
        malos = [c["check"] for c in checks if not c["ok"]]
        falla("comprobaciones fallidas: " + ", ".join(malos))

    paquete = {
        "formato": FORMATO,
        "version": VERSION,
        "edificio": EDIFICIO,
        "elementTag": TAG,
        "viewer_id": VIEWER_ID,
        "nivel": el.get("nivel"),
        "caso": CASO,
        "tipo_elemento": el.get("tipo"),
        "seccion": el.get("seccion"),
        "longitud_m": round(L, 6),
        "nodos": {"i": el.get("nodo_i"), "j": el.get("nodo_j")},
        "p_i_unity": [round(float(x), 6) for x in pi],
        "p_j_unity": [round(float(x), 6) for x in pj],
        "sin_cargas_interiores": True,
        "nota_sin_cargas_interiores": SIN_CARGAS_INTERIORES_NOTA,
        "fuente_metodologica": FUENTE_METODOLOGICA,
        "convencion_signos": CONVENCION,
        "unidades": UNIDADES,
        "indices_componentes": indices,
        "vector_localForce_12_caso_G": [_f6(x) for x in v],
        "n_stations": len(stations),
        "stations": stations,
        "comprobaciones": checks,
        "payload_fuente": {
            "archivo": PAYLOAD.name,
            "formato": p.get("formato"),
            "perfil": (p.get("fuente") or {}).get("perfil"),
            "n_elementos": p.get("n_elementos"),
            "fecha": fecha,
            "sha256": sha256_payload,
        },
        "advertencia_procedencia": ADVERTENCIA,
    }
    texto = _determinado(paquete) + "\n"

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(SALIDA.parent),
                               prefix=f".{SALIDA.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="\n", encoding="utf-8") as fh:
            fh.write(texto)
        os.replace(tmp, SALIDA)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    sha = hashlib.sha256(texto.encode("utf-8")).hexdigest().upper()
    print(f"OK  {SALIDA}")
    print(f"    sha256_payload = {sha256_payload}")
    print(f"    sha256_salida  = {sha}")
    print(f"    stations       = {len(stations)}  L = {round(L, 6)} m")
    print(f"    checks         = {len(checks)} OK")


if __name__ == "__main__":
    main()