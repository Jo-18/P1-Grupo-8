using System.Collections.Generic;
using UnityEngine;

[ExecuteAlways]
public partial class StructureViewer : MonoBehaviour
{
    [Header("Datos exportados desde OpenSeesPy")]
    public TextAsset structureJson;

    [Header("Apariencia")]
    public float elementRadius = 0.06f;
    public float wallScale = 1.6f;
    public Material beamMaterial;
    public Material columnMaterial;
    public Material supportMaterial;

    private Material defaultBeamMaterial;
    private Material defaultColumnMaterial;
    private Material defaultSupportMaterial;
    private Material defaultWallMaterial;
    private Material defaultDiaphragmMaterial;
    private Material defaultBraceMaterial;

    private readonly Dictionary<int, Vector3> nodes = new Dictionary<int, Vector3>();
    private readonly List<ElementSelectable> selectables = new List<ElementSelectable>();
    private DiagramController diagramController;
    private PMPanel pmPanel;
    private StructureData loadedData;

    // Grupos de objetos para los toggles
    private readonly List<GameObject> columnObjects = new List<GameObject>();
    private readonly List<GameObject> beamObjects = new List<GameObject>();
    private readonly List<GameObject> wallObjects = new List<GameObject>();
    private readonly List<GameObject> supportObjects = new List<GameObject>();
    private readonly List<GameObject> diaphragmObjects = new List<GameObject>();
    private readonly List<GameObject> loadObjects = new List<GameObject>();
    private readonly List<GameObject> nodeMarkerObjects = new List<GameObject>();
    private readonly List<GameObject> idLabelObjects = new List<GameObject>();
    private readonly List<GameObject> localAxisObjects = new List<GameObject>();
    private readonly Dictionary<GameObject, string> objectFloor = new Dictionary<GameObject, string>();
    private readonly Dictionary<string, TributaryFloorData> tributaryFloors =
        new Dictionary<string, TributaryFloorData>();

    // Estados de los toggles
    private bool showColumns = true;
    private bool showBeams = true;
    private bool showWalls = true;
    private bool showSupports = true;
    private bool showDiaphragms = true;
    private bool showNodeMarkers = false;
    private bool showIds = false;
    private bool showLocalAxes = false;
    private bool showLoads = false;
    private bool showTributarySummary = false;
    private bool showUtilization = false;
    private readonly Dictionary<GameObject, Color> originalUtilColors = new Dictionary<GameObject, Color>();

    // Superposicion en vivo (Bloque C): sliders de casos base G/Q/EX/EY
    private bool showSuperposition = false;
    private float superpositionG = 1f;
    private float superpositionQ = 1f;
    private float superpositionEX = 1f;
    private float superpositionEY = 1f;

    // Combinaciones de carga
    private string[] comboOptions = new string[0];
    private int comboIndex = 0;

    // UI base FASE 1
    private readonly string[] resultOptions = new string[] { "None", "Axial", "Corte", "Momento", "Deformada" };
    private int resultIndex = 0;
    private string[] floorOptions = new string[] { "Todos" };
    private int floorIndex = 0;
    private string statusMessage = "Click sobre un elemento para ver informacion y P-M.";
    private Vector2 leftScroll;

    private void Start()
    {
        CreateStructure();
    }

    // ------------------------------------------------------------------
    // API para la interfaz (ViewerUI, UI Toolkit). Con ViewerUI activa el
    // viewer no dibuja su barra superior ni su consola IMGUI.
    // ------------------------------------------------------------------
    public DiagramController Diagrams => diagramController;
    public string[] ComboNames => comboOptions;
    public string[] ResultNames => resultOptions;
    public string[] FloorNames => floorOptions;
    public int FloorIndex { get => floorIndex; set => floorIndex = Mathf.Clamp(value, 0, Mathf.Max(0, floorOptions.Length - 1)); }
    public string CurrentResult => resultOptions[Mathf.Clamp(resultIndex, 0, resultOptions.Length - 1)];
    public string Status { get => statusMessage; set => statusMessage = value; }
    public bool ShowColumnsLayer { get => showColumns; set => showColumns = value; }
    public bool ShowBeamsLayer { get => showBeams; set => showBeams = value; }
    public bool ShowWallsLayer { get => showWalls; set => showWalls = value; }
    public bool ShowSupportsLayer { get => showSupports; set => showSupports = value; }
    public bool ShowSlabsLayer { get => showDiaphragms; set => showDiaphragms = value; }
    public bool ShowNodesLayer { get => showNodeMarkers; set => showNodeMarkers = value; }
    public bool ShowIdsLayer { get => showIds; set => showIds = value; }
    public bool ShowLocalAxesLayer { get => showLocalAxes; set => showLocalAxes = value; }
    public bool ShowLoadsLayer { get => showLoads; set => showLoads = value; }
    public bool UtilizationColors => showUtilization;
    public IReadOnlyDictionary<string, TributaryFloorData> TributaryFloors => tributaryFloors;
    public StructureData Data => loadedData;
    public bool SuperpositionActive => showSuperposition;
    public float[] SuperpositionValues => new[] { superpositionG, superpositionQ, superpositionEX, superpositionEY };

    /// Activa un caso base (G, Q, EX, EY) o una combinacion (C1...).
    public void SetCase(string name)
    {
        int index = System.Array.IndexOf(comboOptions, name);
        if (index >= 0) { ApplyCombo(index); }
        else
        {
            UnityData.ActiveCombo = name;
            if (diagramController != null && Application.isPlaying) diagramController.Refresh();
            var picker = FindAnyObjectByType<ElementPicker>();
            if (pmPanel != null && picker != null && picker.Selected != null) pmPanel.ShowPMForElement(picker.Selected);
            if (showUtilization) ApplyUtilizationColors();
        }
        statusMessage = "Caso activo: " + UnityData.GetComboLabel(UnityData.ActiveCombo);
    }

    public void ShowAllLayers()
    {
        showColumns = showBeams = showWalls = showSupports = showDiaphragms = showGrid = true;
        showNodeMarkers = showIds = showLocalAxes = showLoads = showDiaphragmMarks = false;
        if (showUtilization) { showUtilization = false; RestoreUtilizationColors(); }
        floorIndex = 0;
        statusMessage = "Vista restablecida.";
    }

    public void StructureOnly()
    {
        showColumns = showBeams = showWalls = true;
        showSupports = showDiaphragms = showNodeMarkers = showIds = showLocalAxes = showLoads = false;
        showGrid = showDiaphragmMarks = false;
        if (showUtilization) { showUtilization = false; RestoreUtilizationColors(); }
        statusMessage = "Capas auxiliares ocultas.";
    }

    public void Search(string key) => FindAndSelect(key);

    // ---- recarga del modelo con los resultados de un reanalisis ----
    private string overrideJson;
    public string LoadedSource { get; private set; } = "Resources/estructura_p1l4_unity.json";
    public event System.Action ModelReloaded;

    /// Reconstruye toda la escena con un JSON nuevo (escenario de reanalisis o el original).
    public void ReloadFromJson(string json, string source)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            Debug.LogError("[StructureViewer] ReloadFromJson rechazado: JSON nulo o vacio. Fuente: " + source);
            return;
        }
        ApplyReload(json, source);
    }

    // json == null deja el modelo vigente de Resources (sin override).
    private void ApplyReload(string json, string source)
    {
        var picker = FindAnyObjectByType<ElementPicker>();
        if (picker != null) picker.ClearSelection();
        var pm = FindAnyObjectByType<PMPanel>();
        if (pm != null) pm.Hide();
        UnityData.ResetRemovalState();
        overrideJson = json;
        LoadedSource = source;
        string result = CurrentResult;
        CreateStructure();
        SetResult(result);
        statusMessage = "Modelo recargado: " + source;
        ModelReloaded?.Invoke();
    }

    /// Ruta en disco del JSON del proyecto (Assets/Resources), o null si no se encuentra.
    public static string ProjectJsonPath
    {
        get
        {
            string root = PythonJob.ProjectRoot;
            if (root == null) return null;
            string path = System.IO.Path.Combine(root, "edificio_G8", "Assets", "Resources", "estructura_p1l4_unity.json");
            return System.IO.File.Exists(path) ? path : null;
        }
    }

    /// Vuelve al modelo vigente del proyecto (se lee del disco: puede haber sido guardado recien).
    public void ReloadOriginal()
    {
        string path = ProjectJsonPath;
        structureJson = null;
        string json = path != null ? System.IO.File.ReadAllText(path) : null;
        ApplyReload(string.IsNullOrWhiteSpace(json) ? null : json, "Resources/estructura_p1l4_unity.json");
    }
    public void CameraPreset(string preset) => SetCameraPreset(preset);

    public void SetSuperposition(bool active, float g, float q, float ex, float ey)
    {
        superpositionG = g; superpositionQ = q; superpositionEX = ex; superpositionEY = ey;
        if (active)
        {
            showSuperposition = true;
            ApplySyntheticCombo();
        }
        else if (showSuperposition)
        {
            showSuperposition = false;
            if (UnityData.ActiveCombo == UnityData.SuperpositionComboName) RestoreBaseComboColors();
        }
    }

    private void OnEnable()
    {
        CreateStructure();
    }

    private void CreateStructure()
    {
        // Consola de diagnostico en pantalla solo en builds de desarrollo del celular
        if (Application.isPlaying && Debug.isDebugBuild && !Application.isEditor && GetComponent<DebugOverlay>() == null)
        {
            gameObject.AddComponent<DebugOverlay>();
        }
        CreateDefaultMaterials();

        bool hasOverride = !string.IsNullOrWhiteSpace(overrideJson);
        if (!hasOverride) overrideJson = null;

        if (structureJson == null && !hasOverride)
        {
            structureJson = Resources.Load<TextAsset>("estructura_p1l4_unity");
            if (structureJson == null)
            {
                Debug.LogError("Asigna estructura_p1l4_unity.json a Assets/Resources.");
                return;
            }
        }

        string jsonSource = hasOverride ? LoadedSource : "Resources/estructura_p1l4_unity.json (TextAsset '" + structureJson.name + "')";
        string jsonText = hasOverride ? overrideJson : structureJson.text;
        if (string.IsNullOrWhiteSpace(jsonText))
        {
            Debug.LogError("[StructureViewer] El JSON de la estructura esta vacio. Fuente: " + jsonSource);
            return;
        }

        StructureData parsed;
        try
        {
            parsed = JsonUtility.FromJson<StructureData>(jsonText);
        }
        catch (System.ArgumentException e)
        {
            Debug.LogError("[StructureViewer] JSON de la estructura invalido. Fuente: " + jsonSource + ". " + e.Message);
            return;
        }
        if (parsed == null)
        {
            Debug.LogError("[StructureViewer] No se pudo deserializar el JSON de la estructura (resultado null). Fuente: " + jsonSource);
            return;
        }

        loadedData = parsed;
        UnityData.LoadData(loadedData);

        if (loadedData.tributaryList != null)
        {
            foreach (TributaryFloorData td in loadedData.tributaryList)
            {
                tributaryFloors[td.piso] = td;
            }
        }

        ClearStructureChildren();
        nodes.Clear();
        selectables.Clear();
        columnObjects.Clear();
        beamObjects.Clear();
        wallObjects.Clear();
        supportObjects.Clear();
        diaphragmObjects.Clear();
        nodeMarkerObjects.Clear();
        idLabelObjects.Clear();
        localAxisObjects.Clear();
        loadObjects.Clear();
        ClearOverlayState();
        objectFloor.Clear();

        CreateNodes(loadedData);
        CreateColumnAndBeamElements(loadedData);
        CreateWalls(loadedData);
        CreateDiaphragms(loadedData);
        CreateSupports(loadedData);
        CreatePointLoads(loadedData);
        CreateGridAxes(loadedData);
        CreateDiaphragmMarks(loadedData);
        CreateGlobalAxes();
        CreateDiagramController();
        CreatePMPanel();
        CreateMovingLoadPanel();
        if (Application.isPlaying && GetComponent<PersonaSQ4>() == null) gameObject.AddComponent<PersonaSQ4>();   // SQ4: persona sobre la losa
        if (Application.isPlaying && GetComponent<PanelCapacidadViga>() == null) gameObject.AddComponent<PanelCapacidadViga>();   // capacidad de vigas
        CreateGroundGrid();
        if (Application.isPlaying && GetComponent<ViewerUI>() == null) gameObject.AddComponent<ViewerUI>();

        BuildComboOptions();
        BuildFloorOptions();

        if (comboOptions.Length > 0)
        {
            ApplyCombo(0);
        }

        MarkGeneratedDontSave();
        RefreshVisibility();

        Debug.Log($"[StructureViewer] Estructura lista: {selectables.Count} elementos interactivos, {comboOptions.Length} combinaciones.");
    }

    private void BuildComboOptions()
    {
        if (loadedData.p1l4 == null || loadedData.p1l4.combinations == null || loadedData.p1l4.combinations.Length == 0)
        {
            comboOptions = new string[] { "G (sin combo)" };
            comboIndex = 0;
            return;
        }

        var names = new List<string>();
        foreach (ComboInfo c in loadedData.p1l4.combinations)
        {
            if (c != null && !string.IsNullOrEmpty(c.name))
            {
                names.Add(c.name);
            }
        }
        comboOptions = names.ToArray();
        comboIndex = Mathf.Clamp(comboIndex, 0, Mathf.Max(0, comboOptions.Length - 1));
    }

    private void ApplyCombo(int index)
    {
        if (comboOptions == null || comboOptions.Length == 0)
        {
            UnityData.ActiveCombo = null;
            return;
        }

        string name = comboOptions[Mathf.Clamp(index, 0, comboOptions.Length - 1)];
        if (name == "G (sin combo)")
        {
            name = "";
        }
        UnityData.ActiveCombo = name;
        comboIndex = index;

        if (diagramController != null && Application.isPlaying)
        {
            diagramController.Refresh();
        }

        if (pmPanel != null)
        {
            var picker = FindObjectOfType<ElementPicker>();
            if (picker != null && picker.Selected != null)
            {
                pmPanel.ShowPMForElement(picker.Selected);
            }
        }

        if (showUtilization)
        {
            ApplyUtilizationColors();
        }
    }

    private void MarkGeneratedDontSave()
    {
        for (int i = 0; i < transform.childCount; i++)
        {
            Transform child = transform.GetChild(i);
            if (child != null)
            {
                child.gameObject.hideFlags = HideFlags.DontSave;
            }
        }
    }

    private void ClearStructureChildren()
    {
        for (int i = transform.childCount - 1; i >= 0; i--)
        {
            GameObject child = transform.GetChild(i).gameObject;
            if (Application.isPlaying)
            {
                Destroy(child);
            }
            else
            {
                DestroyImmediate(child);
            }
        }
    }

    private void CreateNodes(StructureData data)
    {
        foreach (NodeData node in data.nodes)
        {
            nodes[node.id] = ToUnity(node);
        }
    }

    private void CreateColumnAndBeamElements(StructureData data)
    {
        foreach (ElementData element in data.elements)
        {
            if (!nodes.ContainsKey(element.nodeI) || !nodes.ContainsKey(element.nodeJ))
            {
                continue;
            }
            // muros en el analisis (columna ancha + brazos rigidos): el muro ya se
            // dibuja como pano (CreateWalls) y sus resultados van en su demanda P-M
            if (UnityData.IsAnalysisOnly(element)) continue;

            Vector3 start = nodes[element.nodeI];
            Vector3 end = nodes[element.nodeJ];
            Vector3 midpoint = (start + end) * 0.5f;
            Vector3 direction = end - start;

            bool isColumn = element.type == "columna";
            bool isArriostre = element.type == "arriostre";
            float sectionWidth = GetSectionWidth(element, isColumn);
            float sectionHeight = GetSectionHeight(element, isColumn);

            // Factor SOLO visual (no cambia width_m/height_m del JSON, por lo que
            // no repercute en los cálculos): vigas claramente más esbeltas y
            // columnas claramente más robustas.
            bool isBeam = !isColumn && !isArriostre;
            float visualFactorWidth = isColumn ? 1.30f : (isBeam ? 0.60f : 1.0f);
            float visualFactorDepth = isColumn ? 1.30f : (isBeam ? 0.70f : 1.0f);

            GameObject member = GameObject.CreatePrimitive(PrimitiveType.Cube);
            member.name = $"Elemento_{element.id}_{element.type}_{GetSectionName(element)}";
            member.transform.SetParent(transform);
            member.transform.position = midpoint;
            member.transform.rotation = GetMemberRotation(direction, isColumn);
            member.transform.localScale = new Vector3(sectionWidth * visualFactorWidth, direction.magnitude, sectionHeight * visualFactorDepth);

            Renderer renderer = member.GetComponent<Renderer>();
            renderer.material = isArriostre ? BraceMaterial() : isColumn ? ColumnMaterial() : BeamMaterial();
            (isColumn ? columnObjects : beamObjects).Add(member);
            RegisterFloor(member, element.piso);

            ElementSelectable selectable = member.AddComponent<ElementSelectable>();
            selectable.data = element;
            selectable.startPoint = start;
            selectable.endPoint = end;
            selectable.nodeIId = element.nodeI;
            selectable.nodeJId = element.nodeJ;
            selectable.nodeISupport = FindSupportForNode(data, element.nodeI);
            selectable.nodeJSupport = FindSupportForNode(data, element.nodeJ);

            if (isColumn)
            {
                string secName = GetSectionName(element);
                selectable.pmSectionId = !string.IsNullOrEmpty(element.pmCurveId) && UnityData.GetPMCurve(element.pmCurveId) != null
                    ? element.pmCurveId : ResolvePMSection(secName);
            }

            selectables.Add(selectable);
        }
    }

    private SupportData FindSupportForNode(StructureData data, int nodeId)
    {
        if (data.supports == null)
        {
            return null;
        }
        foreach (SupportData s in data.supports)
        {
            if (s.node == nodeId)
            {
                return s;
            }
        }
        return null;
    }

    private string GetSectionName(ElementData element)
    {
        if (!string.IsNullOrEmpty(element.sectionId)) return element.sectionId;
        if (!string.IsNullOrEmpty(element.seccion)) return element.seccion;
        return element.type == "columna" ? "COL70/70" : "V60/80";
    }

    private float GetSectionWidth(ElementData element, bool isColumn)
    {
        if (element.width_m > 0.001f) return element.width_m;

        string sectionName = GetSectionName(element);
        if (sectionName == "V30/80") return 0.30f;
        if (sectionName == "V40/80") return 0.40f;
        if (sectionName == "V60/80") return 0.60f;
        if (sectionName == "V30/45") return 0.30f;
        return isColumn ? 0.70f : 0.60f;
    }

    private float GetSectionHeight(ElementData element, bool isColumn)
    {
        if (element.height_m > 0.001f) return element.height_m;

        string sectionName = GetSectionName(element);
        if (sectionName == "V30/45") return 0.45f;
        if (sectionName == "V30/80" || sectionName == "V40/80" || sectionName == "V60/80") return 0.80f;
        return isColumn ? 0.70f : 0.80f;
    }

    private Quaternion GetMemberRotation(Vector3 direction, bool isColumn)
    {
        Vector3 axis = direction.normalized;
        if (isColumn || Mathf.Abs(Vector3.Dot(axis, Vector3.up)) > 0.95f)
        {
            return Quaternion.FromToRotation(Vector3.up, axis);
        }

        Vector3 localX = Vector3.Cross(axis, Vector3.up).normalized;
        Vector3 localZ = Vector3.Cross(localX, axis).normalized;
        return Quaternion.LookRotation(localZ, axis);
    }

    private void CreateWalls(StructureData data)
    {
        if (data.walls == null)
        {
            return;
        }

        foreach (WallData wall in data.walls)
        {
            if (!nodes.ContainsKey(wall.nodeI) || !nodes.ContainsKey(wall.nodeJ))
            {
                continue;
            }

            Vector3 start = nodes[wall.nodeI];
            Vector3 end = nodes[wall.nodeJ];
            Vector3 baseMidpoint = (start + end) * 0.5f;
            Vector3 direction = end - start;
            float wallLength = Mathf.Max(direction.magnitude, wall.longitud, 0.01f);
            float wallHeight = EstimateWallHeight(start, end);
            Vector3 lengthAxis = direction.sqrMagnitude > 1e-8f ? direction.normalized : Vector3.forward;
            Vector3 midpoint = baseMidpoint + Vector3.up * (wallHeight * 0.5f);

            GameObject box = GameObject.CreatePrimitive(PrimitiveType.Cube);
            box.name = $"Muro_{wall.id}";
            box.transform.SetParent(transform);
            box.transform.position = midpoint;
            box.transform.rotation = Quaternion.LookRotation(lengthAxis, Vector3.up);
            float thick = Mathf.Max(wall.grosor, 0.01f);
            box.transform.localScale = new Vector3(thick * wallScale, wallHeight, wallLength);
            box.GetComponent<Renderer>().material = WallMaterial();
            wallObjects.Add(box);
            RegisterFloor(box, wall.bottom);

            ElementSelectable selectable = box.AddComponent<ElementSelectable>();
            selectable.isWall = true;
            selectable.wallId = wall.id;
            selectable.wallTag = wall.elementTag;
            selectable.wallThickness = wall.grosor;
            selectable.wallLength = wall.longitud;
            selectable.wallBottom = wall.bottom;
            selectable.wallTop = wall.top;
            selectable.wallSourceBuilding = wall.sourceBuilding;
            selectable.wallSourceId = wall.sourceId;
            selectable.startPoint = start;
            selectable.endPoint = end + Vector3.up * wallHeight;
            selectable.data = null;
            selectable.nodeIId = wall.nodeI;
            selectable.nodeJId = wall.nodeJ;
            selectable.nodeISupport = FindSupportForNode(data, wall.nodeI);
            selectable.nodeJSupport = FindSupportForNode(data, wall.nodeJ);

            string pmSec = ResolveWallPMSection(data, wall.id, wall.nodeI, wall.nodeJ);
            selectable.pmSectionId = pmSec;
            selectable.pmDemands = wall.demands;

            selectables.Add(selectable);
        }
    }

    private float EstimateWallHeight(Vector3 start, Vector3 end)
    {
        float baseY = Mathf.Min(start.y, end.y);
        float best = float.PositiveInfinity;
        foreach (Vector3 node in nodes.Values)
        {
            if (node.y <= baseY + 0.05f)
            {
                continue;
            }

            bool sameStartPlan = Mathf.Abs(node.x - start.x) < 0.05f && Mathf.Abs(node.z - start.z) < 0.05f;
            bool sameEndPlan = Mathf.Abs(node.x - end.x) < 0.05f && Mathf.Abs(node.z - end.z) < 0.05f;
            if (!sameStartPlan && !sameEndPlan)
            {
                continue;
            }

            best = Mathf.Min(best, node.y - baseY);
        }

        if (!float.IsInfinity(best))
        {
            return Mathf.Max(best, 0.5f);
        }

        return EstimateTypicalStoryHeight();
    }

    private float EstimateTypicalStoryHeight()
    {
        float best = float.PositiveInfinity;
        foreach (Vector3 a in nodes.Values)
        {
            foreach (Vector3 b in nodes.Values)
            {
                float diff = b.y - a.y;
                if (diff > 0.5f && diff < best)
                {
                    best = diff;
                }
            }
        }

        return float.IsInfinity(best) ? 4.0f : best;
    }

    private string ResolvePMSection(string sectionId)
    {
        if (UnityData.GetPMCurve(sectionId) != null)
        {
            return sectionId;
        }
        if (UnityData.GetPMCurve(sectionId + "_FIBER") != null)
        {
            return sectionId + "_FIBER";
        }
        return string.IsNullOrEmpty(sectionId) ? null : sectionId;
    }

    private string ResolveWallPMSection(StructureData data, int wallId, int nodeI, int nodeJ)
    {
        if (data.p1l4 != null && data.p1l4.wallRegistry != null)
        {
            foreach (WallRegistryEntry entry in data.p1l4.wallRegistry)
            {
                if (entry != null && (entry.index == wallId || (entry.nodeI == nodeI && entry.nodeJ == nodeJ)) && entry.hasCurve)
                {
                    return entry.pmSectionId;
                }
            }
        }
        return null;
    }

    private void CreateDiaphragms(StructureData data)
    {
        if (data.diaphragmList == null)
        {
            return;
        }

        if (data.slabs != null && data.slabs.Length > 0)
        {
            CreateSlabPanels(data);
            return;
        }

        Bounds bounds = GetStructureBounds();
        float px = Mathf.Max(bounds.size.x, Mathf.Abs(bounds.min.x), Mathf.Abs(bounds.max.x));
        float py = Mathf.Max(bounds.size.y, Mathf.Abs(bounds.min.z), Mathf.Abs(bounds.max.z));

        foreach (DiaphragmData dia in data.diaphragmList)
        {
            Vector3 center = new Vector3(dia.x, dia.z, dia.y);

            GameObject plane = GameObject.CreatePrimitive(PrimitiveType.Cube);
            plane.name = $"Diafragma_{dia.level}_{dia.maestro}";
            plane.transform.SetParent(transform);
            plane.transform.position = center;
            plane.transform.localScale = new Vector3(px * 2f, 0.02f, py * 2f);
            plane.GetComponent<Renderer>().material = DiaphragmMaterial();

            InfoSelectable info = plane.AddComponent<InfoSelectable>();
            info.info = $"Diafragma rigido\n" +
                        $"Nivel: {dia.level}\n" +
                        $"Nodo maestro: {dia.maestro}\n" +
                        $"Esclavos: {(dia.slaves != null ? dia.slaves.Length : 0)}";

            diaphragmObjects.Add(plane);
            RegisterFloor(plane, dia.level);
        }
    }

    private void CreateSlabPanels(StructureData data)
    {
        float thickness = 0.02f;
        foreach (SlabData slab in data.slabs)
        {
            float cx = (slab.x0 + slab.x1) * 0.5f;
            float cy = (slab.y0 + slab.y1) * 0.5f;
            float dx = Mathf.Abs(slab.x1 - slab.x0);
            float dy = Mathf.Abs(slab.y1 - slab.y0);
            if (dx <= 0.001f || dy <= 0.001f)
            {
                continue;
            }

            Vector3 center = new Vector3(cx, slab.z, cy);

            GameObject plane = GameObject.CreatePrimitive(PrimitiveType.Cube);
            plane.name = $"Losa_{slab.id}_{slab.nivel}";
            plane.transform.SetParent(transform);
            plane.transform.position = center;
            plane.transform.localScale = new Vector3(dx, thickness, dy);
            plane.GetComponent<Renderer>().material = DiaphragmMaterial();

            float area = dx * dy;
            float qG = data.q_G;
            float totalLoad = area * qG;
            InfoSelectable info = plane.AddComponent<InfoSelectable>();
            info.info = $"Losa / diafragma de area\n" +
                        $"ID: {slab.id}\n" +
                        $"Nivel: {slab.nivel}\n" +
                        $"Area: {area:0.###} m2\n" +
                        $"Dimensiones: {dx:0.###} x {dy:0.###} m\n" +
                        $"qG: {qG:0.###} kN/m2\n" +
                        $"Carga gravitacional estimada: {totalLoad:0.###} kN\n" +
                        $"Nota: visualizada como panel; no es shell OpenSees.";

            diaphragmObjects.Add(plane);
            RegisterFloor(plane, slab.nivel);
        }
    }

    private Bounds GetStructureBounds()
    {
        Bounds bounds = new Bounds(Vector3.zero, Vector3.zero);
        bool first = true;
        foreach (Vector3 p in nodes.Values)
        {
            if (first)
            {
                bounds = new Bounds(p, Vector3.zero);
                first = false;
            }
            else
            {
                bounds.Encapsulate(p);
            }
        }
        return bounds;
    }

    private void CreateDiagramController()
    {
        // todos los controladores previos (el de la escena y los de recargas anteriores)
        foreach (DiagramController existing in GetComponents<DiagramController>())
        {
            existing.SetResultMode("None");   // limpia sus mallas y deja de dibujar su tabla
            existing.enabled = false;
            if (Application.isPlaying) Destroy(existing); else DestroyImmediate(existing);
        }
        diagramController = gameObject.AddComponent<DiagramController>();
        diagramController.Initialize(selectables);
    }

    private void CreatePMPanel()
    {
        PMPanel existing = GetComponent<PMPanel>();
        if (existing != null)
        {
            if (Application.isPlaying)
            {
                Destroy(existing);
            }
            else
            {
                DestroyImmediate(existing);
            }
        }
        pmPanel = gameObject.AddComponent<PMPanel>();
    }

    private void CreateMovingLoadPanel()
    {
        MovingLoadPanel existing = GetComponent<MovingLoadPanel>();
        if (existing != null)
        {
            if (Application.isPlaying)
            {
                Destroy(existing);
            }
            else
            {
                DestroyImmediate(existing);
            }
        }
        ElementRemovalPanel existingRemoval = GetComponent<ElementRemovalPanel>();
        if (existingRemoval != null)
        {
            if (Application.isPlaying)
            {
                Destroy(existingRemoval);
            }
            else
            {
                DestroyImmediate(existingRemoval);
            }
        }
        UnityData.ResetRemovalState();
        ElementLoadPanel existingElementLoad = GetComponent<ElementLoadPanel>();
        if (existingElementLoad != null)
        {
            if (Application.isPlaying)
            {
                Destroy(existingElementLoad);
            }
            else
            {
                DestroyImmediate(existingElementLoad);
            }
        }
        if (Application.isPlaying)
        {
            MovingLoadPanel panel = gameObject.AddComponent<MovingLoadPanel>();
            panel.Initialize(this, diagramController);
            ElementLoadPanel elementLoad = gameObject.AddComponent<ElementLoadPanel>();
            elementLoad.Initialize(this, diagramController);
            ElementRemovalPanel removal = gameObject.AddComponent<ElementRemovalPanel>();
            removal.Initialize(this, diagramController);
        }
    }

    /// <summary>Cambia el resultado mostrado (Axial/Corte/Momento/Deformada) manteniendo la barra superior sincronizada.</summary>
    public void SetResult(string resultName)
    {
        int index = System.Array.IndexOf(resultOptions, resultName);
        if (index < 0) return;
        resultIndex = index;
        if (diagramController != null)
        {
            diagramController.SetResultMode(resultName);
        }
    }

    /// <summary>Vuelve al combo seleccionado en la barra superior (al cerrar la carga movil).</summary>
    public void RestoreSelectedCombo()
    {
        RestoreBaseComboColors();
        if (diagramController != null && Application.isPlaying)
        {
            diagramController.Refresh();
        }
    }

    private void CreateSupports(StructureData data)
    {
        if (data.supports == null || data.supports.Length == 0)
        {
            return;
        }

        foreach (SupportData supportData in data.supports)
        {
            if (!nodes.ContainsKey(supportData.node))
            {
                continue;
            }

            CreateSupportSymbol(supportData);
        }
    }

    private void CreateSupportSymbol(SupportData supportData)
    {
        Vector3 node = nodes[supportData.node];

        GameObject support = GameObject.CreatePrimitive(PrimitiveType.Cube);
        support.name = $"Apoyo_Empotrado_N{supportData.node}";
        support.transform.SetParent(transform);
        support.transform.position = node + Vector3.down * 0.08f;
        support.transform.localScale = new Vector3(0.55f, 0.14f, 0.55f);
        support.GetComponent<Renderer>().material = SupportMaterial();
        supportObjects.Add(support);
        CreateSupportLabel(supportData, "Empotrado", node);
    }

    private void CreateSupportLabel(SupportData supportData, string label, Vector3 node)
    {
        GameObject labelObject = new GameObject($"Etiqueta_Apoyo_N{supportData.node}");
        labelObject.transform.SetParent(transform);
        labelObject.transform.position = node + new Vector3(0.15f, 0.25f, 0.15f);

        TextMesh text = labelObject.AddComponent<TextMesh>();
        text.text = $"N{supportData.node}\n{label}";
        text.characterSize = 0.18f;
        text.anchor = TextAnchor.MiddleCenter;
        text.color = Paleta.EtiquetaApoyo;
        supportObjects.Add(labelObject);
    }

    private void CreatePointLoads(StructureData data)
    {
        if (data.pointLoads == null)
        {
            return;
        }

        foreach (PointLoadData load in data.pointLoads)
        {
            if (!nodes.ContainsKey(load.node) || Mathf.Abs(load.fz) < 0.001f)
            {
                continue;
            }

            Vector3 node = nodes[load.node];
            float sign = load.fz < 0f ? -1f : 1f;
            Vector3 start = node + Vector3.up * sign * 0.9f;
            Vector3 end = node + Vector3.up * sign * 0.15f;
            Vector3 direction = end - start;

            GameObject arrow = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            arrow.name = $"Carga_Puntual_N{load.node}";
            arrow.transform.SetParent(transform);
            arrow.transform.position = (start + end) * 0.5f;
            arrow.transform.rotation = Quaternion.FromToRotation(Vector3.up, direction.normalized);
            arrow.transform.localScale = new Vector3(0.035f, direction.magnitude * 0.5f, 0.035f);
            arrow.GetComponent<Renderer>().material = CreateMaterial(Paleta.Carga);

            GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            head.name = $"Punta_Carga_N{load.node}";
            head.transform.SetParent(transform);
            head.transform.position = end;
            head.transform.localScale = new Vector3(0.18f, 0.18f, 0.18f);
            head.GetComponent<Renderer>().material = CreateMaterial(Paleta.Carga);
        }
    }

    private void CreateLoadArrows(StructureData data)
    {
        if (data.slabs == null || data.slabs.Length == 0)
        {
            return;
        }

        float qG = data.q_G;
        int created = 0;
        foreach (SlabData slab in data.slabs)
        {
            float cx = (slab.x0 + slab.x1) * 0.5f;
            float cy = (slab.y0 + slab.y1) * 0.5f;
            float dx = Mathf.Abs(slab.x1 - slab.x0);
            float dy = Mathf.Abs(slab.y1 - slab.y0);
            if (dx <= 0.001f || dy <= 0.001f)
            {
                continue;
            }

            float area = dx * dy;
            float load = area * qG;
            if (load < 1f)
            {
                continue;
            }

            Vector3 center = new Vector3(cx, slab.z, cy);
            float sign = -1f;
            Vector3 start = center + Vector3.up * sign * 0.9f;
            Vector3 end = center + Vector3.up * sign * 0.2f;
            Vector3 direction = end - start;

            GameObject arrow = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            arrow.name = $"Carga_Gravitacional_{slab.id}_{load:0}kN";
            arrow.transform.SetParent(transform);
            arrow.transform.position = (start + end) * 0.5f;
            arrow.transform.rotation = Quaternion.FromToRotation(Vector3.up, direction.normalized);
            arrow.transform.localScale = new Vector3(0.045f, direction.magnitude * 0.5f, 0.045f);
            arrow.GetComponent<Renderer>().material = CreateMaterial(Paleta.Carga);
            loadObjects.Add(arrow);
            RegisterFloor(arrow, slab.nivel);

            GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            head.name = $"Punta_Carga_{slab.id}";
            head.transform.SetParent(transform);
            head.transform.position = end;
            head.transform.localScale = new Vector3(0.2f, 0.2f, 0.2f);
            head.GetComponent<Renderer>().material = CreateMaterial(Paleta.Carga);
            loadObjects.Add(head);
            RegisterFloor(head, slab.nivel);
            created++;
        }

        Debug.Log($"[StructureViewer] Flechas de carga gravitacional: {created} losas (qG={qG:0.###} kN/m2).");
    }

    private void CreateGlobalAxes()
    {
        CreateAxis("X global", Vector3.zero, Vector3.right, Paleta.EjeX);
        CreateAxis("Y global", Vector3.zero, Vector3.forward, Paleta.EjeY);
        CreateAxis("Z global", Vector3.zero, Vector3.up, Paleta.EjeZ);
    }

    private void CreateAxis(string name, Vector3 start, Vector3 direction, Color color)
    {
        GameObject axis = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        axis.name = name;
        axis.transform.SetParent(transform);
        axis.transform.position = start + direction * 0.5f;
        axis.transform.rotation = Quaternion.FromToRotation(Vector3.up, direction);
        axis.transform.localScale = new Vector3(0.025f, 0.5f, 0.025f);

        Renderer renderer = axis.GetComponent<Renderer>();
        renderer.material = CreateMaterial(color);
    }

    // Metodos de visualizacion opcional (nodulos, IDs, ejes locales)
    public void SetUtilizationVisible(bool visible)
    {
        showUtilization = visible;
        if (visible)
        {
            ApplyUtilizationColors();
        }
        else
        {
            RestoreUtilizationColors();
        }
        RefreshVisibility();
    }

    private void ApplyUtilizationColors()
    {
        foreach (ElementSelectable sel in selectables)
        {
            if (sel == null)
            {
                continue;
            }
            Renderer renderer = sel.GetComponent<Renderer>();
            if (renderer == null)
            {
                continue;
            }
            GameObject go = sel.gameObject;
            if (!originalUtilColors.ContainsKey(go))
            {
                originalUtilColors[go] = renderer.material.color;
            }
            renderer.material.color = UtilizationColor(sel.GetActiveUtilization());
        }
    }

    private void RestoreUtilizationColors()
    {
        foreach (ElementSelectable sel in selectables)
        {
            if (sel == null)
            {
                continue;
            }
            Renderer renderer = sel.GetComponent<Renderer>();
            GameObject go = sel.gameObject;
            if (renderer != null && originalUtilColors.ContainsKey(go))
            {
                renderer.material.color = originalUtilColors[go];
            }
        }
        originalUtilColors.Clear();
    }

    private Color UtilizationColor(float ratio)
    {
        if (ratio <= 0f) return Paleta.UsoSinDato;
        float clamped = Mathf.Clamp01(ratio);
        if (clamped <= 0.7f)
        {
            return Color.Lerp(Paleta.UsoOk, Paleta.UsoLimite, clamped / 0.7f);
        }
        return Color.Lerp(Paleta.UsoLimite, Paleta.UsoFalla, (clamped - 0.7f) / 0.3f);
    }

    public void SetNodeMarkersVisible(bool visible)
    {
        if (visible && nodeMarkerObjects.Count == 0)
        {
            CreateNodeMarkers();
        }
        showNodeMarkers = visible;
        RefreshVisibility();
    }

    private void CreateNodeMarkers()
    {
        foreach (KeyValuePair<int, Vector3> kv in nodes)
        {
            GameObject marker = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            marker.name = $"Nodo_{kv.Key}";
            marker.transform.SetParent(transform);
            marker.transform.position = kv.Value;
            marker.transform.localScale = new Vector3(0.14f, 0.14f, 0.14f);
            marker.GetComponent<Renderer>().material = CreateMaterial(Paleta.Nodo);
            nodeMarkerObjects.Add(marker);
        }
    }

    public void SetIdsVisible(bool visible)
    {
        if (visible && idLabelObjects.Count == 0)
        {
            CreateIdLabels();
        }
        showIds = visible;
        RefreshVisibility();
    }

    private void CreateIdLabels()
    {
        foreach (KeyValuePair<int, Vector3> kv in nodes)
        {
            GameObject labelObject = new GameObject($"Label_Nodo_{kv.Key}");
            labelObject.transform.SetParent(transform);
            labelObject.transform.position = kv.Value + new Vector3(0, 0.35f, 0);

            TextMesh text = labelObject.AddComponent<TextMesh>();
            text.text = kv.Key.ToString();
            text.characterSize = 0.14f;
            text.anchor = TextAnchor.MiddleCenter;
            text.color = Paleta.EtiquetaNodo;
            idLabelObjects.Add(labelObject);
        }

        foreach (ElementSelectable sel in selectables)
        {
            if (sel.customLabel != null)
            {
                continue;
            }
            string label = GetSelectableLabel(sel);
            GameObject labelObject = new GameObject("Label_" + label.Replace(" ", "_"));
            labelObject.transform.SetParent(transform);
            Vector3 mid = (sel.startPoint + sel.endPoint) * 0.5f;
            labelObject.transform.position = mid + new Vector3(0, 0.3f, 0);

            TextMesh text = labelObject.AddComponent<TextMesh>();
            text.text = label;
            text.characterSize = 0.12f;
            text.anchor = TextAnchor.MiddleCenter;
            text.color = Paleta.EtiquetaElemento;
            idLabelObjects.Add(labelObject);
            RegisterFloor(labelObject, GetSelectableFloor(sel));
        }
    }

    public void SetLocalAxesVisible(bool visible)
    {
        if (visible && localAxisObjects.Count == 0)
        {
            CreateLocalAxes();
        }
        showLocalAxes = visible;
        RefreshVisibility();
    }

    private void CreateLocalAxes()
    {
        foreach (ElementSelectable sel in selectables)
        {
            if (sel.customLabel != null)
            {
                continue;
            }
            Vector3 mid = (sel.startPoint + sel.endPoint) * 0.5f;
            Vector3 dir = (sel.endPoint - sel.startPoint).normalized;
            Vector3 perp = Vector3.Cross(dir, Vector3.up).normalized;
            if (perp.sqrMagnitude < 0.01f)
            {
                perp = Vector3.right;
            }
            GameObject localAxis = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            localAxis.name = "EjeLocal_" + GetSelectableLabel(sel).Replace(" ", "_");
            localAxis.transform.SetParent(transform);
            localAxis.transform.position = mid + dir * 0.75f;
            localAxis.transform.rotation = Quaternion.FromToRotation(Vector3.up, dir);
            localAxis.transform.localScale = new Vector3(0.02f, 0.75f, 0.02f);
            localAxis.GetComponent<Renderer>().material = CreateMaterial(Paleta.EjeLocal);
            localAxisObjects.Add(localAxis);
            RegisterFloor(localAxis, GetSelectableFloor(sel));
        }
    }

    private void RefreshVisibility()
    {
        if (showNodeMarkers && nodeMarkerObjects.Count == 0)
        {
            CreateNodeMarkers();
        }
        if (showIds && idLabelObjects.Count == 0)
        {
            CreateIdLabels();
        }
        if (showLocalAxes && localAxisObjects.Count == 0)
        {
            CreateLocalAxes();
        }
        if (showLoads)
        {
            EnsureLoadOverlay();   // G/Q repartidas y EX/EY del caso activo (StructureViewer.Overlays.cs)
        }

        SetGroupVisible(columnObjects, showColumns);
        SetGroupVisible(beamObjects, showBeams);
        SetGroupVisible(wallObjects, showWalls);
        SetGroupVisible(supportObjects, showSupports);
        SetGroupVisible(diaphragmObjects, showDiaphragms);
        SetGroupVisible(nodeMarkerObjects, showNodeMarkers);
        SetGroupVisible(idLabelObjects, showIds);
        SetGroupVisible(localAxisObjects, showLocalAxes);
        SetGroupVisible(loadObjects, showLoads);
        SetGroupVisible(gridObjects, showGrid);
        SetGroupVisible(diaphragmMarkObjects, showDiaphragmMarks);
    }

    private bool IsRemovedObject(GameObject go)
    {
        if (UnityData.RemovedElements == null || UnityData.RemovedElements.Count == 0) return false;
        ElementSelectable sel = go.GetComponent<ElementSelectable>();
        return sel != null && sel.data != null && UnityData.IsRemoved(sel.data.id);
    }

    private void SetGroupVisible(List<GameObject> group, bool visible)
    {
        foreach (GameObject go in group)
        {
            if (go != null)
            {
                go.SetActive(visible && PassesFloorFilter(go) && !IsRemovedObject(go));
            }
        }
    }

    private void RegisterFloor(GameObject go, string floor)
    {
        if (go == null)
        {
            return;
        }
        objectFloor[go] = NormalizeFloor(floor);
    }

    private bool PassesFloorFilter(GameObject go)
    {
        if (floorOptions == null || floorOptions.Length == 0 || floorIndex <= 0)
        {
            return true;
        }
        string selectedFloor = floorOptions[Mathf.Clamp(floorIndex, 0, floorOptions.Length - 1)];
        string goFloor;
        if (!objectFloor.TryGetValue(go, out goFloor))
        {
            return true;
        }
        return goFloor == selectedFloor;
    }

    private string NormalizeFloor(string floor)
    {
        return string.IsNullOrEmpty(floor) ? "Sin piso" : floor;
    }

    private void BuildFloorOptions()
    {
        var floors = new List<string>();
        floors.Add("Todos");

        foreach (string floor in objectFloor.Values)
        {
            if (!floors.Contains(floor))
            {
                floors.Add(floor);
            }
        }

        floorOptions = floors.ToArray();
        floorIndex = Mathf.Clamp(floorIndex, 0, Mathf.Max(0, floorOptions.Length - 1));
    }

    private void OnGUI()
    {
        UiTheme.ApplyScale();
        if (!ViewerUI.Active)
        {
            DrawTopBar();
            DrawLeftPanel();
        }
        RefreshVisibility();
    }

    private void DrawTopBar()
    {
        float x = UiTheme.SideM;
        float y = 7f;
        float w = UiTheme.ScreenW - UiTheme.SideM * 2f;
        float h = UiTheme.TopBarH - 14f;
        UiTheme.GUIBox(new Rect(x, y, w, h));
        GUI.Label(new Rect(x + 12f, y + 4f, 320f, 16f), "GRUPO 8 · MCOP P1L4 — MODELO TRIBUTARIO · OPENSEES", UiTheme.Brand);

        float cy = y + 26f;
        float cx = x + 12f;
        GUI.Label(new Rect(cx, cy, 52f, 20f), "Combo", UiTheme.DimLabel);
        if (comboOptions.Length > 0)
        {
            int index = GUI.Toolbar(new Rect(cx + 54f, cy, 232f, 20f), comboIndex, comboOptions);
            if (index != comboIndex)
            {
                comboIndex = index;
                ApplyCombo(comboIndex);
                statusMessage = "Combinacion activa: " + UnityData.GetComboLabel(UnityData.ActiveCombo);
            }
        }

        cx = x + 330f;
        GUI.Label(new Rect(cx, cy, 62f, 20f), "Resultado", UiTheme.DimLabel);
        float bx = x + w - 240f;
        float resultW = Mathf.Max(120f, Mathf.Min(430f, w - 560f));
        float maxResultW = bx - (cx + 66f) - 24f;
        if (resultW > maxResultW) resultW = Mathf.Max(120f, maxResultW);
        int nextResult = GUI.Toolbar(new Rect(cx + 66f, cy, resultW, 20f), resultIndex, resultOptions);
        if (nextResult != resultIndex)
        {
            resultIndex = nextResult;
            if (diagramController != null)
            {
                diagramController.SetResultMode(resultOptions[resultIndex]);
            }
            statusMessage = "Resultado activo: " + resultOptions[resultIndex];
        }

        // orbita libre con el mouse: sin botones de vista fija
        DiagramController.AnimateDeformed = GUI.Toggle(new Rect(bx, cy, 230f, 20f), DiagramController.AnimateDeformed, " Animar deformada");

        GUI.Label(new Rect(x + 12f, y + 50f, w - 24f, 14f),
            "Estado: " + statusMessage + (Application.isMobilePlatform
                ? "   |   Toque: seleccionar · 1 dedo: orbitar · Pellizco: zoom · 2 dedos: desplazar"
                : "   |   Click izq: seleccionar · Click der: orbitar · Rueda: zoom · I/J: extremos locales"),
            UiTheme.DimLabel);
    }

    private string searchText = "";

    /// Busca un elemento por id o tag, lo selecciona y centra la camara en el.
    private void FindAndSelect(string key)
    {
        key = (key ?? "").Trim();
        if (key.Length == 0) return;
        foreach (ElementSelectable sel in selectables)
        {
            // muros: MURO-013, W_MURO-013 (elemento OpenSees) o el numero de muro
            if (sel != null && sel.isWall && !string.IsNullOrEmpty(sel.wallTag)
                && (string.Equals(sel.wallTag, key, System.StringComparison.OrdinalIgnoreCase)
                    || string.Equals("W_" + sel.wallTag, key, System.StringComparison.OrdinalIgnoreCase)))
            {
                if (!sel.gameObject.activeInHierarchy) floorIndex = 0;
                var wallPicker = FindAnyObjectByType<ElementPicker>();
                if (wallPicker != null) wallPicker.SelectElement(sel, true);
                statusMessage = "Muro " + sel.wallTag + " seleccionado.";
                return;
            }
            if (sel == null || sel.data == null) continue;
            if (sel.data.id.ToString() == key || string.Equals(sel.data.elementTag, key, System.StringComparison.OrdinalIgnoreCase))
            {
                if (UnityData.IsRemoved(sel.data.id))
                {
                    statusMessage = $"{key} esta quitado en el modelo modificado.";
                    return;
                }
                if (!sel.gameObject.activeInHierarchy)
                {
                    floorIndex = 0;   // quita el filtro de piso para que se vea
                }
                var picker = FindAnyObjectByType<ElementPicker>();
                if (picker != null) picker.SelectElement(sel, true);
                statusMessage = "Elemento " + (sel.data.elementTag ?? key) + " seleccionado.";
                return;
            }
        }
        statusMessage = $"No existe el elemento '{key}'.";
    }

    private void DrawLeftPanel()
    {
        Rect area = UiTheme.LeftArea();
        float x = area.x;
        float y = area.y;
        float w = area.width;
        float h = area.height;
        UiTheme.GUIBox(new Rect(x, y, w, h), "CONSOLA DE CAPAS Y FILTROS");

        float innerX = x + 12f;
        float innerY = y + 30f;
        float innerW = w - 24f;
        leftScroll = GUI.BeginScrollView(new Rect(x + 4f, innerY, w - 8f, h - 38f), leftScroll,
            new Rect(x + 4f, innerY, w - 24f, 596f));

        // Buscar elemento por id/tag: lo selecciona y centra la camara
        GUI.Label(new Rect(innerX, innerY, innerW, 20f), "BUSCAR ELEMENTO", UiTheme.Header);
        innerY += 22f;
        searchText = GUI.TextField(new Rect(innerX, innerY, innerW - 86f, 22f), searchText);
        if (GUI.Button(new Rect(innerX + innerW - 80f, innerY, 80f, 22f), "Ir"))
        {
            FindAndSelect(searchText);
        }
        innerY += 34f;

        GUI.Label(new Rect(innerX, innerY, innerW, 20f), "VISIBILIDAD", UiTheme.Header);
        innerY += 22f;
        showColumns = GUI.Toggle(new Rect(innerX, innerY, 104f, 20f), showColumns, "Columnas");
        showBeams = GUI.Toggle(new Rect(innerX + 108f, innerY, 82f, 20f), showBeams, "Vigas");
        showWalls = GUI.Toggle(new Rect(innerX + 200f, innerY, 82f, 20f), showWalls, "Muros");
        innerY += 24f;
        showSupports = GUI.Toggle(new Rect(innerX, innerY, 104f, 20f), showSupports, "Apoyos");
        showDiaphragms = GUI.Toggle(new Rect(innerX + 108f, innerY, 82f, 20f), showDiaphragms, "Losas");
        showNodeMarkers = GUI.Toggle(new Rect(innerX + 200f, innerY, 82f, 20f), showNodeMarkers, "Nodos");
        innerY += 26f;
        showIds = GUI.Toggle(new Rect(innerX, innerY, 104f, 20f), showIds, "IDs");
        showLocalAxes = GUI.Toggle(new Rect(innerX + 108f, innerY, 118f, 20f), showLocalAxes, "Ejes locales");
        showLoads = GUI.Toggle(new Rect(innerX + 234f, innerY, 78f, 20f), showLoads, "Cargas");
        innerY += 36f;

        GUI.Label(new Rect(innerX, innerY, innerW, 20f), "FILTRO POR PISO", UiTheme.Header);
        innerY += 22f;
        int nextFloor = GUI.SelectionGrid(new Rect(innerX, innerY, innerW, Mathf.Ceil(floorOptions.Length / 2f) * 22f), floorIndex, floorOptions, 2);
        if (nextFloor != floorIndex)
        {
            floorIndex = nextFloor;
            statusMessage = "Filtro de piso: " + floorOptions[floorIndex];
        }
        innerY += Mathf.Ceil(floorOptions.Length / 2f) * 22f + 12f;

        if (GUI.Button(new Rect(innerX, innerY, 102f, 22f), "Mostrar todo"))
        {
            showColumns = showBeams = showWalls = showSupports = showDiaphragms = true;
            showNodeMarkers = showIds = showLocalAxes = showLoads = false;
            if (showUtilization)
            {
                showUtilization = false;
                RestoreUtilizationColors();
            }
            floorIndex = 0;
            statusMessage = "Vista restablecida.";
        }
        if (GUI.Button(new Rect(innerX + 110f, innerY, 102f, 22f), "Solo estructura"))
        {
            showColumns = showBeams = showWalls = true;
            showSupports = showDiaphragms = showNodeMarkers = showIds = showLocalAxes = showLoads = false;
            if (showUtilization)
            {
                showUtilization = false;
                RestoreUtilizationColors();
            }
            statusMessage = "Capas auxiliares ocultas.";
        }
        innerY += 34f;

        showTributarySummary = GUI.Toggle(new Rect(innerX, innerY, 186f, 20f), showTributarySummary, "Resumen tributario");
        innerY += 23f;
        if (showTributarySummary)
        {
            foreach (KeyValuePair<string, TributaryFloorData> kv in tributaryFloors)
            {
                TributaryFloorData td = kv.Value;
                GUI.Label(new Rect(innerX, innerY, innerW, 17f), $"{kv.Key}: A={td.area_total:0.##} m2 | carga={td.carga_total:0.##} kN", UiTheme.Label);
                innerY += 17f;
            }
        }
        innerY += 6f;

        bool nextUtilization = GUI.Toggle(new Rect(innerX, innerY, 216f, 20f), showUtilization, "Colorear por utilizacion (C)");
        if (nextUtilization != showUtilization)
        {
            SetUtilizationVisible(nextUtilization);
            statusMessage = showUtilization ? "Colores por C = demanda/capacidad P-M." : "Colores por capa restaurados.";
        }
        innerY += 22f;
        if (showUtilization)
        {
            GUI.Label(new Rect(innerX, innerY, innerW, 18f), "verde: C<=0.7 | amarillo: C~1 | rojo: C>1", UiTheme.DimLabel);
            innerY += 18f;
        }

        // -------------------------------------------------------------
        // BLOQUE C14/C15/C16 · SUPERPOSICION EN VIVO (sliders G/Q/EX/EY)
        // Los 4 sliders fijan los lambdas de los casos base y al moverlos
        // llaman a UnityData.ApplySuperposition, que genera el combo
        // sintetico "SUP" = Σ lambda_i · caso_base_i para fuerzas Y
        // desplazamientos. Activar ese combo actualiza al instante:
        //    C14 deformada (DiagramController.CreateDeformedDiagram)
        //    C15 resultados/diagramas (DiagramController.GetForceGradient)
        //    C16 punto P-M (PMPanel.GetActiveDemandRecord)
        // porque todo el pipeline lee por UnityData.ActiveCombo.
        // -------------------------------------------------------------
        GUI.Label(new Rect(innerX, innerY, innerW, 18f), "SUPERPOSICIÓN EN VIVO", UiTheme.Header);
        innerY += 22f;   // el titulo ocupa su propia fila (antes quedaba encima del deslizador G)
        if (!showSuperposition)
        {
            if (GUI.Button(new Rect(innerX, innerY, innerW, 22f), "Activar superposicion lineal"))
            {
                showSuperposition = true;
                statusMessage = "Sliders de superposicion activos. Movelos y la estructura se actualiza sola.";
                ApplySyntheticCombo();
            }
            innerY += 26f;
        }
        else
        {
            GUI.Label(new Rect(innerX, innerY, 26f, 20f), "G", UiTheme.DimLabel);
            float newG = GUI.HorizontalSlider(new Rect(innerX + 30f, innerY, 150f, 20f), superpositionG, -3f, 4f);
            if (Mathf.Abs(newG - superpositionG) > 0.0005f)
            {
                superpositionG = newG;
                ApplySyntheticCombo();
            }
            GUI.Label(new Rect(innerX + 184f, innerY, 70f, 20f), superpositionG.ToString("0.##"), UiTheme.DimLabel);
            innerY += 23f;

            GUI.Label(new Rect(innerX, innerY, 26f, 20f), "Q", UiTheme.DimLabel);
            float newQ = GUI.HorizontalSlider(new Rect(innerX + 30f, innerY, 150f, 20f), superpositionQ, -3f, 4f);
            if (Mathf.Abs(newQ - superpositionQ) > 0.0005f)
            {
                superpositionQ = newQ;
                ApplySyntheticCombo();
            }
            GUI.Label(new Rect(innerX + 184f, innerY, 70f, 20f), superpositionQ.ToString("0.##"), UiTheme.DimLabel);
            innerY += 23f;

            GUI.Label(new Rect(innerX, innerY, 26f, 20f), "EX", UiTheme.DimLabel);
            float newEX = GUI.HorizontalSlider(new Rect(innerX + 30f, innerY, 150f, 20f), superpositionEX, -3f, 4f);
            if (Mathf.Abs(newEX - superpositionEX) > 0.0005f)
            {
                superpositionEX = newEX;
                ApplySyntheticCombo();
            }
            GUI.Label(new Rect(innerX + 184f, innerY, 70f, 20f), superpositionEX.ToString("0.##"), UiTheme.DimLabel);
            innerY += 23f;

            GUI.Label(new Rect(innerX, innerY, 26f, 20f), "EY", UiTheme.DimLabel);
            float newEY = GUI.HorizontalSlider(new Rect(innerX + 30f, innerY, 150f, 20f), superpositionEY, -3f, 4f);
            if (Mathf.Abs(newEY - superpositionEY) > 0.0005f)
            {
                superpositionEY = newEY;
                ApplySyntheticCombo();
            }
            GUI.Label(new Rect(innerX + 184f, innerY, 70f, 20f), superpositionEY.ToString("0.##"), UiTheme.DimLabel);
            innerY += 30f;

            if (GUI.Button(new Rect(innerX, innerY, 140f, 22f), "Restaurar lambdas 1.0"))
            {
                superpositionG = superpositionQ = superpositionEX = superpositionEY = 1f;
                ApplySyntheticCombo();
            }
            if (GUI.Button(new Rect(innerX + 148f, innerY, 108f, 22f), "Desactivar"))
            {
                showSuperposition = false;
                if (UnityData.ActiveCombo == UnityData.SuperpositionComboName)
                {
                    RestoreBaseComboColors();
                }
            }
            innerY += 28f;
            GUI.Label(new Rect(innerX, innerY, innerW, 17f),
                "Activa: SUP = " + UnityData.SuperpositionLambdas[0].ToString("0.##") + "G + " +
                UnityData.SuperpositionLambdas[1].ToString("0.##") + "Q + " +
                UnityData.SuperpositionLambdas[2].ToString("0.##") + "EX + " +
                UnityData.SuperpositionLambdas[3].ToString("0.##") + "EY", UiTheme.DimLabel);
        }

        GUI.EndScrollView();
    }

    private void SetCameraPreset(string preset)
    {
        Camera cam = Camera.main;
        if (cam == null) return;
        OrbitCamera orbit = cam.GetComponent<OrbitCamera>();
        if (orbit != null)
        {
            orbit.SetPreset(preset);
            statusMessage = "Vista de camara: " + preset;
        }
    }

    /// <summary>
    /// Aplica la superposicion lineal de los casos base G/Q/EX/EY llamando a
    /// UnityData.ApplySuperposition. Ese metodo genera el combo sintetico "SUP"
    /// (fuerzas y desplazamientos = Σ lambda_i · caso_base_i) y lo deja como
    /// ActiveCombo, con lo cual toda la cadena existente (diagramas axial/
    /// corte/momento, deformada y punto P-M) se actualiza en vivo: C14/C15/C16.
    /// </summary>
    private void ApplySyntheticCombo()
    {
        UnityData.ApplySuperposition(superpositionG, superpositionQ, superpositionEX, superpositionEY);

        if (diagramController != null && Application.isPlaying)
        {
            diagramController.Refresh();
        }

        if (pmPanel != null)
        {
            var picker = FindObjectOfType<ElementPicker>();
            if (picker != null && picker.Selected != null)
            {
                pmPanel.ShowPMForElement(picker.Selected);
            }
        }

        if (showUtilization)
        {
            ApplyUtilizationColors();
        }

        statusMessage = "Superposicion activa: " + UnityData.GetComboLabel(UnityData.ActiveCombo);
    }

    /// <summary>
    /// Al desactivar la superposicion, vuelve al combo base previamente
    /// seleccionado y restaura sus colores.
    /// </summary>
    private void RestoreBaseComboColors()
    {
        if (comboOptions.Length > 0)
        {
            ApplyCombo(comboIndex);
        }
        else
        {
            UnityData.ActiveCombo = null;
        }
    }

    private string GetSelectableLabel(ElementSelectable sel)
    {
        if (sel == null) return "-";
        if (sel.isWall) return "Muro " + sel.wallId;
        if (sel.data == null) return sel.name;
        return sel.data.type + " " + (!string.IsNullOrEmpty(sel.data.elementTag) ? sel.data.elementTag : sel.data.id.ToString());
    }

    private string GetSelectableFloor(ElementSelectable sel)
    {
        if (sel == null) return "Sin piso";
        if (sel.isWall) return NormalizeFloor(sel.wallBottom);
        if (sel.data != null) return NormalizeFloor(sel.data.piso);
        return "Sin piso";
    }

    private Vector3 ToUnity(NodeData node)
    {
        return new Vector3(node.x, node.z, node.y);
    }

    private void CreateDefaultMaterials()
    {
        defaultBeamMaterial = CreateMaterial(Paleta.Viga);
        defaultColumnMaterial = CreateMaterial(Paleta.Pilar);
        defaultSupportMaterial = CreateMaterial(Paleta.Apoyo);
        defaultWallMaterial = CreateMaterial(Paleta.Muro);
        defaultDiaphragmMaterial = CreateMaterial(Paleta.Losa);
        defaultBraceMaterial = CreateMaterial(Paleta.Arriostre);
    }

    // ------------------------------------------------------------------
    // Suelo: pradera de pasto bajo el edificio + cielo de la paleta Arrebol.
    // La textura del pasto se genera por codigo (sin assets externos) y se
    // repite cada PastoTileM metros, con franjas de corte como un prado recien
    // cortado. Queda justo bajo los dados de apoyo: no tapa el subterraneo y,
    // sin collider, no interfiere con la seleccion de elementos.
    // ------------------------------------------------------------------
    private const float PastoTileM = 12f;
    private static Texture2D pastoTex;

    private void CreateGroundGrid()
    {
        Bounds limites = GetStructureBounds();
        float sueloY = limites.min.y - 0.16f;   // los dados de apoyo bajan 0,15 m bajo el nudo
        float lado = Mathf.Max(800f, 8f * Mathf.Max(limites.size.x, limites.size.z));

        GameObject pasto = GameObject.CreatePrimitive(PrimitiveType.Quad);
        pasto.name = "Env_Pasto";
        pasto.transform.SetParent(transform);
        pasto.transform.position = new Vector3(limites.center.x, sueloY, limites.center.z);
        pasto.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
        pasto.transform.localScale = new Vector3(lado, lado, 1f);
        Collider colPasto = pasto.GetComponent<Collider>();
        if (colPasto != null) colPasto.enabled = false;

        Material matPasto = CreateMaterial(Color.white);
        matPasto.mainTexture = PastoTexture();
        matPasto.mainTextureScale = new Vector2(lado / PastoTileM, lado / PastoTileM);
        if (matPasto.HasProperty("_Glossiness")) matPasto.SetFloat("_Glossiness", 0.05f);
        if (matPasto.HasProperty("_Metallic")) matPasto.SetFloat("_Metallic", 0f);

        Renderer rendPasto = pasto.GetComponent<Renderer>();
        rendPasto.material = matPasto;
        rendPasto.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        rendPasto.receiveShadows = true;
        pasto.hideFlags = HideFlags.DontSave;

        AplicarCielo();
    }

    /// Cielo procedural de la escena con un tinte lila (arrebol) y el horizonte
    /// verdoso, para que el pasto se funda con el fondo. Solo en Play: en el
    /// editor no se modifica la configuracion de la escena.
    private void AplicarCielo()
    {
        if (!Application.isPlaying) return;
        Material actual = RenderSettings.skybox;
        if (actual == null || actual.name == "Cielo_Arrebol") return;
        Material cielo = new Material(actual) { name = "Cielo_Arrebol" };
        if (cielo.HasProperty("_SkyTint")) cielo.SetColor("_SkyTint", Paleta.CieloTinte);
        if (cielo.HasProperty("_GroundColor")) cielo.SetColor("_GroundColor", Paleta.CieloSuelo);
        if (cielo.HasProperty("_AtmosphereThickness")) cielo.SetFloat("_AtmosphereThickness", 1.15f);
        if (cielo.HasProperty("_Exposure")) cielo.SetFloat("_Exposure", 1.2f);
        RenderSettings.skybox = cielo;
        DynamicGI.UpdateEnvironment();
    }

    /// Textura repetible de pasto (512 x 512 px = PastoTileM metros): manchas suaves
    /// de ruido periodico, miles de hojas cortas y dos franjas de corte por repeticion.
    private static Texture2D PastoTexture()
    {
        if (pastoTex != null) return pastoTex;
        const int n = 512;
        System.Random rnd = new System.Random(8);   // semilla fija: el mismo pasto en cada corrida

        int[] grillas = { 4, 8, 24 };
        float[] pesos = { 0.5f, 0.3f, 0.2f };
        float[][] redes = new float[grillas.Length][];
        for (int k = 0; k < grillas.Length; k++)
        {
            int g = grillas[k];
            redes[k] = new float[g * g];
            for (int i = 0; i < g * g; i++) redes[k][i] = (float)rnd.NextDouble();
        }

        Color[] px = new Color[n * n];
        for (int y = 0; y < n; y++)
        {
            for (int x = 0; x < n; x++)
            {
                float u = (float)x / n;
                float v = (float)y / n;
                float fbm = 0f;
                for (int k = 0; k < grillas.Length; k++) fbm += pesos[k] * RuidoPeriodico(redes[k], grillas[k], u, v);
                float grano = 1f + ((float)rnd.NextDouble() - 0.5f) * 0.08f;
                px[y * n + x] = Color.Lerp(Paleta.PastoOscuro, Paleta.PastoClaro, 0.2f + 0.7f * fbm) * grano;
            }
        }

        // hojas: trazos cortos en direcciones al azar, con vuelta por los bordes (textura repetible)
        int hojas = n * n / 5;
        for (int i = 0; i < hojas; i++)
        {
            float hx = (float)rnd.NextDouble() * n;
            float hy = (float)rnd.NextDouble() * n;
            float largo = 3f + (float)rnd.NextDouble() * 6f;
            float ang = (float)rnd.NextDouble() * 2f * Mathf.PI;
            double r = rnd.NextDouble();
            Color tono = r < 0.55 ? Paleta.PastoHoja : (r < 0.95 ? Paleta.PastoSombra : Paleta.PastoSeco);
            float cx = Mathf.Cos(ang);
            float cy = Mathf.Sin(ang);
            int pasos = Mathf.CeilToInt(largo);
            for (int s = 0; s < pasos; s++)
            {
                int qx = Mathf.FloorToInt(hx + cx * s) % n;
                int qy = Mathf.FloorToInt(hy + cy * s) % n;
                if (qx < 0) qx += n;
                if (qy < 0) qy += n;
                int idx = qy * n + qx;
                px[idx] = Color.Lerp(px[idx], tono, 0.55f);
            }
        }

        // franjas de corte: media repeticion un poco mas clara y media un poco mas oscura
        for (int x = 0; x < n; x++)
        {
            float onda = Mathf.Sin(2f * Mathf.PI * x / n);
            float t = Mathf.Clamp01((onda + 0.12f) / 0.24f);
            t = t * t * (3f - 2f * t);
            float factor = 1f + 0.05f * (2f * t - 1f);
            for (int y = 0; y < n; y++)
            {
                Color c = px[y * n + x] * factor;
                c.a = 1f;
                px[y * n + x] = c;
            }
        }

        pastoTex = new Texture2D(n, n, TextureFormat.RGBA32, true);
        pastoTex.name = "Pasto_Arrebol";
        pastoTex.wrapMode = TextureWrapMode.Repeat;
        pastoTex.filterMode = FilterMode.Trilinear;
        pastoTex.anisoLevel = 8;
        pastoTex.SetPixels(px);
        pastoTex.Apply(true);
        pastoTex.hideFlags = HideFlags.DontSave;
        return pastoTex;
    }

    /// Ruido de valor periodico en [0, 1): una grilla g x g de valores al azar
    /// interpolada suavemente, que da la vuelta en u = 1 y v = 1 (sin costuras).
    private static float RuidoPeriodico(float[] red, int g, float u, float v)
    {
        float gx = u * g;
        float gy = v * g;
        int x0 = Mathf.FloorToInt(gx);
        int y0 = Mathf.FloorToInt(gy);
        float fx = gx - x0;
        float fy = gy - y0;
        fx = fx * fx * (3f - 2f * fx);
        fy = fy * fy * (3f - 2f * fy);
        int i0 = x0 % g, i1 = (x0 + 1) % g, j0 = y0 % g, j1 = (y0 + 1) % g;
        float a = red[j0 * g + i0], b = red[j0 * g + i1];
        float c = red[j1 * g + i0], d = red[j1 * g + i1];
        float arriba = a + (b - a) * fx;
        float abajo = c + (d - c) * fx;
        return arriba + (abajo - arriba) * fy;
    }

    private void CreateGridLine(Vector3 a, Vector3 b, float thickness, Material material)
    {
        Vector3 mid = (a + b) * 0.5f;
        Vector3 dir = b - a;
        float len = dir.magnitude;
        GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
        obj.name = "Env_GridLine";
        obj.transform.SetParent(transform);
        obj.transform.position = mid;
        obj.transform.rotation = Quaternion.FromToRotation(Vector3.right, dir.normalized);
        obj.transform.localScale = new Vector3(len, thickness, thickness);
        obj.GetComponent<Renderer>().material = material;
        obj.GetComponent<Collider>().enabled = false;
        obj.hideFlags = HideFlags.DontSave;
    }

    private Material CreateMaterial(Color color)
    {
        Shader shader = Shader.Find("Standard");
        if (shader == null)
        {
            shader = Shader.Find("Universal Render Pipeline/Lit");
        }
        if (shader == null)
        {
            shader = Shader.Find("Sprites/Default");
        }

        Material material = new Material(shader);
        material.color = color;
        if (color.a < 1f)
        {
            material.SetFloat("_Mode", 3f);
            material.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            material.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            material.SetInt("_ZWrite", 0);
            material.DisableKeyword("_ALPHATEST_ON");
            material.EnableKeyword("_ALPHABLEND_ON");
            material.renderQueue = 3000;
        }
        return material;
    }

    private Material BeamMaterial()
    {
        return beamMaterial != null ? beamMaterial : defaultBeamMaterial;
    }

    private Material ColumnMaterial()
    {
        return columnMaterial != null ? columnMaterial : defaultColumnMaterial;
    }

    private Material SupportMaterial()
    {
        return supportMaterial != null ? supportMaterial : defaultSupportMaterial;
    }

    private Material WallMaterial()
    {
        return defaultWallMaterial;
    }

    private Material DiaphragmMaterial()
    {
        return defaultDiaphragmMaterial;
    }

    private Material BraceMaterial()
    {
        return defaultBraceMaterial;
    }
}
