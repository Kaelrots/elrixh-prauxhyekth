'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { assertNoLinks } = require('./lib/config.cjs');
const { hashFile } = require('./content-transform.cjs');
const { parseManifest, snapshotTree, validateContent } = require('./content-validate.cjs');
const { assertOwnedLock } = require('./content-swap.cjs');
const { error } = require('./lib/io.cjs');
const { publicationReason } = require('./lib/publication.cjs');
const { progressCounter } = require('./lib/progress.cjs');
const { sourceSnapshot } = require('./source-freshness.cjs');
const mediaPattern = /\.(png|jpe?g|gif|webp|mp3|mp4)$/i;
const fail = (code, message) => { throw error(code, message, 7, 'WEB_PREPARE'); };
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const escaped = s => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
// Matches Quartz's current path slugs; anchors are kept separate from file paths.
const slug = s => s.replace(/\.md$/i, '').replace(/\s/g, '-').replace(/&/g, '-and-').replace(/%/g, '-percent').replace(/[?#]/g, '').replace(/_index$/, 'index');
function mapProse(text, change) {
  const lines = text.match(/[^\r\n]*(?:\r\n|\n|\r|$)/g).filter(Boolean);
  let result = '', prose = '', fence = null, yaml = false;
  const flush = () => {
    const protectedParts = [];
    const hold = value => { protectedParts.push(value); return `\u0000P${protectedParts.length - 1}\u0000`; };
    let value = prose.replace(/<(pre|code)\b[^>]*>[\s\S]*?<\/\1>/gi, hold);
    value = value.replace(/(`+)[^`\r\n]*(?:`(?!\1)[^`\r\n]*)*?\1/g, hold);
    value = change(value).replace(/\u0000P(\d+)\u0000/g, (_, i) => protectedParts[Number(i)]);
    result += value; prose = '';
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (i === 0 && /^\uFEFF?---\s*(?:\r?\n|$)/.test(line)) yaml = true;
    if (yaml) { result += line; if (i > 0 && /^(---|\.\.\.)\s*$/.test(line.trim())) yaml = false; continue; }
    const match = line.match(/^ {0,3}(`{3,}|~{3,})/);
    if (fence) { result += line; if (match && match[1][0] === fence[0] && match[1].length >= fence.length && line.slice(match[0].length).trim() === '') fence = null; continue; }
    if (match) { flush(); fence = match[1]; result += line; continue; }
    prose += line;
  }
  flush(); return result;
}
function createProcessor(rows, warnings) {
  const files = rows.map(x => x.destination), byBase = new Map(), media = new Map();
  for (const row of rows) {
    const name = path.posix.basename(row.destination), key = name.normalize('NFC').toLowerCase();
    const candidates = byBase.get(key) || []; candidates.push(row.destination); byBase.set(key, candidates);
    if (mediaPattern.test(name)) {
      const target = 'assets/media/' + name.replace(/\s+/g, '-');
      const normalized = target.normalize('NFC').toLowerCase(), previous = media.get(normalized);
      if (previous && previous.sha256 !== row.outputInfo.sha256) fail('MEDIA_COLLISION', `같은 미디어 이름의 내용이 다릅니다: ${previous.source}, ${row.destination}`);
      if (!previous) media.set(normalized, { source: row.destination, destination: target, sha256: row.outputInfo.sha256 });
    }
  }
  const mediaBySource = new Map(rows.filter(r => mediaPattern.test(r.destination)).map(r => {
    const key = ('assets/media/' + path.posix.basename(r.destination).replace(/\s+/g, '-')).normalize('NFC').toLowerCase();
    return [r.destination, media.get(key).destination];
  }));
  function resolve(raw, document, markdown = false) {
    let decoded;
    try { decoded = decodeURIComponent(raw.replace(/\\/g, '')).replace(/^\/?kael\//, '').replace(/^\/+/, ''); } catch { decoded = raw; }
    const variants = [decoded, decoded.replace(/\+/g, ' ')];
    if (markdown) for (const v of [...variants]) if (!v.endsWith('.md')) variants.push(v + '.md');
    for (const candidate of variants) {
      const local = path.posix.normalize(path.posix.join(path.posix.dirname(document), candidate));
      if (files.includes(local)) return local;
      if (files.includes(candidate)) return candidate;
    }
    // An explicit path is authoritative. If that exact path is not part of the
    // publishable file set (for example because the target is draft/private),
    // never retarget it to another same-named file elsewhere in the vault.
    // The caller will record it as a missing/excluded reference instead.
    const pathQualified = variants.some(candidate => candidate.includes('/'));
    if (pathQualified) return null;
    for (const candidate of variants) {
      const matches = byBase.get(path.posix.basename(candidate).normalize('NFC').toLowerCase()) || [];
      if (matches.length === 1) return matches[0];
      if (matches.length > 1) {
        // Identical media aliases are safe; documents or different bytes are not.
        if (matches.every(x => mediaBySource.get(x) && mediaBySource.get(x) === mediaBySource.get(matches[0]))) return matches[0];
        fail('AMBIGUOUS_LINK', `모호한 파일 참조: ${document} → ${raw}`);
      }
    }
    return null;
  }
  function mediaUrl(raw, document) {
    const target = resolve(raw, document);
    if (!target || !mediaBySource.has(target)) { warnings.push({ code: 'MISSING_MEDIA', document, reference: raw }); return null; }
    return '/' + mediaBySource.get(target);
  }
  const processMarkdown = (text, document) => mapProse(text, value => {
    value = value.replace(/!\[\[([^\]]+)\]\]/g, (whole, inner) => {
      const [ref, size] = inner.replace(/\\\|/g, '|').split('|');
      if (!mediaPattern.test(ref)) return whole;
      const url = mediaUrl(ref, document); if (!url) return whole;
      const image = /\.(png|jpe?g|gif|webp)$/i.test(ref);
      if (!image) return `[${size || path.posix.basename(ref)}](${encodeURI(url)})`;
      const dimensions = size?.match(/^(\d+)(?:x(\d+))?$/);
      return `<img src="${escaped(url)}" alt="${escaped(dimensions ? path.posix.basename(ref) : size || path.posix.basename(ref))}"${dimensions ? ` width="${dimensions[1]}"${dimensions[2] ? ` height="${dimensions[2]}"` : ''}` : ''}>`;
    });
    value = value.replace(/\b(src|href)="([^"]+)"/gi, (whole, attr, raw) => {
      if (/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(raw) || raw.startsWith('/assets/media/')) return whole;
      const decodedRaw = raw.replace(/&amp;/g, '&');
      if (mediaPattern.test(decodedRaw)) { const url = mediaUrl(decodedRaw, document); return url ? `${attr}="${escaped(url)}"` : whole; }
      if (attr.toLowerCase() === 'href' && /^\/?kael\//.test(decodedRaw)) {
        const [ref, anchor] = decodedRaw.split('#'), target = resolve(ref, document, true);
        if (!target) { warnings.push({ code: 'MISSING_DOCUMENT', document, reference: decodedRaw }); return whole; }
        return `href="/${escaped(slug(target))}${anchor ? '#' + escaped(anchor.replace(/\+/g, ' ').replace(/\s/g, '-')) : ''}"`;
      }
      return whole;
    });
    value = value.replace(/^(\s*#{1,6}\s+)(.*)$/gm, (_, prefix, heading) => prefix + heading.replace(/\*\*(.*?)\*\*/g, '$1'));
    return value.replace(/\*\*([^\r\n]*?)\*\*/g, '<font style="font-weight:bold">$1</font>');
  });
  return { processMarkdown, media: [...media.values()] };
}
async function buildQuartzStaging(c, installedManifest, options = {}) {
  assertOwnedLock(c, options.lock);
  const allRows = [...parseManifest(installedManifest, c).values()], warnings = [], excludedDocuments = [...(installedManifest.pipeline === 'quartz' ? installedManifest.publication?.excludedDocuments || [] : [])], rows = [];
  const vaultSnapshot = sourceSnapshot(c, installedManifest);
  const policyProgress = progressCounter('공개 여부 확인', allRows.length);
  for (const row of allRows) {
    let reason;
    if (row.destination.toLowerCase().startsWith('90-볼트 운영/00-템플릿/')) reason = 'template';
    else if (row.destination.toLowerCase().endsWith('.md')) {
      const source = path.join(c.contentPath, row.destination); assertNoLinks(source);
      const bytes = fs.readFileSync(source);
      if (sha(bytes) !== row.outputInfo.sha256) fail('CONTENT_CHANGED', `설치된 content가 바뀌었습니다: ${row.destination}`);
      try { reason = publicationReason(new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes), c); }
      catch (e) { e.message = `${row.destination}: ${e.message}`; throw e; }
    }
    if (reason) excludedDocuments.push({ path: row.destination, reason }); else rows.push(row);
    policyProgress();
  }
  const processor = createProcessor(rows, warnings);
  assertNoLinks(c.stagingPath);
  if (fs.existsSync(c.stagingPath)) fail('STAGING_EXISTS', 'Quartz staging이 이미 있습니다. 덮어쓰지 않습니다.');
  fs.mkdirSync(c.stagingPath);
  const copyProgress = progressCounter('게시용 파일 변환·복사', rows.length);
  for (const row of rows) {
    const source = path.join(c.contentPath, row.destination), dest = path.join(c.stagingPath, row.destination);
    assertNoLinks(source); assertNoLinks(dest); fs.mkdirSync(path.dirname(dest), { recursive: true });
    if (row.destination.toLowerCase().endsWith('.md')) {
      const bytes = fs.readFileSync(source);
      if (sha(bytes) !== row.outputInfo.sha256) fail('CONTENT_CHANGED', `설치된 content가 바뀌었습니다: ${row.destination}`);
      fs.writeFileSync(dest, processor.processMarkdown(new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes), row.destination), { flag: 'wx' });
    } else {
      fs.copyFileSync(source, dest, fs.constants.COPYFILE_EXCL);
      if (await hashFile(dest) !== row.outputInfo.sha256) fail('CONTENT_CHANGED', `미디어 내용이 바뀌었습니다: ${row.destination}`);
    }
    copyProgress();
  }
  const mediaProgress = progressCounter('미디어 준비', processor.media.length);
  for (const item of processor.media) {
    const dest = path.join(c.stagingPath, item.destination); assertNoLinks(dest);
    if (fs.existsSync(dest)) { if (await hashFile(dest) !== item.sha256) fail('MEDIA_COLLISION', `중앙 미디어 경로 충돌: ${item.destination}`); mediaProgress(); continue; }
    fs.mkdirSync(path.dirname(dest), { recursive: true }); fs.copyFileSync(path.join(c.contentPath, item.source), dest, fs.constants.COPYFILE_EXCL);
    if (await hashFile(dest) !== item.sha256) fail('CONTENT_CHANGED', `미디어 수집 중 파일이 바뀌었습니다: ${item.source}`);
    mediaProgress();
  }
  await validateContent(c, c.contentPath, installedManifest);
  const tree = await snapshotTree(c.stagingPath);
  const files = tree.entries.map(f => ({ source: f.path, destination: f.path, kind: 'file', status: f.path.toLowerCase().endsWith('.md') ? 'converted' : 'copied', outputInfo: { bytes: f.bytes, sha256: f.sha256 }, ...(f.bytes === 0 ? { emptyReason: 'source-empty' } : {}) }));
  const manifest = { schemaVersion: 1, runId: options.logger?.runId || crypto.randomUUID(), generatedAt: new Date().toISOString(), sourceHead: installedManifest.sourceHead, sourceRoot: c.contentPath, pipeline: 'quartz', upstreamRunId: installedManifest.runId, vaultSnapshot, publication: { version: 1, excludedDocuments }, files,
    summary: { sourceFiles: files.length, outputFiles: files.length, markdownFiles: files.filter(f => f.status === 'converted').length, excludedFiles: 0, excludedDirectories: 0, errors: 0 } };
  options.logger?.log('WEB_PREPARE', `게시 제외 ${excludedDocuments.length}개 (비공개·템플릿)`, { excludedDocuments });
  return { manifest, warnings, excludedDocuments, mediaFiles: processor.media.length };
}
function verifyPublicationOutput(output, excludedDocuments) {
  const indexFile = path.join(output, 'static/contentIndex.json'); assertNoLinks(indexFile);
  const index = fs.existsSync(indexFile) ? JSON.parse(fs.readFileSync(indexFile, 'utf8')) : {};
  for (const document of excludedDocuments) {
    const target = slug(document.path), html = path.join(output, target + '.html'); assertNoLinks(html);
    if (fs.existsSync(html) || Object.prototype.hasOwnProperty.call(index, target)) fail('PRIVATE_OUTPUT', `게시 제외 문서가 빌드 결과에 남아 있어 업로드를 막았습니다: ${document.path}`);
  }
  return { excludedDocumentsChecked: excludedDocuments.length };
}
module.exports = { mapProse, createProcessor, buildQuartzStaging, verifyPublicationOutput };
