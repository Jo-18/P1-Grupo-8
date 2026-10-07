using System;
using System.Collections.Generic;
using UnityEngine;
/// Immutable indexes for the packaged dataset. No fallback to legacy moments or loads.
public sealed class StructuralRepository {
    public const string MissingText="No disponible en los datos exportados";
    public readonly StructureData Data;
    public readonly Dictionary<int,NodeData> Nodes=new Dictionary<int,NodeData>();
    public readonly Dictionary<int,ElementData> Elements=new Dictionary<int,ElementData>();
    public readonly Dictionary<int,WallMapping> Walls=new Dictionary<int,WallMapping>();
    public readonly List<string> Cases=new List<string>();
    public readonly List<string> Errors=new List<string>();
    readonly Dictionary<string,ElementForceRecord> forces=new Dictionary<string,ElementForceRecord>();
    readonly Dictionary<string,DisplacementRecord> displacements=new Dictionary<string,DisplacementRecord>();
    readonly Dictionary<string,ReactionRecord> reactions=new Dictionary<string,ReactionRecord>();
    readonly Dictionary<string,CaseState> states=new Dictionary<string,CaseState>();
    readonly Dictionary<string,AppliedLoad> prescribed=new Dictionary<string,AppliedLoad>();
    public bool ContractValid => Errors.Count==0;
    static string Key(string c,int id)=>c+":"+id;
    public static bool Finite(float f)=>!float.IsNaN(f)&&!float.IsInfinity(f);
    public StructuralRepository(StructureData data) {
        Data=data;
        if(data==null){Errors.Add("Dataset ausente");return;}
        if(data.schemaVersion!="mcoc.ar/2.0" || data.resultUnits==null || data.resultUnits.length!="m" || data.resultUnits.force!="kN" || data.resultUnits.moment!="kN*m" || data.resultUnits.displacement!="m" || data.resultUnits.rotation!="rad") Errors.Add("Contrato/unidades inválidos");
        if(data.corrida==null || data.corrida.motor!="OpenSees" || string.IsNullOrEmpty(data.corrida.opensees) || string.IsNullOrEmpty(data.corrida.openseespy) || string.IsNullOrEmpty(data.corrida.fecha) || data.corrida.entradas_sha256==null || string.IsNullOrEmpty(data.corrida.entradas_sha256.modelo) || string.IsNullOrEmpty(data.corrida.entradas_sha256.parametros) || string.IsNullOrEmpty(data.corrida.entradas_sha256.combinaciones) || string.IsNullOrEmpty(data.corrida.entradas_sha256.armaduras))Errors.Add("Procedencia oficial incompleta");
        if(data.conventions==null || data.conventions.forces!="element-local" || data.conventions.sectionI!="-fI" || data.conventions.sectionJ!="+fJ")Errors.Add("Convenciones inválidas");
        var tags=new HashSet<string>();
        foreach(var n in data.nodes??Array.Empty<NodeData>()) {
            if(n==null||Nodes.ContainsKey(n.id)||!Finite(n.x)||!Finite(n.y)||!Finite(n.z))Errors.Add("Nodo inválido/duplicado");else Nodes.Add(n.id,n);
        }
        foreach(var e in data.elements??Array.Empty<ElementData>()) {
            if(e==null||Elements.ContainsKey(e.id)||string.IsNullOrEmpty(e.elementTag)||!tags.Add(e.elementTag)||!Nodes.ContainsKey(e.nodeI)||!Nodes.ContainsKey(e.nodeJ))Errors.Add("Elemento inválido/duplicado");else Elements.Add(e.id,e);
        }
        var p=data.p1l4;
        if(p==null){Errors.Add("Resultados ausentes");return;}
        foreach(var s in p.caseStates??Array.Empty<CaseState>()) {
            if(s==null||string.IsNullOrEmpty(s.name)||states.ContainsKey(s.name))Errors.Add("Caso duplicado/inválido");else {states.Add(s.name,s);Cases.Add(s.name);}
        }
        if(Cases.Count==0)Errors.Add("Casos ausentes");
        foreach(var f in p.elementForces??Array.Empty<ElementForceRecord>()) {
            if(f==null||string.IsNullOrEmpty(f.combo)||!states.ContainsKey(f.combo)||!Elements.ContainsKey(f.id)) {Errors.Add("Fuerza sin caso/geometría");continue;}
            var k=Key(f.combo,f.id);if(forces.ContainsKey(k))Errors.Add("Fuerza duplicada");else forces.Add(k,f);
        }
        foreach(var d in p.displacements??Array.Empty<DisplacementRecord>()) {
            if(d==null||string.IsNullOrEmpty(d.combo)||!states.ContainsKey(d.combo)||!Nodes.ContainsKey(d.node)){Errors.Add("Desplazamiento sin caso/geometría");continue;}
            var k=Key(d.combo,d.node);if(displacements.ContainsKey(k))Errors.Add("Desplazamiento duplicado");else displacements.Add(k,d);
        }
        foreach(var r in p.reactions??Array.Empty<ReactionRecord>()) {
            if(r==null||!states.ContainsKey(r.combo??"")||!Nodes.ContainsKey(r.node)||r.f==null||r.f.Length!=6){Errors.Add("Reacción inválida");continue;}
            bool finite=true;foreach(float v in r.f)finite&=Finite(v);if(!finite){Errors.Add("Reacción no finita");continue;}
            var k=Key(r.combo,r.node);if(reactions.ContainsKey(k))Errors.Add("Reacción duplicada");else reactions.Add(k,r);
        }
        if(p.appliedLoads==null)Errors.Add("Cargas prescritas ausentes");
        foreach(var load in p.appliedLoads??Array.Empty<AppliedLoad>()) {
            if(load==null||load.values==null||load.values.Length!=3&&load.values.Length!=6||load.axes!="model-global"||load.kind!="nodeForce"&&load.kind!="elementUniformTotal"){Errors.Add("Carga inválida");continue;}
            bool finite=true;foreach(float v in load.values)finite&=Finite(v);
            if(!finite||!states.ContainsKey(load.combo??"")||!(load.kind=="nodeForce"?Nodes.ContainsKey(load.targetId):Elements.ContainsKey(load.targetId))){Errors.Add("Carga sin caso/geometría o no finita");continue;}
            string k=load.kind+":"+Key(load.combo,load.targetId);if(prescribed.ContainsKey(k))Errors.Add("Carga duplicada");else prescribed.Add(k,load);
        }
        foreach(var state in states.Values){int count=0;foreach(var load in prescribed.Values)if(load.combo==state.name)count++;if(count!=state.appliedLoadCount)Errors.Add("Cargas prescritas incompletas: "+state.name);}
        var visualWalls=new Dictionary<int,WallData>();
        foreach(var w in data.walls??Array.Empty<WallData>()){if(w==null||visualWalls.ContainsKey(w.id))Errors.Add("Muro visual duplicado/inválido");else visualWalls.Add(w.id,w);}
        var analyticalIds=new HashSet<int>();
        foreach(var m in p.wallMappings??Array.Empty<WallMapping>()) {
            if(m==null||Walls.ContainsKey(m.visualWallId)||!visualWalls.TryGetValue(m.visualWallId,out var w)||w.elementTag!=m.visualTag||w.nodeI!=m.visualNodeI||w.nodeJ!=m.visualNodeJ||!analyticalIds.Add(m.analyticalId)||!Elements.TryGetValue(m.analyticalId,out var e)||e.type!="muro"||e.wallIndex!=m.visualWallId||e.elementTag!=m.analyticalTag||e.nodeI!=m.analysisNodeI||e.nodeJ!=m.analysisNodeJ||!Nodes.ContainsKey(m.visualNodeI)||!Nodes.ContainsKey(m.visualNodeJ)||!Finite(m.topZ)||!Finite(m.bottomZ)||m.topZ<=m.bottomZ||m.wallInPlaneAxis!=e.wallInPlaneAxis)Errors.Add("Mapping de muro inválido");else Walls.Add(m.visualWallId,m);
        }
        if(Walls.Count!=(data.walls?.Length??0))Errors.Add("Mapping de muro incompleto");
    }
    ResultAvailability CaseAvailability(string c) {
        if(!ContractValid)return ResultAvailability.Invalid;
        if(!states.TryGetValue(c??"",out var s))return ResultAvailability.Missing;
        if(!s.ok)return ResultAvailability.Invalid;
        return Parse(s.state);
    }
    public static ResultAvailability Parse(string status) => Enum.TryParse(status,out ResultAvailability s)?s:ResultAvailability.Invalid;
    public bool TryForces(int id,string c,out float[] f,out ResultAvailability availability) {
        f=null;availability=CaseAvailability(c);if(availability!=ResultAvailability.Available)return false;
        if(!forces.TryGetValue(Key(c,id),out var r)){availability=ResultAvailability.Missing;return false;}
        availability=Parse(r.status);
        if(r.f==null){availability=ResultAvailability.Missing;return false;}
        if(r.f.Length!=12){availability=ResultAvailability.Partial;return false;}
        foreach(var v in r.f)if(!Finite(v)){availability=ResultAvailability.Invalid;return false;}
        if(availability!=ResultAvailability.Available)return false;f=r.f;return true;
    }
    public bool TryDisplacement(int id,string c,out DisplacementRecord d,out ResultAvailability a) {
        d=null;a=CaseAvailability(c);if(a!=ResultAvailability.Available)return false;
        if(!displacements.TryGetValue(Key(c,id),out var r)){a=ResultAvailability.Missing;return false;}
        a=Parse(r.status);if(!Finite(r.ux)||!Finite(r.uy)||!Finite(r.uz)||!Finite(r.rx)||!Finite(r.ry)||!Finite(r.rz))a=ResultAvailability.Invalid;
        if(a!=ResultAvailability.Available)return false;d=r;return true;
    }
    public bool TryReaction(int id,string c,out ReactionRecord r) {r=null;return CaseAvailability(c)==ResultAvailability.Available && reactions.TryGetValue(Key(c,id),out r)&&r.status=="Available"&&r.f!=null&&r.f.Length==6;}
    public Vector3 Point(int id) {var n=Nodes[id];return new Vector3(n.x,n.y,n.z);}
    public AppliedLoad Applied(string kind,int id,string c)=>prescribed.TryGetValue(kind+":"+Key(c,id),out var l)?l:null;
    public float Length(ElementData e)=>(Point(e.nodeJ)-Point(e.nodeI)).magnitude;
    public ComboInfo Combo(string c) {foreach(var v in Data.p1l4.combinations??Array.Empty<ComboInfo>())if(v.name==c)return v;return null;}
    public PMCurveData Curve(string id) {foreach(var c in Data.p1l4.pmCurves??Array.Empty<PMCurveData>())if(c.sectionId==id)return c;return null;}
    public WallRegistryEntry WallRegistry(int id){foreach(var w in Data.p1l4.wallRegistry??Array.Empty<WallRegistryEntry>())if(w.index==id)return w;return null;}
}
