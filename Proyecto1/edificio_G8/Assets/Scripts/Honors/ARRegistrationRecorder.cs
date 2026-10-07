using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;
/// Relative image/anchor QA. Independent physical controls belong in a separate file.
public sealed class ARRegistrationRecorder : IDisposable {
    [Serializable] public class Sample {public double timestamp;public string run,marker,trackableId,profile,modelSHA256,eventName,sessionState,markerState,anchorState,logicalState;public int request,windowCount;public float windowSeconds,cameraDistanceMeters,relativeMm,relativeAngleDeg;public Vector3 imagePosition,anchorPosition;public Quaternion imageRotation,anchorRotation;public bool relativeAvailable;}
    [Serializable] class RequestSnapshot {public int version;public string candidate;public Pose pose;public ARMarkerProfile profile;public double started;}
    [Serializable] public class Metrics {public int count;public float median,rms,p95,max;}
    [Serializable] class Summary {public string run,kind="QA_RELATIVA_NO_ERROR_ABSOLUTO",physical="PENDIENTE";public Metrics positionMm,angleDeg;public Sample[] samples;}
    readonly List<Sample> samples=new List<Sample>();readonly StreamWriter csv;readonly string directory;readonly string run=Guid.NewGuid().ToString("N");
    public ARRegistrationRecorder(string output){directory=Path.Combine(output,run);Directory.CreateDirectory(directory);csv=new StreamWriter(Path.Combine(directory,"raw.csv"));csv.WriteLine("monotonicSeconds,run,marker,trackableId,profile,modelSHA256,event,session,markerState,anchorState,logicalState,request,relativeAvailable,relativeMm,relativeAngleDeg,distanceMeters,windowSeconds,windowCount,imageX,imageY,imageZ,imageQX,imageQY,imageQZ,imageQW,anchorX,anchorY,anchorZ,anchorQX,anchorQY,anchorQZ,anchorQW");File.WriteAllText(Path.Combine(directory,"physical_reference_PENDING.csv"),"run,controlId,modelX_m,modelY_m,modelZ_m,independentMeasuredX_m,independentMeasuredY_m,independentMeasuredZ_m,instrument,uncertainty_m\n");}
    public void Record(Sample s){s.run=run;samples.Add(s);var i=CultureInfo.InvariantCulture;
        csv.WriteLine(string.Join(",",new object[]{s.timestamp.ToString("R",i),run,s.marker,s.trackableId,s.profile,s.modelSHA256,s.eventName,s.sessionState,s.markerState,s.anchorState,s.logicalState,s.request,s.relativeAvailable,s.relativeMm.ToString("R",i),s.relativeAngleDeg.ToString("R",i),s.cameraDistanceMeters.ToString("R",i),s.windowSeconds.ToString("R",i),s.windowCount,s.imagePosition.x.ToString("R",i),s.imagePosition.y.ToString("R",i),s.imagePosition.z.ToString("R",i),s.imageRotation.x.ToString("R",i),s.imageRotation.y.ToString("R",i),s.imageRotation.z.ToString("R",i),s.imageRotation.w.ToString("R",i),s.anchorPosition.x.ToString("R",i),s.anchorPosition.y.ToString("R",i),s.anchorPosition.z.ToString("R",i),s.anchorRotation.x.ToString("R",i),s.anchorRotation.y.ToString("R",i),s.anchorRotation.z.ToString("R",i),s.anchorRotation.w.ToString("R",i)}));if(samples.Count%20==0)csv.Flush();
    }
    public static Metrics Statistics(IEnumerable<float> values){var v=new List<float>();foreach(var f in values)if(StructuralRepository.Finite(f))v.Add(f);v.Sort();if(v.Count==0)return new Metrics();double sum=0;foreach(var f in v)sum+=f*f;return new Metrics{count=v.Count,median=v.Count%2==0?(v[v.Count/2-1]+v[v.Count/2])/2:v[v.Count/2],rms=(float)Math.Sqrt(sum/v.Count),p95=v[Mathf.Clamp((int)Math.Ceiling(v.Count*.95)-1,0,v.Count-1)],max=v[v.Count-1]};}
    public void Profiles(IEnumerable<ARMarkerProfile> profiles){File.WriteAllText(Path.Combine(directory,"profiles_snapshot.json"),JsonUtility.ToJson(new ARMarkerProfileRegistry.Bundle{profiles=new List<ARMarkerProfile>(profiles).ToArray()},true));}
    public void Request(ARAnchorSessionState.Request r){File.WriteAllText(Path.Combine(directory,"request_"+r.version+".json"),JsonUtility.ToJson(new RequestSnapshot{version=r.version,candidate=r.candidate,pose=r.pose,profile=r.profile,started=r.started},true));}
    public string OutputDirectory=>directory;
    public void Flush(){csv.Flush();var p=new List<float>();var a=new List<float>();foreach(var s in samples)if(s.relativeAvailable&&s.eventName=="sample"){p.Add(s.relativeMm);a.Add(s.relativeAngleDeg);}File.WriteAllText(Path.Combine(directory,"summary.json"),JsonUtility.ToJson(new Summary{run=run,positionMm=Statistics(p),angleDeg=Statistics(a),samples=samples.ToArray()},true));}
    public void Dispose(){Flush();csv.Dispose();}
}
