# Geometría del Edificio de Ingeniería — importación a Unity

Contrato de datos de geometría (losas, vigas, muros, columnas, aberturas, bordes
libres y juntas) del **Edificio I**, pensado para **importación y visualización
en Unity** y navegación por nivel. **No es un formato ejecutable de análisis
estructural.**

- **Longitud:** metros (`unidad_longitud: "m"`).
- **Estado de los modelos:** `borrador_no_ejecutable`.
- **Transferencias de carga:** `por_definir` (se completan en una fase posterior).

## ¿Qué contiene el formato?

El contrato distingue tres cosas, que **no deben confundirse**:

1. **Geometría** (este repositorio publicable): losas, vigas, muros, columnas,
   aberturas, bordes libres y juntas por nivel, con sus coordenadas en metros.
2. **Cargas superficiales**: solo se declaran como casos de verificación interna
   del tipo 1 kPa (`G_prueba_tributacion_1kpa`); **no** se visualizan ni se
   interpretan como cargas de diseño para Unity.
3. **Resultados**: áreas tributarias, cargas lineales y reportes numéricos se
   generan con el pipeline interno y **no forman parte de esta publicación**.

## Modelos publicados

Niveles incluidos (ver `datos/geometria/indice_modelos.json`, ordenados por cota):

| Nivel | Cota (m) | Visualización | Cálculo estructural |
|---|---|---|---|
| Cielo Piso 1 Subterráneo | -4.01 | permitida | **no permitido** |
| Cielo Piso 1 | -0.05 | permitida | **no permitido** |
| Cielo Piso 2 | 3.91 | permitida | **no permitido** |
| Cielo Piso 3 | 7.87 | permitida | **no permitido** |
| Cielo Piso 4 | 11.83 | permitida | **no permitido** |

Cada modelo conserva `estado: borrador_no_ejecutable`, su hash SHA-256 en el
índice y `permitido_calculo_estructural: false`.

## Requisitos

- **Python mínimo:** 3.10.
- **Python recomendado:** 3.11.

Instalación de dependencias:

```bash
python -m pip install -r requirements.txt
```

## Validar un modelo (antes de usarlo)

Desde la raíz del repositorio:

```bash
python -m src.areas_tributarias.validar_formato datos/geometria/edificio_I_cielo_piso_2_borrador.json
```

- Salida `[OK]` y código de salida `0` ⇒ cumple el contrato.
- Código `2` ⇒ no válido / archivo inexistente.
- El esquema se busca en `datos/geometria/` si no se indica.

## Leer la geometría en Python

```python
from src.areas_tributarias import leer_geometria

modelo = leer_geometria(
    "datos/geometria/edificio_I_cielo_piso_2_borrador.json"
)
```

El lector **conserva** las secciones del contrato (losas, vigas, muros,
columnas, aberturas, bordes libres, juntas, interfaces y metadatos) pero **no
ejecuta cálculo estructural** sobre ellas.

### Clave canónica de columnas

`columnas_referencia` es la clave **canónica** de referencia espacial de
columnas por nivel. La clave `columnas` **solo** se admite como **compatibilidad
para archivos antiguos**; si un archivo trae `columnas` en lugar de
`columnas_referencia`, el lector lo acepta. Si un archivo trae **ambas** con
valores **distintos**, el lector lanza `ValueError` en lugar de elegir una en
silencio. Preferir siempre `columnas_referencia`.

## Contrato y plantilla

- Esquema canónico: `datos/geometria/esquema_entrada_areas_tributarias_v1.json`
  (JSON Schema, draft 2020-12).
- Documentación del formato: `datos/geometria/formato_geometria.md`.
- Plantilla para nuevos pisos/edificios:
  `datos/geometria/plantilla_entrada_geometria_v1.json` — **copiar y rellenar,
  sin modificar el archivo original**.

## Importador Unity

El formato usa diccionarios dinámicos, claves con prefijo `_`, valores `null` y
polígonos de longitud variable. **Se recomienda `Newtonsoft.Json`** (la
`JsonUtility` nativa no los maneja). El importador debe:

- usar **metros**;
- conservar los **IDs como texto**;
- **no interpretar** `null` / `por_definir` como cero;
- **no crear apoyos** ni cerrar aberturas;
- **no unir elementos** a través de las juntas de dilatación;
- **ignorar campos desconocidos**;
- emitir **error si `version_formato` es incompatible**.

## Junta Edificio I – Edificio II

La junta global `JD_EI_EII_10CM` (ancho 0.10 m) está **pendiente de
correlación geométrica** con el edificio II:

- `geometria_ensamblada: false`
- `caras_correlacionadas: false`
- `estado_correlacion_geometrica: "pendiente_json_edificio_II"`
- `contabilizacion: "una_sola_vez_en_modelo_conjunto"`

Unity no debe tratar la interfaz entre ambos edificios como ya cerrada.