# Comparacion G v1/v2 y clasificacion corregida (MODELO_FIEL_2)

## EI
| concepto | v1 | v2 | nota |
|---|---|---|---|
| G antes (checkpoint: PP_losas + PM.ADIC) kN | 25227.7316 | 25227.7316 | sin cambios (identidad preservada) |
| PP elementos confirmados (vigas+col+muros) kN | 17179.2261 | 17179.2261 | sin cambios |
| G despues (permanente aplicada) kN | 42406.9577 | 42406.9577 | PP_total + PM.ADIC |
| PM.ADIC aplicada kN | incluida en G (no separada) | 10244.1389 | NUEVO: separada del PP (10.244,14 superficial) |
| PP_total (sin PM.ADIC) kN | no reportado | 32162.8188 | NUEVO: 14.983,59 losas + 17.179,23 elementos |
| Peso sismico total kN (v1 = 46.516,43) | 46516.4301 | 36272.2911 (A) / 46516.4301 (B) | el 46.516,43 v1 == escenario B (PP_total+PM.ADIC+0.5Q) |
| Diferencia A-B kN | - | -10244.139 | = PM.ADIC 10.244,15 |

## EII
| concepto | v1 | v2 | nota |
|---|---|---|---|
| G confirmado (reproducible) kN | 25970.9994 | 25970.9994 | sin cambios; sin re-solve |
| PP_total kN | no separado | 25970.9993 | losas 9.670,75 + elementos 16.300,25 |
| PM.ADIC aplicada kN | 0 (no incluida) | 0.0 | catálogo A-F completo, todo PM_ADIC_PENDIENTE |
| Peso sismico total kN | 28600.7138 | 28600.7138 (A) == 28600.7138 (B) | A == B por PM.ADIC=0 |
| Pendientes cuantificados kN | 3.752,91 | 3752.91 | muros 3.328,79 + losas 6,27 + ruteo 417,85 |

## Clasificacion corregida

### EI -> **REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES**

- v1: MODELO_FIEL_1 (se llamo 'fiel' en v1; denominacion RETIRADA en v2)
- Motivos:
  - PM.ADIC separada del PP solo en v2 (interpretacion de 'peso propio' pendiente de confirmacion)
  - tramos virtuales BASE->nivel (4.223,82 col + 3.675,18 muro)
  - muros de contencion del sotano (554,54 kN, hipotesis)
  - V.S.I. 20/150 y metalicos: PP no cuantificado

### EII -> **REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES**

- v1: MODELO_FIEL_1 (se llamo 'fiel' en v1; denominacion RETIRADA en v2)
- Motivos:
  - PM.ADIC catálogo A-F (lineal Kg/m) sin mapeo familia->viga (aplicada = 0)
  - muros: identidad A=t*(L/2) vs publicado (3.328,79 kN)
  - losas publicadas vs aplicadas (+6,27 kN)
  - ruteo sin camino estructural (417,85 kN, 14 cargas)
  - V_031 (seccion alternativa) y rigidLinks franja D-D' (hipotesis documentadas)

## Rango de clasificacion

- 0_BLOQUEADO: datos incompletos o con conflicto sin resolver
- 1_REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES: el caso se reproduce y esta en equilibrio; el recorte de componentes de PP (losas entrega, metalicos, V.S.I., muros de contencion, tramos base) puede subir el peso, manteniendo identidad de cargas
- 2_REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES: el caso se reproduce con hipotesis de modelo documentadas (secciones, rigidLinks, convencion de muros) y con cargas pendientes (PM.ADIC catalogada sin mapeo, losas/ruteo) que pueden cambiar el peso
- 3_FIEL: no usar hasta resolver PP y PM.ADIC y cerrar las hipotesis; los artefactos 'MODELO_FIEL_1' NO son fieles
