using System.Collections.Generic;
using UnityEngine;
// Rasterized local coordinates: DrawTexture respects enclosing scroll/group clips.
public static class ARDiagramPanel {
    sealed class Entry {public object source;public Vector2? demand;public int w,h;public Texture2D texture;}
    static readonly List<Entry> cache=new List<Entry>();
    public static void ClearCache(){foreach(var e in cache)Release(e.texture);cache.Clear();}
    static void Release(Texture2D t){if(Application.isPlaying)Object.Destroy(t);else Object.DestroyImmediate(t);}
    public static void Draw(Rect area,StructuralResultSampler.Diagram d)=>DrawPlot(area,d,ARPlotGeometry.DiagramPoints(d),null);
    public static void DrawPM(Rect area,PMCurveData c,Vector2 demand)=>DrawPlot(area,c,ARPlotGeometry.PMPoints(c),new Vector2(demand.y,demand.x));
    static void DrawPlot(Rect area,object source,Vector2[] data,Vector2? demand){
        GUI.Box(area,GUIContent.none);if(Event.current.type!=EventType.Repaint)return;
        Rect plot=ARPlotGeometry.Interior(area);
        int w=Mathf.Clamp(Mathf.CeilToInt(plot.width*2),128,1536),h=Mathf.Clamp(Mathf.CeilToInt(plot.height*2),128,768);
        var found=cache.Find(e=>ReferenceEquals(e.source,source)&&e.w==w&&e.h==h&&e.demand==demand);
        if(found==null){
            found=new Entry{source=source,w=w,h=h,demand=demand,texture=Rasterize(data,demand,w,h)};
            if(cache.Count>=8){Release(cache[0].texture);cache.RemoveAt(0);}cache.Add(found);
        }
        GUI.BeginGroup(plot);
        try{Color old=GUI.color;GUI.color=Color.white;GUI.DrawTexture(new Rect(0,0,plot.width,plot.height),found.texture,ScaleMode.StretchToFill);GUI.color=old;}
        finally{GUI.EndGroup();}
    }
    public static Texture2D Rasterize(Vector2[] data,Vector2? demand,int w,int h){
        var bounds=ARPlotGeometry.Fit(data,demand);var rect=new Rect(5,5,w-11,h-11);
        var pixels=new Color32[w*h];for(int i=0;i<pixels.Length;i++)pixels[i]=new Color32(22,27,34,255);
        System.Action<int,int,Color32> pixel=(x,y,c)=>{if(x>=0&&y>=0&&x<w&&y<h)pixels[(h-1-y)*w+x]=c;};
        System.Action<Vector2,Vector2,Color32,int> line=(a,b,c,r)=>{
            int steps=Mathf.Max(1,Mathf.CeilToInt(Mathf.Max(Mathf.Abs(a.x-b.x),Mathf.Abs(a.y-b.y))));
            for(int i=0;i<=steps;i++){var p=Vector2.Lerp(a,b,(float)i/steps);for(int dx=-r;dx<=r;dx++)for(int dy=-r;dy<=r;dy++)pixel(Mathf.RoundToInt(p.x)+dx,Mathf.RoundToInt(p.y)+dy,c);}
        };
        Color32 grey=new Color32(120,125,135,255),cyan=new Color32(51,191,255,255);
        line(bounds.Map(new Vector2(bounds.xmin,0),rect),bounds.Map(new Vector2(bounds.xmax,0),rect),grey,0);
        line(bounds.Map(new Vector2(0,bounds.ymin),rect),bounds.Map(new Vector2(0,bounds.ymax),rect),grey,0);
        for(int i=1;i<data.Length;i++)line(bounds.Map(data[i-1],rect),bounds.Map(data[i],rect),cyan,1);
        if(demand.HasValue){var p=bounds.Map(demand.Value,rect);line(p,p,new Color32(255,220,0,255),4);}
        var texture=new Texture2D(w,h,TextureFormat.RGBA32,false){name="AR plot (clipped)",hideFlags=HideFlags.HideAndDontSave,filterMode=FilterMode.Bilinear,wrapMode=TextureWrapMode.Clamp};
        texture.SetPixels32(pixels);texture.Apply(false,false);return texture;
    }
}
