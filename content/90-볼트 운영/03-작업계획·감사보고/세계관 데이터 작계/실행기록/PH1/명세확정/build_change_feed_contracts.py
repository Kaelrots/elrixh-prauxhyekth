from pathlib import Path
import json
P=Path(__file__).resolve().parent
N=json.loads((P/'nation_schema.json').read_text(encoding='utf-8-sig'))
R=json.loads((P/'region_schema.json').read_text(encoding='utf-8-sig'))
nt={(t['file_code'],t['table_id']):t for t in N['tables']}
rt={(t['file_code'],t['table_id']):t for t in R['tables']}
common_fields=[
 ('feed_id','text_id',True),('source_file_code','text',True),('source_dataset_id','text',True),('source_table_id','text',True),('source_record_id','text_id',True),('feed_kind','text',True),('change_kind','enum',True),('temporal_kind','enum',True),('source_boundary','enum',True),('nation_id','text_id_nullable',False),('region_id','text_id_nullable',False),('person_id','text_id_nullable',False),('subject_refs_json','json_text_nullable',False),('route','text_nullable',False),('calendar_revision','text_nullable',False),('era','text_nullable',False),('year','integer_nullable',False),('month','integer_nullable',False),('day','integer_nullable',False),('date_precision','enum',True),('date_raw','text_nullable',False),('date_resolution_status','enum',True),('end_status','text_nullable',False),('display_date_text','text',False),('display_change_text','text',False),('boundary_semantics','enum',True),('setting_status','text_nullable',False),('adoption_status','text_nullable',False),('generation_method','enum',True),('validation_status','text',True),('source_id','text_id_nullable',False),('source_locator','text_nullable',False),('legacy_locator','text_nullable',False),('source_record_url','url_nullable',False),('source_snapshot_id','text_nullable',False),('schema_version','text',True),('release_id','text_nullable',False),('source_revision','text_nullable',False),('checked_at','timestamp_nullable',False),('duplicate_group_id','text_nullable',False)]
schema=[{'field_id':f,'type':ty,'required':req} for f,ty,req in common_fields]
contracts=[]
def interval(owner,ds,kind,subjects):
 t=nt[(owner,'IN_'+ds)] if owner!='R50' else rt[('R50','지역국가관계')]
 table=t['table_id'];pk=t['record_key'] if owner!='R50' else t['primary_key_fields'][0]
 fs={f.get('field_id',f.get('field')) for f in t['fields']}
 result={'source_table_id':table,'source_dataset_id':ds,'source_primary_key':pk,'source_owner':owner,'mode':'interval_boundaries','feed_kind':kind,'subject_bindings':{f:f for f in subjects if f in fs},'projections':[],'status':'명세만; 실제행 미생성'}
 for boundary in ('start','end'):
  y=f'{boundary}_year'
  assert y in fs,(owner,ds,y)
  date={part:(f'{boundary}_{part}' if f'{boundary}_{part}' in fs else None) for part in ('era','year','month','day','precision')}
  date['era_context']='era' if 'era' in fs else None
  date['raw']=f'{boundary}_raw' if f'{boundary}_raw' in fs else None
  result['projections'].append({'change_kind':f'{kind}_{boundary}','source_boundary':boundary,'temporal_kind':'interval_boundary','date_bindings':date,'end_status_field':'end_status' if 'end_status' in fs else None,'emit_condition':'실제 원본행 PK 및 해당 경계의 명시 연도 또는 명시 원문 날짜가 있을 때만 파생. 공란/기본FALSE/계산 query_end_year는 경계 근거가 아니다.','boundary_semantics':'start_inclusive' if boundary=='start' else 'end_exclusive_if_exact_otherwise_uncertain'})
 return result
def instant(ds,kind,datefields,subjects):
 t=nt[('N20','IN_'+ds)];fs={f['field_id'] for f in t['fields']}
 assert all(f in fs for f in datefields.values())
 return {'source_table_id':t['table_id'],'source_dataset_id':ds,'source_primary_key':t['record_key'],'source_owner':'N20','mode':'recorded_instant','feed_kind':kind,'subject_bindings':{f:f for f in subjects if f in fs},'projections':[{'change_kind':kind,'source_boundary':'instant','temporal_kind':'instant_event','date_bindings':datefields,'emit_condition':'실제 사건/관계변경 원본행과 명시된 사건일시만 사용. 주기·예정·제도만으로 선거 또는 변경사건 생성 금지. 날짜 원문이 없으면 날짜미상 진단 경로로 보존하고 임의 날짜 생성 금지.','boundary_semantics':'recorded_instant_precision_only'}],'status':'명세만; 실제행 미생성'}
specs={
'N10':[interval('N10','NATION_NAME_HISTORY','nation_name',['nation_id']),interval('N10','CAPITAL_HISTORY','capital',['nation_id','capital_region_id']),interval('N10','CONSTITUTION_HISTORY','constitution',['nation_id'])],
'N20':[interval('N20','OFFICE_TERM','office_term',['nation_id','office_id','person_id','party_id']),interval('N20','INSTITUTION_HISTORY','institution',['nation_id','office_id','parent_office_id']),interval('N20','PARTY_ROLE_TERM','party_role_term',['nation_id','party_id','person_id','party_role_id','faction_id']),interval('N20','PARTY','party_lifetime',['nation_id','party_id']),interval('N20','PARTY_FACTION','party_faction',['nation_id','party_id','faction_id']),instant('ELECTION','election',{'era':'era','year':'year','month':'월','day':'일'},['nation_id','election_id','office_id','system_id']),instant('PARTY_RELATION','party_relation_change',{'era':'era','year':'effective_year','month':'effective_month','day':'effective_day'},['nation_id','predecessor_party_id','successor_party_id']),instant('DISTRICT_RELATION','district_relation_change',{'era':'era','year':'effective_year','month':'effective_month','day':'effective_day'},['nation_id','predecessor_district_id','successor_district_id'])],
'N30':[interval('N30','ROYAL_STATUS','royal_status',['nation_id','person_id','related_emperor_person_id','related_term_id']),interval('N30','KINSHIP','kinship',['nation_id','subject_person_id','object_person_id']),interval('N30','SUCCESSION','succession',['nation_id','person_id','emperor_person_id','emperor_term_id'])],
'R50':[interval('R50','REGION_NATION_RELATIONS','region_nation_relation',['nation_id','region_id','planet_scope_id'])]
}
for owner,projections in specs.items():
 contracts.append({'owner_file_code':owner,'dataset_id':f'PUB_{owner}_CHANGE_FEED_V2','table_id':f'PUB_{owner}_CHANGE_FEED_V2','consumer_file_codes':['H90'],'source_tables':[x['source_table_id'] for x in projections],'primary_key_fields':['feed_id'],'column_schema':schema,'source_projection_contracts':projections,'schema_version':'V2.PH1.change-feed.1','owner_spreadsheet_id':None,'export_range':None,'release_id':None,'implementation_status':'미실행','fact_rows_created':0,'feed_rows_created':0,'input_allowed':False,'source_single_owner_rule':'원본 사실은 source_owner에서 한 번만 입력. 제공 feed는 파생 읽기전용이며 H90/C00/다른 분야 입력표로 되써넣지 않는다.','id_rule':'feed_id는 owner + dataset_id + 원본 PK + change_kind + source_boundary의 튜플로 결정. 원본 날짜/표시명/행위치/스냅샷 변경은 새 역사사건 ID를 생성하는 이유가 아니다. 튜플 인코딩 규칙과 충돌 검사를 고정한다.','consumer_edge':{'provider':owner,'consumer':'H90'},'scope_note':'공직 term_id는 N20만. N30 관련 term_id는 값 연결뿐이며 이 feed 계산도 N20를 import하지 않는다.'})
rules=[
 {'rule_id':'FEED-01','rule':'원본 기간 기록의 시작/종료 경계 표시와 순간 사건을 temporal_kind로 구별. 신설·폐지·박탈·복권 등 세계관 사건의 구체 의미는 원문 사유/코드가 있을 때만 표시하며 start/end라는 기술 경계에서 추정하지 않는다.'},
 {'rule_id':'FEED-02','rule':'정확 종료는 [시작,종료) 경계. 종료연도만 있는 기록은 연간 마지막 유효 연도를 보존하며 그해 48월30일이나 다음해 1월1일 사건으로 바꾸지 않음. 종료미상/지속중의 계산 유효종료연도는 역사종료사건으로 내보내지 않음.'},
 {'rule_id':'FEED-03','rule':'date_precision은 원문으로 확인된 day/month/year/raw_only/unknown. 연도만 있으면 month/day 공란. 원문기년 era와 명시 start_era/end_era를 우선순위로 표시하되 시작과 다른 종료기년을 복사추정하지 않으며 calendar_revision 미대응이면 cross-era 절대정렬 보류.'},
 {'rule_id':'FEED-04','rule':'R50 start_raw/end_raw는 원문 그대로 date_raw에 포함. 근거 없는 문자열 파싱·부분통치확대·영유권주장→실제통치 변환 금지. relation_type과 applied_scope의 원문을 표시문구 또는 원본 이동으로 확인할 수 있게 한다.'},
 {'rule_id':'FEED-05','rule':'연중 순서가 미상인 기록은 같은 연도 묶음으로 표시. UI 정렬을 위한 안정적 PK 순서는 역사상 선후관계가 아님. 서로 다른 루트/기년판본은 섞지 않음.'},
 {'rule_id':'FEED-06','rule':'source_record_url은 실제 V2 파일 ID와 표 위치·고정 record_id 매핑이 확인된 후 생성. 아직 실제파일이 없으면 URL은 공란/미생성. V1 주소는 운영feed 원본링크 대신 보존 evidence로만 분리.'},
 {'rule_id':'FEED-07','rule':'source PK당 한 경계 종류 한 feed행. 원본 사실이 다른 표에도 중복 표현됐다고 이름/날짜로 삭제하지 않음. 확인된 사실 대응으로 duplicate_group_id를 표시하고 출처를 유지. C00 수동사건과 feed 동시존재도 같은 원칙.'},
 {'rule_id':'FEED-08','rule':'입력값 없음·원문 날짜미상·잘못된 날짜·참조미검증·연결실패를 분리. checked_at는 실제 실행시각만. 현재 계약 작성은 행 생성/재계산/인수시험 통과를 뜻하지 않음.'},
 {'rule_id':'FEED-09','rule':'원본표의 명시 event_id가 있는 경우 source subject 참조로 유지하지만 feed_id를 새로운 수동 event_id로 발급하지 않는다. election_id는 이미 존재한 선거 사건의 투영이지 새로운 선거 생성이 아니다.'}
]
obj={'project':'세계관 데이터 V2','status':'PH1 변동feed 투영계약 · 미구현·미실행','contracts':contracts,'common_projection_rules':rules,'test_ids':['T-009','T-010','T-013','T-018','T-019','T-020','T-021','T-023','T-025','T-051','T-061','T-064','T-067','T-069','T-080'],'required_function_bindings':{'N10.국호·수도·헌정 feed':'N10.PUB_N10_CHANGE_FEED_V2','N20.공직·선거·정당·기관 feed':'N20.PUB_N20_CHANGE_FEED_V2','N30.황실·친족·승계 feed':'N30.PUB_N30_CHANGE_FEED_V2','R50.영토변동 feed':'R50.PUB_R50_CHANGE_FEED_V2'},'static_validation':{'contracts':4,'source_tables':sum(len(c['source_tables']) for c in contracts),'source_keys_and_date_fields_checked':True,'self_imports':0,'outbound_consumers':['H90'],'actual_rows_created':0,'online_tests_passed':0}}
(P/'change_feed_contracts.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(obj['static_validation'],ensure_ascii=False))
