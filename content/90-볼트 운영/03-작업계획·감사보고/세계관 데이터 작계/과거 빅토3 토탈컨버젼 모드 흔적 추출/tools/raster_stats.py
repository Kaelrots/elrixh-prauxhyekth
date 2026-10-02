"""Exact, unresampled RGB geography and four-neighbour raster adjacency."""
import json, pathlib, collections
import numpy as np
from PIL import Image

def compute(source,cache):
    image=Image.open(source)
    if image.mode!='RGB': image=image.convert('RGB')
    rgb=np.asarray(image,dtype=np.uint32);h,w=rgb.shape[:2]
    codes=(rgb[:,:,0]<<16)|(rgb[:,:,1]<<8)|rgb[:,:,2];del rgb
    colors,counts=np.unique(codes,return_counts=True);n=len(colors)
    lookup=np.full(1<<24,-1,dtype=np.int32);lookup[colors]=np.arange(n)
    labels=lookup[codes];del lookup,codes
    sx=np.zeros(n,dtype=np.int64);sy=sx.copy();minx=np.full(n,w,dtype=np.int32);maxx=np.full(n,-1,dtype=np.int32);miny=np.full(n,h,dtype=np.int32);maxy=np.full(n,-1,dtype=np.int32)
    cos=np.zeros(n);sin=np.zeros(n);angles=2*np.pi*(np.arange(w)+.5)/w
    pc=np.r_[0,np.cumsum(np.cos(angles))];ps=np.r_[0,np.cumsum(np.sin(angles))]
    firstx=np.full(n,-1,dtype=np.int32);firsty=firstx.copy()
    for y,row in enumerate(labels):
        starts=np.r_[0,np.flatnonzero(row[1:]!=row[:-1])+1];ends=np.r_[starts[1:],w];ids=row[starts];sizes=ends-starts
        np.add.at(sx,ids,(starts+ends-1)*sizes//2);np.add.at(sy,ids,sizes*y)
        np.minimum.at(minx,ids,starts);np.maximum.at(maxx,ids,ends-1);np.minimum.at(miny,ids,y);np.maximum.at(maxy,ids,y)
        np.add.at(cos,ids,pc[ends]-pc[starts]);np.add.at(sin,ids,ps[ends]-ps[starts])
        unique,idx=np.unique(ids,return_index=True);new=firsty[unique]<0;u=unique[new];firsty[u]=y;firstx[u]=starts[idx[new]]
    edges=collections.Counter();seams=collections.Counter()
    def add(a,b,target):
        changed=a!=b;a=a[changed].astype(np.int64);b=b[changed].astype(np.int64)
        p=np.minimum(a,b)*n+np.maximum(a,b);pairs,c=np.unique(p,return_counts=True)
        target.update({int(k):int(v) for k,v in zip(pairs,c)})
    for y in range(0,h,256):
        end=min(h,y+256);add(labels[y:end,:-1],labels[y:end,1:],edges)
        if y<h-1:add(labels[y:min(end,h-1)],labels[y+1:min(end,h-1)+1],edges)
    add(labels[:,0],labels[:,-1],seams);edges.update(seams)
    records=[]
    for i,c in enumerate(colors):
        records.append({'province_hex':f'{int(c):06X}','rgb_r':int(c)>>16,'rgb_g':int(c)>>8&255,'rgb_b':int(c)&255,'pixel_area':int(counts[i]),'sum_x':int(sx[i]),'sum_y':int(sy[i]),'sum_cos_x':float(cos[i]),'sum_sin_x':float(sin[i]),'bbox_min_x':int(minx[i]),'bbox_min_y':int(miny[i]),'bbox_max_x':int(maxx[i]),'bbox_max_y':int(maxy[i]),'representative_x':int(firstx[i]),'representative_y':int(firsty[i]),'touches_left_edge':bool(minx[i]==0),'touches_right_edge':bool(maxx[i]==w-1),'touches_top_edge':bool(miny[i]==0),'touches_bottom_edge':bool(maxy[i]==h-1)})
    edge_rows=[{'province_hex_a':f'{int(colors[p//n]):06X}','province_hex_b':f'{int(colors[p%n]):06X}','shared_pixel_edges':c,'seam_pixel_edges':seams[p]} for p,c in sorted(edges.items())]
    result={'width':w,'height':h,'mode':image.mode,'provinces':records,'adjacency':edge_rows}
    cache.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    return result

if __name__=='__main__':
    base=pathlib.Path(__file__).resolve().parent.parent
    result=compute(base/'source_snapshot/map_data/provinces.png',base/'raster_cache.json')
    print(json.dumps({'width':result['width'],'height':result['height'],'colors':len(result['provinces']),'pixels':sum(r['pixel_area'] for r in result['provinces']),'adjacency_pairs':len(result['adjacency'])}))
