// 통합 배포 트리에서 모든 시작형을 실제 Templater WASM 파서로 생성한다.
// Vault·편집기·YAML은 모의 환경이며 실볼트를 수정하지 않는다.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto'),{execFileSync}=require('child_process');
const root=path.resolve(__dirname,'..'),vaultRoot=path.join(root,'vault');
const entries=JSON.parse(fs.readFileSync(path.join(__dirname,'시작형 목록.json'),'utf8'));
const manifest=JSON.parse(fs.readFileSync(path.join(root,'승격대상_매니페스트.json'),'utf8'));
const files=new Map();for(const item of manifest.files){const p=item.path.slice('vault/'.length);files.set(p,fs.readFileSync(path.join(vaultRoot,p),'utf8'));}
const user={};for(const [name] of files)if(name.endsWith('.js'))user[path.basename(name,'.js')]=require(path.join(vaultRoot,name));
const yamlCode=String.raw`
import sys,json,yaml
from yaml.constructor import ConstructorError
class Strict(yaml.SafeLoader):pass
def mapping(loader,node,deep=False):
    out={}
    for k,v in node.value:
        key=loader.construct_object(k,deep=deep)
        if key in out:raise ConstructorError('mapping',node.start_mark,'duplicate key '+str(key),k.start_mark)
        out[key]=loader.construct_object(v,deep=deep)
    return out
Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
raw=sys.stdin.read()
if sys.argv[1]=='load':print(json.dumps(yaml.load(raw,Loader=Strict),ensure_ascii=False))
else:print(yaml.safe_dump(json.loads(raw),allow_unicode=True,sort_keys=False),end='')
`;
const load=s=>JSON.parse(execFileSync('python',['-c',yamlCode,'load'],{input:s,encoding:'utf8'}));
const dump=x=>execFileSync('python',['-c',yamlCode,'dump'],{input:JSON.stringify(x),encoding:'utf8'});
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
(async()=>{
 const bundle=fs.readFileSync(process.env.TEMPLATER_BUNDLE,'utf8'),a=bundle.indexOf('var Vs={},N,He='),b=bundle.indexOf('var Xe;',a);assert(a>=0&&b>a);
 const Parser=new Function('Ui',bundle.slice(a,b)+';return vi;')(s=>new Uint8Array(Buffer.from(s,'base64')));const parser=new Parser();await parser.init();
 const results=[];
 for(const entry of entries){
   try{
     const target={path:'통합 시험/'+path.basename(entry.path),extension:'md',basename:'통합 시험: "문서"'};let writes=0;
     const file=p=>({path:p,extension:path.extname(p).slice(1),basename:path.basename(p,'.md')});
     const app={vault:{getAbstractFileByPath:p=>files.has(p)?file(p):null,read:async f=>f.path===target.path?'':files.get(f.path),modify:()=>{writes++;throw Error('쓰기 금지');},create:()=>{writes++;throw Error('쓰기 금지');}}};
     const tp={app,config:{target_file:target,template_file:file(entry.path)},file:{title:target.basename,include:async f=>parser.parse_commands(files.get(f.path),tp)},date:{now:()=> '2026-10-03T00:00:00'},obsidian:{parseYaml:load,stringifyYaml:dump},user};
     const output=await parser.parse_commands(files.get(entry.path),tp),m=output.match(/^---\n([\s\S]*?)\n---\n/);assert(m,'YAML 헤더');
     const fm=load(m[1]);assert.equal(fm['제목'],target.basename);assert.equal(fm['스키마버전'],'2.0.0');assert.equal(fm['템플릿 버전'],'2.0.0-rc.1');assert.equal(fm.draft,true);
     for(const [key,value] of Object.entries(entry.metadata))assert.deepEqual(fm[key],value);
     for(const [key,value] of Object.entries(entry.extensions||{}))assert.deepEqual(fm[key],value);
     if(fm['세부유형']==='gate_node')assert.deepEqual(fm.prereq,{hard:[],soft:[]});
     assert(!output.includes('<%'));assert.equal(writes,0);assert.equal((output.match(/^---$/gm)||[]).length,2);
     const dest=path.join(__dirname,'생성예시',String(entry.stage).padStart(2,'0'),path.basename(entry.path));fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,output);
     results.push({stage:entry.stage,file:entry.path,result:'PASS',lines:output.split('\n').length,sha256:hash(output)});
   }catch(e){results.push({stage:entry.stage,file:entry.path,result:'FAIL',error:e.stack});}
 }
 for(const item of manifest.files)assert.equal(hash(fs.readFileSync(path.join(root,item.path))),item.sha256,'배포 파일 불변 '+item.path);
 const report={time:new Date().toISOString(),environment:'Actual Templater 2.13.1 WASM + mock Vault/YAML, combined deployment tree',parser_sha256:hash(bundle),pass:results.filter(x=>x.result==='PASS').length,fail:results.filter(x=>x.result==='FAIL').length,results};
 fs.writeFileSync(path.join(__dirname,'통합 생성 검사.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({pass:report.pass,fail:report.fail,failures:results.filter(x=>x.result==='FAIL')},null,2));if(report.fail)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
