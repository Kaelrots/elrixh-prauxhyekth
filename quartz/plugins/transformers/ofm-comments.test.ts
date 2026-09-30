import test from "node:test"
import assert from "node:assert/strict"
import { unified } from "unified"
import remarkParse from "remark-parse"
import remarkRehype from "remark-rehype"
import { VFile } from "vfile"
import { toHtml } from "hast-util-to-html"
import { ObsidianFlavoredMarkdown } from "./ofm"
import { BuildCtx } from "../../util/ctx"
import { Root } from "mdast"

async function render(value: string) {
  const plugin = ObsidianFlavoredMarkdown({ enableInHtmlEmbed: true })
  const ctx = { argv: {}, cfg: {}, allSlugs: [], allFiles: [] } as unknown as BuildCtx
  const file = new VFile({ value: plugin.textTransform?.(ctx, value) ?? value })
  file.data.slug = "index" as any
  const md = unified()
    .use(remarkParse)
    .use(plugin.markdownPlugins?.(ctx) ?? [])
  const ast = await md.run(md.parse(file), file)
  const html = unified()
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(plugin.htmlPlugins?.(ctx) ?? [])
  return toHtml(await html.run(ast as Root, file))
}

test("numbered document comments retain terminators across headings and tables", async () => {
  const result = await render(
    "<!-- numbered-begin:PREAMBLE -->\n\n## 헌법\n\n<!-- numbered-end:PREAMBLE -->\n\n<div><table><tr><td>내용</td></tr></table></div>",
  )
  assert.match(result, /<!-- numbered-begin:PREAMBLE -->/)
  assert.match(result, /<!-- numbered-end:PREAMBLE -->/)
  assert.match(result, /<h2>헌법<\/h2>/)
  assert.match(result, /<td>내용<\/td>/)
})

test("HTML embeds preserve nested comments while still converting visible arrows and links", async () => {
  const result = await render("<div><!-- hidden --> visible --> [[문서]]</div>")
  assert.match(result, /<!-- hidden -->/)
  assert.match(result, /visible <span>⇒<\/span>/)
  assert.match(decodeURI(result), /<a href="[^"]*문서"/)
})
