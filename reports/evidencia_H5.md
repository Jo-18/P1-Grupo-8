# Evidencia H5: cambio de armadura y regeneración de la curva P-M

Prueba manual en Unity (pestaña MODIFICAR → *Armadura*, luego *Reanalizar ahora*) con OpenSees real.
El escenario se descartó y **no se guardó**: el modelo oficial permanece con 16φ28.

**Elemento:** `E1_287`, columna COL70/70 (edificio 1, piso CIELO_4), f'c = 35 MPa, fy = 420 MPa, 70 × 70 cm.

| Estado | Armadura | Ast (mm²) | ρ | DCR C1 | Combinación crítica |
|---|---|---|---|---|---|
| Original | 16φ28 | 9852 | 2,011 % | 0,392 | C1 (0,392) |
| Modificado | 20φ28 | 12315 | 2,513 % | 0,329 | C2 (0,343) |

- Más armadura aumenta la capacidad y baja el DCR de C1 de 0,392 a 0,329. Con el cambio la combinación crítica pasa a C2, con DCR 0,343 (cumple).
- Demanda en C1 sin cambio entre estados (P = 616,4 kN, M = 481,4 kN·m); en C2, P = 612,9 kN y M = 502,1 kN·m.
- Unity regeneró la curva P-M tras el reanálisis: el título del diagrama pasó de `COL70/70_16f28` a `COL70/70_20f28`, con Po = 18422,3 kN → 19383,4 kN.

## Capturas

1. [Original, 16φ28, C1](img/h5_E1_287_original_16f28_C1.png): Ast = 9852 mm², C = 0,392.
2. [Modificado, 20φ28, C1](img/h5_E1_287_modificado_20f28_C1.png): Ast = 12315 mm², C = 0,329.
3. [Modificado, 20φ28, C2 crítica](img/h5_E1_287_modificado_20f28_C2_critica.png): C = 0,343.

Pruebas automáticas relacionadas: `tests/test_h5_armadura.py` y `tests/test_capacidad.py`.
