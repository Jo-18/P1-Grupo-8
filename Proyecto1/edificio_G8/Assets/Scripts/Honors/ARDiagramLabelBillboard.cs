using UnityEngine;
// Only label orientation follows the rendering camera. Sampled line geometry
// remains event-driven and fixed in the model/anchor coordinates.
public sealed class ARDiagramLabelBillboard : MonoBehaviour {
    void OnWillRenderObject(){if(Camera.current!=null)transform.rotation=Camera.current.transform.rotation;}
}
