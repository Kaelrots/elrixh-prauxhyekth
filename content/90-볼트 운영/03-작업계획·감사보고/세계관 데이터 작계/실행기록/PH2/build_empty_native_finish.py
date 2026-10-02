from pathlib import Path
import json,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
P=Path(__file__).resolve().parent
def rd(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
layout=rd(P/'physical_layout.json')
for code in ['N60','N70']:
 f=next(f for f in layout['files'] if f['file_code']==code)
 meta=rd(P/f'initial_native_{code}.json')
 created=rd(P/f'created_{code}.json')['result']
 sheets={s['properties']['title']:s['properties'] for s in meta['sheets']}
 req=[{'updateSpreadsheetProperties':{'properties':{'locale':'ko_KR','timeZone':'Asia/Seoul'},'fields':'locale,timeZone'}}]
 reads=[];expected=[];tables=[]
 for tab in f['tabs']:
  s=sheets[tab['title']];sid=s['sheetId']
  req.append({'updateSheetProperties':{'properties':{'sheetId':sid,'gridProperties':{'frozenRowCount':tab.get('frozen_row_count',0)}},'fields':'gridProperties.frozenRowCount'}})
  for block in tab.get('blocks',[]):
   cols=block['columns'];w=len(cols);rg={'sheetId':sid,'startRowIndex':block['technical_header_row']-1,'endRowIndex':block['data_end_row'],'startColumnIndex':0,'endColumnIndex':w}
   req.append({'addNamedRange':{'namedRange':{'name':block['named_range'],'range':rg}}})
   reads.append(block['header_range']);expected.append({'sheetId':sid,'row':block['technical_header_row'],'values':[c['field_id'] for c in cols]})
   if tab['role']=='IN':
    tid=str(1000000000+int(hashlib.sha256((code+block['named_range']).encode()).hexdigest()[:8],16)%900000000)
    name='V2T_'+code+'_'+hashlib.sha256(block['named_range'].encode()).hexdigest()[:16]
    req.append({'addTable':{'table':{'tableId':tid,'name':name,'range':rg}}})
    req.append({'updateTable':{'table':{'tableId':tid,'rowsProperties':{'headerColorStyle':{'rgbColor':{'red':.94,'green':.94,'blue':.94}},'firstBandColorStyle':{'rgbColor':{'red':1,'green':1,'blue':1}},'secondBandColorStyle':{'rgbColor':{'red':1,'green':1,'blue':1}}}},'fields':'rowsProperties'}})
    tables.append({'id':tid,'name':name,'range':rg})
    protect={'sheetId':sid,'startRowIndex':0,'endRowIndex':block['technical_header_row'],'startColumnIndex':0,'endColumnIndex':w}
   else:protect=rg
   req.append({'addProtectedRange':{'protectedRange':{'range':protect,'warningOnly':True,'description':'V2 헤더/출력 범위 · 구조 준비 · 계산/검증 미실행'}}})
   req.append({'repeatCell':{'range':{'sheetId':sid,'startRowIndex':block['technical_header_row']-1,'endRowIndex':block['technical_header_row'],'startColumnIndex':0,'endColumnIndex':w},'cell':{'userEnteredFormat':{'textFormat':{'foregroundColorStyle':{'rgbColor':{'red':0,'green':0,'blue':0}},'bold':True}}},'fields':'userEnteredFormat.textFormat'}})
 guide=sheets['00_안내']['sheetId']
 req.append({'updateCells':{'start':{'sheetId':guide,'rowIndex':20,'columnIndex':0},'rows':[{'values':[{'userEnteredValue':{'stringValue':'실제 V2 파일 ID'}},{'userEnteredValue':{'stringValue':created['id']}}]},{'values':[{'userEnteredValue':{'stringValue':'네이티브 구조'}},{'userEnteredValue':{'stringValue':'입력 표 3개·이름 범위·헤더/출력 경고 보호 준비. 자료행 0. 참조·수식·시험 미완료.'}}]}],'fields':'userEnteredValue'}})
 save(P/f'finish_empty_{code}.json',{'file_code':code,'spreadsheet_id':created['id'],'requests':req,'header_ranges':reads,'expected_headers':expected,'tables':tables,'notes':'New-domain native finish only. No world data/formulas. Unspecified column types preserve blank inputs.'})
 print(code,len(req),len(reads))
