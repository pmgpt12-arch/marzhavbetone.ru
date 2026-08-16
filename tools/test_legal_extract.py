#!/usr/bin/env python3
"""Разбор ответа публикатора на размеченных случаях. Сети не требует.

Зачем именно так. Официальные публикаторы из рабочей среды закрыты (замер
16.08.2026: `pravo.gov.ru` — 403 на CONNECT, `vsrf.ru` не резолвится), а
прогон владельца с внешней машины дал семнадцать отказов подряд. Чинить
разбор, проверяя его только следующим прогоном на чужом компьютере, значит
чинить вслепую и через сутки на круг. Поэтому разбор — чистая функция, а
здесь тела ответов и ожидаемый результат.

Случаи ниже **синтетические и названы синтетическими**: они воспроизводят
формы, которые публикаторы дают заведомо, а не байты конкретной страницы.

Четыре теста работают по настоящим данным — шести страницам, снятым с
машины владельца 16.08.2026 и сохранённым **байтами**. Они держат
кодировку, распознавание оболочки ИПС, адрес текста внутри неё и вердикт
по каждому уникальному ответу. Синтетика доказательством починки не
считается там, где есть настоящие байты.

Прежний тест на испорченные слепки снят: он описывал состояние до
повторного захвата, и после починки кодировки перестал быть верным. Его
работу делает `test_кодировка_реальных_страниц_определяется_верно`, и
делает строже — на байтах, а не на пересказе.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_extract import (  # noqa: E402
    ARTICLE, MIN_UNIT_CHARS, POINT, decode_body, extract, find_article,
    find_document_links, ips_document_url, looks_damaged, page_title,
    parse_units, strip_html)

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "legal" / "fixtures"

GK = {"norm_id": "gk-191", "act": "ГК РФ часть первая", "article": "191"}
TELO_191 = ("Статья 191. Начало срока, определенного периодом времени. "
            "Течение срока, определенного периодом времени, начинается на "
            "следующий день после календарной даты или наступления события, "
            "которым определено его начало. ")
TELO_192 = ("Статья 192. Окончание срока, определенного периодом времени. "
            "Срок, исчисляемый годами, истекает в соответствующие месяц и "
            "число последнего года срока. ")
OGLAVLENIE = ("Гражданский кодекс Российской Федерации. Содержание. "
              "Статья 191. Начало срока Статья 192. Окончание срока "
              "Статья 193. Окончание срока в нерабочий день. ")
DOBIVKA = "Прочий текст документа. " * 30


def test_полный_текст_кодекса_разбирается():
    res = extract(DOBIVKA + TELO_191 + TELO_192, GK)
    assert res.ok, res.reason
    assert "начинается на следующий день" in res.text
    assert "Статья 192" not in res.text, "границей служит следующая статья"


def test_оглавление_не_подменяет_текст_нормы():
    """Первое вхождение — заголовок из перечня; берётся длинное."""
    res = extract(OGLAVLENIE + DOBIVKA + TELO_191 + TELO_192, GK)
    assert res.ok, res.reason
    assert len(res.text) > MIN_UNIT_CHARS
    assert "которым определено его начало" in res.text


def test_одно_оглавление_без_текста_отвергается():
    """Тихая подмена страшнее отказа: 25 знаков заголовка выглядят успехом."""
    res = extract(OGLAVLENIE + DOBIVKA, GK)
    assert not res.ok
    assert "оглавление" in res.reason, res.reason


def test_карточка_документа_названа_карточкой():
    res = extract("Портал правовой информации. Карточка документа.", GK)
    assert not res.ok
    assert "карточка" in res.reason, res.reason


def test_страница_не_найдено_названа_отказом():
    res = extract("Документ не найден. " + DOBIVKA, GK)
    assert not res.ok
    assert "не найдено" in res.reason or "отказ" in res.reason, res.reason


def test_постановление_пленума_ищется_пунктами():
    norm = {"norm_id": "ppvs-7-2016",
            "act": "Постановление Пленума ВС РФ от 24.03.2016 № 7",
            "article": "пп. 42, 48, 84"}
    kind, units, _ = parse_units(norm["article"], norm["act"])
    assert kind == POINT, "у постановления Пленума пунктов, а не статей"
    assert units == ["42", "48", "84"]

    body = ("Пленум Верховного Суда Российской Федерации постановляет. "
            "41. Предыдущий пункт разъяснения о порядке начисления процентов "
            "по денежному обязательству и о соотношении требований. "
            "42. Если законом или соглашением сторон установлена неустойка, "
            "то в случае просрочки исполнения денежного обязательства "
            "кредитор вправе предъявить требование о применении одной из мер "
            "ответственности, не допуская их суммирования. "
            "48. Сумма процентов, подлежащих взысканию по правилам статьи 395 "
            "Кодекса, определяется на день вынесения решения судом исходя из "
            "периодов, имевших место до указанного дня. "
            "84. Признать не подлежащим применению постановление Пленума в "
            "части, противоречащей настоящим разъяснениям о порядке расчёта. ")
    res = extract(body, norm)
    assert res.ok, res.reason
    assert res.found == ["42", "48", "84"]
    assert "суммирования" in res.text and "день вынесения решения" in res.text


def test_составная_норма_берёт_все_статьи():
    norm = {"norm_id": "gk-196-200", "act": "ГК РФ часть первая",
            "article": "196, 200"}
    body = (DOBIVKA +
            "Статья 196. Общий срок исковой давности. Общий срок исковой "
            "давности составляет три года со дня, определяемого в "
            "соответствии со статьей 200 настоящего Кодекса. " +
            "Статья 200. Начало течения срока исковой давности. Если законом "
            "не установлено иное, течение срока исковой давности начинается "
            "со дня, когда лицо узнало или должно было узнать о нарушении "
            "своего права. " + TELO_192)
    res = extract(body, norm)
    assert res.ok, res.reason
    assert res.found == ["196", "200"], res.found
    assert "три года" in res.text and "узнало или должно было узнать" in res.text


def test_недостающая_вторая_статья_не_выдаётся_за_успех():
    """Прежний разбор брал последний номер и молчал о первом."""
    norm = {"norm_id": "gk-196-200", "act": "ГК РФ часть первая",
            "article": "196, 200"}
    body = (DOBIVKA +
            "Статья 200. Начало течения срока исковой давности. Если законом "
            "не установлено иное, течение срока исковой давности начинается "
            "со дня, когда лицо узнало или должно было узнать о нарушении "
            "своего права и о том, кто является надлежащим ответчиком. ")
    res = extract(body, norm)
    assert not res.ok
    assert res.missing == ["196"], res.missing


def test_номер_статьи_числом_не_теряет_разряд():
    """`article: 333.40` без кавычек YAML делает числом 333.4."""
    kind, units, _ = parse_units(333.40, "НК РФ часть вторая")
    assert kind == ARTICLE
    assert units == ["333.4"], units  # именно так ломалось
    kind, units, _ = parse_units("333.40", "НК РФ часть вторая")
    assert units == ["333.40"], units


def test_часть_статьи_ищет_статью_а_подраздел_записывает():
    kind, units, subs = parse_units("ч. 5 ст. 4", "АПК РФ")
    assert (kind, units, subs) == (ARTICLE, ["4"], ["5"])
    kind, units, subs = parse_units("п. 2.1 ст. 7", "ФЗ от 26.10.2002 № 127-ФЗ")
    assert (kind, units, subs) == (ARTICLE, ["7"], ["2.1"])


def test_неразрывный_пробел_не_прячет_маркер():
    res = extract(DOBIVKA + TELO_191.replace("Статья 191", "Статья 191")
                  + TELO_192, GK)
    assert res.ok, res.reason


def test_соседний_номер_не_ловится_префиксом():
    body = DOBIVKA + TELO_191 + TELO_192
    assert not find_article(body, "19"), "«Статья 19» не равна «Статья 191»"
    assert not find_article(body, "1911")


def test_кодировка_берётся_из_метатега():
    raw = ('<html><head><meta http-equiv="Content-Type" content="text/html; '
           'charset=windows-1251"></head><body>' + TELO_191
           + "</body></html>").encode("cp1251")
    text, codec = decode_body(raw, header_charset="")
    assert "windows-1251" in codec, codec
    assert "Статья 191" in text and "�" not in text


def test_кодировка_без_объявления_определяется_пробой():
    """Ровно случай pravo.gov.ru: `text/html` без charset и без метатега."""
    raw = ("<html><body>" + TELO_191 + "</body></html>").encode("cp1251")
    text, codec = decode_body(raw, header_charset="")
    assert "cp1251" in codec, codec
    assert "Статья 191" in text and "�" not in text


def test_utf8_страница_пробой_не_ломается():
    raw = ("<html><body>" + TELO_191 + "</body></html>").encode("utf-8")
    text, _ = decode_body(raw, header_charset="")
    assert "Статья 191" in text and "�" not in text


def test_норма_извлекается_из_cp1251_страницы_целиком():
    """Сквозной путь: байты → декодирование → разметка → извлечение."""
    raw = ("<html><body><p>" + DOBIVKA + TELO_191 + "</p><p>" + TELO_192
           + "</p></body></html>").encode("cp1251")
    text, _ = decode_body(raw, header_charset="")
    res = extract(strip_html(text), GK)
    assert res.ok, res.reason
    assert "которым определено его начало" in res.text


def test_порча_декодирования_называется_порчей():
    broken = ("<html><body>" + TELO_191 + "</body></html>"
              ).encode("cp1251").decode("utf-8", "replace")
    assert looks_damaged(broken)
    assert not looks_damaged(TELO_191 + DOBIVKA)


def test_ссылка_на_документ_находится_в_фактическом_перечне():
    listing = ('<ul>'
               '<li><a href="/documents/all/">Все документы</a></li>'
               '<li><a href="/documents/own/28123/">Постановление Пленума '
               'Верховного Суда РФ от 24.03.2016 № 7</a></li>'
               '<li><a href="/documents/own/28999/">Постановление Пленума '
               'от 21.01.2016 № 1</a></li></ul>')
    hits = find_document_links(listing, "https://www.vsrf.ru/documents/own/",
                               ["24.03.2016"])
    assert hits == ["https://www.vsrf.ru/documents/own/28123/"], hits


def test_переход_не_делается_без_реквизитов():
    listing = '<a href="/x/">Постановление Пленума от 24.03.2016 № 7</a>'
    assert find_document_links(listing, "https://www.vsrf.ru/", []) == []


def test_адрес_текста_акта_берётся_из_оболочки_ипс():
    shell = ('<html><body><iframe id="tempframe" src="about:blank"></iframe>'
             '<iframe id="list" frameborder="0" '
             'src="?doc_itself=&amp;nd=102033239&amp;page=1&amp;rdk=156" '
             'onload="onDocRefsLoaded();"></iframe></body></html>')
    base = "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102033239"
    assert ips_document_url(shell, base, page="all") == (
        "http://pravo.gov.ru/proxy/ips/"
        "?doc_itself=&nd=102033239&page=all&rdk=156")
    assert ips_document_url(shell, base, page="7").endswith("page=7&rdk=156")
    assert ips_document_url("<html><body>нет фрейма</body></html>", base) == ""


def test_оболочка_ипс_распознана_во_всех_сохранённых_страницах():
    """Пять актов на настоящих байтах: адрес текста находится у каждого."""
    pages = FIXTURES / "pages"
    if not pages.exists():
        print("      (байтов страниц нет)")
        return
    missing = []
    for shot in sorted(FIXTURES.glob("*.json")):
        card = json.loads(shot.read_text(encoding="utf-8"))
        page = card.get("page_file")
        if not page or not (FIXTURES / page).exists():
            continue
        html, _ = decode_body((FIXTURES / page).read_bytes())
        if "pravo.gov.ru" not in (card.get("final_url") or ""):
            continue
        if not ips_document_url(html, card["final_url"]):
            missing.append(shot.stem)
    assert not missing, ("оболочка ИПС без адреса текста: "
                         + ", ".join(missing))


def test_вердикт_по_каждому_реальному_ответу():
    """По каждому уникальному ответу — явный вердикт на его настоящих байтах.

    Замер 16.08.2026 по шести сохранённым страницам. Пять из них — оболочка
    ИПС: код 200, кодировка windows-1251, декодируется без порчи, заголовок
    акта на месте, слово «Статья» встречается **ноль раз**. Текста акта в
    этом ответе нет вовсе, он во фрейме `doc_itself`. Шестая — перечень
    документов Верховного Суда, UTF-8, тоже без текста постановления.

    Отсюда вердикты: ни один ответ не EXTRACTABLE DIRECTLY, пять —
    REQUIRES FOLLOW LINK через фрейм, один — WRONG PAGE с переходом по
    разделу. Тест держит именно это: если завтра портал начнёт отдавать
    текст сразу, вердикт разойдётся и его придётся пересмотреть осознанно.
    """
    pages = FIXTURES / "pages"
    if not pages.exists():
        print("      (байтов страниц нет)")
        return
    import yaml
    registry = {n["norm_id"]: n for n in yaml.safe_load(
        (FIXTURES.parent / "norms.yaml").read_text(encoding="utf-8"))["norms"]}

    verdicts, wrong = {}, []
    for shot in sorted(FIXTURES.glob("*.json")):
        card = json.loads(shot.read_text(encoding="utf-8"))
        page = card.get("page_file")
        if not page or not (FIXTURES / page).exists():
            continue
        norm = registry[shot.stem]
        html, codec = decode_body((FIXTURES / page).read_bytes())
        if looks_damaged(html):
            wrong.append(f"{shot.stem}: декодировано как {codec}, знаки замены")
            continue
        body = strip_html(html)
        if extract(body, norm).ok:
            verdicts[page] = "EXTRACTABLE DIRECTLY"
        elif ips_document_url(html, card["final_url"]):
            verdicts[page] = "REQUIRES FOLLOW LINK"
        elif find_document_links(html, card["final_url"],
                                 (norm.get("search_path") or [[]])[0]):
            verdicts[page] = "WRONG PAGE"
        else:
            wrong.append(f"{shot.stem}: ни текста, ни пути к нему — OTHER")
    assert not wrong, "неразобранные ответы:\n  " + "\n  ".join(wrong)
    assert len(verdicts) == 6, f"уникальных ответов {len(verdicts)}, ждали 6"
    tally = {}
    for v in verdicts.values():
        tally[v] = tally.get(v, 0) + 1
    assert tally == {"REQUIRES FOLLOW LINK": 5, "WRONG PAGE": 1}, tally


def test_кодировка_реальных_страниц_определяется_верно():
    """Починка кодировки доказывается настоящими байтами, не синтетикой."""
    pages = FIXTURES / "pages"
    if not pages.exists():
        print("      (байтов страниц нет)")
        return
    seen = {}
    for page in sorted(pages.glob("*.html")):
        text, codec = decode_body(page.read_bytes())
        seen[page.name] = codec
        assert not looks_damaged(text), f"{page.name}: порча при {codec}"
        assert "�" not in page_title(text), f"{page.name}: заголовок битый"
    assert sorted(seen.values()).count("windows-1251") == 5, seen
    assert sorted(seen.values()).count("utf-8") == 1, seen


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
