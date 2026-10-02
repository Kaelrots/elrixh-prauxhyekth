from pathlib import Path
import csv,json,re,hashlib,sys
from collections import defaultdict
from datetime import datetime,timezone,timedelta
sys.stdout.reconfigure(encoding='utf-8')
OUT=Path(__file__).resolve().parent
PH1=OUT.parent
BASE=PH1.parents[1]
REG_SHEETS={'00 공통 기준','02 국가 마스터','03 문화 마스터','04 종교 마스터','05 언어 마스터','06 종족 마스터','07 자원 마스터','08 특성 사전','09 경제 지표 정의','11 역사 사건','90 출처','00_기준_메타','99_검증'}
NAT_SHEETS={'00_기준_메타','00_코드북','30_역사사건','40_행성대비_지표','41_행성_연결','42_행성_기본속성_연결','43_지역_참조_연결','44_행성_연간지표_연결','83_연방_통합연표','89_변동_연표','90_출처_레지스트리','91_스키마_안내','98_검증_요약','99_검증_상세'}
def owned(code,sheet): return sheet in (REG_SHEETS if code=='REG-V1' else NAT_SHEETS)
with (PH1/'actual_field_mapping_draft.csv').open(encoding='utf-8-sig',newline='') as f:
    fields=[x for x in csv.DictReader(f) if owned(x['source_file_code'],x['source_sheet_name'])]
inventory=json.loads((PH1/'sheet_inventory.json').read_text(encoding='utf-8-sig'))
headers=json.loads((PH1/'headers_notes_links_validations.json').read_text(encoding='utf-8-sig'))
literal_rows=defaultdict(lambda:defaultdict(dict))
with (PH1/'literal_cells.csv').open(encoding='utf-8-sig',newline='') as f:
    for x in csv.DictReader(f):
        if owned(x['source_file_code'],x['source_sheet_name']):
            row=int(re.search(r'\d+$',x['cell']).group())
            literal_rows[(x['source_file_code'],x['source_sheet_name'])][row][x['source_column']]=json.loads(x['value_json'])

if '--inspect-meta' in sys.argv:
    for key,rows in literal_rows.items():
        if key[1]=='00_기준_메타': print(json.dumps({'key':key,'rows':rows},ensure_ascii=False))
    for x in fields:
        if x['source_sheet_name']=='43_지역_참조_연결': print(json.dumps({k:x[k] for k in ['source_column','source_field','source_role']},ensure_ascii=False))
    raise SystemExit

NOW=datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
tables={}
functions=[]
issues=[]
spec=[]
status='PH1 상세 설계 초안 · 온라인 작성/이관/운영 시험 미실행'

def datatype(field):
    if field in {'value_raw','raw_value','cached_result','original_value','definition_raw','legacy_text'}: return 'json_scalar'
    if field.endswith('_ids'): return 'string_array'
    if field in {'numeric_value','value_numeric','direct_value','calculated_value','selected_value'}: return 'decimal_nullable'
    if field.startswith('is_') or field.endswith('_allowed') or field in {'aggregation_include','active'}: return 'boolean_or_unknown'
    if field.endswith('_count') or field.endswith('_year') or field.endswith('_month') or field.endswith('_day') or field in {'sort_order','priority','rank'}: return 'integer_nullable'
    if any(s in field for s in ('amount','ratio','growth','density','population','gdp','area_value','delta_value')) and not field.endswith(('_id','_ids','_raw','_status','_definition','_rule')): return 'decimal_nullable'
    return 'string_nullable'

def target(file,table,field,role,rule,selector='all_data_rows',kind=None):
    key=(file,table)
    if key not in tables:
        tables[key]={'file_code':file,'table_id':table,'schema_status':status,'fields':{},'primary_key':[],
                     'external_owner_review_required':file not in {'C00','H90'},'table_role':'mixed_until_finalized'}
    ts=tables[key]
    if field not in ts['fields']:
        ts['fields'][field]={'field_id':field,'type':kind or datatype(field),'required':False,'roles':[],'source_field_ids':[]}
    if role not in ts['fields'][field]['roles']:ts['fields'][field]['roles'].append(role)
    return {'file_code':file,'table':table,'field':field,'role':role,'rule':rule,'source_selector':selector}

def issue(id,subject,kind,basis,next_action,ids=None):
    issues.append({'issue_id':id,'subject':subject,'category':kind,'evidence_basis':basis,'next_action':next_action,
                   'source_field_ids':ids or [],'status':'미해결','does_not_authorize_setting_invention':True})

def function(id,name,owner,inputs,outputs,algorithm,tests,limits='',source_refs=None):
    functions.append({'function_id':id,'name':name,'owner_file_code':owner,'required_datasets':inputs,
       'output_tables':outputs,'algorithm':algorithm,'test_ids':tests.split(','),'status':'설계됨 · 미구현·미시험',
       'limits_and_no_data_behavior':limits,'source_refs':source_refs or [],
       'evidence_required':['TEST 사본 ID·실제 입력 범위·기대값·관측값','운영 소비범위/헤더/릴리스 대조','실제 확인 시각과 오류/미실행 구별']})

def schema_field(file,table,field,kind,required=False,description=''):
    target(file,table,field,'input' if file=='C00' else 'display','명세 추가 필드; 세계관 값 생성 없음',kind=kind)
    item=tables[(file,table)]['fields'][field]
    item.update(type=kind,required=required or item.get('required',False),description=description or item.get('description',''))

def set_table(file,table,pk,role,description):
    if (file,table) not in tables: target(file,table,pk[0] if pk else 'record_key','display',description)
    tables[(file,table)].update(primary_key=pk,table_role=role,description=description)
    for f in pk:
        schema_field(file,table,f,'string',True,'행번호가 아닌 고정 식별자; 기존 값이 없으면 이관대응에 고정 발급 기록')

def mapping(field,targets,transform,funcs=None,test_ids=None):
    row={k:field[k] for k in ['source_file_code','source_file_id','source_sheet_id','source_sheet_name','source_column','source_field_id','source_field','source_type','source_role','source_role_evidence','map_id']}
    row.update(targets_json=json.dumps(targets,ensure_ascii=False,separators=(',',':')),transform_rule=transform,
               function_ids=';'.join(funcs or []),test_ids=';'.join(test_ids or []),
               preservation_location=field['preservation_location'],header_review_required=field['header_review_required'],
               source_observation='실행시점 online XLSX + native 8행 관측; 원본 내용 이관 아님',
               spec_status=status,implementation_status='미실행',migration_status='미실행',validation_status='명세 정적 coverage만 확인; 운영 시험 아님')
    for t in targets:
        ft=tables[(t['file_code'],t['table'])]['fields'][t['field']]
        if field['source_field_id'] not in ft['source_field_ids']:ft['source_field_ids'].append(field['source_field_id'])
    spec.append(row)

COMMON_RULE='원문·기존 ID·값 상태·설정 상태·근거·판본을 보존하고 확정 상태를 새로 추정하지 않음. legacy_locator를 이관레코드 관계로 연결.'
DERIVED_RULE='V1 주소/좌표/캐시를 운영값으로 복사하지 않고 지정 V2 owner 제공표에서 다시 산출. 헤더 계약과 연결상태를 먼저 확인.'

CLASS_MAPS={
 '03 문화 마스터':('문화분류',['sort_order','culture_id','name_ko','name_original','parent_culture_id','parent_name','start_raw','end_raw','definition','multiple_membership_allowed','setting_status','source_id','source_name']),
 '04 종교 마스터':('종교분류',['sort_order','religion_id','name_ko','name_original','parent_religion_id','parent_name','start_raw','end_raw','definition','multiple_faith_allowed','setting_status','source_id','source_name']),
 '05 언어 마스터':('언어분류',['sort_order','language_id','name_ko','name_original','parent_language_id','parent_name','script_system','start_raw','end_raw','definition','setting_status','source_id','source_name']),
 '06 종족 마스터':('집단분류',['sort_order','group_id','name_ko','name_original','classification_axis','parent_group_id','parent_name','start_raw','end_raw','definition','multiple_identity_allowed','setting_status','source_id','source_name']),
 '07 자원 마스터':('자원분류',['sort_order','resource_id','resource_name','resource_category','default_unit','description','setting_status','source_id','source_name']),
 '08 특성 사전':('특성사전',['sort_order','trait_id','trait_name','trait_category','description','priority','icon_reference','effect_kind','setting_status','source_id','source_name']),
 '09 경제 지표 정의':('지표사전',['sort_order','metric_id','metric_name','subject_type','definition','unit','period_basis','aggregation_method','calculation_rule_raw','allowed_value_and_missing_rule','setting_status','source_id','source_name']),
}

def colnum(c):
    n=0
    for x in c:n=n*26+ord(x)-64
    return n

ANNUAL_FIELDS=['observation_key','subject_id','route','era','year','metric_id','unit','currency','price_base_era','price_base_year','direct_value','calculated_value','selected_value','selection_rule','coverage_status','aggregation_level','valid_record_count','unique_region_count','target_region_count','setting_status','source_id','notes','delta_value','population_growth']
PROPERTY_FIELDS=['planet_id','property_id','property_name','numeric_value','text_value','unit','calculation_method','setting_status','source_id','original_location','notes']
REGION_FIELDS=['region_id','name_ko','name_elun','name_roman','region_level','parent_region_id','parent_name','parent_region_id','parent_name','region_rank','region_category','hex','color_chip','setting_status','sort_order']

# Metadata is row keyed; column identity remains one unique source_field_id in the output.
META_REG={
2:('R10','분야설정','default_planet_id','input'),3:('C00','입력기본값','default_route','input'),
4:('R20','집계설정','aggregation_level','input'),5:('C00','인구정의','definition_name','input'),
6:('C00','단위정의','units_raw','input'),7:('C00','기년대응','legacy_era_description','input'),
8:('C00','기년대응','current_era_description','input'),9:('C00','계산정책','selection_rule_raw','input'),
10:('C00','계산정책','coverage_rule_raw','input'),11:('H90','운영안내','input_route_legacy','archive'),
12:('H90','운영안내','region_owner_legacy','archive'),13:('H90','운영안내','region_relation_legacy','archive'),
14:('H90','운영안내','environment_owner_legacy','archive'),15:('H90','운영안내','territory_owner_legacy','archive'),
16:('H90','운영안내','source_owner_legacy','archive'),17:('C00','시간정책','annual_boundary_rule_raw','input'),
18:('C00','범위레지스트리','legacy_input_capacity','archive'),19:('C00','지표사전','gdp_classification_rule','input'),
20:('C00','보존링크','legacy_target_url','archive'),
}
META_NAT={
2:('N10','분야설정','default_nation_id','input'),3:('N10','분야설정','default_planet_id','input'),
4:('H90','조회조건','route_filter','input'),5:('H90','조회조건','era_filter','input'),
6:('H90','조회조건','start_year','input'),7:('H90','조회조건','end_year','input'),8:('H90','조회조건','reference_year','input'),
9:('C00','단위정의','default_currency_raw','input'),10:('C00','시간정책','annual_boundary_rule_raw','input'),
11:('C00','시간정책','unknown_end_rule_raw','input'),12:('C00','지표사전','gdp_classification_rule','input'),
13:('C00','기년대응','legacy_era_description','input'),14:('C00','기년대응','current_era_description','input'),
15:('C00','인구정의','definition_name','input'),16:('H90','운영안내','input_visual_guide_legacy','archive'),
17:('C00','범위레지스트리','legacy_capacity_description','archive'),18:('C00','보존링크','legacy_target_url','archive'),
19:('C00','보존링크','template_backup_url','archive'),20:('N20','분야정책','seat_scope_rule_raw','input'),
21:('C00','계산정책','missing_period_rule_raw','input'),22:('N20','분야정책','ratio_selection_rule_raw','input'),
23:('C00','역법','calendar_rule_raw','input'),24:('C00','구판운영기록','legacy_release_description','archive'),
25:('C00','구판운영기록','legacy_data_scope','archive'),26:('R50','분야설정','territory_aggregation_level','input'),
27:('R50','분야설정','territory_coverage_status','input'),28:('H90','운영안내','initial_view_legacy','archive'),
29:('H90','운영안내','input_order_legacy','archive'),30:('H90','운영안내','validation_route_legacy','archive'),
31:('H90','운영안내','party_annual_legacy','archive'),32:('N20','분야정책','ballot_denominator_rule_raw','input'),
33:('N20','분야정책','post_election_seat_rule_raw','input'),34:('N20','분야정책','allocation_scope_rule_raw','input'),
35:('N20','분야정책','district_aggregation_rule_raw','input'),36:('C00','계산정책','ratio_storage_rule_raw','input'),
37:('C00','계산적합조건','definition_match_rule_raw','input'),38:('N20','분야정책','system_revision_rule_raw','input'),
39:('N20','분야정책','seat_selection_rule_raw','input'),40:('N20','분야정책','acting_succession_rule_raw','input'),
41:('N20','분야정책','reelection_rule_raw','input'),42:('N20','분야정책','party_rank_rule_raw','input'),
43:('N20','분야정책','senate_class_rule_raw','input'),44:('N20','분야정책','religious_role_rule_raw','input'),
45:('N20','분야정책','historical_exception_rule_raw','input'),46:('N20','분야정책','legacy_management_scope','archive'),
47:('C00','시간정책','exact_boundary_rule_raw','input'),48:('H90','조회조건','point_year','input'),
49:('H90','조회조건','point_month','input'),50:('H90','조회조건','point_day','input'),
51:('H90','조회조건','party_filter_id','input'),52:('H90','조회조건','person_filter_id','input'),
53:('H90','조회조건','emperor_filter_id','input'),54:('C00','표기정책','language_order_raw','input'),
55:('C00','표기정책','color_rule_raw','input'),56:('H90','운영안내','schema_guide_legacy','archive'),
57:('H90','운영안내','validation_route_legacy','archive'),58:('C00','시간정책','annual_point_difference_raw','input'),
59:('C00','시간정책','exact_boundary_rule_raw','input'),60:('H90','운영안내','new_history_route_legacy','archive'),
61:('C00','범위레지스트리','legacy_validation_capacity','archive'),62:('C00','드롭다운배포','legacy_sync_note','archive'),
63:('H90','상태필터정의','legacy_filter_rule_raw','archive'),
}

for s in fields:
    code,sh,col=s['source_file_code'],s['source_sheet_name'],s['source_column']
    n=colnum(col)-1; ts=[]; fs=[]; tests=['T-004','T-009','T-013']
    transform=COMMON_RULE
    if sh=='00 공통 기준':
        f=['standard_id','domain','item_name','value_raw','unit_format','description','setting_status','source_id','source_name'][n]
        role='formula' if col=='I' else 'input'
        ts=[target('C00','기준개정이력',f,role,'source_name은 C00 출처 레지스트리에서 조회; 그 밖의 원문 필드는 개정별로 보존.' if col=='I' else '같은 standard_id의 행을 개정 후보로 각각 보존; 마지막 행 자동 채택 금지.')]
        if col=='A': ts.append(target('C00','공통기준','standard_id','input','식별자만 중복 제거해 기준 등록. revision_id는 legacy_locator 기반 고정 대응표로 발급.'))
        fs=['C-01','C-03']; tests+=['T-014','T-016','T-017','T-022','T-024']
    elif sh in CLASS_MAPS:
        table,fl=CLASS_MAPS[sh]; f=fl[n]
        role='formula' if f in {'source_name','parent_name'} else 'input'
        rule='동일 C00 분류/출처를 ID로 조회하며 표시명을 수동 원본으로 두지 않음.' if role=='formula' else COMMON_RULE
        if f in {'start_raw','end_raw'}:rule+=' 원문 날짜를 먼저 보존하고 파싱이 확실한 구성만 날짜필드로 구조화. 시작/종료연도 창작 금지.'
        if f.startswith('multiple_'):rule+=' TRUE/FALSE/미입력을 구별하고 기본 FALSE를 실제 판정으로 세지 않음.'
        ts=[target('C00',table,f,role,rule)]; fs=['C-02']; tests+=['T-012','T-042','T-043']
    elif code=='REG-V1' and sh=='02 국가 마스터':
        names=['sort_order','nation_id','neutral_name','alias_text','parent_nation_id','parent_name','existence_start_raw','existence_end_raw','governance_raw','setting_status','source_id','source_name']
        f=names[n]
        file,table=('C00','국가식별목록') if col in {'A','B','C','J','K','L'} else (('C00','개체별칭') if col=='D' else ('N10','국가목록원문속성'))
        role='formula' if f in {'parent_name','source_name'} else 'input'
        ts=[target(file,table,f,role,'국가목록의 중립명과 공식 국호 이력을 구별. parent/존속/통치 원문은 N10 소유로 보존하며 R50 영토관계로 자동 변환하지 않음.')]
        fs=['C-04'];tests+=['T-015']
    elif sh in {'90 출처','90_출처_레지스트리'}:
        fl=['source_id','source_title','source_kind','edition_raw','original_location','url','canon_status','modified_at_raw','notes'] if code=='REG-V1' else ['source_id','source_title','source_kind','url','edition_raw','canon_status','usage_scope','notes']
        ts=[target('C00','출처레지스트리',fl[n],'input','ID·URL·판본·시점·정본 상태 원문 보존. 양 파일에서 ID가 같아도 내용이 다르면 source_namespace로 분리하여 충돌표에 등록.')]
        fs=['C-03']; tests+=['T-012','T-014']
    elif sh in {'11 역사 사건','30_역사사건'}:
        if code=='REG-V1':fl=['event_id','event_title','event_type','start_raw','end_raw','date_precision','target_region_id','target_region_name','target_nation_id','target_nation_name','description','setting_status','source_id','source_name','notes']
        else:fl=['event_id','target_nation_id','route','era','year','month','day','event_title','description','setting_status','source_id','original_location']
        f=fl[n]; table='사건대상관계' if f.startswith('target_') else '수동사건'
        role='display' if f in {'target_region_name','target_nation_name'} else ('formula' if f=='source_name' else 'input')
        file='H90' if role=='display' else 'C00'
        ts=[target(file,'사건대상표시' if role=='display' else table,f,role,'대상 ID는 C00 사건대상관계에 보존하고 실제 존재/이름 조회는 H90에서 수행; C00에 R10/N10 import를 추가하지 않음.' if f.startswith('target_') else COMMON_RULE)]
        fs=['C-05','H-03','H-06'];tests+=['T-016','T-017','T-021','T-025','T-080']
    elif sh=='00_코드북':
        if n<8:
            f=['group_code','stored_code','display_name','definition','name_elun','name_other','usage_status','notes'][n]
            ts=[target('C00','코드북',f,'input','group_code+stored_code를 코드북 키로 보존. 서로 다른 그룹의 같은 문자열 코드는 합치지 않음.')]
        else:
            group=s['source_field']
            ts=[target('C00','코드북제공','stored_code','formula',f'코드북의 group_code={group!r} 유효 코드를 한 번 생성하여 소비파일 참조탭에서 재사용. legacy 그룹은 의미 매핑 확인 전 그룹명을 보존.',f'group_code={group}')]
        fs=['C-06'];tests+=['T-070','T-072','T-081']
    elif sh=='00_기준_메타':
        rules=META_REG if code=='REG-V1' else META_NAT
        for r,(file,table,f,role) in rules.items():
            vals=literal_rows[(code,sh)].get(r,{})
            selector=f'row={r};key={vals.get("A","")}'
            if col=='A':
                ts.append(target('C00','설정출처대응','source_key','archive','원래 설정 이름을 아래 값의 목적지와 연결하는 행별 대응 키로 보존.',selector))
            elif col=='C':
                ts.append(target('C00','설정출처대응','description_raw','archive','과거 탭 좌표가 포함된 설명 원문을 보존. 새 입력경로 설명은 H90 운영안내에서 별도 재작성하며 구판 설명을 작동 지시로 표시하지 않음.',selector))
            else:
                rule='원문 값을 이 설정의 근거 후보로 연결; 동일 기준의 중복 메타는 C00 정본 원본을 참조하며 독립 재입력처를 만들지 않음.'
                if role=='archive':rule='구판 탭·주소·용량·완료 문구를 이전 운영기록으로 보존. V2 연결식/용량/검증완료 값으로 재사용하지 않음.'
                if table=='조회조건':rule='기존 사용자 조회조건을 명시적 조건값으로 보존. 빈 기간/루트는 미입력이며 데이터 없음·0과 구별. point_year의 기존 수식 의존은 새 reference_year 기본값과 직접입력 구별로 재구현.'
                ts.append(target(file,table,f,role,rule,selector))
        fs=['C-01','C-07','H-01','H-09'];tests+=['T-019','T-020','T-022','T-068','T-077','T-078']
    elif sh=='40_행성대비_지표':
        fl=['era','year','nation_population','planet_population','population_ratio','nation_gdp','planet_gdp','gdp_ratio','controlled_land_area_value','planet_land_area_value','land_ratio','population_density','comparison_status']
        ts=[target('H90','행성국가비교',fl[n],'formula','N40/R20/N50/R60/R50/R70의 같은 루트·기년·기간·범위·인구정의·통화·가격기준을 대조한 뒤에만 비교. 부분 영토/다른 행성 전체/불완전 분모이면 수치는 공란+불가 사유.')]
        fs=['H-05'];tests+=['T-029','T-030','T-033','T-035','T-041','T-045','T-046']
    elif sh=='41_행성_연결':
        # Hidden compatibility relay is explicitly retired, but every observed column retains an exact target.
        if n<=23:f=ANNUAL_FIELDS[n];dataset='행성연간지표'
        elif n<=34:f=PROPERTY_FIELDS[n-24];dataset='행성물성'
        elif n==35:f='population_definition';dataset='인구정의'
        else:
            legacy=['sort_order','name_ko','name_roman_raw','name_elun_raw','region_category','region_id','hierarchy_group','parent_name_1_raw','parent_name_2_raw','region_rank_raw','detail_category','setting_status_raw','hex','color_chip','management_raw']
            f=legacy[n-36];dataset='지역참조'
        ts=[target('H90','퇴역연결보존',f,'archive',f'숨긴 41의 {dataset} 호환 출력/캐시를 source_column 포함 장부로 보존. literal로 내보내졌어도 새 수동 원본으로 등록하지 않음. V2 소비는 원 제공 파일을 직접 읽음.')]
        fs=['H-02'];tests+=['T-005','T-068','T-069']
    elif sh=='42_행성_기본속성_연결':
        ts=[target('H90','행성물성참조',PROPERTY_FIELDS[n],'display','R70.PUB_PLANET_PROPERTIES_V2 직접 제공표의 동일 기술 헤더를 읽음; V1 IMPORTRANGE/DUMMYFUNCTION 제거. 원문·계산·채택 상태를 함께 표시.')]
        fs=['H-02','H-05'];tests+=['T-005','T-038','T-068','T-072']
    elif sh=='43_지역_참조_연결':
        f=REGION_FIELDS[n]
        selector='all_data_rows' if col not in {'F','G','H','I'} else ('legacy_parent_slot=1' if col in {'F','G'} else 'legacy_parent_slot=2')
        rule='R10.PUB_REGIONS_V2의 헤더 이름으로 참조. 국가/지역 언어 열 순서를 원문 문자열과 대조; ID·표시명·색상 원문 보존.'
        if col in {'F','G','H','I'}:rule='두 부모 슬롯을 R10 지역관계의 두 관계행에 연결. H90 표시에서는 모든 부모를 행/목록으로 표시하며 부모 개수를 2로 고정하지 않음.'
        if col=='M':rule='원 HEX의 검증 후 V2 셀/조건부서식으로 재현. XLSX 이미지/SPARKLINE 캐시를 원문 색상 또는 입력값으로 삼지 않음.'
        ts=[target('H90','지역참조',f,'formula' if col=='M' else 'display',rule,selector)]
        fs=['H-02','H-04'];tests+=['T-005','T-026','T-027','T-037']
    elif sh=='44_행성_연간지표_연결':
        f='population_definition' if col=='Z' else ANNUAL_FIELDS[n]
        ts=[target('H90','행성연간참조',f,'display','인구는 R20.PUB_PLANET_POP_V2, 경제는 R60.PUB_PLANET_ECON_V2에서 metric_id로 분기. 지표 키 원필드·가격·정의·완전성·채택근거 동반. IFERROR로 연결실패 숨기지 않음.')]
        fs=['H-02','H-05'];tests+=['T-005','T-031','T-032','T-045','T-068','T-070']
    elif sh=='83_연방_통합연표':
        fl=['era','year','nation_name','emperor_terms','council_chair_terms','speaker_terms','lower_elections','upper_elections','population','gdp','gdp_class','real_growth','unclassified_gdp_growth','manual_events','executive_terms','party_leadership','empress_statuses','crown_statuses','first_rank_successors','nominated_successors','capital_constitution_changes','structure_status_changes']
        ts=[target('H90','연방통합연표',fl[n],'formula','각 소유 제공표를 route/era/year/subject로 결합. 동일 해 교체는 유효했던 모든 이력을 표시하고 연중 순서를 창작하지 않음. empty 원본은 자료 없음.')]
        fs=['H-01','H-03','H-07'];tests+=['T-018','T-019','T-020','T-021','T-025','T-065','T-067','T-077','T-079']
    elif sh=='89_변동_연표':
        fl=['subject_id','route','era','year','month','day','change_type','source_record_id','change_description','source_id']
        ts=[target('H90','통합변동연표',fl[n],'formula','분야별 시작/종료/선거 feed와 C00 수동사건을 출처 종류를 유지해 결합. exported literal/spill cache도 파생값이며 수동 사건에 되쓰기하지 않음.')]
        fs=['H-03'];tests+=['T-025','T-080']
    elif sh=='91_스키마_안내':
        f=['category','summary_raw','detail_raw','scope_and_caution_raw'][n]
        ts=[target('C00','구판운영기록',f,'archive','행2~39는 구판 설계/안내, 행41~74는 과거 시험·변경 기록. 2026-09-23 통과 문구를 V2 시험결과로 복제하지 않음; 모든 행은 snapshot_id·원래 row로 추적.')]
        ts.append(target('H90','기능대응안내',f.replace('_raw',''),'display','현재 owner/기능명세/실제 V2 주소가 생긴 뒤 새 안내를 작성; 옛 수식 좌표·완료 상태는 근거로만 연결.', 'legacy_function_reference_only'))
        fs=['H-09'];tests+=['T-068','T-078','T-084']
    elif sh in {'99_검증','98_검증_요약','99_검증_상세'}:
        if code=='REG-V1':fl=['check_name','target_reference','result_raw','action_rule_raw']
        elif sh=='98_검증_요약':fl=['check_group','passed_count','warning_count','error_count','excluded_count','run_status','detail_link','description']
        else:fl=['check_name','source_table','target_reference','result_raw','action_rule_raw','severity','source_link','source_row']
        f=fl[n]
        ts=[target('H90','이전검증기록',f,'archive','기존 정의·수식/캐시·설명과 원래 위치를 snapshot_id로 보존. 이전 결과를 새 run_id의 성공으로 가져오지 않음.')]
        result_f='outcome' if f=='result_raw' else ('action_rule' if f=='action_rule_raw' else f)
        table='검사요약' if sh=='98_검증_요약' else '검사결과'
        ts.append(target('H90',table,result_f,'validation','분야 소유 검사를 읽거나 H90 교차검사를 실제 실행 후 기록. 검사대상0은 no_subject, 연결 미확인은 unverified, 실행 전은 not_run. 오류 하위식 실패를 정상0 집계로 숨기지 않음.'))
        fs=['H-06','H-08'];tests+=['T-066','T-070','T-073','T-078','T-079']
    else:raise RuntimeError('Unhandled sheet '+sh)
    mapping(s,ts,transform,fs,tests)

# Specific schemas and key policies, including new technical structures required by the plan.
for table,pk,description in [
 ('공통기준',['standard_id'],'기준 식별자만 단일 등록; 개정·채택은 별도 이력'),
 ('기준개정이력',['revision_id'],'각 원문 후보 개정과 값·정밀도·출처·설정 상태를 보존'),
 ('문화분류',['culture_id'],'문화 정의와 상위관계; 국가 문화제도/주민 분포는 소유분야 참조'),
 ('종교분류',['religion_id'],'종교/종파 정의; 교단 기관과 구별'),
 ('언어분류',['language_id'],'언어/방언/문자 정의; 국가 언어지위와 별개'),
 ('집단분류',['group_id'],'종족/인종/민족 분류축과 원문 정의 보존'),
 ('자원분류',['resource_id'],'자원 정의와 기본 단위; 매장/생산 수치는 R70/R60'),
 ('특성사전',['trait_id'],'특성 정의와 표시 규칙; 실제 지역 부여는 R10'),
 ('지표사전',['metric_id'],'지표 대상·단위·분모·시점·가격·합산/결측 규칙'),
 ('국가식별목록',['nation_id'],'중립 목록명·소유분야·상태만; 공식 국호 원본은 N10'),
 ('개체별칭',['alias_id'],'원문 외국어명·표기역할·판본·대상 ID'),
 ('출처레지스트리',['source_namespace','source_id'],'같은 ID 문자열의 다른 출처를 덮어쓰지 않는 복합키'),
 ('출처별칭',['source_alias_id'],'통합된 출처도 모든 기존 위치/ID와의 대응을 유지'),
 ('수동사건',['event_id'],'수동 원문 사건; 자동 변동 피드 되쓰기 금지'),
 ('사건대상관계',['event_target_id'],'사건과 국가/지역/인물 한 연결당 한 행'),
 ('코드북',['group_code','stored_code'],'저장 코드·표시명·정의·사용상태의 단일 입력처'),
 ('코드북제공',['group_code','stored_code'],'현재 유효 코드 파생 제공표; 실제 칩 목록 동기화 대조 대상'),
 ('역법',['calendar_id','calendar_revision_id'],'C00에서만 역법값 관리; 천문 물리값은 R70'),
 ('기년대응',['era_mapping_id'],'구형/현행 기년을 분리하며 승인된 경계점만 기록'),
 ('루트정의',['route_id'],'A/B·구형 미분기 판본을 분리'),
 ('시간정책',['policy_id','policy_revision_id'],'정확 경계/연도정밀도/종료미상 규칙'),
 ('단위정의',['unit_id'],'원문 단위·통화 표기와 명시적 환산 규칙'),
 ('인구정의',['population_definition_id','definition_revision_id'],'등록인구와 대상 종족범위·근거·판본'),
 ('계산정책',['policy_id','policy_revision_id'],'직접/합산/부분합/비율값 채택 정책'),
 ('계산적합조건',['compatibility_rule_id'],'통화·가격·분모·정의·기년 일치 조건'),
 ('표기정책',['presentation_rule_id'],'언어 순서·HEX 표현과 원문 보존'),
 ('입력기본값',['default_id'],'원문에 명시된 기본값; 행 상태/판본 자동 확정 금지'),
 ('파일레지스트리',['file_code'],'16개 코드와 생성 후 실제 ID/폴더/제목/소유책임'),
 ('데이터셋레지스트리',['dataset_id'],'제공 owner/범위/키/열 스키마/릴리스/행수/확인시각'),
 ('ID네임스페이스',['namespace_id'],'기존 접두어/대소문자 보존, 신규발급·재실행 규칙'),
 ('범위레지스트리',['dataset_id'],'입력·계산·검증·제공·소비 범위와 확장 묶음'),
 ('드롭다운배포',['distribution_id'],'코드그룹과 소비 범위/네이티브 칩 배포·불일치 상태'),
 ('보존링크',['link_id'],'V1·과거 사본 주소; 운영 import 주소와 격리'),
 ('설정출처대응',['metadata_mapping_id'],'원 메타 행의 키·값 목적지·설명·판본'),
 ('구판운영기록',['legacy_record_id'],'이전 스키마·시험 문구의 snapshot별 보존 기록'),
 ('이관레코드관계',['migration_link_id'],'모든 legacy_locator와 대상레코드의 다대다 역추적'),
 ('데이터사전',['file_code','table_id','field_id'],'한국어 표시명·기술필드·형·값상태·검증·출처 의미'),
]:
    set_table('C00',table,pk,'derived' if table=='코드북제공' else ('archive' if table in {'구판운영기록','보존링크','설정출처대응'} else 'input'),description)

NEW_FIELDS={
 '기준개정이력':{'revision_id':'string','standard_id':'string','value_numeric':'decimal_nullable','value_text':'string_nullable','is_adopted':'boolean_or_unknown','adoption_reason':'string_nullable','effective_scope':'string_nullable','route':'string_nullable','era':'string_nullable','conflict_id':'string_nullable'},
 '지표사전':{'denominator_definition':'string_nullable','price_type':'string_nullable','currency':'string_nullable','missing_value_policy':'string_nullable','allowed_range':'string_nullable'},
 '국가식별목록':{'owner_file_code':'string','country_type':'string_nullable'},
 '개체별칭':{'entity_namespace':'string','entity_id':'string','language_raw':'string_nullable','alias_role':'string','edition_raw':'string_nullable','source_id':'string_nullable'},
 '출처별칭':{'original_namespace':'string','original_source_id':'string','canonical_namespace':'string','canonical_source_id':'string','merge_basis':'string'},
 '수동사건':{'start_era':'string_nullable','start_year':'integer_nullable','start_month':'integer_nullable','start_day':'integer_nullable','end_era':'string_nullable','end_year':'integer_nullable','end_month':'integer_nullable','end_day':'integer_nullable','route':'string_nullable','end_status':'string_nullable','date_precision':'string_nullable','related_event_id':'string_nullable'},
 '사건대상관계':{'event_id':'string','entity_namespace':'string','entity_id':'string','relation_role':'string_nullable'},
 '역법':{'months_per_year':'integer','days_per_month':'integer','days_per_year':'integer','civil_day_seconds':'decimal','correction_seconds':'decimal','correction_after_month':'integer','correction_after_day':'integer','correction_is_date':'boolean','source_standard_revision_ids':'string_array'},
 '기년대응':{'from_era':'string','from_year':'integer','to_era':'string','to_year':'integer','mapping_type':'string','approval_status':'string','source_id':'string_nullable'},
 '인구정의':{'inclusion_scope_raw':'string_nullable','registration_basis_raw':'string_nullable','source_standard_revision_ids':'string_array','setting_status':'string_nullable'},
 '파일레지스트리':{'spreadsheet_id':'string_nullable','title':'string','parent_id':'string_nullable','data_version':'string','schema_version':'string','release_id':'string_nullable','owner_scope':'string','creation_status':'string'},
 '데이터셋레지스트리':{'owner_file_code':'string','owner_spreadsheet_id':'string_nullable','schema_version':'string','release_id':'string_nullable','source_revision':'string_nullable','export_range':'string_nullable','primary_key_fields':'string_array','column_schema':'json','record_count':'integer_nullable','coverage':'string','route_policy':'string','era_policy':'string','status_policy':'string','validation_status':'string','checked_at':'string_nullable'},
 'ID네임스페이스':{'entity_type':'string','owner_file_code':'string','existing_format_raw':'string_nullable','generation_rule':'string','collision_rule':'string','reuse_rule':'string','immutable':'boolean'},
 '범위레지스트리':{'actual_row_count':'integer_nullable','input_end_row':'integer_nullable','calculation_end_row':'integer_nullable','validation_end_row':'integer_nullable','export_end_row':'integer_nullable','consumer_ranges':'json','growth_step':'integer_nullable','warning_threshold':'integer_nullable','expansion_procedure_id':'string'},
 '드롭다운배포':{'group_code':'string','consumer_file_code':'string','consumer_table':'string','consumer_field':'string','native_table_column_id':'string_nullable','validation_range':'string_nullable','distribution_revision':'string_nullable','last_checked_at':'string_nullable','sync_status':'string'},
 '설정출처대응':{'source_file_id':'string','source_sheet_id':'string','source_row':'integer','target_file_code':'string','target_table':'string','target_field':'string','value_raw':'json_scalar'},
 '이관레코드관계':{'legacy_locator':'string','source_snapshot_id':'string','source_record_id':'string_nullable','target_file_code':'string','target_table':'string','target_record_id':'string','operation':'string','transform_rule_id':'string','preservation_reason':'string_nullable'},
 '데이터사전':{'label_ko':'string','type':'string','required':'boolean','role':'string','definition':'string','validation_rule':'string_nullable','display_format':'string_nullable'},
}
for table,items in NEW_FIELDS.items():
    if not items:continue
    for f,kind in items.items():schema_field('C00',table,f,kind)

HUB_TABLES={
 '조회조건':(['view_id'],'control','H90 편집 가능 영역; 원자료 입력 아님'),
 '전체파일목차':(['file_code'],'display','실제 16개 파일의 링크·입력처·자료/연결/검증 상태'),
 '상태필터정의':(['filter_policy_id'],'control','작업/확정정본/보존 조회의 허용 설정상태 목록'),
 '지역참조':(['region_id','relation_display_key'],'display','R10 기준과 부모관계 표시'),
 '행성물성참조':(['planet_id','property_id','record_id'],'display','R70 원문/계산/채택 물성'),
 '행성연간참조':(['record_id'],'display','R20/R60 제공표의 정밀도·분모·상태 동반'),
 '행성국가비교':(['comparison_key'],'derived','적합조건을 만족한 수치만 계산'),
 '연방통합연표':(['view_id','route','era','year'],'derived','여러 소유분야의 연간 결과를 결합'),
 '통합변동연표':(['feed_item_id'],'derived','소유 원자료별 자동변동과 수동사건의 구별된 병합'),
 '지역상세조회':(['view_id','section_key','record_id'],'display','공간·소속·인구·사회·종교·경제·환경을 소유분야별로 조회'),
 '국가분야요약':(['view_id','section_key','record_id'],'display','N10 국호와 분야 소유기록 결합; 두번째 입력 원본 금지'),
 '황제재위결합':(['royal_record_id','term_id'],'derived','N30 신분/승계와 N20 황제 임기의 존재·기간 교차 조회'),
 '사건대상표시':(['event_id','event_target_id'],'display','C00 사건대상의 외부 명칭/존재 조회'),
 '검사정의':(['check_id'],'config','검사 소유 파일/실행조건/기대결과/심각도/범위'),
 '검사결과':(['run_id','check_id','result_id'],'validation','실행시점 결과; old snapshot 결과와 격리'),
 '검사요약':(['run_id','check_group'],'validation','정상/경고/오류/미실행/대상없음/연결미확인 집계'),
 '연결상태':(['consumer_dataset_id','provider_dataset_id'],'validation','헤더/파일 ID/권한/실제 확인시각/오래됨 상태'),
 '교차참조오류':(['run_id','check_id','record_id'],'validation','N30 term_id/C00 외부개체/R50 통치통계 등의 교차검사'),
 '결정대기':(['decision_id'],'display','기술결함·자료없음·세계관 결정 후보를 구별'),
 '이전검증기록':(['snapshot_id','source_sheet_id','source_row'],'archive','이전 검증 캐시·기록; 새 시험 통과와 분리'),
 '퇴역연결보존':(['snapshot_id','source_sheet_id','source_cell'],'archive','41 호환구조의 값/수식/좌표 계보 보존'),
 '운영안내':(['guide_id'],'display','실제 V2 입력원본 이동 링크와 범위확장/복구 절차'),
 '기능대응안내':(['function_id','source_function_ref'],'display','기존 기능에서 V2 위치/시험상태로 연결'),
}
for table,(pk,role,desc) in HUB_TABLES.items():set_table('H90',table,pk,role,desc)
HUB_EXTRA={
 '조회조건':{'nation_id':'string_nullable','region_id':'string_nullable','route_filter':'string_nullable','era_filter':'string_nullable','start_year':'integer_nullable','end_year':'integer_nullable','reference_year':'integer_nullable','point_year':'integer_nullable','point_month':'integer_nullable','point_day':'integer_nullable','filter_policy_id':'string','query_status':'string','party_filter_id':'string_nullable','person_filter_id':'string_nullable','emperor_filter_id':'string_nullable','page_size':'integer'},
 '상태필터정의':{'label_ko':'string','allowed_setting_statuses':'string_array','include_unknown_status':'boolean','purpose':'string'},
 '전체파일목차':{'spreadsheet_id':'string_nullable','title':'string','url':'string_nullable','input_table_links':'json','owner_scope':'string','implementation_status':'string','last_validation_status':'string'},
 '행성국가비교':{'route':'string','nation_id':'string','planet_id':'string','population_definition':'string_nullable','currency':'string_nullable','price_type':'string_nullable','price_base_era':'string_nullable','price_base_year':'integer_nullable','coverage_status':'string','missing_reason':'string_nullable'},
 '연방통합연표':{'nation_id':'string','status_filter':'string','coverage_status':'string','release_status':'string','source_record_links':'json'},
 '통합변동연표':{'feed_kind':'string','owner_file_code':'string','source_record_id':'string','date_precision':'string','end_status':'string_nullable','duplicate_group_id':'string_nullable','source_link':'string','source_release_id':'string','setting_status':'string'},
 '지역상세조회':{'region_id':'string','route':'string','era':'string','point_or_period':'json','owner_file_code':'string','dataset_id':'string','value_raw':'json','coverage_status':'string','source_link':'string'},
 '국가분야요약':{'nation_id':'string','route':'string','era':'string','point_or_period':'json','owner_file_code':'string','dataset_id':'string','value_raw':'json','coverage_status':'string','source_link':'string'},
 '황제재위결합':{'person_id':'string','route':'string','royal_start':'json','royal_end':'json','term_start':'json','term_end':'json','existence_status':'string','period_match_status':'string','precision_status':'string','n20_source_link':'string','n30_source_link':'string'},
 '검사정의':{'owner_file_code':'string','required_datasets':'json','test_ids':'string_array','predicate':'string','no_subject_rule':'string','severity_rule':'string','source_function_refs':'json'},
 '검사결과':{'outcome':'string','checked_at':'string_nullable','subject_count':'integer_nullable','observed_value':'json','expected_value':'json','evidence_location':'string_nullable','source_revision':'string_nullable','release_id':'string_nullable','technical_or_setting_issue':'string'},
 '검사요약':{'not_run_count':'integer','no_subject_count':'integer','unverified_connection_count':'integer','failed_dependency_count':'integer'},
 '연결상태':{'provider_file_code':'string','provider_spreadsheet_id':'string_nullable','import_range':'string_nullable','expected_schema':'string','observed_schema':'string_nullable','permission_status':'string','connection_status':'string','last_verified_at':'string_nullable','source_revision':'string_nullable','release_id':'string_nullable','freshness_status':'string'},
 '교차참조오류':{'owner_file_code':'string','target_namespace':'string','target_id':'string','error_kind':'string','scope_precision':'string','source_link':'string','checked_at':'string'},
 '결정대기':{'issue_category':'string','source_evidence':'json','candidate_values':'json','selected_value':'json_nullable','decision_status':'string','technical_status':'string','owner_file_code':'string'},
}
for table,items in HUB_EXTRA.items():
    for f,kind in items.items():schema_field('H90',table,f,kind)

# Every data/archival table carries immutable lineage; displays carry source links.
for (file,table),t in list(tables.items()):
    if file=='C00' and t['table_role'] in {'input','archive'}:
        for f,k in [('legacy_locator','string_nullable'),('source_snapshot_id','string_nullable'),('setting_status','string_nullable')]:schema_field(file,table,f,k)
    if file=='H90' and t['table_role'] in {'display','derived','validation'}:
        for f,k in [('source_links','json'),('data_status','string'),('schema_version','string'),('release_id','string_nullable')]:schema_field(file,table,f,k)

function('C-01','공통 기준·개정·채택 분리','C00',['C00.기준개정이력','C00.설정출처대응'],['공통기준','기준개정이력'],[
 '기존 standard_id는 유지하고 원본 행/판본별 revision_id를 이관레지스트리에 고정 발급한다.',
 '동일 ID의 초기 검토/후속 초안 모두 보존한다. is_adopted는 확인된 선택 근거가 있을 때만 설정한다.',
 '메타의 중복 표현은 원문 출처대응으로 연결하며 같은 사실의 별도 입력값을 만들지 않는다.'],
 'T-009,T-010,T-012,T-013,T-014','미채택/충돌은 결정대기. 기준 검증 정상과 세계관 확정을 분리.', ['REG 00 공통 기준','REG/NAT 00_기준_메타'])
function('C-02','분류·지표 단일 원본','C00',['C00.문화분류','C00.종교분류','C00.언어분류','C00.집단분류','C00.자원분류','C00.특성사전','C00.지표사전'],['PUB_CLASSIFICATIONS_V2','PUB_METRICS_V2'],[
 '기존 ID·상위관계·기간 원문·중복정체성 허용·상태를 보존하며 분류축을 섞지 않는다.',
 '부모·출처 표시명은 C00 내부에서 조회한다. 분류 정의만 제공하고 실제 지역 분포/자원 수치를 입력하지 않는다.',
 '지표마다 단위·분모·시점/기간·가격유형·합산방식/결측을 계약으로 제공한다.'],
 'T-004,T-009,T-014,T-041,T-042,T-043,T-049','허용 정의/기간 미정이면 자동 합계 및 정본 승격을 하지 않는다.')
function('C-03','출처·이관 계보 유지','C00',['REG 90 출처','NAT 90_출처_레지스트리'],['출처레지스트리','출처별칭','이관레코드관계'],[
 'source_namespace+source_id로 먼저 식별하고 같은 문자열 충돌을 대조한다.',
 '동일 문서라고 확인된 경우에만 대표 출처를 선택하고 나머지 ID·판본·URL·legacy_locator는 별칭관계로 유지한다.',
 '필드 분리/통합은 1원문:N대상 혹은 N원문:1대상 계보를 기록한다.'],
 'T-004,T-009,T-010,T-012,T-013','출처 부족은 미확인. URL 미접근을 자료 없음이나 정상으로 치환하지 않음.')
function('C-04','국가 목록·별칭·상세 속성 분리','C00',['REG 02 국가 마스터','N10.국가기본','N10.국호이력'],['국가식별목록','개체별칭','N10.국가목록원문속성'],[
 '중립 목록명/ID만 C00 원본. 공식 국호/존속/통치 원문은 N10로 분리한다.',
 '구형 외국어 표기는 개체별칭에서 역할·판본·원문을 유지하고 최신 국호로 덮어쓰지 않는다.',
 'parent_nation_id와 거버넌스 문장을 영토 통치관계로 추정하지 않는다. N10 담당과 범위를 확인한다.'],
 'T-004,T-009,T-015,T-036','외국 국가 상세속성 포함 범위는 검토 필요. 사실 삭제 없이 sourcefield 목적지는 N10 보존속성으로 명시.')
function('C-05','수동사건과 사건 대상','C00',['REG 11 역사 사건','NAT 30_역사사건'],['수동사건','사건대상관계','PUB_MANUAL_EVENTS_V2'],[
 '사건 ID와 원문 기간·날짜 정밀도·설명·출처·상태를 보존한다.',
 '국가/지역/인물 대상은 연결 1건1행. 외부 이름과 존재 검사는 H90에 위임한다.',
 'REG 자유서술 날짜는 파싱근거 있는 부분만 구조화하고 미상 월일을 보충하지 않는다.'],
 'T-009,T-013,T-016,T-017,T-021,T-025,T-080','C00는 외부 운영파일 import를 하지 않으며 H90 결과도 역으로 가져오지 않는다.')
function('C-06','코드북·드롭다운 일치','C00',['C00.코드북'],['코드북제공','드롭다운배포'],[
 'group_code+stored_code를 단일 원본으로 하고 표시명/언어/상태를 함께 제공한다.',
 '기존 J:BB 각 목록을 해당 group_code 선택으로 재현하며 60개 칩 열의 별도 선택지를 목록화해 실제 배포/대조한다.',
 '코드 추가 후 범위 기반 드롭다운과 네이티브 칩 모두 동일하거나 미동기화 경고를 보여준다.'],
 'T-072,T-073,T-081,T-082','문서상의 60개 칩 수는 이전 관측. 현재 온라인 inventory의 칩 정의와 실제 개수를 확인해야 구현 완료.')
function('C-07','역법·기년·정밀도 공통 규약','C00',['C00.기준개정이력','REG/NAT 00_기준_메타','R70 행성기본값의 역법 필드'],['역법','기년대응','시간정책'],[
 'C00에서 48개월·30일·1440일·civil 86400초 및 24월30일 뒤 432초 보정구간 근거를 관리하고 R70는 참조한다.',
 '세계관 DATE를 서력 DATE함수에 넣지 않는다. era/year/month/day/precision과 필요시 calendar_phase/correction_second로 표현한다.',
 '정확 경계는 [start,end), 연도 종료는 그해 포함, 종료미상은 시작연도만, 지속중은 조회기준까지 적용한다.',
 '구형 제2기와 현행 제2기 대응은 승인된 경계점 관계만 보존하고 연도 비례축약/전구간 자동변환하지 않는다.'],
 'T-016,T-017,T-018,T-019,T-020,T-021,T-022,T-023,T-024,T-025','기년 사이 절대 대응 미확정은 계산 보류. 0년을 결측으로 처리하지 않음.')

function('H-01','조회조건과 연간·시점 필터','H90',['C00.시간정책','C00.루트정의','H90.조회조건','H90.상태필터정의'],['조회조건','연방통합연표','지역상세조회','국가분야요약'],[
 '조회 대상/루트/기년/기간/시점/상태정책을 명시적으로 선택한다. 루트/기간 미입력은 query_incomplete로 표시한다.',
 '작업 조회는 비폐기 원문 상태를 보존, 확정·정본 조회는 허용 상태 목록을 명시, 보존 조회는 폐기/구버전도 포함한다.',
 '상태 공란을 확정으로 취급하지 않고 조회 필터가 원본의 상태를 바꾸지 않는다.',
 '연도 창을 페이지 단위로 제공하되 창 밖 원자료를 삭제하지 않는다. 연도/시점 날짜의 정밀도를 화면에 표시한다.'],
 'T-019,T-020,T-021,T-023,T-025,T-067,T-077,T-078','빈 조건·자료 없음·연결 실패·범위 밖을 별개 표시.')
function('H-02','V2 제공표·연결 계약·퇴역 호환','H90',['C00.데이터셋레지스트리','R10.PUB_REGIONS_V2','R70.PUB_PLANET_PROPERTIES_V2','R20.PUB_PLANET_POP_V2','R60.PUB_PLANET_ECON_V2'],['지역참조','행성물성참조','행성연간참조','연결상태','퇴역연결보존'],[
 'NAT41 호환 릴레이를 운영에서 퇴역하고 42/43/44 기능을 해당 원 소유 V2 제공표로 직접 연결한다.',
 '각 외부표를 참조 탭에 한번만 받아 재사용한다. 필수 헤더/키/스키마/릴리스/row count를 검증한 후 소비한다.',
 '권한미허용·원본미접근·범위없음·헤더불일치·갱신대기·오래된 스냅샷을 구별한다.',
 '실제 읽기 검증시각만 last_verified_at로 기록한다. NOW만 바뀐 경우 수신완료로 표시하지 않는다.',
 'N30는 N20 임기 import 금지. C00에는 외부 import 없음. H90를 다른 소유파일이 import하지 않는다.'],
 'T-005,T-068,T-069,T-070,T-071,T-072,T-079,T-083','V1 보존주소는 링크 예외목록에만 두며 운영 import 0개. 캐시를 새 직접값으로 삼지 않음.')
function('H-03','수동·자동 변동 및 연방 통합연표','H90',['C00.PUB_MANUAL_EVENTS_V2','N10.국호·수도·헌정 feed','N20.공직·선거·정당·기관 feed','N30.황실·친족·승계 feed','N40.국가인구 제공','N50.국가경제 제공','R50.영토변동 feed'],['통합변동연표','연방통합연표'],[
 '분야 feed에 owner/source_record_id/feed_kind/route/era/date_precision/source_link를 포함하고 전용 파생표로 결합한다.',
 '같은 사건의 수동기록과 자동변동은 duplicate_group_id로 연관만 표시하고 원본 두 근거를 삭제하지 않는다.',
 '월일 미상 기록의 같은 해 내부 순서를 확정하지 않고 연간 묶음으로 표시한다.',
 '83의 A:V 정치·선거·인구·경제·사건·황실·수도·헌정 기능을 모두 source필드별 대조한다.'],
 'T-019,T-020,T-021,T-025,T-051,T-061,T-067,T-080','조회 결과를 C00 수동사건이나 분야 입력표에 되쓰기하지 않음.')
function('H-04','지역 상세·국가 분야 요약','H90',['R10.지역목록·관계·시설·노선','R20.인구관측','R30.사회문화','R40.종교분포','R50.지역국가관계','R60.경제산업','R70.환경자원','N10~N70 분야 제공표'],['지역상세조회','국가분야요약'],[
 '대상과 기간에 맞는 분야별 원본을 읽고 데이터/완전성/원본 이동링크를 함께 표시한다.',
 '국가 영토는 R50 조회로만 제공하고 H90에서 입력하지 않는다.',
 '복수 부모관계와 성계·행성 상위 계층을 모두 유지하고 지역ID 기준 중복표시/중복합산을 분리한다.',
 '빈 분야는 자료 없음과 해당 소유파일 입력링크를 제공한다.'],
 'T-008,T-026,T-027,T-028,T-034,T-035,T-036,T-037,T-040,T-084','최소 스키마가 있다고 실제 사회/문화/교무 자료가 있다고 표시하지 않는다.')
function('H-05','행성·국가 비율·집계 적합성','H90',['N40.국가인구','R20.행성인구','N50.국가경제','R60.행성경제','R50.통치범위','R70.행성물성','C00.지표사전'],['행성국가비교'],[
 'ID 대상 집합·루트·기년·시점·자료정의·종족범위·통화·가격기준·분모를 확인한다.',
 '완전 비중첩 집합에만 총계. 부모+자식/복수 상위지역은 같은 하위ID가 중복되지 않도록 선택집합을 검증한다.',
 '부분합은 partial_sum과 누락ID 목록으로 표시하고 전체 채택값을 만들지 않는다.',
 '직접/산출/채택/차이/근거를 분리한다. 실제0은 보존하되 누락·미상·권한오류를 0으로 바꾸지 않는다.',
 '면적비로 인구/GDP를 배분하지 않으며 국가 전체가 여러 행성이면 단일행성 비교를 보류한다.',
 '비율은 0~1 저장, 성장률은 직전연도 존재·0분모·동일기준을 검사한 후 산출한다.'],
 'T-027,T-028,T-029,T-030,T-031,T-032,T-033,T-035,T-041,T-042,T-043,T-044,T-045,T-046,T-047,T-048,T-050','comparison_status와 missing_reason를 노출하며 IFERROR(...,0) 금지.')
function('H-06','외부 ID·기간 교차검증','H90',['C00.사건대상관계','N20.공직임기','N30.인물·황실·승계','R10.지역','R50.지역국가관계','R20/N40 인구 범위'],['교차참조오류','검사결과','황제재위결합','사건대상표시'],[
 'N30의 외부 term_id가 N20에 존재하는지 검사하고 황제직/인물/루트/기간 적합성을 구별한다.',
 '정확 경계에는 [start,end) 규칙을 적용하고 연도정밀도/미상 종료는 불확실 경고로 남긴다.',
 'N20 인물은 N30 존재 검사, C00 사건의 외부 대상은 해당 소유마스터 존재 검사, R50 통치범위와 통계 대상 집합은 H90에서 대조한다.',
 '외부파일 미접근을 참조ID 미존재와 구별한다. N30에는 통합 검증 대상 상태만 로컬 표시한다.'],
 'T-011,T-018,T-021,T-023,T-029,T-034,T-036,T-065,T-066,T-069,T-070','존재하지 않음과 미검증을 분리. 신분/친족으로 승계권을 자동 판정하지 않음.')
function('H-07','황제 재위·황실·승계 결합','H90',['N20.공직임기','N30.황실신분','N30.황위계승','N10.수도이력','N10.헌정국체이력'],['황제재위결합','연방통합연표'],[
 '황제 재위 원본은 N20, 신분/계승권/순위/지명 원본은 N30으로 별개 유지한다.',
 'NAT86 등 분야 조회에서 요청한 황제·수도·헌정 결합은 H90에서만 수행한다.',
 '연간 조회는 연중 각 이력, 시점 조회는 정확 기준일 유효 구간을 표시하고 박탈/포기/복권 과거상태를 유지한다.'],
 'T-018,T-020,T-021,T-062,T-063,T-064,T-065,T-066,T-067','N30->N20->N30 순환 import를 만들지 않음.')
function('H-08','검사 레지스트리·이전 결과 격리','H90',['각 소유분야 검증제공','C00.데이터셋레지스트리','H90.교차참조오류'],['검사정의','검사결과','검사요약','이전검증기록'],[
 '기존 검사 정의·조치·원자료 이동 기능을 검사정의에 등록하고 분야검사와 교차검사의 실행책임을 나눈다.',
 '이전 결과/통과문구/저장캐시는 snapshot_id가 있는 이전검증기록으로만 보존한다.',
 '새 결과는 run_id/check_id/subject_count/actual/expected/checked_at/evidence/source_revision을 함께 기록한다.',
 '대상0=no_subject, 미실행=not_run, 연결미확인=unverified, 오류=error, 경고=warning을 독립 집계한다.',
 'T002의 현재 별도 인수시험 통과1/나머지83 미실행을 과거 V1 검사와 섞지 않는다.'],
 'T-002,T-005,T-066,T-070,T-073,T-076,T-078,T-079','검증사본 파일·실제 결과가 없으면 새 통과로 기록하지 않는다.')
function('H-09','파일 목차·입력동선·확장·복구','H90',['C00.파일레지스트리','C00.범위레지스트리','C00.이관레코드관계','H90.결정대기'],['전체파일목차','운영안내','기능대응안내'],[
 '실제 생성 후 16개 코드/ID/파일링크와 유일한 입력표로 바로 이동한다. 현재는 파일 미생성으로 명시한다.',
 '새 인물=N30, 모든 공직임기=N20, 영토관계=R50 등 작업별 입력처를 표시한다.',
 '범위확장은 입력/기본값/드롭다운/계산/검증/제공/소비/행수 계약을 하나의 배치로 갱신하고 마지막 준비행+1을 시험한다.',
 '복구 시 V2 신규입력 차분을 보존하고 정상 릴리스 복사본으로 복구한다. V1 역쓰기/원본 공유권한 변경 금지.',
 '구판 좌표·백업주소는 보존구역에 남기고 작동하는 V2 링크와 명확히 구별한다.'],
 'T-001,T-002,T-010,T-068,T-073,T-074,T-075,T-076,T-082,T-084','H90 화면 편집 허용은 조회·필터·실행설정뿐이며 원자료 입력 버튼을 가장하지 않는다.')

issue('CH-001','첨부 기준 XLSX 부재','PH0 증거 게이트','05 구조JSON과 온라인 snapshot만 존재; 셀값 전체 diff 미검증','사용자에게 묻고 있는 온라인 snapshot 기준 예외 여부를 기다림. 승인이 없으면 PH2 착수/PH0완료 금지.')
issue('CH-002','REG 국가마스터의 비연방 상세속성 소유','owner 범위 검토','REG02 E:I 부모/존속/통치 원문 필드 존재','N10 담당과 국가목록원문속성 스키마를 병합 검토; C00는 중립식별/별칭 유지, R50 관계 추정 금지.',[x['source_field_id'] for x in fields if x['source_file_code']=='REG-V1' and x['source_sheet_name']=='02 국가 마스터' and x['source_column'] in {'E','F','G','H','I'}])
issue('CH-003','동일 기준 ID의 복수 개정 및 축 항목 의미','세계관 결정','REG00 std.map 4종 중복과 std.map.crs.axis의 실행시점 원문 관측은 live_decision_observations와 연결','revision_id별 모두 보존하고 채택상태/의미는 사용자 결정 전 미해결. 마지막 행 자동 채택 금지.')
issue('CH-004','서술 날짜·원문 단위·기년 대응 파싱','구조화 한계','C00 분류/REG사건의 시작종료와 메타의 서술 규칙','raw를 보존하고 날짜/단위가 명확한 부분만 구조화. 자동추론 확대 금지.')
issue('CH-005','원본/파생 역할 오인 방지','명세 보정','NAT41/43 M/89 spill 결과가 literal이라 초안 source_role은 input일 수 있음','새 target role을 archive/display/formula로 구별. source_role_original은 원 관측값 유지.')
issue('CH-006','코드북 legacy 그룹과 네이티브 칩 동기화','구현 전 계약','NAT00코드북 AQ:BB legacy 그룹 및 91안내의 구형 칩60열 기록','현재 네이티브 inventory와 각 소비필드 의미를 매칭한 뒤 배포; 과거60개를 현재 수량으로 확정하지 않음.')
issue('CH-007','제공표 이름과 외부분야 스키마 병합','PH1 통합 검토','N20/N30/R50 등 다른 담당 원본을 H90 기능 required_datasets로 참조','각 담당 schema의 table_id와 keys를 병합 대조하고 제공범위/필수헤더 확정 후 PH1 종료. 현재 function dataset이 구체 ID로 해결됐다고 주장하지 않음.')
issue('CH-008','V1 호환시트 미확인 헤더','보존 메타 해석','NAT41 AM/AN/AR/AS/AT/AV/AX 일부 source header 미확인','열위치 기반 보존필드를 지정했으나 실제 의미는 원 제공표 열과 대조 필요. 운영 제공표에서는 R10 정식 기술헤더로 읽음.',[x['source_field_id'] for x in fields if x['source_sheet_name']=='41_행성_연결' and x['header_review_required']=='true'])
issue('CH-009','REG 합산완료의 단순 개수 동치 문구','운영규칙 재구현','REG00메타 10행 원문 유효행수=고유지역수=대상지역수','문구 원문은 보존하되 V2는 실제 대상ID 집합도 일치 검사. 동수지만 다른 ID인 T029를 필수로 연결.')

EXPORTS=[
 ('PUB_STANDARDS_V2','C00',['공통기준','기준개정이력'],['standard_id','revision_id'],['standard_id','revision_id','value_raw','unit_format','setting_status','is_adopted','source_id']),
 ('PUB_CODEBOOK_V2','C00',['코드북'],['group_code','stored_code'],['group_code','stored_code','display_name','definition','usage_status']),
 ('PUB_SOURCES_V2','C00',['출처레지스트리'],['source_namespace','source_id'],['source_namespace','source_id','source_title','url','edition_raw','canon_status']),
 ('PUB_CLASSIFICATIONS_V2','C00',['문화분류','종교분류','언어분류','집단분류','자원분류','특성사전'],['entity_namespace','entity_id'],['entity_namespace','entity_id','parent_id','name_ko','name_original','setting_status','source_id']),
 ('PUB_METRICS_V2','C00',['지표사전'],['metric_id'],['metric_id','subject_type','unit','denominator_definition','period_basis','price_type','aggregation_method','setting_status']),
 ('PUB_NATIONS_V2','C00',['국가식별목록'],['nation_id'],['nation_id','neutral_name','owner_file_code','setting_status']),
 ('PUB_CALENDAR_V2','C00',['역법','기년대응','시간정책'],['record_kind','record_id'],['record_kind','record_id','calendar_id','calendar_revision_id','route','era','value_raw','setting_status']),
 ('PUB_MANUAL_EVENTS_V2','C00',['수동사건','사건대상관계'],['event_id','event_target_id'],['event_id','event_target_id','entity_namespace','entity_id','route','era','year','month','day','date_precision','event_title','setting_status','source_id']),
]
export_contracts=[{'dataset_id':i,'owner_file_code':owner,'source_tables':tabs,'primary_key_fields':pk,'required_headers':headers,
 'owner_spreadsheet_id':None,'export_range':None,'schema_version':'V2-draft-common-hub-1','release_id':None,
 'implementation_status':'미실행','contract_status':'초안·실제표/헤더검증 대기','range_policy':'닫힌 활성 범위+예비입력 행. 확장 시 입력/계산/검증/제공/소비 동시 갱신',
 'state_fields_required':['value_status','setting_status','coverage','source_revision','release_id','checked_at'],
 'no_data_policy':'헤더 유지·record_count=0·자료없음. 연결오류를0행 성공으로 오인하지 않음'} for i,owner,tabs,pk,headers in EXPORTS]

set_table('C00','대상목록',['scope_id'],'input','국가·행성 대상의 ID와 소유분야만 등록. 지역ID와 동일성은 명시 관계 없이는 가정하지 않음.')
for f,k in {'scope_type':'string','neutral_name':'string_nullable','owner_file_code':'string','related_region_id':'string_nullable','identity_relation_status':'string'}.items():schema_field('C00','대상목록',f,k)
for (file,table),t in list(tables.items()):
    if t['table_role']=='mixed_until_finalized':
        set_table(file,table,['record_id'] if table=='국가목록원문속성' else ['config_id'],'external_owner_contract','담당 source 메타/속성의 의미상 소유파일. 해당 분야 명세와 병합 검토할 제안 계약.')
for f,k in {'original_property_id':'string_nullable','planet_scope_id':'string_nullable','original_location':'string_nullable','generation_method':'string_nullable','notes':'string_nullable'}.items():schema_field('C00','기준개정이력',f,k)
integration_contracts=[{
 'contract_id':'REG-C00-CALENDAR-CANDIDATE',
 'status':'병합 적용 규칙 명시 · 원문 이관/채택 미실행',
 'upstream_spec':'region_schema.json / region_field_spec.csv',
 'upstream_target':'C00.공통기준_개정후보',
 'canonical_target':'C00.기준개정이력',
 'temporary_table_rule':'공통기준_개정후보는 이관 배치의 준비 이름이다. 독립 운영 입력표로 만들지 않고 아래 대응으로 기준개정이력에 기록한 후 역법표는 채택 근거가 있는 개정에서 파생한다.',
 'field_map':{'record_id':'revision_id','planet_scope_id':'planet_scope_id','property_id':'original_property_id','property_name':'item_name','value_numeric':'value_numeric','value_text':'value_text','unit':'unit_format','generation_method':'generation_method','setting_status':'setting_status','source_id':'source_id','original_location':'original_location','notes':'notes','legacy_locator':'legacy_locator','source_snapshot_id':'source_snapshot_id'},
 'property_to_calendar_field':{'civil_day':'civil_day_seconds','civil_year_days':'days_per_year','year_correction':'correction_seconds','months_per_year':'months_per_year','days_per_month':'days_per_month'},
 'standard_id_rule':'original_property_id를 삭제/개명하지 않는다. C00 기존 standard_id와 의미가 일치하는지 대조한 연결표를 작성하고 둘의 기존 ID를 모두 보존한다. std.calendar.day/year_length 등과 같은 말이라는 이유로 원문 후보를 덮어쓰지 않는다.',
 'unit_rule':'원문 단위와 수치를 함께 보존. civil_day->seconds 등은 원문 단위가 확인되고 환산식이 명시된 경우만 적용. 단위 미확정이면 정규 수치 채택 보류.',
 'candidate_adoption':'역법의 동일 필드를 별도 수동 입력하지 않는다. 채택된 revision_id 집합에서 계산·조회하는 단일 운영 정의로 제공하고 근거 없는 값은 채우지 않음.',
 'remaining_review':['역법 5개 원문 수치/단위·기존 기준개정과 행별 대응','원문 src와 revision 연결','명세 병합 시 region targets_json의 준비 이름을 canonical 대상/field map으로 해석'],
 'test_ids':['T-004','T-009','T-013','T-014','T-016','T-022','T-024']
}]
tables[('C00','역법')]['table_role']='derived_from_adopted_revisions'
tables[('C00','역법')]['single_input_rule']='기준개정이력에서 채택된 역법 개정으로 파생. 역법표 별도 수동 값 입력 금지.'
issue('CH-010','R70 유래 역법 후보표 병합','PH1 계약 병합','지역 담당의 C00.공통기준_개정후보 5속성','integration_contracts.REG-C00-CALENDAR-CANDIDATE의 필드 대응을 적용하고 동일 내용 개정/원문 ID를 대조. 독립 이중 입력표를 만들지 않음.')

for x in spec:
    for t in json.loads(x['targets_json']):
        ff=tables[(t['file_code'],t['table'])]['fields'][t['field']]
        ff.setdefault('label_ko',x['source_field'])
for t in tables.values():
    for ff in t['fields'].values():ff.setdefault('label_ko',ff.get('description') or ff['field_id'])

for contract in export_contracts:
    contract['technical_envelope']='모든 제공행 또는 별도 제공메타에 owner_file_code, schema_version, release_id, source_revision, validation_status, checked_at 포함'
    if contract['dataset_id']=='PUB_CLASSIFICATIONS_V2':
        contract['union_field_map']={'문화분류':{'entity_id':'culture_id','parent_id':'parent_culture_id'},'종교분류':{'entity_id':'religion_id','parent_id':'parent_religion_id'},'언어분류':{'entity_id':'language_id','parent_id':'parent_language_id'},'집단분류':{'entity_id':'group_id','parent_id':'parent_group_id'},'자원분류':{'entity_id':'resource_id','name_ko':'resource_name','parent_id':None},'특성사전':{'entity_id':'trait_id','name_ko':'trait_name','parent_id':None}}
        contract['normalization_rule']='entity_namespace는 소유 분류표의 종류로 명시. 원 ID를 바꾸지 않고 parent 없는 유형은 공란 유지. 자원/특성의 name_original 없음은 자료없음이며 번역 생성 금지.'
    if contract['dataset_id']=='PUB_CALENDAR_V2':
        contract['record_kinds']=['calendar_definition','era_boundary_mapping','time_policy']
        contract['normalization_rule']='각 record_kind가 고유 record_id와 원본 키를 함께 제공. 역법별 numeric fields/기년대응 pair/정책원문을 column_schema에서 구별하고 한 value_raw로 의미를 합치지 않음.'

# Explicit typed export contracts. Each source binding names a real field above;
# constants below are technical row kinds/status policies, never invented setting values.
for t in ['기준개정이력','문화분류','종교분류','언어분류','집단분류','자원분류','특성사전','지표사전','수동사건','국가식별목록']:
    schema_field('C00',t,'source_namespace','string_nullable')
schema_field('C00','공통기준','current_revision_id','string_nullable')
schema_field('C00','기준개정이력','value_status','string_nullable')
schema_field('C00','시간정책','policy_name','string_nullable')
schema_field('C00','시간정책','policy_raw','string_nullable')
schema_field('C00','기년대응','era_edition','string_nullable')
schema_field('C00','역법','calendar_name','string_nullable')
schema_field('C00','역법','setting_status','string_nullable')
schema_field('C00','역법','source_id','string_nullable')
schema_field('C00','역법','source_namespace','string_nullable')
schema_field('C00','기년대응','setting_status','string_nullable')
schema_field('C00','기년대응','source_namespace','string_nullable')
schema_field('C00','시간정책','source_id','string_nullable')
schema_field('C00','시간정책','source_namespace','string_nullable')
schema_field('C00','수동사건','source_namespace','string_nullable')
schema_field('C00','사건대상관계','setting_status','string_nullable')

def bind(table,field,when=None):
    assert ('C00',table) in tables and field in tables[('C00',table)]['fields'], (table,field)
    return {'file_code':'C00','table_id':table,'field_id':field,**({'when':when} if when else {})}
def cdef(name,kind,required=False,bindings=None,rule=None,constants=None):
    return {'field_id':name,'header':name,'type':kind,'required':required,'source_bindings':bindings or [],
            'projection_rule':rule or '원문 의미와 형을 보존한 직접 투영. 입력 값의 실제 0을 유지.',
            **({'constants_by_record_kind':constants} if constants is not None else {})}
def direct(table,names,required=()):
    return [cdef(n,tables[('C00',table)]['fields'][n]['type'],n in required,[bind(table,n)]) for n in names]

typed={}
typed['PUB_STANDARDS_V2']=direct('기준개정이력',[
 'standard_id','revision_id','domain','item_name','value_raw','value_numeric','value_text','unit_format','description','setting_status','value_status','is_adopted','adoption_reason','effective_scope','route','era','conflict_id','source_namespace','source_id','original_property_id','planet_scope_id','original_location'],['standard_id','revision_id'])
typed['PUB_CODEBOOK_V2']=direct('코드북',['group_code','stored_code','display_name','definition','name_elun','name_other','usage_status','notes'],['group_code','stored_code'])
typed['PUB_SOURCES_V2']=direct('출처레지스트리',['source_namespace','source_id','source_title','source_kind','edition_raw','original_location','url','canon_status','modified_at_raw','usage_scope','notes'],['source_namespace','source_id'])
typed['PUB_METRICS_V2']=direct('지표사전',['metric_id','metric_name','subject_type','definition','unit','period_basis','aggregation_method','calculation_rule_raw','allowed_value_and_missing_rule','denominator_definition','price_type','currency','missing_value_policy','allowed_range','setting_status','source_namespace','source_id'],['metric_id'])
typed['PUB_NATIONS_V2']=direct('국가식별목록',['nation_id','neutral_name','sort_order','owner_file_code','setting_status','source_namespace','source_id'],['nation_id'])

class_specs={
 'culture':('문화분류','culture_id','parent_culture_id','name_ko','name_original'),
 'religion':('종교분류','religion_id','parent_religion_id','name_ko','name_original'),
 'language':('언어분류','language_id','parent_language_id','name_ko','name_original'),
 'group':('집단분류','group_id','parent_group_id','name_ko','name_original'),
 'resource':('자원분류','resource_id',None,'resource_name',None),
 'trait':('특성사전','trait_id',None,'trait_name',None),
}
cols=[cdef('entity_namespace','string',True,rule='소유 분류표별 고정 기술 구분값. 원문 개체ID를 재작성하지 않음.',constants={k:k for k in class_specs})]
for out,index in [('entity_id',1),('parent_id',2),('name_ko',3),('name_original',4)]:
    cols.append(cdef(out,'string_nullable',out=='entity_id',[bind(v[0],v[index],k) for k,v in class_specs.items() if v[index]],'record_kind별 같은 의미 원문필드를 투영. 해당 필드가 없는 자원/특성 유형은 공란·해당없음이며 추정 생성 금지.'))
for out in ['definition','start_raw','end_raw','classification_axis','script_system','multiple_membership_allowed','multiple_faith_allowed','multiple_identity_allowed','default_unit','resource_category','trait_category','icon_reference','effect_kind','setting_status','source_namespace','source_id']:
    bs=[bind(v[0],out,k) for k,v in class_specs.items() if out in tables[('C00',v[0])]['fields']]
    kind='boolean_or_unknown' if out.endswith('_allowed') else 'string_nullable'
    cols.append(cdef(out,kind,False,bs,'유형별 정의/정밀도/분류축을 유지. 다른 유형에 필드가 없으면 공란; 서로 다른 축의 값을 대체하지 않음.'))
typed['PUB_CLASSIFICATIONS_V2']=cols

calendar_tables={'calendar_definition':'역법','era_boundary_mapping':'기년대응','time_policy':'시간정책'}
cal=[cdef('record_kind','string',True,rule='union discriminator',constants={k:k for k in calendar_tables}),
     cdef('record_id','string',True,[bind('역법','calendar_id','calendar_definition'),bind('역법','calendar_revision_id','calendar_definition'),bind('기년대응','era_mapping_id','era_boundary_mapping'),bind('시간정책','policy_id','time_policy'),bind('시간정책','policy_revision_id','time_policy')],
          'calendar_definition은 canonical JSON([calendar_id,calendar_revision_id]), era_boundary_mapping은 era_mapping_id 원문, time_policy는 canonical JSON([policy_id,policy_revision_id]). 원 키 필드를 별도로 유지하며 행번호로 발급하지 않음.')]
cal_fields={
 'calendar_definition':['calendar_id','calendar_revision_id','calendar_name','months_per_year','days_per_month','days_per_year','civil_day_seconds','correction_seconds','correction_after_month','correction_after_day','correction_is_date','source_standard_revision_ids','calendar_rule_raw'],
 'era_boundary_mapping':['era_mapping_id','from_era','from_year','to_era','to_year','mapping_type','approval_status','era_edition','legacy_era_description','current_era_description'],
 'time_policy':['policy_id','policy_revision_id','policy_name','policy_raw','annual_boundary_rule_raw','unknown_end_rule_raw','exact_boundary_rule_raw','annual_point_difference_raw'],
}
for record_kind,names in cal_fields.items():
    table=calendar_tables[record_kind]
    for n in names:
        cal.append(cdef(n,tables[('C00',table)]['fields'][n]['type'],False,[bind(table,n,record_kind)],f'{record_kind} 행에만 값이 존재. 다른 행 종류에서는 공란. 원문/값을 다른 종류 필드에 섞지 않음.'))
for n in ['setting_status','source_namespace','source_id']:
    cal.append(cdef(n,'string_nullable',False,[bind(t,n,k) for k,t in calendar_tables.items()], '각 record_kind의 원문 상태·근거를 그대로 보존. 대응점 승인상태와 설정 상태는 별개.'))
typed['PUB_CALENDAR_V2']=cal

evt=direct('수동사건',['event_id','event_title','event_type','description','route','date_precision','end_status','start_raw','end_raw','start_era','start_year','start_month','start_day','end_era','end_year','end_month','end_day','setting_status','source_namespace','source_id','original_location','notes'],['event_id'])
evt+=direct('사건대상관계',['event_target_id','entity_namespace','entity_id','relation_role'])
for name,alt in [('era','start_era'),('year','start_year'),('month','start_month'),('day','start_day')]:
    evt.append(cdef(name,'string_nullable' if name=='era' else 'integer_nullable',False,[bind('수동사건',name),bind('수동사건',alt)],
       'NAT 점사건의 명시 기년/년/월/일을 사용. REG 기간사건은 근거 있게 파싱된 시작 구성필드가 존재할 때만 제공. 두 표현이 충돌하면 conflict 상태이며 임의 coalesce하지 않음.'))
typed['PUB_MANUAL_EVENTS_V2']=evt

for contract in export_contracts:
    i=contract['dataset_id']; columns=typed[i]
    names={c['field_id'] for c in columns}
    for name,kind in [('owner_file_code','string'),('owner_spreadsheet_id','string_nullable'),('schema_version','string'),('release_id','string_nullable'),('source_revision','string_nullable'),('validation_status','string'),('checked_at','string_nullable'),('record_count','integer_nullable'),('coverage','string')]:
        if name in names:continue
        if name=='owner_file_code': c=cdef(name,kind,True,rule='제공 owner 고정 코드',constants={'all':'C00'})
        else:c=cdef(name,kind,name=='schema_version',[bind('데이터셋레지스트리',name)],f'dataset_id={i} 행의 메타를 읽는다. checked_at/source_revision은 실제 수신검증 기록이며 NOW로 조작하지 않음. 미실행이면 validation_status=not_run, ID/시각은 공란.')
        columns.append(c);names.add(name)
    if 'value_status' not in names:
        columns.append(cdef('value_status','string',False,rule='비수치 정의/분류/목록에는 not_applicable. 수치값이 있는 역법은 실제 값과 공란을 구별하되 세계관 미상/미정 상태를 임의 확정하지 않는다.'));names.add('value_status')
    if 'setting_status' not in names:
        columns.append(cdef('setting_status','string_nullable',False,rule='코드북 사용상태/출처 정본상태를 이 축으로 자동 치환하지 않음. 해당 정의 기록에 별도 설정상태가 없으면 공란 유지.'));names.add('setting_status')
    contract['column_schema']=columns
    contract['required_headers']=[c['field_id'] for c in columns]
    contract['column_order']=contract['required_headers']
    contract['required_values']=[c['field_id'] for c in columns if c['required']]
    contract['field_resolution_status']='모든 source_bindings의 C00 table_id/field_id 존재를 정적 확인; 데이터 변환/온라인 제공 미실행'
    contract['missing_field_policy']='헤더는 고정 유지. 원문에 없는 선택필드 값은 공란/해당없음. required 값이 누락된 불완전 입력행도 삭제하지 않고 별도 오류표시 및 계보보존.'
    contract['contract_status']='typed schema 및 원필드/union 대응 명시 · 온라인 구현/권한/재계산 검증 대기'
    if i=='PUB_MANUAL_EVENTS_V2':
        contract['join']={'type':'left','left':'C00.수동사건','right':'C00.사건대상관계','key':'event_id','cardinality':'1:N','unmatched_policy':'대상 없는 사건도 한 행 보존하고 event_target_id/entity_id 공란. 대상 미입력을 기록.'}
        contract['primary_key_fields']=['event_id','event_target_id']
        contract['key_null_policy']='event_target_id 공란인 사건은 1행만 허용. event_target_id는 대상관계가 있을 때만 필수이며 기술키를 세계관 대상처럼 발급하지 않음.'
    assert len({c['field_id'] for c in columns})==len(columns), i

issue_states={
 'CH-001':('PH0 기준 선택 응답 대기',False,'PH1의 sourcefield 목적지는 현 온라인 snapshot으로 명세. 기준본 동일성은 아직 주장하지 않는다.'),
 'CH-002':('명세 처리규칙 지정 완료',False,'C00 중립목록/별칭과 N10 국가목록원문속성 필드 목적지·키를 명시. 통합 담당은 같은 사실의 입력표 중복이 없도록 schema merge한다.'),
 'CH-003':('행별 정본 채택 대기',False,'서로 다른 후보를 기준개정이력에 보존하고 미채택으로 안전하게 이관하는 명세 완료. 세계관 값 선택은 하지 않는다.'),
 'CH-004':('명세 처리규칙 지정 완료',False,'서술 원문과 구조화된 구성필드를 별도 보존. 파싱 불가/기년 불확실은 계산 제외·원문조회로 명확히 처리한다.'),
 'CH-005':('명세 역할 보정 완료',False,'381행 target role이 literal source role과 분리되어 있고 호환 캐시/동적결과는 입력 사실로 승격하지 않는다.'),
 'CH-006':('명세 지정 · 네이티브 실행시험 대기',False,'legacy 그룹명을 유지해 group_code 계약으로 배포하고 native 칩 검증은 T081로 추적. 현재 60개를 단정하지 않는다.'),
 'CH-007':('C00 typed 계약 완료 · 통합 alias 적용 대상',False,'8개 제공계약의 모든 C00 source bindings를 실제 field와 검증했다. H90 외부 dataset aliases는 통합 담당이 region/nation 제공계약에 맞춰 고정한다.'),
 'CH-008':('퇴역 보존 및 운영 대체 명세 완료',False,'미확인 구판 헤더는 정확 source_cell/column으로 보존하고 운영 의미는 R10 typed 제공표로 대체. 추정 원문 라벨을 정본으로 채택하지 않는다.'),
 'CH-009':('V2 개선규칙 명시 완료',False,'원문 개수조건을 보존하되 H05에서 실제 ID 집합 일치와 T029를 요구한다.'),
 'CH-010':('명시적 canonical 필드 대응 완료',False,'임시 후보명을 기준개정이력으로 옮기는 integration_contracts에 14개 필드 변환과 역법 파생 원칙을 지정했다.'),
}
for it in issues:
    istate,blocked,resolution=issue_states[it['issue_id']]
    it.update(status=istate,is_ph1_field_design_blocker=blocked,resolution_or_current_boundary=resolution)

source_ids={x['source_field_id'] for x in fields}
mapped_ids=[x['source_field_id'] for x in spec]
assert len(mapped_ids)==len(set(mapped_ids))==len(source_ids)
assert set(mapped_ids)==source_ids
assert all(json.loads(x['targets_json']) for x in spec)
assert all(t['field'] and t['table'] and t['file_code'] for x in spec for t in json.loads(x['targets_json']))

schema_tables=[]
for t in tables.values():
    t['fields']=list(t['fields'].values())
    # New technical helper columns cannot silently become user-entered world facts.
    t['new_field_values_not_created']=True
    schema_tables.append(t)
with (OUT/'common_hub_field_spec.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(spec[0]));w.writeheader();w.writerows(spec)
def dump(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
common={'project_id':'WORLD-DATA-V2','spec_owner':'common_hub','created_at':NOW,'status':status,
        'source_snapshot_ids':{'REG-V1':'sha256:1456ec38314c47f740a205e375891d0773d39228b5da678dfd4ffc1da56be15e','NAT-V1':'sha256:f590df6a0c855911011be0f83d942add1f8dcf1a218bcdf053393d1ce37519c1'},
        'assignment_rule':'source row 소유. 입력 원본 owner와 명세 작성자는 별개.',
        'source_documents':['01_세계관_데이터_V2_분리고도화_WORK_작업계획서.md','02_기존87개시트_이관대응표.csv','PH1/actual_field_mapping_draft.csv','PH1/sheet_inventory.json','PH1/headers_notes_links_validations.json'],
        'coverage':{'source_sheets':27,'source_field_ids':len(source_ids),'unique_spec_rows':len(spec),'missing_spec_rows':0,'static_coverage_only':True},
        'acceptance_tests':{'passed':1,'passed_ids':['T-002'],'not_run':83,'basis':'상위 작업의 새 V1 시작/종료 전체 비교 증거. 이 명세 작성은 추가 시험 통과 아님'},
        'PH1_complete':False,'operating_files_created_by_this_subtask':0,'online_actions_by_this_subtask':0}
dump('common_hub_schema.json',{**common,'schema_version':'V2-draft-common-hub-1','tables':schema_tables,'export_contracts':export_contracts,'integration_contracts':integration_contracts,
 'id_rule':'기존 ID 원문 유지. 누락 이관기술키만 legacy_locator를 키로 고정 저장하는 레지스트리에서 발급; 행 정렬/재실행에 바뀌지 않음.',
 'time_rule':'원문/구성필드/정밀도/끝상태를 별도 보존. 서력 DATE 사용 금지.',
 'status_axes':['값 상태','값 생성방식','설정 상태','채택 상태','검증 상태','루트/기년 판본'],
 'schema_next_gate':'외부분야 table_id 병합·required_dataset 계약 해소·미확인 header 대조·정본 결정후보 보존 처리 검토; PH0 예외승인 여부 별도'})
dump('common_hub_function_spec.json',{**common,'functions':functions,'write_boundary':{'C00_imports':[],'H90_input_allowed':['조회조건','상태필터정의','검증 실행설정'],'H90_imported_by_other_owners':False,'N30_import_N20':False},'test_074_safety':'실제 V1에 시험 변경 금지. TEST V1 복제본에서 양쪽 차분을 모의시험하며 실제 V1은 읽기 비교만.'})
dump('common_hub_issues.json',{**common,'issues':issues,'observation_vs_design':'source_header/source_role/수식캐시는 실제 관측; target schema/기능은 구현 전 설계. 계획 미정은 세계관 값으로 채우지 않음.',
 'unsupported_claims':['온라인 운영이관 완료','381필드 의미검증 완료','PH1완료','모든 시험 통과','첨부본과 셀값 동일']})
print(json.dumps({'fields':len(spec),'tables':len(tables),'functions':len(functions),'issues':len(issues),'exports':len(export_contracts),'owned_sheets':27,'outputs':['common_hub_field_spec.csv','common_hub_schema.json','common_hub_function_spec.json','common_hub_issues.json'],'status':status},ensure_ascii=False,indent=2))
if '--inspect' in sys.argv:
    for key,rows in literal_rows.items():
        code,sheet=key
        if sheet in {'00_기준_메타','91_스키마_안내','99_검증','98_검증_요약','99_검증_상세','00 공통 기준','41_행성_연결','43_지역_참조_연결'}:
            take=160 if sheet in {'00_기준_메타','00 공통 기준','91_스키마_안내'} else 12
            print(json.dumps({'source':code,'sheet':sheet,'rows':{k:v for k,v in rows.items() if k<=take}},ensure_ascii=False))
    print(json.dumps({'owned_fields':len(fields),'sheets':len({(x['source_file_code'],x['source_sheet_name']) for x in fields})}))
    raise SystemExit
