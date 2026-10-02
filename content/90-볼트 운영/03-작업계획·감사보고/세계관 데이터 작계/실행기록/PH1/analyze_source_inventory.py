"""Read PH0 evidence only; write reproducible PH1 JSON/CSV inventories, never XLSX.

Formula patterns are diagnostic regex normalization, NOT executable replacements.
All migration/target-field decisions remain pending. FALSE-only rows are kept.
"""
from pathlib import Path
import csv, json, hashlib, re, zipfile, posixpath, collections, sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
PH0 = HERE.parent / 'PH0'
NS = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
RNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
RELNS = '{http://schemas.openxmlformats.org/package/2006/relationships}'

def jwrite(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def writer(name, fields):
    f = (HERE/name).open('w', newline='', encoding='utf-8-sig')
    w = csv.DictWriter(f, fields, extrasaction='ignore'); w.writeheader()
    return f,w

def plain(v):
    return '' if v is None else json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v

def ci(s):
    n=0
    for ch in s: n=n*26+ord(ch)-64
    return n

def cl(n):
    s=''
    while n: n,r=divmod(n-1,26); s=chr(65+r)+s
    return s

def coords(ref):
    m=re.match(r'([A-Z]+)([0-9]+)',ref)
    return ci(m[1]),int(m[2])

def range_list(refs):
    cols=collections.defaultdict(list)
    for ref in refs:
        c,r=coords(ref); cols[c].append(r)
    out=[]
    for c,rs in sorted(cols.items()):
        rs=sorted(set(rs)); a=b=rs[0]
        for r in rs[1:]:
            if r==b+1: b=r
            else:
                out.append(f'{cl(c)}{a}'+(f':{cl(c)}{b}' if b!=a else ''));a=b=r
        out.append(f'{cl(c)}{a}'+(f':{cl(c)}{b}' if b!=a else ''))
    return out

def relations(z,path):
    rp=posixpath.join(posixpath.dirname(path),'_rels',posixpath.basename(path)+'.rels')
    if rp not in z.namelist(): return {}
    out={}
    for e in ET.fromstring(z.read(rp)):
        d=dict(e.attrib);target=d['Target']
        d['resolved']=target if d.get('TargetMode')=='External' else posixpath.normpath(posixpath.join(posixpath.dirname(path),target)).lstrip('/')
        out[d['Id']]=d
    return out

def xtype(c,strings):
    typ=c.get('t','n'); v=c.find('m:v',NS)
    txt=None if v is None else v.text
    if typ=='s': return 'string',strings[int(txt)] if txt is not None else ''
    if typ=='inlineStr': return 'string',''.join(t.text or '' for t in c.findall('.//m:t',NS))
    if typ=='b': return 'boolean',txt=='1'
    if typ=='e': return 'error',txt
    if typ=='str': return 'string',txt or ''
    return ('number',txt) if txt is not None else ('empty',None)

def native_value(c):
    v=c.get('userEnteredValue',{})
    for k in ('stringValue','numberValue','boolValue','formulaValue'):
        if k in v: return k,v[k]
    return 'empty',None

def normalize_formula(f,row):
    # Approximate clustering only: original formulas remain in immutable PH0 XML.
    return re.sub(r'(?<![A-Za-z0-9_])([$]?[A-Z]{1,3})([$]?)([0-9]+)',
        lambda m:m[1]+('$'+m[3] if m[2] else '{r'+str(int(m[3])-row)+'}'),f)

def is_id_header(s):
    s=s.strip().split(' / ')[-1]
    return s.endswith('_id') or s in ('기준 ID','지역 ID','국가 ID','문화 ID','종교 ID','언어 ID','집단 ID','자원 ID','특성 ID','지표 ID','사건 ID','시설 ID','노선 ID','관계 ID','출처 ID')

def canonical_workbook(path):
    output={}
    with zipfile.ZipFile(path) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(t.text or '' for t in si.findall('.//m:t',NS)) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels=relations(z,'xl/workbook.xml')
        for sh in ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',NS):
            root=ET.fromstring(z.read(rels[sh.get(RNS+'id')]['resolved']))
            groups={'export_literal':{},'formula_text_and_attributes':{},'formula_cached_results':{}}
            for c in root.findall('m:sheetData/m:row/m:c',NS):
                ref=c.get('r');typ,val=xtype(c,strings);fe=c.find('m:f',NS)
                if fe is None:
                    if val is not None:groups['export_literal'][ref]=[typ,val]
                else:
                    groups['formula_text_and_attributes'][ref]=[dict(sorted(fe.attrib.items())),fe.text or '']
                    groups['formula_cached_results'][ref]=[typ,val]
            output[sh.get('name')]=groups
    return output

def hash_cells(cells):
    h=hashlib.sha256()
    for ref,value in sorted(cells.items(),key=lambda kv:(coords(kv[0])[1],coords(kv[0])[0])):
        h.update(json.dumps([ref,*value],ensure_ascii=False,separators=(',',':')).encode('utf-8')+b'\n')
    return h.hexdigest()

def compare_end():
    results=[]
    for source in ('REG-V1','NAT-V1'):
        a=PH0/f'{source}_online.xlsx';b=PH0/f'{source}_end.xlsx'
        if not b.exists():
            results.append({'source_file_code':source,'status':'종료 파일 없음 · 미검증'});continue
        before=canonical_workbook(a);after=canonical_workbook(b)
        shresults=[]
        for title in sorted(set(before)|set(after)):
            if title not in before or title not in after:
                shresults.append({'sheet_name':title,'status':'탭 추가/누락'});continue
            checks={}
            for kind in before[title]:
                av=before[title][kind];bv=after[title][kind]
                changed=sorted((ref for ref in set(av)|set(bv) if av.get(ref)!=bv.get(ref)),key=lambda ref:(coords(ref)[1],coords(ref)[0]))
                checks[kind]={'before_count':len(av),'after_count':len(bv),'before_sha256':hash_cells(av),'after_sha256':hash_cells(bv),'changed_cells':len(changed),'changed_examples':[{'cell':ref,'before':av.get(ref),'after':bv.get(ref)} for ref in changed[:30]]}
            shresults.append({'sheet_name':title,'checks':checks})
        unchanged=all('checks' in s and s['checks']['export_literal']['changed_cells']==0 and s['checks']['formula_text_and_attributes']['changed_cells']==0 for s in shresults)
        cache_changes=sum(s.get('checks',{}).get('formula_cached_results',{}).get('changed_cells',0) for s in shresults)
        results.append({'source_file_code':source,'status':'수출 원문 literal 및 수식·수식속성 동일' if unchanged else '변경 또는 표현차이 검토 필요','export_literal_and_formula_equal':unchanged,'formula_cache_changed_cells':cache_changes,'before_file_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'after_file_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'sheets':shresults,'limitations':['XLSX 내 shared strings는 실문자열로 확장, 숫자는 원문 lexical string 보존, 셀은 행·열 순 정렬','수식 text/attributes와 캐시 결과를 별도로 비교함','literal에는 수출된 spill 출력이 포함될 수 있어 실제 사용자 입력과 구별 필요','네이티브 권한·드롭다운 칩·서식 무변경은 별도 온라인 증거가 필요']})
    jwrite('canonical_start_end_comparison.json',results)
    print(json.dumps([{k:v for k,v in r.items() if k!='sheets'} for r in results],ensure_ascii=False),flush=True)

def main():
    maps=list(csv.DictReader((BASE/'02_기존87개시트_이관대응표.csv').open(encoding='utf-8-sig')))
    mapping={(m['source_file'],m['source_sheet']):m for m in maps}
    native={}
    native_files=sorted(PH0.glob('*_headers_*.json'))+sorted(p for p in PH0.glob('native_data_*.json') if re.fullmatch(r'native_data_[0-9]+\.json',p.name))
    for p in native_files:
        obj=json.loads(p.read_text(encoding='utf-8-sig'))
        obj=obj.get('response',obj)
        for sh in obj.get('sheets',[]):
            key=(obj['spreadsheetId'],sh['properties']['title']);v=native.setdefault(key,{'cells':{},'files':[]})
            v['files'].append(p.name)
            for gd in sh.get('data',[]):
                for rr,row in enumerate(gd.get('rowData',[]),gd.get('startRow',0)+1):
                    for cc,c in enumerate(row.get('values',[]),gd.get('startColumn',0)+1):
                        v['cells'][f'{cl(cc)}{rr}']=c
    field_cols=['source_file_code','source_file_id','source_sheet_id','source_sheet_name','source_column','source_field_id','source_field','header_rows','header_original','source_type','source_role','source_role_evidence','literal_cells','formula_cells','default_false_cells','nonempty_formula_cache_cells','map_id','target_file_code_candidates','target_table_candidates','target_file_code','target_table','target_field','transform_rule','preservation_location','change_reason','approval_or_rule','validation_result','migration_status','header_review_required']
    row_cols=['source_file_code','source_file_id','source_sheet_id','source_sheet_name','source_row','row_class','literal_count','nonfalse_literal_count','formula_count','false_count','nonempty_cache_count','id_evidence','literal_cells','legacy_locator']
    lit_cols=['source_file_code','source_file_id','source_sheet_id','source_sheet_name','cell','source_column','source_field','value_type','value_json','cell_role','row_class','legacy_locator']
    cache_cols=['source_file_code','source_sheet_id','source_sheet_name','cell','cache_type','cache_value_json','classification','pattern_id']
    f1,fields=writer('actual_field_mapping_draft.csv',field_cols)
    f2,rowsout=writer('source_row_inventory.csv',row_cols)
    f3,lits=writer('literal_cells.csv',lit_cols)
    f4,caches=writer('formula_nonempty_cache_observations.csv',cache_cols)
    inventories=[];patterns=[];metadata=[];field_count=0;global_counts=collections.Counter();exceptions=[];bounded=[];fingerprints=[]
    for source in ('REG-V1','NAT-V1'):
        info=json.loads((PH0/f'{source}_sheets_start.json').read_text(encoding='utf-8-sig'))
        sid=info['spreadsheetId']; online={s['properties']['title']:s for s in info['sheets']}
        backup_native_path=PH0/f'{source}_backup_native_metadata.json'
        backup_native=json.loads(backup_native_path.read_text(encoding='utf-8-sig')) if backup_native_path.exists() else {}
        backup_sheets={s['properties']['title']:s for s in backup_native.get('updatedSpreadsheet',{}).get('sheets',[])}
        path=PH0/f'{source}_online.xlsx';digest=hashlib.sha256(path.read_bytes()).hexdigest();snap=f'{source}:sha256:{digest}'
        with zipfile.ZipFile(path) as z:
            strings=[]
            if 'xl/sharedStrings.xml' in z.namelist():
                for si in ET.fromstring(z.read('xl/sharedStrings.xml')):
                    strings.append(''.join(t.text or '' for t in si.findall('.//m:t',NS)))
            wb=ET.fromstring(z.read('xl/workbook.xml'));rels=relations(z,'xl/workbook.xml')
            names=[{'attributes':dict(e.attrib),'value':e.text} for e in wb.findall('m:definedNames/m:definedName',NS)]
            for sheet in wb.findall('m:sheets/m:sheet',NS):
                title=sheet.get('name');op=online[title]['properties'];sheetid=op['sheetId'];mp=mapping[(source,title)]
                xmlpath=rels[sheet.get(RNS+'id')]['resolved'];root=ET.fromstring(z.read(xmlpath));sr=relations(z,xmlpath)
                observed=native.get((sid,title),{'cells':{},'files':[]})
                header_end=2 if source=='REG-V1' and title=='01-지역 마스터' else 5 if title in ('87_시점별_황위계승','88_친족관계_조회') else 1
                column=collections.defaultdict(lambda:collections.Counter());rawcells={};rowdata=collections.defaultdict(list);pc={};sample_header={};style_only=0
                literal_hash=hashlib.sha256();formula_hash=hashlib.sha256();cache_hash=hashlib.sha256();nonfalse_hash=hashlib.sha256()
                merged=[e.get('ref') for e in root.findall('m:mergeCells/m:mergeCell',NS)]
                for c in root.findall('m:sheetData/m:row/m:c',NS):
                    ref=c.get('r');col,row=coords(ref);typ,val=xtype(c,strings);fe=c.find('m:f',NS);formula=None if fe is None else (fe.text or '')
                    if formula is None and val is None:style_only+=1;continue
                    item={'ref':ref,'col':col,'row':row,'type':typ,'value':val,'formula':formula}
                    rawcells[ref]=item;rowdata[row].append(item);column[col]['cells']+=1
                    canonical_value=json.dumps([ref,typ,val],ensure_ascii=False,separators=(',',':')).encode('utf-8')+b'\n'
                    if formula is None:
                        literal_hash.update(canonical_value)
                        if val is not False: nonfalse_hash.update(canonical_value)
                    else:
                        formula_hash.update(json.dumps([ref,dict(sorted(fe.attrib.items())),formula],ensure_ascii=False,separators=(',',':')).encode('utf-8')+b'\n')
                        cache_hash.update(canonical_value)
                    if row<=8: sample_header[ref]={'type':typ,'value':val,'formula':formula,'native':observed['cells'].get(ref,{})}
                    if formula is None:
                        column[col]['literal']+=1;column[col]['type_'+typ]+=1
                        if val is False:column[col]['false']+=1
                    else:
                        column[col]['formula']+=1
                        if val not in (None,''): column[col]['cache_nonempty']+=1
                        norm=normalize_formula(formula,row);pid=hashlib.sha256((source+'|'+str(sheetid)+'|'+norm).encode()).hexdigest()[:20]
                        item['pattern_id']=pid
                        if pid not in pc:
                            refs=re.findall(r"'((?:[^']|'')+)'!|(?<![A-Za-z0-9_])([A-Za-z0-9_가-힣][A-Za-z0-9_가-힣]*)!",formula)
                            deps=sorted(set(a.replace("''","'") or b for a,b in refs))
                            native_f=observed['cells'].get(ref,{}).get('userEnteredValue',{}).get('formulaValue')
                            pc[pid]={'pattern_id':pid,'source_file_code':source,'source_sheet_id':sheetid,'source_sheet_name':title,'normalized_pattern_diagnostic_only':norm,'example_cell':ref,'example_xlsx_formula':formula,'example_native_formula':native_f,'functions':sorted(set(re.findall(r'([A-Za-z_][A-Za-z0-9_.]*)\s*\(',formula))),'sheet_dependencies_regex':deps,'external_sheet_ids':sorted(set(re.findall(r'/spreadsheets/d/([A-Za-z0-9_-]+)',formula))),'has_xlsx_compatibility_wrapper':'DUMMYFUNCTION' in formula or '_xlfn.' in formula,'uses_iferror':bool(re.search(r'\bIFERROR\s*\(',formula,re.I)),'cells':[],'cache_types':collections.Counter()}
                        pc[pid]['cells'].append(ref);pc[pid]['cache_types'][typ]+=1
                # Include columns with native notes/validation even if XLSX has no nonempty values.
                for ref,c in observed['cells'].items():
                    col,row=coords(ref)
                    if c.get('note') or c.get('dataValidation') or c.get('userEnteredValue'): column[col]['native_observed']+=1
                headers={};headerdetails={}
                for col in sorted(column):
                    vals=[]
                    hrs=[1,2] if header_end==2 else [5] if header_end==5 else [1]
                    for rr in hrs:
                        ref=f'{cl(col)}{rr}';it=rawcells.get(ref);nc=observed['cells'].get(ref,{})
                        kt,nv=native_value(nc)
                        value=nv if kt=='stringValue' else it['value'] if it else None
                        if value not in (None,''):vals.append(str(value))
                    headers[col]=' / '.join(dict.fromkeys(vals)) if vals else f'[헤더 미확인:{cl(col)}]'
                    headerdetails[col]={'rows':hrs,'values':vals}
                row_counts=collections.Counter();fcount=lcount=falsecount=cachecount=0
                primary_id_cols=[c for c in sorted(column) if is_id_header(headers[c])]
                for row,items in sorted(rowdata.items()):
                    literal=[it for it in items if it['formula'] is None];nonfalse=[it for it in literal if it['value'] is not False and it['value'] not in (None,'')];form=[it for it in items if it['formula'] is not None]
                    ids=[{'cell':it['ref'],'header':headers[it['col']],'value':it['value']} for it in nonfalse if it['col'] in primary_id_cols]
                    derived=any(x in mp['migration_action'] for x in ('조회','수식','검증','퇴역','재작성')) or '연결' in title
                    if row<=header_end:klass='header_or_query_controls'
                    elif not nonfalse and literal and all(it['value'] is False for it in literal):klass='default_false_only_not_fact'
                    elif nonfalse and all(headers[it['col']] in ('순서','정렬') for it in nonfalse):klass='ordering_only_review_not_fact'
                    elif nonfalse:klass='derived_or_configuration_literal_review' if derived else 'literal_input_candidate_with_id' if ids else 'literal_input_candidate_without_id_review'
                    elif form:klass='formula_only_not_input_fact'
                    else:klass='empty_literal_review'
                    row_counts[klass]+=1;legacy=f'{sid}|gid={sheetid}|row={row}|{snap}'
                    rowsout.writerow({'source_file_code':source,'source_file_id':sid,'source_sheet_id':sheetid,'source_sheet_name':title,'source_row':row,'row_class':klass,'literal_count':len(literal),'nonfalse_literal_count':len(nonfalse),'formula_count':len(form),'false_count':sum(it['value'] is False for it in literal),'nonempty_cache_count':sum(it['value'] not in (None,'') for it in form),'id_evidence':plain(ids),'literal_cells':','.join(it['ref'] for it in literal),'legacy_locator':legacy})
                    for it in literal:
                        lits.writerow({'source_file_code':source,'source_file_id':sid,'source_sheet_id':sheetid,'source_sheet_name':title,'cell':it['ref'],'source_column':cl(it['col']),'source_field':headers[it['col']],'value_type':it['type'],'value_json':json.dumps(it['value'],ensure_ascii=False),'cell_role':'header_or_controls' if row<=header_end else 'literal_not_yet_semantically_classified','row_class':klass,'legacy_locator':legacy+'|cell='+it['ref']})
                    for it in form:
                        if it['value'] not in (None,''):
                            caches.writerow({'source_file_code':source,'source_sheet_id':sheetid,'source_sheet_name':title,'cell':it['ref'],'cache_type':it['type'],'cache_value_json':json.dumps(it['value'],ensure_ascii=False),'classification':'export_cached_formula_result_not_input_truth','pattern_id':it['pattern_id']})
                    fcount+=len(form);lcount+=len(literal);falsecount+=sum(it['value'] is False for it in literal);cachecount+=sum(it['value'] not in (None,'') for it in form)
                for col,co in sorted(column.items()):
                    h=headers[col];notes=[observed['cells'].get(f'{cl(col)}{rr}',{}).get('note','') for rr in headerdetails[col]['rows']];notestr=' | '.join(x for x in notes if x)
                    role='validation' if any(t in h for t in ('검증','오류','경고','자료 점검','기록 점검')) else 'formula' if co['formula'] else 'input'
                    if co['formula'] and co['literal']>len(headerdetails[col]['rows']):role='mixed_input_formula_review'
                    if '자동 조회' in notestr and not co['formula']:role='display_review'
                    fields.writerow({'source_file_code':source,'source_file_id':sid,'source_sheet_id':sheetid,'source_sheet_name':title,'source_column':cl(col),'source_field_id':f'{source}:{sheetid}:{cl(col)}','source_field':h,'header_rows':','.join(map(str,headerdetails[col]['rows'])),'header_original':plain(headerdetails[col]),'source_type':','.join(k[5:] for k in co if k.startswith('type_')) or ('formula' if co['formula'] else 'native_metadata_only'),'source_role':role,'source_role_evidence':notestr or '셀 내용 전수의 literal/formula/헤더 기반 초안','literal_cells':co['literal'],'formula_cells':co['formula'],'default_false_cells':co['false'],'nonempty_formula_cache_cells':co['cache_nonempty'],'map_id':mp['mapping_id'],'target_file_code_candidates':mp['target_file_code'],'target_table_candidates':mp['target_table_or_function'],'target_file_code':'','target_table':'','target_field':'','transform_rule':mp['migration_action']+'; '+mp['preservation_and_validation'],'preservation_location':f'PH0/{source}_online.xlsx#{xmlpath}:{cl(col)}; literal=PH1/literal_cells.csv; formulas=PH1/formula_patterns_and_dependencies.json','change_reason':'실제 필드 관측과 탭 대응 결합 초안; V2 대상 필드 결정 전','approval_or_rule':'계획서 11.2 및 '+mp['mapping_id'],'validation_result':'원문 보존 위치 확인; 운영 필드 결정·이관·검증 미실행','migration_status':'미실행','header_review_required':str('[헤더 미확인' in h or header_end==5 or title in ('42_행성_기본속성_연결','44_행성_연간지표_연결')).lower()})
                    field_count+=1
                for p in pc.values():
                    p['cell_count']=len(p['cells']);p['cell_ranges']=range_list(p.pop('cells'));p['cache_types']=dict(p['cache_types']);patterns.append(p)
                comments=[]
                for rr in sr.values():
                    if rr.get('Type','').endswith('/comments') and rr['resolved'] in z.namelist():
                        cr=ET.fromstring(z.read(rr['resolved']));authors=[x.text for x in cr.findall('m:authors/m:author',NS)]
                        for e in cr.findall('m:commentList/m:comment',NS):comments.append({'cell':e.get('ref'),'author_id':e.get('authorId'),'text':''.join(x.text or '' for x in e.findall('.//m:t',NS)),'authors':authors})
                dvs=[{'attributes':dict(e.attrib),'formula1':e.findtext('m:formula1',None,NS),'formula2':e.findtext('m:formula2',None,NS)} for e in root.findall('m:dataValidations/m:dataValidation',NS)]
                links=[{'attributes':dict(e.attrib),'relationship':sr.get(e.get(RNS+'id'))} for e in root.findall('m:hyperlinks/m:hyperlink',NS)]
                nd=collections.defaultdict(list);nn=[]
                for ref,c in observed['cells'].items():
                    if c.get('note'):nn.append({'cell':ref,'note':c['note']})
                    if c.get('dataValidation'):nd[json.dumps(c['dataValidation'],ensure_ascii=False,sort_keys=True)].append(ref)
                copysh=backup_sheets.get(title,{})
                copystruct={k:copysh[k] for k in ('tables','protectedRanges','merges','basicFilter','columnGroups','rowGroups') if k in copysh}
                mdata={'source_file_code':source,'source_sheet_id':sheetid,'source_sheet_name':title,'xml_path':xmlpath,'merged_ranges':merged,'xlsx_comments':comments,'xlsx_hyperlinks':links,'xlsx_data_validations':dvs,'native_sample_notes':nn,'native_sample_validation_groups':[{'rule':json.loads(k),'cell_ranges':range_list(v)} for k,v in nd.items()],'native_sample_files':observed['files'],'native_sample_coverage_cells':len(observed['cells']),'native_sample_not_full_sheet_metadata':True,'named_ranges_workbook':names,'conditional_formatting_ranges':[e.get('sqref') for e in root.findall('m:conditionalFormatting',NS)],'header_and_first_eight_rows':sample_header,'online_sheet_metadata':online[title],'backup_native_copy_observation_only':{'evidence_file':backup_native_path.name,'copy_sheet_properties':copysh.get('properties'),'not_asserted_as_source_native_state':True,'observed_structure':copystruct}}
                metadata.append(mdata)
                nonfalse_items=[it for it in rawcells.values() if it['formula'] is None and it['value'] is not False and it['value'] not in (None,'')]
                last_literal_row=max([it['row'] for it in nonfalse_items],default=header_end)
                last_literal_col=max([it['col'] for it in nonfalse_items],default=max(column,default=1))
                note_cells=sorted(set(x['cell'] for x in comments+nn))
                notes_only=[c for c in note_cells if c not in rawcells]
                escaped_title=title.replace("'","''")
                bounded.append({'source_file_code':source,'spreadsheet_id':sid,'sheet_id':sheetid,'sheet_name':title,'header_rows':headerdetails[next(iter(headerdetails))]['rows'] if headerdetails else [],'header_end_row':header_end,'last_nonfalse_literal_row':last_literal_row,'last_nonfalse_literal_column':cl(last_literal_col),'last_content_column':cl(max(column,default=1)),'bounded_a1':f"'{escaped_title}'!A1:{cl(max(column,default=1))}{max(last_literal_row,header_end)}",'nonfalse_literal_rows':sorted(set(it['row'] for it in nonfalse_items)),'note_cell_ranges':range_list(note_cells) if note_cells else [],'notes_only_cell_ranges':range_list(notes_only) if notes_only else [],'warning':'Includes configuration, auxiliary lists, historical test text and exported spill values; not final fact-row count. FALSE-only and formula-only trailing rows excluded from bounded_a1.'})
                fingerprints.append({'source_file_code':source,'source_sheet_id':sheetid,'source_sheet_name':title,'export_literal_sha256':literal_hash.hexdigest(),'export_nonfalse_literal_sha256':nonfalse_hash.hexdigest(),'formula_text_and_attributes_sha256':formula_hash.hexdigest(),'formula_cached_results_sha256':cache_hash.hexdigest(),'xlsx_sha256':digest,'canonicalization':'XML worksheet order; UTF8 compact JSON record plus LF. Formula attrs sorted. Shared strings expanded; numeric lexical strings retained. Export literals may contain spill output; native readback needed to classify actual input.'})
                inv={'source_file_code':source,'source_file_id':sid,'source_sheet_id':sheetid,'source_sheet_name':title,'online_grid_rows':op.get('gridProperties',{}).get('rowCount'),'online_grid_columns':op.get('gridProperties',{}).get('columnCount'),'xlsx_xml_path':xmlpath,'xlsx_sha256':digest,'hidden':sheet.get('state','visible')!='visible','header_rows_end':header_end,'observed_columns':len(column),'nonempty_or_formula_cells':len(rawcells),'literal_cells':lcount,'formula_cells':fcount,'default_false_cells':falsecount,'nonempty_formula_cache_cells':cachecount,'style_only_cells_excluded':style_only,'formula_patterns':len(pc),'row_class_counts':dict(row_counts),'comments':len(comments),'hyperlinks':len(links),'xlsx_validation_rules':len(dvs),'map_id':mp['mapping_id'],'analysis_status':'관측 완료; 의미/대상 필드 결정 미완료'}
                inventories.append(inv);global_counts.update({'tabs':1,'fields':len(column),'literal_cells':lcount,'formula_cells':fcount,'false_cells':falsecount,'nonempty_formula_caches':cachecount});global_counts.update(row_counts)
                print(f'{source} {title}: fields={len(column)} literals={lcount} formulas={fcount}',flush=True)
    for f in (f1,f2,f3,f4):f.close()
    jwrite('sheet_inventory.json',inventories);jwrite('formula_patterns_and_dependencies.json',patterns);jwrite('headers_notes_links_validations.json',metadata);jwrite('bounded_native_reads.json',bounded);jwrite('canonical_start_fingerprints.json',fingerprints)
    summary={'analysis_status':'전수 관측 완료 · 필드 대응 초안 · PH1 완료 아님','counts':dict(global_counts),'formula_pattern_count':len(patterns),'field_mapping_rows':field_count,'target_fields_decided':0,'migration_completed':0,'observed_tabs_missing_mapping':0,'limitations':['숫자 값은 XLSX XML 원문 숫자 문자열로 보존하여 부동소수점 변환하지 않음','수식 캐시는 입력 사실이 아니며 online 재계산 검증 증거가 아님','수식 패턴은 진단용 정규식 근사 군집이며 실행식으로 사용 금지','FALSE 단독 행은 원문을 보존하되 실제 사실 건수에서 제외; 참인 행과 비FALSE 불완전행은 별도 후보','행 분류는 인벤토리 초안이며 의미 판정·중복 병합·정본 채택을 수행하지 않음','네이티브 note/validation은 PH0에 확보된 헤더 및 bounded 실제 입력 후보 관측 범위; XLSX의 notes/validation은 전체 XML 관측','헤더 없는 spill/import 열과 특수 조회행은 원문 보존 후 검토 필요'],'remaining_gates':['각 실제 필드의 V2 운영 target_table/target_field 결정 및 원문보존 처리 승인 규칙','불완전 입력행 및 기본값·도움목록·설정행 의미 분류','병합·분리·중복 후보 레코드 원본별 대조','수식·조회·검증의 V2 기능 대응 및 온라인 시험','드롭다운 칩·권한·완전 네이티브 요소의 온라인 범위 점검'],'outputs':['sheet_inventory.json','actual_field_mapping_draft.csv','source_row_inventory.csv','literal_cells.csv','formula_nonempty_cache_observations.csv','formula_patterns_and_dependencies.json','headers_notes_links_validations.json']}
    summary['outputs']+=['bounded_native_reads.json','canonical_start_fingerprints.json']
    checks={'tab_count_matches_mapping':len(inventories)==len(maps),'field_rows_match_count':field_count==global_counts['fields'],'formula_patterns_cover_every_formula':sum(p['cell_count'] for p in patterns)==global_counts['formula_cells'],'sheet_literal_totals_match':sum(s['literal_cells'] for s in inventories)==global_counts['literal_cells'],'all_sheet_titles_have_mapping':all((s['source_file_code'],s['source_sheet_name']) in mapping for s in inventories),'migration_completed_is_zero':summary['migration_completed']==0,'target_fields_decided_is_zero':summary['target_fields_decided']==0}
    summary['local_inventory_integrity_checks']=checks
    summary['not_project_acceptance_test_results']=True
    jwrite('inventory_summary.json',summary)
    print(json.dumps(summary['counts'],ensure_ascii=False),flush=True)

if __name__=='__main__':
    if '--compare-end' in sys.argv:compare_end()
    else:main()
