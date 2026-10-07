using UnityEngine;
// One selection; event-driven geometry. Rendering carries no structural solver.
public sealed class ARStructuralDiagramOverlay : MonoBehaviour {
    public Transform OverlayRoot {get;private set;}
    public LineRenderer Curve {get;private set;}
    public StructuralResultSampler.Diagram Diagram {get;private set;}
    public string Description {get;private set;}="H3: selecciona una barra y activa My/Vz.";
    public int Component {get;private set;}=4;
    public float GainMy=.005f,GainVz=.02f;
    public float Gain=>Component==4?GainMy:GainVz;
    public int GeometryUpdates {get;private set;}
    ARStructure structure;StructuralSelectionController selection;ARInspectorUI ui;HonorsConfiguration config;
    StructuralRepository cachedRepo;StructuralResultSampler sampler;bool showing,lastFlag;
    Material curveMaterial,baseMaterial;
    void Start(){
        structure=GetComponent<ARStructure>();selection=GetComponent<StructuralSelectionController>();ui=GetComponent<ARInspectorUI>();config=GetComponent<HonorsConfiguration>();
        if(selection!=null)selection.Changed+=Invalidate;
        if(structure!=null)structure.Rebuilt+=Invalidate;
        if(ui!=null)ui.CaseChanged+=Invalidate;
    }
    void Update(){bool flag=config!=null&&config.H3SpatialDiagrams;if(lastFlag!=flag){lastFlag=flag;Invalidate();}} // flag watch only; no per-frame sampling
    public void Show(int component){
        if(component!=2&&component!=4)return;
        if(config==null)config=GetComponent<HonorsConfiguration>();if(config==null)return;
        Component=component;config.H3SpatialDiagrams=true;showing=true;lastFlag=true;Invalidate();
    }
    public void Hide(){showing=false;if(config!=null)config.H3SpatialDiagrams=false;lastFlag=false;Clear();Description="H3 oculto; inspector 2D disponible.";}
    public void Adjust(float factor){
        if(Component==4)GainMy=Mathf.Clamp(GainMy*factor,.00001f,.2f);else GainVz=Mathf.Clamp(GainVz*factor,.00001f,2f);
        Invalidate();
    }
    public void Invalidate(){
        Clear();Diagram=null;
        if(!showing||config==null||!config.H3SpatialDiagrams||structure?.ModelRoot==null)return;
        var tag=selection?.Selected;
        if(tag==null||!tag.gameObject.activeInHierarchy){Description="H3: selecciona una barra visible.";return;}
        if(tag.wall!=null||tag.element.type=="muro"){Description="Overlay H3 My/Vz no disponible para muros en este alcance.";return;}
        var repo=UnityData.Repository;if(repo==null){Description=ARDiagramGeometry.Unavailable(ResultAvailability.Missing);return;}
        if(repo!=cachedRepo){cachedRepo=repo;sampler=new StructuralResultSampler(repo);}
        string caseId=ui!=null?ui.ActiveCase:"C1";
        if(!sampler.TryDiagram(tag.element,caseId,Component,out var diagram,out var availability)){Description=ARDiagramGeometry.Unavailable(availability);return;}
        if(availability!=ResultAvailability.Available){Description=ARDiagramGeometry.Unavailable(availability);return;}
        Diagram=diagram;
        var a=repo.Point(tag.element.nodeI);var b=repo.Point(tag.element.nodeJ);
        var points=ARDiagramGeometry.Build(a,b,diagram,Component,Gain,structure.ModelToAnchor);
        OverlayRoot=new GameObject("H3 spatial diagram").transform;OverlayRoot.SetParent(structure.ModelRoot,false);
        float width=Mathf.Clamp(structure.Scale*.08f,.0007f,.008f);
        var shader=Shader.Find("Custom/AlwaysOnTopLine");if(shader==null)throw new System.InvalidOperationException("H3 line shader missing");
        curveMaterial=new Material(shader){color=Color.cyan};baseMaterial=new Material(shader){color=Color.gray};
        Curve=Line("My/Vz (graphic, not deformation)",points,curveMaterial,width);
        Line("I to J",new[]{structure.ModelToAnchor(a),structure.ModelToAnchor(b)},baseMaterial,width*.5f);
        string name=Component==4?"My":"Vz",unit=Component==4?"kN·m":"kN",gainUnit=Component==4?"m/(kN·m)":"m/kN";
        Description=$"{tag.element.elementTag} · {name} · {caseId}\nI {diagram.Initial:0.###} / J {diagram.Final:0.###}; mín {diagram.Minimum:0.###} / máx {diagram.Maximum:0.###} {unit}\nGain gráfico {Gain:G4} {gainUnit}; escala visual {structure.Scale:G4}\nEscala gráfica, no deformación. {diagram.Origin}";
        var label=new GameObject("H3 tag "+tag.element.elementTag);label.layer=ARStructure.StructuralLayer;label.transform.SetParent(OverlayRoot,false);
        label.transform.localPosition=points[points.Length/2]+structure.ModelUpLocal*Mathf.Max(.003f,structure.Scale*.2f);
        if(Camera.main!=null)label.transform.rotation=Camera.main.transform.rotation;
        var tm=label.AddComponent<TextMesh>();tm.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");tm.fontSize=40;tm.characterSize=Mathf.Max(.001f,structure.Scale*.03f);
        tm.text=$"{tag.element.elementTag} {name} {caseId}\nI {diagram.Initial:0.##} J {diagram.Final:0.##} {unit}\nmin {diagram.Minimum:0.##} max {diagram.Maximum:0.##}\ngain {Gain:G3} {gainUnit}";
        label.AddComponent<ARDiagramLabelBillboard>();tm.color=Color.cyan;label.GetComponent<MeshRenderer>().sharedMaterial=tm.font.material;
        GeometryUpdates++;
    }
    LineRenderer Line(string name,Vector3[] points,Material material,float width){
        var go=new GameObject(name);go.layer=ARStructure.StructuralLayer;go.transform.SetParent(OverlayRoot,false);var line=go.AddComponent<LineRenderer>();
        line.useWorldSpace=false;line.positionCount=points.Length;line.SetPositions(points);line.sharedMaterial=material;line.startWidth=line.endWidth=width;return line;
    }
    void Clear(){
        if(OverlayRoot!=null){foreach(var line in OverlayRoot.GetComponentsInChildren<LineRenderer>())line.sharedMaterial=null;OverlayRoot.gameObject.SetActive(false);Destroy(OverlayRoot.gameObject);OverlayRoot=null;}
        if(curveMaterial!=null)Destroy(curveMaterial);if(baseMaterial!=null)Destroy(baseMaterial);curveMaterial=baseMaterial=null;Curve=null;
    }
    public void DrawControls(GUIStyle button,GUIStyle text){
        GUILayout.Label("H3 · Diagrama espacial (una barra)",text);GUILayout.BeginHorizontal();
        if(GUILayout.Button("My",button))Show(4);if(GUILayout.Button("Vz",button))Show(2);if(GUILayout.Button("Ocultar",button))Hide();GUILayout.EndHorizontal();
        if(showing){GUILayout.BeginHorizontal();if(GUILayout.Button("− Escala",button))Adjust(.5f);GUILayout.Label(Gain.ToString("G3"),text);if(GUILayout.Button("Escala +",button))Adjust(2);GUILayout.EndHorizontal();}
        GUILayout.Label(Description,text);
    }
    void OnDisable(){Clear();}
    void OnDestroy(){if(selection!=null)selection.Changed-=Invalidate;if(structure!=null)structure.Rebuilt-=Invalidate;if(ui!=null)ui.CaseChanged-=Invalidate;Clear();}
}
