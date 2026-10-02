from pathlib import Path
import csv, json, hashlib, sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent
PH1 = ROOT.parent
PLAN = PH1.parent.parent
PARTS = ['region', 'nation', 'common_hub']
VALID_FILES = {'C00','H90'} | {f'{p}{n}0' for p in 'RN' for n in range(1,8)}

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def save(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def key_list(value):
    if isinstance(value,list): return value
    if not value: return []
    return [x.strip() for x in value.replace('+',',').split(',') if x.strip()]

baseline = read_csv(PH1/'actual_field_mapping_draft.csv')
baseline_ids = {r['source_field_id'] for r in baseline}
test_registry = {r['test_id']:r for r in read_csv(PLAN/'03_검증_체크리스트.csv')}
parts, rows, tables, issues, functions = {}, [], [], [], []
missing_files = []
for part in PARTS:
    paths = {kind:ROOT/f'{part}_{kind}.{ext}' for kind,ext in [('field_spec','csv'),('schema','json'),('function_spec','json'),('issues','json')]}
    if any(not p.exists() for p in paths.values()):
        missing_files += [p.name for p in paths.values() if not p.exists()]
        continue
    r = read_csv(paths['field_spec'])
    s = read_json(paths['schema'])
    fn = read_json(paths['function_spec'])
    iss = read_json(paths['issues'])
    parts[part] = {'rows':r, 'schema':s, 'function_spec':fn, 'issues':iss}
    rows += [dict(x, spec_part=part) for x in r]
    tables += [dict(x, spec_part=part) for x in s.get('tables',[])]
    issues += [dict(x, spec_part=part) for x in iss.get('issues',[])]
    for collection in ['functions','function_rules','empty_area_functions']:
        for x in fn.get(collection,[]):
            functions.append(dict(x, spec_part=part))

extension_sources=[]
for name in ['cross_domain_contract_extensions.json','change_feed_contracts.json','hub_dataset_bindings.json']:
    path=ROOT/name
    if path.exists(): extension_sources.append((name,read_json(path)))
for name,ext in extension_sources:
    for t in ext.get('tables',ext.get('schemas',[])):
        tables.append(dict(t,spec_part=name))

errors, warnings = [], []
# Apply the explicitly reviewed staging-to-owner mapping. The independent source
# specifications remain intact; only the integrated deployment specification is
# canonicalized, with the mapping contract retained alongside it.
integration_contracts = parts.get('common_hub',{}).get('schema',{}).get('integration_contracts',[])
redirects = {}
for contract in integration_contracts:
    old=contract.get('upstream_target','')
    new=contract.get('canonical_target','')
    if old and new:
        redirects[tuple(old.split('.',1))] = {'destination':new.split('.',1),'field_map':contract['field_map'],'contract_id':contract['contract_id']}
tables=[t for t in tables if (t.get('file_code',''),t.get('table_id',t.get('table',''))) not in redirects]
integrated_redirect_count=0
id_counts = Counter(r['source_field_id'] for r in rows)
missing_ids = sorted(baseline_ids-set(id_counts))
extra_ids = sorted(set(id_counts)-baseline_ids)
duplicate_ids = {k:v for k,v in id_counts.items() if v>1}
if missing_ids: errors.append({'kind':'missing_source_field_ids','ids':missing_ids})
if extra_ids: errors.append({'kind':'unknown_source_field_ids','ids':extra_ids})
if duplicate_ids: errors.append({'kind':'duplicate_source_field_ids','ids':duplicate_ids})
if missing_files: errors.append({'kind':'missing_spec_files','files':missing_files})

table_index, table_aliases = defaultdict(list), defaultdict(set)
for t in tables:
    code = t.get('file_code', t.get('owner_file_code',''))
    tid = t.get('table_id',t.get('table',''))
    t['normalized_key'] = code+'.'+tid
    t['normalized_role'] = t.get('role',t.get('table_role',''))
    t['normalized_field_ids'] = [f.get('field_id',f.get('field','')) for f in t.get('fields',[])]
    table_index[(code,tid)].append(t)
    for label in {tid,t.get('table',''),t.get('label_ko','')} - {''}:
        table_aliases[(code,label)].add((code,tid))
    if code not in VALID_FILES: errors.append({'kind':'invalid_file_code','table':t['normalized_key']})
    dup = [f for f,n in Counter(t['normalized_field_ids']).items() if n>1]
    if dup: errors.append({'kind':'duplicate_fields','table':t['normalized_key'],'fields':dup})
    if '' in t['normalized_field_ids']: errors.append({'kind':'blank_field','table':t['normalized_key']})
    pk = key_list(t.get('primary_key_fields',t.get('record_key',t.get('primary_key',[]))))
    t['normalized_primary_key_fields'] = pk
    absent = sorted(set(pk)-set(t['normalized_field_ids']))
    if not pk: errors.append({'kind':'missing_primary_key','table':t['normalized_key']})
    if absent: errors.append({'kind':'primary_key_fields_absent','table':t['normalized_key'],'fields':absent})
    for f in t.get('fields',[]):
        fid=f.get('field_id',f.get('field',''))
        if not f.get('data_type',f.get('type')):
            errors.append({'kind':'missing_type','table':t['normalized_key'],'field':fid})
        if fid in pk and not f.get('required',f.get('nullable') is False):
            warnings.append({'kind':'key_required_not_explicit','table':t['normalized_key'],'field':fid})
for k,v in table_index.items():
    if len(v)>1: errors.append({'kind':'duplicate_table_definition','table':'.'.join(k),'parts':[x['spec_part'] for x in v]})

normalized_rows=[]
for r in rows:
    destinations=[]
    raw = r.get('targets_json') or r.get('target_destinations_json')
    if raw:
        try: destinations=json.loads(raw)
        except Exception as e: errors.append({'kind':'invalid_targets_json','source_field_id':r['source_field_id'],'error':str(e)})
    elif r.get('target_file_code') and r.get('target_table') and r.get('target_field'):
        destinations=[{'file_code':r['target_file_code'],'table':r['target_table'],'field':r['target_field'],'role':r.get('target_role',r.get('source_role','')),'rule':r.get('transform_rule',r.get('transformation',''))}]
    if not destinations: errors.append({'kind':'no_destination','source_field_id':r['source_field_id']})
    for d in destinations:
        k=(d.get('file_code',''),d.get('table',d.get('table_id','')))
        if k in redirects:
            redirect=redirects[k]
            old_field=d.get('field',d.get('field_id'))
            if old_field not in redirect['field_map']:
                errors.append({'kind':'unmapped_redirect_field','source_field_id':r['source_field_id'],'field':old_field})
            else:
                d['upstream_spec_destination']='.'.join(k)+'.'+old_field
                d['file_code'],d['table']=redirect['destination']
                d['field']=redirect['field_map'][old_field]
                d['integration_contract_id']=redirect['contract_id']
                integrated_redirect_count+=1
                k=(d['file_code'],d['table'])
        aliases=table_aliases.get(k,set())
        matches=[t for alias in aliases for t in table_index[alias]]
        if len(matches)!=1:
            errors.append({'kind':'destination_table_not_unique','source_field_id':r['source_field_id'],'destination':d,'match_count':len(matches)})
        elif d.get('field',d.get('field_id')) not in matches[0]['normalized_field_ids']:
            errors.append({'kind':'destination_field_missing','source_field_id':r['source_field_id'],'destination':d})
    if r.get('migration_status')!='미실행':
        errors.append({'kind':'unexpected_migration_claim','source_field_id':r['source_field_id'],'value':r.get('migration_status')})
    if not r.get('preservation_location'): errors.append({'kind':'missing_preservation','source_field_id':r['source_field_id']})
    normalized_rows.append(dict(r,
        target_file_code=';'.join(dict.fromkeys(d.get('file_code','') for d in destinations)),
        target_table=';'.join(dict.fromkeys(d.get('table',d.get('table_id','')) for d in destinations)),
        target_field=';'.join(dict.fromkeys(d.get('field',d.get('field_id','')) for d in destinations)),
        targets_json=json.dumps(destinations,ensure_ascii=False)))

# This traverses known contract fields only; a linked test is not a passed test.
referenced_tests=defaultdict(set)
def walk_tests(obj, context):
    if isinstance(obj,dict):
        for key,value in obj.items():
            if key in ('test_id','test_ids','tests','acceptance_test_ids'):
                vals=[value] if isinstance(value,str) else value if isinstance(value,list) else []
                for val in vals:
                    if isinstance(val,str) and val.startswith('T-'):
                        referenced_tests[val].add(context)
            walk_tests(value,context)
    elif isinstance(obj,list):
        for value in obj: walk_tests(value,context)
for part,p in parts.items(): walk_tests(p['function_spec'],part)
for name,ext in extension_sources: walk_tests(ext,name)
if (ROOT/'ownership_audit.json').exists(): walk_tests(read_json(ROOT/'ownership_audit.json'),'independent_ownership_and_row_admission_audit')
unknown_tests=sorted(set(referenced_tests)-set(test_registry))
if unknown_tests: errors.append({'kind':'unknown_test_ids','ids':unknown_tests})

summary={
    'status':'static_specification_audit_only',
    'source_tab_count':len({(r['source_file_code'],r['source_sheet_id']) for r in rows}),
    'source_field_count':len(rows),
    'unique_source_field_count':len(id_counts),
    'missing_source_fields':len(missing_ids),
    'duplicate_source_fields':len(duplicate_ids),
    'unknown_source_fields':len(extra_ids),
    'logical_table_count':len(tables),
    'logical_tables_by_file':dict(sorted(Counter(t.get('file_code','') for t in tables).items())),
    'specified_file_count':len({t.get('file_code') for t in tables}),
    'canonical_redirected_destinations':integrated_redirect_count,
    'issue_count':len(issues),
    'error_count':len(errors),'warning_count':len(warnings),
    'operating_files_created':0,'migrated_records':0,
    'acceptance_tests_newly_passed':0,
    'error_details':errors,'warning_details':warnings,
    'test_traceability':{k:{'scenario':test_registry[k]['scenario'],'spec_parts':sorted(v),'status':'미실행'} for k,v in sorted(referenced_tests.items()) if k in test_registry},
    'unreferenced_acceptance_tests':sorted(set(test_registry)-set(referenced_tests)),
    'input_artifact_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for part in PARTS for p in ROOT.glob(part+'_*.json') if p.is_file()},
    'note':'정적 필드/명세 검사이며 실제 이관·V1 원본 보존 재시험·권한·재계산·온라인 인수시험을 증명하지 않음. 논리표 수는 생성할 탭 수가 아님.'
}
save('integrated_spec_audit.json',summary)
save('schema_registry.json',{'status':'PH1 design only; not deployed','integration_contracts':integration_contracts,'tables':tables})
for issue in issues:
    if issue.get('issue_id') in ['CH-010','R-009']:
        issue['integrated_design_resolution']='C00 임시 후보표 제외 및 기준개정이력으로 11개 원본필드 목적지 전환 적용. 원문 값의 개정 동일성·채택 판단은 미실행/결정대기.'
    if issue.get('issue_id')=='CH-007' and (ROOT/'hub_dataset_bindings.json').exists():
        issue['integrated_design_resolution']='hub_dataset_bindings.json 및 provider_registry.json 참조. 명세 이름 대조와 실제 파일/권한 시험은 별개.'
save('decision_queue.json',{'status':'설정 쟁점 및 명세 조정 보존; 자동 정본 채택 없음','issues':issues})
if normalized_rows:
    allcols=list(dict.fromkeys(k for r in normalized_rows for k in r))
    with (ROOT/'field_spec.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=allcols); w.writeheader(); w.writerows(normalized_rows)
print(json.dumps({k:v for k,v in summary.items() if k not in ('error_details','warning_details','test_traceability','input_artifact_sha256')},ensure_ascii=False))
print(json.dumps({'first_errors':errors[:15],'first_warnings':warnings[:5]},ensure_ascii=False))
