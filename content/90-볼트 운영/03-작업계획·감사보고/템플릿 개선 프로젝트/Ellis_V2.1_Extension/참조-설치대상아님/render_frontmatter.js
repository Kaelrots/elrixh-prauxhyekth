/**
 * 공통 MD를 읽어 신규 문서의 YAML 문자열을 반환한다. 파일 쓰기·이관·배포를 하지 않는다.
 * 기본 키/값/열거형/선택 여부는 MD만 정의한다. 이 JS에는 대체 스키마가 없다.
 * 사용: await tp.user.render_frontmatter(tp, { values: { ... }, extensions: { ... } })
 * 빈 새 노트에서 Templater로 삽입한다. 기존 노트나 템플릿 자체에서 실행하지 않는다.
 * sourcePath는 격리 시험용 재정의이며 운영 시 아래 경로 하나만 사용한다.
 */
module.exports = async function renderFrontmatter(tp, options = {}) {
  const defaultPath = '90-볼트 운영/00-템플릿/00-yaml 속성탭.md';
  const fail = message => { throw new Error(`[공통 프론트매터] ${message}`); };
  const isObject = value => value !== null && typeof value === 'object' &&
    !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const empty = value => value === null ||
    (typeof value === 'string' && value.trim() === '') || (Array.isArray(value) && value.length === 0);
  const unsafe = key => ['__proto__', 'constructor', 'prototype'].includes(key);

  if (!isObject(options)) fail('options는 객체여야 한다.');
  for (const key of Object.keys(options)) {
    if (!['values', 'extensions', 'sourcePath'].includes(key)) fail(`알 수 없는 옵션: ${key}`);
  }
  const values = options.values ?? {};
  const extensions = options.extensions ?? {};
  if (!isObject(values) || !isObject(extensions)) fail('values와 extensions는 객체여야 한다.');
  const sourcePath = options.sourcePath ?? defaultPath;
  if (typeof sourcePath !== 'string' || !sourcePath.endsWith('.md') ||
      sourcePath.startsWith('/') || sourcePath.includes('\\') ||
      sourcePath.split('/').some(part => part === '..' || part === '.')) {
    fail('원본은 볼트 안의 정확한 상대 MD 경로로 지정한다.');
  }
  if (!tp?.app?.vault || typeof tp.file?.include !== 'function' ||
      typeof tp.obsidian?.parseYaml !== 'function' || typeof tp.obsidian?.stringifyYaml !== 'function') {
    fail('Templater 및 Obsidian YAML API를 확인한다.');
  }
  const vault = tp.app.vault;
  const target = tp.config?.target_file;
  const template = tp.config?.template_file;
  if (!target || target.extension !== 'md' || typeof target.path !== 'string') fail('대상 MD가 없다.');
  if (target.path === sourcePath || target.path === template?.path ||
      target.path.startsWith('90-볼트 운영/00-템플릿/') || target.path.startsWith('.obsidian/')) {
    fail('템플릿·원본·설정 파일을 생성 대상으로 사용할 수 없다.');
  }
  // 디스크 저장 전의 입력도 보호한다. 다른 활성 노트를 대상으로 삼지는 않는다.
  const checkEditor = () => {
    const active = tp.app.workspace?.activeEditor;
    if (active?.file?.path !== target.path) return;
    if (typeof active.editor?.getValue !== 'function') fail('대상 편집기 내용을 확인할 수 없다.');
    if (active.editor.getValue().replace(/^\uFEFF/, '').trim() !== '') {
      fail('편집기에 내용이 있는 문서는 거부한다. 빈 새 노트에서 실행한다.');
    }
  };
  checkEditor();
  // 활성 파일 대신 명시된 target_file만 확인. 기존 값의 덮어쓰기를 원천 차단한다.
  if ((await vault.read(target)).replace(/^\uFEFF/, '').trim() !== '') {
    fail('비어 있지 않은 문서는 거부한다. 기존 문서는 별도 이관 절차로 처리한다.');
  }
  const source = vault.getAbstractFileByPath(sourcePath);
  if (!source || source.extension !== 'md') fail(`공통 원본을 찾을 수 없다: ${sourcePath}`);
  const raw = (await vault.read(source)).replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
  const isolate = text => {
    const match = text.match(/^---\n([\s\S]*?)\n---[ \t]*\n?$/);
    if (!match) fail('공통 원본에는 YAML 블록 하나만 있어야 한다.');
    return match[1];
  };
  const body = isolate(raw);
  const declarations = new Map();
  for (const line of body.split('\n')) {
    if (!line.trim() || line.trimStart().startsWith('#')) continue;
    const match = line.match(/^([^\s:#][^:]*):.*?\s+#\s+(@.*)$/);
    if (!match) fail('원본은 한 줄의 최상위 필드와 @ 주석으로 작성한다.');
    const key = match[1].trim();
    if (unsafe(key) || declarations.has(key)) fail(`금지되거나 중복된 키: ${key}`);
    const rules = {};
    for (const m of match[2].matchAll(/@(\w+(?:-\w+)*)(?:=([^\s]+))?/g)) rules[m[1]] = m[2] ?? true;
    if (!['string', 'list', 'boolean', 'number'].includes(rules.type)) fail(`자료형 선언 누락: ${key}`);
    declarations.set(key, rules);
  }
  const bannedMatch = body.match(/^# @forbid-new=(.+)$/m);
  const banned = new Set(bannedMatch ? bannedMatch[1].trim().split('|') : []);
  // include가 원본 안의 제목·날짜 식만 평가한다. 기본 양식은 캐시하거나 복제하지 않는다.
  const rendered = (await tp.file.include(source)).replace(/\r\n/g, '\n');
  const result = tp.obsidian.parseYaml(isolate(rendered));
  if (!isObject(result) || Object.keys(result).length !== declarations.size ||
      [...declarations.keys()].some(key => !own(result, key))) fail('원본 선언과 YAML 키가 불일치한다.');

  for (const [key, value] of Object.entries(values)) {
    if (unsafe(key) || banned.has(key)) fail(`신규 생성 금지 키: ${key}`);
    if (!declarations.has(key)) fail(`공통 키 미정의: ${key}. 유형 전용값은 extensions에 둔다.`);
    if (declarations.get(key).locked) fail(`생성 시 덮어쓸 수 없는 키: ${key}`);
    result[key] = value;
  }
  for (const [key, rule] of declarations) {
    if (rule['mirror-origin']) {
      // 호환값만 단방향 파생한다. 기원 자체나 정본상태를 추정하지 않는다.
      const origin = result['기원상태'];
      result[key] = origin === 'restored' ? true : origin === 'original' ? false : null;
    }
    const value = result[key];
    if (rule.required && empty(value)) fail(`필수값 누락: ${key}`);
    if (value === null) {
      if (!rule.nullable) fail(`null이 허용되지 않는 키: ${key}`);
    } else {
      const ok = rule.type === 'list' ? Array.isArray(value) && value.every(x => typeof x === 'string') :
        rule.type === 'number' ? typeof value === 'number' && Number.isFinite(value) : typeof value === rule.type;
      if (!ok) fail(`자료형 불일치: ${key}`);
      if (rule.enum && !rule.enum.split('|').includes(value)) fail(`허용값이 아닌 ${key}: ${value}`);
    }
    if (rule.optional && !own(values, key) && empty(value) && !(rule.restore && result['기원상태'] === 'restored')) {
      delete result[key];
    }
  }
  if (result['기원상태'] === 'original') {
    for (const [key, rule] of declarations) {
      if (rule.restore && own(result, key) && !empty(result[key])) fail('original과 복원 출처가 충돌한다.');
    }
  }
  for (const tag of result.tags ?? []) {
    if (!tag || /[\s#]/u.test(tag) || /^\d+$/.test(tag) || !/^[\p{L}\p{N}\p{M}\p{So}_/-]+$/u.test(tag)) {
      fail(`태그 형식을 확인한다: ${tag}`);
    }
  }
  if (target.path.startsWith('80-대체루트·비정사/01-신계 B루트/') &&
      !(result['연속성'] ?? []).includes('B루트')) fail('B루트 대상에는 연속성 B루트를 명시한다.');
  for (const [key, value] of Object.entries(extensions)) {
    if (unsafe(key) || banned.has(key) || declarations.has(key) || !key.trim()) fail(`확장 키 충돌 또는 금지: ${key}`);
    const ok = value === null || typeof value === 'string' || typeof value === 'boolean' ||
      (typeof value === 'number' && Number.isFinite(value)) ||
      (Array.isArray(value) && value.every(x => typeof x === 'string'));
    if (!ok) fail(`새 확장은 평면 속성만 허용한다: ${key}`);
    result[key] = value;
  }
  // YAML을 직렬화한 뒤 다시 읽어 값의 손실을 검사한다. 파일에는 아직 아무것도 쓰지 않는다.
  const yaml = tp.obsidian.stringifyYaml(result).trimEnd();
  const roundTrip = tp.obsidian.parseYaml(yaml);
  if (JSON.stringify(roundTrip) !== JSON.stringify(result)) fail('YAML 직렬화 후 값이 달라졌다.');
  if ((await vault.read(source)).replace(/^\uFEFF/, '').replace(/\r\n/g, '\n') !== raw) {
    fail('생성 도중 공통 원본이 변경되었다. 다시 실행한다.');
  }
  if ((await vault.read(target)).replace(/^\uFEFF/, '').trim() !== '') fail('생성 도중 대상에 내용이 생겼다.');
  checkEditor();
  return `---\n${yaml}\n---\n`;
};
