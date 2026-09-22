# INFORME MODELO_FIEL_2 (clasificacion corregida y componentes)

Clasificacion provisional (NO llamar `fiel` a los casos v1):

- EI : **REPRODUCIBLE_CON_COMPONENTES_PP_PENDIENTES**
- EII: **REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES**

## Numeros clave

| concepto | EI (kN) | EII (kN) |
|---|---|---|
| PP losas | 14983.59 | 9670.76 |
| PM.ADIC | 10244.14 | 0.00 (aplicada) |
| PP total | 32162.82 | 25971.00 |
| Q | 8218.94 | 5259.43 |
| W_A (PP+0.5Q) | 36272.29 | 28600.71 |
| W_B (PP+PM.ADIC+0.5Q) | 46516.43 | 28600.71 |
| masa (esc.B) Mg | 4743.36 | 2916.46 |
| rango por pendientes | [46516.43, 54969.97] | [28600.71, 32353.62] |

## Pendientes cuantificadas

- EI: +**8453.54 kN** (tramos virtuales base 4.223,82+3.675,18; contencion 554,54; V.S.I. y metalicos sin cuantificar)
- EII: +**3752.91 kN** (muros 3.328,79; losas 6,27; ruteo 417,85; ver V_031 y rigidLinks franja D-D')

## Entregables de MODELO_FIEL_2

1. **Ledger PP/PM.ADIC/Q por edificio y nivel** — ledger_PP_PMADIC_Q.{json,csv,md} (columnas separadas; EI 6 bandas, 5 pisos con banda -7.01 integrada en CP1S)
2. **Origen del peso 46.516,43 kN del EI** — origen_46516_43_kN.{json,md} (G_ck 25.227,73 + PP 17.179,23 = 42.406,96 fiel; +0.5Q = 46.516,43 = escenario B)
3. **PM.ADIC del EII aplicada/pendiente** — PM_ADIC_auditoria_EI_EII.{json,md,csv} (catálogo lineal A-F; aplicada=0)
4. **Peso sismico escenarios A y B por piso (peso, masa, CM, rango, diff)** — peso_sismico_MODELO_FIEL_v2.{json,csv,md} (EI A=36.272,29/B=46.516,43; EII 28.600,71; masa = W/9.80665 Mg; CM por escenario)
5. **Comparacion G v1/v2** — comparacion_MODELO_FIEL_v2.{json,md}
6. **Clasificacion corregida** — clasificacion_MODELO_FIEL_v2.{json,md}
7. **Pruebas y regresiones** — regresiones_MODELO_FIEL_v2.json (26/26) + pytest tests/ (28/28) + manifest checkpoint valido
8. **Archivos modificados/nuevos** — src/modelo_fiel/*_v2.py + ledger_PP_PMADIC_Q.py; artefactos modelo_fiel/*_v2.* (ver git status)
9. **git status --short** — imprime el arbol de cambios sin commit

## Verificacion

- regresiones_v2: **26/26**
- pytest_tests: **28/28 (ver detalle regresiones_MODELO_FIEL_v2.json)**
- manifest_checkpoint: **OK**
- manifest_modelo_fiel: **39 archivos verificados OK**

No se ejecuta ninguna operacion Git (sin commit ni push); `git status --short` es un entregable aparte.
