"""#340, опыт до правки: что Calc ru-RU делает с набором «0,05%».

Запускался на книге 04 @ 98165e5. Результат: F = 0,0005, показ «0,0005»,
CELL("format") = «F4» и для «0,05», и для «0,05%» — Calc не переводит ячейку
в процентный формат, знак % в книге не остаётся. Поэтому распознать набор
со знаком % можно только по величине ставки (порог в build_paid_07.py).

    python3 -m pytest tools/candidates/evidence/MB001_P5_FIX2/exp_cell_format_340.py -s
"""
import subprocess, sys, time, shutil, tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[4] / "products-storage/07-uderzhaniya-shtrafy-zachety/04-raschet-ubytkov.xlsx"


def test_exp():
    import uno, openpyxl
    from com.sun.star.beans import PropertyValue
    tmp = Path(tempfile.mkdtemp(prefix="mvb-340-exp-"))
    wb = openpyxl.load_workbook(SRC); ws = wb.active
    for r in (18, 19, 20, 21):
        ws[f"J{r}"] = f'=CELL("format",F{r})'
    wb.save(tmp / "in.xlsx")
    prof = tmp / "profile"; (prof / "user").mkdir(parents=True)
    (prof / "user" / "registrymodifications.xcu").write_text('''<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupSystemLocale" oor:op="fuse"><value>ru-RU</value></prop></item>
</oor:items>
''')
    p = subprocess.Popen(["soffice", f"-env:UserInstallation=file://{prof}", "--headless", "--norestore", "--nologo",
                          "--accept=pipe,name=mvb340exp;urp;"])

    def pv(n, v):
        x = PropertyValue(); x.Name, x.Value = n, v; return x

    local = uno.getComponentContext()
    res = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(120):
        try:
            ctx = res.resolve("uno:pipe,name=mvb340exp;urp;StarOffice.ComponentContext"); break
        except Exception:
            time.sleep(0.5)
    smgr = ctx.ServiceManager
    desk = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    disp = smgr.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)
    try:
        doc = desk.loadComponentFromURL(uno.systemPathToFileUrl(str(tmp / "in.xlsx")), "_blank", 0, (pv("Hidden", True),))
        fr = doc.getCurrentController().getFrame()

        def t(a, s):
            disp.executeDispatch(fr, ".uno:GoToCell", "", 0, (pv("ToPoint", a),))
            disp.executeDispatch(fr, ".uno:EnterString", "", 0, (pv("StringName", s),))
        for r, rate in ((18, "0,05"), (19, "0,05%"), (20, "0,05 %")):
            t(f"B{r}", "29.07.2026"); t(f"C{r}", "05.09.2026"); t(f"E{r}", "240000"); t(f"F{r}", rate)
        t("B21", "29.07.2026"); t("C21", "05.09.2026"); t("E21", "240000"); t("F21", "0,05%"); t("F21", "0,05")
        doc.calculateAll()
        sh = doc.Sheets.getByIndex(0)
        c = lambda a: sh.getCellRangeByName(a)
        for r in (18, 19, 20, 21):
            print(r, "F", c(f"F{r}").getValue(), repr(c(f"F{r}").getString()), "G", c(f"G{r}").getString(),
                  "H", c(f"H{r}").getString(), "CELL", c(f"J{r}").getString())
        print("E18", repr(c("E18").getString()), "B18", repr(c("B18").getString()), c("B18").getValue())
        doc.close(True)
    finally:
        desk.terminate(); p.wait(30)
        shutil.rmtree(tmp, ignore_errors=True)
