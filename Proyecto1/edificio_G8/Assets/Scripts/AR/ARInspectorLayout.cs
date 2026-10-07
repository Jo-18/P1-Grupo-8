using UnityEngine;
public static class ARInspectorLayout {
    public static void Calculate(int width,int height,float dpi,Rect safeArea,bool collapsed,out float scale,out Rect safe,out Rect header,out Rect panel){
        scale=Mathf.Clamp(dpi>0?dpi/160f:width/430f,1,3);
        safe=new Rect(safeArea.x/scale,(height-safeArea.yMax)/scale,safeArea.width/scale,safeArea.height/scale);
        header=new Rect(safe.x+6,safe.y+6,Mathf.Max(1,safe.width-12),58);
        bool portrait=safe.height>safe.width;
        float w=portrait?safe.width-12:Mathf.Min(430,safe.width*.48f);
        float h=collapsed?64:portrait?Mathf.Min(safe.height*.66f,safe.height-78):safe.height-78;
        panel=new Rect(safe.xMax-w-6,safe.yMax-h-6,w,h);
    }
}
