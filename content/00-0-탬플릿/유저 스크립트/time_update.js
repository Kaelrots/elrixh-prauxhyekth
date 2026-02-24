module.exports = async () => {
  const file = app.workspace.getActiveFile();
  const raw = await app.vault.read(file);

  const wrapper = document.createElement("div");
  wrapper.className = "only-local";  // 퍼블리시에서 숨길 클래스

  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const hh = String(now.getHours()).padStart(2, '0');
  const min = String(now.getMinutes()).padStart(2, '0');
  const formatted = `${yyyy}-${mm}-${dd} ${hh}:${min}`;

  let updated;

  if (/^최종수정일\s*:\s*.*/m.test(raw)) {
    // 기존 항목이 있을 경우 → 값만 치환
    updated = raw.replace(/^최종수정일\s*:\s*.*/m, `최종수정일: ${formatted}`);
  } else if (/^---\s*$/m.test(raw)) {
    // YAML 블록 맨 앞에 삽입
    updated = raw.replace(/^---\s*$/, `최종수정일: ${formatted}\n---`);
  } else {
    new Notice("⚠️ 최종수정일 항목이 없고 YAML 블록도 인식되지 않았습니다.");
    return;
  }

  await app.vault.modify(file, updated);
  new Notice(`✅ 최종수정일 갱신됨 → ${formatted}`);
};
