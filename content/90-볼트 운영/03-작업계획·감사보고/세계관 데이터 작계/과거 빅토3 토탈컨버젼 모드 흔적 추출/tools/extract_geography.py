from __future__ import annotations
import collections,csv,hashlib,json,math,pathlib,re,shutil,sys,zipfile,datetime
from parse_mod import Parser,Node,Typed,get,values,items,keys,plain,dictionary,hexcode

BASE=pathlib.Path(__file__).resolve().parent.parent
SRC=BASE/'source_snapshot';OUT=BASE/'rebuild'
OUT.mkdir(exist_ok=True)
TABLES={};ISSUES=[];PARSED={};TEXTS={};FILE_SUMMARY=[]

def dump(path,data):
    p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def emit(name,rows,columns=None,description=''):
    columns=columns or list(dict.fromkeys(k for row in rows for k in row))
    if not columns: columns=['key']
    dump('json/'+name+'.json',rows)
    p=OUT/'csv'/f'{name}.csv';p.parent.mkdir(exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(list,dict)) else ('true' if v is True else 'false' if v is False else v) for k,v in row.items()})
    TABLES[name]={'rows':len(rows),'description':description,'columns':[{'name':k,'types':sorted({type(r[k]).__name__ for r in rows if k in r and r[k] is not None})} for k in columns]}

def issue(kind,entity='',detail='',source_file=None,line=None):
    ISSUES.append(dict(kind=kind,entity=entity,detail=detail,source_file=source_file,line=line))

def seq(node,key):
    return [x for block in values(node,key) for x in items(block)]

def safe_hex(value,entity,field,path,line):
    h=hexcode(value)
    if value not in (None,'') and not h:issue('invalid_hex',entity,{'field':field,'value':plain(value)},path,line)
    return h

for p in sorted(SRC.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(SRC).as_posix()
    if p.suffix in ('.txt','.map','.heightmap','.info'):
        text=p.read_text(encoding='utf-8-sig');TEXTS[rel]=text;parser=Parser(text,rel);PARSED[rel]=parser.parse()
        for i in parser.issues:issue(i['kind'],'',i['detail'],rel,i['line'])
        FILE_SUMMARY.append({'source_file':rel,'top_level_entries':len(PARSED[rel].entries),'parser_issues':len(parser.issues),'empty_or_comments_only':not PARSED[rel].entries})

LOC=[];LOCBY=collections.defaultdict(list)
for p in sorted((SRC/'localization').rglob('*.yml')):
    lang=None;rel=p.relative_to(SRC).as_posix()
    for number,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
        if not line.strip() or line.lstrip().startswith('#'):continue
        m=re.fullmatch(r'\s*l_([A-Za-z_]+):\s*',line)
        if m:lang=m[1];continue
        m=re.match(r'^\s*([^\s:]+):\s*(\d*)\s*"((?:\\.|[^"\\])*)"(.*)$',line)
        if not m:
            issue('localization_unparsed_line','',line,rel,number);continue
        key,version,value,tail=m.groups();value=re.sub(r'\\(["\\])',r'\1',value)
        row={'localization_key':key,'language':lang,'version':int(version) if version else None,'value':value,'source_file':rel,'source_line':number}
        LOC.append(row);LOCBY[(key,lang)].append(row)
        if tail.strip() and not tail.lstrip().startswith('#'):issue('localization_trailing_text',key,tail,rel,number)

def resolve(key,lang,seen=None):
    seen=seen or set()
    rows=LOCBY.get((key,lang),[])
    if not rows:return None
    text=rows[-1]['value']
    if key in seen:return text
    seen=seen|{key}
    return re.sub(r'\$([^$|]+)(?:\|[^$]*)?\$',lambda m:resolve(m[1],lang,seen) or m[0],text)

LANGS=sorted({r['language'] for r in LOC if r['language']})
def names(key):
    local={lang:resolve(key,lang) for lang in LANGS if LOCBY.get((key,lang))}
    alias=key.removeprefix('STATE_').removeprefix('region_').removesuffix('_strategic_region').replace('_',' ').title()
    return {'name_english':local.get('english'),'name_korean':local.get('korean'),'name_key_derived':alias,'name_key_derived_is_official':False,'localized_names':local}

for (key,lang),rows in LOCBY.items():
    if len(rows)>1:issue('duplicate_localization_key',key,{'language':lang,'values':[r['value'] for r in rows],'sources':[f"{r['source_file']}:{r['source_line']}" for r in rows]})

STATES=[];STATE_NODES={};SP=[];HUBS=[];TRAITS=[];RESOURCES=[]
for path,node in PARSED.items():
    if not path.startswith('map_data/state_regions/'):continue
    for key,op,n,line in node.entries:
        if not key or not key.startswith('STATE_') or not isinstance(n,Node):issue('unexpected_state_entry',key,plain(n),path,line);continue
        rid=f'{key}@{path}:{line}';STATE_NODES[rid]=n
        original=seq(n,'provinces');hexes=[]
        for index,v in enumerate(original):
            h=safe_hex(v,key,'provinces',path,line)
            if h:hexes.append(h);SP.append({'state_record_id':rid,'state_id':get(n,'id'),'state_key':key,'province_hex':h,'province_token':v,'membership_order':index,'source_file':path,'source_line':line})
        unique=list(dict.fromkeys(hexes))
        duplicate_fields=[k for k,c in collections.Counter(keys(n)).items() if c>1]
        if duplicate_fields:issue('duplicate_state_field',key,{'fields':duplicate_fields,'policy':'all province blocks unioned; other scalar fields use last; raw AST preserves every occurrence'},path,line)
        if len(hexes)!=len(unique):issue('duplicate_province_within_state',key,{'repeated_hexes':[h for h,c in collections.Counter(hexes).items() if c>1]},path,line)
        row={'state_record_id':rid,'state_id':get(n,'id'),'state_key':key,**names(key),'source_file':path,'source_line':line,'is_sea_state_file':path.endswith('/99_seas.txt'),'province_hexes':unique,'province_token_count':len(original),'province_count':len(unique),'province_assignment_blocks':len(values(n,'provinces')),'traits':seq(n,'traits'),'arable_land':get(n,'arable_land'),'arable_resources':seq(n,'arable_resources'),'capped_resources':dictionary(get(n,'capped_resources')),'resource_blocks':[plain(x) for x in values(n,'resource')],'subsistence_building':get(n,'subsistence_building'),'field_presence':keys(n),'raw_fields':dictionary(n)}
        for hub in ('city','port','farm','mine','wood'):
            raw=get(n,hub);h=safe_hex(raw,key,hub,path,line);row[hub+'_hex']=h
            status='absent' if hub not in keys(n) else 'blank' if raw=='' else 'missing_value' if raw is None else 'valid_hex' if h else 'invalid'
            HUBS.append({'state_record_id':rid,'state_id':row['state_id'],'state_key':key,'hub_type':hub,'province_hex':h,'raw_value':plain(raw),'value_status':status,'in_declared_state':h in unique if h else None,'localization_key':f'HUB_NAME_{key}_{hub}',**names(f'HUB_NAME_{key}_{hub}')})
            if h and h not in unique:issue('hub_outside_declared_state',key,{'hub':hub,'hex':h},path,line)
        for t in row['traits']:TRAITS.append({'state_record_id':rid,'state_id':row['state_id'],'state_key':key,'trait_key':t})
        for t in row['arable_resources']:RESOURCES.append({'state_record_id':rid,'state_id':row['state_id'],'state_key':key,'resource_kind':'arable','resource_key':t,'amount':None,'raw_value':t})
        for block in values(n,'capped_resources'):
            if isinstance(block,Node):
                for k,o,v,l in block.entries:RESOURCES.append({'state_record_id':rid,'state_id':row['state_id'],'state_key':key,'resource_kind':'capped','resource_key':k,'amount':v if isinstance(v,(int,float)) else None,'raw_value':plain(v)})
        for v in values(n,'resource'):RESOURCES.append({'state_record_id':rid,'state_id':row['state_id'],'state_key':key,'resource_kind':'resource_block','resource_key':get(v,'type'),'amount':get(v,'undiscovered_amount'),'raw_value':plain(v)})
        STATES.append(row)
STATEBY=collections.defaultdict(list)
for s in STATES:STATEBY[s['state_key']].append(s)
for field in ('state_key','state_id'):
    counts=collections.defaultdict(list)
    for s in STATES:counts[s[field]].append(s['state_record_id'])
    for k,rs in counts.items():
        if len(rs)>1:issue('duplicate_'+field,str(k),rs)

REGIONS=[];RS=[]
for path,node in PARSED.items():
    if not path.startswith('common/strategic_regions/'):continue
    for key,op,n,line in node.entries:
        if not isinstance(n,Node):continue
        state_keys=seq(n,'states');rid=f'{key}@{path}:{line}';cap=safe_hex(get(n,'capital_province'),key,'capital_province',path,line)
        REGIONS.append({'region_record_id':rid,'region_key':key,**names(key),'capital_province_hex':cap,'map_color_raw':plain(get(n,'map_color')),'state_keys':list(dict.fromkeys(state_keys)),'state_token_count':len(state_keys),'state_count':len(set(state_keys)),'source_file':path,'source_line':line,'raw_fields':dictionary(n)})
        for index,k in enumerate(state_keys):
            matches=STATEBY.get(k,[])
            RS.append({'region_record_id':rid,'region_key':key,'state_key':k,'state_ids':[s['state_id'] for s in matches],'state_record_ids':[s['state_record_id'] for s in matches],'state_defined':bool(matches),'membership_order':index})
            if not matches:issue('region_undefined_state',key,k,path,line)
        for k,c in collections.Counter(state_keys).items():
            if c>1:issue('duplicate_state_within_region',key,{'state_key':k,'occurrences':c},path,line)
REGIONBY=collections.defaultdict(list)
for r in REGIONS:
    for k in r['state_keys']:REGIONBY[k].append(r['region_key'])
for s in STATES:
    s['strategic_region_keys']=REGIONBY[s['state_key']]
    if len(s['strategic_region_keys'])>1:issue('state_in_multiple_regions',s['state_key'],s['strategic_region_keys'])

DEFINITIONS={};COUNTRY_CULTURES=[];CULTURE_NAMES=[]
for category in ['country_definitions','cultures','religions','state_traits','discrimination_traits','terrain']:
    rows=[]
    for path,node in PARSED.items():
        if not path.startswith('common/'+category+'/'):continue
        for key,op,n,line in node.entries:
            if not key or not isinstance(n,Node):continue
            row={'identifier':key,**names(key),'source_file':path,'source_line':line,'color_raw':plain(get(n,'color')),'raw_fields':dictionary(n)}
            if category=='country_definitions':
                row.update(country_tag=key,country_type=get(n,'country_type'),tier=get(n,'tier'),capital_state_key=get(n,'capital'),culture_keys=seq(n,'cultures'),religion_key=get(n,'religion'))
                comment=TEXTS[path].splitlines()[line-1].split('#',1);row['definition_comment']=comment[1].strip() if len(comment)>1 else None
                for c in row['culture_keys']:COUNTRY_CULTURES.append({'country_tag':key,'culture_key':c})
                if row['capital_state_key'] and row['capital_state_key'] not in STATEBY:issue('country_undefined_capital_state',key,row['capital_state_key'],path,line)
            if category in ('cultures','religions'):row.update(religion_key=get(n,'religion'),traits=seq(n,'traits'))
            if category=='cultures':
                for field in keys(n):
                    if 'names' in field:
                        for index,name in enumerate(seq(n,field)):CULTURE_NAMES.append({'culture_key':key,'name_group':field,'name_token':name,'sequence':index,'localized_names':names(str(name))['localized_names']})
            rows.append(row)
    DEFINITIONS[category]=rows

for s in STATES:
    for t in s['traits']:
        if t not in {r['identifier'] for r in DEFINITIONS['state_traits']}:issue('state_trait_not_defined_in_mod',s['state_key'],t,s['source_file'],s['source_line'])
for pair in COUNTRY_CULTURES:
    if pair['culture_key'] not in {r['identifier'] for r in DEFINITIONS['cultures']}:issue('country_culture_not_defined_in_mod',pair['country_tag'],pair['culture_key'])
for c in DEFINITIONS['cultures']:
    if c['religion_key'] and c['religion_key'] not in {r['identifier'] for r in DEFINITIONS['religions']}:issue('culture_religion_not_defined_in_mod',c['identifier'],c['religion_key'])

RASTER=json.loads((BASE/'raster_cache.json').read_text());W=RASTER['width'];H=RASTER['height'];AREA=W*H
GEOBY={r['province_hex']:r for r in RASTER['provinces']}
DEFAULT=PARSED['map_data/default.map'];SEA={hexcode(v) for v in seq(DEFAULT,'sea_starts')};LAKES={hexcode(v) for v in seq(DEFAULT,'lakes')}
SEA.discard(None);LAKES.discard(None)
TERRAIN={hexcode(k):v for k,o,v,l in PARSED['map_data/province_terrains.txt'].entries if hexcode(k)}
OWNERS=collections.defaultdict(list)
for s in STATES:
    for h in s['province_hexes']:OWNERS[h].append(s)

def geometry(g):
    a=g['pixel_area']
    if not a:return {'pixel_area':0,'area_fraction':0,'centroid_x':None,'centroid_y':None,'centroid_x_norm':None,'centroid_y_norm':None,'bbox_min_x':None,'bbox_min_y':None,'bbox_max_x':None,'bbox_max_y':None,'bbox_min_x_norm':None,'bbox_min_y_norm':None,'bbox_max_x_norm':None,'bbox_max_y_norm':None,'circular_centroid_x_norm':None,'circular_resultant_x':None}
    x=g['sum_x']/a;y=g['sum_y']/a
    return {'pixel_area':a,'area_fraction':a/AREA,'centroid_x':x,'centroid_y':y,'centroid_x_norm':(x+.5)/W,'centroid_y_norm':(y+.5)/H,**{k:g[k] for k in ('bbox_min_x','bbox_min_y','bbox_max_x','bbox_max_y')},'bbox_min_x_norm':g['bbox_min_x']/W,'bbox_min_y_norm':g['bbox_min_y']/H,'bbox_max_x_norm':(g['bbox_max_x']+1)/W,'bbox_max_y_norm':(g['bbox_max_y']+1)/H,'circular_centroid_x_norm':(math.atan2(g['sum_sin_x'],g['sum_cos_x'])/(2*math.pi))%1,'circular_resultant_x':math.hypot(g['sum_cos_x'],g['sum_sin_x'])/a}

def aggregate(hexes):
    geos=[GEOBY[h] for h in set(hexes) if h in GEOBY]
    g={k:sum(r[k] for r in geos) for k in ['pixel_area','sum_x','sum_y','sum_cos_x','sum_sin_x']}
    for k in ['bbox_min_x','bbox_min_y']:g[k]=min((r[k] for r in geos),default=None)
    for k in ['bbox_max_x','bbox_max_y']:g[k]=max((r[k] for r in geos),default=None)
    return geometry(g)

REFERENCED=set(OWNERS)|SEA|LAKES|set(TERRAIN)|{h['province_hex'] for h in HUBS if h['province_hex']}|{r['capital_province_hex'] for r in REGIONS if r['capital_province_hex']}
PROVINCES=[];INVERSE={}
for h in sorted(set(GEOBY)|REFERENCED):
    g=GEOBY.get(h);owners=OWNERS.get(h,[])
    if len(owners)>1:issue('province_multiple_state_owners',h,[s['state_record_id'] for s in owners])
    status='unique' if len(owners)==1 else 'multiple' if owners else 'unassigned'
    row={'province_hex':h,'province_token':'x'+h,'hex_css':'#'+h,'rgb_r':int(h[0:2],16),'rgb_g':int(h[2:4],16),'rgb_b':int(h[4:6],16),'map_present':g is not None,'state_id':owners[0]['state_id'] if len(owners)==1 else None,'state_key':owners[0]['state_key'] if len(owners)==1 else None,'state_ids':[s['state_id'] for s in owners],'state_keys':[s['state_key'] for s in owners],'state_record_ids':[s['state_record_id'] for s in owners],'assignment_status':status,'is_sea_start':h in SEA,'is_lake':h in LAKES,'explicit_terrain':TERRAIN.get(h),'water_class':'sea_start_and_lake' if h in SEA&LAKES else 'sea_start' if h in SEA else 'lake' if h in LAKES else 'unspecified',**geometry(g or {'pixel_area':0})}
    for k in ('representative_x','representative_y','touches_left_edge','touches_right_edge','touches_top_edge','touches_bottom_edge'):row[k]=g[k] if g else None
    row['touches_both_x_edges']=bool(g and g['touches_left_edge'] and g['touches_right_edge'])
    PROVINCES.append(row);INVERSE[h]={'state_ids':row['state_ids'],'state_keys':row['state_keys'],'state_record_ids':row['state_record_ids'],'map_present':row['map_present'],'assignment_status':status}
    if not g:issue('referenced_hex_missing_from_map',h,{'state_keys':row['state_keys'],'sea_start':h in SEA,'lake':h in LAKES})

PROVBY={p['province_hex']:p for p in PROVINCES}
for s in STATES:
    missing=[h for h in s['province_hexes'] if h not in GEOBY];present=[h for h in s['province_hexes'] if h in GEOBY]
    s.update(aggregate(s['province_hexes']));s.update(present_province_count=len(present),missing_province_hexes=missing,missing_province_count=len(missing),geometry_status='empty_definition' if not s['province_count'] else 'no_mapped_provinces' if not present else 'partial' if missing else 'complete',has_ambiguous_province_ownership=any(len(OWNERS[h])>1 for h in s['province_hexes']),state_color_hex=None)
for h in HUBS:
    p=PROVBY.get(h['province_hex']);h.update(map_present=bool(p and p['map_present']),centroid_x=p['centroid_x'] if p else None,centroid_y=p['centroid_y'] if p else None,centroid_x_norm=p['centroid_x_norm'] if p else None,centroid_y_norm=p['centroid_y_norm'] if p else None,actual_state_keys=p['state_keys'] if p else [])
for r in REGIONS:
    members=[s for k in r['state_keys'] for s in STATEBY.get(k,[])];hs={h for s in members for h in s['province_hexes']}
    r.update(aggregate(hs));r.update(defined_state_count=len(members),missing_state_keys=[k for k in r['state_keys'] if k not in STATEBY],province_count=len(hs),capital_on_map=r['capital_province_hex'] in GEOBY,capital_in_declared_region=r['capital_province_hex'] in hs if r['capital_province_hex'] else None)
    if r['capital_province_hex'] and r['capital_province_hex'] not in hs:issue('region_capital_outside_declared_region',r['region_key'],r['capital_province_hex'],r['source_file'],r['source_line'])

# Supplemental relations are explicitly geometric, not game pathfinding rules.
STATE_EDGES=collections.Counter();STATE_SEAMS=collections.Counter();ambiguous_edge_count=0
for edge in RASTER['adjacency']:
    a=OWNERS.get(edge['province_hex_a'],[]);b=OWNERS.get(edge['province_hex_b'],[])
    if len(a)==1 and len(b)==1 and a[0]['state_record_id']!=b[0]['state_record_id']:
        pair=tuple(sorted([a[0]['state_record_id'],b[0]['state_record_id']]))
        STATE_EDGES[pair]+=edge['shared_pixel_edges'];STATE_SEAMS[pair]+=edge['seam_pixel_edges']
    elif len(a)>1 or len(b)>1:ambiguous_edge_count+=1
STATE_RECORD_BY={s['state_record_id']:s for s in STATES}
STATE_ADJ=[{'state_record_id_a':a,'state_key_a':STATE_RECORD_BY[a]['state_key'],'state_id_a':STATE_RECORD_BY[a]['state_id'],'state_record_id_b':b,'state_key_b':STATE_RECORD_BY[b]['state_key'],'state_id_b':STATE_RECORD_BY[b]['state_id'],'shared_pixel_edges':n,'seam_pixel_edges':STATE_SEAMS[(a,b)]} for (a,b),n in sorted(STATE_EDGES.items())]

# Geographical identifiers referenced anywhere in the retained text definitions.
REFERENCES=[]
def walk_reference(v,path,trail,line):
    if isinstance(v,Node):
        for k,o,val,l in v.entries:
            if k:walk_reference(k,path,trail+['<key>'],l)
            walk_reference(val,path,trail+[k if k is not None else '[]'],l)
    elif isinstance(v,Typed):walk_reference(v.value,path,trail+[v.kind],line)
    elif isinstance(v,str):
        kind=None;ident=None
        if v.startswith('STATE_'):kind='state';ident=v
        elif re.fullmatch(r's:STATE_\w+',v):kind='state';ident=v[2:]
        elif re.fullmatch(r'c:[A-Z0-9]{3}',v):kind='country';ident=v[2:]
        elif v.startswith('cu:'):kind='culture';ident=v[3:]
        elif v.startswith('religion:'):kind='religion';ident=v[9:]
        if kind:REFERENCES.append({'source_file':path,'source_line':line,'field_path':'/'.join(trail),'identifier_type':kind,'identifier':ident,'raw_token':v})
for path,node in PARSED.items():
    if not path.startswith('map_data/state_regions/'):walk_reference(node,path,[],1)

GEO_LOC=[];LOC_ORPHANS=[]
statekeys=set(STATEBY);regionkeys={r['region_key'] for r in REGIONS};identifierkeys={r['identifier'] for rows in DEFINITIONS.values() for r in rows}
for r in LOC:
    key=r['localization_key'];kind='state' if key.startswith('STATE_') else 'hub' if key.startswith('HUB_NAME_') else 'strategic_region' if key.startswith('region_') else 'identifier' if key in identifierkeys else None
    if kind:
        linked=key in statekeys or key in regionkeys or key in identifierkeys
        statekey=None
        m=re.fullmatch(r'HUB_NAME_(STATE_.+)_(city|port|farm|mine|wood)',key)
        if m:statekey=m[1];linked=statekey in statekeys
        row={**r,'entity_type':kind,'matched_definition':linked,'state_key':statekey,'resolved_value':resolve(key,r['language'])}
        GEO_LOC.append(row)
        if not linked:LOC_ORPHANS.append(row)

INVENTORY=json.loads((BASE/'tools'/'drive_inventory.json').read_text());SOURCES=[]
if (BASE/'tools'/'extra_inventory.json').exists():INVENTORY+=json.loads((BASE/'tools'/'extra_inventory.json').read_text())
for f in INVENTORY:
    p=SRC/f['path'];present=p.is_file()
    SOURCES.append({'source_file':f['path'],'drive_file_id':f['id'],'drive_url':f['url'],'mime_type':f['mime_type'],'drive_size_bytes':int(f['size']) if f['size'] else None,'modified_time':f.get('modified_time'),'downloaded':present,'local_size_bytes':p.stat().st_size if present else None,'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if present else None,'exclusion_reason':None if present else 'compiled or derived map cache; no decoded geography added'})
for f in SOURCES:
    if f['downloaded'] and f['drive_size_bytes']!=f['local_size_bytes']:raise AssertionError('Download size mismatch '+f['source_file'])

FOLDERS=[]
for f in json.loads((BASE/'tools'/'folder_inventory.json').read_text()):FOLDERS.append({'folder':f['path'],'direct_child_count':len(f['data']['files']),'is_empty':not f['data']['files']})
ISSUE_COUNTS=dict(sorted(collections.Counter(i['kind'] for i in ISSUES).items()))
STATS={'source_folder_title':'New World - Rarixhenverk','source_folder_url':'https://drive.google.com/drive/folders/1H4lrdrfa74Y3p7SxOrEyg3E0CUMcOS01','extracted_date_kst':'2026-10-02','source_files_downloaded':sum(s['downloaded'] for s in SOURCES),'state_region_files':sum(p.startswith('map_data/state_regions/') for p in PARSED),'state_records':len(STATES),'unique_state_keys':len(STATEBY),'unique_state_numeric_ids':len({s['state_id'] for s in STATES}),'map_width':W,'map_height':H,'map_total_pixels':AREA,'map_distinct_colors':len(GEOBY),'province_records_including_missing_references':len(PROVINCES),'declared_province_unique_hexes':len(OWNERS),'unassigned_map_colors':sum(p['map_present'] and not p['state_keys'] for p in PROVINCES),'ambiguous_province_hexes':sum(len(p['state_keys'])>1 for p in PROVINCES),'declared_hexes_missing_from_map':sum(h not in GEOBY for h in OWNERS),'all_referenced_hexes_missing_from_map':sum(not p['map_present'] for p in PROVINCES),'state_geometry_status_counts':dict(collections.Counter(s['geometry_status'] for s in STATES)),'strategic_regions':len(REGIONS),'empty_strategic_regions':sum(not r['state_keys'] for r in REGIONS),'states_without_strategic_region':sum(not s['strategic_region_keys'] for s in STATES),'countries':len(DEFINITIONS['country_definitions']),'cultures':len(DEFINITIONS['cultures']),'religions':len(DEFINITIONS['religions']),'state_trait_definitions':len(DEFINITIONS['state_traits']),'localization_languages':LANGS,'localization_entries':len(LOC),'state_korean_names':sum(bool(s['name_korean']) for s in STATES),'state_english_names':sum(bool(s['name_english']) for s in STATES),'province_adjacency_pairs':len(RASTER['adjacency']),'state_adjacency_pairs':len(STATE_ADJ),'state_adjacency_omitted_ambiguous_province_pairs':ambiguous_edge_count,'issue_counts':ISSUE_COUNTS}

emit('states',STATES,description='모든 state 정의, 명칭, province 목록, 허브, 특성·자원 및 픽셀 가중 집계. 기본 테이블.')
emit('provinces',PROVINCES,description='지도 전체 고유 RGB와 모든 참조 HEX의 합집합. 위치·영역·state 역매핑·수역 명시값.')
emit('province_state_memberships',SP,description='원문 province 토큰별 state 관계. 반복과 순서 보존; 면적 집계 시에는 중복 제거.')
inverse_rows=[{'province_hex':h,**v} for h,v in INVERSE.items()]
emit('province_to_states',inverse_rows,description='HEX별 state 역매핑. 복수 소속을 배열로 보존; state가 없으면 빈 배열.')
dump('json/province_to_states_lookup.json',INVERSE)
emit('state_hubs',HUBS,description='모든 state × city/port/farm/mine/wood. 미지정·빈 문자열·HEX 구분 및 허브 명칭과 위치.')
emit('state_traits_memberships',TRAITS,description='state와 trait 식별자의 관계.')
emit('state_resources',RESOURCES,description='경작 가능 자원과 capped/resource 자원 블록. 경작지 총량은 states.arable_land.')
emit('strategic_regions',REGIONS,description='전략지역, 명칭, 수도 province, 원본 map_color, state 목록 및 합집합 지리.')
emit('strategic_region_states',RS,description='전략지역의 원문 state 관계. 반복·미정의 state도 보존.')
emit('province_adjacency',RASTER['adjacency'],description='4방향 픽셀 변 공유 관계. wrap_x=yes에 따라 좌우 경계 연결 포함. 게임 이동 가능성 아님.')
emit('state_adjacency',STATE_ADJ,description='양쪽 province의 state가 각각 유일할 때만 집계한 state 공유 경계.')
SUP=json.loads((BASE/'raster_supplements.json').read_text())
emit('province_height_raw',SUP['height_provinces'],description='각 province에 겹치는 16-bit 원본 높이맵 샘플의 수·합·최소·최대·평균. 미터 단위 아님.')
HEIGHTBY={r['province_hex']:r for r in SUP['height_provinces']};STATE_HEIGHT=[]
for s in STATES:
    hr=[HEIGHTBY[h] for h in set(s['province_hexes']) if h in HEIGHTBY];count=sum(r['height_sample_count'] for r in hr);total=sum(r['height_raw_sum'] for r in hr)
    STATE_HEIGHT.append({'state_record_id':s['state_record_id'],'state_id':s['state_id'],'state_key':s['state_key'],'height_sample_count':count,'height_raw_sum':total,'height_raw_min':min((r['height_raw_min'] for r in hr),default=None),'height_raw_max':max((r['height_raw_max'] for r in hr),default=None),'height_raw_mean':total/count if count else None})
emit('state_height_raw',STATE_HEIGHT,description='state province 합집합의 16-bit 높이맵 원시 통계. 빈 state는 평균·최소·최대 null.')
emit('province_river_palette_counts',SUP['river_province_palette_counts'],description='province별 rivers.png 팔레트 인덱스 픽셀 수. 인덱스 의미는 추정하지 않음.')
emit('river_palette',SUP['river_palette'],description='강 지도에서 실제 사용한 인덱스와 RGB, 전체 픽셀 수.')
dump('raster_supplement_metadata.json',{k:v for k,v in SUP.items() if k not in ('height_provinces','river_province_palette_counts','river_palette')})
OBJECTS=[];OBJECT_GROUPS=[]
for path,node in PARSED.items():
    if not path.startswith('gfx/map/map_object_data/'):continue
    for key,op,n,line in node.entries:
        if not isinstance(n,Node):continue
        inst=seq(n,'instances')
        OBJECT_GROUPS.append({'source_file':path,'source_line':line,'object_type':key,'name':get(n,'name'),'entity':get(n,'entity'),'layer':get(n,'layer'),'declared_count':get(n,'count'),'instance_count':len(inst),'raw_fields':dictionary(n)})
        for index,obj in enumerate(inst):
            pos=items(get(obj,'position'));iid=get(obj,'id')
            OBJECTS.append({'source_file':path,'object_type':key,'object_name':get(n,'name'),'instance_index':index,'instance_id':iid,'position_raw':pos,'x_raw':pos[0] if len(pos)>0 else None,'y_raw':pos[1] if len(pos)>1 else None,'z_raw':pos[2] if len(pos)>2 else None,'rotation_raw':plain(get(obj,'rotation')),'scale_raw':plain(get(obj,'scale')),'state_keys_with_same_numeric_id':[s['state_key'] for s in STATES if s['state_id']==iid] if key=='game_object_locator' else [],'state_match_status':'numeric_id_only_unverified' if key=='game_object_locator' else 'not_joined','raw_fields':dictionary(obj)})
emit('map_object_instances',OBJECTS,description='원본 지도 객체/허브 배치 좌표. 게임의 x/y/z 원본 좌표이며 PNG 좌표 변환·state 연결은 확정하지 않음.')
emit('map_object_groups',OBJECT_GROUPS,description='선택한 지도 객체 그룹과 인스턴스 수. 자동 생성 식생 배치 폴더는 제외.')
EDITOR=[]
editor=get(PARSED.get('tools/mapeditor/map_editor_status.txt'),'map_content_editor') if 'tools/mapeditor/map_editor_status.txt' in PARSED else None
if isinstance(editor,Node):
    for category,op,n,line in editor.entries:
        complete=get(n,'completed')
        if not isinstance(complete,Node):continue
        for ident,o,status,l in complete.entries:
            h=f'{int(ident):06X}' if category=='0' and ident and ident.isdigit() and 0<=int(ident)<1<<24 else None
            statekey=ident if category=='1' and ident in STATEBY else None
            EDITOR.append({'editor_category':category,'raw_identifier':ident,'completed_raw':status,'province_hex_candidate':h,'province_hex_on_map':h in GEOBY if h else None,'state_key_candidate':statekey,'state_record_ids':[s['state_record_id'] for s in STATEBY.get(statekey,[])],'interpretation':'decimal_RGB_candidate_inferred_from_exact_map_matches' if category=='0' else 'opaque_identifier_no_verified_state_mapping','source_line':l})
emit('map_editor_completion',EDITOR,description='편집기 완료 표시 원문. category 0의 숫자→RGB HEX는 값의 일치로 추론. category 1 숫자는 state 연결 미확인. 게임 활성 여부나 완성도 보증 아님.')
for category,rows in DEFINITIONS.items():emit(category,rows,description=category+' 식별자, 로컬라이즈 이름과 모든 원본 필드.')
emit('country_cultures',COUNTRY_CULTURES,description='국가와 주 문화 식별자의 관계. 영토 소유권 아님.')
emit('culture_name_tokens',CULTURE_NAMES,description='문화 정의의 인명·성명 토큰과 순서.')
emit('geographic_identifier_references',REFERENCES,description='보존한 스크립트의 state/country/culture 식별자 참조와 원문 위치.')
emit('localization_all',LOC,description='모든 확보한 localization 문장. 중복 키와 원문 파일·줄 보존.')
emit('localization_geography',GEO_LOC,description='state·hub·region 및 식별자 명칭, 정의 매칭과 정적 별칭 해석.')
emit('localization_unmatched_geography',LOC_ORPHANS,description='명칭은 있으나 확보한 정의와 연결되지 않은 지명.')
emit('province_terrain_overrides',[{'province_hex':h,'terrain_key':t} for h,t in TERRAIN.items()],description='province_terrains.txt의 명시적인 지형만 추출; 다른 지역의 지형은 추정하지 않음.')
emit('map_settings',[{'key':k,'value':plain(v),'source_line':l} for k,o,v,l in DEFAULT.entries],description='default.map 설정. sea_starts/lakes 원문 토큰 및 wrap_x.')
with (SRC/'map_data/adjacencies.csv').open(encoding='utf-8-sig',newline='') as f:
    reader=csv.DictReader(f,delimiter=';');adj=list(reader);columns=reader.fieldnames
emit('special_adjacencies',adj,columns=columns,description='원본 특수 이동 연결. 이번 원본은 헤더만 있고 데이터 행 없음.')
emit('validation_issues',ISSUES,description='원본 결손·중복·참조 오류. 자동 수정하지 않음.')
emit('empty_or_unmapped_states',[{k:s[k] for k in ['state_record_id','state_id','state_key','name_korean','province_count','present_province_count','missing_province_count','geometry_status','source_file','source_line']} for s in STATES if s['geometry_status']!='complete'],description='빈 state, 지도에서 전혀 찾지 못한 state, 부분적으로만 찾은 state.')
emit('source_files',SOURCES,description='Drive 출처, 수정 시각, 다운로드 길이와 SHA-256.')
emit('inspected_history_and_localization_folders',FOLDERS,description='하위 폴더 직접 조회 결과. history/states,pops,buildings 등의 빈 상태 증거.')
emit('parsed_file_summary',FILE_SUMMARY,description='텍스트 정의 파일별 추출 개수와 빈 파일 상태.')
emit('extraction_summary',[{'metric':k,'value':v} for k,v in STATS.items()],description='전체 개수와 검증 통계.')
dump('validation_report.json',STATS)
dump('schema.json',{'schema_version':'1.0.0','tables':TABLES,'json_encoding':'UTF-8','csv_encoding':'UTF-8 BOM','csv_arrays_objects':'JSON inside a CSV cell','nulls':'JSON null; CSV empty cell','hex_format':'6 uppercase digits without prefix; always read as string','state_record_id':'state_key@relative_source_file:source_line; protects duplicate keys/IDs','raw_ast_format':'ordered assignments with key, operator, value, source line; bare-list values retained as arrays; typed rgb/hsv objects retained','coordinates':{'origin':'top left','x':'rightward, zero based pixel index','y':'downward, zero based pixel index','centroid':'mean pixel indexes, weighted by pixel counts','centroid_norm':'(centroid_x+0.5)/width and (centroid_y+0.5)/height','bbox':'integer pixel indexes, max inclusive','bbox_norm':'min/size and (max+1)/size; edges of occupied pixel cells','area':'count of pixels; not square kilometres','circular_centroid_x_norm':'circular mean of 2*pi*(x+0.5)/width; diagnostic for horizontal wrap; low resultant = unstable','circular_resultant_x':'magnitude of circular mean, from 0 to 1'}})
dump('raw/parsed_text_files.json',[{'source_file':p,'data':plain(n)} for p,n in PARSED.items()])
for p in SRC.rglob('*'):
    if p.is_file():
        dest=OUT/'source_snapshot'/p.relative_to(SRC);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)

print(json.dumps(STATS,ensure_ascii=False,indent=2))
