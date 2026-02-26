const fs = require("fs");
const path = require("path");
const vaultPath = path.resolve(__dirname, "..");

const recentPath  = path.join(vaultPath, "99-동기화 제외 파일", "recent_files_table.md");
const commitPath  = path.join(vaultPath, "99-동기화 제외 파일", "commit_count_table.md");
const changedPath = path.join(vaultPath, "99-동기화 제외 파일", "changed_files_table.md"); // ✅ 추가
const outPath     = path.join(vaultPath, "00-0-수정기록", "수정 기록 모음.md");

const now = new Date();
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
const nowStr = formatTime(now);

let recent10 = "", recent7 = "", commit = "", changed = "";

// 1) 소스 표 읽기
if (fs.existsSync(recentPath)) {
  const recent = fs.readFileSync(recentPath, "utf8");
  // <hr class="hr-thick-2"> 기준으로 [최근10 | 최근7] 분리
  if (recent.includes('<hr class="hr-thick-2">')) {
    [recent10, recent7] = recent.split('<hr class="hr-thick-2">').map(s => s.trim());
  } else {
    recent10 = recent.trim();
  }
}
if (fs.existsSync(commitPath)) {
  commit = fs.readFileSync(commitPath, "utf8").trim();
}
if (fs.existsSync(changedPath)) {
  changed = fs.readFileSync(changedPath, "utf8").trim();
}

// 2) 헤더 블록들
const updatedAtBlock = `<div style="text-align: center; font-size: 1.3em; color: #87DFD0 !important; font-weight: bold !important;">《문서 최종 업데이트 시각》<br>${nowStr}</div>`;

// 3) 최종 조립 (단 한 번만 선언)
const finalOutput = [
  "",                 // 맨 윗줄 줄바꿈
  updatedAtBlock,
  "",
  recent10,
  '<hr class="hr-thick-2">',
  "# 🔁 최근 수정된 파일 (이전 대비 증감)\n\n" + (changed || "_증감 내역 없음_"),
  '<hr class="hr-thick-2">',
  commit,
  '<hr class="hr-thick-2">',
  recent7,
  '<hr class="hr-thick-3">'
].join("\n\n");

// 4) 저장
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, finalOutput, "utf8");

console.log("✅ 최종 통합 보고서(수정 기록 모음.md) 생성 완료:", outPath);
