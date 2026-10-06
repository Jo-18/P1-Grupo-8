"""Capacidad RC: fiber section / M-phi, P-M de columna (ACI 318-19), vigas y P-M de muro."""
import math

import pytest

import capacidad_ha as cha
from conftest import cvm

FC, FY = 35.0, 420.0


def test_mphi_convergencia_de_malla():
    """Mmax de la seccion de fibras COL70/70 (P = 0): malla 20x20 vs 40x40 dentro del 1 %."""
    mmax = {}
    for n in (20, 40):
        curv, m = cvm._fiber_moment_curvature(0.0, n, 0.12, 300)
        mmax[n] = max(m)
    assert abs(mmax[20] - mmax[40]) / mmax[40] < 0.01


def test_pm_columna_puntos_aci():
    """COL70/70 16f28: P0, phiPmax = 0.80*0.65*P0 y traccion pura -0.9 fy Ast (calculo a mano)."""
    curva = cha.curva_pm_columna(700, 700, 16, 28)
    ast = 16 * math.pi * 28 ** 2 / 4                                     # 98,52 cm2 (documento de armaduras)
    p0 = (0.85 * FC * (700 * 700 - ast) + FY * ast) / 1000.0           # 18 422 kN
    assert curva["Ast_mm2"] == pytest.approx(ast)
    assert curva["P0_kN"] == pytest.approx(p0)
    assert curva["phiPmax_kN"] == pytest.approx(0.80 * 0.65 * p0)
    ps = [q["P_kN"] for q in curva["puntos"]]
    assert min(ps) == pytest.approx(-0.9 * FY * ast / 1000.0)
    assert max(ps) == pytest.approx(0.80 * 0.65 * p0)
    for q in curva["puntos"]:
        assert 0.65 - 1e-9 <= q["phi"] <= 0.90 + 1e-9


def test_pm_columna_vs_fibras(monkeypatch):
    """Flexion pura de la COL70/70 por dos metodos independientes con las mismas hipotesis
    (acero elastoplastico, eps_cu = 0.003): bloque de Whitney (capacidad_ha) vs integracion de
    fibras hasta el aplastamiento (carga_viva_sismo). Deben coincidir dentro del 5 %."""
    curva = cha.curva_pm_columna(700, 700, 16, 28)                     # misma seccion que la de fibras (16f28, 64 mm)
    pts = sorted(curva["puntos"], key=lambda q: q["Pn_kN"])
    lo = max((q for q in pts if q["Pn_kN"] <= 0), key=lambda q: q["Pn_kN"])
    hi = min((q for q in pts if q["Pn_kN"] > 0), key=lambda q: q["Pn_kN"])
    mn_whitney = lo["Mn_kN_m"] + (hi["Mn_kN_m"] - lo["Mn_kN_m"]) * (0 - lo["Pn_kN"]) / (hi["Pn_kN"] - lo["Pn_kN"])
    monkeypatch.setattr(cvm, "_FIB_EH", 0.0)
    monkeypatch.setattr(cvm, "_FIB_EPS_CU", 0.003)
    curv, m = cvm._fiber_moment_curvature(0.0, 20, 0.12, 2000)
    assert abs(mn_whitney - m[-1]) / m[-1] < 0.05, f"Whitney {mn_whitney:.0f} vs fibras {m[-1]:.0f} kN-m"


def test_mphi_termina_en_aplastamiento():
    """La curva M-phi se corta cuando la fibra extrema comprimida llega a eps_cu (no en el fin del rango)."""
    curv, m = cvm._fiber_moment_curvature(0.0, 20, 0.12, 300)
    assert curv[-1] < 0.12
    assert 1150.0 < max(m) < 1450.0                                     # 16f28: Mmax cerca de 1 290 kN-m


def test_flexion_viga_a_mano():
    """phiMn de V60/80 con 4f22: a = As fy / (0.85 f'c b), Mn = As fy (d - a/2), phi = 0.9."""
    b, d = 600.0, 739.0
    as_ = 4 * math.pi * 22 ** 2 / 4
    a = as_ * FY / (0.85 * FC * b)
    mn = as_ * FY * (d - a / 2) / 1e6
    phimn, mn_calc, eps_t = cha.flexion_rectangular(b, d, as_)
    assert mn_calc == pytest.approx(mn)
    assert eps_t > 0.005 and phimn == pytest.approx(0.9 * mn)


def test_notacion_de_barras():
    assert cha.bars_area_mm2("4φ22")[0] == pytest.approx(4 * math.pi * 22 ** 2 / 4)
    assert cha.bars_area_mm2("2f22+2f25")[0] == pytest.approx(2 * math.pi * (22 ** 2 + 25 ** 2) / 4)
    av, s, d = cha.stirrup("EDf10a10")
    assert (av, s, d) == (pytest.approx(4 * math.pi * 100 / 4), 100.0, 10)


def test_columna_diametros_mixtos():
    """Documento de armaduras: 16f28 con 5 barras por cara y 4f28+16f36 con f28 en las esquinas (As = 187,49 cm2)."""
    pos16 = cha.barras_perimetro(700, 700, 16, 40 + 10 + 14)
    assert sum(1 for _, y in pos16 if abs(y - 286) < 1e-6) == 5
    _, diams = cha.bars_area_mm2("4φ28+16φ36")
    curva = cha.curva_pm_columna(700, 700, len(diams), max(diams), diametros=diams)
    assert curva["Ast_mm2"] == pytest.approx(4 * math.pi * 28 ** 2 / 4 + 16 * math.pi * 36 ** 2 / 4)
    assert curva["Ast_mm2"] / 100 == pytest.approx(187.49, abs=0.01)
    esquinas = cha.barras_perimetro(700, 700, 20, 40 + 10 + 18)[:4]
    assert all(abs(abs(x) - 282) < 1e-6 and abs(abs(y) - 282) < 1e-6 for x, y in esquinas)


def test_pm_muros_con_armadura_real(unity):
    """Cada muro del registro tiene la curva de su armadura (borde f40 + malla doble f10, data/armaduras.json):
    P0, phiPmax y traccion pura calculados a mano con esas barras."""
    arm = cha.load_armaduras()
    curvas = {c["sectionId"]: c for c in unity["p1l4"]["pmCurves"]}
    for r in unity["p1l4"]["wallRegistry"]:
        c = curvas[r["pmSectionId"]]
        a = cha.armadura_muro(r["grosor"], r["longitud"], arm)
        diams = cha.bars_area_mm2(a["bordes"])[1]
        n_borde, db = len(diams), max(diams)
        s_filas = float(a.get("separacionFilasBorde_m", 0.10)) * 1000
        assert s_filas <= 2 * r["grosor"] * 1000 / 3 + 1e-6                   # ACI 318-19 18.10.6.4
        barras = cha.barras_muro(r["grosor"] * 1000, r["longitud"] * 1000, n_borde, d_borde=db, s_filas_mm=s_filas)
        ast = sum(area for _, area in barras)
        assert ast > 2 * n_borde * math.pi * db ** 2 / 4                    # bordes completos + malla
        p0 = (0.85 * FC * (r["grosor"] * r["longitud"] * 1e6 - ast) + FY * ast) / 1000.0
        assert c["Po_kN"] == pytest.approx(p0, rel=1e-6)
        ps = [p["P_kN"] for p in c["points"]]
        assert min(ps) == pytest.approx(-0.9 * FY * ast / 1000.0, abs=0.1)
        assert max(ps) == pytest.approx(0.80 * 0.65 * p0, abs=0.1)
