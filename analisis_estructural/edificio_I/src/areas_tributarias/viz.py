"""
Visualizacion de resultados de areas tributarias.

Genera (si matplotlib esta disponible):
  - planta del paño con celdas coloreadas por receptor (viga/muro) y los
    receptores dibujados como segmentos finitos;
  - perfil de ancho tributario / carga lineal por receptor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from shapely.geometry import Polygon

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _HAY_MPL = True
except Exception:  # pragma: no cover
    _HAY_MPL = False

from .modelo import ModeloGeometria, Receptor
from .tributacion import ResultadoPanel


def _dibujar_poligono(ax, poly, **kw):
    p = np.asarray(poly, dtype=float)
    if p.size == 0:
        return
    p = np.vstack([p, p[0]])
    ax.plot(p[:, 0], p[:, 1], **kw)


def _dibujar_receptor(ax, r: Receptor, **kw):
    ax.plot([r.inicio[0], r.fin[0]], [r.inicio[1], r.fin[1]], **kw)


def graficar_planta(
    modelo: ModeloGeometria,
    por_panel: Dict[str, ResultadoPanel],
    ruta: str,
) -> bool:
    if not _HAY_MPL:
        return False
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 7))
    cmap = plt.get_cmap("tab10")
    for pi, panel in enumerate(modelo.panels):
        pr = por_panel[panel.id]
        _dibujar_poligono(ax, panel.poligono, color="k", lw=1.5)
        # aberturas
        for ab in panel.aberturas:
            _dibujar_poligono(ax, ab.poligono, color="w", lw=1.0, ls="--")
        # celdas por receptor
        for ri, r in enumerate(pr.regiones):
            color = cmap(ri % 10)
            celdas = r.celdas
            if celdas is not None and celdas.size:
                ax.scatter(celdas[:, 0], celdas[:, 1], s=6, color=color,
                           alpha=0.6, linewidths=0)
        # receptores
        for ri, r in enumerate(pr.regiones):
            color = cmap(ri % 10)
            _dibujar_receptor(ax, r.receptor, color=color, lw=3)
            c = np.mean(celdas, axis=0) if (r.celdas is not None and r.celdas.size) else None
            if c is not None:
                ax.text(c[0], c[1], f"{r.receptor.id}\n{r.area:.2f} m2",
                        ha="center", va="center", fontsize=8)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]")
    ax.set_title(f"Regiones tributarias (celdas) - {modelo.nivel.get('id','')}")
    ax.grid(True, ls=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return True


def graficar_perfiles(
    modelo: ModeloGeometria,
    por_panel: Dict[str, ResultadoPanel],
    ruta: str,
) -> bool:
    if not _HAY_MPL:
        return False
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    npan = len(modelo.panels)
    fig, axes = plt.subplots(npan, 1, figsize=(7, 3.5 * max(npan, 1)), squeeze=False)
    for ai, panel in enumerate(modelo.panels):
        ax = axes[ai][0]
        pr = por_panel[panel.id]
        for r in pr.regiones:
            if r.s is None or r.w is None or r.s.size < 2:
                continue
            ax.plot(r.s, r.w, label=r.receptor.id)
        ax.set_xlabel("s a lo largo del receptor [m]")
        ax.set_ylabel("carga lineal w(s) [kN/m]")
        ax.set_title(f"Perfil de carga lineal - {panel.id}")
        ax.legend(fontsize=7)
        ax.grid(True, ls=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return True
