"""Сборка кандидата во временный каталог и копирование только разрешённых изменённых файлов."""
import hashlib
import shutil
import sys
from pathlib import Path

WT = Path("/home/denis/projects/marzhavbetone.ru/.worktrees/codex-correction-363-20261005")
RUN = Path("/home/denis/.local/state/claude-dispatcher/recovery-20261004/corrections-20261005/363")
sys.path.insert(0, str(WT / "tools"))
import build_s1_candidate as B  # noqa: E402
import s1_route as R  # noqa: E402

ALLOWED = {"00-START-HERE.txt", "08-raschet-procentov-395.xlsx", "09-pretenziya.docx", "MANIFEST.md"}
out = RUN / "build-out"
B.build(out)
C = R.CANDIDATE
changed = []
for p in sorted(out.iterdir()):
    old = C / p.name
    if not old.exists() or old.read_bytes() != p.read_bytes():
        changed.append(p.name)
route_same = R.ROUTE_MAP.read_text(encoding="utf-8") == B.route_map_json()
print("changed:", changed, "route_map_same:", route_same)
extra = [n for n in changed if n not in ALLOWED]
if extra or not route_same:
    print("STOP: out-of-scope changes", extra)
    sys.exit(2)
if "--copy" in sys.argv:
    for n in changed:
        shutil.copyfile(out / n, C / n)
        print("copied", n, hashlib.sha256((C / n).read_bytes()).hexdigest())
