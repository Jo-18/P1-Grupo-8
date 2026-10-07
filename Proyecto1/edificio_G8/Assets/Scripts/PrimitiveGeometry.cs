using UnityEngine;
public static class PrimitiveGeometry {
    // CreatePrimitive creates colliders internally. Explicit typed references
    // retain the native SphereCollider class in stripped IL2CPP players.
    // Get-or-add preserves one collider, including node markers that need it.
    public static GameObject CreateSphere(){
        var go=GameObject.CreatePrimitive(PrimitiveType.Sphere);
        if(go.GetComponent<SphereCollider>()==null)go.AddComponent<SphereCollider>();
        if(go.GetComponent<MeshFilter>()==null || go.GetComponent<MeshRenderer>()==null)
            throw new System.InvalidOperationException("Sphere primitive lacks render components");
        return go;
    }
}
