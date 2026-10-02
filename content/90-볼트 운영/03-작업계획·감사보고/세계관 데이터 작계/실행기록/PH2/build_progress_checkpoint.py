from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, csv, hashlib, os, zipfile, sys
sys.stdout.reconfigure(encoding='utf-8')
P=Path(__file__).resolve().parent
B=P.parent
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
now=datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
state=read(B/'실행상태.json')
created={x['file_code']:x for p in sorted(P.glob('created_*.json')) for x in [read(p)]}
tests={x['file_code']:x for p in sorted(P.glob('test_created_*.json')) for x in [read(p)]}
with (B/'검증결과.csv').open(encoding='utf-8-sig',newline='') as f: results=list(csv.DictReader(f))
summary={s:sum(r['status']==s for r in results) for s in ['통과','실패','미실행']}
for c,x in created.items():
 x['build_status']='기본 구조 적용·헤더 검증; 기능 이관·운영시험 미완료'
 if c in ('C00','R10'): x['build_status']='기본 자료 이관·셀 대조 완료; 제공식·후속 기능·운영시험 미완료'
 if c in ('N60','N70'): x['build_status']='자료 없는 분야의 빈 구조·네이티브 표·범위 검증; 운영시험 미완료'
 save(P/f'created_{c}.json',x)
with (B/'파일레지스트리.csv').open(encoding='utf-8-sig',newline='') as f:
 reader=csv.DictReader(f); registry=list(reader); fieldnames=reader.fieldnames
for row in registry:
 if row['file_code'] in created:
  x=created[row['file_code']]; row.update(title=x['result']['title'],status=x['build_status'],note='PH2 체크포인트; 전체 기능·온라인 운영 검증 완료 아님')
with (B/'파일레지스트리.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=fieldnames); writer.writeheader(); writer.writerows(registry)
state.update(created_files=created,actual_operating_file_count=len(created),test_files={c:x['result'] for c,x in tests.items()},test_summary=summary,last_checkpoint=now)
state['phase']='PH2'
state['operating_transition_approved']=False
state['status']='PH2 기본 구조·기본 자료·소형시험 체크포인트 저장 · 사용자 종료 요청에 따라 중단'
state['h90_url']='https://docs.google.com/spreadsheets/d/'+created['H90']['result']['id']+'/edit#gid=1100202602'
state['safe_next_step']='실행상태와 16개 실제 ID·V1 수정 여부를 재확인. PH2 최종 감사와 소형시험 복구 증거를 먼저 읽고 단계 완료 기준을 판정한 뒤 PH3 지역 분야 자료·제공식 이관을 순서대로 진행. 이미 적용된 구조 49배치와 입력 20배치를 재실행하지 말 것. 구판 숨김 탭의 V1 주소·호환식은 보존용이며 V2 운영식으로 사용 금지. 실제 제공·소비 범위와 권한을 함께 검증.'
state['test_results']={'passed':summary['통과'],'failed':summary['실패'],'not_run':summary['미실행'],'passed_ids':[r.get('test_id',r.get('id')) for r in results if r['status']=='통과'],'note':'84개 인수시험과 TEST 소형시험 SF01~06은 별도 집계. 범위가 다른 시험을 자동 통과 처리하지 않음.'}
state['phase_status']['PH2']='16개 실제 파일 기본 구조 적용, 746행 이관, 14003개 헤더 대조 완료. 소형시험 결과·최종 감사 증거는 PH2에 저장. 전체 기능 구축 미완료.'
state['phase_status']['PH6']='84개 중 통과2/실패0/미실행82; 별도 소형시험 결과는 SF 증거에 기록'
state['field_inventory']['migrated_records']=746
state['specification']['scope']='1539개 관측 필드 대응 명세. 16개 기본 구조 헤더 검증과 C00/R10 746행 실제 이관 완료; 전분야 행별 이관·운영식 검증은 미완료.'
state['pending_tasks']=['PH2 소형시험·최종 구조 감사 증거에 따른 단계 종료 판정','PH3~PH7 분야별 자료·수식·연결·H90 기능 이관과 84개 인수시험','구판 보존 탭의 운영식 의존 제거 확인','기준 첨부 XLSX 확보 시 역사적 셀차분 검증; 현재 미검증 예외 보존','별도 운영 전환 승인']
for b in state.get('blocked_tasks',[]):
 if b.get('id')=='B-001':
  b['historical_question']=b.pop('user_question',''); b['next_action']='첨부 XLSX가 나중에 제공되면 당시 온라인 스냅샷과 셀차분 검증. 현재 후속 진행지시가 적용되었으며 재승인 질문 대상 아님.'
state['current_checkpoint_file']='WORLD-DATA-V2_PH2_checkpoint.zip'
state['stop_reason']='사용자 요청: 5분 내 저장·종료. 백그라운드 작업 없이 다음 지시에서 재개.'
state['v1_current_metadata_evidence']='PH2/source_integrity_after.json'
state['completed_tasks']+=['PH2 16개 실제 파일·233개 기본구조 탭 적용 및 14003개 기술 헤더 대조','C00/R10 746행 6313개 입력 셀 값·유효값·메모 일치 및 미기입 6782셀 보존','H90 실제 16개 파일 목차 제공; V1 쓰기0']
state['ph2_evidence']={'headers':'PH2/manifest/native_read_verification.json','inputs':'PH2/input_execution/input_cell_verification.json','test_directory':'PH2/small_flow_execution','metadata_audit_directory':'PH2/manifest','decision_queue':'PH2/input_requests/pending.json','test_scope':'소형 TEST 파일 전용; 16개 운영 전체 시험 대체 아님'}
sf=read(P/'small_flow_execution/execution_summary.json')
state['small_flow_test_summary']={k:sf.get(k) for k in ['api_passed_cases','api_failed_cases','api_incomplete_cases','generated_at']}
state['small_flow_test_summary']['evidence']='PH2/small_flow_execution/execution_summary.json'
state['current_scope_limit']='16개는 실제 생성된 운영 대상 파일 수. 구판 사본 탭 정리/기능이관/연결/검증이 남은 파일을 운영완료로 세지 않음.'
save(B/'실행상태.json',state)
report={
 'checked_at':now,'status':state['status'],'phase':'PH2','operating_target_count':len(created),'operating_ready_count':state.get('operating_ready_count',0),
 'files':[{'file_code':c,'title':x['result']['title'],'id':x['result']['id'],'url':x['result']['url'],'status':x.get('build_status')} for c,x in created.items()],
 'test_files':[{'file_code':c,**x['result']} for c,x in tests.items()],
 'test_summary':summary,'scope':'파일 생성, 별도 V2 기본구조, C00/R10 기본자료 및 소형 연결시험 단계. 실제 완료는 개별 실행증거 기준.',
 'baseline_exception':'역사적 첨부 XLSX 부재로 셀차분 미검증. 후속 사용자 진행지시를 온라인 보존스냅샷 기반 기술 구축에 적용. 첨부본 동일성/운영전환 승인 아님.',
 'canonical_pending':['상위 지역 gal.1 실제 개체 없음; sec.1 원문 상위이름 보존','기준 중복 4그룹 8판본 보존·자동채택 제외','달력 대응 미결 5후보 및 PK 의미대응 미결 설정 보존','국가명 N10 단일 입력: C00 neutral_name 미입력, 원문 계보 보존','일부 기술 필드의 한국어 표시명 검토 필요'],
 'preservation':'V1에는 읽기만 수행. 작업 전후 원본 수정시각·권한·부모 동일 확인; 이번 말미 증거 PH2/source_integrity_after.json. 기존 네이티브/XLSX 백업과 원문·발급원장 보존. V2 구판 사본 탭은 숨김 보존이며 과거 수식이 남아 있어 V1 의존 제거 완료 아님.',
 'achievements':{'operating_files':16,'new_schema_tabs':233,'technical_headers_verified':14003,'source_rows_migrated':746,'input_cells_verified':6313,'preserved_unwritten_cells':6782,'decision_work_items':62},
 'small_flow_evidence':'PH2/small_flow_execution — SF01~06 별도 API 결과 및 복구 증거. 84개 시험 자동 통과 처리 없음.',
 'small_flow_summary':state['small_flow_test_summary'],
 'backup_folder':'https://drive.google.com/drive/folders/1LaoWsUZnNs-fGDOkfq_gO3fdvkCu4jo9',
 'checkpoint_folder':'https://drive.google.com/drive/folders/1-bKopCrg7nkDtAEJXlRMCWcs2JseOJCE',
 'h90_url':state['h90_url'],'safe_next_step':state['safe_next_step']}
save(B/'진행보고.json',report)
lines=['세계관 데이터 V2 진행보고',now,report['status'],'',f"실제 생성 파일 {len(created)}/16 · 운영준비 완료 {report['operating_ready_count']} · 시험 통과 {summary['통과']} / 실패 {summary['실패']} / 미실행 {summary['미실행']}",'파일 생성은 기능·검증 완료를 의미하지 않습니다.','']
for x in report['files']: lines += [x['title'],x['url'],x['status'] or '구축 중','']
lines += ['이번 이관·검증','C00/R10 원문 746행 / 입력6313셀 대조 일치 / 미기입6782셀 보존','16파일 기술 헤더14003개 대조. 기본 구조233탭과 지원 목차·결정대기표 적용.','62개 결정대기 작업 항목 보존. SF01~SF06 소형시험은 84개 인수시험과 별도.','소형시험 상세·복구: PH2/small_flow_execution','H90 진입',report['h90_url'],'','미해결 정본·검증 쟁점',*report['canonical_pending'],'',report['baseline_exception'],'',report['preservation'],'','백업·복구',report['backup_folder'],'실행기록',report['checkpoint_folder'],'','다음 안전한 단계',report['safe_next_step']]
lines += ['',f"소형시험 API 통과 {sf.get('api_passed_cases')} / 실패 {sf.get('api_failed_cases')} / 미완료 {sf.get('api_incomplete_cases')}",'사용자 종료 요청에 따라 다음 단계는 시작하지 않음. 전체 기술 구축 및 운영 전환 미완료.']
(B/'진행보고.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
archive=B/'WORLD-DATA-V2_PH2_checkpoint.zip'
manifest=[]
for root,dirs,files in os.walk(B,followlinks=False):
 dirs[:]=[d for d in dirs if d not in {'node_modules','.git','__pycache__'} and not os.path.islink(os.path.join(root,d)) and not getattr(os.path,'isjunction',lambda p:False)(os.path.join(root,d))]
 for name in files:
  f=Path(root)/name
  if f.suffix.lower() in {'.zip','.log','.tmp'} or name.endswith('.inspect.ndjson') or name in {'PH2_checkpoint_manifest.json'}: continue
  manifest.append({'path':f.relative_to(B).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)})
manifest.sort(key=lambda x:x['path'])
save(B/'PH2_checkpoint_manifest.json',{'checked_at':now,'files':manifest,'rule':'No junction traversal; no recursive old ZIP inclusion; hashes refer to files in this archive.'})
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for x in manifest:z.write(B/x['path'],x['path'])
 z.write(B/'PH2_checkpoint_manifest.json','PH2_checkpoint_manifest.json')
with zipfile.ZipFile(archive) as z: assert z.testzip() is None
verification={'checked_at':now,'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'files':len(manifest)+1,'test_summary':summary,'file_count':len(created),'state_sha256':sha(B/'실행상태.json'),'report_sha256':sha(B/'진행보고.txt')}
save(P/'checkpoint_verification.json',verification)
print(json.dumps(verification,ensure_ascii=False))
