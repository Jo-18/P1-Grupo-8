# CORRECCIONES POST-EVALUACION -- Semana 05 (entregable P1-Grupo-8)

> Fecha: 2026-09-24. Alcance: las 4 correcciones solicitadas sobre el viewer
> Unity + el flujo FE (OpenSeesPy -> exportadores -> JSON -> Unity). Sin arreglos
> solo visuales: cada correccion modifica el flujo de datos o de interaccion y
> se verifica de extremo a extremo (evidencias numericas abajo). Sin commit:
> el estado final de git queda documentado en `git status` de la entrega.

## Indice de correcciones

| Corr. | Tema | Archivos principales |
|---|---|---|
| Corr.1 | Camara (pan/orbit/zoom, punto pivote, home/encuadre, click con umbral) | `CameraController.cs`, `InteraccionUI.cs`, `EsfuerzosController.cs`, `ViewerController.cs` |
| Corr.2 | Carga puntual seleccionable que llega a OpenSeesPy (`eleLoad beamPoint`, caso `PL1`) | `carga_puntual.py` (nuevo), `exportar_esfuerzos_funcional_para_viewer.py`, `CargaPuntualController.cs` (nuevo), `EsfuerzosController.cs` |
| Corr.3 | Diagramas N/V/M con valores i/j y maximo (rotulados con unidad) | `EsfuerzosController.cs` (`DrawDiagrams`) |
| Corr.4 | Deformada global REAL por caso (Hermite 6DOF, mapeo 6DOF de OpenSeesPy) | `EsfuerzosController.cs`, `LabLoader.cs`, `SolverDespAUnity` |

---

## Corr.1 -- Camara del viewer

- Antes: la camara orbitaba alrededor de un punto fijo/deria del pivot con pestokey, sin encuadre, y el click de seleccion se disparaba incluso al orbitar.
- Ahora:
  - `CameraController.cs`: pivote explicito (el punto que se encuadra), zoom
    exponencial sobre el pivote, pan proporcional a la distancia, teclas
    Home/F para `Home()`/`FrameAll()`.
  - `InteraccionUI.cs`: `TrackClic` + `ClicLiberadoDisponible` (clic sincronizado
    en release), guard Shift para pan.
  - `EsfuerzosController.Update` + `ViewerController.Update`: orbitar/pan no
    seleccionan (umbral de desplazamiento de 6 px); la seleccion FE se hace solo
    en el release del clic.

## Corr.2 -- Carga puntual seleccionable que llega a OpenSeesPy (caso `PL1`)

Cadena completa implementada y verificada:

1. **Estado de la UI**: `viewer_unity/Assets/StreamingAssets/lab_data/cargas_puntuales.json`
   (formato `cargas_puntuales_v1`), un config por edificio:
   `{edificio, elemento_tag, elemento_viewer_id, nivel, activa, magnitud_kN,
   direccion_unity_unidad:[u,cota,v], xi}`.
2. **`carga_puntual.py`** (nuevo, `src/unity_esfuerzos/`): construye el modelo del
   perfil, proyecta la direccion a ejes locales (convencion OpenSees `Linear`
   verificada: `x'=unit(pj-pi); z'=proy(vecxz) sobre x'; y'=z' x x'`), aplica
   `ops.eleLoad('-ele', tag, '-type', '-beamPoint', Py, Pz, xi)` y resuelve con
   OpenSeesPy (`analyze()==0`). Escribe el payload
   `PL1_{EI|EII}_MODELO_FE_COMPLETO_FUNCIONAL.json` con layout identico a los
   casos base (fuerzas local/global por elemento, desplazamientos, reacciones,
   `carga_puntual`, `equilibrio_ok`, `solucion_ok`).
3. **Exportador** `exportar_esfuerzos_funcional_para_viewer.py`:
   - Constante `PL_CASO = "PL1"`.
   - `casos_vigentes()` agrega `PL1` SOLO si el payload del perfil existe
     (no rompe los checks `sets_casos` de la auditoria).
   - `_leer_fuerzas` / `_leer_desplazamientos` tratan `PL1` como caso base.
   - `generar()` excluye `PL1` de `combos_vigentes` e incluye
     `PL1_*_MODELO_FE_COMPLETO_FUNCIONAL.json` en `fuente.archivos`.
   - Nuevo bloque `carga_puntual` en el paquete del viewer (configuracion
     resuelta) + check `equilibrio_carga_puntual_PL1` en la auditoria (23 checks
     con PL1 presente, 22 sin el).
4. **Unity**:
   - `EsfuerzosController.cs`: `FuerzasVista`/`DespActivo`/`DespActivoRaw`
     escalan `PL1` por `EFElemento.FactorPL`; helper `Vec6Escalar`;
     `CasosSelectables()` (base + `PL1` si existe en el paquete);
     `SetFactorPL(float)`; al elegir `PL1` se apaga la superposicion libre y se
     reconstruye la deformada; `CargarEdificio` lee las CLAVES presentes de
     `fuerzas` (no la lista fija de casos); `RecargarPaquetes()`.
   - `CargaPuntualController.cs` (nuevo): panel PL1 (elemento seleccionado,
     magnitud, direccion +/-U/V/COTA, xi, activa), lectura/escritura del estado,
     flecha 3D (LineRenderer + cono + etiqueta kN) en el punto de aplicacion,
     banner rojo "RESULTADOS DESACTUALIZADOS", y boton
     "Reanalizar (solver)" que lanza `carga_puntual.py` y re-carga los paquetes.

### Semantica Caso A / Caso B (regla documentada)

- **Caso A** (cambio SOLO de magnitud, mismo edificio+elemento+direccion+xi):
  el viewer escala la solucion PL1 resuelta linealmente:
  `FactorPL = P / P_resuelta` (sin reanalisis, exacto por linealidad).
- **Caso B** (elemento/direccion/xi cambiados): banner rojo y reanalisis
  via OpenSeesPy (boton) -> re-export -> `RecargarPaquetes`.

### Evidencia numerica PL1 (paquete oficial del viewer, redondeo 6)

| Metrica | Edificio I (tag 8, P=50 kN, +U, xi=0.5) | Edificio II (tag 3, P=40 kN, -V, xi=0.3) |
|---|---|---|
| N_i (kN) | 0.8017 | -0.2289 |
| Vy_i (kN) | -25.8931 | -0.0374 |
| Mz_i (kN-m) | -18.5838 | -0.0962 |
| max\|desplazamiento\| (m) | 0.00022523 (nodo 630) | 0.00000665 (nodo 164) |
| P_global / R_global (kN) | [50,0,0] / [-50,0,0] | [0,-40,0] / [0,40,0] |
| residuo de equilibrio | 3e-09 | 0.0 |
| solucion_ok / equilibrio_ok | true / true | true / true |
| auditoria del paquete | 23/23 | 23/23 |

Ambos paquetes (`esfuerzos_FE_EDIFICIO_{I,II}.json`) incluyen PL1 en `casos`,
`fuerzas` por elemento y `deformada.desplazamientos_por_caso`.

## Corr.3 -- Diagramas con valores i/j y maximo

- `DrawDiagrams` ahora rotula en cada extremo el valor del diagrama activo
  (`i ...` / `j ...` con unidad) y en el maximo el texto `max|<magnitud>|` con su
  unidad, usando las etiquetas 3D (`TextMesh`) ya registradas en los diagramas.
- Los valores mostrados son los del paquete FE (redondeo 6 del exportador), sin
  recalculo.

## Corr.4 -- Deformada global real (Hermite 6DOF)

- Antes: la deformada por caso interpolaba/extrapolaba desplazamientos nodales
  sin conservar la giros 6DOF del FE (se perdia el mapeo de rotaciones).
- Ahora:
  - Mapeo 6DOF verificado de OpenSeesPy a Unity: el despacho
    `desplazamientos_por_caso[caso][tag]` es `[u, v, cota, Ru, Rv, Rcota]`
    (indice 2 = vertical cota); `disp=(v0, v2, v1)`, `rot=(v3, v5, v4)`.
  - `SolverDespAUnity` + `DespActivoRaw` / `DespLibreRaw`: vector de estado 6DOF
    por nodo por caso.
  - `RebuildDeformada`: interpolacion **Hermite 6DOF** con las funciones de
    forma del elemento viga (`ELEMENTO NORMALIZADO`), rotaciones conservadas en
    cada extremo; re-rotulada como deformada del modelo FE completo.
  - `MaxDespActivoInM` -> etiquetas `Máx |δ| real`.

---

## Regresion de la suite Python (tests)

- Total recogido: **88 passed, 20 failed** (antes 86 passed / 22 failed).
  - **2 tests adaptados al contrato PL1** (fueron actualizados y ahora pasan):
    `TestFidelidadFuente::test_valores_iguales_a_payload` (PL1 se lee del
    payload `PL1_*` y no de `COMB_PL1_*`) y
    `TestBloqueoCombinacionesObsoletas::test_generar_memoria_ofrece_combos_y_escribir_no_bloquea`
    (los `casos` ahora incluyen `PL1` solo si el payload existe, igual que
    `casos_vigentes()`).
  - **20 failed = preexistentes y regenerables, FUERA de alcance**: todos fallan
    en `FileNotFoundError` de `results/superposicion/verificacion_superposicion_completa_{I,II}.json`,
    artefacto regenerable (paso E3.4 de `ejecutar_entrega_03.py`) que no forma
    parte del flujo S05 (documentado en semana05 seccion 8.2). No estan
    relacionados con las correcciones.
- Comando (desde `entrega_03_cargas_sismo_capacidad/`, venv aislado):
  `python -m pytest tests -q` con `PYTHONPATH=src;<raiz>/analisis_estructural/edificio_I`.

## Compilacion Unity

- `Unity.exe 6000.5.10f1 -batchmode -quit -projectPath viewer_unity`:
  **rc=0, sin `error CS`** (log `unity_compile.log`).

## Artefactos modificados / creados (resumen)

- Creados: `CargaPuntualController.cs`, `carga_puntual.py`,
  `lab_data/cargas_puntuales.json`,
  `PL1_{EI|EII}_MODELO_FE_COMPLETO_FUNCIONAL.json`.
- Modificados: `EsfuerzosController.cs`, `CameraController.cs`,
  `InteraccionUI.cs`, `ViewerController.cs`, `LabLoader.cs`,
  `exportar_esfuerzos_funcional_para_viewer.py`,
  `esfuerzos_FE_EDIFICIO_{I,II}.json` (caso PL1 inyectado),
  `tests/.../test_exportar_esfuerzos_funcional_viewer.py`.

## Pendientes (expl\u00edcitos)

- Los 20 tests regenerables de `verificacion_superposicion_completa_*` requieren
  el paso E3.4 del pipeline de Entrega 3 (fuera del alcance de S05).
- Prueba del APK movil en telefono fisico (heredado, no bloqueo).

---

# Segunda tanda — 4 frentes de interaccion (2026-09-25)

Mejoras de uso del viewer sobre las correcciones anteriores. No cambian el flujo
de datos: OpenSeesPy -> exportador -> JSON -> Unity se mantiene intacto y cada
edificio sigue usando **sus propios** resultados (no se conectan nodos ni se
promedian esfuerzos entre el edificio I y el II).

| Frente | Tema | Veredicto |
|---|---|---|
| F1 | Paneles arrastrables + "Restablecer paneles" | **LISTO** |
| F2 | Alcance de deformada y diagramas (Elem / Edif I / Edif II / Ambos) | **LISTO** |
| F3 | Camara dual: conjunto I+II y encuadre por edificio | **LISTO** |
| F4 | Flecha PL1 adaptativa, fucsia, con estado y desplazamiento | **LISTO** |

## F1 — Paneles arrastrables — LISTO

Los 4 paneles principales (Esfuerzos, Carga Puntual PL1, Carga Movil SQ4 y
Laboratorio de Modificaciones S5) se mueven arrastrando su barra de titulo.

- `Paneles.cs`: `Rect(id, porDefecto)` cachea la posicion por id, la **recorta a
  la pantalla** (con margen y reservando la barra superior) y registra el rect en
  `InteraccionUI` internamente, de modo que el arrastre **no mueve la camara** ni
  **selecciona elementos** que queden detras, y no se pueden activar cargas por
  error. `BarraArrastrable(id, alto)` define la zona de agarre y `Reset()` vuelve
  todo a las posiciones por defecto.
- Se elimino el `InteraccionUI.Registrar` duplicado de cada panel (lo hace
  `Paneles.Rect`), evitando que el area de bloqueo quedara desfasada al moverlo.
- Boton **"Restablecer paneles"** en el menu fijo de la izquierda
  (`ViewerController.OnGUI`) y en la cabecera de Esfuerzos.

## F2 — Alcance de deformada y diagramas — LISTO

Los campos `AlcanceVisual`, `DiagramaAlcance`, `DeformadaAlcance` y
`DiagramaEscala` estaban declarados pero **nunca se leian**: la deformada era
siempre de un solo edificio y el diagrama solo del elemento seleccionado.

- `EdificiosEnAlcance(alcance)` / `VisibleEnViewer(b)`: lista de edificios del
  alcance (I, II o ambos) ya filtrada por lo que el usuario tiene **visible**.
- `RebuildDeformada`: recorre los edificios del alcance y usa **una sola
  amplificacion** (`Amplificacion`) para todos, de modo que con "Ambos" las dos
  deformadas quedan a la misma escala y son comparables.
- `DrawDiagrams` se divide en un despachador por alcance y
  `DrawDiagramaElemento` (dibujo de un FE):
  - `Elemento`: comportamiento original, con la escala local por longitud del FE.
  - `Edif I / Edif II / Ambos`: todos los elementos del alcance con **escala
    comun**: el pico mayor del alcance ocupa `DiagramaEscala` metros
    (`escalaComun = DiagramaEscala / picoAlcance`), de forma que las curvas de I y
    II tienen la misma referencia.
- `ValoresMagnitud` extrae i/j de `EnvValores` (envolvente) o de `FuerzasVista`
  (resto), sin recalcular nada.
- **Rendimiento en modo edificio(s)**: el alcance "Ambos" abarca los 631 FE de
  los dos edificios (378 en I + 253 en II). Se dibuja la **curva de todos** (3
  `LineRenderer` por FE, todos con la misma escala, que es lo que hace posible la
  comparacion) pero los rotulos `i`/`j`/`max` se ponen **solo en el elemento de
  pico** del alcance: tres `TextMesh` por FE serian ~1.900 objetos, inviables en
  el APK Android e ilegibles de tan juntos. El panel indica cuantos FE pintaron
  curva y que el rotulo va en el pico.
- `OnVisualFiltersChanged` ahora redibuja deformada y diagramas: si se oculta el
  edificio II, sus curvas desaparecen.
- `MarcarDiagramaSucio` ya no exige seleccion previa en alcance de edificio(s).
- Panel: fila **"Alcance diag:"** y **"Alcance def:"** (Elem / Edif I / Edif II /
  Ambos) y slider **"Escala comun (m)"** cuando el alcance no es Elemento.

## F3 — Camara dual — LISTO

- `FrameAll()` encuadra el **bbox conjunto de los edificios visibles** (I+II en
  la misma vista y a la misma escala) en vez de todos los renderers de `Lab`
  indiscriminadamente; si no hay ningun edificio visible cae a todos.
- `FrameBuilding(b)` encuadra **solo** un edificio.
- Menu de camara: **"Conjunto I+II" / "Solo I" / "Solo II"**, mas
  **"Vista inicial"** (`Cam.Home`, que recupera el ultimo bbox conjunto).
- El enfoque por elemento (`FocusOn`) se mantiene: la navegacion global es
  sobre el conjunto, el detalle sigue siendo por elemento.

## F4 — Flecha PL1 adaptativa — LISTO

- **Color fucsia/magenta** (`0.94, 0.10, 0.55`) en lugar de naranja, con una
  variante apagada para el estado invalidado.
- **Escala adaptativa con recorte** (`LargoVisual`): longitud
  `clamp(distCamara * 0.11, 0.65, 4.5) m`, y grosor/punta proporcionales, para
  que la flecha se lea igual de cerca que de lejos.
- **La posicion fisica de aplicacion no se mueve**: `baseW` (el punto xi del
  elemento) es fijo; solo crece la longitud visual hacia fuera.
- **Billboard**: la etiqueta mira siempre a la camara, con `characterSize`
  proporcional, y se separa del cono hacia el observador y arriba.
- **Estados ACTIVA / INACTIVA** explicitos en el texto (segun
  `EsCasoA_SoloMagnitud`, que decide si el caso A por linealidad sigue siendo
  valido o hay que reanalizar).
- **Magnitud y desplazamiento en mm**: la etiqueta muestra
  `P=<kN> (direccion)` y `d=<mm>`, con el desplazamiento real del solver
  interpolado linealmente entre los extremos del elemento en `xi`
  (`DespNodoElemento`), no el valor amplificado de la deformada visual.

## Verificacion de la segunda tanda

- **Unity** `6000.5.10f1 -batchmode -quit`: **rc=0, sin `error CS`** en los
  cuatro frentes (solo los warnings preexistentes de `FindObjectOfType`
  obsoleto y del analizador de serializacion).
- **Suite Python**: **88 passed, 20 failed** — exactamente el baseline. Las 20
  fallas son preexistentes y regenerables
  (`FileNotFoundError: results/superposicion/verificacion_superposicion_completa_{I,II}.json`,
  paso E3.4 de Entrega 3) y no guardan relacion con estos cambios, que son
  exclusivamente de C# del viewer.
- Sin commit: el estado final queda en `git status`.

## Pendientes de la segunda tanda

- Verificacion manual en el editor (arrastre de paneles, contraste I vs II con
  la deformada en "Ambos", lectura de la flecha PL1 a distintas distancias de
  camara) y en el APK del telefono.