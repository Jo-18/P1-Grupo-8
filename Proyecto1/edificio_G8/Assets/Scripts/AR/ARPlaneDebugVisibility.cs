using UnityEngine;
// ARPlaneMeshVisualizer stays active: it also updates the MeshCollider.
// AR Foundation writes renderer.enabled in Update; apply the display policy
// in LateUpdate, before rendering, without disabling plane detection/raycast.
[DefaultExecutionOrder(10000)]
public sealed class ARPlaneDebugVisibility : MonoBehaviour {
    public static bool ShowPlanes { get; set; }
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
    static void ResetDebug(){ShowPlanes=false;}
    void Awake(){Apply();}
    void LateUpdate(){Apply();}
    public void Apply(){
        if(ShowPlanes)return; // let AR Foundation enforce tracking visibility
        foreach(var r in GetComponents<Renderer>())r.enabled=false;
    }
}
