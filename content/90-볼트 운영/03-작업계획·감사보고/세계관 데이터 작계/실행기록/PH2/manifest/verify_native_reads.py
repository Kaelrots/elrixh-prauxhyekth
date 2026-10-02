from pathlib import Path
import json,collections,sys
from datetime import datetime,timezone
sys.stdout.reconfigure(encoding='utf-8')
P=Path(__file__).resolve().parent
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
calls=rd(P/'readonly_reads.json')['calls'];items={x['read_id']:x for x in rd(P/'expected_cells.json')['items']}
results=[];missing=[];errors=[];per=collections.defaultdict(lambda:collections.Counter())
for call in calls:
 path=P/call['response_file']
 if not path.exists():missing.append(call['call_id']);continue
 raw=rd(path);r=raw.get('response',raw)
 if r.get('isError'):errors.append({'call_id':call['call_id'],'error':'API_READ_ERROR'});continue
 d=r.get('structuredContent',r);cells={};sheetprops={}
 for s in d.get('sheets',[]):
  sid=s['properties']['sheetId'];sheetprops[sid]=s['properties']
  for data in s.get('data',[]):
   for i,row in enumerate(data.get('rowData',[])):
    for j,c in enumerate(row.get('values',[])):
     cells[(sid,data.get('startRow',0)+i+1,data.get('startColumn',0)+j+1)]=c
 for key in call['read_ids']:
  item=items[key];code=item['file_code'];kind=item['kind'];sid=item['sheet_id'];e=item['expected'];fail=[];display=[]
  if sheetprops.get(sid,{}).get('title')!=item['tab_title']:fail.append({'reason':'sheet identity/title missing or changed'})
  if kind=='headers':
   row=e['technical_header_row']
   for col,value in enumerate(e['technical_field_ids'],1):
    c=cells.get((sid,row,col),{})
    for axis in ['userEnteredValue','effectiveValue']:
     if c.get(axis)!={'stringValue':value}:fail.append({'row':row,'column':col,'axis':axis,'expected':value,'actual':c.get(axis)})
    per[code]['technical_header_cells']+=1
   for col,value in enumerate(e['values'][0],1):
    c=cells.get((sid,item['row_start'],col),{})
    if c.get('userEnteredValue')!={'stringValue':value}:display.append({'row':item['row_start'],'column':col,'expected':value,'actual':c.get('userEnteredValue')})
   per[code]['header_blocks']+=1
  elif kind in {'data_first','data_end_and_boundary'}:
   if code in {'C00','R10'}:
    results.append({'read_id':key,'kind':kind,'status':'MIGRATION_SEPARATE_COMPARISON','note':'C00/R10 source values are compared in input_execution; initial empty expectation superseded.'});continue
   for row in range(item['row_start'],item['row_end']+1):
    for col in range(1,item['column_count']+1):
     c=cells.get((sid,row,col),{})
     if c.get('userEnteredValue') or c.get('effectiveValue'):fail.append({'row':row,'column':col,'actual':c})
     per[code]['empty_boundary_sample_cells']+=1
  else:
   results.append({'read_id':key,'kind':kind,'status':'OBSERVED_NOT_FROZEN_TEXT_ASSERTION','note':'Guide/config status text may update as phase progresses.'});continue
  result={'read_id':key,'kind':kind,'status':'FAIL' if fail else 'PASS','technical_errors':fail,'display_label_differences':display};results.append(result)
  if fail:errors.append(result)
  per[code]['display_label_differences']+=len(display)
report={'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'Actual native headers and sampled empty/boundary rows only; no formula/link/function pass inferred. C00/R10 input values checked separately.','read_calls_present':len(calls)-len(missing),'read_calls_missing':missing,'per_file':dict(per),'technical_errors':errors,'results':results}
(P/'native_read_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'calls_present':report['read_calls_present'],'missing':len(missing),'technical_errors':len(errors),'per_file':report['per_file']},ensure_ascii=False))
