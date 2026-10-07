using System;
using UnityEngine;
// Axes are computed in MODEL coordinates, before handedness reflection.
public static class ARDiagramGeometry {
    public static Vector3[] Build(Vector3 a,Vector3 b,StructuralResultSampler.Diagram d,int component,float gain,Func<Vector3,Vector3> transform){
        if(component!=4&&component!=2)throw new ArgumentException("H3 supports My/Vz only");
        if(d?.X==null||d.Values==null||d.X.Length!=d.Values.Length||d.Length<=0||!StructuralRepository.Finite(gain)||gain<=0)throw new ArgumentException("Invalid diagram geometry");
        StructuralResultSampler.Axes(b-a,out _,out _,out var z);
        var points=new Vector3[d.X.Length];
        for(int i=0;i<points.Length;i++){
            if(!StructuralRepository.Finite(d.X[i])||!StructuralRepository.Finite(d.Values[i]))throw new ArgumentException("Nonfinite result");
            points[i]=transform(a+(d.X[i]/d.Length)*(b-a)+gain*d.Values[i]*z);
        }
        return points;
    }
    public static string Unavailable(ResultAvailability state)=>state==ResultAvailability.Partial?"No disponible: resultado parcial.":state==ResultAvailability.Invalid?"No disponible: resultado inválido.":"No disponible en datos exportados.";
}
