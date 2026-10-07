using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;

/// <summary>
/// Build movil inicial (Android) del viewer.
/// Menu: MCOC / Build Android (APK)
/// Consola: Unity.exe -batchmode -quit -projectPath edificio_G8 -executeMethod BuildAndroid.Build
/// Salida: edificio_G8/Builds/Android/P1G8_Viewer.apk
/// </summary>
public static class BuildAndroid
{
    private const string Scene = "Assets/Scenes/StructureViewerScene.unity";
    private const string OutputDir = "Builds/Android";
    private const string ApkName = "P1G8_Viewer.apk";

    [MenuItem("MCOC/Build Android (APK)")]
    public static void BuildFromMenu()
    {
        Build();
    }

    public static void Configure()
    {
        PlayerSettings.companyName = "UANDES MCOC Grupo 8";
        PlayerSettings.productName = "P1_G8 Viewer";
        PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android, "cl.uandes.mcoc.p1g8");
        PlayerSettings.bundleVersion = "0.5.0";
        PlayerSettings.Android.bundleVersionCode = 5;

        // Telefono de referencia: Samsung Galaxy A54 (Android 13, ARM64, Vulkan 1.1 / GLES 3.2)
        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel29;
        PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevelAuto;
        PlayerSettings.SetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.Vulkan, GraphicsDeviceType.OpenGLES3 });

        IncludeRuntimeShaders();

        // El panel del viewer esta pensado para pantalla horizontal
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
        PlayerSettings.allowedAutorotateToPortrait = false;
        PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
        PlayerSettings.allowedAutorotateToLandscapeLeft = true;
        PlayerSettings.allowedAutorotateToLandscapeRight = true;
    }

    /// Los materiales del viewer se crean en tiempo de ejecucion con Shader.Find:
    /// esos shaders deben ir en "Always Included Shaders" o Unity los elimina del build.
    private static void IncludeRuntimeShaders()
    {
        string[] names = { "Custom/AlwaysOnTopLine", "Standard", "Unlit/Color", "Sprites/Default" };
        var graphics = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>("ProjectSettings/GraphicsSettings.asset");
        var so = new SerializedObject(graphics);
        SerializedProperty list = so.FindProperty("m_AlwaysIncludedShaders");
        foreach (string name in names)
        {
            Shader shader = Shader.Find(name);
            if (shader == null)
            {
                Debug.LogWarning("[BuildAndroid] No se encontro el shader " + name);
                continue;
            }
            bool present = false;
            for (int i = 0; i < list.arraySize; i++)
            {
                if (list.GetArrayElementAtIndex(i).objectReferenceValue == shader) { present = true; break; }
            }
            if (!present)
            {
                list.InsertArrayElementAtIndex(list.arraySize);
                list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = shader;
                Debug.Log("[BuildAndroid] Shader incluido en el build: " + name);
            }
        }
        so.ApplyModifiedProperties();
        AssetDatabase.SaveAssets();
    }

    [MenuItem("MCOC/Build Android de diagnostico (APK)")]
    public static void BuildDevelopmentFromMenu()
    {
        BuildDevelopment();
    }

    /// Build de desarrollo: muestra en pantalla la consola de diagnostico (DebugOverlay).
    public static void BuildDevelopment()
    {
        Build(true);
    }

    public static void Build()
    {
        Build(false);
    }

    // ------------------------------------------------------------------
    // Semana 6: APK de AR (ARScene, ARCore). Se instala aparte del viewer.
    // ------------------------------------------------------------------
    [MenuItem("MCOC/AR/Build Android AR (APK)")]
    public static void BuildARFromMenu()
    {
        BuildAR();
    }

    public static void BuildAR()
    {
        if(Application.unityVersion!="6000.6.0f1")throw new System.InvalidOperationException("Usar Unity 6000.6.0f1 para este proyecto");
        if(!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Android,BuildTarget.Android))throw new System.InvalidOperationException("Falta Android Build Support; instalar desde Unity Hub con autorización del usuario");
        using(var previous=new ARBuildSettingsSnapshot()) {
        try {
        Configure();
        ARInputSettings.Set(true,false);
        var arcore=UnityEditor.XR.ARCore.ARCoreSettings.GetOrCreateSettings();
        arcore.requirement=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Required;
        arcore.depth=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Optional;
        PlayerSettings.productName = "MCOC AR Inspector";
        PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android, "cl.uandes.mcoc.p1g8.ar.inspector");
        PlayerSettings.allowedAutorotateToPortrait=true;
        PlayerSettings.allowedAutorotateToPortraitUpsideDown=false;
        // ARCore: OpenGLES3 es la API grafica mas compatible
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
        // El renderizado multihilo provoca GL_INVALID_ENUM con el fondo de camara de ARCore
        PlayerSettings.SetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android, false);
        // Con GameActivity ARCore recibia ~7 muestras/s de IMU (necesita ~200): se usa la Activity clasica
        PlayerSettings.Android.applicationEntry = AndroidApplicationEntry.Activity;
        ARSetup.ConfigureXR(true);
        ARSetup.CreateARScene();   // la escena se genera por codigo: siempre al dia

        Directory.CreateDirectory(OutputDir);
        File.WriteAllText(Path.Combine(OutputDir,"AR_BuildConfiguration.json"),JsonUtility.ToJson(new ARBuildConfiguration {
            unity=Application.unityVersion,
            identifier=PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android),
            backend=PlayerSettings.GetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Android).ToString(),
            architectures=PlayerSettings.Android.targetArchitectures.ToString(),
            minApi=(int)PlayerSettings.Android.minSdkVersion,
            graphics=string.Join(",",PlayerSettings.GetGraphicsAPIs(BuildTarget.Android)),
            activity=PlayerSettings.Android.applicationEntry.ToString(),
            orientation=PlayerSettings.defaultInterfaceOrientation.ToString(),
            portrait=PlayerSettings.allowedAutorotateToPortrait,
            landscapeLeft=PlayerSettings.allowedAutorotateToLandscapeLeft,
            landscapeRight=PlayerSettings.allowedAutorotateToLandscapeRight,
            mobileMultithreaded=PlayerSettings.GetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android),
            scene=ARSetup.ScenePath,
            xrInit=UnityEditor.XR.Management.XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(BuildTargetGroup.Android).InitManagerOnStart
            ,inputHandling="Input System (New)"
        },true));
        var options = new BuildPlayerOptions
        {
            scenes = new[] { ARSetup.ScenePath },
            locationPathName = Path.Combine(OutputDir, "P1G8_AR_Inspector.apk"),
            target = BuildTarget.Android,
            targetGroup = BuildTargetGroup.Android,
            options = BuildOptions.Development   // consola de errores en pantalla durante las pruebas
        };
        EditorUserBuildSettings.buildAppBundle = false;
        BuildReport report = BuildPipeline.BuildPlayer(options);
        BuildSummary summary = report.summary;
        Debug.Log($"[BuildAndroid] AR {summary.result} | {summary.outputPath} | {summary.totalSize / (1024f * 1024f):0.0} MB | " +
                  $"{summary.totalErrors} errores, {summary.totalWarnings} avisos, {summary.totalTime}");
        WriteEvidence(report);
        if(summary.result!=BuildResult.Succeeded)throw new System.InvalidOperationException("Build Android falló; revisar AR_BuildReport.json y log del editor");
        } finally { AssetDatabase.SaveAssets(); }
        }
    }

    [MenuItem("MCOC/Honors/Build Android Honors independiente")]
    public static void BuildARHonors(){
        if(Application.unityVersion!="6000.6.0f1")throw new System.InvalidOperationException("Unity exacto requerido");
        if(!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Android,BuildTarget.Android))throw new System.InvalidOperationException("Android Build Support requerido");
        Directory.CreateDirectory(OutputDir);
        using(var previous=new ARBuildSettingsSnapshot()){
            try{
                Configure();ARInputSettings.Set(true,false);var arcore=UnityEditor.XR.ARCore.ARCoreSettings.GetOrCreateSettings();
                arcore.requirement=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Required;arcore.depth=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Optional;EditorUtility.SetDirty(arcore);
                PlayerSettings.productName="MCOC P1 G8 Honors";PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android,"cl.uandes.mcoc.p1g8.ar.honors");PlayerSettings.Android.bundleVersionCode=106;
                PlayerSettings.defaultInterfaceOrientation=UIOrientation.AutoRotation;PlayerSettings.allowedAutorotateToPortrait=true;PlayerSettings.allowedAutorotateToPortraitUpsideDown=false;PlayerSettings.allowedAutorotateToLandscapeLeft=true;PlayerSettings.allowedAutorotateToLandscapeRight=true;
                PlayerSettings.SetGraphicsAPIs(BuildTarget.Android,new[]{GraphicsDeviceType.OpenGLES3});PlayerSettings.SetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android,false);PlayerSettings.Android.applicationEntry=AndroidApplicationEntry.Activity;
                ARSetup.ConfigureXR(true);HonorsSetup.Prepare();AssetDatabase.SaveAssets();
                File.WriteAllText(Path.Combine(OutputDir,"Honors_BuildConfiguration.json"),JsonUtility.ToJson(new ARBuildConfiguration{unity=Application.unityVersion,identifier=PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android),backend=PlayerSettings.GetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Android).ToString(),architectures=PlayerSettings.Android.targetArchitectures.ToString(),minApi=(int)PlayerSettings.Android.minSdkVersion,graphics=string.Join(",",PlayerSettings.GetGraphicsAPIs(BuildTarget.Android)),activity=PlayerSettings.Android.applicationEntry.ToString(),orientation=PlayerSettings.defaultInterfaceOrientation.ToString(),portrait=PlayerSettings.allowedAutorotateToPortrait,landscapeLeft=PlayerSettings.allowedAutorotateToLandscapeLeft,landscapeRight=PlayerSettings.allowedAutorotateToLandscapeRight,mobileMultithreaded=PlayerSettings.GetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android),scene=HonorsSetup.ARScene,xrInit=true,inputHandling="Input System"},true));
                EditorUserBuildSettings.buildAppBundle=false;
                var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{HonorsSetup.ARScene},locationPathName=Path.Combine(OutputDir,"P1G8_Honors_H5_H2.apk"),target=BuildTarget.Android,targetGroup=BuildTargetGroup.Android,options=BuildOptions.Development});
                WriteEvidence(report);File.Copy(Path.Combine(OutputDir,"AR_BuildReport.json"),Path.Combine(OutputDir,"Honors_BuildReport.json"),true);
                if(report.summary.result!=BuildResult.Succeeded)throw new System.InvalidOperationException("Build Honors falló: "+report.summary.result);
            }finally{AssetDatabase.SaveAssets();}
        }
        File.Copy(Path.Combine(OutputDir,"AR_SettingsRestoration.json"),Path.Combine(OutputDir,"Honors_SettingsRestoration.json"),true);
    }

    public static void BuildARFlagsOffGate(){
        if(Application.unityVersion!="6000.6.0f1")throw new System.InvalidOperationException("Unity exacto requerido");
        Directory.CreateDirectory(OutputDir);
        using(var previous=new ARBuildSettingsSnapshot()){
            Configure();ARInputSettings.Set(true,false);var settings=UnityEditor.XR.ARCore.ARCoreSettings.GetOrCreateSettings();settings.requirement=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Required;settings.depth=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Optional;EditorUtility.SetDirty(settings);
            PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android,"cl.uandes.mcoc.p1g8.ar.honors.flagsoff");PlayerSettings.productName="MCOC AR flags off gate";
            PlayerSettings.defaultInterfaceOrientation=UIOrientation.AutoRotation;PlayerSettings.allowedAutorotateToPortrait=true;PlayerSettings.allowedAutorotateToPortraitUpsideDown=false;PlayerSettings.allowedAutorotateToLandscapeLeft=true;PlayerSettings.allowedAutorotateToLandscapeRight=true;
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android,new[]{GraphicsDeviceType.OpenGLES3});PlayerSettings.SetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android,false);PlayerSettings.Android.applicationEntry=AndroidApplicationEntry.Activity;ARSetup.ConfigureXR(true);AssetDatabase.SaveAssets();EditorUserBuildSettings.buildAppBundle=false;
            // The legacy scene has no HonorsConfiguration. Do not regenerate its scene/library.
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ARSetup.ScenePath},locationPathName=Path.Combine(OutputDir,"P1G8_AR_FlagsOff_Gate.apk"),target=BuildTarget.Android,targetGroup=BuildTargetGroup.Android,options=BuildOptions.Development});WriteEvidence(report);File.Copy(Path.Combine(OutputDir,"AR_BuildReport.json"),Path.Combine(OutputDir,"FlagsOff_BuildReport.json"),true);
            if(report.summary.result!=BuildResult.Succeeded)throw new System.InvalidOperationException("Legacy flags-off gate falló");
        }
        File.Copy(Path.Combine(OutputDir,"AR_SettingsRestoration.json"),Path.Combine(OutputDir,"FlagsOff_SettingsRestoration.json"),true);
    }

    public static void BuildARHonorsFix01()=>BuildFix01(false);
    public static void BuildARFlagsOffFix01()=>BuildFix01(true);
    static void BuildFix01(bool legacy){
        if(Application.unityVersion!="6000.6.0f1")throw new System.InvalidOperationException("Unity exacto requerido");
        const string fixDir="Builds/Android/fix01";Directory.CreateDirectory(fixDir);
        string prefix=legacy?"FlagsOff_fix01":"Honors_fix01";
        string output=Path.Combine(fixDir,legacy?"P1G8_AR_FlagsOff_fix01.apk":"P1G8_Honors_H5_H2_fix01.apk");
        if(File.Exists(output))throw new System.InvalidOperationException("APK existente: conservarla antes de otro ensayo");
        using(var previous=new ARBuildSettingsSnapshot()){
            Configure();ARInputSettings.Set(true,false);var settings=UnityEditor.XR.ARCore.ARCoreSettings.GetOrCreateSettings();
            settings.requirement=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Required;settings.depth=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Optional;EditorUtility.SetDirty(settings);
            PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android,legacy?"cl.uandes.mcoc.p1g8.ar.honors.flagsoff":"cl.uandes.mcoc.p1g8.ar.honors");
            PlayerSettings.productName=legacy?"MCOC flags off fix01":"MCOC Honors fix01";PlayerSettings.bundleVersion="0.5.1";PlayerSettings.Android.bundleVersionCode=107;
            PlayerSettings.defaultInterfaceOrientation=UIOrientation.AutoRotation;PlayerSettings.allowedAutorotateToPortrait=true;PlayerSettings.allowedAutorotateToPortraitUpsideDown=false;PlayerSettings.allowedAutorotateToLandscapeLeft=true;PlayerSettings.allowedAutorotateToLandscapeRight=true;
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android,new[]{GraphicsDeviceType.OpenGLES3});PlayerSettings.SetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android,false);PlayerSettings.Android.applicationEntry=AndroidApplicationEntry.Activity;
            ARSetup.ConfigureXR(true);ApkFixSetup.Prepare();if(!legacy)HonorsSetup.Prepare();AssetDatabase.SaveAssets();EditorUserBuildSettings.buildAppBundle=false;
            File.WriteAllText(Path.Combine(fixDir,prefix+"_BuildConfiguration.json"),"{\"unity\":\"6000.6.0f1\",\"version\":\"0.5.1\",\"buildNumber\":107,\"developmentBuild\":false,\"identifier\":\""+PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android)+"\",\"minApi\":29,\"architectures\":\"ARM64\",\"backend\":\"IL2CPP\",\"graphics\":\"OpenGLES3\",\"H5\":"+(!legacy).ToString().ToLowerInvariant()+",\"H2\":"+(!legacy).ToString().ToLowerInvariant()+",\"H3\":false}");
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{legacy?ARSetup.ScenePath:HonorsSetup.ARScene},locationPathName=output,target=BuildTarget.Android,targetGroup=BuildTargetGroup.Android,options=BuildOptions.None});
            WriteEvidence(report);File.Copy(Path.Combine(OutputDir,"AR_BuildReport.json"),Path.Combine(fixDir,prefix+"_BuildReport.json"),false);
            if(report.summary.result!=BuildResult.Succeeded)throw new System.InvalidOperationException("fix01 build failed: "+report.summary.result);
        }
        File.Copy(Path.Combine(OutputDir,"AR_SettingsRestoration.json"),Path.Combine(fixDir,prefix+"_SettingsRestoration.json"),false);
    }

    public static void BuildARHonorsFix02()=>BuildFix02(false);
    public static void BuildARFlagsOffFix02()=>BuildFix02(true);
    static void BuildFix02(bool legacy){
        if(Application.unityVersion!="6000.6.0f1")throw new System.InvalidOperationException("Unity exacto requerido");
        const string fixDir="Builds/Android/fix02";Directory.CreateDirectory(fixDir);
        string prefix=legacy?"FlagsOff_fix02":"Honors_fix02";
        string output=Path.Combine(fixDir,legacy?"P1G8_AR_FlagsOff_fix02.apk":"P1G8_Honors_H5_H2_H3_fix02.apk");
        if(File.Exists(output))throw new System.InvalidOperationException("APK existente: conservarla antes de otro ensayo");
        using(var previous=new ARBuildSettingsSnapshot()){
            Configure();ARInputSettings.Set(true,false);var settings=UnityEditor.XR.ARCore.ARCoreSettings.GetOrCreateSettings();
            settings.requirement=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Required;settings.depth=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Optional;EditorUtility.SetDirty(settings);
            PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android,legacy?"cl.uandes.mcoc.p1g8.ar.honors.flagsoff":"cl.uandes.mcoc.p1g8.ar.honors");
            PlayerSettings.productName=legacy?"MCOC flags off fix02":"MCOC Honors fix02";PlayerSettings.bundleVersion="0.5.2";PlayerSettings.Android.bundleVersionCode=108;
            PlayerSettings.defaultInterfaceOrientation=UIOrientation.AutoRotation;PlayerSettings.allowedAutorotateToPortrait=true;PlayerSettings.allowedAutorotateToPortraitUpsideDown=false;PlayerSettings.allowedAutorotateToLandscapeLeft=true;PlayerSettings.allowedAutorotateToLandscapeRight=true;
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android,new[]{GraphicsDeviceType.OpenGLES3});PlayerSettings.SetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android,false);PlayerSettings.Android.applicationEntry=AndroidApplicationEntry.Activity;
            ARSetup.ConfigureXR(true);ApkFixSetup.Prepare();if(!legacy)HonorsSetup.Prepare();AssetDatabase.SaveAssets();EditorUserBuildSettings.buildAppBundle=false;
            File.WriteAllText(Path.Combine(fixDir,prefix+"_BuildConfiguration.json"),"{\"unity\":\"6000.6.0f1\",\"version\":\"0.5.2\",\"buildNumber\":108,\"developmentBuild\":false,\"identifier\":\""+PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android)+"\",\"minApi\":29,\"architectures\":\"ARM64\",\"backend\":\"IL2CPP\",\"graphics\":\"OpenGLES3\",\"H5\":"+(!legacy).ToString().ToLowerInvariant()+",\"H2\":"+(!legacy).ToString().ToLowerInvariant()+",\"H3\":false,\"H3Activation\":\"Manual My/Vz in inspector\",\"VisualizationDefault\":\"Maqueta100\",\"VisualScale\":0.01}");
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{legacy?ARSetup.ScenePath:HonorsSetup.ARScene},locationPathName=output,target=BuildTarget.Android,targetGroup=BuildTargetGroup.Android,options=BuildOptions.None});
            WriteEvidence(report);File.Copy(Path.Combine(OutputDir,"AR_BuildReport.json"),Path.Combine(fixDir,prefix+"_BuildReport.json"),false);
            if(report.summary.result!=BuildResult.Succeeded)throw new System.InvalidOperationException("fix02 build failed: "+report.summary.result);
        }
        File.Copy(Path.Combine(OutputDir,"AR_SettingsRestoration.json"),Path.Combine(fixDir,prefix+"_SettingsRestoration.json"),false);
    }

    public static void BuildARHonorsFix03()=>BuildFix03(false);
    public static void BuildARFlagsOffFix03()=>BuildFix03(true);
    static void BuildFix03(bool legacy){
        if(Application.unityVersion!="6000.6.0f1")throw new System.InvalidOperationException("Unity exacto requerido");
        const string fixDir="Builds/Android/fix03";Directory.CreateDirectory(fixDir);
        string prefix=legacy?"FlagsOff_fix03":"Honors_fix03";
        string output=Path.Combine(fixDir,legacy?"P1G8_AR_FlagsOff_fix03.apk":"P1G8_Honors_H5_H2_H3_fix03.apk");
        if(File.Exists(output))throw new System.InvalidOperationException("APK existente: conservarla antes de otro ensayo");
        using(var previous=new ARBuildSettingsSnapshot()){
            Configure();ARInputSettings.Set(true,false);var settings=UnityEditor.XR.ARCore.ARCoreSettings.GetOrCreateSettings();
            settings.requirement=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Required;settings.depth=UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Optional;EditorUtility.SetDirty(settings);
            PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android,legacy?"cl.uandes.mcoc.p1g8.ar.honors.flagsoff":"cl.uandes.mcoc.p1g8.ar.honors");
            PlayerSettings.productName=legacy?"MCOC flags off fix03":"MCOC Honors fix03";PlayerSettings.bundleVersion="0.5.3";PlayerSettings.Android.bundleVersionCode=109;
            PlayerSettings.defaultInterfaceOrientation=UIOrientation.AutoRotation;PlayerSettings.allowedAutorotateToPortrait=true;PlayerSettings.allowedAutorotateToPortraitUpsideDown=false;PlayerSettings.allowedAutorotateToLandscapeLeft=true;PlayerSettings.allowedAutorotateToLandscapeRight=true;
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android,new[]{GraphicsDeviceType.OpenGLES3});PlayerSettings.SetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android,false);PlayerSettings.Android.applicationEntry=AndroidApplicationEntry.Activity;
            ARSetup.ConfigureXR(true);ApkFixSetup.Prepare();if(!legacy)HonorsSetup.Prepare();AssetDatabase.SaveAssets();EditorUserBuildSettings.buildAppBundle=false;
            File.WriteAllText(Path.Combine(fixDir,prefix+"_BuildConfiguration.json"),"{\"unity\":\"6000.6.0f1\",\"version\":\"0.5.3\",\"buildNumber\":109,\"developmentBuild\":false,\"identifier\":\""+PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android)+"\",\"minApi\":29,\"architectures\":\"ARM64\",\"backend\":\"IL2CPP\",\"graphics\":\"OpenGLES3\",\"H5\":"+(!legacy).ToString().ToLowerInvariant()+",\"H2\":"+(!legacy).ToString().ToLowerInvariant()+",\"H3\":false,\"H3Activation\":\"Manual My/Vz in inspector\",\"VisualizationDefault\":\"Maqueta100\",\"VisualScale\":0.01}");
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{legacy?ARSetup.ScenePath:HonorsSetup.ARScene},locationPathName=output,target=BuildTarget.Android,targetGroup=BuildTargetGroup.Android,options=BuildOptions.None});
            WriteEvidence(report);File.Copy(Path.Combine(OutputDir,"AR_BuildReport.json"),Path.Combine(fixDir,prefix+"_BuildReport.json"),false);
            if(report.summary.result!=BuildResult.Succeeded)throw new System.InvalidOperationException("fix03 build failed: "+report.summary.result);
        }
        File.Copy(Path.Combine(OutputDir,"AR_SettingsRestoration.json"),Path.Combine(fixDir,prefix+"_SettingsRestoration.json"),false);
    }

    public static void RefreshLatestReport()
    {
        BuildReport report=BuildReport.GetLatestReport();
        if(report==null || !report.summary.outputPath.EndsWith("P1G8_AR_Inspector.apk"))
            throw new System.InvalidOperationException("El último BuildReport no corresponde a la APK AR");
        WriteEvidence(report);
    }
    private static void WriteEvidence(BuildReport report)
    {
        var summary=report.summary;
        string buildHash="";
        ulong apkBytes=0;
        if(summary.result==BuildResult.Succeeded && File.Exists(summary.outputPath)) {
            apkBytes=(ulong)new FileInfo(summary.outputPath).Length;
            using(var sha=System.Security.Cryptography.SHA256.Create())buildHash=System.BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(summary.outputPath))).Replace("-","").ToLowerInvariant();
        }
        var warnings=new System.Collections.Generic.List<string>();
        foreach(var step in report.steps)foreach(var message in step.messages)
            if(message.type==LogType.Warning)warnings.Add(message.content);
        File.WriteAllText(Path.Combine(OutputDir,"AR_BuildReport.json"),JsonUtility.ToJson(new ARBuildEvidence{unity=Application.unityVersion,result=summary.result.ToString(),apk=summary.outputPath,sha256=buildHash,errors=summary.totalErrors,warnings=summary.totalWarnings,warningDetails=warnings.ToArray(),seconds=summary.totalTime.TotalSeconds,bytes=apkBytes,totalBuildBytes=summary.totalSize},true));
    }
    [System.Serializable] private class ARBuildEvidence {public string unity,result,apk,sha256;public string[] warningDetails;public int errors,warnings;public double seconds;public ulong bytes,totalBuildBytes;}
    [System.Serializable] private class ARBuildConfiguration {public string unity,identifier,backend,architectures,graphics,activity,orientation,scene,inputHandling;public int minApi;public bool portrait,landscapeLeft,landscapeRight,mobileMultithreaded,xrInit;}
    [System.Serializable] private class ARRestorationEvidence {public bool passed,player,input,xr,graphics,arcore;public string unity;}
    private static class ARInputSettings {
        // Use the installed Input System editor helper, which handles Unity 6
        // global/active BuildProfile settings without its reimport-loop issue.
        static readonly System.Type Helper=System.Type.GetType("UnityEngine.InputSystem.Editor.EditorPlayerSettingHelpers, Unity.InputSystem",true);
        static System.Reflection.PropertyInfo Property(string name)=>Helper.GetProperty(name,System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.Static);
        public static bool New => (bool)Property("newSystemBackendsEnabled").GetValue(null);
        public static bool Old => (bool)Property("oldSystemBackendsEnabled").GetValue(null);
        public static void Set(bool newer,bool older){Property("newSystemBackendsEnabled").SetValue(null,newer);Property("oldSystemBackendsEnabled").SetValue(null,older);}
    }
    private sealed class ARBuildSettingsSnapshot : System.IDisposable {
        readonly UnityEditor.Build.NamedBuildTarget target=UnityEditor.Build.NamedBuildTarget.Android;
        readonly string company=PlayerSettings.companyName,product=PlayerSettings.productName,version=PlayerSettings.bundleVersion,id=PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android);
        readonly int code=PlayerSettings.Android.bundleVersionCode;
        readonly AndroidSdkVersions min=PlayerSettings.Android.minSdkVersion,max=PlayerSettings.Android.targetSdkVersion;
        readonly AndroidArchitecture architectures=PlayerSettings.Android.targetArchitectures;
        readonly ScriptingImplementation backend=PlayerSettings.GetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Android);
        readonly bool defaultGraphics=PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.Android),mobileMt=PlayerSettings.GetMobileMTRendering(UnityEditor.Build.NamedBuildTarget.Android),appBundle=EditorUserBuildSettings.buildAppBundle;
        readonly GraphicsDeviceType[] graphics=PlayerSettings.GetGraphicsAPIs(BuildTarget.Android);
        readonly AndroidApplicationEntry entry=PlayerSettings.Android.applicationEntry;
        readonly UIOrientation orientation=PlayerSettings.defaultInterfaceOrientation;
        readonly bool portrait=PlayerSettings.allowedAutorotateToPortrait,upside=PlayerSettings.allowedAutorotateToPortraitUpsideDown,left=PlayerSettings.allowedAutorotateToLandscapeLeft,right=PlayerSettings.allowedAutorotateToLandscapeRight;
        readonly bool newInput=ARInputSettings.New,oldInput=ARInputSettings.Old;
        readonly UnityEditor.XR.ARCore.ARCoreSettings originalARCore=UnityEditor.XR.ARCore.ARCoreSettings.GetOrCreateSettings();
        readonly string arcoreJson;
        readonly UnityEditor.XR.Management.XRGeneralSettingsPerBuildTarget originalXR;
        readonly UnityEngine.XR.Management.XRGeneralSettings originalGeneral;
        readonly UnityEngine.Object originalManager,originalGraphics;
        readonly string generalJson,managerJson,graphicsJson;
        public ARBuildSettingsSnapshot(){
            arcoreJson=EditorJsonUtility.ToJson(originalARCore);
            originalGraphics=AssetDatabase.LoadAssetAtPath<UnityEngine.Object>("ProjectSettings/GraphicsSettings.asset");
            if(originalGraphics!=null)graphicsJson=EditorJsonUtility.ToJson(originalGraphics);
            if(EditorBuildSettings.TryGetConfigObject(UnityEngine.XR.Management.XRGeneralSettings.settingsKey,out UnityEditor.XR.Management.XRGeneralSettingsPerBuildTarget settings)&&settings!=null){
                originalXR=settings;originalGeneral=settings.SettingsForBuildTarget(BuildTargetGroup.Android);
                if(originalGeneral!=null){generalJson=EditorJsonUtility.ToJson(originalGeneral);originalManager=originalGeneral.Manager;if(originalManager!=null)managerJson=EditorJsonUtility.ToJson(originalManager);}
            }
        }
        public void Dispose(){
            ARInputSettings.Set(newInput,oldInput);
            EditorJsonUtility.FromJsonOverwrite(arcoreJson,originalARCore);EditorUtility.SetDirty(originalARCore);
            PlayerSettings.companyName=company;PlayerSettings.productName=product;PlayerSettings.bundleVersion=version;PlayerSettings.SetApplicationIdentifier(target,id);PlayerSettings.Android.bundleVersionCode=code;
            PlayerSettings.Android.minSdkVersion=min;PlayerSettings.Android.targetSdkVersion=max;PlayerSettings.Android.targetArchitectures=architectures;PlayerSettings.SetScriptingBackend(target,backend);PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android,defaultGraphics);PlayerSettings.SetGraphicsAPIs(BuildTarget.Android,graphics);PlayerSettings.SetMobileMTRendering(target,mobileMt);PlayerSettings.Android.applicationEntry=entry;EditorUserBuildSettings.buildAppBundle=appBundle;
            PlayerSettings.defaultInterfaceOrientation=orientation;PlayerSettings.allowedAutorotateToPortrait=portrait;PlayerSettings.allowedAutorotateToPortraitUpsideDown=upside;PlayerSettings.allowedAutorotateToLandscapeLeft=left;PlayerSettings.allowedAutorotateToLandscapeRight=right;
            if(originalGraphics!=null){EditorJsonUtility.FromJsonOverwrite(graphicsJson,originalGraphics);EditorUtility.SetDirty(originalGraphics);}
            if(originalXR!=null){
                if(originalGeneral!=null){EditorJsonUtility.FromJsonOverwrite(generalJson,originalGeneral);EditorUtility.SetDirty(originalGeneral);}
                if(originalManager!=null){EditorJsonUtility.FromJsonOverwrite(managerJson,originalManager);EditorUtility.SetDirty(originalManager);}
                EditorBuildSettings.AddConfigObject(UnityEngine.XR.Management.XRGeneralSettings.settingsKey,originalXR,true);
            }else EditorBuildSettings.RemoveConfigObject(UnityEngine.XR.Management.XRGeneralSettings.settingsKey);
            AssetDatabase.SaveAssets();
            var restored=new ARRestorationEvidence {
                unity=Application.unityVersion,
                input=ARInputSettings.New==newInput && ARInputSettings.Old==oldInput,
                player=PlayerSettings.companyName==company && PlayerSettings.productName==product && PlayerSettings.bundleVersion==version && PlayerSettings.GetApplicationIdentifier(target)==id && PlayerSettings.Android.bundleVersionCode==code && PlayerSettings.Android.minSdkVersion==min && PlayerSettings.Android.targetSdkVersion==max && PlayerSettings.Android.targetArchitectures==architectures && PlayerSettings.GetScriptingBackend(target)==backend && PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.Android)==defaultGraphics && string.Join(",",PlayerSettings.GetGraphicsAPIs(BuildTarget.Android))==string.Join(",",graphics) && PlayerSettings.GetMobileMTRendering(target)==mobileMt && PlayerSettings.Android.applicationEntry==entry && EditorUserBuildSettings.buildAppBundle==appBundle && PlayerSettings.defaultInterfaceOrientation==orientation && PlayerSettings.allowedAutorotateToPortrait==portrait && PlayerSettings.allowedAutorotateToPortraitUpsideDown==upside && PlayerSettings.allowedAutorotateToLandscapeLeft==left && PlayerSettings.allowedAutorotateToLandscapeRight==right,
                graphics=originalGraphics==null || EditorJsonUtility.ToJson(originalGraphics)==graphicsJson,
                arcore=EditorJsonUtility.ToJson(originalARCore)==arcoreJson,
                xr=(originalGeneral==null || EditorJsonUtility.ToJson(originalGeneral)==generalJson) && (originalManager==null || EditorJsonUtility.ToJson(originalManager)==managerJson)
            };
            restored.passed=restored.player && restored.input && restored.xr && restored.graphics && restored.arcore;
            File.WriteAllText(Path.Combine(OutputDir,"AR_SettingsRestoration.json"),JsonUtility.ToJson(restored,true));
            if(!restored.passed)throw new System.InvalidOperationException("La restauración de ajustes no coincide con el snapshot; revisar AR_SettingsRestoration.json");
        }
    }

    private static void Build(bool development)
    {
        Configure();
        ARSetup.ConfigureXR(false);   // el viewer no inicia la sesion AR
        Directory.CreateDirectory(OutputDir);
        var options = new BuildPlayerOptions
        {
            scenes = new[] { Scene },
            locationPathName = Path.Combine(OutputDir, development ? "P1G8_Viewer_diagnostico.apk" : ApkName),
            target = BuildTarget.Android,
            targetGroup = BuildTargetGroup.Android,
            options = development ? BuildOptions.Development : BuildOptions.None
        };
        EditorUserBuildSettings.buildAppBundle = false;   // APK instalable directamente

        BuildReport report = BuildPipeline.BuildPlayer(options);
        BuildSummary summary = report.summary;
        Debug.Log($"[BuildAndroid] {summary.result} | {summary.outputPath} | {summary.totalSize / (1024f * 1024f):0.0} MB | " +
                  $"{summary.totalErrors} errores, {summary.totalWarnings} avisos, {summary.totalTime}");
        if (Application.isBatchMode && summary.result != BuildResult.Succeeded)
        {
            EditorApplication.Exit(1);
        }
    }
}
