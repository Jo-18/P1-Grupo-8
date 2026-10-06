using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

/// <summary>
/// Paneles del viewer que se pueden mover y cambiar de tamano: se arrastran desde la
/// franja superior (la de los puntos) y se agrandan o achican desde la esquina inferior
/// derecha. Doble clic en la franja los devuelve a su lugar. La posicion y el tamano
/// quedan guardados entre sesiones (PlayerPrefs).
/// </summary>
public static class PanelMovible
{
    const float MinAncho = 300f;
    const float MinAlto = 260f;
    static readonly List<(VisualElement panel, string clave)> registrados = new List<(VisualElement panel, string clave)>();

    /// Devuelve todos los paneles (UI Toolkit e IMGUI) a su posicion y tamano originales.
    /// true si el usuario movio o cambio el tamano de este panel.
    public static bool Movido(VisualElement panel) => panel != null && ultimo.ContainsKey(panel);

    public static void ReiniciarTodos()
    {
        foreach (var (panel, clave) in registrados) Reiniciar(panel, clave);
        UiTheme.ReiniciarMovidos();
    }
    static readonly Dictionary<VisualElement, Rect> ultimo = new Dictionary<VisualElement, Rect>();

    public static void Hacer(VisualElement panel, string clave)
    {
        if (panel == null) return;
        registrados.RemoveAll(x => x.clave == clave);
        registrados.Add((panel, clave));
        var franja = new VisualElement();
        franja.AddToClassList("panel-grip");
        franja.style.height = 12;
        franja.style.flexShrink = 0;
        franja.style.alignItems = Align.Center;
        franja.style.justifyContent = Justify.Center;
        franja.style.backgroundColor = new Color(0.36f, 0.15f, 0.28f, 0.92f);
        franja.style.borderTopLeftRadius = 6;
        franja.style.borderTopRightRadius = 6;
        franja.tooltip = "Arrastra para mover el panel (doble clic: volver a su lugar)";
        var puntos = new Label("• • •");
        puntos.AddToClassList("panel-grip-dots");
        puntos.style.color = new Color(1f, 0.561f, 0.639f);
        puntos.style.fontSize = 9;
        puntos.style.unityTextAlign = TextAnchor.MiddleCenter;
        puntos.style.paddingTop = 0; puntos.style.paddingBottom = 0; puntos.style.marginTop = 0; puntos.style.marginBottom = 0;
        puntos.pickingMode = PickingMode.Ignore;
        franja.Add(puntos);
        panel.Insert(0, franja);

        var esquina = new VisualElement();
        esquina.AddToClassList("panel-resize");
        esquina.style.position = Position.Absolute;
        esquina.style.right = 0;
        esquina.style.bottom = 0;
        esquina.style.width = 16;
        esquina.style.height = 16;
        Color rosa = new Color(1f, 0.561f, 0.639f);
        esquina.style.borderRightWidth = 3;
        esquina.style.borderBottomWidth = 3;
        esquina.style.borderRightColor = rosa;
        esquina.style.borderBottomColor = rosa;
        esquina.style.borderBottomRightRadius = 6;
        esquina.tooltip = "Arrastra para cambiar el tamano del panel";
        panel.Add(esquina);

        Arrastre(franja, panel, clave, false);
        Arrastre(esquina, panel, clave, true);

        EventCallback<GeometryChangedEvent> alPrimerLayout = null;
        alPrimerLayout = _ =>
        {
            panel.UnregisterCallback(alPrimerLayout);
            if (PlayerPrefs.HasKey(clave + "_w"))
            {
                var r = new Rect(PlayerPrefs.GetFloat(clave + "_x"), PlayerPrefs.GetFloat(clave + "_y"),
                                 Mathf.Max(MinAncho, PlayerPrefs.GetFloat(clave + "_w")), Mathf.Max(MinAlto, PlayerPrefs.GetFloat(clave + "_h")));
                Aplicar(panel, Limitar(panel, r));
            }
        };
        panel.RegisterCallback(alPrimerLayout);
    }

    static void Arrastre(VisualElement manija, VisualElement panel, string clave, bool redimensionar)
    {
        bool activo = false;
        Vector2 inicioPuntero = Vector2.zero;
        Rect inicio = Rect.zero;
        manija.RegisterCallback<PointerDownEvent>(e =>
        {
            if (e.button != 0) return;
            if (!redimensionar && e.clickCount == 2)
            {
                Reiniciar(panel, clave);
                e.StopPropagation();
                return;
            }
            activo = true;
            inicioPuntero = e.position;
            inicio = panel.layout;
            Aplicar(panel, inicio);
            manija.CapturePointer(e.pointerId);
            e.StopPropagation();
        });
        manija.RegisterCallback<PointerMoveEvent>(e =>
        {
            if (!activo || !manija.HasPointerCapture(e.pointerId)) return;
            Vector2 d = (Vector2)e.position - inicioPuntero;
            Rect r = inicio;
            if (redimensionar)
            {
                r.width = Mathf.Max(MinAncho, inicio.width + d.x);
                r.height = Mathf.Max(MinAlto, inicio.height + d.y);
            }
            else
            {
                r.x = inicio.x + d.x;
                r.y = inicio.y + d.y;
            }
            Aplicar(panel, Limitar(panel, r));
            e.StopPropagation();
        });
        manija.RegisterCallback<PointerUpEvent>(e =>
        {
            if (!activo) return;
            activo = false;
            if (manija.HasPointerCapture(e.pointerId)) manija.ReleasePointer(e.pointerId);
            Guardar(panel, clave);
            e.StopPropagation();
        });
    }

    static void Aplicar(VisualElement panel, Rect r)
    {
        panel.style.left = r.x;
        panel.style.top = r.y;
        panel.style.width = r.width;
        panel.style.height = r.height;
        panel.style.right = StyleKeyword.Auto;
        panel.style.bottom = StyleKeyword.Auto;
        ultimo[panel] = r;
    }

    static Rect Limitar(VisualElement panel, Rect r)
    {
        VisualElement padre = panel.parent;
        if (padre == null || float.IsNaN(padre.layout.width) || padre.layout.width <= 0f) return r;
        float w = padre.layout.width;
        float h = padre.layout.height;
        r.width = Mathf.Min(r.width, w);
        r.height = Mathf.Min(r.height, h);
        r.x = Mathf.Clamp(r.x, 60f - r.width, w - 60f);   // siempre queda una parte visible para recuperarlo
        r.y = Mathf.Clamp(r.y, 0f, h - 30f);
        return r;
    }

    static void Guardar(VisualElement panel, string clave)
    {
        if (!ultimo.TryGetValue(panel, out Rect r)) return;
        PlayerPrefs.SetFloat(clave + "_x", r.x);
        PlayerPrefs.SetFloat(clave + "_y", r.y);
        PlayerPrefs.SetFloat(clave + "_w", r.width);
        PlayerPrefs.SetFloat(clave + "_h", r.height);
        PlayerPrefs.Save();
    }

    static void Reiniciar(VisualElement panel, string clave)
    {
        panel.style.left = StyleKeyword.Null;
        panel.style.top = StyleKeyword.Null;
        panel.style.width = StyleKeyword.Null;
        panel.style.height = StyleKeyword.Null;
        panel.style.right = StyleKeyword.Null;
        panel.style.bottom = StyleKeyword.Null;
        ultimo.Remove(panel);
        foreach (string s in new[] { "_x", "_y", "_w", "_h" }) PlayerPrefs.DeleteKey(clave + s);
        PlayerPrefs.Save();
    }
}
