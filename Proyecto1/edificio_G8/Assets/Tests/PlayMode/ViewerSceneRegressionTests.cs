#if UNITY_EDITOR
using System.Collections;
using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

public class ViewerSceneRegressionTests
{
    [UnityTest] public IEnumerator DesktopSceneRetainsGeometrySelectionCasesAndPanels()
    {
        yield return EditorSceneManager.LoadSceneAsyncInPlayMode("Assets/Scenes/StructureViewerScene.unity", new LoadSceneParameters(LoadSceneMode.Single));
        yield return null;
        var viewer = Object.FindAnyObjectByType<StructureViewer>();
        Assert.IsNotNull(viewer);
        Assert.That(viewer.GetComponentsInChildren<ElementSelectable>(true).Length, Is.EqualTo(628));
        Assert.IsNotNull(viewer.Diagrams);
        Assert.IsNotNull(Object.FindAnyObjectByType<PMPanel>());
        Assert.IsNotNull(Object.FindAnyObjectByType<ViewerUI>());
        Assert.That(viewer.ComboNames.Length, Is.EqualTo(3));
        foreach (string name in new[] { "G", "Q", "EX", "EY", "C1", "C2", "C3" })
        {
            viewer.SetCase(name);
            Assert.That(UnityData.ActiveCombo, Is.EqualTo(name));
        }
        viewer.Search("E1_243");
        var picker = Object.FindAnyObjectByType<ElementPicker>();
        Assert.IsNotNull(picker.Selected);
        Assert.That(picker.Selected.data.id, Is.EqualTo(243));
        foreach (string result in new[] { "Axial", "Corte", "Momento", "Deformada", "None" })
        {
            viewer.SetResult(result);
            yield return null;
        }
        viewer.StructureOnly();
        yield return null;
        viewer.ShowAllLayers();
        picker.ClearSelection();
        yield return null;
        Assert.IsNull(picker.Selected);
        // Test Runner automatically fails on unexpected errors/exceptions.
        // The desktop deliberately logs geometry and diagram diagnostics.
    }
}
#endif
