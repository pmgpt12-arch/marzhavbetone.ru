#!/usr/bin/env python3
"""Мутации нормативного гейта: каждая обязана красить прогон.

Зелёная проверка ничего не стоит, пока не показано, что она краснеет.
Здесь это показано двенадцатью мутациями — по одной на каждое правило,
ради которого гейт заведён. Проверка работает на копии дерева во временном
каталоге: рабочие файлы не трогаются.

Тринадцатый случай обратный — состояние, где сходится всё, обязано
проходить. Без него набор доказывал бы только то, что гейт умеет краснеть,
а это умеет и `exit 1`. Состояние для него собирается в песочнице, а не
берётся из живых вердиктов: иначе доказательство исправности инструмента
пропадает ровно тогда, когда у документов находятся дефекты.

Запуск без pytest: python3 tools/test_normative_gate.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile

import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = "products-storage/01-zakrytie-rabot"
DOCX = f"{PKG}/12-pretenziya-na-neoplatu-po-ks-2.docx"
XLSX = f"{PKG}/14-raschet-procentov-395-gk.xlsx"

NEEDED = ["tools/normative_gate.py", "tools/semantic_hash.py",
          "tools/legal_evidence.py",
          "data/legal/norms.yaml", "data/legal/document-norms.yaml",
          "data/legal/normative-results.yaml", "products/p1-oplata-po-ks2.html"]


def sandbox(tmp: Path) -> Path:
    """Копия ровно того, что гейту нужно: полное дерево копировать незачем."""
    for rel in NEEDED:
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    (tmp / PKG).mkdir(parents=True, exist_ok=True)
    for src in (ROOT / PKG).glob("*.docx"):
        shutil.copy2(src, tmp / PKG / src.name)
    for src in (ROOT / PKG).glob("*.xlsx"):
        shutil.copy2(src, tmp / PKG / src.name)
    return tmp


def seed_evidence(tmp: Path, source_class: str = "official") -> None:
    """Разложить в песочницу доказательства норм и привязать к ним результат.

    Доказательства в репозитории есть — семнадцать официальных с
    16.08.2026, — но стенд синтезирует свои намеренно. Мутации должны
    проверять правила гейта, а не сегодняшнее содержимое реестра: тест,
    стоящий на живых данных, краснеет от их пополнения. Текст здесь
    условный и за пределы песочницы не выходит.
    """
    sys.path.insert(0, str(tmp / "tools"))
    import importlib
    import legal_evidence
    importlib.reload(legal_evidence)
    legal_evidence.ROOT = tmp
    legal_evidence.EVIDENCE_DIR = tmp / "data/legal/evidence"

    norms = yaml.safe_load((tmp / "data/legal/norms.yaml").read_text("utf-8"))
    hashes = {}
    for norm in norms["norms"]:
        nid = norm["norm_id"]
        text = f"условный текст нормы {nid} для стенда"
        marker = norm.get("edition_marker", "")
        legal_evidence.write(
            nid, official_url=norm.get("official_source", ""),
            edition_marker=marker, text=text, source_class=source_class,
            retrieved_at="2026-08-15", retrieved_by="стенд мутаций")
        hashes[nid] = legal_evidence.source_hash(marker, text)

    path = tmp / "data/legal/normative-results.yaml"
    data = yaml.safe_load(path.read_text("utf-8"))
    for result in data["results"]:
        for checked in result["norms_checked"]:
            checked["source_hash"] = hashes[checked["norm_id"]]
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def run(tmp: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, "tools/normative_gate.py"],
                       cwd=tmp, capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def edit_docx(path: Path, old: bytes, new: bytes) -> None:
    """Подмена внутри word/document.xml с пересборкой контейнера."""
    with zipfile.ZipFile(path) as z:
        items = {n: z.read(n) for n in z.namelist()}
    assert old in items["word/document.xml"], "текст для мутации не найден"
    items["word/document.xml"] = items["word/document.xml"].replace(old, new, 1)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items.items():
            z.writestr(name, data)


def edit_xlsx_formula(path: Path) -> None:
    with zipfile.ZipFile(path) as z:
        items = {n: z.read(n) for n in z.namelist()}
    # Берётся лист, в котором формулы есть: на первом листе книги их нет,
    # там входные данные. Каталог _rels исключается — это не лист.
    target = next(n for n in sorted(items)
                  if n.startswith("xl/worksheets/sheet")
                  and "_rels" not in n and b"<f>" in items[n])
    body = items[target]
    items[target] = body.replace(b"<f>", b"<f>1+", 1)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items.items():
            z.writestr(name, data)


def mutation(name: str, apply, seed: bool = True) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as d:
        tmp = sandbox(Path(d))
        if seed:
            seed_evidence(tmp)
        apply(tmp)
        code, out = run(tmp)
        return code != 0, out


# ── мутации ────────────────────────────────────────────────────────────

def m_docx_text(tmp: Path) -> None:
    edit_docx(tmp / DOCX, "НАПРАВЛЕНИЯ".encode(), "ПОЛУЧЕНИЯ".encode())


def m_xlsx_formula(tmp: Path) -> None:
    edit_xlsx_formula(tmp / XLSX)


def m_stale_result(tmp: Path) -> None:
    """Подставлен результат от прежней версии — хеш чужой."""
    p = tmp / "data/legal/normative-results.yaml"
    s = p.read_text(encoding="utf-8")
    first = s.split("document_hash: ")[1].split("\n")[0]
    p.write_text(s.replace(first, "sha256:" + "0" * 64, 1), encoding="utf-8")


def m_missing_mapping(tmp: Path) -> None:
    """Документ выпал из реестра — файл при этом продаётся."""
    p = tmp / "data/legal/document-norms.yaml"
    s = p.read_text(encoding="utf-8")
    start = s.index("  - path: " + DOCX)
    end = s.index("  - path: ", start + 10)
    p.write_text(s[:start] + s[end:], encoding="utf-8")


def m_secondary_passes(tmp: Path) -> None:
    """Доказательство вторичное — полного PASS оно не даёт."""
    seed_evidence(tmp, source_class="secondary")
    p = tmp / "data/legal/normative-results.yaml"
    p.write_text(p.read_text(encoding="utf-8")
                 .replace("PASS_WITH_CORRECTIONS", "PASS"), encoding="utf-8")


def m_evidence_changed(tmp: Path) -> None:
    """Норму перечитали, текст другой — прежний результат не о чём."""
    import importlib
    sys.path.insert(0, str(tmp / "tools"))
    import legal_evidence
    importlib.reload(legal_evidence)
    legal_evidence.ROOT = tmp
    legal_evidence.EVIDENCE_DIR = tmp / "data/legal/evidence"
    legal_evidence.write(
        "gk-395", official_url="http://pravo.gov.ru/", edition_marker="",
        text="новая редакция статьи 395", source_class="official",
        retrieved_at="2026-08-16", retrieved_by="стенд мутаций")


def m_edition_changed(tmp: Path) -> None:
    """Текст тот же, метка редакции другая — хеш обязан разойтись."""
    import importlib
    sys.path.insert(0, str(tmp / "tools"))
    import legal_evidence
    importlib.reload(legal_evidence)
    legal_evidence.ROOT = tmp
    legal_evidence.EVIDENCE_DIR = tmp / "data/legal/evidence"
    legal_evidence.write(
        "gk-395", official_url="http://pravo.gov.ru/",
        edition_marker="ред. от 01.01.2027 № 999-ФЗ",
        text="условный текст нормы gk-395 для стенда", source_class="official",
        retrieved_at="2026-08-16", retrieved_by="стенд мутаций")


def m_evidence_tampered(tmp: Path) -> None:
    """Текст доказательства правили мимо инструмента — хеш не сойдётся."""
    p = tmp / "data/legal/evidence/gk-395.yaml"
    p.write_text(p.read_text(encoding="utf-8")
                 .replace("условный текст нормы gk-395",
                          "подменённый текст нормы gk-395"), encoding="utf-8")


def m_human_review_cannot_fix_source(tmp: Path) -> None:
    """Запись человека не заменяет официальный текст нормы.

    Проверяется прямой соблазн: доказательства вторичные, владелец
    добавляет human-review на все шесть документов и ждёт зелени. Гейт
    обязан остаться красным — подтверждение человека это эскалация
    юридического вопроса, а не источник редакции нормы.
    """
    seed_evidence(tmp, source_class="secondary")
    mapping = yaml.safe_load(
        (tmp / "data/legal/document-norms.yaml").read_text("utf-8"))
    reviews = [{"document": d["path"], "document_hash": "sha256:" + "f" * 64,
                "reviewed_by": "владелец", "reviewed_at": "2026-08-15"}
               for d in mapping["documents"]]
    (tmp / "data/legal/human-review.yaml").write_text(
        yaml.safe_dump({"reviews": reviews}, allow_unicode=True), encoding="utf-8")


def m_no_evidence_at_all(tmp: Path) -> None:
    """Сегодняшнее состояние репозитория: доказательств нет вовсе."""
    shutil.rmtree(tmp / "data/legal/evidence")


def m_lawyer_claim(tmp: Path) -> None:
    """На страницу вернулось утверждение о вычитке юристом."""
    p = tmp / "products/p1-oplata-po-ks2.html"
    s = p.read_text(encoding="utf-8")
    p.write_text(s.replace("<h2>Что входит в комплект</h2>",
                           "<p>Тексты прошли вычитку юристом.</p>"
                           "<h2>Что входит в комплект</h2>", 1),
                 encoding="utf-8")


def m_verdict_fail(tmp: Path) -> None:
    p = tmp / "data/legal/normative-results.yaml"
    p.write_text(p.read_text(encoding="utf-8")
                 .replace("verdict: PASS_WITH_CORRECTIONS",
                          "verdict: NOT_VERIFIED", 1), encoding="utf-8")


def m_all_official(tmp: Path) -> None:
    """Исходное состояние, приведённое к зелёному честным путём.

    Мутация обратная: она поднимает источники до official и снимает
    единственную сегодняшнюю причину красноты. Гейт обязан позеленеть —
    иначе он краснеет не по названной причине, а всегда.
    """
    p = tmp / "data/legal/norms.yaml"
    p.write_text(p.read_text(encoding="utf-8")
                 .replace("source_class: secondary", "source_class: official"),
                 encoding="utf-8")


def m_result_misses_norm(tmp: Path) -> None:
    """Реестр расширился, результат остался на прежнем наборе норм.

    Причина замером 16.08.2026: контур вырос с 17 норм до 31, а шесть
    результатов сверки покрывали прежние. Сверка по половине применимых
    норм это не сверка документа, и без этого правила гейт её принимал бы.
    """
    m_all_green(tmp)
    path = tmp / "data/legal/document-norms.yaml"
    s = path.read_text(encoding="utf-8")
    # Норма реестра, которой в этом документе нет: добавленная в mapping,
    # она обязана попасть в «не покрыто сверкой».
    assert "gk-330" not in s.split("norms: [gk-746")[1].split("]")[0]
    path.write_text(s.replace("norms: [gk-746", "norms: [gk-330, gk-746", 1),
                    encoding="utf-8")


def m_all_green(tmp: Path) -> None:
    """Привести песочницу к состоянию, где сходится всё.

    Раньше здесь не менялось ничего, и «гейт зеленеет» доказывалось живыми
    вердиктами. Замер 16.08.2026 показал, чем это плохо: первая сверка на
    официальных источниках дала по шести документам PASS_WITH_CORRECTIONS,
    NOT_VERIFIED и FAIL — честный результат, — и проверка того, что гейт
    **умеет** зеленеть, разошлась. То есть доказательство исправности
    инструмента пропадало ровно тогда, когда у документов нашлись дефекты.

    Теперь состояние собирается здесь: вердикты приводятся к PASS,
    эскалации снимаются. Это не ослабление гейта — песочница живёт в
    tempdir и на выпуск не влияет; ослаблением было бы обратное, править
    настоящий результат ради зелени.
    """
    import importlib
    sys.path.insert(0, str(tmp / "tools"))
    import legal_evidence
    importlib.reload(legal_evidence)
    legal_evidence.ROOT = tmp
    legal_evidence.EVIDENCE_DIR = tmp / "data/legal/evidence"

    import semantic_hash
    importlib.reload(semantic_hash)

    mapping = {d["path"]: d for d in yaml.safe_load(
        (tmp / "data/legal/document-norms.yaml").read_text("utf-8"))["documents"]}
    path = tmp / "data/legal/normative-results.yaml"
    data = yaml.safe_load(path.read_text("utf-8"))
    for result in data["results"]:
        result["verdict"] = "PASS"
        result["escalation_required"] = False
        result["recheck"] = ""
        # Хеш документа тоже берётся из песочницы. Замер 16.08.2026: три
        # документа пересобраны после правок, результаты ещё указывали на
        # прежние версии — и базовый случай разошёлся, хотя гейт работал
        # верно. Доказательство того, что гейт умеет зеленеть, не должно
        # зависеть от того, дошла ли до результатов очередная пересборка.
        result["document_hash"] = semantic_hash.semantic_hash(
            tmp / result["document"])
        # Набор сверенных норм собирается из mapping, а не берётся из
        # живого результата: реестр растёт, и базовый случай не должен
        # краснеть от его пополнения.
        result["norms_checked"] = [
            {"norm_id": nid, "source_class": "official",
             "source_hash": legal_evidence.verify(nid)[0]}
            for nid in mapping[result["document"]]["norms"]]
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


CASES = [
    ("1. изменён юридический текст DOCX", m_docx_text, True),
    ("2. изменена формула XLSX", m_xlsx_formula, True),
    ("3. подставлен результат прежней версии", m_stale_result, True),
    ("4. документ выпал из реестра", m_missing_mapping, True),
    ("5. вторичное доказательство получает PASS", m_secondary_passes, True),
    ("6. вернулось утверждение о вычитке юристом", m_lawyer_claim, True),
    ("7. вердикт NOT_VERIFIED", m_verdict_fail, True),
    ("8. изменилось доказательство нормы", m_evidence_changed, True),
    ("9. изменилась метка редакции нормы", m_edition_changed, True),
    ("10. текст доказательства правлен мимо инструмента", m_evidence_tampered, True),
    ("11. human-review не заменяет официальный текст", m_human_review_cannot_fix_source, True),
    ("12. доказательств нет вовсе — состояние на сегодня", m_no_evidence_at_all, True),
    ("13. сверка не покрыла применимые нормы", m_result_misses_norm, True),
    ("14. всё сходится — гейт зеленеет", m_all_green, False),
]


def main() -> int:
    failed = 0
    for title, apply, must_be_red in CASES:
        red, out = mutation(title, apply)
        ok = red is must_be_red
        mark = "✓" if ok else "✗"
        want = "красный" if must_be_red else "зелёный"
        got = "красный" if red else "зелёный"
        print(f"  {mark} {title}: ждали {want}, вышло {got}")
        if not ok:
            failed += 1
            for line in out.strip().splitlines()[:6]:
                print(f"        {line}")
    print(f"\nМутаций {len(CASES)}, разошлось {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
