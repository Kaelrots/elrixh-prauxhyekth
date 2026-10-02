"""Build reviewable N10-N70 PH1 specifications; no source edits/network/imports.

The directory name is not an approval or phase-completion claim. Only specification
coverage is checked here. PH0 baseline comparison and all online tests remain gates.
"""
from pathlib import Path
import csv, json, re, hashlib
from collections import Counter, defaultdict

OUT = Path(__file__).resolve().parent
PH1 = OUT.parent
PACKAGE = PH1.parent.parent
fields = list(csv.DictReader((PH1/'actual_field_mapping_draft.csv').open(encoding='utf-8-sig')))
inventory = json.loads((PH1/'sheet_inventory.json').read_text(encoding='utf-8-sig'))
patterns = json.loads((PH1/'formula_patterns_and_dependencies.json').read_text(encoding='utf-8-sig'))
checklist = list(csv.DictReader((PACKAGE/'03_검증_체크리스트.csv').open(encoding='utf-8-sig')))
literal = list(csv.DictReader((PH1/'literal_cells.csv').open(encoding='utf-8-sig')))

# All source sheets in this shard are explicit. NAT 03 belongs to R50; NAT 00,
# 30, 40-44, 83, 89-91, 98-99 belong to common/H90 specification shards.
# code, dataset id, Korean label, existing record key, local functional rule ids
SHEETS = {
'01':('N10','NATION','국가기본','nation_id','N-ID,N-DEFAULT,N-HEX'),
'02':('N10','NATION_NAME_HISTORY','국호이력','name_id','N-ID,N-TIME,N-STATE'),
'04':('N10','CONSTITUTION_HISTORY','헌정국체이력','constitution_record_id','N-TIME,N-CONSTITUTION'),
'05':('N10','CAPITAL_HISTORY','수도이력','capital_record_id','N-TIME,N-CAPITAL'),
'06':('N20','INSTITUTION_HISTORY','기관구조이력','institution_history_id','N-TIME,N-INSTITUTION'),
'07':('N20','DISTRICT_RELATION','선거구계보','district_relation_id','N-LINEAGE,N-TIME'),
'10':('N40','NATION_POPULATION','국가인구관측','record_id','N-POP,N-OBSERVATION'),
'11':('N50','NATION_ECONOMY','국가경제관측','record_id','N-GDP,N-OBSERVATION'),
'12':('N50','ECONOMY_DERIVED','경제파생','query_key','N-GDP,N-GROWTH,N-PERCAPITA'),
'20':('N20','OFFICE','기관직위','office_id','N-ID,N-OFFICE'),
'21':('N20','OFFICE_TERM','공직임기','term_id','N-TIME,N-OFFICE_TERM,N-PERSON_REF'),
'22':('N20','PARTY','정당','party_id','N-ID,N-PARTY,N-HEX,N-LINEAGE'),
'23':('N20','ELECTION','선거','election_id','N-ELECTION,N-TURNOUT,N-SEATS,N-SENATE'),
'24':('N20','ELECTION_RESULT','선거결과','result_id','N-ELECTION_RESULT,N-SEATS'),
'25':('N20','DISTRICT_RESULT','선거구결과','record_id','N-ELECTION_RESULT,N-VOTE_DENOM,N-PERSON_REF'),
'26':('N20','ELECTION_SYSTEM','선거제도','system_id','N-ELECTION_SYSTEM,N-TIME'),
'27':('N20','PARTY_ANNUAL','정당연간','record_id','N-PARTY_ANNUAL,N-RANK,N-PERSON_REF'),
'28':('N20','ELECTION_COMPONENT','선거부문','component_id','N-VOTE_DENOM,N-TURNOUT,N-ELECTION_SYSTEM'),
'29':('N20','ELECTION_DERIVED','선거계산','result_id','N-ELECTION_RESULT,N-SEATS,N-VOTE_DENOM,N-RANK'),
'31':('N30','PERSON','인물','person_id','N-ID,N-PERSON'),
'32':('N20','PARTY_ROLE','정당직책','party_role_id','N-PARTY_ROLE'),
'33':('N20','PARTY_ROLE_TERM','정당지도부이력','party_role_term_id','N-TIME,N-LEADERSHIP,N-PERSON_REF'),
'34':('N20','PARTY_FACTION','정당계파','faction_id','N-TIME,N-LINEAGE'),
'35':('N30','ROYAL_STATUS','황실신분','royal_status_id','N-TIME,N-ROYAL,N-EXTERNAL_TERM'),
'36':('N30','KINSHIP','친족관계','relation_id','N-TIME,N-KINSHIP'),
'37':('N30','SUCCESSION','황위계승','succession_record_id','N-TIME,N-SUCCESSION,N-EXTERNAL_TERM'),
'38':('N20','PARTY_RELATION','정당관계','party_relation_id','N-LINEAGE,N-TIME'),
'39':('N20','DISTRICT','선거구','district_id','N-TIME,N-DISTRICT,N-LINEAGE'),
'80':('N20','POLITICS_ANNUAL','정치연간뷰','query_key','N-POLITICS_VIEW,N-QUERY'),
'81':('N20','ELECTION_ANNUAL','선거연간뷰','query_key','N-ELECTION_VIEW,N-QUERY'),
'82':('N50','ECONOMY_ANNUAL','경제연간뷰','query_key','N-GDP,N-GROWTH,N-PERCAPITA,N-QUERY'),
'84':('N20','ADMINISTRATION_ANNUAL','행정부연간뷰','query_key','N-ADMIN_VIEW,N-QUERY'),
'85':('N20','LEADERSHIP_ANNUAL','정당지도부뷰','query_key','N-LEADERSHIP_VIEW,N-QUERY'),
'86':('N30','ROYAL_ANNUAL','황실계승뷰','query_key','N-ROYAL_VIEW,N-QUERY'),
'87':('N30','SUCCESSION_AT_DATE','시점승계뷰','query_key','N-SUCCESSION_VIEW,N-QUERY'),
'88':('N30','KINSHIP_AT_DATE','친족조회','query_key','N-KINSHIP_VIEW,N-QUERY'),
}

# Stable field IDs remain readable and unambiguous; untranslated Korean fields
# intentionally retain their exact source meaning, rather than guessing synonyms.
COMMON = {'scope_id':'nation_id','루트':'route','기년':'era','연도':'year',
 '엘룬 표기':'name_elun','영어·기타 표기':'name_other','출처 ID':'source_id',
 '원문 위치':'source_locator','설정 상태':'setting_status','비고':'note',
 '시작연도':'start_year','시작월':'start_month','시작일':'start_day',
 '종료연도':'end_year','종료월':'end_month','종료일':'end_day','종료 상태':'end_status',
 '유효 종료연도':'query_end_year','시작일 순서':'query_start_order','종료일 순서':'query_end_order',
 '대표 HEX 코드':'color_hex','컬러칩':'color_chip','연도 키':'year_key',
 '오류':'error_messages','경고':'warning_messages','검증 상태':'validation_status',
 '참조 오류':'reference_errors','참조 경고':'reference_warnings','추가 검증':'additional_checks',
 '자료 점검':'data_checks','기록 점검':'record_checks',
 '한국어 이름':'name_ko','국가명':'name_ko','국호':'name_ko',
 '인물명':'person_name','인물명_자동':'person_name','person_id':'person_id',
 '지역 ID':'region_id','의회 office_id':'parliament_office_id','의회·기관 ID':'office_id',
 'party_id':'party_id','office_id':'office_id','system_id':'system_id',
 '총인구 (명)':'population','인구 정의':'population_definition','기준통화':'currency',
 '기준가격 기년':'price_base_era','기준가격 연도':'price_base_year',
 'GDP_명목':'gdp_nominal','GDP_실질':'gdp_real','GDP_미분류':'gdp_unclassified',
 '성별·인적 분류':'person_classification_raw','주요 신분·설명':'person_description_raw',
 '관련 term_id':'related_term_id','기준 황제 term_id':'emperor_term_id',
 '관련 event_id':'event_id','관련 황제 person_id':'related_emperor_person_id',
 '기준 황제 person_id':'emperor_person_id','기준 person_id':'subject_person_id',
 '상대 person_id':'object_person_id','후보 person_id':'candidate_person_id',
 '대표 person_id':'representative_person_id','선행 term_id':'previous_term_id',
 '승계 연계 term_id':'succession_term_id','관련 election_id':'election_id',
 '전신 office_id':'predecessor_office_id','후신 office_id':'successor_office_id',
 '전신 party_id':'predecessor_party_id','후신 party_id':'successor_party_id',
 '전신 district_id':'predecessor_district_id','후신 district_id':'successor_district_id',
 '선거구 ID':'district_id','효력연도':'effective_year','효력월':'effective_month','효력일':'effective_day',
 '행성 scope_id':'planet_id','수도 지역 ID':'capital_region_id','수도 지역 ID_기본값':'capital_region_id_raw',
 '상위 기관 ID':'parent_office_id','상위 기관 ID_기본값':'parent_office_id_default',
 '기관장 직위 ID':'head_office_id','기관장 직위 ID_기본값':'head_office_id_default',
 '기반 지역 ID':'base_region_id','적용 office_id':'applies_office_id','적용 의회·기관 ID':'applies_office_id',
 '선거구 계보 ID':'district_relation_id','선행 election_id':'previous_election_id','선행 임기 ID':'previous_party_role_term_id',
 '연정 party_id':'coalition_party_id','집권 party_id':'governing_party_id','이전 system_id':'previous_system_id',
 '전신 체제 ID':'predecessor_constitution_record_id','후신 체제 ID':'successor_constitution_record_id',
 '범위 ID':'allocation_scope_id','계보 parent_faction_id':'parent_faction_id_raw','계보 parent_party_id':'parent_party_id_raw',
 '상태':'setting_status','존속 시작기년':'start_era','존속 시작연도':'start_year','존속 종료연도':'end_year',
 '창당 기년':'start_era','창당연도':'start_year','해산연도':'end_year',
 '출생 기년':'birth_era','출생연도':'birth_year','출생월':'birth_month','출생일':'birth_day',
 '사망 기년':'death_era','사망연도':'death_year','사망월':'death_month','사망일':'death_day',
}

RULES = {}
def rule(rid, label, algorithm, tests='', owner='분야 파일', limits='온라인 구현·재계산·시험 미실행'):
    RULES[rid]={'rule_id':rid,'name':label,'semantic_contract':algorithm,'test_ids':tests.split(',') if tests else [],'execution_owner':owner,'execution_status':limits}
rule('N-ID','ID와 추적','기존 식별자 문자열을 그대로 보존. namespace+ID 충돌 검사. 입력 행 번호를 신규 영속 ID로 사용하지 않는다. 신규 이관행은 legacy_locator 매핑 레지스트리에서 한 번 생성한 고정 ID를 재사용. 이름만으로 인물을 통합하지 않음.','T-003,T-004,T-005')
rule('N-STATE','상태 분리','setting_status, value_status, validation_status, adoption_status, release_id를 별도 필드로 제공. 공란/초안/구버전/폐기를 정본으로 자동 승격하지 않음. 미실행을 정상으로 표시하지 않음.','T-077,T-078,T-079')
rule('N-TIME','기간·정밀도','원문 기년과 시작/종료 구성값을 보존. 정확한 기간은 [시작,종료). 연도만 아는 종료는 연간 조회에서 그 해를 포함하되 가상의 종료일을 저장하지 않는다. 종료 미상은 기록된 시작연도만 표시하고 무기한 지속과 구별. start/end_precision은 원래 입력의 정밀도만 표시. 기년 판본 미대응이면 절대일 순서를 계산하지 않음. 세계관 날짜에 DATE를 사용하지 않음.','T-015,T-016,T-017,T-018,T-019,T-020,T-021,T-022,T-023,T-024')
rule('N-QUERY','조회조건','nation_id, route, era/edition, 연도 범위 또는 시점, status_filter를 명시. 작업조회/정본조회/보존조회를 구별. 조회조건 입력만 허용하고 결과는 보호. 자료 없음/미입력/권한미확인/연결실패/부분합/초안/미실행을 분리. 원본 이동 링크와 release_id를 표시.','T-077,T-078,T-079,T-083,T-084')
rule('N-HEX','HEX와 색상','원문 HEX 문자열을 보존하고 #RRGGBB 문법을 검사. 표시 칩은 해당 HEX로 파생하며 새 색을 추정하지 않음.','T-084')
rule('N-DEFAULT','국가 기본값과 이력','기본 수도/체제는 미기간 원문 기본값으로 별도 보존한다. 기간이 있는 수도/헌정 이력에 같은 사실을 새로 수동 입력하지 않으며, 기본값을 모든 과거 연도에 적용하지 않는다. 상충하면 판본/결정대기 등록.','T-005,T-077')
rule('N-CONSTITUTION','헌정 이력','전신·후신 체제와 법적 근거·변경 사유를 보존. 운영기관 연결은 ID로만 보존하며 N20와 결합한 조회는 H90에서 수행.','T-003,T-077')
rule('N-CAPITAL','수도 이력','수도 종류별 병존 허용. 지역 ID는 R10의 유효키로 검사. 당시 시점의 지역명을 조회하며 역사기간을 국가 기본 수도로 대체하지 않음.','T-003,T-067')
rule('N-INSTITUTION','기관 개칭·신설','기관구조 이력의 office_id와 당시 명칭·상위기관·기관장직위·단계·부문을 기간별로 조회. 개칭은 동일 ID, 실제 신설·폐지는 별도 ID. 다중 전신/후신은 관계표 1연결1행.','T-061')
rule('N-OFFICE','기관·공직·선거권자','office_id를 유지하고 엔티티 종류/역할 종류를 별도로 보존. 기관·기관장직위·선출직 공직자·선거권자를 동일 공직으로 통합하지 않는다. 정원/동시재임 검사는 적용 가능한 종류에만. 황제 EMPEROR 및 두 종교 대표 ID는 N20에 유지.','T-053')
rule('N-OFFICE_TERM','공직 임기','황제 포함 모든 term_id는 N20만 입력. office_id/person_id/party_id/관련 선거/선행 임기/승계 임기를 보존. 대행 종료와 정식 승계는 정확 경계의 별도 term_id. 동시정원 및 기간 중복 검사를 역할 종류에 맞춰 수행.','T-052,T-065,T-066')
rule('N-PERSON_REF','인물 참조','N20은 N30 PUB_PERSON_V2의 person_id로 이름을 한 번 읽는다. 이름/행순서로 조인하지 않음. N30의 N20 재import 금지. 이름 조회 실패는 연결 상태 또는 미존재 ID 오류로 표시.','T-068,T-069,T-070')
rule('N-PARTY','정당·연정·무소속','party_kind, 원어명_기존 보존, 약칭·이념·활동상태·기반지역·HEX 유지. 계보 parent_party_id와 합당·분당 원문 메모는 관계 후보를 표시하고 확정된 다대다 관계만 PARTY_RELATION에 이관.','T-059,T-060')
rule('N-LINEAGE','다대다 계보','전신/후신/부모 참조를 1연결1행 관계로 정규화. 명확한 단일 ID는 관계 생성 가능; 쉼표·자유문장 원문은 raw_relation과 parse_status에 보존하고 해석대기. 미확인 동일기관/정당/선거구 자동 병합 금지.','T-060,T-061')
rule('N-ELECTION','선거 사건','정기/보궐/재선거, 선행 election_id, 사유·예외 근거·적용 system_id·의석범위·클래스를 보존. 주기만으로 역사 선거·결과 생성 금지.','T-051,T-057,T-058')
rule('N-ELECTION_SYSTEM','선거제도 개정판','기존 system_id를 유지하고 이전 system_id/기간/정수/지역구·비례·기타 의석/봉쇄/배분/선거권·피선거권연령/주기/임기/예외를 별도로 보존. 해당 선거에 연결된 개정판을 사용하며 최신 제도를 소급하지 않음.','T-057')
rule('N-TURNOUT','투표율 직접·산출·채택','투표자/선거인으로 산출하되 분모>0 및 동일 표종·회차·범위를 검사. 직접값 우선, 직접값 없을 때만 유효한 산출값을 채택하는 V1 동작을 명시. 채택 근거·차이(직접-산출)·허용오차를 노출. 값 충돌을 숨기지 않음.','T-055,T-056')
rule('N-VOTE_DENOM','부문별 분모','component_id가 있으면 같은 election_id의 부문·표종·회차·범위와 유효표 분모 사용. 대표표종 분모로 임의 대체 금지. component_id 없을 때만 선거 대표표종과 결과 의미가 일치하는지 검사 후 대표분모 사용.','T-055,T-056')
rule('N-ELECTION_RESULT','선거 결과','직접 득표율/득표수/산출 득표율/채택율을 독립 표시. 직접율 우선의 현행 동작 보존, 차이 대조. result_id 및 election_id+party_id+component_id 중복 검사. 후보 person_id, district_id, region_id, 당선여부·의석·회차 보존.','T-054,T-055,T-056')
rule('N-SEATS','의석 의미·분모','전체 정수, 이번 대상, 부문별 배분, 이번 당선, 선거후 보유를 분리. 당선 직접값이 있으면 우선, 없으면 지역구+비례+기타 세 값이 모두 있을 때만 합계 채택. 당선비율=당선/해당배분, 보유비율=보유/기관전체. 누락 부문은 0 처리하지 않음.','T-054')
rule('N-RANK','원내 공동순위','같은 국가·루트·기년·의회·기준시점 또는 선거후 총보유의석에서 정당별 중복 제거 후 비교. 이번 당선의석/득표율로 대체하지 않음. 정당·연정·무소속 구분에 맞는 순위대상만 포함하고 동수는 1,1,3 경쟁순위.','T-059')
rule('N-SENATE','상원 클래스','V1 정기 다음클래스의 코드북 순서를 보존. 재선거·특례가 다음 정기 순서를 변경한다고 추정하지 않음. 클래스 미입력은 자동확정하지 않음.','T-058')
rule('N-PARTY_ANNUAL','정당 연간 스냅샷','의회 office_id·기준시점·보유의석·대표자 스냅샷을 보존. 지도부 상세 이력과 일치 검사하되 해당 연간값을 새 임기 사실로 생성하지 않음.','T-059')
rule('N-PARTY_ROLE','정당직책','공통 직책과 특정정당 전용 직책, 적용 의회/기관, 지역·계파 여부, 동시정원을 독립 보존. office_id와 party_role_id는 별개.','T-053')
rule('N-LEADERSHIP','지도부 기간','party_role_id·party_id·person_id·의회·지역·계파·선임 방식·선행임기·근거를 보존. 공동대표를 단일대표로 축소하지 않음.','T-052,T-059')
rule('N-DISTRICT','선거구','district_id와 region_id를 구별. 적용 기관·선출인원·선거구 종류·기간·계보·경계근거를 보존. 지역 경계와 선거구 경계 동일 추정 금지.','T-060')
rule('N-PERSON','인물','기존 person_id·세 언어 표기·출생/사망의 별도 기년 및 정밀도·인물상태 유지. 성별·인적분류 원문은 분류 사전 결정 전 보존하고 종족 또는 성별로 임의 분해하지 않음. 주요 신분 설명은 설명이며 재위/승계의 원본이 아님.','T-062,T-063')
rule('N-ROYAL','황실신분','royal_status_id별 코드·표시명·기간·시작/종료 사유·관련 황제인물·term_id 보존. 신분 기록을 공직 재위로 중복입력하지 않음. 연간은 연중 이력, 시점은 해당 날짜 유효 신분.','T-065,T-067')
rule('N-EXTERNAL_TERM','황제 임기 교차검증','N30은 관련 term_id 및 emperor_term_id를 문자열 외래키로 보존하고 검사상태를 통합 검증 대상으로 표시. 실제 존재, EMPEROR 여부, 인물·루트·기간 정합성은 H90에서 N20와 결합해 검사. N30은 N20를 import하지 않음.','T-065,T-066,T-069','H90; N30은 안내만')
rule('N-KINSHIP','친족','방향 있는 기준/상대 person_id·관계종류·친생/입양·법적상태·기간을 보존. 역조회는 코드북에 정의된 역관계만 계산, 모르면 미정. 역방향 원자료를 자동추가하지 않음. 친족으로 승계권/황실신분 추정 금지.','T-062,T-063')
rule('N-SUCCESSION','황위계승','권리·순위·지명상태·지명유형·황태자녀 여부·법적근거·예외·사유·event_id·기준황제term_id를 독립 보존. 순위 미상은 정렬표시만 하단, 가상순위 입력 금지. 박탈/포기/복권은 기간이 다른 이력.','T-063,T-064,T-065,T-066')
rule('N-POLITICS_VIEW','정치 연간','황제/최고평의회장/총의장/대법원장/준비기금위원회장/최고평의회부의장/제국도교선출대표/평신도선거권자를 N20 임기와 N30 인물로 표시. 국호 결합은 H90 제공 화면에서 처리.','T-053,T-065')
rule('N-ELECTION_VIEW','선거 연간','연도별 하원·상원·기타 선거와 하원/상원 결과를 현존 선거사건만으로 표시. 정기·보궐·재선거는 별도 사건 유지.','T-051')
rule('N-ADMIN_VIEW','행정부 연간','최고평의회 의장/부의장/각부각처 기관장/당시 기관구조를 당시 기관명과 상위기관 기준으로 조회. 행정부 출력여부는 원문 설정을 사용.','T-061')
rule('N-LEADERSHIP_VIEW','정당 지도부 조회','정당필터를 적용하여 당대표·공동대표/원내대표/주요당직/지역대표/계파지도부/전체지도부를 구분. 이름 대신 각 임기 ID를 함께 제공.','T-059')
rule('N-ROYAL_VIEW','황실 연간','N30은 황후/황태자녀/황자녀/구성원/제1순위/지명자/권리순위를 자기 이력에서 조회. 황제 공직재위·수도·헌정 결합은 H90만 수행.','T-065,T-067,T-069')
rule('N-SUCCESSION_VIEW','시점 승계','국가·루트·기년·날짜·기준황제·상태필터로 SUCCESSION을 조회. 순위와 지명 독립표시, 무순위 하단. N30 내 인물명만 조회하고 실제 재위는 H90 검증 링크.','T-063,T-064,T-066')
rule('N-KINSHIP_VIEW','시점 양방향 친족','선택 인물이 기준 또는 상대인 관계를 한 번만 조회. 기준이면 저장방향, 상대이면 역관계·반대인물 표시. 친생/입양/법적상태/기간/상태필터 유지.','T-062')
rule('N-OBSERVATION','관측키와 후보','기존행별 record_id 고정 발급. entity+route+era+year+metric+unit+definition(+currency/price base)로 비교키 구성. 여러 출처 후보를 보존하고 채택표로 선택. 원문 숫자 문자열·근사 숫자·단위·값상태·출처를 분리.','T-031,T-032,T-033,T-045,T-050')
rule('N-POP','국가인구','직접 인구 관측과 R50 통치범위/R20 동일정의 지역합계는 별개 dataset 및 origin_kind. 부분통치를 면적비로 인구에 배분하지 않음. 누락/중첩/정의불일치면 부분합 또는 계산보류.','T-033,T-035,T-041')
rule('N-GDP','GDP 정규화','11 E/F/G를 metric_id=GDP, price_type=명목/실질/미분류인 별도 관측으로 unpivot. 입력된 0은 보존, 빈 셀은 관측 생성하지 않음. 통화·기준가격기년/연도·미분류검토상태·상태·출처를 함께 복사. 표시GDP는 명목→실질→미분류 우선 규칙이 조회 선택임을 표기하며 원자료 채택과 분리.','T-045,T-049,T-050')
rule('N-GROWTH','연간 증가율','동일 기준의 바로 전 연도 값이 정확히 하나 선택되고 전기>0인 경우 당기/전기-1. 누락 연도 보간 금지, 2년 증감을 1년 성장률로 부르지 않음. 실질GDP는 동일 통화·가격기준, 인구는 동일 정의. 실패이유 별도 표시.','T-045,T-047,T-048')
rule('N-PERCAPITA','1인당 GDP','N40에서 채택된 동일 국가·루트·기년/판본·연도·정의의 양수 인구만 사용. 적합한 GDP/인구를 계산하고 GDP 가격분류·통화·양쪽 원본 ID를 표시. 미입력/불일치/0분모는 계산불가 이유를 표시.','T-046')
rule('N-EMPTY','빈 분야','N40 사회/구성, N50 재정/고용/물가/무역, N60/N70은 스키마·코드북·검증·입력안내를 준비하고 사실행 0개를 유지. 교육/문화/제도/재정 값을 창작하지 않음.','T-078')
rule('N-RANGE','범위 확장','dataset별 active_row_count/capacity/schema_version 관리. 확장시 입력·계산·검증·PUB·소비 REF의 범위를 한 변경단위로 갱신. capacity+1 경계시험과 원복 증거를 남기기 전 검증완료 금지.','T-072,T-073')
rule('N-CONNECT','연결','실제 V2 ID가 등록된 PUB만 읽고 파일당 제공표를 한 번 REF로 수신. 데이터와 connection_status/schema_version/release_id/원본변경확인시각을 별도 제공. V1 주소·DUMMYFUNCTION·IFERROR(...,0)로 연결실패를 정상화하지 않음.','T-068,T-069,T-070,T-071,T-072,T-079,T-083')
RULES['N-ID']['test_ids']=['T-006','T-009','T-010','T-011','T-012','T-013']
RULES['N-TIME']['test_ids']=['T-016','T-017','T-018','T-019','T-020','T-021','T-022','T-023','T-025']
RULES['N-DEFAULT']['test_ids']=['T-013','T-015','T-077']
RULES['N-EMPTY']['test_ids']=['T-008','T-078']
RULES['N-OBSERVATION']['test_ids']=['T-014','T-031','T-033','T-045','T-050']
RULES['N-POP']['test_ids']=['T-027','T-028','T-029','T-030','T-033','T-035','T-041']
RULES['N-RANK']['semantic_contract']+=' 원내순위에서 연정·무소속·0석은 제외하는 기존 규칙을 유지.'
RULES['N-SEATS']['semantic_contract']+=' 기관 총의석 직접값이 숫자이면 실제 0도 우선 채택하고, 없을 때 해당 제도의 총의석 사용. 부분선거 대상 의석은 직접입력하며 1/3 등 임의 반올림 금지.'
RULES['N-ELECTION_SYSTEM']['semantic_contract']+=' 부문별 system_id가 공란인 경우 해당 선거 system_id를 사용하고 채택 출처를 표시.'
RULES['N-VOTE_DENOM']['semantic_contract']+=' 본선·결선은 별도 component_id. 미당선 회차의 당선의석 0은 직접입력된 때만 유지.'

def dtype(field, label):
    if field.endswith('_id') or field in ('record_id','source_id','nation_id'): return 'text_id'
    if field=='color_hex': return 'hex_text'
    if ('여부' in label or field.endswith('_flag')): return 'boolean_nullable'
    if ('연도' in label or label.endswith('월') or label.endswith('일') or '순위' in label or field in ('year','start_year','end_year','effective_year')): return 'integer_nullable'
    if any(x in label for x in ('GDP','인구','득표수','표수','의석','선거인수','투표자수','당원수','정원','선출인원','선출 인원','임기_년','주기_년')) and not any(x in label for x in ('정의','범위','상태','방식','기준','비율','증감률','성장률','분류','점검')): return 'decimal_nullable_with_raw'
    if any(x in label for x in ('율','비율')): return 'ratio_nullable'
    return 'text_nullable'

def canonical(label):
    return COMMON.get(label, label)

def input_validation(field,label,typ):
    rules=['공란을 임의값으로 대체하지 않음','원문 setting_status 보존']
    if typ=='text_id': rules+=['식별자 원문 대소문자·접두어 보존','비어 있지 않은 참조만 존재/namespace 검사']
    if typ=='hex_text': rules+=['^#[0-9A-Fa-f]{6}$; 표시색과 코드 일치']
    if typ=='ratio_nullable': rules+=['저장비율 0..1; 73.45를 0.7345로 침묵 변환 금지']
    if typ=='boolean_nullable': rules+=['실제 레코드의 참/거짓만 사실; ID 없는 기본 FALSE는 행 생성 제외']
    if label.endswith('월'): rules+=['1..48 또는 미상']
    if label.endswith('일'): rules+=['1..30 또는 미상']
    if '연도' in label or field=='year': rules+=['제3기 0년 허용; 기년 판본 별도 검사']
    return '; '.join(rules)

def refs_for(field,label):
    if field in ('political_office_id','political_term_id'):
        return 'H90에서 N20.OFFICE.office_id / N20.OFFICE_TERM.term_id 교차검증. N70은 값/하이퍼링크만 보존하고 N20 import 금지.'
    if field in ('person_id','candidate_person_id','representative_person_id','subject_person_id','object_person_id','related_emperor_person_id','emperor_person_id'): return 'N30.PERSON.person_id'
    if field in ('related_term_id','emperor_term_id'): return 'H90에서 N20.OFFICE_TERM.term_id 존재·기간 검사; N30 import 금지'
    if field=='previous_party_role_term_id': return 'N20.PARTY_ROLE_TERM.party_role_term_id'
    if field in ('previous_term_id','succession_term_id'): return 'N20.OFFICE_TERM.term_id'
    if field=='event_id': return 'C00.수동사건.event_id; 외부 조합검사 H90'
    if field=='source_id': return 'C00.출처레지스트리.source_id'
    if field=='nation_id': return 'C00.국가식별목록.nation_id'
    if field=='planet_id': return 'R10.지역목록.region_id 중 행성; 물리값 재입력 금지'
    if field=='previous_party_role_term_id': return 'N20.PARTY_ROLE_TERM.party_role_term_id'
    if field in ('predecessor_constitution_record_id','successor_constitution_record_id'): return 'N10.CONSTITUTION_HISTORY.constitution_record_id'
    if field=='allocation_scope_id': return '배분 범위 종류에 따른 R10.region_id/N20.district_id; 다형성 참조 검사'
    if field=='previous_system_id': return 'N20.ELECTION_SYSTEM.system_id'
    if field=='previous_election_id': return 'N20.ELECTION.election_id'
    if field=='parent_office_id_default' or field=='head_office_id_default': return 'N20.OFFICE.office_id; 미기간 기본값과 기간이력 구별'
    if field=='region_id' or '지역 ID' in label: return 'R10.지역목록.region_id'
    if field!='office_id' and 'office_id' in field: return 'N20.OFFICE.office_id'
    if field!='party_id' and 'party_id' in field: return 'N20.PARTY.party_id'
    if field!='district_id' and 'district_id' in field: return 'N20.DISTRICT.district_id'
    return ''

spec=[]
tables={}
issues=[]
assigned=[]
for src in fields:
    n=src['source_sheet_name'][:2]
    if src['source_file_code']!='NAT-V1' or n not in SHEETS: continue
    assigned.append(src)
    code,ds,label,pk,rules=SHEETS[n]
    field=canonical(src['source_field'])
    role=src['source_role']
    isview=(int(n)>=80 or n in ('12','29'))
    if role=='validation': role='validation'
    elif isview: role='query_output' if int(n)>=80 else 'calculation'
    elif role=='formula': role='calculation'
    elif role=='input': role='input'
    else: role='review_required'
    transform='원문 의미·값·ID를 해당 입력 필드로 이관. 명시하지 않은 판본 채택/값 추정 없음.'
    review='명세작성; 데이터이관/온라인검증 미실행'
    issues_for=[]
    if role in ('calculation','query_output'):
        transform='기능 계약에 따라 V2 입력/REF로 재구현. 원문 수식·캐시는 비교 증거이며 값 이관 대상 아님.'
    if role=='validation':
        transform='V2 활성 레코드에 해당 검증 의미를 재구현. 이전 정상/경고/오류 결과를 새 시험 결과로 복사하지 않음.'
    # Canonical time-field conversion keeps precision and edition separate.
    if src['source_field']=='기년' and not isview:
        transform+=' era 원문을 보존하고 시작/종료기년·기년판본 확정치는 별도 열; 명시되지 않은 대응을 창작하지 않음.'
    if n=='11' and src['source_column'] in ('E','F','G'):
        field='value'; transform='비어 있지 않은 셀마다 고정 record_id의 GDP 관측을 생성: metric_id=GDP, price_type='+{'E':'명목','F':'실질','G':'미분류'}[src['source_column']]+'. 원문 숫자와 정밀도 보존. 0은 실제 입력일 때 유지.'
    elif n=='11' and src['source_column']!='O':
        transform+=' 같은 원본 행에서 생성되는 명목/실질/미분류 관측 각각에 상응 메타데이터로 연결.'
    if n=='10' and src['source_column']=='L':
        code,ds,label,field,role='N40','UNRESOLVED_FIELDS','미해석 필드','legacy_population_extra_column_L','review_required'
        transform='실제 헤더는 1열이며 본문 literal/formula 0개. 의미를 추정하지 않는다. source_field_id·헤더·공란 구조를 결정대기표와 연결. 운영 인구값/분모에 쓰지 않음.'
        issues_for=['N-ISSUE-001']; review='결정대기: 필드 의미 미정; 명세 대응처 지정만 완료'
    if n=='80' and src['source_column']=='C':
        code,ds,label='H90','NATION_POLITICS_VIEW','국가정치결합뷰'; transform='N10 국호이력을 H90에서 기간·루트·상태필터로 결합. N20에서 N10를 새 import하지 않음.'
    if n=='86' and src['source_column'] in ('C','K','L'):
        code,ds,label='H90','ROYAL_REIGN_COMPOSITE','황제재위결합뷰'; transform='H90에서 '+{'C':'N20 황제 공직임기','K':'N10 수도이력','L':'N10 헌정국체이력'}[src['source_column']]+'를 N30 황실/계승과 결합. N30으로 역import 금지.'
    if n in ('87','88'):
        transform+=' 원문 A6의 FILTER/HSTACK spill 출력임을 확인. 관측기 input/mixed 분류를 실제 입력 사실로 사용하지 않음. 1~4행은 별도 조회안내/컨트롤로 재작성.'
    if n in ('20','21'):
        transform+=' 종교 관련 두 대표 역할 및 황제의 정치적 원본은 N20 유지.'
    if n=='31' and src['source_column']=='M':
        transform+=' 원문 하나에 합쳐진 성별·인적분류를 근거 없이 종족/성별 코드로 분리하지 않음.'
        issues_for=['N-ISSUE-002']
    if n=='01' and src['source_column'] in ('I','J'):
        ds,label='NATION_UNDATED_DEFAULT','국가미기간기본값'; field={'I':'capital_region_id_raw','J':'regime_raw'}[src['source_column']]
        transform='미기간 기본값으로 보존하되 새 기간 이력으로 추정 생성하지 않음. 기간 이력의 확정 입력처는 CAPITAL_HISTORY/CONSTITUTION_HISTORY. 충돌은 결정대기.'
    # Complex predecessor/successor fields are moved to relation stores, never
    # silently joined by a comma-separated list as the active relation model.
    relation_route=None
    if n in ('06','20') and src['source_field'] in ('전신 office_id','후신 office_id'):
        relation_route=('OFFICE_RELATION','기관전후관계','predecessor_office_id' if '전신' in src['source_field'] else 'successor_office_id')
    if n=='22' and src['source_column']=='F': relation_route=('PARTY_RELATION','정당관계','parent_party_id_raw')
    if n=='34' and src['source_column']=='P': relation_route=('FACTION_RELATION','계파관계','parent_faction_id_raw')
    if n=='39' and src['source_column'] in ('S','T'): relation_route=('DISTRICT_RELATION','선거구계보',field)
    if relation_route:
        ds,label,field=relation_route
        pk={'OFFICE_RELATION':'office_relation_id','PARTY_RELATION':'party_relation_id','FACTION_RELATION':'faction_relation_id','DISTRICT_RELATION':'district_relation_id'}[ds]
        transform='식별 가능한 단일 참조는 기존 source_id/행의 개체 ID와 1연결1행 관계로 이관. 기존 명시 계보표의 같은 관계와 대조해 중복 통합, 출처 목록은 유지. 다중·자유문장 값은 raw_relation/parse_status=결정대기. 전후 방향 보존.'
    prefix='IN' if role=='input' else 'CHECK' if role=='validation' else 'REVIEW' if role=='review_required' else 'VIEW' if role=='query_output' else 'CALC'
    table=f'{prefix}_{ds}'
    typ=dtype(field,src['source_field'])
    pids=[x['pattern_id'] for x in patterns if x['source_file_code']=='NAT-V1' and x['source_sheet_id']==int(src['source_sheet_id']) and re.sub(r'\d','',x['example_cell'])==src['source_column']]
    row={k:src[k] for k in ('source_file_code','source_file_id','source_sheet_id','source_sheet_name','source_column','source_field_id','source_field','source_type','source_role','source_role_evidence','literal_cells','formula_cells','default_false_cells','nonempty_formula_cache_cells','map_id','preservation_location')}
    row.update(target_file_code=code,target_table=table,target_field=field,target_display_name=src['source_field'],target_data_type=typ,target_role=role,canonical_dataset_id=ds,input_owner=code if role=='input' else '',record_key=pk,transformation=transform,foreign_key_contract=refs_for(field,src['source_field']),validation_contract=input_validation(field,src['source_field'],typ),function_rule_ids=rules+',N-STATE,N-RANGE,N-CONNECT',source_formula_pattern_ids=';'.join(pids),publish_table=f'PUB_{ds}_V2' if role in ('input','calculation','query_output') else '',issue_ids=';'.join(issues_for),spec_status=review,migration_status='미실행',online_test_status='미실행')
    if field!=pk and field in {'office_id','party_id','system_id','election_id','component_id','district_id','faction_id','party_role_id','district_relation_id'}:
        ref_ds={'office_id':'OFFICE','party_id':'PARTY','system_id':'ELECTION_SYSTEM','election_id':'ELECTION','component_id':'ELECTION_COMPONENT','district_id':'DISTRICT','faction_id':'PARTY_FACTION','party_role_id':'PARTY_ROLE','district_relation_id':'DISTRICT_RELATION'}[field]
        row['foreign_key_contract']=f'N20.{ref_ds}.{field}'
    if field==pk and field!='nation_id': row['foreign_key_contract']=''
    row['targets_json']=json.dumps([{'file_code':code,'table':table,'field':field,'role':role,'rule':transform}],ensure_ascii=False)
    row['test_ids']=';'.join(sorted({tid for rid in row['function_rule_ids'].split(',') for tid in RULES[rid]['test_ids']}))
    spec.append(row)
    key=(code,table)
    if key not in tables:
        tables[key]={'file_code':code,'table_id':table,'label_ko':label,'role':role,'canonical_dataset_id':ds,'record_key':pk,'source_sheets':[],'fields':[],'source_candidate_rows':{},'implemented':False}
    t=tables[key]
    if src['source_sheet_name'] not in t['source_sheets']: t['source_sheets'].append(src['source_sheet_name'])
    if not any(f['field_id']==field for f in t['fields']):
        t['fields'].append({'field_id':field,'display_name':src['source_field'],'data_type':typ,'source_field_ids':[src['source_field_id']],'rules':row['validation_contract'],'foreign_key':row['foreign_key_contract']})
    else:
        next(f for f in t['fields'] if f['field_id']==field)['source_field_ids'].append(src['source_field_id'])

# Required, genuinely usable new schemas; all fact rows remain empty.
NEW = {
 ('N40','NATION_POPULATION_COMPOSITION','국가인구구성'): [('record_id','text_id'),('nation_id','text_id'),('route','text'),('era','text'),('year','integer'),('population_record_id','text_id'),('classification_axis_id','text_id'),('group_id','text_id'),('population','decimal_nullable_with_raw'),('ratio_direct','ratio_nullable'),('denominator_definition','text'),('denominator_record_id','text_id'),('multiple_response','boolean_nullable'),('coverage_status','text')],
 ('N40','NATION_SOCIAL_METRIC','국가사회지표'): [('record_id','text_id'),('nation_id','text_id'),('route','text'),('era','text'),('year','integer'),('metric_id','text_id'),('value','decimal_nullable_with_raw'),('unit_id','text_id'),('target_population_definition','text'),('denominator_record_id','text_id'),('observation_period','text'),('method','text')],
 ('N50','NATION_FISCAL_METRIC','국가재정관측'): [('record_id','text_id'),('nation_id','text_id'),('route','text'),('era','text'),('start_year','integer_nullable'),('start_month','integer_nullable'),('start_day','integer_nullable'),('end_year','integer_nullable'),('end_month','integer_nullable'),('end_day','integer_nullable'),('metric_id','text_id'),('account_scope','text'),('flow_or_stock','text'),('value','decimal_nullable_with_raw'),('currency','text'),('price_type','text'),('budget_or_actual','text'),('accounting_basis','text')],
 ('N50','NATION_PRICE_METRIC','국가물가지표'): [('record_id','text_id'),('nation_id','text_id'),('route','text'),('era','text'),('year','integer'),('metric_id','text_id'),('basket_definition','text'),('base_era','text'),('base_year','integer'),('value','decimal_nullable_with_raw'),('unit_id','text_id')],
 ('N50','NATION_EMPLOYMENT_METRIC','국가고용지표'): [('record_id','text_id'),('nation_id','text_id'),('route','text'),('era','text'),('year','integer'),('metric_id','text_id'),('population_definition','text'),('age_scope','text'),('value','decimal_nullable_with_raw'),('unit_id','text_id'),('denominator_record_id','text_id')],
 ('N50','NATION_TRADE_METRIC','국가무역관측'): [('record_id','text_id'),('nation_id','text_id'),('route','text'),('era','text'),('year','integer'),('partner_nation_id','text_id'),('flow_direction','text'),('commodity_id','text_id'),('metric_id','text_id'),('value','decimal_nullable_with_raw'),('unit_id','text_id'),('currency','text'),('valuation_basis','text')],
 ('N60','NATION_CULTURE_RELATION','국가문화관계'): [('relation_id','text_id'),('nation_id','text_id'),('route','text'),('culture_id','text_id'),('relation_type','text'),('scope_definition','text'),('legal_basis','text')],
 ('N60','LANGUAGE_STATUS_HISTORY','언어지위이력'): [('language_status_id','text_id'),('nation_id','text_id'),('route','text'),('language_id','text_id'),('language_status_code','text'),('legal_or_practice','text'),('scope_definition','text'),('legal_basis','text')],
 ('N60','CULTURAL_INSTITUTION_HISTORY','문화제도이력'): [('cultural_institution_record_id','text_id'),('nation_id','text_id'),('route','text'),('institution_or_policy_name_raw','text'),('culture_id','text_id'),('language_id','text_id'),('heritage_reference','text'),('scope_definition','text'),('legal_basis','text')],
 ('N70','NATION_RELIGION_RELATION','국가종교관계'): [('relation_id','text_id'),('nation_id','text_id'),('route','text'),('religion_id','text_id'),('denomination_id','text_id'),('legal_status_code','text'),('relation_type','text'),('scope_definition','text'),('legal_basis','text')],
 ('N70','RELIGIOUS_ORGANIZATION','교단조직'): [('religious_org_id','text_id'),('nation_id','text_id'),('route','text'),('religion_id','text_id'),('denomination_id','text_id'),('name_ko','text'),('name_elun','text'),('name_other','text'),('legal_entity_kind','text'),('parent_religious_org_id','text_id'),('headquarters_region_id','text_id'),('legal_basis','text')],
 ('N70','RELIGIOUS_AFFAIRS_HISTORY','교무이력'): [('affairs_record_id','text_id'),('nation_id','text_id'),('route','text'),('religious_org_id','text_id'),('person_id','text_id'),('affairs_role_name_raw','text'),('affairs_relation_type','text'),('political_office_id','text_id'),('political_term_id','text_id'),('legal_basis','text')],
}
ENVELOPE=[('legacy_locator','text'),('source_snapshot_id','text'),('schema_version','text'),('release_id','text'),('value_status','text'),('generation_method','text'),('adoption_status','text'),('setting_status','text'),('source_id','text_id'),('source_locator','text'),('note','text')]
TIME_ENVELOPE=[('start_era','text'),('start_year','integer_nullable'),('start_month','integer_nullable'),('start_day','integer_nullable'),('start_precision','text'),('end_era','text'),('end_year','integer_nullable'),('end_month','integer_nullable'),('end_day','integer_nullable'),('end_precision','text'),('end_status','text'),('calendar_revision','text')]
for (code,ds,label),cols in NEW.items():
    allcols=cols+ENVELOPE+(TIME_ENVELOPE if code in ('N60','N70') else [])
    unique=list(dict(allcols).items())
    tables[(code,'IN_'+ds)]={'file_code':code,'table_id':'IN_'+ds,'label_ko':label,'role':'input','canonical_dataset_id':ds,'record_key':cols[0][0],'source_sheets':[],'fields':[{'field_id':f,'display_name':f,'data_type':ty,'source_field_ids':[],'rules':'N-EMPTY,N-ID,N-STATE,N-OBSERVATION'+(',N-TIME' if code in ('N60','N70') else ''),'foreign_key':refs_for(f,f)} for f,ty in unique],'fact_row_count':0,'implemented':False,'empty_schema_instructions':'헤더·자료형·출처·코드북 검증·입력 안내만 준비. 예시행은 TEST 사본에만 배치. 자료 없음 표시.','domain_boundaries':{'N40':'고용 원본은 N50; 문화/종교의 분포는 R30/R40, 국가제도는 N60/N70.','N50':'GDP를 근거로 재정/무역/고용 값을 역산하지 않음.','N60':'대표문화/법정공용어를 주민 다수문화/모어 비율로 해석하지 않음.','N70':'religion_id와 교단 법인 religious_org_id 구별. 정치 공직임기는 N20 단일원본; 교무는 별개 사실.'}[code]}

# Technical envelope, time precision and local keys are actual schema additions,
# rather than claiming old fields already carry those semantics.
for t in list(tables.values()):
    if t['role']!='input':
        for f,ty in [(t['record_key'],'text_id'),('source_record_id','text_id'),('validation_status','text'),('connection_status','text'),('schema_version','text'),('release_id','text')]:
            if not any(x['field_id']==f for x in t['fields']):
                t['fields'].append({'field_id':f,'display_name':f,'data_type':ty,'source_field_ids':[],'rules':'입력 불가; 원본 레코드 키와 조회상태로 결합','foreign_key':''})
        continue
    ids={f['field_id'] for f in t['fields']}
    extras=list(ENVELOPE)
    if any(f in ids for f in ('start_year','end_year','era')): extras+=TIME_ENVELOPE
    if t['record_key'] not in ids: extras.insert(0,(t['record_key'],'text_id'))
    if t['canonical_dataset_id'] in ('NATION_POPULATION','NATION_ECONOMY'):
        extras += [('raw_value_text','text'),('numeric_precision_status','text'),('metric_id','text_id'),('unit_id','text_id'),('origin_kind','text'),('candidate_group_id','text_id'),('selection_reason','text')]
    if t['canonical_dataset_id']=='NATION_ECONOMY': extras += [('price_type','text')]
    if t['canonical_dataset_id']=='PERSON': extras += [('birth_precision','text'),('death_precision','text'),('calendar_revision','text')]
    if t['canonical_dataset_id'] in ('OFFICE_RELATION','PARTY_RELATION','FACTION_RELATION','DISTRICT_RELATION'):
        canonical_pk={'OFFICE_RELATION':'office_relation_id','PARTY_RELATION':'party_relation_id','FACTION_RELATION':'faction_relation_id','DISTRICT_RELATION':'district_relation_id'}[t['canonical_dataset_id']]
        relation_entity={'OFFICE_RELATION':'office','PARTY_RELATION':'party','FACTION_RELATION':'faction','DISTRICT_RELATION':'district'}[t['canonical_dataset_id']]
        extras += [(canonical_pk,'text_id'),(f'predecessor_{relation_entity}_id','text_id'),(f'successor_{relation_entity}_id','text_id'),('relation_type','text'),('raw_relation','text'),('parse_status','text'),('source_record_id','text_id')]
        t['record_key']=canonical_pk
    for f,ty in extras:
        if f not in ids:
            t['fields'].append({'field_id':f,'display_name':f,'data_type':ty,'source_field_ids':[],'rules':'이관 메타/미정 신규 필드. 세계관 사실을 자동 생성하지 않음.','foreign_key':refs_for(f,f)});ids.add(f)
    t['publish_contract']={'table_id':f"PUB_{t['canonical_dataset_id']}_V2",'includes':'위 입력 필드와 record_id/setting_status/adoption_status/validation_status/source_id/source_locator/schema_version/release_id를 포함; 오류행은 표시를 붙여 보존하고 정상조회 채택만 제한','data_rows_only':True,'metadata_separate':True,'status':'설계만 존재'}
    t['row_admission']='기존 고정 ID 또는 실질 직접입력값이 있는 행만 후보. ID 없는 FALSE 기본행/수식전용행/서식행은 사실 0건. ID 없는 실질값은 고정 이관ID+결정대기로 보존.'
    for si in inventory:
        if si['source_file_code']=='NAT-V1' and si['source_sheet_name'] in t['source_sheets']:
            t['source_candidate_rows'][si['source_sheet_name']]=si['row_class_counts']

# Explicit issues protect unclear facts without withholding the rest of the model.
def issue(i,subject,evidence,action,block):
    issues.append({'issue_id':i,'status':'결정대기','subject':subject,'evidence':evidence,'preservation_and_action':action,'blocking_scope':block,'approved_value':None})
issue('N-ISSUE-001','10_인구_연간 L: 1열 의미','관측 CSV 및 literal_cells에 L1 헤더만 존재, 본문 literal/formula 0개','source_field_id 유지, REVIEW_UNRESOLVED_FIELDS에서 헤더와 의미미정을 표시. 의미 승인 전 활성 인구필드로 사용하지 않음.','이 필드의 활성 입력 의미만 보류')
issue('N-ISSUE-002','인물 성별·인적분류 분해 규칙','31_인물_마스터 M은 결합 필드, 현재 실질 인물행 0개','person_classification_raw로 보존; C00 분류 결정 없이 종족·성별을 자동 분해하지 않음.','새 분류코드 입력 규칙')
issue('N-ISSUE-003','국가 이름 판본','NAT 01 D2 Elrixhiyuem Holy-Empire Federation; REG 국가마스터와 별도 판본 대조 대상','N10 공식기본명과 C00 중립목록명/원문별칭을 역할별 보존. 최신 수정순으로 정본 채택 금지.','정본 조회 이름 선택')
issue('N-ISSUE-004','기관의 미입력 엔티티종류·국가·루트','NAT 20 10개 ID 중 명시되지 않은 엔티티종류/범위 다수. LOWER_HOUSE/UPPER_HOUSE 명칭은 의원, 종류는 합의기관','기존 office_id/명칭/종류/출처/설정상태 유지. K열 등 새 의미값을 이름에서 추정해 채우지 않음. 역할별 정원검사 적용불명은 미확인.','해당 기관 분류에 의존하는 검증')
issue('N-ISSUE-005','선거율 차이 허용오차','V1 29 자료점검 식의 0.00005 비교값 관측','기술설정 후보로 보존하되 C00 공통기준으로 등록할 때 원문 설정과 연결. 표시 반올림과 원값 비교 분리.','차이 허용오차 정책')
issue('N-ISSUE-006','PH0 기준첨부 셀차분 미검증','기준 첨부 XLSX 원파일 미확보 상태라는 상위 체크포인트','본 명세는 기존 PH0 온라인 스냅샷 기반 설계. PH0 통과/PH1 완료/이관완료로 표시하지 않음.','PH0 완료 및 온라인 이관 단계 진입')

DEPENDENCIES={
'N10':{'required':['C00','R10'],'optional':[],'forbidden':['N20','H90'],'note':'기관운영 결합은 H90'},
'N20':{'required':['C00','R10','N30'],'optional':[],'forbidden':['H90'],'note':'국호 결합은 H90; N30 인물 제공표를 읽음'},
'N30':{'required':['C00'],'optional':[],'forbidden':['N20','H90'],'note':'term_id 존재·기간 검증은 H90; 하이퍼링크는 허용'},
'N40':{'required':['C00'],'optional':['R20','R30','R50'],'forbidden':['N50','H90'],'note':'경제상 고용 원본 N50과 결합조회는 H90'},
'N50':{'required':['C00','N40'],'optional':['R60','R50','R70','R20'],'forbidden':['H90'],'note':'GDP 분자/인구 분모 메타 함께 검사'},
'N60':{'required':['C00'],'optional':['R30','R50'],'forbidden':['H90'],'note':'기존 명시된 사실이 없으면 0행'},
'N70':{'required':['C00'],'optional':['R40','R50','N30'],'forbidden':['N20','H90'],'note':'정치임기 결합은 H90'},
}
CONTROL_FIELDS=['nation_id','route','era','calendar_revision','query_mode','start_year','end_year','query_year','query_month','query_day','setting_status_filter','party_id','person_id','emperor_person_id']
NEW_CODEBOOKS={
'N40':['population_definition','social_metric','classification_axis','denominator_kind','coverage_status'],
'N50':['economic_metric','currency','price_type','fiscal_metric','flow_or_stock','budget_or_actual','valuation_basis','employment_definition'],
'N60':['culture_relation_type','language_status','legal_or_practice'],
'N70':['religion_legal_status','religious_org_kind','affairs_relation_type'],
}
meta={'project':'세계관 데이터 V2','schema_version':'PH1-nation-review-1','status':'PH1 명세 구체화 · 승인/구현/온라인시험 미완료','source_basis':'PH0 저장 온라인 스냅샷과 계획서. 실행시점 재확인은 상위 PH0 증거를 따름.','ph0_complete':False,'ph1_complete':False,'operating_files_created':0,'facts_migrated':0,'test_pass_claims':0,'source_snapshot_sha256':next(i['xlsx_sha256'] for i in inventory if i['source_file_code']=='NAT-V1')}
schema={**meta,'field_id_policy':'기존 source_field_id를 전부 유지. target_field는 공통키를 영어로 정규화하되 나머지는 한국어 원문 의미를 고유필드로 사용. 제공 계약은 열명으로 해석.','source_sheet_count':len(SHEETS),'source_field_count':len(spec),'dependencies':DEPENDENCIES,'tables':list(tables.values()),'query_control_fields':CONTROL_FIELDS,'new_codebook_groups':NEW_CODEBOOKS,'codebook_policy':'세계관 선택값은 C00 원문 정의만 배포. 새 분야 코드는 의미/단위 정의와 함께 승인 대기, 기본값으로 사실 생성 금지. 기술 상태값(미실행/자료없음 등)은 운영메타.','required_screen_roles':['시작·입력안내','입력','참조읽기전용','계산읽기전용','검증','제공','조회','이관추적'],'range_contract':RULES['N-RANGE'],'migration_batches':[{'batch_id':'NAT-N10','files':['N10'],'depends_on':['PH0 gate','C00','R10'],'status':'미실행'},{'batch_id':'NAT-N30','files':['N30'],'depends_on':['PH0 gate','C00'],'status':'미실행'},{'batch_id':'NAT-N20','files':['N20'],'depends_on':['PH0 gate','C00','R10','N30'],'status':'미실행'},{'batch_id':'NAT-N40','files':['N40'],'depends_on':['PH0 gate','C00'],'status':'미실행'},{'batch_id':'NAT-N50','files':['N50'],'depends_on':['PH0 gate','C00','N40'],'status':'미실행'},{'batch_id':'NAT-N60-N70','files':['N60','N70'],'depends_on':['PH0 gate','C00'],'status':'미실행'}]}
schema['physical_layout_policy']='tables는 논리 데이터셋이다. 각각 별도 시트를 무조건 생성하는 지시가 아니다. N20 입력동선은 기관·재임/정당·지도부/선거·결과로 안내하고 검증 요약은 파일당 한 화면에 모아 행 링크로 원본 이동. 모든 입력표에는 유일한 수정 위치를 둔다.'
for t in schema['tables']:
    for f in t['fields']:
        f['type']=f['data_type']
        f['required']=f['field_id']==t['record_key']
        f['required_policy']='신규 완전 입력의 필수키. 기존 불완전 행은 삭제하지 않고 미입력 오류로 보존.' if f['required'] else '기존 공란은 보존; 의미에 따른 조건부 필수는 function_rules에서 검사.'
    if 'publish_contract' in t:
        t['publish_contract']['primary_key']=[t['record_key']]
        t['publish_contract']['column_schema']=[{'field_id':f['field_id'],'type':f['type'],'required':f['required']} for f in t['fields']]

provided=defaultdict(list)
for t in schema['tables']:
    if t['role'] in ('input','calculation','query_output'): provided[(t['file_code'],t['canonical_dataset_id'])].append(t)
schema['provider_contracts']=[]
for (code,ds),pieces in sorted(provided.items()):
    cols={}
    for t in pieces:
        for f in t['fields']:
            cols.setdefault(f['field_id'],{'field_id':f['field_id'],'type':f['type'],'required':f['required']})
    for fid in ('validation_status','connection_status','schema_version','release_id','source_id','source_locator'):
        cols.setdefault(fid,{'field_id':fid,'type':'text','required':False})
    pks=sorted({t['record_key'] for t in pieces})
    schema['provider_contracts'].append({'file_code':code,'dataset_id':ds,'table_id':f'PUB_{ds}_V2','primary_key':pks,'column_schema':list(cols.values()),'joins':[{'table_id':t['table_id'],'on':t['record_key'],'role':t['role']} for t in pieces],'join_contract':'각 논리표의 고정 레코드 키로 결합. 서로 다른 종류의 키는 legacy/source 매핑을 거치고 행순서 결합 금지.','consumer_header_check':'expected field_id 집합·스키마 버전 검사 후 헤더명으로 선택. 빠진 필드는 스키마 오류.','operation_status':'미구현','runtime_status':'미실행'})

function_rows=[]
for n,(code,ds,label,pk,rids) in SHEETS.items():
    src_rows=[s for s in spec if s['source_sheet_name'][:2]==n]
    function_rows.append({'source_sheet':src_rows[0]['source_sheet_name'],'source_field_ids':[s['source_field_id'] for s in src_rows],'primary_file':code,'dataset_id':ds,'contracts':rids.split(','),'output_destinations':sorted({s['target_file_code']+'.'+s['target_table'] for s in src_rows}),'source_formula_pattern_ids':sorted({p for s in src_rows for p in s['source_formula_pattern_ids'].split(';') if p}),'semantic_coverage':'모든 관측 열에 개별 대상/역할 지정. 빈 표는 헤더·기능을 계승. 동작 동등성 검증은 미실행.','tests':sorted({t for rid in rids.split(',') for t in RULES[rid]['test_ids']}),'status':'명세작성; 구현/온라인시험 미실행'})
    deps={f'{code}.{ds}','C00.코드북','C00.출처레지스트리','C00.역법기준'}
    for p in patterns:
        if p['source_file_code']!='NAT-V1' or p['source_sheet_name']!=src_rows[0]['source_sheet_name']: continue
        for old_dep in p['sheet_dependencies_regex']:
            if old_dep[:2] in SHEETS:
                dc,dd,*_=SHEETS[old_dep[:2]]
                if code=='N30' and dc in ('N20','N10'): continue
                if code=='N20' and dc=='N10': continue
                deps.add(f'{dc}.{dd}')
    if code=='N20': deps.add('N30.PERSON')
    if code=='N50': deps.add('N40.NATION_POPULATION')
    if n=='87': deps.update(['N30.SUCCESSION','N30.PERSON'])
    if n=='88': deps.update(['N30.KINSHIP','N30.PERSON'])
    function_rows[-1]['required_dataset_ids']=sorted(deps)
    function_rows[-1]['test_ids']=function_rows[-1]['tests']
    function_rows[-1]['external_cross_checks_owner']='H90' if code in ('N30','N70') else None
for rid,r in RULES.items():
    r['required_dataset_ids']=sorted({d for fn in function_rows if rid in fn['contracts'] for d in fn['required_dataset_ids']})
relevant_tests=[{k:v for k,v in t.items() if k not in ('actual_result','evidence_location','checked_at')} for t in checklist if any(c in t['target_files'] for c in ('N10','N20','N30','N40','N50','N60','N70')) or t['target_files']=='전체']
functions={**meta,'function_rules':list(RULES.values()),'per_source_sheet':function_rows,'planned_tests':relevant_tests,'all_test_status':'미실행; 문서 정적 점검은 84개 운영 시험의 통과가 아님','query_spill_corrections':[{'source_sheet':'87_시점별_황위계승','source_anchor':'A6','observation_correction':'A6 단일 spill 수식이 A:M 출력. 1~4행은 UI/조회안내, 5행 헤더. B-D/F-M은 입력 원자료 아님.'},{'source_sheet':'88_친족관계_조회','source_anchor':'A6','observation_correction':'A6 단일 spill 수식이 A:H 출력. 1~4행은 UI/조회안내, 5행 헤더. B-D/F-H은 입력 원자료 아님.'}],'empty_area_functions':[{'file_code':c,'required_tables':[t['table_id'] for t in tables.values() if t['file_code']==c and not t['source_sheets']],'rule_id':'N-EMPTY','fact_rows':0,'online_status':'미실행'} for c in ('N40','N50','N60','N70')]}
functions['cross_file_views']=[
 {'function_id':'H90-NATION-POLITICS-NAME','owner':'H90','source_field_ids':[x['source_field_id'] for x in spec if x['source_sheet_name'].startswith('80') and x['target_file_code']=='H90'],'required_dataset_ids':['N10.NATION_NAME_HISTORY','N20.POLITICS_ANNUAL'],'test_ids':['T-015','T-021','T-077'],'contract':'N20 정치연간 출력과 N10 시점국호를 H90에서 결합. N20의 N10 추가 import를 요구하지 않음.','status':'미실행'},
 {'function_id':'H90-ROYAL-REIGN-COMPOSITE','owner':'H90','source_field_ids':[x['source_field_id'] for x in spec if x['source_sheet_name'].startswith('86') and x['target_file_code']=='H90'],'required_dataset_ids':['N20.OFFICE_TERM','N30.PERSON','N30.ROYAL_STATUS','N30.SUCCESSION','N10.CAPITAL_HISTORY','N10.CONSTITUTION_HISTORY'],'test_ids':['T-065','T-066','T-067','T-069'],'contract':'황제 재위·수도·헌정 결합 및 N30 외부 term_id 존재/인물/기간 검증은 H90. N30으로 결과 재import하지 않음.','status':'미실행'},
 {'function_id':'H90-RELIGIOUS-POLITICAL-ROLE','owner':'H90','source_field_ids':[],'required_dataset_ids':['N70.RELIGIOUS_AFFAIRS_HISTORY','N20.OFFICE','N20.OFFICE_TERM','N30.PERSON'],'test_ids':['T-053','T-069'],'contract':'교무상의 관계와 정치공직 임기를 구별하고 외부 political_office_id/term_id는 H90에서 검사. N70의 N20 import 금지.','status':'미실행'}]

# Static quality checks: exact source coverage and references, not runtime claims.
assert len({s['source_field_id'] for s in spec})==len(spec)
assert {s['source_field_id'] for s in spec}=={s['source_field_id'] for s in assigned}
assert all(s['target_table'] and s['target_field'] and s['target_role'] for s in spec)
assert all(r in RULES for s in spec for r in s['function_rule_ids'].split(','))
assert 'N20' not in DEPENDENCIES['N30']['required']+DEPENDENCIES['N30']['optional']
assert all(t['fact_row_count']==0 for t in tables.values() if 'fact_row_count' in t)
stats={'source_sheets':len(SHEETS),'source_fields':len(spec),'role_counts':dict(Counter(s['target_role'] for s in spec)),'destination_counts':dict(Counter(s['target_file_code'] for s in spec)),'table_count':len(tables),'new_empty_table_count':len(NEW),'source_coverage_missing':0,'source_coverage_duplicates':0,'rules_count':len(RULES),'issues':len(issues),'runtime_test_passes':0,'static_status':'명세 내부 정합성 점검 통과; PH1 완료 판정 아님'}
for name,obj in [('nation_schema.json',schema),('nation_function_spec.json',functions),('nation_issues.json',{**meta,'issues':issues,'static_validation':stats})]:
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (OUT/'nation_field_spec.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(spec[0]));w.writeheader();w.writerows(spec)
print(json.dumps(stats,ensure_ascii=False,indent=2))

