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
    [DisallowMultipleComponent]
    public sealed class ARForceDiagram489 : MonoBehaviour
    {
        public static readonly string[] Magnitudes = { "N", "Vy", "Vz", "T", "My", "Mz" };
        static readonly string[] Claves = { "N_kN", "Vy_kN", "Vz_kN", "T_kN_m", "My_kN_m", "Mz_kN_m" };

        const string NombreJSON = "lab_data/edificios/II/results/diagramas_FE_tag489_G.json";
        const string MagnitudInicial = "Vz";
        const int NStationsEsperado = 51;
        const int PasoOrdenadas = 5;
        const float AnchoBase = 0.002f;
        const float AnchoLinea = 0.004f;
        const float AnchoOrdenada = 0.0015f;

        [SerializeField] ARImageAnchorController m_Controller;
        [SerializeField] ARBeam489Loader m_Loader;
        [SerializeField] ARResult489Label m_Label;
        [SerializeField] Transform m_ContentRoot;
        [SerializeField] Material m_BaseMaterial;
        [SerializeField] Material m_DiagramMaterial;
        [SerializeField] Material m_OrdinateMaterial;
        [Tooltip("Amplitud visual maxima del diagrama (m, escala AR 1:10) cuando |valor| == maxAbs.")]
        [SerializeField] float m_AmplitudMaxima = 0.065f;

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
        int m_MagIndex = Array.IndexOf(Magnitudes, MagnitudInicial);
        bool m_DataLoaded;
        bool m_Visible;
        GameObject m_DiagramGo;
        LineRenderer m_Base;
        LineRenderer m_Linea;
        LineRenderer m_Ordenadas;

        public bool DataLoaded => m_DataLoaded;
        public int StationCount => m_Estaciones != null ? m_Estaciones.Length : 0;
        public int MagnitudIndex => m_MagIndex;
        public string MagnitudActual => Magnitudes[m_MagIndex];
        public float LongitudM => m_LongitudM;
        public bool EsNuloActual => m_DataLoaded && m_MaxAbs[m_MagIndex] <= 0f;
        public float MaxAbsActual => m_DataLoaded ? m_MaxAbs[m_MagIndex] : 0f;
        public string UnidadActual => UnidadDe(m_MagIndex);
        public float ValorEstacion(int k) => (m_Estaciones != null && k >= 0 && k < m_Estaciones.Length) ? m_Estaciones[k].val[m_MagIndex] : 0f;
        public float XEstacion(int k) => (m_Estaciones != null && k >= 0 && k < m_Estaciones.Length) ? m_Estaciones[k].xM : 0f;

        public static string UnidadDe(int mag) => mag < 3 ? "kN" : "kN*m";

        void Start()
        {
            if (m_Loader == null || m_Controller == null)
            {
                Debug.LogError("[ARDiag489] Sin referencias serializadas (loader/controller); diagrama no mostrado");
                return;
            }
            if (m_ContentRoot == null) m_ContentRoot = transform;
            StartCoroutine(Cargar());
        }

        IEnumerator Cargar()
        {
            string url = UrlStreamingAssets(NombreJSON);
            using (var req = UnityWebRequest.Get(url))
            {
                req.timeout = 30;
                yield return req.SendWebRequest();

                if (req.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError("[ARDiag489] No se pudo cargar el JSON de diagramas (" + req.error + "): " + NombreJSON);
                    yield break;
                }

                Dictionary<string, object> raiz = null;
                try
                {
                    raiz = Json.AsObj(Json.Parse(req.downloadHandler.text));
                }
                catch (Exception e)
                {
                    Debug.LogError("[ARDiag489] JSON de diagramas invalido: " + e.Message);
                    yield break;
                }

                if (raiz == null)
                {
                    Debug.LogError("[ARDiag489] JSON de diagramas invalido o raiz no es objeto: " + NombreJSON);
                    yield break;
                }

                Construir(raiz);
            }
        }

        void Construir(Dictionary<string, object> raiz)
        {
            List<string> errs = Validar(raiz, "II", 489, "EII_CP2_V_029", "G", 3.05f, NStationsEsperado);

            if (m_Loader != null)
            {
                float lenJson = (float)Json.Num(raiz, "longitud_m");
                if (Mathf.Abs(lenJson - m_Loader.VigaLongitudM) > 0.001f)
                    errs.Add("longitud_m del JSON != longitud de la viga del loader");

                Vector3? pi = Json.V3(raiz, "p_i_unity");
                Vector3? pj = Json.V3(raiz, "p_j_unity");
                if (pi.HasValue && pj.HasValue &&
                    Mathf.Abs(Vector3.Distance(pi.Value, pj.Value) - m_Loader.VigaLongitudM) > 0.001f)
                    errs.Add("distancia p_i..p_j != longitud de la viga del loader");
            }

            if (errs.Count > 0)
            {
                Debug.LogError("[ARDiag489] Diagrama tag 489 invalido (" + errs.Count + " problemas); primero: " + errs[0]);
                return;
            }

            m_Estaciones = ParseEstaciones(raiz);
            m_MaxAbs = CalcularMaxAbs();
            m_LongitudM = (float)Json.Num(raiz, "longitud_m");
            m_DataLoaded = true;

            Debug.Log("[ARDiag489] Diagrama tag 489 cargado: " + m_Estaciones.Length + " estaciones; "
                + "Vz=" + m_Estaciones[0].val[2].ToString("0.000", CultureInfo.InvariantCulture) + " kN; "
                + "T=" + m_Estaciones[0].val[3].ToString("0.000", CultureInfo.InvariantCulture) + " kN*m; "
                + "My_i=" + m_Estaciones[0].val[4].ToString("0.000", CultureInfo.InvariantCulture) + " kN*m; "
                + "My_L=" + m_Estaciones[m_Estaciones.Length - 1].val[4].ToString("0.000", CultureInfo.InvariantCulture) + " kN*m");

            ConstruirGeometria();
            if (m_DiagramGo != null)
                RellenarLineas();

            if (m_Label != null) m_Label.ActualizarConDiagrama(this);
            StartCoroutine(EsperarVisibilidad());
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

        void ConstruirGeometria()
        {
            Vector3 aLocal = m_Loader.VigaPILocal;
            Vector3 bLocal = m_Loader.VigaPJLocal;
            float lenAR = m_Loader.VigaLongitudAR;
            if (lenAR <= 0.0001f) return;

            var go = new GameObject("AR489_Diagrama");
            go.transform.SetParent(m_ContentRoot != null ? m_ContentRoot : transform, false);
            go.transform.localPosition = 0.5f * (aLocal + bLocal);
            go.transform.localRotation = (bLocal - aLocal).sqrMagnitude > 0.0001f
                ? Quaternion.FromToRotation(Vector3.right, (bLocal - aLocal).normalized)
                : Quaternion.identity;
            go.SetActive(false);

            m_Base = go.AddComponent<LineRenderer>();
            m_Linea = go.AddComponent<LineRenderer>();
            m_Ordenadas = go.AddComponent<LineRenderer>();
            Configurar(m_Base, m_BaseMaterial, AnchoBase);
            Configurar(m_Linea, m_DiagramMaterial, AnchoLinea);
            Configurar(m_Ordenadas, m_OrdinateMaterial, AnchoOrdenada);

            m_DiagramGo = go;
        }

        void Configurar(LineRenderer lr, Material mat, float ancho)
        {
            lr.useWorldSpace = false;
            lr.loop = false;
            lr.startWidth = ancho;
            lr.endWidth = ancho;
            lr.shadowCastingMode = ShadowCastingMode.Off;
            lr.receiveShadows = false;
            if (mat != null) lr.sharedMaterial = mat;
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

        float Ordenada(int k)
        {
            float maxAbs = m_MaxAbs[m_MagIndex];
            if (maxAbs <= 0f) return 0f;
            return (m_Estaciones[k].val[m_MagIndex] / maxAbs) * m_AmplitudMaxima;
        }

        IEnumerator EsperarVisibilidad()
        {
            while (m_Controller == null || m_Controller.Anchor == null
                   || m_Loader == null || !m_Loader.DataLoaded || m_Loader.Identity == null)
            {
                yield return null;
            }

            if (m_DiagramGo == null || m_Visible) yield break;

            if (!EsConsistenteConIdentity())
            {
                Debug.LogError("[ARDiag489] Identidad del loader no coincide con el diagrama; diagrama oculto");
                yield break;
            }

            m_DiagramGo.SetActive(true);
            m_Visible = true;
            if (m_Label != null) m_Label.ActualizarConDiagrama(this);
        }

        bool EsConsistenteConIdentity()
        {
            var id = m_Loader.Identity;
            if (id == null) return false;
            return id.ElementTag == 489
                && string.Equals(id.ViewerId, "EII_CP2_V_029", StringComparison.Ordinal)
                && string.Equals(id.Building, "II", StringComparison.Ordinal);
        }

        void OnGUI()
        {
            if (!m_DataLoaded || !m_Visible) return;
            Rect safe = Screen.safeArea;
            const float margen = 14f;
            const float alto = 64f;
            int n = Magnitudes.Length;
            float ancho = (safe.width - margen * (n + 1)) / n;
            if (ancho < 40f) return;

            float y = safe.yMax - margen - alto;
            for (int i = 0; i < n; i++)
            {
                var rect = new Rect(safe.xMin + margen + i * (ancho + margen), y, ancho, alto);
                bool on = i == m_MagIndex;
                Color prev = GUI.backgroundColor;
                GUI.backgroundColor = on
                    ? new Color(0.10f, 0.55f, 0.95f, 1f)
                    : new Color(0.12f, 0.12f, 0.14f, 0.78f);
                bool click = GUI.Button(rect, Magnitudes[i]);
                GUI.backgroundColor = prev;
                if (click && !on) CambiarMagnitud(i);
            }
        }

        void CambiarMagnitud(int mag)
        {
            if (mag < 0 || mag >= Magnitudes.Length || mag == m_MagIndex || !m_DataLoaded) return;
            m_MagIndex = mag;
            RellenarLineas();
            if (m_Label != null) m_Label.ActualizarConDiagrama(this);
            Debug.Log("[ARDiag489] Magnitud seleccionada: " + Magnitudes[m_MagIndex]);
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