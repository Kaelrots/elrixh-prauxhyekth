from pathlib import Path
import csv, json, re, hashlib
from collections import Counter, defaultdict

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
rows = list(csv.DictReader((BASE/'actual_field_mapping_draft.csv').open(encoding='utf-8-sig', newline='')))
inventory = json.loads((BASE/'sheet_inventory.json').read_text(encoding='utf-8-sig'))
literals = list(csv.DictReader((BASE/'literal_cells.csv').open(encoding='utf-8-sig', newline='')))
formula_patterns = json.loads((BASE/'formula_patterns_and_dependencies.json').read_text(encoding='utf-8-sig'))

# Every list below is in the observed source-column order; it is not a column-name guess.
MAP = {
'01-지역 마스터': ('R10','지역목록','sort_order,name_ko,name_roman,name_elun,region_level,region_id,parent_region_id_1,parent_name_1,parent_region_id_2,parent_name_2,region_grade,region_class,hex_color,color_chip,setting_status'),
'02_지역_관계': ('R10','지역관계','legacy_relation_id,child_region_id,child_name,parent_region_id,parent_name,relation_type,original_location'),
'70 지역 특성': ('R10','지역특성관계','region_id,region_name,trait_id,trait_name,start_raw,end_raw,active_status,regional_description,setting_status,source_id,source_name,notes'),
'60 거점 시설': ('R10','시설목록','facility_id,facility_name,facility_type,region_id,region_name,operator_raw,start_raw,end_raw,operating_status,capacity_or_output_raw,unit,setting_status,source_id,source_name,notes'),
'61 교통망': ('R10','교통노선','transport_id,transport_name,transport_type,origin_region_id,origin_region_name,destination_region_id,destination_region_name,path_raw,direction,start_raw,end_raw,design_speed,speed_unit,design_capacity,capacity_unit,operating_status,setting_status,source_id,source_name,notes'),
'20 인구': ('R20','인구관측','region_id,region_name,time_raw,value_status,value_numeric,value_min,value_max,unit,population_definition,data_scope,value_basis,setting_status,source_id,source_name,notes'),
'12_지역_인구': ('R20','인구관측','record_id,planet_scope_id,route,era,year,region_id,value_numeric,population_definition,unit,aggregation_include,setting_status,source_id,notes,region_level,observation_key'),
'21 인구 변동': ('R20','인구변동','region_id,region_name,start_raw,end_raw,births,deaths,in_migration,out_migration,other_change,unit,value_status,value_basis,setting_status,source_id,source_name,notes'),
'30 문화 분포': ('R30','문화분포','region_id,region_name,time_raw,culture_id,culture_name,value_status,value_numeric,unit,denominator,data_scope,setting_status,source_id,source_name,notes'),
'32 언어 분포': ('R30','언어분포','region_id,region_name,time_raw,survey_basis,language_id,language_name,value_status,value_numeric,unit,denominator,data_scope,setting_status,source_id,source_name,notes'),
'33 종족 분포': ('R30','집단분포','region_id,region_name,time_raw,group_id,group_name,value_status,value_numeric,unit,denominator,data_scope,setting_status,source_id,source_name,notes'),
'31 종교 분포': ('R40','종교분포','region_id,region_name,time_raw,religion_id,religion_name,value_status,value_numeric,unit,denominator,data_scope,setting_status,source_id,source_name,notes'),
'10 정치 지역관계': ('R50','지역국가관계','region_id,region_name,relation_type,nation_id,nation_name,start_raw,end_raw,end_status,applied_scope,change_basis,setting_status,source_id,source_name,notes'),
'15_지역_소속이력': ('R50','지역국가관계','relation_id,region_id,planet_scope_id,route,era,nation_id,relation_type,start_year,end_year,end_status,controlled_land_area,setting_status,source_id,notes,query_end_year'),
'03_영토_이력': ('R50','지역국가관계','relation_id,nation_id,route,era,planet_scope_id,region_id,relation_type,start_year,end_year,end_status,controlled_land_area,setting_status,source_id,notes,aggregation_include,query_end_year,region_level'),
'40 경제 지역값': ('R60','경제관측','region_id,region_name,metric_id,metric_name,time_raw,value_status,value_numeric,unit,data_scope,value_basis,setting_status,source_id,source_name,notes'),
'13_지역_경제': ('R60','경제관측','record_id,planet_scope_id,route,era,year,region_id,metric_id,value_numeric,unit,currency,price_era,price_year,aggregation_include,setting_status,source_id,notes,region_level,observation_key'),
'41 산업': ('R60','산업활동','region_id,region_name,start_raw,end_raw,industry_name,product_raw,value_status,production_quantity,production_unit,employment,industry_share,share_denominator,setting_status,source_id,source_name,notes'),
'42 교역': ('R60','지역간교역','origin_region_id,origin_region_name,destination_region_id,destination_region_name,start_raw,end_raw,commodity_raw,value_status,quantity,quantity_unit,transaction_value,currency_or_unit_raw,path_raw,setting_status,source_id,source_name,notes'),
'50 환경 지역값': ('R70','환경관측','region_id,region_name,property_raw,value_status,value_raw,unit,statistic_basis,start_raw,end_raw,setting_status,source_id,source_name,notes'),
'14_지역_자연환경': ('R70','환경관측','record_id,planet_scope_id,region_id,environment_type,property_raw,value_numeric,value_text,unit,route,era,start_year,end_year,setting_status,source_id,notes'),
'51 자원 분포': ('R70','자원분포','region_id,region_name,resource_id,resource_name,time_raw,value_status,existence_status,reserve_quantity,quality_raw,production_quantity,unit,availability_raw,setting_status,source_id,source_name,notes'),
'10_행성_기본값': ('R70','행성기본값','planet_scope_id,property_id,property_name,value_numeric,value_text,unit,generation_method,setting_status,source_id,original_location,notes'),
'11_행성_연간지표': ('R20;R60;R30','행성지표_행조건별','observation_key,planet_scope_id,route,era,year,metric_id,unit,currency,price_era,price_year,direct_value,calculated_value,selected_value,generation_method,coverage_status,aggregation_level,valid_record_count,unique_region_count,target_region_count,setting_status,source_id,notes,direct_sum_difference,population_growth_rate'),
}
LOOKUPS={'region_name','parent_name_1','parent_name_2','child_name','parent_name','nation_name','source_name','culture_name','language_name','group_name','religion_name','metric_name','resource_name','trait_name','origin_region_name','destination_region_name'}
NUMERIC={'value_numeric','value_min','value_max','births','deaths','in_migration','out_migration','other_change','production_quantity','employment','industry_share','quantity','transaction_value','reserve_quantity','design_speed','design_capacity','controlled_land_area','direct_value','calculated_value','selected_value','direct_sum_difference','population_growth_rate'}
INTEGER={'sort_order','year','start_year','end_year','price_year','valid_record_count','unique_region_count','target_region_count','query_end_year','month','day','start_month','start_day','end_month','end_day'}
STATE={'value_status','setting_status','end_status','operating_status','existence_status','active_status','coverage_status','validation_status','selection_rule','date_precision','start_precision','end_precision','generation_method'}
FORMULA={'color_chip','observation_key','query_end_year','calculated_value','selected_value','coverage_status','valid_record_count','unique_region_count','target_region_count','direct_sum_difference','population_growth_rate'}
DATE_FIELDS=['route','calendar_revision','era','year','month','day','date_precision','time_raw','start_era','start_year','start_month','start_day','start_precision','start_raw','end_era','end_year','end_month','end_day','end_precision','end_raw','end_status']
AUDIT_FIELDS=['record_id','legacy_locator','legacy_record_id','source_id','original_location','source_snapshot_id','setting_status','validation_status','notes']
VALUE_FIELDS=['value_raw','value_numeric','value_text','value_status','generation_method','unit','data_scope','value_basis','selection_status','selection_reason']
METRIC_ROUTE={'population': {'file':'R20','input':'行성인구관측'.replace('行','행'),'output':'행성인구계산'},'gdp_nominal': {'file':'R60','input':'행성경제관측','output':'행성경제계산'},'gdp_real': {'file':'R60','input':'행성경제관측','output':'행성경제계산'},'gdp_unclassified': {'file':'R60','input':'행성경제관측','output':'행성경제계산'},'urbanization': {'file':'R30','input':'사회지표','output':'사회지표계산'}}
CALENDAR_PROPERTIES=['civil_day','civil_year_days','year_correction','months_per_year','days_per_month']

def dtype(field):
    if field in NUMERIC: return 'decimal_nullable; exact original in value_raw'
    if field in INTEGER or field.endswith(('_year','_month','_day','_count')): return 'integer_nullable'
    if field=='aggregation_include': return 'boolean_nullable'
    if field in STATE: return 'C00_code_nullable; unknown original retained'
    if field.endswith('_id'): return 'text_identifier; case preserved'
    return 'text_nullable'

def fk(field):
    if field in {'region_id','child_region_id','parent_region_id','origin_region_id','destination_region_id'}: return 'R10.지역목록.region_id'
    if field=='planet_scope_id': return 'C00.대상목록.scope_id; planet.1 preserved; do not equate planet ID to region ID without registered relation'
    if field=='nation_id': return 'C00.국가식별목록.nation_id'
    if field=='source_id': return 'C00.출처레지스트리.source_id'
    for k in ['culture','language','group','religion','resource','trait','metric']:
        if field==k+'_id': return 'C00.'+k+'_dictionary.'+field
    return ''

def destination(file,table,field,role='input',condition='all source records'):
    return dict(file_code=file,table=table,field=field,role=role,row_condition=condition,rule=condition,data_type=dtype(field),reference=fk(field))

def table_role(r,field):
    if field in LOOKUPS or field in FORMULA: return 'calculated'
    if field=='region_level' and r['source_sheet_name']!='01-지역 마스터': return 'calculated'
    return 'input'

issues=[
 dict(issue_id='R-001',status='결정대기',topic='행성 urbanization 행',evidence='11_행성_연간지표 F열의 실제 urbanization 행 24개; 직접값 없음',proposal='R30.사회지표 단일 입력 원본으로 목적지 지정; 도시화 정의·분모·가중 방식 확인 후 계산',blocks='urbanization 계산·채택',no_invention='도시 인구/비율을 창작하지 않음'),
 dict(issue_id='R-002',status='결정대기',topic='시설 수용량/생산량 혼합',evidence='60 거점 시설 J열의 헤더가 수용량/생산량; 원자료 행 없음',proposal='판별되면 설계 수용량은 R10.시설목록.design_capacity, 기간 실적은 R60.시설실적.value_numeric; 미판별 원문은 R10.시설측정미분류.raw_value',blocks='해당 값 자동 계산·목적지 확정',no_invention='빈 분야의 사실·기간·단위 생성 금지'),
 dict(issue_id='R-003',status='결정대기',topic='원문 반경·표면적과 계산값 충돌',evidence='10_행성_기본값 radius_as_written/equatorial_radius 및 surface_area/ellipsoid_area',proposal='각 property_id·원문·산식을 별도 보존하고 adopted=false가 아닌 미채택/미결 상태 사용',blocks='면적 기준 채택·이를 전제한 통계',no_invention='계산값 자동 정본 승격 금지'),
 dict(issue_id='R-004',status='결정대기',topic='자원 매장/생산 공용 단위',evidence='51 자원 분포 H=매장량,J=생산량,K=단위; 입력 행 없음',proposal='reserve_unit와 production_unit를 분리; 원문 단위는 shared_unit_raw에 보존. 값별 의미 확인 후만 변환',blocks='단위·기간 불명 생산 통계',no_invention='생산량을 매장량 또는 연간량으로 추정하지 않음'),
 dict(issue_id='R-005',status='결정대기',topic='구형/확장 지역 사실의 동일성',evidence='20 인구/12_지역_인구,40 경제 지역값/13_지역_경제,50 환경 지역값/14_지역_자연환경,10 정치 지역관계/15_지역_소속이력/NAT03',proposal='대상·루트·기년·기간·정의·단위·범위·출처까지 맞는 후보만 연결; 서로 다른 후보 모두 보존',blocks='중복 자동 병합·최종 채택',no_invention='값 같음/동명만으로 병합 금지'),
 dict(issue_id='R-006',status='결정대기',topic='상위 지역 미해결·지역 계층 충돌',evidence='REG 지역 마스터 G/I 두 부모열과 02_지역_관계 파생식',proposal='다대다 지역관계로 풀고 원문 부모 ID 유지; 누락 ID·자기참조·순환·집계 중첩 진단',blocks='관련 완전 집계',no_invention='누락 부모를 새 설정으로 생성하지 않음'),
 dict(issue_id='R-007',status='결정대기',topic='세계관 날짜 미정밀·기년 대응',evidence='기존 시작/종료/시점 자유문자열 및 연도형 열',proposal='원문과 알려진 정밀도만 구조화; 미해석은 date_parse_status=미해석, 계산 제외',blocks='미해석/교차 기년 날짜의 정렬·합산',no_invention='DATE 함수·연도 비례변환·가상 월일 금지'),
 dict(issue_id='R-008',status='결정대기',topic='문화·집단·종교 분포 분모/응답 방식',evidence='문화·종교·언어·종족 분포 원문 스키마',proposal='분류축별 표 유지, 분모·복수응답·상위종교 포함관계 확인 전 합100% 검사 보류',blocks='무조건 합계·인구환산',no_invention='집단 정의·구성비 보완 금지'),
 dict(issue_id='R-009',status='계약 조정 대기',topic='행성 역법 값의 C00 단일화',evidence='10_행성_기본값 civil_day/civil_year_days/year_correction/months_per_year/days_per_month',proposal='C00 공통기준 개정 원문 후보와 대조; 동일 판본 확인 후 참조. R70은 물리 설명·legacy locator 보존',blocks='미대조 판본의 채택',no_invention='같은 숫자라는 이유만으로 서로 다른 기준개정 병합 금지'),
]

result=[]
tables={}
def register(d,label='',required=False):
    key=(d['file_code'],d['table'])
    if ';' in key[0]: raise ValueError(key)
    t=tables.setdefault(key,dict(file_code=key[0],table=key[1],fields={},source_fields=[],role=d['role']))
    if t['role']!=d['role']: t['role']='mixed_input_derived'
    t['fields'].setdefault(d['field'], dict(field=d['field'],label_ko=label or d['field'],data_type=d['data_type'],nullable=not required,reference=d['reference'],role=d['role']))
    return t

for r in rows:
    sheet=r['source_sheet_name']
    if sheet not in MAP: continue
    if sheet=='03_영토_이력' and r['source_file_code']!='NAT-V1': continue
    if sheet!='03_영토_이력' and r['source_file_code']!='REG-V1': continue
    file,table,fields=MAP[sheet]
    source_group=[x for x in rows if x['source_file_code']==r['source_file_code'] and x['source_sheet_id']==r['source_sheet_id']]
    names=fields.split(',')
    assert len(source_group)==len(names), (sheet,len(source_group),len(names))
    field=names[source_group.index(r)]
    role=table_role(r,field)
    dests=[destination(file,table if role=='input' else table+'_조회계산',field,role)]
    transform='원문값과 기존 ID·상태·판본·출처를 보존. 해석 가능한 형만 변환하고 원문 value_raw/legacy_locator를 유지.'
    validation='키 중복/외래키 존재/자료형/원문 보존 대조; 행이 없으면 자료 없음이며 시험 통과로 보지 않음.'
    issue_ids=[]
    if role=='calculated':
        transform='원 수식과 저장값은 PH0/PH1 증거에 보존. 해당 V2 입력 원본·제공표에서 네이티브 수식으로 재구현. 값으로 이관하거나 입력 원본으로 복제하지 않음.'
        validation='실제 Google Sheets 재계산·오류 전파·입력 변경·범위 확장 시험 필요. 현재 미실행.'
    if field in LOOKUPS:
        transform+=' ID→표시명 조회. 조회 실패는 연결오류/미등록 ID를 구별하고 빈문자/0으로 숨기지 않음.'
    if field.endswith('_raw') and any(w in field for w in ['time','start','end']):
        transform+=' DATE-TEMPORAL 규약으로 era/year/month/day와 precision을 분리하되 원문은 유지; 해석 불가시 결정대기.'; issue_ids.append('R-007')
    if field in {'year','start_year','end_year'}:
        transform+=' 연도만 있으면 precision=year; 월일을 채우지 않음. 제3기 0년 허용; 기년 판본·루트 유지.'
    if field=='query_end_year':
        transform+=' 필터용 종료 경계만 계산하고 end_year 원본에 되쓰기 금지. 종료 미상은 시작연도만 열람, 지속 중과 구분.'
    if field in NUMERIC:
        transform+=' 빈칸·미상·미정·해당없음·확정0을 독립 상태로 처리; 원문 숫자 정밀도 초과시 문자열 보존/근사값 분리.'
    if sheet=='01-지역 마스터' and field in {'parent_region_id_1','parent_region_id_2'}:
        dests=[destination('R10','지역관계','parent_region_id','input',field+' nonblank')]
        transform='G/I의 비어 있지 않은 부모마다 관계 1행; child_region_id=원행 F; relation_source_slot=원열 유지. 02_지역_관계 같은 부모관계의 두 번째 수동 입력을 만들지 않음. 존재 시작연도 미생성.'; issue_ids.append('R-006')
    elif sheet=='01-지역 마스터' and field in {'parent_name_1','parent_name_2'}:
        dests=[destination('R10','지역관계_조회계산','parent_name','calculated')]
    elif sheet=='02_지역_관계':
        dests=[destination('R10','지역관계_조회계산',field,'calculated')]
        transform='REG 마스터 G/I에서 생성된 파생 관계를 검증·대조하는 목적지. 기존 표시 relation ID는 legacy_relation_id로 보존하고, 신규 고정 relation_id는 locator 대응 재사용. 파생 행을 두 번째 사실 입력으로 복제하지 않음.'
    if sheet in {'20 인구','12_지역_인구','40 경제 지역값','13_지역_경제','50 환경 지역값','14_지역_자연환경','10 정치 지역관계','15_지역_소속이력','03_영토_이력'}:
        transform+=' 정규 원본 1개로 합류; 원본 간 동일성 대조 전 후보 행 삭제/합산 금지.'
    if sheet=='03_영토_이력' and field=='nation_id': transform+=' 원문 scope_id는 국가 영역 식별자이므로 nation_id에 대응; 원문 scope_id도 legacy_scope_id로 보존.'
    if field=='controlled_land_area': transform+=' 헤더에 km² 명시된 두 확장표는 area_unit=km²; 면적비로 인구/GDP 배분 금지.'
    if sheet=='60 거점 시설' and field in {'capacity_or_output_raw','unit'}:
        dests=[destination('R10','시설측정미분류', 'raw_value' if field=='capacity_or_output_raw' else 'raw_unit','preservation_pending','semantic unresolved'),destination('R10','시설목록','design_capacity' if field=='capacity_or_output_raw' else 'capacity_unit','input','explicit design capacity'),destination('R60','시설실적','value_numeric' if field=='capacity_or_output_raw' else 'unit','input','explicit period production/throughput actual')]
        transform='측정 의미가 확인된 경우에만 해당 단일 사실 표로 분기. 미분류 원문은 운영 계산에서 제외. 부모 facility_id·원행 근거를 전달; 같은 수치를 두 입력표에 중복 저장 금지.'; issue_ids.append('R-002')
    if sheet=='51 자원 분포':
        if field=='production_quantity': dests=[destination('R60','자원생산',field)]
        elif field in {'region_id','region_name','resource_id','resource_name','time_raw','value_status','setting_status','source_id','source_name','notes','unit'}:
            ff='shared_unit_raw' if field=='unit' else field
            dests=[destination('R70','자원분포' if role=='input' else '자원분포_조회계산',ff,role,'reserve/existence/quality/availability facts'),destination('R60','자원생산' if role=='input' else '자원생산_조회계산',ff,role,'source production_quantity exists')]
        transform+=' 매장/존재/품질/이용은 R70, 생산 실적은 R60. 공유 식별자·근거만 각 사실에 연결. H/J 값의 단위/기간 불명확시 계산 제외.'; issue_ids.append('R-004')
    if sheet=='10_행성_기본값':
        noncal='property_id not in '+','.join(CALENDAR_PROPERTIES)
        dests=[destination('R70','행성기본값',field,'input',noncal+'; original numeric D cell of the same row is not a formula (literal, text-only, or unknown-value property)'),destination('R70','행성기본값_계산', 'calculated_value' if field=='value_numeric' else field,'calculated',noncal+'; original numeric D cell of the same row is a formula; metadata travels with that calculated property')]
        dests.append(destination('C00','공통기준_개정후보',field,'input','property_id in '+','.join(CALENDAR_PROPERTIES)))
        transform='property_id별 직접값/문자값/산식/근거 보존. 역법 5개 속성은 C00 기존 기준 개정 후보와 대조하고 R70에 입력원본 중복 금지. solar_day/sidereal_day/orbital_period는 물리 설명과 산출 근거를 R70에 유지.'
        if field=='value_numeric': transform+=' 7개 수식 셀은 계산 경로로만 재구현; 원문값과 계산값·채택 상태 분리. 불명 육지율을 0으로 보완하지 않음.'
        issue_ids+=['R-003','R-009']
    if sheet=='11_행성_연간지표':
        dests=[]
        for metric,rt in METRIC_ROUTE.items():
            field2='value_numeric' if field=='direct_value' and metric=='urbanization' else field
            target=rt['output'] if role=='calculated' else rt['input']
            if field=='population_growth_rate' and metric!='population':
                dests.append(destination(rt['file'],'旧行성지표수식보존'.replace('旧','구'),field,'preserved_formula_only','metric_id='+metric+'; obsolete nonpopulation population-growth slot'))
            else: dests.append(destination(rt['file'],target,field2,role,'metric_id='+metric))
        transform='행의 실제 metric_id로 분기: population→R20, GDP 3종→R60, urbanization→R30. 입력값·배치조건은 원본표, 파생 수치는 계산표. 정의 불명 새 지표는 미분류 보존/결정대기. 빈 직접값은 실제 관측치로 집계하지 않음.'
        if role=='calculated': transform+=' V1 산식 보존 후 V2 집계 키·대상 ID집합·완전성 계약으로 재구현; 22 고정·IFERROR 0 금지.'
        if field=='population_growth_rate': transform+=' 인구 성장률은 population 행에서만 유효, 나머지 원 수식 슬롯은 증거 보존만 하고 잘못된 인구성장 열을 제공하지 않음.'
        issue_ids.append('R-001')
    if sheet in {'30 문화 분포','31 종교 분포','32 언어 분포','33 종족 분포'}: issue_ids.append('R-008')
    if field=='industry_share': transform+=' % 표시는 0~1로 변환하되 bare 73.45 등 의미 미확정 숫자는 자동 비율화 금지.'
    for d in dests:
        t=register(d,r['source_field'])
        if r['source_field_id'] not in t['source_fields']: t['source_fields'].append(r['source_field_id'])
    o=dict(r)
    o.update(target_file_code=';'.join(dict.fromkeys(x['file_code'] for x in dests)),target_table=';'.join(dict.fromkeys(x['table'] for x in dests)),target_field=';'.join(dict.fromkeys(x['field'] for x in dests)),targets_json=json.dumps(dests,ensure_ascii=False),transform_rule=transform,target_data_type=';'.join(dict.fromkeys(x['data_type'] for x in dests)),issue_ids=';'.join(dict.fromkeys(issue_ids)),spec_status='명세 작성; 행별 의미 대조/온라인 시험 미실행',migration_status='미실행',validation_result=validation,change_reason='PH1 대상표·필드·형·처리경로 명세; 원본단일화 및 파생식 재구현',approval_or_rule='사용자 시작지시 + 계획서 4.2~4.8,5~8; 정본 승인과 별개')
    result.append(o)

# Add required empty schemas and structural fields; these contain no fabricated data rows.
EXTRA={
('R10','지역목록'):['source_id','source_snapshot_id','legacy_locator'],
('R10','지역관계'):['relation_id','legacy_relation_id','child_region_id','parent_region_id','relation_type','relation_source_slot']+DATE_FIELDS+AUDIT_FIELDS,
('R10','공간메타'):['geometry_id','region_id','asset_uri','crs_id','boundary_revision','area_value','area_unit','calculation_method']+DATE_FIELDS+AUDIT_FIELDS,
('R10','시설목록'):['facility_id','design_capacity','capacity_unit','capacity_definition','owner_id','operator_id']+DATE_FIELDS+AUDIT_FIELDS,
('R10','교통노선'):['transport_id']+DATE_FIELDS+AUDIT_FIELDS,
('R10','노선경유관계'):['record_id','transport_id','sequence_no','region_id','facility_id','path_raw']+AUDIT_FIELDS,
('R10','지역특성관계'):DATE_FIELDS+AUDIT_FIELDS,
('R20','인구관측'):['metric_id','planet_scope_id','population_definition','species_scope','aggregation_include']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R20','인구변동'):['population_definition','species_scope','opening_population_record_id','closing_population_record_id']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R20','행성인구관측'):['population_definition','species_scope','selection_rule','selection_reason']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R30','문화분포'):['survey_basis','multiple_response','classification_axis','denominator_definition','denominator_record_id']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R30','언어분포'):['multiple_response','classification_axis','denominator_definition','denominator_record_id']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R30','집단분포'):['survey_basis','multiple_response','classification_axis','classification_revision','denominator_definition','denominator_record_id']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R30','사회지표'):['region_id','planet_scope_id','metric_id','denominator','denominator_definition','population_record_id','urban_definition']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R40','종교분포'):['survey_basis','multiple_response','classification_axis','denominator_definition','denominator_record_id','hierarchy_inclusion']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R40','종교시설관계'):['relation_id','facility_id','religion_id','relation_type']+DATE_FIELDS+AUDIT_FIELDS,
('R50','지역국가관계'):['relation_id','legacy_scope_id','area_unit','applied_scope','aggregation_include','change_basis']+DATE_FIELDS+AUDIT_FIELDS,
('R60','경제관측'):['price_type','currency','price_era','price_year','metric_definition','aggregation_include']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R60','행성경제관측'):['price_type','metric_definition','selection_rule','selection_reason']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R60','산업활동'):['industry_id','employment_definition','share_denominator_definition']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R60','地域間교역'.replace('地域間','지역간')):['currency','price_type','transaction_definition']+DATE_FIELDS+AUDIT_FIELDS,
('R60','자원생산'):['resource_id','region_id','facility_id','production_quantity','production_unit','period_definition']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R60','시설실적'):['facility_id','metric_id','definition']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R70','환경관측'):['property_id','statistic_basis']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R70','자원분포'):['reserve_unit','reserve_definition']+DATE_FIELDS+AUDIT_FIELDS+VALUE_FIELDS,
('R70','행성기본값'):['property_revision_id','calculation_method','selection_status','selection_reason','comparison_record_id','standard_revision_id']+AUDIT_FIELDS+VALUE_FIELDS,
}
for (f,t),fs in EXTRA.items():
    for field in dict.fromkeys(fs): register(destination(f,t,field))

COMMON_RULES={
'no_facts_created':'Schemas/route conditions only. No source records migrated and no online mutation.',
'id_policy':'Existing identifier bytes preserved. New relation/observation record IDs are fixed once and stored against legacy_locator; no row-number formula IDs. Existing source IDs separately retained if namespaced collisions exist.',
'temporal':'World dates stored as route/calendar_revision/era/year/month/day/precision; 48 months and 30 days only when the C00 approved revision supports it. Never Gregorian DATE. Exact intervals [start,end); year-only end includes year for annual query without invented month/day. Unknown end differs from ongoing and preserves recorded-start-only behavior.',
'status_axes':['value_status','generation_method','setting_status','validation_status','selection_status','coverage_status'],
'nullable_numbers':'Blank numeric cell remains blank; confirmed zero is numeric 0 plus value status. Unparseable or overprecision original retained verbatim. Never fill IFERROR result with 0.',
'validation_scope':'Duplicate candidates not automatically deleted. All nonempty literal records, formula-only templates and defaults separated. Old statuses/results do not become V2 tests.',
'single_input':'One table per fact type; annual presentation and labels are read-only derivatives. R50 owns territory, R10 owns regions/facilities, R20 population, R60 production, R70 reserves.',
'range_growth':'For every registered dataset, update input capacity, calculated range, validation rules, named publication range, import range and consumer lookup together; test last existing row, first new row and overflow alert in TEST copy.',
'export_contract':['dataset_id','owner_file_code','owner_spreadsheet_id','schema_version','release_id','source_revision','export_range','primary_key_fields','column_schema','record_count','coverage','route','era','status_policy','validation_status','checked_at'],
'connection_state':['미승인/권한 필요','연결 오류','스키마 불일치','자료 없음','초안만 존재','부분합','연결 확인/검증 미실행','검증 통과'],
'no_cycles':'R10<-C00; R20<-C00,R10; R30/R40<-C00,R10,optional R20; R50<-C00,R10; R70<-C00,R10; R60<-C00,R10,optional R20,R70. H90 alone combines production/reserve and reverse cross-checks. No owner imports H90.',
}

FUNC=[
 ('R-F01','R10','지역관계 전환·계층 조회',['01-지역 마스터','02_지역_관계'],'원래 G/I 부모열을 연결행으로 펼치고 같은 부모/원열의 파생관계와 대조. 고정 관계 ID는 locator registry로 재사용. 자기참조/미등록 부모/순환 진단, 복수 상위 허용.','T-003,T-004,T-005,T-014'),
 ('R-F02','R10','지역·시설·노선·특성 조회',['01-지역 마스터','60 거점 시설','61 교통망','70 지역 특성'],'표시명은 ID 조회; HEX는 문자열+색 미리보기. 설계용량과 실제 생산/수송은 분리. 기간 파싱 실패는 미해석으로 남기고 입력 사실은 보존.','T-004,T-076,T-084'),
 ('R-F03','R20','지역/행성 인구 집계·채택',['20 인구','12_지역_인구','11_행성_연간지표'],'동일 루트/기년/시점/정의/종족범위/단위의 채택 관측에서 비중첩 고유 지역 집합을 합산. 대상 ID집합과 정확히 일치할 때 완전합 후보. 부분합은 결측 대상과 표시. 직접0은 유효; 직접 우선·완전합 선택과 근거는 별도.','T-023,T-024,T-025,T-026,T-027,T-028'),
 ('R-F04','R20','인구 변동 잔차',['21 인구 변동'],'기간·정의 동일한 기초인구+출생-사망+유입-유출+기타와 말기인구 비교. 필수 성분 미입력은 계산 불가; 잔차를 없애기 위한 역산 입력 금지.','T-030'),
 ('R-F05','R20','인구 성장률',['11_행성_연간지표'],'연속된 실제 전년도와 동일 정의일 때 (current/prior)-1. 전기0·전기 없음·기년/루트 차이를 사유로 표시. 비연속 관측 비교는 직전관측 증감 별도.','T-031,T-032'),
 ('R-F06','R30;R40','분포·사회지표 조회와 검증',['30 문화 분포','31 종교 분포','32 언어 분포','33 종족 분포'],'분류축/분모/조사기준/복수응답 분리. 배타적 완전 구성에만 합100% 검사. 종교 상하위 동시합산 금지. 모어와 사용가능 언어를 분리. 도시화율은 정의·분모 없는 평균/합산 금지.','T-035,T-036'),
 ('R-F07','R50','영토·통치기간 조회',['10 정치 지역관계','15_지역_소속이력','03_영토_이력'],'지역·국가·관계종류·루트·시점·적용범위로 조회. 같은 지역의 통치/법적영유/주장 병존 허용. nation별 목록은 제공표 필터, N에 영토 재입력 금지. 정확한 종료 배타적, 연도 종료 포함, 미상/지속 구분.','T-010,T-016,T-020'),
 ('R-F08','R60','경제 집계·채택·비율',['40 경제 지역값','13_지역_경제','11_행성_연간지표'],'명목/실질/미분류, 통화, 기준가격, 루트/기년/기간, 대상집합 일치별로 합산. 직접값·부분합·완전합·차이·채택을 구분. 인구당값은 적합 인구가 있을 때만; 영토면적 비례 GDP 자동배분 금지.','T-023,T-028,T-031,T-032,T-034'),
 ('R-F09','R60;R70','자원·시설 사실 분리',['51 자원 분포','60 거점 시설','61 교통망'],'매장/존재/품질 R70, 생산 R60, 시설/노선 설계 R10. 공용 단위 원문 보존 후 의미 판별. 생산/매장 통합은 H90, R70이 R60을 import하지 않음.','T-011,T-012,T-056'),
 ('R-F10','R70','행성 물리 산식 재구현',['10_행성_기본값'],'반경=대응 지름/2; 해양율=1-육지율은 이분 정의 확인시; 면적=원문 표면적×비율은 양쪽 입력과 정의가 있을 때. 타원체 면적은 원식·근거 보존하고 계산값으로만 제공; 원문 표면적/반경 덮어쓰기 금지.','T-038,T-039,T-040'),
 ('R-F11','R10;R20;R30;R40;R50;R60;R70','제공표·오류·범위확장 계약',list(MAP),'닫힌 PUB 범위와 버전 헤더 검증. 수신 성공/권한/오류/자료없음/부분합을 분리. 테스트 사본에서 원본 수정 반영·행 추가·정렬·삭제·확장·불명ID/중복·null/0·연결실패 확인 후 운영 적용.','T-055,T-056,T-057,T-058,T-059,T-060,T-061,T-078,T-083'),
]
functions=[]
TESTS={
'R-F01':['T-004','T-005','T-009','T-010','T-027','T-028','T-037'],
'R-F02':['T-026','T-040','T-077','T-084'],
'R-F03':['T-014','T-027','T-028','T-029','T-030','T-031','T-032','T-033','T-050'],
'R-F04':['T-031','T-033'],
'R-F05':['T-021','T-022','T-047','T-048'],
'R-F06':['T-041','T-042','T-043','T-044','T-049'],
'R-F07':['T-010','T-013','T-016','T-019','T-020','T-021','T-034','T-035','T-036'],
'R-F08':['T-014','T-028','T-029','T-030','T-031','T-035','T-045','T-046','T-047','T-048','T-050'],
'R-F09':['T-039','T-040','T-069'],
'R-F10':['T-038','T-031','T-050'],
'R-F11':['T-068','T-069','T-070','T-071','T-072','T-073','T-075','T-076','T-078','T-079','T-081','T-082','T-083'],
}
checklist={r['test_id']:r for r in csv.DictReader((BASE.parent.parent/'03_검증_체크리스트.csv').open(encoding='utf-8-sig',newline=''))}
for code,owner,name,sheets,algorithm,tests in FUNC:
    patterns=[p for p in formula_patterns if p['source_sheet_name'] in sheets and (p['source_file_code']=='REG-V1' or p['source_sheet_name']=='03_영토_이력')]
    functions.append(dict(function_id=code,owner_file_code=owner,name=name,source_sheets=sheets,source_pattern_ids=[p['pattern_id'] for p in patterns],algorithm=algorithm,test_ids=TESTS[code],test_scenarios=[{'test_id':i,'scenario':checklist[i]['scenario']} for i in TESTS[code]],test_note='체크리스트 시나리오 대응만 작성. 해당 테스트의 타분야 부분은 별도 담당하며 시험 통과 근거 아님',implementation_status='명세 작성',online_test_status='미실행',source_patterns_preserved='PH1/formula_patterns_and_dependencies.json'))
functions[3]['additional_acceptance_cases']=[{'case':'R-POP-BALANCE-01','setup':'TEST 기초100, 출생10, 사망2, 유입5, 유출3, 기타0, 말기110','expected':'잔차0; 원자료 변동 없음','status':'미실행'},{'case':'R-POP-BALANCE-02','setup':'위 TEST에서 출생값만 제거','expected':'출생 미입력 표시; 잔차를 정상0으로 표시하거나 역산하지 않음','status':'미실행'}]
functions[9]['property_formulas']=[
 {'property_id':'equatorial_radius','expression':'equatorial_diameter / 2','required':['equatorial_diameter'],'source_cell':'D4'},
 {'property_id':'polar_radius','expression':'polar_diameter / 2','required':['polar_diameter'],'source_cell':'D5'},
 {'property_id':'ocean_share','expression':'1 - land_share','required':['land_share','approved binary land/ocean definition'],'source_cell':'D9'},
 {'property_id':'land_area','expression':'surface_area * land_share','required':['surface_area','land_share'],'source_cell':'D10'},
 {'property_id':'ocean_area','expression':'surface_area * ocean_share','required':['surface_area','ocean_share'],'source_cell':'D11'},
 {'property_id':'orbital_period','expression':'C00.civil_day * C00.civil_year_days + C00.year_correction','required':['same approved calendar revision for all three operands'],'source_cell':'D24'},
 {'property_id':'ellipsoid_area','expression':'if a=b then 4*pi*a^2 else 2*pi*a^2*(1+(b/a)^2*atanh(sqrt(1-(b/a)^2))/sqrt(1-(b/a)^2)); a=equatorial_radius,b=polar_radius','required':['a>0','b>0','a>=b','same property revision and unit'],'source_cell':'D25'},
]
functions[9]['formula_guards']='Missing operands return numeric blank plus reason, not numeric 0. Unequal axes outside a>=b are unsupported by this preserved oblate formula and must raise method/shape error. Computed outputs remain calculated candidates; source status is not promoted.'

# Record source evidence without pretending formula-template rows are real facts.
scoped_sheets={(r['source_file_code'],r['source_sheet_id']) for r in result}
inv=[s for s in inventory if (s['source_file_code'],str(s['source_sheet_id'])) in scoped_sheets]
for (f,t),s in tables.items():
    key_table=t.removesuffix('_조회계산').removesuffix('_계산')
    if key_table=='지역목록': pk=['region_id']
    elif key_table=='시설목록': pk=['facility_id']
    elif key_table=='교통노선': pk=['transport_id']
    elif key_table in ['지역관계','지역국가관계','종교시설관계']: pk=['relation_id']
    elif key_table=='행성기본값': pk=['property_revision_id']
    elif s['role'] in {'calculated','preserved_formula_only'}: pk=['record_id']
    else: pk=['record_id']
    for field in dict.fromkeys(pk+['legacy_locator','source_snapshot_id']):
        s['fields'].setdefault(field,dict(field=field,label_ko=field,data_type=dtype(field),nullable=False,reference=fk(field),role='lineage' if field in ['legacy_locator','source_snapshot_id'] else s['role']))
    s['fields']=list(s['fields'].values())
    for field in s['fields']:
        field['field_id']=field['field']; field['type']=field['data_type']; field['required']=field['field'] in pk
        if field['required']: field['nullable']=False
    s['table_id']=t
    s['technical_headers']=[x['field'] for x in s['fields']]
    s['primary_key_fields']=pk
    s['logical_table_note']='논리 표 명세. 표마다 별도 탭을 강제하지 않으며 입력/조회/검증/제공의 역할과 보호 경계로 구현.'
    s['input_policy']='수동 입력 금지; V2 원본에서 파생' if s['role'] in {'calculated','preserved_formula_only'} else '필수키·근거·상태를 갖춘 실제 관측만 입력; 빈 분야는 헤더/검증만'
    s['test_status']='미실행'
    s['export_dataset_id']=None
    s['export_range']='NOT_CREATED: bound by dataset registry during PH2; header plus all active records, closed range'
    s['validation_boundary']={'input':'all actual records including incomplete-ID rows; formula-only/default/format-only rows separately classified','calculation':'key-aligned active source records; no fixed 500/1000 cutoffs','publication':'verified headers and active row count, status/source/route/period retained','consumer':'same schema/release and full published active range','overflow':'error before silent omission; test first beyond-capacity record'}

PUB={
'R10':{'PUB_REGIONS_V2':['지역목록','지역목록_조회계산'],'PUB_REGION_RELATIONS_V2':['지역관계','지역관계_조회계산'],'PUB_FACILITIES_V2':['시설목록','시설목록_조회계산'],'PUB_TRANSPORT_V2':['교통노선','교통노선_조회계산'],'PUB_REGION_TRAITS_V2':['지역특성관계','지역특성관계_조회계산']},
'R20':{'PUB_POPULATION_V2':['인구관측','인구관측_조회계산'],'PUB_POPULATION_CHANGES_V2':['인구변동','인구변동_조회계산'],'PUB_PLANET_POPULATION_V2':['행성인구관측','행성인구계산']},
'R30':{'PUB_CULTURE_DISTRIBUTION_V2':['문화분포','문화분포_조회계산'],'PUB_LANGUAGE_DISTRIBUTION_V2':['언어분포','언어분포_조회계산'],'PUB_GROUP_DISTRIBUTION_V2':['집단분포','집단분포_조회계산'],'PUB_REGIONAL_SOCIAL_V2':['사회지표','사회지표계산']},
'R40':{'PUB_RELIGION_DISTRIBUTION_V2':['종교분포','종교분포_조회계산'],'PUB_RELIGION_FACILITIES_V2':['종교시설관계']},
'R50':{'PUB_REGION_NATION_RELATIONS_V2':['지역국가관계','지역국가관계_조회계산']},
'R60':{'PUB_REGIONAL_ECONOMY_V2':['경제관측','경제관측_조회계산'],'PUB_PLANET_ECONOMY_V2':['행성경제관측','행성경제계산'],'PUB_RESOURCE_PRODUCTION_V2':['자원생산','자원생산_조회계산'],'PUB_INDUSTRY_V2':['산업활동','산업활동_조회계산'],'PUB_TRADE_V2':['지역간교역','지역간교역_조회계산'],'PUB_FACILITY_ACTUALS_V2':['시설실적']},
'R70':{'PUB_PLANET_PROPERTIES_V2':['행성기본값','행성기본값_계산'],'PUB_ENVIRONMENT_V2':['환경관측','환경관측_조회계산'],'PUB_RESOURCE_RESERVES_V2':['자원분포','자원분포_조회계산']},
}
providers=[]
for owner,contracts in PUB.items():
    for dataset,table_names in contracts.items():
        tt=[tables[(owner,n)] for n in table_names]
        headers=list(dict.fromkeys(h for t in tt for h in t['technical_headers']))
        join='left join derived columns to owner input by fixed primary key; unresolved keys/error rows exposed separately; never append a second copy of the input record'
        if dataset=='PUB_PLANET_PROPERTIES_V2':
            join='UNION ALL the independently keyed original-property records and calculated-property records, tagged source_record_kind=original/calculated. Do not left-join them: seven calculated property records have no input-row counterpart. Detect duplicate property_revision_id without silently merging, deleting, or promoting either record. Display comparison_record_id only as a relation.'
        p=dict(dataset_id=dataset,owner_file_code=owner,owner_spreadsheet_id=None,source_tables=table_names,join=join,primary_key_fields=tt[0]['primary_key_fields'],column_schema=[next(c for t in tt for c in t['fields'] if c['field_id']==h) for h in headers],technical_headers=headers,export_range='NOT_CREATED',contract_fields=COMMON_RULES['export_contract'],schema_version='V2.PH1.region-spec.1',release_id=None,online_test_status='미실행')
        p['no_loss_validation']={'key_contract':'each source table primary_key_fields matches publication key','before_publication':'reject duplicate derived key, unknown derived parent key, missing source key, or mismatched release; preserve every offending source record in diagnostic view','expected_ids':'owner-input ID set equals published source-record ID set, except planet properties which uses UNION of original and calculated property record IDs','row_order':'join by fixed key only, never by row number'}
        if dataset=='PUB_PLANET_PROPERTIES_V2':
            p['calculated_property_ids']=['equatorial_radius','polar_radius','ocean_share','land_area','ocean_area','orbital_period','ellipsoid_area']
            p['technical_headers'].append('source_record_kind')
            p['column_schema'].append({'field_id':'source_record_kind','type':'enum(original,calculated)','required':True,'role':'export_derived','rules':'constant from the record source table; never manual worldbuilding input'})
        assert all(t['primary_key_fields']==p['primary_key_fields'] for t in tt), (dataset,[t['primary_key_fields'] for t in tt])
        providers.append(p)
        for t in tt: t['export_dataset_id']=dataset

assert len({r['source_field_id'] for r in result})==len(result)
expected=[r for r in rows if (r['source_file_code']=='REG-V1' and r['source_sheet_name'] in MAP) or (r['source_file_code']=='NAT-V1' and r['source_sheet_name']=='03_영토_이력')]
assert {r['source_field_id'] for r in result}=={r['source_field_id'] for r in expected}
summary=dict(source_fields=len(result),source_sheets=len(scoped_sheets),destination_tables=len(tables),by_source_sheet=dict(Counter(r['source_sheet_name'] for r in result)),unmapped_fields=0,duplicate_source_field_ids=0,online_operations=0,migrated_rows=0,passed_operational_tests=0,status='PH1 세부 명세 작성; 정본 및 행별 채택 미확정; PH0 gate와 온라인 시험 대기')
with (OUT/'region_field_spec.csv').open('w',encoding='utf-8-sig',newline='') as h:
    w=csv.DictWriter(h,fieldnames=list(result[0])); w.writeheader(); w.writerows(result)
schema=dict(schema_version='V2.PH1.region-spec.1',prepared_date='2026-10-02',summary=summary,common_rules=COMMON_RULES,metric_routing=METRIC_ROUTE,calendar_property_routing=dict(owner='C00',properties=CALENDAR_PROPERTIES,physical_period_owner='R70',status='대조 전 후보'),source_inventory=inv,tables=list(tables.values()),providers=providers,required_providers={k:list(v) for k,v in PUB.items()},excluded_shared_sources=['REG 00_기준_메타','REG 99_검증','NAT 42_행성_기본속성_연결','NAT 43_지역_참조_연결','NAT 44_행성_연간지표_연결'],excluded_note='root C00/H90 또는 NAT 소비계약 담당; 누락 허용 아님',row_data_in_this_artifact=False)
for filename,data in [('region_schema.json',schema),('region_function_spec.json',dict(status='설계 명세; 미구현·미시험',functions=functions)),('region_issues.json',dict(status='결정대기 보존; 무단 정본 확정 없음',issues=issues))]:
    (OUT/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
