#!/usr/bin/env python3
"""После набора «КС подписаны, денег нет» следующий шаг один — S1 на адресе P1.

ЗАЧЕМ. Аудит MB001 L1 (tools/candidates/MB001_L1_Judicial_Free_Lead_S1_Audit.md,
G1–G3) нашёл три точки продолжения бесплатного набора dengi, и все вели на T1,
который снимается с продажи. Ещё два документа архива называли цену P1
2 490 ₽ и обещали от его имени исполнительное производство, ФССП и «стратегии
взыскания» — в «Системе получения оплаты за выполненные работы» (S1) этого нет:
её маршрут заканчивается подготовкой обращения в арбитражный суд. По решению
владельца S1 занимает адрес P1 (S1-EDITION-SKU-DECISION-MEMO.md, §7).

ЧТО СТЕРЕЖЁТСЯ. Три точки и два документа:

    materialy/dengi.html        data-continue формы и блок «Если нужен полный
                                порядок действий» — одна карточка S1;
    99-chto-dalshe.pdf          маршрут 1 → адрес S1, utm_content=dengi-primary;
    01-…docx, 04-…docx          раздел «Следующий шаг» → адрес S1, без цены.

Плюс архив downloads/dengi.zip: собран из папки набора штатным
tools/build_free_zips.py и пересобирается побайтово одинаково. Если под рукой
python-docx, openpyxl, reportlab и DejaVu, заодно проверяется, что генератор
products-storage/build_free_01.py воспроизводит файлы папки. Без них этот
случай называется пропущенным, а не пройденным.

Проверка читает только стандартной библиотекой: .docx — через
tools/docx_text.py, из PDF берутся адреса ссылок (текст там — коды глифов
подмножества шрифта, искать в нём нечего).

    python3 tools/test_dengi_next_step.py
    python3 -m pytest tools/test_dengi_next_step.py -q
"""
from __future__ import annotations

import ast
import hashlib
import html
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from docx_text import paragraphs  # noqa: E402

PAGE = ROOT / "materialy" / "dengi.html"
FOLDER = ROOT / "products-storage" / "00-free-ks-podpisany-deneg-net"
GENERATOR = ROOT / "products-storage" / "build_free_01.py"
ARCHIVE = ROOT / "downloads" / "dengi.zip"

# Адрес P1, который станет страницей S1. Своей копии адреса в коде сайта нет —
# он повторён здесь намеренно: тест должен покраснеть, если точку увели
# куда-то ещё, в том числе вслед за генератором.
S1_URL = "https://marzhavbetone.ru/products/p1-oplata-po-ks2.html"
S1_NAME = "Система получения оплаты за выполненные работы"
NEXT_DOCS = ("01-algoritm-pervichnoy-proverki.docx", "04-shablon-pisma.docx")

# Что не должно вернуться. Пробел в цене бывает обычным, неразрывным и узким.
FORBIDDEN = {
    "ссылка на T1": re.compile(r"t1-pervyy|/products/t1-", re.I),
    "цена P1 2 490 ₽": re.compile(r"2[\s  ]?490"),
    "исполнительное производство": re.compile(r"исполнительн\w*\s+производств", re.I),
    "ФССП": re.compile(r"ФССП"),
    "стратегии взыскания": re.compile(r"стратеги\w*\s+взыскани", re.I),
    "консультационные материалы": re.compile(r"консультационн\w*\s+материал", re.I),
}
SKIP = {"00-PISMO-POSLE-POKUPKI.txt", ".htaccess", "MANIFEST.md"}


def нарушения(текст: str) -> list[str]:
    return [имя for имя, шаблон in FORBIDDEN.items() if шаблон.search(текст)]


def адреса_pdf(данные: bytes) -> list[str]:
    """Адреса ссылок PDF в порядке страницы: словари аннотаций не сжаты."""
    return [a.decode("latin-1").replace("\\(", "(").replace("\\)", ")")
            for a in re.findall(rb"/URI \(((?:[^()\\]|\\.)*)\)", данные)]


def страница() -> str:
    return PAGE.read_text(encoding="utf-8")


def архив() -> dict[str, bytes]:
    with zipfile.ZipFile(ARCHIVE) as z:
        return {name: z.read(name) for name in z.namelist()}


def текст_docx(данные: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".docx") as f:
        f.write(данные)
        f.flush()
        return "\n".join(paragraphs(Path(f.name)))


# --- страница ---------------------------------------------------------------

def test_page_continue_leads_to_s1():
    найдено = re.search(r'id="lead-form"[^>]*data-continue="([^"]+)"', страница())
    assert найдено, "у формы #lead-form нет data-continue"
    адрес = html.unescape(найдено.group(1))
    assert адрес.startswith(S1_URL + "?"), адрес
    assert "utm_content=dengi-primary" in адрес, адрес


def test_page_block_is_single_s1_card():
    блок = re.search(r"<h2>Если нужен полный порядок действий</h2>(.*?)</section>",
                     страница(), re.S)
    assert блок, "блок «Если нужен полный порядок действий» не найден"
    карточки = re.findall(r"<article class=\"product-card\">(.*?)</article>",
                          блок.group(1), re.S)
    assert len(карточки) == 1, f"карточек {len(карточки)}, нужна одна — S1"
    карточка = карточки[0]
    assert f"<h3>{S1_NAME}</h3>" in карточка, карточка[:200]
    assert re.findall(r'href="([^"]+)"', карточка) == ["../products/p1-oplata-po-ks2.html"]
    assert "₽" not in карточка, "цена S1 живёт на странице товара, а не в карточке"


def test_page_has_no_forbidden():
    assert not нарушения(страница()), нарушения(страница())


# --- архив ------------------------------------------------------------------

def test_archive_matches_folder():
    ожидаемо = {p.name: p.read_bytes() for p in FOLDER.iterdir()
                if p.is_file() and p.name not in SKIP}
    есть = архив()
    assert sorted(есть) == sorted(ожидаемо), (sorted(есть), sorted(ожидаемо))
    разные = [n for n in есть if есть[n] != ожидаемо[n]]
    assert not разные, f"архив отстал от папки: {разные}; tools/build_free_zips.py dengi"


def test_archive_rebuilds_byte_for_byte():
    описание = importlib.util.spec_from_file_location(
        "build_free_zips", ROOT / "tools" / "build_free_zips.py")
    сборщик = importlib.util.module_from_spec(описание)
    описание.loader.exec_module(сборщик)
    with tempfile.TemporaryDirectory() as tmp:
        сборщик.DOWNLOADS = Path(tmp)
        собран = сборщик.build("dengi", сборщик.MATERIALS["dengi"])
        assert собран is not None
        assert собран.read_bytes() == ARCHIVE.read_bytes(), \
            "повторная сборка dengi.zip даёт другие байты"


def test_archive_has_no_forbidden():
    for имя, данные in архив().items():
        if имя.endswith(".docx"):
            текст = текст_docx(данные)
        elif имя.endswith(".pdf"):
            текст = "\n".join(адреса_pdf(данные))
        elif имя.endswith(".xlsx"):
            with tempfile.NamedTemporaryFile(suffix=".xlsx") as f:
                f.write(данные)
                f.flush()
                with zipfile.ZipFile(f.name) as z:
                    текст = "\n".join(z.read(n).decode("utf-8", "replace")
                                      for n in z.namelist() if n.endswith(".xml"))
        else:
            текст = данные.decode("utf-8", "replace")
        assert not нарушения(текст), f"{имя}: {нарушения(текст)}"


def test_docs_next_step_is_s1_without_price():
    есть = архив()
    for имя in NEXT_DOCS:
        текст = текст_docx(есть[имя])
        assert S1_URL in текст, f"{имя}: нет ссылки на страницу S1"
        assert "Системе получения оплаты за выполненные работы" in текст, имя
        assert "₽" not in текст, f"{имя}: цена в скачанном файле устареет"
        assert "подготовка обращения в арбитражный суд" in текст, имя


def test_pdf_route_one_is_s1():
    адреса = адреса_pdf(архив()["99-chto-dalshe.pdf"])
    assert адреса, "в PDF нет ни одной ссылки"
    первый = адреса[0]
    assert первый.startswith(S1_URL + "?"), первый
    assert "utm_content=dengi-primary" in первый, первый
    assert len(set(адреса)) == 3, f"маршрутов не три: {sorted(set(адреса))}"


# --- генератор --------------------------------------------------------------

def test_generator_strings_have_no_forbidden():
    """Строки генератора, а не его комментарии: в документ идут только они."""
    дерево = ast.parse(GENERATOR.read_text(encoding="utf-8"))
    строки = [n.value for n in ast.walk(дерево)
              if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    текст = "\n".join(строки)
    assert not нарушения(текст), нарушения(текст)
    assert "PAID_PRICE" not in GENERATOR.read_text(encoding="utf-8")


def test_generator_reproduces_folder():
    """Генератор в чистой копии даёт те же байты, что лежат в папке."""
    try:
        import docx, openpyxl, reportlab  # noqa: F401
    except ImportError as e:
        raise Пропуск(f"нет библиотеки генератора: {e.name}")
    if not Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf").exists():
        raise Пропуск("нет шрифта DejaVuSans")
    with tempfile.TemporaryDirectory() as tmp:
        копия = Path(tmp)
        shutil.copy(GENERATOR, копия / GENERATOR.name)
        (копия / FOLDER.name).mkdir()
        прогон = subprocess.run([sys.executable, GENERATOR.name], cwd=копия,
                                capture_output=True, text=True)
        assert прогон.returncode == 0, прогон.stderr[-800:]
        for файл in sorted((копия / FOLDER.name).iterdir()):
            эталон = FOLDER / файл.name
            assert эталон.exists(), f"генератор создал лишний файл {файл.name}"
            assert hashlib.sha256(файл.read_bytes()).digest() == \
                hashlib.sha256(эталон.read_bytes()).digest(), \
                f"{файл.name}: папка не совпадает с генератором"


class Пропуск(Exception):
    pass


try:  # под pytest пропуск — штатный skip
    import pytest

    _пропуск = pytest.skip.Exception
except ImportError:  # pragma: no cover
    _пропуск = None

if _пропуск is not None:
    Пропуск = _пропуск  # type: ignore[misc,assignment]  # noqa: F811


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = skipped = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {str(e)[:400]}")
        except Пропуск as e:
            skipped += 1
            print(f"  – {t.__name__}: не запускался — {e}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}, не запускалось {skipped}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
