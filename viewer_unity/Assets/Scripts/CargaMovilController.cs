using System.Collections.Generic;
using UnityEngine;

namespace LabViewer
{
    /// <summary>SQ4: carga movil. Con "carga movil" activa, el cursor sobre una LOSA
    /// del Edificio I identifica, mediante point-in-polygon sobre las celdas reales
    /// del reparto tributario (regiones_tributarias.json, coordenadas locales u/cota/v),
    /// la viga receptora que recibe la carga G de esa posicion; la resalta y muestra
    /// en HUD el area y la carga que caeria sobre ese receptor (respecta el factor de
    /// area tributaria del laboratorio S05). El modulo es SOLO lectura de datos FE:
    /// no reanaliza, solo lee el reparto geometrico ya resuelto.</summary>
    public class CargaMovilController : MonoBehaviour
    {
        public static CargaMovilController Inst;

        public bool Activo;
        public ElementRef ReceptorSobreCursor;
        public TribRegion RegionSobreCursor;

        private ViewerController _viewer;
        private LabLoader _loader;
        private readonly List<ElementRef> _receptores = new List<ElementRef>();
        private readonly List<Renderer> _resaltados = new List<Renderer>();
        private readonly Dictionary<Renderer, Color> _coloresGuardados = new Dictionary<Renderer, Color>();
        private float _ultimoId;

        void Awake()
        {
            Inst = this;
            _viewer = GetComponent<ViewerController>();
            _loader = GetComponent<LabLoader>();
        }

        private void Update()
        {
            if (!Activo)
            {
                if (_resaltados.Count > 0) LimpiarResaltado();
                return;
            }
            if (_receptores.Count == 0 && _viewer != null && _viewer.ModelPublic != null)
                CargarReceptores();
            if (InteraccionUI.PointerSobreUI()) return;
            if (Input.GetMouseButtonDown(0))
                BuscarBajoCursor();
        }

        private void CargarReceptores()
        {
            _receptores.Clear();
            var elem = _viewer.ModelPublic.Elements;
            if (elem == null) return;
            foreach (var e in elem)
            {
                if (e.Building != "I") continue;
                if (!e.HasTributary) continue;
                if (e.TribRegions == null || e.TribRegions.Count == 0) continue;
                _receptores.Add(e);
            }
            Debug.Log("[SQ4] Receptores tributarios cargados: " + _receptores.Count);
        }

        private void BuscarBajoCursor()
        {
            if (Camera.main == null || _loader == null) return;
            ReceptorSobreCursor = null;
            RegionSobreCursor = null;
            Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
            RaycastHit hit;
            if (!Physics.Raycast(ray, out hit, 2000f)) return;

            // Punto en frame local del edificio I (inversa de ToWorldModel).
            Vector3 origen = _loader.BuildingOrigin("I");
            Vector3 local = hit.point - origen;
            float cotaLocal = local.y;

            // Encontrar el receptor con una celda que contenga el punto (XZ) y en la
            // cota correcta (la losa que el rayo atraviesa = la mas cercana al cursor).
            float mejorDist = float.MaxValue;
            foreach (var r in _receptores)
            {
                if (r.TribRegions == null) continue;
                foreach (var reg in r.TribRegions)
                {
                    if (reg.Points == null || reg.Points.Count < 3) continue;
                    if (Mathf.Abs(reg.Cota - cotaLocal) > 0.6f) continue;
                    if (!PuntoEnPoligono(local, reg.Points)) continue;
                    float d = Mathf.Abs(reg.Cota - cotaLocal) + (r.P0 + r.P1).magnitude * 0f;
                    if (d < mejorDist)
                    {
                        mejorDist = d;
                        ReceptorSobreCursor = r;
                        RegionSobreCursor = reg;
                    }
                }
            }
            if (ReceptorSobreCursor != null)
            {
                Resaltar(ReceptorSobreCursor);
                RegistrarUso();
            }
            else
            {
                LimpiarResaltado();
            }
        }

        private void Resaltar(ElementRef r)
        {
            LimpiarResaltado();
            if (r == null || r.gameObject == null) return;
            var mr = r.gameObject.GetComponent<Renderer>();
            if (mr == null) return;
            if (!_coloresGuardados.ContainsKey(mr))
                _coloresGuardados[mr] = mr.material != null ? mr.material.color : Color.white;
            var nuevo = new Material(Shader.Find("Standard"))
            {
                color = new Color(1f, 0.2f, 1f, 1f)
            };
            mr.material = nuevo;
            _resaltados.Add(mr);
        }

        private void LimpiarResaltado()
        {
            foreach (var r in _resaltados)
            {
                if (r == null) continue;
                if (_coloresGuardados.TryGetValue(r, out var c))
                {
                    if (r.material != null) r.material.color = c;
                }
                else if (r.material != null)
                {
                    r.material.color = _viewer != null ? _viewer.ColorDe(ReceptorSobreCursor) : Color.white;
                }
            }
            _resaltados.Clear();
            _coloresGuardados.Clear();
        }

        private void RegistrarUso()
        {
            if (Time.realtimeSinceStartup - _ultimoId > 0.8f)
            {
                _ultimoId = Time.realtimeSinceStartup;
                Debug.Log("[SQ4] Region '" + (RegionSobreCursor != null ? RegionSobreCursor.Losa : "?")
                          + "' -> receptor " + ReceptorSobreCursor.Id
                          + ", area " + (RegionSobreCursor != null ? RegionSobreCursor.AreaM2 : 0).ToString("0.##")
                          + " m2, carga " + (RegionSobreCursor != null ? RegionSobreCursor.CargaKN : 0).ToString("0.##") + " kN");
            }
        }

        private static bool PuntoEnPoligono(Vector3 p, List<Vector3> poly)
        {
            bool inside = false;
            for (int i = 0, j = poly.Count - 1; i < poly.Count; j = i++)
            {
                var pi = poly[i];
                var pj = poly[j];
                if ((pi.z > p.z) != (pj.z > p.z) &&
                    p.x < (pj.x - pi.x) * (p.z - pi.z) / (pj.z - pi.z) + pi.x)
                    inside = !inside;
            }
            return inside;
        }

        private void OnGUI()
        {
            if (!Activo) return;
            Rect hud = new Rect(10, Screen.height - 116, 330, 108);
            InteraccionUI.Registrar(hud);
            GUI.Box(hud, "SQ4  CARGA MOVIL (modo activo, clic sobre una losa del Ed. I)");
            GUILayout.BeginArea(new Rect(hud.x + 8, hud.y + 22, hud.width - 16, hud.height - 30));
            if (ReceptorSobreCursor != null && RegionSobreCursor != null)
            {
                GUILayout.Label("Receptor: " + ReceptorSobreCursor.Id + "  (" + ReceptorSobreCursor.Level + ")");
                GUILayout.Label("Losa origen: " + RegionSobreCursor.Losa + "   cota " + RegionSobreCursor.Cota.ToString("0.##"));
                GUILayout.Label("Region: area " + RegionSobreCursor.AreaM2.ToString("0.##") + " m2   carga "
                                + RegionSobreCursor.CargaKN.ToString("0.##") + " kN");
                float fac = LabModificaciones.Inst != null ? LabModificaciones.Inst.TribFactor(ReceptorSobreCursor) : 1f;
                GUILayout.Label("Reparto G del receptor a mostrar: area " + (ReceptorSobreCursor.TribAreaM2 * fac).ToString("0.###")
                                + " m2   carga " + (ReceptorSobreCursor.TribCargaKN * fac).ToString("0.###") + " kN"
                                + (Mathf.Abs(fac - 1f) > 0.001f ? "  [factor lab x" + fac.ToString("0.##") + "]" : ""));
            }
            else
            {
                GUILayout.Label("Apunta con el cursor y clic sobre una LOSA.");
            }
            GUILayout.EndArea();
        }
    }
}