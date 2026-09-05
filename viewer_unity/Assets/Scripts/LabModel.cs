using System.Collections.Generic;
using UnityEngine;

namespace LabViewer
{
    /// <summary>Clasificacion de un elemento para filtros/colores/toggles.
    /// RefPendientes = registros cuyo unico respaldo es un rotulo/posicion de texto
    /// (p. ej. P.M.I. desde RLE-TEXTO-1, sin geometria fisica respaldada), mantenidos
    /// como marcadores de referencia en un filtro independiente de "Columnas".</summary>
    public enum ElemType { Losas, Vigas, Columnas, Muros, Diafragma, Abertura, Nodos, RefPendientes }

    /// <summary>Estado de validacion mostrado en el inspector.</summary>
    public enum ValState { Confirmado, Hipotetico, Pendiente }

    /// <summary>Referencia a un elemento dibujado (para seleccion + inspeccion).</summary>
    public class ElementRef : MonoBehaviour
    {
        public string Id;
        public string Building;   // "I" | "II"
        public string Level;      // "P2" | "EII_CP2" ...
        public ElemType Type;
        public string Seccion;    // nombre textual (puede ser null)
        public float SectionW;
        public float SectionH;
        public ValState State;
        // datos de origen
        public List<List<Vector3>> Aberturas;       // losas
        public float Espesor;
        public bool RecibeLosa;
        public List<string> ApoyosValidos;
        public string TipoTransferencia;
        public string Nota;
        public string Grid;

        // --- para mostrar regiones tributarias (vigas II/I) ---
        public bool HasTributary;               // true si hay datos de area/carga para esta viga
        public double TribAreaM2;
        public double TribCargaKN;
        public string TribCase;
        public string TribSource;
        public List<string> TribSourceLosas;    // ids de losas origen
        public List<TribRegion> TribRegions;    // regiones (celdas) reales del reparto geometrico

        // geometria util (vigas/muros: extremos; columnas: posicion)
        public Vector3 P0, P1;

        public override string ToString() => $"{Building}.{Level}.{Type}.{Id}";
    }

    /// <summary>Region tributaria (celda de la malla del reparto geometrico real)
    /// asignada a un receptor. `Points` son vertices del contorno en coordenadas
    /// Unity locales (X,Y,Z)=(u,cota,v) de la LOSA de origen.</summary>
    public class TribRegion
    {
        public string Losa;         // id de la losa de origen
        public double AreaM2;
        public double CargaKN;
        public float Cota;          // cota de la losa (u, cota, v)
        public List<Vector3> Points = new List<Vector3>();
    }

    /// <summary>Datos tributarios de una viga receptora (carga G del lab).</summary>
    public class TribData
    {
        public double Area;
        public double Carga;
        public string Case;
        public string Source;
        public List<string> Losas;
        public TribData(double area, double carga, string caso, string source, List<string> losas)
        {
            Area = area; Carga = carga; Case = caso; Source = source; Losas = losas ?? new List<string>();
        }
    }

    /// <summary>Mantiene el estado del lab cargado y la lista de elementos.</summary>
    public class LabModel
    {
        public string Version;
        public List<ElementRef> Elements = new List<ElementRef>();
        public Dictionary<string, List<string>> FileManifest = new Dictionary<string, List<string>>();
        public int[] EiCounts;
        public int[] EiiCounts;
        public Dictionary<string, Vector3> Placement = new Dictionary<string, Vector3>(); // building -> position
        public Dictionary<string, Quaternion> PlacementRot = new Dictionary<string, Quaternion>();
        public bool GlobalPlacementProvisional;
        public string PlacementDatoNecesario;
        public bool NoUnionEstructural;
        public string JuntaEstado;      // p.ej. "por_correlacionar"
        public string JuntaId;          // p.ej. "JD_EI_EII_10CM"
        public string JuntaAnchoM;      // texto con el ancho declarado (m)
        public string JuntaNotaEI;

        public string EiResultNote;
        public string EiResultSource;
        public string EiiStateNote;

        public List<ElementRef> ById(string id)
        {
            var r = new List<ElementRef>();
            foreach (var e in Elements) if (e.Id == id) r.Add(e);
            return r;
        }
    }
}
