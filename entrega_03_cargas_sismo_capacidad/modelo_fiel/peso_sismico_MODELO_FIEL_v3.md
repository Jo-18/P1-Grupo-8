# Peso sismico MODELO_FIEL_3 (tarea 8)

- B (PRINCIPAL): W_B = PP + PM_ADIC + 0.5*Q
- A (sensibilidad): W_A = PP + 0.5*Q

## EDIFICIO I
- B_PRINCIPAL: 46516.43 kN (4743.36 Mg) ; A_sensibilidad: 36272.29 kN (3698.74 Mg)
- vs v1: B 0.00 / A -10244.14 kN
- Rango B principal: [46516.43, 54969.98] ; A sensibilidad: [36272.29, 44725.84]
  - pendientes cuantificadas: +8453.55 kN (rango superior SOLO si se confirmaran tramos reales y cimentacion; NO se aplica (D3/D7))

| nivel | z (m) | G (kN) | Q (kN) | W_A (kN) | W_B (kN) | masa_B (Mg) | CM_B x/y (m) |
|---|---|---|---|---|---|---|---|
| sotano nucleo (z -7.01) | -7.01 | 172.78 | 52.21 | 122.11 | 198.88 | 20.28 | 10.899394 / -10.819 |
| CP1S | -4.01 | 3374.07 | 721.85 | 2737.92 | 3734.99 | 380.86 | 7.415598 / 1.99845 |
| P1 | -0.05 | 9854.05 | 2011.46 | 8045.00 | 10859.78 | 1107.39 | 25.840775 / 7.975636 |
| P2 | 3.91 | 9672.51 | 1698.46 | 8378.08 | 10521.74 | 1072.92 | 22.493128 / 8.264426 |
| P3 | 7.87 | 10246.53 | 1865.05 | 8834.45 | 11179.06 | 1139.95 | 25.094627 / 8.233534 |
| P4 | 11.83 | 9087.01 | 1869.91 | 8154.74 | 10021.97 | 1021.96 | 25.622269 / 8.248337 |

## EDIFICIO II
- B_PRINCIPAL: 28600.71 kN (2916.46 Mg) ; A_sensibilidad: 28600.71 kN (2916.46 Mg)
- vs v1: B 0.00 / A 0.00 kN
- Rango B principal: [28600.71, 32353.62] ; A sensibilidad: [28600.71, 32353.62]
  - pendientes cuantificadas: +3752.91 kN (muros 3.328,79 + losas 6,27 + ruteo 417,85 kN)

| nivel | z (m) | G (kN) | Q (kN) | W_A (kN) | W_B (kN) | masa_B (Mg) | CM_B x/y (m) |
|---|---|---|---|---|---|---|---|
| EII_CP1S | -4.01 | 4893.85 | 1062.04 | 5424.88 | 5424.88 | 553.18 | 10.503963 / 7.851121 |
| EII_CP1 | -0.05 | 5483.30 | 1062.04 | 6014.32 | 6014.32 | 613.29 | 10.516022 / 7.937521 |
| EII_CP2 | 3.91 | 5438.49 | 1062.22 | 5969.60 | 5969.60 | 608.73 | 10.414114 / 7.999419 |
| EII_CP3 | 7.87 | 5410.05 | 1062.04 | 5941.07 | 5941.07 | 605.82 | 10.335359 / 8.010607 |
| EII_CP4 | 11.83 | 4745.31 | 1011.08 | 5250.85 | 5250.85 | 535.44 | 10.271502 / 7.938049 |

## Verificaciones

- [OK] ei_wb_v1: EI escenario B == v1 (46.516,43)
- [OK] ei_wa_minus_wb_pm: EI W_A = W_B - PM.ADIC
- [OK] eii_ab_v1: EII A == B == v1 (28.600,71)
- [OK] eii_cm_eq: EII CM_A == CM_B (PM.ADIC 0)
- [OK] masa_recompute: masa = W / 9.80665
- [OK] ei_diff_ck_el: EI diff vs checkpoint (escenario B) = PP_elementos
- [OK] eii_diff_ck: EII diff vs checkpoint = 0
- [OK] v3_sin_nuevos_componentes: v3 == v1/v2 (EI 46.516,43 ; EII 28.600,71): ningun PP/P.M.ADIC nuevo confirmado (inventario/mapeo MODELO_FIEL_3)
- [OK] eii_pmadic_0: EII PM.ADIC aplicada = 0 (mapeo AMBIGUO, cobertura 0)
- [OK] pm_ei_total_documentado: PM.ADIC EI tabla v3 (10.244,139) == ledger (10.244,13...)
