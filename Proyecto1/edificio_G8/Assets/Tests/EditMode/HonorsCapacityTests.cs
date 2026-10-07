using System;
using NUnit.Framework;
using UnityEngine;
public class HonorsCapacityTests {
    [Test] public void FlagsDefaultOffAndSaveForbidden(){var go=new GameObject();try{var c=go.AddComponent<HonorsConfiguration>();Assert.IsFalse(c.H5CapacityComparison||c.H2ProfilesAndQA||c.H3SpatialDiagrams);Assert.Throws<InvalidOperationException>(()=>new HonorsCapacitySession().SaveAsCurrent());}finally{UnityEngine.Object.DestroyImmediate(go);}}
    [Test] public void CertifiedComparisonContractCurveAndDemand(){
        var b=HonorsCapacitySession.Validate(Resources.Load<TextAsset>("estructura_p1l4_unity").text);
        var a=HonorsCapacitySession.Validate(Resources.Load<TextAsset>("Honors/H5/after").text);
        HonorsCapacitySession.AssertDemandInvariant(b,a);
        var eb=Array.Find(b.elements,x=>x.id==287);var ea=Array.Find(a.elements,x=>x.id==287);
        Assert.That(ea.pmCurveId,Is.EqualTo("COL70/70_20f28"));Assert.Less(ea.capacidad.DCR,eb.capacidad.DCR);
        Assert.That(ea.capacidad.ForCombo("C2").Pu,Is.EqualTo(eb.capacidad.ForCombo("C2").Pu));
        a.p1l4.elementForces[0].f[0]+=1;Assert.Throws<ArgumentException>(()=>HonorsCapacitySession.AssertDemandInvariant(b,a));
        a=HonorsCapacitySession.Validate(Resources.Load<TextAsset>("Honors/H5/after").text);a.nodes[0].x+=1;Assert.Throws<ArgumentException>(()=>HonorsCapacitySession.AssertDemandInvariant(b,a));
    }
}
