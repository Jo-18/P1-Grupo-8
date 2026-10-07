#if UNITY_EDITOR
using System;
using System.Collections;
using System.IO;
using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
public class HonorsCapacityFlowTests {
    [UnityTest] public IEnumerator ScenarioFailureDiscardAndNativeRegeneration(){
        yield return EditorSceneManager.LoadSceneAsyncInPlayMode("Assets/Scenes/HonorsViewerScene.unity",new LoadSceneParameters(LoadSceneMode.Single));yield return null;
        var viewer=UnityEngine.Object.FindAnyObjectByType<StructureViewer>();var c=viewer.GetComponent<HonorsConfiguration>();Assert.IsNotNull(c);Assert.IsTrue(c.H5CapacityComparison);Assert.IsFalse(c.H2ProfilesAndQA||c.H3SpatialDiagrams);Assert.IsNotNull(viewer.GetComponent<HonorsCapacityComparisonPanel>());
        var session=new HonorsCapacitySession();var input=File.ReadAllText(StructureViewer.ProjectJsonPath);
        viewer.SetCase("C2");viewer.Search("E1_287");var picker=UnityEngine.Object.FindAnyObjectByType<ElementPicker>();var pm=UnityEngine.Object.FindAnyObjectByType<PMPanel>();pm.ShowPMForElement(picker.Selected);
        Assert.That(picker.Selected.data.id,Is.EqualTo(287));
        Assert.IsTrue(session.LoadCertifiedScenario(viewer));yield return null;
        Assert.That(Array.Find(viewer.Data.elements,e=>e.id==287).pmCurveId,Is.EqualTo("COL70/70_20f28"));
        var current=viewer.Data;Assert.IsFalse(session.Apply("{}",viewer));Assert.AreSame(current,viewer.Data);
        session.Discard(viewer);yield return null;Assert.That(Array.Find(viewer.Data.elements,e=>e.id==287).pmCurveId,Is.EqualTo("COL70/70_16f28"));
        Assert.IsTrue(session.Start(viewer),session.Message);float until=Time.realtimeSinceStartup+310;
        while(session.Job.Running&&Time.realtimeSinceStartup<until){session.Poll(viewer);yield return null;}
        Assert.IsTrue(session.Applied,session.Message);viewer.Search("E1_287");viewer.SetCase("C2");pm.ShowPMForElement(picker.Selected);
        var dir=Path.Combine(HonorsPaths.Evidence,"unity_H5");Directory.CreateDirectory(dir);
        File.WriteAllText(Path.Combine(dir,"native_flow.json"),"{\"nativeUnity\":\""+Application.unityVersion+"\",\"capacityJob\":true,\"curve\":\"COL70/70_20f28\",\"failureRetainedScenario\":true,\"discardRestored\":true,\"uiMouseClickExecuted\":false}");
        var cam=Camera.main;var rt=new RenderTexture(1280,720,24);var prior=cam.targetTexture;var active=RenderTexture.active;
        cam.targetTexture=rt;cam.Render();RenderTexture.active=rt;var capture=new Texture2D(1280,720,TextureFormat.RGB24,false);capture.ReadPixels(new Rect(0,0,1280,720),0,0);capture.Apply();
        File.WriteAllBytes(Path.Combine(dir,"viewer_after_geometry.png"),capture.EncodeToPNG());cam.targetTexture=prior;RenderTexture.active=active;UnityEngine.Object.Destroy(rt);UnityEngine.Object.Destroy(capture);yield return null;
        session.Discard(viewer);yield return null;Assert.That(viewer.GetComponentsInChildren<ElementSelectable>(true).Length,Is.EqualTo(628));
        Assert.That(File.ReadAllText(StructureViewer.ProjectJsonPath),Is.EqualTo(input));session.Dispose();
        var normal=ViewerUI.Session;normal.LoadFrom(viewer.Data);normal.armSec["COL70/70"]=new AnalysisSession.Arm{barras="20f28"};
        Assert.IsTrue(normal.StartReanalysis(),normal.Message);until=Time.realtimeSinceStartup+310;
        while(normal.job.Running&&Time.realtimeSinceStartup<until){normal.Poll(viewer);yield return null;}
        Assert.IsTrue(normal.ScenarioLoaded,normal.Message);Assert.That(Array.Find(viewer.Data.elements,e=>e.id==287).pmCurveId,Is.EqualTo("COL70/70_20f28"));
        Assert.IsFalse(normal.SaveAsCurrent(viewer));normal.DiscardScenario(viewer);yield return null;
        Assert.That(File.ReadAllText(StructureViewer.ProjectJsonPath),Is.EqualTo(input));
        File.WriteAllText(Path.Combine(dir,"existing_AnalysisSession_flow.json"),"{\"ReanalysisOpenSees\":true,\"PMCurveBeforeAfter\":true,\"DiscardScenarioReloadOriginal\":true,\"SaveForbidden\":true,\"UIButtonsPhysicallyClicked\":false}");
    }
}
#endif
