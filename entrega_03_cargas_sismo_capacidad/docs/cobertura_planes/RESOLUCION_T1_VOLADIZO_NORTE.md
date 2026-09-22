# RESOLUCION_T1 — Voladizo Norte P2 + Remesh Torre (Edificio I)

_Fecha: 2026-09-11 · Módulo: `src/modelo_fiel/modelo_fe_completo.py` · Test: `tests/verif_remesh_t1.py`_

## 1. Alcance

Resolver en el origen (constructor FE) el bloque de hallazgos de cobertura física del
voladizo norte de la torre G-H (P2/P3/P4):

- **Phantom** `poste_18.96_14.79_P4` (tag 650, cota P3→P4): sin fuente en viewer P3/P4
  ni en candidatos P3/P4 → **retirado** mediante tope documentado (`TORRE_TOPE_NIVEL`).
- **Remesh** de las 3 columnas P.M. 300×300×20 hacia la huella DXF REUBICADA:
  tags 648 (P2), 662 (P4), 674 (P4).
- **Soporte real** de G3S1: incorporación al FE de la ménsula/voladizo norte P2
  (planos 2017_67-102, vigas PLA2017-102 sección V. 60/80) para que la base del poste
  apoye **directamente sobre enmarcado** (sin stub elástico, sin conector artificial).
- **Pilar oeste** del voladizo (RLE-PILAR 0.30×0.30) materializado como **nudo** del
  sub-marco, sin columna elemento (ni tramos fantasma).

## 2. Ledger de trazabilidad (antes → después)

| Tag FE (antes) | Tipo | Nivel | Posición FE (antes) | Posición física (huella DXF / viewer) | Acción | Elemento FE (después) |
|---|---|---|---|---|---|---|
| 648 | Columna P.M. 300×300×20 | P2 | (18.96, 14.79) | (17.49, 20.27) centro huella u[17.34,17.64] v[20.12,20.42] (102.dxf) | **REMESH** a centro de huella | `poste_17.49_20.27_P3` (P2→P3) |
| 650 | Columna P.M. 300×300×20 | P3 | (18.96, 14.79) | Sin huella en P3/P4 (verificado viewer y candidatos) | **RETIRADO** (PHANTOM) | — (no existe; `TORRE_TOPE_NIVEL`) |
| 662 | Columna P.M. 300×300×20 | P4 | (21.50, 21.03) | (20.00, 20.45) centro huella u[19.85,20.15] v[20.30,20.60] (103.dxf) | **REMESH** a centro de huella | `poste_20.0_20.45_remate` |
| 674 | Columna P.M. 300×300×20 | P4 | (31.55, 21.03) | (30.00, 20.45) centro huella u[29.85,30.15] v[20.30,20.60] (103.dxf) | **REMESH** a centro de huella | `poste_30.0_20.45_remate` |

Nota de precisión: el viewer registra G3S1 en `posicion [17.50, 3.91, 20.27]` (pivote del
pivote de modelado). La huella RLE-PILAR u∈[17.34,17.64] tiene **centro 17.49**, que
coincide exactamente con el eje de la viga vertical V_x1749 de la ménsula. El remesh usa
**17.49** (centro de huella) para que los 3 ejes (H_y2027 / V_x1749 / base G3S1)
converjan en un único nudo (MERGE_TOL = 0.0 m), sin flexibilidad artificial.

## 3. Incorporación de vigas del voladizo norte P2 (PLA2017-102)

Geometría fuente: `apply_plan_frames.py` (`P2_ADD_BEAMS`) + `viewer_unity/.../P2.json`
(vigas sin FE/tributaria, `recibe_losa=false`). Se incorporan al FE como `P2_VOLADIZO_VIGAS`
(sección V. 60/80) con los ejes llevados a los **nudos de encuentro reales**:

| Viga | Eje FE (u,v) | Nudo inferior / sur | Nudo superior / norte | Encuentros |
|---|---|---|---|---|
| `H_EI_CP2_y2027_10.30-17.79_PLA2017-102` | v = 20.27 | (10.00, 20.27) | (17.49, 20.27) | pilar oeste (10.00); G3S1/V_x1749 (17.49) |
| `V_EI_CP2_x1000_16.50-20.57_PLA2017-102` | u = 10.00 | (10.00, 16.15) | (10.00, 20.57) | columna F3 (v=16.15); H_y2027 (v=20.27); voladizo al norte |
| `V_EI_CP2_x1749_16.45-19.97_PLA2017-102` | u = 17.49 | (17.49, 16.15) | (17.49, 20.27) | perimetral H_y0162 (v=16.15, se subdivide); G3S1/H_y2027 (v=20.27) |

- **Base de G3S1**: cae sobre H_y2027 → se registra `tipo: apoyo_directo_en_viga`,
  `radio_m: 0.0`, **sin stub** (decisión usuario: "apoya directamente, sin stub").
- **Sin conectores cortos elásticos ni brazos rígidos**: los ejes se tocan exactamente
  en planta; no hay excentricidad física que modelar (solo las excentricidades 0.30–0.35 m
  reales de arranque en ejes base ya existentes; todas ≤ 2.5 m: máximo 2.443 m).
- **Losa / diafragma no extendido**: nada nuevo se apoya en losa fuera de contorno; los
  nodos del voladizo son nodos del enmarcado (vigas), no esclavos de diafragma.

## 4. Pilar oeste del voladizo (10, 20.27)

- **Evidencia**: huella RLE-PILAR u∈[9.85,10.15] v∈[20.12,20.42] (102.dxf) → centro
  (10.00, 20.27); nota de `apply_plan_frames.py` P2_ADD líneas 120–134: material de la
  columna P2 como "acero del voladizo norte (convención de las demás columnas P2)".
- **Decisión**: **NODO** del sub-marco (unión H_y2027 ^ V_x1000 en (10.00,20.27)) con
  rigidez del enmarcado del piso; **sin** columna elemento.
- **Justificación**: huella disponible solo en plano P2; sin huella en P1/P3/P4 ni
  perfil/espesor documentado (la sección 0.30×0.30 es dimensión exterior de huella).
  Un tramo inferior a CP1S (−4.01 m) sería fantasma (PHANTOM_SIN_FUENTE_FISICA) y un
  tramo superior a P3/P4 no tiene fuente.
- **Estado**: **HIPÓTESIS/PENDIENTE** (no "confirmado") — perfil/material asumido por
  convención de capa (`apply_plan_frames` P2_ADD). Verificar con lámina 102/802 si el
  pilar oeste continúa sobre P2.
- **Verificación de ausencia de continuidad**: `tests/verif_remesh_t1.py` — `pilar_oeste_sin_columna`
  (0 columnas en (10,20.27)) y `oeste_sin_tramo` (0 tramos P2→P3/P3→P4 en ese eje).

## 5. Definición explícita del pilar oeste (según guía usuario)

| Ítem | Valor | Fuente |
|---|---|---|
| Coordenada de eje | (10.00, 20.27) | centro huella RLE-PILAR 102.dxf |
| Cota superior | P2 = 3.91 | plano P2 2017_67-102 |
| Cota inferior | **(apoyo real del sub-marco)** columna F3 (10,16.15) que desciende a CP1S (−4.01) vía V_x1000 + H_y2027 | enmarcado FE |
| Elemento físico sobre el que reposa | H_y2027 (v=20.27) y V_x1000 (cabeza → F3) | 102.dxf |
| Uniones | H_y2027 ^ V_x1000 en (10.00,20.27); V_x1000 ^ F3 en (10.00,16.15); V_x1000 cara norte (10.00,20.57) | 102.dxf |
| Sección exterior huella | 0.30 × 0.30 (huella RLE-PILAR) | 102.dxf |
| Material/perfil | Asumido: acero P2 voladizo norte (convención capa) — **HIPÓTESIS/PENDIENTE** | apply_plan_frames P2_ADD |
| Continuidad sobre P2 | Ausencia documentada en P3/P4 (sin huella) → **sin elemento vertical sobre P2** | viewer/candidatos P3/P4 |

## 6. Cambios de código (`modelo_fe_completo.py`)

1. `REMESH_TORRE` aplicado en `_patch_niveles` sobre `niveles[<cod>].columnas` (todos los
   niveles > CP1S) ANTES de la extracción de `acero_posts` (mismo recorrido → el eje
   remallado alimenta los arranques).
2. `P2_VOLADIZO_VIGAS` anexadas a `self.niveles["P2"].vigas` (el motor las subdivide en
   los joints propios y ajenos; la perimetral H_y0162 se corta en u=17.49).
3. `_add_acero_torre`:
   - `por_eje` acumula `niveles` por eje y se procesa ordenado por `(orden de nivel_base,
     u, v)` → las bases P2/P3 se generan antes que los remates P4.
   - `_viga_nodo(base)` (nuevo): si la base del poste es incidente a un `viga_elem` de su
     misma cota → apoyo directo (`tipo: apoyo_directo_en_viga`, `radio_m: 0.0`) sin stub.
   - `TORRE_TOPE_NIVEL[(17.49,20.27)] = "P3"`: el loop de tramos sube solo a la cota del
     tope documentado. Para todos los demás postes se conserva la convención del modelo
     (los que inician en P3 suben a la losa P4; los que inician en P4 al tope hipotético).

## 7. Verificación (tests + corridas)

- `tests/verif_remesh_t1.py` — 31/31 OK: preflight completo; sin phantom (nodo ni
  elemento); G3S1 base/tope/tramo P2→P3 y sin P4; H_y2027 único segmento
  (10,20.27)→(17.49,20.27) a cota P2; V_x1749 (17.49,16.15)→(17.49,20.27) y subdivisión
  de la perimetral en 17.49; V_x1000 (10,16.15)→(10,20.27)→(10,20.57) tocando F3; pilar
  oeste sin columna; stubs ≤ 2.5 m (máx 2.443); apoyo directo G3S1 radio 0; 25 arranques;
  remates P4 remallados; sin tramos en el eje del pilar oeste.
- Preflight del build: `preflight: true` (0 aislados, 0 duplicados, 0 sin camino).
- Corrida G/Q (`--g`): G Pz=Rz=42 406.96 kN equilibrio OK, Q Pz=Rz=12 328.42 kN OK,
  reconciliación contra ` peso_propio_teorico_EDIFICIO_I_v2.json` delta 0.0 kN OK.

## 8. Conteos antes → después

| Métrica | Antes | Después |
|---|---|---|
| n_nodos | 335 | 337 |
| n_columnas | 99 | 115 |
| n_vigas | 233 | 251 |
| n_stubs | 45 | 44 |
| conectores_arranque | 25 | 25 |
| acero posts (origen) | 25 | 25 |
| tag 650 (phantom) | 1 | 0 |
| G3S1 tramos | P2→P3→P4 (2) | P2→P3 (1) |

## 9. Pendientes fuera de alcance

- Cobertura física: regenerar `CLASIFICACION_SIN_I` y `AUDITORIA_COBERTURA_VIEWER_FE_I`
  (scripts) y actualizar `INFORME_COBERTURA_FISICA.md` (etiqueta de cierre de los 4 tags).
- Verificación de perfil del pilar oeste (hipótesis) contra láminas.
- Remesh/retirada equivalentes para hallazgos de la Tarea 2 (muros u=40.15/45.4) y del
  inventario de 105 viewer-SIN (Tarea 3).