# Guía de defensa — Entrega 03 (cargas, superposición, capacidad RC)

> Esta guía responde las preguntas de defensa más probables sobre las tres líneas
> de trabajo: **(1) carga viva y carga sísmica**, **(2) superposición** y **(3)
> capacidad RC mediante secciones por fibras**. Todo lo marcado como
> `DEMOSTRACION_ARBITRARIA` es un ejemplo de flujo, NO es un resultado de diseño.

---

## 1. ¿Por qué funciona la superposición? ¿Cuándo deja de funcionar?

**Por qué funciona.** El análisis estructural de esta entrega es **lineal elástico**
(material elástico, pequeñas deformaciones, pequeñas rotaciones). En un sistema
lineal la respuesta (desplazamientos, reacciones, fuerzas internas) es una función
**aditiva y homogénea** de las cargas:

```
R(λG·G + λQ·Q + λEX·EX + λEY·EY) = λG·R(G) + λQ·R(Q) + λEX·R(EX) + λEY·R(EY)
```

Si el modelo cambia de rigidez por N y M (no linealidad geométrica/material),
la matriz de rigidez depende del estado de carga, y ya **no** se puede sumar
respuestas de casos independientes.

**Cuándo deja de funcionar.**
1. **No linealidad de material**: hormigón agrietado o acero fluido (`Sect 1`/
   `sectionFiber` en capacidad RC reduce rigidez) ⇒ la rigidez depende de `N` y del
   momento, y la superposición de casos elementales deja de representar la respuesta.
2. **No linealidad geométrica (P-Δ)**: los momentos de segundo orden dependen de la
   posición deformada ⇒ el factor de amplificación cambia con la combinación.
3. **Apoyos/interfaces no lineales**: contacto, deslizamiento o daño cambian la
   numeración del sistema.
4. **Cambios de modelo entre casos**: si `G`, `Q`, `EX`, `EY` se corren con modelos
   distintos (p. ej. `G` sin `G_EII` cerrado), sumar respuestas mezcla hipótesis.

**Cómo se garantiza en esta entrega:** los casos base deben ser **casos
compatibles** (mismo modelo, mismas unidades, sin cambios de rigidez), y la
superposición se verifica contra una **corrida explícita equivalente de OpenSees**
(`desplazamiento`, `reacción`, `fuerza interna`). Hoy está verificada la parte
**intermedia G+Q** del Edificio I y II (`IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO`): 3 corridas
FE (G, Q, G+0,7Q) sobre el mismo modelo lineal, con controles de compatibilidad que
abortan y comparación superpuesto vs explícito en 8 magnitudes (errores máx ~3e-15
EI, ~4e-14 EII). Y la verificación **completa de 5 corridas** (G, Q, EX, EY y
EXPLICITA = `1.0G+0.7Q+0.3EX−0.2EY`, conjunto de demostración) está
`IMPLEMENTADO_Y_VERIFICADO` por edificio
(`src/cargas/verificacion_superposicion_completa.py`): 8/8 magnitudes OK, errores
máx ~9,8e-16 (EI) y ~1,7e-13 (EII), patrón consistente y equilibrio global.

## 2. ¿Qué representa cada fibra de una sección por fibras?

Una **fibra** es un pequeño volumen de material con área `A_f` a una posición
`(y, z)` del plano de la sección y una **ley material** (hormigón `Concrete01` o
acero `Steel01`):

```
eps(y) = eps_ct + kappa · y        (compatibilidad: plano de deformaciones)
sigma = material(eps)              (ley constitutiva)
N  = Σ σ_f · A_f
M  = Σ σ_f · A_f · y
```

- En este código hay **fibras de hormigón** (malla `nc_y × nc_z` dentro del
  perímetro, tag 1) y **fibras de acero** (una por barra en `(y_bar, z_bar)`, tag 2).
- **Qué representa**: la contribución discreta de esa pequeña zona al equilibrio
  axial y al momento, respetando que el concreto **no trabaja a tracción**
  (su ley es nula para `eps < 0`) y que el acero es simétrico a tracción/compresión.
- **Conergencia**: se verifica que `Σ A_f(hormigón) + Σ A_f(acero) = A_g` (área
  bruta conservada; en la demo 0,2500 m² = 0,2500 m²).
- El archivo `src/capacidad_rc/fibra.py` replica el patrón `section('Fiber')` +
  `fiber()` de OpenSees; `src/capacidad_rc/fibra.py::seccion_opensees` construye la
  misma discretización dentro de `openseespy` como cross-check.

## 3. ¿Por qué la carga axial P modifica la capacidad a flexión M?

La capacidad a momento se obtiene integrando tensiones sobre la sección
**compatible con un plano de deformaciones** y exigiendo el **equilibrio global**:

```
Σ σ_f·A_f ≈ N        (axial dado)
Σ σ_f·A_f·y = M      (momento asociado)
```

Si se pide `N`, el plano `eps(y) = eps_ct + κ·y` queda condicionado: para
compresión grande la fibra neutra se corre **hacia fuera** (mayor zona comprimida),
lo que cambia el brazo de las fuerzas. Por eso la **curva M–φ se desplaza** con la
carga axial:

- `N = 0`: el concreto solo comprime la zona superior; gran brazo ⇒ alto `M_u`.
- `N` compresión moderada: la zona comprimida crece ⇒ puede **subir** `M_u`
  (hasta el punto balanceado) y luego **cae** cuando el fallo es por compresión del
  concreto antes de fluir el acero.
- `N` tracción (negativa): el concreto se agrieta antes, la capacidad cae rápido.

El **diagrama P–M** muestra el lugar geométrico `M_max(N)`: esa es la superficie de
fallo de la sección.

## 4. ¿Qué diferencia hay entre demanda y capacidad?

- **Demanda** son los efectos de las cargas aplicadas al modelo estructural:
  `M_demanda = λG·M_G + λQ·M_Q + λEX·M_EX + λEY·M_EY` (con la combinación elegida).
  Vive en la parte de **análisis** (cargas → modelo → respuestas).
- **Capacidad** es el esfuerzo máximo que la sección puede resistir antes de fallar
  según su geometría, materiales y armadura: `M_u(N)`, `P_u(M)` (diagrama P–M).
  Vive en la parte de **diseño** (secciones por fibras).
- **Evaluación demanda/capacidad**: para cada `N` de la columna/muro se toma
  `M_u(N)` del diagrama P–M y se compara con `M_demanda`:

```
M_demanda ≤ M_u(N)        → cumple
M_demanda >  M_u(N)       → no cumple (reforzar sección)
```

En esta entrega la **primera evaluación demanda/capacidad** está implementada por
edificio como **evaluación algorítmica con sección de demostración**
(`src/capacidad_rc/demanda_capacidad.py`, estado `EVALUACION_ALGORITMICA_CON_SECCION_DEMO`):
`M_demanda` es la respuesta **EXPLICITA** de la superposición completa
(`1.0G+0.7Q+0.3EX−0.2EY`, misma corrida FE, sin interpolación de casos) y `M_u` se
toma del diagrama P–M interpolado `M_u(N)` de la sección `DEMO_RC_*` (armado de
demostración 12#25, marcado `HIPOTESIS_DEMOSTRACION`). Resultado: **Edificio I** y
**Edificio II**: todas las columnas evaluadas mediante el procedimiento (97 y 32)
quedan con D/C<=1 en comparación **aritmética** con capacidad de demostración;
columnas críticas EI col 208 (D/C=0,5373, nivel P4, extremo j) y EII col 25
(D/C=0,2572, nivel EII_CP3, extremo j). **No es comprobación de diseño y no
aprueba las columnas reales** (armadura real no documentada), pero el flujo
demanda→P–M→D/C está completo y es trazable (el JSON de cada edificio registra
edificio, elemento, nivel/extremo, combinación, P_u, M_demanda, capacidad
interpolada, sección, procedencia de parámetros y rango de interpolación).

## 4b. ¿Cómo se calculó el sismo pseudoestático (EX/EY)?

Por el método de la consigna (no normativo, clasificación
`PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA` en `config/sismo.json`):

```
W_i = PP_i + 0,50 · Q_i            (peso sísmico por nivel; fracción 0,50 de Q)
m_i = W_i / g
F_i = 0,20 · W_i                   (corte por nivel; a = 0,20g)
fn  = F_i · w_n / W_i              (distribución nodal proporcional al peso del nodo)
```

- Se aplica **una sola dirección por caso** (`+X` para EX, `+Y` para EY), fuerza
  horizontal por nivel, sin cargas gravitatorias en el caso sísmico (se combinan
  luego en la superposición), y sin unión EI–EII.
- Resultados de las 4 corridas (retcode 0): **EI** W=31.391,94 kN, F=6.278,39 kN;
  **EII** W=29.915,57 kN, F=5.983,11 kN. Momento accidental 0,0 kN·m, balance
  horizontal OK (residuo ~7e-8) y dirección exclusiva verificada por caso.
- **Sentido de deformada**: se verifica `Σ f·u` por nivel (dominante correcto). En
  EII la franja D-D′ (nodos fuera del diafragma rígido, x=−0,3/−3,35) presenta
  productos locales opuestos pequeños; el desplazamiento dominante del piso es el
  correcto y el check reporta la proporción de nodos opuestos como nota, sin abortar.
- Los parámetros normativos (zona, suelo, R, espectro) quedan `null`/PENDIENTE en
  `config/sismo.json`; no se declaran resultados sísmicos normativos.

## 5. Estado real de lo presentado (para no exagerar en la defensa)

Estados exactos por componente (definidos en `docs/PLAN_ENTREGA_03.md`).
**Las líneas de capacidad son demostración (no diseño real)**:

| Línea | Estado | Bloqueado por |
|---|---|---|
| Q — verificación `ΣQ=q_Q·A` + catálogo separado | `IMPLEMENTADO_Y_VERIFICADO` | — |
| Q — **caso FE Edificio I** (G ausente, equilibrio) | `IMPLEMENTADO_Y_VERIFICADO` | con q_Q=3,0 kN/m² (NCh 1537:2009 Tabla 4, mín. "Escuelas · salas de clases") |
| Q — caso FE Edificio II | `IMPLEMENTADO_Y_VERIFICADO` | modelo congelado G_EII; q_Q=3,0 (NCh 1537:2009) |
| EX/EY — parámetros y ejecución (4 corridas) | `IMPLEMENTADO_Y_VERIFICADO` | método de la consigna (a=0,20, 0,50·Q), no normativo; normativos `null` |
| Superposición (verificación completa G,Q,EX,EY vs EXPLICITA, por edificio) | `IMPLEMENTADO_Y_VERIFICADO` | conjunto demo `1.0/0.7/0.3/-0.2`; 8/8 magnitudes OK (máx rel 9,8e-16 EI / 1,7e-13 EII) |
| Superposición (verificación intermedia G+Q EI/EII) | `IMPLEMENTADO_Y_VERIFICADO_INTERMEDIO` | 3 corridas FE mismo modelo; 8/8 OK (máx rel 3e-15 / 4e-14) |
| Capacidad RC — Fiber Section | `IMPLEMENTADO_Y_VERIFICADO` | — |
| Capacidad RC — M–φ y P–M por edificio (70×70 real, 12#25 demo) | `IMPLEMENTADO_DEMO_ARBITRARIA` | armadura real no documentada → `HIPOTESIS_DEMOSTRACION`. EI f'c 40 → M_u=896,46 kN·m; EII f'c 35 → M_u=875,00 kN·m (aplastamiento hormigón eps_cu=0,004) |
| Evaluación demanda/capacidad (D/C) por edificio | `EVALUACION_ALGORITMICA_CON_SECCION_DEMO` | demanda EXPLICITA superpuesta + P–M interpolado con capacidad de demostración; EI critica col 208 (nivel P4, D/C 0,54), EII critica col 25 (nivel EII_CP3, D/C 0,26); sin validez de diseño ni aprobación estructural |
| Ejecutor único | `IMPLEMENTADO_Y_VERIFICADO` | `src/ejecutar_entrega_03.py`, estado global OK |
| Sección real (fy, recubrimiento, armadura) | `BLOQUEADO_POR_PARAMETROS` (no bloqueante) | armadura/fy/rec reales no documentados → resuelto con `DEMO_RC_*` marcadas |
| Peso sísmico `W` | `IMPLEMENTADO_Y_VERIFICADO` | EI 31.391,94 kN; EII 29.915,57 kN |
| Auditoría PP EII | `IMPLEMENTADO_Y_VERIFICADO` (9/9 checks; `G_EII` NO cerrado) | origen de la definición de muros (`PENDIENTE_ORIGEN_PIPELINE`) |

Regla de honestidad: **nada no documentado se presenta como real**; todo lo
arbitrario está marcado (`DEMOSTRACION_ARBITRARIA`, `PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA`,
`HIPOTESIS_DEMOSTRACION`) y aparece como tal en JSON y figuras. Preguntas para
destrabar: `docs/PREGUNTAS_PROFESOR_MIERCOLES.md`.