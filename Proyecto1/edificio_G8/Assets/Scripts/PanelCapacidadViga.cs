using UnityEngine;

/// <summary>
/// Capacidad de la viga seleccionada. Dibuja los diagramas M(x) y V(x) del caso o combinacion
/// activa (incluida la superposicion en vivo y las cargas agregadas en CARGAS) y los compara
/// con phiMn positivo y negativo y con phiVn de ACI 318 (calculados por capacidad_ha.py con la
/// armadura de la viga). Indica si CUMPLE y con que factor de uso. Las columnas y los muros
/// usan el panel P-M. Se mueve desde su titulo y se agranda desde la esquina inferior derecha.
/// </summary>
public class PanelCapacidadViga : MonoBehaviour
{
    public static Rect AreaVisible { get; private set; }

    private const int N = 41;
    private readonly float[] mx = new float[N];
    private readonly float[] vx = new float[N];
    private ElementPicker picker;
    private StructureViewer viewer;
    private ElementData ultimo;
    private bool oculto;
    private GUIStyle estado;

    private void OnDisable()
    {
        AreaVisible = Rect.zero;
    }

    private void OnGUI()
    {
        AreaVisible = Rect.zero;
        if (picker == null) picker = FindAnyObjectByType<ElementPicker>();
        if (viewer == null) viewer = FindAnyObjectByType<StructureViewer>();
        ElementData e = picker != null && picker.Selected != null ? picker.Selected.data : null;
        if (e != ultimo) { ultimo = e; oculto = false; }
        if (e == null || e.type != "viga" || e.capacidad == null || e.capacidad.phiMn_pos_kN_m <= 0f || oculto) return;
        UiTheme.ApplyScale();

        string combo = UnityData.ActiveCombo;
        float mMax = 0f, mMin = 0f, vAbs = 0f;
        for (int i = 0; i < N; i++)
        {
            float[] r = UnityData.InternalForcesAt(e, i / (float)(N - 1), combo);
            if (r == null || r.Length < 6) r = new float[6];
            mx[i] = -r[4];   // + = traccion abajo (My local < 0), como en los diagramas
            vx[i] = r[2];
            mMax = Mathf.Max(mMax, mx[i]);
            mMin = Mathf.Min(mMin, mx[i]);
            vAbs = Mathf.Max(vAbs, Mathf.Abs(vx[i]));
        }
        CapacityData cap = e.capacidad;
        float mnPos = cap.phiMn_pos_kN_m;
        float mnNeg = cap.phiMn_neg_kN_m > 0f ? cap.phiMn_neg_kN_m : cap.phiMn_pos_kN_m;
        float vn = cap.phiVn_apoyo_kN > 0f ? cap.phiVn_apoyo_kN : cap.phiVn_tramo_kN;
        float usoM = Mathf.Max(mMax / mnPos, -mMin / mnNeg);
        float usoV = vn > 0f ? vAbs / vn : 0f;
        float uso = Mathf.Max(usoM, usoV);
        bool cumple = uso <= 1f;

        float w = Mathf.Min(560f, UiTheme.ScreenW - 24f);
        Rect def = new Rect((UiTheme.ScreenW - w) / 2f, UiTheme.ScreenH - 322f, w, 304f);
        Rect r0 = UiTheme.MoverPanel("viga_capacidad", def, 380f, 240f);
        AreaVisible = r0;
        UiTheme.GUIBox(r0);
        UiTheme.DibujarEsquina(r0);
        GUI.Label(new Rect(r0.x + 10f, r0.y + 4f, r0.width - 50f, 20f),
            $"CAPACIDAD DE LA VIGA {e.elementTag} · {UnityData.GetComboLabel(combo)}", UiTheme.TitleSm);
        if (GUI.Button(new Rect(r0.xMax - 30f, r0.y + 4f, 24f, 20f), "×")) oculto = true;

        if (estado == null) estado = new GUIStyle(UiTheme.Label) { fontStyle = FontStyle.Bold };
        estado.normal.textColor = cumple ? new Color(0.576f, 0.886f, 0.776f) : new Color(1f, 0.42f, 0.48f);
        GUI.Label(new Rect(r0.x + 10f, r0.y + 24f, r0.width - 20f, 20f),
            (cumple ? "CUMPLE" : "NO CUMPLE") + $" · factor de uso {uso:0.00} (flexión {usoM:0.00}, corte {usoV:0.00}) · φMn+ {mnPos:0} · φMn− {mnNeg:0} kN·m · φVn {vn:0} kN", estado);

        float alto = (r0.height - 72f) / 2f;
        float L = Largo(e);
        Grafico(new Rect(r0.x + 10f, r0.y + 50f, r0.width - 20f, alto - 6f), mx, mnPos, -mnNeg, "M [kN·m] (+ = tracción abajo)", L, usoM);
        Grafico(new Rect(r0.x + 10f, r0.y + 50f + alto, r0.width - 20f, alto - 6f), vx, vn, -vn, "V [kN]", L, usoV);
    }

    private float Largo(ElementData e)
    {
        if (viewer == null || viewer.Data == null || viewer.Data.nodes == null) return 0f;
        Vector3 a = Vector3.zero, b = Vector3.zero;
        foreach (NodeData n in viewer.Data.nodes)
        {
            if (n.id == e.nodeI) a = new Vector3(n.x, n.y, n.z);
            if (n.id == e.nodeJ) b = new Vector3(n.x, n.y, n.z);
        }
        return Vector3.Distance(a, b);
    }

    private static void Grafico(Rect r, float[] val, float lim, float limNeg, string titulo, float L, float uso)
    {
        GUI.color = new Color(0f, 0f, 0f, 0.25f);
        GUI.DrawTexture(r, Texture2D.whiteTexture);
        GUI.color = Color.white;
        float maxAbs = Mathf.Max(Mathf.Abs(lim), Mathf.Abs(limNeg));
        foreach (float q in val) maxAbs = Mathf.Max(maxAbs, Mathf.Abs(q));
        maxAbs = Mathf.Max(maxAbs * 1.1f, 1e-3f);
        float mitad = r.y + r.height / 2f, escala = (r.height / 2f - 4f) / maxAbs;

        Linea(new Vector2(r.x, mitad), new Vector2(r.xMax, mitad), 1f, new Color(1f, 1f, 1f, 0.35f));
        Color capacidad = new Color(0.576f, 0.886f, 0.776f, 0.95f);
        Linea(new Vector2(r.x, mitad - lim * escala), new Vector2(r.xMax, mitad - lim * escala), 2f, capacidad);
        Linea(new Vector2(r.x, mitad - limNeg * escala), new Vector2(r.xMax, mitad - limNeg * escala), 2f, capacidad);
        Color demanda = new Color(1f, 0.561f, 0.639f);
        for (int i = 0; i < val.Length - 1; i++)
        {
            float xa = r.x + r.width * i / (val.Length - 1f), xb = r.x + r.width * (i + 1) / (val.Length - 1f);
            Linea(new Vector2(xa, mitad - val[i] * escala), new Vector2(xb, mitad - val[i + 1] * escala), 2f, demanda);
        }
        GUI.Label(new Rect(r.x + 4f, r.y + 2f, r.width - 8f, 18f), $"{titulo} · uso {uso:0.00} · rosa = demanda, verde = capacidad φ", UiTheme.DimLabel);
        GUI.Label(new Rect(r.x + 4f, r.yMax - 16f, 60f, 16f), "nodo I", UiTheme.DimLabel);
        GUI.Label(new Rect(r.xMax - 120f, r.yMax - 16f, 116f, 16f), $"nodo J · L = {L:0.00} m", UiTheme.DimLabel);
    }

    private static void Linea(Vector2 a, Vector2 b, float grosor, Color c)
    {
        if (Event.current == null || Event.current.type != EventType.Repaint) return;
        Matrix4x4 m0 = GUI.matrix;
        Color c0 = GUI.color;
        GUI.color = c;
        float ang = Mathf.Atan2(b.y - a.y, b.x - a.x) * Mathf.Rad2Deg;
        GUIUtility.RotateAroundPivot(ang, a);
        GUI.DrawTexture(new Rect(a.x, a.y - grosor / 2f, (b - a).magnitude, grosor), Texture2D.whiteTexture);
        GUI.matrix = m0;
        GUI.color = c0;
    }
}
