using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
/// Honors controller; a single accepted ContentRoot, with the prior anchor retained until replacement succeeds.
public sealed class HonorsAnchorDriver : MonoBehaviour {
    public readonly ARAnchorSessionState Session=new ARAnchorSessionState();
    public ARMarkerProfile ActiveProfile {get;private set;}
    public string PreferredMarkerId=ARImageAnchor.MarkerName;
    public float timeoutSeconds=8;
    public string Message {get;private set;}="Buscando perfil";
    public bool RelativeAvailable {get;private set;}
    public float RelativeMm {get;private set;}
    public float RelativeAngleDeg {get;private set;}
    public readonly HonorsQATelemetry QA=new HonorsQATelemetry();
    bool priorTracking,awaitingRecovery;string priorKey="";
    public string QAExportStatus {get;private set;}="";
    ARStructure.Mode legacyMode;
    public IHonorsAnchorProvider Provider {get;set;}
    public ARMarkerProfileRegistry Registry {get;private set;}
    ARImageAnchor owner;ARTrackedImageManager images;ARTrackedImage marker;ARRegistrationRecorder recorder;
    bool disposed,wasEnabled,nativePending;double nextSample;readonly Queue<double> window=new Queue<double>();string lastState="";Rect box,launcher;bool showPanel;Vector2 scroll;float uiScale;GUIStyle textStyle,buttonStyle;
    public bool NativePending=>nativePending;
    void Start(){
        owner=GetComponent<ARImageAnchor>();images=FindAnyObjectByType<ARTrackedImageManager>();var manager=FindAnyObjectByType<ARAnchorManager>();if(Provider==null&&manager!=null)Provider=new HonorsAnchorProvider(manager);
        try{var model=Resources.Load<TextAsset>("estructura_p1l4_unity");string hash;using(var sha=System.Security.Cryptography.SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(model.bytes)).Replace("-","").ToLowerInvariant();Registry=new ARMarkerProfileRegistry(Resources.Load<TextAsset>("Honors/marker_profiles").text,hash);}
        catch(Exception e){Message="ERROR perfiles: "+e.Message;enabled=false;}
    }
    public void Tick(){
        if(!enabled||disposed)return;
        if(!HonorsConfiguration.H2){if(wasEnabled){Session.Suspend();recorder?.Dispose();recorder=null;wasEnabled=false;ARStructure.Instance?.SetMode(legacyMode);ARStructure.Instance?.Rebuild();}return;}
        if(!wasEnabled){legacyMode=ARStructure.Instance!=null?ARStructure.Instance.mode:ARStructure.Mode.Maqueta100;Session.Resume();if(ActiveProfile!=null)ARStructure.Instance?.Rebuild();}
        wasEnabled=true;if(recorder==null){recorder=new ARRegistrationRecorder(System.IO.Path.Combine(HonorsPaths.Evidence,"QA"));if(Registry!=null)recorder.Profiles(Registry.Profiles);}
        if(Session.State==ARAnchorSessionState.Phase.Suspended)return;
        var now=Time.realtimeSinceStartupAsDouble;
        if(Session.Timeout(now,timeoutSeconds)){Message="Timeout; se conserva anchor anterior";Record("timeout");}
        if(owner!=null&&Session.HasValidAnchor&&!owner.HasAnchor){Session.AnchorLost();Record("anchor_lost");}
        marker=null;ARMarkerProfile profile=null;
        if(images!=null&&Registry!=null){var list=new List<ARTrackedImage>();foreach(var img in images.trackables)list.Add(img);list.Sort((a,b)=>string.CompareOrdinal(a.trackableId.ToString(),b.trackableId.ToString()));foreach(var img in list)if(img.referenceImage.name==PreferredMarkerId&&Registry.TryGet(img.referenceImage.name,img.referenceImage.guid.ToString(),out var p)){marker=img;profile=p;break;}}
        bool tracking=marker!=null&&marker.trackingState==TrackingState.Tracking;
        string key=tracking?marker.referenceImage.name+":"+marker.trackableId:"";
        if(tracking && (!priorTracking||key!=priorKey)){Record("detection");if(awaitingRecovery){Record("recovery");awaitingRecovery=false;}}
        if(!tracking&&priorTracking){Record("loss");awaitingRecovery=true;}priorTracking=tracking;priorKey=key;
        if(Session.Observe(key,tracking,now,owner!=null?owner.settleTime:.6)&&Provider!=null&&!nativePending){var r=Session.Begin(key,new Pose(marker.transform.position,marker.transform.rotation),profile,now);Record("request");_=ProcessRequest(r,marker.size);}
        if(tracking&&owner!=null&&owner.HasAnchor&&owner.Anchor.trackingState!=TrackingState.Tracking)Session.MarkLimited();
        var state=Session.State.ToString();if(state!=lastState){Record("state_"+state);lastState=state;}
        if(now>=nextSample){nextSample=now+.1;Record("sample");}
    }
    public async Task ProcessRequest(ARAnchorSessionState.Request request,Vector2 size){
        if(nativePending){Session.Fail(request);Message="Solicitud nativa anterior pendiente; sin crear otra";return;}
        nativePending=true;
        try{
            recorder?.Request(request);var r=await Provider.Add(request.pose);
            if(disposed||this==null||!isActiveAndEnabled||!HonorsConfiguration.H2||!Session.IsCurrent(request)){if(r.anchor!=null)Destroy(r.anchor.gameObject);if(!disposed)Record("late_rejected");return;}
            if(!r.success||r.anchor==null){if(r.anchor!=null)Destroy(r.anchor.gameObject);Session.Fail(request);Message="Fallo de reemplazo; anchor anterior conservado";Record("failed");return;}
            Session.Accept(request);ActiveProfile=request.profile;owner=owner??GetComponent<ARImageAnchor>();owner.AcceptHonorsAnchor(r.anchor,ActiveProfile,size);Message="Perfil "+ActiveProfile.markerId+" / "+ActiveProfile.calibrationStatus;Record("accepted");
        }catch(Exception e){if(!disposed&&this!=null&&Session.IsCurrent(request)){Session.Fail(request);Message="ERROR: "+e.Message;Record("exception");}}
        finally{nativePending=false;}
    }
    void Record(string kind){if(recorder==null)return;var now=Time.realtimeSinceStartupAsDouble;window.Enqueue(now);while(window.Count>0&&now-window.Peek()>5)window.Dequeue();var a=owner?.Anchor;var tracked=marker!=null&&marker.trackingState==TrackingState.Tracking;bool relative=a!=null&&tracked&&marker.referenceImage.name==ActiveProfile?.markerId;
        RelativeAvailable=relative;RelativeMm=relative?Vector3.Distance(marker.transform.position,a.transform.position)*1000:0;RelativeAngleDeg=relative?Quaternion.Angle(marker.transform.rotation,a.transform.rotation):0;
        var profile=ActiveProfile;if(profile==null&&Registry!=null)foreach(var p in Registry.Profiles)if(p.markerId==PreferredMarkerId){profile=p;break;}
        var sample=new ARRegistrationRecorder.Sample{timestamp=now,marker=marker!=null?marker.referenceImage.name:"",trackableId=marker!=null?marker.trackableId.ToString():"",profile=profile?.markerId??PreferredMarkerId,modelSHA256=profile?.modelSHA256??"",eventName=kind,sessionState=ARSession.state.ToString(),markerState=marker!=null?marker.trackingState.ToString():"Missing",anchorState=a!=null?a.trackingState.ToString():"Missing",logicalState=Session.State.ToString(),request=Session.Version,windowCount=window.Count,windowSeconds=window.Count>0?(float)(now-window.Peek()):0,relativeAvailable=relative,relativeMm=relative?Vector3.Distance(marker.transform.position,a.transform.position)*1000:0,relativeAngleDeg=relative?Quaternion.Angle(marker.transform.rotation,a.transform.rotation):0,cameraDistanceMeters=marker!=null&&Camera.main!=null?Vector3.Distance(Camera.main.transform.position,marker.transform.position):0,imagePosition=marker!=null?marker.transform.position:Vector3.zero,imageRotation=marker!=null?marker.transform.rotation:Quaternion.identity,anchorPosition=a!=null?a.transform.position:Vector3.zero,anchorRotation=a!=null?a.transform.rotation:Quaternion.identity};
        QA.Event(kind,now);if(kind=="sample")QA.Sample(sample);recorder.Record(sample);
    }
    public bool ExportQA(){
        try{if(recorder==null)throw new InvalidOperationException("Recorder sin iniciar");recorder.Flush();System.IO.File.WriteAllText(System.IO.Path.Combine(recorder.OutputDirectory,"panel_window.json"),JsonUtility.ToJson(QA.Data,true));QAExportStatus="QA exportada: "+recorder.OutputDirectory;return true;}
        catch(Exception e){QAExportStatus="Error real al exportar QA: "+e.Message;Debug.LogException(e,this);return false;}
    }
    public string QAInformation=>QA.Format(Session.State.ToString(),ActiveProfile)+"\nVisualización: "+ARStructure.Instance?.mode+" / escala "+ARStructure.Instance?.Scale+"\nEl perfil de tracking no elige la escala visual.";
    public void Reanchor(){Session.ForceReanchor();Record("reanchor_requested");}
    void OnApplicationPause(bool pause){if(pause){Session.Suspend();Record("pause");recorder?.Flush();}else{Session.Resume();Record("resume");}}
    void OnDisable(){Session.Suspend();Record("disable");recorder?.Flush();}
    void OnEnable(){if(Session.State==ARAnchorSessionState.Phase.Suspended)Session.Resume();}
    void OnDestroy(){disposed=true;Session.Suspend();recorder?.Dispose();recorder=null;}
    void LayoutUI(){uiScale=Mathf.Clamp(Screen.dpi>0?Screen.dpi/160f:Screen.width/430f,1,3);var a=Screen.safeArea;var safe=new Rect(a.x/uiScale,(Screen.height-a.yMax)/uiScale,a.width/uiScale,a.height/uiScale);launcher=new Rect(safe.xMax-163,safe.yMax-52,155,44);box=new Rect(safe.x+8,safe.y+72,Mathf.Min(400,safe.width-16),Mathf.Max(90,Mathf.Min(340,safe.height-140)));}
    public static bool Blocks(Vector2 point){var d=FindAnyObjectByType<HonorsAnchorDriver>();if(d==null||!HonorsConfiguration.H2)return false;d.LayoutUI();var p=new Vector2(point.x/d.uiScale,(Screen.height-point.y)/d.uiScale);return d.launcher.Contains(p)||(d.showPanel&&d.box.Contains(p));}
    void OnGUI(){if(!HonorsConfiguration.H2)return;LayoutUI();var matrix=GUI.matrix;GUI.matrix=Matrix4x4.Scale(Vector3.one*uiScale);if(textStyle==null){textStyle=new GUIStyle(GUI.skin.label){fontSize=16,wordWrap=true};buttonStyle=new GUIStyle(GUI.skin.button){fontSize=16,wordWrap=true,fixedHeight=44};}try{if(GUI.Button(launcher,showPanel?"Cerrar H2":"Honors H2 · QA",buttonStyle))showPanel=!showPanel;if(!showPanel)return;GUILayout.BeginArea(box,GUI.skin.box);scroll=GUILayout.BeginScrollView(scroll);GUILayout.Label(QAInformation,textStyle);GUILayout.Label(Message,textStyle);if(GUILayout.Button("Exportar QA",buttonStyle))ExportQA();GUILayout.Label(QAExportStatus,textStyle);if(GUILayout.Button("Reanclar: conservar anterior hasta éxito",buttonStyle))Reanchor();if(Registry!=null)foreach(var p in Registry.Profiles){GUI.enabled=p.enabled;if(GUILayout.Button(p.markerId+(p.enabled?"":" · PENDIENTE"),buttonStyle)){PreferredMarkerId=p.markerId;Session.ForceReanchor();Record("profile_requested");}GUI.enabled=true;}GUILayout.EndScrollView();GUILayout.EndArea();}finally{GUI.matrix=matrix;}}
}
