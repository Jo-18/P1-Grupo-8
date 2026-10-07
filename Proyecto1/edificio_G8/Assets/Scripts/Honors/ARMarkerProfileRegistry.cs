using System;
using System.Collections.Generic;
using UnityEngine;
public sealed class ARMarkerProfileRegistry {
    [Serializable] public class Bundle {public ARMarkerProfile[] profiles;}
    readonly Dictionary<string,ARMarkerProfile> entries=new Dictionary<string,ARMarkerProfile>();
    public IEnumerable<ARMarkerProfile> Profiles=>entries.Values;
    public ARMarkerProfileRegistry(string json,string modelSHA256){
        var b=JsonUtility.FromJson<Bundle>(json);if(b?.profiles==null)throw new ArgumentException("Perfiles ausentes");
        var guids=new HashSet<string>();
        foreach(var p in b.profiles){if(!p.Validate(out var error)||p.modelSHA256!=modelSHA256)throw new ArgumentException(error??"Modelo SHA no coincide");if(entries.ContainsKey(p.markerId)||(!string.IsNullOrEmpty(p.imageGuid)&&!guids.Add(p.imageGuid)))throw new ArgumentException("Identidad duplicada");entries.Add(p.markerId,p);}
    }
    public bool TryGet(string markerId,string guid,out ARMarkerProfile profile){
        profile=null;if(!entries.TryGetValue(markerId??"",out var p)||!p.enabled||(!string.IsNullOrEmpty(p.imageGuid)&&p.imageGuid!=guid))return false;profile=p.Snapshot();return true;
    }
}
