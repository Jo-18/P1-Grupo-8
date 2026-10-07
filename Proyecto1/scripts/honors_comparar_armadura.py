"""H5 non-destructive capacity scenarios. Uses the existing updater and OpenSees exporter."""
import argparse, copy, csv, hashlib, json, os, subprocess, sys, math
from pathlib import Path
import actualizar_armadura as updater
import capacidad_ha as cha
import export_contract
from validacion_entradas import validar_armaduras, ErrorValidacion

REPO=Path(__file__).resolve().parents[2]
SCRIPTS=Path(__file__).resolve().parent
BASE=REPO/'Proyecto1/edificio_G8/Assets/Resources/estructura_p1l4_unity.json'
INVARIANT_TOP=('nodes','walls')
INVARIANT_RESULTS=('elementForces','displacements','reactions','caseStates','appliedLoads','combinations','wallMappings')
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v): Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
def validate_overrides(o,u):
    errors=[]
    if not isinstance(o,dict) or set(o)-{'secciones','elementos','muros'}: raise ErrorValidacion('Grupos de override desconocidos')
    for group in ('secciones','elementos'):
        values=o.get(group,{})
        if not isinstance(values,dict): raise ErrorValidacion('Override debe ser un objeto')
        allowed={e['sectionId'] for e in u['elements']} if group=='secciones' else {e['elementTag'] for e in u['elements']}|{str(e['id']) for e in u['elements']}
        for key,arm in values.items():
            if key not in allowed or not isinstance(arm,dict) or not arm: errors.append('Override desconocido/vacio: '+key);continue
            for k,v in arm.items():
                if k not in {'barras','estribos','inferior','superior','supleApoyo','estribosApoyo','estribosTramo'} or not isinstance(v,str) or not v.strip(): errors.append('Campo invalido: '+key+'.'+k)
    if errors: raise ErrorValidacion('; '.join(errors))
    validar_armaduras(o,errors)
    if errors: raise ErrorValidacion('; '.join(errors))
def validate_capacity(u):
    export_contract.validate_bundle(u)
    curves={c['sectionId']:c for c in u['p1l4']['pmCurves']}
    for e in u['elements']:
        if e.get('pmCurveId') and e['pmCurveId'] not in curves: raise ValueError('Curva inexistente: '+e['elementTag'])
    for c in curves.values():
        for p in c['points']:
            if not all(math.isfinite(p[k]) for k in ('P_kN','M_kN_m')): raise ValueError('Curva no finita')
def invariant(a,b):
    for k in INVARIANT_TOP: assert a.get(k)==b.get(k),k
    for k in INVARIANT_RESULTS: assert a['p1l4'].get(k)==b['p1l4'].get(k),k
    geom=lambda u:[{k:v for k,v in e.items() if k not in ('capacidad','pmCurveId')} for e in u['elements']]
    assert geom(a)==geom(b),'geometria/metadata'
def safe_output(out,src):
    p=Path(out).resolve(); root=REPO.resolve()
    if p==Path(src).resolve() or not p.is_relative_to(root/'entrega'/'honors'): raise ValueError('Salida solo en entrega/honors del derivado; nunca sobre entrada/base')
    if p.exists(): raise FileExistsError('La salida ya existe: '+str(p))
    p.parent.mkdir(parents=True,exist_ok=True)
    return p
def scenario(src,overrides,out):
    out=safe_output(out,src); u=read(src); validate_capacity(u);validate_overrides(overrides,u)
    protected={p:sha(p) for p in (Path(src),cha.ARMADURAS_PATH)}
    override=out.with_suffix('.overrides.json'); temp=out.with_suffix('.pending.json')
    if override.exists() or temp.exists(): raise FileExistsError('Staging existente')
    write(override,overrides)
    try:
        r=subprocess.run([sys.executable,'-X','utf8',str(SCRIPTS/'actualizar_armadura.py'),'--json',str(src),'--armaduras',str(override),'--out',str(temp)],capture_output=True,text=True,encoding='utf-8',timeout=300)
        out.with_suffix('.log').write_text(r.stdout+'\nSTDERR\n'+r.stderr,encoding='utf-8')
        if r.returncode: raise RuntimeError(r.stderr)
        v=read(temp);validate_capacity(v);invariant(u,v)
        for p,h in protected.items(): assert sha(p)==h,'Entrada alterada'
        os.replace(temp,out)
        return v
    except Exception:
        if temp.exists(): temp.unlink()
        raise
def selected(u): return next(e for e in u['elements'] if e['elementTag']=='E1_287' and e['id']==287)
def compare(src,directory,reference=False):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    u=read(src); e=selected(u);arm=cha.load_armaduras()
    assert e['sectionId']=='COL70/70' and e['elementTag'] not in arm['elementos'] and str(e['id']) not in arm['elementos']
    assert cha.armadura_de(e,arm)['barras'].replace('φ','f')=='16f28'
    before=scenario(src,{},directory/'before.json')
    after=scenario(src,{'secciones':{'COL70/70':{'barras':'20f28'}},'elementos':{}},directory/'after.json')
    rows=[]
    for label,v in [('16f28',before),('20f28',after)]:
        el=selected(v); c=el['capacidad']
        for d in c['porCombo']: rows.append(dict(scenario=label,element='E1_287',curveId=el['pmCurveId'],Ast_mm2=c['Ast_mm2'],P0_kN=c['P0_kN'],phiPmax_kN=c['phiPmax_kN'],**d))
    write(directory/'comparison.json',dict(scope='Override COL70/70; excepciones por elemento conservadas',limitation='Compatibilidad uniaxial de seccion. Rigidez prescrita y demandas OpenSees invariantes. Escenario academico; no armadura construida.',rows=rows))
    with (directory/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,7))
    for label,v in [('16φ28',before),('20φ28',after)]:
        el=selected(v); curve=next(c for c in v['p1l4']['pmCurves'] if c['sectionId']==el['pmCurveId'])
        ax.plot([p['M_kN_m'] for p in curve['points']],[p['P_kN'] for p in curve['points']],label=label)
    d=next(d for d in selected(before)['capacidad']['porCombo'] if d['combo']=='C2');ax.scatter([d['Mu']],[d['Pu']],color='black',label='Demanda C2 invariante',zorder=5)
    ax.set(xlabel='φM [kN·m]',ylabel='φP [kN]',title='E1_287 / COL70/70 — comparación académica H5');ax.legend();ax.grid();fig.tight_layout();fig.savefig(directory/'comparison.png',dpi=160);plt.close(fig)
    checks=[]
    for label,v in [('before',before),('after',after)]:
        o={} if label=='before' else {'secciones':{'COL70/70':{'barras':'20f28'}}}
        a=cha.load_armaduras(overrides=o);el=selected(v)
        combos={d['combo'] for d in el['capacidad']['porCombo']}
        fs={f['combo']:f['f'] for f in u['p1l4']['elementForces'] if f['id']==el['id'] and f['combo'] in combos}
        nodes={n['id']:n for n in u['nodes']}
        direct=cha.evaluar(el,fs,{k:0 for k in fs},updater.cvm.element_length(el,nodes),a)
        assert abs(direct['DCR']-el['capacidad']['DCR'])<=.001
        checks.append(dict(scenario=label,directDCR=direct['DCR'],publishedDCR=el['capacidad']['DCR']))
        if reference:
            target=directory/(label+'_opensees_direct.json')
            args=[sys.executable,'-X','utf8',str(SCRIPTS/'exportar_resultados_unity.py'),'--out',str(target),'--armaduras',str(directory/(label+'.overrides.json'))]
            r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=600)
            (directory/(label+'_opensees.log')).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8');assert r.returncode==0,r.stderr
            ref=read(target);validate_capacity(ref)
            refel=selected(ref);assert refel['pmCurveId']==el['pmCurveId']
            for k in ('Ast_mm2','P0_kN','phiPmax_kN'): assert abs(refel['capacidad'][k]-el['capacidad'][k])<=.1
            assert abs(refel['capacidad']['DCR']-el['capacidad']['DCR'])<=.001
            rc=next(c for c in ref['p1l4']['pmCurves'] if c['sectionId']==el['pmCurveId']);vc=next(c for c in v['p1l4']['pmCurves'] if c['sectionId']==el['pmCurveId'])
            assert len(rc['points'])==len(vc['points'])
            for p,q in zip(rc['points'],vc['points']):
                assert abs(p['P_kN']-q['P_kN'])<=.1 and abs(p['M_kN_m']-q['M_kN_m'])<=.1
    write(directory/'validation.json',dict(invariance=True,directCapacity=checks,realOpenSeesCompared=reference,rounding=dict(capacity_kN=.1,DCR=.001)))
    inputs=[Path(src),cha.ARMADURAS_PATH,*SCRIPTS.glob('*.py'),*(REPO/'Proyecto1/data').glob('*.json')]
    files=list(directory.glob('*'))
    write(directory/'manifest.json',dict(inputs=[dict(path=str(p),sha256=sha(p)) for p in inputs],outputs=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files if p.is_file()],python=sys.version,replica=False))
    print(json.dumps(rows,ensure_ascii=False))
def main():
    p=argparse.ArgumentParser();p.add_argument('--json',type=Path,default=BASE);p.add_argument('--directory',type=Path);p.add_argument('--armaduras',type=Path);p.add_argument('--out',type=Path);p.add_argument('--reference',action='store_true');a=p.parse_args()
    try:
        if a.out:
            v=scenario(a.json,read(a.armaduras) if a.armaduras else {},a.out);print('H5 validated '+str(a.out))
        else:
            if not a.directory: p.error('--directory o --out requerido')
            compare(a.json,a.directory,a.reference)
    except Exception as e: print('ERROR H5: '+str(e),file=sys.stderr);return 2
    return 0
if __name__=='__main__':sys.exit(main())
