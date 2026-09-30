---
제목: <% tp.file.title %>
작성자: 현카엘
최초작성일: <% tp.date.now("YYYY-MM-DDTHH:mm:ss") %>
최종수정일: <% tp.date.now("YYYY-MM-DDTHH:mm:ss") %>
문서버전: "0.1"
최근 변경 요약:
복원여부: <% (tp.frontmatter["기원상태"] === "restored" || tp.frontmatter["복원여부"] === true || (tp.frontmatter["기원상태"] === undefined && tp.frontmatter["복원여부"] === undefined && false)) %>
사용된 템플릿:
템플릿 버전:
태그:
  - <% tp.file.title %>
분야: []
문서유형: reference
적용범위: []
정본상태: <% ["canon", "provisional", "draft", "archival"].includes(tp.frontmatter["정본상태"]) ? tp.frontmatter["정본상태"] : "draft" %>
기원상태: <% (tp.frontmatter["기원상태"] === "restored" || tp.frontmatter["복원여부"] === true || (tp.frontmatter["기원상태"] === undefined && tp.frontmatter["복원여부"] === undefined && false)) ? "restored" : "original" %>
복원원문문서명: <% JSON.stringify(tp.frontmatter["복원원문문서명"] ?? "미상") %>
복원원문최초작성일: <% JSON.stringify(tp.frontmatter["복원원문최초작성일"] ?? "미상") %>
복원원문최종수정일: <% JSON.stringify(tp.frontmatter["복원원문최종수정일"] ?? "미상") %>
---