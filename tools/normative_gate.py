#!/usr/bin/env python3
"""Нормативный гейт: изменённый юридический документ не уезжает без сверки.

Что закрывает. Замер 15.08.2026 (задача D-06): шесть документов комплекта
P1 продавались, и нормативной сверки по ним не проводилось ни разу — так и
было записано в двух манифестах, а нашлось это случайно. Ни одна проверка
репозитория про них не знала. Второй дефект того же ряда: отчёт о сверке
был свободным текстом и ни к чему не привязан, поэтому документ можно
изменить завтра и продавать со вчерашним отчётом.

Гейт **не вызывает модель** и не толкует право. Он проверяет ровно одно:
существует ли для текущей версии каждого юридического документа годный
результат сверки. Добывает результат отдельный заход `normative-checker`.
Это разделение вынужденное и названо прямо: гейт объявлен набором без сети
(`.github/workflows/checks.yml`), а правовые порталы из среды закрыты —
модели здесь работать нечем.

Правила, каждое роняет прогон:

  1. файл в покрытой области не объявлен ни в `documents`, ни в
     `out_of_scope` — новый документ не должен пройти молча;
  2. объявленного документа нет на диске;
  3. результата сверки для документа нет;
  4. смысловой хеш документа не совпадает с хешем в результате;
  5. вердикт FAIL или NOT_VERIFIED;
  6. вердикт PASS_WITH_CORRECTIONS без перечита;
  7. `escalation_required` без записи о проверке человеком под этот хеш;
  8. норма, на которую опирается документ, не объявлена в реестре;
  9. доказательство нормы отсутствует, не сходится по хешу, не официально
     или результат привязан к другой её редакции;
 10. в пользовательской точке стоит утверждение о вычитке юристом, а
     записи `human_review` под текущую версию нет.

Про девятое правило отдельно, потому что именно оно красит гейт сегодня.
Вся сверка D-06 прошла на цитатах из поисковой выдачи: официальные
публикаторы из рабочей среды закрыты (`CONNECT tunnel failed, response
403`). Назвать это чтением официальной публикации нельзя, а выдать
вторичному источнику полный PASS значило бы завести ложную зелень —
худшее, что может сделать проверка. Красное исходное состояние выбрано
сознательно.

Свежесть норм (`recheck_after`) здесь **не проверяется**: истёкший срок не
должен ронять посторонний PR по календарю. Этим занимается
`tools/normative_scope.py`, и он сообщает, а не блокирует.

    python3 tools/normative_gate.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_evidence import verify as verify_evidence  # noqa: E402
from semantic_hash import (  # noqa: E402
    UnsupportedType, docx_parts, semantic_hash, xlsx_parts)

ROOT = Path(__file__).resolve().parent.parent
LEGAL = ROOT / "data" / "legal"

# Утверждения о том, что текст смотрел живой юрист. Нормативная сверка
# таким утверждением не является и создать его не может: для него нужно
# отдельное доказательство человеческой проверки конкретной версии.
#
# Ловится именно утверждение, а не всякое упоминание юриста. Разница не
# теоретическая: правильная формулировка, принятая 15.08.2026, сама
# содержит слова «вычиткой юристом она не является», и правило, написанное
# по одному слову «вычитка», краснело бы ровно на верном тексте. Поэтому
# нужен глагол утверждения рядом — «прошли вычитку», «вычитан», «проверен».
LAWYER_CLAIM = re.compile(
    r"(?:прошл\w+|проходил\w*)\s+вычитку\s+юрист"
    r"|вычитан\w*\s+юрист"
    r"|провере\w+\s+юрист"
    r"|юрист\w*\s+(?:провери\w+|вычита\w+)", re.I)

# Отрицание рядом переворачивает смысл: «вычитку юристом не проходили» и
# «не вычитанные юристом» — это не заявление о проверке.
NEGATION = re.compile(r"\bне\b|\bнет\b|молч\w+|снят\w+", re.I)


def asserts_lawyer_review(text: str) -> str | None:
    """Первое утверждение о вычитке, не снятое отрицанием рядом."""
    for m in LAWYER_CLAIM.finditer(text):
        window = text[max(0, m.start() - 40):m.end() + 40]
        if NEGATION.search(window):
            continue
        return m.group(0)
    return None

ACCEPTABLE = {"PASS", "PASS_WITH_CORRECTIONS"}


def load(name: str) -> dict:
    path = LEGAL / name
    if not path.exists():
        raise SystemExit(f"нет файла {path.relative_to(ROOT)} — гейт не настроен")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def visible_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def check() -> list[str]:
    mapping = load("document-norms.yaml")
    norms = {n["norm_id"]: n for n in load("norms.yaml").get("norms", [])}
    results = {r["document"]: r for r in load("normative-results.yaml").get("results", [])}
    human = {h["document"]: h for h in
             (load("human-review.yaml").get("reviews", [])
              if (LEGAL / "human-review.yaml").exists() else [])}

    declared = {d["path"]: d for d in mapping.get("documents", [])}
    excused = {o["path"] for o in mapping.get("out_of_scope", [])}
    defects: list[str] = []

    # 1. Ничто в покрытой области не остаётся неназванным.
    for area in mapping.get("scope", []):
        base = ROOT / area["path"]
        for pattern in area.get("patterns", []):
            for found in sorted(base.glob(pattern)):
                rel = found.relative_to(ROOT).as_posix()
                if rel not in declared and rel not in excused:
                    defects.append(
                        f"{rel}: файл в покрытой области не объявлен — "
                        "ни в documents, ни в out_of_scope")

    for rel, doc in declared.items():
        if not doc.get("legally_significant"):
            continue
        path = ROOT / rel
        short = rel.split("/")[-1]

        if not path.exists():                                   # 2
            defects.append(f"{short}: объявлен, но файла нет")
            continue

        for norm_id in doc.get("norms", []):                    # 8
            if norm_id not in norms:
                defects.append(f"{short}: норма {norm_id} не объявлена в реестре")

        result = results.get(rel)
        if result is None:                                      # 3
            defects.append(f"{short}: нормативной сверки не было")
            continue

        try:
            actual = semantic_hash(path)
        except (UnsupportedType, OSError) as e:
            defects.append(f"{short}: смысловой хеш не посчитан — {e}")
            continue

        if actual != result.get("document_hash"):               # 4
            defects.append(
                f"{short}: результат сверки относится к другой версии "
                f"(документ {actual[7:19]}, результат "
                f"{str(result.get('document_hash'))[7:19]})")
            continue

        verdict = result.get("verdict")
        if verdict not in ACCEPTABLE:                           # 5
            defects.append(f"{short}: вердикт {verdict}")
            continue

        if verdict == "PASS_WITH_CORRECTIONS" and not result.get("recheck"):
            defects.append(f"{short}: PASS_WITH_CORRECTIONS без перечита")  # 6

        if result.get("escalation_required"):                   # 7
            record = human.get(rel)
            if not record or record.get("document_hash") != actual:
                defects.append(
                    f"{short}: escalation_required, а проверки человеком "
                    "под эту версию нет")

        # 9. Доказательство нормы: официальное, целое и то самое.
        #
        # Проверяется тройка, и каждая часть закрывает свой обход. Хеш
        # пересчитывается из сохранённого текста — записанному хешу верить
        # нельзя, подменивший текст подменил бы и его. Класс обязан быть
        # official — вторичный источник полного PASS не даёт. И результат
        # обязан ссылаться на тот же хеш: документ мог не измениться, а
        # редакция нормы под ним — да, и тогда прежний PASS не о чём.
        weak, stale, broken = [], [], []
        for checked in result.get("norms_checked", []):
            norm_id = checked["norm_id"]
            evidence_hash, why = verify_evidence(norm_id)
            if evidence_hash is None:
                broken.append(f"{norm_id} ({why})")
                continue
            if why:
                weak.append(f"{norm_id} ({why})")
                continue
            if checked.get("source_hash") != evidence_hash:
                stale.append(
                    f"{norm_id} (результат на {str(checked.get('source_hash'))[7:19]}, "
                    f"доказательство {evidence_hash[7:19]})")
        if broken:
            defects.append(f"{short}: доказательства норм негодны — "
                           + "; ".join(broken[:3])
                           + (f" и ещё {len(broken) - 3}" if len(broken) > 3 else ""))
        if weak:
            defects.append(f"{short}: источник норм не официальный — "
                           + "; ".join(weak[:3])
                           + (f" и ещё {len(weak) - 3}" if len(weak) > 3 else ""))
        if stale:
            defects.append(f"{short}: результат привязан к другой редакции нормы — "
                           + "; ".join(stale[:3])
                           + (f" и ещё {len(stale) - 3}" if len(stale) > 3 else ""))

    # 10. Утверждение о юристе — только при доказанной проверке человеком.
    # Сначала сами выдаваемые файлы: именно в них claim и стоял до 15.08.
    for rel, doc in declared.items():
        if not doc.get("legally_significant"):
            continue
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            body = "\n".join(docx_parts(path) if path.suffix.lower() == ".docx"
                              else xlsx_parts(path))
        except Exception:
            continue
        hit = asserts_lawyer_review(body)
        if hit and rel not in human:
            defects.append(
                f"{rel.split('/')[-1]}: утверждение о вычитке юристом "
                f"«{hit}» без записи human-review.yaml")

    for rel in mapping.get("customer_facing", []):
        path = ROOT / rel
        if not path.exists():
            defects.append(f"{rel}: пользовательская точка объявлена, файла нет")
            continue
        hit = asserts_lawyer_review(visible_text(path))
        if not hit:
            continue
        if rel not in human:
            defects.append(
                f"{rel}: утверждение о вычитке юристом «{hit}» без "
                "записи human-review.yaml")
    return defects


def main() -> int:
    defects = check()
    mapping = load("document-norms.yaml")
    covered = sum(1 for d in mapping.get("documents", [])
                  if d.get("legally_significant"))
    if defects:
        print(f"НОРМАТИВНЫЙ ГЕЙТ: дефектов {len(defects)}\n")
        for d in defects:
            print(f"  • {d}")
        print(f"\nЮридических документов под гейтом: {covered}.")
        print("Гейт модель не вызывает: он проверяет наличие годного результата.")
        print("Добыть результат — отдельный заход normative-checker.")
        if any("доказательства норм" in d or "источник норм" in d
               for d in defects):
            print("\nПро доказательства норм. Снимается это ровно одним"
                  " способом:")
            print("  python3 tools/fetch_legal_evidence.py --all")
            print("на машине, у которой есть доступ к официальному"
                  " публикатору. Инструмент сложит")
            print("тексты статей в data/legal/evidence/ и посчитает хеши;"
                  " в CI он не запускается.")
            print("\nЗаписью в human-review.yaml это НЕ снимается, и попытка"
                  " будет напрасной:")
            print("подтверждение человека — эскалация юридического вопроса, а"
                  " не замена")
            print("официальному тексту нормы. Разные вещи, и правило их не"
                  " смешивает.")
        return 1
    print(f"Юридических документов под гейтом: {covered}, дефектов нет: "
          "у каждого есть результат сверки под текущую версию.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
