using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.Rendering;

namespace LabViewer.AR
{
    // Diagrama interno exacto del elemento FE 489 (caso G), leido tal cual del
    // JSON persistido (51 estaciones). El telefono solo dibuja las curvas y sus
    // ordenadas; no reconstruye ningun valor desde el vector de esfuerzos.
    // Selector de magnitud N|Vy|Vz|T|My|Mz (inicial Vz): un toque cambia el
    // diagrama y la etiqueta; los valores provienen de las estaciones internas.
    //
    // Coordinacion de carga (T31D): el JSON se carga y valida internamente y se
    // conserva en memoria ANTES de tocar al loader; las validaciones cruzadas
    // (identidad, tag, viewer_id, longitud, extremos) y la construccion de la
    // geometria esperan el estado final del loader (LoadCompleted) y se ejecutan
    // exactamente una vez. La visibilidad espera el anchor. No hay retrasos fijos
    // ni reintentos por frame; las transiciones AceptarJson /
    // NotificarLoaderTerminado / NotificarAnchor son idempotentes y por-fase.
    [DisallowMultipleComponent]
    public sealed class ARForceDiagram489 : MonoBehaviour
    {
        public static readonly string[] Magnitudes = { "N", "Vy", "Vz", "T", "My", "Mz" };
        static readonly string[] Claves = { "N_kN", "Vy_kN", "Vz_kN", "T_kN_m", "My_kN_m", "Mz_kN_m" };

        const string NombreJSON = "lab_data/edificios/II/results/diagramas_FE_tag489_G.json";
        const string MagnitudInicial = "Vz";
        const int NStationsEsperado = 51;
        const int PasoOrdenadas = 5;

        // Superficie de la cara lateral de la viga (T32). Espesores en metros AR.
        const float AnchoBase = 0.0025f;
        const float AnchoLinea = 0.005f;
        const float AnchoOrdenada = 0.0015f;

        // Margen libre dentro de la silueta: la amplitud nunca rebasa alto/2 - margen.
        const float MargenSilueta = 0.005f;
        // Separacion del plano de la cara para evitar z-fighting.
        const float OffsetSuperficial = 0.0015f;
        // Histeresis del cambio de cara: la camara debe salir de una banda central
        // mayor que el semi-ancho para que el diagrama salte de lado.
        const float HisteresisZ = 0.02f;

        [SerializeField] ARImageAnchorController m_Controller;
        [SerializeField] ARBeam489Loader m_Loader;
        [SerializeField] ARResult489Label m_Label;
        [SerializeField] Transform m_ContentRoot;
        [SerializeField] Camera m_Camera;
        [SerializeField] Material m_BaseMaterial;
        [SerializeField] Material m_DiagramMaterial;
        [SerializeField] Material m_OrdinateMaterial;
        [Tooltip("Amplitud visual maxima del diagrama (m, escala AR 1:10) cuando |valor| == maxAbs. Se recorta a alto/2 - margen de la seccion.")]
        [SerializeField] float m_AmplitudMaxima = 0.035f;

        struct Estacion
        {
            public int k;
            public float xi;
            public float xM;
            public float[] val;
        }

        Estacion[] m_Estaciones;
        float[] m_MaxAbs;
        float m_LongitudM;
        Vector3 m_pIUnity;
        Vector3 m_pJUnity;
        int m_MagIndex = Array.IndexOf(Magnitudes, MagnitudInicial);
        bool m_JsonListo;
        bool m_DataLoaded;
        bool m_Visible;
        bool m_Fallido;
        int m_ConteoConstrucciones;
        int m_ConteoValidaciones;
        int m_ConteoFallos;
        int m_CambiosCara;
        int m_SignoCara = 1;
        float m_AmplitudEfectiva;
        string m_CausaBreve;
        GameObject m_DiagramGo;
        LineRenderer m_Base;
        LineRenderer m_Linea;
        LineRenderer m_Ordenadas;

        public bool DataLoaded => m_DataLoaded;
        public bool JsonListo => m_JsonListo;
        public bool DiagramaVisible => m_Visible;
        public bool Fallido => m_Fallido;
        public int ConteoConstrucciones => m_ConteoConstrucciones;
        public int ConteoValidaciones => m_ConteoValidaciones;
        public int ConteoFallos => m_ConteoFallos;
        public int ConteoCambiosCara => m_CambiosCara;
        public string CausaBreve => m_CausaBreve;
        public int StationCount => m_Estaciones != null ? m_Estaciones.Length : 0;
        public int MagnitudIndex => m_MagIndex;
        public string MagnitudActual => Magnitudes[m_MagIndex];
        public float LongitudM => m_LongitudM;
        public bool EsNuloActual => m_DataLoaded && m_MaxAbs[m_MagIndex] <= 0f;
        public float MaxAbsActual => m_DataLoaded ? m_MaxAbs[m_MagIndex] : 0f;
        public string UnidadActual => UnidadDe(m_MagIndex);
        public float ValorEstacion(int k) => (m_Estaciones != null && k >= 0 && k < m_Estaciones.Length) ? m_Estaciones[k].val[m_MagIndex] : 0f;
        public float XEstacion(int k) => (m_Estaciones != null && k >= 0 && k < m_Estaciones.Length) ? m_Estaciones[k].xM : 0f;

        // Superficie de la cara visible (T32), expuesta para la auditoria Editor.
        public Transform Contenedor => m_DiagramGo != null ? m_DiagramGo.transform : null;
        public int SignoCara => m_SignoCara;
        public float AmplitudMaximaConfigurada => m_AmplitudMaxima;
        public float AmplitudEfectiva => m_AmplitudEfectiva;
        public float MargenSiluetaM => MargenSilueta;
        public float OffsetSuperficialM => OffsetSuperficial;
        public float HisteresisM => HisteresisZ;
        public LineRenderer LineaBase => m_Base;
        public LineRenderer LineaDiagrama => m_Linea;
        public LineRenderer LineaOrdenadas => m_Ordenadas;
        public float OrdenadaDe(int k) => Ordenada(k);

        public static string UnidadDe(int mag) => mag < 3 ? "kN" : "kN*m";

        static GUIStyle s_EstiloStatus;
        static GUIStyle s_EstiloStatusOscuro;

        static GUIStyle ObtenerEstiloStatus()
        {
            if (s_EstiloStatus == null) s_EstiloStatus = CrearEstiloStatus(Color.white);
            return s_EstiloStatus;
        }

        static GUIStyle ObtenerEstiloStatusOscuro()
        {
            if (s_EstiloStatusOscuro == null) s_EstiloStatusOscuro = CrearEstiloStatus(new Color(0f, 0f, 0f, 0.85f));
            return s_EstiloStatusOscuro;
        }

        static GUIStyle CrearEstiloStatus(Color color)
        {
            var gs = new GUIStyle(GUI.skin.label);
            gs.fontSize = 22;
            gs.fontStyle = FontStyle.Bold;
            gs.normal.textColor = color;
            return gs;
        }

        void Start()
        {
            // Identificador del binario en ejecucion: se emite una sola vez, antes
            // de cargar cualquier JSON, para poder confirmar en el telefono que el
            // build corregido (v2, sin la ruta antigua Construir-inmediato) corre.
            Debug.Log("[ARDiag489] Runtime orchestration v2");

            if (m_Loader == null || m_Controller == null)
            {
                Debug.LogError("[ARDiag489] Sin referencias serializadas (loader/controller); diagrama no mostrado");
                return;
            }
            if (m_ContentRoot == null) m_ContentRoot = transform;
            StartCoroutine(Coordinar());
        }

        // Unica coroutine de coordinacion: carga el JSON, espera el estado final
        // del loader y el anchor, delegando las transiciones idempotentes.
        IEnumerator Coordinar()
        {
            Dictionary<string, object> raiz = null;
            string url = UrlStreamingAssets(NombreJSON);
            using (var req = UnityWebRequest.Get(url))
            {
                req.timeout = 30;
                yield return req.SendWebRequest();

                if (req.result != UnityWebRequest.Result.Success)
                {
                    Fallar("No se pudo cargar el JSON de diagramas (" + req.error + "): " + NombreJSON);
                    yield break;
                }

                try
                {
                    raiz = Json.AsObj(Json.Parse(req.downloadHandler.text));
                }
                catch (Exception e)
                {
                    Fallar("JSON de diagramas invalido: " + e.Message);
                    yield break;
                }
                if (raiz == null)
                {
                    Fallar("JSON de diagramas invalido o raiz no es objeto: " + NombreJSON);
                    yield break;
                }
            }

            AceptarJson(raiz);
            if (m_Fallido || !m_JsonListo) yield break;

            // Mismo flujo posterior al JSON que se ejecuta en Android.
            yield return CoordinarDesdeJson();
        }

        // Orquestacion posterior a haber conservado un JSON valido en memoria:
        // sin loader terminal no valida ni construye (espera sin marcar fallo);
        // con loader correcto valida cruzado y construye exactamente una vez;
        // con loader erroneo falla una sola vez y conserva el fallback. Es el
        // mismo metodo de entrada que usa Android (despues de la descarga).
        public IEnumerator CoordinarDesdeJson()
        {
            // Guard obligatorio: no validar/construir/marcar fallo antes de que el
            // loader haya terminado; mientras tanto solo retener los datos.
            while (m_Loader != null && !m_Loader.LoadCompleted) yield return null;
            if (m_Loader == null || !m_Loader.LoadCompleted)
            {
                Fallar("El loader de la viga 489 no quedo disponible");
                yield break;
            }

            NotificarLoaderTerminado();
            if (m_Fallido) yield break;

            while (m_Controller != null && m_Controller.Anchor == null) yield return null;
            if (m_Controller == null) yield break;

            NotificarAnchor();
        }

        // Transicion 1: JSON cargado y validado internamente (sin depender del
        // loader). Conserva estaciones/maxAbs/longitud en memoria y queda a la
        // espera del loader. Idempotente y sin efecto si ya fallo.
        public void AceptarJson(Dictionary<string, object> raiz)
        {
            if (m_Fallido || m_JsonListo) return;

            List<string> errs = Validar(raiz, "II", 489, "EII_CP2_V_029", "G", 3.05f, NStationsEsperado);
            if (errs.Count > 0)
            {
                Fallar("Diagrama tag 489 invalido (" + errs.Count + " problemas): " + string.Join("; ", errs));
                return;
            }

            m_Estaciones = ParseEstaciones(raiz);
            m_MaxAbs = CalcularMaxAbs();
            m_LongitudM = (float)Json.Num(raiz, "longitud_m");
            Vector3? pi = Json.V3(raiz, "p_i_unity");
            Vector3? pj = Json.V3(raiz, "p_j_unity");
            if (pi.HasValue && pj.HasValue)
            {
                m_pIUnity = pi.Value;
                m_pJUnity = pj.Value;
            }

            m_JsonListo = true;
            Debug.Log("[ARDiag489] JSON de diagramas cargado: " + m_Estaciones.Length + " estaciones");
            Debug.Log("[ARDiag489] Esperando datos de la viga 489");
        }

        // Transicion 2: el loader alcanzo su estado final. Sin efecto si el JSON
        // aun no esta o si ya paso (valida y construye exactamente una vez).
        public void NotificarLoaderTerminado()
        {
            if (m_Fallido || !m_JsonListo || m_DataLoaded) return;
            if (m_Loader == null || !m_Loader.LoadCompleted) return;

            if (!m_Loader.LoadSucceeded)
            {
                Fallar("El loader de la viga 489 termino con error: "
                    + (m_Loader.LoadError ?? "sin detalle"));
                return;
            }

            List<string> cruz = CrossValidarConLoader();
            if (cruz.Count > 0)
            {
                Fallar("Diagrama tag 489 invalido (" + cruz.Count + " problemas): " + string.Join("; ", cruz));
                return;
            }

            Debug.Log("[ARDiag489] Validacion cruzada OK");
            m_ConteoValidaciones++;
            m_DataLoaded = true;

            ConstruirGeometria();
            if (m_DiagramGo != null)
            {
                RellenarLineas();
                Debug.Log("[ARDiag489] Diagrama construido: " + MagnitudActual);
            }

            if (m_Controller != null && m_Controller.Anchor != null)
                NotificarAnchor();
        }

        // Transicion 3: anchor disponible. Muestra el diagrama una sola vez y
        // sincroniza el rotulo. Sin efecto si el diagrama no esta validado.
        public void NotificarAnchor()
        {
            if (m_Fallido || !m_DataLoaded || m_Visible) return;
            if (m_Controller == null || m_Controller.Anchor == null) return;
            if (m_DiagramGo == null) return;

            m_DiagramGo.SetActive(true);
            m_Visible = true;
            Debug.Log("[ARDiag489] Diagrama visible: " + MagnitudActual);
            if (m_Label != null) m_Label.ActualizarConDiagrama(this);
        }

        // Cruz entre el JSON (memoria) y el estado final del loader: identidad,
        // tag, viewer_id, edificio, longitudes y extremos locales. Reporta todos
        // los problemas, no solo el primero.
        List<string> CrossValidarConLoader()
        {
            var errs = new List<string>();
            if (m_Loader == null)
            {
                errs.Add("sin referencia al loader");
                return errs;
            }

            // Guard obligatorio: el cruce solo es legitimo con el estado final
            // correcto del loader; antes, retener y no validar ni marcar fallo.
            if (!m_Loader.LoadCompleted || !m_Loader.LoadSucceeded || !m_Loader.DataLoaded)
            {
                errs.Add("loader no termino correctamente (completed=" + m_Loader.LoadCompleted
                    + " ok=" + m_Loader.LoadSucceeded + " data=" + m_Loader.DataLoaded + ")");
                return errs;
            }

            var id = m_Loader.Identity;
            if (id == null)
            {
                errs.Add("identidad de la viga nula");
            }
            else
            {
                if (id.ElementTag != 489) errs.Add("identidad.ElementTag " + id.ElementTag + " != 489");
                if (!EsTxt(id.ViewerId, "EII_CP2_V_029")) errs.Add("identidad.viewer_id '" + id.ViewerId + "' != EII_CP2_V_029");
                if (!EsTxt(id.Building, "II")) errs.Add("identidad.edificio '" + id.Building + "' != II");
            }

            if (!m_Loader.DataLoaded) errs.Add("loader sin DataLoaded; la viga no quedo cargada");
            if (m_Loader.VigaLongitudM <= 0f) errs.Add("longitud real de la viga invalida (" + m_Loader.VigaLongitudM + " m)");

            float lenAR = m_Loader.VigaLongitudAR;
            if (lenAR <= 0.0001f) errs.Add("longitud AR de la viga invalida (" + lenAR + " m)");

            Vector3 a = m_Loader.VigaPILocal;
            Vector3 b = m_Loader.VigaPJLocal;
            float distLocal = Vector3.Distance(a, b);
            if (distLocal <= 0.0001f) errs.Add("extremos locales de la viga invalidos (longitud nula)");
            if (lenAR > 0f && Mathf.Abs(distLocal - lenAR) > 0.001f)
                errs.Add("extremos locales inconsistentes con la longitud AR (dist=" + distLocal + " m, lenAR=" + lenAR + " m)");

            if (Mathf.Abs(m_LongitudM - m_Loader.VigaLongitudM) > 0.001f)
                errs.Add("longitud_m del JSON != longitud de la viga del loader");
            if (Mathf.Abs(Vector3.Distance(m_pIUnity, m_pJUnity) - m_Loader.VigaLongitudM) > 0.001f)
                errs.Add("distancia p_i..p_j != longitud de la viga del loader");

            return errs;
        }

        void Fallar(string mensaje)
        {
            if (m_Fallido) return;
            m_Fallido = true;
            m_ConteoFallos++;
            m_CausaBreve = Breve(mensaje);
            Debug.LogError("[ARDiag489] " + mensaje);
        }

        static string Breve(string s)
        {
            if (string.IsNullOrEmpty(s)) return "error desconocido";
            string t = s.Replace('\n', ' ').Trim();
            return t.Length <= 90 ? t : t.Substring(0, 90) + "…";
        }

        Estacion[] ParseEstaciones(Dictionary<string, object> raiz)
        {
            var list = Json.Arr(raiz, "stations");
            var res = new Estacion[list.Count];
            for (int i = 0; i < list.Count; i++)
            {
                var s = Json.AsObj(list[i]);
                var st = new Estacion();
                st.k = (int)Json.Num(s, "k");
                st.xi = (float)Json.Num(s, "xi");
                st.xM = (float)Json.Num(s, "x_m");
                st.val = new float[6];
                for (int m = 0; m < 6; m++) st.val[m] = (float)Json.Num(s, Claves[m]);
                res[i] = st;
            }
            return res;
        }

        float[] CalcularMaxAbs()
        {
            var mx = new float[6];
            for (int m = 0; m < 6; m++)
            {
                float max = 0f;
                for (int i = 0; i < m_Estaciones.Length; i++)
                    max = Mathf.Max(max, Mathf.Abs(m_Estaciones[i].val[m]));
                mx[m] = max;
            }
            return mx;
        }

        // Geometria sobre la cara lateral visible de la viga (T32). El contenedor
        // se engacha al transform de la viga que creo el loader: la X local es el
        // eje longitudinal, la Y local la ordenada del diagrama (base en el centro
        // de la cara, y = 0) y la Z local la profundidad, a ancho/2 + offset del
        // plano de la cara. Solo se dibuja; ningun valor del JSON se modifica.
        void ConstruirGeometria()
        {
            // Guard obligatorio: requiere loader terminal correcto y exactamente
            // una construccion (idempotente). Si no se dan las condiciones, se
            // retienen los datos y no se construye ni se marca fallo.
            if (m_Loader == null || !m_Loader.LoadCompleted || !m_Loader.LoadSucceeded || !m_Loader.DataLoaded) return;
            if (m_DiagramGo != null) return;

            float lenAR = m_Loader.VigaLongitudAR;
            if (lenAR <= 0.0001f) return;

            // La amplitud nunca puede rebasar la silueta de la seccion.
            float alto = m_Loader.VigaAltoAR;
            float maximo = alto * 0.5f - MargenSilueta;
            if (maximo <= 0f) return;
            m_AmplitudEfectiva = Mathf.Min(m_AmplitudMaxima, maximo);

            Transform viga = m_Loader.VigaTransform;
            if (viga == null) return;

            // El contenedor comparte el SISTEMA DE EJES de la viga (X longitudinal,
            // Y ordenada del diagrama, Z normal de las caras laterales) tomando su
            // pose, pero cuelga del AR Content sin escalar: colgarlo del transform
            // escalado de la viga haria que Unity normalice posiciones y espesores
            // con una escala no uniforme (0.305, 0.080, 0.030). Sigue siendo hijo
            // del anchor a traves del AR Content.
            var go = new GameObject("AR489_Diagrama");
            go.transform.SetParent(m_ContentRoot != null ? m_ContentRoot : transform, true);
            go.transform.localScale = Vector3.one;
            go.transform.SetPositionAndRotation(viga.position, viga.rotation);
            go.SetActive(false);

            // Un LineRenderer por hijo: Unity no permite dos LineRenderer en un
            // mismo GameObject (el segundo AddComponent devuelve null).
            m_Base = CrearLinea(go, "Base", m_BaseMaterial, AnchoBase, 0);
            m_Ordenadas = CrearLinea(go, "Ordenadas", m_OrdinateMaterial, AnchoOrdenada, 1);
            m_Linea = CrearLinea(go, "Diagrama", m_DiagramMaterial, AnchoLinea, 2);

            m_DiagramGo = go;
            AplicarCara();
            m_ConteoConstrucciones++;
        }

        // Coloca el contenedor sobre la cara lateral visible. Es la UNICA operacion
        // que se repite en el tiempo: no reconstruye las 51 estaciones ni toca los
        // puntos, solo la posicion del contenedor.
        void AplicarCara()
        {
            if (m_DiagramGo == null || m_Loader == null) return;
            Transform viga = m_Loader.VigaTransform;
            if (viga == null) return;
            float z = m_SignoCara * (m_Loader.VigaAnchoAR * 0.5f + OffsetSuperficial);
            m_DiagramGo.transform.position = viga.position + viga.TransformDirection(0f, 0f, z);
        }

        // Cara visible a partir de la posicion de la camara expresada en el
        // sistema local de la viga (Z local = normal de las caras laterales).
        // Solo cambia de lado cuando la camara sale de la banda central
        // (histeresis), de modo que no parpadea al cruzar el plano medio.
        public bool ActualizarCaraVisible(Vector3 camaraMundo)
        {
            if (m_DiagramGo == null || m_Loader == null) return false;
            Transform viga = m_Loader.VigaTransform;
            if (viga == null) return false;

            Vector3 local = viga.InverseTransformPoint(camaraMundo);
            int signo = local.z > 0f ? 1 : (local.z < 0f ? -1 : 0);
            if (signo == 0 || signo == m_SignoCara) return false;
            if (Mathf.Abs(local.z) < HisteresisZ) return false;

            m_SignoCara = signo;
            m_CambiosCara++;
            AplicarCara();
            return true;
        }

        // Unico uso de LateUpdate: elegir la cara visible. No reconstruye nada.
        void LateUpdate()
        {
            if (m_DiagramGo == null) return;
            Camera cam = ResolverCamara();
            if (cam == null) return;
            ActualizarCaraVisible(cam.transform.position);
        }

        Camera ResolverCamara()
        {
            if (m_Camera == null && Application.isPlaying) m_Camera = Camera.main;
            return m_Camera;
        }

        LineRenderer CrearLinea(GameObject raiz, string nombre, Material mat, float ancho, int orden)
        {
            var child = new GameObject(nombre);
            child.transform.SetParent(raiz.transform, false);
            child.transform.localPosition = Vector3.zero;
            child.transform.localRotation = Quaternion.identity;
            child.transform.localScale = Vector3.one;
            var lr = child.AddComponent<LineRenderer>();
            if (lr != null) Configurar(lr, mat, ancho, orden);
            return lr;
        }

        void Configurar(LineRenderer lr, Material mat, float ancho, int orden)
        {
            if (lr == null) return;
            lr.useWorldSpace = false;
            lr.loop = false;
            lr.alignment = LineAlignment.View;
            lr.textureMode = LineTextureMode.Stretch;
            lr.startWidth = ancho;
            lr.endWidth = ancho;
            lr.shadowCastingMode = ShadowCastingMode.Off;
            lr.receiveShadows = false;
            if (mat != null) lr.sharedMaterial = mat;
            // Orden explicito de dibujo: las tres lineas son coplanares en la cara
            // y el material es transparente (sin ZWrite), asi que el orden decide
            // el solape en vez del z-fighting.
            lr.sortingOrder = orden;
            lr.positionCount = 0;
        }

        void RellenarLineas()
        {
            if (m_Estaciones == null || m_DiagramGo == null) return;
            float lenAR = m_Loader.VigaLongitudAR;

            m_Base.positionCount = 2;
            m_Base.SetPosition(0, new Vector3(-lenAR * 0.5f, 0f, 0f));
            m_Base.SetPosition(1, new Vector3(lenAR * 0.5f, 0f, 0f));

            bool nulo = EsNuloActual;
            if (nulo)
            {
                m_Linea.positionCount = 0;
                m_Ordenadas.positionCount = 0;
                return;
            }

            m_Linea.positionCount = m_Estaciones.Length;
            for (int i = 0; i < m_Estaciones.Length; i++)
                m_Linea.SetPosition(i, PuntoLocal(i, lenAR));

            int nOrd = m_Estaciones.Length / PasoOrdenadas + 1;
            m_Ordenadas.positionCount = nOrd * 2;
            for (int i = 0; i < nOrd; i++)
            {
                int k = Mathf.Min(i * PasoOrdenadas, m_Estaciones.Length - 1);
                Vector3 baseP = new Vector3((m_Estaciones[k].xi - 0.5f) * lenAR, 0f, 0f);
                Vector3 punta = PuntoLocal(k, lenAR);
                m_Ordenadas.SetPosition(i * 2, baseP);
                m_Ordenadas.SetPosition(i * 2 + 1, punta);
            }
        }

        Vector3 PuntoLocal(int k, float lenAR)
        {
            return new Vector3((m_Estaciones[k].xi - 0.5f) * lenAR, Ordenada(k), 0f);
        }

        // Normalizacion por magnitud conservada: solo cambia la escala grafica
        // (amplitud efectiva recortada a la silueta de la seccion). Estaciones,
        // signos, valores y forma vienen del JSON sin modificar.
        float Ordenada(int k)
        {
            float maxAbs = m_MaxAbs[m_MagIndex];
            if (maxAbs <= 0f) return 0f;
            return (m_Estaciones[k].val[m_MagIndex] / maxAbs) * m_AmplitudEfectiva;
        }

        void OnGUI()
        {
            Rect safe = Screen.safeArea;

            // Estado visible de diagnostico (sin tapar la camara): mientras el
            // diagrama carga se muestra la indicacion; si fallo, la causa breve;
            // al cargar correctamente la indicacion se reemplaza por el selector.
            if (m_Fallido)
            {
                GUI.Label(new Rect(safe.xMin + 13, safe.yMin + 13, safe.width - 26, 46),
                    "Diagramas no disponibles: " + m_CausaBreve, ObtenerEstiloStatusOscuro());
                GUI.Label(new Rect(safe.xMin + 12, safe.yMin + 12, safe.width - 26, 46),
                    "Diagramas no disponibles: " + m_CausaBreve, ObtenerEstiloStatus());
                return;
            }
            if (!m_DataLoaded)
            {
                GUI.Label(new Rect(safe.xMin + 13, safe.yMin + 13, safe.width - 26, 46),
                    "Diagramas: cargando…", ObtenerEstiloStatusOscuro());
                GUI.Label(new Rect(safe.xMin + 12, safe.yMin + 12, safe.width - 26, 46),
                    "Diagramas: cargando…", ObtenerEstiloStatus());
                return;
            }

            const float margen = 18f;
            const float separacion = 10f;
            const float alto = 72f;
            int n = Magnitudes.Length;
            float ancho = (safe.width - margen * 2f - separacion * (n - 1)) / n;
            if (ancho < 40f) return;

            float y = safe.yMax - margen - alto;
            for (int i = 0; i < n; i++)
            {
                var rect = new Rect(safe.xMin + margen + i * (ancho + separacion), y, ancho, alto);
                bool on = i == m_MagIndex;
                bool click = GUI.Button(rect, Magnitudes[i], on ? ObtenerEstiloBotonActivo() : ObtenerEstiloBotonInactivo());
                if (click && !on) CambiarMagnitud(i);
            }
        }

        // Contraste del selector (T32): fondo oscuro semitransparente, texto
        // blanco y la magnitud activa en cian. Solo cambia el aspecto; las seis
        // opciones y el comportamiento tactil son los ya probados.
        static GUIStyle s_EstiloBotonInactivo;
        static GUIStyle s_EstiloBotonActivo;

        static GUIStyle ObtenerEstiloBotonInactivo()
        {
            if (s_EstiloBotonInactivo == null)
                s_EstiloBotonInactivo = CrearEstiloBoton(
                    new Color(0.05f, 0.06f, 0.08f, 0.88f), new Color(0.10f, 0.12f, 0.15f, 0.92f), Color.white);
            return s_EstiloBotonInactivo;
        }

        static GUIStyle ObtenerEstiloBotonActivo()
        {
            if (s_EstiloBotonActivo == null)
                s_EstiloBotonActivo = CrearEstiloBoton(
                    new Color(0.00f, 0.55f, 0.70f, 0.95f), new Color(0.00f, 0.70f, 0.85f, 1f), Color.white);
            return s_EstiloBotonActivo;
        }

        static GUIStyle CrearEstiloBoton(Color fondo, Color fondoHover, Color texto)
        {
            var gs = new GUIStyle(GUI.skin.button);
            gs.fontSize = 30;
            gs.fontStyle = FontStyle.Bold;
            gs.alignment = TextAnchor.MiddleCenter;
            gs.normal.textColor = texto;
            gs.normal.background = CrearTextura(fondo);
            gs.hover.textColor = texto;
            gs.hover.background = CrearTextura(fondoHover);
            gs.active.textColor = texto;
            gs.active.background = CrearTextura(fondoHover);
            gs.focused.textColor = texto;
            gs.focused.background = CrearTextura(fondo);
            return gs;
        }

        static Texture2D CrearTextura(Color c)
        {
            var tex = new Texture2D(1, 1, TextureFormat.RGBA32, false)
            {
                hideFlags = HideFlags.HideAndDontSave
            };
            tex.SetPixel(0, 0, c);
            tex.Apply();
            return tex;
        }

        void CambiarMagnitud(int mag)
        {
            if (mag < 0 || mag >= Magnitudes.Length || mag == m_MagIndex || !m_DataLoaded) return;
            m_MagIndex = mag;
            RellenarLineas();
            if (m_Label != null) m_Label.ActualizarConDiagrama(this);
            Debug.Log("[ARDiag489] Magnitud seleccionada: " + Magnitudes[m_MagIndex]);
        }

        // Seam de auditoria Editor: delega en la MISMA rutina que usa el toque del
        // selector, sin duplicar logica ni alterar el comportamiento tactil.
        public void SeleccionarMagnitud(int mag)
        {
            CambiarMagnitud(mag);
        }

        // Validacion estructural y semantica del JSON de diagramas. Se usa tambien
        // desde la auditoria Editor (sin PlayMode) para verificar los 51 estaciones,
        // los seis componentes, unidades, indices y comprobaciones embebidas.
        public static List<string> Validar(Dictionary<string, object> raiz,
            string edificioEsperado, int tagEsperado, string viewerEsperado, string casoEsperado,
            float longitudEsperadaM, int nStationsEsperado)
        {
            var errs = new List<string>();
            if (raiz == null)
            {
                errs.Add("raiz no es objeto");
                return errs;
            }

            string formato = Json.Str(raiz, "formato");
            if (!EsTxt(formato, "diagrama_interno_FE_v1")) errs.Add("formato != diagrama_interno_FE_v1 (" + (formato ?? "null") + ")");
            if (Json.Num(raiz, "version") != 1) errs.Add("version != 1");

            string edificio = Json.Str(raiz, "edificio");
            if (!EsTxt(edificio, edificioEsperado)) errs.Add("edificio != " + edificioEsperado + " (" + (edificio ?? "null") + ")");

            if ((int)Json.Num(raiz, "elementTag") != tagEsperado) errs.Add("elementTag != " + tagEsperado);

            string viewerId = Json.Str(raiz, "viewer_id");
            if (!EsTxt(viewerId, viewerEsperado)) errs.Add("viewer_id != " + viewerEsperado + " (" + (viewerId ?? "null") + ")");

            string caso = Json.Str(raiz, "caso");
            if (!EsTxt(caso, casoEsperado)) errs.Add("caso != " + casoEsperado + " (" + (caso ?? "null") + ")");

            string nivel = Json.Str(raiz, "nivel");
            if (!EsTxt(nivel, "EII_CP2")) errs.Add("nivel != EII_CP2 (" + (nivel ?? "null") + ")");

            var nodos = raiz.TryGetValue("nodos", out var nv) ? Json.AsObj(nv) : null;
            if (nodos == null)
            {
                errs.Add("sin nodos");
            }
            else
            {
                if (!EsTxt(Json.Str(nodos, "i"), "487")) errs.Add("nodos.i != 487");
                if (!EsTxt(Json.Str(nodos, "j"), "488")) errs.Add("nodos.j != 488");
            }

            double L = Json.Num(raiz, "longitud_m");
            if (Math.Abs(L - longitudEsperadaM) > 0.001) errs.Add("longitud_m != " + longitudEsperadaM);

            int nSt = (int)Json.Num(raiz, "n_stations", -1);
            if (nSt != nStationsEsperado) errs.Add("n_stations != " + nStationsEsperado);

            var stations = Json.Arr(raiz, "stations");
            if (stations == null)
            {
                errs.Add("sin lista stations");
            }
            else if (stations.Count != nStationsEsperado)
            {
                errs.Add("stations.Count(" + stations.Count + ") != n_stations(" + nStationsEsperado + ")");
            }
            else
            {
                for (int i = 0; i < stations.Count; i++)
                {
                    var s = Json.AsObj(stations[i]);
                    if (s == null)
                    {
                        errs.Add("station[" + i + "] no es objeto");
                        continue;
                    }
                    int k = (int)Json.Num(s, "k", -1);
                    float xi = (float)Json.Num(s, "xi", -1);
                    float xm = (float)Json.Num(s, "x_m", -1);
                    if (k != i) errs.Add("station[" + i + "] tiene k=" + k + " != indice");
                    if (i == 0 && Mathf.Abs(xi) > 0.0001f) errs.Add("station[0] xi != 0");
                    if (i == stations.Count - 1 && Mathf.Abs(xi - 1f) > 0.0001f) errs.Add("station[last] xi != 1");
                    if (i == stations.Count - 1 && Mathf.Abs(xm - (float)L) > 0.0001f) errs.Add("station[last] x_m != L");
                    if (xm < -0.0001f || xm > L + 0.0001f) errs.Add("station[" + i + "] x_m fuera de [0,L]");
                    if (i > 0)
                    {
                        var prev = Json.AsObj(stations[i - 1]);
                        if (prev != null && Json.Num(s, "xi", -1) < Json.Num(prev, "xi", -1) - 1e-6)
                            errs.Add("stations no ordenadas por xi en " + i);
                    }
                    for (int m = 0; m < 6; m++)
                    {
                        double v = Json.Num(s, Claves[m]);
                        if (double.IsNaN(v) || double.IsInfinity(v)) errs.Add("station[" + i + "] " + Claves[m] + " no finito");
                    }
                }
            }

            var unidades = raiz.TryGetValue("unidades", out var uv) ? Json.AsObj(uv) : null;
            if (unidades == null)
            {
                errs.Add("sin unidades");
            }
            else
            {
                if (!EsTxt(Json.Str(unidades, "fuerza"), "kN")) errs.Add("unidades.fuerza != kN");
                if (!EsTxt(Json.Str(unidades, "momento"), "kN*m")) errs.Add("unidades.momento != kN*m");
                if (!EsTxt(Json.Str(unidades, "longitud"), "m")) errs.Add("unidades.longitud != m");
            }

            var indices = raiz.TryGetValue("indices_componentes", out var iv) ? Json.AsObj(iv) : null;
            if (indices == null)
            {
                errs.Add("sin indices_componentes");
            }
            else
            {
                if ((int)Json.Num(indices, "N_i", -1) != 0) errs.Add("indices_componentes.N_i != 0");
                if ((int)Json.Num(indices, "Vy_i", -1) != 1) errs.Add("indices_componentes.Vy_i != 1");
                if ((int)Json.Num(indices, "Vz_i", -1) != 2) errs.Add("indices_componentes.Vz_i != 2");
                if ((int)Json.Num(indices, "T_i", -1) != 3) errs.Add("indices_componentes.T_i != 3");
                if ((int)Json.Num(indices, "My_i", -1) != 4) errs.Add("indices_componentes.My_i != 4");
                if ((int)Json.Num(indices, "Mz_i", -1) != 5) errs.Add("indices_componentes.Mz_i != 5");
                if ((int)Json.Num(indices, "N_j", -1) != 6) errs.Add("indices_componentes.N_j != 6");
                if ((int)Json.Num(indices, "Vy_j", -1) != 7) errs.Add("indices_componentes.Vy_j != 7");
                if ((int)Json.Num(indices, "Vz_j", -1) != 8) errs.Add("indices_componentes.Vz_j != 8");
                if ((int)Json.Num(indices, "T_j", -1) != 9) errs.Add("indices_componentes.T_j != 9");
                if ((int)Json.Num(indices, "My_j", -1) != 10) errs.Add("indices_componentes.My_j != 10");
                if ((int)Json.Num(indices, "Mz_j", -1) != 11) errs.Add("indices_componentes.Mz_j != 11");
            }

            var comp = Json.Arr(raiz, "comprobaciones");
            if (comp == null || comp.Count == 0)
            {
                errs.Add("sin comprobaciones");
            }
            else
            {
                for (int i = 0; i < comp.Count; i++)
                {
                    var c = Json.AsObj(comp[i]);
                    if (c == null || !Json.Bool(c, "ok"))
                        errs.Add("comprobacion[" + i + "] no ok (" + (c != null ? Json.Str(c, "check") : "null") + ")");
                }
            }

            if (!Json.Bool(raiz, "sin_cargas_interiores"))
                errs.Add("sin_cargas_interiores != true");

            var pf = raiz.TryGetValue("payload_fuente", out var pfv) ? Json.AsObj(pfv) : null;
            if (pf == null)
            {
                errs.Add("sin payload_fuente");
            }
            else
            {
                if (!EsTxt(Json.Str(pf, "archivo"), "esfuerzos_FE_EDIFICIO_II.json"))
                    errs.Add("payload_fuente.archivo != esfuerzos_FE_EDIFICIO_II.json");
                if (string.IsNullOrEmpty(Json.Str(pf, "sha256")))
                    errs.Add("payload_fuente.sha256 vacio");
            }

            Vector3? pi = Json.V3(raiz, "p_i_unity");
            Vector3? pj = Json.V3(raiz, "p_j_unity");
            if (!pi.HasValue || !pj.HasValue)
            {
                errs.Add("sin p_i_unity/p_j_unity");
            }
            else if (Mathf.Abs(Vector3.Distance(pi.Value, pj.Value) - (float)L) > 0.001f)
            {
                errs.Add("distancia p_i..p_j != longitud_m");
            }

            return errs;
        }

        static string UrlStreamingAssets(string rel)
        {
            string path = Path.Combine(Application.streamingAssetsPath, rel).Replace("\\", "/");
            if (Application.platform == RuntimePlatform.Android)
                return path;
            return "file://" + path;
        }

        static bool EsTxt(string a, string b)
        {
            return !string.IsNullOrEmpty(a) && string.Equals(a, b, StringComparison.Ordinal);
        }
    }
}