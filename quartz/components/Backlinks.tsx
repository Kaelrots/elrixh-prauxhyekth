import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import style from "./styles/backlinks.scss"
import { resolveRelative, simplifySlug } from "../util/path"
import { i18n } from "../i18n"
import { classNames } from "../util/lang"
import OverflowListFactory from "./OverflowList"
import { concatenateResources } from "../util/resources"

interface BacklinksOptions {
  hideWhenEmpty: boolean
}

const defaultOptions: BacklinksOptions = {
  hideWhenEmpty: true,
}

let backlinkPanelCount = 0

export default ((opts?: Partial<BacklinksOptions>) => {
  const options: BacklinksOptions = { ...defaultOptions, ...opts }
  const { OverflowList, overflowListAfterDOMLoaded } = OverflowListFactory()

  const Backlinks: QuartzComponent = ({
    fileData,
    allFiles,
    displayClass,
    cfg,
  }: QuartzComponentProps) => {
    const slug = simplifySlug(fileData.slug!)
    const backlinkFiles = allFiles.filter((file) => file.links?.includes(slug))
    if (options.hideWhenEmpty && backlinkFiles.length == 0) {
      return null
    }
    const panelId = `backlinks-panel-${backlinkPanelCount++}`
    return (
      <div class={classNames(displayClass, "backlinks")}>
        <button type="button" class="backlinks-header" aria-expanded="true" aria-controls={panelId}>
          <h3>{i18n(cfg.locale).components.backlinks.title}</h3>
          <svg
            class="fold"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div class="backlinks-content" id={panelId}>
          <OverflowList>
            {backlinkFiles.length > 0 ? (
              backlinkFiles.map((f) => (
                <li>
                  <a href={resolveRelative(fileData.slug!, f.slug!)} class="internal">
                    {f.frontmatter?.title}
                  </a>
                </li>
              ))
            ) : (
              <li>{i18n(cfg.locale).components.backlinks.noBacklinksFound}</li>
            )}
          </OverflowList>
        </div>
      </div>
    )
  }

  Backlinks.css = style
  Backlinks.afterDOMLoaded = concatenateResources(
    overflowListAfterDOMLoaded,
    `
document.addEventListener("nav", () => {
  for (const button of document.querySelectorAll(".backlinks-header")) {
    const content = document.getElementById(button.getAttribute("aria-controls"))
    if (!content) continue
    let collapsed = false
    try { collapsed = localStorage.getItem("quartz-backlinks-collapsed") === "true" } catch {}
    const update = () => {
      button.setAttribute("aria-expanded", String(!collapsed))
      content.hidden = collapsed
    }
    const toggle = () => {
      collapsed = !collapsed
      update()
      try { localStorage.setItem("quartz-backlinks-collapsed", String(collapsed)) } catch {}
    }
    update()
    button.addEventListener("click", toggle)
    window.addCleanup(() => button.removeEventListener("click", toggle))
  }
})
`,
  )

  return Backlinks
}) satisfies QuartzComponentConstructor
