module.exports = async (tp) => {
  const metaedit = app.plugins.plugins["metaedit"];
  if (!metaedit) {
    console.log("❌ MetaEdit 플러그인 불러오기 실패");
    return;
  }

  const now = window.moment().format("YYYY-MM-DD HH:mm");

  // 파일 캐시: tp.file 바로 사용
  const fileCache = app.metadataCache.getFileCache(tp.file);
  const frontmatter = fileCache?.frontmatter;
  let 최초작성일 = frontmatter?.최초작성일;

  if (!최초작성일) {
    await metaedit.api.update("최초작성일", now);
    console.log(`✅ 최초작성일 새로 기록: ${now}`);
  } else {
    console.log(`ℹ️ 최초작성일 이미 있음: ${최초작성일}`);
  }

  await metaedit.api.update("최종수정일", now);
  console.log(`✅ 최종수정일 갱신됨: ${now}`);

  return `🗂️ 최초작성일: ${최초작성일 || now} / 최종수정일: ${now}`;
};
