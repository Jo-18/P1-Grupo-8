using UnityEditor;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
public static class ApkFixSetup {
    public static void Prepare(){
        const string path="Assets/AR/ARPlaneVisual.prefab";
        var go=PrefabUtility.LoadPrefabContents(path);
        try {
            if(go.GetComponent<ARPlaneDebugVisibility>()==null)go.AddComponent<ARPlaneDebugVisibility>();
            go.GetComponent<MeshRenderer>().enabled=false;
            go.GetComponent<ARPlaneMeshVisualizer>().enabled=true;
            PrefabUtility.SaveAsPrefabAsset(go,path);
        } finally {PrefabUtility.UnloadPrefabContents(go);}
        AssetDatabase.SaveAssets();
    }
}
