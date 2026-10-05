import json, os, subprocess, datetime as dt, openpyxl
RUN = os.path.dirname(os.path.abspath(__file__))
SRC = {'new': '/home/denis/.local/state/claude-dispatcher/recovery-20261004/owner-native-union-20261005-1420/04-owner-layout-accepted-calculation.xlsx', 'old': '/home/denis/.local/state/claude-dispatcher/recovery-20261004/owner-native-union-20261005-1420/old04.xlsx'}
K = "Отдельный платёж — не сам аванс (сверено с выпиской банка)"
D = lambda m, d: dt.datetime(2026, m, d)
base = [(D(6,30),"Начисление по акту","КС-2 № 7",700000,"АКТ-7",None),(D(7,31),"Начисление по акту","КС-2 № 8",450000,"АКТ-8",None),
        (D(6,30),"Зачёт аванса по договору","Договор ПД-07/2026 аванс",150000,"АКТ-7",None),
        (D(8,20),"Оплата","п/п № 101",200000,"АКТ-7",None),(D(9,10),"Оплата","п/п № 102",100000,"АКТ-8",None)]
sc = {"B2": base + [(D(5,12),"Оплата","п/п № 877 (аванс)",150000,"АКТ-7",None)],
      "L1c": base + [(D(9,18),"Оплата","п/п № 300",150000,"АКТ-8",K)]}
prof = "file://" + RUN + "/lo-profile"
os.makedirs(RUN + "/lo-profile/user", exist_ok=True)
open(RUN + "/lo-profile/user/registrymodifications.xcu", "w").write('<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item></oor:items>')
res = {}
for ver, src in SRC.items():
    for name, rows in sc.items():
        wb = openpyxl.load_workbook(src)
        da, vz = wb["Долг по актам"], wb["Взаиморасчёты"]
        da["B5"], da["C5"], da["D5"] = "АКТ-7", "КС-2 № 7 от 30.06.2026", D(7,30)
        da["B6"], da["C6"], da["D6"] = "АКТ-8", "КС-2 № 8 от 31.07.2026", D(8,31)
        for i, (b,c,d,e,f,k) in enumerate(rows):
            r = 5 + i
            for col, v in zip("BCDEF", (b,c,d,e,f)): vz[f"{col}{r}"] = v
            if k: vz[f"K{r}"] = k
        fx = f"{RUN}/fx-{ver}-{name}.xlsx"; wb.save(fx)
        od = f"{RUN}/calc-{ver}"; os.makedirs(od, exist_ok=True)
        subprocess.run(["soffice", f"-env:UserInstallation={prof}", "--headless", "--convert-to", "xlsx", "--outdir", od, fx], check=True, capture_output=True, timeout=90)
        v = openpyxl.load_workbook(f"{od}/fx-{ver}-{name}.xlsx", data_only=True)
        z, a = v["Взаиморасчёты"], v["Долг по актам"]
        res[f"{ver}-{name}"] = {"I": [z[f"I{r}"].value for r in range(5, 5 + len(rows))],
                                "M4_M15": [z[f"M{r}"].value for r in range(4, 16)],
                                "acts_H_J_M_O": [[a[f"{c}{r}"].value for c in "HJMO"] for r in (5, 6)],
                                "C3_all": {s.title: s["C3"].value for s in v.worksheets if s["C3"].value is not None}}
for name in sc:
    res[f"old_vs_new_identical_{name}"] = res[f"old-{name}"] == res[f"new-{name}"]
open(RUN + "/calc.json", "w").write(json.dumps(res, ensure_ascii=False, indent=1, default=str))
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
