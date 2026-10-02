const fs=require('fs'),path=require('path'),assert=require('assert/strict'),{execFileSync}=require('child_process');
const root=path.resolve(__dirname,'../../../vault/90-볼트 운영/00-템플릿');
const fragment=require(path.join(root,'유저 스크립트/render_visual_fragment.js'));
const dir=path.join(root,'80-특수 목적 템플릿');
const results=[];
async function test(name,fn){try{await fn();results.push({name,result:'PASS'});}catch(e){results.push({name,result:'FAIL',error:e.stack});}}
const yaml=s=>JSON.parse(execFileSync('python',['-c','import sys,json,yaml;print(json.dumps(yaml.safe_load(sys.stdin.read()),ensure_ascii=False))'],{input:s,encoding:'utf8'}));
(async()=>{
 const bundle=fs.readFileSync(process.env.TEMPLATER_BUNDLE,'utf8');
 const a=bundle.indexOf('var Vs={},N,He='),b=bundle.indexOf('var Xe;',a);assert(a>=0&&b>a);
 const Parser=new Function('Ui',bundle.slice(a,b)+';return vi;')(s=>new Uint8Array(Buffer.from(s,'base64')));const parser=new Parser();await parser.init();
 async function run(name,{raw='',answers=[]}={}){
   let reads=0,prompts=0,writes=0;
   const tp={config:{target_file:{path:'시험/표시 문서.md'}},app:{vault:{read:async f=>{reads++;assert.equal(f.path,'시험/표시 문서.md');return raw;},modify:()=>{writes++;throw Error('직접 쓰기 금지');}}},obsidian:{parseYaml:yaml},date:{now:()=> '2026-10-03 00:00'},system:{prompt:async()=>answers[prompts++]},user:{render_visual_fragment:fragment}};
   const out=await parser.parse_commands(fs.readFileSync(path.join(dir,name),'utf8'),tp);assert.equal(writes,0);return {out,reads,prompts};
 }
 await test('편집 앵커는 실제 파서에서 시각 문법·날짜만 삽입',async()=>{const {out,reads}=await run('00-편집 앵커 V2.md');assert(out.includes('<center>'));assert(out.includes('2026-10-03 00:00'));assert(!out.includes('<%'));assert.equal(reads,0);});
 for(const [mode,name] of [['left','99-1-좌측 정렬 아이콘+설명문 V2.md'],['right','99-2-우측 정렬 아이콘+설명문 V2.md']]){
   await test('시각 조각 실제 삽입·정렬·br·인용부호 '+mode,async()=>{const {out}=await run(name,{answers:['그림 "1".png','제목 <이름>','앞<br>뒤','문서 "가"','하위 & 문서']});assert(out.includes('width="250"'));assert(out.includes('앞<br>뒤'));assert(out.includes('&quot;'));assert(out.includes('&lt;이름&gt;'));assert.equal(out.includes('row-reverse'),mode==='right');assert(out.includes('internal-link'));});
   await test('시각 조각 중간 입력 취소 '+mode,async()=>assert.equal((await run(name,{answers:['그림','제목',null]})).out.trim(),''));
 }
 await test('배지의 빈 값·중복·취소 처리',async()=>{const name='99-3-배지 추가 다중 V2.md';const {out}=await run(name,{answers:['문서A, 문서B, 문서A, , "문서C"']});assert.equal((out.match(/<span/g)||[]).length,3);assert(out.includes('&quot;'));assert.equal((await run(name,{answers:[null]})).out.trim(),'');});
 await test('복원문서는 출처 안내만 삽입',async()=>{const {out}=await run('00-복원문서주의사항 V2.md',{raw:'---\n기원상태: restored\n복원여부: true\n---\n# 기록'});assert(out.includes('복원 출처 안내'));assert(out.includes('<br>'));assert(!out.includes('2011'));assert(!out.includes('최신화되지 않았습니다'));});
 await test('신규 original 문서에는 복원 안내 없음',async()=>assert.equal((await run('00-복원문서주의사항 V2.md',{raw:'---\n기원상태: original\n복원여부: false\n---\n# 기록'})).out.trim(),''));
 await test('V1 복원여부 호환값 사용',async()=>assert((await run('00-복원문서주의사항 V2.md',{raw:'---\n복원여부: true\n---\n# 기록'})).out.includes('복원 출처 안내')));
 await test('복원 상태 충돌 시 삽입 중단',async()=>{for(const [origin,legacy] of [['original',true],['restored',false]])await assert.rejects(run('00-복원문서주의사항 V2.md',{raw:`---\n기원상태: ${origin}\n복원여부: ${legacy}\n---\n# 기록`}),/충돌/);});
 await test('복원 안내 중복 삽입 방지·BOM·CRLF',async()=>{const raw='\uFEFF---\r\n기원상태: restored\r\n복원여부: true\r\n---\r\n# 기록';assert((await run('00-복원문서주의사항 V2.md',{raw})).out.includes('복원 출처 안내'));assert.equal((await run('00-복원문서주의사항 V2.md',{raw:raw+'\n<!-- restored-note-v2 -->'})).out.trim(),'');});
 const code=fs.readFileSync(path.join(dir,'00-최종수정일 갱신 V2.md'),'utf8').match(/```dataviewjs\n([\s\S]*?)\n```/)[1];
 function button(fm,displayPath='시험/표시.md'){
   const state={writes:0},button={},status={};
   const dv={current:()=>({file:{path:displayPath}}),container:{createEl:()=>({createEl:t=>t==='button'?button:status})}};
   const app={workspace:{getActiveFile:()=>({path:'시험/다른 활성.md'})},vault:{getAbstractFileByPath:p=>({path:p,extension:'md'})},fileManager:{processFrontMatter:async(f,fn)=>{const next={...fm};fn(next);state.writes++;state.file=f.path;Object.assign(fm,next);}}};
   new Function('dv','app',code)(dv,app);return{state,button,status};
 }
 const valid=()=>({'스키마버전':'2.0.0','제목':'시험','문서유형':'entity','정본상태':'canon','최종수정일':'old','최초작성일':'old-created',draft:false,'검토상태':'reviewed','문서버전':'2.4'});
 await test('수정일 버튼 열람은 무변경',async()=>assert.equal(button(valid()).state.writes,0));
 await test('활성 탭이 달라도 표시 문서의 수정일만 갱신',async()=>{const fm=valid(),before={...fm},h=button(fm);await h.button.onclick();assert.equal(h.state.file,'시험/표시.md');assert.equal(h.state.writes,1);assert.notEqual(fm['최종수정일'],'old');delete before['최종수정일'];const after={...fm};delete after['최종수정일'];assert.deepEqual(after,before);});
 await test('V1·템플릿·잘못된 상태 거부',async()=>{for(const fm of [{...valid(),'스키마버전':'1.0'},{...valid(),'문서유형':'template'},{...valid(),'제목':'<% tp.file.title %>'},{...valid(),'정본상태':'unknown'}]){const h=button(fm);await h.button.onclick();assert.equal(h.state.writes,0);}});
 await test('00-템플릿 경로에서는 갱신 거부',async()=>{const h=button(valid(),'90-볼트 운영/00-템플릿/원본.md');await h.button.onclick();assert.equal(h.state.writes,0);});
 const report={pass:results.filter(x=>x.result==='PASS').length,fail:results.filter(x=>x.result==='FAIL').length,environment:'Actual Templater 2.13.1 WASM parser + mock prompts/Vault/YAML; Dataview button harness, no GUI test',results};
 fs.writeFileSync(path.join(__dirname,'운영조각_검사.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({pass:report.pass,fail:report.fail,failures:results.filter(x=>x.result==='FAIL')},null,2));if(report.fail)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
