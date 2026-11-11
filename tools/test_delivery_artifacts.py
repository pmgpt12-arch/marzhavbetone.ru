#!/usr/bin/env python3
"""Файл, за который заплатили, обязан открываться и считать.

Два дефекта, найденные в выдаче с разницей в сутки, устроены одинаково:
сборка прошла без единой ошибки, проверка состава осталась зелёной, а
покупатель получил файл, который не работает.

**PDF без встроенного шрифта.** Стандартные шрифты reportlab («стандартные
четырнадцать») кодируются WinAnsi и кириллических глифов не содержат.
`c.drawString()` с русской строкой отрабатывает молча: файл собирается,
весит 2,3–2,4 КБ вместо 46–91 КБ, и на странице вместо текста — ряды «n».
Так вышло у трёх алгоритмов: `08-algoritm-proverki.pdf` (P3),
`08-algoritm-raboty-s-id.pdf` (P4) и `07-algoritm-proverki-uderzhaniy.pdf`
(P5). Признак, отличающий рабочий файл от пустого, — встроенный шрифт:
`/FontFile`, `/FontFile2` или `/FontFile3` в теле документа.

**Кириллическое имя функции в .xlsx.** Имя функции в файле хранится
латиницей; `СУММ` — то, как его показывает русский интерфейс, а не то, что
лежит в `<f>`. Записанное кириллицей, оно читается как имя несуществующей
функции и даёт `#ИМЯ?`. Так вышло в четырёх книгах: `=ЕСЛИ(`, `=СЧЁТЕСЛИ(`
и `=СРЗНАЧ(` у P3 и P4, `=СУММ(` у P5.

Проверяется только то, что покупателю действительно уходит. Папки, не
адресуемые ни одним sku, — исторические архивы: в них оба дефекта живут и
сегодня, править их нельзя, и источник истины о том, какая папка
адресуема, берётся из `check_packages`, а не заводится здесь второй раз.

Запуск без pytest: python3 tools/test_delivery_artifacts.py
"""
from __future__ import annotations

import html
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_packages as cp                              # noqa: E402

STORAGE = cp.STORAGE
# Тот же список исключений, по которому собирается архив покупателю
НЕ_ВЫДАЁТСЯ = cp.NOT_DELIVERED | cp.NOT_LISTED

ВСТРОЕННЫЙ_ШРИФТ = re.compile(rb"/FontFile\d?")
ФОРМУЛА = re.compile(r"<f[^>]*>([^<]*)</f>")
СТРОКОВЫЙ_ЛИТЕРАЛ = re.compile(r'"(?:[^"]|"")*"')
# Имя функции — слово перед открывающей скобкой, вне строкового литерала
ИМЯ_ФУНКЦИИ = re.compile(r"(?<![A-Za-zА-Яа-я0-9_.])([А-ЯЁ][А-ЯЁа-яё.]{1,})\s*\(")

def выдаваемые() -> list[Path]:
    """Файлы всех комплектов, адресуемых хотя бы одним sku."""
    папки = sorted(p for p in STORAGE.iterdir()
                   if p.is_dir() and p.name != "__pycache__")
    исторические = cp.not_addressed(папки, cp.catalog())
    return [f
            for папка in папки if папка.name not in исторические
            for f in sorted(папка.rglob("*"))
            if f.is_file() and f.name not in НЕ_ВЫДАЁТСЯ]


def кириллические_функции(книга: Path) -> list[str]:
    """Проверяет формулы из OOXML независимо от XML-префикса (<f>, <x:f>)."""
    return [
        формула for формула in формулы_книги(книга)
        if ИМЯ_ФУНКЦИИ.search(СТРОКОВЫЙ_ЛИТЕРАЛ.sub("", формула))
    ]

def test_каждый_выдаваемый_pdf_несёт_встроенный_шрифт() -> None:
    файлы = [f for f in выдаваемые() if f.suffix.lower() == ".pdf"]
    assert файлы, "PDF в выдаче не найдено — проверка ничего не проверяет"
    пустые = [f.relative_to(STORAGE).as_posix() for f in файлы
              if not ВСТРОЕННЫЙ_ШРИФТ.search(f.read_bytes())]
    assert not пустые, (
        "PDF без встроенного шрифта — кириллица в нём не нарисуется:\n  "
        + "\n  ".join(пустые))


def test_ни_одна_выдаваемая_книга_не_зовёт_функцию_кириллицей() -> None:
    книги = [f for f in выдаваемые() if f.suffix.lower() == ".xlsx"]
    assert книги, "книг в выдаче не найдено — проверка ничего не проверяет"
    плохие = []
    for книга in книги:
        адрес = книга.relative_to(STORAGE).as_posix()
        for формула in кириллические_функции(книга):
            плохие.append(f"{адрес}: {формула}")
    assert not плохие, (
        "имя функции записано кириллицей — Excel вернёт #ИМЯ?:\n  "
        + "\n  ".join(плохие))


def формулы_книги(книга: Path) -> list[str]:
    """Извлекает формулы через XML parser, независимо от namespace-префикса.

    Регулярное выражение <f> пропускало формулы <x:f>, из-за чего тест
    мог давать ложный PASS/FAIL на одном и том же XLSX.
    """
    from xml.etree import ElementTree as ET

    формулы = []
    with zipfile.ZipFile(книга) as z:
        for лист in z.namelist():
            if not re.fullmatch(r"xl/worksheets/sheet\d+\.xml", лист):
                continue
            root = ET.fromstring(z.read(лист))
            for node in root.iter():
                if node.tag.rsplit("}", 1)[-1] == "f" and node.text is not None:
                    формулы.append(node.text)
    return формулы

def test_бесплатный_калькулятор_пени_согласован_с_вводом_процента() -> None:
    """При вводе 0,1% Excel хранит 0,001: повторное /100 недопустимо.

    Проверяются исходный XLSX и оба генератора, чтобы исключить регрессию
    при будущей пересборке.
    """
    книга = STORAGE / "00-free-ks-podpisany-deneg-net" / "02-kalkulyator-sroka-oplaty.xlsx"
    ожидаемая = (
        'IF(OR(NOT(ISNUMBER(B8)),NOT(ISNUMBER(B10)),'
        'NOT(ISNUMBER(B11))),"",B8*B10*B11)'
    )
    assert ожидаемая in формулы_книги(книга), (
        "калькулятор должен использовать процентную долю без повторного /100"
    )
    with zipfile.ZipFile(книга) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "Введите договорную ставку как процент, например 0,1%." in sheet, (
        "подсказка к ставке должна требовать ввод со знаком %"
    )

    for имя in ("build_free_01.py", "build_all.py"):
        скрипт = (STORAGE / имя).read_text(encoding="utf-8")
        строки = скрипт.splitlines()
        matches = [v for v in строки if '["Начисленные пени"' in v]
        assert len(matches) == 1, f"{имя}: ожидалась одна формула пеней"
        assert "B8*B10*B11" in matches[0] and "/100" not in matches[0], (
            f"{имя}: повторное деление процента либо другая формула"
        )
        assert any("Введите договорную ставку как процент, например 0,1%." in v
                   for v in строки), f"{имя}: несовместимая подсказка к вводу"

def test_исторические_архивы_проверкой_не_охвачены() -> None:
    """Страховка от обратного дефекта: если однажды выдача начнёт считаться
    по всем папкам подряд, обе проверки покраснеют на архивах, которые
    править запрещено. Пусть это скажет отдельная строка, а не догадка."""
    папки = sorted(p for p in STORAGE.iterdir()
                   if p.is_dir() and p.name != "__pycache__")
    исторические = cp.not_addressed(папки, cp.catalog())
    охвачено = {f.relative_to(STORAGE).parts[0] for f in выдаваемые()}
    assert исторические, "неадресуемых папок нет — проверять нечего"
    assert not (охвачено & исторические), (
        f"в выдачу попали неадресуемые папки: {sorted(охвачено & исторические)}")


def test_p5_не_отдаёт_снятую_сравнительную_таблицу() -> None:
    """В P5 таблица сравнивала покупку со снятым товаром. Продаж до её
    снятия не было, поэтому она удалена из единственного текущего издания,
    а число файлов во всех покупательских точках равно одиннадцати."""
    folder = STORAGE / "07-uderzhaniya-shtrafy-zachety"
    files = cp.delivered(folder)
    stale = "09-sravnitelnaya-tablica.docx"
    assert stale not in files, "снятая таблица снова попала в выдачу P5"
    assert len(files) == 11, f"P5: ожидалось 11 файлов, получено {len(files)}"

    start = (folder / "00-START-HERE.txt").read_text(encoding="utf-8")
    manifest = (folder / "MANIFEST.md").read_text(encoding="utf-8")
    page = (cp.PAGES / "p5-shtrafy-uderzhaniya.html").read_text(encoding="utf-8")
    catalog = (cp.ROOT / "katalog.html").read_text(encoding="utf-8")
    sku_at = catalog.find('data-sku="p5"')
    card_start = catalog.rfind('<article class="product-card">', 0, sku_at)
    card_end = catalog.find('</article>', sku_at)
    card = (catalog[card_start:card_end + len('</article>')]
            if card_start >= 0 and card_end >= 0 else "")

    for name, text in {
        "00-START-HERE": start,
        "MANIFEST": manifest,
        "страница P5": page,
        "карточка P5": card,
    }.items():
        assert text, f"{name}: фрагмент P5 не найден"
        assert stale not in text, f"{name}: назван снятый файл"
        assert "Сравнительная таблица" not in text, f"{name}: названа снятая таблица"
        assert ("11 файлов" in text or "файлов в архиве: 11" in text
                or name == "MANIFEST"), (
            f"{name}: не указан актуальный счёт 11 файлов")


P4 = STORAGE / "08-pto-bez-zamechaniy"
P4_СТРАНИЦА = "p4-ispolnitelnaya-dokumentaciya-pto.html"
# Состав P4, закреплённый выпуском 28.09.2026 (Issue #308): 10 снят, 43 добавлен.
# Список, а не число: число сойдётся и при подмене одного файла другим.
P4_СОСТАВ = (
    "00-START-HERE.txt",
    "01-uvedomlenie-o-gotovnosti-id.docx",
    "02-akt-priemki-id.docx",
    "03-perechen-vozmozhnyh-zamechaniy.docx",
    "04-pismo-na-zamechaniya.docx",
    "05-sluzhebnaya-zapiska.docx",
    "06-reestr-zamechaniy.xlsx",
    "07-grafik-ustraneniya.xlsx",
    "08-algoritm-raboty-s-id.pdf",
    "09-krasnye-flagi.docx",
    "31-pyat-aktov-skrytyh-rabot.docx",
    "32-shablon-ispolnitelnoy-shemy.docx",
    "33-akt-peredachi-komplekta-pto.docx",
    "34-sluzhebnaya-zapiska.docx",
    "35-obshiy-zhurnal-rabot.xlsx",
    "36-vhodnoy-kontrol.xlsx",
    "37-reestr-pasportov.xlsx",
    "38-reestr-id.xlsx",
    "39-algoritm-zamechaniy.pdf",
    "40-ezhemesyachnaya-proverka.pdf",
    "41-akt-peredachi-ploshchadki-fronta.docx",
    "42-akt-vhodnogo-kontrolya-materialov.docx",
    "43-preduprezhdenie-po-st-716.docx",
)
# Сумма числом со знаком рубля. Пустое поле «____ ₽» в бланке суммой не является.
ЦЕНА = re.compile(r"\d[\d   ]*\s*₽")
# Обещания, которых комплект не подтверждает (#300 P4-03, #293 S-5, S-13)
P4_ЛОЖНЫЕ_ОБЕЩАНИЯ = (
    "окупаем", "полный комплект", "полного комплекта", "юридически выверен",
    "автопроверк", "15+", "сп и снип", "закрывает каждый пункт",
)


def текст_файла(файл: Path) -> str:
    """Видимый текст выдаваемого файла: абзацы .docx, строки .xlsx, .txt."""
    import docx_text
    if файл.suffix == ".docx":
        return "\n".join(docx_text.paragraphs(файл))
    if файл.suffix == ".xlsx":
        with zipfile.ZipFile(файл) as z:
            xml = "".join(z.read(n).decode("utf-8", "replace") for n in z.namelist()
                          if n.startswith("xl/") and n.endswith(".xml"))
        return html.unescape(" ".join(re.findall(r"<t[^>]*>([^<]*)</t>", xml)))
    if файл.suffix == ".txt":
        return файл.read_text(encoding="utf-8")
    return ""


def test_p4_покупатель_получает_ровно_обещанный_состав() -> None:
    files = cp.delivered(P4)
    assert sorted(files) == sorted(P4_СОСТАВ), (
        f"P4: лишние {sorted(set(files) - set(P4_СОСТАВ))}, "
        f"нет {sorted(set(P4_СОСТАВ) - set(files))}")

    start = (P4 / "00-START-HERE.txt").read_text(encoding="utf-8")
    названы = set(re.findall(r"^\s+(\d\d-[A-Za-z0-9-]+\.(?:txt|docx|xlsx|pdf))", start, re.M))
    assert названы == set(P4_СОСТАВ), (
        f"START-HERE P4: лишние {sorted(названы - set(P4_СОСТАВ))}, "
        f"не названы {sorted(set(P4_СОСТАВ) - названы)}")
    assert f"файлов в архиве: {len(P4_СОСТАВ)}" in start

    manifest = P4 / "MANIFEST.md"
    assert sorted(cp.declared(manifest)) == sorted(P4_СОСТАВ)
    assert f"Покупателю уходит {len(P4_СОСТАВ)} файла" in manifest.read_text(encoding="utf-8")

    page = (cp.PAGES / P4_СТРАНИЦА).read_text(encoding="utf-8")
    карточки = re.findall(r'<article class="doc-item"><h3>([^<]+)</h3>', page)
    assert len(карточки) == len(P4_СОСТАВ) - 1, (
        f"страница P4: {len(карточки)} карточек в «Что входит», "
        f"файлов кроме START-HERE {len(P4_СОСТАВ) - 1}")
    assert any("ст. 716" in к for к in карточки), "страница P4 не называет письмо по ст. 716"
    assert not any("Сравнительная таблица" in к for к in карточки)
    assert f"{len(P4_СОСТАВ)} файл" in page


def test_p4_обещание_письма_по_716_подкреплено_файлом() -> None:
    """Акт 42 говорит, что шаблон письма-предупреждения входит в комплект, —
    значит, письмо лежит рядом и не отсылает к документам, которых в P4 нет."""
    акт = текст_файла(P4 / "42-akt-vhodnogo-kontrolya-materialov.docx")
    if "Шаблон письма-предупреждения входит в комплект" in акт:
        письмо = P4 / "43-preduprezhdenie-po-st-716.docx"
        assert письмо.is_file(), "акт 42 обещает письмо по ст. 716, а файла нет"
        текст = текст_файла(письмо)
        assert "ст. 716 ГК РФ" in текст
        assert "отдельный документ комплекта" not in текст, (
            "письмо в P4 отсылает к документу P12, которого в P4 нет")


def test_p4_нет_цены_окупаемости_и_неподтверждённых_свойств() -> None:
    плохие = []
    # Фактическая выдача, а не закреплённый список: вернувшийся файл тоже читается
    for имя in sorted(cp.delivered(P4)):
        текст = текст_файла(P4 / имя)
        if имя != "00-START-HERE.txt":
            # Цена в START-HERE — общая политика линейки (#293 S-1, S-17), не P4
            плохие += [f"{имя}: цена «{m.group(0).strip()}»" for m in ЦЕНА.finditer(текст)]
        низ = текст.lower()
        плохие += [f"{имя}: «{с}»" for с in P4_ЛОЖНЫЕ_ОБЕЩАНИЯ if с in низ]
    страница = (cp.PAGES / P4_СТРАНИЦА).read_text(encoding="utf-8").lower()
    плохие += [f"страница P4: «{с}»" for с in P4_ЛОЖНЫЕ_ОБЕЩАНИЯ if с in страница]
    assert not плохие, "P4 обещает то, чего комплект не подтверждает:\n  " + "\n  ".join(плохие)


def test_p4_архив_воспроизводим() -> None:
    """Файл 43 выводится из вычитанного письма P12 одной объявленной правкой,
    а архив, собранный по правилу `mvb_build_product_zip`, дважды одинаков."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_p4_release", STORAGE / "build_p4_release.py")
    выпуск = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(выпуск)
    assert выпуск.расхождения() == [], выпуск.расхождения()
    assert выпуск.содержимое(выпуск.письмо_p4()) == выпуск.содержимое(выпуск.письмо_p4())

    def архив() -> bytes:
        buf = __import__("io").BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for имя in sorted(cp.delivered(P4)):
                z.writestr(zipfile.ZipInfo(имя, (2026, 9, 28, 0, 0, 0)),
                           (P4 / имя).read_bytes())
        return buf.getvalue()

    первый, второй = архив(), архив()
    assert первый == второй, "архив P4 собирается по-разному из одного источника"
    with zipfile.ZipFile(__import__("io").BytesIO(первый)) as z:
        assert sorted(z.namelist()) == sorted(P4_СОСТАВ)
        for имя in z.namelist():
            assert z.read(имя) == (P4 / имя).read_bytes(), имя


def main() -> int:
    провал = 0
    for имя, проверка in sorted(globals().items()):
        if not имя.startswith("test_"):
            continue
        try:
            проверка()
        except AssertionError as ошибка:
            провал += 1
            print(f"ПРОВАЛ  {имя}\n{ошибка}")
        else:
            print(f"ок  {имя}")
    return 1 if провал else 0


if __name__ == "__main__":
    sys.exit(main())
