using UnityEngine;

namespace LabViewer
{
    /// <summary>
    /// Camara orbital + zoom + pan. Boton derecho arrastra = orbitar;
    /// rueda = zoom; boton medio/Shift+izq = pan. Vistas superior e isometrica.
    /// </summary>
    public class CameraController : MonoBehaviour
    {
        public Transform Target;
        public float Distance = 55f;
        public float Yaw = 45f;      // grados
        public float Pitch = 25f;    // grados
        public Vector3 LookAt = Vector3.zero;

        public float OrbitSpeed = 0.25f;
        public float PanSpeed = 0.12f;
        public float ZoomSpeed = 6f;
        public float MinDist = 3f, MaxDist = 400f;

        // Umbral (px) para distinguir un CLIC de un ARRASTRE de camara con LMB:
        // si el raton se mueve mas de este umbral entre el down y el up, no se
        // dispara la seleccion. Ver InteraccionUI.TrackClic/ClicLiberadoDisponible.
        public const float UmbralClicPx = 6f;

        private Vector3 _panOffset = Vector3.zero;
        private Bounds _lastBounds;
        private bool _hasBounds;

        void Update()
        {
            // Interaccion UI: si el puntero esta sobre algun panel IMGUI (rects que
            // registran los controllers en OnGUI), la camara NO orbita/panea/hace
            // zoom; la rueda queda para el ScrollView del panel. Esto se evalua con
            // los rects del frame anterior (OnGUI se dibuja despues de Update), un
            // frame de desfase imperceptible para click/scroll.
            if (InteraccionUI.PointerSobreUI())
            {
                return;
            }

            // orbitar alrededor del PIVOTE (LookAt + pan), no del origen del Lab:
            // FrameAll fija LookAt al centro del edificio y Grid no lo pisa mas.
            // Target se conserva por compatibilidad pero ya NO reescribe LookAt.
            if (Input.GetMouseButton(1))
            {
                Yaw += Input.GetAxis("Mouse X") * OrbitSpeed * 60f;
                Pitch -= Input.GetAxis("Mouse Y") * OrbitSpeed * 60f;
                Pitch = Mathf.Clamp(Pitch, -89f, 89f);
            }
            // pan (un solo factor, proporcional a la distancia)
            if (Input.GetMouseButton(2) || (Input.GetKey(KeyCode.LeftShift) && Input.GetMouseButton(0)))
            {
                float sx = Input.GetAxis("Mouse X");
                float sy = Input.GetAxis("Mouse Y");
                Vector3 right = Camera.main != null ? Camera.main.transform.right : Vector3.right;
                Vector3 up = Camera.main != null ? Camera.main.transform.up : Vector3.up;
                _panOffset -= (right * sx + up * sy) * PanSpeed * Distance;
            }
            // zoom EXPONENCIAL (nunca lineal): mismo factor relativo en cada tick,
            // y nunca atraviesa el pivote gracias al clamp [MinDist, MaxDist].
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(scroll) > 1e-4f)
                Distance = Mathf.Clamp(Distance * Mathf.Exp(-scroll * ZoomSpeed * 0.35f), MinDist, MaxDist);

            PositionCamera();
        }

        void PositionCamera()
        {
            if (Camera.main == null) return;
            Quaternion rot = Quaternion.Euler(Pitch, Yaw, 0f);
            Vector3 dir = rot * Vector3.forward;
            Vector3 look = LookAt + _panOffset;
            Camera.main.transform.position = look - dir * Distance;
            Camera.main.transform.rotation = Quaternion.LookRotation(look - Camera.main.transform.position, Vector3.up);
        }

        public void FrameAll(Bounds b)
        {
            _lastBounds = b;
            _hasBounds = true;
            LookAt = b.center;
            _panOffset = Vector3.zero;
            Distance = Mathf.Clamp(b.size.magnitude > 0.01f ? b.size.magnitude * 1.35f : 40f, MinDist, MaxDist);
            Yaw = 45f; Pitch = 25f;
            PositionCamera();
        }

        /// <summary>Vuelve a encuadrar el ultimo FrameAll guardado (tecla Inicio).</summary>
        public void Home()
        {
            if (_hasBounds) FrameAll(_lastBounds);
        }

        /// <summary>Enfoca un punto concreto (centro de un elemento seleccionado);
        /// mantiene el Yaw/Pitch actuales y ajusta la distancia al diametro dado.</summary>
        public void FocusOn(Vector3 point, float diameter)
        {
            LookAt = point;
            _panOffset = Vector3.zero;
            Distance = Mathf.Clamp(diameter * 1.6f, MinDist, MaxDist);
            PositionCamera();
        }

        public void SetViewTop()
        {
            LookAt += -_panOffset; _panOffset = Vector3.zero;
            Yaw = 0f; Pitch = 89f;
            Distance = Mathf.Clamp(Distance, MinDist, MaxDist);
            PositionCamera();
        }

        public void SetViewIso()
        {
            Yaw = 45f; Pitch = 25f;
            Distance = Mathf.Clamp(Distance, MinDist, MaxDist);
            PositionCamera();
        }
    }
}
