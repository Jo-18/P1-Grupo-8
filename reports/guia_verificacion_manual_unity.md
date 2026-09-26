# GUÍA DE VERIFICACIÓN MANUAL UNITY (Semana 5)

Escena: `viewer_unity/Assets/Scenes/Main.unity` (única). Unity 6000.5.10f1.
Estado de compilación: ver §0.2 (forzar refresh del editor abierto y revisar Consola).

## A. Entorno y datos

| # | Acción | Resultado esperado | Qué prueba |
|---|--------|--------------------|------------|
| 1 | Abrir `viewer_unity/` en Unity 6000.5.10f1 | Consola sin errores CS (0 errores) | Los scripts S05 (incl. `LabModificaciones.cs` editado) compilan |
| 2 | Revisar `StreamingAssets/lab_data/edificios/{I,II}/results/` | Existen `esfuerzos_FE_EDIFICIO_{I,II}.json` y `pm_capacidad_demanda_{I,II}.json` | El viewer tiene resultados FE y P-M válidos |
| 3 | Abrir `StreamingAssets/lab_data/manifest.json` | `generado_por: tools/export_lab_data.py` y 13 casos FE | Paquete de streaming íntegro |

## B. Carga y geometría

| # | Acción | Resultado esperado | Qué prueba |
|---|--------|--------------------|------------|
| 4 | Play | Escena carga sin excepciones | Pipeline StreamingAssets OK |
| 5 | Clic en un elemento | Panel laboratorio muestra `Seleccion: I.P1.Viga #id [tributaria X m2]` | Selección y dato tributario mapean receptor |
| 6 | Ver jerarquía | Niveles CP1S, P1, P2, P3, P4 visibles (Edificios I y II) | Estructura completa |

## C. M1 superposición lineal

| # | Acción | Resultado esperado | Qué prueba |
|---|--------|--------------------|------------|
| 7 | Panel esfuerzos: mover sliders λ (G/Q/EX/EY) | Esfuerzos cambian en vivo, sin banner rojo | Superposición lineal exacta (evidencia 1) |
| 8 | Lab → "Activar superposicion libre (sliders)" | Etiqueta verde "Lineal exacto: NO requiere reanalisis." | M1 correctamente categorizado |

## D. Reanálisis (M2/M3/M4)

| # | Acción | Resultado esperado | Qué prueba |
|---|--------|--------------------|------------|
| 9 | Seleccionar elemento → "Desactivar elemento (eliminar)" | Registro `[REANALISIS] ...` + banner rojo central | M2 dispara reanálisis |
| 10 | Seleccionar elemento → "Aplicar seccion (w x h)" | Registro REANALISIS + banner rojo | M3 registra cambio de rigidez |
| 11 | Lab M4: mover slider factor tributario (0–2) | HUD `factor x N`, banner rojo | M4 registra cambio de reparto |
| 12 | Observar banner rojo | 3 líneas: `modelo_fe_completo.py --g --sismo --combinadas` + "luego exportar_esfuerzos_funcional_para_viewer + pm_capacidad_demanda_hitob" | Corrección P3 visible en la UI |
| 13 | Botón "Reiniciar lab" | Registro 0 + banner verde "modelo sin modificaciones" | Restauración limpia |
| 16 | Botón "Exportar modificaciones (JSON)" | `modelo_modificado_lab.json` con `reanalisis_reproducible: "modelo_fe_completo.py --g --sismo --combinadas && exportar_esfuerzos_funcional_para_viewer && pm_capacidad_demanda_hitob"` | Registro exportable lleva el flujo corregido |

## E. P-M / D-C y esfuerzos

| # | Acción | Resultado esperado | Qué prueba |
|---|--------|--------------------|------------|
| 14 | Activar overlay de esfuerzos FE | Tubos FE con color por magnitud (I: 378 elem / 4914 vectores; II: 253 / 3289) | Overlay consume JSON FE exportado |
| 15 | Ver panel P-M (curva azul + punto demanda) | D/C razonable en la ficha del elemento | Curva P-M y D/C dinámicos |

---

## §0.3 Estado de los ítems 9, 10, 11, 12, 13, 16

No puedo ejecutar clics en el editor Unity (el batch está bloqueado por la instancia abierta y porque estas acciones requieren interacción manual). Estado verificado por código de cada ítem:

| Ítem | Verificación de código (hecha) | Estado |
|------|-----------------------------------------------------------------------------------|--------|
| 9 (M2) | `LabModificaciones.ToggleElemento` (L99-127): `SetActive(false)` + `_esf.OcultarFE` + `MarcarReanalisis` | Verificado por código; pendiente clic manual |
| 10 (M3) | `LabModificaciones.AplicarSeccion` (L130-146): parsea w/h, registra con REANALISIS; NO reconstruye malla visible (limitación) | Verificado por código; pendiente clic manual |
| 11 (M4) | `SetTribFactor` (L77) / `SetTribFactorGlobal` (L89-96) + slider (`DrawPanel` L336) + `MarcarReanalisis` | Verificado por código; pendiente clic manual |
| 12 (banner) | `DrawBannerReanalisis` (~L246-273): 3 líneas con los comandos reales | Verificado por código; **requiere recompilación Unity** (ver §0.2) |
| 13 (Reiniciar) | `LabModificaciones.Reiniciar` (L167-190): limpia registro/ocultos, `SetSuperposicion(false)`, banner verde | Verificado por código; pendiente clic manual |
| 16 (Exportar) | `LabModificaciones.Exportar` (L201-236): escribe `modelo_modificado_lab.json` con `reanalisis_reproducible` corregido | Verificado por código; pendiente clic manual |

## §0.2 Compilación de `LabModificaciones.cs`

- Los cambios aplicados fueron solo de contenido (docstring, cadena del JSON exportado, banner a 3 líneas), sin cambios estructurales.
- `%LOCALAPPDATA%\Unity\Editor\Editor.log` no refleja recompilación posterior a la edición (mtime anterior): el editor abierto aún no procesó el archivo cambiado.
- **Acción necesaria**: hacer clic en la ventana de Unity (o Ctrl+R) para forzar refresh/recompilación y confirmar 0 errores en la Consola (barra inferior sin "compiler errors"). Si hubiera error, será de compilación C# trivial de reportar (los cambios son texto).