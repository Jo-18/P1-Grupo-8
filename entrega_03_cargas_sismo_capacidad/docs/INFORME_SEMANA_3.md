# Informe Semana 3 — Entrega 03 (cargas, sismo, superposición, capacidad RC)

> Resumen ejecutivo del estado verificado de la entrega integral. Los números provienen
> de las corridas ejecutadas por `src/ejecutar_entrega_03.py` (estado global **OK**,
> 12 corridas) y de los JSON/CSV. Los JSON crudos regenerables viven en `results/`
> y `figures/` (ignorados por git); las **copias versionadas** están en `docs/tables/`
> y `docs/assets/` (los enlaces de este informe apuntan a esas copias).
> Acta numérica de cierre: [`docs/ACTA_VERIFICACION_FINAL.md`](ACTA_VERIFICACION_FINAL.md).

## 1. Lo que se hizo esta semana

1. **q_Q adoptado**: la sobrecarga de uso pasa de `null` a **q_Q = 2,0 kN/m²** por
   decisión del grupo (no existía valor en las fuentes). Queda registrado en
   `config/cargas.json`; EI → ΣQ = 8.218,9 kN (Δ 0,0), EII → 5.259,43 kN (rel 5,7e-09).
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
   ~1,9e-15 (EI) y ~2e-13 (EII); `config/superposicion.json`:
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
   D/C<=1 contra capacidad demo; críticas col 208 (D/C = 0,50) y col 25 (D/C = 0,26).
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
| Peso sísmico `W` = Σ(PP + 0,50·Q) | 29.337,20 kN | 28.600,71 kN |
| Corte basal `F = 0,20·W` | 5.867,44 kN | 5.720,14 kN |
| Verificación superposición completa | 8/8 OK (máx rel 1,9e-15) | 8/8 OK (máx rel 2e-13) |
| Sección columna (documentada) | P. 70×70 (f'c 40 MPa, G40 hipótesis) | P. 70×70 (f'c 35 MPa, G35 doc) |
| Armado | 12#25 (demo, rec 0,04 m, fy 420) | 12#25 (demo) |
| M_u(N=0) | 896,46 kN·m | 875,00 kN·m |
| D/C: columnas evaluadas / total | 97 / 97 (aritmético, sin validez de diseño) | 32 / 32 (aritmético, sin validez de diseño) |
| Columna crítica (nivel, extremo) | 208 (P4, j) D/C 0,5014 | 25 (EII_CP3, j) D/C 0,2583 |

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
| **Q (carga viva) y EX/EY (sismo)** | Q: `carga_viva_Q_*` con q_Q=2,0 adoptado, ΣQ=q_Q·A verificado por nivel/global ([tables/cargas/carga_viva_Q_I.json](tables/cargas/carga_viva_Q_I.json)). EX/EY: `caso_sismico_*` (4 corridas, retcode 0, corte basal `0,20·W`, equilibrio y sentido verificados, acta §1; [EX_I](tables/cargas/caso_sismico_EX_I.json)) |
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