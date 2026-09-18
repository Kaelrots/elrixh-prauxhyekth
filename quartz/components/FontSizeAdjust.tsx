import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
// @ts-ignore
import script from "./scripts/readingSettings.inline"
import style from "./styles/readingSettings.scss"

const FontSizeAdjust: QuartzComponent = ({ displayClass }: QuartzComponentProps) => {
  return (
    <div class={`reading-settings ${displayClass ?? ""}`}>
      <button
        type="button"
        class="reading-settings-trigger"
        aria-label="읽기 설정"
        title="읽기 설정"
        aria-haspopup="dialog"
        aria-controls="reading-settings-dialog"
        aria-expanded="false"
      >
        <span aria-hidden="true">Aa</span>
      </button>
      <dialog
        id="reading-settings-dialog"
        class="reading-settings-dialog"
        aria-labelledby="reading-settings-title"
      >
        <div class="reading-settings-header">
          <h2 id="reading-settings-title">읽기 설정</h2>
          <button type="button" class="reading-settings-close" aria-label="읽기 설정 닫기">
            <span aria-hidden="true">×</span>
          </button>
        </div>
        <fieldset>
          <legend>글자 크기</legend>
          <div class="reading-font-controls">
            <button type="button" data-font-step="-1" aria-label="글자 크기 줄이기">
              A−
            </button>
            <output class="reading-font-size" aria-live="polite" aria-label="현재 글자 크기">
              100%
            </output>
            <button type="button" data-font-step="1" aria-label="글자 크기 키우기">
              A+
            </button>
          </div>
          <button type="button" class="reading-font-reset">
            기본 크기로 복원
          </button>
        </fieldset>
        <fieldset>
          <legend>화면 테마</legend>
          <div class="reading-theme-options">
            {[
              ["light", "밝게"],
              ["dark", "어둡게"],
              ["system", "시스템"],
            ].map(([value, label]) => (
              <label>
                <input type="radio" name="reading-theme" value={value} />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <label class="reading-mode-option">
          <input type="checkbox" class="reading-mode-input" />
          <span>
            <strong>본문 집중 모드</strong>
            <small>탐색 패널을 숨겨 읽기에 집중해요.</small>
          </span>
        </label>
      </dialog>
    </div>
  )
}

// Apply preferences before paint; the interactive script takes over after navigation.
FontSizeAdjust.beforeDOMLoaded = `
(() => {
  const read = (key) => { try { return localStorage.getItem(key) } catch { return null } }
  const root = document.documentElement
  const savedTheme = read("theme")
  const preference = savedTheme === "light" || savedTheme === "dark" ? savedTheme : "system"
  const theme = preference === "system"
    ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    : preference
  const savedSize = read("customFontSize")
  const size = savedSize?.trim() && Number.isFinite(Number(savedSize))
    ? Math.min(1.8, Math.max(0.8, Math.round(Number(savedSize) * 10) / 10)) : 1
  root.setAttribute("saved-theme", theme)
  root.setAttribute("theme-preference", preference)
  root.setAttribute("reader-mode", read("reader-mode") === "on" ? "on" : "off")
  root.style.setProperty("--reading-font-scale", String(size))
})()
`
FontSizeAdjust.afterDOMLoaded = script
FontSizeAdjust.css = style

export default (() => FontSizeAdjust) satisfies QuartzComponentConstructor
