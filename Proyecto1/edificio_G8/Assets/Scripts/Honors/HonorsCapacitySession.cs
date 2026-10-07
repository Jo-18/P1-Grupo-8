using System;
using System.IO;
using UnityEngine;
/// Explicit certified-reference capacity adapter. Selection-driven UI uses HonorsCapacityCatalog; this API retains the reproducible reference flow.
public sealed class HonorsCapacitySession : IDisposable {
    public readonly PythonJob Job=new PythonJob();
    public string Message {get;private set;}="Referencia certificada H5: E1_287/C2; escenario académico 16φ28 → 20φ28";
    public bool Applied {get;private set;}
    public StructureData Before {get;private set;}
    public StructureData After {get;private set;}
    string originalJson; bool loading;
    public static StructureData Validate(string json) {
        var d=JsonUtility.FromJson<StructureData>(json);var repo=new StructuralRepository(d);
        if(!repo.ContractValid)throw new ArgumentException(string.Join("; ",repo.Errors));
        foreach(var e in d.elements)if(!string.IsNullOrEmpty(e.pmCurveId) && repo.Curve(e.pmCurveId)==null)throw new ArgumentException("Asociacion P-M inválida");
        return d;
    }
    public bool Start(StructureViewer viewer) {
        if(!HonorsConfiguration.H5 || Job.Running)return false;
        try {
            if(viewer==null || Applied)throw new InvalidOperationException("Restaurar antes de iniciar otro escenario");
            var input=StructureViewer.ProjectJsonPath;originalJson=File.ReadAllText(input);Before=Validate(originalJson);
            var dir=Path.Combine(HonorsPaths.Evidence,"sesiones_H5",Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);
            var source=Path.Combine(dir,"input.json");File.WriteAllText(source,originalJson);
            var arm=Path.Combine(dir,"override.json");File.WriteAllText(arm,"{\"secciones\":{\"COL70/70\":{\"barras\":\"20f28\"}},\"elementos\":{}}",new System.Text.UTF8Encoding(false));
            loading=Job.Start("honors_comparar_armadura.py","--json \""+source+"\" --armaduras \""+arm+"\"",Path.Combine(dir,"result.json"));
            Message=loading?"Regenerando capacidad; demandas OpenSees conservadas":Job.Error;return loading;
        }catch(Exception ex){Message=ex.Message;return false;}
    }
    public bool Poll(StructureViewer viewer) {
        if(!loading||!Job.Poll(300))return false;loading=false;
        if(Job.Error!=null){Message=Job.Error;return false;}
        return Apply(File.ReadAllText(Job.OutputPath),viewer);
    }
    public bool Apply(string json,StructureViewer viewer) {
        try {
            var next=Validate(json);
            if(Before==null){Before=viewer!=null?viewer.Data:UnityData.Structure;originalJson=JsonUtility.ToJson(Before);}
            // The wrapper has validated byte-equivalent demand fields. Check them again before adopting a scenario.
            AssertDemandInvariant(Before,next);
            After=next;
            if(viewer!=null)viewer.ReloadFromJson(json,"Honors H5 / temporal / no guardado");else{UnityData.LoadData(next);ARStructure.Instance?.Rebuild();}
            Applied=true;Message="20φ28 aplicado. Capacidad de sección; rigidez y demandas invariantes.";return true;
        }catch(Exception ex){Message="ERROR H5: "+ex.Message;return false;}
    }
    [Serializable] class Demands {public ElementForceRecord[] forces;public DisplacementRecord[] displacements;public ReactionRecord[] reactions;public CaseState[] states;public AppliedLoad[] loads;public ComboInfo[] combinations;public WallMapping[] mappings;}
    [Serializable] class Geometry {public NodeData[] nodes;public ElementData[] elements;public WallData[] walls;}
    static string GeometryJson(StructureData d){var copy=JsonUtility.FromJson<Geometry>(JsonUtility.ToJson(new Geometry{nodes=d.nodes,elements=d.elements,walls=d.walls}));foreach(var e in copy.elements){e.capacidad=null;e.pmCurveId=null;}return JsonUtility.ToJson(copy);}
    static string DemandJson(StructureData d)=>JsonUtility.ToJson(new Demands{forces=d.p1l4.elementForces,displacements=d.p1l4.displacements,reactions=d.p1l4.reactions,states=d.p1l4.caseStates,loads=d.p1l4.appliedLoads,combinations=d.p1l4.combinations,mappings=d.p1l4.wallMappings});
    public static void AssertDemandInvariant(StructureData before,StructureData after){if(DemandJson(before)!=DemandJson(after)||GeometryJson(before)!=GeometryJson(after))throw new ArgumentException("El escenario cambio geometria/demandas; rechazado");}
    public bool LoadCertifiedScenario(StructureViewer viewer) {
        var a=Resources.Load<TextAsset>("Honors/H5/after");var m=Resources.Load<TextAsset>("Honors/H5/certified");
        if(a==null||m==null){Message="Falta escenario certificado";return false;}
        var c=JsonUtility.FromJson<Certificate>(m.text);
        using(var sha=System.Security.Cryptography.SHA256.Create())if(BitConverter.ToString(sha.ComputeHash(a.bytes)).Replace("-","").ToLowerInvariant()!=c.afterSHA256){Message="SHA256 H5 inválido";return false;}
        return Apply(a.text,viewer);
    }
    [Serializable] class Certificate {public string afterSHA256;}
    public void Discard(StructureViewer viewer) {
        Job.Kill();loading=false;
        if(originalJson!=null){if(viewer!=null)viewer.ReloadFromJson(originalJson,"Honors / snapshot restaurado");else{UnityData.LoadData(Validate(originalJson));ARStructure.Instance?.Rebuild();}}
        Applied=false;After=null;Message="Snapshot base restaurado; sin escritura en Resources/data";
    }
    public void SaveAsCurrent()=>HonorsPaths.RejectSavingBaseline();
    public void Dispose(){Job.Kill();}
}
