# INFORME MODELO_FIEL_3 (cierre de iteracion)

Clasificacion: REPRODUCIBLE_FULL_EXPORT_SIN_PP_PENDIENTES_NUEVOS (EI) / REPRODUCIBLE_FULL_EXPORT_PMADIC_PENDIENTE (EII)

## EDIFICIO I (G)
- PP confirmado: **17179.2261 kN** ; pendientes: 63; ipotesis cuantificadas NO aplicadas: 8453.55 kN
- PM.ADIC aplicada: **10244.1390 kN** (99 losas)
- G fiel v3: **42406.96 kN** ; OK ; vs v2 0.0000 ; vs checkpoint +17179.2261

## EDIFICIO II (G)
- PP confirmado: 25970.9993 kN ; PM.ADIC catalogo 6 familias, aplicada **0.0 kN** (cobertura 0.0%)
- G fiel v3: **25971.00 kN** ; OK

## Peso sismico

- EI: B_PRINCIPAL = **46516.43 kN** ; A_sensibilidad = 36272.29 kN
- EII: B = 28600.71 kN ; A = 28600.71 kN (PM.ADIC 0)
- Rango EI si se confirmara cimentacion: +8453.55 kN

## Verificaciones

- regresiones MODELO_FIEL_3: **42/42 OK** (OK)
- [OK] inventario_n_pendientes
- [OK] inventario_rango_cuantificado
- [OK] inventario_pp_m_tubular_20
- [OK] inventario_pp_m_tubular_5
- [OK] inventario_pp_m_hormigon_70
- [OK] inventario_aplicado_0
- [OK] mapeo_6_familias
- [OK] mapeo_aplicada_0
- [OK] mapeo_todo_ambiguo
- [OK] mapeo_conversion_A
- [OK] mapeo_conversion_D
- [OK] pm_ei_99_losas
- [OK] pm_ei_total_ledger
- [OK] pm_ei_delta_referencia
- [OK] pm_ei_suma_por_nivel
- [OK] gei_v3_equilibrio
- [OK] gei_v3_identidad_pp_pm
- [OK] gei_v3_vs_v2_0
- [OK] gei_v3_vs_checkpoint_pp_el
- [OK] gei_v3_checks_v1
- [OK] geii_v3_equilibrio
- [OK] geii_v3_identidad
- [OK] geii_v3_vs_v2_0
- [OK] geii_v3_artefacto_ok
- [OK] peso3_EI_WB_v1
- [OK] peso3_EI_WA_sensibilidad
- [OK] peso3_EII_AB_v1
- [OK] peso3_rango_EI_inventario
- [OK] unidades_masa_EI_B
- [OK] no_doble_conteo_EII_PMADIC
- [OK] pm_ei_ledger_vs_tabla
- [OK] conservacion_PP_confirmado
- [OK] export_presente
- [OK] export_presente
- [OK] export_presente
- [OK] export_presente
- [OK] export_presente
- [OK] export_presente
- [OK] figuras_plano700_5_niveles
- [OK] regresiones_v1
- [OK] regresiones_v2
- [OK] unittest_tests

Manifiesto: `MANIFIESTO_MODELO_FIEL_v3.csv` (28 archivos).
