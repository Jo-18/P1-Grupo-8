"""Contrato estricto AR v2. No altera fuerzas raw ni resuelve análisis."""
import math,hashlib
from pathlib import Path
import json

SCHEMA = 'mcoc.ar/2.0'
UNITS = dict(length='m', force='kN', moment='kN*m', displacement='m', rotation='rad')
CONVENTIONS = dict(forces='element-local', displacements='model-global',
                   endActions='[Ni,Vyi,Vzi,Ti,Myi,Mzi,Nj,Vyj,Vzj,Tj,Myj,Mzj]',
                   sectionI='-fI', sectionJ='+fJ', axial='tension-positive', capacityP='compression-positive')

def finite(values):
    return all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values)

def unique(rows,key,label):
    values=[r[key] for r in rows]
    if len(set(values))!=len(values):raise ValueError('Duplicado: '+label)

def validate_analysis(data,results):
    """Rechaza casos fallidos/parciales antes de capacidad y empaquetado."""
    nodes={n['id'] for n in data['nodes']}
    elements={e['id'] for e in data['elements'] if not e.get('removed')}
    for case,r in results.items():
        if not r or r.get('ok') is not True:raise ValueError('Caso fallido: '+case)
        if set(r.get('element_forces',{}))!=elements:raise ValueError('Fuerzas incompletas: '+case)
        if set(r.get('displacements',{}))!=nodes:raise ValueError('Desplazamientos incompletos: '+case)
        for f in r['element_forces'].values():
            if len(f)!=12 or not finite(f):raise ValueError('Fuerza parcial/inválida: '+case)
        for d in r['displacements'].values():
            if set(('ux','uy','uz','rx','ry','rz'))-d.keys() or not finite([d[k] for k in ('ux','uy','uz','rx','ry','rz')]):
                raise ValueError('Desplazamiento parcial/inválido: '+case)

def validate_bundle(d):
    if d.get('schemaVersion')!=SCHEMA:raise ValueError('Schema inválido')
    if d.get('resultUnits')!=UNITS:raise ValueError('Unidades faltantes/inválidas')
    if d.get('conventions')!=CONVENTIONS:raise ValueError('Convenciones inválidas')
    c=d.get('corrida',{})
    if c.get('motor')!='OpenSees' or not c.get('openseespy') or not c.get('opensees') or not c.get('fecha'):
        raise ValueError('Procedencia oficial faltante')
    if not all(c.get('entradas_sha256',{}).get(k) for k in ('modelo','parametros','combinaciones','armaduras')):
        raise ValueError('Hashes faltantes')
    ns,els=d['nodes'],d['elements']
    unique(ns,'id','nodeTag');unique(els,'id','eleTag');unique(els,'elementTag','elementTag')
    nodes={n['id']:n for n in ns}; elements={e['id']:e for e in els}
    for n in ns:
        if not finite([n[k] for k in ('x','y','z')]):raise ValueError('Coordenadas inválidas')
    for e in els:
        if e['nodeI'] not in nodes or e['nodeJ'] not in nodes:raise ValueError('Nodo inexistente')
        if e['nodeI']==e['nodeJ']:raise ValueError('Elemento de longitud cero')
    p=d['p1l4']; cases=[s['name'] for s in p['caseStates']]
    unique(p['caseStates'],'name','caso')
    if not cases or any(s['state']!='Available' or not s['ok'] for s in p['caseStates']):raise ValueError('Caso fallido/parcial')
    if 'appliedLoads' not in p:raise ValueError('Cargas prescritas faltantes')
    applied_keys=set()
    for load in p['appliedLoads']:
        key=(load['combo'],load['kind'],load['targetId'])
        if key in applied_keys:raise ValueError('Carga prescrita duplicada')
        applied_keys.add(key)
        if load['combo'] not in cases or load['axes']!='model-global' or load['kind'] not in ('nodeForce','elementUniformTotal') or len(load['values']) not in (3,6) or not finite(load['values']):raise ValueError('Carga prescrita inválida')
        if load['targetId'] not in (nodes if load['kind']=='nodeForce' else elements):raise ValueError('Carga sin geometría')
    for state in p['caseStates']:
        if state['appliedLoadCount']!=sum(load['combo']==state['name'] for load in p['appliedLoads']):raise ValueError('Cargas prescritas incompletas')
    keys=set()
    for r in p['elementForces']:
        key=(r['combo'],r['id'])
        if key in keys:raise ValueError('Fuerza duplicada')
        keys.add(key)
        if r['id'] not in elements or len(r['f'])!=12 or not finite(r['f']) or r.get('status')!='Available':raise ValueError('Fuerza parcial/inválida')
    if keys!={(c,e) for c in cases for e in elements}:raise ValueError('Fuerzas incompletas')
    keys=set()
    for r in p['displacements']:
        key=(r['combo'],r['node'])
        if key in keys:raise ValueError('Desplazamiento duplicado')
        keys.add(key)
        if not finite([r[k] for k in ('ux','uy','uz','rx','ry','rz')]) or r.get('status')!='Available':raise ValueError('Desplazamiento inválido')
    if keys!={(c,n) for c in cases for n in nodes}:raise ValueError('Desplazamientos incompletos')
    reactions=p.get('reactions',[]);keys=set()
    supports={s['node'] for s in d.get('supports',[])}
    for r in reactions:
        key=(r['combo'],r['node'])
        if key in keys or r['combo'] not in cases or r['node'] not in supports or len(r['f'])!=6 or not finite(r['f']) or r.get('status')!='Available':raise ValueError('Reacción duplicada/inválida')
        keys.add(key)
    if keys!={(c,n) for c in cases for n in supports}:raise ValueError('Reacciones incompletas')
    walls=d['walls']; mappings=p['wallMappings']
    unique(walls,'id','muro visual');unique(mappings,'visualWallId','mapping visual');unique(mappings,'analyticalId','mapping analítico')
    if {m['visualWallId'] for m in mappings}!={w['id'] for w in walls}:raise ValueError('Mapping muro incompleto')
    if {m['analyticalId'] for m in mappings}!={e['id'] for e in els if e['type']=='muro'}:raise ValueError('Mapping analítico incompleto')
    for m in mappings:
        e=elements.get(m['analyticalId']);w=next(w for w in walls if w['id']==m['visualWallId'])
        if not e or e.get('wallIndex')!=w['id'] or e['elementTag']!=m['analyticalTag'] or w['elementTag']!=m['visualTag']:
            raise ValueError('Mapping muro inválido')
        if m['analysisNodeI']!=e['nodeI'] or m['analysisNodeJ']!=e['nodeJ'] or m['visualNodeI']!=w['nodeI'] or m['visualNodeJ']!=w['nodeJ'] or not finite([m['bottomZ'],m['topZ']]) or m['topZ']<=m['bottomZ'] or m['wallInPlaneAxis']!=e['wallInPlaneAxis']:
            raise ValueError('Geometría muro inválida')
    for reference in p.get('momentCurvatureReferences',[]):
        x,y=reference['curvature'],reference['moment']
        if not x or len(x)!=len(y) or not finite(x+y) or x!=sorted(x) or reference['curvatureUnit']!='1/m' or reference['momentUnit']!='kN*m' or not reference.get('source') or not reference.get('sha256'):raise ValueError('Referencia M-phi inválida')
    return True

def enrich_bundle(output,results,engine_version,applied_cases):
    # Original geometry mixes numeric/string sourceId; the Unity DTO is string.
    # Keep structural id/nodeTag integers unchanged.
    for entry in output['elements']+output['walls']:
        if 'sourceId' in entry:entry['sourceId']=str(entry['sourceId'])
    output['schemaVersion']=SCHEMA;output['resultUnits']=dict(UNITS);output['conventions']=dict(CONVENTIONS)
    output['corrida']['opensees']=str(engine_version)
    output['corrida']['exporter']='Proyecto1/scripts/exportar_resultados_unity.py:main'
    output['corrida']['forceSource']='ops.eleResponse(eleTag, localForce)'
    output['corrida']['displacementSource']='ops.nodeDisp(nodeTag)'
    output['corrida']['capacitySource']='capacidad_ha.py; compatibilidad Python, no recorder OpenSees'
    p=output['p1l4']
    p['appliedLoads']=[]
    for case,loads in applied_cases.items():
        for key,values in loads.items():
            key=int(key)
            if len(values) not in (3,6) or not finite(values):raise ValueError('Carga prescrita inválida')
            p['appliedLoads'].append(dict(combo=case,targetId=abs(key),kind='elementUniformTotal' if key<0 else 'nodeForce',values=list(values),axes='model-global',source='carga_viva_sismo.apply_nodal_loads; vector total, uniforme dividido por L en solver'))
    p['caseStates']=[dict(name=c,state='Available',ok=True,forceCount=len(r['element_forces']),displacementCount=len(r['displacements']),appliedLoadCount=len(applied_cases[c])) for c,r in results.items()]
    for r in p['elementForces']+p['displacements']:r['status']='Available'
    p['reactions']=[]
    for case,r in results.items():
        for n,v in r.get('per_node_reactions',{}).items():
            if len(v)!=6 or not finite(v):raise ValueError('Reacción parcial')
            p['reactions'].append(dict(combo=case,node=int(n),f=list(v),status='Available'))
    by_index={}
    for e in output['elements']:
        if e['type']=='muro':
            if e['wallIndex'] in by_index:raise ValueError('Mapping analítico duplicado')
            by_index[e['wallIndex']]=e
    nodes={n['id']:n for n in output['nodes']}
    p['wallMappings']=[]
    for wall in output['walls']:
        e=by_index.get(wall['id'])
        if not e:raise ValueError('Muro sin elemento analítico')
        p['wallMappings'].append(dict(visualWallId=wall['id'],visualTag=wall['elementTag'],visualNodeI=wall['nodeI'],visualNodeJ=wall['nodeJ'],analyticalId=e['id'],analyticalTag=e['elementTag'],analysisNodeI=e['nodeI'],analysisNodeJ=e['nodeJ'],wallInPlaneAxis=e['wallInPlaneAxis'],bottomZ=min(nodes[e['nodeI']]['z'],nodes[e['nodeJ']]['z']),topZ=max(nodes[e['nodeI']]['z'],nodes[e['nodeJ']]['z'])))
    reference=Path(__file__).resolve().parents[1]/'data/part_e_wall.json'
    if reference.exists():
        ref=json.loads(reference.read_text(encoding='utf8'));curve=ref.get('Mphi_P0',{})
        if len(curve.get('curv',[]))!=len(curve.get('M',[])) or not finite(curve.get('curv',[])+curve.get('M',[])):raise ValueError('Referencia M-phi inválida')
        p['momentCurvatureReferences']=[dict(sectionId=ref['muro'],source='Proyecto1/data/part_e_wall.json',sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),method='Referencia histórica; integración de fibras Python del pipeline P1L3, no recorder del análisis global actual',curvatureUnit='1/m',momentUnit='kN*m',P_kN=0,L_m=ref['seccion_m']['L'],t_m=ref['seccion_m']['t'],armadura=json.dumps(ref['armadura'],ensure_ascii=False),curvature=curve['curv'],moment=curve['M'])]
    output['notes']=[n for n in output['notes'] if not n.startswith('Demandas muro:')]
    output['notes']+=['Muros: asociación visual/analítica explícita; fuerzas raw del elemento equivalente, demandas P-M en su plano según registro.', 'Sin estaciones solver: curvas de esfuerzos reconstruidas por equilibrio de las cargas uniformes exportadas.', 'Capacidad calculada en Python; curvas uniaxiales/referencias con hipótesis, no chequeo integral.', 'tributaryList legado: no utilizado en la nueva interfaz AR.']
    validate_bundle(output)

def section_at(f,t,length,w=0.0,axis=(1,0,0)):
    """Uniforme global -Z; ejes geomTransf, extremos raw inmutables."""
    import numpy as np
    x=np.asarray(axis,dtype=float);x=x/np.linalg.norm(x)
    vec=np.array((1,0,0) if abs(x[2])>.90 else (0,0,1),dtype=float)
    y=np.cross(vec,x);y/=np.linalg.norm(y);z=np.cross(x,y)
    out=[-(1-t)*f[k]+t*f[k+6] for k in range(6)]
    moment=-w*length**2*t*(1-t)/2*np.cross(x,(0,0,-1))
    out[4]+=float(moment@y);out[5]+=float(moment@z)
    return out

def pm_demand(f):
    # Columnas: contrato común con capacidad_ha; no confundir fuerzas raw con corte.
    return .5*(f[0]-f[6]),max(math.hypot(f[4],f[5]),math.hypot(f[10],f[11]))
