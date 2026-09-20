using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace LabViewer.EditorTools
{
    /// <summary>
    /// Build movil inicial REAL y reproducible (Android APK inicial del LabViewer),
    /// usando el SDK Android BUNDLED del AndroidPlayer de este editor (Editor/Data/
    /// PlaybackEngines/AndroidPlayer -> SDK+adb+JDK bunded; NO requiere
    /// ANDROID_HOME/ANDROID_SDK_ROOT, que estan vacios pero no se necesitan).
    ///
    /// Batchmode (reproducible, registra resultado REAL en evidence/):
    ///   "C:\Program Files\Unity\Hub\Editor\6000.5.10f1\Editor\Unity.exe" ^
    ///     -batchmode -nographics -quit -projectPath <viewer_unity> ^
    ///     -buildTarget Android -executeMethod LabViewer.EditorTools.LabAndroidBuild.BuildInicialAPK ^
    ///     -logFile <s05>\evidence\unity_android_build.log
    ///
    /// Registra <s05>\evidence\android_build_inicial_resultado.json con ruta APK +
    /// resultado REAL (o el error concreto de BuildReport / excepcion).
    /// </summary>
    public static class LabAndroidBuild
    {
        const string ScenePath = "Assets/Scenes/Main.unity";

        [MenuItem("LabViewer/Build Android inicial (APK)")]
        public static void BuildInicialAPK()
        {
            // --- 1) Ruta APK dentro del worktree: <s05>\artifacts\android ---
            string proj = Directory.GetCurrentDirectory();
            string s05 = Directory.GetParent(proj) != null
                ? Path.GetFullPath(Path.Combine(proj, ".."))
                : proj;
            string outDir = Path.Combine(s05, "artifacts", "android");
            Directory.CreateDirectory(outDir);
            string apkPath = Path.Combine(outDir, "lab-viewer-inicial.apk");

            var res = new Dictionary<string, object>
            {
                ["tarea"] = "C_ANDROID_BUILD_INICIAL",
                ["fecha"] = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
                ["editor"] = Application.unityVersion,
                ["apk_path"] = apkPath,
                ["sdk"] = "BUNDLED (Editor/Data/PlaybackEngines/AndroidPlayer con SDK+adb+JDK) - NO usa ANDROID_HOME (vacio) ni ANDROID_SDK_ROOT; SDK Android PRESENTE",
                ["escena"] = ScenePath
            };

            try
            {
                // --- 2) Switch a Android + backend + arquitetura (reproducible) ---
                if (!EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android, BuildTarget.Android))
                {
                    throw new InvalidOperationException("No se pudo cambiar a Android (SwitchActiveBuildTarget=False).");
                }
                PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64;

                // --- 3) Build REAL ---
                BuildPlayerOptions opts = new BuildPlayerOptions
                {
                    scenes = new[] { ScenePath },
                    locationPathName = apkPath,
                    target = BuildTarget.Android,
                    options = BuildOptions.None
                };

                BuildReport br = BuildPipeline.BuildPlayer(opts);
                res["rc"] = br.summary.result == BuildResult.Succeeded ? 0 : 1;
                res["result"] = br.summary.result.ToString();
                res["output_path"] = br.summary.outputPath;
                res["total_size_bytes"] = br.summary.totalSize;
                res["total_errors"] = br.summary.totalErrors;
                res["total_warnings"] = br.summary.totalWarnings;
                res["duracion_seg"] = br.summary.totalTime.TotalSeconds;

                if (br.summary.result != BuildResult.Succeeded)
                {
                    var msgs = new List<string>();
                    foreach (var s in br.steps)
                        foreach (var m in s.messages)
                            if (m.type == LogType.Error || m.type == LogType.Exception)
                                msgs.Add(m.content);
                    res["error_concreto"] = msgs;
                    res["apk_generado"] = File.Exists(apkPath);
                }
                else
                {
                    res["apk_generado"] = File.Exists(apkPath);
                    res["apk_size_bytes"] = File.Exists(apkPath) ? new FileInfo(apkPath).Length : 0L;
                }

                Registrar(res);
                EditorApplication.Exit(res["rc"] is int i ? i : 1);
            }
            catch (Exception ex)
            {
                res["rc"] = 2;
                res["result"] = "EXCEPCION";
                res["error_concreto"] = ex.ToString();
                res["apk_generado"] = File.Exists(apkPath);
                Registrar(res);
                EditorApplication.Exit(2);
            }
        }

        static void Registrar(Dictionary<string, object> resultado)
        {
            string proj = Directory.GetCurrentDirectory();
            string s05 = Directory.GetParent(proj) != null
                ? Path.GetFullPath(Path.Combine(proj, ".."))
                : proj;
            string dir = Path.Combine(s05, "evidence");
            Directory.CreateDirectory(dir);
            string file = Path.Combine(dir, "android_build_inicial_resultado.json");
            File.WriteAllText(file, JsonEscribir(resultado));
            Debug.Log("[LabAndroidBuild] Resultado registrado en " + file);
        }

        /// <summary>Serializador JSON minimo autosuficiente (sin Newtonsoft: la asamblea
        /// Editor de este proyecto NO referencia el paquete com.unity.nuget.newtonsoft-json,
        /// por lo que Newtonsoft.Json no existe aqui -> CS0103 real. Escape manual puro).</summary>
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
            if (v is int i) return i.ToString(System.Globalization.CultureInfo.InvariantCulture);
            if (v is long l) return l.ToString(System.Globalization.CultureInfo.InvariantCulture);
            if (v is float f) return f.ToString(System.Globalization.CultureInfo.InvariantCulture);
            if (v is double d) return d.ToString(System.Globalization.CultureInfo.InvariantCulture);
            if (v is DateTime dt) return "\"" + dt.ToString("yyyy-MM-ddTHH:mm:ss", System.Globalization.CultureInfo.InvariantCulture) + "\"";
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
