#!/usr/bin/env python3
"""#364: значения набора в Calc ru-RU — F, G, H строки и итога, страницы и
сообщения на печати — в typed_04.json рядом со скриптом. Сохранённые Calc
книги и PDF — в каталог из аргумента (вне репозитория).

    python3 -B tools/candidates/evidence/P5_PERCENT_INPUT/collect_typed_04.py /каталог/для/копий
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ЗДЕСЬ = Path(__file__).resolve().parent
КОРЕНЬ = ЗДЕСЬ.parents[3]
sys.path.insert(0, str(КОРЕНЬ / "tools"))


def main() -> int:
    if len(sys.argv) > 1:
        os.environ["P5_EVIDENCE_DIR"] = sys.argv[1]
    import test_p5_calc_results as t
    рез = t.результаты_набора_04()
    сценарии = {**t.НАБОР_04, **t.НАБОР_04_ИЛИ_ОТКАЗ}
    вывод = {"04_sha256": hashlib.sha256(t.книги_из_архива()[t.КНИГА_04]).hexdigest(), "сценарии": []}
    for i, (имя, (таблица, ставка, ожидание)) in enumerate(сценарии.items()):
        f, g, h, g_итог, h_итог, r, r_итог, страниц, текст = рез[имя]
        ввод = [ставка] if isinstance(ставка, str) else [
            f"число {float(с)} (процентный формат)" if isinstance(с, t.Число) else с for с in ставка]
        вывод["сценарии"].append({
            "файл": f"typed-{i}", "имя": имя, "таблица": таблица, "ввод_F": ввод,
            "ожидание": ожидание, "F_сохранено": f, "G": g, "H": h, "итог_G": g_итог, "итог_H": h_итог,
            "строка": r, "строка_итога": r_итог, "страниц_pdf": страниц,
            "сообщение_на_печати": bool(h) and h[:20].lower() in текст.lower()})
    (ЗДЕСЬ / "typed_04.json").write_text(json.dumps(вывод, ensure_ascii=False, indent=1), encoding="utf-8")
    for с in вывод["сценарии"]:
        print(с["файл"], с["имя"], "| F =", repr(с["F_сохранено"]), "| G =", с["G"], "| итог =", с["итог_G"],
              "| H =", с["H"][:60], "| стр.", с["страниц_pdf"], "| на печати", с["сообщение_на_печати"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
