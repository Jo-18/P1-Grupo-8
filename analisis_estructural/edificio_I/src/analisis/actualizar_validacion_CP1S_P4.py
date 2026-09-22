"""Actualiza validacion_fisica_xref_por_nivel.json: promueve CP1S y P4 a
`transformacion_xref_validada` con evidencia de PUNTOS FISICOS identificables
(columnas P70 + esquinas de muro/abertura), y documenta el desfase horizontal
constante (+0.1813 m) de la rejilla RLE-EJES horizontal de P4 SIN modificarla.

Solo actualiza `estado`, `motivo`/`estado` y anade la evidencia de puntos
fisicos (referenciando el JSON de pendientes). No toca XREF ni congelados.
"""
import json
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
PEND = SRC / "datos/casos_analisis/validacion_fisica_puntos_CP1S_P4.json"
MAIN = SRC / "resultados/cargas_reales/validacion_fisica_xref_por_nivel.json"

pend = json.loads(PEND.read_text(encoding="utf-8"))
data = json.loads(MAIN.read_text(encoding="utf-8"))

cp1s = pend["CP1S"]
p4 = pend["P4"]

# ---- CP1S ----
cp1s_sec = data["por_nivel"]["CP1S"]
cp = cp1s["columnas"]
es = cp1s["esquinas_muro_abertura"]
cp1s_sec["estado"] = "transformacion_xref_validada"
cp1s_sec["motivo"] = (
    "VALIDADO por PUNTOS FISICOS identificables: %d columnas (P70) cierran contra "
    "columnas_referencia con residuo 0.0012-0.0069 m y %d esquinas de muro/abertura "
    "contra caras/poligonos con residuo 0.0004-0.0054 m (0 cruces axales de rejilla "
    "porque CP1S no tiene reticula etiquetada; la validacion se apoya en puntos fisicos)."
    % (cp["n_coinciden_5cm"], es["n_coinciden_2.5cm"])
)
cp1s_sec["validacion_puntos_fisicos"] = cp1s

# ---- P4 ----
p4_sec = data["por_nivel"]["P4"]
p4col = p4["columnas"]
off = p4["desfase_rejilla"]
p4_sec["estado"] = "transformacion_xref_validada"
p4_sec["motivo"] = (
    "VALIDADO por PUNTOS FISICOS: %d columnas (P70) cierran contra columnas_referencia "
    "con residuo 0.0025-0.0065 m (sin cruces 'axales' de rejilla porque el eje_y_positivo "
    "de P4 no es una reticula etiquetada de 5+m). Desfase horizontal CONSTANTE +0.1813 m "
    "de la rejilla RLE-EJES horizontal frente a las cotas congeladas, documentado SIN "
    "compensar (las columnas y la rejilla vertical validan sub-centimetrico)."
    % p4col["n_coinciden_5cm"]
)
p4_sec["validacion_puntos_fisicos"] = p4

# ---- RESUMEN ----
data["resumen"]["CP1S"].update(
    estado=cp1s_sec["estado"],
    n_cruces_axales=0, n_validos_axales_tol_5cm=0, residuo_max_axal_m=None,
    n_cruces_geo=15,
    n_columnas_fisicas=cp["n_coinciden_5cm"],
    n_esquinas_fisicas=es["n_coinciden_2.5cm"],
    residuo_max_fisico_m=max(cp["residuo_max_m"], es["residuo_max_m"]),)
data["resumen"]["P4"].update(
    estado=p4_sec["estado"],
    n_cruces_axales=0, n_validos_axales_tol_5cm=0, residuo_max_axal_m=None,
    n_cruces_geo=10,
    n_columnas_fisicas=p4col["n_coinciden_5cm"],
    residuo_max_fisico_m=p4col["residuo_max_m"],
    desfase_rejilla_horizontal_m=off["desfase_medio_m"])

MAIN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("OK. CP1S ->", data["resumen"]["CP1S"]["estado"], "| P4 ->", data["resumen"]["P4"]["estado"])