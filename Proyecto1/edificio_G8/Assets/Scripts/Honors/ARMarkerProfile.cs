using System;
using UnityEngine;
[Serializable] public sealed class ARMarkerProfile {
    public string markerId,imageGuid,modelSHA256,source,date,responsible,calibrationStatus;
    public float declaredWidthMeters,measuredWidthMeters,scale;
    public Vector3 reference,mx,my,mz,minimum,maximum;
    public int mode;public bool sector,enabled,physicalVerified;
    public Matrix4x4 Basis {get {var m=Matrix4x4.identity;m.SetColumn(0,new Vector4(mx.x,mx.y,mx.z,0));m.SetColumn(1,new Vector4(my.x,my.y,my.z,0));m.SetColumn(2,new Vector4(mz.x,mz.y,mz.z,0));return m;}}
    public bool Validate(out string problem) {
        problem=null;
        if(string.IsNullOrWhiteSpace(markerId)||string.IsNullOrWhiteSpace(source)||string.IsNullOrWhiteSpace(calibrationStatus)||modelSHA256==null||modelSHA256.Length!=64)problem="Identidad/procedencia incompleta";
        else if(!Finite(reference)||!Finite(mx)||!Finite(my)||!Finite(mz)||!Finite(minimum)||!Finite(maximum)||!StructuralRepository.Finite(scale)||scale<=0||!StructuralRepository.Finite(declaredWidthMeters)||declaredWidthMeters<=0||!StructuralRepository.Finite(measuredWidthMeters)||measuredWidthMeters<0)problem="Datos no finitos / escala o tamaño inválidos";
        else if(Mathf.Abs(mx.sqrMagnitude-1)>1e-5||Mathf.Abs(my.sqrMagnitude-1)>1e-5||Mathf.Abs(mz.sqrMagnitude-1)>1e-5||Mathf.Abs(Vector3.Dot(mx,my))>1e-5||Mathf.Abs(Vector3.Dot(mx,mz))>1e-5||Mathf.Abs(Vector3.Dot(my,mz))>1e-5||Mathf.Abs(Basis.determinant+1)>1e-5)problem="M debe ser ortonormal con det=-1";
        else if(mode<0||mode>2||minimum.x>maximum.x||minimum.y>maximum.y||minimum.z>maximum.z)problem="Modo/sector inválido";
        else if(physicalVerified&&(measuredWidthMeters<=0||Mathf.Abs(measuredWidthMeters-declaredWidthMeters)>.001))problem="Calibracion fisica inconsistente";
        return problem==null;
    }
    static bool Finite(Vector3 v)=>StructuralRepository.Finite(v.x)&&StructuralRepository.Finite(v.y)&&StructuralRepository.Finite(v.z);
    public ARMarkerProfile Snapshot()=>JsonUtility.FromJson<ARMarkerProfile>(JsonUtility.ToJson(this));
}
