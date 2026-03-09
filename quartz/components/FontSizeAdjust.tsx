import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"

const FontSizeAdjust: QuartzComponent = ({ displayClass }: QuartzComponentProps) => {
  return (
    <div class={`font-size-adjust ${displayClass ?? ""}`}>
      <span class="font-label">본문 크기</span>
      <button id="font-decrease" class="font-btn" aria-label="글씨 크기 줄이기">A-</button>
      <button id="font-increase" class="font-btn" aria-label="글씨 크기 키우기">A+</button>
    </div>
  )
}

FontSizeAdjust.beforeDOMLoaded = `
  // 쿼츠의 SPA 라우팅(페이지 이동) 이벤트에 맞춰 실행
  document.addEventListener("nav", () => {
    const article = document.querySelector("article");
    const btnInc = document.getElementById("font-increase");
    const btnDec = document.getElementById("font-decrease");
    
    // 브라우저에 저장된 폰트 크기 불러오기 (기본값 1)
    let currentSize = localStorage.getItem("customFontSize") ? parseFloat(localStorage.getItem("customFontSize")) : 1;

    const updateFontSize = (size) => {
      if (article) {
        // 본문 크기 변경 (rem 단위 사용)
        article.style.fontSize = size + "rem";
      }
    };

    // 페이지 접속 시 저장된 폰트 크기 즉시 적용
    updateFontSize(currentSize);

    // 버튼 클릭 이벤트 설정
    if (btnInc && btnDec && article) {
      btnInc.addEventListener("click", () => {
        currentSize = Math.min(currentSize + 0.1, 2.0); // 최대 2배까지 확대
        updateFontSize(currentSize);
        localStorage.setItem("customFontSize", currentSize);
      });
      
      btnDec.addEventListener("click", () => {
        currentSize = Math.max(currentSize - 0.1, 0.7); // 최소 0.7배까지 축소
        updateFontSize(currentSize);
        localStorage.setItem("customFontSize", currentSize);
      });
    }
  })
`

FontSizeAdjust.css = `
  .font-size-adjust {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
    margin-bottom: 1.5rem;
  }
  .font-label {
    font-size: 0.85rem;
    color: var(--gray);
    margin-right: 0.2rem;
  }
  .font-btn {
    background: var(--lightgray);
    border: 1px solid var(--gray);
    padding: 0.2rem 0.6rem;
    border-radius: 5px;
    cursor: pointer;
    color: var(--darkgray);
    font-weight: bold;
    transition: all 0.2s ease;
  }
  .font-btn:hover {
    background: var(--secondary);
    color: var(--light);
  }
`

export default (() => FontSizeAdjust) satisfies QuartzComponentConstructor