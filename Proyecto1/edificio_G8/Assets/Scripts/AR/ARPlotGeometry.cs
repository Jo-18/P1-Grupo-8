using System;
using UnityEngine;
// Pure data -> local GUI coordinates; padding never changes structural data.
public static class ARPlotGeometry {
    public struct Bounds {
        public float xmin,xmax,ymin,ymax;
        public Vector2 Map(Vector2 v,Rect r)=>new Vector2(r.x+(v.x-xmin)/(xmax-xmin)*r.width,r.yMax-(v.y-ymin)/(ymax-ymin)*r.height);
    }
    public static Rect Interior(Rect r)=>new Rect(r.x+12,r.y+12,Mathf.Max(1,r.width-24),Mathf.Max(1,r.height-24));
    public static bool Finite(float v)=>!float.IsNaN(v)&&!float.IsInfinity(v);
    public static Bounds Fit(Vector2[] data,Vector2? demand=null){
        if(data==null||data.Length<2)throw new ArgumentException("Insufficient plot points");
        float xmin=0,xmax=0,ymin=0,ymax=0;
        foreach(var v in data)Accumulate(v,ref xmin,ref xmax,ref ymin,ref ymax);
        if(demand.HasValue)Accumulate(demand.Value,ref xmin,ref xmax,ref ymin,ref ymax);
        Pad(ref xmin,ref xmax);Pad(ref ymin,ref ymax);
        return new Bounds{xmin=xmin,xmax=xmax,ymin=ymin,ymax=ymax};
    }
    static void Accumulate(Vector2 v,ref float xmin,ref float xmax,ref float ymin,ref float ymax){
        if(!Finite(v.x)||!Finite(v.y))throw new ArgumentException("Nonfinite plot data");
        xmin=Mathf.Min(xmin,v.x);xmax=Mathf.Max(xmax,v.x);ymin=Mathf.Min(ymin,v.y);ymax=Mathf.Max(ymax,v.y);
    }
    static void Pad(ref float min,ref float max){
        float range=max-min,pad=range>1e-7f?range*.075f:Mathf.Max(1f,Mathf.Abs(min)*.075f);min-=pad;max+=pad;
    }
    public static Vector2[] DiagramPoints(StructuralResultSampler.Diagram d){
        if(d?.X==null||d.Values==null||d.X.Length!=d.Values.Length)throw new ArgumentException("Invalid diagram");
        var p=new Vector2[d.X.Length];for(int i=0;i<p.Length;i++)p[i]=new Vector2(d.X[i],d.Values[i]);return p;
    }
    public static Vector2[] PMPoints(PMCurveData c){
        if(c?.points==null)throw new ArgumentException("Missing P-M curve");
        var p=new Vector2[c.points.Length];for(int i=0;i<p.Length;i++)p[i]=new Vector2(c.points[i].M_kN_m,c.points[i].P_kN);return p;
    }
}
