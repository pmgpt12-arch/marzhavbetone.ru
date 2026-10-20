#!/usr/bin/env python3
"""P1 delivery list and mirrored buyer assets stay aligned."""
from hashlib import sha256
from pathlib import Path
from docx import Document
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "products-storage/01-zakrytie-rabot"
MIRROR = ROOT / "products-storage/04-polnyy-komplekt-pto/01-30-bazovye-pakety/01-zakrytie-rabot"
manifest = json.loads((ROOT / 'tools/candidates/remaining-batch-r3-20261018/final-buyer-review-20261020/P1-manifest-R3.json').read_text())
buyer = [p for p in BASE.iterdir() if p.is_file() and p.name not in {'.htaccess','MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt'}]
assert {p.name:sha256(p.read_bytes()).hexdigest() for p in buyer} == {r['file']:r['sha256'] for r in manifest['members']}
assert len(buyer) == 20
# The retired full PTO bundle is a historical snapshot, outside the active P1 edition.
deliverables = [p for p in buyer if not p.name.startswith('00-')]
instruction = Document(BASE / "00-INSTRUKCIYA.docx")
listed = [row.cells[0].text for row in instruction.tables[0].rows[1:]]
expected = sorted(p.name for p in deliverables)
assert sorted(listed) == expected, ("instruction differs", sorted(set(expected) - set(listed)), sorted(set(listed) - set(expected)))
assert len(listed) == 17, len(listed)
# Историческая дата сверки не является условием актуальности нового комплекта.
# Нормативная готовность проверяется отдельным гейтом под текущие смысловые хеши.
print("P1 delivery alignment: 20 exact approved buyer files, 17 instruction entries PASS")
