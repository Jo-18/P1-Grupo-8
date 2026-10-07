using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.XR.ARSubsystems;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
public static class HonorsSetup {
    public const string ARScene="Assets/Scenes/ARHonorsScene.unity",ViewerScene="Assets/Scenes/HonorsViewerScene.unity";
    const string LibraryPath="Assets/AR/HonorsMarkerLibrary.asset";
    [MenuItem("MCOC/Honors/Preparar escenas independientes")]
    public static void Prepare(){
        if(Application.unityVersion!="6000.6.0f1")throw new InvalidOperationException("Unity exacto requerido");
        HonorsPaths.Evidence.ToString();
        var library=AssetDatabase.LoadAssetAtPath<XRReferenceImageLibrary>(LibraryPath);
        if(library==null){library=ScriptableObject.CreateInstance<XRReferenceImageLibrary>();AssetDatabase.CreateAsset(library,LibraryPath);foreach(var id in new[]{ARImageAnchor.MarkerName,"Marcador_Honors_Plano"}){
            var path="Assets/AR/"+id+".png";var importer=(TextureImporter)AssetImporter.GetAtPath(path);importer.isReadable=true;importer.textureCompression=TextureImporterCompression.Uncompressed;importer.mipmapEnabled=false;importer.npotScale=TextureImporterNPOTScale.None;importer.SaveAndReimport();
            library.Add();var i=library.count-1;library.SetTexture(i,AssetDatabase.LoadAssetAtPath<Texture2D>(path),false);library.SetName(i,id);library.SetSpecifySize(i,true);library.SetSize(i,new Vector2(.2f,.2f));
        }EditorUtility.SetDirty(library);AssetDatabase.SaveAssets();}
        var profilePath="Assets/Resources/Honors/marker_profiles.json";var bundle=JsonUtility.FromJson<ARMarkerProfileRegistry.Bundle>(File.ReadAllText(profilePath));foreach(var p in bundle.profiles)foreach(var image in library)if(image.name==p.markerId)p.imageGuid=image.guid.ToString();File.WriteAllText(profilePath,JsonUtility.ToJson(bundle,true));AssetDatabase.ImportAsset(profilePath);
        CopyScene(ARSetup.ScenePath,ARScene);var ar=UnityEngine.Object.FindAnyObjectByType<ARImageAnchor>();var config=ar.gameObject.GetComponent<HonorsConfiguration>()??ar.gameObject.AddComponent<HonorsConfiguration>();config.H5CapacityComparison=config.H2ProfilesAndQA=true;config.H3SpatialDiagrams=false;
        if(ar.GetComponent<HonorsAnchorDriver>()==null)ar.gameObject.AddComponent<HonorsAnchorDriver>();if(ar.GetComponent<HonorsCapacityComparisonPanel>()==null)ar.gameObject.AddComponent<HonorsCapacityComparisonPanel>();
        var structure=ar.GetComponent<ARStructure>();structure.mode=ARStructure.Mode.Maqueta100;structure.ShowBeams=structure.ShowColumns=structure.ShowWalls=structure.ShowBraces=true;structure.ShowIds=false;
        if(ar.GetComponent<ARStructuralDiagramOverlay>()==null)ar.gameObject.AddComponent<ARStructuralDiagramOverlay>();
        var manager=UnityEngine.Object.FindAnyObjectByType<ARTrackedImageManager>();manager.referenceLibrary=library;manager.requestedMaxNumberOfMovingImages=1;EditorSceneManager.SaveScene(ar.gameObject.scene);
        CopyScene("Assets/Scenes/StructureViewerScene.unity",ViewerScene);var viewer=UnityEngine.Object.FindAnyObjectByType<StructureViewer>();config=viewer.gameObject.GetComponent<HonorsConfiguration>()??viewer.gameObject.AddComponent<HonorsConfiguration>();config.H5CapacityComparison=true;config.H2ProfilesAndQA=config.H3SpatialDiagrams=false;EditorSceneManager.SaveScene(viewer.gameObject.scene);
        File.WriteAllText(Path.Combine(HonorsPaths.Evidence,"setup_honors.json"),"{\"unity\":\""+Application.unityVersion+"\",\"libraryCount\":"+library.count+",\"activeAnchors\":1,\"maxMovingImagesRequested\":1,\"physicalTestExecuted\":false,\"horizontalEnabled\":false}");
        AssetDatabase.SaveAssets();
    }
    static void CopyScene(string source,string dest){if(!File.Exists(dest)){var s=EditorSceneManager.OpenScene(source);EditorSceneManager.SaveScene(s,dest,true);}EditorSceneManager.OpenScene(dest);}
}
