"""Own Calc check for F-1/F-2 (run dir only). Usage: python3 uno_check.py <08.xlsx> <label>"""
import json, shutil, subprocess, sys, time, os
from pathlib import Path
import uno
from com.sun.star.beans import PropertyValue

RUN = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]).resolve()
LABEL = sys.argv[2]
OUT = RUN / f"calc-{LABEL}"
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir()
PROF = RUN / "profile-ru-calc"
xcu = PROF / "user" / "registrymodifications.xcu"
if not xcu.exists():
    xcu.parent.mkdir(parents=True)
    xcu.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
                   'xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
                   '<item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooLocale" oor:op="fuse"><value>ru-RU</value></prop></item>\n'
                   '<item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupSystemLocale" oor:op="fuse"><value>ru-RU</value></prop></item>\n'
                   '</oor:items>\n')
PIPE = f"p377{os.getpid()}"
proc = subprocess.Popen(["soffice", f"-env:UserInstallation=file://{PROF}", "--headless", "--norestore", "--nologo",
                         f"--accept=pipe,name={PIPE};urp;"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
local = uno.getComponentContext()
res = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
for _ in range(60):
    try:
        ctx = res.resolve(f"uno:pipe,name={PIPE};urp;StarOffice.ComponentContext"); break
    except Exception:
        time.sleep(0.5)
smgr = ctx.ServiceManager
desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
disp = smgr.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)


def pv(n, v):
    p = PropertyValue(); p.Name, p.Value = n, v; return p


def load(path):
    return desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(path)), "_blank", 0, ())


def ser(y, m, d):
    from datetime import date
    return (date(y, m, d) - date(1899, 12, 30)).days


def typ(doc, sheet, cell, text):
    """Real typing: select the cell and send the string through EnterString."""
    ctrl = doc.CurrentController
    sh = doc.Sheets.getByName(sheet)
    ctrl.setActiveSheet(sh)
    ctrl.select(sh.getCellRangeByName(cell))
    disp.executeDispatch(ctrl.Frame, ".uno:EnterString", "", 0, (pv("StringName", text),))
    doc.calculateAll()


def fill(doc, acts, b5, b6=None):
    s = doc.Sheets
    ak, op, vv = s.getByName("Акты"), s.getByName("Оплаты"), s.getByName("Ввод")
    for i, (aid, d, start, f) in enumerate(acts):
        r = 5 + i
        ak.getCellRangeByName(f"B{r}").String = aid
        ak.getCellRangeByName(f"C{r}").String = f"КС-2 {aid}"
        ak.getCellRangeByName(f"D{r}").Value = d
        ak.getCellRangeByName(f"E{r}").Value = ser(*start)
        ak.getCellRangeByName(f"F{r}").Value = f
    for i, (dt, sm, aid) in enumerate([((2026, 7, 20), 300000, "A"), ((2026, 8, 15), 100000, "B")]):
        if aid in [a[0] for a in acts]:
            r = 6 + i
            op.getCellRangeByName(f"A{r}").Value = ser(*dt)
            op.getCellRangeByName(f"B{r}").Value = sm
            op.getCellRangeByName(f"C{r}").String = f"п/п {i + 1}"
            op.getCellRangeByName(f"D{r}").String = aid
    vv.getCellRangeByName("B4").Value = ser(2026, 9, 30)
    if b5 is not None:
        vv.getCellRangeByName("B5").Value = b5
    if b6 is not None:
        vv.getCellRangeByName("B6").Value = b6
    vv.getCellRangeByName("A12").Value = ser(2026, 6, 1)
    vv.getCellRangeByName("A13").Value = ser(2026, 9, 15)
    doc.calculateAll()


def state(doc):
    s = doc.Sheets
    g = lambda sh, c: s.getByName(sh).getCellRangeByName(c)  # noqa: E731
    rs = s.getByName("Расчёт")
    g_rows = [rs.getCellRangeByName(f"G{r}").String for r in range(7, 13) if rs.getCellRangeByName(f"A{r}").String]
    return {"B12_value": g("Ввод", "B12").Value, "B12_shown": g("Ввод", "B12").String, "B12_fmt": g("Ввод", "B12").NumberFormat,
            "B13_value": g("Ввод", "B13").Value, "B13_shown": g("Ввод", "B13").String,
            "C12": g("Ввод", "C12").String, "C13": g("Ввод", "C13").String,
            "check13": g("Проверки", "C13").String, "status": g("Проверки", "C20").String,
            "D2": g("Расчёт", "D2").String, "D3": g("Расчёт", "D3").String, "D4": g("Расчёт", "D4").String,
            "Расчёт_G": g_rows, "По_дням_B2": g("По дням", "B2").String, "По_дням_L6": g("По дням", "L6").String}


def row13(doc):
    rows = doc.Sheets.getByName("Проверки").Rows
    fixed = rows.getByIndex(12).Height
    rows.getByIndex(12).OptimalHeight = True
    opt = rows.getByIndex(12).Height
    return {"fixed_1_100mm": fixed, "calc_optimal_1_100mm": opt, "fits": fixed >= opt}


def pdf(doc, name):
    p = OUT / f"{name}.pdf"
    doc.storeToURL(uno.systemPathToFileUrl(str(p)), (pv("FilterName", "calc_pdf_Export"),))
    subprocess.run(["pdftotext", "-layout", str(p), str(OUT / f"{name}.txt")], check=True)
    return (OUT / f"{name}.txt").read_text()


J = [("A", 950000, (2026, 7, 1), 650000), ("B", 320000, (2026, 8, 1), 220000)]
H = [("A", 1000000, (2026, 7, 1), 700000), ("B", 400000, (2026, 8, 1), 300000)]
R = {}
try:
    # P5 re-entry: 21% → 21, then save/reopen, then PDF
    doc = load(SRC); fill(doc, J, 870000); typ(doc, "Ввод", "B13", "19")
    typ(doc, "Ввод", "B12", "21%"); R["typed_21pct"] = state(doc)
    typ(doc, "Ввод", "B12", "21"); R["retyped_21"] = state(doc)
    saved = OUT / "reentry-saved.xlsx"
    doc.storeToURL(uno.systemPathToFileUrl(str(saved)), (pv("FilterName", "Calc MS Excel 2007 XML"),))
    doc.close(True)
    doc = load(saved); doc.calculateAll(); R["reopened"] = state(doc)
    t = pdf(doc, "reentry-reopened"); R["reentry_pdf_has_2100"] = "2100" in t
    R["reentry_pdf_rate_lines"] = [ln.strip() for ln in t.splitlines() if "21,00" in ln or "19,00" in ln][:8]
    doc.close(True)
    # normal typing 21, 19,5 → 19
    doc = load(SRC); fill(doc, J, 870000)
    typ(doc, "Ввод", "B12", "21"); typ(doc, "Ввод", "B13", "19,5"); R["normal_19_5"] = state(doc)
    typ(doc, "Ввод", "B13", "19"); R["normal_19"] = state(doc)
    t = pdf(doc, "normal"); R["normal_pdf_has_2100"] = "2100" in t
    # numeric paste: copy a number cell (Ввод B13 = 19), paste into B14 area? use spare J1 source
    vv = doc.Sheets.getByName("Ввод")
    vv.getCellRangeByName("J1").Value = 21
    ctrl = doc.CurrentController
    ctrl.select(vv.getCellRangeByName("J1")); disp.executeDispatch(ctrl.Frame, ".uno:Copy", "", 0, ())
    typ(doc, "Ввод", "B12", "21%")
    ctrl.select(vv.getCellRangeByName("B12")); disp.executeDispatch(ctrl.Frame, ".uno:Paste", "", 0, ())
    doc.calculateAll(); vv.getCellRangeByName("J1").String = ""; doc.calculateAll()
    R["paste_after_21pct"] = state(doc)
    doc.close(True)
    # forced percent cell format (inherited/pasted format), then typing 21
    from com.sun.star.lang import Locale
    doc = load(SRC); fill(doc, J, 870000); typ(doc, "Ввод", "B13", "19")
    vv = doc.Sheets.getByName("Ввод")
    vv.getCellRangeByName("B12").NumberFormat = doc.NumberFormats.getStandardFormat(128, Locale())
    typ(doc, "Ввод", "B12", "21"); R["forced_pct_format_typed_21"] = state(doc)
    saved = OUT / "forced-saved.xlsx"
    doc.storeToURL(uno.systemPathToFileUrl(str(saved)), (pv("FilterName", "Calc MS Excel 2007 XML"),))
    doc.close(True)
    doc = load(saved); doc.calculateAll(); R["forced_reopened"] = state(doc)
    t = pdf(doc, "forced-reopened"); R["forced_pdf_has_2100"] = "2100" in t
    doc.close(True)
    # mismatch H/L + 870 000 and missing reference
    doc = load(SRC); fill(doc, H, 870000); typ(doc, "Ввод", "B12", "21"); typ(doc, "Ввод", "B13", "19")
    R["mismatch"] = state(doc)
    t = pdf(doc, "mismatch"); R["mismatch_pdf_msg"] = [ln.strip() for ln in t.splitlines() if "сверка с файлом 04" in ln or "бесспорные суммы" in ln or "Периоды без" in ln]
    R["mismatch_row13"] = row13(doc)
    doc.close(True)
    doc = load(SRC); fill(doc, J, None); typ(doc, "Ввод", "B12", "21"); typ(doc, "Ввод", "B13", "19")
    R["missing_reference"] = state(doc); doc.close(True)
finally:
    try:
        desktop.terminate()
    except Exception:
        pass
    proc.wait(timeout=30)
(OUT / "result.json").write_text(json.dumps(R, ensure_ascii=False, indent=1))
print(json.dumps(R, ensure_ascii=False, indent=1))
