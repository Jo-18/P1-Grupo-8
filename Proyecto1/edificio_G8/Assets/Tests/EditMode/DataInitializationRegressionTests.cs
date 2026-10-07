using System;
using NUnit.Framework;
using UnityEngine;

public class DataInitializationRegressionTests
{
    [Test] public void NullDatasetFailsExplicitlyWithoutReplacingValidState()
    {
        var data = JsonUtility.FromJson<StructureData>(Resources.Load<TextAsset>("estructura_p1l4_unity").text);
        UnityData.LoadData(data);
        var repository = UnityData.Repository;
        Assert.Throws<ArgumentNullException>(() => UnityData.LoadData(null));
        Assert.AreSame(data, UnityData.Structure);
        Assert.AreSame(repository, UnityData.Repository);
    }

    [Test] public void EmptyJsonIsNotAStructuralDataset()
    {
        Assert.IsNull(JsonUtility.FromJson<StructureData>(string.Empty));
        var asset = Resources.Load<TextAsset>("estructura_p1l4_unity");
        Assert.IsNotNull(asset);
        Assert.That(asset.text.Length, Is.GreaterThan(0));
        Assert.IsNotNull(JsonUtility.FromJson<StructureData>(asset.text));
    }
}
