"""Carga puntual seleccionable (Corr.2): resolve en OpenSeesPy un
`eleLoad('-type','-beamPoint')` sobre un elemento del perfil
MODELO_FE_COMPLETO_FUNCIONAL y emite el payload
    PL1_{EI|EII}_MODELO_FE_COMPLETO_FUNCIONAL.json
que el exportador funcional inyecta en el paquete del viewer como caso PL1.

Flujo:
  1. Se lee el estado de la UI (`lab_data/cargas_puntuales.json`,
     formato `cargas_puntuales_v1`): por edificio, un config
     { elemento_tag, elemento_viewer_id, nivel, activa, magnitud_kN,
       direccion_unity_unidad: [u, cota, v], xi }.
  2. Por edificio con config activa: se reconstruye el modelo (tags
     deterministicos del perfil), se proyecta la direccion a los ejes
     locales del elemento (convencion OpenSees Linear verificada:
     x' = unit(pj-pi); z' = proyeccion de vecxz; y' = z' x x'),
     se aplica `eleLoad beamPoint` y se corre OpenSees (analyze()==0).
  3. Se escribe el payload PL1 (layout identico al de los casos base:
     fuerzas_local/global_por_elemento, desplazamientos, reacciones) +
     bloque `carga_puntual` (configuracion resuelta para la UI).
  4. Se re-genera el paquete JSON del viewer CON PL1 (Caso B / reanalisis
     completo). El Caso A (cambio SOLO de magnitud) NO necesita re-resolver:
     la UI escala linealmente con EFElemento.FactorPL = P / P_resuelta.

Frame/ejes: Unity (X, Y, Z) = (u, cota, v). En el solver (u, v, cota).
Direccion solver = (dirUnity.u, dirUnity.v, dirUnity.cota).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import openseespy.opensees as ops

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "analisis_estructural" / "edificio_I" / "src"))
sys.path.insert(0, str(RAIZ / "entrega_03_cargas_sismo_capacidad"))

from src.unity_esfuerzos.exportar_esfuerzos_funcional_para_viewer import (  # noqa: E402
    OUT, PREFIJO, TOL_EQ, _metadata, generar, PL_CASO,
)

RAIZ = Path(__file__).resolve().parents[3]
ESTADO_UNITY = RAIZ / "viewer_unity" / "Assets" / "StreamingAssets" \
    / "lab_data" / "cargas_puntuales.json"


# --------------------------------------------------------------------------- #
# Estado de la UI
# --------------------------------------------------------------------------- #
def leer_estado_unity(ruta: Path | None = None) -> dict:
    path = Path(ruta) if ruta else ESTADO_UNITY
    if not path.exists():
        return {"formato": "cargas_puntuales_v1", "cargas": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("formato") != "cargas_puntuales_v1":
        raise ValueError("estado_invalido: se espera formato cargas_puntuales_v1")
    return data


def configs_activas(estado: dict) -> list[dict]:
    """Configs de carga activas (por edificio), ordenadas I, II."""
    cargas = estado.get("cargas") or []
    if isinstance(cargas, dict):
        cargas = list(cargas.values())
    out: list[dict] = []
    for c in cargas:
        if not isinstance(c, dict):
            continue
        edificio = str(c.get("edificio") or "")
        if edificio not in ("I", "II"):
            continue
        if not bool(c.get("activa")):
            continue
        if float(c.get("magnitud_kN") or 0.0) == 0.0:
            continue
        if int(c.get("elemento_tag") or -1) < 0:
            continue
        out.append(c)
    out.sort(key=lambda c: ("I" if c["edificio"] == "I" else "II"))
    return out


# --------------------------------------------------------------------------- #
# Direccion en el solver y ejes locales del elemento
# --------------------------------------------------------------------------- #
def direccion_solver_de_unity(dir_unity) -> list[float]:
    """Unity (X=u, Y=cota, Z=v) -> solver (u, v, cota) = (X, Z, Y)."""
    return [float(dir_unity[0]), float(dir_unity[2]), float(dir_unity[1])]


def _norm(v):
    n = (sum(x * x for x in v)) ** 0.5
    return n or 1e-12


def bases_locales(rec: dict):
    """Convencion OpenSees CrdTransf 'Linear' (verificada con analisis de
    control): x' = unit(pj-pi); z' = normalize(vecxz - (vecxz.x')x');
    y' = z' x x'. vecxz replica la regla del motor (marco._elem):
    componente cota != 0 -> (0,1,0); barra horizontal -> (0,0,1)."""
    du = float(rec["u_j"]) - float(rec["u_i"])
    dv = float(rec["v_j"]) - float(rec["v_i"])
    dz = float(rec["z_j"]) - float(rec["z_i"])
    L = _norm((du, dv, dz))
    x = (du / L, dv / L, dz / L)
    if abs(dz) > 1e-3 or (abs(du) < 1e-6 and abs(dv) < 1e-6):
        vec = (0.0, 1.0, 0.0)   # vertical: +v
    else:
        vec = (0.0, 0.0, 1.0)   # horizontal: +cota
    t = vec[0] * x[0] + vec[1] * x[1] + vec[2] * x[2]
    zp = (vec[0] - t * x[0], vec[1] - t * x[1], vec[2] - t * x[2])
    zn = _norm(zp)
    z = (zp[0] / zn, zp[1] / zn, zp[2] / zn)
    y = (z[1] * x[2] - z[2] * x[1],
         z[2] * x[0] - z[0] * x[2],
         z[0] * x[1] - z[1] * x[0])          # y = z x x
    return x, y, z


# --------------------------------------------------------------------------- #
# Resolucion OpenSees (eleLoad beamPoint)
# --------------------------------------------------------------------------- #
def resolver_carga_puntual(edificio: str, config: dict) -> dict:
    """corre el modelo del perfil con la carga puntual y devuelve el payload."""
    _, recs, _, marco = _metadata(edificio)
    tag = int(config["elemento_tag"])
    if tag not in recs:
        raise KeyError(f"PL1 {edificio}: tag {tag} no esta en el modelo del perfil")
    rec = recs[tag]
    P = float(config["magnitud_kN"])
    dir_solver = direccion_solver_de_unity(config["direccion_unity_unidad"])
    xi = max(0.0, min(1.0, float(config.get("xi") or 0.5)))

    x, y, z = bases_locales(rec)
    Px = (dir_solver[0] * x[0] + dir_solver[1] * x[1] + dir_solver[2] * x[2]) * P
    Py = (dir_solver[0] * y[0] + dir_solver[1] * y[1] + dir_solver[2] * y[2]) * P
    Pz = (dir_solver[0] * z[0] + dir_solver[1] * z[1] + dir_solver[2] * z[2]) * P
    P_global = [Px * x[k] + Py * y[k] + Pz * z[k] for k in range(3)]

    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.eleLoad('-ele', tag, '-type', '-beamPoint', Py, Pz, xi, Px)

    ops.system('BandGeneral')
    ops.numberer('Plain')
    ops.constraints('Transformation')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ok = ops.analyze(1)

    tipo, nivel = rec["tipo"], rec["nivel"]
    viewer_id = config.get("elemento_viewer_id")
    if ok != 0:
        return {
            "perfil": "MODELO_FE_COMPLETO_FUNCIONAL", "edificio": edificio,
            "caso": PL_CASO, "solucion_ok": False, "equilibrio_ok": False,
            "analyze_retcode": int(ok), "magnitud_kN": P, "xi": xi,
            "carga_puntual": {
                "elemento_tag": tag, "elemento_viewer_id": viewer_id,
                "elemento_tipo": tipo, "elemento_nivel": nivel,
                "direccion_solver_unidad": dir_solver,
                "direccion_unity_unidad": [float(v) for v in config["direccion_unity_unidad"]],
                "magnitud_kN": P, "P_global_kN": P_global, "unidad": "kN",
                "descripcion": "analyze()!=0: SIN resultados validos"},
        }

    ops.reactions()
    desplazamientos = {}
    for t in marco.nodes.values():
        try:
            desplazamientos[int(t)] = [ops.nodeDisp(int(t), i) for i in range(1, 7)]
        except Exception:
            desplazamientos[int(t)] = [ops.nodeDisp(int(t), i) for i in range(1, 4)] + [0, 0, 0]
    reacciones = {}
    for t in marco.nodes.values():
        try:
            rx = [ops.nodeReaction(int(t), i) for i in (1, 2, 3, 4, 5, 6)]
        except Exception:
            continue
        if any(abs(x) > 1e-9 for x in rx):
            reacciones[int(t)] = rx

    fuerzas = {"local": {}, "global": {}}
    for rec_e in marco.columnas + marco.vigas_elem + marco.muros_elem:
        tn = int(rec_e["tag"])
        try:
            fuerzas["local"][tn] = [float(x) for x in ops.eleResponse(tn, "localForce")]
            fuerzas["global"][tn] = [float(x) for x in ops.eleResponse(tn, "globalForce")]
        except Exception:
            continue

    R = [0.0] * 6
    for r in reacciones.values():
        for i in range(6):
            R[i] += r[i]
    residuo = max(abs(P_global[k] + R[k]) for k in range(3))
    escala = max(max(abs(x) for x in P_global), 1.0)
    equilibrio_ok = bool(residuo <= TOL_EQ * escala)

    payload = {
        "perfil": "MODELO_FE_COMPLETO_FUNCIONAL",
        "edificio": edificio, "caso": PL_CASO,
        "carga_puntual": {
            "descripcion": "eleLoad beamPoint sobre elemento del perfil; "
                           "Caso A = escala lineal por magnitud SIN reanalisis; "
                           "Caso B = este reanalisis (OpenSeesPy)",
            "unidad": "kN",
            "elemento_tag": tag, "elemento_viewer_id": viewer_id,
            "elemento_tipo": tipo, "elemento_nivel": nivel,
            "xi": round(xi, 6),
            "direccion_solver_unidad": [round(v, 6) for v in dir_solver],
            "direccion_unity_unidad": [round(float(v), 6)
                                       for v in config["direccion_unity_unidad"]],
            "magnitud_kN": round(P, 6),
            "P_global_kN": [round(float(v), 6) for v in P_global],
            "R_global_kN": [round(float(v), 6) for v in R[:3]],
        },
        "magnitud_kN": round(P, 6), "xi": round(xi, 6),
        "Pz_kN": round(float(P_global[2]), 6),
        "Rz_kN": round(float(R[2]), 6),
        "equilibrio_ok": bool(equilibrio_ok),
        "residuo_kN": round(float(residuo), 9),
        "solucion_ok": True,
        "reacciones": {str(int(t)): [round(float(x), 6) for x in r]
                       for t, r in reacciones.items()},
        "desplazamientos": {str(int(t)): [round(float(x), 8) for x in v]
                            for t, v in desplazamientos.items()},
        "fuerzas_local_por_elemento":
            {str(int(k)): [round(float(x), 6) for x in v]
             for k, v in fuerzas["local"].items()},
        "fuerzas_global_por_elemento":
            {str(int(k)): [round(float(x), 6) for x in v]
             for k, v in fuerzas["global"].items()},
    }
    return payload


def escribir_payload(edificio: str, payload: dict) -> Path:
    path = OUT / f"{PL_CASO}_{PREFIJO[edificio]}_MODELO_FE_COMPLETO_FUNCIONAL.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Orquestacion
# --------------------------------------------------------------------------- #
def correr(estado: dict | None = None, edificios: list[str] | None = None,
           escribir: bool = True) -> dict:
    """Reanaliza los edificios con config activa en el estado, escribe los
    payloads PL1 y re-genera los paquetes del viewer. Devuelve resumen."""
    estado = estado if estado is not None else leer_estado_unity()
    act = configs_activas(estado)
    resumen: dict = {"cargos_leidos": len(estado.get("cargas") or []),
                     "configs_activas": len(act), "por_edificio": {}, "ok": True}
    for config in act:
        edificio = config["edificio"]
        if edificios and edificio not in edificios:
            continue
        try:
            payload = resolver_carga_puntual(edificio, config)
            if escribir:
                escribir_payload(edificio, payload)
            (data, auditoria, _) = generar(edificio, escribir=escribir)
            ok = bool(payload.get("solucion_ok")) and bool(payload["equilibrio_ok"]) \
                and bool(auditoria["ok"])
            resumen["por_edificio"][edificio] = {
                "analisis_ok": bool(payload.get("solucion_ok")),
                "equilibrio_ok": bool(payload.get("equilibrio_ok")),
                "residuo_kN": payload.get("residuo_kN"),
                "auditoria_ok": bool(auditoria["ok"]),
                "checks": sum(1 for c in auditoria["checks"] if c["ok"]),
                "n_checks": len(auditoria["checks"]),
                "elementos": data["n_elementos"],
                "casos": data["casos"],
            }
            resumen["ok"] = resumen["ok"] and ok
            print(f"[{edificio}] PL1 {'OK' if ok else 'FALLO'}: "
                  f"P={payload.get('magnitud_kN')} kN, tag={config['elemento_tag']}, "
                  f"xi={payload.get('xi')}, residuo={payload.get('residuo_kN')}, "
                  f"auditoria {resumen['por_edificio'][edificio]['checks']}/"
                  f"{resumen['por_edificio'][edificio]['n_checks']}")
        except Exception as exc:
            import traceback
            traceback.print_exc()
            resumen["por_edificio"][edificio] = {"error": repr(exc)}
            resumen["ok"] = False
    return resumen


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv
    edificios = [a for a in args if a in ("I", "II")] or list(PREFIJO)
    if "--dry-run" in args:
        res = correr(edificios=edificios, escribir=False)
    else:
        res = correr(edificios=edificios)
    print(f"TOTAL: activas={res['configs_activas']}, ok={res['ok']}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))