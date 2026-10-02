from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
import json, csv, hashlib, zipfile, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
PLAN=BASE.parent
SPEC=BASE/'PH1'/'명세확정'
RESUME=BASE/'재개01'
NOW=datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def save(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csvread(path):
    with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def csvwrite(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

audit=read(SPEC/'integrated_spec_audit.json')
providers=read(SPEC/'provider_registry.json')
graph=read(SPEC/'dependency_registry.json')
assert audit['source_field_count']==1539 and audit['error_count']==0
assert not providers['static_errors'] and graph['design_cycle_count']==0
for name in ['실행상태.json','진행보고.json','진행보고.txt','파일레지스트리.csv']:
    backup=RESUME/(Path(name).stem+'_재개전'+Path(name).suffix)
    if not backup.exists(): shutil.copyfile(BASE/name,backup)

state=read(BASE/'실행상태.json')
resume=read(RESUME/'resume_verification.json')
end_checks=[]
for short,code in [('REG','REG-V1'),('NAT','NAT-V1')]:
    end=read(RESUME/(short+'_drive_end.json'))
    old=state['source_snapshot_ids'][code]
    same={k:end.get(k)==old.get(k) for k in ['id','title','modified_time','parent_ids','permissions']}
    assert all(same.values()), (code,same)
    end_checks.append({'source':code,'metadata_equal':True,'fields':same,'end_evidence':f'재개01/{short}_drive_end.json'})
save(RESUME/'v1_resume_unchanged.json',{
    'checked_at':NOW,'v1_write_actions':0,'metadata_checks':end_checks,
    'sheet_metadata_rechecked_at_resume':True,
    'full_content_reexport_this_resume':False,
    'previous_full_content_check':'PH0/T-002_evidence.json; PH1/canonical_start_end_comparison.json',
    'scope':'이번 재개는 읽기·로컬명세작성·감사파일 갱신. 원본 수정시각/제목/부모/권한은 전후 동일. 이전 전체 셀검사를 이번에 다시 수행했다고 주장하지 않음.'})

package=[]
for item in read(PLAN/'06_패키지_파일목록.json')['files']:
    path=PLAN/item['file']
    same=hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
    package.append({'file':item['file'],'sha256_equal':same})
assert all(x['sha256_equal'] for x in package)
save(RESUME/'package_integrity.json',{'checked_at':NOW,'files':package})

rows=csvread(SPEC/'field_spec.csv')
tabgroups=defaultdict(list)
for r in rows: tabgroups[(r['source_file_code'],r['source_sheet_id'])].append(r)
tabrows=[]
for key,items in tabgroups.items():
    targets=sorted({d['file_code'] for r in items for d in json.loads(r['targets_json'])})
    tabrows.append({'map_id':items[0]['map_id'],'source_file_code':key[0],'source_sheet_id':key[1],
        'source_sheet_name':items[0]['source_sheet_name'],'observed_fields':len(items),'target_files':';'.join(targets),
        'spec_status':'전필드 목적지 및 보존/계산 역할 지정; 행별 대조는 이관 단계에서 실행',
        'migration_status':'미실행','actual_target_file_ids':''})
csvwrite(BASE/'탭이관대응_실행.csv',sorted(tabrows,key=lambda x:x['map_id']))

testrows=csvread(BASE/'검증결과.csv')
count=Counter(r['status'] for r in testrows)
assert dict(count)=={'미실행':83,'통과':1} or dict(count)=={'통과':1,'미실행':83}
state.update(status='PH1 전수 명세·정적 감사 저장 · PH0 기준 첨부본 차분/예외 응답 대기',phase='PH1 명세 준비 (PH0 종료 대기)',last_checkpoint=NOW,
    dependency_graph_version='PH1-integrated-design-1',dependency_graph_path='PH1/명세확정/dependency_registry.json',
    actual_operating_file_count=0,h90_url=None,
    field_inventory={'observed_columns':1539,'mapping_spec_rows':1539,'target_fields_assigned':1539,'missing_target_fields':0,
        'duplicate_source_fields':0,'migrated_records':0,'logical_tables':audit['logical_table_count'],
        'status':'입력·계산·검증·조회·보존을 포함한 관측 열 대응. 실제 사업/세계관 사실 1539건이라는 뜻 아님.'},
    resume_verification={'path':'재개01/resume_verification.json','end_path':'재개01/v1_resume_unchanged.json',
        'new_backup_files':0,'new_operating_files':0,'existing_backup_ids_verified':4,'v1_write_actions':0},
    specification={'field_mapping':'PH1/명세확정/field_spec.csv','schema':'PH1/명세확정/schema_registry.json',
        'provider_contracts':'PH1/명세확정/provider_registry.json','provider_contract_counts':providers['counts'],
        'static_audit':'PH1/명세확정/integrated_spec_audit.json','ownership_audit':'PH1/명세확정/ownership_audit.json',
        'decisions':'PH1/명세확정/decision_queue.json','small_flow_tests':'PH1/명세확정/small_flow_test_protocol.json',
        'scope':'명세 정적 감사. 실제 ID·내보내기 범위·온라인 권한·재계산·행별 이관 검증 미실행.'})
state['phase_status']['PH1']='87탭·1539 관측 열 전수 대응 및 제공계약/기능 명세 작성, 정적 누락·중복·순환 검사. PH0 게이트 미해소; 온라인 구현 전.'
state['test_results']={'passed':1,'failed':0,'not_run':83,'passed_ids':['T-002'],'note':'T-002는 이전 전후 전체 비교 증거. 이번 재개 정적감사로 새 온라인 인수시험을 통과 처리하지 않음.'}
state['pending_tasks']=[
    'PH0 기준 첨부 XLSX 셀차분 또는 온라인 스냅샷 기준 예외에 대한 사용자 응답',
    'PH1 제공계약의 실제 파일·탭·범위 바인딩 및 이관 직전 행 단위 후보 대조',
    'PH2 16개 운영 파일·공통 기반·TEST 소형 연결시험',
    'PH3~PH7 이관·H90·회귀·확장·복구·릴리스 검증']
state['blocked_tasks'][0].update(next_action='기준 첨부 XLSX 경로/링크 확인 또는 명시적 온라인 스냅샷 기준 예외 응답. 미응답을 승인으로 처리하지 않음.',
    status='응답 대기',user_question='기준 XLSX 제공 / 온라인 스냅샷 기준 예외승인 / PH1 명세까지만 진행 중 선택')
new_completed=['재개 시 V1 두 ID·수정시각·권한·탭구조 및 백업4개 실재 확인',
    '87탭·1539개 관측 열의 구체 목적지·변환·보존 대응 작성; 정적 누락/중복0',
    '16분야 논리 스키마와 키·형·제공계약, H90 조회연결 명세 작성',
    '행성 계산속성 누락, 당직임기 외래키 오인, 계산/조회 키열 누락 명세 수정',
    '역법 후보를 C00 기준개정 단일 원본으로 통합; 미해결 설정은 후보 보존',
    '55개 허용 연결의 정적 순환0 및 N20→N30/H90→하위파일 금지 확인']
state['completed_tasks'] += [x for x in new_completed if x not in state['completed_tasks']]
state['safe_next_step']='사용자 응답 확인 → 기준 XLSX SHA256·셀차분 또는 승인된 예외를 근거와 함께 기록 → 현재 V1/백업/목적지 ID 재확인 → PH1 통합 명세의 제공계약을 실제 ID·범위에 바인딩하면서 PH2 16개 파일 생성 → TEST C00→R10→R20→H90 및 N30→N20→H90 검증. 소형 시험 전 대량 수식 배포 금지.'
state['approval_state']={'baseline_snapshot_exception':'미승인 · 응답 대기','operating_transition':'미승인','V1_mutation':'금지'}
state['current_checkpoint_file']='재개01_PH1_체크포인트.zip'
save(BASE/'실행상태.json',state)

registry=csvread(BASE/'파일레지스트리.csv')
for row in registry:
    if row['file_code'] in {'C00','H90'}|{f'{p}{n}0' for p in 'RN' for n in range(1,8)}:
        assert not row['spreadsheet_id']
        row['note']='PH1 전수 필드·스키마·제공계약 명세 준비. PH0 기준차분/예외 응답 후 PH2 생성 예정.'
csvwrite(BASE/'파일레지스트리.csv',registry)

issues=read(SPEC/'decision_queue.json')['issues']
report={'checked_at':NOW,'status':state['status'],'technical_completion':False,'operating_files_created':0,'operating_files_planned':16,
    'H90_url':None,'project_folder':state['folders']['project']['url'],'backup_folder':state['folders']['90-V1 보존']['url'],
    'logs_folder':state['folders']['99-실행기록']['url'],
    'migration':{'records_migrated':0,'fields_inventoried':1539,'field_destinations_assigned':1539,'transforms_applied_to_data':0,
        'preservation':'기존 native/XLSX 백업4개 재사용; 원문 메타·값·수식·판본 및 미결 쟁점 유지'},
    'spec_audit':{k:v for k,v in audit.items() if k not in ['error_details','warning_details','input_artifact_sha256','test_traceability']},
    'provider_contract_counts':providers['counts'],'tests':state['test_results'],
    'V1_resume_evidence':read(RESUME/'v1_resume_unchanged.json'),
    'remaining_canon_issues_and_spec_followups':issues,'blocker':state['blocked_tasks'],
    'resume':state['safe_next_step'],
    'recovery':'기존 V1 계속 사용. V2 운영자료 미생성. 백업4개/이전 체크포인트 보존. 다시 시작할 때 레지스트리 실제ID 확인 후 재사용.',
    'operating_transition':'기술 구축 미완료 · 운영 전환 미승인'}
save(BASE/'진행보고.json',report)
text=f'''세계관 데이터 V2 — 재개01 진행보고
확인 시각: {NOW}
현재 상태: PH1 전수 명세·정적 감사 저장 / PH0 기준 첨부본 셀차분 및 예외 응답 대기.
전체 기술 구축 완료가 아니며 운영 전환 전 상태입니다.

이번 수행
- 실제 V1 두 ID와 원본 제목·수정시각·부모·권한·87탭 구조를 재확인했습니다.
- 기존 native/XLSX 백업4개와 목적지 폴더를 재사용했으며 중복 생성하지 않았습니다.
- 87탭·1,539개 관측 열에 입력/계산/조회/검증/원문보존 목적지를 지정했습니다.
- 정적 검사: 누락0, 중복0, 미존재 목적지필드0, PK/자료형 오류0.
- 16분야 {audit['logical_table_count']}개 논리표와 제공계약 {providers['counts']['contracts']}개를 명세화했습니다. 물리 탭 수나 이관 사실 수가 아닙니다.
- 55개 허용 연결의 정적 순환0. C00 외부 import 없음, H90 외부 소비 없음, N30의 N20 import 금지.
- 행성 계산속성7개가 제공표에서 빠지는 계약, 당직임기ID의 잘못된 공직임기 참조, 계산/조회 키열 누락을 수정했습니다.
- C00 역법 후보의 별도 수동 입력표를 제거하고 기준개정이력으로 대응했습니다.
- 모든 84개 시험의 명세 연결을 작성했습니다. 이 작업은 실제 시험 통과가 아닙니다.

실제 실적
운영 파일: 0/16. H90: 미생성. 실제 데이터 이관: 0건. 적용 이관 배치: 없음.
인수시험: 통과1(T-002), 실패0, 미실행83. 이번 재개에서 추가 온라인 시험 통과0.
T-002는 앞선 전후 전체 셀·수식·캐시 비교 증거이며, 이번에는 원본 메타데이터를 재확인했습니다.
이번 V1 쓰기/이동/권한변경 호출: 0건.
원 계획 패키지01~05의 SHA256도 기존 패키지 목록과 일치합니다.

남은 게이트
기준 첨부 XLSX 두 실물이 없어서 첨부 당시와 실행시점의 셀 단위 차분을 입증하지 못했습니다.
계획서2.2·PH0 종료 기준에 따라, 기준본 경로/링크 또는 온라인 스냅샷 기준 예외에 대한 응답을 기다립니다.
미응답은 승인으로 처리하지 않았습니다. PH2 생성·이관·운영 전환은 하지 않았습니다.
명세를 실제 파일ID·탭·범위로 연결하고, 실제 행 후보·정본 채택·온라인 검증을 진행해야 합니다.

보존한 미결 쟁점
지도기준 복수 개정과 좌표축 의미, 행성 반경/면적, 국가명 판본, 종족/인적분류,
도시화 분모·정의, 시설 수용량/생산량 구분, 자원 매장/생산 단위, 날짜·기년 정밀도,
구형/확장 사실의 동일성 등. 원문·ID를 보존했고 값을 새로 채우거나 정본으로 결정하지 않았습니다.

위치
프로젝트: {report['project_folder']}
백업·복구: {report['backup_folder']}
실행기록: {report['logs_folder']}
통합 명세: PH1/명세확정/field_spec.csv, schema_registry.json, provider_registry.json
실행상태: 실행상태.json
새 체크포인트: 재개01_PH1_체크포인트.zip

다음 안전한 단계
{state['safe_next_step']}
'''
(BASE/'진행보고.txt').write_text(text,encoding='utf-8')

excluded_names={'산출물_체크섬_재개01.json','checkpoint_verification.json','cloud_sync_verification.json'}
files=[p for p in sorted(BASE.rglob('*')) if p.is_file() and p.suffix.lower() not in ['.zip','.pyc']
    and p.name not in excluded_names and '_downloaded' not in p.name and '__pycache__' not in p.parts]
manifest=[{'path':p.relative_to(BASE).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
manifest_path=RESUME/'산출물_체크섬_재개01.json'
save(manifest_path,{'created_at':NOW,'files':manifest,'excluded':'기존·새 ZIP, 수신 검증용 파일, 자기참조 manifest'})
archive=BASE/'재개01_PH1_체크포인트.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files+[manifest_path]: z.write(p,p.relative_to(BASE).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for item in manifest:
        assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
verification={'checked_at':NOW,'file_count':len(manifest),'zip_bytes':archive.stat().st_size,
    'zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'all_archived_file_hashes_match':True,
    'source_package_unchanged':True,'operating_files':0,'migrated_records':0,'tests':state['test_results']}
save(RESUME/'checkpoint_verification.json',verification)
print(json.dumps(verification,ensure_ascii=False))
