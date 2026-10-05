"""Н-6: печать листа «Взаиморасчёты» С-1 (три операции) в PDF через Calc.
(1) весь лист как есть; (2) эмуляция «только выделенное» — область печати
A1:J7 (шапка + три строки, колонки A–J). Действие в интерфейсе Calc этим не
проверяется — только то, что даёт такая область. Запуск: python3 … <scratch>"""
import re
import subprocess
import sys
from pathlib import Path

import openpyxl

S = Path(sys.argv[1]).resolve()
src = S / "walk" / "С-1" / "fill" / "04.xlsx"
out = S / "print"
out.mkdir(exist_ok=True)
for name, area in (("whole", None), ("selection", "A1:J7")):
    wb = openpyxl.load_workbook(src)
    for t in [n for n in wb.sheetnames if n != "Взаиморасчёты"]:
        del wb[t]
    if area:
        wb["Взаиморасчёты"].print_area = area
    p = out / f"{name}.xlsx"
    wb.save(p)
    subprocess.run(["soffice", f"-env:UserInstallation=file://{S}/lo-profile", "--headless", "--norestore",
                    "--convert-to", "pdf", "--outdir", str(out), str(p)], capture_output=True, timeout=300, check=True)
    pdf = out / f"{name}.pdf"
    pages = re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout).group(1)
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    print(f"{name}: {pages} стр.; вхождений «900» (нарастающий итог/свод): {len(re.findall(r'900[ .,]?000', txt))}")
