using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;

namespace LabViewer.AR.BuildTools
{
    /// <summary>
    /// Build Android AR: genera un APK que contiene EXCLUSIVAMENTE
    /// Assets/Scenes/ARMain.unity, sin modificar permanentemente el orden de
    /// escenas de EditorBuildSettings ni dejar PlayerSettings modificados.
    ///
    /// La ruta del APK se toma de la variable de entorno LAB_AR_APK_PATH;
    /// si no existe se usa una ruta bajo Path.GetTempPath().
    ///
    /// minSdk temporal adaptado a la validacion de ARCore: si la primera
    /// Graphics API es Vulkan y ARCore es Required exige AndroidApiLevel29;
    /// para Optional (o Required con OpenGLES3 primero) basta AndroidApiLevel26.
    ///
    /// Batch (reproducible, resultado real fuera del repositorio):
    ///   "C:\Program Files\Unity\Hub\Editor\6000.5.10f1\Editor\Unity.exe" ^
    ///     -batchmode -nographics -quit -projectPath <viewer_unity> ^
    ///     -buildTarget Android -executeMethod LabViewer.AR.BuildTools.ARAndroidBuild.BuildAR ^
    ///     -logFile <externo>\unity_android_ar_build.log
    /// </summary>
    public static class ARAndroidBuild
    {
        const string ScenePath = "Assets/Scenes/ARMain.unity";
        const string EnvApkPath = "LAB_AR_APK_PATH";
        const string PackageId = "com.grupo8.labviewer.artag489";
        const string Tag = "[ARBuild] ";

        [MenuItem("LabViewer AR/Build APK Android (solo ARMain)")]
        public static void BuildAR()
        {
            string apkPath = Path.GetFullPath(ResolverRutaApk());
            Debug.Log(Tag + "Inicio: escena=" + ScenePath + " apk=" + apkPath);
            int rc = Ejecutar(apkPath);
            Debug.Log(Tag + "BuildAR finalizado rc=" + rc);
            if (Application.isBatchMode)
                EditorApplication.Exit(rc);
        }

        static string ResolverRutaApk()
        {
            string env = Environment.GetEnvironmentVariable(EnvApkPath);
            if (!string.IsNullOrWhiteSpace(env))
                return env;
            return Path.Combine(Path.GetTempPath(), "semana06_ar_build", "lab-viewer-AR-tag489.apk");
        }

        static int Ejecutar(string apkPath)
        {
            var res = new Dictionary<string, object>
            {
                ["tarea"] = "AR_ANDROID_BUILD",
                ["fecha"] = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
                ["editor"] = Application.unityVersion,
                ["escena"] = ScenePath,
                ["apk_path"] = apkPath,
                ["package"] = PackageId
            };

            BuildTarget targetPrevio = EditorUserBuildSettings.activeBuildTarget;
            BuildTargetGroup grupoPrevio = BuildPipeline.GetBuildTargetGroup(targetPrevio);
            string appIdPrevio = PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android);
            AndroidSdkVersions minSdkPrevio = PlayerSettings.Android.minSdkVersion;
            ScriptingImplementation backendPrevio = PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android);
            AndroidArchitecture archPrevio = PlayerSettings.Android.targetArchitectures;
            bool gfxDefaultPrevio = PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.Android);
            GraphicsDeviceType[] gfxPrevia = PlayerSettings.GetGraphicsAPIs(BuildTarget.Android);

            try
            {
                if (!EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android, BuildTarget.Android))
                    throw new InvalidOperationException("No se pudo cambiar a Android (SwitchActiveBuildTarget=False).");

                PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, PackageId);
                AndroidSdkVersions minSdkTemporal = MinSdkArcoreRequerido();
                PlayerSettings.Android.minSdkVersion = minSdkTemporal;
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARMv7 | AndroidArchitecture.ARM64;
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[]
                {
                    GraphicsDeviceType.Vulkan,
                    GraphicsDeviceType.OpenGLES3
                });

                string dir = Path.GetDirectoryName(apkPath);
                if (!string.IsNullOrEmpty(dir))
                    Directory.CreateDirectory(dir);

                var opts = new BuildPlayerOptions
                {
                    scenes = new[] { ScenePath },
                    locationPathName = apkPath,
                    target = BuildTarget.Android,
                    options = BuildOptions.None
                };

                BuildReport br = BuildPipeline.BuildPlayer(opts);
                BuildSummary s = br.summary;

                bool ok = s.result == BuildResult.Succeeded
                          && s.totalErrors == 0
                          && File.Exists(apkPath)
                          && new FileInfo(apkPath).Length > 0;

                res["result"] = s.result.ToString();
                res["total_errors"] = s.totalErrors;
                res["total_warnings"] = s.totalWarnings;
                res["duracion_seg"] = s.totalTime.TotalSeconds;
                res["min_sdk_usado"] = (int)minSdkTemporal;
                res["apk_generado"] = File.Exists(apkPath);
                res["apk_size_bytes"] = File.Exists(apkPath) ? new FileInfo(apkPath).Length : 0L;

                if (!ok)
                    res["errores"] = MensajesDe(br, LogType.Error, LogType.Exception);

                res["apk_path"] = s.outputPath;

                Debug.Log(Tag + "Resumen: escena=" + ScenePath
                    + "; apk=" + apkPath
                    + "; tamano=" + res["apk_size_bytes"] + " bytes"
                    + "; resultado=" + s.result
                    + "; warnings=" + s.totalWarnings
                    + "; errores=" + s.totalErrors
                    + "; duracion=" + s.totalTime.TotalSeconds + "s");

                Registrar(res, apkPath);
                return ok ? 0 : 1;
            }
            catch (Exception ex)
            {
                res["result"] = "EXCEPCION";
                res["error_concreto"] = ex.ToString();
                Registrar(res, apkPath);
                return 2;
            }
            finally
            {
                try { PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, appIdPrevio); }
                catch (Exception e) { Debug.LogWarning(Tag + "no se pudo restaurar applicationIdentifier: " + e.Message); }
                try { PlayerSettings.Android.minSdkVersion = minSdkPrevio; }
                catch (Exception e) { Debug.LogWarning(Tag + "no se pudo restaurar minSdk: " + e.Message); }
                try { PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, backendPrevio); }
                catch (Exception e) { Debug.LogWarning(Tag + "no se pudo restaurar scriptingBackend: " + e.Message); }
                try { PlayerSettings.Android.targetArchitectures = archPrevio; }
                catch (Exception e) { Debug.LogWarning(Tag + "no se pudo restaurar targetArchitectures: " + e.Message); }
                try
                {
                    PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, gfxDefaultPrevio);
                    if (!gfxDefaultPrevio)
                        PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, gfxPrevia);
                }
                catch (Exception e) { Debug.LogWarning(Tag + "no se pudo restaurar Graphics APIs: " + e.Message); }
                try
                {
                    if (EditorUserBuildSettings.activeBuildTarget != targetPrevio)
                        EditorUserBuildSettings.SwitchActiveBuildTarget(grupoPrevio, targetPrevio);
                }
                catch (Exception e) { Debug.LogWarning(Tag + "no se pudo restaurar build target: " + e.Message); }
                AssetDatabase.SaveAssets();
            }
        }

        static AndroidSdkVersions MinSdkArcoreRequerido()
        {
            string path = Path.Combine("Assets", "XR", "Settings", "ARCoreSettings.asset");
            const string clave = "m_Requirement:";
            if (File.Exists(path))
            {
                foreach (string linea in File.ReadAllLines(path))
                {
                    string t = linea.Trim();
                    if (t.StartsWith(clave, StringComparison.Ordinal))
                    {
                        int req;
                        if (int.TryParse(t.Substring(clave.Length).Trim(), out req))
                            return req == 0 ? AndroidSdkVersions.AndroidApiLevel29 : AndroidSdkVersions.AndroidApiLevel26;
                    }
                }
            }
            return AndroidSdkVersions.AndroidApiLevel29;
        }

        static List<string> MensajesDe(BuildReport br, params LogType[] tipos)
        {
            var msgs = new List<string>();
            foreach (var s in br.steps)
                foreach (var m in s.messages)
                    foreach (var t in tipos)
                        if (m.type == t)
                            msgs.Add(m.content);
            return msgs;
        }

        static void Registrar(Dictionary<string, object> resultado, string apkPath)
        {
            string dir = Path.GetDirectoryName(apkPath);
            if (string.IsNullOrEmpty(dir))
                dir = Path.GetTempPath();
            Directory.CreateDirectory(dir);
            string file = Path.Combine(dir, "AR_ANDROID_BUILD_resultado.json");
            File.WriteAllText(file, JsonEscribir(resultado));
            Debug.Log(Tag + "Resultado registrado en " + file);
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