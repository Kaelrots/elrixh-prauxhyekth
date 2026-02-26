const fs = require("fs");
const path = require("path");

const vaultPath = path.resolve(__dirname, "..");
const resultPath = path.join(vaultPath, "99-동기화 제외 파일", "recent_files_table.md");
const IGNORE_DIRS = ["$RECYCLE.BIN", "System Volume Information", "99-이미지 파일 모음", "99-동기화 제외 파일"];
const now = new Date();

function getAllMarkdownFiles(dir) {
  let results = [];
  let list;
  try { list = fs.readdirSync(dir); } catch { return results; }
  list.forEach((file) => {
    if (IGNORE_DIRS.includes(file)) return;
    const fullPath = path.join(dir, file);
    let stat;
    try { stat = fs.statSync(fullPath); } catch { return; }
    if (stat.isDirectory()) {
      results = results.concat(getAllMarkdownFiles(fullPath));
    } else if (file.endsWith(".md")) {
      results.push({
        fullPath,
        relPath: path.relative(vaultPath, fullPath).replace(/\\/g, "/"),
        mtime: stat.mtime,
        modTimeMs: stat.mtimeMs,
      });
    }
  });
  return results;
}

function formatTime(date) {
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "numeric",
    minute: "numeric",
    hour12: true,
  });
}
function makeTable(title, headers, rows, heading = "#") {
  const headerLine = `| ${headers.join(" | ")} |`;
  const sep = "| " + headers.map(() => "---").join(" | ") + " |";
  const lines = rows.map((r) => "| " + r.join(" | ") + " |");
  return `${heading} ${title}\n\n${headerLine}\n${sep}\n${lines.join("\n")}`;
}

const allFiles = getAllMarkdownFiles(vaultPath);
// 제외할 특정 파일 경로 (슬래시로 통일)
const EXCLUDED_FILES = ["00-0-수정기록/수정 기록 모음.md"];

// ...

const filteredFiles = allFiles.filter(f => 
  !EXCLUDED_FILES.includes(f.relPath)
);
const recent10 = filteredFiles.slice().sort((a, b) => b.modTimeMs - a.modTimeMs).slice(0, 10);
const weekAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
const recent7Days = filteredFiles.filter((f) => f.modTimeMs >= weekAgo).sort((a, b) => b.modTimeMs - a.modTimeMs).slice(0, 100);

const md1 = makeTable(
  "📌 가장 최근 수정된 10개의 문서",
  ["순서", "수정된 시각", "문서 이름"],
  recent10.map((f, i) => [
    i + 1,
    formatTime(f.mtime),
    `[[${f.relPath.replace(/\.md$/, "")}]]`,
  ])
);

const md3 = makeTable(
  "🕒 최근 30일 이내로 수정된 문서 (최대 100개)",
  ["순서", "수정된 시각", "문서 이름"],
  recent7Days.map((f, i) => [
    i + 1,
    formatTime(f.mtime),
    `[[${f.relPath.replace(/\.md$/, "")}]]`,
  ]),
  "#"
);

fs.writeFileSync(resultPath, md1 + "\n\n<hr class=\"hr-thick-2\">\n\n" + md3, "utf8");
console.log("✅ mtime 기반 최근 파일 표(1,3번 표) 생성 완료:", resultPath);
