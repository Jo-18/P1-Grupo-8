using UnityEngine;
public readonly struct HonorsMarkerTransform {
    readonly ARMarkerProfile p;
    public HonorsMarkerTransform(ARMarkerProfile profile){if(!profile.Validate(out var e))throw new System.ArgumentException(e);p=profile;}
    public Vector3 Direction(Vector3 d)=>p.Basis.MultiplyVector(d);
    public Vector3 Forward(Vector3 point)=>p.scale*Direction(point-p.reference);
    public Vector3 Inverse(Vector3 point)=>p.reference+p.Basis.transpose.MultiplyVector(point/p.scale);
    public Vector3 World(Vector3 point,Pose anchor)=>anchor.position+anchor.rotation*Forward(point);
}
