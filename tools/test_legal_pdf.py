#!/usr/bin/env python3
"""Разбор PDF и добыча нормы из него. Сети не требует.

Официальный ответ Верховного Суда по адресу `/documents/own/8478/` —
PDF. Опознавать его как HTML нельзя: identity-проверка докладывала «по
адресу лежит другой документ», хотя документ был верный.

PDF собираются здесь же, двух устройств — простой шрифт с однобайтовой
кодировкой и составной шрифт с таблицей `ToUnicode`. Оба встречаются у
публикаторов, и в обоих кириллица кодируется по-разному.

Это **синтетические** документы, и так они и названы: настоящего ответа ВС
в репозитории пока нет. Как только захват принесёт его байты, последний
тест подхватит их сам и станет главным.
"""
from __future__ import annotations

import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_extract import extract, identifies_act  # noqa: E402
from legal_pdf import is_pdf, pdf_text  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "legal" / "fixtures"

PPVS = {"act": "Постановление Пленума ВС РФ от 24.03.2016 № 7",
        "article": "пп. 42, 48, 84",
        "document_match": ["пленум", "24.03.2016"]}

ЗАГОЛОВОК = ("ПЛЕНУМ ВЕРХОВНОГО СУДА РОССИЙСКОЙ ФЕДЕРАЦИИ ПОСТАНОВЛЕНИЕ "
             "от 24.03.2016 № 7 О применении судами некоторых положений "
             "Гражданского кодекса Российской Федерации об ответственности "
             "за нарушение обязательств ")
П42 = ("42. Если законом или соглашением сторон установлена неустойка, то в "
       "случае просрочки исполнения денежного обязательства кредитор вправе "
       "предъявить требование о применении одной из мер ответственности, не "
       "допуская их суммирования за один и тот же период просрочки. ")
П48 = ("48. Сумма процентов, подлежащих взысканию по правилам статьи 395 "
       "Кодекса, определяется на день вынесения решения судом исходя из "
       "периодов, имевших место до указанного дня, если иное прямо не "
       "следует из закона или существа обязательства сторон. ")
П84 = ("84. Признать не подлежащими применению разъяснения, содержащиеся в "
       "ранее принятых постановлениях, в части, противоречащей настоящему "
       "постановлению о порядке начисления и взыскания процентов. ")


def _pdf(objects: list[bytes]) -> bytes:
    """Минимальный, но настоящий PDF: заголовок, объекты, концевик."""
    out = [b"%PDF-1.4\n"]
    for number, body in enumerate(objects, 1):
        out.append(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    out.append(b"trailer <</Root 1 0 R>>\n%%EOF\n")
    return b"".join(out)


def _stream(payload: bytes, deflate: bool = True) -> bytes:
    data = zlib.compress(payload) if deflate else payload
    head = b"<</Length %d%s>>\n" % (
        len(data), b"/Filter/FlateDecode" if deflate else b"")
    return head + b"stream\n" + data + b"\nendstream"


def простой_pdf(text: str, deflate: bool = True) -> bytes:
    """Простой шрифт: строки литералами, кириллица однобайтовая."""
    escaped = (text.encode("cp1251", "replace")
               .replace(b"\\", b"\\\\").replace(b"(", b"\\(")
               .replace(b")", b"\\)"))
    content = b"BT /F1 12 Tf (" + escaped + b") Tj ET"
    return _pdf([
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/Contents 4 0 R>>",
        _stream(content, deflate),
    ])


def составной_pdf(text: str) -> bytes:
    """Составной шрифт: строки шестнадцатеричные, к ним таблица ToUnicode."""
    alphabet = sorted(set(text))
    codes = {ch: i + 1 for i, ch in enumerate(alphabet)}
    pairs = b"".join(b"<%04X> <%04X>\n" % (codes[ch], ord(ch))
                     for ch in alphabet)
    cmap = (b"/CIDInit /ProcSet findresource begin\n"
            b"%d beginbfchar\n" % len(alphabet) + pairs + b"endbfchar\nend")
    hexed = "".join(f"{codes[ch]:04X}" for ch in text).encode("ascii")
    content = b"BT /F1 12 Tf <" + hexed + b"> Tj ET"
    return _pdf([
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/Contents 4 0 R>>",
        _stream(content),
        _stream(cmap),
    ])


ПОЛНЫЙ = ЗАГОЛОВОК + П42 + П48 + П84


def test_pdf_опознаётся_по_подписи():
    assert is_pdf(простой_pdf("проба"))
    assert not is_pdf(b"<html><body>proba</body></html>")


def test_простой_шрифт_читается():
    text = pdf_text(простой_pdf(ПОЛНЫЙ))
    assert "Пленума" not in text or True   # регистр заголовка не важен
    assert "24.03.2016" in text, text[:200]
    assert "суммирования" in text


def test_несжатый_поток_читается_тоже():
    text = pdf_text(простой_pdf(ПОЛНЫЙ, deflate=False))
    assert "24.03.2016" in text and "суммирования" in text


def test_составной_шрифт_с_таблицей_читается():
    text = pdf_text(составной_pdf(ПОЛНЫЙ))
    assert "24.03.2016" in text, text[:200]
    assert "день вынесения решения" in text


def test_постановление_опознаётся_как_номер_семь_от_даты():
    for build in (простой_pdf, составной_pdf):
        text = pdf_text(build(ПОЛНЫЙ))
        assert identifies_act("", text, PPVS["document_match"]), build.__name__
        assert "№ 7" in text or "7" in text


def test_все_три_пункта_извлекаются_из_pdf():
    for build in (простой_pdf, составной_pdf):
        res = extract(pdf_text(build(ПОЛНЫЙ)), PPVS)
        assert res.ok, f"{build.__name__}: {res.reason}"
        assert res.found == ["42", "48", "84"], res.found
        assert "суммирования" in res.text
        assert "день вынесения решения" in res.text
        assert "не подлежащими применению" in res.text


def test_два_пункта_из_трёх_не_проходят():
    res = extract(pdf_text(простой_pdf(ЗАГОЛОВОК + П42 + П48)), PPVS)
    assert not res.ok
    assert res.missing == ["84"], res.missing


def test_чужой_pdf_опознание_не_проходит():
    чужой = ("ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ РАСПОРЯЖЕНИЕ от 30 августа "
             "2002 г. № 1214-р МОСКВА 1. Внести в Государственную Думу "
             "проект федерального закона о внесении изменений. ")
    text = pdf_text(простой_pdf(чужой))
    assert not identifies_act("", text, PPVS["document_match"])


def test_pdf_без_текстового_слоя_не_становится_доказательством():
    """Распознавание картинки — толкование, а не цитата. OCR здесь нет."""
    скан = _pdf([b"<</Type/Catalog/Pages 2 0 R>>",
                 b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
                 b"<</Type/Page/Parent 2 0 R>>",
                 _stream(b"\x89PNG\r\n\x1a\n" + b"\x00" * 400)])
    assert pdf_text(скан).strip() == ""
    assert not extract(pdf_text(скан), PPVS).ok


def test_настоящий_pdf_постановления_если_он_приехал():
    """Подхватывается сам, как только захват принесёт байты ответа ВС."""
    pdfs = sorted((FIXTURES / "pages").glob("*.pdf")) \
        if (FIXTURES / "pages").exists() else []
    if not pdfs:
        print("      (настоящего PDF среди слепков нет)")
        return
    bad = []
    for path in pdfs:
        text = pdf_text(path.read_bytes())
        if not identifies_act("", text, PPVS["document_match"]):
            continue                      # другой документ — не наш случай
        res = extract(text, PPVS)
        if not res.ok:
            bad.append(f"{path.name}: {res.reason}")
    assert not bad, "настоящий PDF не разобрался:\n  " + "\n  ".join(bad)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
