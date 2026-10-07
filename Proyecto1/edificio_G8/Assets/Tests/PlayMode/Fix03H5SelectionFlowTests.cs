using System;
using System.Collections;
using System.IO;
using System.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.XR.ARFoundation;
using Object=UnityEngine.Object;
public class Fix03H5SelectionFlowTests {
    GameObject app,anchorGo;ARStructure model;StructuralSelectionController selection;ARInspectorUI inspector;HonorsCapacityComparisonPanel panel;ARStructuralDiagramOverlay overlay;HonorsAnchorDriver driver;
    class Fake:IHonorsAnchorProvider{readonly ARAnchor anchor;public Fake(ARAnchor a){anchor=a;}public Task<HonorsAnchorResult> Add(Pose p)=>Task.FromResult(new HonorsAnchorResult(true,anchor));}
    [UnitySetUp] public IEnumerator Setup(){
        UnityData.LoadData(JsonUtility.FromJson<StructureData>(Resources.Load<TextAsset>("estructura_p1l4_unity").text));
        app=new GameObject("Fix03 runtime");var config=app.AddComponent<HonorsConfiguration>();config.H2ProfilesAndQA=true;config.H5CapacityComparison=true;
        var owner=app.AddComponent<ARImageAnchor>();owner.enabled=false;model=app.AddComponent<ARStructure>();selection=app.AddComponent<StructuralSelectionController>();inspector=app.AddComponent<ARInspectorUI>();driver=app.AddComponent<HonorsAnchorDriver>();overlay=app.AddComponent<ARStructuralDiagramOverlay>();panel=app.AddComponent<HonorsCapacityComparisonPanel>();
        anchorGo=new GameObject("Fix03 synthetic seam");anchorGo.SetActive(false);var anchor=anchorGo.AddComponent<ARAnchor>();anchor.enabled=false;anchorGo.SetActive(true);driver.Provider=new Fake(anchor);yield return null;
        var profile=JsonUtility.FromJson<ARMarkerProfileRegistry.Bundle>(Resources.Load<TextAsset>("Honors/marker_profiles").text).profiles[0];driver.Session.Observe("marker",true,0,0);var request=driver.Session.Begin("marker",new Pose(),profile,0);
        var task=driver.ProcessRequest(request,Vector2.one*.2f);yield return null;Assert.IsTrue(task.IsCompleted);inspector.SetCase("C2");
    }
    [UnityTearDown] public IEnumerator Cleanup(){Object.Destroy(app);Object.Destroy(anchorGo);yield return null;}
    void Select(int id){selection.Select(model.Elements.Find(e=>e.element.id==id));}
    [UnityTest] public IEnumerator HotSelectionCloseOpenCaseAndUnsupportedAreBoundWithoutRebuild(){
        var root=model.ModelRoot;var repo=UnityData.Repository;int changes=0;model.Rebuilt+=()=>changes++;
        Select(287);panel.ToggleOpen();Assert.IsTrue(panel.IsOpen);Assert.AreEqual(287,panel.Context.Element.id);var oldDemand=panel.PlotDemand;
        panel.ToggleOpen();Select(301);panel.ToggleOpen();Assert.AreEqual(301,panel.Context.Element.id);Assert.AreNotEqual(oldDemand,panel.PlotDemand);Assert.IsNull(panel.Context.AfterCurve);
        Assert.That(panel.Context.Details,Does.Contain("4φ28+16φ36"));Assert.That(panel.Context.Details,Does.Not.Contain("E1_287"));
        Select(243);Assert.AreEqual(243,panel.Context.Element.id);Select(287);inspector.SetCase("C1");Assert.AreEqual("C1",panel.Context.CaseId);Assert.AreEqual(616.4f,panel.Context.Demand.x);
        inspector.SetCase("EX");Assert.AreEqual("EX",panel.Context.CaseId);Assert.IsNull(panel.Context.BaseCombo);Assert.IsTrue(panel.Context.HasDemand);
        selection.Select(model.Elements.Find(e=>e.element.type=="viga"));Assert.IsNull(panel.Context.BaseCurve);Assert.IsNull(panel.PlotDemand);
        Select(287);inspector.SetCase("C2");Assert.IsTrue(panel.Context.ComparisonAvailable);selection.Clear();Assert.IsNull(panel.Context.Element);Assert.IsNull(panel.Chart());
        Assert.AreEqual(0,changes);Assert.AreSame(root,model.ModelRoot);Assert.AreSame(repo,UnityData.Repository);Assert.AreEqual(628,model.Elements.Count);yield return null;
    }
    [UnityTest] public IEnumerator PlotUsesSelectedPointAndPreservesReferenceAndExceptionEvidence(){
        var dir=Path.Combine(HonorsPaths.Evidence,"H5_selection");Directory.CreateDirectory(dir);
        foreach(int id in new[]{287,301,288,243}){
            Select(id);var c=panel.Context;var t=panel.Chart();Assert.IsNotNull(t);
            var bounds=HonorsCapacityPlot.Bounds(c.BaseCurve,c.AfterCurve,c.Demand);var mapped=bounds.Map(new Vector2(c.Demand.y,c.Demand.x),new Rect(6,6,t.width-13,t.height-13));
            var color=t.GetPixel(Mathf.RoundToInt(mapped.x),t.height-1-Mathf.RoundToInt(mapped.y));Assert.Greater(color.r,.9);Assert.Greater(color.g,.7);Assert.Less(color.b,.1);
            File.WriteAllBytes(Path.Combine(dir,c.Element.elementTag+"_C2.png"),t.EncodeToPNG());
            File.WriteAllText(Path.Combine(dir,c.Element.elementTag+"_C2.txt"),c.Header+"\n"+c.Details+"\nDCR base "+c.BaseCombo?.DCR_PM+" / after "+c.AfterCombo?.DCR_PM);
            Assert.AreEqual(c.Demand,panel.PlotDemand.Value);yield return null;
        }
        Select(287);var withAfter=panel.Chart();panel.SetComparisonVisible(false);Assert.IsNotNull(panel.Chart());Assert.AreNotSame(withAfter,panel.Chart());Assert.AreEqual(287,panel.Context.Element.id);
        Assert.AreEqual(628,model.VisibleElements().Count);
    }
    [UnityTest] public IEnumerator H5DoesNotResetH2H3AnchorOrDatasetAndHiddenClearsContext(){
        Select(287);overlay.Show(4);Assert.IsNotNull(overlay.Curve);var root=model.ModelRoot;var content=app.GetComponent<ARImageAnchor>().ContentRoot;var repo=UnityData.Repository;
        panel.ToggleOpen();panel.SetComparisonVisible(false);panel.SetComparisonVisible(true);Assert.AreSame(root,model.ModelRoot);Assert.AreSame(content,app.GetComponent<ARImageAnchor>().ContentRoot);Assert.AreSame(repo,UnityData.Repository);
        Select(288);Assert.That(overlay.Description,Does.Contain("E1_288"));Assert.IsNotNull(overlay.Curve);inspector.SetCase("C1");Assert.That(overlay.Description,Does.Contain("C1"));Assert.AreEqual("C1",panel.Context.CaseId);
        Assert.IsNotNull(driver.ActiveProfile);Assert.That(driver.QAInformation,Does.Contain("QA RELATIVA"));var profiles=new System.Collections.Generic.List<ARMarkerProfile>(driver.Registry.Profiles);Assert.IsFalse(profiles.Find(p=>p.markerId=="Marcador_Honors_Plano").enabled);model.ShowColumns=false;model.ApplyVisibility();Assert.IsNull(panel.Context.Element);Assert.IsNull(overlay.Curve);Assert.AreSame(root,model.ModelRoot);model.ShowColumns=true;model.ApplyVisibility();Assert.AreEqual(628,model.VisibleElements().Count);yield return null;
    }
}
