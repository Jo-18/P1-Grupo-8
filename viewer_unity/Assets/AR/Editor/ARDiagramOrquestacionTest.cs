using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using LabViewer;
using LabViewer.AR;

namespace LabViewer.AR.EditorTools
{
    // Prueba controlada (EditMode, sin PlayMode) de la coordinacion de carga del
    // diagrama AR frente al loader de la viga (T31D). Simula explicitamente el
    // orden registrado en el telefono (el diagrama obtiene su JSON antes de que
    // el loader este listo) y los ordenes opuestos, usando los MISMOS puntos de
    // transicion del runtime (AceptarJson / NotificarLoaderTerminado /
    // NotificarAnchor), que son idempotentes y por-fase.
    //
    // Ejecutable en batch:
    //   Unity -batchmode -nographics -quit -projectPath <viewer> \
    //     -executeMethod LabViewer.AR.EditorTools.ARDiagramOrquestacionTest.BatchTestSecuencia
    // Resultado: %TEMP%\AR_DIAGRAM_ORQUESTACION_resultado.json (exit 0/1).
    public static class ARDiagramOrquestacionTest
    {
        const string DiagramJsonRel = "StreamingAssets/lab_data/edificios/II/results/diagramas_FE_tag489_G.json";
        const string Tag = "[ARDiagTest] ";
        static readonly List<GameObject> Raices = new List<GameObject>();

        [MenuItem("LabViewer AR/Probar secuencia de carga del diagrama 489")]
        public static void DesdeMenu()
        {
            Ejecutar(false);
        }

        public static void BatchTestSecuencia()
        {
            Ejecutar(true);
        }

        static void Ejecutar(bool batch)
        {
            var res = new Dictionary<string, object>
            {
                ["tarea"] = "AR_DIAGRAM_ORQUESTACION",
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
                    errores.Add("JSON de diagramas no es objeto: " + abs);
                }
                else
                {
                    var estructural = ARForceDiagram489.Validar(raiz, "II", 489, "EII_CP2_V_029", "G", 3.05f, 51);
                    res["estructura_json_errores"] = estructural.Count;
                    if (estructural.Count == 0)
                    {
                        EjecutarPruebas(raiz, res, errores);
                    }
                    else
                    {
                        errores.Add("JSON estructuralmente invalido (" + estructural.Count + "): " + string.Join("; ", estructural));
                    }
                }
            }
            catch (Exception e)
            {
                errores.Add("excepcion en la prueba: " + e);
            }
            finally
            {
                for (int i = Raices.Count - 1; i >= 0; i--)
                {
                    if (Raices[i] != null) UnityEngine.Object.DestroyImmediate(Raices[i]);
                }
                Raices.Clear();
            }

            res["total_errores"] = errores.Count;
            res["errores"] = errores;
            res["resultado"] = errores.Count == 0 ? "OK" : "ERROR";

            string reporte = Path.Combine(Path.GetTempPath(), "AR_DIAGRAM_ORQUESTACION_resultado.json");
            File.WriteAllText(reporte, JsonEscribir(res));
            Debug.Log(Tag + "Reporte: " + reporte);

            string linea = Tag + "resultado=" + res["resultado"] + " errores=" + errores.Count;
            foreach (var e in errores) linea += "\n" + Tag + "  - " + e;
            if (errores.Count == 0) Debug.Log(Tag + "Secuencia de carga OK");
            else Debug.LogError(linea);

            if (batch)
                EditorApplication.Exit(errores.Count == 0 ? 0 : 1);
        }

        static void EjecutarPruebas(Dictionary<string, object> raiz, Dictionary<string, object> res, List<string> errores)
        {
            // Orden A: JSON primero, loader despues (el orden del fallo real).
            bool a1, a2, a3, a4, a5;
            GameObject rootA = CrearDiagrama(out ARForceDiagram489 dA, out ARBeam489Loader lA, out ARElementIdentity idA,
                out ARImageAnchorController cA);
            try
            {
                dA.AceptarJson(raiz);
                a1 = dA.JsonListo && !dA.Fallido && !dA.DataLoaded && dA.ConteoConstrucciones == 0;
                res["A_json_primero_aceptado_sin_error"] = a1;

                // Loader TODAVIA no listo: notificar no debe marcar error, validar ni construir.
                dA.NotificarLoaderTerminado();
                a2 = !dA.Fallido && !dA.DataLoaded && dA.ConteoConstrucciones == 0
                    && dA.ConteoValidaciones == 0 && dA.ConteoFallos == 0;
                res["A_loader_no_listo_no_error_no_construye"] = a2;

                // Loader pasa a estado correcto: valida cruzado y construye una sola vez.
                PonerLoaderOk(lA, idA);
                dA.NotificarLoaderTerminado();
                a3 = !dA.Fallido && dA.DataLoaded && dA.ConteoConstrucciones == 1
                    && dA.ConteoValidaciones == 1 && dA.JsonListo;
                res["A_validacion_cruzada_ok_y_construye"] = a3;
                res["A_magnitud_actual"] = dA.MagnitudActual;

                // Sin anchor no se hace visible.
                dA.NotificarAnchor();
                a4 = !dA.DiagramaVisible && dA.DataLoaded && dA.ConteoConstrucciones == 1;
                res["A_espera_anchor_para_visible"] = a4;

                // Duplicados: segunda notificacion => 1 sola validacion/construccion, sin fallo.
                dA.NotificarLoaderTerminado();
                dA.NotificarAnchor();
                a5 = dA.ConteoConstrucciones == 1 && dA.ConteoValidaciones == 1
                    && !dA.Fallido && dA.DataLoaded && !dA.DiagramaVisible;
                res["A_sin_duplicados"] = a5;

                bool aGlobal = a1 && a2 && a3 && a4 && a5;
                if (!aGlobal)
                {
                    errores.Add("orden A (JSON primero / loader despues) no paso: JsonListo=" + dA.JsonListo
                        + " Fallido=" + dA.Fallido + " DataLoaded=" + dA.DataLoaded
                        + " Construcciones=" + dA.ConteoConstrucciones + " Visible=" + dA.DiagramaVisible);
                }
            }
            finally
            {
                DestroyDiagram(rootA);
            }

            // Orden B: loader listo ANTES que el JSON.
            bool b1, b2, b3;
            GameObject rootB = CrearDiagrama(out ARForceDiagram489 dB, out ARBeam489Loader lB, out ARElementIdentity idB,
                out ARImageAnchorController cB);
            try
            {
                PonerLoaderOk(lB, idB);
                dB.NotificarLoaderTerminado();
                b1 = !dB.Fallido && !dB.DataLoaded && dB.ConteoConstrucciones == 0 && !dB.JsonListo;
                res["B_loader_antes_json_sin_error"] = b1;

                dB.AceptarJson(raiz);
                b2 = dB.JsonListo && !dB.Fallido && !dB.DataLoaded;
                res["B_json_luego_aceptado"] = b2;

                dB.NotificarLoaderTerminado();
                b3 = !dB.Fallido && dB.DataLoaded && dB.ConteoConstrucciones == 1;
                res["B_construye_una_vez"] = b3;

                if (!(b1 && b2 && b3))
                {
                    errores.Add("orden B (loader primero / JSON despues) no paso: JsonListo=" + dB.JsonListo
                        + " Fallido=" + dB.Fallido + " DataLoaded=" + dB.DataLoaded
                        + " Construcciones=" + dB.ConteoConstrucciones);
                }
            }
            finally
            {
                DestroyDiagram(rootB);
            }

            // Orden C: fallo definitivo del loader; el diagrama falla una sola vez
            // y conserva el fallback (rotulo basico: DataLoaded falso).
            bool c1, c2, c3;
            GameObject rootC = CrearDiagrama(out ARForceDiagram489 dC, out ARBeam489Loader lC, out ARElementIdentity idC,
                out ARImageAnchorController cC);
            try
            {
                dC.AceptarJson(raiz);
                c1 = dC.JsonListo && !dC.Fallido;
                res["C_json_valido"] = c1;

                PonerLoaderFallo(lC);
                dC.NotificarLoaderTerminado();
                c2 = dC.Fallido && dC.ConteoFallos == 1 && !dC.DataLoaded && dC.ConteoConstrucciones == 0;
                res["C_falla_una_vez_y_conserva_fallback"] = c2;
                res["C_loader_error_propagado"] = lC.LoadError;

                dC.NotificarLoaderTerminado();
                c3 = dC.ConteoFallos == 1 && dC.Fallido && !dC.DataLoaded;
                res["C_falla_sin_duplicar_registro"] = c3;

                if (!(c1 && c2 && c3))
                {
                    errores.Add("orden C (fallo del loader) no paso: Fallido=" + dC.Fallido
                        + " ConteoFallos=" + dC.ConteoFallos + " DataLoaded=" + dC.DataLoaded
                        + " Construcciones=" + dC.ConteoConstrucciones);
                }
            }
            finally
            {
                DestroyDiagram(rootC);
            }

            // Orden D: selector inicial Vz (componente nuevo, antes de cualquier carga).
            GameObject rootD = CrearDiagrama(out ARForceDiagram489 dD, out ARBeam489Loader lD, out ARElementIdentity idD,
                out ARImageAnchorController cD);
            try
            {
                bool d = string.Equals(dD.MagnitudActual, "Vz", StringComparison.Ordinal) && dD.MagnitudIndex == 2
                    && !dD.Fallido && !dD.DataLoaded;
                res["D_selector_inicial_vz"] = d;
                if (!d)
                    errores.Add("selector inicial != Vz (actual=" + dD.MagnitudActual + ", indice=" + dD.MagnitudIndex + ")");
            }
            finally
            {
                DestroyDiagram(rootD);
            }

            // Superficie de estado final del loader (LoadCompleted/LoadSucceeded/LoadError).
            GameObject rootE = CrearDiagrama(out ARForceDiagram489 dE, out ARBeam489Loader lE, out ARElementIdentity idE,
                out ARImageAnchorController cE);
            try
            {
                PonerLoaderOk(lE, idE);
                bool eOk = lE.LoadCompleted && lE.LoadSucceeded && string.IsNullOrEmpty(lE.LoadError);
                PonerCampo(lE, "m_LoadCompleted", false);
                PonerCampo(lE, "m_LoadSucceeded", false);
                PonerCampo(lE, "m_LoadError", "fallo simulado para verificar la propiedad");
                bool eFallo = lE.LoadCompleted == false && lE.LoadSucceeded == false
                    && string.Equals(lE.LoadError, "fallo simulado para verificar la propiedad", StringComparison.Ordinal);
                res["E_estado_final_loader_readonly"] = eOk && eFallo;
                if (!(eOk && eFallo))
                    errores.Add("propiedades LoadCompleted/LoadSucceeded/LoadError no reflejan el estado final");
            }
            finally
            {
                DestroyDiagram(rootE);
            }

            // Orden F: el MISMO metodo de entrada que ejecuta Android una vez el
            // JSON esta disponible (CoordinarDesdeJson). El JSON llega primero; la
            // coroutine espera al loader sin validar ni construir; al terminar el
            // loader valida cruzado y construye exactamente una vez; el selector
            // queda activo (DataLoaded) y el fallback no es el rotulo principal.
            bool f1, f2, f3, f4, f5, f6;
            GameObject rootF = CrearDiagrama(out ARForceDiagram489 dF, out ARBeam489Loader lF, out ARElementIdentity idF,
                out ARImageAnchorController cF);
            try
            {
                dF.AceptarJson(raiz);
                f1 = dF.JsonListo && !dF.Fallido && !dF.DataLoaded
                    && dF.ConteoConstrucciones == 0 && dF.ConteoValidaciones == 0;
                res["F_json_primero_aceptado"] = f1;

                var iterador = (System.Collections.IEnumerator)dF.CoordinarDesdeJson();
                try
                {
                    // Primer avance: el loader aun no termino => retener datos, sin
                    // validar, sin construir y sin marcar fallo.
                    bool primer = iterador.MoveNext();
                    f2 = primer && !dF.Fallido && !dF.DataLoaded
                        && dF.ConteoConstrucciones == 0 && dF.ConteoValidaciones == 0 && dF.ConteoFallos == 0;
                    res["F_esperando_loader_sin_validar_ni_construir"] = f2;

                    PonerLoaderOk(lF, idF);

                    // Avanzar hasta validar/construir (acota el giro de la espera
                    // de anchor, que en EditMode no termina).
                    int guardas = 0;
                    while (!dF.DataLoaded && guardas < 200) { iterador.MoveNext(); guardas++; }

                    f3 = dF.DataLoaded && !dF.Fallido
                        && dF.ConteoValidaciones == 1 && dF.ConteoConstrucciones == 1;
                    res["F_valida_y_construye_una_vez"] = f3;
                    res["F_magnitud_actual"] = dF.MagnitudActual;

                    // Pasos adicionales: sin duplicar validacion/construccion ni fallo.
                    for (int i = 0; i < 5; i++) iterador.MoveNext();
                    f4 = dF.ConteoValidaciones == 1 && dF.ConteoConstrucciones == 1
                        && !dF.Fallido && dF.ConteoFallos == 0;
                    res["F_sin_duplicados_ni_fallo"] = f4;

                    // Selector activo (DataLoaded, inicial Vz) y fallback ausente.
                    f5 = string.Equals(dF.MagnitudActual, "Vz", StringComparison.Ordinal)
                        && dF.DataLoaded && !dF.Fallido;
                    res["F_selector_activo_sin_fallback"] = f5;

                    // El texto del error de la ruta antigua no puede aparecer antes
                    // de LoadCompleted: en toda la espera no hubo fallo ni causa breve.
                    f6 = dF.ConteoFallos == 0 && string.IsNullOrEmpty(dF.CausaBreve);
                    res["F_sin_error_antiguo_antes_de_loader"] = f6;

                    if (!(f1 && f2 && f3 && f4 && f5 && f6))
                    {
                        errores.Add("orden F (entrada Android) no paso: JsonListo=" + dF.JsonListo
                            + " Fallido=" + dF.Fallido + " DataLoaded=" + dF.DataLoaded
                            + " Validaciones=" + dF.ConteoValidaciones + " Construcciones=" + dF.ConteoConstrucciones
                            + " Fallos=" + dF.ConteoFallos);
                    }
                }
                finally
                {
                    var disp = iterador as IDisposable;
                    if (disp != null) disp.Dispose();
                }
            }
            finally
            {
                DestroyDiagram(rootF);
            }

            // Resumen agregado.
            res["ordenes_exitosos"] = (bool)res["A_json_primero_aceptado_sin_error"]
                && (bool)res["A_loader_no_listo_no_error_no_construye"]
                && (bool)res["A_validacion_cruzada_ok_y_construye"]
                && (bool)res["A_espera_anchor_para_visible"]
                && (bool)res["A_sin_duplicados"]
                && b3 && (bool)res["B_loader_antes_json_sin_error"]
                && c2 && c3 && (bool)res["D_selector_inicial_vz"]
                && f2 && f3 && f4 && f5 && f6;
        }

        static GameObject CrearDiagrama(out ARForceDiagram489 diagrama, out ARBeam489Loader loader,
            out ARElementIdentity identidad, out ARImageAnchorController controlador)
        {
            var root = new GameObject("AR_Test_Orquestacion");
            Raices.Add(root);

            loader = root.AddComponent<ARBeam489Loader>();
            controlador = root.AddComponent<ARImageAnchorController>();
            diagrama = root.AddComponent<ARForceDiagram489>();

            var idGo = new GameObject("identidad");
            idGo.transform.SetParent(root.transform, false);
            identidad = idGo.AddComponent<ARElementIdentity>();
            identidad.Init(489, "EII_CP2_V_029", "II", "viga", "30x80");

            var so = new SerializedObject(diagrama);
            so.FindProperty("m_Loader").objectReferenceValue = loader;
            so.FindProperty("m_Controller").objectReferenceValue = controlador;
            so.FindProperty("m_ContentRoot").objectReferenceValue = root.transform;
            so.FindProperty("m_Label").objectReferenceValue = null;
            so.ApplyModifiedPropertiesWithoutUndo();

            return root;
        }

        static void PonerLoaderOk(ARBeam489Loader loader, ARElementIdentity identidad)
        {
            // Viga de la prueba con las dimensiones AR reales de la seccion
            // (0.305 x 0.080 x 0.030). El diagrama se engancha a su transform, de
            // modo que la viga debe existir para que se pueda construir.
            var viga = new GameObject("FE_TAG_489_prueba");
            viga.transform.SetParent(loader.transform, false);
            viga.transform.localPosition = Vector3.zero;
            viga.transform.localRotation = Quaternion.identity;
            viga.transform.localScale = new Vector3(0.305f, 0.080f, 0.030f);

            PonerCampo(loader, "m_Beam", viga);
            PonerCampo(loader, "m_Identity", identidad);
            PonerCampo(loader, "m_DataLoaded", true);
            PonerCampo(loader, "m_LoadCompleted", true);
            PonerCampo(loader, "m_LoadSucceeded", true);
            PonerCampo(loader, "m_LoadError", null);
            PonerCampo(loader, "m_VigaLongitudM", 3.05f);
            PonerCampo(loader, "m_VigaLongitudAR", 0.305f);
            PonerCampo(loader, "m_VigaAltoAR", 0.080f);
            PonerCampo(loader, "m_VigaAnchoAR", 0.030f);
            PonerCampo(loader, "m_VigaCentroLocal", Vector3.zero);
            PonerCampo(loader, "m_VigaPILocal", Vector3.zero);
            PonerCampo(loader, "m_VigaPJLocal", new Vector3(0.305f, 0f, 0f));
        }

        static void PonerLoaderFallo(ARBeam489Loader loader)
        {
            PonerCampo(loader, "m_Identity", null);
            PonerCampo(loader, "m_DataLoaded", false);
            PonerCampo(loader, "m_LoadCompleted", true);
            PonerCampo(loader, "m_LoadSucceeded", false);
            PonerCampo(loader, "m_LoadError", "fallo simulado del loader en la prueba");
        }

        static void PonerCampo(object target, string nombre, object valor)
        {
            FieldInfo f = typeof(ARBeam489Loader).GetField(nombre, BindingFlags.NonPublic | BindingFlags.Instance);
            if (f == null)
                throw new InvalidOperationException("campo ARBeam489Loader." + nombre + " no encontrado");
            f.SetValue(target, valor);
        }

        static void DestroyDiagram(GameObject root)
        {
            if (root == null) return;
            UnityEngine.Object.DestroyImmediate(root);
            Raices.Remove(root);
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