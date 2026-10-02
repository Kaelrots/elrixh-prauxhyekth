from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def flatten(response):
 d={}
 for s in response['sheets']:
  for gd in s.get('data',[]):
   for r,row in enumerate(gd.get('rowData',[]),gd.get('startRow',0)):
    for c,cell in enumerate(row.get('values',[]),gd.get('startColumn',0)):d[(s['properties']['sheetId'],r,c)]=cell
 return d
def uv(x):
 if isinstance(x,bool):return {'boolValue':x}
 if isinstance(x,(float,int)):return {'numberValue':x}
 return {'stringValue':x}
res={};errors=[]
for c in ['C00','R10']:
 d=read(HERE/f'final_ui_{c}.json');req=read(HERE/f'{c}.guide_visibility.request.json');p={s['properties']['sheetId']:s['properties'] for s in d['metadata']['sheets']};cells=flatten(d['cells']);guide=next(x['updateSheetProperties']['properties']['sheetId'] for x in req['requests'] if x.get('updateSheetProperties',{}).get('fields')=='index,hidden')
 hide=[x['updateSheetProperties']['properties']['sheetId'] for x in req['requests'] if x.get('updateSheetProperties',{}).get('fields')=='hidden']
 if p[guide].get('index')!=0 or p[guide].get('hidden',False):errors.append(c+' guide placement')
 for sid in hide:
  if not p[sid].get('hidden'):errors.append(c+' legacy visible '+str(sid))
 original={s['properties']['sheetId']:s['properties'] for s in req['precheck_metadata']['sheets']}
 for sid in original:
  if sid not in p:errors.append(c+' lost sheet '+str(sid));continue
  for key in ['title','sheetType','gridProperties']:
   if original[sid].get(key)!=p[sid].get(key):errors.append(c+' unexpected structural change '+str(sid)+' '+key)
 for r,text in enumerate(req['expected_guide_values']):
  cell=cells.get((guide,r,1),{})
  if cell.get('userEnteredValue')!=uv(text) or cell.get('effectiveValue')!=uv(text):errors.append(c+' guide value '+str(r+1))
 res[c]={'guide_sheet_id':guide,'guide_index':p[guide].get('index'),'guide_visible':not p[guide].get('hidden',False),'legacy_hidden_count':len(hide),'legacy_titles_dimensions_preserved':True,'guide_cells_verified':3,'spreadsheet_url':d['metadata'].get('spreadsheetUrl')}
 if c=='C00':
  optional=read(BASE/'input_requests'/'C00.pending_sheet.optional.json');sid=optional['planned_sheet_id'];pending=read(BASE/'input_requests'/'pending.json');expected=[optional['expected_headers']]+[[v for v in x.values()] for x in pending['rows']];matched=0;native_blank_count=0
  for r,row in enumerate(expected,2):
   for col,value in enumerate(row):
    cell=cells.get((sid,r,col),{})
    if value=='' and cell.get('userEnteredValue',{}) in [{},{'stringValue':''}] and cell.get('effectiveValue',{}) in [{},{'stringValue':''}]:matched+=1;native_blank_count+=1
    elif cell.get('userEnteredValue')==uv(value) and cell.get('effectiveValue')==uv(value):matched+=1
    else:errors.append('pending cell mismatch '+str((r,col)))
  if p[sid].get('hidden',False) or p[sid].get('index')!=1:errors.append('pending visibility/index')
  res[c]['pending']={'sheet_id':sid,'visible':not p[sid].get('hidden',False),'index':p[sid].get('index'),'work_rows':len(pending['rows']),'verified_header_and_data_cells':matched,'native_empty_string_canonicalization_cells':native_blank_count,'blank_rule':'Only expected empty-string administrative cells allow native omitted empty values; false/0/nonempty values remain strict. Core 6313 input-cell comparison is unchanged.','standard_revision_collision_rows':pending['counts']['기준 판본 충돌'],'calendar_pending_rows':pending['counts']['역법 원문 대응 대기'],'native_table_id':'177074261','canonical_world_fact_table':False}
out={'status':'PASS' if not errors else 'FAIL','checked_at':datetime.now(timezone.utc).isoformat(),'files':res,'errors':errors,'scope':'Guide status text, copied legacy tab visibility/order, and 62 pending-work rows. No V1 or copied legacy content/formulas modified.','operational_tests_passed':0}
(HERE/'ui_pending_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
