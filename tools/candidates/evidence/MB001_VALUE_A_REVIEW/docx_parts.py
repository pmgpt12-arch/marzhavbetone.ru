"""Issue #337: хеши частей docx в двух ревизиях git — что именно менял R3 в 31/32.

Запуск из корня репозитория:
    python3 tools/candidates/evidence/MB001_VALUE_A_REVIEW/docx_parts.py
Только чтение git-объектов, на диск ничего не пишет.
"""
import hashlib
import io
import subprocess
import zipfile

P4 = "products-storage/08-pto-bez-zamechaniy"
FILES = ["31-pyat-aktov-skrytyh-rabot.docx", "32-shablon-ispolnitelnoy-shemy.docx"]
REVS = ["ca62f7b", "1fd82aa", "64b210e", "b5e284e"]
PARTS = ["word/document.xml", "word/header1.xml", "word/footer1.xml"]


def blob(rev, path):
    return subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, check=True).stdout


for name in FILES:
    for rev in REVS:
        data = blob(rev, f"{P4}/{name}")
        z = zipfile.ZipFile(io.BytesIO(data))
        row = [f"{name} @ {rev}", f"file={hashlib.sha256(data).hexdigest()[:12]}"]
        for part in PARTS:
            h = hashlib.sha256(z.read(part)).hexdigest()[:12] if part in z.namelist() else "absent"
            row.append(f"{part.split('/')[1]}={h}")
        print("  ".join(row))
