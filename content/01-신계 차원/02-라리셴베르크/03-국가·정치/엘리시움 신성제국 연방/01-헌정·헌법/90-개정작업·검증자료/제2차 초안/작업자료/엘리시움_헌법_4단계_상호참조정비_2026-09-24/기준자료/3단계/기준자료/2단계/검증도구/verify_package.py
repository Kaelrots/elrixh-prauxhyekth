#!/usr/bin/env python3
"""Verify the stage-2 constitution rearrangement package offline.

Only Python's standard library is used. No file is edited by this script.
This verifies copying, source mapping and hierarchy preservation, not the
substantive correctness of a constitution or unresolved legal references.

Usage:
    python verify_package.py
    python verify_package.py /path/to/unpacked/package
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


class VerificationError(Exception):
    """Raised when a preservation or mapping invariant is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = root / '04_재배치_매니페스트.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    source = manifest['source']
    source_path = root / '기준자료' / source['filename']
    original = source_path.read_bytes()
    source_lines = original.decode('utf-8').splitlines(keepends=True)
    require(digest(original) == source['sha256'], '기준자료 SHA-256 불일치')
    require(len(original) == source['bytes'], '기준자료 바이트 수 불일치')
    require(len(source_lines) == source['lines'], '기준자료 행 수 불일치')

    line_cache: dict[str, list[str]] = {}

    def safe_path(relative: str) -> Path:
        path = (root / relative).resolve()
        require(path.is_relative_to(root), f'패키지 외부 경로 금지: {relative}')
        return path

    def lines(relative: str) -> list[str]:
        if relative not in line_cache:
            line_cache[relative] = safe_path(relative).read_bytes().decode('utf-8').splitlines(keepends=True)
        return line_cache[relative]

    def extract(relative: str, start: int, end: int) -> bytes:
        text = lines(relative)
        require(1 <= start <= end <= len(text), f'파일 행 범위 오류: {relative}:{start}-{end}')
        return ''.join(text[start - 1:end]).encode('utf-8')

    def original_span(start: int, end: int) -> bytes:
        require(1 <= start <= end <= len(source_lines), f'원문 행 범위 오류: {start}-{end}')
        return ''.join(source_lines[start - 1:end]).encode('utf-8')

    # Independently reconstruct the entire input from the *actual* output files.
    cursor = 1
    restored_parts: list[bytes] = []
    destination_used: dict[str, set[int]] = {}
    partition = sorted(manifest['preservation_partition'], key=lambda x: x['source_start_line'])
    require(len({x['id'] for x in partition}) == len(partition), '보존 분할 ID 중복')
    for item in partition:
        start, end = item['source_start_line'], item['source_end_line']
        require(start == cursor, f'원문 보존 범위 누락 또는 중복: 기대 {cursor}, 실제 {start}')
        relative = item['destination_file']
        out_start, out_end = item['destination_start_line'], item['destination_end_line']
        require(end - start == out_end - out_start, f'원문/출력 행 수 차이: {item["id"]}')
        assigned = destination_used.setdefault(relative, set())
        occupied = set(range(out_start, out_end + 1))
        require(not assigned.intersection(occupied), f'같은 출력 원문 범위의 이중 사용: {item["id"]}')
        assigned.update(occupied)
        payload = extract(relative, out_start, out_end)
        require(digest(payload) == item['content_sha256'], f'보존 블록 해시 불일치: {item["id"]}')
        require(payload == original_span(start, end), f'보존 블록 본문 차이: {item["id"]}')
        restored_parts.append(payload)
        cursor = end + 1
    require(cursor == len(source_lines) + 1, '원문 말미 누락')
    reconstructed = b''.join(restored_parts)
    require(reconstructed == original, '원문 전체 바이트 역복원 실패')

    # Verify every article block and native subordinate hierarchy against input.
    units = manifest['source_units']
    unit_map = {u['source_id']: u for u in units}
    require(len(unit_map) == len(units), '원 조문 ID 중복')
    blocks = manifest['placement_blocks']
    block_map = {b['block_id']: b for b in blocks}
    require(len(block_map) == len(blocks), '배치 블록 ID 중복')
    require(sorted(b['placement_order'] for b in blocks) == list(range(1, len(blocks) + 1)), '배치 순번 오류')
    require(len({b['working_anchor'] for b in blocks}) == len(blocks), '작업본 앵커 중복')
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for b in blocks:
        sid = b['source_unit_id']
        require(sid in unit_map, f'알 수 없는 원 조문: {sid}')
        by_unit.setdefault(sid, []).append(b)
        payload = extract(b['working_file'], b['working_start_line'], b['working_end_line'])
        require(payload == original_span(b['source_start_line'], b['source_end_line']), f'배치 본문 변조: {b["block_id"]}')
        require(digest(payload) == b['content_sha256'], f'배치 해시 불일치: {b["block_id"]}')
        require(b['new_article_number'] is None and b['new_paragraph_number'] is None, '2단계에서 새 조문 번호가 입력됨')
        chapter = manifest['structure'].get(str(b['destination_chapter']))
        require(chapter is not None, f'없는 새 장: {b["destination_chapter"]}')
        require(1 <= b['destination_section'] <= len(chapter['sections']), f'없는 새 절: {b["block_id"]}')
        file_text = ''.join(lines(b['working_file']))
        require(len(re.findall(r'^\^' + re.escape(b['working_anchor']) + r'\s*$', file_text, re.M)) == 1,
                f'추적 앵커 누락/중복: {b["working_anchor"]}')
    require(set(by_unit) == set(unit_map), '배치되지 않은 원 조문/부칙 있음')
    split_article_ids: set[str] = set()
    for sid, u in unit_map.items():
        ordered = sorted(by_unit[sid], key=lambda b: b['source_start_line'])
        unit_cursor = u['start']
        for b in ordered:
            require(b['source_start_line'] == unit_cursor, f'원 조문 분할 불연속: {sid}')
            unit_cursor = b['source_end_line'] + 1
        require(unit_cursor == u['end'] + 1, f'원 조문 마지막 부분 누락: {sid}')
        require(digest(original_span(u['start'], u['end'])) == u['sha256'], f'원 조문 해시 불일치: {sid}')
        if u['kind'] == 'article' and len(ordered) > 1:
            split_article_ids.add(sid)

    nodes = manifest['source_nodes']
    node_map = {n['node_id']: n for n in nodes}
    require(len(node_map) == len(nodes), '조항호목 추적 ID 중복')
    for n in nodes:
        nid = n['node_id']
        require(n['source_unit_id'] in unit_map, f'단위의 원 조문 없음: {nid}')
        parent = n['parent']
        if parent is not None:
            require(parent in node_map, f'단위의 부모 없음: {nid}')
            p = node_map[parent]
            require(p['start'] <= n['start'] <= n['end'] <= p['end'], f'부모/자식 원문 범위 오류: {nid}')
        ordered_spans = sorted(n['working_spans'], key=lambda s: s['source_start_line'])
        node_parts: list[bytes] = []
        nc = n['start']
        for s in ordered_spans:
            require(s['source_start_line'] == nc, f'계층 단위 분할 불연속: {nid}')
            require(s['block_id'] in block_map, f'계층 단위 배치 블록 없음: {nid}')
            b = block_map[s['block_id']]
            node_parts.append(extract(b['working_file'], s['working_start_line'], s['working_end_line']))
            nc = s['source_end_line'] + 1
        require(nc == n['end'] + 1, f'계층 단위 말미 누락: {nid}')
        payload = b''.join(node_parts)
        require(payload == original_span(n['start'], n['end']), f'항·호·목 등 원문 차이: {nid}')
        require(digest(payload) == n['content_sha256'], f'계층 단위 해시 불일치: {nid}')
        require(n['new_article_number'] is None and n['new_local_number'] is None, '하위단위 신번호가 이미 확정됨')

    # Check the named chapter/section skeleton and TSV mirrors.
    section_pairs = [(s['chapter'], s['section']) for s in manifest['sections']]
    expected_pairs = [(int(c), i + 1) for c, v in manifest['structure'].items() for i in range(len(v['sections']))]
    require(Counter(section_pairs) == Counter(expected_pairs), '장·절 구조 누락 또는 중복')
    main_lines = lines('01_헌법_장절_재배치_작업본.md')
    for s in manifest['sections']:
        heading = main_lines[s['working_file_heading_line'] - 1].strip()
        require(heading == f'## 제{s["section"]}절 {s["title"]}', f'절 표제 불일치: {s["chapter"]}-{s["section"]}')
        count = sum(b['destination_chapter'] == s['chapter'] and b['destination_section'] == s['section'] for b in blocks)
        require(count == s['block_count'], f'절별 블록 집계 불일치: {s["chapter"]}-{s["section"]}')

    def tsv(relative: str) -> list[dict[str, str]]:
        with safe_path(relative).open(encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f, delimiter='\t'))

    block_rows = tsv('02a_블록_배치대장.tsv')
    require(len(block_rows) == len(blocks), '블록 TSV 행 수 불일치')
    require({r['블록_ID'] for r in block_rows} == set(block_map), '블록 TSV ID 불일치')
    detail_rows = tsv('03_조항호목_상세배치대장.tsv')
    require(len(detail_rows) == len(nodes), '상세 TSV 행 수 불일치')
    require({r['추적_ID'] for r in detail_rows} == set(node_map), '상세 TSV ID 불일치')
    require(all(not r['새조문번호'] and not r['새항호목번호'] for r in detail_rows), 'TSV 신번호 열이 비어 있지 않음')
    references = tsv(manifest['unresolved_reference_inventory_file'])
    require(len(references) == manifest['reference_token_occurrences'], '참조 문자열 집계 불일치')
    for r in references:
        row = int(r['원문행'])
        original_line = source_lines[row - 1].rstrip('\r\n')
        require(r['원문참조표기'] in original_line, f'참조 원문 문자열 없음: {r["참조_ID"]}')
        require(r['배치블록_ID'] in block_map, f'참조 배치 블록 없음: {r["참조_ID"]}')

    # Check stage-2 metadata and the stored count summary, without trusting it.
    actual_articles = sum(u['kind'] == 'article' for u in units)
    require(actual_articles == manifest['checks']['article_count'], '조문 개수 집계 불일치')
    require(len(split_article_ids) == manifest['checks']['split_article_count'], '분할 조문 집계 불일치')
    require(len(blocks) == manifest['checks']['placement_block_count'], '배치 블록 집계 불일치')
    require(manifest['stage'] == 2, '작업단계 표시가 2가 아님')
    require(source_path.read_bytes() == original, '검증 과정에서 기준자료 변경됨')

    return {
        '검증결과': '통과',
        '검증범위': '원문 복사·역복원·계층 추적·장절 배치 구조. 내용개정 또는 법적 정합성 검증 아님.',
        '기준원문_SHA256': source['sha256'],
        '역복원_SHA256': digest(reconstructed),
        '바이트단위_원문역복원': True,
        '원문행수': len(source_lines),
        '원문바이트수': len(original),
        '전체조문수': actual_articles,
        '분할조문수': len(split_article_ids),
        '배치블록수': len(blocks),
        '계층추적단위수': len(nodes),
        '본문장수': len(manifest['structure']) - 1,
        '총강절수': len(manifest['structure']['0']['sections']),
        '본문절수': sum(len(v['sections']) for k, v in manifest['structure'].items() if k != '0'),
        '미배치원문행': 0,
        '중복복사원문행': 0,
        '내용변경원문행': 0,
        '상호참조후속점검_문자열수': len(references),
        '새조항호목번호_미확정': True,
        '검증실행의_기준자료변경': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', nargs='?', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = verify(args.package)
    except (VerificationError, OSError, UnicodeError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        print(json.dumps({'검증결과': '실패', '오류': str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
