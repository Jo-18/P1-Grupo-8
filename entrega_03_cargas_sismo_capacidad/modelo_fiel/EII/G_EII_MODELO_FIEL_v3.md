# G_EII_MODELO_FIEL_v3 (MODELO_FIEL_3 / tarea 7)

Re-solve documentado (artefacto reproducible del checkpoint).

- PP_total: **25970.9993 kN** (losas 9670.7583 + elementos 16300.2410)
- PM.ADIC aplicada: **0.00 kN** (cobertura 0, mapeo AMBIGUO)
- Permanente aplicada: **25970.9994 kN**
- Q: 5259.4288 kN

## Solucion (artefacto)

- P_z = 25970.9994 ; R_z = 25970.9994 ; residuo = 0.000000 ; OK
- max|desplazamiento| = 0.01866325 m ; max|fuerza| = 2420.6503
- reacciones=147, desplazamientos=222, fuerzas local=264, global=264

## PM.ADIC (plancha 700, MODELO_FIEL_3)

- aplicada al FE: **0.00 kN** ; cobertura 0.0% ; catalogo 6 familias ; pendientes 6
-sin correspondencia familia->viga

## Verificaciones del artefacto

- suma_componentes_pp: ERROR
- identidad_cargas_vs_geometria: OK
- equilibrio_vertical: OK
- receptores_sin_fe: ERROR

- vs v2: 0.0000 -> IDENTICO_AL_v2
