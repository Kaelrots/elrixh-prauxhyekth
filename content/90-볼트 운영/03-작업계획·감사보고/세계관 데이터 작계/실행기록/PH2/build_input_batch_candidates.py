"""Audit logical input candidates only. Never emits or submits a Sheets write request."""
from pathlib import Path
from collections import defaultdict, Counter
from decimal import Decimal
import csv, json, hashlib, re, copy

HERE=Path(__file__).resolve().parent
RUN=HERE.parent
SPEC=RUN/'PH1'/'명세확정'
PH0=RUN/'PH0'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def readcsv(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def same(a,b):
 if isinstance(a,bool) or isinstance(b,bool):return type(a)==type(b) and a==b
 return a==b
def colname(n):
 s=''
 while n:n,k=divmod(n-1,26);s=chr(65+k)+s
 return s

input_paths=[HERE/'physical_layout.json',HERE/'reg_seed_records.json',HERE/'nat_seed_records.json',HERE/'reg_migration_candidate_analysis.json',HERE/'nat_migration_candidate_analysis.json',SPEC/'field_spec.csv',SPEC/'schema_registry.json',RUN/'PH1'/'literal_cells.csv',RUN/'PH1'/'source_row_inventory.csv']
hashes={p.relative_to(RUN).as_posix():sha(p) for p in input_paths}
layout,reg,nat,ra,na=[read(p) for p in input_paths[:5]]
schema=read(SPEC/'schema_registry.json')
schema_tables={t['file_code']+'.'+t['table_id']:t for t in schema['tables']}
field_map={f['source_field_id']:json.loads(f['targets_json']) for f in readcsv(SPEC/'field_spec.csv')}
blocks={}
for f in layout['files']:
 for tab in f['tabs']:
  for b in tab.get('blocks',[]):
   if b.get('kind')=='logical_table':
    key=b['schema_registry_key']
    assert key not in blocks,key
    blocks[key]=b

literal_index={x['legacy_locator']:x for x in readcsv(RUN/'PH1'/'literal_cells.csv')}
source_rows=readcsv(RUN/'PH1'/'source_row_inventory.csv')
source_row_index={x['legacy_locator']:x for x in source_rows}
native={}; native_files=[]; native_conflicts=[]
for p in list(PH0.glob('*_headers_*.json'))+[p for p in PH0.glob('native_data_*.json') if re.fullmatch(r'native_data_\d+\.json',p.name)]:
 obj=read(p);obj=obj.get('response',obj)
 if not obj.get('spreadsheetId'):continue
 native_files.append(p)
 for sheet in obj.get('sheets',[]):
  sid=str(sheet['properties']['sheetId'])
  for grid in sheet.get('data',[]):
   for rownum,row in enumerate(grid.get('rowData',[]),grid.get('startRow',0)+1):
    for col,cell in enumerate(row.get('values',[]),grid.get('startColumn',0)+1):
     key=(obj['spreadsheetId'],sid,colname(col)+str(rownum))
     if key in native and native[key].get('userEnteredValue')!=cell.get('userEnteredValue'):native_conflicts.append(key)
     native[key]=cell

def cell_evidence(lineage):
 loc=lineage.get('source_locator',lineage.get('legacy_locator'))
 src=literal_index.get(loc)
 if not src:return {'status':'missing_preserved_literal','source_locator':loc}
 expected=json.loads(src['value_json'])
 if not same(expected,lineage['raw_value']):return {'status':'raw_value_mismatch','source_locator':loc}
 cell=native.get((src['source_file_id'],str(src['source_sheet_id']),src['cell']))
 if cell is None:return {'status':'native_cell_not_observed','source_locator':loc}
 uev=cell.get('userEnteredValue',{})
 if 'formulaValue' in uev:return {'status':'native_formula_not_input','source_locator':loc}
 if not uev:return {'status':'native_effective_or_empty_not_input','source_locator':loc}
 native_value=next(iter(uev.values()))
 if src['value_type']=='number':
  equal=Decimal(str(expected))==Decimal(str(native_value))
 else:equal=same(expected,native_value)
 return {'status':'native_literal_confirmed' if equal else 'native_literal_mismatch','source_locator':loc,'source_field_id':lineage['source_field_id'],'raw_value':expected,'raw_type':src['value_type'],'native_value':native_value}

records=[]
for i,raw in enumerate(reg['target_records']):
 r=copy.deepcopy(raw)
 r['logical_table_key']=r['file_code']+'.'+r['table']
 r['values']=r.pop('fields')
 r['source_evidence_pointer']={'artifact':'PH2/reg_seed_records.json','json_pointer':f'/target_records/{i}'}
 records.append(r)
for i,raw in enumerate(nat['records']):
 r=copy.deepcopy(raw)
 r['logical_table_key']=r['target_file_code']+'.'+r['target_table']
 r['source_evidence_pointer']={'artifact':'PH2/nat_seed_records.json','json_pointer':f'/records/{i}'}
 records.append(r)

pending=[];pending_fields=[];checks=[];warnings=[];accepted=[];record_audit=[]
revision_collisions={x['standard_id'] for x in ra['standard_revision_collisions']}
issued={x['id']:x for x in reg['fixed_migration_id_ledger']}

def reason(code,detail):return {'code':code,'detail':detail}
def pending_record(r,reasons):
 pending.append({'logical_table_key':r['logical_table_key'],'reasons':reasons,'source_evidence_pointer':r['source_evidence_pointer'],'legacy_locator':r['legacy_locator'],'preserved_candidate':r,'ready_for_input_batch':False})

for r in records:
 key=r['logical_table_key'];values=r['values'];reasons=[];rwarnings=[]
 b=blocks.get(key)
 if not b:
  pending_record(r,[reason('UNBOUND_LOGICAL_TABLE','No logical table in frozen physical layout')]);continue
 columns=[c['field_id'] for c in b['columns']]
 if b['role']!='IN':reasons.append(reason('NON_INPUT_DESTINATION','Archive/configuration/view material is preserved; this manifest includes only input tables'))
 unknown=[f for f in values if f not in columns]
 if unknown:reasons.append(reason('UNDECLARED_TARGET_FIELDS',unknown))
 pk=b.get('primary_key_fields',[])
 missing=[f for f in pk if values.get(f) in ['',None]]
 if not pk:reasons.append(reason('UNDECLARED_PRIMARY_KEY','No declared key'))
 if missing:reasons.append(reason('UNRESOLVED_PRIMARY_KEY',missing))
 if key=='C00.기준개정이력' and values.get('standard_id') in revision_collisions:
  reasons.append(reason('MULTIPLE_STANDARD_REVISIONS_PENDING','All members of the original duplicate-standard revision group remain pending; no latest-row adoption'))
 if r.get('requires_review'):reasons.append(reason('EXPLICIT_SEMANTIC_REVIEW',r['requires_review']))
 if key=='C00.국가식별목록' and values.get('neutral_name') not in ['',None]:
  # Parent's explicit ownership decision: nation names have N10 input ownership.
  pending_fields.append({'logical_table_key':key,'primary_key':{f:values.get(f) for f in pk},'field':'neutral_name','raw_value':values['neutral_name'],'source_lineage':r['field_lineage']['neutral_name'],'source_evidence_pointer':r['source_evidence_pointer'],'code':'SOURCE_FIELD_MAPPING_OWNERSHIP_CONFLICT','decision':'국가명 입력 원본은 N10. C00는 최소 공통 식별자만 입력하며 neutral_name은 공란. 원문은 계보/보존 payload에 유지. C00→N10 import를 만들지 않고 표시명은 H90에서 조회.','required_spec_change':'REG-V1:1659135409:C의 C00.국가식별목록.neutral_name input 대응을 운영 입력에서 제외하고 원문 보존 대응으로 수정 필요','status':'부분 명세 수정 대기; 원문 보존 완료; batch에서는 입력 제외'})
  values.pop('neutral_name');r['field_lineage'].pop('neutral_name')
  rwarnings.append('C00 neutral_name intentionally omitted under N10-only nation-name ownership decision')
 # Every original field must still be mapped to the same destination.
 ev=[]
 for field,lin in r.get('field_lineage',{}).items():
  ev.append(cell_evidence(lin))
  match=[m for m in field_map.get(lin['source_field_id'],[]) if m['file_code']+'.'+m['table']==key and m['field']==field]
  if not match:reasons.append(reason('FIELD_SPEC_MISMATCH',{'field':field,'source_field_id':lin['source_field_id']}))
 bad=[e for e in ev if e['status']!='native_literal_confirmed']
 if bad:reasons.append(reason('SOURCE_LITERAL_NOT_CONFIRMED',bad))
 # Region relationships come from original master G/I cells, not formula spill.
 if key=='R10.지역관계':
  parent_src=literal_index.get(r['legacy_locator'])
  if not parent_src:reasons.append(reason('REGION_PARENT_SOURCE_MISSING',r['legacy_locator']))
  else:
   pe=cell_evidence({'source_locator':r['legacy_locator'],'source_field_id':f"REG-V1:{parent_src['source_sheet_id']}:{parent_src['source_column']}",'raw_value':values['parent_region_id']})
   ev.append(pe)
   rootloc=r['legacy_locator'].split('|cell=')[0]
   childloc=rootloc+'|cell=F'+str(re.search(r'row=(\d+)',rootloc)[1])
   child_src=literal_index.get(childloc)
   if not child_src:reasons.append(reason('REGION_CHILD_SOURCE_MISSING',childloc))
   else:ev.append(cell_evidence({'source_locator':childloc,'source_field_id':f"REG-V1:{child_src['source_sheet_id']}:F",'raw_value':values['child_region_id']}))
   if any(e['status']!='native_literal_confirmed' for e in ev):reasons.append(reason('RELATION_SOURCE_LITERAL_NOT_CONFIRMED',ev))
  if r['parent_reference_status']!='present_in_source_regions':rwarnings.append('원본 상위 ID gal.1 미참조: 원문 보존 입력만 허용; 유효 조회·정상 관계로 채택 금지')
  if values['relation_id'] not in issued:reasons.append(reason('TECHNICAL_ID_NOT_IN_LEDGER',values['relation_id']))
 elif not ev:reasons.append(reason('SOURCE_EVIDENCE_MISSING','No confirmed input literal or parent-cell lineage'))
 # A row's identity/provenance is safe technical data, not a setting or adoption.
 for field,val in [('legacy_locator',r['legacy_locator']),('source_snapshot_id',r['source_snapshot_id'])]:
  if field in columns and field not in values:values[field]=val
 if 'source_namespace' in columns and 'source_namespace' not in values:values['source_namespace']=r.get('source_file_code','REG-V1')
 for f in pk:
  v=values.get(f)
  if isinstance(v,str) and re.match(r'(rev|prop|rel|alias|record)\.reg\.',v) and v not in issued:reasons.append(reason('TECHNICAL_ID_NOT_IN_LEDGER',v))
 if r.get('missing_scope_or_classification_fields'):rwarnings.append({'original_blank_scope_or_classification':r['missing_scope_or_classification_fields'],'rule':'No copied meta defaults; preserve original incomplete row and report validation separately'})
 if key=='C00.언어분류' and any(f in values for f in ['start_raw','end_raw']):rwarnings.append('날짜 원문 보존; 기년/끝연도/지속 여부를 추정하지 않으며 미분류 상태 유지')
 nonliteral={}
 for field,val in values.items():
  if field in r.get('field_lineage',{}):continue
  if field in ['legacy_locator','source_snapshot_id','source_namespace']:
   nonliteral[field]={'kind':'technical_source_provenance','rule':'Copied from observed source file/snapshot/locator identity; no worldbuilding fact'}
  elif isinstance(val,str) and val in issued:
   nonliteral[field]={'kind':'previously_fixed_technical_id','ledger_entry':issued[val]}
  elif key=='C00.개체별칭' and field in ['entity_id','entity_namespace']:
   loc=r['legacy_locator']+'|cell=B'+str(r['source_row'])
   nonliteral[field]={'kind':'original_alias_entity_context','source_locator':loc,'rule':'Existing nation ID from same original row B and original nation-master namespace; no new entity'}
  elif key=='R10.지역관계' and field in ['child_region_id','parent_region_id','relation_source_slot']:
   nonliteral[field]={'kind':'direct_parent_slot_transform','source_locator':r['legacy_locator'],'rule':'Same original row F identifies child; original G or I literal identifies parent; slot is original source-column name'}
  elif key=='R10.지역관계' and field in ['legacy_relation_id','relation_type']:
   nonliteral[field]={'kind':'original_derived_relation_crosswalk','source_cache_records':r['legacy_derived_matches'],'rule':'Preserve the original relation formula output only as crosswalk/type evidence for an independently confirmed direct parent edge; no standalone formula-only row admitted'}
  else:reasons.append(reason('UNEXPLAINED_NONLITERAL_VALUE',{'field':field,'value':val}))
 r['nonliteral_field_provenance']=nonliteral
 required_missing=[c['field_id'] for c in b['columns'] if c.get('required') and values.get(c['field_id']) in ['',None]]
 if required_missing:reasons.append(reason('REQUIRED_FIELD_MISSING',required_missing))
 if reasons:pending_record(r,reasons)
 else:
  r['source_verification']=ev;r['batch_warnings']=rwarnings;r['primary_key']={f:values[f] for f in pk}
  accepted.append(r)
  record_audit.append({'logical_table_key':key,'source_evidence_pointer':r['source_evidence_pointer'],'primary_key':r['primary_key'],'status':'LOCAL_ACCEPTED_NOT_WRITTEN','warnings':rwarnings})

# Any true duplicate target key blocks every member; no arbitrary winner.
bykey=defaultdict(list)
for r in accepted:bykey[(r['logical_table_key'],json.dumps(r['primary_key'],ensure_ascii=False,sort_keys=True))].append(r)
duplicates=[];blocked_ids=set()
for (key,pk),rs in bykey.items():
 if len(rs)>1:
  duplicates.append({'logical_table_key':key,'primary_key':json.loads(pk),'members':[r['source_evidence_pointer'] for r in rs]})
  for r in rs:
   blocked_ids.add(id(r));pending_record(r,[reason('DUPLICATE_TARGET_PRIMARY_KEY','All members excluded; no source/version selection')])
accepted=[r for r in accepted if id(r) not in blocked_ids]

# Original metadata fragments and non-data rows retain exact artifact/filter evidence.
for i,p in enumerate(nat.get('pending_metadata_input_fragments',[])):
 pending.append({'logical_table_key':p['target']['file_code']+'.'+p['target']['table'],'reasons':[reason('METADATA_OWNERSHIP_AND_KEY_PENDING',p['pending_reason'])],'source_evidence_pointer':{'artifact':'PH2/nat_seed_records.json','json_pointer':f'/pending_metadata_input_fragments/{i}'},'preserved_candidate':p,'ready_for_input_batch':False})
excluded_material=[
 {'material':'REG calculated-property metadata','row_count':len(reg['calculated_property_metadata']),'reason':'Numerical cells are native formulas; do not insert cached calculated facts as inputs','source_evidence':{'artifact':'PH2/reg_seed_records.json','json_pointer':'/calculated_property_metadata'}},
 {'material':'REG empty annual templates','row_count':len(reg['annual_empty_scaffolds']),'reason':'Direct observation value absent; no population/GDP/urbanization observation invented','source_evidence':{'artifact':'PH2/reg_seed_records.json','json_pointer':'/annual_empty_scaffolds'}},
 {'material':'REG dropdown options','group_count':len(reg['validation_option_candidates']),'reason':'Existing validation choices lack codebook group/row identity; not a second C00 codebook input','source_evidence':{'artifact':'PH2/reg_seed_records.json','json_pointer':'/validation_option_candidates'}},
 {'material':'NAT metadata source rows','row_count':len(nat['metadata_source_rows']),'reason':'Retain source metadata and mapping; fragments need single-owner and technical-key review','source_evidence':{'artifact':'PH2/nat_seed_records.json','json_pointer':'/metadata_source_rows'}},
]
for filecode in ['REG-V1','NAT-V1']:
 for klass in ['default_false_only_not_fact','ordering_only_review_not_fact','formula_only_not_input_fact']:
  count=sum(r['source_file_code']==filecode and r['row_class']==klass for r in source_rows)
  if count:excluded_material.append({'material':filecode+' '+klass,'row_count':count,'reason':'No direct factual observation; retain original literal/formula/formatting evidence','source_evidence':{'artifact':'PH1/source_row_inventory.csv','filter':{'source_file_code':filecode,'row_class':klass},'sha256':hashes['PH1/source_row_inventory.csv']}})

# Exact codebook collision check. No normalization of spaces/case or group names.
codes=[r for r in records if r['logical_table_key']=='C00.코드북']
codegroups=defaultdict(dict)
for r in codes:
 v=r['values'];codegroups[v['group_code']][v['stored_code']]=v.get('display_name')
validation_code_differences=[]
for v in reg['validation_option_candidates']:
 target_fields={t['field'] for t in v.get('destination_field_contracts',[])}
 if 'setting_status' in target_fields and 'setting_status' in codegroups:
  missing=[x for x in v['options_raw'] if x not in codegroups['setting_status']]
  if missing:validation_code_differences.append({'source_field_id':v['source_field_id'],'target_group':'setting_status','options_missing_exact_code':missing,'action':'Preserve original option spelling; update codebook only after correspondence decision, never normalize silently'})

tables=[]
bytable=defaultdict(list)
for r in accepted:bytable[r['logical_table_key']].append(r)
for key,rs in sorted(bytable.items()):
 b=blocks[key];columns=[c['field_id'] for c in b['columns']]
 entries=[];rows_matrix=[]
 for r in rs:
  rows_matrix.append([r['values'].get(f,None) for f in columns])
  entries.append({'primary_key':r['primary_key'],'write_fields':[f for f in columns if f in r['values']],'migration_record_id':r.get('migration_record_id'),'legacy_locator':r['legacy_locator'],'source_snapshot_id':r['source_snapshot_id'],'source_evidence_pointer':r['source_evidence_pointer'],'source_literal_checks':r['source_verification'],'field_lineage':r.get('field_lineage',{}),'nonliteral_field_provenance':r['nonliteral_field_provenance'],'relation_cache_crosswalk':r.get('legacy_derived_matches',[]),'warnings':r['batch_warnings']})
 tables.append({'logical_table_key':key,'owner_file_code':b['file_code'],'logical_table_id':b['logical_table_id'],'role':'IN','primary_key_fields':b['primary_key_fields'],'column_order':columns,'rows':rows_matrix,'source_evidence':entries,'counts':{'accepted_rows':len(rs),'distinct_primary_keys':len({json.dumps(r['primary_key'],sort_keys=True) for r in rs}),'populated_cells':sum(len(r['values']) for r in rs)},'physical_binding_status':'Resolve against current physical_layout at write time; no cell address is an instruction here','current_layout_capacity':b['data_capacity'],'fits_current_capacity':len(rs)<=b['data_capacity']})

rregions=bytable.get('R10.지역목록',[]);rrelations=bytable.get('R10.지역관계',[])
source_region_ids={r['values']['region_id'] for r in records if r['logical_table_key']=='R10.지역목록'}
accepted_region_ids={r['values']['region_id'] for r in rregions}
source_parent_edges={(r['values']['child_region_id'],r['values']['parent_region_id']) for r in records if r['logical_table_key']=='R10.지역관계'}
accepted_parent_edges={(r['values']['child_region_id'],r['values']['parent_region_id']) for r in rrelations}
fixed_used=[]
for r in accepted:
 for f,v in r['values'].items():
  if isinstance(v,str) and v in issued:fixed_used.append({'logical_table_key':r['logical_table_key'],'field':f,**issued[v]})

ownership_checks=[
 {'check':'N10-only nation name input','status':'STATIC_ACCEPTED_WITH_SPEC_CHANGE_PENDING','C00_neutral_name_written':False,'N10_name_ko_records':sum('name_ko' in r['values'] for r in bytable.get('N10.IN_NATION',[])),'pending_field_count':len(pending_fields),'rule':'C00 holds identifiers only; neutral-name source preserved outside active input. Display at H90, no C00 import.'},
 {'check':'R10 region identity and parent single-input','status':'STATIC_ACCEPTED' if accepted_region_ids==source_region_ids and accepted_parent_edges==source_parent_edges else 'STATIC_FAILED','region_count':len(rregions),'region_ids_distinct':len(accepted_region_ids),'relation_count':len(rrelations),'parent_edges_distinct':len(accepted_parent_edges),'unresolved_parent_count':len(ra['region_graph']['missing_parents']),'unresolved_parent_rule':'Input preservation with explicit warning; no normal-query adoption'},
 {'check':'R50 territory / N30 persons / N20 all office terms','status':'STATIC_BOUNDARY_ONLY_NO_ROWS_TO_TEST','R50_input_records':sum(r['logical_table_key'].startswith('R50.') for r in accepted),'N30_input_records':sum(r['logical_table_key'].startswith('N30.') for r in accepted),'N20_office_definition_records':len(bytable.get('N20.IN_OFFICE',[])),'N20_tenure_records':0,'rule':'Office definitions are not fabricated office-holder or tenure records; no person/tenure seeds exist'},
 {'check':'C00 manual events vs H90 generated events','status':'STATIC_BOUNDARY_ONLY_NO_ROWS_TO_TEST','manual_event_records':0,'generated_event_input_records':0,'rule':'No generated event output inserted as manual input'},
 {'check':'Unversioned defaults vs dated facts','status':'STATIC_ACCEPTED_WITH_PENDING_METADATA','REG_metadata_candidates_pending':sum(r['preserved_candidate'].get('source_sheet_name')=='00_기준_메타' for r in pending),'NAT_metadata_fragments_pending':len(nat['pending_metadata_input_fragments']),'rule':'Do not copy scope/status/date/defaults into incomplete factual records or activate duplicated settings'},
 {'check':'C00 codebook composite-key uniqueness','status':'STATIC_ACCEPTED' if not any(d['logical_table_key']=='C00.코드북' for d in duplicates) else 'STATIC_FAILED','source_records':len(codes),'accepted_records':len(bytable.get('C00.코드북',[])),'group_count':len(codegroups),'REG_validation_options_created_as_code_rows':0,'validation_exact_code_differences':validation_code_differences},
]

assert not native_conflicts
assert len(rregions)==133 and len(accepted_region_ids)==133
assert len(rrelations)==142 and len(accepted_parent_edges)==142
assert accepted_region_ids==source_region_ids and accepted_parent_edges==source_parent_edges
assert not duplicates
assert all(t['fits_current_capacity'] for t in tables)
assert all(len(t['rows'])==len(t['source_evidence']) and all(len(row)==len(t['column_order']) for row in t['rows']) for t in tables)
assert all('neutral_name' not in r['values'] for r in bytable.get('C00.국가식별목록',[]))
assert all(sha(p)==hashes[p.relative_to(RUN).as_posix()] for p in input_paths),'Input changed during audit; regenerate against a coherent snapshot'

summary={'source_target_candidates':len(records),'accepted_input_rows':len(accepted),'accepted_tables':len(tables),'pending_target_records':len(pending)-len(nat['pending_metadata_input_fragments']),'pending_metadata_fragments':len(nat['pending_metadata_input_fragments']),'pending_fields':len(pending_fields),'rejected_duplicate_primary_key_groups':len(duplicates),'native_confirmed_source_checks':sum(len(r['source_verification']) for r in accepted),'region_rows':len(rregions),'relation_rows':len(rrelations),'fixed_data_ids_reused_from_ledger':len(fixed_used),'online_writes':0,'runtime_tests_passed':0}
summary['unique_native_literal_source_cells']=len({e['source_locator'] for r in accepted for e in r['source_verification']})
out={'status':'LOCAL_INPUT_BATCH_CANDIDATES_WITH_PENDING_ITEMS','summary':summary,'logical_binding_only':True,'input_snapshot_hashes':hashes,'layout_version_observed':layout['layout_version'],'schema_change_pending':True,'tables':tables,'pending':pending,'pending_fields':pending_fields,'excluded_material':excluded_material,'ownership_checks':ownership_checks,'primary_key_collisions':duplicates,'fixed_technical_id_ledger_used':fixed_used,'native_evidence_files':[{'path':str(p.relative_to(RUN)),'sha256':sha(p)} for p in native_files],'rules':{'null_matrix_cell':'ABSENT/DO_NOT_WRITE, not blank input, not zero; use write_fields mask and never clear formula cells','existing_false':'Boolean false inside an actual keyed source record is retained; FALSE-only template rows are excluded','values_input':'Literal values with preserved types; eventual write must use RAW or native literal value cells so leading = remains text','pending_revisions':'All 8 rows in 4 standard revision-collision groups withheld; identity dictionary can remain because it selects no revision value','adoption':'No source status upgraded and no new adoption/default/date facts created','physical_rebind':'Resolve logical_table_key and current technical field IDs against the then-current layout and reread headers before any write; do not rely on row order or saved A1 addresses','runtime':'Static source acceptance is not online permission/recalculation/functional test success'},'runtime_status':'미실행'}
out['rules']['fixed_id_resume']='This batch allocates no new data ID. Reuse the fixed ledger. For a later snapshot, resolve the existing original file/gid/cell identity before assigning IDs; snapshot-hash changes alone must not duplicate a previously migrated entity/relation.'
(HERE/'input_batch_candidates.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
print(json.dumps({'table_counts':{t['logical_table_key']:t['counts']['accepted_rows'] for t in tables},'pending_reasons':dict(Counter(x['code'] for p in pending for x in p['reasons']))},ensure_ascii=False))
