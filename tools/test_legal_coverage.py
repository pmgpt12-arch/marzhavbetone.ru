#!/usr/bin/env python3
"""Полнота нормативного контура на размеченных случаях. Сети не требует.

Проверка появилась после замера 16.08.2026: сверка шести документов P1
прошла по объявленному реестру и дала вердикты, а потом выяснилось, что
документы ссылаются ещё на четырнадцать норм, которых в контуре нет. По
ним сверки не было ни разу. Реестр отвечал на «что мы проверили», а не на
«на что документ опирается», и различить это было нечем.

Здесь закреплено поведение обнаружителя: что он обязан поймать, чего не
должен ловить, и чем непокрытая ссылка отличается от объявленной нормы,
которую документ не называет по номеру.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_legal_coverage import ключи_нормы, ссылки  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_статья_с_кодексом_находится():
    assert ссылки("нарушены ст. 309 ГК РФ и обязательство") == {"ГК:309"}
    assert ссылки("по правилам статьи 110 АПК РФ") == {"АПК:110"}
    assert ссылки("пошлина по ст. 333.21 НК РФ") == {"НК:333.21"}


def test_перечисление_даёт_все_номера():
    assert ссылки("ст. 309, 310 ГК РФ") == {"ГК:309", "ГК:310"}
    assert ссылки("статей 125 и 126 АПК РФ") == {"АПК:125", "АПК:126"}
    assert ссылки("ст. 4, 27, 35 АПК РФ") == {"АПК:4", "АПК:27", "АПК:35"}


def test_часть_и_пункт_не_путаются_со_статьёй():
    """«п. 5 ч. 1 ст. 126 АПК» — это статья 126, а не пункт 5 и часть 1."""
    assert ссылки("п. 5 ч. 1 ст. 126 АПК РФ") == {"АПК:126"}


def test_статья_без_кодекса_пропускается():
    """Угадывать кодекс по номеру статьи значит толковать право."""
    assert ссылки("в силу ст. 5 договор считается заключённым") == set()


def test_федеральный_закон_по_номеру():
    assert ссылки("ч. 1 ст. 8 Закона № 229-ФЗ") >= {"ФЗ:229"}
    assert "ФЗ:127" in ссылки("уведомление по Федеральному закону № 127-ФЗ")


def test_постановление_пленума_по_номеру():
    assert ссылки("п. 57 постановления Пленума ВС РФ от 22.11.2016 № 54") \
        >= {"ПЛЕНУМ:54"}


def test_акт_утвердивший_форму():
    assert ссылки("форма утверждена постановлением Госкомстата России "
                  "от 11.11.1999 № 100") == {"ГОСКОМСТАТ:100"}


def test_норма_реестра_раскрывается_в_ключи():
    assert ключи_нормы({"act": "ГК РФ часть первая", "article": "309"}) \
        == {"ГК:309"}
    assert ключи_нормы({"act": "ГК РФ часть вторая", "article": "711"}) \
        == {"ГК:711"}, "часть кодекса в ссылке документа не указывается"
    assert ключи_нормы({"act": "АПК РФ", "article": "125, 126"}) \
        == {"АПК:125", "АПК:126"}
    assert ключи_нормы({"act": "АПК РФ", "article": "ч. 5 ст. 4"}) == {"АПК:5",
                                                                       "АПК:4"}
    assert ключи_нормы({"act": "ФЗ от 02.10.2007 № 229-ФЗ", "article": "8"}) \
        == {"ФЗ:229"}
    assert ключи_нормы({"act": "Постановление Пленума ВС РФ от 22.11.2016 № 54",
                        "article": "п. 57"}) == {"ПЛЕНУМ:54"}
    assert ключи_нормы({"act": "Постановление Госкомстата России "
                               "от 11.11.1999 № 100", "article": "—"}) \
        == {"ГОСКОМСТАТ:100"}


def test_на_текущем_репозитории_непокрытых_нет():
    """Главный случай: реестр закрывает все ссылки шести документов P1."""
    p = subprocess.run([sys.executable, "tools/check_legal_coverage.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr


def test_снятая_привязка_краснеет():
    """Норму убрали из mapping, ссылка в документе осталась — это дефект.

    Мутация на копии: рабочие файлы не трогаются. Без неё проверка
    доказывала бы только то, что сегодня всё сходится, а не то, что она
    умеет ловить расхождение.
    """
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for rel in ("tools/check_legal_coverage.py", "tools/semantic_hash.py",
                    "data/legal/norms.yaml", "data/legal/document-norms.yaml"):
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        pkg = "products-storage/01-zakrytie-rabot"
        (tmp / pkg).mkdir(parents=True, exist_ok=True)
        for pattern in ("*.docx", "*.xlsx"):
            for src in (ROOT / pkg).glob(pattern):
                shutil.copy2(src, tmp / pkg / src.name)

        path = tmp / "data/legal/document-norms.yaml"
        path.write_text(path.read_text(encoding="utf-8")
                        .replace("gk-395, ", "", 1), encoding="utf-8")
        p = subprocess.run([sys.executable, "tools/check_legal_coverage.py"],
                           cwd=tmp, capture_output=True, text=True, timeout=120)
        assert p.returncode != 0, "снятая привязка обязана краснеть"
        assert "ГК:395" in p.stdout, p.stdout



def _песочница(tmp):
    import shutil
    for rel in ("tools/check_legal_coverage.py", "tools/semantic_hash.py",
                "data/legal/norms.yaml", "data/legal/document-norms.yaml"):
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    pkg = "products-storage/01-zakrytie-rabot"
    (tmp / pkg).mkdir(parents=True, exist_ok=True)
    for pattern in ("*.docx", "*.xlsx"):
        for src in (ROOT / pkg).glob(pattern):
            shutil.copy2(src, tmp / pkg / src.name)
    return tmp


def _прогон(tmp):
    return subprocess.run([sys.executable, "tools/check_legal_coverage.py"],
                          cwd=tmp, capture_output=True, text=True, timeout=120)


def test_атрибутивная_ссылка_без_причины_краснеет():
    """Иначе объявление атрибутивной стало бы способом спрятать опору."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        tmp = _песочница(Path(d))
        path = tmp / "data/legal/document-norms.yaml"
        s = path.read_text(encoding="utf-8")
        начало = s.index("        reason: >-")
        конец = s.index("\n    mechanisms:", начало)
        path.write_text(s[:начало] + '        reason: ""' + s[конец:],
                        encoding="utf-8")
        p = _прогон(tmp)
        assert p.returncode != 0, "атрибутивная без причины обязана краснеть"
        assert "без причины" in p.stdout, p.stdout


def test_атрибутивной_нельзя_объявить_то_чего_в_тексте_нет():
    """Объявление должно описывать документ, а не желаемое."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        tmp = _песочница(Path(d))
        path = tmp / "data/legal/document-norms.yaml"
        path.write_text(path.read_text(encoding="utf-8")
                        .replace("ref: ГОСКОМСТАТ:100", "ref: ГОСКОМСТАТ:999"),
                        encoding="utf-8")
        p = _прогон(tmp)
        assert p.returncode != 0
        assert "в тексте не найдена" in p.stdout, p.stdout


def test_снятая_атрибутивная_обнажает_ссылку():
    """Убрали объявление — ссылка снова непокрыта, а не исчезла."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        tmp = _песочница(Path(d))
        path = tmp / "data/legal/document-norms.yaml"
        s = path.read_text(encoding="utf-8")
        начало = s.index("    attributive_references:")
        конец = s.index("    mechanisms:", начало)
        path.write_text(s[:начало] + s[конец:], encoding="utf-8")
        p = _прогон(tmp)
        assert p.returncode != 0
        assert "ГОСКОМСТАТ:100" in p.stdout, p.stdout


def test_госкомстат_не_числится_нормативной_опорой():
    import yaml
    norms = {n["norm_id"] for n in yaml.safe_load(
        (ROOT / "data/legal/norms.yaml").read_text(encoding="utf-8"))["norms"]}
    assert "goskomstat-100" not in norms, \
        "акт назван документом, но юридический вывод на нём не стоит"
    docs = yaml.safe_load((ROOT / "data/legal/document-norms.yaml")
                          .read_text(encoding="utf-8"))["documents"]
    for d in docs:
        assert "goskomstat-100" not in d["norms"], d["path"]



def test_кодекс_полным_названием_распознаётся():
    """«Гражданского кодекса РФ» — тот же ГК, что и аббревиатура.

    Замер 16.08.2026: документ 12 пишет «В силу ст. 309, 310 Гражданского
    кодекса РФ», проверка знала только «ГК» и дала ложный ноль непокрытых
    ссылок — ровно тот исход, ради предотвращения которого она заведена.
    Нашёл это сверщик, а не код: цена узкого распознавания.
    """
    assert ссылки("В силу ст. 309, 310 Гражданского кодекса РФ") \
        == {"ГК:309", "ГК:310"}
    assert ссылки("по ст. 125 Арбитражного процессуального кодекса РФ") \
        == {"АПК:125"}
    assert ссылки("ст. 333.21 Налогового кодекса РФ") == {"НК:333.21"}


def test_гражданский_процессуальный_не_читается_как_гражданский():
    """Порядок разбора значим: ГПК начинается с того же слова, что ГК."""
    assert ссылки("ст. 131 Гражданского процессуального кодекса РФ") \
        == {"ГПК:131"}


def test_обе_формы_названия_дают_один_ключ():
    assert ссылки("ст. 395 ГК РФ") == ссылки("ст. 395 Гражданского кодекса РФ")


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
