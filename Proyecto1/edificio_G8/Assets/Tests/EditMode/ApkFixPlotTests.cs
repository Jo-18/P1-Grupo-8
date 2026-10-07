using System;
using System.IO;
using NUnit.Framework;
using UnityEngine;
using UnityEditor;
public class ApkFixPlotTests {
    [TestCase(1920,1080)][TestCase(1080,2400)][TestCase(1080,2340)]
    public void EveryRealCurveAndDemandFitsInPlot(int width,int height){
        UnityData.LoadData(JsonUtility.FromJson<StructureData>(Resources.Load<TextAsset>("estructura_p1l4_unity").text));
        var repo=UnityData.Repository;var sampler=new StructuralResultSampler(repo);
        ARInspectorLayout.Calculate(width,height,420,new Rect(0,32,width,height-64),false,out var scale,out var safe,out var header,out var panel);
        var plot=ARPlotGeometry.Interior(new Rect(0,0,panel.width-28,190));
        foreach(var e in repo.Elements.Values)foreach(var c in repo.Cases)for(int k=0;k<6;k++){
            if(!sampler.TryDiagram(e,c,k,out var d,out _))continue;
            var points=ARPlotGeometry.DiagramPoints(d);AssertInside(points,null,plot);
        }
        var element=repo.Elements[287];
        foreach(var c in repo.Cases)if(sampler.TryPM(element,c,out var demand)){
            var points=ARPlotGeometry.PMPoints(repo.Curve(element.pmCurveId??element.sectionId));
            AssertInside(points,new Vector2(demand.y,demand.x),plot);
        }
    }
    static void AssertInside(Vector2[] points,Vector2? demand,Rect r){
        var bounds=ARPlotGeometry.Fit(points,demand);
        foreach(var p in points)Assert.IsTrue(r.Contains(bounds.Map(p,r)),"Plot exceeded bounds");
        if(demand.HasValue)Assert.IsTrue(r.Contains(bounds.Map(demand.Value,r)));
    }
    [Test] public void ConstantZeroNearConstantAndNegativeDataHaveFinitePaddedScale(){
        foreach(float value in new[]{0f,1e-9f,-5f,500f}){
            var p=new[]{new Vector2(0,value),new Vector2(3,value)};
            var b=ARPlotGeometry.Fit(p);Assert.Greater(b.ymax,b.ymin);AssertInside(p,null,new Rect(19,41,200,160));
        }
        Assert.Throws<ArgumentException>(()=>ARPlotGeometry.Fit(new[]{Vector2.zero,new Vector2(1,float.NaN)}));
    }
    [TestCase(1920,1080)][TestCase(1080,2400)][TestCase(1080,2340)]
    public void OpenCollapsedAndRotatedPanelStayWithinSafeArea(int w,int h){
        foreach(bool collapsed in new[]{false,true})foreach(bool rotate in new[]{false,true}){
            int width=rotate?h:w,height=rotate?w:h;
            ARInspectorLayout.Calculate(width,height,420,new Rect(0,28,width,height-56),collapsed,out _,out var safe,out var header,out var panel);
            Assert.GreaterOrEqual(panel.xMin,safe.xMin);Assert.LessOrEqual(panel.xMax,safe.xMax);
            Assert.GreaterOrEqual(panel.yMin,header.yMax);Assert.LessOrEqual(panel.yMax,safe.yMax);
        }
    }
    [Test] public void ActualPlanePrefabHidesVisualsAndRetainsTrackingMeshAndCollider(){
        var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AR/ARPlaneVisual.prefab");
        Assert.IsNotNull(prefab.GetComponent(Type.GetType("UnityEngine.XR.ARFoundation.ARPlane, Unity.XR.ARFoundation",true)));Assert.IsTrue(((Behaviour)prefab.GetComponent(Type.GetType("UnityEngine.XR.ARFoundation.ARPlaneMeshVisualizer, Unity.XR.ARFoundation",true))).enabled);
        Assert.IsNotNull(prefab.GetComponent<MeshCollider>());Assert.IsNotNull(prefab.GetComponent<ARPlaneDebugVisibility>());
        Assert.IsFalse(prefab.GetComponent<MeshRenderer>().enabled);
    }
    [Test] public void RasterEvidenceContainsRealMyMzVzTPMWithEmptyBoundary(){
        UnityData.LoadData(JsonUtility.FromJson<StructureData>(Resources.Load<TextAsset>("estructura_p1l4_unity").text));
        var repo=UnityData.Repository;var sampler=new StructuralResultSampler(repo);var e=repo.Elements[287];
        var directory=Path.Combine(HonorsPaths.Evidence,"fix01","plots");Directory.CreateDirectory(directory);
        for(int k=0;k<6;k++){
            Assert.IsTrue(sampler.TryDiagram(e,"C2",k,out var d,out _));
            Save(ARPlotGeometry.DiagramPoints(d),null,Path.Combine(directory,StructuralResultSampler.Names[k]+".png"));
        }
        Assert.IsTrue(sampler.TryPM(e,"C2",out var demand));
        Save(ARPlotGeometry.PMPoints(repo.Curve(e.pmCurveId??e.sectionId)),new Vector2(demand.y,demand.x),Path.Combine(directory,"PM.png"));
    }
    static void Save(Vector2[] p,Vector2? demand,string file){
        var t=ARDiagramPanel.Rasterize(p,demand,800,360);
        try {
            var pixels=t.GetPixels32();for(int x=0;x<t.width;x++){Assert.AreEqual(22,pixels[x].r);Assert.AreEqual(22,pixels[(t.height-1)*t.width+x].r);}
            File.WriteAllBytes(file,t.EncodeToPNG());
        } finally {UnityEngine.Object.DestroyImmediate(t);}
    }
}
