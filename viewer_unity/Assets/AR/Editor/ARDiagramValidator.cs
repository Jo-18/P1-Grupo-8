using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LabViewer;
using LabViewer.AR;

namespace LabViewer.AR.EditorTools
{
    // Auditoria Editor (sin PlayMode) del setup de diagramas AR del tag 489:
    // estructura y forma del JSON persistido + wiring de la escena ARMain.
    // Ejecutable en batch:
    //   Unity -batchmode -quit -projectPath <viewer> \
    //     -executeMethod LabViewer.AR.EditorTools.ARDiagramValidator.BatchValidate
    // Tolerancias documentadas de la propia auditoria (solo Editor, nunca se
    // usan para dibujar): lineas constantes/extremos 0.001; pendiente dMy/dx 0.01.
    public static class ARDiagramValidator
    {
        const string DiagramJsonRel = "StreamingAssets/lab_data/edificios/II/results/diagramas_FE_tag489_G.json";
        const string ScenePath = "Assets/Scenes/ARMain.unity";
        const string Tag = "[ARValidateDiagram] ";
        const double TolLinea = 0.001;
        const double TolPendiente = 0.01;

        [MenuItem("LabViewer AR/Validar diagramas AR tag 489")]
        public static void ValidateFromMenu()
        {
            Ejecutar(false);
        }

        public static void BatchValidate()
        {
            Ejecutar(true);
        }

        static void Ejecutar(bool batch)
        {
            var res = new Dictionary<string, object>
            {
                ["tarea"] = "AR_DIAGRAM_VALIDATION",
                ["fecha"] = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
                ["editor"] = Application.unityVersion
            };
            var errores = new List<string>();

            try
            {
                string abs = Path.Combine(Application.dataPath, DiagramJsonRel);
                Dictionary<string, object> raiz = Json.AsObj(Json.Parse(File.ReadAllText(abs)));
                if (raiz == null)
                {
                    errores.Add("JSON no es objeto: " + abs);
                }
                else
                {
                    AuditorJson(raiz, res, errores);
                    AuditorEscena(res, errores);
                    AuditorSuperficie(raiz, res, errores);
                }
            }
            catch (Exception e)
            {
                errores.Add("excepcion: " + e.Message);
            }

            res["total_errores"] = errores.Count;
            res["errores"] = errores;
            res["resultado"] = errores.Count == 0 ? "OK" : "ERROR";

            string reporte = Path.Combine(Path.GetTempPath(), "AR_DIAGRAM_VALIDATION_resultado.json");
            File.WriteAllText(reporte, JsonEscribir(res));
            Debug.Log(Tag + "Reporte: " + reporte);

            string linea = Tag + "resultado=" + res["resultado"] + " errores=" + errores.Count;
            foreach (var e in errores) linea += "\n" + Tag + "  - " + e;
            if (errores.Count == 0) Debug.Log(Tag + "Validacion OK (JSON + escena)");
            else Debug.LogError(linea);

            if (batch)
                EditorApplication.Exit(errores.Count == 0 ? 0 : 1);
        }

        static void AuditorJson(Dictionary<string, object> raiz, Dictionary<string, object> res, List<string> errores)
        {
            res["formato"] = Json.Str(raiz, "formato");
            res["version"] = (long)Json.Num(raiz, "version");
            res["edificio"] = Json.Str(raiz, "edificio");
            res["elementTag"] = (long)Json.Num(raiz, "elementTag");
            res["viewer_id"] = Json.Str(raiz, "viewer_id");
            res["nivel"] = Json.Str(raiz, "nivel");
            res["caso"] = Json.Str(raiz, "caso");
            res["longitud_m"] = Json.Num(raiz, "longitud_m");
            res["n_stations"] = (long)Json.Num(raiz, "n_stations", -1);
            res["seccion"] = Json.Str(raiz, "seccion");

            var nod = raiz.TryGetValue("nodos", out var nv) ? Json.AsObj(nv) : null;
            res["nodos"] = nod != null
                ? new Dictionary<string, object> { ["i"] = Json.Str(nod, "i"), ["j"] = Json.Str(nod, "j") }
                : null;

            var uni = raiz.TryGetValue("unidades", out var uv) ? Json.AsObj(uv) : null;
            res["unidades"] = uni != null
                ? new Dictionary<string, object> { ["fuerza"] = Json.Str(uni, "fuerza"), ["momento"] = Json.Str(uni, "momento"), ["longitud"] = Json.Str(uni, "longitud") }
                : null;

            var comp = Json.Arr(raiz, "comprobaciones");
            int compTotal = comp != null ? comp.Count : 0;
            int compOk = 0;
            if (comp != null)
            {
                foreach (var c in comp)
                {
                    var item = Json.AsObj(c);
                    if (item != null && Json.Bool(item, "ok")) compOk++;
                }
            }
            res["comprobaciones_total"] = compTotal;
            res["comprobaciones_ok"] = compOk;

            var pf = raiz.TryGetValue("payload_fuente", out var pfv) ? Json.AsObj(pfv) : null;
            res["payload_fuente_archivo"] = pf != null ? Json.Str(pf, "archivo") : null;
            res["payload_fuente_sha256"] = pf != null ? Json.Str(pf, "sha256") : null;

            var vec = Json.Arr(raiz, "vector_localForce_12_caso_G");
            var vecVals = new List<double>();
            if (vec != null)
            {
                for (int i = 0; i < vec.Count && i < 12; i++) vecVals.Add(Json.ToNum(vec[i]));
            }
            res["vector_localForce_12_caso_G"] = vecVals;

            // Validacion estructural compartida con el runtime.
            errores.AddRange(ARForceDiagram489.Validar(raiz, "II", 489, "EII_CP2_V_029", "G", 3.05f, 51));

            // Auditoria de forma (Editor): comprobar que las curvas cumplen la
            // convencion interna derivada del propio vector (no se hardcodea el
            // resultado para dibujar; esto solo verifica la coherencia de datos).
            if (vecVals.Count >= 12)
            {
                double vz = vecVals[2];
                double t = vecVals[3];
                double myI = vecVals[4];
                double L = Json.Num(raiz, "longitud_m");
                double myL = myI + vz * L;

                var stations = Json.Arr(raiz, "stations");
                double maxVzDif = 0, maxTDif = 0, maxSlopeDif = 0, maxMyExtremos = 0;
                double maxN = 0, maxVy = 0, maxMz = 0, maxAbsVz = 0, maxAbsMy = 0;
                int cruceMy = -1;

                if (stations == null || stations.Count == 0)
                {
                    errores.Add("sin stations para auditoria de forma");
                }
                else
                {
                    for (int i = 0; i < stations.Count; i++)
                    {
                        var s = Json.AsObj(stations[i]);
                        if (s == null) continue;

                        double N = Json.Num(s, "N_kN");
                        double vy = Json.Num(s, "Vy_kN");
                        double vzi = Json.Num(s, "Vz_kN");
                        double ti = Json.Num(s, "T_kN_m");
                        double my = Json.Num(s, "My_kN_m");
                        double mz = Json.Num(s, "Mz_kN_m");

                        maxVzDif = Math.Max(maxVzDif, Math.Abs(vzi - vz));
                        maxTDif = Math.Max(maxTDif, Math.Abs(ti - t));
                        maxN = Math.Max(maxN, Math.Abs(N));
                        maxVy = Math.Max(maxVy, Math.Abs(vy));
                        maxMz = Math.Max(maxMz, Math.Abs(mz));
                        maxAbsVz = Math.Max(maxAbsVz, Math.Abs(vzi));
                        maxAbsMy = Math.Max(maxAbsMy, Math.Abs(my));

                        if (i > 0)
                        {
                            double xA = Json.Num(s, "x_m");
                            var prev = Json.AsObj(stations[i - 1]);
                            if (prev != null)
                            {
                                double xB = Json.Num(prev, "x_m");
                                double myB = Json.Num(prev, "My_kN_m");
                                if (xA > xB)
                                {
                                    double pend = (my - myB) / (xA - xB);
                                    maxSlopeDif = Math.Max(maxSlopeDif, Math.Abs(pend - vz));
                                }
                                if (cruceMy < 0 && myB < 0 && my >= 0) cruceMy = i - 1;
                            }
                        }
                    }

                    maxMyExtremos = Math.Max(Math.Abs(Json.Num(Json.AsObj(stations[0]), "My_kN_m") - myI),
                                             Math.Abs(Json.Num(Json.AsObj(stations[stations.Count - 1]), "My_kN_m") - myL));
                }

                res["es_vz_constante_max_dif"] = maxVzDif;
                res["es_t_constante_max_dif"] = maxTDif;
                res["my_lineal_max_dif_pendiente_vs_vz"] = maxSlopeDif;
                res["my_extremos_max_dif"] = maxMyExtremos;
                res["my_cero_entre_k"] = cruceMy;
                res["max_abs_N"] = maxN;
                res["max_abs_Vy"] = maxVy;
                res["max_abs_Mz"] = maxMz;
                res["max_abs_Vz"] = maxAbsVz;
                res["max_abs_My"] = maxAbsMy;

                if (maxVzDif > TolLinea) errores.Add("Vz no constante (max|dif|=" + maxVzDif.ToString("0.000000", CultureInfo.InvariantCulture) + ")");
                if (maxTDif > TolLinea) errores.Add("T no constante (max|dif|=" + maxTDif.ToString("0.000000", CultureInfo.InvariantCulture) + ")");
                if (maxSlopeDif > TolPendiente) errores.Add("dMy/dx != Vz (max|dif|=" + maxSlopeDif.ToString("0.000000", CultureInfo.InvariantCulture) + ")");
                if (maxMyExtremos > TolLinea) errores.Add("My extremos != (My_i, My_i+Vz*L) (max|dif|=" + maxMyExtremos.ToString("0.000000", CultureInfo.InvariantCulture) + ")");
                if (cruceMy < 0) errores.Add("My no cruza de negativo a positivo");
                if (maxN > TolLinea || maxVy > TolLinea || maxMz > TolLinea)
                    errores.Add("N/Vy/Mz no son nulos (max=" + Math.Max(maxN, Math.Max(maxVy, maxMz)).ToString("0.000000", CultureInfo.InvariantCulture) + ")");

                // Unidades/indices de la convencion interna del payload.
                if (maxAbsVz > TolLinea && Math.Abs(maxAbsVz - Math.Abs(vz)) > TolLinea)
                    errores.Add("maxAbs(Vz) no coincide con |Vz| del vector");
                if (maxAbsMy > TolLinea && Math.Abs(maxAbsMy - Math.Max(Math.Abs(myI), Math.Abs(myL))) > TolLinea)
                    errores.Add("maxAbs(My) no coincide con extremos esperados");

                if (compOk != compTotal)
                    errores.Add("hay comprobaciones fallidas (" + compOk + "/" + compTotal + ")");
                if (res["unidades"] == null) errores.Add("sin unidades");

                // Los valores esperados de la tabla se reportan como referencia.
                res["extremos_esperados"] = new Dictionary<string, object>
                {
                    ["N"] = 0.0,
                    ["Vy"] = 0.0,
                    ["Vz"] = vz,
                    ["T"] = t,
                    ["My_i"] = myI,
                    ["My_L"] = myL,
                    ["Mz"] = 0.0
                };
            }
            else
            {
                errores.Add("vector_localForce_12_caso_G incompleto");
            }

            // Magnitud inicial del selector (Vz) y coherencia del mapeo de claves.
            if (ARForceDiagram489.Magnitudes.Length != 6 || !string.Equals(ARForceDiagram489.Magnitudes[2], "Vz", StringComparison.Ordinal))
                errores.Add("mapping de magnitudes del runtime alterado (esperado N,Vy,Vz,T,My,Mz)");
            res["magnitud_inicial"] = ARForceDiagram489.Magnitudes.Length == 6 ? ARForceDiagram489.Magnitudes[2] : null;
            res["magnitudes"] = ARForceDiagram489.Magnitudes;
        }

        static void AuditorEscena(Dictionary<string, object> res, List<string> errores)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            res["escena"] = ScenePath;

            GameObject content = null;
            foreach (var root in scene.GetRootGameObjects())
            {
                if (root.name == "AR Content") { content = root; break; }
            }
            if (content == null)
            {
                errores.Add("no se encontro AR Content en la escena");
                return;
            }

            res["ar_content"] = true;
            var controller = content.GetComponent<ARImageAnchorController>();
            var loader = content.GetComponent<ARBeam489Loader>();
            var label = content.GetComponent<ARResult489Label>();
            var diagram = content.GetComponent<ARForceDiagram489>();

            int cantDiagram = 0;
            foreach (var c in content.GetComponents<ARForceDiagram489>()) cantDiagram++;
            var raices = scene.GetRootGameObjects();
            int totalDiagram = 0;
            foreach (var r in raices) totalDiagram += r.GetComponentsInChildren<ARForceDiagram489>(true).Length;

            if (controller == null) errores.Add("AR Content sin ARImageAnchorController");
            if (loader == null) errores.Add("AR Content sin ARBeam489Loader");
            if (label == null) errores.Add("AR Content sin ARResult489Label");
            if (diagram == null) errores.Add("AR Content sin ARForceDiagram489");
            if (totalDiagram != 1) errores.Add("cantidad de ARForceDiagram489 en escena = " + totalDiagram + " (esperado 1)");

            bool refsOk = diagram != null;
            if (diagram != null)
            {
                var so = new SerializedObject(diagram);
                refsOk &= so.FindProperty("m_Controller").objectReferenceValue == controller;
                refsOk &= so.FindProperty("m_Loader").objectReferenceValue == loader;
                refsOk &= so.FindProperty("m_Label").objectReferenceValue == label;
                refsOk &= so.FindProperty("m_ContentRoot").objectReferenceValue == content.transform;
                refsOk &= so.FindProperty("m_BaseMaterial").objectReferenceValue != null;
                refsOk &= so.FindProperty("m_DiagramMaterial").objectReferenceValue != null;
                refsOk &= so.FindProperty("m_OrdinateMaterial").objectReferenceValue != null;
                float amp = so.FindProperty("m_AmplitudMaxima").floatValue;
                res["amplitud_visual_m"] = amp;
                if (Math.Abs(amp - 0.035f) > 0.0001f) errores.Add("amplitud visual != 0.035 m");
            }
            if (label != null)
            {
                var nso = new SerializedObject(label);
                refsOk &= nso.FindProperty("m_Diagrama").objectReferenceValue == diagram;
            }
            else
            {
                refsOk = false;
            }

            // La viga se mantiene opaca: el diagrama se ve por estar sobre la cara,
            // no por transparentar el solido.
            if (loader != null)
            {
                var lso = new SerializedObject(loader);
                var matViga = lso.FindProperty("m_BeamMaterial").objectReferenceValue as Material;
                if (matViga == null)
                {
                    errores.Add("la viga no tiene material asignado");
                }
                else
                {
                    res["material_viga"] = matViga.name + "/cola=" + matViga.renderQueue;
                    if (matViga.renderQueue > 2500)
                        errores.Add("la viga esta en cola transparente (renderQueue=" + matViga.renderQueue + ")");
                }
            }

            res["refs_serializadas_ok"] = refsOk;
            if (!refsOk) errores.Add("referencias serializadas del diagrama/label incompletas");
            res["conteo_diagrama_en_contenido"] = cantDiagram;
        }

        // Auditoria T32 de la superficie: construye un diagrama con los MISMOS
        // puntos de transicion del runtime (loader en estado terminal correcto +
        // AceptarJson + NotificarLoaderTerminado) y comprueba, en el sistema local
        // de la viga, que la curva vive sobre una cara lateral, dentro de la
        // silueta, y que el cambio de cara no reconstruye la geometria.
        static void AuditorSuperficie(Dictionary<string, object> raiz, Dictionary<string, object> res, List<string> errores)
        {
            const float LongitudAR = 0.305f;
            const float AltoAR = 0.080f;
            const float AnchoAR = 0.030f;
            const double TolPos = 0.0002;

            GameObject root = new GameObject("AR_ValidacionSuperficie");
            try
            {
                var loader = root.AddComponent<ARBeam489Loader>();
                var controlador = root.AddComponent<ARImageAnchorController>();
                var diagrama = root.AddComponent<ARForceDiagram489>();

                var idGo = new GameObject("identidad");
                idGo.transform.SetParent(root.transform, false);
                var identidad = idGo.AddComponent<ARElementIdentity>();
                identidad.Init(489, "EII_CP2_V_029", "II", "viga", "V.30/80");

                // Viga de la prueba con las dimensiones AR reales de la seccion.
                var viga = GameObject.CreatePrimitive(PrimitiveType.Cube);
                viga.name = "FE_TAG_489_EII_CP2_V_029";
                viga.transform.SetParent(root.transform, false);
                viga.transform.localPosition = Vector3.zero;
                viga.transform.localRotation = Quaternion.identity;
                viga.transform.localScale = new Vector3(LongitudAR, AltoAR, AnchoAR);
                var col = viga.GetComponent<Collider>();
                if (col != null) UnityEngine.Object.DestroyImmediate(col);
                viga.AddComponent<ARElementIdentity>().Init(489, "EII_CP2_V_029", "II", "viga", "V.30/80");

                PonerCampo(loader, "m_Beam", viga);
                PonerCampo(loader, "m_Identity", identidad);
                PonerCampo(loader, "m_DataLoaded", true);
                PonerCampo(loader, "m_LoadCompleted", true);
                PonerCampo(loader, "m_LoadSucceeded", true);
                PonerCampo(loader, "m_LoadError", null);
                PonerCampo(loader, "m_VigaLongitudM", 3.05f);
                PonerCampo(loader, "m_VigaLongitudAR", LongitudAR);
                PonerCampo(loader, "m_VigaAltoAR", AltoAR);
                PonerCampo(loader, "m_VigaAnchoAR", AnchoAR);
                PonerCampo(loader, "m_VigaCentroLocal", Vector3.zero);
                PonerCampo(loader, "m_VigaPILocal", new Vector3(-LongitudAR * 0.5f, 0f, 0f));
                PonerCampo(loader, "m_VigaPJLocal", new Vector3(LongitudAR * 0.5f, 0f, 0f));

                var so = new SerializedObject(diagrama);
                so.FindProperty("m_Loader").objectReferenceValue = loader;
                so.FindProperty("m_Controller").objectReferenceValue = controlador;
                so.FindProperty("m_ContentRoot").objectReferenceValue = root.transform;
                so.FindProperty("m_Label").objectReferenceValue = null;
                so.FindProperty("m_AmplitudMaxima").floatValue = 0.035f;
                // Materiales versionados reales del proyecto (T32).
                so.FindProperty("m_BaseMaterial").objectReferenceValue = Material("Assets/AR/Materials/DiagramBase489.mat", errores);
                so.FindProperty("m_DiagramMaterial").objectReferenceValue = Material("Assets/AR/Materials/DiagramLine489.mat", errores);
                so.FindProperty("m_OrdinateMaterial").objectReferenceValue = Material("Assets/AR/Materials/DiagramOrdinate489.mat", errores);
                so.ApplyModifiedPropertiesWithoutUndo();

                diagrama.AceptarJson(raiz);
                diagrama.NotificarLoaderTerminado();

                if (diagrama.Fallido || !diagrama.DataLoaded || diagrama.Contenedor == null)
                {
                    errores.Add("el diagrama no se construyo con la viga de prueba (fallido="
                        + diagrama.Fallido + " datos=" + diagrama.DataLoaded
                        + " contenedor=" + (diagrama.Contenedor != null) + ")");
                    return;
                }

                Transform cont = diagrama.Contenedor;
                res["amplitud_efectiva_m"] = diagrama.AmplitudEfectiva;
                res["offset_superficial_m"] = diagrama.OffsetSuperficialM;
                res["histeresis_m"] = diagrama.HisteresisM;
                res["estaciones"] = diagrama.StationCount;

                // 1) Solo hay un diagrama y comparte el sistema de ejes de la viga.
                int contenedores = 0;
                foreach (var r in root.GetComponentsInChildren<Transform>(true))
                    if (r.name == "AR489_Diagrama") contenedores++;
                res["contenedores_diagrama"] = contenedores;
                if (contenedores != 1) errores.Add("contenedores AR489_Diagrama = " + contenedores + " (esperado 1)");
                if (cont.parent != root.transform)
                    errores.Add("el contenedor del diagrama no cuelga del AR Content (sigue al anchor)");
                if (Quaternion.Angle(cont.rotation, viga.transform.rotation) > 0.01f)
                    errores.Add("los ejes del contenedor no coinciden con los de la viga");
                // Escala 1 en toda la cadena: sin escala, los puntos y los
                // espesores de linea son exactamente los que se escribieron.
                Vector3 escala = cont.lossyScale;
                res["escala_contenedor"] = escala.x + "," + escala.y + "," + escala.z;
                if (Mathf.Abs(escala.x - 1f) > 0.001f || Mathf.Abs(escala.y - 1f) > 0.001f || Mathf.Abs(escala.z - 1f) > 0.001f)
                    errores.Add("el contenedor del diagrama tiene escala " + escala + " (se deforma la linea)");

                // 2) Amplitud efectiva dentro de la silueta: <= alto/2 - margen.
                float maxOrdenada = 0f;
                for (int k = 0; k < diagrama.StationCount; k++)
                    maxOrdenada = Mathf.Max(maxOrdenada, Mathf.Abs(diagrama.OrdenadaDe(k)));
                res["max_abs_ordenada_m"] = maxOrdenada;
                res["margen_silueta_m"] = diagrama.MargenSiluetaM;
                if (diagrama.AmplitudEfectiva > AltoAR * 0.5f - diagrama.MargenSiluetaM + (float)TolPos)
                    errores.Add("amplitud efectiva " + diagrama.AmplitudEfectiva + " > alto/2 - margen");
                if (diagrama.AmplitudEfectiva > 0.035f + (float)TolPos)
                    errores.Add("amplitud efectiva " + diagrama.AmplitudEfectiva + " > 0.035 m");
                if (maxOrdenada > 0.035f + (float)TolPos)
                    errores.Add("ordenada fuera de la silueta (max|y|=" + maxOrdenada + " m)");

                // 3) Todos los puntos dentro de la longitud, sobre la cara y dentro
                //    de la silueta, medidos en metros AR sobre los ejes de la viga
                //    (X longitudinal, Y ordenada, Z caras laterales). La viga codifica
                //    sus dimensiones en localScale, por eso la medicion se hace
                //    proyectando el offset respecto del centro sobre sus ejes.
                float mitad = LongitudAR * 0.5f;
                float caraEsperada = diagrama.SignoCara * (AnchoAR * 0.5f + diagrama.OffsetSuperficialM);
                var lineas = new[] { diagrama.LineaBase, diagrama.LineaDiagrama, diagrama.LineaOrdenadas };
                for (int li = 0; li < lineas.Length; li++)
                {
                    var lr = lineas[li];
                    if (lr == null)
                    {
                        errores.Add("LineRenderer " + li + " ausente");
                        continue;
                    }
                    for (int i = 0; i < lr.positionCount; i++)
                    {
                        Vector3 m = MetrosLocales(viga.transform, cont.TransformPoint(lr.GetPosition(i)));
                        if (Mathf.Abs(m.x) > mitad + (float)TolPos)
                            errores.Add("punto fuera de la longitud de la viga (x=" + m.x + " m)");
                        if (Mathf.Abs(m.y) > 0.035f + (float)TolPos)
                            errores.Add("punto fuera de la silueta (y=" + m.y + " m)");
                        if (Mathf.Abs(m.z - caraEsperada) > (float)TolPos)
                            errores.Add("punto fuera del plano de la cara (z=" + m.z + " m, esperado "
                                + caraEsperada + " m)");
                    }
                }
                res["max_abs_x_m"] = halfLengthOf(diagrama.LineaDiagrama, cont, viga.transform);
                Vector3 contLocal = MetrosLocales(viga.transform, cont.position);
                res["contenedor_en_sistema_viga_m"] = contLocal.x.ToString("0.0000", CultureInfo.InvariantCulture)
                    + ", " + contLocal.y.ToString("0.0000", CultureInfo.InvariantCulture)
                    + ", " + contLocal.z.ToString("0.0000", CultureInfo.InvariantCulture);

                // 4) Profundidad en una de las dos caras laterales + offset previsto.
                float z = contLocal.z;
                float z1 = AnchoAR * 0.5f + diagrama.OffsetSuperficialM;
                if (Math.Abs(Math.Abs(z) - z1) > (float)TolPos)
                    errores.Add("profundidad del contenedor (" + z + " m) no coincide con ninguna cara lateral");
                if (diagrama.OffsetSuperficialM < 0.001f - (float)TolPos || diagrama.OffsetSuperficialM > 0.002f + (float)TolPos)
                    errores.Add("offset superficial " + diagrama.OffsetSuperficialM + " m fuera de [0.001, 0.002]");
                if (Mathf.Abs(contLocal.x) > (float)TolPos || Mathf.Abs(contLocal.y) > (float)TolPos)
                    errores.Add("el contenedor no esta centrado en la cara lateral");

                // 5) Materiales asignados, sin iluminacion y con buen contraste.
                string[] nombres = { "Base", "Diagrama", "Ordenadas" };
                for (int li = 0; li < lineas.Length; li++)
                {
                    var lr = lineas[li];
                    if (lr == null) continue;
                    var mat = lr.sharedMaterial;
                    if (mat == null)
                    {
                        errores.Add(nombres[li] + ": material no asignado");
                        continue;
                    }
                    var sh = mat.shader;
                    bool sinIluminacion = sh == null
                        || sh.name.IndexOf("Unlit", StringComparison.OrdinalIgnoreCase) >= 0
                        || sh.name.IndexOf("Sprites/Default", StringComparison.OrdinalIgnoreCase) >= 0;
                    if (!sinIluminacion)
                        errores.Add(nombres[li] + ": shader '" + sh.name + "' no es sin iluminacion");
                    if (lr.shadowCastingMode != UnityEngine.Rendering.ShadowCastingMode.Off || lr.receiveShadows)
                        errores.Add(nombres[li] + ": la linea proyecta o recibe sombras");
                    var color = mat.HasProperty("_Color") ? mat.GetColor("_Color") : Color.white;
                    res["material_" + nombres[li].ToLowerInvariant()] = mat.name + "/" + (sh != null ? sh.name : "null")
                        + "/ancho=" + lr.startWidth.ToString("0.0000", CultureInfo.InvariantCulture)
                        + "/rgb=" + color.r.ToString("0.00", CultureInfo.InvariantCulture) + ","
                            + color.g.ToString("0.00", CultureInfo.InvariantCulture) + ","
                            + color.b.ToString("0.00", CultureInfo.InvariantCulture) + ","
                            + color.a.ToString("0.00", CultureInfo.InvariantCulture);
                }
                float anchoLinea = diagrama.LineaDiagrama != null ? diagrama.LineaDiagrama.startWidth : 0f;
                float anchoBase = diagrama.LineaBase != null ? diagrama.LineaBase.startWidth : 0f;
                float anchoOrd = diagrama.LineaOrdenadas != null ? diagrama.LineaOrdenadas.startWidth : 0f;
                res["ancho_linea_m"] = anchoLinea;
                res["ancho_base_m"] = anchoBase;
                res["ancho_ordenada_m"] = anchoOrd;
                if (anchoLinea < 0.004f - (float)TolPos || anchoLinea > 0.006f + (float)TolPos)
                    errores.Add("espesor de la curva " + anchoLinea + " m fuera de [0.004, 0.006]");
                if (anchoBase < 0.002f - (float)TolPos || anchoBase > 0.003f + (float)TolPos)
                    errores.Add("espesor de la base " + anchoBase + " m fuera de [0.002, 0.003]");
                if (anchoOrd < 0.0015f - (float)TolPos || anchoOrd > 0.0025f + (float)TolPos)
                    errores.Add("espesor de las ordenadas " + anchoOrd + " m fuera de [0.0015, 0.0025]");

                // 6) Selector inicial Vz.
                res["magnitud_seleccionada"] = diagrama.MagnitudActual;
                if (diagrama.MagnitudIndex != 2 || !string.Equals(diagrama.MagnitudActual, "Vz", StringComparison.Ordinal))
                    errores.Add("magnitud inicial != Vz (" + diagrama.MagnitudActual + ")");

                // 7) My conserva el cruce por cero en la curva dibujada.
                diagrama.SeleccionarMagnitud(4);
                int cruce = -1;
                float previa = diagrama.OrdenadaDe(0);
                float myI = diagrama.ValorEstacion(0);
                float myL = diagrama.ValorEstacion(diagrama.StationCount - 1);
                for (int k = 1; k < diagrama.StationCount; k++)
                {
                    float actual = diagrama.OrdenadaDe(k);
                    if (previa < 0f && actual >= 0f) { cruce = k - 1; break; }
                    previa = actual;
                }
                res["my_cruce_cero_entre_k"] = cruce;
                res["my_extremos_dibujados"] = new Dictionary<string, object>
                {
                    ["i"] = myI,
                    ["L"] = myL,
                    ["ordenada_i"] = diagrama.OrdenadaDe(0),
                    ["ordenada_L"] = diagrama.OrdenadaDe(diagrama.StationCount - 1)
                };
                if (cruce < 0) errores.Add("la curva My dibujada no cruza por cero");
                if (myI >= 0f || myL <= 0f) errores.Add("My no va de negativo a positivo");
                diagrama.SeleccionarMagnitud(2);
                if (!string.Equals(diagrama.MagnitudActual, "Vz", StringComparison.Ordinal))
                    errores.Add("no se pudo volver a Vz tras la auditoria de My");

                // 8) Cambio de cara: no reconstruye ni un punto.
                int construccionesAntes = diagrama.ConteoConstrucciones;
                int nCurva = diagrama.LineaDiagrama != null ? diagrama.LineaDiagrama.positionCount : 0;
                int nBase = diagrama.LineaBase != null ? diagrama.LineaBase.positionCount : 0;
                int nOrd = diagrama.LineaOrdenadas != null ? diagrama.LineaOrdenadas.positionCount : 0;
                float[] antes = CopiarY(diagrama.LineaDiagrama);
                float zAntes = MetrosLocales(viga.transform, cont.position).z;

                // Cerca del plano central la histeresis mantiene el lado actual.
                bool cambioCerca = diagrama.ActualizarCaraVisible(viga.transform.TransformPoint(new Vector3(0f, 0f, -0.005f)));
                // Al otro lado, fuera de la banda, cambia de cara.
                bool cambioLejos = diagrama.ActualizarCaraVisible(viga.transform.TransformPoint(new Vector3(0f, 0f, -0.06f)));
                float zDespues = MetrosLocales(viga.transform, cont.position).z;

                res["cambio_cerca_histeresis"] = cambioCerca;
                res["cambio_lejos"] = cambioLejos;
                res["cambios_cara"] = diagrama.ConteoCambiosCara;
                res["z_antes_m"] = zAntes;
                res["z_despues_m"] = zDespues;

                if (cambioCerca) errores.Add("la histeresis cambio de cara con la camara en el plano central");
                if (!cambioLejos) errores.Add("el diagrama no cambio de cara al pasar la camara al otro lado");
                if (Math.Abs(zDespues + zAntes) > (float)TolPos)
                    errores.Add("la cara visible no se invio (z " + zAntes + " -> " + zDespues + ")");
                if (diagrama.ConteoConstrucciones != construccionesAntes)
                    errores.Add("el cambio de cara reconstruyo la geometria");
                if ((diagrama.LineaDiagrama != null ? diagrama.LineaDiagrama.positionCount : 0) != nCurva
                    || (diagrama.LineaBase != null ? diagrama.LineaBase.positionCount : 0) != nBase
                    || (diagrama.LineaOrdenadas != null ? diagrama.LineaOrdenadas.positionCount : 0) != nOrd)
                    errores.Add("el cambio de cara altero el numero de puntos");
                float[] despues = CopiarY(diagrama.LineaDiagrama);
                for (int i = 0; i < Math.Min(antes.Length, despues.Length); i++)
                    if (Math.Abs(antes[i] - despues[i]) > (float)TolPos)
                    { errores.Add("el cambio de cara movio las ordenadas de la curva"); break; }

                // La cara nueva sigue siendo una de las dos caras laterales.
                if (Math.Abs(Math.Abs(zDespues) - z1) > (float)TolPos)
                    errores.Add("la cara tras el cambio no es una cara lateral (z=" + zDespues + " m)");
            }
            catch (Exception e)
            {
                errores.Add("excepcion en la auditoria de superficie: " + e.Message);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        static Material Material(string path, List<string> errores)
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) errores.Add("material ausente: " + path);
            return mat;
        }

        // Coordenadas en metros AR sobre los ejes de la viga. La viga guarda sus
        // dimensiones en localScale (0.305, 0.080, 0.030), por lo que su espacio
        // local NO esta en metros: se proyecta el offset respecto del centro de la
        // viga sobre sus ejes del mundo (right/up/forward).
        static Vector3 MetrosLocales(Transform viga, Vector3 puntoMundo)
        {
            Vector3 d = puntoMundo - viga.position;
            return new Vector3(Vector3.Dot(d, viga.right), Vector3.Dot(d, viga.up), Vector3.Dot(d, viga.forward));
        }

        static float halfLengthOf(LineRenderer lr, Transform cont, Transform viga)
        {
            if (lr == null || lr.positionCount == 0) return 0f;
            float max = 0f;
            for (int i = 0; i < lr.positionCount; i++)
                max = Mathf.Max(max, Mathf.Abs(MetrosLocales(viga, cont.TransformPoint(lr.GetPosition(i))).x));
            return max;
        }

        static float[] CopiarY(LineRenderer lr)
        {
            if (lr == null) return new float[0];
            var ys = new float[lr.positionCount];
            for (int i = 0; i < lr.positionCount; i++) ys[i] = lr.GetPosition(i).y;
            return ys;
        }

        static void PonerCampo(object target, string nombre, object valor)
        {
            FieldInfo f = typeof(ARBeam489Loader).GetField(nombre, BindingFlags.NonPublic | BindingFlags.Instance);
            if (f == null) throw new InvalidOperationException("campo ARBeam489Loader." + nombre + " no encontrado");
            f.SetValue(target, valor);
        }

        static string JsonEscribir(Dictionary<string, object> obj)
        {
            var sb = new System.Text.StringBuilder();
            sb.Append('{');
            bool primero = true;
            foreach (var kv in obj)
            {
                if (!primero) sb.Append(',');
                primero = false;
                sb.Append('"').Append(EscapeJson(kv.Key)).Append("\":");
                sb.Append(JsonValor(kv.Value));
            }
            sb.Append('}');
            return sb.ToString();
        }

        static string JsonValor(object v)
        {
            if (v == null) return "null";
            if (v is string s) return "\"" + EscapeJson(s) + "\"";
            if (v is bool b) return b ? "true" : "false";
            if (v is int i) return i.ToString(CultureInfo.InvariantCulture);
            if (v is long l) return l.ToString(CultureInfo.InvariantCulture);
            if (v is float f) return f.ToString(CultureInfo.InvariantCulture);
            if (v is double d) return d.ToString(CultureInfo.InvariantCulture);
            if (v is System.Collections.IDictionary dic)
            {
                var sb = new System.Text.StringBuilder();
                sb.Append('{');
                bool p = true;
                foreach (System.Collections.DictionaryEntry de in dic)
                {
                    if (!p) sb.Append(',');
                    p = false;
                    sb.Append('"').Append(EscapeJson(Convert.ToString(de.Key, CultureInfo.InvariantCulture))).Append("\":");
                    sb.Append(JsonValor(de.Value));
                }
                sb.Append('}');
                return sb.ToString();
            }
            if (v is System.Collections.IEnumerable e)
            {
                var sb = new System.Text.StringBuilder();
                sb.Append('[');
                bool p = true;
                foreach (object item in e)
                {
                    if (!p) sb.Append(',');
                    p = false;
                    sb.Append(JsonValor(item));
                }
                sb.Append(']');
                return sb.ToString();
            }
            return "\"" + EscapeJson(v.ToString()) + "\"";
        }

        static string EscapeJson(string t)
        {
            return t.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n").Replace("\t", "\\t");
        }
    }
}