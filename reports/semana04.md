# Semana 4 — Cobertura física, cierre de topología y demo Unity

**Informe de entrega del laboratorio Semana 4.** El viewer Unity y sus datos de
resultados están publicados en la rama `modelo-fiel-cobertura-completa` para la
demostración en vivo del 16/09/2026. Las limitaciones del modelo se declaran abajo.

## 1. Estado del modelo (2026-09-16)

| Aspecto | Estado |
|---|---|
| Apoyos artificiales (islas 206/209/212/457) | **0** tras el hito de cierre (Ver Sección 0.8 de `INFORME_COBERTURA_FISICA.md`) |
| Denominación del estado | **MODELO_PARCIAL_DIAGNOSTICO** (la reconciliación G contable NO valida por sí el análisis ni los caminos de carga) |
| `COMB_*.json` (18) | **CALCULADAS**: 9 combinaciones NCh3171 por edificio, regeneradas sobre la topología congelada; equilibrio 9/9 en EI y EII. El exporter publica 13 casos por edificio (G/Q/EX/EY + 9 combinaciones). |
| Núcleo P2 | **excluido** del FE (brecha declarada, ver §4) |
| Pesos de postes/diagonales torre y altura C.H. | PENDIENTE_DE_FUENTE |
| Pruebas de cierre de islas | `tests/islas/test_cierre_islas.py` → 5 OK + 4 subtests OK |
| Hito A1 (mapeo vigas/columnas) | Clasificación 1–4 completa y fix de mapeo aplicado (`V_EI_CP2_x1749` ↔ FE 317) → §3 |

Pipeline vigente regenerado: `python -X utf8 -m src.modelo_fiel.modelo_fe_completo --g --sismo`
→ G 39128.12 kN (Δ 0.0), Q 11016.21 kN, EX/EY corte basal 8927.2448 kN, preflight OK.

## 2. Cobertura por objetos físicos (no FE) — por edificio / nivel / familia

Base: `_cobertura` del exporter sobre la geometría del viewer (objetos físicos;
`con_fuente` = objeto con elementos FE con resultados válidos en los casos
activos; `sin` = SIN_RESULTADO/PENDIENTE, nunca valores de vecinos ni ocultos).
Casos activos: **G/Q/EX/EY y las 9 combinaciones NCh3171** regeneradas para EI y EII.

### 2.1 Edificio I (306 objetos de columnas/vigas/muros) — medición exporter (2026-09-15)

| Nivel | Familia | físicos | con resultado | % | sin (causa) |
|---|---|---|---|---|---|
| CP1S | columnas | 7 | 7 | 100% | – |
| CP1S | vigas | 8 | 7 | 88% | 1 SIN_CORRESPONDENCIA_FE |
| CP1S | muros | 9 | 2 | 22% | 7 SIN_CORRESPONDENCIA_FE |
| P1 | columnas | 18 | 18 | 100% | – |
| P1 | vigas | 10 | 10 | 100% | – |
| P1 | muros | 4 | 0 | 0% | 4 SIN_CORRESPONDENCIA_FE |
| P2 | columnas | 20 | 19 | 95% | 1 SIN_CORRESPONDENCIA_FE |
| P2 | vigas | 39 | **38** | 97% | 1 SIN_CORRESPONDENCIA_FE |
| P2 | muros | 6 | 0 | 0% | 6 SIN_CORRESPONDENCIA_FE |
| P3 | columnas | 34 | 34 | 100% | – |
| P3 | vigas | 50 | 44 | 88% | 6 SIN_CORRESPONDENCIA_FE |
| P3 | muros | 6 | 0 | 0% | 6 SIN_CORRESPONDENCIA_FE |
| P4 | columnas | 32 | 26 | 81% | 6 SIN_CORRESPONDENCIA_FE |
| P4 | vigas | 57 | 47 | 82% | 6 SIN_CORRESPONDENCIA_FE + 4 PENDIENTE_DE_FUENTE |
| P4 | muros | 6 | 0 | 0% | 6 SIN_CORRESPONDENCIA_FE |
| **TOTAL EI** | | **306** | **252** | **82,4%** | 54 sin |

### 2.2 Edificio II (256 objetos) — medición exporter (2026-09-15)

| Nivel | Familia | físicos | con | % | sin |
|---|---|---|---|---|---|
| EII_CP1S | columnas | 8 | 8 | 100% | – |
| EII_CP1S | vigas | 35 | 31 | 89% | 3 SIN + 1 PENDIENTE_DE_FUENTE |
| EII_CP1S | muros | 8 | 8 | 100% | – |
| EII_CP1 / CP2 / CP3 | columnas | 8/nivel | 8 | 100% | – |
| EII_CP1 / CP2 / CP3 | vigas | 35/nivel | 31 | 89% | 3 SIN + 1 PENDIENTE_DE_FUENTE |
| EII_CP1 / CP2 / CP3 | muros | 8/nivel | 8 | 100% | – |
| EII_CP4 | columnas | 9 | 8 | 89% | 1 SIN_CORRESPONDENCIA_FE |
| EII_CP4 | vigas | 35 | 31 | 89% | 3 SIN + 1 PENDIENTE_DE_FUENTE |
| EII_CP4 | muros | 8 | 0 | 0% | 8 PENDIENTE_DE_FUENTE |
| **TOTAL EII** | | **256** | **227** | **88,7%** | 29 sin |

> Nota de coherencia: los 8 muros de EII_CP4 están en `pend_ids` de la topología.
> La regla tomada es **PENDIENTE_DE_FUENTE con precedencia** sobre cualquier
> cobertura geométrica: un objeto pendiente queda rotulado y no adelanta estado
> (mismo criterio que `TOWER_DIAG_*_D2`). Sin esta regla los muros CP4 caerían en
> `con` por tener FE coincidente, mezclando objetos pendientes de fuente.

### 2.3 Losas (áreas, no objetos FE) — reportadas SEPARADAS, cobertura PARCIAL

| Concepto | EI (m²) | Nota |
|---|---|---|
| Física documentada (Ref Semana 2) | 4109,47 | ΣQ_ref = 12328,42 kN |
| Analizada en el FE actual | **3672,07** | −169,05 núcleo − 268,35 retícula previa |
| **Pendiente no aplicada (sin losa FE)** | **437,40** | registro separado de cargas físicas/aplicadas/pendientes |

El "3672,07 m²" es cobertura **parcial**, no total. No se elimina geometría ni
PP/Q para aparentar cobertura.

## 3. Hito A1 — Vigas/columnas sin correspondencia FE, clasificadas y resueltas

### 3.1 Método

Clasificación por objeto (viewer) sobre los `sin_resultado` de `_cobertura`, con
evidencia por vecino más cercano FE del mismo tipo y nivel (script de diagnóstico
regenerable en `AppData\Local\Temp\opencode\diag_sin_resultado_v2.py`). Categorías
del usuario: **(1)** tiene FE válido pero falta mapeo; **(2)** falta representación
FE; **(3)** falta conexión física; **(4)** falta propiedad documental.

### 3.2 Resultado (vigas/columnas únicamente)

| Categoría | EI | EII | Detalle |
|---|---|---|---|
| **(1) FE válido, falta mapeo** | 1 (resuelto) | 0 | `V_EI_CP2_x1749_16.45-19.97_PLA2017-102` ↔ FE tag 317 |
| **(2) Falta representación FE** | 7 col + 14 vig | 1 col + 15 vig | listado en §3.3 |
| **(3) Falta conexión física** | 0 | 0 | – |
| **(4) Falta propiedad documental** | 4 | 5 | `TOWER_DIAG_*` EI; `V_031` ×5 niveles EII |

`SIN_RESULTADO` (columnas+vigas): EI 25 → 24 tras el fix; EII 21. Los restantes
pertenecen a muros (EI sin FE; EII_CP4 pendientes).

### 3.3 Objetos categoría (2) — sin FE, permanecen `SIN_RESULTADO` rotulados

**EI columnas (7):** `COL_EI_CP2_RLE_PILAR_10.00_20.27` (FE col tag 36 en
(10.00,16.15), d=4.12 m); `COL_EI_CP4_S_M1/M2/M3` y `S_J1/J2/J3` (u=47.456/49.794
× v=0.281/9.135/16.347; FE cols 615/623/619/631 a 1.4–2.6 m, ejes distintos).

**EI vigas (14):** CP1S `V_EI_CP1S_x1010_0.700-16.150` (viga vertical u=9.75, FE
más cercana a 8.5 m); P2 `H_EI_CP2_y2027_10.30-17.79_PLA2017-102` (FE a 4.05 m);
P3 6 vigas de base de torre (`H_y1997`, `H_y2057`, `V_x1970`, `V_x2030`,
`V_x2970`, `V_x3030` — el FE modela columnas P3→P4 + anillo P4, sin retícula P3);
P4 6 diagonales `D_EI_CP4_L800_D*_EJ*` (FE a 1.1–1.2 m).

**EII columnas (1):** `EII_CP4_COL_001` (u=0.000, v=0.000, z=11.83; sin FE col).

**EII vigas (15):** `V_029`/`V_030`/`V_032` en los 5 niveles (ala oeste u=−3.35→−0.30;
FE contiguas `V_026`/`V_018`/`V_019` en u≥0, sin tramo oeste).

### 3.4 Fix de mapeo aplicado (categoría 1, 1 objeto recuperado)

En `exportar_esfuerzos_funcional_para_viewer.py`:
- `_cubre_geometricamente` ahora cubre **vigas**: tramo del viewer contenido en un
  FE único de la misma cota → la viga extendida `V_EI_CP2_x1749` (16.45→19.97)
  queda cubierta por el FE tag 317 (16.15→20.27, mismo eje; el FE se extiende a
  los ejes de columnas y0162/y2027). Pasa de `SIN_CORRESPONDENCIA_FE` a
  `con` (`cobertura: geometrica_sin_enlace`). Resultado: **EI P2 vigas 38/39**.
- Precedencia **PENDIENTE_DE_FUENTE antes que cobertura geométrica**: objetos en
  `pend_ids` no se auto-cubren (TOWER_DIAG_*_D2, muros EII_CP4) — quedan
  rotulados como pendientes, sin adelantar estado.

Evidencia de que el resto no es mapeo: los FE cercanos no coinciden en eje
(desfase > tol 2e-3), por lo que su recuperación exigiría remallado del FE
(desplazamiento de ejes) o nueva geometría documentada — fuera de este hito.

## 4. Núcleo P2 excluido (brecha pendiente de representación)

- 16 cuerdas de muro P2 (8 líneas) excluidas; PP de los 4 paneles `P2→P3` =
  330,09 kN pendiente.
- Losas sin FE: P1 588,93 kN (12 losas); P2 núcleo 363,38 kN (121,1 m²) + puente
  19,7 m²; P3 núcleo 907,52 kN; P4 41,06 kN (bordes).
- Conexión faltante: la losa de transferencia P2 está fuera del plano y no hay
  losa FE ni vínculo modelado entre el tramo inferior de las cuerdas y la
  retícula → sin apoyo físico en el modelo actual.

## 5. Unity — requisitos Semana 4 (estado)

| Requisito | Detalle requerido | Estado |
|---|---|---|
| Ficha de selección | viewer_id, elementTag FE, nodos i/j, sección, material, ejes locales, condiciones/restricciones, N, Vy, Vz, T, My, Mz, unidades, caso/combo activo | **Listo en Unity** (`EsfuerzosController.DrawFicha`): + material (fc/ref/nota), reacción G base, desplazamientos nodo i/j del caso, y bloque P–M |
| Deformada | desplazamientos nodales del solver para los casos publicados | **Listo en Unity**: toggle + slider amplificación (1–300), caso activo o envolvente (max\|u\| por componente sobre U1..U4), valores reales no escalados en ficha |
| Diagramas | ≥1 momento validado; ≥1 axial/corte validado | **Validación independiente** (`validar_diagramas_hitob.py`): recomposición U1..U4 desde G/Q/EX/EY, EI 378/378 OK, EII 253/253 OK, peor Δ=6e-6 kN |
| Tributarias | regiones por losa→soporte (`por_viga.json`) | Visualización e inspección disponibles en el viewer; evidencia `capturas/aceptacion7_T6_cargas_apoyos_trib.png` |
| Cargas y apoyos | mostrar G/Q nodos y apoyos reales (48 base + vínculos) | Capas visibles en el viewer; reacción G base (Rx,Ry,Rz,Mx,My,Mz) leída de `apoyos.reacciones_G` en la ficha de columnas; evidencia `capturas/aceptacion7_T6_cargas_apoyos_trib.png` |
| **P–M + D/C** | una columna Y un muro; P y M concurrentes; caso activo; rebar explícito si falta el armado | **Columna y Muro con P–M y demanda concurrente** (§7, `pm_capacidad_demanda_hitob.py`): col. crítica + muro EII tag 76 con armadura **HIPÓTESIS declarada** (no vale como comprobación) |
| Trazabilidad elementTag | OpenSees ↔ Unity ↔ results ↔ sección/capacidad | `correspondencia` mapea viewer_id; ficha unifica tag FE + viewer_id + sección + curva P–M |
| Objetos sin resultados | quedan `SIN_RESULTADO`/`PENDIENTE` (nunca vecinos ni ocultos) | Cumplido en el exporter |

Combinaciones: la curva P–M del demand point usa U1..U4. Con la topología ya
congelada (2026-09-14), las **9 combinaciones se regeneraron** sobre la topología
cerrada (islas + grillaje torre P4) para EI y EII: 9/9 equilibrio OK por edificio
(`U1=1,2G+1,6Q`, `U2/U3=1,2G+Q±1,4S`, `U4=0,9G±1,4S`). El exporter quedó
desbloqueado y se emitió el perfil único
`viewer_unity/.../edificios/{I,II}/results/esfuerzos_FE_EDIFICIO_{I,II}.json`
con respaldo automático (`..._ANTERIOR_20260914_*.json`); `combos_estado=
CALCULADA` y esquema NCh3171 `utilizables=true` (13 casos por elemento,
incluida `envolvente_NCh3171`).

## 6. Pendientes y prohibiciones vigentes

1. [x] ~~No correr combinaciones hasta cerrar la topología~~
      → **cumplido**: 9 combos regenerados (EI+EII), exporter desbloqueado.
2. Núcleo excluido: no eliminar geometría/PP/Q para aparentar cobertura.
3. Sin nuevas fijaciones verticales ni vínculos por proximidad para estabilizar.
4. Altura C.H., armaduras reales, parámetros sísmicos normativos (sismo de la
   consigna) siguen PENDIENTE_DE_FUENTE/DEFINICION.
5. Topología Semana 4 **congelada** desde su snapshot
   (`modelo_fiel/MODELO_FE_COMPLETO_FUNCIONAL/CONGELAMIENTO_TOPOLOGIA_SEMANA4.json`,
   sha256 de topología/preflight registrados): no se modifican nodos, elementos,
   restricciones ni cargas del perfil hasta después de la demo.

## 7. Trabajo completado y pendientes

- [x] **Hito A1**: clasificar todas las vigas/columnas `SIN_CORRESPONDENCIA_FE`
      (categorías 1–4) y resolver el mapeo demostrable (`V_EI_CP2_x1749` ↔ 317).
- [x] **Regeneración de cargas**: G/Q/EX/EY listos + **9 combinaciones**
      recalculadas sobre la topología congelada (EI 378 tags / EII, equilibrio
      9/9); exporter desbloqueado y perfil único emitido con respaldo.
- [x] **Hito B — P–M y demanda concurrente** (`pm_capacidad_demanda_hitob.py`):
      todas las columnas (por_elemento), caso demostrado = max(D/C) entre U1..U4
      con **P y M del mismo caso**; columna crítica EI `COL_EI_CP1S_C_E_0.73_1.35`
      (tag 18, U4_EY_NEG, P=27,4 kN, M=1359,8 kN·m, Mu=895,4, **D/C=1,5187**) y
      EII tag 10 `EII_CP3` (U2_EX_POS, P=622,4, M=2105,1, Mu=1030,4, **D/C=2,0429**);
      muro EII tag 76 (`EII_CP1S_M_001`, U3_EY_NEG, P=550,4, M=8661,2, Mu=7412,9,
      **D/C=1,1684**) con armadura HIPÓTESIS (`EVALUACION_HIPOTESIS_BLOQUEADA_ARMADURA`).
      Tests `tests/unity_esfuerzos/test_pm_capacidad_demanda_hitob.py` 5 OK.
- [x] **Hito B — validación independiente** (`validar_diagramas_hitob.py`): sin
      reutilizar el exportador, recomposición de U1..U4 desde G/Q/EX/EY, peor
      Δ=6e-6 kN; salidas `validacion_diagramas_{I,II}.json` y `.md`. Tests 4 OK.
- [x] **Hito B — Unity C#**: en `EsfuerzosController.cs` (compila 4/0 en Unity
      6000.5.10f1): clases PM + `CargarPMCapacidad`, deformada real amplificada
      (toggle + slider), ficha extendida (material, reacción base, desplazamientos,
      bloque P–M con mini-plot) — **verificado interactivo 2026-09-16**: curva P–M +
      caso activo + D/C visibles y sincronización Inspección↔ficha; 14 capturas
      `aceptacion7_*`.
- [x] **Intervalo físico sub-tramo** (`reconciliar_intervalo_x1749.py`): la viga
      física `V_EI_CP2_x1749_16.45-19.97` está **contenida** en el FE tag 317
      ([16,15;20,27] ⊇ [16,45;19,97]) y su diagrama interno es **lineal** (residuos
      axial/cortante/torsión nulos en los 13 casos) → rotulo **FE_COMPLETO** sin
      inventar correspondencia; `PENDIENTE_DE_FUENTE` de carga de voladizo conservado
      (N[U1]=0). Tests 5 OK.
- [x] **`guia_demo_semana04.md`** actualizada al Hito B (flows A–D + checks).
- [ ] **Hito A2**: repre de muros EI P1–P4 o declararlos pendientes (23 objetos).
- [ ] Selección distribuida ≥2 objetos/nivel durante la demostración en vivo.

Evidencia numérica regenerable (Hito B, una línea por cadena):
`python -X utf8 -m tests.unity_esfuerzos.test_exportar_esfuerzos_funcional_viewer`
(exporter 26 OK, combos CALCULADA),
`python -X utf8 -m tests.islas.test_cierre_islas` (5 OK + 4 subtests),
`python -X utf8 -m tests.unity_esfuerzos.test_pm_capacidad_demanda_hitob` (5 OK),
`python -X utf8 -m tests.unity_esfuerzos.test_validar_diagramas_hitob` (4 OK) y
`python -X utf8 -m tests.unity_esfuerzos.test_reconciliar_intervalo_x1749` (5 OK).
Suite Hito B total: **45 OK (+ 4 subtests de islas)** (exporter funcional 26 + islas 5 +
pm 5 + validación 4 + reconciliación 5). Con las regresiones viewer
`test_exportar_esfuerzos_viewer` (12) y `test_geometria_overlay_fiel` (8), y los nuevos
`test_aceptacion_diagramas_extremos` (9) y `test_correspondencia_3d_columnas` (6),
`tests/unity_esfuerzos` + `tests/islas` suman **80 OK (+ 4 subtests)**; la suite completa
`python -m pytest tests -q` = **108 passed + 4 subtests**.

## 8. Trazabilidad Hito B (cadenas regenerables 2026‑09‑14)

| Cadena | Entrada | Producto | Regeneración |
|---|---|---|---|
| Perfil único | `MODELO_FE_COMPLETO_FUNCIONAL` (topología congelada, sha256 §6) | `viewer_unity/.../edificios/{I,II}/results/esfuerzos_FE_EDIFICIO_{I,II}.json` (9 combos CALCULADA, 13 casos, deformada/apoyos/materiales) | `python -X utf8 -m src.modelo_fiel.modelo_fe_completo --g --sismo` + exporter (respaldo automático `..._ANTERIOR_*.json`) |
| P–M + demanda | perfil (fuerzas U1..U4) + DEMO_RC + armadura hipótesis muro | `results/unity_hitob/pm_capacidad_demanda_{I,II}.json` → `viewer_unity/.../results/pm_capacidad_demanda_{I,II}.json` + `resumen_pm_demanda_hitob.txt` | `python -X utf8 -m src.unity_esfuerzos.pm_capacidad_demanda_hitob` |
| Validación diagramas | `COMBINACIONES_NCH3171` + perfil | `validacion_diagramas_{I,II}.json` + `validacion_diagramas_hitob.md` (muestra jurado: EI viga tag 202 `H_EI_CP1S_y1695...`, columna tag 25, EII viga 231, columna 49, muro 76) | `python -X utf8 -m src.unity_esfuerzos.validar_diagramas_hitob` |
| Reconciliación intervalo | geometry/E_I/P2.json (`V_EI_CP2_x1749_16.45-19.97`) + perfil tag 317 | `reconciliacion_intervalo_x1749.json` (rotulo FE_COMPLETO, residuos nulos 13/13, pendiente de fuente conservado) | `python -X utf8 -m src.unity_esfuerzos.reconciliar_intervalo_x1749` |
| Unity C# | perfil + `pm_capacidad_demanda_*.json` | `EsfuerzosController.cs` (CargarAuxiliares, CargarPMCapacidad, deformada, ficha, P–M) — compila en Unity 6000.5.10f1 (batchmode, 0 errores) | abrir `viewer_unity` y togglar "Deformada amplificada" / ficha de cualquier columna/muro/viga |

Pendientes conservados y visibles (regla: nunca vecinos ni ocultos, sin inventar fuentes):
armaduras reales de muros (hipótesis declarada y bloqueada para P–M), núcleo P2
excluido, losas sin FE (437,40 m²), altura C.H./parámetros sísmicos, y carga de
voladizo P2 no transferida (`V_EI_CP2_x1749`, N[U1]=0). Todo queda rotulado en el
viewer o en las salidas JSON/MD de arriba.
