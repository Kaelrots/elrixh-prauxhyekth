// Node.js 모의환경 검사. 실제 Obsidian/Templater를 구동하는 시험이 아니다.
// 의존: Node.js 및 PyYAML이 설치된 python. 실행: node 검증/test_renderer.js
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const root=path.resolve(__dirname,'../../..');
const renderer = require(path.join(root, 'vault/90-볼트 운영/00-템플릿/유저 스크립트/render_frontmatter.js'));
const original = fs.readFileSync(path.join(root, 'vault/90-볼트 운영/00-템플릿/00-yaml 속성탭.md'), 'utf8');
const sourcePath = '90-볼트 운영/00-템플릿/00-yaml 속성탭.md';
const sourceFile = { path: sourcePath, extension: 'md', basename: '00-yaml 속성탭' };
const yamlBridge = String.raw`
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
if sys.argv[1]=='load':
    print(json.dumps(yaml.load(data,Loader=StrictLoader),ensure_ascii=False))
else:
    print(yaml.safe_dump(json.loads(data),allow_unicode=True,sort_keys=False),end='')
`;
function load(text){ return JSON.parse(execFileSync('python',['-c',yamlBridge,'load'],{input:text,encoding:'utf8'})); }
function dump(data){ return execFileSync('python',['-c',yamlBridge,'dump'],{input:JSON.stringify(data),encoding:'utf8'}); }
const baseValues = () => ({ '문서유형':'entity','세부유형':'person','분야':['인물'],
  '사용된 템플릿':'04-인물 설정 템플릿 V2 파일럿','템플릿 버전':'2.0.0-rc.1','기준시점':null });
function mock(config={}){
  const state={source:config.source??original,target:config.targetContent??'',editor:config.editorContent??'',writes:0,includes:0};
  const target={path:config.targetPath??'시험/가상 인물.md',extension:'md',basename:'가상 인물'};
  const source={...sourceFile,path:config.sourcePath??sourcePath};
  const app={vault:{
    read:async file => file.path===source.path?state.source:state.target,
    getAbstractFileByPath:p => !config.missingSource && p===source.path?source:null,
    modify:()=>{state.writes++;throw Error('write forbidden');},
    create:()=>{state.writes++;throw Error('write forbidden');},
  }};
  const tp={app,config:{target_file:target,template_file:{path:'템플릿/인물.md'}},
    date:{now:()=> '2026-10-02T16:00:00'},
    obsidian:{parseYaml:load,stringifyYaml:dump},
    file:{title:config.title??'가상 인물',include:async file=>{
      state.includes++;
      assert.equal(file.path,source.path);
      const text=await parser.parse_commands(state.source,tp);
      if(config.changeSource) state.source+='\n# concurrent change\n';
      if(config.changeTarget) state.target='다른 편집기가 입력함';
      if(config.changeEditor) state.editor='저장 전 새 입력';
      return text;
    }}
  };
  tp.user={render_frontmatter:renderer};
  if(config.editorContent !== undefined || config.changeEditor) app.workspace={activeEditor:{
    file:{path:config.editorPath??target.path},editor:{getValue:()=>state.editor}
  }};
  return {tp,state};
}
function parsed(text){ return load(text.match(/^---\n([\s\S]*?)\n---\n$/)[1]); }
const results=[];
async function test(name,fn){
  try{await fn(); results.push({name,result:'PASS'});}
  catch(e){results.push({name,result:'FAIL',error:e.stack});}
}
async function generate(values={},options={},config={}){
  const {tp,state}=mock(config);
  const out=await renderer(tp,{...options,values:{...baseValues(),...values}});
  assert.equal(state.writes,0);
  return {out,data:parsed(out),state};
}
async function rejects(values={},options={},config={}){
  const {tp,state}=mock(config);
  await assert.rejects(renderer(tp,{...options,values:{...baseValues(),...values}}));
  assert.equal(state.writes,0);
}

const bundlePath = process.env.TEMPLATER_BUNDLE;
if (!bundlePath) throw new Error('TEMPLATER_BUNDLE에 설치된 Templater 2.13.1 main.js 경로를 지정한다.');
const bundle = fs.readFileSync(bundlePath,'utf8');
const start = bundle.indexOf('var Vs={},N,He=');
const end = bundle.indexOf('var Xe;', start);
if (start<0 || end<0) throw new Error('검증한 2.13.1 파서 구조와 다르다. 원본을 수정하지 말고 검사 어댑터를 검토한다.');
// 설치된 번들에서 WASM 파서 및 바인딩만 메모리에 읽는다. 앱/플러그인 수명주기는 실행하지 않는다.
const Parser = new Function('Ui', bundle.slice(start,end)+';return vi;')(
  text=>new Uint8Array(Buffer.from(text,'base64')));
const parser = new Parser();

(async()=>{
 await parser.init();
 await test('신규 인물: 원본 기본값과 호출부 병합',async()=>{
  const {data,state}=await generate();
  assert.equal(data['제목'],'가상 인물');assert.equal(data['문서유형'],'entity');
  assert.equal(data['스키마버전'],'2.0.0');assert.equal(data['템플릿 버전'],'2.0.0-rc.1');
  assert.equal(data['정본상태'],'draft');assert.equal(data.draft,true);
  assert.equal(data['복원여부'],false);assert.equal(state.includes,1);
 });
 await test('미사용 선택필드는 생략, 명시된 기준시점 null은 유지',async()=>{
  const {data}=await generate();
  for(const key of ['연속성','상위개념','하위개념','permalink','최종검토일','복원원문문서명']) assert(!Object.hasOwn(data,key));
  assert(Object.hasOwn(data,'기준시점'));assert.equal(data['기준시점'],null);
 });
 await test('연속성·개념관계·공개주소·별칭 선택값 전달',async()=>{
  const fields={ '연속성':['B루트'],'상위개념':['[[상위 개념]]'],'하위개념':['[[하위 개념]]'],
   permalink:'/stable/sample',aliases:['인물 별칭','/old/public/sample'] };
  const {data}=await generate(fields);for(const [k,v] of Object.entries(fields))assert.deepEqual(data[k],v);
 });
 await test('원본에서 원창작→복원으로 지정하면 호환값 true',async()=>{
  const {data}=await generate({'기원상태':'restored','복원원문문서명':'옛 기록.md','복원원문최초작성일':'2015년 추정'});
  assert.equal(data['복원여부'],true);assert.equal(data['복원원문최초작성일'],'2015년 추정');
  assert.equal(data['복원원문최종수정일'],null);
 });
 await test('기원 불명은 null, false/original로 추정하지 않음',async()=>{
  const {data}=await generate({'기원상태':null});assert.equal(data['기원상태'],null);assert.equal(data['복원여부'],null);
 });
 for(const kind of ['master','concept','entity','reference','index','report','template','archive','event','period','rule','ledger']){
  await test(`문서유형 ${kind} 보존·허용`,async()=>assert.equal((await generate({'문서유형':kind})).data['문서유형'],kind));
 }
 await test('미정의 유형 거부',()=>rejects({'문서유형':'made_up'}));
 await test('정본 자동승격 거부',()=>rejects({'정본상태':'canon'}));
 await test('신규 즉시 공개값 주입 거부',()=>rejects({draft:false}));
 await test('생성일 기본값 재정의 거부',()=>rejects({'최초작성일':'2000-01-01'}));
 await test('스키마 버전 숫자만 변경하는 호출 거부',()=>rejects({'스키마버전':'9.9.9'}));
 await test('출처와 original 모순 거부',()=>rejects({'복원원문문서명':'old.md'}));
 await test('확장 공통키 충돌 거부',()=>rejects({}, {extensions:{draft:false}}));
 await test('기술 고유 ID/doc_type/전용 속성 유지',async()=>{
  const x={gate_id:'G2-01-001',doc_type:'gate_node',prereq_hard:['G2-01-000']};
  const {data}=await generate({'세부유형':'gate_node'},{extensions:x});
  for(const [k,v] of Object.entries(x))assert.deepEqual(data[k],v);
 });
 await test('명칭 태그의 공백을 자동수선하지 않고 거부',()=>rejects({tags:['공백 태그']}));
 await test('잘못된 목록 자료형 거부',()=>rejects({'분야':'인물'}));
 await test('종래 키를 신규 출력에 재도입하면 거부',()=>rejects({}, {extensions:{'카테고리':'옛 폴더'}}));
 await test('임의 물리경로 필드 생성 거부',()=>rejects({}, {extensions:{'경로':'폴더/파일.md'}}));
 await test('필수 템플릿명 누락 거부',()=>rejects({'사용된 템플릿':null}));
 await test('원본 미발견 시 fallback 없이 중단',()=>rejects({}, {}, {missingSource:true}));
 await test('원본에 본문이 섞이면 거부',()=>rejects({}, {}, {source:original+'\n# 본문\n'}));
 await test('중복 YAML 키 거부',()=>rejects({}, {}, {source:original.replace('aliases: []','aliases: [] # @type=list\naliases: []')}));
 await test('기존 공개문서의 상태·날짜·주소를 건드리지 않음',async()=>{
  const content='---\n정본상태: canon\ndraft: false\n최초작성일: 2015-01-01\npermalink: /old/url\n알수없는키: 유지\n---\n# 기존 문서';
  const {tp,state}=mock({targetContent:content});await assert.rejects(renderer(tp,{values:baseValues()}));
  assert.equal(state.target,content);assert.equal(state.writes,0);
 });
 await test('프론트매터만 있는 기존문서도 거부',()=>rejects({}, {}, {targetContent:'---\ntitle: existing\n---\n'}));
 await test('공통 원본 자체 실행 거부',()=>rejects({}, {}, {targetPath:sourcePath}));
 await test('다른 활성문서를 대상으로 삼지 않음',async()=>{
  const {tp,state}=mock();tp.app.workspace={getActiveFile:()=>{throw Error('should not be called');}};
  await renderer(tp,{values:baseValues()});assert.equal(state.writes,0);
 });
 await test('생성 도중 원본 변경 감지',()=>rejects({}, {}, {changeSource:true}));
 await test('생성 도중 대상 변경 감지',()=>rejects({}, {}, {changeTarget:true}));
 await test('B루트 경로에서 연속성 누락 거부',()=>rejects({}, {}, {targetPath:'80-대체루트·비정사/01-신계 B루트/시험.md'}));
 await test('B루트 명시 시 생성 가능',async()=>assert.deepEqual((await generate({'연속성':['B루트']},{},
  {targetPath:'80-대체루트·비정사/01-신계 B루트/시험.md'})).data['연속성'],['B루트']));
 for(const title of ['이름: 부제','"따옴표" 인물','위키 [[표현]]','# 주석처럼 보이는 제목','줄\n바꿈','백슬래시\\기록']){
  await test(`특수 제목 직렬화: ${JSON.stringify(title)}`,async()=>assert.equal((await generate({}, {}, {title})).data['제목'],title));
 }
 await test('단일원본 변경이 호출부 변경 없이 출력에 반영',async()=>{
  const source=original.replace('작성자: 현카엘','작성자: 변경시험작성자').replace('cssclasses: []', '신규선택속성: null # @type=string @nullable @optional\ncssclasses: []');
  const {data}=await generate({'신규선택속성':'읽기 시험'}, {}, {source});
  assert.equal(data['작성자'],'변경시험작성자');assert.equal(data['신규선택속성'],'읽기 시험');
 });
 await test('격리시험 sourcePath 원본 하나로 작동',async()=>{
  const p='시험원본/00-yaml 속성탭.md';assert.equal((await generate({}, {sourcePath:p},{sourcePath:p})).data['스키마버전'],'2.0.0');
 });
 const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
 for(const name of ['04-인물 설정 템플릿 V2 파일럿.md','04-인물 설정 템플릿 V2 빠른 시작.md']){
  await test(`실제 배포된 호출부 실행: ${name}`,async()=>{
   const text=fs.readFileSync(path.join(root,'vault/90-볼트 운영/00-템플릿',name),'utf8');const m=text.match(/^<%\*([\s\S]*?)%>/);
   assert(m);const {tp,state}=mock();const output=await parser.parse_commands('<%*'+m[1]+'%>',tp);
   assert.equal(parsed(output)['사용된 템플릿'],name.replace(/\.md$/,''));assert.equal(state.writes,0);
  });
 }

 for (const field of ['세부유형','작성자','사용된 템플릿','템플릿 버전']) {
   await test(`공백뿐인 필수값 거부: ${field}`,()=>rejects({[field]:' \t '}));
 }
 await test('공백뿐인 제목 거부',()=>rejects({}, {}, {title:' \t '}));
 await test('저장 전 대상 편집기 본문 거부',()=>rejects({}, {}, {editorContent:'저장 전 기존 본문'}));
 await test('저장 전 대상 편집기 YAML 거부',()=>rejects({}, {}, {editorContent:'---\n제목: 기존\n---'}));
 await test('생성 중 저장 전 편집기 변경 거부',()=>rejects({}, {}, {editorContent:'',changeEditor:true}));
 await test('다른 활성 편집기는 검사 대상이 아님',async()=>{
   const {data}=await generate({}, {}, {editorContent:'다른 문서',editorPath:'다른/노트.md'});
   assert.equal(data['세부유형'],'person');
 });
 await test('공백과 BOM만 있는 새 노트 허용',async()=>{
   const {data}=await generate({}, {}, {targetContent:'\uFEFF\n ',editorContent:'\uFEFF\n '});
   assert.equal(data['문서유형'],'entity');
 });
 await test('대상 편집기 API 미확인 시 중단',async()=>{
   const {tp,state}=mock({editorContent:''});delete tp.app.workspace.activeEditor.editor.getValue;
   await assert.rejects(renderer(tp,{values:baseValues()}),/편집기/);assert.equal(state.writes,0);
 });
 for(const name of ['04-인물 설정 템플릿 V2 파일럿.md','04-인물 설정 템플릿 V2 빠른 시작.md']){
   const text=fs.readFileSync(path.join(root,'vault/90-볼트 운영/00-템플릿',name),'utf8');
   const code=text.match(/^<%\*([\s\S]*?)%>/)[1];
   await test(`생성기 누락 안내: ${name}`,async()=>{
     const {tp}=mock();tp.user={};
     await assert.rejects(parser.parse_commands('<%*'+code+'%>',tp),/User Script Folder/);
   });
   await test(`호출부 오류 시 부분 YAML 반환 안 함: ${name}`,async()=>{
     const {tp,state}=mock({missingSource:true});
     await assert.rejects(parser.parse_commands('<%*'+code+'%>',tp),/공통 원본/);
     assert.equal(state.writes,0);
   });
   await test(`완전한 생성 문서: ${name}`,async()=>{
     const {tp}=mock();
     const fm=await parser.parse_commands('<%*'+code+'%>',tp);
     const output=fm+text.slice(text.indexOf('%>')+2);
     assert(output.startsWith('---\n'));assert.equal((output.match(/^---$/gm)||[]).length,2);
     assert(!output.includes('<%'));assert(output.includes('# 개요'));
     assert.equal(parsed(fm)['템플릿 버전'],'2.0.0-rc.1');
     const examples=path.join(__dirname,'생성예시');fs.mkdirSync(examples,{recursive:true});
     fs.writeFileSync(path.join(examples,name.replace('템플릿 V2','생성예시 V2')),output);
   });
 }
 const detail=fs.readFileSync(path.join(root,'vault/90-볼트 운영/00-템플릿/04-인물 설정 템플릿 V2 파일럿.md'),'utf8');
 const buttonCode=detail.match(/```dataviewjs\n([\s\S]*?)\n```/)[1];
 function buttonHarness(fm,invalidFile=false){
   const state={writes:0,clickedFile:null};const button={},status={};
   const wrapper={createEl:tag=>tag==='button'?button:status};
   const dv={current:()=>({file:{path:'시험/표시 인물.md'}}),container:{createEl:()=>wrapper}};
   const app={vault:{getAbstractFileByPath:p=>invalidFile?null:{path:p,extension:'md'}},
     fileManager:{processFrontMatter:async(file,fn)=>{const next={...fm};fn(next);state.writes++;state.clickedFile=file.path;Object.assign(fm,next);}}};
   new Function('dv','app',buttonCode)(dv,app);return{button,status,state};
 }
 await test('수정일 버튼: 열람만으로 변경 없음',async()=>{
   const h=buttonHarness({});assert.equal(h.state.writes,0);
 });
 await test('수정일 버튼: 클릭하면 표시 문서의 수정일만 변경',async()=>{
   const fm={'제목':'시험','문서유형':'entity','세부유형':'person','정본상태':'canon','최종수정일':'old',draft:false,'문서버전':'3.0','검토상태':'reviewed'};
   const before={...fm};const h=buttonHarness(fm);await h.button.onclick();
   assert.equal(h.state.writes,1);assert.equal(h.state.clickedFile,'시험/표시 인물.md');
   assert.notEqual(fm['최종수정일'],'old');delete before['최종수정일'];
   const after={...fm};delete after['최종수정일'];assert.deepEqual(after,before);assert.equal(h.button.disabled,false);
 });
 await test('수정일 버튼: 다른 유형 및 템플릿 원본 거부',async()=>{
   for(const fm of [{'제목':'시험','문서유형':'entity','세부유형':'nation','정본상태':'draft'}, {'제목':'<% tp.file.title %>','문서유형':'entity','세부유형':'person','정본상태':'draft'}]){
     const h=buttonHarness(fm);await h.button.onclick();assert.equal(h.state.writes,0);assert.match(h.status.textContent,/갱신하지 못했습니다/);
   }
 });

 const report={time:new Date().toISOString(),environment:'Templater 2.13.1 actual WASM parser + mocked Vault/Editor/Obsidian API + PyYAML; no GUI or Quartz build',parser_sha256:crypto.createHash('sha256').update(bundle).digest('hex'),
  pass:results.filter(x=>x.result==='PASS').length,fail:results.filter(x=>x.result==='FAIL').length,results};
 fs.writeFileSync(path.join(__dirname,'Templater_실제파서_검사.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({pass:report.pass,fail:report.fail,failures:results.filter(x=>x.result==='FAIL')},null,2));
 if(report.fail)process.exitCode=1;
})();
