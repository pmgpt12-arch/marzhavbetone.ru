"""Покупатель выполняет новое указание п. 9 «Как пользоваться» на заполненной копии:
оставляет форму N от таблицы «Объект…» до таблицы «Подписи» включительно и
удаляет три названные курсивные строки. Источник только читается."""
import sys
from docx import Document

SRC, OUT, FORM = sys.argv[1], sys.argv[2], int(sys.argv[3])
REMOVE = ("Поля комплекта (в рекомендуемый образец не входят)",
          "Номер в национальном реестре специалистов указывают",
          "Если документов больше пяти")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
d = Document(SRC)
body = d.element.body
kids = [k for k in body.iterchildren() if k.tag != f"{W}sectPr"]
text = lambda el: "".join(t.text or "" for t in el.iter(f"{W}t")).strip()
start_heading = next(i for i, k in enumerate(kids) if text(k).startswith(f"Форма {FORM}. "))
first = next(i for i in range(start_heading, len(kids)) if kids[i].tag == f"{W}tbl")
last = next(i for i in range(first, len(kids)) if kids[i].tag == f"{W}tbl"
            and text(kids[i]).startswith("ПредставительДолжность, Ф. И. О.Подпись"))
keep = set(range(first, last + 1))
removed_inside = []
for i in sorted(keep):
    if kids[i].tag == f"{W}p" and text(kids[i]).startswith(REMOVE):
        removed_inside.append(text(kids[i])[:60])
        keep.discard(i)
for i, k in enumerate(kids):
    if i not in keep:
        body.remove(k)
d.save(OUT)
print("kept nodes:", len(keep), "removed inside form:", removed_inside)
