"""Штатная сборка архива p1 (`mvb_build_product_zip` из products-config.php)
на временной подстановке: папка кандидата копируется во временный
PRODUCTS_DIR под именем `01-zakrytie-rabot`. Сборка дважды, с чистого
каталога; печатает записи архива, их SHA-256 и сверку с файлами кандидата.
products-config.php, сайт и действующая выдача не меняются."""
import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CAND = ROOT / "tools" / "candidates" / "s1-oplata-za-raboty"
PHP = r"""<?php
define('ORDERS_DIR', getenv('WORK') . '/orders');
define('PRODUCTS_DIR', getenv('WORK') . '/products');
require getenv('SITE') . '/products-config.php';
$p = mvb_build_product_zip('p1');
echo $p === null ? "NULL\n" : $p . "\n";
"""


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build(n: int) -> tuple[str, list[tuple[str, int, str]]]:
    work = Path(tempfile.mkdtemp(prefix=f"s1-zip{n}-"))
    try:
        (work / "products").mkdir()
        shutil.copytree(CAND, work / "products" / "01-zakrytie-rabot")
        (work / "build.php").write_text(PHP)
        out = subprocess.run(["php", str(work / "build.php")], env={"WORK": str(work), "SITE": str(ROOT), "PATH": "/usr/bin:/bin"},
                             capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
        z = Path(out)
        with zipfile.ZipFile(z) as zf:
            записи = sorted((i.filename, i.file_size, sha(zf.read(i))) for i in zf.infolist())
        return z.name, записи
    finally:
        shutil.rmtree(work, ignore_errors=True)


имя1, з1 = build(1)
имя2, з2 = build(2)
print(f"архив: {имя1}; записей: {len(з1)}")
for f, size, h in з1:
    равен = sha((CAND / f).read_bytes()) == h
    print(f"  {f}  {size} B  {h}  {'= файлу кандидата' if равен else '≠ ФАЙЛУ КАНДИДАТА'}")
print("MANIFEST в архиве:", any(f == "MANIFEST.md" for f, _, _ in з1))
print("карта маршрута в архиве:", any("ROUTE-MAP" in f for f, _, _ in з1))
print("вторая сборка: записи, размеры и SHA-256 совпадают:", з1 == з2 and имя1 == имя2)
ok = len(з1) == 11 and з1 == з2 and all(sha((CAND / f).read_bytes()) == h for f, _, h in з1)
sys.exit(0 if ok else 1)
