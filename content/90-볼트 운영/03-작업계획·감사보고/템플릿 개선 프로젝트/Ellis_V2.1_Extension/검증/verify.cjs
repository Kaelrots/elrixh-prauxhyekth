const fs=require('fs');
const path=require('path');
const assert=require('assert/strict');
const crypto=require('crypto');
const root=path.resolve(process.argv[2] || path.join(__dirname,'..'));
const deps=process.argv[3] ? path.resolve(process.argv[3]) : __dirname;
const yaml=require(require.resolve('js-yaml',{paths:[deps]}));
const MarkdownIt=require(require.resolve('markdown-it',{paths:[deps]}));
const md=new MarkdownIt({html:true});
const vaultRoot=path.join(root,'vault');
const ext='90-볼트 운영/00-템플릿/V2.1 신규 확장/';
const sourcePath='90-볼트 운영/00-템플릿/00-yaml 속성탭.md';
const registry=JSON.parse(fs.readFileSync(path.join(vaultRoot,ext,'registry.json'),'utf8'));
const original=require(path.join(root,'참조-설치대상아님/render_frontmatter.js'));
const extension=require(path.join(vaultRoot,'90-볼트 운영/00-템플릿/유저 스크립트/render_extension_v21.js'));
const ssot=fs.readFileSync(path.join(root,'참조-설치대상아님/00-yaml 속성탭.md'),'utf8');
const checks=[];
const passed=(name,extra={})=>checks.push({name,status:'PASS',...extra});
let writes=0;
const stableDate='2026-10-03T12:34:56';

function environment(key,opts={}) {
  const config=registry.presets[key];
  const target={path:opts.targetPath || '검증 대상/새 문서.md',extension:'md'};
  const template={path:config.starter,extension:'md'};
  const paths=new Map();
  paths.set(target.path,opts.existing || '');
  paths.set(sourcePath,ssot);
  for(const p of [...config.modules,ext+'registry.json',config.starter]) paths.set(p,fs.readFileSync(path.join(vaultRoot,p),'utf8'));
  if(opts.missing) paths.delete(opts.missing);
  const reads=new Map();
  const vault={
    getAbstractFileByPath(p) { return paths.has(p) ? {path:p,extension:p.split('.').pop()} : null; },
    async read(file) {
      if(!paths.has(file.path)) throw new Error('Missing: '+file.path);
      reads.set(file.path,(reads.get(file.path)||0)+1);
      if(opts.race===file.path && reads.get(file.path)>1) return paths.get(file.path)+'\n변경';
      return paths.get(file.path);
    },
    async modify(){writes++;throw new Error('Unexpected write');},
    async create(){writes++;throw new Error('Unexpected create');},
    async delete(){writes++;throw new Error('Unexpected delete');}
  };
  const tp={
    app:{vault,workspace:{activeEditor:{file:target,editor:{getValue:()=>opts.editor || opts.existing || ''}}}},
    config:{target_file:target,template_file:template},
    file:{title:opts.title || '검증용: 한글 "제목" # 1',async include(file){
      const raw=await vault.read(file);
      return raw.replace(/<%\s*([\s\S]*?)\s*%>/g,(_,expr)=>new Function('tp','return ('+expr+');')(tp));
    }},
    date:{now:()=>stableDate},
    obsidian:{parseYaml:s=>yaml.load(s),stringifyYaml:o=>yaml.dump(o,{lineWidth:-1,noRefs:true})},
    user:{render_frontmatter:original,render_extension_v21:extension}
  };
  return {tp,paths};
}

async function expectReject(name,fn,pattern){
  await assert.rejects(fn,pattern);
  passed(name);
}

async function main(){
  assert.equal(registry.families.length,12);
  assert.equal(Object.keys(registry.presets).length,35);
  assert.equal(new Set(registry.families.map(f=>f.id)).size,12);
  passed('12계열·35시작형 및 고유 식별자');
  const previews=path.join(root,'미리보기-설치대상아님');
  fs.mkdirSync(previews,{recursive:true});
  const results=[];
  for(const [key,c] of Object.entries(registry.presets)){
    const {tp}=environment(key);
    const source=fs.readFileSync(path.join(vaultRoot,c.starter),'utf8').trim();
    const match=source.match(/^<%\*\s*([\s\S]*?)\s*%>$/);
    assert.ok(match,'single execution block');
    const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
    const out=await new AsyncFunction('tp','let tR="";\n'+match[1]+'\nreturn tR;')(tp);
    const fm=out.match(/^---\n([\s\S]*?)\n---\n/);
    assert.ok(fm,'frontmatter');
    const data=yaml.load(fm[1]);
    const body=out.slice(fm[0].length).trim();
    assert.equal((out.match(/^---$/gm)||[]).length,2);
    assert.equal((body.match(/^# /gm)||[]).length,1);
    assert.ok(!out.includes('<%'));
    assert.ok(!out.includes('undefined'));
    assert.ok(body.includes('{작성}'));
    for(const word of ['미정','미상','없음','해당 없음','관련 문서·근거','작성·검토 메모']) assert.ok(body.includes(word),word);
    assert.equal(data['제목'],tp.file.title);
    assert.equal(data['스키마버전'],'2.0.0');
    assert.equal(data['템플릿 버전'],'2.1.0');
    assert.equal(data['문서버전'],'0.1.0');
    assert.equal(data['정본상태'],'draft');
    assert.equal(data['작성상태'],'outline');
    assert.equal(data['검토상태'],'unreviewed');
    assert.equal(data.draft,true);
    assert.equal(data['기원상태'],'original');
    assert.equal(data['복원여부'],false);
    assert.equal(data['최초작성일'],stableDate);
    assert.equal(data['최종수정일'],stableDate);
    assert.equal(data['기준시점'],null);
    for(const k of ['aliases','tags','분야','적용범위']) assert.ok(Array.isArray(data[k]));
    for(const [k,v] of Object.entries(c.values)) assert.deepEqual(data[k],v);
    for(const k of ['태그','tag','별칭','카테고리','폴더','경로','물리위치']) assert.ok(!Object.hasOwn(data,k));
    const tokens=md.parse(body,{});
    const tables=[];
    let cols=0;
    for(const t of tokens){
      if(t.type==='tr_open') cols=0;
      if(t.type==='th_open'||t.type==='td_open') cols++;
      if(t.type==='tr_close') assert.ok(cols<=4,'four column maximum');
      if(t.type==='table_open') tables.push(t);
    }
    assert.ok(tables.length>=3);
    const html=md.render(body);
    assert.ok(html.includes('<h1>개요</h1>'));
    assert.ok(!html.includes('<script'));
    const preview='# 생성 본문 미리보기 — '+c.name+'\n\n이 파일은 검토용이며 설치·새 문서 생성의 원본이 아니다. 실제 시작형은 SSOT에서 YAML을 생성한다.\n\n'+body.replace(/^# 개요/m,'## 개요')+'\n';
    fs.writeFileSync(path.join(previews,key+'.md'),preview,'utf8');
    const corechars=body.length;
    results.push({preset:key,family:c.family,type:data['문서유형'],subtype:data['세부유형'],body_characters:corechars,modules:c.modules.length});
    passed('생성·YAML·Markdown: '+key);
    await expectReject('기존 노트 보호: '+key,()=>extension(environment(key,{existing:'보존해야 할 기존 내용'}).tp,{preset:key}),/비어 있지|내용이 있는/);
  }
  const key='X21-01-core';
  await expectReject('저장 전 편집기 내용 보호',()=>extension(environment(key,{editor:'아직 저장하지 않은 본문'}).tp,{preset:key}),/편집기/);
  await expectReject('템플릿 폴더를 생성 대상으로 사용 금지',()=>extension(environment(key,{targetPath:ext+'빈 파일.md'}).tp,{preset:key}),/생성 대상으로/);
  await expectReject('누락된 구성요소 탐지',()=>extension(environment(key,{missing:registry.presets[key].modules[0]}).tp,{preset:key}),/파일을 찾지/);
  await expectReject('누락된 SSOT 탐지',()=>extension(environment(key,{missing:sourcePath}).tp,{preset:key}),/공통 원본/);
  await expectReject('누락된 공통 생성기 탐지',()=>{const {tp}=environment(key);delete tp.user.render_frontmatter;return extension(tp,{preset:key});},/기존 V2/);
  await expectReject('알 수 없는 시작형 거부',()=>extension(environment(key).tp,{preset:'X21-99-core'}),/알 수 없는 시작형/);
  await expectReject('고정 분류 덮어쓰기 거부',()=>extension(environment(key).tp,{preset:key,values:{'문서유형':'event'}}),/고정 분류/);
  await expectReject('잠긴 상태 덮어쓰기 거부',()=>extension(environment(key).tp,{preset:key,values:{'정본상태':'canon'}}),/덮어쓸 수 없는/);
  await expectReject('금지 공통 키 거부',()=>extension(environment(key).tp,{preset:key,values:{'태그':[]}}),/금지 키/);
  await expectReject('배열 자료형 불일치 거부',()=>extension(environment(key).tp,{preset:key,values:{aliases:'잘못된 문자열'}}),/자료형 불일치/);
  await expectReject('알 수 없는 옵션 거부',()=>extension(environment(key).tp,{preset:key,sourcePath:'다른 원본.md'}),/알 수 없는 옵션/);
  await expectReject('구성요소 변경 중 생성 거부',()=>extension(environment(key,{race:registry.presets[key].modules[0]}).tp,{preset:key}),/구성요소가 바뀌었/);
  const bp='80-대체루트·비정사/01-신계 B루트/새 노트.md';
  await expectReject('B루트 연속성 누락 거부',()=>extension(environment(key,{targetPath:bp}).tp,{preset:key}),/B루트/);
  const b=await extension(environment(key,{targetPath:bp}).tp,{preset:key,values:{'연속성':['B루트'],'기준시점':'제2기 중엽'}});
  assert.deepEqual(yaml.load(b.match(/^---\n([\s\S]*?)\n---/)[1])['연속성'],['B루트']);
  passed('명시적 B루트 연속성·작중 기준시점 전달');
  assert.equal(writes,0);
  passed('Vault 파일 쓰기·수정·삭제 호출 0건');
  const files=[];
  function walk(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,e.name);e.isDirectory()?walk(p):files.push(p);}}
  walk(vaultRoot);
  assert.ok(files.every(p=>p.includes(path.normalize(ext)) || p.endsWith(path.normalize('유저 스크립트/render_extension_v21.js'))));
  assert.ok(!files.some(p=>path.basename(p)==='00-yaml 속성탭.md'||path.basename(p)==='render_frontmatter.js'));
  passed('설치 트리는 확장 폴더·새 조합기만 포함 — 기존 V2 파일 없음');
  // Package links are relative Markdown links. All generated guidance links must resolve.
  const all=[];
  function walkAll(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,e.name);e.isDirectory()?walkAll(p):all.push(p);}}
  walkAll(root);
  let linkCount=0;
  for(const file of all.filter(p=>p.endsWith('.md'))){
    const text=fs.readFileSync(file,'utf8');
    for(const m of text.matchAll(/\]\(<([^>]+)>\)/g)){
      if(/^https?:/.test(m[1]))continue;
      assert.ok(fs.existsSync(path.resolve(path.dirname(file),m[1])),file+' -> '+m[1]);linkCount++;
    }
  }
  passed('패키지 내부 Markdown 링크 실재 확인',{links:linkCount});
  const fmhash=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'참조-설치대상아님/render_frontmatter.js'))).digest('hex');
  const report={date:'2026-10-03',package_version:'2.1.0',schema_version:'2.0.0',execution:'Single Templater execution-block JavaScript evaluated with simulated Vault/editor/date/include APIs and actual V2 render_frontmatter.js; js-yaml 4.1.0 and markdown-it 14.1.0. Not the actual Templater WASM parser.',total_checks:checks.length,failed:0,vault_writes:writes,source_renderer_sha256:fmhash,checks,presets:results,unverified:['Obsidian UI','Prism rendering','Actual Templater plugin and WASM parser','Quartz build and publishing filters','Existing queries and extractors']};
  fs.mkdirSync(path.join(root,'검증'),{recursive:true});
  fs.writeFileSync(path.join(root,'검증/자동검증 결과.json'),JSON.stringify(report,null,2)+'\n','utf8');
  console.log(JSON.stringify({checks:checks.length,failed:0,presets:results.length,links:linkCount,files:files.length,core_sizes:results.filter(r=>r.preset.endsWith('-core')).map(r=>({id:r.family,chars:r.body_characters}))}));
}
main().catch(e=>{console.error(e);process.exit(1);});
