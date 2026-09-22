# ACTA DE VERIFICACIÓN FINAL — Entrega 03

> Documento de cierre técnico de la Entrega 03 (cargas, sismo EX/EY, superposición
> completa, capacidad RC y demanda/capacidad). Todos los números provienen de las
> corridas re-ejecutadas desde cero por `src/ejecutar_entrega_03.py` (12 corridas,
> estado global **OK**) y de los JSON/CSV/MD/PNG versionados en `results/` y `figures/`.
>
> Reproducibilidad:
> ```
> python -X utf8 -m unittest discover -s tests -p "test_*.py"   # 28/28
> python -X utf8 -m src.ejecutar_entrega_03                      # 12 corridas
> ```

---

## 1. Acta numérica — carga sísmica EX/EY (método pseudoestático de la consigna)

### 1.1 Definición del caso

| Parámetro | Valor | Clasificación |
|---|---|---|
| Sobrecarga de uso `q_Q` | **3,0 kN/m²** (EI y EII) | `PARAMETRO_BASADO_EN_NORMA_NCH1537_2009_TABLA4` (`Q_EI/EII_NCH1537_2009_3.0_kN_m2`) |
| Fuente de `q_Q` | **NCh 1537:2009 (Of. 2009), Tabla 4 — "Escuelas · salas de clases"** (mínimo 3,0 kN/m²) | idem |
| Fracción de `Q` en peso sísmico | **0,50** | `PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA` |
| Coeficiente sísmico `a` | **0,20·g** | idem |
| Peso sísmico por nivel | `W_i = PP_i + 0,50·Q_i` | idem |
| Masa por nivel | `m_i = W_i/g` (`g=9,81 m/s²`) | idem |
| Fuerza lateral por nivel | `F_i = m_i·a = (W_i/g)·0,20·g = 0,20·W_i` | idem |
| Distribución nodal | `f_n = F_i·w_n/W_i` (proporcional al peso nodal del nivel) | idem |
| Dirección | `EX` = +X, `EY` = +Y; sin cargas gravitatorias | `direccion_exclusiva` ok |
| Momento accidental | 0 | sin torsión impuesta |

Justificación del coeficiente `0,20g`: proviene del **ejemplo/distribución de la
consigna** (no de parámetros normativos; zona, suelo, `R` y espectro quedan
`null`/`PENDIENTE` en `config/sismo.json`). Como `m_i = W_i/g`, la fuerza
resultante por nivel es `F_i = m_i·a = (W_i/g)·(0,20·g) = 0,20·W_i`.

### 1.2 Edificio I — palabra clave por nivel (idéntico para EX y EY)

Fuente: `results/cargas/caso_sismico_{EX,EY}_I.json` → `peso_sismico/ledger_por_nivel`.

| z del nivel (m) | #nodos | `PP_i` (kN) | `Q_i` (kN) | `W_i` (kN) | `m_i` (kN·s²/m) | Centro de masa (X, Y, m) | `F_i` (kN) |
|---|---|---:|---:|---:|---:|---|---:|
| −7,00 | 2 | 172,78 | 78,32 | 211,93 | 21,6040 | (10,899; −10,819) | 42,387 |
| −4,00 | 117 | 2.324,38 | 1.082,78 | 2.865,76 | 292,1267 | (8,045; 0,094) | 573,153 |
| −0,05 | 31 | 6.513,34 | 3.017,19 | 8.021,94 | 817,7306 | (27,280; 7,919) | 1.604,387 |
| 3,90 | 42 | 5.266,70 | 2.547,69 | 6.540,54 | 666,7219 | (22,278; 8,273) | 1.308,108 |
| 7,85 | 63 | 5.715,77 | 2.797,58 | 7.114,56 | 725,2358 | (24,707; 8,234) | 1.422,913 |
| 11,85 | 69 | 5.234,77 | 2.804,87 | 6.637,20 | 676,5749 | (24,746; 8,283) | 1.327,440 |
| **Σ** | **324** | **25.227,74** | **12.328,42** | **31.391,9401** | — | — | **6.278,388022** |

Verificaciones del modelo (del JSON `verificaciones`):

| Magnitud | EX_I | EY_I |
|---|---|---|
| Carga lateral total aplicada | 6.278,388022 kN (= Σ`F_i`) | 6.278,388022 kN |
| Corte basal (verificador) | 6.278,388022 kN · `ok` | 6.278,388022 kN · `ok` |
| Σ reacciones del FE | R_x = −6.278,3880 kN; R_y ≈ 0 | R_x ≈ 0; R_y = −6.278,3880 kN |
| Residuo horizontal (abs) | 7e−08 kN | 7e−08 kN |
| Residuo horizontal (rel a F) | 1,1e−11 | 1,1e−11 |
| Desplazamiento máximo | 0,06320 m (nivel P4, nodo 248) | 0,07221 m (nivel P4, nodo 242) |
| Deriva máxima de piso | 0,013575 (P4) | 0,016842 (P4) |
| Sentido de deformada | OK · dominio +X · 0 nodos opuestos | OK · dominio +Y · 0 nodos opuestos |
| Rotación máxima de respuesta | 5,99e−3 rad (R_y) | 6,84e−3 rad (R_x) |
| Momento accidental aplicado | 0 | 0 |
| retcode FE / `sol_ok` | 0 / true | 0 / true |

### 1.3 Edificio II — palabra clave por nivel (idéntico para EX y EY)

Fuente: `results/cargas/caso_sismico_{EX,EY}_II.json` → `peso_sismico/ledger_por_nivel`.

| z del nivel (m) | #nodos | `PP_i` (kN) | `Q_i` (kN) | `W_i` (kN) | `m_i` (kN·s²/m) | Centro de masa (X, Y, m) | `F_i` (kN) |
|---|---|---:|---:|---:|---:|---|---:|
| −4,00 | 45 | 4.893,85 | 1.593,06 | 5.690,39 | 580,0598 | (10,505; 7,840) | 1.138,077 |
| −0,05 | 45 | 5.483,30 | 1.593,06 | 6.279,83 | 640,1458 | (10,502; 7,930) | 1.255,966 |
| 3,90 | 44 | 5.438,49 | 1.593,33 | 6.235,15 | 635,5913 | (10,408; 7,990) | 1.247,030 |
| 7,85 | 44 | 5.410,05 | 1.593,06 | 6.206,58 | 632,6788 | (10,332; 8,001) | 1.241,316 |
| 11,85 | 44 | 4.745,31 | 1.516,62 | 5.503,62 | 561,0218 | (10,280; 7,917) | 1.100,725 |
| **Σ** | **222** | **25.971,00** | **7.889,13** | **29.915,5708** | — | — | **5.983,114195** |

Verificaciones del modelo:

| Magnitud | EX_II | EY_II |
|---|---|---|
| Carga lateral total aplicada | 5.983,114195 kN | 5.983,114195 kN |
| Corte basal (verificador) | 5.983,114195 kN · `ok` | 5.983,114195 kN · `ok` |
| Σ reacciones del FE | R_x = −5.983,1142 kN; R_y ≈ 0 | R_x ≈ 0; R_y = −5.983,1142 kN |
| Residuo horizontal (abs) | 2e−08 kN | 2e−08 kN |
| Residuo horizontal (rel a F) | 3,3e−12 | 3,3e−12 |
| Desplazamiento máximo | 0,00471 m (nivel EII_CP4, nodo 604003) | 0,00967 m (nivel EII_CP4, nodo 604040) |
| Deriva máxima de piso | 0,000343 (EII_CP2) | 0,000814 (EII_CP4) |
| Sentido de deformada | OK · dominio +X · **7 nodos opuestos** (fracción 0,0004) | OK · dominio +Y · **18 nodos opuestos** (fracción 0,0012) |
| Rotación máxima de respuesta | 1,75e−3 rad (R_x) | 0,92e−3 rad (R_y) |
| Momento accidental aplicado | 0 | 0 |
| retcode FE / `sol_ok` | 0 / true | 0 / true |

### 1.4 Limitaciones visibles de la carga sísmica (se mantienen explícitas)

- **PP del Edificio I incompleto/pendiente**: la v2 quedó **cota inferior**
  (`PP_confirmado = 17.179,23 kN`, `PP_pendiente`/`PP_no_incluido` en `null`,
  `PP_provisional = 0,0`); la banda 20,3–21,2 MN (≈3.168–4.046 kN, 18,4–23,6 %)
  **no fue adoptada**; el desfase P4 (+0,1813 m, D4) no está aplicado al FE
  (ver `docs/RESOLUCION_PENDIENTES_PP_EI.md`). El `W` sismico del EI se calcula
  sobre el PP que **sí** está modelado.
- **Discrepancia de muros del Edificio II**: `G_EII` **no se cierra**; PP de
  elementos: cota inferior 17.179,23 kN (CONFIRMADO) vs reproducible 17.437,79 kN
  vs público 19.629,04 kN (ver `docs/AUDITORIA_PP_EII_v1.md`). No se aplica ningún
  factor correctivo.
- **Ruteo EII con pendientes**: auditoría de 293 rutas (161 `DOCUMENTADA`,
  118 `HIPOTESIS_GEOMETRICA_DEFENDIBLE`, **14 `SIN_CAMINO_ESTRUCTURAL_CONFIRMADO`**);
  carga **no transferida, mantenida en origen: 417,850839 kN** (nodos 604032,
  600001, 600002, 600006, 600007, 600038, 601038, 602041, 602040, 603038, 603042;
  ver `results/cargas/ruteo_G_EII_auditoria.json`).
- **Indicador `sum_por_nivel` del EI en z=−4 m**: la herramienta de atribución
  por nivel muestra `ok=false` (aplicada=0) porque la cota z=−4 no coincide con las
  cotas de nivel del FE; **las cargas sí están aplicadas** (corte basal 6.278,39 kN
  y equilibrio global con residuo 7e−08 kN lo confirman). Es una limitación de la
  herramienta de atribución, no un desequilibrio del modelo.
- **EII, franja D-D′**: 7/18 nodos con producto local `f·u` opuesto (fracción
  0,0004–0,0012); dominio global de deformada correcto (se reporta como nota, no
  como error).

---

## 2. Acta de superposición completa (por edificio)

### 2.1 Configuración

| Concepto | Valor |
|---|---|
| Combinación | `1,0·G + 0,7·Q + 0,3·EX − 0,2·EY` |
| Etiqueta | `DEMOSTRACION_ARBITRARIA_1.0_0.7_0.3_-0.2` |
| Estatus | **Conjunto de demostración, NO normativo** (coeficientes normativos reales pendientes) |
| Corridas por edificio | 5 (G, Q, EX, EY y la combinación **EXPLICITA**) |
| Fuente | `results/superposicion/verificacion_superposicion_completa_{I,II}.json` |

Respuesta superpuesta = `1,0·G + 0,7·Q + 0,3·EX − 0,2·EY` de respuestas base;
la corrida **EXPLICITA** aplica la carga combinada directamente sobre el FE. Se
comparan desplazamientos, reacciones, fuerzas axiales y momentos de extremo
(`superpuesto` vs `explicito`).

### 2.2 Edificio I

| Familia | # filas | error abs máx | error rel máx | estado |
|---|---|---:|---:|---:|:--:|
| Desplazamiento (1 vertical, 1 horizontal) | 2 | 2,8e−17 | 9,8e−16 | OK |
| Reacción (2 reacciones verticales de base) | 2 | 4,5e−13 | 2,3e−16 | OK |
| Axial (extremos i/j del elemento 64) | 2 | 4,5e−13 | 2,3e−16 | OK |
| Momento (columna 208 y viga 395) | 2 | 1,1e−13 | 1,7e−16 | OK |
| **Total** | **8** | **4,5e−13** | **9,8e−16** | **8/8** |

- Tolerancia relativa usada: `1e−4` (todas las filas cumplen con margen > 10 órdenes).
- Compatibilidad de modelos: matrices 324×324 con firmas idénticas (0 discrepancias);
  claves de resultados consistentes (324 desplazamientos, 318 reacciones, 349
  fuerzas locales; longitudes 6/12 correctas); patrón explícito consistente
  (`max_diferencia = 0,0 kN`).
- Equilibrio explícito: `R_z = P_z = 33.857,62 kN`, residuo vertical −0,0 · `ok`;
  horizontal `Fx=−1.883,52 / Fy=1.255,68` vs cargas `P` (1.883,52 / −1.255,68) · `ok`;
  residual de momentos [−4.552,00; 7.336,89] · `ok`.
- Estado: **`IMPLEMENTADO_Y_VERIFICADO_COMPLETO`**.

### 2.3 Edificio II

| Familia | # filas | error abs máx | error rel máx | estado |
|---|---|---:|---:|---:|:--:|
| Desplazamiento (1 vertical, 1 horizontal) | 2 | 4,2e−15 | 1,7e−13 | OK |
| Reacción (2 reacciones verticales de base) | 2 | 8,2e−12 | 2,2e−15 | OK |
| Axial (extremos i/j del elemento 6) | 2 | 9,1e−13 | 3,0e−16 | OK |
| Momento (columna 25 y viga 188) | 2 | 2,2e−12 | 8,1e−15 | OK |
| **Total** | **8** | **8,2e−12** | **1,7e−13** | **8/8** |

- Tolerancia relativa usada: `1e−4` (cumplida en todas las filas).
- Compatibilidad de modelos: matrices 222×222 idénticas; 222 desplazamientos,
  147–151 reacciones, 264 fuerzas locales; `max_diferencia = 0,0 kN`.
- Equilibrio explícito: `R_z = P_z = 31.493,40 kN`, residuo vertical 0,0 · `ok`;
  horizontal `Fx=−1.794,93 / Fy=1.196,62` vs `P` (1.794,93 / −1.196,62) · `ok`;
  residual de momentos [−949,72; −663,17] · `ok`.
- Estado: **`IMPLEMENTADO_Y_VERIFICADO_COMPLETO`**.

### 2.4 Nota honesta de la acta de superposición

La comparación contiene filas de **desplazamiento, reacción, axial y momento**;
**no incluye una familia de cortantes** (ninguna fila `familia="cortante"`): la
linealidad del cortante queda cubierta implícitamente por la identidad
desplazamientos/reacciones/axiales/momentos del mismo modelo, pero **no se
verificó como magnitud explícita** y se deja señalado como pendiente.

---

## 3. Demanda/capacidad (D/C) — clasificación corregida

El módulo `src/capacidad_rc/demanda_capacidad.py` dejó de reportar
`estado: OK/NO_CUMPLE`. Toda columna reporta ahora una **comparación aritmética
de cuota** (`comparacion_cuota_aritmetica: "D/C <= 1" | "D/C > 1"`) sobre la
**capacidad de demostración**, y el conjunto queda clasificado como
`EVALUACION_ALGORITMICA_CON_SECCION_DEMO` (sin validez de diseño).

| Concepto | Edificio I | Edificio II |
|---|---|---|
| Clasificación | `EVALUACION_ALGORITMICA_CON_SECCION_DEMO` | idem |
| Sección utilizada | `DEMO_RC_EI` (0,70×0,70 m; fc 40 MPa hipótesis G40; armado demo 12#25, rec 0,04 m, fy 420) | `DEMO_RC_EII` (0,70×0,70 m; fc 35 MPa documentado G35; armado demo 12#25) |
| Columnas evaluadas (procedimiento) | 97 | 32 |
| Dentro de la cuota aritmética D/C ≤ 1 | 97 | 32 |
| Fuera de la cuota aritmética | 0 | 0 |
| Dentro del rango de interpolación N del P–M (modo `interpolado`) | **97 (100 %)** | **32 (100 %)** |
| Fuera de rango de interpolación / no evaluables | **0** | **0** |
| **D/C máx (demostración)** | **0,5373** | **0,2572** |
| Columna crítica | **208 · nivel P4 · extremo j** | **25 · nivel EII_CP3 · extremo j** |

### 3.1 Detalle trazable de la columna crítica

**Edificio I, columna 208**
- Elemento: `col_30.0_9.081_base_P4` (tag 208), nodos 207 (z=−4,01 m) / 206 (z=11,83 m), nivel P4.
- Combinación: `1,0·G + 0,7·Q + 0,3·EX − 0,2·EY` (conjunto de demostración, NO normativa).
- Demanda: `P_u = 1.354,751 kN`; `M_demanda = 655,5926 kN·m` (extremo j, componente dominante `Mz_j`).
- Capacidad interpolada: `M_u(N=P_u) = 1.220,1434 kN·m`; modo `interpolado`;
  límites de interpolación `N ∈ [−5.880, 19.600] kN` (21 puntos).
- **D/C = 0,5373** (≤ 1 aritmético, con capacidad demo).
- Procedencia de parámetros: geometría `P. 70x70` **DOCUMENTADA** (candidatos EI
  cielos/pisos; `columnas_tramos_ei.json`, 97 tramos); `fc = 40 MPa` **HIPOTESIS_DEL_GRUPO**
  (sin fuente independiente); armadura **BLOQUEADO_POR_PARAMETROS** → armado de demostración.
- Estado: `EVALUACION_ALGORITMICA_CON_SECCION_DEMO` (sección **demostración**,
  no capacidad real de diseño).

**Edificio II, columna 25**
- Elemento: `EII_CP4_COL_007` (tag 25), nodos 603029 (z=7,87 m) / 604029 (z=11,83 m), nivel EII_CP3.
- Combinación: idéntica (conjunto de demostración).
- Demanda: `P_u = 777,607 kN`; `M_demanda = 274,3842 kN·m` (extremo j, componente dominante `My_j`).
- Capacidad interpolada: `M_u(N=P_u) = 1.066,6417 kN·m`; modo `interpolado`;
  límites `N ∈ [−5.880, 19.600] kN` (21 puntos).
- **D/C = 0,2572** (≤ 1 aritmético, con capacidad demo).
- Procedencia de parámetros: geometría **DOCUMENTADA** 0,70×0,70 (`MODELO_FE_GEOMETRIA_NODOS.json`,
  222 nodos/32 columnas); `fc = 35 MPa` **DOCUMENTADO** G35 (`eii_viewer.json`, Ec=27.805,6 MPa,
  γ=24,517); armadura **BLOQUEADO_POR_PARAMETROS** → armado de demostración.
- Estado: `EVALUACION_ALGORITMICA_CON_SECCION_DEMO` (sección **demostración**).

> **Advertencia:** `D/C ≤ 1` es una comparación **aritmética** `M_dem/M_u(N)` contra
> capacidad de demostración. Mientras no haya armadura/materiales reales
> documentados, **no** se puede afirmar "cumple", "es seguro" ni "aprobar" ningún
> elemento (ver `results/capacidad_rc/resumen_demanda_capacidad.txt`).

---

## 4. Verificación limpia (re-ejecución completa)

Mecanismo elegido: **re-ejecución desde cero en el árbol definitivo** (`results/` y
`figures/` se regeneran de forma determinista; no se añadió una opción de "salida
limpia" al ejecutor para no modificar su contrato ni duplicar código). La
alternativa de un directorio temporal se descartó porque las rutas de salida se
derivan de `REPO` (`parents[2]`); re-apuntarlas exigiría cambios fuera del alcance
del cierre.

| Chequeo | Resultado |
|---|---|
| Corridas del ejecutor (`python -X utf8 -m src.ejecutar_entrega_03`) | 12/12 OK, `returncode 0` cada una, `estado_global = OK` |
| Ejecución bajo `-W error::ResourceWarning` | sin errores por recurso |
| Tests (`unittest discover tests`) | **28/28 OK**, `0 warnings` capturados (10 Fiber + ESPECIFICA del D/C se agregó una prueba para el D/C demo) |
| Salidas regeneradas | 59 archivos en `results/` (JSON/CSV/MD/TXT) + 13 PNG en `figures/` (ver listados) |
| Referencias internas a archivos inexistentes | **NONE** (`estado.json` no embebe rutas; PNG referenciados existen) |
| Rutas espurias | **ninguna**: no existe `…\Proyecto 1\entrega_03_cargas_sismo_capacidad` (sibling espurio) |
| Enlaces relativos de la documentación (`docs/*.md`, `README.md`) | **NONE** rotos |

---

## 5. Cobertura de pruebas (28 tests por módulo)

| Módulo | # | Predominantemente cubre |
|---|---|---|
| `tests/capacidad_rc/test_capacidad_rc.py` | **13** | Fiber Section / M–φ / P–M: acero simétrico, área de fibras conserva área bruta, hormigón sin tracción, criterios de término (aplastamiento, malla sin falla, fractura del acero eps_su), M–φ monótona, envolvente P–M cubre M_u, cross-check OpenSeesPy, saneo `Mu` **+ interpolación del D/C** (punto exacto del P–M, interpolación entre dos puntos, fuera-de-rango se acota y marca sin extrapolar) |
| `tests/cargas/test_carga_viva_Q.py` | 5 | Q: catálogo SC lineal no uniforme EII, geometría demo EII-CP2, verificación por nivel y global EI, no doble aplicación/catálogo separado, q_Q null aborta |
| `tests/cargas/test_sismo_EX_EY.py` | 6 | EX/EY (verificadores: carga lateral total, corte basal, sentido, torsión, bloqueo por parámetros null) |
| `tests/superposicion/test_combinacion.py` | 4 | Superposición base: casos base incompletos abortan, coeficientes null exigen demo, combinación matricial = suma explícita, verificación contra OpenSees |

**Partes no cubiertas (se señalan honestamente; no se añaden tests triviales):**

- La **interpolación del D/C** queda cubierta por tests unitarios (punto exacto, entre
  puntos y fuera de rango); la **integración** del D/C (con las corridas FE de superposición
  y el diagrama P–M) se cubre solo por la corrida del pipeline (trazabilidad en acta §3).
- El **runner `caso_sismico.py`** (4 corridas EX/EY con sus verificaciones nuevas:
  `equilibrio_horizontal`, `sum_por_nivel`, `deriva_por_piso`, `gravitatorias_ausentes`)
  no tiene test propio; `test_sismo_EX_EY` prueba el módulo **legacy** `sismo_EX_EY`.
- **`verificacion_superposicion_completa.py`** (5 corridas, 8 filas por edificio) no
  tiene test unitario; `test_combinacion` cubre solo la base G+Q.
- `peso_sismico.py`, `auditoria_G_EII.py`, `caso_Q_EI/EII.py` (ejecutables) y el
  **ejecutor** `src/ejecutar_entrega_03.py` no tienen tests dedicados (verificados por
  corrida del pipeline y por las actas de este documento).

---

## 6. Limitaciones pendientes (no bloquean el flujo de demostración)

1. Sismo: parámetros **normativos** (zona, suelo, importancia, R, espectro, excentricidad) si el docente exige diseño por norma; hoy: método de la consigna.
2. Superposición: coeficientes normativos reales (hoy: conjunto demo `1.0_0.7_0.3_-0.2`).
3. Capacidad: `fy`, recubrimiento y **armadura reales** para eliminar `DEMO_RC_*`; sin ello, D/C es aritmético y **no** es comprobación de diseño.
4. PP EI incompleto (v2 cota inferior; banda no adoptada) y discrepancia de muros EII (G_EII sin cerrar); 14 ruteos SIN_CAMINO con 417,85 kN en origen.
5. Superposición sin familia de **cortantes** explícita; verificaciones nuevas de `caso_sismico.py` sin tests unitarios.