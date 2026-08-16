#!/usr/bin/env python3
"""Каждая правовая ссылка документа обязана быть в нормативном контуре.

Зачем. Сверка 16.08.2026 на семнадцати официальных доказательствах прошла
по объявленному реестру — и только тогда выяснилось, что документы
ссылаются ещё на четырнадцать норм, которых в реестре нет. По ним сверки
не было **никогда**: ни в D-06, ни сейчас. Реестр отвечал на вопрос «что
мы проверили», а не «на что документ опирается», и разница между этими
двумя вопросами не была видна ничем.

Проверка закрывает именно её:

    правовые ссылки документа − применимые нормы реестра = 0

Право здесь не толкуется. Инструмент не решает, верна ли ссылка и та ли
норма названа — на это есть отдельный заход `normative-checker`. Он
отвечает на единственный вопрос: названа ли норма где-то в контуре, или
документ ссылается в пустоту.

Что распознаётся: статьи кодексов с указанием кодекса, федеральные законы
по номеру, постановления Пленума Верховного Суда по номеру, акты, которыми
утверждены формы (Госкомстат). Ссылка без указания акта («ст. 5»)
пропускается намеренно: угадывать кодекс по номеру статьи значит толковать.

    python3 tools/check_legal_coverage.py
    python3 tools/check_legal_coverage.py --list   # что нашлось по каждому
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from semantic_hash import docx_parts, xlsx_parts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEGAL = ROOT / "data" / "legal"

# Как акт реестра превращается в ключ ссылки. Ключ намеренно грубый: в
# документе пишут «ст. 309 ГК РФ», не называя части кодекса, и требовать
# от текста большей точности, чем в нём есть, значит ловить призраков.
КОДЕКСЫ = {"ГК": "ГК", "АПК": "АПК", "НК": "НК", "ГПК": "ГПК"}

_СТАТЬИ = re.compile(
    r"ст(?:атья|атьи|атье|атьей|атьёй|атей|атьям|атьями|\.)\s*"
    r"(\d+(?:\.\d+)?(?:\s*(?:,|и)\s*\d+(?:\.\d+)?)*)"
    r"[^.;)]{0,60}?\b(ГК|АПК|НК|ГПК)\b")
_ЗАКОН = re.compile(r"№\s*(\d+)\s*-\s*ФЗ")
_ПЛЕНУМ = re.compile(r"Пленума[^№]{0,80}№\s*(\d+)")
_ГОСКОМСТАТ = re.compile(r"Госкомстат\w*[^№]{0,60}№\s*(\d+)")
_НОМЕР = re.compile(r"\d+(?:\.\d+)?")


def текст(path: Path) -> str:
    parts = docx_parts(path) if path.suffix == ".docx" else xlsx_parts(path)
    return " ".join(p for p in parts if p.strip())


def ссылки(body: str) -> set[str]:
    """Правовые ссылки документа в виде ключей «АКТ:единица»."""
    out: set[str] = set()
    for номера, кодекс in _СТАТЬИ.findall(body):
        for единица in _НОМЕР.findall(номера):
            out.add(f"{КОДЕКСЫ[кодекс]}:{единица}")
    for номер in _ЗАКОН.findall(body):
        out.add(f"ФЗ:{номер}")
    for номер in _ПЛЕНУМ.findall(body):
        out.add(f"ПЛЕНУМ:{номер}")
    for номер in _ГОСКОМСТАТ.findall(body):
        out.add(f"ГОСКОМСТАТ:{номер}")
    return out


def ключи_нормы(norm: dict) -> set[str]:
    """Какие ссылки закрывает норма реестра. Выводится из акта и статьи."""
    act = norm.get("act", "")
    единицы = _НОМЕР.findall(str(norm.get("article", "")))
    for короткое, ключ in КОДЕКСЫ.items():
        if re.search(rf"\b{короткое}\b", act) or (
                короткое == "ГК" and "Гражданский кодекс" in act) or (
                короткое == "АПК" and "Арбитражный процессуальный" in act) or (
                короткое == "НК" and "Налоговый кодекс" in act):
            return {f"{ключ}:{u}" for u in единицы}
    m = re.search(r"№\s*(\d+)\s*-\s*ФЗ", act)
    if m:
        return {f"ФЗ:{m.group(1)}"}
    m = re.search(r"Пленума[^№]{0,80}№\s*(\d+)", act)
    if m:
        return {f"ПЛЕНУМ:{m.group(1)}"}
    m = re.search(r"Госкомстат\w*[^№]{0,60}№\s*(\d+)", act)
    if m:
        return {f"ГОСКОМСТАТ:{m.group(1)}"}
    return set()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true",
                    help="показать найденные ссылки по каждому документу")
    args = ap.parse_args()

    norms = {n["norm_id"]: n for n in yaml.safe_load(
        (LEGAL / "norms.yaml").read_text(encoding="utf-8"))["norms"]}
    documents = yaml.safe_load(
        (LEGAL / "document-norms.yaml").read_text(encoding="utf-8"))["documents"]

    непокрыто: list[str] = []
    лишнее: list[str] = []
    for doc in documents:
        path = ROOT / doc["path"]
        if not path.exists():
            непокрыто.append(f"{doc['path']}: файла нет")
            continue
        найдено = ссылки(текст(path))
        покрыто: set[str] = set()
        for nid in doc.get("norms", []):
            покрыто |= ключи_нормы(norms.get(nid, {}))
        мимо = sorted(найдено - покрыто)
        if args.list:
            print(f"\n{path.name}")
            print(f"  ссылок в тексте: {len(найдено)} — {', '.join(sorted(найдено))}")
            print(f"  закрыто реестром: {len(найдено) - len(мимо)}")
        for ключ in мимо:
            непокрыто.append(f"{path.name}: {ключ} — нормы в контуре нет")
        # Норма в реестре, которой в тексте нет, дефектом не считается:
        # документ может опираться на неё по существу, не называя номера.
        # Но знать об этом полезно, поэтому она называется отдельно.
        for nid in doc.get("norms", []):
            ключи = ключи_нормы(norms.get(nid, {}))
            if ключи and not (ключи & найдено):
                лишнее.append(f"{path.name}: {nid} объявлена, в тексте не названа")

    if непокрыто:
        print(f"НЕПОКРЫТЫХ ССЫЛОК: {len(непокрыто)}\n")
        for строка in непокрыто:
            print(f"  • {строка}")
        print("\nДокумент ссылается на норму, которой нет в нормативном контуре:")
        print("сверки по ней не было ни разу, и заявление о нормативной сверке")
        print("на такой документ не распространяется. Норму нужно завести в")
        print("data/legal/norms.yaml, привязать к документу в document-norms.yaml")
        print("и добыть по ней официальное доказательство.")
        return 1

    print(f"Непокрытых правовых ссылок нет. Документов: {len(documents)}.")
    if лишнее:
        print(f"\nОбъявлено, но в тексте не названо — {len(лишнее)} "
              "(не дефект, документ может опираться по существу):")
        for строка in лишнее:
            print(f"  · {строка}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
