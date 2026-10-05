"""Issue #337: минимальные воспроизводимые доказательства приёмки паспорта
tools/candidates/MB001_VALUE_PASSPORTS_A.md (Draft PR #336 @ b5e284e).

Только чтение: продукты, страницы и генераторы не меняются. Текст docx
читает LibreOffice во временный каталог, который удаляется.

Запуск из корня репозитория:
    python3 tools/candidates/evidence/MB001_VALUE_A_REVIEW/verify.py
Вывод этого запуска сохранён рядом в verify.out.
"""
import hashlib
import html
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, check=True).stdout.strip())
PS = ROOT / "products-storage"
P2 = PS / "02-dopraboty-bez-poter"
P3 = PS / "05-ks-bez-vozvrata"
P4 = PS / "08-pto-bez-zamechaniy"
TMP = Path(tempfile.mkdtemp())


def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return (r.stdout + r.stderr).strip()


def hdr(title):
    print(f"\n=== {title} ===")


def docx_text(path):
    out = TMP / (path.stem + ".txt")
    subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text", "--outdir", str(TMP), str(path)],
                   capture_output=True)
    return out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""


def pdf_text(path):
    return sh("pdftotext", "-layout", str(path), "-")


def grep(text, pattern):
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(pattern, line):
            print(f"  {i}: {line.strip()[:160]}")


def sheets(path):
    with zipfile.ZipFile(path) as z:
        return "".join(z.read(n).decode("utf-8") for n in z.namelist()
                       if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))


def formulas(path):
    xml = html.unescape(sheets(path))
    cells = re.findall(r'<c r="([A-Z]+\d+)"[^>]*>(?:<f[^>]*>([^<]*)</f>|<f[^>]*/>)', xml)
    f = [c for c in cells]
    shapes = {}
    for _, expr in f:
        k = re.sub(r"\d+", "N", expr)
        shapes[k] = shapes.get(k, 0) + 1
    print(f"  {path.relative_to(ROOT)}: formulas={len(f)} "
          f"dataValidation={xml.count('<dataValidation ')} "
          f"conditionalFormatting={xml.count('<conditionalFormatting')} shapes={shapes}")
    return f


hdr("1. SHA входов")
for ref in ["HEAD", "origin/main", "origin/claude/issue-329", "b5e284e^"]:
    print(f"  {ref:24} {sh('git', 'rev-parse', ref)}")
print(sh("git", "diff", "--stat", "origin/main", "b5e284e01ef731c81e976399a9786823cfc0ffad"))

hdr("2. Головы PR из паспорта и remote heads")
for s, pr in [("82a051e", "#312"), ("c7f1e87", "#314"), ("e414b41", "#316"),
              ("c5e8461", "#300"), ("bde8b79", "#317")]:
    t = subprocess.run(["git", "cat-file", "-t", s], capture_output=True, text=True, cwd=ROOT)
    print(f"  {pr} {s}: {t.stdout.strip() or 'missing'}")
print(sh("git", "for-each-ref", "--format=  %(refname:short) %(objectname:short)", "refs/remotes/origin"))
print("  ветки с bde8b79:", " ".join(sh("git", "branch", "-a", "--contains", "bde8b79").split()))

hdr("3. SHA-256 файлов §0.4 паспорта")
for p in [P4 / "31-pyat-aktov-skrytyh-rabot.docx", P4 / "32-shablon-ispolnitelnoy-shemy.docx",
          P4 / "03-perechen-vozmozhnyh-zamechaniy.docx", P4 / "08-algoritm-raboty-s-id.pdf",
          P4 / "09-krasnye-flagi.docx", P2 / "00-INSTRUKCIYA.pdf", P2 / "07-raschet-stoimosti.xlsx",
          P3 / "03-akt-skrytyh-rabot.docx", P3 / "10-sravnitelnaya-tablica.docx"]:
    print(f"  {hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(PS)}")

hdr("4. Состав выдачи (число файлов без MANIFEST/START-HERE/письма)")
for d in (P2, P3, P4):
    work = [f.name for f in sorted(d.iterdir())
            if f.name not in ("MANIFEST.md", "00-START-HERE.txt", "00-PISMO-POSLE-POKUPKI.txt")]
    print(f"  {d.name}: {len(work)}")

hdr("5. P4 31 и 32: текст документа")
for name in ["31-pyat-aktov-skrytyh-rabot.docx", "32-shablon-ispolnitelnoy-shemy.docx"]:
    t = docx_text(P4 / name)
    print(f"  --- {name}: непустых строк={sum(1 for l in t.splitlines() if l.strip())} "
          f"полей [___]={len(re.findall(r'\[_+\]', t))} "
          f"'квадратных скобках'={t.count('квадратных скобках')}")
    for line in t.splitlines():
        if line.strip():
            print("   |", line.strip()[:150])

hdr("6. P4 08 (PDF) и 09: «30 дней», суд")
grep(pdf_text(P4 / "08-algoritm-raboty-s-id.pdf"), r"30 дней|суд|Взыщ|блокир|ведения")
t09 = docx_text(P4 / "09-krasnye-flagi.docx")
for pat in (r"через 30 дней", r"Суд взыщет", r"Закон на вашей стороне", r"3-го возврата",
            r"КС считается согласованной"):
    print(f"  P4 09 «{pat}»: {len(re.findall(pat, t09))}")

hdr("7. P4 03: колонка обоснований")
grep(docx_text(P4 / "03-perechen-vozmozhnyh-zamechaniy.docx"),
     r"ИСО 9001|МДС 81-35|160 ГК|5%|48\.13330")

hdr("8. Формулы xlsx")
for p in [P2 / "07-raschet-stoimosti.xlsx", P2 / "08-zhurnal-doprabot.xlsx",
          P3 / "02-reestr-prilozheniy.xlsx", P3 / "06-zhurnal-peredachi.xlsx",
          P4 / "06-reestr-zamechaniy.xlsx", P4 / "07-grafik-ustraneniya.xlsx",
          *sorted(P4.glob("3[5-8]-*.xlsx"))]:
    f = formulas(p)
    if p.name.startswith(("06-reestr", "07-grafik")) or "reestr-prilozheniy" in p.name:
        print("    ", f)
x6 = html.unescape(sheets(P4 / "06-reestr-zamechaniy.xlsx"))
for ref, body in re.findall(r'<c r="([A-Z]+\d+)"[^>]*>(.*?)</c>', x6):
    text = "".join(re.findall(r"<t[^>]*>([^<]*)</t>", body))
    if re.search(r"Всего|Открыто|Закрыто", text):
        print(f"  P4 06 {ref}: «{text}»")
for ref in ("F6", "G6", "H6", "H7", "I7"):
    m = re.search(rf'<c r="{ref}"[^>]*/>|<c r="{ref}"[^>]*>(.*?)</c>', x6)
    print(f"  P4 06 {ref}: {'нет ячейки' if not m else (m.group(1) or 'пусто')}")

hdr("9. P3 10: цена и обещания")
grep(docx_text(P3 / "10-sravnitelnaya-tablica.docx"), r"1 990|Окупаемост|30-40|5-10|15\+|автопровер")

hdr("10. P3 03: «5 типовых форм»")
for line in docx_text(P3 / "03-akt-skrytyh-rabot.docx").splitlines():
    if line.strip():
        print("   |", line.strip()[:150])

hdr("11. P2: START-HERE, инструкция, алгоритм")
grep((P2 / "00-START-HERE.txt").read_text(encoding="utf-8"), r"разводит|без бумаг|Взыскания")
grep(pdf_text(P2 / "00-INSTRUKCIYA.pdf"), r"^\s*\d+\.\s+[А-ЯЁ]")
alg = pdf_text(P2 / "10-algoritm-doprabot.pdf")
print(f"  10-algoritm: непустых строк={sum(1 for l in alg.splitlines() if l.strip())}")
grep(alg, r"закрывающ")

hdr("12. Страницы: обещания")
pages = {"p2": "products/p2-dopolnitelnye-raboty.html", "p3": "products/p3-shablony-ks2-ks3.html",
         "p4": "products/p4-ispolnitelnaya-dokumentaciya-pto.html"}
pats = {"p2": r"15 готовых файлов|сметных норм|разделяет одно от другого|до получения денег|ежедневной фиксации",
        "p3": r"10 документов|реестр сверки объ|подсказки по каждой графе|Сравнительная таблица",
        "p4": r"5 заготовок|геодезических данных|Порядок ведения ИД|Признаки проблем|погоды"}
for k, path in pages.items():
    page = html.unescape(re.sub(r"<[^>]+>", " ", (ROOT / path).read_text(encoding="utf-8")))
    for m in sorted(set(re.findall(rf"[^.]{{0,60}}(?:{pats[k]})[^.]{{0,60}}", page))):
        print(f"  {k}: …{' '.join(m.split())}…")

hdr("13. Бесплатные материалы, генератор, конфиг")
lines = (PS / "build_free_10.py").read_text(encoding="utf-8").splitlines()
for i in range(427, 431):
    print(f"  build_free_10.py:{i + 1}: {lines[i].strip()}")
grep(docx_text(PS / "00-free-dopy-ne-v-podarok/02-shema-fiksacii-porucheniya.docx"), r"свидетельск")
grep(docx_text(PS / "00-free-id-do-peredachi/03-prichiny-vozvrata-komplekta.docx"),
     r"ответственных конструкций|платном комплекте")
cfg = (ROOT / "products-config.php").read_text(encoding="utf-8").splitlines()
for n in (182, 183, 205):
    print(f"  products-config.php:{n}: {cfg[n - 1].strip()}")
for m in re.finditer(r"'(p2|p3|p4|t2)' => \[\s*'name'\s*=> '[^']*',\s*'price' => (\d+)",
                     "\n".join(cfg)):
    print(f"  {m.group(1)} price={int(m.group(2)) // 100} ₽")

hdr("14. MANIFEST P4 о 31/32; отчёты R2/R3")
grep((P4 / "MANIFEST.md").read_text(encoding="utf-8"), r"перечни полей|Решение по ним не принято")
grep((ROOT / "tools/candidates/MB001_R2_P4_COMPOSITION_REPORT.md").read_text(encoding="utf-8"),
     r"5 заготовок актов|R-5")
grep((ROOT / "tools/candidates/MB001_R2_P4_DOCUMENTS_R3.md").read_text(encoding="utf-8"),
     r"A30|P2-02|781207b42dee|2a3d7f5a84a7")
grep((ROOT / "tools/candidates/MB001_R026_P4_R4_IMPLEMENTATION.md").read_text(encoding="utf-8"),
     r"98cde059fdb3")

hdr("15. Решения владельца (memo) и спрос")
grep((ROOT / "tools/candidates/S1-EDITION-SKU-DECISION-MEMO.md").read_text(encoding="utf-8"),
     r"самостоятельн|прежних покупателей|покупателей нет")
print((ROOT / "data/seo/search-demand.csv").read_text(encoding="utf-8").strip())

hdr("16. Прочие точечные утверждения паспорта")
grep(pdf_text(P2 / "00-INSTRUKCIYA.pdf"), r"\b1[012]-|\b0[1-9]-|11|12")
for n in ("01-prikaz-na-dopobem", "02-soglasovanie-obema", "03-uvedomlenie-o-doprabotah",
          "04-akt-skrytyh-rabot", "05-izmenenie-srokov", "06-pismo-o-priostanovke",
          "11-dopsoglashenie-obem-i-cena", "12-dopsoglashenie-sroki-doprabot"):
    t = docx_text(P2 / f"{n}.docx")
    print(f"  P2 {n}: полей [___]={len(re.findall(r'\[_+\]', t))} "
          f"'добавьте по вашему договору'={'добавьте по вашему договору' in t.lower()}")
for n in ("09-checklist-fotofiksacii", "10-algoritm-doprabot"):
    t = pdf_text(P2 / f"{n}.pdf")
    print(f"  P2 {n}.pdf: непустых строк={sum(1 for l in t.splitlines() if l.strip())}")
x7 = html.unescape(sheets(P2 / "07-raschet-stoimosti.xlsx"))
print("  P2 07 'оранжевые':", "оранжев" in x7.lower(), " 'Итого с коэффициентом':", "Итого с коэффициентом" in x7)
print("  P2 07 ячеек I4..I103 с формулой:",
      len(re.findall(r'<c r="I\d+"[^>]*><f>', x7)))
x8 = html.unescape(sheets(P2 / "08-zhurnal-doprabot.xlsx"))
print("  P2 08 ячеек в строке шапки (первая строка с текстом):",
      len(re.findall(r'<c r="[A-Z]+1"', x8)), "/ строка 3:", len(re.findall(r'<c r="[A-Z]+3"', x8)))
free3 = docx_text(PS / "00-free-dopy-ne-v-podarok/03-shablon-uvedomleniya.docx")
paid3 = docx_text(P2 / "03-uvedomlenie-o-doprabotah.docx")
print(f"  непустых строк: бесплатный 03={sum(1 for l in free3.splitlines() if l.strip())} "
      f"платный 03={sum(1 for l in paid3.splitlines() if l.strip())}")
grep(free3, r"вправе отказаться")

p3_01 = docx_text(P3 / "01-proverochnyy-list-komplekta-ks.docx")
print(f"  P3 01 пунктов ☐={p3_01.count('☐')}")
grep(p3_01, r"КС-11|КС-4|бухгалтер|21\.101|СНиП")
grep(docx_text(P3 / "07-sroki-hraneniya.docx"), r"Постоянно|5 лет|424|572")
p3_09 = docx_text(P3 / "09-tipovye-oshibki.docx")
print(f"  P3 09 'Ошибка N'={len(re.findall(r'Ошибка \d+', p3_09))}")
grep(p3_09, r"полный комплект|бухгалтер")
grep(pdf_text(P3 / "08-algoritm-proverki.pdf"), r"^\s*\d+[.)]|письмо")

print(f"  P4 08 'ШАГ N'={len(re.findall(r'ШАГ \d+', pdf_text(P4 / '08-algoritm-raboty-s-id.pdf')))}")
for n in ("39-algoritm-zamechaniy", "40-ezhemesyachnaya-proverka"):
    t = pdf_text(P4 / f"{n}.pdf")
    print(f"  P4 {n}.pdf: непустых строк={sum(1 for l in t.splitlines() if l.strip())}")
grep(docx_text(P4 / "01-uvedomlenie-o-gotovnosti-id.docx"), r"считаться")
grep(docx_text(P4 / "04-pismo-na-zamechaniya.docx"), r"считаться")
grep(docx_text(P4 / "02-akt-priemki-id.docx"), r"КС-2|КС-3")
for n in ("33-akt-peredachi-komplekta-pto", "34-sluzhebnaya-zapiska"):
    print(f"  P4 {n}: полей [___]={len(re.findall(r'\[_+\]', docx_text(P4 / f'{n}.docx')))}")
x35 = html.unescape(sheets(P4 / "35-obshiy-zhurnal-rabot.xlsx"))
print("  P4 35 'Рабочий журнал производства работ':", "Рабочий журнал производства работ" in x35,
      " 'Условия':", "Условия" in x35, " 'погод':", "погод" in x35.lower())
print("  P4 00-INSTRUKCIYA есть:", any(P4.glob("00-INSTRUKCIYA*")))

art = html.unescape(re.sub(r"<[^>]+>", " ", (ROOT / "articles/dopraboty-bez-soglasheniya.html").read_text(encoding="utf-8")))
for pat in (r"Акт дополнительных работ", r"Что придётся доказывать", r"Если уже выполнили", r"162", r"743",
            r"№ ?51"):
    print(f"  статья допработ «{pat}»: {len(re.findall(pat, art))}")

for path, pat in [("tools/candidates/S1-EDITION-SKU-DECISION-MEMO.md", r"^#+ .*7|27\.09\.2026|29 900"),
                  ("tools/candidates/MB001_P5_CLAIMS_R2.md", r"G-1"),
                  ("tools/candidates/MB001_R2_P4_COMPOSITION_REPORT.md", r"^#+ |01\.08\.2026"),
                  ("tools/candidates/MB001_R2_P4_DOCUMENTS_R3.md", r"^#+ "),
                  ("products-storage/14-peredacha-id-pod-podpis/MANIFEST.md", r"юрист|R3"),
                  ("tools/test_delivery_artifacts.py", r"def test_p4_"),
                  ("tools/test_p4_buyer_documents.py", r"def test_"),
                  ("tools/check_packages.py", r"02-dopraboty|06-id-blokiruet|01-30-bazovye")]:
    p = ROOT / path
    print(f"  --- {path}: {'есть' if p.exists() else 'НЕТ ФАЙЛА'}")
    if p.exists():
        grep(p.read_text(encoding="utf-8"), pat)
print("  p6 копии:", sorted(x.name for x in (PS / "04-polnyy-komplekt-pto/01-30-bazovye-pakety").iterdir()
                            if x.name.startswith(("02-", "06-"))))
print("  build_preview:", sorted(str(p.relative_to(ROOT)) for p in ROOT.glob("tools/build_preview*")))
print("  merge #310:", sh("git", "log", "-1", "--format=%h %s%n%b", "64b210e"))

print("  P2 INSTRUKCIYA ветка «уже выполнены»:",
      len(re.findall(r"уже выполнен|без бумаг", pdf_text(P2 / "00-INSTRUKCIYA.pdf"))))
print("  P2 08 шапка:", [t for t in re.findall(r'<c r="[A-Z]+3"[^>]*>.*?<t[^>]*>([^<]*)</t>', x8)])
x302 = html.unescape(sheets(P3 / "02-reestr-prilozheniy.xlsx"))
print("  P3 02 F2..F4:", re.findall(r'<c r="F[2-4]"[^>]*>.*?<t[^>]*>([^<]*)</t>', x302))
s1 = ROOT / "tools/candidates/s1-oplata-za-raboty"
s1_09 = docx_text(s1 / "09-vnutrennyaya-proverka.docx")
print(f"  S1 09 (кандидат, не main-выдача): 'Где проверить'={s1_09.count('Где проверить')} "
      f"'КС-3'={s1_09.count('КС-3')} 'журнал'={s1_09.lower().count('журнал')}")
grep(s1_09, r"^\s*(Раздел|[АБ]\.)")
grep(docx_text(s1 / "10-peredacha-i-zamechaniya.docx"), r"^\s*(Раздел|[АБ]\.)")
p4page = html.unescape(re.sub(r"<[^>]+>", " ", (ROOT / pages["p4"]).read_text(encoding="utf-8")))
print("  p4 «На выходе»:", " ".join(re.findall(r"На выходе.{0,160}", " ".join(p4page.split()))[:1]))

hdr("17. Тесты")
print(sh("python3", "-m", "pytest", "tools/test_p4_buyer_documents.py", "-q").splitlines()[-1])
print(sh("python3", "-m", "pytest", "tools/test_delivery_artifacts.py", "-q").splitlines()[-1])

for f in TMP.iterdir():
    f.unlink()
TMP.rmdir()
