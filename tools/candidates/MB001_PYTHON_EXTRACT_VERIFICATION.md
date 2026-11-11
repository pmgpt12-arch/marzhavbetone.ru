# MB001 Python quoted baseline extraction — issue #332

Historical navigation preparation only; no product, pricing or legal conclusion.

Source: PR #293, `fdd643e1cbc94a0ed975f2280433df4769647a71`, `tools/candidates/MB001_PRODUCT_REPACKAGING_MATRIX.md`. Complete UTF-8 source: 60,947 bytes, 290 lines; Git blob `2a12297c9ffeba6ff5aed3c9f8f711b8d8ab7c39` verified from exact bytes.

Python3 executed once in the ChatGPT execution workspace, not ai-workstation. No LLM API invocation occurred in the extraction process. Coordinator source retrieval and GitHub publication use MCP; they are not extraction inference. Execution time: 0.00129623 sec, below 180-second bound.

Output: 10 records, only P2/P3/P4/P7, all historical=true; exact whole-row quotes and one-based inclusive line ranges. Four main SKU table rows have defect_id=null; six rows carry explicit source IDs. Selection uses primary SKU column in sections 1/3, or a single explicitly named primary SKU location in section6. Mixed/indirect SKU locations are preserved in the proof manual-review list instead of assigned by inference. These quotes intentionally preserve historical prices and statements; none are treated as current decisions or readiness.

Checks: source Git blob PASS; exact schema, <=25 records, eligible SKU, fixed commit SHA, IDs, historical marker and source line equality PASS. Negative cases: modified quote, nonexistent line, wrong SHA, wrong SKU and historical=false all rejected.

Reproduction: run the Python script embedded below with the full immutable source saved as source.md beside it. It uses only stdlib; no network, model client, subprocess or repair loop.

Status: narrow extraction verified; product audits and price/release gates remain independent.

```python
import copy, hashlib, json, re, time
from pathlib import Path

START = time.monotonic()
SHA = 'fdd643e1cbc94a0ed975f2280433df4769647a71'
BLOB = '2a12297c9ffeba6ff5aed3c9f8f711b8d8ab7c39'
SOURCE_PATH = 'tools/candidates/MB001_PRODUCT_REPACKAGING_MATRIX.md'
ALLOWED = {'P2', 'P3', 'P4', 'P7'}
root = Path(__file__).parent
raw = (root / 'source.md').read_bytes()
assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == BLOB
lines = raw.decode().splitlines()
records, manual = [], []
section = None
for n, line in enumerate(lines, 1):
    heading = re.match(r'^## (\d+)\.', line)
    if heading:
        section = int(heading[1])
    if not line.startswith('|') or section not in (1, 3, 6):
        continue
    cells = [c.strip() for c in line.split('|')[1:-1]]
    if section == 1:
        m = re.fullmatch(r'\*\*(p\d+)\*\*', cells[0])
        if not m or m[1].upper() not in ALLOWED:
            continue
        sku, defect = m[1].upper(), None
    elif section == 3:
        if not re.fullmatch(r'D-\d+', cells[0]):
            continue
        if not re.fullmatch(r'p\d+', cells[1]):
            if ALLOWED & {s.upper() for s in re.findall(r'\bp\d+\b', cells[1], re.I)}:
                manual.append({'line': n, 'reason': 'SKU column is not a single explicit SKU', 'exact_quote': line})
            continue
        sku, defect = cells[1].upper(), cells[0]
        if sku not in ALLOWED:
            continue
    else:
        if not re.fullmatch(r'S-\d+', cells[0]):
            continue
        skus = {s.upper() for s in re.findall(r'\bp\d+\b', cells[1], re.I)}
        if not ALLOWED & skus:
            continue
        if len(skus) != 1 or not re.match(r'^p\d+\b', cells[1], re.I):
            manual.append({'line': n, 'reason': 'Location does not identify one explicit primary SKU', 'exact_quote': line})
            continue
        sku, defect = next(iter(skus)), cells[0]
    records.append({'sku': sku, 'defect_id': defect, 'exact_quote': line,
                    'source_path': SOURCE_PATH, 'source_sha': SHA,
                    'start_line': n, 'end_line': n, 'historical': True})

expected_source_rows = {(r['start_line'], r['end_line']): (r['sku'], r['defect_id'])
                        for r in records}

def validate(data):
    assert isinstance(data, list) and len(data) <= 25
    keys = {'sku', 'defect_id', 'exact_quote', 'source_path', 'source_sha', 'start_line', 'end_line', 'historical'}
    for r in data:
        assert set(r) == keys and r['sku'] in ALLOWED
        assert r['historical'] is True and r['source_path'] == SOURCE_PATH and r['source_sha'] == SHA
        assert type(r['start_line']) is int and type(r['end_line']) is int
        assert 1 <= r['start_line'] <= r['end_line'] <= len(lines)
        assert r['exact_quote'] == '\n'.join(lines[r['start_line']-1:r['end_line']])
        assert expected_source_rows.get((r['start_line'], r['end_line'])) == (r['sku'], r['defect_id'])
        assert r['defect_id'] is None or re.fullmatch(r'[DS]-\d+', r['defect_id'])
        if r['defect_id']:
            assert r['exact_quote'].startswith('| ' + r['defect_id'] + ' |')

validate(records)
checks = {'positive': 'PASS'}
for name, change in [('changed_quote', lambda r: r.update(exact_quote=r['exact_quote']+'x')),
                     ('missing_line', lambda r: r.update(start_line=len(lines)+1, end_line=len(lines)+1)),
                     ('wrong_sha', lambda r: r.update(source_sha='0'*40)),
                     ('wrong_sku', lambda r: r.update(sku='P5')),
                     ('eligible_sku_swap', lambda r: r.update(sku='P7')),
                     ('historical_false', lambda r: r.update(historical=False))]:
    bad = copy.deepcopy(records)
    change(bad[0])
    try:
        validate(bad)
    except AssertionError:
        checks[name] = 'REJECTED/PASS'
    else:
        raise AssertionError(name + ' accepted')
elapsed = time.monotonic()-START
assert elapsed <= 180
output = root / 'MB001_BASELINE_QUOTED_DEFECTS.json'
output.write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
proof = {'source_commit': SHA, 'source_blob': BLOB, 'source_bytes': len(raw), 'source_lines': len(lines),
         'record_count': len(records), 'checks': checks, 'manual_review': manual,
         'elapsed_seconds': elapsed, 'llm_api_calls': 0, 'execution_environment': 'ai-workstation Python3; verified 2026-10-04',
         'selection_rule': 'Whole table rows only. Sections1,3,6. Explicit primary SKU or single SKU location; multi/indirect locations retained for manual review. No field paraphrasing.'}
(root / 'MB001_BASELINE_QUOTED_DEFECTS_PROOF.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k != 'manual_review'}, ensure_ascii=False))
```

## Independent recovery verification — 2026-10-04

Base PR #347 remains unchanged at b6e483071f8dc8d8c9a9bf6426776424c386a5fa. Independent ai-workstation reproduction matched all 10 quoted records and 3 manual-review entries. An additional negative case exposed that the original validator accepted changing P2 to eligible P7 while retaining a P2 source quote. The root cause was SKU membership validation without binding SKU/defect ID to its immutable source row.

The reproduction validator now binds each source line range to its extracted SKU/defect ID tuple. A new eligible-SKU substitution negative case rejects P2 to P7, alongside the existing five negative cases. Source bytes, quoted output, historical classification and selection rule are unchanged. Current proof records ai-workstation execution; the earlier workspace proof above is historical.

Regression: python3 -m unittest discover -s tools -p test_baseline_quoted_defects_binding.py -v. Eight tests verify unchanged published records, exact source SHA/blob, the original negative cases, eligible-SKU substitution and explicit defect-ID removal. All tests run deterministically with stdlib and the pinned Git source, without LLM/API calls or product generation.
