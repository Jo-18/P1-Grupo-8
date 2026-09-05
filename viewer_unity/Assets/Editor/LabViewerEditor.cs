using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace LabViewer.EditorTools
{
    /// <summary>
    /// Utilidades de editor: construir la escena principal y verificar la
    /// integridad del paquete de datos (conteos/IDs frente al manifest) sin
    /// necesidad de reproducir. Ejecutables en batch:
    ///   Unity -batchmode -quit -projectPath <viewer> -executeMethod LabViewer.EditorTools.LabViewerEditor.CheckData
    ///   Unity -batchmode -quit -projectPath <viewer> -executeMethod LabViewer.EditorTools.LabViewerEditor.BuildMainScene
    /// </summary>
    // Interactive menu actions must never terminate the user's Editor session.
    internal static class LabViewerExitGuard
    {
        public static void Finish(int code)
        {
            if (Application.isBatchMode) EditorApplication.Exit(code);
            else Debug.Log("[LabViewer] Verificacion terminada (codigo " + code + "). Editor abierto.");
        }
    }

    public static class LabViewerEditor
    {
        const string ScenePath = "Assets/Scenes/Main.unity";

        [MenuItem("LabViewer/Preparar escena principal")]
        public static void BuildMainScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            var cam1 = camGo.AddComponent<Camera>();
            cam1.clearFlags = CameraClearFlags.SolidColor;
            cam1.backgroundColor = new Color(0.15f, 0.17f, 0.20f);
            camGo.AddComponent<AudioListener>();
            camGo.transform.position = new Vector3(30f, 30f, -30f);
            camGo.transform.LookAt(Vector3.zero);

            var sun = new GameObject("Sun");
            var l = sun.AddComponent<Light>();
            l.type = LightType.Directional;
            l.intensity = 1.1f;
            sun.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

            var lab = new GameObject("LabLoader");
            var loader = lab.AddComponent<LabLoader>();
            var viewer = lab.AddComponent<ViewerController>();
            viewer.Cam = camGo.AddComponent<CameraController>();
            viewer.Cam.Target = new GameObject("LabTarget").transform;
            viewer.Cam.Target.position = Vector3.zero;

            EnsureFolders();
            EditorSceneManager.SaveScene(scene, ScenePath, true);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            if (!Application.isBatchMode) EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Debug.Log("Escena principal preparada: " + ScenePath);
        }

        private static void EnsureFolders()
        {
            if (!AssetDatabase.IsValidFolder("Assets/Scenes"))
                AssetDatabase.CreateFolder("Assets", "Scenes");
        }

        /// <summary>
        /// Verifica la integridad del paquete: cada archivo del manifest debe existir,
        /// cada geometry JSON debe contener llaves con conteos coherentes e IDs unicos,
        /// y la tributaria I debe tener receptores. Sin reproducir.
        /// </summary>
        [MenuItem("LabViewer/Verificar datos")]
        public static void CheckData()
        {
            string root = Path.Combine(Application.streamingAssetsPath, "lab_data");
            if (!Directory.Exists(root)) { Debug.LogError("No existe " + root); LabViewerExitGuard.Finish(1); return; }

            bool ok = true;

            // 1) cada archivo declarado en el manifest debe existir
            string manPath = Path.Combine(root, "manifest.json");
            if (!File.Exists(manPath)) { Debug.LogError("Falta manifest.json"); LabViewerExitGuard.Finish(1); return; }
            var manifest = Json.Parse(File.ReadAllText(manPath)) as Dictionary<string, object>;
            var archivos = Json.Arr(manifest, "archivos");
            if (archivos != null)
            {
                foreach (var a in archivos)
                {
                    string rel = a.ToString();
                    string full = Path.Combine(Application.streamingAssetsPath, "lab_data", rel);
                    if (!File.Exists(full)) { Debug.LogError("[Manifest] Falta archivo: " + rel); ok = false; }
                }
            }
            Log("[Manifest] " + (archivos != null ? archivos.Count + " archivos declarados" : "sin archivos"));

            // 2) cada geometry: conteos por tipo e IDs unicos
            var geomFiles = new[]
            {
                ("edificios/I/geometry/CP1S.json"), ("edificios/I/geometry/P1.json"),
                ("edificios/I/geometry/P2.json"), ("edificios/I/geometry/P3.json"), ("edificios/I/geometry/P4.json"),
                ("edificios/II/geometry/EII_CP1S.json"), ("edificios/II/geometry/EII_CP1.json"),
                ("edificios/II/geometry/EII_CP2.json"), ("edificios/II/geometry/EII_CP3.json"), ("edificios/II/geometry/EII_CP4.json"),
            };
            int totalCols = 0, totalVig = 0, totalMuro = 0, totalLosa = 0, totalDiaf = 0, totalAbs = 0;
            var seenIds = new HashSet<string>();
            foreach (var rel in geomFiles)
            {
                string full = Path.Combine(root, rel);
                if (!File.Exists(full)) { Log("[Geom] Falta " + rel); ok = false; continue; }
                var d = Json.Parse(File.ReadAllText(full)) as Dictionary<string, object>;
                int c = Count(d, "columnas"), v = Count(d, "vigas"), m = Count(d, "muros"), l = Count(d, "losas");
                int ab = Count(d, "aberturas_globales");
                totalCols += c; totalVig += v; totalMuro += m; totalLosa += l; totalAbs += ab;
                Log(string.Format("[Geom] {0}: col={1} vig={2} muro={3} losa={4} abert={5}",
                    rel, c, v, m, l, ab));
                foreach (var key in new[] { "columnas", "vigas", "muros", "losas" })
                {
                    var arr = Json.Arr(d, key);
                    if (arr == null) continue;
                    foreach (var it in arr)
                        if (it is Dictionary<string, object> e && Json.Str(e, "id") != null)
                        {
                            string id = Json.Str(e, "id");
                            if (!seenIds.Add(id)) { Log("[Dupe] " + id); ok = false; }
                        }
                }
            }
            Log(string.Format("[Totales] col={0} vig={1} muro={2} losa={3} abert_globales={4}", totalCols, totalVig, totalMuro, totalLosa, totalAbs));
            if (totalVig == 0 || totalMuro == 0 || totalLosa == 0) { LogError("Conteos nulos inesperados"); ok = false; }

            // 3) resultados primera_ejecucion (EI) presente
            string res = Path.Combine(root, "edificios", "I", "results", "primera_ejecucion.json");
            if (!File.Exists(res)) { LogError("Falta resultados EI"); ok = false; }
            else Log("[Resultados] primera_ejecucion OK");

            // 4) tributaria I con receptores
            string tr = Path.Combine(root, "edificios", "I", "tributary", "por_viga.json");
            if (!File.Exists(tr)) { LogError("Falta tributaria I"); ok = false; }
            else
            {
                var td = Json.Parse(File.ReadAllText(tr)) as Dictionary<string, object>;
                int n = 0; double carga = 0;
                if (td != null && td.TryGetValue("por_nivel", out var pn) && pn is Dictionary<string, object> porNivel)
                    foreach (var lvlNode in porNivel)
                        if (lvlNode.Value is List<object> beams)
                        {
                            n += beams.Count;
                            foreach (var b in beams)
                                if (b is Dictionary<string, object> bd)
                                    carga += Json.Num(bd, "carga_total_kN");
                        }
                Log(string.Format("[Tributaria I] receptores={0} cargaTotalG~{1:0.###} kN", n, carga));
                if (n == 0) { LogError("Sin datos tributarios I"); ok = false; }
            }

            Log(ok ? "CHECK DATOS: OK" : "CHECK DATOS: FALLO");
            LabViewerExitGuard.Finish(ok ? 0 : 1);
        }

        private static int Count(Dictionary<string, object> d, string key)
        {
            var a = Json.Arr(d, key);
            return a != null ? a.Count : 0;
        }

        /// <summary>
        /// Ejecuta el camino de construccion real (LabLoader.Load asincrono = el que
        /// usa la escena) y verifica que se crean los elementos y se adjunta la
        /// tributaria. Sin renderizado ni raycast, pero ejercita el codigo runtime.
        /// </summary>
        [MenuItem("LabViewer/Verificar runtime (construccion modelo)")]
        public static void VerifyRuntime()
        {
            var go = new GameObject("RuntimeCheck");
            var loader = go.AddComponent<LabLoader>();
            try
            {
                bool ok = loader.Load();
                var m = loader.Model;
                Log("Runtime load ok=" + ok + " elems=" + (m != null ? m.Elements.Count : -1));
                if (m == null) { LogError("Modelo null"); LabViewerExitGuard.Finish(1); return; }

                int vigas = 0, muros = 0, losas = 0, cols = 0, diaf = 0, abe = 0, trib = 0, hipo = 0, refPed = 0;
                foreach (var e in m.Elements)
                {
                    switch (e.Type)
                    {
                        case ElemType.Vigas: vigas++; break;
                        case ElemType.Muros: muros++; break;
                        case ElemType.Losas: losas++; break;
                        case ElemType.Columnas: cols++; break;
                        case ElemType.Diafragma: diaf++; break;
                        case ElemType.Abertura: abe++; break;
                        case ElemType.RefPendientes: refPed++; break;
                    }
                    if (e.HasTributary) trib++;
                    if (e.State == ValState.Hipotetico) hipo++;
                }
                Log(string.Format("Runtime: col={0} vig={1} muro={2} losa={3} diaf={4} abert={5} conTributaria={6} hipoteticos={7} refPend={8}",
                    cols, vigas, muros, losas, diaf, abe, trib, hipo, refPed));

                bool good = ok && m.Elements.Count > 500 && vigas > 130 && muros > 60
                            && losas > 230 && trib >= 160 && diaf > 230 && cols >= 59;
                // Los 8 registros P.M.I. (solo posicion de rotulo RLE-TEXTO-1, sin geometria)
                // se mantienen como REFERENCIAS PENDIENTES, NO como columnas dibujadas.
                bool refGood = refPed == 8;
                Log(good && refGood ? "RUNTIME CHECK: OK" : "RUNTIME CHECK: FALLO");
                Object.DestroyImmediate(go);
                LabViewerExitGuard.Finish(good && refGood ? 0 : 1);
            }
            catch (System.Exception ex)
            {
                LogError("Runtime exception: " + ex.Message + "\n" + ex.StackTrace);
                Object.DestroyImmediate(go);
                LabViewerExitGuard.Finish(1);
            }
        }

        private static void Log(string s) { Debug.Log("[LabViewer] " + s); }
        private static void LogError(string s) { Debug.LogError("[LabViewer] " + s); }

        /// <summary>
        /// Diagnostico de COORDENADAS del Edificio I: a partir del paquete carga el modelo,
        /// aplica la transformacion comun (placement + com(u,v,cota)) y registra para nodos,
        /// extremos de vigas y columnas: ID, coordenada fuente, local, mundial y residuo de
        /// coincidencia. Escribe QA_COORDENADAS_UNITY_EI.csv y reporta recuentos fuera de rango.
        /// Run: Unity -batchmode -projectPath &lt;viewer&gt; -executeMethod LabViewer.EditorTools.LabViewerEditor.RunEI_CoordinateQA
        /// </summary>
        [MenuItem("LabViewer/QA coordenadas Edificio I (CSV)")]
        public static void RunEI_CoordinateQA()
        {
            var go = new GameObject("EICoordQA");
            var loader = go.AddComponent<LabLoader>();
            try
            {
                bool ok = loader.Load();
                var m = loader.Model;
                if (m == null || !ok) { LogError("No se pudo cargar el modelo."); LabViewerExitGuard.Finish(1); return; }

                string csvPath = System.IO.Path.Combine(
                    new System.IO.DirectoryInfo(Application.dataPath).Parent.FullName,
                    "QA_COORDENADAS_UNITY_EI.csv");

                var sb = new System.Text.StringBuilder();
                sb.AppendLine("tipo,id,nivel,u,v,cota,local_x,local_y,local_z,mundo_x,mundo_y,mundo_z,residual_m");

                int outRangeCol = 0, outRangeBeam = 0, outRangeBeamElev = 0, multiCol = 0;
                double tolerancia = 0.05; // m

                // -- Columnas: intervalos visuales; marcar las que cruzan >1 intervalo o salen del rango [-4.01,11.83]
                foreach (var e in m.Elements)
                {
                    if (e.Building != "I") continue;
                    if (e.Type == ElemType.Columnas)
                    {
                        Vector3 w0 = loader.ToWorldModel("I", e.P0.x, e.P0.y, e.P0.z);
                        Vector3 w1 = loader.ToWorldModel("I", e.P1.x, e.P1.y, e.P1.z);
                        float cotaBase = e.P0.y, cotaTop = e.P1.y;
                        if (cotaBase < -4.01f - 0.001f || cotaTop > 11.83f + 0.001f) outRangeCol++;
                        if (cotaTop - cotaBase > 4.2f) multiCol++;   // > ~3.96+0.1 => atraviesa mas de un entrepiso
                        sb.AppendLine(string.Join(",",
                            "columna", e.Id, e.Level,
                            e.P0.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P0.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            cotaBase.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P0.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            cotaBase.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P0.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            w0.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            w0.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            w0.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            "0.000"));
                        if (cotaBase <= -4.01f + 0.001f)
                            sb.AppendLine(string.Join(",",
                                "nodo", e.Id, e.Level,
                                e.P0.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                                e.P0.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                                cotaBase.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                                e.P0.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                                cotaBase.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                                e.P0.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                                w0.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                                w0.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                                w0.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                                "0.000"));
                    }
                    else if (e.Type == ElemType.Vigas)
                    {
                        Vector3 w0 = loader.ToWorldModel("I", e.P0.x, e.P0.y, e.P0.z);
                        Vector3 w1 = loader.ToWorldModel("I", e.P1.x, e.P1.y, e.P1.z);
                        float expected = LevelCota(e.Level);
                        float elev = (e.P0.y + e.P1.y) * 0.5f;
                        if (Mathf.Abs(elev - expected) > tolerancia) outRangeBeamElev++;
                        // fuera de limites en planta del nivel: |u|<1e3 y 0..~55 (aprox EI)
                        float maxPlan = 60f;
                        if (Mathf.Abs(e.P0.x) > maxPlan || Mathf.Abs(e.P0.z) > maxPlan) outRangeBeam++;
                        sb.AppendLine(string.Join(",",
                            "viga_inicio", e.Id, e.Level,
                            e.P0.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P0.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P0.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P0.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P0.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P0.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            w0.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            w0.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            w0.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            "0.000"));
                        sb.AppendLine(string.Join(",",
                            "viga_fin", e.Id, e.Level,
                            e.P1.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P1.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P1.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P1.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P1.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            e.P1.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            w1.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            w1.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            w1.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            "0.000"));
                    }
                }

                // -- Residuo de coincidencia: cada extremo de viga frente a la columna/base mas cercana de su nivel
                var cols = new List<Vector3>();
                foreach (var e in m.Elements)
                    if (e.Building == "I" && e.Type == ElemType.Columnas)
                        cols.Add(loader.ToWorldModel("I", e.P0.x, e.P0.y, e.P0.z));

                foreach (var e in m.Elements)
                {
                    if (e.Building != "I" || e.Type != ElemType.Vigas) continue;
                    for (int k = 0; k < 2; k++)
                    {
                        Vector3 sweep = k == 0 ? e.P0 : e.P1;
                        Vector3 wEnd = loader.ToWorldModel("I", sweep.x, sweep.y, sweep.z);
                        float best = float.MaxValue;
                        foreach (var c in cols) best = Mathf.Min(best, Vector3.Distance(wEnd, c));
                        sb.AppendLine(string.Join(",",
                            "viga_residual", e.Id, e.Level,
                            sweep.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            sweep.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            sweep.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            wEnd.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            sweep.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            wEnd.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            wEnd.x.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            wEnd.y.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            wEnd.z.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture),
                            best.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture)));
                    }
                }

                System.IO.File.WriteAllText(csvPath, sb.ToString(), System.Text.Encoding.UTF8);
                Log("CSV escrito: " + csvPath);
                Log(string.Format("EI QA: columnasFueraRango[-4.01,11.83]={0} multiIntervalo(altura>{1:0.##}m)={2} vigasFueraPlanta={3} vigasElevacionFuera={4}",
                    outRangeCol, 4.2f, multiCol, outRangeBeam, outRangeBeamElev));

                bool pass = outRangeCol == 0 && multiCol == 0 && outRangeBeam == 0 && outRangeBeamElev == 0;
                Log(pass ? "EI QA COORDENADAS: OK" : "EI QA COORDENADAS: FALLO");
                Object.DestroyImmediate(go);
                LabViewerExitGuard.Finish(pass ? 0 : 1);
            }
            catch (System.Exception ex)
            {
                LogError("EI QA exception: " + ex.Message + "\n" + ex.StackTrace);
                Object.DestroyImmediate(go);
                LabViewerExitGuard.Finish(1);
            }
        }

        private static float LevelCota(string lvl)
        {
            switch (lvl)
            {
                case "P1": return -0.05f;
                case "P2": return 3.91f;
                case "P3": return 7.87f;
                case "P4": return 11.83f;
                case "CP1S": return -4.01f;
            }
            return 0f;
        }
    }

    /// <summary>
    /// Ejecuta la escena en modo play unas pocas frames (Update/Start/OnGUI/rebuild)
    /// para detectar excepciones de runtime, y sale con codigo 0/1. Best effort en
    /// batch; la verificacion visual se hace abriendo el proyecto en el Editor.
    /// Uso: Unity -batchmode -quit -projectPath &lt;viewer&gt; -executeMethod LabViewer.EditorTools.PlaySmoke.Run
    /// </summary>
    public static class PlaySmoke
    {
        private const string ScenePath = "Assets/Scenes/Main.unity";
        private const string RequestedKey = "LabViewer.PlaySmoke.Requested";
        private static double _t0;
        private static bool _reported;
        private static readonly List<string> _runtimeErrors = new List<string>();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void OnPlayStarted()
        {
            // Only explicit smoke tests may register the timed callback.
            if (!SessionState.GetBool(RequestedKey, false)) return;
            Application.logMessageReceived -= LogHandler;
            Application.logMessageReceived += LogHandler;
            _reported = false;
            _runtimeErrors.Clear();
            _t0 = EditorApplication.timeSinceStartup;
            EditorApplication.update -= Tick;
            EditorApplication.update += Tick;
        }

        private static void Tick()
        {
            if (!EditorApplication.isPlaying)
            {
                EditorApplication.update -= Tick;
                Application.logMessageReceived -= LogHandler;
                SessionState.SetBool(RequestedKey, false);
                return;
            }
            if (EditorApplication.timeSinceStartup - _t0 < 2.5) return;
            if (!_reported)
            {
                _reported = true;
                try
                {
                    string dir = System.IO.Path.Combine(Directory.GetCurrentDirectory(), "capturas");
                    if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
                    ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, "viewer_iso.png"));
                    Debug.Log("[LabViewer] Captura en proceso: capturas/viewer_iso.png");
                }
                catch (System.Exception ex) { Debug.Log("[LabViewer] No se pudo capturar: " + ex.Message); }
            }
            if (EditorApplication.timeSinceStartup - _t0 < 3.8) return;
            EditorApplication.update -= Tick;
            SessionState.SetBool(RequestedKey, false);
            Application.logMessageReceived -= LogHandler;
            EditorApplication.isPlaying = false;
            bool ok = _runtimeErrors.Count == 0;
            Debug.Log("[LabViewer] PLAY SMOKE: " + (ok ? "OK" : "FALLO") + "  runtimeErrores=" + _runtimeErrors.Count);
            if (!ok) foreach (var e in _runtimeErrors) Debug.LogError("[LabViewer] runtime: " + e);
            EditorApplication.delayCall += () => { if (!EditorApplication.isPlaying) LabViewerExitGuard.Finish(ok ? 0 : 1); };
        }

        [MenuItem("LabViewer/Probar escena (modo play ~2.5s)")]
        public static void Run()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
            {
                Debug.LogWarning("[LabViewer] Deten Play antes de iniciar la prueba automatica.");
                return;
            }
            if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            UnityEditor.SceneManagement.EditorSceneManager.OpenScene(ScenePath, UnityEditor.SceneManagement.OpenSceneMode.Single);
            SessionState.SetBool(RequestedKey, true);
            EditorApplication.isPlaying = true;
        }

        private static void LogHandler(string condition, string stack, LogType type)
        {
            if (type == LogType.Error || type == LogType.Exception)
                lock (_runtimeErrors) _runtimeErrors.Add(condition + "\n" + stack);
        }
    }

    /// <summary>
    /// Verificacion de aceptacion de los CONTROLES DE VISUALIZACION en modo Play
    /// (donde la escena ya esta construida y los Renderers son reales). Para cada toggle
    /// registra cuantos objetos hay, lo apaga y confirma 0 visibles, lo enciende y
    /// confirma que vuelve el conteo esperado, y comprueba la combinacion
    /// edificio + nivel + tipo. Mismo patron que PlaySmoke (entra a Play, ejecuta,
    /// sale y devuelve codigo 0/1).
    /// Uso: Unity -batchmode -projectPath &lt;viewer&gt; -executeMethod LabViewer.EditorTools.VisibilityAudit.Run
    /// </summary>
    public static class VisibilityAudit
    {
        private const string ScenePath = "Assets/Scenes/Main.unity";
        private const string RequestedKey = "LabViewer.VisibilityAudit.Requested";
        private static double _t0;
        private static bool _done;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void OnPlayStarted()
        {
            if (!SessionState.GetBool(RequestedKey, false)) return;
            _done = false;
            _t0 = EditorApplication.timeSinceStartup;
            EditorApplication.update -= Tick;
            EditorApplication.update += Tick;
        }

        private static void Tick()
        {
            if (!EditorApplication.isPlaying)
            {
                EditorApplication.update -= Tick;
                SessionState.SetBool(RequestedKey, false);
                return;
            }
            if (EditorApplication.timeSinceStartup - _t0 < 2.5) return; // deja correr Start/construccion
            if (_done) return;
            _done = true;

            var viewer = Object.FindObjectOfType<ViewerController>();
            if (viewer == null)
            {
                Debug.LogError("[LabViewer] AUDIT: no ViewerController en escena.");
                Finish(false);
                return;
            }

            bool ok = true;
            Debug.Log("[LabViewer] == AUDIT CONTROLES DE VISUALIZACION ==");

            viewer.SetLevelAll(true);
            viewer.SetBuilding("I", true);
            viewer.SetBuilding("II", true);
            viewer.ShowAllTypes();
            viewer.SetOverlay("nodo", false);
            viewer.SetOverlay("apoyo", false);
            viewer.SetOverlay("id", false);
            viewer.SetOverlay("axis", false);
            viewer.SetOverlay("trib", false);

            // 1) tipos de elemento: apagar -> 0, encender -> vuelve el conteo
            var typeKeys = new[]
            {
                ElemType.Losas, ElemType.Vigas, ElemType.Columnas,
                ElemType.Muros, ElemType.Diafragma, ElemType.Abertura, ElemType.Nodos
            };
            foreach (var t in typeKeys)
            {
                string key = t.ToString();
                int model = viewer.TotalInModel(t);
                viewer.SetType(key, true);
                int before = viewer.CountTypeRenderers(key);
                viewer.SetType(key, false);
                int off = viewer.CountTypeRenderers(key);
                viewer.SetType(key, true);
                int after = viewer.CountTypeRenderers(key);
                bool pass = off == 0 && after == before;
                Debug.Log(string.Format("[LabViewer] [Tipo {0}] modelo={1} visible_ON={2} OFF={3} ON_otra={4} -> {5}",
                    key, model, before, off, after, pass ? "OK" : "FALLO"));
                if (!pass) ok = false;
            }

            // 2) nodos y apoyos (simbolos) y IDs del seleccionado
            viewer.SetType(ElemType.Columnas.ToString(), true);
            viewer.SetOverlay("nodo", true);
            int nodos = viewer.CountMarkerRenderers("nodo");
            viewer.SetOverlay("nodo", false);
            int nodosOff = viewer.CountMarkerRenderers("nodo");
            bool nPass = nodos > 0 && nodosOff == 0;
            Debug.Log(string.Format("[LabViewer] [Nodos] ON={0} OFF={1} -> {2}", nodos, nodosOff, nPass ? "OK" : "FALLO"));
            if (!nPass) ok = false;

            viewer.SetOverlay("apoyo", true);
            int apoyos = viewer.CountMarkerRenderers("apoyo");
            viewer.SetOverlay("apoyo", false);
            int apoyosOff = viewer.CountMarkerRenderers("apoyo");
            bool aPass = apoyos > 0 && apoyosOff == 0;
            Debug.Log(string.Format("[LabViewer] [Apoyos] ON={0} OFF={1} -> {2}", apoyos, apoyosOff, aPass ? "OK" : "FALLO"));
            if (!aPass) ok = false;

            var idElem = firstViga(viewer);
            if (idElem != null && viewer.SelectId(idElem.Id))
            {
                viewer.SetOverlay("id", true);
                int ids = viewer.CountMarkerRenderers("id");
                viewer.SetOverlay("id", false);
                int idsOff = viewer.CountMarkerRenderers("id");
                bool iPass = ids >= 1 && idsOff == 0;
                Debug.Log(string.Format("[LabViewer] [IDs seleccionado] ON={0} OFF={1} -> {2}", ids, idsOff, iPass ? "OK" : "FALLO"));
                if (!iPass) ok = false;
            }
            else Debug.Log("[LabViewer] [IDs seleccionado] sin viga para probar -> SKIP");

            // 3) combinacion edificio + nivel + tipo (AND)
            viewer.ShowAllTypes();
            viewer.SetLevelAll(true);
            int bothtypes = viewer.CountTypeRenderers(ElemType.Vigas.ToString());
            viewer.SetBuilding("II", false);
            int bIOnly = viewer.CountTypeRenderers(ElemType.Vigas.ToString());
            viewer.SetBuilding("II", true);
            int bothRestored = viewer.CountTypeRenderers(ElemType.Vigas.ToString());
            bool combPass = bIOnly < bothtypes && bothRestored == bothtypes;
            Debug.Log(string.Format("[LabViewer] [Combinacion] vigas I+II={0} solo I={1} restaurado={2} -> {3}",
                bothtypes, bIOnly, bothRestored, combPass ? "OK" : "FALLO"));
            if (!combPass) ok = false;

            viewer.SetLevelsOnly("P4", "EII_CP4");
            int p4vigas = viewer.CountTypeRenderers(ElemType.Vigas.ToString());
            Debug.Log("[LabViewer] [Nivel P4 solo] vigas visibles=" + p4vigas);
            viewer.SetLevelAll(true);

            // 4) Mostrar todo / Ocultar todo
            viewer.HideAllTypes();
            int hidden = viewer.CountTypeRenderers(ElemType.Losas.ToString())
                       + viewer.CountTypeRenderers(ElemType.Vigas.ToString());
            viewer.ShowAllTypes();
            int shown = viewer.CountTypeRenderers(ElemType.Losas.ToString())
                      + viewer.CountTypeRenderers(ElemType.Vigas.ToString());
            bool batchPass = hidden == 0 && shown > 0;
            Debug.Log(string.Format("[LabViewer] [Mostrar/Ocultar todo] oculto={0} mostrado={1} -> {2}",
                hidden, shown, batchPass ? "OK" : "FALLO"));
            if (!batchPass) ok = false;

            // seleccion + IDs/ejes: el marcador responde al seleccionado
            if (idElem != null && viewer.SelectId(idElem.Id))
            {
                viewer.SetOverlay("axis", true);
                int axes = viewer.CountMarkerRenderers("axis");
                Debug.Log(string.Format("[LabViewer] [Ejes seleccionado] ejes visibles={0}", axes));
                viewer.SetOverlay("axis", false);
                if (axes < 1) ok = false;
            }

            Finish(ok);
        }

        private static ElementRef firstViga(ViewerController v)
        {
            var m = v.ModelPublic;
            if (m == null) return null;
            foreach (var e in m.Elements) if (e.Type == ElemType.Vigas) return e;
            return null;
        }

        private static void Finish(bool ok)
        {
            Debug.Log("[LabViewer] AUDIT CONTROLES: " + (ok ? "OK" : "FALLO"));
            EditorApplication.update -= Tick;
            SessionState.SetBool(RequestedKey, false);
            EditorApplication.isPlaying = false;
            EditorApplication.delayCall += () => { if (!EditorApplication.isPlaying) LabViewerExitGuard.Finish(ok ? 0 : 1); };
        }

        [MenuItem("LabViewer/Verificar controles de visualizacion (modo play)")]
        public static void Run()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
            {
                Debug.LogWarning("[LabViewer] Deten Play antes de iniciar la verificacion.");
                return;
            }
            if (!Application.isBatchMode && !UnityEditor.SceneManagement.EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            UnityEditor.SceneManagement.EditorSceneManager.OpenScene(ScenePath, UnityEditor.SceneManagement.OpenSceneMode.Single);
            SessionState.SetBool(RequestedKey, true);
            EditorApplication.isPlaying = true;
        }
    }

    /// <summary>
    /// Verificacion de la integracion de AREA TRIBUTARIA REAL (celdas del reparto
    /// geometrico) en modo Play. Para cada una de las tres vigas documentadas en el
    /// informe comprueba que al seleccionarla y activar "Area tributaria" se DIBUJAN
    /// las celdas reales (overlay en escena), con el numero de regiones esperado y los
    /// totales de area/carga de por_viga; que los tres overlays son DIFERENTES; que al
    /// apagar el control se destruye el overlay anterior; y que el Edificio II no
    /// dibuja geometria (solo indica "no disponible"). Sigue el patron PlaySmoke.
    /// Uso: Unity -batchmode -projectPath &lt;viewer&gt; -executeMethod LabViewer.EditorTools.TributaryAudit.Run
    /// </summary>
    public static class TributaryAudit
    {
        private const string ScenePath = "Assets/Scenes/Main.unity";
        private const string RequestedKey = "LabViewer.TributaryAudit.Requested";
        private static double _t0;
        private static bool _done;

        private struct Viga
        {
            public string Level;
            public string Id;
            public int Regions;
            public float Area;
            public float Carga;
            public Viga(string lvl, string id, int regions, float area, float carga)
            { Level = lvl; Id = id; Regions = regions; Area = area; Carga = carga; }
        }

        private static readonly Viga[] TRES_VIGAS = new[]
        {
            new Viga("P1", "V_COL_CP1_E", 582, 36.760f, 228.91f),
            new Viga("P2", "H_EI_CP2_y0089_0.00-10.00", 426, 27.346f, 170.28f),
            new Viga("P3", "H_EI_CP3_y0162_20.00-25.00", 390, 24.926f, 155.22f),
        };

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void OnPlayStarted()
        {
            if (!SessionState.GetBool(RequestedKey, false)) return;
            _done = false;
            _t0 = EditorApplication.timeSinceStartup;
            EditorApplication.update -= Tick;
            EditorApplication.update += Tick;
        }

        private static void Tick()
        {
            if (!EditorApplication.isPlaying)
            {
                EditorApplication.update -= Tick;
                SessionState.SetBool(RequestedKey, false);
                return;
            }
            if (EditorApplication.timeSinceStartup - _t0 < 2.5) return;
            if (_done) return;
            _done = true;

            var viewer = Object.FindObjectOfType<ViewerController>();
            if (viewer == null) { Debug.LogError("[LabViewer] TRIB: no ViewerController"); Finish(false); return; }

            bool ok = true;
            Debug.Log("[LabViewer] == AUDIT AREA TRIBUTARIA REAL ==");

            viewer.SetLevelAll(true);
            viewer.SetBuilding("I", true);
            viewer.SetBuilding("II", true);
            viewer.ShowAllTypes();
            viewer.SetOverlay("trib", false);
            viewer.SetOverlay("id", false);
            viewer.SetOverlay("axis", false);

            var drawnCounts = new List<int>();
            for (int i = 0; i < TRES_VIGAS.Length; i++)
            {
                var v = TRES_VIGAS[i];
                string desc = v.Level + " " + v.Id;

                // Seleccion + activar overlay: se dibujan las celdas reales del repuesto
                bool sel = viewer.SelectId(v.Id);
                ElementRef selElem = viewer.Selected;
                viewer.SetOverlay("trib", true);
                int drawn = viewer.CountMarkerRenderers("trib");
                drawnCounts.Add(drawn);

                bool passRegions = sel && selElem != null && selElem.TribRegions != null
                                   && selElem.TribRegions.Count == v.Regions;
                bool passDrawn = drawn == v.Regions; // cada region = un Renderer en escena
                bool passArea = selElem != null && Mathf.Abs((float)selElem.TribAreaM2 - v.Area) < 0.02f;
                bool passCarga = selElem != null && Mathf.Abs((float)selElem.TribCargaKN - v.Carga) < 0.2f;
                bool passSource = selElem != null && selElem.TribSource == "primera_ejecucion";
                bool pass = passRegions && passDrawn && passArea && passCarga && passSource;

                Debug.Log(string.Format("[LabViewer] [Tribu {0}] regions_modelo={1} dibujadas={2} area={3:0.###} carga={4:0.###} fuente={5} -> {6}",
                    desc,
                    selElem != null ? (selElem.TribRegions != null ? selElem.TribRegions.Count : -1) : -1,
                    drawn,
                    selElem != null ? selElem.TribAreaM2 : -1,
                    selElem != null ? selElem.TribCargaKN : -1,
                    selElem != null ? selElem.TribSource : "?",
                    pass ? "OK" : "FALLO"));
                if (!pass) ok = false;
            }

            // 3 overlays distintos (cada viga genera un numero de celdas diferente)
            bool distinct = drawnCounts.Count == 3
                            && drawnCounts[0] != drawnCounts[1]
                            && drawnCounts[1] != drawnCounts[2]
                            && drawnCounts[0] != drawnCounts[2];
            Debug.Log(string.Format("[LabViewer] [Overlays distintos] {0} -> {1}",
                string.Join(",", drawnCounts), distinct ? "OK" : "FALLO"));
            if (!distinct) ok = false;

            // Apagar el control destruye el overlay anterior
            viewer.SetOverlay("trib", false);
            int off = viewer.CountMarkerRenderers("trib");
            bool offPass = off == 0;
            Debug.Log(string.Format("[LabViewer] [Overlay apagado] trib_restantes={0} -> {1}", off, offPass ? "OK" : "FALLO"));
            if (!offPass) ok = false;

            // Edificio II: viga de EII sin dibujo (no disponible), sin reutilizar area del I
            ElementRef eii = null;
            var m = viewer.ModelPublic;
            if (m != null)
            {
                foreach (var e in m.Elements)
                    if (e.Building == "II" && e.Type == ElemType.Vigas) { eii = e; break; }
            }
            if (eii != null)
            {
                viewer.SelectId(eii.Id);
                viewer.SetOverlay("trib", true);
                int esp = viewer.CountMarkerRenderers("trib");
                // EII no adjunta celdas de reparto: si hay overlay es solo el texto
                // "no disponible" (1 marcador), nunca celdas geometricas.
                bool eiiNoGeo = (eii.TribRegions == null || eii.TribRegions.Count == 0) && esp <= 1;
                Debug.Log(string.Format("[LabViewer] [EII] viga={0} regiones={1} marcadores_trib={2} -> {3}",
                    eii.Id, eii.TribRegions != null ? eii.TribRegions.Count : 0, esp, eiiNoGeo ? "OK" : "FALLO"));
                if (!eiiNoGeo) ok = false;
            }
            else Debug.Log("[LabViewer] [EII] sin viga en modelo -> SKIP");

            viewer.SetOverlay("trib", false);
            Finish(ok);
        }

        private static void Finish(bool ok)
        {
            Debug.Log("[LabViewer] AUDIT TRIBUTARIA: " + (ok ? "OK" : "FALLO"));
            EditorApplication.update -= Tick;
            SessionState.SetBool(RequestedKey, false);
            EditorApplication.isPlaying = false;
            EditorApplication.delayCall += () => { if (!EditorApplication.isPlaying) LabViewerExitGuard.Finish(ok ? 0 : 1); };
        }

        [MenuItem("LabViewer/Verificar area tributaria real (modo play)")]
        public static void Run()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
            {
                Debug.LogWarning("[LabViewer] Deten Play antes de iniciar la verificacion.");
                return;
            }
            if (!Application.isBatchMode && !UnityEditor.SceneManagement.EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            UnityEditor.SceneManagement.EditorSceneManager.OpenScene(ScenePath, UnityEditor.SceneManagement.OpenSceneMode.Single);
            SessionState.SetBool(RequestedKey, true);
            EditorApplication.isPlaying = true;
        }
    }
}
