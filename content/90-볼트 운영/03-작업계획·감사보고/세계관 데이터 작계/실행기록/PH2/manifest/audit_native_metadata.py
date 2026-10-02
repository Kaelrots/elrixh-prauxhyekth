"""Offline comparison only. Re-run after final native response snapshots arrive."""
import datetime
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def native(value):
    if not isinstance(value, dict):
        return None
    if "sheets" in value and "spreadsheetId" in value:
        return value
    for key in ("updatedSpreadsheet", "structuredContent", "response", "metadata"):
        found = native(value.get(key))
        if found:
            return found
    return None


def rectangle(value):
    return {k: value.get(k, 0) for k in ("sheetId", "startRowIndex", "endRowIndex", "startColumnIndex", "endColumnIndex")}


def covers(outer, inner):
    return outer.get("sheetId") == inner.get("sheetId") and all(
        outer.get(start, 0) <= inner.get(start, 0) and outer.get(end, 10**9) >= inner.get(end, 10**9)
        for start, end in (("startRowIndex", "endRowIndex"), ("startColumnIndex", "endColumnIndex")))


def main():
    expected = load(HERE / "expected_native_metadata.json")["files"]
    layouts = {f["file_code"]: f for f in load(BASE / "physical_layout.json")["files"]}
    results = []
    for ex in expected:
        code = ex["file_code"]
        candidates = [BASE / "structure_compat" / f"native_after_structure_{code}.json",
                      BASE / f"finish_native_{code}.json"]
        if code in {"C00", "R10"}:
            candidates = [BASE / "input_execution" / f"final_native_{code}.json", BASE / "input_execution" / f"final_ui_{code}.json"] + candidates
        evidence = next((p for p in candidates if p.exists()), None)
        if not evidence:
            results.append({"file_code": code, "status": "unverified", "reason": "최종 native metadata 응답 파일 미도착", "expected_paths": [str(p) for p in candidates]})
            continue
        actual = native(load(evidence))
        if actual is None:
            results.append({"file_code": code, "status": "unverified", "reason": "updatedSpreadsheet 미포함", "evidence": str(evidence)})
            continue
        errors = []
        supplemental_evidence = []
        final_native_verified = True
        if code in {"C00", "R10"} and "namedRanges" not in actual:
            earlier_path = BASE / "input_requests" / f"table_preflight_{code}.json"
            if earlier_path.exists():
                earlier = native(load(earlier_path))
                latest_props = {s["properties"]["sheetId"]: s for s in actual["sheets"]}
                earlier_sheets = {s["properties"]["sheetId"]: s for s in earlier["sheets"]}
                for sid, latest in latest_props.items():
                    if sid in earlier_sheets:
                        earlier_sheets[sid]["properties"] = latest["properties"]
                    else:
                        earlier_sheets[sid] = latest
                earlier["sheets"] = list(earlier_sheets.values())
                actual = earlier
                supplemental_evidence.append(str(evidence))
                evidence = earlier_path
                final_native_verified = False
        native_sections_available = "namedRanges" in actual and any("tables" in s for s in actual["sheets"])
        sheets = {s["properties"]["sheetId"]: s for s in actual["sheets"]}
        if code == "H90" and (BASE / "H90_directory_readback.json").exists():
            directory_path = BASE / "H90_directory_readback.json"
            directory = native(load(directory_path))
            for sheet in directory["sheets"]:
                if sheet["properties"]["sheetId"] == 1100202602:
                    sheets[1100202602] = sheet
                    supplemental_evidence.append(str(directory_path))
        tables = [t for s in actual["sheets"] for t in s.get("tables", [])]
        byname = {t["name"]: t for t in tables}
        named = {n["name"]: n for n in actual.get("namedRanges", [])}
        planned = {t["title"]: t for t in layouts[code]["tabs"]}
        for t in ex["tabs"]:
            s = sheets.get(t["sheet_id"], {})
            props = s.get("properties", {})
            gp = props.get("gridProperties", {})
            intended = planned[t["title"]]
            if props.get("title") != t["title"]:
                errors.append({"kind": "sheet_id_title", "tab": t["title"]})
            # Imported N60/N70 initial grids were larger; native finishing is
            # allowed to shrink them to the approved layout's reserved bounds.
            if gp.get("rowCount", 0) < intended["row_count"] or gp.get("columnCount", 0) < intended["column_count"]:
                errors.append({"kind": "grid_below_layout", "tab": t["title"]})
            if props.get("hidden", False):
                errors.append({"kind": "new_tab_hidden", "tab": t["title"]})
            if t["role"] == "GUIDE" and props.get("index") != 0:
                errors.append({"kind": "guide_index", "actual": props.get("index")})
            if native_sections_available and t["role"] in {"VIEW", "CHECK", "PUB", "REF", "ARCHIVE"}:
                blocks = [n["range"] for n in ex["named_ranges"] if n["range"]["sheetId"] == t["sheet_id"]]
                if not blocks or not all(any(p.get("warningOnly") and covers(p["range"], block) for p in s.get("protectedRanges", [])) for block in blocks):
                    errors.append({"kind": "output_warning_protection", "tab": t["title"]})
        for n in ex["named_ranges"] if native_sections_available else []:
            a = named.get(n["name"])
            if not a or rectangle(a["range"]) != rectangle(n["range"]):
                errors.append({"kind": "named_range", "name": n["name"]})
        observed_tables = []
        for t in ex["native_tables"] if native_sections_available else []:
            if t.get("name"):
                a = byname.get(t["name"])
            else:
                matches = [v for v in tables if rectangle(v["range"]) == rectangle(t["range"])]
                a = matches[0] if len(matches) == 1 else None
            if not a:
                errors.append({"kind": "native_table_missing_or_ambiguous", "name": t.get("name"), "table": t.get("logical_table_id")})
                continue
            if rectangle(a["range"]) != rectangle(t["range"]) or (t.get("tableId") and str(a["tableId"]) != str(t["tableId"])):
                errors.append({"kind": "native_id_or_range", "name": a["name"]})
            ac = {c.get("columnIndex", 0): c for c in a.get("columnProperties", [])}
            if len(ac) != len(t["columns"]):
                errors.append({"kind": "native_column_count", "name": a["name"]})
            for c in t["columns"]:
                v = ac.get(c["columnIndex"], {})
                if v.get("columnName") != c["columnName"]:
                    errors.append({"kind": "native_column_name", "table": a["name"], "field": c["columnName"]})
                if "columnType" in c:
                    et, at = c["columnType"], v.get("columnType")
                    if et != at and not (et is None and at == "COLUMN_TYPE_UNSPECIFIED"):
                        errors.append({"kind": "native_type", "table": a["name"], "field": c["columnName"], "expected": et, "actual": at})
                if v.get("columnType") == "BOOLEAN":
                    errors.append({"kind": "empty_structure_boolean_declaration", "table": a["name"], "field": c["columnName"]})
            observed_tables.append({"name": a["name"], "tableId": a["tableId"], "range": a["range"], "column_count": len(ac)})
        for old in ex["legacy_sheets_preserved"]:
            s = sheets.get(old["sheet_id"], {})
            prop = s.get("properties", {})
            gp = prop.get("gridProperties", {})
            if prop.get("title") != old["title"] or gp.get("rowCount") != old["row_count"] or gp.get("columnCount") != old["column_count"]:
                errors.append({"kind": "legacy_id_title_grid_changed", "sheet_id": old["sheet_id"]})
            if not prop.get("hidden", False):
                errors.append({"kind": "legacy_not_hidden", "sheet_id": old["sheet_id"]})
        old_native_count = 0
        if native_sections_available and ex["legacy_sheets_preserved"]:
            source_kind = "REG" if code == "C00" or code.startswith("R") else "NAT"
            template = native(load(BASE / f"native_template_{source_kind}.json"))
            for s in template["sheets"]:
                sid = s["properties"]["sheetId"]
                if s.get("tables", []) != sheets.get(sid, {}).get("tables", []):
                    errors.append({"kind": "legacy_native_table_metadata_changed", "sheet_id": sid})
                old_native_count += len(s.get("tables", []))
        planned_ids = {x["sheet_id"] for x in ex["tabs"] + ex["legacy_sheets_preserved"]}
        extras = [s["properties"] for sid, s in sheets.items() if sid not in planned_ids]
        allowed_extra = {1235509559} if code == "C00" else {1100202602} if code == "H90" else set()
        for extra in extras:
            if extra["sheetId"] not in allowed_extra:
                errors.append({"kind": "unexpected_extra_tab", "sheet_id": extra["sheetId"]})
        results.append({"file_code": code, "status": "fail" if errors else "pass" if native_sections_available and final_native_verified else "partial", "evidence": str(evidence),
                        "supplemental_evidence": supplemental_evidence, "known_extra_tabs": extras,
                        "native_sections_available": native_sections_available,
                        "native_metadata_epoch": "final structure response" if final_native_verified else "입력 전 table_preflight; 최신 시트 속성은 final_ui로 별도 확인. 입력 후 native 정보 재조회는 미확인",
                        "unverified_checks": [] if native_sections_available and final_native_verified else ["입력 후 native table IDs/ranges/types", "입력 후 namedRanges", "입력 후 output warning protections", "입력 후 legacy native table metadata"],
                        "spreadsheet_id": actual["spreadsheetId"], "total_tabs_observed": len(sheets),
                        "planned_new_tabs_checked": len(ex["tabs"]), "native_tables_checked": len(ex["native_tables"]) if native_sections_available else 0,
                        "named_ranges_checked": len(ex["named_ranges"]) if native_sections_available else 0, "legacy_tabs_hidden": len(ex["legacy_sheets_preserved"]),
                        "legacy_native_tables_unchanged": old_native_count, "observed_native_tables": observed_tables, "errors": errors})
    read_path = HERE / "native_read_verification.json"
    cell = load(read_path) if read_path.exists() else None
    report = {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "최종 저장 native metadata 대조; 업무기능/연결/권한/재계산/84시험 통과 아님", "files": results,
              "summary": {"files": len(results), "pass": sum(x["status"] == "pass" for x in results),
                          "fail": sum(x["status"] == "fail" for x in results), "unverified": sum(x["status"] == "unverified" for x in results),
                          "partial": sum(x["status"] == "partial" for x in results),
                          "base_tabs_checked": sum(x.get("planned_new_tabs_checked", 0) for x in results),
                          "known_extra_tabs": sum(len(x.get("known_extra_tabs", [])) for x in results),
                          "errors": sum(len(x.get("errors", [])) for x in results),
                          "new_native_tables_checked": sum(x.get("native_tables_checked", 0) for x in results),
                          "named_ranges_checked": sum(x.get("named_ranges_checked", 0) for x in results)},
              "separate_cell_verification": {"path": str(read_path), "read_calls_present": cell.get("read_calls_present") if cell else None,
                                             "technical_error_count": len(cell.get("technical_errors", [])) if cell else None,
                                             "technical_header_cells": sum(x["technical_header_cells"] for x in cell["per_file"].values()) if cell else None},
              "checklist_result_unchanged": True}
    pending_receipt = BASE / "input_execution" / "021_C00_pending_sheet.receipt.json"
    if pending_receipt.exists():
        def find_table(value):
            if isinstance(value, dict):
                if str(value.get("tableId")) == "177074261" and "range" in value:
                    return value
                for item in value.values():
                    result = find_table(item)
                    if result:
                        return result
            elif isinstance(value, list):
                for item in value:
                    result = find_table(item)
                    if result:
                        return result
            return None
        pending = find_table(load(pending_receipt))
        report["known_extra_native_table"] = {"file_code": "C00", "evidence": str(pending_receipt),
            "evidence_kind": "addTable success response; excluded from 108 base-table comparisons",
            "table": pending, "final_native_readback": "unverified"}
    (HERE / "structure_metadata_audit_16.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    print(json.dumps([{"file": x["file_code"], "errors": x.get("errors", []), "status": x["status"]} for x in results if x["status"] != "pass"], ensure_ascii=False))


if __name__ == "__main__":
    main()
