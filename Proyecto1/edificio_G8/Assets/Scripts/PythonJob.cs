using System.IO;
using UnityEngine;

/// <summary>
/// Ejecuta un script de Proyecto1/scripts en segundo plano (python o py) y
/// avisa cuando termina. Solo disponible en el editor o en PC.
/// La salida se lee en forma asincrona (un script que imprime mucho no se
/// bloquea con el bufer lleno) y la ultima linea queda en <see cref="LastLine"/>.
/// </summary>
public class PythonJob
{
    public string OutputPath { get; private set; }
    public string Error { get; private set; }
    public bool Running => process != null;
    /// Ultima linea impresa por el script (progreso).
    public string LastLine => lastLine;
    public float Elapsed => process != null ? Time.unscaledTime - startTime : lastElapsed;

    /// true en el editor y en PC (hay Python/OpenSees); false en celular.
    public static bool Available
    {
        get
        {
#if UNITY_EDITOR || UNITY_STANDALONE
            return ScriptsDir != null;
#else
            return false;
#endif
        }
    }

#if UNITY_EDITOR || UNITY_STANDALONE
    private System.Diagnostics.Process process;
#else
    private object process;
#endif
    private float startTime;
    private float lastElapsed;
    private volatile string lastLine = "";
    private readonly System.Text.StringBuilder errors = new System.Text.StringBuilder();

    private static string scriptsDir;
    private static bool scriptsSearched;

    // Interprete con openseespy (se busca una vez): MCOC_PYTHON, "py -3.12", "python" o "py".
    private static string interprete;
    private static string prefijo = "";
    private static bool interpreteBuscado;

    /// Que Python se usa para el analisis, o por que no se encontro uno con openseespy.
    public static string Diagnostico { get; private set; } = "";

    /// Si ningun Python tiene openseespy, calcular con el solver de verificacion del proyecto
    /// (replica numpy/scipy de las funciones de OpenSees que usa el analisis). Se guarda entre sesiones.
    public static bool UsarReplica
    {
        get => PlayerPrefs.GetInt("mcoc_usar_replica", 0) == 1;
        set { PlayerPrefs.SetInt("mcoc_usar_replica", value ? 1 : 0); PlayerPrefs.Save(); ReiniciarBusqueda(); }
    }

    /// true si el Python elegido no tiene openseespy y se calcula con el solver de verificacion.
    public static bool ConReplica { get; private set; }

    public static void ReiniciarBusqueda()
    {
        interpreteBuscado = false;
        interprete = null;
        prefijo = "";
        ConReplica = false;
        Diagnostico = "";
    }

    /// Vuelve a buscar el Python y devuelve el diagnostico (para el boton de la pestana ANALISIS).
    public static string RevisarPython()
    {
        ReiniciarBusqueda();
        BuscarInterprete();
        return string.IsNullOrEmpty(Diagnostico) ? "Python no disponible en esta plataforma." : Diagnostico;
    }

    private static void BuscarInterprete()
    {
#if UNITY_EDITOR || UNITY_STANDALONE
        if (interpreteBuscado) return;
        interpreteBuscado = true;
        var candidatos = new System.Collections.Generic.List<(string exe, string pre)>();
        string env = System.Environment.GetEnvironmentVariable("MCOC_PYTHON");
        if (!string.IsNullOrEmpty(env)) candidatos.Add((env, ""));
        candidatos.Add(("py", "-3.12 "));
        candidatos.Add(("python", ""));
        candidatos.Add(("py", ""));
        foreach (var (exe, pre) in candidatos)
        {
            if (Probar(exe, pre + "-c \"import openseespy.opensees\""))
            {
                interprete = exe;
                prefijo = pre;
                Diagnostico = "Motor de cálculo: OpenSees, con " + (exe + " " + pre).Trim() + ".";
                return;
            }
        }
        if (UsarReplica)
        {
            foreach (var (exe, pre) in candidatos)
            {
                if (Probar(exe, pre + "-c \"import numpy, scipy\""))
                {
                    interprete = exe;
                    prefijo = pre;
                    ConReplica = true;
                    Diagnostico = "OpenSees no está instalado: se calculará con el solver de verificación usando " + (exe + " " + pre).Trim() + ". Para usar OpenSees ejecuta instalar_dependencias.bat.";
                    return;
                }
            }
        }
        Diagnostico = "Ningún Python del PATH tiene openseespy: ejecuta instalar_dependencias.bat (instala openseespy en Python 3.12), " +
                      "o activa «calcular con el solver de verificación», o indica la ruta de python.exe en la variable MCOC_PYTHON.";
#endif
    }

#if UNITY_EDITOR || UNITY_STANDALONE
    private static bool Probar(string exe, string args)
    {
        try
        {
            var info = new System.Diagnostics.ProcessStartInfo
            {
                FileName = exe,
                Arguments = args,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            using (var p = System.Diagnostics.Process.Start(info))
            {
                if (p == null) return false;
                p.StandardOutput.ReadToEndAsync();
                p.StandardError.ReadToEndAsync();
                if (!p.WaitForExit(20000))
                {
                    try { p.Kill(); } catch (System.Exception) { }
                    return false;
                }
                return p.ExitCode == 0;
            }
        }
        catch (System.Exception)
        {
            return false;
        }
    }
#endif

    /// Carpeta Proyecto1/scripts: se busca hacia arriba desde los datos de la app
    /// (editor: edificio_G8/Assets; build de Windows: Builds/Windows/..._Data).
    public static string ScriptsDir
    {
        get
        {
            if (scriptsSearched) return scriptsDir;
            scriptsSearched = true;
            var dir = new DirectoryInfo(Application.dataPath);
            for (int i = 0; i < 7 && dir != null; i++, dir = dir.Parent)
            {
                string candidate = Path.Combine(dir.FullName, "scripts");
                if (File.Exists(Path.Combine(candidate, "carga_viva_sismo.py"))) { scriptsDir = candidate; break; }
            }
            return scriptsDir;
        }
    }

    /// Carpeta Proyecto1 (padre de scripts), o null.
    public static string ProjectRoot => ScriptsDir != null ? Path.GetDirectoryName(ScriptsDir) : null;

    public static string ScriptPath(string scriptName)
    {
        return ScriptsDir != null ? Path.Combine(ScriptsDir, scriptName) : scriptName;
    }

    /// Lanza "python -X utf8 script args --out <salida>". Devuelve false si no se pudo.
    public bool Start(string scriptName, string args, string outName)
    {
        Error = null;
        lastLine = "";
        errors.Length = 0;
#if UNITY_EDITOR || UNITY_STANDALONE
        string script = ScriptPath(scriptName);
        if (!File.Exists(script))
        {
            Error = "No encontre scripts/" + scriptName;
            return false;
        }
        OutputPath = Path.Combine(Application.temporaryCachePath, outName);
        if (File.Exists(OutputPath)) File.Delete(OutputPath);
        BuscarInterprete();
        var candidatos = interprete != null
            ? new[] { (interprete, prefijo) }
            : new[] { ("python", ""), ("py", "") };
        foreach (var (exe, pre) in candidatos)
        {
            try
            {
                var info = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = exe,
                    Arguments = $"{pre}-X utf8 \"{script}\" {args} --out \"{OutputPath}\"",
                    WorkingDirectory = Path.GetDirectoryName(script),
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };
                info.EnvironmentVariables["MCOC_REPLICA"] = UsarReplica ? "1" : "0";
                var p = new System.Diagnostics.Process { StartInfo = info };
                p.OutputDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) lastLine = e.Data.Trim(); };
                p.ErrorDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) lock (errors) errors.AppendLine(e.Data); };
                p.Start();
                p.BeginOutputReadLine();
                p.BeginErrorReadLine();
                process = p;
                startTime = Time.unscaledTime;
                return true;
            }
            catch (System.Exception)
            {
                process = null;
            }
        }
        Error = "No se pudo ejecutar Python (python/py en el PATH).";
        return false;
#else
        Error = "Requiere Python: solo disponible en el editor o en PC.";
        return false;
#endif
    }

    /// Llamar en Update. Devuelve true una vez, cuando el proceso termino.
    public bool Poll(float timeoutSeconds = 120f)
    {
#if UNITY_EDITOR || UNITY_STANDALONE
        if (process == null) return false;
        if (!process.HasExited)
        {
            if (Time.unscaledTime - startTime > timeoutSeconds)
            {
                try { process.Kill(); } catch (System.Exception) { }
                process = null;
                Error = "Tiempo de calculo excedido.";
                return true;
            }
            return false;
        }
        process.WaitForExit();   // vacia las lecturas asincronas pendientes
        lastElapsed = Time.unscaledTime - startTime;
        int exitCode = process.ExitCode;
        process = null;
        if (exitCode != 0 || !File.Exists(OutputPath))
        {
            string err;
            lock (errors) err = errors.ToString().Trim();
            string[] lines = err.Split('\n');
            // el exportador valida las entradas y sale con codigo 2: "ERROR de validacion: ..."
            string validation = System.Array.Find(lines, l => l.StartsWith("ERROR"));
            if (validation != null) Error = validation.Trim();
            else Error = $"Error en Python (codigo {exitCode}): " + (err.Length == 0 ? (lastLine.Length > 0 ? lastLine : "sin salida") : lines[lines.Length - 1].Trim());
            if (Error.Contains("openseespy") && !string.IsNullOrEmpty(Diagnostico)) Error += "\n" + Diagnostico;
            if (File.Exists(OutputPath)) File.Delete(OutputPath);   // nunca cargar un resultado de una corrida fallida
        }
        return true;
#else
        return false;
#endif
    }

    public void Kill()
    {
#if UNITY_EDITOR || UNITY_STANDALONE
        if (process != null && !process.HasExited)
        {
            try { process.Kill(); } catch (System.Exception) { }
        }
        process = null;
#endif
    }
}
