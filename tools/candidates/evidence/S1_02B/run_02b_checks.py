"""Прогон только четырёх проверок S1-02Б (контракт #321 §9.2) из tools/test_s1_candidate.py
и изменённого ожидания регрессии (test_libreoffice_прогон: 779 934 — общий долг)."""
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import test_s1_candidate as T  # noqa: E402

ПРОВЕРКИ = ["test_общий_долг_и_спорная_часть_раздельно", "test_допработы_спорная_сумма_в_реестре",
            "test_акт_сверки_из_реестра", "test_книга_расчёта_берёт_только_бесспорную_часть",
            "test_libreoffice_прогон"]
провал = 0
for имя in ПРОВЕРКИ:
    try:
        getattr(T, имя)()
    except Exception as ошибка:  # на базе лист «Акт сверки» отсутствует — KeyError тоже провал
        провал += 1
        print(f"ПРОВАЛ  {имя}\n  {type(ошибка).__name__}: {str(ошибка)[:400]}")
    else:
        print(f"ок  {имя}")
for п in T.ПРОПУСКИ:
    print(f"ПРОПУСК  {п}")
print(f"итог: провалов {провал} из {len(ПРОВЕРКИ)}")
sys.exit(1 if провал else 0)
