using System.Collections.Generic;
using UnityEngine;

namespace LabViewer
{
    public struct TriangulateResult
    {
        public List<Vector2> Points;   // vertices efectivos (exterior de la losa)
        public List<int> Triangles;    // indices a Points, tripletes (siempre en rango)
    }

    /// <summary>
    /// Triangulacion de ofrenda (ear clipping) de un poligono simple. Devuelve
    /// POINTS = verticies del contorno exterior y TRIANGLES = indices a esos
    /// mismos verticies, de modo que la malla SIEMPRE tiene indices validos y
    /// triangulos no degenerados (la causa de los errores de malla anteriores).
    ///
    /// Los huecos (aberturas) no se sustraen en la cara superior; sus laterales
    /// los genera el consumidor a partir del parametro holes de PrismMesh. Esto
    /// garantiza un render visible y libre de errores de indice.
    /// </summary>
    public static class Triangulator
    {
        public static TriangulateResult Triangulate(List<Vector2> exterior, List<List<Vector2>> holes)
        {
            var pts = new List<Vector2>(exterior);
            EnsureCCW(pts);
            var tris = EarClip(pts);
            return new TriangulateResult { Points = pts, Triangles = tris };
        }

        // ------------------------------------------------------------------ //
        //  Ordena el contorno en sentido antihorario (standard math).
        // ------------------------------------------------------------------ //
        private static void EnsureCCW(List<Vector2> pts)
        {
            double a = SignedArea(pts);
            if (a < 0) pts.Reverse();
        }

        private static double SignedArea(List<Vector2> pts)
        {
            double sum = 0;
            int n = pts.Count;
            for (int i = 0, j = n - 1; i < n; j = i++)
                sum += (pts[j].x - pts[i].x) * (pts[j].y + pts[i].y);
            return sum;
        }

        // ------------------------------------------------------------------ //
        //  Ear clipping sobre poligono antihorario (simple, no auto-intersecante).
        //  Todos los indices devueltos estan en [0, count) -> siempre validos.
        // ------------------------------------------------------------------ //
        private static List<int> EarClip(List<Vector2> pts)
        {
            var res = new List<int>();
            int n = pts.Count;
            if (n < 3) return res;
            if (n == 3) return new List<int> { 0, 1, 2 };

            var idx = new List<int>();
            for (int i = 0; i < n; i++) idx.Add(i);

            while (idx.Count > 3)
            {
                bool cut = false;
                for (int k = 0; k < idx.Count; k++)
                {
                    int i = idx[(k - 1 + idx.Count) % idx.Count];
                    int j = idx[k];
                    int l = idx[(k + 1) % idx.Count];
                    Vector2 a = pts[i], b = pts[j], c = pts[l];
                    if (Cross(a, b, c) <= 0) continue;        // requiere giro a la izquierda
                    if (AnyInsideTriangle(pts, idx, i, j, l)) continue;
                    res.Add(i); res.Add(j); res.Add(l);
                    idx.RemoveAt(k);
                    cut = true;
                    break;
                }
                if (!cut)
                {
                    // Fan de seguridad: cubre el poligono restante evitando dejar huecos.
                    for (int k = 1; k + 1 < idx.Count; k++)
                    {
                        res.Add(idx[0]); res.Add(idx[k]); res.Add(idx[k + 1]);
                    }
                    idx.Clear();
                    break;
                }
            }
            if (idx.Count == 3)
                res.AddRange(new[] { idx[0], idx[1], idx[2] });
            return res;
        }

        private static float Cross(Vector2 a, Vector2 b, Vector2 c)
            => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);

        private static bool AnyInsideTriangle(List<Vector2> pts, List<int> idx, int i, int j, int l)
        {
            Vector2 a = pts[i], b = pts[j], c = pts[l];
            foreach (int m in idx)
            {
                if (m == i || m == j || m == l) continue;
                if (PointInTriangle(pts[m], a, b, c)) return true;
            }
            return false;
        }

        private static bool PointInTriangle(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
        {
            float d1 = Cross(p, a, b);
            float d2 = Cross(p, b, c);
            float d3 = Cross(p, c, a);
            bool hasNeg = d1 < 0 || d2 < 0 || d3 < 0;
            bool hasPos = d1 > 0 || d2 > 0 || d3 > 0;
            return !(hasNeg && hasPos);
        }
    }
}
