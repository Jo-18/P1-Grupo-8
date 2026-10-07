using System;
using System.Collections;
using System.Reflection;
using System.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.XR.ARFoundation;
using Object=UnityEngine.Object;
public class Fix02ARFlowTests {
    GameObject app,anchorGo;ARStructure model;ARImageAnchor owner;HonorsAnchorDriver driver;StructuralSelectionController select;ARInspectorUI ui;ARStructuralDiagramOverlay overlay;
    class Fake:IHonorsAnchorProvider {
        readonly ARAnchor anchor;public Fake(ARAnchor a){anchor=a;}
        public Task<HonorsAnchorResult> Add(Pose p)=>Task.FromResult(new HonorsAnchorResult(true,anchor));
    }
    [UnitySetUp] public IEnumerator Setup(){
        UnityData.LoadData(JsonUtility.FromJson<StructureData>(Resources.Load<TextAsset>("estructura_p1l4_unity").text));
        app=new GameObject("Fix02 runtime");var c=app.AddComponent<HonorsConfiguration>();c.H2ProfilesAndQA=true;c.H5CapacityComparison=true;
        owner=app.AddComponent<ARImageAnchor>();owner.enabled=false;model=app.AddComponent<ARStructure>();select=app.AddComponent<StructuralSelectionController>();ui=app.AddComponent<ARInspectorUI>();driver=app.AddComponent<HonorsAnchorDriver>();overlay=app.AddComponent<ARStructuralDiagramOverlay>();
        anchorGo=new GameObject("Synthetic ARCore seam");anchorGo.SetActive(false);var anchor=anchorGo.AddComponent<ARAnchor>();anchor.enabled=false;anchorGo.SetActive(true);
        driver.Provider=new Fake(anchor);yield return null;
        var p=JsonUtility.FromJson<ARMarkerProfileRegistry.Bundle>(Resources.Load<TextAsset>("Honors/marker_profiles").text).profiles[0];
        driver.Session.Observe("marker-real-profile",true,0,0);var request=driver.Session.Begin("marker-real-profile",new Pose(),p,0);
        var task=driver.ProcessRequest(request,Vector2.one*.2f);yield return null;
        Assert.IsTrue(task.IsCompleted);ui.SetCase("C2");
    }
    [UnityTearDown] public IEnumerator Cleanup(){Object.Destroy(app);if(anchorGo!=null)Object.Destroy(anchorGo);yield return null;}
    [UnityTest] public IEnumerator FirstHonorsAnchorPreservesFullBuildingAndExplicitModes(){
        Assert.AreEqual(ARStructure.Mode.Maqueta100,model.mode);Assert.AreEqual(.01f,model.Scale);Assert.AreEqual(628,model.Elements.Count);Assert.AreEqual(628,model.VisibleElements().Count);
        Assert.AreEqual(Vector3.one,model.ModelRoot.localScale);Assert.AreEqual(Vector3.one,owner.ContentRoot.localScale);
        Assert.IsFalse(model.SupportRoot.gameObject.activeSelf);Assert.IsFalse(model.AxesRoot.gameObject.activeSelf);
        int walls=0;var buildings=new System.Collections.Generic.HashSet<string>();var min=new Vector3(float.PositiveInfinity,float.PositiveInfinity,float.PositiveInfinity);var max=-min;
        foreach(var e in model.Elements){if(e.wall!=null)walls++;buildings.Add(e.element.sourceBuilding);Assert.AreNotEqual("rigido",e.element.type);if(e.wall==null)Assert.IsFalse(UnityData.IsAnalysisOnly(e.element));}
        Assert.AreEqual(91,walls);Assert.AreEqual(537,model.Elements.Count-walls);Assert.AreEqual(2,buildings.Count);
        foreach(var n in UnityData.Structure.nodes){var p=new Vector3(n.x,n.y,n.z);min=Vector3.Min(min,p);max=Vector3.Max(max,p);}
        var dimensions=(max-min)*model.Scale;
        Assert.AreEqual(.815f,dimensions.x,.005f);Assert.AreEqual(.214f,dimensions.y,.005f);Assert.AreEqual(.198f,dimensions.z,.005f);
        model.SetMode(ARStructure.Mode.Columna1a1);yield return null;Assert.AreEqual(1,model.Scale);Assert.Less(model.Elements.Count,628);
        model.SetMode(ARStructure.Mode.Maqueta100);yield return null;Assert.AreEqual(.01f,model.Scale);Assert.AreEqual(628,model.VisibleElements().Count);Assert.IsNull(select.Selected);
        model.SetMode(ARStructure.Mode.SobrePlano);yield return null;Assert.AreEqual(628,model.Elements.Count);Assert.Greater(model.Scale,0);
        model.SetMode(ARStructure.Mode.Maqueta100);yield return null;
    }
    [UnityTest] public IEnumerator SelectionAcrossTypesFloorsBuildingsDoesNotRebuildAndHiddenCannotPick(){
        var root=model.ModelRoot;var first=model.Elements[0];select.Select(first);var highlighted=first.GetComponent<Renderer>().sharedMaterial;
        foreach(var tag in model.Elements){select.Select(tag);Assert.AreSame(tag,select.Selected);Assert.AreSame(root,model.ModelRoot);}
        Assert.AreNotSame(highlighted,first.GetComponent<Renderer>().sharedMaterial);select.Clear();Assert.IsNull(ui.SelectedTag);Assert.AreEqual(628,model.VisibleElements().Count);
        var column=model.Elements.Find(t=>t.element.type=="columna");select.Select(column);model.ShowColumns=false;model.ApplyVisibility();Assert.IsNull(select.Selected);
        Assert.IsFalse(column.GetComponent<Collider>().enabled&&column.gameObject.activeInHierarchy);
        select.Select(column);Assert.IsNull(select.Selected);model.ShowColumns=true;model.ApplyVisibility();
        ui.SetCase("EY");Assert.AreSame(root,model.ModelRoot);Assert.AreEqual("EY",ui.ActiveCase);yield return null;
    }
    [UnityTest] public IEnumerator MyVzFollowSamplerCaseAndCleanupWithoutChanging2D(){
        var a=model.Elements.Find(t=>t.element.id==287);var b=model.Elements.Find(t=>t.element.type=="viga");select.Select(a);
        var root=model.ModelRoot;overlay.Show(4);Assert.IsNotNull(overlay.Curve);Assert.IsFalse(overlay.Curve.useWorldSpace);Assert.AreSame(root,overlay.OverlayRoot.parent);
        var sampler=new StructuralResultSampler(UnityData.Repository);Assert.IsTrue(sampler.TryDiagram(a.element,"C2",4,out var d,out _));
        var expected=ARDiagramGeometry.Build(UnityData.Repository.Point(a.element.nodeI),UnityData.Repository.Point(a.element.nodeJ),d,4,overlay.Gain,model.ModelToAnchor);
        for(int i=0;i<expected.Length;i++)Assert.Less(Vector3.Distance(expected[i],overlay.Curve.GetPosition(i)),1e-7);
        int updates=overlay.GeometryUpdates;yield return null;yield return null;Assert.AreEqual(updates,overlay.GeometryUpdates);
        ui.SetCase("C1");Assert.Greater(overlay.GeometryUpdates,updates);Assert.AreSame(root,model.ModelRoot);
        overlay.Show(2);Assert.AreEqual(2,overlay.Component);Assert.IsNotNull(overlay.Curve);Assert.That(overlay.Description,Does.Contain("m/kN"));
        // Same raster renderer/source contract remains independent of the spatial overlay.
        var texture=ARDiagramPanel.Rasterize(ARPlotGeometry.DiagramPoints(overlay.Diagram),null,300,180);Assert.AreEqual(300,texture.width);Object.Destroy(texture);
        select.Select(b);Assert.That(overlay.Description,Does.Contain(b.element.elementTag));select.Clear();Assert.IsNull(overlay.OverlayRoot);
        select.Select(a);model.ShowColumns=false;model.ApplyVisibility();Assert.IsNull(overlay.OverlayRoot);model.ShowColumns=true;model.ApplyVisibility();
        select.Select(a);model.Rebuild();yield return null;Assert.IsNull(overlay.OverlayRoot);Assert.IsNull(select.Selected);Assert.AreEqual(628,model.Elements.Count);
        select.Select(model.Elements.Find(t=>t.wall!=null));Assert.IsNull(overlay.Curve);Assert.That(overlay.Description,Does.Contain("muros"));
        overlay.Hide();Assert.IsFalse(app.GetComponent<HonorsConfiguration>().H3SpatialDiagrams);Assert.IsNull(overlay.OverlayRoot);Assert.AreEqual(628,model.VisibleElements().Count);
    }
    [UnityTest] public IEnumerator MissingPartialInvalidClearOverlayAndValidZeroDraws(){
        var original=Resources.Load<TextAsset>("estructura_p1l4_unity").text;
        foreach(var state in new[]{"missing","partial","invalid","zero"}){
            var data=JsonUtility.FromJson<StructureData>(original);
            if(state=="missing")data.p1l4.elementForces=Array.FindAll(data.p1l4.elementForces,f=>f.id!=287||f.combo!="C2");
            else if(state=="invalid")Array.Find(data.p1l4.caseStates,s=>s.name=="C2").ok=false;
            else Array.Find(data.p1l4.elementForces,f=>f.id==287&&f.combo=="C2").f=new float[state=="partial"?3:12];
            UnityData.LoadData(data);yield return null;ui.SetCase("C2");select.Select(model.Elements.Find(t=>t.element.id==287));overlay.Show(2);
            if(state=="zero"){Assert.IsNotNull(overlay.Curve);Assert.AreEqual(0,overlay.Diagram.Maximum);}
            else{Assert.IsNull(overlay.Curve);Assert.That(overlay.Description,Does.Contain(state=="missing"?"datos":state=="partial"?"parcial":"inválido"));}
        }
        UnityData.LoadData(JsonUtility.FromJson<StructureData>(original));yield return null;
    }
    [UnityTest] public IEnumerator H2InformationReflectsRealSamplesAndExportsRecorder(){
        owner.enabled=true;yield return null;driver.QA.Event("detection",0);
        for(int i=0;i<10;i++)driver.QA.Sample(new ARRegistrationRecorder.Sample{timestamp=i*.1,marker="Marcador_E1_243",trackableId="controlled-provider-seam",profile="Marcador_E1_243",sessionState="Synthetic",markerState="Tracking",anchorState="Tracking",relativeAvailable=true,relativeMm=2,relativeAngleDeg=.1f,anchorRotation=Quaternion.identity,imagePosition=Vector3.right*.002f});
        Assert.That(driver.QAInformation,Does.Contain("mediana"));Assert.That(driver.QAInformation,Does.Contain("Marcador_E1_243"));
        Assert.IsTrue(driver.ExportQA());Assert.That(driver.QAExportStatus,Does.Contain("QA exportada"));
        var profiles=new System.Collections.Generic.List<ARMarkerProfile>(driver.Registry.Profiles);Assert.IsFalse(profiles.Find(p=>p.markerId=="Marcador_Honors_Plano").enabled);yield return null;
    }
    [UnityTest] public IEnumerator NativeRenderedFullBuildingAndMyVzEvidence(){
        var go=new GameObject("Fix02 evidence camera");var cam=go.AddComponent<Camera>();cam.enabled=false;cam.cullingMask=1<<ARStructure.StructuralLayer;cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=new Color(.08f,.1f,.14f);cam.nearClipPlane=.01f;cam.farClipPlane=10;cam.fieldOfView=52;
        var lightGo=new GameObject("Fix02 light");var light=lightGo.AddComponent<Light>();light.type=LightType.Directional;light.intensity=1;lightGo.transform.rotation=Quaternion.Euler(40,-30,0);
        var bounds=new Bounds(model.Elements[0].transform.position,Vector3.zero);foreach(var tag in model.Elements)bounds.Encapsulate(tag.GetComponent<Renderer>().bounds);
        cam.transform.position=bounds.center+new Vector3(.65f,.55f,-.65f);cam.transform.LookAt(bounds.center);
        var dir=System.IO.Path.Combine(HonorsPaths.Evidence,"fix02","renders");System.IO.Directory.CreateDirectory(dir);
        foreach(int k in new[]{-1,4,2}){
            if(k>=0){select.Select(model.Elements.Find(t=>t.element.id==(k==4?287:72)));ui.SetCase("C2");overlay.Show(k);var plotBounds=new Bounds(overlay.Curve.transform.TransformPoint(overlay.Curve.GetPosition(0)),Vector3.zero);for(int v=1;v<overlay.Curve.positionCount;v++)plotBounds.Encapsulate(overlay.Curve.transform.TransformPoint(overlay.Curve.GetPosition(v)));cam.transform.position=plotBounds.center+new Vector3(.10f,.08f,-.10f);cam.transform.LookAt(plotBounds.center);}
            var rt=new RenderTexture(1280,720,24);var previous=RenderTexture.active;cam.targetTexture=rt;cam.Render();RenderTexture.active=rt;
            var image=new Texture2D(1280,720,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1280,720),0,0);image.Apply();System.IO.File.WriteAllBytes(System.IO.Path.Combine(dir,k<0?"full_628.png":k==4?"H3_My.png":"H3_Vz.png"),image.EncodeToPNG());
            RenderTexture.active=previous;cam.targetTexture=null;Object.Destroy(image);Object.Destroy(rt);
            Assert.AreEqual(628,model.VisibleElements().Count);yield return null;
        }
        overlay.Hide();Object.Destroy(go);Object.Destroy(lightGo);yield return null;
    }

}
