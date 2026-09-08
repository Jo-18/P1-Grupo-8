# Auditoría del peso propio — Edificio II (Entrega 03, v1)

Modo de trabajo: **solo lectura**. No se modifica el FE, ni el viewer, ni las geometrías, ni los
resultados publicados del caso `G`. Este documento aporta **evidencia documental** de la reconstrucción
del PP por tipo de elemento y por nivel, clasifica cada componente con estados de evidencia explícitos y
documenta las discrepancias (muros) y las decisiones de modelo pendientes.

- Ejecutable: `src/peso_propio_teorico_EDIFICIO_II_v1.py` (abre el JSON solo en `results/…_hash.txt`).
- Salida determinista: `results/peso_propio_teorico_EDIFICIO_II_v1.json`
- Hash (2 corridas idénticas, tras cierre limpio): `df7fa34f71096a6169f0e41d8a9ac701ad23e511429e9a479d26efc7f8ce6246`

> Documentos relacionados de esta entrega: `README.md` (estructura por líneas de
> trabajo), `docs/PLAN_ENTREGA_03.md` (matriz de estados) y `docs/GUIA_DEFENSA.md`
> (superposición, fibras, demanda/capacidad). El bloqueo de muros
> (`PENDIENTE_ORIGEN_PIPELINE`, sección 4) impide cerrar `G_EII` y, en cadena, el
> peso sísmico `W` para EX/EY.

## Estados de evidencia usados

| Estado | Significado |
|---|---|
| `CONFIRMADO_REPRODUCIDO` | Recalculado desde fuentes rastreables; coincide con el publicado/implicito (tol. ≤0,1 %) |
| `CONFIRMADO_ARTEFACTO` | Existe en la salida publicada sin pipeline versionado para re-ejecutarlo (`Pz`, `n_reac`, `n_esfuerzos`, `residuo`) |
| `HIPOTESIS_MODELO` | Decisión de modelo sin fuente definitiva (V_031, G35/G40, cimentación) |
| `PENDIENTE` | Bloqueado/irreproducible con las fuentes disponibles |
| `NO_INCLUIDO` | Catalogado pero NO aplicado en el caso G |

---

## 1. Resultados principales

| Componente | Publicado (artefacto) | Reproducido (directo) | Delta | Estado |
|---|---|---|---|---|
| Columnas (32 tramos FE, 0,70×0,70) | 1.522,31 kN | 1.522,304 kN | 0,006 | `CONFIRMADO_REPRODUCIDO` |
| Vigas V.60/80 (175 tramos FE) | 11.585,48 kN | 11.585,466 kN | 0,014 | `CONFIRMADO_REPRODUCIDO` |
| Vigas V.30/80 (escenario) | — | 11.495,736 kN | 89,73 vs V.60 | `CONFIRMADO_REPRODUCIDO` (Δ=peso V_031 exacto) |
| Muros (40 paneles viewer) | 6.521,26 kN | 4.330,024 kN | **2.191,24 (factor 1,506)** | **`PENDIENTE_ORIGEN_PIPELINE`** |
| Losas (140 paños, e=0,15 m) | ≈9.677,03 kN (implícito de `Pz`) | 9.670,748 kN | 6,28 (0,065 %) | `CONFIRMADO_REPRODUCIDO` |
| **PP elementos (sin losas)** | **−19.629,04 kN** | 17.437,79 kN | = solo muros | — |
| `Pz` (V.60/80) | 29.306,0667 kN | — | — | `CONFIRMADO_ARTEFACTO` |
| `Pz` (V.30/80) | 29.216,3359 kN | — | — | `CONFIRMADO_ARTEFACTO` |

Densidad usada: γ = 24,5166 kN/m³ (del `resumen_PP_ELEMENTOS.txt`; el viewer registra 24,517,
redondeo +0,0004, irrelevante).

## 2. Clasificación del caso G

- `G_EII publicado = PP_losas + PP_vigas + PP_columnas + PP_muros` (elementos; −19.629,04 kN) — artefacto del pipeline externo.
- `G_EII reproducible` (JSON): columnas 1.522,30 · vigas V.60/80 11.585,47 · V.30/80 11.495,74 · muros directo 4.330,02 · losas 9.670,75 → `PP_elementos` 17.437,79 kN (con losas ~27.108,54 kN).
- `diferencia_no_resuelta`: muros, **2.191,24 kN** (4.330,02 calculado vs 6.521,26 publicado; factor 1,506; `PENDIENTE_ORIGEN_PIPELINE`).
- Componentes **confirmados**: columnas, vigas V.60/80, vigas V.30/80, losas. Componentes **pendientes**: muros.
- **`G_EII` NO cerrar**: la discrepancia de muros impide cerrar el total. No se ajusta ningún factor.
- `PP_losas` no figuran en el resumen de elementos; se obtienen implícitas: `Pz(V.60/80) − |PP_elementos| = 9.677,03 kN` (el valor informado es el **directo**: 9.670,75 kN).
- `PM.ADIC` = **NO_INCLUIDA** (catálogo `cargas.caso_G.PM_ADIC_lineal_kg_m`; no aplicada al FE).
- `Q/SC` = **NO_INCLUIDA**; `Q_EII` **no construida** (no existe caso con sobrecarga).
- `peso sísmico W` **no construido**.

## 3. Desglose por tipo y nivel (kN; reproducido)

| Nivel | Columnas (gap) | Vigas V.60 | Muros directo | Losas área/PP |
|---|---|---|---|---|
| CP1S→CP1 | 380,58 (8) | 2.315,15 (35) | 907,22 (8) | 531,02 m² → 1.952,83 |
| CP1→CP2 | 380,58 (8) | 2.315,15 (35) | 907,22 (8) | 531,02 m² → 1.952,83 |
| CP2→CP3 | 380,58 (8) | 2.324,86 (35) | 838,53 (8) | 531,11 m² → 1.953,15 |
| CP3→CP4 | 380,58 (8) | 2.315,15 (35) | 838,53 (8) | 531,02 m² → 1.952,83 |
| CP4 | — | 2.315,15 (35) | 838,53 (8) | 505,54 m² → 1.859,12 |
| **Total** | **1.522,30** | **11.585,47** | **4.330,02** | **2.630,72 m² → 9.670,75** |

Nota: CP2 tiene 35 vigas igual que los demás, pero +9,71 kN (una viga más larga); los muros CP2–CP4
suman menos L que CP1S/CP1 (ΣL 25,27 vs 28,1 m) → −68,69 kN por nivel.

## 4. Muros — discrepancia (BLOQUEO)

| Campo | Valor |
|---|---|
| Muros calculados (geometría versionada) | **4.330,02 kN** |
| Muros publicados (`resumen_PP_ELEMENTOS.txt`) | **6.521,26 kN** |
| Diferencia | **2.191,24 kN** |
| Factor (publicado/calculado) | **1,506** |
| Estado | **`PENDIENTE_ORIGEN_PIPELINE`** |

El publicado **no se reproduce** con la geometría versionada. El generador del `resumen_PP_ELEMENTOS.txt`
**no está versionado** en el repositorio (sin rastro de `columnas_kN/muros_kN/resumen_PP` ni en
`generar_resultados.py`, que es de áreas tributarias del Edificio I, ni en `marco.py`, que es el FE del
Edificio I). Posibles causas a confirmar con el proveedor:

1. longitud/espesor de muro distinto al eje canónico del viewer;
2. contado de las **dos caras** completas (t·L por cara) en vez de un panel único;
3. espesor promedio mayor que el registrado (0,375 vs 0,25);
4. piezas/exclusiones adicionales en el modelo del proveedor.

**No se aplica factor de corrección para forzar la coincidencia** y **`G_EII` NO se declara cerrado**.
En el JSON se separan `G_EII_reproducible`, `G_EII_publicado`, `diferencia_no_resuelta` y las listas de
componentes confirmados (`columnas`, `vigas V.60/80`, `vigas V.30/80`, `losas`) y pendientes (`muros`).

## 5. Losas — delta pequeño documentado

- 140 paños, **todas con e = 0,15 m** (`esp_ctr {0,15: 140}`); `Q_PP_LOSA_020`/ascensor/`e=0,20` solo existen
  en el catálogo, no en el viewer.
- Área por shoelace == área por triangulación (redundancia interna exacta).
- PP directo 9.670,75 vs implícito 9.677,03 kN → Δ 6,28 kN (0,065 %), atribuible a la discretización
  tributaria del proveedor (tol. 1 % → OK). El valor a reportar es el **directo**.

## 6. Vigas V_031 — dos escenarios simultáneos (HIPOTESIS_MODELO, sin elección)

`V_031` (5 elementos, uno por nivel, `por_resolver=true`, `seccion_geom=null`, L=3,05 m c/u) se evalúa
con **ambas** secciones simultáneamente; no se elige definitiva. **Explica íntegramente la diferencia
entre las soluciones V.30/80 y V.60/80**: no hay otra diferencia estructural entre los dos casos FE.

| Sección | A (m²) | PP total (5×L=15,25 m) | PP por viga | Δ publicado |
|---|---|---|---|---|
| V.60/80 | 0,48 | 179,46 kN | 35,89 kN | — |
| V.30/80 | 0,24 | 89,73 kN | 17,95 kN | **89,73 kN** |

El delta de variantes (89,7308 kN) **coincide exactamente** con `Pz(V.60/80) − Pz(V.30/80) = 89,7308 kN`
(verificación 4 OK). Es la única diferencia entre las dos soluciones FE publicadas.

## 7. PM.ADIC y sobrecargas — catálogo no aplicado

`cargas.caso_G` del viewer (NO aplicado al FE, NO en el caso G):
`Q_PP_LOSA_kPa=3,677`, `Q_PP_LOSA_020_kPa=4,903`, `PM_ADIC_lineal_kg_m A260/B260/C200/D1500/E260/F260`,
`SC_lineal_kg_m A500/B300/C200/D100/E200/F500`.

- PP losa → **correlacionable directo** (área neta × kPa, sin tributaria).
- PM.ADIC/SC lineal A–F → correlacionables **con tributaria** por línea centroidal; pendiente de decisión
  de ancho tributario y unidades (kg vs kgf; 1 kgf = 9,80665 N → kN = kg×0,00980665).
- Cargas superficiales/puntuales del plano 700 → correlación PARCIAL (trama regiones).
- El informe `informe_extraccion_pagina_11.md` es del **Edificio I** (contexto; el catálogo EII es el del viewer).

## 8. Riesgos geométricos / pendientes

- **COL_010–012 (CP4)**: columnas CP4 por resolver, excluidas del FE (32 columnas) → `PENDIENTE`.
- **Franja ETAPA ANTERIOR** `x∈[27,95, ≈29,5]`: `RESUELTO_EXCLUIDO` (junta `x=27,85`; la franja es del
  Edificio I). No reactivar `M_005/COL_009-011/BL_001`. `exclusiones.ok=true`.
- **Base/cimentación CP1S**: base en cota −4,01 (hipótesis); cimentación no documentada → `HIPOTESIS_MODELO`.
- **CP2/CP3**: geometría `borrador_no_ejecutable` → `PENDIENTE`.
- **CP4 e_losa**: `e_losa CP4 = null` en borrador (mezcla e15/e20 sin cerrar) → `PENDIENTE`.
- **Elementos sin dueño/sección/material/continuidad**: `V_031` (sección), `COL_010-012 CP4` (elemento),
  `M_006/L_PARKING` verificados ausentes (`exclusiones.ok=true`).
- Nodos FE: 222 (45/45/44/44/44); resumen: columnas 32, muros FE 57, vigas 175.

## 9. Bloqueantes (material y capacidad)

- Densidad 2500 kgf/m³ → el **peso propio no cambia** con G35_10/G40.
- Pero `E_c = 27.805,6 MPa` (G35_10 real, `eii_viewer materiales`) → rigidez, periodos y esfuerzos **sí
  cambian** con G40. **Bloquea EX/EY, Fiber Sections y capacidad**; **no recalcular** hasta resolver.
- `fc_MPa=35`, `fc_cubica_R28_MPa=40` registrados → el grupo debe decidir qué `f'c` usar para capacidad.

## 10. Decisiones que se dejan abiertas al grupo

1. Elegir (o mantener ambos) el escenario V_031.
2. Confirmar el algoritmo de muros del proveedor (para cerrar el tramo de 2.191,24 kN).
3. Resolver G35 vs G40 antes de EX/EY y capacidad.
4. Adoptar PM.ADIC/SC con ancho tributario y unidades.
5. Confirmar cimentación/base (−4,01) y espesores de losa CP4.

## Verificaciones deterministas (9 obligatorias)

| # | Verificación | Resultado |
|---|---|---|
| 1 | Suma de detalles = subtotales (+ redundancia losa shoelace vs triangulos, 140/140, Δmax 0,0 m²) | OK |
| 2 | Subtotales = total elementos (público 19.629,04; repro 17.437,79 solo por muros) | OK (diferencia declarada) |
| 3 | Losas directas vs implícitas de `Pz` (tol. 1 %) | OK (Δ 6,28 kN, 0,065 %) |
| 4 | Δ variantes = peso V_031 | OK (89,7308 == 89,7308) |
| 5 | Sin duplicados (32 col · 175 vigas · 40 muros por nivel; montante 2×(t·L/2) = t·L) | OK |
| 6 | Pendientes/exclusiones fuera de totales (`exclusiones.ok=true`) | OK |
| 7 | Doble ejecución (tras cierre limpio y borrado de temporales) | OK (2 corridas) |
| 8 | SHA-256 idéntico entre corridas | OK (`df7fa3…`) |
| 9 | Modo lectura (sin tocar FE/viewer/publicados) | OK |

## Comparación EI vs EII

| Componente | Edificio I | Estado EI | Edificio II | Estado EII |
|---|---|---|---|---|
| Vigas | 14.803,53 | CONFIRMADO (v2, hash `a158fcb3…`) | 11.585,47 / 11.495,74 | CONFIRMADO_REPRODUCIDO |
| Columnas | 2.045,60 | CONFIRMADO | 1.522,30 | CONFIRMADO_REPRODUCIDO |
| Muros | 330,09 | CONFIRMADO | 4.330,02 (directo) | **PENDIENTE_ORIGEN_PIPELINE** (público 6.521,26) |
| Losas | — (no aparte) | — | 9.670,75 directo | CONFIRMADO_REPRODUCIDO |
| PP elementos | 17.179,23 (cota inferior) | CONFIRMADO | 17.437,79 (repro) / 19.629,04 (público) | **G_EII NO cerrado** (muros pendientes) |
| `Pz` | — | — | 29.216,34 (V.30/80) · 29.306,07 (V.60/80) | CONFIRMADO_ARTEFACTO |

## Fuentes

- `analisis_estructural/edificio_II_casoG_PP_elementos/MODELO_FE_GEOMETRIA_NODOS.json`
- `analisis_estructural/edificio_II_casoG_PP_elementos/eii_viewer.json`
- `analisis_estructural/edificio_II_casoG_PP_elementos/resumen_PP_ELEMENTOS.txt`
- `analisis_estructural/edificio_II_casoG_PP_elementos/solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.60_80.json`
- `analisis_estructural/edificio_II_casoG_PP_elementos/solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.30_80.json`
- Script: `entrega_03_cargas_sismo_capacidad/src/peso_propio_teorico_EDIFICIO_II_v1.py`