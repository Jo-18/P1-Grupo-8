using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

/// <summary>
/// Interfaz del viewer en UI Toolkit (reemplaza la barra superior, la consola
/// de capas y el panel de resultados IMGUI):
///   - barra superior: caso/combinacion, resultado, camara, busqueda y estado;
///   - dock izquierdo con pestanas VISTA · RESULTADOS · CARGAS · MODIFICAR · ANALISIS;
///   - panel de propiedades del elemento seleccionado (derecha).
/// Los paneles que siguen en IMGUI (carga movil, carga en elemento, quitar
/// elemento) se dibujan dentro de su pestana, en <see cref="HostRect"/>.
/// La agrega StructureViewer en Play.
/// </summary>
public class ViewerUI : MonoBehaviour
{
    public const string TabVista = "VISTA";
    public const string TabResultados = "RESULTADOS";
    public const string TabCargas = "CARGAS";
    public const string TabModificar = "MODIFICAR";
    public const string TabAnalisis = "ANALISIS";
    private static readonly string[] Tabs = { TabVista, TabResultados, TabCargas, TabModificar, TabAnalisis };

    public static bool Active { get; private set; }
    public static string ActiveTab { get; private set; } = TabVista;
    /// Zona (coordenadas GUI) donde la pestana activa aloja paneles IMGUI.
    public static Rect HostRect { get; private set; }

    // Sub-paneles de CARGAS y MODIFICAR: se ve uno a la vez, asi ningun panel queda encima de otro.
    public const string SubMovil = "Carga móvil";
    public const string SubElemento = "Carga en elemento";
    public const string SubSeccion = "Sección";
    public const string SubArmadura = "Armadura";
    public const string SubQuitar = "Quitar";
    public const string SubApoyo = "Apoyo";
    public const string SubArea = "Área trib.";
    public const string SubPersona = "Persona (SQ4)";
    public static string SubCargas { get; private set; } = SubMovil;

    /// Primer problema al crear la interfaz (se muestra en pantalla para poder reportarlo).
    public static string Falla { get; private set; }
    private static void RegistrarFalla(string motivo)
    {
        if (string.IsNullOrEmpty(Falla)) Falla = motivo;
        Debug.LogError("[ViewerUI] " + motivo);
    }

    /// Garantia: si la construccion de la escena fallo antes de agregar esta interfaz, se agrega
    /// en cuanto el visor tiene datos (VigilanteInterfaz).
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    private static void AsegurarInterfaz()
    {
        foreach (StructureViewer v in UnityEngine.Object.FindObjectsByType<StructureViewer>(FindObjectsSortMode.None))
            if (v.GetComponent<VigilanteInterfaz>() == null) v.gameObject.AddComponent<VigilanteInterfaz>();
    }
    public static string SubModificar { get; private set; } = SubSeccion;
    private readonly Dictionary<string, Dictionary<string, Button>> subBotones = new Dictionary<string, Dictionary<string, Button>>();
    private readonly Dictionary<string, Dictionary<string, VisualElement>> subPaginas = new Dictionary<string, Dictionary<string, VisualElement>>();
    public static bool TextFocused { get; private set; }

    private static ViewerUI instance;
    /// Parametros editables y reanalisis (persisten aunque se reconstruya la interfaz).
    public static readonly AnalysisSession Session = new AnalysisSession();
    private UIDocument document;
    private VisualElement root;
    private StructureViewer viewer;
    private DiagramController diagrams;
    private ElementPicker picker;

    private readonly Dictionary<string, Button> tabButtons = new Dictionary<string, Button>();
    private readonly Dictionary<string, VisualElement> tabPages = new Dictionary<string, VisualElement>();
    private readonly Dictionary<string, VisualElement> hosts = new Dictionary<string, VisualElement>();
    private VisualElement tabBody;
    private VisualElement dockPanel;
    private readonly Dictionary<string, Button> caseButtons = new Dictionary<string, Button>();
    private readonly Dictionary<string, Button> resultButtons = new Dictionary<string, Button>();
    private readonly List<System.Action> syncers = new List<System.Action>();
    private Label statusLabel;
    private VisualElement propsPanel;
    private Label propsTitle;
    private VisualElement propsBody;
    private string propsText;
    private float nextSync;

    private static readonly (string name, string label)[] ResultModes =
    {
        ("None", "Sin diagrama"), ("Axial", "Axial N"), ("Corte", "Corte V"), ("Momento", "Momento M"), ("Deformada", "Deformada"),
    };

    // ------------------------------------------------------------------
    private void Start()
    {
        viewer = GetComponent<StructureViewer>();
        diagrams = viewer.Diagrams;
        picker = FindAnyObjectByType<ElementPicker>();
        try { Session.LoadFrom(viewer.Data); }   // antes de construir: la pestana ANALISIS muestra estos valores
        catch (System.Exception e) { Debug.LogError("[ViewerUI] No se pudieron leer los parametros del modelo: " + e.Message); Debug.LogException(e); }
        bool ok;
        try { ok = Build(); }
        catch (System.Exception e)
        {
            RegistrarFalla("error al crear la interfaz: " + e.Message);
            Debug.LogException(e);
            ok = root != null;   // se usa lo que alcanzo a construirse
        }
        if (!ok)
        {
            RegistrarFalla("no se pudo crear la interfaz nueva (faltan los estilos de Assets/Resources/UI); se usa la interfaz antigua.");
            return;
        }
        instance = this;
        Active = true;
        viewer.ModelReloaded += Rebuild;
        Paso("seleccion de pestana", () => { SelectTab(ActiveTab); SyncAll(); });
    }

    /// Ejecuta una parte de la construccion; si falla, la registra en la Consola y sigue con el resto.
    private void Paso(string nombre, System.Action accion)
    {
        try { accion(); }
        catch (System.Exception e)
        {
            RegistrarFalla($"error en '{nombre}': {e.Message}");
            Debug.LogException(e);
        }
    }

    private void ConstruirPaneles()
    {
        Paso("barra superior", BuildTopBar);
        Paso("panel izquierdo", BuildDock);
        Paso("panel de propiedades", BuildProps);
        Paso("paneles movibles", () =>
        {
            if (dockPanel != null) PanelMovible.Hacer(dockPanel, "mcoc_panel_dock");
            if (propsPanel != null) PanelMovible.Hacer(propsPanel, "mcoc_panel_props");
        });
    }

    /// Pagina de una pestana; si falla al construirse, muestra el error en vez de botar toda la interfaz.
    private VisualElement PaginaSegura(string nombre, System.Func<VisualElement> crear)
    {
        try { return crear(); }
        catch (System.Exception e)
        {
            RegistrarFalla($"error al construir la pestaña {nombre}: {e.Message}");
            Debug.LogException(e);
            var p = new VisualElement();
            p.AddToClassList("tab-content");
            p.Add(Text($"No se pudo construir esta pestaña ({e.Message}). Revisa la Consola de Unity.", "hint"));
            return p;
        }
    }

    /// Tras recargar el modelo (reanalisis): se rehace la interfaz con los datos nuevos.
    private void Rebuild()
    {
        diagrams = viewer.Diagrams;
        root.Clear();
        tabButtons.Clear(); tabPages.Clear(); hosts.Clear(); caseButtons.Clear(); resultButtons.Clear(); syncers.Clear();
        subBotones.Clear(); subPaginas.Clear();
        propsText = null;
        ConstruirPaneles();
        Paso("seleccion de pestana", () => { SelectTab(ActiveTab); SyncAll(); });
        PrepararResumen();   // se recargo el modelo (reanalisis, quitar elemento o restaurar): se muestran sus resultados
        resumenVisible = resumen.Count > 0;
    }

    // ---- resumen de resultados despues de un reanalisis ----
    private bool resumenVisible;
    private readonly List<string> resumen = new List<string>();
    public static Rect AreaResumen { get; private set; }

    private void PrepararResumen()
    {
        resumen.Clear();
        StructureData d = viewer != null ? viewer.Data : null;
        if (d == null || d.elements == null) return;
        float vMax = 0f, cMax = 0f;
        int vMal = 0, cMal = 0;
        string vPeor = "-", cPeor = "-";
        foreach (ElementData e in d.elements)
        {
            if (e == null || e.capacidad == null || e.capacidad.DCR <= 0f) continue;
            if (e.type == "viga")
            {
                if (e.capacidad.DCR > vMax) { vMax = e.capacidad.DCR; vPeor = e.elementTag; }
                if (e.capacidad.DCR > 1f) vMal++;
            }
            else if (e.type == "columna")
            {
                if (e.capacidad.DCR > cMax) { cMax = e.capacidad.DCR; cPeor = e.elementTag; }
                if (e.capacidad.DCR > 1f) cMal++;
            }
        }
        resumen.Add($"Vigas: factor de uso máx {vMax:0.00} ({vPeor}) · {(vMal == 0 ? "todas cumplen" : vMal + " no cumplen")}");
        resumen.Add($"Columnas: factor de uso máx {cMax:0.00} ({cPeor}) · {(cMal == 0 ? "todas cumplen" : cMal + " no cumplen")}");
        if (d.resumenAnalisis != null && d.resumenAnalisis.uMax != null)
            foreach (CaseMax u in d.resumenAnalisis.uMax)
                if (u != null && (u.caso == "G" || u.caso == "EX" || u.caso == "EY")) resumen.Add($"Desplazamiento máximo {u.caso}: {u.u_mm:0.0} mm");
        resumen.Add("Selecciona una columna o muro para ver su P-M, o una viga para ver M y V contra su capacidad.");
    }

    private void DibujarResumen()
    {
        float h = 66f + 20f * resumen.Count;
        Rect def = new Rect(UiTheme.ScreenW - 482f, UiTheme.ScreenH - h - 72f, 470f, h);
        Rect r = UiTheme.MoverPanel("resumen_reanalisis", def, 380f, h);
        AreaResumen = r;
        UiTheme.GUIBox(r);
        GUI.Label(new Rect(r.x + 10f, r.y + 4f, r.width - 50f, 20f), "RESULTADOS DEL MODELO RECALCULADO", UiTheme.TitleSm);
        if (GUI.Button(new Rect(r.xMax - 30f, r.y + 4f, 24f, 20f), "×")) { resumenVisible = false; return; }
        float y = r.y + 28f;
        foreach (string l in resumen)
        {
            GUI.Label(new Rect(r.x + 10f, y, r.width - 20f, 20f), l, UiTheme.Label);
            y += 20f;
        }
        float bw = (r.width - 40f) / 3f;
        if (GUI.Button(new Rect(r.x + 10f, y + 4f, bw, 24f), "Deformada animada")) { viewer.SetResult("Deformada"); DiagramController.AnimateDeformed = true; }
        if (GUI.Button(new Rect(r.x + 20f + bw, y + 4f, bw, 24f), "Momentos")) viewer.SetResult("Momento");
        if (GUI.Button(new Rect(r.x + 30f + 2f * bw, y + 4f, bw, 24f), "Utilización")) viewer.SetUtilizationVisible(true);
    }

    private void OnDestroy()
    {
        if (instance == this) { Active = false; instance = null; HostRect = Rect.zero; }
        if (viewer != null) viewer.ModelReloaded -= Rebuild;
        if (document != null) Destroy(document.gameObject);
    }

    private bool Build()
    {
        var theme = Resources.Load<ThemeStyleSheet>("UI/ViewerTheme");
        var sheet = Resources.Load<StyleSheet>("UI/viewer");
        if (theme == null)
        {
            // respaldo: el tema por defecto de UI Toolkit, si Unity ya lo tiene cargado
            foreach (ThemeStyleSheet t in Resources.FindObjectsOfTypeAll<ThemeStyleSheet>()) { theme = t; break; }
            RegistrarFalla("no se encontró Assets/Resources/UI/ViewerTheme.tss" + (theme != null ? " (se usa el tema por defecto)" : ""));
        }
        if (sheet == null) RegistrarFalla("no se encontró Assets/Resources/UI/viewer.uss (la interfaz se ve sin estilos)");
        if (theme == null && sheet == null) return false;

        var settings = ScriptableObject.CreateInstance<PanelSettings>();
        settings.name = "ViewerPanelSettings";
        settings.themeStyleSheet = theme;
        if (Application.isMobilePlatform)
        {
            // mismas unidades que la GUI IMGUI del celular (pantalla virtual de 720 de alto)
            settings.scaleMode = PanelScaleMode.ScaleWithScreenSize;
            settings.referenceResolution = new Vector2Int(1280, 720);
            settings.screenMatchMode = PanelScreenMatchMode.MatchWidthOrHeight;
            settings.match = 1f;
        }
        else
        {
            settings.scaleMode = PanelScaleMode.ConstantPixelSize;
            settings.scale = 1f;
        }

        var go = new GameObject("ViewerUI (UI Toolkit)");
        document = go.AddComponent<UIDocument>();
        document.panelSettings = settings;
        root = document.rootVisualElement;
        if (sheet != null) root.styleSheets.Add(sheet);
        root.AddToClassList("root");
        root.pickingMode = PickingMode.Ignore;

        ConstruirPaneles();
        return true;
    }

    // ------------------------------------------------------------------
    // Barra superior
    // ------------------------------------------------------------------
    private void BuildTopBar()
    {
        var bar = Panel("topbar");
        root.Add(bar);

        var row1 = Row();
        row1.Add(Text("GRUPO 8 · P1_G8", "brand"));
        row1.Add(Text("Modelo OpenSees · edificios 1 y 2 · G35 / A36", "brand-sub"));
        row1.Add(Spacer());
        var search = Input(new TextField { value = "" });
        search.AddToClassList("search");
        search.tooltip = "Id o elementTag (ej. E1_72)";
        search.RegisterCallback<FocusInEvent>(_ => TextFocused = true);
        search.RegisterCallback<FocusOutEvent>(_ => TextFocused = false);
        search.RegisterCallback<KeyDownEvent>(e =>
        {
            if (e.keyCode == KeyCode.Return || e.keyCode == KeyCode.KeypadEnter) viewer.Search(search.value);
        });
        row1.Add(search);
        row1.Add(Btn("Buscar", () => viewer.Search(search.value), "small"));
        row1.Add(Gap());
        // orbita libre con el mouse (sin botones de vista fija); la deformada se puede animar desde aqui
        row1.Add(Check("Animar deformada", () => DiagramController.AnimateDeformed, v => DiagramController.AnimateDeformed = v));
        bar.Add(row1);

        var row2 = Row();
        row2.Add(Text("Caso", "group-label", "first"));
        var cases = Seg();
        var names = new List<string> { "G", "Q", "EX", "EY" };
        foreach (string c in viewer.ComboNames) if (!names.Contains(c) && c != "G (sin combo)") names.Add(c);
        foreach (string c in names)
        {
            string name = c;
            Button b = Btn(name, () => viewer.SetCase(name), "small");
            b.tooltip = UnityData.GetComboLabel(name);
            caseButtons[name] = b;
            cases.Add(b);
        }
        FinishSeg(cases);
        row2.Add(cases);
        row2.Add(Text("Resultado", "group-label"));
        var results = Seg();
        foreach (var (name, label) in ResultModes)
        {
            string n = name;
            Button b = Btn(label, () => viewer.SetResult(n), "small");
            resultButtons[name] = b;
            results.Add(b);
        }
        FinishSeg(results);
        row2.Add(results);
        bar.Add(row2);

        statusLabel = Text("", "status");
        bar.Add(statusLabel);

        syncers.Add(() =>
        {
            string active = UnityData.ActiveCombo;
            foreach (var kv in caseButtons) kv.Value.EnableInClassList("on", kv.Key == active);
            string mode = diagrams != null ? diagrams.CurrentResultName() : "None";
            foreach (var kv in resultButtons) kv.Value.EnableInClassList("on", kv.Key == mode);
            string hint = Application.isMobilePlatform
                ? "Toque: seleccionar · 1 dedo: orbitar · pellizco: zoom · 2 dedos: desplazar"
                : "Clic: seleccionar · clic der.: orbitar · rueda: zoom · 1-4: diagramas · +/−: escala";
            string sup = active == UnityData.SuperpositionComboName ? "  ·  SUP = " + UnityData.GetComboLabel(active) : "";
            statusLabel.text = (viewer.Status ?? "") + sup + "     |     " + hint;
        });
    }

    // ------------------------------------------------------------------
    // Dock con pestanas
    // ------------------------------------------------------------------
    private void BuildDock()
    {
        var dock = Panel("dock");
        dockPanel = dock;
        dock.style.flexDirection = FlexDirection.Column;
        dock.pickingMode = PickingMode.Ignore;
        root.Add(dock);

        var tabs = new VisualElement();
        tabs.AddToClassList("tabs");
        foreach (string t in Tabs)
        {
            string tab = t;
            var b = new Button(() => SelectTab(tab)) { text = tab == TabAnalisis ? "ANÁLISIS" : tab };
            b.AddToClassList("tab");
            tabButtons[tab] = b;
            tabs.Add(b);
        }
        dock.Add(tabs);

        tabBody = new VisualElement();
        tabBody.AddToClassList("tab-body");
        dock.Add(tabBody);

        tabPages[TabVista] = PaginaSegura("VISTA", () => Page(BuildVista));
        tabPages[TabResultados] = PaginaSegura("RESULTADOS", () => Page(BuildResultados));
        tabPages[TabCargas] = PaginaSegura("CARGAS", () => HostPage(TabCargas,
            "Carga móvil sobre un recorrido de vigas, o carga puntual o repartida en un elemento. " +
            "Se resuelven con superposición de casos unitarios de OpenSees."));
        tabPages[TabModificar] = PaginaSegura("MODIFICAR", () => HostPage(TabModificar,
            "Cambia secciones o armadura, o quita elementos, y recalcula con OpenSees. El modelo original no se modifica."));
        tabPages[TabAnalisis] = PaginaSegura("ANÁLISIS", () => Page(BuildAnalisis));
        foreach (var page in tabPages.Values) tabBody.Add(page);
    }

    public static void ShowTab(string tab)
    {
        if (instance != null) instance.SelectTab(tab);
    }

    /// Abre una pestana y uno de sus sub-paneles (CARGAS o MODIFICAR).
    public static void ShowSub(string tab, string sub)
    {
        if (instance == null) return;
        instance.SelectTab(tab);
        instance.SelectSub(tab, sub);
    }

    private void SelectTab(string tab)
    {
        ActiveTab = tab;
        foreach (var kv in tabButtons) kv.Value.EnableInClassList("on", kv.Key == tab);
        foreach (var kv in tabPages) kv.Value.style.display = kv.Key == tab ? DisplayStyle.Flex : DisplayStyle.None;
        // las pestanas con paneles IMGUI dejan transparente el cuerpo para que se vean encima
        tabBody.EnableInClassList("host-mode", hosts.ContainsKey(tab) && HostVisible(tab));
    }

    private VisualElement Page(System.Action<VisualElement> fill)
    {
        var scroll = new ScrollView(ScrollViewMode.Vertical);
        scroll.AddToClassList("tab-scroll");
        var content = new VisualElement();
        content.AddToClassList("tab-content");
        fill(content);
        scroll.Add(content);
        return scroll;
    }

    private VisualElement HostPage(string tab, string hint)
    {
        var page = new VisualElement();
        page.style.flexGrow = 1;
        var head = new VisualElement();
        head.AddToClassList("tab-content");
        head.AddToClassList("host-head");
        head.style.backgroundColor = Paleta.PanelSuave;
        head.style.paddingBottom = 8;
        head.style.flexShrink = 0;
        head.Add(Text(hint, "hint"));
        if (!PythonJob.Available && tab == TabModificar)
            head.Add(Text("Requiere Python + OpenSees en el PC (no disponible en este equipo).", "hint"));

        // un sub-panel a la vez: asi nada queda encima de otra cosa
        string[] subs = tab == TabCargas ? new[] { SubMovil, SubElemento, SubPersona } : new[] { SubSeccion, SubArmadura, SubApoyo, SubArea, SubQuitar };
        var seg = Seg();
        seg.style.flexWrap = Wrap.Wrap;   // con muchos sub-paneles los botones pasan a una segunda fila
        var botones = new Dictionary<string, Button>();
        foreach (string nombreSub in subs)
        {
            string sub = nombreSub;
            var b = Btn(sub, () => SelectSub(tab, sub), "wide");
            botones[sub] = b;
            seg.Add(b);
        }
        FinishSeg(seg);
        head.Add(seg);
        var estado = Text("", "hint");
        estado.style.marginTop = 6;
        head.Add(estado);
        syncers.Add(() =>
        {
            string t = EstadoSub(tab);
            if (estado.text != t) estado.text = t;
            estado.style.display = string.IsNullOrEmpty(t) ? DisplayStyle.None : DisplayStyle.Flex;
        });
        page.Add(head);

        var paginas = new Dictionary<string, VisualElement>();
        if (tab == TabModificar)
        {
            paginas[SubSeccion] = SubPagina(BuildSectionEditor);
            paginas[SubArmadura] = SubPagina(BuildArmaduraEditor);
            paginas[SubApoyo] = SubPagina(BuildApoyoEditor);
            paginas[SubArea] = SubPagina(BuildAreaEditor);
            foreach (var pg in paginas.Values) page.Add(pg);
        }
        var host = new VisualElement();
        host.AddToClassList("host");
        page.Add(host);
        hosts[tab] = host;
        subBotones[tab] = botones;
        subPaginas[tab] = paginas;
        SelectSub(tab, tab == TabCargas ? SubCargas : SubModificar);
        return page;
    }

    /// Sub-panel desplazable construido con UI Toolkit (Seccion y Armadura en MODIFICAR).
    private VisualElement SubPagina(System.Action<VisualElement> fill)
    {
        var scroll = new ScrollView(ScrollViewMode.Vertical);
        scroll.AddToClassList("tab-scroll");
        scroll.style.flexGrow = 1;
        var content = new VisualElement();
        content.AddToClassList("tab-content");
        try { fill(content); }
        catch (System.Exception e)
        {
            Debug.LogException(e);
            content.Add(Text("No se pudo construir este panel: " + e.Message, "hint"));
        }
        scroll.Add(content);
        return scroll;
    }

    private void SelectSub(string tab, string sub)
    {
        if (tab == TabCargas) SubCargas = sub; else SubModificar = sub;
        if (subBotones.TryGetValue(tab, out var botones))
            foreach (var kv in botones) kv.Value.EnableInClassList("on", kv.Key == sub);
        if (subPaginas.TryGetValue(tab, out var paginas))
            foreach (var kv in paginas) kv.Value.style.display = kv.Key == sub ? DisplayStyle.Flex : DisplayStyle.None;
        bool imgui = HostVisible(tab);
        if (hosts.TryGetValue(tab, out var host)) host.style.display = imgui ? DisplayStyle.Flex : DisplayStyle.None;
        if (tabBody != null && ActiveTab == tab) tabBody.EnableInClassList("host-mode", imgui);
    }

    /// true si la pestana muestra ahora un panel IMGUI (carga movil, carga en elemento o quitar elemento).
    private static bool HostVisible(string tab)
    {
        return tab == TabCargas || (tab == TabModificar && SubModificar == SubQuitar);
    }

    /// Por que un sub-panel IMGUI no se muestra (vacio si se muestra).
    private string EstadoSub(string tab)
    {
        if (tab == TabCargas)
        {
            if (SubCargas == SubPersona) return "";
            if (UnityData.IsModelModified) return "Con elementos quitados estas cargas no aplican: restaura el modelo original en MODIFICAR → Quitar elemento.";
            if (SubCargas == SubMovil)
            {
                MovingLoadData m = UnityData.GetMovingLoadData();
                if (m == null || m.paths == null || m.paths.Length == 0) return "El análisis cargado no trae casos de carga móvil.";
                if (UnityData.ActiveCombo == UnityData.ElementLoadComboName) return "La carga en elemento está activa: desactívala para usar la carga móvil.";
                return "";
            }
            if (!PythonJob.Available) return "La carga en elemento requiere Python + OpenSees en este equipo.";
            if (UnityData.ActiveCombo == UnityData.MovingLoadComboName) return "La carga móvil está activa: desactívala para usar la carga en elemento.";
            return "";
        }
        if (tab == TabModificar && SubModificar == SubQuitar)
        {
            if (!PythonJob.Available) return "Quitar elementos requiere Python + OpenSees en este equipo.";
            if (UnityData.ActiveCombo == UnityData.MovingLoadComboName || UnityData.ActiveCombo == UnityData.ElementLoadComboName)
                return "Hay una carga móvil o en elemento activa: desactívala para quitar elementos.";
        }
        return "";
    }

    // ---- VISTA ----
    private void BuildVista(VisualElement c)
    {
        c.Add(Title("CAPAS", true));
        var grid = new VisualElement();
        grid.AddToClassList("grid3");
        grid.Add(Check("Columnas", () => viewer.ShowColumnsLayer, v => viewer.ShowColumnsLayer = v));
        grid.Add(Check("Vigas", () => viewer.ShowBeamsLayer, v => viewer.ShowBeamsLayer = v));
        grid.Add(Check("Muros", () => viewer.ShowWallsLayer, v => viewer.ShowWallsLayer = v));
        grid.Add(Check("Apoyos", () => viewer.ShowSupportsLayer, v => viewer.ShowSupportsLayer = v));
        grid.Add(Check("Losas", () => viewer.ShowSlabsLayer, v => viewer.ShowSlabsLayer = v));
        grid.Add(Check("Nodos", () => viewer.ShowNodesLayer, v => viewer.ShowNodesLayer = v));
        grid.Add(Check("IDs", () => viewer.ShowIdsLayer, v => viewer.ShowIdsLayer = v));
        grid.Add(Check("Ejes locales", () => viewer.ShowLocalAxesLayer, v => viewer.ShowLocalAxesLayer = v));
        grid.Add(Check("Cargas", () => viewer.ShowLoadsLayer, v => viewer.ShowLoadsLayer = v));
        grid.Add(Check("Ejes", () => viewer.ShowGridLayer, v => viewer.ShowGridLayer = v));
        grid.Add(Check("Diafragmas", () => viewer.ShowDiaphragmsLayer, v => viewer.ShowDiaphragmsLayer = v));
        c.Add(grid);
        var loadInfo = Text("", "hint");
        c.Add(loadInfo);
        syncers.Add(() =>
        {
            loadInfo.text = viewer.ShowLoadsLayer ? "Cargas del caso activo — " + viewer.LoadOverlaySummary
                : "Cargas: muestra G y Q repartidas en cada viga y EX/EY en el nodo maestro, según el caso o combinación activa.";
        });

        var presets = Row();
        presets.style.marginTop = 6;
        presets.Add(Btn("Mostrar todo", () => viewer.ShowAllLayers(), "wide"));
        presets.Add(Btn("Solo estructura", () => viewer.StructureOnly(), "wide"));
        c.Add(presets);

        c.Add(Title("PISO"));
        var floors = new DropdownField(new List<string>(viewer.FloorNames), viewer.FloorIndex);
        floors.AddToClassList("dropdown");
        floors.RegisterValueChangedCallback(e =>
        {
            viewer.FloorIndex = floors.index;
            viewer.Status = "Filtro de piso: " + e.newValue;
        });
        syncers.Add(() => { if (floors.index != viewer.FloorIndex) floors.SetValueWithoutNotify(viewer.FloorNames[viewer.FloorIndex]); });
        c.Add(floors);

        c.Add(Title("ÁREAS TRIBUTARIAS POR PISO"));
        if (viewer.TributaryFloors.Count == 0) c.Add(Text("Sin resumen tributario en el JSON.", "hint"));
        foreach (var kv in viewer.TributaryFloors)
        {
            c.Add(KeyValue(kv.Key, $"{kv.Value.area_total:0.0} m²  ·  {kv.Value.carga_total:0} kN"));
        }
        c.Add(Title("PANELES"));
        c.Add(Btn("Restablecer posición y tamaño de los paneles", PanelMovible.ReiniciarTodos, "wide"));
        c.Add(Text("Los paneles se mueven arrastrando su franja superior y cambian de tamaño desde la esquina inferior derecha. Doble clic en la franja: vuelve a su lugar.", "hint"));
    }

    // ---- RESULTADOS ----
    private void BuildResultados(VisualElement c)
    {
        c.Add(Title("DIAGRAMA", true));
        c.Add(Text("Plano de flexión (ejes locales del elemento)", "hint"));
        var planes = Seg();
        var planeButtons = new List<Button>();
        string[] planeLabels = { "Auto", "xz · My, Vz", "xy · Mz, Vy" };
        for (int i = 0; i < 3; i++)
        {
            int idx = i;
            Button b = Btn(planeLabels[i], () => { DiagramController.DiagramPlane = (DiagramController.Plane)idx; RefreshDiagrams(); }, "small", "wide");
            planeButtons.Add(b);
            planes.Add(b);
        }
        FinishSeg(planes);
        c.Add(planes);
        syncers.Add(() => { for (int i = 0; i < 3; i++) planeButtons[i].EnableInClassList("on", (int)DiagramController.DiagramPlane == i); });

        var types = Row();
        types.style.marginTop = 6;
        types.Add(Check("Vigas", () => DiagramController.ShowBeams, v => { DiagramController.ShowBeams = v; RefreshDiagrams(); }));
        types.Add(Check("Columnas y arriostres", () => DiagramController.ShowColumns, v => { DiagramController.ShowColumns = v; RefreshDiagrams(); }));
        c.Add(types);

        // escala logaritmica: 0..1 -> x0.1 .. x10
        var scaleRow = new VisualElement();
        scaleRow.AddToClassList("slider-row");
        scaleRow.Add(new Label("Escala"));
        var scale = new Slider(0f, 1f) { value = ScaleToSlider(DiagramController.DiagramScale) };
        scale.AddToClassList("slider");
        var scaleNum = Text("", "num");
        scale.RegisterValueChangedCallback(e =>
        {
            DiagramController.DiagramScale = Mathf.Pow(10f, 2f * e.newValue - 1f);
            scaleNum.text = "x" + DiagramController.DiagramScale.ToString("0.00");
        });
        scale.RegisterCallback<PointerCaptureOutEvent>(_ => RefreshDiagrams());
        scaleRow.Add(scale);
        scaleRow.Add(scaleNum);
        c.Add(scaleRow);
        syncers.Add(() =>
        {
            float s = ScaleToSlider(DiagramController.DiagramScale);
            if (Mathf.Abs(scale.value - s) > 0.002f && scale.panel?.GetCapturingElement(PointerId.mousePointerId) != scale) scale.SetValueWithoutNotify(s);
            scaleNum.text = "x" + DiagramController.DiagramScale.ToString("0.00");
        });

        var labels = new DropdownField("Etiquetas", new List<string> { "No", "Máximos", "Seleccionado" },
            (int)DiagramController.Labels);
        labels.AddToClassList("dropdown");
        labels.RegisterValueChangedCallback(_ => DiagramController.Labels = (DiagramController.LabelMode)labels.index);
        c.Add(labels);
        c.Add(Check("Animar la deformada", () => DiagramController.AnimateDeformed, v => DiagramController.AnimateDeformed = v));

        c.Add(Title("CONVENCIÓN"));
        c.Add(Legend(Paleta.DiagPosLinea, "M+ (tracción abajo) · N tracción · V+"));
        c.Add(Legend(Paleta.DiagNegLinea, "M− (tracción arriba) · N compresión · V−"));
        c.Add(Text("El momento se dibuja del lado traccionado. Escala común a todo el modelo: el tamaño compara barras entre sí. " +
                   "Pasa el mouse sobre un diagrama para leer x y el valor.", "hint"));

        c.Add(Title("COLOREAR POR UTILIZACIÓN"));
        c.Add(Check("Demanda / capacidad P-M (C)", () => viewer.UtilizationColors, v =>
        {
            viewer.SetUtilizationVisible(v);
            viewer.Status = v ? "Colores por C = demanda/capacidad P-M." : "Colores por capa restaurados.";
        }));
        c.Add(Legend(Paleta.UsoOk, "C ≤ 0,7"));
        c.Add(Legend(Paleta.UsoLimite, "C ≈ 1"));
        c.Add(Legend(Paleta.UsoFalla, "C > 1"));

        c.Add(Title("SUPERPOSICIÓN EN VIVO"));
        c.Add(Text("SUP = λG·G + λQ·Q + λEX·EX + λEY·EY, sin reanalizar (análisis lineal).", "hint"));
        float[] lam = viewer.SuperpositionValues;
        var sliders = new Slider[4];
        string[] names = { "λG", "λQ", "λEX", "λEY" };
        var supToggle = new Toggle("Activar superposición") { value = viewer.SuperpositionActive };
        supToggle.AddToClassList("chk");
        System.Action apply = () => viewer.SetSuperposition(supToggle.value, sliders[0].value, sliders[1].value, sliders[2].value, sliders[3].value);
        supToggle.RegisterValueChangedCallback(_ => apply());
        c.Add(supToggle);
        for (int i = 0; i < 4; i++)
        {
            var row = new VisualElement();
            row.AddToClassList("slider-row");
            row.Add(new Label(names[i]));
            var s = new Slider(-3f, 4f) { value = lam[i] };
            s.AddToClassList("slider");
            var num = Text(lam[i].ToString("0.00"), "num");
            s.RegisterValueChangedCallback(e => { num.text = e.newValue.ToString("0.00"); if (supToggle.value) apply(); });
            sliders[i] = s;
            row.Add(s);
            row.Add(num);
            c.Add(row);
        }
        var supButtons = Row();
        supButtons.Add(Btn("λ = 1", () => { foreach (var s in sliders) s.value = 1f; }, "wide"));
        supButtons.Add(Btn("Solo G", () => { sliders[0].value = 1f; sliders[1].value = 0f; sliders[2].value = 0f; sliders[3].value = 0f; }, "wide"));
        c.Add(supButtons);
        syncers.Add(() => { if (supToggle.value != viewer.SuperpositionActive) supToggle.SetValueWithoutNotify(viewer.SuperpositionActive); });
    }

    private static float ScaleToSlider(float scale) => (Mathf.Log10(Mathf.Clamp(scale, 0.1f, 10f)) + 1f) / 2f;

    private void RefreshDiagrams()
    {
        if (diagrams != null) diagrams.Refresh();
    }

    // ---- MODIFICAR: armadura del elemento seleccionado ----
    private void BuildArmaduraEditor(VisualElement c)
    {
        c.Add(Title("ARMADURA (ACI 318)", true));
        var info = Text("Selecciona una viga o columna de hormigón.", "hint");
        c.Add(info);
        var estado = Text("", "line");
        c.Add(estado);

        // campos: vigas (5) y columnas (2); se muestran segun el tipo
        string[] beamKeys = { "Inferior", "Superior", "Suple apoyo", "Estribos apoyo", "Estribos tramo" };
        string[] colKeys = { "Barras", "Estribos" };
        var beamFields = new List<TextField>();
        var colFields = new List<TextField>();
        var beamBox = new VisualElement();
        var colBox = new VisualElement();
        foreach (string k in beamKeys) { var f = ArmField(k); beamFields.Add(f); beamBox.Add(f); }
        foreach (string k in colKeys) { var f = ArmField(k); colFields.Add(f); colBox.Add(f); }
        c.Add(beamBox);
        c.Add(colBox);
        c.Add(Text("Notación: 4f22 o 4φ22, 2f22+2f25; estribos Ef10a10 (2 ramas), EDf10a10 (doble, 4 ramas).", "hint"));

        var row1 = Row();
        var toElem = Btn("Aplicar al elemento", null, "wide");
        var toSec = Btn("Aplicar a la sección", null, "wide");
        row1.Add(toElem);
        row1.Add(toSec);
        c.Add(row1);
        var row2 = Row();
        var clear = Btn("Quitar cambios", null, "wide");
        var run = Btn("Reanalizar ahora", () => { if (Session.StartReanalysis()) viewer.Status = "Reanálisis en curso..."; else viewer.Status = Session.Message; }, "wide");
        row2.Add(clear);
        row2.Add(run);
        c.Add(row2);
        var pending = Text("", "hint");
        c.Add(pending);

        ElementData current = null;
        System.Func<AnalysisSession.Arm> read = () =>
        {
            var a = new AnalysisSession.Arm();
            if (current == null) return a;
            ArmaduraData now = current.capacidad != null ? current.capacidad.armadura : null;
            string Pick(TextField f, string old) => string.IsNullOrWhiteSpace(f.value) || f.value.Trim() == (old ?? "") ? null : f.value.Trim();
            if (current.type == "viga")
            {
                a.inferior = Pick(beamFields[0], now?.inferior);
                a.superior = Pick(beamFields[1], now?.superior);
                a.supleApoyo = Pick(beamFields[2], now?.supleApoyo);
                a.estribosApoyo = Pick(beamFields[3], now?.estribosApoyo);
                a.estribosTramo = Pick(beamFields[4], now?.estribosTramo);
            }
            else
            {
                a.barras = Pick(colFields[0], now?.barras);
                a.estribos = Pick(colFields[1], now?.estribos);
            }
            return a;
        };
        System.Action fill = () =>
        {
            ArmaduraData now = current != null && current.capacidad != null ? current.capacidad.armadura : null;
            AnalysisSession.Arm pendingElem = current != null && Session.armElem.TryGetValue(current.elementTag, out var pe) ? pe : null;
            AnalysisSession.Arm pendingSec = current != null && Session.armSec.TryGetValue(current.sectionId ?? "", out var ps) ? ps : null;
            string V(string elem, string sec, string cur) => elem ?? sec ?? cur ?? "";
            beamFields[0].SetValueWithoutNotify(V(pendingElem?.inferior, pendingSec?.inferior, now?.inferior));
            beamFields[1].SetValueWithoutNotify(V(pendingElem?.superior, pendingSec?.superior, now?.superior));
            beamFields[2].SetValueWithoutNotify(V(pendingElem?.supleApoyo, pendingSec?.supleApoyo, now?.supleApoyo));
            beamFields[3].SetValueWithoutNotify(V(pendingElem?.estribosApoyo, pendingSec?.estribosApoyo, now?.estribosApoyo));
            beamFields[4].SetValueWithoutNotify(V(pendingElem?.estribosTramo, pendingSec?.estribosTramo, now?.estribosTramo));
            colFields[0].SetValueWithoutNotify(V(pendingElem?.barras, pendingSec?.barras, now?.barras));
            colFields[1].SetValueWithoutNotify(V(pendingElem?.estribos, pendingSec?.estribos, now?.estribos));
        };
        toElem.clicked += () =>
        {
            if (current == null) return;
            AnalysisSession.Arm a = read();
            if (a.Describe().Length == 0) { viewer.Status = "Sin cambios de armadura."; return; }
            Session.armElem[current.elementTag] = a;
            viewer.Status = $"Armadura de {current.elementTag}: {a.Describe()}. Reanaliza para ver el factor de uso.";
        };
        toSec.clicked += () =>
        {
            if (current == null) return;
            AnalysisSession.Arm a = read();
            if (a.Describe().Length == 0) { viewer.Status = "Sin cambios de armadura."; return; }
            Session.armSec[current.sectionId] = a;
            viewer.Status = $"Armadura tipo de {current.sectionId}: {a.Describe()}. Reanaliza para ver el factor de uso.";
        };
        clear.clicked += () =>
        {
            if (current == null) return;
            Session.armElem.Remove(current.elementTag);
            Session.armSec.Remove(current.sectionId ?? "");
            fill();
        };

        syncers.Add(() =>
        {
            ElementData e = picker != null && picker.Selected != null ? picker.Selected.data : null;
            bool editable = e != null && e.capacidad != null && e.capacidad.armadura != null && (e.type == "viga" || e.type == "columna");
            ElementData next = editable ? e : null;
            if (next != current)
            {
                current = next;
                fill();
            }
            beamBox.style.display = current != null && current.type == "viga" ? DisplayStyle.Flex : DisplayStyle.None;
            colBox.style.display = current != null && current.type == "columna" ? DisplayStyle.Flex : DisplayStyle.None;
            info.text = current != null ? $"{current.elementTag} · {current.type} {current.sectionId}"
                : e != null ? $"{e.elementTag}: sin armadura de hormigón editable" : "Selecciona una viga o columna de hormigón.";
            if (current != null)
            {
                CapacityData cap = current.capacidad;
                CapacityCombo cc = cap.ForCombo(UnityData.ActiveCombo);
                float dcr = cc != null ? Mathf.Max(cc.DCR_flexion, Mathf.Max(cc.DCR_corte, cc.DCR_PM)) : cap.DCR;
                string semaforo = dcr > 1f ? "NO CUMPLE" : dcr > 0.9f ? "al límite" : "cumple";
                estado.text = current.type == "viga"
                    ? $"φMn+ {cap.phiMn_pos_kN_m:0} · φMn− {cap.phiMn_neg_kN_m:0} kN·m · φVn {cap.phiVn_apoyo_kN:0} kN · DCR {dcr:0.00} ({semaforo})"
                    : $"φPmax {cap.phiPmax_kN:0} kN · Ast {cap.Ast_mm2:0} mm² · DCR {dcr:0.00} ({semaforo})";
                estado.style.color = dcr > 1f ? Paleta.SemaforoFalla : dcr > 0.9f ? Paleta.SemaforoLimite : Paleta.SemaforoOk;
            }
            else estado.text = "";
            toElem.SetEnabled(current != null && !Session.job.Running);
            toSec.SetEnabled(current != null && !Session.job.Running);
            clear.SetEnabled(current != null);
            run.SetEnabled(PythonJob.Available && !Session.job.Running);
            run.text = Session.job.Running ? $"Analizando... {Session.job.Elapsed:0} s" : "Reanalizar ahora";
            var lines = new List<string>();
            foreach (var kv in Session.armSec) lines.Add($"Sección {kv.Key}: {kv.Value.Describe()}");
            foreach (var kv in Session.armElem) lines.Add($"{kv.Key}: {kv.Value.Describe()}");
            pending.text = lines.Count == 0 ? "Sin cambios de armadura pendientes." : "Pendientes:\n" + string.Join("\n", lines);
        });
    }

    private TextField ArmField(string label)
    {
        var f = Input(new TextField(label) { value = "" });
        f.AddToClassList("dropdown");
        f.RegisterCallback<FocusInEvent>(_ => TextFocused = true);
        f.RegisterCallback<FocusOutEvent>(_ => TextFocused = false);
        return f;
    }

    // ---- MODIFICAR: cambio de seccion ----
    private void BuildSectionEditor(VisualElement c)
    {
        c.Add(Title("CAMBIAR SECCIÓN", true));
        var info = Text("Selecciona una viga o columna de hormigón en el modelo.", "line");
        c.Add(info);

        // secciones rectangulares de hormigon del modelo, de menor a mayor area
        // (las de acero y los muros equivalentes no se editan aqui)
        var presets = new Dictionary<string, Vector2>();
        foreach (ElementData e in viewer.Data.elements)
        {
            string sid = e.sectionId ?? "";
            if ((sid.StartsWith("V") && !sid.StartsWith("VM")) || sid.StartsWith("COL")) presets[sid] = new Vector2(e.width_m, e.height_m);
        }
        var orden = new List<string>(presets.Keys);
        orden.Sort((a, b) => (presets[a].x * presets[a].y).CompareTo(presets[b].x * presets[b].y));
        var choices = new List<string>(orden);
        if (choices.Count == 0) choices.Add("—");
        var preset = new DropdownField("Sección del modelo", choices, 0);
        preset.AddToClassList("dropdown");
        c.Add(preset);

        var bField = Input(new FloatField("b [m]") { value = 0.6f, formatString = "0.00" });
        var hField = Input(new FloatField("h [m]") { value = 0.8f, formatString = "0.00" });
        bField.AddToClassList("dropdown");
        hField.AddToClassList("dropdown");
        foreach (FloatField f in new[] { bField, hField })
        {
            FloatField campo = f;
            var fila = Row();
            campo.style.flexGrow = 1;
            fila.Add(campo);
            fila.Add(Btn("−5 cm", () => campo.value = Mathf.Max(0.15f, Mathf.Round((campo.value - 0.05f) * 100f) / 100f), "small"));
            fila.Add(Btn("+5 cm", () => campo.value = Mathf.Min(2.0f, Mathf.Round((campo.value + 0.05f) * 100f) / 100f), "small"));
            c.Add(fila);
        }
        preset.RegisterValueChangedCallback(e =>
        {
            if (presets.TryGetValue(e.newValue, out Vector2 d)) { bField.value = d.x; hField.value = d.y; }
        });

        var tam = Row();
        var menor = Btn("◀ Más pequeña", null, "wide");
        var mayor = Btn("Más grande ▶", null, "wide");
        tam.Add(menor);
        tam.Add(mayor);
        c.Add(tam);
        var resumen = Text("", "line");
        c.Add(resumen);
        bool todas = false;
        c.Add(Check("Aplicar a todos los elementos con la misma sección", () => todas, v => todas = v));

        var buttons = Row();
        var add = Btn("Agregar cambio", null, "wide");
        var undo = Btn("Quitar cambio", null, "wide");
        buttons.Add(add);
        buttons.Add(undo);
        c.Add(buttons);
        var run = Btn("Reanalizar ahora", () => { if (Session.StartReanalysis()) viewer.Status = "Reanálisis en curso..."; else viewer.Status = Session.Message; }, "wide");
        run.style.height = 28;
        c.Add(run);
        var progreso = Text("", "hint");
        c.Add(progreso);

        c.Add(Title("CAMBIOS PENDIENTES"));
        var list = new VisualElement();
        c.Add(list);
        var vaciar = Btn("Quitar todos los cambios de sección", () => Session.sections.Clear(), "wide");
        c.Add(vaciar);
        c.Add(Text("Al reanalizar, OpenSees recalcula rigidez, peso propio, esfuerzos y capacidad con las secciones nuevas. Los archivos del modelo no se modifican.", "hint"));

        ElementData current = null;
        string Id(ElementData e, float b, float h) => $"{(e.type == "columna" ? "COL" : "V")}{Mathf.RoundToInt(b * 100)}/{Mathf.RoundToInt(h * 100)}";
        System.Action refreshList = () =>
        {
            list.Clear();
            if (Session.sections.Count == 0) { list.Add(Text("Sin cambios de sección.", "hint")); return; }
            foreach (var sc in Session.sections.Values)
                list.Add(KeyValue(sc.tag, $"{sc.before} → {sc.sectionId} ({sc.width:0.00} × {sc.height:0.00} m)"));
        };
        System.Action<int> cambiarTamano = dir =>
        {
            if (current == null) return;
            string fam = current.type == "columna" ? "COL" : "V";
            float area = bField.value * hField.value;
            string elegido = null;
            if (dir > 0)
            {
                foreach (string sid in orden)
                    if (sid.StartsWith(fam) && presets[sid].x * presets[sid].y > area + 1e-4f) { elegido = sid; break; }
            }
            else
            {
                for (int i = orden.Count - 1; i >= 0; i--)
                    if (orden[i].StartsWith(fam) && presets[orden[i]].x * presets[orden[i]].y < area - 1e-4f) { elegido = orden[i]; break; }
            }
            if (elegido != null) { preset.value = elegido; return; }
            // no hay otra seccion del modelo en esa direccion: se escala 10 %, redondeado a 5 cm
            float k = dir > 0 ? 1.1f : 0.9f;
            bField.value = Mathf.Clamp(Mathf.Round(bField.value * k * 20f) / 20f, 0.15f, 2f);
            hField.value = Mathf.Clamp(Mathf.Round(hField.value * k * 20f) / 20f, 0.15f, 2f);
        };
        menor.clicked += () => cambiarTamano(-1);
        mayor.clicked += () => cambiarTamano(1);
        add.clicked += () =>
        {
            if (current == null) return;
            float b = Mathf.Clamp(bField.value, 0.15f, 2f), h = Mathf.Clamp(hField.value, 0.15f, 2f);
            string sid = Id(current, b, h);
            int n = 0;
            foreach (ElementData e in viewer.Data.elements)
            {
                bool aplica = todas ? (e.type == current.type && e.sectionId == current.sectionId) : e == current;
                if (!aplica) continue;
                string before = Session.sections.TryGetValue(e.id, out var prev) ? prev.before : e.sectionId;
                Session.SetSection(e, sid, b, h, before);
                n++;
            }
            viewer.Status = n == 1
                ? $"Cambio pendiente: {current.elementTag} {current.sectionId} → {sid}. Toca «Reanalizar ahora»."
                : $"Cambio pendiente en {n} elementos {current.sectionId} → {sid}. Toca «Reanalizar ahora».";
            refreshList();
        };
        undo.clicked += () =>
        {
            if (current == null) return;
            if (todas)
            {
                foreach (ElementData e in viewer.Data.elements)
                    if (e.type == current.type && e.sectionId == current.sectionId) Session.sections.Remove(e.id);
            }
            else Session.sections.Remove(current.id);
            refreshList();
        };
        refreshList();
        syncers.Add(() =>
        {
            ElementData e = picker != null && picker.Selected != null ? picker.Selected.data : null;
            bool editable = e != null && (e.type == "viga" || e.type == "columna") && presets.ContainsKey(e.sectionId ?? "");
            if (e != current)
            {
                current = editable ? e : null;
                if (current != null)
                {
                    preset.SetValueWithoutNotify(current.sectionId);
                    bField.SetValueWithoutNotify(current.width_m);
                    hField.SetValueWithoutNotify(current.height_m);
                }
            }
            info.text = current != null ? $"{current.elementTag} · {current.type} · sección actual {current.sectionId} ({current.width_m:0.00} × {current.height_m:0.00} m)"
                : e != null ? $"{e.elementTag}: sección {e.sectionId} (no editable aquí: acero o muro)" : "Selecciona una viga o columna de hormigón en el modelo.";
            if (current != null)
            {
                float b = bField.value, h = hField.value;
                float a0 = current.width_m * current.height_m, a1 = b * h;
                float i0 = current.width_m * Mathf.Pow(current.height_m, 3f), i1 = b * Mathf.Pow(h, 3f);
                string t = $"Nueva: {Id(current, b, h)} · área × {(a0 > 0f ? a1 / a0 : 0f):0.00} · inercia × {(i0 > 0f ? i1 / i0 : 0f):0.00} · peso propio {a0 * 25f:0.0} → {a1 * 25f:0.0} kN/m";
                if (resumen.text != t) resumen.text = t;
            }
            else if (resumen.text != "") resumen.text = "";
            bool running = Session.job.Running;
            add.SetEnabled(current != null && !running);
            undo.SetEnabled(current != null && Session.sections.Count > 0);
            menor.SetEnabled(current != null && !running);
            mayor.SetEnabled(current != null && !running);
            vaciar.SetEnabled(Session.sections.Count > 0 && !running);
            run.SetEnabled(PythonJob.Available && !running);
            run.text = running ? $"Analizando... {Session.job.Elapsed:0} s" : "Reanalizar ahora";
            progreso.text = running ? (Session.job.LastLine ?? "") : Session.Message;
            if (list.childCount != Mathf.Max(1, Session.sections.Count)) refreshList();
        });
    }

    // ---- MODIFICAR → Apoyo ----
    private void BuildApoyoEditor(VisualElement c)
    {
        c.Add(Title("CAMBIAR APOYO", true));
        c.Add(Text("Selecciona un apoyo (el dado bajo una columna o muro) o una columna o muro: se usa su nudo inferior. También puedes escribir el número del nodo. Requiere reanálisis.", "hint"));
        var info = Text("", "line");
        c.Add(info);
        var campo = Input(new IntegerField("Nodo") { value = 0 });
        campo.AddToClassList("dropdown");
        c.Add(campo);
        var fila1 = Row();
        var empotrado = Btn("Empotrado", null, "wide");
        var articulado = Btn("Articulado", null, "wide");
        var deslizante = Btn("Deslizante", null, "wide");
        fila1.Add(empotrado);
        fila1.Add(articulado);
        fila1.Add(deslizante);
        c.Add(fila1);
        var fila2 = Row();
        var libre = Btn("Sin apoyo", null, "wide");
        var deshacer = Btn("Deshacer", null, "wide");
        fila2.Add(libre);
        fila2.Add(deshacer);
        c.Add(fila2);
        var run = Btn("Reanalizar ahora", () => { if (Session.StartReanalysis()) viewer.Status = "Reanálisis en curso..."; else viewer.Status = Session.Message; }, "wide");
        run.style.height = 28;
        c.Add(run);
        c.Add(Title("CAMBIOS DE APOYO PENDIENTES"));
        var list = new VisualElement();
        c.Add(list);
        c.Add(Text("Empotrado: restringe los 6 grados de libertad. Articulado: restringe las traslaciones y deja libres los giros. Deslizante: solo restringe la traslación vertical. Sin apoyo: el nodo queda libre; si es la base de una columna, revisa que la estructura siga siendo estable.", "hint"));

        System.Action<string> poner = tipo =>
        {
            int n = campo.value;
            if (!NodoExiste(n)) { viewer.Status = $"El nodo {n} no existe en el modelo."; return; }
            Session.apoyos[n] = tipo;
            viewer.Status = $"Cambio pendiente: apoyo del nodo {n} → {NombreApoyo(tipo)}. Toca «Reanalizar ahora».";
        };
        empotrado.clicked += () => poner("fixed");
        articulado.clicked += () => poner("pinned");
        deslizante.clicked += () => poner("roller");
        libre.clicked += () => poner("libre");
        deshacer.clicked += () => Session.apoyos.Remove(campo.value);
        int ultimoSel = -1;
        int vistos = -1;
        syncers.Add(() =>
        {
            int sel = NodoSeleccionado();
            if (sel >= 0 && sel != ultimoSel) { ultimoSel = sel; campo.SetValueWithoutNotify(sel); }
            string pend = Session.apoyos.TryGetValue(campo.value, out string t) ? $" → pendiente: {NombreApoyo(t)}" : "";
            info.text = NodoExiste(campo.value) ? $"Nodo {campo.value}: apoyo actual {ApoyoActual(campo.value)}{pend}" : "Selecciona un apoyo, una columna o un muro, o escribe un nodo.";
            bool running = Session.job.Running;
            run.SetEnabled(PythonJob.Available && !running);
            run.text = running ? $"Analizando... {Session.job.Elapsed:0} s" : "Reanalizar ahora";
            if (vistos != Session.apoyos.Count)
            {
                vistos = Session.apoyos.Count;
                list.Clear();
                if (Session.apoyos.Count == 0) list.Add(Text("Sin cambios de apoyo.", "hint"));
                foreach (var ap in Session.apoyos) list.Add(KeyValue($"Nodo {ap.Key}", $"{ApoyoActual(ap.Key)} → {NombreApoyo(ap.Value)}"));
            }
        });
    }

    private static string NombreApoyo(string tipo)
    {
        return tipo == "fixed" ? "empotrado" : tipo == "pinned" ? "articulado" : tipo == "roller" ? "deslizante" : "sin apoyo";
    }

    private bool NodoExiste(int n)
    {
        if (viewer == null || viewer.Data == null || viewer.Data.nodes == null) return false;
        foreach (NodeData nd in viewer.Data.nodes) if (nd.id == n) return true;
        return false;
    }

    private string ApoyoActual(int n)
    {
        if (viewer == null || viewer.Data == null || viewer.Data.supports == null) return "—";
        foreach (SupportData s in viewer.Data.supports)
        {
            if (s.node != n) continue;
            if (s.ux == 1 && s.uy == 1 && s.uz == 1 && s.rx == 1 && s.ry == 1 && s.rz == 1) return "empotrado";
            if (s.ux == 1 && s.uy == 1 && s.uz == 1) return "articulado";
            return "parcial";
        }
        return "sin apoyo";
    }

    /// Nodo del apoyo seleccionado ("Apoyo_..._N123") o nudo inferior de la columna o muro seleccionado.
    private int NodoSeleccionado()
    {
        if (picker == null) return -1;
        string nombre = picker.SelectedInfoName;
        if (!string.IsNullOrEmpty(nombre) && nombre.StartsWith("Apoyo"))
        {
            int k = nombre.LastIndexOf("_N");
            if (k >= 0 && int.TryParse(nombre.Substring(k + 2), out int n)) return n;
        }
        ElementData e = picker.Selected != null ? picker.Selected.data : null;
        if (e != null && (e.type == "columna" || e.type == "muro") && viewer != null && viewer.Data != null)
        {
            float zi = float.MaxValue, zj = float.MaxValue;
            foreach (NodeData nd in viewer.Data.nodes)
            {
                if (nd.id == e.nodeI) zi = nd.z;
                if (nd.id == e.nodeJ) zj = nd.z;
            }
            return zi <= zj ? e.nodeI : e.nodeJ;
        }
        return -1;
    }

    // ---- MODIFICAR → Area tributaria ----
    private void BuildAreaEditor(VisualElement c)
    {
        c.Add(Title("ÁREA TRIBUTARIA", true));
        c.Add(Text("Selecciona una viga. Su área tributaria define la carga de losa que recibe: G = q_G · A y Q = q · A. Requiere reanálisis.", "hint"));
        var info = Text("Selecciona una viga.", "line");
        c.Add(info);
        var area = Input(new FloatField("Área [m²]") { value = 0f, formatString = "0.00" });
        area.AddToClassList("dropdown");
        var fila = Row();
        area.style.flexGrow = 1;
        fila.Add(area);
        fila.Add(Btn("−10 %", () => area.value = Mathf.Max(0f, area.value * 0.9f), "small"));
        fila.Add(Btn("+10 %", () => area.value = area.value * 1.1f, "small"));
        c.Add(fila);
        var resumen = Text("", "line");
        c.Add(resumen);
        var botones = Row();
        var add = Btn("Agregar cambio", null, "wide");
        var undo = Btn("Quitar cambio", null, "wide");
        botones.Add(add);
        botones.Add(undo);
        c.Add(botones);
        var run = Btn("Reanalizar ahora", () => { if (Session.StartReanalysis()) viewer.Status = "Reanálisis en curso..."; else viewer.Status = Session.Message; }, "wide");
        run.style.height = 28;
        c.Add(run);
        c.Add(Title("CAMBIOS DE ÁREA PENDIENTES"));
        var list = new VisualElement();
        c.Add(list);
        c.Add(Text("El área que se quita a una viga no pasa sola a sus vecinas: la carga total del piso cambia. Para redistribuir, ajusta también las vigas vecinas. En VISTA se ve el área tributaria por piso.", "hint"));

        ElementData current = null;
        add.clicked += () =>
        {
            if (current == null) return;
            Session.tributarias[current.id] = Mathf.Max(0f, area.value);
            viewer.Status = $"Cambio pendiente: área tributaria de {current.elementTag} {current.areaTributaria:0.00} → {Mathf.Max(0f, area.value):0.00} m². Toca «Reanalizar ahora».";
        };
        undo.clicked += () => { if (current != null) Session.tributarias.Remove(current.id); };
        int vistos = -1;
        syncers.Add(() =>
        {
            ElementData e = picker != null && picker.Selected != null ? picker.Selected.data : null;
            bool editable = e != null && e.type == "viga";
            if (e != current)
            {
                current = editable ? e : null;
                if (current != null) area.SetValueWithoutNotify(Session.tributarias.TryGetValue(current.id, out float a) ? a : current.areaTributaria);
            }
            info.text = current != null ? $"{current.elementTag} · área actual {current.areaTributaria:0.00} m² · carga muerta de losa {current.deadLoad:0.0} kN"
                : e != null ? $"{e.elementTag}: solo las vigas reciben área de losa." : "Selecciona una viga.";
            if (current != null)
            {
                float a0 = current.areaTributaria, a1 = Mathf.Max(0f, area.value);
                float qg = viewer.Data != null && viewer.Data.q_G > 0f ? viewer.Data.q_G : Session.qG;
                float qq = Session.qKgM2 * 0.00980665f;
                string t = $"Cambio: {a0:0.00} → {a1:0.00} m² · ΔG = {(a1 - a0) * qg:0.0} kN · ΔQ = {(a1 - a0) * qq:0.0} kN";
                if (resumen.text != t) resumen.text = t;
            }
            else if (resumen.text != "") resumen.text = "";
            bool running = Session.job.Running;
            add.SetEnabled(current != null && !running);
            undo.SetEnabled(current != null && Session.tributarias.ContainsKey(current.id));
            run.SetEnabled(PythonJob.Available && !running);
            run.text = running ? $"Analizando... {Session.job.Elapsed:0} s" : "Reanalizar ahora";
            if (vistos != Session.tributarias.Count)
            {
                vistos = Session.tributarias.Count;
                list.Clear();
                if (Session.tributarias.Count == 0) list.Add(Text("Sin cambios de área tributaria.", "hint"));
                foreach (var tr in Session.tributarias) list.Add(KeyValue($"Elemento {tr.Key}", $"{tr.Value:0.00} m²"));
            }
        });
    }

    // ---- ANALISIS: parametros, combinaciones y reanalisis ----
    private void BuildAnalisis(VisualElement c)
    {
        StructureData d = viewer.Data;
        c.Add(Title("MODELO", true));
        if (d != null)
        {
            int beams = 0, cols = 0, braces = 0, walls = 0, links = 0;
            foreach (ElementData e in d.elements)
            {
                if (e.type == "viga") beams++; else if (e.type == "columna") cols++; else if (e.type == "muro") walls++;
                else if (e.type == "rigido") links++; else braces++;
            }
            c.Add(KeyValue("Nodos · elementos", $"{d.nodes.Length} · {beams + cols + braces} ({beams} V, {cols} C, {braces} A)"));
            if (walls > 0) c.Add(KeyValue("Muros en el análisis", $"{walls} paños (columna ancha) · {links} brazos rígidos"));
            c.Add(KeyValue("Muros · apoyos", $"{d.walls?.Length ?? 0} · {d.supports?.Length ?? 0}"));
            c.Add(KeyValue("Resultados cargados", viewer.LoadedSource));
        }

        c.Add(Title("PARÁMETROS DE CARGA"));
        var qG = Input(new FloatField("q_G losa + terminaciones [kN/m²]") { value = Session.qG, formatString = "0.###" });
        var qQ = Input(new FloatField("Q sobrecarga de uso [kg/m²]") { value = Session.qKgM2, formatString = "0.###" });
        var qR = Input(new FloatField("Q cubierta [kg/m²]") { value = Session.qCubiertaKgM2, formatString = "0.###" });
        foreach (var f in new[] { qG, qQ, qR })
        {
            f.AddToClassList("dropdown");
            c.Add(f);
        }
        qG.RegisterValueChangedCallback(e => Session.qG = Mathf.Max(0f, e.newValue));
        qQ.RegisterValueChangedCallback(e => Session.qKgM2 = Mathf.Max(0f, e.newValue));
        qR.RegisterValueChangedCallback(e => Session.qCubiertaKgM2 = Mathf.Max(0f, e.newValue));
        c.Add(Text("G = q_G·A_trib + peso propio (25 kN/m³ hormigón, 78,5 kN/m³ acero).", "hint"));

        // sismo: NCh433 estatico (C por edificio y direccion con T* del modal) o C fijo
        c.Add(Title("SISMO"));
        var metodo = new DropdownField("Método", new List<string> { "NCh433", "C fijo" }, Session.sismoNCh ? 0 : 1);
        var zonas = new List<string> { "1", "2", "3" };
        var zona = new DropdownField("Zona sísmica", zonas, Mathf.Clamp(Session.zona - 1, 0, 2));
        var suelos = new List<string> { "A", "B", "C", "D", "E" };
        var suelo = new DropdownField("Suelo", suelos, Mathf.Max(0, suelos.IndexOf(Session.suelo)));
        var rField = Input(new FloatField("R") { value = Session.R, formatString = "0.##" });
        var iField = Input(new FloatField("I (importancia)") { value = Session.I, formatString = "0.##" });
        var fqField = Input(new FloatField("Fracción de Q en P") { value = Session.fraccionQ, formatString = "0.##" });
        var sc = Input(new FloatField("Coeficiente sísmico C") { value = Session.seismicCoeff, formatString = "0.###" });
        var nchBox = new VisualElement();
        foreach (VisualElement f in new VisualElement[] { zona, suelo, rField, iField, fqField }) { f.AddToClassList("dropdown"); nchBox.Add(f); }
        nchBox.Add(Text("C = 2,75·S·A0/(g·R)·(T'/T*)ⁿ con Cmin ≤ C ≤ Cmax; T* del modal de cada edificio y dirección. " +
                        "P = D + fracción·Q (0,25 habitual, 0,50 con aglomeración de público). Q0 = C·I·P repartido en altura con Ak.", "hint"));
        var fijoBox = new VisualElement();
        sc.AddToClassList("dropdown");
        fijoBox.Add(sc);
        fijoBox.Add(Text("Criterio de las semanas 3 a 6: F = C·(D + 0,5Q) en cada piso, igual en X e Y.", "hint"));
        metodo.AddToClassList("dropdown");
        c.Add(metodo);
        c.Add(nchBox);
        c.Add(fijoBox);
        System.Action showSismo = () =>
        {
            nchBox.style.display = Session.sismoNCh ? DisplayStyle.Flex : DisplayStyle.None;
            fijoBox.style.display = Session.sismoNCh ? DisplayStyle.None : DisplayStyle.Flex;
        };
        showSismo();
        metodo.RegisterValueChangedCallback(_ => { Session.sismoNCh = metodo.index == 0; showSismo(); });
        zona.RegisterValueChangedCallback(_ => Session.zona = zona.index + 1);
        suelo.RegisterValueChangedCallback(_ => Session.suelo = suelos[suelo.index]);
        rField.RegisterValueChangedCallback(e => Session.R = Mathf.Max(1f, e.newValue));
        iField.RegisterValueChangedCallback(e => Session.I = Mathf.Max(0.1f, e.newValue));
        fqField.RegisterValueChangedCallback(e => Session.fraccionQ = Mathf.Clamp01(e.newValue));
        sc.RegisterValueChangedCallback(e => Session.seismicCoeff = Mathf.Max(0f, e.newValue));

        c.Add(Title("MATERIAL: HORMIGÓN"));
        var fc = Input(new FloatField("f'c [MPa]") { value = Session.fcMPa, formatString = "0.#" });
        fc.AddToClassList("dropdown");
        c.Add(fc);
        fc.RegisterValueChangedCallback(e => Session.fcMPa = Mathf.Clamp(e.newValue, 15f, 90f));
        var fcRow = Row();
        foreach (float valor in new[] { 25f, 30f, 35f, 40f })
        {
            float v = valor;
            fcRow.Add(Btn($"G{v:0}", () => fc.value = v, "wide"));
        }
        c.Add(fcRow);
        var eTxt = Text("", "hint");
        c.Add(eTxt);
        syncers.Add(() =>
        {
            string t = $"E = 4700·√f'c = {4700f * Mathf.Sqrt(Session.fcMPa):0} MPa. Cambia la rigidez de vigas, columnas y muros y la capacidad ACI (P-M, flexión y corte). Requiere reanálisis.";
            if (eTxt.text != t) eTxt.text = t;
        });

        c.Add(Title("RIGIDEZ (FACTOR SOBRE LA INERCIA BRUTA)"));
        var kv = Input(new FloatField("Vigas") { value = Session.kViga, formatString = "0.###" });
        var kc = Input(new FloatField("Columnas") { value = Session.kColumna, formatString = "0.###" });
        var km = Input(new FloatField("Muros") { value = Session.kMuro, formatString = "0.###" });
        foreach (var f in new[] { kv, kc, km }) { f.AddToClassList("dropdown"); c.Add(f); }
        kv.RegisterValueChangedCallback(e => Session.kViga = Mathf.Clamp(e.newValue, 0.05f, 1f));
        kc.RegisterValueChangedCallback(e => Session.kColumna = Mathf.Clamp(e.newValue, 0.05f, 1f));
        km.RegisterValueChangedCallback(e => Session.kMuro = Mathf.Clamp(e.newValue, 0.05f, 1f));
        var kRow = Row();
        kRow.Add(Btn("Vigente", () => { kv.value = 0.35f; kc.value = 0.70f; km.value = 1f; }, "wide"));
        kRow.Add(Btn("ACI fisurada", () => { kv.value = 0.35f; kc.value = 0.70f; km.value = 0.35f; }, "wide"));
        kRow.Add(Btn("Sección bruta", () => { kv.value = 1f; kc.value = 1f; km.value = 1f; }, "wide"));
        c.Add(kRow);
        c.Add(Text("Vigente: vigas 0,35 y columnas 0,70 (ACI 318-19 §6.6.3.1.1); muros 1,0 con deformación por corte, calibrado con el modelo ETABS de referencia. «ACI fisurada» usa muros 0,35. Acero sin reducción.", "hint"));

        c.Add(Title("COMBINACIONES  ·  λG  λQ  λEX  λEY"));
        var comboList = new VisualElement();
        c.Add(comboList);
        System.Action buildCombos = null;
        buildCombos = () =>
        {
            comboList.Clear();
            foreach (AnalysisSession.Combo combo in Session.combos)
            {
                AnalysisSession.Combo cb = combo;
                var row = Row();
                row.style.marginBottom = 3;
                var name = Input(new TextField { value = cb.name });
                name.AddToClassList("search");
                name.style.width = 48;
                name.RegisterCallback<FocusInEvent>(_ => TextFocused = true);
                name.RegisterCallback<FocusOutEvent>(_ => TextFocused = false);
                name.RegisterValueChangedCallback(e => cb.name = e.newValue.Trim());
                row.Add(name);
                row.Add(Factor(cb.G, v => cb.G = v));
                row.Add(Factor(cb.Q, v => cb.Q = v));
                row.Add(Factor(cb.EX, v => cb.EX = v));
                row.Add(Factor(cb.EY, v => cb.EY = v));
                row.Add(Btn("✕", () => { Session.combos.Remove(cb); buildCombos(); }, "small"));
                comboList.Add(row);
            }
        };
        buildCombos();
        c.Add(Btn("+ Agregar combinación", () =>
        {
            Session.combos.Add(new AnalysisSession.Combo { name = "C" + (Session.combos.Count + 1), G = 1f, Q = 0.5f });
            buildCombos();
        }, "wide"));

        c.Add(Title("¿QUÉ REQUIERE REANÁLISIS?"));
        c.Add(Text("Instantáneo, sin reanálisis: capas, combinación activa, superposición en vivo (λ), carga móvil, carga en elemento y persona SQ4. Combinan casos ya calculados del modelo lineal.", "hint"));
        c.Add(Text("Requiere reanálisis con OpenSees: intensidad de carga (q_G, Q, sismo), material (f'c), rigidez, combinaciones, sección, armadura, apoyos, área tributaria y quitar elementos.", "hint"));

        c.Add(Title("CAMBIOS PENDIENTES"));
        var secs = Text("", "hint");
        c.Add(secs);

        c.Add(Title("REANÁLISIS CON OPENSEES"));
        var py = Text(string.IsNullOrEmpty(PythonJob.Diagnostico) ? "Toca «Revisar Python» para ver qué Python y qué motor de cálculo se usarán." : PythonJob.Diagnostico, "hint");
        c.Add(py);
        var pyRow = Row();
        pyRow.Add(Btn("Revisar Python", () => py.text = PythonJob.RevisarPython(), "wide"));
        c.Add(pyRow);
        c.Add(Check("Si falta OpenSees, calcular con el solver de verificación", () => PythonJob.UsarReplica, v => { PythonJob.UsarReplica = v; py.text = PythonJob.RevisarPython(); }));
        c.Add(Text("Para usar OpenSees ejecuta instalar_dependencias.bat (carpeta del repositorio): instala openseespy en Python 3.12. El solver de verificación es una réplica validada de OpenSees; sus resultados quedan marcados como tales.", "hint"));
        var run = Btn("Reanalizar el modelo completo", () =>
        {
            if (Session.StartReanalysis()) viewer.Status = "Reanálisis en curso..."; else viewer.Status = Session.Message;
        }, "wide");
        run.style.height = 30;
        c.Add(run);
        var reset = Btn("Restaurar valores del modelo cargado", () => { Session.LoadFrom(viewer.Data); Rebuild(); }, "wide");
        c.Add(reset);
        var progress = Text("", "hint");
        c.Add(progress);
        syncers.Add(() =>
        {
            bool running = Session.job.Running;
            run.SetEnabled(PythonJob.Available && !running);
            reset.SetEnabled(!running);
            run.text = running ? $"Analizando...  {Session.job.Elapsed:0} s" : "Reanalizar el modelo completo";
            progress.text = running ? (Session.job.LastLine ?? "") : Session.Message;
            var lines = new List<string>();
            foreach (var x in Session.sections.Values) lines.Add($"{x.tag}: {x.before} → {x.sectionId}");
            foreach (var kv in Session.armSec) lines.Add($"Armadura {kv.Key}: {kv.Value.Describe()}");
            foreach (var kv in Session.armElem) lines.Add($"Armadura {kv.Key}: {kv.Value.Describe()}");
            foreach (var ap in Session.apoyos) lines.Add($"Apoyo nodo {ap.Key}: {NombreApoyo(ap.Value)}");
            foreach (var tr in Session.tributarias) lines.Add($"Área tributaria elemento {tr.Key}: {tr.Value:0.00} m²");
            if (d != null && d.resumenAnalisis != null && d.resumenAnalisis.fc_MPa > 0f && Mathf.Abs(Session.fcMPa - d.resumenAnalisis.fc_MPa) > 0.01f)
                lines.Add($"Material: f'c {d.resumenAnalisis.fc_MPa:0.#} → {Session.fcMPa:0.#} MPa");
            secs.text = lines.Count == 0 ? "Sin cambios (se agregan en la pestaña MODIFICAR)." : string.Join("\n", lines);
        });
        if (!PythonJob.Available) c.Add(Text("Requiere Python + OpenSees en este equipo (carpeta Proyecto1/scripts).", "hint"));

        // verificacion del analisis cargado
        AnalysisSummary r = d?.resumenAnalisis;
        c.Add(Title("VERIFICACIÓN DEL ANÁLISIS CARGADO"));
        if (r == null || r.G_aplicada_kN == 0f)
        {
            c.Add(Text("El JSON cargado no trae resumen (se genera al reanalizar o al exportar de nuevo).", "hint"));
        }
        else
        {
            c.Add(KeyValue("q_G · Q · C eq. X/Y", $"{r.q_G_kN_m2:0.00} kN/m² · {r.Q_kN_m2:0.00} kN/m² · {r.coeficienteSismico:0.###} / {(r.sismo != null ? r.sismo.C_equivalente_Y : r.coeficienteSismico):0.###}"));
            c.Add(KeyValue("Rigidez V · C · M", $"{r.rigidezViga:0.##} · {r.rigidezColumna:0.##} · {r.rigidezMuro:0.##} × Ig"));
            c.Add(KeyValue("G aplicada / ΣRz", $"{r.G_aplicada_kN:0} / {r.G_reaccion_kN:0} kN"));
            c.Add(KeyValue("Q aplicada / ΣRz", $"{r.Q_aplicada_kN:0} / {r.Q_reaccion_kN:0} kN"));
            c.Add(KeyValue("Corte basal EX · EY", $"{r.corteBasal_EX_kN:0} · {r.corteBasal_EY_kN:0} kN"));
            SismoSummary s = r.sismo;
            if (s != null && s.metodo == "NCh433")
            {
                c.Add(KeyValue("Sismo", $"NCh433 · zona {s.zona} · suelo {s.suelo} · R {s.R:0.#} · I {s.I:0.##} · {s.hipotesis}"));
                if (s.edificios != null)
                    foreach (SismoEdificio b in s.edificios)
                        c.Add(KeyValue(b.edificio.Replace("edificio_", "Edificio "),
                            $"T* {b.T_X_s:0.000} / {b.T_Y_s:0.000} s · C {b.C_X:0.000} / {b.C_Y:0.000} · Q0 {b.Q0_X_kN:0} / {b.Q0_Y_kN:0} kN (X / Y)"));
            }
            else if (s != null) c.Add(KeyValue("Sismo", $"C fijo {s.C_fijo:0.###} · {s.hipotesis}"));
            if (r.armadura != null && r.armadura.vigas > 0)
            {
                c.Add(KeyValue("Vigas DCR > 1", $"{r.armadura.vigas_DCR_mayor_1} de {r.armadura.vigas} (máx {r.armadura.DCR_max_viga:0.00} en {r.armadura.peorViga})"));
                c.Add(KeyValue("Columnas DCR > 1", $"{r.armadura.columnas_DCR_mayor_1} de {r.armadura.columnas} (máx {r.armadura.DCR_max_columna:0.00} en {r.armadura.peorColumna})"));
            }
            if (r.uMax != null)
                foreach (CaseMax u in r.uMax) c.Add(KeyValue("|u| máx " + u.caso, $"{u.u_mm:0.00} mm"));
        }

        if (Session.ScenarioLoaded)
        {
            c.Add(Title("ESCENARIO SIN GUARDAR"));
            c.Add(Text("Se está viendo el resultado del reanálisis. Guardarlo reemplaza el modelo vigente del proyecto " +
                       "(Assets/Resources/estructura_p1l4_unity.json, data/combinaciones.json y data/parametros_analisis.json).", "hint"));
            var keep = Row();
            keep.Add(Btn("Guardar como modelo vigente", () => { if (Session.SaveAsCurrent(viewer)) Rebuild(); }, "wide"));
            keep.Add(Btn("Descartar", () => Session.DiscardScenario(viewer), "wide"));
            c.Add(keep);
        }
    }

    private FloatField Factor(float value, System.Action<float> set)
    {
        var f = Input(new FloatField { value = value, formatString = "0.###" });
        f.AddToClassList("factor");
        f.style.width = 54; f.style.minWidth = 54; f.style.flexShrink = 0;
        f.RegisterCallback<AttachToPanelEvent>(_ =>
        {
            var input = f.Q(className: "unity-base-text-field__input");
            if (input != null) { input.style.width = 52; input.style.minWidth = 0; input.style.flexGrow = 1; }
        });
        f.RegisterValueChangedCallback(e => set(e.newValue));
        return f;
    }

    // ------------------------------------------------------------------
    // Propiedades del elemento seleccionado
    // ------------------------------------------------------------------
    private void BuildProps()
    {
        propsPanel = Panel("props");
        var head = new VisualElement();
        head.AddToClassList("props-head");
        propsTitle = Text("", "props-title");
        head.Add(propsTitle);
        head.Add(Btn("✕", () => picker?.ClearSelection(), "small"));
        propsPanel.Add(head);
        var scroll = new ScrollView(ScrollViewMode.Vertical);
        scroll.AddToClassList("props-scroll");
        propsBody = new VisualElement();
        propsBody.AddToClassList("props-body");
        scroll.Add(propsBody);
        propsPanel.Add(scroll);
        propsPanel.style.display = DisplayStyle.None;
        root.Add(propsPanel);
    }

    private void SyncProps()
    {
        string text = picker != null ? picker.InfoText : null;
        propsPanel.style.display = text == null ? DisplayStyle.None : DisplayStyle.Flex;
        if (!PanelMovible.Movido(propsPanel)) propsPanel.style.width = UiTheme.InfoWidth;   // respeta el tamano elegido por el usuario
        if (text == null || text == propsText) return;
        propsText = text;
        propsBody.Clear();

        VisualElement target = propsBody;
        foreach (string raw in text.Split('\n'))
        {
            string line = raw.Trim();
            if (line.Length == 0) continue;
            if (line.StartsWith("==="))
            {
                propsTitle.text = line.Trim('=', ' ');
                continue;
            }
            if (line.StartsWith("---") && line.EndsWith("---"))
            {
                string header = line.Trim('-', ' ');
                var fold = new Foldout { text = header.ToUpperInvariant(), value = !header.StartsWith("Trazabilidad") && !header.StartsWith("Ejes") };
                fold.AddToClassList("fold");
                propsBody.Add(fold);
                target = fold;
                continue;
            }
            target.Add(PropLine(line));
        }
    }

    /// "Clave: valor" o "Clave = valor" (una sola vez) como fila; si no, texto.
    private static VisualElement PropLine(string line)
    {
        int colon = line.IndexOf(':');
        int eq = line.IndexOf(" = ");
        bool oneColon = colon > 0 && colon < 30 && line.IndexOf(':', colon + 1) < 0 && !line.Contains("|");
        bool oneEq = eq > 0 && eq < 12 && line.IndexOf(" = ", eq + 3) < 0 && !line.Contains("|");
        if (oneColon) return KeyValue(line.Substring(0, colon).Trim(), line.Substring(colon + 1).Trim());
        if (oneEq) return KeyValue(line.Substring(0, eq).Trim(), line.Substring(eq + 3).Trim());
        return Text(line, "line");
    }

    // ------------------------------------------------------------------
    private void Update()
    {
        // el reanalisis se vigila siempre (tambien si quedo la interfaz antigua)
        if (Session.job.Running && viewer != null) Session.Poll(viewer);   // al terminar recarga el modelo (Rebuild)
        if (!Active) return;
        UpdateHostRect();
        if (Time.unscaledTime < nextSync) return;
        nextSync = Time.unscaledTime + 0.2f;
        SyncAll();
    }

    /// Aviso en pantalla si alguna parte de la interfaz no se pudo crear.
    private void OnGUI()
    {
        UiTheme.ApplyScale();
        AreaResumen = Rect.zero;
        if (resumenVisible && resumen.Count > 0) DibujarResumen();
        if (string.IsNullOrEmpty(Falla)) return;
        float w = Mathf.Min(UiTheme.ScreenW - 24f, 820f);
        Rect r = new Rect(12f, UiTheme.ScreenH - 58f, w, 46f);
        GUI.color = new Color(0.50f, 0.10f, 0.20f, 0.95f);
        GUI.DrawTexture(r, Texture2D.whiteTexture);
        GUI.color = Color.white;
        var estilo = new GUIStyle(UiTheme.Label) { wordWrap = true, fontSize = 12 };
        string texto = (Active ? "Aviso de la interfaz: " : "No se pudo crear la interfaz completa: ") + Falla + "  · Copia este mensaje (y la Consola) para revisarlo.";
        GUI.Label(new Rect(r.x + 10f, r.y + 4f, r.width - 110f, r.height - 8f), texto, estilo);
        if (GUI.Button(new Rect(r.xMax - 92f, r.y + 12f, 82f, 22f), "Ocultar")) Falla = null;
    }

    private void SyncAll()
    {
        if (picker == null) picker = FindAnyObjectByType<ElementPicker>();
        diagrams = viewer.Diagrams;
        foreach (var s in syncers) s();
        SyncProps();
    }

    private void UpdateHostRect()
    {
        if (HostVisible(ActiveTab) && hosts.TryGetValue(ActiveTab, out VisualElement host) && host.panel != null)
        {
            Rect r = host.worldBound;   // unidades del panel = unidades GUI (ver Build)
            if (!float.IsNaN(r.width) && r.width > 1f && r.height > 1f)
            {
                HostRect = new Rect(r.x, r.y + 4f, r.width, r.height - 4f);
                return;
            }
        }
        HostRect = new Rect(-10000f, -10000f, 0f, 0f);   // paneles IMGUI fuera de pantalla
    }

    /// true si la posicion (pixeles, origen abajo-izquierda) cae sobre la interfaz.
    public static bool IsPointerOverUI(Vector2 screenPos)
    {
        if (instance == null || instance.root?.panel == null) return false;
        IPanel panel = instance.root.panel;
        Vector2 p = RuntimePanelUtils.ScreenToPanel(panel, new Vector2(screenPos.x, Screen.height - screenPos.y));
        if (PMPanel.AreaVisible.Contains(p)) return true;   // panel P-M (IMGUI), que tambien se puede mover
        if (DiagramController.AreaTabla.Contains(p)) return true;   // tabla de valores del diagrama (IMGUI)
        if (PanelCapacidadViga.AreaVisible.Contains(p) || AreaResumen.Contains(p)) return true;   // capacidad de viga y resumen
        VisualElement picked = panel.Pick(p);
        return picked != null;
    }

    // ------------------------------------------------------------------
    // Fabricas de elementos
    // ------------------------------------------------------------------
    private static VisualElement Panel(string cls)
    {
        var v = new VisualElement();
        v.AddToClassList("panel");
        v.AddToClassList(cls);
        return v;
    }

    private static VisualElement Row()
    {
        var v = new VisualElement();
        v.AddToClassList("row");
        return v;
    }

    private static VisualElement Seg()
    {
        var v = new VisualElement();
        v.AddToClassList("seg");
        return v;
    }

    private static void FinishSeg(VisualElement seg)
    {
        if (seg.childCount == 0) return;
        seg[0].AddToClassList("seg-first");
        seg[seg.childCount - 1].AddToClassList("seg-last");
    }

    private static VisualElement Spacer()
    {
        var v = new VisualElement();
        v.AddToClassList("spacer");
        return v;
    }

    private static VisualElement Gap()
    {
        var v = new VisualElement();
        v.AddToClassList("seg-sep");
        return v;
    }

    private static Label Text(string text, params string[] classes)
    {
        var l = new Label(text);
        foreach (string c in classes) l.AddToClassList(c);
        return l;
    }

    private static Label Title(string text, bool first = false)
    {
        Label l = Text(text, "section-title");
        if (first) l.AddToClassList("first");
        return l;
    }

    private static Button Btn(string text, System.Action onClick, params string[] classes)
    {
        var b = new Button(onClick) { text = text };
        b.AddToClassList("btn");
        foreach (string c in classes) b.AddToClassList(c);
        return b;
    }

    private Toggle Check(string label, System.Func<bool> get, System.Action<bool> set)
    {
        var t = new Toggle(label) { value = get() };
        t.AddToClassList("chk");
        t.RegisterValueChangedCallback(e => set(e.newValue));
        syncers.Add(() => { if (t.value != get()) t.SetValueWithoutNotify(get()); });
        return t;
    }

    /// Texto visible en los campos de entrada (color, tamano y alto fijados en linea).
    private static T Input<T>(T field) where T : VisualElement
    {
        field.RegisterCallback<AttachToPanelEvent>(_ =>
        {
            var input = field.Q(className: "unity-base-text-field__input");
            if (input != null)
            {
                input.style.backgroundColor = Paleta.Entrada;
                input.style.paddingLeft = 4; input.style.paddingRight = 4;
                input.style.paddingTop = 0; input.style.paddingBottom = 0;
                input.style.minHeight = 20;
            }
            var text = field.Q<TextElement>(className: "unity-text-element--inner-input-field-component");
            if (text != null)
            {
                text.style.color = Paleta.Texto;
                text.style.fontSize = 12;
                text.style.unityTextAlign = TextAnchor.MiddleLeft;
                text.style.flexGrow = 1;
            }
        });
        return field;
    }

    private static VisualElement KeyValue(string key, string value)
    {
        var row = new VisualElement();
        row.AddToClassList("kv");
        row.Add(Text(key, "k"));
        row.Add(Text(value, "v"));
        return row;
    }

    private static VisualElement Legend(Color color, string text)
    {
        var row = new VisualElement();
        row.AddToClassList("legend-row");
        var sw = new VisualElement();
        sw.AddToClassList("swatch");
        sw.style.backgroundColor = color;
        row.Add(sw);
        row.Add(Text(text, "legend-text"));
        return row;
    }
}
