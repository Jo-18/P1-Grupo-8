"""bloqueo_PMADIC_EII_plano700 - bloqueo documental del PM.ADIC EII (iteracion MODELO_FIEL_4).

Tarea 3: busca en TODAS las fuentes del repo (solo lectura) el plano/catalogo 700
del EII (DXF, PDF vectorial, imagen, catalogo, tabla con posiciones A-F). El repositorio
NO contiene ninguna fuente con POSICIONES por viga/nivel: solo el catalogo de
intensidades A-F (eii_viewer.cargas.caso_G). Las laminas reales existen FUERA del repo.

Consecuencia: las 6 familias A-F permanecen `AMBIGUO_NO_APLICADO`; PM.ADIC aplicada
al FE del EII = 0 kN; cobertura 0 %. NO se distribuye por proximidad, NO se inventa
mapeo ni se regenera G_EII ni el peso sismico.

Escribe en modelo_fiel/:
  BLOQUEO_PMADIC_EII_plano700.json
  BLOQUEO_PMADIC_EII_plano700.md

Uso:
  python -X utf8 -m src.modelo_fiel.bloqueo_PMADIC_EII_plano700
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3 = REPO / "entrega_03_cargas_sismo_capacidad"
DATA = E3 / "data" / "externas"
OUT = E3 / "modelo_fiel"

EII_VIEWER = DATA / "eii_viewer.json"
MAPEO_V3 = OUT / "mapeo_PMADIC_EII_plano700.json"

DXF_EXTERNO = (r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1"
               r"\Datos Estructurales\2017_67-700.dxf")
PDF_EXTERNO = (r"C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1"
               r"\Datos Estructurales\Union PDF's Edificio II.pdf")

G = 9.80665
G_KN_POR_KG = G / 1000.0

UBICACIONES_BUSCADAS = [
    ("tree completo (glob) DXF/DWG/PDF/PNG/JPG/TIFF/SVG *", "0 DXF/DWG/PDF en el arbol"),
    ("datos/geometria/*.json", "referencias a DXF estructurales del EI 2017_67-101/102/103; nada del 700"),
    ("analisis_estructural/edificio_II_casoG_PP_elementos/eii_viewer.json",
     "catalogo A-F de intensidades (PM_ADIC_lineal_kg_m y SC_lineal_kg_m); nota: 'plano 700 (DXF), catalogo por zona'; SIN posiciones por viga/nivel"),
    ("analisis_estructural/edificio_II_casoG_PP_elementos/eii_esfuerzos.json", "caso G estructural; sin catalogo posicional"),
    ("laboratorio_semana2/src/analisis/auditoria_xref_700.py",
     "auditoria CAD de metadatos del DXF 700 (XREF/bloques/INSERT/viewports); DXF referenciado en ruta EXTERNA; salidas: transformacion por nivel, SIN posiciones A-F"),
    ("laboratorio_semana2/datos/cargas/*", "solo catalogo del edificio I (SC/PM.ADIC kgf/m2); nada del EII"),
    ("laboratorio_semana2/datos/entradas_recibidas/edificio_II/2026-09-03/EII_2024_22/*",
     "figuras por nivel y ensayos CP2; sin catalogo del plano 700 con posiciones"),
    ("viewer_unity/Assets/StreamingAssets/lab_data/edificios/II/*",
     "solo geometria EII_CP1..CP4; tributary y regiones_tributarias SOLO del edificio I"),
    ("config/fuentes.json, README, docs/PLAN_*", "referencias documentales del plano 700; ninguna aporta posiciones"),
]


def main() -> dict:
    viewer = json.loads(EII_VIEWER.read_text(encoding="utf-8"))
    cg = viewer["cargas"]["caso_G"]
    intensidades = cg["PM_ADIC_lineal_kg_m"]
    mapeo_v3 = json.loads(MAPEO_V3.read_text(encoding="utf-8"))

    conversion = {f: round(v * G_KN_POR_KG, 6) for f, v in intensidades.items()}
    v3_conversion = mapeo_v3["interpretacion_kg_m"]

    payload = {
        "iteracion": "MODELO_FIEL_4",
        "tarea": "3_bloqueo_PMADIC_EII_plano700",
        "estado": "BLOQUEADO_FALTA_EVIDENCIA_POSICIONAL",
        "resumen": {
            "n_familias_catalogadas": 6,
            "familias_estado": "AMBIGUO_NO_APLICADO",
            "aplicada_al_FE_kN": 0.0,
            "cobertura": 0.0,
            "motivo": "no hay correspondencia familia->viga/nivel sin la lamina 700 con posiciones",
        },
        "catalogo_intensidades_kg_m": intensidades,
        "conversion_g_kn_m": conversion,
        "unidad_interpretacion": v3_conversion,
        "conversion_ejemplo": {
            "A": "260 Kg/m x 0.00980665 = 2.549729 kN/m",
            "D": "1500 Kg/m x 0.00980665 = 14.709975 kN/m",
            "nota": "no se suma longitud de tramo (desconocida hasta obtener la lamina)",
        },
        "fuentes_buscadas": [
            {"ubicacion": ubic, "resultado": res} for ubic, res in UBICACIONES_BUSCADAS
        ],
        "hallazgo_fisico_fuera_del_repo": {
            "dxf_700": {
                "ruta": DXF_EXTERNO,
                "tamano_bytes": 18207984,
                "sha256": "F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF",
                "modificado": "02/09/2026 10:53",
                "nota": "existe pero NO esta versionado dentro del repo; no es evidencia reproducible de la entrega",
            },
            "pdf_edificio_II": {
                "ruta": PDF_EXTERNO,
                "tamano_bytes": 14692764,
                "sha256": "4899A8B0033141FEB7F630F3AB8392ACBAEC364DE647BF7607C168B10D0CBB28",
                "modificado": "26/08/2026 06:21",
                "nota": "contendria la lamina 700 vectorial (pagina correspondiente); no versionado en el repo",
            },
        },
        "archivo_a_solicitar": {
            "primario": {
                "nombre": "2017_67-700.dxf",
                "ruta_de_entrega_sugerida": ("laboratorio_semana2/datos/entradas_recibidas/"
                                             "edificio_II/2026-09-03/EII_2024_22/00_planos/"
                                             "2017_67-700.dxf"),
                "sha256": "F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF",
                "tamano_bytes": 18207984,
                "requisitos": [
                    "trazado del texto/leader 'A'..'F' de PM.ADIC (y su rango Kg/m)",
                    "posicion de las polilines de trama/hatch por zona con unidad",
                    "la planta estructural embebida (bloques 2017_67-101/102/103) para la transformacion por nivel",
                ],
            },
            "alternativo": {"nombre": "paginas vectoriales de 'Union PDF's Edificio II.pdf'"
                            " correspondientes a la lamina 700 con las zonas A-F",
                            "sha256": "4899A8B0033141FEB7F630F3AB8392ACBAEC364DE647BF7607C168B10D0CBB28"},
            "nota": ("una vez en el repositorio se podra ejecutar el mapeo con controles: "
                     "rotulo A-F, intensidad original, conversion g, tramo/longitud, IDs "
                     "receptores por nivel, carga total por familia/nivel, conservacion y "
                     "doble conteo. Si no llega, se mantiene cobertura 0 % y G_EII/peso "
                     "sismico sin cambios."),
        },
        "decision": {
            "mantener": "mapeo_PMADIC_EII_plano700 (v3) AMBIGUO_NO_APLICADO 3/6 familias y cobertura 0",
            "no_por_proximidad": True,
            "no_regenerar": ["G_EII (25970.9994 kN v3)",
                             "peso_sismico EII (28600.7138 kN v3)",
                             "EX/EY, superposicion, D/C"],
        },
        "consistencia_con_v3": {
            "aplicada_al_FE_kN": mapeo_v3["aplicacion"]["aplicada_al_FE_kN"],
            "cobertura": mapeo_v3["aplicacion"]["cobertura"],
            "n_mapeada": mapeo_v3["mapeo"]["n_mapeada"],
        },
    }
    (OUT / "BLOQUEO_PMADIC_EII_plano700.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# BLOQUEO PM.ADIC Edificio II - plano 700 (MODELO_FIEL_4)", "",
          f"**Estado:** `{payload['estado']}`",
          "",
"## Resumen", "",
        "- Familias catalogadas (intensidades del catalogo EII): 6 (A-F).",
        "- Estado por familia: **AMBIGUO_NO_APLICADO** (sin correspondencia familia->viga/nivel).",
        "- PM.ADIC aplicada al FE del EII: **0 kN**. Cobertura: **0 %**.",
        "- No se distribuye por proximidad ni se inventa mapeo.",
        "",
          "## Catalogo (intensidades) y conversion", "",
          "| Familia | Kg/m | kN/m (g=9.80665) |",
          "|---|---|---|"]
    for f in sorted(intensidades):
        md.append(f"| {f} | {intensidades[f]} | {conversion[f]} |")
    md += ["", "D = 1500 Kg/m -> 14.709975 kN/m (tramo/longitud desconocida).", "",
           "## Donde se busco (solo lectura)", ""]
    for ubic, res in UBICACIONES_BUSCADAS:
        md.append(f"- **{ubic}:** {res}")
    md += ["", "## Hallazgo fisico fuera del repo", "",
           f"- `2017_67-700.dxf` en `{DXF_EXTERNO}` (18,207,984 B; sha256 "
           + "`F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF`).",
           "- `Union PDF's Edificio II.pdf` en `Datos Estructurales\\` (14,692,764 B; "
           "sha256 `4899A8B0033141FEB7F630F3AB8392ACBAEC364DE647BF7607C168B10D0CBB28`),"
           " incluiria la lamina 700 vectorial.",
           "- Ambos fuera del repo: **no constituyen evidencia reproducible** de la entrega.", "",
           "## Archivo exacto a solicitar", "",
           "### Primario",
           f"- **`2017_67-700.dxf`** (sha256 `F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF`, "
           "18,207,984 B), a versionar en "
           "`laboratorio_semana2/datos/entradas_recibidas/edificio_II/2026-09-03/EII_2024_22/00_planos/`."
           "",
           "- Requisitos para el mapeo: texto/leader `A`..`F` de PM.ADIC con su rango Kg/m, "
           "posicion de las polilineas de trama por zona con unidad, y la planta estructural "
           "embebida (`2017_67-101/102/103`) para la transformacion por nivel.", "",
           "### Alternativo",
           "- Paginas vectoriales de `Union PDF's Edificio II.pdf` correspondientes a la lamina 700 "
           "con las zonas A-F.", "",
           "## Decision de MODELO_FIEL_4", "",
           "- Mantener el mapeo v3 en `AMBIGUO_NO_APLICADO` (6/6 familias) con cobertura 0 %.",
           "- **No** se regenera `G_EII` (25,970.9994 kN) ni el peso sismico EII (28,600.7138 kN).",
           "- **No** se tocan EX/EY, superposicion ni D/C.", "",
           "| Control | Valor |",
           "|---|---|",
           f"| Familias AMBIGUO_NO_APLICADO | 6/6 |",
           f"| PM.ADIC aplicada (kN) | 0.0 |",
           f"| Cobertura | 0 % |",
    ]
    (OUT / "BLOQUEO_PMADIC_EII_plano700.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"estado": payload["estado"],
                      "familias": 6,
                      "aplicada_kN": 0.0,
                      "cobertura": 0.0,
                      "archivo_a_solicitar": "2017_67-700.dxf",
                      "sha256": "F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF"},
                     ensure_ascii=False, indent=2))
    return payload


if __name__ == "__main__":
    main()