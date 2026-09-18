type ReadingTheme = "light" | "dark" | "system"

const readingRoot = document.documentElement
const readingColorScheme = window.matchMedia("(prefers-color-scheme: dark)")
const normalizeReadingSize = (value: string | null) => {
  const size = value?.trim() ? Number(value) : 1
  return Number.isFinite(size) ? Math.min(1.8, Math.max(0.8, Math.round(size * 10) / 10)) : 1
}
const normalizeReadingTheme = (value: string | null): ReadingTheme =>
  value === "light" || value === "dark" ? value : "system"
const saveReadingPreference = (key: string, value: string) => {
  try {
    localStorage.setItem(key, value)
  } catch {
    // The controls remain usable for this session when browser storage is unavailable.
  }
}

let readingSize = normalizeReadingSize(readingRoot.style.getPropertyValue("--reading-font-scale"))
let readingTheme = normalizeReadingTheme(readingRoot.getAttribute("theme-preference"))
let readingMode = readingRoot.getAttribute("reader-mode") === "on"

function applyReadingTheme() {
  const theme =
    readingTheme === "system" ? (readingColorScheme.matches ? "dark" : "light") : readingTheme
  const changed = readingRoot.getAttribute("saved-theme") !== theme
  readingRoot.setAttribute("saved-theme", theme)
  readingRoot.setAttribute("theme-preference", readingTheme)
  if (changed) document.dispatchEvent(new CustomEvent("themechange", { detail: { theme } }))
}

readingColorScheme.addEventListener("change", () => {
  if (readingTheme === "system") applyReadingTheme()
})

document.addEventListener("nav", () => {
  const trigger = document.querySelector<HTMLButtonElement>(".reading-settings-trigger")
  const dialog = document.querySelector<HTMLDialogElement>(".reading-settings-dialog")
  if (!trigger || !dialog) return

  // Keep the dialog outside the sticky sidebar and mobile app bar's backdrop filter.
  document.body.appendChild(dialog)
  const decrease = dialog.querySelector<HTMLButtonElement>('[data-font-step="-1"]')!
  const increase = dialog.querySelector<HTMLButtonElement>('[data-font-step="1"]')!
  const sizeOutput = dialog.querySelector<HTMLOutputElement>(".reading-font-size")!
  const reset = dialog.querySelector<HTMLButtonElement>(".reading-font-reset")!
  const closeButton = dialog.querySelector<HTMLButtonElement>(".reading-settings-close")!
  const themeInputs = dialog.querySelectorAll<HTMLInputElement>('input[name="reading-theme"]')
  const modeInput = dialog.querySelector<HTMLInputElement>(".reading-mode-input")!
  const listeners: Array<() => void> = []
  let disposed = false

  function listen(target: EventTarget, type: string, handler: EventListener) {
    target.addEventListener(type, handler)
    listeners.push(() => target.removeEventListener(type, handler))
  }

  function refreshControls() {
    sizeOutput.textContent = `${Math.round(readingSize * 100)}%`
    decrease.disabled = readingSize <= 0.8
    increase.disabled = readingSize >= 1.8
    for (const input of themeInputs) input.checked = input.value === readingTheme
    modeInput.checked = readingMode
  }

  function changeSize(nextSize: number) {
    readingSize = normalizeReadingSize(String(nextSize))
    readingRoot.style.setProperty("--reading-font-scale", String(readingSize))
    saveReadingPreference("customFontSize", String(readingSize))
    refreshControls()
  }

  const finishClose = () => {
    if (dialog.open) return
    readingRoot.classList.remove("reading-settings-open")
    trigger.setAttribute("aria-expanded", "false")
    if (!disposed && trigger.isConnected) trigger.focus({ preventScroll: true })
  }

  const closeSettings = () => {
    if (dialog.open) dialog.close()
    finishClose()
  }

  listen(trigger, "click", () => {
    if (
      dialog.open ||
      readingRoot.classList.contains("content-gate-open") ||
      readingRoot.classList.contains("content-warning-open") ||
      document.querySelector("dialog:modal")
    )
      return
    refreshControls()
    dialog.showModal()
    readingRoot.classList.add("reading-settings-open")
    trigger.setAttribute("aria-expanded", "true")
    closeButton.focus({ preventScroll: true })
  })
  listen(closeButton, "click", closeSettings)
  listen(dialog, "close", finishClose)
  listen(dialog, "cancel", (event) => {
    event.preventDefault()
    closeSettings()
  })
  listen(dialog, "click", (event) => {
    if (event.target !== dialog) return
    const { clientX, clientY } = event as MouseEvent
    const bounds = dialog.getBoundingClientRect()
    if (
      clientX < bounds.left ||
      clientX > bounds.right ||
      clientY < bounds.top ||
      clientY > bounds.bottom
    ) {
      closeSettings()
    }
  })
  listen(decrease, "click", () => changeSize(readingSize - 0.1))
  listen(increase, "click", () => changeSize(readingSize + 0.1))
  listen(reset, "click", () => changeSize(1))
  for (const input of themeInputs) {
    listen(input, "change", () => {
      if (!input.checked) return
      readingTheme = normalizeReadingTheme(input.value)
      saveReadingPreference("theme", readingTheme)
      applyReadingTheme()
      refreshControls()
    })
  }
  listen(modeInput, "change", () => {
    readingMode = modeInput.checked
    const mode = readingMode ? "on" : "off"
    readingRoot.setAttribute("reader-mode", mode)
    saveReadingPreference("reader-mode", mode)
    document.dispatchEvent(new CustomEvent("readermodechange", { detail: { mode } }))
  })
  refreshControls()

  window.addCleanup(() => {
    disposed = true
    closeSettings()
    for (const cleanup of listeners) cleanup()
    dialog.remove()
  })
})
