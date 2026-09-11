# Inventario estructural definitivo (Edificios I y II)

Fecha: 2026-09-10 · Rama: `entrega-03-modelos-fieles` · Pre-modelo (no se ha tocado el modelo FE).

Generado por `entrega_03_cargas_sismo_capacidad/src/modelo_fiel/inventario_universo_estructural.py`,
salidas en `modelo_fiel/inventario_universo_estructural_{I,II}.json|.md` y resumen en `.json`.

## 1. Clasificación

Clases (taxonomía del proyecto): `ESTRUCTURAL_CONFIRMADO`, `REFERENCIA_O_HIPOTESIS`,
`NO_ESTRUCTURAL`, `PENDIENTE_DE_FUENTE`. **Objetivo de cobertura: 100% de `ESTRUCTURAL_CONFIRMADO`.**
No se admite declarar completo mientras quede un confirmado sin análisis (regla del proyecto).

## 2. Totales

| | Viewer | ESTRUCTURAL_CONFIRMADO | NO_ESTRUCTURAL | REFERENCIA_O_HIPOTESIS | PENDIENTE_DE_FUENTE |
|---|---|---|---|---|---|
| **I** | 304 | **279** | 2 | 0 | 23 |
| **II** | 256 | **251** | 0 | 0 | 5 |
| **Σ** | 560 | **530** | 2 | 0 | 28 |

Ref.: (I) 111 columnas + 164 vigas + 29 muros; (II) 41 columnas + 175 vigas + 40 muros.

## 3. Cobertura actual de confirmados (resultados FE previos, a regenerar)

| Edificio | 1A1 | CONTENIDO | SIN_RESULTADO_FE | Cobertura actual |
|---|---|---|---|---|
| I | 108 | 46 | 125 | 55.2 % |
| II | 202 | 28 | 21 | 91.6 % |

> Nota EI: la 1A1 restante del viewer (109) corresponde a una viga `PENDIENTE_DE_FUENTE`
> (V.S.I. 20/150, tag FE 398) que el modelo previo analizó con sección asumida; no se cuenta como
> confirmado analizado.

### Distribución de SIN por nivel (confirmados)

- **EI**: CP1S 7 · P1 4 · P2 6 · P3 30 (columnas P3 30/34 en grilla sin tramo FE) · P4 78
  (vigas y columnas en eje físico +0.181 sin resultados FE previos).
- **EII**: CP1S 1 (M_002INF) · CP1 1 (M_002C) · CP2 1 (M_002C) · CP3 1 (M_002C) · CP4 17
  (9 columnas + 8 muros, "no hay elementos por encima de 11.83 en el modelo").
  El resto del CP4 (34 vigas) ya está modelado.

## 4. Decisiones de geometría (documentadas en `DECISION_GEOMETRIA_EJE_P4.md`)

1. **Eje P4 (EI)** = físico documentado (2017_67-103, RLE-SOLID/RLE-VIGA): `v = 0.18 / 9.08 / 16.33`
   (+0.1812 m sobre la grilla RLE-EJE 0/8.9/16.15). Aplica a columnas y vigas del P4.
2. **Continuidad P3→P4**: tramo P3 (7.87→11.83) en grilla (u, 0/8.9/16.15); el segmento P4 sobre
   11.83 en el eje físico +0.1812 (desfase registrado; reconciliación 18/18).
   `COL_EI_CP3_C_I3_40.0` **no** se da de alta en (40,16.331): no existe tramo FE ahí.
3. **EII CP4**: 34 vigas ya analizadas; las 9 columnas y 8 muros del CP4 (referencia nodal) son
   elementos extendidos que el modelo no incluye → deben incorporarse al `MODELO_FE_COMPLETO` con su
   continuidad vertical; la cota superior se fija con la fuente de cubierta (plano EII, pendiente).
4. **Muros**: segmentación viewer (29 objetos EI / 40 EII) vs. 45 (EI) tramos FE. Se consolida el muro
   físico M_002 del EII (sub-segmentos DER/IZQ/INF/C) en un único elemento continuo con sus nodos.

## 5. Pendientes de fuente (28) — fuera de cobertura hasta resolver

- **EI (23)**: 22 columnas `P.M.I.` (RLE-TEXTO-1, sin huella / sección por resolver) en P3 y P4;
  y 1 viga `V.S.I. 20/150` (H_EI_CP1S_y2732, peralte/armadura sin fuente). El FE previo las modeló
  con secciones asumidas (tag 398 p.ej.); esas asunciones quedan marcadas y no se cuentan como
  resultado fiel.
- **EII (5)**: vigas `V_031` (cantilever eje A) con sección `por_resolver` en la geometría; el FE
  previo las modeló como V.60/80 (hipótesis a confirmar con lámina).

## 6. Excluidos de manera razonada (EI, 2)

| id | Motivo |
|---|---|
| `COL_EI_CP2_RLE_PILAR_10.00_20.27` | Huella RLE-PILAR 0.30x0.30 sin elemento resistente (2017_67-102) |
| `COL_EI_CP2_S_G3S1_18.96` | P.M. 300x300x20 sin huella en planta (RLE-TEXTO-1) |

Sin elementos `REFERENCIA_O_HIPOTESIS` persistidos en el viewer (todo objeto viewer es físico).

## 7. Tareas de resolución para llegar al modelo fiel completo

1. Fijar cota superior y continuidad de los elementos sobre la cubierta (EI: P.M. huella `piso4_103`,
   diagonales marco I'–J/torre G–H; EII: CP4 columnas/muros) con láminas de elevación.
2. Registrar secciones de los 27 ítems `P.M.I.`/`V.S.I.`/`por_resolver` o moverlos explícitamente a
   `PENDIENTE_DE_FUENTE` documentado.
3. Construir `MODELO_FE_COMPLETO` EI/EII (variante separada, sin sobrescribir resultados previos).
4. Corridas independientes **G, Q, EX, EY** con **q_Q = 3,0 kN/m²** (NCh1537 Tabla 4; 0.5Q_fiel ×1,5).
5. Exportar por elemento: **N, Vy, Vz, T, My, Mz** en **extremos i/j** por caso; actualizar viewer con
   estados `CON_RESULTADO_FE` / `SIN_RESULTADO_FE` / `EXCLUIDO_NO_ESTRUCTURAL` / `PENDIENTE_DE_FUENTE`.
6. Paquete de aceptación: matrices viewer→FE / FE→viewer antes-después, cobertura 100% de confirmados,
   verificación de coordenadas/conectividad por nodo, equilibrio por caso, comparación con resultados
   previos, pruebas automatizadas (suite 48/48) y revisión visual en Unity; estado final en git (sin commit).

## 8. Estado de git

Rama `entrega-03-modelos-fieles`, checkpoint `9413871` intacto; sin commits/tags/pushes.
Archivos nuevos de este trabajo: `src/modelo_fiel/inventario_universo_estructural.py`,
`modelo_fiel/inventario_universo_estructural_{I,II}.{json,md}`,
`modelo_fiel/inventario_universo_estructural_resumen.json`, `modelo_fiel/DECISION_GEOMETRIA_EJE_P4.md`.