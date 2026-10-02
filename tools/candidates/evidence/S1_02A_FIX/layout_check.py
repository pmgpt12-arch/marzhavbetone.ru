"""Writer: слова заголовков изменённых таблиц (05 табл. 1, 09 табл. п. 1, 06, 10 А)
не рвутся посередине. Ищет каждое слово длиной от 6 букв в тексте PDF."""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import test_s1_candidate as T  # noqa: E402

ФАЙЛЫ = ["05-peregovory-i-perenos-sroka.docx", "06-uvedomlenie-o-prosrochke.docx", "09-pretenziya.docx",
         "10-obrashchenie-v-sud.docx", "03-algoritm-dejstviy.docx"]
tmp = Path(tempfile.mkdtemp(prefix="s1-layout-"))
try:
    subprocess.run(["soffice", f"-env:UserInstallation=file://{tmp}/profile", "--headless", "--norestore",
                    "--convert-to", "pdf", "--outdir", str(tmp), *[str(T.C / f) for f in ФАЙЛЫ]],
                   check=True, capture_output=True, timeout=600)
    for f in ФАЙЛЫ:
        pdf = tmp / f.replace(".docx", ".pdf")
        txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        слова_pdf = set(re.findall(r"[А-Яа-яЁё]+", txt))
        слова_docx = {w for w in re.findall(r"[А-Яа-яЁё]{6,}", T.docx_text(T.C / f))}
        разрывы = sorted(w for w in слова_docx if w not in слова_pdf)
        стр = re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout).group(1)
        print(f"{f}: {стр} стр.; слов ≥6 букв: {len(слова_docx)}; не найдено целиком в PDF: {len(разрывы)} {разрывы[:10]}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
