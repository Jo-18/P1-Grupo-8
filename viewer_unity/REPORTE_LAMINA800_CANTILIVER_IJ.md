# REPORTE — Lámina 800 / Voladizo este I′–J (P3–P4, Edificio I)

**Alcance.** Sector I′–J (u≈44–52, v≈0–17), 4º nivel, entre cotas **+7.87 (P3)** y **+11.83 (P4)**.
Correlación de la elevación de la Lámina 800 (EJE 1–2–3) con los paquetes de planta P3/P4 del visor Unity.

**Convenciones.**
- `posicion` = `[u, cota, v]`; frame Unity `(X,Y,Z) = (u, cota, v)`.
- DXF→u,v: P3 `u=(x−535.00)/100`, `v=(4260.35−y)/100`; P4 `u=(x−490.30)/100`, `v=(6297.30−y)/100`.
- Se distingue **texto** (etiqueta `RLE-TEXTO-1`, coordenadas de rótulo = posición, NO geometría) de **elemento** (huella `RLE-PILAR`/`RLE-VIGA` = geometría física).
- Los tramos `base→7.87`/`base→11.83` de `columnas_tramos_ei.json` son hipótesis sintéticas de `marco.py`; **no** se usan como evidencia de altura real.

---

## 1. Miembros físicos entre +7.87 y +11.83 (sector I′–J, v≈0–17)

### 1.1 Paquete P3 (cota +7.87)

| ID | u | v | Sección | Estado |
|---|---|---|---|---|
| `COL_EI_CP3_S_IpJ1` | 46.35 | 0.55 | `V.M. 300x300x5` | confirmado (etiqueta) |
| `COL_EI_CP3_S_IpJ2` | 46.36 | 9.32 | `V.M. 300x300x5` | confirmado |
| `COL_EI_CP3_S_IpJ3` | 46.34 | 16.61 | `V.M. 300x300x5` | confirmado |
| `COL_EI_CP3_S_J1` | 48.68 | 0.55 | `V.M. 300x300x5` | confirmado |
| `COL_EI_CP3_S_J2` | 48.70 | 9.32 | `V.M. 300x300x5` | confirmado |
| `COL_EI_CP3_S_J3` | 48.90 | 16.61 | `V.M. 300x300x5` | confirmado |
| `COL_EI_CP3_S_JP1` | 47.78 | −0.60 | `P.M.I.` | **por_resolver** (solo rótulo) |
| `COL_EI_CP3_S_JP2` | 47.89 | 8.30 | `P.M.I.` | **por_resolver** |
| `COL_EI_CP3_S_JP3` | 47.82 | 15.51 | `P.M.I.` | **por_resolver** |
| `COL_EI_CP3_S_JP4` | 50.58 | −0.60 | `P.M.I.` | **por_resolver** |
| `COL_EI_CP3_S_JP5` | 50.82 | 8.61 | `P.M.I.` | **por_resolver** |
| `COL_EI_CP3_S_JP6` | 50.71 | 15.85 | `P.M.I.` | **por_resolver** |

### 1.2 Paquete P4 (cota +11.83)

| ID | u | v | Sección | Estado |
|---|---|---|---|---|
| `COL_EI_CP4_S_IpS1` | 45.97 | 1.36 | `P.M.I.` | **por_resolver** |
| `COL_EI_CP4_S_JS2` | 48.77 | 7.46 | `P.M.I.` | **por_resolver** |
| `COL_EI_CP4_S_JS3` | 51.97 | 8.12 | `P.M.I.` | **por_resolver** |
| `COL_EI_CP4_S_JS4` | 52.11 | 15.23 | `P.M.I.` | **por_resolver** |
| `COL_EI_CP4_S_JS5` | 48.73 | 17.30 | `P.M.I.` | **por_resolver** |
| `COL_EI_CP4_S_JS8` | 52.08 | −0.87 | `P.M.I.` | **por_resolver** |

Las P4 `IpS1`/`JS2/3/4/5/8` fueron **reclasificadas a "Referencias pendientes"** por `tools/apply_plan_frames.py`
(no caen sobre huella física ni tienen etiqueta legible; ver §Objetivo 3).

### 1.3 Filas de concreto (contexto de apoyo, mismas cotas)

- P3 concreto: `COL_EI_CP3_C_Ip1/2/3` (u=45.0, v=0/8.9/16.15) — apoyo **Ip**.
- P4 concreto: `COL_EI_CP4_C_Ip1/2/3` (u=45.0, v=0.18/9.08/16.33) — apoyo **Ip**.
- No existen columnas de concreto en J=50 (la fila J es metálica/solo voladizo).

---

## 2. Resolución de los 3 objetivos

### Objetivo 1 — Miembros físicos entre +7.87 y +11.83

El voladizo I′–J se compone, en la elevación de Lámina 800 **EJE 1–2–3**, de **2 verticales extremas** (I′≈u46.3 y J≈u48.7) más **2 grupos de montantes `P.M.I.`** (u≈47.8 y u≈50.7) que en la elevación se dibujan como **diagonales convergentes** hacia un **nudo superior a +11.83**. La distancia nominal de la elevación es **5.00 m = 2.55 + 2.45** y va de extremo I′ a extremo J.

- **No hay jiros entre forjados reconstruibles** solo con planta: las `RLE-VIGA` del sector I′–J son **caras de vigas de hormigón** (`V.60/80`, `V.40/60`) ya modeladas, y **no existen diagonales en planta**. Las diagonales/arriostramiento solo constan en la **elevación 800**, cuyo detalle de conexión es necesario para fijar topología exacta.

### Objetivo 2 — Endpoints vs. huellas de planta + IDs existentes

| Miembro elevación 800 | Etiqueta planta | ID existente (paquete) | Extremo inferior (P3, +7.87) | Extremo superior (P4, +11.83) | Paridad |
|---|---|---|---|---|---|
| Vertical I′ | `V.M. 300x300x5` (P3, u≈46.35) | `COL_EI_CP3_S_IpJ1/2/3` | u≈46.35, +7.87 | — | coincide con IpS1 **solo a +11.83** (alineación vertical pendiente) |
| Vertical J | `V.M. 300x300x5` (P3, u≈48.7) | `COL_EI_CP3_S_J1/2/3` | u≈48.7, +7.87 | — | coincide con JS2/JS5 (aproximado) |
| Diagonal/montante A | `P.M.I.` u≈47.8 (`JP1/2/3`) | `COL_EI_CP3_S_JP1/2/3` | u≈47.8, +7.87 | — | sin par en P4 (nudo superior en JS?) |
| Diagonal/montante B | `P.M.I.` u≈50.7 (`JP4/5/6`) | `COL_EI_CP3_S_JP4/5/6` | u≈50.7, +7.87 | — | sin par en P4 (nudo superior en JS3/JS4?) |
| Nudo superior | `P.M. 300x300x20` P4 | `COL_EI_CP4_S_JS3/JS4` (u≈52) | — | +11.83, u≈52 | coincide en nivel, posición a confirmar |
| Nudo superior | `P.M. 300x300x20` P4 | `COL_EI_CP4_S_JS2/JS5` (u≈48.7) | — | +11.83, u≈48.7 | coincide en nivel/x con vertical J |

**Hipótesis de la investigación (a validar con detalle de conexión 800):** varios `P.M.I.` de P3 que la
elevación muestra **solo como rótulos de texto en +7.87** son en realidad **diagonales/arriostramientos**
cuyo extremo superior alcanza +11.83, conectando al nudo P4. **No** corresponde forzar paridad por
proximidad; la topología exacta queda **pendiente** de leer el nudo de conexión.

### Objetivo 3 — Columnas P3 bajo el voladizo malinterpretadas en Unity

Todas las `P.M.I.` de P3 (`JP1..JP6`, más `FS3`/`GS4`) **carecen de geometría física** — solo posición de
rótulo (`RLE-TEXTO-1`, `ancho=peralte=0`). En el visor `BuildColumns` (`LabLoader.cs`) se detectan con la
condición **`estado_seccion=="por_resolver"` && `ancho<=0 && peralte<=0`** y se reclasifican como
**"Referencias pendientes"** (marcador lila compacto), **no** como columnas continuas entre forjados.

**Lista exacta reclasificada (8 en P3):** `JP1(47.78)`, `JP2(47.89)`, `JP3(47.82)`, `JP4(50.58)`,
`JP5(50.82)`, `JP6(50.71)`, `FS3(20.5)`, `GS4(30.51)` — cota +7.87.

- **Antes:** se dibujaban como prismas naranjas "pendiente" de altura completa entre **+3.91 y +7.87**.
- **Después:** son marcadores lilas compactos en su posición documentada (grupo `Referencias pendientes`); no se arrastran al forjado superior.
- **No se fabrica** geometría: las `P.M.I.` podrían ser diagonales, pero eso solo se demuestra con la
  elevación 800 (leer detalle de conexión). El resultado honesto: **el marco entre forjados no se reconstruye**.

---

## 3. Correlación ejes/dimensiones (verificación)

| Eje plano | u nominal (P3/P4) | Observación |
|---|---|---|
| E | 0 | concreto P3/P4 |
| F | 10 | concreto |
| G | 20 | concreto |
| H | 30 | concreto |
| I | 40 | concreto |
| Ip | 45 | concreto (`C_Ip*` u=45.0) |
| **I′** | ~46.3 | **metálico** `IpJ*` (P3) — extremo izq. voladizo |
| **J** | ~48.7 | **metálico** `J*` (P3) / `JS2,JS5` (P4) — extremo der. voladizo |
| (montantes) | ~47.8 / ~50.7 | `JP*` P.M.I. por_resolver |

La elevación 800 "extremes I′ y J; 5.00 m = 2.55+2.45; +7.87→+11.83" concuerda con: extremos metálicos en
u≈46.3 (I′) y u≈48.7 (J). Las filas concretas de apoyo están en Ip (u=45) y los montantes en u≈47.8/50.7,
consistentes con los 2 tramos de 2.55+2.45 m between the vertical extremes / montantes. La paridad exacta
de cotas de inserción no es directamente legible sin el detalle de conexión.

---

## 4. Ambigüedades / TODOs pendientes

1. **Topología / nudo de las 2 diagonales (u≈47.8 y u≈50.7):** cuáles convergen y a qué nudo P4 exacto
   (`JS2/JS3/JS4/JS5`) — requiere leer el **detalle de conexión de la Lámina 800**.
2. **Alineación vertical I′–P4:** `IpS1` (P4, u=45.97) vs. vertical `IpJ` (P3, u≈46.35) — confirmar paridad.
   Nota: coincide en zona, pero `IpS1` es `por_resolver`/`RefPendientes` (sin huella).
3. **Alineación vertical J–P4:** `J*` (P3, u≈48.7) vs. `JS2/JS5` (P4, u≈48.77/48.73) — coinciden; `JS3/JS4`
   (u≈52) caen fuera de la coordenada J y solo podrían ser nudo de diagonal, no extremo de vertical.
4. **Cotas de inserción vs. cota de conexión real** — la elevación usa 5.00 m nominales; los offsets de
   unión hacen ilegible la cota fina sin detalle.
5. **Verificación visual en Unity Editor** (capturas antes/después de la reclasificación) — pendiente de
   ejecutar en Play.
6. `columnas_tramos_ei.json` (`base→7.87`/`base→11.83`) **no** debe usarse como evidencia de altura (sintético).

---

## 5. Registro de lecturas (qué se leyó de cada fuente)

| Fuente | Qué se extrajo |
|---|---|
| `P3.json` (paquete) | 36 columnas: 18 concreto `P.70x70` (u=0/10/20/30/40/45 × v=0/8.9/16.15) + 6 `V.M.300x300x5` (`IpJ*`, `J*`) + `FS1/GS2` + 8 `P.M.I.` por_resolver (`JP*`, `FS3`, `GS4`), cota 7.87 |
| `P4.json` (paquete) | 18 concreto `P.70x70` (cota 11.83) + `IpS1`, `JS2/3/4/5/8` (por_resolver `P.M.I.`) + `GS6/HS7` (`P.M.300x300x20` confirmado) |
| `pdf102_alltext.txt` (P3) | Etiquetas de texto del sector I′–J: `V.M. 300x300x5` (x1960/2049), `P.M.I.` (x2037/2143), `P.70x70`, `V.60/80`, `300x300x20` (P.M.), `(ARR)`, `PASADA 45/30`, `45/15`, `45/30` |
| `pdf103_alltext.txt` (P4) | Etiquetas P4: `300x300x20` con `P.M.` (x2169/2044/1013/1393/1938/2170), `+V.I. 20/90 (2ºETAPA)`, `P.70x70`, `V.60/80` |
| `columnas_tramos_ei.json` | Estructura + tramos P3/P4 sector I′–J (todos `base_*`, sintéticos, no evidencian altura real) |
| `LabLoader.cs` (457–605) | `BuildColumns` + `FindEiTramo` (criterio `por_resolver`+`ancho<=0&peralte<=0`) |
| `REPORTE_QA_GEOMETRIA_UNITY.md` | Contexto §9.6/§10/§11, reclasificación `P.M.I.`→RefPendientes, huellas físicas P4 (44.92/47.46/49.79) |
| `CROP_EI800_EL_superior_izquierda.png` / `EI_LAM800_full.png` | Elevación 800, cotas +7.87/+11.83; imagen grande → se aborda por tiles (análisis de detalle de conexión pendiente) |

---

## 6. Estado final

| Item | Estado |
|---|---|
| Vigas de hormigón I′–J (`V.60/80`/`V.40/60`) | ya modeladas, sin duplicar |
| P3 `IpJ*`/`J*` (`V.M.300x300x5`) | **confirmado** (etiqueta) |
| P3 `JP*` (`P.M.I.`) | **RefPendientes** (8 reclasificadas) |
| P4 `IpS1`/`JS2/3/4/5/8` (sin huella física) | **RefPendientes** (reclasificadas) |
| Diagonales + topología entre forjados (Lám. 800) | **pendiente** (requiere detalle de conexión) |
| Miembros fabricados / conexiones cerradas | **0** |
| Originales fuente + análisis FE | **sin tocar** |
| Verificación visual en Editor (antes/después) | **pendiente de ejecutar** |
