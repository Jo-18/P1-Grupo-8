using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace LabViewer
{
    /// <summary>
    /// Construye la escena a partir del paquete autocontenido que YACE en
    /// StreamingAssets/lab_data (manifest + placement + geometry + tributary +
    /// results). Solo LEE datos; no ejecuta analisis ni inventa resultados.
    /// </summary>
    public class LabLoader : MonoBehaviour
    {
        public LabModel Model;

        public string DataFolder = "lab_data";

        private const string DIAF_COLOR_HEX = "#7F9FFF";
        private const string LOSA_COLOR_HEX = "#BFBFBF";
        private const string VIGA_COLOR_HEX = "#E67E22";
        private const string COL_COLOR_HEX = "#3498DB";
        private const string MURO_COLOR_HEX = "#95A5A6";
        private const string ABER_COLOR_HEX = "#E74C3C";
        private const string PENDIENTE_COLOR_HEX = "#FFAA00";
        // Marcador de "Referencias pendientes": registros solo con posicion de rotulo de
        // texto (RLE-TEXTO-1/P.M.I.) sin geometria fisica respaldada.
        private const string REF_COLOR_HEX = "#9B59B6";

        private readonly Dictionary<string, float> _storyHeight = new Dictionary<string, float>();
        private readonly Dictionary<string, TribData> _tribByBeam = new Dictionary<string, TribData>();
        // Regiones tributarias REALES (celdas del reparto geometrico) por nivel/receptor:
        // _tribRegions[level][receptorID] = lista de TribRegion.
        private readonly Dictionary<string, Dictionary<string, List<TribRegion>>> _tribRegions =
            new Dictionary<string, Dictionary<string, List<TribRegion>>>();
        // Tramos de columna REALES del modelo FE del Edificio I (ejecucion primaria):
        // (u, v, topNivel, baseY, topY, esHipotesisBase). Se usan para dibujar las columnas
        // desde el nodo inicial al final en vez de fabricar la altura del ultimo nivel.
        // esHipotesisBase marca los tramos hipoteticos base->_nivel del modelo FE (llevan la
        // carga a cimentacion en posiciones cuya columna documentada mas baja es ese nivel);
        // esos NO representan una columna de entrepiso verificada y se excluyen del dibujo.
        private readonly List<(float u, float v, string topNivel, float baseY, float topY, bool esHipotesisBase)> _colTramosEI =
            new List<(float, float, string, float, float, bool)>();

        public bool Load()
        {
            Model = new LabModel();
            string root = Path.Combine(Application.streamingAssetsPath, DataFolder);
            if (!Directory.Exists(root)) { Debug.LogError("No existe paquete de datos: " + root); return false; }

            LoadPlacement(Path.Combine(root, "placement.json"));
            LoadResultsAndTributary(Path.Combine(root, "edificios", "I", "tributary", "por_viga.json"));
            LoadTributaryRegions(Path.Combine(root, "edificios", "I", "tributary", "regiones_tributarias.json"));
            LoadResultsSummary(Path.Combine(root, "edificios", "I", "results", "primera_ejecucion.json"));

            var ei = new List<(string lvl, string file)>
            {
                ("CP1S", "edificios/I/geometry/CP1S.json"),
                ("P1",   "edificios/I/geometry/P1.json"),
                ("P2",   "edificios/I/geometry/P2.json"),
                ("P3",   "edificios/I/geometry/P3.json"),
                ("P4",   "edificios/I/geometry/P4.json"),
            };
            var eii = new List<(string lvl, string file)>
            {
                ("EII_CP1S", "edificios/II/geometry/EII_CP1S.json"),
                ("EII_CP1", "edificios/II/geometry/EII_CP1.json"),
                ("EII_CP2", "edificios/II/geometry/EII_CP2.json"),
                ("EII_CP3", "edificios/II/geometry/EII_CP3.json"),
                ("EII_CP4", "edificios/II/geometry/EII_CP4.json"),
            };

            var rootGO = new GameObject("Lab");
            BuildBuilding(rootGO.transform, "I", ei, root);
            BuildBuilding(rootGO.transform, "II", eii, root);
            return true;
        }

        private void LoadPlacement(string path)
        {
            if (!File.Exists(path)) return;
            object parsed = Json.Parse(File.ReadAllText(path));
            var d = parsed as Dictionary<string, object>;
            if (d == null) return;
            Model.PlacementDatoNecesario = Json.Str(d, "dato_necesario_para_resolver");
            // La colocacion global es PROVISIONAL (separacion de comparacion, NO es la
            // junta fisica real). Se refleja en el visor para no presentarla como real.
            string coloc = Json.Str(d, "colocacion_global");
            Model.GlobalPlacementProvisional = !string.IsNullOrEmpty(coloc) &&
                                               coloc.ToLowerInvariant().Contains("provisional");
            Model.NoUnionEstructural = Json.Bool(d, "no_union_estructural", false);
            if (d.TryGetValue("junta", out var jo) && jo is Dictionary<string, object> j)
            {
                Model.JuntaId = Json.Str(j, "id");
                Model.JuntaAnchoM = Json.Num(j, "ancho_m").ToString("0.###");
                Model.JuntaEstado = Json.Str(j, "estado");
            }
            if (d.TryGetValue("edificios", out var eo) && eo is Dictionary<string, object> eds)
            {
                foreach (var kv in eds)
                {
                    var cfg = kv.Value as Dictionary<string, object>;
                    if (cfg == null) continue;
                    Vector3 pos = Vector3.zero;
                    var parr = Json.Arr(cfg, "posicion_unity");
                    if (parr != null && parr.Count >= 3)
                        pos = new Vector3((float)Json.ToNum(parr[0]), (float)Json.ToNum(parr[1]), (float)Json.ToNum(parr[2]));
                    Model.Placement[kv.Key] = pos;
                    Model.PlacementRot[kv.Key] = Quaternion.identity;
                }
            }
            if (!Model.Placement.ContainsKey("II")) Model.Placement["II"] = Vector3.zero;
            Model.PlacementRot["II"] = Quaternion.identity;
            if (!Model.Placement.ContainsKey("I")) Model.Placement["I"] = new Vector3(60f, 0f, 0f);
            Model.PlacementRot["I"] = Quaternion.identity;
        }

        private void LoadResultsAndTributary(string path)
        {
            if (!File.Exists(path)) return;
            var d = Json.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
            if (d == null) return;
            if (!(d.TryGetValue("por_nivel", out var pn) && pn is Dictionary<string, object> porNivel)) return;
            foreach (var lvlNode in porNivel)
            {
                if (!(lvlNode.Value is List<object> beams)) continue;
                foreach (var bn in beams)
                {
                    var b = bn as Dictionary<string, object>;
                    if (b == null) continue;
                    string id = Json.Str(b, "receptor");
                    if (id == null) continue;
                    double area = Json.Num(b, "area_tributaria_m2");
                    double carga = Json.Num(b, "carga_total_kN");
                    var losas = new List<string>();
                    var lar = Json.Arr(b, "losas");
                    if (lar != null)
                        foreach (var lo in lar)
                            if (lo is Dictionary<string, object> ld && Json.Str(ld, "losa") != null)
                                losas.Add(Json.Str(ld, "losa"));
                    _tribByBeam[id] = new TribData(area, carga, "G = PP + PM.ADIC (lab)", "primera_ejecucion", losas);
                }
            }
        }

        /// <summary>Lee las regiones tributarias REALES (celdas del reparto geometrico)
        /// exportadas en regiones_tributarias.json. Solo Edificio I; sin geometria -> lista vacia
        /// (el visor muestra "area tributaria no disponible" sin inventar un rectangulo).</summary>
        private void LoadTributaryRegions(string path)
        {
            if (!File.Exists(path)) return;
            var d = Json.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
            if (d == null) return;
            if (!(d.TryGetValue("por_nivel", out var pn) && pn is Dictionary<string, object> porNivel)) return;
            foreach (var lvlNode in porNivel)
            {
                if (!(lvlNode.Value is Dictionary<string, object> lvlDict)) continue;
                if (!(lvlDict.TryGetValue("receptores", out var ro) && ro is Dictionary<string, object> receptores)) continue;
                float cota = (float)Json.Num(lvlDict, "cota");
                var byId = new Dictionary<string, List<TribRegion>>();
                foreach (var kv in receptores)
                {
                    var rec = kv.Value as Dictionary<string, object>;
                    if (rec == null) continue;
                    var celdaArr = Json.Arr(rec, "celdas");
                    if (celdaArr == null) continue;
                    var list = new List<TribRegion>();
                    foreach (var cn in celdaArr)
                    {
                        var cell = cn as Dictionary<string, object>;
                        if (cell == null) continue;
                        string losa = Json.Str(cell, "losa");
                        // Estructura exportada: "poligono" = lista de anillos [[u,v],...]
                        // (solo se usa el anillo exterior para dibujar la celda).
                        var rings = Json.Arr(cell, "poligono");
                        if (rings == null || rings.Count == 0) continue;
                        var ring = rings[0] as List<object>;
                        if (ring == null || ring.Count < 3) continue;
                        var reg = new TribRegion
                        {
                            Losa = losa,
                            AreaM2 = Json.Num(cell, "area_m2"),
                            CargaKN = Json.Num(cell, "carga_kN"),
                            Cota = cota,
                        };
                        foreach (var pt in ring)
                        {
                            if (pt is List<object> p && p.Count >= 2)
                                reg.Points.Add(new Vector3((float)Json.ToNum(p[0]), cota, (float)Json.ToNum(p[1])));
                        }
                        if (reg.Points.Count >= 3) list.Add(reg);
                    }
                    if (list.Count > 0) byId[kv.Key] = list;
                }
                if (byId.Count > 0) _tribRegions[lvlNode.Key] = byId;
            }
        }

        private void LoadResultsSummary(string path)
        {
            if (!File.Exists(path)) return;
            var d = Json.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
            if (d == null) return;
            Model.EiResultNote = Json.Str(d, "nota_limite");
            Model.EiResultSource = Json.Str(d, "ejecucion") ?? Model.EiResultSource;

            // Tramos de columna reales del modelo FE (Edificio I). Cada tramo:
            // {nivel, u, z_i, z_j, v} en convencion Unity (X,Y,Z)=(u,cota,v).
            // z_i = base (nodo inicial), z_j = cota superior (nodo final).
            if (d.TryGetValue("columnas_tramos", out var ct) && ct is List<object> tramos)
                foreach (var tn in tramos)
                {
                    var t = tn as Dictionary<string, object>;
                    if (t == null) continue;
                    string niv = Json.Str(t, "nivel");
                    double u = Json.Num(t, "u"), v = Json.Num(t, "v");
                    double zi = Json.Num(t, "z_i"), zj = Json.Num(t, "z_j");
                    string eid = Json.Str(t, "elemento_id") ?? "";
                    bool hipo = eid.IndexOf("_base_", System.StringComparison.Ordinal) >= 0;
                    _colTramosEI.Add(((float)u, (float)v, niv, (float)zi, (float)zj, hipo));
                }
        }

        private void BuildBuilding(Transform parent, string building, List<(string lvl, string file)> levels, string root)
        {
            var bgo = new GameObject(building);
            bgo.transform.SetParent(parent, false);
            if (Model.Placement.TryGetValue(building, out var pos)) bgo.transform.localPosition = pos;
            else bgo.transform.localPosition = Vector3.zero;
            if (Model.PlacementRot.TryGetValue(building, out var rot)) bgo.transform.localRotation = rot;

            var cotas = new List<float>();
            foreach (var (lvl, _) in levels) cotas.Add(CotaOf(lvl));
            for (int i = 0; i < levels.Count; i++)
            {
                float h = (i + 1 < levels.Count) ? cotas[i + 1] - cotas[i] : 3.96f;
                if (h < 1.0f) h = 3.96f;
                _storyHeight[levels[i].lvl] = h;
            }

            for (int idx = 0; idx < levels.Count; idx++)
            {
                var (lvl, file) = levels[idx];
                string full = Path.Combine(root, file);
                if (!File.Exists(full)) continue;
                var d = Json.Parse(File.ReadAllText(full)) as Dictionary<string, object>;
                if (d == null) continue;
                float cota = (float)Json.Num(d, "cota");

                var lvlGO = new GameObject(lvl);
                lvlGO.transform.SetParent(bgo.transform, false);

                var groups = new Dictionary<ElemType, GameObject>();
                foreach (ElemType t in System.Enum.GetValues(typeof(ElemType)))
                {
                    var g = new GameObject(t.ToString());
                    g.transform.SetParent(lvlGO.transform, false);
                    groups[t] = g;
                }

                BuildColumns(d, lvl, building, groups[ElemType.Columnas], groups[ElemType.RefPendientes]);
                BuildBeams(d, lvl, building, cota, groups[ElemType.Vigas]);
                BuildWalls(d, lvl, building, cota, groups[ElemType.Muros]);
                BuildSlabs(d, lvl, building, cota, groups[ElemType.Losas], groups[ElemType.Diafragma]);
                BuildAberturas(d, lvl, building, cota, groups[ElemType.Abertura]);
            }
        }

        private static float CotaOf(string lvl)
        {
            switch (lvl)
            {
                case "CP1S": case "EII_CP1S": return -4.01f;
                case "P1": case "EII_CP1": return -0.05f;
                case "P2": case "EII_CP2": return 3.91f;
                case "P3": case "EII_CP3": return 7.87f;
                case "P4": case "EII_CP4": return 11.83f;
            }
            return 0f;
        }

        // ---------------------------------------------------------------- //
        //  TRANSFORMACION COMUN (fuente unica de verdad)
        //  com(u,v,cota) -> Unity (X,Y,Z) = (u, cota, v)  [frame local del edificio]
        //  El desplazamiento de colocacion ("placement") del edificio NO se suma aqui:
        //  se aplica UNA sola vez por el transform del nodo raiz del edificio (o por
        //  ToWorldModel para objetos superpuestos que no cuelgan de esa jerarquia).
        //  Todos los builders (losas, vigas, columnas, muros, nodos, apoyos, overlays)
        //  usan estas funciones, nunca transformaciones ad-hoc.
        // ---------------------------------------------------------------- //
        public static Vector3 CommonTransform(float u, float cota, float v)
        {
            return new Vector3(u, cota, v);
        }

        public Vector3 BuildingOrigin(string building)
        {
            if (Model != null && Model.Placement.TryGetValue(building, out var p)) return p;
            return Vector3.zero;
        }

        /// <summary>Punto final MUNDIAL = placement del edificio + com(u,v,cota).
        /// Se aplica para elementos superpuestos/marcadores que NO cuelgan de la
        /// jerarquia Lab/Building/Level (nodos, apoyos, ejes, ids, tributaria).</summary>
        public Vector3 ToWorldModel(string building, float u, float cota, float v)
        {
            return BuildingOrigin(building) + CommonTransform(u, cota, v);
        }

        // ---------------------------------------------------------------- //
        //  Losas + diafragma
        // ---------------------------------------------------------------- //
        private void BuildSlabs(Dictionary<string, object> d, string lvl, string building, float cota,
                                GameObject losaGroup, GameObject diafGroup)
        {
            var losas = Json.Arr(d, "losas");
            if (losas == null) return;
            foreach (var lo in losas)
            {
                var L = (Dictionary<string, object>)lo;
                var poly = Json.V3List(L, "poligono");
                if (poly.Count < 3) continue;
                float e = (float)Json.Num(L, "espesor", 0.15f);

                var holes = new List<List<Vector2>>();
                var aberturas = Json.Arr(L, "aberturas");
                if (aberturas != null)
                    foreach (var ab in aberturas)
                        if (ab is List<object> ring && ring.Count >= 3)
                        {
                            var h = new List<Vector2>();
                            foreach (var pt in ring)
                                if (pt is List<object> p && p.Count >= 3)
                                    h.Add(new Vector2((float)Json.ToNum(p[0]), (float)Json.ToNum(p[2])));
                            if (h.Count >= 3) holes.Add(h);
                        }

                var refr = MakeElement(losaGroup, L, lvl, building, ElemType.Losas, poly[0]);
                refr.Espesor = e;
                refr.Aberturas = AberturasAsV3(aberturas);
                refr.ApoyosValidos = StrList(L, "apoyos_validos");
                refr.TipoTransferencia = Json.Str(L, "tipo_transferencia");

                var mesh = SlabMesh(poly, e, holes);
                ApplyMesh(refr.gameObject, mesh, Mat(HexColor(LOSA_COLOR_HEX)), refr);

                // Diafragma: SOLO contorno diferenciado, NO una losa estructural adicional.
                // Se dibuja como polilinea cerrada (color cian) sobre el borde de la losa y
                // de sus aberturas, desplazado un pequeno escalon sobre la cara superior para
                // evitar z-fighting. Se conserva un MeshCollider INVISIBLE (prisma delgado
                // del mismo poligono) unicamente para poder seleccionarlo en el visor; no se
                // pinta relleno, de modo que no puede confundirse con geometria estructural.
                var diaf = new GameObject(refr.Id + "_DIAF");
                diaf.transform.SetParent(diafGroup.transform, false);
                float diafY = poly[0].y + 0.05f;
                var lr = diaf.AddComponent<LineRenderer>();
                // El contorno se dibuja en coordenadas LOCALES (u,cota,v) ya que el diafragma
                // cuelga de la jerarquia Lab/Edificio/Nivel que transporta el offset de
                // colocacion del edificio. useWorldSpace debe ser FALSE: por defecto LineRenderer
                // interpreta las posiciones en espacio MUNDIAL, lo que dejaba el contorno sin el
                // desplazamiento del edificio (p. ej. Edificio I descolocado ~60 m en X respecto
                // a su losa, mientras su MeshCollider invisible, en local, sí alineado).
                lr.useWorldSpace = false;
                lr.positionCount = poly.Count + 1;
                for (int k = 0; k <= poly.Count; k++)
                    lr.SetPosition(k, new Vector3(poly[k % poly.Count].x, diafY, poly[k % poly.Count].z));
                lr.startWidth = lr.endWidth = 0.08f;
                lr.loop = true;
                lr.material = new Material(Shader.Find("Standard")) { color = HexColor(DIAF_COLOR_HEX) };
                if (holes != null)
                    foreach (var h in holes)
                        if (h != null && h.Count >= 2)
                        {
                            var hl = new GameObject("HOLE_" + refr.Id + "_DIAF");
                            hl.transform.SetParent(diaf.transform, false);
                            var hlr = hl.AddComponent<LineRenderer>();
                            hlr.useWorldSpace = false;
                            hlr.positionCount = h.Count + 1;
                            for (int k = 0; k <= h.Count; k++)
                                hlr.SetPosition(k, new Vector3(h[k % h.Count].x, diafY, h[k % h.Count].y));
                            hlr.startWidth = hlr.endWidth = 0.05f;
                            hlr.loop = true;
                            hlr.material = lr.material;
                        }
                var dr = diaf.AddComponent<ElementRef>();
                dr.Id = refr.Id + "_DIAF"; dr.Building = building; dr.Level = lvl;
                dr.Type = ElemType.Diafragma; dr.State = ValState.Confirmado;
                dr.Seccion = "diafragma rigido (contorno)";
                // collider invisible para poder seleccionar el diafragma por click;
                // se coloca ligeramente POR ENCIMA de la cara superior de la losa para
                // que el click caiga en el diafragma (contorno) antes que en la losa.
                var cmf = diaf.AddComponent<MeshFilter>();
                cmf.sharedMesh = ThinSlabMesh(poly, poly[0].y + 0.05f, 0.02f, holes);
                diaf.AddComponent<MeshCollider>();
                Model.Elements.Add(dr);
            }
        }

        private void BuildBeams(Dictionary<string, object> d, string lvl, string building, float cota, GameObject group)
        {
            var vigas = Json.Arr(d, "vigas");
            if (vigas == null) return;
            foreach (var vi in vigas)
            {
                var V = (Dictionary<string, object>)vi;
                var pts = Json.V3List(V, "pts");
                if (pts.Count < 2) continue;
                float w = (float)Json.Num(V, "ancho", 0.5f);
                float h = (float)Json.Num(V, "peralte", 0.8f);
                string sec = Json.Str(V, "seccion");
                // Resolucion de seccion robusta: si la fuente no entregO un "ancho" o
                // "peralte" explicito (campo ausente/nulo) o el valor no es positivo, se
                // resuelve de la etiqueta de seccion (p. ej. "V. 60/80" -> 0.6 x 0.8 m).
                // Evita que un campo ausente caiga en los defaults 0.5/0.8 y dibuje la
                // viga mas angosta de lo documentado.
                bool hasAncho = V.ContainsKey("ancho") && V["ancho"] != null;
                bool hasPeralte = V.ContainsKey("peralte") && V["peralte"] != null;
                bool needParse = !hasAncho || !hasPeralte || w <= 0 || h <= 0;
                float pw = 0f, ph = 0f;
                if (needParse) TryParseSection(sec, out pw, out ph);
                if (needParse && !string.IsNullOrEmpty(sec))
                {
                    if (!hasAncho || w <= 0) w = pw;
                    if (!hasPeralte || h <= 0) h = ph;
                }

                var refr = MakeElement(group, V, lvl, building, ElemType.Vigas, pts[0]);
                refr.Seccion = sec; refr.SectionW = w; refr.SectionH = h;
                refr.RecibeLosa = Json.Bool(V, "recibe_losa", true);
                refr.P0 = pts[0]; refr.P1 = pts[1];
                refr.State = StateOf(V, building);

                if (_tribByBeam.TryGetValue(refr.Id, out var td))
                {
                    refr.HasTributary = true; refr.TribAreaM2 = td.Area; refr.TribCargaKN = td.Carga;
                    refr.TribCase = td.Case; refr.TribSource = td.Source; refr.TribSourceLosas = td.Losas;
                }
                AttachTribRegions(refr, lvl);
                ApplyMesh(refr.gameObject, BoxBeam(pts[0], pts[1], w, h),
                          Mat(StateColorKey("viga", refr)), refr);
            }
        }

        /// <summary>Adjunta las regiones tributarias REALES (celdas del reparto geometrico)
        /// al elemento receptor por su ID original. Solo Edificio I; si no hay geometria
        /// la lista queda vacia (no se fabrica ningun rectangulo).</summary>
        private void AttachTribRegions(ElementRef refr, string lvl)
        {
            if (refr == null || refr.Building != "I") return;
            if (_tribRegions.TryGetValue(lvl, out var byId))
                if (byId.TryGetValue(refr.Id, out var regs))
                {
                    refr.TribRegions = regs;
                    if (!refr.HasTributary && regs.Count > 0) refr.HasTributary = true;
                }
        }

        private void BuildColumns(Dictionary<string, object> d, string lvl, string building,
                                  GameObject group, GameObject refGroup)
        {
            var cols = Json.Arr(d, "columnas");
            if (cols == null) return;

            foreach (var co in cols)
            {
                var C = (Dictionary<string, object>)co;
                var pos = Json.V3(C, "posicion");
                if (pos == null) continue;
                float w = (float)Json.Num(C, "ancho", 0f);
                float h = (float)Json.Num(C, "peralte", 0f);
                var baseState = StateOf(C, building);

                // Registros de REFERENCIA PENDIENTE: solo tienen posicion/rotulo de texto
                // (p. ej. P.M.I. proveniente de RLE-TEXTO-1), SIN geometria fisica respaldada
                // (sin seccion confirmada, sin dimensiones). No se dibujan como columna
                // completa entre forjados; se conservan como marcador compacto con su ID y
                // procedencia en el filtro independiente "Referencias pendientes".
                bool esReferenciaPendiente = Json.Str(C, "estado_seccion") == "por_resolver" && w <= 0 && h <= 0;
                if (esReferenciaPendiente)
                {
                    BuildRefPendiente(C, pos.Value, lvl, building, refGroup);
                    continue;
                }

                if (w <= 0 || h <= 0)
                {
                    w = 0.5f; h = 0.5f;
                    baseState = ValState.Pendiente;
                }

                float baseY, topY;
                if (lvl == "CP1S" || lvl == "EII_CP1S")
                {
                    baseY = pos.Value.y;
                    topY = pos.Value.y + 0.5f;
                    baseState = ValState.Pendiente;
                }
                else
                {
                    baseY = StoryBaseY(lvl);
                    topY = pos.Value.y;
                }

                var refr = MakeElement(group, C, lvl, building, ElemType.Columnas, pos.Value);
                refr.Seccion = Json.Str(C, "seccion");
                refr.SectionW = w; refr.SectionH = h;
                refr.Grid = Json.Str(C, "grid") ?? Json.Str(C, "eje");
                refr.P0 = new Vector3(pos.Value.x, baseY, pos.Value.z);
                refr.P1 = new Vector3(pos.Value.x, topY, pos.Value.z);
                refr.State = baseState;
                if (topY - baseY < 0.01f) refr.State = ValState.Pendiente;
                ApplyMesh(refr.gameObject, BoxBeam(new Vector3(pos.Value.x, baseY, pos.Value.z),
                          new Vector3(pos.Value.x, topY, pos.Value.z), w, h),
                          Mat(StateColorKey("col", refr)), refr);
            }
        }

        /// <summary>Base inferior (forjado de arranque) de una columna de entrepiso: la cota
        /// del forjado inmediatamente inferior documentado para el edificio del nivel.</summary>
        private float StoryBaseY(string lvl)
        {
            switch (lvl)
            {
                case "P1": return -4.01f;
                case "P2": return -0.05f;
                case "P3": return 3.91f;
                case "P4": return 7.87f;
                case "EII_CP1": return -4.01f;
                case "EII_CP2": return -0.05f;
                case "EII_CP3": return 3.91f;
                case "EII_CP4": return 7.87f;
            }
            return 3.91f;
        }

        /// <summary>Marcador compacto de REFERENCIA PENDIENTE (registro sin geometria fisica,
        /// solo posicion de rotulo de texto). Se dibuja un pequeno cubo semitransparente en la
        /// posicion documentada + una etiqueta de ID, bajo el grupo "Referencias pendientes",
        /// independiente de "Columnas". No altera coordenadas ni el modelo FE.</summary>
        private void BuildRefPendiente(Dictionary<string, object> C, Vector3 pos, string lvl,
                                       string building, GameObject refGroup)
        {
            var refr = MakeElement(refGroup, C, lvl, building, ElemType.RefPendientes, pos);
            refr.Seccion = Json.Str(C, "seccion");
            refr.Grid = Json.Str(C, "grid") ?? Json.Str(C, "eje");
            float yp = pos.y;
            refr.P0 = new Vector3(pos.x, yp, pos.z);
            refr.P1 = new Vector3(pos.x, yp + 0.3f, pos.z);
            refr.State = ValState.Pendiente;

            var mf = refr.gameObject.AddComponent<MeshFilter>();
            mf.sharedMesh = BoxBeam(new Vector3(pos.x, yp, pos.z),
                                    new Vector3(pos.x, yp + 0.35f, pos.z), 0.2f, 0.2f);
            var mr = refr.gameObject.AddComponent<MeshRenderer>();
            mr.sharedMaterial = MakeTransparentMat(HexColor(REF_COLOR_HEX), 0.55f);
            AddCollider(refr.gameObject, mf.sharedMesh, building, lvl, refr.Id, refr.Type.ToString());

            // etiqueta de ID + procedencia sobre el marcador (superpuesta, en coord mundial
            // = placement + local, definiendo con la misma fuente comun del modelo)
            var labelGO = new GameObject("REFID_" + refr.Id);
            labelGO.transform.SetParent(refGroup.transform, false);
            var tm = labelGO.AddComponent<TextMesh>();
            tm.text = refr.Id + (refr.Nota != null && refr.Nota.Contains("RLE-TEXTO-1") ? " (RLE-TEXTO-1)" : "");
            tm.characterSize = 0.1f; tm.fontSize = 30;
            tm.color = Color.black;
            labelGO.transform.localPosition = new Vector3(pos.x, yp + 0.55f, pos.z);
            labelGO.transform.localEulerAngles = new Vector3(90f, 0f, 0f);
            var tr = labelGO.AddComponent<ElementRef>();
            tr.Id = refr.Id; tr.Building = building; tr.Level = lvl; tr.Type = ElemType.RefPendientes;
        }

        /// <summary>Cota del siguiente nivel documentado del edificio por encima de `cota`, o
        /// float.NaN si no existe (ultimo nivel / techo sin cota documentada).</summary>
        private float NextDocCota(string building, string lvl, float cota)
        {
            string prefix = building == "I" ? "" : "EII_";
            string[] names = building == "I"
                ? new[] { "CP1S", "P1", "P2", "P3", "P4" }
                : new[] { "CP1S", "CP1", "CP2", "CP3", "CP4" };
            float best = float.NaN;
            foreach (var n in names)
            {
                float c = CotaOf(prefix + n);
                if (c > cota + 0.001f && (float.IsNaN(best) || c < best)) best = c;
            }
            return best;
        }

        /// <summary>Busca el tramo de columna FE del Edificio I que TERMINA en `cota` (la cota
        /// del cielo del nivel) y cuyo (u,v) coincide con (x,z) de la posicion Unity. La columna
        /// de un nivel desciende desde su cielo hasta el forjado inferior del tramo, por lo que
        /// se casa por extremo SUPERIOR (topY == cota), no por arranque. Nada se dibuja por
        /// encima del ultimo cielo. Tolera 1 cm (10 mm) por diferencias numericas del JSON.</summary>
        private (float baseY, float topY)? FindEiTramo(float x, float z, float cota)
        {
            // Se excluyen los tramos hipoteticos base->_nivel (esHipotesisBase): son el
            // elemento FE que lleva la carga a cimentacion cuando la columna documentada mas
            // baja es ese nivel; NO son una columna de entrepiso verificada, por lo que no
            // deben dibujarse como columna estructural completa. Si el unico candidato es
            // hipotetico, la columna del nivel queda PENDIENTE (cae al else de BuildColumns).
            foreach (var t in _colTramosEI)
                if (!t.esHipotesisBase && Mathf.Abs(t.u - x) < 0.011f && Mathf.Abs(t.v - z) < 0.011f &&
                    Mathf.Abs(t.topY - cota) < 0.011f)
                    return (t.baseY, t.topY);
            return null;
        }

        private void BuildWalls(Dictionary<string, object> d, string lvl, string building, float cota, GameObject group)
        {
            var muros = Json.Arr(d, "muros");
            if (muros == null) return;
            float hStory = _storyHeight.TryGetValue(lvl, out var hs) ? hs : 3.96f;
            foreach (var mu in muros)
            {
                var M = (Dictionary<string, object>)mu;
                var pts = Json.V3List(M, "pts");
                if (pts.Count < 2) continue;
                float e = (float)Json.Num(M, "espesor", 0.25f);
                var refr = MakeElement(group, M, lvl, building, ElemType.Muros, pts[0]);
                refr.SectionW = e;
                refr.P0 = pts[0]; refr.P1 = pts[1];
                refr.RecibeLosa = Json.Bool(M, "recibe_losa", true);
                refr.State = StateOf(M, building);

                if (_tribByBeam.TryGetValue(refr.Id, out var mr))
                {
                    refr.HasTributary = true; refr.TribAreaM2 = mr.Area; refr.TribCargaKN = mr.Carga;
                    refr.TribCase = mr.Case; refr.TribSource = mr.Source; refr.TribSourceLosas = mr.Losas;
                }
                AttachTribRegions(refr, lvl);
                ApplyMesh(refr.gameObject, BoxBeam(pts[0], pts[1], e, hStory),
                          Mat(StateColorKey("muro", refr)), refr);
            }
        }

        private void BuildAberturas(Dictionary<string, object> d, string lvl, string building, float cota, GameObject group)
        {
            var abs = Json.Arr(d, "aberturas_globales");
            if (abs == null) return;
            foreach (var abn in abs)
            {
                var AB = (Dictionary<string, object>)abn;
                var poly = Json.V3List(AB, "poligono");
                if (poly.Count < 3) continue;
                var refr = MakeElement(group, AB, lvl, building, ElemType.Abertura, poly[0]);
                var mf = refr.gameObject.AddComponent<MeshFilter>();
                mf.sharedMesh = ThinSlabMesh(poly, cota, 0.05f, null);
                var mr = refr.gameObject.AddComponent<MeshRenderer>();
                mr.sharedMaterial = MakeTransparentMat(HexColor(ABER_COLOR_HEX), 0.45f);
                AddCollider(refr.gameObject, mf.sharedMesh, building, lvl, refr.Id, "abertura");
            }
        }

        // ---------------------------------------------------------------- //
        //  Construccion de mallas
        // ---------------------------------------------------------------- //
        private static List<List<Vector3>> AberturasAsV3(object aberturas)
        {
            var res = new List<List<Vector3>>();
            if (aberturas is List<object> arr)
                foreach (var ring in arr)
                {
                    var l = new List<Vector3>();
                    if (ring is List<object> r)
                        foreach (var pt in r)
                            if (pt is List<object> p && p.Count >= 3)
                                l.Add(new Vector3((float)Json.ToNum(p[0]), (float)Json.ToNum(p[1]), (float)Json.ToNum(p[2])));
                    res.Add(l);
                }
            return res;
        }

        private static Mesh SlabMesh(List<Vector3> poly, float e, List<List<Vector2>> holes)
            => PrismMesh(poly, poly[0].y, e, holes, "slab");

        /// <summary>
        /// Prisma delgado (capa) usado para diafragmas y lineas de abertura: consume la
        /// misma triangulacion y conserva su volumen para que el MeshCollider sea valido.
        /// </summary>
        private static Mesh ThinSlabMesh(List<Vector3> poly, float topY, float thickness, List<List<Vector2>> holes)
            => PrismMesh(poly, topY, thickness, holes, "thinslab");

        /// <summary>Prisma delgado reutilizable para dibujar una celda de region
        /// tributaria como capa (misma triangulacion que losas/diafragma).</summary>
        public static Mesh TribRegionMesh(List<Vector3> poly, float topY, float thickness)
            => ThinSlabMesh(poly, topY, thickness, null);

        /// <summary>
        /// Construye un prisma vertical (tapa superior + inferior + laterales) a partir de
        /// la TRIANGULACION EFECTIVA de {exterior + aberturas}. Los laterales se generan
        /// para el borde exterior Y para cada abertura (laterales interiores de la losa).
        /// </summary>
        private static Mesh PrismMesh(List<Vector3> poly, float topY, float thickness, List<List<Vector2>> holes, string name)
        {
            float bot = topY - thickness;
            var ext = new List<Vector2>();
            foreach (var p in poly) ext.Add(new Vector2(p.x, p.z));
            var tr = Triangulator.Triangulate(ext, holes);
            if (tr.Triangles.Count == 0 || tr.Points.Count < 3)
            {
                Debug.LogError("[LabViewer] PrismMesh: triangulacion vacia para poligono con " + poly.Count + " verticies.");
                var empty = new Mesh(); empty.vertices = new Vector3[0]; empty.triangles = new int[0]; return empty;
            }
            int nT = tr.Points.Count;

            var verts = new List<Vector3>();
            var uv = new List<Vector2>();
            for (int i = 0; i < nT; i++)
            {
                verts.Add(new Vector3(tr.Points[i].x, topY, tr.Points[i].y));
                uv.Add(new Vector2(tr.Points[i].x, tr.Points[i].y));
            }
            for (int i = 0; i < nT; i++)
            {
                verts.Add(new Vector3(tr.Points[i].x, bot, tr.Points[i].y));
                uv.Add(new Vector2(tr.Points[i].x, tr.Points[i].y));
            }

            var tris = new List<int>();
            // Los indices salen CCW en (x,z); en Unity eso produce normal -Y (hacia abajo).
            // Tapa superior: invertimos -> normal +Y (cara arriba).
            // Tapa inferior: CCW -> normal -Y (cara abajo).
            // Una sola orientacion por cara (sin solapar triangulos coplanares) =>
            // sin z-fighting y sin losas negras.
            for (int i = 0; i < tr.Triangles.Count; i += 3)
            {
                tris.AddRange(new[] { tr.Triangles[i], tr.Triangles[i + 2], tr.Triangles[i + 1] });
            }
            for (int i = 0; i < tr.Triangles.Count; i += 3)
            {
                tris.AddRange(new[] { nT + tr.Triangles[i], nT + tr.Triangles[i + 1], nT + tr.Triangles[i + 2] });
            }
            // laterales: contorno exterior + cada abertura (ambas caras del cuadrilatero)
            AddRingSides(verts, uv, tris, ext, topY, bot);
            if (holes != null)
                foreach (var h in holes)
                    if (h != null && h.Count >= 2)
                        AddRingSides(verts, uv, tris, h, topY, bot);

            var m = new Mesh { name = name };
            m.SetVertices(verts);
            m.SetTriangles(tris, 0);
            m.SetUVs(0, uv);
            m.RecalculateNormals();
            return m;
        }

        private static void AddRingSides(List<Vector3> verts, List<Vector2> uv, List<int> tris,
                                         List<Vector2> ring, float topY, float botY)
        {
            int n = ring.Count;
            for (int i = 0; i < n; i++)
            {
                int b0 = verts.Count;
                Vector2 a = ring[i], b = ring[(i + 1) % n];
                verts.Add(new Vector3(a.x, topY, a.y));
                verts.Add(new Vector3(b.x, topY, b.y));
                verts.Add(new Vector3(b.x, botY, b.y));
                verts.Add(new Vector3(a.x, botY, a.y));
                uv.Add(Vector2.zero); uv.Add(Vector2.zero); uv.Add(Vector2.zero); uv.Add(Vector2.zero);
                // ambas caras del lateral (visible fuera e interior de aberturas)
                tris.AddRange(new[] { b0, b0 + 1, b0 + 2, b0, b0 + 2, b0 + 3 });
                tris.AddRange(new[] { b0, b0 + 2, b0 + 1, b0, b0 + 3, b0 + 2 });
            }
        }

        /// <summary>
        /// Valida la malla ANTES de usarla en un MeshCollider: indices en rango,
        /// triangulos no degenerados, sin vertices NaN. Logea edificio/nivel/ID en fallo.
        /// </summary>
        private static bool MeshIsValid(Mesh m, out string reason)
        {
            reason = null;
            if (m == null || m.vertexCount == 0) { reason = "malla vacia"; return false; }
            var v = m.vertices;
            var t = m.triangles;
            int nv = v.Length;
            for (int i = 0; i < t.Length; i++)
                if (t[i] < 0 || t[i] >= nv) { reason = "indice fuera de rango " + t[i] + " (nv=" + nv + ")"; return false; }
            for (int i = 0; i + 2 < t.Length; i += 3)
            {
                Vector3 a = v[t[i]], b = v[t[i + 1]], c = v[t[i + 2]];
                double area = Vector3.Cross(b - a, c - a).magnitude * 0.5;
                if (double.IsNaN(area) || double.IsInfinity((double)a.x) || double.IsInfinity((double)a.z)) { reason = "vertices invalidos"; return false; }
                if (area < 1e-9) { reason = "triangulo degenerado en " + i; return false; }
            }
            return true;
        }

        private void AddCollider(GameObject go, Mesh mesh, string building, string level, string id, string tipo)
        {
            string reason;
            if (MeshIsValid(mesh, out reason))
                go.AddComponent<MeshCollider>();
            else
                Debug.LogError("[LabViewer] Collider rechazado: Edificio=" + building + " Nivel=" + level
                               + " ID=" + id + " Tipo=" + tipo + " Motivo=" + reason);
        }

        private static void AddBox(List<Vector3> verts, List<int> tris, Vector3[] corners)
        {
            int b = verts.Count;
            foreach (var c in corners) verts.Add(c);
            tris.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3 });
        }

        private static Mesh BoxBeam(Vector3 p0, Vector3 p1, float w, float h)
        {
            Vector3 mid = (p0 + p1) * 0.5f;
            Vector3 ax = p1 - p0;
            float L = ax.magnitude;
            Vector3 dir = L > 1e-6f ? ax / L : Vector3.right;
            Vector3 right = Vector3.Cross(dir, Vector3.up);
            if (right.sqrMagnitude < 1e-6f) right = Vector3.Cross(dir, Vector3.forward);
            right.Normalize();
            Vector3 nrm = Vector3.Cross(right, dir).normalized;

            float Hw = w * 0.5f, Hh = h * 0.5f;
            Vector3 cb = mid - dir * (L * 0.5f);
            Vector3 ce = mid + dir * (L * 0.5f);

            var pgBottom = new[]
            {
                cb + right * Hw + nrm * (-Hh), ce + right * Hw + nrm * (-Hh),
                ce - right * Hw + nrm * (-Hh), cb - right * Hw + nrm * (-Hh)
            };
            var pgTop = new[]
            {
                cb - right * Hw + nrm * Hh, ce - right * Hw + nrm * Hh,
                ce + right * Hw + nrm * Hh, cb + right * Hw + nrm * Hh
            };

            var verts = new List<Vector3>(); var tris = new List<int>();
            AddBox(verts, tris, pgBottom);
            AddBox(verts, tris, pgTop);
            // laterales
            AddBox(verts, tris, new[] {
                cb + right*Hw + nrm*(-Hh), ce + right*Hw + nrm*(-Hh),
                ce + right*Hw + nrm*Hh, cb + right*Hw + nrm*Hh });
            AddBox(verts, tris, new[] {
                cb - right*Hw + nrm*(-Hh), cb - right*Hw + nrm*Hh,
                ce - right*Hw + nrm*Hh, ce - right*Hw + nrm*(-Hh) });
            AddBox(verts, tris, new[] {
                cb + right*Hw + nrm*(-Hh), cb + right*Hw + nrm*Hh,
                cb - right*Hw + nrm*Hh, cb - right*Hw + nrm*(-Hh) });
            AddBox(verts, tris, new[] {
                ce - right*Hw + nrm*(-Hh), ce - right*Hw + nrm*Hh,
                ce + right*Hw + nrm*Hh, ce + right*Hw + nrm*(-Hh) });

            var m = new Mesh { name = "box" };
            m.SetVertices(verts); m.SetTriangles(tris, 0); m.RecalculateNormals();
            return m;
        }

        private static void TryParseSection(string sec, out float w, out float h)
        {
            w = 0.5f; h = 0.8f;
            if (string.IsNullOrEmpty(sec)) return;
            var nums = System.Text.RegularExpressions.Regex.Matches(sec, @"\d+");
            if (nums.Count >= 2)
            {
                w = float.Parse(nums[0].Value) / 100f;
                h = float.Parse(nums[1].Value) / 100f;
            }
        }

        private void ApplyMesh(GameObject go, Mesh mesh, Material mat, ElementRef refr)
        {
            var mf = go.AddComponent<MeshFilter>();
            mf.sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            AddCollider(go, mesh, refr.Building, refr.Level, refr.Id, refr.Type.ToString());
        }

        private string StateColorKey(string kind, ElementRef e)
        {
            if (e.State == ValState.Pendiente) return PENDIENTE_COLOR_HEX;
            switch (kind)
            {
                case "viga": return VIGA_COLOR_HEX;
                case "col": return COL_COLOR_HEX;
                case "muro": return MURO_COLOR_HEX;
                default: return LOSA_COLOR_HEX;
            }
        }

        private ElementRef MakeElement(GameObject parent, Dictionary<string, object> data, string lvl,
                                       string building, ElemType type, Vector3 origin)
        {
            var go = new GameObject(Json.Str(data, "id") ?? type.ToString());
            go.transform.SetParent(parent.transform, false);
            var r = go.AddComponent<ElementRef>();
            r.Id = Json.Str(data, "id") ?? "";
            r.Building = building; r.Level = lvl; r.Type = type;
            r.Nota = Json.Str(data, "nota");
            r.Grid = Json.Str(data, "grid") ?? Json.Str(data, "eje");
            r.SectionW = 0; r.SectionH = 0;
            Model.Elements.Add(r);
            return r;
        }

        private static ValState StateOf(Dictionary<string, object> data, string building)
        {
            string es = Json.Str(data, "estado_seccion");
            if (es == "por_resolver") return ValState.Pendiente;
            string ect = Json.Str(data, "estado");
            if (ect == "confirmado") return ValState.Confirmado;
            if (building == "II") return ValState.Hipotetico;
            return ValState.Confirmado;
        }

        private static List<string> StrList(Dictionary<string, object> d, string key)
        {
            var res = new List<string>();
            var a = Json.Arr(d, key);
            if (a != null) foreach (var v in a) if (v is string s) res.Add(s);
            return res;
        }

        // ---------------------------------------------------------------- //
        //  Materiales
        // ---------------------------------------------------------------- //
        private static Material Mat(Color c)
        {
            var m = new Material(Shader.Find("Standard"));
            if (m.shader == null) m.shader = Shader.Find("Unlit/Color");
            m.color = c;
            return m;
        }

        private static Material Mat(string hex)
        {
            return Mat(HexColor(hex));
        }

        public Material MakeTransparentMat(Color c, float alpha)
        {
            c.a = alpha;
            var m = new Material(Shader.Find("Standard"));
            if (m.shader == null) m.shader = Shader.Find("Unlit/Color");
            m.color = c;
            m.SetFloat("_Mode", 3);
            m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            m.SetInt("_ZWrite", 0);
            m.DisableKeyword("_ALPHATEST_ON");
            m.EnableKeyword("_ALPHABLEND_ON");
            m.renderQueue = 3000;
            return m;
        }

        private static Color HexColor(string hex)
        {
            Color c; ColorUtility.TryParseHtmlString(hex, out c); return c;
        }
    }
}
