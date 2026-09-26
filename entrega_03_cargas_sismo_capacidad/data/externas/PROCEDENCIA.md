# Procedencia de datos externos mínimos copiados

Tres archivos mínimos tomados de fuentes externas a la Entrega 3 (dos de
`laboratorio_semana2/`, uno de `viewer_unity/`; ninguno versionado como parte de
los artefactos de Entrega 3). El resto del pipeline lee exclusivamente de fuentes
ya versionadas en el repositorio o de artefactos regenerados por el propio
ejecutor. No se copian carpetas completas.

## 1. `catalogo_cargas_diseno_edificio_I.json`

- **Origen:** `laboratorio_semana2/datos/cargas/catalogo_cargas_diseno_edificio_I.json`
- **Uso:** bloque `catalogo_sobrecarga_documentada` del reporte Q del edificio I
  (carga catalogada en kgf/m2 **no aplicada**; la Q aplicada es la adoptada por el grupo, 2.0 kN/m2).
- **Tamaño:** 8970 bytes.
- **SHA-256:** `2CD90CABB35F26226FDD57AA8249ED33451F629C0D61AE5B7A3D8AA2D6958625`
- **Licencia/condición:** dato interno del laboratorio del curso (levantamiento
  "página 11"). Se copia tal cual, sin modificación, para reproducibilidad de la Entrega 3.

## 2. `areas_tributarias.csv`

- **Origen:** `laboratorio_semana2/datos/entradas_recibidas/edificio_II/2026-09-03/EII_2024_22/03_ensayos/CP2_transferencia_mixta_FASE4B/tablas/areas_tributarias.csv`
- **Uso:** geometría tributaria del nivel EII_CP2 (ensayo CP2 FASE4B, 1 kPa) para el
  reporte Q del edificio II; el resto de niveles queda `PENDIENTE_SIN_GEOMETRIA_TRIBUTARIA`.
- **Tamaño:** 6139 bytes.
- **SHA-256:** `54D98D404EA9F58AC2C7E333467F640723ADDF683890823FC32749DC0F8EE463`
- **Licencia/condición:** ensayo interno del laboratorio del curso. Copia sin modificación.

## 3. `por_viga.json`

- **Origen:** `viewer_unity/Assets/StreamingAssets/lab_data/edificios/I/tributary/por_viga.json`
- **Uso:** geometría tributaria línea→receptores del edificio I (áreas/masas por
  viga/muro por nivel, pesos nodales por longitud de segmento, Semana 2) para el
  reporte Q del edificio I y la suite de pruebas. Copia interna para que la Entrega 3
  corra sin depender de `viewer_unity/`.
- **Tamaño:** 63449 bytes.
- **SHA-256:** `7952CE51B1F822137028B013E61F21F4AF4E9438EDD32DB4C9340371627B0492`
- **Licencia/condición:** datos geométricos internos del laboratorio del curso
  (levantamiento Semana 2). Se copia tal cual, sin modificación; el original en
  `viewer_unity/` permanece intacto y en modo lectura.

## 4. `eii_viewer.json`

- **Origen:** `analisis_estructural/edificio_II_casoG_PP_elementos/eii_viewer.json`
  (artefacto versionado del repositorio).
- **Uso:** catálogo documentado de sobrecargas lineales del EII
  (`cargas.caso_G.SC_lineal_kg_m`, `Q_PP_LOSA_kPa`, etc.) para el bloque
  "catálogo documentado (no aplicado)" del reporte Q del edificio II y la suite de
  pruebas. Copia interna para que el reporte Q y los tests corran en aislamiento con
  una copia que contenga exclusivamente la Entrega 3 (los módulos del modelo fiel
  siguen consumiendo los artefactos versionados de `analisis_estructural/`).
- **Tamaño:** 249499 bytes.
- **SHA-256:** `C3435C7B23072A87D7F3931100C63B1669A1EBF24B9BCD997BED1CCB32446BB1`
- **Licencia/condición:** artefacto interno del repositorio del curso. Copia sin
  modificación; solo lectura de la fuente.

## 5. `areas_tributarias_EII_todos_niveles.json`

- **Origen:** REGENERADO por `src/modelo_fiel/tributarias_EII_niveles.py` a partir de
  `data/externas/eii_viewer.json` (copia interna, sección 4), replicando el método
  validado del ensayo `EII_CP2_transferencia_mixta_FASE4B` (malla de celdas,
  receptor = segmento finito más cercano de `apoyos_validos`, rayos unidireccionales
  en corredores S/N, renormalización a área neta). NO es copia de una fuente; es un
  derivado calculado con SHA-256 de su entrada en el propio archivo.
- **Uso:** áreas tributarias por viga de los niveles EII_CP1S, EII_CP1, EII_CP2,
  EII_CP3 y EII_CP4 para la aplicación de las cargas superficiales A/B/C/E/F
  (kg/m²) sobre las vigas receptoras en MODELO_FIEL_5.
- **Regresión:** contra `areas_tributarias.csv` (sección 2) documentada en
  `modelo_fiel/regresiones/regresion_tributarias_EII_v5.{md,json}` (suma dentro de
  tolerancia 0.5%; 66/78 filas ≤5%; 12 filas fuera con causa documentada, sin
  extrapolar automáticamente el CSV del ensayo).
- **Licencia/condición:** derivado del repositorio; la entrada `eii_viewer.json`
  permanece intacta y en modo lectura.

## Regla de mantenimiento

Si el pipeline requiere más insumos de `laboratorio_semana2/` o `viewer_unity/`, se
copian aquí SIEMPRE de forma mínima y con esta nota de procedencia; nunca se incorpora
`laboratorio_semana2/` ni el árbol de `viewer_unity/` completos.