# Viewer Unity — Edificio I + Edificio II

Viewer 3D del laboratorio FE (MCOC). Crea una escena Unity desde cero que visualiza
juntos el **Edificio I** y el **Edificio II** a partir de un paquete de datos
autocontenido. Solo **lee** datos; no re-ejecuta análisis dentro de Unity ni inventa
resultados.

```
viewer_unity/
├─ Assets/
│  ├─ Scripts/          Json, Triangulator, LabModel, LabLoader,
│  │                    CameraController, ViewerController,
│  │                    EsfuerzosController (overlay esfuerzos FE)
│  ├─ Editor/           LabViewerEditor (.EditorTools) + PlaySmoke
│  │                    + EsfuerzosAudit
│  ├─ Scenes/Main.unity escena de arranque (ya preparada)
│  └─ StreamingAssets/lab_data/   paquete de datos (manifest + geometry + results + tributary + esfuerzos_FE)
├─ tools/export_lab_data.py       genera el paquete desde el laboratorio FE
├─ Packages/  ProjectSettings/    proyecto Unity (Editor 6000.5.10f1)
└─ README.md
```

## Requisitos
- Unity **6000.5.10f1** (verificado en `C:\Program Files\Unity\Hub\Editor\6000.5.10f1`).
- El paquete de datos ya está en `Assets/StreamingAssets/lab_data/` (no hace falta regenerarlo).

## Cómo abrir y ejecutar
1. Abre este proyecto con Unity Hub (Add → selecciona la carpeta `viewer_unity`) en
   la versión 6000.5.10f1. La primera importación compila los scripts.
2. La escena `Assets/Scenes/Main.unity` ya está preparada y es la escena activa:
   contiene cámara, luz y `LabLoader` + `ViewerController`. Si no está abierta,
   `File → Open Scene → Assets/Scenes/Main.unity`.
3. Pulsa **Play**. La escena carga `lab_data`, construye los edificios y muestra el
   panel de control.

Si quieres regenerar la escena por menú: `LabViewer → Preparar escena principal`.

## Controles de cámara
- **Botón derecho** arrastrar → orbitar.
- **Rueda** → zoom.
- **Botón medio** (o **Shift + botón izquierdo**) → pan.
- Botones del panel: «Encuadrar todo», «Vista superior», «Vista isométrica».

## Panel / filtros
- Edificios **I** y **II** (activar/desactivar).
- Tipos de elemento: Losas, Vigas, Columnas, Muros, Diafragmas, Aberturas, Nodos,
  **Referencias pendientes** (registros `RLE-TEXTO-1`/`P.M.I.` con solo posición de rótulo,
  sin geometría física respaldada; se mantienen como marcadores de referencia, **no** se
  dibujan como columnas).
- Superpuestos: **Nodos (pilares)**, **Apoyos de base**, **IDs**, **Ejes locales**.
- «Aplicar filtros / redes» reconstruye los marcadores tras cambiar filtros.

## Inspección con clic
Haz clic en cualquier elemento: el panel derecho muestra edificio, nivel, tipo, ID,
elementTag, sección, espesor (losas), aberturas, transferencia, estado de validación,
y (si es viga o muro receptor de Edificio I) el **área tributaria**, la **carga G**
(kN), el caso de carga y las losas de origen.

## Esfuerzos FE (overlay por elemento)
Desde **Play**, el botón «ESFUERZOS FE» (panel propio a la izquierda del de inspección)
dibuja sobre la geometría (atenuada) una **tubería coloreada por elemento** en las
coordenadas exactas del modelo FE, para los **13 casos** del paquete: 4 bases
`G`/`Q`/`EX`/`EY`, las 9 combinaciones NCh3171 `U1_GQ`/`U2_EX_POS`/…/`U4_EY_NEG`
(corridas FE explícitas) y la **envolvente NCh3171 independiente** (máx |valor| por
componente, con caso y signo gobernante). Magnitudes
`N/Vy/Vz/T/My/Mz`, representación extremo i / extremo j / max-abs, escala P95 o Máximo
(mapas divergente blanco→rojo + / azul −), selección por clic (raycast → tag) con ficha
completa y diagramas locales interpolados (con advertencia). Si falta un caso → `SIN_RESULTADO`;
sin correspondencia viewer → `SIN_CORRESPONDENCIA_VIEWER`. NO recolorea la geometría
original (solo la atenúa) y NO inventa resultados. Datos: `Assets/StreamingAssets/lab_data/
edificios/{I,II}/results/esfuerzos_FE_EDIFICIO_{I,II}.json` (generados por
`entrega_03_cargas_sismo_capacidad/src/unity_esfuerzos/exportar_esfuerzos_funcional_para_viewer.py`).

Verificación automática (aceptación, determinista, valida **FE_TOTAL** y
**OVERLAY_NORMAL_MAPEADO**):
```
Unity -batchmode -nographics -quit -projectPath <viewer_unity> \
      -executeMethod LabViewer.EditorTools.LabViewerEditor.CheckEsfuerzosOverlay
```
Comprueba conteos (FE_TOTAL I 409 / II 252; overlay normal mapeado I 292 / II 237),
anclas de valores, construcción por edificio, geometría
de cada tubería (centro mundial vs centro esperado del elemento, envolvente del edificio)
y restauración → **OVERLAY ESFUERZOS FE (EDITOR): OK**. Capturas de evidencia en modo
normal: `capturas/esfuerzos_I_U2_EX_POS_N.png`, `capturas/esfuerzos_I_envolvente_N.png`,
`capturas/esfuerzos_II_envolvente_Mz.png` y `capturas/esfuerzos_II_G_Mz.png` (se generan en
batch con device gráfico; en `-nographics` se omiten). También existe el auditor de play
`LabViewer.EditorTools.EsfuerzosAudit.Run` para el Editor interactivo.

### Selección del overlay (interacción)
El clic usa `ProcesarClic` (**correspondencia viewer↔FE**, no el EFPicker más cercano a la
cámara): el primer `Physics.Raycast` identifica el `ElementRef` de la geometría original
pinchada, y los FE se eligen por `correspondencia.viewer_id == ElementRef.Id`:
- **1A1** → el FE directo del elemento;
- **CONTENIDO** → los sub-elementos FE de la misma barra viewer, se elige el segmento más
  cercano al punto real del clic y la cabecera muestra `segmento n/N` con botones ◀/▶
  (`CiclarSegmento`) para cambiar de sub-elemento;
- **SIN_CORRESPONDENCIA_VIEWER** → NO se selecciona ninguna otra barra (delante/detrás);
  el panel informa que ese elemento del viewer no tiene FE mapeado.

Solo el clic directo sobre un tubo SIN correspondencia puede seleccionar ese tubo, y esto
ocurre únicamente en el **modo de diagnóstico** ("Todos los FE"): en el modo normal los
elementos `SIN_CORRESPONDENCIA_VIEWER` (incluidos los 45 stubs analíticos del EI) quedan
**ocultos y no seleccionables**, y no participan del porcentaje de cobertura viewer↔FE.
El collider de la geometría original ya no "se salta" buscando tuberías por
raycast-all: la fuente primaria de la selección es el viewer, y el FE mostrado debe cumplir
exactamente la correspondencia (si el `viewer_id` mostrado no coincide con
`correspondencia.viewer_id` el auditor FALLA). Cabecera fija del panel con `Viewer: id ·
tipo · nivel` y `Elemento FE: tag · tipo · nivel · estado`, valores `i / j / max|abs|` del
caso y magnitud actuales, y resaltado amarillo del tubo. Añade filtros de tipología
(Vigas/Columnas/Muros) y de correspondencia (Mapeados [1A1+CONTENIDO, modo normal] / Todos
los FE [modo diagnóstico: incluye SIN_CORRESPONDENCIA_VIEWER y stubs]). El panel inferior
muestra FE_TOTAL / OVERLAY_NORMAL_MAPEADO / SIN_CORRESPONDENCIA y la cobertura que excluye
los stubs analíticos. Auditor de aceptación en
`EsfuerzosAudit.Run` (play): clics **reales de pantalla** desde varias poses de cámara en
EI y EII verificando columna→columna del nivel correcto, viga→viga del mismo piso (nunca
columna ni otro piso), dos columnas con N distintos, dos vigas con My/Mz distintos y el
fallo automático si el `viewer_id` mostrado no coincide con la correspondencia.

### Fidelidad geométrica (registro de la corrección)
Las tuberías del overlay usan un **único** sistema de coordenadas **centrado**: malla local
`PrismaLocal(-L/2, +L/2, …)` a lo largo del eje +Y del objeto, colocada/rotada una sola vez
en el `mid` mundial del elemento (eje local +Y → dir `w1-w0`) y `BoxCollider.center = 0`,
`size=(0.35, L+0.2, 0.35)`. Así los extremos renderizados caen exactamente en `w0`/`w1`.
Errores previos corregidos: (1) malla en coords mundiales + posición/rotación extra
(doble transformación → rayas flotantes); (2) malla local `0..L` con posición en `mid` (cada
tubería quedaba desplazada `L/2` hacia su extremo j). El contrato de coordenadas es
`p_i_unity = [u, cota, v]` (índice 1 = elevación); **no** se cambió el orden.
Auditor en-engine `EsfuerzosController.VerificarGeometria(tol)` compara, para **todos** los
elementos de EI y EII, los extremos renderizados `TransformPoint(LocalA/B)` contra `w0/w1`
(orden directo o invertido), `Renderer.bounds.center` contra el punto medio y la longitud
renderizada contra `|w1−w0|` (reporta máx, RMS y fuera de tolerancia; `TOL=0.01 m`).
Aceptación geométrica en `entrega_03_cargas_sismo_capacidad/tests/unity_esfuerzos/
test_geometria_overlay_fiel.py` (8 tests): error 1A1 máx 0.0005 m / RMS 0.0000 m,
envolvente y centroide FE≈viewer, columnas verticales, vigas en cota y sin elementos
fuera del edificio.

## Verificación realizada (headless)
Comandos ejecutables en batch (sin abrir el Editor) para verificar el paquete y la
construcción del modelo:

```
Unity -batchmode -nographics -quit -projectPath <viewer_unity> \
      -executeMethod LabViewer.EditorTools.LabViewerEditor.CheckData

Unity -batchmode -nographics -quit -projectPath <viewer_unity> \
      -executeMethod LabViewer.EditorTools.LabViewerEditor.VerifyRuntime

Unity -batchmode -projectPath <viewer_unity> \
      -executeMethod LabViewer.EditorTools.PlaySmoke.Run
```

Resultados de la verificación (fechados en la sesión):
- **Importación + compilación**: sin errores de compilador (Assembly-CSharp).
- **CheckData (integridad del paquete)**: OK. 13 archivos del manifest presentes;
  conteos por nivel coherentes y sin IDs duplicados; resultados EI presentes;
  tributaria I con 166 receptores y ~25 227,81 kN de carga total G.
- **VerifyRuntime (construcción real)**: OK. 972 elementos (59 col / 314 vig / 69 muros /
  239 losas / 239 diaf / 52 aberturas globales); 166 elementos con tributaria;
  251 marcados Hipotético (Edificio II).
- **PlaySmoke (modo play ~4 s)**: OK, 0 errores de runtime en Start/Update/OnGUI.

> La **verificación visual en pantalla** (renderizado, raycast de selección, captura de
> imagen) **no se puede confirmar en batchmode** (no hay superficie de render en batch).
> Se comprobó que la escena se construye y ejecuta sin excepciones; para ver el resultado
> hay que abrir el proyecto y pulsar **Play** en el Editor (paso obligatorio de la demo).

## Notas y limitaciones (coherentes con el laboratorio)
- **Colocación global I–II es PROVISIONAL** (`colocacion_global="provisional"`):
  EII se sitúa en el origen; EI se traslada comparativamente a `[60,0,0]` para poder
  verlos juntos. NO es una unión física; no comparten soportes. Para resolverlo hace
  falta correlacionar el eje D–D′ de EI con x=27.85 de EII (junta `por_correlacionar`).
- **Resultados EI** = ejecución PRIMARIA (`primera_ejecucion`, mult=1000). La ejecución
  `subdiv4` es PROVISIONAL (V.S.I., desplazamiento 12.68 m sin validar) y NO se usa.
- **Edificio II**: solo geometría/adaptaciones respaldadas; sin tributaria real ni
  solución FE. Se visualiza igual, marcado `Hipotético`/`Pendiente`. El ensayo CP2 1 kPa
  es unitario y NO se usa como dato.
- **Columnas EI**: solo P1 declara columnas explícitas (18); CP1S/P2/P3/P4 muestran 0
  (limitación del dato fuente, se documenta, no se inventa).
- Convención de casos: `G = PP + PM.ADIC` (priorizado); PP no duplicado; SC separada;
  A1 (solo CP4) no se prolonga ni se apoya artificialmente; G40 es hipótesis académica.
- No se re-ejecuta análisis FE y no se dibujan los nodos/vigas discretizados del FE como
  elementos físicos: la geometría mostrada es la geométrica fuente (losas/vigas/muros/columnas).

## Regenerar el paquete de datos (solo si cambia el exportador)
```
python tools/export_lab_data.py
```
El exportador escribe directamente en `Assets/StreamingAssets/lab_data/`. Unity carga
solo los archivos declarados en `manifest.json` (no respaldos ni ensayos unitarios).

Al final del exportador se invoca automáticamente `tools/apply_plan_frames.py`, la
**corrección candidata** del sector de acero I′–J (P3/P4): reclasifica como "Referencia
pendiente" las columnas de acero de P4 (`IpS1`, `JS2`, `JS3`, `JS4`, `JS5`, `JS8`) que
no caen sobre ninguna huella física del plano (u=44.92/47.46/49.79, RLE-PILAR de
`piso4_103.dxf`) ni tienen etiqueta legible. P3 se mantiene (IpJ/J con etiqueta
`V.M.300x300x5` = confirmado). No añade ni fabrica geometría (0 miembros nuevos, sin
duplicados) y es idempotente. Detalle en `REPORTE_QA_GEOMETRIA_UNITY.md` §11.
