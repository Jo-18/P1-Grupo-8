"""Genera una figura resumen por nivel con los valores de carga extraidos de la
pagina 11 (catalogo_cargas_diseno_edificio_I.json). No modifica geometria."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[2]
CAT = BASE / "datos/cargas/catalogo_cargas_diseno_edificio_I.json"
OUT = BASE / "resultados/cargas_disponibles" / "figuras"
OUT.mkdir(parents=True, exist_ok=True)

cat = json.load(open(CAT, encoding="utf-8"))
niveles = cat["catalogo_por_nivel"]

palette = {"PM": "#d1495b", "SC": "#0471a8"}
for nombre, info in niveles.items():
    cuadros = info.get("cuadros_superficiales", [])
    if not cuadros:
        continue
    ids = [c["trama_id"].replace("por_definir_trama", "T") for c in cuadros]
    pm = [c["PM_ADIC_kgf_m2"] for c in cuadros]
    sc = [c["SC_kgf_m2"] for c in cuadros]
    x = range(len(cuadros))
    fig, ax = plt.subplots(figsize=(6, 4))
    b1 = ax.bar([i - 0.2 for i in x], pm, width=0.4, label="PM.ADIC. (kgf/m2)", color=palette["PM"])
    b2 = ax.bar([i + 0.2 for i in x], sc, width=0.4, label="SC (kgf/m2)", color=palette["SC"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(ids, rotation=20, ha="right")
    ax.set_ylabel("kgf/m2")
    ax.set_title(nombre)
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    for bar in list(b1) + list(b2):
        ax.annotate(f"{bar.get_height():g}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    textcoords="offset points", xytext=(0, 2), ha="center", fontsize=7)
    if info.get("cuadro_excepcional"):
        ax.plot([], [])
    fig.tight_layout()
    fig.savefig(OUT / f"cargas_{nombre.replace(' ', '_').replace('/', '_').replace('°', 'g')}.png", dpi=150)
    plt.close(fig)
    print("fig ->", OUT / nombre, len(cuadros), "cuadros")

# figura con cargas puntuales y lineal
fig, ax = plt.subplots(figsize=(6, 4))
pp = json.load(open(BASE / "datos/cargas/cargas_puntuales_edificio_I.json", encoding="utf-8"))
ids = [p["id"] for p in pp["puntuales"]]
pm = [p["PM_ADIC_original"]["valor"] for p in pp["puntuales"]]
sc = [p["SC_original"]["valor"] for p in pp["puntuales"]]
x = range(len(pp["puntuales"]))
ax.bar([i - 0.2 for i in x], pm, 0.4, label="PM.ADIC. (kgf)", color=palette["PM"])
ax.bar([i + 0.2 for i in x], sc, 0.4, label="SC (kgf)", color=palette["SC"])
ax.set_xticks(list(x)); ax.set_xticklabels(ids, rotation=20, ha="right")
ax.set_ylabel("kgf"); ax.set_title("Cargas puntuales (Pisos 2 y 3)")
ax.grid(axis="y", alpha=0.3); ax.legend()
fig.tight_layout(); fig.savefig(OUT / "cargas_puntuales_pisos_2_3.png", dpi=150); plt.close(fig)

ll = json.load(open(BASE / "datos/cargas/cargas_lineales_edificio_I.json", encoding="utf-8"))["carga_lineal"]
fig, ax = plt.subplots(figsize=(4, 3))
vals = [ll["PM_ADIC_original"]["valor"], ll["SC_original"]["valor"]]
lab = ["PM.ADIC.", "SC"]
ax.bar(lab, vals, color=[palette["PM"], palette["SC"]])
for i, v in enumerate(vals):
    ax.annotate(f"{v} kg/m", (i, v), textcoords="offset points", xytext=(0, 3), ha="center")
ax.set_title("Carga lineal (Piso 4)"); ax.grid(axis="y", alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "carga_lineal_piso_4.png", dpi=150); plt.close(fig)
print("fig puntuales y lineal listas")
print("DIR", OUT)