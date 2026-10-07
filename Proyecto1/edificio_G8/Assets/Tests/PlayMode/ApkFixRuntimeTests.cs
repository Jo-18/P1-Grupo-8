using System.Collections;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.XR.ARFoundation;
public class ApkFixRuntimeTests {
    [UnityTest] public IEnumerator TypedSphereHasOneColliderAndARSupportsCannotPick(){
        var sphere=PrimitiveGeometry.CreateSphere();Assert.AreEqual(1,sphere.GetComponents<SphereCollider>().Length);
        Object.Destroy(sphere);
        UnityData.LoadData(JsonUtility.FromJson<StructureData>(Resources.Load<TextAsset>("estructura_p1l4_unity").text));
        var app=new GameObject("Fix regression");var model=app.AddComponent<ARStructure>();app.AddComponent<StructuralSelectionController>();
        var root=new GameObject("Fix anchor");yield return null;
        typeof(ARStructure).GetMethod("OnAnchored",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(model,new object[]{root.transform});yield return null;
        Assert.AreEqual(628,model.Elements.Count);Assert.IsFalse(model.SupportRoot.gameObject.activeSelf);
        Assert.AreEqual(0,model.SupportRoot.GetComponentsInChildren<Collider>(true).Length);
        foreach(var e in model.Elements)Assert.AreEqual(1,e.GetComponents<BoxCollider>().Length);
        Object.Destroy(app);Object.Destroy(root);yield return null;LogAssert.NoUnexpectedReceived();
    }
    [UnityTest] public IEnumerator PlaneUpdatesCannotLeavePinkRendererVisible(){
        var go=new GameObject("Detected plane");go.AddComponent<ARPlane>();go.AddComponent<MeshFilter>();
        var renderer=go.AddComponent<MeshRenderer>();var collider=go.AddComponent<MeshCollider>();
        var visualizer=go.AddComponent<ARPlaneMeshVisualizer>();var policy=go.AddComponent<ARPlaneDebugVisibility>();
        ARPlaneDebugVisibility.ShowPlanes=false;renderer.enabled=true;yield return null;yield return null;
        Assert.IsFalse(renderer.enabled);Assert.IsTrue(visualizer.enabled);Assert.IsTrue(collider.enabled);
        ARPlaneDebugVisibility.ShowPlanes=true;renderer.enabled=true;policy.Apply();Assert.IsTrue(renderer.enabled);
        ARPlaneDebugVisibility.ShowPlanes=false;policy.Apply();Assert.IsFalse(renderer.enabled);
        Object.Destroy(go);yield return null;
    }
}
