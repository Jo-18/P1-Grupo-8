using System;
using System.Collections.Generic;
using UnityEngine;
// A five-second relative pose window at the recorder's actual cadence.
// No physical accuracy claim; unavailable samples never become zero.
public sealed class HonorsQATelemetry {
    public const int ReadySamples=10;
    [Serializable] public class Snapshot {
        public int samples,totalSamples,detections,losses,recoveries,reanchors,pauses,resumes;
        public double duration,lastEventTime,lastDetection=-1;
        public string lastEvent="Sin eventos";
        public float noiseMm;
        public ARRegistrationRecorder.Metrics position=new ARRegistrationRecorder.Metrics(),angle=new ARRegistrationRecorder.Metrics();
    }
    public readonly Snapshot Data=new Snapshot();
    public ARRegistrationRecorder.Sample Current {get;private set;}
    readonly Queue<ARRegistrationRecorder.Sample> window=new Queue<ARRegistrationRecorder.Sample>();
    public void Event(string kind,double now){
        if(kind=="sample")return;
        Data.lastEvent=kind;Data.lastEventTime=now;
        switch(kind){case "detection":Data.detections++;Data.lastDetection=now;break;case "loss":Data.losses++;break;case "recovery":Data.recoveries++;break;case "reanchor_requested":Data.reanchors++;break;case "pause":Data.pauses++;break;case "resume":Data.resumes++;break;}
        if(kind=="accepted"||kind=="loss"||kind=="pause")window.Clear();
    }
    public void Sample(ARRegistrationRecorder.Sample s){
        Current=s;Data.totalSamples++;
        if(s.relativeAvailable)window.Enqueue(s);
        while(window.Count>0 && s.timestamp-window.Peek().timestamp>5)window.Dequeue();
        var positions=new List<float>();var angles=new List<float>();var vectors=new List<Vector3>();Vector3 mean=Vector3.zero;
        foreach(var item in window){
            if(!StructuralRepository.Finite(item.relativeMm)||!StructuralRepository.Finite(item.relativeAngleDeg))continue;
            positions.Add(item.relativeMm);angles.Add(item.relativeAngleDeg);
            var delta=Quaternion.Inverse(item.anchorRotation)*(item.imagePosition-item.anchorPosition)*1000;
            vectors.Add(delta);mean+=delta;
        }
        Data.samples=positions.Count;Data.duration=window.Count>0?s.timestamp-window.Peek().timestamp:0;
        Data.position=ARRegistrationRecorder.Statistics(positions);Data.angle=ARRegistrationRecorder.Statistics(angles);
        if(vectors.Count>0)mean/=vectors.Count;float sum=0;foreach(var v in vectors)sum+=(v-mean).sqrMagnitude;
        Data.noiseMm=vectors.Count>0?Mathf.Sqrt(sum/vectors.Count):0;
    }
    public string Format(string logical,ARMarkerProfile profile){
        var s=Current;var d=Data;
        string state=$"H2 · {logical}\nPerfil {profile?.markerId??s?.profile??"Sin perfil"}\nMarker {s?.marker??"No detectado"} / trackable {Short(s?.trackableId)}\nSession {s?.sessionState??"Sin muestra"} / marker {s?.markerState??"Missing"} / anchor {s?.anchorState??"Missing"}\nDesde detección: {(d.lastDetection>=0&&s!=null?(s.timestamp-d.lastDetection).ToString("0.0")+" s":"--")}\nMuestras QA totales {d.totalSamples}; ventana {d.samples}, {d.duration:0.0} s";
        string qa=d.samples<ReadySamples?$"Recolectando QA: {d.samples}/{ReadySamples} muestras válidas (umbral sólo de presentación).":
            $"Δ posición actual {(s!=null&&s.relativeAvailable?s.relativeMm.ToString("0.00")+" mm":"No disponible")}\nPosición relativa: mediana {d.position.median:0.00}, RMS {d.position.rms:0.00}, p95 {d.position.p95:0.00}, máx {d.position.max:0.00} mm\nRuido RMS del vector relativo: {d.noiseMm:0.00} mm\nΔ angular actual {(s!=null&&s.relativeAvailable?s.relativeAngleDeg.ToString("0.00")+"°":"No disponible")}\nÁngulo relativo: mediana {d.angle.median:0.00}, RMS {d.angle.rms:0.00}, p95 {d.angle.p95:0.00}, máx {d.angle.max:0.00}°";
        return state+"\n"+qa+$"\nDetecciones {d.detections} / pérdidas {d.losses} / recuperaciones {d.recoveries}\nReanclajes {d.reanchors} / pause {d.pauses} / resume {d.resumes}\nÚltimo evento {d.lastEvent}, t={d.lastEventTime:0.0} s monotónicos\nPerfil: ancho declarado {(profile!=null?profile.declaredWidthMeters*100:20):0.0} cm\np_ref {profile?.reference}; M: {profile?.mx} / {profile?.my} / {profile?.mz}\n{profile?.calibrationStatus??"Calibración física PENDIENTE"}\nQA RELATIVA de poses ARCore; no error físico absoluto ni persistencia espacial.";
    }
    static string Short(string id)=>string.IsNullOrEmpty(id)?"--":id.Length>16?id.Substring(0,16)+"…":id;
}
