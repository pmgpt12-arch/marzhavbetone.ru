#!/usr/bin/env python3
"""Independent P2 A4 instruction candidate gate. Structural/editorial only; no release claim."""
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"tools/candidates/p2-instruction-style-20261013"
PARENT=DIR/"00-INSTRUKCIYA-parent.docx"
CANDIDATE=DIR/"00-INSTRUKCIYA.docx"
PDF=DIR/"00-INSTRUKCIYA-preview.pdf"
RECEIPT=DIR/"review-receipt.json"
PARENT_SHA="0bb84800a2bac43b50f4521db4e6397963f76377aea350b42ea4cc6bc8cf2eb4"
CANDIDATE_SHA="0f3882fae04bd8bf32a9c368abc24e6d4c1c41fad5d008d37bfc522098148b11"
PDF_SHA="b57be3f02a1765526b49662c45434cb7910f1271a38186660599a6aecba945b9"
W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
UPDATED={2,4,5,6,7,11,16,19,20,22,24,25,93}
FORBIDDEN=["шаблон","юридическая консультация","не заменяет юриста",
           "допы согласованы","на сами деньги","без подписанных бумаг","посчитайте цену"]
def sha(data):return hashlib.sha256(data).hexdigest()
def zipdata(path):
    b=path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        assert z.testzip() is None, "CRC_ERROR"
        assert len(z.namelist())==len(set(z.namelist()))
        return sha(b),{n:z.read(n) for n in z.namelist()}
def paras(xml):
    root=ET.fromstring(xml)
    return ["".join(t.text or "" for t in p.iter(W+"t")) for p in root.iter(W+"p")]
def forb(text):return [f for f in FORBIDDEN if f in text.casefold()]
def refs(text):return sorted(re.findall(r"(?<!\w)[\w.-]+\.(?:docx|xlsx|pdf|txt)\b",text,re.I))
def run():
    h0,a=zipdata(PARENT);h1,b=zipdata(CANDIDATE)
    assert h0==PARENT_SHA and h1==CANDIDATE_SHA, "INPUT_HASH_DRIFT"
    assert set(a)==set(b) and len(a)==17, "PACKAGE_MEMBERS_CHANGED"
    parts={n for n in a if a[n]!=b[n]}
    assert parts=={"word/document.xml"},("UNEXPECTED_XML_PARTS",parts)
    old,new=paras(a["word/document.xml"]),paras(b["word/document.xml"])
    assert len(old)==len(new)==97,("PARAGRAPH_COUNT",len(old),len(new))
    changed={i+1 for i,(x,y) in enumerate(zip(old,new)) if x!=y}
    assert changed==UPDATED,("CHANGED_PARAGRAPHS",sorted(changed))
    orig="\n".join(old);updated="\n".join(new)
    assert refs(orig)==refs(updated), "CROSS_FILE_REFERENCES_CHANGED"
    assert not forb(updated),("BANNED_PHRASES",forb(updated))
    assert "Случай А подготовлен к началу работ, когда уполномоченные представители письменно согласовали" in updated
    assert "урегулирование задолженности за выполненные работы" in updated
    assert "приказом Минстроя России" in updated
    pz=list(ET.fromstring(b["word/document.xml"]).iter(W+"pgSz"))
    assert pz and pz[-1].get(W+"w")=="11906" and pz[-1].get(W+"h")=="16838", "NOT_A4"
    rawpdf=PDF.read_bytes()
    assert rawpdf.startswith(b"%PDF-") and sha(rawpdf)==PDF_SHA and len(rawpdf)>50000, "PDF_PREVIEW_INVALID"
    assert forb(updated+" Допы согласованы"),"NEGATIVE_1_NOT_CAUGHT"
    assert forb(updated+" посчитайте цену"),"NEGATIVE_2_NOT_CAUGHT"
    assert forb(updated+" без подписанных бумаг"),"NEGATIVE_3_NOT_CAUGHT"
    rec=json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert rec["candidate_sha256"]==CANDIDATE_SHA and rec["parent_sha256"]==PARENT_SHA, "RECEIPT_MISMATCH"
    print("P2_INSTRUCTION_STYLE_PASS: SHA exact, 17/17 ZIP parts, 13/97 paragraphs corrected, A4, 3 negative tests; no native Word, legal, buyer, G1-G8")
    return 0
if __name__=="__main__":
    try:sys.exit(run())
    except Exception as e:
        print(f"P2_INSTRUCTION_STYLE_FAIL: {type(e).__name__}: {e}",file=sys.stderr)
        sys.exit(1)
