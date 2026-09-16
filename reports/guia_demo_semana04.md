# Guía demo / defensa — Semana 4 (3 integrantes)

Ensayo el **martes**; comprobación y publicación el **miércoles 16/09 antes de las 10:30**.
Demo en vivo en Unity. Regla transversal: **nunca inventar números**; si falta una
fuente, mostrar el bloqueo concreto (`SIN_RESULTADO`/`PENDIENTE`/hipótesis declarada).

## Estado congelado (defensivo)

- Topología Semana 4 **congelada** (`CONGELAMIENTO_TOPOLOGIA_SEMANA4.json` con sha256).
- **9 combinaciones NCh3171 calculadas** sobre esa topología (EI+EII, equilibrio 9/9;
  `combos_estado=CALCULADA`), perfil único con respaldo automático. Ya NO se dice
  "combos pendientes de regenerar".

## Flujo sugerido (5-7 min por integrante dentro de la demo coordinada)

### A. Cierre de islas y topología (líder ejecutor)
1. `python -X utf8 -m tests.islas.test_cierre_islas` → 5 OK + 4 subtests OK.
2. 1 kN → ΣRz base = 1,0 kN; apoyos artificiales = 0 (Enlace: `INFORME_COBERTURA_FISICA.md` §0.8).
3. Mostrar snapshot de congelamiento con hashes de EI/EII.

### B. Cobertura física y validación independiente (líder cobertura)
1. Tabla por edificio/nivel/familia (`reports/semana04.md` §2): EI 252/306 (82,4%), EII 227/256 (88,7%).
2. Métrica = **objetos físicos del viewer con resultados válidos**, NO segmentos FE.
3. Losas: 3672,07 m² analizados vs 4109,47 físicos → 437,40 m² **pendiente** (parcial, separada).
4. **Validación independiente del diagrama** (`validar_diagramas_hitob.py`, sin reutilizar el
   exportador): EI 378/378 OK, EII 253/253 OK, peor Δ=6e-6 kN. Mostrar la fila de la muestra
   jurado en `validacion_diagramas_hitob.md` (viga + columna + muro por edificio).
5. Intervalo físico sub-tramo: `V_EI_CP2_x1749_16.45-19.97` → **rotulo FE_COMPLETO**
   (contenida en FE tag 317, diagrama lineal, residuos nulos) — `reconciliacion_intervalo_x1749.json`.

### C. Unity: selección, ficha, deformada (líder Unity)
1. Ficha por clic: viewer_id + elementTag + nodos i/j + sección + **material (fc/ref/nota)** +
   N/Vy/Vz/T/My/Mz + unidades + caso activo + **reacción G base** (solo columnas) +
   **desplazamientos nodo i/j del caso** (sin amplificar).
2. Seleccionar columnas/vigas/muros en ≥4 niveles distintos (validar distribución; min. 2
   objetos/nivel para la ronda).
3. Toggle "Deformada amplificada" + slider: valores REALES del caso activo (o envolvente),
   escalados solo visualmente; ejemplo que cambia de signo entre U2_EX y U3_EY.
4. ≥1 diagrama de momento y ≥1 axial/corte dibujados en elementos clave.

### D. Capacidad: P–M y D/C (líder capacidad) — verificado 2026-09-15
1. Columna crítica por edificio con **P y M del mismo caso concurrente** (U1..U4,
   `por_elemento` del `pm_capacidad_demanda_{I,II}.json` real): EI tag 18
   `COL_EI_CP1S_C_E_0.73_1.35` (U4_EY_NEG, P=27,4 kN → en EI, arriba;
   véase lista completa abajo) y EII `EII_CP3` (tag 10, U2_EX_POS, **D/C=2,0429**).
   Datos verificados en JSON (claves P_u_kN, N_i/N_j_kN, M_demanda_kN_m,
   M_u_N_kN_m, modo_mu, D_C):
   - **EI** `por_elemento` = **115 filas** (p. ej. tag 3: U4_EX_POS,
     `0.9*G + 1.4*EX`, P=311,06 kN, M=1409,67 kN·m, M_u=967,06, **D/C=1,4577**).
   - **EII** `por_elemento` = **32 filas** + **muro_demostrado**:
     `EII_CP1S_M_001` con demanda **concurrente** (caso U3_EY_NEG,
     viewer_id, P=550,44 kN, M=8661,17 kN·m).
2. Muro: `EII_CP1S_M_001` (tag 76, U3_EY_NEG, **D/C=1,1684**) con
   **armadura HIPÓTESIS declarada** (`EVALUACION_HIPOTESIS_BLOQUEADA_ARMADURA`):
   es una evaluación de hipótesis, NO vale como comprobación de diseño. Los muros
   EI P1–P4 sin armadura real quedan bloqueados con el pendiente visible (Hito A2
   en curso). La **curva de capacidad columna EI es DEMO** (`fc=40 MPa`,
   `HIPOTESIS_DEMOSTRACION`, sección 0,7×0,7 con 12 barras) → rotulado, no oculto.
3. En la ficha (`DibujarPmBloque`, `EsfuerzosController.cs`), el bloque P–M dibuja
   la **curva N–M de capacidad** + el **punto de demanda (P, M)** del caso gobernante;
   la etiqueta indica clasificación, estado de armadura, modo_μu y D/C. El panel se
   amplió (640 px) y al seleccionar un elemento con P–M la ficha se auto-desplaza al
   bloque; ficha y panel Inspección quedan sincronizados. Verificado en escena
   2026-09-16 (14 capturas `aceptacion7_*`). Se activa por **selección normal del
   elemento** (clic sobre columna/muro con resultados).

## Argumentos de defensa

- **Topología**: apoyos artificiales 0; enlaces/excentricidades documentados; congelamiento
  con hash; combos regenerados sobre la topología cerrada.
- **Honestidad contable**: reconciliación G = inventario (parcial), no validación; ninguna
  fuente se inventa — las hipótesis se declaran y bloquean por id (`EVALUACION_HIPOTESIS_*`).
- **Trazabilidad**: elementTag único FE ↔ objeto viewer ↔ resultados ↔ sección ↔ curva P–M;
  cadenas regenerables listadas en `semana04.md` §8.
- **Validación independiente** de la superposición normativa (no re-usa el exportador).

## Pendientes que SÍ se pueden mencionar (mostrarlos rotulados, no ocultos)

- Armaduras reales de muros (hipótesis bloqueada para P–M); núcleo P2 excluido; losas sin FE
  (437,40 m²); altura C.H. y parámetros sísmicos normativos; carga de voladizo P2 (`N[U1]=0`).

## Check rápido antes del miércoles

- [ ] Suite total Python **108 passed + 4 subtests** (Hito B 45: exporter 26 + islas 5 + pm 5
  + validación 4 + reconciliación 5; + aceptación extremos 9 + correspondencia 3D 6 +
  regresiones viewer 12/8 + cargas 11 + combinación 4 + capacidad RC 13).
- [ ] Unity compila en batchmode (0 errores, `CheckEsfuerzosOverlay` OK) y escena `Main`
  validada 2026-09-16 (P–M visible + sincronización Inspección↔ficha, capturas `aceptacion7_*`).
- [ ] Ficha con todos los campos del contrato + material + reacción base + desplazamientos + P–M.
- [ ] Deformada amplificada (toggle+slider), valores reales en ficha; envolvente mencionada.
- [ ] Selección distribuida por todos los niveles (min. 2 objetos/nivel).
- [ ] P–M columna y muro con caso concurrente; hipótesis declaradas y bloqueadas.
- [ ] Nombres/roles de los 3 integrantes alineados con A–D.