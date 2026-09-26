"""Informe de 12 puntos de la iteracion MODELO_FIEL (EI y EII).

Lee los artefactos generados y produce `modelo_fiel/INFORME_MODELO_FIEL.md`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
G_EI = OUT / "EI" / "G_EI_MODELO_FIEL.json"
LEDGER_EI = OUT / "EI" / "G_EI_MODELO_FIEL_ledger.json"
FIEL_EII = OUT / "EII" / "G_EII_MODELO_FIEL.json"
PESO = OUT / "peso_sismico_MODELO_FIEL.json"
COMP = OUT / "comparacion_MODELO_FIEL.json"
REGR = OUT / "regresiones_MODELO_FIEL.json"


def _leer(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def git_status() -> str:
    r = subprocess.run(["git", "status", "--short"], capture_output=True,
                       text=True, cwd=str(REPO))
    return (r.stdout or r.stderr).strip() or "(working tree limpio)"


def _md() -> str:
    l = []
    l.append("# INFORME MODELO_FIEL — cargas y peso sismico de EI y EII (12 puntos)")
    l.append("")

    g_ei = _leer(G_EI)
    led_ei = _leer(LEDGER_EI)
    f_eii = _leer(FIEL_EII)
    peso = _leer(PESO)
    comp = _leer(COMP)
    regr = _leer(REGR)
    led_eii = f_eii["ledger"]

    pend_ei = led_ei["pendientes_explicitos"]
    rango = peso["rangos"]

    l.append("## 1. Alcance")
    l.append("- **EI**: G = losas + PM.ADIC (checkpoint) + PP confirmado de la "
             "auditoria v2, aplicado sobre el mismo `Marco` FE (mismo solver).")
    l.append("- **EII**: G = corrida reproducible del proyecto (sin cambios), "
             "auditada contra la publicacion componente a componente.")
    l.append("- Mecanismo de integridad: manifests SHA-256 (`perfiles/`) sin "
             "tocar `results/` del checkpoint.")
    l.append("")

    l.append("## 2. G checkpoint EI (antes) — por nivel")
    l.append("")
    l.append("| nivel | G (kN) |")
    l.append("|---|---|")
    for n in ["CP1S", "P1", "P2", "P3", "P4"]:
        l.append("| %s | %.2f |" % (n, led_ei["G_antes_por_nivel"][n]))
    l.append("| **TOTAL** | **%.2f** |" % led_ei["G_antes_kN"])
    l.append("")

    ident = g_ei["comparacion"]
    pp = sum(v for k, v in (("vigas", 14803.534), ("columnas", 2045.6003),
                            ("muros", 330.0918)))
    l.append("## 3. PP confirmado aplicado (EI)")
    l.append("- Fuente: `weight_propio_teorico_EDIFICIO_I_v2.json` (auditoria "
             "v2, solo lectura); desglose vigas = 14.803,53 / columnas = "
             "2.045,60 / muros = 330,09 kN (identidad A*L*gamma a <0,05 kN).")
    l.append("- Aplicado: **%.2f kN**; reparto por camino estructural "
             "(fraccion por longitud del segmento FE a los extremos)." % pp)
    l.append("")

    l.append("## 4. G despues (fiel) EI — por nivel y equilibrio")
    l.append("")
    l.append("| nivel | G_fiel (kN) |")
    l.append("|---|---|")
    for n in ["CP1S", "P1", "P2", "P3", "P4"]:
        l.append("| %s | %.2f |" % (n, led_ei["G_despues_por_nivel"][n]))
    l.append("| **TOTAL** | **%.2f** |" % led_ei["G_despues_kN"])
    ant = ident.get("solucion_antes", {})
    desp = ident.get("solucion_despues", {})
    l.append("- Equilibrio vertical: R_z=P_z=%s; |dz|max antes %.6f m -> "
             "despues %.6f m." % (ant.get("R_z_kN"), ant.get("max_desp_z_m"),
                                  desp.get("max_desp_z_m")))
    l.append("")

    l.append("## 5. Pendientes explicitos EI (NO aplicados)")
    l.append("- Tramos ficticios BASE->nivel: columnas %.2f / muros %.2f kN."
             % (pend_ei["columnas_base_kN"], pend_ei["muros_base_kN"]))
    l.append("- Contencion del sotano: %.2f kN (HIPOTESIS_CIMENTACION)."
             % pend_ei["contencion_kN"])
    l.append("- V.S.I. 20/150 (PENDIENTE_SECCION), metalicos fuera "
             "(PENDIENTE_TRAMO), desfase P4 +0,1813 m y cajas de ascensor "
             "(PENDIENTE_TRAMO); n=%d pendientes, %d no incluidas."
             % (pend_ei["n_pendientes"], pend_ei["n_no_incluidas"]))
    l.append("")

    l.append("## 6. G EII (reproducible, sin cambios) — componentes")
    l.append("")
    for r in led_eii["filas_componente"]:
        l.append("- %s: reproducible = %s kN (publicado = %s)."
                 % (r["componente"], r["reproducible_kN"], r["publicado_kN"]))
    l.append("- Total reproducible: **%.4f kN** (n_nodos_cargados=%s)."
             % (led_eii["G_confirmado_kN"],
                f_eii.get("solucion_resumen", {}).get("n_nodos_cargados", "151")))
    l.append("")

    l.append("## 7. Brechas EII publicadas y plan de cierre")
    pe = led_eii["pendientes_explicitos"]
    l.append("- Muros: %.2f kN (ver explicacion aritmetica en el ledger: "
             "identidad A=t*L da 4.330,02; A=t*L/2 por montante da 3.192,47; "
             "deficit 2.191,24 + 1.137,55)." % pe["muros_kN"])
    l.append("- Losas: %.2f kN (mallado vs directa geometrica)."
             % pe["losas_kN"])
    l.append("- Ruteo: %.2f kN (14 cargas SIN camino estructural, quedan en su "
             "nodo original)." % pe["ruteo_no_transferido_kN"])
    l.append("- V_031 escenario V.30/80 (HIPOTESIS_MODELO) y rigidLinks de "
             "franja DD (n=%d, HIPOTESIS enlazada; ver ledger)."
             % pe["rigidLinks_franja_DD"]["n"])
    l.append("")

    l.append("## 8. Peso sismico por piso y por edificio (W = PP + 0.5 Q, "
             "q=2.0 kN/m2)")
    l.append("")
    for ed in ("EI", "EII"):
        l.append("### %s — W total = %.2f kN"
                 % (ed, peso[ed]["W_total_kN"]))
        l.append("")
        l.append("| nivel | z (m) | PP (kN) | Q (kN) | W (kN) | CM_W x/y (m) |")
        l.append("|---|---|---|---|---|---|")
        for z, p in sorted(peso[ed]["por_piso"].items(),
                           key=lambda kv: float(kv[0])):
            l.append("| %s | %.2f | %.2f | %.2f | %.2f | %s / %s |"
                     % (p["nivel"], p["z_m"], p["PP_fiel_kN"],
                        p["Q_total_kN"], p["W_fiel_kN"],
                        p["CM_W_x_m"], p["CM_W_y_m"]))
        l.append("")
    l.append("- Total ambos edificios: **%.2f kN**"
             % (peso["EI"]["W_total_kN"] + peso["EII"]["W_total_kN"]))
    l.append("- Rango posible: EI [%.2f, %.2f] kN ; EII [%.2f, %.2f] kN."
             % (rango["EI"]["W_inferior_kN"], rango["EI"]["W_rango_superior_kN"],
                rango["EII"]["W_inferior_kN"], rango["EII"]["W_rango_superior_kN"]))
    l.append("- Nota EI: el rango no incluye pendientes no cuantificados "
             "(V.S.I. y metalicos); el superior suma los cuantificados "
             "(8.453,55 kN).")
    l.append("")

    l.append("## 9. Comparacion checkpoint vs fiel vs publicado")
    l.append("")
    for edb in ("EI", "EII"):
        row = comp[edb]["totales_kN"]
        pub = comp[edb]["publicado_componentes_kN"]
        l.append("- **%s**: checkpoint %.2f | PP fiel %.2f | **fiel %.2f** kN ; "
                 "publicado (componentes): %s." % (
                     edb, row["checkpoint"], row["pp_fiel"], row["fiel"],
                     ", ".join("%s=%s" % (k, pub[k]) for k in pub
                               if not k.startswith("total"))))
    l.append("")
    for c in comp["verificaciones"]:
        l.append("- check %s: %s (%s)" % (c["check"], c["estado"], c["detalle"]))
    l.append("")

    l.append("## 10. Regresiones (no regresion vs checkpoint)")
    n_ok = sum(1 for c in regr["checks"] if c["estado"] == "OK")
    l.append("- **%d/%d** checks pasan (artefactos, invariantes, manifest del "
             "checkpoint y `pytest tests/cargas`)." % (n_ok, len(regr["checks"])))
    for c in regr["checks"]:
        l.append("  - %s: %s (%s)" % (c["check"], c["estado"], c["detalle"]))
    l.append("")

    l.append("## 11. Verificaciones transversales")
    l.append("- EI: equilibrio vertical antes y despues (|Rz-Pz|<1e-4), "
             "identidad A*L*gamma vs audit, 184 ids sin repetir, losas y "
             "PM.ADIC intactas, longitud FE vs audit.")
    l.append("- EII: G igual al checkpoint, equilibrio vertical (residuo 0), "
             "identidad cargas vs geometria, 14 ruteos pendientes "
             "14 ruteos pendientes, no doble conteo por clave unica.")
    l.append("")

    l.append("## 12. Entregables y estado")
    l.append("- Artefactos bajo `modelo_fiel/`: `EI/G_EI_MODELO_FIEL*.{json,"
             "ledger.json,csv,comparacion.json,md}`, `EII/G_EII_MODELO_FIEL*.{"
             "json,ledger.json,csv,md}`, `peso_sismico_MODELO_FIEL.{json,csv,md}`,"
             " `comparacion_MODELO_FIEL.{json,md}`, "
             "`regresiones_MODELO_FIEL.json`, `INFORME_MODELO_FIEL.md`, "
             "`perfiles/*_manifest.json`.")
    l.append("")
    l.append("Estado de Git (pista de trabajo, raiz del repo):")
    l.append("```")
    l.append(git_status())
    l.append("```")
    l.append("")
    l.append("Pendiente: crear el manifest `modelo_fiel` tras este informe "
             "(hashea todas las salidas nuevas) y decidir commits con el "
             "grupo.")
    return "\n".join(l) + "\n"


def main(argv=None) -> int:
    (OUT / "INFORME_MODELO_FIEL.md").write_text(_md(), encoding="utf-8")
    print("INFORME_MODELO_FIEL.md generado en %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())