using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Semana 6 · Fase 3: dibuja la estructura (o el sector de la columna ancla) sobre el
/// anchor de la imagen, transformando coordenadas OpenSees -> AR.
///
///   p_AR (mundo) = T_anchor · ( s · M · (p_OpenSees − p_ref) )
///
///   p_OpenSees : nodo del modelo (x, y, z), z hacia arriba, metros.
///   p_ref      : punto del modelo que coincide con el centro de la imagen.
///   M          : cambio de ejes modelo -> ejes de la imagen (x derecha,
///                y normal saliendo de la imagen, z hacia el borde superior).
///                  marcador en la columna (vertical, normal n de la cara):
///                    (d·r, d·n, dz) con r = (−n) × z  (derecha de quien mira)
///                    cara −Y: (dx, −dy, dz) · cara +X: (dy, dx, dz)
///                  marcador en la mesa (horizontal):  (dx,  dz, dy)
///                Ambos tienen det = −1: pasan de un sistema de mano derecha
///                (OpenSees) a uno de mano izquierda (Unity), igual que el
///                viewer (x, z, y).
///   s          : escala (1 = 1:1, 0.01 = maqueta 1:100).
///   T_anchor   : pose del ARAnchor (rotacion + traslacion en el mundo AR),
///                la calcula ARCore en el telefono.
/// </summary>
public class ARStructure : MonoBehaviour
{
    public enum Mode { Columna1a1, Maqueta100, SobrePlano }

    public const string AnchorTag = "E1_243";
    /// Elementos revisados en detalle: siempre se dibujan (tambien fuera del sector en 1:1) y tienen acceso directo.
    /// E1_72 es la viga de borde del voladizo, en el cielo de la sala de la demo.
    public static readonly string[] FeaturedTags = { "E1_243", "E1_72" };

    // Sala de la demo: voladizo sur del edificio 1, sobre las losas L22, L23 y L95 de
    // CIELO_1 (x 0..7,51, y -11,37..0, piso z = 3,96). Marcador pegado en la cara +X
    // (hacia la sala) de la columna E1_243 (x = 0, y = -7,25, COL70/70), con su centro
    // a 1,20 m del piso terminado.
    public static readonly Vector3 MarkerOnColumn = new Vector3(0.35f, -7.25f, 3.96f + 1.20f);
    public static readonly Vector3 MarkerFaceNormal = new Vector3(1f, 0f, 0f);   // normal saliente de la cara (modelo)
    public const float SectorXMin = -1f, SectorXMax = 8.5f, SectorYMin = -12f, SectorYMax = 0.5f;
    public const float SectorZMin = 3.96f, SectorZMax = 7.92f;

    // Dibujo de la planta en el marcador (mismos parametros que scripts/generar_marcador_ar.py)
    private const float MarkerPx = 1600f, PlanMarginTop = 230f, PlanMargin = 110f, PlanBottomBand = 160f;

    public Mode mode = Mode.Maqueta100;
    public bool ShowBeams=true, ShowColumns=true, ShowWalls=true, ShowBraces=true, ShowIds;
    public string FloorFilter="", BuildingFilter="";
    public int IsolatedId=-1;
    public const int StructuralLayer=8;
    public readonly List<ARElementTag> Elements=new List<ARElementTag>();
    private readonly List<ARElementTag> visibleElements=new List<ARElementTag>();
    public Transform SupportRoot { get; private set; }
    public Transform AxesRoot { get; private set; }
    private ARImageAnchor subscribedAnchor;
    private readonly Dictionary<int,Transform> tagLabels=new Dictionary<int,Transform>();
    private Material matWall;
    public static ARStructure Instance { get; private set; }
    public Transform ModelRoot { get; private set; }
    public float Scale { get; private set; } = 1f;
    public Vector3 RefPoint { get; private set; }
    public ElementData Selected { get; set; }
    public event System.Action Rebuilt;

    private readonly Dictionary<int, NodeData> nodes = new Dictionary<int, NodeData>();
    private readonly Dictionary<int, Renderer> renderers = new Dictionary<int, Renderer>();
    private readonly List<Transform> labels = new List<Transform>();
    private Transform contentRoot;
    private Font labelFont;
    private Material matColumn, matBeam, matBrace, matAnchor, matSelected;
    private Vector2 planCenter;
    private float planScale;   // m de dibujo por m de modelo (modo SobrePlano)

    private void Awake()
    {
        Instance = this;
    }

    private void Start()
    {
        LoadModel();
        subscribedAnchor=ARImageAnchor.Instance;
        if (subscribedAnchor != null) {
            subscribedAnchor.Anchored += OnAnchored;
            if(subscribedAnchor.ContentRoot!=null)OnAnchored(subscribedAnchor.ContentRoot);
        }
    }

    private void LoadModel()
    {
        if (UnityData.Structure == null)
        {
            var json = Resources.Load<TextAsset>("estructura_p1l4_unity");
            if (json == null) { Debug.LogError("[ARStructure] Falta Resources/estructura_p1l4_unity.json"); return; }
            UnityData.LoadData(JsonUtility.FromJson<StructureData>(json.text));
        }
        if(UnityData.Repository==null || !UnityData.Repository.ContractValid) {Debug.LogError("[ARStructure] Contrato inválido; no construir geometría");return;}
        nodes.Clear();
        float xmin = float.MaxValue, xmax = float.MinValue, ymin = float.MaxValue, ymax = float.MinValue;
        foreach (NodeData n in UnityData.Structure.nodes)
        {
            nodes[n.id] = n;
            xmin = Mathf.Min(xmin, n.x); xmax = Mathf.Max(xmax, n.x);
            ymin = Mathf.Min(ymin, n.y); ymax = Mathf.Max(ymax, n.y);
        }
        // misma escala y centro del dibujo que generar_marcador_ar.py
        float sx = (MarkerPx - 2f * PlanMargin) / (xmax - xmin);
        float sy = (MarkerPx - PlanMarginTop - PlanMargin - PlanBottomBand) / (ymax - ymin);
        float pxPerM = Mathf.Min(sx, sy);
        planScale = pxPerM * ARSetupConstants.MarkerWidth / MarkerPx;
        float planCenterPxY = PlanMarginTop + (MarkerPx - PlanMarginTop - PlanMargin - PlanBottomBand) / 2f;
        // el centro de la planta queda (MarkerPx/2 − planCenterPxY) px sobre el centro de la imagen
        float upOffsetM = (MarkerPx / 2f - planCenterPxY) / pxPerM;
        planCenter = new Vector2((xmax + xmin) / 2f, (ymax + ymin) / 2f - upOffsetM);

        labelFont = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        Shader lit = Shader.Find("Standard") ?? Shader.Find("Unlit/Color");
        matColumn = new Material(lit) { color = Paleta.ARPilar };
        matBeam = new Material(lit) { color = Paleta.ARViga };
        matBrace = new Material(lit) { color = Paleta.ARArriostre };
        matAnchor = new Material(lit) { color = Paleta.ARAncla };
        matSelected = new Material(lit) { color = Paleta.Seleccion };
        matWall = new Material(lit) { color = new Color(.65f,.72f,.82f) };
    }

    private void OnAnchored(Transform root)
    {
        contentRoot = root;
        Rebuild();
    }

    public void SetMode(Mode m)
    {
        if (mode == m && ModelRoot != null) return;
        mode = m;
        Rebuild();
    }

    /// Cambio de ejes M (modelo -> ejes de la imagen), sin escala.
    public Vector3 AxesToImage(Vector3 d)
    {
        var p=ARImageAnchor.Instance?.HonorsProfile;if(p!=null && mode==Mode.Columna1a1)return new HonorsMarkerTransform(p).Direction(d);
        return new ModelCoordinateTransform(1,Vector3.zero,mode==Mode.Columna1a1).Direction(d);
    }

    /// Punto del modelo (OpenSees) -> coordenadas locales del anchor: s · M · (p − p_ref).
    public Vector3 ModelToAnchor(Vector3 p)
    {
        var profile=ARImageAnchor.Instance?.HonorsProfile;if(profile!=null && mode==Mode.Columna1a1)return Scale*new HonorsMarkerTransform(profile).Direction(p-RefPoint);
        return new ModelCoordinateTransform(Scale,RefPoint,mode==Mode.Columna1a1).Forward(p);
    }

    /// Direccion vertical del modelo (+z OpenSees) en ejes de la imagen.
    public Vector3 ModelUpLocal => AxesToImage(new Vector3(0f, 0f, 1f));

    public Vector3 NodePos(int id)
    {
        NodeData n = nodes[id];
        return new Vector3(n.x, n.y, n.z);
    }

    public bool InSector(ElementData e)
    {
        var profile=ARImageAnchor.Instance?.HonorsProfile;
        if(profile!=null && mode==Mode.Columna1a1){if(!profile.sector)return true;foreach(var id in new[]{e.nodeI,e.nodeJ}){var p=NodePos(id);var lo=profile.minimum;var hi=profile.maximum;if(p.x<lo.x-.01f||p.x>hi.x+.01f||p.y<lo.y-.01f||p.y>hi.y+.01f||p.z<lo.z-.01f||p.z>hi.z+.01f)return false;}return true;}
        foreach (int id in new[] { e.nodeI, e.nodeJ })
        {
            NodeData n = nodes[id];
            if (n.x < SectorXMin - 0.01f || n.x > SectorXMax + 0.01f || n.y < SectorYMin - 0.01f || n.y > SectorYMax + 0.01f ||
                n.z < SectorZMin - 0.01f || n.z > SectorZMax + 0.01f) return false;
        }
        return true;
    }

    public void Rebuild()
    {
        if (contentRoot == null || UnityData.Structure == null) return;
        if(UnityData.Repository==null || !UnityData.Repository.ContractValid) {GetComponent<StructuralSelectionController>()?.Clear();if(ModelRoot!=null)ModelRoot.gameObject.SetActive(false);return;}
        GetComponent<StructuralSelectionController>()?.Clear();
        if (ModelRoot != null) {
            foreach(var line in ModelRoot.GetComponentsInChildren<LineRenderer>(true))if(line.sharedMaterial!=null)Destroy(line.sharedMaterial);
            ModelRoot.gameObject.SetActive(false); Destroy(ModelRoot.gameObject);
        }
        renderers.Clear();
        labels.Clear();
        tagLabels.Clear();Elements.Clear();Selected=null;IsolatedId=-1;

        switch (mode)
        {
            case Mode.Columna1a1: Scale = 1f; RefPoint = MarkerOnColumn; break;
            case Mode.Maqueta100: Scale = 0.01f; RefPoint = new Vector3(planCenter.x, planCenter.y, 0f); break;
            default: Scale = planScale; RefPoint = new Vector3(planCenter.x, planCenter.y, 0f); break;
        }
        var profile=ARImageAnchor.Instance?.HonorsProfile;if(profile!=null && mode==Mode.Columna1a1){RefPoint=profile.reference;} // Registration never chooses visualization mode.

        ModelRoot = new GameObject("Modelo AR (" + mode + ")").transform;
        ModelRoot.SetParent(contentRoot, false);

        bool sectorOnly = mode == Mode.Columna1a1;
        // seccion minima visible: en maqueta las vigas de 0,6 m quedarian de 6 mm o menos
        float minSection = mode == Mode.Columna1a1 ? 0f : 0.003f;
        foreach (ElementData e in UnityData.Structure.elements)
        {
            if (!nodes.ContainsKey(e.nodeI) || !nodes.ContainsKey(e.nodeJ)) continue;
            if (UnityData.IsAnalysisOnly(e)) continue;
            bool featured = System.Array.IndexOf(FeaturedTags, e.elementTag) >= 0;
            if (sectorOnly && !InSector(e) && !featured) continue;
            Vector3 a = ModelToAnchor(NodePos(e.nodeI));
            Vector3 b = ModelToAnchor(NodePos(e.nodeJ));
            float w = Mathf.Max(minSection, Scale * Mathf.Max(0.15f, e.width_m));
            float h = Mathf.Max(minSection, Scale * Mathf.Max(0.15f, e.height_m));
            if (mode == Mode.SobrePlano) { w = Mathf.Max(w, 0.0025f); h = Mathf.Max(h, 0.0025f); }
            Renderer r = MakeBar(e, a, b, w, h);
            renderers[e.id] = r;

            bool isAnchor = e.elementTag == AnchorTag;
            {
                float textH = sectorOnly ? 0.12f : 0.006f;
                AddLabel(e.elementTag, (a + b) * 0.5f + ModelUpLocal * textH * 0.6f, textH, isAnchor);
                tagLabels[e.id]=labels[labels.Count-1];
            }
        }
        var repo=UnityData.Repository;
        if(repo!=null && repo.ContractValid)foreach(var wall in UnityData.Structure.walls??System.Array.Empty<WallData>()) {
            if(!repo.Walls.TryGetValue(wall.id,out var mapping))continue;
            var e=repo.Elements[mapping.analyticalId];
            if(sectorOnly && !InSector(e))continue;
            Vector3 i=repo.Point(wall.nodeI),j=repo.Point(wall.nodeJ);i.z=j.z=mapping.bottomZ;
            Vector3 a=ModelToAnchor(i),b=ModelToAnchor(j);
            Vector3 center=(a+b)/2+ModelUpLocal*Scale*(mapping.topZ-mapping.bottomZ)/2;
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=wall.elementTag+" -> "+e.elementTag;
            go.layer=StructuralLayer;go.transform.SetParent(ModelRoot,false);go.transform.localPosition=center;
            go.transform.localRotation=Quaternion.LookRotation((b-a).normalized,ModelUpLocal);
            go.transform.localScale=new Vector3(Scale*wall.grosor,Scale*(mapping.topZ-mapping.bottomZ),(b-a).magnitude);
            var tag=go.AddComponent<ARElementTag>();tag.element=e;tag.wall=wall;tag.mapping=mapping;Elements.Add(tag);
            renderers[e.id]=go.GetComponent<Renderer>();
            AddLabel(wall.elementTag,center,sectorOnly?.12f:.006f,false);tagLabels[e.id]=labels[labels.Count-1];
        }
        BuildAuxiliaryLayers();
        ApplyVisibility();
        RefreshColors();
        Rebuilt?.Invoke();
    }

    private Renderer MakeBar(ElementData e, Vector3 a, Vector3 b, float w, float h)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = e.elementTag;
        go.layer=StructuralLayer;
        go.transform.SetParent(ModelRoot, false);
        Vector3 d = b - a;
        float len = d.magnitude;
        go.transform.localPosition = (a + b) * 0.5f;
        if (len > 1e-6f)
        {
            // alto de la seccion en la vertical del modelo; en columnas, el ancho segun +x del modelo
            Vector3 up = Mathf.Abs(Vector3.Dot(d / len, ModelUpLocal)) > 0.95f ? AxesToImage(Vector3.right) : ModelUpLocal;
            go.transform.localRotation = Quaternion.LookRotation(d / len, up);
        }
        go.transform.localScale = new Vector3(w, h, len);
        var tag=go.AddComponent<ARElementTag>();tag.element=e;Elements.Add(tag);
        return go.GetComponent<Renderer>();
    }

    private void AddLabel(string text, Vector3 localPos, float height, bool highlight)
    {
        var go = new GameObject("Tag " + text);
        go.transform.SetParent(ModelRoot, false);
        go.transform.localPosition = localPos;
        var tm = go.AddComponent<TextMesh>();
        tm.text = text;
        tm.font = labelFont;
        tm.fontSize = 64;
        tm.characterSize = height / 6.4f;   // alto aprox. de la letra = characterSize * fontSize / 10
        tm.anchor = TextAnchor.LowerCenter;
        tm.color = highlight ? Paleta.AREtiquetaDestacada : Color.white;
        go.GetComponent<MeshRenderer>().material = labelFont.material;
        labels.Add(go.transform);
    }

    public void RefreshColors()
    {
        foreach (var kv in renderers)
        {
            ElementData e = kv.Value.GetComponent<ARElementTag>().element;
            Material m = e == Selected ? matSelected
                : e.elementTag == AnchorTag ? matAnchor
                : e.type == "muro" ? matWall
                : e.type == "columna" ? matColumn
                : e.type == "viga" ? matBeam : matBrace;
            kv.Value.sharedMaterial = m;
        }
    }

    public ElementData FindByTag(string tag)
    {
        if (UnityData.Structure == null) return null;
        foreach (ElementData e in UnityData.Structure.elements) if (e.elementTag == tag) return e;
        return null;
    }

    private void LateUpdate()
    {
        // etiquetas siempre mirando a la camara
        Camera cam = Camera.main;
        if (cam == null) return;
        foreach (Transform t in labels)
        {
            if (t != null && t.gameObject.activeInHierarchy) t.rotation = Quaternion.LookRotation(t.position - cam.transform.position, cam.transform.up);
        }
    }
    public void ApplyVisibility() {
        visibleElements.Clear();
        foreach(var tag in Elements) {
            var e=tag.element;
            bool type=e.type=="viga"?ShowBeams:e.type=="columna"?ShowColumns:e.type=="muro"?ShowWalls:ShowBraces;
            bool visible=type&&(string.IsNullOrEmpty(FloorFilter)||e.piso==FloorFilter)&&(string.IsNullOrEmpty(BuildingFilter)||e.sourceBuilding==BuildingFilter)&&(IsolatedId<0||e.id==IsolatedId);
            tag.gameObject.SetActive(visible);
            if(visible)visibleElements.Add(tag);
            if(tagLabels.TryGetValue(e.id,out var label))label.gameObject.SetActive(visible&&ShowIds);
        }
        visibleElements.Sort((a,b)=>a.element.id.CompareTo(b.element.id));
        var selection=GetComponent<StructuralSelectionController>();
        if(selection!=null && selection.Selected!=null && !selection.Selected.gameObject.activeInHierarchy)selection.Clear();
    }
    public List<ARElementTag> VisibleElements() => visibleElements;
    void BuildAuxiliaryLayers() {
        SupportRoot=new GameObject("Apoyos (restricciones, no fuerzas)").transform;SupportRoot.SetParent(ModelRoot,false);
        foreach(var s in UnityData.Structure.supports??System.Array.Empty<SupportData>()) {
            if(!nodes.ContainsKey(s.node))continue;var go=PrimitiveGeometry.CreateSphere();go.transform.SetParent(SupportRoot,false);go.transform.localPosition=ModelToAnchor(NodePos(s.node));go.transform.localScale=Vector3.one*(mode==Mode.Columna1a1?.12f:.003f);Destroy(go.GetComponent<Collider>());go.GetComponent<Renderer>().sharedMaterial=matAnchor;
        }SupportRoot.gameObject.SetActive(false);
        AxesRoot=new GameObject("Ejes del plano").transform;AxesRoot.SetParent(ModelRoot,false);
        foreach(var axis in UnityData.Structure.ejesGrilla??System.Array.Empty<EjeGrillaData>()) {
            Vector3 a=axis.direccion=="y"?new Vector3(axis.coord,axis.desde,0):new Vector3(axis.desde,axis.coord,0);
            Vector3 b=axis.direccion=="y"?new Vector3(axis.coord,axis.hasta,0):new Vector3(axis.hasta,axis.coord,0);
            ARImageAnchor.Line(AxesRoot,axis.nombre,Color.white,mode==Mode.Columna1a1?.008f:.0007f,false,ModelToAnchor(a),ModelToAnchor(b));
        }AxesRoot.gameObject.SetActive(false);
    }
    void OnDestroy() {
        if(subscribedAnchor!=null)subscribedAnchor.Anchored-=OnAnchored;
        if(Instance==this)Instance=null;
        foreach(var m in new[]{matColumn,matBeam,matBrace,matAnchor,matSelected,matWall})if(m!=null)Destroy(m);
    }
}

/// Une cada barra dibujada con su ElementData (id y elementTag de OpenSees).
public class ARElementTag : MonoBehaviour
{
    public ElementData element;
    public WallData wall;
    public WallMapping mapping;
}

/// Constantes compartidas con el editor (ARSetup.MarkerWidth).
public static class ARSetupConstants
{
    public const float MarkerWidth = 0.20f;
}
