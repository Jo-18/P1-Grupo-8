using System;
using System.Collections.Generic;
using UnityEngine;
/// Responsive IMGUI inspector. All numerical snapshots are refreshed on selection/case changes.
public class ARInspectorUI : MonoBehaviour {
    public static ARInspectorUI Instance { get; private set; }
    readonly string[] tabs={"RESUMEN","ESFUERZOS","DIAGRAMAS","CARGAS","CAPACIDAD","DATOS"};
    ARStructure structure;StructuralSelectionController selection;StructuralRepository repo;StructuralResultSampler sampler;
    string activeCase="",query="",message="",hash="";
    int tab,component=4;bool collapsed,filters,diagnostics,showReference;
    Vector2 scroll;Rect safe,header,panel;float scale;
    float[] cutI,cutMid,cutJ;StructuralResultSampler.Diagram diagram;ResultAvailability availability;
    PMCurveData capacityCurve;CapacityCombo capacityCombo;Vector2 capacityDemand;bool hasCapacityDemand;string demandNote;
    readonly Dictionary<MomentCurvatureReference,StructuralResultSampler.Diagram> referenceDiagrams=new Dictionary<MomentCurvatureReference,StructuralResultSampler.Diagram>();
    GUIStyle text,heading,button,toggle;
    TouchScreenKeyboard keyboard;
    readonly List<string> floors=new List<string>(),buildings=new List<string>();
    public event Action CaseChanged;
    public string ActiveCase=>activeCase;
    public string SelectedTag=>selection?.Selected?.element.elementTag;
    void Awake(){Instance=this;Layout();}
    void Start(){structure=GetComponent<ARStructure>();selection=GetComponent<StructuralSelectionController>();if(selection!=null)selection.Changed+=Refresh;}
    void OnDestroy(){ARDiagramPanel.ClearCache();if(selection!=null)selection.Changed-=Refresh;if(Instance==this)Instance=null;}
    void Update(){
        if(keyboard!=null && keyboard.status==TouchScreenKeyboard.Status.Visible)query=keyboard.text;
        if(repo!=UnityData.Repository && UnityData.Repository!=null){repo=UnityData.Repository;sampler=new StructuralResultSampler(repo);activeCase=repo.Cases.Contains("C1")?"C1":repo.Cases.Count>0?repo.Cases[0]:"";floors.Clear();buildings.Clear();foreach(var e in repo.Elements.Values){if(!string.IsNullOrEmpty(e.piso)&&!floors.Contains(e.piso))floors.Add(e.piso);if(!string.IsNullOrEmpty(e.sourceBuilding)&&!buildings.Contains(e.sourceBuilding))buildings.Add(e.sourceBuilding);}floors.Sort();buildings.Sort();var asset=Resources.Load<TextAsset>("estructura_p1l4_unity");if(asset!=null){using(var sha=System.Security.Cryptography.SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(asset.bytes)).Replace("-","").ToLowerInvariant();}Refresh();CaseChanged?.Invoke();}
        Layout();
    }
    public void SetCase(string value){if(repo==null||!repo.Cases.Contains(value))return;activeCase=value;Refresh();CaseChanged?.Invoke();}
    public void Refresh(){
        cutI=cutMid=cutJ=null;diagram=null;availability=ResultAvailability.Missing;collapsed=false;scroll=Vector2.zero;
        capacityCurve=null;capacityCombo=null;hasCapacityDemand=false;demandNote="";
        var e=selection?.Selected?.element;if(e==null||sampler==null)return;
        sampler.TryAt(e,activeCase,0,out cutI,out availability);sampler.TryAt(e,activeCase,.5f,out cutMid,out _);sampler.TryAt(e,activeCase,1,out cutJ,out _);sampler.TryDiagram(e,activeCase,component,out diagram,out _);
        var s=selection.Selected;var registry=s.wall==null?null:repo.WallRegistry(s.wall.id);
        capacityCurve=repo.Curve(s.wall!=null?registry?.pmSectionId:e.pmCurveId??e.sectionId);
        hasCapacityDemand=sampler.TryPM(e,activeCase,out capacityDemand);
        if(s.wall!=null){hasCapacityDemand=false;foreach(var d in registry?.demands??Array.Empty<DemandRecord>())if(d.combo==activeCase){capacityDemand=new Vector2(d.P_kN,d.M_kN_m);hasCapacityDemand=true;demandNote=d.note;break;}}
        capacityCombo=e.capacidad?.ForCombo(activeCase);
    }
    void Layout(){ARInspectorLayout.Calculate(Screen.width,Screen.height,Screen.dpi,Screen.safeArea,collapsed,out scale,out safe,out header,out panel);}
    public static bool BlocksScreenPoint(Vector2 point){
        if(HonorsAnchorDriver.Blocks(point)||HonorsCapacityComparisonPanel.Blocks(point))return true;
        if(Instance==null)return false;var ui=Instance;ui.Layout();Vector2 gui=new Vector2(point.x/ui.scale,(Screen.height-point.y)/ui.scale);
        return ui.header.Contains(gui)||((ui.selection?.Selected!=null||ui.filters||ui.diagnostics)&&ui.panel.Contains(gui));
    }
    void Styles(){
        if(text!=null)return;text=new GUIStyle(GUI.skin.label){fontSize=16,wordWrap=true};heading=new GUIStyle(text){fontStyle=FontStyle.Bold,fontSize=19};
        button=new GUIStyle(GUI.skin.button){fontSize=16,wordWrap=true,fixedHeight=44};toggle=new GUIStyle(GUI.skin.toggle){fontSize=16,wordWrap=true,fixedHeight=40};
    }
    void OnGUI(){
        Styles();var old=GUI.matrix;GUI.matrix=Matrix4x4.TRS(Vector3.zero,Quaternion.identity,Vector3.one*scale);
        try {
            GUILayout.BeginArea(header,GUI.skin.box);GUILayout.BeginHorizontal();
            GUILayout.Label("MCOC · AR",heading);
            if(GUILayout.Button("Filtros",button))filters=!filters;
            if(GUILayout.Button("Estado",button))diagnostics=!diagnostics;
            GUILayout.EndHorizontal();GUILayout.EndArea();
            if(selection?.Selected==null&&!filters&&!diagnostics)return;
            GUILayout.BeginArea(panel,GUI.skin.box);
            GUILayout.BeginHorizontal();GUILayout.Label(selection?.Selected?.wall?.elementTag??SelectedTag??"Edificio",heading);
            if(GUILayout.Button(collapsed?"Abrir":"Plegar",button,GUILayout.Width(78)))collapsed=!collapsed;
            if(GUILayout.Button("×",button,GUILayout.Width(44))){selection?.Clear();filters=diagnostics=false;}
            GUILayout.EndHorizontal();
            if(!collapsed){scroll=GUILayout.BeginScrollView(scroll);
                if(repo==null)Label("Esperando dataset...");else if(!repo.ContractValid){Label("Dataset inválido: "+string.Join("; ",repo.Errors));}else {
                    if(diagnostics)Diagnostics();if(filters)Filters();
                    if(selection?.Selected!=null){CaseButtons();Tabs();GetComponent<ARStructuralDiagramOverlay>()?.DrawControls(button,text);switch(tab){case 0:Summary();break;case 1:Forces();break;case 2:Diagrams();break;case 3:Loads();break;case 4:Capacity();break;case 5:Provenance();break;}}
                }GUILayout.EndScrollView();}
            GUILayout.EndArea();
        } finally {GUI.matrix=old;}
    }
    void Label(string value)=>GUILayout.Label(value,text);
    void CaseButtons(){Label("Caso/combinación: "+activeCase);for(int i=0;i<repo.Cases.Count;i+=3){GUILayout.BeginHorizontal();for(int j=i;j<Math.Min(i+3,repo.Cases.Count);j++)if(GUILayout.Button(repo.Cases[j],button))SetCase(repo.Cases[j]);GUILayout.EndHorizontal();}}
    void Tabs(){for(int i=0;i<6;i+=3){GUILayout.BeginHorizontal();for(int j=i;j<i+3;j++)if(GUILayout.Button(tabs[j],button)){tab=j;scroll=Vector2.zero;}GUILayout.EndHorizontal();}}
    void Summary(){var selected=selection.Selected;var e=selected.element;
        Label($"{e.elementTag} · OpenSees eleTag {e.id}\n{e.type} · {e.sourceBuilding}\nNodos analíticos {e.nodeI} → {e.nodeJ}\n{e.sectionId} · {e.material}\nPlanta etiquetada: {e.piso}\nLongitud analítica: {repo.Length(e):0.###} m");
        var i=repo.Point(e.nodeI);var j=repo.Point(e.nodeJ);StructuralResultSampler.Axes(j-i,out var x,out var y,out var z);Label($"Modelo global (m): I {i.ToString("F3")} / J {j.ToString("F3")}\nEjes locales en modelo: x {x.ToString("F3")}, y {y.ToString("F3")}, z {z.ToString("F3")}");
        if(selected.wall!=null)Label($"Visual: {selected.wall.elementTag} (id {selected.wall.id}), nodos {selected.wall.nodeI} → {selected.wall.nodeJ}\n{selected.wall.bottom} → {selected.wall.top}; espesor {selected.wall.grosor:0.###} m\nAltura {selected.mapping.topZ-selected.mapping.bottomZ:0.###} m · largo {selected.wall.longitud:0.###} m");
        GUILayout.BeginHorizontal();if(GUILayout.Button("Anterior",button))selection.Navigate(-1);if(GUILayout.Button("Siguiente",button))selection.Navigate(1);GUILayout.EndHorizontal();
        if(GUILayout.Button("Aislar seleccionado",button))selection.Isolate();if(GUILayout.Button("Vista completa",button))selection.ShowAll();
    }
    void Forces(){
        Label("Esfuerzos locales: N tracción +; sección I = -fI, J = +fJ. T/My/Mz: kN·m; N/Vy/Vz: kN.");
        if(cutI==null){Label(StructuralRepository.MissingText+" ("+availability+")");return;}
        for(int k=0;k<6;k++)Label($"{StructuralResultSampler.Names[k]} ({(k<3?"kN":"kN·m")})\nI {cutI[k]:0.###} · centro {cutMid[k]:0.###} · J {cutJ[k]:0.###}");
        var e=selection.Selected.element;
        foreach(var id in new[]{e.nodeI,e.nodeJ}){
            if(repo.TryDisplacement(id,activeCase,out var d,out var a))Label($"Nodo {id} · global modelo\nu (mm): {d.ux*1000:0.###}, {d.uy*1000:0.###}, {d.uz*1000:0.###}\nr (rad): {d.rx:G5}, {d.ry:G5}, {d.rz:G5}");else Label($"Nodo {id}: {StructuralRepository.MissingText} ({a})");
            if(repo.TryReaction(id,activeCase,out var r))Label($"Reacción global nodo {id}:\nF(kN) {r.f[0]:0.###}, {r.f[1]:0.###}, {r.f[2]:0.###}\nM(kN·m) {r.f[3]:0.###}, {r.f[4]:0.###}, {r.f[5]:0.###}");
        }
    }
    void Diagrams(){for(int i=0;i<6;i+=3){GUILayout.BeginHorizontal();for(int j=i;j<i+3;j++)if(GUILayout.Button(StructuralResultSampler.Names[j],button)){component=j;sampler.TryDiagram(selection.Selected.element,activeCase,component,out diagram,out availability);}GUILayout.EndHorizontal();}
        if(diagram==null){Label(StructuralRepository.MissingText+" ("+availability+")");return;}
        string unit=component<3?"kN":"kN·m";Label($"{StructuralResultSampler.Names[component]} local · {unit}\nI {diagram.Initial:0.###} / J {diagram.Final:0.###}\nMín {diagram.Minimum:0.###} / Máx {diagram.Maximum:0.###}");
        ARDiagramPanel.Draw(GUILayoutUtility.GetRect(100,190,GUILayout.ExpandWidth(true)),diagram);
        Label($"x = 0 → {diagram.Length:0.###} m (I → J)\nLímites reales con margen gráfico 7,5%; cero gris; {activeCase} · {unit}\n{diagram.Origin}");
    }
    void Loads(){var e=selection.Selected.element;float L=repo.Length(e);var load=repo.Applied("elementUniformTotal",e.id,activeCase);
        if(load!=null)Label($"Carga uniforme prescrita {activeCase}, global modelo\nTotal F (kN): {load.values[0]:0.###}, {load.values[1]:0.###}, {load.values[2]:0.###}\nPor metro (kN/m): {load.values[0]/L:0.###}, {load.values[1]/L:0.###}, {load.values[2]/L:0.###}\n{load.source}");else Label("Sin carga uniforme explícita registrada para este elemento/caso.");
        foreach(int id in new[]{e.nodeI,e.nodeJ}){var nodal=repo.Applied("nodeForce",id,activeCase);if(nodal==null)Label($"Nodo {id}: sin carga nodal explícita registrada.");else Label($"Carga nodal prescrita, nodo {id}, global modelo\nF (kN): {nodal.values[0]:0.###}, {nodal.values[1]:0.###}, {nodal.values[2]:0.###}\n{nodal.source}");}
        Label($"EX/EY son cargas nodales precalculadas, incluidas en las combinaciones exportadas. Los maestros de diafragmas pueden ser nodos distintos de I/J.\nNo se usa cargaTributaria legacy.\nEstaciones solver y deformada continua: {StructuralRepository.MissingText}.");
    }
    void Capacity(){var s=selection.Selected;var e=s.element;
        var curve=capacityCurve;var demand=capacityDemand;
        Label("P compresión +. Curvas uniaxiales con hipótesis; no verificación integral biaxial.");
        if(!string.IsNullOrEmpty(demandNote))Label(demandNote);
        if(curve?.points!=null&&curve.points.Length>1&&hasCapacityDemand){Label($"{curve.sectionId}\n{curve.interpretation}\nP={demand.x:0.###} kN; M={demand.y:0.###} kN·m\nGráfico: x=M, y=P; amarillo=demanda; cian=curva.");ARDiagramPanel.DrawPM(GUILayoutUtility.GetRect(100,210,GUILayout.ExpandWidth(true)),curve,demand);}else Label(StructuralRepository.MissingText);
        var cap=e.capacidad;var c=capacityCombo;
        if(c!=null){Label($"Capacidad exportada capacidad_ha.py · {activeCase}\n"+(e.type=="viga"?$"DCR flexión {c.DCR_flexion:0.###}; corte {c.DCR_corte:0.###}":$"DCR P-M {c.DCR_PM:0.###}; corte {c.DCR_corte:0.###}")+"\nArmadura: "+JsonUtility.ToJson(cap.armadura));}else Label("Utilización: "+StructuralRepository.MissingText);
        Label("M-phi por elemento: "+StructuralRepository.MissingText+". La curva de muro externa es una referencia; no se atribuye automáticamente a cada muro.");
        if(s.wall!=null && repo.Data.p1l4.momentCurvatureReferences!=null) {
            showReference=GUILayout.Toggle(showReference,"Ver M-phi de sección de referencia",toggle);
            if(showReference)foreach(var reference in repo.Data.p1l4.momentCurvatureReferences) {
                Label($"REFERENCIA {reference.sectionId}: L={reference.L_m} m, t={reference.t_m} m, P={reference.P_kN} kN. No es la curva del muro seleccionado.\n{reference.method}\nArmadura {reference.armadura}\n{reference.source}\nSHA256 {reference.sha256}");
                if(reference.curvature!=null&&reference.moment!=null&&reference.curvature.Length==reference.moment.Length&&reference.curvature.Length>1) {
                    if(!referenceDiagrams.TryGetValue(reference,out var d)){float min=reference.moment[0],max=min;foreach(var value in reference.moment){min=Mathf.Min(min,value);max=Mathf.Max(max,value);}d=new StructuralResultSampler.Diagram{X=reference.curvature,Values=reference.moment,Length=reference.curvature[reference.curvature.Length-1],Minimum=min,Maximum=max};referenceDiagrams[reference]=d;}
                    ARDiagramPanel.Draw(GUILayoutUtility.GetRect(100,190,GUILayout.ExpandWidth(true)),d);Label($"x=curvatura 0 → {d.Length:G5} {reference.curvatureUnit}; y=M ({reference.momentUnit}), límites reales con margen gráfico 7,5%. Sin demanda superpuesta.");
                }
            }
        }
    }
    void Provenance(){var e=selection.Selected.element;var c=repo.Data.corrida;Label($"Archivo Resources/estructura_p1l4_unity.json\nSHA256 {hash}\nSchema {repo.Data.schemaVersion}\nRegistro p1l4.elementForces: id={e.id}, combo={activeCase}\n{c.forceSource}\nMotor {c.motor} {c.opensees}, OpenSeesPy {c.openseespy}\nFecha {c.fecha}\nExportador {c.exporter}\nComando {c.comando}\nEntradas {JsonUtility.ToJson(c.entradas_sha256)}\nConvenciones {JsonUtility.ToJson(repo.Data.conventions)}\nUnidades {JsonUtility.ToJson(repo.Data.resultUnits)}\nCapacidad: {c.capacitySource}");var combo=repo.Combo(activeCase);if(combo!=null)Label($"Factores: G {combo.G}, Q {combo.Q}, EX {combo.EX}, EY {combo.EY}");foreach(var n in repo.Data.notes??Array.Empty<string>())Label(n);}
    void Filters(){Label("Edificio completo: marker horizontal de 20 cm. Modo columna: marker vertical calibrado cara +X.");
        GUILayout.BeginHorizontal();if(GUILayout.Button("Sector 1:1",button))structure.SetMode(ARStructure.Mode.Columna1a1);if(GUILayout.Button("Edificio 1:100",button))structure.SetMode(ARStructure.Mode.Maqueta100);if(GUILayout.Button("Sobre plano",button))structure.SetMode(ARStructure.Mode.SobrePlano);GUILayout.EndHorizontal();
        bool before=GUI.changed;GUI.changed=false;
        structure.ShowBeams=GUILayout.Toggle(structure.ShowBeams,"Vigas",toggle);structure.ShowColumns=GUILayout.Toggle(structure.ShowColumns,"Columnas",toggle);structure.ShowWalls=GUILayout.Toggle(structure.ShowWalls,"Muros",toggle);structure.ShowBraces=GUILayout.Toggle(structure.ShowBraces,"Arriostres",toggle);structure.ShowIds=GUILayout.Toggle(structure.ShowIds,"IDs",toggle);
        if(GUI.changed)structure.ApplyVisibility();GUI.changed|=before;
        if(structure.SupportRoot!=null)structure.SupportRoot.gameObject.SetActive(GUILayout.Toggle(structure.SupportRoot.gameObject.activeSelf,"Apoyos / restricciones",toggle));
        if(structure.AxesRoot!=null)structure.AxesRoot.gameObject.SetActive(GUILayout.Toggle(structure.AxesRoot.gameObject.activeSelf,"Ejes del plano",toggle));
        Label("Planta (nivel etiquetado del elemento)");if(GUILayout.Button("Todas las plantas",button)){structure.FloorFilter="";structure.ApplyVisibility();}foreach(var f in floors)if(GUILayout.Button(f,button)){structure.FloorFilter=f;structure.ApplyVisibility();}
        Label("Edificio");if(GUILayout.Button("Ambos edificios",button)){structure.BuildingFilter="";structure.ApplyVisibility();}foreach(var b in buildings)if(GUILayout.Button(b,button)){structure.BuildingFilter=b;structure.ApplyVisibility();}
        query=GUILayout.TextField(query,new GUIStyle(GUI.skin.textField){fontSize=18,fixedHeight=44});
        if(Application.isMobilePlatform && GUILayout.Button("Escribir tag / ID",button))keyboard=TouchScreenKeyboard.Open(query,TouchScreenKeyboardType.Default);
        if(GUILayout.Button("Buscar tag / eleTag visible",button))message=selection.Search(query.Trim())?"Seleccionado":"No visible / no encontrado";Label(message);
        if(GUILayout.Button("Vista completa",button))selection.ShowAll();Label($"Visibles {structure.VisibleElements().Count}; construidos {structure.Elements.Count}. Brazos rígidos excluidos.");
    }
    void Diagnostics(){ARPlaneDebugVisibility.ShowPlanes=GUILayout.Toggle(ARPlaneDebugVisibility.ShowPlanes,"DEBUG: visualizar planos detectados (OFF por defecto)",toggle);var anchor=ARImageAnchor.Instance;if(HonorsConfiguration.H2){var d=anchor?.GetComponent<HonorsAnchorDriver>();Label("Honors H2: "+d?.Session.State+"\nQA relativa (no error absoluto): "+(d!=null&&d.RelativeAvailable?d.RelativeMm.ToString("0.0")+" mm / "+d.RelativeAngleDeg.ToString("0.00")+" deg":"No disponible")+"\nReferencia fisica independiente PENDIENTE. Sin persistencia espacial.");if(GUILayout.Button("Reanclar",button))d?.Reanchor();return;}Label($"Sesión: {UnityEngine.XR.ARFoundation.ARSession.state}\nAnchor: {(anchor?.Anchor==null?"Sin anchor":anchor.Anchor.trackingState.ToString())}\nRegistro relativo imagen-anchor: Δ {anchor?.RegDeltaMm:0.0} mm, Δθ {anchor?.RegAngleDeg:0.00}°; requiere medición física independiente.\nModo {structure?.mode}; escala {structure?.Scale:G5}.\nEdificio permanece bajo ContentRoot. OpenSees no corre en Android.");if(GUILayout.Button("Reanclar desde marker visible",button))anchor?.CreateAnchor();}
}
