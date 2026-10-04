"""Печать изменённых 08 (заполненные копии) и 09 в изолированных профилях ru-RU → PDF → текст."""
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

WT = Path("/home/denis/projects/marzhavbetone.ru/.worktrees/codex-correction-363-20261005")
RUN = Path("/home/denis/.local/state/claude-dispatcher/recovery-20261004/corrections-20261005/363")
EV = WT / "tools/candidates/evidence/S1_MANUAL_TRANSFER"
sys.path.insert(0, str(WT / "tools"))
import test_s1_candidate as T  # noqa: E402

XCU = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooLocale" oor:op="fuse"><value>ru-RU</value></prop></item>
<item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupSystemLocale" oor:op="fuse"><value>ru-RU</value></prop></item>
<item oor:path="/org.openoffice.Office.Linguistic/General"><prop oor:name="DefaultLocale" oor:op="fuse"><value>ru-RU</value></prop></item>
</oor:items>
"""


def profile(name: str) -> Path:
    p = RUN / f"profile-ru-{name}"
    (p / "user").mkdir(parents=True, exist_ok=True)
    (p / "user/registrymodifications.xcu").write_text(XCU, encoding="utf-8")
    return p


def to_pdf(src: Path, prof: Path, outdir: Path, mode: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = ["soffice", f"-env:UserInstallation=file://{prof}", "--headless", "--norestore", mode,
           "--convert-to", "pdf", "--outdir", str(outdir), str(src)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                       env={"LANG": "ru_RU.UTF-8", "LC_ALL": "ru_RU.UTF-8", "PATH": "/usr/bin:/bin",
                            "HOME": str(RUN)})
    (outdir / (src.stem + ".log")).write_text(r.stdout + r.stderr, encoding="utf-8")
    pdf = outdir / (src.stem + ".pdf")
    assert pdf.exists(), r.stderr
    return pdf


def text(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout


fill = RUN / "print-in"
fill.mkdir(exist_ok=True)
b = T.КНИГА_РАСЧЁТА
A, B = ("A", 950_000, date(2026, 7, 1)), ("B", 320_000, date(2026, 8, 1))
HA, HB = ("A", 1_000_000, date(2026, 7, 1)), ("B", 400_000, date(2026, 8, 1))
ok = T.заполнить_395(b, fill / "08-verno.xlsx", [A, B], T.R1_КОНЕЦ, T.R1_СТАВКА, T.R1_ОПЛАТЫ_08, итог04=870_000)
hl = T.заполнить_395(b, fill / "08-obshchiy.xlsx", [HA, HB], T.R1_КОНЕЦ, T.R1_СТАВКА, T.R1_ОПЛАТЫ_08,
                     остаток={"A": 700_000, "B": 300_000}, итог04=870_000)
out = RUN / "print-out"
res = {}
for src in (ok, hl):
    pdf = to_pdf(src, profile("calc"), out, "--calc")
    t = text(pdf)
    (out / (src.stem + ".txt")).write_text(t, encoding="utf-8")
    res[src.name] = {"pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                     "pages": t.count("\f"),
                     "head": t[:6000]}
pdf09 = to_pdf(WT / "tools/candidates/s1-oplata-za-raboty/09-pretenziya.docx", profile("writer"), out, "--writer")
t09 = text(pdf09)
(out / "09-pretenziya.txt").write_text(t09, encoding="utf-8")
res["09-pretenziya.docx"] = {"pdf_sha256": hashlib.sha256(pdf09.read_bytes()).hexdigest(), "pages": t09.count("\f")}
(RUN / "print-result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "head"} for k, v in res.items()}, ensure_ascii=False))
