"""Extract REG snapshot candidates without modifying source files or online documents.

No workbook authorship: JSON transfer manifests only. Original source values,
formula evidence and identifiers are never promoted to adopted worldbuilding facts.
"""
from pathlib import Path
import csv, json, re, hashlib
from collections import defaultdict, Counter
from decimal import Decimal, InvalidOperation

HERE=Path(__file__).resolve().parent
PH1=HERE.parent/'PH1'; PH0=HERE.parent/'PH0'; SPEC=PH1/'명세확정'
SID='1EACdRIiAPGk4LAbttpXZiJd_cuqIh-cVi4jQsbfmqDw'
SNAP='REG-V1:sha256:'+hashlib.sha256((PH0/'REG-V1_online.xlsx').read_bytes()).hexdigest()
def readcsv(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def colnum(n):
 s=''
 while n:n,k=divmod(n-1,26);s=chr(k+65)+s
 return s
def rownum(cell):return int(re.search(r'\d+',cell)[0])
def stable(kind,locator):return kind+'.reg.'+hashlib.sha256((kind+'|'+locator).encode()).hexdigest()[:24]

fields={x['source_field_id']:x for x in readcsv(SPEC/'field_spec.csv') if x['source_file_code']=='REG-V1'}
inv=[x for x in json.loads((PH1/'sheet_inventory.json').read_text(encoding='utf-8-sig')) if x['source_file_code']=='REG-V1']
rows=[x for x in readcsv(PH1/'source_row_inventory.csv') if x['source_file_code']=='REG-V1']
lits=[x for x in readcsv(PH1/'literal_cells.csv') if x['source_file_code']=='REG-V1']
cache=[x for x in readcsv(PH1/'formula_nonempty_cache_observations.csv') if x['source_file_code']=='REG-V1']
schemas=[json.loads((SPEC/f).read_text(encoding='utf-8')) for f in ['common_hub_schema.json','region_schema.json','nation_schema.json']]
tables={(t['file_code'],t['table_id']):t for s in schemas for t in s['tables']}
native={};nativefiles=[];native_conflicts=[]
files=list(PH0.glob('REG_headers_*.json'))+[p for p in PH0.glob('native_data_*.json') if re.fullmatch(r'native_data_\d+\.json',p.name)]
for p in files:
 obj=json.loads(p.read_text(encoding='utf-8-sig'));obj=obj.get('response',obj)
 if obj.get('spreadsheetId')!=SID:continue
 nativefiles.append(p)
 for sh in obj.get('sheets',[]):
  title=sh['properties']['title']
  for gd in sh.get('data',[]):
   for rr,row in enumerate(gd.get('rowData',[]),gd.get('startRow',0)+1):
    for cc,cell in enumerate(row.get('values',[]),gd.get('startColumn',0)+1):
     key=(title,f'{colnum(cc)}{rr}')
     if key in native and native[key].get('userEnteredValue')!=cell.get('userEnteredValue'):native_conflicts.append({'sheet':title,'cell':key[1]})
     native[key]=cell
byrow=defaultdict(dict)
for x in lits:
 if x['cell_role']!='header_or_controls':byrow[(x['source_sheet_name'],rownum(x['cell']))][x['source_column']]=x
rowindex={(x['source_sheet_name'],int(x['source_row'])):x for x in rows}
def raw(x):return json.loads(x['value_json'])
def value(x):
 v=raw(x)
 if x['value_type']=='number':
  try:
   d=Decimal(v)
   return int(d) if d==d.to_integral_value() and abs(d)<2**53 else float(d)
  except (InvalidOperation,TypeError,ValueError):return v
 return v
def cells(k):return {c:raw(x) for c,x in byrow[k].items()}

candidate_classes={'literal_input_candidate_with_id','literal_input_candidate_without_id_review'}
candidates=[];formula_metadata=[];config_records=[];derived_literals=[];input_conflicts=[];native_unverified=[];cell_counts=Counter()
field_lineage=[];targetmap={};id_ledger=[]
calendar={'civil_day','civil_year_days','year_correction','months_per_year','days_per_month'}

def chosen(d,sheet,rn,values):
 selector=d.get('source_selector','')
 if selector.startswith('row='):
  m=re.match(r'row=(\d+);key=(.*)',selector)
  return bool(m and rn==int(m[1]) and str(values.get('A'))==m[2])
 if sheet=='10_행성_기본값':
  p=values.get('B');formula='formulaValue' in native.get((sheet,'D'+str(rn)),{}).get('userEnteredValue',{})
  if d['file_code']=='C00':return p in calendar
  return p not in calendar and ((d['table']=='행성기본값_계산')==formula)
 return True

def add_target(d,row,field,cellobj,v):
 # Region parents become one relation per parent slot below, never one scalar overwrite.
 if row['source_sheet_name']=='01-지역 마스터' and d['table']=='지역관계':return
 key=(d['file_code'],d['table'],row['legacy_locator'])
 rec=targetmap.setdefault(key,{'file_code':key[0],'table':key[1],'migration_record_id':stable('mig',key[0]+'|'+key[1]+'|'+key[2]),'source_file_code':'REG-V1','source_sheet_name':row['source_sheet_name'],'source_row':int(row['source_row']),'legacy_locator':key[2],'source_snapshot_id':SNAP,'fields':{},'field_lineage':{},'migration_status':'LOCAL_CANDIDATE_ONLY','adoption_status':'未採択'.replace('未採択','미채택'),'candidate_role':d['role']})
 old=rec['fields'].get(d['field'])
 if old is not None and old!=v:input_conflicts.append({'key':key,'field':d['field'],'values':[old,v]})
 rec['fields'][d['field']]=v
 rec['field_lineage'][d['field']]={'source_field_id':field['source_field_id'],'source_cell':cellobj['cell'],'source_locator':cellobj['legacy_locator'],'raw_type':cellobj['value_type'],'raw_value':raw(cellobj),'rule':d.get('rule','')}

for row in rows:
 sheet=row['source_sheet_name'];rn=int(row['source_row']);klass=row['row_class'];k=(sheet,rn)
 if klass=='header_or_query_controls':continue
 if klass not in candidate_classes and not (sheet=='11_행성_연간지표' and klass=='derived_or_configuration_literal_review'):continue
 vals=cells(k)
 rec={'source_file_code':'REG-V1','source_file_id':SID,'sheet_id':int(row['source_sheet_id']),'sheet':sheet,'row':rn,'row_class':klass,'legacy_locator':row['legacy_locator'],'source_snapshot_id':SNAP,'cells':[],'input_literal_count':0,'migration_status':'LOCAL_CANDIDATE_ONLY'}
 for c,x in byrow[k].items():
  fid=f"REG-V1:{row['source_sheet_id']}:{c}";f=fields[fid];nv=native.get((sheet,x['cell']));uev={} if nv is None else nv.get('userEnteredValue',{})
  if nv is None and raw(x)=='':classification='export_empty_native_omitted'
  elif nv is None:classification='xlsx_literal_native_unverified';native_unverified.append(x['legacy_locator'])
  elif 'formulaValue' in uev:classification='native_formula_not_input'
  elif not uev and raw(x)=='' and not nv.get('effectiveValue'):classification='native_blank_export_empty'
  elif not uev:classification='native_effective_or_spill_not_input'
  else:classification='native_user_literal'
  cell_counts[classification]+=1
  ent={'source_field_id':fid,'source_column':c,'source_cell':x['cell'],'source_locator':x['legacy_locator'],'source_type':x['value_type'],'raw_value':raw(x),'native_classification':classification,'targets':json.loads(f['targets_json'])}
  rec['cells'].append(ent)
  if classification=='native_user_literal':rec['input_literal_count']+=1
  if classification in {'native_formula_not_input','native_effective_or_spill_not_input','export_empty_native_omitted','native_blank_export_empty'}:continue
  for d in ent['targets']:
   if not chosen(d,sheet,rn,vals):continue
   lineage={'source_cell_locator':x['legacy_locator'],'source_field_id':fid,'destination':d,'native_classification':classification}
   field_lineage.append(lineage)
   if d['role'] in ['input','archive'] and klass in candidate_classes:
    add_target(d,row,f,x,value(x))
   elif klass in candidate_classes and classification=='native_user_literal' and not (sheet=='10_행성_기본값' and d['role']=='calculated'):
    derived_literals.append({'source_locator':x['legacy_locator'],'source_field_id':fid,'raw_value':raw(x),'target_role':d['role'],'target':d,'reason':'literal override in a declared derived/display field; preserve without treating display name as another entity master'})
 formula_prop=sheet=='10_행성_기본값' and 'formulaValue' in native.get((sheet,'D'+str(rn)),{}).get('userEnteredValue',{})
 if formula_prop:
  rec['reason']='property metadata is direct, numerical value is native formula; preserve metadata and reimplement, no input numerical fact'
  rec['formula']=native[(sheet,'D'+str(rn))]['userEnteredValue']['formulaValue']
  formula_metadata.append(rec)
 elif klass in candidate_classes:candidates.append(rec)
 elif sheet=='11_행성_연간지표':
  rec['reason']='annual observation scaffold/configuration; direct value K absent; zero factual observations'
  config_records.append(rec)

# Complete seed-row keys from observed identifiers or fixed migration-only IDs.
for key,rec in targetmap.items():
 f,t,locator=key;vs=rec['fields'];srcvals=cells((rec['source_sheet_name'],rec['source_row']))
 if t=='基準改正'.replace('基準改正','기준개정이력'):
  vs['revision_id']=stable('rev',locator);id_ledger.append({'kind':'revision_id','id':vs['revision_id'],'legacy_locator':locator,'generated_once_rule':'deterministic SHA-256 24hex; reuse this ledger; no source entity ID replaced'})
 if t=='개체별칭':
  vs.update(alias_id=stable('alias',locator+'|D'),entity_namespace='nation',entity_id=srcvals['B']);id_ledger.append({'kind':'alias_id','id':vs['alias_id'],'legacy_locator':locator})
 if t=='국가목록원문속성':
  rec['source_entity_id']=srcvals['B']
  rec['requires_review']='N10 source-attribute contract lacks nation_id field; keep observed identity in lineage until owner resolves join contract'
  vs['record_id']=stable('record',locator)
  id_ledger.append({'kind':'record_id','id':vs['record_id'],'legacy_locator':locator})
 if t=='출처레지스트리':vs['source_namespace']='REG-V1'
 if t=='지역목록':
  rec['source_setting_status']=vs.get('setting_status');rec['adoption_status']='원문 상태 보존; 새 정본 승격 없음'
 if t=='행성기본값':
  vs['property_revision_id']=stable('prop',locator);id_ledger.append({'kind':'property_revision_id','id':vs['property_revision_id'],'legacy_locator':locator})
 tab=tables.get((f,t),{})
 pk=tab.get('primary_key_fields',tab.get('primary_key',[]))
 rec['missing_primary_keys']=[x for x in pk if x not in vs or vs[x] in ['',None]]
 rec['record_class']='source_definition_or_configuration' if rec['source_sheet_name']=='00_기준_메타' else 'input_candidate'
 if rec['source_sheet_name']=='10_행성_기본값' and rec['fields'].get('original_property_id') in calendar:
  rec['requires_review']='existing C00 standard_id/revision correspondence; no invented standard_id and no adoption'

# Deduplicate only the dictionary of existing standard identifiers, not revisions.
dedup=defaultdict(list)
for key,rec in list(targetmap.items()):
 if key[0]=='C00' and key[1]=='공통기준':dedup[rec['fields']['standard_id']].append((key,rec))
for sid,items in dedup.items():
 head=items[0][1];head['all_source_locators']=[v['legacy_locator'] for _,v in items]
 for key,_ in items[1:]:del targetmap[key]

# Parent relations derive from direct parent cells. Legacy calculated relation IDs
# and output rows are crosswalk evidence, not a second input table.
regions=[x for x in targetmap.values() if (x['file_code'],x['table'])==('R10','지역목록')]
region_ids={x['fields']['region_id'] for x in regions}
relation_cache=defaultdict(dict)
for x in cache:
 if x['source_sheet_name']=='02_지역_관계':relation_cache[rownum(x['cell'])][re.match(r'[A-Z]+',x['cell'])[0]]=json.loads(x['cache_value_json'])
cache_by_parent=defaultdict(list)
for rn,d in relation_cache.items():
 if d.get('B') and d.get('D'):cache_by_parent[(d['B'],d['D'])].append({'cache_row':rn,'legacy_relation_id':d.get('A'),'original_location':d.get('G'),'relation_type':d.get('F'),'classification':'formula_cache_not_input'})
parent_groups=defaultdict(list)
for rg in regions:
 data=byrow[(rg['source_sheet_name'],rg['source_row'])]
 for c in ['G','I']:
  if c in data and raw(data[c]):parent_groups[(rg['fields']['region_id'],raw(data[c]))].append({'region':rg,'cell':data[c]})
relations=[];missing=[];duplicate_parent_slots=[]
for (child,parent),items in parent_groups.items():
 first=items[0];rg=first['region'];loc=first['cell']['legacy_locator'];cached=cache_by_parent.get((child,parent),[])
 rv={'relation_id':stable('rel',loc),'child_region_id':child,'parent_region_id':parent,'relation_source_slot':first['cell']['source_column'],'legacy_relation_id':cached[0]['legacy_relation_id'] if len(cached)==1 else None}
 if cached and len({x['relation_type'] for x in cached})==1:rv['relation_type']=cached[0]['relation_type']
 rec={'file_code':'R10','table':'지역관계','migration_record_id':stable('mig',loc),'legacy_locator':loc,'source_snapshot_id':SNAP,'fields':rv,'all_source_locators':[x['cell']['legacy_locator'] for x in items],'legacy_derived_matches':cached,'inherited_region_status':rg['fields'].get('setting_status'),'parent_reference_status':'present_in_source_regions' if parent in region_ids else 'unresolved_original_parent','date_status':'기간 원문 없음; 날짜 생성 안 함','migration_status':'LOCAL_CANDIDATE_ONLY','adoption_status':'미채택','candidate_role':'input'}
 relations.append(rec);id_ledger.append({'kind':'relation_id','id':rv['relation_id'],'legacy_locator':loc,'original_relation_ids':[x['legacy_relation_id'] for x in cached]})
 if len(items)>1:duplicate_parent_slots.append({'child':child,'parent':parent,'source_cells':[x['cell']['cell'] for x in items],'action':'one candidate relationship, all source locators preserved'})
 if parent not in region_ids:missing.append({'child':child,'parent':parent,'source_locator':loc,'original_display_name':cells((rg['source_sheet_name'],rg['source_row'])).get('H' if first['cell']['source_column']=='G' else 'J'),'action':'keep original parent ID and display text; do not synthesize missing entity'})

# Cycles among known IDs and cache crosswalk completeness.
graph=defaultdict(set)
for ch,pa in parent_groups:graph[ch].add(pa)
cycles=[]
def visit(node,path):
 if node in path:
  cyc=path[path.index(node):]+[node]
  if cyc not in cycles:cycles.append(cyc)
  return
 for nxt in graph.get(node,[]):visit(nxt,path+[node])
for node in region_ids:visit(node,[])
standards=defaultdict(list)
for rec in targetmap.values():
 if rec['file_code']=='C00' and rec['table']=='기준개정이력' and rec['fields'].get('standard_id'):standards[rec['fields']['standard_id']].append(rec)
duplicates=[{'standard_id':s,'revision_count':len(rs),'revisions':[{'revision_id':v['fields']['revision_id'],'value_raw':v['fields'].get('value_raw'),'setting_status':v['fields'].get('setting_status'),'legacy_locator':v['legacy_locator']} for v in rs],'action':'preserve all; no latest-row adoption'} for s,rs in standards.items() if len(rs)>1]

dateissues=[]
for rec in candidates:
 for cell in rec['cells']:
  for d in cell['targets']:
   if d['field'] in ['start_raw','end_raw','existence_start_raw','existence_end_raw','time_raw'] and cell['raw_value'] not in ['',None]:
    rawdate=cell['raw_value'];recognized=re.fullmatch(r'(제\d+기)\s+(\d+)년',str(rawdate))
    dateissues.append({'source_locator':cell['source_locator'],'raw':rawdate,'target':d,'lexically_explicit_components':{'era_raw':recognized[1],'year':int(recognized[2]),'precision':'year'} if recognized else None,'status':'기년판본/루트 대응 미확정; 원문 보존' if recognized else '미분류 원문; 월일/끝연도/지속 여부 추정 금지'})

per_sheet=[]
for item in inv:
 sh=item['source_sheet_name'];rr=[x for x in rows if x['source_sheet_name']==sh]
 per_sheet.append({'sheet':sh,'sheet_id':item['source_sheet_id'],'row_classes':dict(Counter(x['row_class'] for x in rr)),'input_candidate_rows':sum(x['sheet']==sh for x in candidates),'calculated_property_metadata_rows':sum(x['sheet']==sh for x in formula_metadata),'configuration_scaffold_rows':sum(x['sheet']==sh for x in config_records),'source_formula_cells':item['formula_cells'],'style_only_cells_excluded':item.get('style_only_cells_excluded',0),'fact_empty':not any(x['sheet']==sh for x in candidates)})
alltargets=list(targetmap.values())+relations
# Dropdown lists are existing validation configuration, not asserted entity facts.
# Group only observed native cells; do not claim unobserved full-column coverage.
validation_lists={}
sheet_ids={x['source_sheet_name']:x['source_sheet_id'] for x in inv}
for (sheet,cell),nativecell in native.items():
 dv=nativecell.get('dataValidation',{})
 condition=dv.get('condition',{})
 if condition.get('type')!='ONE_OF_LIST':continue
 col=re.match(r'[A-Z]+',cell)[0]
 fid=f"REG-V1:{sheet_ids[sheet]}:{col}"
 options=[x.get('userEnteredValue') for x in condition.get('values',[])]
 key=(fid,json.dumps(dv,ensure_ascii=False,sort_keys=True))
 group=validation_lists.setdefault(key,{'source_field_id':fid,'source_sheet_name':sheet,'source_column':col,'options_raw':options,'validation_raw':dv,'observed_native_cells':[],'classification':'source_validation_configuration_not_codebook_fact','adoption_status':'미채택','destination_field_contracts':json.loads(fields[fid]['targets_json']) if fid in fields else []})
 group['observed_native_cells'].append(cell)
unknown_target_fields=[];missing_key_records=[]
for rec in alltargets:
 tab=tables.get((rec['file_code'],rec['table']),{})
 defined={f['field_id'] for f in tab.get('fields',[])}
 unknown_target_fields.extend({'table':rec['file_code']+'.'+rec['table'],'field':f,'source_locator':rec['legacy_locator']} for f in rec['fields'] if f not in defined)
 if rec.get('missing_primary_keys'):missing_key_records.append({'table':rec['file_code']+'.'+rec['table'],'missing_primary_keys':rec['missing_primary_keys'],'source_locator':rec['legacy_locator'],'action':'retain raw candidate; do not assign semantic unit/metric/definition/era/policy identity without correspondence review'})
numeric_zero=[{'source_locator':x['legacy_locator'],'raw_value':raw(x),'native_confirmed':(x['source_sheet_name'],x['cell']) in native} for x in lits if x['cell_role']!='header_or_controls' and x['value_type']=='number' and raw(x) is not None and Decimal(raw(x))==0]
def numeric_obs(sheets_columns):
 return sum(1 for x in candidates if x['sheet'] in sheets_columns and any(c['source_column']==sheets_columns[x['sheet']] and c['source_type']=='number' and c['raw_value'] is not None and c['native_classification']=='native_user_literal' for c in x['cells']))
summary={'source_tabs':len(inv),'source_input_candidate_rows':len(candidates),'source_fact_or_definition_rows':sum(x['sheet']!='00_기준_메타' for x in candidates),'source_metadata_configuration_rows':sum(x['sheet']=='00_기준_메타' for x in candidates),'calculated_property_metadata_rows':len(formula_metadata),'annual_empty_scaffold_rows':len(config_records),'annual_scaffold_metrics':dict(Counter(cells((x['sheet'],x['row'])).get('F') for x in config_records)),'regional_population_numeric_observations':numeric_obs({'20 인구':'E','12_지역_인구':'G'}),'regional_economy_numeric_observations':numeric_obs({'40 경제 지역값':'G','13_지역_경제':'H'}),'region_rows':len(regions),'unique_region_ids':len(region_ids),'parent_relation_candidates':len(relations),'multiple_parent_regions':sum(len(v)>1 for v in graph.values()),'duplicate_same_parent_slot_groups':len(duplicate_parent_slots),'missing_parent_ids':len({x['parent'] for x in missing}),'known_graph_cycles':len(cycles),'standard_revision_candidates':sum(len(x) for x in standards.values()),'unique_standard_ids':len(standards),'duplicate_standard_id_groups':len(duplicates),'local_target_record_candidates':len(alltargets),'literal_native_classification':dict(cell_counts),'native_conflicts':len(native_conflicts),'target_assignment_conflicts':len(input_conflicts),'native_unverified_nonempty_literal_cells':len(native_unverified),'direct_numeric_zero_literals':len(numeric_zero),'online_writes':0,'operational_tests_passed':0,'online_migrated_records':0}
summary.update(observed_dropdown_configuration_groups=len(validation_lists),observed_dropdown_option_values=sum(len(x['options_raw']) for x in validation_lists.values()),records_with_unresolved_primary_keys=len(missing_key_records),unknown_target_fields=len(unknown_target_fields))
seed={'status':'LOCAL_MIGRATION_CANDIDATES_NOT_ONLINE','source_snapshot_id':SNAP,'field_spec_sha256':sha(SPEC/'field_spec.csv'),'summary':summary,'target_records':alltargets,'source_input_rows':candidates,'calculated_property_metadata':formula_metadata,'annual_empty_scaffolds':config_records,'literal_overrides_in_derived_fields':derived_literals,'validation_option_candidates':list(validation_lists.values()),'fixed_migration_id_ledger':id_ledger,'field_lineage':field_lineage,'id_rule':'Existing source entity IDs preserved exactly. New migration/revision/relation IDs are deterministic SHA-256 of full snapshot locator and persisted in ledger; reuse them on rerun. Do not allocate worldbuilding entities to fix references.','numerical_rule':'fields has typed convenience value; field_lineage.raw_value preserves exact lexical source. Large or nonexact numbers require downstream precision guard; no new measurements created.','native_spill_policy':'Only native userEntered literals become input candidates. Native formulas and effective-only/spill values remain derived evidence. Existing unverified export literals are flagged rather than asserted input.','no_adoption':'Candidate extraction is not source selection, deduplication of conflicting facts, or online migration.'}
analysis={'status':'REG full snapshot candidate extraction and static data diagnostics; online migration not performed','source_snapshot_id':SNAP,'summary':summary,'per_sheet':per_sheet,'target_counts':dict(Counter(x['file_code']+'.'+x['table'] for x in alltargets)),'region_graph':{'missing_parents':missing,'duplicate_parent_slots':duplicate_parent_slots,'cycles':cycles,'legacy_cache_rows':len(cache_by_parent),'direct_edges_missing_cache':[list(k) for k in parent_groups if k not in cache_by_parent],'cache_edges_without_direct_input':[list(k) for k in cache_by_parent if k not in parent_groups],'cache_rule':'existing 02 relation formula output crosswalk confirms original G/I edges; never a second source record'},'standard_revision_collisions':duplicates,'date_issues':dateissues,'display_literal_exceptions':derived_literals,'numeric_zero_literals':numeric_zero,'native_conflicts':native_conflicts,'target_assignment_conflicts':input_conflicts,'native_unverified_literal_cells':native_unverified,'row_admission_evidence':{'default_false_only_rows':sum(x['row_class']=='default_false_only_not_fact' for x in rows),'ordering_only_rows':sum(x['row_class']=='ordering_only_review_not_fact' for x in rows),'formula_only_rows':sum(x['row_class']=='formula_only_not_input_fact' for x in rows),'diagnostic_configuration_rows_99':sum(x['source_sheet_name']=='99_검증' and x['row_class']!='header_or_query_controls' for x in rows),'rule':'default FALSE, sorting-only, formula-only, diagnostics and empty annual scaffolds do not become factual observations; all raw evidence remains in PH1/PH0'},'small_flow_readiness':{'C00':'standards revisions, sources, languages and nation identity have seed candidates; preserve unresolved calendar/revision conflicts','R10':'133 regions + 142 relationships, keep gal.1 unresolved; 9 multi-parent relationships retained','blocking_facts_to_invent':[],'needs_runtime_checks':['native source-currentness check','native table upload and ID readback','formula/lookup/protection/permission','input/compute/validation/export/consumer range coverage']},'input_artifact_sha256':{str(p.relative_to(HERE.parent)):sha(p) for p in [PH1/'source_row_inventory.csv',PH1/'literal_cells.csv',PH1/'formula_nonempty_cache_observations.csv',SPEC/'field_spec.csv']+nativefiles},'runtime_status':'미실행'}
assert len(region_ids)==len(regions)
assert not input_conflicts and not native_conflicts
assert not unknown_target_fields
analysis['destination_integrity']={'unknown_target_fields':unknown_target_fields,'records_with_unresolved_primary_keys':missing_key_records,'nation_source_attribute_join_issue':'N10.국가목록원문속성 has record_id but lacks nation_id; source_entity_id is lineage only, pending owner contract'}
analysis['codebook_evidence']={'source_codebook_fact_rows':0,'observed_dropdown_configuration_groups':len(validation_lists),'status':'existing native ONE_OF_LIST settings preserved separately; no codebook facts created from choices','coverage':'observed native snapshot cells only; no claim of full data-validation range verification'}
assert all(not x['missing_primary_keys'] for x in targetmap.values() if x['table'] in ['지역목록','공통기준','국가식별목록','언어분류','출처레지스트리'])
for name,data in [('reg_seed_records.json',seed),('reg_migration_candidate_analysis.json',analysis)]:
 (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
