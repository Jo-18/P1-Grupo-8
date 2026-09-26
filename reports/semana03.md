# Semana 3 — ENTREGA 03: cargas, sismo, superposición NCh 3171 y capacidad RC

**Entregable:** `reports/semana03.md` — **informe grupal** (no se atribuye a
integrantes individuales). Se deriva exclusivamente de los **archivos publicados en
este repositorio**, rama `entrega-03-modelos-fieles`.

Informe técnico completo: `entrega_03_cargas_sismo_capacidad/docs/INFORME_SEMANA_3.md`.
Acta numérica de cierre: `entrega_03_cargas_sismo_capacidad/docs/ACTA_VERIFICACION_FINAL.md`.
Plan y estado: `entrega_03_cargas_sismo_capacidad/docs/PLAN_ENTREGA_03.md`.

## 1. Versión del modelo y contexto

**Modelo FE verificado del entregable (perfil `MODELO_FE_COMPLETO_FUNCIONAL`):**

| | Edificio I | Edificio II |
|---|---|---|
| Nodos | 337 | 182 |
| Columnas | 115 | 32 |
| Vigas (incl. stubs EI) | 251 | 156 |
| Muros | 46 | 64 |
| **Elementos** | **412** | **252** |
| Vectores de esfuerzo exportados al viewer | 5.356 | 3.276 |

- Unidades SI: `longitud=m`, `area=m2`, `fuerza=kN`, `momento=kN.m`, `carga_superficial=kN/m2`.
- Convención de esfuerzos OpenSees `localForce` (12 valores por elemento,
  `N>0` compresión según contrato del exportador).
- Todas las corridas reportadas son **lineales estáticas** (`analyze_retcode = 0`,
  `solucion_ok = true`) y con **equilibrio verificado** (`equilibrio_ok = true`,
  `R_z = P_z`).

## 2. Los diez puntos de la consigna → evidencia

### P1. G, Q, EX y EY (cargas gravitacionales y sísmicas)

Payloads crudos en
`modelo_fiel/MODELO_FE_COMPLETO_FUNCIONAL/` (reproducibles desde los scripts de
`src/modelo_fiel/`):

| Caso | Edificio I `P_z/R_z` (kN) | Edificio II `P_z/R_z` (kN) |
|---|---|---|
| **G** (peso propio + PM.ADIC EI; EII sin PM.ADIC, bloqueado) | 42.406,96 | 25.341,54 |
| **Q** (sobrecarga de uso, q_Q = 3,0 kN/m²) | 12.328,42 | 7.568,13 |
| **EX** (`F_x = 0,20·W`, W = ΣPP+0,50·Q) | 9.714,23 | 5.825,12 |
| **EY** (idem, dirección Y) | 9.714,23 | 5.825,12 |

Verificaciones registradas en cada payload: `equilibrio_ok = true`,
`solucion_ok = true`, `R_z = P_z`. El caso G **EI** se reconcilia contra el modelo
fiel con Δ = 0,0 kN (`reconciliacion_G_EI.json`: 42.406,9577 = 42.406,9577, `ok_contra_fiel=true`).

### P2. Conservación de Q

`ΣQ = q_Q × A_neta` verificada por nivel y global:

- **EI:** `ΣQ = 12.328,42 kN`, `A_neta = 4.109,47 m²` → `3,0 × 4.109,47 = 12.328,42` (Δ 0,0).
- **EII:** `ΣQ = 7.568,13 kN` (área neta del perfil funcional; ver §7 coherencia de versiones).

`q_Q = 3,0 kN/m²` = mínimo de la categoría "Escuelas — salas de clases" de la
**Tabla 4 de la NCh 1537:2009** (`config/cargas.json`,
`PARAMETRO_BASADO_EN_NORMA_NCH1537_2009_TABLA4`).

### P3. Sismo pseudoestático (método de la consigna)

Parámetros: `a = 0,20·g`, `W_i = PP_i + 0,50·Q_i`, `F_i = 0,20·W_i`, distribución
nodal proporcional (mismo z en cada nivel). Clasificación:
`PARAMETROS_BASADOS_EN_EJEMPLO_DE_LA_CONSIGNA` (no normativos).

| | EI `W` (kN) | EI `F=0,20·W` (kN) | EII `W` (kN) | EII `F=0,20·W` (kN) |
|---|---|---|---|---|
| EX | 48.571,17 | 9.714,23 | 29.125,61 | 5.825,12 |
| EY | 48.571,17 | 9.714,23 | 29.125,61 | 5.825,12 |

`F_total_aplicada = F_total_esperado` (Δ 0,0) y `sum_por_nivel` OK por nivel en
los 4 payloads (`EX/EY_{EI,EII}_MODELO_FE_COMPLETO_FUNCIONAL.json`).

### P4. Tres comparaciones superposición normativa vs corrida OpenSees

Las **9 combinaciones NCh 3171** (U1..U4, EI y EII) se ejecutan como **corridas FE
explícitas** (`COMB_U*_*_{EI,EII}_MODELO_FE_COMPLETO_FUNCIONAL.json`,
18 archivos) y no como superposición post-proceso:

| Combo | Expresión |
|---|---|
| U1_GQ | `1,2G + 1,6Q` (gravedad) |
| U2_EX_POS/NEG | `1,2G + Q ± 1,4EX` |
| U3_EY_POS/NEG | `1,2G + Q ± 1,4EY` |
| U4_EX_POS/NEG | `0,9G ± 1,4EX` (descompresión/volteo) |
| U4_EY_POS/NEG | `0,9G ± 1,4EY` (descompresión/volteo) |

9 combinaciones `COMBINACIONES_NCH3171` de la **NCh3171.Of2008 (ed. 2021)** (sin
variantes 100%/30%; la antigua COMBINADA arbitraria `1,0G+0,7Q+0,3EX−0,2EY` de la
superposición demo queda **eliminada** del conjunto normativo — se conserva solo
como conjunto de demostración del §P4 para validar la superposición).

Cada payload confirma el corte basal aplicado (`COMB_U2_EX_POS_EI`:
`P_z = 63.216,77 kN`, `V_x = 13.599,93 kN = 1,4·EX`), equilibrio vertical/horizontal
OK y `solucion_ok = true` en EI y EII.

Comparación **superposición vs corrida explícita** (conjunto de demostración
`1,0G+0,7Q+0,3EX−0,2EY`): `docs/tables/superposicion/verificacion_superposicion_completa_{I,II}.json`
→ **8/8 magnitudes OK** con errores máx **~9,8e-16 (EI)** y **~1,7e-13 (EII)**
(errores de máquina). Figuras en `docs/assets/superposicion/*.png`.
Verificación unitaria matricial vs OpenSees: `tests/superposicion/test_combinacion.py`.

### P5. M–φ (curva momento–curvatura)

Fiber Section (malla hormigón + acero, cross-check OpenSeesPy):
`src/capacidad_rc/fiber_section.py`. `M_u(N=0)`: **EI = 896,46 kN·m** (f'c 40 MPa,
hipótesis G40) y **EII = 875,00 kN·m** (f'c 35 MPa, G35). Criterio de falla:
aplastamiento del hormigón (`eps_cu = 0,004`); las figuras marcan `M_u` en su `κ_u`.
Figuras: `docs/assets/capacidad_rc/DEMO_RC_{EI,EII}_m_phi.png`.

### P6. P–M columna (diagrama de interacción)

Envolvente P–M por edificio: `docs/assets/capacidad_rc/DEMO_RC_{EI,EII}_diagrama_pm.png`.
Se interpola `M_u(N)` para el D/C de P9. Sección real de columna 70×70 documentada;
**armadura de demostración 12#25** (rec 0,04 m, fy 420), `HIPOTESIS_DEMOSTRACION`
(armado real no documentado).

### P7. P–M muro — **PENDIENTE (no ejecutado en esta entrega)**

La curva P–M (y las Fiber Sections) de **muros** no está implementada
(`config/parametros_pendientes.json`: *"Fiber Sections de muro, curva P-M"*,
`necesario_para` pendiente). No se declara ningún resultado de capacidad de muro.
El P–M de esta entrega cubre **columnas** (§P6); el alcance de muros queda
registrado como trabajo no realizado — ver §6 "Pendientes".

### P8. Verificación RC (secciones por fibras)

- `src/capacidad_rc/fiber_section.py` + `tests/capacidad_rc/test_capacidad_rc.py`
  (**13 tests**: área conservada, sin tracción en acero, cross-check con
  OpenSeesPy, falla por `eps_cu`, etc.).
- Evidencia metodológica: `entrega_03_cargas_sismo_capacidad/docs/FIBER_SECTION_EVIDENCIA.md`.
- Secciones de fibras por edificio: `docs/assets/capacidad_rc/DEMO_RC_{EI,EII}_seccion_fibras.png`.

### P9. Demanda–capacidad

Estado `EVALUACION_ALGORITMICA_CON_SECCION_DEMO`: demanda = respuesta **explícita**
de la corrida FE de superposición; capacidad = `M_u(N)` interpolado del P–M demo.

| | Columnas evaluadas / total | Crítica | D/C |
|---|---|---|---|
| EI | 97 / 97 (100 % interpoladas) | col 208 (P4, extremo j) | 0,5373 |
| EII | 32 / 32 (100 % interpoladas) | col 25 (EII_CP3, extremo j) | 0,2572 |

0 columnas fuera de rango de interpolación de N.
**No válido como comprobación de diseño** (sección de demostración).
Evidencia: `docs/tables/capacidad_rc/demanda_capacidad_{I,II}.json` y
`resumen_demanda_capacidad.txt`.

### P10. Uso de IA

1. **Generación y auditoría del caso G y de la reconciliación** del modelo fiel
   (`modelo_fiel/`): el agente implementó `caso_G_EI/EII`, `informe_MODELO_FIEL_v4`
   y la `reconciliacion_G_EI` (Δ = 0,0 kN frente al modelo fiel).
2. **Combinaciones NCh 3171**: se redactaron y ejecutaron las 18 corridas
   explícitas (`src/modelo_fiel/combinaciones_nch3171.py`) y se verificó el corte
   basal aplicado por combo (`V = 1,4·EX` en U2, etc.).
3. **Verificación de superposición**: se re-implementó la comparación
   superposición vs corrida explícita y se reportaron los errores de máquina
   (~9,8e-16 / ~1,7e-13).
4. **Visualización del overlay en el viewer Unity**: el agente corrigió la doble
   transformación de las tuberías del overlay (malla local centrada en `mid`) y
   validó la geometría renderizada (`TOL_GEOM = 0,01 m`, error máx **0,0000 m**).
5. **Correspondencia viewer↔FE y selección por clic**: el agente implementó la
   selección por `correspondencia.viewer_id` (1A1 / CONTENIDO / SIN) y su auditor
   de invarianza (id/tipo/nivel) en clics reales de pantalla.
6. **Este informe**: redactado con apoyo del agente, contrastando cada número con
   el payload del repositorio (sin inventar resultados).

## 3. Viewer Unity: archivos activos y verificación

Overlay de esfuerzos FE integrado (exporter funcional autoritativo):

- Generador: `entrega_03_cargas_sismo_capacidad/src/unity_esfuerzos/exportar_esfuerzos_funcional_para_viewer.py`
  (22/22 chequeos internos OK por edificio; exporta el estado [412/252] con
  5.356/3.276 vectores; total 664 elementos / 8.632 vectores).
- Paquetes activos del viewer:
  `viewer_unity/Assets/StreamingAssets/lab_data/edificios/I/results/esfuerzos_FE_EDIFICIO_I.json`
  y `edificios/II/results/esfuerzos_FE_EDIFICIO_II.json`; declarados en
  `lab_data/manifest.json`.
- Runtime: `viewer_unity/Assets/Scripts/EsfuerzosController.cs` (auto-adjunto en
  `AfterSceneLoad`), `ViewerController.cs`, `LabViewerEditor.cs` (auditor batch).
- Suite funcional del viewer (**registrada hoy**):
  `python -X utf8 -m unittest tests.unity_esfuerzos.test_exportar_esfuerzos_funcional_viewer`
  → **17/17 OK (4,766 s)**.
- Regresión geométrica T1: `python -X utf8 tests/verif_remesh_t1.py` →
  **0 failures / 31**.

**Cobertura física del viewer (limitación documentada, en desarrollo):** la
visualización de *todos* los elementos físicos (tareas de mapeo por nivel, T2–T5)
está **en desarrollo**; `docs/cobertura_planes/INFORME_COBERTURA_FISICA.md`
corresponde a un estado previo del modelo (v. §7, nota de versiones) y no se
declara como cobertura física completa. Los clasificadores actuales por
"sin resultado" están en `docs/cobertura_planes/CLASIFICACION_SIN_{I,II}.json`
(EI: `{AUX_SEGMENTO_VERTICAL:32, PENDIENTE_DE_FUENTE:2, AUX_STUB:44}`; EII: `{}`).
El resto de este mapeo se completará en la siguiente iteración; **no se declara
cobertura física validada**.

## 4. Cómo reproducir

```bash
# Suite completa de la entrega 03 + laboratorio semana 2 (estado del ACTA: 28/28 OK)
python -X utf8 -m unittest discover -s tests -p "test_*.py"
# Ejecutor único del pipeline (Q, sismo EX/EY, verificación G+Q, superposición, capacidad RC, D/C)
python -X utf8 -m src.ejecutar_entrega_03
# Suite rápida registrada hoy (viewer funcional + remesh T1)
python -X utf8 -m unittest tests.unity_esfuerzos.test_exportar_esfuerzos_funcional_viewer
python -X utf8 tests/verif_remesh_t1.py
```

## 5. Coherencia de versiones (informe ↔ tablas ↔ resultados)

**Versión vigente del entregable:** perfil `MODELO_FE_COMPLETO_FUNCIONAL`
(EI 412 / EII 252) + vistas NCh 3171. Los **payloads** de `modelo_fiel/…` y los
**paquetes activos del viewer** corresponden a esta versión.

Discrepancias conocidas y declaradas (NO ocultadas):

| Magnitud | Valor vigente (funcional) | Copia previa en `docs/tables` | Causa |
|---|---|---|---|
| Q EI | 12.328,42 kN | 12.328,42 kN (Δ 0,0) | misma área neta |
| Q EII | **7.568,13 kN** | 7.889,14 kN | `docs/tables` generado con el perfil anterior (área neta EII distinta, modelo "congelado" 264 elementos) |
| G EII | 25.341,54 kN | 25.970,99 kN (modelo fiel v4, bloqueado PM.ADIC) | `PM.ADIC` EII bloqueado (`BLOQUEO_PMADIC_EII_plano700.json`) |
| Sismo EI `F` | 9.714,23 kN | 6.278,39 kN (ACTA) | ACTA sobre modelo congelado (W=31.391,94); vigente W=48.571,17 (reconciliado con el G fiel) |

Conclusión de la revisión explícita: el **informe nuevo
(`reports/semana03.md`), los payloads de `modelo_fiel` y los archivos activos del
viewer usan la misma versión (412/252 + NCh 3171)**. Las tablas de `docs/tables`
y partes del `INFORME_SEMANA_3.md` fueron generadas con el perfil anterior y se
mantienen como evidencia histórica; las secciones donde el número difiere del
vigente se señalan en esta tabla (la §7 del informe describe el overlay LEGACY
349/264, que fue reemplazado por el funcional 412/252).

## 6. Pendientes registrados (no bloquean el estado del entregable)

1. **P–M de muros y Fiber Sections de muro** (§P7) — trabajo no ejecutado.
2. Armadura real de columnas/muros, `fy` y recubrimiento (D/C deja de ser
   aritmético con sección demo).
3. Parámetros sísmicos normativos (zona, suelo, R, espectro) si el docente exige
   diseño por norma; coeficientes reales de superposición (hoy el conjunto de
   demostración `1,0G+0,7Q+0,3EX−0,2EY`).
4. PP EI (v2 cota inferior) y cierre del G_EII (PM.ADIC, plano 700 a solicitar).
5. Cobertura física completa del viewer (T2–T5) — en desarrollo.
6. Franja D-D′ EII en el chequeo de sentido (nota en `caso_sismico_EY_II.json`).

## 7. Limitaciones de alcance

- Sismo por el **método de la consigna** (no normativo); no se declaran resultados
  sísmicos normativos.
- M–φ, P–M y D/C con **secciones de demostración** (`HIPOTESIS_DEMOSTRACION`):
  demuestran el flujo de integración, **no certifican columnas ni edificios**.
- Las 6 figuras de capacidad llevan la advertencia visible
  `DEMOSTRACIÓN — SECCIÓN HIPOTÉTICA, NO VÁLIDA PARA DISEÑO`.
- El viewer muestra esfuerzos FE verificados (overlay), pero la **cobertura física
  completa** (visualización de todos los elementos) está en desarrollo (§3).