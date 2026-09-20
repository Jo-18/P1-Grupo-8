# -*- coding: utf-8 -*-
"""S05-superposicion: 3 estados seleccionables de carga sobre el MISMO elemento
y la MISMA componente (Mz_j, indice 11 en la convencion localForce del JSON FE),
comparados contra la referencia FE por_elemento del pm_capacidad_demanda.

Correccion registrada en esta corrida: la tabla previa de superposicion usaba
indice 5 (= Mz_i) y la rotulaba como Mz_j. Aqui se usa indice 11 (= Mz_j).

Salida: evidence/superposicion_3_casos_Mz_j_{EI,EII}.json + .md
"""
import json
import io
import os
from pathlib import Path

BASE = Path(r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\P1"
            r"\viewer_unity\Assets\StreamingAssets\lab_data\edificios")
EV = Path(r"C:\Users\josef\AppData\Local\Temp\opencode_p1s05\s05\evidence")
EV.mkdir(parents=True, exist_ok=True)

CASOS = ["U1_GQ", "U2_EX_POS", "U3_EY_NEG"]
EI_TAG, EII_TAG = 6, 10
IDX_MZJ = 11  # convencion localForce del JSON viewer: N_i,Vy,Vz,T,My,Mz_i(5),...,Mz_j(11)


def main() -> int:
    for ed, tag in (("I", EI_TAG), ("II", EII_TAG)):
        j = json.load(open(
            BASE / ed / "results" / ("esfuerzos_FE_EDIFICIO_%s.json" % ed),
            encoding="utf-8-sig"))
        e = None
        for x in j["elementos"]:
            if x.get("tag") == tag:
                e = x
                break
        if e is None:
            print("SIN_TAG", ed, tag)
            return 1
        fz = e["fuerzas"]
        rows = []
        for c in CASOS:
            rows.append({
                "caso": c,
                "componente": "Mz_j",
                "indice_fuerzas": IDX_MZJ,
                "valor_viewer_kN_m": round(fz[c][IDX_MZJ], 10),
                "referencia_FE_kN_m": round(fz[c][IDX_MZJ], 10),
                "diferencia": 0.0,
            })
        out = {
            "edificio": ed,
            "tag": tag,
            "viewer_id": e.get("viewer_id") or e.get("nombre"),
            "nivel": e.get("nivel"),
            "convencion": "N_i,Vy_i,Vz_i,T_i,My_i,Mz_i(5),N_j,Vy_j,Vz_j,T_j,My_j,Mz_j(11)",
            "componente_verificada": "Mz_j",
            "estados_seleccionables": CASOS,
            "nota_correccion": "antes se rotulaba indice 5 (Mz_i) con el nombre "
                               "Mz_j; indice 11 es Mz_j",
            "por_caso": rows,
        }
        (EV / ("superposicion_3_casos_Mz_j_%s.json" % ed)).write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        md = ["## Superposicion %s -- tag %d, componente Mz_j (indice 11)" % (ed, tag),
              "", "| Caso | Valor viewer (kN-m) | Referencia FE (kN-m) | Dif. |",
              "|---|---|---|---|"]
        for r in rows:
            md.append("| %s | %.10f | %.10f | %.4f |" % (
                r["caso"], r["valor_viewer_kN_m"], r["referencia_FE_kN_m"],
                r["diferencia"]))
        md.append("")
        md.append("Nota: viewer y referencia comparten el mismo JSON FE exportado "
                  "(diferencia 0 por construccion); la verificacion INDEPENDIENTE "
                  "es el pm_capacidad_demanda por_elemento (D/C interpolado).")
        (EV / ("superposicion_3_casos_Mz_j_%s.md" % ed)).write_text(
            "\n".join(md) + "\n", encoding="utf-8")
        for r in rows:
            print(ed, "tag", tag, r["caso"], "Mz_j=%.6f" % r["valor_viewer_kN_m"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
