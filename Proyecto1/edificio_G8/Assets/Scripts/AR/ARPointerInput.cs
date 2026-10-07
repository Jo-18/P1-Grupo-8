using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// Single pointer source shared by the AR pickers. Android uses Input System.
public static class ARPointerInput
{
    public static bool TryPress(out Vector2 position)
    {
        position = default;
#if ENABLE_INPUT_SYSTEM
        var screen = Touchscreen.current;
        if (screen != null)
        {
            int active = 0;
            UnityEngine.InputSystem.Controls.TouchControl candidate = null;
            foreach (var touch in screen.touches)
                if (touch.press.isPressed) { active++; candidate = touch; }
            if (active > 0)
            {
                if (active != 1 || !candidate.press.wasPressedThisFrame) return false;
                position = candidate.position.ReadValue();
                return true;
            }
        }
#if UNITY_EDITOR || UNITY_STANDALONE
        var mouse = Mouse.current;
        if (mouse != null && mouse.leftButton.wasPressedThisFrame)
        {
            position = mouse.position.ReadValue();
            return true;
        }
#endif
#elif ENABLE_LEGACY_INPUT_MANAGER
        if (Input.touchCount == 1 && Input.GetTouch(0).phase == TouchPhase.Began)
        {
            position = Input.GetTouch(0).position;
            return true;
        }
#if UNITY_EDITOR || UNITY_STANDALONE
        if (Input.touchCount == 0 && Input.GetMouseButtonDown(0))
        {
            position = Input.mousePosition;
            return true;
        }
#endif
#endif
        return false;
    }
}
