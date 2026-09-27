#!/usr/bin/env python3
"""Проверки кандидата S1 «Система получения оплаты за выполненные работы».

Issue pmgpt12-arch/marzhavbetone.ru#263. Проверяется фактически собранный
кандидат `tools/candidates/s1-oplata-za-raboty/`, а не намерения генератора.

Три слоя:
1. Статические проверки — только стандартная библиотека, идут в CI:
   состав против карты маршрута, у каждого шага есть инструмент и
   подтверждение, в текстах покупателя нет обязательной допокупки, формы
   содержат рабочую табличную часть, кандидат не адресован ни одним sku.
2. Эталон расчёта процентов (`s1_interest.py`) против независимого
   подневного подсчёта: частичная оплата внутри периода, 12 оплат.
3. Функциональный прогон в LibreOffice на временных копиях: книги
   заполняются входами, пересчитываются `soffice --headless` и читаются
   обратно. Нет `soffice` или openpyxl — слой печатается строкой
   «ПРОПУСК» с причиной, а не проходит молча.

    python3 tools/test_s1_candidate.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s1_interest as SI                                   # noqa: E402
import s1_route as R                                        # noqa: E402
import test_delivery_artifacts as TDA                       # noqa: E402

C = R.CANDIDATE
ПРОПУСКИ: list[str] = []


# ───────────────────────────── чтение ─────────────────────────────

def docx_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def docx_text(path: Path) -> str:
    xml = docx_xml(path)
    return html.unescape(" ".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)))


def xlsx_text(path: Path) -> str:
    out = []
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n == "xl/sharedStrings.xml" or re.match(r"xl/worksheets/sheet\d+\.xml$", n):
                xml = z.read(n).decode("utf-8")
                out += re.findall(r"<t[^>]*>([^<]*)</t>", xml)
                out += re.findall(r"<f>([^<]*)</f>", xml)
    return html.unescape(" ".join(out))


def buyer_text(path: Path) -> str:
    if path.suffix == ".docx":
        return docx_text(path)
    if path.suffix == ".xlsx":
        return xlsx_text(path)
    return path.read_text(encoding="utf-8")


def sheet_xml(book: Path, title: str) -> str:
    with zipfile.ZipFile(book) as z:
        wbx = z.read("xl/workbook.xml").decode("utf-8")
        rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
        rid = re.search(rf'<sheet[^>]*name="{re.escape(title)}"[^>]*r:id="([^"]+)"', wbx).group(1)
        target = re.search(rf'<Relationship[^>]*Id="{rid}"[^>]*Target="([^"]+)"', rels) or \
            re.search(rf'<Relationship[^>]*Target="([^"]+)"[^>]*Id="{rid}"', rels)
        t = target.group(1).lstrip("/")
        return z.read(t if t.startswith("xl/") else "xl/" + t).decode("utf-8")


def formulas(book: Path, title: str) -> list[str]:
    return [html.unescape(f) for f in re.findall(r"<f>([^<]*)</f>", sheet_xml(book, title))]


def delivered() -> list[Path]:
    return sorted(p for p in C.iterdir() if p.is_file() and p.name not in R.INTERNAL)


# ─────────────────────── 1. статические проверки ───────────────────────

def test_состав_совпадает_с_картой() -> None:
    фактически = {p.name for p in delivered()}
    assert фактически == set(R.FILES), (
        f"лишние: {sorted(фактически - set(R.FILES))}; нет: {sorted(set(R.FILES) - фактически)}")
    for n in R.INTERNAL:
        assert (C / n).is_file(), f"нет служебного файла {n}"


def test_карта_маршрута_не_отстала_от_источника() -> None:
    на_диске = json.loads((C / "ROUTE-MAP.json").read_text(encoding="utf-8"))
    assert на_диске == json.loads(json.dumps(R.route_map(), ensure_ascii=False)), (
        "ROUTE-MAP.json расходится с s1_route.py — пересоберите кандидат")


def test_каждый_шаг_имеет_инструмент_подтверждение_и_следующий_шаг() -> None:
    ids = [s["id"] for s in R.STEPS]
    assert ids == [f"S{i}" for i in range(len(ids))], "шаги должны идти S0..Sn подряд"
    for s in R.STEPS:
        assert s["tools"], f"{s['id']}: нет инструмента"
        for t in s["tools"]:
            assert t in R.FILES, f"{s['id']}: инструмент {t} не входит в состав"
        assert len(s["confirmation"]) > 30, f"{s['id']}: нет проверяемого подтверждения"
        if s["next"] == R.SCENARIO_NEXT:
            assert s["id"] in ("S0", "S1"), f"{s['id']}: следующий шаг «по ситуации» допустим только у S0 и S1"
        else:
            assert s["next"] in ids or s["next"] == "END", f"{s['id']}: следующий шаг {s['next']} не существует"
        for b in s["boundaries"]:
            assert b in R.BOUNDARIES, f"{s['id']}: неизвестная граница {b}"
    # каждый шаг, кроме выбора ситуации и проверки по желанию, лежит на пути
    # хотя бы одной ситуации
    вне_путей = set(ids) - R.scenario_steps() - {"S0", "S1"}
    assert not вне_путей, f"шаги вне всех путей: {sorted(вне_путей)}"


def _шаг(sid: str) -> dict:
    return next(s for s in R.STEPS if s["id"] == sid)


def test_каждый_сценарий_имеет_однозначный_старт_и_следующий_шаг() -> None:
    ids = [sc["id"] for sc in R.SCENARIOS]
    assert len(ids) == len(set(ids)), "повторяющиеся ситуации"
    for sc in R.SCENARIOS:
        путь = sc["path"]
        assert sc["start"] == путь[0], f"{sc['id']}: стартовый шаг не совпадает с началом пути"
        assert len(путь) == len(set(путь)), f"{sc['id']}: шаг повторяется в пути"
        for a, b in zip(путь, путь[1:]):
            assert _шаг(a)["next"] == b, (
                f"{sc['id']}: после {a} в пути {b}, а в шаге {a} следующим назван {_шаг(a)['next']}")
        assert _шаг(путь[-1])["next"] == "END", f"{sc['id']}: путь не доходит до конца маршрута"
    # то же в файлах покупателя: стартовый и следующий шаг в карте ситуаций,
    # путь — в алгоритме
    карта = docx_text(C / "01-karta-situacii-i-granic.docx")
    алгоритм = docx_text(C / "03-algoritm-dejstviy.docx")
    старт = START_HERE()
    for sc in R.SCENARIOS:
        путь = " → ".join(x[1:] for x in sc["path"])
        строка = (f"{sc['id']}. {sc['title']} {sc['signs']} Шаг {sc['start'][1:]} {путь} "
                  f"шаг {sc['path'][1][1:]}")
        assert строка in карта, f"файл 01: строка ситуации {sc['id']} расходится с картой маршрута"
        assert f"{sc['id']}. {sc['title']} Шаг {sc['start'][1:]} {путь}" in алгоритм, (
            f"файл 03: путь ситуации {sc['id']} расходится с картой маршрута")
        assert f"Начать: шаг {sc['start'][1:]}. Путь: шаги {путь}." in старт, (
            f"00-START-HERE: ситуация {sc['id']} расходится с картой маршрута")
    карта_json = json.loads((C / "ROUTE-MAP.json").read_text(encoding="utf-8"))
    assert карта_json["scenarios"] == json.loads(json.dumps(R.SCENARIOS, ensure_ascii=False))


def START_HERE() -> str:
    return (C / "00-START-HERE.txt").read_text(encoding="utf-8")


def test_основной_сценарий_ведёт_напрямую_s6_s12() -> None:
    прямой = [f"S{i}" for i in range(6, 13)]
    оформление = {"S2", "S3", "S4", "S5"}
    осн = next(sc for sc in R.SCENARIOS if sc["id"] == R.MAIN_SCENARIO)
    assert "КС-2/КС-3" in осн["signs"] and "срок оплаты истёк" in осн["signs"], "основная ситуация описана не так, как утверждено"
    assert осн["path"] == прямой, f"основная ситуация идёт не S6–S12: {осн['path']}"
    # не сверены взаиморасчёты — тоже с S6 и реестра взаиморасчётов, без S2–S5
    несверено = next(sc for sc in R.SCENARIOS if "не сверены" in sc["title"])
    assert несверено["path"] == прямой, f"ситуация «{несверено['title']}» уходит в оформление актов"
    assert any("реестр взаиморасчётов" in f for f in _шаг("S6")["forks"]), "S6 не ведёт несверенный долг через реестр взаиморасчётов"
    # S2–S5 — только там, где документы не оформлены, не переданы или есть замечания
    for sc in R.SCENARIOS:
        if оформление & set(sc["path"]):
            assert re.search(r"не оформлены|не переданы|замечани|не подписывает", sc["title"]), (
                f"ситуация «{sc['title']}» без причины проходит шаги 2–5")
    алгоритм = docx_text(C / "03-algoritm-dejstviy.docx")
    assert "Основной путь при просроченной оплате — шаги 6–12" in алгоритм


def test_детальные_вопросы_не_обязательный_вход() -> None:
    s0, s1 = _шаг("S0"), _шаг("S1")
    assert "02-pervichnaya-proverka-i-kontrol.xlsx" not in s0["tools"], "выбор ситуации требует опросник файла 02"
    assert s1.get("optional") and s1["id"] not in R.scenario_steps(), "детальная проверка стоит на обязательном пути"
    старт = START_HERE()
    первая_ситуация = старт.find(f"{R.SCENARIOS[0]['id']}. {R.SCENARIOS[0]['title']}")
    assert 0 <= первая_ситуация < старт.find("02-pervichnaya"), "первый экран начинается не с выбора ситуации"
    assert "Отвечать на вопросы файла 02 не нужно" in старт
    assert "ответьте\n   на все вопросы" not in старт, "первый экран требует ответить на все вопросы"
    маршрут = xlsx_text(C / "02-pervichnaya-proverka-i-kontrol.xlsx")
    assert "Детальная проверка — по желанию" in маршрут and "Необязательно" in маршрут
    карта = docx_text(C / "01-karta-situacii-i-granic.docx")
    assert "Для выбора ситуации она не обязательна" in карта


def test_стороны_только_субподрядчик_и_заказчик() -> None:
    роль = re.compile(r"(?<![А-Яа-яЁё])(подрядчик|генподрядчик)", re.I)
    плохие = []
    for f in delivered():
        for m in set(роль.findall(buyer_text(f))):
            плохие.append(f"{f.name}: «{m}»")
    assert not плохие, "в покупательском тексте осталась роль «Подрядчик»:\n  " + "\n  ".join(плохие)
    for name in ("05-akt-vypolnennyh-rabot.docx", "11-peregovory-i-perenos-sroka.docx", "13-pretenziya.docx"):
        t = docx_text(C / name)
        assert "Субподрядчик" in t and "Заказчик" in t, f"{name}: стороны не названы"
    кс = xlsx_text(C / "04-ks-2-ks-3.xlsx")
    assert "Субподрядчик" in кс and "Заказчик" in кс


def test_устная_договорённость_фиксируется_документом() -> None:
    утв = ("Итог устной договорённости фиксируют документом с основанием, суммой, "
           "сроком оплаты и полномочиями подписанта.")
    assert утв in docx_text(C / "11-peregovory-i-perenos-sroka.docx"), "нет утверждённой формулировки"
    for f in delivered():
        assert "Устная договорённость в споре не существует" not in buyer_text(f), f"{f.name}: старая фраза"


def test_нет_файлов_ради_счётчика() -> None:
    используемые = {t for s in R.STEPS for t in s["tools"]}
    лишние = set(R.FILES) - используемые - {"00-START-HERE.txt"}
    assert not лишние, f"файлы без функции в маршруте: {sorted(лишние)}"


def test_каждая_граница_распознаётся_и_имеет_следующий_шаг() -> None:
    обязательные = {
        "B1": ["исполнительн"], "B2": ["удержан", "зачёт", "неустойк", "недостат", "встречн"],
        "B3": ["банкрот"], "B4": ["мотивированн", "односторонн", "экспертиз", "подпис"],
    }
    распознаются = {b for s in R.STEPS for b in s["boundaries"]}
    карта = docx_text(C / "01-karta-situacii-i-granic.docx").lower()
    маршрут = xlsx_text(C / "02-pervichnaya-proverka-i-kontrol.xlsx")
    for b, слова in обязательные.items():
        assert b in распознаются, f"граница {b} не распознаётся ни на одном шаге"
        assert R.BOUNDARIES[b]["buyer_next"], f"{b}: нет следующего шага"
        текст = (R.BOUNDARIES[b]["name"] + R.BOUNDARIES[b]["signs"]).lower()
        for w in слова:
            assert w in текст, f"{b}: признак «{w}» не назван"
        assert R.BOUNDARIES[b]["name"].lower() in карта, f"{b}: нет в карте границ (файл 01)"
        assert f'"{b}"' in маршрут, f"{b}: маршрутизатор файла 02 не выдаёт эту границу"


def test_нет_обязательной_допокупки() -> None:
    плохие = []
    for f in delivered():
        текст = buyer_text(f)
        for слово in R.CROSS_SELL:
            if re.fullmatch(r"[A-Za-z]\d+|sku", слово):
                pattern = rf"(?<![A-Za-zА-Яа-я0-9]){re.escape(слово)}(?![0-9A-Za-z])"
                if re.search(pattern, текст):
                    плохие.append(f"{f.name}: «{слово}»")
            elif слово.lower() in текст.lower():
                плохие.append(f"{f.name}: «{слово}»")
    assert not плохие, "в тексте покупателя ссылка на покупку:\n  " + "\n  ".join(плохие)


def test_система_не_обещает_решить_граничные_ситуации() -> None:
    # Отрицание («не гарантирует оплату») — это как раз оговорка, а не обещание
    обещание = re.compile(r"(?<!не )(гарантирует (взыскание|оплату|результат)|решит спор|гарантированн|100\s?%)")
    for f in delivered():
        m = обещание.search(buyer_text(f).lower())
        assert not m, f"{f.name}: обещание «{m.group(0)}»"
    for f in delivered():
        if f.suffix == ".docx":
            assert "не юридическая консультация" in docx_text(f), (
                f"{f.name}: нет блока «Важно»")


def test_формы_содержат_рабочую_табличную_часть() -> None:
    for name, (_, нужна) in R.FILES.items():
        if not нужна:
            continue
        f = C / name
        if f.suffix == ".docx":
            xml = docx_xml(f)
            таблицы = re.findall(r"<w:tbl>.*?</w:tbl>", xml, re.S)
            assert таблицы, f"{name}: нет ни одной таблицы"
            строк = max(len(re.findall(r"<w:tr[ >]", t)) for t in таблицы)
            assert строк >= 4, f"{name}: самая большая таблица — {строк} строк, это перечень, а не форма"
        elif f.suffix == ".xlsx":
            with zipfile.ZipFile(f) as z:
                n = sum(len(re.findall(r"<f>", z.read(x).decode()))
                        for x in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", x))
            assert n >= 20, f"{name}: {n} формул — книга не рабочая"


def test_кс2_кс3_связаны_и_считают() -> None:
    book = C / "04-ks-2-ks-3.xlsx"
    ks2 = formulas(book, "КС-2")
    assert sum("ROUND(F" in f and "*G" in f for f in ks2) == 50, "в КС-2 не 50 строк со стоимостью = количество × цена"
    assert any(f.startswith("SUM(H21:H70)") for f in ks2), "нет итога КС-2"
    assert any("/100" in f and "H72" in f for f in ks2), "НДС должен вводиться в процентах и делиться на 100"
    ks3 = formulas(book, "КС-3")
    assert any("'КС-2'!H71" in f for f in ks3), "КС-3 не берёт сумму за период из КС-2"
    sv = " ".join(formulas(book, "Сверка"))
    assert "'КС-3'!F21-'КС-2'!H71" in sv, "нет сверки КС-3 с КС-2"


def test_реестры_на_месте() -> None:
    book = C / "08-uchet-obemov-peredachi-raschetov.xlsx"
    with zipfile.ZipFile(book) as z:
        wbx = z.read("xl/workbook.xml").decode("utf-8")
    for лист in ("Журнал объёмов", "Реестр замечаний", "Реестр передачи", "Взаиморасчёты", "Реестр приложений"):
        assert f'name="{лист}"' in wbx, f"нет листа «{лист}»"
    вз = " ".join(formulas(book, "Взаиморасчёты"))
    assert "ГРАНИЦА B2" in вз, "взаиморасчёты не распознают удержание/зачёт/неустойку"
    assert "COUNTA(A505" in вз, "записи ниже таблицы взаиморасчётов не блокируют итог"
    пер = " ".join(formulas(book, "Реестр передачи"))
    assert "НЕТ ДОКАЗАТЕЛЬСТВА" in пер, "реестр передачи не требует доказательства"


def test_гарантийное_письмо_не_заменяет_соглашение() -> None:
    t = docx_text(C / "11-peregovory-i-perenos-sroka.docx")
    assert "ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ" in t, "нет двустороннего соглашения"
    assert "Гарантийное письмо не заменяет соглашение" in t, "не сказано, что гарантийное письмо не заменяет соглашение"
    assert "Обе стороны" in t and "Только заказчик" in t


def test_расчёт_395_устроен_без_молчаливых_потерь() -> None:
    book = C / "14-raschet-procentov-395.xlsx"
    дни = formulas(book, "По дням")
    дневные = [f for f in дни if "/100/" in f]
    assert len(дневные) == 3661, f"ожидалось 3661 подневных формул, найдено {len(дневные)}"
    assert all(f.count("/100") == 1 for f in дневные), "ставка должна делиться на 100 ровно один раз"
    assert any('SUMIF(Оплаты!$A$6:$A$505,"<"&A' in f for f in дни), "долг на день должен учитывать все 500 строк оплат"
    ввод = " ".join(formulas(book, "Ввод"))
    assert "похоже на долю" in ввод, "нет блокировки ставки, введённой долей"
    пров = " ".join(formulas(book, "Проверки"))
    assert "COUNTA(Оплаты!A506" in пров, "оплаты ниже таблицы не блокируют итог"
    расч = " ".join(formulas(book, "Расчёт"))
    assert 'IF(D2="ГОТОВ"' in расч, "итог не зависит от статуса проверок"


def test_нет_кириллических_функций() -> None:
    плохие = [f"{b.name}: {x}" for b in C.glob("*.xlsx") for x in TDA.кириллические_функции(b)]
    assert not плохие, "\n  ".join(плохие)


def test_кандидат_не_подключён_к_выдаче() -> None:
    config = (R.ROOT / "products-config.php").read_text(encoding="utf-8")
    assert C.name not in config, "кандидат адресован в products-config.php"
    assert "s1" not in re.findall(r"'([a-z0-9]+)'\s*=>\s*\[\s*'name'", config), "появился sku s1"
    assert not (R.ROOT / "products-storage" / C.name).exists(), "кандидат лежит в products-storage"
    deploy = (R.ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert re.search(r"EXCLUDES=\([^)]*'tools'", deploy, re.S), "каталог tools больше не исключён из деплоя"


# ───────────────────── 2. эталон расчёта процентов ─────────────────────

def подневно(principal, start, end, rates, payments, excluded=()):
    """Независимый подсчёт без группировки: сумма по дням, округление в конце
    каждого отрезка с неизменными параметрами не делается — поэтому
    сравнение с эталоном идёт с допуском в копейку на период."""
    total = Decimal(0)
    d = start
    while d <= end:
        debt = Decimal(principal) - sum(Decimal(a) for pd, a in payments if pd < d)
        rate = Decimal(str([r for rd, r in sorted(rates) if rd <= d][-1]))
        if not any(a <= d <= b for a, b in excluded):
            total += debt * rate / 100 / SI.year_days(d)
        d += timedelta(days=1)
    return total


def test_эталон_частичная_оплата_внутри_периода() -> None:
    total, periods = SI.calculate(1_000_000, date(2025, 1, 10), date(2025, 3, 31),
                                  [(date(2024, 10, 28), 21)], [(date(2025, 2, 14), 300_000)])
    assert len(periods) == 2 and periods[0].end == date(2025, 2, 14), "оплата не разделила период"
    assert periods[1].debt == 700_000
    # 1 000 000 × 21 % × 36 / 365 + 700 000 × 21 % × 45 / 365
    assert total == Decimal("20712.33") + Decimal("18123.29") == Decimal("38835.62")
    без_учёта = SI.calculate(1_000_000, date(2025, 1, 10), date(2025, 3, 31), [(date(2024, 10, 28), 21)])[0]
    assert без_учёта > total, "частичная оплата должна уменьшать проценты"


def сценарий_12_оплат():
    pays = [(date(2023, 12, 20) + timedelta(days=15 * i), 10_000 + 1_000 * i) for i in range(12)]
    rates = [(date(2023, 10, 30), 15), (date(2023, 12, 18), 16), (date(2024, 7, 29), 18)]
    return dict(principal=500_000, start=date(2023, 12, 1), end=date(2024, 8, 31), rates=rates, payments=pays)


def test_эталон_больше_десяти_оплат() -> None:
    s = сценарий_12_оплат()
    total, periods = SI.calculate(**s)
    assert abs(total - подневно(**s)) <= Decimal("0.01") * len(periods)
    без_последних = SI.calculate(**{**s, "payments": s["payments"][:10]})[0]
    assert total < без_последних, "11-я и 12-я оплаты не повлияли на расчёт"
    assert {p.year_days for p in periods} == {365, 366}, "сценарий должен пересекать високосный год"


# ─────────────────────── 3. прогон в LibreOffice ───────────────────────

def _lo_ready() -> str | None:
    soffice = shutil.which("soffice")
    if not soffice:
        return "soffice не найден"
    # Пакет libreoffice-core ставит soffice без Calc: тогда книгу он не
    # открывает («source file could not be loaded»), и это не провал кандидата,
    # а неполная среда. Системные пакеты тест не ставит.
    программа = Path(soffice).resolve().parent
    if not (программа / "libsclo.so").exists():
        return f"LibreOffice без модуля Calc ({программа}), установлен только core"
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return "нет openpyxl для заполнения временных копий"
    return None


def пересчитать(книги: dict[str, Path], tmp: Path) -> dict[str, Path]:
    out = tmp / "out"
    cmd = ["soffice", f"-env:UserInstallation=file://{tmp}/profile", "--headless", "--norestore",
           "--calc", "--convert-to", "xlsx", "--outdir", str(out), *map(str, книги.values())]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    результат = {k: out / v.name for k, v in книги.items()}
    нет = [k for k, p in результат.items() if not p.exists()]
    assert not нет, f"LibreOffice не пересчитал {нет}: {r.stdout[-500:]} {r.stderr[-500:]}"
    return результат


def заполнить_395(src: Path, dst: Path, principal, start, end, rates, payments=(), excluded=(), extra=None):
    import openpyxl
    wb = openpyxl.load_workbook(src)
    v, o = wb["Ввод"], wb["Оплаты"]
    v["B4"], v["B5"], v["B6"] = principal, start, end
    for i, (d, r) in enumerate(rates):
        v[f"A{12 + i}"], v[f"B{12 + i}"] = d, r
    for i, (a, b) in enumerate(excluded):
        v[f"F{12 + i}"], v[f"G{12 + i}"] = a, b
    for i, (d, a) in enumerate(payments):
        o[f"A{6 + i}"], o[f"B{6 + i}"] = d, a
    if extra:
        extra(wb)
    wb.save(dst)
    return dst


def test_libreoffice_прогон() -> None:
    причина = _lo_ready()
    if причина:
        ПРОПУСКИ.append(f"прогон LibreOffice: {причина}")
        return
    import openpyxl
    tmp = Path(tempfile.mkdtemp(prefix="s1-lo-"))
    try:
        b395 = C / "14-raschet-procentov-395.xlsx"
        s12 = сценарий_12_оплат()
        ex = [(date(2024, 3, 1), date(2024, 3, 31))]
        книги = {
            "частичная": заполнить_395(b395, tmp / "p1.xlsx", 1_000_000, date(2025, 1, 10), date(2025, 3, 31),
                                       [(date(2024, 10, 28), 21)], [(date(2025, 2, 14), 300_000)]),
            "12оплат": заполнить_395(b395, tmp / "p2.xlsx", **s12),
            "исключение": заполнить_395(b395, tmp / "p3.xlsx", **{**s12, "excluded": ex}),
            "доля": заполнить_395(b395, tmp / "p4.xlsx", 1_000_000, date(2025, 1, 10), date(2025, 3, 31),
                                  [(date(2024, 10, 28), 0.21)]),
            "ниже_таблицы": заполнить_395(b395, tmp / "p5.xlsx", 1_000_000, date(2025, 1, 10), date(2025, 3, 31),
                                          [(date(2024, 10, 28), 21)], [(date(2025, 2, 14), 300_000)],
                                          extra=lambda wb: wb["Оплаты"].__setitem__("A506", date(2025, 3, 1)) or
                                          wb["Оплаты"].__setitem__("B506", 1_000)),
            "до_начала": заполнить_395(b395, tmp / "p6.xlsx", 1_000_000, date(2025, 1, 10), date(2025, 3, 31),
                                       [(date(2024, 10, 28), 21)], [(date(2025, 1, 5), 300_000)]),
        }
        # КС-2 / КС-3
        wb = openpyxl.load_workbook(C / "04-ks-2-ks-3.xlsx")
        k = wb["КС-2"]
        for c, v in {"D12": "7", "D13": date(2025, 5, 31), "D14": date(2025, 5, 1), "D15": date(2025, 5, 31), "D16": 10_000_000}.items():
            k[c] = v
        for i, (n, q, p) in enumerate([("Бетонирование", 120.5, 5_400), ("Армирование", 18.2, 92_000), ("Опалубка", 340, 780.25)]):
            k[f"C{21 + i}"], k[f"F{21 + i}"], k[f"G{21 + i}"] = n, q, p
        k["H72"] = 20
        wb["КС-3"]["D19"], wb["КС-3"]["E19"] = 2_000_000, 1_000_000
        wb.save(tmp / "ks.xlsx")
        k["H72"] = 0.2
        wb.save(tmp / "ks_dolya.xlsx")
        книги["кс"], книги["кс_доля"] = tmp / "ks.xlsx", tmp / "ks_dolya.xlsx"
        # маршрутизатор
        хорошие = {"q1": "Да", "q2": "Да", "q3": "Нет", "q4": "Нет", "q5": "Нет", "q6": "Нет", "q7": "Нет",
                   "q8": "Нет", "q9": "Нет", "q10": "Нет", "q11": "Да", "q12": "Да", "q13": "Нет",
                   "q14": "Нет", "q15": "Да", "q16": "Да"}
        варианты = {"ок": {}, "b2": {"q8": "Да"}, "b3": {"q8": "Да", "q9": "Да"}, "b4": {"q4": "Да"},
                    "рано": {"q12": "Нет"}, "гарантийное": {"q14": "Да"}}
        for имя, правка in варианты.items():
            wb = openpyxl.load_workbook(C / "02-pervichnaya-proverka-i-kontrol.xlsx")
            ws = wb["Маршрут"]
            for i, q in enumerate(хорошие):
                ws[f"C{5 + i}"] = {**хорошие, **правка}[q]
            wb["Контроль ответа"]["F5"] = "Встречное требование, зачёт, удержание, неустойка"
            wb.save(tmp / f"r_{имя}.xlsx")
            книги[f"r_{имя}"] = tmp / f"r_{имя}.xlsx"
        # взаиморасчёты: 12 оплат + удержание
        wb = openpyxl.load_workbook(C / "08-uchet-obemov-peredachi-raschetov.xlsx")
        vz = wb["Взаиморасчёты"]
        строки = [("Начисление по акту", 1_000_000), ("Зачёт аванса по договору", 100_000)]
        строки += [("Оплата", 10_000 + i) for i in range(12)] + [("Удержание", 50_000)]
        for i, (t, s) in enumerate(строки):
            vz[f"B{5 + i}"], vz[f"C{5 + i}"], vz[f"E{5 + i}"] = date(2025, 1, 1) + timedelta(days=i), t, s
        wb.save(tmp / "vz.xlsx")
        книги["вз"] = tmp / "vz.xlsx"

        r = пересчитать(книги, tmp)
        get = lambda k, sh, c: openpyxl.load_workbook(r[k], data_only=True)[sh][c].value  # noqa: E731

        def итог(k):
            wb = openpyxl.load_workbook(r[k], data_only=True)
            return wb["Расчёт"]["D2"].value, wb["Расчёт"]["D3"].value, wb["Расчёт"]

        st, val, _ = итог("частичная")
        assert st == "ГОТОВ" and Decimal(str(val)) == Decimal("38835.62"), f"частичная оплата: {st} {val}"
        st, val, ws = итог("12оплат")
        эталон, периоды = SI.calculate(**s12)
        assert st == "ГОТОВ" and Decimal(str(val)).quantize(Decimal("0.01")) == эталон, f"12 оплат: {val} ≠ {эталон}"
        оплаты_в_таблице = sum(float(ws[f"I{i}"].value or 0) for i in range(7, 7 + len(периоды)))
        assert round(оплаты_в_таблице, 2) == sum(a for _, a in s12["payments"]), "не все 12 оплат попали в периоды"
        st, val, _ = итог("исключение")
        эталон_ex = SI.calculate(**s12, excluded=ex)[0]
        assert st == "ГОТОВ" and Decimal(str(val)).quantize(Decimal("0.01")) == эталон_ex, f"исключение: {val} ≠ {эталон_ex}"
        for k in ("доля", "ниже_таблицы", "до_начала"):
            st, val, _ = итог(k)
            assert st == "ЗАБЛОКИРОВАН" and isinstance(val, str), f"{k}: ожидалась блокировка, получено {st} {val}"

        сумма = round(120.5 * 5400, 2) + round(18.2 * 92000, 2) + round(340 * 780.25, 2)
        assert abs(get("кс", "КС-2", "H71") - сумма) < 0.005
        assert abs(get("кс", "КС-2", "H73") - round(сумма * 0.2, 2)) < 0.005, "НДС 20 должен давать 20 %"
        assert abs(get("кс", "КС-3", "F21") - сумма) < 0.005 and abs(get("кс", "КС-3", "D21") - (2_000_000 + сумма)) < 0.005
        assert get("кс", "Сверка", "C12").startswith("ВСЁ СХОДИТСЯ"), get("кс", "Сверка", "C12")
        assert get("кс_доля", "Сверка", "C6").startswith("РАСХОЖДЕНИЕ"), "ставка НДС долей не распознана"

        n = 4 + 16 + 3  # строка «ИТОГ»: шапка, 16 вопросов, пропуск, служебный код
        ожидания = {"ок": "МОЖНО ИДТИ ПО S1", "b2": "ГРАНИЦА B2", "b3": "ГРАНИЦА B3", "b4": "ГРАНИЦА B4", "рано": "РАНО"}
        for имя, начало in ожидания.items():
            v = get(f"r_{имя}", "Маршрут", f"C{n}")
            assert str(v).startswith(начало), f"маршрут «{имя}»: {v}"
        assert "не переносит срок" in str(get("r_гарантийное", "Маршрут", f"C{n + 2}")), "нет предупреждения о гарантийном письме"
        assert str(get("r_ок", "Контроль ответа", "G5")).startswith("Граница B2"), "контроль ответа не ведёт к границе B2"

        wb = openpyxl.load_workbook(r["вз"], data_only=True)["Взаиморасчёты"]
        долг = 1_000_000 - 100_000 - sum(10_000 + i for i in range(12))
        assert abs(wb["K10"].value - долг) < 0.005, f"бесспорный долг {wb['K10'].value} ≠ {долг}"
        assert str(wb["K11"].value).startswith("ГРАНИЦА B2"), wb["K11"].value
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_сборка_воспроизводима() -> None:
    try:
        import build_s1_candidate as B
    except SystemExit as e:
        ПРОПУСКИ.append(f"воспроизводимость: {e}")
        return
    tmp = Path(tempfile.mkdtemp(prefix="s1-build-"))
    try:
        B.build(tmp / "c")
        разные = [p.name for p in sorted(C.iterdir())
                  if p.read_bytes() != (tmp / "c" / p.name).read_bytes()]
        assert not разные, f"закоммиченный кандидат отличается от вывода генератора: {разные}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
    for п in ПРОПУСКИ:
        print(f"ПРОПУСК  {п}")
    return 1 if провал else 0


if __name__ == "__main__":
    sys.exit(main())
