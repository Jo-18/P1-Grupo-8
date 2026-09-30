using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
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
                if (Math.Abs(amp - 0.065f) > 0.0001f) errores.Add("amplitud visual != 0.065 m");
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

            res["refs_serializadas_ok"] = refsOk;
            if (!refsOk) errores.Add("referencias serializadas del diagrama/label incompletas");
            res["conteo_diagrama_en_contenido"] = cantDiagram;
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