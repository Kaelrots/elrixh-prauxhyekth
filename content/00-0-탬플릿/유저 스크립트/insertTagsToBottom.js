module.exports = async (tp) => {
  const fm = tp.frontmatter;
  if (!fm) {
    new Notice("YAML frontmatter가 이 문서에 없습니다.");
    return;
  }

  const tagList = fm.tags || fm.태그;
  if (!tagList || tagList.length === 0) {
    new Notice("tags 또는 태그 필드가 없습니다.");
    return;
  }

  const tags = Array.isArray(tagList) ? tagList : [tagList];
  const tagLine = tags.map(t => `#${t}`).join(" ");

  const fileContent = await tp.file.read();
  const tagLineExists = fileContent.trim().endsWith(tagLine);

  if (!tagLineExists) {
    await tp.file.append('\n\n' + tagLine);
    new Notice("태그 줄이 본문 맨 아래에 추가되었습니다.");
  } else {
    new Notice("이미 동일한 태그 줄이 존재합니다.");
  }
};
