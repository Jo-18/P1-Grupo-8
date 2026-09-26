# GUÍA DE DEFENSA EN VIVO — SEMANA 5

Todo lo de este documento está verificado contra el código. Leyenda: **[H]** hecho/implementado · **[V]** verificado por ejecución · **[S]** supuesto/hipótesis · **[L]** limitación.

---

## 0. ESTADO PARA LA DEFENSA (el profesor llega y tú tienes esto)

- **OpenSeesPy: [V]** corre en `.venv` (Python 3.12, `openseespy==3.7.0.3`). Import OK, solver rc=0, exportadores dry-run OK.
- **Documentación P3/P4 corregida** en `reports/semana05.md` y banner/UI de `LabModificaciones.cs` (pendiente recompilar en Unity).
- **Tests**: 108 → 88 OK, 0 FAIL, 20 ERROR (todos son `FileNotFoundError` de un insumo regenerable, ver §0.4). Sin impacto en el flujo S05.
- **P-M es DEMO** (armadura hipótesis) **[S — declarado en el repo]**.
- **M2 oculta visualmente el elemento pero NO resuelve el sistema nuevo** **[L]**; M3 registra pero NO cambia la malla visible **[L]**; SQ4 es click (prototipo) no seguimiento continuo **[L]**.

## 0.4 Discrepancia de tests (aclarada)

| Métrica | Auditoría anterior | Estado actual (re-ejecutado hoy, `.venv` py3.12) |
|---|---|---|
| Total | Ran 104 | **Ran 108** |
| OK/PASS | — | **88** |
| FAIL | 0 | **0** |
| ERROR | 51 | **20** |
| SKIP | — | **0** |

Causa del cambio 104/51 → 108/20: la auditoría anterior corrió con el **Python 3.14 del sistema** (sin `.venv`), donde `openseespy` NO importaba → errores extra de import/e2e. Con `.venv` (Python 3.12) los módulos importan y el solver corre.

Los **20 ERROR actuales son todos idénticos**: `FileNotFoundError` en
`results/superposicion/verificacion_superposicion_completa_{I,II}.json`
(los 20 errores coinciden con ese path). Origen:
`src/unity_esfuerzos/exportar_esfuerzos_para_viewer.py` → `leer_superposicion` (L100), del exporter LEGACY.

Módulos (2):
- `tests/unity_esfuerzos/test_exportar_esfuerzos_viewer.py` → 12 tests.
- `tests/unity_esfuerzos/test_geometria_overlay_fiel.py` → 8 tests.

Clasificación:
- **Afectan Semana 5: NO.** El flujo S05 usa `exportar_esfuerzos_funcional_para_viewer.py`, que no depende de ese JSON.
- **Preexistentes / insumos regenerables:** los 20. El archivo faltante lo genera el paso 4 de `src/ejecutar_entrega_03.py` (`src/cargas/verificacion_superposicion_completa.py`); es gitignored (`results/` se regenera).
- Respuesta al profesor: *"108 tests, 88 pasan, 0 fallan; los 20 errores son de un módulo exportador legacy que necesita regenerar un archivo de verificación intermedia de la Entrega 3 (`results/superposicion/...`), no afecta el pipeline de Semana 5."*

---

## 1. PREPARACIÓN DEL COMPUTADOR (antes de que llegue el profesor)

### VS Code — pestañas en este orden

1. `entrega_03_cargas_sismo_capacidad/src/modelo_fiel/modelo_fe_completo.py` — el solver S05. Ctrl+F: `import openseespy`, `rigidDiaphragm`, `def construir`, `def correr`.
2. `entrega_03_cargas_sismo_capacidad/src/unity_esfuerzos/exportar_esfuerzos_funcional_para_viewer.py` — cómo los FE llegan a Unity. Ctrl+F: `CASOS_BASE`, `def main`, `elementos`.
3. `entrega_03_cargas_sismo_capacidad/src/unity_esfuerzos/pm_capacidad_demanda_hitob.py` — P-M y D/C. Ctrl+F: `_mu_interp`, `_evaluar`, `NOTA_MURO_ARMADURA`.
4. `entrega_03_cargas_sismo_capacidad/src/modelo_fiel/combinaciones_nch3171.py` — las 9 combinaciones. Ctrl+F: `U1_GQ`, `U4_EX_NEG`.
5. `analisis_estructural/edificio_I/src/analisis/fe/resolver.py` — comando `ops.*` (análisis y extracción). Ctrl+F: `eleResponse`, `nodeDisp`, `analyze`.
6. `analisis_estructural/edificio_I/src/analisis/fe/marco.py` — modelo (nodos/elementos/diafragma). Ctrl+F: `rigidDiaphragm`, `ops.element`, `ops.fix`.
7. `viewer_unity/Assets/Scripts/EsfuerzosController.cs` — overlay, superposición λ, deformada, P-M en Unity. Ctrl+F: `CombinarLibre`, `DespLibre`, `MuParaN`, `SetLam`, `RebuildDeformada`.
8. `viewer_unity/Assets/Scripts/LabModificaciones.cs` — M1–M4, banner, export JSON. Ctrl+F: `ToggleElemento`, `AplicarSeccion`, `Exportar`, `MarcarReanalisis`.
9. `viewer_unity/Assets/Scripts/LabLoader.cs` — carga de StreamingAssets y placement. Ctrl+F: `LoadPlacement`, `ToWorldModel`, `BuildBuilding`.
10. `viewer_unity/Assets/Scripts/ViewerController.cs` — raycast, selección, filtros/capas. Ctrl+F: `RaycastPick`, `ApplyFilters`, `Select`.

### Unity (proyecto ya abierto)

- Proyecto: `viewer_unity` · Escena única: `Assets/Scenes/Main.unity`.
- Hierarchy: expandir **GO "Lab"** (o el contenedor `1734279528` con `ViewerController` + `LabLoader`) y **Main Camera** (con `CameraController`, Target = LabTarget).
- GameObjects importantes: Main Camera (16619364) + AudioListener; Sun (75092570); contenedor con ViewerController+LabLoader (1734279528); LabTarget (2032357102). 4 raíces en la escena.
- Inspector útil: Main Camera → `CameraController` (Distance 55, Yaw 45, Pitch 25); contenedor → componente `LabLoader` (lista niveles) y `EsfuerzosController` (overlay activo).
- Paneles/UI a dejar visibles: vista Game 3D (origen 0,0,0), panel izquierdo del viewer y panel "LABORATORIO S5" (derecho). Play mode para la demo.

### PowerShell (carpeta y comandos listos para copiar)

Carpeta base:
```
cd "C:\Users\javie\OneDrive\Escritorio\Universidad\9no semestre\MCOC\Proyecto 1\Proyecto1_Semana05_estable_31e5cfb\P1-Grupo-8-semana05"
```
Activar entorno (1 vez) y verificar OpenSeesPy:
```
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -X utf8 -c "import openseespy.opensees as ops; print('OpenSeesPy OK')"
```
Correr el solver (desde `entrega_03_cargas_sismo_capacidad/`):
```
cd entrega_03_cargas_sismo_capacidad
..\.venv\Scripts\python.exe -X utf8 -m src.modelo_fiel.modelo_fe_completo --g --sismo --combinadas
```
Exportar esfuerzos al viewer (default I y II; `--dry-run` no escribe):
```
..\.venv\Scripts\python.exe -X utf8 -m src.unity_esfuerzos.exportar_esfuerzos_funcional_para_viewer
```
Regenerar P-M / D-C (relee esfuerzos + DEMO_RC):
```
..\.venv\Scripts\python.exe -X utf8 -m src.unity_esfuerzos.pm_capacidad_demanda_hitob
```
Suite de tests:
```
..\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests
```

---

## 2. LOS 10 ARCHIVOS MÁS IMPORTANTES

| # | Archivo | Ruta | Qué contiene | Ctrl+F | Responde: |
|---|---------|------|--------------|--------|-----------|
| 1 | modelo_fe_completo.py | `entrega_03_cargas_sismo_capacidad/src/modelo_fiel/` | Solver S05: modelo + G/Q/EX/EY + combos | `rigidDiaphragm`, `correr_combinadas`, `OUT =` | "¿Dónde se arma y resuelve el modelo?" |
| 2 | exportar_esfuerzos_funcional_para_viewer.py | `.../src/unity_esfuerzos/` | Traduce payloads FE → JSON del viewer | `CASOS_BASE`, `def main`, `"unidades"` | "¿Cómo llega esto a Unity?" |
| 3 | pm_capacidad_demanda_hitob.py | `.../src/unity_esfuerzos/` | P-M: N/M → Mu(P) → D/C | `_mu_interp`, `_evaluar`, `CLASIF_EVAL` | "¿Dónde está el P-M?" |
| 4 | combinaciones_nch3171.py | `.../src/modelo_fiel/` | Fórmulas U1..U4 | `U1_GQ`, `0.9*G` | "¿Qué combinaciones usas?" |
| 5 | resolver.py | `analisis_estructural/edificio_I/src/analisis/fe/` | Comandos ops.* (analyze, nodeDisp, eleResponse) | `eleResponse`, `ops.analyze` | "¿Dónde se resuelve y se extrae el resultado?" |
| 6 | marco.py | `analisis_estructural/edificio_I/src/analisis/fe/` | Nodos, elementos, secciones, apoyos, diafragma | `rigidDiaphragm`, `ops.fix`, `ops.element` | "¿Dónde está el diafragma rígido?" |
| 7 | EsfuerzosController.cs | `viewer_unity/Assets/Scripts/` | Overlay, λ, deformada, P-M, diagramas | `CombinarLibre`, `DespLibre`, `MuParaN`, `RebuildDeformada` | "¿Por qué los sliders no reanalizan?" / deformada |
| 8 | LabModificaciones.cs | `viewer_unity/Assets/Scripts/` | M1–M4, banner, Exportar (JSON) | `ToggleElemento`, `Exportar`, `MarcarReanalisis` | "¿Por qué esto requiere reanálisis?" |
| 9 | LabLoader.cs | `viewer_unity/Assets/Scripts/` | Carga StreamingAssets, placement, meshes | `LoadPlacement`, `ToWorldModel` | "¿Cómo se coloca el Edificio I en Unity?" |
| 10 | ViewerController.cs | `viewer_unity/Assets/Scripts/` | Raycast, selección, filtros/capas | `RaycastPick`, `ApplyFilters` | "Clic → ¿qué elemento FE?" |

Datos de apoyo: `config/cargas.json` (q_Q=3.0), `config/sismo.json` (a=0.20g), `reports/semana05.md`, `reports/guia_verificacion_manual_unity.md`.

---

## 3. MAPA COMPLETO DEL SISTEMA

```
Geometría/datos  (placement.json, geometry/*.json, config/cargas.json, config/sismo.json)
   │  [H] utf-8 JSON; unidades kN, m; placement es "única fuente de posición relativa"
   ▼
modelo_fe_completo.py  (MarcoFECompleto(Marco), L147; construye con GF.cargar_todos())
   │  [H] carga nodal G (PP+losas+PM.ADIC), Q losa→receptor→nodo (L750-762), EX/EY pseudoestáticos
   ▼
OpenSeesPy  (ops = openseespy.opensees; import L54)
   │  [V] resolver.py: ops.analyze(1) L64; 9 combos = corridas explícitas (correr_combinadas def L1136, bucle de corridas L1176-1182)
   ▼
Casos G / Q / EX / EY + 9 COMB  (localForce/globalForce: 12 comp por elemento)
   │  [H] payloads JSON en modelo_fiel/MODELO_FE_COMPLETO_FUNCIONAL/ (G/Q L1052, sismo L1121, combos L1242)
   ▼
exportar_esfuerzos_funcional_para_viewer.py
   │  [V] read payloads (L354-362) → esfuerzos_FE_EDIFICIO_{I,II}.json (StreamingAssets) + respaldo _ANTERIOR
   ▼
pm_capacidad_demanda_hitob.py
   │  [V] relee esfuerzos_FE + DEMO_RC_{EI,EII} → pm_capacidad_demanda_{I,II}.json
   ▼
JSON StreamingAssets  (lab_data/edificios/{I,II}/results/… + manifest.json + placement.json)
   │  [H] LabLoader.Load() → BuildBuilding("II"/"I") (L36-75); ToWorldModel con BuildingOrigin
   ▼
LabLoader / ViewerController / EsfuerzosController
   │  [H] EFElemento[] (L1220); overlay como tubos FE en coords reales (RebuildOverlay L1359)
   ▼
Unity (selección / deformada / diagramas / P-M)
   │  RaycastPick (L512) → Select → ficha; λ combo (CombinarLibre L695, DespLibre L744); MuParaN (L768)
```

En cada flecha la información viaja como JSON utf-8 con unidades SQL-kN·m; la correspondencia FE↔Unity se fija por `viewer_id`/tag deterministas (QAs lo auditan con números ancla).

---

## 4. Q, EX Y EY (PRIORIDAD MÁXIMA)

### Q — carga viva
- **Archivo**: `config/cargas.json`, `"q_Q.I/II`. **Función/aplicación**: `modelo_fe_completo.py` L750-762.
- **Magnitud**: `q_Q = 3.0 kN/m²` (NCh 1537:2009 Tabla 4 "Escuelas – salas de clases") **[H/S: base normativa declarada]**.
- **Reparto**: losa → área tributaria de soporte (`TB.distribuir_losa`) → `F = frac * q_Q * neto` por receptor → nodo (componente vertical, `cur[2] -= F*w`).
- **Qué decir**: "Q es la sobrecarga de uso uniforme de 3,0 kN/m² que baja por área tributaria; entra al FE como carga nodal descendente en el caso Q, que se resuelve igual que G."

### EX / EY — casos sísmicos
- **Archivo**: `config/sismo.json` (a=0.20g, fracción Q=0.50, g=9.81) + `src/cargas/peso_sismico.py` L207-243.
- **Método** **[H — parametrizado, marcado ejemplo de consigna]**: pseudoestático: `Wi = PPi + 0.5·Qi`, `Fi = a·Wi`, `f_n = Fi · w_n / Wi` por nodo.
- **EX** = componente **+X** (índice 0), **EY** = componente **+Y** (índice 1); misma magnitud, cambia solo la dirección (L207 `idx = 0 if direccion == "X" else 1`). Verificación de exclusividad direccional en `caso_sismico.py` L234-237.
- **Análisis**: son patrones estáticos resueltos con un `ops.analyze(1)`; los resultados salen con `desplazamientos`, `reciónes`, `fuerzas_local/global`.
- **Qué decir**: "Ex y Ey son casos sísmicos pseudo-estáticos horizontales (a=0,20 g de la consigna), uno por dirección; distribuidos en cada nivel proporcional al peso tributario. No son espectro ni viento: es el método del ejemplo del profesor, y los parámetros definitivos quedan parametrizados en config/sismo.json."

### Respuesta preparada: "¿Cuál es la diferencia entre Q, Ex y Ey?"
> "Q es carga vertical de uso (3,0 kN/m², NCh 1537), entra hacia abajo por área tributaria. Ex y Ey son cargas horizontales equivalentes del sismo: cada una combina el peso del edificio (PP + 50%Q) con la aceleración a=0,20g y se aplica en una sola dirección — Ex en X, Ey en Y. G es el peso propio. Los tres se resuelven por separado y luego se combinan con los factores de NCh 3171."

---

## 5. DÓNDE SE DEFINE EL MODELO

| Concepto | Archivo | Función/líneas | Qué mostrar |
|---|---|---|---|
| Nodos/coordenadas | `analisis_estructural/edificio_I/src/analisis/fe/marco.py` | `ops.node` L92; fuentes: `GF.cargar_todos()` en modelo_fe_completo.py L266 | Coordenadas tipo `(u,v,z)` y cotas por nivel |
| Elementos/conectividad | `marco.py` | `ops.element('elasticBeamColumn', …)` L975 | Tags y nodos i/j |
| Materiales/secciones | `marco.py` | `ops.section('Elastic', E,A,Iz,Iy,G,J)` L991-992 | Sección elástica lineal |
| Apoyos | `marco.py` | `ops.fix` base 6DOF L478; rodillo losa L531 | Vínculos |
| Restricciones | `marco.py` | `ops.rigidLink("beam", …)` L721/873 | Conectores excéntricos documentados |
| Diafragma rígido | `marco.py` L1040; `modelo_fe_completo.py` L501/511 | `ops.rigidDiaphragm(3, master, *slaves)` | Losas como diafragma horizontal |
| Masas | (peso sísmico) | `peso_sismico.py` L221-243 | W nodal derivado de PP+0.5Q (sin `ops.mass`: es pseudoestático) |
| Cargas | `modelo_fe_completo.py` | Q losa L750-762; EX/EY L1121 | — |

---

## 6. ESFUERZOS INTERNOS

- **Comando**: `openseespy`: `ops.eleResponse(tag, "localForce")` (L109 resolver.py) y `"globalForce"` (L110).
- **Elemento 3D** → **12 componentes**, orden local:
  `[N_i, Vy_i, Vz_i, T_i, My_i, Mz_i, N_j, Vy_j, Vz_j, T_j, My_j, Mz_j]`.
  Índices clave: **N→0(i)/6(j)**, **Vy→1/7**, **Mz→5/11** (documentado en `exportar_...funcional...py` L82-91 `INDICES`).
- **Local vs global**: `localForce` es sistema local de la barra; `globalForce` global (primeros 6 = nodo i). **Signo**: +N compresión (convención documentada). **Unidades**: kN y kN·m (`exportar` L1069).

Sigue **un MOMENTO real**:

1. **Elemento** → `Ops` `elasticBeamColumn`: solver (`resolver.py:64 ops.analyze(1)`).
2. **Resultado** → `eleResponse(tag,"localForce")` → 12 floats en payload `COMB_*/G_*/Q_*/EX_*/EY_*…json` (`fuerzas_local_por_elemento`).
3. **Python → JSON**: `exportar_esfuerzos_funcional_para_viewer.py` coloca `"fuerzas": {caso: [12]}` por elemento (L1040) y escribe `esfuerzos_FE_EDIFICIO_{I,II}.json`.
4. **JSON → C#**: `EsfuerzosController.CargarEdificio` (L1220) parsea `elementos[]` → `EFElemento` con `Fuerzas[caso]`.
5. **C# → Unity**: `EFElemento.Valor(caso, magnitud, repre)` (L72) → overlay `CrearTuberia` (L1428) y diagramas `DrawDiagrams` (L2676).

**Respuesta "¿De dónde salió este momento que muestro?"**: elegir elemento → ficha muestra `My_j` de la combinación activa; el valor viene del payload `COMB_U2_EX_POS_...json` (`fuerzas_local_por_elemento` → índice 4/5/10/11) → `esfuerzos_FE_EDIFICIO_I.json` → `EFElemento.Valor()`. Ejemplo verificable ancla: EI col 1A1 tag3 `U2_EX_POS` comp0 = 730.72 kN (en LabViewerEditor.cs L459).
```
python -X utf8 -m src.unity_esfuerzos.exportar_esfuerzos_funcional_para_viewer
```

---

## 7. DEFORMADA

- **`ops.nodeDisp(tag, 1..6)`** (`resolver.py` L21) → 6 DOF por nodo → payload `desplazamientos` (dict nodo→[ux,uy,uz,rx,ry,rz]).
- **JSON**: `deformada:{nodos, desplazamientos_por_caso}` en `esfuerzos_FE_EDIFICIO_{I,II}.json` (L1075-1085) → C# `_despCaso` (EsfuerzosController L1063-1087).
- **Combinación λ**: `DespLibre(b)` (L744-764) `Σ λ·desp_base` con los 4 casos base; `DespActivo(b, caso)` (L1612) devuelve el caso activo (o la libre).
- **Escala gráfica**: `Amplificacion = 60f` default (L278), slider 1–300 en GUI (L2193-2198); se aplica en `RebuildDeformada` (`A = Amplificacion`, L1660).

### SI EL PROFESOR PIDE "MUÉSTRAME CÓMO CALCULAS LA DEFORMADA"
1. Abrir `EsfuerzosController.cs`, Ctrl+F `RebuildDeformada`.
2. Mostrar L1650-1692: lee `DespActivo(Edificio, Caso)`, multiplica por `Amplificacion`, reposiciona tuberías/nodos.
3. Abrir `DespLibre` (L744): la suma lineal `Σ λ·desp_base` (mismo supuesto lineal que los esfuerzos).
4. Mostrar la fuente: payload `desplazamientos` (esfuerzos_FE JSON) o el solver `resolver.py:21 nodeDisp`.

---

## 8. SUPERPOSICIÓN

`R = Σ λᵢ·Rᵢ` con los 4 casos base {G, Q, EX, EY}.

- **Esfuerzos**: `CombinarLibre(EFElemento)` EsfuerzosController L695-710 (`r[k] += f[k]*l`, 12 comp).
- **Deformada**: `DespLibre(b)` L744-764.
- **Sliders**: UI panel esfuerzos L2020-2030 (`GUILayout.Label("C = "+FormulaLibre())` L2020, `GUILayout.HorizontalSlider(Lam[i],0,2)` L2025, `SetLam` L2030); `SetLam` L800-814; `FormulaLibre()` L869-878 → `C = λG·G + λQ·Q + λEX·EX + λEY·EY` con vector `Lam[]{1,0,0,0}` inicial (L815).
- **Datos base**: los 4 casos exportados (13 en total: + 9 combos) cargados en `_despCaso`/elementos.
- **Actualización en vivo**: `SetLam` refresca colores (`ActualizarColoresLibre` L820) y deformada (`RebuildDeformada`) SIN recrear geometría; presets `U1_GQ`, `U2_EX_*`, etc. en `CoefDePreset` L852-867.

Qué abrir primero: `EsfuerzosController.cs` → L695 (`CombinarLibre`). Después: `LabModificaciones.cs` → L301 (`C = FormulaLibre()`).

**Respuesta corta "¿Por qué mover estos sliders no requiere ejecutar OpenSees nuevamente?"**
> "Porque el modelo es lineal y los casos base ya están resueltos una vez. Un caso cualquiera es una combinación lineal de las respuestas base; mover un slider solo recalcula esa combinación (R=Σλ·Rᵢ) en el viewer. No cambia rigideces ni carga última; si el profesor cambia el modelo, ahí sí se vuelve a resolver. La evidencia numérica es `evidencias/evidencia_1_linealidad.txt`: las 9 combinaciones NCh3171 reproducidas por superposición con error máx. 6,2e-6."

---

## 9. M1 — intensidad de carga (demo perfecta)

- **Qué modifica**: los λ de intensidad λG, λQ, λEX, λEY.
- **Por qué NO reanaliza**: lineal -> superposición exacta (supuesto declarado). `SetSuperposicion`/`SetLam` (L786/800) recalculan en vivo.
- **Sliders**: panel esfuerzos L2017-2025; toggle en ViewerController L741-743; también en Lab panel L301-311.
- **Qué cambia**: colores del overlay, diagrama del elemento, deformada, y ficha (`FormulaLibre`).
- **Evidencia**: `evidence/evidencia_1_linealidad.txt` **[V]**:
  - 9 combos NCh3171 vs superposición: `max|diff| global = 6.2e-06` (comps 4536 por combo).
  - Deformada por nodo: `max|diff| = 2.0e-08` (comps 14310).
  - Texto: "SUPERPOSICION LINEAL EXACTA → los sliders reproducen las combinaciones NCh3171".
- Dónde encontrarla: `evidence/evidencia_1_linealidad.txt` (abrir en la defensa).

---

## 10. M2 — elemento ON/OFF

Flujo real:
```
clic → ViewerController.RaycastPick (L512) → Select (L521)
   → LabModificaciones.ToggleElemento (L99-127): go.SetActive(false)  [visual: se oculta]
     + _esf.OcultarFE(viewerId, true) (EsfuerzosController L899-905)  [también se oculta el tubo FE]
     + MarcarReanalisis (L155-160): RequiereReanalisis=true, banner rojo
   → Exportar (L201-236): modelo_modificado_lab.json con el registro REANALISIS + reanalisis_reproducible
   → reanálisis manual: modelo_fe_completo.py --g --sismo --combinadas  (no está automatizado)
```
- **Modificación visual actual**: el elemento se oculta en la escena (SetActive false + tubo FE oculto).
- **Modificación estructural solicitada**: quitar ese elemento del modelo = cambiar K global → pendiente.
- **Pendiente hasta reanálisis**: los resultados visibles siguen siendo del modelo ORIGINAL → por eso el banner **[H/consistente]**.

**Respuesta "¿Por qué eliminar un elemento requiere reanalizar?"**
> "Porque quitar un elemento cambia la matriz de rigidez del sistema y el reparto de fuerzas en TODO el marco. Ocultarlo visualmente solo lo saca de la escena; eso no equivale a haber resuelto el nuevo sistema. Por eso el banner dice explícitamente que los resultados aún corresponden al modelo original, y el comando de reanálisis queda registrado y exportable."

---

## 11. M3 — cambio de sección

- **Dónde se introduce w×h**: `DrawPanel` texto `_wTxt/_hTxt` (L325-332) → `AplicarSeccion(sel, w, h)` (L130-146).
- **Dónde queda registrado**: `Registro` con `RequiereReanalisis=true`; se fija `r.SectionW/SectionH`.
- **Qué propiedad estructural debería cambiar**: A, I, EI → K del elemento.
- **Por qué cambia K y requiere reanálisis**: la rigidez entra en `ops.section('Elastic', E,A,Iz,Iy,G,J)` (marco.py L991) → hay que re-ensamblar y resolver.
- **[L] Limitación (NO ocultar)**: la auditoría previa encontró que la modificación **no está cableada a la geometría visible**: `AplicarSeccion` solo parsea y registra; **no reconstruye la malla** ni cambia el dibujo del elemento. Es UI/registro → reanálisis.
- Frase para el profesor: "M3 captura el cambio w×h, lo registra como que requiere reanálisis y lo exporta. Hoy el cambio visible de sección es un registro de intención (el elemento no se re-dibuja con la nueva sección); el paso estructural está en reanálisis, no simulamos haberlo resuelto."

---

## 12. M4 — área tributaria

- **Slider**: `DrawPanel` L334-338 (`GUILayout.HorizontalSlider(k,0,2)` + `factor x N`); `SetTribFactor` (por elemento) L77, `SetTribFactorGlobal` (global) L89-96 (clamp 0–2, `MarcarReanalisis`).
- **Dato**: factor multiplica las áreas/cargas tributarias (HUD en ficha y en `CargaMovilController.OnGUI` L182-185 aplica `TribFactor`).
- **Carga/reparto**: si cambia el reparto losa→receptor→nodo → repartos y K del lado de carga cambian en general → **reanálisis**.
- **[L] Limitación**: al igual que M3, hoy es registro/HUD; el cambio estructural queda como intención hasta reanálisis.

---

## 13. REANÁLISIS REAL (secuencia exacta)

```
1. cd "C:\Users\javie\...\P1-Grupo-8-semana05"
2. .\.venv\Scripts\Activate.ps1
3. ..\.venv\Scripts\python.exe -X utf8 -c "import openseespy.opensees as ops; print('OpenSeesPy OK')"
4. cd entrega_03_cargas_sismo_capacidad
5. ..\.venv\Scripts\python.exe -X utf8 -m src.modelo_fiel.modelo_fe_completo --g --sismo --combinadas
6. ..\.venv\Scripts\python.exe -X utf8 -m src.unity_esfuerzos.exportar_esfuerzos_funcional_para_viewer
7. ..\.venv\Scripts\python.exe -X utf8 -m src.unity_esfuerzos.pm_capacidad_demanda_hitob
8. JSON que cambian (StreamingAssets): esfuerzos_FE_EDIFICIO_{I,II}.json, pm_capacidad_demanda_{I,II}.json
   y en modelo_fiel/MODELO_FE_COMPLETO_FUNCIONAL/: G_*, Q_*, EX_*, EY_*, COMB_*.
9. Volver a Unity: refresh (el editor relee StreamingAssets al re-paquetizar/rejugar).
```
[V] Todos estos comandos ya corrieron hoy (solver rc=0; exportadores dry-run 22/22).

---

## 14. P-M / DEMANDA-CAPACIDAD

Flujo:
```
elemento seleccionado → N = máx axial (indices 0/6) → P (concurrente _concurrente L99)
→ M = máx |M| (indices 4,5,10,11) → MuParaN (interpola curva; py `_mu_interp` L88-96 / cs `MuParaN` L771)
→ D/C = M / Mu → Unity panel (DibujarPmBloque L1790, curva ParseCurva L1176)
```
- **Curva P-M (py)**: `capacity_rc/edificios.py` (0.70×0.70, 12#25, L50-62; `diagrama_pm` N/M L187-188) → `results/capacidad_rc/DEMO_RC_{EI,EII}.json`.
- **JSON P-M (viewer)**: `pm_capacidad_demanda_{I,II}.json`; ejemplo I: columna crítica tag18 `U4_EY_NEG` (0.9G−1.4EY) P_u=27.37, M_dem=1359.81, M_u_N=895.39, **D_C=1.52**; II: muro `U3_EY_NEG` P_u=550.44, M_dem=8661.17, M_u_N=7412.85, **D_C=1.17**.
- **Evidencia dinámico**: `evidence/evidencia_2_pm.txt` **[V]**: 115 elementos, `max|diff| P=1.4e-6, M=1.6e-6, D/C=4.9e-5` → "D/C DINAMICO == pm_capacidad_demanda".
- **P-M del CASO ACTIVO (S05, corregido)**: `DibujarPmBloque` recalculaba el punto P-M solo en LIBRE; ahora también recalcula desde el vector del **caso activo seleccionado** (base o combinación NCh3171) con la misma convención P/M → al cambiar combinación, el punto, la M_u(P) y el D/C acompañan al caso elegido (envolvente conserva la fila crítica del paquete). Verificado al vuelo: **147/147 filas** (`por_elemento` I+II) y el muro EII reproducen el paquete con `max|diff| < 1e-3`. Además el panel ahora muestra la etiqueta del elemento y un rectángulo proporcional **b×h** con barras/As de la hipótesis DEMO (rúbrica 4.2).

**Aclaración de defensa**: la curva es **DEMO**: la armadura del muro está BLOQUEADA y se usa una hipótesis de demostración (dos capas ~3.2 cm²/m, 16mm@0.20; `NOTA_MURO_ARMADURA` pm_capacidad_demanda_hitob.py L55-59), y para columnas se usa una sección 0.70×0.70 con 12#25 (`DEMOSTRACION_ARBITRARIA` en capacity_rc/seccion.py L14). **[S/L]**

**Respuesta "¿Entonces esta capacidad es definitiva?"**
> "No. La armadura es una hipótesis de demostración (el dato real está bloqueado como 'pendiente' en config/parametros_pendientes.json). La curva P-M y el D/C prueban el MÉTODO, no un diseño definitivo: si el profesor entrega el armado real o la aceleración definitiva, se reparametriza sin cambiar el pipeline."

---

## 15. SELECCIÓN EN UNITY

```
clic (no sobre UI; InteraccionUI.PointerSobreUI decide)
→ ViewerController.RaycastPick (L512): Physics.Raycast desde ScreenPointToRay
→ collider del elemento viewer → ElementRef (LabModel) → tag/viewer_id
→ EsfuerzosController.ProcesarClic (L457/463) / SeleccionarPorViewer (L512)
   con correspondencia viewer_id ↔ ET (estados 1A1 / CONTENIDO / SIN_CORRESPONDENCIA)
→ Select (L521); ficha DrawInspectionPanel / DrawFicha (L2372) con id · tipo · nivel · esfuerzos · tributaria
```
- ID del FE: `viewer_id` (p.ej. `COL_EI_CP1S_C_E_0.71_16.16`), match QA en `LabViewerEditor.ProbarClicCorrespondencia`.

---

## 16. CAPAS / FILTROS

- `ApplyFilters` (ViewerController L122-147): recorre bldg→nivel→tipo (`BuildingOn/LevelOn/TypeOn` L118-120) haciendo `SetActive`; luego `ApplyMarkerVisibility` y `_esf.OnVisualFiltersChanged()` (EsfuerzosController L1340 → `ApplyOverlayVisibility`).
- Filtros overlay: `SetUI(caso, magnitud, repre, escala)` y estado `SIN_CORRESPONDENCIA_VIEWER` (L2324-2334); modos "Mapeados" / "Todos los FE".
- Demo: cambiar normativa/nivel/tipo → solo elementos FE correspondientes recalculan kolor.

---

## 17. ÁREAS TRIBUTARIAS

- **JSON**: `viewer_unity/Assets/StreamingAssets/lab_data/edificios/I/tributary/` (`por_viga.json`, `regiones_tributarias.json`, 63.502 celdas) — Edificio I; **II sin carpeta tributary** **[L]**.
- **Estructura**: `por_nivel` → `receptores` (166) → `carga_kN` / `carga_total_kN`; generadores: `src/cargas/peso_sismico.py`, `src/comun/geometria_tributaria.py`, `tools/export_lab_data.py`.
- **C#**: `LabLoader.LoadResultsAndTributary` (L126-152) → `TribRegion{CargaKN,...}` (LabModel L56-63); `LoadTributaryRegions` (L157-205); visual: `TribRegionMesh` (L700) + `ViewerController.BuildTributaryMarker` (superficie + fleja `carga_kN`, `BuildCargaMarker` L468-495).
- **Lógica**: `área/panel → fracción del soporte más cercano (Voronoi sobre malla 0.25 m) → receptor con carga_kN → nodo`. Ruotalidad: en solver `modelo_fe_completo.py` L750-762.
- **Conservación [V]**: Σ `carga_kN` = 25.227,38 kN; Σ `carga_total_kN` = 25.227,34 kN (Δ≈0,04); QA `CheckData` de `LabViewerEditor.cs` (L140-158) reporta `cargaTotalG ≈ 25.227,81` kN con 166 receptores.

---

## 18. SQ4 — CARGA MÓVIL (prototipo click)

- **Archivo**: `viewer_unity/Assets/Scripts/CargaMovilController.cs` (194 líneas).
- **Comportamiento real [H/L]**: NO es seguimiento continuo; es **selección por clic sobre celdas** con resaltado magenta: `BuscarBajoCursor` (L64-107): raycast → local = punto − BuildingOrigin("I") → filtro cota ±0.6 m → `PuntoEnPoligono` (L155-167) sobre `regiones_tributarias.json`; solo Edificio I (`CargarReceptores` L49-62).
- **Panel/celdas/receptores**: celda (polígono, malla 0.25 m) → receptor tributario (`TribRegion`) → carga repartida.
- **Conservación**: las celdas son partición disjunta de la losa; `sum(CargaKN receptores)` = misma carga (25.227,38 kN) sin fugas/soelapes (`reports/semana05.md` L339-345).

**Respuesta "¿La carga se conserva?"**
> "Sí. Las celdas son una partición de la losa: cada uno produce una carga proporcional a su área y la suma de los receptores se mantiene en ≈25.227 kN (Σ celdas 25.227,38; Σ receptores 25.227,34; el QA CheckData del estático reporta 25.227,81). No hay dobles conteos."

---

## 19. UNITY: MAPA DE OBJETOS Y SCRIPTS

| Hierarchy / GameObject | Component | Script | Función |
|---|---|---|---|
| Main Camera (16619364) | CameraController (16619365) + AudioListener | LabViewer.CameraController | Órbita/zoom sobre LabTarget (Yaw 45, Pitch 25) |
| Sun (75092570) | Light directional intensity 1.1 | — | Iluminación |
| Contenedor escena (1734279528) | ViewerController + LabLoader + EsfuerzosController | LabViewer.* | Consumo JSON, selección, filtros, overlay |
| LabTarget (2032357102/3) | Transform en 0,0,0 | — | Punto de mira de cámara |
| GOs dinámicos por elemento | MeshRenderer+Collider | LabLoader.BuildBeams/BuildWalls (L414/623), AddCollider (L805) | Geometría y clic |
| Tubos FE overlay | MeshRenderer + EFPicker | EsfuerzosController.RebuildOverlay (L1359)/CrearTuberia (L1428) | Overlay FE exacto |
| Receptores tributarios | Mesh | LabLoader.TribRegionMesh (L700) | Áreas tributarias |

---

## 20. JSON MÁS IMPORTANTES

| JSON | Quién lo genera | Quién lo lee | Campos clave |
|---|---|---|---|
| `esfuerzos_FE_EDIFICIO_{I,II}.json` | `exportar_esfuerzos_funcional_para_viewer.py` (L1112-1123) | `EsfuerzosController.CargarEdificio` (L1220) | `elementos[] {tag,tipo,nivel,fuerzas:{caso:[12]},correspondencia}`, `casos`, `deformada`, `unidades` |
| `pm_capacidad_demanda_{I,II}.json` | `pm_capacidad_demanda_hitob.py` (L227-237) | `EsfuerzosController` (P-M), `DibujarPmBloque` L1790 | `columna_critica`, `por_elemento`, `muro` con `capacidad_pm {N,M}`, `dc`, `seccion {b_m,h_m,n_barras}` |
| `manifest.json` | `tools/export_lab_data.py` | LabLoader/QA | `ejecucion_fuente_Edificio_I`, 13 casos FE, unidades |
| `placement.json` | export_lab_data | LabLoader.LoadPlacement (L78-124) | EI en `[28.400227,0,0]`; junta `JD_EI_EII_10CM`; cotas por nivel |
| `I/tributary/regiones_tributarias.json` | export_lab_data / peso_sismico | LabLayer + CargaMovilController | `por_nivel→receptores→carga_kN`, 63.502 celdas |
| `modelo_modificado_lab.json` | LabModificaciones.Exportar (L201-236) | (reanálisis manual) | `registro[], requires_reanalisis, reanalisis_reproducible` |

Nota trampa: `manifest.json` describe al Edificio II como "geometria_adaptada_sin_solucion_FE"; pero II SÍ tiene esfuerzos FE (13 casos) y P-M desde después de la semana 2 — el manifest registra la génesis del paquete. Si el profesor lo nota, aclarar con `esfuerzos_FE_EDIFICIO_II.json` (1,5 MB) y `pm_capacidad_demanda_II.json`.

---

## 21. DEMOSTRACIÓN IDEAL DE 5 MINUTOS

| Tiempo | Acción | Qué muestra | Riesgo |
|---|---|---|---|
| 0:00–0:30 | Abrir Unity + Play; cargar Main.unity | Pipeline de carga OK; escena completa I y II | bajo |
| 0:30–1:00 | **Seleccionar** una columna (clic) | Ficha: id/tipo/nivel/tributaria; correspondencia FE | bajo |
| 1:00–1:30 | **Capas/filtros**: mostrar solo un nivel o tipo | ApplyFilters → overlay FE filtrado | bajo |
| 1:30–2:00 | **Overlay esfuerzos** + cambiar combinación (◀▶) | Tuberías FE coloreadas; valores por magnitud | bajo |
| 2:00–2:45 | **Sliders λ** (C=…): mover G/Q/EX/EY | Superposición en vivo, sin reanálisis; `FormulaLibre` | bajo |
| 2:45–3:15 | **Deformada amplificada** (slider escala) | `RebuildDeformada` (Amplificacion 60) | bajo |
| 3:15–3:45 | **P-M**: seleccionar elemento, ver curva y D/C | MuParaN interpolado; nota DEMO armadura | medio |
| 3:45–4:15 | **M1**: preset U1_GQ y λ manual | Lineal exacto; evidencia 1 (max diff 6e-6) | bajo |
| 4:15–4:50 | **M2**: desactivar elemento → banner rojo → Reiniciar | Criterio: requiere reanálisis; comando reproducible | medio |
| 4:50–5:00 | Cierre: solver OpenSeesPy + exportadores | Comandos en PS; rc=0 | medio |

No centrar en M3/M4 (riesgo de limitación UI). Si se pregunta, usar la *frase de riesgo* de §11/§12.

---

## 22. 30 PREGUNTAS PROBABLES

| Pregunta | Respuesta corta | Archivo | Ctrl+F |
|---|---|---|---|
| ¿Qué es Q? | Sobrecarga 3,0 kN/m² (NCh1537) baja tributaria | config/cargas.json | `q_Q_kN_m2` |
| ¿Qué es Ex/Ey? | Sismo pseudoestático a=0,20g, Ex=X/Ey=Y | config/sismo.json / peso_sismico.py L207-243 | `coeficiente_sismico_a` / `idx = 0 if` |
| ¿OpenSeesPy? | Librería Python oficial; usa el kernel OpenSees; import L54 | modelo_fe_completo.py | `import openseespy` |
| ¿Nodos? | ops.node L92 marco.py; coords GF.cargar_todos L266 | marco.py | `ops.node` |
| ¿Elementos? | elasticBeamColumn L975; tags deterministas | marco.py | `ops.element` |
| ¿Apoyos? | ops.fix base 6DOF L478; rodillos losa L531 | marco.py | `ops.fix` |
| ¿Diafragma? | ops.rigidDiaphragm(3, master, slaves) L1040/511 | marco.py / modelo_fe_completo.py | `rigidDiaphragm` |
| ¿Cargas? | G nodal + Q losa (L750-762) + EX/EY | modelo_fe_completo.py | `distribuir_losa` |
| ¿Áreas tributarias? | Voronoi de malla 0.25 → receptores (166) 25.227 kN | tributaria.py / regiones_tributarias.json | `distribuir_losa` / `carga_kN` |
| ¿Superposición? | R=Σλ·Rᵢ; no reanaliza (lineal) | EsfuerzosController.cs | `CombinarLibre` |
| ¿Deformada? | nodeDisp → DespLibre→RebuildDeformada (×60) | EsfuerzosController.cs | `DespLibre`, `RebuildDeformada` |
| ¿Axial? | N en índices 0/6 localForce (kN, +compresión) | exportar_...funcional | `INDICES` |
| ¿Corte? | Vy/Vz índices 1/2 y 7/8 | exportar.../EsfuerzosController | `INDICES` |
| ¿Momento? | My/Mz índices 4/5 y 10/11; Mz_j=magnitud 5 +6 | EsfuerzosController.cs | `Valor` |
| ¿P-M? | curva Ei 12#25; muro hipótesis; MuParaN interp | pm_hitob.py / capacity_rc/edificios.py | `_mu_interp` / `MuParaN` |
| ¿D/C? | M/Mu; ej. I 1.52 (U4_EY_NEG), II 1.17 (U3_EY_NEG) | pm_capacidad_demanda_{I,II}.json | `D_C` |
| ¿M1? | cambia λ; sin reanálisis por linealidad | EsfuerzosController.cs | `SetLam` |
| ¿M2? | oculta elemento + requiere reanálisis + comando | LabModificaciones.cs | `ToggleElemento` |
| ¿M3? | registra w×h y reanálisis; NO cambia malla [L] | LabModificaciones.cs | `AplicarSeccion` |
| ¿M4? | factor tributario slider; reanálisis; HUD | LabModificaciones.cs | `SetTribFactorGlobal` |
| ¿Reanálisis? | re-correr solver + export + pm | §13 comands | — |
| ¿JSON→Unity? | exportar_esfuerzos → StreamingAssets → CargarEdificio | exportar_...py / EsfuerzosController.cs | `CargarEdificio` |
| ¿Unity solver? | NO; solo visualizador de resultados pre-resueltos | LabModificaciones doc L24-25 | `SOLO-lectura` |
| ¿Sliders ejecutan OpenSees? | No; combinan respuestas base ya resueltas | EsfuerzosController.cs | `CombinarLibre` |
| ¿Conservación de carga? | 25.227,38/25.227,34/25.227,81 kN | LabViewerEditor.cs | `cargaTotalG` |
| ¿Cómo se coloca EI? | placement.json → [28.400227,0,0] | LabLoader.cs | `LoadPlacement` |
| ¿Envolvente? | max |valor| por comp entre 9 combos | EsfuerzosController.cs | `EnvValores`, `_envolvente` |
| ¿Estado 1A1/CONTENIDO/SIN_CORRESPONDENCIA? | correspondencia FE↔viewer | EsfuerzosController.cs | `EstadoCorr` |
| ¿Tests? | 108: 88 OK, 20 ERROR (insumo regenerable superposición legacy) | tests/unity_esfuerzos/* | — |
| ¿Reanálisis reproducible? | 3 comandos en PS (§13) | reports/semana05.md §8.2 | `exportar_esfuerzos_funcional` |

---

## 23. PREGUNTAS TRAMPA (frases exactas)

1. **"¿OpenSeesPy es un programa distinto?"** → "No: es la librería oficial de OpenSees para Python; arma el modelo y el kernel de OpenSees lo resuelve (`import openseespy.opensees as ops`). No usamos el binario tcl/OpenSees.exe."
2. **"¿Esta capacidad es definitiva?"** → "No: es DEMO. La armadura real del muro está BLOQUEADA (parametros_pendientes.json) y usamos hipótesis de demostración (2 capas ~3,2 cm²/m, 16mm@0,20). El D/C valida el método, no un diseño."
3. **"Si ocultaste el elemento, ¿ya resolviste el sistema sin él?"** → "No: ocultar es visual; el sistema resuelto sigue siendo el original hasta que corra el reanálisis. Por eso el banner." (M2)
4. **"¿M3 cambia el dibujo?"** → "No en esta semana: registra w×h, marca reanálisis y exporta; la malla visible no se reconstruye. Es una limitación declarada." (M3)
5. **"¿M4 cambia el reparto ya mismo?"** → "Solo factor HUD/reanálisis; el reparto estructural nuevo requiere reanálisis." (M4)
6. **"¿SQ4 es carga en movimiento?"** → "Es un prototipo de selección por clic sobre celdas (resaltado magenta); no es seguimiento continuo. La conservación se cumple: la suma se mantiene en ~25.227 kN." (SQ4)
7. **"¿Unity resuelve el modelo?"** → "No: Unity es el visualizador 3D de resultados pre-resueltos; el solver es OpenSeesPy." 
8. **"¿Mover sliders ejecuta OpenSees?"** → "No: combina linealmente respuestas base resueltas una vez. Evidencia: error máx 6,2e-6 vs las 9 combinaciones."
9. **"¿Por qué el manifest de II dice 'sin solución FE'?"** → "Es la génesis del paquete (semana 2). Las soluciones FE y P-M de II llegaron después (esfuerzos_FE_EDIFICIO_II.json, 13 casos)."
10. **"¿Los 20 tests en error?"** → "88 pasan, 0 fallan; los 20 ERROR son FileNotFound de un archivo de verificación regenerable del exportador legacy; el flujo S05 no lo usa."
11. **"¿La deformada es exagerada?"** → "Sí: está amplificada ×60 (slider 1–300) para que se vea; los desplazamientos del FE son en metros reales en el JSON."
12. **"¿Geometría I colocada en 28,4 m?"** → "Sí: placement.json es la fuente única; EI en [28.400227,0,0] con junta JD_EI_EII_10CM documentada."
13. **"¿Envolvente?"** → "Por componente, toma el caso con mayor |valor| entre las 9 combinaciones NCh3171 (guardando signo y caso); se resuelve aparte porque conserva NaN por componente."
14. **"¿Peso sísmico usa PP pendiente?"** → "No: el PP pendiente se reporta como nota, pero se excluye del peso sísmico (config/sismo.json 'PP_pendiente_visible': true)."
15. **"¿El modelo es definitivo?"** → "La geometría física del nivel P4 está aprobada según la cabecera del solver, pero persisten postes hipotéticos de la torre y diagonales PENDIENTE_TORRE; régimen HIPOTESIS_DE_ANALISIS documentado en la cabecera del solver; el perfil es MODELO_FE_COMPLETO_FUNCIONAL, no declarado definitivo."

---

## 24. RESPUESTAS DE 15 SEGUNDOS (memorizar)

- **Q**: "Sobrecarga de uso uniforme, 3,0 kN/m² (NCh 1537)."
- **Ex**: "Sismo horizontal pseudo-estático en +X, a=0,20 g, repartido por peso tributario."
- **Ey**: "Igual que Ex pero en +Y (cambia solo el índice de componente)."
- **OpenSeesPy**: "Librería oficial de OpenSees para Python; resuelve con el kernel de OpenSees."
- **Área tributaria**: "Voronoi de malla 0,25 m: cada panel va al soporte más cercano y su carga se conserva."
- **Superposición**: "R=Σλ·Rᵢ sobre casos base resueltos; lineal → sin reanálisis."
- **Deformada**: "Desplazamientos del FE (en m) combinados por λ y amplificados ×60 para visualizar."
- **Esfuerzo interno**: "Vector local de 12 componentes por elemento: N,V,T,M en i y j, kN y kN·m."
- **P-M**: "Curva de interacción axial–momento; DEMO con armadura hipótesis."
- **D/C**: "Mdem / M_u(P); ej. I=1,52 y II=1,17 en la demanda crítica."
- **M1**: "Intensidad de carga vía λ; no requiere reanálisis por linealidad."
- **M2**: "Elemento ON/OFF; oculta visualmente y exige reanálisis (comando registrado)."
- **Reanálisis**: "3 comandos: solver OpenSeesPy → exportar esfuerzos → regenerar P-M."

---

## 25. CHULETA FINAL (cerrar y dejar abierta)

```
TEMA            → ARCHIVO                          → CTRL+F                    → QUÉ DECIR
Q               → config/cargas.json               → q_Q_kN_m2                 → 3,0 kN/m² NCh1537, baja tributaria
EX/EY           → config/sismo.json; sismo.py      → coeficiente_sismico_a      → a=0,20g; Ex=X, Ey=Y; pseudoestático
OpenSeesPy      → modelo_fe_completo.py            → import openseespy          → kernel de OpenSees, librería oficial Python
MODELO          → marco.py                         → rigidDiaphragm / ops.fix   → nodos/elems/secciones/apoyos/diafragma
COMBINACIONES   → combinaciones_nch3171.py         → U1_GQ                      → 1.2G+1.6Q, 1.2G+Q+1.4EX, 0.9G±1.4EX/EY (9)
RESULTADOS      → resolver.py                      → eleResponse                 → localForce 12 comp; N=0/6, V=1/7, M=5/11
A UNITY         → exportar_esfuerzos_funcional...  → def main                    → 13 casos → esfuerzos_FE_EDIFICIO_{I,II}.json
SUPERPOSICIÓN   → EsfuerzosController.cs           → CombinarLibre / SetLam     → R=ΣλR; sliders NO reanalizan
DEFORMADA       → EsfuerzosController.cs           → RebuildDeformada / DespLibre → nodeDisp combinado ×60
P-M / D/C       → pm_capacidad_demanda_hitob.py    → _mu_interp / MuParaN        → Mu(P) interp; D/C ej. 1.52/1.17; DEMO armadura
M1              → EsfuerzosController.cs           → SetSuperposicion           → lineal exacto; evidencia 6.2e-6
M2              → LabModificaciones.cs             → ToggleElemento             → oculta + REANALISIS + comando
M3              → LabModificaciones.cs             → AplicarSeccion             → registra w×h; NO cambia malla (L)
M4              → LabModificaciones.cs             → SetTribFactorGlobal        → factor tributario; reanálisis (L)
REANÁLISIS      → PowerShell §13                   → 3 comandos                 → solver + export + pm; rc=0
SELECCIÓN       → ViewerController.cs              → RaycastPick                 → clic → ElementRef → viewer_id → ficha
CAPAS           → ViewerController.cs              → ApplyFilters                → bldg/nivel/tipo + markers + overlay
RIBUTARIA/CONS  → regiones_tributarias.json        → carga_kN                    → Σ 25.227 kN (166 receptores, 63.502 celdas)
SQ4             → CargaMovilController.cs          → BuscarBajoCursor           → click/prototipo, conserva carga
JSON→Unity      → LabLoader.cs                     → LoadPlacement/LoadResults  → placement [28.400227,0,0]; CargarEdificio
UNITY=VIZ       → LabModificaciones.cs doc         → SOLO-lectura                → no resuelve nada; muestra pre-resuelto
TESTS           → tests/ (Pwsh)                    → discover -s tests            → 108/88 OK/20 ERROR regenerables [L]