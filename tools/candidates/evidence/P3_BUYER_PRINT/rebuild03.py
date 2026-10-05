"""Пересборка ТОЛЬКО файла 03 генератором из worktree.

reportlab не установлен и не ставится: только на этот прогон подложена
заглушка (stub/reportlab) — PDF 08 не собирается, утверждений о нём нет.
Сначала собирает в run dir, затем (с флагом --install) копирует в выдачу.
"""
import hashlib, importlib.util, shutil, sys, types
from pathlib import Path

RUN = Path(__file__).resolve().parent
WT = Path(sys.argv[1])
KIT = WT / "products-storage" / "05-ks-bez-vozvrata"

# заглушка reportlab: только имена, которые импортирует генератор
for name in ("reportlab", "reportlab.pdfgen", "reportlab.pdfgen.canvas",
             "reportlab.lib", "reportlab.lib.pagesizes", "reportlab.lib.units"):
    sys.modules[name] = types.ModuleType(name)
sys.modules["reportlab.pdfgen"].canvas = sys.modules["reportlab.pdfgen.canvas"]
sys.modules["reportlab.lib.pagesizes"].A4 = (595.27, 841.89)
sys.modules["reportlab.lib.units"].cm = 28.3465

spec = importlib.util.spec_from_file_location("bp05", WT / "products-storage" / "build_paid_05.py")
bp05 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp05)

out = RUN / "rebuild" / "03-akt-skrytyh-rabot.docx"
out.parent.mkdir(exist_ok=True)
bp05.build_aosr_forms(str(out))
again = RUN / "rebuild" / "03-second-run.docx"
bp05.build_aosr_forms(str(again))
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
print("old ", h(KIT / "03-akt-skrytyh-rabot.docx"))
print("new ", h(out))
print("run2", h(again), "deterministic" if h(again) == h(out) else "NOT DETERMINISTIC")
if "--install" in sys.argv:
    shutil.copyfile(out, KIT / "03-akt-skrytyh-rabot.docx")
    print("installed", h(KIT / "03-akt-skrytyh-rabot.docx"))
