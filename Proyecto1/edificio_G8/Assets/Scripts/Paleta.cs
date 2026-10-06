using UnityEngine;

/// Paleta "Arrebol" del viewer y de la app AR (P1_G8).
/// Inspirada en el arrebol: el brillo rosado de la cordillera al atardecer.
/// Ciruela para los paneles, rosa arrebol como acento, menta para los encabezados
/// y un pasto verde bajo el edificio. Todos los colores del proyecto salen de aqui:
/// para retocar la paleta basta con cambiar estos valores (r, g, b, alfa entre 0 y 1).
/// Los estilos de la interfaz UI Toolkit estan en Resources/UI/viewer.uss.
public static class Paleta
{
    // ---- Interfaz (paneles, textos y acentos; UiTheme y ViewerUI los toman de aqui) ----
    public static readonly Color Panel = new Color(0.133f, 0.086f, 0.157f, 0.970f);
    public static readonly Color PanelSuave = new Color(0.133f, 0.086f, 0.157f, 0.950f);
    public static readonly Color Entrada = new Color(0.102f, 0.063f, 0.125f, 1.000f);
    public static readonly Color Acento = new Color(1.000f, 0.561f, 0.639f, 1.000f);
    public static readonly Color AcentoTenue = new Color(0.722f, 0.400f, 0.580f, 1.000f);
    public static readonly Color Acento2 = new Color(0.576f, 0.886f, 0.776f, 1.000f);
    public static readonly Color Texto = new Color(0.969f, 0.933f, 0.953f, 1.000f);
    public static readonly Color TextoTenue = new Color(0.722f, 0.647f, 0.749f, 1.000f);

    // ---- Diagramas: indigo lavanda = M+, N traccion, V+; rosa coral = M-, N compresion, V- ----
    public static readonly Color DiagPosRelleno = new Color(0.557f, 0.510f, 1.000f, 0.420f);
    public static readonly Color DiagNegRelleno = new Color(1.000f, 0.502f, 0.604f, 0.420f);
    public static readonly Color DiagPosLinea = new Color(0.478f, 0.443f, 1.000f, 1.000f);
    public static readonly Color DiagNegLinea = new Color(1.000f, 0.400f, 0.522f, 1.000f);
    public static readonly Color DeformadaOriginal = new Color(0.800f, 0.740f, 0.820f, 0.850f);
    public static readonly Color EtiquetaFondo = new Color(0.130f, 0.080f, 0.160f, 0.850f);

    // ---- Escala de la deformada |u| (atardecer: indigo -> violeta -> rosa -> durazno -> dorado) ----
    public static readonly Color Def0 = new Color(0.420f, 0.360f, 0.950f, 1.000f);
    public static readonly Color Def1 = new Color(0.660f, 0.300f, 0.850f, 1.000f);
    public static readonly Color Def2 = new Color(0.950f, 0.380f, 0.580f, 1.000f);
    public static readonly Color Def3 = new Color(1.000f, 0.600f, 0.350f, 1.000f);
    public static readonly Color Def4 = new Color(1.000f, 0.880f, 0.400f, 1.000f);

    // ---- Utilizacion (C = demanda/capacidad) y semaforo de armadura ----
    public static readonly Color UsoSinDato = new Color(0.720f, 0.680f, 0.720f, 1.000f);
    public static readonly Color UsoOk = new Color(0.180f, 0.740f, 0.550f, 1.000f);
    public static readonly Color UsoLimite = new Color(1.000f, 0.840f, 0.300f, 1.000f);
    public static readonly Color UsoFalla = new Color(0.860f, 0.130f, 0.330f, 1.000f);
    public static readonly Color SemaforoOk = new Color(0.580f, 0.900f, 0.740f, 1.000f);
    public static readonly Color SemaforoLimite = new Color(1.000f, 0.840f, 0.420f, 1.000f);
    public static readonly Color SemaforoFalla = new Color(1.000f, 0.500f, 0.580f, 1.000f);

    // ---- Modelo 3D ----
    public static readonly Color Viga = new Color(0.800f, 0.760f, 0.730f, 1.000f);
    public static readonly Color Pilar = new Color(0.460f, 0.330f, 0.520f, 1.000f);
    public static readonly Color Apoyo = new Color(0.950f, 0.420f, 0.550f, 1.000f);
    public static readonly Color Muro = new Color(0.930f, 0.740f, 0.790f, 0.550f);
    public static readonly Color Losa = new Color(0.580f, 0.890f, 0.780f, 0.220f);
    public static readonly Color Arriostre = new Color(0.290f, 0.400f, 0.480f, 1.000f);
    public static readonly Color Seleccion = new Color(1.000f, 0.270f, 0.620f, 1.000f);
    public static readonly Color Nodo = new Color(0.550f, 0.380f, 0.980f, 1.000f);
    public static readonly Color EtiquetaNodo = new Color(1.000f, 0.920f, 0.620f, 1.000f);
    public static readonly Color EtiquetaElemento = new Color(0.970f, 0.930f, 0.950f, 1.000f);
    public static readonly Color EtiquetaApoyo = new Color(1.000f, 0.800f, 0.860f, 1.000f);
    public static readonly Color EjeLocal = new Color(0.860f, 0.330f, 0.780f, 1.000f);
    public static readonly Color EjeX = new Color(0.910f, 0.270f, 0.360f, 1.000f);
    public static readonly Color EjeY = new Color(0.300f, 0.750f, 0.450f, 1.000f);
    public static readonly Color EjeZ = new Color(0.360f, 0.420f, 0.960f, 1.000f);

    // ---- Capas: grilla, diafragmas y cargas ----
    public static readonly Color Grilla = new Color(1.000f, 0.900f, 0.550f, 0.900f);
    public static readonly Color GrillaSecundaria = new Color(0.850f, 0.800f, 0.620f, 0.500f);
    public static readonly Color Diafragma = new Color(0.580f, 0.920f, 0.800f, 0.950f);
    public static readonly Color NodoMaestro = new Color(1.000f, 0.560f, 0.640f, 1.000f);
    public static readonly Color Carga = new Color(0.960f, 0.360f, 0.420f, 1.000f);
    public static readonly Color CargaGravedad = new Color(0.960f, 0.400f, 0.420f, 1.000f);
    public static readonly Color CargaEX = new Color(0.200f, 0.720f, 0.620f, 1.000f);
    public static readonly Color CargaEY = new Color(0.450f, 0.480f, 1.000f, 1.000f);
    public static readonly Color CargaMovil = new Color(0.960f, 0.360f, 0.420f, 1.000f);
    public static readonly Color CargaMovilRecorrido = new Color(1.000f, 0.840f, 0.450f, 1.000f);
    public static readonly Color CargaElemento = new Color(0.550f, 0.380f, 0.980f, 1.000f);
    public static readonly Color Eliminado = new Color(0.860f, 0.130f, 0.330f, 0.450f);

    // ---- Panel P-M ----
    public static readonly Color PMCapacidad = new Color(0.576f, 0.886f, 0.776f, 1.000f);
    public static readonly Color PMDemanda = new Color(1.000f, 0.450f, 0.500f, 1.000f);
    public static readonly Color PMOtros = new Color(0.700f, 0.580f, 1.000f, 1.000f);
    public static readonly Color PMGrilla = new Color(0.320f, 0.250f, 0.350f, 1.000f);
    public static readonly Color PMEje = new Color(0.660f, 0.590f, 0.690f, 1.000f);
    public static readonly Color PMFondo = new Color(0.120f, 0.075f, 0.145f, 0.920f);
    public static readonly Color PMEtiquetaFondo = new Color(0.120f, 0.075f, 0.145f, 0.880f);
    public static readonly Color PMCaja = new Color(0.150f, 0.095f, 0.180f, 0.950f);

    // ---- App AR (sobre la imagen de la camara: colores claros y saturados) ----
    public static readonly Color ARPilar = new Color(0.660f, 0.520f, 0.980f, 1.000f);
    public static readonly Color ARViga = new Color(0.950f, 0.900f, 0.930f, 1.000f);
    public static readonly Color ARArriostre = new Color(1.000f, 0.720f, 0.560f, 1.000f);
    public static readonly Color ARAncla = new Color(0.500f, 0.900f, 0.760f, 1.000f);
    public static readonly Color AREtiquetaDestacada = new Color(1.000f, 0.560f, 0.640f, 1.000f);
    public static readonly Color ARMarco = new Color(1.000f, 0.560f, 0.640f, 1.000f);
    public static readonly Color ARCuboPrueba = new Color(0.580f, 0.890f, 0.780f, 1.000f);
    public static readonly Color ARPlano = new Color(1.000f, 0.560f, 0.640f, 0.250f);

    // ---- Escena: cielo procedural y fondo de las capturas ----
    public static readonly Color CieloTinte = new Color(0.580f, 0.500f, 0.620f, 1.000f);
    public static readonly Color CieloSuelo = new Color(0.300f, 0.360f, 0.260f, 1.000f);
    public static readonly Color FondoCaptura = new Color(0.100f, 0.065f, 0.120f, 1.000f);

    // ---- Pasto (textura generada por codigo en StructureViewer.PastoTexture) ----
    public static readonly Color PastoOscuro = new Color(0.200f, 0.350f, 0.150f, 1.000f);
    public static readonly Color PastoClaro = new Color(0.340f, 0.510f, 0.210f, 1.000f);
    public static readonly Color PastoHoja = new Color(0.470f, 0.630f, 0.290f, 1.000f);
    public static readonly Color PastoSombra = new Color(0.130f, 0.250f, 0.100f, 1.000f);
    public static readonly Color PastoSeco = new Color(0.550f, 0.560f, 0.290f, 1.000f);

    /// Color de la deformada segun |u| normalizado (0 = minimo, 1 = maximo).
    public static Color Deformada(float x)
    {
        x = Mathf.Clamp01(x) * 4f;
        if (x < 1f) return Color.Lerp(Def0, Def1, x);
        if (x < 2f) return Color.Lerp(Def1, Def2, x - 1f);
        if (x < 3f) return Color.Lerp(Def2, Def3, x - 2f);
        return Color.Lerp(Def3, Def4, x - 3f);
    }
}
