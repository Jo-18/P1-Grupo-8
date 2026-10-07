using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
public static class ApkFix02Setup {
    public static void Prepare(){ApkFixSetup.Prepare();HonorsSetup.Prepare();}
    public static void Diagnose(){
        EditorSceneManager.OpenScene(HonorsSetup.ARScene);
        var model=Object.FindAnyObjectByType<ARStructure>();
        var driver=Object.FindAnyObjectByType<HonorsAnchorDriver>();
        var profile=JsonUtility.FromJson<ARMarkerProfileRegistry.Bundle>(Resources.Load<TextAsset>("Honors/marker_profiles").text).profiles[0];
        typeof(HonorsAnchorDriver).GetProperty("ActiveProfile").SetValue(driver,profile);
        typeof(ARStructure).GetMethod("LoadModel",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(model,null);
        typeof(ARImageAnchor).GetMethod("Awake",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(driver.GetComponent<ARImageAnchor>(),null);
        var before=model.mode;var root=new GameObject("Diagnostic synthetic anchor");
        typeof(ARStructure).GetMethod("OnAnchored",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(model,new object[]{root.transform});
        File.WriteAllText(Path.Combine(HonorsPaths.Evidence,"fix02","diagnosis_before.json"),"{\"before\":\""+before+"\",\"after\":\""+model.mode+"\",\"scale\":"+model.Scale.ToString(System.Globalization.CultureInfo.InvariantCulture)+",\"elements\":"+model.Elements.Count+",\"physicalTracking\":false}");
        // Do not save the diagnostic scene or profile.
    }
}
