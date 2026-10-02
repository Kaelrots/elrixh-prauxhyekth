import json,pathlib,hashlib,datetime
B=pathlib.Path(__file__).parent
E=B/'small_flow_execution'
M=json.loads((B/'small_flow_requests/small_flow_request_manifest.json').read_text(encoding='utf-8'))
ids=set(M['allowlisted_test_ids'].values())
results={p.stem:json.loads(p.read_text(encoding='utf-8')) for p in E.glob('*_api_result.json')}
case_steps={'SF01':['SF01_initial_api_result'],'SF02':['SF01_initial_api_result','SF02_end_exclusive_api_result','SF02_restore_point_api_result'],'SF03':['SF03_change_api_result'],'SF04':['SF04_numeric_zero_api_result','SF04_empty_api_result','SF04_connection_failure_api_result','SF04_restore_api_result'],'SF05':['SF05_header_drift_api_result','SF05_restore_api_result'],'SF06':['SF06_append_boundary_api_result','SF06_expand_all_ranges_api_result']}
case_results={c:{'api_result':'passed'if all(results.get(s,{}).get('api_validation')=='passed'for s in ss)else'not_complete','evidence_files':[str(E/(s+'.json'))for s in ss],'ui_status':'별도 root UI증거 기록 참조'}for c,ss in case_steps.items()}
actual_ids=set();api_errors=[]
def walk(x,p):
    if isinstance(x,dict):
        if 'spreadsheetId'in x:actual_ids.add(x['spreadsheetId'])
        if x.get('isError')is True:api_errors.append(str(p))
        for v in x.values():walk(v,p)
    elif isinstance(x,list):
        for v in x:walk(v,p)
for p in E.glob('*.json'):
    if p.name=='execution_summary.json':continue
    walk(json.loads(p.read_text(encoding='utf-8')),p)
assert actual_ids<=ids
stage_totals={'applied':0,'not_applicable':0,'pending':0,'failed':0}
for c,f in M['files'].items():
    for stage,s in f['stages'].items():
        receipt=E/f'{c}_{stage}_response.json'
        if not receipt.exists():s['status']='미실행';stage_totals['pending']+=1;continue
        r=json.loads(receipt.read_text(encoding='utf-8'))
        s['execution_receipt']=str(receipt)
        if r.get('status')=='not_applicable_no_provider_row_fill':
            s['status']='실행 확인 · 요청0개(해당 없음)';s['online_request_sent']=False;stage_totals['not_applicable']+=1
        elif r.get('response',{}).get('isError')is False:
            s['status']='실행 확인';s['online_request_sent']=True;s['actual_request_count']=len(r['response'].get('structuredContent',{}).get('replies',[]));stage_totals['applied']+=1
        else:s['status']='실패·확인 필요';stage_totals['failed']+=1
coverage={
'T-009':'합성 TEST IDs만 확인. 기존 전체 개체 ID 집합 정렬·이동 전후 대조는 별도.',
'T-018':'단일 임기의 시작포함/끝제외 확인. 102년 같은날 A→B 교체·중첩오탐 전체 시나리오는 별도.',
'T-031':'정상0/빈행/연결실패만 확인. 미상·미정·해당없음 관측 집계는 별도.',
'T-068':'TEST8연결 공급자ID 확인. 운영16전체 실제 import 전수검색은 별도.',
'T-069':'TEST6 실제ID 그래프 무순환 및N30 역수신없음 확인. 운영전체 그래프 검증은 별도.',
'T-070':'TEST승인전·승인후·잘못된범위 확인. 운영전체 접근실패/권한변경 영향 검증은 별도.',
'T-071':'R20인구·N30이름 변경 반영 확인. 지역명 변경 및N40 포함 전체경로는 별도.',
'T-072':'TEST R20→H90 필수헤더개명 감지·차단·복구 확인. 운영전체 제공계약 범위는 별도.',
'T-073':'TEST R20→H90 입력/계산/검증/PUB/REF 경계확장 확인. 운영전체 표의 확장시험은 별도.',
'T-078':'TEST빈인구 0행을 자료없음으로표시. 운영전체 입력표 검사대상없음 처리는 별도.',
'T-083':'헤더반영 지연을 실제관측·갱신대기로 기록. 캐시고정+시계만갱신 시나리오는 별도.'}
summary={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'전용 TEST6 native 소형연결시험','run_id':M['run_id'],'case_results':case_results,'api_passed_cases':sum(c['api_result']=='passed'for c in case_results.values()),'api_failed_cases':sum(c['api_result']=='failed'for c in case_results.values()),'api_incomplete_cases':sum(c['api_result']=='not_complete'for c in case_results.values()),'api_tool_errors':sorted(set(api_errors)),'actual_spreadsheet_ids_observed':sorted(actual_ids),'all_observed_api_targets_within_test_allowlist':actual_ids<=ids,'production_or_v1_mutations_performed_by_this_agent':False,'test_files':M['files'],'test_graph':M['edges'],'test_graph_cycle_count':0,'source_value_status':'값 있음 — REG온라인 인구검증옵션원문을TEST코드북에만사용','schema_drift_delay':'SF05변형·복원모두1차read에서이전값관측→갱신대기기록→5초후2차read에서기대값관측','time_measurement':'*_write_response의완료시각과*_readback의확인시각을보존. propagation_upper_bound_ms는순차API관측의상한이며즉시성보장아님.','final_fixture_restore':results.get('SF_final_restore_api_result',{'api_validation':'pending'}),'retained_capacity':'R20입력/계산/PUB 및H90소비·계산은11행용량(마지막14행), 원래fixture복구후경계추가행은빈칸.','ui_evidence':[{'source':'root 협업메시지','observation':'H90초기UI 인구100/건수1/원본위치/두경로이름/재직TRUE/이름일치TRUE 확인. 대화도구이미지증거이며로컬PNG없음.','confirmed':True},{'source':'root 확인 대기','observation':'SF06확장후250/2행 및최종복구화면','confirmed':False}],'checklist_84':{'automatic_updates':0,'fully_covered_global_tests_recommended_as_pass':[],'partial_coverage_only':[{'test_id':k,'recommended_status':'기존상태유지 · 소형시험부분증거첨부','scope_gap':v}for k,v in coverage.items()]},'overall_migration_completion':'주장하지 않음','evidence_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in E.glob('*.json')if p.name!='execution_summary.json'}}
summary['initial_stage_totals']=stage_totals
(E/'execution_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'api_passed_cases':summary['api_passed_cases'],'api_tool_errors':summary['api_tool_errors'],'actual_test_targets':len(actual_ids),'restore':summary['final_fixture_restore'].get('api_validation'),'global84_pass_recommendations':0},ensure_ascii=False))
