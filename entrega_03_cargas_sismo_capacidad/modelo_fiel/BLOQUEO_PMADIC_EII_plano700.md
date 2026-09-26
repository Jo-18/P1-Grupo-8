# BLOQUEO PM.ADIC Edificio II - plano 700 (MODELO_FIEL_4)

**Estado:** `BLOQUEADO_FALTA_EVIDENCIA_POSICIONAL`

## Resumen

- Familias catalogadas (intensidades del catalogo EII): 6 (A-F).
- Estado por familia: **AMBIGUO_NO_APLICADO** (sin correspondencia familia->viga/nivel).
- PM.ADIC aplicada al FE del EII: **0 kN**. Cobertura: **0 %**.
- No se distribuye por proximidad ni se inventa mapeo.

## Catalogo (intensidades) y conversion

| Familia | Kg/m | kN/m (g=9.80665) |
|---|---|---|
| A | 260 | 2.549729 |
| B | 260 | 2.549729 |
| C | 200 | 1.96133 |
| D | 1500 | 14.709975 |
| E | 260 | 2.549729 |
| F | 260 | 2.549729 |

D = 1500 Kg/m -> 14.709975 kN/m (tramo/longitud desconocida).

## Donde se busco (solo lectura)

- **tree completo (glob) DXF/DWG/PDF/PNG/JPG/TIFF/SVG *:** 0 DXF/DWG/PDF en el arbol
- **datos/geometria/*.json:** referencias a DXF estructurales del EI 2017_67-101/102/103; nada del 700
- **analisis_estructural/edificio_II_casoG_PP_elementos/eii_viewer.json:** catalogo A-F de intensidades (PM_ADIC_lineal_kg_m y SC_lineal_kg_m); nota: 'plano 700 (DXF), catalogo por zona'; SIN posiciones por viga/nivel
- **analisis_estructural/edificio_II_casoG_PP_elementos/eii_esfuerzos.json:** caso G estructural; sin catalogo posicional
- **laboratorio_semana2/src/analisis/auditoria_xref_700.py:** auditoria CAD de metadatos del DXF 700 (XREF/bloques/INSERT/viewports); DXF referenciado en ruta EXTERNA; salidas: transformacion por nivel, SIN posiciones A-F
- **laboratorio_semana2/datos/cargas/*:** solo catalogo del edificio I (SC/PM.ADIC kgf/m2); nada del EII
- **laboratorio_semana2/datos/entradas_recibidas/edificio_II/2026-09-03/EII_2024_22/*:** figuras por nivel y ensayos CP2; sin catalogo del plano 700 con posiciones
- **viewer_unity/Assets/StreamingAssets/lab_data/edificios/II/*:** solo geometria EII_CP1..CP4; tributary y regiones_tributarias SOLO del edificio I
- **config/fuentes.json, README, docs/PLAN_*:** referencias documentales del plano 700; ninguna aporta posiciones

## Hallazgo fisico fuera del repo

- `2017_67-700.dxf` en `C:\Users\josef\OneDrive\Universidad\10mo Semestre\MCOC\Proyecto 1\Datos Estructurales\2017_67-700.dxf` (18,207,984 B; sha256 `F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF`).
- `Union PDF's Edificio II.pdf` en `Datos Estructurales\` (14,692,764 B; sha256 `4899A8B0033141FEB7F630F3AB8392ACBAEC364DE647BF7607C168B10D0CBB28`), incluiria la lamina 700 vectorial.
- Ambos fuera del repo: **no constituyen evidencia reproducible** de la entrega.

## Archivo exacto a solicitar

### Primario
- **`2017_67-700.dxf`** (sha256 `F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF`, 18,207,984 B), a versionar en `laboratorio_semana2/datos/entradas_recibidas/edificio_II/2026-09-03/EII_2024_22/00_planos/`.
- Requisitos para el mapeo: texto/leader `A`..`F` de PM.ADIC con su rango Kg/m, posicion de las polilineas de trama por zona con unidad, y la planta estructural embebida (`2017_67-101/102/103`) para la transformacion por nivel.

### Alternativo
- Paginas vectoriales de `Union PDF's Edificio II.pdf` correspondientes a la lamina 700 con las zonas A-F.

## Decision de MODELO_FIEL_4

- Mantener el mapeo v3 en `AMBIGUO_NO_APLICADO` (6/6 familias) con cobertura 0 %.
- **No** se regenera `G_EII` (25,970.9994 kN) ni el peso sismico EII (28,600.7138 kN).
- **No** se tocan EX/EY, superposicion ni D/C.

| Control | Valor |
|---|---|
| Familias AMBIGUO_NO_APLICADO | 6/6 |
| PM.ADIC aplicada (kN) | 0.0 |
| Cobertura | 0 % |
