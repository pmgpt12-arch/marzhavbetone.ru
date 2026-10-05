"""Статический поиск циклических ссылок в формулах книги: граф ячейка → ячейки/диапазоны."""
import sys, re
from pathlib import Path
import openpyxl
from openpyxl.formula import Tokenizer
from openpyxl.utils import range_boundaries
sys.setrecursionlimit(1000000)

def refs(sheet, formula):
    out = []
    for t in Tokenizer(formula).items:
        if t.type == "OPERAND" and t.subtype == "RANGE":
            v = t.value
            sh = sheet
            if "!" in v:
                sh, v = v.rsplit("!", 1); sh = sh.strip("'")
            v = v.replace("$", "")
            if not re.match(r"^[A-Z]+\d*(:[A-Z]+\d*)?$", v):
                continue  # именованный диапазон и т.п.
            out.append((sh, v))
    return out

for book in sys.argv[1:]:
    wb = openpyxl.load_workbook(book)
    cells = {}
    for ws in wb:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    cells[(ws.title, c.row, c.column)] = refs(ws.title, c.value)
    # диапазоны раскрываем через индекс ячеек-формул по листу/колонке
    bycol = {}
    for (sh, r, col) in cells:
        bycol.setdefault((sh, col), []).append(r)
    def targets(sh, v):
        mnc, mnr, mxc, mxr = range_boundaries(v if ":" in v else f"{v}:{v}")
        mnr = mnr or 1; mxr = mxr or 1048576
        for col in range(mnc, mxc + 1):
            for r in bycol.get((sh, col), []):
                if mnr <= r <= mxr:
                    yield (sh, r, col)
    graph = {n: [t for sh, v in rs for t in targets(sh, v)] for n, rs in cells.items()}
    # итеративный поиск цикла (DFS с цветами)
    color = {}; cyc = None
    for s in graph:
        if s in color: continue
        stack = [(s, iter(graph[s]))]; color[s] = 1
        while stack and not cyc:
            n, it = stack[-1]
            for m in it:
                if color.get(m) == 1: cyc = (n, m); break
                if m not in color:
                    color[m] = 1; stack.append((m, iter(graph.get(m, [])))); break
            else:
                color[n] = 2; stack.pop()
        if cyc: break
    edges = sum(map(len, graph.values()))
    print(f"{Path(book).name}: формул {len(cells)}, связей {edges}, цикл: {cyc or 'нет'}")
