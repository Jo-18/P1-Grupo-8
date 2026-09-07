using System.Collections.Generic;
using UnityEngine;

namespace LabViewer
{
    /// <summary>
    /// Controlador principal: carga el paquete, gestiona filtros independientes
    /// (edificio, nivel, tipo), controles de visualizacion (losas, vigas, columnas,
    /// muros, nodos, apoyos, diafragmas, aberturas, IDs, ejes locales, areas
    /// tributarias), vistas, seleccion por clic, panel de inspeccion e inspector de
    /// areas tributarias. UI via OnGUI (sin dependencias externas).
    ///
    /// Cada toggle activa/desactiva los Renderers del tipo correspondiente de forma
    /// inmediata (SetActive sobre el grupo de la jerarquia o el marcador) sin
    /// reconstruir el modelo ni perder la seleccion. Edificio + nivel + tipo se
    /// combinan en AND: un objeto se muestra solo si cumple todos los filtros activos.
    /// </summary>
    public class ViewerController : MonoBehaviour
    {
        public CameraController Cam;
        private LabLoader _loader;
        private LabModel Model => _loader != null ? _loader.Model : null;

        /// <summary>Acceso al modelo cargado (para inspeccion y verificaciones).</summary>
        public LabModel ModelPublic => Model;

        // filtros (independientes y combinables en AND)
        private readonly Dictionary<string, bool> _bldgOn = new Dictionary<string, bool> { ["I"] = true, ["II"] = true };
        private readonly Dictionary<string, bool> _typeOn = new Dictionary<string, bool>();
        private readonly Dictionary<string, bool> _levelOn = new Dictionary<string, bool>();

        // superpuestos
        public bool ShowNodos, ShowApoyos, ShowIds, ShowAxes, ShowTributary;
        public bool GlobalIds, GlobalAxes;   // mostrar IDs/ejes en TODOS los elementos

        // --- cielo P4 ---
        private bool _p4SkyMode;
        private int _p4CountI;
        private int _p4CountII;
        private const string P4_DIAG_HEX = "#00CCAA";

        private ElementRef _selected;
        private readonly List<Marker> _markers = new List<Marker>();
        private bool _draggingUi;

        private Vector2 _scroll;
        private Vector2 _inspScroll;
        private bool _showIntegrationDiag;

        /// <summary>Marcador superpuesto (nodo/apoyo/eje/id/tributaria) con su
        /// contexto de filtrado para combinarlo en AND con edificio+nivel+estado.</summary>
        public class Marker
        {
            public GameObject Go;
            public string Building;
            public string Level;
            public string Kind; // "nodo","apoyo","axis","id","trib"
            public Marker(GameObject go, string building, string level, string kind)
            { Go = go; Building = building; Level = level; Kind = kind; }
        }

        void Awake() { _loader = GetComponent<LabLoader>(); }

        void Start()
        {
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
                _typeOn[t.ToString()] = t != ElemType.Nodos; // nodos off por defecto

            bool ok = _loader.Load();
            if (ok)
            {
                SetupCameraAndLight();
                RebuildOverlays();
            }
            else
            {
                Debug.LogError("Fallo la carga del paquete de datos.");
            }
        }

        private void SetupCameraAndLight()
        {
            if (Cam == null)
            {
                var camGo = GameObject.Find("Main Camera");
                if (camGo == null)
                {
                    camGo = new GameObject("Main Camera");
                    camGo.tag = "MainCamera";
                    var c = camGo.AddComponent<Camera>();
                    c.clearFlags = CameraClearFlags.SolidColor;
                    c.backgroundColor = new Color(0.15f, 0.17f, 0.2f);
                    camGo.AddComponent<AudioListener>();
                }
                Cam = camGo.AddComponent<CameraController>();
            }
            if (GameObject.FindObjectOfType<Light>() == null)
            {
                var sun = new GameObject("Sun");
                var l = sun.AddComponent<Light>();
                l.type = LightType.Directional;
                l.intensity = 1.1f;
                sun.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
            }
            Cam.Target = GameObject.Find("Lab") != null ? GameObject.Find("Lab").transform : null;
            Cam.Distance = 75f;
            FrameAll();
        }

        // ---------------------------------------------------------------- //
        //  Filtros (recorren la jerarquia Lab/Building/Level/Type)
        // ---------------------------------------------------------------- //
        private bool BuildingOn(string b) => _bldgOn.TryGetValue(b, out var v) && v;
        private bool LevelOn(string l) => _levelOn.TryGetValue(l, out var v) ? v : true;
        private bool TypeOn(string t) => _typeOn.TryGetValue(t, out var v) && v;

        private void ApplyFilters()
        {
            var lab = GameObject.Find("Lab");
            if (lab != null)
            {
                foreach (Transform bldg in lab.transform)
                {
                    bool bOn = BuildingOn(bldg.name);
                    bldg.gameObject.SetActive(bOn);
                    if (!bOn) continue;
                    foreach (Transform lvl in bldg)
                    {
                        bool lOn = LevelOn(lvl.name);
                        lvl.gameObject.SetActive(lOn);
                        if (!lOn) continue;
                        foreach (Transform type in lvl)
                        {
                            bool tOn = TypeOn(type.name);
                            type.gameObject.SetActive(tOn);
                        }
                    }
                }
            }
            ApplyMarkerVisibility();
        }

        private void ApplyMarkerVisibility()
        {
            foreach (var m in _markers)
            {
                if (m == null || m.Go == null) continue;
                bool show = false;
                if (m.Kind == "nodo") show = ShowNodos;
                else if (m.Kind == "apoyo") show = ShowApoyos;
                else if (m.Kind == "axis") show = ShowAxes || GlobalAxes;
                else if (m.Kind == "id") show = ShowIds || GlobalIds;
                else if (m.Kind == "trib") show = ShowTributary;
                if (show) show = BuildingOn(m.Building) && LevelOn(m.Level);
                m.Go.SetActive(show);
            }
        }

        private void RebuildOverlays()
        {
            ClearOverlays();
            BuildMarkers();
            ApplyFilters();
            if (_p4SkyMode) ApplyP4DiagnosticMaterial();
        }

        private void ClearOverlays()
        {
            foreach (var m in _markers) if (m != null && m.Go != null) Destroy(m.Go);
            _markers.Clear();
        }

        // ---------------------------------------------------------------- //
        //  Controles de lote: mostrar/ocultar todo, aislar, restaurar
        // ---------------------------------------------------------------- //
        private void ShowAll()
        {
            _bldgOn["I"] = true; _bldgOn["II"] = true;
            _levelOn.Clear();
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
                _typeOn[t.ToString()] = true;
            RebuildOverlays();
        }

        // Acciones explicitas de integracion visual I/II (solo visualizacion;
        // no cambian la geometria ni el placement, que es placement.json).
        private void ShowBothBuildings()
        {
            _bldgOn["I"] = true; _bldgOn["II"] = true;
            ApplyFilters();
            FrameAll();
        }

        private void ShowOnlyBuilding(string b)
        {
            _bldgOn["I"] = (b == "I"); _bldgOn["II"] = (b == "II");
            ApplyFilters();
            FrameAll();
        }

        private void HideAll()
        {
            _levelOn.Clear();
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
                _typeOn[t.ToString()] = false;
            ShowNodos = ShowApoyos = ShowIds = ShowAxes = ShowTributary = false;
            GlobalIds = GlobalAxes = false;
            _selected = null;
            RebuildOverlays();
        }

        private void RestoreView()
        {
            _p4SkyMode = false;
            _bldgOn["I"] = true; _bldgOn["II"] = true;
            _levelOn.Clear();
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
                _typeOn[t.ToString()] = t != ElemType.Nodos;
            ShowNodos = ShowApoyos = ShowIds = ShowAxes = ShowTributary = false;
            GlobalIds = GlobalAxes = false;
            _selected = null;
            ClearSelectionHighlights();
            RebuildOverlays();
            FrameAll();
        }

        private void IsolateSelected()
        {
            if (_selected == null) return;
            _bldgOn["I"] = false; _bldgOn["II"] = false;
            _bldgOn[_selected.Building] = true;
            _levelOn.Clear();
            foreach (string lv in AllLevelNames()) _levelOn[lv] = false;
            _levelOn[_selected.Level] = true;
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
                _typeOn[t.ToString()] = t == _selected.Type;
            ShowNodos = ShowApoyos = ShowIds = ShowAxes = ShowTributary = false;
            RebuildOverlays();
            FrameAll();
        }

        private static string[] AllLevelNames() =>
            new[] { "CP1S","P1","P2","P3","P4","EII_CP1S","EII_CP1","EII_CP2","EII_CP3","EII_CP4" };

        // ---------------------------------------------------------------- //
        //  Marcadores: nodos / apoyos / ejes / ids / tributaria
        // ---------------------------------------------------------------- //
        private void BuildMarkers()
        {
            if (Model == null) return;
            var lab = GameObject.Find("Lab");
            if (lab == null) return;

            foreach (var e in Model.Elements)
            {
                if (e.Type != ElemType.Columnas) continue;

                // NODO (esfera amarilla) en el extremo base de la columna.
                // Transformacion COMUN: placement + com(u,v,cota) (ver LabLoader).
                if (ShowNodos)
                {
                    var s = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    s.transform.localScale = Vector3.one * 0.25f;
                    s.transform.position = WorldPoint(e.Building, e.P0);
                    s.transform.SetParent(lab.transform, false);
                    var r = s.GetComponent<Renderer>();
                    var nm = new Material(Shader.Find("Standard")) { color = new Color(1f, 0.84f, 0f) };
                    r.sharedMaterial = nm;
                    s.name = "NODO_" + e.Id;
                    _markers.Add(new Marker(s, e.Building, e.Level, "nodo"));
                }

                // APOYO (cubo verde) en el nivel de base documentado.
                // Edificio I: ademas de las columnas reales del nivel base (CP1S),
                // se dibuja el apoyo en las columnas P1 del sector L_EI_CP1_D_INF_I_Ip
                // (u=40/45, v=16.15/8.9): su extremo inferior esta fijado 6DOF en
                // z=CP1S (-4.01 m) por la hipotesis de cimentacion del modelo FE
                // (los tramos col_*_base_P1 llevan reaccion y desplazamiento nulo).
                bool esBase = e.Level == "CP1S" || e.Level == "EII_CP1S";
                if (!esBase && e.Building == "I" && e.Level == "P1")
                {
                    // P0 = Vector3(u, baseY, v): P0.x = u, P0.z = v, P0.y = cota base.
                    float u = e.P0.x;
                    float v = e.P0.z;
                    bool enSector = (Mathf.Abs(u - 40.0f) < 0.011f && (Mathf.Abs(v - 8.9f) < 0.011f || Mathf.Abs(v - 16.15f) < 0.011f)) ||
                                    (Mathf.Abs(u - 45.0f) < 0.011f && (Mathf.Abs(v - 8.9f) < 0.011f || Mathf.Abs(v - 16.15f) < 0.011f));
                    esBase = enSector && e.P0.y < -0.04f + 0.001f; // extremo en cota base P1 (-4.01)
                }
                if (ShowApoyos && esBase)
                {
                    var s = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    s.transform.localScale = new Vector3(1.1f, 0.15f, 1.1f);
                    s.transform.position = WorldPoint(e.Building, e.P0) + Vector3.down * 0.1f;
                    s.transform.SetParent(lab.transform, false);
                    var r = s.GetComponent<Renderer>();
                    var am = new Material(Shader.Find("Standard")) { color = new Color(0.1f, 0.6f, 0.2f) };
                    r.sharedMaterial = am;
                    s.name = "APOYO_" + e.Id;
                    _markers.Add(new Marker(s, e.Building, e.Level, "apoyo"));
                }
            }

            // IDs y ejes: para el seleccionado (o todos si la opcion global esta activa)
            if (ShowIds || GlobalIds || ShowAxes || GlobalAxes)
            {
                bool processId = ShowIds || GlobalIds;
                bool processAxis = ShowAxes || GlobalAxes;
                if (GlobalIds || GlobalAxes)
                {
                    foreach (var e in Model.Elements)
                    {
                        if (e.Id.EndsWith("_DIAF")) continue;
                        if (processId) BuildIdMarker(lab, e);
                        if (processAxis) BuildLocalAxes(lab, e, e.Building, e.Level);
                    }
                }
                else if (_selected != null)
                {
                    if (processId && !_selected.Id.EndsWith("_DIAF")) BuildIdMarker(lab, _selected);
                    if (processAxis && !_selected.Id.EndsWith("_DIAF")) BuildLocalAxes(lab, _selected, _selected.Building, _selected.Level);
                }
            }

            // Area tributaria de la viga/muro seleccionado
            if (ShowTributary && _selected != null &&
                (_selected.Type == ElemType.Vigas || _selected.Type == ElemType.Muros))
            {
                BuildTributaryMarker(lab, _selected);
            }
        }

        /// <summary>World model = placement del edificio + com(u,v,cota) local.
        /// Usa EXACTAMENTE la misma transformacion que los builders de geometria
        /// (unica fuente en LabLoader), aplicada una sola vez.</summary>
        private Vector3 WorldPoint(string building, Vector3 localUnity)
        {
            if (_loader != null) return _loader.ToWorldModel(building, localUnity.x, localUnity.y, localUnity.z);
            return localUnity;
        }

        private void BuildIdMarker(GameObject lab, ElementRef e)
        {
            string name = "ID_" + e.Id;
            foreach (var m in _markers) if (m.Go != null && m.Go.name == name) return;
            var go = new GameObject(name);
            go.transform.SetParent(lab.transform, false);
            var tm = go.AddComponent<TextMesh>();
            tm.text = e.Id;
            tm.characterSize = 0.1f;
            tm.fontSize = 40;
            Vector3 lp = e.Type == ElemType.Columnas ? e.P0 : (e.P0 + e.P1) * 0.5f;
            if (e.Type == ElemType.Losas) lp = e.P0;
            tm.transform.position = WorldPoint(e.Building, lp) + Vector3.up * 0.4f;
            var tr = go.AddComponent<ElementRef>();
            tr.Id = e.Id; tr.Building = e.Building; tr.Level = e.Level; tr.Type = e.Type;
            _markers.Add(new Marker(go, e.Building, e.Level, "id"));
        }

        private void BuildLocalAxes(GameObject lab, ElementRef e, string building, string level)
        {
            Vector3 localOrigin = e.Type == ElemType.Columnas ? e.P0 : (e.P0 + e.P1) * 0.5f;
            Vector3 origin = WorldPoint(building, localOrigin);
            Vector3 along = e.P1 - e.P0;   // direccion/invariante al traslacion
            Vector3 dir = along.magnitude > 1e-6f ? along.normalized : Vector3.up;
            float len = 1.2f;
            AddAxisLine(lab, origin, dir * len, Color.red, "AXISX_" + e.Id, building, level);
            AddAxisLine(lab, origin, Vector3.up * len, Color.green, "AXISY_" + e.Id, building, level);
            Vector3 n = Vector3.Cross(dir, Vector3.up);
            if (n.magnitude < 1e-6f) n = Vector3.forward; else n.Normalize();
            AddAxisLine(lab, origin, n * len, Color.blue, "AXISZ_" + e.Id, building, level);
        }

        private void AddAxisLine(GameObject parent, Vector3 a, Vector3 disp, Color c, string name,
                                 string building, string level)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent.transform, false);
            var lr = go.AddComponent<LineRenderer>();
            lr.positionCount = 2;
            lr.SetPosition(0, a);
            lr.SetPosition(1, a + disp);
            lr.startWidth = lr.endWidth = 0.05f;
            lr.material = new Material(Shader.Find("Standard")) { color = c };
            _markers.Add(new Marker(go, building, level, "axis"));
        }

        private void BuildTributaryMarker(GameObject lab, ElementRef e)
        {
            var regions = e.TribRegions;
            bool hasGeo = regions != null && regions.Count > 0;

            // Edificio II: sin reparto tributario real (no se reutiliza nada del I).
            if (e.Building == "II")
            {
                var tf = new GameObject("TRIB_" + e.Id);
                tf.transform.SetParent(lab.transform, false);
                var tm = tf.AddComponent<TextMesh>();
                tm.text = "No disponible: Edificio II sin reparto tributario real";
                tm.characterSize = 0.1f; tm.fontSize = 34;
                tm.color = new Color(0.85f, 0.55f, 0.2f);
                tm.transform.position = WorldPoint(e.Building, (e.P0 + e.P1) * 0.5f) + Vector3.up * 0.6f;
                _markers.Add(new Marker(tf, e.Building, e.Level, "trib"));
                return;
            }

            // Sin geometria tributaria: NO se dibuja rectangulo (nada inventado).
            if (!hasGeo)
            {
                var tf = new GameObject("TRIB_" + e.Id);
                tf.transform.SetParent(lab.transform, false);
                var tm = tf.AddComponent<TextMesh>();
                tm.text = "Area tributaria no disponible";
                tm.characterSize = 0.1f; tm.fontSize = 34;
                tm.color = new Color(0.6f, 0.6f, 0.6f);
                tm.transform.position = WorldPoint(e.Building, (e.P0 + e.P1) * 0.5f) + Vector3.up * 0.6f;
                _markers.Add(new Marker(tf, e.Building, e.Level, "trib"));
                return;
            }

            // Dibujar TODAS las celdas (porciones) reales del reparto geometrico del
            // Edificio I, transformadas con la misma funcion central del edificio y
            // colocadas en la cota de su losa con un pequeno offset solo visual.
            var mat = MakeTransparentMat(new Color(0.30f, 0.85f, 0.45f, 0.45f));
            int idx = 0;
            foreach (var reg in regions)
            {
                if (reg.Points == null || reg.Points.Count < 3) continue;
                var world = new List<Vector3>();
                foreach (var p in reg.Points)
                    world.Add(WorldPoint(e.Building, p) + Vector3.up * 0.06f);
                var mesh = LabLoader.TribRegionMesh(world, world.Count > 0 ? world[0].y : 0f, 0.05f);
                if (mesh == null || mesh.vertexCount == 0) continue;
                var go = new GameObject("TRIBCELL_" + e.Id + "_" + (idx++));
                go.transform.SetParent(lab.transform, false);
                var mf = go.AddComponent<MeshFilter>();
                mf.sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = mat;
                _markers.Add(new Marker(go, e.Building, e.Level, "trib"));
            }
        }

        // ---------------------------------------------------------------- //
        //  Seleccion
        // ---------------------------------------------------------------- //
        void Update()
        {
            if (Input.GetMouseButtonDown(0) && !_draggingUi)
            {
                ElementRef hit = RaycastPick();
                if (hit != null) Select(hit);
            }
        }

        private ElementRef RaycastPick()
        {
            if (Camera.main == null) return null;
            var ray = Camera.main.ScreenPointToRay(Input.mousePosition);
            if (Physics.Raycast(ray, out var hit, 2000f))
                return hit.collider.GetComponent<ElementRef>();
            return null;
        }

        private void Select(ElementRef e)
        {
            ClearSelectionHighlights();
            _selected = e;
            if (e != null)
            {
                var r = e.GetComponent<Renderer>();
                if (r != null)
                {
                    Color c = r.sharedMaterial != null ? r.sharedMaterial.color : Color.white;
                    r.material.color = Color.Lerp(c, Color.white, 0.6f);
                    r.material.EnableKeyword("_EMISSION");
                    r.material.SetColor("_EmissionColor", c * 0.6f);
                }
            }
            if (ShowAxes || ShowIds || ShowTributary || GlobalAxes || GlobalIds) RebuildOverlays();
        }

        private void ClearSelectionHighlights()
        {
            if (Model == null) return;
            Material p4Diag = null;
            if (_p4SkyMode)
                p4Diag = new Material(Shader.Find("Unlit/Color")) { color = HexColor(P4_DIAG_HEX) };
            foreach (var e in Model.Elements)
            {
                var r = e.GetComponent<Renderer>();
                if (r == null) continue;
                if (_p4SkyMode && e.Type == ElemType.Losas &&
                    (e.Level == "P4" || e.Level == "EII_CP4"))
                    r.material = p4Diag;
                else
                    r.material = new Material(Shader.Find("Standard")) { color = ColorFor(e) };
            }
        }

        private Color ColorFor(ElementRef e)
        {
            if (e.State == ValState.Pendiente) return new Color(1f, 0.666f, 0f);
            switch (e.Type)
            {
                case ElemType.Vigas: return new Color(0.9f, 0.49f, 0.13f);
                case ElemType.Columnas: return new Color(0.2f, 0.6f, 0.86f);
                case ElemType.Muros: return new Color(0.58f, 0.65f, 0.65f);
                case ElemType.Diafragma: return new Color(0.5f, 0.62f, 1f); // contorno diferenciado
                case ElemType.RefPendientes: return HexColor("#9B59B6");    // marcador de referencia
                default: return new Color(0.75f, 0.75f, 0.75f);
            }
        }

        // ---------------------------------------------------------------- //
        //  Camara
        // ---------------------------------------------------------------- //
        public void FrameAll()
        {
            if (Cam == null) return;
            var lab = GameObject.Find("Lab");
            var all = new List<Renderer>();
            if (lab != null) foreach (var r in lab.GetComponentsInChildren<Renderer>()) all.Add(r);
            if (all.Count == 0) return;
            Bounds b = all[0].bounds;
            foreach (var r in all) b.Encapsulate(r.bounds);
            Cam.FrameAll(b);
        }
        public void ViewTop() => Cam?.SetViewTop();
        public void ViewIso() => Cam?.SetViewIso();

        // ---------------------------------------------------------------- //
        //  Modo cielo P4: aísla losas de P4/CP4 con material de diagnóstico
        // ---------------------------------------------------------------- //
        private void EnterP4SkyMode()
        {
            _p4SkyMode = true;
            _levelOn.Clear();
            foreach (string lv in AllLevelNames()) _levelOn[lv] = false;
            _levelOn["P4"] = true;
            _levelOn["EII_CP4"] = true;
            _typeOn.Clear();
            // Vista aislada P4: ademas de losas, se muestran vigas/columnas/muros para
            // comprobar el alero norte (0.05 m) y los encuentros viga-columna de la
            // candidata con grid +0.18 m en v. Se excluyen nodos/apoyos (ruido visual).
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
                _typeOn[t.ToString()] =
                    t == ElemType.Losas || t == ElemType.Vigas || t == ElemType.Columnas || t == ElemType.Muros;
            ApplyFilters();
            ApplyP4DiagnosticMaterial();
            FrameP4Level();
        }

        private void ExitP4SkyMode()
        {
            _p4SkyMode = false;
            _levelOn.Clear();
            _typeOn.Clear();
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
                _typeOn[t.ToString()] = t != ElemType.Nodos;
            RebuildOverlays();
        }

        private void ApplyP4DiagnosticMaterial()
        {
            _p4CountI = 0;
            _p4CountII = 0;
            var lab = GameObject.Find("Lab");
            if (lab == null) return;
            var diagMat = new Material(Shader.Find("Unlit/Color")) { color = HexColor(P4_DIAG_HEX) };
            foreach (Transform bldg in lab.transform)
            {
                string bName = bldg.name;
                foreach (Transform lvl in bldg)
                {
                    if (lvl.name != "P4" && lvl.name != "EII_CP4") continue;
                    foreach (Transform typeGroup in lvl)
                    {
                        if (typeGroup.name != ElemType.Losas.ToString()) continue;
                        foreach (Transform slab in typeGroup)
                        {
                            var r = slab.GetComponent<Renderer>();
                            if (r != null) r.sharedMaterial = diagMat;
                            if (bName == "I") _p4CountI++;
                            else if (bName == "II") _p4CountII++;
                        }
                    }
                }
            }
        }

        private void FrameP4Level()
        {
            if (Cam == null) return;
            var lab = GameObject.Find("Lab");
            if (lab == null) return;
            var renderers = new List<Renderer>();
            foreach (Transform bldg in lab.transform)
                foreach (Transform lvl in bldg)
                {
                    if (lvl.name != "P4" && lvl.name != "EII_CP4") continue;
                    foreach (Transform tg in lvl)
                    {
                        if (tg.name != ElemType.Losas.ToString()) continue;
                        renderers.AddRange(tg.GetComponentsInChildren<Renderer>());
                    }
                }
            if (renderers.Count == 0) return;
            Bounds b = renderers[0].bounds;
            foreach (var r in renderers) b.Encapsulate(r.bounds);
            Cam.FrameAll(b);
        }

        private void DrawP4InfoPanel()
        {
            float pw = 340f, ph = 170f;
            GUI.Box(new Rect(Screen.width - pw - 10, 10, pw, ph), "Cielo P4 / CP4");
            GUILayout.BeginArea(new Rect(Screen.width - pw - 4, 36, pw - 12, ph - 30));
            GUILayout.Label("Edificio I — nivel P4");
            GUILayout.Label("  Cota: 11.83 m   Losas activas: " + _p4CountI);
            GUILayout.Space(4);
            GUILayout.Label("Edificio II — nivel EII_CP4 (CP4)");
            GUILayout.Label("  Cota: 11.83 m   Losas activas: " + _p4CountII);
            GUILayout.Space(6);
            GUILayout.Label("Total: " + (_p4CountI + _p4CountII) + " losas en cielo superior");
            GUILayout.EndArea();
        }

        // ---------------------------------------------------------------- //
        //  UI
        // ---------------------------------------------------------------- //
        void OnGUI()
        {
            GUI.Box(new Rect(10, 10, 230, 12 + 4), "Lab FE viewer");
            int y = 30;
            GUILayout.BeginArea(new Rect(10, y, 230, 700));
            _scroll = GUILayout.BeginScrollView(_scroll, GUI.skin.box, GUILayout.Width(230), GUILayout.Height(560));

            GUILayout.Label("Camara");
            if (GUILayout.Button("Encuadrar todo")) FrameAll();
            if (GUILayout.Button("Vista superior")) ViewTop();
            if (GUILayout.Button("Vista isometrica")) ViewIso();

            GUILayout.Space(6);
            if (!_p4SkyMode)
            {
                if (GUILayout.Button("Mostrar cielo P4")) EnterP4SkyMode();
            }
            else
            {
                if (GUILayout.Button("Restaurar vista completa")) ExitP4SkyMode();
            }

            GUILayout.Space(6);
            GUILayout.Label("Controles de lote");
            if (GUILayout.Button("Mostrar todo")) ShowAll();
            if (GUILayout.Button("Ocultar todo")) HideAll();
            if (GUILayout.Button("Restaurar filtros")) RestoreView();
            if (GUILayout.Button("Aislar seleccionado")) IsolateSelected();

            GUILayout.Space(6);
            GUILayout.Label("Edificios");
            foreach (var b in new[] { "I", "II" })
            {
                bool bOn = BuildingOn(b);
                bool nv = GUILayout.Toggle(bOn, "Edificio " + b);
                if (nv != bOn) { _bldgOn[b] = nv; ApplyFilters(); }
            }
            if (GUILayout.Button("Mostrar ambos edificios")) { ShowBothBuildings(); }
            if (GUILayout.Button("Solo Edificio I")) { ShowOnlyBuilding("I"); }
            if (GUILayout.Button("Solo Edificio II")) { ShowOnlyBuilding("II"); }
            GUILayout.Space(4);
            bool di = GUILayout.Toggle(_showIntegrationDiag, "Diagnostico integracion (junta D-D'/bbox)");
            if (di != _showIntegrationDiag) { _showIntegrationDiag = di; }

            GUILayout.Space(6);
            GUILayout.Label("Solo nivel (Edificio I)");
            if (GUILayout.Button("Todos los niveles")) { SetLevelAll(true); ApplyFilters(); }
            foreach (var lv in new[] { "CP1S", "P1", "P2", "P3", "P4" })
            {
                if (GUILayout.Button("Solo " + lv)) { SetLevelsOnly(lv); ApplyFilters(); }
            }

            GUILayout.Space(6);
            GUILayout.Label("Tipos de elemento");
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
            {
                string key = t.ToString();
                bool tOn = TypeOn(key);
                bool nv = GUILayout.Toggle(tOn, SpanishType(t));
                if (nv != tOn) { _typeOn[key] = nv; ApplyFilters(); }
            }

            GUILayout.Space(6);
            GUILayout.Label("Superpuestos");
            bool nn = GUILayout.Toggle(ShowNodos, "Nodos");
            if (nn != ShowNodos) { ShowNodos = nn; RebuildOverlays(); }
            bool aa = GUILayout.Toggle(ShowApoyos, "Apoyos de base");
            if (aa != ShowApoyos) { ShowApoyos = aa; RebuildOverlays(); }
            bool ids = GUILayout.Toggle(ShowIds, "IDs (seleccionado)");
            if (ids != ShowIds) { ShowIds = ids; RebuildOverlays(); }
            bool gids = GUILayout.Toggle(GlobalIds, "IDs (todos)");
            if (gids != GlobalIds) { GlobalIds = gids; RebuildOverlays(); }
            bool ax = GUILayout.Toggle(ShowAxes, "Ejes locales (seleccionado)");
            if (ax != ShowAxes) { ShowAxes = ax; RebuildOverlays(); }
            bool gax = GUILayout.Toggle(GlobalAxes, "Ejes locales (todos)");
            if (gax != GlobalAxes) { GlobalAxes = gax; RebuildOverlays(); }
            bool tr = GUILayout.Toggle(ShowTributary, "Area tributaria (seleccionado)");
            if (tr != ShowTributary) { ShowTributary = tr; RebuildOverlays(); }

            GUILayout.Space(6);
            if (GUILayout.Button("Aplicar filtros / redes")) RebuildOverlays();
            GUILayout.Space(6);
            if (Model != null)
            {
                GUILayout.Label("Ejecucion I: " + (Model.EiResultSource ?? "-"));
                GUILayout.Label(Model.EiResultNote ?? "");
                if (Model.GlobalPlacementProvisional)
                {
                    GUILayout.Space(4);
                    GUILayout.Label("COLOCACION GLOBAL PROVISIONAL");
                    GUILayout.Label("La separacion EI<->EII es de comparacion,");
                    GUILayout.Label("NO es la junta fisica real (por_correlacionar).");
                }
                if (Model.NoUnionEstructural)
                    GUILayout.Label("Sin union estructural entre edificios.");
                if (!string.IsNullOrEmpty(Model.JuntaId))
                    GUILayout.Label("Junta: " + Model.JuntaId +
                                    (Model.JuntaEstado != null ? " [" + Model.JuntaEstado + "]" : "") +
                                    (Model.JuntaAnchoM != null ? " " + Model.JuntaAnchoM + " m" : ""));
            }

            GUILayout.EndScrollView();
            GUILayout.EndArea();

            if (ShowIds && _selected != null) DrawIdLabel(_selected);
            DrawInspectionPanel();
            DrawP4CandidateNote();
            DrawLegend();
            if (_p4SkyMode) DrawP4InfoPanel();
            if (_showIntegrationDiag) DrawIntegrationDiag();
        }

        // ---------------------------------------------------------------- //
        //  Diagnostico de integracion visual I/II: bbox MUNDIAL real de cada
        //  edificio (renderers en la jerarquia, ya transformados por placement),
        //  separacion minima entre AABBs y deteccion de superposicion indebida.
        //  Solo lectura; no altera el modelo ni el placement.json.
        // ---------------------------------------------------------------- //
        private Bounds WorldBoundsOf(string building)
        {
            var lab = GameObject.Find("Lab");
            if (lab == null) return new Bounds(Vector3.zero, Vector3.zero);
            var bgo = lab.transform.Find(building);
            if (bgo == null) return new Bounds(Vector3.zero, Vector3.zero);
            var rs = bgo.GetComponentsInChildren<Renderer>();
            if (rs == null || rs.Length == 0) return new Bounds(Vector3.zero, Vector3.zero);
            var b = rs[0].bounds;
            for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
            return b;
        }

        private static float AabbDist(Bounds a, Bounds b)
        {
            float dx = Mathf.Max(0f, Mathf.Max(a.min.x - b.max.x, b.min.x - a.max.x));
            float dy = Mathf.Max(0f, Mathf.Max(a.min.y - b.max.y, b.min.y - a.max.y));
            float dz = Mathf.Max(0f, Mathf.Max(a.min.z - b.max.z, b.min.z - a.max.z));
            return Mathf.Sqrt(dx * dx + dy * dy + dz * dz);
        }

        private void DrawIntegrationDiag()
        {
            Bounds bi = WorldBoundsOf("I");
            Bounds bii = WorldBoundsOf("II");
            bool overlap = bi.size.sqrMagnitude > 0f && bii.size.sqrMagnitude > 0f && bi.Intersects(bii);
            float dist = AabbDist(bi, bii);
            // Junta D-D': caras planas x=const (paralelas). Cara D (EI, oeste) = renderer mas
            // occidental (muro M_EI_CP1S_001, u=-0.450227; es el limite del modelo). Cara D'
            // (EII, este) = renderer mas oriental (losas L_E1/L_EM/L_S6, x=27.85). Medida
            // cara-a-cara, NO es la distancia AABB general.
            float carD = bi.min.x;
            float carDp = bii.max.x;
            float junta = carD - carDp;

            GUI.Box(new Rect(Screen.width - 340, Screen.height - 430, 330, 420), "Diagnostico integracion I/II");
            GUILayout.BeginArea(new Rect(Screen.width - 334, Screen.height - 394, 318, 382));
            GUILayout.Label("Junta D-D' (cara a cara): " + junta.ToString("0.###") + " m");
            GUILayout.Label("  cara D  (EI, oeste) x=" + carD.ToString("0.###") + " (mundo)");
            GUILayout.Label("  cara D' (EII, este) x=" + carDp.ToString("0.###") + " (mundo)");
            GUILayout.Label("  (caras x=const paralelas; placement.json unico)");
            GUILayout.Space(4);
            GUILayout.Label("Separacion minima AABB: " + dist.ToString("0.###") + " m");
            GUILayout.Label("  (referencia; NO sustituye la medicion de la junta D-D').");
            GUILayout.Label("Superposicion indebida: " + (overlap ? "SI" : "NO"));
            GUILayout.Space(4);
            GUILayout.Label("Placement unico: placement.json");
            if (Model != null)
            {
                GUILayout.Label("I  pos: " + Vec(Model.Placement.ContainsKey("I") ? Model.Placement["I"] : Vector3.zero));
                GUILayout.Label("II pos: " + Vec(Model.Placement.ContainsKey("II") ? Model.Placement["II"] : Vector3.zero));
            }
            GUILayout.Space(4);
            GUILayout.Label("Contornos/diafragmas en espacio local");
            GUILayout.Label("(useWorldSpace=false); marcadores con");
            GUILayout.Label("ToWorldModel = placement + com().");
            GUILayout.EndArea();
        }

        private static string Vec(Vector3 v) =>
            "(" + v.x.ToString("0.###") + ", " + v.y.ToString("0.###") + ", " + v.z.ToString("0.###") + ")";

        // Nota persistente: identifica P4 como candidata con traslacion de vigas +0.18 m.
        private void DrawP4CandidateNote()
        {
            GUI.backgroundColor = new Color(1f, 0.97f, 0.85f);
            GUI.Box(new Rect(10, Screen.height - 118, 250, 100), "Candidata P4 - vigas +0.18 m");
            GUILayout.BeginArea(new Rect(16, Screen.height - 100, 238, 80));
            GUILayout.Label("Grid de vigas trasladado +0.18 m en v");
            GUILayout.Label("(fuente 2017_67-103.dxf; ejes 0.18/9.08/16.33).");
            GUILayout.Label("Areas tributarias y resultados FE previos");
            GUILayout.Label("NO estan revalidados para esta candidata.");
            GUILayout.EndArea();
            GUI.backgroundColor = Color.white;
        }

        private void DrawLegend()
        {
            GUI.Box(new Rect(Screen.width - 340, Screen.height - 210, 330, 200), "Leyenda");
            GUILayout.BeginArea(new Rect(Screen.width - 334, Screen.height - 176, 318, 168));
            LegendRow(new Color(0.9f, 0.49f, 0.13f), "Vigas");
            LegendRow(new Color(0.2f, 0.6f, 0.86f), "Columnas");
            LegendRow(new Color(0.58f, 0.65f, 0.65f), "Muros equivalentes");
            LegendRow(new Color(0.75f, 0.75f, 0.75f), "Losas");
            LegendRow(new Color(0.5f, 0.62f, 1f), "Diafragma rigido");
            LegendRow(new Color(0.9f, 0.29f, 0.24f), "Aberturas");
            LegendRow(new Color(1f, 0.84f, 0f), "Nodo");
            LegendRow(new Color(0.1f, 0.6f, 0.2f), "Apoyo de base");
            LegendRow(new Color(1f, 0.666f, 0f), "Pendiente (sin respaldo)");
            LegendRow(new Color(0.75f, 0.75f, 0.75f), "Confirmado / Hipotetico (EII)");
            LegendRow(new Color(0.61f, 0.35f, 0.71f), "Referencia pendiente (RLE-TEXTO-1/P.M.I.)");
            GUILayout.EndArea();
        }

        private void LegendRow(Color c, string label)
        {
            GUILayout.BeginHorizontal();
            var box = new GUIStyle("label") { richText = true };
            GUILayout.Label("<color=#" + ColorUtility.ToHtmlStringRGB(c) + ">■</color> " + label, box);
            GUILayout.EndHorizontal();
        }

        private static string SpanishType(ElemType t)
        {
            switch (t)
            {
                case ElemType.Losas: return "Losas";
                case ElemType.Vigas: return "Vigas";
                case ElemType.Columnas: return "Columnas";
                case ElemType.Muros: return "Muros";
                case ElemType.Diafragma: return "Diafragmas";
                case ElemType.Abertura: return "Aberturas";
                case ElemType.Nodos: return "Nodos";
                case ElemType.RefPendientes: return "Referencias pendientes";
            }
            return t.ToString();
        }

        private void DrawIdLabel(ElementRef e)
        {
            if (Camera.main == null) return;
            Vector3 wp = (e.Type == ElemType.Columnas) ? e.P0 : (e.P0 + e.P1) * 0.5f;
            if (e.Type == ElemType.Losas) wp = e.P0;
            Vector3 sp = Camera.main.WorldToScreenPoint(wp);
            if (sp.z < 0) return;
            var rect = new Rect(sp.x, Screen.height - sp.y, 200, 20);
            GUI.Label(rect, e.Id);
        }

        private void DrawInspectionPanel()
        {
            if (_selected == null) return;
            var r = _selected;
            GUI.Box(new Rect(Screen.width - 340, 10, 330, 300), "Inspeccion");
            GUILayout.BeginArea(new Rect(Screen.width - 334, 50, 318, 250));
            _inspScroll = GUILayout.BeginScrollView(_inspScroll, GUIStyle.none, GUI.skin.verticalScrollbar);

            GUILayout.Label("Edificio: " + r.Building + "  Nivel: " + r.Level);
            GUILayout.Label("Tipo: " + SpanishType(r.Type));
            if (r.Type != ElemType.Diafragma)
                GUILayout.Label("Cota base: " + r.P0.y.ToString("0.###") + " m");
            GUILayout.Label("ID original: " + r.Id);
            if (r.Type == ElemType.Losas)
            {
                GUILayout.Label("Limite u [" + r.UVBounds.x.ToString("0.###") + ", "
                                + r.UVBounds.y.ToString("0.###") + "] m");
                GUILayout.Label("Limite v [" + r.UVBounds.z.ToString("0.###") + ", "
                                + r.UVBounds.w.ToString("0.###") + "] m");
            }
            GUILayout.Label("elementTag: no disponible");
            // Aviso de CANDIDATA P4 (grid de vigas trasladado +0.18 m en v): los resultados y
            // areas tributarias FE previos corresponden a la geometria anterior y NO estan
            // revalidados para esta candidata. Se muestra para toda viga P4 (el grid corregido).
            if (r.Building == "I" && r.Level == "P4" && r.Type == ElemType.Vigas)
            {
                GUI.color = new Color(0.72f, 0.55f, 0.05f);
                GUILayout.Space(6);
                GUILayout.Label("CANDIDATA P4 (vigas +0.18 m en v):");
                GUILayout.Label("Areas tributarias y resultados FE previos");
                GUILayout.Label("corresponden a la geometria ANTERIOR y NO");
                GUILayout.Label("estan revalidados para esta viga trasladada.");
                GUI.color = Color.white;
            }
            if (!string.IsNullOrEmpty(r.Seccion)) GUILayout.Label("Seccion: " + r.Seccion);
            if (r.SectionW > 0) GUILayout.Label("Seccion: " + r.SectionW + " x " + r.SectionH + " m");
            if (r.Type == ElemType.Columnas) GUILayout.Label("Grid: " + (r.Grid ?? "-"));
            if (r.Type == ElemType.Losas)
            {
                GUILayout.Label("Espesor: " + r.Espesor + " m");
                if (r.Aberturas != null && r.Aberturas.Count > 0) GUILayout.Label("Aberturas: " + r.Aberturas.Count);
                GUILayout.Label("Transferencia: " + (r.TipoTransferencia ?? "n/d"));
            }
            if (r.Type == ElemType.Vigas || r.Type == ElemType.Muros)
                GUILayout.Label("Recibe losa: " + r.RecibeLosa);
            GUILayout.Label("Estado: " + StateName(r.State));
            if (!string.IsNullOrEmpty(r.Grid)) GUILayout.Label("Eje: " + r.Grid);

            // tributaria (vigas y muros receptores)
            bool esReceptor = r.Type == ElemType.Vigas || r.Type == ElemType.Muros;
            bool hasGeo = r.TribRegions != null && r.TribRegions.Count > 0;
            if (esReceptor && r.Building == "II")
            {
                GUILayout.Space(6);
                GUILayout.Label("No disponible: Edificio II sin reparto tributario real");
                GUILayout.Label("(no se reutilizan areas del I ni el ensayo unitario de 1 kPa)");
            }
            else if (esReceptor && r.HasTributary && hasGeo)
            {
                GUILayout.Space(6);
                GUILayout.Label("--- AREA TRIBUTARIA (reparto real) ---");
                GUILayout.Label("Viga/Muro: " + r.Id);
                GUILayout.Label("Area total: " + r.TribAreaM2.ToString("0.###") + " m2  |  Carga: "
                                + r.TribCargaKN.ToString("0.###") + " kN");
                GUILayout.Label("Ejecucion: " + r.TribSource + "  |  Caso: " + r.TribCase);
                GUILayout.Label("n porciones: " + r.TribRegions.Count);
                var porLosa = new Dictionary<string, double>();
                foreach (var rr in r.TribRegions)
                    if (!string.IsNullOrEmpty(rr.Losa))
                        porLosa[rr.Losa] = porLosa.ContainsKey(rr.Losa) ? porLosa[rr.Losa] + rr.AreaM2 : rr.AreaM2;
                GUILayout.Label("Losas contribuyentes:");
                foreach (var kv in porLosa)
                    GUILayout.Label("  " + kv.Key + "  (" + kv.Value.ToString("0.###") + " m2)");
                GUILayout.Label("ADVERTENCIA: representacion academica provisional del");
                GUILayout.Label("reparto geometrico; no es dato de diseno.");
            }
            else if (esReceptor && r.HasTributary)
            {
                GUILayout.Space(6);
                GUILayout.Label("Area tributaria no disponible");
                GUILayout.Label("(hay area total pero sin geometria de region; no se dibuja)");
            }
            else if (esReceptor)
            {
                GUILayout.Space(6);
                GUILayout.Label("Area tributaria no disponible (sin dato)");
            }

            GUILayout.EndScrollView();
            GUILayout.EndArea();
        }

        private static string StateName(ValState s)
        {
            switch (s)
            {
                case ValState.Confirmado: return "confirmado";
                case ValState.Hipotetico: return "hipotetico";
                default: return "pendiente";
            }
        }

        private static Color HexColor(string hex)
        {
            Color c; ColorUtility.TryParseHtmlString(hex, out c); return c;
        }

        private Material MakeTransparentMat(Color c)
        {
            var m = new Material(Shader.Find("Standard"));
            if (m.shader == null) m.shader = Shader.Find("Unlit/Color");
            m.color = c;
            m.SetFloat("_Mode", 3);
            m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            m.SetInt("_ZWrite", 0);
            m.DisableKeyword("_ALPHATEST_ON");
            m.EnableKeyword("_ALPHABLEND_ON");
            m.renderQueue = 3000;
            return m;
        }

        // allow click on elements while dragging the cursor in UI
        private void OnGUIEnter()
        {
            if (Event.current != null && (Event.current.type == EventType.MouseDown || Event.current.type == EventType.MouseDrag))
                _draggingUi = true;
            if (Event.current != null && Event.current.type == EventType.MouseUp)
                _draggingUi = false;
        }

        // ---------------------------------------------------------------- //
        //  API publica para la verificacion de aceptacion (EditorTools)
        // ---------------------------------------------------------------- //
        /// <summary>Cuenta los Renderers activos visibles de un tipo de elemento
        /// (recorre la jerarquia respetando edificio/nivel/tipo activos).</summary>
        public int CountTypeRenderers(string typeName)
        {
            int n = 0;
            var lab = GameObject.Find("Lab");
            if (lab == null) return 0;
            foreach (Transform bldg in lab.transform)
            {
                if (!BuildingOn(bldg.name)) continue;
                foreach (Transform lvl in bldg)
                {
                    if (!LevelOn(lvl.name)) continue;
                    foreach (Transform type in lvl)
                    {
                        if (type.name != typeName) continue;
                        foreach (Transform child in type)
                        {
                            var r = child.GetComponent<Renderer>();
                            if (r != null && r.enabled && child.gameObject.activeInHierarchy) n++;
                        }
                    }
                }
            }
            return n;
        }

        /// <summary>Cuenta marcadores superpuestos activos de un tipo ("nodo","apoyo",
        /// "id","axis","trib") que se muestran realmente (respetando filtros).</summary>
        public int CountMarkerRenderers(string kind)
        {
            int n = 0;
            foreach (var m in _markers)
            {
                if (m == null || m.Go == null) continue;
                if (m.Kind != kind) continue;
                if (!BuildingOn(m.Building) || !LevelOn(m.Level)) continue;
                if (!m.Go.activeInHierarchy) continue;
                var r = m.Go.GetComponent<Renderer>();
                if (r != null && r.enabled) n++;
                else if (m.Go.activeSelf) n++;   // text/line markers
            }
            return n;
        }

        /// <summary>Numero de objetos de un tipo existentes en el modelo (sin filtros).</summary>
        public int TotalInModel(ElemType t)
        {
            if (Model == null) return 0;
            int n = 0;
            foreach (var e in Model.Elements) if (e.Type == t) n++;
            return n;
        }

        public void SetBuilding(string b, bool on) { _bldgOn[b] = on; ApplyFilters(); }
        public void SetType(string t, bool on) { _typeOn[t] = on; ApplyFilters(); }
        public void SetLevelAll(bool on)
        {
            foreach (string lv in AllLevelNames()) _levelOn[lv] = on;
            ApplyFilters();
        }
        public void SetLevelsOnly(params string[] levels)
        {
            foreach (string lv in AllLevelNames()) _levelOn[lv] = false;
            foreach (var lvl in levels) if (!string.IsNullOrEmpty(lvl)) _levelOn[lvl] = true;
            ApplyFilters();
        }
        public void SetOverlay(string kind, bool on)
        {
            if (kind == "nodo") ShowNodos = on;
            else if (kind == "apoyo") ShowApoyos = on;
            else if (kind == "id") ShowIds = on;
            else if (kind == "axis") ShowAxes = on;
            else if (kind == "trib") ShowTributary = on;
            RebuildOverlays();
        }
        public void ShowAllTypes()
        {
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
            {
                _typeOn[t.ToString()] = true;
            }
            ApplyFilters();
        }
        public void HideAllTypes()
        {
            foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
            {
                _typeOn[t.ToString()] = false;
            }
            ApplyFilters();
        }
        public bool SelectId(string id)
        {
            if (Model == null) return false;
            foreach (var e in Model.Elements)
                if (e.Id == id) { Select(e); return true; }
            return false;
        }
        public ElementRef Selected => _selected;
        public bool IsP4Mode => _p4SkyMode;
    }
}
