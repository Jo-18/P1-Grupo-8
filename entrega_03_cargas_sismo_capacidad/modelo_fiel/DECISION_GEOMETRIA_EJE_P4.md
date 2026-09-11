# Decisión documentada: eje P4 del Edificio I (16.15 vs 16.331)

Fecha: 2026-09-10 · Rama: `entrega-03-modelos-fieles` · Estado: **decisión adoptada para MODELO_FE_COMPLETO**
(sin tocar aún el modelo FE; este documento es el insumo previo).

## 1. Contexto

La auditoría de cobertura viewer→FE mostró que el desajuste dominante del EI (148 elementos SIN de 149)
se concentra en el nivel P4 y en la zona norte (eje 3): columnas P3 34/34 SIN y vigas P4 46/57 SIN.
La causa raíz es la existencia de **dos lecturas de grilla** para el plano del cielo del piso 4
(lámina 2017_67-103): una en la grilla dimensional (v = 16.15) y otra en los centros físicos de los
elementos dibujados (v = 16.331).

## 2. Fuentes consultadas

| Archivo | Lámina | Capa / objeto | Qué aporta |
|---|---|---|---|
| `datos/geometria/edificio_I_cielo_Piso_4_borrador.json` | 2017_67-103.dxf | notas de conversión | Origen E-1 en (0,0); conversión `x_m=(DXF_X-490.3)/100`, `y_m=(6297.3-DXF_Y)/100`; escala 100 DWG-un./m |
| `datos/geometria/edificio_I_cielo_Piso_4_borrador.json` | 2017_67-103.dxf | RLE-EJE | Marcas de eje en `Y=6297.3(1)`, `5407.3(2)`, `4682.3(3)` → grilla **0 / 8.9 / 16.15** m |
| `analisis_estructural/edificio_I/datos/candidatos/edificio_I_cielo_piso_4_candidata_unity.json` | 2017_67-103.dxf | RLE-SOLID (_candidata_unity.evidencia_columnas) | Centros físicos de **las 18 columnas** de concreto en `v = grilla + 0.1812` (handles 1E206, 1E202, …). Ej.: E1 (0.0003, 0.1812), I3 (40.0003, 16.3314). |
| `laboratorio_semana2/datos/candidatos/correccion_vigas_perimetrales_P4/P4_candidata_vigas_perimetrales.json` | 2017_67-103.dxf | `_candidata` (2026-09-03) | `correccion_grid_longitudinal_P4`: traslación +0.18 en v de todo el grid de vigas (y0000/y0089/y0162 y 11 transversales V) a **0.18 / 9.08 / 16.33**; alero norte **0.23 → 0.05 m**; "Análisis FE previo NO revalidado para esta geometría". |
| `datos/geometria/edificio_I_cielo_Piso_{1,3}_borrador.json` + viewer/FE | 2017_67-101 / 2017_67-102 | RLE-PILAR / RLE-TEXTO-1 | P1 y P3 en **grilla 0/8.9/16.15** (puntos de control P2: 18 refs en ejes 0/8.9/16.15; P3: 34 refs). Sin desfase documentado en niveles inferiores. |
| `entrega_03_cargas_sismo_capacidad/src/modelo_fiel/reconciliar_PP_pendiente_EI.py` (línea ~98) | reconciliación PP | — | Regla de continuación P.70x70: `abs((c.v + 0.181) − v) < 0.05`; check 5_`P70_P4_continuacion_de_hormigon_confirmado` **18/18** OK. |

## 3. Hechos establecidos

1. La grilla dimensional de 2017_67-103 (RLE-EJE) da **v = 0 / 8.9 / 16.15** (ejes 1–3).
2. Los **centros físicos** de las 18 columnas de concreto en 2017_67-103 (RLE-SOLID) están a
   **v = 0.1812 / 9.0812 / 16.3314** (grilla + 0.1812 m), con handle DXF individual por columna.
3. Las **vigas** del P4 en 2017_67-103 (RLE-VIGA, corregidas 2026-09-03) se alinean con esos centros
   (**+0.18 m**: y0000=0.18, y0089=9.08, y0162=16.33). Con esa alineación el vuelo norte queda en
   **0.05 m** (lectura físicamente coherente: viga de borde casi a ras de las columnas).
4. P1–P3 (2017_67-101/102) están en **grilla** (sin desfase documentado); las columnas P.70x70
   continuas P1…P3 llegan a la cota 11.83 (losa de P4) en (u, 0/8.9/16.15).
5. El viewer P4 (geometry `P4.json`) y las columnas FE `P4` (tags 148–178 y 189–232, rangos z
   −4.01→11.83 y 11.83→nombre) ya usan la rejilla **corregida +0.181** en columnas.
6. Las vigas FE previas del P4 quedaron en **grilla 16.15** (ajadas del grid previo) → 41 SIN que la
   manifestación candidata llama "41 vigas trasladadas", es decir, **debían estar en +0.18**.

## 4. Decisión adoptada

Para el `MODELO_FE_COMPLETO` del Edificio I, nivel P4 (cielo piso 4, cota 11.83):

- **Columnas y vigas del P4 se modelan en el eje físico documentado**
  `v = 0.1812 / 9.0812 / 16.3314` (redondeadas 0.18 / 9.08 / 16.33), que es el `RLE-SOLID`/`RLE-VIGA`
  de 2017_67-103. La grilla RLE-EJE (16.15) es **referencia dimensional**, no centro físico.
- **Continuidad P3→P4**: las columnas de concreto P.70x70 del P3 (z 7.87→11.83) permanecen en
  **grilla (u, 0/8.9/16.15)**, y el segmento P4 (sobre 11.83) sigue en el eje físico +0.1812
  (desfase registrado de 0.1812 m entre la prolongación de la grilla y el eje físico del plano de P4).
  La reconciliación 18/18 ya asume este desfase.
- **No se da de alta `COL_EI_CP3_C_I3_40.0` como elemento nuevo en (40, 16.331, 7.87–11.83)**:
  no hay tramo FE pendiente en ese eje; el tramo real entre 7.87 y 11.83 va en (40, 16.15).
- **Vigas P4**: 41 vigas de y0000/y0089/y0162 (+ 11 transversales de V) se colocan en +0.18/9.08/16.33;
  las vigas de borde N quedan a v=16.33 con vuelo 0.05 m.
- **Elementos sobre la cubierta**: P.M. con huella `piso4_103` (6) y diagonales de marco/torre (10)
  siguen siendo estructurales; su cota superior (marco I'–J elev 800, torre G–H 801/802) se fijará
  con las láminas de elevación antes de correr el modelo (ítem de geometría pendiente, ver §6).

## 5. Verificación impuesta

- Node/coordinates check: cada elemento confirmado con ID estable, nodos i/j, nivel, sección+material,
  transformación y correspondencia viewer (id) en el inventario.
- Equilibrio por caso (G, Q, EX, EY) y cortes basales; forma deformada y convergencia.
- Matrices viewer→FE y FE→viewer antes/después: el objetivo es 100% de `ESTRUCTURAL_CONFIRMADO` con
  resultado; los SIN deben quedar en 0 para los confirmados.

## 6. Pendientes de fuente (para resolver antes de declarar completo, NO por proximidad)

| Ítem | Evidencia requerida | Estado |
|---|---|---|
| Cota superior de columnas/huellas `piso4_103` y diagonales marco I'–J / torre G–H | láminas de elevación 800/801/802 (fw) | pendiente |
| Secciones `P.M.I.` (22 en EI) y `V.S.I. 20/150` (1) | plano de detalle de perfiles (con espesores reales) | pendiente, quedan `PENDIENTE_DE_FUENTE` |
| Números de lámina EII (CP1S…CP4) | origen del plano (solo sha256 de 2017_67-700 registrado) | pendiente |

## 7. Estado de git

No hay commits/tags/pushes en `entrega-03-modelos-fieles`; el checkpoint `9413871` queda intacto.