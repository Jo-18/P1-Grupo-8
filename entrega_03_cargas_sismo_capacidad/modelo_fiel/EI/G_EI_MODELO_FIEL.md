# G_EI_MODELO_FIEL (primera iteracion)

G antes (checkpoint, losas + PM.ADIC): **25227.73 kN** = {'CP1S': 2497.1523, 'P1': 6513.3433, 'P2': 5266.698, 'P3': 5715.7725, 'P4': 5234.7655}

PP confirmado aplicado (auditoria v2, cota inferior): **17179.23 kN** (vigas 14803.52 + columnas 2045.60 + muros 330.09)

G despues (fiel): **42406.96 kN**

## Pendientes explicitos (NO aplicados)

- tramos ficticios BASE->nivel (HIPOTESIS_FE): columnas 4223.82 kN / muros 3675.18 kN
- V.S.I. 20/150 de CP1S: PENDIENTE_SECCION (pp no cuantificado)
- desfase P4 +0.1813 m y cajas de ascensor de un solo plano: PENDIENTE_TRAMO
- muros de contencion del sotano: HIPOTESIS_CIMENTACION (554.54 kN, no adoptados)
- metalicos (V.M./P.M. y P.M.I.): fuera del total confirmado (seccion tubular confirmada pero tramo PENDIENTE_TRAMO)

## Verificaciones

| check | estado | detalle |
|---|---|---|
| suma_pp_igual_audit | OK | aplicado 17179.2261 vs audit 17179.2261 |
| identidad_AxLxG_vs_audit | OK | {"viga_AxLxG_kN": 14803.52, "viga_audit_kN": 14803.534, "columna_AxLxG_kN": 2045.5965, "columna_audit_kN": 2045.6003, "muro_AxLxG_kN": 330.0915, "muro_audit_kN": 330.0918} |
| longitud_fe_vs_audit | OK | 137 vigas + 43 col + 4 muros |
| cada_id_una_vez | OK | 184 de 184 ids contados una sola vez |
| equilibrio_vertical_antes | OK | Pz=25227.7316, Rz=25227.7316 |
| equilibrio_vertical_despues | OK | Pz=42406.9577, Rz=42406.9577 |
| losas_y_pm_adic_intactas | OK | delta esperado = 17179.2261, delta observado = 17179.2261 |

## Comparacion con el checkpoint (mismo solver)

- R_z antes = 25227.7316 kN  ->  R_z despues = 42406.9577 kN  (delta 17179.2261 kN)
- max |dz| antes = 0.10771983 m  ->  despues = 0.15438370 m
