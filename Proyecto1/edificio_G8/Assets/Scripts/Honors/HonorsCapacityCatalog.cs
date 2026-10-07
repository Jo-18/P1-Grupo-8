using System;
using UnityEngine;
/// Offline section curves + per-element/combo capacity, bound to the frozen solver dataset.
public sealed class HonorsCapacityCatalog {
    [Serializable] public sealed class Bundle {public string schema,baseSHA256,afterSHA256,certificateSHA256,reinforcementSHA256,limitation;public Scenario[] scenarios;public PMCurveData[] curves;public Entry[] elements;}
    [Serializable] public sealed class Scenario {public string id,sectionId,baseCurveId,afterCurveId,reference,provenance;public ArmaduraData beforeArm,afterArm;public CapacityData afterCapacity;}
    [Serializable] public sealed class Entry {public int id;public string elementTag,sectionId,baseCurveId,reinforcementSource,scenarioId;public ArmaduraData baseArm;public CapacityData beforeCapacity;public CapacityCombo[] afterCombos;}
    [Serializable] sealed class Manifest {public string catalogSHA256;}
    public readonly Bundle Data;
    public HonorsCapacityCatalog(Bundle data){Data=data??throw new ArgumentNullException(nameof(data));if(data.schema!="mcoc.honors.h5-catalog/1")throw new ArgumentException("Catálogo H5 inválido");}
    static HonorsCapacityCatalog cached;
    static string Hash(byte[] bytes){using(var sha=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
    public static HonorsCapacityCatalog Load(){
        if(cached!=null)return cached;
        var resource=Resources.Load<TextAsset>("Honors/H5/catalog");var manifest=Resources.Load<TextAsset>("Honors/H5/catalog_manifest");var baseline=Resources.Load<TextAsset>("estructura_p1l4_unity");
        if(resource==null||manifest==null||baseline==null)throw new ArgumentException("Catálogo offline H5 no disponible");
        var m=JsonUtility.FromJson<Manifest>(manifest.text);if(Hash(resource.bytes)!=m.catalogSHA256)throw new ArgumentException("SHA256 catálogo H5 inválido");
        var data=JsonUtility.FromJson<Bundle>(resource.text);if(Hash(baseline.bytes)!=data.baseSHA256)throw new ArgumentException("Catálogo H5 de otro dataset");
        cached=new HonorsCapacityCatalog(data);return cached;
    }
    public Entry Find(int id,string tag)=>Array.Find(Data.elements??Array.Empty<Entry>(),e=>e.id==id&&e.elementTag==tag);
    public Scenario FindScenario(string id)=>string.IsNullOrEmpty(id)?null:Array.Find(Data.scenarios??Array.Empty<Scenario>(),s=>s.id==id);
    public PMCurveData Curve(string id)=>Array.Find(Data.curves??Array.Empty<PMCurveData>(),c=>c.sectionId==id);
    public static bool SameArm(ArmaduraData a,ArmaduraData b)=>a!=null&&b!=null&&a.barras==b.barras&&a.estribos==b.estribos;
    static bool SameCurve(PMCurveData a,PMCurveData b){
        if(a?.points==null||b?.points==null||a.sectionId!=b.sectionId||a.b_m!=b.b_m||a.h_m!=b.h_m||a.fc_MPa!=b.fc_MPa||a.fy_MPa!=b.fy_MPa||a.points.Length!=b.points.Length)return false;
        for(int i=0;i<a.points.Length;i++)if(a.points[i].P_kN!=b.points[i].P_kN||a.points[i].M_kN_m!=b.points[i].M_kN_m)return false;return true;
    }
    public HonorsCapacityContext Resolve(StructuralRepository repo,ElementData selected,string caseId){
        var c=new HonorsCapacityContext{CaseId=caseId,Element=selected};
        if(selected==null){c.Status="Selecciona un elemento para H5.";return c;}
        if(repo==null||!repo.ContractValid||!repo.Elements.TryGetValue(selected.id,out var e)||e.elementTag!=selected.elementTag){c.Status="Datos del seleccionado no disponibles.";return c;}
        c.Element=e;c.BaseCapacity=e.capacidad;
        if(e.type!="columna"){c.Status="Curva P-M no disponible para este tipo de elemento en H5.";return c;}
        c.BaseCurve=repo.Curve(e.pmCurveId);
        if(c.BaseCurve==null){c.Status="Curva P-M no disponible para este elemento.";return c;}
        var sampler=new StructuralResultSampler(repo);c.HasDemand=sampler.TryPM(e,caseId,out c.Demand);
        if(c.HasDemand){
            var published=e.capacidad?.ForCombo(caseId);
            // Published rounding preserved. Never borrow a combo or a demand from another element.
            if(published!=null&&Mathf.Abs(published.Pu-c.Demand.x)<=.1f&&Mathf.Abs(published.Mu-c.Demand.y)<=.1f){c.BaseCombo=published;c.Demand=new Vector2(published.Pu,published.Mu);}
        }
        var entry=Find(e.id,e.elementTag);c.ReinforcementSource=entry?.reinforcementSource??"Metadata del dataset";
        var scenario=FindScenario(entry?.scenarioId);
        bool compatible=entry!=null&&scenario!=null&&entry.sectionId==e.sectionId&&entry.baseCurveId==e.pmCurveId&&scenario.sectionId==e.sectionId&&scenario.baseCurveId==e.pmCurveId
            &&SameArm(e.capacidad?.armadura,entry.baseArm)&&SameArm(entry.baseArm,scenario.beforeArm)&&SameCurve(c.BaseCurve,Curve(entry.baseCurveId));
        if(!compatible){c.Status="Comparación Honors before/after no disponible para este elemento.";return c;}
        // Reject a locally modified capacity/demand before associating certified after values.
        if(c.BaseCombo!=null){
            var expected=entry.beforeCapacity?.ForCombo(caseId);
            if(expected==null||expected.Pu!=c.BaseCombo.Pu||expected.Mu!=c.BaseCombo.Mu||expected.DCR_PM!=c.BaseCombo.DCR_PM||expected.phiMn_at_Pu!=c.BaseCombo.phiMn_at_Pu){c.Status="Comparación no disponible: demanda/capacidad fuera del catálogo certificado.";return c;}
        }
        var after=Curve(scenario.afterCurveId);
        if(after==null){c.Status="Comparación no disponible: curva Honors ausente.";return c;}
        c.Scenario=scenario;c.AfterCurve=after;c.AfterCapacity=scenario.afterCapacity;
        if(c.BaseCombo!=null){
            var ac=Array.Find(entry.afterCombos??Array.Empty<CapacityCombo>(),r=>r.combo==caseId);
            if(ac!=null&&ac.Pu==c.BaseCombo.Pu&&ac.Mu==c.BaseCombo.Mu)c.AfterCombo=ac;
        }
        c.Status=c.HasDemand?(c.BaseCombo!=null&&c.AfterCombo!=null?"Comparación del elemento/caso seleccionado disponible.":"Curvas disponibles; Mcap/DCR no publicados para el caso activo (sólo C1/C2/C3)."):"Demanda no disponible para el caso activo.";
        return c;
    }
}
public sealed class HonorsCapacityContext {
    public ElementData Element;public string CaseId,Status,ReinforcementSource;
    public PMCurveData BaseCurve,AfterCurve;public CapacityData BaseCapacity,AfterCapacity;
    public CapacityCombo BaseCombo,AfterCombo;public HonorsCapacityCatalog.Scenario Scenario;
    public Vector2 Demand;public bool HasDemand;
    public bool ComparisonAvailable=>Scenario!=null&&AfterCurve!=null;
    public string Header=>"H5 · "+(Element?.elementTag??"Sin selección")+" · "+(Element?.sectionId??"")+" · "+Bars(BaseCapacity?.armadura)+(ComparisonAvailable?" → "+Bars(Scenario.afterArm):"");
    public static string Bars(ArmaduraData a)=>string.IsNullOrEmpty(a?.barras)?"Armadura no disponible":a.barras.Replace("f","φ");
    public string Details=>Element==null?Status:$"Elemento: {Element.elementTag}\nOpenSees eleTag: {Element.id}\nCaso activo: {CaseId}\nSección: {Element.sectionId}\nArmadura base: {Bars(BaseCapacity?.armadura)} / {BaseCapacity?.armadura?.estribos}\nOrigen armadura: {ReinforcementSource}\nCurva base: {BaseCurve?.sectionId??"No disponible"}\nEscenario Honors: {Scenario?.id??"No disponible"}\n"+(HasDemand?$"Pu {Demand.x:0.0} kN · Mu {Demand.y:0.0} kN·m":"Demanda no disponible.")+"\n"+Status;
}
