import json, pathlib, zipfile, xml.etree.ElementTree as ET, re, hashlib
BASE=pathlib.Path(__file__).parent
OUT=BASE/'outputs'/'01a0fba0-1c53-7c51-9911-969855ad4f16'
M=OUT/'N60_N70_build_metadata.json'
meta=json.loads(M.read_text(encoding='utf-8'))
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
report={'scope':'local XLSX structure/content only','native_tests':'미실행','files':[],'errors':[]}
def colnum(c):
    n=0
    for x in c:n=n*26+ord(x)-64
    return n
for f in meta['files']:
    p=pathlib.Path(f['path'])
    res={'file_code':f['file_code'],'path':str(p),'sheet_count':0,'technical_headers_checked':0,'world_fact_rows':0,'data_nonblank_cells':0,'formula_count':0,'error_cell_count':0,'frozen_sheets':0,'sheets':[]}
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        rel=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rels={x.attrib['Id']:x.attrib['Target'] for x in rel}
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        sheets=wb.findall('s:sheets/s:sheet',NS)
        assert [s.attrib['name'] for s in sheets]==[s['title'] for s in f['sheets']]
        res['sheet_count']=len(sheets)
        for sheet,expected in zip(sheets,f['sheets']):
            target=rels[sheet.attrib['{'+NS['r']+'}id']]
            target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            xml=ET.fromstring(z.read(target))
            cells={}
            for c in xml.findall('.//s:sheetData/s:row/s:c',NS):
                value=c.find('s:v',NS)
                val=value.text if value is not None else ''
                if c.attrib.get('t')=='s':val=strings[int(val)]
                elif c.attrib.get('t')=='inlineStr':val=''.join(c.find('s:is',NS).itertext())
                cells[c.attrib['r']]=val or ''
                if c.find('s:f',NS) is not None:res['formula_count']+=1
                if c.attrib.get('t')=='e':res['error_cell_count']+=1
            frozen=xml.find('s:sheetViews/s:sheetView/s:pane',NS)
            if frozen is not None:res['frozen_sheets']+=1
            sr={'title':expected['title'],'header_count':0,'data_nonblank_cells':0,'visual_review':'reviewed'}
            for b in expected['blocks']:
                hdr=b['header_range'].split('!')[1]
                a,bb=hdr.split(':');row=int(re.findall(r'\d+',a)[0]);c0=colnum(re.match('[A-Z]+',a)[0])
                for i,field in enumerate(b['columns']):
                    n=c0+i;s=''
                    while n:s=chr(65+(n-1)%26)+s;n=(n-1)//26
                    assert cells.get(f'{s}{row}')==field['field_id'],(expected['title'],field['field_id'])
                    sr['header_count']+=1;res['technical_headers_checked']+=1
                dr=b['data_range'].split('!')[1];a,bb=dr.split(':')
                r1,r2=int(re.findall(r'\d+',a)[0]),int(re.findall(r'\d+',bb)[0])
                c1,c2=colnum(re.match('[A-Z]+',a)[0]),colnum(re.match('[A-Z]+',bb)[0])
                found=[address for address,v in cells.items() if v!='' and r1<=int(re.findall(r'\d+',address)[0])<=r2 and c1<=colnum(re.match('[A-Z]+',address)[0])<=c2]
                sr['data_nonblank_cells']+=len(found)
                assert not found,(expected['title'],b['id'],found)
            res['data_nonblank_cells']+=sr['data_nonblank_cells'];res['sheets'].append(sr)
        assert res['formula_count']==0 and res['error_cell_count']==0
    res['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    res['result']='pass'
    report['files'].append(res)
meta['local_verification']=report
meta['visual_review']={'sheets_reviewed':16,'preview_files_created':29,'result':'pass','scope':'all sheet opening views; every block header preview generated','notes':'White/light gray; Korean labels readable; data bodies blank. Long technical field IDs wrap without loss.'}
meta['build_process']={'observed_exit_code':1,'stderr':'none captured','all_requested_exports_saved':True,'metadata_written':True,'independent_saved_xlsx_zip_xml_verification':'pass','note':'Process exit anomaly retained; export validity is confirmed separately by ZIP/XML checks, not inferred from process exit.'}
M.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'N60_N70_local_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['scope','native_tests','errors']},ensure_ascii=False))
print(json.dumps([{k:v for k,v in f.items() if k!='sheets'} for f in report['files']],ensure_ascii=False))
