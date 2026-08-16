#!/usr/bin/env python3
"""Перенос вердикта на новую версию файла, когда правка юридически пуста.

Зачем. Гейт привязывает результат сверки к смысловому хешу документа, и это
верно: изменённый документ не должен ехать со вчерашним вердиктом. Но хеш
меняется и от правки, в которой нет ни одной нормы, — 16.08.2026 в файле
расчёта поменялась одна строка, дата собственной сверки во врезке, и это
стоило бы полного захода проверяющего. Заход по такой правке — расход без
предмета: сверять нечего.

Что здесь есть. Узкий механизм: объявленный в `data/legal/rebinds.yaml`
перенос вердикта со старой версии на новую, допустимый **только** если
правка доказанно не трогает право. Доказательство даётся не суждением, а
равенством: из нового текста подставляется обратно старый токен, и
результат обязан совпасть со старым текстом **побайтно**. Любая другая
правка — слово, цифра, формула, порядок пункта — равенство ломает.

Одного равенства мало: подобрав достаточно широкий токен, через него можно
протащить смысл («не подлежат» → «подлежат»). Поэтому вид токена задан
списком, и сегодня в списке ровно один вид — `date`, календарная дата в
предложении о сверке. Неизвестный вид — отказ, а не разрешение.

Механизм намеренно не общий. Он не «умеет отличать юридические правки от
неюридических»: он умеет одно узкое, проверяемое утверждение и на всё
остальное отвечает отказом.

    python3 tools/legal_rebind.py            # показать, что будет сделано
    python3 tools/legal_rebind.py --write    # перенести вердикты в реестр
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_legal_coverage import ссылки, текст  # noqa: E402
from semantic_hash import semantic_hash  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEGAL = ROOT / "data" / "legal"
REBINDS = LEGAL / "rebinds.yaml"
RESULTS = LEGAL / "normative-results.yaml"

# Календарная дата и ничего кроме неё: токен не должен нести предложения.
_ДАТА = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")

# Дата допустима к переносу, только когда речь о дате нашей же сверки.
# Дата срока, дата акта, дата договора под механизм не попадают.
_КОНТЕКСТ_СВЕРКИ = ("сверен", "сверка", "сверки")
_ОКНО = 160


def _даты_совпадают(было: str, стало: str) -> tuple[bool, str]:
    if not _ДАТА.fullmatch(было) or not _ДАТА.fullmatch(стало):
        return False, "токен не календарная дата — перенос запрещён"
    return True, ""


ВИДЫ = {"date": _даты_совпадают}


def в_контексте_сверки(текст_документа: str, токен: str) -> bool:
    """Каждое вхождение токена окружено словом о сверке."""
    места = [m.start() for m in re.finditer(re.escape(токен), текст_документа)]
    if not места:
        return False
    for i in места:
        окно = текст_документа[max(0, i - _ОКНО):i + _ОКНО].lower()
        if not any(с in окно for с in _КОНТЕКСТ_СВЕРКИ):
            return False
    return True


def перенос_допустим(старый: str, новый: str, было: str, стало: str,
                     вид: str = "date") -> tuple[bool, str]:
    """Чистая функция: можно ли перенести вердикт со старого текста на новый.

    Сети, файлов и состояния не требует — поэтому проверяема примерами.
    """
    if вид not in ВИДЫ:
        return False, f"вид правки «{вид}» механизмом не поддержан"
    if not было or not стало or было == стало:
        return False, "пара токенов пуста или совпадает"
    годен, почему = ВИДЫ[вид](было, стало)
    if not годен:
        return False, почему
    if "=" in было or "=" in стало:
        return False, "токен похож на формулу"
    if ссылки(было) or ссылки(стало):
        return False, "токен содержит правовую ссылку"
    if ссылки(старый) != ссылки(новый):
        появились = sorted(ссылки(новый) - ссылки(старый))
        исчезли = sorted(ссылки(старый) - ссылки(новый))
        return False, ("набор правовых ссылок изменился: "
                       f"+{появились} −{исчезли}")
    if not в_контексте_сверки(новый, стало):
        return False, "дата стоит не в предложении о сверке"
    сколько_было = старый.count(было)
    сколько_стало = новый.count(стало)
    if сколько_было == 0 or сколько_было != сколько_стало:
        return False, (f"токен встречается {сколько_было} раз в старом тексте "
                       f"и {сколько_стало} в новом")
    if новый.replace(стало, было) != старый:
        return False, ("после подстановки старого токена тексты не совпали — "
                       "правка не сводится к объявленной")
    return True, "правка сводится к объявленному токену и права не касается"


def _старый_текст(path: str, ref: str) -> str:
    """Прежняя версия файла берётся из истории, а не со слов."""
    blob = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout
    with tempfile.NamedTemporaryFile(suffix=Path(path).suffix,
                                     delete=False) as f:
        f.write(blob)
        tmp = Path(f.name)
    try:
        return текст(tmp), semantic_hash(tmp)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true",
                    help="перенести вердикты в normative-results.yaml")
    args = ap.parse_args()

    if not REBINDS.exists():
        print("Объявленных переносов нет.")
        return 0
    записи = yaml.safe_load(REBINDS.read_text(encoding="utf-8")) or {}
    записи = записи.get("rebinds") or []
    if not записи:
        print("Объявленных переносов нет.")
        return 0

    data = yaml.safe_load(RESULTS.read_text(encoding="utf-8"))
    результаты = {r["document"]: r for r in data["results"]}

    отказов = 0
    к_записи: list[tuple[dict, dict]] = []
    for з in записи:
        имя = з["document"].split("/")[-1]
        result = результаты.get(з["document"])
        if result is None:
            print(f"  ✗ {имя}: документа нет в реестре результатов")
            отказов += 1
            continue

        старый, хеш_старого = _старый_текст(з["document"], з["from_ref"])
        новый = текст(ROOT / з["document"])
        хеш_нового = semantic_hash(ROOT / з["document"])

        # Оба конца перехода обязаны быть теми, что объявлены. Иначе перенос
        # описывает не ту правку, которая на самом деле произошла.
        if хеш_старого != з["from_hash"]:
            print(f"  ✗ {имя}: версия {з['from_ref']} даёт {хеш_старого[7:19]}, "
                  f"объявлено {з['from_hash'][7:19]}")
            отказов += 1
            continue
        if хеш_нового != з["to_hash"]:
            print(f"  ✗ {имя}: текущая версия {хеш_нового[7:19]}, "
                  f"объявлено {з['to_hash'][7:19]}")
            отказов += 1
            continue
        if result.get("document_hash") != з["from_hash"]:
            print(f"  ✗ {имя}: в реестре стоит "
                  f"{str(result.get('document_hash'))[7:19]}, "
                  f"перенос объявлен с {з['from_hash'][7:19]}")
            отказов += 1
            continue

        можно, почему = перенос_допустим(старый, новый, з["token_before"],
                                         з["token_after"], з.get("kind", ""))
        if not можно:
            print(f"  ✗ {имя}: {почему}")
            отказов += 1
            continue
        print(f"  ✓ {имя}: {почему}")
        print(f"      {з['from_hash'][7:19]} → {з['to_hash'][7:19]}, "
              f"вердикт {result['verdict']} переносится")
        к_записи.append((з, result))

    if отказов:
        print(f"\nПереносов отклонено: {отказов}. Такая правка закрывается "
              "заходом проверяющего, а не переносом.")
        return 1

    if not args.write:
        print("\nПоказ. Записать — с ключом --write.")
        return 0

    for з, result in к_записи:
        result["document_hash"] = з["to_hash"]
        result.setdefault("rebinds", []).append({
            "from_hash": з["from_hash"],
            "from_ref": з["from_ref"],
            "kind": з.get("kind"),
            "token_before": з["token_before"],
            "token_after": з["token_after"],
            "reason": з["reason"],
            "verified_by": "tools/legal_rebind.py",
            "at": з["at"],
        })
    head = RESULTS.read_text(encoding="utf-8").split("\nmeta:")[0]
    RESULTS.write_text(
        head + "\n" + yaml.dump(data, allow_unicode=True, sort_keys=False,
                                default_flow_style=False, width=100),
        encoding="utf-8")
    print(f"\nПеренесено вердиктов: {len(к_записи)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
