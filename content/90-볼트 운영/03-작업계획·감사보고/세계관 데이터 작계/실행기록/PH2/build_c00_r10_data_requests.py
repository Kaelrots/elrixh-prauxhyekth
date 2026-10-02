"""Prepare C00/R10 literal writes, readback expectations and a pending-work log.
No network calls. Existing candidates, bindings and source artifacts stay unchanged.
"""
from pathlib import Path
from collections import defaultdict, Counter
import json, csv, hashlib, re, math

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'input_requests'
OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(name,obj):
 p=OUT/name;p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return p
def colname(n):
 s=''
 while n:n,k=divmod(n-1,26);s=chr(65+k)+s
 return s
def quote(s):return "'"+s.replace("'","''")+"'"
def native(value):
 assert value is not None
 if isinstance(value,bool):return {'boolValue':value}
 if isinstance(value,(int,float)):
  assert math.isfinite(value)
  return {'numberValue':value}
 assert isinstance(value,str),type(value)
 return {'stringValue':value}
def locate(locator):
 f=locator.split('|')[0];gid=re.search(r'\|gid=(\d+)',locator);row=re.search(r'\|row=(\d+)',locator);cell=re.search(r'\|cell=([A-Z]+)(\d+)',locator)
 suffix=re.search(r'\|([A-Z]+)$',locator)
 originalcolumn=cell[1] if cell else (suffix[1] if suffix else None)
 return {'source_file_id':f,'source_sheet_id':int(gid[1]) if gid else None,'original_row':int(row[1]) if row else None,'original_column':originalcolumn,'original_cell':cell[1]+cell[2] if cell else (originalcolumn+row[1] if originalcolumn and row else None)}
def independent(locator,key,field):
 s=locate(locator)
 return f"{s['source_file_id']}|gid={s['source_sheet_id']}|original_row={s['original_row']}|original_column={s['original_column'] or 'ROW'}|logical_table={key}|id_field={field}"

inp=ROOT/'input_batch_candidates.json'
batch=read(inp)
bindings={c:read(ROOT/'structure_requests'/f'{c}.binding.json') for c in ['C00','R10']}
input_hashes={str(inp):sha(inp),**{str(ROOT/'structure_requests'/f'{c}.binding.json'):sha(ROOT/'structure_requests'/f'{c}.binding.json') for c in bindings}}
originals={'1EACdRIiAPGk4LAbttpXZiJd_cuqIh-cVi4jQsbfmqDw','1mTRKFfCFtiTmuAR6QwrslcBI6Q-wutYzVP_weDAW9uI'}
bound={}
for c,binding in bindings.items():
 assert binding['spreadsheet_id'] not in originals
 for tab in binding['tabs']:
  for block in tab['blocks']:
   if block.get('kind')=='logical_table':
    k=c+'.'+block['logical_table_id'];assert k not in bound
    bound[k]=(tab,block)

manifests={};requests_by_code=defaultdict(list);row_resume=[];written_ids=[];table_write_counts={};all_expected=[]
for code,binding in bindings.items():
 manifests[code]={'file_code':code,'spreadsheet_id':binding['spreadsheet_id'],'status':'PREPARED_NOT_EXECUTED','binding_sha256':input_hashes[str(ROOT/'structure_requests'/f'{code}.binding.json')],'prewrite_live_header_read_required':True,'header_readback':[],'table_preflight':[],'readback_ranges':[],'expected_cells':[],'unwritten_masks':[],'table_counts':{}}

order=['C00.코드북','C00.출처레지스트리','C00.공통기준','C00.국가식별목록','C00.기준개정이력','C00.언어분류','C00.개체별칭','R10.지역목록','R10.지역관계']
for ti,table in sorted(enumerate(batch['tables']),key=lambda x:order.index(x[1]['logical_table_key']) if x[1]['logical_table_key'] in order else 999):
 code=table['owner_file_code']
 if code not in bindings:continue
 key=table['logical_table_key'];tab,b=bound[key];m=manifests[code]
 assert tab['role']=='IN' and b['role']=='IN'
 assert table['primary_key_fields']==b['primary_key_fields']
 columns={x['field_id']:x for x in b['field_columns']}
 assert set(table['column_order'])==set(columns)
 n=len(table['rows']);start=b['data_start_row'];end=start+n-1
 assert n<=b['data_capacity'] and end<=b['data_end_row'] and end<tab['row_count']
 sid=tab['planned_sheet_id'];title=tab['actual_tab_title']
 assert sid==b['grid_range']['sheetId']
 header_order=[x['field_id'] for x in sorted(b['field_columns'],key=lambda x:x['column_index'])]
 hrow=b['technical_header_row'];hfirst=min(x['column_index'] for x in b['field_columns']);hlast=max(x['column_index'] for x in b['field_columns'])
 hrange=f"{quote(title)}!{colname(hfirst)}{hrow}:{colname(hlast)}{hrow}"
 drange=f"{quote(title)}!{colname(hfirst)}{start}:{colname(hlast)}{end}"
 m['header_readback'].append({'logical_table_key':key,'sheet_id':sid,'actual_tab_title':title,'range':hrange,'expected_userEnteredValue':[{'stringValue':x} for x in header_order],'expected_effectiveValue':[{'stringValue':x} for x in header_order],'fail_if':'Any changed title/sheetId/technical-header field order, missing column or nonliteral header'})
 m['table_preflight'].append({'logical_table_key':key,'range':drange,'sheet_id':sid,'capacity':b['data_capacity'],'candidate_rows':n,'input_start_row':start,'input_last_row':end,'required_native_table_coverage':{'startRowIndex':hrow-1,'endRowIndex':end,'startColumnIndex':hfirst-1,'endColumnIndex':hlast},'expected_native_table_name':b['native_table_name'],'rule':'Observe actual table range and sheet identity. For written cells allow only empty or exact same literal+note; any different existing value/formula/chip or incompatible validation stops that table. Snapshot untouched cells before applying.'})
 m['readback_ranges'].append(drange)
 cells=[]
 for ri,(row,evidence) in enumerate(zip(table['rows'],table['source_evidence'])):
  actual_row=start+ri;vmap=dict(zip(table['column_order'],row));mask=set(evidence['write_fields'])
  assert len(mask)==len(evidence['write_fields'])
  assert all(vmap[f] is not None for f in mask)
  assert {f for f,v in vmap.items() if v is not None}==mask
  fullpointer=str(inp)+f'#/tables/{ti}/source_evidence/{ri}'
  row_resume.append({'logical_table_key':key,'primary_key':evidence['primary_key'],'source_identity':locate(evidence['legacy_locator']),'snapshot_independent_key':independent(evidence['legacy_locator'],key,'ROW_PRIMARY_KEY'),'source_snapshot_id':evidence['source_snapshot_id'],'legacy_locator':evidence['legacy_locator'],'original_source_evidence':fullpointer,'planned_target':{'spreadsheet_id':bindings[code]['spreadsheet_id'],'sheet_id':sid,'row':actual_row},'resume_rule':'Read current target PK and original-source identity before write; matching PK is verify/update, not append. Different snapshot alone never allocates a new record.'})
  for f in table['column_order']:
   if f not in mask:continue
   col=columns[f]['column_index'];uv=native(vmap[f]);line=evidence.get('field_lineage',{}).get(f,{})
   locator=line.get('source_locator',line.get('legacy_locator',evidence['legacy_locator']))
   note='원문/기술계보 보존 · 정본 채택 아님\n원본 위치: '+locator+'\n전체 계보: '+fullpointer+'\n필드: '+key+'.'+f
   item={'row':actual_row,'column':col,'cell':{'userEnteredValue':uv,'note':note},'field':f}
   cells.append(item)
   expected={'logical_table_key':key,'primary_key':evidence['primary_key'],'sheet_id':sid,'tab_title':title,'cell':colname(col)+str(actual_row),'row_index':actual_row-1,'column_index':col-1,'field_id':f,'expected_userEnteredValue':uv,'expected_effectiveValue':uv,'expected_note_sha256':hashlib.sha256(note.encode()).hexdigest(),'source_evidence':fullpointer,'source_locator':locator}
   m['expected_cells'].append(expected);all_expected.append((code,sid,actual_row,col,uv))
  m['unwritten_masks'].append({'logical_table_key':key,'sheet_id':sid,'row':actual_row,'fields_do_not_write':[f for f in table['column_order'] if f not in mask],'rule':'Null means no request. Preserve values/formulas/notes/validation/formatting in these cells; compare against prewrite snapshot.'})
  if evidence.get('migration_record_id'):
   written_ids.append({'kind':'migration_record_id','id':evidence['migration_record_id'],'data_cell_written':False,'logical_table_key':key,'source_identity':locate(evidence['legacy_locator']),'snapshot_independent_key':independent(evidence['legacy_locator'],key,'migration_record_id'),'source_snapshot_id':evidence['source_snapshot_id'],'legacy_locator':evidence['legacy_locator'],'resume_rule':'Reuse this already-fixed ID for the same source identity after a source snapshot change; content/revision changes require an explicit update decision.'})
 # Combine contiguous populated cells in each column; no null cell enters a range.
 bycol=defaultdict(list)
 for x in cells:bycol[x['column']].append(x)
 for col,items in sorted(bycol.items()):
  items.sort(key=lambda x:x['row']);run=[]
  def flush(run):
   if not run:return
   req={'updateCells':{'range':{'sheetId':sid,'startRowIndex':run[0]['row']-1,'endRowIndex':run[-1]['row'],'startColumnIndex':col-1,'endColumnIndex':col},'rows':[{'values':[x['cell']]} for x in run],'fields':'userEnteredValue,note'}}
   requests_by_code[code].append({'logical_table_key':key,'request':req,'written_cells':len(run),'field_id':run[0]['field']})
  for item in items:
   if run and (item['row']!=run[-1]['row']+1 or len(run)>=40):flush(run);run=[]
   run.append(item)
  flush(run)
 m['table_counts'][key]={'rows':n,'cells':len(cells),'null_cells_excluded':n*len(table['column_order'])-len(cells)}
 table_write_counts[key]=m['table_counts'][key]

for x in batch['fixed_technical_id_ledger_used']:
 if x['logical_table_key'].split('.')[0] not in bindings:continue
 y=dict(x);y['source_identity']=locate(x['legacy_locator']);y['snapshot_independent_key']=independent(x['legacy_locator'],x['logical_table_key'],x['field']);y['data_cell_written']=True
 y['resume_rule']='Lookup this snapshot-independent source/field key before any new allocation. Preserve the existing ID. A moved source row must match its preserved natural PK/crosswalk before deciding it is new.'
 written_ids.append(y)

# Independent rectangular-request audit and exact cell-set equality.
reconstructed=[]
for code,wrappers in requests_by_code.items():
 for w in wrappers:
  r=w['request'];assert list(r)==['updateCells'];u=r['updateCells'];g=u['range']
  assert u['fields']=='userEnteredValue,note' and len(u['rows'])==g['endRowIndex']-g['startRowIndex']
  assert g['endColumnIndex']-g['startColumnIndex']==1
  for i,row in enumerate(u['rows']):
   assert len(row['values'])==1
   cv=row['values'][0];assert len(cv['userEnteredValue'])==1 and 'formulaValue' not in cv['userEnteredValue']
   reconstructed.append((code,g['sheetId'],g['startRowIndex']+i+1,g['startColumnIndex']+1,cv['userEnteredValue']))
normalize=lambda xs:sorted((c,s,r,k,json.dumps(v,sort_keys=True,ensure_ascii=False)) for c,s,r,k,v in xs)
assert normalize(reconstructed)==normalize(all_expected)
assert len({(c,s,r,k) for c,s,r,k,_ in reconstructed})==len(reconstructed)
assert len({x['snapshot_independent_key'] for x in written_ids})==len(written_ids)

# A request file is a candidate payload, not evidence that any online write ran.
request_index=[]
for code,wrappers in requests_by_code.items():
 groups=[];current=[];size=0;tablekey=None
 for w in wrappers:
  enc=len(json.dumps(w['request'],ensure_ascii=False,separators=(',',':')).encode())
  if current and (size+enc>250_000 or len(current)>=100 or w['logical_table_key']!=tablekey):groups.append(current);current=[];size=0
  current.append(w);size+=enc;tablekey=w['logical_table_key']
 if current:groups.append(current)
 for n,group in enumerate(groups,1):
  payload={'spreadsheet_id':bindings[code]['spreadsheet_id'],'body':{'requests':[x['request'] for x in group],'includeSpreadsheetInResponse':False}}
  name=f'{code}.data.{n:03d}.json';p=save(name,payload)
  request_index.append({'file_code':code,'path':str(p),'sha256':sha(p),'logical_table_keys':sorted({x['logical_table_key'] for x in group}),'request_count':len(group),'cell_count':sum(x['written_cells'] for x in group),'payload_bytes':p.stat().st_size,'status':'PREPARED_NOT_SENT','preconditions':['Live sheetId/title/technical header order exact match','Live written cells empty or same exact literal/note; no foreign formula/chip','Native table covers every candidate row and column','Resume PK/source ledger checked; do not append an existing record']})
 save(f'{code}.readback_manifest.json',manifests[code])

ledger={'status':'PREPARED_EXISTING_IDS_REUSED_NOT_NEWLY_ALLOCATED','source_snapshot_hashes':batch['input_snapshot_hashes'],'row_resume_index':row_resume,'fixed_id_records':written_ids,'counts':{'candidate_rows':len(row_resume),'existing_fixed_ids':len(written_ids),'data_cell_technical_ids':sum(x['data_cell_written'] for x in written_ids),'migration_metadata_ids':sum(not x['data_cell_written'] for x in written_ids)},'policy':'A snapshot hash is evidence, not a new source identity. Existing PK and snapshot-independent key must be checked before rerun/new snapshot import. Original row coordinates are lineage; if rows move, natural PK and preserved field/parent edge crosswalk must resolve identity before allocation.'}
save('technical_id_resume_ledger.json',ledger)

# Visible work-log rows preserve pending versions separately from canonical data.
pending_rows=[]
for i,p in enumerate(batch['pending']):
 if p['logical_table_key'].split('.')[0] not in bindings:continue
 cand=p['preserved_candidate'];values=cand.get('values',cand.get('fields',{}));locator=p.get('legacy_locator',cand.get('legacy_locator',''))
 codes=[x['code'] for x in p['reasons']]
 cls='기준 판본 충돌' if 'MULTIPLE_STANDARD_REVISIONS_PENDING' in codes else ('역법 원문 대응 대기' if p['logical_table_key']=='C00.기준개정이력' else '필드/키/단일원본 대응 대기')
 sourcekey=values.get('standard_id') or values.get('original_property_id') or cand.get('source_field_id') or values.get('source_key','')
 rawpayload={'candidate_fields':values,'source_literals':{f:lin.get('raw_value') for f,lin in cand.get('field_lineage',{}).items()},'source_fragment_raw':cand.get('source_raw_value')}
 pending_rows.append({'pending_id':'pend.ph2.'+hashlib.sha256((p['logical_table_key']+'|'+locator+'|'+str(p['source_evidence_pointer'])).encode()).hexdigest()[:20],'file_code':p['logical_table_key'].split('.')[0],'logical_table_key':p['logical_table_key'],'classification':cls,'source_key':str(sourcekey),'source_setting_status':values.get('setting_status',''),'raw_values_json':json.dumps(rawpayload,ensure_ascii=False),'reason':'; '.join(x['code']+': '+str(x['detail']) for x in p['reasons']),'workflow_status':'결정대기 · 미채택','input_write_excluded':True,'legacy_locator':locator,'evidence_file':str(inp),'evidence_pointer':f'/pending/{i}','required_action':'원문·판본 보존 후 대응 결정. 임의 정본 선택/빈 키 채우기 금지.'})
for i,p in enumerate(batch['pending_fields']):
 pending_rows.append({'pending_id':'pend.ph2.'+digest(p)[:20],'file_code':'C00','logical_table_key':p['logical_table_key'],'classification':'국가명 단일소유 명세 수정','source_key':p['field'],'source_setting_status':'','raw_values_json':json.dumps(p['raw_value'],ensure_ascii=False),'reason':p['decision'],'workflow_status':'명세 수정 대기 · 원문 보존','input_write_excluded':True,'legacy_locator':p['source_lineage'].get('source_locator',''),'evidence_file':str(inp),'evidence_pointer':f'/pending_fields/{i}','required_action':p['required_spec_change']})
for ti,table in enumerate(batch['tables']):
 if table['logical_table_key']!='R10.지역관계':continue
 for i,e in enumerate(table['source_evidence']):
  if any(isinstance(w,str) and 'gal.1' in w for w in e['warnings']):
   pending_rows.append({'pending_id':'pend.ph2.'+digest(e['primary_key'])[:20],'file_code':'R10','logical_table_key':table['logical_table_key'],'classification':'원문 상위지역 미참조','source_key':'gal.1','source_setting_status':'','raw_values_json':json.dumps(e['primary_key'],ensure_ascii=False),'reason':'sec.1의 원문 상위 ID gal.1에 대응하는 지역 실자료 없음. 원문 표시 하르아지엘 은하 보존.','workflow_status':'원문 입력 보존 · 참조오류','input_write_excluded':False,'legacy_locator':e['legacy_locator'],'evidence_file':str(inp),'evidence_pointer':f'/tables/{ti}/source_evidence/{i}','required_action':'기존 근거를 확인하기 전 은하 엔티티/관계 기간 생성 또는 정상조회 채택 금지.'})
optiondiff=next(x for x in batch['ownership_checks'] if x['check']=='C00 codebook composite-key uniqueness')['validation_exact_code_differences']
if optiondiff:
 pending_rows.append({'pending_id':'pend.ph2.'+digest(optiondiff)[:20],'file_code':'C00','logical_table_key':'C00.코드북','classification':'REG 드롭다운 선택지 대응','source_key':'setting_status:임시/미명명','source_setting_status':'','raw_values_json':json.dumps(optiondiff,ensure_ascii=False),'reason':'REG 9필드의 임시/미명명 선택지는 NAT 코드북 setting_status에 없음. 이번 수용자료에는 두 값 없음.','workflow_status':'선택지 대응 대기 · 임의 추가 안 함','input_write_excluded':True,'legacy_locator':'REG 원본 드롭다운 메타데이터','evidence_file':str(inp),'evidence_pointer':'/ownership_checks/5/validation_exact_code_differences','required_action':'원문 선택지와 공통코드 대응 결정. 임시/미명명은 개별 설정 확정 의미로 해석하지 않음.'})
assert sum(x['classification']=='기준 판본 충돌' for x in pending_rows)==8
assert sum(x['classification']=='역법 원문 대응 대기' for x in pending_rows)==5
save('pending.json',{'status':'WORK_LOG_ONLY_NOT_CANONICAL_FACTS','counts':dict(Counter(x['classification'] for x in pending_rows)),'rows':pending_rows,'phase3_deferred_tables':[{'logical_table_key':t['logical_table_key'],'rows':len(t['rows']),'reason':'Only C00/R10 data writes authorized in this PH2 preparation'} for t in batch['tables'] if t['owner_file_code'] not in bindings]})
with (OUT/'pending.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(pending_rows[0]));writer.writeheader();writer.writerows(pending_rows)

# Optional separate tab. Root must first confirm title absence / ID availability.
pending_title='09_운영결정대기';usedids=set(bindings['C00']['existing_sheet_ids_preserved'])|{t['planned_sheet_id'] for t in bindings['C00']['tabs']}
pending_sid=1_000_000_000+int(hashlib.sha256(b'PH2:C00:PENDING:09').hexdigest()[:8],16)%999_999_999
while pending_sid in usedids:pending_sid+=1
headers=['대기 ID','분야','논리표','구분','원문 항목','원문 설정 상태','원문 값(JSON)','대기 사유','작업 상태','운영 입력 제외','원본 위치','계보 파일','계보 위치','다음 조치']
keys=list(pending_rows[0])
assert len(headers)==len(keys)
pending_values=[[native(x[k]) for k in keys] for x in pending_rows]
pending_req=[{'addSheet':{'properties':{'sheetId':pending_sid,'title':pending_title,'gridProperties':{'rowCount':max(100,len(pending_rows)+40),'columnCount':len(headers),'frozenRowCount':3}}}},
 {'updateCells':{'range':{'sheetId':pending_sid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':0,'endColumnIndex':1},'rows':[{'values':[{'userEnteredValue':{'stringValue':'PH2 운영 결정대기 — 원문·판본 보존 / 정본 채택 아님'}}]}],'fields':'userEnteredValue'}},
 {'updateCells':{'range':{'sheetId':pending_sid,'startRowIndex':1,'endRowIndex':2,'startColumnIndex':0,'endColumnIndex':1},'rows':[{'values':[{'userEnteredValue':{'stringValue':'기준 판본 충돌 8행 + 역법 대응 5행을 포함. 결정 전 원문 덮어쓰기·값 추정 금지. 전체 계보: '+str(OUT/'pending.json')}}]}],'fields':'userEnteredValue'}},
 {'updateCells':{'range':{'sheetId':pending_sid,'startRowIndex':2,'endRowIndex':3+len(pending_rows),'startColumnIndex':0,'endColumnIndex':len(headers)},'rows':[{'values':[{'userEnteredValue':native(h)} for h in headers]}]+[{'values':[{'userEnteredValue':v} for v in row]} for row in pending_values],'fields':'userEnteredValue'}},
 {'addTable':{'table':{'name':'V2_WORK_PENDING_PH2_C00','range':{'sheetId':pending_sid,'startRowIndex':2,'endRowIndex':3+len(pending_rows),'startColumnIndex':0,'endColumnIndex':len(headers)}}}}]
save('C00.pending_sheet.optional.json',{'status':'OPTIONAL_PREPARED_NOT_SENT','spreadsheet_id':bindings['C00']['spreadsheet_id'],'planned_sheet_id':pending_sid,'planned_title':pending_title,'precondition':'Live metadata must show this title absent and planned sheetId unused. If already present, reuse after header/data comparison instead of addSheet. This is a work log, not another input source.','body':{'requests':pending_req,'includeSpreadsheetInResponse':False},'expected_range':f"{quote(pending_title)}!A3:N{len(pending_rows)+3}",'expected_headers':headers,'expected_row_count':len(pending_rows),'expected_values_sha256':digest([[x[k] for k in keys] for x in pending_rows])})

assert all(sha(Path(p))==h for p,h in input_hashes.items()),'Source candidate or binding changed while preparing; regenerate'
summary={'status':'READY_FOR_ROOT_LIVE_PREFLIGHT_ONLY','candidate_files':['C00','R10'],'candidate_tables':len(table_write_counts),'candidate_rows':len(row_resume),'candidate_cells':len(all_expected),'request_files':len(request_index),'request_count':sum(len(v) for v in requests_by_code.values()),'fixed_ids_reused':len(written_ids),'new_data_ids_allocated':0,'pending_worklog_rows':len(pending_rows),'pending_standard_collision_rows':8,'pending_calendar_rows':5,'online_writes':0,'runtime_status':'미실행'}
save('manifest.json',{'summary':summary,'source_hashes':input_hashes,'source_candidates_unchanged':True,'request_index':request_index,'table_write_counts':table_write_counts,'live_preflight_fields':['userEnteredValue','effectiveValue','note','dataValidation','chipRuns','userEnteredFormat'],'header_manifest_files':[str(OUT/f'{c}.readback_manifest.json') for c in bindings],'comparison_manifest_rule':'For every expected cell compare userEnteredValue and effectiveValue including union type, plus SHA-256(note). Count exact PKs/rows. Compare all unwritten-mask cells with prewrite snapshot. Recalculation/function tests remain separate and unexecuted.','resume_ledger':str(OUT/'technical_id_resume_ledger.json'),'pending_json':str(OUT/'pending.json'),'pending_csv':str(OUT/'pending.csv'),'optional_pending_sheet_request':str(OUT/'C00.pending_sheet.optional.json'),'scope':'PH2 C00/R10 only. N10/N20/R70 candidate rows remain deferred, no original V1 ID is an output target.','chunk_resume_rule':'Record success plus exact readback for each request file. Before rerun compare live cell/PK state; do not blindly replay or append.'})
print(json.dumps(summary,ensure_ascii=False))
