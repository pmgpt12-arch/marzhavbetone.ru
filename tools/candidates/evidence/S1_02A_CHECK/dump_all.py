"""Дамп всех файлов распакованного архива в <dir>/txt/ (для чтения проверяющим)."""
import subprocess
import sys
from pathlib import Path

d = Path(sys.argv[1])
(d / "txt").mkdir(exist_ok=True)
for f in sorted((d / "kit").iterdir()):
    if f.suffix in (".docx", ".xlsx"):
        out = subprocess.run([sys.executable, str(Path(__file__).with_name("dump.py")), str(f)], capture_output=True, text=True).stdout
        (d / "txt" / (f.stem + ".txt")).write_text(out)
