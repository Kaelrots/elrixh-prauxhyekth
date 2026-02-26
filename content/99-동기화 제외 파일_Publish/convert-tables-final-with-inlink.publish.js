const fs = require('fs');
const path = require('path');

const srcRoot = path.resolve(process.argv[2]);
const publishRoot = srcRoot + "_Publish";

if (publishRoot.startsWith(srcRoot + path.sep)) {
  console.error('❌ 퍼블리시 폴더가 원본 폴더 내부에 위치할 수 없습니다.');
  process.exit(1);
}

console.log("⚙️ 원본 경로:", srcRoot);
console.log("🟢 퍼블리시 경로:", publishRoot);

function ensureDirSync(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

// ⬇⬇⬇ 여기 바로 아래에 추가 ⬇⬇⬇
function copyDirRecursive(src, dst) {
  if (!fs.existsSync(src)) return;
  ensureDirSync(dst);
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name);
    const d = path.join(dst, e.name);
    if (e.isDirectory()) copyDirRecursive(s, d);
    else fs.copyFileSync(s, d);
  }
}


// 제외할 상위 폴더명
const EXCLUDE_DIRS = ['99-동기화 제외 파일', '99-이미지 파일 모음', '.git', '.obsidian'];

const OBSIDIAN_ALLOW = {
  files: ['appearance.json', 'app.json'],          // 필요 없으면 비워도 됨
  snippetsPattern: /^pub-.*\.css$/i,               // 퍼블리시용 스니펫 접두사(예: pub-*.css)
  snippetsExtra: ['통합 로컬 스니펫.css'],          // 로컬 스니펫 복사
  copyPrismTheme: true,                            // Prism 테마까지 복사하려면 true
  prismThemeDir: ['.obsidian','themes','Prism'],     // 필요 시 경로
  copyCorePluginsJson: true,        // 코어 플러그인 설정 복사
  corePluginsExclude: [],            // ['sync'] 같이 제외하고 싶으면 여기에 id 추가
  copyCommunityPlugins: true,                      // 커뮤니티 플러그인 화이트리스트 복사
  allowedCommunityPlugins: ['obsidian-style-settings'] // Style Settings만 허용
};

function isExcluded(filePath) {
  const relativePath = path.relative(srcRoot, filePath);
  return EXCLUDE_DIRS.some(exclude => relativePath.split(path.sep).includes(exclude));
}

function removeDataviewButtonBlocks(content) {
  return content.replace(/```dataviewjs[\s\S]*?```/g, '');
}

function exposeYamlBlock(content) {
  if (content.startsWith('---')) {
    const endIdx = content.indexOf('\n---', 3);
    if (endIdx !== -1) {
      const yamlBlock = content.slice(0, endIdx + 4);
      const rest = content.slice(endIdx + 4);
      const yamlInner = yamlBlock.replace(/^---\s*\n?/, '').replace(/\n?---\s*$/, '');
      return "```yaml\n" + yamlInner.trim() + "\n```\n" + rest.trimStart();
    }
  }
  return content;
}

function preserveFootnoteDefinitions(content) {
  const lines = content.split('\n');
  return lines.map(line => {
    if (/^\[\^[0-9a-zA-Z_-]+\]: /.test(line)) return line;
    return line;
  }).join('\n');
}

function splitMdTableRow(row) {
  let result = [];
  let curr = '';
  let inLink = false;
  for (let i = 0; i < row.length; i++) {
    if (row.slice(i, i + 2) === '[[') {
      inLink = true;
      curr += '[[';
      i++;
      continue;
    }
    if (inLink && row.slice(i, i + 2) === ']]') {
      inLink = false;
      curr += ']]';
      i++;
      continue;
    }
    if (row[i] === '|' && !inLink) {
      result.push(curr.trim());
      curr = '';
    } else {
      curr += row[i];
    }
  }
  result.push(curr.trim());
  if (result[0] === '') result = result.slice(1);
  if (result[result.length - 1] === '') result = result.slice(0, -1);
  return result;
}

function parseRow(row) {
  return splitMdTableRow(row);
}

function normalize(text) {
  if (typeof text !== 'string') return '';
  return text
    .replace(/\[\[([\s\S]+?)\]\]/g, (_, content) => {
      let [rawPath, label] = content.includes("|") ? content.split("|") : [content, content];
      const cleanedPath = rawPath.trim()
        .replace(/\\/g, "/")
        .replace(/\.md$/i, "")
        .replace(/ /g, "+");
      const fullPath = cleanedPath.startsWith('/') ? '/kael' + cleanedPath : '/kael/' + cleanedPath;
      return `<a href="${fullPath}">${label.trim()}</a>`;
    })
    .replace(/\n/g, "<br>");
}

function parseMarkdownTable(md) {
  let lines = md.trim().split('\n').filter(Boolean);
  if (lines.length < 2) return md;

  let [headerLine, alignLine, ...bodyLines] = lines;

  let rawHeaders = parseRow(headerLine);
  let headers = [], headerSkips = [];
  for (let i = 0; i < rawHeaders.length; i++) {
    if (rawHeaders[i] === '<') {
      let prev = headers[headers.length - 1];
      if (prev) prev.colspan++;
      headerSkips[i] = true;
    } else {
      headers.push({ text: rawHeaders[i], colspan: 1 });
      headerSkips[i] = false;
    }
  }

  let bodyArr = bodyLines.map(parseRow);
  let nRow = bodyArr.length;
  let nCol = rawHeaders.length;
  let skip = Array.from({ length: nRow }, () => Array(nCol).fill(false));

  let html = '<table>\n  <thead>\n    <tr>';
  let thCol = 0;
  for (let i = 0; i < rawHeaders.length; i++) {
    if (headerSkips[i]) continue;
    let th = headers[thCol++];
    let colspan = th.colspan > 1 ? ` colspan="${th.colspan}"` : '';
    html += `\n      <th${colspan}>${normalize(th.text)}</th>`;
  }
  html += '\n    </tr>\n  </thead>\n  <tbody>';

  for (let r = 0; r < nRow; r++) {
    let trContent = '';
    for (let c = 0; c < nCol; c++) {
      if (skip[r][c]) continue;
      let cell = bodyArr[r][c];
      if (cell === '<' || cell === '^') continue;
      let colspan = 1, rowspan = 1;
      for (let cc = c + 1; cc < nCol && bodyArr[r][cc] === '<'; cc++) {
        colspan++;
        skip[r][cc] = true;
      }
      for (let rr = r + 1; rr < nRow && bodyArr[rr][c] === '^'; rr++) {
        rowspan++;
        skip[rr][c] = true;
      }
      let attr = '';
      if (colspan > 1) attr += ` colspan="${colspan}"`;
      if (rowspan > 1) attr += ` rowspan="${rowspan}"`;
      trContent += `\n      <td${attr}>${normalize(cell)}</td>`;
    }
    if (trContent.trim()) {
      html += '\n    <tr>' + trContent + '\n    </tr>';
    }
  }

  html += '\n  </tbody>\n</table>\n';
  return html;
}

// 표를 가로 스크롤 가능하게 래핑 + "열 수"로 표 최소폭(min-width) 주입
// 표를 가로 스크롤 가능하게만 래핑 (min-width 강제 주입 제거)
function wrapTablesWithScrollX(html) {
  return html.replace(/<table\b[\s\S]*?<\/table>/gi, (tbl) => {
    // 스타일 주입 없이, 표 그대로 감싸기만 한다.
    return `<div class="scroll-x nowrap">${tbl}</div>`;
  });
}

function convertMarkdownTables(content) {
  const tableRegex = /(^|\n)[ \t]*((?:\|.*\|\n)+)[ \t]*\|[ \-:\|]+\|\n((?:[ \t]*\|.*\|\n?)+)/g;
  return content.replace(tableRegex, (match) => {
    return '\n' + parseMarkdownTable(match.trim()) + '\n';
  });
}

function processDirectory(srcDir, destDir) {
  if (path.resolve(srcDir) === path.resolve(publishRoot) ||
      path.resolve(srcDir).startsWith(path.resolve(publishRoot) + path.sep)) {
    return;
  }

  ensureDirSync(destDir);
  const entries = fs.readdirSync(srcDir, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(srcDir, entry.name);
    const destPath = path.join(destDir, entry.name);

    if (isExcluded(srcPath)) continue;

    if (entry.isDirectory()) {
      if (entry.name === ".git" || entry.name === '.obsidian') continue;
      processDirectory(srcPath, destPath);
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      const content = fs.readFileSync(srcPath, 'utf8');
      const yamlExposed = exposeYamlBlock(content);
      const converted = convertMarkdownTables(yamlExposed);
      const wrapped   = wrapTablesWithScrollX(converted);
      const withoutButton = removeDataviewButtonBlocks(wrapped);
      const finalContent = preserveFootnoteDefinitions(withoutButton);
      fs.writeFileSync(destPath, finalContent, 'utf8');
      console.log("✅ 변환&복사:", destPath);
    } else if (entry.isFile()) {
      if (entry.name.endsWith('.canvas')) continue;
      fs.copyFileSync(srcPath, destPath);
      console.log("📁 일반파일 복사:", destPath);
    }
  }
}

function copyObsidianWhitelist() {
  const srcOb = path.join(srcRoot, '.obsidian');
  if (!fs.existsSync(srcOb)) return;

  const dstOb = path.join(publishRoot, '.obsidian');
  ensureDirSync(dstOb);

  // 3-1) 허용 파일 복사
  for (const f of OBSIDIAN_ALLOW.files) {
    const s = path.join(srcOb, f);
    if (fs.existsSync(s)) {
      fs.copyFileSync(s, path.join(dstOb, f));
      console.log('🟢 .obsidian 파일 복사:', f);
    }
  }

  // 3-2) 스니펫 화이트리스트 (패턴 + 추가 목록)
  {
    const srcSnip = path.join(srcOb, 'snippets');
    const dstSnip = path.join(dstOb, 'snippets');
    if (fs.existsSync(srcSnip)) {
      ensureDirSync(dstSnip);
      const extras = (OBSIDIAN_ALLOW.snippetsExtra || []).map(s => s.toLowerCase());
      for (const name of fs.readdirSync(srcSnip)) {
        const okByPattern = OBSIDIAN_ALLOW.snippetsPattern.test(name);
        const okByExtra   = extras.includes(name.toLowerCase());
        if (okByPattern || okByExtra) {
          fs.copyFileSync(path.join(srcSnip, name), path.join(dstSnip, name));
          console.log('🟢 snippet 복사:', name);
        }
      }
    }
  }

  // 3-x) core-plugins.json (코어 플러그인 on/off 상태 복사)
  if (OBSIDIAN_ALLOW.copyCorePluginsJson) {
    const srcCore = path.join(srcOb, 'core-plugins.json');
    const dstCore = path.join(dstOb, 'core-plugins.json');
    if (fs.existsSync(srcCore)) {
      try {
        const raw = fs.readFileSync(srcCore, 'utf8');
        let list = JSON.parse(raw);
        if (Array.isArray(list) && OBSIDIAN_ALLOW.corePluginsExclude.length) {
          list = list.filter(id => !OBSIDIAN_ALLOW.corePluginsExclude.includes(id));
          fs.writeFileSync(dstCore, JSON.stringify(list, null, 2), 'utf8');
          console.log('🟢 core-plugins.json 복사(필터링 적용):', list.length, '개');
        } else {
          fs.copyFileSync(srcCore, dstCore);
          console.log('🟢 core-plugins.json 복사');
        }
      } catch (e) {
        console.warn('⚠ core-plugins.json 처리 실패:', e?.message || e);
        try { fs.copyFileSync(srcCore, dstCore); } catch {}
      }
    }
  }

  // 3-y) 커뮤니티 플러그인 화이트리스트 복사
  if (OBSIDIAN_ALLOW.copyCommunityPlugins) {
    const srcPlugins = path.join(srcOb, 'plugins');
    const dstPlugins = path.join(dstOb, 'plugins');
    const allow = new Set(OBSIDIAN_ALLOW.allowedCommunityPlugins || []);
    if (fs.existsSync(srcPlugins) && allow.size > 0) {
      ensureDirSync(dstPlugins);
      for (const id of allow) {
        const s = path.join(srcPlugins, id);
        const d = path.join(dstPlugins, id);
        copyDirRecursive(s, d); // 재귀 복사 유틸
        console.log('🟢 plugin 복사:', id);
      }
      // community-plugins.json 생성(허용 목록만)
      try {
        fs.writeFileSync(
          path.join(dstOb, 'community-plugins.json'),
          JSON.stringify([...allow], null, 2),
          'utf8'
        );
        console.log('🟢 community-plugins.json 작성');
      } catch {}
    }
  }

  // 3-3) (선택) Prism 테마
  if (OBSIDIAN_ALLOW.copyPrismTheme) {
    const srcTheme = path.join(srcRoot, ...OBSIDIAN_ALLOW.prismThemeDir);
    const dstTheme = path.join(publishRoot, ...OBSIDIAN_ALLOW.prismThemeDir);
    copyDirRecursive(srcTheme, dstTheme);
    console.log('🟢 Prism 테마 복사 완료');
  }

  // 3-4) 안전장치: 허용 외 플러그인/파일 제거
  try {
    const dstPlugins = path.join(dstOb, 'plugins');
    const allow = new Set(OBSIDIAN_ALLOW.allowedCommunityPlugins || []);
    if (fs.existsSync(dstPlugins)) {
      for (const e of fs.readdirSync(dstPlugins, { withFileTypes: true })) {
        if (e.isDirectory() && !allow.has(e.name)) {
          fs.rmSync(path.join(dstPlugins, e.name), { recursive: true, force: true });
          console.log('🧹 제거된 plugin:', e.name);
        }
      }
      // 허용 목록이 비어 있으면 plugins 폴더 자체 삭제
      if (allow.size === 0) fs.rmSync(dstPlugins, { recursive: true, force: true });
    }
  } catch {}
  // workspace.json은 계속 제거
  for (const bad of ['workspace.json']) {
    try { fs.rmSync(path.join(dstOb, bad), { force: true }); } catch {}
  }

}

if (!fs.existsSync(srcRoot)) {
  console.error('❌ 원본 경로가 존재하지 않습니다:', srcRoot);
  process.exit(1);
}

processDirectory(srcRoot, publishRoot);
copyObsidianWhitelist();
console.log("🎉 퍼블리싱 폴더 변환 완료.");
