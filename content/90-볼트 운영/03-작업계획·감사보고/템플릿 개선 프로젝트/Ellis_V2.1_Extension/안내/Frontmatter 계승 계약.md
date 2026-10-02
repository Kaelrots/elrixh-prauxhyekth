# Frontmatter 계승 계약

## 단일 원본

운영 양식의 유일한 원본은 기존 `90-볼트 운영/00-템플릿/00-yaml 속성탭.md`다. 확인한 파일은 [공통 Frontmatter SSOT](https://drive.google.com/file/d/1s0KYmVf1bRFq9aHaj4evndys_kgvvW48/view)이며, 원문 내용과 해시는 참고 사본·매니페스트에 기록한다. `render_frontmatter.js`도 확인한 V2 원본을 사용했다.

V2.1 조합기는 양식의 기본 키·타입·열거값을 복제하지 않는다. registry는 시작형의 <font style="font-weight:bold">문서유형·세부유형·분야·사용된 템플릿·템플릿 버전·기준시점</font>만 지정하고, 기존 생성기가 SSOT를 읽어 생성·검사한다. 이번 패키지는 새 공통 키 또는 중첩 확장 키를 요구하지 않는다.

## 생성 기본값

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>항목</th>
      <th>새 문서의 값·생성 방식</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>제목</td>
      <td>Templater 대상 파일 제목</td>
    </tr>
    <tr>
      <td>aliases / tags / 적용범위</td>
      <td>빈 문자열 배열</td>
    </tr>
    <tr>
      <td>정본상태 / 작성상태 / 검토상태</td>
      <td>draft / outline / unreviewed</td>
    </tr>
    <tr>
      <td>draft</td>
      <td>true, 불리언</td>
    </tr>
    <tr>
      <td>작성자</td>
      <td>SSOT의 현카엘</td>
    </tr>
    <tr>
      <td>최초작성일 / 최종수정일</td>
      <td>실행 기기의 현실 시각, SSOT 형식 유지</td>
    </tr>
    <tr>
      <td>문서버전</td>
      <td>0.1.0</td>
    </tr>
    <tr>
      <td>스키마버전</td>
      <td>2.0.0</td>
    </tr>
    <tr>
      <td>사용된 템플릿</td>
      <td>선택한 X21 시작형의 고유 파일명, 확장자 제외</td>
    </tr>
    <tr>
      <td>템플릿 버전</td>
      <td>2.1.0</td>
    </tr>
    <tr>
      <td>기원상태 / 복원여부</td>
      <td>original / false</td>
    </tr>
    <tr>
      <td>기준시점</td>
      <td>null, 이후 작중 시점 입력</td>
    </tr>
  </tbody>
</table></div>

선택 공통 키는 V2 생성기의 규칙에 따라 빈 값일 때 생략될 수 있다. `original`은 새로 작성하는 이 문서의 기원을 가리키며 그 문서가 다루는 천체·시대·종족이 새로 생겼다는 뜻이 아니다. 기존 문서 이관에는 이 기본값을 소급 적용하지 않는다.

## 분류 대응

새 `문서유형` 열거값을 만들지 않는다. `entity`, `period`, `concept`, `reference`, `rule`은 모두 기존 SSOT의 허용값이다. 세부유형은 다음처럼 명시한다.

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>시작형 식별자</th>
      <th>문서유형</th>
      <th>세부유형</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>X21-01-core</td>
      <td>entity</td>
      <td>astronomical_object</td>
    </tr>
    <tr>
      <td>X21-01-detail</td>
      <td>entity</td>
      <td>astronomical_object</td>
    </tr>
    <tr>
      <td>X21-01-galaxy</td>
      <td>entity</td>
      <td>galactic_structure</td>
    </tr>
    <tr>
      <td>X21-01-system</td>
      <td>entity</td>
      <td>stellar_system</td>
    </tr>
    <tr>
      <td>X21-01-star</td>
      <td>entity</td>
      <td>star</td>
    </tr>
    <tr>
      <td>X21-01-planet</td>
      <td>entity</td>
      <td>planet_or_moon</td>
    </tr>
    <tr>
      <td>X21-02-core</td>
      <td>period</td>
      <td>historical_period</td>
    </tr>
    <tr>
      <td>X21-02-detail</td>
      <td>period</td>
      <td>historical_period</td>
    </tr>
    <tr>
      <td>X21-03-core</td>
      <td>entity</td>
      <td>language</td>
    </tr>
    <tr>
      <td>X21-03-detail</td>
      <td>entity</td>
      <td>language</td>
    </tr>
    <tr>
      <td>X21-03-script</td>
      <td>entity</td>
      <td>writing_system</td>
    </tr>
    <tr>
      <td>X21-04-core</td>
      <td>concept</td>
      <td>world_concept</td>
    </tr>
    <tr>
      <td>X21-04-detail</td>
      <td>concept</td>
      <td>world_concept</td>
    </tr>
    <tr>
      <td>X21-04-phenomenon</td>
      <td>concept</td>
      <td>world_phenomenon</td>
    </tr>
    <tr>
      <td>X21-04-law</td>
      <td>rule</td>
      <td>world_law</td>
    </tr>
    <tr>
      <td>X21-05-core</td>
      <td>concept</td>
      <td>ability_system</td>
    </tr>
    <tr>
      <td>X21-05-detail</td>
      <td>concept</td>
      <td>ability_system</td>
    </tr>
    <tr>
      <td>X21-05-ability</td>
      <td>concept</td>
      <td>individual_ability</td>
    </tr>
    <tr>
      <td>X21-06-core</td>
      <td>reference</td>
      <td>reference_guide</td>
    </tr>
    <tr>
      <td>X21-06-detail</td>
      <td>reference</td>
      <td>reference_guide</td>
    </tr>
    <tr>
      <td>X21-06-glossary</td>
      <td>reference</td>
      <td>glossary</td>
    </tr>
    <tr>
      <td>X21-06-taxonomy</td>
      <td>reference</td>
      <td>taxonomy</td>
    </tr>
    <tr>
      <td>X21-06-standard</td>
      <td>reference</td>
      <td>documentation_standard</td>
    </tr>
    <tr>
      <td>X21-07-core</td>
      <td>entity</td>
      <td>species</td>
    </tr>
    <tr>
      <td>X21-07-detail</td>
      <td>entity</td>
      <td>species</td>
    </tr>
    <tr>
      <td>X21-08-core</td>
      <td>entity</td>
      <td>ethnic_group</td>
    </tr>
    <tr>
      <td>X21-08-detail</td>
      <td>entity</td>
      <td>ethnic_group</td>
    </tr>
    <tr>
      <td>X21-09-core</td>
      <td>entity</td>
      <td>cultural_sphere</td>
    </tr>
    <tr>
      <td>X21-09-detail</td>
      <td>entity</td>
      <td>cultural_sphere</td>
    </tr>
    <tr>
      <td>X21-10-core</td>
      <td>entity</td>
      <td>nationality_citizenship_community</td>
    </tr>
    <tr>
      <td>X21-10-detail</td>
      <td>entity</td>
      <td>nationality_citizenship_community</td>
    </tr>
    <tr>
      <td>X21-11-core</td>
      <td>entity</td>
      <td>religious_community</td>
    </tr>
    <tr>
      <td>X21-11-detail</td>
      <td>entity</td>
      <td>religious_community</td>
    </tr>
    <tr>
      <td>X21-12-core</td>
      <td>entity</td>
      <td>speech_community</td>
    </tr>
    <tr>
      <td>X21-12-detail</td>
      <td>entity</td>
      <td>speech_community</td>
    </tr>
  </tbody>
</table></div>

`rule/world_law`는 자연·초자연 법칙에만 쓴다. 국가 법령은 이번 패키지의 대상이 아니다. `entity/species`는 기존 종족 V2와 분류 호환을 유지한다.

## 호환성과 보존

기존 01~11 파일, 번호 없는 종족 V2, 기존 공통 원본·생성기·조회 스크립트는 변경하지 않았다. X21은 확장 식별자이며 기존 템플릿 번호의 재배정이 아니다. 동일 문서의 V2와 V2.1 버전을 자동 병합하지 않는다.

기존 Obsidian 쿼리·Quartz 변환기가 신규 세부유형까지 처리하는지는 별도 확인해야 한다. JSON의 registry와 manifest는 문서 생성·배포 구성 파일이며 새로운 세계관 Frontmatter SSOT가 아니다.
