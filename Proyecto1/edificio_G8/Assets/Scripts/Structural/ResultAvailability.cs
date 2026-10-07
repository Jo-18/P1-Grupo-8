using System;
public enum ResultAvailability { Available, Partial, Missing, Invalid }
[Serializable] public class ResultUnits { public string length, force, moment, displacement, rotation; }
[Serializable] public class ResultConventions { public string forces, displacements, endActions, sectionI, sectionJ, axial, capacityP; }
[Serializable] public class InputHashes { public string modelo, parametros, combinaciones, armaduras, mods, armaduras_cambios; }
[Serializable] public class RunProvenance { public string comando, fecha, python, openseespy, opensees, motor, commit, exporter, forceSource, displacementSource, capacitySource; public InputHashes entradas_sha256; }
[Serializable] public class CaseState { public string name, state; public bool ok; public int forceCount, displacementCount, appliedLoadCount; }
[Serializable] public class AppliedLoad {public string combo,kind,axes,source;public int targetId;public float[] values;}
[Serializable] public class ReactionRecord { public string combo, status; public int node; public float[] f; }
[Serializable] public class WallMapping {
    public int visualWallId, visualNodeI, visualNodeJ, analyticalId, analysisNodeI, analysisNodeJ;
    public string visualTag, analyticalTag, wallInPlaneAxis;
    public float bottomZ, topZ;
}
[Serializable] public class MomentCurvatureReference {
    public string sectionId, source, sha256, method, curvatureUnit, momentUnit, armadura;
    public float P_kN,L_m,t_m;
    public float[] curvature,moment;
}
