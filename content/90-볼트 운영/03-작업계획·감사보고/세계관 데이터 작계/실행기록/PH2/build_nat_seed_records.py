"""Extract literal NAT candidates from the preserved snapshot; never writes online."""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import csv,json,re,hashlib,zipfile,xml.etree.ElementTree as ET,uuid
OUT=Path(__file__).resolve().parent
RUN=OUT.parent; PH1=RUN/'PH1'; SPEC=PH1/'명세확정'; PH0=RUN/'PH0'
readcsv=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig')))
readjson=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
rows=readcsv(PH1/'source_row_inventory.csv')
cells=readcsv(PH1/'literal_cells.csv')
inventory=readjson(PH1/'sheet_inventory.json')
mapping=readcsv(SPEC/'nation_field_spec.csv')+readcsv(SPEC/'common_hub_field_spec.csv')
mapping={x['source_field_id']:x for x in mapping if x['source_file_code']=='NAT-V1'}
ns=readjson(SPEC/'nation_schema.json');cs=readjson(SPEC/'common_hub_schema.json')
schemas={(t['file_code'],t['table_id']):t for t in ns['tables']+cs['tables']}
inv={x['source_sheet_name']:x for x in inventory if x['source_file_code']=='NAT-V1'}
ri={(x['source_sheet_id'],int(x['source_row'])):x for x in rows if x['source_file_code']=='NAT-V1'}
snapshot_hash=hashlib.sha256((PH0/'NAT-V1_online.xlsx').read_bytes()).hexdigest()
expected_hash=next(iter(inv.values()))['xlsx_sha256'];assert snapshot_hash==expected_hash
snapshot_id='NAT-V1:sha256:'+snapshot_hash
cells_by_row=defaultdict(list)
for c in cells:
 if c['source_file_code']=='NAT-V1':cells_by_row[(c['source_sheet_id'],int(re.search(r'\d+',c['cell']).group()))].append(c)

# Independent XML verification rejects cached formula results even if an inventory
# row classification was optimistic. Native formula results are never literal seeds.
S='http://schemas.openxmlformats.org/spreadsheetml/2006/main';q=lambda x:'{'+S+'}'+x
xmlcells={}
with zipfile.ZipFile(PH0/'NAT-V1_online.xlsx') as z:
 shared=[]
 if 'xl/sharedStrings.xml' in z.namelist():
  shared=[''.join(t.text or '' for t in e.iter(q('t'))) for e in ET.fromstring(z.read('xl/sharedStrings.xml'))]
 for sheet,si in inv.items():
  root=ET.fromstring(z.read(si['xlsx_xml_path']))
  for c in root.iter(q('c')):
   if c.find(q('f')) is not None:
    xmlcells[(str(si['source_sheet_id']),c.attrib['r'])]={'formula':True};continue
   v=c.find(q('v')); value=None
   if c.attrib.get('t')=='s' and v is not None:value=shared[int(v.text)]
   elif c.attrib.get('t')=='inlineStr':value=''.join(t.text or '' for t in c.iter(q('t')))
   elif v is not None:
    value=(v.text=='1') if c.attrib.get('t')=='b' else v.text
   xmlcells[(str(si['source_sheet_id']),c.attrib['r'])]={'formula':False,'value':value}

def decode(c):
 raw=json.loads(c['value_json']); typ=c['value_type']
 if typ=='number':
  d=Decimal(str(raw))
  if d==d.to_integral_value() and abs(d)<=9007199254740991:return int(d),raw,'exact numeric literal; integer-compatible conversion, original token preserved'
  return str(raw),raw,'decimal text retained; numerical write needs precision check'
 return raw,raw,'identity'
def selector_matches(selector,row,cellsrow):
 if not selector or selector=='all_data_rows':return True
 m=re.match(r'row=(\d+);key=(.*)',selector)
 if m:
  sourcekey=next((json.loads(c['value_json']) for c in cellsrow if c['source_column']=='A'),None)
  return row==int(m.group(1)) and sourcekey==m.group(2)
 return False
def pks(t):return t.get('primary_key') or [t['record_key']]
def field_ids(t):return {f.get('field_id',f.get('field')) for f in t['fields']}
records=[];pending=[];meta=[];ledger=[];exclusions=Counter();decisions=[]
meta_tables=Counter();seedcellcount=0;verifiedcells=0;default_false_kept=0
existing_namespace='5c70e50a-3e4f-5f2a-a791-d57e1a8e1aa3'
eligible_sheets={m['source_sheet_name'] for m in mapping.values() if any(t['role']=='input' for t in json.loads(m['targets_json']))}
for (sid,rowno),source_row in sorted(ri.items(),key=lambda x:(inv[x[1]['source_sheet_name']]['source_sheet_name'],x[0][1])):
 sheet=source_row['source_sheet_name'];rowclass=source_row['row_class'];rowcells=cells_by_row.get((sid,rowno),[])
 if rowclass=='header_or_query_controls':exclusions['header_or_query_controls_rows']+=1;continue
 if sheet=='00_기준_메타':
  sourcekey=next((json.loads(c['value_json']) for c in rowcells if c['source_column']=='A'),None)
  obj={'source_sheet_name':sheet,'source_sheet_id':sid,'source_row':rowno,'source_key':sourcekey,'legacy_locator':source_row['legacy_locator'],'source_snapshot_id':snapshot_id,'raw_cells':[],'mapped_fragments':[],'active_input_record_created':False}
  for c in rowcells:
   value,raw,conversion=decode(c); f=mapping.get(f'NAT-V1:{sid}:{c["source_column"]}')
   obj['raw_cells'].append({'cell':c['cell'],'value_type':c['value_type'],'raw_value':raw,'value':value,'legacy_locator':c['legacy_locator']})
   if not f:continue
   for target in json.loads(f['targets_json']):
    if selector_matches(target.get('source_selector'),rowno,rowcells):
     frag={'source_field_id':f['source_field_id'],'source_cell':c['cell'],'source_value':value,'source_raw_value':raw,'target':target,'target_record_key':pks(schemas[(target['file_code'],target['table'])]),'status':'원문 후보; 중복설정 대조·기술PK 발급 전 활성 이관 대기'}
     obj['mapped_fragments'].append(frag)
     if target['role']=='input':
      pending.append(frag|{'legacy_locator':source_row['legacy_locator'],'source_snapshot_id':snapshot_id,'pending_reason':'동일 공통기준/정책의 REG·NAT 후보와 대조해 단일원본 확정. 행별 입력 원본을 중복 생성하지 않음.','ready_for_write':False})
      meta_tables[target['file_code']+'.'+target['table']]+=1
  # Preserve formula presence separately: no cached literal is synthesized.
  formula_cells=[addr for (ss,addr),xc in xmlcells.items() if ss==sid and int(re.search(r'\d+',addr).group())==rowno and xc['formula']]
  obj['formula_cells_not_seeded']=formula_cells
  meta.append(obj)
  locator=source_row['legacy_locator']
  proposed='nat-meta-'+str(uuid.uuid5(uuid.UUID(existing_namespace),locator+'|C00.설정출처대응'))
  ledger.append({'allocation_key':locator+'|C00.설정출처대응.metadata_mapping_id','proposed_id':proposed,'id_kind':'technical_migration_mapping','status':'proposed_not_allocated','existing_entity_id_replaced':False,'action':'공통 영속ID 원장 중복조회 후 같은 allocation_key 재사용; 원장에 고정 저장한 다음에만 발급 처리'})
  continue
 if rowclass=='default_false_only_not_fact':exclusions['default_false_only_rows']+=1;continue
 if rowclass=='formula_only_not_input_fact':exclusions['formula_only_rows']+=1;continue
 if sheet not in eligible_sheets:
  exclusions['non_input_or_other_shard_rows']+=1;continue
 if not rowclass.startswith('literal_input_candidate'):exclusions['non_candidate_rows']+=1;continue
 grouped={}
 for c in rowcells:
  fid=f'NAT-V1:{sid}:{c["source_column"]}';f=mapping.get(fid)
  if not f:exclusions['unmapped_literal_cells']+=1;continue
  xc=xmlcells[(sid,c['cell'])]
  assert not xc['formula'],(sid,c['cell'])
  value,raw,conversion=decode(c)
  if c['value_type']=='number':assert Decimal(str(xc['value']))==Decimal(str(raw))
  else:assert xc['value']==raw,(sheet,c['cell'],xc['value'],raw)
  verifiedcells+=1
  targets=[t for t in json.loads(f['targets_json']) if t['role']=='input' and selector_matches(t.get('source_selector'),rowno,rowcells)]
  if not targets:exclusions['derived_or_archive_literal_cells']+=1;continue
  for target in targets:
   tk=(target['file_code'],target['table']);schema=schemas[tk]
   rec=grouped.setdefault(tk,{'target_file_code':tk[0],'target_table':tk[1],'record_kind':'world_fact_or_reference_input','primary_key_fields':pks(schema),'values':{},'field_lineage':{},'source_file_code':'NAT-V1','source_file_id':source_row['source_file_id'],'source_sheet_id':sid,'source_sheet_name':sheet,'source_row':rowno,'legacy_locator':source_row['legacy_locator'],'source_snapshot_id':snapshot_id,'write_status':'candidate_only_not_written','ready_for_native_population':True,'online_validation_status':'미실행'})
   tf=target['field'];assert tf in field_ids(schema)
   if tf in rec['values'] and rec['values'][tf]!=value:raise ValueError('target collision')
   rec['values'][tf]=value
   rec['field_lineage'][tf]={'source_field_id':fid,'source_cell':c['cell'],'source_type':c['value_type'],'raw_value':raw,'typed_value':value,'conversion':conversion,'legacy_locator':c['legacy_locator'],'transform_rule':target['rule']}
   seedcellcount+=1
   if value is False:default_false_kept+=1
 for tk,rec in grouped.items():
  schema=schemas[tk];ids=field_ids(schema)
  for field,value in [('legacy_locator',rec['legacy_locator']),('source_snapshot_id',snapshot_id)]:
   if field in ids:rec['values'][field]=value
  if tk==('C00','출처레지스트리'):
   rec['values']['source_namespace']='NAT-V1'
   rec['technical_metadata_basis']={'source_namespace':'원본 식별 namespace; 기존 source_id를 변경하지 않고 파일간 동일 문자열 충돌을 구분'}
  missing=[k for k in rec['primary_key_fields'] if rec['values'].get(k) in ('',None)]
  rec['primary_key']={k:rec['values'].get(k) for k in rec['primary_key_fields']}
  rec['missing_primary_keys']=missing
  if missing:
   rec['ready_for_native_population']=False;rec['pending_reason']='기존 ID 없는 불완전 입력; locator 기반 기술ID 발급·검토 필요'
  if tk[0] in ('N10','N20'):
   rec['missing_scope_or_classification_fields']=[f for f in ('nation_id','route','era','엔티티 종류') if f in ids and rec['values'].get(f) in ('',None)]
   rec['raw_status_preserved']=rec['values'].get('setting_status')
   rec['no_default_fill']='meta default_nation_id/default_planet_id는 레코드의 미입력 범위/분류/정원/기간에 자동 복사하지 않음'
  records.append(rec)

# Inventory all NAT field-owned input sheets, including empty schemas, rather than
# interpreting a absent candidate record as a missing migration definition.
per_sheet=[]
for name,si in inv.items():
 source_records=[r for r in records if r['source_sheet_name']==name]
 source_rows=[r for r in rows if r['source_file_code']=='NAT-V1' and r['source_sheet_name']==name]
 covered_fields=[m for m in mapping.values() if m['source_sheet_name']==name]
 input_fields=[m['source_field_id'] for m in covered_fields if any(t['role']=='input' for t in json.loads(m['targets_json']))]
 per_sheet.append({'source_sheet_name':name,'source_sheet_id':si['source_sheet_id'],'classified_rows':dict(Counter(r['row_class'] for r in source_rows)),'declared_input_field_count':len(input_fields),'seed_records':len(source_records),'status':'metadata_fragments_pending_reconciliation' if name=='00_기준_메타' else 'seeds_extracted' if source_records else 'no_actual_input_records_in_snapshot' if input_fields else 'derived_archive_or_other_shard','default_false_and_formula_rows_are_not_facts':True})

counts=Counter(r['target_file_code']+'.'+r['target_table'] for r in records)
assert counts['N10.IN_NATION']==1 and counts['N20.IN_OFFICE']==10
assert all(r['source_sheet_name']!='31_인물_마스터' for r in records)
assert len({(r['target_file_code'],r['target_table'],json.dumps(r['primary_key'],ensure_ascii=False,sort_keys=True)) for r in records})==len(records)
assert all(not r['missing_primary_keys'] for r in records)
source_seed_cols={r['source_sheet_name'] for r in records}
assert not any(r['source_sheet_name'].startswith(('87_','88_','98_','99_')) for r in records)
decisions=[
 {'issue_id':'NAT-SEED-001','scope':'00_기준_메타','status':'이관판단 대기','action':'REG/NAT의 공통 기준·정책 필드를 대조하고 동일사실은 하나의 C00 원본으로 유지. 각 메타 sourcekey/값/설명/selector는 metadata_source_rows에 보존. 기술PK는 계획된 영속원장에서 발급 전 활성 입력행 생성 금지.'},
 {'issue_id':'NAT-SEED-002','scope':'N20.IN_OFFICE','status':'원문 공란 유지','action':'미입력 nation_id/route/era/엔티티 종류 및 정원은 자동 채우지 않음. source_role 종류와 설명은 그대로 보존. 역할별 검증 중 적용불명은 미확인으로 표시.'},
 {'issue_id':'NAT-SEED-003','scope':'C00.출처레지스트리','status':'namespace 보존 후보','action':'source_namespace=NAT-V1로 기존 source_id 3개 유지. 다른 원본의 출처 ID와 URL/판본 비교 전 자동 병합하지 않음. SRC-FORMAT는 서식근거이며 역사실적근거로 확대하지 않음.'},
 {'issue_id':'NAT-SEED-004','scope':'C00.코드북','status':'원문값 보존·활성목록 채택 검증 대기','action':'A:H의 실제 행만 코드 원본으로 추출. J:BB 보조목록은 파생 목록이라 이중 입력하지 않음. 사용상태를 정본상태로 변환하지 않음.'}
]
meta_basis={'source_snapshot_file':'PH0/NAT-V1_online.xlsx','source_snapshot_sha256':snapshot_hash,'source_inventory_sha256_match':True,'source_file_id':'1mTRKFfCFtiTmuAR6QwrslcBI6Q-wutYzVP_weDAW9uI','extraction_is_live_source_read':False,'online_actions':0,'facts_written_online':0,'phase_claim':'로컬 이관 후보 추출; PH2/운영 이관 완료 아님'}
seed={'project':'세계관 데이터 V2',**meta_basis,'records':records,'pending_metadata_input_fragments':pending,'metadata_source_rows':meta,'record_counts_by_table':dict(counts),'data_generation_policy':'기존 literal 입력과 원문 메타만 추출. 자료·ID·설정·기간·인물 생성 없음. technical namespace/locator는 이관메타.','exclusion_policy':'FALSE만 있는 템플릿행, 수식 결과·캐시, spill 출력, 헤더·조회설명·과거검증 레이블은 운영 원자료에서 제외하며 PH0 보존파일은 유지.'}
analysis={'project':'세계관 데이터 V2',**meta_basis,'summary':{'seed_record_count':len(records),'record_counts_by_table':dict(counts),'N30_actual_person_records':0,'N20_actual_office_records':10,'N10_actual_nation_records':1,'C00_codebook_records':counts['C00.코드북'],'C00_source_records':counts['C00.출처레지스트리'],'metadata_source_rows':len(meta),'pending_metadata_input_fragments':len(pending),'raw_seed_cell_assignments':seedcellcount,'xml_checked_literal_cells':verifiedcells,'default_false_retained_inside_actual_records':default_false_kept,'duplicate_candidate_keys':0,'missing_existing_primary_keys':0,'online_tests_passed':0},'exclusion_counts':dict(exclusions),'per_sheet':per_sheet,'decisions':decisions,'id_ledger_plan':{'status':'계획만; ID 실제 발급/기존 ID 교체 없음','namespace_seed':existing_namespace,'technical_id_candidates':ledger,'rule':'전역 공통 ledger의 allocation_key 존재 여부를 먼저 확인. 이미 발급되었으면 저장된 ID를 사용. locator의 원문 snapshot을 보존하고 동일 기록의 후속 snapshot 승계는 별도 source_record_match로 대응.'},'missing_data_policy':'빈 N30/N40/N50 등은 스키마만 존재. 시험·가상 자료를 운영 후보로 넣지 않음.','source_ownership_boundary':'NAT03 영토는 R50 대응 담당; 현재 default_false-only 500행으로 실질 자료 0. REG 출처/기준은 다른 산출물과 합쳐 정합성 비교 필요.','snapshot_recheck_gate':'실제 온라인 쓰기 전 root의 실행시점 원본 변경 검증/PH0 게이트를 확인. 이 스크립트는 저장된 스냅샷 해시만 검증.'}
for name,obj in [('nat_seed_records.json',seed),('nat_migration_candidate_analysis.json',analysis)]:
 (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(analysis['summary'],ensure_ascii=False,indent=2))
