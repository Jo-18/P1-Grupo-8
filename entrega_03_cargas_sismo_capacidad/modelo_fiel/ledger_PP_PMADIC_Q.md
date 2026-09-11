# Ledger PP / PM.ADIC / Q por edificio y nivel (MODELO_FIEL_2)

Regla: `PP` = peso propio de elementos (losas, vigas, columnas, muros, otros) SIN PM.ADIC. `PM.ADIC` y `Q` en columnas separadas.

## EDIFICIO I
| nivel | PP_losas_kN | PM_ADIC_kN | PP_elementos_kN | Q | 0.5Q | W_A | W_B |
|---|---|---|---|---|---|---|---|
| CP1S | 1423.3023 | 1073.8500 | 1049.6913 | 774.0610 | 387.0305 | 2860.0241 | 3933.8741 |
| P1 | 3698.5632 | 2814.7801 | 3340.7096 | 2011.4586 | 1005.7293 | 8045.0020 | 10859.7821 |
| P2 | 3123.0343 | 2143.6637 | 4405.8150 | 1698.4580 | 849.2290 | 8378.0783 | 10521.7420 |
| P3 | 3371.1585 | 2344.6140 | 4530.7615 | 1865.0540 | 932.5270 | 8834.4470 | 11179.0610 |
| P4 | 3367.5344 | 1867.2312 | 3852.2488 | 1869.9130 | 934.9565 | 8154.7397 | 10021.9708 |
| **TOTAL** | 14983.5927 | 10244.1389 | 17179.2261 | 8218.9446 | 4109.4723 | 36272.2911 | 46516.4301 |


## EDIFICIO II
| nivel | PP_losas_kN | PM_ADIC_kN | PP_columnas_kN | PP_vigas_kN | PP_muros_kN | Q | 0.5Q | W_A | W_B |
|---|---|---|---|---|---|---|---|---|---|
| EII_CP1S | 1952.8277 | 0.0000 | 380.5761 | 2315.1516 | 871.1746 | 1062.0427 | 531.0214 | 5424.8759 | 5424.8759 |
| EII_CP1 | 1952.8277 | 0.0000 | 380.5761 | 2315.1516 | 798.3117 | 1062.0427 | 531.0214 | 6014.3199 | 6014.3199 |
| EII_CP2 | 1953.1495 | 0.0000 | 380.5761 | 2324.8601 | 761.4920 | 1062.2177 | 531.1089 | 5969.5964 | 5969.5964 |
| EII_CP3 | 1952.8277 | 0.0000 | 380.5761 | 2315.1516 | 761.4920 | 1062.0427 | 531.0214 | 5941.0687 | 5941.0687 |
| EII_CP4 | 1859.1258 | 0.0000 | 0.0000 | 2315.1516 | 0.0000 | 1011.0830 | 505.5415 | 5250.8529 | 5250.8529 |
| **TOTAL** | 9670.7583 | 0.0000 | 1522.3043 | 11585.4664 | 3192.4703 | 5259.4288 | 2629.7144 | 28600.7138 | 28600.7138 |

Nota EII: PM.ADIC = 0 aplicada (catálogo A-F completo en PM_ADIC_auditoria_EI_EII.*, todo PM_ADIC_PENDIENTE por falta de mapeo familia->viga). Por eso W_A == W_B.
Nota EII (conciliacion): las columnas `PP_columnas/PP_vigas/PP_muros` asignan cada elemento completo a su nivel (rec-nivel, igual que el ledger v1). La `G_aplicada_kN` reparte en nodos 50/50 a los extremos, por lo que en un piso `G != losas+col+vig+muros` (columnas/muros atraviesan el piso). Las sumas totales de ambos criterios coinciden (los 25.970,999 kN).

## Origen de los 46.516,43 kN del EI

25.227,73 (G checkpoint = PP_losas + PM_ADIC) + 17.179,23 (PP elementos confirmado auditoria v2) = 42.406,96 (G fiel) + 0.5*8218,94463 (4.109,47) = 46.516,43

**46.516,43 kN = PP_total + PM_ADIC + 0.5*Q (escenario B); NO es PP_total + 0.5*Q. Su lectura como 'peso propio' exige decisión del profesor. El escenario A (PP_total + 0.5*Q) da 36272.29 kN (diferencia = PM_ADIC 10244.14 kN).**
