# INFORME MODELO_FIEL — cargas y peso sismico de EI y EII (12 puntos)

## 1. Alcance
- **EI**: G = losas + PM.ADIC (checkpoint) + PP confirmado de la auditoria v2, aplicado sobre el mismo `Marco` FE (mismo solver).
- **EII**: G = corrida reproducible del proyecto (sin cambios), auditada contra la publicacion componente a componente.
- Mecanismo de integridad: manifests SHA-256 (`perfiles/`) sin tocar `results/` del checkpoint.

## 2. G checkpoint EI (antes) — por nivel

| nivel | G (kN) |
|---|---|
| CP1S | 2497.15 |
| P1 | 6513.34 |
| P2 | 5266.70 |
| P3 | 5715.77 |
| P4 | 5234.77 |
| **TOTAL** | **25227.73** |

## 3. PP confirmado aplicado (EI)
- Fuente: `weight_propio_teorico_EDIFICIO_I_v2.json` (auditoria v2, solo lectura); desglose vigas = 14.803,53 / columnas = 2.045,60 / muros = 330,09 kN (identidad A*L*gamma a <0,05 kN).
- Aplicado: **17179.23 kN**; reparto por camino estructural (fraccion por longitud del segmento FE a los extremos).

## 4. G despues (fiel) EI — por nivel y equilibrio

| nivel | G_fiel (kN) |
|---|---|
| CP1S | 3380.34 |
| P1 | 9592.41 |
| P2 | 9507.47 |
| P3 | 10839.73 |
| P4 | 9087.01 |
| **TOTAL** | **42406.96** |
- Equilibrio vertical: R_z=P_z=25227.7316; |dz|max antes 0.107720 m -> despues 0.154384 m.

## 5. Pendientes explicitos EI (NO aplicados)
- Tramos ficticios BASE->nivel: columnas 4223.82 / muros 3675.18 kN.
- Contencion del sotano: 554.54 kN (HIPOTESIS_CIMENTACION).
- V.S.I. 20/150 (PENDIENTE_SECCION), metalicos fuera (PENDIENTE_TRAMO), desfase P4 +0,1813 m y cajas de ascensor (PENDIENTE_TRAMO); n=63 pendientes, 1 no incluidas.

## 6. G EII (reproducible, sin cambios) — componentes

- losas (aplicada via mallado): reproducible = 9670.758325 kN (publicado = 9677.0267).
- losas (directa geometria publicada): reproducible = 9670.748464 kN (publicado = None).
- vigas (incluye V_031): reproducible = 11585.46643 kN (publicado = 11585.48).
- V_031 (subconjunto de vigas): reproducible = 179.461512 kN (publicado = incluido en vigas).
- columnas: reproducible = 1522.30434 kN (publicado = 1522.31).
- muros (pipeline A=t*(L/2) por montante): reproducible = 3192.470257 kN (publicado = 6521.26).
- Total reproducible: **25970.9994 kN** (n_nodos_cargados=151).

## 7. Brechas EII publicadas y plan de cierre
- Muros: 3328.79 kN (ver explicacion aritmetica en el ledger: identidad A=t*L da 4.330,02; A=t*L/2 por montante da 3.192,47; deficit 2.191,24 + 1.137,55).
- Losas: 6.27 kN (mallado vs directa geometrica).
- Ruteo: 417.85 kN (14 cargas SIN camino estructural, quedan en su nodo original).
- V_031 escenario V.30/80 (HIPOTESIS_MODELO) y rigidLinks de franja DD (n=32, HIPOTESIS enlazada; ver ledger).

## 8. Peso sismico por piso y por edificio (W = PP + 0.5 Q, q=2.0 kN/m2)

### EI — W total = 46516.43 kN

| nivel | z (m) | PP (kN) | Q (kN) | W (kN) | CM_W x/y (m) |
|---|---|---|---|---|---|
| sotano nucleo (z -7.01) | -7.01 | 172.78 | 52.21 | 198.88 | 10.899394 / -10.819 |
| CP1S | -4.01 | 3374.07 | 721.85 | 3734.99 | 7.415598 / 1.99845 |
| P1 | -0.05 | 9854.05 | 2011.46 | 10859.78 | 25.840775 / 7.975636 |
| P2 | 3.91 | 9672.51 | 1698.46 | 10521.74 | 22.493128 / 8.264426 |
| P3 | 7.87 | 10246.53 | 1865.05 | 11179.06 | 25.094627 / 8.233534 |
| P4 | 11.83 | 9087.01 | 1869.91 | 10021.97 | 25.622269 / 8.248337 |

### EII — W total = 28600.71 kN

| nivel | z (m) | PP (kN) | Q (kN) | W (kN) | CM_W x/y (m) |
|---|---|---|---|---|---|
| EII_CP1S | -4.01 | 4893.85 | 1062.04 | 5424.88 | 10.503962 / 7.851121 |
| EII_CP1 | -0.05 | 5483.30 | 1062.04 | 6014.32 | 10.516022 / 7.93752 |
| EII_CP2 | 3.91 | 5438.49 | 1062.22 | 5969.60 | 10.414114 / 7.99942 |
| EII_CP3 | 7.87 | 5410.05 | 1062.04 | 5941.07 | 10.335359 / 8.010607 |
| EII_CP4 | 11.83 | 4745.31 | 1011.08 | 5250.85 | 10.271502 / 7.938049 |

- Total ambos edificios: **75117.14 kN**
- Rango posible: EI [46516.43, 54969.97] kN ; EII [28600.71, 32353.62] kN.
- Nota EI: el rango no incluye pendientes no cuantificados (V.S.I. y metalicos); el superior suma los cuantificados (8.453,55 kN).

## 9. Comparacion checkpoint vs fiel vs publicado

- **EI**: checkpoint 25227.73 | PP fiel 17179.23 | **fiel 42406.96** kN ; publicado (componentes): vigas=14803.534, columnas=2045.6003, muros=330.0918.
- **EII**: checkpoint 25971.00 | PP fiel 25971.00 | **fiel 25971.00** kN ; publicado (componentes): losas=9677.0267, vigas=11585.48, columnas=1522.31, muros=6521.26.

- check ck_ei: OK (checkpoint EI 25227.7316)
- check fiel_ei: OK (fiel EI 42406.9577)
- check suma_pp_por_nivel: OK (PP EI tributario por nivel 17179.2261)
- check paridad_por_nivel: OK (checkpoint+PP = fiel en todos los pisos (tributario))
- check eii_publicado_vs_fiel: OK (ambos totales EII cuantificados)

## 10. Regresiones (no regresion vs checkpoint)
- **17/17** checks pasan (artefactos, invariantes, manifest del checkpoint y `pytest tests/cargas`).
  - peso_EI_W=PP+05Q: OK (46516.4301)
  - peso_EI_PP==G_despues: OK (PR fiel 42406.9577 vs G_despues 42406.9577)
  - peso_EI_Q_total: OK (Q EI por piso)
  - peso_EII_ck==fiel_EII_CP1S: OK (4893.8546)
  - peso_EII_ck==fiel_EII_CP1: OK (5483.2985)
  - peso_EII_ck==fiel_EII_CP2: OK (5438.4876)
  - peso_EII_ck==fiel_EII_CP3: OK (5410.0473)
  - peso_EII_ck==fiel_EII_CP4: OK (4745.3114)
  - comparacion_EI_fiel==ledger: OK (42406.9577)
  - comparacion_EII_fiel==ledger: OK (25970.999352)
  - artefacto_G_EI: OK (verificaciones 7/7)
  - artefacto_LEDGER_EI: OK (verificaciones 7/7)
  - artefacto_G_EII: OK (verificaciones 6/6)
  - artefacto_PESO: OK (verificaciones 6/6)
  - artefacto_COMP: OK (verificaciones 5/5)
  - manifest_checkpoint: OK (})
  - pytest_tests_cargas: OK (11 passed in 0.03s)

## 11. Verificaciones transversales
- EI: equilibrio vertical antes y despues (|Rz-Pz|<1e-4), identidad A*L*gamma vs audit, 184 ids sin repetir, losas y PM.ADIC intactas, longitud FE vs audit.
- EII: G igual al checkpoint, equilibrio vertical (residuo 0), identidad cargas vs geometria, 14 ruteos pendientes 14 ruteos pendientes, no doble conteo por clave unica.

## 12. Entregables y estado
- Artefactos bajo `modelo_fiel/`: `EI/G_EI_MODELO_FIEL*.{json,ledger.json,csv,comparacion.json,md}`, `EII/G_EII_MODELO_FIEL*.{json,ledger.json,csv,md}`, `peso_sismico_MODELO_FIEL.{json,csv,md}`, `comparacion_MODELO_FIEL.{json,md}`, `regresiones_MODELO_FIEL.json`, `INFORME_MODELO_FIEL.md`, `perfiles/*_manifest.json`.

Estado de Git (pista de trabajo, raiz del repo):
```
M viewer_unity/ProjectSettings/ProjectAuditorSettings.asset
?? entrega_03_cargas_sismo_capacidad/docs/PLAN_COMPLETAR_MODELOS_EI_EII.md
?? entrega_03_cargas_sismo_capacidad/modelo_fiel/
?? entrega_03_cargas_sismo_capacidad/src/modelo_fiel/
?? laboratorio_semana2/
?? viewer_unity/PROPUESTA_MARCO_II_ELEV800.md
```

Pendiente: crear el manifest `modelo_fiel` tras este informe (hashea todas las salidas nuevas) y decidir commits con el grupo.
