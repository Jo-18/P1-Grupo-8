"""La capa de arquitectura (fachada, escaleras, sala, cafeteria) es SOLO VISUAL."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "Proyecto1"
ARQ = ROOT / "edificio_G8" / "Assets" / "Resources" / "arquitectura_visual.json"
GENERADOR = ROOT / "scripts" / "generar_arquitectura.py"
ENTRADAS_ANALISIS = [
    ROOT / "data" / "estructura_completo_unity.json", ROOT / "data" / "parametros_analisis.json",
    ROOT / "data" / "combinaciones.json", ROOT / "data" / "armaduras.json",
    ROOT / "edificio_G8" / "Assets" / "Resources" / "estructura_p1l4_unity.json",
]


def _generador():
    spec = importlib.util.spec_from_file_location("generar_arquitectura", GENERADOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _cajas(g):
    c = g["cajas"]
    return [c[i:i + 6] for i in range(0, len(c), 6)]


def test_json_valido():
    d = json.loads(ARQ.read_text(encoding="utf-8"))
    mats = {m["nombre"] for m in d["materiales"]}
    assert d["grupos"]
    for g in d["grupos"]:
        assert g["capa"] in ("fachada", "entorno", "mobiliario", "mobiliario_exterior")
        assert g["material"] in mats
        assert len(g["cajas"]) % 6 == 0 and len(g["hexas"]) % 24 == 0
        for b in _cajas(g):
            assert b[0] < b[1] and b[2] < b[3] and b[4] < b[5]
    piezas = {g["nombre"] for g in d["grupos"]}
    assert any("turquesa" in n for n in piezas)          # taburetes de la sala
    assert any("quitasol" in n for n in piezas)          # terrazas de la cafeteria


def test_json_al_dia_con_el_generador():
    gen = _generador()
    assert json.loads(ARQ.read_text(encoding="utf-8")) == json.loads(json.dumps(gen.generar()))


def test_sala_tiene_6_mesas_y_cafeteria_solo_bajo_la_sala():
    d = json.loads(ARQ.read_text(encoding="utf-8"))
    tops = next(g for g in d["grupos"] if g["capa"] == "mobiliario" and g["piso"] == "CIELO_1" and g["material"] == "mesa_blanca")
    assert len(tops["cajas"]) // 6 == 6
    cafe = next(g for g in d["grupos"] if g["capa"] == "mobiliario" and g["piso"] == "CIELO_1S" and g["material"] == "madera")
    cubiertas = [b for b in _cajas(cafe) if b[5] - b[4] < 0.05 and b[5] > 0.7]
    assert len(cubiertas) >= 15
    # todo el mobiliario interior de la planta baja queda en el rectangulo bajo la sala (x 0..7,51)
    for g in d["grupos"]:
        if g["capa"] == "mobiliario" and g["piso"] == "CIELO_1S":
            for b in _cajas(g):
                assert -0.01 <= b[0] and b[1] <= 7.52 and -7.25 <= b[2] and b[3] <= 8.9, (g["nombre"], b)


def test_entorno_en_dos_niveles_y_escalera_norte():
    gen = _generador()
    gen.generar()
    g = gen.A.grupos
    # plaza de la entrada principal a la altura del 2.o piso, al este del edificio
    pav = _cajas(g[("entorno", "", "pavimento")])
    assert any(abs(b[5] - gen.Z_SUP) < 1e-9 and b[0] >= gen.E1_ESTE - 1e-9 for b in pav)
    # escalera norte: dos tramos de 10 peldanos y un descanso a media altura (z = 1,98)
    horm = _cajas(g[("entorno", "", "hormigon")])
    y0, y1 = gen.ESC_NORTE["y0"], gen.ESC_NORTE["y1"]
    norte = [b for b in horm if b[2] >= y0 - 1e-9 and b[3] <= y1 + 1e-9]
    assert len(norte) == 21
    assert any(abs(b[5] - (gen.Z_SUP + gen.Z_INF) / 2) < 1e-9 and b[1] - b[0] > 1.5 for b in norte)
    assert all(gen.Z_INF < b[5] < gen.Z_SUP for b in norte)
    # escalinata ancha: baja desde la plataforma (2.o piso) hacia el oeste hasta la terraza
    ancha = sorted((b for b in horm if b[2] >= gen.ESCALINATA["y0"] - 1e-9 and b[3] <= gen.ESCALINATA["y1"] + 1e-9
                    and b[1] <= gen.PLATAFORMA[0] + 1e-9), key=lambda b: b[0])
    assert len(ancha) == 21
    assert all(a[5] < b[5] for a, b in zip(ancha, ancha[1:]))       # sube hacia el este (la plataforma)


def test_sin_choques_con_la_estructura():
    gen = _generador()
    gen.generar()
    assert gen.choques() == []


def test_generar_no_modifica_el_modelo_ni_los_resultados(tmp_path):
    antes = {p: _sha(p) for p in ENTRADAS_ANALISIS}
    gen = _generador()
    datos = gen.generar()
    (tmp_path / "arq.json").write_text(json.dumps(datos), encoding="utf-8")
    assert {p: _sha(p) for p in ENTRADAS_ANALISIS} == antes
    assert ARQ.resolve() not in {p.resolve() for p in ENTRADAS_ANALISIS}
