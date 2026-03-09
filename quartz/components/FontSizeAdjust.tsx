import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"

const FontSizeAdjust: QuartzComponent = ({ displayClass }: QuartzComponentProps) => {
  return (
    <div class={`font-size-adjust-floating ${displayClass ?? ""}`}>
      <button id="font-increase" class="font-btn" aria-label="글씨 크기 키우기">A+</button>
      <div class="font-divider"></div>
      <button id="font-decrease" class="font-btn" aria-label="글씨 크기 줄이기">A-</button>
    </div>
  )
}

FontSizeAdjust.beforeDOMLoaded = `
  document.addEventListener("nav", () => {
    const article = document.querySelector("article");
    const btnInc = document.getElementById("font-increase");
    const btnDec = document.getElementById("font-decrease");
    
    // 저장된 폰트 크기 불러오기 (기본 1)
    let currentSize = localStorage.getItem("customFontSize") ? parseFloat(localStorage.getItem("customFontSize")) : 1;

    const updateStyle = (size) => {
      if (article) {
        // 1. 폰트 크기 변경
        article.style.fontSize = size + "rem";
        // 2. [핵심] 줄간격 강제 비율 설정 (글씨가 커져도 1.7배 비율로 넉넉하게 간격 유지!)
        article.style.lineHeight = "1.7"; 
      }
    };

    // 접속 시 즉시 적용
    updateStyle(currentSize);

    // 버튼 클릭 이벤트 (최대 1.8배, 최소 0.8배)
    if (btnInc && btnDec && article) {
      btnInc.addEventListener("click", () => {
        currentSize = Math.min(currentSize + 0.1, 1.8); 
        updateStyle(currentSize);
        localStorage.setItem("customFontSize", currentSize);
      });
      
      btnDec.addEventListener("click", () => {
        currentSize = Math.max(currentSize - 0.1, 0.8); 
        updateStyle(currentSize);
        localStorage.setItem("customFontSize", currentSize);
      });
    }
  })
`

FontSizeAdjust.css = `
  /* 우측 하단 플로팅 버튼 스타일 */
  .font-size-adjust-floating {
    position: fixed;
    bottom: 2.5rem;
    right: 2.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 999;
    background: var(--light);
    padding: 0.3rem;
    border-radius: 8px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
    border: 1px solid var(--lightgray);
    transition: all 0.3s ease;
  }

  /* 다크모드 대응 (엘리시움의 고급스러운 느낌) */
  [saved-theme="dark"] .font-size-adjust-floating {
    background: var(--dark);
    border: 1px solid var(--darkgray);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6);
  }

  /* 버튼 디자인 */
  .font-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--gray);
    font-weight: bold;
    font-size: 1rem;
    padding: 0.5rem;
    border-radius: 4px;
    transition: all 0.2s ease;
    width: 100%;
  }

  .font-btn:hover {
    color: var(--secondary);
    background: rgba(150, 150, 150, 0.1);
  }

  /* 버튼 사이 얇은 구분선 */
  .font-divider {
    width: 70%;
    height: 1px;
    background: var(--lightgray);
    margin: 2px 0;
  }
  
  [saved-theme="dark"] .font-divider {
    background: var(--darkgray);
  }

  /* 모바일 화면에서는 버튼 위치 살짝 조정 */
  @media all and (max-width: 800px) {
    .font-size-adjust-floating {
      bottom: 1.5rem;
      right: 1.5rem;
    }
  }
`

export default (() => FontSizeAdjust) satisfies QuartzComponentConstructor