# Esquema Nodal — Voladizo Norte P2 / Torre G-H (Edificio I)

_Fecha: 2026-09-11 · Módulo: `src/modelo_fiel/modelo_fe_completo.py` · Verificación: `tests/verif_remesh_t1.py`_

Esquema de los nudos de interés en planta (u,v) para las cotas P2 (3.91), P3 (7.87), P4 (11.83).
Los nudos son los del **enmarcado FE** (labels internos de OpenSees, no tags viewer).

## 1. ANTES (pre-remesh / pre-ménsula)

La ménsula norte P2 no existía en el FE (solo en el viewer, `recibe_losa=false`, sin FE).
G3S1 estaba en la posición candidata (18.96,14.79) con tramos P2→P3→P4 (tags 648/650);
GS6/HS7 en (21.50,21.03)/(31.55,21.03) con remates P4.

| Nudo | Cota | Estado ANTES | Comentario |
|---|---|---|---|
| (18.96, 14.79) | 3.91 | Poste base P2 (stub hacia axiles<trib$) | G3S1 candidato; fuera de toda huella |
| (18.96, 14.79) | 7.87 | Nudo P3 + tramo P2→P3 (tag 648) | "
| (18.96, 14.79) | 11.83 | Nudo P4 + tramo P3→P4 (**tag 650, PHANTOM**) | Sin fuente P3/P4 |
| (10.00, 20.27) | 7.87 | — | Sin huella en P3 |
| (10.50, 20.72)/(20.50, 20.72) | 11.83 | Concretas P4 físicas (v+0.18) | sin unión con ménsula |
| (17.49, 16.15) | 3.91 | — | La perimetral H_y0162 no tenía nudo interior (segmento u 17.2→20.0) |
| (21.50, 21.03) | 11.83 | Poste P4 remate (candidato) | sin huella física |
| (31.55, 21.03) | 11.83 | Poste P4 remate (candidato) | sin huella física |

> Hiato principal: G3S1 (18.96,14.79) no conectaba con ninguna viga: los ejes documentados
> de la ménsula (H_y2027 v=20.27, V_x1000 u=10, V_x1749 u=17.49) no estaban en el FE y sus
> caras quedaban a 0.30–0.35 m sobre el enmarcado (isla flotante).

## 2. DESPUÉS (remesh + ménsula incorporada)

| Tipo | Nudo FE | Cota | Elementos incidentes |
|---|---|---|---|
| Base G3S1 ∨ H_y2027 ∨ V_x1749 | (17.49, 20.27) | 3.91 | H_y2027 (ext. E), V_x1749 (ext. N), `poste_17.49_20.27_P3` (tramo P2→P3), sin stub (apoyo directo) |
| Tope G3S1 | (17.49, 20.27) | 7.87 | `poste_17.49_20.27_P3` (extremo superior). **Sin** nudo en P4 |
| Subdivisión perimetral | (17.49, 16.15) | 3.91 | H_y0162 (segmentos 17.2→17.49 y 17.49→20.0), V_x1749 (ext. S) |
| Pilar oeste (nudo del sub-marco) | (10.00, 20.27) | 3.91 | H_y2027 (ext. W), V_x1000 (nudo intermedio) — **sin** columna |
| Cabeza de V_x1000 | (10.00, 20.57) | 3.91 | V_x1000 (ext. N, cara documentada 20.57) |
| Fundación de la célula este | (10.00, 16.15) | 3.91 | V_x1000 (ext. S) ∨ columna F.70x70 `col_10.0_16.15_P3`/… la misma nodo |
| Remates P4 | (20.00, 20.45) y (30.00, 20.45) | 11.83 | `poste_20.0_20.45_remate`/`poste_30.0_20.45_remate` (base P4 → 15.79) |

Esquema en planta (P2, u→, v↑):

```
  v=20.57                              (10.00,20.57)
  v=20.27   (10.00,20.27) ———————— H_y2027 —————─── G3S1 (17.49,20.27)
                |        ^                                  ^
  v=16.15   (10.00,16.15) F3 ✕ ———— perimetral H_y0162 ———— ✕ (17.49,16.15)
                                      V_x1000 (u=10)        V_x1749 (u=17.49)
```

## 3. Caminos de carga (test de continuidad)

1. **G3S1** (17.49,20.27,3.91) → `poste_17.49_20.27_P3` → losa P3. Soporte lateral:
   H_y2027 → V_x1749 → perimetral H_y0162 → columna G3 (20,16.15) → base CP1S;
   y H_y2027 → V_x1000 → columna F3 (10,16.15) → base CP1S. *(caminos verificados por
   `caminos_de_carga_a_base`: 0 nodos sin camino)*
2. **Voladizo norte de V_x1000** (10.00,20.57) → V_x1000 → F3/H_y2027 → rim.
3. **Pilar oeste** = nudo (10.00,20.27) con los 2 ejes de la ménsula → F3/perimetral.
   Sin camino propio vertical (no hay columna) → correcto por diseño.

## 4. Checks estructurales de la continuidad (`tests/verif_remesh_t1.py`)

- Nodo G3S1 en (17.49,20.27): base P2 ✓, tope P3 ✓, **sin** nodo P4 ✓.
- Tramo P2→P3 único: `poste_17.49_20.27_P3` ✓.
- H_y2027: 1 solo segmento (10,20.27)→(17.49,20.27) a cota P2 ✓ (sin duplicados).
- V_x1749: 1 solo segmento (17.49,16.15)→(17.49,20.27) ✓; perimetral subdividida en
  17.49 sin duplicación ✓.
- V_x1000: 2 segmentos (16.15→20.27→20.57), toca F3 ✓.
- Pilar oeste: 0 columnas, 0 tramos sobre P2 ✓.
- stubs: todos ≤ 2.5 m (máx 2.443 m) ✓; G3S1 sin stub (apoyo directo, radio 0.0) ✓.
- Preflight + G/Q: equilibrio y reconciliación OK ✓.

## 5. Criterio de convergencia (nodos)

| Nudo | ANTES | DESPUÉS | Δ |
|---|---|---|---|
| G3S1 horizontal | (18.96,14.79) | (17.49,20.27) | −5.67 m (centro huella) |
| Total n_nodos | 335 | 337 | +2 |
| Phantom P4 (G3S1) | 1 | 0 | −1 |
| Stubs | 45 | 44 | −1 (G3S1 pasó a apoyo directo) |