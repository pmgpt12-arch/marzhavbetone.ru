#!/usr/bin/env python3
"""Case package: живая история спора, собранная только из подтверждённых фактов.

«Маржа в бетоне» делает не юридические справки, а документальные истории:
деньги зависли, КС-2 подписан, объект стоит, кассовый разрыв давит.
Читатель должен узнать свою ситуацию, а не прочитать пересказ определения.
Отсюда две вещи, которые тянут в разные стороны, и обе обязательны.

**Текст живой.** В повествовании — стороны, объект, суммы, даты,
документы, поворотная точка и развязка. Номера дела и процессуального
жаргона в нём нет: они уезжают в технический блок внизу, где их ищет тот,
кому нужна ссылка, а не тот, у кого не платят за КС-2.

**Текст не выдуман.** Каждый факт с именем, числом, датой или исходом
привязан в манифесте к дословному фрагменту первичного источника. Гейт
детерминированный: он не рассуждает о праве и не оценивает достоверность —
он сверяет, что названное в тексте названо и в источнике. Чего в манифесте
нет, то в текст не попадает, и это решает не человек.

Почему гейт, а не ручная вычитка: вычитка не масштабируется и молчит о
том, чего не заметила. Гейт молчать не умеет — он называет каждую находку
строкой и роняет сборку.

ЧЕГО ЗДЕСЬ НЕТ. Ни сети, ни очереди публикации Телеграма, ни расписаний,
ни отправки наружу. Модуль пишет два черновика рядом с кейсом и статус;
что с ними делать дальше — решение владельца. Автоматический вызов модели
разрешён только моделью с суффиксом `:free`, и ответ модели проходит тот
же гейт, что и собранный текст: бесплатная модель не имеет права дописать
факт.

КАК ВНЕСТИ НАСТОЯЩИЙ КЕЙС. Ручной шаг владельца, и он единственный.

1. Текст официального акта — в `data/cases/sources/<case_id>.yaml`:

       case_id: <case_id>
       source_kind: official      # только для первичного документа
       source_url: <адрес официального публикатора>
       retrieved_at: '<дата получения>'
       case_number: <номер дела>
       court: <суд>
       text: |
         <текст акта дословно>

2. Факты — в `data/cases/<case_id>.facts.yaml`: на каждый `type`, `value` и
   `quote` — ДОСЛОВНЫЙ фрагмент источника, внутри которого это значение
   стоит. Роли `contract`, `acceptance`, `penalty` фиксируют связки, на
   которых гейт молчит по устройству: числа в неверной связке подтверждены.
3. Прогон: `python3 tools/case_package.py --case <case_id> --write`.

Код 0 и `status: ready_for_owner` — черновики собраны и ждут решения
владельца. Код 1 — сборка заблокирована, и каждая причина названа строкой.

Каталог `data/` в этом репозитории не хранится (`.gitignore`: внутренние
материалы только локально), поэтому кейсы живут у владельца, а образец для
приёмки лежит в самой проверке `tools/test_case_package.py`.

    python3 tools/case_package.py --case <id>
    python3 tools/case_package.py --case <id> --write
    python3 tools/case_package.py --case <id> --json
    python3 tools/case_package.py --case <id> --root <каталог кейсов>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "cases"
DRAFTS = DATA / "drafts"

# Классы источника. Официальным считается только судебный акт или иной
# первичный документ, внесённый владельцем вручную; образец приёмки таким
# не является и к владельцу не выпускается.
OFFICIAL = "official"
FIXTURE = "fixture_sample"

READY = "ready_for_owner"
BLOCKED = "blocked"

# Граница между историей и техническим блоком. Всё, что ниже, читает тот,
# кому нужна ссылка на источник.
TECH_MARK = "## Источник"

CASE_NUMBER = re.compile(r"[АA]\d{2}-\d+/\d{4}")

# Что считается проверяемым утверждением. Каждая находка обязана совпасть
# со значением факта из манифеста — иначе она выдумана.
ПРОВЕРЯЕМОЕ = [
    re.compile(r"(?:ООО|АО|ПАО|ЗАО|ИП)\s+«[^»]+»"),
    re.compile(r"\d{1,2}\.\d{2}\.\d{4}"),
    re.compile(r"\d[\d\s ]*(?:рублей|рубля|руб\.|₽)"),
    re.compile(r"\d+(?:[.,]\d+)?\s*%"),
    re.compile(r"\d+\s+(?:рабочих\s+)?(?:дней|дня|день|недель|месяцев|месяца)"),
]

# Выдумка, которой в судебном акте быть не может: мотивы, кулуары, слухи,
# чувства. Список закрытый и короткий — он ловит жанр, а не слова.
#
# «Мотив» здесь только как побуждение и только целым словом. Прежняя
# редакция ловила `мотив\w*`, а значит и «мотивированный отказ» — термин
# приёмки, который в такой истории стоит по делу. Найдено собственным
# прогоном: гейт краснел на своём же черновике.
ВЫДУМКА = re.compile(
    r"(?:назло|в\s+кулуарах|по\s+слухам|якобы"
    r"|\bмотив(?:ы|а|ов|у|ом|е|ам|ами|ах)?\b"
    r"|решил\w*\s+не\s+плат\w*|хотел\w*\s+(?:обман|проучить)\w*"
    r"|разозл\w*|переживал\w*|призна\w*ся|втайне|на\s+самом\s+деле\s+хотел)",
    re.IGNORECASE)

# Процессуальный язык. В истории ему не место: подрядчик читает про свои
# деньги, а не про стадии процесса.
ЖАРГОН = re.compile(
    r"(?:резолютивн\w+\s+часть|мотивировочн\w+\s+часть|исков\w+\s+заявлени\w*"
    r"|апелляционн\w+\s+жалоб\w*|кассационн\w+\s+жалоб\w*"
    r"|\bистец\w*|\bответчик\w*|в\s+порядке\s+ст\.)",
    re.IGNORECASE)


def _norm(text: str) -> str:
    """Схлопывает пробелы: перенос строки в акте ничего не меняет."""
    return re.sub(r"[\s ]+", " ", str(text or "")).strip()


def source_hash(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


# ── Чтение и запись ─────────────────────────────────────────────────────

def source_path(case_id: str, root: Path = DATA) -> Path:
    return Path(root) / "sources" / f"{case_id}.yaml"


def manifest_path(case_id: str, root: Path = DATA) -> Path:
    return Path(root) / f"{case_id}.facts.yaml"


def load_source(case_id: str, root: Path = DATA) -> dict:
    return yaml.safe_load(source_path(case_id, root).read_text(encoding="utf-8"))


def load_manifest(case_id: str, root: Path = DATA) -> dict:
    return yaml.safe_load(manifest_path(case_id, root).read_text(encoding="utf-8"))


def save_source(source: dict, root: Path) -> Path:
    path = source_path(source["case_id"], root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(source, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")
    return path


def save_manifest(manifest: dict, root: Path) -> Path:
    path = manifest_path(manifest["case_id"], root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")
    return path


# ── Source gate, часть первая: факт против источника ────────────────────

def check_manifest(source: dict, manifest: dict) -> list[str]:
    """Каждый факт обязан лежать во фрагменте, а фрагмент — в источнике."""
    беды: list[str] = []
    текст = _norm(source.get("text"))
    for факт in manifest.get("facts") or []:
        имя = факт.get("id") or "без имени"
        фрагмент = _norm(факт.get("quote"))
        значение = _norm(факт.get("value"))
        if not фрагмент:
            беды.append(f"{имя}: нет фрагмента источника")
            continue
        if фрагмент not in текст:
            беды.append(f"{имя}: фрагмент не найден в источнике дословно")
            continue
        if значение and значение not in фрагмент:
            беды.append(f"{имя}: значение «{значение}» вне своего фрагмента")
    return беды


# ── Source gate, часть вторая: текст против манифеста ───────────────────

def narrative_part(text: str) -> str:
    """История без технического блока: по неё и предъявляются требования."""
    голова, _, _ = str(text or "").partition(TECH_MARK)
    return голова


def _подтверждённые(manifest: dict) -> list[str]:
    значения = []
    for факт in manifest.get("facts") or []:
        значения.append(_norm(факт.get("value")))
        значения.append(_norm(факт.get("quote")))
    return [з for з in значения if з]


def _без_повторов(беды: list[str]) -> list[str]:
    """Одна и та же находка, названная дважды, только удлиняет отчёт."""
    видели, итог = set(), []
    for беда in беды:
        if беда not in видели:
            видели.add(беда)
            итог.append(беда)
    return итог


def audit_facts(text: str, manifest: dict) -> list[str]:
    """Конкретика текста против манифеста — по ВСЕМУ тексту, не по истории.

    Сверяется не смысл, а то, что читатель примет за факт: организация,
    дата, сумма, процент, срок. Граница технического блока здесь не
    действует, и это найдено собственным прогоном: модель дописала
    выдуманную сумму ПОСЛЕ блока источника, и проверка, смотревшая только
    повествование, её не увидела. Дописанное внизу читается так же, как
    дописанное вверху.
    """
    беды: list[str] = []
    проза = _norm(text)
    подтверждённое = _подтверждённые(manifest)

    for выражение in ПРОВЕРЯЕМОЕ:
        for найдено in выражение.finditer(проза):
            кусок = _norm(найдено.group(0))
            if not any(кусок in значение for значение in подтверждённое):
                беды.append(f"не подтверждено манифестом: «{кусок}»")

    for найдено in ВЫДУМКА.finditer(проза):
        беды.append(f"выдуманный мотив или закулисье: «{найдено.group(0)}»")
    return _без_повторов(беды)


def audit_style(text: str) -> list[str]:
    """Жаргон и номер дела. Спрашивается только с истории, не с блока источника."""
    беды: list[str] = []
    проза = _norm(text)
    for найдено in ЖАРГОН.finditer(проза):
        беды.append(f"процессуальный жаргон в истории: «{найдено.group(0)}»")
    if CASE_NUMBER.search(проза):
        беды.append("номер дела в повествовании — ему место в техническом блоке")
    return _без_повторов(беды)


def audit_narrative(text: str, manifest: dict) -> list[str]:
    """Обе стороны разом: для куска истории, который проверяют целиком."""
    return _без_повторов(audit_facts(text, manifest) + audit_style(text))


# ── Сборка черновиков ───────────────────────────────────────────────────

def _факты(manifest: dict, тип: str) -> list[str]:
    return [_norm(f.get("value")) for f in manifest.get("facts") or []
            if f.get("type") == тип and _norm(f.get("value"))]


def _первый(manifest: dict, тип: str, умолчание: str = "") -> str:
    значения = _факты(manifest, тип)
    return значения[0] if значения else умолчание


def _по_роли(manifest: dict, роль: str, умолчание: str = "") -> str:
    """Документ выбирается ролью, а не порядком в списке.

    Найдено глазами на своём же черновике: строка о приёмке подставляла
    договор вместо КС-2, и гейт молчал — все числа и названия были
    подтверждены, неверной была связка. Роль эту связку и фиксирует.
    """
    for факт in manifest.get("facts") or []:
        if факт.get("role") == роль and _norm(факт.get("value")):
            return _norm(факт["value"])
    return умолчание


def build_article(source: dict, manifest: dict) -> str:
    """История из фактов: кто, что подписал, где встали деньги, чем кончилось."""
    подрядчик, заказчик = (_факты(manifest, "party") + ["", ""])[:2]
    объект = _первый(manifest, "object")
    договор = _по_роли(manifest, "contract", _первый(manifest, "document"))
    приёмка = _по_роли(manifest, "acceptance")
    неустойка = _по_роли(manifest, "penalty")
    срок = _первый(manifest, "term")
    суммы = _факты(manifest, "amount")
    даты = _факты(manifest, "date")
    позиция = _первый(manifest, "position")
    перелом = _первый(manifest, "turning_point")
    исходы = _факты(manifest, "outcome")

    строки = [
        f"# Деньги встали после подписания КС-2: {объект}" if объект
        else "# Деньги встали после подписания КС-2",
        "",
        f"{подрядчик} работал на объекте «{объект}» по документу: {договор}."
        if объект and договор else f"{подрядчик} работал по документу: {договор}.",
        "",
        "## Как встали деньги",
        "",
    ]
    if даты:
        строки.append(f"Работы приняты {даты[0]}: {приёмка or договор} "
                      f"подписан без замечаний со стороны {заказчик}.")
    if суммы:
        строки.append(f"Стоимость принятых работ — {суммы[0]}.")
    if срок:
        строки.append(f"Срок оплаты по договору — {срок}. Деньги в этот срок "
                      "не поступили.")
    if len(даты) > 1:
        строки.append(f"Претензия {даты[1]} осталась без ответа.")
    if позиция:
        строки.append(f"Позиция другой стороны: {позиция}.")
    строки += ["", "## Что изменило исход", ""]
    if перелом:
        строки.append(f"Поворотная точка одна: {перелом}.")
    строки += ["", "## Чем кончилось", ""]
    for исход in исходы:
        строки.append(f"- {исход}.")
    if неустойка:
        строки.append(f"- дополнительно — {неустойка}.")
    строки += [
        "",
        "## Что проверить у себя",
        "",
        "- сверьте дату подписания актов и срок оплаты по своему договору;",
        "- проверьте, направляла ли вторая сторона мотивированный отказ в срок;",
        "- сохраните переписку о приёмке: возражения после подписания читаются иначе;",
        "- посчитайте, с какого дня у вас начинается просрочка оплаты.",
        "",
        TECH_MARK,
        "",
        f"- материал: {source.get('court', 'первичный документ')}, "
        f"дело № {source.get('case_number', 'не указано')};",
        f"- класс источника: {source.get('source_kind')};",
        f"- адрес: {source.get('source_url') or 'внесён вручную, адрес не указан'};",
        f"- дата получения: {source.get('retrieved_at', 'не указана')};",
        f"- sha256 текста источника: {source_hash(source.get('text', ''))};",
        "- каждый факт истории привязан к фрагменту источника в манифесте "
        f"`data/cases/{manifest.get('case_id')}.facts.yaml`.",
    ]
    if source.get("source_note"):
        строки.append(f"- примечание: {source['source_note']}")
    return "\n".join(строки).strip() + "\n"


def build_telegram(source: dict, manifest: dict) -> str:
    """Короткая версия: ставка, перелом, развязка, один вопрос читателю."""
    подрядчик, заказчик = (_факты(manifest, "party") + ["", ""])[:2]
    суммы = _факты(manifest, "amount")
    даты = _факты(manifest, "date")
    перелом = _первый(manifest, "turning_point")
    исход = _первый(manifest, "outcome")

    строки = [f"{подрядчик} сдал работы {даты[0] if даты else ''} — и не получил денег."
              .replace("  ", " ")]
    if суммы:
        строки.append(f"На счету зависло {суммы[0]}.")
    if заказчик:
        строки.append(f"Вторая сторона — {заказчик}.")
    if перелом:
        строки.append(f"Что решило дело: {перелом}.")
    if исход:
        строки.append(f"Итог: {исход}.")
    строки.append("Проверьте у себя: с какого дня по договору начинается "
                  "просрочка оплаты и был ли мотивированный отказ в срок.")
    return "\n\n".join(строки).strip() + "\n"


# ── Сборка пакета ───────────────────────────────────────────────────────

def build(case_id: str, *, root: Path = DATA, out_dir: Path | None = None,
          write: bool = False, generate: Callable[..., str] | None = None,
          model: str | None = None) -> dict:
    """Источник и манифест → два черновика, список бед и статус.

    Статус `ready_for_owner` выдаётся только когда бед нет вовсе и источник
    официальный. Любая находка гейта оставляет `blocked` — и называет себя.
    """
    источник = load_source(case_id, root)
    манифест = load_manifest(case_id, root)

    беды: list[str] = list(check_manifest(источник, манифест))

    статья = build_article(источник, манифест)
    пост = build_telegram(источник, манифест)

    if generate is not None:
        имя = str(model or "")
        if not имя.endswith(":free"):
            беды.append(f"генератор остановлен: модель «{имя or 'не названа'}» "
                        "без суффикса :free")
        else:
            статья = str(generate(статья, model=имя) or "")

    # Факты спрашиваются с текста целиком, стиль — только с истории:
    # технический блок обязан называть номер дела, а дописанная внизу
    # сумма — такая же выдумка, как дописанная в первом абзаце.
    for название, текст in (("статья", статья), ("телеграм", пост)):
        for беда in audit_facts(текст, манифест):
            беды.append(f"{название}: {беда}")
        for беда in audit_style(narrative_part(текст)):
            беды.append(f"{название}: {беда}")

    класс = источник.get("source_kind")
    if класс != OFFICIAL:
        беды.append(f"источник не официальный ({класс}): к владельцу такой "
                    "случай не выпускается")

    пакет = {
        "case_id": case_id,
        "status": READY if not беды else BLOCKED,
        "source_kind": класс,
        "source_sha256": source_hash(источник.get("text", "")),
        "facts": len(манифест.get("facts") or []),
        "problems": беды,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "drafts": {"article": статья, "telegram": пост},
    }

    if write:
        куда = Path(out_dir or DRAFTS) / case_id
        куда.mkdir(parents=True, exist_ok=True)
        (куда / "article.md").write_text(статья, encoding="utf-8")
        (куда / "telegram.md").write_text(пост, encoding="utf-8")
        сводка = {k: v for k, v in пакет.items() if k != "drafts"}
        сводка["drafts"] = {"article": "article.md", "telegram": "telegram.md"}
        (куда / "package.yaml").write_text(
            yaml.safe_dump(сводка, allow_unicode=True, sort_keys=False),
            encoding="utf-8")
        пакет["written_to"] = str(куда)
    return пакет


def main(argv=None) -> int:
    разбор = argparse.ArgumentParser(
        description="Case package: черновики из подтверждённых фактов. Без сети.")
    разбор.add_argument("--case", required=True, help="идентификатор кейса")
    разбор.add_argument("--write", action="store_true",
                        help="записать черновики рядом с кейсом")
    разбор.add_argument("--json", action="store_true", help="машинный вывод")
    разбор.add_argument("--root", type=Path, default=DATA,
                        help="каталог кейсов; по умолчанию data/cases")
    аргументы = разбор.parse_args(argv)

    пакет = build(аргументы.case, root=аргументы.root, write=аргументы.write,
                  out_dir=аргументы.root / "drafts")
    if аргументы.json:
        print(json.dumps({k: v for k, v in пакет.items() if k != "drafts"},
                         ensure_ascii=False, indent=2))
    else:
        print(f"case: {пакет['case_id']}")
        print(f"источник: {пакет['source_kind']}, sha256 {пакет['source_sha256'][:12]}")
        print(f"фактов в манифесте: {пакет['facts']}")
        for беда in пакет["problems"]:
            print(f"  блокировка: {беда}")
        print(f"status: {пакет['status']}")
    return 0 if пакет["status"] == READY else 1


if __name__ == "__main__":
    sys.exit(main())
