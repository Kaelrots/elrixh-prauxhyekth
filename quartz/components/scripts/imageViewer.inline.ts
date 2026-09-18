type ImagePoint = { x: number; y: number }

let detachImageViewer = () => {}

function setupImageViewer() {
  detachImageViewer()
  const dialog = document.querySelector<HTMLDialogElement>("#quartz-image-viewer")
  const viewport = dialog?.querySelector<HTMLElement>(".image-viewer-viewport")
  const image = dialog?.querySelector<HTMLImageElement>(".image-viewer-image")
  const title = dialog?.querySelector<HTMLElement>(".image-viewer-title")
  const original = dialog?.querySelector<HTMLAnchorElement>(".image-viewer-original")
  const output = dialog?.querySelector<HTMLOutputElement>(".image-viewer-scale")
  const error = dialog?.querySelector<HTMLElement>(".image-viewer-error")
  const zoomIn = dialog?.querySelector<HTMLButtonElement>('[data-image-action="in"]')
  const zoomOut = dialog?.querySelector<HTMLButtonElement>('[data-image-action="out"]')
  if (
    !dialog ||
    !viewport ||
    !image ||
    !title ||
    !original ||
    !output ||
    !error ||
    !zoomIn ||
    !zoomOut
  )
    return

  let scale = 1
  let fitScale = 1
  let maxScale = 8
  let width = 0
  let height = 0
  let offset = { x: 0, y: 0 }
  let opener: HTMLElement | null = null
  let active = true
  const pointers = new Map<number, ImagePoint>()
  const disposers: (() => void)[] = []
  const controller = new AbortController()
  const listenerOptions = { signal: controller.signal }

  function paint() {
    if (!image || !viewport || !output || !zoomIn || !zoomOut) return
    const maxX = Math.max(0, (width * scale - viewport.clientWidth) / 2)
    const maxY = Math.max(0, (height * scale - viewport.clientHeight) / 2)
    offset.x = Math.max(-maxX, Math.min(maxX, offset.x))
    offset.y = Math.max(-maxY, Math.min(maxY, offset.y))
    image.style.transform = `translate(-50%, -50%) translate(${offset.x}px, ${offset.y}px) scale(${scale})`
    output.value = `${Math.round(scale * 100)}%`
    zoomIn.disabled = scale >= maxScale - 0.0001
    zoomOut.disabled = scale <= fitScale + 0.0001
  }

  function fit() {
    if (!viewport || !image || !dialog?.open) return
    width = image.naturalWidth
    height = image.naturalHeight
    if (!width || !height || !viewport.clientWidth || !viewport.clientHeight) return
    image.style.width = `${width}px`
    image.style.height = `${height}px`
    fitScale = Math.min(1, viewport.clientWidth / width, viewport.clientHeight / height)
    maxScale = Math.max(1, fitScale * 8)
    scale = fitScale
    offset = { x: 0, y: 0 }
    image.hidden = false
    error!.hidden = true
    paint()
  }

  function zoom(next: number, from: ImagePoint = { x: 0, y: 0 }, to = from) {
    if (!width || !height) return
    const bounded = Math.max(fitScale, Math.min(maxScale, next))
    const ratio = bounded / scale
    offset = { x: to.x - (from.x - offset.x) * ratio, y: to.y - (from.y - offset.y) * ratio }
    scale = bounded
    paint()
  }

  function clearPointers() {
    for (const id of pointers.keys()) {
      if (viewport?.hasPointerCapture(id)) viewport.releasePointerCapture(id)
    }
    pointers.clear()
    viewport?.classList.remove("is-dragging")
  }

  function unlock() {
    document.documentElement.classList.remove("image-viewer-open")
    clearPointers()
  }

  function close() {
    if (!dialog?.open) return
    dialog.close()
    unlock()
    if (opener?.isConnected) opener.focus({ preventScroll: true })
  }

  function open(source: HTMLImageElement) {
    if (!dialog || !image || !title || !original || !error || dialog.open) return
    if (
      document.documentElement.matches(".content-gate-open, .content-warning-open") ||
      document.querySelector("dialog[open]")
    )
      return
    opener = source
    width = height = 0
    offset = { x: 0, y: 0 }
    image.hidden = true
    error.hidden = true
    image.alt = source.alt
    title.textContent = source.alt || "이미지"
    original.href = source.currentSrc || source.src
    dialog.showModal()
    document.documentElement.classList.add("image-viewer-open")
    image.src = source.currentSrc || source.src
    if (image.complete && image.naturalWidth) fit()
  }

  image.addEventListener("load", fit, listenerOptions)
  image.addEventListener(
    "error",
    () => {
      image.hidden = true
      error.hidden = false
    },
    listenerOptions,
  )
  dialog.addEventListener("close", unlock, listenerOptions)
  dialog.addEventListener(
    "cancel",
    (event) => {
      event.preventDefault()
      close()
    },
    listenerOptions,
  )
  dialog.addEventListener(
    "click",
    (event) => {
      const action = (event.target as Element).closest<HTMLButtonElement>("[data-image-action]")
        ?.dataset.imageAction
      if (action === "close") close()
      else if (action === "fit") fit()
      else if (action === "in") zoom(scale * 1.5)
      else if (action === "out") zoom(scale / 1.5)
      else if (event.target === dialog) {
        const rect = dialog.getBoundingClientRect()
        if (
          event.clientX < rect.left ||
          event.clientX > rect.right ||
          event.clientY < rect.top ||
          event.clientY > rect.bottom
        )
          close()
      }
    },
    listenerOptions,
  )
  dialog.addEventListener(
    "keydown",
    (event) => {
      if (event.ctrlKey || event.metaKey || event.altKey) return
      if (event.key === "+" || event.key === "=") zoom(scale * 1.5)
      else if (event.key === "-") zoom(scale / 1.5)
      else if (event.key === "0") fit()
      else if (event.key === "ArrowLeft") offset.x += 50
      else if (event.key === "ArrowRight") offset.x -= 50
      else if (event.key === "ArrowUp") offset.y += 50
      else if (event.key === "ArrowDown") offset.y -= 50
      else return
      event.preventDefault()
      paint()
    },
    listenerOptions,
  )

  const localPoint = (event: { clientX: number; clientY: number }): ImagePoint => {
    const rect = viewport.getBoundingClientRect()
    return {
      x: event.clientX - rect.left - rect.width / 2,
      y: event.clientY - rect.top - rect.height / 2,
    }
  }
  const center = (a: ImagePoint, b: ImagePoint) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 })
  const distance = (a: ImagePoint, b: ImagePoint) => Math.hypot(a.x - b.x, a.y - b.y)

  viewport.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault()
      zoom(
        scale * Math.exp(-Math.max(-100, Math.min(100, event.deltaY)) * 0.005),
        localPoint(event),
      )
    },
    { ...listenerOptions, passive: false },
  )
  viewport.addEventListener(
    "pointerdown",
    (event) => {
      if (event.button !== 0 || !width || pointers.size >= 2) return
      event.preventDefault()
      viewport.focus({ preventScroll: true })
      pointers.set(event.pointerId, localPoint(event))
      viewport.setPointerCapture(event.pointerId)
      viewport.classList.add("is-dragging")
    },
    listenerOptions,
  )
  viewport.addEventListener(
    "pointermove",
    (event) => {
      const previous = pointers.get(event.pointerId)
      if (!previous) return
      const before = [...pointers.values()]
      const next = localPoint(event)
      pointers.set(event.pointerId, next)
      if (pointers.size === 2) {
        const after = [...pointers.values()]
        const oldDistance = distance(before[0], before[1])
        if (oldDistance > 0)
          zoom(
            (scale * distance(after[0], after[1])) / oldDistance,
            center(before[0], before[1]),
            center(after[0], after[1]),
          )
      } else {
        offset.x += next.x - previous.x
        offset.y += next.y - previous.y
        paint()
      }
    },
    listenerOptions,
  )
  const finishPointer = (event: PointerEvent) => {
    pointers.delete(event.pointerId)
    if (viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId)
    if (!pointers.size) viewport.classList.remove("is-dragging")
  }
  viewport.addEventListener("pointerup", finishPointer, listenerOptions)
  viewport.addEventListener("pointercancel", finishPointer, listenerOptions)
  viewport.addEventListener("lostpointercapture", finishPointer, listenerOptions)

  // Re-fit after orientation changes; the source image's intrinsic ratio is always retained.
  const resizeObserver = new ResizeObserver(() => {
    if (dialog.open) fit()
  })
  resizeObserver.observe(viewport)

  function enhance(source: HTMLImageElement) {
    if (!active || !source.isConnected || source.classList.contains("image-viewer-trigger")) return
    if (
      source.closest(
        'button, nav, [role="button"], [role="presentation"], [aria-hidden="true"], .callout-icon, .icon, .logo, .no-lightbox, [data-no-lightbox]',
      )
    )
      return
    if (source.alt.split(/\s+/).includes("callbg")) return
    const sourceUrl = source.currentSrc || source.src
    if (!sourceUrl) return
    const bounds = source.getBoundingClientRect()
    if (
      Math.min(source.naturalWidth, source.naturalHeight) < 96 ||
      Math.max(source.naturalWidth, source.naturalHeight) < 240
    )
      return
    // Images inside a collapsed callout have zero bounds until the reader opens it.
    if (bounds.width > 0 && bounds.height > 0 && bounds.width <= 96 && bounds.height <= 96) return
    const anchor = source.closest("a")
    if (anchor && anchor.href !== sourceUrl && anchor.href !== source.src) return
    const attributes = ["role", "tabindex", "aria-label", "aria-haspopup", "aria-controls"]
    const previous = attributes.map((attribute) => source.getAttribute(attribute))
    source.classList.add("image-viewer-trigger")
    source.setAttribute("role", "button")
    source.setAttribute("tabindex", "0")
    source.setAttribute("aria-label", `${source.alt || "이미지"} 확대해서 보기`)
    source.setAttribute("aria-haspopup", "dialog")
    source.setAttribute("aria-controls", dialog!.id)
    source.addEventListener(
      "click",
      (event) => {
        if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
          return
        event.preventDefault()
        event.stopPropagation()
        open(source)
      },
      listenerOptions,
    )
    source.addEventListener(
      "keydown",
      (event) => {
        if (event.key !== "Enter" && event.key !== " ") return
        event.preventDefault()
        event.stopPropagation()
        open(source)
      },
      listenerOptions,
    )
    disposers.push(() => {
      source.classList.remove("image-viewer-trigger")
      attributes.forEach((attribute, index) => {
        if (previous[index] === null) source.removeAttribute(attribute)
        else source.setAttribute(attribute, previous[index]!)
      })
    })
  }

  for (const source of document.querySelectorAll<HTMLImageElement>("article img")) {
    if (source.complete) enhance(source)
    else source.addEventListener("load", () => enhance(source), { ...listenerOptions, once: true })
  }

  detachImageViewer = () => {
    if (!active) return
    active = false
    // SPA navigation replaces the source article; avoid restoring focus into the old page.
    opener = null
    close()
    unlock()
    controller.abort()
    resizeObserver.disconnect()
    for (const dispose of disposers) dispose()
    image.removeAttribute("src")
  }
  window.addCleanup(detachImageViewer)
}

document.addEventListener("nav", setupImageViewer)
