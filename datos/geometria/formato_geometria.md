# Formato de entrada de áreas tributarias

El **contrato canónico** de datos de entrada del módulo de áreas tributarias es:

> `datos/geometria/esquema_entrada_areas_tributarias_v1.json`

Es un **JSON Schema** (draft 2020-12) que define la estructura de los archivos de
geometría de cada nivel (losas, vigas, muros, aberturas, bordes libres y cargas
superficiales). Todos los pisos reales y los casos de prueba deben cumplirlo.

El lector de entrada (`src/areas_tributarias/modelo.py`) interpreta este esquema.
Los casos de ejemplo están en `datos/casos_prueba/`.

---

## Estructura raíz del archivo de datos

Cada archivo JSON de geometría tiene esta forma general:

```json
{
  "version_formato": "1.0",
  "estado": "...",
  "proyecto": { "nombre": "...", "edificio": "...", "unidades": {...} },
  "sistema_coordenadas": { "origen": [0,0], "eje_x_positivo": "...", "eje_y_positivo": "..." },
  "nivel": { "id": "...", "cota": ..., "espesor_losa": ... },
  "configuracion_calculo": {
    "representacion_inicial": "...",
    "tamano_celda_inicial": ...,
    "tolerancia_geometrica": ...,
    "tolerancia_relativa_area": ...,
    "tolerancia_relativa_carga": ...,
    "generar_trazabilidad_celdas": ...
  },
  "losas": [
    {
      "id": "...",
      "espesor": ...,
      "poligono_exterior": [[x,y], ...],
      "aberturas": ["id_abertura_global", {"id":..., "poligono":[[x,y],...]}],
      "tipo_transferencia": "bidireccional" | "unidireccional" | "por_definir",
      "direccion_transferencia": [x,y] | null,
      "apoyos_validos": ["id_viga", "id_muro"]
    }
  ],
  "vigas": [
    { "id": "...", "inicio": [x,y], "fin": [x,y], "seccion": {...}, "recibe_losa": true }
  ],
  "muros": [
    { "id": "...", "eje": {"inicio":[x,y], "fin":[x,y]}, "espesor": ..., "recibe_losa": true }
  ],
  "aberturas_globales": [ { "id": "...", "tipo": "...", "poligono": [[x,y], ...] } ],
  "bordes_libres": [ { "id": "...", "inicio": [x,y], "fin": [x,y] } ],
  "cargas_superficiales": { "G_piso": { "valor": 5.0, "unidad": "kN/m2" } },
  "resultados_esperados_benchmark": { ... },
  "notas": [ "..."]
}
```

## Puntos a tener en cuenta

1. **Unidades**: longitud `m`, área `m²`, carga superficial `kN/m²`, carga lineal
   `kN/m`. El esquema las fija con `const`.
2. **Geometría directa**: los puntos son coordenadas `[x, y]` (no hay registros de
   nodos compartidos). Cada losa declara su `poligono_exterior`.
3. **Soportes**: un borde del polígono de una losa es **soportado** si coincide
   (dentro de la tolerancia geométrica) con una viga o muro con
   `recibe_losa: true`, o si figura en `apoyos_validos` de la losa. Un `borde_libre`
   NO recibe carga. Si un borde no coincide con ningún soporte ni es borde libre,
   se considera no soportado.
4. **Aberturas**: se referencian por id en `aberturas_globales`, o se declaran
   inline con su `poligono`. Reducen el área neta del paño.
5. **Transferencia**: en la fase actual el módulo implementa solo `bidireccional`
   (criterio 45°). `unidireccional` y `por_definir` quedan para fases posteriores;
   el cálculo rechaza `unidireccional` por ahora con un mensaje claro.

## Ejemplo

Ver el caso sintético `datos/casos_prueba/rectangulo_5x8_9.json`, que sigue este
esquema y sirve de validación del algoritmo.
