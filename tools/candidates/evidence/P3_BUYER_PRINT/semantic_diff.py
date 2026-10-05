"""Семантика 03 до/после: старый генератор воспроизводит старый 03; в новом
document.xml, если убрать <w:cantSplit/> и новый абзац «Перед печатью…»,
байт в байт совпадает со старым. Остальные части архива — байт в байт."""
import hashlib, importlib.util, re, sys, types, zipfile
from pathlib import Path

RUN = Path(__file__).resolve().parent
OLD, NEW = Path(sys.argv[1]), Path(sys.argv[2])

for name in ("reportlab", "reportlab.pdfgen", "reportlab.pdfgen.canvas",
             "reportlab.lib", "reportlab.lib.pagesizes", "reportlab.lib.units"):
    sys.modules[name] = types.ModuleType(name)
sys.modules["reportlab.pdfgen"].canvas = sys.modules["reportlab.pdfgen.canvas"]
sys.modules["reportlab.lib.pagesizes"].A4 = (595.27, 841.89)
sys.modules["reportlab.lib.units"].cm = 28.3465
spec = importlib.util.spec_from_file_location("old05", RUN / "old-build_paid_05.py")
old05 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old05)
regen = RUN / "rebuild" / "03-old-generator.docx"
old05.build_aosr_forms(str(regen))
h = lambda b: hashlib.sha256(b).hexdigest()
print("old generator -> old 03 byte-identical:", regen.read_bytes() == OLD.read_bytes())

zo, zn = zipfile.ZipFile(OLD), zipfile.ZipFile(NEW)
print("parts equal list:", zo.namelist() == zn.namelist())
for part in zo.namelist():
    if part != "word/document.xml":
        print(f"  {part}: {'SAME' if zo.read(part) == zn.read(part) else 'DIFF'}")
xo = zo.read("word/document.xml").decode()
xn = zn.read("word/document.xml").decode()
print("cantSplit old/new:", xo.count("<w:cantSplit/>"), xn.count("<w:cantSplit/>"),
      "rows old/new:", len(re.findall(r"<w:tr[ >]", xo)), len(re.findall(r"<w:tr[ >]", xn)))
stripped = xn.replace("<w:cantSplit/>", "")
paras = [m for m in re.finditer(r"<w:p>(?:(?!</w:p>).)*?Перед печатью для подписания\..*?</w:p>", stripped, re.S)]
print("new paragraphs found:", len(paras))
m = paras[-1]
added = re.sub(r"<[^>]+>", "", m.group(0))
reduced = stripped[:m.start()] + stripped[m.end():]
print("document.xml minus cantSplit minus new paragraph == old:", reduced == xo)
print("added text:", added)
