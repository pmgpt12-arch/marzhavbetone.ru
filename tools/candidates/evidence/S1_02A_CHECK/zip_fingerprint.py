"""Независимая сборка штатного архива p1: mvb_build_product_zip('p1') из
products-config.php на временной подстановке ORDERS_DIR/PRODUCTS_DIR.
Архив распаковывается в каталог из argv[1] — по нему и идёт проверка.
Печатает записи, размеры, SHA-256 и сверку с деревом git HEAD."""
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CAND = "tools/candidates/s1-oplata-za-raboty"
OUT = Path(sys.argv[1]).resolve()
WORK = OUT / "work"
shutil.rmtree(OUT, ignore_errors=True)
(WORK / "products").mkdir(parents=True)
(WORK / "orders" / "delivery").mkdir(parents=True)
shutil.copytree(ROOT / CAND, WORK / "products" / "01-zakrytie-rabot")
(WORK / "b.php").write_text(
    "<?php define('ORDERS_DIR', getenv('WORK').'/orders');"
    "define('PRODUCTS_DIR', getenv('WORK').'/products');"
    "require getenv('SITE').'/products-config.php';"
    "$p = mvb_build_product_zip('p1'); echo $p === null ? 'NULL' : $p, \"\\n\";")
zp = subprocess.run(["php", str(WORK / "b.php")], env={"WORK": str(WORK), "SITE": str(ROOT), "PATH": "/usr/bin:/bin"},
                    capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
print("php вернул:", zp.replace(str(OUT), "<scratch>"))
head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
print("HEAD:", head)
kit = OUT / "kit"
ok = True
with zipfile.ZipFile(zp) as zf:
    infos = zf.infolist()
    print("записей:", len(infos))
    zf.extractall(kit)
    for i in sorted(infos, key=lambda x: x.filename):
        b = zf.read(i)
        h = hashlib.sha256(b).hexdigest()
        g = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{CAND}/{i.filename}"], capture_output=True).stdout
        same = hashlib.sha256(g).hexdigest() == h
        ok &= same
        print(f"  {i.filename}  {i.file_size}  {h}  {'= git HEAD' if same else '!= git HEAD'}")
names = [i.filename for i in infos]
print("MANIFEST в архиве:", "MANIFEST.md" in names)
print("ROUTE-MAP в архиве:", any("ROUTE-MAP" in n for n in names))
ok &= len(infos) == 11 and "MANIFEST.md" not in names
print("ИТОГ:", "ok" if ok else "ПРОВАЛ")
sys.exit(0 if ok else 1)
