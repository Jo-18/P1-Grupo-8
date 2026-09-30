using UnityEngine;

namespace LabViewer.AR
{
    [DisallowMultipleComponent]
    public sealed class ARElementIdentity : MonoBehaviour
    {
        [SerializeField] int m_ElementTag;
        [SerializeField] string m_ViewerId;
        [SerializeField] string m_Building;
        [SerializeField] string m_ElementType;
        [SerializeField] string m_Section;

        public int ElementTag => m_ElementTag;
        public string ViewerId => m_ViewerId;
        public string Building => m_Building;
        public string ElementType => m_ElementType;
        public string Section => m_Section;

        public void Init(int elementTag, string viewerId, string building, string elementType, string section)
        {
            m_ElementTag = elementTag;
            m_ViewerId = viewerId ?? "";
            m_Building = building ?? "";
            m_ElementType = elementType ?? "";
            m_Section = section ?? "";
        }
    }
}