"""FIX03 offline index. Reuses already certified scenarios, never invents reinforcement."""
import argparse, hashlib, json, copy
from pathlib import Path
import capacidad_ha as cha
import honors_comparar_armadura as evidence

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def build(base_path, after_path, certificate_path):
    base,after,certificate=load(base_path),load(after_path),load(certificate_path)
    if digest(after_path)!=certificate["afterSHA256"]: raise ValueError("Certified after SHA mismatch")
    evidence.validate_capacity(base);evidence.validate_capacity(after);evidence.invariant(base,after)
    arm=cha.load_armaduras()
    bs={e["id"]:e for e in base["elements"]};as_={e["id"]:e for e in after["elements"]}
    ref=bs[287];alt=as_[287]
    assert ref["elementTag"]=="E1_287" and ref["sectionId"]=="COL70/70"
    assert ref["capacidad"]["armadura"]["barras"].replace("φ","f")=="16f28" and alt["capacidad"]["armadura"]["barras"].replace("φ","f")=="20f28"
    bc={c["sectionId"]:c for c in base["p1l4"]["pmCurves"]};ac={c["sectionId"]:c for c in after["p1l4"]["pmCurves"]}
    scenario={"id":"COL70_70_16f28_TO_20f28","sectionId":ref["sectionId"],
        "baseCurveId":ref["pmCurveId"],"afterCurveId":alt["pmCurveId"],
        "beforeArm":ref["capacidad"]["armadura"],"afterArm":alt["capacidad"]["armadura"],
        "reference":"Referencia certificada H5: E1_287/C2",
        "provenance":"Override académico por sección COL70/70 16φ28→20φ28; excepciones por elemento conservadas. Capacidad uniaxial de sección, demandas/rigidez prescrita invariantes.",
        "afterCapacity":{"Ast_mm2":alt["capacidad"]["Ast_mm2"],"P0_kN":alt["capacidad"]["P0_kN"],"phiPmax_kN":alt["capacidad"]["phiPmax_kN"]}}
    elements=[];curves={}
    for e in bs.values():
        if e.get("type")!="columna":continue
        a=as_[e["id"]];cap=e.get("capacidad") or {}
        actual=cha.armadura_de(e,arm)
        if cap.get("armadura"):
            assert all(cap["armadura"].get(k)==v for k,v in actual.items()),"Effective reinforcement mismatch"
        cid=e.get("pmCurveId","")
        if cid in bc:curves[cid]=bc[cid]
        compatible=(e["sectionId"]==scenario["sectionId"] and cid==scenario["baseCurveId"]
            and cap.get("armadura")==scenario["beforeArm"] and a.get("pmCurveId")==scenario["afterCurveId"]
            and a.get("capacidad",{}).get("armadura")==scenario["afterArm"])
        if compatible:
            assert bc[cid]==bc[scenario["baseCurveId"]]
            assert ac[a["pmCurveId"]]==ac[scenario["afterCurveId"]]
            old={v["combo"]:v for v in cap["porCombo"]}
            for row in a["capacidad"]["porCombo"]:
                assert row["Pu"]==old[row["combo"]]["Pu"] and row["Mu"]==old[row["combo"]]["Mu"]
        by_element=arm.get("elementos",{})
        origin="EXCEPCIÓN POR ELEMENTO" if e["elementTag"] in by_element or str(e["id"]) in by_element else "CONFIGURACIÓN DE SECCIÓN"
        elements.append({"id":e["id"],"elementTag":e["elementTag"],"sectionId":e["sectionId"],
            "baseCurveId":cid,"baseArm":cap.get("armadura",{}),"reinforcementSource":origin,
            "scenarioId":scenario["id"] if compatible else "",
            "beforeCapacity":cap,"afterCombos":a["capacidad"]["porCombo"] if compatible else []})
    curves[scenario["afterCurveId"]]=ac[scenario["afterCurveId"]]
    return {"schema":"mcoc.honors.h5-catalog/1","baseSHA256":digest(base_path),"afterSHA256":digest(after_path),
        "certificateSHA256":digest(certificate_path),"reinforcementSHA256":digest(cha.ARMADURAS_PATH),
        "scenarios":[scenario],"curves":list(curves.values()),"elements":elements,
        "limitation":"Sólo alternativa académica existente 16φ28→20φ28. Curvas compartidas; demandas por elemento/caso. G/Q/EX/EY: demanda raw existente, Mcap/DCR no publicados. Sin Python/OpenSees en Android."}

def main():
    p=argparse.ArgumentParser();p.add_argument("--base",type=Path,required=True);p.add_argument("--after",type=Path,required=True);p.add_argument("--certificate",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    catalog=build(a.base,a.after,a.certificate);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(catalog,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    manifest={"catalogSHA256":digest(a.out),"inputs":[{"path":str(f),"sha256":digest(f)} for f in [a.base,a.after,a.certificate,Path(__file__),cha.ARMADURAS_PATH]]}
    a.out.with_name(a.out.stem+"_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("Catalog:",len(catalog["elements"]),"columns,",sum(bool(e["scenarioId"]) for e in catalog["elements"]),"eligible; curves",len(catalog["curves"]))
if __name__=="__main__":main()
