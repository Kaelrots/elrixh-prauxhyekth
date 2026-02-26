// sync_commit_stats.js
const { execSync } = require("child_process");
const fs   = require("fs");
const path = require("path");

const vaultPath = path.resolve(__dirname, "..");

// ── 경로 ------------------------------------------------------------------
const statsJson = path.join(vaultPath, "99-동기화 제외 파일", "commit_stats.json");
const prevJson  = path.join(vaultPath, "99-동기화 제외 파일", "commit_stats_prev.json");

// ── 1. 이전 누적 통계 로드 ---------------------------------------------------
let prevStats = {};
if (fs.existsSync(statsJson)) {
  try { prevStats = JSON.parse(fs.readFileSync(statsJson, "utf8")); }
  catch { console.log("[WARN] commit_stats.json 파싱 실패 → 초기화"); }
}

// ── 1-B. **백업 저장(Δ 계산용)** --------------------------------------------
fs.writeFileSync(prevJson, JSON.stringify(prevStats, null, 2), "utf8");

// ── 2. 새 스냅샷 커밋 -------------------------------------------------------
try {
  execSync("git add .",                       { cwd: vaultPath, stdio: "inherit" });
  execSync('git commit -m "auto: vault snapshot"', { cwd: vaultPath, stdio: "inherit" });
} catch (e) {
  if (!/nothing to commit/.test(String(e))) console.log("[WARN] 커밋 생성 실패:", e.message);
}

// ── 3. 커밋 해시 리스트 ------------------------------------------------------
const hashes = execSync('git log --pretty=format:%H --reverse', {
  cwd: vaultPath, encoding: "utf8"
}).split("\n").filter(Boolean);

// ── 4. 커밋별 변경 MD 파일 누적 --------------------------------------------
const stats = { ...prevStats };               // 새 누적 테이블
for (const hash of hashes) {
  const changed = execSync(
    `git diff-tree --no-commit-id --name-only -r ${hash}`,
    { cwd: vaultPath, encoding: "utf8" }
  ).split("\n")
   .map(s => s.trim())
   .filter(s => s.endsWith(".md") && s.length);

  for (const f of changed) stats[f] = (stats[f] || 0) + 1;
}

// ── 5. 누적 통계 저장 -------------------------------------------------------
fs.writeFileSync(statsJson, JSON.stringify(stats, null, 2), "utf8");

// ── 6. 표 생성 스크립트 실행 ------------------------------------------------
[
  "recent_files_table.js",
  "commit_count_table.js",
  "merge_tables.js",
  "changed_files_table.js"
].forEach(js => {
  try { execSync(`node ${js}`, { cwd: __dirname, stdio: "inherit" }); }
  catch (e) { console.log(`[WARN] ${js} 실패:`, e.message); }
});

// ── 7. 최종 커밋 ------------------------------------------------------------
try {
  execSync("git add .",                        { cwd: vaultPath, stdio: "inherit" });
  execSync('git commit -m "auto: stats/md up to date"', {
    cwd: vaultPath, stdio: "inherit"
  });
} catch (e) {
  if (!/nothing to commit/.test(String(e))) console.log("[WARN] 최종 커밋 실패:", e.message);
}

// ── 8. 히스토리 슬림화(기존 로직 유지) --------------------------------------
try {
  execSync('git checkout --orphan latest_only', { cwd: vaultPath, stdio: "inherit" });
  execSync('git add .',                         { cwd: vaultPath, stdio: "inherit" });
  execSync('git commit -m "keep latest only"',  { cwd: vaultPath, stdio: "inherit" });
  execSync('git branch -D main',                { cwd: vaultPath, stdio: "inherit" });
  execSync('git branch -m main',                { cwd: vaultPath, stdio: "inherit" });
  execSync('git gc --prune=now',                { cwd: vaultPath, stdio: "inherit" });
  console.log("[OK] 최신 커밋만 남기고 정리 완료.");
} catch (e) {
  console.log("[WARN] 커밋 슬림화 실패:", e.message);
}
