const fs = require("fs");
const path = require("path");

const vaultPath = path.resolve(__dirname, "..");
const statsJson = path.join(vaultPath, "99-동기화 제외 파일", "commit_stats.json");
const resultPath = path.join(vaultPath, "99-동기화 제외 파일", "commit_count_table.md");

// 1. 누적 stats 불러오기
let stats = {};
if (fs.existsSync(statsJson)) {
  try { stats = JSON.parse(fs.readFileSync(statsJson, "utf8")); } catch {}
}

// 2. 상위 30개만 추출 (실제 파일 존재하고, 집계 제외 조건 만족 시)
function isExcluded(relPath) {
  if (relPath.replace(/\\/g, "/").startsWith("99-동기화 제외 파일/")) return true;
  if (relPath.replace(/\\/g, "/") === "00-0-수정기록/수정 기록 모음.md") return true;
  return false;
}

const entries = Object.entries(stats)
  .filter(([relPath]) => {
    const absPath = path.join(vaultPath, relPath);
    return fs.existsSync(absPath) && !isExcluded(relPath);
  })
  .sort((a, b) => b[1] - a[1])
  .slice(0, 30)
  .map(([relPath, count], i) => [
    i + 1,
    count,
    `[[${relPath.replace(/\.md$/, "")}]]`
  ]);

function makeTable(title, headers, rows, heading = "#") {
  const headerLine = `| ${headers.join(" | ")} |`;
  const sep = "| " + headers.map(() => "---").join(" | ") + " |";
  const lines = rows.map((r) => "| " + r.join(" | ") + " |");
  return `${heading} ${title}\n\n${headerLine}\n${sep}\n${lines.join("\n")}`;
}

const md2 = makeTable(
  "🪄 가장 많이 수정된 30개의 문서",
  ["순위", "총 수정 횟수", "문서 이름"],
  entries
);
const commitNote = "-  수정 횟수 기록은 누적 기준입니다.";

fs.writeFileSync(resultPath, md2 + "\n" + commitNote, "utf8");
console.log("✅ 커밋 기반 통계(2번 표) 생성 완료:", resultPath);
