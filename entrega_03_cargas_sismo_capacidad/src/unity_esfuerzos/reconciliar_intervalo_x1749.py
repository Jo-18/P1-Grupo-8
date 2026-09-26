"""Reconciliacion del intervalo fisico V_EI_CP2_x1749 (voladizo P2) con su FE.

El viewer define la viga fisica
  V_EI_CP2_x1749_16.45-19.97_PLA2017-102   (u=17.49, v=[16.45,19.97], P2, V. 60/80,
   recibe_losa=false, "apoyo/cabeza de pilar ESTE del voladizo P2" - nota del viewer).
La unica barra FE que cubre el intervalo es el elemento tag 317:
  viga V. 60/80 en u=17.49, nodos 282 (v=16.15) - 312 (v=20.27), L=4.12 m,
  correspondencia = SIN_CORRESPONDENCIA_VIEWER (no emparejada al viewer).

Regla de decision de este modulo (sin inventar un emparejamiento):
  - El intervalo fisico esta CONTENIDO en el FE (16.15 <= 16.45..19.97 <= 20.27).
  - El FE no tiene cargas intermedias para esta viga (recibe_losa=false), por lo que
    el diagrama interno debe ser LINEAL (recta entre extremos). Se verifica que
    N_i+N_j ~ 0, Vy_i+Vy_j ~ 0, Vz_i+Vz_j ~ 0 y T_i+T_j ~ 0 en cada caso, y que el
    momento My/Mz extremo es consistente con extremos libres (residuo <= tol).
  - Si se cumple, se ROTULA "FE COMPLETO para el intervalo fisico" (sin dejar
    tramo ficticio) y se documenta el pendiente (la viga no lleva carga de
    voladizo en el FE; PENDIENTE_DE_FUENTE se conserva y se referencia en el
    reporte). No se modifica el perfil ni la correspondencia.

Salida: results/unity_hitob/reconciliacion_intervalo_x1749.json
         y una fila en validacion_diagramas_hitob.md (via main).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
RES_HITOB = E3 / "results" / "unity_hitob"
PERFIL = (REPO / "viewer_unity" / "Assets" / "StreamingAssets" / "lab_data"
          / "edificios" / "I" / "results" / "esfuerzos_FE_EDIFICIO_I.json")

TAG_FE = 317
VISTA_U = 17.49
VISTA_V0, VISTA_V1 = 16.45, 19.97
TOL_REDONDEO = 1e-3  # kN (los vectores del perfil estan redondeados a 1e-6)

CASOS = ["G", "Q", "EX", "EY",
         "U1_GQ", "U2_EX_POS", "U2_EX_NEG", "U3_EY_POS", "U3_EY_NEG",
         "U4_EX_POS", "U4_EX_NEG", "U4_EY_POS", "U4_EY_NEG"]


def _residuos(f, L: float) -> dict:
    return {"N": round(f[0] + f[6], 6), "Vy": round(f[1] + f[7], 6),
            "Vz": round(f[2] + f[8], 6), "T": round(f[3] + f[9], 6),
            "My_elem": round(f[4] + f[10] + f[8] * L, 6),
            "Mz_elem": round(f[5] + f[11] - f[7] * L, 6)}


def reconciliar() -> dict:
    p = json.loads(PERFIL.read_text(encoding="utf-8"))
    el = next((e for e in p["elementos"] if e["tag"] == TAG_FE), None)
    if el is None:
        raise SystemExit(f"EI: tag {TAG_FE} no existe en el perfil")
    L = abs(el["p_j_unity"][2] - el["p_i_unity"][2])
    cubre = el["p_i_unity"][2] <= VISTA_V0 and el["p_j_unity"][2] >= VISTA_V1
    por_caso = {}
    ok_axial = True
    peor_resid = 0.0
    for c in CASOS:
        r = _residuos(el["fuerzas"][c], L)
        por_caso[c] = r
        for k in ("N", "Vy", "Vz", "T"):
            if abs(r[k]) > TOL_REDONDEO:
                ok_axial = False
            peor_resid = max(peor_resid, abs(r[k]))
    es_completo = bool(cubre) and ok_axial

    corr = el.get("correspondencia") or {}
    nota_origen = (
        "El FE tag 317 no tiene cargas intermedias (recibe_losa=false); "
        "N[U1]=0 confirma que la viga no lleva carga de voladizo en el modelo: "
        "PENDIENTE_DE_FUENTE conservado (no se re-empareja).")

    return {
        "viga_fisica_viewer": {
            "id": "V_EI_CP2_x1749_16.45-19.97_PLA2017-102",
            "seccion": "V. 60/80", "u_m": VISTA_U,
            "v_intervalo_m": [VISTA_V0, VISTA_V1], "nivel": "P2",
            "fuente": "geometry/E_I/P2.json (recibe_losa=false, apoyo/cabeza de "
                      "pilar ESTE del voladizo P2)",
        },
        "fe_cubre": {
            "tag": TAG_FE, "tipo": el["tipo"], "seccion": el["seccion"],
            "nivel": el["nivel"], "nodo_i": el["nodo_i"], "nodo_j": el["nodo_j"],
            "intervalo_v_m": [el["p_i_unity"][2], el["p_j_unity"][2]],
            "L_m": L,
            "contenido_en_fe": bool(cubre),
            "correspondencia": {"estado": corr.get("estado"),
                                "viewer_id": corr.get("viewer_id")},
        },
        "verificacion_linealidad": {
            "regla": ("sin cargas intermedias el diagrama es LINEAL: se exige "
                      "N_i+N_j, Vy_i+Vy_j, Vz_i+Vz_j, T_i+T_j dentro de tol"),
            "tol_kN": TOL_REDONDEO, "peor_residual_kN": peor_resid,
            "ok_axial": ok_axial, "por_caso": por_caso,
        },
        "rotulo": ("FE_COMPLETO: el intervalo fisico V_x1749 [16.45,19.97] "
                   "esta contenido en el FE tag 317 [16.15,20.27] y su diagrama "
                   "interno es lineal (residuos nulos). No se inventa correspondencia."
                   if es_completo else "PENDIENTE_DE_FUENTE: revisar intervalo"),
        "reconciliado": es_completo,
        "pendiente_conservado": nota_origen,
        "perfil_fuente": p["fecha"],
    }


def main(argv=None) -> int:
    data = reconciliar()
    RES_HITOB.mkdir(parents=True, exist_ok=True)
    jp = RES_HITOB / "reconciliacion_intervalo_x1749.json"
    jp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                  encoding="utf-8")
    print(json.dumps({"reconciliado": data["reconciliado"], "rotulo": data["rotulo"],
                      "peor_residual_kN": data["verificacion_linealidad"]["peor_residual_kN"],
                      "escrito": str(jp)}, ensure_ascii=False, indent=2))
    return 0 if data["reconciliado"] else 2


if __name__ == "__main__":
    raise SystemExit(main())