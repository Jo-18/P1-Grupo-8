using System;
using UnityEngine;
using Object=UnityEngine.Object;
/// Selection-driven offline comparison. Does not apply a global dataset or rebuild AR.
public sealed class HonorsCapacityComparisonPanel : MonoBehaviour {
    // Legacy explicit reference adapter retained for original desktop regression tests.
    public HonorsCapacitySession Session {get;private set;}=new HonorsCapacitySession();
    public HonorsCapacityContext Context {get;private set;}=new HonorsCapacityContext{Status="Selecciona un elemento para H5."};
    public bool IsOpen {get;private set;}
    public bool ShowComparison {get;private set;}=true;
    public int ContextUpdates {get;private set;}
    public Vector2? PlotDemand=>Context.HasDemand?(Vector2?)Context.Demand:null;
    StructureViewer viewer;StructuralSelectionController selection;ARInspectorUI inspector;ElementPicker picker;
    HonorsCapacityCatalog catalog;string catalogError;StructuralRepository lastRepo;int lastId=-1;string lastCase;
    Texture2D chart;Vector2 scroll;Rect panel,launcher;float scale;GUIStyle label,button;
    void Layout(){scale=Mathf.Clamp(Screen.dpi>0?Screen.dpi/160f:Screen.width/430f,1,3);var a=Screen.safeArea;var safe=new Rect(a.x/scale,(Screen.height-a.yMax)/scale,a.width/scale,a.height/scale);launcher=new Rect(safe.x+8,safe.yMax-52,165,44);panel=new Rect(safe.x+12,safe.y+72,Mathf.Min(650,safe.width-24),Mathf.Max(90,Mathf.Min(720,safe.height-140)));}
    void Start(){
        viewer=GetComponent<StructureViewer>();selection=GetComponent<StructuralSelectionController>();inspector=GetComponent<ARInspectorUI>();if(viewer!=null)picker=Object.FindAnyObjectByType<ElementPicker>();
        try{catalog=HonorsCapacityCatalog.Load();}catch(Exception e){catalogError=e.Message;}
        if(selection!=null)selection.Changed+=RefreshContext;if(inspector!=null)inspector.CaseChanged+=RefreshContext;if(viewer!=null)viewer.ModelReloaded+=RefreshContext;
        RefreshContext();
    }
    ElementData Selected=>selection!=null?selection.Selected?.element:picker?.Selected?.data;
    string ActiveCase=>inspector!=null?inspector.ActiveCase:UnityData.ActiveCombo;
    void Update(){
        if(HonorsConfiguration.H5)Session.Poll(viewer);else if(Session.Applied)Session.Discard(viewer);
        // Desktop ElementPicker has no event. Watch identity/case/repository only, never sample/rebuild each frame.
        if(lastRepo!=UnityData.Repository||lastId!=(Selected?.id??-1)||lastCase!=ActiveCase)RefreshContext();
    }
    public void RefreshContext(){
        var e=Selected;lastRepo=UnityData.Repository;lastId=e?.id??-1;lastCase=ActiveCase;
        Context=catalog!=null?catalog.Resolve(lastRepo,e,ActiveCase):new HonorsCapacityContext{Element=e,CaseId=ActiveCase,Status=catalogError??"Catálogo no disponible"};
        ContextUpdates++;ShowComparison=true;scroll=Vector2.zero;ReleaseChart();
    }
    public void ToggleOpen(){IsOpen=!IsOpen;if(IsOpen)RefreshContext();}
    public void SetComparisonVisible(bool visible){ShowComparison=visible;ReleaseChart();}
    void ReleaseChart(){if(chart!=null){if(Application.isPlaying)Destroy(chart);else DestroyImmediate(chart);chart=null;}}
    public Texture2D Chart(){if(Context.BaseCurve==null)return null;if(chart==null)chart=HonorsCapacityPlot.Render(Context.BaseCurve,ShowComparison?Context.AfterCurve:null,PlotDemand);return chart;}
    void OnDestroy(){if(selection!=null)selection.Changed-=RefreshContext;if(inspector!=null)inspector.CaseChanged-=RefreshContext;if(viewer!=null)viewer.ModelReloaded-=RefreshContext;ReleaseChart();Session.Dispose();}
    public static bool Blocks(Vector2 point){var p=Object.FindAnyObjectByType<HonorsCapacityComparisonPanel>();if(p==null||!HonorsConfiguration.H5)return false;p.Layout();var gui=new Vector2(point.x/p.scale,(Screen.height-point.y)/p.scale);return p.launcher.Contains(gui)||(p.IsOpen&&p.panel.Contains(gui));}
    void Capacity(string title,CapacityData cap,CapacityCombo combo){
        if(cap==null)return;GUILayout.Label($"{title}: Ast {cap.Ast_mm2:0.0} mm² · P0 {cap.P0_kN:0.0} kN · φPmax {cap.phiPmax_kN:0.0} kN",label);
        GUILayout.Label(combo!=null?$"{Context.CaseId}: Mcap(Pu) {combo.phiMn_at_Pu:0.0} kN·m · DCR P-M {combo.DCR_PM:0.000}":"Mcap/DCR no disponibles para el caso activo.",label);
    }
    void OnGUI(){
        if(!HonorsConfiguration.H5)return;Layout();var matrix=GUI.matrix;GUI.matrix=Matrix4x4.Scale(Vector3.one*scale);
        if(label==null){label=new GUIStyle(GUI.skin.label){fontSize=16,wordWrap=true};button=new GUIStyle(GUI.skin.button){fontSize=16,wordWrap=true,fixedHeight=44};}
        try{
            if(GUI.Button(launcher,IsOpen?"Cerrar Honors H5":"Honors H5 · comparar",button))ToggleOpen();if(!IsOpen)return;
            GUILayout.BeginArea(panel,GUI.skin.box);scroll=GUILayout.BeginScrollView(scroll);
            GUILayout.Label(Context.Header,label);GUILayout.Label(Context.Details,label);
            if(Context.BaseCurve!=null){
                Capacity("BASE",Context.BaseCapacity,Context.BaseCombo);
                if(Context.ComparisonAvailable){
                    if(GUILayout.Button(ShowComparison?"Ocultar comparación / vista base":"Mostrar comparación del seleccionado",button))SetComparisonVisible(!ShowComparison);
                    if(ShowComparison)Capacity("HONORS "+HonorsCapacityContext.Bars(Context.Scenario.afterArm),Context.AfterCapacity,Context.AfterCombo);
                }
                var texture=Chart();float w=Mathf.Max(1,panel.width-42);var area=GUILayoutUtility.GetRect(w,w*.625f);
                GUI.BeginGroup(area);try{GUI.DrawTexture(new Rect(0,0,area.width,area.height),texture,ScaleMode.StretchToFill);}finally{GUI.EndGroup();}
                GUILayout.Label("Horizontal φM [kN·m] · Vertical φP [kN]. Azul: base · Naranja: Honors · Amarillo: demanda del seleccionado/caso activo. Misma escala con margen gráfico.",label);
            }
            if(Context.Scenario!=null)GUILayout.Label(Context.Scenario.provenance,label);
            GUILayout.Label("Referencia certificada H5: E1_287/C2. No sustituye al seleccionado. Android usa catálogo offline; no ejecuta Python/OpenSees. Comparar/volver a base no cambia geometría, demanda ni anchor.",label);
            GUILayout.EndScrollView();GUILayout.EndArea();
        }finally{GUI.matrix=matrix;}
    }
}
