#!/usr/bin/env python3
"""Что пора пересверить: просроченные нормы и задетые ими документы.

Отделено от гейта намеренно. Гейт отвечает за целостность выпуска: у
документа этой версии есть годный результат. Свежесть — другой вопрос, и
он календарный: срок нормы истекает сам по себе, без чьей-либо правки.
Ронять чужой PR за то, что наступило первое ноября, — способ научить
команду обходить проверку, а не поддерживать реестр.

Поэтому здесь **сообщение, а не блокировка**: код возврата всегда 0.
Инструмент отвечает на два вопроса и строит обратный индекс, которого
нигде больше нет:

    норма просрочена → какие документы её применяют → что пересверить

`recheck_after` — это «пора перепроверить», а не «закон изменился».
Автоматически узнать об изменении закона репозиторий сегодня не может:
официальные публикаторы из рабочей среды закрыты (`CONNECT 403`), а вывод
об изменении по вторичному источнику опаснее его отсутствия.

    python3 tools/normative_scope.py
    python3 tools/normative_scope.py --norm gk-395   # кого задевает норма
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_evidence import verify as verify_evidence  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEGAL = ROOT / "data" / "legal"


def load(name: str) -> dict:
    return yaml.safe_load((LEGAL / name).read_text(encoding="utf-8")) or {}


def affected_by(norm_id: str, documents: list[dict]) -> list[str]:
    """Обратный индекс строится, а не хранится: второй перечень разъедется."""
    return [d["path"] for d in documents if norm_id in d.get("norms", [])]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--norm", help="показать документы, применяющие норму")
    ap.add_argument("--today", help="дата для проверки срока (ГГГГ-ММ-ДД)")
    args = ap.parse_args()

    norms = {n["norm_id"]: n for n in load("norms.yaml").get("norms", [])}
    documents = load("document-norms.yaml").get("documents", [])
    today = date.fromisoformat(args.today) if args.today else date.today()

    if args.norm:
        if args.norm not in norms:
            print(f"нормы {args.norm} в реестре нет")
            return 0
        hit = affected_by(args.norm, documents)
        print(f"{args.norm}: документов {len(hit)}")
        for path in hit:
            print(f"  • {path}")
        return 0

    expired, soon, weak, fresh_hashes = [], [], [], {}
    for norm_id, norm in sorted(norms.items()):
        after = norm.get("recheck_after")
        if after:
            due = date.fromisoformat(str(after))
            (expired if due < today else soon).append((norm_id, due))
        evidence_hash, why = verify_evidence(norm_id)
        fresh_hashes[norm_id] = evidence_hash if not why else None
        if why:
            weak.append((norm_id, why))

    if expired:
        print(f"ПОРА ПЕРЕСВЕРИТЬ — норм {len(expired)}\n")
        for norm_id, due in sorted(expired, key=lambda x: x[1]):
            docs = affected_by(norm_id, documents)
            print(f"  {norm_id} (срок {due}) → документов {len(docs)}")
            for path in docs:
                print(f"      {path.split('/')[-1]}")
        print("\nЭто «пора перепроверить», а не «закон изменился»: узнать об")
        print("изменении закона репозиторий сегодня не может — официальные")
        print("публикаторы из среды закрыты.")
    else:
        nearest = min(soon, key=lambda x: x[1]) if soon else None
        print("Просроченных норм нет"
              + (f"; ближайший срок {nearest[1]} ({nearest[0]})." if nearest else "."))

    if weak:
        print(f"\nНорм без годного офлайн-доказательства: {len(weak)} из {len(norms)}.")
        for norm_id, why in weak[:5]:
            print(f"  {norm_id}: {why}")
        if len(weak) > 5:
            print(f"  … и ещё {len(weak) - 5}")
        print("\nПолного PASS такие нормы документу не дают. Снимается одним")
        print("способом: python3 tools/fetch_legal_evidence.py --all на машине")
        print("с доступом к официальному публикатору. Подтверждением человека")
        print("это не снимается — эскалация не заменяет текст нормы.")

    # Смена доказательства — то, ради чего нужен обратный индекс: какие
    # документы придётся пересверить, если норма перечитана и изменилась.
    changed = [(n, h) for n, h in fresh_hashes.items() if h]
    if changed:
        print(f"\nНорм с годным доказательством: {len(changed)}. Если при "
              "следующем прогоне")
        print("fetch_legal_evidence хеш любой из них изменится, пересверить "
              "придётся:")
        for norm_id, _ in changed[:3]:
            docs = affected_by(norm_id, documents)
            print(f"  {norm_id} → {len(docs)} документ(ов)")

    print(f"\nДокументов под нормативным контуром: {len(documents)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
