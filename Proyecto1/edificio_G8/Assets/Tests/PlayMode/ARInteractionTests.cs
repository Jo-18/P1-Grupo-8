using System.Collections;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
public class ARInteractionTests {
    GameObject app,root;ARStructure model;StructuralSelectionController selection;ARInspectorUI ui;
    [UnitySetUp] public IEnumerator Setup(){UnityData.LoadData(JsonUtility.FromJson<StructureData>(Resources.Load<TextAsset>("estructura_p1l4_unity").text));app=new GameObject("AR test app");model=app.AddComponent<ARStructure>();selection=app.AddComponent<StructuralSelectionController>();ui=app.AddComponent<ARInspectorUI>();root=new GameObject("Test content root");yield return null;typeof(ARStructure).GetMethod("OnAnchored",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(model,new object[]{root.transform});yield return null;}
    [UnityTearDown] public IEnumerator Cleanup(){Object.Destroy(app);Object.Destroy(root);yield return null;}
    [UnityTest] public IEnumerator CompleteGeometryAndMetadata(){Assert.That(model.Elements.Count,Is.EqualTo(628));int walls=0;foreach(var tag in model.Elements){Assert.That(tag.transform.IsChildOf(root.transform),Is.True);Assert.That(tag.element.type,Is.Not.EqualTo("rigido"));Assert.IsNotNull(tag.GetComponent<BoxCollider>());if(tag.wall!=null){walls++;Assert.That(tag.mapping.analyticalId,Is.EqualTo(tag.element.id));}}Assert.That(walls,Is.EqualTo(91));yield return null;}
    [UnityTest] public IEnumerator RepeatedSelectionPanelCaseFilterAndIsolation(){var a=model.Elements.Find(t=>t.element.id==243);var b=model.Elements.Find(t=>t.element.id==618);var material=a.GetComponent<Renderer>().sharedMaterial;selection.Select(a);selection.Select(b);Assert.That(a.GetComponent<Renderer>().sharedMaterial,Is.EqualTo(material));Assert.That(ui.SelectedTag,Is.EqualTo("W_MURO-013"));ui.SetCase("EY");Assert.That(ui.ActiveCase,Is.EqualTo("EY"));selection.Clear();Assert.IsNull(ui.SelectedTag);selection.Select(a);selection.Isolate();Assert.That(model.VisibleElements().Count,Is.EqualTo(1));selection.ShowAll();Assert.That(model.VisibleElements().Count,Is.EqualTo(628));model.ShowColumns=false;model.ApplyVisibility();Assert.IsFalse(a.gameObject.activeInHierarchy);Assert.IsNull(selection.Selected);model.ShowColumns=true;model.ApplyVisibility();Assert.IsTrue(a.gameObject.activeInHierarchy);yield return null;}
    [UnityTest] public IEnumerator ReanchorRebuildClearsSelection(){selection.Select(model.Elements[0]);model.Rebuild();Assert.IsNull(selection.Selected);Assert.That(model.Elements.Count,Is.EqualTo(628));yield return null;Assert.That(root.transform.childCount,Is.EqualTo(1));}
    [UnityTest] public IEnumerator PanelHitTesting(){var safe=Screen.safeArea;Assert.IsTrue(ARInspectorUI.BlocksScreenPoint(new Vector2(safe.x+safe.width*.5f,safe.yMax-20)));selection.Clear();yield return null;Assert.IsFalse(ARInspectorUI.BlocksScreenPoint(new Vector2(safe.x+safe.width*.5f,safe.y+safe.height*.5f)));}
    [UnityTest] public IEnumerator MissingPartialAndFailedCaseDoNotFabricateForces(){
        var a=model.Elements.Find(t=>t.element.id==243);selection.Select(a);ui.SetCase("C1");
        var data=JsonUtility.FromJson<StructureData>(Resources.Load<TextAsset>("estructura_p1l4_unity").text);
        data.p1l4.elementForces=System.Array.FindAll(data.p1l4.elementForces,r=>r.combo!="C1"||r.id!=243);UnityData.LoadData(data);yield return null;
        Assert.IsNull(typeof(ARInspectorUI).GetField("cutI",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(ui));
        Assert.That(typeof(ARInspectorUI).GetField("availability",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(ui),Is.EqualTo(ResultAvailability.Missing));
        data=JsonUtility.FromJson<StructureData>(Resources.Load<TextAsset>("estructura_p1l4_unity").text);
        System.Array.Find(data.p1l4.elementForces,r=>r.combo=="C1"&&r.id==243).f=new float[3];UnityData.LoadData(data);yield return null;
        Assert.That(typeof(ARInspectorUI).GetField("availability",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(ui),Is.EqualTo(ResultAvailability.Partial));
        System.Array.Find(data.p1l4.caseStates,c=>c.name=="C1").ok=false;UnityData.LoadData(data);yield return null;
        Assert.That(typeof(ARInspectorUI).GetField("availability",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(ui),Is.EqualTo(ResultAvailability.Invalid));
    }
}
