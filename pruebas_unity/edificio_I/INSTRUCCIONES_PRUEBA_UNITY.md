# Prueba visual aislada en Unity

## Archivos

Usar exclusivamente los archivos listados en `manifest_prueba_visual_unity.json` y las matrices de `matrices_transformacion_unity.json`.

## Reglas del importador

- Aplicar `JSON local -> sistema común -> Unity` una sola vez.
- No aplicar `DXF -> local`; esa matriz solo documenta la procedencia CAD.
- No centrar ni trasladar cada planta por separado.
- Respetar `losas[*].aberturas` y `losas[*].espesor` por losa.
- Mantener señalados los 8 elementos metálicos de P4 como `sin revisar`.
- No tratar alturas o extensiones verticales de columnas/muros como datos confirmados; no están declaradas.
- Usar `(X,Y,Z)=(u,cota,v)` y las cotas de nivel del manifiesto.

## Escena y resultados

Crear una escena separada. No reemplazar ni modificar la escena actual.

Entregar, con niveles y ejes identificados:

- Vista superior ortográfica.
- Elevación en dirección `u`.
- Elevación en dirección `v`.
- Vista en perspectiva.

Comparar esas cuatro salidas con `superposicion_candidata_comun.png` y `vista_3d_candidata_comun.png`.
Reportar también la versión de Unity, escala/unidades usadas y cualquier advertencia del importador.

La prueba no se considera ejecutada ni validada hasta revisar las imágenes y la salida real de Unity.
