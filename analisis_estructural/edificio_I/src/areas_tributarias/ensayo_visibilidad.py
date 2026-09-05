"""
Ensayo geométrico EXPERIMENTAL: reparto por camino de distancia mínima dentro del dominio.

PROPÓSITO (NO sustituye el método de producción)
------------------------------------------------
Prototipo independiente para evaluar un criterio geométrico propio para tratar aberturas:
asignar cada celda al receptor cuya distancia de RECORRIDO dentro del dominio sea mínima.
El dominio permitido es el polígono exterior menos los interiores de las aberturas:
los recorridos pueden rodear huecos pero no atravesarlos ni salir del dominio.

Este módulo NO cambia el comportamiento predeterminado (nada lo importa), NO toca el
esquema canónico ni los casos de referencia. Es solo un ensayo.

MÉTODO
------
1) Grafo de visibilidad sobre los VÉRTICES OBSTÁCULO (anillos exterior y de aberturas).
   Arista entre dos vértices si el segmento recto está dentro del dominio (tolerancia
   numérica pequeña). Pesos = distancia euclidiana. Esto captura los giros de los caminos
   alrededor de los huecos (los caminos más cortos en dominios poligonales son cadenas
   poligonales por vértices obstáculo).

2) LLEGADA AL SEGMENTO RECEPTOR (aproximación documentada): cada receptor se discretiza
   en puntos muestreados cada `delta_r` m. La arista de llegada desde un vértice v es el
   mínimo |v - muestra| entre las muestras visibles desde v. ESTA discretización es un
   error propio del receptor, independiente del tamaño de celda de área; se identifica
   por separado (cota <= delta_r/2 a lo largo del receptor). No se reduce el receptor a
   su centro ni a sus extremos.

3) Para cada vértice v y receptor R se precalcula g_R(v) = distancia más corta en el
   grafo (por vértices) desde v hasta R (incluida la llegada a segmento).

4) Para cada CELDA p (los mismos centros que la malla de área):
   - llegada directa: distancia recta a R si el tramo p->punto está dentro del dominio;
   - o por grafo: min_{v visible desde p} [ |p - v| + g_R(v) ].
   Se asigna a R que minimiza la distancia de recorrido. Si ninguna es finita -> SIN ASIGNAR.

VISIBILIDAD: un tramo a-b se considera dentro del dominio si el segmento lineal está
contenido (o sobre el borde) de D con una TOLERANCIA NUMÉRICA pequeña `tol` (por defecto
1e-9 m). NO se reducen los huecos (no se aplica -0.05 m) ni se abren pasos artificiales.

SIN ASIGNAR: si una componente del dominio no tiene ningún receptor alcanzable, se
informa el área sin asignar; NO se reparte con fallback ni se oculta renormalizando.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import LineString, Point, Polygon

# --------------------------------------------------------------------------- #
# Utilidades de dominio
# --------------------------------------------------------------------------- #
def _vertices_obstaculo(dominio):
    """Devuelve (listas de vértices) de anillos exterior y de aberturas.

    Soporta Polygon y MultiPolygon (componentes desconectadas del dominio).
    """
    polys = list(dominio.geoms) if hasattr(dominio, "geoms") else [dominio]
    ext = []
    holes = []
    for p in polys:
        ext.extend(list(p.exterior.coords)[:-1])
        holes.extend(list(h.coords)[:-1] for h in p.interiors)
    return ext, holes


def _segmento_en_dominio(a, b, dominio_tol: Polygon) -> bool:
    """True si el segmento a-b está dentro (o sobre el borde) del dominio tolerado."""
    if np.allclose(a, b):
        return dominio_tol.covers(Point(a))
    seg = LineString([a, b])
    return dominio_tol.covers(seg)


class ExperimentoTributacionCamino:
    """Reparto experimental por camino más corto dentro del dominio."""

    def __init__(self, panel, tamano_celda: float = 0.025,
                 delta_r: float = 0.02, tol: float = 1e-9):
        self.panel = panel
        self.cs = tamano_celda
        self.delta_r = delta_r
        self.tol = tol
        self.dominio = panel.dominio
        self.dominio_tol = self.dominio.buffer(tol)
        self.receptores = panel.receptores_validos()

        # celdas (mismos centros que la malla de área del método de producción)
        from .tributacion import _generar_celdas
        self.celdas = _generar_celdas(self.dominio, tamano_celda)

        # vértices obstáculo
        self.ext, self.holes = _vertices_obstaculo(self.dominio)
        self.obst_verts = []
        for pt in self.ext + sum(self.holes, []):
            self.obst_verts.append((float(pt[0]), float(pt[1])))

        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        """Construye grafo de visibilidad sobre vértices obstáculo y tablas g_R."""
        n = len(self.obst_verts)
        INF = float("inf")

        # matriz de adyacencia de visibilidad
        # DIAGONAL CERO: la llegada directa desde el propio vértice es válida
        # (dist(i,i)=0). Sin esto, dist(i,i) queda en INF y g_R(v) puede omitir la
        # llegada directa desde v y forzar un ciclo/paso por otro vértice.
        adj = [[INF for _ in range(n)] for _ in range(n)]
        for i in range(n):
            adj[i][i] = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                a = self.obst_verts[i]; b = self.obst_verts[j]
                if _segmento_en_dominio(a, b, self.dominio_tol):
                    w = float(np.hypot(b[0] - a[0], b[1] - a[1]))
                    adj[i][j] = adj[j][i] = w

        # Floyd-Warshall (n pequeño)
        dist = [row[:] for row in adj]
        for k in range(n):
            dk = dist[k]
            for i in range(n):
                dik = dist[i][k]
                if dik == INF: continue
                di = dist[i]
                for j in range(n):
                    nd = dik + dk[j]
                    if nd < di[j]:
                        di[j] = nd
        self.grafo_dist = dist

        # llegada a cada receptor (muestreo del segmento)
        # g_R[v] = min_{v'} dist(v,v') + llegada(v', R)
        self.g_R: Dict[str, List[float]] = {}
        for R in self.receptores:
            llegada = self._llegada_receptor(R)
            gR = [
                min(dist[i][j] + llegada[j] for j in range(n))
                for i in range(n)
            ]
            self.g_R[R.id] = gR

        self._check_grafos()

    def _check_grafos(self):
        """Controles explícitos de consistencia del grafo de distancias.

        - Diagonal: grafo_dist[i][i] == 0.
        - Simetría: grafo_dist[i][j] == grafo_dist[j][i].
        - Desigualdad triangular: dist[i][j] <= dist[i][k] + dist[k][j] (tol numérica).
        - Para cada receptor R y vértice v con llegada visible:
            g_R[v] <= llegada[v]  (la llegada directa desde v debe ser candidata).
        Lanza AssertionError si alguna comprobación falla.
        """
        n = len(self.obst_verts)
        INF = float("inf")
        tol = 1e-6
        try:
            for i in range(n):
                assert self.grafo_dist[i][i] == 0.0, f"diagonal {i} no es 0"
            for i in range(n):
                for j in range(n):
                    a = self.grafo_dist[i][j]; b = self.grafo_dist[j][i]
                    if a == INF and b == INF:
                        continue  # ambos inalcanzables: simétricos (inf==inf; nan no es < tol)
                    assert abs(a - b) < tol, f"no simétrica ({i},{j}): {a} vs {b}"
            for i in range(n):
                for j in range(n):
                    dij = self.grafo_dist[i][j]
                    if dij == INF:
                        continue
                    for k in range(n):
                        dik = self.grafo_dist[i][k]; dkj = self.grafo_dist[k][j]
                        if dik == INF or dkj == INF:
                            continue
                        assert dij <= dik + dkj + tol, \
                            f"desigualdad triangular falla ({i},{j},{k})"
            # llegada directa desde el mismo vértice
            for R in self.receptores:
                llegada = self._llegada_receptor(R)
                gR = self.g_R[R.id]
                for v in range(n):
                    if llegada[v] != INF:
                        assert gR[v] <= llegada[v] + tol, \
                            f"g_R[{v}]>{llegada[v]} para {R.id}: omite llegada directa"
        except AssertionError as e:
            raise AssertionError(f"check de grafo fallido: {e}") from e

    def _llegada_receptor(self, R) -> List[float]:
        """Distancia de llegada desde cada vértice obstáculo al segmento R (muestreo)."""
        ax, ay = R.inicio; bx, by = R.fin
        L = R.longitud
        n_samples = max(int(np.ceil(L / self.delta_r)), 2)
        res = []
        for (vx, vy) in self.obst_verts:
            best = float("inf")
            for k in range(n_samples):
                t = k / (n_samples - 1)
                px, py = ax + t * (bx - ax), ay + t * (by - ay)
                if _segmento_en_dominio((vx, vy), (px, py), self.dominio_tol):
                    d = float(np.hypot(px - vx, py - vy))
                    if d < best:
                        best = d
            res.append(best)
        return res

    def _llegada_directa(self, p, R) -> float:
        """Distancia recta p->R si el tramo está dentro del dominio; si no, INF."""
        ax, ay = R.inicio; bx, by = R.fin
        dx = bx - ax; dy = by - ay; L2 = dx * dx + dy * dy
        if L2 <= 0:
            return _segmento_en_dominio(p, R.inicio, self.dominio_tol) and \
                float(np.hypot(p[0] - ax, p[1] - ay)) or 0.0
        t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2
        t = min(1.0, max(0.0, t))
        foot = (ax + t * dx, ay + t * dy)
        if _segmento_en_dominio(p, foot, self.dominio_tol):
            return float(np.hypot(p[0] - foot[0], p[1] - foot[1]))
        # si el pie está bloqueado, probar extremos
        best = float("inf")
        for e in (R.inicio, R.fin):
            if _segmento_en_dominio(p, e, self.dominio_tol):
                best = min(best, float(np.hypot(p[0] - e[0], p[1] - e[1])))
        return best

    # ------------------------------------------------------------------ #
    def asignar(self):
        """Asigna cada celda. Devuelve arrays: receptor_id por celda, distancia, sin_asignar."""
        INF = float("inf")
        n_celdas = len(self.celdas)
        asign = [None] * n_celdas
        dist = [INF] * n_celdas
        # vértices visibles desde cada celda (cache por proximidad no; calculo directo)
        # para acelerar: pre-calcular indices de vértices
        n_vert = len(self.obst_verts)
        for idx in range(n_celdas):
            p = (float(self.celdas[idx][0]), float(self.celdas[idx][1]))
            best_d = INF; best_r = None
            # directa por receptor
            for R in self.receptores:
                d = self._llegada_directa(p, R)
                if d < best_d:
                    best_d = d; best_r = R.id
            # por grafo
            for vi, v in enumerate(self.obst_verts):
                if not _segmento_en_dominio(p, v, self.dominio_tol):
                    continue
                dv = float(np.hypot(p[0] - v[0], p[1] - v[1]))
                # por receptor
                for R in self.receptores:
                    cand = dv + self.g_R[R.id][vi]
                    if cand < best_d:
                        best_d = cand; best_r = R.id
            asign[idx] = best_r
            dist[idx] = best_d
        return asign, dist

    # ------------------------------------------------------------------ #
    def areas_por_receptor(self, asign) -> Dict[str, float]:
        ac = self.cs ** 2
        areas = {R.id: 0.0 for R in self.receptores}
        sin_asignar = 0.0
        for r in asign:
            if r is None:
                sin_asignar += ac
            elif r in areas:
                areas[r] += ac
            else:
                sin_asignar += ac
        return areas, sin_asignar

    def camino_representativo(self, p, R_id):
        """Devuelve la cadena de puntos del camino más corto DE DOMINIO de p a R.

        Si la llegada es directa (tramo recto dentro del dominio), devuelve [p, pie].
        Si la llegada exige rodear huecos, reconstruye la cadena por vértices obstáculo
        (camino más corto en el grafo de visibilidad) hasta la muestra de llegada.
        """
        R = next(r for r in self.receptores if r.id == R_id)
        INF = float("inf")
        # --- llegada directa ---
        ax, ay = R.inicio; bx, by = R.fin
        dx = bx - ax; dy = by - ay; L2 = dx * dx + dy * dy
        if L2 > 0:
            t = min(1.0, max(0.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
            foot = (ax + t * dx, ay + t * dy)
            if _segmento_en_dominio(p, foot, self.dominio_tol):
                return [p, foot]

        # --- por grafo: vértice de salida v* óptimo ---
        best_v = None; best_val = INF
        for vi, v in enumerate(self.obst_verts):
            if _segmento_en_dominio(p, v, self.dominio_tol):
                cand = float(np.hypot(p[0] - v[0], p[1] - v[1])) + self.g_R[R_id][vi]
                if cand < best_val:
                    best_val = cand; best_v = vi
        if best_v is None:
            return [p]
        # reconstruir camino en el grafo desde best_v hacia el vértice de llegada óptimo
        # vértice objetivo = el que cierra la llegada mínima: minimiza dist(best_v,o)+llegada(o)
        n = len(self.obst_verts)
        obj = best_v
        best_target = INF
        llegada = self._llegada_receptor(R)
        for o in range(n):
            vig = self.grafo_dist[best_v][o] + llegada[o]
            if vig < best_target:
                best_target = vig; obj = o
        # camino best_v -> obj (Dijkstra con padres)
        chain = self._dijkstra_camino(best_v, obj)
        pts = [p] + [self.obst_verts[i] for i in chain]
        # punto de llegada: muestra visible del receptor más próxima desde el último vértice
        ult = self.obst_verts[obj]
        ns = max(int(np.ceil(R.longitud / self.delta_r)), 2)
        best_d = INF; best_pt = R.inicio
        for k in range(ns):
            tt = k / (ns - 1); px, py = ax + tt * (bx - ax), ay + tt * (by - ay)
            if _segmento_en_dominio(ult, (px, py), self.dominio_tol):
                d = float(np.hypot(px - ult[0], py - ult[1]))
                if d < best_d:
                    best_d = d; best_pt = (px, py)
        pts.append(best_pt)
        return pts

    def _dijkstra_camino(self, s, t):
        """Devuelve lista de índices del camino más corto en el grafo (con llega 0)."""
        n = len(self.obst_verts); INF = float("inf")
        d = [INF] * n; d[s] = 0.0
        padre = [-1] * n
        pq = [(0.0, s)]
        while pq:
            du, u = heapq.heappop(pq)
            if du > d[u]: continue
            for v in range(n):
                w = self.grafo_dist[u][v]
                if w == INF: continue
                nd = du + w
                if nd < d[v] - 1e-12:
                    d[v] = nd; padre[v] = u; heapq.heappush(pq, (nd, v))
        chain = []
        cur = t
        while cur != -1:
            chain.append(cur)
            if cur == s: break
            cur = padre[cur]
        chain.reverse()
        return chain
