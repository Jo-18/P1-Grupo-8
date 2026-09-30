using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using Unity.XR.CoreUtils;
using UnityEngine;
using UnityEngine.SpatialTracking;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

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
            var camera = CreateXROrigin(lib);
            CreateARContent();
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

        static Camera CreateXROrigin(XRReferenceImageLibrary lib)
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

            originGo.AddComponent<ARTrackedImageManager>();
            originGo.AddComponent<ARAnchorManager>();

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

            var trackedImageManager = originGo.GetComponent<ARTrackedImageManager>();
            trackedImageManager.referenceLibrary = lib;
            trackedImageManager.requestedMaxNumberOfMovingImages = 1;

            return camera;
        }

        static void CreateARContent()
        {
            ObjectFactory.CreateGameObject("AR Content");
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