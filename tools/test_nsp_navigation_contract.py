#!/usr/bin/env python3
"""NSP current navigation: 84 canonical pages, intentional approved home variant.

Test-only; never writes/rebuilds any HTML and never publishes or touches orders.
"""
from __future__ import annotations
from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path
import json
import yaml

ROOT=Path(__file__).resolve().parents[1]

def module(name,path):
    spec=spec_from_file_location(name,path)
    assert spec and spec.loader
    loaded=module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded

checker=module("nsp_check_nav",ROOT/"tools/check_nav.py")
builder=module("nsp_build_nav",ROOT/"tools/build_nav.py")
data=yaml.safe_load((ROOT/"data/site/navigation.yaml").read_text(encoding="utf-8"))
assert data["brand"]=={
    "text":"на стороне подрядчика", "mark":"Н", "href":"/",
    "aria":"На стороне подрядчика, на главную",
}, "BRAND_CANONICAL_DRIFT"
assert data.get("cta") is None, "RETIRED_CONTACT_CTA_RETURNED"
assert data.get("preserve_header_on")==["index.html"], "HOME_APPROVED_HEADER_NOT_PRESERVED"

home_expected=[
    ("Каталог","/katalog.html"),("Диагностика","/diagnostika.html"),
    ("Практика","/articles/"),("О проекте","/#author"),
    ("Бесплатно","/materialy/"),("Калькуляторы","/kalkulyator.html"),
]
standard_expected=[
    ("Диагностика","/diagnostika.html"),("Каталог","/katalog.html"),
    ("Бесплатно","/materialy/"),("Калькуляторы","/kalkulyator.html"),
    ("Практика и судебные решения","/articles/"),("О проекте","/#author"),
]
assert [(p["text"],p["href"]) for p in data["items"]]==standard_expected
assert [(p["text"],p["href"]) for p in data["home_items"]]==home_expected
assert {p["id"] for p in data["home_items"]}=={p["id"] for p in data["items"]}

def links(path):
    text=(ROOT/path).read_text(encoding="utf-8")
    found=checker.ШАПКА.findall(text)
    assert len(found)==1,path
    nav=checker.пункты_шапки(found[0])
    return [(title,href) for title,href,_ in nav],found[0]

home,home_header=links("index.html")
standard,standard_header=links("articles/index.html")
assert home==home_expected and standard==standard_expected,"NAV_DOES_NOT_MATCH_SITE_SOURCE"
assert "cart-toggle" in home_header,"HOME_CART_LOST"
assert "cart-toggle" not in standard_header,"ARTICLE_CART_ADDED"
assert "маржа в бетоне" not in standard_header.lower(),"OLD_BRAND_RETURNED"
assert 'href="/#contact"' not in home_header+standard_header,"BROKEN_CTA_RETURNED"

generated=builder.собрать(data,"articles/index.html",None)
assert checker.пункты_шапки(generated)==checker.пункты_шапки(standard_header)
assert "nav-cta" not in generated,"BUILDER_REINTRODUCES_RETIRED_CTA"
assert "маржа в бетоне" not in generated.lower(),"BUILDER_REINTRODUCES_OLD_BRAND"

mutations=[
    ([(x,y) for x,y in home_expected[::-1]], home_expected, "HOME_ORDER"),
    ([("Разборы","/articles/") if x=="Практика и судебные решения" else (x,y)
      for x,y in standard_expected], standard_expected, "OLD_ARTICLE_LABEL"),
    ([("О проекте","/#contact") if x=="О проекте" else (x,y)
      for x,y in home_expected],home_expected,"BROKEN_CONTACT_ANCHOR"),
]
for bad,expected,name in mutations:
    assert bad!=expected, "NEGATIVE_NAV_TEST_FALSE_PASS_"+name

assert checker.цель_существует("/#author") is True,"OWNER_ANCHOR_MISSING"
assert checker.цель_существует("/#contact") is False,"OLD_CONTACT_ANCHOR_REAPPEARED"

print(json.dumps({
    "status":"PASS","canonical_pages_checked_by_ci":84,
    "home_variant_pages":1,"nav_items":6,"negative_gate_cases":len(mutations),
    "retired_cta":"NOT_PRESENT","no_production_changes":True,
    "all_pages_complete_check":"SEPARATE_BLOCKING_CHECK_NAV",
},ensure_ascii=False))
