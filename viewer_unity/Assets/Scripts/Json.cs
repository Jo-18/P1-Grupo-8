using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace LabViewer
{
    /// <summary>
    /// Mini parser JSON (recursive descent) que produce arboles tipados:
    /// Dictionary&lt;string,object&gt; | List&lt;object&gt; | double | string | bool | null.
    /// No depende de JsonUtility ni Newtonsoft (proyecto minimo).
    /// </summary>
    public static class Json
    {
        public static object Parse(string text)
        {
            var p = new JParser(text);
            object v = p.ParseValue();
            p.SkipWs();
            if (!p.AtEnd) throw new FormatException("JSON trailing content at " + p.Pos);
            return v;
        }

        public static Dictionary<string, object> AsObj(object o) => o as Dictionary<string, object>;
        public static List<object> AsArr(object o) => o as List<object>;

        public static bool IsNull(object o) => o == null;

        public static string Str(object o, string key)
        {
            if (o is Dictionary<string, object> d && d.TryGetValue(key, out var v) && v is string s) return s;
            return null;
        }

        public static double Num(object o, string key, double dflt = 0)
        {
            if (o is Dictionary<string, object> d && d.TryGetValue(key, out var v))
            {
                if (v is double db) return db;
                if (v is string s && double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out db)) return db;
            }
            return dflt;
        }

        public static bool Bool(object o, string key, bool dflt = false)
        {
            if (o is Dictionary<string, object> d && d.TryGetValue(key, out var v))
            {
                if (v is bool b) return b;
                if (v is string s && s.ToLowerInvariant() == "true") return true;
                if (v is string s2 && s2.ToLowerInvariant() == "false") return false;
            }
            return dflt;
        }

        public static List<object> Arr(object o, string key)
        {
            if (o is Dictionary<string, object> d && d.TryGetValue(key, out var v) && v is List<object> a) return a;
            return null;
        }

        /// <summary>Lee una tupla [x,y,z] como Vector3 (frame Unity). Devuelve null si ausente.</summary>
        public static UnityEngine.Vector3? V3(object o, string key)
        {
            var arr = Arr(o, key);
            if (arr == null || arr.Count < 3) return null;
            double x = ToNum(arr[0]), y = ToNum(arr[1]), z = ToNum(arr[2]);
            return new UnityEngine.Vector3((float)x, (float)y, (float)z);
        }

        public static double ToNum(object o)
        {
            if (o is double d) return d;
            if (o is string s && double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out d)) return d;
            if (o is bool b) return b ? 1 : 0;
            return 0;
        }

        public static List<UnityEngine.Vector3> V3List(object o, string key)
        {
            var res = new List<UnityEngine.Vector3>();
            var arr = Arr(o, key);
            if (arr == null) return res;
            foreach (var pt in arr)
            {
                if (pt is List<object> p && p.Count >= 3)
                    res.Add(new UnityEngine.Vector3((float)ToNum(p[0]), (float)ToNum(p[1]), (float)ToNum(p[2])));
            }
            return res;
        }
    }

    internal sealed class JParser
    {
        private readonly string s;
        private int i;

        public JParser(string text) { s = text; i = 0; }
        public int Pos => i;
        public bool AtEnd => i >= s.Length;

        public void SkipWs()
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        public object ParseValue()
        {
            SkipWs();
            if (i >= s.Length) throw new FormatException("Unexpected end of JSON");
            char c = s[i];
            switch (c)
            {
                case '{': return ParseObject();
                case '[': return ParseArray();
                case '"': return ParseString();
                case 't': Expect("true"); return true;
                case 'f': Expect("false"); return false;
                case 'n': Expect("null"); return null;
                default: return ParseNumber();
            }
        }

        private void Expect(string w)
        {
            if (i + w.Length > s.Length || s.Substring(i, w.Length) != w)
                throw new FormatException("Invalid token at " + i);
            i += w.Length;
        }

        private Dictionary<string, object> ParseObject()
        {
            i++; // {
            var d = new Dictionary<string, object>();
            SkipWs();
            if (i < s.Length && s[i] == '}') { i++; return d; }
            while (true)
            {
                SkipWs();
                if (i >= s.Length || s[i] != '"') throw new FormatException("Expected key at " + i);
                string key = ParseString();
                SkipWs();
                if (i >= s.Length || s[i] != ':') throw new FormatException("Expected ':' at " + i);
                i++;
                object val = ParseValue();
                d[key] = val;
                SkipWs();
                if (i >= s.Length) throw new FormatException("Unterminated object");
                if (s[i] == ',') { i++; continue; }
                if (s[i] == '}') { i++; return d; }
                throw new FormatException("Expected ',' or '}' at " + i);
            }
        }

        private List<object> ParseArray()
        {
            i++; // [
            var a = new List<object>();
            SkipWs();
            if (i < s.Length && s[i] == ']') { i++; return a; }
            while (true)
            {
                a.Add(ParseValue());
                SkipWs();
                if (i >= s.Length) throw new FormatException("Unterminated array");
                if (s[i] == ',') { i++; continue; }
                if (s[i] == ']') { i++; return a; }
                throw new FormatException("Expected ',' or ']' at " + i);
            }
        }

        private string ParseString()
        {
            i++; // "
            var sb = new StringBuilder();
            while (i < s.Length)
            {
                char c = s[i];
                if (c == '"') { i++; return sb.ToString(); }
                if (c == '\\')
                {
                    i++;
                    if (i >= s.Length) break;
                    char e = s[i];
                    switch (e)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            if (i + 4 < s.Length)
                            {
                                string hex = s.Substring(i + 1, 4);
                                sb.Append((char)ushort.Parse(hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture));
                                i += 4;
                            }
                            break;
                        default: sb.Append(e); break;
                    }
                    i++;
                }
                else { sb.Append(c); i++; }
            }
            throw new FormatException("Unterminated string");
        }

        private object ParseNumber()
        {
            int start = i;
            if (i < s.Length && (s[i] == '-' || s[i] == '+')) i++;
            while (i < s.Length && (char.IsDigit(s[i]) || s[i] == '.' || s[i] == 'e' || s[i] == 'E' || s[i] == '-' || s[i] == '+')) i++;
            string num = s.Substring(start, i - start);
            if (!double.TryParse(num, NumberStyles.Float, CultureInfo.InvariantCulture, out double d))
                throw new FormatException("Invalid number: " + num);
            return d;
        }
    }
}
