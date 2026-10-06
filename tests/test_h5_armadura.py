"""Honors H5: cambio de armadura con regeneracion de la curva de interaccion P-M y del DCR."""
import json
import math

import pytest

import capacidad_ha as cha
from conftest import run_exporter

FC, FY = 35.0, 420.0


@pytest.fixture(scope="module")
def con_20f28(tmp_session):
    """Escenario como el editor de armadura de Unity: la COL70/70 tipo pasa de 16f28 a 20f28.
    Las columnas con excepcion propia en data/armaduras.json (porticos extremos y la especial) no cambian."""
    arm = tmp_session / "armaduras_unity.json"
    arm.write_text(json.dumps({"secciones": {"COL70/70": {"barras": "20f28"}}, "elementos": {}}), encoding="utf-8")
    out = tmp_session / "arm20.json"
    r = run_exporter(out, "--armaduras", arm)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(out.read_text(encoding="utf-8"))


def _sin_excepcion(e):
    return e["elementTag"] not in cha.load_armaduras()["elementos"]


@pytest.mark.lento
def test_curva_regenerada(con_20f28):
    curvas = {c["sectionId"]: c for c in con_20f28["p1l4"]["pmCurves"]}
    assert "COL70/70_20f28" in curvas
    c = curvas["COL70/70_20f28"]
    ast = 20 * math.pi * 28 ** 2 / 4
    p0 = (0.85 * FC * (700 * 700 - ast) + FY * ast) / 1000.0
    assert c["Ast_mm2"] == pytest.approx(ast) and c["steelBars"] == 20
    assert c["Po_kN"] == pytest.approx(p0, abs=0.1)        # exportado con 0.1 kN
    assert max(p["P_kN"] for p in c["points"]) == pytest.approx(0.80 * 0.65 * p0, abs=0.1)
    # la curva exportada es la misma que calcula capacidad_ha directamente
    arm = cha.load_armaduras()                                  # recubrimiento y estribo reales (EDf10a10)
    d_estribo = cha.stirrup(arm["secciones"]["COL70/70"]["estribos"])[2]
    directa = cha.curva_pm_columna(700, 700, 20, 28, arm["recubrimiento_m"], d_estribo)["puntos"]
    assert len(directa) == len(c["points"])
    ordenar = lambda pts: sorted(pts, key=lambda q: (round(q["P_kN"], 1), round(q["M_kN_m"], 1)))
    for p, q in zip(ordenar(c["points"]), ordenar(directa)):
        assert p["P_kN"] == pytest.approx(q["P_kN"], abs=0.1) and p["M_kN_m"] == pytest.approx(q["M_kN_m"], abs=0.1)


@pytest.mark.lento
def test_mas_armadura_mas_capacidad_menor_dcr(con_20f28, unity):
    """Con mas acero cada columna COL70/70 tipo tiene capacidad mayor y DCR menor o igual (mismas fuerzas)."""
    base = {e["elementTag"]: e for e in unity["elements"] if e.get("sectionId") == "COL70/70" and _sin_excepcion(e)}
    for e in con_20f28["elements"]:
        if e.get("sectionId") != "COL70/70" or not _sin_excepcion(e):
            continue
        assert e["pmCurveId"] == "COL70/70_20f28"
        assert e["capacidad"]["DCR"] <= base[e["elementTag"]]["capacidad"]["DCR"] + 1e-9
    peor = max(base.values(), key=lambda x: x["capacidad"]["DCR"])["elementTag"]
    nuevo = next(e for e in con_20f28["elements"] if e["elementTag"] == peor)
    assert nuevo["capacidad"]["DCR"] < base[peor]["capacidad"]["DCR"]
