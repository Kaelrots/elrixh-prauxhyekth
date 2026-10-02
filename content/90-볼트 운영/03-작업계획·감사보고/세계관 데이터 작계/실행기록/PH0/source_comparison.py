"""Read-only OOXML comparison. Does not modify XLSX or mark operating tests passed."""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import csv
import hashlib
import json
import posixpath
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / '실행기록' / 'PH0'
PH1 = BASE / '실행기록' / 'PH1'
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'p': 'http://schemas.openxmlformats.org/package/2006/relationships'}
EXPECTED = {
    'REG-V1': '1456ec38314c47f740a205e375891d0773d39228b5da678dfd4ffc1da56be15e',
    'NAT-V1': 'f590df6a0c855911011be0f83d942add1f8dcf1a218bcdf053393d1ce37519c1',
}
SOURCE_IDS = {
    'REG-V1': '1EACdRIiAPGk4LAbttpXZiJd_cuqIh-cVi4jQsbfmqDw',
    'NAT-V1': '1mTRKFfCFtiTmuAR6QwrslcBI6Q-wutYzVP_weDAW9uI',
}
checked_at = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def extract(path):
    result = []
    with ZipFile(path) as z:
        workbook = ET.fromstring(z.read('xl/workbook.xml'))
        relationships = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        targets = {n.attrib['Id']: n.attrib['Target'] for n in relationships}
        for index, sheet in enumerate(workbook.find('m:sheets', NS), 1):
            target = targets[sheet.attrib['{' + NS['r'] + '}id']]
            xml_path = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('xl', target))
            tree = ET.fromstring(z.read(xml_path))
            formulas, imports, wrappers = [], [], []
            for cell in tree.findall('.//m:sheetData/m:row/m:c', NS):
                f = cell.find('m:f', NS)
                if f is None:
                    continue
                formula = ''.join(f.itertext())
                detail = {'cell': cell.attrib.get('r'), 'formula': formula}
                formulas.append(detail)
                if 'IMPORTRANGE' in formula.upper():
                    imports.append(detail)
                if 'DUMMYFUNCTION' in formula.upper():
                    wrappers.append(detail)
            dim = tree.find('m:dimension', NS)
            result.append({
                'name': sheet.attrib['name'], 'ordinal': index,
                'state': sheet.attrib.get('state', 'visible'),
                'xlsx_sheet_id': sheet.attrib['sheetId'],
                'dimension': None if dim is None else dim.attrib.get('ref'),
                'formula_count': len(formulas),
                'importrange_formula_count': len(imports),
                'dummyfunction_formula_count': len(wrappers),
                'importrange': imports,
            })
    return result

baseline_path = BASE / '05_첨부본_구조점검.json'
baselines = json.loads(baseline_path.read_text(encoding='utf-8-sig'))
report = {
    'project': '세계관 데이터 V2',
    'artifact_type': '첨부 구조 요약과 실행시점 온라인 내보내기의 제한적 구조 비교',
    'checked_at': checked_at,
    'baseline_path': str(baseline_path),
    'baseline_sha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
    'baseline_original_xlsx_available': False,
    'baseline_absence_basis': '부모 작업의 로컬 작업폴더 및 온라인 Drive 정확한 XLSX 이름 검색에서 기준 XLSX 원파일을 찾지 못함',
    'limitations': [
        '첨부 XLSX 원파일이 없어 셀값·전체 수식 원문·서식·메모·링크·보호·권한의 첨부본 대비 차분은 미검증이다.',
        'SHA-256 차이는 파일 바이트 차이이며 세계관 내용 변경의 증거로 단정하지 않는다.',
        'formula_count는 OOXML의 수식 셀 수이며 실데이터 행 수·온라인 연산량·재계산 성공을 뜻하지 않는다.',
        '기준 importrange 목록은 대표 관측이다. 등록 표본의 식과 위치만 비교하며 전체 래퍼의 동일성을 주장하지 않는다.',
        'XLSX sheetId는 온라인 Google Sheets sheetId와 동일하다고 간주하지 않는다.',
        'dimension=null인 기준은 범위 비교에 충분하지 않다.',
        '이번 결과는 T-001~T-084 시험 통과 기록이 아니며 검증 CSV를 수정하지 않는다.',
    ],
    'sources': [],
}
rows = []
for baseline in baselines:
    code = baseline['source']
    current_path = OUT / (code + '_online.xlsx')
    data = current_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED[code]:
        raise RuntimeError(f'{code}: expected export hash mismatch')
    current_sheets = extract(current_path)
    current_by_name = {s['name']: s for s in current_sheets}
    baseline_by_name = {s['name']: s for s in baseline['sheets']}
    details = []
    for old_index, old in enumerate(baseline['sheets'], 1):
        cur = current_by_name.get(old['name'])
        if cur is None:
            details.append({'name': old['name'], 'comparison_status': '기준에만 있음'})
            continue
        observed_imports = {x['cell']: x['formula'] for x in cur['importrange']}
        sample_matches = [{
            'cell': x['cell'], 'baseline_formula': x['formula'],
            'current_formula': observed_imports.get(x['cell']),
            'exact_match': observed_imports.get(x['cell']) == x['formula'],
        } for x in old['importrange']]
        details.append({
            'name': old['name'],
            'comparison_status': '비교 가능한 구조 동일' if (
                old_index == cur['ordinal'] and old['state'] == cur['state'] and
                old['formula_count'] == cur['formula_count'] and all(x['exact_match'] for x in sample_matches)
            ) else '비교 가능한 구조 차이 있음',
            'baseline_ordinal': old_index, 'current_ordinal': cur['ordinal'],
            'baseline_state': old['state'], 'current_state': cur['state'],
            'baseline_xlsx_sheet_id': old['sheet_id'], 'current_xlsx_sheet_id': cur['xlsx_sheet_id'],
            'baseline_formula_count': old['formula_count'], 'current_formula_count': cur['formula_count'],
            'formula_count_delta': cur['formula_count'] - old['formula_count'],
            'baseline_dimension': old['dimension'], 'current_dimension': cur['dimension'],
            'dimension_comparison': '비교 불가: 기준 범위 미수록' if old['dimension'] is None else ('동일' if old['dimension'] == cur['dimension'] else '차이 있음'),
            'baseline_importrange_sample_count': len(old['importrange']),
            'current_importrange_formula_count': cur['importrange_formula_count'],
            'current_dummyfunction_formula_count': cur['dummyfunction_formula_count'],
            'importrange_baseline_sample_comparison': sample_matches,
            'current_importrange_formulas': cur['importrange'],
            'cell_value_diff_status': '미검증: 첨부 XLSX 원파일 없음',
            'full_formula_text_diff_status': '미검증: 기준에 전체 수식 원문 없음',
            'full_wrapper_diff_status': '미검증: 기준은 대표 외부 연결식 관측만 포함',
        })
    for cur in current_sheets:
        if cur['name'] not in baseline_by_name:
            details.append({'name': cur['name'], 'comparison_status': '현재에만 있음', 'current': cur})
    source = {
        'source': code, 'source_spreadsheet_id': SOURCE_IDS[code],
        'current_export_path': str(current_path),
        'baseline_sha256': baseline['sha256'], 'current_sha256': digest,
        'file_bytes_equal': digest == baseline['sha256'],
        'baseline_size_bytes': baseline['size_bytes'], 'current_size_bytes': len(data),
        'size_delta_bytes': len(data) - baseline['size_bytes'],
        'baseline_sheet_count': len(baseline['sheets']), 'current_sheet_count': len(current_sheets),
        'added_sheet_names': [s['name'] for s in current_sheets if s['name'] not in baseline_by_name],
        'missing_sheet_names': [s['name'] for s in baseline['sheets'] if s['name'] not in current_by_name],
        'baseline_formula_count_total': sum(s['formula_count'] for s in baseline['sheets']),
        'current_formula_count_total': sum(s['formula_count'] for s in current_sheets),
        'current_dummyfunction_formula_count_total': sum(s['dummyfunction_formula_count'] for s in current_sheets),
        'current_importrange_formula_count_total': sum(s['importrange_formula_count'] for s in current_sheets),
        'baseline_hidden_sheet_names': [s['name'] for s in baseline['sheets'] if s['state'] != 'visible'],
        'current_hidden_sheet_names': [s['name'] for s in current_sheets if s['state'] != 'visible'],
        'comparable_structure_difference_count': sum(s['comparison_status'] != '비교 가능한 구조 동일' for s in details),
        'cell_value_diff_status': '미검증: 첨부 XLSX 원파일 없음',
        'content_change_determined': False,
        'sheets': details,
    }
    report['sources'].append(source)
    for detail in details:
        rows.append({
            'source': code, 'sheet_name': detail['name'],
            **{k: v for k, v in detail.items() if k not in ('name', 'importrange_baseline_sample_comparison', 'current_importrange_formulas', 'current')},
            'known_import_samples_match': all(s['exact_match'] for s in detail.get('importrange_baseline_sample_comparison', [])) if detail.get('baseline_importrange_sample_count', 0) else '등록 표본 없음',
            'checked_at': checked_at,
        })

report['ph0_gate_assessment'] = {
    'status': 'PH0 부분 수행: 비교 가능한 구조 대조 완료, 첨부본 전체 차분 미검증',
    'can_assert_ph0_complete_from_this_report': False,
    'remaining_gate': '기준 첨부 XLSX 원파일 확보 후 값·수식·필드 차분, 또는 기준 부재를 명시적으로 수용하는 프로젝트 기준 결정. 네이티브 백업·권한·전체 인벤토리·원본 최종 대조는 별도 증거 확인 필요.',
    'safe_next_step': '현재 온라인 스냅샷에 근거한 PH1 필드 대응 초안과 원본 책임/의존 설계 준비. 첨부본 동일·무손실 이관·온라인 시험 완료로 표시하지 않음.',
}
write_json(OUT / 'source_comparison.json', report)
columns = list(dict.fromkeys(k for row in rows for k in row))
with (OUT / 'source_comparison.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

allowed = {
 'C00': ([], []), 'R10': (['C00'], []), 'R20': (['C00','R10'], []),
 'R30': (['C00','R10'], ['R20']), 'R40': (['C00','R10'], ['R20']),
 'R50': (['C00','R10'], []), 'R70': (['C00','R10'], []),
 'R60': (['C00','R10'], ['R70','R20']), 'N10': (['C00','R10'], []),
 'N30': (['C00'], []), 'N20': (['C00','R10','N30'], []),
 'N40': (['C00'], ['R20','R30','R50']), 'N50': (['C00','N40'], ['R60','R50','R70','R20']),
 'N60': (['C00'], ['R30','R50']), 'N70': (['C00'], ['R40','R50','N30']),
 'H90': ([], ['C00','R10','R20','R30','R40','R50','R60','R70','N10','N20','N30','N40','N50','N60','N70']),
}
edges = [{'provider': p, 'consumer': c, 'edge_type': '기본 허용' if kind == 0 else '필요시 허용',
          'implemented': False, 'provider_spreadsheet_id': None, 'consumer_spreadsheet_id': None}
         for c, lists in allowed.items() for kind, providers in enumerate(lists) for p in providers]
incoming = {n: set(p for providers in lists for p in providers) for n, lists in allowed.items()}
ordered = []
while len(ordered) < len(incoming):
    ready = [n for n in incoming if n not in ordered and incoming[n].issubset(ordered)]
    if not ready:
        raise RuntimeError('Cycle in design graph')
    ordered.extend(ready)
graph = {
 'project': '세계관 데이터 V2', 'schema_version': 'draft-1', 'created_at': checked_at,
 'status': 'PH1 설계 초안 · 운영 구현/실제 ID 검증 미실행',
 'source_type': '사용자 승인 계획서의 설계 규칙', 'source': '01 계획서 8.3절 523~542행',
 'direction': 'provider -> consumer (데이터 흐름 방향)',
 'nodes': [{'file_code': n, 'spreadsheet_id': None, 'created_by_this_artifact': False} for n in allowed],
 'edges': edges, 'planned_topological_order': ordered,
 'design_static_cycle_count': 0, 'actual_file_id_graph_cycle_count': None,
 'static_validation_scope': '모든 기본/선택 허용 간선을 포함한 문서 설계만 검사. T-069 운영 시험의 통과를 뜻하지 않음.',
 'rules': ['C00 외부 import 없음', 'N20이 N30 인물을 읽고 N30은 N20 임기를 import하지 않음',
           'H90은 필요한 원본을 읽고 다른 운영 파일은 H90을 import하지 않음',
           'R70의 생산 비교와 N30 외부 term_id 존재/기간 검증은 H90에서 수행',
           '하이퍼링크와 값으로 보존된 외래 ID는 import 간선에 포함하지 않음',
           '선택 허용 간선도 실제 필요와 계약 검증 후에만 구현'],
 'ph2_small_tests': ['C00 -> R10 -> R20 -> H90', 'N30 -> N20 -> H90'],
}
write_json(PH1 / 'dependency_design.json', graph)
decision_items = [
 ('DQ-001', '공통 지도기준의 초기 검토/후속 초안', 'std.map.projection; std.map.wrap_x; std.map.wrap_y; std.map.scale', '기준 ID와 개정 ID를 분리하고 원문·판본·채택 상태 보존', 'C00'),
 ('DQ-002', '축 기준 항목명과 값의 의미 불일치', 'std.map.crs.axis', '원문을 임의 치환하지 않고 의미 검토 대상으로 남김', 'C00'),
 ('DQ-003', '행성 원문 반경/지름환산 반경/표면적 대조', '10_행성_기본값', '직접 원문과 계산값을 보존하고 채택 미결정이면 자동 정본 승격 금지', 'R70'),
 ('DQ-004', '국가 외국어 이름의 역할·판본 차이', '지역 국가목록 / 국가 기본정보', '공식 표기·중립 목록명·원문 별칭·구판의 역할을 보존하고 최신값 자동선택 금지', 'C00;N10'),
 ('DQ-005', '종족·인적 분류의 후보 정의/분류체계 충돌', '공통 분류사전', '정의·판본·설정 상태와 충돌 연결을 보존하고 확정으로 일괄 변경하지 않음', 'C00;R30'),
]
queue = {
 'project': '세계관 데이터 V2', 'schema_version': 'draft-1', 'created_at': checked_at,
 'status': '계획서 기반 결정 후보 초안 · 온라인 셀 단위 재확인 대기',
 'items': [{'decision_id': k, 'subject': title, 'source_hint': hint, 'owner_file_codes': owners,
            'basis_type': '계획서의 첨부본 관측 및 보존 지시', 'basis_document': '01 계획서 2.3절/4.1절/4.8절',
            'live_cell_observation_confirmed': False, 'legacy_locators': [],
            'safe_preservation_rule': handling, 'setting_decision_status': '결정 대기 후보',
            'selected_setting_value': None, 'technical_implementation_status': '미실행'}
           for k, title, hint, handling, owners in decision_items],
 'technical_limitations_separate_from_setting_decisions': [{
    'issue_id': 'PH0-BASELINE-001', 'issue_type': '증거 자료 없음',
    'subject': '기준 첨부 XLSX 원파일 부재',
    'observed_fact': '현재 온라인 내보내기와 05 구조 JSON은 존재하나 기준 XLSX 원파일은 검색에서 발견되지 않음(부모 작업 보고)',
    'effect': '첨부본 대비 셀값·전체 수식 차분 미검증. SHA 차이만으로 내용 변경 판단 금지.',
    'setting_decision': False,
 }],
}
write_json(PH1 / 'decision_queue_draft.json', queue)
print(json.dumps({
 'source_summaries': [{k:v for k,v in s.items() if k not in ('sheets',)} for s in report['sources']],
 'csv_rows': len(rows), 'design_edges': len(edges), 'design_cycle_count': 0,
 'outputs': [str(OUT / 'source_comparison.json'), str(OUT / 'source_comparison.csv'),
             str(PH1 / 'dependency_design.json'), str(PH1 / 'decision_queue_draft.json')]
}, ensure_ascii=False, indent=2))
