"""Peso sismico, centro de masa y distribucion de fuerza lateral por nivel.

Metodologia pseudoestatica (consigna del profesor, ejemplo):
  Wi = PPi + fraccion_Q * Qi   (peso sismico por piso)
  mi = Wi / g                   (masa)
  Fi = a * mi = coef * Wi       (fuerza lateral; a = coef*g se simplifica)

Distribucion nodal: fn = Fi * wn / Wi (proporcional al peso tributario del nodo).

El calculo usa los pesos distribuidos (tributarios) del modelo FE, NO el centro
geometrico automatico. La resultante de fn queda exactamente en el CM y el momento
accidental es exactamente cero por construccion.

El PP pendiente (diferencia de muros EII: 3335 kN) se muestra como nota pero NO
se suma al peso sismico (no se calibra).

Unidades: kN, m.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONFIG_SISMO = REPO / "entrega_03_cargas_sismo_capacidad" / "config" / "sismo.json"


def leer_config_sismo() -> dict:
    return json.loads(CONFIG_SISMO.read_text(encoding="utf-8"))


def _agrupar_nodos_por_nivel(key_of_tag: dict, tol_z: float = 0.05) -> list[dict]:
    """Agrupa nodos por coordenada z (tolerancia), retorna lista de {z, tags}."""
    z_vals = sorted(set(round(k[2] / tol_z) * tol_z for k in key_of_tag.values()))
    floors = []
    for z in z_vals:
        tags = [t for t, k in key_of_tag.items() if abs(k[2] - z) < tol_z]
        if tags:
            floors.append({"z": z, "tags": sorted(tags)})
    return floors


def peso_nodal_vertical(cargas: dict, tags: list) -> float:
    """Suma del componente vertical (indice 2, negativo = hacia abajo) de las cargas
    nodales para los tags dados. Retorna el peso total (positivo) en kN."""
    return sum(abs(cargas.get(t, [0, 0, 0, 0, 0, 0])[2]) for t in tags)


def peso_sismico_ledger(cargas_G: dict | list[dict], cargas_Q: dict | list[dict],
                        key_of_tag: dict, nivel_cota: dict | None = None,
                        cfg_sismo: dict | None = None,
                        PP_pendiente_global_kN: float = 0.0,
                        PP_pendiente_nota: str = "") -> dict:
    """Calcula el ledger de peso sismico por nivel, centro de masa, y fuerzas
    laterales.

    Parameters
    ----------
    cargas_G : dict o list[dict]
        Cargas nodales del caso G. Si es dict plano {tag: [6-vec]}, se usa
        directamente. Si es list[dict], es por nivel [{tag: [6-vec]}, ...] y
        se aplana.
    cargas_Q : dict o list[dict]
        Cargas nodales del caso Q (misma estructura).
    key_of_tag : dict
        {tag: (x, y, z)} coordenadas de nodos.
    nivel_cota : dict | None
        {cod: z_cota} mapping nivel -> cota z. Si None, se agrupa por z.
    cfg_sismo : dict | None
        Config sismo. Si None, lee config/sismo.json.
    PP_pendiente_global_kN : float
        PP no incluido en el modelo (visible pero excluido del peso sismico).
    PP_pendiente_nota : str
        Nota sobre el PP pendiente.

    Returns
    -------
    dict con ledger, CM por nivel, fuerzas, y verificaciones.
    """
    cfg = cfg_sismo or leer_config_sismo()
    mp = cfg["metodo_pseudoestatico"]
    coef_a = float(mp["coeficiente_sismico_a"])
    fraccion_Q = float(mp["fraccion_Q_gravitacional"])
    g = float(mp["g_gravedad_m_s2"])

    # Aplana cargas por nivel si vienen como lista
    if isinstance(cargas_G, list):
        G_flat = {}
        for car in cargas_G:
            for t, f in car.items():
                G_flat.setdefault(int(t), [0.0]*6)
                for i in range(6):
                    G_flat[int(t)][i] += f[i]
        cargas_G = G_flat
    if isinstance(cargas_Q, list):
        Q_flat = {}
        for car in cargas_Q:
            for t, f in car.items():
                Q_flat.setdefault(int(t), [0.0]*6)
                for i in range(6):
                    Q_flat[int(t)][i] += f[i]
        cargas_Q = Q_flat

    # Agrupa nodos por nivel
    floors = _agrupar_nodos_por_nivel(key_of_tag)

    ledger = []
    F_total = 0.0
    W_total = 0.0
    PP_total_incluido = 0.0
    Q_total = 0.0

    for fl in floors:
        z = fl["z"]
        tags = fl["tags"]

        PP_nivel = peso_nodal_vertical(cargas_G, tags)
        Q_nivel = peso_nodal_vertical(cargas_Q, tags)
        W_nivel = PP_nivel + fraccion_Q * Q_nivel
        m_nivel = W_nivel / g
        F_nivel = coef_a * W_nivel

        # Centro de masa por pesos distribuidos
        Wx = sum(abs(cargas_G.get(t, [0,0,0,0,0,0])[2]
                       + fraccion_Q * cargas_Q.get(t, [0,0,0,0,0,0])[2])
                  * key_of_tag[t][0] for t in tags)
        Wy = sum(abs(cargas_G.get(t, [0,0,0,0,0,0])[2]
                       + fraccion_Q * cargas_Q.get(t, [0,0,0,0,0,0])[2])
                  * key_of_tag[t][1] for t in tags)
        X_cm = Wx / W_nivel if W_nivel > 0 else 0.0
        Y_cm = Wy / W_nivel if W_nivel > 0 else 0.0

        ledger.append({
            "z_m": round(z, 4),
            "n_nodos": len(tags),
            "PP_incluido_kN": round(PP_nivel, 4),
            "Q_total_kN": round(Q_nivel, 4),
            "fraccion_Q": fraccion_Q,
            "fr_Q_kN": round(fraccion_Q * Q_nivel, 4),
            "W_sismico_kN": round(W_nivel, 4),
            "masa_kN_s2_m": round(m_nivel, 4),
            "F_lateral_kN": round(F_nivel, 6),
            "X_cm_m": round(X_cm, 6),
            "Y_cm_m": round(Y_cm, 6),
        })

        F_total += F_nivel
        W_total += W_nivel
        PP_total_incluido += PP_nivel
        Q_total += Q_nivel

    # Verificaciones
    verificaciones = {
        "W_total_sismico_kN": round(W_total, 4),
        "F_total_lateral_kN": round(F_total, 4),
        "coeficiente_sismico_a": coef_a,
        "fraccion_Q": fraccion_Q,
        "g_m_s2": g,
        "PP_total_incluido_kN": round(PP_total_incluido, 4),
        "PP_pendiente_global_kN": PP_pendiente_global_kN,
        "PP_pendiente_nota": PP_pendiente_nota,
        "Q_total_kN": round(Q_total, 4),
    }

    return {
        "metodo": "pseudoestatico_ejemplo_consigna",
        "clasificacion": mp["clasificacion"],
        "ledger_por_nivel": ledger,
        "resumen": verificaciones,
    }


def generar_cargas_sismicas_directas(
        cargas_G: dict, cargas_Q: dict, key_of_tag: dict,
        direccion: str = "X",
        cfg_sismo: dict | None = None) -> dict:
    """Version directa: genera cargas nodales sísmicas sin pasar por el ledger.

    Calcula el peso tributario por nodo, CM por nivel, y distribuye la fuerza
    lateral proporcionalmente. Retorna las cargas nodales y verificaciones.

    Parameters
    ----------
    cargas_G : dict {tag: [6-vec]}
        Cargas nodales del caso G (plano).
    cargas_Q : dict {tag: [6-vec]}
        Cargas nodales del caso Q (plano).
    key_of_tag : dict {tag: (x, y, z)}
    direccion : str "X" o "Y"
    cfg_sismo : dict | None

    Returns
    -------
    dict con cargas_nodales, ledger_por_nivel, verificaciones.
    """
    cfg = cfg_sismo or leer_config_sismo()
    mp = cfg["metodo_pseudoestatico"]
    coef_a = float(mp["coeficiente_sismico_a"])
    fraccion_Q = float(mp["fraccion_Q_gravitacional"])
    g = float(mp["g_gravedad_m_s2"])

    if direccion not in ("X", "Y"):
        raise ValueError("direccion debe ser 'X' o 'Y'")

    floors = _agrupar_nodos_por_nivel(key_of_tag)
    idx = 0 if direccion == "X" else 1  # indice de la componente horizontal

    cargas_sismicas = {}
    ledger = []
    F_total_aplicado = 0.0
    W_total = 0.0

    for fl in floors:
        tags = fl["tags"]
        z = fl["z"]

        # Peso tributario por nodo: wn = |Gz| + fraccion_Q * |Qz|
        pesos_nodo = {}
        for t in tags:
            wz = abs(cargas_G.get(t, [0,0,0,0,0,0])[2]
                      + fraccion_Q * cargas_Q.get(t, [0,0,0,0,0,0])[2])
            pesos_nodo[t] = wz

        W_nivel = sum(pesos_nodo.values())
        m_nivel = W_nivel / g
        F_nivel = coef_a * W_nivel

        # Centro de masa
        if W_nivel > 0:
            X_cm = sum(pesos_nodo[t] * key_of_tag[t][0] for t in tags) / W_nivel
            Y_cm = sum(pesos_nodo[t] * key_of_tag[t][1] for t in tags) / W_nivel
        else:
            X_cm = Y_cm = 0.0

        # Distribucion proporcional
        F_aplicado = 0.0
        Mz_acc = 0.0  # momento accidental respecto al CM
        for t in tags:
            f_n = F_nivel * pesos_nodo[t] / W_nivel if W_nivel > 0 else 0.0
            vec = [0.0] * 6
            vec[idx] = f_n
            cargas_sismicas[t] = vec
            F_aplicado += f_n
            x, y, _ = key_of_tag[t]
            # Momento accidental: fy*(x-Xcm) - fx*(y-Ycm) para momento en z
            # Con solo fx: Mz = -fx*(y-Ycm)
            if direccion == "X":
                Mz_acc += -f_n * (y - Y_cm)
            else:
                Mz_acc += f_n * (x - X_cm)

        PP_nivel = sum(abs(cargas_G.get(t, [0,0,0,0,0,0])[2]) for t in tags)
        Q_nivel = sum(abs(cargas_Q.get(t, [0,0,0,0,0,0])[2]) for t in tags)

        ledger.append({
            "z_m": round(z, 4),
            "n_nodos": len(tags),
            "PP_incluido_kN": round(PP_nivel, 4),
            "Q_total_kN": round(Q_nivel, 4),
            "W_sismico_kN": round(W_nivel, 4),
            "masa_kN_s2_m": round(m_nivel, 4),
            "F_lateral_kN": round(F_nivel, 6),
            "F_aplicada_kN": round(F_aplicado, 6),
            "X_cm_m": round(X_cm, 6),
            "Y_cm_m": round(Y_cm, 6),
            "momento_accidental_kN_m": round(Mz_acc, 10),
        })

        F_total_aplicado += F_aplicado
        W_total += W_nivel

    # Verificaciones globales
    verificaciones = {
        "direccion": direccion,
        "W_total_sismico_kN": round(W_total, 4),
        "F_total_esperado_kN": round(coef_a * W_total, 6),
        "F_total_aplicada_kN": round(F_total_aplicado, 6),
        "diferencia_F_kN": round(abs(F_total_aplicado - coef_a * W_total), 10),
        "coeficiente_a": coef_a,
        "fraccion_Q": fraccion_Q,
        "g_m_s2": g,
        "momento_accidental_total_kN_m": round(
            sum(fl["momento_accidental_kN_m"] for fl in ledger), 10),
    }

    return {
        "direccion": direccion,
        "clasificacion": mp["clasificacion"],
        "cargas_nodales": cargas_sismicas,
        "ledger_por_nivel": ledger,
        "verificaciones": verificaciones,
    }
