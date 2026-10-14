"""Apply deterministic A4/print metadata and build non-buyer scenario fixtures."""
import json,os,shutil
from datetime import datetime
from pathlib import Path
import openpyxl
from openpyxl.workbook.properties import CalcProperties
ROOT=Path(__file__).resolve().parent
CAND=ROOT/"candidate"
STATE=Path("/home/denis/.local/state/claude-dispatcher/coordinator/2026-10-14-p3-subject-remediation/unit-c-xlsx02-06")
def atomic_json(path,data):
    tmp=path.with_suffix(path.suffix+".tmp")
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2,default=str);f.write("\n");f.flush();os.fsync(f.fileno())
    os.replace(tmp,path);fd=os.open(path.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
def setup(name,main,last_col,last_row,data_row_height=None):
    p=CAND/name;wb=openpyxl.load_workbook(p)
    ws=wb[main]
    ws.sheet_view.showGridLines=False
    ws.auto_filter.ref=f"A4:{last_col}{last_row}"
    ws.print_area=f"A1:{last_col}{last_row}"
    ws.print_title_rows="4:4"
    if data_row_height is not None:
        for row in range(5,last_row+1):
            ws.row_dimensions[row].height=data_row_height
    ws.page_setup.orientation="landscape"
    ws.page_setup.paperSize=ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth=1;ws.page_setup.fitToHeight=0
    ws.sheet_properties.pageSetUpPr.fitToPage=True
    ws.page_margins.left=0.25;ws.page_margins.right=0.25;ws.page_margins.top=0.35;ws.page_margins.bottom=0.35
    ins=wb["Инструкция"]
    ins.print_area="A1:B7";ins.page_setup.paperSize=ins.PAPERSIZE_A4
    ins.page_setup.orientation="portrait";ins.page_setup.fitToWidth=1;ins.page_setup.fitToHeight=1
    ins.sheet_properties.pageSetUpPr.fitToPage=True
    if wb.calculation is None:
        wb.calculation=CalcProperties()
    wb.calculation.fullCalcOnLoad=True;wb.calculation.forceFullCalc=True;wb.calculation.calcMode="auto"
    wb.save(p)
setup("02-reestr-prilozheniy.xlsx","Реестр приложений","I",54,21)
setup("06-zhurnal-peredachi.xlsx","Журнал передачи комплекта КС","L",54)
fx=STATE/"scenario-fixtures";fx.mkdir(exist_ok=True)
for p in fx.glob("*.xlsx"): p.unlink()
# 02 fixture
p=CAND/"02-reestr-prilozheniy.xlsx";wb=openpyxl.load_workbook(p);ws=wb["Реестр приложений"]
cases02=[
 ("blank",{},""),
 ("blank_date",{"B":"АОСР — акт освидетельствования скрытых работ","C":"АОСР-1","E":3,"F":"Приложено","H":"Да"},"ЗАПОЛНИТЬ"),
 ("text_date",{"B":"АОСР — акт освидетельствования скрытых работ","C":"АОСР-1","D":"не дата","E":3,"F":"Приложено","H":"Да"},"ЗАПОЛНИТЬ"),
 ("complete",{"B":"АОСР — акт освидетельствования скрытых работ","C":"АОСР-1","D":datetime(2026,10,1),"E":3,"F":"Приложено","H":"Да"},"ГОТОВО"),
 ("not_required",{"B":"Иное приложение","C":"N/A","D":datetime(2026,10,1),"E":1,"F":"Не требуется","G":"По договору не применяется","H":"Да"},"ПРОВЕРИТЬ ОСНОВАНИЕ"),
 ("not_checked",{"B":"КС-2 — акт о приёмке выполненных работ","C":"КС-2-1","D":datetime(2026,10,1),"E":2,"F":"Приложено","H":"Нет"},"НЕ ГОТОВО"),
]
for i,(case,vals,expected) in enumerate(cases02,5):
    for col,v in vals.items(): ws[f"{col}{i}"]=v
out=fx/"02-scenarios.xlsx";wb.save(out)
# 06 fixture
p=CAND/"06-zhurnal-peredachi.xlsx";wb=openpyxl.load_workbook(p);ws=wb["Журнал передачи комплекта КС"]
base={"B":datetime(2026,10,1),"C":"КС-2-1","D":"КС-3-1","E":"Иванов И.И.","F":"Инженер","G":8,"H":"ЭДО"}
cases06=[
 ("blank",{},""),
 ("blank_date",{"C":"КС-2-1","D":"КС-3-1","E":"Иванов И.И.","F":"Инженер","G":8,"H":"ЭДО","I":"Принято"},"ЗАПОЛНИТЬ"),
 ("return_missing",dict(base,I="Возврат"),"УКАЗАТЬ ВОЗВРАТ"),
 ("return_before",dict(base,I="Возврат",J=datetime(2026,9,30),K="Исправить"),"УКАЗАТЬ ВОЗВРАТ"),
 ("return_complete",dict(base,I="Возврат",J=datetime(2026,10,2),K="Исправить"),"ВОЗВРАТ ЗАФИКСИРОВАН"),
 ("accepted",dict(base,I="Принято"),"ЗАКРЫТО"),
 ("review",dict(base,I="На проверке"),"В РАБОТЕ"),
 ("missing_recipient",dict(base,E="",I="Принято"),"ЗАПОЛНИТЬ"),
]
for i,(case,vals,expected) in enumerate(cases06,5):
    for col,v in vals.items(): ws[f"{col}{i}"]=v
out=fx/"06-scenarios.xlsx";wb.save(out)
atomic_json(STATE/"scenario-map.json",{"02":[{"row":i,"case":c,"expected":e} for i,(c,v,e) in enumerate(cases02,5)],"06":[{"row":i,"case":c,"expected":e} for i,(c,v,e) in enumerate(cases06,5)]})
print("POSTPROCESS_AND_FIXTURES_READY")
