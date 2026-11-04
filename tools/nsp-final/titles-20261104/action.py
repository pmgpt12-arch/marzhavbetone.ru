#!/usr/bin/env python3
"""NSP one-shot public title release via existing nsp-final workflow; 8 HTML only."""
import concurrent.futures
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EVIDENCE=Path("/tmp/nsp-final-evidence")
EVIDENCE.mkdir(parents=True,exist_ok=True)
SHA=lambda b:hashlib.sha256(b).hexdigest()
EXPECTED_NAMES={
    "p3":("p3-shablony-ks2-ks3.html","Система подготовки и проверки документов КС-2 и КС-3 перед сдачей",1790000),
    "p7":("p7-dogovor-podryada.html","Система проверки и согласования договора субподряда",2490000),
    "p8":("p8-avans-po-dogovoru-subpodryada.html","Система управления авансами и расчётами по договору подряда",2490000),
    "p9":("p9-bankrotstvo-genpodryadchika.html","Система защиты требований подрядчика при банкротстве генподрядчика",2490000),
    "p10":("p10-otvet-na-pretenziyu.html","Система подготовки ответа на претензию заказчика",1790000),
    "p11":("p11-raschet-metrami.html","Система проверки расчётов недвижимостью и уступки прав",2490000),
    "p13":("p13-chto-v-smete-ne-oplatyat.html","Система проверки сметной документации и выявления неоплачиваемых затрат",1790000)
}
class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons=[]
        self.meta=[]
        self.href=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="button" and "data-sku" in d:self.buttons.append(d)
        if tag=="meta":self.meta.append(d)
        if tag=="a":self.href.append(d.get("href"))
def model_check(manifest):
    assert manifest["schema"]=="NSP_TITLES_8_STATIC_V1" and manifest["count"]==8
    assert manifest["candidate_head"]=="da4185108d4cce0002d6fbdb6ca993228a123a72"
    rows=manifest["files"]
    paths=[x["path"] for x in rows]
    assert len(rows)==len(set(paths))==8
    assert set(paths)=={"katalog.html"}|{"products/"+n for n,_,_ in EXPECTED_NAMES.values()}
    for row in rows:
        path=ROOT/row["path"]
        blob=path.read_bytes()
        assert SHA(blob)==row["after"], "CANDIDATE_SHA_DRIFT:"+row["path"]
        assert row["before"]!=row["after"] and len(blob)<300000
        assert not any(marker in blob for marker in (b"-----BEGIN PRIVATE KEY",b"ghp_",b"sk_live_"))
    katalog=(ROOT/"katalog.html").read_text()
    parsed=Parser();parsed.feed(katalog)
    expected_prices={"p1":2990000,"p2":2490000,"p3":1790000,"p4":2490000,"p5":2990000,
       "p7":2490000,"p8":2490000,"p9":2490000,"p10":1790000,"p11":2490000,"p13":1790000}
    sku_prices={d["data-sku"]:int(d["data-price"]) for d in parsed.buttons}
    assert len(parsed.buttons)==11 and sku_prices==expected_prices, "CATALOG_11_SKU_PRICES"
    assert katalog.count('class="product-card free"')==10, "FREE_MATERIALS_COUNT"
    for sku,(fn,name,price) in EXPECTED_NAMES.items():
        match=[d for d in parsed.buttons if d["data-sku"]==sku]
        assert len(match)==1 and match[0]["data-product"]==name
        src=(ROOT/"products"/fn).read_text()
        p=Parser();p.feed(src)
        h1=re.search(r"<h1[^>]*>(.*?)</h1>",src,re.I|re.S)
        title=re.search(r"<title[^>]*>(.*?)</title>",src,re.I|re.S)
        assert h1 and title
        assert html.unescape(re.sub("<[^>]+>","",h1.group(1))).strip()==name
        assert name in html.unescape(title.group(1))
        assert name in [x.get("content") for x in p.meta if x.get("property")=="og:title"]
        bt=[x for x in p.buttons if x.get("data-sku")==sku]
        assert len(bt)==1 and bt[0].get("data-product")==name and int(bt[0]["data-price"])==price
        scripts=re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',src,re.S|re.I)
        assert scripts
        def find_product(x):
            if isinstance(x,dict):
                if x.get("@type")=="Product":yield x.get("name")
                for v in x.values(): yield from find_product(v)
            elif isinstance(x,list):
                for v in x:yield from find_product(v)
        assert name in [n for s in scripts for n in find_product(json.loads(s))]
    return rows

def call(cmd, *, data=None, timeout=70):
    r=subprocess.run(cmd,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if r.returncode:
        stderr=r.stderr.decode("utf-8","replace")
        gate=re.search(r"NSP_TITLES_RELEASE_ERROR=([A-Z0-9_:/.-]{1,100})",stderr)
        if gate:raise RuntimeError("RELEASE_GATE:"+gate.group(1))
        raise RuntimeError("RELEASE_CMD_EXIT:"+str(r.returncode)+":"+stderr[-400:])
    return r.stdout

def write_report(name,data):
    p=EVIDENCE/name
    assert not p.exists(),name
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

def main(action):
    assert action in ("titles-preflight","titles-publish")
    run=os.environ["GITHUB_RUN_ID"]
    assert re.fullmatch(r"[0-9]{8,16}",run)
    assert os.environ.get("GITHUB_REF_NAME")=="fix/nsp-cutover-final-20261021"
    manifest=json.loads((HERE/"manifest.json").read_text())
    rows=model_check(manifest)
    call(["php","-l",str(HERE/"transaction.php")],timeout=12)
    host=os.environ["HOST"];user=os.environ["SSH_USER"];port=os.environ["PORT"]
    assert host and user and re.fullmatch("[0-9]{1,5}",port)
    key=Path.home()/".ssh/nsp_final_key"
    known=key.parent/"known_hosts"
    assert key.is_file() and known.is_file()
    ssh=["ssh","-p",port,"-i",str(key),"-o","BatchMode=yes",
        "-o","IdentitiesOnly=yes","-o","StrictHostKeyChecking=yes",
        "-o","UserKnownHostsFile="+str(known),"-o","ConnectTimeout=12",
        "-o","ServerAliveInterval=10","-o","ServerAliveCountMax=3",user+"@"+host]
    tarbuf=io.BytesIO()
    with tarfile.open(fileobj=tarbuf,mode="w:gz") as tf:
        for name,content in (("manifest.json",(HERE/"manifest.json").read_bytes()),
                             ("transaction.php",(HERE/"transaction.php").read_bytes())):
            info=tarfile.TarInfo(name);info.mode=0o600;info.size=len(content)
            tf.addfile(info,io.BytesIO(content))
        for r in rows:
            raw=(ROOT/r["path"]).read_bytes()
            info=tarfile.TarInfo("candidate/"+r["path"]);info.mode=0o600;info.size=len(raw)
            tf.addfile(info,io.BytesIO(raw))
    archive=tarbuf.getvalue()
    assert len(archive)<1_000_000
    remote='"$HOME/nsp-title-releases/title-'+run+'"'
    site='"$HOME/www/nastoronepodryadchika.ru"'
    cmd='set -eu; umask 077; mkdir -p "$HOME/nsp-title-releases"; test ! -e '+remote+'; mkdir -m 700 '+remote+'; tar -xzf - -C '+remote
    receipt={"schema":"NSP_TITLE_RELEASE_V1","run_id":run,"action":action,"source_head":manifest["candidate_head"],
             "status":"STAGING","files":8,"paid_sku":11,"free_materials":10,"production_modified":False}
    stage_started=False
    apply_attempted=False
    try:
        call(ssh+[cmd],data=archive,timeout=85)
        stage_started=True
        def phase(mode,timeout=65):
            return json.loads(call(ssh+['php '+remote+'/transaction.php '+mode+' '+site+' '+remote],timeout=timeout))
        pre=phase("preflight")
        assert pre["status"]=="PREFLIGHT_PASS" and pre["scope"]==8 and pre["production_writes"] is False
        write_report("title-preflight.json",pre)
        receipt["status"]="PREFLIGHT_PASS";write_report("title-state-preflight.json",receipt)
        if action=="titles-preflight":
            print("NSP_TITLE_PREFLIGHT_PASS; NO_PUBLIC_FILES_MODIFIED")
            return
        apply_attempted=True
        res=phase("apply",timeout=110)
        assert res["status"]=="APPLIED_AND_VERIFIED" and res["files"]==8
        write_report("title-apply.json",res)
        ver=phase("verify")
        assert ver["status"]=="VERIFIED" and ver["files"]==8
        write_report("title-verify.json",ver)
        def inspect(row):
            path=row["path"]
            url="https://nastoronepodryadchika.ru/"+path+"?nsp_titles="+run
            req=Request(url,headers={"Cache-Control":"no-cache","Accept-Encoding":"identity","User-Agent":"NSP-Title-QA/1.0"})
            with urlopen(req,timeout=17) as response:
                assert response.status==200 and urlsplit(response.url).hostname=="nastoronepodryadchika.ru"
                data=response.read(300001)
            assert SHA(data)==row["after"],"PUBLIC_HTTPS_SHA:"+path
            return {"path":path,"http":200,"sha256":SHA(data)}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            public=list(pool.map(inspect,rows))
        assert len(public)==8
        write_report("title-https.json",{"status":"PASS","files":public})
        # Independent second server process after HTTPS: detect intervening changes.
        ver2=phase("verify")
        assert ver2["status"]=="VERIFIED" and ver2["files"]==8
        receipt["status"]="PUBLISHED_AND_HTTPS_VERIFIED"
        receipt["production_modified"]=True
        receipt["public"]=public
        write_report("title-release-state.json",receipt)
        print("NSP_TITLES_PUBLISHED_AND_VERIFIED; HTTPS_FILES=8")
    except BaseException as exc:
        receipt["status"]="FAILED"
        receipt["error_type"]=type(exc).__name__
        if apply_attempted and stage_started:
            try:
                result=phase("rollback",timeout=75)
                if result["status"]=="ROLLBACK_VERIFIED":
                    receipt["status"]="FAILED_ROLLBACK_VERIFIED"
            except BaseException as rb:
                receipt["status"]="MANUAL_RECOVERY_REQUIRED"
                receipt["rollback_error_type"]=type(rb).__name__
        write_report("title-release-state.json",receipt)
        raise

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit(8)
    main(sys.argv[1])
