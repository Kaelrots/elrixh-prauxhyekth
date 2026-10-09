import { appendFile, lstat, mkdir, open, readFile, rename, rm } from 'node:fs/promises';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { parse } from 'parse5';

const marker = '<!-- ELP-LEGACY-TRANSITION:1 -->';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const escape = text => text.replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
const fail = message => { throw new Error(message); };
async function regular(file) {
  const absolute = path.resolve(file), parts = absolute.split(path.sep), root = path.parse(absolute).root;
  let cursor = root;
  for (const part of parts.slice(1)) {
    cursor = path.join(cursor, part);
    const s = await lstat(cursor);
    if (s.isSymbolicLink() || (cursor === absolute ? !s.isFile() : !s.isDirectory())) fail(`Not a regular path: ${cursor}`);
  }
  const s = await lstat(absolute);
  if (s.size > 64 * 1024 * 1024) fail('HTML/configuration file exceeds the 64 MiB limit.');
  return readFile(absolute);
}
export async function readConfiguration(filename) {
  const c = JSON.parse(await regular(filename));
  if (c.schemaVersion !== 1 || typeof c.enabled !== 'boolean' || c.targetRepository !== 'Kaelrots/elrixh-prauxhyekth-site'
    || c.oldBaseUrl !== 'https://kaelrots.github.io/elrixh-prauxhyekth/' || c.targetBaseUrl !== 'https://kaelrots.github.io/elrixh-prauxhyekth-site/'
    || c.mapFile !== 'config/elp-legacy-mappings.json' || c.expectedMappings !== 377) fail('Unexpected transition configuration.');
  if (c.enabled && (!/^[0-9a-f]{40}$/.test(c.approvedTargetCommit ?? '') || !/^[A-Za-z0-9-]{8,80}$/.test(c.approvedBuildId ?? ''))) fail('Enable only with an explicitly approved target commit and build ID.');
  return c;
}
function checked(raw, base) {
  if (typeof raw !== 'string' || raw.trim() !== raw || /[\\\u0000-\u0020\u007f]/.test(raw) || /%(?:2f|5c|00)/i.test(raw)) fail('Unsafe migration URL.');
  let decoded = raw;
  for (let i = 0; i < 4; i++) { const next = decodeURIComponent(decoded); if (next === decoded) break; decoded = next; }
  if (decoded.split('/').some(p => p === '.' || p === '..') || /[\\\u0000-\u001f\u007f]/.test(decoded)) fail('Unsafe decoded path.');
  const u = new URL(raw);
  if (u.search || u.hash || u.username || u.password || u.origin !== new URL(base).origin || !u.href.startsWith(base)) fail('Migration URLs must stay in the exact approved bases and contain no query or fragment.');
  return u;
}
function inspect(html) {
  const tree = parse(html, { sourceCodeLocationInfo: true }), result = { canonicals: [], refresh: false, head: null, body: null };
  const visit = node => {
    const attrs = Object.fromEntries((node.attrs ?? []).map(a => [a.name, a.value]));
    if (node.tagName === 'link' && (attrs.rel ?? '').toLowerCase().split(/\s+/).includes('canonical')) result.canonicals.push(attrs.href);
    if (node.tagName === 'meta' && ((attrs['http-equiv'] ?? '').toLowerCase() === 'refresh' || attrs.name === 'elp-url-migration')) result.refresh = true;
    if (node.tagName === 'head') result.head = node.sourceCodeLocation?.startTag?.endOffset;
    if (node.tagName === 'body') result.body = node.sourceCodeLocation?.startTag?.endOffset;
    for (const child of node.childNodes ?? []) visit(child);
  };
  visit(tree); return result;
}
export function overlay(html, destination) {
  if (html.includes(marker)) fail('Old output already contains an overlay; rebuild fresh Quartz output.');
  const dom = inspect(html);
  if (!Number.isInteger(dom.head) || !Number.isInteger(dom.body) || dom.head >= dom.body || dom.refresh) fail('Expected a complete non-redirect old HTML document.');
  const data = JSON.stringify(destination).replace(/</g, '\\u003c');
  const script = `${marker}<script>(()=>{if(location.hash)return;location.replace(${data})})()</script>`;
  const banner = `${marker}<aside aria-label="새 사이트 안내" style="padding:1rem;border:1px solid currentColor;margin:1rem">새 문서 주소: <a href="${escape(destination)}">새 사이트에서 문서 열기</a>. 이전 항목 링크와 본문은 이 페이지에 보존됩니다.</aside>`;
  return html.slice(0, dom.head) + script + html.slice(dom.head, dom.body) + banner + html.slice(dom.body);
}
export async function buildPlan(map, oldRoot, currentRoot, c) {
  if (map.schemaVersion !== 1 || !Array.isArray(map.mappings) || map.mappings.length !== c.expectedMappings) fail('Unexpected mapping count/schema.');
  const result = [], seen = new Set();
  for (const m of map.mappings) {
    if (m.confirmed !== true) fail('Unconfirmed mapping.');
    const from = checked(m.from, c.oldBaseUrl), to = checked(m.to, c.targetBaseUrl);
    const old = decodeURIComponent(from.pathname.slice(new URL(c.oldBaseUrl).pathname.length));
    const next = decodeURIComponent(to.pathname.slice(new URL(c.targetBaseUrl).pathname.length));
    if (old.replace(/\/$/, '') !== next.replace(/\/$/, '')) fail('This release permits only verified unchanged full paths.');
    const file = !old ? 'index.html' : old.endsWith('/') ? `${old}index.html` : `${old}.html`;
    if (seen.has(file.normalize('NFC').toLowerCase())) fail('Duplicate/colliding old file.');
    seen.add(file.normalize('NFC').toLowerCase());
    const oldFile = path.join(oldRoot, file), targetFile = path.join(currentRoot, next ? `${next.replace(/\/$/, '')}/index.html` : 'index.html');
    const [before, current] = await Promise.all([regular(oldFile), regular(targetFile)]);
    if (!Buffer.from(before.toString('utf8')).equals(before) || !Buffer.from(current.toString('utf8')).equals(current)) fail('HTML must be UTF-8.');
    const target = inspect(current.toString('utf8'));
    if (target.refresh || target.canonicals.length !== 1 || checked(target.canonicals[0], c.targetBaseUrl).href !== to.href) fail(`Target is not the exact final canonical page: ${m.to}`);
    let after;
    try { after = Buffer.from(overlay(before.toString('utf8'), to.href)); }
    catch (error) { fail(`${file}: ${error.message}`); }
    result.push({ file, oldFile, targetFile, from: from.href, to: to.href, before, after, beforeHash: hash(before), afterHash: hash(after) });
  }
  return result;
}
async function replace(file, bytes) {
  const temporary = path.join(path.dirname(file), `.elp-transition-${randomUUID()}.tmp`), h = await open(temporary, 'wx', 0o644);
  try { await h.writeFile(bytes); await h.close(); await rename(temporary, file); }
  finally { await h.close().catch(() => {}); await rm(temporary, { force: true }); }
}
export async function applyPlan(plan, backupRoot) {
  await mkdir(backupRoot); // A previous backup is never overwritten.
  const written = [];
  try {
    for (const item of plan) {
      if (hash(await regular(item.oldFile)) !== item.beforeHash) fail('Old output changed during validation.');
      const backup = path.join(backupRoot, item.file); await mkdir(path.dirname(backup), { recursive: true });
      const h = await open(backup, 'wx', 0o600); try { await h.writeFile(item.before); } finally { await h.close(); }
    }
    for (const item of plan) {
      if (hash(await regular(item.oldFile)) !== item.beforeHash) fail('Old output changed before applying overlays.');
      await replace(item.oldFile, item.after); written.push(item);
    }
  } catch (error) { for (const item of written.reverse()) await replace(item.oldFile, item.before); throw error; }
}
async function main(args) {
  if (args[0] === '--gate' && args.length === 2) {
    const c = await readConfiguration(args[1]);
    if (process.env.GITHUB_OUTPUT) await appendFile(process.env.GITHUB_OUTPUT, `enabled=${c.enabled}\ntarget_commit=${c.enabled ? c.approvedTargetCommit : ''}\n`);
    console.log(c.enabled ? 'Approved ELP transition is enabled.' : 'ELP transition is disabled; the existing Quartz deployment is unchanged.'); return;
  }
  if (args[0] !== '--apply' || args.length !== 4) fail('Usage: --gate config OR --apply config old-output target-checkout');
  const c = await readConfiguration(args[1]); if (!c.enabled) fail('Transition is disabled.');
  const targetRoot = path.resolve(args[3]);
  const revision = execFileSync('git', ['-C', targetRoot, 'rev-parse', 'HEAD'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  if (revision !== c.approvedTargetCommit) fail('Target checkout does not match the approved immutable commit.');
  const boundary = JSON.parse(await regular(path.join(targetRoot, '.elp-site.json'))), info = JSON.parse(await regular(path.join(targetRoot, 'site/build-info.json')));
  if (boundary.schemaVersion !== 1 || boundary.sourceRepository !== 'Kaelrots/elrixh-prauxhyekth-publish-project' || boundary.outputDirectory !== 'site' || info.buildId !== c.approvedBuildId) fail('Target publication boundary/build ID does not match approval.');
  const map = JSON.parse(await regular(c.mapFile)), plan = await buildPlan(map, path.resolve(args[2]), path.join(targetRoot, 'site'), c);
  await applyPlan(plan, '.elp-transition-backup');
  const report = { schemaVersion: 1, targetCommit: revision, buildId: info.buildId, mappings: plan.length, originalBodiesPreserved: true, allFragmentsStayOnOldPage: true, entries: plan.map(({ before, after, oldFile, targetFile, ...entry }) => entry) };
  const h = await open('elp-transition-report.json', 'wx', 0o600); try { await h.writeFile(JSON.stringify(report, null, 2)); } finally { await h.close(); }
  console.log(`Prepared ${plan.length} document redirects. All old fragments, unmapped pages, and assets are preserved.`);
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 1; });
