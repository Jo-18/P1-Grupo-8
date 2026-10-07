using System;
using UnityEngine;
/// Local raster for two curves with a shared fit and the selected element's point.
public static class HonorsCapacityPlot {
    public static ARPlotGeometry.Bounds Bounds(PMCurveData before,PMCurveData after,Vector2? demand){
        var a=ARPlotGeometry.PMPoints(before);var b=after==null?Array.Empty<Vector2>():ARPlotGeometry.PMPoints(after);var both=new Vector2[a.Length+b.Length];a.CopyTo(both,0);b.CopyTo(both,a.Length);
        return ARPlotGeometry.Fit(both,demand.HasValue?new Vector2(demand.Value.y,demand.Value.x):(Vector2?)null);
    }
    public static Texture2D Render(PMCurveData before,PMCurveData after,Vector2? demand,int w=800,int h=500){
        var bounds=Bounds(before,after,demand);var plot=new Rect(6,6,w-13,h-13);var pixels=new Color32[w*h];for(int i=0;i<pixels.Length;i++)pixels[i]=new Color32(22,27,34,255);
        Action<Vector2,Vector2,Color32,int> line=(a,b,color,r)=>{
            int steps=Mathf.Max(1,Mathf.CeilToInt(Mathf.Max(Mathf.Abs(a.x-b.x),Mathf.Abs(a.y-b.y))));
            for(int i=0;i<=steps;i++){var p=Vector2.Lerp(a,b,(float)i/steps);for(int dx=-r;dx<=r;dx++)for(int dy=-r;dy<=r;dy++){int x=Mathf.RoundToInt(p.x)+dx,y=Mathf.RoundToInt(p.y)+dy;if(x>=0&&y>=0&&x<w&&y<h)pixels[(h-1-y)*w+x]=color;}}
        };
        var grey=new Color32(110,115,130,255);
        line(bounds.Map(new Vector2(bounds.xmin,0),plot),bounds.Map(new Vector2(bounds.xmax,0),plot),grey,0);line(bounds.Map(new Vector2(0,bounds.ymin),plot),bounds.Map(new Vector2(0,bounds.ymax),plot),grey,0);
        Action<PMCurveData,Color32> curve=(c,color)=>{var points=ARPlotGeometry.PMPoints(c);for(int i=1;i<points.Length;i++)line(bounds.Map(points[i-1],plot),bounds.Map(points[i],plot),color,1);};
        curve(before,new Color32(51,191,255,255));if(after!=null)curve(after,new Color32(255,149,40,255));
        if(demand.HasValue){var p=bounds.Map(new Vector2(demand.Value.y,demand.Value.x),plot);line(p,p,new Color32(255,220,0,255),4);}
        var t=new Texture2D(w,h,TextureFormat.RGBA32,false){name="H5 selected comparison",hideFlags=HideFlags.HideAndDontSave,wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};t.SetPixels32(pixels);t.Apply(false,false);return t;
    }
}
