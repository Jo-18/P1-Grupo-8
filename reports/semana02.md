# Semana 2 — AVANCE: modelo global v1 y transferencia de cargas

**Entregable:** `reports/semana02.md`

Todo lo reportado se **deriva exclusivamente de archivos publicados en este
repositorio**:

| Fuente en el repo | Uso |
|---|---|
| `datos/geometria/edificio_I_cielo_piso_*.json` (+ `indice_modelos.json`) | Geometría del Edificio I (borrador no ejecutable), carga de ensayo `G_prueba_tributacion_1kpa` |
| `src/areas_tributarias/` | Contrato de datos y modelo (Panel/Receptor), esquema canónico |
| `analisis_estructural/edificio_II_casoG_PP_elementos/MODELO_FE_GEOMETRIA_NODOS.json` | Modelo FE del Edificio II (nodos, columnas, vigas, muros, trazabilidad) |
| `.../solucion_FE_EII_completo_casoG_PP_ELEMENTOS_V.60_80.json` (y `_V.30_80.json`) | Solución caso G con peso propio de elementos (reacciones, desplazamientos, esfuerzos) |
| `.../eii_viewer.json` y `.../eii_esfuerzos.json` | Viewer: materiales, cargas caso G, áreas tributarias por viga, apoyos, esfuerzos |

Convenciones del repositorio: unidades SI (`longitud=m`, `area=m2`,
`carga_superficial=kN/m2`, `carga_lineal=kN/m`). El Edificio I está en estado
`borrador_no_ejecutable`/`permitido_calculo_estructural=false`: se usa solo como
referencia geométrica y para el ensayo numérico de 1 kPa. El modelo ejecutable y
analizado es el **Edificio II**.

---

## 1. Trazabilidad desde planos

Cadena completa `plano -> nodo -> elemento -> seccion -> tag`. Los nodos se
generan a partir de la posición `(u,v)` del plano (columna izquierda de la tabla
con `trazabilidad_pos_tag` de `MODELO_FE_GEOMETRIA_NODOS.json`).

**Viga (reticula x = 7.5 m, nivel CP1S):**

```
plano EII_CP1S (cota -4.01 m)
  -> posicion [7.5,0]-[7.5,8.9] (eje_reticula "x=7.5 vano[0,8.9]")
  -> nodos 600022 / 600023        (trazabilidad_pos_tag)
  -> elemento EII_CP1S_V_001      (vigas_fe) con recibe_losa=true
  -> seccion V.60/80  (0.60 x 0.80 m, seccion_geom [0.6,0.8])
  -> elementTag FE: 500000
```

**Columna (reticula A2):**

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

## 2. Estadísticas

Conteos directos de `MODELO_FE_GEOMETRIA_NODOS.json` (campo `resumen`) y de los
niveles del viewer:

| Magnitud | Valor |
|---|---|
| Nodos | **222** |
| Vigas | **175** (35 por nivel) |
| Columnas | **32** (todas `0.70x0.70`) |
| Muros | **57** |
| Diafragmas (losas rígidas) | **5** (uno por nivel) |
| Pisos / niveles | **5** (`EII_CP1S` a `EII_CP4`) |
| Springs verticales (resumen FE) | 88 |

Nodos por nivel: `EII_CP1S` 45, `EII_CP1` 45, `EII_CP2` 44, `EII_CP3` 44,
`EII_CP4` 44 (total 222). Secciones de vigas: `V.60/80` ×155, `V.30/80` ×10,
`V.40/80` ×5, `por_resolver` ×5 (estas 5 se resuelven según la hipótesis de la
solución, véase §9). Todas las vigas tienen `recibe_losa: true`.

Edificio I (solo geometría, `datos/geometria`):

| Nivel | Losas | Vigas | Muros | Col. ref. | Aberturas | Bordes libres |
|---|---|---|---|---|---|---|
| CP1 Subterráneo | 3 | 8 | 7 | 7 | 3 | 2 |
| CP1 | 16 | 10 | 4 | 18 | 4 | 5 |
| CP2 | 26 | 36 | 6 | 19 | 5 | 7 |
| CP3 | 29 | 44 | 6 | 34 | 3 | 7 |
| CP4 | 25 | 41 | 6 | 26 | 13 | 5 |
| **Total** | **99** | **139** | **29** | **104** | **28** | **26** |

## 3. Carga superficial

Definición completa en `eii_viewer.json` → `materiales` y `cargas.caso_G`.

- **Espesor de losa:** `0.15 m` (todos los niveles); excepción losa de ascensor
  `0.20 m` (nota de `caso_G`).
- **Peso unitario:** hormigón **G35**, `densidad_kg_m3 = 2500`, conversión por
  gravedad `0.00980665` → `gamma_kN_m3 = 2500·0.00980665 = 24.517 kN/m³`
  (resumen usa 24.5166). Módulo `E_c_MPa = 27805.6`, `fc_MPa = 35`.
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

- **Ensayo de validación del EI:** `G_prueba_tributacion_1kpa = 1.0 kN/m²`,
  "CARGA DE ENSAYO ... SEPARADA de las cargas reales". Es el caso de validación
  numérica del pipeline de tributación (se usa para los chequeos de reparto
  cuando se quieren aislar las cargas reales).

## 4. Áreas tributarias (3 vigas, `EII_CP2`)

Método: reparto fino por celdas del pipeline interno (`tamano_celda_inicial =
0.1 m`) según los `apoyos_validos` de cada losa; el **área tributaria por viga
queda publicada** en `eii_viewer.json` (`area_tributaria_m2`). Recinto
tributario = unión de las losas que declaran a la viga como receptor en
`apoyos_validos`; el área del recinto coincide con `area_tributaria_m2` de la
viga. Carga: `W = q_G × A_trib`; distribución equivalente `q_eq = W / L`.

| Viga | Sección | Luz L (m) | Recinto tributario (losas, polígonos m) | A_trib (m²) | q_G (kPa) | W (kN) | q_eq (kN/m) |
|---|---|---|---|---|---|---|---|
| `EII_CP2_V_003` | V.60/80 | 8.90 | `L_001` `[7.5,0][12.5,0][12.5,8.9][7.5,8.9]` ∪ `L_002` `[12.5,0][17.5,0][17.5,8.9][12.5,8.9]` | **16.3748** | 3.677 | **60.21** | **6.765** |
| `EII_CP2_V_001` | V.60/80 | 8.90 | `L_001` `[7.5,0][12.5,0][12.5,8.9][7.5,8.9]` ∪ `L_008` `[3.75,0][7.5,0][7.5,8.9][3.75,8.9]` | **15.9967** | 3.677 | **58.82** | **6.609** |
| `EII_CP2_V_020` | V.60/80 | 8.90 | `L_007` `[0,0][3.75,0][3.75,8.9][0,8.9]` ∪ `L_008` `[3.75,0][7.5,0][7.5,8.9][3.75,8.9]` | **13.5021** | 3.677 | **49.65** | **5.578** |

Los polígonos de losa son netos de aberturas (p. ej. `L_001` neta = 5.0 × 8.9 =
44.500 m², `L_007` = 33.375 m²). El reparto por celdas finas es el que alimenta
al modelo FE (caso `G_prueba` = mismo pipeline que el caso G real).

## 5. Conservación

Tolerancias adoptadas del repo (`configuracion_calculo`):
`tolerancia_relativa_area = 1e-6` y `tolerancia_relativa_carga = 1e-6`.

**(a) Conservación global del análisis (gold standard del FE).** El solver
reporta `equilibrio_vertical`:

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

## 6. Apoyos y restricciones

Tomado de `MODELO_FE_GEOMETRIA_NODOS.json` + `solucion_...V.60_80.json`
(`reacciones`).

**Tipos de apoyo/restricción usados:**

1. **Apoyos de base (placa de cimentación):** los 45 nodos del nivel
   `EII_CP1S` (`600000`–`600044`, z = −4.01 m) registran reacciones completas
   (6 DOF) → **empotramientos**. Σ reacción vertical base =
   **17,447.66 kN**, máximo individual **1,432.69 kN** (nodo `600029`).
2. **Restricción de diafragma rígido** en los niveles superiores (v. §7): la
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

## 7. Diafragmas

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

## 8. Viewer Unity

El viewer se asume **desplegado** (build pendiente por definir en otra entrega);
el **contrato de datos** que lo alimenta está publicado en `eii_viewer.json`,
`eii_esfuerzos.json` y `MODELO_FE_GEOMETRIA_NODOS.json`:

| Capa | Contenido | Devuelve |
|---|---|---|
| Niveles | 5 (cota, `espesor_losa`) | conmutador de piso |
| Losas | 28/nivel: `poligono_exterior` ± `aberturas_poligonos` (+ triangulación) | selección por losa |
| Vigas | 35/nivel: ID, sección, `eje_reticula`, `area_tributaria_m2` | IDs visibles, recinto tributario |
| Muros / Columnas | muros, columnas de referencia | IDs y secciones |
| Ejes | `grid` de columnas (p. ej. `A2`), `eje_reticula` de vigas | rotulación de ejes |
| Apoyos | base: 45 reacciones Fz (min–max: 18.4–1432.7 kN) | cubos de apoyo / color por intensidad |
| Esfuerzos | 247 elementos (`eii_esfuerzos.json`: `inicio`/`fin`, n_estaciones) | mapas de esfuerzo por elemento |
| Cargas / Material | `caso_G` (q_G, SC/PM.ADIC), G35 (γ, E, fc) | panel de cargas |

Selección: por nivel y por ID único de elemento (`EII_CP2_V_003`,
`EII_CP1_COL_004`, `M_004`...). Las áreas tributarias se muestran por viga
(`area_tributaria_m2`) y, a futuro, por muro.

## 9. Modificación del modelo (desde datos)

Modificación sencilla **sin reanálisis automático desde Unity** (Unity solo
visualiza; el reanálisis queda en el pipeline FE externo).

**(a) Cambiar hipótesis de sección** (campo `v031_hipotesis_seccion`):

```json
{ "v031_hipotesis_seccion": "V.60/80" }   ->   { "v031_hipotesis_seccion": "V.30/80" }
```

Ambas soluciones están publicadas. Impacto observado (verificado en los JSON):

| Hipótesis | P_z / R_z (kN) | max_desp_z (m) |
|---|---|---|
| V.60/80 | 29,306.0667 | 0.00076866 |
| V.30/80 | 29,216.3359 | 0.00076866 |

La diferencia (89.73 kN) es el peso propio de las 5 vigas `V_031` por nivel
(`v031_regiones`), un dato sensible a la hipótesis.

**(b) Cambiar apoyo:** en `eii_esfuerzos.json` se edita el bloque de reacciones
de un nodo base (p. ej. quitar/agregar `600029`):

```json
"600029": [0.0, 0.0, 1432.6943, 0.0, 0.0, 0.0]
```

**(c) Editar polígono tributario:** modificar `poligono_exterior` de una losa
en `eii_viewer.json` (o en `datos/geometria/*.json`) y marcar
`area_tributaria_m2` de las vigas del recinto como pendiente de recomputar:

```json
{ "poligono_exterior": [[7.5, 0.0], [12.5, 0.0], [12.5, 8.9], [7.5, 8.9]], "area_tributaria_m2": 0.0 }
```

## 10. Uso de IA — corrección de un error propuesto por el agente

Caso real, ya documentado en la auditoría del análisis estructural del Edificio II
(procedimiento interno de verificación):

**Error:** al ensamblar el equilibrio nodal, el agente sumó las fuerzas globales
de barra con su signo tal cual (`soma += globalForce`). El balance en los nodos
de base daba un residuo de **2.2e3 kN**:

```
nodo 600029:  columna 1106.46 + reaccion 1432.69 + carga -326.23 = residuo 2212.92 kN
```

**Diagnóstico:** en OpenSees, `globalForce` en cada extremo es la fuerza que el
**nodo** ejerce sobre el **elemento**, es decir, la fuerza del elemento sobre el
nodo tiene signo opuesto.

**Corrección:** restar las fuerzas de barra en el balance
(`soma -= globalForce`):

```
nodo 600029:  -1106.46 - 326.23 + 1432.69 = 0.000 kN
```

**Resultado:** el residuo nodal máximo pasó de 2.2e3 kN a **5e-7 kN**
(**1.7e-11 relativo**) en los 222 nodos y 6 DOF → `AUDITORIA: APROBADA`.
Lección incorporada al procedimiento: contrastar la convención de signos contra
un nodo aislado antes de cerrar una auditoría.