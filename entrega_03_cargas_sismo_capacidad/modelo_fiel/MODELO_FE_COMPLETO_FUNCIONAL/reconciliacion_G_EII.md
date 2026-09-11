# Reconciliacion del caso G - MODELO_FE_COMPLETO_FUNCIONAL (Edificio II)

El G del II es auto-consistente: losas (PP estructural) + PP de elementos FE
(vigas/columnas/muros). PM.ADIC/SC lineales (kg/m) sin mapeo, la columna A1
(solo EII_CP4, no desciende) y las vigas por_resolver (V_031) quedan
PENDIENTE_DE_FUENTE y NO entran al caso G ni se inventan.

| Familia | Cantidad | Dimension | Peso unit. | Carga total (kN) | Como entra al caso G |
|---|---|---|---|---|---|
| Losas (PP estructural, espesor 0.15 x gamma) | 140 losas | 2550.18 m2 netas | e x 24.5166 | 9670.7592 | TB.calcular_cargas_nodales: PP sobre area neta |
| Vigas (seccion documento, 34/nivel) | 156 elementos FE | None | A*L*24.516625 | 11047.0932 | mitad del PP en cada extremo del tramo FE |
| Columnas (0.70x0.70, 8 ejes/nivel) | 32 tramos | None | A*L*24.516625 | 1522.3059 | idem; A1 (solo CP4) PENDIENTE_DE_FUENTE sin tramo |
| Muros (montantes t x L/2) | 64 montantes | None | A*L*24.516625 | 3494.8959 | idem; cada eje lleva t x L/2 (area total sin duplicar) |
| PM.ADIC superficial | 0 lineal kg/m sin mapeo | None | - | 0.0000 | PENDIENTE_DE_FUENTE: SC/PM.ADIC del EII son lineales (kg/m) sin mapeo al panio de losa; no se aplican |
| Columna A1 (EII_CP4, no desciende) | 1 eje | None | - | 0.0000 | PENDIENTE_DE_FUENTE: sin tramo ni apoyo documentado (no se inventa descenso) |
| Vigas por_resolver (V_031) | 5 vigas | None | - | 0.0000 | PENDIENTE_DE_FUENTE: seccion V_031 sin respaldo; la carga asignada a ellas se reporta aparte |
| Vigas sin soporte vertical documentado | 15 segmentos | None | - | 0.0000 | PENDIENTE_DE_FUENTE: extremos sin columna/muro en el nivel (portico perimetral izq., junta/acceso); no se inventa conexion |
| apoyos de losa sin FE (receptores ausentes) | 35 receptores | None | - | 0.0000 | PENDIENTE_DE_FUENTE: area tributaria asignada a receptores sin nodos FE (p.ej. viga por_resolver); no se inventa receptor |
| TOTAL G MODELO_FE_COMPLETO_FUNCIONAL | - - | None | - | 25735.0541 | PP losas + PP elementos FE (auto-consistente; sin referencia externa de G para el II) |

## Totales

- G MODELO_FE_COMPLETO_FUNCIONAL: **25735.0541 kN**
- Area neta de losas: 2550.18 m2
- PP losas: 9670.7592 kN | vigas: 11047.0932 kN | columnas: 1522.3059 kN | muros: 3494.8959 kN
- Densidad concreto (HIPOTESIS_DE_ANALISIS): 24.5166 kN/m3

## Pendientes fuera del G (reportados, no sumados)

- Columna A1 (no desciende): 1 eje(s)
- Vigas por_resolver (V_031): 5
- Vigas sin soporte vertical documentado: 15 segmentos
- apoyos de losa sin nodos FE: 0

## Nota de omision / duplicacion

El PP de elementos (vigas+columnas+muros FE) se aplica una vez por tramo/montante real; las losas aportan solo su PP estructural (e x gamma) por area neta. PM.ADIC/SC lineales, columna A1 y vigas por_resolver quedan PENDIENTE_DE_FUENTE y NO entran al G ni se inventan. Ningun peso se ajusta artificialmente para cuadrar.

