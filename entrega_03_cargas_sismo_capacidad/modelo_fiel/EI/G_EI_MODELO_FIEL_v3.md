# G_EI_MODELO_FIEL_v3 (MODELO_FIEL_3 / tarea 7)

Re-solve real (OpenSeesPy, marco EI). Clasificacion: **REPRODUCIBLE_FULL_EXPORT_SIN_PP_PENDIENTES_NUEVOS**

- PP_total aplicado: **32162.8188 kN** (= losas 14983.5927 + elementos 17179.2261)
- PM.ADIC aplicada: **10244.1389 kN** (99 losas)
- Permanente aplicada (G_despues): **42406.96 kN**
- Q: 8218.9446 kN

## Solucion

- P_z = 42406.9577 ; R_z = 42406.9577 ; residuo = 0.000000 ; OK
- max|desplazamiento| = 0.15438370 m ; max|fuerza| = 2619.3381 (unidad de fuerza del FE)
- max_desp_z = 0.15438370 m

## Comparacion

- checkpoint (G_ck = losas + PM.ADIC): 25227.73 kN
- vs checkpoint: **+17179.2261 kN** (PP elementos)
- vs v2: 0.0000 kN -> IDENTICO_AL_v2

## PP pendiente (inventario MODELO_FIEL_3)

- Nuevo aplicado al FE: **0.00 kN**
- Pendientes: 63 ; hipotesis cuantificadas (no aplicadas): 8453.55 kN
- tramos virtuales BASE->nivel (col 4223.82 + muro 3675.18) NO aplicados
- muros de contencion del sotano (554.54) HIPOTESIS_CIMENTACION
- V.S.I. 20/150 de CP1S pp~157 kN NO confirmada (D5)
- tubulares 300x300x20/5: seccion confirmada, tramo PENDIENTE
- P.M.I. sin dimensiones; hormigon P3->P4 desfase +0.1813 m

## Export

- reacciones: 254 ; desplazamientos: 324 ; fuerzas por elemento: csv
- `EI/G_EI_MODELO_FIEL_v3_reacciones.csv`
- `EI/G_EI_MODELO_FIEL_v3_desplazamientos.csv`
- `EI/G_EI_MODELO_FIEL_v3_fuerzas.csv`

Verificaciones v1: 7/7 OK ; rc solver=0
