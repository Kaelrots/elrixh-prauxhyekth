
const { execSync } = require("child_process");
const path = require("path");

const cwd = process.cwd().replace(/\\/g, "/");

console.log("현재 경로:", cwd);

let vaultPath = null;

if (cwd.includes("E:/구글 드라이브/세계관")) {
  vaultPath = "E:/구글 드라이브/세계관";
  console.log("[데스크탑 Vault 경로 감지됨]");
} else {
  console.error("[⚠️ 지원되지 않는 경로]:", cwd);
  process.exit(1);
}

try {
  const output = execSync(`git -C "${vaultPath}" pull origin main`, {
    encoding: "utf8",
    stdio: "inherit",
  });
  console.log("\n✅ GitHub pull 완료.");
} catch (e) {
  console.error("❌ Git pull 실패:", e.message);
}
