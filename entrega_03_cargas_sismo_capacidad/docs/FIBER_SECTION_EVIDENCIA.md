# Fibre Section — evidencia de la sección de demostración `DEMO_50x50_8#25`

> Estado: `IMPLEMENTADO_DEMO_ARBITRARIA`. La sección es **arbitraria** (la consigna la
> permite): no corresponde a ninguna sección real del Edificio I ni II. Todos los
> números de este informe provienen de la **ejecución numérica por fibras** (integración
> no lineal), no de fórmulas cerradas externas.
> Código: `src/capacidad_rc/{materiales,seccion,fibra,momento_curvatura,diagrama_pm}.py`.

## 1. Geometría y posición de las fibras

- Sección **0,50 × 0,50 m**, recubrimiento 0,04 m, hormigón `fc'=21 MPa`, acero `fy=420 MPa`, **8 Ø25** (`As=0,000491 m²` cada una).
- **196 fibras de hormigón**: malla `14×14` (`n_celdas_y=n_celdas_z=14`) sobre el
  perímetro completo (centros en `y∈[−0,2143..0,2143] m`, `z∈[−0,2143..0,2143] m`, paso 0,0357 m).
  Cada fibra tiene `A_celda = (0,50/14)² = 0,0012755 m²`. El acero se **descuenta de la
  fibra de hormigón más cercana** a cada barra (evita doble conteo; ver `seccion.py::fibra_concreto`).
- **8 fibras de acero**: una por barra en `(y_bar, z_bar)`, en esquinas
  `(±0,21, ±0,21) m` y puntos medios de caras `(±0,21,0)` y `(0,±0,21) m`, con `A_s` cada una.
- **Conservación de área**: `ΣA_concreto + ΣA_acero = A_g = 0,2500 m²` (verificado, diferencia 0,0 m²).
- Posiciones exactas verificables en `results/capacidad_rc/m_phi.csv` (por curvatura) y
  en el gráfico `figures/capacidad_rc/seccion_fibras.png`.

## 2. Modelos constitutivos usados (familia OpenSees)

| Material | OpenSees | Parámetros (demo) | Implementación |
|---|---|---|---|
| Hormigón no confinado | `Concrete01` | `fc=21 MPa`, `fcu=0,85·fc=17,85 MPa`, `eps0=0,002`, `epsu=0,004` | `materiales.py::Concrete01` (ascenso parabólico Hognestad → rama descendente lineal → residual `fcu`; **tracción nula**) |
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

La curva N=1050 kN (compresión, 20% de fc·Ag) usa el **mismo protocolo** con distinto `N`.

## 5. Carga axial constante por curva

Cada curva M–φ se ejecuta con **N fijo**: `N=0` y `N=1050 kN` (compresiones positivas).
`N` no cambia a lo largo de la curva; solo crece `κ`. El diagrama P–M evalúa `N` en 21
puntos `N∈[−1575, +5250] kN` (de “tracción simple” a compresión), cada uno con su curva M–φ.

## 6. Criterio de término o falla

→ **Se añadió un criterio explícito de falla** (versión vigente):

- **Criterio 1 — Aplastamiento del hormigón:** la fibra extrema comprimida (+y) alcanza
  `ε_top ≥ episu = 0,004`.
- **Criterio 2 — Fractura supuesta del acero a tracción:** la fibra extrema (−y)
  alcanza `ε_bottom ≤ −0,05` (supuesto documentado del hormigón/acero de la demo).
- **Criterio 3 — Cap de análisis:** si el barrido de κ termina sin alcanzar 1 o 2, el
  punto se marca `CAP_MALLA_SIN_FALLA` y no se reporta como capacidad última confirmada.

`M_u` se define como **el momento en el primer paso que alcanza el criterio** (no el máximo
sobre toda la malla).

## 7. Convergencia por incremento

- Bisección sobre `ε_ct` por punto (tolerancia relativa `1e-7` sobre `|ΔN|`).
- Si el intervalo inicial `[−0,20, 0,08]` no encuadra a `N`, se amplía (hasta 80 pasos por
  lado) en cada κ.
- El análisis es determinista (sin aleatoriedad); la malla `κ` y `n_pasos` quedan
  registrados en `results/capacidad_rc/seccion_demo.json` → reproducibilidad exacta.

## 8. Construcción de cada punto P–M

`puntos_pm` recorre `N` en el rango fijo; para cada `N` calcula su curva M–φ completa y
toma `M_u(N)` = momento del **punto de falla por criterio** de esa curva. El diagrama
P–M es el lugar geométrico `M_max(N)` (superficie de falla). Ver
`diagrama_pm.py` y `results/capacidad_rc/p_m.csv`.

## 9. Convención (compresión, momento, curvatura)

- `ε > 0` = **compresión**; `N > 0` = compresión; `M_z > 0` con compresión en `+y`;
  `κ > 0` deforma con compresión en `+y`.
- Ejes de la sección: `y` = eje de flexión (profundidad), `z` = ancho.

## 10. ¿De dónde sale `M_u`? (confirmación no lineal)

- **`M_u(N=0) = 378,99 kN·m`** (versión vigente tras auditar el criterio) y
  **`κ_u = 0,05718 1/m`** con criterio
  `APLASTAMIENTO_HORMIGON_eps_ext_fibra>=eps_cu` (`eps_cu = epsu_hormigón = 0,004`).
  Proviene íntegramente de la **integración por
  fibras y la búsqueda de `ε_ct` por bisección** dentro de `curva_mphi` (bucle número
  sobre deformaciones/tensiones): no es una fórmula cerrada (`0.85·fc`, Whitney u otra).
- **Auditoría del criterio (iteración actual):** se comprobó que el chequeo previo de
  "fractura del acero" usaba la fibra extrema de **hormigón** (`y=±h/2`) y no las
  fibras de acero reales (barras en `y≈±0,21`; `h/2=0,25`). Corrección aplicada:
  fractura del acero se dispara por **la deformación real de las fibras de acero**,
  `abs(ε) >= eps_su` (`eps_su=0,05`, supuesto documentado), y el aplastamiento por
  `eps_cu` en la fibra extrema de hormigón comprimida. **El `M_u(N=0)` no cambia**
  (el aplastamiento sigue gobernando, la fibra de acero más exigida alcanza ~0,022).
  Etiquetas: `APLASTAMIENTO_HORMIGON_eps_ext_fibra>=eps_cu` /
  `FRACTURA_ACERO_FIBRA_abs_eps>=eps_su`.
- El valor **`403,66 kN·m`** citado en iteraciones previas corresponde al momento en el
  **tope de la malla de curvaturas** (`κ=0,10`) con el material de demo **sin criterio de
  falla**; con el criterio añadido, la curva sigue pero `M_u` se corta antes
  (aplastamiento). Ambos provienen de la misma ejecución no lineal; el primero NO es
  capacidad última, el segundo es el reportado ahora.
- Las curvas completas (más allá del punto de falla) se conservan en `results/capacidad_rc/m_phi.csv`
  y `figures/capacidad_rc/m_phi.png` para trazabilidad.