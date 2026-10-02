# Harhaziel 은하 에디터 — EXE 전환 세부 계획서

버전: 1.0 · 작성일: 2026-10-02 · 실행 대상: `Kaelrots/galaxy-editor`
계획 상태: <font style="font-weight:bold">사전조사·계획 작성 / 코드 수정·실행·패키징 미실시</font>
공통 기준: `00_공통_EXE전환_실행기준.md` · 근거: `05_사전조사_근거와미확인사항.md`

## 1. 전환 판단

이번 은하 전환의 기본 방향은 <font style="font-weight:bold">기존 M6 편집기와 프로젝트 codec을 유지한 Electron 데스크톱 어댑터 추가</font>다. 기존 서버를 EXE에서 다시 띄워 브라우저를 여는 방식이나 PixiJS 렌더러 전면 교체를 첫 선택으로 삼지 않는다. 단, 로컬 최신 코드의 런타임 요구를 확인해 최소 실행 관문으로 적용 가능성을 검증한다.

원격 README는 이미 편집·Undo·프로젝트 저장·복구·Worker 생성·대표 은하를 설명한다. 반면 행성 원격은 편집·저장이 후속 단계이므로, <font style="font-weight:bold">현재 근거상 첫 이식 후보는 은하</font>다. 이 판단은 코드 실행성·수정량·성능 향상의 확정 판정은 아니다. [G1–G3, P3–P4]

## 2. 사전 확인된 기준과 미확인 경계

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>항목</th>
      <th>조회한 기준</th>
      <th>실행 전에 확인할 것</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>저장소/기준</td>
      <td>`Kaelrots/galaxy-editor`, `main`, `5e4466cfdab3b8d8cebfedc79d1d8f956631f86f`</td>
      <td>로컬 HEAD·다른 진행 브랜치·미커밋 작업</td>
    </tr>
    <tr>
      <td>앱 위치</td>
      <td>저장소의 `app/`에 `package.json`, README</td>
      <td>실제 루트·도구·배포 위치</td>
    </tr>
    <tr>
      <td>기술 선언</td>
      <td>React/TypeScript/Vite/PixiJS, fflate, Papa Parse</td>
      <td>lockfile·Worker URL·번들 자산·실행 호환성</td>
    </tr>
    <tr>
      <td>현재 실행 설명</td>
      <td>CMD→Node 로컬 서버→브라우저</td>
      <td>EXE에서는 개발 서버와 외부 브라우저 의존 제거</td>
    </tr>
    <tr>
      <td>프로젝트</td>
      <td>형식 6; 과거 1–5 읽기; `.harhaziel` 저장·`.haraziel` 읽기</td>
      <td>실제 codec·마이그레이션·표본별 보존</td>
    </tr>
    <tr>
      <td>복구</td>
      <td>IndexedDB, 프로필·로컬 주소/포트 영향</td>
      <td>네이티브 복구의 분리·기존 파일 이관</td>
    </tr>
    <tr>
      <td>큰 표본</td>
      <td>참고 은하 37,219성계/71,938항로; 생성 최대 50,000</td>
      <td>실제 파일 위치·내용 해시·재현 가능한 생성 조건</td>
    </tr>
    <tr>
      <td>확장</td>
      <td>M7 문서 연결은 9월 가이드상 설계</td>
      <td>로컬에 실제 추가되었는지 확인; 미구현이면 전환에 끼워 넣지 않음</td>
    </tr>
  </tbody>
</table></div>

README의 검사·규모 설명은 기존 문서의 주장이다. 이번 계획 작성에서 앱을 실행해 재검증한 것은 아니다. [G1–G4]

## 3. 제품 설정 초안

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>설정</th>
      <th>이번 제안</th>
      <th>결정 규칙</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>표시 이름</td>
      <td>`Harhaziel 은하 편집기`</td>
      <td>기존 제품 이름 유지</td>
    </tr>
    <tr>
      <td>내부/실행 이름</td>
      <td>ASCII 고유 이름, 예: `HarhazielGalaxyEditor.exe`</td>
      <td>빌더·기존 배포와 충돌 검사 후 A에서 확정</td>
    </tr>
    <tr>
      <td>사용자 프로필</td>
      <td>은하 전용 userData·복구·캐시·로그</td>
      <td>도시·행성·브라우저 저장소와 분리</td>
    </tr>
    <tr>
      <td>로컬 scheme</td>
      <td>제품별 제한 scheme 후보</td>
      <td>Worker/자산/CSP 검사를 통과한 방식 채택</td>
    </tr>
    <tr>
      <td>파일 연결</td>
      <td>최초 전환 기본 제외</td>
      <td>`.harhaziel`을 열 수 있는 기능과 OS 연결 등록은 별개</td>
    </tr>
    <tr>
      <td>정본 저장</td>
      <td>기존 `.harhaziel` 및 현행 형식</td>
      <td>편의상 `.galaxy`나 `.citymap`로 바꾸지 않음</td>
    </tr>
    <tr>
      <td>출력</td>
      <td>CSV ZIP·PNG</td>
      <td>정본 프로젝트 저장과 분리</td>
    </tr>
    <tr>
      <td>배포</td>
      <td>Windows 대상, 무설치 폴더+설치본</td>
      <td>CPU 아키텍처·지원 OS는 실제 PC에서 확인</td>
    </tr>
  </tbody>
</table></div>

도시의 저장 상한을 복사하지 않는다. 원격 README에 있는 <font style="font-weight:bold">압축 64MiB/해제 256MiB, CSV 합계 64MiB</font>를 우선 호환 기준으로 대조하고, 확장이 필요하면 한도·공격 방어·성능·과거 입력 회귀를 함께 변경한다. [G3, R0 §4]

## 4. 보존해야 할 데이터 계약

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>데이터 영역</th>
      <th>보존할 의미</th>
      <th>회귀</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>성계 ID</td>
      <td>문자열 그대로, `0017`과 `17` 구분</td>
      <td>G02</td>
    </tr>
    <tr>
      <td>좌표/원문</td>
      <td>기존 지도 좌표, 추가 CSV 열, 원본 CSV, `r_kpc`</td>
      <td>G03–G04</td>
    </tr>
    <tr>
      <td>성계 편집</td>
      <td>다중 이동·복제·삭제의 원자성, 연결 항로 동반 처리</td>
      <td>G05–G07</td>
    </tr>
    <tr>
      <td>정치 관계</td>
      <td>소유와 점령 분리, 수도·섹터·속국·연방·탐사 참조</td>
      <td>G08–G10</td>
    </tr>
    <tr>
      <td>연결망</td>
      <td>항로 종류·방향·활성·권한·게이트웨이 네트워크</td>
      <td>G11–G12</td>
    </tr>
    <tr>
      <td>생성</td>
      <td>현재 생성기와 재현용 v1의 seed·매개변수·결과</td>
      <td>G13–G14</td>
    </tr>
    <tr>
      <td>지도 표현</td>
      <td>수동/자동 국경, 사용자 지도 구간, 배경·레이어·주석</td>
      <td>G15–G17</td>
    </tr>
    <tr>
      <td>출력</td>
      <td>PNG 구도·크기·한글, CSV의 원본 열과 축약 경고</td>
      <td>G18–G19</td>
    </tr>
    <tr>
      <td>이력/화면</td>
      <td>보기 변경은 좌표 변경이 아님; 재열기 시 Undo 초기화 정책</td>
      <td>G21, C32</td>
    </tr>
    <tr>
      <td>문서 연결</td>
      <td>현행 구현 시 참조·출처·미연결 상태만 보존</td>
      <td>G26</td>
    </tr>
  </tbody>
</table></div>

기존 파일의 전체 의미를 비교한다. 객체 개수만 같다고 통과하지 않는다. 무순서 컬렉션만 계약에 따라 정규화하고, 순서가 의미 있는 레이어·행·제어점·우선순위는 그대로 비교한다. 부동소수 좌표는 무손실 왕복을 우선하며 허용 오차가 필요하면 측정 전에 계약으로 고정한다.

파일 저장에 포함되지 않던 Undo 이력을 새로 영구 저장하는 것은 기본 범위가 아니다. 대신 세션 안에서 Undo/Redo로 돌아온 데이터가 저장·재열기 후 동일한지 검사한다. 과거 형식의 원본은 읽기만 하고 자동 덮어쓰지 않는다. [G3]

## 5. 표본 묶음과 기준 측정

아래 이름과 소규모 구성은 <font style="font-weight:bold">새 시험 제안</font>이며 실세계관 설정이 아니다.

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>표본</th>
      <th>내용</th>
      <th>용도</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>GX-S</td>
      <td>8개 성계, 소수 국가·섹터·항로, `0017`/`17`, 한글·추가 열, 작은 배경 이미지</td>
      <td>매 변경 후 빠른 실행·전체 의미 왕복</td>
    </tr>
    <tr>
      <td>GX-V</td>
      <td>존재하는 형식 1–6 및 두 확장자의 원본 사본</td>
      <td>읽기 호환·명시적 이관·미래 형식 거부</td>
    </tr>
    <tr>
      <td>GX-R</td>
      <td>실제 제공되는 37,219/71,938 참고 은하</td>
      <td>대표 열기·선택·이동·저장; 존재와 내용은 A에서 확인</td>
    </tr>
    <tr>
      <td>GX-L</td>
      <td>현행 생성기로 만든 50,000성계, 고정 seed·매개변수·최대 길이 한글 템플릿</td>
      <td>생성·파일 크기·저장·재열기·메모리</td>
    </tr>
    <tr>
      <td>GX-A</td>
      <td>기존에 열리는 PNG/JPEG/WebP, 투명도·색상 프로필 등 호환 표본</td>
      <td>이미지 디코더 변경과 PNG 출력</td>
    </tr>
    <tr>
      <td>GX-BAD</td>
      <td>깨진 참조, 중복 ID, 미래 형식, 손상 ZIP, 한도 초과</td>
      <td>현재 작업 보존·진단·복구</td>
    </tr>
  </tbody>
</table></div>

실제 파일이 없으면 검증된 합성 표본을 사용하되 GX-R 실자료 인수는 BLOCKED_INPUT이다. 단순히 같은 객체 수를 합성했다고 실자료 검사로 표기하지 않는다. 각 표본에 입력 해시·포맷·개수·자산 수·예상 내용·생성 경로를 기록한다.

## 6. 단계별 작업 목록

### A. 착수 조사와 작업 영역 보호

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>작업 ID</th>
      <th>세부 작업</th>
      <th>산출물</th>
      <th>완료 기준</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>GX-A1</td>
      <td>로컬 경로, AGENTS/요구 문서, Git/미커밋 변경, 원격과 차이 확인</td>
      <td>`reports/desktop/initial-audit.md`</td>
      <td>실제 작업 기준과 보호 대상 명시</td>
    </tr>
    <tr>
      <td>GX-A2</td>
      <td>진입점·렌더러·codec·IndexedDB·다운로드·Worker·Undo 경로 조사</td>
      <td>모듈 대응표와 앱 설정</td>
      <td>실제 파일로 경계 확인; 미확인 별도</td>
    </tr>
    <tr>
      <td>GX-A3</td>
      <td>도시의 main/preload/storage/검사 파일과 공급 커밋 확인</td>
      <td>reuse-map</td>
      <td>재사용·수정·비대상 및 대응 테스트</td>
    </tr>
    <tr>
      <td>GX-A4</td>
      <td>기존 배포·사용자 데이터·대표 자료를 새 작업과 분리</td>
      <td>백업/fixture manifest</td>
      <td>원본 해시·브라우저 복구 이관 절차 확보</td>
    </tr>
  </tbody>
</table></div>

기존 `app/README.md`와 `app/package.json`은 확인된 경로다. core/model·codec·저장 모듈 등은 이름을 추측해 파일을 만들지 않고 실제 파일 목록과 호출을 확인해 대응한다. 조사 첫 결과는 한 장으로 요약한다.

### B. 웹 기준선과 작은 왕복

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>작업 ID</th>
      <th>세부 작업</th>
      <th>산출물</th>
      <th>완료 기준</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>GX-B1</td>
      <td>기존 잠금 설치와 `build/test/test:ui`를 실제 정의대로 실행</td>
      <td>baseline 검증 기록</td>
      <td>기존 실패와 환경 차단을 분리</td>
    </tr>
    <tr>
      <td>GX-B2</td>
      <td>GX-S의 열기→이동/필드수정→Undo/Redo→정본 저장→새 세션 열기</td>
      <td>전체 데이터 비교 결과</td>
      <td>참조·원문·화면 설정 보존</td>
    </tr>
    <tr>
      <td>GX-B3</td>
      <td>대표 표본에서 내부 처리·사용자 완료·메모리 기준 수집</td>
      <td>baseline-performance</td>
      <td>입력 해시·환경·명령·분리된 측정값</td>
    </tr>
  </tbody>
</table></div>

`setup:browser`가 Bash에 의존한다면 Windows 실행 환경에 맞는 기존 경로를 확인한다. 테스트 도구 준비 문제를 앱 결함으로 단정하거나 실행되지 않은 UI 검사를 PASS 처리하지 않는다.

### C. 최소 EXE — 기존 제품 경계를 유지

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>작업 ID</th>
      <th>세부 작업</th>
      <th>산출물</th>
      <th>완료 기준</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>GX-C1</td>
      <td>앱 설정·main·preload·제한된 권한 API, 빌드된 화면 로드</td>
      <td>개발용 데스크톱 실행</td>
      <td>외부 Chrome·로컬 서버 없이 시작</td>
    </tr>
    <tr>
      <td>GX-C2</td>
      <td>PixiJS·Worker·이미지·폰트·자산 URL 연결, 웹 플랫폼 분기</td>
      <td>자산 검사와 네이티브 어댑터</td>
      <td>오프라인과 한국어/공백 경로 통과</td>
    </tr>
    <tr>
      <td>GX-C3</td>
      <td>기존 codec을 네이티브 파일 열기·저장 서비스에 연결</td>
      <td>native-smoke·저장 파일</td>
      <td>GX-S 편집→저장→재열기→종료 전체 통과</td>
    </tr>
    <tr>
      <td>GX-C4</td>
      <td>파일 메뉴·Ctrl+S·다른 이름 저장·최근 파일·미저장 안내</td>
      <td>실제 UI 검사</td>
      <td>취소/실패는 저장 성공 아님; IME와 입력 Undo 보호</td>
    </tr>
  </tbody>
</table></div>

소규모 C 관문 전에는 설치본·50,000성계 반복 부하·엔진 최적화를 시작하지 않는다. 최근 파일은 실제 성공적으로 연 경로만 기록하고, 사라진 파일은 경고·목록 정리 대상으로 처리한다. 존재하지 않는 프로젝트를 새 빈 파일로 덮어쓰지 않는다.

### D. 저장·복구·도메인 회귀

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>작업 ID</th>
      <th>세부 작업</th>
      <th>산출물</th>
      <th>완료 기준</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>GX-D1</td>
      <td>네이티브 세대 저장·읽기 검증·복구 목록·보존 예산</td>
      <td>storage/recovery 계약과 검사</td>
      <td>이전 정상본 보존; 이전 세대 사유 표시</td>
    </tr>
    <tr>
      <td>GX-D2</td>
      <td>저장 중 편집·연속 저장·오래된 요청·renderer 교체·종료/재시작</td>
      <td>오류 주입 결과</td>
      <td>요청과 snapshot 일치; 잘못된 dirty 해제 없음</td>
    </tr>
    <tr>
      <td>GX-D3</td>
      <td>원래 브라우저의 중요 복구본을 파일로 내보내 데스크톱에 이관</td>
      <td>migration 결과</td>
      <td>프로젝트별 전체 비교, 원래 DB 보존</td>
    </tr>
    <tr>
      <td>GX-D4</td>
      <td>성계/정치/항로/생성/이미지/CSV/PNG 전 영역의 기존 계약 재검사</td>
      <td>G01–G28 및 공통 C 검사</td>
      <td>기능 축소·정본 누락·새 참조 오류 없음</td>
    </tr>
  </tbody>
</table></div>

기존 웹 복구 세대 수를 도시의 20세대/7일 정책으로 자동 교체하지 않는다. 네이티브 복구 보존은 새 정책으로 명시하고 대형 프로젝트의 디스크 예산을 함께 측정한다. 손상된 snapshot도 조사 사본으로 남기되 사용자 경로나 개인 데이터가 로그 전문으로 유출되지 않게 한다.

### E. 측정으로 필요한 최적화만 수행

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>작업 ID</th>
      <th>세부 작업</th>
      <th>산출물</th>
      <th>완료 기준</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>GX-E1</td>
      <td>GX-R/GX-L 열기·pan/zoom·선택·드래그 확정·Undo·저장·재열기</td>
      <td>성능 비교표</td>
      <td>같은 입력·뷰포트·조건, 단독 실행</td>
    </tr>
    <tr>
      <td>GX-E2</td>
      <td>병목별 한 가지 변경: codec 복사, 그래프 계산, 국경, 라벨, GPU/장면 캐시</td>
      <td>근거·전후 비교·정확성 회귀</td>
      <td>효과가 있거나 되돌림 사유 명시</td>
    </tr>
    <tr>
      <td>GX-E3</td>
      <td>반복 열기/닫기·생성 취소·이미지 교체 후 자원 해제</td>
      <td>제한된 반복 안정성 결과</td>
      <td>Worker·GPU 자원·object URL 누적 확인</td>
    </tr>
  </tbody>
</table></div>

추천 측정 항목은 열기/직렬화/압축/I/O, 그래프 Worker, 생성기, 국경 재계산, 라벨·히트테스트, 프레임·프로세스 메모리다. 이는 병목 <font style="font-weight:bold">후보</font>이지 현재 확인된 원인이 아니다. 화면 밖 객체 생략·국소 갱신·전송 방식 변경은 측정으로 필요성이 확인된 것만 적용한다.

### F. 최종 고정과 배포

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>작업 ID</th>
      <th>세부 작업</th>
      <th>산출물</th>
      <th>완료 기준</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>GX-F1</td>
      <td>최종 전체 회귀 후 빌드 입력 목록·해시·lockfile·앱 설정 고정</td>
      <td>release manifest</td>
      <td>작업 중 바뀐 소스/오래된 dist 혼입 없음</td>
    </tr>
    <tr>
      <td>GX-F2</td>
      <td>새 generation의 무설치 폴더, 포함/제외 자산 대조</td>
      <td>무설치 배포·해시·실제 실행 결과</td>
      <td>저장·복구·PNG/CSV가 실제 패키지에서 동작</td>
    </tr>
    <tr>
      <td>GX-F3</td>
      <td>설치본·설치/업데이트/제거 시험·서명 상태·최상위 실행 안내</td>
      <td>설치본·사용법·바로가기</td>
      <td>설치 여부·서명 여부·데이터 보존 별도 기록</td>
    </tr>
  </tbody>
</table></div>

개발기의 Node가 PATH에 있는 상태의 실행만으로 ‘별도 Node 설치 불필요’라고 판정하지 않는다. 외부 Node 없이 동작하는 환경에서 검사한다. 무설치 폴더 전체를 배포하며 EXE만 옮기면 된다고 안내하지 않는다.

### G. 두 PC 인계

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>작업 ID</th>
      <th>세부 작업</th>
      <th>산출물</th>
      <th>완료 기준</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>GX-G1</td>
      <td>작은 파일과 대표 파일을 A→Drive→B로 전달·재열기</td>
      <td>전달 manifest·B 결과</td>
      <td>데이터·이미지·참조 동일, 브라우저 DB 비의존</td>
    </tr>
    <tr>
      <td>GX-G2</td>
      <td>B 편집→새 전달본→A 확인, 설치/제거·충돌 사본 검수</td>
      <td>최종 인수 보고</td>
      <td>양방향 이어쓰기와 원본 보존; 미실시는 미완료</td>
    </tr>
  </tbody>
</table></div>

M7 외부 문서 참조가 실제 구현된 경우 문서/자산의 전달 범위와 누락 안내를 추가한다. 참조가 끊겼다고 이름으로 다른 성계나 문서를 자동 연결하지 않는다.

## 7. 호환성과 사용자 경험 인수

정본 프로젝트 저장·CSV 교환·PNG 출력·복구 snapshot은 별도 동작과 상태로 표시한다. CSV에는 포함되지 않는 정치/행정 정보가 있다는 기존 경고를 유지하고 CSV만 저장한 상태를 ‘전체 프로젝트 백업 완료’로 안내하지 않는다. [G3]

다중 성계 이동은 끝점과 연결 항로가 함께 이동하고 한 번의 Undo로 복원되어야 한다. 생성 미리보기·취소는 현재 프로젝트를 변경하지 않는다. Worker의 옛 경로/생성 결과는 다른 프로젝트나 새 revision에 적용하지 않는다. 한글 입력 중 전역 단축키가 조합 문자열을 훼손하지 않아야 한다.

PNG 출력은 기존 1536/3072/4096px 선택과 구도·레이어·한글 표시를 검증한다. 저장할 이미지에 편집 선택 표식·사이드 패널이 섞이지 않는지 확인한다. 이미지 디코더를 바꿀 때 기존에 열리던 입력을 거부하는 회귀가 생기면 검증을 우회하지 말고 호환 경로를 검토한다.

## 8. 중단·분리 조건

<div class="scroll-x nowrap"><table>
  <thead>
    <tr>
      <th>상황</th>
      <th>조치</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>로컬 최신 코드가 원격보다 크게 다름</td>
      <td>원격 기준을 강제하지 않고 A 대응표 갱신</td>
    </tr>
    <tr>
      <td>기존 웹에서도 작은 왕복이 실패</td>
      <td>기존 결함을 분리 수정·재검사한 뒤 이식</td>
    </tr>
    <tr>
      <td>창/자산 실패</td>
      <td>C에 머물러 origin·scheme·Worker·환경 진단</td>
    </tr>
    <tr>
      <td>저장 의미 누락·이전 정상본 손상</td>
      <td>배포 중단; 저장 경계만 수정하고 전체 왕복 재검사</td>
    </tr>
    <tr>
      <td>실제 기능이 문서와 다름</td>
      <td>차이를 보고하고 구현 여부에 맞춰 테스트 범위 재정의</td>
    </tr>
    <tr>
      <td>최적화가 모델·파일 형식 대규모 교체를 요구</td>
      <td>기본 EXE 전환과 분리한 후속 ADR로 기록</td>
    </tr>
    <tr>
      <td>실기기/실자료 접근 불가</td>
      <td>해당 인수만 BLOCKED/NOT_RUN; 합성 결과로 대체 완료 금지</td>
    </tr>
  </tbody>
</table></div>

## 9. 최종 산출물과 인계 조건

제품별 상태 정본, 실제 모듈 대응표·제품 설정, 웹/데스크톱 연결 코드, 보존·이관 안내, fixture manifest, 공통 C·은하 G·배포 R 검사 결과, 전후 성능 기록, 빌드 출처 manifest, 무설치 폴더·설치본·해시·실행 안내를 남긴다.

<font style="font-weight:bold">합격 문장 예시:</font> ‘은하 편집기 [commit/build]의 기존 형식·편집·저장·복구와 패키지 실행은 [환경]에서 PASS. [입력]의 두 PC 왕복은 [상태]. 실행 위치는 [실제 경로]. 남은 차단은 [항목].’ 검사하지 않은 대상에는 이 문장을 확장하지 않는다.
