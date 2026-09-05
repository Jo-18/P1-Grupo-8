"""Resolver estatico lineal del marco con OpenSeesPy + extraccion de resultados.

Norma (directiva del usuario):
  - El exito del analisis se define SOLO por analyze() == 0.
  - Las contribuciones de carga se ACUMULAN por nodo (un mismo nodo puede recibir
    cargas de varias losas); NO se descartan por repetir el tag.
  - Los desplazamientos/reacciones/fuerzas solo se publican como resultados validos
    si analyze() == 0; en caso de fallo se conserva el diagnostico (ecuacion singular,
    si es localizable por OpenSees) y NO se devuelven respuestas como solucion.
  - Se extraen las fuerzas reales por elemento (local y global, 12 por extremo).
"""

from __future__ import annotations

import openseespy.opensees as ops


def _handle_num(ops, tag, ndm=3):
    """Resiliente: nodeDisp/nodeReaction de 6 DOFs."""
    try:
        return [ops.nodeDisp(tag, i) for i in range(1, 7)]
    except Exception:
        return [ops.nodeDisp(tag, i) for i in range(1, ndm + 1)] + [0, 0, 0]


def resolver(marco, cargas_nodales_por_nivel: dict, load_factor=1.0):
    """cargas_nodales_por_nivel: {nivel: {tag: [fx,fy,fz,mx,my,mz]}} (kN).

    Devuelve dict con `ok` (bool, exito == analyze()==0), y, solo si ok, los
    campos de resultado validos; si no, mantiene diagnostico y sin-respuesta.
    """
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)

    # ACUMULAR todas las contribuciones por nodo (sin descartar por tag repetido).
    F_por_nodo = {}
    for nivel, cargas in cargas_nodales_por_nivel.items():
        for tag, f in cargas.items():
            tagi = int(tag)
            acc = F_por_nodo.setdefault(tagi, [0.0] * 6)
            acc[0] += f[0] * load_factor
            acc[1] += f[1] * load_factor
            acc[2] += f[2] * load_factor
            acc[3] += f[3] * load_factor
            acc[4] += f[4] * load_factor
            acc[5] += f[5] * load_factor

    F_total = [0.0] * 6
    for tagi, ff in F_por_nodo.items():
        ops.load(tagi, *ff)
        for i in range(6):
            F_total[i] += ff[i]

    # Se usa BandGeneral (mas robusto ante pivotes nulos) en lugar de BandSPD.
    ops.system('BandGeneral')
    ops.numberer('Plain')
    ops.constraints('Transformation')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')

    singular_info = None
    try:
        ok = ops.analyze(1)
    except Exception as exc:            # OpenSeesPy sube excepcion al factorizar
        ok = -1
        singular_info = {"tipo": "excepcion", "mensaje": repr(exc)}

    resultado = {
        "ok": bool(ok == 0),
        "success": bool(ok == 0),
        "analyze_retcode": int(ok),
        "F_total_kN": F_total,
        "n_nodos_cargados": len(F_por_nodo),
        "carga_total_apor_momento": None,
    }

    if ok != 0:
        resultado["singular_info"] = singular_info
        resultado["estado"] = "FALLO"
        resultado["diagnostico"] = (
            "analyze != 0: el ensamblaje es singular (mecanismo). NO se publican "
            "desplazamientos/reacciones/esfuerzos como solucion valida."
        )
        return resultado

    # --- exito: extraer respuestas reales ---
    ops.reactions()

    desplazamientos = {}
    for tag in marco.nodes.values():
        desplazamientos[int(tag)] = _handle_num(ops, int(tag))

    reacciones = {}
    for tag in marco.nodes.values():
        try:
            rx = [ops.nodeReaction(int(tag), i) for i in (1, 2, 3, 4, 5, 6)]
        except Exception:
            continue
        if any(abs(x) > 1e-9 for x in rx):
            reacciones[int(tag)] = rx

    # Fuerzas reales por elemento: local (12) y global (12) desde eleResponse.
    fuerzas = {"local": {}, "global": {}}
    elem_records = marco.columnas + marco.vigas_elem + marco.muros_elem
    for rec in elem_records:
        tagn = int(rec["tag"])
        try:
            loc = [float(x) for x in ops.eleResponse(tagn, "localForce")]
            glo = [float(x) for x in ops.eleResponse(tagn, "globalForce")]
        except Exception:
            continue
        fuerzas["local"][tagn] = loc
        fuerzas["global"][tagn] = glo

    resultado.update({
        "estado": "OK",
        "desplazamientos": desplazamientos,
        "reacciones": reacciones,
        "n_reacciones": len(reacciones),
        "fuerzas": fuerzas,
    })
    return resultado
