# Viewer Unity — Edificio I + Edificio II

Viewer 3D del laboratorio FE (MCOC). Crea una escena Unity desde cero que visualiza
juntos el **Edificio I** y el **Edificio II** a partir de un paquete de datos
autocontenido. Solo **lee** datos; no re-ejecuta análisis dentro de Unity ni inventa
resultados.

```
viewer_unity/
├─ Assets/
│  ├─ Scripts/          Json, Triangulator, LabModel, LabLoader,
│  │                    CameraController, ViewerController
│  ├─ Editor/           LabViewerEditor (.EditorTools) + PlaySmoke
│  ├─ Scenes/Main.unity escena de arranque (ya preparada)
│  └─ StreamingAssets/lab_data/   paquete de datos (manifest + geometry + results + tributary)
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
