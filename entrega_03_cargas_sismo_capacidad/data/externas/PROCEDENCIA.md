# Procedencia de datos externos mínimos copiados

Únicos dos archivos tomados de `laboratorio_semana2/` (no versionado). El resto del
pipeline lee exclusivamente de fuentes ya versionadas en el repositorio o de
artefactos regenerados por el propio ejecutor. No se copia la carpeta completa.

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

## Regla de mantenimiento

Si el pipeline requiere más insumos de `laboratorio_semana2/`, se copian aquí SIEMPRE de
forma mínima y con esta nota de procedencia; nunca se incorpora `laboratorio_semana2/` completa.