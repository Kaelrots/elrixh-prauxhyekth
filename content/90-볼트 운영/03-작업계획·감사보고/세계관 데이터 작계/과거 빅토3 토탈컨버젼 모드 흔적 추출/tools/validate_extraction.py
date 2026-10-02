import csv,hashlib,json,pathlib,random,re,math,collections
import numpy as np
from PIL import Image
BASE=pathlib.Path(__file__).resolve().parent.parent;OUT=BASE/'rebuild';checks=[]
def read(name):return json.loads((OUT/'json'/f'{name}.json').read_text(encoding='utf-8'))
def check(name,condition,detail=None):
    if not condition:raise AssertionError(name+': '+str(detail))
    checks.append({'check':name,'passed':True,'detail':detail})
states=read('states');provinces=read('provinces');prov={p['province_hex']:p for p in provinces};W=8192;H=3616
arr=np.asarray(Image.open(BASE/'source_snapshot/map_data/provinces.png'),dtype=np.uint32)
codes=(arr[:,:,0]<<16)|(arr[:,:,1]<<8)|arr[:,:,2];del arr
u,c=np.unique(codes,return_counts=True)
check('all_44522_RGB_counts_match_independent_numpy_unique',all(prov[f'{int(h):06X}']['pixel_area']==int(n) for h,n in zip(u,c)),len(u))
check('all_pixels_accounted_for',sum(p['pixel_area'] for p in provinces)==W*H,W*H)
check('global_x_moment',math.isclose(sum(p['centroid_x']*p['pixel_area'] for p in provinces if p['map_present']),H*W*(W-1)/2,abs_tol=.01))
check('global_y_moment',math.isclose(sum(p['centroid_y']*p['pixel_area'] for p in provinces if p['map_present']),W*H*(H-1)/2,abs_tol=.01))
sample=sorted([p for p in provinces if p['map_present']],key=lambda p:p['pixel_area'],reverse=True)[:3]
sample+=random.Random(1836).sample([p for p in provinces if p['map_present']],12)
sample+=[p for p in provinces if p['touches_both_x_edges']][:3]
for p in sample:
    yy,xx=np.nonzero(codes==int(p['province_hex'],16))
    check('province_direct_pixel_coordinates_'+p['province_hex'],int(xx.min())==p['bbox_min_x'] and int(xx.max())==p['bbox_max_x'] and int(yy.min())==p['bbox_min_y'] and int(yy.max())==p['bbox_max_y'] and math.isclose(float(xx.mean()),p['centroid_x'],abs_tol=1e-10) and math.isclose(float(yy.mean()),p['centroid_y'],abs_tol=1e-10))
    check('representative_pixel_'+p['province_hex'],int(codes[p['representative_y'],p['representative_x']])==int(p['province_hex'],16))
state_sample=sorted([s for s in states if s['pixel_area']],key=lambda s:s['pixel_area'],reverse=True)[:2]+random.Random(2026).sample([s for s in states if s['pixel_area']],8)
state_sample += [s for s in states if s['province_assignment_blocks']>1 or s['geometry_status']=='partial']
for s in state_sample:
    mask=np.isin(codes,np.array([int(h,16) for h in s['province_hexes']],dtype=np.uint32));yy,xx=np.nonzero(mask)
    check('state_direct_pixel_union_'+s['state_record_id'],len(xx)==s['pixel_area'] and xx.min()==s['bbox_min_x'] and xx.max()==s['bbox_max_x'] and yy.min()==s['bbox_min_y'] and yy.max()==s['bbox_max_y'] and math.isclose(xx.mean(),s['centroid_x'],abs_tol=1e-10) and math.isclose(yy.mean(),s['centroid_y'],abs_tol=1e-10))
check('all_state_areas_match_unique_province_union',all(s['pixel_area']==sum(prov[h]['pixel_area'] for h in set(s['province_hexes'])) for s in states))
check('empty_state_coordinates_are_null',all(s['centroid_x'] is None and s['bbox_min_x'] is None and s['pixel_area']==0 for s in states if s['geometry_status']=='empty_definition'))
check('normalization_inside_unit_square',all(0<=p['centroid_x_norm']<1 and 0<=p['centroid_y_norm']<1 and 0<=p['bbox_min_x_norm']<p['bbox_max_x_norm']<=1 and 0<=p['bbox_min_y_norm']<p['bbox_max_y_norm']<=1 for p in provinces if p['map_present']))
rawstate='\n'.join(re.sub(r'#[^\n]*','',p.read_text(encoding='utf-8-sig')) for p in (BASE/'source_snapshot/map_data/state_regions').glob('*.txt'))
check('state_definitions_match_independent_regex',len(re.findall(r'(?m)^\s*STATE_\w+\s*=\s*\{',rawstate))==len(states),len(states))
check('state_numeric_ids_match_independent_regex',len(re.findall(r'\bid\s*=\s*\d+',rawstate))==len(states))
hex_count=len(re.findall(r'"[xX][0-9a-fA-F]{6}"',rawstate))
check('all_original_state_HEX_tokens_retained',hex_count==len(read('province_state_memberships'))+sum(h['province_hex'] is not None for h in read('state_hubs')),hex_count)
members=read('province_state_memberships');inv={r['province_hex']:r for r in read('province_to_states')}
check('forward_reverse_memberships_agree',all(m['state_record_id'] in inv[m['province_hex']]['state_record_ids'] for m in members))
schema=json.loads((OUT/'schema.json').read_text(encoding='utf-8'))
for name,info in schema['tables'].items():
    j=read(name)
    with (OUT/'csv'/f'{name}.csv').open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);rows=list(reader)
    check('csv_json_row_parity_'+name,len(rows)==len(j)==info['rows'])
    check('csv_header_'+name,reader.fieldnames==[c['name'] for c in info['columns']])
    for jr,cr in zip(j,rows):
        for key,value in jr.items():
            if isinstance(value,(dict,list)):assert json.loads(cr[key])==value,(name,key)
check('all_nested_csv_JSON_roundtrips',True)
for source in read('source_files'):
    if not source['downloaded']:continue
    p=OUT/'source_snapshot'/source['source_file']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==source['sha256']
check('all_source_snapshot_hashes_match_downloads',True)
edges=read('province_adjacency')
edge_sum=sum(e['shared_pixel_edges'] for e in edges)
direct=int(np.count_nonzero(codes[:,1:]!=codes[:,:-1])+np.count_nonzero(codes[1:]!=codes[:-1])+np.count_nonzero(codes[:,0]!=codes[:,-1]))
check('adjacency_shared_edges_conservation',edge_sum==direct,{'exported':edge_sum,'direct':direct})
Image.MAX_IMAGE_PIXELS=None
height=Image.open(BASE/'source_snapshot/map_data/heightmap.png');heightrows=read('province_height_raw');hb={r['province_hex']:r for r in heightrows}
check('height_counts_match_2x2_alignment',all(r['height_sample_count']==prov[r['province_hex']]['pixel_area']*4 for r in heightrows))
check('all_height_samples_accounted',sum(r['height_sample_count'] for r in heightrows)==height.width*height.height)
check('height_raw_sum_conservation',sum(r['height_raw_sum'] for r in heightrows)==int(np.asarray(height).sum(dtype=np.uint64)))
for p in random.Random(733).sample([p for p in provinces if p['map_present'] and p['pixel_area']<100000],5):
    x0,y0,x1,y1=(p[k] for k in ['bbox_min_x','bbox_min_y','bbox_max_x','bbox_max_y'])
    sub=codes[y0:y1+1,x0:x1+1]==int(p['province_hex'],16)
    raw=np.asarray(height.crop((x0*2,y0*2,(x1+1)*2,(y1+1)*2)))
    samples=raw[np.repeat(np.repeat(sub,2,axis=0),2,axis=1)];r=hb[p['province_hex']]
    check('height_direct_samples_'+p['province_hex'],len(samples)==r['height_sample_count'] and int(samples.min())==r['height_raw_min'] and int(samples.max())==r['height_raw_max'] and int(samples.sum())==r['height_raw_sum'])
rivercounts=collections.Counter()
for r in read('province_river_palette_counts'):rivercounts[r['province_hex']]+=r['pixel_count']
check('all_river_palette_counts_cover_each_province',all(rivercounts[p['province_hex']]==p['pixel_area'] for p in provinces if p['map_present']))
check('map_editor_records_count',len(read('map_editor_completion'))==46786)
check('hub_locator_instances_count',sum(r['object_type']=='game_object_locator' for r in read('map_object_instances'))==5)
result={'passed':True,'check_count':len(checks),'checks':checks,'note':'These checks validate extraction fidelity, not game validity of the original mod.'}
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':True,'check_count':len(checks),'province_samples':len(sample),'state_samples':len(state_sample)},ensure_ascii=False))
