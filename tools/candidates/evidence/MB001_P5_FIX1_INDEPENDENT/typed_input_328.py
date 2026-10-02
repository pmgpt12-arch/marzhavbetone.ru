#!/usr/bin/env python3
"""#328: ввод с «клавиатуры» в Calc через UNO-диспетчер (.uno:EnterString).

Строки вводятся так, как их набирает покупатель в русской локали: «0,05»,
«01.03.2026», «0,05%», «24.05.2026». Разбор строки делает сам Calc (тот же
путь, что набор в ячейке), локаль профиля — ru-RU. Отдельный временный
профиль LibreOffice, книги — копии из каталога acceptance_328.py.

Запуск: python3 typed_input_328.py <каталог копий acceptance_328.py>
"""
import subprocess
import sys
import time
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue

каталог = Path(sys.argv[1]).resolve()
профиль = каталог / "lo-profile-328-uno"
труба = "mvb328uno"
proc = subprocess.Popen(["soffice", f"-env:UserInstallation=file://{профиль}", "--headless",
                         "--norestore", "--nologo", f"--accept=pipe,name={труба};urp;"])


def pv(n, v):
    p = PropertyValue()
    p.Name, p.Value = n, v
    return p


try:
    ctx = None
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            ctx = resolver.resolve(f"uno:pipe,name={труба};urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(0.5)
    smgr = ctx.ServiceManager
    # Локаль ввода — ru-RU, как у покупателя
    cp = smgr.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", ctx)
    upd = cp.createInstanceWithArguments("com.sun.star.configuration.ConfigurationUpdateAccess",
                                         (pv("nodepath", "/org.openoffice.Setup/L10N"),))
    upd.setPropertyValue("ooSetupSystemLocale", "ru-RU")
    upd.commitChanges()
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    disp = smgr.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)

    def набрать(doc, ввод):
        frame = doc.getCurrentController().getFrame()
        for адрес, строка in ввод:
            disp.executeDispatch(frame, ".uno:GoToCell", "", 0, (pv("ToPoint", адрес),))
            disp.executeDispatch(frame, ".uno:EnterString", "", 0, (pv("StringName", строка),))
        doc.calculateAll()

    def значение(doc, адрес):
        c = doc.Sheets.getByIndex(0).getCellRangeByName(адрес)
        return c.getString(), c.getValue(), c.NumberFormat

    src04 = каталог / "zip" / "04-raschet-ubytkov.xlsx"
    doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(src04)), "_blank", 0, ())
    набрать(doc, [("B18", "29.07.2026"), ("C18", "05.09.2026"), ("E18", "240000"), ("F18", "0,05"),
                  ("B19", "29.07.2026"), ("C19", "05.09.2026"), ("E19", "240000"), ("F19", "0,05%")])
    # Показ (getString) после смены локали в работающем процессе может
    # путать разделители; доказательство — число (getValue).
    print("04 набор: строка 18 «0,05»  → D18 %r, F18 %r, G18 = %r, H18 %r" % (
        значение(doc, "D18")[1], значение(doc, "F18")[1], значение(doc, "G18")[1], значение(doc, "H18")[0]))
    print("04 набор: строка 19 «0,05%%» → F19 %r, G19 = %r, H19 %r" % (
        значение(doc, "F19")[1], значение(doc, "G19")[1], значение(doc, "H19")[0]))
    print("04 набор: итог пени G23 = %r, H23 %r" % (значение(doc, "G23")[1], значение(doc, "H23")[0]))
    doc.close(True)

    src05 = каталог / "zip" / "05-reestr-uderzhaniy.xlsx"
    doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(src05)), "_blank", 0, ())
    набрать(doc, [("G3", "24.04.2026"), ("J3", "24.05.2026"), ("E3", "25000")])
    for a in ("G3", "J3", "E21"):
        print("05 набор: %s → показ %r, число %r" % (a, значение(doc, a)[0], значение(doc, a)[1]))
    out = каталог / "05-typed.pdf"
    doc.storeToURL(uno.systemPathToFileUrl(str(out)), (pv("FilterName", "calc_pdf_Export"),))
    doc.close(True)
    print("05 набор: PDF", out)
finally:
    try:
        desktop.terminate()
    except Exception:
        pass
    proc.wait(timeout=30)
