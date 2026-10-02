# 개요

> [!abstract] 자원의 한 줄 정의
> {작성}

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th colspan="2"><span style="font-size:1.2em; font-weight:bold;">자원 프로필</span></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>자원명 · 한글 / 엘룬·로마자</td>
      <td>{작성}</td>
    </tr>
    <tr>
      <td>자원 ID</td>
      <td>Frontmatter의 resource_id 참조 · 미정이면 null 유지</td>
    </tr>
    <tr>
      <td>분류·기원</td>
      <td>{작성}</td>
    </tr>
    <tr>
      <td>물리적·차원적 특성</td>
      <td>{작성}</td>
    </tr>
    <tr>
      <td>생성·분포·주요 산지</td>
      <td>{작성}</td>
    </tr>
    <tr>
      <td>매장·생산 · 시점·단위 포함</td>
      <td>{작성}</td>
    </tr>
    <tr>
      <td>가공·표준 정제 단계</td>
      <td>{작성}</td>
    </tr>
    <tr>
      <td>핵심 활용</td>
      <td>{작성}</td>
    </tr>
    <tr>
      <td>경제적 가치·가격 기준</td>
      <td>{작성}</td>
    </tr>
    <tr>
      <td>전략적 가치·대체 가능성</td>
      <td>{작성}</td>
    </tr>
  </tbody>
</table></div>

> [!tip]- 처음 작성할 때
> <font style="font-weight:bold">명칭·분류·생성·주요 활용</font>부터 적는다. `{작성}`·빈칸은 미입력, `미정`은 창작상 미결정, `미상`은 설정 안에서 알려지지 않음, `없음`은 부재 확정, `해당 없음`은 비적용이다. 모든 자원이 마학 반응·영혼 마모·연방 통제의 대상인 것은 아니다.
> resource_id는 확인된 고정 식별자만 직접 기록한다. 현재 시각에서 새 번호를 자동 생성하지 않는다. 기존 식별자가 있다면 이름·정제 단계 변경을 이유로 재발급하지 않는다.

## 분류와 기본 값

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>항목</th>
      <th>값·내용</th>
      <th>척도·단위·조건·근거</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>자원 유형</td>
      <td>{작성}</td>
      <td>에너지·물질·생물·경이·초월·특수·특유 등 선택</td>
    </tr>
    <tr>
      <td>기원·발견 경로·최초 발견 시점</td>
      <td>{작성}</td>
      <td>자연·인공·차원·생체·유물 등 선택</td>
    </tr>
    <tr>
      <td>희귀도 등급 · rarity_grade</td>
      <td>{작성}</td>
      <td>F~SSS 등 채택한 척도 명시</td>
    </tr>
    <tr>
      <td>채굴 난이도 · extraction_difficulty</td>
      <td>{작성}</td>
      <td>1~5 척도는 정의 확인 후 사용</td>
    </tr>
    <tr>
      <td>위험도 · danger_level</td>
      <td>{작성}</td>
      <td>1~5 척도·위험 유형·사고 코드</td>
    </tr>
    <tr>
      <td>전략 우선순위 · strategic_priority</td>
      <td>{작성}</td>
      <td>Low·Medium·High·Critical 등 선택</td>
    </tr>
    <tr>
      <td>거래 상태 · trade_status</td>
      <td>{작성}</td>
      <td>Open·Restricted·Embargo 등 선택</td>
    </tr>
    <tr>
      <td>주요 분야 · primary_domains</td>
      <td>{작성}</td>
      <td>실제 사용 분야·범위</td>
    </tr>
  </tbody>
</table></div>

미입력은 F·1·0·Raw·Open·안전을 뜻하지 않는다. 자원 자체의 위험, 취급 위험, 전략적 중요도는 서로 다른 판단이다.

<hr class="hr-thick-2">

## 공급 가공과 활용 요약

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>산지·생산 주체</th>
      <th>매장·생산량·기간·단위</th>
      <th>가공·제품 단계</th>
      <th>활용·대체재·병목</th>
      <th>관련 지역·국가·기술</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="2">{작성}</td>
      <td>{작성}</td>
      <td>{작성}</td>
      <td>{작성}</td>
      <td>{작성}</td>
    </tr>
    <tr>
      <td>{작성}</td>
      <td>{작성}</td>
      <td>{작성}</td>
      <td>{작성}</td>
    </tr>
  </tbody>
</table></div>

매장량·채굴 가능량·기간 생산량·재고를 구별한다. 지역 분포와 국가의 소유·통제는 동일하지 않다.

<hr class="hr-thick-3">

## 가격과 가치

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>가격·가치</th>
      <th>단위·통화</th>
      <th>정제 등급·지역·기준 시점</th>
      <th>근거·불확실성</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>{작성}</td>
      <td>{작성}</td>
      <td>{작성}</td>
      <td>{작성}</td>
    </tr>
  </tbody>
</table></div>

standard_price는 조건이 갖춰진 가격만 기록한다. 가격이 없거나 거래되지 않는다는 사실을 가치 0으로 바꾸지 않는다. 원본의 resource_name·resource_name_roman은 프로필의 명칭, standard_refinement_tier는 가공 단계에 대응한다. 구식 인용 YAML 블록은 실제 Frontmatter 인덱스가 아니므로 새 문서에 중복 인덱스로 복사하지 않는다.
