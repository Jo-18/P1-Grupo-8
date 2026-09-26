# Auditoria PM.ADIC — EI (aplicada) y EII (catalogo pendiente)

## Edificio I — PM.ADIC aplicada en el checkpoint G

`datos/casos_analisis/correlacion_cargas_validada_5niveles.json`

Tipo: **superficial** (kgf/m2 correlacionadas, pm_avg -> kN/m2 con g=0.00980665). No hay cargas lineales en el EI.

| nivel | n losas | area neta (m2) | PM.ADIC (kN) | PP losa (kN) |
|---|---|---|---|---|
| CP1S | 3 | 387.03 | 1073.8500 | 1423.3023 |
| P1 | 16 | 1005.73 | 2814.7802 | 3698.5631 |
| P2 | 26 | 849.23 | 2143.6636 | 3123.0341 |
| P3 | 29 | 932.53 | 2344.6139 | 3371.1584 |
| P4 | 25 | 934.96 | 1867.2313 | 3367.5341 |

- CP1S: calculada 1073.8500 vs referencia 1073.85 -> OK
- P1: calculada 2814.7802 vs referencia 2814.78 -> OK
- P2: calculada 2143.6636 vs referencia 2143.66 -> OK
- P3: calculada 2344.6139 vs referencia 2344.61 -> OK
- P4: calculada 1867.2313 vs referencia 1867.23 -> OK
- TOTAL: calculada 10244.1390 vs referencia 10244.15 -> OK

PP losas total: 14983.59 kN; PM.ADIC total: 10244.1390 kN; GTG (PP losas + PM.ADIC): 25227.73 kN.

No doble conteo: `tributaria.calcular_cargas_nodales` mantiene `por_comp_kN.pp` (e*rho*area) y `por_comp_kN.pm_adic` (pm_kn_m2*area) como componentes separados; ambos se reparten por la misma malla pero nunca se suman dentro de un componente.

## Edificio II — PM.ADIC lineal catalogada (pendiente de mapeo)

| familia | PM.ADIC orig (Kg/m) | SC (Kg/m) | conv (kN/m) | estado | motivo |
|---|---|---|---|---|---|
| A | 260 | 500 | 2.549729 | PM_ADIC_PENDIENTE | sin correspondencia familia->viga/eje disponible en los datos recibidos: la leye |
| B | 260 | 300 | 2.549729 | PM_ADIC_PENDIENTE | sin correspondencia familia->viga/eje disponible en los datos recibidos: la leye |
| C | 200 | 200 | 1.961330 | PM_ADIC_PENDIENTE | sin correspondencia familia->viga/eje disponible en los datos recibidos: la leye |
| D | 1500 | 100 | 14.709975 | PM_ADIC_PENDIENTE | sin correspondencia familia->viga/eje disponible en los datos recibidos: la leye |
| E | 260 | 200 | 2.549729 | PM_ADIC_PENDIENTE | sin correspondencia familia->viga/eje disponible en los datos recibidos: la leye |
| F | 260 | 500 | 2.549729 | PM_ADIC_PENDIENTE | sin correspondencia familia->viga/eje disponible en los datos recibidos: la leye |

Checks EII:
- sum(PM_ADIC_aplicada) = 0.0000 kN (ninguna carga correlacionable con recepto confirmado).
- sum(q_lineal x longitud_confirmada) = 0.0000 kN (0 longitudes confirmadas).
- equilibrio de reacciones: N/A (carga aplicada nula).
- intensidad unitaria total del catalogo: 26.870221 kN/m (referencia; NO se multiplica por longitudes no confirmadas).
