using UnityEngine;

public static class UiTheme
{
    // Layout coordinado: todas las zonas se derivan de estas constantes
    // para que NINGUN panel se superponga a otro.
    public const float TopBarH = 86f;
    public const float SideM = 12f;
    public const float CtrlW = 348f;
    public const float Gap = 16f;

    // Escala de la interfaz: 1 en PC; en celular la GUI se dibuja sobre una
    // pantalla virtual de ~720 px de alto (botones legibles en alta densidad).
    public static float Scale
    {
        get { return Application.isMobilePlatform ? Mathf.Max(1f, Screen.height / 720f) : 1f; }
    }

    public static float ScreenW { get { return Screen.width / Scale; } }
    public static float ScreenH { get { return Screen.height / Scale; } }

    /// Llamar al inicio de cada OnGUI.
    public static void ApplyScale()
    {
        float s = Scale;
        GUI.matrix = Matrix4x4.Scale(new Vector3(s, s, 1f));
    }

    /// true si la posicion de pantalla (origen abajo-izquierda, pixeles reales)
    /// cae sobre la barra superior, la columna de paneles o el panel de resultados.
    public static bool IsOverUI(Vector2 screenPos, bool infoPanelVisible)
    {
        if(HonorsCapacityComparisonPanel.Blocks(screenPos))return true;
        if (ViewerUI.Active) return ViewerUI.IsPointerOverUI(screenPos);
        float gx = screenPos.x / Scale;
        float gy = (Screen.height - screenPos.y) / Scale;
        if (gy < TopBarH + 8f) return true;
        if (gx < SideM + CtrlW + 4f) return true;
        if (infoPanelVisible && gx > InfoLeft - 4f) return true;
        return false;
    }

    // Paleta "Arrebol" (los valores viven en Paleta.cs)
    public static readonly Color PanelBg = Paleta.Panel;
    public static readonly Color Accent = Paleta.Acento;
    public static readonly Color AccentDim = Paleta.AcentoTenue;
    public static readonly Color Accent2 = Paleta.Acento2;
    public static readonly Color TextMain = Paleta.Texto;
    public static readonly Color TextDim = Paleta.TextoTenue;

    static GUIStyle _panelBox;
    static GUIStyle _titleSm;
    static GUIStyle _label;
    static GUIStyle _labelBold;
    static GUIStyle _header;
    static GUIStyle _dimLabel;
    static GUIStyle _brand;
    static Texture2D _panelTex;
    static Texture2D _stripTex;
    static Texture2D _whiteTex;
    static Font _mono;

    public static float LeftHeight
    {
        get
        {
            float avail = ScreenH - TopBarH - 8f;
            float maxLeft = 520f;
            float reservedPm = 372f;
            return Mathf.Clamp(avail - reservedPm, 250f, maxLeft);
        }
    }

    public static float InfoWidth
    {
        get { return Mathf.Clamp(ScreenW * 0.26f, 372f, 455f); }
    }

    public static float InfoLeft
    {
        get { return ScreenW - SideM - InfoWidth; }
    }

    public static Rect LeftArea()
    {
        // con ViewerUI, los paneles IMGUI (carga movil, carga en elemento, quitar
        // elemento) se dibujan dentro de la pestana activa: y = LeftArea().yMax + 14
        if (ViewerUI.Active) { Rect h = ViewerUI.HostRect; return new Rect(h.x, h.y - 14f, h.width, 0f); }
        return new Rect(SideM, TopBarH + 8f, CtrlW, LeftHeight);
    }

    public static Rect InfoPanel()
    {
        float w = InfoWidth;
        return new Rect(ScreenW - SideM - w, TopBarH + 8f, w, ScreenH - TopBarH - 8f);
    }

    public static Rect PMArea()
    {
        float x = SideM + CtrlW + Gap;
        float y = TopBarH + 8f + LeftHeight + 14f;
        float available = InfoLeft - Gap - x;
        float pw = Mathf.Min(430f, Mathf.Min(ScreenW * 0.4f, available));
        if (pw < 300f) pw = 300f;
        float ph = ScreenH - y - 12f;
        if (ph < 280f) ph = 280f;
        return new Rect(x, y, pw, ph);
    }

    public static Rect CenterTop(float w, float h)
    {
        float left = SideM + CtrlW + Gap;
        float right = InfoLeft - Gap;
        float span = right - left;
        if (span < w) w = Mathf.Max(210f, span);
        float x = left + (span - w) * 0.5f;
        return new Rect(x, TopBarH + 8f + 4f, w, h);
    }

    public static Texture2D White()
    {
        if (_whiteTex != null) return _whiteTex;
        _whiteTex = MakeTex(Color.white, 1, 1);
        return _whiteTex;
    }

    public static Texture2D MakeTex(Color color, int w = 1, int h = 1)
    {
        var tex = new Texture2D(w, h);
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                tex.SetPixel(x, y, color);
        tex.Apply();
        return tex;
    }

    // ------------------------------------------------------------------
    // Paneles IMGUI movibles (panel P-M): se arrastran desde la franja del titulo (24 px),
    // se redimensionan desde la esquina inferior derecha y con doble clic en el titulo
    // vuelven a su lugar.
    // ------------------------------------------------------------------
    static readonly System.Collections.Generic.Dictionary<string, Rect> _movidos = new System.Collections.Generic.Dictionary<string, Rect>();
    static string _arrastre;
    static bool _redimensiona;
    static Vector2 _ancla;

    /// Devuelve todos los paneles IMGUI movidos a su lugar original.
    public static void ReiniciarMovidos()
    {
        _movidos.Clear();
        _arrastre = null;
    }

    /// Borde inferior disponible para los paneles IMGUI: el de la pestana activa (ViewerUI) o la pantalla.
    public static float AreaBottom => ViewerUI.Active && ViewerUI.HostRect.height > 1f ? ViewerUI.HostRect.yMax : ScreenH;

    /// Recorta el dibujo IMGUI al area de la pestana activa sin cambiar las coordenadas, para que
    /// ningun panel quede encima de otro. Si devuelve true hay que cerrar con GUI.EndClip().
    public static bool InicioRecorteHost()
    {
        if (!ViewerUI.Active) return false;
        Rect h = ViewerUI.HostRect;
        if (h.width <= 1f || h.height <= 1f || h.x < -1000f) return false;
        ApplyScale();
        GUI.BeginClip(h, -h.position, Vector2.zero, false);
        return true;
    }

    public static Rect MoverPanel(string clave, Rect porDefecto, float minW = 280f, float minH = 220f)
    {
        Rect r = _movidos.TryGetValue(clave, out Rect guardado) ? guardado : porDefecto;
        Event e = Event.current;
        if (e == null) return r;
        Rect titulo = new Rect(r.x, r.y, r.width, 24f);
        Rect esquina = new Rect(r.xMax - 18f, r.yMax - 18f, 18f, 18f);
        if (e.type == EventType.MouseDown && e.button == 0)
        {
            if (titulo.Contains(e.mousePosition) && e.clickCount == 2)
            {
                _movidos.Remove(clave);
                e.Use();
                return porDefecto;
            }
            if (esquina.Contains(e.mousePosition))
            {
                _arrastre = clave;
                _redimensiona = true;
                _ancla = new Vector2(r.xMax - e.mousePosition.x, r.yMax - e.mousePosition.y);
                e.Use();
            }
            else if (titulo.Contains(e.mousePosition))
            {
                _arrastre = clave;
                _redimensiona = false;
                _ancla = e.mousePosition - r.position;
                e.Use();
            }
        }
        else if (e.type == EventType.MouseDrag && _arrastre == clave)
        {
            if (_redimensiona)
            {
                r.width = Mathf.Max(minW, e.mousePosition.x + _ancla.x - r.x);
                r.height = Mathf.Max(minH, e.mousePosition.y + _ancla.y - r.y);
            }
            else
            {
                r.position = e.mousePosition - _ancla;
            }
            r.x = Mathf.Clamp(r.x, 60f - r.width, ScreenW - 60f);
            r.y = Mathf.Clamp(r.y, 0f, ScreenH - 30f);
            _movidos[clave] = r;
            e.Use();
        }
        else if (e.type == EventType.MouseUp && _arrastre == clave)
        {
            _arrastre = null;
            e.Use();
        }
        return r;
    }

    /// Marca de la esquina para redimensionar un panel IMGUI.
    public static void DibujarEsquina(Rect r)
    {
        if (Event.current == null || Event.current.type != EventType.Repaint) return;
        GUI.DrawTexture(new Rect(r.xMax - 14f, r.yMax - 4f, 12f, 2f), Strip);
        GUI.DrawTexture(new Rect(r.xMax - 4f, r.yMax - 14f, 2f, 12f), Strip);
        GUI.DrawTexture(new Rect(r.xMax - 9f, r.yMax - 7f, 6f, 2f), Strip);
        GUI.DrawTexture(new Rect(r.xMax - 7f, r.yMax - 9f, 2f, 6f), Strip);
    }

    public static void GUIBox(Rect rect, string title = null)
    {
        GUI.Box(rect, GUIContent.none, PanelBox);
        GUI.DrawTexture(new Rect(rect.x, rect.y, rect.width, 3f), Strip);
        GUI.DrawTexture(new Rect(rect.x, rect.y, 3f, rect.height), Strip);
        if (!string.IsNullOrEmpty(title))
        {
            GUI.Label(new Rect(rect.x + 10f, rect.y + 7f, rect.width - 20f, 18f), title, TitleSm);
        }
    }

    static GUIStyle PanelBox
    {
        get
        {
            if (_panelBox == null)
            {
                _panelBox = new GUIStyle(GUI.skin.box);
                _panelBox.normal.background = PanelTex;
                _panelBox.border = new RectOffset(2, 2, 2, 2);
                _panelBox.padding = new RectOffset(8, 8, 8, 8);
            }
            return _panelBox;
        }
    }

    public static GUIStyle Label
    {
        get
        {
            if (_label == null)
            {
                _label = new GUIStyle(GUI.skin.label);
                _label.font = Monospace;
                _label.fontSize = 12;
                _label.normal.textColor = TextMain;
                _label.wordWrap = true;
                _label.richText = false;
                _label.alignment = TextAnchor.UpperLeft;
                _label.padding = new RectOffset(0, 0, 0, 0);
            }
            return _label;
        }
    }

    public static GUIStyle LabelBold
    {
        get
        {
            if (_labelBold == null)
            {
                _labelBold = new GUIStyle(Label);
                _labelBold.fontStyle = FontStyle.Bold;
                _labelBold.normal.textColor = TextMain;
            }
            return _labelBold;
        }
    }

    public static GUIStyle TitleSm
    {
        get
        {
            if (_titleSm == null)
            {
                _titleSm = new GUIStyle(Label);
                _titleSm.fontSize = 13;
                _titleSm.fontStyle = FontStyle.Bold;
                _titleSm.normal.textColor = Accent;
            }
            return _titleSm;
        }
    }

    public static GUIStyle Header
    {
        get
        {
            if (_header == null)
            {
                _header = new GUIStyle(Label);
                _header.fontSize = 11;
                _header.fontStyle = FontStyle.Bold;
                _header.normal.textColor = Accent2;
            }
            return _header;
        }
    }

    public static GUIStyle DimLabel
    {
        get
        {
            if (_dimLabel == null)
            {
                _dimLabel = new GUIStyle(Label);
                _dimLabel.normal.textColor = TextDim;
            }
            return _dimLabel;
        }
    }

    public static GUIStyle Brand
    {
        get
        {
            if (_brand == null)
            {
                _brand = new GUIStyle(Label);
                _brand.fontSize = 13;
                _brand.fontStyle = FontStyle.Bold;
                _brand.normal.textColor = Accent;
            }
            return _brand;
        }
    }

    static Texture2D PanelTex
    {
        get
        {
            if (_panelTex == null) _panelTex = MakeTex(PanelBg);
            return _panelTex;
        }
    }

    static Texture2D Strip
    {
        get
        {
            if (_stripTex == null) _stripTex = MakeTex(AccentDim);
            return _stripTex;
        }
    }

    static bool _monoResolved;

    /// Fuente monoespaciada del sistema SOLO si esta instalada. En Android no
    /// existe Consolas: CreateDynamicFontFromOSFont igual devuelve una fuente
    /// vacia (texto invisible y un aviso por cuadro), asi que ahi se usa la
    /// fuente por defecto de Unity (null).
    static Font Monospace
    {
        get
        {
            if (!_monoResolved)
            {
                _monoResolved = true;
                _mono = null;
                if (!Application.isMobilePlatform)
                {
                    var installed = new System.Collections.Generic.HashSet<string>(Font.GetOSInstalledFontNames());
                    foreach (string name in new[] { "Consolas", "Courier New", "Liberation Mono", "DejaVu Sans Mono" })
                    {
                        if (installed.Contains(name))
                        {
                            _mono = Font.CreateDynamicFontFromOSFont(name, 12);
                            break;
                        }
                    }
                }
            }
            return _mono;
        }
    }
}
