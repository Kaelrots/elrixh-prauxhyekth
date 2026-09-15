import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"

// 4가지 모달 팝업 대상 정의
const WARNING_DEFINITIONS: Record<string, { badge: string; title: string; desc: string }> = {
  "nsfw-15": {
    badge: "15+",
    title: "연령 제한 (15세 이용가)",
    desc: "만 15세 미만의 청소년에게 부적합한 폭력성, 암투 또는 경미한 선정적 요소가 포함되어 있습니다.",
  },
  "nsfw-18": {
    badge: "19+",
    title: "성인 등급 (청소년 관람불가)",
    desc: "수위 높은 폭력, 잔혹한 유혈 묘사 또는 성인 등급의 설정 및 서사가 포함되어 있습니다.",
  },
  "ai-generated": {
    badge: "AI",
    title: "AI 생성 콘텐츠 포함",
    desc: "문서 내에 인공지능(AI)을 통해 생성된 컨셉 아트, 삽화 이미지 또는 텍스트 데이터가 포함되어 있습니다.",
  },
  "wip": {
    badge: "WIP",
    title: "작업 진행 중 (미완성)",
    desc: "현재 집필 중인 문서입니다. 내용 누락, 설정 오류 또는 예고 없는 대규모 수정이 빈번할 수 있습니다.",
  },
}

const ContentWarning: QuartzComponent = ({ fileData }: QuartzComponentProps) => {
  const rawWarning = fileData.frontmatter?.warning
  if (!rawWarning) return null

  // 문자열 또는 배열 모두 배열 형태로 정규화
  const warningList = Array.isArray(rawWarning) ? rawWarning : [rawWarning]
  
  // 모달 대상 4개 키에 해당하는 것만 필터링
  const activeWarnings = warningList
    .map((w) => String(w).toLowerCase())
    .filter((w) => WARNING_DEFINITIONS[w])
    .map((w) => ({ key: w, ...WARNING_DEFINITIONS[w] }))

  if (activeWarnings.length === 0) return null

  return (
    <div id="content-warning-modal" class="warning-overlay">
      <div class="warning-card">
        <div class="warning-header">
          <span class="warning-icon">⚠️</span>
          <h3>열람 전 주의사항 안내</h3>
        </div>

        <p class="warning-subtext">
          본 문서는 아래와 같은 요소를 포함하고 있습니다. 내용을 확인한 후 열람을 진행해 주세요.
        </p>

        <ul class="warning-items">
          {activeWarnings.map((item) => (
            <li class={`warning-item warning-type-${item.key}`}>
              <div class="item-badge">{item.badge}</div>
              <div class="item-content">
                <strong>{item.title}</strong>
                <p>{item.desc}</p>
              </div>
            </li>
          ))}
        </ul>

        <div class="warning-actions">
          <button id="warning-decline" class="btn-decline">이전으로</button>
          <button id="warning-accept" class="btn-accept">확인 및 계속 읽기</button>
        </div>
      </div>
    </div>
  )
}

ContentWarning.afterDOMLoaded = `
document.addEventListener("nav", () => {
  const modal = document.getElementById("content-warning-modal")
  if (!modal) return

  // 팝업 시 배경 스크롤 차단
  document.body.style.overflow = "hidden"

  const acceptBtn = document.getElementById("warning-accept")
  const declineBtn = document.getElementById("warning-decline")

  acceptBtn?.addEventListener("click", () => {
    modal.style.display = "none"
    document.body.style.overflow = "auto"
  })

  declineBtn?.addEventListener("click", () => {
    if (window.history.length > 1) {
      window.history.back()
    } else {
      window.location.href = "/"
    }
  })
})
`

ContentWarning.css = `
.warning-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.82);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 1rem;
}

.warning-card {
  background: var(--light);
  color: var(--dark);
  border: 1px solid var(--lightgray);
  border-radius: 12px;
  padding: 1.75rem;
  max-width: 520px;
  width: 100%;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.warning-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.warning-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--secondary);
}

.warning-icon {
  font-size: 1.4rem;
}

.warning-subtext {
  margin: 0;
  font-size: 0.9rem;
  color: var(--gray);
  line-height: 1.4;
}

.warning-items {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  max-height: 40vh;
  overflow-y: auto;
}

.warning-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 8px;
  background: var(--highlight);
  border: 1px solid var(--lightgray);
}

.item-badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  background: var(--secondary);
  color: var(--light);
  white-space: nowrap;
  margin-top: 0.1rem;
}

.warning-type-nsfw-18 .item-badge {
  background: #d32f2f;
  color: #ffffff;
}

.warning-type-nsfw-15 .item-badge {
  background: #f57c00;
  color: #ffffff;
}

.warning-type-ai-generated .item-badge {
  background: #1976d2;
  color: #ffffff;
}

.warning-type-wip .item-badge {
  background: #689f38;
  color: #ffffff;
}

.item-content strong {
  display: block;
  font-size: 0.95rem;
  margin-bottom: 0.2rem;
  color: var(--dark);
}

.item-content p {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--darkgray);
}

.warning-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 0.5rem;
}

.warning-actions button {
  padding: 0.55rem 1.1rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  transition: opacity 0.15s ease;
}

.warning-actions button:hover {
  opacity: 0.85;
}

.btn-accept {
  background: var(--secondary);
  color: var(--light);
  border: none;
}

.btn-decline {
  background: transparent;
  border: 1px solid var(--lightgray);
  color: var(--darkgray);
}
`

export default (() => ContentWarning) satisfies QuartzComponentConstructor