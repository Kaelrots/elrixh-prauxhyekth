import type { ContentDetails } from "../../plugins/emitters/contentIndex"
import {
  SimulationNodeDatum,
  SimulationLinkDatum,
  Simulation,
  forceSimulation,
  forceManyBody,
  forceCenter,
  forceLink,
  forceCollide,
  forceRadial,
  zoomIdentity,
  select,
  drag,
  zoom,
} from "d3"
import { Text, Graphics, Application, Container, Circle } from "pixi.js"
import { Group as TweenGroup, Tween as Tweened } from "@tweenjs/tween.js"
import { removeAllChildren } from "./util"
import { FullSlug, SimpleSlug, resolveRelative, simplifySlug } from "../../util/path"
import { D3Config } from "../Graph"

type GraphicsInfo = {
  color: string
  gfx: Graphics
  alpha: number
  active: boolean
}

type NodeData = {
  id: SimpleSlug
  text: string
  tags: string[]
} & SimulationNodeDatum

type SimpleLinkData = {
  source: SimpleSlug
  target: SimpleSlug
}

type LinkData = {
  source: NodeData
  target: NodeData
} & SimulationLinkDatum<NodeData>

type LinkRenderData = GraphicsInfo & {
  simulationData: LinkData
}

type NodeRenderData = GraphicsInfo & {
  simulationData: NodeData
  label: Text
}

const localStorageKey = "graph-visited"
function getVisited(): Set<SimpleSlug> {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(localStorageKey) ?? "[]")
    return new Set(Array.isArray(stored) ? stored : [])
  } catch {
    return new Set()
  }
}

function addToVisited(slug: SimpleSlug) {
  const visited = getVisited()
  visited.add(slug)
  try {
    localStorage.setItem(localStorageKey, JSON.stringify([...visited]))
  } catch {
    // Graph navigation remains usable when browser storage is unavailable.
  }
}

type TweenNode = {
  update: (time: number) => void
  stop: () => void
}

async function renderGraph(graph: HTMLElement, fullSlug: FullSlug, signal: AbortSignal) {
  const slug = simplifySlug(fullSlug)
  const visited = getVisited()
  removeAllChildren(graph)

  let {
    drag: enableDrag,
    zoom: enableZoom,
    depth,
    scale,
    repelForce,
    centerForce,
    linkDistance,
    fontSize,
    opacityScale,
    removeTags,
    showTags,
    focusOnHover,
    enableRadial,
  } = JSON.parse(graph.dataset["cfg"]!) as D3Config

  const data: Map<SimpleSlug, ContentDetails> = new Map(
    Object.entries<ContentDetails>(await fetchData).map(([k, v]) => [
      simplifySlug(k as FullSlug),
      v,
    ]),
  )
  if (signal.aborted || !graph.isConnected || graph.offsetWidth === 0) return () => {}
  const links: SimpleLinkData[] = []
  const tags: SimpleSlug[] = []
  const validLinks = new Set(data.keys())

  const tweens = new Map<string, TweenNode>()
  for (const [source, details] of data.entries()) {
    const outgoing = details.links ?? []

    for (const dest of outgoing) {
      if (validLinks.has(dest)) {
        links.push({ source: source, target: dest })
      }
    }

    if (showTags) {
      const localTags = details.tags
        .filter((tag) => !removeTags.includes(tag))
        .map((tag) => simplifySlug(("tags/" + tag) as FullSlug))

      tags.push(...localTags.filter((tag) => !tags.includes(tag)))

      for (const tag of localTags) {
        links.push({ source: source, target: tag })
      }
    }
  }

  const neighbourhood = new Set<SimpleSlug>()
  const wl: (SimpleSlug | "__SENTINEL")[] = [slug, "__SENTINEL"]
  if (depth >= 0) {
    while (depth >= 0 && wl.length > 0) {
      // compute neighbours
      const cur = wl.shift()!
      if (cur === "__SENTINEL") {
        depth--
        wl.push("__SENTINEL")
      } else {
        neighbourhood.add(cur)
        const outgoing = links.filter((l) => l.source === cur)
        const incoming = links.filter((l) => l.target === cur)
        wl.push(...outgoing.map((l) => l.target), ...incoming.map((l) => l.source))
      }
    }
  } else {
    validLinks.forEach((id) => neighbourhood.add(id))
    if (showTags) tags.forEach((tag) => neighbourhood.add(tag))
  }

  const nodes = [...neighbourhood].map((url) => {
    const text = url.startsWith("tags/") ? "#" + url.substring(5) : (data.get(url)?.title ?? url)
    return {
      id: url,
      text,
      tags: data.get(url)?.tags ?? [],
    }
  })
  const graphData: { nodes: NodeData[]; links: LinkData[] } = {
    nodes,
    links: links
      .filter((l) => neighbourhood.has(l.source) && neighbourhood.has(l.target))
      .map((l) => ({
        source: nodes.find((n) => n.id === l.source)!,
        target: nodes.find((n) => n.id === l.target)!,
      })),
  }

  const width = graph.offsetWidth
  const height = Math.max(graph.offsetHeight, 250)

  // we virtualize the simulation and use pixi to actually render it
  const simulation: Simulation<NodeData, LinkData> = forceSimulation<NodeData>(graphData.nodes)
    .force("charge", forceManyBody().strength(-100 * repelForce))
    .force("center", forceCenter().strength(centerForce))
    .force("link", forceLink(graphData.links).distance(linkDistance))
    .force("collide", forceCollide<NodeData>((n) => nodeRadius(n)).iterations(3))

  const stopSimulation = () => simulation.stop()
  signal.addEventListener("abort", stopSimulation, { once: true })

  const radius = (Math.min(width, height) / 2) * 0.8
  if (enableRadial) simulation.force("radial", forceRadial(radius).strength(0.2))

  // precompute style prop strings as pixi doesn't support css variables
  const cssVars = [
    "--secondary",
    "--tertiary",
    "--gray",
    "--light",
    "--lightgray",
    "--dark",
    "--darkgray",
    "--bodyFont",
  ] as const
  const computedStyleMap = cssVars.reduce(
    (acc, key) => {
      acc[key] = getComputedStyle(document.documentElement).getPropertyValue(key)
      return acc
    },
    {} as Record<(typeof cssVars)[number], string>,
  )

  // calculate color
  const color = (d: NodeData) => {
    const isCurrent = d.id === slug
    if (isCurrent) {
      return computedStyleMap["--secondary"]
    } else if (visited.has(d.id) || d.id.startsWith("tags/")) {
      return computedStyleMap["--tertiary"]
    } else {
      return computedStyleMap["--gray"]
    }
  }

  function nodeRadius(d: NodeData) {
    const numLinks = graphData.links.filter(
      (l) => l.source.id === d.id || l.target.id === d.id,
    ).length
    return 2 + Math.sqrt(numLinks)
  }

  let hoveredNodeId: string | null = null
  let hoveredNeighbours: Set<string> = new Set()
  const linkRenderData: LinkRenderData[] = []
  const nodeRenderData: NodeRenderData[] = []
  function updateHoverInfo(newHoveredId: string | null) {
    hoveredNodeId = newHoveredId

    if (newHoveredId === null) {
      hoveredNeighbours = new Set()
      for (const n of nodeRenderData) {
        n.active = false
      }

      for (const l of linkRenderData) {
        l.active = false
      }
    } else {
      hoveredNeighbours = new Set()
      for (const l of linkRenderData) {
        const linkData = l.simulationData
        if (linkData.source.id === newHoveredId || linkData.target.id === newHoveredId) {
          hoveredNeighbours.add(linkData.source.id)
          hoveredNeighbours.add(linkData.target.id)
        }

        l.active = linkData.source.id === newHoveredId || linkData.target.id === newHoveredId
      }

      for (const n of nodeRenderData) {
        n.active = hoveredNeighbours.has(n.simulationData.id)
      }
    }
  }

  let dragStartTime = 0
  let dragging = false

  function renderLinks() {
    tweens.get("link")?.stop()
    const tweenGroup = new TweenGroup()

    for (const l of linkRenderData) {
      let alpha = 1

      // if we are hovering over a node, we want to highlight the immediate neighbours
      // with full alpha and the rest with default alpha
      if (hoveredNodeId) {
        alpha = l.active ? 1 : 0.2
      }

      l.color = l.active ? computedStyleMap["--gray"] : computedStyleMap["--lightgray"]
      tweenGroup.add(new Tweened<LinkRenderData>(l).to({ alpha }, 200))
    }

    tweenGroup.getAll().forEach((tw) => tw.start())
    tweens.set("link", {
      update: tweenGroup.update.bind(tweenGroup),
      stop() {
        tweenGroup.getAll().forEach((tw) => tw.stop())
      },
    })
  }

  function renderLabels() {
    tweens.get("label")?.stop()
    const tweenGroup = new TweenGroup()

    const defaultScale = 1 / scale
    const activeScale = defaultScale * 1.1
    for (const n of nodeRenderData) {
      const nodeId = n.simulationData.id

      if (hoveredNodeId === nodeId) {
        tweenGroup.add(
          new Tweened<Text>(n.label).to(
            {
              alpha: 1,
              scale: { x: activeScale, y: activeScale },
            },
            100,
          ),
        )
      } else {
        tweenGroup.add(
          new Tweened<Text>(n.label).to(
            {
              alpha: n.label.alpha,
              scale: { x: defaultScale, y: defaultScale },
            },
            100,
          ),
        )
      }
    }

    tweenGroup.getAll().forEach((tw) => tw.start())
    tweens.set("label", {
      update: tweenGroup.update.bind(tweenGroup),
      stop() {
        tweenGroup.getAll().forEach((tw) => tw.stop())
      },
    })
  }

  function renderNodes() {
    tweens.get("hover")?.stop()

    const tweenGroup = new TweenGroup()
    for (const n of nodeRenderData) {
      let alpha = 1

      // if we are hovering over a node, we want to highlight the immediate neighbours
      if (hoveredNodeId !== null && focusOnHover) {
        alpha = n.active ? 1 : 0.2
      }

      tweenGroup.add(new Tweened<Graphics>(n.gfx, tweenGroup).to({ alpha }, 200))
    }

    tweenGroup.getAll().forEach((tw) => tw.start())
    tweens.set("hover", {
      update: tweenGroup.update.bind(tweenGroup),
      stop() {
        tweenGroup.getAll().forEach((tw) => tw.stop())
      },
    })
  }

  function renderPixiFromD3() {
    renderNodes()
    renderLinks()
    renderLabels()
  }

  tweens.forEach((tween) => tween.stop())
  tweens.clear()

  const app = new Application()
  try {
    await app.init({
      width,
      height,
      antialias: true,
      autoStart: false,
      autoDensity: true,
      backgroundAlpha: 0,
      preference: "webgpu",
      resolution: window.devicePixelRatio,
      eventMode: "static",
    })
  } catch (error) {
    simulation.stop()
    signal.removeEventListener("abort", stopSimulation)
    if (app.renderer) app.destroy(true, { children: true })
    throw error
  }
  if (signal.aborted || !graph.isConnected || graph.offsetWidth === 0) {
    simulation.stop()
    signal.removeEventListener("abort", stopSimulation)
    app.destroy(true, { children: true })
    return () => {}
  }
  graph.appendChild(app.canvas)

  const stage = app.stage
  stage.interactive = false

  const labelsContainer = new Container<Text>({
    zIndex: 3,
    isRenderGroup: true,
  })
  const nodesContainer = new Container<Graphics>({
    zIndex: 2,
    isRenderGroup: true,
  })
  const linkContainer = new Container<Graphics>({
    zIndex: 1,
    isRenderGroup: true,
  })
  stage.addChild(nodesContainer, labelsContainer, linkContainer)

  for (const n of graphData.nodes) {
    const nodeId = n.id

    const label = new Text({
      interactive: false,
      eventMode: "none",
      text: n.text,
      alpha: 0,
      anchor: { x: 0.5, y: 1.2 },
      style: {
        fontSize: fontSize * 15,
        fill: computedStyleMap["--dark"],
        fontFamily: computedStyleMap["--bodyFont"],
      },
      resolution: window.devicePixelRatio * 4,
    })
    label.scale.set(1 / scale)

    let oldLabelOpacity = 0
    const isTagNode = nodeId.startsWith("tags/")
    const gfx = new Graphics({
      interactive: true,
      label: nodeId,
      eventMode: "static",
      hitArea: new Circle(0, 0, nodeRadius(n)),
      cursor: "pointer",
    })
      .circle(0, 0, nodeRadius(n))
      .fill({ color: isTagNode ? computedStyleMap["--light"] : color(n) })
      .on("pointerover", (e) => {
        updateHoverInfo(e.target.label)
        oldLabelOpacity = label.alpha
        if (!dragging) {
          renderPixiFromD3()
        }
      })
      .on("pointerleave", () => {
        updateHoverInfo(null)
        label.alpha = oldLabelOpacity
        if (!dragging) {
          renderPixiFromD3()
        }
      })

    if (isTagNode) {
      gfx.stroke({ width: 2, color: computedStyleMap["--tertiary"] })
    }

    nodesContainer.addChild(gfx)
    labelsContainer.addChild(label)

    const nodeRenderDatum: NodeRenderData = {
      simulationData: n,
      gfx,
      label,
      color: color(n),
      alpha: 1,
      active: false,
    }

    nodeRenderData.push(nodeRenderDatum)
  }

  for (const l of graphData.links) {
    const gfx = new Graphics({ interactive: false, eventMode: "none" })
    linkContainer.addChild(gfx)

    const linkRenderDatum: LinkRenderData = {
      simulationData: l,
      gfx,
      color: computedStyleMap["--lightgray"],
      alpha: 1,
      active: false,
    }

    linkRenderData.push(linkRenderDatum)
  }

  let currentTransform = zoomIdentity
  if (enableDrag) {
    select<HTMLCanvasElement, NodeData | undefined>(app.canvas).call(
      drag<HTMLCanvasElement, NodeData | undefined>()
        .container(() => app.canvas)
        .subject(() => graphData.nodes.find((n) => n.id === hoveredNodeId))
        .on("start", function dragstarted(event) {
          if (!event.active) simulation.alphaTarget(1).restart()
          event.subject.fx = event.subject.x
          event.subject.fy = event.subject.y
          event.subject.__initialDragPos = {
            x: event.subject.x,
            y: event.subject.y,
            fx: event.subject.fx,
            fy: event.subject.fy,
          }
          dragStartTime = Date.now()
          dragging = true
        })
        .on("drag", function dragged(event) {
          const initPos = event.subject.__initialDragPos
          event.subject.fx = initPos.x + (event.x - initPos.x) / currentTransform.k
          event.subject.fy = initPos.y + (event.y - initPos.y) / currentTransform.k
        })
        .on("end", function dragended(event) {
          if (!event.active) simulation.alphaTarget(0)
          event.subject.fx = null
          event.subject.fy = null
          dragging = false

          // if the time between mousedown and mouseup is short, we consider it a click
          if (Date.now() - dragStartTime < 500) {
            const node = graphData.nodes.find((n) => n.id === event.subject.id) as NodeData
            const targ = resolveRelative(fullSlug, node.id)
            window.spaNavigate(new URL(targ, window.location.toString()))
          }
        }),
    )
  } else {
    for (const node of nodeRenderData) {
      node.gfx.on("click", () => {
        const targ = resolveRelative(fullSlug, node.simulationData.id)
        window.spaNavigate(new URL(targ, window.location.toString()))
      })
    }
  }

  if (enableZoom) {
    select<HTMLCanvasElement, NodeData>(app.canvas).call(
      zoom<HTMLCanvasElement, NodeData>()
        .extent([
          [0, 0],
          [width, height],
        ])
        .scaleExtent([0.25, 4])
        .on("zoom", ({ transform }) => {
          currentTransform = transform
          stage.scale.set(transform.k, transform.k)
          stage.position.set(transform.x, transform.y)

          // zoom adjusts opacity of labels too
          const scale = transform.k * opacityScale
          let scaleOpacity = Math.max((scale - 1) / 3.75, 0)
          const activeNodes = nodeRenderData.filter((n) => n.active).flatMap((n) => n.label)

          for (const label of labelsContainer.children) {
            if (!activeNodes.includes(label)) {
              label.alpha = scaleOpacity
            }
          }
        }),
    )
  }

  let stopAnimation = false
  let animationFrame = 0
  function animate(time: number) {
    if (stopAnimation) return
    for (const n of nodeRenderData) {
      const { x, y } = n.simulationData
      if (!x || !y) continue
      n.gfx.position.set(x + width / 2, y + height / 2)
      if (n.label) {
        n.label.position.set(x + width / 2, y + height / 2)
      }
    }

    for (const l of linkRenderData) {
      const linkData = l.simulationData
      l.gfx.clear()
      l.gfx.moveTo(linkData.source.x! + width / 2, linkData.source.y! + height / 2)
      l.gfx
        .lineTo(linkData.target.x! + width / 2, linkData.target.y! + height / 2)
        .stroke({ alpha: l.alpha, width: 1, color: l.color })
    }

    tweens.forEach((t) => t.update(time))
    app.renderer.render(stage)
    animationFrame = requestAnimationFrame(animate)
  }

  animationFrame = requestAnimationFrame(animate)
  return () => {
    if (stopAnimation) return
    stopAnimation = true
    cancelAnimationFrame(animationFrame)
    simulation.stop()
    signal.removeEventListener("abort", stopSimulation)
    tweens.forEach((tween) => tween.stop())
    tweens.clear()
    app.destroy(true, { children: true })
  }
}

// A controller owns one canvas, including renders still awaiting Pixi initialization.
// This prevents hidden panels, rapid resize/theme changes, or SPA navigation from
// leaving stale canvases, force simulations, or animation loops behind.
function createGraphController(graph: HTMLElement, slug: FullSlug, isVisible: () => boolean) {
  let disposed = false
  let revision = 0
  let frame = 0
  let forceNextRender = false
  let dimensions = ""
  let cleanup: (() => void) | undefined
  let pending: AbortController | undefined

  function stop() {
    revision++
    pending?.abort()
    pending = undefined
    cleanup?.()
    cleanup = undefined
    dimensions = ""
  }

  async function update() {
    frame = 0
    const force = forceNextRender
    forceNextRender = false
    if (disposed) return
    if (
      !isVisible() ||
      !graph.isConnected ||
      graph.offsetWidth === 0 ||
      graph.getClientRects().length === 0
    ) {
      stop()
      return
    }
    const nextDimensions = `${graph.offsetWidth}:${graph.offsetHeight}:${window.devicePixelRatio}`
    if (!force && dimensions === nextDimensions) return
    stop()
    dimensions = nextDimensions
    const currentRevision = revision
    const abort = new AbortController()
    pending = abort
    try {
      const destroy = await renderGraph(graph, slug, abort.signal)
      if (disposed || abort.signal.aborted || currentRevision !== revision) {
        destroy()
      } else {
        cleanup = destroy
      }
    } catch (error) {
      if (!disposed && !abort.signal.aborted) console.warn("Unable to render Quartz graph", error)
    }
  }

  function refresh(force = false) {
    if (disposed) return
    forceNextRender ||= force
    if (!isVisible()) stop()
    if (!frame) frame = requestAnimationFrame(() => void update())
  }

  const observer = new ResizeObserver(() => refresh())
  observer.observe(graph)
  refresh()
  return {
    refresh,
    dispose() {
      disposed = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      stop()
    },
  }
}

document.addEventListener("nav", (e: CustomEventMap["nav"]) => {
  const slug = e.detail.url
  addToVisited(simplifySlug(slug))
  const controllers: ReturnType<typeof createGraphController>[] = []
  const globalControllers = new Map<HTMLElement, ReturnType<typeof createGraphController>>()
  const listeners: (() => void)[] = []
  let activeOverlay: HTMLElement | undefined
  let returnFocus: HTMLElement | null = null

  function hideGlobalGraph(restoreFocus = true) {
    if (!activeOverlay) return
    const overlay = activeOverlay
    activeOverlay = undefined
    overlay.classList.remove("active")
    overlay.closest(".sidebar")?.classList.remove("graph-open")
    document.documentElement.classList.remove("quartz-graph-open")
    globalControllers.get(overlay)?.refresh()
    if (restoreFocus && returnFocus?.isConnected) returnFocus.focus({ preventScroll: true })
    returnFocus = null
  }

  function showGlobalGraph(overlay: HTMLElement) {
    if (activeOverlay === overlay) return
    hideGlobalGraph(false)
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    activeOverlay = overlay
    overlay.classList.add("active")
    overlay.closest(".sidebar")?.classList.add("graph-open")
    document.documentElement.classList.add("quartz-graph-open")
    overlay.querySelector<HTMLButtonElement>(".global-graph-close")?.focus({ preventScroll: true })
    globalControllers.get(overlay)?.refresh(true)
  }

  for (const root of document.querySelectorAll<HTMLElement>(".graph")) {
    const button = root.querySelector<HTMLButtonElement>(".graph-header")
    const panel = root.querySelector<HTMLElement>(".graph-outer")
    const local = root.querySelector<HTMLElement>(".graph-container")
    if (button && panel && local) {
      let collapsed = false
      try {
        collapsed = localStorage.getItem("quartz-graph-collapsed") === "true"
      } catch {}
      const applyState = () => {
        button.setAttribute("aria-expanded", String(!collapsed))
        panel.hidden = collapsed
      }
      applyState()
      const controller = createGraphController(local, slug, () => !panel.hidden)
      controllers.push(controller)
      const toggle = () => {
        collapsed = !collapsed
        applyState()
        controller.refresh(true)
        try {
          localStorage.setItem("quartz-graph-collapsed", String(collapsed))
        } catch {}
      }
      button.addEventListener("click", toggle)
      listeners.push(() => button.removeEventListener("click", toggle))
    }

    const overlay = root.querySelector<HTMLElement>(".global-graph-outer")
    const global = overlay?.querySelector<HTMLElement>(".global-graph-container")
    if (!overlay || !global) continue
    const controller = createGraphController(global, slug, () =>
      overlay.classList.contains("active"),
    )
    controllers.push(controller)
    globalControllers.set(overlay, controller)

    const icon = root.querySelector<HTMLButtonElement>(".global-graph-icon")
    const close = overlay.querySelector<HTMLButtonElement>(".global-graph-close")
    const show = () => showGlobalGraph(overlay)
    const hide = () => hideGlobalGraph()
    const backdrop = (event: MouseEvent) => {
      if (event.target === overlay) hideGlobalGraph()
    }
    icon?.addEventListener("click", show)
    close?.addEventListener("click", hide)
    overlay.addEventListener("click", backdrop)
    listeners.push(() => {
      icon?.removeEventListener("click", show)
      close?.removeEventListener("click", hide)
      overlay.removeEventListener("click", backdrop)
    })
  }

  function keyboardHandler(event: KeyboardEvent) {
    if (event.key.toLowerCase() === "g" && (event.ctrlKey || event.metaKey) && !event.shiftKey) {
      const overlay = globalControllers.keys().next().value
      if (!overlay) return
      event.preventDefault()
      activeOverlay ? hideGlobalGraph() : showGlobalGraph(overlay)
      return
    }
    if (!activeOverlay) return
    if (event.key === "Escape") {
      event.preventDefault()
      hideGlobalGraph()
    } else if (event.key === "Tab") {
      const focusable = [
        ...activeOverlay.querySelectorAll<HTMLElement>(
          'button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ].filter(
        (element) => !element.hasAttribute("disabled") && element.getClientRects().length > 0,
      )
      const first = focusable[0]
      const last = focusable.at(-1)
      if (
        first &&
        last &&
        (!activeOverlay.contains(document.activeElement) ||
          (event.shiftKey && document.activeElement === first) ||
          (!event.shiftKey && document.activeElement === last))
      ) {
        event.preventDefault()
        const focusTarget = event.shiftKey ? last : first
        focusTarget.focus()
      }
    }
  }

  const themeChange = () => controllers.forEach((controller) => controller.refresh(true))
  const resize = () => controllers.forEach((controller) => controller.refresh())
  document.addEventListener("themechange", themeChange)
  document.addEventListener("keydown", keyboardHandler)
  window.addEventListener("resize", resize)
  window.addCleanup(() => {
    hideGlobalGraph(false)
    document.removeEventListener("themechange", themeChange)
    document.removeEventListener("keydown", keyboardHandler)
    window.removeEventListener("resize", resize)
    listeners.forEach((remove) => remove())
    controllers.forEach((controller) => controller.dispose())
  })
})
