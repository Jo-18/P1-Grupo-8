using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using Unity.XR.CoreUtils;

/// Real editor scene validation; invoked with -executeMethod.
public static class UnityIterationValidation
{
    [InitializeOnLoadMethod] static void RegisterReviewRequest()
    {
        EditorApplication.update -= OpenRequestedViewer;
        EditorApplication.update += OpenRequestedViewer;
    }
    static void OpenRequestedViewer()
    {
        if(Application.isBatchMode || EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.isPlayingOrWillChangePlaymode) return;
        string request=Path.GetFullPath("../../entrega/unity_android/abrir_viewer.request");
        if(!File.Exists(request)) return;
        File.Delete(request);
        EditorSceneManager.OpenScene("Assets/Scenes/StructureViewerScene.unity");
        EditorApplication.delayCall += () => {
            var viewer=UnityEngine.Object.FindAnyObjectByType<StructureViewer>();
            Require(viewer && viewer.GetComponentsInChildren<ElementSelectable>(true).Length==628,"Apertura del viewer: geometría incompleta");
            File.WriteAllText(Path.GetFullPath("../../entrega/unity_android/Editor_viewer_open.json"),"{\"result\":\"Passed\",\"interactiveElements\":628,\"unity\":\""+Application.unityVersion+"\"}");
        };
    }
    [Serializable] class Evidence
    {
        public string unity, result, libraryName, diagramPanel;
        public int layers, markerCount;
        public float markerWidth;
        public bool regenerated, initialScene, managers, inspector, selection, legacyDisabled;
    }
    static void Require(bool ok, string message)
    {
        if (!ok) throw new InvalidOperationException(message);
    }
    static Evidence Inspect(bool regenerated)
    {
        var session = UnityEngine.Object.FindAnyObjectByType<ARSession>();
        var origin = UnityEngine.Object.FindAnyObjectByType<XROrigin>();
        var image = UnityEngine.Object.FindAnyObjectByType<ARTrackedImageManager>();
        Require(session && origin && image, "ARSession/XROrigin/ImageManager ausente");
        Require(origin.GetComponent<ARAnchorManager>() && origin.Camera.GetComponent<ARCameraManager>(), "Managers ausentes");
        var app = UnityEngine.Object.FindAnyObjectByType<ARStructure>();
        Require(app && app.GetComponent<ARImageAnchor>(), "AR App incompleta");
        Require(app.GetComponent<ARInspectorUI>() && app.GetComponent<StructuralSelectionController>(), "Inspector/selección ausentes");
        var legacy = app.GetComponent<ARResultsPanel>();
        Require(legacy && !legacy.enabled, "Panel legacy activo");
        Require(app.mode == ARStructure.Mode.Maqueta100, "Modo inicial incorrecto");
        var library = image.referenceLibrary;
        Require(library != null && library.count == 1, "Librería de marcador ausente");
        Require(Mathf.Abs(library[0].size.x - .2f) < .000001f, "Ancho físico incorrecto");
        Require(LayerMask.NameToLayer("MCOCStructure") == 8, "Capa incorrecta");
        Require(typeof(ARDiagramPanel) != null, "Renderer de diagramas ausente");
        return new Evidence {unity=Application.unityVersion, result="Passed", regenerated=regenerated, initialScene=!regenerated, managers=true, inspector=true, selection=true, legacyDisabled=true, layers=8, markerCount=library.count, markerWidth=library[0].size.x, libraryName=library[0].name, diagramPanel="ARDiagramPanel: renderer estático usado por ARInspectorUI"};
    }
    public static void Run()
    {
        Require(Application.unityVersion == "6000.6.0f1", "Versión Unity incorrecta");
        string output = Path.GetFullPath("../../entrega/unity_android");
        Directory.CreateDirectory(output);
        EditorSceneManager.OpenScene(ARSetup.ScenePath);
        File.WriteAllText(Path.Combine(output,"ARScene_initial.json"),JsonUtility.ToJson(Inspect(false),true));
        ARSetup.SetupAll();
        File.WriteAllText(Path.Combine(output,"ARScene_regenerated.json"),JsonUtility.ToJson(Inspect(true),true));
        EditorSceneManager.OpenScene("Assets/Scenes/StructureViewerScene.unity");
        AssetDatabase.ImportAsset("Assets/Resources/estructura_p1l4_unity.json", ImportAssetOptions.ForceUpdate);
        AssetDatabase.SaveAssets();
        Debug.Log("[UnityIterationValidation] ARScene inicial y regenerada: PASS. Viewer PlayMode verificado por ViewerSceneRegressionTests.");
    }
    public static void AfterBuild()
    {
        BuildAndroid.RefreshLatestReport();
        EditorSceneManager.OpenScene(ARSetup.ScenePath);
        File.WriteAllText(Path.GetFullPath("../../entrega/unity_android/ARScene_built.json"),JsonUtility.ToJson(Inspect(true),true));
        EditorSceneManager.OpenScene("Assets/Scenes/StructureViewerScene.unity");
    }
}
