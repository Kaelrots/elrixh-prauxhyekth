import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import legacyStyle from "./styles/legacyToc.scss"
import modernStyle from "./styles/toc.scss"
import { classNames } from "../util/lang"

// @ts-ignore
import script from "./scripts/toc.inline"
import { i18n } from "../i18n"

interface Options {
  layout: "modern" | "legacy"
  variant: "sidebar" | "mobile"
}

const defaultOptions: Options = {
  layout: "modern",
  variant: "sidebar",
}

let numTocs = 0
export default ((opts?: Partial<Options>) => {
  const layout = opts?.layout ?? defaultOptions.layout
  const variant = opts?.variant ?? defaultOptions.variant
  const TableOfContents: QuartzComponent = ({
    fileData,
    displayClass,
    cfg,
  }: QuartzComponentProps) => {
    if (!fileData.toc?.length) {
      return null
    }

    const id = `toc-${numTocs++}`
    const title = i18n(cfg.locale).components.tableOfContents.title
    const entries = fileData.toc.map((tocEntry) => (
      <li key={tocEntry.slug} class={`depth-${tocEntry.depth}`}>
        <a href={`#${tocEntry.slug}`} data-for={tocEntry.slug}>
          {tocEntry.text}
        </a>
      </li>
    ))
    if (variant === "mobile") {
      const closeLabel = cfg.locale.startsWith("ko") ? "목차 닫기" : "Close table of contents"
      return (
        <div class={classNames(displayClass, "mobile-toc")}>
          <button
            type="button"
            class="mobile-toc-trigger"
            aria-haspopup="dialog"
            aria-controls={id}
            aria-expanded="false"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              aria-hidden="true"
            >
              <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
            </svg>
            <span>{title}</span>
          </button>
          <dialog id={id} class="mobile-toc-dialog" aria-labelledby={`${id}-title`}>
            <div class="mobile-toc-sheet">
              <div class="mobile-toc-heading">
                <h2 id={`${id}-title`}>{title}</h2>
                <button
                  type="button"
                  class="mobile-toc-close"
                  aria-label={closeLabel}
                  title={closeLabel}
                >
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    aria-hidden="true"
                  >
                    <path d="m6 6 12 12M18 6 6 18" />
                  </svg>
                </button>
              </div>
              <nav aria-label={title}>
                <ul class="mobile-toc-content">{entries}</ul>
              </nav>
            </div>
          </dialog>
        </div>
      )
    }
    return (
      <div class={classNames(displayClass, "toc")}>
        <button
          type="button"
          class={fileData.collapseToc ? "collapsed toc-header" : "toc-header"}
          aria-controls={id}
          aria-expanded={!fileData.collapseToc}
        >
          <h3>{title}</h3>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="fold"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
        <ul id={id} class="toc-content" hidden={Boolean(fileData.collapseToc)}>
          {entries}
        </ul>
      </div>
    )
  }

  TableOfContents.css = modernStyle
  TableOfContents.afterDOMLoaded = script

  const LegacyTableOfContents: QuartzComponent = ({ fileData, cfg }: QuartzComponentProps) => {
    if (!fileData.toc?.length) {
      return null
    }
    return (
      <details class="toc" open={!fileData.collapseToc}>
        <summary>
          <h3>{i18n(cfg.locale).components.tableOfContents.title}</h3>
        </summary>
        <ul>
          {fileData.toc.map((tocEntry) => (
            <li key={tocEntry.slug} class={`depth-${tocEntry.depth}`}>
              <a href={`#${tocEntry.slug}`} data-for={tocEntry.slug}>
                {tocEntry.text}
              </a>
            </li>
          ))}
        </ul>
      </details>
    )
  }
  LegacyTableOfContents.css = legacyStyle

  return layout === "modern" || variant === "mobile" ? TableOfContents : LegacyTableOfContents
}) satisfies QuartzComponentConstructor
