using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;

namespace LabViewer.AR
{
    // La geometria (viga del tag 489) y el resultado (caso G del mismo tag)
    // comparten el mismo elemento FE. OpenSees produjo previamente el vector de
    // esfuerzos de 12 componentes; el telefono solo lee y presenta ese resultado.
    [DisallowMultipleComponent]
    public sealed class ARBeam489Loader : MonoBehaviour
    {
        [SerializeField] ARImageAnchorController m_Controller;
        [SerializeField] Transform m_ContentRoot;
        [SerializeField] Material m_BeamMaterial;
        [SerializeField] int m_ElementTag = 489;
        [SerializeField] string m_Building = "II";
        [SerializeField] string m_ExpectedViewerId = "EII_CP2_V_029";
        [SerializeField] float m_ARScale = 0.10f;
        [SerializeField] Vector2 m_SectionM = new Vector2(0.30f, 0.80f);

        const string BeamName = "FE_TAG_{0}_{1}";
        const string ResultadosAgo = "lab_data/edificios/II/results/esfuerzos_FE_EDIFICIO_II.json";
        const string CasoG = "G";

        GameObject m_Beam;
        bool m_BeamVisible;
        bool m_DataLoaded;
        float m_VzI;
        float m_VzJ;
        float m_VigaLongitudM;
        float m_VigaLongitudAR;
        Vector3 m_VigaCentroLocal;
        Vector3 m_VigaPILocal;
        Vector3 m_VigaPJLocal;
        ARElementIdentity m_Identity;
        bool m_LoadCompleted;
        bool m_LoadSucceeded;
        string m_LoadError;

        public bool DataLoaded => m_DataLoaded;
        public string Caso => CasoG;
        public float VzI => m_VzI;
        public float VzJ => m_VzJ;
        public string Unidad => "kN";
        public ARElementIdentity Identity => m_Identity;
        // Estado final de la carga del loader. LoadCompleted se activa siempre
        // (con exito o con error) para que el diagrama no espere indefinidamente.
        public bool LoadCompleted => m_LoadCompleted;
        public bool LoadSucceeded => m_LoadSucceeded;
        public string LoadError => m_LoadError;
        public int ElementTag => m_ElementTag;
        public float VigaLongitudM => m_VigaLongitudM;
        public float VigaLongitudAR => m_VigaLongitudAR;
        public Vector3 VigaCentroLocal => m_VigaCentroLocal;
        public Vector3 VigaPILocal => m_VigaPILocal;
        public Vector3 VigaPJLocal => m_VigaPJLocal;
        public Vector3 VigaTamanoAR => m_Beam != null ? m_Beam.transform.localScale : Vector3.zero;

        void Awake()
        {
            if (m_Controller == null) m_Controller = GetComponent<ARImageAnchorController>();
            if (m_ContentRoot == null) m_ContentRoot = transform;
        }

        void Start()
        {
            StartCoroutine(CargarJson());
        }

        IEnumerator CargarJson()
        {
            Dictionary<string, object> raiz = null;
            string url = UrlStreamingAssets(ResultadosAgo);
            using (var req = UnityWebRequest.Get(url))
            {
                req.timeout = 30;
                yield return req.SendWebRequest();

                if (req.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError("[AR489] No se pudo cargar el JSON de esfuerzos (" + req.error + "): " + ResultadosAgo);
                    TerminarFallo("No se pudo cargar el JSON de esfuerzos: " + req.error);
                    yield break;
                }

                try
                {
                    raiz = Json.AsObj(Json.Parse(req.downloadHandler.text));
                }
                catch (Exception e)
                {
                    Debug.LogError("[AR489] JSON de esfuerzos invalido: " + e.Message);
                    TerminarFallo("JSON de esfuerzos invalido: " + e.Message);
                    yield break;
                }
                if (raiz == null)
                {
                    Debug.LogError("[AR489] JSON invalido o raiz no es objeto: " + ResultadosAgo);
                    TerminarFallo("JSON invalido o raiz no es objeto: " + ResultadosAgo);
                    yield break;
                }

                Debug.Log("[AR489] JSON cargado");
            }

            // Fuera del bloque with yield: cualquier excepcion inesperada en la
            // construccion sincrona tambien debe dejar LoadCompleted activo.
            try
            {
                ConstruirViga(raiz);
            }
            catch (Exception e)
            {
                TerminarFallo("excepcion al cargar esfuerzos: " + e.Message);
            }
        }

        void ConstruirViga(Dictionary<string, object> raiz)
        {
            string edificio = Json.Str(raiz, "edificio");
            if (!EsTxt(edificio, m_Building))
            {
                Debug.LogError("[AR489] Edificio del JSON '" + (edificio ?? "null") + "' != esperado '" + m_Building + "'");
                TerminarFallo("edificio del JSON != " + m_Building);
                return;
            }

            var arr = Json.Arr(raiz, "elementos");
            var hits = new List<Dictionary<string, object>>();
            if (arr != null)
            {
                foreach (var it in arr)
                {
                    var item = Json.AsObj(it);
                    if (item != null && (int)Json.Num(item, "tag") == m_ElementTag) hits.Add(item);
                }
            }

            if (hits.Count == 0)
            {
                Debug.LogError("[AR489] No se encontro ningun elemento con tag " + m_ElementTag + " en " + ResultadosAgo);
                TerminarFallo("sin elemento con tag " + m_ElementTag);
                return;
            }

            if (hits.Count > 1)
            {
                Debug.LogError("[AR489] Se encontraron " + hits.Count + " elementos con tag " + m_ElementTag + "; se esperaba exactamente 1");
                TerminarFallo("tag " + m_ElementTag + " duplicado (" + hits.Count + ")");
                return;
            }

            var d = hits[0];
            string tipo = Json.Str(d, "tipo");
            if (!EsTxt(tipo, "viga"))
            {
                Debug.LogError("[AR489] Elemento tag " + m_ElementTag + " no es viga (tipo='" + (tipo ?? "null") + "')");
                TerminarFallo("elemento tag " + m_ElementTag + " no es viga");
                return;
            }

            var corr = d.TryGetValue("correspondencia", out var co) ? Json.AsObj(co) : null;
            string viewerId = corr != null ? Json.Str(corr, "viewer_id") : null;
            if (!EsTxt(viewerId, m_ExpectedViewerId))
            {
                Debug.LogError("[AR489] correspondencia.viewer_id '" + (viewerId ?? "null") + "' != esperado '" + m_ExpectedViewerId + "'");
                TerminarFallo("viewer_id '" + (viewerId ?? "null") + "' != esperado '" + m_ExpectedViewerId + "'");
                return;
            }

            Vector3? pi = Json.V3(d, "p_i_unity");
            Vector3? pj = Json.V3(d, "p_j_unity");
            if (!pi.HasValue || !pj.HasValue)
            {
                Debug.LogError("[AR489] Elemento tag " + m_ElementTag + " sin p_i_unity/p_j_unity validos");
                TerminarFallo("elemento tag " + m_ElementTag + " sin p_i_unity/p_j_unity validos");
                return;
            }

            string seccion = Json.Str(d, "seccion") ?? "";
            float wM, hM;
            if (!TryParseSeccion(seccion, out wM, out hM)) { wM = m_SectionM.x; hM = m_SectionM.y; }

            Debug.Log("[AR489] Elemento tag " + m_ElementTag + " encontrado");

            Vector3 a = pi.Value * m_ARScale;
            Vector3 b = pj.Value * m_ARScale;
            float lenReal = Vector3.Distance(pi.Value, pj.Value);
            float lenAR = lenReal * m_ARScale;
            Vector3 dir = pj.Value - pi.Value;
            m_VigaLongitudM = lenReal;
            m_VigaLongitudAR = lenAR;
            m_VigaCentroLocal = 0.5f * (a + b);
            m_VigaPILocal = a;
            m_VigaPJLocal = b;

            GameObject beam = GameObject.CreatePrimitive(PrimitiveType.Cube);
            beam.name = string.Format(BeamName, m_ElementTag, viewerId);
            var col = beam.GetComponent<Collider>();
            if (col != null) Destroy(col);

            var renderer = beam.GetComponent<Renderer>();
            Material mat = m_BeamMaterial != null ? m_BeamMaterial : CrearMaterial();
            if (renderer != null && mat != null) renderer.sharedMaterial = mat;

            beam.transform.SetParent(m_ContentRoot != null ? m_ContentRoot : transform, false);
            beam.transform.localPosition = 0.5f * (a + b);
            beam.transform.localRotation = dir.sqrMagnitude > 0.0001f
                ? Quaternion.FromToRotation(Vector3.right, dir.normalized)
                : Quaternion.identity;
            beam.transform.localScale = new Vector3(lenAR, hM * m_ARScale, wM * m_ARScale);

            var identity = beam.GetComponent<ARElementIdentity>();
            if (identity == null) identity = beam.AddComponent<ARElementIdentity>();
            identity.Init(m_ElementTag, viewerId, edificio ?? m_Building, tipo, seccion);

            // El resultado se lee del mismo elemento FE (tag 489) del mismo JSON.
            m_Identity = identity;
            m_DataLoaded = LeerVzCasoG(d);

            beam.SetActive(false);
            m_Beam = beam;
            m_BeamVisible = false;

            Debug.Log("[AR489] Viga creada, longitud AR=" + lenAR.ToString("0.000", CultureInfo.InvariantCulture) + " m");

            if (m_DataLoaded) TerminarExito();
            else TerminarFallo("no se pudo leer el vector de esfuerzos del caso G");

            StartCoroutine(EsperarAnchor());
        }

        // Vector de 12 componentes del caso G (convencion de la fuente):
        // [2] = Vz_i, [8] = Vz_j (cortante local, kN). No se hardcodea ningun valor.
        bool LeerVzCasoG(Dictionary<string, object> d)
        {
            var fuerzas = d.TryGetValue("fuerzas", out var f) ? Json.AsObj(f) : null;
            if (fuerzas == null)
            {
                Debug.LogError("[AR489] Elemento tag " + m_ElementTag + " sin objeto 'fuerzas'");
                return false;
            }

            var coincidencias = new List<List<object>>();
            foreach (var kv in fuerzas)
            {
                if (string.Equals(kv.Key, CasoG, StringComparison.Ordinal)) coincidencias.Add(Json.AsArr(kv.Value));
            }

            if (coincidencias.Count == 0)
            {
                Debug.LogError("[AR489] Elemento tag " + m_ElementTag + " sin caso '" + CasoG + "' en fuerzas");
                return false;
            }

            if (coincidencias.Count > 1)
            {
                Debug.LogError("[AR489] Caso '" + CasoG + "' duplicado para el tag " + m_ElementTag);
                return false;
            }

            var vec = coincidencias[0];
            if (vec == null || vec.Count < 12)
            {
                Debug.LogError("[AR489] Caso '" + CasoG + "' incompleto para tag " + m_ElementTag
                    + " (" + (vec != null ? vec.Count : 0) + " componentes, se esperan 12)");
                return false;
            }

            m_VzI = (float)Json.ToNum(vec[2]);
            m_VzJ = (float)Json.ToNum(vec[8]);
            return true;
        }

        IEnumerator EsperarAnchor()
        {
            if (m_Controller == null)
            {
                Debug.LogError("[AR489] Sin referencia a ARImageAnchorController; la viga queda oculta");
                yield break;
            }

            while (m_Controller.Anchor == null) yield return null;

            if (m_Beam == null || m_BeamVisible) yield break;
            m_Beam.SetActive(true);
            m_BeamVisible = true;
            Debug.Log("[AR489] Viga visible bajo anchor");
        }

        static string UrlStreamingAssets(string rel)
        {
            string path = Path.Combine(Application.streamingAssetsPath, rel).Replace("\\", "/");
            if (Application.platform == RuntimePlatform.Android)
                return path;
            return "file://" + path;
        }

        // Estado final: LoadCompleted siempre se activa con exito o con error.
        // Los detalles del error ya se registran en el punto exacto que lo
        // detecta; aqui solo se propaga la condicion para el diagrama.
        void TerminarExito()
        {
            m_LoadCompleted = true;
            m_LoadSucceeded = true;
            m_LoadError = null;
        }

        void TerminarFallo(string detalle)
        {
            m_LoadCompleted = true;
            m_LoadSucceeded = false;
            m_LoadError = detalle;
        }

        static bool EsTxt(string a, string b)
        {
            return !string.IsNullOrEmpty(a) && string.Equals(a, b, StringComparison.Ordinal);
        }

        static bool TryParseSeccion(string seccion, out float w, out float h)
        {
            w = 0f;
            h = 0f;
            if (string.IsNullOrEmpty(seccion)) return false;
            string[] parts = seccion.Split(new[] { '/' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length != 2) return false;
            string first = parts[0];
            int cut = first.LastIndexOf('.');
            if (cut < 0 || !float.TryParse(first.Substring(cut + 1), NumberStyles.Float, CultureInfo.InvariantCulture, out float baseCm)) return false;
            if (!float.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out float depthCm)) return false;
            w = baseCm * 0.01f;
            h = depthCm * 0.01f;
            return w > 0f && h > 0f;
        }

        static Material CrearMaterial()
        {
            Shader sh = Shader.Find("Standard");
            if (sh == null) sh = Shader.Find("Legacy Shaders/Diffuse");
            if (sh == null) sh = Shader.Find("Unlit/Color");
            if (sh == null) return null;
            Material m = new Material(sh);
            m.color = new Color(1f, 0.55f, 0.05f, 1f);
            return m;
        }
    }
}