import { QuartzComponent, QuartzComponentConstructor } from "./types"
import style from "./styles/imageViewer.scss"
// @ts-ignore
import script from "./scripts/imageViewer.inline"

export default (() => {
  const ImageViewer: QuartzComponent = () => (
    <dialog id="quartz-image-viewer" class="image-viewer" aria-label="이미지 확대 보기">
      <div class="image-viewer-toolbar">
        <p class="image-viewer-title">이미지</p>
        <div class="image-viewer-controls" role="group" aria-label="이미지 보기 설정">
          <button type="button" data-image-action="out" aria-label="이미지 축소" title="축소 (-)">
            −
          </button>
          <output class="image-viewer-scale" aria-label="이미지 배율">
            100%
          </output>
          <button type="button" data-image-action="in" aria-label="이미지 확대" title="확대 (+)">
            +
          </button>
          <button type="button" data-image-action="fit" title="화면에 맞추기 (0)">
            맞춤
          </button>
          <a class="image-viewer-original" target="_blank" rel="noopener noreferrer">
            원본 ↗
          </a>
          <button
            type="button"
            data-image-action="close"
            aria-label="이미지 확대 보기 닫기"
            title="닫기 (Esc)"
            autofocus
          >
            ×
          </button>
        </div>
      </div>
      <div
        class="image-viewer-viewport"
        tabindex={0}
        aria-label="이미지 영역. 확대 후 드래그하거나 방향키로 이동할 수 있습니다."
      >
        <img class="image-viewer-image" alt="" draggable={false} />
        <p class="image-viewer-error" role="status" hidden>
          이미지를 불러오지 못했어요. 원본을 열어 확인해 주세요.
        </p>
      </div>
      <p class="image-viewer-hint">버튼·두 손가락으로 확대 · 드래그로 이동</p>
    </dialog>
  )

  ImageViewer.css = style
  ImageViewer.afterDOMLoaded = script
  return ImageViewer
}) satisfies QuartzComponentConstructor
