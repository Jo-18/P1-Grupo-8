# Auditoría inicial — Entrega 03 (cargas gravitacionales, sismo pseudoestático y capacidad)

> **Alcance:** esta entrega se trata como **una sola entrega integral** (jueves + viernes).
> Los 11 puntos se desarrollan como un proceso único; el reparto en días es solo de
> defensa oral. Se corrige la versión previa en lo referente a la clasificación de
> casos, método sísmico, "completitud" del caso G, peso sísmico, combinaciones,
> reproducibilidad y prioridades.

---

## 1. Estado del caso G — reclasificación

### 1.1 Edificio I (verificado en código, NO es un resultado "completo")

Declaración corregida:

> **`G_EI` actual = PP losas + PM.ADIC** (ΣFz = **−25.227,73 kN**),
> **sin PP explícito de vigas, columnas y muros**.

Evidencia en el código (`analisis_estructural/edificio_I/src/analisis/fe/`):
- `resolver.py:26–50` aplica **solo `ops.load` nodal** (carga de losas por tributaria);
- **no hay** `selfWeight`, `eleLoad`, `setMass` ni `mass` en el modelo
  (grep verificado); por lo tanto el peso propio de vigas/columnas/muros **no está
  incorporado**.

Desglose por nivel del caso G publicado (del JSON `resultado_primera_ejecucion.json`, eje vertical −Z; kN):

| Nivel | PP losas | PM.ADIC | Subtotal | Acumulado |
|---|---|---|---|---|
| P4 | 3.367,53 | 1.867,23 | 5.234,76 | 5.234,76 |
| P3 | 3.371,16 | 2.344,61 | 5.715,77 | 10.950,53 |
| P2 | 3.123,03 | 2.143,66 | 5.266,69 | 16.217,22 |
| P1 | 3.698,56 | 2.814,78 | 6.513,34 | 22.730,56 |
| CP1S | 1.423,30 | 1.073,85 | 2.497,15 | **25.227,73** |

- Total **PP losas = 14.983,58 kN**; **PM.ADIC = 10.244,15 kN** (suma por nivel);
  **Σ = 25.227,73 kN**, consistente con `F_total_kN = [0,0,−25227.732,0,0,0]`.
- Los valores al 2º decimal difieren ±0,01–0,02 por redondeo de la tabla por nivel
  (10.244,37 ≈ 10.244,15 + redondeo acumulado); el total publicado es la referencia.

### 1.2 PP de elementos del Edificio I — modo auditoría (NO aplicado al FE)

Se calculó el PP teórico de vigas, columnas y muros a partir de la geometría
(sección, longitud/área, densidad, nivel, tipo de elemento) **en modo lectura**, sin
modificar el modelo.

**> El total v1 de 24.116,51 kN queda DESCARTADO.**

La versión 1 (`results/peso_propio_teorico_EDIFICIO_I.json`) se rechazó por tres
errores metodológicos: (a) los perfiles metálicos `300x300x20` y `300x300x5` se
trataron como macizos `B×H` (0,09 m²) en lugar de tubulares
`B×H−(B−2t)(H−2t)`; (b) los tramos verticales ficticios `BASE→P_n` (columnas y
muros que solo aparecen en un nivel) se sumaron al total; (c) el agrupamiento de
muros por tolerancia 0,35 m no seguía la regla canónica del motor FE.

**Resultado v2 confirmado** (`results/peso_propio_teorico_EDIFICIO_I_v2.json`,
determinista, `_hash.txt` verificado; hash actual `a158fcb3…e7a515` tras incorporar decisiones D1–D7):

| Componente | PP [kN] | Nota |
|---|---|---|
| Vigas | 14.803,53 | 137 vigas confirmadas; excluye V.S.I. (PENDIENTE_SECCION) y muro M.H.A. e=30 erroneo en lista de vigas |
| Columnas | 2.045,60 | 43 tramos FE reales (P. 70x70, h=3,96 m): solo CP1S→P1, P1→P2, P2→P3 |
| Muros | 330,09 | 4 paneles reales P2→P3 (2×e=0,3; 2×e=0,2) por regla canónica FE |
| **Total confirmado** | **17.179,23** | |

**Fuera del total confirmado** (por separado, informativo):

| Concepto | PP [kN] | Estado |
|---|---|---|
| Hipótesis FE base→nivel, columnas | 4.223,82 | informativo; tramos `base_…` (cimentación no documentada) |
| Hipótesis FE base→nivel, muros | 3.675,18 | informativo |
| Muros de contención CP1S | 554,54 | HIPOTESIS_CIMENTACION (h_sotano=3,0 m); M_001 e=0,2 panel 25,25 m = 371,43 kN; M_002 e=0,3 panel 8,299 m = 183,12 kN |
| Pendientes (63) | 0,0 | pp null, fuera del total |
| No incluidas (1) | 0,0 | fuera del total |

**Desglose por nivel del total confirmado (kN):**

| Nivel | Vigas (n) | Columnas (n_tramos) | Muros (n_paneles) |
|---|---|---|---|
| CP1S | 883,19 (6) | 0 | 0 |
| P1 | 2.746,06 (10) | 333,00 (7) | 0 |
| P2 | 3.384,47 (36) | 856,30 (18) | 330,09 (4) |
| P3 | 3.937,57 (44) | 856,30 (18) | 0 |
| P4 | 3.852,25 (41) | 0 | 0 |

**Comparación v1 → v2 (antes/después):**

| Componente | v1 (descartado) | v2 (confirmado) | Diferencia y causa |
|---|---|---|---|
| Vigas | 14.808,47 | 14.803,53 | −4,94: V.S.I. pasa de metálica provisional a PENDIENTE_SECCION |
| Columnas | 5.674,98 | 2.045,60 | −3.629,38: metálicas bajadas de macizo (0,09→tubular) y tramos base→P4/P3/P2 excluidos |
| Muros | 3.078,51 | 330,09 | −2.748,42: solo paneles entre niveles consecutivos con línea canónica (4); el resto PENDIENTE_TRAMO |
| Muros contención | 554,54 | 554,54 | igual monto, reclasificado HIPOTESIS_CIMENTACION (fuera del total) |
| **Total** | **24.116,51** | **17.179,23** | −6.937,28 (28,8 %) |

**Precisión metodológica — verificación de no doble conteo (v2):**

- **Columnas:** se usan los **tramos reales FE** de `columnas_tramos_ei.json`
  (`col_{u}_{v}_{nivel}`, sin `_base_`): 7 CP1S→P1 + 18 P1→P2 + 18 P2→P3 = **43**,
  cada `elemento_id` instanciado una vez (verificados sin duplicados en 97 tramos).
- **Perfiles metálicos:** `300x300x20` y `300x300x5` → **tubular confirmado**
  `A=B×H−(B−2t)(H−2t)` (0,0224 y 0,0059 m²); nunca 0,09 m² macizo (verificación 1).
  Los metálicos que solo aparecen en un nivel (CP2:1, CP3:16, CP4:8) → `pp null` +
  `PENDIENTE_TRAMO` (lámina 800 de continuidad pendiente); `P.M.I.` sin dimensiones →
  además `PENDIENTE_SECCION`.
- **Hormigón P3→P4:** el FE NO instancia el tramo (P4 desplazado +0,181 m, desfase
  físico documentado); 18 columnas de P4 → `PENDIENTE_TRAMO`, sin generar
  `BASE→P4` confirmado (verificación 2).
- **Muros:** agrupación por línea canónica `round(u,v,3)` + espesor, igual que
  `marco.py`; solo descienden entre niveles consecutivos que comparten la línea
  (4 paneles reales P2→P3). Los montantes FE 2×(t/2)×L suman t×L: el panel se cuenta
  **1 vez** con área total (verificación 6).
- **Vigas:** un registro por id y nivel, longitud = polilínea del candidato; la
  `V_S I. 20/150` (`H_EI_CP1S_y2732`) queda `PENDIENTE_SECCION` y
  `V_EI_CP1S_x1010` (`M.H.A. e=30` = muro) se excluye (`NO_INCLUIDA`).
- Densidades usadas: concreto **24,5166 kN/m³** (2500 kgf/m³ × 0,00980665) y acero
  **76,982 kN/m³** (7850 kgf/m³ × 0,00980665).

**Pendientes (63) — para no fabricar datos:**

- 1 viga: `V.S.I. 20/150` → `PENDIENTE_SECCION`; hipótesis de grupo D5 (HA 0,20×1,50 m, pp≈157 kN) para análisis.
- 25 columnas metálicas tramo simple → `PENDIENTE_TRAMO` (8 `P.M.I.` además
  `PENDIENTE_SECCION`).
- 18 columnas hormigón P4 → `PENDIENTE_TRAMO` (tramo P3→P4 no instanciado; desfase P4 +0,181 m, D4).
- 19 muros mononivel o sin par en nivel consecutivo → `PENDIENTE_TRAMO`
  (D2: cajas P2→P3→P4 solo si coincidencia plena; los paneles de una planta NO pasan a tramo continuo).
- 1 no incluida: muro `M.H.A. e=30` listado como viga → se contabiliza como parte del muro eje F (D6).

**Decisiones adoptadas (D1–D7) y reconciliación L800 vs L801/L802 — ver
`docs/RESOLUCION_PENDIENTES_PP_EI.md`:**

- D1: v2 = COTA INFERIOR (PP_confirmado 17.179,23 kN; pendientes/provisional sin cuantificar).
- D2: cajas de ascensor por coincidencia plena (PENDIENTE_TRAMO hasta verificarla).
- D3: sin tramos sintéticos base→nivel.
- D4: desfase P4 +0,1813 m → corrección propuesta `v'=v−0,1813` en rejillas horizontales de P4 (no aplicada).
- D5: V.S.I. 20/150 = HIPOTESIS_GRUPO HA 0,20×1,50 m (pp≈157 kN); incluir/excluir en sensibilidad.
- D6: `V_EI_CP1S_x1010` = muro eje F; no-duplicación verificada.
- D7: banda 20,3–21,2 MN = SOLO_SENSIBILIDAD (no PP adoptado).
- **Reconciliación vectorial:** la banda estricta del marco F–G–H (P3→P4) en la lámina 800 **no tiene
  diagonales de acero**; las líneas m≈+1,573/−1,706 de L800 son **RLA-EJES** (ejes de estructura, apex
  ~cota 9,86). Los paneles X P3→P4 de la torre G–H (m=±0,961, θ=43,87°/136,13°, panel 4,12×3,96 m,
  L=5,714) están en las láminas **801/802** y coinciden con el viewer. La identificación previa era correcta;
  el total confirmado no cambia.

**Consecuencia:** el caso G del Edificio I **no debe** describirse como completo. Para
poder comparar los casos G de ambos edificios, la suma `PP losa + PM.ADIC +
PP elementos` (25.227,73 + 17.179,23 ≈ **42.407 kN**) es orientativa y requiere además
validar la interacción de subida de cargas (la carga de losas ya reposa en el modelo;
el PP de elementos no debe sumarse a ciegas sin reanalizar).

### 1.3 Edificio II — componentes del caso G (artefactos publicados)

Del "resumen_PP_ELEMENTOS.txt" y `eii_viewer.json`:

| Componente | PP [kN] | Estado |
|---|---|---|
| PP columnas | 1.522,31 | incluido en soluciones publicadas |
| PP vigas | 11.585,48 | incluido |
| PP muros | 6.521,26 | incluido |
| **Subtotal PP elementos** | **19.629,04** | |
| PP losas (3,677 kPa; a definir con geometría) | ~9.677 | incluido (implícito en Pz) |
| PM.ADIC (lineal kg/m, por viga del plano) | pendiente | **NO incluido en caso G** |
| Q/SC (lineal kg/m) | pendiente | **NO incluido en caso G** |

- Soluciones publicadas: `Pz(V.60/80)=29.306,07 kN`, `Pz(V.30/80)=29.216,34 kN`
  (Δ=89,73 kN ≈ 5 vigas V_031 por nivel). Sección de la viga `V_031` = `por_resolver`.
- Material publicado en artefactos EII: `G35_10` (fc=35 MPa, E=27.805,6 MPa,
  γ=24,517 kN/m³, "real, fuente DXF 100"); la configuración interna del motor de
  reproducción declara **G40** como hipótesis del grupo. **No presentar G35/G40 como
  definitivo** hasta fijarlo con fuente (ver §7).

> **No comparar directamente los totales de `G_EI` y `G_EII` cuando los casos no tengan
> los mismos componentes.** Tabla comparable de casos G en §2.

---

## 2. Vista comparada de casos G (I vs II) — al nivel de componente

| Componente | Edificio I | Edificio II |
|---|---|---|
| PP losas [kN] | 14.983,58 (en FE) | ~9.677 (en soluciones; desde plano 3,677 kPa a confirmar) |
| PM.ADIC [kN] | 10.244,15 (en FE) | pendiente de mapeo (lineal kg/m) |
| PP vigas [kN] | 14.808,47 (auditoría, NO en FE) | 11.585,48 (en FE) |
| PP columnas [kN] | 5.674,98 (auditoría, NO en FE) | 1.522,31 (en FE) |
| PP muros [kN] | 3.078,51 (+554,54 contención; auditoría, NO en FE) | 6.521,26 (en FE) |
| Durabilidad real de las magnitudes | valores desglosados | valores desglosados |

---

## 3. Clasificación correcta de casos (nomenclatura)

- `G` = cargas **permanentes** (PP + PM.ADIC).
- `Q` = carga **viva / sobrecarga de uso** (SC). La `SC` es **componente de Q**, NO un
  "faltante del caso G" (corrección sobre la versión previa).
- `EX`, `EY` = acción sísmica (sentido positivo en X / Y).
- `−EX`, `−EY` = **sentidos opuestos**.
- Se conservan **los casos elementales con su signo** para la superposición.

---

## 4. Método sísmico requerido: pseudoestático

La pauta pide **sismo pseudoestático**; el análisis modal/espectral se deja como
**ampliación futura**. Cadena de cálculo que debe completarse (sin pasos inventados):

1. **Peso sísmico** `W` = Σ por nivel de (PP losa + PP vigas + PP columnas + PP muros +
   PM.ADIC + **fracción normativa de Q**).
2. **Coeficiente sísmico / corte basal** `Q0` (requiere zona sísmica, tipo de suelo,
   categoría de importancia, R/coeficiente — ver §7).
3. **Distribución vertical** entre pisos (proporcional a peso y altura).
4. **Fuerza horizontal por nivel** aplicada a cada losa (→ traslada a nodos/rigid??).
5. Casos `±EX` y `±EY`.
6. **Desplazamientos, reacciones y derivas**.

Unidades a distinguir por el código:
- **peso sísmico [kN]** (fuerza),
- **masa [kN·s²/m]** (m–kN–s), para la versión dinámica (ampliación futura),
- **fuerza sísmica por nivel [kN]**.

> La **excentricidad accidental / torsión** se incorpora **solo si la norma adoptada lo
> exige**; queda en `null` en `config/parametros_pendientes.json`.

---

## 5. Peso sísmico — construcción parametrizada

`W(totales) = Σ_nivel ( PP_losa + PP_vigas + PP_columnas + PP_muros + PM.ADIC +
f_Q·Q )` con `f_Q` (fracción normativa de la sobrecarga que entra al peso sísmico):

- **`f_Q` queda en `null`** en `config/parametros_pendientes.json` hasta tener fuente
  (norma/ETOG/memoria) o **decisión explícita del grupo** registrada.
- Del caso G actual del EII **no** debe inferirse peso sísmico: el G del EII no incluye
  PM.ADIC ni SC, y el G del EI no incluye PP de elementos. El peso sísmico se
  construye **por componente**, no por "el Pz del caso G".

---

## 6. Combinaciones — sin asumir LRFD/ASCE

- **No** se adopta LRFD/ASCE como decisión tomada.
- Orden de búsqueda de la fuente normativa de combinaciones y factores:
  1) pauta de la asignatura; 2) documentos entregados; 3) ETOG; 4) memoria de cálculo;
  5) norma chilena (NCh/NDS).
- Si no aparece → se registran como **`pendientes_de_fuente`** (en
  `config/parametros_pendientes.json`) y el código **debe detenerse** con mensaje claro
  antes de generar superposición con factores inventados.
- La superposición **inicial y verificada** y las **envolventes** se harán una vez
  definidos los factores; mientras tanto se documenta la **matriz de casos elementales**
  con signos: `G`, `Q`, `EX`, `−EX`, `EY`, `−EY`.

---

## 7. Capacidad (Fiber Sections, M–φ, P–M) — prioridad alta

- **No existe** código Fiber / M–φ / P–M en el repo (solo hay secciones elásticas:
  `secciones.py`, `hipótesis.py` con ACERO/Estribos marcados como provisionales).
- Datos requeridos (deben venir de **fuente** o quedar como **hipótesis del grupo
  explícita**; NO inventar): dimensiones, recubrimiento, `f'c`, `fy`, comportamiento
  confinado/no confinado, armadura longitudinal (posición y área), estribos,
  discretización de fibras, ejes locales de la sección.
- Pendientes registrados cuando su valor es `null`: `fy`, `recubrimiento`,
  `armadura_columna`, `armadura_muro`, `seccion_V031`,
  `material_definitivo_hormigon_EI`, `material_definitivo_hormigon_EII`.
- Entregables esperados: curvas `M–φ` y `P–M` para **columna y muro** (ver §10).

---

## 8. Parámetros pendientes → `config/parametros_pendientes.json`

Registro **único** de bloqueos, con esquema por parámetro:
`valor | unidad | estado | fuente | necesario_para | observacion`, **`valor: null`**
inicial para todos (no se rellenan con hipótesis silenciosas).

Dominios y entradas (18 en total):
1. **Normativas/combos:** `norma_combinaciones`, `factores_combinacion`.
2. **Sísmicos:** `zona_sismica`, `tipo_suelo`, `categoria_importancia`,
   `amortiguamiento`, `factor_reduccion_R`, `coeficiente_sismico_o_base`,
   `excentricidad_accidental`.
3. **Peso sísmico:** `fraccion_Q_peso_sismico`.
4. **Capacidad:** `fy`, `recubrimiento`, `armadura_columna`, `armadura_muro`.
5. **Modelo EII:** `seccion_V031`, `material_definitivo_hormigon_EI`,
   `material_definitivo_hormigon_EII`, `base_cimentacion_EII`.

Regla de uso: el código de esta entrega que necesite alguno de estos valores debe
**verificar ≠ null** y abortar con mensaje claro si está pendiente.

---

## 9. Reproducibilidad del Edificio II

### 9.1 Situación

Solo los **artefactos de salida** del EII están versionados
(`analisis_estructural/edificio_II_casoG_PP_elementos/*`: `MODELO_FE_GEOMETRIA_NODOS.json`,
`eii_viewer.json`, soluciones FE, `resumen_PP_ELEMENTOS.txt`). El pipeline de
levantamiento/adaptación vive en **`laboratorio_semana2/` (no versionado)** y en
parte en el temp externo.

### 9.2 Tabla de fuentes externas (para decidir qué incluir en Git)

| Archivo externo requerido | Información exacta que aporta | Tamaño | Origen | ¿Versionado? | ¿Fuente o generado? | Ubicación canónica propuesta | ¿Incluir en Git? |
|---|---|---|---|---|---|---|---|
| `EII_2024_22.zip` | geometría EII (planos 2024_22, 5 niveles) | 8,06 MB | compañera (2026-09-03) | NO | fuente (entrada) | `raw/eii/2024_22/EII_2024_22.zip` | candidato (PDF/DXF de planta) |
| `01_niveles/CP*)json` (EII_CP*_cielo_piso*_borrador.json) | planta por nivel (losas/vigas/columnas/muros/aberturas) | ~0,13–0,18 MB c/u | levantamiento laboratorio | NO | generado (derivado del plano) | `datos/levantamiento/eii/niveles/*.json` | sí (determinista, pequeño) |
| `CUADRO_SECCIONES_MATERIALES_CARGAS_EII.md` | secciones/materiales/cargas EII (incl. V_031, armaduras) | 10,6 kB | laboratorio | NO | fuente (recopilación) | `raw/eii/CUADRO_SECCIONES_MATERIALES_CARGAS_EII.md` | **sí (imprescindible)** |
| `EII_CPn_..._adaptado_contrato_comun.json` (5) | geometría adaptada (contrato común con motor) | ~58–70 kB c/u | adaptación | NO | derivado | `datos/eii/adaptados/*.json` | sí |
| `LISTA_UNICA_DATOS_FALTANTES_EII.md` | brechas conocidas (V_031, armaduras) | 6,3 kB | laboratorio | NO | fuente/decisión | `raw/eii/LISTA_UNICA_DATOS_FALTANTES_EII.md` | sí |
| `informes/informe_pendientes_EII_CPn.md` | pendientes por nivel | ~6–18 kB c/u | laboratorio | NO | derivado | (documentación) | opcional |
| `datos/cargas/informe_extraccion_pagina_11.md` + catálogos `catalogo/asignacion/lineales/puntuales` | cargas G/Q (PP losa, PM.ADIC, SC por viga y por plano) | ~28 kB | extracción página 11 | NO | fuente | `raw/eii/cargas/` | sí (byte a byte, con hash) |
| `eii_viewer.json` (soluciones) | materiales reales usados (G35), cargas, Pz | 249 kB | generado | NO | generado | (ya versionado en `edificio_II_casoG_PP_elementos/`) | ya incluido |

### 9.3 Mínimo necesario para reproducir el EII

1. **Geometría FE EII**: 5 `EII_CPn_..._adaptado_contrato_comun.json` + `CUADRO` de
   secciones/materiales.
2. **Cargas G y Q**: `informe_extraccion_pagina_11.md` + catálogos de asignación/lineales/puntuales.
3. **Peso sísmico**: fruto de 8.1+8.2 + `fraccion_Q_peso_sismico`.
4. **Sismo EX/EY**: `parametros_pendientes.json` §8.2.
5. **Secciones y capacidad (M–φ, P–M)**: `CUADRO_SECCIONES_MATERIALES_CARGAS_EII.md`
   (V_031, armaduras) — sin esto no hay Fiber.

**Propuesta (NO copiar todavía):** incorporar a Git únicamente
`CUADRO_SECCIONES_MATERIALES_CARGAS_EII.md`,
`LISTA_UNICA_DATOS_FALTANTES_EII.md`, los 5 JSON adaptados, el informe+catálogos de
cargas y (opcional) el zip de planos. Confirmar tamaño total y licencia con el profesor
antes de incluir el zip.

### 9.4 Viabilidad de reconstruir el pipeline EII con el motor del Edificio I

- **Favorable:** el contrato común (`EII_CPn_adaptado_contrato_comun.json`) está
  diseñado para alimentar el motor del EII; el motor EI acepta geometría por JSON
  (`main_fe.py`), por lo que es **conceptualmente viable** reanalizar EII con el mismo
  motor si se adaptan secciones/materiales (viga `V_031` fijada, materiales reales).
- **Riesgos:** (a) `EDIFICIO_II.geometria_disponible=False` y `modelo_entrada` en el
  motor ajeno a EII; (b) la transferencia de carga de losas a vigas (tributaria) y los
  apoyos/base del EII deben **revalidarse** contra las soluciones publicadas
  (verificación de reproducción, no solo de éxito); (c) `pyj`/paths del `config_fe.py`
  están orientados a EI.
- **Conclusión:** reconstrucción viable como **tarea verificable** (comparación de
  `Pz` y desplazamientos con `solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.60_80.json`),
  siempre recargando geometría+materiales desde las fuentes de §9.2 y validando
  componentes del caso G antes de comparar.

---

## 10. Prioridades de la entrega integral (única tabla)

| Prioridad | Bloque | Estado | Desbloqueado por |
|---|---|---|---|
| **P0** | Desbloqueos de datos/fuentes (sísmicos, combos, armadura, V_031, material G35/G40) | bloqueado | `config/parametros_pendientes.json` + decisiones profesor/grupo |
| **P1** | Casos G y Q completos (PP de elementos al FE; PM.ADIC/SC planos) | EI: aplicar PP auditoría (~17.179 kN confirmado) y reanalizar; EII: mapear PM.ADIC/SC | decisión sobre reanálisis EI; fuentes planos |
| **P2** | Sismo pseudoestático (`W`, `Q0`, distribución vertical, ±EX/±EY, derivas) | pendiente | P0 (sísmicos) + P1 (peso sísmico por componente) |
| **P3** | Superposición inicial y verificada + envolventes | pendiente | P0 (combos) + P1 + P2 |
| **P4** | Fiber Sections de columna y muro + M–φ + P–M | inexistente (crear) | P0 (armadura/fy/recubrimiento/material) |
| **P5** | Primera evaluación demanda/capacidad | pendiente | P3 + P4 |
| **P6** | Material completo para presentación oral | pendiente | P0–P5 |

---

## 11. Correcciones editoriales aplicadas a la versión previa

- "FALTA tsunami" → corregido (no es requisito; se elimina la marca).
- "Pakete" → "Paquete".
- "reprodicción" → "reproducción".
- G35/G40 ya **no** se presentan como decisión definitiva (material en `null`).
- `Q/SC` ya **no** se clasifica como sismo: `Q` es carga viva; el sismo es `EX/EY/−EX/−EY`.
- El caso G del EI ya **no** se declara completo (ver §1.1).
- La entrega ya **no** se divide en "jueves/viernes": es **integral** (§Introducción).

---

## 12. Entregables de esta auditoría

1. `README.md` (alcance único integral, clasificación, método, estructura).
2. `docs/AUDITORIA_INICIAL.md` (este documento).
3. `config/parametros_pendientes.json` (18 bloqueos, `valor:null`).
4. `src/peso_propio_teorico_EDIFICIO_I.py` (v1, descartada) +
   `src/peso_propio_teorico_EDIFICIO_I_v2.py` (v2, vigente) +
   `results/peso_propio_teorico_EDIFICIO_I_v2.json` + `_hash.txt`
   (PP de elementos EI, modo auditoría, determinista).
5. Tabla de fuentes externas del EII y evaluación de viabilidad de reproducción (§9).
6. Tabla de prioridades P0–P6 (§10).
7. Lista de decisiones abiertas (§13).

---

## 13. Decisiones que se requieren (profesor / grupo)

1. **Norma de combinaciones y factores** (país/norma) — sin esto, P3 bloqueado.
2. **Parámetros sísmicos**: zona, tipo de suelo, categoría de importancia,
   R/coeficiente; y **si la torsión/excentricidad accidental aplica**.
3. **Fracción de Q en el peso sísmico** (`f_Q`).
4. **¿Reanálisis del Edificio I con PP de elementos (~17.179 kN confirmado) incluido?** (cambiaría
   resultados publicados de fase previa).
5. **Material definitivo: G35 (artefactos EII) vs G40 (hipótesis del motor)** por
   edificio.
6. **Sección de la viga `V_031`, `fy`, recubrimiento y armadura** de columna y muro
   (para M–φ y P–M).
7. **Versar fuentes del EII** (§9.2): aceptación de incluir en Git los JSON adaptados,
   cargas-y-cuadro, y el zip de planos.