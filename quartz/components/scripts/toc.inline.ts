function setupToc() {
  for (const toc of document.querySelectorAll<HTMLElement>(".toc")) {
    const button = toc.querySelector<HTMLButtonElement>(".toc-header")
    const content = toc.querySelector<HTMLUListElement>(".toc-content")
    if (!button || !content) continue
    const toggle = () => {
      const expanded = button.getAttribute("aria-expanded") !== "true"
      button.setAttribute("aria-expanded", String(expanded))
      button.classList.toggle("collapsed", !expanded)
      content.hidden = !expanded
    }
    button.addEventListener("click", toggle)
    window.addCleanup(() => button.removeEventListener("click", toggle))
  }

  for (const toc of document.querySelectorAll<HTMLElement>(".mobile-toc")) {
    const trigger = toc.querySelector<HTMLButtonElement>(".mobile-toc-trigger")
    const dialog = toc.querySelector<HTMLDialogElement>(".mobile-toc-dialog")
    const closeButton = dialog?.querySelector<HTMLButtonElement>(".mobile-toc-close")
    if (!trigger || !dialog || !closeButton) continue
    // A body portal keeps the sheet independent of the fixed, filtered mobile toolbar.
    document.body.append(dialog)
    const desktop = window.matchMedia("(min-width: 1200px)")
    let previousFocus: HTMLElement | null = null

    const unlock = () => {
      document.documentElement.classList.remove("mobile-toc-open")
      trigger.setAttribute("aria-expanded", "false")
    }
    const close = (restoreFocus = true) => {
      if (!dialog.open) return
      dialog.close()
      unlock()
      if (restoreFocus && previousFocus?.isConnected) previousFocus.focus({ preventScroll: true })
    }
    const open = () => {
      if (
        desktop.matches ||
        dialog.open ||
        document.documentElement.matches(".content-gate-open, .content-warning-open") ||
        document.querySelector("dialog[open]")
      )
        return
      previousFocus =
        document.activeElement instanceof HTMLElement ? document.activeElement : trigger
      dialog.showModal()
      trigger.setAttribute("aria-expanded", "true")
      document.documentElement.classList.add("mobile-toc-open")
      const current = dialog.querySelector<HTMLElement>('a[aria-current="location"]')
      current?.scrollIntoView({ block: "nearest" })
      ;(current ?? closeButton).focus({ preventScroll: true })
    }
    const cancel = (event: Event) => {
      event.preventDefault()
      close()
    }
    const clickClose = () => close()
    const onClose = () => {
      if (!dialog.open) unlock()
    }
    const resize = () => {
      if (desktop.matches) close(false)
    }
    const click = (event: MouseEvent) => {
      if (event.target === dialog) {
        close()
        return
      }
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
      const link = (event.target as Element).closest<HTMLAnchorElement>("a[data-for]")
      const target = link && document.getElementById(link.dataset.for ?? "")
      if (!link || !target) return
      // Unlock first: scrolling while a modal dialog is open may be suppressed.
      event.preventDefault()
      event.stopPropagation()
      close(false)
      target.scrollIntoView({ block: "start" })
      history.pushState({}, "", link.href)
      const previousTabIndex = target.getAttribute("tabindex")
      target.setAttribute("tabindex", "-1")
      target.focus({ preventScroll: true })
      if (previousTabIndex === null) target.removeAttribute("tabindex")
      else target.setAttribute("tabindex", previousTabIndex)
    }
    trigger.addEventListener("click", open)
    closeButton.addEventListener("click", clickClose)
    dialog.addEventListener("cancel", cancel)
    dialog.addEventListener("close", onClose)
    dialog.addEventListener("click", click)
    desktop.addEventListener("change", resize)
    window.addCleanup(() => {
      trigger.removeEventListener("click", open)
      closeButton.removeEventListener("click", clickClose)
      dialog.removeEventListener("cancel", cancel)
      dialog.removeEventListener("close", onClose)
      dialog.removeEventListener("click", click)
      desktop.removeEventListener("change", resize)
      close(false)
      unlock()
      dialog.remove()
    })
  }

  const links = Array.from(
    document.querySelectorAll<HTMLAnchorElement>(
      ".toc a[data-for], .mobile-toc-dialog a[data-for]",
    ),
  )
  const tocIds = new Set(links.map((link) => link.dataset.for))
  const headers = Array.from(
    document.querySelectorAll<HTMLElement>(
      "article h1[id], article h2[id], article h3[id], article h4[id], article h5[id], article h6[id]",
    ),
  ).filter((header) => tocIds.has(header.id))
  let frame = 0
  let currentId: string | undefined
  const update = () => {
    frame = 0
    const offset =
      Math.max(24, parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0) +
      16
    let active = headers[0]
    for (const header of headers) {
      if (header.getBoundingClientRect().top > offset) break
      active = header
    }
    if (active?.id === currentId) return
    currentId = active?.id
    for (const link of links) {
      const isCurrent = link.dataset.for === currentId
      link.classList.toggle("in-view", isCurrent)
      if (isCurrent) link.setAttribute("aria-current", "location")
      else link.removeAttribute("aria-current")
    }
  }
  const schedule = () => {
    if (!frame) frame = requestAnimationFrame(update)
  }
  update()
  document.addEventListener("scroll", schedule, { passive: true })
  window.addEventListener("resize", schedule, { passive: true })
  window.addCleanup(() => {
    document.removeEventListener("scroll", schedule)
    window.removeEventListener("resize", schedule)
    cancelAnimationFrame(frame)
  })
}

document.addEventListener("nav", setupToc)
