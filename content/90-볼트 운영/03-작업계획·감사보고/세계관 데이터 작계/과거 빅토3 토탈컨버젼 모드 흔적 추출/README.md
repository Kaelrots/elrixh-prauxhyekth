# New World – Rarixhenverk 지리·행정 데이터 추출본

2026-10-02 (Asia/Seoul). Google Drive의 `New World - Rarixhenverk` 폴더에서 읽기 전용으로 확보한 원본 사본을 분석했다. Drive의 파일 내용·이름·폴더·권한은 변경하지 않았다.

출처: https://drive.google.com/drive/folders/1H4lrdrfa74Y3p7SxOrEyg3E0CUMcOS01

이 패키지는 원본에 적혀 있는 데이터의 복구본이다. 현재 Victoria 3에서 정상 실행되는 모드나 수정된 정답 데이터셋이라는 의미는 아니다. 기본 게임의 정의·번역·실행 시 로드 순서는 적용하지 않았다.

## 주요 결과

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>항목</th>
      <th>개수</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>다운로드·보존한 원본 파일</td>
      <td>95</td>
    </tr>
    <tr>
      <td>state_regions 파일</td>
      <td>29</td>
    </tr>
    <tr>
      <td>state 정의 레코드</td>
      <td>1,954</td>
    </tr>
    <tr>
      <td>고유 state key / 고유 numeric ID</td>
      <td>1,952 / 1,953</td>
    </tr>
    <tr>
      <td>지도 크기</td>
      <td>8192 × 3616</td>
    </tr>
    <tr>
      <td>실제 지도 RGB 색상</td>
      <td>44,522</td>
    </tr>
    <tr>
      <td>참조됐으나 지도에 없는 HEX까지 포함한 province 행</td>
      <td>44,542</td>
    </tr>
    <tr>
      <td>state에 선언된 고유 province HEX</td>
      <td>35,401</td>
    </tr>
    <tr>
      <td>지도에 있으나 state에 소속되지 않은 색상</td>
      <td>9,128</td>
    </tr>
    <tr>
      <td>소속 province가 전부 지도에 존재하는 state</td>
      <td>1,394</td>
    </tr>
    <tr>
      <td>province 목록이 완전히 빈 state</td>
      <td>555</td>
    </tr>
    <tr>
      <td>일부 province가 지도에 없는 state</td>
      <td>5</td>
    </tr>
    <tr>
      <td>전략지역 / state 목록이 빈 전략지역</td>
      <td>13 / 4</td>
    </tr>
    <tr>
      <td>국가 / 문화 / 종교 / state trait 정의</td>
      <td>28 / 6 / 2 / 9</td>
    </tr>
    <tr>
      <td>한국어 이름을 연결한 state 레코드</td>
      <td>1,953</td>
    </tr>
    <tr>
      <td>공식 영문 localization 이름</td>
      <td>0</td>
    </tr>
    <tr>
      <td>픽셀 경계에서 추출한 province 인접 쌍</td>
      <td>131,898</td>
    </tr>
  </tbody>
</table></div>

## 바로 사용하기

1. `json/states.json`과 `json/provinces.json`을 읽으면 핵심 지리·행정 정보를 사용할 수 있다.
2. HEX로 빠르게 state를 찾으려면 `json/province_to_states_lookup.json`을 사용한다. HEX 키에 `x`나 `#`를 붙이지 않는다.
3. CSV를 선호하면 `csv/`의 동일 이름 파일을 사용한다. 모든 주요 테이블은 CSV와 JSON으로 함께 제공한다.
4. state 연결에는 <font style="font-weight:bold">`state_record_id`</font>를 가장 안전한 식별자로 사용한다. 원본에 중복 state key와 numeric ID가 있기 때문이다.
5. `validation_issues`, `empty_or_unmapped_states`를 확인한 후 앱에 가져온다. 누락·빈 값·중복을 임의로 채우거나 삭제하지 않았다.

`source_snapshot/map_data/provinces.png`에는 원본 색상과 경계가 그대로 보존되어 있다. bounding box는 영역의 바깥 사각형일 뿐 정확한 경계 폴리곤이 아니다. 정확한 도형이 필요하면 PNG의 색상 마스크를 사용한다.

## 파일 구성

- `csv/`, `json/`: 아래 표의 동일한 데이터 테이블.
- `README.md`: 스키마·좌표 규칙·주의사항·누락 설명 및 모든 테이블의 필드 목록.
- `schema.json`: 타입과 테이블 행 수를 포함하는 기계 판독 스키마.
- `validation_report.json`: 추출 개수와 원본 데이터 문제 통계.
- `verification.json`: 원본 픽셀과 대조한 추출 검증 결과.
- `raster_supplement_metadata.json`: 높이맵 격자 대응과 원시 단위 설명.
- `source_snapshot/`: 분석한 원본 파일의 바이트 단위 사본. 원본 provinces/heightmap/rivers 이미지 포함.
- `raw/parsed_text_files.json`: 순서를 유지한 텍스트 구문 구조. 반복된 필드와 원문 줄 번호 포함.
- `tools/`: 네트워크 접속 없이 추출과 검증을 재현하는 보조 스크립트 및 원본 메타데이터.
- `checksums.sha256`: 패키지 내 파일의 무결성 확인용 SHA-256. 이 체크섬 파일 자체는 제외.

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>테이블 이름 (`csv/이름.csv`, `json/이름.json`)</th>
      <th>행</th>
      <th>내용</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>`states`</td>
      <td>1,954</td>
      <td>모든 state 정의, 명칭, province 목록, 허브, 특성·자원 및 픽셀 가중 집계. 기본 테이블.</td>
    </tr>
    <tr>
      <td>`provinces`</td>
      <td>44,542</td>
      <td>지도 전체 고유 RGB와 모든 참조 HEX의 합집합. 위치·영역·state 역매핑·수역 명시값.</td>
    </tr>
    <tr>
      <td>`province_state_memberships`</td>
      <td>35,401</td>
      <td>원문 province 토큰별 state 관계. 반복과 순서 보존; 면적 집계 시에는 중복 제거.</td>
    </tr>
    <tr>
      <td>`province_to_states`</td>
      <td>44,542</td>
      <td>HEX별 state 역매핑. 복수 소속을 배열로 보존; state가 없으면 빈 배열.</td>
    </tr>
    <tr>
      <td>`state_hubs`</td>
      <td>9,770</td>
      <td>모든 state × city/port/farm/mine/wood. 미지정·빈 문자열·HEX 구분 및 허브 명칭과 위치.</td>
    </tr>
    <tr>
      <td>`state_traits_memberships`</td>
      <td>252</td>
      <td>state와 trait 식별자의 관계.</td>
    </tr>
    <tr>
      <td>`state_resources`</td>
      <td>2,958</td>
      <td>경작 가능 자원과 capped/resource 자원 블록. 경작지 총량은 states.arable_land.</td>
    </tr>
    <tr>
      <td>`strategic_regions`</td>
      <td>13</td>
      <td>전략지역, 명칭, 수도 province, 원본 map_color, state 목록 및 합집합 지리.</td>
    </tr>
    <tr>
      <td>`strategic_region_states`</td>
      <td>216</td>
      <td>전략지역의 원문 state 관계. 반복·미정의 state도 보존.</td>
    </tr>
    <tr>
      <td>`province_adjacency`</td>
      <td>131,898</td>
      <td>4방향 픽셀 변 공유 관계. wrap_x=yes에 따라 좌우 경계 연결 포함. 게임 이동 가능성 아님.</td>
    </tr>
    <tr>
      <td>`state_adjacency`</td>
      <td>3,999</td>
      <td>양쪽 province의 state가 각각 유일할 때만 집계한 state 공유 경계.</td>
    </tr>
    <tr>
      <td>`province_height_raw`</td>
      <td>44,522</td>
      <td>각 province에 겹치는 16-bit 원본 높이맵 샘플의 수·합·최소·최대·평균. 미터 단위 아님.</td>
    </tr>
    <tr>
      <td>`state_height_raw`</td>
      <td>1,954</td>
      <td>state province 합집합의 16-bit 높이맵 원시 통계. 빈 state는 평균·최소·최대 null.</td>
    </tr>
    <tr>
      <td>`province_river_palette_counts`</td>
      <td>57,636</td>
      <td>province별 rivers.png 팔레트 인덱스 픽셀 수. 인덱스 의미는 추정하지 않음.</td>
    </tr>
    <tr>
      <td>`river_palette`</td>
      <td>7</td>
      <td>강 지도에서 실제 사용한 인덱스와 RGB, 전체 픽셀 수.</td>
    </tr>
    <tr>
      <td>`map_object_instances`</td>
      <td>5</td>
      <td>원본 지도 객체/허브 배치 좌표. 게임의 x/y/z 원본 좌표이며 PNG 좌표 변환·state 연결은 확정하지 않음.</td>
    </tr>
    <tr>
      <td>`map_object_groups`</td>
      <td>99</td>
      <td>선택한 지도 객체 그룹과 인스턴스 수. 자동 생성 식생 배치 폴더는 제외.</td>
    </tr>
    <tr>
      <td>`map_editor_completion`</td>
      <td>46,786</td>
      <td>편집기 완료 표시 원문. category 0의 숫자→RGB HEX는 값의 일치로 추론. category 1 숫자는 state 연결 미확인. 게임 활성 여부나 완성도 보증 아님.</td>
    </tr>
    <tr>
      <td>`country_definitions`</td>
      <td>28</td>
      <td>country_definitions 식별자, 로컬라이즈 이름과 모든 원본 필드.</td>
    </tr>
    <tr>
      <td>`cultures`</td>
      <td>6</td>
      <td>cultures 식별자, 로컬라이즈 이름과 모든 원본 필드.</td>
    </tr>
    <tr>
      <td>`religions`</td>
      <td>2</td>
      <td>religions 식별자, 로컬라이즈 이름과 모든 원본 필드.</td>
    </tr>
    <tr>
      <td>`state_traits`</td>
      <td>9</td>
      <td>state_traits 식별자, 로컬라이즈 이름과 모든 원본 필드.</td>
    </tr>
    <tr>
      <td>`discrimination_traits`</td>
      <td>2</td>
      <td>discrimination_traits 식별자, 로컬라이즈 이름과 모든 원본 필드.</td>
    </tr>
    <tr>
      <td>`terrain`</td>
      <td>25</td>
      <td>terrain 식별자, 로컬라이즈 이름과 모든 원본 필드.</td>
    </tr>
    <tr>
      <td>`country_cultures`</td>
      <td>29</td>
      <td>국가와 주 문화 식별자의 관계. 영토 소유권 아님.</td>
    </tr>
    <tr>
      <td>`culture_name_tokens`</td>
      <td>769</td>
      <td>문화 정의의 인명·성명 토큰과 순서.</td>
    </tr>
    <tr>
      <td>`geographic_identifier_references`</td>
      <td>250</td>
      <td>보존한 스크립트의 state/country/culture 식별자 참조와 원문 위치.</td>
    </tr>
    <tr>
      <td>`localization_all`</td>
      <td>5,974</td>
      <td>모든 확보한 localization 문장. 중복 키와 원문 파일·줄 보존.</td>
    </tr>
    <tr>
      <td>`localization_geography`</td>
      <td>4,853</td>
      <td>state·hub·region 및 식별자 명칭, 정의 매칭과 정적 별칭 해석.</td>
    </tr>
    <tr>
      <td>`localization_unmatched_geography`</td>
      <td>2,834</td>
      <td>명칭은 있으나 확보한 정의와 연결되지 않은 지명.</td>
    </tr>
    <tr>
      <td>`province_terrain_overrides`</td>
      <td>9</td>
      <td>province_terrains.txt의 명시적인 지형만 추출; 다른 지역의 지형은 추정하지 않음.</td>
    </tr>
    <tr>
      <td>`map_settings`</td>
      <td>7</td>
      <td>default.map 설정. sea_starts/lakes 원문 토큰 및 wrap_x.</td>
    </tr>
    <tr>
      <td>`special_adjacencies`</td>
      <td>0</td>
      <td>원본 특수 이동 연결. 이번 원본은 헤더만 있고 데이터 행 없음.</td>
    </tr>
    <tr>
      <td>`validation_issues`</td>
      <td>45</td>
      <td>원본 결손·중복·참조 오류. 자동 수정하지 않음.</td>
    </tr>
    <tr>
      <td>`empty_or_unmapped_states`</td>
      <td>560</td>
      <td>빈 state, 지도에서 전혀 찾지 못한 state, 부분적으로만 찾은 state.</td>
    </tr>
    <tr>
      <td>`source_files`</td>
      <td>98</td>
      <td>Drive 출처, 수정 시각, 다운로드 길이와 SHA-256.</td>
    </tr>
    <tr>
      <td>`inspected_history_and_localization_folders`</td>
      <td>15</td>
      <td>하위 폴더 직접 조회 결과. history/states,pops,buildings 등의 빈 상태 증거.</td>
    </tr>
    <tr>
      <td>`parsed_file_summary`</td>
      <td>77</td>
      <td>텍스트 정의 파일별 추출 개수와 빈 파일 상태.</td>
    </tr>
    <tr>
      <td>`extraction_summary`</td>
      <td>34</td>
      <td>전체 개수와 검증 통계.</td>
    </tr>
  </tbody>
</table></div>

## 핵심 스키마와 결합 규칙

### State

`state_id`는 원문 numeric ID, `state_key`는 `STATE_...` 코드다. `state_record_id`는 `state_key@파일:줄` 형식으로 원문 정의를 유일하게 식별한다. `province_hexes`는 <font style="font-weight:bold">모든 provinces 블록을 합쳐 중복을 제거한 목록</font>이다. `province_token_count`는 원래 토큰 수이고, 개별 토큰의 순서·반복은 `province_state_memberships`에 보존했다.

`city_hex`, `port_hex`, `farm_hex`, `mine_hex`, `wood_hex`는 원문 허브 참조다. `traits`, `arable_land`, `arable_resources`, `capped_resources`, `resource_blocks`, `subsistence_building`은 원문 필드에서 추출했다. 이번 원본에는 독립 `resource` 블록이 없어 해당 목록은 비어 있다. 없는 필드를 0으로 채우지 않는다. 허브 필드의 미선언·빈 문자열·유효 HEX는 `state_hubs.value_status`로 구분한다.

`state_color_hex`는 모두 null이다. 원본 state_regions에는 state 자체를 식별하는 단일 색상 필드가 없다. 국가 색상·전략지역 색상·province 식별색을 state 색상으로 혼용하지 않았다.

### Province와 역매핑

`province_hex`는 접두사 없는 대문자 6자리 문자열이다. 예: `85C9A1`. `province_token=x85C9A1`, `hex_css=#85C9A1`, RGB 채널 값도 함께 제공한다. <font style="font-weight:bold">HEX는 숫자로 변환하지 말고 문자열로 읽는다.</font>

`provinces`는 실제 지도 색상 전체에 state·허브·전략지역 수도·수역·지형에서 참조한 HEX를 합친 테이블이다. 지도에 없는 참조는 `map_present=false`, 면적 0, 좌표 null이다. 지도에 있지만 state가 없으면 `assignment_status=unassigned`이다. 이 경우 바다·배경·미완성 육지 중 무엇인지 임의로 확정하지 않는다.

`state_ids`, `state_keys`, `state_record_ids`는 배열이며, `state_id`와 `state_key` 단일 열은 소속 원문 정의가 유일할 때만 채운다. 이번 원본에서 서로 다른 state 정의가 같은 province HEX를 공유하는 경우는 없었다. 이름이나 numeric ID가 중복돼도 서로 다른 `state_record_id`는 유지된다.

### 좌표·면적

- 원점: PNG 좌상단. x는 오른쪽, y는 아래쪽으로 증가한다.
- 정수 픽셀 인덱스: x=0…8191, y=0…3615. 크기 조정·회전·색상 보간 없이 RGB를 정확히 비교했다.
- `pixel_area`: 해당 HEX의 모든 픽셀 수. km² 등 실제 면적이 아니다.
- `centroid_x`, `centroid_y`: 해당 영역 픽셀 인덱스의 산술평균.
- `centroid_x_norm=(centroid_x+0.5)/8192`, `centroid_y_norm=(centroid_y+0.5)/3616`. 픽셀 중심을 지도 바깥 테두리 기준 0…1 좌표로 표현한다.
- `bbox_min_x/y`, `bbox_max_x/y`: 픽셀 인덱스이며 <font style="font-weight:bold">최대값도 포함</font>한다. 따라서 bbox 폭은 `max_x-min_x+1`이다.
- 정규화 bbox 최소값은 `min/size`, 최대값은 `(max+1)/size`다. 정규화 bbox는 차지한 픽셀 셀의 외곽 경계다.
- `area_fraction=pixel_area/(8192×3616)`.
- state/전략지역 중심점은 소속 province의 <font style="font-weight:bold">픽셀 수로 가중한 중심점</font>이다. province 중심점의 단순평균이 아니다. 중복 토큰과 반복된 state 관계는 지리 합산에서 한 번만 센다.
- `representative_x/y`는 그 색상이 실제로 존재하는 첫 픽셀로, 중심점과 별개다. 섬·오목한 영역·분리된 조각의 중심점은 해당 영역 밖에 있을 수 있다. 같은 HEX의 분리된 조각은 하나의 province로 합산했다.
- `default.map`에 `wrap_x=yes`가 있다. 일반 centroid/bbox는 평면 좌표 계산값이므로 좌우 끝을 가로지르는 영역에서 길게 퍼질 수 있다. `touches_both_x_edges`와 `circular_centroid_x_norm`을 참고한다. 원형 중심의 `circular_resultant_x`가 0에 가까우면 그 중심도 불안정하다. 원형 최소 bbox·지구 위경도·투영·실제 거리·폴리곤은 추정하지 않았다.

### 명칭

`name_korean`은 실제 localization의 정확한 키로 연결했다. 해당 폴더의 언어는 한국어뿐이라 `name_english`는 null이다. `name_key_derived`는 코드의 접두사·밑줄을 정리한 표시용 이름이며 <font style="font-weight:bold">공식 영문명이나 검증된 로마자 표기명이 아니다</font>. `name_key_derived_is_official=false`로 구분한다.

`localized_names`는 언어→표기 사전이다. 전체 번역 원문은 `localization_all`에, 지리 관련 항목은 `localization_geography`에 있다. 정적 `$KEY$` 별칭만 같은 언어 내에서 재귀 해석하며 게임의 동적 표현식·문법·스타일은 실행하지 않는다. 동일 키가 여러 번 나오면 파일 경로 순·파일 내 순서의 마지막 값을 연결하되 모든 후보와 중복 경고를 보존한다. 이는 게임의 최종 로드 결과를 보장하는 규칙이 아니다.

### 전략지역·국가·문화·종교

`strategic_region_states`는 전략지역과 state의 원문 관계다. 전략지역에 없는 state 1,739개는 임의 배정하지 않았다. 국가 테이블의 `capital_state_key`는 기본 수도 참조이고 `country_cultures`는 국가의 주 문화 참조다. <font style="font-weight:bold">국가의 영토 소유권·culture의 지리적 분포를 뜻하지 않는다.</font>

`common/history/states`, `pops`, `buildings`는 실제 폴더 조회에서 비어 있었다. 따라서 국가별 state 소유권, homeland·claim, 실제 POP 분포, 주별 건물과 경제는 복구할 원문이 없다. 국가 이력 스크립트와 문화 인명, 종교·특성 식별자는 별도로 보존했다. 게임 기본 파일에서 상속되는 정의는 가져오지 않았다.

`color_raw`, `map_color_raw`는 원문의 rgb·정수·소수 표현을 보존한다. 정수 0…255와 소수 0…1 값을 임의로 같은 스케일이라고 가정하지 않는다. `raw_fields`와 순서형 원문 AST로 모든 부가 필드를 다시 확인할 수 있다.

## 빈 state와 원본 문제

`geometry_status=empty_definition`은 province 목록 합집합이 비어 있는 state다. 면적은 0, 중심점·bbox는 null이며 ID·명칭·자원 등 다른 정보는 그대로 남아 있다. `partial`은 일부 참조 HEX가 지도에 없어서 실제 찾은 부분만 집계한 상태다. `complete`는 지리 참조가 모두 지도에 존재한다는 뜻이며 모드 완성도를 뜻하지 않는다.

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>빈 state가 있는 파일</th>
      <th>개수</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>`map_data/state_regions/03_south_senaxh.txt`</td>
      <td>37</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/04_south_west_senaxh.txt`</td>
      <td>35</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/05_north_west_senaxh.txt`</td>
      <td>71</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/06_rwikelven.txt`</td>
      <td>23</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/07_raionion_korea.txt`</td>
      <td>18</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/08_raikan.txt`</td>
      <td>53</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/09_hyaryet.txt`</td>
      <td>13</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/10_rwiaxhe.txt`</td>
      <td>119</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/11_ryuyen.txt`</td>
      <td>26</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/12_siyraeion.txt`</td>
      <td>40</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/13_kerwishien.txt`</td>
      <td>119</td>
    </tr>
    <tr>
      <td>`map_data/state_regions/21_xhiryuenderh.txt`</td>
      <td>1</td>
    </tr>
  </tbody>
</table></div>

- `STATE_AKANPACZATANIAH`(342)에는 96개 HEX가 든 `provinces` 블록 다음에 빈 `provinces={}`가 반복된다. 복구 목적에 따라 두 블록을 합쳐 96개를 보존했다. 따라서 마지막 선언만 읽으면 빈 state 556개로 보이지만 이 추출본은 완전히 빈 정의 555개다. 게임이 어떤 선언을 최종 적용할지는 판단하지 않는다.
- 중복 state key: `STATE_GWANBUK`, `STATE_AINTOVOLRA`. 각각 원문 정의 두 개를 보존했다.
- numeric ID `2638`: `STATE_INEHSPANTEZIAH`와 `STATE_UNTFUNVERKH`가 공유한다.
- state 소속 목록에서 지도에 없는 HEX는 7개이며 5개 state에 걸쳐 있다. `STATE_RIESELRANTO`, `STATE_AILRUUENTH`, `STATE_AIVELRENNERANTH`, `STATE_VADANTANTH`, `STATE_NIDOTORAXHEMAHN`이다. 상세 HEX는 `missing_province_hexes`에 있다.
- 모든 종류의 참조를 합치면 지도에 없는 HEX는 20개다. RARHELIYA의 4개 허브와 SHINSEOUL의 city, 값이 있는 전략지역 수도 9개도 포함된다. 허브를 근처 province로 자동 치환하지 않았다. `state_hubs`의 좌표가 존재할 때도 그것은 허브 province 중심이며 실제 건물 위치는 아니다.
- 전략지역 4개에는 수도 HEX와 state 목록이 비어 있다. `water_strategic_regions.txt`에는 활성 정의가 없다.
- `STATE_KUSPELRAHASHI`의 정확한 한국어 localization 키는 없었다. 비슷한 다른 키로 자동 보정하지 않았다.
- `STATE_GWANBUK`의 localization은 동일한 한국어 값으로 중복된다.
- 이름 localization의 `Czehn_ Zailrits` 항목은 키 안의 공백 때문에 정규 구문으로 읽지 않았다. 원문 줄은 `validation_issues` 및 원본 사본에 그대로 남아 있다.
- `adjacencies.csv`는 헤더만 있으며 특수 이동 연결 데이터는 0행이다. 대신 별도 픽셀 인접 관계를 추출했다.

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>문제 유형</th>
      <th>건수</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>`duplicate_localization_key`</td>
      <td>1</td>
    </tr>
    <tr>
      <td>`duplicate_state_field`</td>
      <td>1</td>
    </tr>
    <tr>
      <td>`duplicate_state_id`</td>
      <td>1</td>
    </tr>
    <tr>
      <td>`duplicate_state_key`</td>
      <td>2</td>
    </tr>
    <tr>
      <td>`duplicate_state_within_region`</td>
      <td>1</td>
    </tr>
    <tr>
      <td>`hub_outside_declared_state`</td>
      <td>5</td>
    </tr>
    <tr>
      <td>`localization_unparsed_line`</td>
      <td>1</td>
    </tr>
    <tr>
      <td>`missing_assignment_value`</td>
      <td>4</td>
    </tr>
    <tr>
      <td>`referenced_hex_missing_from_map`</td>
      <td>20</td>
    </tr>
    <tr>
      <td>`region_capital_outside_declared_region`</td>
      <td>9</td>
    </tr>
  </tbody>
</table></div>

## 보조 지리 정보

<font style="font-weight:bold">픽셀 인접 관계:</font> 대각선 접촉은 제외하고 상하좌우 픽셀 변을 공유하는 province 쌍을 집계했다. 좌우 지도 끝도 연결했다. `shared_pixel_edges`는 접한 픽셀 변의 수이며 실제 경계 길이·이동 허용·항로·해협 판정이 아니다. `seam_pixel_edges`는 이 중 좌우 끝 연결분이다. state 인접 관계는 양쪽 province의 소속이 각각 하나로 확정되는 경우만 집계했다.

<font style="font-weight:bold">높이맵:</font> 원본은 16384×7232, 16-bit 샘플이다. 픽셀 그리드의 좌상단과 방향이 일치한다는 대응 규칙으로 province 픽셀 하나에 높이맵 2×2 픽셀을 대응해 원시 샘플 수·합·최소·최대·평균을 계산했다. 이 격자 대응은 두 원본 이미지의 크기와 방향에 따른 분석 규칙이며 게임 좌표계 변환 검증을 뜻하지 않는다. 원시값을 미터나 해발고도로 변환하지 않았다. `source_snapshot`에는 원본도 포함했다.

<font style="font-weight:bold">강 지도:</font> `province_river_palette_counts`는 각 province 안에서 rivers.png의 팔레트 인덱스별 픽셀 수를 보존한다. `river_palette`에서 인덱스와 RGB를 볼 수 있다. 지류·발원·합류·강 등급의 의미는 해석하지 않았다. 배경 인덱스도 모두 포함하므로 이 값들을 전부 강 면적으로 더하면 안 된다.

<font style="font-weight:bold">지도 객체:</font> 확보한 지도 객체 파일의 인스턴스 위치·회전·크기를 보존했다. 5개 허브 locator의 `instance_id=1`과 state ID 1의 일치는 참고 후보일 뿐 확정 연결이 아니다. 게임의 원시 x/y/z를 PNG x/y로 변환하지 않았다. 오래된 배치일 수 있다. 대량 자동 생성 식생·농장 장식 객체와 렌더링 텍스처는 이번 지리·행정 추출에서 제외했다.

<font style="font-weight:bold">편집기 완료 상태:</font> category 0은 숫자를 RGB 정수로 풀었을 때 지도 HEX와 다수 일치하므로 후보 HEX를 제공한다. 과거 지도에 속하는 항목도 있을 수 있어 지도 존재 여부를 함께 표시했다. category 1의 숫자는 불투명한 식별자로 남겼으며 state ID나 state 이름의 해시라고 확정하지 않았다. 완료 표시는 현재 모드 완성 여부를 보증하지 않는다.

<font style="font-weight:bold">제외·미해석:</font> `nodes.dat`, `packed_heightmap.png`, `indirection_heightmap.png`는 컴파일 또는 파생 지도 캐시로 별도 해독·보존하지 않았다. 원본 `heightmap.heightmap`의 파일 참조는 해당 이름을 유지하므로 이 패키지 자체를 플레이용 모드로 실행하면 안 된다. 확보한 binary `spline_network.splnet`은 원본 사본만 보존했다. 물·지형 표현용 대용량 DDS/TGA·마스크, 모델·초상화·국기·이벤트·일반 게임 플레이 정의 등은 최소 요구 지리·행정 데이터에 해당하지 않아 전부 복제하지 않았다. 따라서 이 ZIP은 모드 전체 백업은 아니다.

## 형식·타입 주의사항

- JSON은 UTF-8, CSV는 한글 Excel 호환용 UTF-8 BOM이며 구분자는 쉼표다. CSV의 배열·객체 셀은 JSON 문자열이다.
- JSON `null`은 CSV 빈 셀이다. 값이 없음과 원문 빈 배열의 차이가 중요하면 JSON 또는 `field_presence`, `value_status`, `raw_fields`를 사용한다.
- CSV를 Excel에서 가져올 때 HEX, tag, key, raw_identifier는 텍스트 열로 지정한다. 선행 0이나 `E`가 포함된 HEX를 숫자/지수로 자동 변환하지 않는다.
- 모든 좌표는 소수 정밀도를 유지했다. 파일을 읽는 쪽에서 필요한 만큼만 표시 반올림한다.
- 원문 AST는 `assignments` 배열로 키·연산자·값·줄 번호를 보존한다. 목록은 배열, `rgb {…}`와 같은 형식은 type/value 객체다. `raw_fields`는 편의를 위한 사전형 뷰이며 중복 필드는 `repeated_values`로 기록한다.

## 검증 및 재현

총 155개 검증을 통과했다. 전체 29,622,272픽셀과 44,522색의 면적을 독립 RGB 집계와 대조했고, province 18개 및 state 16개를 원본 픽셀 마스크에서 다시 계산했다. 원문 state 선언/ID/HEX 토큰 수, 역매핑, CSV·JSON 행 수와 배열 왕복, 정규화 범위, 전체 경계 변 수, 원본 사본 SHA-256도 확인했다. 높이맵 원시 합계와 표본, province별 강 팔레트 픽셀 총합을 대조했다. 이 검증은 <font style="font-weight:bold">추출의 일치성</font> 검증이며 원본의 설계 오류를 고쳤다는 뜻은 아니다.

재현에는 Python 3.10 이상, numpy, Pillow가 필요하다. ZIP을 푼 최상위 폴더에서 아래 순서대로 실행하면 `rebuild/`에 데이터와 검증 결과를 새로 만든다. 원본 사본에는 쓰지 않는다. 데이터와 raw AST는 재생성되며 이 README·ZIP 포장은 별도로 유지된다.

```text
python tools/raster_stats.py
python tools/raster_supplements.py
python tools/extract_geography.py
python tools/validate_extraction.py
```

## 전체 테이블 필드 목록

타입 표기: str=문자열, int=정수, float=실수, bool=참/거짓, list=배열, dict=객체. `null only`는 이번 원본에서 모든 값이 null인 열이다. 아래 타입 목록에는 null 가능성을 별도로 나열하지 않았다. 값이 일부 없을 수 있으므로 JSON null 처리도 필요하다.

### states

`state_record_id` (str); `state_id` (int); `state_key` (str); `name_english` (null only); `name_korean` (str); `name_key_derived` (str); `name_key_derived_is_official` (bool); `localized_names` (dict); `source_file` (str); `source_line` (int); `is_sea_state_file` (bool); `province_hexes` (list); `province_token_count` (int); `province_count` (int); `province_assignment_blocks` (int); `traits` (list); `arable_land` (int); `arable_resources` (list); `capped_resources` (dict); `resource_blocks` (list); `subsistence_building` (str); `field_presence` (list); `raw_fields` (dict); `city_hex` (str); `port_hex` (null only); `farm_hex` (str); `mine_hex` (str); `wood_hex` (str); `strategic_region_keys` (list); `pixel_area` (int); `area_fraction` (float/int); `centroid_x` (float); `centroid_y` (float); `centroid_x_norm` (float); `centroid_y_norm` (float); `bbox_min_x` (int); `bbox_min_y` (int); `bbox_max_x` (int); `bbox_max_y` (int); `bbox_min_x_norm` (float); `bbox_min_y_norm` (float); `bbox_max_x_norm` (float); `bbox_max_y_norm` (float); `circular_centroid_x_norm` (float); `circular_resultant_x` (float); `present_province_count` (int); `missing_province_hexes` (list); `missing_province_count` (int); `geometry_status` (str); `has_ambiguous_province_ownership` (bool); `state_color_hex` (null only).

### provinces

`province_hex` (str); `province_token` (str); `hex_css` (str); `rgb_r` (int); `rgb_g` (int); `rgb_b` (int); `map_present` (bool); `state_id` (int); `state_key` (str); `state_ids` (list); `state_keys` (list); `state_record_ids` (list); `assignment_status` (str); `is_sea_start` (bool); `is_lake` (bool); `explicit_terrain` (str); `water_class` (str); `pixel_area` (int); `area_fraction` (float/int); `centroid_x` (float); `centroid_y` (float); `centroid_x_norm` (float); `centroid_y_norm` (float); `bbox_min_x` (int); `bbox_min_y` (int); `bbox_max_x` (int); `bbox_max_y` (int); `bbox_min_x_norm` (float); `bbox_min_y_norm` (float); `bbox_max_x_norm` (float); `bbox_max_y_norm` (float); `circular_centroid_x_norm` (float); `circular_resultant_x` (float); `representative_x` (int); `representative_y` (int); `touches_left_edge` (bool); `touches_right_edge` (bool); `touches_top_edge` (bool); `touches_bottom_edge` (bool); `touches_both_x_edges` (bool).

### province_state_memberships

`state_record_id` (str); `state_id` (int); `state_key` (str); `province_hex` (str); `province_token` (str); `membership_order` (int); `source_file` (str); `source_line` (int).

### province_to_states

`province_hex` (str); `state_ids` (list); `state_keys` (list); `state_record_ids` (list); `map_present` (bool); `assignment_status` (str).

### state_hubs

`state_record_id` (str); `state_id` (int); `state_key` (str); `hub_type` (str); `province_hex` (str); `raw_value` (str); `value_status` (str); `in_declared_state` (bool); `localization_key` (str); `name_english` (null only); `name_korean` (str); `name_key_derived` (str); `name_key_derived_is_official` (bool); `localized_names` (dict); `map_present` (bool); `centroid_x` (null only); `centroid_y` (null only); `centroid_x_norm` (null only); `centroid_y_norm` (null only); `actual_state_keys` (list).

### state_traits_memberships

`state_record_id` (str); `state_id` (int); `state_key` (str); `trait_key` (str).

### state_resources

`state_record_id` (str); `state_id` (int); `state_key` (str); `resource_kind` (str); `resource_key` (str); `amount` (int); `raw_value` (int/str).

### strategic_regions

`region_record_id` (str); `region_key` (str); `name_english` (null only); `name_korean` (str); `name_key_derived` (str); `name_key_derived_is_official` (bool); `localized_names` (dict); `capital_province_hex` (str); `map_color_raw` (dict); `state_keys` (list); `state_token_count` (int); `state_count` (int); `source_file` (str); `source_line` (int); `raw_fields` (dict); `pixel_area` (int); `area_fraction` (float/int); `centroid_x` (float); `centroid_y` (float); `centroid_x_norm` (float); `centroid_y_norm` (float); `bbox_min_x` (int); `bbox_min_y` (int); `bbox_max_x` (int); `bbox_max_y` (int); `bbox_min_x_norm` (float); `bbox_min_y_norm` (float); `bbox_max_x_norm` (float); `bbox_max_y_norm` (float); `circular_centroid_x_norm` (float); `circular_resultant_x` (float); `defined_state_count` (int); `missing_state_keys` (list); `province_count` (int); `capital_on_map` (bool); `capital_in_declared_region` (bool).

### strategic_region_states

`region_record_id` (str); `region_key` (str); `state_key` (str); `state_ids` (list); `state_record_ids` (list); `state_defined` (bool); `membership_order` (int).

### province_adjacency

`province_hex_a` (str); `province_hex_b` (str); `shared_pixel_edges` (int); `seam_pixel_edges` (int).

### state_adjacency

`state_record_id_a` (str); `state_key_a` (str); `state_id_a` (int); `state_record_id_b` (str); `state_key_b` (str); `state_id_b` (int); `shared_pixel_edges` (int); `seam_pixel_edges` (int).

### province_height_raw

`province_hex` (str); `height_sample_count` (int); `height_raw_sum` (int); `height_raw_min` (int); `height_raw_max` (int); `height_raw_mean` (float).

### state_height_raw

`state_record_id` (str); `state_id` (int); `state_key` (str); `height_sample_count` (int); `height_raw_sum` (int); `height_raw_min` (int); `height_raw_max` (int); `height_raw_mean` (float).

### province_river_palette_counts

`province_hex` (str); `palette_index` (int); `pixel_count` (int).

### river_palette

`palette_index` (int); `rgb_r` (int); `rgb_g` (int); `rgb_b` (int); `map_pixel_count` (int).

### map_object_instances

`source_file` (str); `object_type` (str); `object_name` (str); `instance_index` (int); `instance_id` (int); `position_raw` (list); `x_raw` (float); `y_raw` (float); `z_raw` (float); `rotation_raw` (list); `scale_raw` (list); `state_keys_with_same_numeric_id` (list); `state_match_status` (str); `raw_fields` (dict).

### map_object_groups

`source_file` (str); `source_line` (int); `object_type` (str); `name` (str); `entity` (str); `layer` (str); `declared_count` (int); `instance_count` (int); `raw_fields` (dict).

### map_editor_completion

`editor_category` (str); `raw_identifier` (str); `completed_raw` (str); `province_hex_candidate` (str); `province_hex_on_map` (bool); `state_key_candidate` (null only); `state_record_ids` (list); `interpretation` (str); `source_line` (int).

### country_definitions

`identifier` (str); `name_english` (null only); `name_korean` (str); `name_key_derived` (str); `name_key_derived_is_official` (bool); `localized_names` (dict); `source_file` (str); `source_line` (int); `color_raw` (list); `raw_fields` (dict); `country_tag` (str); `country_type` (str); `tier` (str); `capital_state_key` (str); `culture_keys` (list); `religion_key` (null only); `definition_comment` (str).

### cultures

`identifier` (str); `name_english` (null only); `name_korean` (str); `name_key_derived` (str); `name_key_derived_is_official` (bool); `localized_names` (dict); `source_file` (str); `source_line` (int); `color_raw` (dict/list); `raw_fields` (dict); `religion_key` (str); `traits` (list).

### religions

`identifier` (str); `name_english` (null only); `name_korean` (str); `name_key_derived` (str); `name_key_derived_is_official` (bool); `localized_names` (dict); `source_file` (str); `source_line` (int); `color_raw` (list); `raw_fields` (dict); `religion_key` (null only); `traits` (list).

### state_traits

`identifier` (str); `name_english` (null only); `name_korean` (str); `name_key_derived` (str); `name_key_derived_is_official` (bool); `localized_names` (dict); `source_file` (str); `source_line` (int); `color_raw` (null only); `raw_fields` (dict).

### discrimination_traits

`identifier` (str); `name_english` (null only); `name_korean` (str); `name_key_derived` (str); `name_key_derived_is_official` (bool); `localized_names` (dict); `source_file` (str); `source_line` (int); `color_raw` (null only); `raw_fields` (dict).

### terrain

`identifier` (str); `name_english` (null only); `name_korean` (null only); `name_key_derived` (str); `name_key_derived_is_official` (bool); `localized_names` (dict); `source_file` (str); `source_line` (int); `color_raw` (null only); `raw_fields` (dict).

### country_cultures

`country_tag` (str); `culture_key` (str).

### culture_name_tokens

`culture_key` (str); `name_group` (str); `name_token` (str); `sequence` (int); `localized_names` (dict).

### geographic_identifier_references

`source_file` (str); `source_line` (int); `field_path` (str); `identifier_type` (str); `identifier` (str); `raw_token` (str).

### localization_all

`localization_key` (str); `language` (str); `version` (int); `value` (str); `source_file` (str); `source_line` (int).

### localization_geography

`localization_key` (str); `language` (str); `version` (int); `value` (str); `source_file` (str); `source_line` (int); `entity_type` (str); `matched_definition` (bool); `state_key` (str); `resolved_value` (str).

### localization_unmatched_geography

`localization_key` (str); `language` (str); `version` (int); `value` (str); `source_file` (str); `source_line` (int); `entity_type` (str); `matched_definition` (bool); `state_key` (str); `resolved_value` (str).

### province_terrain_overrides

`province_hex` (str); `terrain_key` (str).

### map_settings

`key` (str); `value` (list/str); `source_line` (int).

### special_adjacencies

`From` (null only); `To` (null only); `Type` (null only); `Through` (null only); `start_x` (null only); `start_y` (null only); `stop_x` (null only); `stop_y` (null only); `adjacency_rule_name` (null only); `Comment` (null only).

### validation_issues

`kind` (str); `entity` (str); `detail` (dict/list/str); `source_file` (str); `line` (int).

### empty_or_unmapped_states

`state_record_id` (str); `state_id` (int); `state_key` (str); `name_korean` (str); `province_count` (int); `present_province_count` (int); `missing_province_count` (int); `geometry_status` (str); `source_file` (str); `source_line` (int).

### source_files

`source_file` (str); `drive_file_id` (str); `drive_url` (str); `mime_type` (str); `drive_size_bytes` (int); `modified_time` (str); `downloaded` (bool); `local_size_bytes` (int); `sha256` (str); `exclusion_reason` (str).

### inspected_history_and_localization_folders

`folder` (str); `direct_child_count` (int); `is_empty` (bool).

### parsed_file_summary

`source_file` (str); `top_level_entries` (int); `parser_issues` (int); `empty_or_comments_only` (bool).

### extraction_summary

`metric` (str); `value` (dict/int/list/str).
