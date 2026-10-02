import json,pathlib,datetime
B=pathlib.Path(__file__).parent
P=B/'small_flow_requests'
M=json.loads((P/'small_flow_request_manifest.json').read_text(encoding='utf-8'))
ids=M['allowlisted_test_ids'];sheets={c:x['sheet_ids'] for c,x in M['files'].items()}
def cell(c,tab,row,col,value):
    return {'updateCells':{'range':{'sheetId':sheets[c][tab],'startRowIndex':row-1,'endRowIndex':row,'startColumnIndex':col-1,'endColumnIndex':col},'rows':[{'values':[{'userEnteredValue':{'stringValue':value}}]}],'fields':'userEnteredValue'}}
r20=json.loads((P/'R20_01_headers_config_fixtures.json').read_text(encoding='utf-8'))
original=next(x for x in r20['requests'] if x.get('updateCells',{}).get('range',{}).get('sheetId')==sheets['R20']['IN_인구관측'] and x['updateCells']['range']['startRowIndex']==3)
assert original['updateCells']['rows'][0]['values'][3]['userEnteredValue']['numberValue']==100
requests={
'R20':[original,{'updateCells':{'range':{'sheetId':sheets['R20']['IN_인구관측'],'startRowIndex':13,'endRowIndex':14,'startColumnIndex':0,'endColumnIndex':48},'rows':[{'values':[{} for _ in range(48)]}],'fields':'userEnteredValue'}},cell('R20','01_설정',6,2,'TEST.REV.7')],
'N30':[cell('N30','IN_PERSON',4,2,'시험 인물'),cell('N30','01_설정',6,2,'TEST.REV.3')],
'N20':[cell('N20','01_설정',6,2,'TEST.REV.3'),cell('N20','01_설정',20,11,'TEST.REV.3')],
'H90':[cell('H90','01_설정',20,11,'TEST.REV.7'),cell('H90','01_설정',21,11,'TEST.REV.3'),cell('H90','01_설정',22,11,'TEST.REV.3')]}
plan={'step_id':'SF_final_restore','status':'요청 생성 · 미실행','scope':'TEST 6파일 중 변경된4파일만','expected':{'population':100,'population_records':1,'person_name':'시험 인물','point_active':True,'boundary_source_row14_empty':True,'capacity':11},'retained':'검증된확장capacity11/named range 끝14는유지. 합성추가자료행14만제거.','writes':[{'file_code':'TEST-'+c,'spreadsheet_id':ids[c],'requests':r} for c,r in requests.items()]}
(P/'SF_final_restore.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared restoration to initial TEST facts, retaining verified capacity 11.')
