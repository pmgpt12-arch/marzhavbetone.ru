"""Calc gate: each «Проверки» row height ≥ Calc optimal height of its longest message. Usage: rows_check.py <08.xlsx>"""
import json, subprocess, sys, time, os
from pathlib import Path
import uno
import openpyxl
sys.path.insert(0, "/home/denis/projects/marzhavbetone.ru/.worktrees/codex-correction-377-20261005/tools")
import build_s1_candidate as B

RUN = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]).resolve()
wb = openpyxl.load_workbook(SRC)
msgs = {r: B.самое_длинное(str(wb["Проверки"].cell(r, 3).value)) for r in range(2, 19)}
PROF = RUN / "profile-ru-calc"
PIPE = f"r377{os.getpid()}"
proc = subprocess.Popen(["soffice", f"-env:UserInstallation=file://{PROF}", "--headless", "--norestore",
                         f"--accept=pipe,name={PIPE};urp;"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
local = uno.getComponentContext()
res = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
for _ in range(60):
    try:
        ctx = res.resolve(f"uno:pipe,name={PIPE};urp;StarOffice.ComponentContext"); break
    except Exception:
        time.sleep(0.5)
desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
out = {}
try:
    doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(SRC)), "_blank", 0, ())
    sh = doc.Sheets.getByName("Проверки")
    for r, m in msgs.items():
        row = sh.Rows.getByIndex(r - 1)
        fixed = row.Height
        sh.getCellByPosition(2, r - 1).String = m
        row.OptimalHeight = True
        out[r] = {"chars": len(m), "fixed": fixed, "optimal": row.Height, "fits": fixed >= row.Height}
    doc.close(True)
finally:
    desktop.terminate(); proc.wait(timeout=30)
print(json.dumps(out, ensure_ascii=False))
print("ALL_FIT", all(v["fits"] for v in out.values()))
