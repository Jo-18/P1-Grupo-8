# Preguntas para el profesor — miércoles (Entrega 3)

Estado al momento de plantear las preguntas: 7 ítems abiertos. Cada pregunta indica
el bloqueo (`BLOQUEADO_POR_PARAMETROS`, `PENDIENTE_ORIGEN_PIPELINE`,
`BLOQUEADO_POR_PARAMETROS_SISMICOS` — antes `BLOQUEADO_POR_CASOS_BASE`) que su
respuesta destraba.

---

## 1. Coeficientes de combinación de carga `λ_G, λ_Q, λ_EX, λ_EY`

- **Contexto:** ya se combina `R = λ_G·G + λ_Q·Q + λ_EX·EX + λ_EY·EY` con un conjunto
  de demostración marcado `DEMOSTRACION_ARBITRARIA_1.0_0.7_0.3_-0.2`
  (`config/superposicion.json`) y la verificación estructural está bloqueada hasta
  tener los casos base.
- **Pregunta:** ¿qué norma de combinación y qué factores deben usarse para las
  cargas definitivas? ¿Se usan factores de servicio o de diseño (1.2/1.6, 1.4G+1.7Q,
  NSR, NEC, ASCE…)? ¿Deben aplicarse ya como valores (no null) en el entregable?
- **Bloquea / destraba:** sustituir los λ demostrativos por los definitivos
  (`DEFINIDO` en `config/superposicion.json`).

## 2. Valor real de `q_Q` (carga viva repartida) y cómo se pide

- **Contexto:** `q_Q` está `null` en `config/cargas.json` (ambos edificios). El caso Q
  del Edificio I ya corre como FE completo con `--demo` y `q_Q=2.0 kN/m²` marcado
  `DEMOSTRACION_ARBITRARIA_qQ_2.0`; el Edificio II quedó `PREPARADO_NO_EJECUTADO`.
- **Pregunta:** ¿cuál es el valor real de carga viva por m² a usar (y si aplica en
  losa y en la totalidad de la planta)? ¿Se debe usar *un solo* `q_Q` o hay
  sobrecarga por destinos?
- **Bloquea / destraba:** quitar la marca de demostración y ejecutar el caso Q
  definitivo (`q_Q` real) en ambos edificios.

## 3. Definición del sismo `EX` / `EY` (antes bloqueado por parámetros)

- **Contexto:** `config/sismo.json` tiene todo `null` (aceleración, periodos,
  espectro). El runner de sismo aborta con mensaje claro por diseño
  (`BLOQUEADO_POR_PARAMETROS`).
- **Pregunta:** ¿con qué procedimiento se busca el sismo del proyecto (curva de
  capacidad, espectro de respuesta, análisis modal espectral)? ¿En qué formato y con
  qué unidades entrega el curso las aceleraciones de piso / espectro (g, m/s², %g)?
  ¿El sismo se aplica como fuerzas estáticas equivalentes, espectro de respuesta o
  historias? ¿Cuál es el periodo fundamental esperado para el Edificio I?
- **Bloquea / destraba:** casos base `EX`/`EY` → verificación final de superposición.

## 4. Tolerancia de la verificación estructural de la superposición

- **Contexto:** la comparación R vs corrida explícita usa hoy `tolerancia_rel=0.01`.
- **Pregunta:** ¿qué tolerancia relativa es aceptable para desplazamiento, reacción y
  fuerza interna (0.1 %, 1 %, 5 %)? ¿Debe reportarse por familia o una única global?
- **Bloquea / destraba:** blindar la métrica usada en
  `src/superposicion/verificar_explicita.py` antes de la entrega definitiva.

## 5. Sección real para el análisis de capacidad (RC) del Edificio I

- **Contexto:** la sección `DEMO_50x50_8#25` (fc=21 MPa, fy=420 MPa, 196 fibras de
  hormigón + 8 de acero) es arbitraria y marcada como demostración; no proviene de la
  geometría FE del edificio.
- **Pregunta:** ¿qué sección(columna/viga) real se debe analizar con la fibra
  (dimensiones, recubrimiento, cuantía y materiales según el edificio)? ¿Se cuenta con
  planos o se fija un criterio para elegirla?
- **Bloquea / destraba:** sustituir la demo por la sección real (`IMPLEMENTADO_Y_VERIFICADO`
  para capacidad RC).

## 6. Criterio de material y falla para el M_u de la sección

- **Contexto:** en la curva M–φ el hormigón usa `Concrete01`-style (`fc=21 MPa`,
  `epsu=0.004`, `fcu=0.85 fc` sin tracción) y el acero `Steel02`/`Steel01` con
  endurecimiento `b=0.01`. `M_u` se toma en el primer agotamiento
  (`APLASTAMIENTO_HORMIGON_eps_ext_fibra>=eps_cu`, `eps_cu=epsu=0.004`, o fractura
  del acero `abs(eps)>=eps_su=0.05` sobre las fibras de acero reales), ver
  `docs/FIBER_SECTION_EVIDENCIA.md`.
- **Pregunta:** ¿se confirman la deformación de aplastamiento `epsu` y `eps0`/`fcu`
  (o se prefiere el criterio de la curva de momento vs rotación)? ¿Qué deformación
  límite del acero se debe usar (p. ej. 0.05, 0.075)? ¿La sección se evalúa con la
  carga axial del caso G (compresión) además de `N=0`?
- **Bloquea / destraba:** acotar el criterio de falla y los valores reportados de
  `M_u`/`κ_u`.

## 7. Edificio II — origen del modelo (geometría, muros y motor FE)

- **Contexto:** la re-auditoría del caso G del Edificio II (9/9 checks) mantiene la
  diferencia en fuerzas laterales de los **muros**: `4.330,02 kN` (según nuestra
  ejecución) vs `6.521,26 kN` (según la fuente publicada) → factor `1,506`. El origen
  es la definición del comportamiento (columna vs muro) en el FE publicado
  (`PENDIENTE_ORIGEN_PIPELINE`, `G_EII_cerrado=False`) y no hay pipa FE importable
  para el Edificio II (por eso el caso Q del EII quedó `PREPARADO_NO_EJECUTADO`).
- **Pregunta:** para el Edificio II, ¿el marco conceptual de muros es PyMuro o
  columna? ¿Cuál es la fuente oficial de la geometría/muros? ¿Existe el motor FE del
  Edificio II (mismo `main_fe.py`) para ejecutar casos con las mismas unidades?
- **Bloquea / destraba:** reconciliar `G_EII` y cerrar el `PENDIENTE_ORIGEN_PIPELINE`.