using System.Collections.Generic;
using System.Text;

/// <summary>
/// Ordena el texto de propiedades de un elemento segun las seis preguntas del curso:
/// donde esta, como esta apoyado, que lo carga, como se deforma, que fuerzas tiene y
/// cuanta capacidad tiene. No cambia los datos: solo agrupa las secciones bajo esas preguntas.
/// </summary>
public static class InfoPreguntas
{
    static readonly string[] Preguntas =
    {
        "1. ¿Dónde está?",
        "2. ¿Cómo está apoyado?",
        "3. ¿Qué lo carga?",
        "4. ¿Cómo se deforma?",
        "5. ¿Qué fuerzas tiene?",
        "6. ¿Cuánta capacidad tiene?",
        "Trazabilidad",
    };

    static int Categoria(string encabezado)
    {
        string h = encabezado.ToLowerInvariant();
        if (h.Contains("trazab")) return 6;
        if (h.Contains("restric") || h.Contains("apoyo") || h.Contains("conexi")) return 1;
        if (h.Contains("tribut") || h.Contains("carga") || h.Contains("peso")) return 2;
        if (h.Contains("despl") || h.Contains("deform") || h.Contains("deriva")) return 3;
        if (h.Contains("capacidad") || h.Contains("armadura") || h.Contains("seccion") || h.Contains("sección") || h.Contains("material")
            || h.Contains("p-m") || h.Contains("dcr") || h.Contains("utiliz")) return 5;
        if (h.Contains("fuerza") || h.Contains("esfuerz") || h.Contains("extremo")) return 4;
        return 0;   // ejes locales, ubicacion
    }

    public static string Organizar(string texto)
    {
        if (string.IsNullOrEmpty(texto)) return texto;
        var grupos = new List<string>[Preguntas.Length];
        for (int i = 0; i < grupos.Length; i++) grupos[i] = new List<string>();
        string titulo = null;
        int actual = 0;
        foreach (string raw in texto.Split('\n'))
        {
            string linea = raw.TrimEnd();
            string t = linea.Trim();
            if (t.Length == 0) continue;
            if (t.StartsWith("==="))
            {
                if (titulo == null) titulo = t; else grupos[actual].Add(t.Trim('=', ' '));
                continue;
            }
            if (t.StartsWith("---") && t.EndsWith("---"))
            {
                string h = t.Trim('-', ' ');
                actual = Categoria(h);
                grupos[actual].Add("· " + h);
                continue;
            }
            grupos[actual].Add(linea);
        }
        var sb = new StringBuilder();
        if (titulo != null) sb.Append(titulo).Append('\n');
        for (int i = 0; i < Preguntas.Length; i++)
        {
            if (grupos[i].Count == 0) continue;
            sb.Append("--- ").Append(Preguntas[i]).Append(" ---\n");
            foreach (string l in grupos[i]) sb.Append(l).Append('\n');
        }
        return sb.ToString();
    }
}
