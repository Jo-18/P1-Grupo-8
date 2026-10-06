using System.Collections.Generic;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// SQ4 · Persona sobre la losa (carga movil asociada al usuario).
/// Una persona (carga puntual P) camina por un piso. En cada posicion:
///   1. se identifica el pano de losa que pisa;
///   2. se resaltan las vigas que reciben su carga;
///   3. se muestra cuanto recibe cada viga.
/// Regla fisica: reparto en dos direcciones de Grashof-Rankine. La franja en x lleva la
/// fraccion alfa = Ly^4 / (Lx^4 + Ly^4) (la franja corta es la mas rigida y lleva mas) y la
/// franja en y lleva 1 - alfa. Cada franja entrega su parte a sus dos bordes con la regla de
/// la palanca. La carga se conserva: la suma de lo asignado es P.
/// Es un reparto estatico de la losa a las vigas: instantaneo, sin reanalisis.
/// </summary>
public class PersonaSQ4 : MonoBehaviour
{
    public static bool Activa { get; private set; }

    private StructureViewer viewer;
    private StructureData datos;
    private readonly Dictionary<int, NodeData> nodos = new Dictionary<int, NodeData>();
    private readonly List<float> niveles = new List<float>();
    private readonly List<string> nombresNivel = new List<string>();
    private int nivel = -1;
    private float px, py;                 // posicion de la persona en ejes del modelo [m]
    private float P = 0.8f;               // kN (una persona de unos 80 kg)
    private const float Velocidad = 2.0f; // m/s con las teclas W A S D

    private SlabData pano;
    private float alfa;
    private readonly List<Receptora> receptoras = new List<Receptora>();
    private GameObject marcador;
    private readonly List<LineRenderer> lineas = new List<LineRenderer>();
    private Material matLinea;
    private GUIStyle etiqueta;
    private Vector2 scroll;
    private bool abiertoAntiguo;

    private class Receptora
    {
        public string borde;        // x0, x1, y0, y1
        public ElementData viga;    // null si el borde no tiene viga (muro o borde libre)
        public float carga;         // kN
        public Vector3 a, b;        // extremos de la viga en coordenadas de Unity
        public float posicion;      // distancia desde el nodo I de la viga [m]
    }

    private void Start()
    {
        viewer = GetComponent<StructureViewer>();
    }

    private void OnDestroy()
    {
        Limpiar();
        Activa = false;
    }

    // ------------------------------------------------------------------ datos
    private bool Preparar()
    {
        if (viewer == null) viewer = GetComponent<StructureViewer>();
        StructureData d = viewer != null ? viewer.Data : null;
        if (d == null || d.slabs == null || d.nodes == null || d.elements == null) return false;
        if (d == datos) return true;
        datos = d;
        nodos.Clear();
        foreach (NodeData n in d.nodes) nodos[n.id] = n;
        niveles.Clear();
        nombresNivel.Clear();
        foreach (SlabData s in d.slabs)
        {
            bool nuevo = true;
            foreach (float z in niveles) if (Mathf.Abs(z - s.z) < 0.05f) { nuevo = false; break; }
            if (!nuevo) continue;
            niveles.Add(s.z);
        }
        niveles.Sort();
        foreach (float z in niveles)
        {
            string nombre = $"z = {z:0.00} m";
            foreach (SlabData s in d.slabs) if (Mathf.Abs(s.z - z) < 0.05f && !string.IsNullOrEmpty(s.nivel)) { nombre = $"{s.nivel} (z = {z:0.00} m)"; break; }
            nombresNivel.Add(nombre);
        }
        if (nivel >= niveles.Count) nivel = -1;
        return niveles.Count > 0;
    }

    private void Activar(bool on)
    {
        if (on && !Preparar()) return;
        Activa = on;
        if (!on) { Limpiar(); return; }
        if (nivel < 0) nivel = Mathf.Min(1, niveles.Count - 1);
        IrAPano(0);
    }

    /// Lleva a la persona al centro del pano numero k (en orden) del nivel actual.
    private void IrAPano(int paso)
    {
        if (!Preparar() || nivel < 0) return;
        var panos = new List<SlabData>();
        foreach (SlabData s in datos.slabs) if (Mathf.Abs(s.z - niveles[nivel]) < 0.05f) panos.Add(s);
        if (panos.Count == 0) return;
        int actual = pano != null ? panos.IndexOf(pano) : -1;
        int k = actual < 0 ? 0 : ((actual + paso) % panos.Count + panos.Count) % panos.Count;
        SlabData s2 = panos[k];
        px = 0.5f * (s2.x0 + s2.x1);
        py = 0.5f * (s2.y0 + s2.y1);
        Recalcular();
    }

    private void CambiarNivel(int d)
    {
        if (niveles.Count == 0) return;
        nivel = Mathf.Clamp(nivel + d, 0, niveles.Count - 1);
        pano = null;
        IrAPano(0);
    }

    // ------------------------------------------------------------------ regla fisica
    private void Recalcular()
    {
        receptoras.Clear();
        pano = null;
        if (!Preparar() || nivel < 0) { Dibujar(); return; }
        float z = niveles[nivel];
        foreach (SlabData s in datos.slabs)
        {
            if (Mathf.Abs(s.z - z) > 0.05f) continue;
            float x0 = Mathf.Min(s.x0, s.x1), x1 = Mathf.Max(s.x0, s.x1), y0 = Mathf.Min(s.y0, s.y1), y1 = Mathf.Max(s.y0, s.y1);
            if (px >= x0 - 1e-3f && px <= x1 + 1e-3f && py >= y0 - 1e-3f && py <= y1 + 1e-3f) { pano = s; break; }
        }
        if (pano != null)
        {
            float X0 = Mathf.Min(pano.x0, pano.x1), X1 = Mathf.Max(pano.x0, pano.x1);
            float Y0 = Mathf.Min(pano.y0, pano.y1), Y1 = Mathf.Max(pano.y0, pano.y1);
            float lx = Mathf.Max(0.01f, X1 - X0), ly = Mathf.Max(0.01f, Y1 - Y0);
            alfa = Mathf.Pow(ly, 4f) / (Mathf.Pow(lx, 4f) + Mathf.Pow(ly, 4f));
            float enX = P * alfa, enY = P - enX;
            Agregar("x0", enX * (X1 - px) / lx, X0, true, py, z);
            Agregar("x1", enX * (px - X0) / lx, X1, true, py, z);
            Agregar("y0", enY * (Y1 - py) / ly, Y0, false, px, z);
            Agregar("y1", enY * (py - Y0) / ly, Y1, false, px, z);
        }
        Dibujar();
    }

    /// Busca la viga del borde (x = c o y = c) que contiene la proyeccion de la persona.
    private void Agregar(string borde, float carga, float c, bool bordeEnX, float proy, float z)
    {
        var r = new Receptora { borde = borde, carga = carga };
        ElementData mejor = null;
        float mejorDist = float.MaxValue;
        foreach (ElementData e in datos.elements)
        {
            if (e.type != "viga") continue;
            if (!nodos.TryGetValue(e.nodeI, out NodeData a) || !nodos.TryGetValue(e.nodeJ, out NodeData b)) continue;
            if (Mathf.Abs(a.z - z) > 0.05f || Mathf.Abs(b.z - z) > 0.05f) continue;
            float ca = bordeEnX ? a.x : a.y, cb = bordeEnX ? b.x : b.y;
            if (Mathf.Abs(ca - c) > 0.05f || Mathf.Abs(cb - c) > 0.05f) continue;
            float pa = bordeEnX ? a.y : a.x, pb = bordeEnX ? b.y : b.x;
            float lo = Mathf.Min(pa, pb), hi = Mathf.Max(pa, pb);
            float dist = proy < lo ? lo - proy : proy > hi ? proy - hi : 0f;
            if (dist < mejorDist) { mejorDist = dist; mejor = e; }
        }
        if (mejor != null && mejorDist < 0.5f)
        {
            NodeData a = nodos[mejor.nodeI], b = nodos[mejor.nodeJ];
            r.viga = mejor;
            r.a = new Vector3(a.x, a.z, a.y);
            r.b = new Vector3(b.x, b.z, b.y);
            Vector3 pto = new Vector3(bordeEnX ? c : proy, z, bordeEnX ? proy : c);
            r.posicion = Vector3.Distance(r.a, pto);
        }
        receptoras.Add(r);
    }

    // ------------------------------------------------------------------ movimiento
    private void Update()
    {
        if (!Activa) return;
        LeerTeclas(out float dx, out float dy);
        if (dx != 0f || dy != 0f)
        {
            px += dx * Velocidad * Time.deltaTime;
            py += dy * Velocidad * Time.deltaTime;
            Recalcular();
        }
    }

    private static float Eje(bool mas, bool menos) => (mas ? 1f : 0f) - (menos ? 1f : 0f);

    private static void LeerTeclas(out float dx, out float dy)
    {
#if ENABLE_INPUT_SYSTEM
        Keyboard k = Keyboard.current;
        dx = k != null ? Eje(k.dKey.isPressed, k.aKey.isPressed) : 0f;
        dy = k != null ? Eje(k.wKey.isPressed, k.sKey.isPressed) : 0f;
#else
        dx = Eje(Input.GetKey(KeyCode.D), Input.GetKey(KeyCode.A));
        dy = Eje(Input.GetKey(KeyCode.W), Input.GetKey(KeyCode.S));
#endif
    }

    // ------------------------------------------------------------------ visual
    private void Dibujar()
    {
        if (!Activa || nivel < 0) { Limpiar(); return; }
        if (marcador == null)
        {
            marcador = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            marcador.name = "SQ4_Persona";
            Collider col = marcador.GetComponent<Collider>();
            if (col != null) Destroy(col);
            marcador.transform.localScale = new Vector3(0.5f, 0.85f, 0.5f);
            var r = marcador.GetComponent<Renderer>();
            r.material = new Material(Shader.Find("Sprites/Default")) { color = new Color(0.576f, 0.886f, 0.776f) };
        }
        marcador.transform.position = new Vector3(px, niveles[nivel] + 0.9f, py);
        if (matLinea == null) matLinea = new Material(Shader.Find("Sprites/Default"));
        while (lineas.Count < 4)
        {
            var go = new GameObject("SQ4_VigaReceptora");
            var lr = go.AddComponent<LineRenderer>();
            lr.material = matLinea;
            lr.startWidth = lr.endWidth = 0.22f;
            lr.positionCount = 2;
            lr.useWorldSpace = true;
            lineas.Add(lr);
        }
        for (int i = 0; i < lineas.Count; i++)
        {
            Receptora rc = i < receptoras.Count ? receptoras[i] : null;
            bool ver = rc != null && rc.viga != null && rc.carga > 1e-4f;
            lineas[i].gameObject.SetActive(ver);
            if (!ver) continue;
            Color col = new Color(1f, 0.561f, 0.639f);
            lineas[i].startColor = lineas[i].endColor = col;
            lineas[i].SetPosition(0, rc.a + Vector3.up * 0.08f);
            lineas[i].SetPosition(1, rc.b + Vector3.up * 0.08f);
        }
    }

    private void Limpiar()
    {
        if (marcador != null) Destroy(marcador);
        marcador = null;
        foreach (LineRenderer lr in lineas) if (lr != null) Destroy(lr.gameObject);
        lineas.Clear();
    }

    // ------------------------------------------------------------------ interfaz
    private void OnGUI()
    {
        UiTheme.ApplyScale();
        if (Activa) DibujarEtiquetas();
        if (ViewerUI.Active)
        {
            if (ViewerUI.ActiveTab != ViewerUI.TabCargas || ViewerUI.SubCargas != ViewerUI.SubPersona) return;
            bool recorte = UiTheme.InicioRecorteHost();
            try
            {
                Rect h = ViewerUI.HostRect;
                Panel(new Rect(h.x + 6f, h.y + 4f, h.width - 12f, h.height - 8f));
            }
            finally { if (recorte) GUI.EndClip(); }
            return;
        }
        // interfaz antigua: recuadro movible abajo a la izquierda
        Rect def = new Rect(12f, UiTheme.ScreenH - (abiertoAntiguo ? 430f : 42f), 340f, abiertoAntiguo ? 420f : 32f);
        Rect r = UiTheme.MoverPanel("sq4", def, 300f, 32f);
        UiTheme.GUIBox(r);
        if (!abiertoAntiguo)
        {
            if (GUI.Button(new Rect(r.x + 8f, r.y + 5f, r.width - 16f, 22f), "PERSONA SOBRE LA LOSA (SQ4) ▸")) abiertoAntiguo = true;
            return;
        }
        if (GUI.Button(new Rect(r.xMax - 30f, r.y + 4f, 24f, 20f), "×")) abiertoAntiguo = false;
        Panel(new Rect(r.x + 8f, r.y + 26f, r.width - 16f, r.height - 32f));
    }

    private void Panel(Rect area)
    {
        GUILayout.BeginArea(area);
        scroll = GUILayout.BeginScrollView(scroll);
        GUILayout.Label("PERSONA SOBRE LA LOSA (SQ4)", UiTheme.Header);
        GUILayout.Label("Una persona camina por el piso: se identifica el paño que pisa, se resaltan las vigas que reciben su peso y se muestra cuánto recibe cada una. Instantáneo, sin reanálisis.", UiTheme.DimLabel);
        bool on = GUILayout.Toggle(Activa, Activa ? " Activa (moverse con W A S D o los botones)" : " Activar");
        if (on != Activa) Activar(on);
        if (!Activa) { GUILayout.EndScrollView(); GUILayout.EndArea(); return; }

        GUILayout.Space(4f);
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("◀", GUILayout.Width(30f))) CambiarNivel(-1);
        GUILayout.Label(nivel >= 0 && nivel < nombresNivel.Count ? "Piso: " + nombresNivel[nivel] : "Piso: —", UiTheme.Label);
        if (GUILayout.Button("▶", GUILayout.Width(30f))) CambiarNivel(1);
        GUILayout.EndHorizontal();

        GUILayout.BeginHorizontal();
        GUILayout.Label($"P = {P:0.00} kN (≈ {P / 0.00980665f:0} kg)", UiTheme.Label, GUILayout.Width(170f));
        float nuevoP = GUILayout.HorizontalSlider(P, 0.2f, 5f);
        GUILayout.EndHorizontal();
        if (Mathf.Abs(nuevoP - P) > 1e-4f) { P = nuevoP; Recalcular(); }

        GUILayout.Label($"Posición: x = {px:0.00} m · y = {py:0.00} m", UiTheme.Label);
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("◀ x")) { px -= 0.5f; Recalcular(); }
        if (GUILayout.Button("x ▶")) { px += 0.5f; Recalcular(); }
        if (GUILayout.Button("▼ y")) { py -= 0.5f; Recalcular(); }
        if (GUILayout.Button("y ▲")) { py += 0.5f; Recalcular(); }
        GUILayout.EndHorizontal();
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("Paño anterior")) IrAPano(-1);
        if (GUILayout.Button("Siguiente paño")) IrAPano(1);
        GUILayout.EndHorizontal();

        GUILayout.Space(6f);
        if (pano == null)
        {
            GUILayout.Label("La persona no está sobre un paño de losa de este piso: muévela hacia el edificio.", UiTheme.DimLabel);
        }
        else
        {
            float lx = Mathf.Abs(pano.x1 - pano.x0), ly = Mathf.Abs(pano.y1 - pano.y0);
            GUILayout.Label($"1. Paño pisado: {pano.id} · {lx:0.00} × {ly:0.00} m", UiTheme.TitleSm);
            GUILayout.Label($"Regla: Grashof en dos direcciones, α = Ly⁴/(Lx⁴+Ly⁴) = {alfa:0.000} va por la franja en x y {1f - alfa:0.000} por la franja en y; cada franja reparte a sus dos bordes con la regla de la palanca.", UiTheme.DimLabel);
            GUILayout.Label("2 y 3. Vigas receptoras y carga asignada:", UiTheme.TitleSm);
            float suma = 0f;
            foreach (Receptora rc in receptoras)
            {
                suma += rc.carga;
                string quien = rc.viga != null ? $"{rc.viga.elementTag} (a {rc.posicion:0.00} m del nodo I)" : "sin viga: muro o borde libre";
                GUILayout.Label($"Borde {rc.borde}: {rc.carga:0.000} kN → {quien}", UiTheme.Label);
            }
            bool conserva = Mathf.Abs(suma - P) < 1e-3f * Mathf.Max(1f, P);
            GUILayout.Label($"Conservación: suma = {suma:0.000} kN {(conserva ? "= P ✓" : "≠ P")}", conserva ? UiTheme.Label : UiTheme.DimLabel);
            GUILayout.Label("Las vigas receptoras se resaltan en rosa y cada una muestra su carga en la vista 3D.", UiTheme.DimLabel);
        }
        GUILayout.EndScrollView();
        GUILayout.EndArea();
    }

    private void DibujarEtiquetas()
    {
        Camera cam = Camera.main;
        if (cam == null || pano == null) return;
        if (etiqueta == null)
        {
            etiqueta = new GUIStyle(UiTheme.Label) { fontSize = 12, alignment = TextAnchor.MiddleCenter, wordWrap = false };
            etiqueta.normal.background = UiTheme.MakeTex(new Color(0.133f, 0.086f, 0.157f, 0.88f));
            etiqueta.padding = new RectOffset(5, 5, 2, 2);
        }
        foreach (Receptora rc in receptoras)
        {
            if (rc.viga == null || rc.carga <= 1e-4f) continue;
            Vector3 mitad = 0.5f * (rc.a + rc.b) + Vector3.up * 0.4f;
            Vector3 sp = cam.WorldToScreenPoint(mitad);
            if (sp.z <= 0f) continue;
            Vector2 g = new Vector2(sp.x, Screen.height - sp.y) / UiTheme.Scale;
            string txt = $"{rc.viga.elementTag}: {rc.carga:0.00} kN";
            Vector2 tam = etiqueta.CalcSize(new GUIContent(txt));
            GUI.Label(new Rect(g.x - tam.x / 2f, g.y - tam.y, tam.x + 4f, tam.y + 2f), txt, etiqueta);
        }
        if (marcador != null)
        {
            Vector3 sp = cam.WorldToScreenPoint(marcador.transform.position + Vector3.up * 1.1f);
            if (sp.z > 0f)
            {
                Vector2 g = new Vector2(sp.x, Screen.height - sp.y) / UiTheme.Scale;
                string txt = $"Persona · P = {P:0.00} kN";
                Vector2 tam = etiqueta.CalcSize(new GUIContent(txt));
                GUI.Label(new Rect(g.x - tam.x / 2f, g.y - tam.y, tam.x + 4f, tam.y + 2f), txt, etiqueta);
            }
        }
    }
}
