"""Narrow correction of the reproduced second subtraction; no public ZIP writes."""
from pathlib import Path
import hashlib, io, json, zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
NAME = '04-pismo-o-vozvrate-uderzhaniya.docx'
OLD = 'Итог по колонке «Разница» за вычетом подтверждённых возвратов — это сумма вашего обращения. Она должна совпадать с суммой в тексте письма.'
NEW = 'Итог по колонке «Разница» — сумма вашего обращения: возвраты уже учтены в каждой строке. Повторно их не вычитайте. Итог должен совпадать с суммой в письме.'
sha = lambda b: hashlib.sha256(b).hexdigest()

def main():
    source = ROOT / 'downloads/uderzhaniya.zip'
    before = source.read_bytes()
    with zipfile.ZipFile(io.BytesIO(before)) as archive:
        data = archive.read(NAME)
    original = OUT / 'retention/original' / NAME
    candidate = OUT / 'retention/candidate' / NAME
    assert not candidate.exists()
    original.parent.mkdir(parents=True, exist_ok=True)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(data)
    with zipfile.ZipFile(io.BytesIO(data)) as old, zipfile.ZipFile(candidate, 'w') as new:
        body = old.read('word/document.xml')
        assert body.count(OLD.encode()) == 1
        for entry in old.infolist():
            content = old.read(entry.filename)
            if entry.filename == 'word/document.xml':
                content = content.replace(OLD.encode(), NEW.encode())
            new.writestr(entry, content)
    with zipfile.ZipFile(io.BytesIO(data)) as old, zipfile.ZipFile(candidate) as new:
        assert old.namelist() == new.namelist()
        changed = [n for n in old.namelist() if old.read(n) != new.read(n)]
        assert changed == ['word/document.xml']
        assert new.read('word/document.xml').replace(NEW.encode(), OLD.encode()) == old.read('word/document.xml')
        assert new.testzip() is None
    # Known returns are already removed when each difference is calculated.
    cases = []
    for held, returned in [(100000, 20000), (100000, 0), (100000, 100000)]:
        remaining = held - returned
        cases.append(dict(held=held, returned=returned, difference=remaining,
                          old_instruction_result=remaining-returned,
                          corrected_instruction_result=remaining,
                          pass_=remaining == held-returned))
    receipt = dict(issue='FL10_DOUBLE_SUBTRACTION', status='CANDIDATE_TESTED_NATIVE_PENDING',
                   source_zip_sha256=sha(before), source_docx_sha256=sha(data),
                   candidate_docx_sha256=sha(candidate.read_bytes()),
                   changed_parts=changed, other_parts_byte_exact=True,
                   change_count=1, old=OLD, new=NEW, cases=cases,
                   remaining='FL12 and other whole-product issues remain open; this is one arithmetic instruction fix.',
                   publication=False)
    assert source.read_bytes() == before
    (OUT/'retention/REPRODUCTION_AND_FIX.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
