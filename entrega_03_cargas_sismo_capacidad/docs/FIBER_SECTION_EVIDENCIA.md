# Fibre Section — evidencia de la sección de demostración oficial `DEMO_RC_EI`

> Estado: `IMPLEMENTADO_DEMO_ARBITRARIA`. La sección es **de demostración** con
> **geometría documentada** (columna de hormigón 0,70 × 0,70 m, real de los edificios)
> y **armado de demostración 12Ø25** (la armadura real no está documentada →
> `HIPOTESIS_DEMOSTRACION`). La sección **no** es capacidad real de diseño de ninguna
> columna. Todos los números provienen de la **ejecución numérica por fibras**
> (integración no lineal), no de fórmulas cerradas externas.
> Código: `src/capacidad_rc/{materiales,seccion,fibra,momento_curvatura,diagrama_pm}.py`
> y el generador por edificio `src/capacidad_rc/edificios.py`.
> `DEMO_RC_EII` es **idéntica salvo `fc=35 MPa`** (documentado G35); esta nota describe
> la `DEMO_RC_EI` (fc=40 MPa, hipótesis del grupo G40).
>
> La antigua sección genérica `DEMO_50x50_8#25` (fc=21, 8Ø25) quedó **eliminada**
> como artefacto obsoleto; ya no existe `seccion_demo()` en el código.

## 1. Geometría y posición de las fibras

- Sección **0,70 × 0,70 m**, recubrimiento 0,04 m, hormigón `fc'=40 MPa`, acero
  `fy=420 MPa`, **12 Ø25** (`As=0,000491 m²` cada una; `As_total = 0,0058904 m²`).
- **196 fibras de hormigón**: malla `14×14` (`n_celdas_y=n_celdas_z=14`) sobre el
  perímetro completo (centros en `y,z∈[−0,32..0,32] m`, paso 0,05 m).
  Cada fibra tiene `A_celda = (0,70/14)² = 0,0025 m²`. El acero se **descuenta de la
  fibra de hormigón más cercana** a cada barra (evita doble conteo; ver `seccion.py::fibra_concreto`).
- **12 fibras de acero**: una por barra, distribución simétrica:
  - 4 esquinas en `(±0,31, ±0,31) m`;
  - 4 en caras `±Y` en `(±0,31, ±0,1033) m`;
  - 4 en caras `±Z` en `(±0,1033, ±0,31) m`.
- **Conservación de área**: `ΣA_concreto + ΣA_acero = A_g = 0,4900 m²` (verificado, diferencia 0,0 m²).
- Posiciones exactas verificables en `results/capacidad_rc/DEMO_RC_EI_m_phi.csv` y
  en el gráfico `figures/capacidad_rc/DEMO_RC_EI_seccion_fibras.png`.

## 2. Modelos constitutivos usados (familia OpenSees)

| Material | OpenSees | Parámetros (demo) | Implementación |
|---|---|---|---|
| Hormigón no confinado | `Concrete01` | `fc=40 MPa`, `fcu=0,85·fc=34,0 MPa`, `eps0=0,002`, `epsu=0,004` | `materiales.py::Concrete01` (ascenso parabólico Hognestad → rama descendente lineal → residual `fcu`; **tracción nula**) |
| Acero | `Steel02` simplificado | `fy=420 MPa`, `Es=200 000 MPa`, `Ep=2000 MPa` (endurecimiento lineal) | `materiales.py::Steel02Simpl` (simétrico; `epsy=fy/Es=0,0021`) |

En OpenSees se define la misma discretización con
`uniaxialMaterial("Concrete01",...)` + `uniaxialMaterial("Steel01", fy, Es, b=Ep/Es)`
según `fibra.py::seccion_opensees` (cross-check de que los parámetros son los del código).
`b = Ep/Es = 0,01` (relación de endurecimiento).

## 3. Unidades

- Esfuerzos: **MPa** (1 MPa = 1000 kN/m²).
- Áreas: **m²**. Deformaciones: adimensionales (compresión positiva).
- Fuerzas: **kN**. Momentos: **kN·m**. Longitudes: **m**. Curvatura: **1/m**.
- `N = Σ σ_f·A_f` (kN, compresión +), `M = Σ σ_f·A_f·y` (kN·m, compresión en +y).

## 4. Protocolo de carga del análisis M–φ

Para cada curva y cada paso de curvatura (ver `momento_curvatura.py::curva_mphi`):

1. Compatibilidad: `ε(y) = ε_ct + κ·y`, con `y∈[−h/2, +h/2]`.
2. La ley `σ_f = material(ε_f)` de cada fibra se evalúa numéricamente (hormigón nulo a
   tracción; acero simétrico).
3. **Se fija κ** y se resuelve `ε_ct` tal que `N_int(ε_ct) = Σ σ_f A_f = N` (carga axial
   **constante** de la curva) mediante **bisección** (≤90 iteraciones, tolerancia
   `|N_int−N| < 1e-7·max(1,|N|)`).
4. Con `ε_ct` convergido: `M = Σ σ_f A_f y` y se guardan `ε_top`, `ε_bottom`, `y_neutra`.
5. Se barre `κ ∈ [0, 0,24]` en 320 pasos (`kappa_max_analisis=0.24`, `n_pasos=320`) con
   `LoadControl` equivalente de un solo paso por punto (análisis cuasiestático, sin
   integración temporal).

La curva `N=3920 kN` (compresión, 20% de fc·Ag) usa el **mismo protocolo** con distinto `N`.

## 5. Carga axial constante por curva

Cada curva M–φ se ejecuta con **N fijo**: `N=0` y `N=3920 kN` (compresiones
positivas). `N` no cambia a lo largo de la curva; solo crece `κ`. El diagrama P–M
evalúa `N` en 21 puntos `N∈[−5880, +19600] kN` (de “tracción simple” a compresión),
cada uno con su curva M–φ.

## 6. Criterio de término o falla

- **Criterio 1 — Aplastamiento del hormigón:** la fibra extrema comprimida (+y) alcanza
  `ε_top ≥ episu = 0,004`.
- **Criterio 2 — Fractura supuesta del acero a tracción:** una fibra de **acero**
  alcanza `abs(ε) ≥ ε_su = 0,05` (supuesto documentado del acero de la demo).
- **Criterio 3 — Cap de análisis:** si el barrido de κ termina sin alcanzar 1 o 2, el
  punto se marca `CAP_MALLA_SIN_FALLA` y no se reporta como capacidad última confirmada.

`M_u` se define como **el momento en el primer paso que alcanza el criterio** (no el máximo
sobre toda la malla). Para `N=0` el aplastamiento del hormigón es el primer criterio.

## 7. Convergencia por incremento

- Bisección sobre `ε_ct` por punto (tolerancia relativa `1e-7` sobre `|ΔN|`).
- Si el intervalo inicial `[−0,20, 0,08]` no encuadra a `N`, se amplía (hasta 80 pasos por
  lado) en cada κ.
- El análisis es determinista (sin aleatoriedad); la malla `κ` y `n_pasos` quedan
  registrados en `results/capacidad_rc/DEMO_RC_EI.json` → reproducibilidad exacta.

## 8. Construcción de cada punto P–M

`puntos_pm` recorre `N` en el rango fijo; para cada `N` calcula su curva M–φ completa y
toma `M_u(N)` = momento del **punto de falla por criterio** de esa curva. El diagrama
P–M es el lugar geométrico `M_max(N)` (superficie de falla). Ver
`diagrama_pm.py` y `results/capacidad_rc/DEMO_RC_EI_p_m.csv`.

## 9. Convención (compresión, momento, curvatura)

- `ε > 0` = **compresión**; `N > 0` = compresión; `M_z > 0` con compresión en `+y`;
  `κ > 0` deforma con compresión en `+y`.
- Ejes de la sección: `y` = eje de flexión (profundidad), `z` = ancho.

## 10. ¿De dónde sale `M_u`? (confirmación no lineal)

- **`M_u(N=0) = 896,46 kN·m`** y **`κ_u = 0,06395 1/m`** con criterio
  `APLASTAMIENTO_HORMIGON_eps_ext_fibra>=eps_cu` (`eps_cu = epsu_hormigón = 0,004`).
  Origina íntegramente de la **integración por fibras y la búsqueda de `ε_ct` por
  bisección** dentro de `curva_mphi` (bucle numérico sobre deformaciones/tensiones):
  no es una fórmula cerrada (`0.85·fc`, Whitney u otra).
- Curva de compresión `N=3920 kN`: `M_u = 1.715,06 kN·m` (mismo protocolo y criterio).
- **Auditoría del criterio aplicada (documentada):** el chequeo de fractura del acero
  se dispara por **la deformación real de las fibras de acero**, `abs(ε) >= eps_su`
  (`eps_su=0,05`, supuesto documentado), y el aplastamiento por `eps_cu` en la fibra
  extrema de hormigón comprimida. Etiquetas: `APLASTAMIENTO_HORMIGON_eps_ext_fibra>=eps_cu`
  / `FRACTURA_ACERO_FIBRA_abs_eps>=eps_su`.
- La sección `DEMO_RC_EII` (mismo armado, `fc=35 MPa`) da `M_u(N=0) = 875,00 kN·m`
  (las figuras y JSON por edificio están bajo `DEMO_RC_{EI,EII}_*`).
- Las curvas completas (más allá del punto de falla) se conservan en
  `results/capacidad_rc/DEMO_RC_EI_m_phi.csv` y `figures/capacidad_rc/DEMO_RC_EI_m_phi.png`
  para trazabilidad.