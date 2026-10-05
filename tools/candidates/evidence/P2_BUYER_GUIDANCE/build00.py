"""Изолированная сборка 00-INSTRUKCIYA: генератор из worktree копируется в
каталог прогона и пишет только в build/02-dopraboty-bez-poter. Два прогона —
проверка детерминизма; затем две выходные копии кладутся в worktree."""
import hashlib
import runpy
import shutil
import sys
from pathlib import Path

sys.path.append("/home/denis/projects/ai-business-os/.venv/lib/python3.12/site-packages")
import reportlab  # noqa: E402
print("reportlab", reportlab.Version)

WT = Path("/home/denis/projects/marzhavbetone.ru/.worktrees/codex-correction-388-20261005")
RUN = Path(__file__).parent
hashes = []
for n in (1, 2):
    b = RUN / f"build{n}"
    shutil.rmtree(b, ignore_errors=True)
    (b / "02-dopraboty-bez-poter").mkdir(parents=True)
    shutil.copy(WT / "products-storage/build_paid_02_instrukciya.py", b)
    runpy.run_path(str(b / "build_paid_02_instrukciya.py"), run_name="__main__")
    h = {f: hashlib.sha256((b / "02-dopraboty-bez-poter" / f).read_bytes()).hexdigest()
         for f in ("00-INSTRUKCIYA.docx", "00-INSTRUKCIYA.pdf")}
    print(n, h)
    hashes.append(h)
assert hashes[0] == hashes[1], "сборка не детерминирована"
for f in hashes[0]:
    shutil.copy(RUN / "build1/02-dopraboty-bez-poter" / f,
                WT / "products-storage/02-dopraboty-bez-poter" / f)
print("copied")
