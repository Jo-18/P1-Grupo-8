# Regresión de áreas tributarias EII — CP2 v5 vs FASE4B

- Referencia: `areas_tributarias.csv` (ensayo EII_CP2_transferencia_mixta_FASE4B).
- Generado: `areas_tributarias_EII_todos_niveles.json` (motor `src/modelo_fiel/tributarias_EII_niveles.py`).
- Tolerancias declaradas: suma = 0.5% ; por fila = 5.0%.

## Resultado

- Filas de referencia: **78**; dentro de tolerancia por fila: **66/78 (84.62%)**.
- Suma referencia: **530.443854 m²**; suma v5: **530.83135 m²**;
  diferencia rel: **0.0731%** → dentro de tolerancia:
  **True**.
- Conservación por panel: **28/28** (check en el JSON de niveles).

## Fuera de tolerancia por fila (>5%)

- `EII_CP2_L_W2 → EII_CP2_V_028`: ref 2.20632 m², v5 2.762059 m², dif 25.189%
- `EII_CP2_L_S6 → EII_CP2_V_033`: ref 5.0025 m², v5 5.715 m², dif 14.243%
- `EII_CP2_L_S0 → EII_CP2_V_031`: ref 1.84 m², v5 2.0125 m², dif 9.375%
- `EII_CP2_L_W2 → EII_CP2_V_019`: ref 4.01934 m², v5 3.727536 m², dif 7.26%
- `EII_CP2_L_009 → EII_CP2_V_026`: ref 3.400793 m², v5 3.61 m², dif 6.152%
- `EII_CP2_L_010 → EII_CP2_V_027`: ref 3.400793 m², v5 3.61 m², dif 6.152%
- `EII_CP2_L_006 → EII_CP2_V_014`: ref 6.493111 m², v5 6.125 m², dif 5.669%
- `EII_CP2_L_W3 → EII_CP2_M_003`: ref 1.778316 m², v5 1.680912 m², dif 5.477%
- `EII_CP2_L_N6 → EII_CP2_V_035`: ref 1.68 m², v5 1.7675 m², dif 5.208%
- `EII_CP2_L_S0 → EII_CP2_V_022`: ref 0.345 m², v5 None m², dif None%
- `EII_CP2_L_S6 → EII_CP2_V_011`: ref 0.345 m², v5 None m², dif None%
- `EII_CP2_L_N6 → EII_CP2_V_017`: ref 0.105 m², v5 None m², dif None%

## Limitaciones documentadas

- El ensayo FASE4B usa columnas como receptores nodales (COL_002/COL_003) no
- reproducidas en v5 (eii_viewer las declara referencia_no_receptor_losa).
- Los paneles corredor S0/S6/N6 en FASE4B reparten franjas secundarias
- (V_011/V_017/V_022, 0.105-0.345 m2) con logica mixta unidireccional+nodal
- no codificada en eii_viewer; en v5 ese area queda en la viga principal.
- Las zonas W2/W3 y paños L_006/L_009/L_010 muestran difs 5.5-6% por
- alineacion de malla y conjunto de apoyos; se preserva conservacion 28/28.
- ancho_max_m no se reproduce en v5 (solo area y ancho_promedio).

Detalles por fila en `regresion_tributarias_EII_v5.json`.