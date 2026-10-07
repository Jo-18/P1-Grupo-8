using System;
using System.Collections.Generic;
using UnityEngine;
public sealed class StructuralResultSampler {
    public static readonly string[] Names={"N","Vy","Vz","T","My","Mz"};
    public sealed class Diagram { public float[] X,Values; public float Initial,Final,Minimum,Maximum,Length; public string Origin="Extremos solver; interior reconstruido por equilibrio de cargas uniformes prescritas. Sin estaciones solver."; }
    readonly StructuralRepository repo;
    readonly Dictionary<string,Diagram> cache=new Dictionary<string,Diagram>();
    public StructuralResultSampler(StructuralRepository repository){repo=repository;}
    public bool TryAt(ElementData e,string c,float t,out float[] r,out ResultAvailability availability) {
        r=null;if(e==null){availability=ResultAvailability.Missing;return false;}
        if(!repo.TryForces(e.id,c,out var f,out availability))return false;
        float L=repo.Length(e);if(L<=1e-8f){availability=ResultAvailability.Invalid;return false;}
        var load=repo.Applied("elementUniformTotal",e.id,c);
        Vector3 perM=load==null?Vector3.zero:new Vector3(load.values[0],load.values[1],load.values[2])/L;
        r=EvaluateUniform(f,t,L,perM,repo.Point(e.nodeJ)-repo.Point(e.nodeI));return true;
    }
    public float UniformGravity(ElementData e,string c,float L) {
        var load=repo.Applied("elementUniformTotal",e.id,c);
        return load==null?0:-load.values[2]/L;
    }
    public static void Axes(Vector3 d,out Vector3 x,out Vector3 y,out Vector3 z) {
        if(d.sqrMagnitude<1e-16f)throw new ArgumentException("Longitud cero");
        x=d.normalized;y=Vector3.Cross(Mathf.Abs(x.z)>.90f?Vector3.right:Vector3.forward,x).normalized;z=Vector3.Cross(x,y);
    }
    public static float[] Evaluate(float[] f,float t,float L,float w,Vector3 direction) {
        return EvaluateUniform(f,t,L,new Vector3(0,0,-w),direction);
    }
    public static float[] EvaluateUniform(float[] f,float t,float L,Vector3 perM,Vector3 direction) {
        if(f==null||f.Length!=12)throw new ArgumentException("Se requieren doce acciones raw");
        t=Mathf.Clamp01(t);var r=new float[6];for(int k=0;k<6;k++)r[k]=Mathf.Lerp(-f[k],f[k+6],t);
        Axes(direction,out var x,out var y,out var z);
        Vector3 m=-L*L*t*(1-t)/2*Vector3.Cross(x,perM);
        r[4]+=Vector3.Dot(m,y);r[5]+=Vector3.Dot(m,z);return r;
    }
    public bool TryDiagram(ElementData e,string c,int component,out Diagram diagram,out ResultAvailability a) {
        diagram=null;if(component<0||component>5) {a=ResultAvailability.Invalid;return false;}
        if(!TryAt(e,c,0,out var i,out a)||!TryAt(e,c,1,out var j,out a)||!TryAt(e,c,.5f,out var mid,out a))return false;
        string key=e.id+":"+c+":"+component;
        if(cache.TryGetValue(key,out diagram))return true;
        // Quadratic extrema inserted exactly, in addition to drawing samples.
        float A=2*(j[component]+i[component]-2*mid[component]),B=j[component]-i[component]-A;
        var ts=new List<float>();for(int n=0;n<=40;n++)ts.Add(n/40f);
        if(Mathf.Abs(A)>1e-8f){float t=-B/(2*A);if(t>0&&t<1)ts.Add(t);}ts.Sort();
        diagram=new Diagram{Length=repo.Length(e),X=new float[ts.Count],Values=new float[ts.Count],Initial=i[component],Final=j[component],Minimum=float.PositiveInfinity,Maximum=float.NegativeInfinity};
        for(int n=0;n<ts.Count;n++){TryAt(e,c,ts[n],out var v,out a);diagram.X[n]=ts[n]*diagram.Length;diagram.Values[n]=v[component];diagram.Minimum=Mathf.Min(diagram.Minimum,v[component]);diagram.Maximum=Mathf.Max(diagram.Maximum,v[component]);}
        cache[key]=diagram;return true;
    }
    public bool TryPM(ElementData e,string c,out Vector2 demand) {
        demand=default;if(!repo.TryForces(e.id,c,out var f,out _))return false;
        // Same definition as capacidad_ha columns and Excel; no sign clamping.
        demand=new Vector2(.5f*(f[0]-f[6]),Mathf.Max(new Vector2(f[4],f[5]).magnitude,new Vector2(f[10],f[11]).magnitude));return true;
    }
}
