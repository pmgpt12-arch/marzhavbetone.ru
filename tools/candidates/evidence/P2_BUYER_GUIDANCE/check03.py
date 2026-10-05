"""Проверки результата: страницы и остатки в PDF фикстур, сверка текста
инструкции DOCX ↔ поставленный PDF ↔ Writer-PDF, PNG для просмотра, sha256."""
import hashlib
import re
import subprocess
import zipfile
from pathlib import Path

RUN = Path(__file__).parent
WT = Path("/home/denis/projects/marzhavbetone.ru/.worktrees/codex-correction-388-20261005")
KIT = WT / "products-storage/02-dopraboty-bez-poter"
(RUN / "png").mkdir(exist_ok=True)


def pdftext(p):
    return subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(p), "-"],
                          capture_output=True, text=True, check=True).stdout


def pages(p):
    out = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", out).group(1))


def flat(t):
    return re.sub(r"\s+", " ", t.replace("­", "")).strip()


BAD = re.compile(r"\[[^\]]*\]| / |МАРЖА В БЕТОНЕ|РАБОЧИЙ ШАБЛОН|Контроль перед|"
                 r"Важно: шаблон|marzhavbetone|подсказк|Заполните|для случая|"
                 r"случай [АБ]|python", re.I)
for case, other in (("A", ["выполнена с", "по просьбе", "Приложения"]),
                    ("B", ["выявлена", "Режим до решения", "Работа не начинается",
                           "выполняются только"])):
    pdf = RUN / f"pdf/{case}-03-uvedomlenie-o-doprabotah.pdf"
    t = flat(pdftext(pdf))
    print(case, "pages", pages(pdf), "bad", BAD.findall(t),
          "other-variant", [s for s in other if s in t])
    subprocess.run(["pdftoppm", "-r", "70", "-png", str(pdf), str(RUN / f"png/{case}-03")], check=True)

# инструкция: каждый абзац DOCX есть в поставленном PDF и в Writer-PDF
with zipfile.ZipFile(KIT / "00-INSTRUKCIYA.docx") as z:
    xml = z.read("word/document.xml").decode()
paras = [flat(re.sub(r"<[^>]+>", "", "".join(re.findall(r"<w:t[^>]*>[^<]*</w:t>", p))))
         for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)]
paras = [p.replace("&quot;", '"').replace("&amp;", "&") for p in paras if p]
for name, pdf in (("delivered", KIT / "00-INSTRUKCIYA.pdf"), ("writer", RUN / "pdf/00-INSTRUKCIYA.pdf")):
    t = flat(subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"],
                            capture_output=True, text=True).stdout)
    # номера шагов DOCX пишет текстом, PDF reportlab — маркером списка
    miss = [p for p in paras if re.sub(r"^\d+\. ", "", p) not in t]
    print(name, "pages", pages(pdf), "docx paragraphs", len(paras), "missing", len(miss))
    for m in miss:
        print("   MISSING:", m[:120])
    subprocess.run(["pdftoppm", "-r", "60", "-png", str(pdf), str(RUN / f"png/00-{name}")], check=True)

for f in sorted(KIT.iterdir()):
    print(hashlib.sha256(f.read_bytes()).hexdigest(), f.name)
for f in sorted((RUN / "filled").iterdir()) + sorted((RUN / "pdf").iterdir()):
    print(hashlib.sha256(f.read_bytes()).hexdigest(), f.relative_to(RUN))
