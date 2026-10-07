using System;
using NUnit.Framework;
using UnityEngine;
public class Fix03H5SelectionTests {
    StructuralRepository repo;HonorsCapacityCatalog catalog;
    [OneTimeSetUp] public void Setup(){repo=new StructuralRepository(HonorsCapacitySession.Validate(Resources.Load<TextAsset>("estructura_p1l4_unity").text));catalog=HonorsCapacityCatalog.Load();}
    HonorsCapacityContext Resolve(int id,string c="C2")=>catalog.Resolve(repo,repo.Elements[id],c);
    [Test] public void CertifiedReferenceStillMatches(){
        var c=Resolve(287);Assert.That(c.Header,Does.Contain("E1_287"));Assert.IsTrue(c.ComparisonAvailable);Assert.AreEqual(287,c.Element.id);
        Assert.AreEqual("COL70/70_16f28",c.BaseCurve.sectionId);Assert.AreEqual("COL70/70_20f28",c.AfterCurve.sectionId);Assert.AreEqual(612.9f,c.Demand.x);Assert.AreEqual(502.1f,c.Demand.y);
        Assert.AreEqual(.409f,c.BaseCombo.DCR_PM);Assert.AreEqual(.343f,c.AfterCombo.DCR_PM);Assert.AreEqual(1462.6f,c.AfterCombo.phiMn_at_Pu);
    }
    [Test] public void Selection301UsesExceptionAndNever287Fallback(){
        var c=Resolve(301);Assert.That(c.Header,Does.Contain("E1_301"));Assert.AreEqual(301,c.Element.id);Assert.AreEqual("COL70/70",c.Element.sectionId);
        Assert.AreEqual("COL70/70_4f28+16f36",c.BaseCurve.sectionId);Assert.AreEqual("4φ28+16φ36",c.BaseCapacity.armadura.barras);
        Assert.AreEqual(1421.8f,c.Demand.x);Assert.AreEqual(149.8f,c.Demand.y);Assert.AreEqual(.07f,c.BaseCombo.DCR_PM);
        Assert.IsFalse(c.ComparisonAvailable);Assert.IsNull(c.AfterCombo);Assert.That(c.Status,Does.Contain("no disponible"));Assert.That(c.Details,Does.Not.Contain("E1_287"));
    }
    [Test] public void SharedCurveDoesNotShareDemand(){
        var a=Resolve(287);var b=Resolve(288);Assert.IsTrue(b.ComparisonAvailable);Assert.AreSame(a.BaseCurve,b.BaseCurve);Assert.AreSame(a.AfterCurve,b.AfterCurve);
        Assert.AreNotEqual(a.Demand,b.Demand);Assert.AreEqual(403.3f,b.Demand.x);Assert.AreEqual(.033f,b.BaseCombo.DCR_PM);Assert.AreEqual(b.BaseCombo.Pu,b.AfterCombo.Pu);
    }
    [TestCase("G")][TestCase("Q")][TestCase("EX")][TestCase("EY")][TestCase("C1")][TestCase("C2")][TestCase("C3")]
    public void ActiveCaseNeverSilentlyBecomesC2(string name){
        var c=Resolve(287,name);Assert.AreEqual(name,c.CaseId);Assert.IsTrue(c.HasDemand);
        var sampler=new StructuralResultSampler(repo);Assert.IsTrue(sampler.TryPM(c.Element,name,out var raw));
        Assert.AreEqual(raw.x,c.Demand.x,.1);Assert.AreEqual(raw.y,c.Demand.y,.1);
        if(name.StartsWith("C")){Assert.AreEqual(name,c.BaseCombo.combo);Assert.AreEqual(name,c.AfterCombo.combo);}
        else{Assert.IsNull(c.BaseCombo);Assert.IsNull(c.AfterCombo);Assert.That(c.Status,Does.Contain("no publicados"));}
    }
    [Test] public void NoneUnknownBeamBraceWallDoNotFallback(){
        Assert.IsNull(catalog.Resolve(repo,null,"C2").Element);
        var unknown=new ElementData{id=-1,elementTag="Unknown"};Assert.IsNull(catalog.Resolve(repo,unknown,"C2").BaseCurve);
        foreach(var type in new[]{"viga","arriostre","muro"}){
            var e=Array.Find(repo.Data.elements,x=>x.type==type);Assert.IsNotNull(e);var c=catalog.Resolve(repo,e,"C2");Assert.IsFalse(c.HasDemand);Assert.IsNull(c.AfterCurve);Assert.That(c.Details,Does.Not.Contain("E1_287"));
        }
    }
    [Test] public void SwitchingContextsCannotRetainPreviousReference(){
        foreach(int id in new[]{287,301,243,288,287}){var c=Resolve(id);Assert.AreEqual(id,c.Element.id);Assert.That(c.Header,Does.Contain(c.Element.elementTag));Assert.AreEqual(c.Element.capacidad.ForCombo("C2").Pu,c.Demand.x);}
    }
    [Test] public void IncompatibleCatalogSectionIsNotApplied(){
        var copy=JsonUtility.FromJson<HonorsCapacityCatalog.Bundle>(Resources.Load<TextAsset>("Honors/H5/catalog").text);copy.scenarios[0].sectionId="wrong";
        var c=new HonorsCapacityCatalog(copy).Resolve(repo,repo.Elements[287],"C2");Assert.IsFalse(c.ComparisonAvailable);Assert.IsNotNull(c.BaseCurve);
    }
    [Test] public void PlotFitContainsBothCurvesAndSelectedDemand(){
        var c=Resolve(287);var bounds=HonorsCapacityPlot.Bounds(c.BaseCurve,c.AfterCurve,c.Demand);var r=new Rect(6,6,787,487);
        foreach(var curve in new[]{c.BaseCurve,c.AfterCurve})foreach(var p in ARPlotGeometry.PMPoints(curve))Assert.IsTrue(r.Contains(bounds.Map(p,r)));
        Assert.IsTrue(r.Contains(bounds.Map(new Vector2(c.Demand.y,c.Demand.x),r)));
    }
}
