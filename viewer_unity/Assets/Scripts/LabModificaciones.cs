using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace LabViewer
{
    /// <summary>Entrada del registro de una modificacion aplicada en el laboratorio S05.</summary>
    [System.Serializable]
    public class ModRegistro
    {
        public string Hora;
        public string Tipo;
        public string Elemento;
        public string Detalle;
        public bool RequiereReanalisis;
        public ModRegistro(string tipo, string elemento, string detalle, bool req)
        {
            Hora = System.DateTime.Now.ToString("HH:mm:ss");
            Tipo = tipo; Elemento = elemento; Detalle = detalle; RequiereReanalisis = req;
        }
    }

    /// <summary>Laboratorio S05 de modificacion del modelo (el viewer es SOLO-lectura
    /// de los JSON FE, no re-resuelve en Unity). Criterio explicito de reanalisis:
    ///   M1 intensidad de carga (lamG/lamQ/lamEX/lamEY en el panel esfuerzos):
    ///      superposicion lineal exacta  => NO requiere reanalisis.
    ///   M2 elemento ON/OFF:  cambia K y el reparto       => requiere reanalisis.
    ///   M3 seccion w x h :   cambia la rigidez           => requiere reanalisis.
    ///   M4 area tributaria:  cambia el reparto de cargas => requiere reanalisis.
    /// Flujo reproducible: solver Python (modelo_fe_completo.py --g --sismo
    /// --combinadas) + export_lab_data.py. El banner y el registro dejan explicito
    /// cuando lo mostrado deja de corresponder al modelo analizado.</summary>
    public class LabModificaciones : MonoBehaviour
    {
        public static LabModificaciones Inst;

        public bool PanelAbierto = true;
        public bool RequiereReanalisis;
        public readonly List<ModRegistro> Registro = new List<ModRegistro>();

        private ViewerController _viewer;
        private EsfuerzosController _esf;
        private readonly HashSet<string> _elementosApagados = new HashSet<string>(); // ElementRef.Id
        private readonly Dictionary<string, Vector2> _seccionPorId = new Dictionary<string, Vector2>();
        private readonly Dictionary<string, float> _tribFactorPorId = new Dictionary<string, float>();
        private bool _tribGlobalOn;
        private float _tribFactorGlobal = 1f;
        private string _wTxt = "";
        private string _hTxt = "";
        private Vector2 _regScroll;

        void Awake()
        {
            Inst = this;
            _viewer = GetComponent<ViewerController>();
            _esf = GetComponent<EsfuerzosController>();
        }

        // ------------------------- consultas para el resto de la UI ------------- //
        public bool ElementoApagado(ElementRef r)
        {
            return r != null && !string.IsNullOrEmpty(r.Id) && _elementosApagados.Contains(r.Id);
        }

        public float TribFactor(ElementRef r)
        {
            if (r == null) return 1f;
            if (_tribFactorPorId.TryGetValue(r.Id, out var f)) return f;
            return _tribGlobalOn ? _tribFactorGlobal : 1f;
        }

        public double AreaVista(ElementRef r) => r == null ? 0d : r.TribAreaM2 * TribFactor(r);
        public double CargaVista(ElementRef r) => r == null ? 0d : r.TribCargaKN * TribFactor(r);

        public void SetTribFactor(ElementRef r, float k)
        {
            if (r == null || string.IsNullOrEmpty(r.Id)) return;
            k = Mathf.Clamp(k, 0f, 2f);
            if (r.HasTributary && !_tribFactorPorId.ContainsKey(r.Id) && !_tribGlobalOn)
            {
                _tribGlobalOn = true; _tribFactorGlobal = 1f;
            }
            _tribFactorPorId[r.Id] = k;
            MarcarReanalisis("Area tributaria", r.Id, "factor " + k.ToString("0.##") + " x sobre el reparto G");
        }

        public void SetTribFactorGlobal(float k)
        {
            k = Mathf.Clamp(k, 0f, 2f);
            if (Mathf.Abs(k - (_tribGlobalOn ? _tribFactorGlobal : 1f)) < 0.001f) return;
            _tribGlobalOn = true;
            _tribFactorGlobal = k;
            MarcarReanalisis("Area tributaria", "TODAS las vigas", "factor global " + k.ToString("0.##") + " x");
        }

        // ------------------------- M2: elemento on/off --------------------------- //
        public void ToggleElemento(ElementRef r)
        {
            if (r == null || string.IsNullOrEmpty(r.Id)) return;
            bool apagar = !_elementosApagados.Contains(r.Id);
            if (apagar)
            {
                _elementosApagados.Add(r.Id);
                if (r.gameObject != null) r.gameObject.SetActive(false);
                if (_esf != null) _esf.OcultarFE(r.Id, true);
                MarcarReanalisis("Elemento ON/OFF", r.Id, "elemento desactivado (eliminado del modelo)");
            }
            else
            {
                _elementosApagados.Remove(r.Id);
                if (r.gameObject != null)
                {
                    r.gameObject.SetActive(true);
                    var mr = r.gameObject.GetComponent<Renderer>();
                    if (mr != null)
                    {
                        var m = new Material(Shader.Find("Standard"));
                        if (m != null) m.color = _viewer != null ? _viewer.ColorDe(r) : Color.gray;
                        mr.material = m;
                    }
                }
                if (_esf != null) _esf.OcultarFE(r.Id, false);
                MarcarReanalisis("Elemento ON/OFF", r.Id, "elemento reactivado (se restaura el original)");
            }
        }

        // ------------------------- M3: seccion ----------------------------------- //
        public void AplicarSeccion(ElementRef r, string wTxt, string hTxt)
        {
            if (r == null) return;
            if (!float.TryParse(wTxt, System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out var w) ||
                !float.TryParse(hTxt, System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out var h) ||
                w <= 1e-4f || h <= 1e-4f)
            {
                Debug.LogWarning("LabModificaciones: seccion invalida (w=" + wTxt + ", h=" + hTxt + ")");
                return;
            }
            _seccionPorId[r.Id] = new Vector2(w, h);
            r.SectionW = w; r.SectionH = h;
            MarcarReanalisis("Seccion", r.Id, r.Seccion
                            + "  ->  " + w.ToString("0.##") + " x " + h.ToString("0.##") + " m");
        }

        public bool SeccionModificada(ElementRef r, out Vector2 seccion)
        {
            seccion = default;
            return r != null && _seccionPorId.TryGetValue(r.Id, out seccion);
        }

        // ------------------------- registro / reanalisis ------------------------- //
        private void MarcarReanalisis(string tipo, string elemento, string detalle)
        {
            RequiereReanalisis = true;
            Registro.Add(new ModRegistro(tipo, elemento, detalle, true));
            Debug.Log("[Lab S05] " + tipo + " en " + elemento + ": " + detalle + "  =>  REQUIERE REANALISIS");
        }

        public void RegistrarVivo(string tipo, string detalle)
        {
            Registro.Add(new ModRegistro(tipo, "-", detalle, false));
        }

        public void Reiniciar()
        {
            if (_esf != null)
            {
                if (_esf._ocultaLab.Count > 0)
                {
                    _esf._ocultaLab.Clear();
                    if (_esf.OverlayOn) _esf.RebuildOverlay();
                }
                _esf.SetSuperposicion(false);
            }
            foreach (var id in _elementosApagados)
            {
                var r = FindElemento(id);
                if (r != null && r.gameObject != null) r.gameObject.SetActive(true);
            }
            _elementosApagados.Clear();
            _seccionPorId.Clear();
            _tribFactorPorId.Clear();
            _tribGlobalOn = false; _tribFactorGlobal = 1f;
            RequiereReanalisis = false;
            Registro.Add(new ModRegistro("Reinicio", "-", "laboratorio restablecido al modelo original", false));
            Debug.Log("[Lab S05] Laboratorio reiniciado al modelo original.");
        }

        private ElementRef FindElemento(string id)
        {
            if (_viewer == null || _viewer.ModelPublic == null) return null;
            foreach (var e in _viewer.ModelPublic.Elements)
                if (e.Id == id) return e;
            return null;
        }

        // ------------------------- exportacion reproducible ---------------------- //
        public string Exportar()
        {
            var sb = new StringBuilder();
            sb.AppendLine("{");
            sb.AppendLine("  \"version\": \"S05-lab_modificaciones\",");
            sb.AppendLine("  \"generado\": \"" + System.DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "\",");
            sb.AppendLine("  \"requiere_reanalisis\": " + (RequiereReanalisis ? "true" : "false") + ",");
            sb.AppendLine("  \"reanalisis_reproducible\": \"modelo_fe_completo.py --g --sismo --combinadas && export_lab_data.py\",");
            sb.AppendLine("  \"modificaciones\": [");
            for (int i = 0; i < Registro.Count; i++)
            {
                var m = Registro[i];
                sb.Append("    { \"hora\": \"" + m.Hora + "\", \"tipo\": \"" + m.Tipo
                          + "\", \"elemento\": \"" + m.Elemento + "\", \"detalle\": \""
                          + m.Detalle + "\", \"requiere_reanalisis\": "
                          + (m.RequiereReanalisis ? "true" : "false") + " }");
                sb.AppendLine(i < Registro.Count - 1 ? "," : "");
            }
            sb.AppendLine("  ]");
            sb.AppendLine("}");

            string dir = Path.Combine(Application.streamingAssetsPath, "lab_data");
            string path = Path.Combine(dir, "modelo_modificado_lab.json");
            try
            {
                Directory.CreateDirectory(dir);
                File.WriteAllText(path, sb.ToString());
                Debug.Log("[Lab S05] Exportado: " + path);
                return path;
            }
            catch (System.Exception ex)
            {
                Debug.LogError("[Lab S05] No se pudo exportar: " + ex.Message);
                return null;
            }
        }

        // ------------------------- UI -------------------------------------------- //
        void OnGUI()
        {
            DrawBannerReanalisis();
            if (!PanelAbierto) return;
            DrawPanel();
        }

        private void DrawBannerReanalisis()
        {
            if (Screen.width < 600) return;
            float w = Mathf.Min(660f, Screen.width - 40f);
            Rect r = new Rect((Screen.width - w) / 2f, 6f, w, 42f);
            InteraccionUI.Registrar(r);
            if (RequiereReanalisis)
            {
                GUI.color = new Color(0.8f, 0.18f, 0.1f, 0.92f);
                GUI.Box(r, "");
                GUI.color = Color.white;
                GUI.Label(new Rect(r.x + 8, r.y + 4, r.width - 16, 16),
                          "MODIFICACION ESTRUCTURAL ACTIVA: los resultados visibles corresponden al modelo ORIGINAL.");
                GUI.Label(new Rect(r.x + 8, r.y + 22, r.width - 16, 16),
                          "REANALISIS: modelo_fe_completo.py --g --sismo --combinadas + export_lab_data.py (o 'Reiniciar lab').");
            }
            else
            {
                GUI.color = new Color(0.15f, 0.6f, 0.2f, 0.2f);
                GUI.Box(r, "");
                GUI.color = new Color(0f, 0f, 0f, 0.9f);
                GUI.Label(new Rect(r.x + 8, r.y + 10, r.width - 16, 16),
                          "Laboratorio S5 - modelo sin modificaciones. Sliders lambda (panel esfuerzos): variar cargas en vivo.");
            }
        }

        private void DrawPanel()
        {
            float pw = 344f;
            float x = Screen.width - pw - 8f;
            float y = 318f;
            Rect rect = new Rect(x, y, pw, 330f);
            if (rect.yMax > Screen.height - 4f) rect.y = Screen.height - rect.height - 4f;
            InteraccionUI.Registrar(rect);
            GUI.Box(rect, "LABORATORIO S5  /  MODIFICACION DEL MODELO");
            GUILayout.BeginArea(new Rect(rect.x + 8, rect.y + 24, rect.width - 16, rect.height - 32));

            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Reiniciar lab", GUILayout.Width(96))) Reiniciar();
            GUILayout.Label("Registro: " + Registro.Count);
            GUILayout.EndHorizontal();

            var sel = _viewer != null ? _viewer.SelectedPublic : null;
            if (sel != null)
            {
                GUI.color = new Color(0.9f, 0.9f, 0.2f);
                GUILayout.Label("Seleccion: " + sel.Building + "." + sel.Level + "." + sel.Type + " #" + sel.Id
                                + (sel.HasTributary ? "  [tributaria " + sel.TribAreaM2.ToString("0.##") + " m2]" : ""));
                GUI.color = Color.white;
            }
            else GUILayout.Label("(sin seleccion: clic sobre un elemento para M2/M3)");

            GUILayout.Box("M1  Intensidad de carga (superposicion lineal)");
            GUILayout.Label("C = " + (_esf != null ? _esf.FormulaLibre() : "G"));
            if (_esf != null && _esf.SuperposicionOn)
            {
                GUI.color = new Color(0.35f, 1f, 0.45f);
                GUILayout.Label("Lineal exacto: NO requiere reanalisis.");
                GUI.color = Color.white;
            }
            else if (_esf != null)
            {
                if (GUILayout.Button("Activar superposicion libre (sliders lambda)"))
                    _esf.SetSuperposicion(true);
            }

            GUILayout.Box("M2  Elemento ON/OFF (seleccion)  ->  REANALISIS");
            if (sel != null)
            {
                bool apagado = ElementoApagado(sel);
                if (GUILayout.Button(apagado ? "Reactivar elemento (modelo original)"
                                             : "Desactivar elemento (eliminar)"))
                    ToggleElemento(sel);
            }
            else GUILayout.Label("(selecciona primero)");

            GUILayout.Box("M3  Seccion nueva (w x h)  ->  REANALISIS");
            GUILayout.BeginHorizontal();
            GUILayout.Label("w(m):", GUILayout.Width(38));
            _wTxt = GUILayout.TextField(_wTxt, GUILayout.Width(52));
            GUILayout.Label("h(m):", GUILayout.Width(38));
            _hTxt = GUILayout.TextField(_hTxt, GUILayout.Width(52));
            GUILayout.EndHorizontal();
            if (GUILayout.Button("Aplicar seccion" + (string.IsNullOrEmpty(_wTxt) ? " (ej: 0.9 x 0.9)" : "")))
                AplicarSeccion(sel, _wTxt, _hTxt);

            GUILayout.Box("M4  Area tributaria (todas las vigas)  ->  REANALISIS");
            float k = _tribGlobalOn ? _tribFactorGlobal : 1f;
            float k2 = GUILayout.HorizontalSlider(k, 0f, 2f);
            if (Mathf.Abs(k2 - k) > 0.0001f) SetTribFactorGlobal(k2);
            GUILayout.Label("factor x " + (_tribGlobalOn ? _tribFactorGlobal : 1f).ToString("0.##"));

            GUILayout.Box("Registro de modificaciones");
            _regScroll = GUILayout.BeginScrollView(_regScroll, GUILayout.Height(66));
            int desde = Mathf.Max(0, Registro.Count - 5);
            for (int i = desde; i < Registro.Count; i++)
            {
                var m = Registro[i];
                GUILayout.Label((m.RequiereReanalisis ? "[REANALISIS] " : "[LIVE] ")
                                + m.Hora + " " + m.Tipo + " " + m.Elemento + "  " + m.Detalle);
            }
            GUILayout.EndScrollView();
            if (GUILayout.Button("Exportar modificaciones (JSON)")) Exportar();

            GUILayout.EndArea();
        }
    }
}