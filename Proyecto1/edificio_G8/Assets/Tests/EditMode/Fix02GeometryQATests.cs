using System;
using NUnit.Framework;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
public class Fix02GeometryQATests {
    [Test] public void HonorsDefaultIsFullModelAndMarkerCalibrationRemainsIndependent(){
        var scene=EditorSceneManager.OpenScene(HonorsSetupPath);
        var model=UnityEngine.Object.FindAnyObjectByType<ARStructure>();
        Assert.AreEqual(ARStructure.Mode.Maqueta100,model.mode);
        Assert.IsTrue(model.ShowBeams&&model.ShowColumns&&model.ShowWalls&&model.ShowBraces);Assert.IsFalse(model.ShowIds);
        Assert.IsNotNull(model.GetComponent<ARStructuralDiagramOverlay>());
        var p=JsonUtility.FromJson<ARMarkerProfileRegistry.Bundle>(Resources.Load<TextAsset>("Honors/marker_profiles").text).profiles[0];
        Assert.AreEqual(0,p.mode);Assert.AreEqual(1,p.scale);Assert.IsTrue(p.sector); // registration stays documented
        var transform=new ModelCoordinateTransform(.01f,new Vector3(3,4,0),false);
        Assert.AreEqual(new Vector3(.01f,.03f,.02f),transform.Forward(new Vector3(4,6,3)));
    }
    const string HonorsSetupPath="Assets/Scenes/ARHonorsScene.unity";
    [TestCase(1,0,0)][TestCase(-1,0,0)][TestCase(0,1,0)][TestCase(0,-1,0)][TestCase(0,0,1)][TestCase(1,2,3)]
    public void MyVzUseModelAxesAndTransformExactlyOnce(float x,float y,float z){
        Vector3 a=new Vector3(3,-2,7),b=a+new Vector3(x,y,z)*4;float L=Vector3.Distance(a,b);
        var d=new StructuralResultSampler.Diagram{Length=L,X=new[]{0f,L/2,L},Values=new[]{-2f,5f,3f},Initial=-2,Final=3,Minimum=-2,Maximum=5};
        StructuralResultSampler.Axes(b-a,out _,out _,out var axisZ);
        foreach(int k in new[]{4,2})foreach(float scale in new[]{1f,.01f})foreach(bool column in new[]{true,false}){
            var transform=new ModelCoordinateTransform(scale,new Vector3(.35f,-7.25f,5.16f),column);
            var vertices=ARDiagramGeometry.Build(a,b,d,k,.02f,transform.Forward);
            for(int i=0;i<3;i++)Assert.Less(Vector3.Distance(vertices[i],transform.Forward(a+(d.X[i]/L)*(b-a)+.02f*d.Values[i]*axisZ)),1e-6);
            Assert.Less(Vector3.Distance(vertices[0],transform.Forward(a-.04f*axisZ)),1e-6);
            Assert.Less(Vector3.Distance(vertices[2],transform.Forward(b+.06f*axisZ)),1e-6);
        }
    }
    [Test] public void ZeroAndUnavailableRemainDistinct(){
        var d=new StructuralResultSampler.Diagram{Length=2,X=new[]{0f,2f},Values=new[]{0f,0f}};
        Assert.AreEqual(new[]{Vector3.zero,Vector3.right*2},ARDiagramGeometry.Build(Vector3.zero,Vector3.right*2,d,2,1,v=>v));
        Assert.That(ARDiagramGeometry.Unavailable(ResultAvailability.Missing),Does.Contain("datos"));
        Assert.That(ARDiagramGeometry.Unavailable(ResultAvailability.Partial),Does.Contain("parcial"));
        Assert.That(ARDiagramGeometry.Unavailable(ResultAvailability.Invalid),Does.Contain("inválido"));
        Assert.Throws<ArgumentException>(()=>ARDiagramGeometry.Build(Vector3.zero,Vector3.right*2,d,3,1,v=>v));
    }
    [Test] public void QAWithoutSamplesShowsCollectingAndNoFakeAccuracy(){
        var q=new HonorsQATelemetry();var text=q.Format("Searching",null);
        Assert.That(text,Does.Contain("0/10"));Assert.That(text,Does.Contain("no error físico"));
        Assert.AreEqual(0,q.Data.position.count);
    }
    [Test] public void QAMetricsWindowEventsAndNoiseAreReproducible(){
        var q=new HonorsQATelemetry();q.Event("detection",0);q.Event("accepted",0);
        for(int i=0;i<10;i++)q.Sample(new ARRegistrationRecorder.Sample{timestamp=i*.1,relativeAvailable=true,relativeMm=i+1,relativeAngleDeg=i*.1f,imagePosition=Vector3.right*(i+1)*.001f,anchorRotation=Quaternion.identity,anchorPosition=Vector3.zero});
        Assert.AreEqual(10,q.Data.samples);Assert.AreEqual(5.5f,q.Data.position.median);
        Assert.AreEqual(Mathf.Sqrt(38.5f),q.Data.position.rms,1e-5);Assert.AreEqual(10,q.Data.position.p95);
        Assert.AreEqual(Mathf.Sqrt(8.25f),q.Data.noiseMm,1e-4);Assert.That(q.Format("Anchored",null),Does.Contain("RMS"));
        q.Event("loss",1);q.Sample(new ARRegistrationRecorder.Sample{timestamp=6,relativeAvailable=false});
        Assert.AreEqual(0,q.Data.samples);q.Event("detection",7);q.Event("recovery",7);q.Event("reanchor_requested",7);q.Event("pause",8);q.Event("resume",9);
        Assert.AreEqual(2,q.Data.detections);Assert.AreEqual(1,q.Data.losses);Assert.AreEqual(1,q.Data.recoveries);Assert.AreEqual(1,q.Data.reanchors);Assert.AreEqual(1,q.Data.pauses);Assert.AreEqual(1,q.Data.resumes);
    }
}
