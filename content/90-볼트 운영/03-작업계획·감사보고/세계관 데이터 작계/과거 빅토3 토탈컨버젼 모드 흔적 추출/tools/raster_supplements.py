import json,pathlib
import numpy as np
from PIL import Image
BASE=pathlib.Path(__file__).resolve().parent.parent
Image.MAX_IMAGE_PIXELS=None
img=np.asarray(Image.open(BASE/'source_snapshot/map_data/provinces.png'),dtype=np.uint32)
codes=(img[:,:,0]<<16)|(img[:,:,1]<<8)|img[:,:,2];del img
colors=np.unique(codes);n=len(colors);h,w=codes.shape
lookup=np.full(1<<24,-1,dtype=np.int32);lookup[colors]=np.arange(n);labels=lookup[codes];del lookup,codes
height=Image.open(BASE/'source_snapshot/map_data/heightmap.png');assert height.size==(w*2,h*2)
sums=np.zeros(n,dtype=np.float64);counts=np.zeros(n,dtype=np.int64);mins=np.full(n,65536,dtype=np.int32);maxs=np.full(n,-1,dtype=np.int32)
for y in range(0,h,64):
    end=min(h,y+64);part=np.asarray(height.crop((0,y*2,w*2,end*2)),dtype=np.uint32).reshape(end-y,2,w,2)
    sums2=part.sum(axis=(1,3));min2=part.min(axis=(1,3));max2=part.max(axis=(1,3));ids=labels[y:end].ravel()
    sums+=np.bincount(ids,weights=sums2.ravel(),minlength=n);counts+=np.bincount(ids,minlength=n)*4
    np.minimum.at(mins,ids,min2.ravel());np.maximum.at(maxs,ids,max2.ravel())
rows=[{'province_hex':f'{int(c):06X}','height_sample_count':int(counts[i]),'height_raw_sum':int(sums[i]),'height_raw_min':int(mins[i]),'height_raw_max':int(maxs[i]),'height_raw_mean':float(sums[i]/counts[i])} for i,c in enumerate(colors)]
river=Image.open(BASE/'source_snapshot/map_data/rivers.png');assert river.mode=='P' and river.size==(w,h)
indices=np.asarray(river);pairs,pc=np.unique(labels.astype(np.int64)*256+indices,return_counts=True)
riverrows=[{'province_hex':f'{int(colors[k//256]):06X}','palette_index':int(k%256),'pixel_count':int(c)} for k,c in zip(pairs,pc)]
palette=river.getpalette();palette_rows=[{'palette_index':int(index),'rgb_r':palette[int(index)*3],'rgb_g':palette[int(index)*3+1],'rgb_b':palette[int(index)*3+2],'map_pixel_count':int(c)} for index,c in zip(*np.unique(indices,return_counts=True))]
cache={'height_alignment':'same top-left origin; one province pixel covers 2x2 original height pixels; no vertical flip','height_raw_units':'unsigned raw sample, not calibrated metres','height_width':height.width,'height_height':height.height,'height_mode':height.mode,'height_provinces':rows,'river_province_palette_counts':riverrows,'river_palette':palette_rows}
assert sum(r['height_sample_count'] for r in rows)==height.width*height.height
assert sum(r['pixel_count'] for r in riverrows)==w*h
(BASE/'raster_supplements.json').write_text(json.dumps(cache,separators=(',',':')),encoding='utf-8')
print(json.dumps({'height_rows':len(rows),'height_sample_count':sum(r['height_sample_count'] for r in rows),'river_palette_rows':len(riverrows),'river_palette':palette_rows}))
