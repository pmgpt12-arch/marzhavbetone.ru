#!/usr/bin/env python3
"""Independent full-page route/content delta gate for article section renaming.

Compares all 88 public HTML files with the frozen approved R1 baseline.
Allowed: only the deterministic label changes and CSS cache fingerprints
produced by the scoped rename tool. No changes to amounts, SKUs, href routes,
old-domain canonical links, forms or order fields.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
BASE_SHA="39a7a00aca1f8257fda89aabfb81363234194553"
SCRIPT=ROOT/"tools/rename_practice_section.py"
SPECS=importlib.util.spec_from_file_location("rename_practice_section",SCRIPT)
assert SPECS and SPECS.loader
REN=importlib.util.module_from_spec(SPECS)
SPECS.loader.exec_module(REN)
URL=re.compile(r'(?:href|src|action|poster)="([^"]+)"')
FINANCIAL=re.compile(r'data-(?:sku|price|product)="[^"]*"|id="(?:cart-[^"]*|checkout-[^"]*)"',re.I)
CSS_REF=re.compile(r'brand-approved-2026\.css\?v=[a-f\d]{8}')

def git(*args:str)->str:
 p=subprocess.run(["git",*args],cwd=ROOT,text=True,capture_output=True,check=True,timeout=15)
 return p.stdout

def stable_links(text:str)->list[str]:
 return [CSS_REF.sub("brand-approved-2026.css?v=STABLE",x) for x in URL.findall(text)]

def check()->dict:
 pages=REN.html_files()
 current_css=(ROOT/"brand-approved-2026.css").read_bytes()
 parent_css=git("show",f"{BASE_SHA}:brand-approved-2026.css").encode("utf-8")
 if not current_css.startswith(parent_css):
  raise ValueError("Approved base CSS was overwritten; only append allowed")
 current_version=hashlib.sha1(current_css).hexdigest()[:8]
 old_version=hashlib.sha1(parent_css).hexdigest()[:8]
 page_results=[]
 for rel in pages:
  name=rel.as_posix()
  original=git("show",f"{BASE_SHA}:{name}")
  expected=REN.html_transform(original,rel)
  expected=CSS_REF.sub("brand-approved-2026.css?v="+current_version,expected)
  actual=(ROOT/rel).read_text(encoding="utf-8")
  problems=[]
  if expected!=actual:problems.append("UNAPPROVED_HTML_DELTA")
  if stable_links(actual)!=stable_links(original):problems.append("ROUTE_OR_ASSET_CHANGED")
  if FINANCIAL.findall(actual)!=FINANCIAL.findall(original):problems.append("PRODUCT_OR_CART_IDENTIFIER_CHANGED")
  if actual.count("https://marzhavbetone.ru")!=original.count("https://marzhavbetone.ru"):problems.append("DOMAIN_SWAP_WRONG_BRANCH")
  page_results.append({"path":name,"pass":not problems,"problems":problems,"changed":actual!=original})
 nav_old=git("show",f"{BASE_SHA}:data/site/navigation.yaml")
 nav_now=(ROOT/"data/site/navigation.yaml").read_text("utf-8")
 nav_expected=REN.sub_once(nav_old,"    text: Разборы\n    href: /articles/","    text: Практика и судебные решения\n    href: /articles/","navigation")
 source_problems=[]
 if nav_expected!=nav_now:source_problems.append("NAV_SOURCE_DRIFT")
 for path,rules in REN.GENERATOR.items():
  original=git("show",f"{BASE_SHA}:{path}")
  expected=original
  for a,b in rules.items():expected=REN.sub_once(expected,a,b,path)
  actual=(ROOT/path).read_text("utf-8")
  if expected!=actual:source_problems.append("GENERATOR_SOURCE_DRIFT:"+path)
 data={x["path"]:x for x in page_results}
 docs=[x for x in pages if x.as_posix().startswith("articles/")]
 article_schema_count=sum('"name": "Практика и судебные решения"' in (ROOT/p).read_text("utf-8") for p in docs)
 nav_label_count=sum('>Практика и судебные решения</a>' in (ROOT/p).read_text("utf-8") for p in pages)
 hub=(ROOT/"articles/index.html").read_text("utf-8")
 return {
  "gate":"R1_PRACTICE_AND_COURT_DECISIONS_V2",
  "scope":"presentation labels only, no production",
  "baseline":BASE_SHA,
  "current_commit":git("rev-parse","HEAD").strip(),
  "css_old_sha1_8":old_version,
  "css_new_sha1_8":current_version,
  "public_html_total":len(pages),
  "public_html_changed":sum(x["changed"] for x in page_results),
  "page_exact_matches":sum(x["pass"] for x in page_results),
  "nav_label_pages":nav_label_count,
  "article_schema_pages":article_schema_count,
  "source_problems":source_problems,
  "hub_h1_ok":"Практика и судебные решения" in hub,
  "hub_label_ok":"ПРАКТИЧЕСКИЕ МАТЕРИАЛЫ" in hub,
  "hub_title_ok":"<title>Практика и судебные решения — На стороне подрядчика</title>" in hub,
  "problems":[x for x in page_results if not x["pass"]],
  "pages":page_results,
  "pass":len(pages)==88 and all(x["pass"] for x in page_results)
    and nav_label_count==85 and article_schema_count==42
    and not source_problems and all((
      "Практика и судебные решения" in hub,
      "ПРАКТИЧЕСКИЕ МАТЕРИАЛЫ" in hub,
      "<title>Практика и судебные решения — На стороне подрядчика</title>" in hub,
    )),
  "non_goals":["No payment processing or legal product files changed",
    "No actual buyer checkout or DNS/cutover tested",
    "R1 historic V3 exact baseline remains evidence for previous iteration; this gate supersedes it only for UI labels"],
 }

def main()->int:
 p=argparse.ArgumentParser()
 p.add_argument("--report",type=Path)
 p.add_argument("--check",action="store_true")
 a=p.parse_args()
 result=check()
 if a.report:
  a.report.parent.mkdir(parents=True,exist_ok=True)
  a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({k:v for k,v in result.items() if k in (
    "gate","baseline","public_html_total","public_html_changed","page_exact_matches",
    "nav_label_pages","article_schema_pages","source_problems","hub_h1_ok","hub_label_ok","hub_title_ok","pass"
 )},ensure_ascii=False,indent=2))
 if a.check and not result["pass"]:return 1
 return 0

if __name__=="__main__":
 raise SystemExit(main())
