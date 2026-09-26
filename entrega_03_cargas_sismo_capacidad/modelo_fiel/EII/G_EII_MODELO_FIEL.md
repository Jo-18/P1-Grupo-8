# G_EII_MODELO_FIEL (primera iteracion)

Estado congelado: **G_EII_MODELO_FIEL_1**

G confirmado (reproducible V.60/80) = **25970.999 kN**

| componente | publicado (kN) | reproducible (kN) | dif (pub-pro) |
|---|---|---|---|
| losas (aplicada via mallado) | 9677.0267 | 9670.758325 | 6.26837455 |
| losas (directa geometria publicada) | None | 9670.748464 | None |
| vigas (incluye V_031) | 11585.48 | 11585.46643 | 0.0135704 |
| V_031 (subconjunto de vigas) | incluido en vigas | 179.461512 | no publicado por separado |
| columnas | 1522.31 | 1522.30434 | 0.00565952 |
| muros (pipeline A=t*(L/2) por montante) | 6521.26 | 3192.470257 | 3328.78974311 |

## Pendientes explicitos (NO aplicados)

- muros **3328.79 kN** (publicado 6521.26 vs pipeline 3192.47: A=t*(L/2) por montante (3.192,47); la identidad A=t*L por panel daria 4.330,02; deficit = 2.191,24 + 1.137,55 = 3.328,79)
- losas **6.27 kN** (discretizacion mallado/receptores sin FE)
- ruteo sin camino **417.85 kN** (14 cargas, tabla abajo)
- V_031 V.30/80 alternativo: {'escenario': 'V.30/80', 'estado': 'HIPOTESIS_MODELO (sin eleccion)', 'V60_80_kN': 11585.4664}
- rigidLinks franja D-D': {'n': 32, 'estado': 'HIPOTESIS (documentada, no resorte publicado)', 'nota': "16 rigidLink('beam'); 8 a 0.15 m sobre M_003_B/M_004_B (defensible) y 8 a 1.61-4.14 m (HIPOTESIS_ESTRUCTURAL)"}

## Verificaciones

- **identidad_componentes**: OK
- **equilibrio_vertical**: OK
- **coincide_con_checkpoint**: OK

Brecha global: publicado 29306.07 - fiel 25971.00 = **3335.07 kN**

## Tabla de los 14 ruteos SIN camino estructural confirmado

| n | origen | nivel | nodo | receptor | dist (m) | carga efe. (kN) | motivo |
|---|---|---|---|---|---|---|---|
| 1 | losa | EII_CP1 | 601038 | 601037 | 8.9006 | -44.302 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 2 | losa | EII_CP1S | 600001 | 600017 | 7.9610 | -18.331 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 3 | losa | EII_CP1S | 600002 | 600017 | 6.5386 | -18.331 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 4 | losa | EII_CP1S | 600006 | 600017 | 5.7189 | -10.331 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 5 | losa | EII_CP1S | 600007 | 600017 | 4.4870 | -12.753 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 6 | losa | EII_CP1S | 600038 | 600037 | 8.9006 | -44.302 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 7 | losa | EII_CP2 | 602040 | 602036 | 8.5530 | -24.016 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 8 | losa | EII_CP2 | 602041 | 602036 | 8.9028 | -33.507 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 9 | losa | EII_CP3 | 603038 | 603037 | 8.9006 | -33.507 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 10 | losa | EII_CP3 | 603042 | 603037 | 8.5530 | -24.016 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 11 | PP_elemento | EII_CP4 | 604032 | 604035 | 3.7708 | 52.367 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 12 | PP_elemento | EII_CP4 | 604032 | 604035 | 3.7708 | 42.659 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 13 | PP_elemento | EII_CP4 | 604032 | 604035 | 3.7708 | 29.420 | el segmento recto cruza un vano de losa (patio/hueco): sin c |
| 14 | PP_elemento | EII_CP4 | 604032 | 604035 | 3.7708 | 30.008 | el segmento recto cruza un vano de losa (patio/hueco): sin c |


