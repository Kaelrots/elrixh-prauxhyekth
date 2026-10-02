"""Compile requests only. This file never sends network requests."""
import json, pathlib, hashlib, re, datetime

BASE=pathlib.Path(__file__).parent
SPEC=BASE.parent/'PH1'/'명세확정'
OUT=BASE/'small_flow_requests'
OUT.mkdir(exist_ok=True)
layout=json.loads((BASE/'physical_layout.json').read_text(encoding='utf-8'))
protocol=json.loads((SPEC/'small_flow_test_protocol.json').read_text(encoding='utf-8'))
RUN='TEST-SF-20261002-01'
SCHEMA='PH2-SMALL-FLOW-1'
CAP=10
CODE_ORDER=['C00','R10','R20','N30','N20','H90']
files={x['operating_file_code']:x for x in layout['small_flow_test_layouts']}
created={c:json.loads((BASE/f'test_created_{c}.json').read_text(encoding='utf-8')) for c in CODE_ORDER}
initial={c:json.loads((BASE/f'test_initial_{c}.json').read_text(encoding='utf-8')) for c in CODE_ORDER}
ids={c:created[c]['result']['id'] for c in CODE_ORDER}
for c in CODE_ORDER:
    assert created[c]['file_code']=='TEST-'+c
    assert created[c]['creation_route']=='N60_empty_native_copy_for_disposable_test'
    assert initial[c]['spreadsheetId']==ids[c]
    assert initial[c]['properties']['title'].startswith('TEST-'+c+' ')
assert len(set(ids.values()))==6
for p in BASE.glob('created_*.json'):
    x=json.loads(p.read_text(encoding='utf-8'))
    assert not any(i in json.dumps(x,ensure_ascii=False) for i in ids.values()),'TEST matches operating file'
assert not ({'1EACdRIiAPGk4LAbttpXZiJd_cuqIh-cVi4jQsbfmqDw','1mTRKFfCFtiTmuAR6QwrslcBI6Q-wutYzVP_weDAW9uI'}&set(ids.values()))

def key(b):return b.get('logical_table_id') or b.get('dataset_id')
blocks={c:{key(b):b for b in f['blocks']} for c,f in files.items()}
def fields(b):return [x['field_id'] for x in b['columns']]
def letter(n):
    s=''
    while n:s=chr(65+(n-1)%26)+s;n=(n-1)//26
    return s
def q(s):return "'"+s.replace("'","''")+"'"
def cellref(b,f,r):return f"{q(b['tab_title'])}!{letter(fields(b).index(f)+1)}{r}"
def rng(b,f,end=13):return f"{q(b['tab_title'])}!${letter(fields(b).index(f)+1)}$4:${letter(fields(b).index(f)+1)}${end}"
def raw_ref(b,f,r):return f'=IF({cellref(b,b["primary_key_fields"][0],r)}="","",IF({cellref(b,f,r)}="","",{cellref(b,f,r)}))'
def fvalue(v):
    if v is None:return {}
    if isinstance(v,bool):return {'userEnteredValue':{'boolValue':v}}
    if isinstance(v,(int,float)):return {'userEnteredValue':{'numberValue':v}}
    if v.startswith('='):return {'userEnteredValue':{'formulaValue':v}}
    return {'userEnteredValue':{'stringValue':v}}
def update(c,tab,row,col,matrix):
    assert matrix and all(len(r)==len(matrix[0]) for r in matrix)
    return {'updateCells':{'range':{'sheetId':sheet_ids[c][tab],'startRowIndex':row-1,'endRowIndex':row-1+len(matrix),'startColumnIndex':col-1,'endColumnIndex':col-1+len(matrix[0])},'rows':[{'values':[fvalue(x) for x in r]} for r in matrix],'fields':'userEnteredValue'}}
def single(c,tab,row,col,v):return update(c,tab,row,col,[[v]])
def patch_field(c,table,field,value,row=4):
    b=blocks[c][table];return single(c,b['tab_title'],row,fields(b).index(field)+1,value)
def record_matrix(c,table,record):return [[record.get(f) for f in fields(blocks[c][table])]]

# Every edge is confined to the verified TEST allowlist. No N20 -> N30 edge exists.
edges=[('R10','C00','PUB_CODEBOOK_V2'),('R20','C00','PUB_CODEBOOK_V2'),('R20','R10','PUB_REGIONS_V2'),('N20','N30','PUB_PERSON_V2'),('H90','R20','PUB_POPULATION_V2'),('H90','N30','PUB_PERSON_V2'),('H90','N20','PUB_OFFICE_TERM_V2'),('H90','C00','PUB_CODEBOOK_V2')]
def stem(ds):return ds.removeprefix('PUB_').removesuffix('_V2')
def ref_tab(ds):return 'REF_'+stem(ds)
def meta_tab(ds):return 'META_'+stem(ds)
def rmeta_tab(ds):return 'RMETA_'+stem(ds)
incoming={c:[(o,d) for cc,o,d in edges if cc==c] for c in CODE_ORDER}
edge_rows={(c,d):20+i for c in CODE_ORDER for i,(o,d) in enumerate(incoming[c])}
def status(c,d):return f"{q('01_설정')}!G{edge_rows[c,d]}"
def countstatus(c,d):return f"{q('01_설정')}!J{edge_rows[c,d]}"
def freshness(c,d):return f"{q('01_설정')}!M{edge_rows[c,d]}"
def refblock(owner,ds):
    b=dict(blocks[owner][ds]);b['tab_title']=ref_tab(ds);return b
def guarded_lookup(c,ds,owner,keyfield,keyexpr,valuefield,end=13):
    b=refblock(owner,ds)
    return f'IF({status(c,ds)}<>"연결확인",{status(c,ds)},IF(COUNTIFS({rng(b,keyfield,end)},{keyexpr})<>1,"키 없음·중복",INDEX({rng(b,valuefield,end)},MATCH({keyexpr},{rng(b,keyfield,end)},0))))'

sheet_names={}
for c in CODE_ORDER:
    names=['00_안내','01_설정']+[b['tab_title'] for b in files[c]['blocks']]
    names+=['VALID_자료','VIEW_소형흐름']
    names += [meta_tab(key(b)) for b in files[c]['blocks'] if b['kind']=='provider']
    for o,d in incoming[c]:names.extend([ref_tab(d),rmeta_tab(d)])
    assert len(names)==len(set(names))
    sheet_names[c]=names
sheet_ids={c:{n:71000000+CODE_ORDER.index(c)*1000+i for i,n in enumerate(sheet_names[c])} for c in CODE_ORDER}

reg=json.loads((BASE/'reg_seed_records.json').read_text(encoding='utf-8'))
value_evidence=next(x for x in reg['validation_option_candidates'] if x['source_field_id']=='REG-V1:456698286:D')
assert value_evidence['options_raw']==['값 있음','추정','미정','미상','해당 없음']
value_status='값 있음'
fixture_common={'setting_status':'초안','source_snapshot_id':RUN,'schema_version':SCHEMA,'release_id':RUN,'source_locator':'TEST fixture: small_flow_test_protocol.json','legacy_locator':RUN,'note':'기술 시험값. 세계관 설정 아님.'}
fixtures={
 'C00':{'공통기준':[{'standard_id':'TEST-REGION-CLASS','current_revision_id':'TEST-REV-CLASS-001','legacy_locator':RUN}],
        '기준개정이력':[{'standard_id':'TEST-REGION-CLASS','domain':'TEST 분류','item_name':'시험 지역분류','value_raw':'TEST-REGION-CLASS','value_text':'시험 지역분류','revision_id':'TEST-REV-CLASS-001','route':'TEST-A','era':'TEST-ERA','legacy_locator':RUN,'notes':'명시된 합성 fixture. 운영 분류 아님.'}],
        '코드북':[{'group_code':'region_class','stored_code':'TEST-REGION-CLASS','display_name':'시험 지역분류','definition':'SF-01 합성 시험 분류','usage_status':'사용','legacy_locator':RUN},
                {'group_code':'value_status','stored_code':value_status,'display_name':value_status,'definition':'REG 온라인 인구 드롭다운의 원문 옵션. TEST 코드북에만 사용. 운영 코드북 확정 아님.','usage_status':'사용','legacy_locator':'REG-V1:456698286:D','source_snapshot_id':reg['source_snapshot_id']} ]},
 'R10':{'지역목록':[dict(fixture_common,region_id='TEST-REGION-001',name_ko='시험 지역',region_class='TEST-REGION-CLASS')]},
 'R20':{'인구관측':[dict(fixture_common,record_id='TEST-POP-001',region_id='TEST-REGION-001',value_numeric=100,value_status=value_status,route='TEST-A',era='TEST-ERA',year=100,time_raw='TEST-ERA 100',aggregation_include=True,population_definition='SF-01 동일조건 인구',notes='합성 기술 시험값. 운영 파일에 이관 금지.')]},
 'N30':{'IN_PERSON':[dict(fixture_common,person_id='TEST-PERSON-001',name_ko='시험 인물')]},
 'N20':{'IN_OFFICE':[dict(fixture_common,office_id='TEST-OFFICE-001',**{'직위·기관명':'시험 공직'})],
        'IN_OFFICE_TERM':[dict(fixture_common,term_id='TEST-TERM-001',person_id='TEST-PERSON-001',office_id='TEST-OFFICE-001',route='TEST-A',era='TEST-ERA',start_era='TEST-ERA',start_year=100,start_month=1,start_day=1,end_era='TEST-ERA',end_year=101,end_month=1,end_day=1,start_precision='일',end_precision='일')]},
 'H90':{'조회조건':[{'route_filter':'TEST-A','era_filter':'TEST-ERA','point_year':100,'point_month':1,'point_day':1,'reference_year':100,'region_id':'TEST-REGION-001','person_filter_id':'TEST-PERSON-001','view_id':'TEST-SMALL-FLOW'}]}}
provider_sources={('C00','PUB_STANDARDS_V2'):['기준개정이력'],('C00','PUB_CODEBOOK_V2'):['코드북'],('R10','PUB_REGIONS_V2'):['지역목록','지역목록_조회계산'],('R20','PUB_POPULATION_V2'):['인구관측','인구관측_조회계산'],('N30','PUB_PERSON_V2'):['IN_PERSON'],('N20','PUB_OFFICE_V2'):['IN_OFFICE'],('N20','PUB_OFFICE_TERM_V2'):['IN_OFFICE_TERM','CALC_OFFICE_TERM']}

def view_formula(c,b,f,r,end):
    if c=='R10':
        source=blocks[c]['지역목록']
        return raw_ref(source,f,r) if f in fields(source) else ''
    if c=='R20':
        source=blocks[c]['인구관측'];pk=cellref(source,'record_id',r);region=cellref(source,'region_id',r)
        if f in fields(source):return raw_ref(source,f,r)
        if f in ('region_name','region_level'):
            vf='name_ko' if f=='region_name' else 'region_level'
            return f'=IF({pk}="","",{guarded_lookup(c,"PUB_REGIONS_V2","R10","region_id",region,vf,end)})'
        if f=='observation_key':return f'=IF({pk}="","",{cellref(source,"route",r)}&"|"&{cellref(source,"era",r)}&"|"&{cellref(source,"year",r)}&"|"&{region})'
        return ''
    if c=='N20':
        s=blocks[c]['IN_OFFICE_TERM'];pk=cellref(s,'term_id',r)
        if f=='term_id' or f in ['schema_version','release_id']:return raw_ref(s,f,r)
        if f=='source_record_id':return raw_ref(s,'term_id',r)
        if f=='person_name':return f'=IF({pk}="","",{guarded_lookup(c,"PUB_PERSON_V2","N30","person_id",cellref(s,"person_id",r),"name_ko",end)})'
        if f=='query_end_year':return raw_ref(s,'end_year',r)
        if f in ['query_start_order','query_end_order']:
            p='start' if f=='query_start_order' else 'end';a=[cellref(s,p+'_'+z,r) for z in ['year','month','day']]
            return f'=IF({pk}="","",IF(AND({",".join("ISNUMBER("+x+")" for x in a)}),{a[0]}*10000+{a[1]}*100+{a[2]},"정밀도 부족"))'
        if f=='직위명_자동':
            off=blocks[c]['IN_OFFICE'];kp=cellref(s,'office_id',r)
            return f'=IF({pk}="","",IF(COUNTIFS({rng(off,"office_id",end)},{kp})<>1,"키 없음·중복",INDEX({rng(off,"직위·기관명",end)},MATCH({kp},{rng(off,"office_id",end)},0))))'
        if f=='connection_status':return f'=IF({pk}="","",{status(c,"PUB_PERSON_V2")})'
        return ''
    return ''

def provider_formula(c,b,f,r,end):
    sources=[blocks[c][t] for t in provider_sources[c,key(b)]];s=sources[0];pk=cellref(s,s['primary_key_fields'][0],r)
    for src in sources:
        if f in fields(src):return raw_ref(src,f,r)
    extra={'owner_file_code':'"TEST-'+c+'"','owner_spreadsheet_id':f'{q("01_설정")}!$B$4','schema_version':'"'+SCHEMA+'"','release_id':f'{q("01_설정")}!$B$5','source_revision':f'{q("01_설정")}!$B$6','record_count':f'COUNTIF({rng(s,s["primary_key_fields"][0],end)},"?*")'}
    return f'=IF({pk}="","",{extra[f]})' if f in extra else ''

def all_formulas(c,start=4,end=13,bound=None):
    bound=end if bound is None else bound
    req=[]
    for b in files[c]['blocks']:
        if b['kind']=='provider':matrix=[[provider_formula(c,b,f,r,bound) for f in fields(b)] for r in range(start,end+1)]
        elif b['tab_title'].startswith('VIEW_') and c in ['R10','R20','N20']:matrix=[[view_formula(c,b,f,r,bound) for f in fields(b)] for r in range(start,end+1)]
        else:continue
        req.append(update(c,b['tab_title'],start,1,matrix))
    return req

def metadata_formulas(c,end=13):
    req=[]
    for b in files[c]['blocks']:
        if b['kind']!='provider':continue
        ds=key(b);s=blocks[c][provider_sources[c,ds][0]]
        req.append(update(c,meta_tab(ds),4,1,[[ds,f'={q("01_설정")}!B6',f'=COUNTIF({rng(s,s["primary_key_fields"][0],end)},"?*")',f'=TEXTJOIN("|",FALSE,{q(b["tab_title"])}!A3:{letter(len(fields(b)))}3)',f'={q("01_설정")}!B5']]))
    return req

def connection_formulas(c,end=13):
    req=[]
    for owner,ds in incoming[c]:
        row=edge_rows[c,ds];b=blocks[owner][ds];width=len(fields(b));rb=refblock(owner,ds)
        observed=f'=IF(ISERROR({q(ref_tab(ds))}!A3),"연결실패",TEXTJOIN("|",FALSE,{q(ref_tab(ds))}!A3:{letter(width)}3))'
        conn=f'=IF(ISERROR({q(ref_tab(ds))}!A3),IF(N{row}="승인 대기","연결 승인 대기","연결실패"),IF(F{row}<>E{row},"스키마 불일치","연결확인"))'
        pcount=f'=IF(ISERROR({q(rmeta_tab(ds))}!A3),"메타 연결실패",IF({q(rmeta_tab(ds))}!A3<>"dataset_id","메타 스키마 불일치",{q(rmeta_tab(ds))}!C4))'
        rcount=f'=IF(G{row}<>"연결확인","미확인",COUNTIF({rng(rb,b["primary_key_fields"][0],end)},"?*"))'
        equal=f'=IF(OR(NOT(ISNUMBER(H{row})),NOT(ISNUMBER(I{row}))),"미확인",IF(H{row}=I{row},"일치","불일치"))'
        rev=f'=IF(ISERROR({q(rmeta_tab(ds))}!A3),"미확인",{q(rmeta_tab(ds))}!B4)'
        fresh=f'=IF(G{row}<>"연결확인","미확인",IF(L{row}=K{row},"판본 일치","갱신 대기"))'
        req.append(update(c,'01_설정',row,6,[[observed,conn,pcount,rcount,equal,'TEST.REV.1',rev,fresh]]))
    return req

def overflow_formulas(c,end=13):
    req=[]
    for i,b in enumerate(x for x in files[c]['blocks'] if x['kind']=='logical_table' and not x['tab_title'].startswith(('VIEW_','CHECK_'))):
        k=b['primary_key_fields'][0];rr=4+i
        req.append(update(c,'VALID_자료',rr,1,[[key(b),f'=COUNTIF({rng(b,k,end)},"?*")',f'=IF(COUNTIF({cellref(b,k,end+1)},"?*")>0,"범위초과","범위내")',f'=TEXTJOIN("|",FALSE,{q(b["tab_title"])}!A3:{letter(len(fields(b)))}3)']]))
    return req

def hub_formulas(end=13):
    c='H90';req=[];pop=refblock('R20','PUB_POPULATION_V2');term=refblock('N20','PUB_OFFICE_TERM_V2');person=refblock('N30','PUB_PERSON_V2');query=blocks[c]['조회조건']
    ps=status(c,'PUB_POPULATION_V2');pj=countstatus(c,'PUB_POPULATION_V2');pr=freshness(c,'PUB_POPULATION_V2');ts=status(c,'PUB_OFFICE_TERM_V2')
    conds=[(rng(pop,'route',end),cellref(query,'route_filter',4)),(rng(pop,'era',end),cellref(query,'era_filter',4)),(rng(pop,'year',end),cellref(query,'reference_year',4)),(rng(pop,'region_id',end),cellref(query,'region_id',4))]
    cargs=','.join(x for pair in conds for x in pair);total=f'COUNTIFS({cargs})';codes=status(c,'PUB_CODEBOOK_V2');cb=refblock('C00','PUB_CODEBOOK_V2')
    validcode=f'COUNTIFS({rng(cb,"group_code",end)},"value_status",{rng(cb,"stored_code",end)},"{value_status}")=1'
    popstate=f'=IF({ps}<>"연결확인",{ps},IF({pj}<>"일치","건수 불일치",IF({pr}<>"판본 일치","갱신 대기",IF({codes}<>"연결확인",{codes},IF(NOT({validcode}),"값상태 코드 없음·중복",IF({total}=0,"자료없음",IF(COUNTIFS({cargs},{rng(pop,"value_status",end)},"{value_status}")<>{total},"값상태 확인 필요","자료 있음")))))))'
    sumformula=f'=IF(B4<>"자료 있음",B4,SUMIFS({rng(pop,"value_numeric",end)},{cargs}))'
    # Empty numeric cells must not silently become a legitimate sum of zero.
    numeric_count='+'.join(f'IF(AND({cellref(pop,"route",r)}={cellref(query,"route_filter",4)},{cellref(pop,"era",r)}={cellref(query,"era_filter",4)},{cellref(pop,"year",r)}={cellref(query,"reference_year",4)},{cellref(pop,"region_id",r)}={cellref(query,"region_id",4)},ISNUMBER({cellref(pop,"value_numeric",r)})),1,0)' for r in range(4,end+1))
    sumformula=f'=IF(B4<>"자료 있음",B4,IF(({numeric_count})<>B5,"수치 없음",SUMIFS({rng(pop,"value_numeric",end)},{cargs})))'
    person_name='='+guarded_lookup(c,'PUB_OFFICE_TERM_V2','N20','term_id','"TEST-TERM-001"','person_name',end)
    point=f'{cellref(query,"point_year",4)}*10000+{cellref(query,"point_month",4)}*100+{cellref(query,"point_day",4)}'
    def termval(f):return f'INDEX({rng(term,f,end)},MATCH("TEST-TERM-001",{rng(term,"term_id",end)},0))'
    interval=f'=IF({ts}<>"연결확인",{ts},IF(COUNTIFS({rng(term,"term_id",end)},"TEST-TERM-001")<>1,"키 없음·중복",IF(AND(ISNUMBER({termval("query_start_order")}),ISNUMBER({termval("query_end_order")})),AND({termval("route")}={cellref(query,"route_filter",4)},{termval("era")}={cellref(query,"era_filter",4)},{point}>={termval("query_start_order")},{point}<{termval("query_end_order")}),"정밀도 부족")))'
    direct='='+guarded_lookup(c,'PUB_PERSON_V2','N30','person_id','"TEST-PERSON-001"','name_ko',end)
    locator='='+guarded_lookup(c,'PUB_POPULATION_V2','R20','record_id','"TEST-POP-001"','legacy_locator',end)
    namecheck=f'=IF(OR({ts}<>"연결확인",{status(c,"PUB_PERSON_V2")}<>"연결확인"),"연결 미확인",IF(OR(COUNTIFS({rng(term,"term_id",end)},"TEST-TERM-001")<>1,COUNTIFS({rng(person,"person_id",end)},"TEST-PERSON-001")<>1),"키 없음·중복",IF({termval("connection_status")}<>"연결확인","상위 연결 미확인",IF(OR(B8="",B10=""),"이름 없음",B8=B10))))'
    req.append(update(c,'VIEW_소형흐름',4,1,[['인구 자료 상태',popstate],['동일조건 자료 건수',f'=IF({ps}<>"연결확인","미확인",{total})'],['동일조건 인구',sumformula],['인구 원본 위치',locator],['N20 임기에서 읽은 인물명',person_name],['조회 시점 재직 여부',interval],['N30 직접 인물명',direct],['이름 일치',namecheck]]))
    return req

stages={c:{'00_structure':[],'01_headers_config_fixtures':[],'02_sample_formulas':[],'03_fill_capacity':[]} for c in CODE_ORDER}
for c in CODE_ORDER:
    st=stages[c]
    for n in sheet_names[c]:
        st['00_structure'].append({'addSheet':{'properties':{'sheetId':sheet_ids[c][n],'title':n,'gridProperties':{'rowCount':120,'columnCount':80,'frozenRowCount':3,'frozenColumnCount':1}}}})
    # Rename conflicts first. Deletion is restricted to the snapshotted TEST-only sheet IDs.
    rename=[{'updateSheetProperties':{'properties':{'sheetId':s['properties']['sheetId'],'title':'ARCHIVE_TEST_INIT_'+str(i+1)},'fields':'title'}} for i,s in enumerate(initial[c]['sheets']) if s['properties']['title'] in sheet_names[c]]
    st['00_structure']=rename+st['00_structure']+[{'deleteSheet':{'sheetId':s['properties']['sheetId']}} for s in initial[c]['sheets']]
    st['00_structure'].append({'updateSpreadsheetProperties':{'properties':{'locale':'ko_KR','timeZone':'Asia/Seoul'},'fields':'locale,timeZone'}})
    hdr=st['01_headers_config_fixtures']
    for b in files[c]['blocks']:
        hdr.append(single(c,b['tab_title'],1,1,key(b)+' · 전용 TEST'))
        hdr.append(update(c,b['tab_title'],2,1,[[x['label_ko'] for x in b['columns']],fields(b)]))
        hdr.append({'addNamedRange':{'namedRange':{'namedRangeId':b['named_range'],'name':b['named_range'],'range':{'sheetId':sheet_ids[c][b['tab_title']],'startRowIndex':2,'endRowIndex':13,'startColumnIndex':0,'endColumnIndex':len(fields(b))}}}})
    hdr.append(update(c,'00_안내',1,1,[['소형 연결시험','TEST-'+c],['자료 성격','합성 기술시험값. 세계관 설정 및 운영16파일과 분리.'],['실행 상태','시험 미실행. API와 UI 읽기로 기대값까지 검증한 뒤 판정.'],['원본 단일화','N30 인물 → N20 임기 → H90. N30은 N20을 읽지 않음.'],['연결 승인','REF 탭의 A3에서 접근 허용이 필요하면 실제 TEST 공급자 ID를 확인한 후 허용.'],['코드 근거','값 있음: REG-V1 온라인 인구 D열 검증옵션. TEST 코드북에만 명시해 사용. 운영 채택과 구별.'],['오류 처리','REF 원오류 보존. 0·자료없음·연결실패·스키마 불일치·갱신 대기를 구별.'],['범위','초기 자료행4:13. 다음 경계행14. 확장시 입력·계산·검증·제공·소비를 동시 갱신.']]))
    hdr.append(update(c,'01_설정',1,1,[['시험 설정','값'],['파일 코드','TEST-'+c],['범위','TEST 전용'],['실제 파일 ID',ids[c]],['시험 실행 ID',RUN],['원본 판본','TEST.REV.1'],['자료 용량',10]]))
    hdr.append(update(c,'01_설정',19,1,[['제공자료','공급 파일','실제 공급자 ID','수신 범위','기대 스키마','읽은 스키마','연결 상태','공급 건수','수신 건수','건수 비교','기대 판본','읽은 판본','갱신 상태','권한 관측']]))
    hdr.append(update(c,'VALID_자료',3,1,[['원자료표','현재 건수','다음 행 초과','스키마 서명']]))
    hdr.append(update(c,'VIEW_소형흐름',3,1,[['항목','결과']]))
    for table,recs in fixtures[c].items():
        for i,rec in enumerate(recs):hdr.append(update(c,blocks[c][table]['tab_title'],4+i,1,record_matrix(c,table,rec)))
    for b in files[c]['blocks']:
        if b['kind']!='provider':continue
        ds=key(b);mt=meta_tab(ds)
        hdr.append(update(c,mt,3,1,[['dataset_id','source_revision','record_count','schema_signature','run_id']]))
        hdr.append({'addNamedRange':{'namedRange':{'namedRangeId':'META_'+ds,'name':'META_'+ds,'range':{'sheetId':sheet_ids[c][mt],'startRowIndex':2,'endRowIndex':4,'startColumnIndex':0,'endColumnIndex':5}}}})
    for owner,ds in incoming[c]:
        rr=edge_rows[c,ds];b=blocks[owner][ds]
        hdr.append(update(c,'01_설정',rr,1,[[ds,'TEST-'+owner,ids[owner],ds,'|'.join(fields(b))]]))
        hdr.append(single(c,'01_설정',rr,14,'미확인'))
        hdr.append(single(c,ref_tab(ds),1,1,'TEST-'+owner+' '+ds+' · 원오류 보존'))
        hdr.append(update(c,ref_tab(ds),2,1,[[x['label_ko'] for x in b['columns']]]))
        st['02_sample_formulas'].append(single(c,ref_tab(ds),3,1,f'=IMPORTRANGE({q("01_설정")}!C{rr},{q("01_설정")}!D{rr})'))
        st['02_sample_formulas'].append(single(c,rmeta_tab(ds),3,1,f'=IMPORTRANGE({q("01_설정")}!C{rr},"META_{ds}")'))
    st['02_sample_formulas']+=all_formulas(c,4,5,bound=13)+metadata_formulas(c)+connection_formulas(c)+overflow_formulas(c)
    st['03_fill_capacity']+=all_formulas(c,6,13)
    # The sample uses full declared bounded ranges but fills only its first formula row.
    st['02_sample_formulas']=[r for r in st['02_sample_formulas']]
    if c=='R10':
        src=blocks[c]['지역목록'];rb=refblock('C00','PUB_CODEBOOK_V2');cid=cellref(src,'region_class',4)
        lookup=guarded_lookup(c,'PUB_CODEBOOK_V2','C00','stored_code',cid,'display_name')
        st['02_sample_formulas'].append(update(c,'VIEW_소형흐름',4,1,[['분류 코드',f'={cid}'],['C00 분류명','='+lookup]]))
    if c=='H90':st['02_sample_formulas']+=hub_formulas()
    # Basic styling remains separate from values. Gray headers only, no colored bands.
    for name in sheet_names[c]:
        sid=sheet_ids[c][name]
        hdr.extend([{'repeatCell':{'range':{'sheetId':sid,'startRowIndex':0,'endRowIndex':30,'startColumnIndex':0,'endColumnIndex':80},'cell':{'userEnteredFormat':{'textFormat':{'fontFamily':'Arial','fontSize':10},'verticalAlignment':'MIDDLE','wrapStrategy':'WRAP'}},'fields':'userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy'}},
                    {'repeatCell':{'range':{'sheetId':sid,'startRowIndex':1,'endRowIndex':3,'startColumnIndex':0,'endColumnIndex':80},'cell':{'userEnteredFormat':{'backgroundColor':{'red':0.95,'green':0.96,'blue':0.96}}},'fields':'userEnteredFormat.backgroundColor'}},
                    {'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':0,'endIndex':80},'properties':{'pixelSize':170},'fields':'pixelSize'}}])

# Local compiler validations. These do not declare any Google Sheets test passed.
manifest={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_id':RUN,'status':'요청 생성 · 온라인 미실행','allowlisted_test_ids':ids,'operating_file_ids_excluded':True,'source_layout_sha256':hashlib.sha256((BASE/'physical_layout.json').read_bytes()).hexdigest(),'initial_inventory_sha256':{c:hashlib.sha256((BASE/f'test_initial_{c}.json').read_bytes()).hexdigest() for c in CODE_ORDER},'source_value_status_evidence':value_evidence,'value_status_adoption':'TEST 코드북에만 원문 옵션 사용. 운영 V2 코드북 확정 아님.','files':{},'edges':[{'provider':'TEST-'+o,'consumer':'TEST-'+c,'dataset_id':d} for c,o,d in edges],'all_case_results':'미실행','preflight_required':['실행 직전 실제 파일 ID·title TEST-prefix·sheet IDs가 저장된 inventory와 같은지 읽기','구조요청은 최초 1회만. 적용후 재실행 금지; 실제 metadata에서 진행상태 판정','기존 8탭 삭제는 각 test_initial ID에만 적용. 운영·V1·다른 파일 대상 금지','원자료 변경·비우기 전 get_cells로 백업. 이전 값을 복원할 수 있어야 함.','02 첫행 결과·권한·원오류 검증 후에만 03 용량 수식 확장','전수 native readback+UI 전에는 통과 판정 금지'],'formula_notes':['year*10000+month*100+day는 TEST-ERA에서만 정렬키. 날짜serial·일수환산 아님.','날짜정보 부족은 정밀도 부족. 열린 끝을 임의 infinity로 만들지 않음.','CHECK 표는 운영 계산의 원본이 아니다. 수신가드는 01_설정/REF에서 직접 관측.','원본 판본은 명시적 변경 묶음으로 갱신. NOW 값으로 수신성공을 주장하지 않음.']}
for c in CODE_ORDER:
    manifest['files'][c]={'spreadsheet_id':ids[c],'url':created[c]['result']['url'],'sheet_ids':sheet_ids[c],'stages':{}}
    for stage,reqs in stages[c].items():
        for r in reqs:
            assert len(r)==1
            if 'updateCells' in r:
                v=r['updateCells'];gr=v['range'];assert len(v['rows'])==gr['endRowIndex']-gr['startRowIndex'];assert all(len(row['values'])==gr['endColumnIndex']-gr['startColumnIndex'] for row in v['rows'])
        out=OUT/f'{c}_{stage}.json';out.write_text(json.dumps({'spreadsheet_id':ids[c],'requests':reqs},ensure_ascii=False,indent=2),encoding='utf-8')
        manifest['files'][c]['stages'][stage]={'path':str(out),'requests':len(reqs),'status':'미실행'}

def stage(name,writes,expected,readbacks,gate=None):
    data={'step_id':name,'run_id':RUN,'result':'미실행','preconditions':gate or ['앞 단계 native 읽기 확인','정확한 TEST 대상 ID 검증'],'writes':[{'spreadsheet_id':ids[c],'file_code':'TEST-'+c,'requests':req} for c,req in writes.items()],'expected':expected,'readback':readbacks}
    (OUT/f'{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');return str(OUT/f'{name}.json')
def rev_updates(changed,rev):
    d={c:[single(c,'01_설정',6,2,rev)] for c in changed}
    for c,o,ds in edges:
        if o in changed:d.setdefault(c,[]).append(single(c,'01_설정',edge_rows[c,ds],11,rev))
    return d
def merge(a,c,req):a.setdefault(c,[]).extend(req);return a
steps=[]
steps.append(stage('SF01_SF02_initial',{}, {'H90_VIEW_소형흐름_B6':100,'H90_VIEW_소형흐름_B8':'시험 인물','H90_VIEW_소형흐름_B9':True,'R10_VIEW_소형흐름_B5':'시험 지역분류','all_connection':'연결확인','all_count':'일치','all_revision':'판본 일치'},['H90:VIEW_소형흐름!A3:B11','R10:VIEW_소형흐름!A3:B5','all:01_설정!A19:M24','all:VALID_자료!A3:D7']))
steps.append(stage('SF02_end_exclusive',{'H90':[patch_field('H90','조회조건','point_year',101)]},{'H90_VIEW_소형흐름_B9':False},['H90:VIEW_소형흐름!A9:B9']))
steps.append(stage('SF02_restore_point',{'H90':[patch_field('H90','조회조건','point_year',100)]},{'H90_VIEW_소형흐름_B9':True},['H90:VIEW_소형흐름!A9:B9']))
d=rev_updates(['R20','N30','N20'],'TEST.REV.2');merge(d,'R20',[patch_field('R20','인구관측','value_numeric',200)]);merge(d,'N30',[patch_field('N30','IN_PERSON','name_ko','시험 인물 수정')])
steps.append(stage('SF03_change',d,{'H90_VIEW_소형흐름_B6':200,'H90_VIEW_소형흐름_B8':'시험 인물 수정','H90_VIEW_소형흐름_B10':'시험 인물 수정'},['H90:VIEW_소형흐름!A3:B11','N20:VIEW_OFFICE_TERM!A4:O4','all:01_설정!A19:M24']))
d=rev_updates(['R20'],'TEST.REV.3');merge(d,'R20',[patch_field('R20','인구관측','value_numeric',0)])
steps.append(stage('SF04_numeric_zero',d,{'H90_VIEW_소형흐름_B4':'자료 있음','H90_VIEW_소형흐름_B6':0},['H90:VIEW_소형흐름!A4:B6']))
d=rev_updates(['R20'],'TEST.REV.4');merge(d,'R20',[update('R20',blocks['R20']['인구관측']['tab_title'],4,1,[[None]*len(fields(blocks['R20']['인구관측']))])])
steps.append(stage('SF04_empty',d,{'H90_VIEW_소형흐름_B4':'자료없음','H90_VIEW_소형흐름_B6':'자료없음','provider_count':0,'receiver_count':0},['H90:VIEW_소형흐름!A4:B6','H90:01_설정!A20:M20','R20:IN_인구관측!A4:AV4'],['TEST-R20 원자료4행 get_cells 백업 저장 후만 실행','0단계 실제0 readback 확인']))
rr=edge_rows['H90','PUB_POPULATION_V2']
steps.append(stage('SF04_connection_failure',{'H90':[single('H90','01_설정',rr,4,'TEST_RANGE_DOES_NOT_EXIST')]},{'H90_VIEW_소형흐름_B4':'연결실패','H90_VIEW_소형흐름_B6':'연결실패','H90_REF_POPULATION_A3':'native #REF! with error details; numeric0 forbidden'},['H90:REF_POPULATION!A3:D5','H90:VIEW_소형흐름!A4:B6','H90:01_설정!A20:M20']))
d=rev_updates(['R20'],'TEST.REV.5');restore=dict(fixtures['R20']['인구관측'][0],value_numeric=200);merge(d,'R20',[update('R20','IN_인구관측',4,1,record_matrix('R20','인구관측',restore))]);merge(d,'H90',[single('H90','01_설정',rr,4,'PUB_POPULATION_V2')])
steps.append(stage('SF04_restore',d,{'H90_VIEW_소형흐름_B6':200,'provider_count':1,'receiver_count':1},['H90:VIEW_소형흐름!A4:B6','H90:01_설정!A20:M20']))
popb=blocks['R20']['PUB_POPULATION_V2'];popcolumn=fields(popb).index('value_numeric')+1
steps.append(stage('SF05_header_drift',{'R20':[single('R20',popb['tab_title'],3,popcolumn,'TEST_DRIFT_value_numeric')]},{'H90_connection':'스키마 불일치','H90_VIEW_소형흐름_B6':'스키마 불일치'},['R20:PUB_POPULATION!A3:AZ3','H90:REF_POPULATION!A3:AZ3','H90:VIEW_소형흐름!A4:B6']))
steps.append(stage('SF05_restore',{'R20':[single('R20',popb['tab_title'],3,popcolumn,'value_numeric')]},{'H90_VIEW_소형흐름_B6':200,'H90_connection':'연결확인'},['H90:01_설정!A20:M20','H90:VIEW_소형흐름!A4:B6']))
boundary=dict(fixtures['R20']['인구관측'][0],record_id='TEST-POP-011',value_numeric=50,legacy_locator=RUN+'|boundary_row=14')
steps.append(stage('SF06_append_boundary',{'R20':[update('R20','IN_인구관측',14,1,record_matrix('R20','인구관측',boundary))]},{'R20_VALID_자료_C4':'범위초과','H90_VIEW_소형흐름_B6':200,'provider_count':1,'boundary_not_yet_included':True},['R20:IN_인구관측!A14:AV14','R20:VALID_자료!A4:D4','H90:VIEW_소형흐름!A4:B6']))
d=rev_updates(['R20'],'TEST.REV.6')
merge(d,'R20',[single('R20','01_설정',7,2,11)]+all_formulas('R20',4,14)+metadata_formulas('R20',14)+overflow_formulas('R20',14))
for b in files['R20']['blocks']:
    merge(d,'R20',[{'updateNamedRange':{'namedRange':{'namedRangeId':b['named_range'],'range':{'sheetId':sheet_ids['R20'][b['tab_title']],'startRowIndex':2,'endRowIndex':14,'startColumnIndex':0,'endColumnIndex':len(fields(b))}},'fields':'range'}}])
merge(d,'H90',[single('H90','01_설정',7,2,11)]+connection_formulas('H90',14)+hub_formulas(14))
# connection_formulas initializes expected revisions; restore current values in the same atomic batch.
for c,o,ds in edges:
    if c=='H90':merge(d,c,[single(c,'01_설정',edge_rows[c,ds],11, 'TEST.REV.6' if o=='R20' else 'TEST.REV.2' if o in ['N30','N20'] else 'TEST.REV.1')])
steps.append(stage('SF06_expand_all_ranges',d,{'H90_VIEW_소형흐름_B6':250,'provider_count':2,'receiver_count':2,'R20_VALID_자료_C4':'범위내'},['R20:IN_인구관측!A3:AV14','R20:VIEW_인구관측_조회계산!A3:G14','R20:PUB_POPULATION!A3:AZ14','R20:VALID_자료!A3:D5','H90:REF_POPULATION!A3:AZ14','H90:VIEW_소형흐름!A4:B6','H90:01_설정!A20:M23'],['SF06확장 전5범위·named range·입력행백업','TEST-R20과TEST-H90 요청을 같은 이관배치로 적용하고 양쪽 native readback 완료']))
manifest['case_step_files']=steps
manifest['test_result_rule']='실제 결과/권한/원본판본/읽기시각/경과시간/API및UI증거를 모두 기록하기 전에는 미실행 유지. 수식문자열 정적검사는 case 통과 아님.'
(OUT/'small_flow_request_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'files':6,'request_files':24,'case_steps':len(steps),'edges':len(edges),'result':'LOCAL_REQUESTS_COMPILED_NOT_EXECUTED','output':str(OUT)},ensure_ascii=False))
