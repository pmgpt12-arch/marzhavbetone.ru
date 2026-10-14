#!/usr/bin/env python3
from copy import copy
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
from xml.etree import ElementTree as ET
import hashlib, io, json, os, subprocess

ROOT=Path("/home/denis/projects/mb001-p11-buyer-wording-20261014")
BASE=ROOT/"tools/candidates/portfolio-owner-pdf-20261013"
SRC=BASE/"13-raschet-metrami"
EV=BASE/"p11-buyer-wording-delta-20261014"
TARGET=SRC/"50-slovar-poley-raschet-metrami.docx"
OLDZIP=BASE/"p11-t6-eight-files-candidate-ics-20261014.zip"
NEWZIP=BASE/"p11-t6-eight-files-candidate-buyer-wording-20261014.zip"
HEAD="a9be7e88d0b4bae12bcc230c7184dbb2ea44eb4b"
OLDZIP_SHA="ee07ec000a1076a64cc9ddbc6a735f924be9e9eaf8b376a473897858fed1dbe8"
OLDTARGET_SHA="6f40e5d3757d77d6460efb990f459167220f5fb9f3f36a6a6bcfb92b415869d5"
REVIEW_SHA="77e59d54655dc62be220e3635810fd048abdeddeacafc87d31203093cd5d3fc0"
OLD="Телефон и адрес электронной почты для суда"
NEW="Рабочие телефон и адрес электронной почты для связи"
OTHER={
"00-START-HERE.txt":"2f895a2f2b8ea5e166c8f18dd416465f2651b3562068551fc9f26841fd5dcf3a",
"51-algoritm-raschet-metrami.pdf":"2a4c98dc4a1b131dbccb787276f487a17a76a0c6643932c0ee0ca666601135d7",
"52-chek-list-raschet-metrami.docx":"6094a91af0a2e750a1ef71f9b394ea49207af11f8c5420ade1a7da48ff79fd38",
"53-zapros-status-obekta.docx":"c3fccbdc5e7e6841ca8c48b5ab1c199bdebe0d2f4990c232040d20f70bfc023e",
"54-zapros-sostoyanie-escrow.docx":"8e76f513b4f72c51bd8e9ad1bd56c27409285585b2f38f96c76b5f8dfbfa4f96",
"55-pamyatka-punkt-ustupki-escrow.pdf":"20f65a850db70836b2897dc747ed6478781641e3a4f5a537b094a7afec0814a2",
"56-pervyy-den-do-podpisi.docx":"9c40a96498037b53a68ecea6f3ee57129a9f2c236d1073d1818c603016260807"}
ORDER=["00-START-HERE.txt","50-slovar-poley-raschet-metrami.docx","51-algoritm-raschet-metrami.pdf","52-chek-list-raschet-metrami.docx","53-zapros-status-obekta.docx","54-zapros-sostoyanie-escrow.docx","55-pamyatka-punkt-ustupki-escrow.pdf","56-pervyy-den-do-podpisi.docx"]
W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def shab(b): return hashlib.sha256(b).hexdigest()
def shaf(p): return shab(p.read_bytes())
def fsdir(p):
    fd=os.open(p,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
def abytes(p,b):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+".tmp")
    with t.open("wb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
    os.replace(t,p); fsdir(p.parent)
def ajson(p,o): abytes(p,(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode())
def visible(b):
    r=ET.fromstring(b)
    return "".join(n.text or "" for n in r.iter(W+"t"))

def run():
    actual_head=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
    assert actual_head==HEAD,(actual_head,HEAD)
    before=TARGET.read_bytes(); assert shab(before)==OLDTARGET_SHA
    with ZipFile(io.BytesIO(before)) as z:
        infos=z.infolist(); parts={i.filename:z.read(i.filename) for i in infos}
    xb=parts["word/document.xml"]; s=xb.decode("utf-8")
    assert s.count(OLD)==1 and NEW not in s
    xa=s.replace(OLD,NEW,1).encode("utf-8"); ET.fromstring(xa)
    after=dict(parts); after["word/document.xml"]=xa
    changed=[n for n in parts if parts[n]!=after[n]]
    assert changed==["word/document.xml"]
    assert visible(xa)==visible(xb).replace(OLD,NEW,1)
    buf=io.BytesIO()
    with ZipFile(buf,"w") as z:
        for i in infos: z.writestr(copy(i),after[i.filename])
    abytes(TARGET,buf.getvalue())
    with ZipFile(TARGET) as z:
        assert z.testzip() is None
        assert {n:z.read(n) for n in z.namelist()}==after
    newtarget=shaf(TARGET)
    assert shaf(OLDZIP)==OLDZIP_SHA
    expected=dict(OTHER); expected["50-slovar-poley-raschet-metrami.docx"]=newtarget
    expected={n:expected[n] for n in ORDER}
    actual={n:shaf(SRC/n) for n in ORDER}; assert actual==expected,(actual,expected)
    out=io.BytesIO()
    with ZipFile(out,"w",compression=ZIP_DEFLATED,compresslevel=9) as z:
        for n in ORDER:
            i=ZipInfo(n,date_time=(2026,10,14,10,20,0)); i.compress_type=ZIP_DEFLATED
            i.external_attr=0o100644<<16; i.create_system=3; z.writestr(i,(SRC/n).read_bytes())
    abytes(NEWZIP,out.getvalue())
    with ZipFile(NEWZIP) as z:
        names=z.namelist(); bad=z.testzip(); extracted={n:shab(z.read(n)) for n in names}
    assert bad is None and names==ORDER and len(names)==len(set(names)) and extracted==expected
    newzip=shaf(NEWZIP); now=datetime.now(timezone.utc).isoformat()
    receipt={"schema_version":1,"id":"P11-BUYER-WORDING-DELTA-20261014","status":"PASS_AUTHOR_EXACT_DELTA_AND_ARCHIVE_ONLY","finished_at_utc":now,"checkpoint_policy":"verified_only",
      "input":{"head":HEAD,"archive_path":str(OLDZIP.relative_to(ROOT)),"archive_sha256":OLDZIP_SHA,"target_path":str(TARGET.relative_to(ROOT)),"target_sha256":OLDTARGET_SHA,"independent_failure_receipt_sha256":REVIEW_SHA},
      "delta":{"old_text":OLD,"new_text":NEW,"occurrences":1,"changed_ooxml_parts":changed,"visible_text_exact_replacement":True,"new_target_sha256":newtarget},
      "output":{"archive_path":str(NEWZIP.relative_to(ROOT)),"archive_sha256":newzip,"archive_bytes":NEWZIP.stat().st_size,"ordered_members":names,"member_sha256":extracted,"zip_crc":"PASS","extracted_sha256_match":"8_OF_8_PASS","unchanged_members":"7_OF_7_BYTE_IDENTICAL"},
      "route":"deterministic Python zip/OOXML; no Office, render or model call",
      "acceptance":["exact parent head","one exact buyer-visible replacement","only word/document.xml payload changed in file 50","other seven archive members byte-identical","new archive unique root members 8/8, CRC PASS, extracted SHA 8/8"],
      "limitations":["author cannot independently accept own delta/archive","no new visual, native Office, release, nomination, production or delivery acceptance","release HOLD; G1-G8 0/13"],
      "next_step":"commit isolated candidate, independent exact-text/OOXML/archive delta-review, exact-head CI; retain HOLD","release_authorized":False,"model_calls":0,"no_paid_api":True}
    manifest={"schema_version":1,"id":"P11-T6-RELEASE-MANIFEST-BUYER-WORDING-HOLD","status":"HOLD","input_head":HEAD,"supersedes_archive_sha256":OLDZIP_SHA,"candidate_archive_sha256":newzip,"buyer_files":extracted,"accepted_author_scope":["exact one-string OOXML delta","archive CRC","8/8 extracted member SHA"],"open_gates":["independent delta/archive acceptance","ARTIFACT-REGISTRY nomination","controlled production delivery"],"G1_G8_accepted_products":0,"portfolio_total":13,"release_authorized":False}
    ajson(EV/"buyer-wording-delta-receipt.json",receipt); ajson(EV/"release-manifest-buyer-wording-HOLD.json",manifest)
    summary={"status":receipt["status"],"target_sha256":newtarget,"archive_sha256":newzip,"archive_bytes":NEWZIP.stat().st_size,"receipt_sha256":shaf(EV/"buyer-wording-delta-receipt.json"),"hold_sha256":shaf(EV/"release-manifest-buyer-wording-HOLD.json")}
    ajson(EV/"result.json",summary); abytes(EV/"exit.code",b"0\n")
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True)); return 0

if __name__=="__main__":
    try: raise SystemExit(run())
    except Exception as e:
        ajson(EV/"failure.json",{"schema_version":1,"id":"P11-BUYER-WORDING-DELTA-20261014","status":"FAIL","finished_at_utc":datetime.now(timezone.utc).isoformat(),"error_type":type(e).__name__,"error":str(e),"input_head":HEAD,"release_authorized":False})
        abytes(EV/"exit.code",b"1\n"); raise
