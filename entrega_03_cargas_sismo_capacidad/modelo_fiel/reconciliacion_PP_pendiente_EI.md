# Reconciliacion PP pendiente del Edificio I (MODELO_FIEL_4)

17 179,23 kN = COTA INFERIOR confirmada; las hipotesis base->nivel suman adicional 8 453,55 kN SOLO si se confirmaran tramos reales y cimentacion; no convertidas en carga aplicada

## Resumen por categoria

| Categoria | Conteo | PP cuantificado (kN) |
|---|---|---|
| elemento real con unidad FE pero seccion/material pendiente | 9 | 0.0 |
| seccion confirmada pero tramo continuado pendiente | 18 | 0.0 |
| hipotesis FE base->nivel / contencion (informativo, no aplica) | 4 | 8453.5488 |
| metalico tubular con seccion confirmada (tramo real pendiente) | 17 | 0.0 |
| muro con una sola planta documentada | 19 | 0.0 |
| no incluida por falta de evidencia | 1 | 0.0 |

## Conciliacion numerica

| Concepto | kN |
|---|---|
| PP confirmado (viga+columna+muro) | 17179.2261 |
| Pendientes cuantificados | 0.0 |
| Hipotesis base->nivel (informativo) | 8453.5488 |
| Rango real posible | 17179.2261 .. 25632.7749 |

## Chequeos

- 1_conteo_pendientes_63: **OK** (`columnas 43 + vigas 1 + muros 19`)
- 2_conteo_no_incluidas_1: **OK** (`1`)
- 3_total_filas_68: **OK** (`68 filas (63 pendientes + 1 no incl + 2 hipotesis + 2 contencion)`)
- 4_sin_id_repetido_confirmado_pendiente: **OK** (`{'conf_col': [], 'conf_viga': [], 'conf_muro': []}`)
- 5_P70_P4_continuacion_de_hormigon_confirmado: **OK** (`18/18 continuaciones en P1..P3 confirmadas`)
- 6_P70_no_tiene_doble_conteo_interno: **OK** (`cada P. 70x70 pendiente P4 tiene un unico id`)
- 7_conciliacion_numerica: **OK** (`{'PP_confirmado': 17179.2261, 'vigas': 14803.534, 'columnas': 2045.6003, 'muros': 330.0918}`)
- 8_hipotesis_solo_informativo_no_aplica: **OK** (`{'columnas': 4223.8204, 'muros': 3675.1844, 'contencion': 554.544, 'total_rango': 8453.5488}`)
- 9_determinismo_hash_v2: **OK** (`sha256 v2 coincide con el seed`)

## Tabla ID por ID (68 filas)

| # | Categoria | Simbolo / seccion | ID | Nivel | Tipo | pp/m (kN/m) | L (m) | pp (kN) | Continuacion | Estado |
|---|-----------|------|-----|-------|------|-------------|-------|---------|--------------|--------|
| 1 | C4_metalico_tubular_confirmado | P.M. 300x300x20 | col_18.96_14.79_base_P2 | P2 | columna_metalica | 1.7244 | None | None | - | PENDIENTE_TRAMO |
| 2 | C4_metalico_tubular_confirmado | V.M. 300x300x5 | col_46.35_0.55_base_P3 | P3 | columna_metalica | 0.4542 | None | None | - | PENDIENTE_TRAMO |
| 3 | C4_metalico_tubular_confirmado | V.M. 300x300x5 | col_46.36_9.32_base_P3 | P3 | columna_metalica | 0.4542 | None | None | - | PENDIENTE_TRAMO |
| 4 | C4_metalico_tubular_confirmado | V.M. 300x300x5 | col_46.34_16.61_base_P3 | P3 | columna_metalica | 0.4542 | None | None | - | PENDIENTE_TRAMO |
| 5 | C4_metalico_tubular_confirmado | V.M. 300x300x5 | col_48.68_0.55_base_P3 | P3 | columna_metalica | 0.4542 | None | None | - | PENDIENTE_TRAMO |
| 6 | C4_metalico_tubular_confirmado | V.M. 300x300x5 | col_48.7_9.32_base_P3 | P3 | columna_metalica | 0.4542 | None | None | - | PENDIENTE_TRAMO |
| 7 | C4_metalico_tubular_confirmado | V.M. 300x300x5 | col_48.9_16.61_base_P3 | P3 | columna_metalica | 0.4542 | None | None | - | PENDIENTE_TRAMO |
| 8 | C4_metalico_tubular_confirmado | V.M. 300x300x5 | col_20.38_18.28_base_P3 | P3 | columna_metalica | 0.4542 | None | None | - | PENDIENTE_TRAMO |
| 9 | C4_metalico_tubular_confirmado | V.M. 300x300x5 | col_30.4_18.37_base_P3 | P3 | columna_metalica | 0.4542 | None | None | - | PENDIENTE_TRAMO |
| 10 | C1_real_FE_seccion_pendiente | P.M.I. | col_47.78_-0.6_base_P3 | P3 | columna_metalica | None | None | None | - | PENDIENTE_SECCION |
| 11 | C1_real_FE_seccion_pendiente | P.M.I. | col_47.89_8.3_base_P3 | P3 | columna_metalica | None | None | None | - | PENDIENTE_SECCION |
| 12 | C1_real_FE_seccion_pendiente | P.M.I. | col_47.82_15.51_base_P3 | P3 | columna_metalica | None | None | None | - | PENDIENTE_SECCION |
| 13 | C1_real_FE_seccion_pendiente | P.M.I. | col_50.58_-0.6_base_P3 | P3 | columna_metalica | None | None | None | - | PENDIENTE_SECCION |
| 14 | C1_real_FE_seccion_pendiente | P.M.I. | col_50.82_8.61_base_P3 | P3 | columna_metalica | None | None | None | - | PENDIENTE_SECCION |
| 15 | C1_real_FE_seccion_pendiente | P.M.I. | col_50.71_15.85_base_P3 | P3 | columna_metalica | None | None | None | - | PENDIENTE_SECCION |
| 16 | C1_real_FE_seccion_pendiente | P.M.I. | col_20.5_20.72_base_P3 | P3 | columna_metalica | None | None | None | - | PENDIENTE_SECCION |
| 17 | C1_real_FE_seccion_pendiente | P.M.I. | col_30.51_20.66_base_P3 | P3 | columna_metalica | None | None | None | - | PENDIENTE_SECCION |
| 18 | C4_metalico_tubular_confirmado | P.M. 300x300x20 | col_45.97_1.36_base_P4 | P4 | columna_metalica | 1.7244 | None | None | - | PENDIENTE_TRAMO |
| 19 | C4_metalico_tubular_confirmado | P.M. 300x300x20 | col_48.77_7.46_base_P4 | P4 | columna_metalica | 1.7244 | None | None | - | PENDIENTE_TRAMO |
| 20 | C4_metalico_tubular_confirmado | P.M. 300x300x20 | col_51.97_8.12_base_P4 | P4 | columna_metalica | 1.7244 | None | None | - | PENDIENTE_TRAMO |
| 21 | C4_metalico_tubular_confirmado | P.M. 300x300x20 | col_52.11_15.23_base_P4 | P4 | columna_metalica | 1.7244 | None | None | - | PENDIENTE_TRAMO |
| 22 | C4_metalico_tubular_confirmado | P.M. 300x300x20 | col_48.73_17.3_base_P4 | P4 | columna_metalica | 1.7244 | None | None | - | PENDIENTE_TRAMO |
| 23 | C4_metalico_tubular_confirmado | P.M. 300x300x20 | col_21.5_21.03_base_P4 | P4 | columna_metalica | 1.7244 | None | None | - | PENDIENTE_TRAMO |
| 24 | C4_metalico_tubular_confirmado | P.M. 300x300x20 | col_31.55_21.03_base_P4 | P4 | columna_metalica | 1.7244 | None | None | - | PENDIENTE_TRAMO |
| 25 | C4_metalico_tubular_confirmado | P.M. 300x300x20 | col_52.08_-0.87_base_P4 | P4 | columna_metalica | 1.7244 | None | None | - | PENDIENTE_TRAMO |
| 26 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_E1_0.73 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 27 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_F1_10.74 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 28 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_H1_30.71 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 29 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_G1_20.42 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 30 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_I1_40.5 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 31 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_Ip1_44.24 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 32 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_E2_0.75 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 33 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_F2_10.74 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 34 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_G2_20.73 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 35 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_H2_30.76 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 36 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_I2_38.87 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 37 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_Ip2_43.95 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 38 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_E3_0.74 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 39 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_F3_9.24 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 40 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_G3_20.73 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 41 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_H3_29.21 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 42 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_I3_40.37 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 43 | C2_seccion_confirmada_tramo_pendiente | P. 70x70 | COL_EI_CP4_C_Ip3_44.52 | P4 | columna_hormigon | 12.0131 | None | None | SI | PENDIENTE_TRAMO |
| 44 | C1_real_FE_seccion_pendiente | V.S.I. 20/150 | H_EI_CP1S_y2732_0.200-21.600 | CP1S | viga | None | 21.4 | None | - | PENDIENTE_SECCION |
| 45 | C5_muro_una_sola_planta | e=0.7 m | M_EI_CP1S_003 | CP1S | muro | None | 16.951 | None | - | PENDIENTE_TRAMO |
| 46 | C5_muro_una_sola_planta | e=0.2 m | M_EI_CP1S_004 | CP1S | muro | None | 4.479 | None | - | PENDIENTE_TRAMO |
| 47 | C5_muro_una_sola_planta | e=0.2 m | M_EI_CP1S_005 | CP1S | muro | None | 4.479 | None | - | PENDIENTE_TRAMO |
| 48 | C5_muro_una_sola_planta | e=0.2 m | M_EI_CP1S_006 | CP1S | muro | None | 2.35 | None | - | PENDIENTE_TRAMO |
| 49 | C5_muro_una_sola_planta | e=0.2 m | M_EI_CP1S_007 | CP1S | muro | None | 2.35 | None | - | PENDIENTE_TRAMO |
| 50 | C5_muro_una_sola_planta | e=0.2 m | M_EI_CP1_001 | P1 | muro | None | 16.15 | None | - | PENDIENTE_TRAMO |
| 51 | C5_muro_una_sola_planta | e=0.3 m | M_EI_CP1_002 | P1 | muro | None | 17.08 | None | - | PENDIENTE_TRAMO |
| 52 | C5_muro_una_sola_planta | e=0.3 m | M_EI_CP1_003 | P1 | muro | None | 6.1 | None | - | PENDIENTE_TRAMO |
| 53 | C5_muro_una_sola_planta | e=0.15 m | M_EI_CP1_004 | P1 | muro | None | 3.05 | None | - | PENDIENTE_TRAMO |
| 54 | C5_muro_una_sola_planta | e=0.25 m | M_EI_CP2_004 | P2 | muro | None | 1.679 | None | - | PENDIENTE_TRAMO |
| 55 | C5_muro_una_sola_planta | e=0.25 m | M_EI_CP2_005 | P2 | muro | None | 1.679 | None | - | PENDIENTE_TRAMO |
| 56 | C5_muro_una_sola_planta | e=0.25 m | M_EI_CP3_004 | P3 | muro | None | 1.479 | None | - | PENDIENTE_TRAMO |
| 57 | C5_muro_una_sola_planta | e=0.25 m | M_EI_CP3_005 | P3 | muro | None | 1.479 | None | - | PENDIENTE_TRAMO |
| 58 | C5_muro_una_sola_planta | e=0.2 m | M_EI_CP4_001 | P4 | muro | None | 6.8 | None | - | PENDIENTE_TRAMO |
| 59 | C5_muro_una_sola_planta | e=0.3 m | M_EI_CP4_002 | P4 | muro | None | 2.15 | None | - | PENDIENTE_TRAMO |
| 60 | C5_muro_una_sola_planta | e=0.3 m | M_EI_CP4_003 | P4 | muro | None | 2.15 | None | - | PENDIENTE_TRAMO |
| 61 | C5_muro_una_sola_planta | e=0.25 m | M_EI_CP4_004 | P4 | muro | None | 1.578 | None | - | PENDIENTE_TRAMO |
| 62 | C5_muro_una_sola_planta | e=0.25 m | M_EI_CP4_005 | P4 | muro | None | 1.578 | None | - | PENDIENTE_TRAMO |
| 63 | C5_muro_una_sola_planta | e=0.2 m | M_EI_CP4_006 | P4 | muro | None | 3.45 | None | - | PENDIENTE_TRAMO |
| 64 | C6_no_incluida | M.H.A. e=30 | V_EI_CP1S_x1010_0.700-16.150 | CP1S | no viga (muro M.H.A. e=30) | None | 15.4502 | None | - | NO_INCLUIDA |
| 65 | C3_hipotesis_base_nivel | segun FE | HIPOTESIS_columnas_base_nivel | BASE->nivel | hipotesis FE base->nivel (columnas) | None | None | 4223.8204 | - | PENDIENTE_HIPOTESIS_FE |
| 66 | C3_hipotesis_base_nivel | segun FE | HIPOTESIS_muros_base_nivel | BASE->nivel | hipotesis FE base->nivel (muros) | None | None | 3675.1844 | - | PENDIENTE_HIPOTESIS_FE |
| 67 | C3_hipotesis_base_nivel | e=0.2 m, panel=25.25 m | M_EI_CP1S_001 | CP1S | muro de contencion del sotano | None | 25.25 | 371.4269 | - | HIPOTESIS_CIMENTACION |
| 68 | C3_hipotesis_base_nivel | e=0.3 m, panel=8.299 m | M_EI_CP1S_002 | CP1S | muro de contencion del sotano | None | 8.299 | 183.1171 | - | HIPOTESIS_CIMENTACION |
