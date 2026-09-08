# Entrega 03 — Cargas gravitacionales, sismo y capacidad (entrega integral)

> **Proyecto 1 · MCOC.** Esta entrega se trata como **una sola entrega integral**: la
> pauta puede distribuir los puntos entre el jueves y el viernes para la defensa oral,
> pero **no** se divide el trabajo: la presentación debe mostrar el proceso completo.
> Se organiza únicamente por **dependencia técnica**.
>
> Alcance único (11 puntos):
> 1. Caso `G` completo.
> 2. Caso `Q` completo.
> 3. Sismo pseudoestático: `EX`, `−EX`, `EY`, `−EY`.
> 4. Peso sísmico y fuerzas por nivel.
> 5. Superposición inicial y verificada.
> 6. Envolventes de resultados.
> 7. Fiber Sections de columna y muro.
> 8. Curvas momento–curvatura `M–φ`.
> 9. Curvas de interacción `P–M` de columna y muro.
> 10. Primera evaluación demanda/capacidad.
> 11. Material completo para presentación oral.

---

## Clasificación de casos (nomenclatura estricta)

| Caso | Significado |
|---|---|
| `G` | Cargas **permanentes** (peso propio + PM.ADIC). |
| `Q` | Carga **viva / sobrecarga de uso** (`SC`). La `SC` es componente de **Q**, no un faltante del caso `G`. |
| `EX` | Acción sísmica pseudoestática en dirección X. |
| `−EX` | Sentido opuesto de `EX`. |
| `EY` | Acción sísmica pseudoestática en dirección Y. |
| `−EY` | Sentido opuesto de `EY`. |

---

## Método sísmico requerido: **pseudoestático**

La pauta solicita **sismo pseudoestático**. Como requisito inmediato (no análisis
modal/espectral):

- determinación del **peso sísmico**;
- **coeficiente sísmico / corte basal**;
- **distribución vertical** de fuerzas;
- **aplicación horizontal por nivel**;
- casos `±EX` y `±EY`;
- **excentricidad accidental / torsión** solo si la norma adoptada lo exige;
- cálculo de **desplazamientos, reacciones y derivas**.

> El análisis modal o espectral puede quedar mencionado como **ampliación futura**, no
> como implementación necesaria de esta entrega.

---

## Estructura de carpetas

Organización por las **tres líneas de trabajo** (mensaje del profesor):
carga viva / sismo, superposición, y capacidad RC por fibras.

```
entrega_03_cargas_sismo_capacidad/
├── README.md                        ← este archivo (alcance único integral)
├── config/
│   ├── cargas.json                  ← q_Q = 2,0 kN/m² ADOPTADA por el grupo (antes null)
│   ├── sismo.json                   ← pseudoestático de la consigna (a=0,20, 0,50·Q); normativos null
│   ├── superposicion.json           ← coeficientes (conjunto demo) + verificación completa
│   ├── capacidad_rc.json            ← DEMO_RC_EI (f'c 40) / DEMO_RC_EII (f'c 35), 12#25
│   ├── fuentes.json                 ← rutas de consulta a fuentes existentes (lectura)
│   └── parametros_pendientes.json   ← bloqueos (valor null hasta tener fuente)
├── src/
│   ├── comun/
│   │   ├── __init__.py
│   │   └── geometria_tributaria.py  ← loaders Semana 2 (EI por_viga.json / EII CSV)
│   ├── cargas/
│   │   ├── __init__.py
│   │   ├── carga_viva_Q.py          ← Q por nivel y global, catálogo separado
│   │   ├── caso_Q_EI.py             ← caso FE Q completo del Edificio I (G ausente)
│   │   ├── caso_Q_EII.py            ← caso FE Q completo del Edificio II (G ausente)
│   │   ├── peso_sismico.py          ← ledger W + CM + F_i (proporcional a W_i)
│   │   ├── caso_sismico.py          ← EX/EY pseudoestático por edificio + verificadores
│   │   ├── auditoria_G_EII.py       ← auditoría corta + congelación G_EII
│   │   ├── verificacion_intermedia_G_Q_EI.py   ← G+Q (3 corridas FE) Edificio I
│   │   ├── verificacion_intermedia_G_Q_EII.py  ← G+Q (3 corridas FE) Edificio II
│   │   ├── verificacion_superposicion_completa.py ← 5 corridas (G,Q,EX,EY,EXPLICITA) por edificio
│   │   └── sismo_EX_EY.py           ← (legado) arquitectura inicial; sustituido por caso_sismico
│   ├── superposicion/
│   │   ├── __init__.py
│   │   └── combinacion.py           ← R = λG·G+λQ·Q+λEX·EX+λEY·EY
│   ├── capacidad_rc/                ← herramienta INDEPENDIENTE de capacidad RC
│   │   ├── __init__.py  materiales.py  seccion.py  fibra.py
│   │   ├── edificios.py             ← M–φ y P–M por edificio (DEMO_RC_EI/EII)
│   │   ├── demanda_capacidad.py     ← D/C por edificio (demanda EXPLICITA + P–M)
│   │   └── __main__.py              ← demo mínimo → results/ y figures/
│   ├── ejecutar_entrega_03.py       ← EJECUTOR ÚNICO de todo el pipeline
│   ├── peso_propio_teorico_EDIFICIO_I_v2.py        ← auditoría PP EI (vigente)
│   └── peso_propio_teorico_EDIFICIO_II_v1.py       ← auditoría PP EII (hash df7fa3…)
├── tests/
│   ├── cargas/  test_carga_viva_Q.py  test_sismo_EX_EY.py
│   ├── superposicion/  test_combinacion.py
│   └── capacidad_rc/  test_capacidad_rc.py
├── results/
│   ├── cargas/          ← caso_Q_{EI,EII}_FE.json, caso_sismico_{EX,EY}_{I,II}.json, G_EII_reproducible, AUDITORIA_G_EII_v1
│   ├── superposicion/   ← verificacion_intermedia_G_Q_EI/_EII + verificacion_superposicion_completa_{I,II}.{json,csv,md}
│   ├── capacidad_rc/    ← DEMO_RC_{EI,EII}.json (+_m_phi/_p_m.csv), demanda_capacidad_{I,II}.{json,csv}, resumenes
│   ├── ejecutor_entrega_03/ ← estado.json/md (estado global OK)
│   └── peso_propio_teorico_EDIFICIO_I/II_v*.json (+ _hash.txt)
├── figures/
│   ├── cargas/          ← Q por nivel/global + sismo
│   ├── superposicion/   ← verificacion_{intermedia,completa}_*.png
│   ├── capacidad_rc/    ← DEMO_RC_*_{seccion_fibras,m_phi,diagrama_pm}.png
│   └── (figuras PP)
└── docs/
    ├── GUIA_DEFENSA.md              ← respuestas de defensa (superposición, fibras, P–M…)
    ├── INFORME_SEMANA_3.md          ← resumen ejecutivo de esta entrega
    ├── FIBER_SECTION_EVIDENCIA.md   ← evidencia de la sección por fibras (M_u, criterio)
    ├── PREGUNTAS_PROFESOR_MIERCOLES.md ← 7 preguntas abiertas (bloqueos)
    ├── PLAN_ENTREGA_03.md           ← este planificador + matriz de estados exactos
    ├── AUDITORIA_INICIAL.md
    └── RESOLUCION_PENDIENTES_PP_EI.md
```

---

## Estado del caso G al momento de la auditoría *(NO está completo en el Edificio I)*

- **Edificio I — caso G aplicado en el FE:** `G_EI = PP losas + PM.ADIC` únicamente
  (`ΣFz = −25.227,73 kN`). **NO** incluye PP explícito de vigas, columnas ni muros
  (verificado en el código: solo `ops.load` nodal desde losas; sin `selfWeight`,
  `eleLoad` ni `mass`). Por tanto **no** debe describirse como completo.
- PP teórico de elementos (auditoría, **sin aplicar**): ≈ **17.179,23 kN confirmado**
  (vigas ~14.803,5 + columnas ~2.045,6 + muros ~330,1; el total v1 de 24.116,5 kN
  queda **descartado** — perfiles metálicos macizos, tramos base ficticios y muros
  agrupados incorrectamente). Ver `src/peso_propio_teorico_EDIFICIO_I_v2.py` y
  `results/peso_propio_teorico_EDIFICIO_I_v2.json` (+ `_hash.txt`).
- **Edificio II — caso G publicado:** PP de elementos (19.629 kN: columnas 1.522 +
  vigas 11.585 + muros 6.521) **sí incluidos**; PP de losas (~9.677 kN); PM.ADIC y
  `Q/SC` del plano son **lineales (kg/m) pendientes de mapeo**.
- **No comparar directamente totales** de I y II mientras sus casos `G` no contengan
  los mismos tipos de componentes.

---

## Reproducibilidad

- **Requisitos (pinned):** `requirements.txt` de esta misma carpeta
  (`openseespy==3.7.0.3`, `numpy==2.4.6`, `matplotlib==3.11.1`, `shapely==2.1.2`).
  Probado en **Windows 11, Python 3.11.9**. Instalación:
  `python -m pip install -r requirements.txt`.
- El motor del Edificio I se **reutiliza por importación** (`PYTHONPATH=src`);
  `config/fuentes.json` lista las rutas de lectura.
- **Edificio II:** los artefactos `analisis_estructural/edificio_II_casoG_PP_elementos/*`
  están versionados, pero el **pipeline que los generó no** (la geometría original vivía en
  `laboratorio_semana2/`, sin versionar). La auditoría incorpora la tabla de fuentes
  externas en `docs/AUDITORIA_INICIAL.md` §9 y la evaluación de viabilidad de
  reconstruir el pipeline con el motor del edificio I.
- **Dependencias externas resueltas:** del total de `laboratorio_semana2/` se copian **solo 2
  archivos mínimos** a `data/externas/` (el catálogo de sobrecargas del EI y las áreas
  tributarias del EII), con procedencia, tamaño y SHA-256 en `data/externas/PROCEDENCIA.md`.
  Todo el resto del pipeline lee de fuentes versionadas o de artefactos regenerados por el
  propio ejecutor; no se copia `laboratorio_semana2/` completa.

---

## Estado actual de las tres líneas de trabajo

Estados exactos (matriz completa en `docs/PLAN_ENTREGA_03.md`): un componente = un
estado de `IMPLEMENTADO_Y_VERIFICADO`, `IMPLEMENTADO_DEMO_ARBITRARIA`,
`PREPARADO_NO_EJECUTADO`, `BLOQUEADO_POR_PARAMETROS`, `PENDIENTE_ORIGEN_PIPELINE`,
`IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO(_II)`, `PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA`,
`HIPOTESIS_DEMOSTRACION` y el estado congelado
`G_EII_REPRODUCIBLE_CON_DISCREPANCIAS_DOCUMENTADAS`.
**Las líneas de capacidad no son "diseño real"**: usan secciones de demostración
claramente marcadas.

| Componente | Estado |
|---|---|
| `Q` — verificación `ΣQ=q_Q·A` + catálogo separado | `IMPLEMENTADO_Y_VERIFICADO` |
| `Q` — **caso FE completo Edificio I** (G ausente, equilibrio) | `IMPLEMENTADO_Y_VERIFICADO` (q_Q=2,0 adoptada) |
| `Q` — **caso FE completo Edificio II** (G ausente, equilibrio) | `IMPLEMENTADO_Y_VERIFICADO` (q_Q=2,0 adoptada) |
| `EX`/`EY` — parámetros (pseudoestático de la consigna) y ejecución | `IMPLEMENTADO_Y_VERIFICADO` (`PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA`: a=0,20; 0,50·Q en W) |
| Peso sísmico `W` y distribución nodal `F_i` | `IMPLEMENTADO_Y_VERIFICADO` (EI W=29337,20 kN, F=5867,44 kN; EII W=28600,71 kN, F=5720,14 kN) |
| Superposición (combinación + verificación **completa** G+Q+EX+EY) | `IMPLEMENTADO_Y_VERIFICADO` (`verificacion_final=IMPLEMENTADO_Y_VERIFICADO_COMPLETO`) |
| Superposición (verificación **intermedia G+Q Edificio I**) | `IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO` |
| Superposición (verificación **intermedia G+Q Edificio II**) | `IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO_II` |
| Fiber Section | `IMPLEMENTADO_Y_VERIFICADO` |
| Curva M–φ y diagrama P–M **por edificio** (70×70 real, armado demo 12#25) | `IMPLEMENTADO_DEMO_ARBITRARIA` (`HIPOTESIS_DEMOSTRACION`; EI f'c 40 → M_u=896,46 kN·m; EII f'c 35 → M_u=875,00 kN·m) |
| Evaluación demanda/capacidad (D/C) por edificio | `EVALUACION_ALGORITMICA_CON_SECCION_DEMO` (97/97 y 32/32 columnas evaluadas mediante el procedimiento con D/C<=1 *aritmético* sobre capacidad de demostración; crítico EI col. 208, EII col. 25) |
| Ejecutor único | `IMPLEMENTADO_Y_VERIFICADO` (`src/ejecutar_entrega_03.py`, estado global OK) |
| Auditoría PP EII | `IMPLEMENTADO_Y_VERIFICADO` (G_EII NO cerrado, muros `PENDIENTE_ORIGEN_PIPELINE`) |
| Cierre **`G_EII`** | `G_EII_REPRODUCIBLE_CON_DISCREPANCIAS_DOCUMENTADAS` (auditoría corta `auditoria_G_EII.py`; sin calibrar rigideces/ruteos) |

Detalles clave:

- **Q caso FE EI/EII**: `src/cargas/caso_Q_EI.py` y `caso_Q_EII.py` corren con
  **q_Q=2,0 kN/m² adoptada** (decisión del grupo registrada en `config/cargas.json`);
  ya no requieren `--demo`. `ΣQ=q_Q·A=8.218,9 kN` (EI, Δ0,0) y `5.259,43 kN` (EII,
  rel 5,7e-09); equilibrio `Rz=Pz`; `G_ausente`. Resultados:
  `results/cargas/caso_Q_EI_FE.json` y `case_Q_{EI,EII}_FE_reacciones.csv`.
- **EX/EY**: método pseudoestático de la consigna en `src/cargas/caso_sismico.py`
  (4 combinaciones ejecutadas y verificadas con retcode 0). `F_i = 0,20·W_i` con
  `W_i = PP_i + 0,50·Q_i`, distribución nodal `fn = Fi·wn/Wi`. Verificaciones por
  caso: corte basal, balance horizontal, momento accidental 0, dirección exclusiva,
  sentido de deformada (con aviso de nodos opuestos en la franja D-D' de EII) y
  retcode FE. `config/sismo.json` marca `PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA`;
  los parámetros normativos (zona, suelo, R, espectro) quedan `null`/PENDIENTE.
- **Superposición completa**: `src/cargas/verificacion_superposicion_completa.py`
  ejecuta 5 corridas FE por edificio (G, Q, EX, EY y la combinación EXPLICITA
  `1.0G+0.7Q+0.3EX−0.2EY` del conjunto de demostración) y compara la superpuesta vs
  la explícita en 8 magnitudes con errores máximos ~1,9e-15 (EI) y ~2e-13 (EII);
  8/8 OK y equilibrio global por edificio. `config/superposicion.json`:
  `verificacion_final=IMPLEMENTADO_Y_VERIFICADO_COMPLETO`. La combinación usada no
  es la normativa (coeficientes reales pendientes).
- **Capacidad RC por edificio**: `src/capacidad_rc/edificios.py` + `config/capacidad_rc.json`.
  Sección real de columna **70×70** documentada en ambos edificios (EI G40 → f'c=40 MPa
  hipótesis del grupo; EII G35 → f'c=35 MPa documentado). Armadura real no documentada
  → armado de demostración **12#25** (rec 0,04 m, fy 420 MPa), marcado
  `HIPOTESIS_DEMOSTRACION`. M_u(N=0): **EI 896,46 kN·m**, **EII 875,00 kN·m** (criterio:
  aplastamiento del hormigón, eps_cu=0,004). Resultados: `results/capacidad_rc/DEMO_RC_{EI,EII}.json`
  (+ `_m_phi.csv`, `_p_m.csv`, figuras `figures/capacidad_rc/`), `resumen_DEMO_RC_EI_EII.json`.
- **D/C** (`EVALUACION_ALGORITMICA_CON_SECCION_DEMO`): `src/capacidad_rc/demanda_capacidad.py`
  toma la demanda **EXPLICITA** de la superposición (misma corrida FE) y la capacidad del
  P–M interpolado M_u(N) de la **sección de demostración** `DEMO_RC_*`. Todas las columnas
  se **evalúan mediante el procedimiento** (EI 97, EII 32) y quedan por debajo de D/C<=1
  en comparación **aritmética** con capacidad de demostración; crítico **EI col 208 (D/C=0,5014)**,
  **EII col 25 (D/C=0,2583)**. El resultado **no es válido como comprobación de diseño** y no
  representa aprobación estructural de las columnas reales (armadura real bloqueada). Resultados:
  `results/capacidad_rc/demanda_capacidad_{I,II}.{json,csv}` y `resumen_demanda_capacidad.txt`.
- **Ejecutor único**: `src/ejecutar_entrega_03.py` corre las 12 corridas del pipeline
  (Q, sismo EX/EY, G+Q, superposición completa, capacidad RC y D/C) y escribe
  `results/ejecutor_entrega_03/estado.{json,md}` con estado global **OK**.

### Cómo ejecutar (desde esta carpeta)

```bash
python -X utf8 -m unittest discover -s tests -p "test_*.py"   # tests OK
python -X utf8 -m src.ejecutar_entrega_03                    # EJECUTOR ÚNICO (todo el pipeline)
python -X utf8 -m src.cargas.carga_viva_Q --demo             # reporte Q (áreas tributarias EI/EII)
python -X utf8 -m src.cargas.caso_Q_EI                       # caso FE Q del EI (G ausente)
python -X utf8 -m src.cargas.caso_Q_EII                      # caso FE Q del EII (G ausente)
python -X utf8 -m src.cargas.caso_sismico --edificio I --direccion X   # sismo EX del EI
python -X utf8 -m src.cargas.caso_sismico --edificio II --direccion Y  # sismo EY del EII
python -X utf8 -m src.cargas.auditoria_G_EII                 # auditoría corta + congelación G_EII (requiere corrida previa de caso_G_EII)
python -X utf8 -m src.cargas.verificacion_intermedia_G_Q_EI        # G+Q EI (3 corridas FE)
python -X utf8 -m src.cargas.verificacion_intermedia_G_Q_EII       # G+Q EII (3 corridas FE)
python -X utf8 -m src.cargas.verificacion_superposicion_completa --edificio I   # 5 corridas EI
python -X utf8 -m src.cargas.verificacion_superposicion_completa --edificio II  # 5 corridas EII
python -X utf8 -m src.capacidad_rc.edificios                # M-phi + P-M por edificio
python -X utf8 -m src.capacidad_rc.demanda_capacidad       # D/C por edificio
```

Preguntas para destrabar antes de la defensa:
`docs/PREGUNTAS_PROFESOR_MIERCOLES.md`.

---

## Reglas operativas

1. **No modificar** los modelos numéricos, cargas, resultados ni el viewer Unity.
2. **No mover ni borrar** archivos externos; todo lo que produce esta entrega vive en
   esta carpeta o se documenta como derivado.
3. `laboratorio_semana2/` **no se copia ni se incluye** en el paquete. Solo se incorporan
   los **2 archivos mínimos** necesarios en tiempo de ejecución (ver `data/externas/PROCEDENCIA.md`):
   el catálogo de sobrecargas del EI y las áreas tributarias del EII. Si el pipeline
   necesitara más insumos, se copian de forma mínima con nota de procedencia.
4. Los edificios I y II conservan modelos FE **independientes** (nunca nodos
   compartidos en la junta D–D′).
5. **No inventar parámetros no documentados**: q_Q (2,0 kN/m²), el coeficiente
   sísmico (método de la consigna, a=0,20) y el armado de columnas (12#25, demo) son
   **decisiones del grupo, explícitamente marcadas** en `config/` como
   adoptadas/demostración; el resto de datos pendientes queda en `null` en
   `config/parametros_pendientes.json` y el código debe detenerse si intenta usarlo.
6. La superposición conserva los casos elementales y sus signos: `G`, `Q`, `EX`,
   `−EX`, `EY`, `−EY`. No se adopta LRFD/ASCE como decisión tomada; se busca fuente.

---

## Punto de partida (resumen de `docs/AUDITORIA_INICIAL.md`)

- Caso G del EI está **parcial** (sin PP de elementos, PP teórico ~17.179 kN aparte).
- Caso G del EII publicado (PP elementos + losas), pero con **material G35 vs G40**
  en conflicto, `V_031` `por_resolver`, y PM.ADIC/`Q` lineales pendientes.
- Bloqueos sísmicos (`config/parametros_pendientes.json`): zona sísmica, suelo,
  importancia, R, coeficiente, excentricidad, fracción de `Q` en peso sísmico,
  combinaciones.
- Bloqueos de capacidad: `fy`, recubrimiento, armadura de columna/muro. No existe
  código Fiber / M–φ / P–M en el repo (solo secciones elásticas).
- Tabla completa de trabajo en `docs/AUDITORIA_INICIAL.md` §11.