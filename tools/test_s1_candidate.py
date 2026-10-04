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
    assert not (C / "ROUTE-MAP.json").exists(), "ROUTE-MAP.json лежит в папке выдачи"


def test_карта_маршрута_не_отстала_от_источника() -> None:
    assert R.ROUTE_MAP.parent != C and C not in R.ROUTE_MAP.parents, "карта маршрута внутри папки выдачи"
    на_диске = json.loads(R.ROUTE_MAP.read_text(encoding="utf-8"))
    assert на_диске == json.loads(json.dumps(R.route_map(), ensure_ascii=False)), (
        f"{R.ROUTE_MAP.name} расходится с s1_route.py — пересоберите кандидат")


def test_каждый_шаг_имеет_инструмент_подтверждение_и_следующий_шаг() -> None:
    ids = [s["id"] for s in R.STEPS]
    # S1-02А: шагов сдачи работ (2–5) нет; номера 6–12 сохранены — на них ссылаются тексты
    assert ids == ["S0", "S1"] + [f"S{i}" for i in range(6, 13)], f"шаги маршрута: {ids}"
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
    # W-1: шаг 7 проходим, если заказчик на переговоры не вышел
    s7 = _шаг("S7")
    assert "переговоров не было" in s7["confirmation"] and "«Контроль ответа»" in s7["confirmation"], (
        "шаг 7 не допускает «переговоров не было»")
    assert "Не вышел на переговоры" in реакции_02(), "в «Контроле ответа» нельзя отметить, что переговоров не было"


def _шаг(sid: str) -> dict:
    return next(s for s in R.STEPS if s["id"] == sid)


def test_каждый_сценарий_имеет_однозначный_старт_и_следующий_шаг() -> None:
    ids = [sc["id"] for sc in R.SCENARIOS]
    assert ids == ["А", "Б", "В"], f"ситуации системы — А, Б, В: {ids}"
    for sc in R.SCENARIOS:
        путь = sc["path"]
        assert sc["start"] == путь[0], f"{sc['id']}: стартовый шаг не совпадает с началом пути"
        assert len(путь) == len(set(путь)), f"{sc['id']}: шаг повторяется в пути"
        for a, b in zip(путь, путь[1:]):
            assert _шаг(a)["next"] == b, (
                f"{sc['id']}: после {a} в пути {b}, а в шаге {a} следующим назван {_шаг(a)['next']}")
        assert _шаг(путь[-1])["next"] == "END", f"{sc['id']}: путь должен заканчиваться завершением маршрута"
    # то же в файлах покупателя: стартовый шаг и путь в карте ситуаций и в
    # алгоритме; выход «работы не приняты» — последней строкой обеих таблиц
    карта = docx_text(C / "01-karta-situacii-i-granic.docx")
    алгоритм = docx_text(C / "03-algoritm-dejstviy.docx")
    старт = START_HERE()
    for sc in R.SCENARIOS:
        маршрут = "G → " + " → ".join(x[1:] for x in sc["path"])
        старт_ = f"Проверка G, затем шаг {sc['start'][1:]}"
        assert f"{sc['id']}. {sc['title']} {sc['signs']} {старт_} {маршрут}" in карта, (
            f"файл 01: строка ситуации {sc['id']} расходится с картой маршрута")
        assert f"{sc['id']}. {sc['title']} {старт_} {маршрут}" in алгоритм, (
            f"файл 03: путь ситуации {sc['id']} расходится с картой маршрута")
        assert f"Начать: {старт_[0].lower()}{старт_[1:]}. Путь: {маршрут}." in старт, (
            f"00-START-HERE: ситуация {sc['id']} расходится с картой маршрута")
    выход = R.EXIT
    assert f"{выход['title']} {выход['signs']} — Что сделать: {выход['todo']}" in карта, "файл 01: нет строки выхода"
    assert f"{выход['title']} — Что сделать: {выход['todo']}" in алгоритм, "файл 03: нет строки выхода"
    assert выход["title"].upper() in старт and выход["todo"] in " ".join(старт.split()), "START-HERE: нет выхода"
    карта_json = json.loads(R.ROUTE_MAP.read_text(encoding="utf-8"))
    assert карта_json["scenarios"] == json.loads(json.dumps(R.SCENARIOS, ensure_ascii=False))
    assert карта_json["exit"] == json.loads(json.dumps(R.EXIT, ensure_ascii=False))


def START_HERE() -> str:
    return (C / "00-START-HERE.txt").read_text(encoding="utf-8")


def test_основной_сценарий_ведёт_напрямую_s6_s12() -> None:
    прямой = [f"S{i}" for i in range(6, 13)]
    осн = next(sc for sc in R.SCENARIOS if sc["id"] == R.MAIN_SCENARIO)
    assert "КС-2/КС-3" in осн["signs"] and "срок оплаты истёк" in осн["signs"], "основная ситуация описана не так, как утверждено"
    # А, Б, В — принятые работы: все идут шагами 6–12
    for sc in R.SCENARIOS:
        assert sc["path"] == прямой, f"ситуация «{sc['title']}» идёт не S6–S12: {sc['path']}"
    # не сверены взаиморасчёты — с S6 и реестра взаиморасчётов
    assert any("реестр взаиморасчётов" in f for f in _шаг("S6")["forks"]), "S6 не ведёт несверенный долг через реестр взаиморасчётов"
    алгоритм = docx_text(C / "03-algoritm-dejstviy.docx")
    assert "Основной путь при просроченной оплате — шаги 6–12" in алгоритм


def test_задолженность_только_через_проверку_G() -> None:
    """S1-A3 и S1-02А: работы не приняты — задолженность не фиксируется, и
    система называет выход, а не ведёт в сдачу работ или в претензию."""
    assert R.GATE["pass"] == "S6"
    ведут_к_6 = [s["id"] for s in R.STEPS if s["next"] == "S6"]
    assert not ведут_к_6, f"шаг 6 достижим в обход проверки G: {ведут_к_6}"
    assert len(R.GATE["conditions"]) >= 3
    условия = " ".join(R.GATE["conditions"])
    assert "подписан обеими сторонами" in условия and "срок истёк" in условия and "замечаний" in условия
    for sc in R.SCENARIOS:
        assert "приняты" in sc["signs"] and "срок оплаты истёк" in sc["signs"], (
            f"{sc['id']}: ситуация задолженности без принятых работ и истёкшего срока")
    # строки «не выполнено» и выход не ведут в долг: ни шагов 6–12, ни файлов долга
    долговые = re.compile(r"[Шш]аг(?:и)? (?:6|7|8|9|1[0-2])\b|файл(?:ы|е|а)? (?:0[4-6]|0[89]|10)\b|претензи[юя] (?:направ|подгот)")
    for когда, дальше in R.GATE["fail"] + [(R.EXIT["title"], R.EXIT["todo"])]:
        m = долговые.search(дальше)
        assert not m, f"проверка G, «{когда}»: следующий шаг ведёт в долг («{m.group(0)}»)"
    assert "Долг не фиксируйте" in R.EXIT["todo"] and "претензию не готовьте" in R.EXIT["todo"]
    assert "запрос подписать акт или прислать мотивированный отказ" in R.EXIT["todo"], "выход не называет, что делать при молчании"
    assert R.GATE["fail"][0][1] == R.EXIT["todo"], "строка проверки G «работы не приняты» расходится с выходом"
    # то же в файлах покупателя 00, 01, 03 и 02
    старт, карта, алгоритм = START_HERE(), docx_text(C / "01-karta-situacii-i-granic.docx"), docx_text(C / "03-algoritm-dejstviy.docx")
    for имя, текст in (("00", старт), ("01", карта), ("03", алгоритм)):
        assert R.GATE["title"].lower() in текст.lower(), f"файл {имя}: нет проверки G"
        for когда, дальше in R.GATE["fail"]:
            assert дальше in " ".join(текст.split()), f"файл {имя}: нет строки проверки G «{когда}»"
    assert "Работы выполнены и приняты, задолженность" not in старт, "START HERE описывает только ситуацию долга"
    маршрут02 = xlsx_text(ПРОВЕРКА_02)
    assert "затем шаг 6" not in маршрут02, "файл 02 ведёт в шаг 6 в обход проверки G"
    assert '"НЕ ПРИНЯТЫ"' in маршрут02 and "РАБОТЫ НЕ ПРИНЯТЫ" in маршрут02, "файл 02 не называет выход «работы не приняты»"
    for код in ("ДОКУМЕНТЫ", "ПЕРЕДАЧА", "ЗАМЕЧАНИЯ", "ПОДПИСЬ"):
        assert f'"{код}"' not in маршрут02, f"файл 02 ведёт в сдачу работ кодом {код}"


def test_start_here_использует_утверждённую_формулировку_об_оплате() -> None:
    старт = START_HERE()
    assert "Работы выполнены, но оплата не поступила." in старт
    assert "Работы выполнены, а оплата не получена." not in старт


def test_start_here_не_обещает_всё_внутри() -> None:
    старт = START_HERE()
    for фраза in ("ВСЁ НЕОБХОДИМОЕ ВНУТРИ", "Других материалов", "не требуется"):
        assert фраза.lower() not in старт.lower(), f"START HERE обещает полноту: «{фраза}»"
    текст = " ".join(старт.split())
    assert "Все рабочие инструменты маршрута включены" in текст
    for документ in ("договор", "акты", "платёжные документы", "переписку"):
        assert документ in текст, f"START HERE не называет «{документ}» среди того, что собирает покупатель"
    assert "Исходные документы по своему объекту собираете вы" in текст


def _служебные_из_выдачи() -> set[str]:
    """Имена, которые mvb_build_product_zip не кладёт в архив, — из самой
    выдачи, а не из копии списка: изменится выдача — изменится проверка."""
    php = (R.ROOT / "products-config.php").read_text(encoding="utf-8")
    fn = php[php.index("function mvb_build_product_zip"):]
    список = re.search(r"\$service\s*=\s*\[([^\]]*)\]", fn).group(1)
    return set(re.findall(r"'([^']+)'", список))


def _архив_покупателя(папка: Path) -> list[str]:
    служебные = _служебные_из_выдачи()
    return sorted(p.relative_to(папка).as_posix() for p in папка.rglob("*")
                  if p.is_file() and p.name not in служебные)


def test_детальные_вопросы_не_обязательный_вход() -> None:
    s0, s1 = _шаг("S0"), _шаг("S1")
    assert "02-proverka-i-kontrol-otveta.xlsx" not in s0["tools"], "выбор ситуации требует опросник файла 02"
    assert s1.get("optional") and s1["id"] not in R.scenario_steps(), "детальная проверка стоит на обязательном пути"
    старт = START_HERE()
    первая_ситуация = старт.find(f"{R.SCENARIOS[0]['id']}. {R.SCENARIOS[0]['title']}")
    assert 0 <= первая_ситуация < старт.find("02-proverka-i-kontrol-otveta"), "первый экран начинается не с выбора ситуации"
    assert "Отвечать на вопросы файла 02 не нужно" in старт
    assert "ответьте\n   на все вопросы" not in старт, "первый экран требует ответить на все вопросы"
    маршрут = xlsx_text(C / "02-proverka-i-kontrol-otveta.xlsx")
    assert "Детальная проверка — по желанию" in маршрут and "Необязательно" in маршрут
    карта = docx_text(C / "01-karta-situacii-i-granic.docx")
    assert "Для выбора ситуации она не обязательна" in карта


def test_стороны_только_субподрядчик_и_заказчик() -> None:
    # Класс ошибки, а не отдельные слова: любая сторона, кроме субподрядчика и
    # заказчика. «Субподрядчик» не ловится — перед «подрядчик» стоит буква.
    роль = re.compile(r"(?<![А-Яа-яЁё])(подрядчик|генподрядчик|инвестор|иные участники)", re.I)
    плохие = []
    for f in delivered():
        for m in set(роль.findall(buyer_text(f))):
            плохие.append(f"{f.name}: «{m}»")
    assert not плохие, "в покупательском тексте третья сторона или роль «Подрядчик»:\n  " + "\n  ".join(плохие)
    for name in ("05-peregovory-i-perenos-sroka.docx", "06-uvedomlenie-o-prosrochke.docx", "09-pretenziya.docx",
                 "10-obrashchenie-v-sud.docx"):
        t = docx_text(C / name)
        assert "Субподрядчик" in t and "Заказчик" in t, f"{name}: стороны не названы"


def test_устная_договорённость_фиксируется_документом() -> None:
    утв = ("Итог устной договорённости фиксируют документом с основанием, суммой, "
           "сроком оплаты и полномочиями подписанта.")
    assert утв in docx_text(C / "05-peregovory-i-perenos-sroka.docx"), "нет утверждённой формулировки"
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
        "B5": ["допработ", "соглашени"],
    }
    распознаются = {b for s in R.STEPS for b in s["boundaries"]}
    карта = docx_text(C / "01-karta-situacii-i-granic.docx").lower()
    маршрут = xlsx_text(C / "02-proverka-i-kontrol-otveta.xlsx")
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


def test_реестры_на_месте() -> None:
    book = КНИГА_УЧЁТА
    # S1-02А: листы сдачи работ («Журнал объёмов», «Реестр замечаний») исключены
    assert листы(book) == ["Взаиморасчёты", "Долг по актам", "Реестр передачи", "Реестр приложений"], листы(book)
    вз = " ".join(formulas(book, "Взаиморасчёты"))
    assert "ГРАНИЦА B2" in вз, "взаиморасчёты не распознают удержание/зачёт/неустойку"
    assert "COUNTA(A505" in вз, "записи ниже таблицы взаиморасчётов не блокируют итог"
    пер = " ".join(formulas(book, "Реестр передачи"))
    assert "НЕТ ДОКАЗАТЕЛЬСТВА" in пер, "реестр передачи не требует доказательства"


def test_взаиморасчёты_требуют_отнесения_к_акту_и_ловят_двойной_аванс() -> None:
    """S1-H: платёж без акта и один аванс, введённый дважды, не проходят молча."""
    book = C / "04-uchet-raschetov-i-otpravok.xlsx"
    вз = " ".join(formulas(book, "Взаиморасчёты"))
    assert "не указан акт" in вз, "операция, влияющая на долг, не требует идентификатора акта"
    assert "распределите его документально" in вз.lower() or "Распределите его документально" in вз, (
        "нет требования распределить платёж документально")
    assert "двойной учёт аванса" in вз, "реестр не ловит одну сумму как «Оплату» и как «Зачёт аванса»"
    assert "'Долг по актам'!$B$5:$B$34" in вз, "акт строки не сверяется со листом «Долг по актам»"
    assert 'COUNTIF(I5:I504,"БЛОК*")' in вз, "строки с БЛОК не блокируют итог свода"
    # итог свода заблокирован именно строками с БЛОК, а не только счётчиками
    итог = next(f for f in formulas(book, "Взаиморасчёты") if "ИТОГ ЗАБЛОКИРОВАН" in f)
    assert "M14" in итог, f"итог не зависит от строк с БЛОК: {итог}"
    да = " ".join(formulas(book, "Долг по актам"))
    assert "ДОЛГ НА ПЕРВЫЙ ДЕНЬ ПРОСРОЧКИ" in xlsx_text(book), "лист не называет долг на первый день просрочки"
    for нужно in ('SUMIFS(Взаиморасчёты!$E$5:$E$504,Взаиморасчёты!$C$5:$C$504,"Оплата"',
                  '"<"&E5', '">="&E5'):
        assert нужно in да, f"«Долг по актам» не делит оплаты датой начала просрочки: нет {нужно}"
    assert "идентификатор акта повторяется" in да, "повторяющийся акт не блокируется"
    assert "реестр «Взаиморасчёты» заблокирован" in да and "ISNUMBER(Взаиморасчёты!$M$10)" in да, (
        "«Долг по актам» выдаёт суммы к переносу при заблокированном реестре")


def test_гарантийное_письмо_не_заменяет_соглашение() -> None:
    t = docx_text(C / "05-peregovory-i-perenos-sroka.docx")
    assert "ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ" in t, "нет двустороннего соглашения"
    assert "Гарантийное письмо не заменяет соглашение" in t, "не сказано, что гарантийное письмо не заменяет соглашение"
    assert "Обе стороны" in t and "Только заказчик" in t


def test_расчёт_395_устроен_без_молчаливых_потерь() -> None:
    book = C / "08-raschet-procentov-395.xlsx"
    import build_s1_candidate as B
    дни = formulas(book, "По дням")
    дневные = [f for f in дни if "DATE(YEAR(" in f]
    assert len(дневные) == B.DAYS, f"ожидалось {B.DAYS} подневных строк, найдено {len(дневные)}"
    строки = [f for f in formulas(book, "Интервалы") if "SUMPRODUCT(ROUND(" in f]
    assert len(строки) == B.INTERVALS, f"ожидалось {B.INTERVALS} строк-отрезков, найдено {len(строки)}"
    assert all(f.count("/100") == 1 for f in строки), "ставка должна делиться на 100 ровно один раз"
    инт = " ".join(formulas(book, "Интервалы"))
    assert 'SUMIFS(Оплаты!$B$6:$B$505,Оплаты!$D$6:$D$505,A' in инт and '"<="&Оплаты!$A$' in инт, (
        "долг отрезка должен учитывать все 500 строк оплат своего акта")
    ввод = " ".join(formulas(book, "Ввод"))
    assert "похоже на долю" in ввод, "нет блокировки ставки, введённой долей"
    пров = " ".join(formulas(book, "Проверки"))
    assert "COUNTA(Оплаты!A506" in пров, "оплаты ниже таблицы не блокируют итог"
    assert f"COUNTA(Акты!A{B.ACT_LAST + 1}" in пров, "акты ниже таблицы не блокируют итог"
    расч = " ".join(formulas(book, "Расчёт"))
    assert 'IF(D2="ГОТОВ"' in расч, "итог не зависит от статуса проверок"


ПО_ДНЯМ_МАКС_СТРОК = 4000     # вместе с заголовком; матрица «акт × день» давала 43 933


def строки_листа(book: Path, title: str) -> int:
    xml = sheet_xml(book, title)
    return max((int(n) for n in re.findall(r'<row r="(\d+)"', xml)), default=0)


def test_по_дням_одна_строка_на_день_без_матрицы_актов() -> None:
    """Gate S1-H: лист «По дням» — одна строка на календарный день, не больше
    4 000 строк с заголовком. Ловит возврат матрицы «акт × календарный день»
    (43 933 строки, sheet7.xml 59 МБ)."""
    book = C / "08-raschet-procentov-395.xlsx"
    import build_s1_candidate as B
    строк = строки_листа(book, "По дням")
    assert строк <= ПО_ДНЯМ_МАКС_СТРОК, (
        f"лист «По дням»: {строк} строк > {ПО_ДНЯМ_МАКС_СТРОК} — вернулась матрица «акт × день»?")
    assert B.DAY_ROWS <= ПО_ДНЯМ_МАКС_СТРОК and B.DAY_LAST <= ПО_ДНЯМ_МАКС_СТРОК, "предел генератора выше 4 000 строк"
    дни = formulas(book, "По дням")
    # ни одна формула не привязана к отдельной строке листа «Акты»: долг дня
    # собирается по всему диапазону актов, а не блоком на акт
    одиночные = sorted({m for f in дни for m in re.findall(r"Акты!\$[A-Z]\$\d+(?!:)", f)})
    assert not одиночные, f"«По дням» ссылается на отдельные строки актов (матрица по актам): {одиночные[:5]}"
    строк_инт = строки_листа(book, "Интервалы")
    assert строк_инт <= 1 + B.ACTS + 500, f"лист «Интервалы»: {строк_инт} строк — больше строки на акт и на оплату"
    with zipfile.ZipFile(book) as z:
        размеры = {i.filename: i.file_size for i in z.infolist()}
    крупнейший = max(размеры.values())
    assert крупнейший < 8 * 2**20, f"лист книги 14 распакован {крупнейший / 2**20:.1f} МБ — книга раздута"
    assert book.stat().st_size < 2 * 2**20, f"книга 14 весит {book.stat().st_size / 2**20:.1f} МБ"


def test_расчёт_395_считает_акты_по_отдельности() -> None:
    """S1-H: у каждого акта своя дата начала просрочки и свои оплаты; долг дня —
    сумма наступивших актов; один долг с одной датой нигде не собирается."""
    book = C / "08-raschet-procentov-395.xlsx"
    import build_s1_candidate as B
    with zipfile.ZipFile(book) as z:
        wbx = z.read("xl/workbook.xml").decode("utf-8")
    assert 'name="Акты"' in wbx, "нет листа «Акты»"
    дни = " ".join(formulas(book, "По дням"))
    assert f"MIN(Акты!$E${B.ACT_FIRST}:$E${B.ACT_LAST})" in дни, "сетка дней не начинается с самого раннего акта"
    # строка-отрезок принадлежит одному акту: своя дата начала, свой долг
    инт = " ".join(formulas(book, "Интервалы"))
    for k in range(B.ACTS):
        ar = B.ACT_FIRST + k
        assert f"Акты!$E${ar}" in инт and f"Акты!$D${ar}" in инт, f"акт строки {ar} не считается своим отрезком"
    акты = " ".join(formulas(book, "Акты"))
    assert "идентификатор акта повторяется" in акты, "повторяющийся идентификатор акта не блокируется"
    assert "нет ставки, действовавшей в первый день просрочки по этому акту" in акты, (
        "ставка проверяется не на дату начала просрочки каждого акта")
    опл = " ".join(formulas(book, "Оплаты"))
    assert "не указан акт" in опл and "распределить платёж документально" in опл, (
        "оплата без акта не блокирует расчёт с объяснением")
    assert "Акты!$B$5:$B$16" in опл, "акт оплаты не сверяется с листом «Акты»"
    пров = " ".join(formulas(book, "Проверки"))
    assert "есть оплата, не отнесённая к конкретному акту" in пров, (
        "нераспределённый платёж не останавливает итог"
    )
    расч_ф = formulas(book, "Расчёт")
    расч = " ".join(расч_ф)
    assert f"SUM(Акты!G5:G{B.ACT_LAST})" in расч, "долг на последний день не собирается по акта́м"
    # итог = SUM итогов по актам, итог акта = SUMIF строк расчёта по этому акту
    итог = next(f for f in расч_ф if "РАСЧЁТ НЕ ВЫПОЛНЕН" in f)
    assert f"SUM(P7:P{6 + B.ACTS})" in итог, f"«Проценты итого» не сумма итогов по актам: {итог}"
    последняя = 6 + B.INTERVALS
    for k in range(B.ACTS):
        assert f"SUMIF($L$7:$L${последняя},{k + 1},$I$7:$I${последняя})" in расч, (
            f"итог акта {k + 1} не сумма его строк расчёта")
    пров = " ".join(formulas(book, "Проверки"))
    assert f"SUM(Расчёт!I7:I{последняя})-SUM(Расчёт!P7:P{6 + B.ACTS})" in пров, (
        "нет проверки «итог = сумма строк по актам»")
    for k in range(B.ACTS):
        ar = B.ACT_FIRST + k
        assert f"Акты!$B${ar}" in расч and f"Акты!$E${ar}" in расч, f"свод не показывает акт строки {ar}"


def test_книга_расчёта_не_берёт_текущий_остаток_как_сумму_долга() -> None:
    """S1-H: подсказка ведёт за долгом на первый день просрочки (книга учёта,
    файл 04, лист «Долг по актам»), а не за текущим остатком реестра."""
    book = C / "08-raschet-procentov-395.xlsx"
    текст = xlsx_text(book)
    assert "файл 04, лист «Долг по актам»" in текст, "книга расчёта не ссылается на лист «Долг по актам» файла 04"
    assert "Из реестра взаиморасчётов (файл 04): бесспорный долг без спорных сумм." not in текст, (
        "книга расчёта по-прежнему отправляет за текущим остатком реестра")
    акты = " ".join(formulas(book, "Акты"))
    assert "сверка не сходится" in акты, "нет сверки долга на первый день просрочки с текущим остатком"
    assert "внесён текущий остаток, из которого оплаты уже вычтены" in акты, (
        "сверка не объясняет, что в колонку долга попал текущий остаток")
    # книга учёта прямо предупреждает, что её итог в книгу расчёта переносить нельзя
    вз = xlsx_text(КНИГА_УЧЁТА)
    assert "ТЕКУЩИЙ остаток" in вз and "переносить нельзя" in вз, (
        "книга учёта не предупреждает, что текущий остаток не годится для расчёта процентов")


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


# ── сценарии приёмки S1-H: тестовая ставка 20 %, не реальная ключевая ──

СТАВКА = [(date(2026, 1, 1), 20)]
КОНЕЦ = date(2026, 9, 27)
АКТ_A = ("КС-2 № 1", 700_000, date(2026, 7, 31))
АКТ_B = ("КС-2 № 2", 300_000, date(2026, 8, 11))
ОПЛАТА_A = [(date(2026, 8, 20), 200_000, "КС-2 № 1")]


def test_эталон_сценарий_A_частичная_оплата_после_начала_просрочки() -> None:
    total, periods = SI.calculate(700_000, date(2026, 7, 31), КОНЕЦ, СТАВКА,
                                  [(date(2026, 8, 20), 200_000)])
    assert total == Decimal("18465.75"), f"сценарий A: {total} ≠ 18465.75"
    assert periods[-1].debt == 700_000 - 200_000 == 500_000, "долг на последний день ≠ 500 000"
    # старая ошибка: текущий остаток 500 000 как сумма долга даёт 12 000
    неверно = SI.calculate(500_000, date(2026, 7, 31), КОНЕЦ, СТАВКА,
                           [(date(2026, 8, 20), 200_000)])[0]
    assert неверно == Decimal("12000.00") and неверно != total, (
        "проверка не отличает заниженный результат двойного учёта от верного")


def test_эталон_сценарий_B_несколько_актов_с_разными_датами() -> None:
    акты = [SI.Act(АКТ_A[0], АКТ_A[1], АКТ_A[2], [(date(2026, 8, 20), 200_000)]),
            SI.Act(АКТ_B[0], АКТ_B[1], АКТ_B[2])]
    total, по_актам = SI.calculate_acts(акты, КОНЕЦ, СТАВКА)
    assert total == Decimal("26356.16"), f"сценарий B: {total} ≠ 26356.16"
    assert [r.total for r in по_актам] == [Decimal("18465.75"), Decimal("7890.41")]
    assert sum(r.total for r in по_актам) == total, "итог не равен сумме по акта́м"
    assert [r.debt_at_end for r in по_актам] == [500_000, 300_000]
    # объединение в один долг с одной датой даёт другой (неверный) результат
    слито = SI.calculate(1_000_000, АКТ_A[2], КОНЕЦ, СТАВКА, [(date(2026, 8, 20), 200_000)])[0]
    assert слито != total, "проверка не отличает объединённый долг от расчёта по акта́м"
    # один акт в модели актов совпадает с однократным расчётом
    один = SI.calculate_acts([акты[0]], КОНЕЦ, СТАВКА)
    assert один[0] == SI.calculate(700_000, АКТ_A[2], КОНЕЦ, СТАВКА, [(date(2026, 8, 20), 200_000)])[0]
    # оплата акта B раньше его первого дня просрочки отвергается
    try:
        SI.calculate_acts([акты[0], SI.Act(АКТ_B[0], АКТ_B[1], АКТ_B[2], [(date(2026, 8, 5), 1)])], КОНЕЦ, СТАВКА)
    except ValueError:
        pass
    else:
        raise AssertionError("оплата раньше первого дня просрочки своего акта принята")
    # повторяющийся идентификатор акта не даёт отнести оплату однозначно
    try:
        SI.calculate_acts([SI.Act("КС-2 № 1", 100, АКТ_A[2]), SI.Act("КС-2 № 1", 100, АКТ_B[2])],
                          КОНЕЦ, СТАВКА)
    except ValueError as e:
        assert "повторяется" in str(e)
    else:
        raise AssertionError("повторяющийся идентификатор акта не отвергнут")


# Регрессия округления: два акта, оплата и смена ставки. Сумма по актам
# (каждый акт — свои периоды, своё округление) = 4 553,15; округление
# периодов общего долга дало бы 4 553,14. Итог обязан быть суммой по актам.
СТАВКА_R = [(date(2026, 1, 1), 20), (date(2026, 9, 1), 21)]
АКТЫ_R = [("КС-2 № 11", 100_003, date(2026, 7, 31)), ("КС-2 № 12", 70_007, date(2026, 8, 11))]
ОПЛАТЫ_R = [(date(2026, 8, 20), 30_001, "КС-2 № 11")]
# строки расчёта: (акт, с, по, долг акта, проценты = сумма округлённых периодов ставки)
СТРОКИ_R = [("КС-2 № 11", date(2026, 7, 31), date(2026, 8, 20), 100_003, Decimal("1150.72")),
            ("КС-2 № 11", date(2026, 8, 21), КОНЕЦ, 70_002, Decimal("421.93") + Decimal("1087.43")),
            ("КС-2 № 12", date(2026, 8, 11), КОНЕЦ, 70_007, Decimal("805.56") + Decimal("1087.51"))]


def test_эталон_округление_по_актам_а_не_общего_долга() -> None:
    акты = [SI.Act(a, d, s, [(pd, x) for pd, x, pa in ОПЛАТЫ_R if pa == a]) for a, d, s in АКТЫ_R]
    total, по_актам = SI.calculate_acts(акты, КОНЕЦ, СТАВКА_R)
    assert [r.total for r in по_актам] == [Decimal("2660.08"), Decimal("1893.07")], [r.total for r in по_актам]
    assert total == Decimal("4553.15") == sum(r.total for r in по_актам)
    assert total == sum(x[4] for x in СТРОКИ_R), "строки расчёта не дают итог по актам"
    общий = SI.calculate_combined(акты, КОНЕЦ, СТАВКА_R)[0]
    assert общий == Decimal("4553.14") and общий != total, (
        f"сценарий не различает округление общего долга ({общий}) и сумму по актам ({total})")


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


def заполнить_395(src: Path, dst: Path, acts, end, rates, payments=(), excluded=(),
                  extra=None, остаток=None):
    """Заполняет книгу 14 по её модели ввода.

    acts — [(идентификатор, долг на первый день просрочки, первый день просрочки)];
    payments — [(дата, сумма, идентификатор акта)]; сверочный остаток по акту
    считается как долг минус отнесённые к нему оплаты, `остаток` его подменяет
    (так проверяется блокировка неверного ввода).
    """
    import openpyxl
    wb = openpyxl.load_workbook(src)
    v, ak, o = wb["Ввод"], wb["Акты"], wb["Оплаты"]
    v["B4"] = end
    for i, (d, r) in enumerate(rates):
        v[f"A{12 + i}"], v[f"B{12 + i}"] = d, r
    for i, (a, b) in enumerate(excluded):
        v[f"F{12 + i}"], v[f"G{12 + i}"] = a, b
    for i, (aid, debt, start) in enumerate(acts):
        ak[f"B{5 + i}"], ak[f"D{5 + i}"], ak[f"E{5 + i}"] = aid, debt, start
        ak[f"F{5 + i}"] = (остаток or {}).get(
            aid, debt - sum(s for _, s, ai in payments if ai == aid))
    for i, (d, s, aid) in enumerate(payments):
        o[f"A{6 + i}"], o[f"B{6 + i}"] = d, s
        if aid is not None:
            o[f"D{6 + i}"] = aid
    if extra:
        extra(wb)
    wb.save(dst)
    return dst


ОДИН_АКТ = "КС-2 № 1"


def один_акт(src: Path, dst: Path, principal, start, end, rates, payments=(), **kw):
    """Прежние сценарии кандидата (регрессия D) в модели ввода «один акт»."""
    return заполнить_395(src, dst, [(ОДИН_АКТ, principal, start)], end, rates,
                         [(d, a, ОДИН_АКТ) for d, a in payments], **kw)


def test_libreoffice_прогон() -> None:
    """Регрессия D: прежние сценарии кандидата в новой модели ввода —
    частичная оплата, 12 оплат, исключённый период, ставка долей, ввод ниже
    таблицы, оплата до начала периода, маршрутизатор, реакции «Контроля ответа»,
    реестр. S1-02А: КС-2/КС-3 и случаи сдачи работ ушли вместе с файлами."""
    причина = _lo_ready()
    if причина:
        ПРОПУСКИ.append(f"прогон LibreOffice: {причина}")
        return
    import openpyxl
    tmp = Path(tempfile.mkdtemp(prefix="s1-lo-"))
    try:
        b395 = C / "08-raschet-procentov-395.xlsx"
        s12 = сценарий_12_оплат()
        ex = [(date(2024, 3, 1), date(2024, 3, 31))]
        книги = {
            "частичная": один_акт(b395, tmp / "p1.xlsx", 1_000_000, date(2025, 1, 10), date(2025, 3, 31),
                                  [(date(2024, 10, 28), 21)], [(date(2025, 2, 14), 300_000)]),
            "12оплат": один_акт(b395, tmp / "p2.xlsx", **s12),
            "исключение": один_акт(b395, tmp / "p3.xlsx", **{**s12, "excluded": ex}),
            "доля": один_акт(b395, tmp / "p4.xlsx", 1_000_000, date(2025, 1, 10), date(2025, 3, 31),
                             [(date(2024, 10, 28), 0.21)]),
            "ниже_таблицы": один_акт(b395, tmp / "p5.xlsx", 1_000_000, date(2025, 1, 10), date(2025, 3, 31),
                                     [(date(2024, 10, 28), 21)], [(date(2025, 2, 14), 300_000)],
                                     extra=lambda wb: wb["Оплаты"].__setitem__("A506", date(2025, 3, 1)) or
                                     wb["Оплаты"].__setitem__("B506", 1_000)),
            "до_начала": один_акт(b395, tmp / "p6.xlsx", 1_000_000, date(2025, 1, 10), date(2025, 3, 31),
                                  [(date(2024, 10, 28), 21)], [(date(2025, 1, 5), 300_000)]),
        }
        # маршрутизатор: чистый случай «ок» и по одной правке на каждый исход
        варианты = {"ок": {}, "b2": {"q8": "Да"}, "b3": {"q8": "Да", "q9": "Да"}, "b4": {"q4": "Да"},
                    "b4_после_подписания": {"q6": "Да"}, "b5": {"q17": "Да"},
                    "рано": {"q12": "Нет"}, "гарантийное": {"q14": "Да"},
                    "не_подписан": {"q2": "Нет"}, "замечания": {"q7": "Да"}}
        реакции = list(реакции_02().items())
        for имя, правка in варианты.items():
            книги[f"r_{имя}"] = заполнить_маршрут(ПРОВЕРКА_02, tmp / f"r_{имя}.xlsx", правка)
        # «Контроль ответа»: каждая реакция справочника — своей строкой
        wb = openpyxl.load_workbook(книги["r_ок"])
        for i, (реакция, _) in enumerate(реакции):
            wb["Контроль ответа"][f"F{5 + i}"] = реакция
        wb.save(книги["r_ок"])
        # взаиморасчёты: 12 оплат + удержание, всё отнесено к одному акту
        wb = openpyxl.load_workbook(C / "04-uchet-raschetov-i-otpravok.xlsx")
        vz = wb["Взаиморасчёты"]
        строки = [("Начисление по акту", 1_000_000), ("Зачёт аванса по договору", 100_000)]
        строки += [("Оплата", 10_000 + i) for i in range(12)] + [("Удержание", 50_000)]
        for i, (t, s) in enumerate(строки):
            vz[f"B{5 + i}"] = date(2025, 1, 1) + timedelta(days=i)
            vz[f"C{5 + i}"], vz[f"D{5 + i}"], vz[f"E{5 + i}"] = t, f"док. № {i + 1}", s
            vz[f"F{5 + i}"] = ОДИН_АКТ
        wb["Долг по актам"]["B5"] = ОДИН_АКТ
        wb["Долг по актам"]["D5"] = date(2025, 1, 20)
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
        оплаты_в_таблице = sum(float(ws[f"J{i}"].value or 0) for i in range(7, 7 + len(периоды)))
        assert round(оплаты_в_таблице, 2) == sum(a for _, a in s12["payments"]), "не все 12 оплат попали в периоды"
        st, val, _ = итог("исключение")
        эталон_ex = SI.calculate(**s12, excluded=ex)[0]
        assert st == "ГОТОВ" and Decimal(str(val)).quantize(Decimal("0.01")) == эталон_ex, f"исключение: {val} ≠ {эталон_ex}"
        for k in ("доля", "ниже_таблицы", "до_начала"):
            st, val, _ = итог(k)
            assert st == "ЗАБЛОКИРОВАН" and isinstance(val, str), f"{k}: ожидалась блокировка, получено {st} {val}"

        n = строка_итога()
        ожидания = {"ок": "МОЖНО ИДТИ ПО S1", "b2": "ГРАНИЦА B2", "b3": "ГРАНИЦА B3", "b4": "ГРАНИЦА B4",
                    "b4_после_подписания": "ГРАНИЦА B4", "b5": "ГРАНИЦА B5", "рано": "РАНО"}
        for имя, начало in ожидания.items():
            v = get(f"r_{имя}", "Маршрут", f"C{n}")
            assert str(v).startswith(начало), f"маршрут «{имя}»: {v}"
        assert "не переносит срок" in str(get("r_гарантийное", "Маршрут", f"C{n + 2}")), "нет предупреждения о гарантийном письме"
        # работы не приняты — выход из системы, следующий шаг не в долг
        for имя in ("не_подписан", "замечания"):
            итог_, след = get(f"r_{имя}", "Маршрут", f"C{n}"), str(get(f"r_{имя}", "Маршрут", f"C{n + 1}"))
            assert str(итог_).startswith("РАБОТЫ НЕ ПРИНЯТЫ"), f"маршрут «{имя}»: {итог_}"
            assert not ДОЛГОВЫЕ_ШАГИ.search(след) and "претензи" not in след.replace("претензию не готовьте", ""), (
                f"маршрут «{имя}» ведёт в задолженность: {след}")
        # каждая реакция в Calc показывает свой шаг из справочника
        ко = openpyxl.load_workbook(r["r_ок"], data_only=True)["Контроль ответа"]
        for i, (реакция, шаг) in enumerate(реакции):
            assert ко[f"G{5 + i}"].value == шаг, f"реакция «{реакция}»: в Calc «{ко[f'G{5 + i}'].value}»"
        assert str(ко["G5"].value).startswith("Внесите оплату"), ко["G5"].value

        книга08 = openpyxl.load_workbook(r["вз"], data_only=True)
        wb = книга08["Взаиморасчёты"]
        долг = 1_000_000 - 100_000 - sum(10_000 + i for i in range(12))
        блоки = [wb[f"I{i}"].value for i in range(5, 20) if str(wb[f"I{i}"].value).startswith("БЛОК")]
        assert not блоки, f"корректный реестр заблокирован: {блоки}"
        # S1-02Б (§9.2): 779 934 — общий долг; рядом спорная 50 000 и бесспорная 729 934
        assert abs(wb["M10"].value - долг) < 0.005, f"общий долг {wb['M10'].value} ≠ {долг}"
        assert abs(wb["M11"].value - 50_000) < 0.005, f"спорная часть {wb['M11'].value} ≠ 50 000"
        assert abs(wb["M12"].value - (долг - 50_000)) < 0.005, f"бесспорная часть {wb['M12'].value} ≠ {долг - 50_000}"
        assert str(wb["M13"].value).startswith("ГРАНИЦА B2"), wb["M13"].value
        # тот же реестр даёт долг на первый день просрочки: оплаты до 20.01.2025
        да = книга08["Долг по актам"]
        оплаты_до = sum(10_000 + i for i in range(12) if date(2025, 1, 3) + timedelta(days=i) < date(2025, 1, 21))
        assert abs(да["H5"].value - (1_000_000 - 100_000 - оплаты_до)) < 0.005, (
            f"долг на первый день просрочки {да['H5'].value}")
        assert abs(да["L5"].value - долг) < 0.005, f"текущий общий остаток по акту {да['L5'].value} ≠ {долг}"
        assert abs(да["M5"].value - (долг - 50_000)) < 0.005, f"текущий бесспорный остаток {да['M5'].value}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── сценарии приёмки A–C в LibreOffice (D — прогон выше) ──

def заполнить_08(src: Path, dst: Path, операции, акты):
    import openpyxl
    wb = openpyxl.load_workbook(src)
    vz = wb["Взаиморасчёты"]
    for i, (d, t, doc, s, act) in enumerate(операции):
        vz[f"B{5 + i}"], vz[f"C{5 + i}"], vz[f"D{5 + i}"] = d, t, doc
        vz[f"E{5 + i}"], vz[f"F{5 + i}"] = s, act
    da = wb["Долг по актам"]
    for i, (aid, doc, срок) in enumerate(акты):
        da[f"B{5 + i}"], da[f"C{5 + i}"], da[f"D{5 + i}"] = aid, doc, срок
    wb.save(dst)
    return dst


_ПРИЁМКА: dict | None = None


def сценарии_приёмки():
    """Один прогон LibreOffice на сценарии A–C; результат кешируется."""
    global _ПРИЁМКА
    if _ПРИЁМКА is not None:
        return _ПРИЁМКА or None
    причина = _lo_ready()
    if причина:
        ПРОПУСКИ.append(f"сценарии приёмки A–C: {причина}")
        _ПРИЁМКА = {}
        return None
    import openpyxl
    tmp = Path(tempfile.mkdtemp(prefix="s1-abc-"))
    try:
        b395, b08 = C / "08-raschet-procentov-395.xlsx", C / "04-uchet-raschetov-i-otpravok.xlsx"
        C_ОПЕРАЦИИ = [
            (date(2026, 6, 30), "Начисление по акту", "КС-2 № 1 от 30.06.2026", 1_200_000, АКТ_A[0]),
            (date(2026, 5, 15), "Зачёт аванса по договору", "п/п № 100 от 15.05.2026", 200_000, АКТ_A[0]),
            (date(2026, 7, 10), "Оплата", "п/п № 210 от 10.07.2026", 300_000, АКТ_A[0]),
            (date(2026, 8, 20), "Оплата", "п/п № 415 от 20.08.2026", 200_000, АКТ_A[0]),
        ]
        # тот же аванс введён и «Оплатой»: тот же документ, сумма и дата
        C_ДВОЙНОЙ = C_ОПЕРАЦИИ + [
            (date(2026, 5, 15), "Оплата", "п/п № 100 от 15.05.2026", 200_000, АКТ_A[0])]
        C_АКТЫ = [(АКТ_A[0], "КС-2 № 1 от 30.06.2026", date(2026, 7, 30))]
        книги = {
            "A": заполнить_395(b395, tmp / "a.xlsx", [АКТ_A], КОНЕЦ, СТАВКА, ОПЛАТА_A),
            # старая передача: текущий остаток 500 000 вместе с оплатой 200 000
            "A_остаток": заполнить_395(b395, tmp / "ao.xlsx", [(АКТ_A[0], 500_000, АКТ_A[2])],
                                       КОНЕЦ, СТАВКА, ОПЛАТА_A, остаток={АКТ_A[0]: 500_000}),
            "B": заполнить_395(b395, tmp / "b.xlsx", [АКТ_A, АКТ_B], КОНЕЦ, СТАВКА, ОПЛАТА_A),
            "B_без_акта": заполнить_395(b395, tmp / "bn.xlsx", [АКТ_A, АКТ_B], КОНЕЦ, СТАВКА,
                                        [(date(2026, 8, 20), 200_000, None)]),
            # оплата акта B после начала просрочки по A, но раньше своей
            "B_до_начала_акта": заполнить_395(b395, tmp / "bd.xlsx", [АКТ_A, АКТ_B], КОНЕЦ, СТАВКА,
                                              ОПЛАТА_A + [(date(2026, 8, 5), 50_000, АКТ_B[0])]),
            "R": заполнить_395(b395, tmp / "r.xlsx", АКТЫ_R, КОНЕЦ, СТАВКА_R, ОПЛАТЫ_R),
            # та же книга, но проценты первой строки-отрезка подменены числом
            # на 100 ₽ больше: итог обязан сдвинуться ровно на 100 ₽
            "R_подмена": заполнить_395(b395, tmp / "rp.xlsx", АКТЫ_R, КОНЕЦ, СТАВКА_R, ОПЛАТЫ_R,
                                       extra=lambda wb: wb["Интервалы"].__setitem__("F2", 1250.72)),
            "C": заполнить_08(b08, tmp / "c.xlsx", C_ОПЕРАЦИИ, C_АКТЫ),
            "C_двойной": заполнить_08(b08, tmp / "cd.xlsx", C_ДВОЙНОЙ, C_АКТЫ),
            # S1-02Б: тот же сценарий с удержанием 50 000 — акт сверки
            "C_удержание": заполнить_08(b08, tmp / "cu.xlsx", C_ОПЕРАЦИИ + [
                (date(2026, 8, 25), "Удержание", "письмо исх. № 77 от 25.08.2026", 50_000, АКТ_A[0])], C_АКТЫ),
        }
        r = пересчитать(книги, tmp)
        _ПРИЁМКА = {k: openpyxl.load_workbook(p, data_only=True) for k, p in r.items()}
        return _ПРИЁМКА
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_libreoffice_сценарий_A_частичная_оплата() -> None:
    кн = сценарии_приёмки()
    if not кн:
        return
    рс = кн["A"]["Расчёт"]
    assert рс["D2"].value == "ГОТОВ", f"сценарий A заблокирован: {рс['D2'].value}"
    assert Decimal(str(рс["D3"].value)) == Decimal("18465.75"), f"сценарий A: {рс['D3'].value} ≠ 18465.75"
    assert abs(рс["D4"].value - 500_000) < 0.005, f"долг на последний день {рс['D4'].value} ≠ 500 000"
    # ввод текущего остатка вместе с оплатой заблокирован, а не даёт 12 000
    плохо = кн["A_остаток"]
    assert плохо["Расчёт"]["D2"].value == "ЗАБЛОКИРОВАН", (
        f"текущий остаток как сумма долга прошёл: {плохо['Расчёт']['D3'].value}")
    итог = плохо["Расчёт"]["D3"].value
    assert isinstance(итог, str), f"заблокированный расчёт всё равно выдал сумму {итог}"
    assert "12000" not in итог.replace(" ", ""), f"получен заниженный результат двойного учёта: {итог}"
    сообщение = str(плохо["Акты"]["H5"].value)
    assert "сверка не сходится" in сообщение and "ПЕРВЫЙ ДЕНЬ ПРОСРОЧКИ" in сообщение, сообщение


def test_libreoffice_сценарий_B_несколько_актов() -> None:
    кн = сценарии_приёмки()
    if not кн:
        return
    рс = кн["B"]["Расчёт"]
    assert рс["D2"].value == "ГОТОВ", f"сценарий B заблокирован: {рс['D2'].value}"
    assert Decimal(str(рс["D3"].value)) == Decimal("26356.16"), f"сценарий B: {рс['D3'].value} ≠ 26356.16"
    # акты не объединены: у каждого свои проценты и своя дата начала просрочки
    свод = {рс[f"M{7 + i}"].value: рс[f"P{7 + i}"].value for i in range(2)}
    assert set(свод) == {АКТ_A[0], АКТ_B[0]}, f"свод по актам: {свод}"
    assert Decimal(str(свод[АКТ_A[0]])) == Decimal("18465.75"), свод
    assert Decimal(str(свод[АКТ_B[0]])) == Decimal("7890.41"), свод
    assert рс["N7"].value.date() == АКТ_A[2] and рс["N8"].value.date() == АКТ_B[2], "даты актов слиты"
    assert abs(рс["D4"].value - 800_000) < 0.005, f"долг на последний день {рс['D4'].value}"
    # строки расчёта — по каждому акту отдельно, итог — их сумма
    assert строки_расчёта(рс) == [
        (АКТ_A[0], date(2026, 7, 31), date(2026, 8, 20), 700_000, Decimal("8054.79")),
        (АКТ_A[0], date(2026, 8, 21), КОНЕЦ, 500_000, Decimal("10410.96")),
        (АКТ_B[0], date(2026, 8, 11), КОНЕЦ, 300_000, Decimal("7890.41"))], строки_расчёта(рс)
    дни = кн["B"]["По дням"]
    assert дни.max_row <= ПО_ДНЯМ_МАКС_СТРОК, f"«По дням» после пересчёта: {дни.max_row} строк"
    заполнено = [r for r in range(2, 2 + 70) if дни[f"A{r}"].value not in (None, "")]
    assert len(заполнено) == (КОНЕЦ - АКТ_A[2]).days + 1, "не одна строка на календарный день"
    # оплата акта раньше его первого дня просрочки блокирует
    рано = кн["B_до_начала_акта"]
    assert рано["Расчёт"]["D2"].value == "ЗАБЛОКИРОВАН", "оплата раньше начала просрочки акта прошла"
    assert "раньше первого дня просрочки" in str(рано["Оплаты"]["E7"].value), рано["Оплаты"]["E7"].value
    # платёж без акта расчёт не пропускает
    без = кн["B_без_акта"]
    assert без["Расчёт"]["D2"].value == "ЗАБЛОКИРОВАН", "нераспределённый платёж прошёл в расчёт"
    assert "распределить платёж документально" in str(без["Оплаты"]["E6"].value), без["Оплаты"]["E6"].value


def строки_расчёта(рс) -> list:
    return [(рс[f"B{r}"].value, рс[f"C{r}"].value.date(), рс[f"D{r}"].value.date(), рс[f"F{r}"].value,
             Decimal(str(рс[f"I{r}"].value)).quantize(Decimal("0.01")))
            for r in range(7, 7 + 512) if рс[f"C{r}"].value not in (None, "")]


def test_libreoffice_итог_это_сумма_строк_по_актам() -> None:
    """Регрессия округления: два акта, где округление периодов общего долга
    (4 553,14) отличается от суммы по актам (4 553,15). Итог — сумма строк."""
    кн = сценарии_приёмки()
    if not кн:
        return
    рс = кн["R"]["Расчёт"]
    assert рс["D2"].value == "ГОТОВ", f"сценарий R заблокирован: {рс['D2'].value}"
    строки = строки_расчёта(рс)
    assert строки == СТРОКИ_R, f"строки расчёта: {строки}"
    итог = Decimal(str(рс["D3"].value)).quantize(Decimal("0.01"))
    assert итог == Decimal("4553.15") == sum(x[4] for x in строки), f"итог {итог} ≠ сумма строк"
    assert итог != Decimal("4553.14"), "итог посчитан округлением общего долга"
    свод = [Decimal(str(рс[f"P{r}"].value)).quantize(Decimal("0.01")) for r in (7, 8)]
    assert свод == [Decimal("2660.08"), Decimal("1893.07")] and sum(свод) == итог, f"свод по актам: {свод}"
    # подмена одной строки: итог и итог акта сдвигаются ровно на неё
    п = кн["R_подмена"]["Расчёт"]
    assert п["D2"].value == "ГОТОВ", п["D2"].value
    assert Decimal(str(п["D3"].value)).quantize(Decimal("0.01")) == итог + 100, (
        f"итог не следует за строкой расчёта: {п['D3'].value}")
    assert Decimal(str(п["P7"].value)).quantize(Decimal("0.01")) == свод[0] + 100, п["P7"].value
    assert Decimal(str(п["I7"].value)).quantize(Decimal("0.01")) == Decimal("1250.72"), п["I7"].value


def test_libreoffice_сценарий_C_двойной_учёт_аванса() -> None:
    кн = сценарии_приёмки()
    if not кн:
        return
    вз = кн["C"]["Взаиморасчёты"]
    assert abs(вз["M10"].value - 500_000) < 0.005, f"корректный остаток {вз['M10'].value} ≠ 500 000"
    да = кн["C"]["Долг по актам"]
    assert abs(да["H5"].value - 700_000) < 0.005, f"долг на первый день просрочки {да['H5'].value} ≠ 700 000"
    assert abs(да["L5"].value - 500_000) < 0.005, f"текущий остаток по акту {да['L5'].value} ≠ 500 000"
    # спорных нет: бесспорные колонки равны общим
    assert abs(да["J5"].value - 700_000) < 0.005 and abs(да["M5"].value - 500_000) < 0.005, (да["J5"].value, да["M5"].value)
    assert да["E5"].value.date() == АКТ_A[2], "первый день просрочки считается не от срока оплаты"
    # тот же аванс дважды: итог заблокирован, 300 000 без предупреждения не выдаётся
    двойной = кн["C_двойной"]["Взаиморасчёты"]
    assert isinstance(двойной["M10"].value, str) and "ЗАБЛОКИРОВАН" in двойной["M10"].value, (
        f"двойной учёт аванса дал итог {двойной['M10'].value}")
    сообщения = [str(двойной[f"I{i}"].value) for i in range(5, 11)
                 if "двойной учёт аванса" in str(двойной[f"I{i}"].value)]
    assert len(сообщения) >= 2, f"двойной учёт не помечен на обеих строках: {сообщения}"
    assert "учитывается один раз" in сообщения[0], сообщения[0]
    # и лист «Долг по актам» не выдаёт суммы к переносу в файл 14 (было: 500 000 и 300 000)
    да = кн["C_двойной"]["Долг по актам"]
    assert not isinstance(да["H5"].value, (int, float)), f"при двойном авансе долг к переносу {да['H5'].value}"
    for c in ("J5", "L5", "M5"):
        assert not isinstance(да[c].value, (int, float)), f"при двойном авансе {c} к переносу {да[c].value}"
    assert str(да["N5"].value).startswith("БЛОК") and "двойной учёт аванса" in str(да["N5"].value), да["N5"].value
    assert да["O5"].value in (None, ""), f"акт помечен к переносу: {да['O5'].value}"


def test_сборка_воспроизводима() -> None:
    try:
        import build_s1_candidate as B
    except SystemExit as e:
        ПРОПУСКИ.append(f"воспроизводимость: {e}")
        return
    tmp = Path(tempfile.mkdtemp(prefix="s1-build-"))
    try:
        B.build(tmp / "c")
        assert sorted(p.name for p in C.iterdir()) == sorted(p.name for p in (tmp / "c").iterdir()), (
            "состав закоммиченного кандидата отличается от вывода генератора")
        разные = [p.name for p in sorted(C.iterdir())
                  if p.read_bytes() != (tmp / "c" / p.name).read_bytes()]
        assert not разные, f"закоммиченный кандидат отличается от вывода генератора: {разные}"
        assert R.ROUTE_MAP.read_text(encoding="utf-8") == B.route_map_json(), (
            f"{R.ROUTE_MAP.name} отличается от вывода генератора")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────── S1-02А: состав и маршрут (контракт §9.1) ───────────────

# Перечень §10.1a — утверждённый состав выдачи. Держится здесь, а не берётся
# из s1_route: проверка ловит расхождение источника с утверждённым перечнем.
СОСТАВ_11 = [
    "00-START-HERE.txt",
    "01-karta-situacii-i-granic.docx",
    "02-proverka-i-kontrol-otveta.xlsx",
    "03-algoritm-dejstviy.docx",
    "04-uchet-raschetov-i-otpravok.xlsx",
    "05-peregovory-i-perenos-sroka.docx",
    "06-uvedomlenie-o-prosrochke.docx",
    "07-otpravka-i-dokazatelstvo.docx",
    "08-raschet-procentov-395.xlsx",
    "09-pretenziya.docx",
    "10-obrashchenie-v-sud.docx",
]
# §10.1a «Не входят в выдачу»: файлы, листы книги учёта и часть файла 10 #286
ИСКЛЮЧЁННЫЕ_ФАЙЛЫ = {"04-ks-2-ks-3.xlsx", "05-akt-vypolnennyh-rabot.docx", "06-akt-priemki-rezultata.docx",
                     "07-peredatochnyy-akt.docx", "09-vnutrennyaya-proverka.docx"}
ИСКЛЮЧЁННЫЕ_ЛИСТЫ = {"Журнал объёмов", "Реестр замечаний"}
ИСКЛЮЧЁННОЕ_В_ТЕКСТЕ = re.compile(r"журнал\w* объёмов|реестр\w* замечаний|сопроводительн\w* письм|"
                                  r"[Шш]аг(?:и|е|у|ам|ов)?\s+[2-5]\b", re.I)
ПРОВЕРКА_02 = C / "02-proverka-i-kontrol-otveta.xlsx"
КНИГА_УЧЁТА = C / "04-uchet-raschetov-i-otpravok.xlsx"
КНИГА_РАСЧЁТА = C / "08-raschet-procentov-395.xlsx"
# ссылка на шаг маршрута задолженности (6–12)
ДОЛГОВЫЕ_ШАГИ = re.compile(r"[Шш]аг(?:и|у|ам|ов)?\s+(?:6|7|8|9|1[0-2])\b")
ШАГ_ИЛИ_ГРАНИЦА = re.compile(r"[Шш]аг(?:и|у|ам)?\s+\d|[Гг]раница B\d|[Мм]аршрут завершён")
РЕАКЦИИ_ND6 = ("Прислал гарантийное письмо без соглашения", "Подписал акт сверки, но не оплатил",
               "Возражает по сумме или вернул акт сверки с расхождением",
               "Отказ: работы не предусмотрены договором")
ВХОДЯЩИЕ_ND2 = ("Гарантийное письмо заказчика", "Протокол переговоров / соглашение",
                "Акт сверки, подписанный Заказчиком", "Возражения Заказчика")


def docx_элементы(path: Path) -> list[tuple[str, str, int | None]]:
    """Тело документа по порядку: (вид, текст, уровень заголовка или None).
    Таблица — одним элементом, текст ячеек через « | »."""
    xml = docx_xml(path)
    body = xml[xml.index("<w:body>"):]
    out = []
    for m in re.finditer(r"<w:tbl>.*?</w:tbl>|<w:p[ >].*?</w:p>", body, re.S):
        el = m.group(0)
        if el.startswith("<w:tbl>"):
            ячейки_ = [html.unescape("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc)))
                       for tc in re.findall(r"<w:tc>.*?</w:tc>", el, re.S)]
            out.append(("tbl", " | ".join(ячейки_), None))
            continue
        текст = html.unescape("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", el)))
        стиль = re.search(r'<w:pStyle w:val="([^"]+)"', el)
        уровень = None
        if стиль:
            s = стиль.group(1)
            уровень = 0 if s == "Title" else (int(s[7:]) if s.startswith("Heading") and s[7:].isdigit() else None)
        out.append(("p", текст, уровень))
    return out


def docx_заголовки(path: Path) -> list[str]:
    return [t for вид, t, ур in docx_элементы(path) if вид == "p" and ур is not None]


def раздел(path: Path, начало: str) -> str:
    """Текст раздела от заголовка, который начинается с `начало`, до следующего
    заголовка того же или более высокого уровня. Нет раздела — пустая строка."""
    эл = docx_элементы(path)
    for i, (вид, t, ур) in enumerate(эл):
        if вид == "p" and ур is not None and t.startswith(начало):
            части = []
            for вид2, t2, ур2 in эл[i + 1:]:
                if ур2 is not None and ур2 <= ур:
                    break
                части.append(t2)
            return "\n".join(части)
    return ""


def таблица_строк(path: Path, заголовок_колонки: str) -> int:
    """Число строк самой длинной таблицы, у которой есть колонка с этим заголовком."""
    xml = docx_xml(path)
    строк = [len(re.findall(r"<w:tr[ >]", t)) for t in re.findall(r"<w:tbl>.*?</w:tbl>", xml, re.S)
             if заголовок_колонки in html.unescape("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", t)))]
    return max(строк, default=0)


def листы(book: Path) -> list[str]:
    with zipfile.ZipFile(book) as z:
        return [html.unescape(n) for n in re.findall(r'<sheet[^>]*name="([^"]+)"', z.read("xl/workbook.xml").decode())]


def ячейки(book: Path, title: str) -> dict[str, str]:
    """Значения ячеек листа без openpyxl: строки общего словаря и вписанные."""
    with zipfile.ZipFile(book) as z:
        общие = []
        if "xl/sharedStrings.xml" in z.namelist():
            sx = z.read("xl/sharedStrings.xml").decode("utf-8")
            общие = [html.unescape("".join(re.findall(r"<t[^>]*>([^<]*)</t>", si)))
                     for si in re.findall(r"<si>(.*?)</si>", sx, re.S)]
    out = {}
    for ref, attrs, body in re.findall(r'<c r="([A-Z]+\d+)"([^>]*?)(?:/>|>(.*?)</c>)', sheet_xml(book, title), re.S):
        v = re.search(r"<v>([^<]*)</v>", body or "")
        if 't="s"' in attrs and v:
            out[ref] = общие[int(v.group(1))]
        elif 't="inlineStr"' in attrs:
            out[ref] = html.unescape("".join(re.findall(r"<t[^>]*>([^<]*)</t>", body)))
        elif v:
            out[ref] = html.unescape(v.group(1))
    return out


# «файл 04», «файлы 04–07, 09», «файл 04, лист «Долг по актам»», «файл 10, раздел В»,
# «файл 01, таблица 2», «файла 15 (раздел «Опись…»)»
ССЫЛКА = re.compile(
    r"[Фф]айл(?:а|е|ы|ом|у|ам|ах)?\s+(\d{2}(?:\s*(?:,|и|–|-)\s*\d{2})*)"
    r"(?:\s*[,(]?\s*(?:(?:лист|раздел)\s*)?«([^»]+)»"
    r"|\s*[,(]\s*раздел\s+([А-Г])(?![А-Яа-я])"
    r"|\s*[,(]\s*таблиц[аеуы]\s+(\d+а?)(?![А-Яа-я0-9]))?")
ИМЯ_ФАЙЛА = re.compile(r"\b\d{2}-[a-z0-9-]+\.(?:docx|xlsx|txt)\b")


def _номера(список: str) -> list[str]:
    out = []
    for часть in re.split(r"\s*(?:,|и)\s*", список):
        m = re.fullmatch(r"(\d{2})\s*[–-]\s*(\d{2})", часть)
        out += [f"{n:02d}" for n in range(int(m.group(1)), int(m.group(2)) + 1)] if m else [часть]
    return out


def перекрёстные_ссылки() -> tuple[list[str], list[str]]:
    """(битые, на исключённое) по всем выдаваемым файлам."""
    по_номеру = {p.name[:2]: p for p in delivered()}
    битые, исключённые = [], []
    for f in delivered():
        текст = " ".join(buyer_text(f).split())
        for m in ССЫЛКА.finditer(текст):
            номера, кавычки, буква, таблица = m.groups()
            for i, n in enumerate(_номера(номера)):
                цель = по_номеру.get(n)
                где = f"{f.name}: «{m.group(0)}»"
                if цель is None:
                    битые.append(f"{где} — файла {n} нет в выдаче")
                    continue
                if цель.name in ИСКЛЮЧЁННЫЕ_ФАЙЛЫ:
                    исключённые.append(f"{где} → {цель.name}")
                    continue
                if i != len(_номера(номера)) - 1 or not (кавычки or буква or таблица):
                    continue
                if цель.suffix == ".xlsx":
                    if кавычки in ИСКЛЮЧЁННЫЕ_ЛИСТЫ:
                        исключённые.append(f"{где} → лист исключён")
                    elif кавычки and кавычки not in листы(цель):
                        битые.append(f"{где} — в {цель.name} нет листа «{кавычки}»")
                    elif буква or таблица:
                        битые.append(f"{где} — у книги нет разделов и таблиц")
                    continue
                заголовки = docx_заголовки(цель) if цель.suffix == ".docx" else []
                if кавычки and not any(кавычки.lower() in з.lower() for з in заголовки):
                    битые.append(f"{где} — в {цель.name} нет раздела «{кавычки}»")
                elif буква and not any(з.startswith(f"Раздел {буква}.") for з in заголовки):
                    битые.append(f"{где} — в {цель.name} нет раздела {буква}")
                elif таблица and not any(з.startswith(f"Таблица {таблица}.") for з in заголовки):
                    битые.append(f"{где} — в {цель.name} нет таблицы {таблица}")
        for имя in ИМЯ_ФАЙЛА.findall(текст):
            if имя not in R.FILES:
                (исключённые if имя in ИСКЛЮЧЁННЫЕ_ФАЙЛЫ else битые).append(f"{f.name}: имя {имя} не в составе")
        for m in ИСКЛЮЧЁННОЕ_В_ТЕКСТЕ.finditer(текст):
            исключённые.append(f"{f.name}: «{m.group(0)}» — исключённая часть или шаг 2–5")
    return битые, исключённые


def test_перекрёстные_ссылки_целы() -> None:
    битые, исключённые = перекрёстные_ссылки()
    assert not битые and not исключённые, (
        f"битых ссылок {len(битые)}, ссылок на исключённое {len(исключённые)}:\n  "
        + "\n  ".join(битые + исключённые))


def test_выдача_ровно_11_файлов_без_карты_маршрута() -> None:
    assert list(R.FILES) == СОСТАВ_11, f"состав s1_route не совпадает с перечнем §10.1a: {list(R.FILES)}"
    assert "ROUTE-MAP.json" not in _служебные_из_выдачи(), "проверка опиралась бы на исключение, а не на отсутствие"
    архив = _архив_покупателя(C)
    assert архив == sorted(СОСТАВ_11), (
        f"в архив попало {len(архив)} файлов: лишние {sorted(set(архив) - set(СОСТАВ_11))}, "
        f"нет {sorted(set(СОСТАВ_11) - set(архив))}")
    assert not any("ROUTE-MAP" in n or n.endswith(".json") for n in архив), "служебная карта в выдаче"
    # «СОСТАВ» START-HERE и MANIFEST перечисляют ровно архив
    старт = START_HERE()
    assert "\nСОСТАВ\n" in старт, "в START-HERE нет раздела «СОСТАВ»"
    блок = старт.split("\nСОСТАВ\n", 1)[1].split("\n\n", 1)[0]
    assert re.findall(r"^\s+(\S+\.(?:txt|docx|xlsx)) — ", блок, re.M) == СОСТАВ_11, f"«СОСТАВ» START-HERE:\n{блок}"
    ман = (C / "MANIFEST.md").read_text(encoding="utf-8")
    assert re.findall(r"^- `(\d{2}-[^`]+)`", ман, re.M) == СОСТАВ_11, "MANIFEST перечисляет не 11 файлов выдачи"
    # #320 S-3: строка книги расчёта говорит, что актов может быть несколько
    строка = next(l for l in блок.splitlines() if "08-raschet-procentov-395.xlsx" in l)
    assert "несколько актов" in строка, f"START-HERE не говорит, что книга считает несколько актов: {строка}"
    try:
        import build_s1_candidate as B
    except SystemExit as e:
        ПРОПУСКИ.append(f"выдача из генератора: {e}")
        return
    tmp = Path(tempfile.mkdtemp(prefix="s1-out-"))
    try:
        B.build(tmp / "izdanie")
        архив = _архив_покупателя(tmp / "izdanie")
        assert архив == sorted(СОСТАВ_11) and len(архив) == 11, f"генератор кладёт в выдачу: {архив}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


ОТВЕТ_ДА = {"q1", "q2", "q11", "q12", "q15"}   # остальные вопросы «Маршрута» — «Нет» в чистом случае


def заполнить_маршрут(src: Path, dst: Path, правки: dict) -> Path:
    import openpyxl
    import build_s1_candidate as B
    wb = openpyxl.load_workbook(src)
    ws = wb["Маршрут"]
    for i, (q, _) in enumerate(B.QUESTIONS):
        ws[f"C{5 + i}"] = правки.get(q, "Да" if q in ОТВЕТ_ДА else "Нет")
    wb.save(dst)
    return dst


def строка_итога() -> int:
    import build_s1_candidate as B
    return 4 + len(B.QUESTIONS) + 3   # шапка, вопросы, пропуск, служебный код


def test_допработы_выход_B5_маршрут() -> None:
    assert "B5" in R.BOUNDARIES, "нет границы B5 «Допработы без соглашения»"
    b5 = R.BOUNDARIES["B5"]
    for w in ("допработ", "соглашени"):
        assert w in (b5["name"] + b5["signs"]).lower(), f"B5: признак «{w}» не назван"
    m = ДОЛГОВЫЕ_ШАГИ.search(b5["buyer_next"])
    assert not m, f"B5 ведёт в шаги 6–12: «{m.group(0)}»"
    assert "файл 10, раздел В" in b5["buyer_next"], "B5 не называет опись по точному имени раздела"
    for sid in ("S6", "S11"):
        assert "B5" in _шаг(sid)["boundaries"], f"{sid}: B5 не распознаётся"
        assert any("B5" in f for f in _шаг(sid)["forks"]), f"{sid}: нет развилки на B5"
    assert b5["name"] in docx_text(C / "01-karta-situacii-i-granic.docx"), "B5 нет в карте границ (файл 01)"
    assert "B5" in раздел(C / "09-pretenziya.docx", "Перед отправкой"), "B5 нет в «Перед отправкой» претензии"
    assert "B5" in раздел(C / "10-obrashchenie-v-sud.docx", "Раздел А."), "B5 нет в проверочном листе иска"
    assert ПРОВЕРКА_02.exists(), f"нет {ПРОВЕРКА_02.name}"
    маршрут = xlsx_text(ПРОВЕРКА_02)
    assert '"B5"' in маршрут and "ГРАНИЦА B5" in маршрут, "маршрутизатор файла 02 не выдаёт B5"
    причина = _lo_ready()
    if причина:
        ПРОПУСКИ.append(f"B5 в Calc: {причина}")
        return
    import openpyxl
    import build_s1_candidate as B
    q = next(k for k, t in B.QUESTIONS if "допсоглашени" in t and "смет" in t)
    tmp = Path(tempfile.mkdtemp(prefix="s1-b5-"))
    try:
        r = пересчитать({"b5": заполнить_маршрут(ПРОВЕРКА_02, tmp / "b5.xlsx", {q: "Да"})}, tmp)
        ws = openpyxl.load_workbook(r["b5"], data_only=True)["Маршрут"]
        итог, след = str(ws[f"C{строка_итога()}"].value), str(ws[f"C{строка_итога() + 1}"].value)
        assert итог.startswith("ГРАНИЦА B5"), f"ответ «Да» о допработах даёт «{итог}»"
        assert not ДОЛГОВЫЕ_ШАГИ.search(след), f"B5 ведёт в шаги 6–12: {след}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def реакции_02() -> dict[str, str]:
    спр = ячейки(ПРОВЕРКА_02, "Справочник")
    шапка = next(int(k[1:]) for k, v in спр.items() if k.startswith("A") and v == "Реакция заказчика")
    out, r = {}, шапка + 1
    while спр.get(f"A{r}"):
        out[спр[f"A{r}"]] = спр.get(f"B{r}", "")
        r += 1
    return out


def test_реакции_на_сверку_письмо_допработы() -> None:
    assert ПРОВЕРКА_02.exists(), f"нет {ПРОВЕРКА_02.name}"
    реакции = реакции_02()
    нет = [р for р in РЕАКЦИИ_ND6 if р not in реакции]
    assert not нет, f"в «Контроле ответа» нет реакций: {нет}"
    # список выбора в «Контроле ответа» покрывает все реакции
    dv = re.search(r"<formula1>Справочник!\$A\$(\d+):\$A\$(\d+)</formula1>",
                   html.unescape(sheet_xml(ПРОВЕРКА_02, "Контроль ответа")))
    assert dv and int(dv.group(2)) - int(dv.group(1)) + 1 == len(реакции), "список выбора реакций короче справочника"
    for р, шаг in реакции.items():
        assert ШАГ_ИЛИ_ГРАНИЦА.search(шаг), f"реакция «{р}» не называет следующего шага: {шаг}"
        if re.search(r"[Гг]раница B[245]", шаг):
            m = ДОЛГОВЫЕ_ШАГИ.search(шаг)
            assert not m, f"спорная реакция «{р}» ведёт в шаги 6–12: «{m.group(0)}»"
    assert "не перенесён" in реакции[РЕАКЦИИ_ND6[0]], "гарантийное письмо: нет правила «срок не перенесён»"
    assert ДОЛГОВЫЕ_ШАГИ.search(реакции[РЕАКЦИИ_ND6[1]]), "подписанный акт сверки не ведёт дальше по маршруту"
    for b in ("B2", "B4", "B5"):
        assert b in реакции[РЕАКЦИИ_ND6[2]], f"возражение по сумме не разводит по {b}"
    assert "B5" in реакции[РЕАКЦИИ_ND6[3]], "«работы не предусмотрены договором» не ведёт к B5"
    # ND-7: B4 — для принятых работ; неоспоренные акты идут дальше
    b4 = R.BOUNDARIES["B4"]
    assert "после подписания" in b4["signs"], "B4 описан не для принятых работ"
    assert "не оспаривает" in b4["buyer_next"], "B4 не говорит, что неоспоренные акты идут дальше"
    assert "файл 10, раздел В" in b4["buyer_next"], "B4 не называет опись по точному имени раздела"


def test_входящие_документы_не_в_реестре_передачи() -> None:
    f05 = C / "05-peregovory-i-perenos-sroka.docx"
    assert f05.exists(), f"нет {f05.name}"
    в = раздел(f05, "Раздел В.")
    assert в, "в файле 05 нет раздела В"
    m = re.search(r"(?<!не )(?:внес|внос)\w*[^.;|]{0,40}реестр\w* передачи", в, re.I)
    assert not m, f"файл 05, раздел В отправляет входящий документ в «Реестр передачи»: «{m.group(0)}»"
    assert "«Контроль ответа»" in в and "«Реестр приложений»" in в, "файл 05, раздел В не называет места учёта входящих"
    assert КНИГА_УЧЁТА.exists(), f"нет {КНИГА_УЧЁТА.name}"
    строки = {v for k, v in ячейки(КНИГА_УЧЁТА, "Реестр приложений").items() if re.fullmatch(r"B\d+", k)}
    нет = [d for d in ВХОДЯЩИЕ_ND2 if d not in строки]
    assert not нет, f"в «Реестре приложений» нет строк: {нет}"
    передача = " ".join(ячейки(КНИГА_УЧЁТА, "Реестр передачи").values())
    assert "входящие" in передача.lower(), "«Реестр передачи» не говорит, что входящие в него не вносятся"


def test_претензия_содержит_сумму_процентов() -> None:
    f09, f06 = C / "09-pretenziya.docx", C / "06-uvedomlenie-o-prosrochke.docx"
    assert f09.exists() and f06.exists(), "нет файлов 09 и 06 нового состава"
    абзацы = [t for вид, t, _ in docx_элементы(f09) if вид == "p"]
    п4 = next((a for a in абзацы if a.startswith("4. Требуем")), "")
    for поле in ("{{СУММА_ПРОЦЕНТОВ}}", "{{ДАТА_РАСЧЁТА}}"):
        assert поле in п4, f"в требовании претензии (п. 4) нет поля {поле}: {п4}"
        assert поле in раздел(f09, "Перед отправкой"), f"«Перед отправкой» не говорит, откуда взять {поле}"
    for f, колонка in ((f06, "Акт (№, дата)"), (f09, "Документ (КС-2, КС-3, акт), №"), (f09, "Дата оплаты")):
        строк = таблица_строк(f, колонка) - 1
        assert строк >= 12, f"{f.name}: в таблице «{колонка}» {строк} строк, книга расчёта принимает 12 актов"


# ── S1-02А-FIX: замечания независимой проверки #325, §5.2 ──

АЛГОРИТМ_03 = C / "03-algoritm-dejstviy.docx"


def формула(book: Path, title: str, ref: str) -> str:
    m = re.search(rf'<c r="{ref}"[^>]*>\s*<f>([^<]*)</f>', sheet_xml(book, title))
    return html.unescape(m.group(1)) if m else ""


def _развилка_письма(sid: str) -> str:
    return next((f for f in _шаг(sid)["forks"] if "гарантийное письмо без соглашения" in f.lower()), "")


def test_н1_гарантийное_письмо_один_следующий_шаг_в_02_и_03() -> None:
    """Н-1: для одного события 02 и 03 называют один и тот же следующий шаг,
    в том числе «дата из письма прошла — сразу шаг 9»."""
    реакция = реакции_02()[РЕАКЦИИ_ND6[0]]
    assert "сразу шаг 9" in реакция, f"02: реакция на гарантийное письмо не ведёт к шагу 9 при срыве даты: {реакция}"
    текст03 = docx_text(АЛГОРИТМ_03)
    for sid in ("S7", "S11"):
        развилка = _развилка_письма(sid)
        assert развилка, f"{sid}: нет развилки «гарантийное письмо без соглашения»"
        assert реакция in развилка, (
            f"{sid}: следующий шаг развилки письма в 03 расходится с 02.\n03: {развилка}\n02: {реакция}")
        assert развилка in текст03, f"{sid}: развилка письма не дошла до файла 03"


def _маршрут_в_calc(варианты: dict) -> dict[str, dict[str, str]]:
    import openpyxl
    tmp = Path(tempfile.mkdtemp(prefix="s1-fix-"))
    try:
        книги = {k: заполнить_маршрут(ПРОВЕРКА_02, tmp / f"{k}.xlsx", v) for k, v in варианты.items()}
        r = пересчитать(книги, tmp)
        out = {}
        for k in варианты:
            ws = openpyxl.load_workbook(r[k], data_only=True)["Маршрут"]
            out[k] = {str(ws[f"B{i}"].value or ""): str(ws[f"C{i}"].value or "") for i in range(1, ws.max_row + 1)}
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_н2_детальная_проверка_называет_ситуацию_В() -> None:
    """Н-2: ответ «Да» только на вопрос о гарантийном письме даёт ситуацию В,
    а не А; письмо при подписанном соглашении — не В."""
    import build_s1_candidate as B
    q = next(k for k, t in B.QUESTIONS if "гарантийное письмо" in t)
    строка_q = 5 + [k for k, _ in B.QUESTIONS].index(q)
    код = формула(ПРОВЕРКА_02, "Маршрут", f"C{строка_итога() - 1}")
    assert f"C{строка_q}" in код, f"код маршрута не читает вопрос о гарантийном письме (C{строка_q}): {код}"
    итоги = " ".join(v for k, v in ячейки(ПРОВЕРКА_02, "Справочник").items() if k.startswith("B"))
    assert "СИТУАЦИЯ В" in итоги, "в «Справочнике» нет итога для ситуации В"
    причина = _lo_ready()
    if причина:
        ПРОПУСКИ.append(f"Н-2 в Calc: {причина}")
        return
    с = {"ок": {}, "письмо": {q: "Да"}, "письмо_и_соглашение": {q: "Да", "q13": "Да"}, "сверка": {"q15": "Нет"}}
    r = _маршрут_в_calc(с)
    assert r["письмо"]["ИТОГ"].startswith("СИТУАЦИЯ В"), f"гарантийное письмо: итог «{r['письмо']['ИТОГ']}»"
    assert "шаг 9" in r["письмо"]["Следующий шаг"], f"ситуация В: нет правила шага 9: {r['письмо']['Следующий шаг']}"
    assert "Ситуация А" in r["ок"]["Следующий шаг"], f"чистый случай: {r['ок']}"
    assert "Ситуация А" in r["письмо_и_соглашение"]["Следующий шаг"], f"письмо + соглашение: {r['письмо_и_соглашение']}"
    assert r["сверка"]["ИТОГ"].startswith("СИТУАЦИЯ Б"), f"не сверено: {r['сверка']['ИТОГ']}"


def test_н3_детальная_проверка_не_теряет_вторую_границу() -> None:
    """Н-3: при B4 и B5 одновременно итог называет обе границы."""
    причина = _lo_ready()
    if причина:
        ПРОПУСКИ.append(f"Н-3 в Calc: {причина}")
        return
    r = _маршрут_в_calc({"b4b5": {"q6": "Да", "q17": "Да"}, "b5": {"q17": "Да"}, "ок": {}})
    assert r["b4b5"]["ИТОГ"].startswith("ГРАНИЦА B4"), r["b4b5"]["ИТОГ"]
    ещё = r["b4b5"].get("Ещё границы", "")
    assert "B5" in ещё and "B4" not in ещё, f"при B4 и B5 вторая граница не названа: «{ещё}»"
    assert not r["b5"].get("Ещё границы") and not r["ок"].get("Ещё границы"), "лишние границы при одной или ни одной"


def test_н4_претензия_говорит_о_входящих_документах() -> None:
    т = docx_text(C / "09-pretenziya.docx")
    прил = т[т.find("Приложения (по реестру"):т.find("После отправки")] if "Приложения (по реестру" in т else ""
    assert "гарантийн" in прил.lower() and "«К претензии»" in прил, (
        f"в приложениях претензии нет правила для входящих документов заказчика: {прил}")


def test_н5_даты_просрочки_по_каждому_акту() -> None:
    """Н-5: при нескольких актах дата срока — по каждому акту в таблице,
    а не одно поле на все акты."""
    f09, f06, f10, f05 = (C / n for n in ("09-pretenziya.docx", "06-uvedomlenie-o-prosrochke.docx",
                                          "10-obrashchenie-v-sud.docx", "05-peregovory-i-perenos-sroka.docx"))
    for f, одно in ((f09, "Срок оплаты истёк {{ДАТА}}"), (f06, "договора истёк {{ДАТА}}"),
                    (f10, "{{ДАТА_С}}"), (f05, "{{ДАТА_НАЧАЛА_ПРОСРОЧКИ}}")):
        assert одно not in docx_text(f), f"{f.name}: одно поле даты на все акты «{одно}»"
    for f, колонка in ((f09, "Последний день срока оплаты"), (f05, "Первый день просрочки")):
        assert таблица_строк(f, колонка) > 1, f"{f.name}: в таблице актов нет колонки «{колонка}»"


def test_н6_выгрузка_взаиморасчётов_печатается() -> None:
    fj = формула(КНИГА_УЧЁТА, "Взаиморасчёты", "J6")
    assert '""' in fj, f"нарастающий итог печатается в пустых строках: {fj}"
    т = docx_text(C / "06-uvedomlenie-o-prosrochke.docx")
    assert "выгрузка из файла 04" not in т and "выделен" in т.lower(), "06 не говорит, как сделать приложение-реестр"


def test_н8_подтверждение_шага_12_называет_опись() -> None:
    п = _шаг("S12")["confirmation"]
    assert "«Реестр приложений»" in п and "файл 10, раздел В" in п, f"шаг 12: неясно, какая опись: {п}"


def test_н8a_проверочный_лист_иска_согласован_с_B4() -> None:
    а = раздел(C / "10-obrashchenie-v-sud.docx", "Раздел А.")
    п5 = next((s for s in а.split(" | ") if "мотивированного отказа" in s), "")
    assert "переданы специалисту" in п5 and "в иск" in п5, f"п. 5 не согласован с п. 4 и B4: {п5}"


def test_н9_нет_остатков_сдачи_работ_и_даты_для_входящих() -> None:
    прил = {v for k, v in ячейки(КНИГА_УЧЁТА, "Реестр приложений").items() if re.fullmatch(r"B\d+", k)}
    assert not [d for d in прил if "замечани" in d.lower()], f"остаток этапа сдачи работ: {прил}"
    шапка = ячейки(ПРОВЕРКА_02, "Контроль ответа").get("B4", "")
    assert "получени" in шапка, f"колонка для входящего письма: «{шапка}»"


# ── S1-02Б: финансовая граница (контракт §9.2) ──

# Типы спорных операций — дословно как в списке «Взаиморасчётов» (§9.2)
СПОРНЫЕ_ТИПЫ = ("Удержание", "Зачёт встречного требования", "Неустойка заявлена",
                "Допработы без соглашения (спорно)")
# данные теста #286: начисление 1 000 000, аванс 100 000, 12 оплат на 120 066, удержание 50 000
ДАННЫЕ_286 = ([(date(2025, 1, 1) + timedelta(days=i), t, f"док. № {i + 1}", s, ОДИН_АКТ)
               for i, (t, s) in enumerate([("Начисление по акту", 1_000_000), ("Зачёт аванса по договору", 100_000)]
                                          + [("Оплата", 10_000 + i) for i in range(12)]
                                          + [("Удержание", 50_000)])],
              [(ОДИН_АКТ, "КС-2 № 1 от 01.01.2025", date(2025, 1, 20))])
# лист «Акт сверки» книги учёта: статус, строка итога, строка-вывод
АС_СТАТУС, АС_ИТОГ, АС_ВЫВОД = "C3", 43, "A45"


def _число(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _учёт_в_calc(сценарии: dict, tmp: Path) -> dict:
    """Книга учёта в Calc: имя → (операции, акты) → пересчитанная книга (data_only)."""
    import openpyxl
    книги = {k: заполнить_08(КНИГА_УЧЁТА, tmp / f"u_{k}.xlsx", оп, акты) for k, (оп, акты) in сценарии.items()}
    r = пересчитать(книги, tmp / "u")
    return {k: openpyxl.load_workbook(p, data_only=True) for k, p in r.items()}


def test_общий_долг_и_спорная_часть_раздельно() -> None:
    """§9.2: общий 779 934, спорная 50 000, бесспорная 729 934; в «Акты» книги
    расчёта уходит 729 934; спорная операция без акта и спорная сверх общего — БЛОК."""
    причина = _lo_ready()
    if причина:
        ПРОПУСКИ.append(f"финансовая граница в Calc: {причина}")
        return
    import openpyxl
    оп, акты = ДАННЫЕ_286
    без_акта = оп[:-1] + [оп[-1][:4] + (None,)]
    сверх = оп[:-1] + [оп[-1][:3] + (800_000, ОДИН_АКТ)]
    tmp = Path(tempfile.mkdtemp(prefix="s1-02b-"))
    try:
        кн = _учёт_в_calc({"ок": (оп, акты), "без_акта": (без_акта, акты), "сверх": (сверх, акты)}, tmp)
        вз, да = кн["ок"]["Взаиморасчёты"], кн["ок"]["Долг по актам"]
        assert "общий долг" in str(вз["L10"].value).lower(), f"M10 не называется общим долгом: {вз['L10'].value}"
        for ячейка, ждём in (("M10", 779_934), ("M11", 50_000), ("M12", 729_934)):
            assert _число(вз[ячейка].value) and abs(вз[ячейка].value - ждём) < 0.005, f"{ячейка} = {вз[ячейка].value} ≠ {ждём}"
        assert "спорн" in str(вз["L11"].value).lower() and "бесспорн" in str(вз["L12"].value).lower(), (вз["L11"].value, вз["L12"].value)
        for ячейка, ждём in (("H5", 779_934), ("I5", 50_000), ("J5", 729_934), ("L5", 779_934), ("M5", 729_934)):
            assert _число(да[ячейка].value) and abs(да[ячейка].value - ждём) < 0.005, f"«Долг по актам» {ячейка} = {да[ячейка].value} ≠ {ждём}"
        assert да["N5"].value == "ок" and да["O5"].value == "да", (да["N5"].value, да["O5"].value)
        # передача в книгу расчёта: D ← J, E ← E, F ← M
        конец, ставка = date(2025, 3, 31), [(date(2024, 10, 28), 21)]
        b = заполнить_395(КНИГА_РАСЧЁТА, tmp / "r.xlsx", [(ОДИН_АКТ, да["J5"].value, да["E5"].value.date())],
                          конец, ставка, остаток={ОДИН_АКТ: да["M5"].value})
        рс = openpyxl.load_workbook(пересчитать({"r": b}, tmp / "r")["r"], data_only=True)["Расчёт"]
        эталон = SI.calculate(729_934, date(2025, 1, 21), конец, ставка)[0]
        assert рс["D2"].value == "ГОТОВ", f"бесспорная часть не прошла в книгу расчёта: {рс['D2'].value}"
        assert Decimal(str(рс["D3"].value)).quantize(Decimal("0.01")) == эталон, f"проценты {рс['D3'].value} ≠ {эталон}"
        assert эталон != SI.calculate(779_934, date(2025, 1, 21), конец, ставка)[0]
        assert abs(рс["D4"].value - 729_934) < 0.005, рс["D4"].value
        # спорная операция без акта
        вз = кн["без_акта"]["Взаиморасчёты"]
        строка = 5 + len(оп) - 1
        assert str(вз[f"I{строка}"].value).startswith("БЛОК") and "спорн" in str(вз[f"I{строка}"].value), вз[f"I{строка}"].value
        assert not _число(вз["M10"].value) and not _число(вз["M12"].value), (вз["M10"].value, вз["M12"].value)
        # спорная часть больше общего долга по акту
        вз, да = кн["сверх"]["Взаиморасчёты"], кн["сверх"]["Долг по актам"]
        assert str(да["N5"].value).startswith("БЛОК") and "спорн" in str(да["N5"].value), да["N5"].value
        assert not _число(да["J5"].value) and not _число(да["M5"].value), (да["J5"].value, да["M5"].value)
        assert да["O5"].value in (None, ""), да["O5"].value
        assert not _число(вз["M12"].value), f"бесспорная часть отрицательная или не заблокирована: {вз['M12'].value}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_допработы_спорная_сумма_в_реестре() -> None:
    """§9.2: начисление 1 000 000, «Допработы без соглашения (спорно)» 200 000 →
    общий 1 000 000, спорная 200 000, бесспорная 800 000; граница B5."""
    вз_ф = " ".join(formulas(КНИГА_УЧЁТА, "Взаиморасчёты"))
    for тип in СПОРНЫЕ_ТИПЫ:
        assert f'"{тип}"' in вз_ф, f"тип «{тип}» не считается спорным"
    with zipfile.ZipFile(КНИГА_УЧЁТА) as z:
        список = html.unescape(z.read(next(n for n in z.namelist() if n.endswith(".xml") and "sheet" in n
                                            and "Допработы" in html.unescape(z.read(n).decode()))).decode())
    assert СПОРНЫЕ_ТИПЫ[3] in список, "в списке типов операций нет «Допработы без соглашения (спорно)»"
    # тексты B2 называют типы так же, как список
    b2 = R.BOUNDARIES["B2"]["buyer_next"]
    for тип in СПОРНЫЕ_ТИПЫ[:3]:
        assert f"«{тип}»" in b2, f"B2 не называет тип «{тип}» как в списке: {b2}"
    assert f"«{СПОРНЫЕ_ТИПЫ[3]}»" in R.BOUNDARIES["B5"]["buyer_next"], "B5 не называет тип операции"
    причина = _lo_ready()
    if причина:
        ПРОПУСКИ.append(f"допработы в Calc: {причина}")
        return
    акт = "КС-2 № 3"
    оп = [(date(2026, 6, 16), "Начисление по акту", "КС-2 № 3 от 16.06.2026", 1_000_000, акт),
          (date(2026, 8, 6), СПОРНЫЕ_ТИПЫ[3], "возражения исх. № 131", 200_000, акт)]
    tmp = Path(tempfile.mkdtemp(prefix="s1-02b-b5-"))
    try:
        кн = _учёт_в_calc({"b5": (оп, [(акт, "КС-2 № 3 от 16.06.2026", date(2026, 7, 16))])}, tmp)["b5"]
        вз, да = кн["Взаиморасчёты"], кн["Долг по актам"]
        for ячейка, ждём in (("M10", 1_000_000), ("M11", 200_000), ("M12", 800_000)):
            assert _число(вз[ячейка].value) and abs(вз[ячейка].value - ждём) < 0.005, f"{ячейка} = {вз[ячейка].value} ≠ {ждём}"
        assert "B5" in str(вз["M13"].value), f"граница B5 не названа: {вз['M13'].value}"
        assert abs(да["J5"].value - 800_000) < 0.005 and abs(да["I5"].value - 200_000) < 0.005, (да["J5"].value, да["I5"].value)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_акт_сверки_из_реестра() -> None:
    """§9.2, ND-1: сценарий C #286 — общий 500 000, спорная 0; тот же сценарий
    с удержанием — спорная отдельной графой; двойной аванс — лист заблокирован."""
    assert "Акт сверки" in листы(КНИГА_УЧЁТА), f"в книге учёта нет листа «Акт сверки»: {листы(КНИГА_УЧЁТА)}"
    текст = " ".join(ячейки(КНИГА_УЧЁТА, "Акт сверки").values())
    for нужно in ("АКТ СВЕРКИ", "в том числе оспаривается Заказчиком", "По данным Заказчика", "Подпись"):
        assert нужно in текст, f"в акте сверки нет «{нужно}»"
    кн = сценарии_приёмки()
    if not кн:
        return
    ас = кн["C"]["Акт сверки"]
    assert ас[АС_СТАТУС].value == "ГОТОВ", f"акт сверки сценария C: {ас[АС_СТАТУС].value}"
    assert ас["B13"].value == АКТ_A[0], ас["B13"].value
    assert abs(ас[f"F{АС_ИТОГ}"].value - 500_000) < 0.005 and abs(ас[f"G{АС_ИТОГ}"].value) < 0.005, (
        ас[f"F{АС_ИТОГ}"].value, ас[f"G{АС_ИТОГ}"].value)
    уд = кн["C_удержание"]["Акт сверки"]
    assert уд[АС_СТАТУС].value == "ГОТОВ", уд[АС_СТАТУС].value
    assert abs(уд[f"F{АС_ИТОГ}"].value - 500_000) < 0.005, f"общий долг в акте сверки {уд[f'F{АС_ИТОГ}'].value}"
    assert abs(уд["G13"].value - 50_000) < 0.005 and abs(уд[f"G{АС_ИТОГ}"].value - 50_000) < 0.005, (
        уд["G13"].value, уд[f"G{АС_ИТОГ}"].value)
    вывод = str(уд[АС_ВЫВОД].value)
    assert "500" in вывод and "в том числе оспаривается" in вывод and "50" in вывод, вывод
    дв = кн["C_двойной"]["Акт сверки"]
    assert str(дв[АС_СТАТУС].value).startswith("НЕ ГОТОВ"), f"двойной аванс: акт сверки {дв[АС_СТАТУС].value}"
    assert not _число(дв[f"F{АС_ИТОГ}"].value), f"при двойном авансе акт сверки выдал итог {дв[f'F{АС_ИТОГ}'].value}"
    assert "НЕ ГОТОВ" in str(дв[АС_ВЫВОД].value), дв[АС_ВЫВОД].value


def test_книга_расчёта_берёт_только_бесспорную_часть() -> None:
    """§9.2 (статика): источник суммы «Актов» — «Бесспорный на первый день
    просрочки», сверка — «Текущий бесспорный остаток», а не «Общий»."""
    шапка = {k: v for k, v in ячейки(КНИГА_УЧЁТА, "Долг по актам").items() if re.fullmatch(r"[A-O]4", k)}
    assert "бесспорный на первый день просрочки" in шапка.get("J4", "").lower() and "файл 08" in шапка.get("J4", ""), шапка.get("J4")
    assert "текущий бесспорный остаток" in шапка.get("M4", "").lower() and "файл 08" in шапка.get("M4", ""), шапка.get("M4")
    assert "общий" in шапка.get("H4", "").lower() and "спорно" in шапка.get("I4", "").lower(), (шапка.get("H4"), шапка.get("I4"))
    for k, v in шапка.items():
        if "общий" in v.lower():
            assert "файл 08" not in v, f"«Общий» ведёт в книгу расчёта: {k} {v}"
    текст = xlsx_text(КНИГА_РАСЧЁТА)
    акты = ячейки(КНИГА_РАСЧЁТА, "Акты")
    assert "бесспорн" in акты.get("D4", "").lower() and "колонка J" in акты.get("D4", ""), акты.get("D4")
    assert "бесспорн" in акты.get("F4", "").lower() and "колонка M" in акты.get("F4", ""), акты.get("F4")
    assert "Бесспорный на первый день просрочки" in текст and "колонка H" not in текст, (
        "книга расчёта ссылается не на бесспорную колонку файла 04")
    assert "Общий на первый день" not in текст, "книга расчёта называет общий долг источником суммы"
    # S-1 (#320): служебный ключ «Интервалов» — число, а не дата
    assert re.search(r'<c r="G2" s="(\d+)"', sheet_xml(КНИГА_РАСЧЁТА, "Интервалы")), "нет ключа G2"
    import openpyxl
    iv = openpyxl.load_workbook(КНИГА_РАСЧЁТА)["Интервалы"]
    assert iv["G2"].number_format == "0", f"формат ключа «Интервалов»: {iv['G2'].number_format}"


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
