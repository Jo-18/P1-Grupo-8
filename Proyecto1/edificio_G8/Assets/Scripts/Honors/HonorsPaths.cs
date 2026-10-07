using System;
using System.IO;
using UnityEngine;
public static class HonorsPaths {
    public static string Repository => Directory.GetParent(Application.dataPath).Parent.Parent.FullName;
    public static string Evidence {
        get {
#if UNITY_EDITOR || UNITY_STANDALONE
            var root=Repository;
            if(!File.Exists(Path.Combine(root,"entrega/honors/proteccion/freeze_originales.json"))) throw new InvalidOperationException("Honors requiere un derivado congelado; se prohibe escribir en 03/04");
            var allowed=Path.GetFullPath(Path.Combine(root,"entrega/honors"));
            var requested=Environment.GetEnvironmentVariable("MCOC_HONORS_EVIDENCE");
            if(!string.IsNullOrEmpty(requested)){
                var resolved=Path.GetFullPath(requested);
                if(!resolved.StartsWith(allowed+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Evidence outside Honors derivative");
                return resolved;
            }
            return allowed;
#else
            return Path.Combine(Application.persistentDataPath,"honors");
#endif
        }
    }
    public static void RejectSavingBaseline() => throw new InvalidOperationException("Honors no guarda como vigente. Descartar/restaurar; base 03/04 protegida.");
}
