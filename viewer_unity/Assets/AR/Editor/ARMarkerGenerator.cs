using System;
using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.XR.ARSubsystems;
using UnityEngine;
using UnityEngine.XR.ARSubsystems;

namespace LabViewer
{
    public static class ARMarkerGenerator
    {
        const int Size = 1024;
        const int W = Size;
        const int H = Size;

        static readonly Color32 Black = new Color32(0, 0, 0, 255);
        static readonly Color32 White = new Color32(255, 255, 255, 255);

        static readonly byte[][] Digits =
        {
            new byte[] { 0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110 },
            new byte[] { 0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001 },
            new byte[] { 0b11111, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b11111 },
            new byte[] { 0b11111, 0b10001, 0b10001, 0b11111, 0b10001, 0b10010, 0b11100 },
        };

        [MenuItem("AR/Generate Marker 489 + Reference Library")]
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
                Debug.LogError("[ARMarkerGenerator] fallo: " + e);
                EditorApplication.Exit(1);
                return;
            }

            EditorApplication.Exit(0);
        }

        static void Generate()
        {
            string root = "Assets/AR";
            string dir = root + "/ReferenceImages";
            EnsureFolder(root);
            EnsureFolder(dir);

            string pngPath = dir + "/marker_489.png";
            string libPath = dir + "/AR_REF_489.asset";

            var buffer = new Color32[W * H];
            for (int i = 0; i < buffer.Length; i++)
                buffer[i] = White;

            Fill(buffer, 44, 44, 980, 980, Black);
            Fill(buffer, 92, 92, 932, 932, White);

            Fill(buffer, 120, 120, 340, 340, Black);
            Fill(buffer, 610, 120, 770, 280, Black);
            Fill(buffer, 120, 660, 250, 790, Black);

            const int bandX0 = 310;
            const int bandY0 = 470;
            const int bandX1 = 714;
            const int bandY1 = 560;
            Fill(buffer, bandX0, bandY0, bandX1, bandY1, Black);

            int[] glyphIndex = { 1, 2, 3 };
            const int scale = 9;
            const int gap = 14;
            int textW = glyphIndex.Length * 5 * scale + (glyphIndex.Length - 1) * gap;
            int startX = (W - textW) / 2;
            int startY = bandY0 + (bandY1 - bandY0 - 7 * scale) / 2;
            for (int d = 0; d < glyphIndex.Length; d++)
            {
                DrawDigit(buffer, glyphIndex[d], startX, startY, scale);
                startX += 5 * scale + gap;
            }

            int[] barWidths = { 6, 12, 6, 18, 6, 12, 18, 6 };
            const int barGap = 8;
            const int barY0 = 600;
            const int barY1 = 668;
            int barW = 0;
            for (int i = 0; i < barWidths.Length; i++)
                barW += barWidths[i] + barGap;
            int bx = (W - barW) / 2;
            for (int i = 0; i < barWidths.Length; i++)
            {
                if ((i & 1) == 0)
                    Fill(buffer, bx, barY0, bx + barWidths[i] - 1, barY1, Black);
                bx += barWidths[i] + barGap;
            }

            const int hatchLen = 130;
            const int hatchThick = 9;
            for (int k = 0; k < 5; k++)
            {
                int hx = 300 + k * 40;
                DrawLine(buffer, hx, 700, hx + hatchLen, 830, hatchThick, Black);
            }

            DrawScatter(buffer);

            var tex = new Texture2D(W, H, TextureFormat.RGBA32, false);
            tex.SetPixels32(buffer);
            tex.Apply(false);

            byte[] png = tex.EncodeToPNG();
            if (png == null || png.Length == 0)
                throw new InvalidOperationException("EncodeToPNG devolvio vacio");
            File.WriteAllBytes(pngPath, png);
            UnityEngine.Object.DestroyImmediate(tex);

            AssetDatabase.ImportAsset(pngPath, ImportAssetOptions.ForceUpdate);
            ConfigureImporter((TextureImporter)AssetImporter.GetAtPath(pngPath));

            var textureAsset = (Texture2D)AssetDatabase.LoadAssetAtPath(pngPath, typeof(Texture2D));
            if (textureAsset == null)
                throw new InvalidOperationException("No se pudo cargar la textura importada");

            var lib = AssetDatabase.LoadAssetAtPath<XRReferenceImageLibrary>(libPath);
            if (lib == null)
            {
                lib = ScriptableObject.CreateInstance<XRReferenceImageLibrary>();
                AssetDatabase.CreateAsset(lib, libPath);
            }

            while (lib.count > 1)
                lib.RemoveAt(lib.count - 1);
            if (lib.count == 0)
                lib.Add();

            lib.SetTexture(0, textureAsset, true);
            lib.SetName(0, "REF_EII_CP2_V_029");
            lib.SetSpecifySize(0, true);
            lib.SetSize(0, new Vector2(0.30f, 0.30f));

            EditorUtility.SetDirty(lib);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            var reloaded = AssetDatabase.LoadAssetAtPath<XRReferenceImageLibrary>(libPath);
            if (reloaded == null)
                throw new InvalidOperationException("No se pudo recargar la biblioteca");

            if (reloaded.guid == Guid.Empty)
                EnsureLibraryGuid(reloaded);

            if (reloaded.count != 1)
                throw new InvalidOperationException("La biblioteca debe tener exactamente 1 imagen");

            string pngGuid = AssetDatabase.AssetPathToGUID(pngPath);
            string libGuid = AssetDatabase.AssetPathToGUID(libPath);
            Debug.Log("[ARMarkerGenerator] OK png: " + pngPath + " guid=" + pngGuid + " " +
                      "lib: " + libPath + " guid=" + libGuid + " " +
                      "name=" + reloaded[0].name + " size=" + reloaded[0].size +
                      " specifySize=" + reloaded[0].specifySize +
                      " referenceImageGuid=" + reloaded[0].guid);
        }

        static void ConfigureImporter(TextureImporter ti)
        {
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = true;
            ti.mipmapEnabled = true;
            ti.maxTextureSize = 1024;
            ti.textureCompression = TextureImporterCompression.Uncompressed;
            ti.isReadable = false;

            var android = new TextureImporterPlatformSettings
            {
                name = "Android",
                overridden = true,
                maxTextureSize = 1024,
                textureCompression = TextureImporterCompression.Uncompressed,
                format = TextureImporterFormat.RGBA32,
            };
            ti.SetPlatformTextureSettings(android);
            ti.SaveAndReimport();
        }

        static void EnsureLibraryGuid(XRReferenceImageLibrary lib)
        {
            var g = Guid.NewGuid();
            byte[] b = g.ToByteArray();
            ulong low = BitConverter.ToUInt64(b, 0);
            ulong high = BitConverter.ToUInt64(b, 8);

            var so = new SerializedObject(lib);
            SerializedProperty pLow = so.FindProperty("m_GuidLow");
            SerializedProperty pHigh = so.FindProperty("m_GuidHigh");
            pLow.longValue = unchecked((long)low);
            pHigh.longValue = unchecked((long)high);
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(lib);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path))
                return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            string leaf = Path.GetFileName(path);
            AssetDatabase.CreateFolder(parent, leaf);
        }

        static void Fill(Color32[] buf, int x0, int y0, int x1, int y1, Color32 c)
        {
            for (int y = y0; y <= y1; y++)
            {
                int row = y * W;
                for (int x = x0; x <= x1; x++)
                    buf[row + x] = c;
            }
        }

        static void DrawDigit(Color32[] buf, int digit, int x0, int y0, int scale)
        {
            byte[] glyph = Digits[digit];
            for (int gy = 0; gy < 7; gy++)
            {
                byte rowBits = glyph[gy];
                for (int gx = 0; gx < 5; gx++)
                {
                    if ((rowBits & (1 << gx)) == 0)
                        continue;
                    int px = x0 + gx * scale;
                    int py = y0 + gy * scale;
                    Fill(buf, px, py, px + scale - 1, py + scale - 1, White);
                }
            }
        }

        static void DrawLine(Color32[] buf, int x0, int y0, int x1, int y1, int thickness, Color32 c)
        {
            int dx = Mathf.Abs(x1 - x0);
            int dy = Mathf.Abs(y1 - y0);
            int sx = x0 < x1 ? 1 : -1;
            int sy = y0 < y1 ? 1 : -1;
            int err = dx - dy;
            int x = x0;
            int y = y0;
            int t = thickness / 2;
            while (true)
            {
                Fill(buf, x - t, y - t, x + t, y + t, c);
                if (x == x1 && y == y1)
                    break;
                int e2 = 2 * err;
                if (e2 > -dy) { err -= dy; x += sx; }
                if (e2 < dx) { err += dx; y += sy; }
            }
        }

        static void DrawScatter(Color32[] buf)
        {
            var reserved = new List<RectInt>
            {
                new RectInt(120, 120, 221, 221),
                new RectInt(610, 120, 161, 161),
                new RectInt(120, 660, 131, 131),
                new RectInt(310, 470, 405, 91),
                new RectInt(420, 580, 201, 89),
                new RectInt(260, 700, 491, 233),
            };

            var rng = new System.Random(489);
            int placed = 0;
            for (int attempt = 0; attempt < 400 && placed < 30; attempt++)
            {
                int s = rng.Next(10, 27);
                int x = rng.Next(96, W - s - 96);
                int y = rng.Next(96, H - s - 96);
                var r = new RectInt(x, y, s, s);
                bool overlap = false;
                foreach (var rr in reserved)
                {
                    if (Overlaps(r, rr))
                    {
                        overlap = true;
                        break;
                    }
                }
                if (!overlap)
                {
                    Fill(buf, x, y, x + s - 1, y + s - 1, Black);
                    placed++;
                }
            }
        }

        static bool Overlaps(RectInt a, RectInt b)
        {
            return a.x < b.x + b.width &&
                   a.x + a.width > b.x &&
                   a.y < b.y + b.height &&
                   a.y + a.height > b.y;
        }
    }
}