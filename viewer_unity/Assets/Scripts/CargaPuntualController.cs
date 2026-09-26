using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace LabViewer
{
    /// <summary>Corr.2: carga puntual seleccionable que viaja hasta OpenSeesPy.
    /// Un config por edificio (formato `cargas_puntuales_v1`) se edita en el
    /// panel y se persiste en lab_data/cargas_puntuales.json. El analisis
    /// (eleLoad beamPoint) lo corre `carga_puntual.py` (CLI) que re-exporta el
    /// paquete del viewer con el caso PL1; el exportador inyecta PL1 SOLO si el
    /// payload del perfil existe.
    ///   - Caso A: cambio SOLO de magnitud -> escala lineal EXACTA en el viewer
    ///     (EFElemento.FactorPL = P / P_resuelta), sin reanalisis.
    ///   - Caso B: elemento/direccion/xi cambiados -> banner RESULTADOS
    ///     DESACTUALIZADOS y reanalisis por boton (OpenSeesPy).
    /// La flecha 3D indica el punto de aplicacion (xi), direccion y magnitud.</summary>
    public class CargaPuntualController : MonoBehaviour
    {
        public static CargaPuntualController Inst;
        public bool Activo = true;

        private EsfuerzosController _esf;
        private LabLoader _loader;

        [System.Serializable]
        public class CargaPL
        {
            public string edificio = "I";
            public int elemento_tag = -1;
            public string elemento_viewer_id;
            public string nivel = "";
            public bool activa;
            public float magnitud_kN = 50f;
            public float x = 1f, y = 0f, z = 0f;
            public float xi = 0.5f;
        }

        private readonly List<CargaPL> _estado = new List<CargaPL>();
        private CargaPL _edit;

        private bool _tieneResu;
        private bool _solResu;
        private int _resuTag = -1;
        private float _resuP;
        private float _resuXi;
        private Vector3 _resuDir;

        private GameObject _flechaShaft;
        private GameObject _flechaCone;
        private LineRenderer _lr;
        private TextMesh _label;

        private int _ultimoFeTag = -1;
        private float _ultimoFactor = -1f;
        private System.Diagnostics.Process _proc;
        private bool _analizando;

        private static readonly Color Fucsia = new Color(0.94f, 0.10f, 0.55f, 1f);
        private static readonly Color FucsiaInactiva = new Color(0.50f, 0.40f, 0.46f, 1f);
        private static readonly Color RojoBanner = new Color(0.85f, 0.16f, 0.1f, 0.92f);

        void Awake()
        {
            Inst = this;
            _esf = GetComponent<EsfuerzosController>();
            _loader = GetComponent<LabLoader>();
        }

        void Start()
        {
            CargarEstado();
            LeerResu();
            _ultimoFeTag = FEActualTag();
            _ultimoFactor = -1f;
        }

        // ------------------------------------------------------------------ //
        //  Estado (lectura/escritura del config persistido)
        // ------------------------------------------------------------------ //
        private static string EstadoPath()
        {
            return Path.Combine(Application.streamingAssetsPath, "lab_data", "cargas_puntuales.json");
        }

        private void CargarEstado()
        {
            _estado.Clear();
            string path = EstadoPath();
            if (!File.Exists(path)) return;
            try
            {
                var raiz = Json.AsObj(Json.Parse(File.ReadAllText(path)));
                if (raiz == null) return;
                var arr = raiz.TryGetValue("cargas", out var cw) ? Json.AsArr(cw) : null;
                if (arr == null) return;
                foreach (var it in arr)
                {
                    var d = Json.AsObj(it);
                    if (d == null) continue;
                    var pl = new CargaPL
                    {
                        edificio = Json.Str(d, "edificio") ?? "I",
                        elemento_tag = (int)Json.Num(d, "elemento_tag"),
                        elemento_viewer_id = Json.Str(d, "elemento_viewer_id"),
                        nivel = Json.Str(d, "nivel") ?? "",
                        activa = Json.Bool(d, "activa"),
                        magnitud_kN = (float)Json.Num(d, "magnitud_kN"),
                        xi = (float)Json.Num(d, "xi"),
                    };
                    var dd = d.TryGetValue("direccion_unity_unidad", out var dv) ? Json.AsArr(dv) : null;
                    if (dd != null && dd.Count >= 3)
                    {
                        pl.x = (float)Json.ToNum(dd[0]);
                        pl.y = (float)Json.ToNum(dd[1]);
                        pl.z = (float)Json.ToNum(dd[2]);
                    }
                    _estado.Add(pl);
                }
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning("[PL1] Estado no leido: " + ex.Message);
            }
        }

        public void EscribirEstado()
        {
            string dir = Path.Combine(Application.streamingAssetsPath, "lab_data");
            Directory.CreateDirectory(dir);
            var sb = new StringBuilder();
            sb.AppendLine("{\"formato\": \"cargas_puntuales_v1\", \"cargas\": [");
            for (int i = 0; i < _estado.Count; i++)
            {
                var pl = _estado[i];
                sb.Append("  {\"edificio\": \"" + pl.edificio + "\", \"elemento_tag\": " + pl.elemento_tag
                          + ", \"elemento_viewer_id\": " + (string.IsNullOrEmpty(pl.elemento_viewer_id)
                              ? "null" : "\"" + pl.elemento_viewer_id + "\"")
                          + ", \"nivel\": \"" + pl.nivel + "\", \"activa\": " + (pl.activa ? "true" : "false")
                          + ", \"magnitud_kN\": " + pl.magnitud_kN.ToString("0.####", System.Globalization.CultureInfo.InvariantCulture)
                          + ", \"direccion_unity_unidad\": [" + pl.x.ToString("0.###", System.Globalization.CultureInfo.InvariantCulture)
                          + ", " + pl.y.ToString("0.###", System.Globalization.CultureInfo.InvariantCulture)
                          + ", " + pl.z.ToString("0.###", System.Globalization.CultureInfo.InvariantCulture)
                          + "], \"xi\": " + pl.xi.ToString("0.###", System.Globalization.CultureInfo.InvariantCulture) + "}");
                sb.AppendLine(i < _estado.Count - 1 ? "," : "");
            }
            sb.AppendLine("]}");
            File.WriteAllText(EstadoPath(), sb.ToString());
            Debug.Log("[PL1] Estado guardado: " + EstadoPath());
        }

        private CargaPL CargarOLaEditar(string edificio, int feTag)
        {
            foreach (var pl in _estado)
                if (pl.edificio == edificio)
                    return pl;
            var n = new CargaPL { edificio = edificio, elemento_tag = feTag };
            _estado.Add(n);
            return n;
        }

        // ------------------------------------------------------------------ //
        //  Resultados resueltos en el paquete del viewer (bloque carga_puntual)
        // ------------------------------------------------------------------ //
        private void LeerResu()
        {
            _tieneResu = false;
            if (_esf == null || string.IsNullOrEmpty(_esf.Edificio)) return;
            string path = Path.Combine(Application.streamingAssetsPath, "lab_data",
                "edificios", _esf.Edificio, "results", "esfuerzos_FE_EDIFICIO_" + _esf.Edificio + ".json");
            if (!File.Exists(path)) return;
            try
            {
                var raiz = Json.AsObj(Json.Parse(File.ReadAllText(path)));
                if (raiz == null) return;
                var cp = raiz.TryGetValue("carga_puntual", out var cw) ? Json.AsObj(cw) : null;
                if (cp == null) return;
                _resuTag = (int)Json.Num(cp, "elemento_tag");
                _resuP = (float)Json.Num(cp, "magnitud_kN");
                _resuXi = (float)Json.Num(cp, "xi");
                var dd = cp.TryGetValue("direccion_unity_unidad", out var dv) ? Json.AsArr(dv) : null;
                if (dd != null && dd.Count >= 3)
                    _resuDir = new Vector3((float)Json.ToNum(dd[0]), (float)Json.ToNum(dd[1]), (float)Json.ToNum(dd[2]));
                _solResu = Json.Bool(cp, "solucion_ok");
                _tieneResu = true;
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning("[PL1] Resultados no leidos: " + ex.Message);
            }
        }

        // ------------------------------------------------------------------ //
        //  Estado derivado (Caso A escala / Caso B reanalisis)
        // ------------------------------------------------------------------ //
        private int FEActualTag()
        {
            return (_esf != null && _esf.SelectedFE != null && _esf.OverlayOn)
                ? _esf.SelectedFE.Tag : -1;
        }

        private bool MismoDir(Vector3 a, Vector3 b)
        {
            if (a.magnitude < 1e-6f || b.magnitude < 1e-6f) return false;
            return Vector3.Distance(a.normalized, b.normalized) < 1e-3f;
        }

        private bool EsCasoA_SoloMagnitud()
        {
            if (!_tieneResu || !_edit.activa) return false;
            if (_edit.elemento_tag != _resuTag) return false;
            if (Mathf.Abs(_edit.xi - _resuXi) > 1e-3f) return false;
            if (!MismoDir(new Vector3(_edit.x, _edit.y, _edit.z), _resuDir)) return false;
            return true;
        }

        void LateUpdate()
        {
            if (_esf == null) return;
            int fe = FEActualTag();
            if (fe != _ultimoFeTag)
            {
                _ultimoFeTag = fe;
                if (fe >= 0)
                    _edit = CargarOLaEditar(_esf.Edificio, fe);
            }
            if (_edit == null)
                _edit = CargarOLaEditar(_esf.Edificio, fe >= 0 ? fe : -1);

            AplicarFactor();
            ActualizarFlecha();
            FinalizarReanalisis();
        }

        private void AplicarFactor()
        {
            if (!_tieneResu) return;
            float f = 1f;
            if (EsCasoA_SoloMagnitud() && _resuP > 0f)
                f = _edit.magnitud_kN / _resuP;
            f = Mathf.Max(0f, f);
            if (Mathf.Abs(f - _ultimoFactor) > 1e-3f)
            {
                _ultimoFactor = f;
                if (_esf != null) _esf.SetFactorPL(f);
            }
        }

        // ------------------------------------------------------------------ //
        //  Flecha 3D (punto de aplicacion, direccion, magnitud)
        // ------------------------------------------------------------------ //
        /// <summary>Longitud visual de la flecha proporcional a la distancia de la
        /// camara, con recorte: mantiene el mismo tamano EN PANTALLA al acercarse o
        /// alejarse. NUNCA se toca el punto de aplicacion (baseW): solo crece hacia
        /// fuera del elemento, asi que la posicion fisica de la carga no se altera.</summary>
        private static float LargoVisual(float distCam)
        {
            return Mathf.Clamp(distCam * 0.11f, 0.65f, 4.5f);
        }

        private void ActualizarFlecha()
        {
            if (_edit == null) return;
            bool dibujar = _edit.activa && _edit.elemento_tag >= 0;
            var fe = _esf != null ? _esf.SelectedFE : null;
            if (dibujar && fe != null && fe.Tag == _edit.elemento_tag)
            {
                Vector3 p = Vector3.Lerp(fe.Pi, fe.Pj, _edit.xi);
                Vector3 baseW = _loader != null ? _loader.ToWorldModel(fe.Building, p.x, p.y, p.z)
                                                : p;
                Vector3 dirW = new Vector3(_edit.x, _edit.y, _edit.z).normalized;
                bool vale = EsCasoA_SoloMagnitud();

                var cam = Camera.main;
                Vector3 camPos = cam != null ? cam.transform.position : baseW + new Vector3(0f, 10f, -20f);
                float dist = Vector3.Distance(camPos, baseW);
                float largo = LargoVisual(dist);
                float grosor = Mathf.Clamp(largo * 0.075f, 0.045f, 0.30f);
                float anchoPunta = Mathf.Clamp(largo * 0.20f, 0.14f, 0.85f);

                Vector3 dest = baseW + dirW * largo;
                if (_lr == null) CrearFlecha();
                _lr.enabled = true;
                _lr.SetPosition(0, baseW);
                _lr.SetPosition(1, dest);
                _lr.startWidth = grosor;
                _lr.endWidth = grosor * 0.28f;
                Color col = vale ? Fucsia : FucsiaInactiva;
                _lr.startColor = _lr.endColor = col;

                // Cono (cilindro de Unity) alineado con la direccion de la carga; su
                // escala sigue a la de la flecha para no despegarse del extremo.
                _flechaCone.transform.position = dest;
                _flechaCone.transform.rotation = Quaternion.LookRotation(dirW) * Quaternion.Euler(90f, 0f, 0f);
                _flechaCone.transform.localScale =
                    new Vector3(anchoPunta, Mathf.Max(largo * 0.10f, 0.06f), anchoPunta);
                var mr = _flechaCone.GetComponent<Renderer>();
                if (mr != null && mr.material != null) mr.material.color = col;
                _flechaCone.SetActive(true);

                if (_label == null) CrearLabel();
                // Billboard: el texto mira SIEMPRE a la camara, descolocado hacia el
                // observador y arriba para no meterse dentro del cono ni de la barra.
                Vector3 haciaCam = (baseW - camPos).normalized;
                _label.transform.position = dest + haciaCam * (largo * 0.30f) + Vector3.up * (largo * 0.22f);
                _label.transform.rotation = Quaternion.LookRotation(_label.transform.position - camPos, Vector3.up);
                _label.characterSize = Mathf.Clamp(largo * 0.085f, 0.05f, 0.30f);
                _label.fontSize = 26;
                _label.text = EtiquetaFlecha(fe, vale, dirW);
                _label.color = col;
                return;
            }
            if (_lr != null) _lr.enabled = false;
            if (_flechaCone != null) _flechaCone.SetActive(false);
        }

        /// <summary>Texto de la etiqueta: estado del caso, carga aplicada y el
        /// desplazamiento REAL que produce en el punto de aplicacion, interpolado
        /// linealmente entre los extremos del elemento y en mm (dato del solver, no
        /// el valor amplificado de la deformada visual).</summary>
        private string EtiquetaFlecha(EFElemento fe, bool vale, Vector3 dir)
        {
            string txt = "PL1 " + (vale ? "ACTIVA" : "INACTIVA")
                       + "  P=" + _edit.magnitud_kN.ToString("0.#") + " kN (" + EtiquetaDir(dir) + ")";
            if (_esf != null
                && _esf.DespNodoElemento(fe, "i", out var di0)
                && _esf.DespNodoElemento(fe, "j", out var dj0))
            {
                float dmm = Vector3.Lerp(di0, dj0, _edit.xi).magnitude * 1000f;
                if (!float.IsNaN(dmm) && !float.IsInfinity(dmm))
                    txt += "  d=" + dmm.ToString("0.00") + " mm";
            }
            if (!vale) txt += "  [reanalizar]";
            return txt;
        }

        private static string EtiquetaDir(Vector3 d)
        {
            if (Mathf.Abs(d.x) > 0.9f) return d.x > 0 ? "+U" : "-U";
            if (Mathf.Abs(d.z) > 0.9f) return d.z > 0 ? "+V" : "-V";
            return d.y > 0 ? "+COTA" : "-COTA";
        }

        private void CrearFlecha()
        {
            var root = new GameObject("PL1_FLECHA");
            _flechaShaft = new GameObject("PL1_SHAFT");
            _flechaShaft.transform.SetParent(root.transform, false);
            _lr = _flechaShaft.AddComponent<LineRenderer>();
            _lr.positionCount = 2;
            _lr.startWidth = 0.12f;
            _lr.endWidth = 0.03f;
            Shader sh = Shader.Find("Unlit/Color");
            if (sh == null) sh = Shader.Find("Sprites/Default");
            _lr.material = new Material(sh);
            _flechaCone = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            _flechaCone.name = "PL1_CONE";
            _flechaCone.transform.SetParent(root.transform, false);
            _flechaCone.transform.localScale = new Vector3(0.22f, 0.38f, 0.22f);
            var mr = _flechaCone.GetComponent<Renderer>();
            mr.material = new Material(sh);
            mr.material.color = Fucsia;
            var col = _flechaCone.GetComponent<Collider>();
            if (col != null) Destroy(col);
            if (_label == null) CrearLabel();
        }

        private void CrearLabel()
        {
            var go = new GameObject("PL1_LABEL");
            go.transform.SetParent(_flechaShaft != null ? _flechaShaft.transform : transform, false);
            _label = go.AddComponent<TextMesh>();
            _label.characterSize = 0.16f;
            _label.fontSize = 26;
            _label.color = Fucsia;
        }

        // ------------------------------------------------------------------ //
        //  Reanalisis (CLI -> OpenSeesPy -> re-exportar)
        // ------------------------------------------------------------------ //
        public void Reanalizar()
        {
            if (_analizando) return;
            EscribirEstado();
            string sa = Application.streamingAssetsPath;
            var d = new DirectoryInfo(sa);
            string repo = d.Parent != null && d.Parent.Parent != null && d.Parent.Parent.Parent != null
                ? d.Parent.Parent.Parent.FullName : null;
            if (repo == null) return;
            string python = Path.Combine(repo, ".venv", "Scripts", "python.exe");
            if (!File.Exists(python)) python = "python";
            string script = Path.Combine(repo, "entrega_03_cargas_sismo_capacidad",
                "src", "unity_esfuerzos", "carga_puntual.py");
            if (!File.Exists(script))
            {
                Debug.LogError("[PL1] No se encontro carga_puntual.py: " + script);
                return;
            }
            try
            {
                var psi = new System.Diagnostics.ProcessStartInfo(python, "\"" + script + "\"")
                {
                    WorkingDirectory = repo,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                };
                _proc = System.Diagnostics.Process.Start(psi);
                _analizando = true;
                Debug.Log("[PL1] Reanalisis en marcha (OpenSeesPy)...");
            }
            catch (System.Exception ex)
            {
                Debug.LogError("[PL1] No se pudo lanzar el reanalisis: " + ex.Message);
                _analizando = false;
            }
        }

        private void FinalizarReanalisis()
        {
            if (_proc == null) return;
            if (!_proc.HasExited) return;
            string outT = _proc.StandardOutput.ReadToEnd();
            string errT = _proc.StandardError.ReadToEnd();
            int code = _proc.ExitCode;
            _proc.Close();
            _proc = null;
            _analizando = false;
            if (code != 0)
            {
                Debug.LogError("[PL1] Reanalisis fallo (exit " + code + "):\n" + errT);
                return;
            }
            Debug.Log("[PL1] Reanalisis OK\n" + outT);
            if (_esf != null) _esf.RecargarPaquetes();
            CargarEstado();
            LeerResu();
            _edit = CargarOLaEditar(_esf.Edificio, FEActualTag());
            _ultimoFactor = -1f;
        }

        // ------------------------------------------------------------------ //
        //  Panel
        // ------------------------------------------------------------------ //
        void OnGUI()
        {
            if (_esf == null || !Activo) return;
            if (_esf.Edificio == null) return;
            if (_edit == null) _edit = CargarOLaEditar(_esf.Edificio, FEActualTag());
            if (_esf.Edificio != _edit.edificio)
                _edit = CargarOLaEditar(_esf.Edificio, FEActualTag());

            DrawBanner();

            // Panel PL1 ARRASTRABLE desde la barra de titulo (Paneles). El rect
            // queda registrado en InteraccionUI => el arrastre no orbita/panea la
            // camara ni selecciona elementos por detras; Paneles clampa para que
            // la barra siga siempre visible en pantalla.
            Rect panel = Paneles.Rect("pl1_panel", new Rect(Screen.width - 372, 10, 362, 330));
            GUI.Box(panel, "PL1  CARGA PUNTUAL (" + _esf.Edificio + ", caso PL1)");
            Paneles.BarraArrastrable("pl1_panel", 20f);
            GUILayout.BeginArea(new Rect(panel.x + 8, panel.y + 22, panel.width - 16, panel.height - 30));
            GUILayout.Label(_edit.elemento_tag >= 0
                ? "Elemento FE: tag " + _edit.elemento_tag + "  (" + _edit.nivel + ")"
                : "Selecciona un elemento FE (overlay on).");
            _edit.activa = GUILayout.Toggle(_edit.activa, " Aplicada (activa)");
            GUILayout.BeginHorizontal();
            GUILayout.Label("P", GUILayout.Width(14));
            _edit.magnitud_kN = GUILayout.HorizontalSlider(_edit.magnitud_kN, 1f, 300f);
            GUILayout.Label(_edit.magnitud_kN.ToString("0.#") + " kN", GUILayout.Width(64));
            GUILayout.EndHorizontal();
            GUILayout.Label("Direccion:");
            GUILayout.BeginHorizontal();
            DireccionBoton("+U", new Vector3(1f, 0f, 0f));
            DireccionBoton("-U", new Vector3(-1f, 0f, 0f));
            DireccionBoton("+V", new Vector3(0f, 0f, 1f));
            DireccionBoton("-V", new Vector3(0f, 0f, -1f));
            DireccionBoton("+COTA", new Vector3(0f, 1f, 0f));
            DireccionBoton("-COTA", new Vector3(0f, -1f, 0f));
            GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal();
            GUILayout.Label("xi", GUILayout.Width(14));
            _edit.xi = GUILayout.HorizontalSlider(_edit.xi, 0.05f, 0.95f);
            GUILayout.Label(_edit.xi.ToString("0.00"), GUILayout.Width(40));
            GUILayout.EndHorizontal();

            GUILayout.Space(4);
            GUILayout.Label(EstadoTexto());
            if (_analizando)
            {
                GUILayout.Label("ANALIZANDO EN OPENSEESPY...");
            }
            else
            {
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("Guardar estado"))
                    EscribirEstado();
                if (GUILayout.Button("Reanalizar (solver)"))
                    Reanalizar();
                GUILayout.EndHorizontal();
            }
            GUILayout.Label("El caso PL1 se activa en el selector de casos "
                            + "(" + string.Join(" / ", _esf.CasosSelectables()) + ").");
            GUILayout.EndArea();
        }

        private void DireccionBoton(string etiqueta, Vector3 dir)
        {
            bool on = Mathf.Abs(_edit.x - dir.x) < 1e-3f && Mathf.Abs(_edit.y - dir.y) < 1e-3f
                      && Mathf.Abs(_edit.z - dir.z) < 1e-3f;
            bool nuevo = GUILayout.Toggle(on, etiqueta, "button");
            if (nuevo && !on)
            {
                _edit.x = dir.x;
                _edit.y = dir.y;
                _edit.z = dir.z;
                _ultimoFactor = -1f;
            }
        }

        private string EstadoTexto()
        {
            if (!_edit.activa)
                return "Carga inactiva: sin aporte de PL1.";
            if (!_tieneResu)
                return "SIN RESULTADOS PL1 en el paquete. Pulsa \u201Creanalizar\u201D.";
            if (EsCasoA_SoloMagnitud())
                return "Caso A (escala lineal exacta): factor " + _ultimoFactor.ToString("0.###")
                       + " sobre P0=" + _resuP.ToString("0.#") + " kN."
                       + (_esf.Caso != EsfuerzosController.PL_CASO
                           ? " Selecciona el caso PL1 en el overlay." : "");
            if (_resuTag != _edit.elemento_tag)
                return "El payload PL1 se calculo sobre el elemento " + _resuTag
                       + ". Reanaliza para este elemento.";
            return "Configuracion distinta a la resuelta: REANALIZAR (los "
                   + "resultados vigentes quedan DESACTUALIZADOS).";
        }

        private void DrawBanner()
        {
            bool desact = _edit.activa && _tieneResu && !EsCasoA_SoloMagnitud()
                          && _resuTag == _edit.elemento_tag;
            if (!desact) return;
            if (Screen.width < 600) return;
            float w = Mathf.Min(680f, Screen.width - 40f);
            Rect r = new Rect((Screen.width - w) / 2f, 62f, w, 42f);
            InteraccionUI.Registrar(r);
            GUI.color = RojoBanner;
            GUI.Box(r, "RESULTADOS DESACTUALIZADOS: la carga puntual activa difiere "
                       + "de la resuelta en el caso PL1 (pulsa Reanalizar)");
            GUI.color = Color.white;
        }
    }
}