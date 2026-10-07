using System;
using UnityEngine;
/// Touch picking is independent of IMGUI. Hidden GameObjects have no active colliders.
public class StructuralSelectionController : MonoBehaviour {
    public LayerMask selectableLayers=1<<ARStructure.StructuralLayer;
    public ARElementTag Selected { get; private set; }
    public event Action Changed;
    ARStructure structure;
    void Start(){structure=GetComponent<ARStructure>();if(structure!=null)structure.Rebuilt+=Clear;}
    void OnDestroy(){if(structure!=null)structure.Rebuilt-=Clear;}
    public void Select(ARElementTag tag) {
        if(tag==null||tag.element==null||!tag.gameObject.activeInHierarchy){Clear();return;}
        if(structure==null)structure=GetComponent<ARStructure>();
        Selected=tag;if(structure!=null){structure.Selected=tag.element;structure.RefreshColors();}Changed?.Invoke();
    }
    public void Clear(){Selected=null;if(structure==null)structure=GetComponent<ARStructure>();if(structure!=null){structure.Selected=null;structure.RefreshColors();}Changed?.Invoke();}
    public bool Pick(Vector2 position) {
        if(ARInspectorUI.BlocksScreenPoint(position))return false;
        var cam=Camera.main;if(cam==null)return false;
        if(Physics.Raycast(cam.ScreenPointToRay(position),out var hit,300f,selectableLayers,QueryTriggerInteraction.Ignore)) {
            var tag=hit.collider.GetComponent<ARElementTag>();if(tag!=null){Select(tag);return true;}
        }return false;
    }
    void Update() {
        if(ARPointerInput.TryPress(out var position))Pick(position);
    }
    public void Navigate(int delta) {
        if(structure==null)return;var list=structure.VisibleElements();if(list.Count==0){Clear();return;}
        int index=Selected==null?-1:list.IndexOf(Selected);index=(index+delta+list.Count)%list.Count;Select(list[index]);
    }
    public bool Search(string query) {
        if(structure==null)return false;foreach(var tag in structure.VisibleElements()) {
            if(string.Equals(tag.element.elementTag,query,StringComparison.OrdinalIgnoreCase)||tag.element.id.ToString()==query||tag.wall!=null&&(string.Equals(tag.wall.elementTag,query,StringComparison.OrdinalIgnoreCase)||("MURO-"+tag.wall.id)==query)){Select(tag);return true;}
        }return false;
    }
    public void Isolate(){if(structure==null||Selected==null)return;structure.IsolatedId=Selected.element.id;structure.ApplyVisibility();}
    public void ShowAll(){if(structure==null)return;structure.IsolatedId=-1;structure.FloorFilter=structure.BuildingFilter="";structure.ShowBeams=structure.ShowColumns=structure.ShowWalls=structure.ShowBraces=true;structure.ApplyVisibility();}
}
