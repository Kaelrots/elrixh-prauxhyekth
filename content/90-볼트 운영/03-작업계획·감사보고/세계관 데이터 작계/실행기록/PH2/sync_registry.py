from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,csv,sys
sys.stdout.reconfigure(encoding='utf-8')
PH2=Path(__file__).resolve().parent
BASE=PH2.parent
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
state=read(BASE/'실행상태.json')
with (BASE/'파일레지스트리.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
for path in sorted(PH2.glob('created_*.json')):
    obj=read(path); code=obj['file_code']; result=obj['result']
    assert result['id'] not in {v['id'] for v in state['source_snapshot_ids'].values()}
    state['created_files'][code]=obj
    for row in rows:
        if row['file_code']==code:
            row.update(role='V2 운영 대상 파일',spreadsheet_id=result['id'],url=result['url'],
                status=obj.get('build_status','생성 · 구조 준비 중'),note='PH2 단계; 기능이관·연결시험 완료를 의미하지 않음')
state['actual_operating_file_count']=len(state['created_files'])
state['phase']='PH2'
state['status']='PH2 독립 운영 파일·공통 기반·소형 연결시험 진행 중'
state['phase_status']['PH0']='실행 원본·백업 확인; 첨부 XLSX 셀차분 미검증 예외를 보존하고 후속 사용자 진행지시에 따라 조건부 진행'
state['phase_status']['PH1']='1539필드 전수명세 및 109제공계약·단일원본·순환없는 설계 정적감사 완료'
state['phase_status']['PH2']='실제 생성ID 기록·구조준비 진행; 기본수신/권한/반영 시험 미완료'
state['last_checkpoint']=datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
state['approval_state']['baseline_snapshot_exception']='후속 진행지시 적용; 첨부본 차분 미검증 예외 유지 (PH2/authorization_and_gate.json)'
state['approval_state']['operating_transition']='미승인'
state['blocked_tasks'][0]['status']='미검증 예외로 보존; 후속 진행지시 적용'
state['blocked_tasks'][0]['scope']='첨부본과 현재 셀차분 증거; V2 기술 구축은 진행'
state['safe_next_step']='PH2/created_*.json 실ID 재확인 → physical_layout 기반 구조준비 → 전용 TEST 소형흐름 권한/변경/오류검증 → 통과 후만 분야별 수식·자료 이관. 생성 재시도 전 레지스트리/목적지검색으로 중복방지.'
if 'H90' in state['created_files']: state['h90_url']=state['created_files']['H90']['result']['url']
save(BASE/'실행상태.json',state)
with (BASE/'파일레지스트리.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
print(json.dumps({'created':len(state['created_files']),'codes':sorted(state['created_files']),'operating_ready':0},ensure_ascii=False))
