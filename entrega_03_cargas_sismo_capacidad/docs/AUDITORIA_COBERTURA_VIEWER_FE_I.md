AUDITORIA DE COBERTURA VIEWER<->FE — EDIFICIO I

Estados: 1A1 | CONTENIDO | MULTIPLE (cobertura geo sin enlace) | SIN_RESULTADO_FE

Matriz por nivel y tipo (viewer = objetos visibles; FE = elementos del paquete):

nivel   tipo        v_total     v_1A1     v_CON     v_MUL     v_SIN    v_cov%   f_total     f_1A1     f_CON     f_MUL     f_SIN    f_cov%
-----------------------------------------------------------------------------------------------------------------------------------------
CP1S    columna           7         7         0         0         0     100.0        36         7         0         0        29      19.4
CP1S    viga              8         5         2         0         1      87.5         9         5         4         0         0     100.0
CP1S    muro              9         0         8         0         1      88.9        38         0        36         0         2      94.7
P1      columna          18        18         0         0         0     100.0        18        18         0         0         0     100.0
P1      viga             10         1         9         0         0     100.0        31         1        30         0         0     100.0
P1      muro              4         0         0         0         4       0.0         0         0         0         0         0       0.0
P2      columna          20        19         0         0         1      95.0        19        19         0         0         0     100.0
P2      viga             39        26        11         0         2      94.9        50        26        21         0         3      94.0
P2      muro              6         0         4         0         2      66.7         8         0         8         0         0     100.0
P3      columna          34        34         0         0         0     100.0        34        34         0         0         0     100.0
P3      viga             50        33        11         0         6      88.0        55        33        22         0         0     100.0
P3      muro              6         0         0         0         6       0.0         0         0         0         0         0       0.0
P4      columna          32         8         0         0        24      25.0         8         8         0         0         0     100.0
P4      viga             57        33        14         0        10      82.5        62        33        29         0         0     100.0
P4      muro              6         0         0         0         6       0.0         0         0         0         0         0       0.0

TOTALES  viewer: 306  -> 1A1=184 CONTENIDO=59 MULTIPLE=0 SIN_RESULTADO=63
TOTALES  FE    : 412  -> 1A1=184 CONTENIDO=150 MULTIPLE=0 SIN_RESULTADO=78

=== VIEWER -> FE ===
  SIN_RESULTADO_FE: 63
    CP1S  muro     M_EI_CP1S_003                                sec=                       tags=[]
    CP1S  viga     V_EI_CP1S_x1010_0.700-16.150                 sec=M.H.A. e=30            tags=[]
    P1    muro     M_EI_CP1_001                                 sec=                       tags=[]
    P1    muro     M_EI_CP1_002                                 sec=                       tags=[]
    P1    muro     M_EI_CP1_003                                 sec=                       tags=[]
    P1    muro     M_EI_CP1_004                                 sec=                       tags=[]
    P2    columna  COL_EI_CP2_RLE_PILAR_10.00_20.27             sec=0.30 x 0.30 (huella RLE-PILAR 2017_67-102) tags=[]
    P2    muro     M_EI_CP2_004                                 sec=                       tags=[]
    P2    muro     M_EI_CP2_005                                 sec=                       tags=[]
    P2    viga     H_EI_CP2_y2027_10.30-17.79_PLA2017-102       sec=V. 60/80               tags=[]
    P2    viga     V_EI_CP2_x1749_16.45-19.97_PLA2017-102       sec=V. 60/80               tags=[]
    P3    muro     M_EI_CP3_001                                 sec=                       tags=[]
    P3    muro     M_EI_CP3_002                                 sec=                       tags=[]
    P3    muro     M_EI_CP3_003                                 sec=                       tags=[]
    P3    muro     M_EI_CP3_004                                 sec=                       tags=[]
    P3    muro     M_EI_CP3_005                                 sec=                       tags=[]
    P3    muro     M_EI_CP3_006                                 sec=                       tags=[]
    P3    viga     H_EI_CP3_y1997_20.30-29.70                   sec=V. 60/80               tags=[]
    P3    viga     H_EI_CP3_y2057_19.70-30.30                   sec=V. 60/80               tags=[]
    P3    viga     V_EI_CP3_x1970_16.45-20.57                   sec=V.M. 300x300x5         tags=[]
    P3    viga     V_EI_CP3_x2030_16.45-20.57                   sec=V.M. 300x300x5         tags=[]
    P3    viga     V_EI_CP3_x2970_16.45-20.57                   sec=V.M. 300x300x5         tags=[]
    P3    viga     V_EI_CP3_x3030_16.45-20.57                   sec=V.M. 300x300x5         tags=[]
    P4    columna  COL_EI_CP4_C_E1_0.73                         sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_E2_0.75                         sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_E3_0.74                         sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_F1_10.74                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_F2_10.74                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_F3_9.24                         sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_G1_20.42                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_G2_20.73                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_G3_20.73                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_H1_30.71                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_H2_30.76                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_H3_29.21                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_I1_40.5                         sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_I2_38.87                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_I3_40.37                        sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_Ip1_44.24                       sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_Ip2_43.95                       sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_C_Ip3_44.52                       sec=P. 70x70               tags=[]
    P4    columna  COL_EI_CP4_S_J1_49.7935                      sec=P.M. 300x300x20 (huella piso4_103) tags=[]
    P4    columna  COL_EI_CP4_S_J2_49.7935                      sec=P.M. 300x300x20 (huella piso4_103) tags=[]
    P4    columna  COL_EI_CP4_S_J3_49.7935                      sec=P.M. 300x300x20 (huella piso4_103) tags=[]
    P4    columna  COL_EI_CP4_S_M1_47.4558                      sec=P.M. 300x300x20 (huella piso4_103) tags=[]
    P4    columna  COL_EI_CP4_S_M2_47.4558                      sec=P.M. 300x300x20 (huella piso4_103) tags=[]
    P4    columna  COL_EI_CP4_S_M3_47.4558                      sec=P.M. 300x300x20 (huella piso4_103) tags=[]
    P4    muro     M_EI_CP4_001                                 sec=                       tags=[]
    P4    muro     M_EI_CP4_002                                 sec=                       tags=[]
    P4    muro     M_EI_CP4_003                                 sec=                       tags=[]
    P4    muro     M_EI_CP4_004                                 sec=                       tags=[]
    P4    muro     M_EI_CP4_005                                 sec=                       tags=[]
    P4    muro     M_EI_CP4_006                                 sec=                       tags=[]
    P4    viga     D_EI_CP4_L800_D1_EJ1_44.919-47.456           sec=Diag. marco I'-J (elev 800) tags=[]
    P4    viga     D_EI_CP4_L800_D1_EJ2_44.919-47.456           sec=Diag. marco I'-J (elev 800) tags=[]
    P4    viga     D_EI_CP4_L800_D1_EJ3_44.919-47.456           sec=Diag. marco I'-J (elev 800) tags=[]
    P4    viga     D_EI_CP4_L800_D2_EJ1_49.793-47.456           sec=Diag. marco I'-J (elev 800) tags=[]
    P4    viga     D_EI_CP4_L800_D2_EJ2_49.793-47.456           sec=Diag. marco I'-J (elev 800) tags=[]
    P4    viga     D_EI_CP4_L800_D2_EJ3_49.793-47.456           sec=Diag. marco I'-J (elev 800) tags=[]
    P4    viga     TOWER_DIAG_P3_P4_EAST_3030_1645-2057_D1      sec=Diag. torre G-H (lamina 801/802) tags=[]
    P4    viga     TOWER_DIAG_P3_P4_EAST_3030_1645-2057_D2      sec=Diag. torre G-H (lamina 801/802) tags=[]
    P4    viga     TOWER_DIAG_P3_P4_WEST_1970_1645-2057_D1      sec=Diag. torre G-H (lamina 801/802) tags=[]
    P4    viga     TOWER_DIAG_P3_P4_WEST_1970_1645-2057_D2      sec=Diag. torre G-H (lamina 801/802) tags=[]
  MULTIPLE: (ninguno)

=== FE -> VIEWER ===
  SIN_RESULTADO_FE: 78
    CP1S     columna  tag=57   sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=64   sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=71   sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=78   sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=85   sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=92   sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=99   sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=106  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=113  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=120  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=127  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=130  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=133  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=136  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=139  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=142  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=145  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=148  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=151  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=154  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=157  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=160  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=163  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=166  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=169  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=172  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=175  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=178  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     columna  tag=181  sec=P. 70x70               fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     muro     tag=212  sec=M 0.15x1.52x2          fuente=SIN_CORRESPONDENCIA_VIEWER
    CP1S     muro     tag=215  sec=M 0.15x1.52x2          fuente=SIN_CORRESPONDENCIA_VIEWER
    P1       stub_elastico_rigidez_elevada tag=593  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P1       stub_elastico_rigidez_elevada tag=594  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P2       viga     tag=429  sec=V. 60/80               fuente=SIN_CORRESPONDENCIA_VIEWER
    P2       viga     tag=430  sec=V. 60/80               fuente=SIN_CORRESPONDENCIA_VIEWER
    P2       viga     tag=433  sec=V. 60/80               fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=657  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=661  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=665  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=669  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=673  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=677  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=681  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=685  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=689  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=693  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=697  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=701  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=705  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=709  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=713  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P3       stub_elastico_rigidez_elevada tag=717  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=602  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=605  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=608  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=611  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=614  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=617  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=620  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=623  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=626  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=629  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=632  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=635  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=638  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=641  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=644  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=647  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=650  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=653  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=721  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=725  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=729  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=733  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=737  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=741  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=745  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
    P4       stub_elastico_rigidez_elevada tag=749  sec=RIGIDA                 fuente=SIN_CORRESPONDENCIA_VIEWER
  MULTIPLE: (ninguno)
