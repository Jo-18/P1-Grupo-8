using System.Collections;
using System.Globalization;
using UnityEngine;

namespace LabViewer.AR
{
    // Pantalla de resultados: el vector de esfuerzos (caso G, tag 489) fue
    // producido por OpenSees. Este componente solo lee y presenta esos datos.
    // Si el diagrama interno esta cargado, muestra los valores de seccion
    // (primer/ultima estacion) de la magnitud seleccionada; si no, el caso por
    // defecto Vz(i)/Vz(j) de extremos del vector.
    [DisallowMultipleComponent]
    public sealed class ARResult489Label : MonoBehaviour
    {
        [SerializeField] ARBeam489Loader m_Loader;
        [SerializeField] ARImageAnchorController m_Controller;
        [SerializeField] Transform m_ContentRoot;
        [SerializeField] Camera m_Camera;
        [SerializeField] ARForceDiagram489 m_Diagrama;

        const string FormatoNumero = "+0.000;-0.000;0.000";

        GameObject m_TextoGo;
        TextMesh m_Texto;
        bool m_Visible;

        void Start()
        {
            if (m_Loader == null || m_Controller == null || m_Camera == null)
            {
                Debug.LogError("[AR489] ARResult489Label sin referencias (loader/controller/camera); rotulo no mostrado");
                return;
            }

            if (m_ContentRoot == null) m_ContentRoot = transform;
            StartCoroutine(EsperarVisibilidad());
        }

        // El rotulo queda oculto hasta que esten: datos cargados, viga/identidad
        // existente y anchor valido. Se muestra una sola vez (coroutine liviana;
        // el unico per-frame permitido es el billboard en LateUpdate).
        IEnumerator EsperarVisibilidad()
        {
            while (m_Loader == null || !m_Loader.DataLoaded || m_Loader.Identity == null
                   || m_Controller == null || m_Controller.Anchor == null)
            {
                yield return null;
            }

            if (m_Visible) yield break;
            Mostrar();
            m_Visible = true;
        }

        void Mostrar()
        {
            var identity = m_Loader.Identity;
            if (identity == null) return;

            if (m_TextoGo == null) CrearTextoGo();
            AplicarTexto();
        }

        void CrearTextoGo()
        {
            m_TextoGo = new GameObject("AR489_Resultado");
            m_TextoGo.transform.SetParent(m_ContentRoot, false);
            m_TextoGo.AddComponent<MeshRenderer>();
            m_Texto = m_TextoGo.AddComponent<TextMesh>();

            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (font == null) font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            if (font == null)
            {
                Debug.LogError("[AR489] No se encontro la fuente builtin; rotulo sin tipografia");
            }
            else
            {
                m_Texto.font = font;
                m_Texto.GetComponent<MeshRenderer>().sharedMaterial = font.material;
            }

            m_Texto.anchor = TextAnchor.MiddleCenter;
            m_Texto.alignment = TextAlignment.Center;
            m_Texto.color = Color.black;
        }

        // Llamado por el diagrama cuando carga o cuando cambia la magnitud
        // seleccionada. Si el rotulo aun no es visible, Mostrar() usara el
        // diagrama solo si ya esta listo.
        public void ActualizarConDiagrama(ARForceDiagram489 diagrama)
        {
            if (diagrama == null || !diagrama.DataLoaded) return;
            if (m_TextoGo == null) return;
            AplicarTexto();
        }

        void AplicarTexto()
        {
            if (m_Texto == null || m_Loader == null || m_Loader.Identity == null) return;

            string texto = (m_Diagrama != null && m_Diagrama.DataLoaded)
                ? TextoConDiagrama(m_Diagrama)
                : TextoBase();
            m_Texto.text = texto;

            // Tamano en unidades de mundo AR (escala 1:10 del modelo real), no en
            // pixeles de pantalla. Formula del TextMesh legacy:
            //   characterSize = altoObjetivoMundo * 10 / fontSize
            // Objetivo: bloque de texto no mas ancho que la viga AR (0.305 m) y
            // legible a distancia normal de observacion.
            float len = m_Loader.VigaLongitudAR;
            float maxAncho = Mathf.Max(0.10f, Mathf.Min(len, 0.28f));
            int maxChars = MayorLinea(texto);
            float anchoGlifo = 0.5f;
            float altoGlifo = maxAncho / Mathf.Max(1f, maxChars * anchoGlifo);
            m_Texto.fontSize = 48;
            m_Texto.characterSize = Mathf.Max(altoGlifo * 10f / m_Texto.fontSize, 0.001f);

            AjustarAnchoReal(maxAncho);

            int nLineas = CantidadLineas(texto);
            float altoBloque = altoGlifo * nLineas * 1.2f;
            Vector3 tamViga = m_Loader.VigaTamanoAR;
            float semiAlturaViga = tamViga.y * 0.5f;
            float offsetY = semiAlturaViga + 0.02f + altoBloque * 0.5f;
            m_TextoGo.transform.localPosition = m_Loader.VigaCentroLocal + new Vector3(0f, offsetY, 0f);
        }

        string TextoBase()
        {
            var identity = m_Loader.Identity;
            return identity.ViewerId + "\n"
                + "FE tag " + m_Loader.ElementTag + " | Caso " + m_Loader.Caso + "\n"
                + "Vz(i): " + Fmt(m_Loader.VzI) + " " + m_Loader.Unidad + "\n"
                + "Vz(j): " + Fmt(m_Loader.VzJ) + " " + m_Loader.Unidad + "\n"
                + "Escala AR 1:10";
        }

        string TextoConDiagrama(ARForceDiagram489 d)
        {
            var identity = m_Loader.Identity;
            string unidad = d.UnidadActual.Replace("*", "·");
            int ultima = Mathf.Max(0, d.StationCount - 1);
            string estado = d.EsNuloActual ? "Diagrama nulo (0)" : "Diagrama normalizado";
            return identity.ViewerId + "\n"
                + "FE tag " + m_Loader.ElementTag + " | Caso " + m_Loader.Caso + "\n"
                + "Diagrama interno: " + d.MagnitudActual + "\n"
                + "x=" + d.XEstacion(0).ToString("0.000", CultureInfo.InvariantCulture) + " m: " + Fmt(d.ValorEstacion(0)) + " " + unidad + "\n"
                + "x=" + d.XEstacion(ultima).ToString("0.000", CultureInfo.InvariantCulture) + " m: " + Fmt(d.ValorEstacion(ultima)) + " " + unidad + "\n"
                + "Escala geometrica AR 1:10\n"
                + estado;
        }

        static int MayorLinea(string texto)
        {
            int max = 1;
            int cur = 0;
            for (int i = 0; i < texto.Length; i++)
            {
                if (texto[i] == '\n')
                {
                    max = Mathf.Max(max, cur);
                    cur = 0;
                }
                else
                {
                    cur++;
                }
            }
            return Mathf.Max(max, cur);
        }

        static int CantidadLineas(string texto)
        {
            int n = 1;
            for (int i = 0; i < texto.Length; i++)
            {
                if (texto[i] == '\n') n++;
            }
            return n;
        }

        // Limite dinamico: si el ancho real del bloque (medido por el renderer)
        // excede el maximo, reescala uniformemente characterSize. Sin divisiones
        // invalidas: se ignora si el renderer aun no reporta geometria (size nulo).
        void AjustarAnchoReal(float maxAncho)
        {
            if (m_TextoGo == null || maxAncho <= 0f) return;
            var rend = m_TextoGo.GetComponent<Renderer>();
            if (rend == null) return;
            float ancho = rend.bounds.size.x;
            if (ancho <= 0.0001f || ancho <= maxAncho) return;
            float factor = Mathf.Clamp(maxAncho / ancho, 0.05f, 5f);
            m_Texto.characterSize *= factor;
        }

        static string Fmt(float v)
        {
            return v.ToString(FormatoNumero, CultureInfo.InvariantCulture);
        }

        // Unico uso de LateUpdate: billboard del rotulo hacia la camara. Sin logs.
        void LateUpdate()
        {
            if (m_TextoGo == null || m_Camera == null) return;
            m_TextoGo.transform.rotation = Quaternion.LookRotation(m_TextoGo.transform.position - m_Camera.transform.position);
        }
    }
}