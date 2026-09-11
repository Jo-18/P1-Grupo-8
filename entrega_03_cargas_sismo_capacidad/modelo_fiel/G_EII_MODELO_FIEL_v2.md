# G_EII_MODELO_FIEL_v2 (MODELO_FIEL_2)

Clasificacion: **REPRODUCIBLE_CON_HIPOTESIS_Y_CARGAS_PENDIENTES**

Sin re-solve: reutiliza el pipeline reproducible V.60/80 = **25970.999 kN**.

- PP_losas: 9670.7583 kN
- PP columnas: 1522.3043 kN
- PP vigas (incl. V_031): 11585.4664 kN
- PP muros (pipeline): 3192.4703 kN
- PP_total: **25970.9993 kN**
- PM.ADIC aplicada: **0.00 kN** (catálogo A-F, todo PM_ADIC_PENDIENTE)
- Permanente aplicada: **25971.00 kN** = reproducible
- Q: 5259.4288 kN

## Solucion (artefacto checkpoint)

- P_z = 25970.9994 kN ; R_z = 25970.9994 kN ; residuo = 0.000000 kN ; OK

## Pendientes / no incluidos

- PM.ADIC (catálogo A-F del plano 2024_22-700) [PM_ADIC_PENDIENTE]: - kN | lineal Kg/m A=260 B=260 C=200 D=1500 E=260 F=260; sin mapeo familia->viga (DXF no incluido en la copia) -> aplicada = 0
- muros (publicado vs pipeline) [PENDIENTE_ORIGEN_PIPELINE]: 3328.79 kN | publicado 6521.26 vs pipeline A=t*(L/2) por montante 3192.47; identidad A=t*L por panel 4330.02
- losas (publicado vs aplicada) [PENDIENTE]: 6.27 kN | 
- ruteo sin camino estructural [PENDIENTE (14 cargas, no transferidas)]: 417.85 kN | 
- V_031 seccion alternativa [HIPOTESIS_MODELO]: - kN | 
- rigidLinks franja D-D' [HIPOTESIS (documentada)]: - kN | 

Total pendientes cuantificados: 3752.91 kN

Verificaciones v1: 6/6 OK
