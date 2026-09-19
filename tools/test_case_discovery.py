#!/usr/bin/env python3
"""Приёмка Discovery: сигналы для семантического ядра, а не факты статьи.

Discovery-запись — формулировка боли, тема, угол подачи, поисковый запрос
или продуктовая гипотеза. Она собирается руками из форумов, вопросов,
отраслевых лент и чужих блогов, и ни одно её слово не становится
утверждением материала: источник факта у «Маржи в бетоне» — первичный
документ, и его проверяет `case_package`, отдельный контур.

Отсюда две стороны приёмки:

  · **структура строгая** — обязательные поля есть, невалидная запись
    названа и отброшена, точный дубль по нормализованному `text + topic`
    не удваивает словарь;
  · **смысла в записи не ищется** — юридической, нормативной и ценовой
    проверки здесь нет по устройству, и `sudact.ru` как источник сигнала
    допустим ровно так же, как форум.

Слипание близких формулировок для семантического ядра хуже пропуска:
«денег нет четыре месяца» и «денег нет второй месяц» — две разные боли, и
частота обеих нужна как есть.

Запуск без pytest: python3 tools/test_case_discovery.py
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import case_discovery as поиск                                     # noqa: E402

# Ожидаемые значения записаны здесь, а не прочитаны из проверяемого модуля:
# проверка, берущая ожидаемое из проверяемого, согласится с любой подменой.
ТИПЫ = ("forum", "qa", "industry_media", "law_firm_blog", "competitor",
        "official_index", "manual")
ОБЯЗАТЕЛЬНЫЕ = ("text", "topic", "source_type", "found_at", "tags")

# Фикстура лежит здесь, а не в `data/`: каталог в этом репозитории намеренно
# в .gitignore («внутренние материалы только локально»), и проверка,
# зависящая от него, в CI не пошла бы вовсе.
СИГНАЛЫ = [
    {
        "id": "pain-ks2-no-payment-001",
        "text": "КС-2 подписан, денег нет четыре месяца",
        "topic": "неоплата после приёмки",
        "source_url": "https://example.invalid/thread/1",
        "source_type": "forum",
        "found_at": "2026-09-19",
        "tags": ["кс-2", "неоплата", "подрядчик"],
        "possible_content_angle": "что фиксировать после подписания КС-2",
        "possible_case_query": "КС-2 подписан оплата не поступила арбитраж",
    },
    {
        "id": "pain-ks2-no-payment-002",
        "text": "  КС-2   ПОДПИСАН, денег нет четыре месяца ",
        "topic": "Неоплата после приёмки",
        "source_url": "https://example.invalid/thread/77",
        "source_type": "qa",
        "found_at": "2026-09-19",
        "tags": ["кс-2", "неоплата"],
    },
    {
        "id": "pain-ks2-no-payment-003",
        "text": "КС-2 подписан, денег нет второй месяц",
        "topic": "неоплата после приёмки",
        "source_type": "forum",
        "found_at": "2026-09-18",
        "tags": ["кс-2", "неоплата"],
        "possible_case_query": "взыскание долга по КС-2 подряд",
    },
    {
        "id": "pain-otkaz-001",
        "text": "заказчик тянет с подписанием, мотивированный отказ не шлёт",
        "topic": "затянутая приёмка",
        "source_url": "https://sudact.ru/arbitral/doc/00000000/",
        "source_type": "official_index",
        "found_at": "2026-09-17",
        "tags": ["приёмка", "мотивированный отказ"],
        "possible_content_angle": "срок на мотивированный отказ",
        "possible_product_idea": "чек-лист приёмки для подрядчика",
    },
    {
        "id": "pain-uderzhanie-001",
        "text": "гарантийное удержание не вернули после года",
        "topic": "гарантийное удержание",
        "source_type": "manual",
        "found_at": "2026-09-16",
        "tags": ["удержание", "подрядчик"],
        "possible_product_idea": "шаблон письма о возврате удержания",
    },
]

БЕЗ_ТЕМЫ = {
    "id": "broken-001",
    "text": "смета не согласована, работы идут",
    "source_type": "forum",
    "found_at": "2026-09-19",
    "tags": ["смета"],
}


def записать(каталог: Path, записи: list[dict], имя: str = "signals.jsonl") -> Path:
    путь = каталог / имя
    путь.write_text("\n".join(json.dumps(з, ensure_ascii=False) for з in записи) + "\n",
                    encoding="utf-8")
    return путь


def импорт(записи: list[dict]) -> dict:
    with tempfile.TemporaryDirectory() as каталог:
        return поиск.load_signals(записать(Path(каталог), записи))


# ── Импорт и структура ──────────────────────────────────────────────────

def test_валидный_сигнал_импортируется() -> None:
    итог = импорт([СИГНАЛЫ[0]])
    assert len(итог["signals"]) == 1, итог
    assert not итог["invalid"], итог
    сигнал = итог["signals"][0]
    assert сигнал["text"] == "КС-2 подписан, денег нет четыре месяца"
    assert сигнал["topic"] == "неоплата после приёмки"
    assert сигнал["tags"] == ["кс-2", "неоплата", "подрядчик"]


def test_сигнал_без_обязательного_поля_блокируется() -> None:
    """Каждое обязательное поле проверено по отдельности, а не списком.

    Проверка «одного не хватает — упало» зелена и при том, что модуль
    смотрит ровно одно поле из пяти.
    """
    for поле in ОБЯЗАТЕЛЬНЫЕ:
        калека = {k: v for k, v in СИГНАЛЫ[0].items() if k != поле}
        итог = импорт([калека])
        assert not итог["signals"], f"{поле}: запись прошла"
        assert итог["invalid"], f"{поле}: запись не названа невалидной"
        assert поле in итог["invalid"][0]["problems"][0], итог["invalid"]


def test_запись_без_ссылки_проходит() -> None:
    """У ручной заметки источника-адреса нет, и это не дефект."""
    итог = импорт([СИГНАЛЫ[4]])
    assert len(итог["signals"]) == 1, итог
    assert итог["signals"][0].get("source_url", "") == ""


def test_неизвестный_тип_источника_блокируется() -> None:
    чужой = dict(СИГНАЛЫ[0], source_type="telegram_channel")
    итог = импорт([чужой])
    assert not итог["signals"], итог
    assert any("source_type" in b for b in итог["invalid"][0]["problems"]), итог


def test_все_объявленные_типы_принимаются() -> None:
    for тип in ТИПЫ:
        итог = импорт([dict(СИГНАЛЫ[0], source_type=тип)])
        assert len(итог["signals"]) == 1, тип


def test_битая_строка_jsonl_названа_а_не_роняет_прогон() -> None:
    with tempfile.TemporaryDirectory() as каталог:
        путь = Path(каталог) / "signals.jsonl"
        путь.write_text(json.dumps(СИГНАЛЫ[0], ensure_ascii=False) + "\n"
                        + "{это не json}\n", encoding="utf-8")
        итог = поиск.load_signals(путь)
    assert len(итог["signals"]) == 1, итог
    assert итог["invalid"], итог
    assert any("строк" in b.lower() or "json" in b.lower()
               for b in итог["invalid"][0]["problems"]), итог


# ── Дубли ───────────────────────────────────────────────────────────────

def test_точный_дубль_не_удваивает_словарь() -> None:
    """Регистр, лишние пробелы и другой адрес дубля не отменяют."""
    итог = импорт([СИГНАЛЫ[0], СИГНАЛЫ[1]])
    assert len(итог["signals"]) == 1, итог
    assert len(итог["duplicates"]) == 1, итог
    assert итог["duplicates"][0]["id"] == "pain-ks2-no-payment-002", итог


def test_близкие_формулировки_не_склеиваются() -> None:
    """Четыре месяца и второй месяц — две боли, и частота нужна у обеих."""
    итог = импорт([СИГНАЛЫ[0], СИГНАЛЫ[2]])
    assert len(итог["signals"]) == 2, итог
    assert not итог["duplicates"], итог


def test_одна_формулировка_в_разных_темах_не_дубль() -> None:
    другая = dict(СИГНАЛЫ[0], id="pain-x", topic="другая тема")
    итог = импорт([СИГНАЛЫ[0], другая])
    assert len(итог["signals"]) == 2, итог


# ── Отчёт ───────────────────────────────────────────────────────────────

def test_отчёт_считает_темы_и_теги() -> None:
    итог = импорт(СИГНАЛЫ)
    отчёт = поиск.build_report(итог)

    assert отчёт["signals"] == 4, отчёт          # пятая запись — точный дубль
    assert отчёт["duplicates"] == 1, отчёт
    assert отчёт["invalid"] == 0, отчёт
    assert dict(отчёт["topics"])["неоплата после приёмки"] == 2, отчёт
    теги = dict(отчёт["tags"])
    assert теги["кс-2"] == 2 and теги["неоплата"] == 2, отчёт
    assert теги["подрядчик"] == 2, отчёт


def test_отчёт_называет_повторяющуюся_боль() -> None:
    итог = импорт(СИГНАЛЫ)
    отчёт = поиск.build_report(итог)
    боли = dict(отчёт["pains"])
    assert боли["неоплата после приёмки"] == 2, отчёт
    # Одиночная боль тоже в отчёте: частота 1 — это сигнал, а не шум.
    assert "гарантийное удержание" in боли, отчёт


def test_отчёт_собирает_углы_запросы_и_гипотезы() -> None:
    итог = импорт(СИГНАЛЫ)
    отчёт = поиск.build_report(итог)
    assert "что фиксировать после подписания КС-2" in отчёт["angles"], отчёт
    assert "КС-2 подписан оплата не поступила арбитраж" in отчёт["queries"], отчёт
    assert "чек-лист приёмки для подрядчика" in отчёт["product_ideas"], отчёт
    assert len(отчёт["product_ideas"]) == 2, отчёт


def test_отчёт_держит_блок_дублей_и_невалидных_отдельно() -> None:
    итог = импорт(СИГНАЛЫ + [БЕЗ_ТЕМЫ])
    отчёт = поиск.build_report(итог)
    assert отчёт["invalid"] == 1, отчёт
    assert отчёт["duplicates"] == 1, отчёт
    # Невалидная запись в частоты не попала.
    assert "смета" not in dict(отчёт["tags"]), отчёт


def test_отчёт_называет_десять_тем_в_работу() -> None:
    итог = импорт(СИГНАЛЫ)
    отчёт = поиск.build_report(итог)
    assert len(отчёт["take_next"]) <= 10, отчёт
    assert отчёт["take_next"], отчёт
    первая = отчёт["take_next"][0]
    assert первая["topic"] == "неоплата после приёмки", отчёт
    assert первая["signals"] == 2, отчёт


def test_текстовый_отчёт_читается_владельцем() -> None:
    итог = импорт(СИГНАЛЫ)
    текст = поиск.render_report(поиск.build_report(итог))
    for кусок in ("Сигналов", "Что чаще всего болит", "Взять в работу",
                  "Дубли", "неоплата после приёмки"):
        assert кусок in текст, текст


def test_json_вывод_стабилен() -> None:
    """Один и тот же ввод даёт байт в байт тот же JSON.

    Нестабильный вывод нельзя ни сравнить с прошлой неделей, ни положить
    в проверку: порядок словаря и время прогона в него не попадают.
    """
    with tempfile.TemporaryDirectory() as каталог:
        путь = записать(Path(каталог), СИГНАЛЫ)
        первый = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "case_discovery.py"),
             "report", "--input", str(путь), "--json"],
            capture_output=True, text=True, cwd=ROOT, timeout=120)
        второй = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "case_discovery.py"),
             "report", "--input", str(путь), "--json"],
            capture_output=True, text=True, cwd=ROOT, timeout=120)

    assert первый.returncode == 0, первый.stdout + первый.stderr
    assert первый.stdout == второй.stdout, "вывод разошёлся между прогонами"
    разбор = json.loads(первый.stdout)
    assert разбор["signals"] == 4, разбор
    assert json.dumps(разбор, ensure_ascii=False, sort_keys=True) == \
        json.dumps(json.loads(второй.stdout), ensure_ascii=False, sort_keys=True)


def test_порядок_строк_во_вводе_не_меняет_частоты() -> None:
    """Отчёт не зависит от того, в каком порядке владелец дописывал строки.

    Счётчик Python идёт порядком вставки, и без явной сортировки две
    недели с одними и теми же сигналами дают разные списки. Сравнить их
    тогда нельзя — а ради сравнения отчёт и печатается. Прогон двух
    одинаковых вводов эту поломку не ловит: она видна только на
    переставленном.
    """
    прямо = поиск.build_report(импорт(СИГНАЛЫ))
    наоборот = поиск.build_report(импорт(list(reversed(СИГНАЛЫ))))

    assert прямо["topics"] == наоборот["topics"], (прямо["topics"], наоборот["topics"])
    assert прямо["tags"] == наоборот["tags"], (прямо["tags"], наоборот["tags"])
    assert прямо["source_types"] == наоборот["source_types"], прямо["source_types"]
    assert [т["topic"] for т in прямо["take_next"]] == \
        [т["topic"] for т in наоборот["take_next"]], прямо["take_next"]


def test_cli_импорта_называет_дубли_и_невалидные() -> None:
    with tempfile.TemporaryDirectory() as каталог:
        путь = записать(Path(каталог), СИГНАЛЫ + [БЕЗ_ТЕМЫ])
        прогон = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "case_discovery.py"),
             "import", "--input", str(путь)],
            capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert прогон.returncode == 0, прогон.stdout + прогон.stderr
    assert "дубл" in прогон.stdout.lower(), прогон.stdout
    assert "topic" in прогон.stdout, прогон.stdout


# ── Границы контура ─────────────────────────────────────────────────────

def test_discovery_не_судит_об_официальности_источника() -> None:
    """sudact.ru — нормальный Discovery-сигнал.

    Первичным официальным источником он в `case_package` не работает, и это
    разные вопросы: там решается, чем подтверждён факт статьи, здесь — о
    чём люди спрашивают. Сигнал не становится фактом ни при каком
    источнике, поэтому и гейта источника тут нет.
    """
    итог = импорт([СИГНАЛЫ[3]])
    assert len(итог["signals"]) == 1, итог
    assert итог["signals"][0]["source_url"].startswith("https://sudact.ru/")

    # Слов вердикта о статусе источника модуль не произносит вовсе.
    исходник = (ROOT / "tools" / "case_discovery.py").read_text(encoding="utf-8")
    for слово in ("ready_for_owner", "official_publisher", "ПУБЛИКАТОРЫ",
                  "source_kind"):
        assert слово not in исходник, слово


def test_модуль_не_ходит_в_сеть_и_не_зовёт_публикацию() -> None:
    исходник = (ROOT / "tools" / "case_discovery.py").read_text(encoding="utf-8")
    дерево = ast.parse(исходник)
    импорты = set()
    for узел in ast.walk(дерево):
        if isinstance(узел, ast.Import):
            импорты.update(и.name.split(".")[0] for и in узел.names)
        elif isinstance(узел, ast.ImportFrom) and узел.module:
            импорты.add(узел.module.split(".")[0])

    разрешено = {"argparse", "collections", "json", "re", "sys", "unicodedata",
                 "__future__", "pathlib", "typing", "dataclasses"}
    assert импорты <= разрешено, импорты - разрешено

    # Запрет — на сетевой ВЫЗОВ, не на буквы «http»: адрес-пример в
    # инструкции никуда не ходит, и проверка, краснеющая на нём, ловит
    # документацию вместо поведения. Найдено собственным прогоном.
    for запрет in ("requests.", "urlopen", "urlretrieve", "http.client",
                   "socket.", "httpx", "post_telegram", "content/telegram",
                   "case_package.", "import case_package", "openai",
                   "openrouter", "subprocess", "os.environ", "getenv",
                   "TOKEN", "SECRET"):
        assert запрет not in исходник, запрет

    # И отдельно: ни одного адреса, по которому можно пойти. Пример в
    # докстроке — на зарезервированном .invalid, он не резолвится нигде.
    for адрес in re.findall(r"https?://[^\s\"')]+", исходник):
        assert ".invalid" in адрес, адрес


def test_ничего_не_создано_в_content_telegram_и_data() -> None:
    очередь = ROOT / "content" / "telegram"
    было = sorted(p.name for p in очередь.glob("*")) if очередь.exists() else []
    данные = ROOT / "data"
    было_данных = sorted(p.name for p in данные.glob("*")) if данные.exists() else []

    итог = импорт(СИГНАЛЫ)
    поиск.render_report(поиск.build_report(итог))

    стало = sorted(p.name for p in очередь.glob("*")) if очередь.exists() else []
    стало_данных = sorted(p.name for p in данные.glob("*")) if данные.exists() else []
    assert было == стало, (было, стало)
    assert было_данных == стало_данных, (было_данных, стало_данных)


def test_фикстуры_живут_в_проверке_а_не_в_data() -> None:
    """Сигналы — внутренний материал: в репозиторий они не едут.

    `data/` здесь в .gitignore, поэтому проверка, читающая файл оттуда,
    в CI просто не пошла бы, а положенный туда образец потерялся бы молча.
    """
    свои = (ROOT / "tools" / "test_case_discovery.py").read_text(encoding="utf-8")
    assert "СИГНАЛЫ = [" in свои, "образец не лежит в самой проверке"

    # Проверка не читает `data/` ни одним способом: ни по склейке с ROOT,
    # ни относительным путём. Список строк-запретов тут не годится — он
    # краснел бы на самом себе.
    # Приставка собирается из кусков: записанная строкой, она нашлась бы
    # в этой же проверке и покрасила бы её саму.
    приставка = "da" + "ta" + "/"
    дерево = ast.parse(свои)
    for узел in ast.walk(дерево):
        if isinstance(узел, ast.Constant) and isinstance(узел.value, str):
            assert not узел.value.startswith((приставка, "./" + приставка)), узел.value
    # Про сам `ROOT / "data"` здесь не спрашивается: соседняя проверка
    # заглядывает туда намеренно, чтобы убедиться, что мы ничего не
    # записали. Читать оттуда и сторожить — разные вещи.

    # И в самом репозитории файла сигналов нет: он внутренний.
    данные = ROOT / "data"
    if данные.exists():
        assert not list(данные.rglob("*discovery*")), "образец уехал в data/"


def test_инструкция_называет_три_команды() -> None:
    докстрока = поиск.__doc__ or ""
    for команда in ("import --input", "report --input", "--json"):
        assert команда in докстрока, команда
    # И говорит главное: сигнал не факт.
    assert "не факт" in докстрока.lower() or "не становится фактом" in докстрока.lower()


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {str(e)[:200]}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
