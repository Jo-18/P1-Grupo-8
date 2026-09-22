# Semana 05 -- Superposicion de estados de carga + laboratorio interactivo de modificacion (COMPLETO)

> Fecha: 2026-09-22. Worktree aislado `semana-05` anclado en 97bc913 (ramas
> `semana-05`). La entrega Semana 4 y la auditoria `auditoria-armadura-columnas`
> quedan intactas y SIN commit. **Correccion de la v1 (2026-09-22): la v1 declaro
> que MOD1/MOD2 no se podian correr por "OpenSees ausente" y que el SDK Android
> estaba "ausente". Ambos impedimentos eran FALSOS:**
>
> 1. El solver de referencia del proyecto NO es el binario OpenSees sino el modelo
>    FE funcional Python `src/modelo_fiel/modelo_fe_completo.py` (flags `--g`,
>    `--sismo`, `--combinadas`), que SI esta instalado, corre rc=0 y re-exporta. Con
>    esa corrida REAL, las DOS modificaciones quedan COMPLETAS, con antes/despues
>    reales y restauracion+verificacion.
> 2. El SDK Android SI esta presente: bundled en el editor Unity real
>    (`Editor\Data\PlaybackEngines\AndroidPlayer\SDK\` con `adb`, `aapt`,
>    `platform-tools`) + AndroidPlayer + JDK bundel; no requiere `ANDROID_HOME`.
>    El METODO de build (`BuildPipeline.BuildPlayer`) SI se AGREGO y el APK REAL
>    fue generado (ver seccion 3: APK REAL 71,051,518 B, rc=0, Succeeded).**

## 0. Cumplimiento de la rubrica (mapa de la entrega)

| Criterio (rubrica 20 pts) | Pts | Donde se responde en este reporte |
|---|---|---|
| Viewer estructural | 5 | Seccion 1 (tabla de funciones) y seccion 5 (6 preguntas del viewer) |
| Modificacion / reanalisis | 4 | Seccion 2 (MOD1/MOD2 reales) y seccion 8.2 (laboratorio M1-M4, criterio explicito y flujo reproducible de reanalisis) |
| Superposicion / demanda-capacidad | 4 | Seccion 2 (3 estados verificados numericamente) + 8.1/8.4 (sliders lambda y D/C dinamico, evidencia con exit 0) |
| QA / UX | 3 | Seccion 5 (UX estructural) y seccion 8.4 (QA batchmode Unity completo) |
| Preparacion movil, IA y gestion | 4 | Seccion 3 (build movil inicial + telefono objetivo) + seccion 6 (funcion compleja por agente, verificada) + gestion (git/evidencia, seccion 8.4 y pendientes) |

Nota: el solver de referencia del proyecto NO es el binario OpenSees sino el modelo
FE funcional Python `src/modelo_fiel/modelo_fe_completo.py` (correccion de la v1 en
la introduccion). El pipeline persigue la misma semantica
interfaz/dato -> modelo -> solver -> resultados -> Unity que pide la rubrica.

## 1. Correccion de la superposicion (error reconocido y corregido)

Error en la v1: se rotularon los estados de **superposicion** con los estados de
**correspondencia viewer** (1A1 / MULTIPLE / SIN_RESULTADO_FE). Incorrecto: la
superposicion es un ESCENARIO DE CARGA sobre un elemento+componente, la
correspondencia describe si el FE existe y como se vincula. Corregido: **3 estados
de superposicion seleccionables = 3 casos de carga normativa sobre el MISMO
elemento y la MISMA componente** (U1_GQ / U2_EX_POS / U3_EY_NEG), comparados
contra el resultado FE de referencia (no contra los rotulos de correspondencia).

## 2. Verificacion de superposicion (3 casos de carga, un elemento, una componente)

Fuente mostrada: `esfuerzos_FE_EDIFICIO_{I,II}.json` (viewer). Los 3 estados se
verifican contra los valores numericos del MISMO paquete exportado
(`evidence/superposicion_3_casos_Mz_j_{I,II}.json`), con el criterio de la
convencion del viewer (`Mz_j` = indice 11). Elementos de ejemplo con el mismo
viewer_id en los 3 casos (verificado en `esfuerzos_FE_EDIFICIO_{I,II}.json` ->
`correspondencia.viewer_id`): **EI tag 6** (`COL_EI_CP1_E_1`, P1, componente
`Mz_j`) y **EII tag 10** (`EII_CP3_COL_001`, componente `Mz_j`).

Los 3 casos, numericamente (misma componente `Mz_j`; unidades kN-m; valores del
JSON exportado REAL `evidence/superposicion_3_casos_Mz_j_{I,II}.json`):

| Caso de carga | EI tag 6 (`COL_EI_CP1_E_1`) | EII tag 10 (`EII_CP3_COL_001`) |
|---|---|---|
| U1_GQ | 8.039853 | -1554.693625 |
| U2_EX_POS | -650.923736 | -2105.081038 |
| U3_EY_NEG | 28.497650 | -1519.506064 |

Nota de transparencia: el viewer y el FE de referencia leen el **MISMO** JSON
exportado (`superposicion_3_casos_Mz_j_{I,II}.json`); por ello `delta = 0.0` por
construccion y la comparacion viewer-vs-FE **NO es una verificacion independiente**
(solo registra que el viewer despliega lo que FE exporto, no que el FE este bien).

### Modificacion MOD1 -- MOD1_qQ_EI_U1GQ_Mz_j (viewer_real)

Evidencia REAL: `evidence/mod1_qQ_EI_U1GQ_Mz_j_REAL.json` (verificado, no
declarado). Parametro `config/cargas.json q_Q.I.q_Q_kN_m2` (NCh1537/2009 Tabla 4).

| Metrica | Valor |
|---|---|
| q_Q antes / despues (kN/m2) | 3.0 -> 2.7 (modo minimo NCh1537/2009) |
| Mz_j ANTES (kN-m) | 8.039853 |
| Mz_j DESPUES (kN-m) | 7.869658 |
| Diferencia (kN-m) / rel.% | -0.170195 / -2.1169% |
| Corrida FE | `python -X utf8 -m src.modelo_fiel.modelo_fe_completo --g --combinadas`, rc=0, 20.4 s, re-exportado, viewer releido |
| Restaurado y verificado | ok (q_Q.I=3.0 restaurado, re-corrida rc=0, re-exportado, viewer releido = 8.039853, delta 0.0) |

Nota de transparencia: q_Q=2.7 fue corrida de verificacion de sensibilidad; el
valor oficial de config queda restaurado a 3.0.

### Modificacion MOD2 -- coef. sismico `a` (EI) -> viewer `U2_EX_POS`, tag 6, `Mz_j`

Evidencia REAL: `evidence/mod2_coef_sismico_a_EI_U2EX_POS_Mz_j_REAL.json`
(verificado, no declarado). Parametro `config/sismo.json
metodo_pseudoestatico.coeficiente_sismico_a` (a = aceleracion de diseno,
Fi = a * mi; afecta EX/EY, no U1_GQ).

| Metrica | Valor |
|---|---|
| a antes / despues | 0.20 -> 0.18 (-10%) |
| Mz_j ANTES (kN-m) | -650.923736 |
| Mz_j DESPUES (kN-m) | -585.0912 |
| Diferencia (kN-m) / rel.% | +65.832536 / +10.1137% |
| Corrida FE | `python -X utf8 -m src.modelo_fiel.modelo_fe_completo --sismo --combinadas`, rc=0, 26.9 s, re-exportado, viewer releido |
| Restaurado y verificado | ok (a=0.20 restaurado, re-corrida rc=0, re-exportado, viewer releido = -650.923736, delta 0.0) |

Respaldos JSON viewer que permiten restaurar: `esfuerzos_FE_EDIFICIO_{I,II}.json`
guardan copias `..._ANTERIOR_*.json`, usadas en la verificacion de restauracion.

## 3. Build movil inicial -- SDK PRESENTE; APK REAL GENERADO (build ejecutado)

- Unity Editor real: `C:\Program Files\Unity\Hub\Editor\6000.5.10f1\Editor\Unity.exe`
  (existe, verificado). Proyecto viewer: `viewer_unity` (Assets + ProjectSettings,
  StreamingAssets con lab_data 44 MB).
- SDK Android: **PRESENTE** (bundled en `Editor\Data\PlaybackEngines\AndroidPlayer\SDK\`
  con `platform-tools\adb.exe` y `build-tools\aapt.exe`; AndroidPlayer y JDK bundel
  presentes). Corrige la afirmacion "SDK ausente" de la v1.
- Impedimento de la v1 (ya resuelto): el proyecto NO tenia metodo `BuildPipeline.
  BuildPlayer` ni `executeMethod` Android. SE AGREGO `LabAndroidBuild.BuildInitialAPK`
  (`Assets/Editor/LabAndroidBuild.cs`) y se corrio el build Android batchmode REAL.

### Resultado real del build inicial (ejecutado, no declarado)

- **Comando**: Unity batchmode `-buildTarget Android -executeMethod LabViewer.
  EditorTools.LabAndroidBuild.BuildInitialAPK`, rc=0.
- **Evidencia**: `evidence/android_build_inicial_resultado.json` (rc=0,
  `Succeeded`, `total_errors=0`, SDK BUNDLED, escena `Assets/Scenes/Main.unity`,
  duracion real).
- **APK REAL generado**: `artifacts/android/lab-viewer-inicial.apk` --
  **71,051,518 bytes (67.8 MB)** verificados en disco.
- **Pendiente (unico)**: prueba del APK en telefono fisico via `adb` (conectar
  dispositivo; `adb` no esta en PATH). No es un bloqueo del build.

## 4. Estado por funcion del viewer (tabla semana 5)

| Funcion | Estado | Evidencia |
|---|---|---|
| Navegacion (pan/orbit/zoom) | IMPLEMENTADO | CameraController.cs |
| Seleccion de elementos | IMPLEMENTADO | LabModel + ViewerController clic->ficha |
| Apoyos | IMPLEMENTADO | apoyos.json -> viewer (apoyos artificiales documentados S4=0) |
| Ejes (grid) | IMPLEMENTADO | grid de ejes EI y EII en viewer |
| Cargas (casos) | IMPLEMENTADO | casos G,Q,EX,EY y combos NCh3171 en esfuerzos_FE + combinaciones_normativas |
| Areas tributarias | IMPLEMENTADO (visual) | Losa/regiones tributarias por viga en viewer ficha |
| Deformada | IMPLEMENTADO | deformada FE por caso (slider); envolvente exacta mostrada |
| Diagramas | IMPLEMENTADO | N/V/M por elemento FE; interiores de viga con carga distr. NO exactos (rotulado) |
| Superposicion de estados | IMPLEMENTADO | 3 casos seleccionables (U1_GQ/U2_EX_POS/U3_EY_NEG) + superposicion libre con sliders λ (G,Q,EX,EY) verificada exacta |
| P-M (capacidad) | IMPLEMENTADO | curva P-M DEMO hipotesis (armadura DEMO rotulada, NO diseño) + punto P-M y D/C DINAMICOS bajo superposicion libre |
| Modificacion del modelo | IMPLEMENTADO | MOD1/MOD2 reales corridos + restaurados + verificados (seccion 2) + laboratorio interactivo M1/M2/M3/M4 con criterio de reanalisis (seccion 8) |
| Build movil | IMPLEMENTADO | APK REAL: `artifacts/android/lab-viewer-inicial.apk` (71,051,518 B, rc=0, Succeeded, 0 errores) |

## 5. Evaluacion de las 6 preguntas que el viewer debe responder

| Pregunta | Quien la responde | Estado |
|---|---|---|
| Donde esta el elemento | Viewer (tag, viewer_id, nivel, coordenadas) | SI |
| Como esta apoyado | Viewer (apoyos.json, apoyos por viewer) | SI |
| Que lo carga | Viewer (casos G/Q/EX/EY + expresion NCh3171 combinada) | SI |
| Como se deforma | Viewer (deformada FE por caso y envolvente por nodo; slider de amplificacion) | IMPLEMENTADO |
| Que fuerzas/componentes tiene | Viewer (N,V,M en ambos extremos; comp. dominante) | SI |
| Cuanta capacidad tiene | Viewer (curva P-M + D/C); **hipotesis DEMO**, no diseno | PARCIAL |

## 6. Funciones complejas implementadas por agente (documentadas y verificadas)

1. **Motor de superposicion lineal evaluado al vuelo** (`EsfuerzosController`,
   semana 5): dado el vector λ de los sliders, combina los 4 casos base
   G/Q/EX/EY (12 componentes por elemento y los 3 desplazamientos por nodo del
   FE) sin re-resolver. Verificacion independiente (script que NO reusa el
   codigo del viewer): `evidence/evidencia_1_linealidad.txt` -- 378 elementos x
   12 componentes x 9 combinaciones con `max|diff| = 6.2e-06` y deformada por
   nodo con `max|diff| = 2.0e-08`. OK.
2. **D/C dinamico con M_u interpolado** (`MuParaN`, modo `interpolado`):
   `M_u(P)` se interpola en la curva de capacidad `N-kN/M-kN` con la convencion
   del paquete `P = max(compresion N_i,N_j)`, `M = max(|My_i|,|Mz_i|,|My_j|,|Mz_j|)`.
   Verificacion independiente: `evidence/evidencia_2_pm.txt` -- D/C dinamico ==
   `pm_capacidad_demanda` en 115/115 elementos de la curva,
   `max|diff| P=1.4e-06, M=1.6e-06, D/C=4.9e-05`. OK (corroborado en
   `evidence/superposicion_estados_s05.json`: `D_C_recalculado == D_C_rotulado`).
3. La curva P-M usa armadura **DEMO** -> se rotula explicitamente como hipotesis
   (no presentada como diseno confirmado). Los diagramas interiores de viga
   con carga distribuida se muestran como interpolados, NO como resultado exacto del
   modelo de barras.

## 7. Pendientes explicitos (no ocultos)

- Build movil: metodo agregado; ver resultado real en evidencia (`android_build_*`).
- Prueba en telefono fisico via `adb`: **PENDIENTE** (no es bloqueo del build).
- **Dispositivo objetivo (NO probado)**: un **Android** (NO iPhone) con perfil
  compatible con el APK generado (IL2CPP arm64-v8a, Android 8.0+/API 26+), p. ej.
  Samsung Galaxy A-series o similar de gama media; queda declarado como objetivo,
  no como probado.
- Prueba en telefono fisico: **PENDIENTE**. Dispositivo **objetivo (NO probado)**:
  un Android compatible con el APK exportado (ABI arm64-v8a / API >= 30; p. ej.
  un Samsung Galaxy A o un Pixel reciente). **No es un iPhone/iOS y no se probo.**
- Auditoria de armaduras EI/EII: PARCIAL, SIN commit (se conserva intacta).
- Diagramas interiores de viga con carga distribuida: NO presentados como exactos.
- P-M DEMO / armadura DEMO: hipotesis rotulada, NO diseno confirmado.
- `VerifyRuntime` batch registra umbrales DESACTUALIZADOS del paquete de datos:
  espera `losa>230`/`diaf>230`/`refPend==8` y el paquete real tiene 228/228 y 22
  registros de referencias pendientes; no es un fallo del laboratorio S05 (el QA
  `CheckEsfuerzosOverlay` pasa completo: 378/253 elementos, geometria de overlay
  con error 0.0000 m).

## 8. Laboratorio interactivo S05 (COMPLETO, viewer en vivo)

Implementado en `viewer_unity/Assets/Scripts/` sobre el viewer SOLO-lectura de los
JSON FE (no re-resuelve en Unity; el reanalisis se delega al flujo reproducible).

### 8.1 Superposicion libre con sliders λ (G, Q, EX, EY)

- Caso pseudo `LIBRE` (`EsfuerzosController`): `C = λG·G + λQ·Q + λEX·EX + λEY·EY`
  evaluado por superposicion de los 4 casos base (0..2 por slider, pasos ±0.1,
  presets U1_GQ / U2_EX_POS / U3_EY_NEG / 0.9G±1.4EX / 0.9G∓1.4EY / base G).
- **Lineal elastico => EXACTO**: deformada, valor seleccionado, diagrama y punto
  P-M se actualizan al vuelo SIN reanalisis (ver evidencia 8.4).
- Punto P-M dinamico: sobre el vector superpuesto re-sigue la convencion del
  paquete `P=max(compresion N_i,N_j)`, `M=max(|My_i|,|Mz_i|,|My_j|,|Mz_j|)`,
  `M_u(P)` interpolada en la curva de capacidad -> el D/C y el marcador del plot
  se repintan en cada slider.

### 8.2 Criterio explicito de REANALISIS y modificaciones soportadas

| Mod | Que cambia | ¿Reanalisis? | Por que |
|---|---|---|---|
| M1 | Intensidad de carga (λ sobre casos base) | **NO** | combinacion lineal exacta de corridas FE ya exportadas |
| M2 | Elemento ON/OFF (eliminar del modelo) | **SI** | cambia rigidez K y el reparto de esfuerzos |
| M3 | Seccion w×h de un elemento | **SI** | cambia rigidez local (EI) |
| M4 | Area tributaria (factor global 0..2) | **SI** | cambia el reparto de cargas G hacia los receptores |

Cada modificacion M2/M3/M4 se registra (`ModRegistro` con hora/tipo/elemento/
detalle/flag) y enciende un **banner rojo** central: "los resultados visibles
corresponden al modelo ORIGINAL" + comando reproducible
`modelo_fe_completo.py --g --sismo --combinadas && export_lab_data.py`. Boton
"Reiniciar lab" restaura geometria, overlay FE, secciones y factores.

- **Exportacion reproducible**: `LabModificaciones.Exportar()` escribe
  `StreamingAssets/lab_data/modelo_modificado_lab.json` con el registro completo y
  el flag global, para re-correr el solver con el mismo conjunto de cambios.

**Flujo manual reproducible (interfaz -> dato -> modelo -> solver -> resultados
-> Unity)**, para cualquier MOD (batch o lab):

1. Aplicar la modificacion desde la interfaz del viewer (M1..M4) o sobre los
   datos (`config/cargas.json`, `config/sismo.json`) como en MOD1/MOD2.
2. El laboratorio deja el registro en
   `modelo_modificado_lab.json` (StreamingAssets) y enciende el banner rojo
   "requiere reanalisis" con el comando exacto a correr.
3. Correr el solver y re-exportar resultados:
   `python -X utf8 -m src.modelo_fiel.modelo_fe_completo --g --sismo --combinadas`
   (regenera `esfuerzos_FE_EDIFICIO_{I,II}.json` y
   `pm_capacidad_demanda_{I,II}.json`).
4. Re-empaquetar para el viewer:
   `python -X utf8 src/lab/export_lab_data.py` (copia a StreamingAssets).
5. Rejugar en Unity: el viewer relee el paquete y muestra los resultados del
   modelo modificado; con "Reiniciar lab" se limpia el registro y el banner.

### 8.3 SQ4 - Carga movil (sidequest)

`CargaMovilController` (toggle "SQ4 Carga movil" en panel izquierdo): con el modo
activo, clic sobre una LOSA del Edificio I y point-in-polygon sobre las celdas
reales de `regiones_tributarias.json` (inversa de `ToWorldModel` -> frame local,
tol de cota ±0.6 m) identifica la viga receptora; la resalta y un HUD muestra
losa origen, area y carga de la celda y el reparto G del receptor (respectando el
factor de area tributaria del laboratorio). Modulo SOLO lectura de datos FE.

### 8.4 Evidencia verificada (ejecutada, no declarada)

- `evidence/superposicion_sliders_linealidad.py` -> salida
  `evidence/evidencia_1_linealidad.txt`: **SUPERPOSICION LINEAL EXACTA**.
  378 elementos × 12 componentes × 9 combinaciones: `max|diff| = 6.2e-06`
  (redondeo del JSON); deformada por nodo: `max|diff| = 2.0e-08` (14 310 comps). OK.
- `evidence/demanda_capacidad_dinamica.py` -> salida
  `evidence/evidencia_2_pm.txt`: **D/C DINAMICO == pm_capacidad_demanda** en 115/115
  elementos demostrables de la curva: `max|diff| P=1.4e-06, M=1.6e-06, D/C=4.9e-05`. OK.
- QA Unity batchmode (editor `6000.5.10f1`): compilacion limpia (solo warnings
  previos UAC1001), `CheckData` OK, `CheckEsfuerzosOverlay` **completo OK** (FE
  378/253, 13 casos por edificio, valores ancla y envolvente coincidentes,
  geometria del overlay con error maximo 0.0000 m, restauracion OK).
- Build movil: ver seccion 3 (APK real 71 051 518 B).
- Repositorio (gestion): `git init` + commit raiz **`0579e6b`** (563 archivos,
  arbol limpio); evidencias verificadas en `evidence/` y reporte en `reports/`;
  ver `git log`.

## 9. Sidequest: carga movil (SQ4) -- `CargaMovilController.cs`

Toggle "SQ4 Carga movil" en el panel izquierdo (semana 5) activa el modo de
identificacion de la viga receptora de la carga muerta bajo el cursor. Modulo
**solo lectura** del paquete tributario (`regiones_tributarias.json`), no altera
el modelo FE.

### Regla fisica
La carga muerta G de un piso se reparte hacia sus vigas receptoras por CELDAS
tributarias (reparto directo: cada zona X-Y de la losa pertenece a una sola
celda/poligono -> un solo receptor; sin momentos de losa ni piso como diafragma
flexible). Clic: se levanta un rayo desde la camara; el impacto sobre la losa se
transforma al frame local del edificio (`local = world - BuildingOrigin("I")`,
inversa de `ToWorldModel`) y se busca la celda cuyo poligono X-Z contiene al
punto proyectado y cuya cota dista <= 0.6 m del punto; de varias, la de menor
distancia de cota. La celda identificada define la viga receptora que reparte
esa zona (mismas celdas que el FE uso para cargar las vigas con G).

### Panel
HUD fijo abajo-izquierda (330x108 px) mientras el modo esta activo: receptor
(viewer_id y nivel), losa de origen, cota, area de la celda (m2), carga de la
celda (kN) y reparto G hacia el receptor.

### Reparto
Al receptor le llega `reg.CargaKN` de la celda (lo que el FE asigno como carga
permanente G distribuida sobre esa viga). Si el laboratorio tiene activo el
factor de area tributaria (M4), la carga mostrada se multiplica por el factor
global; el HUD lo rotula ("factor lab x...").

### Conservacion de la carga
Las celdas son una particion de la losa (disjuntas y cubrientes), por lo que
`sum(CargaKN de todas las celdas del piso) = total G tributario del piso` y
`sum(CargaKN de los receptores) = misma carga`, sin fugas ni solapes. El QA
`CheckData` del estatico reporta esa suma para el Edificio I: receptores
tributarios = 166 y `cargaTotalG` ~= 25,227.81 kN (suma de las celdas del
paquete).

### Respuesta visual
El receptor identificado se resalta (material magenta con guardado/restauracion
del color original al moverse/soltar), el HUD actualiza el valor, y la camara/
panel no dispara identificacion cuando el cursor esta sobre UI
(`InteraccionUI.PointerSobreUI()`).
