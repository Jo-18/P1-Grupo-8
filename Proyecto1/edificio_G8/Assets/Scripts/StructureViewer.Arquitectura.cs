using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

/// <summary>
/// Capa de ARQUITECTURA del viewer: SOLO VISUAL.
///
/// Dibuja la fachada (vidrio al sur, ventanas con aletas naranjas al norte, terracota al oeste,
/// caja naranja y entrada principal en el extremo este), el terreno en dos niveles (plaza de la
/// entrada a la altura del piso 2, terrazas de la cafeteria en el nivel inferior), la escalera
/// naranja de la fachada sur con su plataforma y la escalinata, la escalera norte de dos tramos,
/// la sala de Metodos Computacionales (6 mesas altas con taburetes) y la cafeteria bajo la sala,
/// a partir de Resources/arquitectura_visual.json (lo genera scripts/generar_arquitectura.py).
///
/// No es parte del modelo de OpenSees ni cambia ningun valor: no se toca el JSON de la
/// estructura, las mallas no tienen collider (no se seleccionan ni tapan clics) y no se
/// registran como elementos. La fachada y el entorno se ocultan solos en la vista
/// estructural (diagrama, deformada, utilizacion o filtro de un piso), y en ese caso el pasto
/// vuelve a su nivel bajo los apoyos para que se vea el subterraneo.
/// </summary>
public partial class StructureViewer
{
    [System.Serializable] private class ArqMaterial { public string nombre; public float r, g, b, a = 1f; }

    [System.Serializable]
    private class ArqGrupo
    {
        public string nombre, capa, piso, material;
        public float[] cajas;    // [x0, x1, y0, y1, z0, z1] por caja, ejes del modelo
        public float[] hexas;    // 8 esquinas (x, y, z) por prisma, ejes del modelo
    }

    [System.Serializable]
    private class ArqDatos
    {
        public int version;
        public string nota;
        public float nivelTerreno = -0.2f;
        public ArqMaterial[] materiales;
        public ArqGrupo[] grupos;
    }

    private bool showFachada = true;
    private bool showEntorno = true;
    private bool showMobiliario = true;
    private readonly List<GameObject> arqFachada = new List<GameObject>();
    private readonly List<GameObject> arqEntorno = new List<GameObject>();
    private readonly List<GameObject> arqMobiliario = new List<GameObject>();
    private readonly List<GameObject> arqMobiliarioExterior = new List<GameObject>();
    private Transform pastoTerreno;
    private float pastoYEstructural;
    private float pastoYArquitectura = -0.2f;

    public bool ShowFachadaLayer { get => showFachada; set => showFachada = value; }
    public bool ShowEntornoLayer { get => showEntorno; set => showEntorno = value; }
    public bool ShowMobiliarioLayer { get => showMobiliario; set => showMobiliario = value; }
    /// true si hay arquitectura cargada (existe Resources/arquitectura_visual.json).
    public bool HayArquitectura { get; private set; }

    /// Vista estructural: se ve un diagrama o la deformada, la utilizacion o un solo piso.
    /// En ella la fachada y el entorno se ocultan para no tapar la estructura.
    public bool VistaEstructural =>
        (diagramController != null && diagramController.MostrandoResultado) || showUtilization || floorIndex > 0;

    private void CreateArquitectura()
    {
        arqFachada.Clear();
        arqEntorno.Clear();
        arqMobiliario.Clear();
        arqMobiliarioExterior.Clear();
        HayArquitectura = false;

        Transform pasto = transform.Find("Env_Pasto");
        pastoTerreno = pasto;
        if (pasto != null) pastoYEstructural = pasto.position.y;

        TextAsset texto = Resources.Load<TextAsset>("arquitectura_visual");
        if (texto == null) return;   // sin arquitectura: el viewer queda como antes
        ArqDatos datos;
        try
        {
            datos = JsonUtility.FromJson<ArqDatos>(texto.text);
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("[Arquitectura] No se pudo leer arquitectura_visual.json: " + e.Message);
            return;
        }
        if (datos == null || datos.grupos == null) return;
        pastoYArquitectura = datos.nivelTerreno;

        var materiales = new Dictionary<string, Material>();
        if (datos.materiales != null)
        {
            foreach (ArqMaterial m in datos.materiales)
            {
                if (m == null || string.IsNullOrEmpty(m.nombre)) continue;
                materiales[m.nombre] = CreateMaterial(new Color(m.r, m.g, m.b, m.a));
            }
        }

        var raiz = new GameObject("Arquitectura (solo visual)");
        raiz.transform.SetParent(transform, false);
        var vertices = new List<Vector3>();
        var triangulos = new List<int>();
        var esquinas = new Vector3[8];

        foreach (ArqGrupo g in datos.grupos)
        {
            if (g == null) continue;
            vertices.Clear();
            triangulos.Clear();
            if (g.cajas != null)
            {
                for (int i = 0; i + 5 < g.cajas.Length; i += 6)
                {
                    float x0 = g.cajas[i], x1 = g.cajas[i + 1], y0 = g.cajas[i + 2], y1 = g.cajas[i + 3], z0 = g.cajas[i + 4], z1 = g.cajas[i + 5];
                    esquinas[0] = ModeloAUnity(x0, y0, z0); esquinas[1] = ModeloAUnity(x1, y0, z0);
                    esquinas[2] = ModeloAUnity(x1, y1, z0); esquinas[3] = ModeloAUnity(x0, y1, z0);
                    esquinas[4] = ModeloAUnity(x0, y0, z1); esquinas[5] = ModeloAUnity(x1, y0, z1);
                    esquinas[6] = ModeloAUnity(x1, y1, z1); esquinas[7] = ModeloAUnity(x0, y1, z1);
                    AgregarPrisma(vertices, triangulos, esquinas);
                }
            }
            if (g.hexas != null)
            {
                for (int i = 0; i + 23 < g.hexas.Length; i += 24)
                {
                    for (int k = 0; k < 8; k++)
                        esquinas[k] = ModeloAUnity(g.hexas[i + 3 * k], g.hexas[i + 3 * k + 1], g.hexas[i + 3 * k + 2]);
                    AgregarPrisma(vertices, triangulos, esquinas);
                }
            }
            if (vertices.Count == 0) continue;

            var malla = new Mesh { name = g.nombre, indexFormat = IndexFormat.UInt32 };
            malla.SetVertices(vertices);
            malla.SetTriangles(triangulos, 0);
            malla.RecalculateNormals();
            malla.RecalculateBounds();

            var go = new GameObject(g.nombre);
            go.transform.SetParent(raiz.transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = malla;
            var rend = go.AddComponent<MeshRenderer>();
            if (!materiales.TryGetValue(g.material ?? "", out Material mat))
            {
                mat = CreateMaterial(Color.gray);
                materiales[g.material ?? ""] = mat;
            }
            rend.sharedMaterial = mat;
            bool transparente = mat.color.a < 0.99f;
            rend.shadowCastingMode = transparente ? ShadowCastingMode.Off : ShadowCastingMode.On;
            rend.receiveShadows = !transparente;
            // sin collider: no se selecciona ni intercepta los clics sobre la estructura

            switch (g.capa)
            {
                case "fachada": arqFachada.Add(go); break;
                case "entorno": arqEntorno.Add(go); break;
                case "mobiliario_exterior": arqMobiliarioExterior.Add(go); break;
                default: arqMobiliario.Add(go); break;
            }
            if (!string.IsNullOrEmpty(g.piso)) RegisterFloor(go, g.piso);
        }
        HayArquitectura = arqFachada.Count + arqEntorno.Count + arqMobiliario.Count + arqMobiliarioExterior.Count > 0;
        ActualizarArquitectura();
    }

    /// Modelo (x, y, z con z hacia arriba) -> Unity (x, z, y), igual que los nodos del viewer.
    private static Vector3 ModeloAUnity(float x, float y, float z) => new Vector3(x, z, y);

    /// Agrega un prisma de 8 esquinas (0-3 abajo, 4-7 arriba) con caras planas y normales hacia afuera.
    private static void AgregarPrisma(List<Vector3> v, List<int> t, Vector3[] c)
    {
        Vector3 centro = Vector3.zero;
        for (int i = 0; i < 8; i++) centro += c[i];
        centro /= 8f;
        for (int f = 0; f < 6; f++)
        {
            Vector3 a = c[Caras[f, 0]], b = c[Caras[f, 1]], cc = c[Caras[f, 2]], d = c[Caras[f, 3]];
            Vector3 n = Vector3.Cross(b - a, cc - a);
            if (n.sqrMagnitude < 1e-12f) n = Vector3.Cross(cc - a, d - a);
            if (n.sqrMagnitude < 1e-12f) continue;   // cara degenerada (vertice del quitasol)
            int i0 = v.Count;
            if (Vector3.Dot(n, (a + b + cc + d) * 0.25f - centro) >= 0f)
            {
                v.Add(a); v.Add(b); v.Add(cc); v.Add(d);
            }
            else
            {
                v.Add(d); v.Add(cc); v.Add(b); v.Add(a);
            }
            t.Add(i0); t.Add(i0 + 1); t.Add(i0 + 2);
            t.Add(i0); t.Add(i0 + 2); t.Add(i0 + 3);
        }
    }

    private static readonly int[,] Caras = { { 0, 1, 2, 3 }, { 4, 5, 6, 7 }, { 0, 1, 5, 4 }, { 1, 2, 6, 5 }, { 2, 3, 7, 6 }, { 3, 0, 4, 7 } };

    /// Visibilidad de la capa (se llama desde RefreshVisibility en cada OnGUI).
    private void ActualizarArquitectura()
    {
        if (!HayArquitectura) return;
        bool arquitectonica = !VistaEstructural;
        SetGroupVisible(arqFachada, showFachada && arquitectonica);
        SetGroupVisible(arqEntorno, showEntorno && arquitectonica);
        SetGroupVisible(arqMobiliario, showMobiliario);
        SetGroupVisible(arqMobiliarioExterior, showMobiliario && showEntorno && arquitectonica);
        // con el entorno a la vista, el pasto sube al nivel inferior del terreno (terrazas de la
        // cafeteria; el subterraneo queda bajo tierra); en la vista estructural vuelve bajo los
        // apoyos y el subterraneo se ve completo
        if (pastoTerreno != null)
        {
            float y = showEntorno && arquitectonica ? pastoYArquitectura : pastoYEstructural;
            Vector3 p = pastoTerreno.position;
            if (Mathf.Abs(p.y - y) > 1e-4f) pastoTerreno.position = new Vector3(p.x, y, p.z);
        }
    }
}
