# 기술·연구 V2 격리 후보본

11/12 단계. `vault/`는 검토용 배포 경로이며 실제 볼트가 아니다. 상세 내용은 `검증 및 승격 준비 보고.md`를 본다.

신규 빈 문서에 시작형을 삽입한다. Templater 템플릿 폴더는 `90-볼트 운영/00-템플릿`, User Script Folder는 그 아래 `유저 스크립트`다. 구성요소 파일은 직접 실행하는 시작형이 아니다.

공통 파일이 이미 있으면 SHA-256을 대조하고 일치할 때 한 벌만 사용한다. 임의로 기존 파일을 덮어쓰지 않는다.

자동검증 재현: Node.js·Python·PyYAML을 준비하고 `TEMPLATER_BUNDLE`을 Templater 2.13.1 main.js 경로로 지정한 뒤 `node 검증/test_stage.js`, `node 검증/test_stage.js --engine`을 실행한다. GUI·웹 표시는 별도 확인한다.
