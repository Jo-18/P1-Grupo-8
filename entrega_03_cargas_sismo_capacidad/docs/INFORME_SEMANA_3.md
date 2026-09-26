# Informe Semana 3 — Entrega 03 (cargas, sismo, superposición, capacidad RC)

> Resumen ejecutivo del estado verificado de la entrega integral. Los números provienen
> de las corridas ejecutadas por `src/ejecutar_entrega_03.py` (estado global **OK**,
> 12 corridas) y de los JSON/CSV. Los JSON crudos regenerables viven en `results/`
> y `figures/` (ignorados por git); las **copias versionadas** están en `docs/tables/`
> y `docs/assets/` (los enlaces de este informe apuntan a esas copias).
> Acta numérica de cierre: [`docs/ACTA_VERIFICACION_FINAL.md`](ACTA_VERIFICACION_FINAL.md).

## 1. Lo que se hizo esta semana

1. **q_Q normativo adoptado**: la sobrecarga de uso pasa de `null` a **q_Q = 3,0 kN/m²**
   (EI y EII), como **mínimo** de la categoría "Escuelas — salas de clases" de la
   **Tabla 4 de la NCh 1537:2009** (clasificación
   `PARAMETRO_BASADO_EN_NORMA_NCH1537_2009_TABLA4`), reemplazando la adopción previa
   del grupo de 2,0 kN/m². Queda registrado en `config/cargas.json`; EI → ΣQ = 12.328,42 kN
   (Δ 0,0), EII → 7.889,14 kN (rel 5,7e-09).
   Evidencia: [`tables/cargas/carga_viva_Q_I.json`](tables/cargas/carga_viva_Q_I.json).
2. **Sismo pseudoestático EX/EY ejecutado y verificado** por el método de la
   consigna (clasificación `PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA`):
   `a=0,20g`, `W_i = PP_i + 0,50·Q_i`, `F_i = 0,20·W_i`, distribución nodal
   proporcional. 4 corridas OK (EX/EY × EI/EII) con retcode 0.
   Evidencia: [`tables/cargas/caso_sismico_EX_I.json`](tables/cargas/caso_sismico_EX_I.json)
   y `caso_sismico_{EY_I,EX_II,EY_II}.json`.
3. **Superposición completa verificada por edificio**: 5 corridas FE (G, Q, EX, EY y
   la combinación explícita `1.0G+0.7Q+0.3EX−0.2EY` del conjunto de demostración);
   la respuesta superpuesta vs la explícita da 8/8 magnitudes OK con errores máx
   ~9,8e-16 (EI) y ~1,7e-13 (EII); `config/superposicion.json`:
   `verificacion_final = IMPLEMENTADO_Y_VERIFICADO_COMPLETO`.
   La figura separa **paneles por magnitud** (desplazamientos [m], reacciones [kN],
   fuerzas axiales [kN], momentos [kN·m]) y el error relativo en escala logarítmica
   con piso de representación 1e-16 (errores ≈ 0); la combinación de demostración
   queda rotulada en la propia figura.
   Evidencia: [`tables/superposicion/verificacion_superposicion_completa_I.json`](tables/superposicion/verificacion_superposicion_completa_I.json)
   (y `_II.json`).
4. **Capacidad RC por edificio** con secciones por fibras (Fiber Section, malla
   hormigón + acero, cross-check OpenSeesPy): sección real de columna 70×70
   documentada; armadura real no documentada → armado de demostración 12#25
   (`HIPOTESIS_DEMOSTRACION`). Resultados Mu(N=0): **EI 896,46 kN·m** (f'c 40 MPa,
   hipótesis del grupo G40) y **EII 875,00 kN·m** (f'c 35 MPa, documentado G35).
Criterio de falla: aplastamiento del hormigón (eps_cu = 0,004). Las figuras
    de capacidad marcan **`M_u` en su `κ_u`** y **truncan las curvas M–φ en el primer
    criterio de falla** (`M_u` = momento en el paso de falla, **no el máximo de la
    malla**); las seis figuras llevan la advertencia visible
    `DEMOSTRACIÓN — SECCIÓN HIPOTÉTICA, NO VÁLIDA PARA DISEÑO`.
    Evidencia: [`assets/capacidad_rc/DEMO_RC_EI_seccion_fibras.png`](assets/capacidad_rc/DEMO_RC_EI_seccion_fibras.png),
    [`assets/capacidad_rc/DEMO_RC_EI_m_phi.png`](assets/capacidad_rc/DEMO_RC_EI_m_phi.png),
    [`assets/capacidad_rc/DEMO_RC_EI_diagrama_pm.png`](assets/capacidad_rc/DEMO_RC_EI_diagrama_pm.png)
    (idem `DEMO_RC_EII_*`: sección → M–φ → P–M).
5. **D/C por edificio** (estado `EVALUACION_ALGORITMICA_CON_SECCION_DEMO`): demanda =
   respuesta EXPLICITA de la superposición (misma corrida FE) y capacidad = P–M
   interpolado M_u(N) de una **sección de demostración**. Todas las columnas se
   **evalúan mediante el procedimiento** (EI 97, EII 32) con comparación **aritmética**
   D/C<=1 contra capacidad demo; críticas col 208 (D/C = 0,54) y col 25 (D/C = 0,26).
   Las 97 y 32 demandas caen **dentro del rango de interpolación N del P–M** (100 % en
   modo `interpolado`, **0 columnas fuera de rango / no evaluables**).
   **No válido como comprobación de diseño; no aprueba las columnas reales**.
   Evidencia: [`tables/capacidad_rc/demanda_capacidad_I.json`](tables/capacidad_rc/demanda_capacidad_I.json)
   (y `_II.json`, `resumen_demanda_capacidad.txt`).
6. **Ejecutor único** `src/ejecutar_entrega_03.py`: corre el pipeline completo en un
   comando y deja traza de estado en `results/ejecutor_entrega_03/estado.{json,md}`.

## 2. Resultados clave (verificados)

| Concepto | Edificio I | Edificio II |
|---|---|---|
| Peso sísmico `W` = Σ(PP + 0,50·Q) | 31.391,94 kN | 29.915,57 kN |
| Corte basal `F = 0,20·W` | 6.278,39 kN | 5.983,11 kN |
| Verificación superposición completa | 8/8 OK (máx rel 9,8e-16) | 8/8 OK (máx rel 1,7e-13) |
| Sección columna (documentada) | P. 70×70 (f'c 40 MPa, G40 hipótesis) | P. 70×70 (f'c 35 MPa, G35 doc) |
| Armado | 12#25 (demo, rec 0,04 m, fy 420) | 12#25 (demo) |
| M_u(N=0) | 896,46 kN·m | 875,00 kN·m |
| D/C: columnas evaluadas / total | 97 / 97 (aritmético, sin validez de diseño) | 32 / 32 (aritmético, sin validez de diseño) |
| Columna crítica (nivel, extremo) | 208 (P4, j) D/C 0,5373 | 25 (EII_CP3, j) D/C 0,2572 |

> ⚠️ **Ninguna línea de esta tabla es un resultado definitivo de diseño.** Las
> filas de sección/armado/M_u/D/C usan **secciones de demostración**
> (`HIPOTESIS_DEMOSTRACION`) y la combinación de superposición es un **conjunto de
> demostración** (`1.0_0.7_0.3_-0.2`). La tabla demuestra que el flujo completo
> (cargas → sismo → superposición → P–M → D/C) se ejecuta y se verifica numéricamente
> con errores de máquina; no certifica ninguna columna ni edificio.

## 3. Honestidad de alcance

- EX/EY usan el **método de la consigna**, no parámetros normativos (zona, suelo,
  R, espectro quedan `null`/PENDIENTE): no se declaran resultados sísmicos normativos.
- La superposición usa el **conjunto de demostración** `1.0_0.7_0.3_-0.2` (coeficientes
  normativos reales pendientes).
- M_u, P–M y el D/C usan **secciones de demostración** (`HIPOTESIS_DEMOSTRACION`):
  demuestran el flujo completo de integración, no son capacidad de diseño real.
- En el chequeo de sentido de deformada, EII tiene nodos de la franja D-D′ fuera del
  diafragma rígido con productos `f·u` locales opuestos; el desplazamiento dominante
  es correcto y se reporta como nota (ver `results/cargas/caso_sismico_EY_II.json`).
- PP del EI incompleto (v2 cota inferior) y G_EII sin cerrar (discrepancia de muros):
  detalle y figuras en `docs/ACTA_VERIFICACION_FINAL.md` §1.4.

## 4. Criterios de la rúbrica → dónde queda evidenciado

| Criterio | Evidencia en esta entrega |
|---|---|
| **Q (carga viva) y EX/EY (sismo)** | Q: `carga_viva_Q_*` con q_Q=3,0 kN/m² (NCh 1537:2009 Tabla 4, "Escuelas — salas de clases"), ΣQ=q_Q·A verificado por nivel/global ([tables/cargas/carga_viva_Q_I.json](tables/cargas/carga_viva_Q_I.json)). EX/EY: `caso_sismico_*` (4 corridas, retcode 0, corte basal `0,20·W`, equilibrio y sentido verificados, acta §1; [EX_I](tables/cargas/caso_sismico_EX_I.json)) |
| **Superposición verificada** | [tables/superposicion/verificacion_superposicion_completa_I.json](tables/superposicion/verificacion_superposicion_completa_I.json) (y `_II.json`): 8/8 filas OK, errores de máquina, estado `IMPLEMENTADO_Y_VERIFICADO_COMPLETO`; figura [assets/superposicion/verificacion_superposicion_completa_I.png](assets/superposicion/verificacion_superposicion_completa_I.png) |
| **Fiber Section (secciones por fibras)** | `src/capacidad_rc/fiber_section.py` + tests (área conservada, sin tracción, cross-check OpenSeesPy); secciones en [assets/capacidad_rc/DEMO_RC_EI_seccion_fibras.png](assets/capacidad_rc/DEMO_RC_EI_seccion_fibras.png) (y `EII`) |
| **Primeras curvas de capacidad** | M–φ y envolvente P–M por edificio: [assets/capacidad_rc/DEMO_RC_EI_m_phi.png](assets/capacidad_rc/DEMO_RC_EI_m_phi.png) y [assets/capacidad_rc/DEMO_RC_EI_diagrama_pm.png](assets/capacidad_rc/DEMO_RC_EI_diagrama_pm.png) (idem EII); Mu(N=0) 896,46 / 875,00 kN·m; D/C interpolado sobre P–M |
| **Defensa individual** | `docs/GUIA_DEFENSA.md` (explicación del flujo y de qué significa cada resultado), `docs/PREGUNTAS_PROFESOR_MIERCOLES.md`, este informe y `docs/ACTA_VERIFICACION_FINAL.md` |

## 5. Cómo reproducir todo

```bash
python -X utf8 -m unittest discover -s tests -p "test_*.py"
python -X utf8 -m src.ejecutar_entrega_03
```

Un comando re-ejecuta casos Q, sismo EX/EY (×2 edificios), verificación G+Q,
superposición completa (×2), capacidad RC y D/C; el estado queda en
`results/ejecutor_entrega_03/estado.json`.

## 6. Pendientes para destrabar (no bloquean el flujo de demostración)

- Sismo: parámetros normativos si el docente exige diseño por norma.
- Superposición: coeficientes normativos reales.
- Capacidad: fy, recubrimiento y armadura reales de columnas/muros (para que el D/C
  deje de ser aritmético y pase a ser comprobación de diseño).
- PP EI (v2 cota inferior, banda no adoptada) y discrepancia de muros EII (G_EII).
- Riesgos menores señalados en el acta: chequeo `sum_por_nivel` en z=−4 del EI (atribución de herramienta, no desequilibrio), franja D-D′ EII, y superposición sin familia de cortantes.

## 7. Overlay de esfuerzos FE en el viewer Unity (integración final)

Se incorporó al viewer Unity la visualización de **esfuerzos internos por elemento FE**
como **overlay independiente** (tubería fina en las coordenadas exactas del modelo FE), sin
recolorear la geometría original (solo la atenúa opcionalmente) y **sin inventar**
resultados: los valores provienen 1:1 de las corridas FE ya verificadas.

- **Exportador**: [`src/unity_esfuerzos/exportar_esfuerzos_para_viewer.py`](../src/unity_esfuerzos/exportar_esfuerzos_para_viewer.py)
  genera `effuerzos_FE_EDIFICIO_{I,II}.json` (I: 349 elementos/1 745 vectores; II: 264/1 320;
  total 613/3 065) a partir de `results/superposicion/verificacion_superposicion_completa_{I,II}.json`
  (corridas `G`,`Q`,`EX`,`EY` y `EXPLICITA`) y de la metadata geométrica (CSV EI y `caso_G_EII_reproducible.json`).
  La corrida **COMBINADA = EXPLICITA** `1.0G+0.7Q+0.3EX−0.2EY` se copia tal cual, sin
  recomponer; redondeo fuerzas 6, coordenadas 9; convención `localForce`
  `[N_i,Vy_i,Vz_i,T_i,My_i,Mz_i,N_j,Vy_j,Vz_j,T_j,My_j,Mz_j]` (kN/kN·m, +N = compresión).
- **Correspondencia viewer 1:1 por coordenadas** (`1A1`/`CONTENIDO`/`SIN_CORRESPONDENCIA_VIEWER`):
  EI → columna 43 `1A1`/54 `SIN`, viga 66 `1A1`/97 `CONTENIDO`/41 `SIN`, muro 7 `CONTENIDO`/39
  `SIN`, stub 2 `SIN`; EII → columna 32 `1A1`, viga 175 `1A1`, muro 49 `CONTENIDO`/8 `SIN`.
  La correspondencia es solo de referencia (identifica qué objeto del viewer contiene el
  elemento FE); nunca asigna valores FE a la geometría visual.
- **Trazabilidad**: `manifest.json` declara la sección `esfuerzos_FE` y los dos archivos
  nuevos en `archivos`; `CheckData` los valida.
- **Runtime**: `EsfuerzosController` (se auto-adjunta en `AfterSceneLoad`, sin editar
  `Main.unity`), panel propio (casos, magnitudes N/Vy/Vz/T/My/Mz, extremos i/j/max-abs,
  escala P95/Máximo, diagramas interpolados con advertencia), selección por raycast (tag).
- **Verificación automática (aceptación, modo editor, determinista)**:
  `Unity -batchmode -quit -projectPath viewer_unity -executeMethod LabViewer.EditorTools.LabViewerEditor.CheckEsfuerzosOverlay`
  → **OK**: carga I/II, conteos 349/264, 5 anclas numéricas (I tag3 G[N_i]=141.800353…,
  COMBINADA[N_i]=355.834…, COMBINADA[Mz_i]=-143.636…; II tag1 G[N_i]=1186.506…,
  COMBINADA[N_i]=1474.218…), overlay 349/264 tuberías, selección tag3, escala>0 y
  restauración 0. Evidencia PNG en `viewer_unity/capturas/esfuerzos_{I_COMBINADA_N,II_G_Mz}.png`
  (rendered batch con device gráfico).
- **Python**: `tests/unity_esfuerzos/test_exportar_esfuerzos_viewer.py` (12 tests de
  estructura/fidelidad de fuente/metadata/correspondencia); suite completa **40/40 OK**.

## 7.1 Corrección de fidelidad geométrica del overlay (doble transformación)

**Síntoma**: en Play Mode interactivo el overlay mostraba cientos de tuberías flotando y
separadas de la estructura, pese a que los conteos (349/264) y los valores numéricos
pasaban todas las pruebas.

**Diagnóstico (confirmado en código, no en datos)**:

1. `CrearTuberia()` construía la malla con `Prisma(w0, w1, …)` en **coordenadas
   mundiales** y además aplicaba `go.transform.position = mid` y `go.transform.rotation =
   FromToRotation(…)` sobre el mismo GameObject: **doble transformación** (malla absoluta
   que además se trasladaba/rotaba). Eso esparcía los prismas fuera de su posición real
   → la nube de rayas flotantes.
2. Se descartó la hipótesis del orden `(x,y,z)`: el contrato del paquete es
   `p_i_unity = [u, cota, v]` (ver `frame.nota` en los JSON y `leer_metadata_I/II` del
   exportador). El **segundo** índice es la elevación (p. ej. tag 3 de EI, P1: pasa de
   `-4.01` a `-0.05` en el índice 1). `ToWorldModel(b, u, cota, v)` ya se usaba
   correctamente; cambiar el orden habría *roto* la geometría.

**Corrección v1 (doble transformación)** (`EsfuerzosController.cs`):

- Malla en **espacio local** (`PrismaLocal(0, L, …)` a lo largo del eje +Y del objeto).
- `go.transform.position = mid` y una **única** rotación para alinear el eje local con
  `w1−w0`.
- `BoxCollider` en las **mismas coordenadas locales** (`center=(0, L/2, 0)`,
  `size=(0.35, L+0.2, 0.35)`) para que la selección por raycast siga funcionando.

**Corrección v2 (desplazamiento residual L/2)** — la v1 era incompleta: con malla local
`0..L` y posición en `mid`, cada tubería quedaba desplazada `L/2` hacia su extremo j
(columnas sobresaliendo media planta en cubierta y sobre su base; vigas sin coincidir
extremo a extremo). La v1 además validaba `transform.position` (=`mid`, siempre correcto),
por lo que no detectaba el desvío de los extremos renderizados. Corrección:

- Convención **centrada**: malla local `PrismaLocal(-L/2, +L/2, …)`, posición `mid`,
  rotación única +Y→(w1−w0).
- `BoxCollider.center = Vector3.zero`, `size=(0.35, L+0.2, 0.35)`.
- Auditor in-engine reemplazado: `VerificarGeometria(tol, …)` compara por cada elemento
  los extremos **reales renderizados** `TransformPoint(LocalA/B)` contra `w0/w1` (orden
  directo o invertido), `Renderer.bounds.center` contra `(w0+w1)/2` y la longitud
  renderizada contra `|w1−w0|`. Reporta error máximo, RMS y cantidad fuera de tolerancia
  (`TOL_GEOM = 0.01 m`). Cubre **todos** los elementos de EI y EII (613).

**Evidencia del auditor (antes/después)**:

- Antes de la v2, funcionando contra la implementación desplazada: `[Geometria]
  maxErrExtremos=6.25 m RMS=2.79 m maxErrCentroBounds=6.25 m fueraTol=264 → FALLO`
  (el error coincide con L/2 del elemento más largo: 6.25 m).
- Después de la v2: `[Geometria] maxErrExtremos=0.0000 m RMS=0.0000 m
  maxErrCentroBounds=0.0000 m maxErrLongitud=0.0000 m fueraTol=0 → OK`.

**Tests de aceptación geométrica nuevos** (`tests/unity_esfuerzos/test_geometria_overlay_fiel.py`,
8 tests):

- extremos `1A1` overlay vs viewer (columnas en el plano (u,v) + cota base; vigas en 3D);
- error máximo y RMS en metros;
- bounding box + centroide overlay FE vs edificio correspondiente;
- envolvente espacial: falla si cualquier tubería queda fuera del edificio inflado;
- elementos `SIN_CORRESPONDENCIA_VIEWER` en su posición real (sin nubes flotantes);
- columnas FE verticales (deriva horizontal ≤ 2e-3 m);
- vigas FE a la cota de su piso; vigas `1A1` descansando sobre la viga del viewer.

**Resultado**: 1A1 → **max error 0.0005 m, RMS 0.0000 m** (632 extremos entre I y II);
envolvente FE ≈ viewer (centroides: EI ΔX=ΔZ=0, ΔY=1.5 m por 2 stubs verticales; EII 0.0 m).
Suite Python complete **60/60 OK** (40 previos + 8 nuevos + laboratorio semana 2).

**Verificación en-engine (batch)**:
`CheckEsfuerzosOverlay` → **OK** (con `[Geometria]` por extremos, todos los elementos);
`EsfuerzosAudit.Run` (play, device gráfico) → **AUDIT ESFUERZOS FE: OK** (exit 0). Capturas
regeneradas: `viewer_unity/capturas/esfuerzos_I_COMBINADA_N.png` (41.7 KB) y
`esfuerzos_II_G_Mz.png` (40.5 KB). Histórico de tamaños: 67.7/57.5 KB (doble transformación,
rayas esparcidas) → 47.5/41.7 KB (v1, desplazadas L/2) → 41.7/40.5 KB (v2, coincidentes).

**Pendiente**: confirmación visual del usuario en Play Mode interactivo.

## 7.2 Selección del overlay FE por correspondencia viewer↔FE (interacción)

**Síntoma**: en Play Mode el clic sobre una columna visible seleccionaba una barra FE
incorrecta (p. ej. pinchando la columna `COL_EI_CP3_C_I3_40.0` se mostraba la viga FE
`tag 494` del nivel P2): el viejo `SeleccionarPorRay` elegía el `EFPicker` FE **más
cercano a la cámara** entre todos los impactos de la pantalla, sin comprobar que ese FE
correspondiera al elemento del viewer realmente pinchado.

**Causa raíz**: la correspondencia `viewer_id` del JSON (`correspondencia.viewer_id`,
`correspondencia.viewer_nivel`) no era la fuente de la selección; el rayo podía saltar a
otra barra FE delante/detrás en pantalla (vista con elementos superpuestos).

**Corrección** (esquema implementado):

1. El clic usa `ProcesarClic`: `Physics.Raycast` al **primer** impacto, que identifica el
   `ElementRef` de la geometría original pinchada (el mismo que selecciona el
   `ViewerController`). 

2. Los FE se eligen **exclusivamente** por la correspondencia
   `correspondencia.viewer_id == ElementRef.Id` (y `correspondencia.viewer_nivel ==
   ElementRef.Level`):
   - `1A1` → el FE directo del elemento;
   - `CONTENIDO` → se filtran los sub-elementos FE de la misma barra viewer, se elige el
     segmento más cercano al punto REAL del clic (`SegmentoMasCercano`) y la cabecera
     muestra `segmento n/N` con botones ◀ / ▶ (`CiclarSegmento`);
   - `SIN_CORRESPONDENCIA_VIEWER` → **no** se selecciona ninguna otra barra; el panel
     informa que ese elemento del viewer no tiene FE mapeado.

3. Solo cuando el clic cae directamente en un tubo FE **sin** correspondencia, se
   selecciona ese tubo directo. Si el tubo tiene `viewer_id`, se re-enruta por él.

4. Filtros de overlay nuevos en la UI: tipología (Vigas / Columnas / Muros) y
   correspondencia (**Mapeados** [1A1+CONTENIDO, esto es el comportamiento por defecto] /
   **Todos los FE** [incluye SIN_CORRESPONDENCIA_VIEWER]). Con el default Mapeados los
   tubos visibles son I=213 y II=256 (se ocultan los 136+8 SIN_CORRESPONDENCIA_VIEWER).

5. Cabecera fija del panel: `Viewer: id · tipo · nivel`, `Elemento FE: tag · tipo ·
   nivel · estado`, valores `i / j / max|abs|` del caso/magnitud actuales y (si hay
   CONTENIDO) `segmento n/N` con el ciclo. La selección se conserva al cambiar
   caso/magnitud/extremo (`RebuildOverlay` re-aplica el resaltado amarillo).

**Prueba automática** (`EsfuerzosAudit.Run`, modo play, ambas edificaciones): clics
**reales de pantalla** (proyección a `ScreenPointToRay` desde `Camera.main`, el mismo
camino que el usuario) desde **varias poses de cámara** (vistas con elementos
superpuestos) sobre EI y EII, verificando las comprobaciones obligatorias:

- columna viewer → FE columna del nivel correspondiente;
- viga viewer → FE viga (nunca columna) del mismo piso (nunca otro nivel);
- dos columnas con valores axiales distintos (verificación de que el clic devuelve los
  esfuerzos de la propia barra);
- dos vigas con `My` o `Mz` distintos;
- el auditor **FALLA** si el `viewer_id` mostrado en la selección no coincide con
  `correspondencia.viewer_id` (invarianza `idOk`, `tipoOk` y `nivelOk` por cada clic).

Resultado del auditor en batch (tras regenerar capturas):

```
[ClicCorr I]  clics=… invarianza=OK dosColN=OK dosVigas=OK -> OK
[ClicCorr II] clics=… invarianza=OK dosColN=OK dosVigas=OK -> OK
AUDIT ESFUERZOS FE: OK  (exit 0)
```

Capturas regeneradas con el elemento FE correctamente seleccionado + ficha 3D visible:
`capturas/esfuerzos_I_COMBINADA_N.png` y `capturas/esfuerzos_II_G_Mz.png`.

**Pendiente**: confirmación visual del usuario en Play Mode (pinchar una columna visible y
obtener sus esfuerzos; comprobar el cambio de segmento en CONTENIDO).