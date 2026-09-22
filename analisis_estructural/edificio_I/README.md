# Edificio I - Analisis estructural (laboratorio, reproduccion)

Analisis estructural gravitacional (caso G = PP losa + PM.ADIC correlacionado) del
Edificio I con OpenSeesPy. Resultado academico de laboratorio: NO utilizable para
diseno.

## Requisitos

Python 3.11 + paquetes de `requirements.txt` (verificado con openseespy 3.7.0.3,
numpy 2.4.6, shapely 2.1.2).

```powershell
pip install -r requirements.txt
```

## Reproducir el analisis

Desde la raiz de esta carpeta:

```powershell
set PYTHONPATH=src
python -m src.analisis.fe.main_fe
```

Entradas leidas (rutas relativas a la raiz de esta carpeta):

- `datos/candidatos/*.json` - geometria de los 5 niveles (CP1S, P1, P2, P3, P4)
- `datos/candidatos/matrices_transformacion_unity.json` - transformacion local->comun
- `datos/casos_analisis/correlacion_cargas_validada_5niveles.json` - carga superficial
  correlacionada por zona/losa

Salidas (en `resultados/modelo_estructural/`):

- `resultado_primera_ejecucion.json` - resumen, hipotesis, verificaciones, equilibrio
- `solucion_cruda_primera_ejecucion.json` - desplazamientos, reacciones, fuerzas por elemento

Herramientas auxiliares (misma carpeta `src/analisis/fe/`):

```powershell
python -m src.analisis.fe.exportar_esfuerzos_csv      # esfuerzos CSV
python -m src.analisis.fe.exportar_tramos_columnas    # tramos de columnas por nivel
python -m src.analisis.fe.exportar_regiones_tributarias
```

## Archivos de resultados publicados

| Archivo | Contenido |
|---|---|
| `resultado_primera_ejecucion.json` | modelo, hipotesis, verificaciones, balances |
| `solucion_cruda_primera_ejecucion.json` | desplazamientos, reacciones, esfuerzos por tag |
| `paquete_entrega_edificio_I.json` | paquete de entrega (viewer/trazabilidad) |
| `trazabilidad_losa_receptor_fe.json` | trazabilidad losa -> receptor -> nodo FE |
| `columnas_tramos_ei.json` | 97 tramos de columna (nivel, tag, nodos, cotas) |
| `esfuerzos_elementos_edificio_I.csv` | esfuerzos por elemento en ejes locales (349 filas) |

## Unidades

SI: `m`, `kN`, `kN/m2`, `kN/m`, `kN.m`. Convencion de signos OpenSees `localForce`:
N>0 traccion; ver `GUIA_ESFUERZOS_EDIFICIO_I.md` (misma carpeta de resultados en el
laboratorio).