# Reconciliacion del caso G - MODELO_FE_COMPLETO_FUNCIONAL (Edificio I)

La tabla siguiente lista las familias del peso propio y cargas permanentes del
caso G, verificadas contra el G_EI_MODELO_FIEL v3/v4. El G del modelo completo
debe coincidir con 42406.9577 kN; el checkpoint previo (losas + PM.ADIC) era
25227.73 kN. Desde el cierre 2026-09-14 (hito nucleo P2) los 4 paneles de muro
del nucleo (P2->P3) quedaron EXCLUIDOS del modelo definitivo por no tener apoyo
fisico documentado; su PP (330.0918 kN) se reporta como pendiente NO aplicado.

| Familia | Cantidad | Dimension | Peso unit. | Carga total (kN) | Como entra al caso G |
|---|---|---|---|---|---|
| Losas (PP estructural, espesor x gamma) | 99 losas | 4109.47 m2 netas | - | 13375.0464 | TB.calcular_cargas_nodales distribuye el PP estructural de cada losa (neta x h x gamma) en nodos receptores |
| PM.ADIC (superficial correlacionada) | 99 losas | 4109.47 m2 netas | - | 8903.9390 | idem losas con pm_kn_m2 correlacionado (el PP superficial de PM.ADIC esta dentro de la carga superficial; el PP estructural de losa es aparte) |
| Vigas (CONFIRMADO auditoria v2) | 137 vigas | None | A*L*24.5166 | 14803.5340 | aplicar_pp_nodal: mitad del PP en cada extremo, proporcional a longitud FE (nunca el nodo mas cercano); ids = detalle.vigas_confirmadas |
| Columnas (CONFIRMADO auditoria v2) | 43 tramos nl/S | None | A*L*24.5166 | 2045.6003 | idem aplicar_pp_nodal; ids = detalle.columnas_confirmadas (P1/P2/P3; las columnas P4 son PENDIENTE_TRAMO, fuera de la auditoria) |
| Muros (CONFIRMADO auditoria v2) | 4 paneles | None | A*L*24.5166 | 0.0000 | solo los paneles con montante FE aplican su PP; los 4 paneles del nucleo (P2->P3) quedaron EXCLUIDOS del modelo definitivo (sin apoyo fisico documentado) y su PP (330.0918 kN) se reporta como pendiente NO aplicado |
| CHECKPOINT G (losas + PM.ADIC) | - - | None | - | 22278.9854 | subtotal con el que corria el modelo antes de la reconciliacion + cargas de G_EI_MODELO_FIEL v1 |
| Postes de acero torre (HIPOTESIS, NO aplicado) | 25 ejes | 99.00 m L total | pendiente seccion real (hoy perfil metalico provisorio) | 0.0000 | 0 kN al G: seccion provisional HIPOTESIS y PP no confirmado (criterio identico al MODELO_FIEL v1) |
| Stubs rigid A->B (arranques/excentricidad) | 54 stubs | None | E*mult rigida | 0.0000 | 0 kN: dispositivo rigido sin masa propia; el peso del tramo real le corresponde a la columna/paño que conecta |
| Conectores rigidos P4 (A grilla -> B fisico) | 18 conectores | None | rigido | 0.0000 | 0 kN: excentricidad documentada; las columnas P4 que crean siguen PENDIENTE_TRAMO sin PP confirmado |
| TOTAL G MODELO_FE_COMPLETO_FUNCIONAL | - - | None | - | 39128.1197 | checkpoint + PP_el confirmado; objetivo igual al G_EI_MODELO_FIEL v3/v4 (42406.9577 kN) |
| Pendientes por falta de fuente (NO aplicado, regla usuario) | 27 receptores | None | - | 3278.8381 | 0 kN aplicados: (1) tributaria de losas sobre receptores de muros PENDIENTE_DE_FUENTE sin nodo FE (2948.7463 kN) + (2) PP de paneles de muro del nucleo EXCLUIDOS (330.0918 kN). No se traslada a montantes vecinos (regla): se reporta y se suma al G fiel solo para reconciliar |
| TOTAL G fiel (aplicado + pendientes no aplicadas) | - - | None | - | 42406.9578 | reconciliacion con el G_EI_MODELO_FIEL v3/v4 (42406.9577 kN): lo aplicado mas lo pendiente por falta de fuente, sin ajustes artificiales |
| Pendientes fuera del G (NO omitidos del reporte) | 4 diag torre | None | - | 0.0000 | TOWER_DIAG PENDIENTE_TORRE, V.S.I. provisional, contencion sotano, tramos base ficticios (por diseño no existen aqui); se reportan, no se suman al G |

## Totales

- G MODELO_FE_COMPLETO_FUNCIONAL (aplicado): **39128.1197 kN**
- Peso PENDIENTE por falta de fuente (NO aplicado, regla del usuario): 3278.8381 kN
  (27 receptores sin nodo FE: losas sobre muros PENDIENTE_DE_FUENTE + PP de
  paneles de nucleo excluidos; no se traslada a vecinos)
- TOTAL G reconciliado (aplicado + pendiente): 42406.9578 kN
- G_EI_MODELO_FIEL v3/v4 (referencia): 42406.9577 kN
- Delta: 0.0001 kN  (ok si |aplicado + pendiente - 42406.9577| < 0.2 kN)
- Checkpoint previo (losas + PM.ADIC): 22278.9854 kN
- PP de elementos CONFIRMADO (auditoria v2) aplicado: 16849.1343 kN
  - vigas: 14803.5340 (137) | columnas: 2045.6003 (43) | muros: 0.0000 (0 paneles en FE)
  - PP paneles de nucleo EXCLUIDOS -> pendiente: 330.0918 kN
- Match de ids de la auditoria contra la topologia FE: TRUE (137/43/muros coherentes)
- n ids aplicados como carga nodal: 180 (137 + 43 + 0 muros)

## Postes de acero de la torre y dispositivos rigidos

- Postes de acero (HIPOTESIS, no aplicados al G): 25 ejes, 99.00 m de longitud
  total; seccion provisional de perfil metalico, PP pendiente de seccion real.
- Stubs rigidos A->B: 54 (sin masa propia; el peso real es de la columna/paño).
- Conectores rigidos P4 (grilla->fisico): 18 (excentricidad documentada;
  columnas P4 siguen PENDIENTE_TRAMO sin PP confirmado).
- Pendientes fuera del G (reportados, no sumados): 4 diagonales de torre
  (PENDIENTE_TORRE), V.S.I. provisional, contencion sotano, tramos base
  ficticios (por diseno no existen aqui).

## Nota de omision / duplicacion

El PP_el confirmado se aplica una vez (matchers por id unico); losas y PM.ADIC son cargas superficiales sobre la misma losa, sin solaparse con el PP de elementos. Los 4 paneles de muro del nucleo P2->P3 quedaron EXCLUIDOS del modelo definitivo (sin apoyo fisico documentado) y su PP se reporta como pendiente NO aplicado. Ningun peso se ajusta artificialmente para cuadrar el total.

Densidades usadas por la auditoria v2: concreto 24.5166 kN/m3;
acero A36 (hipotesis) 76.9822 kN/m3.

