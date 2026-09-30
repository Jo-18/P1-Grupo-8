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

        static void Generate()
        {
            var lib = FindReferenceLibrary();
            if (lib == null)
                throw new InvalidOperationException("No se encontro la XRReferenceImageLibrary REF_EII_CP2_V_029");

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            CreateARSession();
            var (_, imageManager, anchorManager) = CreateXROrigin(lib);
            CreateARContent(imageManager, anchorManager);
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

        static void CreateARContent(ARTrackedImageManager imageManager, ARAnchorManager anchorManager)
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
            lso.ApplyModifiedPropertiesWithoutUndo();
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