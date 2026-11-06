#!/usr/bin/env python3
"""Check 13 paid article-CTA blocks against approved prices and actual ZIP counts.

No network, no product master files, no orders, no email, no production edits.
The QA checks exact SKU-bound CTA blocks, never prices from sibling products.
"""
import ast
from html import unescape
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"tools/reports/nsp-paid-master-counts-20261106.json"
PRICE_SOURCE=ROOT/"tools/nsp-final/validate.py"
PAGES={
"p8": [
    "articles/avans-eto-ne-dengi-eto-kryuchok.html",
    "articles/avans-po-dogovoru-podryada.html",
    "articles/bankovskaya-garantiya-na-vozvrat-avansa.html",
    "articles/vozvrat-avansa-po-dogovoru-podryada.html",
],
"p9": [
    "articles/reestr-trebovaniy-kreditorov.html",
    "articles/srok-vklyucheniya-v-reestr-trebovaniy-kreditorov.html",
    "articles/vklyuchenie-v-reestr-trebovaniy-kreditorov.html",
    "articles/zapros-arbitrazhnomu-upravlyayushchemu.html",
    "articles/zayavlenie-o-vklyuchenii-v-reestr-trebovaniy.html",
],
"p2": [
    "articles/dopolnitelnye-raboty-v-stroitelstve.html",
    "articles/dopraboty-bez-soglasheniya.html",
    "articles/vsyo-vklyucheno-v-cenu.html",
],
"p11": ["articles/zos-v-stroitelstve.html"],
}
CTA=re.compile(r'<div\b[^>]*class="[^"]*\barticle-cta\b[^"]*"[^>]*>[\s\S]*?</div>',re.I)
PRICE=re.compile(r'(?<!\d)(\d{1,3}(?:[\s\u00a0]\d{3})*)\s*₽')
COUNT=re.compile(r'(?<!\d)(\d{1,3})\s+файл(?:ов|а)?\b',re.I)


def approved_prices():
    tree=ast.parse(PRICE_SOURCE.read_text(encoding="utf-8"))
    values=[]
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(
                isinstance(t,ast.Name) and t.id=="PRICES" for t in node.targets):
            values.append(ast.literal_eval(node.value))
    assert len(values)==1
    return values[0]


def audit_cta(page,sku,price_kopeks,file_count):
    found=[m.group() for m in CTA.finditer(page)
           if re.search(r"/products/"+sku+r"[-.]",m.group())]
    assert len(found)==1, "MISSING_OR_DUPLICATE_SKU_CTA_"+sku
    raw=found[0]
    text=unescape(re.sub(r"<[^>]+>"," ",raw))
    prices=[int(m.group(1).replace(" ","").replace("\u00a0","")) for m in PRICE.finditer(text)]
    numbers=[int(m.group(1)) for m in COUNT.finditer(text)]
    assert prices==[price_kopeks//100], "CTA_PRICE_MISMATCH_"+sku+"_"+str(prices)
    assert numbers==[file_count], "CTA_FILE_COUNT_MISMATCH_"+sku+"_"+str(numbers)
    assert re.search(r"/products/"+sku+r"[-.]",raw)
    return raw


def expected():
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert registry["schema"]=="NSP_PAID_MASTER_COUNT_CONTRACT_20261106_v1"
    assert registry["evidence"]["read_only_action_run"]==42133240407
    assert registry["evidence"]["result"]=="PASS_ALL_11_REAL_PRIVATE_PINNED_ZIPS"
    counts=registry["count_by_sku"]
    prices=approved_prices()
    assert len(counts)==11 and len(prices)==11
    assert {sku for sku in PAGES} <= set(counts) & set(prices)
    return counts,prices


def main():
    counts,prices=expected()
    scanned=0
    for sku,paths in PAGES.items():
        for path in paths:
            source=(ROOT/path).read_text(encoding="utf-8")
            audit_cta(source,sku,prices[sku],counts[sku])
            scanned+=1
    assert scanned==13 and len({p for paths in PAGES.values() for p in paths})==13

    # Negative gates must actually reject an old price, old ZIP count,
    # missing target link and invented extra CTA (no "green by omission").
    sku="p8"; path=PAGES[sku][0]
    source=(ROOT/path).read_text(encoding="utf-8")
    block=audit_cta(source,sku,prices[sku],counts[sku])
    formatted=f"{prices[sku]//100:,}".replace(","," ")+" ₽"
    wrong_price=block.replace(formatted,"2 490 ₽",1)
    wrong_count=block.replace("12 файлов","11 файлов",1)
    broken_link=block.replace("/products/p8-","/products/p7-",1)
    duplicate=source.replace(block,block+block,1)
    negative=[source.replace(block,wrong_price,1),
              source.replace(block,wrong_count,1),
              source.replace(block,broken_link,1),
              duplicate]
    for index,mutated in enumerate(negative):
        try:
            audit_cta(mutated,sku,prices[sku],counts[sku])
        except AssertionError:
            continue
        raise AssertionError("NEGATIVE_TEST_FALSE_PASS_"+str(index))

    print(json.dumps({
        "status":"PASS","paid_article_ctas":scanned,
        "sku_coverage":sorted(PAGES),
        "invalid_mutations_rejected":len(negative),
        "buyers_price_source":"tools/nsp-final/validate.py",
        "buyer_zip_count_source":"REG_RU_42133240407",
        "production_writes":0,"paid_archives_read":0,"orders_created":0,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
