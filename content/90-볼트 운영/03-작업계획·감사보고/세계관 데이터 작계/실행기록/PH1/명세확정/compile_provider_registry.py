from pathlib import Path
from collections import Counter, defaultdict
import json, sys, copy
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parent
def read(name): return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
def write(name,obj): (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

providers=[]
sources=[(part,read(part+'_schema.json')[key]) for part,key in [('region','providers'),('nation','provider_contracts'),('common_hub','export_contracts')]]
for filename in ['cross_domain_contract_extensions.json','change_feed_contracts.json']:
    if (ROOT/filename).exists():
        ext=read(filename)
        sources.append((filename,ext.get('contracts',ext.get('provider_contracts',ext.get('providers',[])))))
for part,contracts in sources:
    for raw in contracts:
        p=copy.deepcopy(raw)
        if part=='nation':
            p['logical_dataset_alias']=p['dataset_id']
            p['dataset_id']=p['table_id']
            p['owner_file_code']=p['file_code']
            p['source_tables']=[j['table_id'] for j in p['joins']]
            p['primary_key_fields']=p['primary_key']
        p['spec_part']=part
        p['consumer_scope']='local_display_only' if p['owner_file_code']=='H90' else 'downstream_import'
        for key in ['owner_spreadsheet_id','release_id','source_revision','export_range','record_count','coverage','route','era','validation_status','checked_at']:
            p.setdefault(key,None)
        p.setdefault('schema_version',f'PH1-{part}-1')
        p.setdefault('status_policy','자료없음/미입력/초안/미채택/부분/연결오류/미실행을 별도 표시; 오류를0으로 은폐하지 않음')
        p['implementation_status']='미실행'
        p['runtime_binding_status']='실제 파일·탭·범위 미생성'
        p['technical_headers']=[c.get('field_id',c.get('field','')) for c in p.get('column_schema',[])]
        providers.append(p)

errors=[]
for p in providers:
    pk=p['primary_key_fields']
    fields=p['technical_headers']
    if not p.get('column_schema'): errors.append({'dataset':p['dataset_id'],'problem':'column_schema_missing'})
    if set(pk)-set(fields): errors.append({'dataset':p['dataset_id'],'problem':'pk_not_in_headers','missing':sorted(set(pk)-set(fields))})
    duplicate=[k for k,n in Counter(fields).items() if n>1]
    if duplicate: errors.append({'dataset':p['dataset_id'],'problem':'duplicate_headers','fields':duplicate})
    for c in p.get('column_schema',[]):
        if not c.get('type',c.get('data_type')): errors.append({'dataset':p['dataset_id'],'problem':'column_type_missing','field':c})
counts=Counter(p['dataset_id'] for p in providers)
if any(n>1 for n in counts.values()): errors.append({'problem':'duplicate_dataset_ids','ids':[k for k,n in counts.items() if n>1]})

design=json.loads((ROOT.parent/'dependency_design.json').read_text(encoding='utf-8-sig'))
edges={(e['provider'],e['consumer']) for e in design['edges']}
for consumer,rule in read('nation_schema.json')['dependencies'].items():
    for provider in rule['required']+rule['optional']:
        if (provider,consumer) not in edges: errors.append({'problem':'nation_dependency_not_in_design','provider':provider,'consumer':consumer})
nodes=sorted({x for edge in edges for x in edge})
indegree=Counter(c for p,c in edges)
queue=sorted(n for n in nodes if indegree[n]==0)
order=[]
while queue:
    n=queue.pop(0); order.append(n)
    for p,c in sorted(edges):
        if p==n:
            indegree[c]-=1
            if indegree[c]==0: queue.append(c);queue.sort()
for p,c in sorted(edges):
    if c=='C00' or p=='H90' or (p,c)==('N20','N30'): errors.append({'problem':'forbidden_dependency','provider':p,'consumer':c})
if len(order)!=len(nodes): errors.append({'problem':'dependency_cycle','unresolved_nodes':sorted(set(nodes)-set(order))})

aliases={}
for p in providers:
    aliases[p['owner_file_code']+'.'+p['dataset_id']]=p['dataset_id']
    if p.get('logical_dataset_alias'): aliases[p['owner_file_code']+'.'+p['logical_dataset_alias']]=p['dataset_id']
if (ROOT/'hub_dataset_bindings.json').exists():
    bindings=read('hub_dataset_bindings.json')
    registered={p['dataset_id']:p for p in providers}
    for b in bindings['bindings']:
        if 'missing' in b['binding_kind'] or 'pending' in b['binding_kind']:
            errors.append({'problem':'hub_binding_contract_unresolved','function':b['function_id'],'requested':b['requested_dataset'],'kind':b['binding_kind']})
        for binding in b.get('provider_bindings',[]):
            did=binding.get('dataset_id',binding.get('provider_id',''))
            if did not in registered and binding.get('table_id') in registered:
                did=binding['table_id']
            if did not in registered:
                errors.append({'problem':'hub_binding_provider_missing','function':b['function_id'],'binding':binding})
            elif b.get('operation_import_edge'):
                owner=registered[did]['owner_file_code'];consumer=b['consumer_file_code']
                if owner!=consumer and (owner,consumer) not in edges:
                    errors.append({'problem':'hub_binding_edge_not_allowed','provider':owner,'consumer':consumer})
write('provider_registry.json',{
    'status':'명세 통합; 운영 제공범위·권한·재계산 미검증',
    'providers':providers,'dataset_aliases':aliases,
    'runtime_metadata_note':'null은 아직 관측되지 않음. record_count null을 실제0건으로 해석하지 않는다. H90 계약은 로컬 표시만 가능하고 소비파일이 import할 수 없다.',
    'static_errors':errors,
    'counts':{'contracts':len(providers),'external_providers':sum(p['consumer_scope']=='downstream_import' for p in providers),'H90_local_views':sum(p['consumer_scope']=='local_display_only' for p in providers),'static_errors':len(errors)}
})
write('dependency_registry.json',{
    'status':'정적 연결 설계; 실제 file ID/range graph 미구현',
    'direction':'provider to consumer',
    'nodes':nodes,
    'edges':[dict(provider=p,consumer=c,provider_file_id=None,consumer_file_id=None,implemented=False) for p,c in sorted(edges)],
    'topological_order':order,'design_cycle_count':0 if len(order)==len(nodes) else None,
    'actual_graph_cycle_count':None,
    'constraints':{'C00_imports_none':True,'H90_is_not_a_provider':True,'N30_never_imports_N20':True,'office_person_period_reverse_validation':'H90'},
    'edge_count':len(edges),'static_errors':errors
})
print(json.dumps({'provider_count':len(providers),'edge_count':len(edges),'design_cycle_count':0 if len(order)==len(nodes) else None,'error_count':len(errors),'first_errors':errors[:8]},ensure_ascii=False))
