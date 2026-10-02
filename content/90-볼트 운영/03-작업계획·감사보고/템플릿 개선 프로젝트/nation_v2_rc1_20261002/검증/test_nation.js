// Node.js + PyYAML. --engine은 설치된 Templater 2.13.1 WASM 파서를 사용한다.
// Vault/Editor/Obsidian YAML API는 두 모드 모두 모의 환경이며 GUI 시험이 아니다.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const {execFileSync}=require('child_process');
const root=path.resolve(__dirname,'..');
const dir='90-볼트 운영/00-템플릿/';
const sourcePath=dir+'00-yaml 속성탭.md';
const moduleDir=dir+'국가 V2 구성요소/';
const entries={core:'01-01-국가 설정 템플릿 V2.md',detailed:'01-01-국가 설정 템플릿 V2 상세형.md'};
const moduleNames=['01-국가 Core.md','02-정치 행정.md','03-국토 수도.md','04-사회 문화.md','05-경제 산업.md','06-외교 군사와 역사.md','07-참고 및 문서 관리.md'];
const fmRenderer=require(path.join(root,'vault',dir,'유저 스크립트/render_frontmatter.js'));
const nationRenderer=require(path.join(root,'vault',dir,'유저 스크립트/render_nation.js'));
const engine=process.argv.includes('--engine');
let parser,parserHash;
const yamlBridge=String.raw`
import sys,json,yaml
from yaml.constructor import ConstructorError
class StrictLoader(yaml.SafeLoader): pass
def mapping(loader,node,deep=False):
    out={}
    for k,v in node.value:
        key=loader.construct_object(k,deep=deep)
        if key in out: raise ConstructorError('mapping',node.start_mark,'duplicate key: '+str(key),k.start_mark)
        out[key]=loader.construct_object(v,deep=deep)
    return out
StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
data=sys.stdin.read()
if sys.argv[1]=='load': print(json.dumps(yaml.load(data,Loader=StrictLoader),ensure_ascii=False))
else: print(yaml.safe_dump(json.loads(data),allow_unicode=True,sort_keys=False),end='')
`;
function yamlLoad(s){return JSON.parse(execFileSync(process.env.PYTHON||'python',['-c',yamlBridge,'load'],{input:s,encoding:'utf8'}));}
function yamlDump(x){return execFileSync(process.env.PYTHON||'python',['-c',yamlBridge,'dump'],{input:JSON.stringify(x),encoding:'utf8'});}
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
async function renderText(s,tp){
  if(engine) return parser.parse_commands(s,tp);
  let out='',offset=0;
  for(const m of s.matchAll(/<%(\*?)([\s\S]*?)%>/g)){
    out+=s.slice(offset,m.index);
    out+=m[1]?await new AsyncFunction('tp','tR',m[2]+'\nreturn tR;')(tp,''):await new AsyncFunction('tp','return ('+m[2]+');')(tp);
    offset=m.index+m[0].length;
  }
  return out+s.slice(offset);
}
function mock(config={}){
  const files=new Map();
  for(const name of ['00-yaml 속성탭.md',...Object.values(entries),...moduleNames.map(x=>'국가 V2 구성요소/'+x)]){
    files.set(dir+name,fs.readFileSync(path.join(root,'vault',dir,name),'utf8'));
  }
  if(config.sourcePath){files.set(config.sourcePath,files.get(sourcePath));files.delete(sourcePath);}
  if(config.sourceChange){const key=config.sourcePath||sourcePath;files.set(key,config.sourceChange(files.get(key)));}
  for(const [key,value] of Object.entries(config.replace??{}))files.set(key,value);
  for(const key of config.missing??[])files.delete(key);
  const state={files,writes:0,target:config.content??'',editor:config.editor??'',reads:[]};
  const target={path:config.targetPath??'시험/가상 국가.md',extension:'md',basename:config.title??'가상 국가'};
  const tf=p=>({path:p,extension:'md',basename:path.posix.basename(p,'.md')});
  const vault={getAbstractFileByPath:p=>files.has(p)?tf(p):null,
    read:async f=>{state.reads.push(f.path);return f.path===target.path?state.target:files.get(f.path);},
    modify:()=>{state.writes++;throw Error('쓰기 금지');},create:()=>{state.writes++;throw Error('쓰기 금지');}};
  const tp={app:{vault},config:{target_file:target,template_file:tf(dir+entries[config.preset??'core'])},
    date:{now:()=> '2026-10-02T20:00:00'},obsidian:{parseYaml:yamlLoad,stringifyYaml:yamlDump},
    file:{title:target.basename,include:async f=>renderText(files.get(f.path),tp)},user:{}};
  tp.user.render_frontmatter=async(...args)=>{
    const out=await fmRenderer(...args);
    if(config.afterFM)config.afterFM(state,tp);
    return out;
  };
  tp.user.render_nation=nationRenderer;
  if(config.editor!==undefined||config.afterFM)tp.app.workspace={activeEditor:{file:tf(config.editorPath??target.path),editor:{getValue:()=>state.editor}}};
  return{tp,state};
}
function parsed(out){const match=out.match(/^---\n([\s\S]*?)\n---\n/);assert(match,'출력 시작에 YAML 필요');return yamlLoad(match[1]);}
async function generate(preset='core',values={},config={},extra={}){
  const {tp,state}=mock({...config,preset});
  const out=await nationRenderer(tp,{preset,values,...extra});assert.equal(state.writes,0);
  return{out,data:parsed(out),state,tp};
}
async function rejected(options,config={},pattern){
  const {tp,state}=mock(config);await assert.rejects(nationRenderer(tp,options),pattern);assert.equal(state.writes,0);
}
const results=[];
async function test(name,fn){try{await fn();results.push({name,result:'PASS'});}catch(e){results.push({name,result:'FAIL',error:e.stack});}}
(async()=>{
 if(engine){
   const bundle=fs.readFileSync(process.env.TEMPLATER_BUNDLE,'utf8');
   const start=bundle.indexOf('var Vs={},N,He='),end=bundle.indexOf('var Xe;',start);
   assert(start>=0&&end>start,'Templater 2.13.1 파서 어댑터 확인 필요');
   const Parser=new Function('Ui',bundle.slice(start,end)+';return vi;')(s=>new Uint8Array(Buffer.from(s,'base64')));
   parser=new Parser();await parser.init();parserHash=crypto.createHash('sha256').update(bundle).digest('hex');
 }
 for(const [preset,name] of Object.entries(entries)){
   await test(`실제 시작형 전체 삽입: ${preset}`,async()=>{
     const {tp,state}=mock({preset});const text=fs.readFileSync(path.join(root,'vault',dir,name),'utf8');
     const output=await renderText(text,tp),data=parsed(output);
     assert.equal(data['제목'],'가상 국가');assert.equal(data['문서유형'],'entity');assert.equal(data['세부유형'],'nation');
     assert.deepEqual(data['분야'],['국가','정치']);assert.equal(data['사용된 템플릿'],name.slice(0,-3));
     assert.equal(data['템플릿 버전'],'2.0.0-rc.1');assert.equal(data['스키마버전'],'2.0.0');
     assert.equal(data.draft,true);assert.equal(data['정본상태'],'draft');assert.equal(data['작성상태'],'outline');assert.equal(data['검토상태'],'unreviewed');
     assert.equal(data['기준시점'],null);assert.equal(typeof data['최초작성일'],'string');assert.equal(state.writes,0);
     assert.equal((output.match(/^---$/gm)||[]).length,2);assert(!output.includes('<%'));assert(!output.includes('NATION_TIMESTAMP_BUTTON'));
     const dest=path.join(__dirname,'생성예시',engine?'실제파서':'모의');fs.mkdirSync(dest,{recursive:true});fs.writeFileSync(path.join(dest,name),output);
   });
   await test(`구획 구성: ${preset}`,async()=>{
     const {out}=await generate(preset);
     for(const heading of ['# 정치와 행정','# 국토와 수도','# 사회와 문화','# 경제와 산업','# 외교 군사와 역사'])assert.equal(out.includes(heading),preset==='detailed');
     for(const h of ['# 개요','# 기타 설정과 참고','# 문서 관리'])assert.equal(out.split(h).length-1,1);
   });
   await test(`시각 문법과 미입력 유지: ${preset}`,async()=>{
     const {out}=await generate(preset);for(const marker of ['| < |','| ^ |','<span','hr-thick-1','hr-thick-2','hr-thick-3','<center','<br','{작성}'])assert(out.includes(marker),marker);
     assert(!out.includes('#XXXXXX'));assert(!out.includes('98-%'));assert(!out.includes('[[]]'));assert(!out.includes('- [x]'));
   });
   await test(`기존 문서 삽입 거부: ${preset}`,()=>rejected({preset},{content:'---\ndraft: false\n---\n# 기존 설정'},/비어 있지/));
   await test(`시작형 생성기 누락 안내: ${preset}`,async()=>{
     const {tp}=mock({preset});delete tp.user.render_nation;
     await assert.rejects(renderText(fs.readFileSync(path.join(root,'vault',dir,name),'utf8'),tp),/User Script Folder/);
   });
 }
 await test('Frontmatter 원본 변경은 두 시작형에 함께 반영',async()=>{
   for(const preset of Object.keys(entries))assert.equal((await generate(preset,{}, {sourceChange:s=>s.replace('작성자: 현카엘','작성자: 시험작성자')})).data['작성자'],'시험작성자');
 });
 await test('Core 본문 한 곳 변경은 두 시작형에 함께 반영',async()=>{
   const file=moduleDir+moduleNames[0],original=fs.readFileSync(path.join(root,'vault',file),'utf8');
   for(const preset of Object.keys(entries))assert((await generate(preset,{}, {replace:{[file]:original+'\n공통본문변경시험\n'}})).out.includes('공통본문변경시험'));
 });
 await test('연속성·적용범위·기준시점·주소 값 보존',async()=>{
   const values={'연속성':['B루트'],'적용범위':['신계','라리셴베르크'],'기준시점':'제2기 100년',aliases:['과거 명칭','/old-nation'],permalink:'/nation-test'};
   const {data}=await generate('detailed',values);for(const [k,v] of Object.entries(values))assert.deepEqual(data[k],v);
 });
 await test('B루트 누락 거부',()=>rejected({preset:'core'},{targetPath:'80-대체루트·비정사/01-신계 B루트/국가.md'},/B루트/));
 await test('B루트 명시 생성',async()=>assert.deepEqual((await generate('core',{'연속성':['B루트']},{targetPath:'80-대체루트·비정사/01-신계 B루트/국가.md'})).data['연속성'],['B루트']));
 await test('복원 출처 및 호환값 보존',async()=>{
   const {data}=await generate('core',{'기원상태':'restored','복원원문문서명':'옛 국가 기록','복원원문최초작성일':'2015년 추정'});
   assert.equal(data['복원여부'],true);assert.equal(data['복원원문최초작성일'],'2015년 추정');assert.equal(data['복원원문최종수정일'],null);
 });
 await test('original과 복원 출처 충돌 거부',()=>rejected({values:{'복원원문문서명':'옛 기록'}},{},/충돌/));
 for(const title of ['국가: 부제','위키 [[표현]]', '따옴표 "국가"', '역슬래시\\국가','줄\n바꿈']){
   await test(`특수 제목 직렬화 ${JSON.stringify(title)}`,async()=>assert.equal((await generate('core',{}, {title})).data['제목'],title));
 }
 await test('공백 필수값 거부',()=>rejected({values:{'작성자':' \t '}},{},/필수값/));
 await test('저장 전 편집 내용 거부',()=>rejected({preset:'core'},{editor:'기존 내용'},/편집기/));
 await test('다른 활성 문서는 변경하거나 대상으로 삼지 않음',async()=>assert.equal((await generate('core',{}, {editor:'다른 기록',editorPath:'다른.md'})).data['세부유형'],'nation'));
 await test('공백만 있는 새 노트 허용',async()=>assert.equal((await generate('core',{}, {content:'\uFEFF\n ',editor:'\n '})).data.draft,true));
 for(const [key,value] of [['draft',false],['정본상태','canon'],['스키마버전','9.9.9'],['세부유형','region'],['사용된 템플릿','임의'],['분야',['법률']]]){
   await test(`상태·고정 분류 재정의 거부 ${key}`,()=>rejected({values:{[key]:value}}));
 }
 for(const name of moduleNames)await test(`본문 누락 시 전체 중단 ${name}`,()=>rejected({preset:'detailed'},{missing:[moduleDir+name]},/공통 본문/));
 for(const value of ['','---\n제목: 중복\n---\n# 개요','# 개요\n<% 1+1 %>']){
   await test(`잘못된 구성요소 거부 ${JSON.stringify(value)}`,()=>rejected({preset:'core'},{replace:{[moduleDir+moduleNames[0]]:value}},/일반 Markdown/));
 }
 await test('공통 원본 누락 시 전체 중단',()=>rejected({preset:'core'},{missing:[sourcePath]},/공통 원본/));
 await test('공통 생성기 누락 안내',async()=>{const {tp}=mock();delete tp.user.render_frontmatter;await assert.rejects(nationRenderer(tp),/render_frontmatter/);});
 await test('격리용 공통 sourcePath 재정의',async()=>{
   const other='검증원본/00-yaml 속성탭.md';assert.equal((await generate('core',{}, {sourcePath:other},{sourcePath:other})).data['스키마버전'],'2.0.0');
 });
 await test('조합 중 본문 변경 거부',()=>rejected({preset:'core'},{afterFM:s=>s.files.set(moduleDir+moduleNames[0],'# 변경')},/공통 본문이 변경/));
 await test('조합 중 대상 저장 내용 변경 거부',()=>rejected({preset:'core'},{afterFM:s=>{s.target='동시 입력';}},/대상 문서/));
 await test('조합 중 대상 편집기 변경 거부',()=>rejected({preset:'core'},{afterFM:s=>{s.editor='동시 입력';}},/편집기/));
 for(const preset of ['unknown','__proto__','constructor'])await test(`지원하지 않는 시작형 ${String(preset)}`,()=>rejected({preset},{},/지원하지 않는/));
 await test('미정의 옵션 거부',()=>rejected({templatePath:'임의.md'},{},/알 수 없는/));
 const body=fs.readFileSync(path.join(root,'vault',moduleDir,moduleNames[6]),'utf8');
 const buttonCode=body.match(/```dataviewjs\n([\s\S]*?)\n```/)[1];
 function buttonHarness(fm){
   const state={writes:0,file:null},button={},status={};
   const dv={current:()=>({file:{path:'시험/표시 국가.md'}}),container:{createEl:()=>({createEl:tag=>tag==='button'?button:status})}};
   const app={vault:{getAbstractFileByPath:p=>({path:p,extension:'md'})},fileManager:{processFrontMatter:async(file,fn)=>{const next={...fm};fn(next);state.writes++;state.file=file.path;Object.assign(fm,next);}}};
   new Function('dv','app','console',buttonCode)(dv,app,{error:()=>{}});return{state,button,status};
 }
 await test('수정일 버튼 열람만으로 쓰지 않음',async()=>assert.equal(buttonHarness({}).state.writes,0));
 await test('수정일 버튼은 표시 국가의 수정일만 변경',async()=>{
   const fm={'제목':'국가','문서유형':'entity','세부유형':'nation','정본상태':'canon','최종수정일':'old','문서버전':'2.3','검토상태':'reviewed',draft:false},before={...fm};
   const h=buttonHarness(fm);await h.button.onclick();assert.equal(h.state.file,'시험/표시 국가.md');assert.equal(h.state.writes,1);assert.notEqual(fm['최종수정일'],'old');
   delete before['최종수정일'];const after={...fm};delete after['최종수정일'];assert.deepEqual(after,before);assert.equal(h.button.disabled,false);
 });
 await test('수정일 버튼은 인물·템플릿 원본에서 중단',async()=>{
   for(const fm of [{'제목':'인물','문서유형':'entity','세부유형':'person','정본상태':'canon'},{'제목':'<% tp.file.title %>','문서유형':'entity','세부유형':'nation','정본상태':'draft'}]){
     const h=buttonHarness(fm);await h.button.onclick();assert.equal(h.state.writes,0);assert.match(h.status.textContent,/갱신하지 못했습니다/);
   }
 });

 await test('국가 선택지 원문은 생성 본문에 자동 삽입하지 않음',async()=>{
   for(const preset of Object.keys(entries)){
     const {out}=await generate(preset);
     assert(out.includes('국가 V1 선택표 보존본'));
     assert(!out.includes('BEGIN_V1_SYSTEM_CATALOG'));
     assert(!out.includes('국가(정부)의 개입 정도에 따른 경제 체제 구분'));
   }
 });
 await test('V1 특정 국가·인구·비율 예시를 기본값으로 넣지 않음',async()=>{
   const {out}=await generate('detailed');
   for(const token of ['95.72','99.99','일렌시엘','엘리시움 연방','세이나스','72,','98-%'])assert(!out.includes(token),token);
   assert(out.includes('인구 0으로 해석하지 않는다'));assert(out.includes('값이 없으면 0으로 채우지 않는다'));
 });
 await test('국가의 관점과 제도·실제 양상을 분리',async()=>{
   const {out}=await generate('detailed');
   for(const marker of ['공공(국가) 지향 이데올로기','민간(시민사회) 지향 이데올로기','관찰된 사실·작중 주장·해석 구분','영유권 주장·법적 지위·실제 통제·대표 점유국 표기를 구별'])assert(out.includes(marker));
 });
 await test('국토 기록은 지역 V2의 지리·행정 구분을 계승',async()=>{
   const {out}=await generate('detailed');
   for(const marker of ['전략지역권','지역층위와 법정 행정구역은 자동으로 동일하지 않다','복수 대륙','하나의 상위 권역'])assert(out.includes(marker));
 });
 await test('선택 장이 없어도 핵심형은 생성 가능',async()=>{
   const missing=moduleNames.slice(1,-1).map(x=>moduleDir+x);
   const {out}=await generate('core',{}, {missing});
   assert(out.includes('# 개요'));assert(!out.includes('# 경제와 산업'));
 });
 await test('수정일 버튼은 지역 실문서에서 중단',async()=>{
   const h=buttonHarness({'제목':'지역','문서유형':'entity','세부유형':'region','정본상태':'canon'});
   await h.button.onclick();assert.equal(h.state.writes,0);
 });
 const report={time:new Date().toISOString(),environment:engine?'Actual Templater 2.13.1 WASM parser + mock Vault/Editor/YAML API (PyYAML)':'Node.js mock Templater/Vault/Editor/YAML API (PyYAML)',parser_sha256:parserHash,pass:results.filter(x=>x.result==='PASS').length,fail:results.filter(x=>x.result==='FAIL').length,results};
 fs.writeFileSync(path.join(__dirname,engine?'Templater_실제파서_검사.json':'국가_모의검사.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({pass:report.pass,fail:report.fail,failures:results.filter(x=>x.result==='FAIL')},null,2));
 if(report.fail)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
