using System;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

namespace LabViewer.AR
{
    [DisallowMultipleComponent]
    public sealed class ARImageAnchorController : MonoBehaviour
    {
        public const string DefaultExpectedImageName = "REF_EII_CP2_V_029";

        [SerializeField]
        ARTrackedImageManager m_ImageManager;

        [SerializeField]
        ARAnchorManager m_AnchorManager;

        [SerializeField]
        Transform m_ContentRoot;

        [SerializeField]
        string m_ExpectedImageName = DefaultExpectedImageName;

        [SerializeField]
        string m_DetectedImageName;

        [SerializeField]
        TrackingState m_TrackingState;

        [SerializeField]
        Pose m_LastDetectedPose;

        [SerializeField]
        ARAnchor m_Anchor;

        [SerializeField]
        bool m_AnchorPending;

        [SerializeField]
        string m_StatusMessage = "Sin reconocer";

        [NonSerialized]
        bool m_WasTracking;

        [NonSerialized]
        ARTrackedImage m_DetectedImage;

        public ARTrackedImageManager ImageManager => m_ImageManager;
        public ARAnchorManager AnchorManager => m_AnchorManager;
        public Transform ContentRoot => m_ContentRoot;
        public string ExpectedImageName => m_ExpectedImageName;

        public ARTrackedImage DetectedImage => m_DetectedImage;
        public bool ImageDetected => !string.IsNullOrEmpty(m_DetectedImageName);
        public string DetectedImageName => m_DetectedImageName;
        public TrackingState TrackingState => m_TrackingState;
        public Pose LastDetectedPose => m_LastDetectedPose;
        public ARAnchor Anchor => m_Anchor;
        public bool IsAnchorPending => m_AnchorPending;
        public string StatusMessage => m_StatusMessage;

        void OnEnable()
        {
            if (m_ImageManager != null)
                m_ImageManager.trackablesChanged.AddListener(OnTrackablesChanged);
        }

        void OnDisable()
        {
            if (m_ImageManager != null)
                m_ImageManager.trackablesChanged.RemoveListener(OnTrackablesChanged);
        }

        void OnTrackablesChanged(ARTrackablesChangedEventArgs<ARTrackedImage> args)
        {
            foreach (ARTrackedImage image in args.added)
                HandleImage(image);

            foreach (ARTrackedImage image in args.updated)
                HandleImage(image);
        }

        void HandleImage(ARTrackedImage image)
        {
            if (image == null || image.referenceImage == null)
                return;

            if (image.referenceImage.name != m_ExpectedImageName)
                return;

            image.transform.GetPositionAndRotation(out Vector3 position, out Quaternion rotation);
            m_DetectedImage = image;
            m_LastDetectedPose = new Pose(position, rotation);
            m_TrackingState = image.trackingState;
            m_DetectedImageName = image.referenceImage.name;

            if (image.trackingState != TrackingState.Tracking)
            {
                m_WasTracking = false;
                return;
            }

            if (!m_WasTracking)
            {
                m_WasTracking = true;
                m_StatusMessage = "Imagen detectada";
                Debug.Log("[AR489] Imagen detectada");
            }

            if (m_Anchor == null && !m_AnchorPending)
                CreateAnchorAsync(m_LastDetectedPose);
        }

        async void CreateAnchorAsync(Pose pose)
        {
            if (m_Anchor != null || m_AnchorPending)
                return;

            if (m_AnchorManager == null)
            {
                ReportAnchorError("ARAnchorManager no asignado");
                return;
            }

            m_AnchorPending = true;
            m_StatusMessage = "Creando anchor...";

            try
            {
                Result<ARAnchor> result = await m_AnchorManager.TryAddAnchorAsync(pose);
                if (result.status.IsSuccess() && result.value != null)
                {
                    m_Anchor = result.value;
                    m_AnchorPending = false;
                    AttachContentToAnchor();
                    m_StatusMessage = "Anchor creado";
                    Debug.Log("[AR489] Anchor creado");
                }
                else
                {
                    ReportAnchorError(result.status.statusCode.ToString());
                }
            }
            catch (Exception e)
            {
                ReportAnchorError(e.Message);
            }
        }

        void AttachContentToAnchor()
        {
            if (m_ContentRoot == null || m_Anchor == null)
                return;

            m_ContentRoot.SetParent(m_Anchor.transform, false);
            m_ContentRoot.localPosition = Vector3.zero;
            m_ContentRoot.localRotation = Quaternion.identity;
            m_ContentRoot.localScale = Vector3.one;
        }

        void ReportAnchorError(string detail)
        {
            m_AnchorPending = false;
            m_StatusMessage = "Error al crear anchor: " + detail;
            Debug.LogError("[AR489] Error al crear anchor: " + detail);
        }
    }
}