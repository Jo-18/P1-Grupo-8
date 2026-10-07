using UnityEngine;
/// Points are model coordinates (Z up). M has determinant -1; anchor rotation is separate.
public struct ModelCoordinateTransform {
    public readonly float Scale;
    public readonly Vector3 Reference;
    public readonly bool Column;
    public ModelCoordinateTransform(float scale, Vector3 reference, bool column) {
        if (scale <= 0 || float.IsNaN(scale) || float.IsInfinity(scale)) throw new System.ArgumentOutOfRangeException(nameof(scale));
        Scale=scale; Reference=reference; Column=column;
    }
    public Vector3 Direction(Vector3 d) => Column ? new Vector3(d.y,d.x,d.z) : new Vector3(d.x,d.z,d.y);
    public Vector3 Forward(Vector3 p) => Scale * Direction(p-Reference);
    public Vector3 Inverse(Vector3 p) => Direction(p/Scale)+Reference;
    public Vector3 World(Vector3 p, Pose anchor) => anchor.position+anchor.rotation*Forward(p);
    public Vector3 FromWorld(Vector3 p, Pose anchor) => Inverse(Quaternion.Inverse(anchor.rotation)*(p-anchor.position));
}
