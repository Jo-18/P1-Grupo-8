# Peso sismico MODELO_FIEL_2: escenarios A y B por piso

- Escenario A: W_A = PP_total + 0.50*Q (excluye PM.ADIC)
- Escenario B: W_B = PP_total + PM_ADIC + 0.50*Q (= G completa + 0.5Q)

## EDIFICIO I
- A: 36272.29 kN (3698.74 Mg)   B: 46516.43 kN (4743.36 Mg)
- Diferencia A-B: -10244.14 kN (PM.ADIC)
- vs peso v1: B 0.00 / A -10244.14 kN
- Rango por pendientes (A): [36272.29, 44725.83] kN
- Rango por pendientes (B): [46516.43, 54969.97] kN
  - pendientes cuantificadas: +8453.54 kN (tramos virtuales BASE->nivel (columnas 4.223,82) + muros base 3.675,18 + contencion 554,54; NO incluye V.S.I. 20/150 ni metalicos (PP no cuantificado))

| nivel | z (m) | G (kN) | Q (kN) | W_A (kN) | W_B (kN) | masa_A (Mg) | masa_B (Mg) | CM_A x/y (m) | CM_B x/y (m) |
|---|---|---|---|---|---|---|---|---|---|
| sotano nucleo (z -7.01) | -7.01 | 172.78 | 52.21 | 122.11 | 198.88 | 12.45 | 20.28 | 10.897991 / -10.819 | 10.899394 / -10.819 |
| CP1S | -4.01 | 3374.07 | 721.85 | 2737.92 | 3734.99 | 279.19 | 380.86 | 7.138383 / 2.81203 | 7.415598 / 1.99845 |
| P1 | -0.05 | 9854.05 | 2011.46 | 8045.00 | 10859.78 | 820.36 | 1107.39 | 25.034503 / 8.395304 | 25.840775 / 7.975636 |
| P2 | 3.91 | 9672.51 | 1698.46 | 8378.08 | 10521.74 | 854.33 | 1072.92 | 22.548526 / 8.24796 | 22.493128 / 8.264426 |
| P3 | 7.87 | 10246.53 | 1865.05 | 8834.45 | 11179.06 | 900.86 | 1139.95 | 25.149932 / 8.219448 | 25.094627 / 8.233534 |
| P4 | 11.83 | 9087.01 | 1869.91 | 8154.74 | 10021.97 | 831.55 | 1021.96 | 25.907385 / 8.258956 | 25.622269 / 8.248337 |

## EDIFICIO II
- A: 28600.71 kN (2916.46 Mg)   B: 28600.71 kN (2916.46 Mg)
- Diferencia A-B: 0.00 kN (PM.ADIC)
- vs peso v1: B 0.00 / A 0.00 kN
- Rango por pendientes (A): [28600.71, 32353.62] kN
- Rango por pendientes (B): [28600.71, 32353.62] kN
  - pendientes cuantificadas: +3752.91 kN (muros 3.328,79 + losas 6,27 + ruteo 417,85 kN)

| nivel | z (m) | G (kN) | Q (kN) | W_A (kN) | W_B (kN) | masa_A (Mg) | masa_B (Mg) | CM_A x/y (m) | CM_B x/y (m) |
|---|---|---|---|---|---|---|---|---|---|
| EII_CP1S | -4.01 | 4893.85 | 1062.04 | 5424.88 | 5424.88 | 553.18 | 553.18 | 10.503963 / 7.851121 | 10.503963 / 7.851121 |
| EII_CP1 | -0.05 | 5483.30 | 1062.04 | 6014.32 | 6014.32 | 613.29 | 613.29 | 10.516022 / 7.937521 | 10.516022 / 7.937521 |
| EII_CP2 | 3.91 | 5438.49 | 1062.22 | 5969.60 | 5969.60 | 608.73 | 608.73 | 10.414114 / 7.999419 | 10.414114 / 7.999419 |
| EII_CP3 | 7.87 | 5410.05 | 1062.04 | 5941.07 | 5941.07 | 605.82 | 605.82 | 10.335359 / 8.010607 | 10.335359 / 8.010607 |
| EII_CP4 | 11.83 | 4745.31 | 1011.08 | 5250.85 | 5250.85 | 535.44 | 535.44 | 10.271502 / 7.938049 | 10.271502 / 7.938049 |

## Verificaciones

- [OK] ei_wb_v1: EI escenario B == v1 (46.516,43)
- [OK] ei_wa_minus_wb_pm: EI W_A = W_B - PM.ADIC
- [OK] eii_ab_v1: EII A == B == v1 (28.600,71)
- [OK] eii_cm_eq: EII CM_A == CM_B (PM.ADIC 0)
- [OK] masa_recompute: masa = W / 9.80665
- [OK] ei_diff_ck_el: EI diff vs checkpoint (escenario B) = PP_elementos
- [OK] eii_diff_ck: EII diff vs checkpoint = 0
