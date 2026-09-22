# REPORTE QA — GEOMETRIA Y CONTROLES DE VISUALIZACION (Unity)

Proyecto: `viewer_unity` · Unity 6000.5.10f1 · Panel de control `ViewerController` + construcción `LabLoader`.

> Rubrica: los **controles de visualización deben cambiar la visibilidad real** de los
> elementos (no solo dibujar botones). Este reporte documenta qué implementa cada
> control y cómo se verifica que de verdad activa/desactiva los Renderers.

---

## 1. Controles de visualización implementados

Cada control es un **toggle independiente** que actúa de forma inmediata sobre los
`Renderer`/objetos del tipo (sin reconstruir el modelo ni perder la selección).

| Control | Alcance | Cómo aplica visibilidad |
|---|---|---|
| Losas | tipo `ElemType.Losas` | grupo de jerarquía `.../Losas` `SetActive` |
| Vigas | tipo `ElemType.Vigas` | grupo `.../Vigas` |
| Columnas | tipo `ElemType.Columnas` | grupo `.../Columnas` |
| Muros equivalentes | tipo `ElemType.Muros` | grupo `.../Muros` |
| Diafragmas | tipo `ElemType.Diafragma` | grupo `.../Diafragma` |
| Aberturas | tipo `ElemType.Abertura` | grupo `.../Abertura` |
| Nodos | superpuesto (esfera amarilla) | marcador `nodo` (por columna) |
| Apoyos de base | superpuesto (cubo verde) | marcador `apoyo` (columnas de base) |
| IDs (seleccionado) | marcador `id` | `TextMesh` solo del elemento seleccionado |
| IDs (todos) | marcador `id` | todos los elementos (opción global) |
| Ejes locales (seleccionado) | marcador `axis` | `LineRenderer` X/Y/Z del seleccionado |
| Ejes locales (todos) | marcador `axis` | todos los elementos (opción global) |
| Área tributaria | marcador `trib` | celdas reales del reparto geométrico (malla 0.25 m) dibujadas como capas traslúcidas + m²/kN por losa en inspector |

### Controles de lote
- **Mostrar todo**: enciende edificios I+II, todos los niveles y todos los tipos.
- **Ocultar todo**: apaga todos los tipos y superpuestos.
- **Restaurar filtros**: vuelve al estado inicial (todo visible salvo nodos).
- **Aislar seleccionado**: deja visible solo el edificio + nivel + tipo del elemento
  seleccionado.
- **Modo cielo P4** (previo): aísla las losas de P4/EII_CP4 con material de diagnóstico.

### Filtros independientes
- **Edificio I / II**: toggles por edificio.
- **Nivel**: toggles por nivel (CP1S…P4 / EII_CP1S…EII_CP4).
- Combine **AND**: un elemento se muestra solo si su **edificio + nivel + tipo** están
  activos (`ApplyFilters` recorre Lab/Building/Level/Type). Los marcadores (nodos/apoyos/
  ids/ejes/tributaria) respetan los mismos filtros de edificio y nivel
  (`ApplyMarkerVisibility`).

---

## 2. Comportamientos clave

- **IDs y ejes locales**: por defecto solo para el elemento **seleccionado**. Se pueden
  activar en **todos** con las opciones "IDs (todos)" / "Ejes locales (todos)".
- **Nodos y apoyos**: símbolos distinguibles (esfera amarilla nodo; cubo verde apoyo).
- **Diafragma = solamente contorno**: el diafragma (ej. `L_EI_CP1S_D_SUPERIOR_DIAF`) ya NO
  se dibuja como prisma relleno semitransparente; se renderiza como **polilínea cerrada**
  (cian `#7F9FFF`) sobre el borde de la losa + un **MeshCollider invisible** para poder
  seleccionarlo. No puede confundirse con una losa estructural adicional. Véase §3.
- **Área tributaria**: al activarla con una viga/muro de **EI** seleccionado dibuja **todas
  las celdas reales** del reparto geométrico (malla 0.25 m, `regiones_tributarias.json`) como
  capas traslúcidas verdes y muestra **m²/kN por losa** en el inspector. No se dibuja ningún
  rectángulo o área inventada.
- **Edificio II sin datos**: no existir resultado FE/tributario real → se indica
  **"no disponible"** en el inspector; no se inventa. (Véase §5.)

---

## 3. Voladizo del Edificio I — causa raíz y corrección

### 3.1 Causa raíz (visual, no geométrica)

La pieza seleccionada `L_EI_CP1S_D_SUPERIOR_DIAF` era el **overlay de diafragma** de la losa
de borde `L_EI_CP1S_D_SUPERIOR` (zona de voladizo del nivel CP1S). El diafragma se dibujaba
como un **prisma relleno semitransparente** del mismo contorno que la losa estructural,
quedando directamente sobre ella y **aparentando una losa estructural adicional** en el
voladizo. No era una losa duplicada: era el propio diafragma superpuesto a la losa.

**Fijación** (`LabLoader.BuildSlabs`): el diafragma ya **no es un prisma relleno**; se dibuja
solo como **polilínea cerrada** (cian `#7F9FFF`, ancho 0.08) sobre el borde de la losa y de
sus aberturas, en `cota + 0.05`, más un **MeshCollider invisible** (prisma delgado, colocado
por encima de la cara superior) solo para selección por clic. `Seccion = "diafragma rígido
(contorno)"`. Así no puede confundirse con geometría estructural.

### 3.2 Trazabilidad de la pieza del voladizo

| Pieza | Rol | Coordenadas comunes (u, cota, v) |
|---|---|---|
| `L_EI_CP1S_D_SUPERIOR` (losa CP1S) | losa de borde / voladizo | u∈[−0.150, 21.250], v∈[−10.819, −0.450], cota −4.01, espesor 0.15, sin aberturas |
| `L_EI_CP1S_D_SUPERIOR_DIAF` (contorno) | diafragma = overlay | mismo contorno que la losa; línea en Y_local = cota+0.05 = −3.96 |
| `H_EI_CP1S_y1695_0.200-21.600` (viga de borde) | apoyo del borde superior | v = −0.450, u∈[−0.150, 21.250] |
| `H_EI_CP1S_y2732_0.200-21.600` (viga de borde) | apoyo del borde inferior | v = −10.819, u∈[−0.150, 21.250] |
| `M_EI_CP1S_001`, `M_EI_CP1S_002` | muros de apoyo | apoyos válidos de la losa |

Conversión (transformación central): `CommonTransform(u, cota, v) → (X, Y, Z) = (u, cota, v)`;
posición mundo = `BuildingOrigin("I") + CommonTransform` (placement [60,0,0] aplicado **una**
vez). Es decir, la losa queda en Y = −4.01 (local) y el contorno del diafragma en Y = −3.96.

> Verificación: la losa y sus vigas de borde son coherentes (los tres cierran el mismo
> tramo u∈[−0.15,21.25], v∈[−10.819,−0.45]); no hay geometría inventada ni en la losa ni en
> sus apoyos. Lo anterior a la corrección era un problema de **renderizado** del diafragma.

---

## 4. Geometría tributaria real (Edificio I)

Reemplaza el rectángulo tributario *placeholder* por las **celdas reales** del reparto
geométrico determinista (`calcular_cargas_nodales`, malla 0.25 m, "soporte más cercano").

- **Exportador**: `laboratorio_semana2/src/analisis/fe/exportar_regiones_tributarias.py`.
  Re-ejecuta **solo** el reparto documentado (no modifica la solución FE) y conserva cada
  celda (centroide + área + polígono) por receptor.
- **Salida**: `Assets/StreamingAssets/lab_data/edificios/I/tributary/regiones_tributarias.json`
  — `por_nivel[LEVEL].receptores[ID] = {area_total_m2, carga_total_kN, n_losas, celdas}`, con
  `cota` por nivel; cada celda: `{u, v, area_m2, carga_kN, losa, poligono:[ring]}`.
- **Validación**: **166 receptores**; delta máximo de área vs `por_viga.json` = **0.0044 m²**
  (`verificacion_resumen_por_viga.csv`). Todas las celdas (63 502) son polígonos simples y
  válidos (0 self-intersection / área mínima 0.0625 m²).
- **Dibujo en Unity** (`ViewerController.BuildTributaryMarker`): cada celda real se renderiza
  como capa traslúcida verde (0.30,0.85,0.45,0.45) en la cota de su losa, vía la transformación
  central (`WorldPoint`) — misma transformación que las vigas, garantizando coherencia.

### Vigas de prueba (receptores reales, validación de m²/kN)

| Nivel | ID | Long. | Área tributaria | Carga | Losas contribuyentes |
|---|---|---|---|---|---|
| P1 | `V_COL_CP1_E` | 16.15 m | 36.759 m² (pv 36.76) | 228.905 kN (pv 228.91) | `L_EI_CP1_D_INF_W_E`(1.69), `..._E_F`(12.25), `L_EI_CP1_D_MED_W_E`(2.23), `..._E_F`(20.60) |
| P2 | `H_EI_CP2_y0089_0.00-10.00` | 10.00 m | 27.345 m² (pv 27.35) | 170.274 kN (pv 170.28) | `L_EI_CP2_200`(12.59), `L_EI_CP2_202`(14.76) |
| P3 | `H_EI_CP3_y0162_20.00-25.00` | 5.00 m | 24.927 m² (pv 24.93) | 155.225 kN (pv 155.22) | `L_EI_CP3_317`(5.83), `L_EI_CP3_324`(19.10) |

Las tres provienen de niveles y longitudes distintos (16.15 / 10.00 / 5.00 m); la suma de las
celdas de cada receptor reproduce el **área y la carga totales** de `por_viga.json` (validado,
dif. < 0.01 m²/kN), y cada celda cae dentro de las losas contribuyentes correctas.

---

## 5. "No disponible" vs "oculto"

- **Edificio II** no tiene resultados FE ni tributaria reales autorizados. Al seleccionar
  una viga/muro de EII, el inspector muestra **"No disponible: Edificio II sin reparto
  tributario real"** — no se oculta silenciosamente ni se reutiliza un área del I.
- Cuando un receptor no tiene dato de tributaria se indica **"sin dato"** en lugar de
  mostrarse como oculto.
- Los `elementTag` del FE no se exportan al paquete visual: el inspector informa
  **"elementTag: no disponible"** (no se fabrica correspondencia).

---

## 6. Pruebas de aceptación

Se añadió una verificación automática **en modo Play** que ejercita cada toggle sobre los
Renderers reales:

`LabViewer → Verificar controles de visualizacion (modo play)`

o en batch:
```
Unity -batchmode -projectPath <viewer_unity> \
      -executeMethod LabViewer.EditorTools.VisibilityAudit.Run
```

La rutina (`Assets/Editor/LabViewerEditor.cs → VisibilityAudit`) para cada toggle:

1. registra cuántos objetos corresponden al tipo (`TotalInModel` / `CountTypeRenderers`);
2. lo **desactiva** y confirma **0 Renderers visibles** de ese tipo;
3. lo **reactiva** y confirma que **vuelve el conteo esperado**;
4. comprueba la **combinación edificio + nivel + tipo** (vigas I+II vs solo I; nivel P4);
5. confirma **Mostrar todo / Ocultar todo**;
6. confirma que **selección / IDs / ejes** responden (marcadores aparecen/desaparecen).

Salida esperada por consola (formato por toggle):
```
[LabViewer] [Tipo Losas] modelo=239 visible_ON=239 OFF=0 ON_otra=239 -> OK
[LabViewer] [Tipo Vigas] modelo=314 visible_ON=314 OFF=0 ON_otra=314 -> OK
[LabViewer] [Tipo Columnas] modelo=145 visible_ON=145 OFF=0 ON_otra=145 -> OK
...
[LabViewer] [Nodos] ON=N OFF=0 -> OK
[LabViewer] [Apoyos] ON=M OFF=0 -> OK
[LabViewer] [IDs seleccionado] ON=1 OFF=0 -> OK
[LabViewer] [Combinacion] vigas I+II=314 solo I=... restaurado=314 -> OK
[LabViewer] [Mostrar/Ocultar todo] oculto=0 mostrado=... -> OK
[LabViewer] AUDIT CONTROLES: OK
```

> Nota: los conteos exactos dependen del paquete `lab_data` cargado (col=145, etc. según
> la geometría vigente). La verificación valida **0 cuando está apagado** y **restauración**
> al encendido, no un número fijo.

### 6.1 Verificación automatizada de la tributaria real (`TributaryAudit`)

Además del audit de controles, se añade una verificación **en modo Play** de la integración
del área tributaria real (celdas del reparto). Selecciona las **tres vigas documentadas** en
§4 y confirma en cada una: el número de regiones adjuntas, que el overlay dibujado en escena
(coincide con ese número de celdas), el área y la carga totales de `por_viga`, y la ejecución
fuente; además comprueba que los **tres overlays son diferentes** y que al **apagar** el
control se destruye el overlay anterior. También verifica que una viga de **Edificio II** no
adjunta celdas (solo el marcador "no disponible").

```
Unity -batchmode -quit -projectPath <viewer_unity> \
      -executeMethod LabViewer.EditorTools.TributaryAudit.Run
```

Salida esperada (por viga, con `regions/dibujadas` y totales):
```
[LabViewer] [Tribu P1 V_COL_CP1_E] regions_modelo=582 dibujadas=582 area=36.76 carga=228.91 fuente=primera_ejecucion -> OK
[LabViewer] [Tribu P2 H_EI_CP2_y0089_0.00-10.00] regions_modelo=426 dibujadas=426 area=27.35 carga=170.28 fuente=primera_ejecucion -> OK
[LabViewer] [Tribu P3 H_EI_CP3_y0162_20.00-25.00] regions_modelo=390 dibujadas=390 area=24.93 carga=155.22 fuente=primera_ejecucion -> OK
[LabViewer] [Overlays distintos] 582,426,390 -> OK
[LabViewer] [Overlay apagado] trib_restantes=0 -> OK
[LabViewer] [EII] viga=... regiones=0 marcadores_trib=... -> OK
[LabViewer] AUDIT TRIBUTARIA: OK
```

> Requiere la escena en modo Play (Renderers reales); se ejecuta desde el menú
> **LabViewer → Verificar area tributaria real (modo play)** o en batch como arriba.

---

## 7. Prueba manual en Play (capturas)

Pasos obligatorios en el Editor (la verificación visual/render requiere pantalla):

1. Abrir `Assets/Scenes/Main.unity` y pulsar **Play**.
2. **Solo vigas**: `Vigas` ON, resto OFF → capturar.
3. **Solo columnas**: `Columnas` ON, resto OFF → capturar.
4. **Solo muros**: `Muros` ON, resto OFF → capturar.
5. **Solo losas**: `Losas` ON, resto OFF → capturar.
6. **Nodos y apoyos**: activar `Nodos` y `Apoyos de base` → capturar (esferas + cubos).
7. **Elemento seleccionado con ID y ejes**: clic en un elemento, activar `IDs
   (seleccionado)` y `Ejes locales (seleccionado)` → capturar.
8. **Diafragma-contorno (voladizo CP1S)**: clic en `L_EI_CP1S_D_SUPERIOR_DIAF` en el voladizo
   del Edificio I → debe verse **solo el contorno cian** (sin relleno) → capturar (verifica la
   corrección del voladizo).
9. **Área tributaria real — EI (16 m)**: clic en `V_COL_CP1_E` (P1) y activar `Area
   tributaria (seleccionado)` → se dibujan las **celdas reales** (capas verdes 0.25 m sobre las
   4 losas) y el inspector muestra m²/kN por losa y totales → capturar.
10. **Área tributaria real — EI corta (5 m)**: clic en `H_EI_CP3_y0162_20.00-25.00` (P3) →
    celdas sobre `L_EI_CP3_317+324` → capturar (confirma celdas entre vigas, sin rectángulo).
11. **Edificio II**: clic en una viga de EII y activar `Area tributaria` → el inspector indica
    **"No disponible: Edificio II sin reparto tributario real"** (sin dibujo) → capturar.

> Estas capturas se toman manualmente en el Editor. La verificación automática de
> aceptación (§6) valida los cambios de visibilidad de forma reproducible sin capturas.

---

## 8. Estado

- Controles de visualización **implementados** en `ViewerController.cs` (toggles
  independientes, lote, aislar, leyenda, ID/ejes globales, tributaria real).
- **Diafragma-contorno** (corrección del voladizo) implementado en `LabLoader.BuildSlabs`.
- **Regiones tributarias reales** (celdas 0.25 m) exportadas y validadas vs `por_viga.json`
  (166 receptores, delta máx 0.0044 m²) y dibujadas en `BuildTributaryMarker`.
- El archivo `regiones_tributarias.json` está declarado en el `manifest.json` (`archivos`) y
  lo carga `LabLoader.LoadTributaryRegions` (se vincula a cada receptor por su ID original vía
  `AttachTribRegions`). Solo se instancian las celdas del receptor **seleccionado** (nunca las
  63 502 al iniciar).
- **Verificación automatizada de la integración** añadida: `TributaryAudit` (modo Play), §6.1.
- Verificación de aceptación **implementada** en `LabViewerEditor.cs`
  (`VisibilityAudit`, modo play).
- **Corrección "0.5 × 0.8"** (§9) aplicada: el exportador ahora emite `ancho`/`peralte`
  resueltos de la etiqueta de sección para vigas EI; el viewer (`BuildBeams`) se ha
  endurecido para resolver de la etiqueta cuando los campos están ausentes.
- Falta por ejecutar en el Editor (requiere pantalla):
  1. confirmar **0 errores CS** en Console al reimportar los scripts;
  2. correr `Verificar controles de visualizacion (modo play)` y revisar `AUDIT: OK`;
  3. tomar las **capturas** de la §7 y adjuntarlas aquí.

---

## 9. Investigación de sobresaliente horizontal y sección "V. 60/80" vs "0.5 × 0.8"

### 9.1 Sobresaliente horizontal — conclusión

La geometría exportada de las **losas estructurales** es correcta: las aristas coinciden
con las **líneas centrales** de sus apoyos (vigas/muros), de modo que el soporte cubre la
arista de la losa por su mitad de ancho/espesor (inset). **No hay sobresaliente** en las
losas principales.

Métrica corregida (por-lado): para cada arista de losa, se selecciona el soporte **paralelo**
más cercano **del lado exterior** (distancia perpendicular a la línea central del soporte) y
se calcula `overhang = distancia_eje − medio-ancho`. Resultado: todas las losas estructurales
(D_INF, D_MED, y las numeradas de P2/P3/P4) muestran **overhang negativo** (inset):

| Nivel | Losa representativa | Arista | Soporte | Distancia al eje | half-width | overhang |
|-------|-------------------|--------|---------|-----------------|------------|----------|
| P1 | `L_EI_CP1_D_INF_W_E` | Norte (v=16.15) | `GV_CP1_G3` | 0.000 m | 0.30 m | **−0.300 m** |
| P1 | `L_EI_CP1_D_INF_W_E` | Oeste (u=−0.25) | `M_EI_CP1_001` | 0.000 m | 0.10 m | **−0.100 m** |
| P1 | `L_EI_CP1_D_INF_W_E` | Este (u=0.00) | `V_COL_CP1_E` | 0.000 m | 0.30 m | **−0.300 m** |
| P1 | `L_EI_CP1_D_INF_W_E` | Sur (v=8.90) | `GV_CP1_G2` | 0.000 m | 0.30 m | **−0.300 m** |

Los únicos valores positivos son los **voladizos documentados** (`D_VOL_ESTE_*`,
`D_ATRIO_ESTE`, `D_VOLADIZO_*`), que por definición se extienden más allá de su apoyo
más cercano. Los valores enormes (5–45 m) del análisis previo eran **artefactos de
atribución** (soporte paralelo lejano atribuido a una arista libre de cantilever).

### 9.2 Sección "V. 60/80" vs "0.5 × 0.8" — causa raíz

**Problema**: en los niveles CP1S, P2, P3 y P4, el inspector mostraba **"0.5 × 0.8 m"**
para vigas etiquetadas `V. 60/80` (debería ser **0.6 × 0.8 m**).

**Causa raíz** (doble):

1. **Exportador** (`export_lab_data.py` → `export_ei`): solo emitía el campo `ancho`
   cuando la fuente lo tenía (P1, porque la fuente P1 sí lo incluye); en CP1S/P2/P3/P4
   la fuente **no** tiene `ancho` ni `peralte` → se exportaban como `null`.

2. **Visor** (`LabLoader.BuildBeams:397-400`):
   ```
   float w = Json.Num(V, "ancho", 0.5f);  // 0.5 default
   float h = Json.Num(V, "peralte", 0.8f); // 0.8 default
   if (w <= 0 || h <= 0) TryParseSection(sec, ...);
   ```
   Como `peralte` se exportaba `null` → `h = 0.8` (default, > 0) → el `TryParseSection`
   **nunca se ejecutaba** → `w` quedaba en **0.5** (el default) en vez de 0.6.

En P1, `ancho=0.6` sí estaba presente → `w=0.6` → correcto por coincidencia. Pero en los
otros 4 niveles, `ancho=null` → `w=0.5` → incorrecto. Todos los 163 vigas `V. 60/80` de
CP1S+P2+P3+P4 se dibujaban **0.10 m más angostas** de lo documentado.

### 9.3 Corrección aplicada

1. **Exportador** (`export_lab_data.py`): se añadió `_parse_beam_section(sec_name)` que
   extrae `(w, h)` de la etiqueta (formato `N/M`, centímetros → metros). Para vigas EI:
   - `ancho`: usa el valor explícito de la fuente si existe; si no, el de la etiqueta.
   - `peralte`: siempre de la etiqueta (la fuente EI nunca lo entrega).
   - Se emite `ancho` y `peralte` en el JSON exportado para todas las vigas.

2. **Visor** (`LabLoader.BuildBeams:400`): endurecido para que cuando un campo
   (`ancho`/`peralte`) esté ausente del JSON o sea <= 0, se resuelva de la etiqueta de
   sección. Esto protege tanto contra JSONs regenerados como contra JSONs anteriores a la
   corrección.

3. **Manifiesto** (`export_lab_data.py`): `_with_tributary_regions` asegura que
   `regiones_tributarias.json` se incluya en el manifiesto (preservado de la regeneración).

**Estado post-corrección**: todos los vigas `V. 60/80` de CP1S/P1/P2/P3/P4 ahora tienen
`ancho=0.6, peralte=0.8` (verificado en los 5 niveles). Las únicas excepciones son:
- `GV_CP1_GE_este` (P1): `ancho=0.3` (la fuente lo especifica explícitamente como
  viga más angosta del este).
- `V_EI_CP1S_x1010` (CP1S): sección `M.H.A. e=30` (no parseable por formato distinto;
  se mantiene el default del viewer).

### 9.4 Discrepancia vertical (cota) — estado y alcance

**Lo que se sabe con certeza:**
1. `N.S. losa` = **Nivel Superior de la losa** (cara superior). Evidencia SOLO en Edificio II
   (`informe_pendientes_EII_CP1S.md` línea 4 y CP4). **No hay evidencia equivalente para el
   Edificio I en los archivos revisados**; no se generaliza un informe del II al I sin respaldo.
2. La losa se extruye **hacia abajo** desde la cota (`PrismMesh(topY = cota)`, fondo en
   cota−e). La cara superior de la losa coincide con la cota del nivel.
3. viga/muro/columna se dibujan actualmente **referenciadas al eje de la cota** (no al
   caraso de la losa). Es la lectura por defecto que NO debe presentarse como geometría
   física validada.

**Lo que NO está confirmado (no se declaró válido):**
- Que los 0.80 m de "V. 60/80" correspondan al canto total de la viga bajo la losa: podría
  ser el canto total o el descuelgue bajo la losa. **No se encontró corte/detalle que lo
  resuelva en esta sesión.** La posición que produciría 0.95 m desde cara superior de losa a
  fondo de viga (0.15 losa + 0.80 viga) queda SIN respaldo y NO se implementó.
- Que una columna deba intimidar en el caraso (base −4.01→−4.16): el tramo que llega a la
  cota intersecta la losa [cota−e, cota] y **no deja un hueco bajo ella**. Desplazarla sin
  evidencia independiente sería inventar geometría; se descartó.
- Que un muro deba sustituirse por un intervalo genérico centrado bajo la losa: sus
  extremos documentados no fueron verificados; no se aplicó.

**Decisión en esta sesión:** los desplazamientos verticales especulativos (eje de viga a
`cota−e−h/2`, muro a `cota−e−hStory/2`, columna a `[levelBase−e, cota−e]`) se **revirtieron
completamente** en `LabLoader.cs`. No se implementa ninguna de las dos interpretaciones como
geometría física validada; el visualizador conserva la versión anterior con sus limitaciones
conocidas. Un eventual ajuste queda supeditado a un **corte/detalle único** (archivo, lámina,
dimensiones, coordenadas) que respalde el encuentro losa–viga–columna antes de generalizar.

### 9.5 Revisión de las láminas originales de `Datos Estructurales` (Edificio I vs. Edificio II)

Revisión de las láminas fuente (PDF planos) para separar qué respalda la semántica de la cota
y la ubicación física de losa/viga/columna en cada edificio. **No alteró ningún offset; no se
declaró geometría física validada.**

**Edificio II** — `Planos en PDF Edificio II\2024_22-*.pdf`:
- `informe_pendientes_EII_CP1S.md` (línea 4) y `informe_pendientes_EII_CP4.md`: el CUADRO DE
  NIVELES etiqueta cada fila como **"N.S. losa"** (CP1S `-4.01`, CP4 `+11.83`). Es la única
  confirmación textual: **cota = N.S. losa = nivel superior (cara superior) de la losa**,
  y es la fuente del contrato analítico (cota como Z nodal).
- `2024_22-101.dxf`/`2024_22-102.dxf` (CP1S/CP4): planos de cielo piso; `LOSA`, pasadas, vigas.
- Union PDF (22 pág.): solo una página con `LOSA` y cotas absolutas `52.46/52.62`; sin texto de
  CORTE/SECCIÓN extraíble.

**Edificio I** — `Planos en PDF Edificio I\2017_67-*.pdf` (38 láminas):
- Láminas 100–103 (armadura/encofrado de CP1S/CP1): vigas `V. 60/80`, `V. 20/80`, `V. 15/VAR`,
  `V. 20/130`; losa `e=15/20/30`; muros `M.H.A. e=20/25/30`; pilares `70x70`, `30x30`,
  `P.M.I. 300x300x5`; pasadas `45/15`, `45/30`.
- Lamina 101: **`N.S.M. +0.95`** = **N.S. = "Nivel Superior" de Muro** (cara superior = +0.95),
  junto a un muro `M.H.A. e=30`. Corrobora la convención "N.S. = nivel superior de elemento"
  **aplicada a un muro**, NO textualmente a la losa.
- Informe `informe_pendientes_cielo_piso_2.md` (Edificio I): lamina `2017_67-102` =
  "PLANTA CIELO PISO 2, Nivel **+3.91 m**, LOSA **e=15 (S.I.C.)**"; cita las elevaciones
  `2017_67-301/304` como evidencia de continuidad vertical bajo +3.91.
- Láminas 300–310 (ELEVACIONES, escala 1:50): vigas de fachada/alineación `V. 20/80`,
  `V. 15/125`, `V.F. 15/225`, `V.F. 20/220`, `V. 20/130`; niveles 1°S/1°S-2°-3°-4°. Cota
  `-5.21` en lamina 309.
- Láminas 400/500/600/700/800 (detalles constructivos): **dibujo sin capa de texto extraíble**
  (solo "ESCALA"); las cotas de las secciones de viga NO son legibles por OCR ni texto con las
  herramientas disponibles. Se generaron renders para inspección visual:
  `%TEMP%\opencode\EI_LAM101_NSM_muro.png`, `EI_LAM301_elevaciones.png`, `EI_LAM102.png`,
  `EI_LAM304.png`, `EI_LAM400.png`, `EI_LAM500.png`, `EI_LAM800.png`.

**Conclusión de la revisión (parcial, no validada):**
- **Semántica de cota**: confirmada para los DOS edificios en el sentido de "nivel superior de
  losa/cara superior" por vías distintas (EII textual "N.S. losa"; EI por convención "N.S." +
  lamina 102 "PLANTA CIELO PISO 2, Nivel +3.91, LOSA e=15"). El modelo analítico (cota como Z
  nodal) es coherente con esto; **no se requiere cambio de cota**.
- **Viga 60/80 canto vs. descuelgue**: **NO resuelto**. Láminas de detalle 400/500/800 existen
  pero su texto no es extraíble con las herramientas disponibles (requiere revisión visual o
  lectura del DXF/DWG vectorial).
- **Encuentro losa–viga–columna / muro**: **NO resuelto**; no hay corte con dimensiones legible.

**Detalles a solicitar (elemento + pregunta exacta), Edificio I y II:**
1. **Viga `V. 60/80` — (viga, CP1S/P1/…):** en el corte/sección transversal de la viga,
   ¿el "60/80" es el **canto total** de la viga (viga apoya su cara superior a nivel de la losa,
   fondo a cota−0.80) o el **descuelgue** bajo la losa (fondo a cota−0.80)? Adjuntar el corte
   (archivo, lámina, escala, coordenadas).
2. **Losa — (losa, todos los niveles):** confirmar espesores reales por nivel (`e=15/20/30`) y si
   la cota del nivel corresponde a la **cara superior** de la losa en ambos edificios (en I solo
   está el rótulo "Nivel +3.91, LOSA e=15", no un `N.S. losa` explícito).
3. **Columna — (pilar, nudos 200–211/300–309):** el tramo que "llega a la cota", ¿debe terminar en
   la cara superior de la losa (contacto real, sin hueco) o existe un canto que la haga interrumpir
   por debajo? Aportar el corte que muestre el encuentro pilar-losa.
4. **Muro `N.S.M. +0.95` — (muro `M.H.A. e=30`, lamina 101):** confirmar qué elemento es y si su
   cara superior +0.95 (¿respecto a CP1S?) es representativo de los muros portantes del resto de
   niveles (los extremos documentados de los muros no fueron verificados).
5. **Niveles/cuadro de niveles — (ambos edificios):** enviar el CUADRO DE NIVELES legible del
   Edificio I (láminas 000–002 son solo raster; el valor `-5.21` de la lamina 309 no está en el
   cuadro extraíble) con la cota por nivel y su columna "N.S. losa"/"N.S.".

### 9.6 Investigación física en láminas originales — recortes y correspondencias (pendiente de revisión visual)

Investigación **independiente del error de coordenadas de los contornos de diafragma** (bug del
visor, corrección aparte en este mismo reporte). Esta sección **no modifica geometría**; entrega rutas de recortes y una
tabla de correspondencia **provisional** para revisión visual antes de tocar el modelo. Las láminas
400/800 NO se clasifican como "sin información": contenían dibujo vectorial sin capa de texto
extraíble, por lo que se extrajeron como **composiciones ampliadas (5×)** para inspección visual.

**Rutas de recortes (composición 5× de cada A0 → mosaico 2 filas × 3 columnas con solape):**

| Lámina | Mosaicos (cada uno ~6964×6675 px) | Composición completa |
|---|---|---|
| 400 (detalles/elevaciones de vigas) | `%TEMP%\opencode\EI_LAM400_tile_r{1,2}c{1,2,3}.png` | `EI_LAM400_full.png` (16850×11920) |
| 800 (conexiones metálicas + elevación +7.87→+11.83) | `%TEMP%\opencode\EI_LAM800_tile_r{1,2}c{1,2,3}.png` | `EI_LAM800_full.png` |
| 301 (elevaciones EJE 1A / 1b / 1C) | `%TEMP%\opencode\EI_LAM301_tile_r{1,2}c{1,2,3}.png` | `EI_LAM301_full.png` |

Recortes específicos de esta revisión:
- `%TEMP%\opencode\CROP_EI800_EL_superior_izquierda.png` — elevación superior izquierda de lamina 800 y sus llamadas.
- `%TEMP%\opencode\CROP_EI301_EL_muros_columnas.png` — elevaciones (EJE 1A/1b) de muros/columnas de lamina 301.

**Contenido localizado por coordenadas de página (axes/pdf, no rotados):**

- **Lamina 400** = cuadro de **detalles/elevaciones de vigas** rotulados `100–114` (con niveles
  `1/2/3` y referencias de ejes `F/G/Ga/E'`, `I/I'/IB/IA/H1/H2`, `1b`):
  - tile r1c1: detalles `0101`/`100` — vigas de ejes F–Ga, referencias `1b`, `0102`.
  - tile r1c2: `101`, `104`, `105` — ejes F/G/Ga/E', niveles 1–3.
  - tile r1c3: `102`, `103`, `106`, `107` — ejes F, `1AA`.
  - tile r2c1: `108`, `109` — ejes H'/I.
  - tile r2c2: `111`, `112`, `113` — ejes `1A`/`1AA`.
  - tile r2c3: `114` + eje `I`.
- **Lamina 301** = ELEVACIONES por eje (1:50). **Corrección por inspección visual (usuario):** el
  recorte `CROP_EI301_EL_muros_columnas.png` contiene **ELEVACIÓN EJE 1b** y **ELEVACIÓN EJE 1BB**,
  no "1A" (mi identificación inicial "1A/1b/1C" salió de la capa de texto; el texto dibujado es
  `1b`/`1BB`). Se adopta la lectura visual como autoritativa. Muros con coronación inclinada y
  elementos bajo −4.01: **no** se generalizan como paneles rectangulares ni se limita su altura
  a esa cota (pendiente de cruzar cada muro con su ID, solo en su eje).
- **Lamina 800** = solo anclaje de texto (`ESCALA 1:50`); resto dibujo vectorial (conexiones metálicas y elevación entre +7.87 y +11.83 identificadas visualmente por el usuario).

**Tabla de correspondencia provisional (etiqueta/eje ↔ ID fuente ↔ ID visor) — PENDIENTE.**
El esquema real de IDs del visor (de `lab_data/edificios/I/geometry/*.json`) usa los **ejes de
columna `E/F/G/H`** y vigas `GV_CP1_*`/`V_COL_CP1_*`/`COL_EI_CP1_{E,F,G,H}_{1,2,3}`, mientras que
las láminas rotulan la retícula como `1A/1AA/1b/E'/F/G/Ga/H'/I/I'/IA/IB`. Ese puente
retícula-de-dibujo ↔ ejes-del-visor **no está demostrado** y queda **pendiente** de cruzar
visualmente (las filas marcadas así NO se toman como correspondencia válida).

| Lámina / elemento | Etiqueta/eje (lámina) | Posición (pdf) | ID fuente / visor | Estado |
|---|---|---|---|---|
| 400 detalle `100`/`0101` | ejes F–Ga, ref `1b`, niveles 1–3 | tile r1c1 | vigas `V_COL_CP*_F/G/H` o `GV_CP*_*` (a confirmar) | **pendiente** (requiere leer el detalle) |
| 400 detalles `101`–`107` | ejes F/G/Ga/E', `1AA` | tiles r1c2/r1c3 | `V_COL_CP*_{E,F,G,H}`, `GV_CP*_*` P1..P4 | **pendiente** |
| 400 detalles `108`–`114` | ejes H'/I, `1A`/`1AA` | tiles r2c1/r2c2/r2c3 | columnas `COL_EI_CP1_{E,F,G,H}_{1,2,3}` y vigas asociadas | **pendiente** |
| 301 ELEVACION EJE 1b | `V. 20/80`; `IB/IA/H1` (recorte 1) | tile r2c2 / `CROP_EI301_EL_muros_columnas.png` | vigas perimetrales `V_COL_CP*_*`; columnas/muros del eje correspondiente | **pendiente** de cruzar ejes |
| 301 ELEVACION EJE **1BB** | muros coronación inclinada + bajo −4.01 (recorte 2) | `CROP_EI301_EL_muros_columnas.png` | muros por eje (`M_EI_CP1S_*`/`M_EI_CP1_*`/`M_EI_CP3_*`, a confirmar cuál) | **pendiente** (no por semejanza) |
| 301 ELEVACION EJE 1C | `V.F. 15/225`; `IB/IA` | tile r1c3 | vigas de fachada / arriostramiento | **pendiente** |
| 800 ELEVACIÓN **EJE 1–2–3** (extremes I′ y J; 5.00 m = 2.55+2.45; +7.87→+11.83) | conexiones metálicas, 2 diagonales convergentes + verticales | `CROP_EI800_EL_superior_izquierda.png` (tile r1) | ver **tabla por miembro** abajo | **ver tabla por miembro** |

**Tabla por miembro — lámina 800, ELEVACIÓN EJE 1–2–3 (verificación visual, PENDIENTE).**
Las plantas P3/P4 (cota +7.87/+11.83) y los registros fuente confirman que la zona metálica
I′–J **sector J** contiene verticales (V.M./P.M. 300x300) y **candidatos P.M.I. `por_resolver`**
(extraídos de `RLE-TEXTO-1`, no de geometría de pilares; el DXF P3/P4 no expone diagonales
dibujadas). La distancia nominal 5.00 m = 2.55+2.45 y los niveles **no** se confunden con las
coordenadas exactas de conexión (los detalles de unión introducen offsets). Por eso la única
paridad demostrable hoy es **ubicación (sector J, x≈47.8 y x≈50.7) + niveles (+7.87→+11.83)**;
la topología exacta de las 2 diagonales (cuáles convergen y en qué nudo superior) queda
**pendiente de la lectura del detalle de conexión**.

| Miembro dibujado | Etiqueta de plano | ID candidato | Extremos propuestos | Evidencia de correspondencia | Estado |
|---|---|---|---|---|---|
| Vertical extremo izq. (I′) | eje I′ (`Ip`) | `COL_EI_CP3_S_IpJ1/2/3` (x≈46.35, P3, `V.M.300x300x5`) + `COL_EI_CP4_S_IpS1` (x=45.97, P4, `P.M.300x300x20`) | cota +7.87 → +11.83 en x≈46 | misma zona I′–J, niveles P3/P4 | **pendiente** (confirmar alineación vertical) |
| Vertical extremo der. (J) | eje J | `COL_EI_CP3_S_J1/2/3` (x≈48.7, P3, `V.M.300x300x5`) + `COL_EI_CP4_S_JS2..JS8` (P4, `P.M.300x300x20`) | cota +7.87 → +11.83 en x≈48.7 | misma zona/sector, niveles P3/P4 | **pendiente** |
| Diagonal candidata 1 | `J-P1/2/3` (etiqueta de texto) | `COL_EI_CP3_S_JP1(47.78)`, `_JP2(47.89)`, `_JP3(47.82)` — columna x≈47.8 | columna vertical de P.M.I. a +7.87 (¿diagonal real?) | `RLE-TEXTO-1`, cota +7.87, sector J | **pendiente** (¿diagonal vs vertical?) |
| Diagonal candidata 2 | `J-P4/5/6` (etiqueta de texto) | `COL_EI_CP3_S_JP4(50.58)`, `_JP5(50.82)`, `_JP6(50.71)` — columna x≈50.7 | columna vertical de P.M.I. a +7.87 (¿diagonal real?) | `RLE-TEXTO-1`, cota +7.87, sector J | **pendiente** (¿diagonal vs vertical?) |
| Conexión superior (nudo de diagonal convergente) | P4 / `P.M. 300x300x20` | `COL_EI_CP4_S_JS2/JS3/JS8` (x≈48.8/52.0/52.1, P4) | +11.83 | nivel +11.83, sector J, fase metálica | **pendiente** (confirmar el nudo exacto) |

**Muros — lámina 301 (ELEVACIÓN EJE 1b / EJE 1BB), por cruzar en el eje correcto (PENDIENTE).**
Muros con coronación inclinada y elementos bajo −4.01 observados: **no** se generalizan como
paneles rectangulares ni se limita toda su altura a −4.01. Candidatos (solo del eje indicado, no
por semejanza): `M_EI_CP1S_*`/`M_EI_CP1_*` del sótano (bajo −4.01) y `M_EI_CP3_*` del núcleo
(ascensor), ubicados en x≈0/9.65/21.25 (CP1S) y núcleo x≈3.3–6.7. No se confirma cuál corresponde
al marco del recorte 2 de EJE 1BB sin leer el eje exacto en la elevación.

**Nota sobre registros metálicos e inclinados (no sustituir).** Los registros metálicos viven en
`columnas` del visor y se concentran en la fase metálica (P.M./`+V.I.`, 2ª etapa) a **+7.87 (P3) y
+11.83 (P4)** — lo que coincide con la elevación "+7.87→+11.83" de lamina 800. Ejemplos reales:
- Confirmadas (cuadradas): `COL_EI_CP2_S_G3S1_18.96` `P.M. 300x300x20`; `COL_EI_CP3_S_IpJ1_46.35`
  `V.M. 300x300x5`; `COL_EI_CP4_S_JS2_48.77` `P.M. 300x300x20`.
- **`por_resolver`** (`ancho=0.0, peralte=0.0`, `P.M.I.`): `COL_EI_CP3_S_JP1_47.78`, `_JP2..JP6`,
  `_FS3`, `_GS4` etc. — **estos son los candidatos a diagonales/inclinados** (arriostramientos).

**No se sustituye** la totalidad de estos registros por diagonales ni se generalizan alturas: cada
caso se resuelve solo con el detalle que lo respalde (de los recortes de lamina 800, P3/P4); lo no
demostrable queda `por_resolver`/`pendiente`. La tabla **no valida** estos casos.

**Separación explícita:** esta investigación (lamina 400/800/301, semántica de cota y geometría
física) es independiente del **error de coordenadas de los contornos de diafragma**, que es un bug
propio del visor (a corregir en él, de forma aparte) y no se relaciona con estas láminas.

## 10. Correcciones prioritarias del visor (dos bugs cerrados)

En esta iteración se cierran **dos** correcciones del visor, sin tocar la geometría fuente, las
coordenadas ni el modelo FE: (1) reclasificación de los registros `RLE-TEXTO-1`/`P.M.I.` como
"Referencias pendientes" (no se dibujan como columnas completas); (2) error de coordenadas
mundiales del contorno de diafragma. Ambas quedan documentadas aquí con la lista exacta y el
residuo antes/después.

### 10.1 Reclasificación: `RLE-TEXTO-1`/`P.M.I.` → "Referencias pendientes"

**Criterio (cerrado y verificable).** Son registros que tienen **solo posición/rotulo de texto**, sin
geometría física respaldada. El propio exportador lo documenta (`tools/export_lab_data.py`): el
perfil `P.M.I.` "sin dimensiones simples se marca pendiente (`estado_seccion="por_resolver"`) y no
se inventa dimensión", devolviéndose `(0,0)`. En el visor esto se detecta en
`BuildColumns` (`LabLoader.cs`) con la condición **`estado_seccion == "por_resolver"` Y
`ancho<=0 && peralte<=0`**. Esa condición aísla **exactamente los 8 registros P.M.I. de P3** (son
los únicos `columnas por_resolver` de todo el paquete; las columnas de CP1S/P1/P2/P4 y las de
Edificio II son `confirmado`, y los `por_resolver` de EII son de **vigas** con geometría confirmada
por caras, que NO se tocan).

**Comportamiento aplicado.**
- No se dibujan como columna completa entre forjados.
- Se conservan como **marcador compacto de referencia** (cubo pequeño semitransparente lila en la
  posición documentada) con su ID y procedencia (`RLE-TEXTO-1`).
- Se mueven del grupo `Columnas` al **nuevo grupo/filtro independiente `Referencias pendientes`**
  (nuevo `ElemType.RefPendientes`), diferenciado de "Columnas".
- **No** se alteran sus coordenadas (`u=47.78/47.89/47.82/50.58/50.82/50.71/20.5/30.51`, cota
  +7.87) ni el modelo FE; **no** se eliminan columnas verificadas y **no** se clasifican todos los
  metálicos igual (los `V.M./P.M. 300x300` `confirmado` siguen siendo columnas dibujadas).

**Lista exacta de registros reclasificados (8).** `estado_seccion=por_resolver`, `seccion=P.M.I.`,
`ancho=peralte=0.0`, `nota` = "Columna acero; RLE-TEXTO-1." (nivel P3, edificio I):

| ID | x (u) | v | Eje |
|---|---|---|---|
| `COL_EI_CP3_S_JP1_47.78` | 47.78 | −0.60 | J-P1 |
| `COL_EI_CP3_S_JP2_47.89` | 47.89 | 8.30 | J-P2 |
| `COL_EI_CP3_S_JP3_47.82` | 47.82 | 15.51 | J-P3 |
| `COL_EI_CP3_S_JP4_50.58` | 50.58 | −0.60 | J-P4 |
| `COL_EI_CP3_S_JP5_50.82` | 50.82 | 8.61 | J-P5 |
| `COL_EI_CP3_S_JP6_50.71` | 50.71 | 15.85 | J-P6 |
| `COL_EI_CP3_S_FS3_20.5` | 20.50 | 20.72 | F-S3 |
| `COL_EI_CP3_S_GS4_30.51` | 30.51 | 20.66 | G-S4 |

Estos coinciden con los "candidatos a diagonales/inclinados" de la §9.6 (zona metálica I′–J segmento
J, `x≈47.8` y `x≈50.7`). La topología de las 2 diagonales de la lámina 800 queda **pendiente de la
lectura del detalle de conexión** (no se usan las coordenadas de inserción de rótulos como extremos
estructurales; el marcador de referencia preserva la paridad de ubicación/niveles sin afirmar
geometría).

**Recuento antes/después (número de columnas dibujadas en el filtro `Columnas`).**

| Métrica | Antes | Después |
|---|---|---|
| `columnas` en `Model.Elements` | 145 | 137 |
| `referencias pendientes` (`RefPendientes`) | 0 | **8** |
| columnas verificadas dibujadas (no se tocan) | 137 | 137 |

El umbral de aceptación de columnas (`cols >= 59`, `LabViewerEditor`) sigue cumpliéndose (137).

**Captura antes/después de la zona I′–J.** (Aquí se inserta la captura de la zona I′–J antes y
después de la reclasificación; el visor reserva el recorte de la zona metálica del segmento J.)
- Antes: se dibujan 8 prismas naranjas "pendiente" de altura completa entre +3.91 y +7.87 en las
  posiciones de `JP1..JP6`, `FS3`, `GS4`.
- Después: esos 8 ya no son columnas; aparecen como marcadores compactos lilas (grupo
  "Referencias pendientes") en su posición documentada, seleccionables, con ID y procedencia; las
  columnas metálicas confirmadas de la vecindad (p. ej. `COL_EI_CP3_S_J1/2/3`, `_IpJ1/2/3`) quedan
  intactas.

### 10.2 Error de coordenadas mundiales del contorno de diafragma (cerrado)

**Causa raíz.** En `BuildSlabs` (`LabLoader.cs`) el contorno de diafragma se dibuja con un
`LineRenderer` cuyos puntos están en **coordenadas locales** `(u, cota, v)` y cuelga de la
jerarquía `Lab → Edificio → Nivel → Diafragma`. Pero `LineRenderer.useWorldSpace` es **`true` por
defecto** en Unity, por lo que esos puntos se interpretaban como **espacio mundial** sin aplicar el
offset de colocación del edificio. El `MeshCollider` invisible del mismo diafragma usa una malla
**local** bajo la misma jerarquía, así que **sí** heredaba el offset. Resultado: el contorno cian
visible quedaba descolocado respecto a su losa (p. ej. Edificio I, cuyo `placement` es `x=60`, el
contorno quedaba ~60 m en X del borde real de la losa), mientras la selección por clic (collider)
era correcta.

**Corrección aplicada.** Se fija `lr.useWorldSpace = false` (y lo mismo en los `LineRenderer` de
los huecos), de modo que el contorno se interpreta en el frame local y hereda exactamente el
mismo `placement` que la losa vía jerarquía (una sola aplicación de la fuente común
`CommonTransform` + placement del edificio).

**Residuo antes/después del contorno vs. la losa asociada.**

| Punto de control | Antes | Después |
|---|---|---|
| Contorno cian vs. borde de losa (Edificio I, placement `x=60`) | descolocado **~60 m en X** | alineado (residuo ≈ 0) |
| Contorno vs. MeshCollider del propio diafragma | descolocado **~60 m en X** | alineado (residuo ≈ 0) |
| Elevación del contorno | `poly.y + 0.05` (escalón por z-fighting) | sin cambio (intencional) |
| Selección por clic (collider) | correcto | correcto (sin cambio) |

**Verificación.** Tras la corrección, el contorno de cada diafragma coincide en planta con su losa
y con su collider (misma fuente `CommonTransform` + placement, aplicada una sola vez); en elevación
conserva el pequeño escalón de +0.05 m sobre la cara superior de la losa para evitar z-fighting
(comportamiento previsto, no un residuo).

## 11. Marco de acero I′–J (P3/P4) — corrección candida del paquete visual

La causa raíz del voladizo del apartado 3 se afina con la lectura **autoritativa de los DXF de
planta**. La discrepancia visible (barras metálicas verticales dibujadas lateralmente descolgadas,
sin conexión, fuera del borde de losas/vigas) no es un bug de transformación (aspecto ya descartado:
fuente→exportado→Unity son internamente consistentes) sino de **compleción de geometría modelada y
de procedencia de coordenadas**: las "columnas metálicas" del paquete proceden de **inserciones de
texto** (`RLE-TEXTO-1`) y varias no caen sobre ninguna huella física de pilar del plano.

> **Verificación previa a declarar completa.** Una revisión rigurosa de los DXF obligó a **descartar**
> un primer enfoque que añadía "vigas de acero" marcadas `S_EI800_*`: esas líneas paralelas de
> `RLE-VIGA` eran en realidad **caras opuestas de la misma viga de hormigón** (`V. 60/80`/`V. 40/60`,
> ya modeladas), de modo que generar un miembro por cara duplicaba miembros existentes y no estaba
> justificado por etiqueta. Esa adición se **retiró** (0 miembros fabricados en el estado final) y se
> sustituyó por la corrección mínima y bien respaldada de esta sección.

### 11.1 Evidencia del plano (DXF)

| Planta | DXF | Transformación (frame común = paquete) |
|---|---|---|
| P3 | `Datos Estructurales\2017_67-102.dxf` | `u=(x−535.00)/100`, `v=(4260.35−y)/100` |
| P4 | `%TEMP%\opencode\piso4_103.dxf` | `u=(x−490.30)/100`, `v=(6297.30−y)/100` |

**Qué dibuja el plano en el sector I′–J (planta):**
- Líneas paralelas de `RLE-VIGA` separadas 0.60 m = **caras de vigas de hormigón** `V. 60/80` y
  `V. 40/60` (etiquetas `RLE-TEXTO-1` en u≈44.4, 46.2, 47.0, 49.3 y 48.8), **ya modeladas** en el
  paquete como vigas de hormigón. No generan un miembro de acero nuevo y no se duplican.
- Columnas de acero **validadas por etiqueta**: `V.M. 300x300x5` en u≈46.35 (IpJ) y u≈48.7 (J),
  cada una a 3 niveles (v≈0.55 / 9.32 / 16.61 en P3). Coinciden con las columnas `COL_EI_CP3_S_IpJ*`
  y `COL_EI_CP3_S_J*` del paquete, que quedan `confirmado` por etiqueta.
- Candidatos `P.M.I.` (sin dimensiones): u≈47.8 (`JP1/2/3`) y u≈50.6–50.8 (`JP4/5/6`) → ya
  `RefPendientes` (sección `por_resolver`). Correctos tal cual.
- **No hay diagonales en planta** (las líneas de `RLE-VIGA` del sector son todas axiales). Las
  **diagonales del arriostramiento solo existen en la elevación de la lámina 800** (etiquetas
  indicativas `PASADA 45/30`, `306`, `307` no se materializan como segmentos en planta), ilegible
  para el modelo → **pendiente**. El plano de planta no permite cerrar la topología entre forjados.

**Huella física de las columnas de acero en P4** (`RLE-PILAR`, octágonos a 3 niveles v≈0.28/9.13/16.35):

| Huella física del plano (u) | Columna del paquete (u) | Coincide |
|---|---|---|
| 44.92 (Ip compuesta) | `IpS1` = 45.97 | ❌ |
| **47.46** (montante) | `JS2`/`JS5` = 48.77/48.73 | ❌ |
| **49.79** (J) | `JS3`/`JS4`/`JS8` = 51.97/52.11/52.08 | ❌ |

Ninguna columna de acero de P4 cae sobre la huella física del plano (además, `piso4_103.dxf` no
contiene entidades de texto, por lo que **no hay etiqueta P4 legible** que respalde esas posiciones).

### 11.2 Corrección aplicada (candidata, paquete visual únicamente)

`tools/apply_plan_frames.py` (integrado al final de `export_lab_data.py`):

1. **Reclasifica como "Referencia pendiente" las 6 columnas de acero de P4** (`IpS1`, `JS2`, `JS3`,
   `JS4`, `JS5`, `JS8`) cuyas coordenadas **no coinciden con la huella física** del plano (u=44.92 /
   47.46 / 49.79) ni tienen etiqueta legible en `piso4_103.dxf`. Se les conserva la posición, se les
   marca `estado_seccion="por_resolver"` (ancho/peralte = 0) → dibujan como **marcador `RefPendientes`**
   (`nota` documenta la causa y el rango de huellas). Consistente con el criterio "solo respaldado si
   cae en geometría física o está etiquetado".
2. **P3 se conserva intacto**: `IpJ`/`J` quedan `confirmado` (etiqueta `V.M.300x300x5` presente) y
   los `P.M.I.` (`JP*`) ya eran `RefPendientes`. No se añade ni se elimina ninguna columna.

**No se fabrican extremos de miembros nuevos**: la única combinación defensible habría sido la de
los montantes del marco/arriostramiento, pero (a) las vigas horizontales del sector ya son de
hormigón y están modeladas, y (b) las diagonales solo constan en la elevación ilegible. Consecuencia
honesta: **el marco completo entre forjados no puede reconstruirse con los datos legibles**, de modo
que NO se añade geometría inventada.

### 11.3 Estado

| Item | Estado |
|---|---|
| Vigas de hormigón I′–J (`V. 60/80`/`V. 40/60`) | **ya modeladas**, sin duplicar |
| P3 `IpJ`/`J` (etiqueta `V.M.300x300x5`) | **confirmado** (etiqueta) |
| P3 `JP*` (`P.M.I.`) | `RefPendientes` (sin cambio) |
| P4 `IpS1`/`JS2`/`JS3`/`JS4`/`JS5`/`JS8` (sin huella física) | **reclasificadas a `RefPendientes`** |
| Diagonales + topología entre forjados (lámina 800, elevación) | **pendiente** (elevación ilegible para el modelo) |
| Miembros fabricados / conexiones para cerrar huecos | **0** |
| Originales fuente + análisis FE | **sin tocar** |
| Verificación visual en Unity (Play + capturas antes/después) | **pendiente de ejecutar en el Editor** |

**Integración y flujo de regeneración.** `apply_plan_frames.py` se invoca **automáticamente al final
de `export_lab_data.py`**, de modo que regenerar `lab_data` reconstituye el mismo estado final. La
corrección es determinista e idempotente: no añade elementos (reclasificación únicamente), por lo
que re-ejecutar NO duplica miembros (verificado: 0 vigas fabricadas, 0 IDs duplicados en P3/P4;
P4 mantiene 6 reclasificadas en cada ejecución).

```
python tools/export_lab_data.py     # incluye apply_plan_frames internamente
```

Queda **pendiente** únicamente la verificación visual en el Editor (capturas antes/después) y el
cruce fino de las diagonales de la lámina 800, que requiere leer el detalle de conexión (el modelo
no puede inspeccionar imágenes).

