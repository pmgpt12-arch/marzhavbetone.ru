#!/usr/bin/env python3
"""#340: SHA-256 штатного ZIP P5 и каждого файла в нём.

ZIP собирает функция выдачи mvb_build_product_zip('p5') (тот же PHP, что
у харнесса tools/test_p5_documents.архив_выдачи). Печатается SHA двух
сборок подряд: если они различаются, ZIP недетерминирован (время в
записях архива), и сверять нужно SHA файлов.

    python3 -m pytest tools/candidates/evidence/MB001_P5_FIX2/zip_sha_340.py -s
"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import test_p5_documents as h  # noqa: E402


def собрать() -> bytes:
    with tempfile.TemporaryDirectory(prefix="mvb-340-zip-") as tmp:
        скрипт = Path(tmp) / "build.php"
        скрипт.write_text(h._PHP, encoding="utf-8")
        заказы = Path(tmp) / "orders"
        (заказы / "delivery").mkdir(parents=True)
        r = subprocess.run([shutil.which("php"), str(скрипт), str(h.КОРЕНЬ), str(заказы), str(h.МАСТЕРА)],
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr + r.stdout
        return Path(r.stdout.strip()).read_bytes()


def test_sha_zip() -> None:
    первая, вторая = собрать(), собрать()
    print("ZIP сборка 1:", hashlib.sha256(первая).hexdigest(), len(первая), "байт")
    print("ZIP сборка 2:", hashlib.sha256(вторая).hexdigest(), len(вторая), "байт")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "p5.zip"
        p.write_bytes(первая)
        with zipfile.ZipFile(p) as z:
            for i in z.infolist():
                if not i.is_dir():
                    print(hashlib.sha256(z.read(i.filename)).hexdigest(), i.filename)


if __name__ == "__main__":
    test_sha_zip()
