from pathlib import Path
import json
from collections import Counter
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text(encoding='utf-8-sig'))
C=read('common_hub_schema.json');R=read('region_schema.json');N=read('nation_schema.json');F=read('common_hub_function_spec.json')
registry={}
for p in C['export_contracts']+R['providers']:
 registry[(p['owner_file_code'],p['dataset_id'])]={'owner':p['owner_file_code'],'provider_id':p['dataset_id'],'source_tables':p['source_tables'],'primary_key':p['primary_key_fields'],'source_artifact':'common_hub_schema.json' if p['owner_file_code']=='C00' else 'region_schema.json'}
for p in N['provider_contracts']:
 registry[(p['file_code'],p['table_id'])]={'owner':p['file_code'],'provider_id':p['table_id'],'source_tables':[x['table_id'] for x in p['joins']],'primary_key':p['primary_key'],'source_artifact':'nation_schema.json'}
feed_extensions=read('change_feed_contracts.json') if (P/'change_feed_contracts.json').exists() else None
if feed_extensions:
 for p in feed_extensions['contracts']:
  registry[(p['owner_file_code'],p['dataset_id'])]={'owner':p['owner_file_code'],'provider_id':p['dataset_id'],'source_tables':p['source_tables'],'primary_key':p['primary_key_fields'],'source_artifact':'change_feed_contracts.json'}
cross_extensions=read('cross_domain_contract_extensions.json') if (P/'cross_domain_contract_extensions.json').exists() else None
if cross_extensions:
 for p in cross_extensions['provider_contracts']:
  registry[(p['owner_file_code'],p['dataset_id'])]={'owner':p['owner_file_code'],'provider_id':p['dataset_id'],'source_tables':p['source_tables'],'primary_key':p['primary_key_fields'],'source_artifact':'cross_domain_contract_extensions.json'}
for p in registry.values():
 p['dataset_id']=p['provider_id']
 p['table_id']=p['provider_id']
 p['owner_file_code']=p['owner']
def exact(owner,*ids):return [(owner,x) for x in ids]
def all_owner(owner):return [k for k,v in registry.items() if k[0]==owner and v['source_artifact'] in ('region_schema.json','nation_schema.json')]
M={
'C00.시간정책':exact('C00','PUB_CALENDAR_V2'),
'C00.사건대상관계':exact('C00','PUB_MANUAL_EVENTS_V2'),
'C00.지표사전':exact('C00','PUB_METRICS_V2'),
'R20.PUB_PLANET_POP_V2':exact('R20','PUB_PLANET_POPULATION_V2'),
'R60.PUB_PLANET_ECON_V2':exact('R60','PUB_PLANET_ECONOMY_V2'),
'N10.국가기본':exact('N10','PUB_NATION_V2'),
'N10.국호이력':exact('N10','PUB_NATION_NAME_HISTORY_V2'),
'N10.국호·수도·헌정 feed':exact('N10','PUB_NATION_NAME_HISTORY_V2','PUB_CAPITAL_HISTORY_V2','PUB_CONSTITUTION_HISTORY_V2'),
'N20.공직·선거·정당·기관 feed':exact('N20','PUB_OFFICE_TERM_V2','PUB_ELECTION_V2','PUB_ELECTION_RESULT_V2','PUB_PARTY_ROLE_TERM_V2','PUB_PARTY_RELATION_V2','PUB_INSTITUTION_HISTORY_V2','PUB_OFFICE_RELATION_V2','PUB_DISTRICT_RELATION_V2'),
'N30.황실·친족·승계 feed':exact('N30','PUB_ROYAL_STATUS_V2','PUB_KINSHIP_V2','PUB_SUCCESSION_V2'),
'N40.국가인구 제공':exact('N40','PUB_NATION_POPULATION_V2'),
'N50.국가경제 제공':exact('N50','PUB_NATION_ECONOMY_V2','PUB_ECONOMY_DERIVED_V2'),
'R50.영토변동 feed':exact('R50','PUB_REGION_NATION_RELATIONS_V2'),
'R10.지역목록·관계·시설·노선':all_owner('R10'),
'R20.인구관측':all_owner('R20'),
'R30.사회문화':all_owner('R30'),
'R40.종교분포':all_owner('R40'),
'R50.지역국가관계':all_owner('R50'),
'R60.경제산업':all_owner('R60'),
'R70.환경자원':all_owner('R70'),
'N10~N70 분야 제공표':[k for k,v in registry.items() if k[0] in ['N10','N20','N30','N40','N50','N60','N70'] and v['source_artifact']=='nation_schema.json'],
'N40.국가인구':exact('N40','PUB_NATION_POPULATION_V2'),
'R20.행성인구':exact('R20','PUB_PLANET_POPULATION_V2'),
'N50.국가경제':exact('N50','PUB_NATION_ECONOMY_V2'),
'R60.행성경제':exact('R60','PUB_PLANET_ECONOMY_V2'),
'R50.통치범위':exact('R50','PUB_REGION_NATION_RELATIONS_V2'),
'R70.행성물성':exact('R70','PUB_PLANET_PROPERTIES_V2'),
'N20.공직임기':exact('N20','PUB_OFFICE_TERM_V2','PUB_OFFICE_V2'),
'N30.인물·황실·승계':exact('N30','PUB_PERSON_V2','PUB_ROYAL_STATUS_V2','PUB_SUCCESSION_V2'),
'R10.지역':exact('R10','PUB_REGIONS_V2','PUB_REGION_RELATIONS_V2'),
'R20/N40 인구 범위':exact('R20','PUB_POPULATION_V2','PUB_PLANET_POPULATION_V2')+exact('N40','PUB_NATION_POPULATION_V2'),
'N30.황실신분':exact('N30','PUB_ROYAL_STATUS_V2','PUB_PERSON_V2'),
'N30.황위계승':exact('N30','PUB_SUCCESSION_V2'),
'N10.수도이력':exact('N10','PUB_CAPITAL_HISTORY_V2'),
'N10.헌정국체이력':exact('N10','PUB_CONSTITUTION_HISTORY_V2'),
}
if feed_extensions:
 for requested,resolved in feed_extensions['required_function_bindings'].items():
  owner,pid=resolved.split('.',1)
  M[requested]=exact(owner,pid)
missing_names={
'C00.루트정의':'루트정의',
'C00.데이터셋레지스트리':'데이터셋레지스트리',
'C00.파일레지스트리':'파일레지스트리',
'C00.범위레지스트리':'범위레지스트리',
'C00.이관레코드관계':'이관레코드관계',
}
bindings=[]
for fn in F['functions']:
 for requested in fn['required_datasets']:
  b={'function_id':fn['function_id'],'consumer_file_code':fn['owner_file_code'],'requested_dataset':requested,'provider_bindings':[],'local_tables':[],'operation_import_edge':False,'status':'미실행','test_ids':fn['test_ids']}
  if fn['owner_file_code']=='C00':
   if requested.startswith('C00.'):
    b.update(binding_kind='same_file_local',local_tables=[requested.split('.',1)[1]],note='동일 C00 내부 읽기. 외부 import 간선 없음.')
   else:
    b.update(binding_kind='migration_snapshot_comparison_only',note='PH0 보존 스냅샷/이관 명세 대조에만 사용. C00의 운영 외부 import로 구현하지 않음.')
    if requested in M:b['comparison_reference_providers']=[registry[k] for k in M[requested]]
    if requested.startswith('R70'):b['comparison_reference_providers']=[registry[('R70','PUB_PLANET_PROPERTIES_V2')]]
  elif requested.startswith('H90.'):
   b.update(binding_kind='same_file_local',local_tables=[requested.split('.',1)[1]],note='H90 자기수신/IMPORTRANGE 금지. 로컬 조회조건 또는 파생 결과 읽기.')
  elif requested in missing_names:
   table=missing_names[requested]
   available=[p for (o,pid),p in registry.items() if o=='C00' and table in p['source_tables']]
   if available:
    b.update(binding_kind='existing_declared_provider_contract',provider_bindings=available,operation_import_edge=True,note='추가된 C00 제공계약의 실제 source_tables를 대조하여 연결. 온라인 수신은 미실행.')
   else:
    b.update(binding_kind='missing_external_provider_contract',missing_owner='C00',missing_source_table=table,proposed_provider_id=None,note='C00 원본표는 명세에 존재하지만 해당 표를 외부 제공하는 PUB 계약은 현재 export_contracts에 없다. 기존 다른 PUB에 포함된 것으로 간주하거나 ID를 창작하지 않는다. PUB 계약 보완 전 외부 수신 미완료.')
  elif requested=='각 소유분야 검증제공':
   checks=[p for (o,pid),p in registry.items() if o!='H90' and pid.endswith('_CHECK_RESULTS_V2')]
   if len(checks)==15 and len({x['owner'] for x in checks})==15:
    b.update(binding_kind='existing_declared_provider_contract',provider_bindings=checks,operation_import_edge=True,note='15개 분야별 typed CHECK_RESULTS 제공계약에 연결. run_id/check_id/subject_count/actual/expected/evidence 등 상세 실행결과 스키마를 사용. 실제 실행결과는 0건 생성, 운영시험 미실행.')
   else:
    b.update(binding_kind='missing_detailed_validation_provider_contract',missing_owner='각 소유분야',note='기존 제공표 validation_status는 행 상태 요약일 뿐 check_id/run_id/subject_count/actual/expected/evidence가 있는 상세 검사결과 제공 계약이 아니다. 분야별 전용 검증 제공계약 및 실제 실행기록이 필요. H90 내부검사와 혼합하지 않음.')
  else:
   keys=M.get(requested)
   if keys is None and '.' in requested:
    owner,pid=requested.split('.',1)
    if (owner,pid) in registry:keys=[(owner,pid)]
   if keys is None:raise ValueError('Unresolved requested dataset '+requested)
   assert all(k in registry for k in keys)
   assert all(k[0]!='H90' for k in keys)
   b.update(binding_kind='existing_declared_provider_contract',provider_bindings=[registry[k] for k in keys],operation_import_edge=True,note='설계상 제공 ID만 확인. 실제 Google 파일ID/범위/권한/수신/재계산은 미실행.')
   if 'feed' in requested and not all(registry[k]['source_artifact']=='change_feed_contracts.json' for k in keys):
    b['binding_kind']='base_provider_bound_feed_contract_pending'
    b['note']='열거한 제공표로 원본 이력 범위는 특정했다. 소유분야 자동변동 feed의 feed_kind/source_record_id/변동종류/시간정밀도/중복키 투영계약은 별도 보완 필요. 현재 제공표를 완성 feed로 오인하지 않는다.'
   elif 'feed' in requested:
    b['note']='change_feed_contracts.json의 소유분야 경계/순간사건 typed 투영계약에 결합. 실제행·운영수신·온라인시험은 미실행.'
   if requested in ('R20.PUB_PLANET_POP_V2','R60.PUB_PLANET_ECON_V2'):
    b['alias_rule']='짧은 계획서 명칭을 실제 선언된 POPULATION/ECONOMY 제공 ID로 정정. 별도 중복 제공표 생성 금지.'
  bindings.append(b)
edges=sorted({(p['owner'],b['consumer_file_code']) for b in bindings if b['operation_import_edge'] for p in b['provider_bindings']})
assert all(a!=b and b=='H90' and a!='H90' for a,b in edges)
out={'project':'세계관 데이터 V2','status':'PH1 제공 명칭 대응 명세 · 실제 온라인 시험 미실행','binding_source':'common_hub_function_spec.json functions[].required_datasets','registry_sources':['common_hub_schema.json export_contracts','region_schema.json providers','nation_schema.json provider_contracts'],'bindings':bindings,'operating_provider_to_consumer_edges':[{'provider':a,'consumer':b} for a,b in edges],'rules':['C00 외부 operating import 0','H90 자기수신 0','H90를 소비하는 운영파일 0','명세 제공ID 존재는 실제 파일·범위·권한·재계산 성공 증거가 아님'],'summary':{'requested_dependencies':len(bindings),'binding_kind_counts':dict(Counter(x['binding_kind'] for x in bindings)),'operating_edge_count':len(edges),'unresolved_reference_strings':0,'online_tests_passed':0,'runtime_status':'미실행','missing_contracts_are_not_passes':True},'remaining_contract_gates':['C00 루트/데이터셋/파일/범위/이관관계 제공계약','각 분야 상세 검증 제공계약','각 분야 자동변동 feed 투영계약']}
if feed_extensions:
 out['registry_sources'].append('change_feed_contracts.json contracts')
 out['remaining_contract_gates'].remove('각 분야 자동변동 feed 투영계약')
if cross_extensions:
 out['registry_sources'].append('cross_domain_contract_extensions.json provider_contracts')
 if not any(b['binding_kind']=='missing_external_provider_contract' for b in bindings):out['remaining_contract_gates'].remove('C00 루트/데이터셋/파일/범위/이관관계 제공계약')
 if not any(b['binding_kind']=='missing_detailed_validation_provider_contract' for b in bindings):out['remaining_contract_gates'].remove('각 분야 상세 검증 제공계약')
out['summary']['missing_declared_contract_count']=sum('missing_' in b['binding_kind'] for b in bindings)
(P/'hub_dataset_bindings.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out['summary'],ensure_ascii=False,indent=2))
