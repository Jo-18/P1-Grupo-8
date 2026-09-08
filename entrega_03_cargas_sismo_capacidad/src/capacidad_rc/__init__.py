"""Capacidad RC por secciones con fibras (Fiber Section). Herramienta independiente.

Genera secciones de columna RC arbitrarias, las discretiza tipo 'Fiber Section'
(patron de OpenSees: seccion('Fiber') + comandos fiber), y obtiene curva M-phi,
primeros puntos de P-M, figuras y salidas JSON/CSV. Sin GUI ni integracion a Unity.

Materiales implementados con las mismas familias de OpenSees:
  - hormigon: parabola ascendente (Concrete01 / Hognestad) + rama lineal de descenso;
  - acero: elastico-plastico con endurecimiento lineal (family Steel02 simplificada).
Requisitos: numpy, matplotlib. Opcional: openseespy (solo para cross-check).
Ningun valor de los edificios se usa aqui si falta: el ejemplo es DEMOSTRACION_ARBITRARIA.
"""