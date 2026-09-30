using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using Unity.XR.CoreUtils;
using UnityEngine;
using UnityEngine.SpatialTracking;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
using LabViewer.AR;

namespace LabViewer
{
    public static class ARSceneGenerator
    {
        const string ScenePath = "Assets/Scenes/ARMain.unity";
        const string ReferenceName = "REF_EII_CP2_V_029";
        const string LibraryGuid = "3d96e05733a27544ea6586824e399576";
        const string BeamMaterialPath = "Assets/AR/Materials/Beam489.mat";
        const string BeamMaterialFolder = "Assets/AR/Materials";

        [MenuItem("AR/Generate ARMain Scene + Build Settings")]
        public static void GenerateFromMenu()
        {
            Generate();
        }

        public static void BatchGenerate()
        {
            try
            {
                Generate();
            }
            catch (Exception e)
            {
                Debug.LogError("[ARSceneGenerator] fallo: " + e);
                EditorApplication.Exit(1);
                return;
            }

            EditorApplication.Exit(0);
        }

        // Batch dedicado: solo crea (o reutiliza) el material versionado de la viga.
        // No regenera la escena. Referenciado serializadamente en ARMain.unity, el
        // material y su shader quedan incluidos en el build Android aunque "Standard"
        // no este en Always Included Shaders.
        [MenuItem("AR/Ensure Beam 489 Material")]
        public static void BatchEnsureBeamMaterial()
        {
            try
            {
                Material mat = EnsureBeamMaterial();
                if (mat == null)
                    throw new InvalidOperationException("No se pudo crear/ubicar el material Beam489");
                Debug.Log("[ARSceneGenerator] Beam489 material listo: " + AssetDatabase.GetAssetPath(mat));
            }
            catch (Exception e)
            {
                Debug.LogError("[ARSceneGenerator] fallo al asegurar material: " + e);
                EditorApplication.Exit(1);
                return;
            }

            EditorApplication.Exit(0);
        }

        // Material estructural (naranja/ambar) del tag 489. Solo existe un asset
        // versionado, asi que la referencia serializada de la escena viaja al APK.
        static Material EnsureBeamMaterial()
        {
            var existing = AssetDatabase.LoadAssetAtPath<Material>(BeamMaterialPath);
            if (existing != null) return existing;

            if (!AssetDatabase.IsValidFolder(BeamMaterialFolder))
                AssetDatabase.CreateFolder("Assets/AR", "Materials");

            Shader sh = Shader.Find("Standard");
            if (sh == null) sh = Shader.Find("Unlit/Color");
            if (sh == null)
                throw new InvalidOperationException("Sin shader Standard ni Unlit/Color en el editor");

            var mat = new Material(sh);
            mat.color = new Color(1f, 0.55f, 0.05f, 1f);
            if (mat.HasProperty("_Glossiness")) mat.SetFloat("_Glossiness", 0.4f);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", 0f);
            AssetDatabase.CreateAsset(mat, BeamMaterialPath);
            AssetDatabase.SaveAssets();
            return mat;
        }

        static void Generate()
        {
            var lib = FindReferenceLibrary();
            if (lib == null)
                throw new InvalidOperationException("No se encontro la XRReferenceImageLibrary REF_EII_CP2_V_029");

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            CreateARSession();
            var (camera, imageManager, anchorManager) = CreateXROrigin(lib);
            CreateARContent(camera, imageManager, anchorManager);
            CreateDirectionalLight();

            EditorSceneManager.SaveScene(scene, ScenePath);
            AddSceneToBuildSettings();
        }

        static XRReferenceImageLibrary FindReferenceLibrary()
        {
            string path = AssetDatabase.GUIDToAssetPath(LibraryGuid);
            var byGuid = (XRReferenceImageLibrary)AssetDatabase.LoadAssetAtPath(path, typeof(XRReferenceImageLibrary));
            if (byGuid != null)
                return byGuid;

            foreach (string assetGuid in AssetDatabase.FindAssets("t:XRReferenceImageLibrary"))
            {
                var candidate = (XRReferenceImageLibrary)AssetDatabase.LoadAssetAtPath(
                    AssetDatabase.GUIDToAssetPath(assetGuid), typeof(XRReferenceImageLibrary));
                if (candidate != null && candidate.count == 1 && candidate[0].name == ReferenceName)
                    return candidate;
            }

            return null;
        }

        static void CreateARSession()
        {
            ObjectFactory.CreateGameObject("AR Session", typeof(ARSession), typeof(ARInputManager));
        }

        static (Camera camera, ARTrackedImageManager imageManager, ARAnchorManager anchorManager) CreateXROrigin(XRReferenceImageLibrary lib)
        {
            var originGo = ObjectFactory.CreateGameObject("XR Origin", typeof(XROrigin));
            var offsetGo = ObjectFactory.CreateGameObject("Camera Offset");
            offsetGo.transform.SetParent(originGo.transform, false);

            var cameraGo = ObjectFactory.CreateGameObject(
                "Main Camera",
                typeof(Camera),
                typeof(AudioListener),
                typeof(ARCameraManager),
                typeof(ARCameraBackground),
                typeof(TrackedPoseDriver));
            cameraGo.tag = "MainCamera";
            cameraGo.transform.SetParent(offsetGo.transform, false);

            var trackedImageManager = originGo.AddComponent<ARTrackedImageManager>();
            var anchorManager = originGo.AddComponent<ARAnchorManager>();

            var camera = cameraGo.GetComponent<Camera>();
            camera.clearFlags = CameraClearFlags.Color;
            camera.backgroundColor = Color.black;
            camera.nearClipPlane = 0.1f;
            camera.farClipPlane = 100f;

            var origin = originGo.GetComponent<XROrigin>();
            origin.CameraFloorOffsetObject = offsetGo;
            origin.Camera = camera;

            var so = new SerializedObject(origin);
            SerializedProperty originBase = so.FindProperty("m_OriginBaseGameObject");
            if (originBase != null)
            {
                originBase.objectReferenceValue = originGo;
                so.ApplyModifiedPropertiesWithoutUndo();
            }

            trackedImageManager.referenceLibrary = lib;
            trackedImageManager.requestedMaxNumberOfMovingImages = 1;

            return (camera, trackedImageManager, anchorManager);
        }

        static void CreateARContent(Camera camera, ARTrackedImageManager imageManager, ARAnchorManager anchorManager)
        {
            var contentGo = ObjectFactory.CreateGameObject("AR Content");

            if (contentGo.GetComponent<ARImageAnchorController>() == null)
                ObjectFactory.AddComponent<ARImageAnchorController>(contentGo);

            var controller = contentGo.GetComponent<ARImageAnchorController>();
            var so = new SerializedObject(controller);
            so.FindProperty("m_ImageManager").objectReferenceValue = imageManager;
            so.FindProperty("m_AnchorManager").objectReferenceValue = anchorManager;
            so.FindProperty("m_ContentRoot").objectReferenceValue = contentGo.transform;
            so.FindProperty("m_ExpectedImageName").stringValue = ARImageAnchorController.DefaultExpectedImageName;
            so.ApplyModifiedPropertiesWithoutUndo();

            if (contentGo.GetComponent<ARBeam489Loader>() == null)
                ObjectFactory.AddComponent<ARBeam489Loader>(contentGo);

            var loader = contentGo.GetComponent<ARBeam489Loader>();
            var lso = new SerializedObject(loader);
            lso.FindProperty("m_Controller").objectReferenceValue = controller;
            lso.FindProperty("m_ContentRoot").objectReferenceValue = contentGo.transform;
            lso.FindProperty("m_ElementTag").intValue = 489;
            lso.FindProperty("m_Building").stringValue = "II";
            lso.FindProperty("m_ExpectedViewerId").stringValue = "EII_CP2_V_029";
            lso.FindProperty("m_ARScale").floatValue = 0.10f;
            lso.FindProperty("m_SectionM").vector2Value = new Vector2(0.30f, 0.80f);
            lso.FindProperty("m_BeamMaterial").objectReferenceValue = EnsureBeamMaterial();
            lso.ApplyModifiedPropertiesWithoutUndo();

            if (contentGo.GetComponent<ARResult489Label>() == null)
                ObjectFactory.AddComponent<ARResult489Label>(contentGo);

            var label = contentGo.GetComponent<ARResult489Label>();
            var nso = new SerializedObject(label);
            nso.FindProperty("m_Loader").objectReferenceValue = loader;
            nso.FindProperty("m_Controller").objectReferenceValue = controller;
            nso.FindProperty("m_ContentRoot").objectReferenceValue = contentGo.transform;
            nso.FindProperty("m_Camera").objectReferenceValue = camera;
            nso.ApplyModifiedPropertiesWithoutUndo();
        }

        static void CreateDirectionalLight()
        {
            var lightGo = ObjectFactory.CreateGameObject("Directional Light", typeof(Light));
            var light = lightGo.GetComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1f;
            light.shadows = LightShadows.Soft;
            lightGo.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
        }

        static void AddSceneToBuildSettings()
        {
            var scenes = EditorBuildSettings.scenes;
            bool mainPresent = false;
            bool arPresent = false;
            var list = new List<EditorBuildSettingsScene>();
            for (int i = 0; i < scenes.Length; i++)
            {
                var s = scenes[i];
                if (s.path == "Assets/Scenes/Main.unity" && s.enabled)
                {
                    mainPresent = true;
                    list.Add(s);
                }
                else if (s.path == ScenePath)
                {
                    arPresent = true;
                    list.Add(s);
                }
                else
                {
                    list.Add(s);
                }
            }

            if (!mainPresent)
            {
                list.Insert(0, new EditorBuildSettingsScene("Assets/Scenes/Main.unity", true));
                mainPresent = true;
            }

            if (!arPresent)
                list.Add(new EditorBuildSettingsScene(ScenePath, true));

            EditorBuildSettings.scenes = list.ToArray();
        }
    }
}