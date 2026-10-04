#!/usr/bin/env python3
"""#364: пересборка только 04 комплекта P5 генератором build_paid_07.py.

Генератор запускается на копии во временной папке с заглушкой reportlab
(как в MB001_P5_FIX2/rebuild_04_05_340.py: reportlab в среде нет). В
products-storage возвращается только 04. 05 из временной сборки
сравнивается с лежащим в репозитории побайтно и не записывается.

    python3 -B tools/candidates/evidence/P5_PERCENT_INPUT/rebuild_04.py          # записать 04
    python3 -B tools/candidates/evidence/P5_PERCENT_INPUT/rebuild_04.py --check  # только сверить
"""
import hashlib
import importlib.util
import shutil
import sys
import tempfile
import types
from pathlib import Path

КОРЕНЬ = Path(__file__).resolve().parents[4]
ХРАНИЛИЩЕ = КОРЕНЬ / "products-storage"
КОМПЛЕКТ = "07-uderzhaniya-shtrafy-zachety"
КНИГА_04, КНИГА_05 = "04-raschet-ubytkov.xlsx", "05-reestr-uderzhaniy.xlsx"


def _заглушка_reportlab() -> None:
    if "reportlab" in sys.modules:
        return
    класс = type("Canvas", (), {"__init__": lambda self, *a, **k: None,
                                 "__getattr__": lambda self, n: (lambda *a, **k: None)})
    модули = {
        "reportlab": {}, "reportlab.pdfgen": {}, "reportlab.pdfgen.canvas": {"Canvas": класс},
        "reportlab.lib": {}, "reportlab.lib.pagesizes": {"A4": (595.0, 842.0)},
        "reportlab.lib.units": {"cm": 28.35},
    }
    for имя, атрибуты in модули.items():
        m = types.ModuleType(имя)
        m.__dict__.update(атрибуты)
        sys.modules[имя] = m
    sys.modules["reportlab.pdfgen"].canvas = sys.modules["reportlab.pdfgen.canvas"]


def main(только_сверить: bool) -> int:
    _заглушка_reportlab()
    tmp = Path(tempfile.mkdtemp(prefix="mvb-364-build-"))
    try:
        shutil.copy2(ХРАНИЛИЩЕ / "build_paid_07.py", tmp / "build_paid_07.py")
        (tmp / КОМПЛЕКТ).mkdir()
        spec = importlib.util.spec_from_file_location("build_paid_07_364", tmp / "build_paid_07.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.create_pdf_simple = lambda *a, **k: None
        mod.build_paid_07()
        новая_04 = (tmp / КОМПЛЕКТ / КНИГА_04).read_bytes()
        новая_05 = (tmp / КОМПЛЕКТ / КНИГА_05).read_bytes()
        assert новая_05 == (ХРАНИЛИЩЕ / КОМПЛЕКТ / КНИГА_05).read_bytes(), "05 разошлась с репозиторием"
        print("05 BYTE_EQUAL", hashlib.sha256(новая_05).hexdigest())
        if только_сверить:
            assert новая_04 == (ХРАНИЛИЩЕ / КОМПЛЕКТ / КНИГА_04).read_bytes(), "04 разошлась с генератором"
            print("04 BYTE_EQUAL", hashlib.sha256(новая_04).hexdigest())
        else:
            (ХРАНИЛИЩЕ / КОМПЛЕКТ / КНИГА_04).write_bytes(новая_04)
            print("04 WRITTEN", hashlib.sha256(новая_04).hexdigest())
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main("--check" in sys.argv))
