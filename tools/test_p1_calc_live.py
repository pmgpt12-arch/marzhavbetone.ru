#!/usr/bin/env /usr/bin/python3
"""Живой Calc fixture P1: частичная оплата меняет базу со следующего дня."""
from datetime import date
from pathlib import Path
import os
import subprocess
import sys
import time
import uno

ROOT = Path(__file__).resolve().parents[1]
FILE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (ROOT / "products-storage/01-zakrytie-rabot/14-raschet-procentov-395-gk.xlsx")
PORT = 21000 + os.getpid() % 10000
PROFILE = f"file:///tmp/lo-p1-live-fixture-{os.getpid()}"
cmd = ["libreoffice", f"-env:UserInstallation={PROFILE}", "--headless",
       f"--accept=socket,host=localhost,port={PORT};urp;StarOffice.ComponentContext",
       "--norestore", "--nodefault", "--nofirststartwizard"]
proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
try:
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    deadline = time.monotonic() + 12
    while True:
        try:
            ctx = resolver.resolve(
                f"uno:socket,host=localhost,port={PORT};urp;StarOffice.ComponentContext")
            break
        except Exception:
            if time.monotonic() > deadline or proc.poll() is not None:
                raise RuntimeError("LibreOffice UNO did not become ready within 12 seconds")
            time.sleep(0.2)
    desktop = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)
    hidden = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    hidden.Name, hidden.Value = "Hidden", True
    doc = desktop.loadComponentFromURL(FILE.as_uri(), "_blank", 0, (hidden,))
    if doc is None:
        raise RuntimeError("workbook did not open")
    def serial(y, m, d):
        return (date(y, m, d) - date(1899, 12, 30)).days
    def put(sheet, cell, value):
        sheet.getCellRangeByName(cell).setValue(value)
    source = doc.Sheets.getByName("Входные данные")
    calc = doc.Sheets.getByName("Расчёт")
    result = doc.Sheets.getByName("Итог для документа")
    put(source, "B4", 1000)
    put(source, "B5", serial(2024, 1, 1))
    put(source, "B6", serial(2024, 1, 3))
    put(source, "A12", serial(2024, 1, 1))
    put(source, "B12", 36.5)
    put(source, "A35", serial(2024, 1, 2))
    put(source, "B35", 200)
    put(calc, "A4", serial(2024, 1, 1))
    put(calc, "B4", serial(2024, 1, 2))
    put(calc, "A5", serial(2024, 1, 3))
    put(calc, "B5", serial(2024, 1, 3))
    doc.calculateAll()
    def number(sheet, cell):
        return sheet.getCellRangeByName(cell).getValue()
    def string(sheet, cell):
        return sheet.getCellRangeByName(cell).getString()
    observed = {"base_before": number(calc, "D4"),
                "base_after": number(calc, "D5"),
                "days_before": number(calc, "C4"),
                "days_after": number(calc, "C5"),
                "year_days": number(calc, "F4"),
                "interest_before": number(calc, "G4"),
                "interest_after": number(calc, "G5"),
                "interest_total": number(result, "B10"),
                "period_check_1": string(calc, "H4"),
                "period_check_2": string(calc, "H5")}
    print(observed)
    expected = {"base_before": 1000, "base_after": 800,
                "days_before": 2, "days_after": 1, "year_days": 366,
                "interest_before": 1.99, "interest_after": 0.80,
                "interest_total": 2.79, "period_check_1": "", "period_check_2": ""}
    assert observed == expected, f"Calc fixture differs: expected {expected}"
    put(calc, "A5", serial(2024, 1, 4))
    put(calc, "B5", serial(2024, 1, 4))
    doc.calculateAll()
    assert "пропущен или перекрыт" in string(calc, "H5")
    print("P1 live Calc: payment timing, leap year, total, and gap warning PASS")
    doc.close(True)
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
