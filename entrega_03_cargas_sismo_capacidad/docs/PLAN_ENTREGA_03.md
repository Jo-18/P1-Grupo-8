# PLAN — Entrega 03 (cargas, sismo, superposición, capacidad RC)

> Planificador de la entrega integral. Estados exactos (un componente = un estado):
> `IMPLEMENTADO_Y_VERIFICADO` (código + ejecución verificada), `IMPLEMENTADO_DEMO_ARBITRARIA`
> (funciona con valores arbitrarios marcados, no reales), `PREPARADO_NO_EJECUTADO`
> (código listo, no ejecutable o no ejecutado por falta de datos),
> `BLOQUEADO_POR_PARAMETROS` (no ejecutable sin parámetros/documentos),
> `PENDIENTE_ORIGEN_PIPELINE` (depende de reconciliar el origen del modelo/geometría).
> Los valores arbitrarios se marcan siempre `DEMOSTRACION_ARBITRARIA` /
> `HIPOTESIS_DEMOSTRACION`.

## Líneas de trabajo (mensaje del profesor)

1. **Carga viva y carga sísmica** → `src/cargas/` + `config/{cargas,sismo}.json`.
2. **Superposición** → `src/superposicion/` + `config/superposicion.json`.
3. **Capacidad RC mediante secciones por fibras** → `src/capacidad_rc/`
   (herramienta independiente, no integrada al viewer).

## Matriz de estados

Estado exacto por componente; ningún estado indica "todo terminado".

| Componente | Estado | Nota / bloqueo |
|---|---|---|
| Geometría tributaria Semana 2 (EI `por_viga.json`, EII `areas_tributarias.csv`) | `IMPLEMENTADO_Y_VERIFICADO` | loaders en `src/comun/geometria_tributaria.py`; EII solo ensayo CP2 |
| `Q` — catálogo separado de aplicada | `IMPLEMENTADO_Y_VERIFICADO` | `aplicada_al_modelo_FE=false`; no doble aplicación |
| `Q` — `q_Q` **adoptado** por el grupo (decisión registrada) | `IMPLEMENTADO_Y_VERIFICADO` | **q_Q = 2,0 kN/m²** para EI y EII, adoptado por el grupo y documentado (antes `null`). EI verificación `ΣQ=q_Q·A=8218,9 kN` (Δ0,0), EII `5.259,43 kN` (rel 5,7e-09) |
| `Q` — verificación `ΣQ = q_Q·A` por nivel y global | `IMPLEMENTADO_Y_VERIFICADO` | EI `OK` (0,0), EII `OK` (rel 9e-08); tol 0,005 |
| `Q` — **caso FE completo del Edificio I** (G ausente, equilibrio) | `IMPLEMENTADO_Y_VERIFICADO` | `src/cargas/caso_Q_EI.py` con q_Q adoptado: `ΣQ=q_Q·A=8218,9 kN` (Δ0,0), `G_ausente`, equilibrio `Rz=Pz`; 324 nodos/349 elementos |
| `Q` — **caso FE completo del Edificio II** (G ausente, equilibrio) | `IMPLEMENTADO_Y_VERIFICADO` | `src/cargas/caso_Q_EII.py` sobre el modelo congelado EII: `ΣQ=q_Q·A=5259,43 kN`, conservación exacta (Δ0,0); 222 nodos/264 elementos; `caso_Q_EII_FE.json` |
| `EX`/`EY` — arquitectura + verificadores (corte basal, sentido deformada, torsión) | `IMPLEMENTADO_Y_VERIFICADO` | `src/cargas/caso_sismico.py` con verificaciones por caso: corte basal F=ΣW·0,20, balance horizontal, momento accidental, dirección exclusiva, sentido dominante (con aviso de nodos opuestos D-D'), retcode FE |
| `EX`/`EY` — parámetros y ejecución | `IMPLEMENTADO_Y_VERIFICADO` | **Método pseudoestático de la consigna** (resuelto por el grupo, no normativo): `a=0,20g`, `m_i=(PP_i+0,50·Q_i)/g`, `F_i=0,20·W_i`; clasificación `PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA`. 4 corridas OK: EX_EI, EY_EI, EX_EII, EY_EII (retcode 0). EI: W=29337,20 kN F=5867,44 kN; EII: W=28600,71 kN F=5720,14 kN |
| Peso sísmico `W` — ledger y distribución nodal | `IMPLEMENTADO_Y_VERIFICADO` | `src/cargas/peso_sismico.py` probado; distribución nodal `fn=Fi·wn/Wi`; resultados en `results/cargas/caso_sismico_*` |
| Superposición completa 5 corridas por edificio (G, Q, EX, EY, EXPLICITA) | `IMPLEMENTADO_Y_VERIFICADO` | `config/superposicion.json` `verificacion_final=IMPLEMENTADO_Y_VERIFICADO_COMPLETO`. Conjunto de demostración `1.0G+0.7Q+0.3EX−0.2EY` (marcado, NO normativo). 8/8 magnitudes OK por edificio (máx rel 1,9e-15 EI / 2e-13 EII); patrón consistente; equilibrio |G, |Q, |EX, |EY por edificio |
| — Intermedio: **verificación G+Q Edificio I** | `IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO` | 3 corridas FE (G, Q, G+λ·Q); 8/8 OK (máx rel 3e-15) |
| — Intermedio: **verificación G+Q Edificio II** | `IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO_II` | sobre modelo congelado EII; 8/8 OK (máx rel 4e-14); `R_z` explícito = 29652,60 kN |
| **Capacidad RC por edificio** (M–φ y P–M con secciones por fibras) | `IMPLEMENTADO_DEMO_ARBITRARIA` | `src/capacidad_rc/edificios.py` + `config/capacidad_rc.json`: sección real **P. 70×70 documentada** en ambos; armadura real **no documentada → armado de demostración 12#25** (rec 0,04 m, fy 420 MPa). **DEMO_RC_EI** (f'c 40 MPa, hipótesis del grupo G40): M_u(N=0)=896,46 kN·m; **DEMO_RC_EII** (f'c 35 MPa, documentado G35): M_u(N=0)=875,00 kN·m. Criterio falla: aplastamiento hormigón (eps_cu=0,004). Clasificación `HIPOTESIS_DEMOSTRACION` |
| **D/C por edificio** (demanda/capacidad con selección trazable) | `EVALUACION_ALGORITMICA_CON_SECCION_DEMO` | `src/capacidad_rc/demanda_capacidad.py`: demanda EXPLICITA superpuesta (1.0G+0.7Q+0.3EX−0.2EY, conjunto demo) + capacidad P–M interpolada M_u(N) con **sección de demostración** `DEMO_RC_*`. **EI**: 97 columnas evaluadas, crítico col 208 (nivel P4, extremo j, D/C 0,5014); **EII**: 32 evaluadas, crítico col 25 (nivel EII_CP3, extremo j, D/C 0,2583). D/C<=1 es **aritmético** sobre capacidad demo: **no válido como comprobación de diseño y no aprueba las columnas reales**. `resumen_demanda_capacidad.txt` |
| **Ejecutor único** (todo el pipeline) | `IMPLEMENTADO_Y_VERIFICADO` | `src/ejecutar_entrega_03.py`: 12 corridas (Q EI/EII, EX/EY × 2 edificios, G+Q EI/EII, superposición completa EI/EII, capacidad RC, D/C) → `results/ejecutor_entrega_03/estado.json` estado global **OK** |
| Fiber Section (malla hormigón + acero) | `IMPLEMENTADO_Y_VERIFICADO` | cross-check OpenSees; área conservada |
| Sección real columna/muro | `BLOQUEADO_POR_PARAMETROS_NO_BLOQUEANTE` | f'c documentado (EI G40 hipótesis del grupo / EII G35 documentado), fy/rec/armadura **no documentados** → resuelto con secciones `DEMO_RC_*` marcadas `HIPOTESIS_DEMOSTRACION`; **no se declara capacidad real de diseño** |
| Auditoría PP EII | `IMPLEMENTADO_Y_VERIFICADO` | `G_EII_REPRODUCIBLE_CON_DISCREPANCIAS_DOCUMENTADAS`; 293 rutas (161 DOC / 118 HIPOT / 14 SIN_CAMINO) |
| Docs defensa / README / este plan / FAQ profesor | `IMPLEMENTADO_Y_VERIFICADO` | + `INFORME_SEMANA_3.md` (resumen ejecutivo de la entrega) |

> **Carpeta definitiva:** `entrega_03_cargas_sismo_capacidad/` (única).

## Cómo ejecutar (desde `entrega_03_cargas_sismo_capacidad/`)

```bash
# Pruebas
python -X utf8 -m unittest discover -s tests -p "test_*.py"

# EJECUTOR ÚNICO (todo el pipeline: Q, sismo EX/EY, G+Q, superposición, capacidad RC, D/C)
python -X utf8 -m src.ejecutar_entrega_03
#   opcional: --solo 1,4  (1=Q, 2=sismo, 3=G+Q, 4=superposición, 5=capacidad, 6=D/C)

# Q: caso FE completo por edificio (q_Q=2,0 adoptado; sin --demo)
python -X utf8 -m src.cargas.caso_Q_EI
python -X utf8 -m src.cargas.caso_Q_EII

# Sismo EX/EY por edificio (pseudoestático de la consigna)
python -X utf8 -m src.cargas.caso_sismico --edificio I --direccion X
python -X utf8 -m src.cargas.caso_sismico --edificio II --direccion Y

# Superposición: verificación intermedia G+Q por edificio
python -X utf8 -m src.cargas.verificacion_intermedia_G_Q_EI
python -X utf8 -m src.cargas.verificacion_intermedia_G_Q_EII

# Superposición: verificación completa 5 corridas por edificio
python -X utf8 -m src.cargas.verificacion_superposicion_completa --edificio I
python -X utf8 -m src.cargas.verificacion_superposicion_completa --edificio II

# Capacidad RC por edificio (M-φ, P-M, resumen) y D/C
python -X utf8 -m src.capacidad_rc.edificios
python -X utf8 -m src.capacidad_rc.demanda_capacidad
```

## Cómo se resolvió el alcance (decisiones registradas en config)

- **q_Q = 2,0 kN/m²**: valor real no disponible en fuentes → adoptado por el grupo
  (decisión del equipo), documentado en `config/cargas.json` y `case_Q_*`; ya no
  requiere `--demo`.
- **EX/EY**: método pseudoestático de la consigna (`a=0,20`, `0,50·Q` en el peso
  sísmico, `F=0,20·W`, distribución nodal proporcional) clasificado
  `PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA`; **no** se usan parámetros
  normativos (zona, suelo, R, espectro quedan `null`/PENDIENTE en `config/sismo.json`).
- **Superposición**: combinación `1.0G+0.7Q+0.3EX−0.2EY` marcada como conjunto de
  demostración (coeficientes normativos reales no disponibles).
- **Capacidad**: armadura real no documentada → secciones `DEMO_RC_EI/EII`
  (12#25, f'c 40/35 MPa) marcadas `HIPOTESIS_DEMOSTRACION`; M_u y P–M representan
  la integración del método, no capacidad de diseño real.

## Pendientes explícitos (para destrabar)

- Sismo: parámetros **normativos** (zona, suelo, importancia, `R`, espectro,
  excentricidad real) si el docente exige diseño normativo; hoy se usa el método
  de la consigna (acordado).
- Capacidad: `fy`, recubrimiento y armadura **reales** de columnas/muros para
  sustituir las secciones `DEMO_RC_*`.
- Superposición: coeficientes normativos reales para sustituir el conjunto de
  demostración `1.0_0.7_0.3_-0.2`.
- Preguntas para destrabar: `docs/PREGUNTAS_PROFESOR_MIERCOLES.md`.