#if UNITY_EDITOR
using System;
using System.Collections;
using System.Reflection;
using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
using UnityEngine.XR.ARFoundation;
public class HonorsSceneTests {
    [UnityTest] public IEnumerator HonorsSceneSyntheticGeometryCertifiedH5AndFlagsOff(){
        yield return EditorSceneManager.LoadSceneAsyncInPlayMode("Assets/Scenes/ARHonorsScene.unity",new LoadSceneParameters(LoadSceneMode.Single));yield return null;
        var config=HonorsConfiguration.Current;Assert.IsTrue(config.H5CapacityComparison&&config.H2ProfilesAndQA);Assert.IsFalse(config.H3SpatialDiagrams);
        Assert.That(UnityEngine.Object.FindAnyObjectByType<ARTrackedImageManager>().referenceLibrary.count,Is.EqualTo(2));
        var model=ARStructure.Instance;var root=new GameObject("Synthetic_Honors_control_root");typeof(ARStructure).GetMethod("OnAnchored",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(model,new object[]{root.transform});yield return null;
        Assert.That(model.Elements.Count,Is.EqualTo(628));var select=model.GetComponent<StructuralSelectionController>();select.Select(model.Elements.Find(t=>t.element.id==287));Assert.That(select.Selected.element.id,Is.EqualTo(287));
        var session=new HonorsCapacitySession();Assert.IsTrue(session.LoadCertifiedScenario(null),session.Message);yield return null;Assert.That(Array.Find(UnityData.Structure.elements,e=>e.id==287).pmCurveId,Is.EqualTo("COL70/70_20f28"));session.Discard(null);yield return null;Assert.That(Array.Find(UnityData.Structure.elements,e=>e.id==287).pmCurveId,Is.EqualTo("COL70/70_16f28"));
        config.H5CapacityComparison=config.H2ProfilesAndQA=false;yield return null;model.SetMode(ARStructure.Mode.Maqueta100);model.Rebuild();yield return null;Assert.That(model.Elements.Count,Is.EqualTo(628));Assert.IsNull(select.Selected);Assert.That(root.transform.childCount,Is.EqualTo(1));UnityEngine.Object.Destroy(root);session.Dispose();yield return null;
    }
}
#endif
