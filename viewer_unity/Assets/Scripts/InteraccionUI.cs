using System.Collections.Generic;
using UnityEngine;

namespace LabViewer
{
    /// <summary>
    /// Interaccion panel <-> camara para los OnGUI de los controllers del viewer.
    /// Mientras el puntero este sobre uno de los paneles registrados:
    ///  - la camara NO orbita/hace zoom/panea (ver CameraController.Update),
    ///  - el raycast de seleccion NO dispara (ver ViewerController.Update y
    ///    EsfuerzosController.Update),
    ///  - el scroll del raton se consume dentro del panel (no escapa a zoom).
    /// Los controllers registran sus rects de GUI en OnGUI (coordenadas Screen);
    /// PointerSobreUI() convierte Input.mousePosition (y=0 abajo) a coords GUI.
    /// </summary>
    public static class InteraccionUI
    {
        private static readonly List<Rect> _paneles = new List<Rect>();
        private static int _ultimoFrameReg = -1;
        private static bool _scrollConsumidoEnFrame;

        // --- distincion CLIC vs ARRASTRE de camara ---
        // El LMB tambien pannea con Shift (CameraController). Sin este umbral, el
        // pan o un simple arrastre del raton lanzaria la seleccion al soltar. Los
        // controllers llaman TrackClic() cada Update (antes del chequeo UI) y solo
        // ClicLiberadoDisponible() (que exige down->up con desplazamiento < umbral
        // y sin Shift) dispara la seleccion.
        private static bool _posibleClic;
        private static Vector2 _posibleClicInicio;

        private static bool ShiftAbajo()
        {
            return Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift);
        }

        /// <summary>Rastrear LMB cada Update: arma el candidato a clic solo si baja
        /// sin Shift (el pan con Shift+izq no debe seleccionar) y lo anula si el
        /// raton se mueve mas del umbral (se convirtio en arrastre/pan).</summary>
        public static void TrackClic()
        {
            if (Input.GetMouseButtonDown(0) && !ShiftAbajo())
            {
                _posibleClic = true;
                _posibleClicInicio = Input.mousePosition;
            }
            else if (_posibleClic &&
                     Vector2.Distance(_posibleClicInicio, (Vector2)Input.mousePosition) > CameraController.UmbralClicPx)
            {
                _posibleClic = false;
            }
        }

        /// <summary>True en el frame del MouseUp SOLO si fue un clic valido (habia
        /// candidato y sin superar el umbral de arrastre). Lo consumen ViewerController
        /// y EsfuerzosController para sus raycasts de seleccion (solo lectura, ambos
        /// pueden reaccionar al mismo clic como antes). El candidato se rearma en el
        /// proximo MouseDown y se anula con el umbral de arrastre.</summary>
        public static bool ClicLiberadoDisponible()
        {
            return _posibleClic && Input.GetMouseButtonUp(0);
        }

        /// <summary>
        /// Limpiar SOLO una vez por frame. Los rects se registran desde el OnGUI
        /// de varios controllers (ViewerController + EsfuerzosController); Unity
        /// llama OnGUI varias veces por frame y en orden no garantizado entre
        /// componentes, asi que limpiar por llamada perderia los rects ajenos.
        /// </summary>
        public static void Limpiar()
        {
            if (_ultimoFrameReg == Time.frameCount) return;
            _ultimoFrameReg = Time.frameCount;
            _paneles.Clear();
            _scrollConsumidoEnFrame = false;
        }

        /// <summary>Registrar cada area de panel (Box/BeginArea/area de scroll).</summary>
        public static void Registrar(Rect r)
        {
            if (r.width <= 0f || r.height <= 0f) return;
            _paneles.Add(r);
        }

        /// <summary>
        /// True si el cursor esta dentro de algun panel registrado este frame.
        /// Usa las coordenadas de GUI (Screen), iguales a las de los rects.
        /// </summary>
        public static bool PointerSobreUI()
        {
            Vector2 mp = Input.mousePosition;
            Vector2 p = new Vector2(mp.x, Screen.height - mp.y); // y GUI: 0 arriba
            for (int i = 0; i < _paneles.Count; i++)
                if (_paneles[i].Contains(p))
                    return true;
            return false;
        }

        /// <summary>
        /// Consume el ScrollWheel actual cuando el cursor esta sobre la UI,
        /// para que el reposicionado no escape del panel (punto "consumo del
        /// scroll dentro del panel"). Llamar dentro de OnGUI despues del dibujo.
        /// Usa InteraccionUI.PointerSobreUI() interno del helper; los paneles ya
        /// deben estar registrados con Registrar() antes de llamar esta.
        /// </summary>
        public static void UsarScrollSobrePanel()
        {
            if (Event.current == null) return;
            if (Event.current.type != EventType.ScrollWheel) return;
            if (!PointerSobreUI()) return;
            _scrollConsumidoEnFrame = true;
            Event.current.Use();
        }

        /// <summary>
        /// Toggle con estado ACTIVADO/INACTIVO inequivoco: fondo verde cuando
        /// esta on, gris oscuro cuando off. Devuelve el nuevo valor como un
        /// GUILayout.Toggle normal con el estilo indicado (p.ej. "button").
        /// </summary>
        public static bool ToggleEstado(bool valor, string texto, string estilo = "button")
        {
            Color baseColor = GUI.backgroundColor;
            GUI.backgroundColor = valor
                ? new Color(0.20f, 0.72f, 0.28f)
                : new Color(0.42f, 0.42f, 0.42f);
            bool nv = GUILayout.Toggle(valor, texto, estilo);
            GUI.backgroundColor = baseColor;
            return nv;
        }
    }
}
