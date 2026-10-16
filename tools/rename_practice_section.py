#!/usr/bin/env python3
"""Rename the public editorial section while keeping /articles/ routes unchanged.

This script touches only approved visible labels and their source generators.
It never renames a route, product, legal party, paid file, SKU, amount, payment
or social account. Repeat calls are idempotent.

    python3 tools/rename_practice_section.py           # preview
    python3 tools/rename_practice_section.py --write   # update approved labels
    python3 tools/rename_practice_section.py --check   # fail when drift remains
"""
from __future__ import annotations
import argparse
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
NEW="Практика и судебные решения"
OLD="Разборы"
HEADER_LINK=re.compile(r'(<a\b[^>]*href="/articles/"[^>]*>)Разборы(</a>)')
BREAD_SCHEMA='"name": "Разборы"'
LABELS={
  "Новые разборы — в канале и в Дзене":"Новые материалы — в Telegram и Дзене",
}
HOME={
  "Все разборы →":"Все материалы →",
  "Витрина разборов →":"Смотреть практические материалы →",
  "СВЕЖИЕ РАЗБОРЫ":"ПРАКТИКА И СУДЕБНЫЕ РЕШЕНИЯ",
  "Открыть разбор →":"Читать материал →",
}
HUB={
  'content="Практические разборы договоров, допработ, КС-2, приёмки, удержаний, авансов, тендеров и банкротства. Контринтуитивные факты из строительной практики."':
  'content="Рабочие ситуации для исполнителей работ и услуг в строительстве: договоры, дополнительные работы, приёмка, оплата, удержания и споры с заказчиком."',
  'content="Разборы — На стороне подрядчика"':
  'content="Практика и судебные решения — На стороне подрядчика"',
  '<title>Разборы — На стороне подрядчика</title>':
  '<title>Практика и судебные решения — На стороне подрядчика</title>',
  '"name": "Разборы для строительных подрядчиков"':
  '"name": "Практические материалы для исполнителей работ и услуг в строительстве"',
  '<li aria-current="page">Разборы</li>':
  '<li aria-current="page">Практика и судебные решения</li>',
  'aria-label="Темы разборов"':
  'aria-label="Темы практических материалов"',
  '<h1>Деньги теряются тихо</h1>':
  '<h1>Практика и судебные решения</h1>',
  'ВИТРИНА ЭКСПЕРТИЗЫ':'ПРАКТИЧЕСКИЕ МАТЕРИАЛЫ',
  'Ситуации, в которых выполненный объём не превращается в оплату. Каждый материал заканчивается контрольными точками и готовыми документами.':
  'Рабочие ситуации, практические рекомендации и судебная практика: как согласовывать условия, оформлять результат и защищать право на оплату.',
}
GENERATOR={
  "tools/build_cases.py": {
    "Все разборы →":"Все материалы →",
    "Открыть разбор →":"Читать материал →",
  },
  "tools/rebuild_home_2026-08-15.py": {
    "Все разборы →":"Все материалы →",
    "Витрина разборов →":"Смотреть практические материалы →",
    "СВЕЖИЕ РАЗБОРЫ":"ПРАКТИКА И СУДЕБНЫЕ РЕШЕНИЯ",
    "Открыть разбор →":"Читать материал →",
  },
  "tools/articles_index.py": {
    'aria-label="Темы разборов"':'aria-label="Темы практических материалов"',
  },
  "tools/build_diagnostic.py":{
    'Разборы по темам — <a href="/articles/">все разборы</a>.':
    'Практические материалы по темам — <a href="/articles/">все материалы</a>.',
  },
  "tools/rebuild_index_2026-08-14.py":{
    '<a href="articles/">Разборы</a>':'<a href="articles/">Практика и судебные решения</a>',
  },
  "tools/build_rss.py":{
    "Разборы для строительных подрядчиков: как оформить работы, ":
    "Практические материалы для исполнителей работ и услуг в строительстве: как оформить работы, ",
  },
}
NAV_PATH=Path("data/site/navigation.yaml")

def sub_once(text:str, old:str, new:str, where:str) -> str:
    # Re-running is safe; a changed/ambiguous target is blocked.
    count=text.count(old)
    if count>1:
        raise ValueError(f"{where}: ambiguous source {old[:70]!r}: count={count}")
    if count==0 and new not in text:
        raise ValueError(f"{where}: expected source/target missing {old[:70]!r}")
    return text.replace(old,new)

def html_files()->list[Path]:
    names=subprocess.run(["git","ls-files","--","*.html"],capture_output=True,
                         cwd=ROOT,text=True,check=True,timeout=12).stdout.splitlines()
    paths=[Path(name) for name in names if not name.startswith(("data/","tools/","content/","node_modules/"))]
    if len(paths)!=88:
        raise ValueError(f"expected 88 public HTML pages, found {len(paths)}")
    return paths

def html_transform(text:str, rel:Path) ->str:
    text=HEADER_LINK.sub(lambda m:m.group(1)+NEW+m.group(2),text)
    text=text.replace(BREAD_SCHEMA,'"name": "Практика и судебные решения"')
    for source,target in LABELS.items():
        text=text.replace(source,target)
    if rel.as_posix()=="index.html":
        for source,target in HOME.items():
            text=text.replace(source,target)
    if rel.as_posix()=="articles/index.html":
        for source,target in HUB.items():
            text=sub_once(text,source,target,str(rel))
    return text

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument("--write",action="store_true")
    mode.add_argument("--check",action="store_true")
    args=p.parse_args()
    updates=[]
    for rel in html_files():
        current=(ROOT/rel).read_text("utf-8")
        changed=html_transform(current,rel)
        if changed!=current:updates.append((rel,changed))
    nav=(ROOT/NAV_PATH).read_text("utf-8")
    newer=sub_once(nav,"    text: Разборы\n    href: /articles/","    text: Практика и судебные решения\n    href: /articles/",str(NAV_PATH))
    if nav!=newer:updates.append((NAV_PATH,newer))
    for name,rules in GENERATOR.items():
        rel=Path(name)
        src=(ROOT/rel).read_text("utf-8")
        nxt=src
        for before,after in rules.items():nxt=sub_once(nxt,before,after,name)
        if nxt!=src:updates.append((rel,nxt))
    print(f"PUBLIC_HTML=88 PENDING_PATHS={len(updates)}")
    for rel,_ in updates[:12]:print(" ",rel)
    if args.check and updates:return 1
    if args.write:
        for rel,data in updates:(ROOT/rel).write_text(data,encoding="utf-8")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
