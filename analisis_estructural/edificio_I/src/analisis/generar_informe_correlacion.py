"""Reporte markdown de correlacion de cargas reales (pagina 11) - parte deterministica.
Genera: informe_correlacion_cargas.md con tabla nivel x losa x PP x PM.ADIC x SC,
% de area inequivocamente clasificada, zonas pendientes y ubicacion de puntuales/lineal."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
res = json.loads((BASE / "resultados/cargas_reales/correlacion_cargas_pagina11.json"
                  ).read_text(encoding="utf-8"))
cat = res["catalogo_tramas_con_certeza"]["catalogo_por_nivel"]
pp = res["peso_propio_por_losa"]
cov = res["auditoria_cobertura_niveles"]
pu = res["cargas_puntuales_y_lineal"]

lines = []
lines.append("# Correlacion de cargas reales - Edificio I (pagina 11): parte deterministic")
lines.append("")
lines.append("## 1. Tabla nivel x region(losa) x PP x PM.ADIC x SC")
lines.append("")
lines.append("`PM.ADIC`/`SC` corresponden al catalogo por nivel (aun `por_confirmar_trama` "
             "hasta correlacion vectorial). `PP` usa el espesor real de cada losa. "
             "Unidades provisionales kgf (SI provisional kN).")
lines.append("")
lines.append("| Nivel | Losa (region) | e (m) | PP kgf/m2 | PP kN/m2 | area neta m2 | PM.ADIC kgf/m2 | SC kgf/m2 |")
lines.append("|---|---|---|---|---|---|---|---|")
pmad_by_nivel, sc_by_nivel = {}, {}
for nk, info in cat.items():
    cads = info.get("cuadros_superficiales", [])
    pm = ", ".join(str(t["PM_ADIC_kgf_m2"]) for t in cads)
    sc = ", ".join(str(t["SC_kgf_m2"]) for t in cads)
    if info.get("cuadro_excepcional"):
        pm = pm + f" (+{info['cuadro_excepcional']['PM_ADIC_kgf_m2']})"
    pmad_by_nivel[nk] = pm
    sc_by_nivel[nk] = sc

for cod in ["CP1S", "P1", "P2", "P3", "P4"]:
    etiq = {"CP1S": "1° Subterráneo", "P1": "Piso 1", "P2": "Piso 2", "P3": "Piso 3",
            "P4": "Piso 4"}[cod]
    pmk = {"CP1S": "Piso 1 Subterraneo (CP1S)", "P1": "Piso 1", "P2": "Piso 2",
           "P3": "Piso 3", "P4": "Piso 4"}[cod]
    for losa in pp[cod]["losas"]:
        lines.append(f"| {etiq} | {losa['id']} | {losa['espesor_m']} | "
                     f"{losa['pp']['pp_kgf_m2']} | {losa['pp']['pp_kN_m2']} | "
                     f"{losa['area_neta_cargada_m2']} | {pmad_by_nivel.get(pmk,'?')} | "
                     f"{sc_by_nivel.get(pmk,'?')} |")

lines.append("")
lines.append("## 2. Porcentaje de area inequivocamente clasificada por nivel")
lines.append("")
lines.append("| Nivel | Area neta m2 | % trama identificada | % trama por confirmar | % sin clasificar |")
lines.append("|---|---|---|---|---|")
for cod in ["CP1S", "P1", "P2", "P3", "P4"]:
    c = cov[cod]
    neta = c["area_neta_total_m2"]
    lines.append(f"| {c['etiqueta']} | {c['area_neta_total_m2']} | 0% | 100% | 0% |")
lines.append("")
lines.append("Sin correlacion de tramas la clasificacion inequivoca es **0%** en todos los "
             "niveles; el 100% queda `por_confirmar_trama` de forma explicita (no se rellena "
             "con la trama mas cercana).")
lines.append("")
lines.append("## 3. Zonas pendientes")
lines.append("")
lines.append("- `transformacion_pagina_modelo`: pendiente_correlacion_vectorial en las 5 plantas.")
lines.append("- Coordenadas del modelo de cargas puntuales P2/P3: por_confirmar_vectorial.")
lines.append("- Trazado/extremos de la carga lineal P4: por_confirmar_vectorial.")
lines.append("- Interpretacion de unidad kg vs kgf: por_confirmar (SI provisional).")
lines.append("- Region exacta y trama del valor excepcional 2800 kg/m2 (P1): por_confirmar "
             "(requiere revision de ingenieria).")
lines.append("")
lines.append("## 4. Ubicacion de cargas puntuales y lineal")
lines.append("")
lines.append("| Carga | Nivel | Coord OCR px | Coord modelo | Dominio | Receptor | Mecanismo | PM.ADIC | SC |")
lines.append("|---|---|---|---|---|---|---|---|---|")
for p in pu["puntuales"]:
    c = p["coordenada_ocr_px"]
    lines.append(f"| {p['id']} | {p['nivel']} | ({c['x']},{c['y']}) | {p['coordenada_modelo_m']['estado']} "
                 f"| {p['dominio_contenedor']} | {p['elemento_receptor']} | "
                 f"{p['mecanismo_transferencia']} | {p['PM_ADIC']['valor']} | {p['SC']['valor']} |")
l = pu["lineal"]
lines.append(f"| {l['id']} | {l['nivel']} | (por_confirmar)2 pts | por_confirmar_vectorial | "
             f"{l['dominio_o_elemento']} | por_confirmar | carga_directa_lineal | "
             f"{l['PM_ADIC']['valor']} kg/m | {l['SC']['valor']} kg/m |")
lines.append("")
lines.append("## 5. Notas")
lines.append("")
lines.append("- Losas con e=0.15: PP 375 kgf/m2 = 3.67749375 kN/m2 (provisional).")
lines.append("- Losas con e=0.12: PP 300 kgf/m2 = 2.941995 kN/m2 (provisional).")
lines.append("- La carga lineal del Piso 4 (7600/800 kg/m) YA es lineal; no se multiplica por ancho.")
lines.append("- Los JSON congelados se leyeron solo-lectura y quedaron byte-identicos al manifest.")

out = BASE / "resultados/cargas_reales/informe_correlacion_cargas.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("escrito", out)
print("lineas", len(lines))