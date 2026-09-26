# PLAN y matriz de fidelidad de los modelos EI y EII

Iteración `MODELO_FIEL_1` (proyecto 1, MCOC). Este documento registra fidelidad,
brechas, pendientes y el plan de cierre por edificio y por nivel.

## 1. Reglas de la iteracion MODELO_FIEL

- **EI** (G): el peso propio confirmado de la auditoria v2 se aplica **sobre el
  modelo FE del checkpoint** con mismo `Marco` + configuracion del motor y mismo
  solver; G del checkpoint (losas + PM.ADIC) intacto. Reparto por camino
  estructural: cada id reparte su PP a los extremos de sus segmentos FE
  proporcional a su longitud (**nunca** nodo mas cercano).
- **EII** (G): la corrida reproducible del proyecto (mismo `MarcoEII`) es la
  fiel; no se modifico. Se audita contra la publicacion oficial componente a
  componente.
- Sin doble conteo: verificado por clave unica
  `(origen, elemento_id, nodo_original, receptor, carga_efectiva)`, incluyendo
  los 4 ruteos legitimos hacia el receptor 604035 (mitades de elementos
  distintos).
- `results/` del checkpoint es de **solo lectura**; todas las salidas nuevas
  viven en `modelo_fiel/{EI,EII}/` y `modelo_fiel/*`.
- **Actualización Q (q_Q 2,0→3,0 kN/m², NCh 1537:2009 Tabla 4)**: las áreas
  tributarias no cambian, por lo que **0,5·Q fiel por nivel escala ×1,5** (y el
  total 0,5·Q fiel pasa de 4 109,47→6 164,21 kN en EI y 2 629,72→3 944,57 kN en
  EII). Las tablas 2.1/2.2 y los escenarios A/B (secciones 2 y 5) reflejan ya ese
  efecto; regenerar `peso_sismico_MODELO_FIEL*` al retomar el pipeline FIEL.

## 2. Matriz de fidelidad por edificio y por nivel

### 2.1 EI (G = losas + PM.ADIC + PP confirmado)

| Nivel | z (m) | checkpoint G (kN) | PP fiel nuevo (kN) | G fiel (kN) | W sismico fiel (kN) | brecha vs publicado | estado |
|---|---|---|---|---|---|---|---|
| nucleo/sotano | -7.01 | 172.78 | 0.00 | 172.78 | 198.88 | 0 | CERRADO |
| CP1S | -4.01 | 2324.38 | 1049.69 | 3374.07 | 3734.99 | 0 | CERRADO |
| P1 | -0.05 | 6513.34 | 3340.71 | 9854.05 | 10859.78 | 0 | CERRADO |
| P2 | 3.91 | 5266.70 | 4405.81 | 9672.51 | 10521.74 | 0 | CERRADO |
| P3 | 7.87 | 5715.77 | 4530.76 | 10246.53 | 11179.06 | 0 | CERRADO |
| P4 | 11.83 | 5234.77 | 3852.25 | 9087.01 | 10021.97 | 0 | CERRADO |
| **TOTAL** | | **25227.73** | **17179.23** | **42406.96** | **46516.43** | **0** | CERRADO |

Nota: el PP por piso es el tributario nodal (la mitad de cada pieza se descarga
en el extremo inferior y la otra en el superior); no equivale a la asignacion de
la tabla publicada por elemento.

Simplificacion controlada (7/7 verificaciones en
`EI/G_EI_MODELO_FIEL_ledger.json`): 184 ids (137 vigas + 43 columnas + 4
paneles de muro) contados una sola vez; `A*L*gamma` coincide con lo auditado a
<0.05 kN; equilibrio vertical antes/despues a <0.0001 kN.

### 2.2 EII (G = reproducible, sin cambios)

| Nivel | z (m) | G fiel / checkpoint (kN) | W sismico fiel (kN) | brecha vs publicado | estado |
|---|---|---|---|---|---|
| EII_CP1S | -4.01 | 4893.85 | 5424.88 | ver 2.3 | ABIERTO |
| EII_CP1 | -0.05 | 5483.30 | 6014.32 | ver 2.3 | ABIERTO |
| EII_CP2 | 3.91 | 5438.49 | 5969.60 | ver 2.3 | ABIERTO |
| EII_CP3 | 7.87 | 5410.05 | 5941.07 | ver 2.3 | ABIERTO |
| EII_CP4 | 11.83 | 4745.31 | 5250.85 | ver 2.3 | ABIERTO |
| **TOTAL** | | **25970.999** | **28600.71** | **3335.07** | ABIERTO |

### 2.3 EII — brechas componente a componente

| Componente | Publicado (kN) | Fiel/reproducible (kN) | Diferencia (kN) | Estado |
|---|---|---|---|---|
| Losas (publicado vs mallado) | 9677.03 | 9670.76 | 6.27 | ABIERTO (losas directa 9670.75) |
| Vigas (incl. V_031) | 11585.48 | 11585.47 | 0.01 | CERRADO |
| Columnas | 1522.31 | 1522.30 | 0.01 | CERRADO |
| Muros (publicado vs pipeline A=t*L/2) | 6521.26 | 3192.47 | 3328.79 | ABIERTO |
| Ruteo 14 cargas SIN camino | - | 417.85 pendiente | 417.85 | ABIERTO |
| **Total** | **29306.07** | **25970.999** | **3335.07** | ABIERTO |

Explicacion de muros: el pipeline FE usa `A = t*(L/2)` por montante
(dos montantes por panel); la identidad geometrica `A = t*L` por panel daria
4.330,02 kN; el deficit entre publicado y pipeline es
2.191,24 + 1.137,55 = 3.328,79 kN (ver `EII/G_EII_MODELO_FIEL_ledger.json`).

## 3. Plan de cierre (pendientes explicitos)

### EI
1. **Tramos ficticios BASE->nivel** (HIPOTESIS_FE): columnas 4.223,82 kN y
   muros 3.675,18 kN. Cerrados = tramos FE reales sobre nodos de losa;
   abiertos = tramos puramente geometricos. Cuantificar con material y decidir
   inclusion.
2. **Muros de contencion del sotano**: 554,54 kN (HIPOTESIS_CIMENTACION).
   Decidir si entran a la masa sismica.
3. **V.S.I. 20/150** de CP1S: `PENDIENTE_SECCION`, pp no cuantificado.
4. **Metalicos** (V.M./P.M./P.M.I.): seccion tubular confirmada, tramo
   `PENDIENTE_TRAMO`; cuantificar y decidir inclusion.
5. Desfase P4 +0,1813 m y cajas de ascensor de un solo plano: `PENDIENTE_TRAMO`.

Incluyen a W: los abiertos 1-4 no cuantificados -> el rango del peso sismico EI
usa solo lo cuantificado (ver `peso_sismico_MODELO_FIEL.json`, rango EI
[46.516, 54.970] MN con 8.453,55 kN de pendientes cuantificados + nota).

### EII
1. **Muros (3.328,79 kN)**: unificar criterio geometrico (A=t*L por panel) o
   justificar A=t*L/2 por montante; la decision se debe documentar como la
   diferencia publicada vs reproducible.
2. **Losas (6,27 kN)**: mallado vs directa geometrica; cerrar con la directa
   (9670,75) o el mallado (9670,76).
3. **Ruteo (417,85 kN, 14 SIN camino)**: 14 cargas de PP_elemento sin camino
   estructural confirmado (cruce de vano o salida por junta) se dejan en su
   nodo original; definir camino o inercia adicional.
4. **V_031**: escenario alternativo V.30/80 (`HIPOTESIS_MODELO`); decidir
   seccion.
5. **Rigid links de franja DD**: 16 enlazados (8 a 0,15 m sobre M_003_B/M_004_B
   defensibles; 8 a 1,61-4,14 m `HIPOTESIS_ESTRUCTURAL`). Documentar como
   hipotesis estructural, no como resorte publicado.

## 4. Entregables por edificio (todo bajo `modelo_fiel/`)

| Salida | Descripcion |
|---|---|
| `EI/G_EI_MODELO_FIEL.{json,ledger.json,reacciones.csv,comparacion.json,md}` | caso G EI fiel |
| `EII/G_EII_MODELO_FIEL.{json,ledger.json,ruteos_14.csv,md}` | caso G EII fiel + auditoria |
| `peso_sismico_MODELO_FIEL.{json,csv,md}` | W = PP + 0.5 Q por piso (q=2.0) |
| `comparacion_MODELO_FIEL.{json,md}` | perfiles checkpoint vs fiel vs publicado |
| `perfiles/...` | manifests de integridad SHA-256 (crear al final) |

## 5. Iteracion MODELO_FIEL_2 (clasificacion corregida + separacion PP/PM.ADIC/Q)

Cambios de la iteracion 2 (sin tocar `results/` del checkpoint):

- **Clasificacion corregida**: el termino "fiel" de MODELO_FIEL_1 queda RETIRADO.
  - EI = `REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES`
  - EII = `REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES`
  - (ver `modelo_fiel/clasificacion_MODELO_FIEL_v2.*`)
- **Separacion explicita PP / PM.ADIC / Q** por edificio y nivel
  (`modelo_fiel/ledger_PP_PMADIC_Q.*`): nunca se llama `PP` a una suma con PM.ADIC.
- **PM.ADIC EI**: superficial (kgf/m^2 correlacionadas) aplicada por
  `tributaria -> pm_kn_m2 x area_geometrica_FE` = **10 244,14 kN** con PP losas
  14 983,59 kN (G checkpoint 25 227,73 kN intacto).
- **PM.ADIC EII**: catálogo LINEAL del plano 2024_22-700 (A=260, B=260, C=200,
  D=1500, E=260, F=260 Kg/m); sin mapeo familia->viga -> **aplicada = 0**
  (todo `PM_ADIC_PENDIENTE`).
- **Pesos sismicos**: escenario A = PP_total + 0.5Q; escenario B = PP_total +
  PM.ADIC + 0.5Q.
  - EI: A = **36 272,29 kN** / B = **46 516,43 kN** (46 516,43 v1 == escenario B)
  - EII: A = B = **28 600,71 kN** (PM.ADIC = 0)
  - rangos por pendientes: EI +8 453,54 kN; EII +3 752,91 kN
  - (ver `modelo_fiel/peso_sismico_MODELO_FIEL_v2.*`)
- **Origen de 46 516,43 kN**: 25 227,73 (G checkpoint) + 17 179,23 (PP elementos)
  = 42 406,96 (G fiel) + 0.5*8218,94 = 46 516,43 (= escenario B; ver
  `modelo_fiel/origen_46516_43_kN.*`).
- Verificaciones MODELO_FIEL_2: regresiones 26/26 + pytest 28/28 +
  manifests (`modelo_fiel/perfiles/`).
- Pendientes abiertos sin cambios (seccion 3): los entregables v2 los listan
  componente a componente.

## 6. Iteracion MODELO_FIEL_3 (inventario PP pendiente + mapeo plancha 700 + re-solve)

Cierre de la iteracion 3 (sin tocar `results/` del checkpoint ni `laboratorio_semana2/`):

- **T.2 inventario de PP pendiente EI** (`modelo_fiel/inventario_PP_pendiente_EI.*`):
  tabla de 11 columnas por elemento (1 viga, 43 columnas, 19 muros = 63) + 1 no incluida.
  Nada pendiente se convierte en confirmado; hipotesis cuantificadas NO aplicadas =
  **+8 453,55 kN** (tramos base->nivel col 4 223,82 + muro 3 675,18 + contencion 554,54).
  pp/m documentados: P.M. 300x300x20 = 1,7244; V.M. 300x300x5 = 0,4542;
  P. 70x70 hormigon = 12,0131 kN/m.
- **T.3-5 mapeo PM.ADIC EII plancha 700** (`modelo_fiel/mapeo_PMADIC_EII_plano700.*` +
  `figuras_plano700/*.png`): catalogo A-F (6 familias), conversion Kg/m->kN/m con
  g=9.80665 (A/B/E/F=2,5497; C=1,9613; D=14,7100 kN/m); todo `AMBIGUO_NO_APLICADO`
  (DXF no incluido en el arbol); aplicada = **0** (cobertura 0); figuras de auditoria
  por nivel con vigas FE/muros/losa y caja de catalogo (> 175 vigas FE, 5 niveles).
- **T.6 PM.ADIC EI aplicada** (`modelo_fiel/PMADIC_EI_aplicada.*`): tabla por losa
  (99), total = **10 244,139 kN**, delta -0,011 vs referencia, sin doble conteo.
- **T.7 casos G v3** (`modelo_fiel/EI|EII/..._v3.*`): EI **re-solve real** (OpenSeesPy)
  = 42 406,96 kN con export completo (254 reacciones, 324 desplazamientos, fuerzas);
  EII = 25 970,9994 kN (artefacto reproducible del checkpoint, export completo:
  147 reacciones, 222 desplazamientos, 264 fuerzas local/global). Ambos identicos a v2.
- **T.8 peso sismico v3** (`modelo_fiel/peso_sismico_MODELO_FIEL_v3.*`): B **PRINCIPAL**
  EI = 46 516,43 kN ; A sensibilidad = 36 272,29 kN ; EII = 28 600,71 kN.
- **T.9 verificaciones**: `regresiones_MODELO_FIEL_v3` **42/42 OK** (incluye 28/28
  unittest y regresiones v1 17/17, v2 26/26), manifest de 28 archivos, prueba aislada
  (copia de solo entrega en temp): por la dependencia `viewer_unity/.../por_viga.json`
  se registraron 23/28 + 16/17, 25/26, 40/42.
- Informe de cierre: `modelo_fiel/INFORME_MODELO_FIEL_v3.*`.

---

## MODELO_FIEL_4 (cierre de la brecha de portabilidad + reconciliacion + bloqueo)

- **T.1 portabilidad** (`data/externas/*` + `data/externas/PROCEDENCIA.md`): copias
  internas minimas con SHA-256: `catalogo_cargas_diseno_edificio_I.json`
  (2CD90C...), `areas_tributarias.csv` (54D98D...), `por_viga.json`
  (7952CE...; origen `viewer_unity/Assets/StreamingAssets/lab_data/edificios/I/tributary/`),
  `eii_viewer.json` (C3435C...; origen `analisis_estructural/edificio_II_casoG_PP_elementos/`).
  `config/cargas.json` -> `data/externas/...`. La brecha v3 (23/28 por `por_viga.json`)
  queda cerrada.
- **T.2 reconciliacion PP pendiente EI id por id**
  (`modelo_fiel/reconciliar_PP_pendiente_EI.py` + `reconciliacion_PP_pendiente_EI.{json,md,csv}`):
  9/9 checks OK; 63 pendientes; 68 filas; C1=9, C2=18, C3=4, C4=17, C5=19, C6=1;
  PP confirmado = **17 179,2261 kN** (= inventario); hipotesis 8 453,5488 solo informativas;
  aplicado = 0. Todos los P.70x70 P4 son continuacion (u, v-0,181) de columnas confirmadas.
- **T.3 bloqueo plano 700** (`modelo_fiel/BLOQUEO_PMADIC_EII_plano700.{json,md}` +
  `src/modelo_fiel/bloqueo_PMADIC_EII_plano700.py`): el 700 NO esta versionado en el
  repo (0 DXF/DWG/PDF); existe solo en
  `Datos Estructurales\2017_67-700.dxf` (18 207 984 B; sha256
  `F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF`) y
  `Union PDF's Edificio II.pdf` (14 692 764 B; sha256 `4899A8B0...`). Estado
  `BLOQUEADO_FALTA_EVIDENCIA_POSICIONAL`; 6 familias AMBIGUO_NO_APLICADO; aplicada = 0,
  cobertura 0; archivo exacto a solicitar = `2017_67-700.dxf` (ruta sugerida en el informe).
- **T.4 conservacion G_EII / peso sismico**
  (`modelo_fiel/CONSERVACION_G_EII_peso_sismico_v4.{json,md}` +
  `src/modelo_fiel/conservar_G_EII_peso_MODELO_FIEL_v4.py`): decision
  **NO_REGENERAR** (sin mapeo documental); verificados v3: G_EI 42 406,9577,
  G_EII 25 970,9994, peso EI B 46 516,4301 / A 36 272,2911, EII A==B 28 600,7138 kN.
- **T.5 regresiones e informe v4**:
  `modelo_fiel/regresiones_MODELO_FIEL_v4` **31/31 OK** en repo y en copia aislada
  (`PRUEBA_AISLADA_MODELO_FIEL_v4.json`): unittest 28/28, v1 17/17, v2 26/26,
  v3 42/42, v4 31/31, reconciliacion 9/9, bloqueo y conservacion OK; temp eliminada.
  `modelo_fiel/INFORME_MODELO_FIEL_v4.*` + `MANIFIESTO_MODELO_FIEL_v4.csv`.
- No se regeneraron EX/EY, superposicion ni D/C; ni results/ ni el checkpoint.