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

        /// <summary>Las 13 cargas del paquete V1 (4 bases + 9 combinaciones NCh3171).</summary>
        private static readonly string[] CASOS_FE =
        {
            "G", "Q", "EX", "EY",
            "U1_GQ", "U2_EX_POS", "U2_EX_NEG", "U3_EY_POS", "U3_EY_NEG",
            "U4_EX_POS", "U4_EX_NEG", "U4_EY_POS", "U4_EY_NEG",
        };

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

        /// <summary>
        /// Verificacion de aceptacion del OVERLAY DE ESFUERZOS FE en MODO EDITOR
        /// (deterministica, sin play ni raycast): ejercita el mismo codigo runtime
        /// EsfuerzosController sobre un LabLoader real. Comprueba: carga de ambos
        /// paquetes (FE_TOTAL I 409, II 252), los 13 casos V1 presentes sin casos
        /// heredados, valores identicos a la fuente (anclas de combinaciones
        /// NCh3171 + envolvente con caso/signo gobernante), construccion del overlay
        /// en MODO NORMAL (OVERLAY_NORMAL_MAPEADO I 292, II 237: solo 1A1+CONTENIDO;
        /// SIN_CORRESPONDENCIA_VIEWER y stubs ocultos) y en modo diagnostico
        /// ("Todos los FE" = FE_TOTAL completo), seleccion de dos columnas y dos
        /// vigas con valores reales distintos, cambio real de valores entre casos,
        /// y restauracion completa al apagar. Toma capturas de evidencia en modo
        /// normal (sin stubs ni lineas sin barra fisica).
        /// Uso: Unity -batchmode -quit -projectPath &lt;viewer&gt; -executeMethod LabViewer.EditorTools.LabViewerEditor.CheckEsfuerzosOverlay
        /// </summary>
        [MenuItem("LabViewer/Verificar overlay esfuerzos FE (modo editor)")]
        public static void CheckEsfuerzosOverlay()
        {
            var go = new GameObject("EsfuerzosCheck");
            var loader = go.AddComponent<LabLoader>();
            try
            {
                bool okLoad = loader.Load();
                var esf = go.AddComponent<EsfuerzosController>();
                esf.Preparar(loader);
                var lab = GameObject.Find("Lab");

                bool ok = okLoad && lab != null;
                Log("EsfEditor: load=" + okLoad + " LabRoot=" + (lab != null));
                if (!ok) { LogError("EsfEditor: el modelo no cargo."); }

// 1) carga de paquetes y FE_TOTAL (elementos completos del paquete)
                bool loadPass = esf.EstaCargado("I") && esf.EstaCargado("II");
                int nI = esf.TotalElementos("I"), nII = esf.TotalElementos("II");
                bool countPass = nI == 409 && nII == 252;
                Log(string.Format("[Esf] [Carga] I={0} II={1} -> {2}", esf.EstaCargado("I"), esf.EstaCargado("II"), loadPass ? "OK" : "FALLO"));
                Log(string.Format("[Esf] [FE_TOTAL] I={0} II={1} (esperados 409/252) -> {2}", nI, nII, countPass ? "OK" : "FALLO"));
                ok &= loadPass && countPass;

                // 1.5) 13 casos V1 disponibles (perfil MODELO_FE_COMPLETO_FUNCIONAL),
                //      sin casos heredados fuera de esa lista, y envolvente NCh3171 con
                //      casos gobernantes.
                foreach (var b in new[] { "I", "II" })
                {
                    var probe = esf.Buscar(b, 3); // columna 1A1 con los 13 casos
                    if (probe == null) { LogError("[Esf] Sin columna probe " + b + " tag3"); ok = false; continue; }
                    int presentes = 0;
                    foreach (var c in CASOS_FE)
                        if (!float.IsNaN((float)esf.Valor(b, 3, c, 0)) && probe.Tiene(c)) presentes++;
                    bool casosOk = presentes == CASOS_FE.Length && probe.EnvOk;
                    bool sinHeredado = probe.Disponible.Count == CASOS_FE.Length;
                    Log(string.Format("[Esf] [Casos {0}] presentes={1}/13 envolvente_ok={2} sin_casos_heredados={3} -> {4}",
                        b, presentes, probe.EnvOk, sinHeredado, (casosOk && sinHeredado) ? "OK" : "FALLO"));
                    ok &= casosOk && sinHeredado;
                }

                // 2) valores identicos a la fuente: combinaciones NCh3171 (corridas
                //    EXPLICITAS) + envolvente (caso y signo gobernante por componente).
                var anclas = new[]
                {
                    new { b = "I", tag = 3, caso = "G", comp = 0, val = 285.246214 },
                    new { b = "I", tag = 3, caso = "U1_GQ", comp = 0, val = 453.661065 },
                    new { b = "I", tag = 3, caso = "U2_EX_POS", comp = 0, val = 1889.601113 },
                    new { b = "I", tag = 3, caso = "U2_EX_NEG", comp = 5, val = 1461.801234 },
                    new { b = "II", tag = 3, caso = "U2_EX_POS", comp = 0, val = 2568.793090 },
                    new { b = "II", tag = 3, caso = "U2_EX_NEG", comp = 0, val = 3768.523550 },
                    new { b = "II", tag = 3, caso = "U2_EX_POS", comp = 5, val = -2177.963531 },
                };
                foreach (var a in anclas)
                {
                    double val = esf.Valor(a.b, a.tag, a.caso, a.comp);
                    bool pass = Mathf.Abs((float)(val - a.val)) < 1e-3f;
                    Log(string.Format("[Esf] [Valor] {0} tag{1} {2}[comp{3}]={4} esperado={5} -> {6}",
                        a.b, a.tag, a.caso, a.comp, val, a.val, pass ? "OK" : "FALLO"));
                    ok &= pass;
                }
                var envAnclas = new[]
                {
                    new { b = "I", tag = 3, comp = 0, caso = "U2_EX_POS", val = 1889.601113 },
                    new { b = "I", tag = 3, comp = 5, caso = "U2_EX_NEG", val = 1461.801234 },
                    new { b = "II", tag = 3, comp = 0, caso = "U2_EX_NEG", val = 3768.523550 },
                    new { b = "II", tag = 3, comp = 11, caso = "U2_EX_POS", val = -1320.086813 },
                };
                foreach (var a in envAnclas)
                {
                    var e2 = esf.Buscar(a.b, a.tag);
                    double val = e2 != null && e2.EnvOk ? e2.EnvValores[a.comp] : double.NaN;
                    string casoG = e2 != null ? e2.EnvCasos[a.comp] : null;
                    bool pass = Mathf.Abs((float)(val - a.val)) < 1e-3f && casoG == a.caso;
                    Log(string.Format("[Esf] [Envolvente] {0} tag{1} comp{2}={3} gobernante={4} esperado={5} [{6}] -> {7}",
                        a.b, a.tag, a.comp, val, casoG, a.val, a.caso, pass ? "OK" : "FALLO"));
                    ok &= pass;
                }

                // 3) correspondencia viewer (estados validos en anclas conocidas)
                foreach (var a in anclas)
                {
                    var e = esf.Buscar(a.b, a.tag);
                    if (e == null) { LogError("[Esf] No existe tag " + a.b + " " + a.tag); ok = false; continue; }
                    bool estado = e.EstadoCorr == "1A1" || e.EstadoCorr == "CONTENIDO"
                                  || e.EstadoCorr == "SIN_CORRESPONDENCIA_VIEWER";
                    if (!estado) { LogError("[Esf] Estado invalido " + a.b + " tag" + a.tag + ": " + e.EstadoCorr); ok = false; }
                }

// 4) overlay por edificio en MODO NORMAL (solo 1A1+CONTENIDO): combinacion sismica
//    NCh3171 (I), envolvente independiente (I y II) y caso base (II G/Mz).
//    En modo normal los SIN_CORRESPONDENCIA_VIEWER (incluidos los 45 stubs EI)
//    NO se renderizan => OVERLAY_NORMAL_MAPEADO EI 292, EII 237.
esf.SetFiltros(true, true, true, "Mapeados");
esf.SetUI("I", "U2_EX_POS", 0, 2, 0, true);
int dibI = esf.CountOverlayRenderers("I");
bool ovIPass = dibI == 292;
Log(string.Format("[Esf] [Overlay I U2_EX_POS/N (MODO_NORMAL)] tubos={0} esperados=292 escala={1} maxReal={2} -> {3}",
    dibI, esf.EscalaActual, esf.MaxRealActual, ovIPass ? "OK" : "FALLO"));
ok &= ovIPass;
CapturarEditor("capturas/esfuerzos_I_U2_EX_POS_N.png");

esf.SeleccionarEnvolvente();
int dibIEnv = esf.CountOverlayRenderers("I");
bool ovIEnvPass = dibIEnv == 292 && esf.EscalaActual > 0f;
Log(string.Format("[Esf] [Overlay I Envolvente N (MODO_NORMAL)] tubos={0} esperados=292 escala={1} maxReal={2} -> {3}",
    dibIEnv, esf.EscalaActual, esf.MaxRealActual, ovIEnvPass ? "OK" : "FALLO"));
ok &= ovIEnvPass;
CapturarEditor("capturas/esfuerzos_I_envolvente_N.png");

esf.SetUI("II", "ENVOLVENTE_NCh3171", 5, 1, 1, true);
int dibIIEnv = esf.CountOverlayRenderers("II");
bool ovIIEnvPass = dibIIEnv == 237;
Log(string.Format("[Esf] [Overlay II Envolvente Mz/extremo j (MODO_NORMAL)] tubos={0} esperados=237 escala={1} -> {2}",
    dibIIEnv, esf.EscalaActual, ovIIEnvPass ? "OK" : "FALLO"));
ok &= ovIIEnvPass;
CapturarEditor("capturas/esfuerzos_II_envolvente_Mz.png");

esf.SetUI("II", "G", 5, 0, 1, true);
int dibII = esf.CountOverlayRenderers("II");
bool ovIIPass = dibII == 237;
Log(string.Format("[Esf] [Overlay II G/Mz (MODO_NORMAL)] tubos={0} esperados=237 escala={1} maxReal={2} -> {3}",
    dibII, esf.EscalaActual, esf.MaxRealActual, ovIIPass ? "OK" : "FALLO"));
ok &= ovIIPass;
CapturarEditor("capturas/esfuerzos_II_G_Mz.png");

// 4.1) modo de diagnostico "Todos los FE" (OVERLAY_DIAGNOSTICO): FE_TOTAL completo
//      visible incluyendo SIN_CORRESPONDENCIA_VIEWER y stubs analiticos. Verifica
//      que esos elementos solo aparecen en este modo.
esf.SetUI("I", "U2_EX_POS", 0, 2, 0, true);
esf.SetFiltros(true, true, true, "Todos los FE");
int dibDiagI = esf.CountOverlayRenderers("I");
bool diagIPass = dibDiagI == nI;
Log(string.Format("[Esf] [Overlay I Todos los FE (DIAGNOSTICO)] tubos={0} esperados={1} -> {2}",
    dibDiagI, nI, diagIPass ? "OK" : "FALLO"));
ok &= diagIPass;
esf.SetUI("II", "G", 5, 0, 1, true);
int dibDiagII = esf.CountOverlayRenderers("II");
bool diagIIPass = dibDiagII == nII;
Log(string.Format("[Esf] [Overlay II Todos los FE (DIAGNOSTICO)] tubos={0} esperados={1} -> {2}",
    dibDiagII, nII, diagIIPass ? "OK" : "FALLO"));
ok &= diagIIPass;

// volver al modo normal para el resto del auditor
esf.SetFiltros(true, true, true, "Mapeados");
esf.SetUI("I", "U2_EX_POS", 0, 2, 0, true);

                // 4.5) geometria del overlay en TODOS los elementos: extremos renderizados (TransformPoint)
                //      vs w0/w1 FE, centro de bounds vs punto medio, longitud renderizada.
                const float TOL_GEOM = 0.01f; // m, tolerancia documentada de extremos
                float maxErrE = 0f, rmsE = 0f, maxErrC = 0f, maxErrL = 0f;
                int fueraTol = 0;
                bool geomPass = esf.VerificarGeometria(TOL_GEOM, out maxErrE, out rmsE, out maxErrC, out maxErrL, out fueraTol);
                Log(string.Format("[Esf] [Geometria] todos(maxErrExtremos={0:0.0000} m RMS={1:0.0000} m " +
                    "maxErrCentroBounds={2:0.0000} m maxErrLongitud={3:0.0000} m fueraTol={4}) -> {5}",
                    maxErrE, rmsE, maxErrC, maxErrL, fueraTol, geomPass ? "OK" : "FALLO"));
                ok &= geomPass;

                // 5) seleccion por tag: DOS COLUMNAS y DOS VIGAS con valores NCh3171 REALES
                //    distintos + cambio REAL de tag y de valores al cambiar de caso.
                bool escPass = esf.EscalaActual > 0f && esf.MaxRealActual > 0f;
                bool selPares = true;
                {
                    var escenarios = new[]
                    {
                        new { b = "I",  t0 = 25, t1 = 616, tipo = "columna" },
                        new { b = "II", t0 = 49, t1 = 28,  tipo = "columna" },
                        new { b = "I",  t0 = 318, t1 = 320, tipo = "viga" },
                        new { b = "II", t0 = 244, t1 = 230, tipo = "viga" },
                    };
                    foreach (var s in escenarios)
                    {
                        double n0 = esf.Valor(s.b, s.t0, "U2_EX_POS", 0);
                        double n1 = esf.Valor(s.b, s.t1, "U2_EX_POS", 0);
                        bool sel0 = esf.SelectFE(s.b, s.t0) && esf.SelectedFE != null && esf.SelectedFE.Tag == s.t0;
                        bool sel1 = esf.SelectFE(s.b, s.t1) && esf.SelectedFE != null && esf.SelectedFE.Tag == s.t1;
                        bool tipoOk = esf.SelectedFE != null && esf.SelectedFE.Tipo != null
                                      && esf.SelectedFE.Tipo.Contains(s.tipo);
                        bool vals = !float.IsNaN((float)n0) && !float.IsNaN((float)n1)
                                    && Mathf.Abs((float)(n0 - n1)) > 1e-3f;
                        bool passS = sel0 && sel1 && tipoOk && vals;
                        Log(string.Format("[Esf] [Seleccion 2 {0} {1}] tags={2},{3} N_U2_EX_POS={4:0.###}/{5:0.###} -> {6}",
                            s.tipo, s.b, s.t0, s.t1, n0, n1, passS ? "OK" : "FALLO"));
                        selPares &= passS;
                    }
                }
                bool valChange = false;
                {
                    double g = esf.Valor("I", 3, "G", 0);
                    double c = esf.Valor("I", 3, "U1_GQ", 0);
                    valChange = Mathf.Abs((float)(c - g)) > 1e-3f;
                    Log(string.Format("[Esf] [Cambio real de valores] I tag3 G N_i={0:0.###} -> U1_GQ N_i={1:0.###} -> {2}",
                        g, c, valChange ? "OK" : "FALLO"));
                }
                Log(string.Format("[Esf] [Seleccion tag3] ok={0} -> {1} | [Escala>0 / MaxReal>0] {2} / {3} -> {4}",
                    selPares, selPares ? "OK" : "FALLO", esf.EscalaActual, esf.MaxRealActual, escPass ? "OK" : "FALLO"));
                ok &= selPares && escPass && valChange;

                // 6) restauracion: apagar overlay deja 0 tuberias visibles
                esf.SetOverlay(false);
                int rest = esf.CountOverlayRenderers("I") + esf.CountOverlayRenderers("II");
                bool restPass = rest == 0;
                Log(string.Format("[Esf] [Restauracion] tubos={0} -> {1}", rest, restPass ? "OK" : "FALLO"));
                ok &= restPass;

                Log(ok ? "OVERLAY ESFUERZOS FE (EDITOR): OK" : "OVERLAY ESFUERZOS FE (EDITOR): FALLO");
                Object.DestroyImmediate(go);
                if (lab != null) Object.DestroyImmediate(lab);
                LabViewerExitGuard.Finish(ok ? 0 : 1);
            }
            catch (System.Exception ex)
            {
                LogError("EsfEditor exception: " + ex.Message + "\n" + ex.StackTrace);
                Object.DestroyImmediate(go);
                LabViewerExitGuard.Finish(1);
            }
        }

        /// <summary>Renderiza la escena (modo editor) y escribe PNG de evidencia.</summary>
        private static void CapturarEditor(string rutaRel)
        {
            string[] cli = System.Environment.GetCommandLineArgs();
            bool sinGraficos = System.Array.IndexOf(cli, "-nographics") >= 0;
            if (Application.isBatchMode && sinGraficos)
            {
                Log("Captura omitida en batch (-nographics): " + rutaRel + " (usar el Editor interactivo o el auditor de play).");
                return;
            }
            try
            {
                string full = Path.Combine(new DirectoryInfo(Application.dataPath).Parent.FullName, rutaRel);
                string dir = Path.GetDirectoryName(full);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);

                var camGo = new GameObject("EsfCapCam");
                var cam = camGo.AddComponent<Camera>();
                cam.enabled = false;
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = new Color(0.15f, 0.17f, 0.20f);
                cam.nearClipPlane = 0.3f;
                cam.farClipPlane = 3000f;

                var sunGO = new GameObject("EsfCapSun");
                var sun = sunGO.AddComponent<Light>();
                sun.type = LightType.Directional;
                sun.intensity = 1.1f;
                sunGO.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

                int w = 1280, h = 720;
                var rt = new RenderTexture(w, h, 24);
                cam.targetTexture = rt;

                Bounds bb = new Bounds(Vector3.zero, Vector3.one);
                bool have = false;
                foreach (var r in Object.FindObjectsOfType<Renderer>())
                {
                    if (!have) { bb = r.bounds; have = true; }
                    else bb.Encapsulate(r.bounds);
                }
                if (!have) bb.size = new Vector3(80f, 40f, 80f);
                float d = Mathf.Max(bb.size.magnitude * 1.15f, 80f);
                Vector3 dirIso = new Vector3(0.6f, 0.55f, 0.72f).normalized;
                cam.transform.position = bb.center + dirIso * d;
                cam.transform.LookAt(bb.center);

                cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
                tex.Apply();
                RenderTexture.active = null;
                File.WriteAllBytes(full, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                cam.targetTexture = null;
                rt.Release();
                Object.DestroyImmediate(camGo);
                Object.DestroyImmediate(sunGO);
                Log("Captura (editor): " + rutaRel);
            }
            catch (System.Exception ex)
            {
                Log("No se pudo capturar (editor) " + rutaRel + ": " + ex.Message);
            }
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

    /// <summary>
    /// Verificacion de aceptacion del OVERLAY DE ESFUERZOS FE (independiente por
    /// elemento). En modo Play: carga (FE_TOTAL I: 409, II: 252), los 13 casos V1
    /// presentes sin casos heredados, valores identicos a la fuente (anclas de
    /// combinaciones NCh3171 + envolvente con caso/signo gobernante), construccion
    /// del overlay en MODO NORMAL (OVERLAY_NORMAL_MAPEADO I 292, II 237: solo
    /// 1A1+CONTENIDO) y en modo diagnostico (Todos los FE = FE_TOTAL completo),
    /// seleccion por correspondencia con clics reales (2 columnas y 2 vigas), por
    /// tag y restauracion. Toma capturas: combinacion sismica y envolvente en modo
    /// normal (sin stubs ni lineas sin barra fisica).
    /// Uso: Unity -batchmode -projectPath &lt;viewer&gt; -executeMethod LabViewer.EditorTools.EsfuerzosAudit.Run
    /// </summary>
    public static class EsfuerzosAudit
    {
        private const string ScenePath = "Assets/Scenes/Main.unity";
        private const string RequestedKey = "LabViewer.EsfuerzosAudit.Requested";
        private static double _t0;
        private static bool _done;

        private class Ancla { public string B; public int Tag; public string Caso; public int Comp; public double Val; }
        private static readonly Ancla[] ANCLAS = new Ancla[]
        {
            // edificio, tag, caso/comp, valor esperado (combos NCh3171 EXPLICITOS + base)
            new Ancla { B = "I", Tag = 3, Caso = "G", Comp = 0, Val = 285.246214 },
            new Ancla { B = "I", Tag = 3, Caso = "U1_GQ", Comp = 0, Val = 453.661065 },
            new Ancla { B = "I", Tag = 3, Caso = "U2_EX_POS", Comp = 0, Val = 1889.601113 },
            new Ancla { B = "I", Tag = 3, Caso = "U2_EX_NEG", Comp = 5, Val = 1461.801234 },
            new Ancla { B = "II", Tag = 3, Caso = "U2_EX_POS", Comp = 0, Val = 2568.793090 },
            new Ancla { B = "II", Tag = 3, Caso = "U2_EX_NEG", Comp = 0, Val = 3768.523550 },
            new Ancla { B = "II", Tag = 3, Caso = "U2_EX_POS", Comp = 5, Val = -2177.963531 },
        };
        private static readonly Ancla[] ENV_ANCLAS = new Ancla[]
        {
            // envolvente NCh3171: componente y caso gobernante esperado (signo conservado)
            new Ancla { B = "I", Tag = 3, Caso = "U2_EX_POS", Comp = 0, Val = 1889.601113 },
            new Ancla { B = "I", Tag = 3, Caso = "U2_EX_NEG", Comp = 5, Val = 1461.801234 },
            new Ancla { B = "II", Tag = 3, Caso = "U2_EX_NEG", Comp = 0, Val = 3768.523550 },
            new Ancla { B = "II", Tag = 3, Caso = "U2_EX_POS", Comp = 11, Val = -1320.086813 },
        };
        private static readonly string[] CASOS = {
            "G", "Q", "EX", "EY",
            "U1_GQ", "U2_EX_POS", "U2_EX_NEG", "U3_EY_POS", "U3_EY_NEG",
            "U4_EX_POS", "U4_EX_NEG", "U4_EY_POS", "U4_EY_NEG",
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
            if (EditorApplication.timeSinceStartup - _t0 < 2.5) return; // dejar cargar modelo + overlay
            if (_done) return;
            _done = true;

            var esf = Object.FindObjectOfType<EsfuerzosController>();
            if (esf == null)
            {
                Debug.LogError("[LabViewer] ESF: no EsfuerzosController (no se adjunto).");
                Finish(false);
                return;
            }
            var viewer = Object.FindObjectOfType<ViewerController>();
            viewer.SetLevelAll(true);
            viewer.SetBuilding("I", true);
            viewer.SetBuilding("II", true);
            viewer.ShowAllTypes();

            bool ok = true;
            Debug.Log("[LabViewer] == AUDIT OVERLAY ESFUERZOS FE ==");

            // 1) carga de paquetes
            bool loadPass = esf.EstaCargado("I") && esf.EstaCargado("II");
            Debug.Log(string.Format("[LabViewer] [Carga] I={0} II={1} -> {2}",
                esf.EstaCargado("I"), esf.EstaCargado("II"), loadPass ? "OK" : "FALLO"));
            if (!loadPass) ok = false;

            // 2) FE_TOTAL por edificio (elementos completos del paquete)
            int nI = esf.TotalElementos("I"), nII = esf.TotalElementos("II");
            bool countPass = nI == 409 && nII == 252;
            Debug.Log(string.Format("[LabViewer] [FE_TOTAL] I={0} II={1} (esperados 409/252) -> {2}", nI, nII, countPass ? "OK" : "FALLO"));
            if (!countPass) ok = false;

            // 2.5) los 13 casos V1 presentes (columna probe 1A1) sin casos heredados
            //      + envolvente con casos gobernantes.
            foreach (var b in new[] { "I", "II" })
            {
                var probe = esf.Buscar(b, 3);
                if (probe == null) { Debug.Log("[LabViewer] [Casos " + b + "] sin probe tag3 -> FALLO"); ok = false; continue; }
                int presentes = 0;
                foreach (var c in CASOS)
                    if (!float.IsNaN((float)esf.Valor(b, 3, c, 0)) && probe.Tiene(c)) presentes++;
                bool casosOk = presentes == CASOS.Length && probe.EnvOk;
                bool sinHeredado = probe.Disponible.Count == CASOS.Length;
                Debug.Log(string.Format("[LabViewer] [Casos {0}] presentes={1}/13 envolvente_ok={2} sin_casos_heredados={3} -> {4}",
                    b, presentes, probe.EnvOk, sinHeredado, (casosOk && sinHeredado) ? "OK" : "FALLO"));
                if (!(casosOk && sinHeredado)) ok = false;
            }

            // 3) valores identicos a la fuente (redondeo 6, tolerancia float32 1e-3)
            foreach (var a in ANCLAS)
            {
                double val = esf.Valor(a.B, a.Tag, a.Caso, a.Comp);
                bool pass = Mathf.Abs((float)(val - a.Val)) < 1e-3f;
                Debug.Log(string.Format("[LabViewer] [Valor] {0} tag{1} {2}[comp{3}]={4} esperado={5} -> {6}",
                    a.B, a.Tag, a.Caso, a.Comp, val, a.Val, pass ? "OK" : "FALLO"));
                if (!pass) ok = false;
            }
            foreach (var a in ENV_ANCLAS)
            {
                var eEn = esf.Buscar(a.B, a.Tag);
                double val = eEn != null && eEn.EnvOk ? eEn.EnvValores[a.Comp] : double.NaN;
                string casoG = eEn != null ? eEn.EnvCasos[a.Comp] : null;
                bool pass = Mathf.Abs((float)(val - a.Val)) < 1e-3f && casoG == a.Caso;
                Debug.Log(string.Format("[LabViewer] [Envolvente] {0} tag{1} comp{2}={4:0.######} gobernante={3} esperado={5} [{6}] -> {7}",
                    a.B, a.Tag, a.Comp, casoG, val, a.Val, a.Caso, pass ? "OK" : "FALLO"));
                if (!pass) ok = false;
            }

            // 4) OVERLAY_NORMAL_MAPEADO en MODO NORMAL (solo 1A1+CONTENIDO): los
//    SIN_CORRESPONDENCIA_VIEWER (incluidos los 45 stubs EI) quedan ocultos
//    en el render y no cuentan en la cobertura del viewer.
esf.SetFiltros(true, true, true, "Mapeados");
esf.ConteosCorrespondencia("I", out int totI, out int mapI, out int sinI, out int stubsI);
bool convI = totI == 409 && mapI == 292 && sinI == 117 && stubsI == 45;
Debug.Log(string.Format("[LabViewer] [Conteos I (MODO_NORMAL)] FE_TOTAL={0} OVERLAY_NORMAL_MAPEADO={1} "
    + "SIN_CORRESPONDENCIA={2} stubs_analiticos={3} -> {4}",
    totI, mapI, sinI, stubsI, convI ? "OK" : "FALLO"));
if (!convI) ok = false;
esf.ConteosCorrespondencia("II", out int totII, out int mapII, out int sinII, out int stubsII);
bool convII = totII == 252 && mapII == 237 && sinII == 15 && stubsII == 0;
Debug.Log(string.Format("[LabViewer] [Conteos II (MODO_NORMAL)] FE_TOTAL={0} OVERLAY_NORMAL_MAPEADO={1} "
    + "SIN_CORRESPONDENCIA={2} stubs_analiticos={3} -> {4}",
    totII, mapII, sinII, stubsII, convII ? "OK" : "FALLO"));
if (!convII) ok = false;

esf.SetUI("I", "U2_EX_POS", 0, 2, 0, true);
int dibujadasI = esf.CountOverlayRenderers("I");
bool overlayIPass = dibujadasI == mapI;
Debug.Log(string.Format("[LabViewer] [Overlay I U2_EX_POS/N (MODO_NORMAL)] tubos={0} esperados={1} "
    + "(OVERLAY_NORMAL_MAPEADO) escala={2} maxReal={3} -> {4}",
    dibujadasI, mapI, esf.EscalaActual, esf.MaxRealActual, overlayIPass ? "OK" : "FALLO"));
if (!overlayIPass) ok = false;

// 5) SELECCION POR CORRESPONDENCIA viewer<->FE (clics reales de pantalla)
//    sobre una combinacion sismica en modo normal; captura de la combinacion.
bool rayIPass = ProbarClicCorrespondencia(esf, "I", "U2_EX_POS", 0, 2);
Capture("capturas/esfuerzos_I_U2_EX_POS_N.png", esf);

// 5a) ENVOLVENTE NCh3171 independiente (I) en modo normal: overlay + captura
esf.SetUI("I", "ENVOLVENTE_NCh3171", 0, 2, 0, true);
int dibIEnv = esf.CountOverlayRenderers("I");
bool ovIEnvPass = dibIEnv == mapI && esf.EscalaActual > 0f;
Debug.Log(string.Format("[LabViewer] [Overlay I Envolvente/N (MODO_NORMAL)] tubos={0} esperados={1} "
    + "escala={2} maxReal={3} -> {4}",
    dibIEnv, mapI, esf.EscalaActual, esf.MaxRealActual, ovIEnvPass ? "OK" : "FALLO"));
if (!ovIEnvPass) ok = false;
bool rayEnvPass = ProbarClicCorrespondencia(esf, "I", "ENVOLVENTE_NCh3171", 0, 2);
Capture("capturas/esfuerzos_I_envolvente_N.png", esf);

// 5b) overlay II en modo normal (G, Mz, extremo i, Maximo)
esf.SetUI("II", "G", 5, 0, 1, true);
int dibujadasII = esf.CountOverlayRenderers("II");
bool overlayIIPass = dibujadasII == mapII;
Debug.Log(string.Format("[LabViewer] [Overlay II G/Mz (MODO_NORMAL)] tubos={0} esperados={1} "
    + "(OVERLAY_NORMAL_MAPEADO) escala={2} maxReal={3} -> {4}",
    dibujadasII, mapII, esf.EscalaActual, esf.MaxRealActual, overlayIIPass ? "OK" : "FALLO"));
if (!overlayIIPass) ok = false;
bool rayIIPass = ProbarClicCorrespondencia(esf, "II", "G", 5, 0);
Capture("capturas/esfuerzos_II_G_Mz.png", esf);

esf.SetUI("II", "ENVOLVENTE_NCh3171", 5, 1, 1, true);
int dibIIEnv = esf.CountOverlayRenderers("II");
bool ovIIEnvPass = dibIIEnv == mapII && esf.EscalaActual > 0f;
Debug.Log(string.Format("[LabViewer] [Overlay II Envolvente/Mz (MODO_NORMAL)] tubos={0} esperados={1} "
    + "-> {2}",
    dibIIEnv, mapII, ovIIEnvPass ? "OK" : "FALLO"));
if (!ovIIEnvPass) ok = false;
Capture("capturas/esfuerzos_II_envolvente_Mz.png", esf);

// 5c) MODO DE DIAGNOSTICO "Todos los FE": FE_TOTAL completo visible (incluye
//     SIN_CORRESPONDENCIA_VIEWER y stubs). Verifica que esos elementos solo se
//     renderizan en este modo.
esf.SetFiltros(true, true, true, "Todos los FE");
esf.SetUI("I", "U2_EX_POS", 0, 2, 0, true);
int diagI = esf.CountOverlayRenderers("I");
bool diagPassI = diagI == totI;
Debug.Log(string.Format("[LabViewer] [Overlay I Todos los FE (DIAGNOSTICO)] tubos={0} esperados={1} -> {2}",
    diagI, totI, diagPassI ? "OK" : "FALLO"));
if (!diagPassI) ok = false;
esf.SetUI("II", "G", 5, 0, 1, true);
int diagII = esf.CountOverlayRenderers("II");
bool diagPassII = diagII == totII;
Debug.Log(string.Format("[LabViewer] [Overlay II Todos los FE (DIAGNOSTICO)] tubos={0} esperados={1} -> {2}",
    diagII, totII, diagPassII ? "OK" : "FALLO"));
if (!diagPassII) ok = false;

// filtros por tipologia (solo columnas visibles en el overlay)
esf.SetFiltros(false, true, false, "Todos los FE");
var soloColumnasII = esf.CountOverlayRenderers("II");
bool tipPass = soloColumnasII > 0 && soloColumnasII < totII;
Debug.Log(string.Format("[LabViewer] [Filtro solo Columnas II] tubos={0} esperado (0,{1}) -> {2}",
    soloColumnasII, totII, tipPass ? "OK" : "FALLO"));
if (!tipPass) ok = false;

// volver al modo normal para el resto del auditor
esf.SetFiltros(true, true, true, "Mapeados");
esf.SetUI("II", "G", 5, 0, 1, true);

            // 6) seleccion por tag y escala (metodo directo, sin raycast)
            bool sel = esf.SelectFE("I", 3);
            bool selPass = sel && esf.SelectedFE != null && esf.SelectedFE.Tag == 3;
            bool escPass = esf.EscalaActual > 0f;
            Debug.Log(string.Format("[LabViewer] [Seleccion tag3] ok={0} -> {1} | [Escala>0] {2} -> {3}",
                sel, selPass ? "OK" : "FALLO", esf.EscalaActual, escPass ? "OK" : "FALLO"));
            if (!selPass || !escPass) ok = false;

            // 7) restauracion (off limpia overlay, seleccion y resaltado)
            esf.SetOverlay(false);
            int restantes = esf.CountOverlayRenderers("I") + esf.CountOverlayRenderers("II");
            bool restPass = restantes == 0;
            Debug.Log(string.Format("[LabViewer] [Restauracion] tubos={0} -> {1}", restantes, restPass ? "OK" : "FALLO"));
            if (!restPass) ok = false;

            ok &= rayIPass && rayIIPass && rayEnvPass;
            Finish(ok);
        }

        private static void Capture(string rutaRel, EsfuerzosController esf)
        {
            GameObject fichaRoot = null;
            if (esf != null && esf.SelectedFE != null) fichaRoot = CrearFicha3D(esf);
            try
            {
                string root = new DirectoryInfo(Application.dataPath).Parent.FullName;
                string full = Path.Combine(root, rutaRel);
                string dir = Path.GetDirectoryName(full);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                    Directory.CreateDirectory(dir);
                ScreenCapture.CaptureScreenshot(full);
            }
            catch (System.Exception ex) { Debug.Log("[LabViewer] No se pudo capturar " + rutaRel + ": " + ex.Message); }
            RenderizarAPng(rutaRel); // render RT sincrono (captura sin IMGUI)
            if (fichaRoot != null) Object.DestroyImmediate(fichaRoot);
        }

        /// <summary>
        /// Seleccion por CORRESPONDENCIA viewer<->FE usando clics REALES de pantalla
        /// (el mismo camino que un usuario: Physics.Raycast del primer hit + filtro por
        /// correspondencia.viewer_id), desde varias poses de camara (las vistas incluyen
        /// elementos superpuestos en pantalla).
        /// Comprobaciones obligatorias:
        ///   * columna viewer -> FE columna del nivel correspondiente;
        ///   * viga viewer -> FE viga (nunca columna), del MISMO nivel (nunca otro piso);
        ///   * muro viewer -> FE muro del nivel correspondiente;
        ///   * si el viewer_id mostrado en la seleccion no coincide con
        ///     correspondencia.viewer_id -> FALLO (auditor falla);
        ///   * dos columnas con valores axiales distintos;
        ///   * dos vigas con My o Mz distintos;
        ///   * se ejecuta para EI y EII por separado.
        /// El punto de clic es el centroide visible del ElementRef (proyectado a pantalla
        /// por Camera.main), de modo que el usuario PODRIA pinchar esa barra y obtener
        /// los esfuerzos de ESE elemento (nunca de otra barra delante/detras).
        /// </summary>
        private static bool ProbarClicCorrespondencia(EsfuerzosController esf,
                                                     string b, string caso, int mag, int repre)
        {
            var cam = Camera.main;
            if (cam == null)
            {
                Debug.Log(string.Format("[LabViewer] [ClicCorr {0}] sin Camera.main -> FALLO", b));
                return false;
            }

            // Candidatos: FE mapeados (1A1/CONTENIDO) con valor valido y longitud util.
            var map = new Dictionary<string, List<EFElemento>>(); // viewer_id -> FE
            foreach (var e in esf.ElementosDe(b))
            {
                if (string.IsNullOrEmpty(e.ViewerId)) continue;        // SIN_CORRESPONDENCIA
                if (e.Longitud < 1.5f) continue;
                if (float.IsNaN(e.Valor(caso, mag, repre))) continue;
                List<EFElemento> grupo;
                if (!map.TryGetValue(e.ViewerId, out grupo)) { grupo = new List<EFElemento>(); map[e.ViewerId] = grupo; }
                grupo.Add(e);
            }
            if (map.Count == 0)
            {
                Debug.Log(string.Format("[LabViewer] [ClicCorr {0}] sin grupos mapeados -> FALLO", b));
                return false;
            }

            // Centro del edificio para posar la camara (varias vistas -> solapes en pantalla).
            Bounds bb = new Bounds();
            {
                bool first = true;
                foreach (var e in esf.ElementosDe(b))
                {
                    Vector3 w0 = esf.PuntoMundo(b, e.Pi), w1 = esf.PuntoMundo(b, e.Pj);
                    if (first) { bb = new Bounds(w0, Vector3.zero); first = false; }
                    bb.Encapsulate(w0); bb.Encapsulate(w1);
                }
            }
            if (bb.size.sqrMagnitude < 1f) bb.size = new Vector3(60f, 30f, 60f);
            float dist = Mathf.Max(bb.size.magnitude * 1.05f, 60f);
            Vector3[] dirs =
            {
                new Vector3(0.62f, 0.55f, 0.72f).normalized,
                new Vector3(-0.70f, 0.50f, 0.58f).normalized,
                new Vector3(0.68f, 0.45f, -0.60f).normalized,
                new Vector3(-0.62f, 0.58f, -0.62f).normalized,
            };

            Vector3 savedPos = cam.transform.position;
            Quaternion savedRot = cam.transform.rotation;

            // Invariantes verificados por cada clic:
            //   refEl = ElementRef pinchado (fuente primaria), FE = selectedFE.
            //   El FE mostrado debe tener ViewerId == refEl.Id, tipo coherente y nivel
            //   del mismo piso que refEl (o el ViewerNivel de la correspondencia).
            bool okAll = true;
            var columnasN = new List<float>();
            var vigasMy = new List<float>();
            var vigasMz = new List<float>();
            int clicsValidos = 0, clicsOcluidos = 0, clicsMapeados = 0;
            bool logCol = false, logViga = false;

            try
            {
                for (int v = 0; v < dirs.Length; v++)
                {
                    cam.transform.position = bb.center + dirs[v] * dist;
                    cam.transform.LookAt(bb.center);

                    foreach (var kv in map)
                    {
                        var refEl = BuscarElementRefEnEscena(kv.Key);
                        if (refEl == null) continue;
                        Vector3 worldCenter = esf.PuntoMundo(b, (kv.Value[0].Pi + kv.Value[0].Pj) * 0.5f);
                        Vector3 sp = cam.WorldToScreenPoint(worldCenter);
                        if (sp.z <= 0f || sp.x < 0f || sp.x > Screen.width || sp.y < 0f || sp.y > Screen.height)
                        {
                            clicsOcluidos++;
                            continue;
                        }

                        esf.ProcesarClic(new Vector2(sp.x, sp.y));
                        var fe = esf.SelectedFE;
                        var hitRef = esf.ViewerSel;
                        if (fe == null) { clicsOcluidos++; continue; }
                        if (hitRef == null) { clicsOcluidos++; continue; }
                        clicsValidos++;
                        if (!string.IsNullOrEmpty(kv.Key) && kv.Key == hitRef.Id) clicsMapeados++;

                        // CORRESPONDENCIA ESTRICTA: viewer_id mostrado == ElementRef pinchado.
                        bool idOk = fe.ViewerId == hitRef.Id;
                        bool esCol = hitRef.Type == ElemType.Columnas;
                        bool esViga = hitRef.Type == ElemType.Vigas;
                        bool esMuro = hitRef.Type == ElemType.Muros;
                        bool tipoOk = true;
                        string tipoFE = fe.Tipo != null ? fe.Tipo : "";
                        if (esCol) tipoOk = tipoFE.Contains("columna");
                        else if (esViga) tipoOk = tipoFE.Contains("viga");
                        else if (esMuro) tipoOk = tipoFE.Contains("muro");
                        // nivel: el FE del mapeo debe estar en el mismo piso del viewer
                        // (si ViewerNivel está disponible se compara contra él; en su
                        // defecto contra el Level del ElementRef).
                        bool nivelOk = true;
                        if (!string.IsNullOrEmpty(hitRef.Level))
                            nivelOk = fe.ViewerNivel == hitRef.Level;

                        if (!idOk || !tipoOk || !nivelOk)
                        {
                            Debug.Log(string.Format(
                                "[LabViewer] [ClicCorr {0}] FALLO invarianza: refEl={1}({2}, niv {3}) FE.tag={4} ViewerId={5} tipo={6} ViewerNivel={7} idOk={8} tipoOk={9} nivelOk={10}",
                                b, hitRef.Id, hitRef.Type, hitRef.Level, fe.Tag, fe.ViewerId ?? "<null>",
                                tipoFE, fe.ViewerNivel ?? "<null>", idOk, tipoOk, nivelOk));
                            okAll = false;
                            if (!Application.isBatchMode) break; // en interactivo salimos pronto
                            continue;
                        }

                        // acumular valores para la comprobacion de dos columnas / dos vigas.
                        float n = (float)esf.Valor(b, fe.Tag, caso, 0);
                        if (!float.IsNaN(n) && esCol) columnasN.Add(n);
                        float myj = fe.Valor(caso, 4, repre);
                        float mzj = fe.Valor(caso, 5, repre);
                        if (!float.IsNaN(myj) && esViga) vigasMy.Add(myj);
                        if (!float.IsNaN(mzj) && esViga) vigasMz.Add(mzj);

                        // Ejemplos positivos (uno por tipo y edificio) para la evidencia.
                        if (!logCol && esCol)
                        {
                            logCol = true;
                            Debug.Log(string.Format(
                                "[LabViewer] [ClicCorr {0}] EJEMPLO columna OK: viewer={1} (tipo {2}, niv {3}) -> FE tag={4} tipo={5} ViewerId={6} ViewerNivel={7}",
                                b, hitRef.Id, hitRef.Type, hitRef.Level, fe.Tag, tipoFE,
                                fe.ViewerId ?? "<null>", fe.ViewerNivel ?? "<null>"));
                        }
                        if (!logViga && esViga)
                        {
                            logViga = true;
                            Debug.Log(string.Format(
                                "[LabViewer] [ClicCorr {0}] EJEMPLO viga OK: viewer={1} (tipo {2}, niv {3}) -> FE tag={4} tipo={5} ViewerId={6} ViewerNivel={7}",
                                b, hitRef.Id, hitRef.Type, hitRef.Level, fe.Tag, tipoFE,
                                fe.ViewerId ?? "<null>", fe.ViewerNivel ?? "<null>"));
                        }
                    }
                }
            }
            finally
            {
                cam.transform.position = savedPos;
                cam.transform.rotation = savedRot;
            }

            // Comprobacion de valores distintos.
            bool dosColumnas = ColumnasDistintas(columnasN);
            bool dosVigas = VigasDistintas(vigasMy, vigasMz);
            string logV = "";
            if (!dosColumnas) logV += " columnasN=" + (columnasN != null ? columnasN.Count.ToString() : "0") + " sin 2 valores distintos";
            if (!dosVigas) logV += " sin 2 valores distintos en vigas (My/Mz)";

            bool pass = okAll && clicsValidos > 0 && dosColumnas && dosVigas;
            string res1 = okAll ? "OK" : "FALLO";
            string res2 = dosColumnas ? "OK" : "FALLO";
            string res3 = dosVigas ? "OK" : "FALLO";
            Debug.Log(string.Format(
                "[LabViewer] [ClicCorr {0}] clics={1} mapeodos={2} invarianza={3} dosColN={4} dosVigas={5} -> {6}{7}",
                b, clicsValidos, clicsMapeados, res1, res2, res3, pass ? "OK" : "FALLO", logV));
            return pass;
        }

        private static ElementRef BuscarElementRefEnEscena(string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            foreach (var r in Object.FindObjectsOfType<ElementRef>(true))
                if (r != null && r.Id == id) return r;
            return null;
        }

        private static bool ColumnasDistintas(List<float> valores)
        {
            for (int i = 0; i < valores.Count; i++)
                for (int j = i + 1; j < valores.Count; j++)
                    if (Mathf.Abs(valores[i] - valores[j]) > 1e-3f) return true;
            return false;
        }

        private static bool VigasDistintas(List<float> my, List<float> mz)
        {
            for (int i = 0; i < my.Count; i++)
                for (int j = i + 1; j < my.Count; j++)
                    if (Mathf.Abs(my[i] - my[j]) > 1e-3f) return true;
            for (int i = 0; i < mz.Count; i++)
                for (int j = i + 1; j < mz.Count; j++)
                    if (Mathf.Abs(mz[i] - mz[j]) > 1e-3f) return true;
            return false;
        }

        /// <summary>Crea una ficha 3D con TextMesh frente a la camara principal para que la
        /// captura RT incluya el elemento seleccionado. Se destruye tras capturar.</summary>
        private static GameObject CrearFicha3D(EsfuerzosController esf)
        {
            var cam = Camera.main;
            if (cam == null) return null;
            var e = esf.SelectedFE;
            if (e == null) return null;
            Font font = null;
            try { font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); }
            catch { font = null; }
            if (font == null) return null;

            string[] MAG = { "N", "Vy", "Vz", "T", "My", "Mz" };
            string[] REP = { "extremo i", "extremo j", "max abs" };
            string texto = "Elemento FE: tag " + e.Tag + " (" + e.Building + ")  " + e.Tipo + "  nivel " + e.Nivel;
            int m = esf.MagnitudIdxActual;
            string uni = m >= 3 ? "kN*m" : "kN";
            if (esf.CasoActual == EsfuerzosController.ENVOLVENTE && e.EnvOk)
            {
                string ci = e.EnvCasos[m], cj = e.EnvCasos[m + 6];
                string si = ci == null ? "SIN_RESULTADO" : e.EnvValores[m].ToString("0.###") + " [" + ci + "]";
                string sj = cj == null ? "SIN_RESULTADO" : e.EnvValores[m + 6].ToString("0.###") + " [" + cj + "]";
                float vr = e.Valor(EsfuerzosController.ENVOLVENTE, m, 2);
                texto += "\nEnvolvente NCh3171  " + MAG[m] + "  " + REP[2] + ":"
                         + "\n  i: " + si + "   j: " + sj
                         + "   " + vr.ToString("0.###") + " " + uni;
            }
            else
            {
                var f = e.De(esf.CasoActual);
                if (f != null)
                {
                    float vi = f[m], vj = f[m + 6], vr = e.Valor(esf.CasoActual, m, 2);
                    texto += "\n" + esf.CasoActual + "  " + MAG[m] + "  " + REP[2] + ":"
                             + "\n  i: " + vi.ToString("0.###") + "   j: " + vj.ToString("0.###")
                             + "   " + vr.ToString("0.###") + " " + uni;
                }
            }

            // — Raiz auxiliar para la ficha 3D —
            var root = new GameObject("FICHA_3D_ROOT");
            root.transform.position = Vector3.zero;
            var textGO = new GameObject("Texto");
            textGO.transform.SetParent(root.transform, false);
            var tm = textGO.AddComponent<TextMesh>();
            tm.text = texto;
            tm.font = font;
            tm.fontSize = 56;
            tm.characterSize = 0.065f;
            tm.anchor = TextAnchor.UpperLeft;
            tm.alignment = TextAlignment.Left;
            tm.color = Color.white;
            textGO.GetComponent<MeshRenderer>().material = font.material;

            // fondo oscuro semitransparente
            var bgGO = GameObject.CreatePrimitive(PrimitiveType.Quad);
            bgGO.name = "Fondo";
            bgGO.transform.SetParent(root.transform, false);
            bgGO.GetComponent<MeshRenderer>().sharedMaterial =
                new Material(Shader.Find("Standard")) { color = new Color(0.06f, 0.06f, 0.08f, 0.82f) };
            bgGO.transform.localScale = new Vector3(5.2f, 2.2f, 1f);
            bgGO.transform.localPosition = new Vector3(-0.05f, -0.15f, 0.01f);

            // Colocar frente a la camara: mas a la izquierda y arriba.
            float depth = 38f;
            Vector3 fwd = cam.transform.forward, up = cam.transform.up, right = cam.transform.right;
            root.transform.position = cam.transform.position + fwd * depth + right * (-13f) + up * (7f);
            root.transform.rotation = cam.transform.rotation;
            return root;
        }

        /// <summary>Renderiza la escena actual (play o editor) a RenderTexture y escribe PNG.
        /// Reutiliza la pose de Camera.main si existe; respeta los tubos del overlay.</summary>
        private static void RenderizarAPng(string rutaRel)
        {
            try
            {
                string root = new DirectoryInfo(Application.dataPath).Parent.FullName;
                string full = Path.Combine(root, rutaRel);
                string dir = Path.GetDirectoryName(full);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);

                var camGo = new GameObject("PlayEsfCapCam");
                var cam = camGo.AddComponent<Camera>();
                cam.enabled = false;
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = new Color(0.15f, 0.17f, 0.20f);
                cam.nearClipPlane = 0.3f;
                cam.farClipPlane = 3000f;
                var mainCam = Camera.main;
                if (mainCam != null)
                {
                    cam.transform.position = mainCam.transform.position;
                    cam.transform.rotation = mainCam.transform.rotation;
                    cam.fieldOfView = mainCam.fieldOfView;
                }
                else
                {
                    Bounds bb = new Bounds(Vector3.zero, Vector3.one);
                    bool have = false;
                    foreach (var r in Object.FindObjectsOfType<Renderer>())
                    {
                        if (!have) { bb = r.bounds; have = true; }
                        else bb.Encapsulate(r.bounds);
                    }
                    if (!have) bb.size = new Vector3(80f, 40f, 80f);
                    float d = Mathf.Max(bb.size.magnitude * 1.15f, 80f);
                    Vector3 dirIso = new Vector3(0.6f, 0.55f, 0.72f).normalized;
                    cam.transform.position = bb.center + dirIso * d;
                    cam.transform.LookAt(bb.center);
                }

                int w = 1280, h = 720;
                var rt = new RenderTexture(w, h, 24);
                cam.targetTexture = rt;
                cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
                tex.Apply();
                RenderTexture.active = null;
                File.WriteAllBytes(full, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                cam.targetTexture = null;
                rt.Release();
                Object.DestroyImmediate(camGo);
                Debug.Log("[LabViewer] Captura (render): " + rutaRel);
            }
            catch (System.Exception ex)
            {
                Debug.Log("[LabViewer] No se pudo capturar (render) " + rutaRel + ": " + ex.Message);
            }
        }

        private static void Finish(bool ok)
        {
            Debug.Log("[LabViewer] AUDIT ESFUERZOS FE: " + (ok ? "OK" : "FALLO"));
            EditorApplication.update -= Tick;
            SessionState.SetBool(RequestedKey, false);
            EditorApplication.isPlaying = false;
            if (Application.isBatchMode)
            {
                EditorApplication.Exit(ok ? 0 : 1); // salida directa en batch (sin depender de delayCall)
            }
            else
            {
                EditorApplication.delayCall += () => { if (!EditorApplication.isPlaying) LabViewerExitGuard.Finish(ok ? 0 : 1); };
            }
        }

        [MenuItem("LabViewer/Verificar overlay esfuerzos FE (modo play)")]
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
