#!/usr/bin/env python3
"""Isolated staging acceptance. No paid transactions, production access or mail."""
import hashlib, json, os, pathlib, re, shutil, socket, subprocess, tempfile, time, urllib.error, urllib.parse, urllib.request, zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(os.environ.get("NSP_STAGING_EVIDENCE_DIR","nsp-publication-staging-evidence")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
records=json.loads((HERE/"NSP_PRODUCT_PUBLICATION_MATRIX.json").read_text())["rows"]
assert len(records)==24 and len({r["url"] for r in records})==24

def port():
    sock=socket.socket();sock.bind(("127.0.0.1",0));value=sock.getsockname()[1];sock.close();return value

def http(url,method="GET",body=None,headers=None,timeout=10):
    req=urllib.request.Request(url,method=method,data=body,headers=headers or {})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:return r.status,r.read()
    except urllib.error.HTTPError as ex:return ex.code,ex.read()

@contextmanager
def serve(root):
    p=port()
    log=(OUT/("php-server-%s.log"%p)).open("wb")
    proc=subprocess.Popen(["php","-S","127.0.0.1:"+str(p),"-t",str(root)],stdout=log,stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            if proc.poll() is not None:raise RuntimeError("PHP_SERVER_EXIT "+str(proc.returncode))
            try:
                http("http://127.0.0.1:"+str(p)+"/__probe__",timeout=1)
                break
            except Exception:time.sleep(.12)
        yield "http://127.0.0.1:"+str(p)
    finally:
        proc.terminate()
        try:proc.wait(timeout=4)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
        log.close()

def static_check():
    pages=[];errors=[];titles=[];metas=[];canon=[]
    baseline_paths=["index.html","products/p3-shablony-ks2-ks3.html","products/p5-shtrafy-uderzhaniya.html"]
    hashes=[]
    for rel in baseline_paths:
        data=(ROOT/rel).read_bytes()
        old=subprocess.run(["git","-C",str(ROOT),"show","origin/main:"+rel],capture_output=True,timeout=20)
        hashes.append({"path":rel,"unchanged":old.returncode==0 and data==old.stdout,"sha256":sha(data)})
        if old.returncode!=0 or data!=old.stdout:errors.append("BASELINE_PROTECTED_CHANGED:"+rel)
    for row in records:
        url=row["url"]
        f=ROOT/url.lstrip("/")
        if not f.is_file():errors.append("MISSING_PAGE:"+url);continue
        html=f.read_text("utf-8")
        soup=BeautifulSoup(html,"html.parser")
        tags=soup.select("h1");title=soup.find("title");desc=soup.find("meta",attrs={"name":"description"});c=soup.find("link",rel="canonical")
        if len(tags)!=1:errors.append("H1_COUNT:"+url)
        if not title or not title.get_text(strip=True):errors.append("TITLE_MISSING:"+url)
        if not desc or not desc.get("content"):errors.append("DESCRIPTION_MISSING:"+url)
        if not c or c.get("href")!="https://nastoronepodryadchika.ru"+url:errors.append("CANONICAL:"+url)
        titles.append(title.get_text(" ",strip=True) if title else "")
        metas.append(desc.get("content","") if desc else "")
        canon.append(c.get("href","") if c else "")
        if row["type"]=="PAID" and row["SKU"].lower() not in ("p3","p5"):
            if soup.select(".add-to-cart,[data-sku]"):errors.append("PAID_ANNOUNCEMENT_CART:"+url)
            for tag in soup.select('script[type="application/ld+json"]'):
                try:
                    data=json.loads(tag.string or "{}")
                    text=json.dumps(data).lower()
                    if "https://schema.org/instock" in text or '"offers"' in text:
                        errors.append("PAID_SCHEMA_OFFER:"+url)
                except ValueError:errors.append("INVALID_LD_JSON:"+url)
        if row["type"]=="FREE" and soup.select("form#lead-form"):errors.append("FREE_LEGACY_LEAD_FORM:"+url)
        pages.append({"sku":row["SKU"],"url":url,"sha256":sha(f.read_bytes()),"h1":tags[0].get_text(" ",strip=True) if tags else "","canonical":c.get("href") if c else None})
    if len(set(titles))!=len(titles):errors.append("DUPLICATE_TITLES")
    if len(set(metas))!=len(metas):errors.append("DUPLICATE_DESCRIPTIONS")
    if len(set(canon))!=len(canon):errors.append("DUPLICATE_CANONICAL")
    return {"status":"PASS" if not errors else "FAIL","checked":len(pages),"pages":pages,"protected_baselines":hashes,"failures":errors}

def http_check():
    results=[];fail=[]
    with serve(ROOT) as base:
        for row in records:
            status,body=http(base+row["url"])
            results.append({"SKU":row["SKU"],"method":"GET","path":row["url"],"http_status":status,"response_sha256":sha(body)})
            if status!=200:fail.append("PAGE_HTTP:"+row["SKU"]+":"+str(status))
        for row in records:
            if row["type"]=="FREE":
                sku=row["SKU"].split("/",1)[1]
                form=urllib.parse.urlencode({"material":sku,"name":"Synthetic","contact":"synthetic@example.invalid","consent":"yes"}).encode()
                status,body=http(base+"/lead.php","POST",form,{"Content-Type":"application/x-www-form-urlencoded"})
                results.append({"SKU":row["SKU"],"method":"POST","path":"/lead.php","http_status":status,"response_sha256":sha(body)})
                if status!=409 or b'"download"' in body:fail.append("HOLD_FREE_LEAD:"+sku)
            elif row["SKU"].lower() not in ("p3","p5"):
                item=json.dumps({"items":[{"sku":row["SKU"].lower()}],"email":"synthetic@example.invalid"}).encode()
                status,body=http(base+"/payment.php","POST",item,{"Content-Type":"application/json"})
                results.append({"SKU":row["SKU"],"method":"POST","path":"/payment.php","http_status":status,"response_sha256":sha(body)})
                if status!=409:fail.append("HOLD_PAID_ORDER:"+row["SKU"]+":"+str(status))
        # Direct URLs existed before this PR, and remain a separate HOLD risk.
        direct=[]
        for n in ["dengi.zip","avans.zip","checklist-zakrytiya-rabot.pdf"]:
            status,body=http(base+"/downloads/"+n)
            direct.append({"path":"/downloads/"+n,"status":status,"sha256":sha(body)})
    return {"status":"PASS" if not fail else "FAIL","checks":results,"hold_denials":sum(x["http_status"]==409 for x in results),"legacy_direct_existing_urls":direct,"failures":fail}

def old_order_check():
    # Synthetic, isolated storage and local fixture only. No real orders touched.
    with tempfile.TemporaryDirectory(prefix="nsp-order-synthetic-") as temp:
        t=pathlib.Path(temp); web=t/"web";web.mkdir(); orders=t/"orders";(orders/"delivery").mkdir(parents=True);products=t/"products";products.mkdir()
        for n in ("download.php","products-config.php"):shutil.copyfile(ROOT/n,web/n)
        config="<?php\n"+ "\n".join([
            "define('ORDERS_DIR',"+repr(str(orders))+");",
            "define('PRODUCTS_DIR',"+repr(str(products))+");",
            "define('SITE_URL','http://127.0.0.1');",
            "define('ADMIN_EMAIL','qa@example.invalid');",
            "define('YOOKASSA_SHOP_ID','stub');",
            "define('YOOKASSA_SECRET_KEY','stub');",
            "define('YOOKASSA_MODE','test');",
            "define('YOOKASSA_API_URL','http://127.0.0.1:1/disabled');",
        ])
        (web/"config.php").write_text(config+"\n")
        zipped=orders/"delivery"/"legacy-synthetic.zip"
        with zipfile.ZipFile(zipped,"w") as z:z.writestr("legacy.txt","paid order fixture only")
        token="qaSyntheticToken0123456789"; id="order_20261027_000000_syn777"
        payload={"id":id,"status":"paid","items":[{"sku":"p3"}],"delivery":{"token":token,"expires_at":"2099-01-01T00:00:00+00:00","downloads":0,"items":{"p3":zipped.name}}}
        order=orders/(id+".json");order.write_text(json.dumps(payload))
        basepath="/download.php?o="+id+"&f=p3&t="
        checks=[]
        with serve(web) as base:
            for typ,tok,expected in [("first",token,200),("repeat",token,200),("invalid","wrong-token",403)]:
                code,body=http(base+basepath+tok)
                checks.append({"case":typ,"http_status":code,"sha256":sha(body)})
            payload=json.loads(order.read_text())
            payload["delivery"]["expires_at"]="2020-01-01T00:00:00+00:00"
            order.write_text(json.dumps(payload))
            code,body=http(base+basepath+token)
            checks.append({"case":"expired","http_status":code,"sha256":sha(body)})
        ok=[x["http_status"] for x in checks]==[200,200,403,410] and checks[0]["sha256"]==checks[1]["sha256"]==sha(zipped.read_bytes())
        return {"status":"PASS" if ok else "FAIL","test":"SYNTHETIC_OLD_PAID_TOKEN","cases":checks,"fixture_zip_sha256":sha(zipped.read_bytes()),"real_orders_accessed":False}

def browser_check():
    shots=[];fails=[]
    from playwright.sync_api import sync_playwright
    widths=[1366,1920,1280,390,430]
    folder=OUT/"screenshots";folder.mkdir(exist_ok=True)
    with serve(ROOT) as base:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
            for w in widths:
                context=browser.new_context(viewport={"width":w,"height":900},device_scale_factor=1)
                page=context.new_page()
                for row in records:
                    url=row["url"]
                    try:
                        response=page.goto(base+url,wait_until="domcontentloaded",timeout=18000)
                        page.wait_for_timeout(100)
                        width=page.evaluate("document.documentElement.scrollWidth")
                        over=width-w
                        name=row["SKU"].replace("/","-")+"-"+str(w)+".png"
                        shot=folder/name
                        page.screenshot(path=str(shot),full_page=True,timeout=25000)
                        shots.append({"SKU":row["SKU"],"width":w,"http":response.status if response else None,
                                     "scroll_width":width,"horizontal_overflow":over,"screenshot":"screenshots/"+name,
                                     "screenshot_sha256":sha(shot.read_bytes())})
                        if not response or response.status!=200:fails.append("BROWSER_HTTP:"+url+"@"+str(w))
                        if over>8:fails.append("HORIZONTAL_OVERFLOW:"+url+"@"+str(w)+":"+str(over))
                    except Exception as ex:fails.append("BROWSER_ERROR:"+url+"@"+str(w)+":"+str(ex)[:130])
                context.close()
            browser.close()
    return {"status":"PASS" if not fails else "FAIL","expected_screenshots":120,
            "actual_screenshots":len(shots),"results":shots,"failures":fails}

def main():
    static=static_check()
    (OUT/"static.json").write_text(json.dumps(static,ensure_ascii=False,indent=2)+"\n")
    httpqa=http_check()
    (OUT/"http.json").write_text(json.dumps(httpqa,ensure_ascii=False,indent=2)+"\n")
    prior=old_order_check()
    (OUT/"old-orders.json").write_text(json.dumps(prior,ensure_ascii=False,indent=2)+"\n")
    try:browser=browser_check()
    except Exception as ex:browser={"status":"FAIL","failures":["BROWSER_HARNESS:"+str(ex)[:400]],"actual_screenshots":0}
    (OUT/"browser.json").write_text(json.dumps(browser,ensure_ascii=False,indent=2)+"\n")
    report={"schema":"NSP_STAGING_QA_RUNTIME_V1","run_utc":datetime.now(timezone.utc).isoformat(),
            "scope":"EPHEMERAL_GITHUB_ACTIONS_STAGING_NO_REAL_ORDERS_OR_PAYMENTS",
            "static":static["status"],"http_new_orders":httpqa["status"],
            "synthetic_existing_order":prior["status"],"browser":browser["status"],
            "http_hold_denials":httpqa["hold_denials"],"browser_screenshots":browser.get("actual_screenshots",0),
            "release_permission":"HOLD","qa04_git_provenance":"EVIDENCE_MISSING",
            "production_changed":False,"final_status":"PARTIAL_READY_WITH_BLOCKERS"}
    (OUT/"NSP_STAGING_QA_RECEIPT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False))
    return 0 if all(x=="PASS" for x in (static["status"],httpqa["status"],prior["status"],browser["status"])) else 1

if __name__=="__main__":raise SystemExit(main())
