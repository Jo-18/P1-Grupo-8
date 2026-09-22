# Resolución de pendientes de peso propio — Edificio I (Entrega 03, v2)

Modo de trabajo: **solo lectura**. No se modifica el FE, ni las geometrías, ni el viewer, ni el caso `G`.
Este documento aporta **evidencia documental** para los 63 elementos pendientes de la v2, clasifica cada
familia en `confirmado / hipótesis adoptable / sensibilidad` y plantea hipótesis **sin adoptarlas**.
Cualquier adopción futura requiere re-ejecutar la auditoría y actualizar la cota.

- Subtotal confirmado (COTA INFERIOR): **17.179,23 kN** (vigas 14.803,53 · columnas 2.045,60 · muros 330,09).
- Hash determinista del JSON v2 (actualizado con decisiones D1–D7): `a158fcb32147998dcbf83c0270bcd171ac394a82532e90bb63fb890e91e7a515`.
- Pendientes v2 sin cuantificar (`pp_kN:null`, `PP_provisional_kN=0.0`): 19 muros + 1 viga (V.S.I.) + 43 columnas
  (18 hormigón P3→P4, 17 metálicas, 8 P.M.I.) = **63 elementos**.

## 0. Decisiones adoptadas (bloque D1–D7, este documento y `config/parametros_pendientes.json`)

| Decisión | Estado | Efecto en el total |
|---|---|---|
| **D1** Estado de la v2 | `ADOPTADA` | `PP_confirmado=17.179,23 kN` solo cota inferior; `PP_pendiente=null`; `PP_provisional=0.0` |
| **D2** Cajas de ascensor | `ADOPTADA_PARCIAL` | Confirmar panel solo si coincide plenamente línea+espesor+posición+geometría+niveles consecutivos; muros de un solo plano **no** pasan a tramo continuo; cajas P4 `M_CP4_001..006` quedan `PENDIENTE_TRAMO` |
| **D3** Tramos a la base | `ADOPTADA` | Sin tramos sintéticos `BASE→nivel`; solo extremos reales documentados/instanciados |
| **D4** Desfase P4 +0,181 | `ADOPTAR_COMO_DEFECTO_DE_CORRELACION_PENDIENTE_DE_IMPLEMENTAR` | Corrección propuesta +0,1813 m en Y (rejillas horizontales P4) para restaurar P3→P4; no aplicada al FE; hormigón P3→P4 sigue `PENDIENTE_TRAMO` hasta verificar |
| **D5** V.S.I. 20/150 | `HIPOTESIS_DE_GRUPO_PARA_ANALISIS` | HA 0,20×1,50 m, ρ=24,5166, L=21,40 m, pp≈157 kN; NO confirmada; sensibilidad incluir/excluir |
| **D6** M.H.A. e=30 | `ADOPTADA` | `V_EI_CP1S_x1010` = parte del muro eje F (no viga); verificación explícita de no-duplicación |
| **D7** Banda 20,3–21,2 MN | `SOLO_SENSIBILIDAD` | NO adoptada como PP; solo banda de sensibilidad |

---

## 1. Evidencia vectorial de la lámina 800 (elevaciones)

Fuente: `2017_67-800.dxf` (22.936 POLYLINE; textos vectorizados; PDF 800 sin capa de texto).
Calibración anclada (torre, banda `y[1300,1800]`):

```
u   = 19.70 + (x − 3065.3)/100
cota = 7.87  + (y − 1365.1)/100        # verticales x=3065 y[1365,1763] → Δ≈398 ≈ cota 7.87→11.85
```

Cotización FE (autoritativa, `config_edificios.py`): CP1S −4,01 · P1 −0,05 · P2 3,91 · P3 7,87 · P4 11,83 m;
todos los entrepisos 3,96 m.

### 1.1 Hallazgos vectoriales

1. **Marco torre F–G–H (u≈19,70–30,40), banda estricta +7,87→+11,85: sin diagonales de acero.**
   Verticales de entrepiso (RLA-MUROS) de cota +7,87 → +11,85 (L≈3,98 m) en u≈19,70 y u≈30,37 (extremos de la
   torre) y en el vano este u≈32,31/33,30; verticales interiores u≈24,04/26,03 (cota 8,86–11,25); vigas a
   cota 7,87 / 8,86 / 11,25 / 11,85 m. En la ventana estricta `y[1360,1770]` (cota 7,87→11,83), la capa
   **RLA-PERFILES/RLA-SEGMENTO1 (acero) NO contiene diagonales confinadas en la banda**: el listado L>100 de
   la ventana estricta produce solo líneas **RLA-EJES** (ejes de estructura) y verticales/horizontales.
2. **Las líneas m≈+1,573 / −1,706 de la lámina 800 son RLA-EJES (líneas de ejes), no diagonales de acero.**
   Segmentos `(3152.7,862.2)→(3599.0,1564.1)` (m=+1.57, L=831.7) y `(4010.3,862.2)→(3599.0,1564.1)`
   (m=−1.71, L=813.5) **convergen en el apex (3599.0,1564.1)** (u≈24,0; cota≈9,86) sobre la vertical
   RLA-EJES x=3599 (`y[862,1900]`, L=1038). Son líneas de eje del entramado (cota base 3,28 → apex 9,86),
   no miembros de acero; corresponden al patrón "diagonales D1/D2 en otra banda o marco" de la revisión previa.
3. **Ningún miembro metálico desciende a la base.** Los perfiles aparecen solo entre forjados;
   la base (CP1S −4,01) es hormigón P.70x70 (plantas 101/102/103). No hay evidencia de tramo `base→nivel`
   metálico; **no se inventan tramos sintéticos**.
4. **Marco I′–M–J (u≈44–52):** fuera del bbox de miembros estructurales que se escanea en el DXF 800
   (x hasta 5.326 → u≈42,3). Su posición proviene de rótulos planta P3 (`V.M. 300x300x5` u≈46,34/48,70;
   `P.M.I.` u≈47,8/50,7) y huellas planta P4 (I′ u=44,919 concreto; M u=47,456; J u=49,794). La lectura
   humana de la lámina (REPORTE_LAMINA800_CANTILIVER_IJ) reporta verticales + diagonales convergentes
   (5,00 m = 2,55 + 2,45). Sin el detalle de conexión no se confirma la continuidad vertical P3→P4.

### 1.2 Tabla de continuidad (fuente: DXF 800 + plantas + DXF 801/802)

| Familia | u / v | Cota inferior | Cota superior | Longitud | Sección | Fuente |
|---|---|---|---|---|---|---|
| Columnas retícula hormigón (E,F,G,H,I,I′) filas 1/2/3 | u 0…45 · v 0 / 8,9–9,3 / 15,8–16,15 | −4,01 (CP1S) | +11,83 (P4) | 15,84 m acum. | P.70x70 | Plantas 101/102/103 + `columnas_tramos_ei.json` |
| Torre F–G–H: verticales extremas | u≈19,70 y 30,37 (vano este u≈32,31/33,30) | +7,87 | +11,85 | ≈2,99–3,98 m | V.M.300x300x5 (rótulos FS/GS) | DXF 800 (RLA-MUROS) |
| Torre F–G–H: verticales interiores | u≈24,04 / 26,03 | +8,86 | +11,25 | ≈2,39 m(parcial) | P.M.300x300x20 (hip.) | DXF 800 (RLA-MUROS) |
| Torre F–G–H: paneles X P3→P4 (±0,961) | u 20,30–29,70 · v 16,45–20,57 | +7,87 (P3) | +11,83 (P4) | L=5,714 m (panel 4,12×3,96) | celosía X | **DXF 801/802** (RLA-PERFILES/SEGMENTO1, m=±0,961; viewer TORRE G–H) |
| Linhas de ejes convergentes (apex 9,86) | u≈22,9–30,4 · cota 3,28→9,86 | ~+3,28 | ~+9,86 | 5,49–8,32 m | RLA-EJES (no acero) | DXF 800 (RLA-EJES, apex 3599,0/1564,1) |
| Marco I′–M–J: verticales | u≈46,34 / 47,46–47,89 / 48,70 / 49,79(50,7) | +7,87 (P3) | +11,83 (P4) | ≈3,96 m | V.M.300x300x5 / P.M.I. (rótulos) | Reporte 800 + rótulos planta P3 + huellas P4. **Continuidad P3→P4 NO legible (detalle de conexión)** |

### 1.3 Reconciliación vectorial L800 vs L801/L802 (resuelve la contradicción)

**Contradicción reportada:** el informe nuevo atribuía a L800 una "celosía F–G–H P3→P4 con diagonales
m≈+1,573/−1,706", mientras la revisión previa concluyó "banda estricta +7,87→+11,85 sin diagonales de acero;
paneles X de la torre vienen de L801/L802 (m≈±0,961); viewer ±0,961".

**Reconciliación vectorial (por patrón):**

| Patrón | Lámina | Título/eje | bbox del dibujo | Coordenadas (cm DXF) | Cotas verticales | Pendiente | Elemento/marco | Correspondencia u/v |
|---|---|---|---|---|---|---|---|---|
| Paneles X torre G–H (+0,961) | **801** | detalle torre G–H | window (1500,3100,900,3800) | (2500,0,3132,2)→(2907,6,3524,0) L=565 | P3→P4 (3,96 m) | **m=+0,961** (43,87°) | RLA-PERFILES + RLA-SEGMENTO1 (líneas gemelas) | u=20,30–29,70 … v=16,45–20,57; panel 4,12×3,96; L=5,714 |
| Paneles X torre G–H (−0,961) | **802** | detalle torre G–H | window (1400,2600,1600,2500) | espejo (m=−0,961) | P3→P4 | **m=−0,961** (136,13°) | RLA-PERFILES/SEGMENTO1 | ídem, invertida; viewer `|m|=0,961`, θ=43,87/136,13, L=5,714 |
| Líneas de ejes convergentes | **800** | entramado F–G–H (elevación) | torre box x[3060,4140] y[1360,1770] | (3152,7,862,2)→(3599,0,1564,1) y (4010,3,862,2)→(3599,0,1564,1) | 3,28→9,86 (apex) | m=+1,57 / −1,71 | **RLA-EJES** (NO acero) | u≈22,9–30,4; apex u≈24,0/cota≈9,86; **no** son paneles P3→P4 |
| Verticales/horizontales banda | **800** | torre F–G–H | ídem | x=3065,3/3698,4/4132,7; y=1365,1…1763 | 7,87→11,85 | vertical/horizontal | RLA-MUROS | u=19,70/26,03/30,37; v per nivel |

**Conclusión de la reconciliación:**

1. **L800 ≠ lámina de celosía P3→P4.** La banda estricta +7,87→+11,85 del marco F–G–H **no contiene
   diagonales de acero** (RLA-PERFILES/SEGMENTO1 confinadas en la banda). Las líneas m=+1,573/−1,706 son
   **RLA-EJES** (líneas de ejes) que convergen en el apex (3599,0,1564.1) — coinciden con el hallazgo previo
   "diagonales D1/D2 en otra banda o marco".
2. **L801/L802 = torre G–H (paneles X P3→P4).** Los paneles X de la torre entre cota +7,87 y +11,83 se
   documentan con m=**±0,961** (43,87°/136,13°) en las láminas **801/802**; corresponden **exactamente** a los
   paneles implementados en el viewer (`TORRE G–H`, panel 4,12×3,96 m, L=5,714, anclados a nodos P3/P4 entre
   v=16,45 y v=20,57).
3. **Identificación previa correcta.** La reimplementación previa (viewer ±0,961 desde 801/802) es **consistente
   con el DXF vectorial**; la afirmación del informe nuevo (celosía P3→P4 en L800 con m=1,573/1,706) queda
   **corregida en este documento** (§1.1 ítem 1). No se cambia el viewer ni los pesos metálicos.
4. **Elementos sen la banda:** solo verticales/horizontales (RLA-MUROS) u≈19,70/26,03/30,37; esto **no** altera
   el total confirmado (los X panels no estaban cuantificados: siguen representados por los metálicos pendientes).

### 1.3 Consecuencia para columnas en la v2

- 18 columnas de **hormigón P3→P4** (`COL_EI_CP4_C_*`, P.70x70): existen en planta P4 (huellas) y en el FE;
  el tramo P3→P4 no está instanciado por el desfase +0,181 de P4 (D4) → **PENDIENTE_TRAMO**
  (hipótesis adoptable: pp = 18 × 0,49 × 3,96 × 24,5166 ≈ **856 kN**).
- 9 `P.M. 300x300x20` (A=0,0224 m²) y 8 `V.M. 300x300x5` (A=0,0059 m²): tubulares confirmados por rótulos;
  sin tramo documentado entre niveles → **PENDIENTE_TRAMO** (pp hipótesis 9×6,83 + 8×1,80 ≈ **75,8 kN**).
- 8 `P.M.I.`: sin B×H×t en planos → **PENDIENTE_SECCION** (pp hipótesis si fuesen 300x300x20 → **+54,6 kN**).

---

## 2. Desfase +0,181 m en P4 — diagnóstico y propuesta exacta (D4)

Evidencia documentada originalmente en `informe_validacion_fisica_xref.md` y `tabla_residuos_transformacion.md`;
los valores textuales se reconstruyen y verifican desde `validacion_fisica_xref.py`,
`validacion_pendientes_CP1S_P4.py` y `matrices_transformacion_unity.json`:

- Cadena `p_700 = p_estructural + insercion_xref` (escala 1, rotación 0, sin reflejo); **todas las
  transformaciones validadas** (CP1S…P4 `transformacion_xref_validada`).
- Matriz P4 (`dxf_to_local`): `u=(x−490.30)/100`, `v=(6297.30−y)/100`; el origen local P4 es
  `(0.0, 0.181221, 11.83)` → la rejilla horizontal `RLE-EJES` de P4 queda en y-analítica **0,1812 / 9,0812 / 16,3314**,
  es decir **+0,1813 m constante** respecto a las cotas congeladas (1=0, 2=8,9, 3=16,15). Columnas y rejilla
  vertical cierran sub-centimétrico (0,0025–0,0065 m).
- **Conclusión:** el desfase es propiedad de las líneas de eje dibujadas (registro `eje` vs `cara`), no un
  desplazamiento físico, ni un error de transformación, ni una transición estructural.

**Propuesta exacta de corrección (D4 — pendiente de implementar, NO aplicada):**

| Elemento | Transformación | Antes | Después |
|---|---|---|---|
| 3 líneas de rejilla horizontales `RLE-EJES` de P4 (ejes 1, 2, 3) | `v' = v − 0.1813` (equivalente `y' = y + 18.13` cm) | v = 0,1812 / 9,0812 / 16,3314 | v = 0,0000 / 8,9000 / 16,1500 |
| Elementos afectados | las 3 líneas de rejilla horizontales de P4 (registro `eje`). **No** columnas (u/v cerraron sub-centimétrico) ni rejilla vertical | desfase +0,1813 | desfase residual ≤ 0,01 m |
| FE / viewer / caso G | **NO se modifican** | — | — |

Al implementar, debe restaurarse la conectividad P3→P4 y solo entonces los tramos `P.70x70` P3→P4 podrían
pasar de `PENDIENTE_TRAMO` (hoja de "8 columnas hormigón P3→P4" en la v2) tras revalidación. Hasta entonces
permanecen `PENDIENTE_TRAMO`.

---

## 3. Muros pendientes (19) — resolución por continuidad (D2)

Mecanismo v2: un muro se confirma si la misma línea+espesor aparece en ≥2 niveles consecutivos; los
pendientes son muros de un solo nivel o sin par exacto por extensión. Evidencia = candidatos de plantas
101/102/103 (línea, espesor, id) + FE (`niveles[*].muros`).

### 3.1 Cajas de ascensor (D2 — ADOPTADA_PARCIAL)

**Decisión adoptada (D2):** se confirma un panel solo si la continuidad P2→P3→P4 está respaldada por
**coincidencia plena** (línea + espesor + posición + geometría + niveles consecutivos). Un muro que aparece
en un solo plano **no** se convierte automáticamente en tramo continuo: permanece `PENDIENTE_TRAMO` a menos
que la convención de planta demuestre explícitamente el entrepiso.

| Familia | x (m) | v (m) | e (m) | Estado actual | Decisión |
|---|---|---|---|---|---|
| Caja trasera (ascensor) | 3,275 y 6,725 | 12,27–14,03 | 0,25 | P2 M_004/005 · P3 M_004/005 (vert.) + P4 M_004/005 (vert.) + P4 M_006 (cierre v=14,026) | coincidencia de línea/posición en 3 niveles; espesores y geometría de cierre **por validar** → **PENDIENTE_TRAMO** (candidata a plena coincidencia) |
| Caja delantera (ascensor) | 3,55 y 6,45 | 4,0–6,2 | 0,30 | P4 M_002/003 (vert.) + P4 M_001 (cabezal v=4,081) | empalma con M_CP2_001/002 y M_CP3_002/003 (confirmados P2→P3); tramo P3→P4 y cabezal **por validar** → **PENDIENTE_TRAMO** |

Masa hipótesis de las cajas (contando 1 vez, h entrepisos): ≈ **554 kN** (P2 81,5 + P3 71,8 + P4 400,9);
solo sensibilidad (D7), no adoptada.

### 3.2 Muros de un solo nivel (evidencia = planta de su nivel; sin prolongación)

| Id | Nivel | Posición | e (m) | L (m) | Decisión |
|---|---|---|---|---|---|
| M_EI_CP1S_003 | CP1S | x=9,65 (−0,45…16,50) núcleo eje F | 0,70 | 16,95 | propuesta **CONFIRMADA single-level** (sostén del portico CP1S; véase 5) |
| M_EI_CP1S_004/005 | CP1S | x=3,4/6,6 (caja trasera) | 0,20 | 4,48 | propuesta CONFIRMADA single-level (sin plano P1 que la documenta) |
| M_EI_CP1S_006/007 | CP1S | x=3,7/6,3 (caja delantera) | 0,20 | 2,35 | propuesta CONFIRMADA single-level (ídem) |
| M_EI_CP1_001 | P1 | x=−0,25 (v 0–16,15) cerramiento oeste | 0,20 | 16,15 | propuesta CONFIRMADA single-level |
| M_EI_CP1_002 | P1 | x=40,15 (v 9,25–26,33) | 0,30 | 17,08 | propuesta CONFIRMADA single-level |
| M_EI_CP1_003 | P1 | x=45,4 (v −0,2…−6,3) | 0,30 | 6,10 | propuesta CONFIRMADA single-level |
| M_EI_CP1_004 | P1 | x=38,83 (v −0,6…−3,65) | 0,15 | 3,05 | propuesta CONFIRMADA single-level |

- No se prolongan ni se deduce base (read-only); si se adoptara la caja continua al sótano, las piezas
  CP1S 004–007 quedarían absorbidas como cabezales (hipótesis, no adoptada).
- Rango de masa de los 19 muros pendientes (h 3,0–3,96 m): **≈ 2.661–3.005 kN** (≈15–17 % de la cota),
  solo sensibilidad (D7).

---

## 4. V.S.I. 20/150 (`H_EI_CP1S_y2732_0.200-21.600`) — D5 (HIPOTESIS_DE_GRUPO_PARA_ANALISIS)

- Evidencia FE (`trace_vsi2.py`): la malla parsea la etiqueta `20/150` como **0,02×0,15 m acero**
  (b=0,02 h=0,15, E=2e8 kPa) → desplazamiento propio de −12,68 m en el vano de 21,40 m (claramente absurdo);
  el ordenador real (SS b=0,02×0,15 acero → 63,2 m; b=0,20×1,50 m hormigón → 0,043 m).
- Soporte: descansa en los muros de contención M_001 (u=−0,35) y M_002 (u=21,25) a cota CP1S. w=26,06 kN/m
  sobre 84,24 m² tributarios. Solo hay un rótulo del plano (`V.S.I. 20/150`); no fija material ni unidades.
- **Decisión adoptada (D5):** se adopta como **HIPOTESIS_DE_GRUPO_PARA_ANALISIS** (provisional, NO confirmada)
  la viga de gran canto de hormigón **0,20×1,50 m** (ρ=24,5166 kN/m³, L=21,40 m) pp ≈ **157,4 kN** (~0,9 %);
  queda **fuera del total confirmado**. En la sensibilidad (D7) se evalúa **incluir / excluir** su peso.
- Pendiente: confirmación documental de la materialidad (HA vs acero) para elevarla a confirmada.
- La sección provisional FE (30×60) es inconsistente con la etiqueta; corregirla cambia masa y rigidez:
  fuera del alcance read-only. Estado en la v2: **PENDIENTE_SECCION** (permanece).

---

## 5. Viga `V_EI_CP1S_x1010` (`M.H.A. e=30`) — D6 (ADOPTADA)

- Está en la lista de vigas del FE pero es **una sección de muro** (M.H.A. e=30) del eje F (x≈10,10,
  v 0,70–16,15), coincidente en posición con `M_EI_CP1S_003` (x=9,65). No es una viga → **NO_INCLUIDA**
  en el cómputo de vigas (decisión v2, confirmada).
- **Decisión adoptada (D6):** se contabiliza como **parte del muro del eje F**, no como viga adicional.
  Verificación explícita de **no-duplicación**: su masa NO está en ningún total confirmado (ni vigas ni
  muros) y la sensibilidad del muro eje F (`M_CP1S_003` ∪ `V_EI_CP1S_x1010`) se computa **una sola vez**
  (evita doble conteo entre `V_EI_CP1S_x1010` y `M_EI_CP1S_003`).
- Si se adoptara como muro único del eje F, pp = 0,20–0,70 × 15,45 × 3,0–3,96 × 24,5166 ≈ **227–1.050 kN**
  (solo sensibilidad; NO entra al total confirmado).

---

## 6. Escenarios de sensibilidad (D7 — SOLO_SENSIBILIDAD, no adoptados)

Banda de masa fuera de la cota inferior (kN); **NO es PP adoptado** (D7):

| Familia | Min | Max |
|---|---|---|
| Columnas hormigón P3→P4 (18) | 856 | 856 |
| Columnas metálicas (P.M. + V.M. + P.M.I.) | 76 | 131 |
| V.S.I. gran canto (H1) | 157 | 157 |
| Cajas ascensor P2–P4 (1 vez) | 554 | 554 |
| Muros P1 (single-level) | 1.033 | 1.033 |
| Muro eje F sótano (`M_CP1S_003` ∪ `V_EI_CP1S_x1010`, sin doble conteo) | 227 | 1.050 |
| Muros caja sótano CP1S (004–007) | 265 | 265 |
| **Total banda** | **3.168** | **4.046** |
| **% sobre 17.179,23** | **18,4 %** | **23,6 %** |
| **PP total si todo adoptado** | **≈ 20.347** | **≈ 21.225** |

La mayoría de la banda corresponde a muros y al tramo de hormigón P3→P4 (los metálicos X de 801/802 y la
celosía son marginales: <1 %). Precisar exige solo ensayo: adoptar la caja continua (D2 pendiente de plena
coincidencia) y el gran canto H1 (D5), y confirmar el tramo P3→P4 de hormigón tras implementar la corrección
del desfase P4 (D4).

---

## 7. Decisiones adoptadas (bloque D1–D7)

1. **D1 — ADOPTADA:** la v2 es **COTA INFERIOR**; `PP_confirmado=17.179,23 kN`;
   `PP_pendiente_kN`/`PP_no_incluido…` `null`; `PP_provisional=0.0`.
2. **D2 — ADOPTADA_PARCIAL:** cajas de ascensor se confirman solo con coincidencia plena
   (línea+espesor+posición+geometría+niveles consecutivos) P2→P3→P4; muros de un solo plano **no**
   pasan a tramo continuo; `M_CP4_001..006` permanecen `PENDIENTE_TRAMO`.
3. **D3 — ADOPTADA:** no se crean tramos `base→nivel` sin evidencia; los metálicos solo entre forjados.
4. **D4 — ADOPTAR_COMO_DEFECTO_DE_CORRELACION_PENDIENTE_DE_IMPLEMENTAR:** desfase P4 +0,1813 m; corrección
   `v'=v−0,1813` en las 3 rejillas horizontales de P4; NO aplicada al FE; hormigón P3→P4 sigue pendiente
   hasta verificar conectividad.
5. **D5 — HIPOTESIS_DE_GRUPO_PARA_ANALISIS:** V.S.I. → gran canto HA 0,20×1,50 m (pp≈157,4 kN), fuera del
   total; sensibilidad incluir/excluir; requiere confirmación documental de materialidad.
6. **D6 — ADOPTADA:** `V_EI_CP1S_x1010` (M.H.A. e=30) = muro del eje F (no viga); no-duplicación verificada.
7. **D7 — SOLO_SENSIBILIDAD:** banda 20,3–21,2 MN (≈3.168–4.046 kN, 18,4–23,6 %) NO adoptada como PP.