import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?:([A-Za-z]:))/, '$1'));
const base = decodeURIComponent(here);
const layoutPath = path.join(base, 'physical_layout.json');
const layoutRaw = await fs.readFile(layoutPath, 'utf8');
const layout = JSON.parse(layoutRaw);
const outputDir = path.join(base, 'outputs', process.env.CODEX_THREAD_ID || '01a0fba0-1c53-7c51-9911-969855ad4f16');
const previewDir = path.join(outputDir, 'previews');
await fs.mkdir(previewDir, {recursive: true});

const labels = {
  relation_id:'관계 ID',culture_id:'문화 ID',relation_type:'관계 유형',scope_definition:'적용 범위',legal_basis:'법적 근거',
  language_status_id:'언어 지위 이력 ID',language_id:'언어 ID',language_status_code:'언어 지위 코드',legal_or_practice:'법정·관행 구분',
  cultural_institution_record_id:'문화제도 이력 ID',institution_or_policy_name_raw:'기관·정책명 원문',heritage_reference:'문화유산 참조',
  value_status:'값 상태',source_locator:'출처 내 위치',start_year:'시작 연도',start_month:'시작 월',start_day:'시작 일',
  end_year:'종료 연도',end_month:'종료 월',end_day:'종료 일',end_status:'종료 상태',religion_id:'종교 ID',denomination_id:'교단 ID',
  legal_status_code:'법적 지위 코드',religious_org_id:'종교조직 ID',name_other:'기타 명칭',legal_entity_kind:'법인 유형',
  parent_religious_org_id:'상위 종교조직 ID',headquarters_region_id:'본부 지역 ID',affairs_record_id:'교무 이력 ID',
  affairs_role_name_raw:'교무 역할명 원문',affairs_relation_type:'교무 관계 유형',political_office_id:'연관 공직 ID',political_term_id:'연관 공직 임기 ID',
  validation_status:'검증 상태',record_count:'자료 건수',connection_status:'연결 상태',approval_status:'승인 상태',
  annual_boundary_rule_raw:'연간 경계 규칙 원문',annual_point_difference_raw:'연간 시점 차이 원문',calendar_id:'역법 ID',
  calendar_name:'역법명',calendar_revision_id:'역법 판본 ID',calendar_rule_raw:'역법 규칙 원문',canon_status:'정본 상태',
  civil_day_seconds:'민간일 길이(초)',correction_after_day:'보정 기준 일',correction_after_month:'보정 기준 월',
  correction_is_date:'보정일 날짜 여부',correction_seconds:'보정 길이(초)',current_era_description:'현 기년 설명',
  days_per_month:'월별 일수',days_per_year:'연간 일수',definition:'정의',display_name:'표시명',edition_raw:'판본 원문',
  era_edition:'기년 판본',era_mapping_id:'기년 대응 ID',exact_boundary_rule_raw:'정확한 경계 규칙 원문',from_era:'시작 기년',
  from_year:'시작 연도',group_code:'코드 그룹',legacy_era_description:'기존 기년 설명',mapping_type:'대응 유형',
  modified_at_raw:'수정 시각 원문',months_per_year:'연간 월수',neutral_name:'중립 명칭',original_location:'원문 위치',
  owner_spreadsheet_id:'소유 파일 ID',policy_id:'정책 ID',policy_name:'정책명',policy_raw:'정책 원문',policy_revision_id:'정책 판본 ID',
  record_kind:'기록 종류',source_kind:'출처 종류',source_namespace:'출처 구분',source_standard_revision_ids:'출처 표준 판본 ID',
  source_title:'출처 제목',stored_code:'저장 코드',to_era:'대상 기년',to_year:'대상 연도',unknown_end_rule_raw:'종료 미상 규칙 원문',
  url:'주소',usage_scope:'사용 범위',usage_status:'사용 상태',birth_day:'출생 일',birth_era:'출생 기년',birth_month:'출생 월',
  birth_precision:'출생일 정밀도',birth_year:'출생 연도',death_day:'사망 일',death_era:'사망 기년',death_month:'사망 월',
  death_precision:'사망일 정밀도',death_year:'사망 연도',person_classification_raw:'인물 분류 원문',person_description_raw:'인물 설명 원문'
};
const domainTitles={N60:'국가문화·언어제도',N70:'국가종교·교무'};
const blockTitles={
  IN_NATION_CULTURE_RELATION:'국가문화관계',IN_LANGUAGE_STATUS_HISTORY:'언어지위 이력',IN_CULTURAL_INSTITUTION_HISTORY:'문화제도 이력',
  IN_NATION_RELIGION_RELATION:'국가종교관계',IN_RELIGIOUS_ORGANIZATION:'종교조직',IN_RELIGIOUS_AFFAIRS_HISTORY:'교무 이력',
  CHECK_RESULTS:'검증 결과',PUB_CULTURAL_INSTITUTION_HISTORY_V2:'문화제도 이력 제공',PUB_LANGUAGE_STATUS_HISTORY_V2:'언어지위 이력 제공',
  PUB_NATION_CULTURE_RELATION_V2:'국가문화관계 제공',PUB_NATION_RELIGION_RELATION_V2:'국가종교관계 제공',
  PUB_RELIGIOUS_AFFAIRS_HISTORY_V2:'교무 이력 제공',PUB_RELIGIOUS_ORGANIZATION_V2:'종교조직 제공',
  PUB_N60_CHECK_RESULTS_V2:'N60 검증 결과 제공',PUB_N70_CHECK_RESULTS_V2:'N70 검증 결과 제공',
  PUB_CALENDAR_V2:'역법 참조',PUB_CODEBOOK_V2:'코드북 참조',PUB_NATIONS_V2:'국가 참조',PUB_PERSON_V2:'인물 참조',PUB_SOURCES_V2:'출처 참조'
};
function col(n){let s='';for(;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
function local(a){return a.slice(a.indexOf('!')+1);}
function sha(buf){return crypto.createHash('sha256').update(buf).digest('hex');}
const metadata={created_at:new Date().toISOString(),layout_version:layout.layout_version,layout_path:layoutPath,layout_sha256:sha(layoutRaw),
  method:'@oai/artifact-tool',online_actions_performed:false,native_validation_status:'미실행',world_fact_rows:0,
  marker_expected_output_count:2,style:'Google native white/light gray; Korean-first',files:[],label_translations:labels,
  pending_native_actions:['Google Sheets import','실제 격자 크기 적용','이름범위 생성','입력·제공·참조·검사 보호 적용','빈 표는 실제 입력 발생 후 native table 전환','코드·기간 검증 규칙','연결·재계산·회귀 시험'],
  no_operating_formulas:true,notes:['예약 범위는 입력 가능 용량이며 실제 자료가 아니다.','입력·제공·검사·참조의 데이터 영역은 모두 빈칸이다.','검사 결과 표가 비어 있는 것은 통과 판정이 아니다.']};

for (const file of layout.files.filter(x=>['N60','N70'].includes(x.file_code))) {
  const wb=Workbook.create();
  const fm={file_code:file.file_code,path:path.join(outputDir,file.file_code+'.xlsx'),sheets:[],world_fact_rows:0,formula_count:0,export_status:'pending'};
  for (const tab of file.tabs) {
    const sheet=wb.worksheets.add(tab.title);sheet.showGridLines=true;
    const maxcol=col(tab.column_count);
    const styleRange=sheet.getRange(`A1:${maxcol}${tab.row_count}`);
    styleRange.format.font={name:'Arial',size:10,color:'#202124'};
    styleRange.format.fill='#FFFFFF';styleRange.format.verticalAlignment='center';styleRange.format.rowHeight=22;
    styleRange.format.columnWidth=23;
    const sm={title:tab.title,role:tab.role,planned_rows:tab.row_count,planned_columns:tab.column_count,blocks:[],previews:[]};
    if(tab.role==='GUIDE') {
      sheet.getRange('A2').values=[[`${file.file_code} ${domainTitles[file.file_code]}`]];
      sheet.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:'#202124'};
      sheet.getRange('A2:B2').format.rowHeight=30;
      sheet.getRange('A4:B4').values=[['항목','내용']];
      const guide=[['구축 상태','신규 빈 분야. 실제 설정 자료는 아직 없습니다.'],['실제 자료','입력·제공·참조·검사 결과 모두 0행입니다. 예약된 빈칸은 자료 건수에 포함하지 않습니다.'],
        ['입력 범위',file.file_code==='N60'?'국가문화관계, 언어지위 이력, 문화제도 이력':'국가종교관계, 종교조직, 교무 이력'],
        ['입력 시작','각 입력 탭의 4행부터 기록합니다. 2행은 한글 항목명, 3행은 연결용 필드명입니다.'],
        ['설정 근거','근거가 확인된 자료만 입력합니다. 미정·충돌 설정은 출처와 판본을 보존하고 결정대기로 남깁니다.'],
        ['ID 원칙','기존 ID를 유지합니다. 신규 ID는 ID 원장에 등록한 뒤 사용합니다.'],
        ['기간 기록','기년·연도·월·일과 정밀도를 분리합니다. 모르는 날짜를 임의로 채우지 않습니다.'],
        ['연결 상태','온라인 연결과 제공 수식은 아직 적용하지 않았습니다. 연결 미실행을 자료 없음으로 판정하지 않습니다.'],
        ['검사 상태','온라인 권한·재계산·연결·회귀 시험은 미실행입니다. 빈 검사표는 통과 결과가 아닙니다.'],
        ['원본 단일화',file.file_code==='N70'?'인물은 N30, 모든 공직 임기는 N20에서만 입력합니다. 공직·임기 연관 검증은 H90에서 수행합니다.':'국가 기준 ID와 분류는 공통 기준을 사용합니다. 문화·언어의 국가별 적용 이력은 이 파일에서 입력합니다.'],
        ['범위 확장','입력·계산·검증·제공·소비 범위와 이름범위를 함께 갱신하고 경계행 시험을 수행합니다.'],
        ['운영 전환','기술 구축·온라인 검증을 마친 뒤 별도 운영 전환 승인을 받습니다.']];
      sheet.getRange(`A5:B${guide.length+4}`).values=guide;
      sheet.getRange('A1:A20').format.columnWidth=21;sheet.getRange('B1:B20').format.columnWidth=112;
      sheet.getRange('A4:B4').format={fill:'#F1F3F4',font:{name:'Arial',size:10,bold:true,color:'#202124'}};
      sheet.getRange(`A5:B${guide.length+4}`).format.rowHeight=32;
      sm.guide_rows=guide.length;
    } else if(tab.role==='CONFIG') {
      sheet.getRange('A2').values=[['운영 설정']];sheet.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:'#202124'};
      sheet.getRange('A4:C4').values=[['항목','현재 값','적용 상태']];
      const config=[['파일 코드',file.file_code,'로컬 작성'],['분야',domainTitles[file.file_code],'신규 빈 분야'],['실제 세계관 자료',0,'근거 자료 입력 전'],
        ['물리 배치 판본',layout.layout_version,'현재 배치'],['온라인 파일 ID','','Google Sheets 가져오기 후 등록'],['제공 판본','','온라인 검증 후 발급'],
        ['원본 연결','','미실행'],['검증 실행','','미실행'],['운영 전환','','승인 대기']];
      sheet.getRange(`A5:C${config.length+4}`).values=config;
      sheet.getRange('A1:A16').format.columnWidth=24;sheet.getRange('B1:B16').format.columnWidth=38;sheet.getRange('C1:C16').format.columnWidth=43;
      sheet.getRange('A4:C4').format={fill:'#F1F3F4',font:{name:'Arial',size:10,bold:true,color:'#202124'}};
      sheet.getRange('A5:C13').format.rowHeight=28;
    } else {
      for(const b of tab.blocks) {
        const id=b.logical_table_id||b.dataset_id;
        const status={IN:'신규 분야 · 자료 없음',PUB:'제공식 미배치',REF:'온라인 연결 미실행',CHECK:'시험 미실행'}[tab.role];
        const title=blockTitles[id]||id;
        sheet.getRange(`A${b.block_title_row}`).values=[[`${title} · ${status}`]];
        sheet.getRange(`A${b.block_title_row}:${b.last_column}${b.block_title_row}`).format.rowHeight=28;
        sheet.getRange(`A${b.block_title_row}`).format.font={name:'Arial',size:12,bold:true,color:'#202124'};
        const display=b.columns.map(c=>labels[c.field_id]||c.label_ko);
        sheet.getRange(local(b.display_header_range)).values=[display];
        sheet.getRange(local(b.display_header_range)).format={fill:'#F1F3F4',font:{name:'Arial',size:10,bold:true,color:'#202124'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:36};
        sheet.getRange(local(b.header_range)).values=[b.columns.map(c=>c.field_id)];
        sheet.getRange(local(b.header_range)).format={fill:'#FAFAFA',font:{name:'Arial',size:10,color:'#5F6368'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:58};
        sheet.getRange(local(b.header_range)).format.borders={bottom:{style:'thin',color:'#DADCE0'}};
        for(const c of b.columns){
          const rg=sheet.getRange(`${c.column_letter}${b.data_start_row}:${c.column_letter}${b.data_end_row}`);
          if(c.type==='text_id'||c.type==='text')rg.setNumberFormat('@');
          else if(c.type?.startsWith('integer'))rg.setNumberFormat('0');
        }
        sm.blocks.push({id,role:tab.role,header_range:b.header_range,display_header_range:b.display_header_range,data_range:b.data_range,bounded_range:b.bounded_range,named_range:b.named_range,named_range_status:'native 생성 대기',primary_key_fields:b.primary_key_fields,columns:b.columns.map((c,i)=>({field_id:c.field_id,label_ko:display[i],required:c.required,type:c.type})),actual_data_rows:0,formula_state:'미배치'});
      }
      sheet.freezePanes.freezeRows(tab.frozen_row_count||3);sheet.freezePanes.freezeColumns(tab.frozen_column_count||1);
    }
    fm.sheets.push(sm);
  }
  wb.recalculate();
  for(const sm of fm.sheets){
    const ranges=(sm.role==='GUIDE'?[{range:'A1:B17',label:'overview'}]:sm.role==='CONFIG'?[{range:'A1:C14',label:'overview'}]:sm.blocks.map((b,i)=>{const rr=Number(local(b.header_range).match(/\d+/)[0]);return{range:`A${rr-2}:H${rr+2}`,label:`block${i+1}`};}));
    for(const r of ranges){
      const previewPath=path.join(previewDir,`${file.file_code}_${sm.title}_${r.label}.png`);
      const preview=await wb.render({sheetName:sm.title,range:r.range,scale:1.25,format:'png'});
      await fs.writeFile(previewPath,new Uint8Array(await preview.arrayBuffer()));sm.previews.push({path:previewPath,range:r.range});
    }
  }
  const errorScan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'Final blank-domain formula error scan'});
  fm.formula_error_scan=errorScan.ndjson;
  const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(fm.path);
  const bytes=await fs.readFile(fm.path);fm.sha256=sha(bytes);fm.byte_size=bytes.length;fm.export_status='saved';
  metadata.files.push(fm);
  console.log(JSON.stringify({file:file.file_code,path:fm.path,sheets:fm.sheets.length,previews:fm.sheets.reduce((s,x)=>s+x.previews.length,0),bytes:fm.byte_size}));
}
await fs.writeFile(path.join(outputDir,'N60_N70_build_metadata.json'),JSON.stringify(metadata,null,2),'utf8');
