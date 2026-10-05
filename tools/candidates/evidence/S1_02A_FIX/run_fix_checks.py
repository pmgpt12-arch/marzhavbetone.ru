"""Прогон только проверок S1-02А-FIX (Н-1…Н-9) из tools/test_s1_candidate.py."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import test_s1_candidate as T  # noqa: E402

провал = 0
for имя in sorted(n for n in dir(T) if re.match(r"test_н\d", n)):
    try:
        getattr(T, имя)()
    except AssertionError as ошибка:
        провал += 1
        print(f"ПРОВАЛ  {имя}\n  {ошибка}")
    else:
        print(f"ок  {имя}")
for п in T.ПРОПУСКИ:
    print(f"ПРОПУСК  {п}")
print(f"итог: провалов {провал}")
sys.exit(1 if провал else 0)
