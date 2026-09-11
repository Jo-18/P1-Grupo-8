# mapeo_PMADIC_EII_plano700 (MODELO_FIEL_3 / t.3-4-5)

Interpretacion de unidades: Kg/m leido como masa lineal * g, o como kgf/m esa misma unidad (1 kgf = 9.80665 N); ambos dan el mismo q_kN/m. NO se asume kN/m directo.

| familia | q (Kg/m) | q (kN/m) | leyenda | estado |
|---|---|---|---|---|
| A | 260 | 2.549729 | CP1S..CP3 (leyenda PLANTA DE CARGAS 'CIELO 1ºSUBTERRANEO a CIELO PISO 3º'); CP4 sin cubrir por la leyenda | **AMBIGUO_NO_APLICADO** |
| B | 260 | 2.549729 | CP1S..CP3 (leyenda PLANTA DE CARGAS 'CIELO 1ºSUBTERRANEO a CIELO PISO 3º'); CP4 sin cubrir por la leyenda | **AMBIGUO_NO_APLICADO** |
| C | 200 | 1.961330 | CP1S..CP3 (leyenda PLANTA DE CARGAS 'CIELO 1ºSUBTERRANEO a CIELO PISO 3º'); CP4 sin cubrir por la leyenda | **AMBIGUO_NO_APLICADO** |
| D | 1500 | 14.709975 | CP1S..CP3 (leyenda PLANTA DE CARGAS 'CIELO 1ºSUBTERRANEO a CIELO PISO 3º'); CP4 sin cubrir por la leyenda | **AMBIGUO_NO_APLICADO** |
| E | 260 | 2.549729 | CP1S..CP3 (leyenda PLANTA DE CARGAS 'CIELO 1ºSUBTERRANEO a CIELO PISO 3º'); CP4 sin cubrir por la leyenda | **AMBIGUO_NO_APLICADO** |
| F | 260 | 2.549729 | CP1S..CP3 (leyenda PLANTA DE CARGAS 'CIELO 1ºSUBTERRANEO a CIELO PISO 3º'); CP4 sin cubrir por la leyenda | **AMBIGUO_NO_APLICADO** |

Totales: catalogada=6, mapeada=0, aplicada_al_FE=**0.0 kN**, pendiente=6, cobertura=0.0%

Motivo unico: sin correspondencia familia->viga/eje disponible en los datos recibidos: la leyenda del plano no fija sobre que elemento lineal actua cada bloque y el DXF 2024_22-700 no esta incluido en la copia (solo se leyeron los bloques de leyenda). Longitud y receptor sin confirmar -> no se aplica.

## Receptores potenciales (contexto, no mapeo)

- EII_CP1S (cota -4.01): 35 vigas FE, 8 muros
- EII_CP1 (cota -0.05): 35 vigas FE, 8 muros
- EII_CP2 (cota 3.91): 35 vigas FE, 8 muros
- EII_CP3 (cota 7.87): 35 vigas FE, 8 muros
- EII_CP4 (cota 11.83): 35 vigas FE, 8 muros
- Total vigas FE en el modelo: 175

Figuras por nivel en `modelo_fiel/figuras_plano700/`.
