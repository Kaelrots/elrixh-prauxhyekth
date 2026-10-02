#!/usr/bin/env python3
"""Read-only, standard-library validation of stage-3 numbering and mapping.
Usage: python verify_stage3.py [unpacked_package_directory]
Checks editing/mapping integrity, NOT the substance of legal provisions.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

class VerificationError(Exception): pass

def require(test: bool, message: str) -> None:
    if not test: raise VerificationError(message)

def digest(b: bytes) -> str: return hashlib.sha256(b).hexdigest()

def verify(root: Path) -> dict:
    root=root.resolve()
    def path(rel: str) -> Path:
        p=(root/rel).resolve();require(p.is_relative_to(root),'Unsafe path: '+rel);return p
    def js(rel: str):return json.loads(path(rel).read_text(encoding='utf-8'))
    m=js('06_리넘버링_매니페스트.json')
    j=js('기준자료/2단계/04_재배치_매니페스트.json')
    raw=path('기준자료/2단계/기준자료/엘리시움 연방 헌법.md').read_bytes()
    source=raw.decode('utf-8').splitlines(keepends=True)
    require(digest(raw)==m['source']['sha256']==j['source']['sha256'],'Source hash mismatch')
    require(digest(path('기준자료/2단계/04_재배치_매니페스트.json').read_bytes())==m['stage2_manifest_sha256'],'Stage2 manifest changed')
    patches=js(m['patches_file'])['patches'];pd={p['source_line']:p for p in patches}
    require(len(pd)==len(patches),'Duplicate patch lines')
    cache={}
    def lines(rel: str):
        if rel not in cache:cache[rel]=path(rel).read_bytes().decode('utf-8').splitlines(keepends=True)
        return cache[rel]
    def extract(rel,a,z):return ''.join(lines(rel)[a-1:z]).encode('utf-8')
    # Allow only structural heading tokens, not body numbers/amounts/references.
    def strip_label(s):
        if re.match(r'^#{3,6}\s+제\d+[조항호목]',s):
            return re.sub(r'^#{3,6}\s+제\d+[조항호목](?:의\s*\d+)?','<heading>',s,count=1)
        if re.match(r'^> \[!summary\][+-]?\s+제\d+조',s):
            return re.sub(r'제\d+조(?:의\s*\d+)?','<article>',s,count=1)
        raise VerificationError('Patch outside allowed headings: '+s[:100])
    for p in patches:
        require(p['before']==source[p['source_line']-1],'Patch before mismatch')
        require(strip_label(p['before'])==strip_label(p['after']),'Non-label source edit')
        before=re.search(r'제\d+([조항호목])',p['before']).group(1)
        after=re.search(r'제\d+([조항호목])',p['after']).group(1)
        require(before==after or (p['source_line']==9099 and before=='조' and after=='항'),'Unapproved hierarchy type edit')
    restored=[None]*len(source);line_map={}
    for p in m['source_line_partition']:
        a,z=p['source_start_line'],p['source_end_line'];da,dz=p['destination_start_line'],p['destination_end_line']
        got=lines(p['destination_file'])[da-1:dz]
        require(len(got)==z-a+1,'Source span line length mismatch: '+p['id'])
        require(digest(''.join(got).encode())==p['numbered_sha256'],'Numbered content hash mismatch: '+p['id'])
        back=[]
        for i,v in zip(range(a,z+1),got):
            require(restored[i-1] is None,'Duplicate source line placement')
            expected=pd[i]['after'] if i in pd else source[i-1]
            require(v==expected,f'Unexpected text at source L{i}')
            restored[i-1]=pd[i]['before'] if i in pd else v;back.append(restored[i-1])
            line_map[i]=(p['destination_file'],da+i-a)
        require(digest(''.join(back).encode())==p['original_sha256'],'Inverse span hash mismatch')
    require(all(x is not None for x in restored),'Unmapped source lines')
    reconstructed=''.join(restored).encode('utf-8');require(reconstructed==raw,'Byte-exact inverse reconstruction failed')
    groups=m['new_groups'];gd={g['id']:g for g in groups};edges=m['mapping_edges'];ed={e['mapping_id']:e for e in edges}
    require(len(gd)==len(groups),'Duplicate new group ID')
    require(len(ed)==len(edges),'Duplicate mapping ID')
    require(len({e['new_address'] for e in edges})==len(edges),'Duplicate full destination address')
    require({e['source_node_id'] for e in edges}=={n['node_id'] for n in j['source_nodes']},'Missing/new source node IDs')
    require(m['source_nodes_original']==j['source_nodes'],'Original source-node index modified')
    require(m['structure']==j['structure'],'Approved chapter/section structure modified')
    bs={b['block_id']:b for b in j['placement_blocks']};seq=[];bg={}
    for g in groups:
        for bid in g['block_ids']:
            b=bs[bid];seq.append(b['placement_order']);bg[bid]=g['id']
            require((g['chapter'],g['section'])==(b['destination_chapter'],b['destination_section']),'Stage2 placement changed')
            require(b['source_unit_id']==g['source_unit_id'],'Different old articles merged')
    require(seq==list(range(1,len(bs)+1)),'Stage2 block order changed/missing')
    for c in range(22):
        nums=[g['article_number'] for g in groups if g['chapter']==c and g['kind']=='article']
        require(nums==list(range(1,len(nums)+1)),'Nonconsecutive article numbers')
    # Independently parse rendered headings, not just manifest values.
    actual=[];c=None;s=None
    for i,v in enumerate(lines('01_헌법_리넘버링_작업본.md'),1):
        mc=re.match(r'^# 제(\d+)장 ',v)
        if v=='# 총강\n':c=0;s=None
        elif mc:c=int(mc[1]);s=None
        ms=re.match(r'^## 제(\d+)절 ',v)
        if ms:s=int(ms[1])
        ma=re.match(r'^### 제(\d+)조',v)
        if ma:actual.append((c,s,int(ma[1])))
    expect=[(g['chapter'],g['section'],g['article_number']) for g in groups if g['kind']=='article']
    require(actual==expect,'Rendered article order differs from mapping')
    for sec in m['sections']:
        v=lines('01_헌법_리넘버링_작업본.md')[sec['heading_line']-1]
        require(v==f'## 제{sec["new_section"]}절 {sec["title"]}\n','Section heading/line mismatch')
    bysource=defaultdict(list);under=defaultdict(list)
    for e in edges:
        bysource[e['source_node_id']].append(e)
        if e['new_parent_mapping_id']:
            require(e['new_parent_mapping_id'] in ed,'Dangling parent mapping')
            require(ed[e['new_parent_mapping_id']]['group_id']==e['group_id'],'Cross-group subordinate parent')
        if e['new_type'] in ('항','호','목'):
            under[(e['new_parent_mapping_id'],e['new_type'])].append(e['new_number'])
            # Its actual own heading must carry the new number.
            own=next(p for p in e['working_spans'] if p['source_start_line']<=e['source_start_line']<=p['source_end_line'])
            ln=own['new_start_line']+e['source_start_line']-own['source_start_line']
            require(re.match(r'^#{4,6}\s+제'+str(e['new_number'])+e['new_type'],lines(own['file'])[ln-1]) is not None,'Rendered subordinate number mismatch')
        for p in e['working_spans']:
            require((p['file'],p['new_start_line'])==line_map[p['source_start_line']],'Working span start mismatch')
            require((p['file'],p['new_end_line'])==line_map[p['source_end_line']],'Working span end mismatch')
    for vals in under.values():require(sorted(vals)==list(range(1,len(vals)+1)),'Subordinate number gap/duplicate')
    for n in j['source_nodes']:
        intervals=[]
        for e in bysource[n['node_id']]:
            for p in e['source_spans']:intervals.extend(range(p['source_start_line'],p['source_end_line']+1))
        require(sorted(intervals)==list(range(n['start'],n['end']+1)),'Source-node range missing/duplicated')
        require(digest(''.join(source[n['start']-1:n['end']]).encode())==n['content_sha256'],'Source node hash mismatch')
    def tsv(rel):
        with path(rel).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))
    rows=tsv('05_조항호목_상세매칭표.tsv')
    require(len(rows)==len(edges),'TSV row count mismatch')
    for r in rows:
        e=ed[r['대응_ID']]
        require(r['새계층경로']==e['new_address'] and r['원추적_ID']==e['source_node_id'],'TSV target mismatch')
    # Same complete edge multiset in both human-readable tables.
    for rel in ['02_구위치_신위치_전체매칭표.md','03_신위치_구위치_역매칭표.md']:
        data=[v for v in lines(rel) if v.startswith('| SRC-')]
        require(len(data)==len(edges),'Markdown mapping row count mismatch')
        need=Counter((e['source_node_id'],e['new_address']) for e in edges)
        got=Counter()
        for v in data:
            cells=re.split(r'(?<!\\)\|',v)
            got[(cells[1].strip(),cells[4].strip().replace('\\|','|'))]+=1
        require(got==need,'Markdown direction table contents differ')
    require(len([v for v in lines('04_조문_리넘버링_대응표.md') if v.startswith('| SRC-')])==len(j['source_units']),'Article summary missing source units')
    lr=tsv('10_원문행_신행_대응표.tsv');require(len(lr)==len(source),'Line-table count mismatch')
    for r in lr:require((r['3단계파일'],int(r['3단계행']))==line_map[int(r['원문행'])],'Line-table destination mismatch')
    refs=tsv('08_상호참조_4단계_입력대장.tsv');old=tsv('기준자료/2단계/07_상호참조_후속점검대장.tsv')
    require([r['참조_ID'] for r in refs]==[r['참조_ID'] for r in old],'Inherited reference inventory changed')
    for r in refs:
        require((r['3단계파일'],int(r['3단계행']))==line_map[int(r['원문행'])],'Reference occurrence location mismatch')
    wt=''.join(lines('01_헌법_리넘버링_작업본.md'))
    anchors=re.findall(r'^\^([a-z0-9-]+)$',wt,re.M)
    require(len(anchors)==len(set(anchors)),'Duplicate work-file anchor')
    require(all(g['anchor'] in anchors for g in groups),'Missing destination anchors')
    require(all(b['working_anchor'] in anchors for b in bs.values()),'Stage2 block anchor lost')
    # No general body line, quantity, voting threshold, term or citation edited.
    require(all(i in pd or restored[i-1]==source[i-1] for i in range(1,len(source)+1)),'Untracked edit')
    return {
       '검증결과':'통과','검증범위':'구조번호·전체 위치대응·원문 보존. 실질적 헌법 정합성 또는 상호참조 의미 검증 아님.',
       '원문_SHA256':digest(raw),'역복원_SHA256':digest(reconstructed),'번호패치_역적용_원문바이트복원':True,
       '원문행수':len(source),'미매칭_추적단위':0,'미배치_원문행':0,'중복복사_원문행':0,'허용밖_원문변경':0,
       '기존조문수':sum(u['kind']=='article' for u in j['source_units']),
       '새조문수':len(expect),'자료묶음수':sum(g['kind']!='article' for g in groups),
       '기존추적단위수':len(j['source_nodes']),'전체대응행수':len(edges),'원배치블록수':len(bs),
       '번호표제_변경행수':len(patches),'새조번호_중복누락':0,'새항호목번호_중복누락':0,
       '장절구조_유지':True,'2단계배치순서_유지':True,'원추적ID_유지':True,
       '정방향역방향_TSV_JSON_일치':True,'본문상호참조_치환실시':False,
       '4단계입력대장_출현수':len(refs),'총강절수':len(m['structure']['0']['sections']),
       '본문장수':len(m['structure'])-1,'본문절수':sum(len(s['sections']) for c,s in m['structure'].items() if c!='0')}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]);a=ap.parse_args()
    try:result=verify(a.directory)
    except (VerificationError,KeyError,ValueError,OSError) as exc:
        print(json.dumps({'검증결과':'실패','오류':str(exc)},ensure_ascii=False,indent=2));return 1
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
