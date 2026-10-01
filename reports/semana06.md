# Semana 6 — AVANCE: validación AR y cierre técnico

## Alcance

Esta entrega valida la cadena completa de realidad aumentada para un elemento estructural real del Edificio II. La aplicación reconoce un marcador físico, obtiene su pose, crea un *anchor*, coloca una viga a escala 1:10 y presenta sus esfuerzos internos previamente calculados.

El elemento demostrado es la viga `EII_CP2_V_029`, asociada en el snapshot de resultados al `elementTag = 489`, nodos `487 → 488`, sección `V.30/80` y longitud real `L = 3.05 m`.

## 1. Flujo AR

La secuencia implementada es:

```text
marker → pose → anchor → transform → elemento → resultado
```

1. **Marker.** ARCore reconoce la imagen `REF_EII_CP2_V_029`, registrada en `viewer_unity/Assets/AR/ReferenceImages/AR_REF_489.asset` con tamaño físico `0.30 × 0.30 m`.
2. **Pose.** `ARImageAnchorController.HandleImage()` lee la posición y la orientación de `ARTrackedImage.transform` y las guarda como `Pose(position, rotation)`.
3. **Anchor.** `CreateAnchorAsync()` crea un `ARAnchor` en esa pose. El contenido se hace hijo del anchor con posición y rotación locales nulas.
4. **Transform.** Las coordenadas estructurales se expresan en el sistema de Unity, se escalan por `s = 0.10` y se transforman mediante la pose del anchor.
5. **Elemento.** `ARBeam489Loader` busca exactamente el tag `489`, comprueba `viewer_id = EII_CP2_V_029` y genera una viga con longitud AR `0.305 m` y sección escalada `0.03 × 0.08 m`.
6. **Resultado.** `ARForceDiagram489` carga `diagramas_FE_tag489_G.json`, valida la identidad y dibuja las 51 estaciones de `N`, `Vy`, `Vz`, `T`, `My` o `Mz`. El teléfono no ejecuta un nuevo análisis estructural.

Archivos principales:

- `viewer_unity/Assets/AR/Scripts/ARImageAnchorController.cs`
- `viewer_unity/Assets/AR/Scripts/ARBeam489Loader.cs`
- `viewer_unity/Assets/AR/Scripts/ARForceDiagram489.cs`
- `viewer_unity/Assets/AR/Scripts/ARResult489Label.cs`

## 2. Transformación entre sistemas

### 2.1 Sistemas de coordenadas

El mapeo usado por el paquete de resultados es:

```text
OpenSees: (u, v, cota)
Unity:    (x, y, z) = (u, cota, v)
```

Para el elemento:

```text
p_i = (-3.35, 3.91, 4.265)
p_j = (-0.30, 3.91, 4.265)
L   = ||p_j - p_i|| = 3.05 m
```

### 2.2 Composición de transforms

Sea `P_os = (u, v, cota)` un punto de OpenSees. Primero se permutan sus componentes:

```text
P_u = (u, cota, v)
```

Luego se usa el nodo inicial como origen local y se aplica la escala `s = 0.10`:

```text
P_local = s · (P_u - P_i)
```

Finalmente se aplica la transformación rígida del anchor:

```text
P_mundo = T_anchor · P_local
        = R_anchor · P_local + t_anchor
```

donde `R_anchor` es la rotación detectada y `t_anchor` es la posición del marcador en el mundo AR.

En la implementación, la viga se construye entre los extremos escalados, se centra en `(a+b)/2` y se orienta con:

```text
Quaternion.FromToRotation(Vector3.right, dir.normalized)
```

Así, el eje local `X` del cubo coincide con el eje longitudinal de la viga. El diagrama comparte la pose y los ejes locales de la viga. Su amplitud se normaliza solo para visualización; esto no modifica los valores estructurales ni la escala longitudinal 1:10.

## 3. Precisión de alineamiento

La prueba física confirmó estabilidad visual al mover el teléfono, pero no incluyó un instrumento externo ni puntos de control, por lo que no existe un error metrológico certificado.

Como estimación simple se usa el ancho conocido del marcador:

```text
error aproximado = (desplazamiento observado / ancho observado del marker) · 0.30 m
```

Adoptando una tolerancia visual conservadora del `5 %` del ancho del marcador:

```text
e ≈ 0.05 · 0.30 m = 0.015 m = 1.5 cm
```

Por lo tanto, el error de alineamiento se estima **del orden de 1–2 cm en condiciones favorables**, no como medición certificada. Puede aumentar por iluminación deficiente, reflejos, impresión con escala incorrecta, poca textura, movimiento rápido o un ángulo de observación muy oblicuo.

Para medirlo formalmente se deben marcar puntos de control físicos, capturar al menos cinco poses y calcular el error medio y máximo entre la posición AR y la posición medida.

## 4. Resultados y correspondencia

### 4.1 Elemento demostrado

| Propiedad | Valor |
|---|---|
| Edificio | II |
| Nivel | `EII_CP2` |
| Tipo | Viga |
| Viewer ID | `EII_CP2_V_029` |
| OpenSees `elementTag` | `489` |
| Nodos | `487 → 488` |
| Sección | `V.30/80` |
| Longitud real | `3.05 m` |
| Escala AR | `1:10` |
| Longitud AR | `0.305 m` |
| Caso mostrado | `G` |

La evidencia de correspondencia está almacenada en `esfuerzos_FE_EDIFICIO_II.json`, donde el mismo registro contiene simultáneamente `tag = 489`, `viewer_id = EII_CP2_V_029`, nodos, sección, coordenadas y vector de fuerzas. Unity vuelve a verificar esa identidad antes de mostrar el elemento y el diagrama.

### 4.2 Vector de fuerzas del caso G

El vector local persistido es:

```text
[N_i, Vy_i, Vz_i, T_i, My_i, Mz_i,
 N_j, Vy_j, Vz_j, T_j, My_j, Mz_j]

[0, 0, +53.035246, -48.634120, -21.504977, 0,
 0, 0, -53.035246, +48.634120, -140.252523, 0]
```

Como el elemento no tiene cargas interiores, los diagramas se obtienen por equilibrio:

```text
N(x)  = N_i
Vy(x) = Vy_i
Vz(x) = Vz_i
T(x)  = T_i
My(x) = My_i + Vz_i·x
Mz(x) = Mz_i - Vy_i·x
```

El archivo `diagramas_FE_tag489_G.json` contiene 51 estaciones entre `x=0` y `x=3.05 m`:

| Magnitud | `x=0` | `x=L` | Forma |
|---|---:|---:|---|
| `N` | `0 kN` | `0 kN` | Nulo |
| `Vy` | `0 kN` | `0 kN` | Nulo |
| `Vz` | `+53.035246 kN` | `+53.035246 kN` | Constante |
| `T` | `−48.634120 kN·m` | `−48.634120 kN·m` | Constante |
| `My` | `−21.504977 kN·m` | `+140.252523 kN·m` | Lineal, cruza por cero |
| `Mz` | `0 kN·m` | `0 kN·m` | Nulo |

La etiqueta AR redondea a tres decimales: `Vz = +53.035 kN`, `T = −48.634 kN·m` y `My = −21.505 → +140.253 kN·m`.

### 4.3 Evidencia física

La prueba del 30 de septiembre de 2026 verificó en un teléfono Android:

- reconocimiento del marcador;
- obtención de la pose;
- creación del anchor;
- aparición de la viga `EII_CP2_V_029`;
- carga de las 51 estaciones;
- funcionamiento del selector `N | Vy | Vz | T | My | Mz`;
- permanencia del elemento y los diagramas bajo el mismo anchor.

![Prueba física AR — Vz](../docs/evidencia/semana_06_ar/telefono_vz.png)

![Prueba física AR — T](../docs/evidencia/semana_06_ar/telefono_t.png)

![Prueba física AR — My](../docs/evidencia/semana_06_ar/telefono_my.png)

## 5. QA final estructural

| Prueba | Estado |
|---|---|
| Equilibrio G | **OK** — EI: `Pz=Rz=39128.1197 kN`; EII: `Pz=Rz=25269.4564 kN` |
| Equilibrio Q | **OK** — EI: `Pz=Rz=11016.2083 kN`; EII: `Pz=Rz=7568.1279 kN` |
| Corte basal EX | **OK** — solución, equilibrio horizontal y corte basal verificados en EI y EII |
| Corte basal EY | **OK** — solución, equilibrio horizontal y corte basal verificados en EI y EII |
| Superposición | **OK** — 8/8 magnitudes verificadas por edificio; error relativo máximo `9.8e−16` en EI y `1.7e−13` en EII |
| `M-phi` | **OK como procedimiento de demostración** — flujo numérico implementado; armado real pendiente, por lo que no constituye diseño estructural |
| `P-M` columna | **OK como procedimiento de demostración** — demanda concurrente y curva visibles; capacidad depende de armado de hipótesis |
| `P-M` muro | **OK con limitación declarada** — caso EII tag 76 implementado; evaluación bloqueada como comprobación real por armadura de hipótesis |
| IDs Unity | **OK para el snapshot AR** — `489 ↔ EII_CP2_V_029`, nodos `487–488`; existe una brecha de reproducibilidad con el modelo actual |
| AR | **OK** — prueba física exitosa en Android: marker, pose, anchor, viga, diagramas y selector |

La aprobación de `M-phi` y `P-M` corresponde al funcionamiento del procedimiento y la visualización, no a la aprobación de diseño de una sección real.

## 6. Errores conocidos y limitaciones

1. **Snapshot distinto del modelo actual.** La aplicación AR utiliza un snapshot de 258 elementos que contiene el tag 489. El modelo regenerable actual tiene 253 elementos y excluye `EII_CP2_V_029` como `PENDIENTE_DE_FUENTE` por falta de soporte vertical documentado.
2. **No existe regeneración actual de extremo a extremo para el tag 489.** El repositorio contiene el vector persistido y el exportador de diagramas, pero no una corrida actual que vuelva a producir ese elemento con OpenSees.
3. **Verificación T31A no incluida.** El exportador menciona una reproducción del `localForce` desde desplazamientos, pero el script específico de esa verificación no está presente en la entrega.
4. **SHA de procedencia desactualizado.** `diagramas_FE_tag489_G.json` declara como fuente el SHA `79A7B6…`, mientras que el `esfuerzos_FE_EDIFICIO_II.json` entregado actualmente tiene SHA `EC2453…`. Los valores del tag coinciden, pero el enlace criptográfico debe regenerarse.
5. **Precisión AR no medida instrumentalmente.** El error de 1–2 cm es una estimación operativa, no un resultado de calibración.
6. **Un solo elemento y marcador.** El APK final está preparado para `REF_EII_CP2_V_029` y tag 489. Agregar otro elemento requiere incorporar su imagen de referencia y datos.
7. **Solo caso G en la demostración AR.** El JSON estructural contiene otros casos, pero el selector AR presentado corresponde a las seis magnitudes del caso G.
8. **Amplitud del diagrama normalizada.** La longitud y sección de la viga respetan la escala 1:10; la altura de las curvas es una escala gráfica normalizada y no una longitud física.
9. **Capacidad RC demostrativa.** `M-phi` y `P-M` utilizan armadura de demostración donde faltan parámetros reales; no deben presentarse como verificación de diseño.
10. **Dependencia de condiciones de captura.** Reflejos, impresión fuera de escala, iluminación deficiente o movimiento brusco pueden degradar el tracking.

## 7. Plan final

### Núcleo

Trabajo obligatorio para cerrar técnicamente la entrega:

1. Unificar el modelo y el snapshot: decidir si se restituye `EII_CP2_V_029` con respaldo estructural o se selecciona un elemento reproducible del modelo actual.
2. Regenerar desde OpenSees el resultado del elemento elegido y conservar el script exacto de reproducción.
3. Regenerar `esfuerzos_FE_EDIFICIO_II.json` y `diagramas_FE_tag489_G.json` con SHA coincidente.
4. Ejecutar nuevamente las validaciones estructurales, de correspondencia y de Unity.
5. Realizar una medición física de precisión con puntos de control y registrar error medio y máximo.
6. Mantener `reports/semana06.md` como documento único de cierre de la semana.

### Polish

Mejoras de presentación que no cambian el núcleo técnico:

- reducir el tamaño del rótulo para evitar que cubra la viga;
- mejorar contraste y jerarquía visual de texto, curva y ordenadas;
- añadir una indicación visible de tracking y pérdida temporal del marcador;
- mostrar claramente que la amplitud del diagrama está normalizada;
- incorporar una leyenda breve de unidades y convención de signos;
- repetir la prueba con distintas distancias, iluminaciones y ángulos.

### Honors

Extensiones opcionales de mayor complejidad:

- selección de múltiples elementos y marcadores;
- cambio de caso de carga `G/Q/EX/EY/U*` desde la interfaz AR;
- actualización automática de datos desde un pipeline OpenSees reproducible;
- oclusión, iluminación estimada y sombreado coherente con el entorno;
- calibración de precisión con marcadores múltiples o puntos de control;
- comparación simultánea entre geometría real, deformada y diagramas;
- visualización de incertidumbre y alertas cuando la calidad del tracking sea baja.

## Conclusión

La prueba AR cumple el flujo `marker → pose → anchor → transform → elemento → resultado` y demuestra en un teléfono real la correspondencia `489 ↔ EII_CP2_V_029`, junto con seis diagramas internos de 51 estaciones. El cierre técnico es satisfactorio para la demostración del snapshot, pero debe conservarse explícitamente la limitación principal: el modelo OpenSees actual no reproduce el tag 489 y se requiere reconciliar la topología para lograr trazabilidad regenerable de extremo a extremo.
