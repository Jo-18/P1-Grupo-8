# Semana 05 -- Superposicion de estados de carga en el viewer + laboratorio v1 (INCOMPLETO, con impedimentos registrados)

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

## 1. Correccion de la superposicion (error reconocido y corregido)

Error en la v1: se rotularon los estados de **superposicion** con los estados de
**correspondencia viewer** (1A1 / MULTIPLE / SIN_RESULTADO_FE). Incorrecto: la
superposicion es un ESCENARIO DE CARGA sobre un elemento+componente, la
correspondencia describe si el FE existe y como se vincula. Corregido: **3 estados
de superposicion seleccionables = 3 casos de carga normativa sobre el MISMO
elemento y la MISMA componente** (U1_GQ / U2_EX_POS / U3_EY_NEG), comparados
contra el resultado FE de referencia (no contra los rotulos de correspondencia).

## 2. Verificacion de superposicion (3 casos de carga, un elemento, una componente)

Fuente mostrada: `esfuerzos_FE_EDIFICIO_{I,II}.json` (viewer). Fuente de
referencia: `pm_capacidad_demanda_{I,II}.json` -> `por_elemento` (mismo viewer_id,
caso dominante, D/C interpolado). Elementos de ejemplo con los mismos viewer_id en
los 3 casos: **EI tag 6** (`COL_EI_CP1_E_1`, componente `Mz_j`) y **EII tag 10**
(`EII_CP3_COL_001`, componente `Mz_j`).

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
| Deformada | PARCIAL | deformada FE por caso (slider); envolvente no exacta |
| Diagramas | PARCIAL | N/V/M por elemento FE; interiores de viga con carga distr. NO exactos |
| Superposicion de estados | IMPLEMENTADO | 3 casos seleccionables (U1_GQ/U2_EX_POS/U3_EY_NEG) sobre misma componente |
| P-M (capacidad) | PARCIAL | curva P-M DEMO hipotesis (armadura DEMO rotulada) - NO como diseno |
| Modificacion del modelo | IMPLEMENTADO | MOD1/MOD2 reales corridos + restaurados + verificados (ver secciones 2) |
| Build movil | IMPLEMENTADO | APK REAL: `artifacts/android/lab-viewer-inicial.apk` (71,051,518 B, rc=0, Succeeded, 0 errores) |

## 5. Evaluacion de las 6 preguntas que el viewer debe responder

| Pregunta | Quien la responde | Estado |
|---|---|---|
| Donde esta el elemento | Viewer (tag, viewer_id, nivel, coordenadas) | SI |
| Como esta apoyado | Viewer (apoyos.json, apoyos por viewer) | SI |
| Que lo carga | Viewer (casos G/Q/EX/EY + expresion NCh3171 combinada) | SI |
| Como se deforma | Viewer (deformada FE por caso; envolvente pendiente) | PARCIAL |
| Que fuerzas/componentes tiene | Viewer (N,V,M en ambos extremos; comp. dominante) | SI |
| Cuanta capacidad tiene | Viewer (curva P-M + D/C); **hipotesis DEMO**, no diseno | PARCIAL |

## 6. Funcion compleja implementada por agente (documentada y verificada)

Funcion: **interpolacion de mu en modo `interpolado`** del D/C viewer
(`pm_capacidad_demanda_{I,II}.json`): toma M_demanda del caso de carga y M_u_N de la
curva P-M, interpola. Verificacion independiente (no reusa el exportador): script
python recalculo D/C = M_demanda / M_u_N para EI tag 6, dio coincidencia a 1e-4
(0.6954). La curva P-M usa armadura **DEMO** -> se rotula explicitamente como
hipotesis (no presentada como diseno confirmado). Los diagramas interiores de viga
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
