import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"

const BLOCKED_ACCESS_VALUES = new Set(["unavailable", "blocked", "locked"])
const BLOCKED_TAGS = new Set(["unavailable", "unreleased", "blocked", "locked"])

function toNormalizedList(value: unknown): string[] {
  if (value === undefined || value === null) return []
  const list = Array.isArray(value) ? value : [value]
  return list.map((item) => String(item).trim().toLowerCase()).filter(Boolean)
}

function isContentBlocked(frontmatter: Record<string, unknown> | undefined): boolean {
  if (!frontmatter) return false

  const access = String(frontmatter.access ?? "").trim().toLowerCase()
  const tags = toNormalizedList(frontmatter.tags)

  return BLOCKED_ACCESS_VALUES.has(access) || tags.some((tag) => BLOCKED_TAGS.has(tag))
}

export default (() => {
  const ContentGate: QuartzComponent = ({ fileData }: QuartzComponentProps) => {
    const frontmatter = fileData.frontmatter as Record<string, unknown> | undefined
    if (!isContentBlocked(frontmatter)) return null

    const customReason = frontmatter?.["access-reason"]
    const reason = customReason ? String(customReason).trim() : ""

    return (
      <div id="content-gate-modal" class="content-gate-overlay" role="dialog" aria-modal="true" aria-labelledby="content-gate-title">
        <div class="content-gate-card">
          <div class="content-gate-header">
            <span class="content-gate-icon" aria-hidden="true">🔒</span>
            <h3 id="content-gate-title">현재 열람할 수 없는 문서입니다</h3>
          </div>

          <p class="content-gate-subtext">
            이 문서는 현재 공개되지 않았거나 열람 준비가 완료되지 않았습니다.
          </p>

          {reason && (
            <div class="content-gate-reason">
              <strong>안내</strong>
              <p>{reason}</p>
            </div>
          )}

          <div class="content-gate-actions">
            <button id="content-gate-back" class="content-gate-back" type="button">이전으로 돌아가기</button>
          </div>
        </div>
      </div>
    )
  }

  ContentGate.afterDOMLoaded = `
  let detachContentGateEvents = () => {}
  const attachContentGateEvents = () => {
    detachContentGateEvents()
    const modal = document.getElementById("content-gate-modal")
    const root = document.documentElement

    root.classList.toggle("content-gate-open", Boolean(modal))
    if (!modal) return

    const backBtn = document.getElementById("content-gate-back")
    const goBack = () => {
      if (window.history.length > 1) {
        window.history.back()
      } else {
        window.location.href = "/"
      }
    }
    backBtn?.addEventListener("click", goBack)
    detachContentGateEvents = () => {
      backBtn?.removeEventListener("click", goBack)
      root.classList.remove("content-gate-open")
    }
    window.addCleanup?.(detachContentGateEvents)
  }

  document.addEventListener("nav", attachContentGateEvents)
  attachContentGateEvents()
  `

  ContentGate.css = `
  html.content-gate-open {
    overflow: hidden;
  }

  .content-gate-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.88);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000000;
    padding: 1rem;
  }

  .content-gate-card {
    background: var(--light);
    color: var(--dark);
    border: 1px solid var(--lightgray);
    border-radius: 12px;
    padding: 1.75rem;
    max-width: 520px;
    width: 100%;
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .content-gate-header {
    display: flex;
    align-items: center;
    gap: 0.65rem;
  }

  .content-gate-header h3 {
    margin: 0;
    font-size: 1.25rem;
    color: #d65a52;
  }

  .content-gate-icon {
    width: 2.35rem;
    min-width: 2.35rem;
    height: 2.35rem;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(211, 47, 47, 0.16);
    font-size: 1.15rem;
  }

  .content-gate-subtext {
    margin: 0;
    font-size: 0.92rem;
    line-height: 1.55;
    color: var(--gray);
  }

  .content-gate-reason {
    padding: 0.9rem 1rem;
    border-radius: 8px;
    border: 1px solid var(--lightgray);
    border-left: 3px solid #d32f2f;
    background: var(--highlight);
  }

  .content-gate-reason strong {
    display: block;
    margin-bottom: 0.25rem;
    font-size: 0.9rem;
    color: var(--dark);
  }

  .content-gate-reason p {
    margin: 0;
    font-size: 0.85rem;
    line-height: 1.5;
    color: var(--darkgray);
  }

  .content-gate-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 0.25rem;
  }

  .content-gate-back {
    padding: 0.6rem 1.1rem;
    border-radius: 6px;
    border: 1px solid var(--lightgray);
    background: var(--secondary);
    color: var(--light);
    cursor: pointer;
    font-weight: 600;
    font-size: 0.9rem;
    transition: opacity 0.15s ease;
  }

  .content-gate-back:hover {
    opacity: 0.85;
  }
  `

  return ContentGate
}) satisfies QuartzComponentConstructor
