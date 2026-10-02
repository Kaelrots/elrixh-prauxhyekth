from pathlib import Path
import re,json,hashlib,collections,difflib

ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'기준자료').exists(): OUT=ROOT
else: OUT=ROOT/'delivery/헌법_제2차_초안_최종본_패키지'
src=next((OUT/'기준자료').glob('*R5-A1.16*.md')).read_text()
final=(OUT/'엘리시움 연방 헌법_제2차 초안 최종본.md').read_text()
style=(OUT/'기준자료/제1차_초안_양식기준.md').read_text()
sha=lambda x:hashlib.sha256(x.encode()).hexdigest()

def norm(text,source=False):
    if source:text=text[text.index('# 서문\n')+len('# 서문\n'):]
    else:text=text[text.index('## 서문 및 총강\n')+len('## 서문 및 총강\n'):]
    text=re.sub(r'<!--.*?-->','',text,flags=re.S)
    text=re.sub(r'^> \[!success\]- R5-A1\.13 · D-10 승인 반영\n> [^\n]+\n','',text,flags=re.M)
    text=re.sub(r'^\^[\w-]+\s*$','',text,flags=re.M)
    text=re.sub(r' \^[\w-]+\s*$','',text,flags=re.M)
    if source:
        text=re.sub(r'^### 제(\d+)조:[^\n]+\n(?:\s*\n)*(?=### 제\1조:)','',text,flags=re.M)
        # Expected, explicitly recorded paragraph-order-only change.
        p7=re.search(r'^#### 제7항\n긴급 연방 황제령.*?(?=\n\s*#### 제6항)',text,re.M|re.S)[0].strip()
        p6=re.search(r'^#### 제6항\n연방 황제령의 제·개정·폐지의 세부는 황제령 통합관리 규정으로 정한다\.',text,re.M)[0]
        text=text.replace(p7,'',1).replace(p6,p6+'\n\n'+p7,1)
    text=text.replace('# 제2연방 헌법: 본문 조항','')
    text=re.sub(r'^<hr class="hr-thick-\d+">\s*$','',text,flags=re.M)
    text=re.sub(r'^<div[^\n]+?<font[^>]*>『(제\d+절 [^』]+)』</font></div>',r'\1',text,flags=re.M)
    text=re.sub(r'^#{1,6} ', '', text,flags=re.M)
    text=re.sub(r'!\[[^\]]*\]\(<assets/([^>]+)>\)',r'![[\1]]',text)
    return '\n'.join(x.rstrip() for x in text.splitlines() if x.strip())

sn,fn=norm(src,True),norm(final)
diff=list(difflib.unified_diff(sn.splitlines(),fn.splitlines(),fromfile='source-normalized',tofile='final-normalized',lineterm=''))
if diff:
    (OUT/'검증자료/내용대조_차이.txt').write_text('\n'.join(diff))
    raise AssertionError('\n'.join(diff[:50]))

def chapter_chunks(text):
    # Operative chapter headings only, not the TOC/HTML display duplicates.
    result={}; current='총강'; buf=[]
    for line in text.splitlines():
        if re.match(r'^제\d+장:',line):
            result[current]='\n'.join(buf);current=line;buf=[]
        if line=='이관 경과별표':
            result[current]='\n'.join(buf);current='이관 경과별표';buf=[]
        buf.append(line)
    result[current]='\n'.join(buf)
    return result
sc,fc=chapter_chunks(sn),chapter_chunks(fn)
unit_hashes=[{'scope':k,'source_sha256':sha(v),'final_sha256':sha(fc[k]),'identical':v==fc[k]} for k,v in sc.items()]

anchors=re.findall(r'(?:^| )\^([a-zA-Z0-9-]+)$',final,re.M)
refs=re.findall(r'\[\[#\^([^|\]]+)',final)
heading_refs=re.findall(r'(?<!!)\[\[#(?!\^)([^|\]]+)',final)
headings=[re.sub(r' \^[\w-]+$','',m[1]) for m in re.finditer(r'^#{1,6} (.*)$',final,re.M)]
definitions=re.findall(r'^\[\^([^\]]+)\]:',final,re.M)
calls=re.findall(r'\[\^([^\]]+)\](?!:)',final)
source_definitions=re.findall(r'^\[\^([^\]]+)\]:',src,re.M)
def footnotes(t):
    return {m[1]:m[2].rstrip() for m in re.finditer(r'^\[\^([^\]]+)\]:(.*(?:\n(?:[ \t]+.*|\s*$))*)',t,re.M)}
footnote_payload_identical=footnotes(src)==footnotes(final)
images=re.findall(r'!\[\[([^\]]+)\]\]',final)
chapters=re.findall(r'^## (제\d+장:[^\n]+)',final,re.M)
section_titles=re.findall(r'<font[^>]*>『(제\d+절 [^』]+)』</font></div>',final)

# Delimit paragraphs by ALL article-level blocks, including independently
# titled transition blocks. The separately headed proviso is not a new para.
ch='총강';article=None;arts=collections.defaultdict(list);paras=collections.defaultdict(list);provisos=[]
for line in final[final.index('### 총강'):final.index('# 이관 경과별표')].splitlines():
    if m:=re.match(r'^## (제\d+장:[^\n]+)',line):ch=m[1];article=None
    if re.match(r'^### (?:부칙|구 용어집)',line):article=None
    if m:=re.match(r'^#{3,4} 제(\d+)조(?:의\s*(\d+))?:',line):
        article=(int(m[1]),int(m[2] or 0));arts[ch].append(article)
    if article and (m:=re.match(r'^#### 제(\d+)항(.*)',line)):
        if '단서' in m[2]:provisos.append([ch,article,int(m[1])]);continue
        paras[(ch,article)].append(int(m[1]))
article_dups=[];article_gaps=[];paragraph_issues=[]
for c,v in arts.items():
    nums={x[0] for x in v if not x[1]}
    for a,n in collections.Counter(v).items():
        if n>1:article_dups.append([c,a,n])
    if gap:=sorted(set(range(1,max(nums)+1))-nums):article_gaps.append([c,gap])
for k,v in paras.items():
    dup=[n for n,c in collections.Counter(v).items() if c>1]
    gap=sorted(set(range(1,max(v)+1))-set(v))
    if dup or gap or v!=sorted(v):paragraph_issues.append({'chapter':k[0],'article':k[1],'sequence':v,'duplicates':dup,'missing':gap,'ordered':v==sorted(v)})

anchor_targets={m[2]:re.sub(r'^#+ ','',m[1]) for m in re.finditer(r'^(.*?) \^([\w-]+)$',final,re.M)}
label_mismatch=[]
for target,label in re.findall(r'\[\[#\^([^|\]]+)\|([^\]]+)\]\]',final):
    if (lm:=re.search(r'(?:제\d+장|총강) 제(\d+)조(?:의\s*(\d+))?',label)) and (tm:=re.search(r'^제(\d+)조(?:의\s*(\d+))?',anchor_targets.get(target,''))):
        if lm.groups()!=tm.groups():label_mismatch.append([target,label,anchor_targets.get(target)])

report={
    'comparison':{'source_sha256':sha(src),'style_sha256':sha(style),'final_sha256':sha(final),'normalized_source_sha256':sha(sn),'normalized_final_sha256':sha(fn),'identical_after_documented_format_changes':sn==fn,'substantive_text_changes':0,'source_trace_blocks':len(re.findall('<!-- numbered-begin:',src)),'scope_hashes':unit_hashes},
    'structure':{'chapters':len(chapters),'sections_including_general':len(section_titles),'articles_including_general':sum(map(len,arts.values())),'articles_by_chapter':{k:len(v) for k,v in arts.items()},'paragraph_heading_count':sum(map(len,paras.values())),'article_number_duplicates':article_dups,'article_number_gaps':article_gaps,'inherited_paragraph_issues':paragraph_issues,'separately_headed_provisos':provisos},
    'links':{'anchor_definitions':len(anchors),'anchor_references':len(refs),'duplicate_anchors':[a for a,n in collections.Counter(anchors).items() if n>1],'missing_anchors':sorted(set(refs)-set(anchors)),'heading_references':len(heading_refs),'missing_headings':sorted(set(heading_refs)-set(headings)),'explicit_article_label_mismatch':label_mismatch},
    'footnotes':{'definitions':len(definitions),'references':len(calls),'duplicate_definitions':[a for a,n in collections.Counter(definitions).items() if n>1],'missing_definitions':sorted(set(calls)-set(definitions)),'definition_set_preserved':set(definitions)==set(source_definitions),'definition_payload_preserved':footnote_payload_identical},
    'images':{'embedded_occurrences':len(images),'embedded_files':sorted(set(images)),'missing': [x for x in set(images) if not (OUT/'assets'/x).exists()],'packaged_png_count':len(list((OUT/'assets').glob('*.png'))),'royal_chart':'external text reference retained; no fabricated embed'},
    'format':{'yaml_field_names_preserved':re.findall(r'^([^ :\n]+):',style.split('---')[1],re.M)==re.findall(r'^([^ :\n]+):',final.split('---')[1],re.M),'dataviewjs_exact':re.search(r'```dataviewjs.*?```',style,re.S)[0]==re.search(r'```dataviewjs.*?```',final,re.S)[0],'central_title_html_exact':all(x in final for x in re.findall(r'^<div[^\n]+(?:《|『제2연방|제3기)[^\n]+$',style,re.M)),'section_html_style':'first-draft centered 1.6em #88dfd0; 181 section titles preserved','editorial_comment_count':len(re.findall(r'<!--',final))},
    'time_standards':{'source_FST':len(re.findall(r'\bFST\b',src)),'final_FST':len(re.findall(r'\bFST\b',final)),'source_UST':len(re.findall(r'\bUST\b',src)),'final_UST':len(re.findall(r'\bUST\b',final))},
    'work_markers':{x:final.count(x) for x in ['구 인용','대상 확인 필요','TODO','편집용·공포본 제거','numbered-begin','user-reserve-begin']},
    'final_status':'format-complete; substantive promotion blocked by inherited source conflict; native Obsidian/Quartz rendering not executed'
}
assert len(chapters)==21 and len(section_titles)==181
assert len(definitions)==229 and footnote_payload_identical
assert not report['links']['missing_anchors'] and not report['links']['duplicate_anchors']
assert not report['links']['missing_headings'] and not article_dups and not article_gaps
assert not report['images']['missing']
assert not report['footnotes']['missing_definitions']
assert len(paragraph_issues)==2,paragraph_issues
(OUT/'검증자료/최종본_정적QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(OUT/'검증자료/내용대조_범위별_SHA256.json').write_text(json.dumps(unit_hashes,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='comparison'},ensure_ascii=False,indent=2))
