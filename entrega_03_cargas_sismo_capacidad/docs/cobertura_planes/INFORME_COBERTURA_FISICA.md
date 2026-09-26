# Informe de Cobertura Física — Viewer ↔ FE

_Generado 2026-09-11; suplemento de cierre 2026-09-14 en la Sección 0; hito del
núcleo P2 (retiro de las 16 restricciones artificiales) en la Sección 0.7
(2026-09-15); hito de cierre de las 4 islas (M0 apoyos artificiales) en la
Sección 0.8 (2026-09-15)._

> **NOTA DE VIGENCIA**: el cuerpo de este documento (Secciones 1–7) corresponde al
> estado previo del perfil (2026-09-11, 409 elementos FE). El estado vigente del
> modelo fiel "cobertura completa" es el de la **Sección 0** (auditoria de cierre):
> 265 nodos FE, checks 22/22, EXPORTER SIN_RESULTADO=39, auditoria viewer
> SIN_RESULTADO=36 / FE SIN_RESULTADO=44, G reconciliado contra el inventario
> fiel. La **Sección 0.7** documenta el retiro de las 16 restricciones
> artificiales del núcleo P2 (SIN núcleo FE en el modelo). La **Sección 0.8**
> documenta el cierre de las 4 islas: el estado vigente se denomina
> **MODELO_PARCIAL_DIAGNOSTICO** (la reconciliación G contable no valida por sí
> misma el análisis completo ni los caminos de carga; ver 0.8).

---

## 0. Auditoría de cierre — modelo fiel cobertura completa (2026-09-14)

Auditoría de **solo lectura** (sin modificar topología, sin re-ejecutar pipeline).
Reacciones obtenidas con solves en memoria del mismo modelo que generó el paquete;
lista de SIN_RESULTADO del exporter obtenida con su propio método (`--dry-run`).
Los apartados 0.1–0.6 describen el estado PREVIO al hito del núcleo; el estado
vigente (post-retiro de las 16 restricciones) es el de la **Sección 0.7**.

### 0.1 Apoyos en losa (20) — auditoría por nodo

**Definición**: nodos con restricción vertical única `ops.fix(tag,0,0,1,0,0,0)`
(DOF 3 = `w`), aplicada por `_anclar_apoyos_losa` a las cadenas/cuerdas que no
alcanzan cimentación. No pertenecen a `_base_fixed`.

| Grupo | Nodos (tag) | (u, v, z) | Elemento físico incididente | Diafragma | Clasificación |
|---|---|---|---|---|---|
| Núcleo P2 — 16 | 192, 195, 200, 205, 208, 213, 218, 221, 224, 227, 232, 237, 240, 245, 250, 253 | cada una en z=3.91 (p. ej. 192=(3.55,4.0); 205=(6.45,3.9)); ver id: `muro_<u>_<v>_P3` | Nodo inferior del 1.º tramo (P2→P3) de la cuerda de muro del núcleo (demarks multinivel con arranque P2) | **Sí** — esclavo de diafragma P2 (maestro 5), dofs 1–2 acoplados | **RESTRICCIÓN ARTIFICIAL (idealización de apoyo en losa)** |
| Isla de viga CP1S — 3 | 270, 273, 276 | 270=(0.35,15.9); 273=(0.35,0.25); 276=(0.25,15.8), z=-4.01 | Nodo interior de viga (H_EI_CP1S_y0601, H_EI_CP1S_y1625, V_EI_CP1S_x0060) | No | **RESTRICCIÓN ARTIFICIAL (idealización)** |
| Isla P4 torre — 1 | 521 | (20.3, 20.15, 11.83) | Nodo interior de H_EI_CP4_y2015 y extremo inferior de postes V_EI_CP4_x2030 (16.45–20.57) | **Sí** — esclavo de diafragma P4 (maestro 128), dofs 1–2 | **RESTRICCIÓN ARTIFICIAL (idealización de apoyo de la torre en losa P4)** |

**Reacciones verticales en los 20 nodos** (solves en memoria G, EX y EY):
`Rz_G = 0.0000`, `Rz_EX = 0.0000`, `Rz_EY = 0.0000` kN; máx |Rz| = 0.0.
**No portan carga**: son **estabilizadores cinemáticos** (cierran mecanismos de
cuerdas que arrancan sobre la losa) y no generan fuerzas espurias en ningún caso.
Su peso real no está aplicado (ver 0.4).

**Camino de carga**: desde estos nodos **no existe** trayectoria por elementos FE
hacia cimentación en el modelo (no hay losa FE ni continuaos; el diafragma solo
acopla movimiento en plano). En la realidad la losa del nivel transporta su carga
a la retícula; esa transferencia **no está modelada** y se reporta como pendiente
no aplicado. Por ello **ninguno** de los 20 corresponde a un apoyo físico verificado
con fuente documental.

### 0.2 Estado de validación — NO declarado físicamente validado

Debido a (a) los 20 apoyos artificiales, (b) el peso pendiente no aplicado
(1920.57 kN) y (c) las alturas sin fuente (muros CH), **el modelo NO se declara
físicamente validado**. La verificaciones que SÍ se respaldan son de consistencia
numérica: analyze G ok (retcode 0), equilibrio G/Q, corte basal exacto, checks
22/22 del paquete, y la reconciliación de inventario de 0.4.

### 0.3 Ledger de cargas y masa sísmica (valores vigentes)

| Concepto | Valor | Nota |
|---|---|---|
| G aplicado (nodal: losas PP+PM.ADIC + PP elementos confirmados) | 40486.3893 kN | de `_cargas_G` |
| G pendiente NO aplicado (receptores sin FE: M_EI_CP1_002 ×3, M_EI_CP1_003, M_EI_CP1_004, M_EI_CP4_001, M_EI_CP4_006) | 1920.5684 kN | **inventario**, no es un caso G completo |
| G fiel reconciliado (aplicado + pendiente) | **42406.9577 kN** | = inventario de referencia; `ok_contra_fiel=True` |
| Q aplicado | 11523.3658 kN | q_Q = 3.0 kN/m² — área 3841.12 m² |

Peso sísmico Wi = G_i + 0.5·Q_i (fracción Q = 0.5, coeficiente a = 0.20, ambos
de la configuración; pseudoestático manual igual en X e Y):

| z (m) | G_kN | Q_kN | W_sismico_kN | F_lateral_kN |
|---|---|---|---|---|
| −7.0 | 172.78 | 78.32 | 211.93 | 42.39 |
| −4.0 | 3374.07 | 1082.78 | 3915.45 | 783.09 |
| −0.05 | 8078.98 | 2289.55 | 9223.75 | 1844.75 |
| +3.9 | 9672.51 | 2547.69 | 10946.36 | 2189.27 |
| +7.85 | 10246.53 | 2797.58 | 11645.32 | 2329.06 |
| +11.85 | 8941.52 | 2727.46 | 10305.25 | 2061.05 |
| +15.8 (pertiga) | 0 | 0 | 0 | 0 |
| **Total** | 40486.39 | 11523.37 | **46248.0723** | **9249.614454** |

Corte basal: V = 0.20 × W = **9249.614454 kN** (igual en X e Y; suma de Fi por
nivel = V; F_total_aplicada = F_total_esperado, diferencia 0.0; momento
accidental total 0.0 con chequeo ok; direcciones exclusivas y sentido de la
deformada ok).
**Nota de masa**: W usa G aplicado y **excluye** los 1920.57 kN pendientes
(≈4.5% del peso fiel); subestimación documentada, no es un error.

### 0.4 Reconciliación SIN_RESULTADO del exporter (39) vs inventarios (36)

Existen **dos inventarios de 36** distintos; se reconcilian ambos:

1. **Inventario de muros del modelo** (`pendientes["muros"]` = 36 cadenas/muros
   sin fuente o sin apoyo inferior confirmado). Desglose en 0.5.
2. **Auditoría viewer** (`AUDITORIA_COBERTURA_VIEWER_FE_I`) — viewer SIN = 36
   (objetos del viewer sin vínculo FE).

El **exporter** reporta SIN_RESULTADO = 39 = **35 SIN_CORRESPONDENCIA_FE + 4
PENDIENTE_DE_FUENTE**. Respecto de la lista del auditor (36), **coinciden 36** y
los **3 registros adicionales** son:

| Registro adicional | Causa en exporter | Por qué no está en la lista del auditor (36) |
|---|---|---|
| `H_EI_CP2_y2027_10.30-17.79_PLA2017-102` (viga P2) | SIN_CORRESPONDENCIA_FE | El auditor la marca MULTIPLE (cubierta geométricamente por los FE tags [377, 381]); el exporter no la vincula por tolerancia más estricta. |
| `TOWER_DIAG_P3_P4_EAST_3030_1645-2057_D2` (P4) | PENDIENTE_DE_FUENTE | El auditor la marca MULTIPLE (la diagonal D2 tiene FE, tags [530, 540]); el exporter la cataloga pendiente porque su id aparece en `topologia_I.json` (catálogo de `_pendientes_ids`). |
| `TOWER_DIAG_P3_P4_WEST_1970_1645-2057_D2` (P4) | PENDIENTE_DE_FUENTE | Ídem anterior (tags [526, 532]). |

Así, **36 + 1 + 2 = 39**. Las diagonales D1 (este/oeste) están en AMBAS listas.
Los 4 `PENDIENTE_DE_FUENTE` del exporter son las diagonales de torre D1/D2.

### 0.5 Pendientes por causa (36 muros) — dependencia de la altura del C.H.

| Causa | Registros | Ids | Depende de CH |
|---|---|---|---|
| Muro de un solo nivel sobre el nivel base (sin cota superior) — **C.H.** | 10 | M_EI_CP4_001 (×2), M_EI_CP4_002, M_EI_CP4_003, M_EI_CP4_004 (×2), M_EI_CP4_005 (×2), M_EI_CP4_006 (×2) | **SÍ** |
| Muro de un solo nivel en P1 (sin cota superior) | 8 | M_EI_CP1_001 (×2), M_EI_CP1_002 (×2), M_EI_CP1_003 (×2), M_EI_CP1_004 (×2) | No |
| Muro de un solo nivel en P2 (CP2_004/CP2_005, demarc. 13.945) | 2 | M_EI_CP2_004, M_EI_CP2_005 | No |
| Cuerda multinivel que arranca sobre el nivel base (apoyo en losa P2) | 16 | las 16 cuerdas del núcleo (mismas que tienen nodo en 0.1) | No |

Total = 36. El **C.H. permanece PENDIENTE_DE_FUENTE** (la altura del entrepiso
sobre +11.83 no tiene fuente en los PDF/DXF EI; verificado sin hits). No se
prosiguió buscando su altura en esta etapa.

### 0.6 Conclusión

- Modelo numérico consistente (G/EX/EY/9 combinaciones resuelven; corte basal
  exacto; checks 22/22). **No se declara físicamente validado**.
- 20 apoyos artificiales documentados con coords/restricción/incidencias;
  reacciones nulas; su peso está en el inventario pendiente NO aplicado.
- SIN_RESULTADO reconciliado (39 exporter vs 36 del auditor; 3 registros
  adicionales explicados) e inventario de muros (36) clasificado por causa.
- Próximo hito (fuera de esta auditoría): tablas por muro (fuente/función/cotas)
  consistentes con estos 36 y con los 20 apoyos.

### 0.7 Hito núcleo P2 — retiro de las 16 restricciones artificiales (2026-09-15)

Resuelve la auditoría 0.1: **las 16 cuerdas del núcleo quedan EXCLUIDAS del
modelo definitivo** y sus apoyos artificiales retirados (regla del usuario:
ausencia de continuidad alineada → no se inventa un apoyo; se excluye y se
declara). El modelo definitivo **no contiene el núcleo P2**; 4 apoyos isla
restantes (3 CP1S + 1 P4) siguen documentados.

#### 0.7.1 Clasificación de las 16 cuerdas (evidencia)

| Línea | Demarcaciones (da) | Espesor (m) | Nivel | Ids catalogo | Clasificación |
|---|---|---|---|---|---|
| V3.55 | 4.0, 4.181, 6.15 | 0.30 | P2 | M_EI_CP2_001; M_EI_CP3_002 (+M_EI_CP4_002 en 6.15) | (b) apoyo en losa de transferencia P2 |
| V6.45 | 3.9, 4.181, 6.15 | 0.30 | P2 | M_EI_CP2_003; M_EI_CP3_001 (+M_EI_CP4_003 en 6.15) | (b) ídem |
| H3.9 | −0.35, 6.6 | 0.20 | P2 | M_EI_CP2_007; M_EI_CP3_006 | (b) ídem |
| V3.275 | 12.266, 12.448, 13.745 | 0.25 | P2 | M_EI_CP2_004 (×2); M_EI_CP3_002 (×2) | (b) ídem |
| V6.725 | 12.266, 12.448, 13.745 | 0.25 | P2 | M_EI_CP2_005 (×2); M_EI_CP3_003 (×2) | (b) ídem |
| H13.845 | 3.275, 6.725 | 0.20 | P2 | M_EI_CP2_006; M_EI_CP3_004 | (b) ídem |

Evidencia de que **no existe apoyo físico documentado bajo el núcleo**:

- El **núcleo solo aparece en P2** (líneas verticales y horizontales de la familia
  M.H.A. e=0.20/0.25/0.30, planos 2017_67-102/103). **P1 (plan 101) no lo
  dibuja**.
- El foso/muro del ascensor en **CP1S está en ejes desplazados**: V3.400/V6.600
  (v 13.746→9.267) y V3.700/V6.300 (v 6.151→3.801), e=0.20 — **ninguna línea
  coincide** con los ejes del núcleo (V3.275/V3.55/V6.45/V6.725; H3.9/H13.845).
- **Sin vigas ni columnas en los ejes del núcleo** en P2, P3 y P4 (verificado por
  barrido de `geometria_fe`; 0 coincidencias en cada nivel).
- La losa de transferencia P2 transportaría esa carga en la realidad, pero la
  **rigidez fuera del plano de losa NO está modelada** (solo diafragma rígido en
  plano, que no la sustituye). → EXCLUSIÓN + declaración de limitación.

#### 0.7.2 Cambios de código

- `marco.py::_add_muros`: los runs multinivel con `run[0] != nivel_base` ya no
  crean nodos/elementos/fijación; se registran como `PENDIENTE_DE_FUENTE` con
  `dato_faltante='apoyo_fisico_inferior'` (línea, demarcación, nivel, espesor,
  ids) en `_componentes_excluidos_apoyo` (16). Al no existir cadenas del núcleo,
  `_anclar_apoyos_losa` ya no genera las 16 restricciones.
- `modelo_fe_completo.py::pp_elementos_confirmados`: tolera el estado coherente
  de los 4 paneles `P2->P3#0..#3` (0 ó 4 presentes); reporta sus PP como
  `muros_sin_FE_kN` (pendiente), no aplicado.
- `modelo_fe_completo.py::reconciliacion_por_familia`: suma el PP de los paneles
  excluidos al pendiente (total a reconciliar 42406.9577 kN).
- `caso_sismico.py::_verificaciones` + `modelo_fe_completo.py::correr_sismo`
  (validación por banda): la suma por nivel se valida contra el **z real de los
  nodos** del modelo (tol 0.1 m) y las cotas nominales vienen de
  `marco.niveles[].cota` — corrige el `ok:false` aparente en el nivel +7.85
  (bandas del foso −7.0 y montantes desplazados ahora cierran exacto).

#### 0.7.3 Ledger vigente (SUSTITUYE la tabla 0.3)

| Concepto | Valor | Nota |
|---|---|---|
| G aplicado (nodal) | **39128.1197 kN** | −1358.27 vs 40486.3893 (núcleo fuera) |
| G pendiente NO aplicado | **3278.8381 kN** | losas sin FE 2948.7463 (1920.5684 previos + 1028.1779 del núcleo) + PP paneles núcleo 330.0918 |
| G fiel reconciliado | **42406.9577 kN** | `delta=0.0001`, `ok_contra_fiel=True` |
| Q aplicado | **11016.2083 kN** | q_Q=3.0 kN/m² → **área 3672.07 m²** |

Peso sísmico Wi = G_i + 0.5·Q_i (coef. a=0.20, igual X e Y):

| z (m) | G_kN | Q_kN | W_sismico_kN | F_lateral_kN |
|---|---|---|---|---|
| −7.0 | 172.78 | 78.32 | 211.93 | 42.39 |
| −4.0 | 3374.07 | 1082.78 | 3915.45 | 783.09 |
| −0.05 | 8078.98 | 2289.55 | 9223.75 | 1844.75 |
| +3.9 | 9102.20 | 2352.44 | 10278.42 | 2055.68 |
| +7.85 | 9679.28 | 2603.11 | 10980.84 | 2196.17 |
| +11.85 | 8720.81 | 2610.02 | 10025.82 | 2005.16 |
| +15.8 | 0 | 0 | 0 | 0 |
| **Total** | **39128.12** | **11016.21** | **44636.2239** | **8927.244779** |

Corte basal V = 0.20 × W = **8927.244779 kN** (X e Y). Verificaciones EX/EY:
sol ok, suma por nivel cierra en las 7 bandas (`ok=true`), equilibrio horizontal
residuo ~0, momento accidental 0, direcciones exclusivas y sentido de la
deformada ok. Nota de masa: W excluye los 3278.84 kN pendientes (≈7.7 % del
peso fiel); subestimación documentada.

#### 0.7.4 Auditoría Q — área por nivel (m²) y justificación de los deltas

| Nivel | Ref Semana 2 | c/ núcleo FE | definitivo | Δ vs Ref | Causa (receptor sin FE) |
|---|---|---|---|---|---|
| −7.0 (foso) | — | 26.11 | 26.11 | +26.11 | fondo del foso (nodos profundos del ascensor) |
| CP1S (−4.01) | 387.03 | 360.93 | 360.93 | −26.11 | reclasificada al fondo (−7.0) |
| P1 (−0.05) | 1005.73 | 763.18 | 763.18 | −242.55 | 8 muros solo-P1 sin FE (M_EI_CP1_001..004) |
| P2 (3.91) | 849.23 | 849.23 | 784.15 | −65.08 | núcleo P2 (losa de transferencia no modelada) |
| P3 (7.87) | 932.52 | 932.53 | 867.70 | −64.82 | núcleo P3 |
| P4 (11.83) | 934.95 | 909.15 | 870.01 | −64.94 | 25.80 muros CP4/CH sin FE + 39.15 núcleo |
| **Total** | **4109.47** | **3841.12** | **3672.07** | **−437.40** | sin redistribuir (regla del usuario) |

Desglose por estado: (1) 4109.47 m² (inventario Semana 2, `cargo_viva_Q_I` y
`reports/semana02.md`); (2) 3841.12 m² (modelo con núcleo FE en el payload EX
previo; −268.35); (3) **3672.07 m²** (definitivo sin núcleo; −169.05 = P2 65.08
+ P3 64.82 + P4 39.15). Ninguna carga se trasladó a vecinos.

#### 0.7.5 Prueba local de camino de carga (vertical unitaria)

1 kN vertical en nodo de columna P2 (tag 12): solve G → ΣRz en apoyos reales de
base = 1.0000 kN (100 %), reacciones en los 4 apoyos-isla = 0.0 y ningún nodo de
la antigua fijación del núcleo porta reacción (las 16 restricciones ya no
existen). `analyze=0`.

#### 0.7.6 Estado final del modelo y restricciones

- **Restricciones retiradas: 16** (núcleo). **Apoyos restantes: 4 islas** —
  tags 206 (0.35,15.9,−4.01), 209 (0.35,0.25,−4.01), 212 (0.25,15.8,−4.01),
  457 (20.3,20.15,11.83); ahora portan carga real: Rz_G = 97.14 / 108.90 /
  175.29 / 0.00 kN.
- Topología definitiva: **265 nodos**, 115 columnas, 251 vigas, 2 muros FE
  (contenciones CP1S), 44 stubs, 18 conectores P4; 0 nodos aislados; 0 nodos sin
  camino de carga; 4 diafragmas (22/32/34/84 esclavos, maestros 2/5/7/128).
- Pendientes de muros: 36 (16 excluidas + 8 solo-P1 + 2 CP2-solo + 10 CH);
  `cuerdas_nucleo_en_FE=0`. PP aplicado de vigas/columnas confirmadas: 137+43;
  los 4 paneles `P2->P3` quedaron como pendiente (330.09 kN).

#### 0.7.7 Bloques y limitaciones declaradas

1. Transferencia de la losa P2 fuera del plano **no modelada** → núcleo P2
   completo **excluido** del modelo definitivo (sus cargas G/Q quedan en el
   pendiente no aplicado; afecta W y cortes, ya recomputados sin él).
2. Las 4 islas (206/209/212 y el grillaje de torre) quedaron **cerradas el
   2026-09-15**: se retiraron los apoyos artificiales con conectores/enlaces
   reales documentados (ver **Sección 0.8**). Este punto quedó **resuelto**.
3. Altura del C.H. sigue **PENDIENTE_DE_FUENTE** (10 muros CP4).
4. Peak vigentes: pesos de postes de acero de la torre y diagonales (hipótesis)
   **no aplicados**.
5. **Las combinaciones NCh3171 (`COMB_*.json`) corresponden al modelo previo y se
   marcan OBSOLETOS_POR_CAMBIO_DE_TOPOLOGIA**; la prohibición de correr
   combinaciones se mantiene durante el hito de las islas (cerrado) y se
   regenerarán solo cuando se cierre la topología del perfil (ver 0.8.4).

---

#### 0.8 Cierre de las 4 islas — 0 apoyos artificiales (2026-09-15)

Estado vigente del modelo: **MODELO_PARCIAL_DIAGNOSTICO** (la denominación
"definitivo" de secciones previas es contabilidad de inventario y **no** valida por
sí misma el análisis completo ni el camino de carga de toda geometría pendiente:
núcleo excluido, losas sin FE y pesajes PENDIENTE_DEFINICION/FUENTE). No se
commiteó nada; base `c2e2c65` intacta, todo cambio local.

##### 0.8.1 Regularización física por isla

| Isla | Nodos (tag) | Elementos físicos | Antes (apoyo artificial) | Solución respaldada | Fuente documental |
|---|---|---|---|---|---|
| 206 | 206 (0.35, 15.9, -4.01) | Viga H_y0601 del pórtico del cielo del subterráneo + losa que tributa | w-fix `_anclar_apoyos_losa` | Enlace rígido real a columnas de la retícula que bajan a cimentación (206↔16? vía enlace excéntrico 206-207, desf 0.43) | Plano CP1S (`M_EI_CP1S_001..007`, vigas del marco); `marco.cp1s_eccentric_links` |
| 209 | 209 (0.35, 0.25, -4.01) | Viga H_y1625 ídem | w-fix | Enlace rígido real (209-210, desf 0.357/0.43) a columnas con camino a base | Plano CP1S |
| 212 | 212 (0.25, 15.8, -4.01) | Viga V_x0060 ídem | w-fix | Enlace rígido real (212-213, desf 0.43/0.302) | Plano CP1S |
| 457 (grillaje torre) | 457 y anillo 458/460/461/463/465/467/469/472/475 | Grillage/anillo del arriostramiento de la torre V.E.I. sobre la losa P4 | w-fix en 457 | 10 conectores cortos elásticos al montante real más cercano (patas de torre 546/554 y columnas P4 604/608/170/173), desf ≤0.424 m | Plano P4/torre + precedente P1 (`STUB_RIGID_*`, conectores de rigidez elevada) |

Detalle de los 10 conectores del grillaje (nodo → soporte real, desfase m):
457→(20,20.45) 0.424; 458→(30,20.45) 0.424; 460→(20,20.45) 0.323;
461→(20.5,20.72) 0.250; 463→(30,20.45) 0.323; 465→(30.51,20.66) 0.228;
467→(20,16.331) 0.323; 469→(20,16.331) 0.323; 472→(30,16.331) 0.323;
475→(30,16.331) 0.323.

##### 0.8.2 Cambios de código (locales, sin commit)

- `analisis_estructural/edificio_I/src/analisis/fe/marco.py`
  - `_anclar_apoyos_losa`: usa como aristas de adyacencia de conectividad los
    enlaces rígidos registrados no-stub (`enlaces_rigidos_reales`); las islas CP1S
    ya ancladas por vínculo real **no** vuelven a recibir w-fix.
  - `_add_p4_grillaje_links(cotas)`: whitelist de los 10 puntos del anillo; pool =
    nodos P4 (17.5 ≤ u ≤ 31.5) excluyendo el anillo; conecta con `_add_stub_rigid`
    (mismo conector corto elástico de rigidez elevada ya documentado en P1);
    **nunca** `rigidLink` bajo el diafragma P4.
  - `defer_anclar_apoyos`: se difiere `_anclar_apoyos_losa` para ejecutarlo después
    de crear las patas de la torre (son el apoyo real del grillaje).
- `entrega_03_cargas_sismo_capacidad/src/modelo_fiel/modelo_fe_completo.py`
  (`MarcoFECompleto.construir`): `defer_anclar_apoyos=True` antes de
  `super().construir()`; tras `_add_p4_bridge()` + `_add_acero_torre()` llama
  `_add_p4_grillaje_links` y luego re-ancla.

##### 0.8.3 Resultado verificado

- `apoyos_losa`: **4 → 0**; `enlaces_rigidos_reales`: 6 (CP1S); conectores de
  grillaje: **+10** (máx desf 0.424 m); stubs 44 → 54; vigas FE 259 → 261;
  265 nodos; preflight **true**.
- **Separación de reacciones G**: Rz en cimentación (48 nodos `_base_fixed`) =
  **38365.4526 kN**; Rz en nodos de vínculos documentados (slaves de rigidLink /
  extremos de stub, ya conectados a base) = 762.6671 kN; **Rz en apoyos
  artificiales = 0.0000**; Σ = 39128.1197 kN = G aplicado (Δ 0.0000).
- Las 4 antiguas islas quedan **libres** (sin fijación) y sus cargas viajan por
  la conexión física real hacia cimentación (206: 97.14 / 209: 108.90 / 212:
  175.29 kN de su propio PP; 457: 0.0000 kN, el grillaje no porta carga propia).
- **Pruebas**: `tests/islas/test_cierre_islas.py` — **5 OK**: 0 apoyos
  artificiales; 0 componentes sin camino a base; preflight; enlaces documentados
  presentes (6+10, desf ≤0.45); y **carga unitaria de 1 kN en cada isla
  (206/209/212/457)** → ΣRz en base = 1.0 kN con `analyze ok` (el peso real llega
  sin fijación artificial).
- **Pipeline regenerado** (topología de islas cerradas): G eq exacto (39128.12 kN),
  Q eq exacto (11016.21 kN), EX/EY ok (corte basal 8927.2448 kN, sin cambios frente
  a la topología previa porque G/Q no cambiaron). Reconciliación G/P pendiente no
  aplicado = 3278.8381 kN (Δ 0.0001). Topología, preflight y reconciliación
  regrabadas en `MODELO_FE_COMPLETO_FUNCIONAL/`.

##### 0.8.4 Pendientes que permanecen (brechas declaradas)

1. **Núcleo P2**: excluido del FE (transferencia de la losa de transferencia con
   el núcleo no modelada). Lista de geometría pendiente en 0.8.5.
2. **Áreas de losas Q** se reportan separadas, NO como cobertura completa:
   físicas documentadas (Ref Semana 2: 4109.47 m²) vs analizadas en el FE actual
   (3672.07 m²; −169.05 m² núcleo − 268.35 m² retícula previa) vs **pendientes no
   aplicadas** (losas sin FE: 437.40 m²). El "3672.07 m²" es cobertura **parcial**.
3. **`COMB_*.json`**: **18 archivos marcados `OBSOLETOS_POR_CAMBIO_DE_TOPOLOGIA`**
   (2026-09-15, campo `estado` + `estado_reason` en cada payload, JSON revalidado).
   El exporter (`exportar_esfuerzos_funcional_para_viewer.py`) ya **bloquea** la
   escritura de paquetes de esfuerzos con combinaciones obsoletas y dejó de
   mezclarlas con la topología actual: en memoria,
   `casos_vigentes()` = G/Q/EX/EY solamente (sin combos), `casos` del paquete,
   `envolvente_NCh3171` vacía y esquema con `utilizables=false` y `pendientes`. Se
   regenerarán G/Q/EX/EY + las 9 combinaciones NCh3171 **solo al cerrar la
   topología del perfil**.
4. Pesos de postes/diagonales de la torre (hipótesis) y altura C.H.:
   **PENDIENTE_DE_FUENTE**.

##### 0.8.5 Núcleo excluido — inventario físico pendiente de representación

- **16 cuerdas de muro P2 (8 líneas)** excluidas: el tramo inferior apoya en la
  losa de transferencia (apoyo físico real) pero no hay losa FE ni conexión
  modelada; PP de los 4 paneles `P2→P3` pendiente = **330.09 kN**.
- **Losas sin FE** (área/carga Q/G pendientes, por nivel): P1 588.93 kN (12
  losas); P2 núcleo 363.38 kN (121.1 m²) + puente 19.7 m² pendiente; P3 núcleo
  907.52 kN; P4 41.06 kN (bordes sin losa FE). Registro separado de cargas
  físicas/aplicadas/pendientes (no se elimina geometría ni PP/Q para aparentar
  cobertura).

---

## 1. Resumen Ejecutivo

### 1.1 Conteos definitivos

| | Viewer | FE | Matched (1A1+CONT) | FE SIN | Viewer SIN |
|---|---|---|---|---|---|
| **Edificio I** | 306 | 409 | 329 | 80 | 67 |
| **Edificio II** | 256 | 252 | 252 | 0 | 38 |
| **TOTAL** | 562 | 661 | 581 | 80 | 105 |

### 1.2 Clasificación de FE SIN (Edificio I — 80 elementos)

| Clase | Cuenta | Descripción |
|---|---|---|
| AUX_STUB | 45 | Stub rigido (conector postes/arraigo P4, enlace P3→P4, rigidez P1) — **excluido de cobertura física** |
| AUX_SEGMENTO_VERTICAL | 29 | Segmento FE subdivide una columna/muro ya mapeado (comparte nodo) — **no es entidad física independiente** |
| FISICO_FE_DESPLAZADO | 3 | Columnas P.M. 300×300×20 cuya posición FE (candidato) difiere 2.2–5.7 m de la huella DXF REUBICADA en el viewer. Tags 648 (P2), 662 (P4), 674 (P4). **Requiere re-mesh FE** |
| PENDIENTE_DE_FUENTE | 2 | Muros no estructurales (e=0.15 mampostería) en la zona de torre. Tags 212, 215 — **excluidos de cobertura estructural** |
| PENDIENTE_DE_FUENTE | 1 | Columna P3 tag 650 (P.M. 300×300×20, u=18.96, v=14.79) — sin equivalente en viewer ni candidato P3. **Requiere verificación contra lámina 102 (banda P3)** |

### 1.3 Elementos excluidos / auxiliares

| Categoría | EI | EII | Nota |
|---|---|---|---|
| Stub rigido | 45 | 0 | Conectores analíticos |
| Aux. segmento vertical | 29 | 0 | FE subdivide columnas/muros ya mapeados |
| **Total excluido** | **74** | **0** | **No es objeto físico independiente** |

### 1.4 Elementos estructurales pendientes (requieren acción)

| Elemento | Edificio | Nivel | Sección | Posición FE (u,v) | Estado | Acción requerida |
|---|---|---|---|---|---|---|
| tag 648 | I | P2 | P.M. 300×300×20 | (18.96, 14.79) | FE desplazado vs viewer | Re-mesh FE: posición correcta es (17.50, 20.27) |
| tag 662 | I | P4 | P.M. 300×300×20 | (21.50, 21.03) | FE desplazado vs viewer | Re-mesh FE: posición correcta es (20.00, 20.45) |
| tag 674 | I | P4 | P.M. 300×300×20 | (31.55, 21.03) | FE desplazado vs viewer | Re-mesh FE: posición correcta es (30.00, 20.45) |
| tag 650 | I | P3 | P.M. 300×300×20 | (18.96, 14.79) | Sin equivalente en viewer ni candidato P3 | Verificar en lámina 102 banda P3 |
| tag 212 | I | CP1S | M 0.15×1.52×2 | (38.83, -0.60) | No estructural (mampostería) | Documentar como no estructural; excluir |
| tag 215 | I | CP1S | M 0.15×1.52×2 | (38.83, -3.65) | No estructural (mampostería) | Documentar como no estructural; excluir |

---

## 2. Correcciones realizadas en esta iteración

### 2.1 Emparejamiento de muros (exportar_esfuerzos_para_viewer.py)

**Problema raíz**: los 46 muros EI y 80 EII usaban caja estricta 2 mm para matching. Los ejes FE de los muros de contención están descentrados 0.125–0.31 m de la polilinea central del panel viewer (EI) o caen en esquinas compartidas por 2 paneles (EII). Resultado: 39 muros EI SIN y 15 EII SIN.

**Solución**:
- `TOL_MURO = 0.35` m (tolerancia de distancia punto-FE a polilinea-panel, muy por debajo de separación entre muros)
- `TOL_COLIN = 0.05` (residuo máximo de colinealidad para tie-break)
- Funciones auxiliares: `dist_punto_segmento`, `_d2`, `dist_punto_polilinea`, `_largo_seccion` (parsea `"M <e>x<L>x..."`)
- Tie-break `_resolver_esquina` (4 reglas en orden):
  1. Colinealidad: largo de sección FE = k × largo panel (residuo ≤ 0.05 × L)
  2. Interioridad de proyección: `interior = max(0, min(t, 1-t))` con t = proyección del pie sobre eje dominante
  3. Mayor extensión del panel
  4. ID lexicográficamente menor (determinista)

**Resultado**: EI muros CONTENIDO 7 → 44, SIN 39 → 2 (solo 212/215 no estructurales). EII CONTENIDO 49 → 64, SIN 15 → 0.

### 2.2 Muros torre CP1S (viewer geometry)

Se agregaron 2 muros torre al viewer CP1S que existían en el FE y en las elevaciones 801/802 pero faltaban en la geometría viewer:
- `M_EI_CP1S_008`: u=40.15, v 9.25→26.33, e=0.3 (eje I'-J; tags 200/203)
- `M_EI_CP1S_009`: u=45.4, v -6.3→-0.2, e=0.3 (eje J; tags 206/209)

### 2.3 Extensión de contenciones CP1S

Los muros M_001 (u=-0.35) y M_002 (u=21.25) se extendieron de v=-8.75 a v=-10.82 para cubrir el borde sur de la losa CP1S y permitir el matching de tags 588/590 (extensión de fundación, z -7.01→-4.01).

### 2.4 Nivelación de elementos sub-fundación (nivel_viewer)

Se añadió fallback en `nivel_viewer`: elementos con base por debajo del nivel más bajo (cota_i < CP1S) se asignan a CP1S si su extremo superior (cota_j) alcanza la cota de ese nivel. Esto permite que tags 588/590 (cota_i=-7.01, cota_j=-4.01) se clasifiquen correctamente en CP1S.

### 2.5 Clasificación FISICO_FE_DESPLAZADO

Se añadió la clase `FISICO_FE_DESPLAZADO` al clasificador para las 3 columnas P.M. 300×300×20 cuya posición FE difiere significativamente de la huella DXF REUBICADA en el viewer (ver Nota REUBICADA en la geometría viewer). Desfases: 5.67 m (tag 648), 2.24 m (tag 662), 2.28 m (tag 674). Estas 3 columnas requieren re-mesh en el modelo FE.

---

## 3. Verificación PENDIENTE_DE_FUENTE (8 elementos iniciales)

| Tag | Tipo | Nivel | Sección | Posición FE | Veredicto | Evidencia |
|---|---|---|---|---|---|---|
| 200 | muro | CP1S | M 0.3×8.54×2 | (40.15, 26.33) | **CONTENIDO** → M_EI_CP1S_008 | Muro torre elev. 801/802, se agregó al viewer |
| 203 | muro | CP1S | M 0.3×8.54×2 | (40.15, 9.25) | **CONTENIDO** → M_EI_CP1S_008 | Muro torre elev. 801/802, se agregó al viewer |
| 206 | muro | CP1S | M 0.3×3.05×2 | (45.40, -0.20) | **CONTENIDO** → M_EI_CP1S_009 | Muro torre elev. 801/802, se agregó al viewer |
| 209 | muro | CP1S | M 0.3×3.05×2 | (45.40, -6.30) | **CONTENIDO** → M_EI_CP1S_009 | Muro torre elev. 801/802, se agregó al viewer |
| 212 | muro | CP1S | M 0.15×1.52×2 | (38.83, -0.60) | **NO ESTRUCTURAL** | e=0.15 mampostería; equivale a M_EI_CP1_004 en P1 (no estructural) |
| 215 | muro | CP1S | M 0.15×1.52×2 | (38.83, -3.65) | **NO ESTRUCTURAL** | e=0.15 mampostería; equivale a M_EI_CP1_004 en P1 (no estructural) |
| 588 | muro | CP1S | M 0.2×12.62×2 | (-0.35, -10.82) | **CONTENIDO** → M_EI_CP1S_001 | Extensión de fundación (z -7.01→-4.01); extensión viewer M_001 a v=-10.82 |
| 590 | muro | CP1S | M 0.3×4.15×2 | (21.25, -10.82) | **CONTENIDO** → M_EI_CP1S_002 | Extensión de fundación (z -7.01→-4.01); extensión viewer M_002 a v=-10.82 |
| 650 | columna | P3 | P.M. 300×300×20 | (18.96, 14.79) | **PENDIENTE_DE_FUENTE** | Sin equivalente en viewer P3 ni candidato P3 (borrador incompleto); verificar en lámina 102 banda P3 |

---

## 4. Matrices de Cobertura Viewer ↔ FE

### 4.1 Edificio I

| Nivel | Tipo | Viewer Total | 1A1 | CONT | MULTI | SIN | FE Total | 1A1 | CONT | MULTI | SIN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CP1S | columna | 7 | 7 | 0 | 0 | 0 | 36 | 7 | 0 | 0 | 29 |
| CP1S | viga | 8 | 5 | 2 | 0 | 1 | 9 | 5 | 4 | 0 | 0 |
| CP1S | muro | **9** | 0 | 8 | 0 | 1 | **38** | 0 | 36 | 0 | 2 |
| P1 | columna | 18 | 18 | 0 | 0 | 0 | 18 | 18 | 0 | 0 | 0 |
| P1 | viga | 10 | 1 | 9 | 0 | 0 | 31 | 1 | 30 | 0 | 0 |
| P1 | muro | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| P2 | columna | 20 | 18 | 0 | 0 | 2 | 19 | 18 | 0 | 0 | 1 |
| P2 | viga | 39 | 27 | 9 | 0 | 3 | 45 | 27 | 18 | 0 | 0 |
| P2 | muro | 6 | 0 | 4 | 0 | 2 | 8 | 0 | 8 | 0 | 0 |
| P3 | columna | 34 | 34 | 0 | 0 | 0 | 35 | 34 | 0 | 0 | 1 |
| P3 | viga | 50 | 33 | 11 | 0 | 6 | 55 | 33 | 22 | 0 | 0 |
| P3 | muro | 6 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| P4 | columna | 32 | 6 | 0 | 0 | 26 | 8 | 6 | 0 | 0 | 2 |
| P4 | viga | 57 | 33 | 14 | 0 | 10 | 62 | 33 | 29 | 0 | 0 |
| P4 | muro | 6 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| **TOT** | | **306** | **182** | **57** | **0** | **67** | **409** | **182** | **147** | **0** | **80** |

**FE ↔ Viewer match**: 329/409 = 80.4% (182×1A1 + 147×CONT)
**Elementos FE auxiliares (excluidos de cobertura)**: 74 (45 stubs + 29 aux. segmento vertical)
**Elementos FE estructurales SIN match**: 6 (3 DESPLAZADO + 2 no-estructural + 1 pendiente)

### 4.2 Edificio II

| Nivel | Tipo | Viewer Total | 1A1 | CONT | MULTI | SIN | FE Total | 1A1 | CONT | MULTI | SIN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EII_CP1S | columna | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 |
| EII_CP1S | viga | 35 | 31 | 0 | 0 | 4 | 31 | 31 | 0 | 0 | 0 |
| EII_CP1S | muro | 8 | 0 | 8 | 0 | 0 | 18 | 0 | 18 | 0 | 0 |
| EII_CP1 | columna | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 |
| EII_CP1 | viga | 35 | 31 | 0 | 0 | 4 | 31 | 31 | 0 | 0 | 0 |
| EII_CP1 | muro | 8 | 0 | 7 | 0 | 1 | 14 | 0 | 14 | 0 | 0 |
| EII_CP2 | columna | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 |
| EII_CP2 | viga | 35 | 30 | 1 | 0 | 4 | 32 | 30 | 2 | 0 | 0 |
| EII_CP2 | muro | 8 | 0 | 8 | 0 | 0 | 16 | 0 | 16 | 0 | 0 |
| EII_CP3 | columna | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 |
| EII_CP3 | viga | 35 | 31 | 0 | 0 | 4 | 31 | 31 | 0 | 0 | 0 |
| EII_CP3 | muro | 8 | 0 | 8 | 0 | 0 | 16 | 0 | 16 | 0 | 0 |
| EII_CP4 | columna | 9 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 |
| EII_CP4 | viga | 35 | 31 | 0 | 0 | 4 | 31 | 31 | 0 | 0 | 0 |
| EII_CP4 | muro | 8 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 |
| **TOT** | | **256** | **186** | **32** | **0** | **38** | **252** | **186** | **66** | **0** | **0** |

**FE ↔ Viewer match**: 252/252 = **100%** (todos los elementos FE tienen viewer)
**Viewer SIN**: 38 = vigas que el viewer tiene pero el FE model no (vigueta liviana, TOWER_DIAG)

---

## 5. Aceptación por nivel

### Edificio I

| Nivel | Viewer match% | FE match% | Estado | Nota |
|---|---|---|---|---|
| CP1S | 88.9% (muros) / 100% (col) / 87.5% (vigas) | 94.7% (muros) / 19.4% (col) / 100% (vigas) | **CONDICIONAL** | CP1S tiene 29 cols FE auxiliares SIN (segmentos de columnas ya mapeados). Muros torre agregados. |
| P1 | 100% (col) / 100% (vigas) / 0% (muros) | 100% / 100% / 0% | **OK** | Viewer P1 tiene 4 muros sin FE (viguetas livianas, no muros estructurales). FE P1 sin muros. |
| P2 | 90% (col) / 92.3% (vigas) / 66.7% (muros) | 94.7% (col) / 100% (vigas) / 100% (muros) | **CONDICIONAL** | 2 cols viewer SIN (tag 648 P.M. DESPLAZADO + 1 aux). Muros 100%. |
| P3 | 100% (col) / 88% (vigas) / 0% (muros) | 97.1% (col) / 100% (vigas) / 0% | **CONDICIONAL** | 1 col FE SIN (tag 650, pendiente lámina 102). Vigas viewer SIN (4 aux no modelados). |
| P4 | 18.8% (col) / 82.5% (vigas) / 0% (muros) | 75% (col) / 100% (vigas) / 0% | **CONDICIONAL** | 2 cols P.M. DESPLAZADO (tags 662, 674). 26 cols viewer SIN = 70x70 que FE modela como stub/segmento. |

### Edificio II

| Nivel | Viewer match% | FE match% | Estado | Nota |
|---|---|---|---|---|
| EII_CP1S | 100% (col) / 88.6% (vigas) / 100% (muros) | 100% / 100% / 100% | **OK** | |
| EII_CP1 | 100% (col) / 88.6% (vigas) / 87.5% (muros) | 100% / 100% / 100% | **OK** | 1 muro viewer SIN (EII_CP1_M_002B) |
| EII_CP2 | 100% (col) / 88.6% (vigas) / 100% (muros) | 100% / 100% / 100% | **OK** | |
| EII_CP3 | 100% (col) / 88.6% (vigas) / 100% (muros) | 100% / 100% / 100% | **OK** | |
| EII_CP4 | 0% (col) / 88.6% (vigas) / 0% (muros) | N/A (sin FE) | **N/A** | CP4 no tiene elementos FE (nivel solo en viewer) |

---

## 6. Hallazgos de Posición

### 6.1 3 Columnas P.M. — Desfase FE vs DXF

Las 3 columnas P.M. 300×300×20 (G3S1, GS6, HS7) fueron deliberadamente REUBICADAS en el viewer durante una iteración anterior para coincidir con la huella RLE-PILAR del DXF (ver notas REUBICADA en P2.json y P4.json). El modelo FE (candidato/borrador) conserva las posiciones originales que difieren 2.2–5.7 m de la huella DXF.

| Columna | Posición FE | Posición Viewer (DXF) | Desfase | DXF huella |
|---|---|---|---|---|
| CP2 G3S1 (tag 648) | (18.96, 14.79) | (17.50, 20.27) | 5.67 m | u[17.34,17.64] v[20.12,20.42] 102.dxf |
| CP4 GS6 (tag 662) | (21.50, 21.03) | (20.00, 20.45) | 2.24 m | u[19.85,20.15] v[20.30,20.60] 103.dxf |
| CP4 HS7 (tag 674) | (31.55, 21.03) | (30.00, 20.45) | 2.28 m | u[29.85,30.15] v[20.30,20.60] 103.dxf |

**Acción**: Re-mesh del modelo FE con las posiciones corregidas (las huellas DXF son definitivas).

### 6.2 Muros torre P1/P3/P4 sin FE

Los muros viewer M_CP1_002/003 (u=40.15, 45.4), M_CP3_002/003, M_CP4_002/003 y piernas M_004/M_005 no tienen elementos FE cercanos (verificado con tolerancia 0.06 m). Los muros CP1S fueron agregados al viewer (M_008/009) para los tags 200/203/206/209. Los muros P1/P3/P4 permanecen como gap genuino del modelo FE.

---

## 7. Archivos Generados

| Archivo | Descripción |
|---|---|
| `docs/cobertura_planes/CLASIFICACION_SIN_{I,II}.json` | Clasificación analítica de FE SIN |
| `docs/cobertura_planes/CLASIFICACION_SIN_{I,II}.md` | Versión legible |
| `docs/AUDITORIA_COBERTURA_VIEWER_FE_{I,II}.json` | Matrices de cobertura |
| `viewer_unity/.../results/esfuerzos_FE_EDIFICIO_{I,II}.json` | Resultados FE con correspondencia |
| Viewer geometry: `CP1S.json` | Muros torre + extensiones de fundación agregados |
