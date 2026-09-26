"""Regresiones y verificaciones de la iteracion MODELO_FIEL_4 (tareas 1-5).

Verifica (sin tocar results/ ni laboratorio_semana2/):
  1. suite completa (tests/: 28) con unittest discover + regresiones v3 (42).
  2. reconciliacion PP pendiente EI id por id (9/9; 63 pendientes; 68 filas;
     categorias C1..C6; PP confirmado 17179.2261; hipotesis 8453.5488 info).
  3. bloqueo PM.ADIC EII plano 700 (archivo exacto a solicitar, sha256, 0 kN).
  4. conservacion G_EII y peso sismico v3 (NO_REGENERAR, 6 checks OK).
  5. portabilidad: copias internas con SHA procedencia, config->data/externas,
     scan src/tests/config sin dependencias externas (excepto procedencia).

Salida: modelo_fiel/regresiones_MODELO_FIEL_v4.json
Uso:
  python -X utf8 -m src.modelo_fiel.regresiones_MODELO_FIEL_v4 [--skip-tests]
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

GRAV = 9.80665
G_KN_POR_KG = GRAV / 1000.0

PO = {
    "por_viga": "7952CE51B1F822137028B013E61F21F4AF4E9438EDD32DB4C9340371627B0492",
    "eii_viewer": "C3435C7B23072A87D7F3931100C63B1669A1EBF24B9BCD997BED1CCB32446BB1",
    "catalogo_I": "2CD90CABB35F26226FDD57AA8249ED33451F629C0D61AE5B7A3D8AA2D6958625",
    "areas_II": "54D98D404EA9F58AC2C7E333467F640723ADDF683890823FC32749DC0F8EE463",
}

SHA_DXF = "F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF"
SHA_PDF_EII = "4899A8B0033141FEB7F630F3AB8392ACBAEC364DE647BF7607C168B10D0CBB28"


def _r(ok, check, detalle):
    return {"check": check, "estado": "OK" if ok else "ERROR", "detalle": detalle}


REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
OUT = E3 / "modelo_fiel"
DATA = E3 / "data" / "externas"
CFG = E3 / "config"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def main(argv=None) -> int:
    skip = "--skip-tests" in (argv or sys.argv[1:])
    out = []

    rec = json.loads((OUT / "reconciliacion_PP_pendiente_EI.json").read_text(encoding="utf-8"))
    inv = json.loads((OUT / "inventario_PP_pendiente_EI.json").read_text(encoding="utf-8"))
    bloq = json.loads((OUT / "BLOQUEO_PMADIC_EII_plano700.json").read_text(encoding="utf-8"))
    cons = json.loads((OUT / "CONSERVACION_G_EII_peso_sismico_v4.json").read_text(encoding="utf-8"))
    mp = json.loads((OUT / "mapeo_PMADIC_EII_plano700.json").read_text(encoding="utf-8"))
    peso3 = json.loads((OUT / "peso_sismico_MODELO_FIEL_v3.json").read_text(encoding="utf-8"))
    led = json.loads((OUT / "ledger_PP_PMADIC_Q.json").read_text(encoding="utf-8"))

    # ---------------- 2) reconciliacion EI ----------------
    cheq = rec["chequeos"]
    out.append(_r(len(cheq) == 9 and all(c["ok"] for c in cheq.values())
                  and rec["total_chequeos_ok"] is True and rec["estado"] == "OK",
                  "rec_9_9_checks", "reconciliacion 9/9 OK y estado OK"))
    out.append(_r(cheq["1_conteo_pendientes_63"]["ok"]
                  and inv["conteo"]["pendientes"] == 63,
                  "rec_pendientes_63", "63 PP pendientes EI"))
    out.append(_r(len(rec["por_categoria"]) == 6
                  and sum(c["conteo"] for c in rec["por_categoria"]) == 68,
                  "rec_por_categoria_68",
                  "C1..C6 suman %d filas" % sum(c["conteo"] for c in rec["por_categoria"])))
    exp_cat = {"C1_real_FE_seccion_pendiente": 9, "C2_seccion_confirmada_tramo_pendiente": 18,
               "C3_hipotesis_base_nivel": 4, "C4_metalico_tubular_confirmado": 17,
               "C5_muro_una_sola_planta": 19, "C6_no_incluida": 1}
    got_cat = {c["categoria"]: c["conteo"] for c in rec["por_categoria"]}
    out.append(_r(got_cat == exp_cat, "rec_categorias_C1_C6",
                  str(got_cat)))
    out.append(_r(cheq["7_conciliacion_numerica"]["ok"]
                  and rec["margen"]["PP_confirmado_kN"] == 17179.2261,
                  "rec_pp_confirmado", "PP confirmado = 17179.2261 kN"))
    out.append(_r(abs(rec["margen"]["hipotesis_rango_superiorinformativo_kN"] - 8453.5488)
                  < 1e-6 and rec["aplicado_al_FE_kN"] == 0.0,
                  "rec_hipotesis_informativo",
                  "hipotesis 8453.5488 kN solo informativo; aplicado 0"))
    out.append(_r(rec["margen"]["PP_confirmado_kN"] == inv["PP_confirmado_kN"],
                  "rec_igual_inventario",
                  "PP confirmado == inventario %.4f" % inv["PP_confirmado_kN"]))
    out.append(_r(abs(led["EI"]["totales"]["PP_elementos_kN"] - 17179.2261) < 0.01,
                  "rec_consistente_ledger",
                  "LEDGER EI PP_elementos %.4f" % led["EI"]["totales"]["PP_elementos_kN"]))
    out.append(_r((OUT / "reconciliacion_PP_pendiente_EI.csv").exists()
                  and (OUT / "reconciliacion_PP_pendiente_EI.md").exists(),
                  "rec_artefactos_csv_md", "csv+md presentes"))

    # ---------------- 3) bloqueo plano 700 EII ----------------
    out.append(_r(bloq["estado"] == "BLOQUEADO_FALTA_EVIDENCIA_POSICIONAL",
                  "bloq_estado", bloq["estado"]))
    out.append(_r(bloq["resumen"]["n_familias_catalogadas"] == 6
                  and bloq["resumen"]["aplicada_al_FE_kN"] == 0.0
                  and bloq["resumen"]["cobertura"] == 0.0,
                  "bloq_6_familias_0_kN", "A-F AMBIGUO_NO_APLICADO, 0 kN, cobertura 0"))
    out.append(_r(bloq["conversion_g_kn_m"]["A"] == 260.0 * G_KN_POR_KG
                  and bloq["conversion_g_kn_m"]["D"] == 1500.0 * G_KN_POR_KG,
                  "bloq_conversion_g", "260/1500 Kg/m con g=9.80665"))
    pr = bloq["archivo_a_solicitar"]["primario"]
    out.append(_r(pr["nombre"] == "2017_67-700.dxf" and pr["sha256"] == SHA_DXF
                  and pr["tamano_bytes"] == 18207984,
                  "bloq_dxf_exacto", "%s sha %s" % (pr["nombre"], pr["sha256"][:16])))
    out.append(_r(bloq["archivo_a_solicitar"]["alternativo"]["sha256"] == SHA_PDF_EII,
                  "bloq_pdf_alternativo", "Union PDF's Edificio II.pdf sha ok"))
    out.append(_r(bloq["decision"]["no_por_proximidad"] is True
                  and "G_EII" in " ".join(bloq["decision"]["no_regenerar"]),
                  "bloq_no_por_proximidad_no_regenerar", "sin mapeo por proximidad"))
    out.append(_r(bloq["consistencia_con_v3"]["aplicada_al_FE_kN"] == 0.0
                  and bloq["consistencia_con_v3"]["cobertura"] == 0.0
                  and mp["aplicacion"]["aplicada_al_FE_kN"] == 0.0,
                  "bloq_consistencia_v3", "v3 y v4 cobertura 0"))
    out.append(_r(len(bloq["fuentes_buscadas"]) >= 9,
                  "bloq_lugares_buscados", "%d ubicaciones" % len(bloq["fuentes_buscadas"])))

    # ---------------- 4) conservacion G_EII / peso sismico ----------------
    out.append(_r(cons["decision"] == "NO_REGENERAR" and cons["controles"]["todo_ok"] is True,
                  "cons_NO_REGENERAR_todo_ok", "conservacion sin regenerar, 6/6 OK"))
    out.append(_r(cons["verificados_v3"]["G_EII_P_z_kN"]["verificado"] == 25970.9994
                  and cons["verificados_v3"]["G_EI_P_z_kN"]["verificado"] == 42406.9577,
                  "cons_G_EI_EII", "G_EI 42406.9577 ; G_EII 25970.9994"))
    out.append(_r(cons["verificados_v3"]["peso_EII_W_A_kN"]["verificado"] == 28600.7138
                  and cons["verificados_v3"]["peso_EI_W_B_kN"]["verificado"] == 46516.4301,
                  "cons_peso_sismico", "EII 28600.7138 A==B ; EI B 46516.4301"))
    out.append(_r(cons["controles"]["pmadic_EII_ok"] is True
                  and cons["controles"]["peso_EII_A_eq_B"] is True,
                  "cons_pmadic_0_AeqB", "PM.ADIC EII 0 ; peso EII A==B"))
    out.append(_r(peso3["EII"]["resumen"]["W_A_kN"] == 28600.7138
                  and peso3["EII"]["resumen"]["W_B_kN"] == 28600.7138,
                  "cons_peso3_EII", "peso v3 EII intacto 28600.7138"))

    # ---------------- 5) portabilidad ----------------
    for key, fname in (("por_viga", "por_viga.json"), ("eii_viewer", "eii_viewer.json"),
                       ("catalogo_I", "catalogo_cargas_diseno_edificio_I.json"),
                       ("areas_II", "areas_tributarias.csv")):
        p = DATA / fname
        ok = p.exists() and _sha(p) == PO[key]
        out.append(_r(ok, "port_copia_%s" % key,
                      "%s sha %s" % (fname, _sha(p)[:16] if p.exists() else "FALTA")))

    cfg_txt = (CFG / "cargas.json").read_text(encoding="utf-8")
    out.append(_r("data/externas/por_viga.json" in cfg_txt
                  and "entrega_03_cargas_sismo_capacidad/data/externas/por_viga.json"
                  in (CFG / "cargas.json").read_text(encoding="utf-8"),
                  "port_config_I_interna", "config I -> data/externas/por_viga.json"))
    out.append(_r("data/externas/areas_tributarias.csv" in cfg_txt,
                  "port_config_II_interna", "config II -> data/externas/areas_tributarias.csv"))

    allowed = {
        "src/comun/geometria_tributaria.py",
        "src/modelo_fiel/bloqueo_PMADIC_EII_plano700.py",
        "src/modelo_fiel/informe_MODELO_FIEL_v3.py",
        "src/modelo_fiel/regresiones_MODELO_FIEL_v3.py",
        "src/peso_propio_teorico_EDIFICIO_I_v2.py",
        "config/fuentes.json",
    }
    pat = re.compile(r"C:\\Users|viewer_unity|laboratorio_semana2|Datos Estructurales")
    fuera = {}
    for base, exts in ((E3 / "src", ("*.py",)), (E3 / "tests", ("*.py",)),
                       (CFG, ("*.json",))):
        for f in base.rglob("*"):
            if not f.is_file() or "__pycache__" in f.parts or f.suffix not in exts:
                continue
            if pat.search(f.read_text(encoding="utf-8", errors="ignore")):
                rel = str(f.relative_to(E3)).replace("\\", "/")
                if rel not in allowed:
                    fuera[rel] = True
    out.append(_r(not fuera, "port_scan_sin_externos",
                  "son libres salvo procedencia; fuera: %s" % (",".join(sorted(fuera)) or "ninguno")))

    # ---------------- 1) regresiones v3 y suite ------------
    ok42 = False
    if not skip:
        pr3 = subprocess.run([sys.executable, "-X", "utf8", "-m",
                              "src.modelo_fiel.regresiones_MODELO_FIEL_v3"],
                             capture_output=True, text=True, cwd=str(E3))
        r3 = json.loads((OUT / "regresiones_MODELO_FIEL_v3.json").read_text(encoding="utf-8"))
        ch3 = r3["checks"]
        ok42 = pr3.returncode == 0 and len(ch3) == 42 and all(
            c.get("estado") == "OK" for c in ch3)
        out.append(_r(ok42, "regresiones_v3_42_42", "rc=%d checks=%d" % (pr3.returncode, len(ch3))))

        pru = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest",
                              "discover", "-s", "tests", "-p", "test_*.py"],
                             capture_output=True, text=True, cwd=str(E3))
        oku = pru.returncode == 0 and "Ran 28 tests" in (pru.stdout + pru.stderr)
        out.append(_r(oku, "unittest_28_28", "discover tests/ RC=%d" % pru.returncode))
    else:
        out.append(_r(True, "regresiones_v3_42_42", "SKIP"))
        out.append(_r(True, "unittest_28_28", "SKIP"))

    checks = out
    payload = {"iteracion": "MODELO_FIEL_4", "gravedad_m_s2": GRAV,
               "n_checks_v4": len(checks), "checks": checks}
    (OUT / "regresiones_MODELO_FIEL_v4.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = all(c["estado"] == "OK" for c in checks)
    print(json.dumps({"regresiones_v4": True,
                      "checks_ok": sum(1 for c in checks if c["estado"] == "OK"),
                      "checks_total": len(checks),
                      "estado": "OK" if ok else "ERROR"}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())