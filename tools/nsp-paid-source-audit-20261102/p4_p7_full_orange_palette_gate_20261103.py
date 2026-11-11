#!/usr/bin/env python3
"""Release-blocking read-only applied ORANGE font+fill check for 7 QA candidate XLSX.

If a customer-visible font or fill is still E85D22, status is FAIL and exit 2.
The approved title accent is muted gold #8E6F32, the header fill graphite #262F37.
"""
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
import pathlib
import re
import sys
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT=pathlib.Path("/home/denis/projects/nsp-paid-source-audit-20261102/tools/nsp-paid-source-audit-20261102")
MANIFEST=ROOT/"palette-candidates-20261103/SIX_PALETTE_CANDIDATES_RECEIPT.json"
FIRST=ROOT/"p4-35a-visual-20261103/candidate/P4-35A-REESTR-GRAPHITE-QA-ONLY.json"
NS="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
ORANGE="E85D22"
def digest(content):return sha256(content).hexdigest()

def inspect(blob):
    found=[]
    with ZipFile(BytesIO(blob)) as z:
        assert z.testzip() is None, "ZIP_CRC"
        root=ET.fromstring(z.read("xl/styles.xml"))
        fonts=root.find(NS+"fonts").findall(NS+"font")
        fills=root.find(NS+"fills").findall(NS+"fill")
        xfs=root.find(NS+"cellXfs").findall(NS+"xf")
        orange_font_ids=set()
        for ix,f in enumerate(fonts):
            color=f.find(NS+"color")
            if color is not None and color.get("rgb","").upper()[-6:]==ORANGE:
                orange_font_ids.add(ix)
        orange_fill_ids=set()
        for ix,f in enumerate(fills):
            pat=f.find(NS+"patternFill")
            fg=pat.find(NS+"fgColor") if pat is not None and pat.get("patternType")=="solid" else None
            if fg is not None and fg.get("rgb","").upper()[-6:]==ORANGE:
                orange_fill_ids.add(ix)
        for path in z.namelist():
            if not re.fullmatch(r"xl/worksheets/sheet\d+\.xml",path):continue
            for cell in ET.fromstring(z.read(path)).iter(NS+"c"):
                s=int(cell.get("s","0"))
                assert 0<=s<len(xfs), "XLSX_STYLE_REFERENCE"
                xf=xfs[s]
                if int(xf.get("fontId","0")) in orange_font_ids:
                    found.append({"sheet":path,"cell":cell.get("r"),"type":"font"})
                if int(xf.get("fillId","0")) in orange_fill_ids:
                    found.append({"sheet":path,"cell":cell.get("r"),"type":"fill"})
    return found

def main():
    first=json.loads(FIRST.read_text())
    six=json.loads(MANIFEST.read_text())
    files=[(ROOT/"p4-35a-visual-20261103/candidate/P4-35A-REESTR-GRAPHITE-QA-ONLY.xlsx",first["candidate_sha256"])]
    files.extend((pathlib.Path(e["path"]),e["candidate_sha256"]) for e in six["candidates"])
    assert len(files)==7
    results=[]
    for path,pin in files:
        raw=path.read_bytes()
        assert digest(raw)==pin, "CANDIDATE_SHA_PIN_DRIFT:"+path.name
        flagged=inspect(raw)
        results.append({"file":path.name,"sha256":pin,"orange_applied":len(flagged),"locations":flagged})
    total=sum(item["orange_applied"] for item in results)
    out={"status":"BLOCK_RELEASE_APPLIED_ORANGE" if total else "PALETTE_NO_APPLIED_ORANGE_PASS",
         "files":len(files),"orange_applied_total":total,
         "count_by_type":dict(Counter(e["type"] for r in results for e in r["locations"])),
         "results":results,"release_allowed":False}
    print(json.dumps(out,ensure_ascii=False))
    return 2 if total else 0

if __name__=="__main__":
    sys.exit(main())
