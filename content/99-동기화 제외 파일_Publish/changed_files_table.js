// changed_files_table.js
const fs   = require("fs");
const path = require("path");

const vaultPath   = path.resolve(__dirname, "..");
const statsFile   = path.join(vaultPath, "99-동기화 제외 파일", "commit_stats.json");
const prevFile    = path.join(vaultPath, "99-동기화 제외 파일", "commit_stats_prev.json");
const deltaFile   = path.join(vaultPath, "99-동기화 제외 파일", "commit_delta.json");
const tableTarget = path.join(vaultPath, "99-동기화 제외 파일", "changed_files_table.md");

// 1. 이전·현재 통계 로드
const prevStats = fs.existsSync(prevFile)  ? JSON.parse(fs.readFileSync(prevFile,  "utf8")) : {};
const stats     = fs.existsSync(statsFile) ? JSON.parse(fs.readFileSync(statsFile, "utf8")) : {};

// 2. 증감 계산
const delta = {};
for (const f of Object.keys(stats)) {
  const diff = (stats[f] || 0) - (prevStats[f] || 0);
  if (diff !== 0) delta[f] = diff;
}
fs.writeFileSync(deltaFile, JSON.stringify(delta, null, 2), "utf8"); // (선택) 추적용 저장


// 2-1. 변동 없음이면 기존 MD 유지(덮어쓰지 않음)
const deltaCount = Object.keys(delta).length;
if (deltaCount === 0) {
  console.log("[SKIP] no changes; keep previous changed_files_table.md");
  // 첫 실행 등으로 파일이 아예 없으면 최소한의 안내만 남겨둠
  if (!fs.existsSync(tableTarget)) {
    const placeholder = `| 순위 | 증감 | 총 수정 횟수 | 문서명 |
| :-: | :-: | :-: | --- |
| - | 0 | - | (변동 없음) |

-  증감 횟수 기록은 최신-(최신-1 저장) 기준입니다. 변동이 없다면, 이전 기록을 유지합니다.`;
    fs.writeFileSync(tableTarget, placeholder, "utf8");
  }
  process.exit(0);
}

// 3. Markdown 표 생성 (증감 절대값 큰 순)
const EXCLUDED_DIR_PREFIX = "99-동기화 제외 파일/";
const EXCLUDED_FILES = new Set(["00-0-수정기록/수정 기록 모음.md"]);

const rowsArr = Object.entries(delta)
  // 다른 테이블과 동일한 제외 규칙
  .filter(([file]) => {
    const p = file.replace(/\\/g, "/");
    return !(p.startsWith(EXCLUDED_DIR_PREFIX) || EXCLUDED_FILES.has(p));
  })
  .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
  .map(([file, diff], i) => {
    const p = file.replace(/\\/g, "/");
    return `| ${i+1} | ${diff > 0 ? "+"+diff : diff} | ${stats[file]} | [[${p}]] |`;
  });

// (선택) 제외만 생겨서 비면, 이전 표 유지
if (rowsArr.length === 0) {
  console.log("[SKIP] only excluded files changed; keep previous changed_files_table.md");
  process.exit(0);
}
const rows = rowsArr.join("\n");

const md = `| 순위 | 증감 | 총 수정 횟수 | 문서명 |
| :-: | :-: | :-: | --- |
${rows}
`;

const tableNote = "-  증감 횟수 기록은 최신-(최신-1 저장) 기준입니다. 변동이 없다면, 이전 기록을 유지합니다.";

// fs.writeFileSync(tableTarget, md, "utf8"); //

fs.writeFileSync(tableTarget, md + "\n" + tableNote, "utf8");

console.log(`[OK] changed_files_table.md (${Object.keys(delta).length}건)`);
