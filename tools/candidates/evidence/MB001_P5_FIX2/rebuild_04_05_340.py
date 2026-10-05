#!/usr/bin/env python3
"""#340: пересборка только 04 и 05 комплекта P5 генератором build_paid_07.py.

Генератор импортирует reportlab ради 07.pdf, а в среде исполнителя reportlab
нет. Поэтому генератор запускается на копии каталога комплекта во временной
папке с заглушкой reportlab, и в products-storage возвращаются только 04 и
05 — остальные файлы комплекта (docx, 07.pdf) не трогаются.

    python3 -m pytest tools/candidates/evidence/MB001_P5_FIX2/rebuild_04_05_340.py -s
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
КНИГИ = ("04-raschet-ubytkov.xlsx", "05-reestr-uderzhaniy.xlsx")


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


def пересобрать() -> dict[str, str]:
    _заглушка_reportlab()
    tmp = Path(tempfile.mkdtemp(prefix="mvb-340-build-"))
    try:
        shutil.copy2(ХРАНИЛИЩЕ / "build_paid_07.py", tmp / "build_paid_07.py")
        (tmp / КОМПЛЕКТ).mkdir()
        spec = importlib.util.spec_from_file_location("build_paid_07_340", tmp / "build_paid_07.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # create_pdf_simple с заглушкой ничего не пишет; 07.pdf не нужен
        mod.create_pdf_simple = lambda *a, **k: None
        mod.build_paid_07()
        итог = {}
        for имя in КНИГИ:
            данные = (tmp / КОМПЛЕКТ / имя).read_bytes()
            (ХРАНИЛИЩЕ / КОМПЛЕКТ / имя).write_bytes(данные)
            итог[имя] = hashlib.sha256(данные).hexdigest()
        return итог
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_пересборка_04_05() -> None:
    for имя, sha in пересобрать().items():
        print(f"{sha}  {имя}")


if __name__ == "__main__":
    test_пересборка_04_05()
