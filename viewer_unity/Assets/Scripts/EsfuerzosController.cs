using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace LabViewer
{
    /// <summary>Dato de un elemento FE con sus esfuerzos por caso (puente a los JSON
    /// esfuerzos_FE_EDIFICIO_{I,II}.json generados por el exportador Python).</summary>
    public class EFElemento
    {
        public int Tag;
        public string Building;   // "I" | "II"
        public string Tipo;       // columna | viga | muro | stub_...
        public string Nivel;
        public string Seccion;
        public string NodoI, NodoJ;
        public Vector3 Pi, Pj;    // locales (u, cota, v)
        public string EstadoCorr; // 1A1 | CONTENIDO | SIN_CORRESPONDENCIA_VIEWER | SIN_GEOMETRIA_FISICA_3D
        public string ViewerId;
        public string ViewerNivel;
        public Dictionary<string, float[]> Fuerzas = new Dictionary<string, float[]>(); // caso -> 12
        public HashSet<string> Disponible = new HashSet<string>();

        // Envolvente NCh3171: 12 componentes (i:0..5, j:6..11) con su caso gobernante
        // y valor (signo conservado). EnvValores[x] == NaN ⇒ SIN_RESULTADO para ese
        // componente (ninguna de las 9 combinaciones tiene valor).
        public float[] EnvValores = new float[12];
        public string[] EnvCasos = new string[12];
        public bool EnvOk;

        // material (Hito B), desde el bloque `material` del elemento
        public bool TieneMaterial;
        public float HcFcMpa;
        public string MatRef;
        public string MatNota;

        // ejes locales (bloque `ejes_locales` del elemento): Z_barra en frame Unity
        // y vector de referencia del geomTransf del FE (verificacion de la convencion
        // viewer<->FE de la ficha).
        public bool TieneEjes;
        public float[] EjeZBarra = new float[3];
        public float[] EjeRefGeomTransf = new float[3];

        // restricciones (bloque `restricciones` del elemento): estado por nodo
        // (BASE_FIJA_6DOF | LIBRE) + nota de la convencion de apoyo FE.
        public bool TieneRestricciones;
        public bool RestriccionesFlag;
        public string RestrNodoI, RestrNodoJ;
        public string RestrNota;

        public float[] De(string caso) => Fuerzas.TryGetValue(caso, out var v) ? v : null;
        public bool Tiene(string caso)
        {
            if (caso == EsfuerzosController.ENVOLVENTE) return EnvOk;
            return Disponible.Contains(caso);
        }

        /// <summary>Caso gobernante de la envolvente para una magnitud/representación
        /// (null si SIN_RESULTADO).</summary>
        public string CasoGobernante(int magnitud, int repre)
        {
            if (!EnvOk) return null;
            if (repre == 0) return EnvCasos[magnitud];
            if (repre == 1) return EnvCasos[magnitud + 6];
            float ai = float.IsNaN(EnvValores[magnitud]) ? 0f : Mathf.Abs(EnvValores[magnitud]);
            float aj = float.IsNaN(EnvValores[magnitud + 6]) ? 0f : Mathf.Abs(EnvValores[magnitud + 6]);
            return aj > ai ? EnvCasos[magnitud + 6] : EnvCasos[magnitud];
        }

        /// <summary>Valor escalar a color según magnitud/representación (NaN si no hay
        /// resultado para esa componente, o el caso no está disponible).</summary>
        public float Valor(string caso, int magnitud, int repre)
        {
            int iIdx = magnitud;         // N_i,Vy_i,Vz_i,T_i,My_i,Mz_i
            int jIdx = magnitud + 6;     // N_j,Vy_j,Vz_j,T_j,My_j,Mz_j
            if (caso == EsfuerzosController.ENVOLVENTE)
            {
                if (!EnvOk) return float.NaN;
                if (repre == 0) return float.IsNaN(EnvValores[iIdx]) ? float.NaN : EnvValores[iIdx];
                if (repre == 1) return float.IsNaN(EnvValores[jIdx]) ? float.NaN : EnvValores[jIdx];
                float ai = float.IsNaN(EnvValores[iIdx]) ? 0f : Mathf.Abs(EnvValores[iIdx]);
                float aj = float.IsNaN(EnvValores[jIdx]) ? 0f : Mathf.Abs(EnvValores[jIdx]);
                return Mathf.Max(ai, aj);
            }
            var f = De(caso);
            if (f == null) return float.NaN;
            if (repre == 0) return f[iIdx];
            if (repre == 1) return f[jIdx];
            return Mathf.Max(Mathf.Abs(f[iIdx]), Mathf.Abs(f[jIdx]));
        }

        public float Longitud => Vector3.Distance(Pi, Pj);
    }

    /// <summary>Componente plano para seleccionar un elemento FE por raycast.</summary>
    public class EFPicker : MonoBehaviour
    {
        public EFElemento Elem;
        /// <summary>Extremos de la malla en coordenadas LOCALES del objeto (para poder
        /// auditar los extremos REALES renderizados via TransformPoint).</summary>
        public Vector3 LocalA, LocalB;
        /// <summary>Material original del tubo (para restaurar al quitar el resaltado).</summary>
        public Material OriginalMaterial;
    }

    /// <summary>Curva P-M cargada desde pm_capacidad_demanda_{I,II}.json (Hito B):
    /// M_u(N) con N compresion positiva (kN) y M en kN*m.</summary>
    public class PMCurva
    {
        public readonly List<float> N = new List<float>();
        public readonly List<float> M = new List<float>();
        public string Seccion;
        public float FcMpa;
        public float MuN0;
        public string Clasif;
        public string EstadoArmadura;
        public string Nota;
        public bool MaxMQueda;
        public float PlotScaleM = 1f;
        public float PlotScaleN = 1f;
        public Texture2D PlotTex;
    }

    /// <summary>Fila de demanda concurrente (P, M del MISMO caso) de un elemento FE.</summary>
    public class PMFila
    {
        public int Tag;
        public string ViewerId;
        public string Nivel;
        public string Caso;
        public string Expresion;
        public float P;
        public float M;
        public float Mu;
        public float DC;
        public bool EsMuro;
        public string Nota;
    }

    /// <summary>Paquete P-M de un edificio: curva de capacidad + demanda por elemento.</summary>
    public class PMCapacidad
    {
        public PMCurva Columna;
        public readonly Dictionary<int, PMFila> PorElemento = new Dictionary<int, PMFila>();
        public PMFila Muro;
        public PMCurva MuroCurva;
    }

    /// <summary>
    /// Overlay de ESFUERZOS INTERNOS FE, independiente de la geometria del viewer:
    /// dibuja un elemento coloreado en las coordenadas EXACTAS del modelo FE (tuberia
    /// fina a lo largo del elemento), conservando la correspondencia 1:1 con su tag.
    /// NO recolorea la geometria original (solo la atenua opcionalmente); NO inventa
    /// resultados (si falta un caso o componente muestra SIN_RESULTADO y nunca
    /// reutiliza el valor anterior). Los valores provienen de
    /// esfuerzos_FE_EDIFICIO_{I,II}.json (V1: 4 casos base + 9 combinaciones
    /// NCh3171 EXPLICITAS + envolvente_NCh3171 independiente por componente).
    ///
    /// Se auto-inyecta en la escena en runtime (AfterSceneLoad) sobre el objeto que ya
    /// tiene LabLoader/ViewerController, sin modificar Main.unity.
    /// </summary>
    public class EsfuerzosController : MonoBehaviour
    {
        public enum Representacion { ExtremoI = 0, ExtremoJ = 1, MaxAbs = 2 }
        public enum EscalaModo { Percentil95 = 0, Maximo = 1 }

        private const string NOMBRE_RAIZ = "ESFUERZOS_FE";

        /// <summary>Las 13 cargas que viajan en el paquete (formato V1): 4 casos base
        /// + 9 combinaciones normativas NCh3171. El paquete contiene EXACTAMENTE estas
        /// 13 cargas (sin casos heredados).</summary>
        private static readonly string[] CASOS = {
            "G", "Q", "EX", "EY",
            "U1_GQ", "U2_EX_POS", "U2_EX_NEG", "U3_EY_POS", "U3_EY_NEG",
            "U4_EX_POS", "U4_EX_NEG", "U4_EY_POS", "U4_EY_NEG",
        };
        private static readonly string[] CASOS_BASE = { "G", "Q", "EX", "EY" };
        /// <summary>Combinaciones NCh3171 seleccionables (== IDS_COMBINACIONES del
        /// exportador). En las sísmicas Q=1.0 es la combinación básica adoptada del
        /// perfil MODELO_FE_COMPLETO_FUNCIONAL (sin la reducción opcional a 0.5).</summary>
        private static readonly string[] COMBINACIONES = {
            "U1_GQ", "U2_EX_POS", "U2_EX_NEG", "U3_EY_POS", "U3_EY_NEG",
            "U4_EX_POS", "U4_EX_NEG", "U4_EY_POS", "U4_EY_NEG",
        };
        /// <summary>Envolvente NCh3171: visualización INDEPENDIENTE (no es una corrida
        /// de análisis). Por elemento y componente guarda el caso con mayor |valor|
        /// entre las 9 combinaciones, conservando el caso y el signo gobernante.</summary>
        public const string ENVOLVENTE = "ENVOLVENTE_NCh3171";
        private static readonly Dictionary<string, string> FORMULAS = new Dictionary<string, string>
        {
            { "U1_GQ",     "1.2·G + 1.6·Q" },
            { "U2_EX_POS", "1.2·G + Q + 1.4·EX" },
            { "U2_EX_NEG", "1.2·G + Q − 1.4·EX" },
            { "U3_EY_POS", "1.2·G + Q + 1.4·EY" },
            { "U3_EY_NEG", "1.2·G + Q − 1.4·EY" },
            { "U4_EX_POS", "0.9·G + 1.4·EX" },
            { "U4_EX_NEG", "0.9·G − 1.4·EX" },
            { "U4_EY_POS", "0.9·G + 1.4·EY" },
            { "U4_EY_NEG", "0.9·G − 1.4·EY" },
        };
        private static readonly string[] MAGNITUDES = { "N", "Vy", "Vz", "T", "My", "Mz" };

        // Capa exclusiva para los tubos FE: si "EsfuerzosFE" existe en
        // ProjectSettings/TagManager.asset (NameToLayer >= 0) se asigna a cada tubo.
        // El raycast NO usa la mascara de capa (colider estrecho de 0.35 m); filtra
        // por componente EFPicker en su lugar.
        private static int _layerFE = -1;

        private LabLoader _loader;
        private ViewerController _viewer;
        private readonly List<EFElemento> _elementos = new List<EFElemento>();
        private readonly Dictionary<string, bool> _cargadoPorEdificio = new Dictionary<string, bool>();

        // --- estado de la visualizacion ---
        public string Edificio = "I";
        public string Caso = "G";
        /// <summary>Combinación NCh3171 actualmente elegida en el selector (-1 si el
        /// caso activo no es una combinación: base o envolvente).</summary>
        public int CombinacionIdx = -1;
        public int MagnitudIdx;                    // 0..5 (N,Vy,Vz,T,My,Mz)
        public Representacion Repre = Representacion.ExtremoI;
        public EscalaModo Escala = EscalaModo.Percentil95;
        public bool OverlayOn;
        public bool MostrarDiagrama;

        public EFElemento SelectedFE;
        private GameObject _raiz;
        private readonly List<GameObject> _overlay = new List<GameObject>();
        private readonly Dictionary<Renderer, Color> _atenuados = new Dictionary<Renderer, Color>();
        private GameObject _resaltado; // tubo FE resaltado actual (si hay seleccion)
        private Material _materialResaltado;

        // --- seleccion por correspondencia viewer <-> FE ---
        // ViewerSel = ElementRef (geometria original) que origino la seleccion. Es la
        // fuente PRIMARIA: el FE elegido debe cumplir correspondencia.viewer_id ==
        // ViewerSel.Id (1A1 directo, o CONTENIDO con segmentos del mismo viewer_id).
        public ElementRef ViewerSel;
        // Segmentos del viewer_id CONTENIDO (si >1 son los sub-elementos FE de la misma
        // barra viewer). SegmentoIdx = seleccion actual dentro del grupo ("segmento n/N").
        public readonly List<EFElemento> Segmentos = new List<EFElemento>();
        public int SegmentoIdx = -1;

        // --- filtros de overlay (tipo + correspondencia) ---
        public bool FiltroVigas = true;
        public bool FiltroColumnas = true;
        public bool FiltroMuros = true;
        public string FiltroCorr = "Mapeados"; // "Mapeados" (modo normal) | "Todos los FE" (modo diagnostico)

        // --- estadisticas de la configuracion actual ---
        private float _maxReal;
        private float _escala;

        private Vector2 _scrollUI;

        /// <summary>Panel fijo compacto para la presentacion: oculta el bloque de
        /// diagnostico (filtros, envolvente, colorbar, contadores y ficha) y solo
        /// deja edificio, caso/combinacion, magnitud, representacion, escala y los
        /// toggles de overlay/diagrama/deformada.</summary>
        public bool ModoPresentacion;
        /// <summary>Bloque de diagnostico plegable del panel normal (filtros,
        /// envolvente, colorbar, contadores y ficha detallada).</summary>
        public bool DiagnosticoVisible = true;

        // --- Hito B: deformada amplificada + ficha material/reactivos + panel P-M ---
        public bool MostrarDeformada;
        public float Amplificacion = 60f;
        private readonly Dictionary<string, Dictionary<string, Vector3>> _defNodos =
            new Dictionary<string, Dictionary<string, Vector3>>();
        // _despCaso[b][caso][tagNodo] = [du, dcota, dv, rx, ry, rz]
        private readonly Dictionary<string, Dictionary<string, Dictionary<string, float[]>>>
            _despCaso = new Dictionary<string, Dictionary<string, Dictionary<string, float[]>>>();
        // reacciones_G[b][tagNodo] = [Rx, Ry, Rz, Mx, My, Mz]
        private readonly Dictionary<string, Dictionary<string, float[]>> _reaccionesG =
            new Dictionary<string, Dictionary<string, float[]>>();
        private readonly Dictionary<string, object> _materialesTop = new Dictionary<string, object>();
        private readonly Dictionary<string, PMCapacidad> _pm = new Dictionary<string, PMCapacidad>();
        private readonly List<GameObject> _deformadaGo = new List<GameObject>();
        private string _defUltimoCaso = "";
        private string _defUltimaB = "";

        public int TotalElementos(string b)
        {
            int n = 0;
            foreach (var e in _elementos) if (e.Building == b) n++;
            return n;
        }

        public bool EstaCargado(string b) => _cargadoPorEdificio.TryGetValue(b, out var v) && v;

        /// <summary>Conteos por correspondencia del viewer de un edificio: total de FE
        /// del paquete (FE_TOTAL), visibles en modo normal (1A1+CONTENIDO) y sin
        /// correspondencia (SIN_CORRESPONDENCIA_VIEWER). Devuelve también cuántos de los
        /// sin correspondencia son stubs analíticos (auxiliares, excluidos de la cobertura).</summary>
        public void ConteosCorrespondencia(string b, out int total, out int mapeados, out int sinCorr, out int stubs)
        {
            total = 0; mapeados = 0; sinCorr = 0; stubs = 0;
            foreach (var e in _elementos)
            {
                if (e.Building != b) continue;
                total++;
                if (e.EstadoCorr == "1A1" || e.EstadoCorr == "CONTENIDO") mapeados++;
                else
                {
                    sinCorr++;
                    if (e.Tipo != null && e.Tipo.StartsWith("stub")) stubs++;
                }
            }
        }

        public double Valor(string b, int tag, string caso, int comp)
        {
            var e = Buscar(b, tag);
            if (e == null) return double.NaN;
            if (caso == ENVOLVENTE)
            {
                if (!e.EnvOk || comp < 0 || comp >= 12 || float.IsNaN(e.EnvValores[comp])) return double.NaN;
                return e.EnvValores[comp];
            }
            var f = e.De(caso);
            if (f == null || comp < 0 || comp >= f.Length) return double.NaN;
            return f[comp];
        }

        public EFElemento Buscar(string b, int tag)
        {
            foreach (var e in _elementos) if (e.Building == b && e.Tag == tag) return e;
            return null;
        }

        /// <summary>Selecciona el FE indicado (por tag) y enlaza su viewer vinculado. En el
        /// modo normal solo permite seleccionar 1A1 / CONTENIDO; en modo de diagnostico
        /// ("Todos los FE") también acepta SIN_CORRESPONDENCIA_VIEWER.</summary>
        public bool SelectFE(string b, int tag)
        {
            var e = Buscar(b, tag);
            if (e == null) return false;
            if (EsSinCorrespondencia(e) && FiltroCorr != "Todos los FE") return false;
            SetSeleccion(e, BuscarViewerElement(e.ViewerId));
            Edificio = b;
            ReaplicarResaltado();
            return true;
        }

        /// <summary>Lista blanca de correspondencia para el modo normal: solo
        /// 1A1/CONTENIDO. Todo lo demas (SIN_CORRESPONDENCIA_VIEWER,
        /// SIN_GEOMETRIA_FISICA_3D para barras analiticas sin tramo fisico en el
        /// viewer, stubs...) queda SOLO en el modo de diagnostico "Todos los FE".</summary>
        private static bool EsCorrespondenciaNormal(EFElemento e)
        {
            return e != null && (e.EstadoCorr == "1A1" || e.EstadoCorr == "CONTENIDO");
        }

        private static bool EsSinCorrespondencia(EFElemento e)
        {
            return !EsCorrespondenciaNormal(e);
        }

        /// <summary>Fija la seleccion FE + su viewer vinculado (si existe) y re-aplica
        /// el resaltado del tubo. No toca la lista de segmentos CONTENIDO.</summary>
        /// <remarks>SINCRONIZA el edificio activo con la seleccion (EI&harr;EII): si el FE
        /// elegido pertenece a un edificio distinto del activo, cambia Edificio y
        /// reconstruye overlay+deformada ANTES de volver (la cabecera "Edificio I/II"
        /// queda coherente con la ficha sin usar el toggle manual).</remarks>
        private void SetSeleccion(EFElemento e, ElementRef viewer)
        {
            SelectedFE = e;
            ViewerSel = viewer;
            // La ficha "Inspeccion" del ViewerController se alimenta de su _selected
            // (ElementRef de la geometria original). Se sincroniza aqui para que
            // cambien JUNTOS al seleccionar FE por script/tool/panel (el clic normal
            // tambien pasa por aqui via ProcesarClic). Sin geometria (SIN_CORRESPONDENCIA)
            // se limpia: el panel no debe quedarse con un elemento anterior.
            if (_viewer != null) _viewer.SincronizarSeleccion(viewer);
            // Si el elemento elegido tiene bloque P-M (muro demo o columna por tag), el
            // bloque es el ULTIMO del scroll de diagnostico: auto-scroll ahi para que la
            // curva, el punto de demanda, D/C y el caso quedan visibles al seleccionar.
            _scrollUI.y = TienePmVisible(e) ? float.MaxValue : 0f;
            if (e != null && !string.IsNullOrEmpty(e.Building) && e.Building != Edificio)
            {
                Edificio = e.Building;
                if (OverlayOn) RebuildOverlay();      // recrea tuberias/escala/resaltado/diagrama
                else ReaplicarResaltado();
                MarcarDiagramaSucio();
                return;
            }
            ReaplicarResaltado();
            MarcarDiagramaSucio();   // seleccion: el diagrama local pertenece a este FE
        }

        /// <summary>Sincroniza el panel "Inspeccion" del ViewerController con el
        /// ElementRef de geometria original (null limpia). Sin geometria (null)
        /// la Inspeccion no debe quedarse con un elemento anterior.</summary>
        private void SincronizarInspeccion(ElementRef r)
        {
            if (_viewer != null) _viewer.SincronizarSeleccion(r);
        }

        /// <summary>Fija _diagramaSucia para que DrawFicha redibuje el diagrama
        /// local SOLO cuando cambio algo relevante (nunca por frame). Todo trigger
        /// (seleccion/segmento/edificio/caso/comb/envolvente/magnitud/repre/escala/
        /// toggle) debe llamar esta.</summary>
        private void MarcarDiagramaSucio()
        {
            _diagramaSucia = true;
            if (SelectedFE == null) return;
            DrawDiagrams(SelectedFE);   // valores ya disponibles: dibujo INMEDIATO
        }

        /// <summary>Todos los elementos FE de un edificio (para pruebas y paneles).</summary>
        public List<EFElemento> ElementosDe(string b)
        {
            var l = new List<EFElemento>();
            foreach (var e in _elementos) if (e.Building == b) l.Add(e);
            return l;
        }

        /// <summary>Info resumida del muro P-M demostrado (viewer_id/tag/D/C), para
        /// diagnostico y pruebas de aceptacion. Vacio si no hay muro demo.</summary>
        public string PmMuroInfo(string b)
        {
            if (!_pm.TryGetValue(b, out var cap) || cap.Muro == null) return "";
            return b + ":" + cap.Muro.ViewerId + ":tag" + cap.Muro.Tag
                   + ":D_C=" + cap.Muro.DC.ToString("0.00")
                   + ":P=" + cap.Muro.P.ToString("0.0")
                   + ":M=" + cap.Muro.M.ToString("0.0");
        }

        /// <summary>Convierte una posicion en el frame local (u, cota, v) al mundo.</summary>
        public Vector3 PuntoMundo(string b, Vector3 local)
        {
            if (_loader == null) return local;
            return _loader.ToWorldModel(b, local.x, local.y, local.z);
        }

        /// <summary>
        /// Seleccion por CLAVENIE: primero identifica el ElementRef de la geometria
        /// ORIGINAL bajo el clic EXACTAMENTE igual que ViewerController.RaycastPick
        /// (Physics.Raycast al primer hit). Ese ElementRef.Ia es la fuente del
        /// correspondencia: los FE elegidos son los que cumplen
        /// correspondencia.viewer_id == ElementRef.Id. Sin esa correspondencia se muestra
        /// SIN_CORRESPONDENCIA_VIEWER y NO se selecciona otra barra (delante/detras).
        /// Solo si el clic cae directamente en una tuberia SIN correspondencia viewer se
        /// usa el raycast directo sobre EFPicker.
        /// </summary>
        public ElementRef ProcesarClic(Vector2 pantalla)
        {
            if (Camera.main == null) return null;
            return ProcesarClic(Camera.main.ScreenPointToRay(pantalla));
        }

        public ElementRef ProcesarClic(Ray ray)
        {
            RaycastHit hit;
            if (!Physics.Raycast(ray, out hit, 3000f))
            {
                SelectedFE = null; ViewerSel = null; Segmentos.Clear(); SegmentoIdx = -1;
                SincronizarInspeccion(null);
                SetResaltado(null);
                return null;
            }
            var refEl = hit.collider != null ? hit.collider.GetComponent<ElementRef>() : null;
            if (refEl != null)
            {
                // (1) geometria original: seleccion por correspondencia viewer <-> FE.
                SeleccionarPorViewer(refEl, hit.point);
                return refEl;
            }
            // (2) clic directo sobre un tubo FE (sin ElementRef en el primer hit):
            var tube = hit.collider != null ? hit.collider.GetComponent<EFPicker>() : null;
            if (tube != null && tube.Elem != null)
            {
                if (!string.IsNullOrEmpty(tube.Elem.ViewerId))
                {
                    // La tuberia tiene correspondencia viewer: re-enrutar por su viewer_id.
                    var byId = BuscarViewerElement(tube.Elem.ViewerId);
                    if (byId != null) { SeleccionarPorViewer(byId, hit.point); return byId; }
                }
                // Sin correspondencia viewer: seleccion directa solo en modo diagnostico.
                if (FiltroCorr != "Todos los FE")
                {
                    SelectedFE = null; ViewerSel = null; Segmentos.Clear(); SegmentoIdx = -1;
                    SincronizarInspeccion(null);
                    SetResaltado(null);
                    return null;
                }
                SetSeleccion(tube.Elem, null);
                SetResaltado(tube.gameObject);
                return null;
            }
            SelectedFE = null; ViewerSel = null; Segmentos.Clear(); SegmentoIdx = -1;
            SincronizarInspeccion(null);
            SetResaltado(null);
            return null;
        }

        /// <summary>Selecciona los FE cuyo correspondencia.viewer_id coincide con el
        /// ElementRef de la geometria original pinchada. 1A1 -> tag directo; CONTENIDO
        /// (varias segmentos) -> se filtra al grupo y se elige el segmento mas cercano al
        /// punto REAL del clic; sin coincidencia -> SIN_CORRESPONDENCIA_VIEWER.</summary>
        public EFElemento SeleccionarPorViewer(ElementRef refEl, Vector3 clickPoint)
        {
            if (refEl == null) return null;
            ViewerSel = refEl;
            var grupo = new List<EFElemento>();
            foreach (var e in _elementos)
            {
                if (e.Building != refEl.Building) continue;
                if (string.IsNullOrEmpty(e.ViewerId)) continue;
                if (e.ViewerId != refEl.Id) continue;
                grupo.Add(e);
            }
            if (grupo.Count == 0)
            {
                // Sin correspondencia en este edificio: NO seleccionar ninguna otra barra.
                SelectedFE = null; Segmentos.Clear(); SegmentoIdx = -1;
                SincronizarInspeccion(null);
                SetResaltado(null);
                return null;
            }
            if (grupo.Count == 1)
            {
                Segmentos.Clear(); SegmentoIdx = -1;
                SetSeleccion(grupo[0], refEl);
                return grupo[0];
            }
            // CONTENIDO: el segmento mas cercano al punto del clic.
            int idx = SegmentoMasCercano(grupo, clickPoint);
            Segmentos.Clear();
            Segmentos.AddRange(grupo);
            SegmentoIdx = idx;
            SetSeleccion(grupo[idx], refEl);
            return grupo[idx];
        }

        private int SegmentoMasCercano(List<EFElemento> grupo, Vector3 clickPoint)
        {
            int best = 0; float bestD = float.MaxValue;
            for (int i = 0; i < grupo.Count; i++)
            {
                Vector3 w0 = PuntoMundo(grupo[i].Building, grupo[i].Pi);
                Vector3 w1 = PuntoMundo(grupo[i].Building, grupo[i].Pj);
                float d = DistanciaPuntoSegmento(clickPoint, w0, w1);
                if (d < bestD) { bestD = d; best = i; }
            }
            return best;
        }

        private static float DistanciaPuntoSegmento(Vector3 p, Vector3 a, Vector3 b)
        {
            Vector3 ab = b - a;
            float len2 = ab.sqrMagnitude;
            if (len2 < 1e-9f) return Vector3.Distance(p, a);
            float t = Mathf.Clamp01(Vector3.Dot(p - a, ab) / len2);
            return Vector3.Distance(p, a + ab * t);
        }

        /// <summary>ElementRef de la geometria original por su Id (fuente única: el modelo
        /// del LabLoader, el mismo que usa ViewerController para seleccionar).</summary>
        private ElementRef BuscarViewerElement(string id)
        {
            if (string.IsNullOrEmpty(id) || _loader == null || _loader.Model == null) return null;
            foreach (var e in _loader.Model.Elements)
                if (e.Id == id) return e;
            return null;
        }

        /// <summary>Cambia la seleccion dentro del grupo CONTENIDO ("segmento n/N").</summary>
        public void CiclarSegmento(int delta)
        {
            if (Segmentos.Count <= 1) return;
            int n = Segmentos.Count;
            SegmentoIdx = ((SegmentoIdx + delta) % n + n) % n;
            SetSeleccion(Segmentos[SegmentoIdx], ViewerSel);
        }

        /// <summary>Tag del tubo FE resaltado actualmente (-1 si no hay seleccion).</summary>
        public int ResaltadoTag()
        {
            if (_resaltado == null) return -1;
            var p = _resaltado.GetComponent<EFPicker>();
            return p != null && p.Elem != null ? p.Elem.Tag : -1;
        }

        private void SetResaltado(GameObject go)
        {
            if (_resaltado == go) return;
            if (_resaltado != null)
            {
                var mr = _resaltado.GetComponent<MeshRenderer>();
                var prev = _resaltado.GetComponent<EFPicker>();
                if (mr != null && prev != null && prev.OriginalMaterial != null)
                    mr.sharedMaterial = prev.OriginalMaterial;
            }
            _resaltado = go;
            if (go == null) return;
            var pr = go.GetComponent<EFPicker>();
            var nm = go.GetComponent<MeshRenderer>();
            if (pr == null || nm == null) return;
            if (_materialResaltado == null)
            {
                _materialResaltado = new Material(Shader.Find("Standard"));
                _materialResaltado.color = new Color(1f, 0.92f, 0.2f);
                _materialResaltado.EnableKeyword("_EMISSION");
                _materialResaltado.SetColor("_EmissionColor", new Color(0.6f, 0.5f, 0f));
            }
            if (pr.OriginalMaterial == null) pr.OriginalMaterial = nm.sharedMaterial;
            nm.sharedMaterial = _materialResaltado;
        }

        /// <summary>Re-aplica el resaltado despues de un RebuildOverlay (el tubo del
        /// elemento seleccionado se recrea).</summary>
        private void ReaplicarResaltado()
        {
            if (SelectedFE == null) { SetResaltado(null); return; }
            foreach (var go in _overlay)
            {
                if (go == null) continue;
                var p = go.GetComponent<EFPicker>();
                if (p != null && p.Elem == SelectedFE) { SetResaltado(go); return; }
            }
            SetResaltado(null);
        }

        public void SetOverlay(bool on)
        {
            if (OverlayOn == on) { _overlayOnChanged = true; RebuildOverlay(); return; }
            OverlayOn = on;
            RebuildOverlay();
        }
        private bool _overlayOnChanged;

        public void SetUI(string b, string caso, int magnitud, int repre, int escala, bool on)
        {
            Edificio = b;
            if (System.Array.IndexOf(CASOS, caso) >= 0 || caso == ENVOLVENTE) Caso = caso;
            CombinacionIdx = System.Array.IndexOf(COMBINACIONES, Caso);
            MagnitudIdx = Mathf.Clamp(magnitud, 0, 5);
            Repre = (Representacion)Mathf.Clamp(repre, 0, 2);
            Escala = (EscalaModo)Mathf.Clamp(escala, 0, 1);
            SetOverlay(on);
        }

        /// <summary>Selecciona la combinación NCh3171 i-ésima (index en COMBINACIONES)
        /// y reconstruye el overlay conservando la selección de elemento.</summary>
        public void SeleccionarCombinacion(int index)
        {
            if (index < 0 || index >= COMBINACIONES.Length) return;
            CombinacionIdx = index;
            Caso = COMBINACIONES[index];
            RebuildOverlay();
        }

        /// <summary>Paginado ◀/▶ por las 9 combinaciones NCh3171 (desde cualquier caso
        /// activo). Recorre en círculo y conserva la selección de elemento.</summary>
        public void CiclarCombinacion(int delta)
        {
            int n = COMBINACIONES.Length;
            if (CombinacionIdx < 0) CombinacionIdx = delta > 0 ? 0 : n - 1;
            else CombinacionIdx = (CombinacionIdx + delta + n) % n;
            Caso = COMBINACIONES[CombinacionIdx];
            RebuildOverlay();
        }

        public bool SeleccionarEnvolvente()
        {
            if (Caso == ENVOLVENTE) return true;
            Caso = ENVOLVENTE;
            CombinacionIdx = -1;
            RebuildOverlay();
            return true;
        }

        public int CountOverlayRenderers(string b)
        {
            int n = 0;
            foreach (var go in _overlay)
            {
                if (go == null || !go.activeInHierarchy) continue;
                var p = go.GetComponent<EFPicker>();
                if (p == null || p.Elem == null || p.Elem.Building != b) continue;
                if (go.GetComponent<Renderer>() != null) n++;
            }
            return n;
        }

        /// <summary>Verificacion geometrica del overlay en-engine sobre TODOS los elementos:
        /// compara los extremos REALES renderizados (TransformPoint de los extremos locales
        /// de la malla) contra w0/w1 del elemento FE (orden directo o invertido), el centro
        /// de Renderer.bounds contra el punto medio, y la longitud renderizada contra
        /// |w1-w0|. Reporta error maximo, RMS, cantidad fuera de tolerancia.</summary>
        public bool VerificarGeometria(float tolExtremos,
                                       out float maxErrExtremos, out float rmsExtremos,
                                       out float maxErrCentro, out float maxErrLongitud,
                                       out int fueraTol)
        {
            maxErrExtremos = 0f;
            rmsExtremos = 0f;
            maxErrCentro = 0f;
            maxErrLongitud = 0f;
            fueraTol = 0;
            if (_loader == null || _loader.Model == null) return false;

            int revisados = 0;
            double sumaCuadrados = 0.0;
            foreach (var go in _overlay)
            {
                if (go == null || !go.activeInHierarchy) continue;
                var p = go.GetComponent<EFPicker>();
                if (p == null || p.Elem == null) continue;
                string b = p.Elem.Building;
                Vector3 w0 = _loader.ToWorldModel(b, p.Elem.Pi.x, p.Elem.Pi.y, p.Elem.Pi.z);
                Vector3 w1 = _loader.ToWorldModel(b, p.Elem.Pj.x, p.Elem.Pj.y, p.Elem.Pj.z);

                // extremos renderizados de la malla (con el transform actual de una sola vez)
                Vector3 r0 = go.transform.TransformPoint(p.LocalA);
                Vector3 r1 = go.transform.TransformPoint(p.LocalB);

                // orden directo o invertido (acepta ambas orientaciones de la malla)
                float errDirecto = Mathf.Max(Vector3.Distance(r0, w0), Vector3.Distance(r1, w1));
                float errInvertido = Mathf.Max(Vector3.Distance(r0, w1), Vector3.Distance(r1, w0));
                float err = Mathf.Min(errDirecto, errInvertido);
                maxErrExtremos = Mathf.Max(maxErrExtremos, err);
                sumaCuadrados += err * err;
                revisados++;
                if (err > tolExtremos) fueraTol++;

                // centro del Renderer.bounds vs punto medio esperado
                var mr = go.GetComponent<Renderer>();
                if (mr != null)
                {
                    Vector3 esperadoMid = (w0 + w1) * 0.5f;
                    float errC = Vector3.Distance(mr.bounds.center, esperadoMid);
                    maxErrCentro = Mathf.Max(maxErrCentro, errC);
                }

                // longitud renderizada vs longitud FE
                float rLen = Vector3.Distance(r0, r1);
                float feLen = Vector3.Distance(w0, w1);
                float errL = Mathf.Abs(rLen - feLen);
                maxErrLongitud = Mathf.Max(maxErrLongitud, errL);
            }
            if (revisados > 0) rmsExtremos = (float)Mathf.Sqrt((float)(sumaCuadrados / revisados));
            return revisados > 0 && fueraTol == 0 && maxErrExtremos <= tolExtremos;
        }

        public float EscalaActual => _escala;
        public float MaxRealActual => _maxReal;
        public string CasoActual => Caso;
        public int MagnitudIdxActual => MagnitudIdx;
        public bool IsOn => OverlayOn;

        // ------------------------------------------------------------------ //
        //  Ciclo de vida
        // ------------------------------------------------------------------ //
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void AutoAdjuntar()
        {
            var viewer = Object.FindObjectOfType<ViewerController>();
            if (viewer == null) return;
            if (viewer.GetComponent<EsfuerzosController>() != null) return;
            viewer.gameObject.AddComponent<EsfuerzosController>();
        }

        void Awake()
        {
            _loader = GetComponent<LabLoader>();
            _viewer = GetComponent<ViewerController>();
            if (_layerFE < 0) _layerFE = LayerMask.NameToLayer("EsfuerzosFE");
        }

        /// <summary>Uso en modo editor (verificaciones automatizadas sin play): ata el
        /// loader ya cargado, lee los paquetes y deja el controlador listo.</summary>
        public void Preparar(LabLoader loader)
        {
            _loader = loader;
            _viewer = loader != null ? loader.GetComponent<ViewerController>() : null;
            CargarPaquetes();
        }

        IEnumerator Start()
        {
            yield return null; // esperar a que ViewerController.Start ya haya construido el modelo
            if (_loader == null) _loader = GetComponent<LabLoader>();
            if (_loader == null) yield break;
            if (_loader.Model == null || _loader.Model.Elements.Count == 0) _loader.Load();
            CargarPaquetes();
            if (OverlayOn) RebuildOverlay(); // si el usuario ya lo encendio antes de terminar la carga
        }

        private void CargarPaquetes()
        {
            _elementos.Clear();
            foreach (var b in new[] { "I", "II" })
            {
                _cargadoPorEdificio[b] = false;
                string path = System.IO.Path.Combine(
                    Application.streamingAssetsPath, "lab_data", "edificios", b,
                    "results", "esfuerzos_FE_EDIFICIO_" + b + ".json");
                if (!System.IO.File.Exists(path))
                {
                    Debug.LogWarning("[EsfuerzosFE] No existe " + path);
                    continue;
                }
                try
                {
                    string texto = System.IO.File.ReadAllText(path);
                    CargarEdificio(b, texto);
                    var raiz = Json.AsObj(Json.Parse(texto));
                    if (raiz != null) CargarAuxiliares(b, raiz);
                    _cargadoPorEdificio[b] = true;
                }
                catch (System.Exception ex)
                {
                    Debug.LogError("[EsfuerzosFE] Error cargando " + path + ": " + ex.Message);
                }
            }
        }

        private void CargarAuxiliares(string b, Dictionary<string, object> raiz)
        {
            _reaccionesG[b] = new Dictionary<string, float[]>();
            if (raiz.TryGetValue("apoyos", out var apoRaw) && Json.AsObj(apoRaw) != null)
            {
                var apo = Json.AsObj(apoRaw);
                var rg = apo.TryGetValue("reacciones_G", out var rgRaw) ? Json.AsObj(rgRaw) : null;
                if (rg != null)
                    foreach (var kv in rg)
                        _reaccionesG[b][kv.Key] = Floats6(kv.Value);
            }

            _materialesTop[b] = raiz.TryGetValue("materiales", out var mt) ? mt : null;

            _defNodos[b] = new Dictionary<string, Vector3>();
            _despCaso[b] = new Dictionary<string, Dictionary<string, float[]>>();
            if (raiz.TryGetValue("deformada", out var defRaw) && Json.AsObj(defRaw) != null)
            {
                var def = Json.AsObj(defRaw);
                var nodos = def.TryGetValue("nodos", out var noRaw) ? Json.AsObj(noRaw) : null;
                if (nodos != null)
                    foreach (var kv in nodos)
                    {
                        var arr = Json.AsArr(kv.Value);
                        if (arr == null || arr.Count < 3) continue;
                        _defNodos[b][kv.Key] = new Vector3(
                            (float)Json.ToNum(arr[0]), (float)Json.ToNum(arr[1]),
                            (float)Json.ToNum(arr[2]));
                    }
                var desp = def.TryGetValue("desplazamientos_por_caso", out var dpRaw)
                    ? Json.AsObj(dpRaw) : null;
                if (desp != null)
                    foreach (var kv in desp)
                    {
                        var porNodo = Json.AsObj(kv.Value);
                        if (porNodo == null) continue;
                        var d = new Dictionary<string, float[]>();
                        foreach (var nd in porNodo)
                            d[nd.Key] = Floats6(nd.Value);
                        _despCaso[b][kv.Key] = d;
                    }
            }

            CargarPMCapacidad(b);
        }

        private void CargarPMCapacidad(string b)
        {
            var cap = new PMCapacidad();
            string path = System.IO.Path.Combine(
                Application.streamingAssetsPath, "lab_data", "edificios", b,
                "results", "pm_capacidad_demanda_" + b + ".json");
            if (System.IO.File.Exists(path))
            {
                try
                {
                    var raiz = Json.AsObj(Json.Parse(System.IO.File.ReadAllText(path)));
                    if (raiz != null)
                    {
                        var capRaw = raiz.TryGetValue("capacidad", out var c) ? Json.AsObj(c) : null;
                        if (capRaw != null)
                        {
                            cap.Columna = ParseCurva(capRaw, "curva_columna");
                            cap.Columna.Seccion = SeccionEtiqueta(capRaw, "seccion");
                            cap.Columna.FcMpa = (float)Json.Num(capRaw, "fc_MPa");
                            cap.Columna.MuN0 = (float)Json.Num(capRaw, "M_u_N0_kN_m");
                            cap.Columna.Clasif = Json.Str(capRaw, "clasificacion") ?? "";
                            cap.Columna.EstadoArmadura = Json.Str(capRaw, "estado_armadura") ?? "";
                        }
                        var pe = raiz.TryGetValue("por_elemento", out var peRaw)
                            ? Json.AsObj(peRaw) : null;
                        if (pe != null)
                            foreach (var kv in pe)
                            {
                                var f = ParseFila(kv.Value, false);
                                if (f != null) cap.PorElemento[f.Tag] = f;
                            }
                        if (raiz.TryGetValue("muro_demostrado", out var mRaw)
                            && Json.AsObj(mRaw) != null)
                        {
                            var m = Json.AsObj(mRaw);
                            var dem = m.TryGetValue("demanda", out var dd) ? Json.AsObj(dd) : null;
                            if (dem != null)
                            {
                                var el = dem.TryGetValue("elemento_demostrado", out var ee)
                                    ? Json.AsObj(ee) : null;
                                var conc = dem.TryGetValue("demanda_concurrente", out var cc)
                                    ? Json.AsObj(cc) : null;
                                var fila = new PMFila
                                {
                                    EsMuro = true,
                                    Tag = el != null ? (int)Json.Num(el, "tag") : -1,
                                    ViewerId = el != null ? (Json.Str(el, "viewer_id") ?? "") : "",
                                    Nivel = el != null ? (Json.Str(el, "nivel") ?? "") : "",
                                    Caso = conc != null ? (Json.Str(conc, "caso") ?? "") : "",
                                    Expresion = conc != null ? (Json.Str(conc, "expresion") ?? "") : "",
                                    P = conc != null ? (float)Json.Num(conc, "P_u_kN") : 0f,
                                    M = conc != null ? (float)Json.Num(conc, "M_demanda_kN_m") : 0f,
                                    Mu = (float)Json.Num(dem, "M_u_N_kN_m"),
                                    DC = (float)Json.Num(dem, "D_C"),
                                };
                                fila.Nota = Json.Str(m, "nota_armadura") ?? "";
                                cap.Muro = fila;
                                var capPm = m.TryGetValue("capacidad_pm", out var cp)
                                    ? Json.AsObj(cp) : null;
                                if (capPm != null)
                                {
                                    cap.MuroCurva = ParseCurva(capPm, "curva_muro");
                                    cap.MuroCurva.Clasif = Json.Str(capPm, "clasificacion") ?? "";
                                    cap.MuroCurva.FcMpa = (float)Json.Num(capPm, "fc_MPa");
                                    var sec2 = capPm.TryGetValue("seccion", out var s2)
                                        ? Json.AsObj(s2) : null;
                                    if (sec2 != null) cap.MuroCurva.Seccion = Json.Str(sec2, "etiqueta") ?? "";
                                    cap.MuroCurva.EstadoArmadura = Json.Str(capPm, "armadura_hipotesis") ?? "";
                                }
                            }
                        }
                    }
                }
                catch (System.Exception ex)
                {
                    Debug.LogWarning("[EsfuerzosFE] P-M " + path + " no cargado: " + ex.Message);
                }
            }
            _pm[b] = cap;
        }

        private PMCurva ParseCurva(Dictionary<string, object> cap, string pref)
        {
            var c = new PMCurva();
            var n = Json.Arr(cap, "N_kN");
            var m = Json.Arr(cap, "M_kN_m");
            if (n != null) foreach (var x in n) c.N.Add((float)Json.ToNum(x));
            if (m != null) foreach (var x in m) c.M.Add((float)Json.ToNum(x));
            return c;
        }

        private PMFila ParseFila(object obj, bool esMuro)
        {
            var d = Json.AsObj(obj);
            if (d == null) return null;
            var f = new PMFila
            {
                EsMuro = esMuro,
                Tag = (int)Json.Num(d, "tag"),
                ViewerId = Json.Str(d, "viewer_id") ?? "",
                Nivel = Json.Str(d, "nivel") ?? "",
                Caso = Json.Str(d, "caso") ?? "",
                Expresion = Json.Str(d, "expresion") ?? "",
                P = (float)Json.Num(d, "P_u_kN"),
                M = (float)Json.Num(d, "M_demanda_kN_m"),
                Mu = (float)Json.Num(d, "M_u_N_kN_m"),
                DC = (float)Json.Num(d, "D_C"),
            };
            return f;
        }

        private static string SeccionEtiqueta(Dictionary<string, object> cap, string key)
        {
            var s = cap.TryGetValue(key, out var sv) ? Json.AsObj(sv) : null;
            return s != null ? (Json.Str(s, "etiqueta") ?? "") : "";
        }

        private static float[] Floats6(object o)
        {
            var arr = Json.AsArr(o);
            var r = new float[6];
            if (arr == null) return r;
            for (int i = 0; i < 6 && i < arr.Count; i++) r[i] = (float)Json.ToNum(arr[i]);
            return r;
        }

        private void CargarEdificio(string b, string texto)
        {
            var raiz = Json.AsObj(Json.Parse(texto));
            if (raiz == null) return;
            var arr = Json.Arr(raiz, "elementos");
            if (arr == null) return;
            foreach (var it in arr)
            {
                var d = Json.AsObj(it);
                if (d == null) continue;
                var e = new EFElemento
                {
                    Building = b,
                    Tag = (int)Json.Num(d, "tag"),
                    Tipo = Json.Str(d, "tipo") ?? "",
                    Nivel = Json.Str(d, "nivel") ?? "",
                    Seccion = Json.Str(d, "seccion") ?? "",
                    NodoI = Json.Str(d, "nodo_i") ?? "",
                    NodoJ = Json.Str(d, "nodo_j") ?? "",
                    Pi = V3De(d, "p_i_unity"),
                    Pj = V3De(d, "p_j_unity"),
                };
                var corr = d.TryGetValue("correspondencia", out var co) ? Json.AsObj(co) : null;
                e.EstadoCorr = corr != null ? (Json.Str(corr, "estado") ?? "SIN_CORRESPONDENCIA_VIEWER")
                                             : "SIN_CORRESPONDENCIA_VIEWER";
                e.ViewerId = corr != null ? Json.Str(corr, "viewer_id") : null;
                e.ViewerNivel = corr != null ? Json.Str(corr, "viewer_nivel") : null;
                var fuerzas = d.TryGetValue("fuerzas", out var fw) ? Json.AsObj(fw) : null;
                if (fuerzas != null)
                {
                    foreach (var caso in CASOS)
                    {
                        var v = Json.Arr(fuerzas, caso);
                        if (v == null || v.Count < 12) continue;
                        var f = new float[12];
                        for (int i = 0; i < 12; i++) f[i] = (float)Json.ToNum(v[i]);
                        e.Fuerzas[caso] = f;
                        e.Disponible.Add(caso);
                    }
                }
                // Envolvente NCh3171 (independiente): 12 entradas {indice, caso, valor}.
                // Componentes sin resultado quedan NaN / caso null (SIN_RESULTADO).
                var ev = d.TryGetValue("envolvente_NCh3171", out var evRaw) ? Json.AsArr(evRaw) : null;
                if (ev != null)
                {
                    for (int i = 0; i < 12; i++) { e.EnvValores[i] = float.NaN; e.EnvCasos[i] = null; }
                    foreach (var item in ev)
                    {
                        var en = Json.AsObj(item);
                        if (en == null) continue;
                        int idx = (int)Json.Num(en, "indice");
                        if (idx < 0 || idx >= 12) continue;
                        e.EnvValores[idx] = (float)Json.Num(en, "valor");
                        e.EnvCasos[idx] = Json.Str(en, "caso");
                        e.EnvOk = true;
                    }
                }
                var matRaw = d.TryGetValue("material", out var mR) ? Json.AsObj(mR) : null;
                if (matRaw != null)
                {
                    e.TieneMaterial = true;
                    e.HcFcMpa = (float)Json.Num(matRaw, "hormigon_fc_MPa");
                    e.MatRef = Json.Str(matRaw, "referencia") ?? "";
                    e.MatNota = Json.Str(matRaw, "nota") ?? "";
                }

                // ejes locales (bloque `ejes_locales` del elemento) + restricciones por
                // nodo (bloque `restricciones`): fertilidad cruzada con el modelo FE
                // (BASE_FIJA_6DOF base cimentacion / LIBRE) y verificacion viewer<->FE.
                var ejesRaw = d.TryGetValue("ejes_locales", out var ejRaw) ? Json.AsObj(ejRaw) : null;
                if (ejesRaw != null)
                {
                    var zb = Json.Arr(ejesRaw, "Z_barra_unity");
                    if (zb != null && zb.Count >= 3)
                    {
                        e.TieneEjes = true;
                        for (int k = 0; k < 3; k++) e.EjeZBarra[k] = (float)Json.ToNum(zb[k]);
                        var rf = Json.Arr(ejesRaw, "referencia_geomTransf");
                        if (rf != null)
                        {
                            for (int k = 0; k < 3 && k < rf.Count; k++)
                                e.EjeRefGeomTransf[k] = (float)Json.ToNum(rf[k]);
                        }
                    }
                }
                var restRaw = d.TryGetValue("restricciones", out var rsRaw) ? Json.AsObj(rsRaw) : null;
                if (restRaw != null)
                {
                    e.TieneRestricciones = true;
                    e.RestrNodoI = Json.Str(restRaw, "nodo_i") ?? "";
                    e.RestrNodoJ = Json.Str(restRaw, "nodo_j") ?? "";
                    e.RestriccionesFlag = true;
                }
                _elementos.Add(e);
            }
        }

        private static Vector3 V3De(Dictionary<string, object> d, string key)
        {
            var arr = Json.Arr(d, key);
            if (arr == null || arr.Count < 3) return Vector3.zero;
            return new Vector3((float)Json.ToNum(arr[0]), (float)Json.ToNum(arr[1]), (float)Json.ToNum(arr[2]));
        }

        // ------------------------------------------------------------------ //
        //  Overlay
        // ------------------------------------------------------------------ //
        void Update()
        {
            // clic sobre un panel IMGUI => no seleccionar FE detras de la UI.
            if (InteraccionUI.PointerSobreUI()) return;
            if (!OverlayOn || !Input.GetMouseButtonDown(0)) return;
            if (Camera.main == null) return;
            // Seleccion por correspondencia viewer <-> FE: el ElementRef de la geometria
            // original (primer hit) define el viewer_id; los FE se eligen por el mapping
            // de correspondencias. Ya no se usa "EFPicker mas cercano a la camara".
            ProcesarClic(Input.mousePosition);
        }

        /// <summary>Llamado por ViewerController cuando cambian los filtros visuales.</summary>
        public void OnVisualFiltersChanged() => ApplyOverlayVisibility();

        private GameObject Raiz()
        {
            if (_raiz != null) return _raiz;
            var lab = GameObject.Find("Lab");
            if (lab == null) return null;
            _raiz = new GameObject(NOMBRE_RAIZ);
            _raiz.transform.SetParent(lab.transform, false);
            return _raiz;
        }

        /// <summary>Reconstruye el overlay FE sobre el edificio activo. Este es el
        /// PUNTO CANONICO por el que pasan TODOS los cambios de filtro/estado del
        /// panel (seleccion, edificio, caso base, combinacion, envolvente, caso
        /// FE, magnitud, representacion, escala y toggles de overlay); por eso
        /// tambien invalida el diagrama local del elemento: cualquier evento que
        /// reconstruya el overlay cambia las fuerzas mostradas, y el diagrama
        /// pertenece a ese FE.</summary>
        public void RebuildOverlay()
        {
            MarcarDiagramaSucio();  // disparadores: reconstruir overlay == datos cambiaron
            ClearOverlay();
            if (!_overlayOnChanged) ClearAttenuation();
            _overlayOnChanged = false;

            if (!OverlayOn)
            {
                SelectedFE = null;
                SincronizarInspeccion(null);
                SetResaltado(null);
                return;
            }

            var raiz = Raiz();
            if (raiz == null || _loader == null) return;
            CalcularEscala();
            foreach (var e in _elementos)
            {
                if (e.Building != Edificio) continue;
                if (e.Longitud < 1e-4f) continue;
                CrearTuberia(raiz, e);
            }
            ApplyAttenuation(true);
            ApplyOverlayVisibility();
            ReaplicarResaltado(); // conserva la seleccion y su brillo al cambiar caso/magnitud/etc
        }

        private void ClearOverlay()
        {
            _resaltado = null; // los GO se destruyen; evita tocar objetos destruidos al restaurar material
            foreach (var go in _overlay)
            {
                if (go == null) continue;
                go.SetActive(false); // evita render fantasma entre destruct y frame
                if (Application.isPlaying) Destroy(go);
                else DestroyImmediate(go);
            }
            _overlay.Clear();
        }

        private void CalcularEscala()
        {
            _maxReal = 0f;
            var valores = new List<float>();
            foreach (var e in _elementos)
            {
                if (e.Building != Edificio) continue;
                float v = e.Valor(Caso, MagnitudIdx, (int)Repre);
                if (float.IsNaN(v)) continue;
                float av = Mathf.Abs(v);
                if (av > _maxReal) _maxReal = av;
                valores.Add(av);
            }
            if (Escala == EscalaModo.Maximo)
            {
                _escala = _maxReal;
            }
            else
            {
                valores.Sort();
                int idx = Mathf.Clamp((int)Mathf.Floor(valores.Count * 0.95f), 0, valores.Count - 1);
                _escala = valores.Count > 0 ? valores[idx] : 1f;
            }
            if (_escala < 1e-9f) _escala = 1f;
        }

        private void CrearTuberia(GameObject raiz, EFElemento e)
        {
            // Posiciones MUNDIALES de los extremos del elemento FE (frame local del
            // edificio + placement). Solo se usan para orientar el prisma UNA vez.
            Vector3 w0 = _loader.ToWorldModel(e.Building, e.Pi.x, e.Pi.y, e.Pi.z);
            Vector3 w1 = _loader.ToWorldModel(e.Building, e.Pj.x, e.Pj.y, e.Pj.z);
            Vector3 mid = (w0 + w1) * 0.5f;
            float L = Vector3.Distance(w0, w1);
            if (L < 1e-4f) return;

            var go = new GameObject("EFE_" + e.Building + "_" + e.Tag);
            go.transform.SetParent(raiz.transform, false);
            if (_layerFE >= 0) go.layer = _layerFE; // capa exclusiva para raycast de seleccion

            // UN SOLO sistema de coordenadas CENTRADO: la malla se construye en espacio
            // local entre (0,-L/2,0) y (0,+L/2,0), el GameObject se coloca en `mid` y se
            // rota UNA vez para que su eje local siga w1-w0. Asi los extremos renderizados
            // caen exactamente en w0/w1. (No mezclar `0..L` con posicion en `mid`: eso
            // desplaza cada tuberia L/2 hacia el extremo j.)
            var mf = go.AddComponent<MeshFilter>();
            mf.sharedMesh = PrismaLocal(-L * 0.5f, L * 0.5f, 0.07f, (int)e.Tag);
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = MaterialPara(e);

            go.transform.position = mid;
            go.transform.rotation = Quaternion.FromToRotation(Vector3.up, (w1 - w0).normalized);

            // Collider en las MISMAS coordenadas locales (centrado en el origen).
            var bc = go.AddComponent<BoxCollider>();
            bc.center = Vector3.zero;
            bc.size = new Vector3(0.35f, L + 0.2f, 0.35f);

            var picker = go.AddComponent<EFPicker>();
            picker.Elem = e;
            picker.LocalA = new Vector3(0f, -L * 0.5f, 0f);
            picker.LocalB = new Vector3(0f, L * 0.5f, 0f);
            picker.OriginalMaterial = mr.sharedMaterial; // para restaurar al quitar el resaltado
            _overlay.Add(go);
        }

        /// <summary>Prisma en coordenadas LOCALES, con su eje a lo largo de +Y, desde
        /// altura =a hasta altura =b (ambas en el eje Y del objeto local). Los nodos
        /// viewers ya aplican position/rotation una sola vez; el render queda en el
        /// espacio del GameObject, sin transformar de nuevo.</summary>
        private static Mesh PrismaLocal(float a, float b, float radio, int seed)
        {
            var verts = new Vector3[8];
            for (int i = 0; i < 4; i++)
            {
                float ang = i * Mathf.PI * 0.5f;
                Vector2 cc = new Vector2(Mathf.Cos(ang), Mathf.Sin(ang)) * radio;
                verts[i] = new Vector3(cc.x, a, cc.y);
                verts[i + 4] = new Vector3(cc.x, b, cc.y);
            }
            var tris = new[]
            {
                0, 2, 1, 0, 3, 2,
                4, 5, 6, 4, 6, 7,
                0, 1, 5, 0, 5, 4,
                1, 2, 6, 1, 6, 5,
                2, 3, 7, 2, 7, 6,
                3, 0, 4, 3, 4, 7,
            };
            var m = new Mesh();
            m.name = "EFE_prism_" + seed;
            m.vertices = verts;
            m.triangles = tris;
            m.RecalculateNormals();
            return m;
        }

        private Material MaterialPara(EFElemento e)
        {
            float v = e.Valor(Caso, MagnitudIdx, (int)Repre);
            if (float.IsNaN(v))
                return new Material(Shader.Find("Standard")) { color = new Color(0.6f, 0.6f, 0.6f, 0.6f) };
            return new Material(Shader.Find("Standard")) { color = ColorPara(v) };
        }

        public Color ColorPara(float v)
        {
            float t = Mathf.Clamp(v / Mathf.Max(_escala, 1e-9f), -1f, 1f);
            if (t > 0f) return Color.Lerp(new Color(0.92f, 0.92f, 0.92f), new Color(0.82f, 0.05f, 0.02f), t);
            if (t < 0f) return Color.Lerp(new Color(0.92f, 0.92f, 0.92f), new Color(0.02f, 0.2f, 0.75f), -t);
            return new Color(0.92f, 0.92f, 0.92f);
        }

        // ------------------------------------------------------------------ //
        //  Atenuacion de la geometria original (solo color; nunca le asigna el
        //  valor FE. Restauracion de valores anteriores al apagar el overlay)
        // ------------------------------------------------------------------ //
        private void ApplyAttenuation(bool on)
        {
            if (on && !Application.isPlaying) return; // en modo editor no se atenua (evita fugas de material)
            var lab = GameObject.Find("Lab");
            if (lab == null) return;
            if (on)
            {
                if (_atenuados.Count > 0) return;
                foreach (var r in lab.GetComponentsInChildren<Renderer>())
                {
                    if (r.transform.IsChildOf(Raiz().transform)) continue;
                    _atenuados[r] = ColorParaBruto(r);
                    if (r.material != null) r.material.color = Color.Lerp(ColorParaBruto(r), Color.black, 0.45f);
                }
            }
            else ClearAttenuation();
        }

        private void ClearAttenuation()
        {
            foreach (var kv in _atenuados)
                if (kv.Key != null)
                {
                    var m = kv.Key.material;
                    if (m != null) m.color = kv.Value;
                }
            _atenuados.Clear();
        }

        private static Color ColorParaBruto(Renderer r)
        {
            var m = r.sharedMaterial;
            if (m != null && m.HasProperty("_Color")) return m.color;
            return Color.gray;
        }

        private void ApplyOverlayVisibility()
        {
            bool bI = _viewer == null || _viewer.BuildingVisible("I");
            bool bII = _viewer == null || _viewer.BuildingVisible("II");
            bool todos = FiltroCorr == "Todos los FE";
            foreach (var go in _overlay)
            {
                if (go == null) continue;
                var p = go.GetComponent<EFPicker>();
                if (p == null || p.Elem == null) { go.SetActive(false); continue; }
                bool bOn = p.Elem.Building == "I" ? bI : bII;
                bool nivelOn = _viewer == null || _viewer.LevelVisible(p.Elem.Nivel);
                bool tipoOn = FiltroTipo(p.Elem.Tipo);
                bool corrOn = todos || EsCorrespondenciaNormal(p.Elem);
                go.SetActive(bOn && nivelOn && tipoOn && corrOn);
            }
        }

        private bool FiltroTipo(string tipo)
        {
            if (tipo == null) return false;
            if (tipo.Contains("viga")) return FiltroVigas;
            if (tipo.Contains("columna")) return FiltroColumnas;
            if (tipo.Contains("muro")) return FiltroMuros;
            return true; // stubs/sin clasificar
        }

        /// <summary>Conjunto de filtros: "Mapeados" (modo normal, solo 1A1+CONTENIDO) o
        /// "Todos los FE" (modo de diagnostico, incluye SIN_CORRESPONDENCIA_VIEWER y
        /// stubs analiticos); además del filtro por tipología.</summary>
        public void SetFiltros(bool vigas, bool columnas, bool muros, string corr)
        {
            FiltroVigas = vigas;
            FiltroColumnas = columnas;
            FiltroMuros = muros;
            if (corr == "Todos los FE" || corr == "Mapeados") FiltroCorr = corr;
            ApplyOverlayVisibility();
        }

        // ------------------------------------------------------------------ //
        //  Hito B: deformada amplificada (desplazamientos FE del caso activo)
        // ------------------------------------------------------------------ //
        private void DestroyDeformada()
        {
            foreach (var go in _deformadaGo)
            {
                if (go == null) continue;
                if (Application.isPlaying) Destroy(go);
                else DestroyImmediate(go);
            }
            _deformadaGo.Clear();
        }

        /// <summary>Desplazamiento local por nodo del caso activo. Para la envolvente
        /// se toma max|u| por componente entre las 9 combinaciones explicitas (criterio
        /// independiente, igual que la envolvente de esfuerzos).</summary>
        private Dictionary<string, Vector3> DespActivo(string b, string caso)
        {
            var outD = new Dictionary<string, Vector3>();
            var porCaso = _despCaso.TryGetValue(b, out var pc) ? pc : null;
            if (porCaso == null) return outD;
            if (porCaso.TryGetValue(caso, out var d1))
            {
                foreach (var kv in d1)
                {
                    float[] v = kv.Value;
                    outD[kv.Key] = new Vector3(v[0], v[1], v[2]);
                }
                return outD;
            }
            if (caso == ENVOLVENTE)
            {
                for (int i = 0; i < COMBINACIONES.Length; i++)
                {
                    if (!porCaso.TryGetValue(COMBINACIONES[i], out var di)) continue;
                    foreach (var kv in di)
                    {
                        float[] v = kv.Value;
                        if (!outD.TryGetValue(kv.Key, out var cur))
                        {
                            outD[kv.Key] = new Vector3(v[0], v[1], v[2]);
                            continue;
                        }
                        if (Mathf.Abs(v[0]) > Mathf.Abs(cur.x)) cur.x = v[0];
                        if (Mathf.Abs(v[1]) > Mathf.Abs(cur.y)) cur.y = v[1];
                        if (Mathf.Abs(v[2]) > Mathf.Abs(cur.z)) cur.z = v[2];
                        outD[kv.Key] = cur;
                    }
                }
            }
            return outD;
        }

        public void RebuildDeformada()
        {
            DestroyDeformada();
            if (!MostrarDeformada || _loader == null) return;
            if (!_despCaso.TryGetValue(Edificio, out var porCaso) || porCaso.Count == 0) return;
            if (!_defNodos.TryGetValue(Edificio, out var nodos) || nodos.Count == 0) return;
            var desp = DespActivo(Edificio, Caso);
            if (desp.Count == 0) return;
            var raiz = Raiz();
            if (raiz == null) return;
            float A = Amplificacion;
            foreach (var e in _elementos)
            {
                if (e.Building != Edificio) continue;
                if (e.NodoI == null || e.NodoJ == null) continue;
                if (!desp.TryGetValue(e.NodoI, out var di)) continue;
                if (!desp.TryGetValue(e.NodoJ, out var dj)) continue;
                if (!nodos.TryGetValue(e.NodoI, out var ni)) continue;
                if (!nodos.TryGetValue(e.NodoJ, out var nj)) continue;
                Vector3 w0 = _loader.ToWorldModel(e.Building,
                    ni.x + di.x * A, ni.y + di.y * A, ni.z + di.z * A);
                Vector3 w1 = _loader.ToWorldModel(e.Building,
                    nj.x + dj.x * A, nj.y + dj.y * A, nj.z + dj.z * A);
                DrawDeformadaLine(w0, w1, new Color(0.95f, 0.16f, 0.2f),
                                 "DEF_EFE_" + e.Building + "_" + e.Tag, 0.15f);
            }
        }

        private void DrawDeformadaLine(Vector3 a, Vector3 b, Color c, string nombre, float grosor)
        {
            var lab = Raiz();
            if (lab == null) return;
            var go = new GameObject(nombre);
            go.transform.SetParent(lab.transform, false);
            var lr = go.AddComponent<LineRenderer>();
            lr.positionCount = 2;
            lr.SetPosition(0, a);
            lr.SetPosition(1, b);
            lr.startWidth = lr.endWidth = grosor;
            lr.material = new Material(Shader.Find("Standard")) { color = c };
            _deformadaGo.Add(go);
        }

        /// <summary>Desplazamiento (local, sin amplificar) del nodo i/j del elemento en el
        /// caso activo. False si no hay dato.</summary>
        public bool DespNodoElemento(EFElemento e, string cual, out Vector3 local)
        {
            local = Vector3.zero;
            string tag = cual == "i" ? e.NodoI : e.NodoJ;
            if (tag == null) return false;
            var desp = DespActivo(e.Building, Caso);
            return desp.TryGetValue(tag, out local);
        }

        // ------------------------------------------------------------------ //
        //  Hito B: panel P-M (capacidad DEMO / demanda concurrente NCh3171)
        // ------------------------------------------------------------------ //
        private static void PreparePlot(PMCurva c)
        {
            if (c.PlotTex != null) return;
            const int W = 190, H = 150;
            float mm = 1f, nm = 1f;
            for (int i = 0; i < c.M.Count; i++)
            {
                if (c.M[i] > mm) mm = c.M[i];
                if (c.N[i] > nm) nm = c.N[i];
            }
            c.PlotScaleM = mm;
            c.PlotScaleN = nm;
            var t = new Texture2D(W, H, TextureFormat.RGBA32, false);
            Color bg = new Color(0.96f, 0.96f, 0.96f);
            for (int y = 0; y < H; y++)
                for (int x = 0; x < W; x++)
                    t.SetPixel(x, y, bg);
            Color borde = new Color(0.25f, 0.25f, 0.25f);
            for (int x = 0; x < W; x++) { t.SetPixel(x, 0, borde); t.SetPixel(x, H - 1, borde); }
            for (int y = 0; y < H; y++) { t.SetPixel(0, y, borde); t.SetPixel(W - 1, y, borde); }
            if (c.N.Count > 0)
            {
                int pxPrev = 0, pyPrev = 0;
                for (int i = 0; i < c.N.Count; i++)
                {
                    int px = (int)(4 + (c.M[i] / c.PlotScaleM) * (W - 8));
                    int py = (int)(H - 4 - (c.N[i] / c.PlotScaleN) * (H - 8));
                    px = Mathf.Clamp(px, 1, W - 2);
                    py = Mathf.Clamp(py, 1, H - 2);
                    if (i > 0) PlotLinea(t, pxPrev, pyPrev, px, py, new Color(0.05f, 0.25f, 0.7f));
                    t.SetPixel(px, py, new Color(0.05f, 0.25f, 0.7f));
                    pxPrev = px; pyPrev = py;
                }
            }
            t.Apply();
            c.PlotTex = t;
        }

        private static void PlotLinea(Texture2D t, int x0, int y0, int x1, int y1, Color c)
        {
            int dx = Mathf.Abs(x1 - x0), dy = -Mathf.Abs(y1 - y0);
            int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
            int err = dx + dy;
            while (true)
            {
                if (x0 >= 0 && x0 < t.width && y0 >= 0 && y0 < t.height)
                    t.SetPixel(x0, y0, c);
                if (x0 == x1 && y0 == y1) break;
                int e2 = 2 * err;
                if (e2 >= dy) { err += dy; x0 += sx; }
                if (e2 <= dx) { err += dx; y0 += sy; }
            }
        }

        /// <summary>True si el elemento tiene bloque P-M visible en el panel (muro demo
        /// por viewer_id/tag o columna por tag). Se usa para auto-scroll a ese bloque.</summary>
        private bool TienePmVisible(EFElemento e)
        {
            if (e == null || !_pm.TryGetValue(e.Building, out var cap)) return false;
            bool esMuro = e.Tipo != null && e.Tipo.Contains("muro");
            if (esMuro)
            {
                if (cap.Muro == null) return false;
                bool coincide = !string.IsNullOrEmpty(cap.Muro.ViewerId) && !string.IsNullOrEmpty(e.ViewerId)
                    ? cap.Muro.ViewerId == e.ViewerId
                    : cap.Muro.Tag == e.Tag;
                return coincide;
            }
            return cap.PorElemento.ContainsKey(e.Tag);
        }

        private void DibujarPmBloque(EFElemento e)
        {
            if (!_pm.TryGetValue(e.Building, out var cap)) return;
            PMFila fila = null;
            PMCurva curva = cap.Columna;
            bool esMuro = e.Tipo != null && e.Tipo.Contains("muro");
            if (esMuro && cap.Muro != null)
            {
                // Identidad del muro por viewer_id (EII_CP1S_M_001): los dos segmentos FE
                // del contenido (tags 76/85) comparten el MISMO viewer; comparar solo por
                // tag dejaba sin P-M al segundo segmento. Fallback al tag si no hay viewer.
                bool coincide = !string.IsNullOrEmpty(cap.Muro.ViewerId) && !string.IsNullOrEmpty(e.ViewerId)
                    ? cap.Muro.ViewerId == e.ViewerId
                    : cap.Muro.Tag == e.Tag;
                if (coincide)
                {
                    fila = cap.Muro;
                    if (cap.MuroCurva != null) curva = cap.MuroCurva;
                }
            }
            if (fila == null) cap.PorElemento.TryGetValue(e.Tag, out fila);
            if (fila == null) return;

            GUILayout.Space(4);
            GUILayout.Box("P-M: capacidad DEMO + demanda concurrente");
            GUILayout.Label("Caso gobernante: " + fila.Caso
                            + (string.IsNullOrEmpty(fila.Expresion) ? "" : "  [" + fila.Expresion + "]")
                            + (fila.EsMuro ? "  (MURO EII)" : "  (columna)"));
            GUILayout.Label("P_u = " + fila.P.ToString("0.0") + " kN (comp. +)   "
                            + "M_demanda = " + fila.M.ToString("0.0") + " kN*m");
            GUILayout.Label("M_u(P) = " + fila.Mu.ToString("0.0") + " kN*m   ->   "
                            + "D/C = " + fila.DC.ToString("0.00"));
            if (curva != null)
            {
                GUILayout.Label("Capacidad: " + curva.Seccion + "  |  fc=" + curva.FcMpa
                                + " MPa  |  " + curva.Clasif);
            }
            if (curva != null && curva.N.Count > 1 && curva.M.Count > 1)
            {
                PreparePlot(curva);
                if (curva.PlotTex != null)
                {
                    Rect r = GUILayoutUtility.GetRect(190f, 150f);
                    GUI.DrawTexture(r, curva.PlotTex);
                    float px = r.x + 4 + (fila.M / curva.PlotScaleM) * (r.width - 8);
                    float py = r.y + (r.height - 4) - (fila.P / curva.PlotScaleN) * (r.height - 8);
                    GUI.color = new Color(0.85f, 0.1f, 0.05f);
                    GUI.DrawTexture(new Rect(px - 3f, py - 3f, 6f, 6f), Texture2D.whiteTexture);
                    GUI.color = Color.white;
                    GUILayout.Label("eje N compr. vertical arriba; M (kN*m) horizontal.");
                    GUILayout.Label("(demanda P-M = caso actual, D/C aritmético sin validez de diseño)");
                }
            }
            if (curva != null && !string.IsNullOrEmpty(curva.EstadoArmadura))
            {
                GUILayout.Label("Hipótesis de armadura: " + curva.EstadoArmadura);
            }
            if (fila.EsMuro && !string.IsNullOrEmpty(fila.Nota))
            {
                GUI.color = new Color(0.72f, 0.55f, 0.05f);
                GUILayout.Label("ADVERTENCIA: " + fila.Nota);
                GUI.color = Color.white;
            }
        }

        // ------------------------------------------------------------------ //
        //  UI (OnGUI propio; no modifica el panel del ViewerController)
        // ------------------------------------------------------------------ //
        void OnGUI()
        {
            // Mostrar si el overlay esta activo o hay una seleccion (FE o SOLO
            // ViewerSel con SIN_CORRESPONDENCIA: el panel informa que no se selecciono).
            if (!OverlayOn && SelectedFE == null && ViewerSel == null) return;
            DrawPanel();
        }

        /// <summary>El bloque de diagnostico se muestra solo cuando el plegable esta
        /// abierto y no estamos en el modo de presentacion compacta.</summary>
        private bool _diagnosticoEnPanel() => DiagnosticoVisible && !ModoPresentacion;

        private void DrawPanel()
        {
            if (MostrarDeformada && (_defUltimoCaso != Caso || _defUltimaB != Edificio))
            {
                _defUltimoCaso = Caso;
                _defUltimaB = Edificio;
                RebuildDeformada();
            }
            // Cabecera FIJA (siempre visible, nunca la oculta el scroll): modo de
            // pantalla, seleccion, edificio, modo de correspondencia, caso, magnitud y
            // toggles de vista. En presentacion el panel es SOLO esa cabecera; el detalle
            // tecnico baja dentro del bloque plegable de diagnostico con scroll propio.
            float pw = 348f, ph = ModoPresentacion ? 368f : 640f;
            float left = Screen.width - pw - 356f;
            if (left < 240f) left = 240f;

            // region del panel IMGUI: excluye del control de camara y de la
            // seleccion FE cualquier clic/scroll dentro de esta zona.
            Rect panelRect = new Rect(left, 10, pw + 120, ph);
            InteraccionUI.Registrar(panelRect);
            GUI.Box(new Rect(left, 10, pw, ph), "Resultados estructurales — Esfuerzos FE");
            GUILayout.BeginArea(new Rect(left + 4, 34, pw - 12, ph - 44));

            DibujarCabeceraFija();

            if (!EstaCargado(Edificio))
            {
                GUI.color = new Color(0.8f, 0.4f, 0.1f);
                GUILayout.Label("NO_DISPONIBLE: sin paquete de esfuerzos del edificio " + Edificio + ".");
                GUI.color = Color.white;
                GUILayout.EndArea();
                return;
            }

            if (!_diagnosticoEnPanel())
            {
                GUI.color = new Color(0.55f, 0.55f, 0.55f);
                if (SelectedFE != null)
                    GUILayout.Label("Elemento activo: tag " + SelectedFE.Tag + " [" + SelectedFE.Building
                                    + "] — el detalle queda en el modo diagnóstico.");
                else
                    GUILayout.Label("Seleccione un elemento FE (clic sobre el overlay).");
                GUI.color = Color.white;
                GUILayout.EndArea();
                return;
            }

            _scrollUI = GUILayout.BeginScrollView(_scrollUI, GUIStyle.none, GUI.skin.verticalScrollbar);
            DibujarBloqueDiagnostico();
            GUILayout.EndScrollView();
            GUILayout.EndArea();
        }

        /// <summary>Cabecera fija del panel: controles que nunca deben desaparecer con el
        /// scroll (modo de pantalla, seleccion, edificio, modo de correspondencia, caso,
        /// magnitud y toggles de vista) con los rótulos de estado VISIBLE/OCULTO del
        /// diagrama y de la deformada.</summary>
        private void DibujarCabeceraFija()
        {
            // modo de pantalla: presentacion compacta fija / diagnostico plegable
            GUILayout.BeginHorizontal();
            bool mPres = GUILayout.Toggle(ModoPresentacion, "Presentación (compacto)", "button");
            if (mPres != ModoPresentacion) ModoPresentacion = mPres;
            bool mDiag = GUILayout.Toggle(DiagnosticoVisible, "Diagnóstico", "button");
            if (mDiag != DiagnosticoVisible) DiagnosticoVisible = mDiag;
            GUILayout.EndHorizontal();

            // elemento seleccionado + valores (siempre visibles)
            DibujarCabeceraSeleccion();
            GUILayout.Space(3);

            // edificio (toggle estado inequivoco: verde=ACTIVADO, gris=INACTIVO)
            GUILayout.BeginHorizontal();
            GUILayout.Label("Edificio:");
            bool bI = InteraccionUI.ToggleEstado(Edificio == "I", "I", "button");
            bool bII = InteraccionUI.ToggleEstado(Edificio == "II", "II", "button");
            if (bI && Edificio != "I") { Edificio = "I"; SelectedFE = null; SincronizarInspeccion(null); SetResaltado(null); RebuildOverlay(); }
            if (bII && Edificio != "II") { Edificio = "II"; SelectedFE = null; SincronizarInspeccion(null); SetResaltado(null); RebuildOverlay(); }
            GUILayout.EndHorizontal();

            // modo de correspondencia (lista blanca normal / diagnostico completo)
            GUILayout.BeginHorizontal();
            GUILayout.Label("Modo:");
            bool fMape = InteraccionUI.ToggleEstado(FiltroCorr == "Mapeados", "Mapeados", "button");
            bool fTodos = InteraccionUI.ToggleEstado(FiltroCorr == "Todos los FE", "Todos los FE (diag.)", "button");
            GUILayout.EndHorizontal();
            if ((fMape && FiltroCorr != "Mapeados") || (fTodos && FiltroCorr != "Todos los FE"))
            {
                if (fMape) FiltroCorr = "Mapeados";
                if (fTodos) FiltroCorr = "Todos los FE";
                ApplyOverlayVisibility();
            }

            // caso base (G, Q, EX, EY)
            GUILayout.BeginHorizontal();
            GUILayout.Label("Caso:", GUILayout.Width(42));
            foreach (var c in CASOS_BASE)
            {
                bool onC = GUILayout.Toggle(Caso == c, c, "button");
                if (onC && Caso != c) { Caso = c; CombinacionIdx = -1; RebuildOverlay(); }
            }
            GUILayout.EndHorizontal();

            // combinaciones normativas NCh3171: paginado ◀/▶ (nombre + fórmula)
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("◀", GUILayout.Width(34))) CiclarCombinacion(-1);
            if (GUILayout.Button("▶", GUILayout.Width(34))) CiclarCombinacion(1);
            string comboNom = CombinacionIdx >= 0 ? COMBINACIONES[CombinacionIdx] : "—";
            GUILayout.Label("  " + comboNom, GUILayout.ExpandWidth(true));
            GUILayout.EndHorizontal();

            // envolvente NCh3171: visualización INDEPENDIENTE (no una corrida)
            bool envOn = GUILayout.Toggle(Caso == ENVOLVENTE, "Envolvente NCh3171 (independiente)", "button");
            if (envOn && Caso != ENVOLVENTE) SeleccionarEnvolvente();
            else if (!envOn && Caso == ENVOLVENTE) { Caso = CASOS_BASE[0]; CombinacionIdx = -1; RebuildOverlay(); }

            // magnitud
            GUILayout.BeginHorizontal();
            GUILayout.Label("Mag:", GUILayout.Width(42));
            for (int i = 0; i < MAGNITUDES.Length; i++)
            {
                int sel = i;
                if (GUILayout.Toggle(MagnitudIdx == i, MAGNITUDES[i], "button"))
                    if (MagnitudIdx != sel) { MagnitudIdx = sel; RebuildOverlay(); }
            }
            GUILayout.EndHorizontal();

            // toggles de vista: overlay FE + diagrama local (con estado explícito)
            GUILayout.BeginHorizontal();
            bool ov = InteraccionUI.ToggleEstado(OverlayOn, "Overlay FE", "button");
            if (ov != OverlayOn) SetOverlay(ov);
            bool dia = InteraccionUI.ToggleEstado(MostrarDiagrama, "Diagrama " + MAGNITUDES[MagnitudIdx], "button");
            if (dia != MostrarDiagrama) { MostrarDiagrama = dia; if (SelectedFE != null) DrawDiagrams(SelectedFE); }
            // Estado EXPLICITO: OCULTO / VISIBLE / SIN AMPLITUD (el componente del
            // elemento es 0 real, p.ej. Vy=Vz en celosias/grillage EII: es el numero
            // del JSON, no un fallo de mapeo ni un valor a inventar).
            string estadoDia;
            if (!MostrarDiagrama)
            {
                estadoDia = "OCULTO";
                GUI.color = Color.white;
            }
            else if (SelectedFE == null || !TieneAmplitud(SelectedFE))
            {
                estadoDia = "SIN AMPLITUD";
                GUI.color = new Color(1f, 0.65f, 0.2f);
            }
            else
            {
                estadoDia = "VISIBLE";
                GUI.color = new Color(0.35f, 1f, 0.45f);
            }
            GUILayout.Label("Diagrama " + MAGNITUDES[MagnitudIdx] + ": " + estadoDia);
            GUI.color = Color.white;
            GUILayout.EndHorizontal();

            // deformada
            GUILayout.BeginHorizontal();
            bool deh = InteraccionUI.ToggleEstado(MostrarDeformada, "Deformada", "button");
            if (deh != MostrarDeformada) { MostrarDeformada = deh; RebuildDeformada(); }
            if (MostrarDeformada) GUI.color = new Color(0.35f, 1f, 0.45f);
            GUILayout.Label(MostrarDeformada ? "Deformada: VISIBLE" : "Deformada: OCULTO");
            GUI.color = Color.white;
            GUILayout.EndHorizontal();
        }

        /// <summary>Bloque de diagnostico: filtros, representacion, escala, advertencias,
        /// conteos, ficha del elemento y botones. Solo se dibuja dentro de la zona con
        /// scroll cuando el plegable de diagnostico está abierto y no hay presentacion.</summary>
        private void DibujarBloqueDiagnostico()
        {
            // filtros de overlay (por tipo)
            GUILayout.Label("Filtros overlay — tipología:");
            GUILayout.BeginHorizontal();
            bool fv = InteraccionUI.ToggleEstado(FiltroVigas, "Vigas", "button");
            bool fc = InteraccionUI.ToggleEstado(FiltroColumnas, "Columnas", "button");
            bool fm = InteraccionUI.ToggleEstado(FiltroMuros, "Muros", "button");
            GUILayout.EndHorizontal();
            if (fv != FiltroVigas || fc != FiltroColumnas || fm != FiltroMuros)
            {
                FiltroVigas = fv;
                FiltroColumnas = fc;
                FiltroMuros = fm;
                ApplyOverlayVisibility();
            }
            if (FiltroCorr == "Todos los FE")
            {
                GUI.color = new Color(0.8f, 0.55f, 0.1f);
                GUILayout.Label("Modo de diagnóstico: incluye SIN_CORRESPONDENCIA_VIEWER,");
                GUILayout.Label("SIN_GEOMETRIA_FISICA_3D y stubs analíticos del modelo FE.");
                GUI.color = Color.white;
            }
            else
            {
                GUI.color = new Color(0.5f, 0.5f, 0.5f);
                GUILayout.Label("Modo normal (lista blanca): solo 1A1 y CONTENIDO; los");
                GUILayout.Label("estados SIN_* (incl. SIN_GEOMETRIA_FISICA_3D) y stubs se");
                GUILayout.Label("muestran únicamente en el modo de diagnóstico.");
                GUI.color = Color.white;
            }

            if (CombinacionIdx >= 0)
            {
                string sel = COMBINACIONES[CombinacionIdx];
                GUILayout.Label("Nombre: " + sel);
                GUILayout.Label("Fórmula: " + FORMULAS[sel] + "   [corrida FE EXPLICITA]");
            }
            else if (Caso != ENVOLVENTE)
            {
                GUILayout.Label("◀/▶ para elegir una combinación, o active la envolvente abajo.");
            }

            if (Caso == ENVOLVENTE)
            {
                GUILayout.Label("Máx |valor| por componente entre las 9 combinaciones;");
                GUILayout.Label("se conserva el caso y el signo gobernante.");
            }
            GUI.color = new Color(0.7f, 0.7f, 0.7f);
            GUILayout.Label("NCh3171: en combinaciones sísmicas Q=1.0 es la combinación");
            GUILayout.Label("básica adoptada (sin la reducción opcional a 0.5).");
            GUI.color = Color.white;

            // representacion
            GUILayout.Label("Representación:");
            GUILayout.BeginHorizontal();
            if (GUILayout.Toggle(Repre == Representacion.ExtremoI, "Extremo i", "button"))
                if (Repre != Representacion.ExtremoI) { Repre = Representacion.ExtremoI; RebuildOverlay(); }
            if (GUILayout.Toggle(Repre == Representacion.ExtremoJ, "Extremo j", "button"))
                if (Repre != Representacion.ExtremoJ) { Repre = Representacion.ExtremoJ; RebuildOverlay(); }
            if (GUILayout.Toggle(Repre == Representacion.MaxAbs, "Max abs", "button"))
                if (Repre != Representacion.MaxAbs) { Repre = Representacion.MaxAbs; RebuildOverlay(); }
            GUILayout.EndHorizontal();

            // escala
            GUILayout.Label("Escala:");
            GUILayout.BeginHorizontal();
            if (GUILayout.Toggle(Escala == EscalaModo.Percentil95, "P95", "button"))
                if (Escala != EscalaModo.Percentil95) { Escala = EscalaModo.Percentil95; RebuildOverlay(); }
            if (GUILayout.Toggle(Escala == EscalaModo.Maximo, "Maximo", "button"))
                if (Escala != EscalaModo.Maximo) { Escala = EscalaModo.Maximo; RebuildOverlay(); }
            GUILayout.EndHorizontal();

            DrawColorBar();

            // advertencia de interpolacion: una sola linea
            if (MostrarDiagrama)
            {
                GUI.color = new Color(0.72f, 0.55f, 0.05f);
                GUILayout.Label("Diagrama interpolado desde fuerzas de extremo; no refleja la");
                GUILayout.Label("distribución continua exacta bajo carga distribuida.");
                GUI.color = Color.white;
            }

            if (MostrarDeformada)
            {
                GUILayout.BeginHorizontal();
                GUILayout.Label("Amplif. x", GUILayout.Width(58));
                float nv = GUILayout.HorizontalSlider(Amplificacion, 1f, 300f);
                GUILayout.Label(Amplificacion.ToString("0"), GUILayout.Width(30));
                GUILayout.EndHorizontal();
                if (Mathf.Abs(nv - Amplificacion) > 0.01f)
                {
                    Amplificacion = nv;
                    RebuildDeformada();
                }
            }

            GUILayout.Space(6);
            if (GUILayout.Button("Restaurar aspecto original"))
            {
                SetOverlay(false);
            }
            if (GUILayout.Button("Capturar pantalla (PNG)")) GuardarCaptura();

            GUILayout.Space(8);
            ConteosCorrespondencia(Edificio, out int totFE, out int mapFE, out int sinFE, out int stubsFE);
            int baseCobertura = totFE - stubsFE;
            float pct = baseCobertura > 0 ? 100f * mapFE / baseCobertura : 0f;
            GUILayout.Label(string.Format("FE_TOTAL: {0}   OVERLAY_NORMAL_MAPEADO (1A1+CONTENIDO): {1}", totFE, mapFE));
            GUILayout.Label(string.Format("SIN_CORRESPONDENCIA_VIEWER: {0} (stubs analiticos: {1})", sinFE, stubsFE));
            int nSinGeo = 0;
            foreach (var ee in _elementos)
                if (ee.Building == Edificio && ee.EstadoCorr == "SIN_GEOMETRIA_FISICA_3D") nSinGeo++;
            GUILayout.Label(string.Format("SIN_GEOMETRIA_FISICA_3D (solo diagnóstico): {0}", nSinGeo));
            GUILayout.Label(string.Format("Cobertura viewer\u2194FE (excluye stubs): {0}/{1} ({2:0.0}%)   ",
                                          mapFE, baseCobertura, pct));
            if (SelectedFE != null) DrawFicha(SelectedFE);
            else GUILayout.Label("Seleccione un elemento FE (clic sobre el overlay).");
        }

        private void DibujarCabeceraSeleccion()
        {
            // Linea Viewer: el ElementRef (geometria original) que origina la seleccion.
            if (ViewerSel != null)
                GUILayout.Label("Viewer: " + ViewerSel.Id + " · " + TipoViewerNombre(ViewerSel.Type)
                                + " · nivel " + ViewerSel.Level + "  [" + ViewerSel.Building + "]");
            else if (SelectedFE != null)
                GUILayout.Label("Viewer: (tuberia directa sin ElementRef)");

            if (SelectedFE != null)
            {
                var e = SelectedFE;
                string estado = EstadoMostrar(e);
                string tagTexto = "tag " + e.Tag;
                if (Segmentos.Count > 1)
                    tagTexto += "  ·  segmento " + (SegmentoIdx + 1) + "/" + Segmentos.Count;
                if (e.Tipo == null || e.Tipo.Length == 0)
                    GUILayout.Label("Elemento FE seleccionado: " + tagTexto + "  [" + e.Building + "]");
                else
                    GUILayout.Label("Elemento FE seleccionado: " + tagTexto + " · " + e.Tipo
                                    + " · nivel " + e.Nivel + "  [" + e.Building + "]");
                GUILayout.Label("Estado correspondencia: " + estado);

                if (Segmentos.Count > 1)
                {
                    GUILayout.BeginHorizontal();
                    if (GUILayout.Button("◀ segmento")) CiclarSegmento(-1);
                    GUILayout.Label("  " + (SegmentoIdx + 1) + "/" + Segmentos.Count + "  ");
                    if (GUILayout.Button("segmento ▶")) CiclarSegmento(1);
                    GUILayout.EndHorizontal();
                }

                var eSel = e;
                bool envSel = Caso == ENVOLVENTE;
                float mostrado;
                if (envSel)
                {
                    mostrado = eSel.Valor(ENVOLVENTE, MagnitudIdx, (int)Repre);
                    if (float.IsNaN(mostrado))
                        mostrarSIN_RESULTADO("Sin resultado para " + ENVOLVENTE + " en esta componente.");
                    else
                    {
                        int iIdx = MagnitudIdx, jIdx = MagnitudIdx + 6;
                        string si = eSel.EnvCasos[iIdx];
                        string sj = eSel.EnvCasos[jIdx];
                        string t_i = si == null ? "SIN_RESULTADO" : eSel.EnvValores[iIdx].ToString("0.###") + " [" + si + "]";
                        string t_j = sj == null ? "SIN_RESULTADO" : eSel.EnvValores[jIdx].ToString("0.###") + " [" + sj + "]";
                        GUILayout.Label(string.Format("{0}_i: {1}    {0}_j: {2}    {3}: {4} {5}   [Envolvente NCh3171]",
                            MAGNITUDES[MagnitudIdx], t_i, t_j, RepreNombre(Repre), mostrado.ToString("0.###"), Unidades()));
                    }
                }
                else
                {
                    var f = eSel.De(Caso);
                    if (f == null || float.IsNaN(eSel.Valor(Caso, MagnitudIdx, (int)Repre)))
                        mostrarSIN_RESULTADO("Sin resultado para caso " + Caso + ".");
                    else
                    {
                        float vi = f[MagnitudIdx], vj = f[MagnitudIdx + 6];
                        mostrado = eSel.Valor(Caso, MagnitudIdx, (int)Repre);
                        GUILayout.Label(string.Format("{0}_i={1:0.###}   {0}_j={2:0.###}   {3}={4:0.###} {5}   [{6}]",
                            MAGNITUDES[MagnitudIdx], vi, vj, RepreNombre(Repre), mostrado, Unidades(), Caso));
                    }
                }
            }
            else if (ViewerSel != null)
            {
                GUI.color = new Color(0.9f, 0.3f, 0.25f);
                GUILayout.Label("SIN_CORRESPONDENCIA_VIEWER: este elemento del viewer");
                GUILayout.Label("no tiene un FE mapeado (no se seleccionó otra barra).");
                GUI.color = Color.white;
            }
            else
            {
                GUI.color = new Color(0.9f, 0.3f, 0.25f);
                GUILayout.Label("No se seleccionó un elemento FE (clic sobre el overlay).");
                GUI.color = Color.white;
            }
        }

        private void mostrarSIN_RESULTADO(string msg)
        {
            GUI.color = new Color(0.8f, 0.55f, 0.1f);
            GUILayout.Label("Valores: " + msg);
            GUI.color = Color.white;
        }

        private static string EstadoMostrar(EFElemento e)
        {
            if (e.EstadoCorr == null) return "SIN_CORRESPONDENCIA_VIEWER";
            switch (e.EstadoCorr)
            {
                case "1A1": return "1A1";
                case "CONTENIDO": return "CONTENIDO";
                case "SIN_GEOMETRIA_FISICA_3D": return "SIN_GEOMETRIA_FISICA_3D";
                default: return "SIN_CORRESPONDENCIA_VIEWER";
            }
        }

        private static string TipoViewerNombre(ElemType t)
        {
            switch (t)
            {
                case ElemType.Columnas: return "Columnas";
                case ElemType.Vigas: return "Vigas";
                case ElemType.Muros: return "Muros";
                case ElemType.Losas: return "Losas";
                case ElemType.Diafragma: return "Diafragma";
                case ElemType.Abertura: return "Abertura";
                case ElemType.Nodos: return "Nodos";
                default: return t.ToString();
            }
        }

        private void DrawColorBar()
        {
            float barW = 200f, barH = 18f;
            GUILayout.Label("Mapa de color (divergente por signo):");
            var rect = GUILayoutUtility.GetRect(barW, barH);
            for (int i = 0; i < 40; i++)
            {
                float t = -1f + 2f * i / 39f;
                var c = ColorPara(t * _escala);
                GUI.color = c;
                GUI.DrawTexture(new Rect(rect.x + i * (barW / 40f), rect.y, barW / 40f + 0.5f, barH), Texture2D.whiteTexture);
            }
            GUI.color = Color.white;
            GUILayout.Label("min " + (-_escala).ToString("0.##") + "   cero    max " + _escala.ToString("0.##"));
            GUILayout.Label("Nota: escala GLOBAL del edificio (una sola barra para todo el");
            GUILayout.Label("overlay); el diagrama del elemento usa su escala LOCAL propia.");
            GUILayout.Label("Escala actual: " + _escala.ToString("0.##") + "   Max real: " + _maxReal.ToString("0.##"));
        }

        private void GuardarCaptura()
        {
            string root = new System.IO.DirectoryInfo(Application.dataPath).Parent.FullName;
            string dir = System.IO.Path.Combine(root, "capturas");
            if (!System.IO.Directory.Exists(dir)) System.IO.Directory.CreateDirectory(dir);
            string name = "jugador_esfuerzos_" + Caso.Replace('/', '_') + "_" + System.DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".png";
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(dir, name));
            Debug.Log("[EsfuerzosFE] Captura guardada: capturas/" + name);
        }

        private void DrawFicha(EFElemento e)
        {
            GUILayout.Space(6);
            GUILayout.Box("Elemento FE seleccionado");
            GUILayout.Label("tag: " + e.Tag + "   (" + e.Building + ")");
            GUILayout.Label("Tipo: " + e.Tipo + "   Nivel: " + e.Nivel);
            GUILayout.Label("Seccion: " + e.Seccion);
            GUILayout.Label("Nodos i/j: " + e.NodoI + " / " + e.NodoJ);
            GUILayout.Label("Local i: (" + e.Pi.x.ToString("0.##") + ", " + e.Pi.y.ToString("0.##")
                            + ", " + e.Pi.z.ToString("0.##") + ") m");
            GUILayout.Label("Local j: (" + e.Pj.x.ToString("0.##") + ", " + e.Pj.y.ToString("0.##")
                            + ", " + e.Pj.z.ToString("0.##") + ") m");

            // Ejes locales (bloque `ejes_locales` del elemento): Z_barra en frame Unity
            // (u, cota, v) y vector de referencia usado por el geomTransf del motor FE.
            if (e.TieneEjes)
            {
                GUILayout.Label("Ejes locales (Z_barra en frame Unity u,cota,v):");
                GUILayout.Label("  Z_barra   = (" + e.EjeZBarra[0].ToString("0.###") + ", "
                              + e.EjeZBarra[1].ToString("0.###") + ", "
                              + e.EjeZBarra[2].ToString("0.###") + ")");
                GUILayout.Label("  ref geom  = (" + e.EjeRefGeomTransf[0].ToString("0.###") + ", "
                              + e.EjeRefGeomTransf[1].ToString("0.###") + ", "
                              + e.EjeRefGeomTransf[2].ToString("0.###") + ")");
            }

            // Restricciones de apoyo por nodo (BASE_FIJA_6DOF = base de cimentacion fija
            // del FE; LIBRE = nodo sin fijacion). Bloque `restricciones` del elemento.
            if (e.TieneRestricciones)
            {
                GUILayout.Label("Restricciones de apoyo:");
                GUILayout.Label("  nodo i: " + e.RestrNodoI);
                GUILayout.Label("  nodo j: " + e.RestrNodoJ);
                if (!string.IsNullOrEmpty(e.RestrNota))
                    GUILayout.Label("  nota: " + e.RestrNota);
            }

            // Ejes locales (bloque `ejes_locales`): Z_barra en frame Unity (u, cota, v)
            // y vector de referencia usado por el geomTransf del motor FE.
            if (e.TieneEjes)
            {
                GUILayout.Label("Ejes locales (Z_barra en frame Unity u,cota,v):");
                GUILayout.Label("  Z_barra = (" + e.EjeZBarra[0].ToString("0.###") + ", "
                              + e.EjeZBarra[1].ToString("0.###") + ", "
                              + e.EjeZBarra[2].ToString("0.###") + ")");
                GUILayout.Label("  ref geomTransf = (" + e.EjeRefGeomTransf[0].ToString("0.###") + ", "
                              + e.EjeRefGeomTransf[1].ToString("0.###") + ", "
                              + e.EjeRefGeomTransf[2].ToString("0.###") + ")");
            }

            // Restricciones de apoyo por nodo (bloque `restricciones`):
            // BASE_FIJA_6DOF = base de cimentacion fija del FE | LIBRE = sin fijacion.
            if (e.TieneRestricciones)
            {
                GUILayout.Label("Restricciones de apoyo:");
                GUILayout.Label("  nodo " + e.RestrNodoI);
                GUILayout.Label("  nodo " + e.RestrNodoJ);
                if (!string.IsNullOrEmpty(e.RestrNota))
                    GUILayout.Label("  nota: " + e.RestrNota);
            }
            switch (e.EstadoCorr)
            {
                case "1A1":
                    GUILayout.Label("Correspondencia viewer: 1A1 -> " + e.ViewerId + " [" + e.ViewerNivel + "]");
                    break;
                case "CONTENIDO":
                    GUILayout.Label("Correspondencia viewer: CONTENIDO -> " + e.ViewerId + " [" + e.ViewerNivel + "]");
                    break;
                default:
                    GUILayout.Label("Sin correspondencia: " + (e.EstadoCorr ?? "SIN_CORRESPONDENCIA_VIEWER"));
                    break;
            }

            // Hito B: material de la ficha (desde el perfil)
            if (e.TieneMaterial)
            {
                GUILayout.Label("Material: hormigón fc = " + e.HcFcMpa.ToString("0.#") + " MPa"
                                + (string.IsNullOrEmpty(e.MatRef) ? "" : "  |  " + e.MatRef));
                if (!string.IsNullOrEmpty(e.MatNota))
                {
                    GUI.color = new Color(0.7f, 0.55f, 0.05f);
                    GUILayout.Label(e.MatNota);
                    GUI.color = Color.white;
                }
            }
            else GUILayout.Label("Material: no disponible en el perfil");

            // Hito B: reaccion de base (G) si el nodo i es apoyo con reaccion > 0
            if (e.Tipo != null && e.Tipo.Contains("columna")
                && _reaccionesG.TryGetValue(e.Building, out var rG)
                && rG.TryGetValue(e.NodoI ?? "", out var rr))
            {
                GUILayout.Label("Reacción G base (nodo " + e.NodoI + "):");
                GUILayout.Label(string.Format("  R=({0:0.0}, {1:0.0}, {2:0.0}) kN",
                                 rr[0], rr[1], rr[2]));
                GUILayout.Label(string.Format("  M=({0:0.0}, {1:0.0}, {2:0.0}) kN*m",
                                 rr[3], rr[4], rr[5]));
            }

            // Hito B: desplazamiento de los nodos i/j en el caso activo
            bool dI = DespNodoElemento(e, "i", out var udI);
            bool dJ = DespNodoElemento(e, "j", out var udJ);
            if (dI || dJ)
            {
                GUILayout.Label("Desplazamientos (caso " + Caso + ", sin amplificar):");
                if (dI) GUILayout.Label(string.Format("  nodo {0}: u=({1:0.###}, {2:0.###}, {3:0.###}) m",
                                                      e.NodoI, udI.x, udI.y, udI.z));
                if (dJ) GUILayout.Label(string.Format("  nodo {0}: u=({1:0.###}, {2:0.###}, {3:0.###}) m",
                                                      e.NodoJ, udJ.x, udJ.y, udJ.z));
            }

            DibujarPmBloque(e);

            GUILayout.Space(4);
            if (Caso == ENVOLVENTE)
            {
                GUILayout.Label("Envolvente NCh3171 (kN / kN*m) — caso y valor gobernante:");
                string[] nom = { "N", "Vy", "Vz", "T", "My", "Mz" };
                GUILayout.Label("  i: " + FilaEnvolvente(nom, e, 0));
                GUILayout.Label("  j: " + FilaEnvolvente(nom, e, 6));
            }
            else
            {
                GUILayout.Label("Fuerzas locales (kN / kN*m) — caso " + Caso + ":");
                var f = e.De(Caso);
                if (f == null)
                {
                    GUILayout.Label("SIN_RESULTADO para " + Caso);
                }
                else
                {
                    string[] nom = { "N", "Vy", "Vz", "T", "My", "Mz" };
                    GUILayout.Label("  i: " + Fila(nom, f, 0, MagnitudIdx));
                    GUILayout.Label("  j: " + Fila(nom, f, 6, MagnitudIdx));
                }
            }

            GUILayout.Space(4);
            float val = e.Valor(Caso, MagnitudIdx, (int)Repre);
            if (!float.IsNaN(val))
            {
                GUILayout.Label("Valor (" + MAGNITUDES[MagnitudIdx] + ", " + RepreNombre(Repre) + "): "
                                + val.ToString("0.####") + "  " + Unidades());
            }
            else GUILayout.Label("Valor: SIN_RESULTADO");

            // ------------------------------------------------------------------ //
            //  Diagrama = SOLO al cambiar estado, NUNCA por frame (OnGUI/DrawFicha
            //  corre cada frame; dibujar aqui destruiria/recrearia continuamente).
            //  Los eventos de cambio (seleccion/segmento/edificio/caso/combinacion/
            //  magnitud/representacion/escala/toggle) fijan _diagramaSucia; aqui
            //  SOLO se redibuja una vez por cambio real.
            //  La escala del diagrama es LOCAL del elemento (visible aun con valores
            //  pequenos p.ej. My 24,38 en un edificio con pico global ±800,26).
            // ------------------------------------------------------------------ //
            if (MostrarDiagrama && _diagramaSucia)
            {
                _diagramaSucia = false;
                DrawDiagrams(e);
            }
        }

        private static string Fila(string[] nom, float[] f, int baseIdx, int magnitud)
        {
            var partes = new List<string>();
            for (int k = 0; k < 6; k++)
            {
                partes.Add(nom[k] + "=" + f[baseIdx + k].ToString("0.###"));
            }
            return string.Join("  ", partes);
        }

        private static string FilaEnvolvente(string[] nom, EFElemento e, int baseIdx)
        {
            var partes = new List<string>();
            for (int k = 0; k < 6; k++)
            {
                int idx = baseIdx + k;
                string c = e.EnvCasos[idx];
                partes.Add(c == null ? nom[k] + "=SIN_RESULTADO"
                                     : nom[k] + "=" + e.EnvValores[idx].ToString("0.###") + "[" + c + "]");
            }
            return string.Join("  ", partes);
        }

        private string RepreNombre(Representacion r)
        {
            switch (r)
            {
                case Representacion.ExtremoI: return "extremo i";
                case Representacion.ExtremoJ: return "extremo j";
                default: return "max abs";
            }
        }

        private static bool EsMomento(int m) => m >= 3;
        private string Unidades() => EsMomento(MagnitudIdx) ? "kN*m" : "kN";

        // ------------------------------------------------------------------ //
        //  Diagrama local interpolado (solo del elemento seleccionado)
        // ------------------------------------------------------------------ //
        private bool _diagramaSucia;                  // evento: seleccion/segmento/edificio/caso/
        //  combinacion/magnitud/representacion/escala/toggle fijan esta bandera;
        //  DrawFicha SOLO redibuja el diagrama cuando esta sucia (nunca por frame).
        private readonly Color[] _colorMagnitud = new Color[6]
        {
            Color.cyan,                       // N
            new Color(0.30f, 1f, 0.50f),      // Vy
            Color.magenta,                    // Vz
            new Color(1f, 0.70f, 0.20f),      // T
            Color.yellow,                     // My
            new Color(1f, 0.50f, 0f)          // Mz
        };

        private readonly List<GameObject> _diagramas = new List<GameObject>();

        /// <summary>True si la magnitud ACTIVA del elemento tiene amplitud no nula:
        /// max(|extremo i|, |extremo j|) &gt; ~1e-4 en el caso/envolvente actual.
        /// Con ceros REALES (p.ej. Vy=Vz en celosias/grillage del EII, cuyo JSON trae
        /// los 12 valores a 0) el diagrama no se dibuja y la cabecera indica
        /// "SIN AMPLITUD": es el resultado del modelo, no un fallo de mapeo.</summary>
        public bool TieneAmplitud(EFElemento e)
        {
            if (e == null) return false;
            int m = MagnitudIdx;
            float vi, vj;
            if (Caso == ENVOLVENTE && e.EnvValores != null)
            {
                vi = float.IsNaN(e.EnvValores[m]) ? 0f : e.EnvValores[m];
                vj = float.IsNaN(e.EnvValores[m + 6]) ? 0f : e.EnvValores[m + 6];
            }
            else
            {
                var f = e.De(Caso);
                if (f == null) return false;
                vi = float.IsNaN(f[m]) ? 0f : f[m];
                vj = float.IsNaN(f[m + 6]) ? 0f : f[m + 6];
            }
            return Mathf.Max(Mathf.Abs(vi), Mathf.Abs(vj)) > 1e-4f;
        }

        /// <summary>ElementRef del viewer que representa a este FE (muro/viga) para
        /// obtener el espesor real y el plano del panel (normal al muro).</summary>
        private bool NormalPanelMuro(EFElemento e, out Vector3 n, out float espesor)
        {
            n = Vector3.zero;
            espesor = 0f;
            if (_loader == null || _loader.Model == null || string.IsNullOrEmpty(e.ViewerId))
                return false;
            foreach (var r in _loader.Model.Elements)
            {
                if (r == null || r.Building != e.Building || r.Id != e.ViewerId) continue;
                if (r.Type != ElemType.Muros) continue;
                // r.P0/r.P1 = extremos del panel en frame local (u, cota, v);
                // tangente del plano = direccion del panel, barra = eje vertical del FE.
                Vector3 a = _loader.ToWorldModel(e.Building, r.P0.x, r.P0.y, r.P0.z);
                Vector3 b = _loader.ToWorldModel(e.Building, r.P1.x, r.P1.y, r.P1.z);
                Vector3 tang = (b - a).normalized;
                Vector3 w0 = _loader.ToWorldModel(e.Building, e.Pi.x, e.Pi.y, e.Pi.z);
                Vector3 w1 = _loader.ToWorldModel(e.Building, e.Pj.x, e.Pj.y, e.Pj.z);
                Vector3 dir = (w1 - w0).normalized;
                if (tang.sqrMagnitude < 1e-6f || dir.sqrMagnitude < 1e-6f) continue;
                Vector3 c = Vector3.Cross(dir, tang);
                if (c.sqrMagnitude < 1e-6f) continue;
                n = c.normalized;
                espesor = r.Espesor;
                return true;
            }
            return false;
        }

        /// <summary>Centro (mundo) aproximado del edificio: media de los extremos de su
        /// geometria viewer. Se usa para despejar el diagrama del muro hacia el lado
        /// EXTERIOR del panel (alejado del interior del edificio).</summary>
        private Vector3 CentroEdificio(string b)
        {
            if (_loader == null || _loader.Model == null) return Vector3.zero;
            Vector3 s = Vector3.zero;
            int n = 0;
            foreach (var r in _loader.Model.Elements)
            {
                if (r == null || r.Building != b) continue;
                s += _loader.ToWorldModel(b, r.P0.x, r.P0.y, r.P0.z);
                s += _loader.ToWorldModel(b, r.P1.x, r.P1.y, r.P1.z);
                n += 2;
            }
            return n > 0 ? s / n : Vector3.zero;
        }

        /// <summary>Seccion textual FE del viewer vinculado (ficha del inspector viewer).
        /// Con CONTENIDO (varios FE por viewer) usa el primero que tenga seccion.</summary>
        public string SeccionDe(ElementRef r)
        {
            if (r == null) return null;
            foreach (var e in _elementos)
            {
                if (e.Building != r.Building) continue;
                if (string.Equals(e.ViewerId, r.Id) && !string.IsNullOrEmpty(e.Seccion))
                    return e.Seccion;
            }
            return null;
        }

        private void DrawDiagrams(EFElemento e)
        {
            foreach (var go in _diagramas)
            {
                if (go == null) continue;
                if (Application.isPlaying) Destroy(go);
                else DestroyImmediate(go);
            }
            _diagramas.Clear();
            if (!MostrarDiagrama || _loader == null || e == null) return;

            // ------------------------------------------------------------------ //
            //  Magnitud ACTIVA del panel (MagnitudIdx 0..5 = N, Vy, Vz, T, My, Mz).
            //  Extremo i en el indice m y extremo j en m+6 del vector local FE
            //  (f[0..5] = i; f[6..11] = j). Con la envolvente NCh3171 los valores
            //  i/j provienen de EnvValores/EnvCasos (caso y signo gobernantes).
            // ------------------------------------------------------------------ //
            int m = MagnitudIdx;
            float vi, vj;
            if (Caso == ENVOLVENTE && e.EnvValores != null)
            {
                vi = float.IsNaN(e.EnvValores[m]) ? 0f : e.EnvValores[m];
                vj = float.IsNaN(e.EnvValores[m + 6]) ? 0f : e.EnvValores[m + 6];
            }
            else
            {
                var f = e.De(Caso);
                if (f == null) return;
                vi = float.IsNaN(f[m]) ? 0f : f[m];
                vj = float.IsNaN(f[m + 6]) ? 0f : f[m + 6];
            }
            // SIN AMPLITUD: el componente es 0 real (p.ej. Vy/Vz de celosias/grillage).
            // No se inventa nada ni se sustituye valor; simplemente no hay curva.
            if (Mathf.Max(Mathf.Abs(vi), Mathf.Abs(vj)) <= 1e-4f) return;

            Vector3 w0 = _loader.ToWorldModel(e.Building, e.Pi.x, e.Pi.y, e.Pi.z);
            Vector3 w1 = _loader.ToWorldModel(e.Building, e.Pj.x, e.Pj.y, e.Pj.z);
            Vector3 dir = (w1 - w0).normalized;
            if (dir.sqrMagnitude < 1e-9f) return;

            // ------------------------------------------------------------------ //
            //  Ejes locales REALES del FE (bloque `ejes_locales` del JSON / frame
            //  Unity u,cota,v). Z_barra = eje local z del geomTransf del motor;
            //  Y_barra = completacion ortogonal con el eje de la barra.
            //  Plano de dibujo del diagrama (convencion documentada):
            //    N  (0) y T (3): sin desplazamiento transversal (se dibuja a lo largo
            //        de la barra; montante vertical minimo para no quedar si se usa
            //        Representacion diferente de i/j).
            //    Vy (1) y Mz (5): flexion/corte en el plano local X-Y  -> eje Z_barra.
            //    Vz (2) y My (4): flexion/corte en el plano local X-Z  -> eje Y_barra.
            // ------------------------------------------------------------------ //
            Vector3 zLocal = (e.TieneEjes && e.EjeZBarra != null)
                ? new Vector3(e.EjeZBarra[0], e.EjeZBarra[1], e.EjeZBarra[2]).normalized
                : Vector3.zero;
            if (zLocal.sqrMagnitude < 1e-4f)
            {
                Vector3 up0 = Mathf.Abs(Vector3.Dot(dir, Vector3.up)) < 0.9f ? Vector3.up : Vector3.forward;
                zLocal = Vector3.Cross(dir, up0).normalized;
            }
            // `Z_barra` (casi) PARALELO al eje de la barra: el dato exportado no sirve
            // como perpendicular (viga horizontal con Z_barra_unity=[1,0,0]=eje X).
            // Se regenera un eje transversal ortogonal al eje de la barra.
            if (Mathf.Abs(Vector3.Dot(dir, zLocal)) > 0.9f)
            {
                Vector3 up1 = Mathf.Abs(Vector3.Dot(dir, Vector3.up)) < 0.9f ? Vector3.up : Vector3.forward;
                zLocal = Vector3.Cross(dir, up1).normalized;
            }
            Vector3 yLocal = Vector3.Cross(dir, zLocal).normalized;
            if (yLocal.sqrMagnitude < 1e-4f)
                yLocal = Vector3.Cross(dir, Vector3.up).normalized;
            bool usarY = m == 2 || m == 4;   // Vz, My  -> plano X-Z local (eje Y_barra)
            Vector3 eje = usarY ? yLocal : zLocal;

            // ------------------------------------------------------------------ //
            //  Escala LOCAL automatica del diagrama del elemento, SEPARADA de la
            //  escala global del edificio (P95/maximo, inmutable al cambiar viga).
            //  El pico local ocupa ~35% de la altura de referencia de cota 0.8;
            //  valores pequenos (p.ej. My=24,38 en un edificio con ±800,26) quedan
            //  SIEMPRE visibles sin depender de la escala global.
            // ------------------------------------------------------------------ //
            // ------------------------------------------------------------------ //
            //  Amplitud visual PROPORCIONAL a la longitud del FE (no fija 0,12 m):
            //  el pico ocupa ~22% de la longitud del elemento, recortado a un
            //  rango [0,65 m .. 3,5 m] para que la curva SIEMPRE salga del tubo
            //  (peralte tipico 0,30-0,50 m en vigas) sin volverse gigante en
            //  elementos largos. Valores pequenos (p.ej. My=24,38 sobre picos
            //  de ±800,26) siguen visibles por ser escala LOCAL del elemento.
            // ------------------------------------------------------------------ //
            float lenFE = Mathf.Max(e.Longitud, 1e-3f);
            // Amplitud visual REAL: pico = 25 % de la longitud del FE, recortado al
            // rango [0,8 m .. 5,0 m] para salir SIEMPRE del tubo (peralte tipico
            // 0,30-0,50 m, y 0,60x0,80 en columnas grandes) sin volverse gigante.
            bool esMuro = e.Tipo != null && e.Tipo.Contains("muro");
            float ampVisual = Mathf.Clamp(lenFE * 0.25f, 0.8f, 5f);
            if (esMuro) ampVisual = Mathf.Clamp(lenFE * 0.35f, 1.2f, 6f);
            float rama = Mathf.Max(Mathf.Abs(vi), Mathf.Abs(vj), 1e-6f);
            float factor = ampVisual / rama;   // pico local REAL = ampVisual

            // Muros: la barra FE vive EN el plano del panel (borde de la losa-muro), el
            // diagrama quedaria dentro del espesor. Se desplaza la LINEA BASE fuera del
            // panel (normal x (espesor/2 + margen 0.4), hacia el exterior del edificio).
            Vector3 offset = Vector3.zero;
            if (esMuro && NormalPanelMuro(e, out var nPanel, out var espesorMuro))
            {
                Vector3 mid = (w0 + w1) * 0.5f;
                if (Vector3.Dot(nPanel, mid - CentroEdificio(e.Building)) < 0f) nPanel = -nPanel;
                offset = nPanel * (espesorMuro * 0.5f + 0.4f);
            }
            Vector3 b0 = w0 + offset;
            Vector3 b1 = w1 + offset;

            // montantes i/j desde el eje de la barra (desplazado en muros) hasta el valor
            Vector3 pi = b0 + eje * (vi * factor);
            Vector3 pj = b1 + eje * (vj * factor);
            DrawLine(b0, pi, _colorMagnitud[MagnitudIdx], "DIAG_MONT_i");
            DrawLine(b1, pj, _colorMagnitud[MagnitudIdx], "DIAG_MONT_j");

            // curva interpolada i->j (lineal entre extremos; distribucion continua
            // real NO disponible en el JSON: se documenta como interpolacion FE)
            DrawLine(pi, pj, _colorMagnitud[MagnitudIdx], "DIAG_MAG_" + m);
        }

        private void DrawLine(Vector3 a, Vector3 b, Color c, string nombre)
        {
            var lab = Raiz();
            if (lab == null) return;
            var go = new GameObject(nombre);
            go.transform.SetParent(lab.transform, false);
            var lr = go.AddComponent<LineRenderer>();
            lr.positionCount = 2;
            lr.SetPosition(0, a);
            lr.SetPosition(1, b);
            lr.startWidth = lr.endWidth = 0.09f;
            lr.startColor = lr.endColor = c;
            // Shader UNLIT plano (NO Standard): Standard ignora los vertex colors del
            // LineRenderer y las lineas salian blancas/invisibles sobre la geometria.
            // Unlit/Color pinta SIEMPRE el color plano a plena luminosidad y sin luz.
            Shader sh = Shader.Find("Unlit/Color");
            if (sh == null) sh = Shader.Find("Sprites/Default");
            if (sh == null) sh = Shader.Find("Standard");
            var mat = new Material(sh);
            mat.color = c;
            lr.material = mat;
            _diagramas.Add(go);
        }
    }
}