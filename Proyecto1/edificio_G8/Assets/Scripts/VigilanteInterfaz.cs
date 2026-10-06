using UnityEngine;

/// <summary>
/// Agrega la interfaz completa (ViewerUI) en cuanto el visor tiene datos, aunque la
/// construccion de la escena haya fallado antes de hacerlo. Despues se desactiva.
/// </summary>
public class VigilanteInterfaz : MonoBehaviour
{
    private float limite;

    private void Start()
    {
        limite = Time.unscaledTime + 30f;
    }

    private void Update()
    {
        if (GetComponent<ViewerUI>() != null)
        {
            enabled = false;
            return;
        }
        StructureViewer v = GetComponent<StructureViewer>();
        if (Application.isPlaying && v != null && v.Data != null)
        {
            gameObject.AddComponent<ViewerUI>();
            enabled = false;
        }
        else if (Time.unscaledTime > limite)
        {
            enabled = false;
        }
    }
}
