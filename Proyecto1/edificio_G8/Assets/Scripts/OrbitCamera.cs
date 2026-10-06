using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

public class OrbitCamera : MonoBehaviour
{
    public Transform target;
    public float distance = 75f;
    public float xSpeed = 120f;
    public float ySpeed = 80f;
    public float zoomSpeed = 4f;
    public float panSpeed = 8f;

    private float x = 45f;
    private float y = 28f;

    private void Start()
    {
        if (target == null)
        {
            GameObject pivot = new GameObject("CameraPivot");
            pivot.transform.position = new Vector3(-0.7f, 5f, -4.5f);
            target = pivot.transform;
        }

        UpdatePosition();
    }

    // Mouse: arrastre izquierdo o derecho = orbitar; boton central o Shift + arrastre = desplazar;
    // rueda = zoom; flechas = desplazar. Un arrastre solo empieza fuera de los paneles, pero sigue
    // aunque el puntero pase sobre ellos. El clic izquierdo sin arrastre sigue seleccionando.
    public float gradosPorPixel = 0.3f;
    private const float UmbralArrastrePx = 4f;
    private int botonArrastre = -1;      // -1 ninguno, 0 izquierdo, 1 derecho, 2 central
    private bool desplazando;
    private bool izquierdoPendiente;
    private Vector2 inicioPuntero, ultimoPuntero;
    private ElementPicker picker;

    private void LateUpdate()
    {
        float scroll = 0f;
        if (!Application.isMobilePlatform)
        {
            ManejarMouse();
            ManejarTeclado();
            scroll = LeerRueda();
            // sobre un panel la rueda desplaza el panel, no la camara
            if (scroll != 0f && UiTheme.IsOverUI(PunteroPantalla(), InfoVisible())) scroll = 0f;
        }
        HandleTouch();   // toques del celular (API Input legacy, activa en modo "Both")
        // zoom proporcional a la distancia: ~12 % por clic de rueda
        distance = Mathf.Clamp(distance * Mathf.Pow(1f - Mathf.Clamp(0.03f * zoomSpeed, 0.02f, 0.3f), scroll), 5f, 120f);

        UpdatePosition();
    }

    private void ManejarMouse()
    {
        LeerBotones(out bool izq, out bool der, out bool med, out bool izqBaja, out bool derBaja, out bool medBaja);
        Vector2 pos = PunteroPantalla();
        bool shift = ShiftPresionado();

        if (botonArrastre < 0)
        {
            if ((derBaja || medBaja) && !UiTheme.IsOverUI(pos, InfoVisible()))
            {
                botonArrastre = derBaja ? 1 : 2;
                desplazando = medBaja || shift;
                ultimoPuntero = pos;
            }
            else if (izqBaja)
            {
                izquierdoPendiente = !UiTheme.IsOverUI(pos, InfoVisible());
                inicioPuntero = pos;
                ultimoPuntero = pos;
            }
            else if (izquierdoPendiente && izq && (pos - inicioPuntero).magnitude > UmbralArrastrePx)
            {
                botonArrastre = 0;
                izquierdoPendiente = false;
                desplazando = shift;
                ultimoPuntero = pos;
            }
            if (!izq) izquierdoPendiente = false;
        }

        if (botonArrastre < 0) return;
        bool sigue = botonArrastre == 0 ? izq : botonArrastre == 1 ? der : med;
        if (!sigue)
        {
            botonArrastre = -1;
            return;
        }
        Vector2 d = pos - ultimoPuntero;
        ultimoPuntero = pos;
        if (desplazando)
        {
            float k = distance * 0.0016f;   // metros por pixel, proporcional a la distancia
            Pan(-d.x * k, -d.y * k);
        }
        else
        {
            x += d.x * gradosPorPixel;
            y = Mathf.Clamp(y - d.y * gradosPorPixel, -10f, 85f);
        }
    }

    private void ManejarTeclado()
    {
        float ax = 0f, ay = 0f;
#if ENABLE_INPUT_SYSTEM
        Keyboard keyboard = Keyboard.current;
        if (keyboard != null)
        {
            if (keyboard.rightArrowKey.isPressed) ax += 1f;
            if (keyboard.leftArrowKey.isPressed) ax -= 1f;
            if (keyboard.upArrowKey.isPressed) ay += 1f;
            if (keyboard.downArrowKey.isPressed) ay -= 1f;
        }
#else
        ax = (Input.GetKey(KeyCode.RightArrow) ? 1f : 0f) - (Input.GetKey(KeyCode.LeftArrow) ? 1f : 0f);
        ay = (Input.GetKey(KeyCode.UpArrow) ? 1f : 0f) - (Input.GetKey(KeyCode.DownArrow) ? 1f : 0f);
#endif
        if (ax != 0f || ay != 0f) Pan(ax * panSpeed * Time.deltaTime, ay * panSpeed * Time.deltaTime);
    }

    private static void LeerBotones(out bool izq, out bool der, out bool med, out bool izqBaja, out bool derBaja, out bool medBaja)
    {
#if ENABLE_INPUT_SYSTEM
        Mouse m = Mouse.current;
        if (m != null)
        {
            izq = m.leftButton.isPressed;
            der = m.rightButton.isPressed;
            med = m.middleButton.isPressed;
            izqBaja = m.leftButton.wasPressedThisFrame;
            derBaja = m.rightButton.wasPressedThisFrame;
            medBaja = m.middleButton.wasPressedThisFrame;
            return;
        }
        izq = der = med = izqBaja = derBaja = medBaja = false;
#else
        izq = Input.GetMouseButton(0);
        der = Input.GetMouseButton(1);
        med = Input.GetMouseButton(2);
        izqBaja = Input.GetMouseButtonDown(0);
        derBaja = Input.GetMouseButtonDown(1);
        medBaja = Input.GetMouseButtonDown(2);
#endif
    }

    private static Vector2 PunteroPantalla()
    {
#if ENABLE_INPUT_SYSTEM
        if (Mouse.current != null) return Mouse.current.position.ReadValue();
#endif
        return Input.mousePosition;
    }

    private static bool ShiftPresionado()
    {
#if ENABLE_INPUT_SYSTEM
        Keyboard k = Keyboard.current;
        return k != null && (k.leftShiftKey.isPressed || k.rightShiftKey.isPressed);
#else
        return Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift);
#endif
    }

    private static float LeerRueda()
    {
#if ENABLE_INPUT_SYSTEM
        Mouse m = Mouse.current;
        float s = m != null ? m.scroll.ReadValue().y : 0f;
        if (Mathf.Abs(s) > 10f) s /= 120f;   // segun la version la rueda entrega ±1 o ±120 por clic
        return s;
#else
        return Input.GetAxis("Mouse ScrollWheel") * 10f;   // 0,1 por clic -> clics
#endif
    }

    private bool InfoVisible()
    {
        if (picker == null) picker = FindAnyObjectByType<ElementPicker>();
        return picker != null && picker.HasSelection;
    }

    // ------------------------------------------------------------------
    // Celular: 1 dedo = orbitar, 2 dedos = pellizco (zoom) + arrastre (paneo).
    // Los toques que empiezan sobre un panel no mueven la camara.
    // ------------------------------------------------------------------
    public float touchOrbitSpeed = 0.25f;   // grados por pixel
    public float touchPanSpeed = 0.0025f;   // fraccion de la distancia por pixel
    private bool touchOrbitActive;
    private bool twoFingerActive;

    private void HandleTouch()
    {
        if (Input.touchCount == 0)
        {
            touchOrbitActive = false;
            twoFingerActive = false;
            return;
        }

        var picker = FindAnyObjectByType<ElementPicker>();
        bool infoVisible = picker != null && picker.Selected != null;

        if (Input.touchCount == 1)
        {
            UnityEngine.Touch t = Input.GetTouch(0);
            if (t.phase == UnityEngine.TouchPhase.Began)
            {
                touchOrbitActive = !UiTheme.IsOverUI(t.position, infoVisible);
            }
            if (touchOrbitActive && !twoFingerActive && t.phase == UnityEngine.TouchPhase.Moved)
            {
                x += t.deltaPosition.x * touchOrbitSpeed;
                y = Mathf.Clamp(y - t.deltaPosition.y * touchOrbitSpeed, -10f, 80f);
            }
            if (t.phase == UnityEngine.TouchPhase.Ended || t.phase == UnityEngine.TouchPhase.Canceled)
            {
                twoFingerActive = false;
            }
            return;
        }

        UnityEngine.Touch a = Input.GetTouch(0);
        UnityEngine.Touch b = Input.GetTouch(1);
        if (b.phase == UnityEngine.TouchPhase.Began)
        {
            twoFingerActive = !UiTheme.IsOverUI((a.position + b.position) * 0.5f, infoVisible);
        }
        if (!twoFingerActive) return;
        touchOrbitActive = false;

        Vector2 prevA = a.position - a.deltaPosition;
        Vector2 prevB = b.position - b.deltaPosition;
        float prevDist = (prevA - prevB).magnitude;
        float dist = (a.position - b.position).magnitude;
        if (prevDist > 1f && dist > 1f)
        {
            distance = Mathf.Clamp(distance * prevDist / dist, 5f, 120f);
        }
        Vector2 move = (a.deltaPosition + b.deltaPosition) * 0.5f;
        Pan(-move.x * touchPanSpeed * distance, -move.y * touchPanSpeed * distance);
    }

    private void Pan(float screenX, float screenY)
    {
        Quaternion rotation = Quaternion.Euler(y, x, 0f);
        Vector3 right = rotation * Vector3.right;
        Vector3 up = rotation * Vector3.up;

        Vector3 offset = right * screenX + up * screenY;
        target.position += offset;
    }

    private void UpdatePosition()
    {
        Quaternion rotation = Quaternion.Euler(y, x, 0f);
        Vector3 offset = rotation * new Vector3(0f, 0f, -distance);
        transform.position = target.position + offset;
        transform.rotation = rotation;
    }

    public void FocusOn(Vector3 point, float newDistance = -1f)
    {
        if (target == null)
        {
            GameObject pivot = new GameObject("CameraPivot");
            target = pivot.transform;
        }
        target.position = point;
        if (newDistance > 0f)
        {
            distance = Mathf.Clamp(newDistance, 5f, 120f);
        }
        UpdatePosition();
    }

    public void SetPreset(string preset)
    {
        if (preset == "TOP") { x = 0f; y = 80f; }
        else if (preset == "FRONT") { x = 0f; y = 8f; }
        else if (preset == "RIGHT") { x = 90f; y = 8f; }
        else if (preset == "ISO") { x = 45f; y = 30f; }
        UpdatePosition();
    }
}
