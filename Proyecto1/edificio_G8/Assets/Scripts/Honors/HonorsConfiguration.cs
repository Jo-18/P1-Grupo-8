using UnityEngine;
/// Independent switches. Absence of this component preserves the legacy application.
public sealed class HonorsConfiguration : MonoBehaviour {
    public bool H5CapacityComparison, H2ProfilesAndQA, H3SpatialDiagrams;
    public static HonorsConfiguration Current => Object.FindAnyObjectByType<HonorsConfiguration>();
    public static bool H5 => Current!=null && Current.H5CapacityComparison;
    public static bool H2 => Current!=null && Current.H2ProfilesAndQA;
    public static bool H3 => Current!=null && Current.H3SpatialDiagrams;
}
