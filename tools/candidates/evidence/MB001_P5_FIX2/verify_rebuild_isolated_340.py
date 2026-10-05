#!/usr/bin/env python3
"""Rebuild only in an isolated temporary mirror; compare shipped 04/05 bytes."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
REL_SCRIPT = Path('tools/candidates/evidence/MB001_P5_FIX2/rebuild_04_05_340.py')
PACK = Path('products-storage/07-uderzhaniya-shtrafy-zachety')
BOOKS = ('04-raschet-ubytkov.xlsx', '05-reestr-uderzhaniy.xlsx')


def main():
    with tempfile.TemporaryDirectory(prefix='mb001-340-rebuild-check-') as temp:
        mirror = Path(temp)
        script = mirror / REL_SCRIPT
        script.parent.mkdir(parents=True)
        (mirror / PACK).mkdir(parents=True)
        shutil.copy2(ROOT / REL_SCRIPT, script)
        shutil.copy2(ROOT / 'products-storage/build_paid_07.py', mirror / 'products-storage/build_paid_07.py')
        result = subprocess.run(['python3', '-B', str(script)], capture_output=True, text=True, timeout=60)
        print(result.stdout, end='')
        assert result.returncode == 0, result.stderr
        for name in BOOKS:
            original = (ROOT / PACK / name).read_bytes()
            rebuilt = (mirror / PACK / name).read_bytes()
            assert original == rebuilt, f'Rebuild divergence: {name}'
            print('BYTE_EQUAL', name, hashlib.sha256(rebuilt).hexdigest())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
