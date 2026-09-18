import { QuartzComponent, QuartzComponentConstructor } from "./types"

const TableFormatting: QuartzComponent = () => null

TableFormatting.afterDOMLoaded = `
document.addEventListener("nav", () => {
  const undo = []
  for (const table of document.querySelectorAll("article .table-container > table")) {
    // Authored layouts and merged-cell infoboxes keep their original presentation.
    if (table.matches('[data-table-layout="compact"], .table-compact')) continue
    const rows = Array.from(table.rows)
    const cells = rows.flatMap(row => Array.from(row.cells))
    if (cells.some(cell => cell.colSpan > 1 || cell.rowSpan > 1)) continue
    const proseColumns = new Set()
    for (const row of rows) {
      Array.from(row.cells).forEach((cell, column) => {
        if (cell.tagName !== "TD") return
        const text = (cell.textContent || "").replace(/\\s+/g, " ").trim()
        const longText = text.length >= 36 && /[A-Za-z가-힣]/.test(text)
        if (longText || cell.querySelector("p, ul, ol")) proseColumns.add(column)
      })
    }
    if (!proseColumns.size) continue
    const hadTableClass = table.classList.contains("table-prose")
    table.classList.add("table-prose")
    const marked = []
    for (const row of rows) {
      Array.from(row.cells).forEach((cell, column) => {
        if (proseColumns.has(column) && !cell.classList.contains("prose-column")) {
          cell.classList.add("prose-column")
          marked.push(cell)
        }
      })
    }
    undo.push(() => {
      if (!hadTableClass) table.classList.remove("table-prose")
      marked.forEach(cell => cell.classList.remove("prose-column"))
    })
  }
  window.addCleanup(() => undo.forEach(restore => restore()))
})
`

export default (() => TableFormatting) satisfies QuartzComponentConstructor
