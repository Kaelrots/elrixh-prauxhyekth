import pathlib,json,re,collections,hashlib
BASE=pathlib.Path(__file__).parent/'small_flow_requests'
M=json.loads((BASE/'small_flow_request_manifest.json').read_text(encoding='utf-8'))
ids=set(M['allowlisted_test_ids'].values())
all_names={c:set(x['sheet_ids']) for c,x in M['files'].items()}
errors=[];formula_count=0;request_count=0
def visit(obj,current=None):
    global formula_count,request_count
    if isinstance(obj,dict):
        if 'spreadsheet_id'in obj:
            assert obj['spreadsheet_id'] in ids
            current=next(c for c,x in M['files'].items() if x['spreadsheet_id']==obj['spreadsheet_id'])
        if 'requests'in obj:
            for r in obj['requests']:
                request_count+=1
                assert len(r)==1
                if 'updateCells'in r:
                    u=r['updateCells'];g=u['range'];assert len(u['rows'])==g['endRowIndex']-g['startRowIndex']
                    assert all(len(z['values'])==g['endColumnIndex']-g['startColumnIndex'] for z in u['rows'])
                if 'deleteSheet'in r:
                    allow={s['properties']['sheetId'] for s in json.loads((BASE.parent/f'test_initial_{current}.json').read_text(encoding='utf-8'))['sheets']}
                    assert r['deleteSheet']['sheetId'] in allow
        if 'formulaValue'in obj:
            formula_count+=1;f=obj['formulaValue'];assert f.startswith('=')
            stripped=re.sub(r'"(?:[^"]|"")*"','""',f)
            depth=0
            for char in stripped:
                if char=='(':depth+=1
                elif char==')':depth-=1
                assert depth>=0,(current,f)
            assert depth==0,(current,f)
            assert '_xlfn'not in f and 'IFERROR('not in f
            for name in re.findall(r"'((?:[^']|'')+)'!",f):
                assert name.replace("''","'") in all_names[current],(current,name,f)
        for k,v in obj.items():visit(v,current)
    elif isinstance(obj,list):
        for v in obj:visit(v,current)
for p in BASE.glob('*.json'):
    if p.name in ['small_flow_request_manifest.json','local_request_validation.json']:continue
    try:visit(json.loads(p.read_text(encoding='utf-8')))
    except Exception as e:errors.append({'file':p.name,'error':str(e)})
graph=collections.defaultdict(list)
for e in M['edges']:graph[e['provider']].append(e['consumer'])
def cycle(n,trail):
    assert n not in trail
    for c in graph[n]:cycle(c,trail+[n])
for n in list(graph):cycle(n,[])
assert not any(e['consumer']=='TEST-N30' and e['provider']=='TEST-N20' for e in M['edges'])
assert not any(e['provider']=='TEST-H90' for e in M['edges'])
# Independent fixture arithmetic/interval oracle; this does not evaluate native formulas.
oracle={'initial_population':100,'changed_population':200,'zero_population':0,'empty_population':'자료없음','expanded_population':200+50,'start_included':1000101<=1000101<1010101,'end_excluded':not (1000101<=1010101<1010101),'fixture_key_counts':{'region':1,'person':1,'office':1,'term':1},'native_execution':'미실행'}
r={'scope':'local request structure, formula bracket/name checks, TEST-only targets, acyclic graph, independent fixture oracle','request_count':request_count,'formula_cell_count':formula_count,'errors':errors,'result':'pass'if not errors else'fail','native_execution_status':'미실행','oracle':oracle,'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.glob('*.json') if p.name!='local_request_validation.json'}}
(BASE/'local_request_validation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k!='files_sha256'},ensure_ascii=False))
assert not errors
