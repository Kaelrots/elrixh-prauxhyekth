#!/usr/bin/env python3
"""Read-only validation of the R4.0 cross-reference patch package.
Usage: python verify_stage4.py [unpacked_package_directory]
Uses Python standard library only. Verifies editing/mapping integrity, not legal substance.
"""
from __future__ import annotations
import csv,hashlib,json,re,sys,collections
from pathlib import Path

def check(ok,message):
 if not ok:raise ValueError(message)
def digest(data):return hashlib.sha256(data).hexdigest()
def verify(root):
 root=Path(root).resolve();base=root/'기준자료/3단계'
 load=lambda path:json.loads(path.read_text(encoding='utf-8'))
 patch=load(root/'07_상호참조_패치기록.json');data=load(root/'04_상호참조_처리데이터.json')
 m=load(base/'06_리넘버링_매니페스트.json')
 source=(base/'기준자료/2단계/기준자료/엘리시움 연방 헌법.md').read_bytes()
 original_lines=source.decode().splitlines(keepends=True)
 stage3=(base/patch['stage3_work_file']).read_bytes();stage4=(root/patch['stage4_work_file']).read_bytes()
 check(digest(source)==patch['original_sha256']==m['source']['sha256'],'Original source hash')
 check(digest(stage3)==patch['stage3_sha256']==data['stage3_work_sha256'],'Stage3 hash')
 check(digest(stage4)==patch['stage4_sha256'],'Stage4 hash')
 a=stage3.decode().splitlines(keepends=True);z=stage4.decode().splitlines(keepends=True)
 n=patch['stage4_body_line_count'];check(n==len(a),'Original working-body line count')
 check(''.join(z[n:])==patch['appended_editorial_text'],'Editorial appendix changed')
 pp={x['stage3_line']:x for x in patch['patches']};check(len(pp)==len(patch['patches']),'Duplicate patch line')
 restored=list(z[:n])
 for i in range(1,n+1):
  if i in pp:
   p=pp[i];check(p['before']==a[i-1],'Patch original line mismatch '+str(i));check(p['after']==z[i-1],'Patch result mismatch '+str(i));restored[i-1]=p['before']
  else:check(a[i-1]==z[i-1],'Unrecorded edit '+str(i))
 check(''.join(restored).encode()==stage3,'Stage3 byte-exact reverse reconstruction')
 # Independently reconstruct each reference-edited line from recorded character spans.
 findings=data['findings'];ids={r['id'] for r in findings};check(len(ids)==len(findings),'Duplicate finding ID')
 grouped=collections.defaultdict(list)
 for r in findings:grouped[r['working_line']].append(r)
 for ln,rows in grouped.items():
  before=a[ln-1];s=before.rstrip('\r\n');ending=before[len(s):]
  active=[r for r in rows if r['result']['mode'] not in ('historic-apparatus','unchanged-generic','external-link')]
  spans=sorted((r['start'],r['end']) for r in active)
  check(all(b<=c for (_,b),(c,_) in zip(spans,spans[1:])),'Overlapping reference spans '+str(ln))
  for r in sorted(active,key=lambda r:r['start'],reverse=True):
   check(s[r['start']:r['end']]==r['raw'],'Reference span before mismatch '+r['id'])
   s=s[:r['start']]+r['rendered']+s[r['end']:]
  # Only wrapping backticks around a generated link or editorial footnote can be removed.
  s=re.sub(r'`([^`\n]+)`',lambda mt:mt[1] if ('[[05_원범위_' in mt[1] or '[[#^ren-' in mt[1] or '[^r4-' in mt[1]) else mt[0],s)
  check(s+ending==z[ln-1],'Non-reference text changed on content line '+str(ln))
 # Undo R3 structural numbering and then restore every original source line once.
 r3patches=load(base/m['patches_file'])['patches'];r3p={p['source_line']:p for p in r3patches}
 cache={patch['stage3_work_file']:restored};recreated=[None]*len(original_lines)
 for p in m['source_line_partition']:
  fn=p['destination_file']
  if fn not in cache:cache[fn]=(root/fn).read_bytes().decode().splitlines(keepends=True)
  lines=cache[fn][p['destination_start_line']-1:p['destination_end_line']]
  check(len(lines)==p['source_end_line']-p['source_start_line']+1,'Source span length')
  check(digest(''.join(lines).encode())==p['numbered_sha256'],'Numbered block hash '+p['id'])
  for j,text in enumerate(lines,p['source_start_line']):
   check(recreated[j-1] is None,'Repeated source line')
   if j in r3p:check(text==r3p[j]['after'],'R3 numbered line mismatch');text=r3p[j]['before']
   recreated[j-1]=text
 check(all(x is not None for x in recreated),'Missing source line')
 check(''.join(recreated).encode()==source,'Original source byte-exact reverse reconstruction')
 # All referenced new groups and lower hierarchy entries are real R3.0 entries.
 g={x['id']:x for x in m['new_groups']};e={x['mapping_id']:x for x in m['mapping_edges']};u={x['source_unit_id']:x for x in m['source_unit_mapping']}
 anchors=set(re.findall(r'^\^([a-zA-Z0-9-]+)\s*$',stage4.decode(),re.M))
 for group in g.values():check(group['anchor'] in anchors,'Missing group anchor '+group['id'])
 for r in findings:
  q=r['result']
  check(all(t in g for t in q['targets']),'Nonexistent target group '+r['id'])
  check(all(t in e for t in q['target_edges']),'Nonexistent target paragraph '+r['id'])
  check(all(e[t]['group_id'] in q['targets'] for t in q['target_edges']),'Paragraph outside target groups '+r['id'])
  if q['error']:check('대상 확인 필요' in r['rendered'] and q['text'] is None,'Unresolved ref presented as resolved')
  if q['mode']=='historic-apparatus':check(z[r['working_line']-1]==a[r['working_line']-1],'Original glossary content changed')
 # Every chapter/section scope points to exactly the transferred original members.
 for key,scope in data['scope_sets'].items():
  expected={d['id'] for uid in scope['source_unit_ids'] for d in u[uid]['destinations']}
  check(expected==set(scope['target_groups']),'Scope broadened/narrowed '+key)
  if not scope.get('custom_range'):
   members={x['source_unit_id'] for x in u.values() if x['old_chapter']==scope['old_chapter'] and (scope['old_section'] is None or x['old_section']==scope['old_section'])}
   check(members==set(scope['source_unit_ids']),'Old scope membership changed '+key)
 # Newly generated wiki targets only. Original linked worldbuilding assets are outside this pass.
 scope_text=(root/data['scope_document']).read_text();issue_text=(root/'03_확인필요_및_원문보정대장.md').read_text()
 scope_anchors=set(re.findall(r'^\^([a-zA-Z0-9-]+)\s*$',scope_text,re.M))
 issue_anchors=set(re.findall(r'^\^([a-zA-Z0-9-]+)\s*$',issue_text,re.M))
 generated_strings=[r['rendered'] for r in findings if r['result']['mode']!='historic-apparatus']
 generated_strings += [scope_text,issue_text,patch['appended_editorial_text']]
 links=0
 for text in generated_strings:
  # Ignore doubled-backtick source quotation, so old source wikilinks are not treated as generated links.
  text=re.sub(r'``[^\n]*?``','',text)
  for mt in re.finditer(r'\[\[([^\]|]+?)(?:\\?\|[^\]]*)?\]\]',text):
   target=mt[1].rstrip('\\');path,sep,anchor=target.partition('#^')
   if not sep:continue
   if not path or path==patch['stage4_work_file'][:-3]:check(anchor in anchors,'New body link broken '+target);links+=1
   elif path==data['scope_document'][:-3]:check(anchor in scope_anchors,'New scope link broken '+target);links+=1
   elif path=='03_확인필요_및_원문보정대장':check(anchor in issue_anchors,'New issue link broken '+target);links+=1
 # Editorial footnotes are uniquely defined and present.
 ft=stage4.decode();defs=re.findall(r'^\[\^(r4-[^\]]+)\]:',ft,re.M);refs=re.findall(r'\[\^(r4-[^\]]+)\](?!:)',ft)
 check(len(defs)==len(set(defs)),'Duplicate editorial footnote')
 check(set(refs)==set(defs),'Missing/unused editorial footnote')
 # Metadata and stage3 numbering are unchanged except explicit editorial status/labels.
 for ln,p in pp.items():
  if p['category']!='reference':continue
  for pat in [r'^(#{3,6}\s+제\d+[조항호목])',r'^(> \[!summary\][+-]?\s+제\d+조)']:
   m0=re.match(pat,p['before'])
   if m0:check(re.match(pat,p['after']).group(1)==m0.group(1),'R3 structural number changed')
 # The stage4 full TSV has one row for each JSON entry with matching source/new texts.
 rows=list(csv.DictReader((root/'04_상호참조_전체처리대장.tsv').open(encoding='utf-8-sig'),delimiter='\t'))
 check(len(rows)==len(findings),'TSV size mismatch')
 for row,r in zip(rows,findings):
  check(row['ID']==r['id'] and row['구인용']==r['raw'] and row['신인용']==(r['result']['text'] or '') and row['본문표시']==r['rendered'],'TSV/JSON mismatch '+r['id'])
 oldrows=list(csv.DictReader((root/'08_기존참조목록_대조표.tsv').open(encoding='utf-8-sig'),delimiter='\t'))
 check(len(oldrows)==1368,'Inherited inventory coverage count')
 check(all(x['처리'] for x in oldrows),'Unaccounted inherited occurrence')
 line_rows=list(csv.DictReader((root/'10_원문행_4단계행_대응표.tsv').open(encoding='utf-8-sig'),delimiter='\t'))
 check(len(line_rows)==len(original_lines),'Source line correspondence count')
 check([int(x['원문행']) for x in line_rows]==list(range(1,len(original_lines)+1)),'Source line correspondence missing/duplicate')
 return {'passed':True,'verification_scope':'편집·복원·표기대응·링크·범위보존. 헌법적 실질 정합성 전체 보증 아님.',
 'original_sha256':digest(source),'restored_original_sha256':digest(''.join(recreated).encode()),
 'stage3_sha256':digest(stage3),'restored_stage3_sha256':digest(''.join(restored).encode()),
 'stage4_sha256':digest(stage4),'source_lines':len(original_lines),
 'reference_records':len(findings),'reference_patched_lines':sum(x['category']=='reference' for x in pp.values()),
 'original_scope_sets':len(data['scope_sets']),'new_target_groups_exist':True,'new_lower_targets_exist':True,
 'original_scope_membership_exact':True,'group_anchors_preserved':len(g),'checked_generated_links':links,
 'editorial_footnotes':len(defs),'unaccounted_inherited_occurrences':0,
 'unrecorded_edits':0,'source_rows_missing':0,'source_rows_duplicated':0,'new_numbering_changed':0,
 'tsv_json_concordance':True,'counts':data['counts']}

if __name__=='__main__':
 root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
 try:print(json.dumps(verify(root),ensure_ascii=False,indent=2))
 except Exception as exc:print('VERIFICATION FAILED:',exc,file=sys.stderr);sys.exit(1)
