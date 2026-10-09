import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm, symlink } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { runInNewContext } from 'node:vm';
import { overlay, buildPlan, applyPlan, readConfiguration } from '../scripts/elp-legacy-transition.mjs';

const oldBaseUrl = 'https://kaelrots.github.io/elrixh-prauxhyekth/', targetBaseUrl = 'https://kaelrots.github.io/elrixh-prauxhyekth-site/';
const c = { oldBaseUrl, targetBaseUrl, expectedMappings: 1 };
const map = { schemaVersion: 1, mappings: [{ from: `${oldBaseUrl}same`, to: `${targetBaseUrl}same/`, confirmed: true }] };
const old = '<!doctype html><html><head><script>const quoted="<head>"</script></head><body class="quartz"><h2 id="article-8">OLD MEANING</h2><img src="original.png"></body></html>';
async function fixture(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'elp-quartz-transition-')); t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(path.join(root, 'old')); await mkdir(path.join(root, 'new/same'), { recursive: true });
  await writeFile(path.join(root, 'old/same.html'), old); await writeFile(path.join(root, 'old/unmapped.html'), old); await writeFile(path.join(root, 'old/original.png'), 'IMAGE');
  await writeFile(path.join(root, 'new/same/index.html'), `<html><head><link rel="canonical" href="${targetBaseUrl}same/"></head><body><h2 id="article-8">NEW MEANING</h2></body></html>`);
  return root;
}
test('only a full document redirects; every old fragment remains on the old meaning', () => {
  const result = overlay(old, `${targetBaseUrl}same/`);
  const script = /<!-- ELP-LEGACY-TRANSITION:1 --><script>([\s\S]*?)<\/script>/.exec(result)[1];
  for (const fragment of ['', '#article-8', '#unknown', '#%QQ']) {
    let destination = ''; runInNewContext(script, { location: { hash: fragment, replace: url => destination = url } });
    assert.equal(destination, fragment ? '' : `${targetBaseUrl}same/`);
  }
  assert.ok(result.includes('<h2 id="article-8">OLD MEANING</h2><img src="original.png">'));
  assert.throws(() => overlay(result, targetBaseUrl), /already contains/);
});
test('false gate needs no target, while enabled gate needs explicit immutable commit/build', async t => {
  const root = await fixture(t), file = path.join(root, 'config.json');
  const config = { ...c, schemaVersion: 1, enabled: false, expectedMappings: 377, targetRepository: 'Kaelrots/elrixh-prauxhyekth-site', mapFile: 'config/elp-legacy-mappings.json', approvedTargetCommit: null, approvedBuildId: null };
  await writeFile(file, JSON.stringify(config)); assert.equal((await readConfiguration(file)).enabled, false);
  await writeFile(file, JSON.stringify({ ...config, enabled: true })); await assert.rejects(readConfiguration(file), /approved target commit/);
});
test('applying verified overlays preserves old body, exact rollback backup, other pages, assets, and target output', async t => {
  const root = await fixture(t), oldRoot = path.join(root, 'old'), newRoot = path.join(root, 'new');
  const current = await readFile(path.join(newRoot, 'same/index.html'));
  const plan = await buildPlan(map, oldRoot, newRoot, c); await applyPlan(plan, path.join(root, 'backup'));
  assert.equal(await readFile(path.join(root, 'backup/same.html'), 'utf8'), old);
  assert.equal(await readFile(path.join(oldRoot, 'unmapped.html'), 'utf8'), old);
  assert.equal(await readFile(path.join(oldRoot, 'original.png'), 'utf8'), 'IMAGE');
  assert.deepEqual(await readFile(path.join(newRoot, 'same/index.html')), current);
  assert.ok((await readFile(path.join(oldRoot, 'same.html'), 'utf8')).includes('OLD MEANING'));
});
test('all validation happens before writing; wrong target or changed original aborts', async t => {
  const root = await fixture(t), oldRoot = path.join(root, 'old'), newRoot = path.join(root, 'new');
  await assert.rejects(buildPlan({ schemaVersion: 1, mappings: [{ ...map.mappings[0], to: `${targetBaseUrl}different/` }] }, oldRoot, newRoot, c), /unchanged full paths/);
  const plan = await buildPlan(map, oldRoot, newRoot, c);
  await writeFile(path.join(oldRoot, 'same.html'), 'USER CHANGE');
  await assert.rejects(applyPlan(plan, path.join(root, 'backup')), /changed during/);
  assert.equal(await readFile(path.join(oldRoot, 'same.html'), 'utf8'), 'USER CHANGE');
});
test('canonical redirects and wrong bases fail instead of making a redirect chain', async t => {
  const root = await fixture(t), oldRoot = path.join(root, 'old'), newRoot = path.join(root, 'new');
  await writeFile(path.join(newRoot, 'same/index.html'), `<html><head><meta http-equiv="refresh" content="0;url=/elsewhere"><link rel="canonical" href="${targetBaseUrl}same/"></head><body></body></html>`);
  await assert.rejects(buildPlan(map, oldRoot, newRoot, c), /final canonical/);
  await assert.rejects(buildPlan({ schemaVersion: 1, mappings: [{ ...map.mappings[0], from: 'https://kaelrots.github.io/same' }] }, oldRoot, newRoot, c), /approved bases/);
});
test('symlink paths are never followed when inspecting public HTML', async t => {
  const root = await fixture(t), file = path.join(root, 'old/same.html');
  await rm(file); await symlink(path.join(root, 'old/unmapped.html'), file);
  await assert.rejects(buildPlan(map, path.join(root, 'old'), path.join(root, 'new'), c), /regular path/);
});
test('an empty old HTML blocks the complete transition before any page is changed', async t => {
  const root = await fixture(t), file = path.join(root, 'old/same.html');
  await writeFile(file, '');
  await assert.rejects(buildPlan(map, path.join(root, 'old'), path.join(root, 'new'), c), /same.html: Expected a complete/);
  assert.equal(await readFile(file, 'utf8'), '');
  assert.equal(await readFile(path.join(root, 'old/unmapped.html'), 'utf8'), old);
});
