import csv, json, hashlib, pathlib, datetime, zipfile
BASE=pathlib.Path(__file__).resolve().parent
PLAN=BASE.parent
NOW=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds")
def read(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
state=read(BASE/"실행상태.json")
inventory=read(BASE/"PH1/inventory_summary.json")
comparison=read(BASE/"PH1/canonical_start_end_comparison.json")
original_checks=[]
for code in ["REG","NAT"]:
    start=read(BASE/f"PH0/{code}-V1_drive_start.json")
    end=read(BASE/f"PH0/{code}-V1_drive_end.json")
    ss=read(BASE/f"PH0/{code}-V1_sheets_start.json")
    es=read(BASE/f"PH0/{code}-V1_sheets_end.json")
    canonical=next(x for x in comparison if x["source_file_code"]==code+"-V1")
    original_checks.append({"source":code+"-V1","metadata_equal":start==end,"sheet_metadata_equal":ss==es,
      "export_literal_and_formula_equal":canonical["export_literal_and_formula_equal"],
      "formula_cache_changed_cells":canonical["formula_cache_changed_cells"]})
assert all(x["metadata_equal"] and x["sheet_metadata_equal"] and x["export_literal_and_formula_equal"] and x["formula_cache_changed_cells"]==0 for x in original_checks)
package=[]
for x in read(PLAN/"06_패키지_파일목록.json")["files"]:
    p=PLAN/x["file"]
    package.append({"file":x["file"],"size_equal":p.stat().st_size==x["size_bytes"],"sha256_equal":hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]})
assert all(x["size_equal"] and x["sha256_equal"] for x in package)
write(BASE/"PH0/package_integrity_check.json",{"checked_at":NOW,"files":package})
write(BASE/"PH0/T-002_evidence.json",{"test_id":"T-002","status":"통과","checked_at":NOW,
 "scope":"이번 WORK 구간의 V1 무변경 검사. 첨부 시점과 현재 차분 및 V2 완성 검증을 의미하지 않음.",
 "v1_write_actions":0,"checks":original_checks,
 "evidence":["v1_mutation_audit.json","REG-V1_drive_start.json","REG-V1_drive_end.json","NAT-V1_drive_start.json","NAT-V1_drive_end.json",
 "REG-V1_sheets_start.json","REG-V1_sheets_end.json","NAT-V1_sheets_start.json","NAT-V1_sheets_end.json","../PH1/canonical_start_end_comparison.json"]})
with (PLAN/"03_검증_체크리스트.csv").open(encoding="utf-8-sig",newline="") as f:
    reader=csv.DictReader(f); keys=reader.fieldnames; tests=list(reader)
assert len(tests)==84 and all(t["status"]=="미실행" for t in tests)
for t in tests:
    if t["test_id"]=="T-002":
        t.update(status="통과",actual_result="V1 2개 전후 제목·권한·부모·수정시각·87탭 구조 동일; 내보내기 literal·수식·속성·캐시 변경 0셀. V1 쓰기 호출 0.",
          evidence_location="PH0/T-002_evidence.json;PH1/canonical_start_end_comparison.json",checked_at=NOW)
with (BASE/"검증결과.csv").open("w",encoding="utf-8-sig",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(tests)
state.update(status="PH0 일부 완료 · 기준 첨부 XLSX 위치 응답 대기",phase="PH0",
 last_checkpoint=NOW,test_results={"passed":1,"failed":0,"not_run":83,"passed_ids":["T-002"],"note":"V1 무변경만 실제 통과. 로컬 준비검사와 나머지 V2 운영시험은 구별."},
 dependency_graph_version="draft-1",dependency_graph_path="PH1/dependency_design.json",h90_url=None,
 field_inventory={"observed_columns":inventory["counts"]["fields"],"mapping_draft_rows":inventory["field_mapping_rows"],
 "target_fields_decided":inventory["target_fields_decided"],"migrated_records":0,"status":"전수 관측 및 보존 경로 인벤토리 · V2 대응 확정 미완료"},
 v1_unchanged_verification={"status":"확인","checked_at":NOW,"checks":original_checks,"evidence":"PH0/T-002_evidence.json"},
 phase_status={"PH0":"원본·백업·구조 확인; 첨부본 셀값 차분 미검증","PH1":"읽기 전용 인벤토리·의존·결정대기 초안","PH2":"미착수","PH3":"미착수","PH4":"미착수","PH5":"미착수","PH6":"V1 보존 검사 T-002만 통과; V2 시험 미실행","PH7":"미착수"},
 safe_next_step="기준 XLSX 두 개의 SHA256 확인 → 현재 보존본과 셀/수식/메모 차분 → PH0 종료 판단 → PH1 1,539개 열 대응 및 기능 명세 확정. 기존 폴더·백업 ID를 재사용하고 중복 생성 금지.")
state["completed_tasks"] += [x for x in ["87탭·1,539개 관측 열 인벤토리 및 보존 경로 작성","55개 허용 연결 설계의 순환 0 확인(실제 구현 미검증)","18개 추가 native 범위 관측 보존","T-002 작업 전후 V1 무변경 검사 통과"] if x not in state["completed_tasks"]]
state["pending_tasks"]=[x for x in state["pending_tasks"] if x!="PH0 native 및 전체 실제 사용 범위 목록 마무리"]
state["cloud_state_reference"]=read(BASE/"cloud_state_reference.json")
state["native_backup_probe_evidence"]="PH0/v1_mutation_audit.json (사본에만 실시; 원본 아님)"
write(BASE/"실행상태.json",state)
dq=read(BASE/"PH1/decision_queue_draft.json")
dq["status"]="결정대기 초안 · 지도기준 2항목 온라인 관측 연결 · 정본 채택 없음"
for item in dq["items"]:
    if item["decision_id"] in ["DQ-001","DQ-002"]:
        rows=[39,40,41,42,87,89,90,92] if item["decision_id"]=="DQ-001" else [86]
        item["live_cell_observation_confirmed"]=True
        item["basis_type"]="계획서 지시 + 실행시점 온라인 원문 관측"
        item["legacy_locators"]=[{"source_file_id":"1EACdRIiAPGk4LAbttpXZiJd_cuqIh-cVi4jQsbfmqDw","source_sheet_id":861639760,
          "source_sheet_name":"00 공통 기준","row":r,"snapshot_id":state["execution_id"],"evidence":"live_decision_observations.json"} for r in rows]
        item["setting_decision_status"]="결정 대기 · 원문 보존"
write(BASE/"PH1/decision_queue_draft.json",dq)
report={
 "status":"미완료 · PH0 첨부 기준본 차분 대기","project_folder":state["folders"]["project"]["url"],
 "backup_folder":state["folders"]["90-V1 보존"]["url"],"logs_folder":state["folders"]["99-실행기록"]["url"],
 "operating_files_created":0,"operating_files_planned":16,"H90_url":None,
 "migration":{"records_migrated":0,"fields_inventoried":1539,"fields_decided":0,"transforms_applied":0,
 "preservation":"V1 네이티브 백업 2개, 실행시점 XLSX 2개, 시작/종료 관측 및 필드·행·수식 인벤토리"},
 "tests":state["test_results"],"V1_unchanged":state["v1_unchanged_verification"],
 "remaining_canon_issues":dq["items"],"blocker":state["blocked_tasks"],
 "recovery":"V1 원본 계속 사용. V2 운영파일/신규입력은 아직 없어 롤백할 운영 데이터 없음. 실행상태의 실제 백업·폴더 ID를 재조회하고 같은 파일을 다시 만들지 않는다.",
 "technical_completion":False,"operating_transition":"아직 기술 구축 전; 운영 전환 요청하지 않음",
 "resume":state["safe_next_step"],"T-074_override":"V1 원본 시험쓰기 금지. 후속 차분 시험은 TEST 원본 복제본으로 수행.",
 "checked_at":NOW}
write(BASE/"진행보고.json",report)
text=f"""세계관 데이터 V2 실행 체크포인트
확인 시각: {NOW}
상태: PH0 일부 완료 / 첨부 기준 XLSX 원파일 위치 확인 대기. 전체 기술 구축 완료 아님.

수행
- 지정 V1 두 ID의 권한·탭·표본 및 실제 입력후보 범위를 읽었음.
- REG 36탭, NAT 51탭. 첨부 구조기록 대비 탭·순서·숨김·수식개수 차이 0.
- 원본별 네이티브 Google Sheets 사본과 실행시점 XLSX를 별도 보존함.
- 전체 셀을 읽어 1,539개 관측 열의 인벤토리와 보존 경로를 기록함. V2 target 결정 0개, 이관 0건.
- V1 두 파일의 제목·부모·권한·수정시각·탭구조가 전후 동일함.
- 전후 내보내기 87탭의 literal·수식·속성·캐시 변경 0셀. T-002 통과.
- 원 계획서/CSV/구조JSON은 패키지 체크섬과 일치하며 수정하지 않음.

시험: 통과 1 (T-002), 실패 0, 미실행 83.
운영 파일: 0/16. H90: 미생성.
PH1: 전수 필드 인벤토리와 의존·결정대기 초안. PH2~PH7: 미착수.
빈 수식·FALSE·조회결과·검증 라벨을 실제 세계관 사실 개수로 보고하지 않음.

중단 사유
기준 첨부 XLSX 두 실물이 없어서 첨부 당시와 실행시점의 셀값 차분을 검증할 수 없음.
필요한 기준 해시:
REG: cbb7cde61ec86aa3b05bfbddaf63a2ac65205a632398c0de88645f0eae966b07
NAT: 3b3c410b64425403614b26ad9bdf900a254c81c2ffe9fc02eaa798664ee151d1
현재 온라인 XLSX는 확보했으나 과거 기준본을 대체하지 않음.
Downloads/Documents 추가 파일명 검색에서 발견한 이전 국가 데이터.xlsx의 해시는
1f934e99b6c5588dd168b81d7a743b35fa9ad723f5aaa86e5853f557f4c4ce36으로 불일치하여 대체하지 않음.

미해결 정본 쟁점
지도 투영·wrap·축척의 초기 검토/후속 초안, 좌표축 항목의 의미 불일치를 실제 원문에서 확인함.
행성 반경/면적, 국가 외국어 명칭 역할, 종족 분류는 계획서 기반 검토 후보로 유지함.
어느 값도 새로 채택·확정하거나 창작하지 않음.

백업·복구
프로젝트: {report['project_folder']}
백업 4개: {report['backup_folder']}
실행기록: {report['logs_folder']}
원본 V1 계속 사용. V2 운영 입력 없음. 백업을 원본으로 덮어쓰지 않음.
폴더·파일레지스트리에 기록된 실제 ID를 확인하고 재개하며 동일 파일을 다시 만들지 않음.

다음 단계
{report['resume']}
"""
(BASE/"진행보고.txt").write_text(text,encoding="utf-8")
manifest=[]
for p in sorted(BASE.rglob("*")):
    if p.is_file() and p.name not in ["산출물_체크섬.json","PH0_PH1_체크포인트.zip","archive_upload_reference.json"]:
        manifest.append({"path":p.relative_to(BASE).as_posix(),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
write(BASE/"산출물_체크섬.json",{"checked_at":NOW,"files":manifest})
with zipfile.ZipFile(BASE/"PH0_PH1_체크포인트.zip","w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(BASE.rglob("*")):
        if p.is_file() and p.name not in ["PH0_PH1_체크포인트.zip","archive_upload_reference.json"]:
            z.write(p,p.relative_to(BASE).as_posix())
print(json.dumps({"metadata_and_content_unchanged":True,"operating_files":0,"fields":1539,"tests":state["test_results"],
 "artifact_files":len(manifest),"zip_bytes":(BASE/"PH0_PH1_체크포인트.zip").stat().st_size},ensure_ascii=False))

