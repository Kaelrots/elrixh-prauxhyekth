"""Generate additive V2 structure requests. This script has no online client.

Inputs are PH2/physical_layout.json and initial_native_{CODE}.json. Existing
source-copy sheets are never targeted, renamed, hidden, deleted, or resized.
Only new sheet headers/guide text are written; business data and formulas are
not emitted. A caller must refresh metadata and apply chunks sequentially,
read back each chunk, and record successful request IDs before resuming.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
V1_IDS = {
    "1EACdRIiAPGk4LAbttpXZiJd_cuqIh-cVi4jQsbfmqDw",
    "1mTRKFfCFtiTmuAR6QwrslcBI6Q-wutYzVP_weDAW9uI",
}
SKIP = {"N60", "N70"}
MAX_REQUESTS = 100
MAX_CELLS = 10_000_000
WHITE = {"red": 1, "green": 1, "blue": 1}
BLACK = {"red": 0, "green": 0, "blue": 0}
GRAY = {"red": .94, "green": .94, "blue": .94}
LIGHT = {"red": .97, "green": .97, "blue": .97}
ALLOWED_REQUESTS = {
    "addSheet", "updateCells", "addTable", "addNamedRange", "repeatCell",
    "addProtectedRange", "updateDimensionProperties",
}
API_SOURCES = [
    "https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/request#AddTableRequest",
    "https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/sheets#TableColumnProperties",
    "https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/sheets#ColumnType",
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def short_hash(value, length=16):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def col(number):
    result = ""
    while number:
        number, rem = divmod(number - 1, 26)
        result = chr(65 + rem) + result
    return result


def a1(title, start, end, width):
    return "'" + title.replace("'", "''") + f"'!A{start}:{col(width)}{end}"


def grid(sheet_id, start_row, end_row, columns, start_column=0):
    return {"sheetId": sheet_id, "startRowIndex": start_row,
            "endRowIndex": end_row, "startColumnIndex": start_column,
            "endColumnIndex": columns}


def string_cell(value, note=None, link=None):
    result = {"userEnteredValue": {"stringValue": str(value)}}
    if note:
        result["note"] = note
    if link:
        result["userEnteredFormat"] = {"textFormat": {"link": {"uri": link}}}
    return result


def update_rows(sheet_id, start_row, rows, fields="userEnteredValue,note"):
    assert rows and rows[0]
    width = len(rows[0])
    assert all(len(row) == width for row in rows)
    return {"updateCells": {"range": grid(sheet_id, start_row, start_row + len(rows), width),
                            "rows": [{"values": row} for row in rows], "fields": fields}}


def repeat_format(rectangle, fmt):
    return {"repeatCell": {"range": rectangle, "cell": {"userEnteredFormat": fmt},
                           "fields": "userEnteredFormat(" + ",".join(fmt) + ")"}}


def type_for(column):
    """Only exact, reliable declared types become native column restrictions."""
    typ = column["type"]
    if typ in {
        "integer", "integer_nullable", "decimal_nullable", "decimal_nullable_with_raw",
        "decimal_nullable; exact original in value_raw", "ratio_nullable", "decimal",
    }:
        return "DOUBLE", "명세에 명시된 수치형; 원문 필드는 별도 보존"
    if typ in {"boolean", "boolean_nullable"}:
        return "BOOLEAN", "명세에 명시된 불린형; 미입력은 FALSE로 채우지 않음"
    if typ in {"text", "text_nullable", "text_id", "text_identifier; case preserved", "hex_text"}:
        return "TEXT", "명세에 명시된 문자형; ID 원문과 대소문자 보존"
    return None, "혼합값/미확정 형식 가능성 때문에 columnType 생략; 임의 변환하지 않음"


def reserve_name(proposed, existing, prefix, suffix):
    name = proposed
    if name in existing:
        name = prefix + proposed
    if name in existing:
        name = prefix + proposed + "_" + suffix[:8]
    index = 2
    while name in existing:
        name = prefix + proposed + "_" + suffix[:8] + "_" + str(index)
        index += 1
    existing.add(name)
    return name


def native_table(block, sheet_id, unique_key, used_names):
    name = reserve_name("V2T_" + block["file_code"] + "_" + short_hash(unique_key),
                        used_names, "V2_", short_hash(unique_key))
    columns, type_audit = [], []
    seen = set()
    for index, column in enumerate(block["columns"]):
        fid = column["field_id"]
        if fid.casefold() in seen:
            raise ValueError(f"duplicate native-table column: {unique_key}.{fid}")
        seen.add(fid.casefold())
        native_type, reason = type_for(column)
        prop = {"columnIndex": index, "columnName": fid}
        if native_type:
            prop["columnType"] = native_type
        columns.append(prop)
        type_audit.append({"field_id": fid, "declared_type": column["type"],
                           "native_column_type": native_type, "reason": reason})
    table = {
        "name": name,
        "range": grid(sheet_id, block["technical_header_row"] - 1,
                      block["data_end_row"], len(columns)),
        "columnProperties": columns,
        "rowsProperties": {"headerColorStyle": {"rgbColor": GRAY},
                           "firstBandColorStyle": {"rgbColor": WHITE},
                           "secondBandColorStyle": {"rgbColor": WHITE}},
    }
    # Table range begins with exactly one technical header row. The Korean
    # display row precedes it and is deliberately outside the native table.
    return {"addTable": {"table": table}}, name, type_audit


def validate_requests(requests, old_ids, new_properties, permitted_write_rows):
    errors = []
    added = set()
    names = set()
    formula_count = data_value_count = 0
    for index, request in enumerate(requests):
        if len(request) != 1 or next(iter(request)) not in ALLOWED_REQUESTS:
            errors.append(f"request_shape:{index}")
            continue
        kind, body = next(iter(request.items()))
        if kind == "addSheet":
            sid = body["properties"]["sheetId"]
            if sid in old_ids or sid in added:
                errors.append(f"existing_or_duplicate_sheet_id:{sid}")
            added.add(sid)
        if kind == "addNamedRange":
            name = body["namedRange"]["name"]
            if name in names:
                errors.append("duplicate_named_range:" + name)
            names.add(name)
        def ranges(value):
            if isinstance(value, dict):
                if "sheetId" in value and ("startRowIndex" in value or "dimension" in value):
                    yield value
                for item in value.values():
                    yield from ranges(item)
            elif isinstance(value, list):
                for item in value:
                    yield from ranges(item)
        for rect in ranges(body):
            sid = rect["sheetId"]
            if sid in old_ids or sid not in added:
                errors.append(f"uncreated_or_legacy_target:{index}:{sid}")
            props = new_properties[sid]
            if "dimension" in rect:
                bound = props["columnCount"] if rect["dimension"] == "COLUMNS" else props["rowCount"]
                if rect["endIndex"] > bound:
                    errors.append(f"dimension_overflow:{index}")
            else:
                if rect.get("endRowIndex", 0) > props["rowCount"] or rect.get("endColumnIndex", 0) > props["columnCount"]:
                    errors.append(f"range_overflow:{index}")
                if not rect.get("startRowIndex", 0) < rect.get("endRowIndex", props["rowCount"]):
                    errors.append(f"empty_range:{index}")
        if kind == "updateCells":
            rect, rows = body["range"], body["rows"]
            if len(rows) != rect["endRowIndex"] - rect["startRowIndex"]:
                errors.append(f"row_shape:{index}")
            width = rect["endColumnIndex"] - rect["startColumnIndex"]
            for ri, row in enumerate(rows, rect["startRowIndex"]):
                if len(row["values"]) != width:
                    errors.append(f"column_shape:{index}:{ri}")
                for cell in row["values"]:
                    if "formulaValue" in cell.get("userEnteredValue", {}):
                        formula_count += 1
                    if "userEnteredValue" in cell and ri not in permitted_write_rows[rect["sheetId"]]:
                        data_value_count += 1
        if kind == "addTable":
            table = body["table"]
            width = table["range"]["endColumnIndex"] - table["range"]["startColumnIndex"]
            if len(table["columnProperties"]) != width:
                errors.append(f"table_column_shape:{index}")
            for ci, column in enumerate(table["columnProperties"]):
                if column["columnIndex"] != ci:
                    errors.append(f"table_column_index:{index}:{ci}")
                if column.get("columnType") not in {None, "DOUBLE", "BOOLEAN", "TEXT", "DROPDOWN"}:
                    errors.append(f"unsupported_type:{index}:{ci}")
        if kind in {"updateCells", "repeatCell", "updateDimensionProperties"} and not body.get("fields"):
            errors.append(f"missing_field_mask:{index}")
    if formula_count or data_value_count:
        errors.append("business_values_or_formulas_emitted")
    return {"errors": errors, "formula_writes": formula_count,
            "business_data_value_writes": data_value_count,
            "legacy_target_writes": 0 if not any("legacy_target" in x for x in errors) else None,
            "allowed_request_types": sorted(ALLOWED_REQUESTS)}


def build_one(file_layout, initial, outdir, layout_hash, initial_path):
    code, spreadsheet_id = file_layout["file_code"], initial["spreadsheetId"]
    assert code not in SKIP and spreadsheet_id not in V1_IDS
    old = initial["sheets"]
    old_ids = {s["properties"]["sheetId"] for s in old}
    used_ids = set(old_ids)
    used_titles = {s["properties"]["title"] for s in old}
    used_named = {n["name"] for n in initial.get("namedRanges", [])}
    used_table_names = {t["name"] for s in old for t in s.get("tables", [])}
    template_kind = "REG" if code == "C00" or code.startswith("R") else "NAT"
    template_path = ROOT / ("native_template_" + template_kind + ".json")
    template_audit = None
    if template_path.exists():
        template = read(template_path)["updatedSpreadsheet"]
        template_sheets = template["sheets"]
        template_ids = {s["properties"]["sheetId"] for s in template_sheets}
        assert template_ids == old_ids, "Native template ancestry sheet IDs mismatch"
        template_names = {t["name"] for s in template_sheets for t in s.get("tables", [])}
        used_table_names.update(template_names)
        used_named.update(n["name"] for n in template.get("namedRanges", []))
        template_audit = {"path": str(template_path), "sha256": digest(template_path),
                          "ancestry_sheet_id_match": True,
                          "observed_native_table_count": len(template_names),
                          "observed_native_table_names": sorted(template_names),
                          "observed_named_ranges_count": len(template.get("namedRanges", [])),
                          "note": "복사 계보의 native 표 이름과 대조. 적용 직전 목적지 metadata 재확인은 별도."}
    existing_cells = sum(s["properties"].get("gridProperties", {}).get("rowCount", 0) *
                         s["properties"].get("gridProperties", {}).get("columnCount", 0) for s in old)
    new_cells = sum(t["row_count"] * t["column_count"] for t in file_layout["tabs"])
    if existing_cells + new_cells >= MAX_CELLS:
        raise ValueError(f"{code}: allocated cells {existing_cells + new_cells} >= {MAX_CELLS}")
    tab_bindings = []
    for tab in file_layout["tabs"]:
        key = spreadsheet_id + ":" + tab["title"]
        sid = 1_000_000_000 + int(short_hash(key, 8), 16) % 1_000_000_000
        while sid in used_ids:
            sid += 1
        used_ids.add(sid)
        title = reserve_name(tab["title"], used_titles, "V2_", short_hash(key))
        tab_bindings.append({"layout_tab_title": tab["title"], "actual_tab_title": title,
                             "planned_sheet_id": sid, "role": tab["role"],
                             "row_count": tab["row_count"], "column_count": tab["column_count"],
                             "blocks": []})
    name_map = {t["layout_tab_title"]: t for t in tab_bindings}
    groups, permitted_rows = [], collections.defaultdict(set)
    new_properties = {}
    type_audit = []
    for tab, bound in zip(file_layout["tabs"], tab_bindings):
        sid, title = bound["planned_sheet_id"], bound["actual_tab_title"]
        props = {"rowCount": tab["row_count"], "columnCount": tab["column_count"],
                 "frozenRowCount": tab.get("frozen_row_count", 0),
                 "frozenColumnCount": tab.get("frozen_column_count", 0), "hideGridlines": False}
        new_properties[sid] = props
        requests = [{"addSheet": {"properties": {"sheetId": sid, "title": title,
                                                  "sheetType": "GRID", "gridProperties": props}}}]
        width = tab["column_count"]
        # Only authored columns receive widths; original source-copy tabs are untouched.
        requests.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": width},
            "properties": {"pixelSize": 150}, "fields": "pixelSize"}})
        if tab["role"] == "GUIDE":
            rows = [
                [string_cell(code + " · 세계관 데이터 V2"), string_cell("구조 구축 중 · 운영 전환 대기")],
                [string_cell("현재 범위"), string_cell("새 V2 표·헤더·제공 범위 구조만 준비. 이관·수식·검증은 미실행.")],
                [string_cell("원본 보존"), string_cell("기존 V1 원본과 이 파일에 복사된 구판 탭을 구별합니다. 구판 탭은 이번 추가 요청에서 변경하지 않습니다.")],
                [string_cell("기술·표시 헤더"), string_cell("한글 표시행 아래의 기술 헤더 한 행이 입력 표와 제공 범위의 기준입니다.")],
                [string_cell("표의 빈 행"), string_cell("여유 입력 공간입니다. 자료없음·미실행·연결실패를 확정하는 결과가 아닙니다.")],
                [string_cell("상태 구별"), string_cell("0·자료없음·초안·부분합·오류·권한 문제·미실행은 각각 기록합니다.")],
                [string_cell("확장"), string_cell("입력·계산·검증·제공·소비 5개 범위를 함께 갱신하고 경계행을 시험합니다.")],
                [string_cell("확인할 표시명"), string_cell("‘항목 · 원문’ 표시는 한글 의미 검토가 남은 필드이며 정본 설정을 새로 만든 것이 아닙니다.")],
                [string_cell("파일 ID"), string_cell(spreadsheet_id)],
                [string_cell("배치 기준"), string_cell("PH2.PHYSICAL.2 / " + layout_hash)],
                [string_cell("역할"), string_cell("새 V2 탭")],
            ]
            for b in tab_bindings:
                url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={b['planned_sheet_id']}"
                rows.append([string_cell(b["role"]), string_cell(b["actual_tab_title"], link=url)])
            if len(rows) > props["rowCount"]:
                raise ValueError("guide_rows_exceed_layout")
            requests.append(update_rows(sid, 0, rows, "userEnteredValue,note,userEnteredFormat.textFormat.link"))
            permitted_rows[sid].update(range(len(rows)))
            requests.append(repeat_format(grid(sid, 0, len(rows), 2),
                                           {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}))
            requests.append({"updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
                "properties": {"pixelSize": 680}, "fields": "pixelSize"}})
            requests.append(repeat_format(grid(sid, 0, 1, 2),
                                           {"backgroundColorStyle": {"rgbColor": GRAY},
                                            "textFormat": {"bold": True, "foregroundColorStyle": {"rgbColor": BLACK}}}))
        elif not tab["blocks"]:
            # Empty settings surface remains separate from technical/data tables.
            rows = [[string_cell("항목"), string_cell("설정/상태")],
                    [string_cell("구조 상태"), string_cell("구조 요청 준비 · 온라인 검증 미실행")],
                    [string_cell("연결 설정"), string_cell("실제 V2 제공 파일 ID/범위 검증 후 배치")]]
            requests.append(update_rows(sid, 0, rows))
            permitted_rows[sid].update(range(len(rows)))
        for block in tab["blocks"]:
            ident = block.get("logical_table_id") or block["dataset_id"]
            key = code + "." + block["kind"] + "." + ident
            columns = block["columns"]
            n = len(columns)
            assert len({x["field_id"] for x in columns}) == n, key
            title_row = [string_cell(ident + " · " + block["role"] + " · 이관/계산/검증 미실행")]
            requests.append(update_rows(sid, block["block_title_row"] - 1, [title_row]))
            permitted_rows[sid].add(block["block_title_row"] - 1)
            labels = []
            for column in columns:
                note = None
                if column.get("label_semantic_review_required"):
                    note = "한글 의미 확정 전 원문 표기 보존. PH1 명세의 기술 필드와 동일하며 데이터값/설정은 생성하지 않음."
                labels.append(string_cell(column["label_ko"], note))
            technical = [string_cell(c["field_id"], "자료형: " + c["type"] +
                                     (" / 필수키 또는 필수 필드" if c.get("required") else "")) for c in columns]
            requests.append(update_rows(sid, block["display_header_row"] - 1, [labels]))
            requests.append(update_rows(sid, block["technical_header_row"] - 1, [technical]))
            permitted_rows[sid].update({block["display_header_row"] - 1, block["technical_header_row"] - 1})
            actual_named = reserve_name(block["named_range"], used_named, "V2_", short_hash(key))
            rectangle = grid(sid, block["technical_header_row"] - 1, block["data_end_row"], n)
            requests.append({"addNamedRange": {"namedRange": {"name": actual_named, "range": rectangle}}})
            native_name = None
            if block["role"] in {"IN", "CONFIG"} and block["kind"] == "logical_table":
                request, native_name, audit = native_table(block, sid, spreadsheet_id + ":" + key, used_table_names)
                requests.append(request)
                type_audit.append({"logical_table_id": ident, "native_table_name": native_name,
                                   "columns": audit})
            requests.append(repeat_format(grid(sid, block["display_header_row"] - 1,
                                               block["technical_header_row"], n),
                                           {"backgroundColorStyle": {"rgbColor": LIGHT},
                                            "textFormat": {"bold": True, "foregroundColorStyle": {"rgbColor": BLACK}},
                                            "wrapStrategy": "WRAP"}))
            requests.append({"addProtectedRange": {"protectedRange": {
                "range": grid(sid, block["block_title_row"] - 1, block["technical_header_row"], n),
                "description": "V2 기술/표시 헤더 · 변경 시 제공/소비 스키마 동시 갱신", "warningOnly": True}}})
            bb = {
                "kind": block["kind"], "role": block["role"], "logical_table_id": block.get("logical_table_id"),
                "dataset_id": block.get("dataset_id"), "primary_key_fields": block["primary_key_fields"],
                "technical_header_row": block["technical_header_row"], "display_header_row": block["display_header_row"],
                "data_start_row": block["data_start_row"], "data_end_row": block["data_end_row"],
                "data_capacity": block["data_capacity"], "overflow_sentinel_row": block["overflow_sentinel_row"],
                "layout_named_range": block["named_range"], "actual_named_range": actual_named,
                "native_table_name": native_name, "native_table_id": None,
                "grid_range": rectangle,
                "bounded_range": a1(title, block["technical_header_row"], block["data_end_row"], n),
                "data_range": a1(title, block["data_start_row"], block["data_end_row"], n),
                "field_columns": [{"field_id": c["field_id"], "column_index": c["column_index"],
                                   "column_letter": c["column_letter"]} for c in columns],
                "source_tables": block.get("source_tables", []),
                "provider_file_code": block.get("provider_file_code"),
                "binding_status": "예정; 요청 성공/readback 전 실제 생성으로 간주 금지",
            }
            if block["kind"] == "provider":
                bb["export_range"] = bb["bounded_range"]
                bb["export_named_range"] = actual_named
                bb["export_column_ids"] = [c["field_id"] for c in columns]
            bound["blocks"].append(bb)
        if tab["role"] in {"VIEW", "CHECK", "PUB", "REF", "ARCHIVE"}:
            requests.append({"addProtectedRange": {"protectedRange": {
                "range": {"sheetId": sid}, "warningOnly": True,
                "description": "V2 출력/참조/보존 영역 · 직접 입력 전에 관련 범위와 계산/검증 상태 확인"}}})
        if len(requests) > MAX_REQUESTS:
            raise ValueError(f"one tab exceeds chunk budget: {code}/{title}:{len(requests)}")
        groups.append({"sheet_id": sid, "title": title, "requests": requests})
    requests = [r for g in groups for r in g["requests"]]
    audit = validate_requests(requests, old_ids, new_properties, permitted_rows)
    assert not audit["errors"], audit
    chunks, current = [], {"requests": [], "new_sheets": []}
    for group in groups:
        if current["requests"] and len(current["requests"]) + len(group["requests"]) > MAX_REQUESTS:
            chunks.append(current)
            current = {"requests": [], "new_sheets": []}
        current["requests"].extend(group["requests"])
        current["new_sheets"].append({"sheet_id": group["sheet_id"], "title": group["title"]})
    if current["requests"]:
        chunks.append(current)
    for index, chunk in enumerate(chunks, 1):
        chunk.update({"chunk_id": f"{code}-STRUCT-{index:03d}", "sequence": index,
                      "request_count": len(chunk["requests"]),
                      "precondition": "이 chunk의 new_sheets ID/title이 대상에 없어야 함. 존재하면 자동 재시도하지 말고 응답/현상태와 대조.",
                      "write_status": "미실행"})
    bindings = {
        "file_code": code, "spreadsheet_id": spreadsheet_id,
        "layout_version": "PH2.PHYSICAL.2", "layout_sha256": layout_hash,
        "existing_sheet_ids_preserved": sorted(old_ids), "tabs": tab_bindings,
        "planned_not_observed": True, "formula_or_business_data_written": False,
        "initial_metadata_path": str(initial_path), "initial_metadata_sha256": digest(initial_path),
        "cells": {"existing": existing_cells, "new": new_cells, "planned_total": existing_cells + new_cells,
                  "limit": MAX_CELLS, "below_limit": existing_cells + new_cells < MAX_CELLS},
        "type_audit": type_audit,
        "native_template_collision_basis": template_audit,
    }
    summary = {
        "file_code": code, "spreadsheet_id": spreadsheet_id, "new_sheet_count": len(tab_bindings),
        "legacy_sheet_count": len(old), "new_native_table_count": len(type_audit),
        "new_named_range_count": sum(len(t["blocks"]) for t in tab_bindings),
        "request_count": len(requests), "chunk_count": len(chunks),
        "max_chunk_requests": max(c["request_count"] for c in chunks),
        "type_counts": dict(collections.Counter(c["native_column_type"] or "UNSPECIFIED" for t in type_audit for c in t["columns"])),
        "cells": bindings["cells"], "static_preflight": audit,
    }
    bundle = {
        "bundle_version": "PH2.STRUCTURE.1", "status": "요청 생성/정적 검증만 완료 · 온라인 미실행",
        "file_code": code, "spreadsheet_id": spreadsheet_id,
        "initial_metadata_sha256": digest(initial_path), "physical_layout_sha256": layout_hash,
        "bindings_file": code + ".binding.json", "summary": summary,
        "execution_contract": {
            "connector": "google_drive_batch_update_spreadsheet",
            "requests_argument": "chunks[sequence-1].requests",
            "spreadsheet_id_argument": "spreadsheet_id",
            "execute_in_order": True, "max_requests_per_call": MAX_REQUESTS,
            "refresh_metadata_before_first_chunk": True,
            "existing_table_and_named_range_snapshot_omission": "initial_native 스냅샷에 tables/namedRanges가 없으면 부재를 뜻하지 않음. 적용 전 native metadata와 대조; 충돌 시 이 binding만 갱신하고 원문은 보존.",
            "idempotency": "자체 request ID는 기록용이며 Google의 멱등키가 아니다. 불명확 응답 뒤 재전송 금지; planned sheet ID/title 및 table/name range의 readback으로 완료 여부 확정.",
            "native_tables": "각 input/config 표 기술 헤더 한 행부터 capacity 마지막 데이터행까지. 한글 표시행은 표 밖에 보존. tableId는 서버 응답으로 기록.",
            "warning_protection_only": True,
            "no_sheet_delete_or_legacy_mutation": True,
            "no_formula_rollout": True,
            "readback_required": ["new sheet IDs/titles/dimensions", "all technical and display header cells", "tables range/columnProperties/types", "namedRanges bounds", "warningOnly protection", "no authored data/formulas", "legacy IDs/counts unchanged"],
        },
        "chunks": chunks,
    }
    dump(outdir / (code + ".json"), bundle)
    dump(outdir / (code + ".binding.json"), bindings)
    return summary, bindings


def expansion_registry(bindings, layout):
    files = {b["file_code"]: b for b in bindings}
    block_index, pubs, refs = {}, {}, []
    for binding in bindings:
        for tab in binding["tabs"]:
            for block in tab["blocks"]:
                location = {"file_code": binding["file_code"], "spreadsheet_id": binding["spreadsheet_id"],
                            "tab_title": tab["actual_tab_title"], "sheet_id": tab["planned_sheet_id"],
                            "kind": block["kind"], "role": block["role"], "logical_table_id": block["logical_table_id"],
                            "dataset_id": block["dataset_id"], "named_range": block["actual_named_range"],
                            "bounded_range": block["bounded_range"], "data_range": block["data_range"],
                            "data_capacity": block["data_capacity"], "native_table_name": block["native_table_name"]}
                if block["kind"] == "logical_table":
                    block_index[binding["file_code"], block["logical_table_id"]] = (block, location)
                elif block["kind"] == "provider":
                    pubs[block["dataset_id"]] = (block, location)
                else:
                    refs.append((block, location))
    bundles = []
    for (code, table), (block, location) in block_index.items():
        if block["role"] not in {"IN", "CONFIG"}:
            continue
        provider_matches = [(b, loc) for b, loc in pubs.values() if loc["file_code"] == code and table in b["source_tables"]]
        related = {table}
        for provider, _ in provider_matches:
            related.update(provider["source_tables"])
        base = re.sub(r"^IN_", "", table)
        calculations = [loc for (fc, tid), (b, loc) in block_index.items() if fc == code and b["role"] == "VIEW" and
                        (tid in related or tid in {"CALC_" + base, table + "_조회계산", table + "_계산"})]
        checks = [loc for (fc, tid), (b, loc) in block_index.items() if fc == code and b["role"] == "CHECK" and
                  (tid in {"CHECK_RESULTS", "CHECK_" + base} or tid in related)]
        provided = {b["dataset_id"] for b, _ in provider_matches}
        consumers = [loc for b, loc in refs if b["dataset_id"] in provided]
        bundles.append({"owner_file_code": code, "logical_table_id": table,
                        "input": [location], "calculation": calculations, "validation": checks,
                        "publication": [loc for _, loc in provider_matches], "consumption": consumers,
                        "mapping_basis": "provider source_tables와 동일 원천 계산표; CHECK_<base> 및 소유 CHECK_RESULTS. 빈 목록은 기능/수식 배치 전에 추가 계약 점검 필요이며 완료가 아님.",
                        "before_expansion": ["same-tab downstream blocks shift calculation", "native table range", "all named ranges", "validation/protection", "all provider/consumer ranges", "grid dimensions and cell limit"],
                        "native_boundary_test_status": "미실행"})
    remaining = []
    for f in layout["files"]:
        if f["file_code"] in SKIP:
            remaining.append({"file_code": f["file_code"], "reason": "다른 담당자의 artifact 생성/실제 binding 이후 합류", "planned_tabs": len(f["tabs"])})
    return {"status": "5범위 확장 주소 대응 설계; 수식/온라인 시험 미실행", "files_excluded": remaining,
            "input_expansion_bundles": bundles,
            "cross_file_refs": [{"consumer": loc, "provider": pubs[b["dataset_id"]][1] if b["dataset_id"] in pubs else
                                 {"dataset_id": b["dataset_id"], "file_code": b["provider_file_code"], "status": "external_artifact_binding_pending"}}
                                for b, loc in refs]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "structure_requests")
    args = parser.parse_args()
    layout_path = ROOT / "physical_layout.json"
    layout = read(layout_path)
    assert layout["layout_version"] == "PH2.PHYSICAL.2", "Re-review builder when layout version changes"
    summaries, bindings = [], []
    for file_layout in layout["files"]:
        code = file_layout["file_code"]
        if code in SKIP:
            continue
        initial_path = ROOT / f"initial_native_{code}.json"
        summary, binding = build_one(file_layout, read(initial_path), args.output_dir, digest(layout_path), initial_path)
        summaries.append(summary)
        bindings.append(binding)
    dump(args.output_dir / "expansion_bindings.json", expansion_registry(bindings, layout))
    report = {
        "status": "로컬 구조 요청 생성·정적 검증 완료; 온라인 API 수락/생성/시험 미실행",
        "source": {"physical_layout": str(layout_path), "sha256": digest(layout_path)},
        "api_reference_sources": API_SOURCES,
        "excluded_file_codes": sorted(SKIP), "files": summaries,
        "totals": {"file_count": len(summaries),
                   "new_sheets": sum(s["new_sheet_count"] for s in summaries),
                   "new_native_tables": sum(s["new_native_table_count"] for s in summaries),
                   "new_named_ranges": sum(s["new_named_range_count"] for s in summaries),
                   "requests": sum(s["request_count"] for s in summaries),
                   "chunks": sum(s["chunk_count"] for s in summaries),
                   "max_chunk_requests": max(s["max_chunk_requests"] for s in summaries),
                   "max_target_cells_including_legacy": max(s["cells"]["planned_total"] for s in summaries),
                   "static_errors": sum(len(s["static_preflight"]["errors"]) for s in summaries),
                   "formula_writes": 0, "business_data_writes": 0, "legacy_target_writes": 0},
        "legacy_cleanup": {"status": "이번 요청에서 제외", "plan": "복사된 구판의 native table/validation/수식/서식 보존 검증 후 별도 목록으로 정리 여부 결정; deleteSheet/deleteDimension/rename 요청 없음"},
    }
    dump(args.output_dir / "validation_summary.json", report)
    print(json.dumps(report["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
