using System.IO;
using System.Linq;
using System.Xml.Linq;
using UnityEditor.Android;
using UnityEngine;

/// <summary>
/// Semana 6 (AR): en el Galaxy S24 el sistema entregaba el giroscopio y el
/// acelerometro a la app cada 160 ms (~6 Hz) aunque ARCore pide 5 ms (200 Hz):
/// sin IMU el tracking visual-inercial deriva y no detecta planos.
/// Se agrega HIGH_SAMPLING_RATE_SENSORS (Android 12+) al manifiesto generado.
/// </summary>
public class ARManifestPatch : IPostGenerateGradleAndroidProject
{
    public int callbackOrder => 100;

    private const string Permission = "android.permission.HIGH_SAMPLING_RATE_SENSORS";

    public void OnPostGenerateGradleAndroidProject(string path)
    {
        string manifest = Path.Combine(path, "src", "main", "AndroidManifest.xml");
        if (!File.Exists(manifest)) return;
        var xml=XDocument.Load(manifest);XNamespace android="http://schemas.android.com/apk/res/android";var root=xml.Root;
        foreach(var name in new[]{Permission,"android.permission.CAMERA"})if(!root.Elements("uses-permission").Any(e=>(string)e.Attribute(android+"name")==name))root.Add(new XElement("uses-permission",new XAttribute(android+"name",name)));
        if(UnityEditor.PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android).Contains(".ar")) {
            if(!root.Elements("uses-feature").Any(e=>(string)e.Attribute(android+"name")=="android.hardware.camera.ar"))root.Add(new XElement("uses-feature",new XAttribute(android+"name","android.hardware.camera.ar"),new XAttribute(android+"required","true")));
            // ARCore adds required depth but does not remove it on an incremental
            // build when settings become optional. Reconcile the cached manifest.
            if(UnityEditor.XR.ARCore.ARCoreSettings.GetOrCreateSettings().depth==UnityEditor.XR.ARCore.ARCoreSettings.Requirement.Optional) {
                var depth=root.Elements("uses-feature").FirstOrDefault(e=>(string)e.Attribute(android+"name")=="com.google.ar.core.depth");
                if(depth==null){depth=new XElement("uses-feature",new XAttribute(android+"name","com.google.ar.core.depth"));root.Add(depth);}
                depth.SetAttributeValue(android+"required","false");
            }
        }
        xml.Save(manifest);
        Debug.Log("[ARManifestPatch] Permiso agregado: " + Permission);
    }
}
