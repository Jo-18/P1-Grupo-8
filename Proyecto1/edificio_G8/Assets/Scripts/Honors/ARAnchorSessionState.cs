using UnityEngine;
/// Logical cancellation and immutable request snapshots; no invented CancellationToken overload.
public sealed class ARAnchorSessionState {
    public enum Phase {Searching,Settling,Creating,Anchored,Limited,Suspended,Error}
    public sealed class Request {public readonly int version;public readonly string candidate;public readonly Pose pose;public readonly ARMarkerProfile profile;public readonly double started;internal Request(int v,string c,Pose p,ARMarkerProfile f,double time){version=v;candidate=c;pose=p;profile=f.Snapshot();started=time;}}
    public Phase State {get;private set;}=Phase.Searching;
    public int Version {get;private set;}
    public bool HasValidAnchor {get;private set;}
    public string Candidate {get;private set;}="";
    public string ActiveProfile {get;private set;}="";
    public double SettlingSince {get;private set;}=-1;
    Request pending;
    public bool Observe(string key,bool tracking,double now,double settle){
        if(State==Phase.Suspended)return false;
        if(!tracking){if(pending!=null)Invalidate();Candidate="";SettlingSince=-1;State=HasValidAnchor?Phase.Limited:Phase.Searching;return false;}
        if(Candidate!=key){if(pending!=null)Invalidate();Candidate=key;SettlingSince=now;State=Phase.Settling;}
        if(pending!=null)return false;
        if(HasValidAnchor&&ActiveProfile==key){State=Phase.Anchored;return false;}
        State=Phase.Settling;return now-SettlingSince>=settle;
    }
    public Request Begin(string key,Pose pose,ARMarkerProfile profile,double now){if(State==Phase.Suspended)throw new System.InvalidOperationException("Suspendido");pending=new Request(++Version,key,pose,profile,now);State=Phase.Creating;return pending;}
    public bool IsCurrent(Request r)=>r!=null&&pending==r&&r.version==Version&&Candidate==r.candidate&&State==Phase.Creating;
    public bool Accept(Request r){if(!IsCurrent(r))return false;pending=null;HasValidAnchor=true;ActiveProfile=r.candidate;State=Phase.Anchored;return true;}
    public void Fail(Request r){if(!IsCurrent(r))return;Invalidate();SettlingSince=-1;Candidate="";State=Phase.Error;}
    public bool Timeout(double now,double seconds){if(pending==null||now-pending.started<seconds)return false;var r=pending;Fail(r);return true;}
    public void Invalidate(){Version++;pending=null;}
    public void Suspend(){Invalidate();Candidate="";SettlingSince=-1;State=Phase.Suspended;}
    public void Resume(){Invalidate();Candidate="";SettlingSince=-1;State=HasValidAnchor?Phase.Limited:Phase.Searching;}
    public void ForceReanchor(){Invalidate();ActiveProfile="";Candidate="";SettlingSince=-1;State=Phase.Searching;}
    public void AnchorLost(){HasValidAnchor=false;ForceReanchor();}
    public void MarkLimited(){if(State==Phase.Anchored)State=Phase.Limited;}
}
