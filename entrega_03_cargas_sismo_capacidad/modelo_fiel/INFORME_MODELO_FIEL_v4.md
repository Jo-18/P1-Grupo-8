# INFORME MODELO_FIEL_4 (cierre de iteracion)

Clasificacion: REPRODUCIBLE_FULL_EXPORT_SIN_PP_PENDIENTES_NUEVOS (EI) / REPRODUCIBLE_FULL_EXPORT_PMADIC_PENDIENTE (EII)

## Portabilidad (tarea 1)
- Copias internas en `data/externas/` con SHA procedencia: catalogo EI, areas_tributarias.csv, por_viga.json, eii_viewer.json.
- `config/cargas.json` -> `data/externas/...`; scan src/tests/config sin dependencias externas (solo cadenas de procedencia).

## EDIFICIO I (G) - reconciliacion id por id (tarea 2)
- PP confirmado: **17179.2261 kN** ; pendientes: 63 ; hipotesis informativas (no aplicadas): 8453.55 kN
- Categorias C1..C6: C1_real_FE_seccion_pendiente=9, C2_seccion_confirmada_tramo_pendiente=18, C3_hipotesis_base_nivel=4, C4_metalico_tubular_confirmado=17, C5_muro_una_sola_planta=19, C6_no_incluida=1.
- PM.ADIC aplicada: **10244.1390 kN** (99 losas); G fiel v3: 42406.9577 kN (OK)

## EDIFICIO II (G) - bloqueo PM.ADIC (tarea 3)
- PM.ADIC catalogo 6 familias (A-F); aplicada **0.0 kN** (cobertura 0.0%); estado: BLOQUEADO_FALTA_EVIDENCIA_POSICIONAL
- Archivo exacto a solicitar: `2017_67-700.dxf` (sha256 F86BB87FDC16FB4780DD17DCF8C456C6581FE10D089CD234FE09E85594C2B5CF).
- G fiel v3 conservado: **25970.9994 kN** (OK)

## Conservacion sin regenerar (tarea 4)
- Decision: **NO_REGENERAR** ; sin mapeo documental del PM.ADIC EII (plano 700 no versionado en el repo; ver BLOQUEO_PMADIC_EII_plano700)
- Verificaciones: OK ; peso EII A==B 28.600,71 (EI B 46.516,43 / A 36.272,29).

## Peso sismico (conservado v3)
- EI: B_PRINCIPAL = **46516.43 kN** ; A_sensibilidad = 36272.29 kN
- EII: B = A = 28600.71 kN (PM.ADIC 0)

## Verificaciones

- Regresiones MODELO_FIEL_4: **31/31 OK** (OK); base v3 42/42.
- Prueba aislada: unittest 28/28 ; regresiones v3 42/42 ; v4 31/31.
- Directorio aislado temporal: `C:\Users\josef\AppData\Local\Temp\opencode\p1_aislado_v4\entrega_03_cargas_sismo_capacidad` (eliminado tras la corrida).
- [OK] rec_9_9_checks
- [OK] rec_pendientes_63
- [OK] rec_por_categoria_68
- [OK] rec_categorias_C1_C6
- [OK] rec_pp_confirmado
- [OK] rec_hipotesis_informativo
- [OK] rec_igual_inventario
- [OK] rec_consistente_ledger
- [OK] rec_artefactos_csv_md
- [OK] bloq_estado
- [OK] bloq_6_familias_0_kN
- [OK] bloq_conversion_g
- [OK] bloq_dxf_exacto
- [OK] bloq_pdf_alternativo
- [OK] bloq_no_por_proximidad_no_regenerar
- [OK] bloq_consistencia_v3
- [OK] bloq_lugares_buscados
- [OK] cons_NO_REGENERAR_todo_ok
- [OK] cons_G_EI_EII
- [OK] cons_peso_sismico
- [OK] cons_pmadic_0_AeqB
- [OK] cons_peso3_EII
- [OK] port_copia_por_viga
- [OK] port_copia_eii_viewer
- [OK] port_copia_catalogo_I
- [OK] port_copia_areas_II
- [OK] port_config_I_interna
- [OK] port_config_II_interna
- [OK] port_scan_sin_externos
- [OK] regresiones_v3_42_42
- [OK] unittest_28_28

Manifiesto: `MANIFIESTO_MODELO_FIEL_v4.csv` (10 archivos).
