using System.Collections.Generic;
using UnityEngine;

namespace LabViewer
{
    /// <summary>Corrección integral: paneles IMGUI ARRASTRABLES desde su barra
    /// superior. Cada controller obtiene su recto por id (<see cref="Rect"/>),
    /// lo dibuja con su Box/BeginArea habituale y llama
    /// <see cref="BarraArrastrable"/> mientras dibuja la barra de título. El
    /// arrastre consume el evento (MouseDown/Drag/Up) y NO dispara cámara ni
    /// selección (el recto queda registrado en InteraccionUI). Se clampa a la
    /// pantalla conservando la barra accesible y se puede restablecer con
    /// <see cref="Reset"/>. Posiciones persistentes en sesión (no a disco).</summary>
    public static class Paneles
    {
        private sealed class Estado
        {
            public Rect rect;
            public bool abierto = true;
        }

        private static readonly Dictionary<string, Estado> _estados = new Dictionary<string, Estado>();
        private static string _arrastrando;
        private static Vector2 _grabOffset;

        /// <summary>Restablece todas las posiciones a sus valores por defecto.</summary>
        public static void Reset()
        {
            _estados.Clear();
            _arrastrando = null;
            GUIUtility.hotControl = 0;
        }

        public static bool EnArrastre => _arrastrando != null;

        public static bool Arrastrando(string id) => _arrastrando == id;

        private static Estado EstadoDe(string id)
        {
            if (!_estados.TryGetValue(id, out var e))
            {
                e = new Estado();
                _estados[id] = e;
            }
            return e;
        }

        /// <summary>Recto del panel (posicion memorizada o por defecto la primera
        /// vez). Registra el recto en InteraccionUI (bloqueo camara/seleccion).</summary>
        public static Rect Rect(string id, Rect porDefecto)
        {
            var e = EstadoDe(id);
            if ((e.rect.width <= 0f || e.rect.height <= 0f) && porDefecto.width > 0f && porDefecto.height > 0f)
                e.rect = porDefecto;
            InteraccionUI.Registrar(e.rect);
            return e.rect;
        }

        /// <summary>Recto del panel devolviendo tambien la posicion sin el area de
        /// contenido (util para paneles con barra de titulo propia).</summary>
        public static Rect BarraTitle(string id)
        {
            return new Rect(EstadoDe(id).rect.x, EstadoDe(id).rect.y, EstadoDe(id).rect.width, 24f);
        }

        /// <summary>Barra superior arrastrable. Llamar en OnGUI mientras la barra
        /// del panel se dibuja (coordenadas GUI). Consume el MouseDown/Drag/Up sobre
        /// la franja superior del recto para mover el panel sin interferir con el
        /// viewer ni con los controles del interior (la franja no cubre el contenido).</summary>
        public static void BarraArrastrable(string id)
        {
            BarraArrastrable(id, 26f);
        }

        /// <summary>Barra superior arrastrable con altura de franja configurable.
        /// La franja es la parte superior del recto del panel: los paneles que
        /// inician su BeginArea muy arriba deben pasar una altura menor para no
        /// pisar el primer control.</summary>
        public static void BarraArrastrable(string id, float altoTitulo)
        {
            var e = EstadoDe(id);
            var ev = Event.current;
            if (ev == null) return;
            Rect barra = new Rect(e.rect.x, e.rect.y, e.rect.width, altoTitulo);
            int control = (id.GetHashCode()) & 0x7fffffff;
            switch (ev.type)
            {
                case EventType.MouseDown:
                    if (ev.button == 0 && barra.Contains(ev.mousePosition))
                    {
                        _arrastrando = id;
                        _grabOffset = ev.mousePosition - e.rect.position;
                        GUIUtility.hotControl = control;
                        ev.Use();
                    }
                    break;
                case EventType.MouseDrag:
                    if (_arrastrando == id)
                    {
                        Rect r = e.rect;
                        r.position = ev.mousePosition - _grabOffset;
                        // Límites de pantalla: la barra superior SIEMPRE accesible.
                        float minX = Mathf.Min(Screen.width - 60f, -r.width + 150f);
                        float maxX = Screen.width - 30f;
                        float maxY = Screen.height - 44f;
                        r.x = Mathf.Clamp(r.x, minX, maxX);
                        r.y = Mathf.Clamp(r.y, 0f, maxY);
                        e.rect = r;
                        ev.Use();
                    }
                    break;
                case EventType.MouseUp:
                    if (_arrastrando == id)
                    {
                        _arrastrando = null;
                        GUIUtility.hotControl = 0;
                        ev.Use();
                    }
                    break;
            }
        }

        /// <summary>Colapso opcional por panel: estado abierto/cerrado.</summary>
        public static bool Abierto(string id) => EstadoDe(id).abierto;

        public static void SetAbierto(string id, bool abierto) => EstadoDe(id).abierto = abierto;
    }
}