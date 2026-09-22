# Semana 2 — AVANCE: modelo gravitacional global (Edificio I reproducible + Edificio II aportado)

**Entregable:** `reports/semana02.md` — **informe grupal** (no se atribuye a
integrantes individuales).

## 1. Objetivo y alcance

Este informe consolida el avance de la semana 2 del curso: el modelo estructural
gravitacional de ambos edificios del proyecto y la transferencia de cargas hacia el
modelo de elementos finitos (FE). Todo lo reportado se deriva exclusivamente de los
**archivos publicados en este repositorio**.

- **Edificio I:** análisis gravitacional **reproducible** (caso G = PP losa + PM.ADIC
  correlacionado) con OpenSeesPy desde el paquete autosuficiente
  `analisis_estructural/edificio_I/`. Es un resultado de
  **laboratorio** (`resuelto_laboratorio_no_utilizable_para_diseno`).
- **Edificio II:** el repositorio incluye los artefactos y resultados del análisis
  del Edificio II; su pipeline generador no fue verificado como parte de esta
  integración.

Convenciones del repositorio: unidades SI (`longitud=m`, `area=m2`,
`carga_superficial=kN/m2`, `carga_lineal=kN/m`, `fuerza=kN`, `momento=kN.m`).
Convención de esfuerzos OpenSees `localForce` (`N > 0` tracción).

## 2. Archivos y fuentes

| Fuente en el repo | Uso |
|---|---|
| `analisis_estructural/edificio_I/` (`src/`, `datos/`, `resultados/`, `README.md`, `requirements.txt`) | Paquete reproducible del Edificio I: pipeline FE OpenSeesPy, geometría, cargas correlacionadas y resultados publicados |
| `analisis_estructural/edificio_I/resultados/modelo_estructural/resultado_primera_ejecucion.json` | Resumen del I: modelo, hipótesis, verificaciones, balances |
| `analisis_estructural/edificio_I/resultados/modelo_estructural/solucion_cruda_primera_ejecucion.json` | Solución del I: desplazamientos, reacciones, fuerzas por elemento |
| `analisis_estructural/edificio_I/resultados/modelo_estructural/esfuerzos_elementos_edificio_I.csv` | Esfuerzos del I por elemento en ejes locales (349 filas × 34 columnas) |
| `analisis_estructural/edificio_I/resultados/modelo_estructural/columnas_tramos_ei.json`, `trazabilidad_losa_receptor_fe.json`, `paquete_entrega_edificio_I.json` | Tramos de columna, trazabilidad losa→receptor→nodo FE y paquete de entrega del I |
| `analisis_estructural/edificio_II_casoG_PP_elementos/MODELO_FE_GEOMETRIA_NODOS.json` | Modelo FE del Edificio II (nodos, columnas, vigas, muros, trazabilidad la sección |
| `analisis_estructural/edificio_II_casoG_PP_elementos/solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.60_80.json` (y `_V.30_80.json`) | Solución caso G con peso propio de elementos (reacciones, desplazamientos, esfuerzos) |
| `analisis_estructural/edificio_II_casoG_PP_elementos/eii_viewer.json` y `eii_esfuerzos.json` | Viewer del II: materiales, cargas caso G, áreas tributarias por viga, apoyos, esfuerzos |
| `analisis_estructural/edificio_II_casoG_PP_elementos/resumen_PP_ELEMENTOS.txt` | Resumen de peso propio de elementos del II |
| `viewer_unity/Assets/StreamingAssets/lab_data/manifest.json` | Contrato del viewer Unity para ambos edificios (14 archivos) |

El Edificio I se publica como **paquete reproducible y autosuficiente**: todos los
datos que lee el pipeline viven dentro de la misma carpeta, y la ejecución de
comprobación se describe en §7. Los artefactos del Edificio II (modelo, soluciones
`V.60/80` y `V.30/80`, viewer, esfuerzos, resumen de peso propio) están incluidos
como resultados publicados.

---

## 3. Edificio I: modelo, materiales, secciones y apoyos

**Modelo FE** (`analisis_estructural/edificio_I/resultados/modelo_estructural/resultado_primera_ejecucion.json`
→ `modelo`):

| Magnitud | Valor |
|---|---|
| Nodos | **324** |
| Columnas | **97** (sección documentada `P. 70x70`; `P.M. 30 cm` / `V.S.I. 30x60` provisionales según `config_edificios.py`) |
| Vigas | **206** en el modelo (CSV: 204 de tipo `viga` + 2 conectores elásticos cortos de P1 como `stub_elastico_rigidez_elevada`) |
| Muros | **46** (contención CP1S + muros de cada nivel) |
| Diafragmas (losas rígidas en plano) | 4 (P1, P2, P3, P4; CP1S excluido como basamento) |
| Niveles | 5 (`CP1S` −4.01, `P1` −0.05, `P2` 3.91, `P3` 7.87, `P4` 11.83 m) |
| Nodo maestro por nivel | P1=2, P2=5, P3=7, P4=179 |

Resumen por tipo y nivel del CSV (349 filas):

| Nivel | Columnas | Vigas | Muros | Stubs | Total |
|---|---|---|---|---|---|
| CP1S | 0 | 9 | 2 | 0 | 11 |
| P1 | 25 | 31 | 1 | 0 | 57 |
| P2 | 25 | 50 | 1 | 0 | 76 |
| P3 | 25 | 75 | 1 | 0 | 101 |
| P4 | 22 | 39 | 41 | 0 | 102 |
| −0.05 | 0 | 0 | 0 | 2 | 2 |
| **Total** | **97** | **204** | **46** | **2** | **349** |

**Materiales** (config `config_edificios.py` / `hipotesis.py`): hormigón **G40**
(`f'c = 40 MPa`), `E_c = 4700·√f'c = 29725.5 MPa` (ACI 318-19 19.2.2.1), `ν = 0.2`,
`densidad = 2500 kgf/m³`, conversión `g = 0.00980665` → `γ = 24.517 kN/m³`.

**Apoyos:** base fija 6 DOF en CP1S (hipótesis académica global). El conector
excéntrico de la viga perimetral de P1 se modela con stubs elásticos de rigidez
elevada (**aproximación documentada**, tags 429/430), no como vínculo rígido exacto.

**Ejemplos de trazabilidad** (`trazabilidad_losa_receptor_fe.json`,
`columnas_tramos_ei.json`, CSV):

```
columna col_10.0_8.9_P1  ->  tag FE 25 (nodo_i 23 en z=-4.01, nodo_j 24 en z=-0.05)
  seccion P. 70x70  ->  N_i = 1269.82 kN (compresion)  | Mz_mx_abs = 13.95 kN.m

viga GV_CP1_G3 (P1) ->  tag 408 (y 409..413, 415 continuacion; retícula)
  seccion V (hormigon)  ->  Vz_i = 178.85 kN, My_i = -5.75 kN.m
                            Vz_j = -178.85, My_j = -38.96 kN.m | M_mx_abs = 38.96 kN.m

muro M_EI_CP1S_001_contencion  ->  tag FE 673 (nodo_i 671, nodo_j 672)
  seccion M 0.2x12.62x2 (e=0.20 m, L=12.62 m)  ->  N_i = 361.59 kN (compresion),
                                                     Mz_mx = 55.57 kN.m
```

## 4. Edificio I: carga gravitacional

- **q_G (peso propio de losa):** `e(m) × 2500 × 0.00980665`
  - `e = 0.15 m` → **3.677 kPa**
  - `e = 0.20 m` (ascensor y zonas especiales) → **4.903 kPa**
- **PM.ADIC correlacionado por zona** (solo bandas con clasificación; zona sin
  clasificar = 0, hipótesis `carga_sin_clasificar`):

  | Clasificación plano (kgf/m²) | q_PM.ADIC |
  |---|---|
  | 260 | **2.550 kPa** |
  | 300 | **2.942 kPa** |

  Verificado en el payload: p. ej. losa `L_EI_CP1_D_INF_W_E` (1.8125 m²) =
  6.6655 kN PP + 4.6214 kN PM.ADIC → 3.677 + 2.550 kPa.
- **SC** se mantiene separada y **no se aplica** en el caso G (`incluir_sc=False`;
  `sc = 0` en todo el payload).
- Ejemplo real (P1, losa `L_EI_CP1_D_MED_F_G`, 89.0 m²):
  `W = (3.677 + 2.550) × 89.0 = 554.2 kN`.

## 5. Edificio I: áreas tributarias y transferencia

Método: reparto por celdas (`tamano_celda_inicial = 0.1 m`) sobre la losa neta de
aberturas según los `apoyos_validos` de cada losa. El **área tributaria por receptor**
queda publicada en
`viewer_unity/Assets/StreamingAssets/lab_data/edificios/I/tributary/por_viga.json`
(`area_tributaria_m2`) y en `resultado_primera_ejecucion.json`
(`area_asignada_receptores_m2`). Los polígonos son netos de aberturas.

Ejemplos reales (CP1S, extras del cielo del subterráneo):

| Receptor | Área tributaria (m²) | Carga total (kN) | n_nodos FE |
|---|---|---|---|
| `H_EI_CP1S_y1695_0.200-21.600` (viga perimetral) | 87.962 | 581.33 | 4 |
| `H_EI_CP1S_y2732_0.200-21.600` (V.S.I.) | 84.238 | 557.61 | 2 |
| `M_EI_CP1S_002` (muro de contención) | 27.188 | 179.97 | 2 |
| `V_EI_CP1S_x0060_0.700-16.150` (viga) | 27.102 | 168.77 | 2 |

`W(receptor) = Σ_losas (q_G + q_PM) × A_trib(losa→receptor)` se descarga sobre los
nodos FE del receptor (`cargas_nodales`); distribución equivalente `q_eq = W / L`
para vigas. `cargas_nodales_total_kN = [0, 0, -25227.732, 0, 0, 0]` (sin fuerzas
horizontales).

**Total por piso (caso G = PP + PM.ADIC, sin SC):**

| Nivel | Área neta (m²) | PP losa (kN) | PM.ADIC (kN) | Total (kN) | % |
|---|---|---|---|---|---|
| CP1S | 387.03 | 1423.30 | 1073.85 | 2497.15 | 9.9 % |
| P1 | 1005.73 | 3698.56 | 2814.78 | 6513.34 | 25.8 % |
| P2 | 849.23 | 3123.03 | 2143.66 | 5266.70 | 20.9 % |
| P3 | 932.53 | 3371.16 | 2344.61 | 5715.77 | 22.7 % |
| P4 | 934.96 | 3367.53 | 1867.23 | 5234.77 | 20.7 % |
| **Total** | **4109.47** | **14983.58** | **10244.37** | **25227.73** | 100 % |

`PP/PM.ADIC` global ≈ 59.4 % / 40.6 % (PP losa domina). Nivel con mayor carga: **P1**
(25.8 %).

## 6. Edificio I: conservación, equilibrio y diafragmas

**(a) Áreas por nivel:** `Σ A_asignada = Σ A_neta` en los 5 niveles
(`ok_area = true`; `area_no_asignada = 0`).

**(b) Balance A — carga del caso G vs aplicada al FE:**

```
carga_casoG_integrada_kN   = 25227.7308
carga_aplicada_nodal_total = 25227.7316
residuo_kN                 = -0.0008   (rel 0.0)   ok = true
carga_omitida (receptores sin FE) = 0.0 kN        ok = true
```

**(c) Balance B / equilibrio global del FE:**

```
R_z = P_z = 25227.7316 kN      residuo = -0.0    ok
F_x = -0.0, F_y = 0.0 kN                          ok
Momentos: res_Mx = -810.75 kN.m, res_My = -1155.13 kN.m (dentro tol 5 %, brazo 30 m)
reacciones_total_kN = 25227.7316 = carga aplicada        ok
```

El residuo de momentos es ~0.4 % de la referencia (modelo con diafragmas rígidos y
conector excéntrico aproximado), dentro de la tolerancia declarada.

**(d) Diafragmas (compatibilidad cinemática):** cada nivel P1–P4 es losa rígida en
su plano (`rigidDiaphragm`): los nodos esclavos comparten `u`, `v` y rotación de
piso `rz` con el maestro; `w` vertical queda libre. Verificación
(`u = u_m − rz·dy`, `v = v_m + rz·dx`):

| Nivel | N esclavos comprobados | max err cinemático (m) | ok |
|---|---|---|---|
| P1 | 28 | 0.0 | true |
| P2 | 41 | 0.0 | true |
| P3 | 62 | 0.0 | true |
| P4 | 68 | 0.0 | true |

CP1S (basamento sin losa rígida) queda excluido. Los extremos excéntricos de P1
(tags 429/430) siguen el cuerpo rígido del piso con err 0; su deformación vertical
de conector es ~ −2e-5/−4e-5 m (conector elástico mult=1000, aproximación documentada).

## 7. Edificio I: resultados y reproducción

**Esfuerzos:** `analisis_estructural/edificio_I/resultados/modelo_estructural/esfuerzos_elementos_edificio_I.csv`
(349 filas × 34 columnas), fuerzas en ejes **locales** por extremo (i/j) y envolvente
`_mx_`, convención OpenSees `localForce` (`N>0` tracción), unidades explícitas
`_kN`/`_kNm`. Son valores de extremo (no diagramas interiores de corte/momento). La
solución es estática lineal: `analyze_retcode = 0`, sin singularidades.

**Reproducción (comprobada en esta integración).** Desde la raíz de
`analisis_estructural/edificio_I/`:

```powershell
$env:PYTHONPATH = "src"
python -m pip install -r requirements.txt      # openseespy 3.7.0.3 (+ openseespywin 3.7.0.1)
python -m src.analisis.fe.main_fe     # -> resultados/modelo_estructural/
```

Exportaciones auxiliares: `python -m src.analisis.fe.exportar_esfuerzos_csv`,
`python -m src.analisis.fe.exportar_tramos_columnas`,
`python -m src.analisis.fe.exportar_regiones_tributarias`.

La corrida de comprobación se re-ejecutó desde la copia reproducible; los payloads
son **idénticos campo a campo** (modelo, hipótesis, cargas, verificaciones,
balances) salvo `tiempos_s` (4.22 s congelado vs **3.74 s** de la comprobación).
`R_z = P_z = 25227.7316 kN`, balances A y B ok, diafragmas ok, carga omitida 0.

**Advertencia de resultado académico provisional:** estado
`resuelto_laboratorio_no_utilizable_para_diseno`. La viga metálica de soporte
interior del cielo del subterráneo (`H_EI_CP1S_y2732_0.200-21.600`, 21.4 m) tiene
sección/refinamiento **provisional** (ejecución subdiv4 reportó desplazamiento
anómalo 12.68 m no validado: error de interpretación de unidad de sección); se
reporta pero **no se usa como dato de diseño**.

---

## 8. Edificio II: trazabilidad desde planos

Cadena completa `plano -> nodo -> elemento -> seccion -> tag`. Los nodos se
generan a partir de la posición `(u,v)` del plano (columna izquierda de la tabla
`trazabilidad_pos_tag` de
`analisis_estructural/edificio_II_casoG_PP_elementos/MODELO_FE_GEOMETRIA_NODOS.json`).

**Viga (retícula x = 7.5 m, nivel CP1S):**

```
plano EII_CP1S (cota -4.01 m)
  -> posicion [7.5,0]-[7.5,8.9] (eje_reticula "x=7.5 vano[0,8.9]")
  -> nodos 600022 / 600023        (trazabilidad_pos_tag)
  -> elemento EII_CP1S_V_001      (vigas_fe) con recibe_losa=true
  -> seccion V.60/80  (0.60 x 0.80 m, seccion_geom [0.6,0.8])
  -> elementTag FE: 500000
```

**Columna (retícula A2):**

```
plano EII_CP1 (cota -0.05 m)
  -> grid "A2"  (u=0.0, v=8.9)
  -> nodos 600017 / 601017        (nodo_inf / nodo_sup)
  -> elemento EII_CP1_COL_004     (columnas_fe)
  -> seccion 0.70x0.70
  -> elementTag FE: 300000        (id EII_CP1_COL_004)
```

**Muro (eje 1):**

```
plano EII_CP1S
  -> extremo [-3.65,-1.095]
  -> nodos 600000 / 601000
  -> elemento M_004 (ids EII_CP1S_M_004 / EII_CP1_M_004)
  -> espesor segun muro del plano
  -> elementTag FE: 400000
```

`sectionTag`: en la publicación la sección se conserva por su **nombre canónico**
(`0.70x0.70`, `V.60/80`, `V.40/80`, `V.30/80`); el ensamblaje FE asigna el
`sectionTag` interno correspondiente al resolver (no serializado en los JSON
publicados). Un mismo `plano -> [u,v]` produce exactamente el mismo nodo en los
5 niveles (mismo `u,v`, distinta `cota`), lo que garantiza la verticalidad de
columnas y muros.

## 9. Edificio II: modelo, estadísticas y resultados publicados

Conteos directos de `analisis_estructural/edificio_II_casoG_PP_elementos/MODELO_FE_GEOMETRIA_NODOS.json`
(campo `resumen`) y de los niveles del viewer:

| Magnitud | Valor |
|---|---|
| Nodos | **222** |
| Vigas | **175** (35 por nivel) |
| Columnas | **32** (todas `0.70x0.70`) |
| Muros | **57** |
| Diafragmas (losas rígidas) | **5** (uno por nivel) |
| Pisos / niveles | **5** (`EII_CP1S` a `EII_CP4`) |
| Springs verticales (resumen FE, `n_springs_vert`) | 88 |

Nodos por nivel: `EII_CP1S` 45, `EII_CP1` 45, `EII_CP2` 44, `EII_CP3` 44, `EII_CP4`
44 (total 222). Secciones de vigas: `V.60/80` ×155, `V.30/80` ×10, `V.40/80` ×5,
`por_resolver` ×5 (estas 5 se resuelven según la hipótesis de la solución publicada,
véase §15). Todas las vigas tienen `recibe_losa: true`.

**Resultados publicados** (caso G con peso propio de elementos): las soluciones
`_V.60_80` y `_V.30_80` existen en el repo y su comparación se documenta en §15.
Esfuerzos: **247** elementos en `eii_esfuerzos.json` (`inicio`/`fin`,
`n_estaciones`). El resumen de peso propio de elementos está en
`resumen_PP_ELEMENTOS.txt`.

## 10. Edificio II: cargas y materiales

Definición completa en
`analisis_estructural/edificio_II_casoG_PP_elementos/eii_viewer.json` →
`materiales` y `cargas.caso_G`.

- **Espesor de losa:** `0.15 m` (todos los niveles); excepción losa de ascensor
  `0.20 m` (nota de `caso_G`).
- **Peso unitario:** hormigón **G35**, `densidad_kg_m3 = 2500`, conversión por
  gravedad `0.00980665` → `gamma_kN_m3 = 2500·0.00980665 = 24.517 kN/m³`
  (el resumen usa 24.5166). Módulo `E_c_MPa = 27805.6`, `fc_MPa = 35`.
- **Carga de terminaciones y sobrecarga:** el plano 700 (DXF) declara **cargas
  lineales por zona** (no superficiales), `SC_lineal_kg_m` y `PM_ADIC_lineal_kg_m`:

  | Zona | PM.ADIC (kg/m) | SC (kg/m) |
  |---|---|---|
  | A | 260 | 500 |
  | B | 260 | 300 |
  | C | 200 | 200 |
  | D | 1500 | 100 |
  | E | 260 | 200 |
  | F | 260 | 500 |

- **q_G (peso propio de losa):** `Q_PP_LOSA_kPa = e(m) × 2500 × 0.00980665`:

  | Losa | q_G |
  |---|---|
  | e = 0.15 m | **3.677 kPa** |
  | e = 0.20 m (ascensor) | **4.903 kPa** |

- **Ensayo de validación de la tributación:** `G_prueba_tributacion_1kpa =
  1.0 kN/m²`, "CARGA DE ENSAYO ... SEPARADA de las cargas reales". Es el caso de
  validación numérica del pipeline de tributación (se usa para los chequeos de
  reparto cuando se quieren aislar las cargas reales).

## 11. Edificio II: áreas tributarias (3 vigas, `EII_CP2`)

Método: reparto fino por celdas del pipeline (`tamano_celda_inicial = 0.1 m`) según
los `apoyos_validos` de cada losa; el **área tributaria por viga queda publicada** en
`eii_viewer.json` (`area_tributaria_m2`). Recinto tributario = unión de las losas
que declaran a la viga como receptor en `apoyos_validos`; el área del recinto
coincide con `area_tributaria_m2` de la viga. Carga: `W = q_G × A_trib`;
distribución equivalente `q_eq = W / L`.

| Viga | Sección | Luz L (m) | Recinto tributario (losas, polígonos m) | A_trib (m²) | q_G (kPa) | W (kN) | q_eq (kN/m) |
|---|---|---|---|---|---|---|---|
| `EII_CP2_V_003` | V.60/80 | 8.90 | `L_001` `[7.5,0][12.5,0][12.5,8.9][7.5,8.9]` ∪ `L_002` `[12.5,0][17.5,0][17.5,8.9][12.5,8.9]` | **16.3748** | 3.677 | **60.21** | **6.765** |
| `EII_CP2_V_001` | V.60/80 | 8.90 | `L_001` `[7.5,0][12.5,0][12.5,8.9][7.5,8.9]` ∪ `L_008` `[3.75,0][7.5,0][7.5,8.9][3.75,8.9]` | **15.9967** | 3.677 | **58.82** | **6.609** |
| `EII_CP2_V_020` | V.60/80 | 8.90 | `L_007` `[0,0][3.75,0][3.75,8.9][0,8.9]` ∪ `L_008` `[3.75,0][7.5,0][7.5,8.9][3.75,8.9]` | **13.5021** | 3.677 | **49.65** | **5.578** |

Los polígonos de losa son netos de aberturas (p. ej. `L_001` neta = 5.0 × 8.9 =
44.500 m², `L_007` = 33.375 m²). El reparto por celdas finas es el que alimenta al
modelo FE (caso `G_prueba` = mismo pipeline que el caso G real).

## 12. Edificio II: conservación

Tolerancias del pipeline (`configuracion_calculo`, configuración interna del
análisis): `tolerancia_relativa_area = 1e-6` y `tolerancia_relativa_carga = 1e-6`.

**(a) Conservación global del análisis (gold standard del FE).** El solver reporta
`equilibrio_vertical`:

```
R_z_kN = P_z_kN = 29306.0667   |   residuo_kN = -0.0   |   ok = true
```

Es decir, `sum(cargas aplicadas) = sum(reacciones)`, residuo **exactamente 0**
(exacto al redondeo del JSON). `F_total_kN = [0.0, 0.0, -29306.0667, 0, 0, 0]`
(no hay fuerzas horizontales).

**(b) Conservación del reparto de losa en `EII_CP2`.** Área neta de losas del
nivel = 531.1088 m² → carga de losa `q_G × A_neta = 3.677 × 531.1088 =
1952.89 kN`. La suma de las áreas tributarias **de vigas** publicadas en el
viewer es `Σ A_trib(vigas) = 265.9353 m²` → `977.84 kN (50.1 %)`. El resto
(974.9 kN, 49.9 %) lo reciben los **muros** y demás receptores declarados en
`apoyos_validos` (el área por muro no se publica en el viewer; el balance total
lo cierra el FE, apartado (a)). En dominios donde todos los receptores son
vigas, `Σ A_trib = A_neta` se cumple por construcción de la partición.

**(c) Coherencia entre peso propio de losa y elementos.** Descomponiendo la
carga total del caso G:
`P_z − Σ PP_elementos = 29306.0667 − 19629.04 = 9677.03 kN` (PP losa inferido)
contra `Σ (q_G × A_neta) de los 5 niveles = 9669.5 kN` (con `q_G = 3.677 kPa`;
`A_neta` por nivel: 531.0213, 531.0213, 531.1088, 531.0213, 505.5413 m²).
Diferencia **0.08 %**, explicable por el redondeo de `gamma` (24.517 vs 24.5166
usado en el resumen) y por la losa de ascensor de 0.20 m (4.903 kPa). Coherente.

## 13. Edificio II: apoyos y restricciones

Tomado de
`analisis_estructural/edificio_II_casoG_PP_elementos/MODELO_FE_GEOMETRIA_NODOS.json`
+ `solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.60_80.json` (`reacciones`).

**Tipos de apoyo/restricción usados:**

1. **Apoyos de base (placa de cimentación):** los 45 nodos del nivel
   `EII_CP1S` (`600000`–`600044`, z = −4.01 m) registran reacciones completas
   (6 DOF) → **empotramientos**. Σ reacción vertical base =
   **17,447.66 kN**, máximo individual **1,432.69 kN** en el nodo **`600029`**
   (ejemplo de identificación y trazabilidad del apoyo/reacción, ver §15 y §18).
2. **Restricción de diafragma rígido** en los niveles superiores (v. §14): la
   carga por encima de la base se transfiere a través de los diafragmas;
   reacciones internas por nivel:
   `EII_CP1 2,831.77` · `EII_CP2 2,944.31` · `EII_CP3 3,036.48` ·
   `EII_CP4 3,045.85` kN (Σ interna = 11,858.41 kN; total global
   17,447.66 + 11,858.41 = 29,306.07 ✓).
3. **Springs verticales:** el resumen FE declara `n_springs_vert = 88`
   (resortes verticales del modelo).

Representación esquemática (vista lateral):

```
  CP4 ▬▬▬▬▬▬▬▬▬▬ (diafragma, reaccion interna 3,045.85 kN)
  CP3 ▬▬▬▬▬▬▬▬▬▬ (3,036.48)
  CP2 ▬▬▬▬▬▬▬▬▬▬ (2,944.31)
  CP1 ▬▬▬▬▬▬▬▬▬▬ (2,831.77)
 CP1S ▄▄▄▄▄▄▄▄▄▄ base 45 empotramientos (17,447.66)
```

El valor publicado de la reacción del nodo `600029` en `_V.60_80.json` es:

```
"600029": [ -0.007587, -0.485859, 1432.6943, -4.46677, -0.040387, 0.0 ]
```

(componente dominante vertical `Fz = 1,432.69 kN`; las demás componentes son de
orden despreciable). Este valor es un **resultado**; si el modelo cambiara, sería
regenerado por el análisis (ver §15).

## 14. Edificio II: diafragmas

**Cinemática:** cada nivel es una losa rígida en su plano: los nodos de un mismo
nivel comparten el movimiento horizontal (`u`, `v`) y la rotación de piso
(`rz`); la deformación vertical (`w`) queda libre (compatible con las cargas
verticales del peso propio). Es el modelo estándar "rigid diaphragm" por nivel.

**Verificación numérica** con los `desplazamientos` de la solución V.60/80
(`MODELO_FE_GEOMETRIA_NODOS` → `nodos_por_nivel`):

| Nivel | n | u mín/máx (m) | dispersión u | v mín/máx (m) | rz máx (rad) | max \|w\| (m) |
|---|---|---|---|---|---|---|
| `EII_CP1S` | 45 | 0.000000 / 0.000000 | 0 | 0/0 | 0 | 0.00000 |
| `EII_CP1` | 45 | 0.000000 / 0.000000 | 0 | 0/0 | 0 | 0.00032 |
| `EII_CP2` | 44 | 0.000001 / 0.000001 | 0 | 0/0 | 0 | 0.00055 |
| `EII_CP3` | 44 | 0.000002 / 0.000002 | 0 | 0/0 | 0 | 0.00070 |
| `EII_CP4` | 44 | 0.000002 / 0.000002 | 0 | 0/0 | 0 | **0.00077** |

Cada nivel se mueve como **cuerpo rígido en su plano** (dispersión in-plane
nula a precisión del JSON: 0 ± 1e-9), mientras `w` varía por nodo
(flexión vertical; `max_desp_z = 0.00076866 m`). La restricción de diafragma
queda así verificada numéricamente.

## 15. Edificio II: modificación del modelo (desde datos)

La modificación del modelo del II requiere **editar las entradas del pipeline y
re-ejecutar el análisis FE**. Unity solo visualiza; no reanaliza. Como el
pipeline generador del Edificio II **no fue verificado** como parte de esta
integración, cualquier reanálisis queda **fuera del alcance** de este entregable.

Los JSON del paquete (`MODELO_FE_GEOMETRIA_NODOS.json`, `eii_viewer.json`,
`eii_esfuerzos.json`, las soluciones) son **artefactos publicados** (resultados del
modelo y datos del viewer). En particular, **editar las reacciones de
`eii_esfuerzos.json` no cambia ningún apoyo del modelo**: ese archivo es un
resultado. Un cambio real de apoyo exige modificar la entrada del modelo (el
conjunto de restricciones de base del input) y volver a ejecutar el análisis FE;
ese reanálisis queda fuera del alcance (§1).

**(a) Hipótesis de sección de las vigas `V_031` (ambas soluciones publicadas).**
El modelo declara `v031_hipotesis_seccion`; las dos hipótesis ya están resueltas y
publicadas en el repo, por lo que su comparación es una **verificación** de datos
existentes (no un reanálisis):

| Hipótesis | P_z / R_z (kN) | max_desp_z (m) |
|---|---|---|
| V.60/80 | **29,306.0667** | 0.00076866 |
| V.30/80 | 29,216.3359 | 0.00076866 |

La diferencia (89.73 kN) es el peso propio de las 5 vigas `V_031` por nivel
(`v031_regiones`), un dato sensible a la hipótesis.

**(b) Identificación y trazabilidad de un apoyo/reacción de base.** El nodo
`600029` es el apoyo de base con mayor reacción vertical (1,432.69 kN, ver §13).
El valor publicado no debe editarse a mano: es un resultado del análisis. Para
cambiar la condición de apoyo habría que modificar la **restricción en el input
del modelo** y re-ejecutar el análisis FE, tarea que queda fuera del alcance de
esta integración (pipeline del II no verificado, §1).

_Referencia del resultado publicado (muestra de `_V.60_80.json`, no editable como
entrada):_

```json
"600029": [ -0.007587, -0.485859, 1432.6943, -4.46677, -0.040387, 0.0 ]
```

**(c) Edición de polígono tributario.** Si el plano cambia, se modifica el
`poligono_exterior` de la losa (o las `aberturas_poligonos`) en la **entrada
geométrica** del modelo; a continuación **deben recalcularse las áreas
tributarias, las cargas aplicadas y el análisis FE**. No se deben editar
manualmente los resultados (`area_tributaria_m2`, reacciones, esfuerzos) para
simular el recálculo. La siguiente forma muestra el dato que el recálculo
regeneraría (referencia conceptual de la edición de geometría):

```json
{ "poligono_exterior": [[7.5, 0.0], [12.5, 0.0], [12.5, 8.9], [7.5, 8.9]], "area_tributaria_m2": 0.0, "pendiente_rec_areas_cargas_y_fe": true }
```

## 16. Viewer Unity para ambos edificios

**Contrato de datos en `viewer_unity/Assets/StreamingAssets/lab_data/`**
(`manifest.json`, **14 archivos verificados presentes**) y en los JSON del
análisis (`MODELO_FE_GEOMETRIA_NODOS.json`, `eii_viewer.json`, `eii_esfuerzos.json`):

| Capa | Contenido | Devuelve |
|---|---|---|
| Niveles | cotas del I (`CP1S` a `P4`) y del II (`EII_CP1S` a `EII_CP4`), `espesor_losa` | conmutador de piso |
| Geometría I | `viewer_unity/Assets/StreamingAssets/lab_data/edificios/I/geometry/CP1S.json`, `P1.json`, `P2.json`, `P3.json`, `P4.json` | losas, vigas, columnas, muros, aberturas |
| Geometría II | `lab_data/edificios/II/geometry/EII_CP1.json`, `EII_CP1S.json`, `EII_CP2.json`, `EII_CP3.json`, `EII_CP4.json` | visualización del II (solo geometría en el viewer; los resultados del II residen en `analisis_estructural/edificio_II_casoG_PP_elementos/`) |
| Losas del II | 28/nivel: `poligono_exterior` ± `aberturas_poligonos` (+ triangulación) | selección por losa |
| Vigas del II | 35/nivel: ID, sección, `eje_reticula`, `area_tributaria_m2` | IDs visibles, recinto tributario |
| Muros / Columnas del II | muros, columnas de referencia (`grid` `A2`, eje de retícula de vigas) | IDs, secciones, ejes |
| Resultados I | `lab_data/edificios/I/results/primera_ejecucion.json` (324 nodos, mult=1000, subdiv=1) | reacciones, desplazamientos |
| Tributaria I | `lab_data/edificios/I/tributary/por_viga.json`, `regiones_tributarias.json` | área tributaria por receptor, recintos |
| Apoyos del II | base: 45 reacciones Fz (min–max: **18.4–1432.7 kN**) | cubos de apoyo / color por intensidad |
| Esfuerzos del II | 247 elementos (`eii_esfuerzos.json`: `inicio`/`fin`, `n_estaciones`) | mapas de esfuerzo por elemento |
| Cargas / Material del II | `caso_G` (q_G, SC/PM.ADIC), G35 (γ, E, fc) | panel de cargas |
| Colocación | `lab_data/placement.json` | posición de ambos edificios (cadena `comun(u,v,cota) -> Unity(u,cota,v)`, aplicada una sola vez) |

Selección: por nivel y por ID único de elemento (`EII_CP2_V_003`,
`EII_CP1_COL_004`, `M_004`...). Las áreas tributarias del II se muestran por viga
(`area_tributaria_m2`) y, a futuro, por muro.

**Geometría candidata P4 del viewer:** vigas trasladadas **+0.18 m en v** (ejes
sur/interior/norte = 0.18/9.08/16.33, 41 vigas, fuente `2017_67-103.dxf`); el
manifest declara que las áreas tributarias y los resultados FE (ejecución primaria)
corresponden a la geometría **previa** de P4 (vigas en v=0/8.9/16.15) y **no están
revalidados** para esa candidata.

**Correcciones visuales recientes del voladizo norte (P1/P2/P4),**
implementadas de forma idempotente en `viewer_unity/tools/apply_plan_frames.py`
y aplicadas a `geometry/P1.json`, `P2.json` y `P4.json`: P1 elimina 2 losas del
voladizo este (`L_EI_CP1_D_VOL_ESTE_OE/ES`, sin soporte físico en el plano P1);
P2 reubica la columna G3S1 sobre su huella RLE-PILAR, incorpora
`COL_EI_CP2_RLE_PILAR_10.00_20.27` y agrega 3 vigas del voladizo norte (solo
geometría del viewer, sin tributaria/FE); P4 reubica GS6/HS7 sobre sus huellas
(`2017_67-103.dxf`). Estas correcciones fueron sometidas a **validación visual en
Unity**; la validación mostró que **no resuelven completamente** la representación
del voladizo (persisten losas que sobresalen respecto de las vigas perimetrales y
columnas que parecen desconectadas o fuera de la huella visible). La discrepancia
queda **documentada como limitación geométrica del viewer** (§19) y **no se declara
como geometría validada definitivamente**.

## 17. Verificaciones y demostración

- **Edificio I (verificado):** balances A y B ok (residuo 0.0008 kN y 0.0,
  respectivamente), carga omitida 0, diafragmas con error cinemático 0, manifest del
  viewer con 14/14 archivos presentes, y **reproducción idéntica** del análisis
  desde el paquete (`§7`).
- **Edificio II (verificado sobre los artefactos publicados):** equilibrio vertical
  `R_z = P_z = 29306.0667 kN` con residuo 0 (§12), diafragmas con dispersión
  in-plane 0 (§14), y trazabilidad `plano -> nodo -> elemento -> tag` consistente
  entre `MODELO_FE_GEOMETRIA_NODOS.json` (§8) y las soluciones publicadas.

## 18. Uso de IA

1. **Convención de signos `globalForce` (Edificio II) — corrección de un error
   propuesto por el agente.** Caso real de la auditoría del análisis estructural del
   Edificio II (procedimiento interno de verificación):
   - **Error:** al ensamblar el equilibrio nodal, el agente sumó las fuerzas
     globales de barra con su signo tal cual (`soma += globalForce`). El balance en
     los nodos de base daba un residuo de **2.2e3 kN**:

     ```
     nodo 600029:  columna 1106.46 + reaccion 1432.69 + carga -326.23 = residuo 2212.92 kN
     ```

   - **Diagnóstico:** en OpenSees, `globalForce` en cada extremo es la fuerza que el
     **nodo** ejerce sobre el **elemento**, es decir, la fuerza del elemento sobre el
     nodo tiene signo opuesto.
   - **Corrección:** restar las fuerzas de barra en el balance (`soma -= globalForce`):

     ```
     nodo 600029:  -1106.46 - 326.23 + 1432.69 = 0.000 kN
     ```

   - **Resultado:** el residuo nodal máximo pasó de 2.2e3 kN a **5e-7 kN**
     (**1.7e-11 relativo**) en los 222 nodos y 6 DOF → `AUDITORIA: APROBADA`.
     Lección: contrastar la convención de signos contra un nodo aislado antes de
     cerrar una auditoría.

2. **Convención de signos `localForce` y esfuerzos (Edificio I):** se documentó el
   desglose de `localForce` (12 valores) y los ejemplos de §3/§7 fueron contrastados
   contra el CSV real.

3. **Voladizo norte del Edificio I (P1/P2/P4):** con soporte del agente se
   aplicaron, regeneraron y verificaron las correcciones idempotentes de
   `viewer_unity/tools/apply_plan_frames.py` (P1 −2 losas; P2 +1 columna y +3 vigas;
   P4 2 columnas reubicadas), con verificación automática de intersecciones,
   duplicados y del manifest (14 archivos). La validación visual posterior en Unity
   no resolvió completamente la representación del voladizo (ver §16 y §19).

4. **Reproducción del análisis del Edificio I:** el agente re-ejecutó el pipeline
   desde el paquete reproducible y comparó los payloads (idénticos salvo `tiempos_s`),
   cerrando la trazabilidad `datos -> FE -> resultados -> reporte`.

## 19. Limitaciones y pendientes

**Edificio I:**
1. Resultado de **laboratorio, no utilizable para diseño** (hipótesis: base fija
   6DOF en CP1S, continuidad vertical de pilares/muros, diafragma rígido).
2. Conector excéntrico de P1 = conector elástico de rigidez elevada (**aproximado**,
   no vínculo rígido exacto; deformación ~e-5 m documentada).
3. **Geometría candidata P4** (vigas +0.18 m) y **correcciones visuales P1/P2/P4**
   (limitación geométrica del viewer): la validación visual en Unity **fue
   realizada** y las modificaciones candidatas **no resolvieron completamente** la
   representación del voladizo: persisten **losas que sobresalen respecto de las
   vigas perimetrales** y **columnas que parecen desconectadas o fuera de la huella
   visible**. La discrepancia queda **documentada como limitación geométrica del
   viewer** y **no afecta a los resultados FE ya publicados**, porque estos
   corresponden a la geometría analítica previa indicada en el informe (§16). Los
   resultados FE/tributaria no se revalidaron contra las candidatas.
4. V.S.I. del cielo del subterráneo provisional (sección/refinamiento subdiv4 no
   validado; desplazamiento anómalo 12.68 m descartado).
5. Esfuerzos solo de extremo (no diagramas interiores).
6. `SC` identificada por separado y no aplicada en G; zona sin clasificar = 0.

**Edificio II:**
7. El repositorio incluye los artefactos y resultados del análisis del Edificio II;
   su pipeline generador **no fue verificado como parte de esta integración**.
8. Cualquier modificación del modelo (apoyos, secciones, geometría tributaria)
   exige editar la **entrada del pipeline** y re-ejecutar el análisis FE; ese
   reanálisis queda **fuera del alcance** de esta integración (no se editan a mano
   los resultados publicados para simular recálculo — §15).
9. El paquete del viewer para el II es de **solo geometría**: no incluye tributaria
   ni resultados dentro del viewer (los resultados del II residen en
   `analisis_estructural/edificio_II_casoG_PP_elementos/`).