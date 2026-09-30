import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { glob } from "./glob"

test("verified staging can ignore Git exclusions while retaining Quartz exclusions", async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "quartz-glob-"))
  const staging = path.join(root, "content.__staging")
  try {
    await fs.mkdir(path.join(root, ".git"))
    await fs.mkdir(path.join(staging, "templates"), { recursive: true })
    await fs.writeFile(path.join(root, ".gitignore"), "/content.__staging/\n")
    await fs.writeFile(path.join(staging, "index.md"), "# Home\n")
    await fs.writeFile(path.join(staging, "한글 그림.png"), "fixture")
    await fs.writeFile(path.join(staging, "templates/template.md"), "<% template %>")
    assert.deepEqual(await glob("**/*.*", staging, []), [])
    assert.deepEqual((await glob("**/*.*", staging, ["templates/**"], false)).sort(), [
      "index.md",
      "한글 그림.png",
    ])
    assert.deepEqual(await glob("**", staging, ["**/*.md"], false), ["한글 그림.png"])
  } finally {
    // Every entry is created by this test under its unique OS temporary directory.
    for (const file of [
      "content.__staging/templates/template.md",
      "content.__staging/index.md",
      "content.__staging/한글 그림.png",
      ".gitignore",
    ])
      await fs.unlink(path.join(root, file))
    for (const dir of ["content.__staging/templates", "content.__staging", ".git", ""])
      await fs.rmdir(path.join(root, dir))
  }
})
