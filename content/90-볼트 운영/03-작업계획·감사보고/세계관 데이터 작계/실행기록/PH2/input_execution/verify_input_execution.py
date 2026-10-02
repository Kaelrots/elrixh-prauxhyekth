from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def flatten(response):
 out={};titles={}
 for sh in response.get('sheets',[]):
  sid=sh['properties']['sheetId'];titles[sid]=sh['properties']['title']
  for gd in sh.get('data',[]):
   for r,row in enumerate(gd.get('rowData',[]),gd.get('startRow',0)):
    for c,cell in enumerate(row.get('values',[]),gd.get('startColumn',0)):out[(sid,r,c)]=cell
 return out,titles
def compact(cell):return {k:cell[k] for k in ['userEnteredValue','effectiveValue','note'] if k in cell}
reports={};grand={'expected_cells':0,'matched_user_values':0,'matched_effective_values':0,'matched_notes':0,'untouched_cells_compared':0,'headers_compared':0}
for code in ['C00','R10']:
 manifest=read(BASE/'input_requests'/f'{code}.readback_manifest.json')
 pre=read(BASE/'input_requests'/f'prewrite_{code}.json')
 post=read(HERE/f'postwrite_{code}.json')
 before,_=flatten(pre['response']);after,titles=flatten(post['response'])
 errors=[];stats={k:0 for k in grand};written=set()
 assert post['response']['spreadsheetId']==manifest['spreadsheet_id']==pre['response']['spreadsheetId']
 for x in manifest['expected_cells']:
  key=(x['sheet_id'],x['row_index'],x['column_index']);written.add(key);cell=after.get(key,{})
  stats['expected_cells']+=1
  for field,expectedname,stat in [('userEnteredValue','expected_userEnteredValue','matched_user_values'),('effectiveValue','expected_effectiveValue','matched_effective_values')]:
   if cell.get(field)==x[expectedname]:stats[stat]+=1
   else:errors.append({'cell':x['cell'],'table':x['logical_table_key'],'kind':field,'expected':x[expectedname],'actual':cell.get(field)})
  if hashlib.sha256(cell.get('note','').encode()).hexdigest()==x['expected_note_sha256']:stats['matched_notes']+=1
  else:errors.append({'cell':x['cell'],'table':x['logical_table_key'],'kind':'note_sha256'})
  if titles[x['sheet_id']]!=x['tab_title']:errors.append({'kind':'sheet_title_changed','sheetId':x['sheet_id']})
 for header in manifest['header_readback']:
  sid=header['sheet_id'];row=int(header['range'].split('!')[-1].split(':')[0][1:])-1
  for col,expected in enumerate(header['expected_userEnteredValue']):
   key=(sid,row,col);stats['headers_compared']+=1
   if after.get(key,{}).get('userEnteredValue')!=expected or after.get(key,{}).get('effectiveValue')!=expected:errors.append({'kind':'header_value_changed','cell_key':key})
   if compact(after.get(key,{}))!=compact(before.get(key,{})):errors.append({'kind':'header_or_note_changed','cell_key':key})
  if titles.get(sid)!=header['actual_tab_title']:errors.append({'kind':'header_title_changed','sheetId':sid})
 # Field positions come from the header manifest, not candidate array assumptions.
 columns={h['logical_table_key']:{x['stringValue']:i for i,x in enumerate(h['expected_userEnteredValue'])} for h in manifest['header_readback']}
 for row in manifest['unwritten_masks']:
  for field in row['fields_do_not_write']:
   key=(row['sheet_id'],row['row']-1,columns[row['logical_table_key']][field]);assert key not in written
   stats['untouched_cells_compared']+=1
   if compact(before.get(key,{}))!=compact(after.get(key,{})):errors.append({'kind':'unwritten_cell_changed','cell_key':key,'field':field,'before':compact(before.get(key,{})),'after':compact(after.get(key,{}))})
 for k,v in stats.items():grand[k]+=v
 reports[code]={'status':'NATIVE_CELL_READBACK_PASS' if not errors else 'FAIL','counts':stats,'errors':errors,'table_counts':manifest['table_counts'],'source_prewrite_sha256':digest(BASE/'input_requests'/f'prewrite_{code}.json'),'postwrite_sha256':digest(HERE/f'postwrite_{code}.json'),'limitations':['This verifies literal values/effective values/notes and untouched null fields, not calculation or 84 operational tests.','Formatting/validation is not changed by userEnteredValue,note requests; visual inspection is separately recorded.']}
out={'status':'NATIVE_INPUT_CELL_COMPARISON_PASS' if all(not x['errors'] for x in reports.values()) else 'FAIL','checked_at':datetime.now(timezone.utc).isoformat(),'counts':grand,'files':reports,'online_operational_tests_passed':0,'test_checklist_status':'84개 시험표 자동 변경 없음','runtime_scope':'C00/R10 literal migration cell verification only'}
(HERE/'input_cell_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':out['status'],'counts':grand,'errors':{c:len(r['errors']) for c,r in reports.items()}},ensure_ascii=False))
