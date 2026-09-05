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

        private Vector3 _panOffset = Vector3.zero;

        void Update()
        {
            if (Target != null) LookAt = Target.position + _panOffset;

            // orbitar
            if (Input.GetMouseButton(1))
            {
                Yaw += Input.GetAxis("Mouse X") * OrbitSpeed * 60f;
                Pitch -= Input.GetAxis("Mouse Y") * OrbitSpeed * 60f;
                Pitch = Mathf.Clamp(Pitch, -89f, 89f);
            }
            // pan
            if (Input.GetMouseButton(2) || (Input.GetKey(KeyCode.LeftShift) && Input.GetMouseButton(0)))
            {
                float sx = Input.GetAxis("Mouse X");
                float sy = Input.GetAxis("Mouse Y");
                Vector3 right = Camera.main != null ? Camera.main.transform.right : Vector3.right;
                Vector3 up = Camera.main != null ? Camera.main.transform.up : Vector3.up;
                _panOffset -= (right * sx + up * sy) * PanSpeed * Distance * 0.12f;
            }
            // zoom
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(scroll) > 1e-4f)
                Distance = Mathf.Clamp(Distance - scroll * ZoomSpeed * 4f, MinDist, MaxDist);

            PositionCamera();
        }

        void PositionCamera()
        {
            if (Camera.main == null) return;
            Quaternion rot = Quaternion.Euler(Pitch, Yaw, 0f);
            Vector3 dir = rot * Vector3.forward;
            Camera.main.transform.position = LookAt - dir * Distance;
            Camera.main.transform.rotation = Quaternion.LookRotation(LookAt - Camera.main.transform.position, Vector3.up);
        }

        public void FrameAll(Bounds b)
        {
            LookAt = b.center;
            _panOffset = Vector3.zero;
            Distance = Mathf.Clamp(b.size.magnitude * 1.35f, MinDist, MaxDist);
            Yaw = 45f; Pitch = 25f;
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
