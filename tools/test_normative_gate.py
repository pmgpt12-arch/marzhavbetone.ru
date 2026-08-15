#!/usr/bin/env python3
"""Мутации нормативного гейта: каждая обязана красить прогон.

Зелёная проверка ничего не стоит, пока не показано, что она краснеет.
Здесь это показано восемью мутациями — по одной на каждое правило, ради
которого гейт заведён. Проверка работает на копии дерева во временном
каталоге: рабочие файлы не трогаются.

Восьмой случай обратный — неизменный проверенный документ обязан
проходить. Без него набор доказывал бы только то, что гейт умеет краснеть,
а это умеет и `exit 1`.

Запуск без pytest: python3 tools/test_normative_gate.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = "products-storage/01-zakrytie-rabot"
DOCX = f"{PKG}/12-pretenziya-na-neoplatu-po-ks-2.docx"
XLSX = f"{PKG}/14-raschet-procentov-395-gk.xlsx"

NEEDED = ["tools/normative_gate.py", "tools/semantic_hash.py",
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


def mutation(name: str, apply) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as d:
        tmp = sandbox(Path(d))
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
    """Вторичному источнику пытаются выдать полный PASS."""
    p = tmp / "data/legal/normative-results.yaml"
    p.write_text(p.read_text(encoding="utf-8")
                 .replace("PASS_WITH_CORRECTIONS", "PASS"), encoding="utf-8")


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


CASES = [
    ("1. изменён юридический текст DOCX", m_docx_text, True),
    ("2. изменена формула XLSX", m_xlsx_formula, True),
    ("3. подставлен результат прежней версии", m_stale_result, True),
    ("4. документ выпал из реестра", m_missing_mapping, True),
    ("5. вторичный источник получает PASS", m_secondary_passes, True),
    ("6. вернулось утверждение о вычитке юристом", m_lawyer_claim, True),
    ("7. вердикт NOT_VERIFIED", m_verdict_fail, True),
    ("8. источники official — гейт зеленеет", m_all_official, False),
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
