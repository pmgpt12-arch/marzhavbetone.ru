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

Пять тестов работают по настоящим байтам, сохранённым захватом с машины
владельца. Они держат кодировку, наличие пути к тексту, печатный вид у
каждой оболочки, извлечение из настоящего фрейма и полноту составной
нормы. Синтетика доказательством починки не считается там, где есть
настоящие байты.

Ни один из них не закрепляет **счёт** страниц или вердиктов: набор растёт
с каждым захватом, и прибитый к снимку тест краснеет на пополнении
доказательств, а не на дефекте. Так уже случилось дважды — с тестом на
испорченные слепки и с тестом на пять оболочек. Закрепляются свойства.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_pdf import is_pdf, pdf_text  # noqa: E402
from legal_extract import (  # noqa: E402
    ARTICLE, MIN_UNIT_CHARS, POINT, decode_body, extract, find_article,
    find_document_links, identifies_act, ips_document_url, ips_print_url,
    looks_damaged, looks_truncated, page_title, parse_units, strip_html)

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


def _real_pages():
    """(norm_id, норма, html, карточка) по каждому сохранённому ответу."""
    import yaml
    fx = FIXTURES
    if not (fx / "pages").exists():
        return []
    registry = {n["norm_id"]: n for n in yaml.safe_load(
        (fx.parent / "norms.yaml").read_text(encoding="utf-8"))["norms"]}
    out = []
    for shot in sorted(fx.glob("*.json")):
        if shot.name == "responses.json":
            continue
        card = json.loads(shot.read_text(encoding="utf-8"))
        page = card.get("page_file")
        if page and (fx / page).exists():
            raw = (fx / page).read_bytes()
            # Ответ бывает не разметкой: Верховный Суд отдаёт постановление
            # файлом PDF. Разбирать его как HTML нельзя — тексту неоткуда
            # взяться, и тест краснел бы на верном документе.
            html = pdf_text(raw) if is_pdf(raw) else decode_body(raw)[0]
            out.append((shot.stem, registry[shot.stem], html, card))
    return out


def test_каждый_сохранённый_ответ_декодируется_без_порчи():
    """Кодировка доказывается настоящими байтами, а не синтетикой.

    Счёт страниц здесь не закрепляется: он растёт с каждым захватом, и
    прибитый к нему тест краснел бы на пополнении доказательств, а не на
    дефекте. Закрепляется свойство — ни одна страница не декодируется в
    знаки замены, ни один заголовок не бит.
    """
    pages = FIXTURES / "pages"
    if not pages.exists():
        print("      (байтов страниц нет)")
        return
    bad = []
    for page in sorted(pages.glob("*")):
        raw = page.read_bytes()
        if not page.is_file() or is_pdf(raw):
            continue
        text, codec = decode_body(raw)
        if looks_damaged(text) or "\ufffd" in page_title(text):
            bad.append(f"{page.name}: {codec}")
    assert not bad, "порча при декодировании:\n  " + "\n  ".join(bad)


def test_у_каждого_ответа_есть_текст_или_путь_к_нему():
    """Главное свойство: тупика быть не должно.

    Ответ либо содержит норму, либо объявляет, где её взять — фреймом,
    печатным видом или ссылкой перечня, либо честно оборван и повторяется.
    Запрещён единственный исход — OTHER: код 200, ответ целый, а пути к
    тексту нет. Он означает, что путь снова потерян и мы этого не заметили.
    """
    verdicts = {}
    registry = _registry()
    for norm_id, norm, html, card in _real_pages():
        base = card.get("final_url") or card.get("url") or ""
        # Слепок, снятый по прежнему адресу реестра, тупиком не считается:
        # адрес заменён, и ответ по нему больше ни о чём не говорит.
        declared = registry[norm_id]["official_source"].split("?")[-1]
        if declared not in (card.get("url") or "") and declared not in base:
            continue
        if looks_truncated(html):
            verdicts[norm_id] = "TRUNCATED — повтор запроса"
        elif extract(strip_html(html), norm).ok:
            verdicts[norm_id] = "EXTRACTABLE DIRECTLY"
        elif ips_document_url(html, base) or ips_print_url(html, base):
            verdicts[norm_id] = "REQUIRES FOLLOW LINK"
        elif find_document_links(html, base, (norm.get("search_path")
                                              or [[]])[0]):
            verdicts[norm_id] = "WRONG PAGE"
        else:
            verdicts[norm_id] = "OTHER"
    if not verdicts:
        print("      (байтов страниц нет)")
        return
    dead = [n for n, v in verdicts.items() if v == "OTHER"]
    assert not dead, "ни текста, ни пути к нему: " + ", ".join(dead)


def test_печатный_вид_объявлен_каждой_оболочкой_ипс():
    """Второй путь к тексту, и он есть у всех оболочек, а не у части."""
    seen, missing = 0, []
    for norm_id, _, html, card in _real_pages():
        base = card.get("final_url") or ""
        if "pravo.gov.ru" not in base or not ips_document_url(html, base):
            continue          # не оболочка: это уже сам текст
        seen += 1
        if not ips_print_url(html, base):
            missing.append(norm_id)
    if not seen:
        print("      (оболочек среди слепков нет)")
        return
    assert not missing, "оболочка без печатного вида: " + ", ".join(missing)


def test_норма_извлекается_из_настоящего_фрейма():
    """Успех пяти норм проверяется по байтам, а не по записи в слепке."""
    checked = 0
    for norm_id, norm, html, card in _real_pages():
        if not card.get("ok"):
            continue
        res = extract(strip_html(html), norm)
        assert res.ok, f"{norm_id}: слепок говорит успех, разбор — {res.reason}"
        assert not res.missing, f"{norm_id}: недобрано {res.missing}"
        checked += 1
    if not checked:
        print("      (успешных слепков нет)")


def test_составная_норма_на_настоящем_фрейме_берёт_все_единицы():
    """Доказательство не может быть половиной нормы.

    Составных норм реестра (196+200, 125+126, 128+148) среди добытых пока
    нет, поэтому свойство проверяется на том акте, который добыт: две
    статьи из настоящего фрейма ГК части второй берутся обе, а
    несуществующая третья роняет весь результат, а не пропускается молча.
    """
    frame = None
    for _, _, html, card in _real_pages():
        if card.get("ok") and "102039276" in (card.get("final_url") or ""):
            frame = strip_html(html)
            break
    if frame is None:
        print("      (фрейма ГК части второй среди слепков нет)")
        return
    act = "ГК РФ часть вторая"
    both = extract(frame, {"act": act, "article": "711, 719"})
    assert both.ok and both.found == ["711", "719"], both.found
    assert "предварительная оп" in both.text or len(both.text) > 800
    half = extract(frame, {"act": act, "article": "711, 999"})
    assert not half.ok and half.missing == ["999"], half.missing



def _responses():
    """Полный след прогона: (запись, html, текст) по каждому ответу."""
    index = FIXTURES / "responses.json"
    if not index.exists():
        return []
    out = []
    for rec in json.loads(index.read_text(encoding="utf-8")):
        page = FIXTURES / rec["page_file"]
        if page.exists():
            html, _ = decode_body(page.read_bytes())
            out.append((rec, html, strip_html(html)))
    return out


def test_надстрочный_номер_статьи_склеивается():
    """`Статья 333<span class="W9">21</span>.` — это статья 333.21.

    Так публикатор печатает статьи с дополнительным индексом. После снятия
    тегов получалось «Статья 333 21», и «Статья 333.21» не находилась ни
    разу: замер по семимегабайтному печатному виду НК — вхождений ноль при
    261 найденной статье. На этом стояли оба отказа по НК.
    """
    html = ('<p>Статья 333<span class="W9">21</span>. Размеры пошлины</p>'
            '<p>1. По делам, рассматриваемым судами, пошлина уплачивается в '
            'следующих размерах, если иное не установлено настоящей статьёй '
            'и главой 25.3 настоящего Кодекса, с учётом особенностей.</p>'
            '<p>Статья 333<sup>22</sup>. Особенности уплаты</p>')
    body = strip_html(html)
    assert "Статья 333.21." in body, body[:120]
    assert "Статья 333.22." in body
    res = extract(body + " " + DOBIVKA, {"act": "НК РФ часть вторая",
                                         "article": "333.21"})
    assert res.ok, res.reason


def test_нк_извлекается_из_настоящего_печатного_вида():
    """Сквозная проверка на семи мегабайтах настоящего ответа портала."""
    got = 0
    for rec, html, body in _responses():
        if "print=1&nd=102067058" not in rec["url"]:
            continue
        for num in ("333.21", "333.40"):
            res = extract(body, {"act": "НК РФ часть вторая", "article": num})
            assert res.ok, f"ст. {num}: {res.reason}"
            assert len(res.text) > 1000, f"ст. {num}: текста {len(res.text)}"
            got += 1
    if not got:
        print("      (печатного вида НК среди ответов нет)")


def test_чужой_документ_по_адресу_реестра_отвергается():
    """`nd=102078170` отдаёт Распоряжение Правительства, а не АПК.

    Без опознания акта совпадения номера статьи хватило бы, чтобы текст
    чужого документа лёг в доказательство под именем АПК. Это хуже отказа:
    гейт получил бы зелень на подложном тексте.
    """
    checked = 0
    for rec, html, body in _responses():
        if "102078170" not in rec["url"]:
            continue
        checked += 1
        assert not identifies_act(html, body, ["арбитражный процессуальный "
                                               "кодекс"]), rec["url"]
    if not checked:
        print("      (ответов по адресу АПК среди сохранённых нет)")


def test_опознание_не_отвергает_настоящие_акты():
    """Защита не должна ронять то, что уже работает."""
    pairs = (("102039276", ["гражданский кодекс", "часть вторая"]),
             ("102067058", ["налоговый кодекс", "часть вторая"]),
             ("102078527", ["о несостоятельности"]))
    for nd, terms in pairs:
        for rec, html, body in _responses():
            if nd in rec["url"] and ("page=all" in rec["url"]
                                     or "print=1" in rec["url"]):
                assert identifies_act(html, body, terms), rec["url"]


def test_оборванный_ответ_опознаётся_обрывом():
    """Код 200, заголовок верный, но `</html>` нет — ответ недокачан."""
    seen = 0
    for rec, html, body in _responses():
        if rec["url"].endswith("nd=102033239") and rec["length"] < 10000:
            seen += 1
            assert looks_truncated(html), "обрыв не опознан"
            assert not ips_document_url(html, rec["url"]), \
                "в обрезке не может быть фрейма с текстом"
    for rec, html, body in _responses():
        if "page=all" in rec["url"]:
            assert not looks_truncated(html), f"ложный обрыв: {rec['url']}"
    if not seen:
        print("      (оборванного ответа среди сохранённых нет)")




def _registry():
    import yaml
    return {n["norm_id"]: n for n in yaml.safe_load(
        (FIXTURES.parent / "norms.yaml").read_text(encoding="utf-8"))["norms"]}


def test_адрес_апк_ведёт_на_апк_а_не_на_прежний_документ():
    """Прежний `nd=102078170` отдавал Распоряжение Правительства № 1214-р.

    Проверено слепками 16.08.2026: и оболочка, и фрейм, и печатный вид по
    тому адресу — чужой документ. Идентификатор заменён на проверенный
    владельцем по официальному публикатору (АПК РФ от 24.07.2002 № 95-ФЗ).
    Тест держит замену: возврат прежнего номера — регресс, а не правка.
    """
    reg = _registry()
    for norm_id in ("apk-4-5", "apk-125-126", "apk-128-148"):
        src = reg[norm_id]["official_source"]
        assert "nd=102079219" in src, f"{norm_id}: {src}"
        assert "102078170" not in src, f"{norm_id}: вернулся прежний адрес"
        assert reg[norm_id]["document_match"] == [
            "арбитражный процессуальный кодекс"], norm_id


def test_прежний_адрес_апк_не_опознаётся_как_апк():
    """Сохранённые байты доказывают, почему замена понадобилась."""
    checked = 0
    for rec, html, body in _responses():
        if "102078170" not in rec["url"]:
            continue
        checked += 1
        assert not identifies_act(html, body,
                                  ["арбитражный процессуальный кодекс"])
    if not checked:
        print("      (ответов по прежнему адресу среди сохранённых нет)")


def test_ппвс_идёт_прямо_на_документ_а_не_в_перечень():
    """Перечень `/documents/own/` собирается скриптом и ссылок не даёт.

    Замер по сохранённой странице: 85 ссылок, ни одной на документ. Обход
    раздела снят, адрес документа проверен владельцем.
    """
    norm = _registry()["ppvs-7-2016"]
    assert norm["official_source"].rstrip("/").endswith("/documents/own/8478"), \
        norm["official_source"]
    assert not norm.get("search_path"), "обход перечня больше не нужен"
    kind, units, _ = parse_units(norm["article"], norm["act"])
    assert (kind, units) == (POINT, ["42", "48", "84"])


def test_все_три_пункта_постановления_обязательны():
    """Два пункта из трёх доказательством не считаются."""
    norm = {"act": "Постановление Пленума ВС РФ от 24.03.2016 № 7",
            "article": "пп. 42, 48, 84"}
    two = ("Пленум Верховного Суда постановляет. "
           "42. Если законом или соглашением сторон установлена неустойка, "
           "кредитор вправе предъявить требование о применении одной из мер "
           "ответственности, не допуская их суммирования по одному periodu. "
           "48. Сумма процентов, подлежащих взысканию по правилам статьи 395 "
           "Кодекса, определяется на день вынесения решения судом исходя из "
           "периодов, имевших место до указанного дня, если иное не следует. "
           + DOBIVKA)
    res = extract(two, norm)
    assert not res.ok, "84-го пункта нет — это не доказательство"
    assert res.missing == ["84"], res.missing


def test_каждая_норма_реестра_объявляет_реквизиты_опознания():
    """Без опознания чужой документ снова сможет стать доказательством."""
    without = [n for n, v in _registry().items() if not v.get("document_match")]
    assert not without, "нормы без document_match: " + ", ".join(without)



def test_адреса_проверенных_актов_не_возвращаются_к_прежним():
    """Каждый идентификатор давался владельцем после проверки. Регресс.

    Замер 16.08.2026: `nd=102078170` отдавал Распоряжение Правительства
    вместо АПК, перечень ВС не вёл к постановлению, а у ФЗ об
    исполнительном производстве есть предшественник `102048381`,
    утративший силу. Ошибка в идентификаторе не видна ничем, кроме
    опознания акта, — и стоит она целого захода владельца.
    """
    reg = _registry()
    assert "nd=102117007" in reg["fz-229-8"]["official_source"]
    assert "102048381" not in reg["fz-229-8"]["official_source"], \
        "прежний закон об исполнительном производстве, утратил силу"
    assert reg["plenum-54-57"]["official_source"].rstrip("/").endswith(
        "/documents/own/8524"), reg["plenum-54-57"]["official_source"]
    assert "nd=102079219" in reg["apk-4-5"]["official_source"]
    assert reg["ppvs-7-2016"]["official_source"].rstrip("/").endswith(
        "/documents/own/8478")


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
