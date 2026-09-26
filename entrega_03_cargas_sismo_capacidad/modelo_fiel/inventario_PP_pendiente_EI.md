# inventario_PP_pendiente_EI (MODELO_FIEL_3 / tarea 2)

PP confirmado (cota inferior): **17179.2261 kN**
PP provisional: 0.0000 kN ; PP pendiente: None ; no incluido: None

Pendientes: vigas 1, columnas 43, muros 19 ; no incluidas 1.

## Por metro (familias con seccion+densidad documentadas)

- P.M. 300x300x20 : 1.7244 kN/m
- V.M. 300x300x5 : 0.4542 kN/m
- P. 70x70 : 12.0131 kN/m

## Revisados y NO aplicados (hipotesis/falta de evidencia)

- Tramso base->nivel columnas: 4223.8204 kN (hipotesis FE)
- Tramos base->nivel muros: 3675.1844 kN (hipotesis FE)
- M_EI_CP1S_001 contencion: 371.4269 kN [HIPOTESIS_CIMENTACION]
- M_EI_CP1S_002 contencion: 183.1171 kN [HIPOTESIS_CIMENTACION]
- Total hipotesis cuantificadas (rango superior SI se confirmara la cimentacion): **8453.55 kN**

## Tabla

1. `H_EI_CP1S_y2732_0.200-21.600` viga nivel=CP1S V.S.I. 20/150 L=21.40 | estado=PENDIENTE_SECCION | decision=PENDIENTE_SECCION
2. `col_18.96_14.79_base_P2` columna metalica (tubular) nivel=P2 P.M. 300x300x20 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
3. `col_46.35_0.55_base_P3` columna metalica (tubular) nivel=P3 V.M. 300x300x5 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
4. `col_46.36_9.32_base_P3` columna metalica (tubular) nivel=P3 V.M. 300x300x5 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
5. `col_46.34_16.61_base_P3` columna metalica (tubular) nivel=P3 V.M. 300x300x5 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
6. `col_48.68_0.55_base_P3` columna metalica (tubular) nivel=P3 V.M. 300x300x5 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
7. `col_48.7_9.32_base_P3` columna metalica (tubular) nivel=P3 V.M. 300x300x5 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
8. `col_48.9_16.61_base_P3` columna metalica (tubular) nivel=P3 V.M. 300x300x5 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
9. `col_20.38_18.28_base_P3` columna metalica (tubular) nivel=P3 V.M. 300x300x5 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
10. `col_30.4_18.37_base_P3` columna metalica (tubular) nivel=P3 V.M. 300x300x5 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
11. `col_47.78_-0.6_base_P3` columna metalica (P.M.I.) nivel=P3 P.M.I. L=0.00 | estado=PENDIENTE_SECCION | decision=estado PENDIENTE_SECCION (no exiten BxHxt documentadas)
12. `col_47.89_8.3_base_P3` columna metalica (P.M.I.) nivel=P3 P.M.I. L=0.00 | estado=PENDIENTE_SECCION | decision=estado PENDIENTE_SECCION (no exiten BxHxt documentadas)
13. `col_47.82_15.51_base_P3` columna metalica (P.M.I.) nivel=P3 P.M.I. L=0.00 | estado=PENDIENTE_SECCION | decision=estado PENDIENTE_SECCION (no exiten BxHxt documentadas)
14. `col_50.58_-0.6_base_P3` columna metalica (P.M.I.) nivel=P3 P.M.I. L=0.00 | estado=PENDIENTE_SECCION | decision=estado PENDIENTE_SECCION (no exiten BxHxt documentadas)
15. `col_50.82_8.61_base_P3` columna metalica (P.M.I.) nivel=P3 P.M.I. L=0.00 | estado=PENDIENTE_SECCION | decision=estado PENDIENTE_SECCION (no exiten BxHxt documentadas)
16. `col_50.71_15.85_base_P3` columna metalica (P.M.I.) nivel=P3 P.M.I. L=0.00 | estado=PENDIENTE_SECCION | decision=estado PENDIENTE_SECCION (no exiten BxHxt documentadas)
17. `col_20.5_20.72_base_P3` columna metalica (P.M.I.) nivel=P3 P.M.I. L=0.00 | estado=PENDIENTE_SECCION | decision=estado PENDIENTE_SECCION (no exiten BxHxt documentadas)
18. `col_30.51_20.66_base_P3` columna metalica (P.M.I.) nivel=P3 P.M.I. L=0.00 | estado=PENDIENTE_SECCION | decision=estado PENDIENTE_SECCION (no exiten BxHxt documentadas)
19. `col_45.97_1.36_base_P4` columna metalica (tubular) nivel=P4 P.M. 300x300x20 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
20. `col_48.77_7.46_base_P4` columna metalica (tubular) nivel=P4 P.M. 300x300x20 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
21. `col_51.97_8.12_base_P4` columna metalica (tubular) nivel=P4 P.M. 300x300x20 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
22. `col_52.11_15.23_base_P4` columna metalica (tubular) nivel=P4 P.M. 300x300x20 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
23. `col_48.73_17.3_base_P4` columna metalica (tubular) nivel=P4 P.M. 300x300x20 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
24. `col_21.5_21.03_base_P4` columna metalica (tubular) nivel=P4 P.M. 300x300x20 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
25. `col_31.55_21.03_base_P4` columna metalica (tubular) nivel=P4 P.M. 300x300x20 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
26. `col_52.08_-0.87_base_P4` columna metalica (tubular) nivel=P4 P.M. 300x300x20 L=0.00 | estado=PENDIENTE_TRAMO | decision=pp null + PENDIENTE_TRAMO cuando la seccion tubular esta confirmada (solo falta el tramo)
27. `COL_EI_CP4_C_E1_0.73` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
28. `COL_EI_CP4_C_F1_10.74` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
29. `COL_EI_CP4_C_H1_30.71` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
30. `COL_EI_CP4_C_G1_20.42` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
31. `COL_EI_CP4_C_I1_40.5` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
32. `COL_EI_CP4_C_Ip1_44.24` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
33. `COL_EI_CP4_C_E2_0.75` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
34. `COL_EI_CP4_C_F2_10.74` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
35. `COL_EI_CP4_C_G2_20.73` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
36. `COL_EI_CP4_C_H2_30.76` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
37. `COL_EI_CP4_C_I2_38.87` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
38. `COL_EI_CP4_C_Ip2_43.95` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
39. `COL_EI_CP4_C_E3_0.74` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
40. `COL_EI_CP4_C_F3_9.24` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
41. `COL_EI_CP4_C_G3_20.73` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
42. `COL_EI_CP4_C_H3_29.21` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
43. `COL_EI_CP4_C_I3_40.37` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
44. `COL_EI_CP4_C_Ip3_44.52` columna de hormigon nivel=P4 P. 70x70 L=0.00 | estado=PENDIENTE_TRAMO | decision=PENDIENTE_TRAMO (desfase +0.181 m documentado; FE no instancia el tramo)
45. `(muro)` muro (1 sola planta documentada) nivel=CP1S sin seccion/espesor/cotas confirmados L=16.95 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
46. `(muro)` muro (1 sola planta documentada) nivel=CP1S sin seccion/espesor/cotas confirmados L=4.48 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
47. `(muro)` muro (1 sola planta documentada) nivel=CP1S sin seccion/espesor/cotas confirmados L=4.48 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
48. `(muro)` muro (1 sola planta documentada) nivel=CP1S sin seccion/espesor/cotas confirmados L=2.35 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
49. `(muro)` muro (1 sola planta documentada) nivel=CP1S sin seccion/espesor/cotas confirmados L=2.35 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
50. `(muro)` muro (1 sola planta documentada) nivel=P1 sin seccion/espesor/cotas confirmados L=16.15 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
51. `(muro)` muro (1 sola planta documentada) nivel=P1 sin seccion/espesor/cotas confirmados L=17.08 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
52. `(muro)` muro (1 sola planta documentada) nivel=P1 sin seccion/espesor/cotas confirmados L=6.10 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
53. `(muro)` muro (1 sola planta documentada) nivel=P1 sin seccion/espesor/cotas confirmados L=3.05 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
54. `(muro)` muro (1 sola planta documentada) nivel=P2 sin seccion/espesor/cotas confirmados L=1.68 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
55. `(muro)` muro (1 sola planta documentada) nivel=P2 sin seccion/espesor/cotas confirmados L=1.68 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
56. `(muro)` muro (1 sola planta documentada) nivel=P3 sin seccion/espesor/cotas confirmados L=1.48 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
57. `(muro)` muro (1 sola planta documentada) nivel=P3 sin seccion/espesor/cotas confirmados L=1.48 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
58. `(muro)` muro (1 sola planta documentada) nivel=P4 sin seccion/espesor/cotas confirmados L=6.80 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
59. `(muro)` muro (1 sola planta documentada) nivel=P4 sin seccion/espesor/cotas confirmados L=2.15 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
60. `(muro)` muro (1 sola planta documentada) nivel=P4 sin seccion/espesor/cotas confirmados L=2.15 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
61. `(muro)` muro (1 sola planta documentada) nivel=P4 sin seccion/espesor/cotas confirmados L=1.58 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
62. `(muro)` muro (1 sola planta documentada) nivel=P4 sin seccion/espesor/cotas confirmados L=1.58 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
63. `(muro)` muro (1 sola planta documentada) nivel=P4 sin seccion/espesor/cotas confirmados L=3.45 | estado=PENDIENTE_TRAMO | decision=ADOPTADA_PARCIAL: confirmar panel solo si coincidencia plena (linea+espesor+posicion+geometria+niveles consecutivos) P2->P3->P4; muro de un solo plano NO se vuelve tramo continuo automaticamente; cajas P4 M_CP4_001..006 mantienen PENDIENTE_TRAMO
64. `V_EI_CP1S_x1010_0.700-16.150` no viga (muro e=30 eje F) nivel=CP1S M.H.A. e=30 L=15.45 | estado=NO_INCLUIDA | decision=ADOPTADA: V_EI_CP1S_x1010 = muro eje F (no viga adicional); no-duplicacion con M_EI_CP1S_003 verificada (masa no sumada dos veces)
