#!/usr/bin/env python3
"""Read-only P4/P7 QA v2: print, row-3 header geometry and style attributes."""
from pathlib import Path
from zipfile import ZipFile
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
from io import BytesIO
import json, re, xml.etree.ElementTree as ET
ROOT=Path("/mnt/server-data/nsp/operations/qa-style-candidates-v2-20261103")
M=json.loads((ROOT/"V2_GOLD_FONT_CANDIDATES_MANIFEST.json").read_text())
OUT=ROOT/"PRINT_GEOMETRY_STATIC_V2_R3_20261103.json"
S="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R="{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
def cell_text(c,shared):
    direct="".join(x.text or "" for x in c.iter(S+"t"))
    if direct:return direct
    # OOXML t="str" stores the header as <v>Unicode text</v>, not <is><t>.
    if c.get("t")=="str":
        v=c.find(S+"v")
        return v.text if v is not None and v.text else ""
    if c.get("t")!="s":return direct
    index=c.find(S+"v")
    assert index is not None and index.text is not None, "SHARED_STRING_MISSING"
    n=int(index.text)
    assert 0<=n<len(shared), "SHARED_STRING_INDEX_INVALID"
    return shared[n]
def check(path,pin):
    raw=path.read_bytes()
    assert sha256(raw).hexdigest()==pin,"SOURCE_SHA_DRIFT"
    with ZipFile(BytesIO(raw)) as z:
        assert z.testzip() is None
        wt=ET.fromstring(z.read("xl/workbook.xml"))
        shared=[]
        if "xl/sharedStrings.xml" in z.namelist():
            shared_root=ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared=["".join(t.text or "" for t in si.iter(S+"t")) for si in shared_root.findall(S+"si")]
        sheets=[s.get("name") for s in wt.findall(S+"sheets/"+S+"sheet")]
        defined=[{"name":n.get("name"),"value":n.text,"localSheetId":n.get("localSheetId")} for n in wt.iter(S+"definedName") if n.get("name")=="_xlnm.Print_Area"]
        style=ET.fromstring(z.read("xl/styles.xml"))
        styles=style.find(S+"cellXfs").findall(S+"xf")
        fonts=style.find(S+"fonts").findall(S+"font")
        fills=style.find(S+"fills").findall(S+"fill")
        report=[]
        for index,name in enumerate(sorted(s for s in z.namelist() if re.fullmatch("xl/worksheets/sheet[0-9]+[.]xml",s))):
            root=ET.fromstring(z.read(name))
            cells={c.get("r"):c for c in root.iter(S+"c")}
            info={"sheet":sheets[index] if index<len(sheets) else f"sheet{index+1}","xml_part":name}
            dim=root.find(S+"dimension"); info["dimension"]=dim.get("ref") if dim is not None else None
            cols=root.find(S+"cols")
            coldef={}
            if cols is not None:
                for col in cols.findall(S+"col"):
                    start=int(col.get("min"));end=int(col.get("max"))
                    for n in range(start,min(end,30)+1):
                        coldef[n]={"width":float(col.get("width","0")),"hidden":col.get("hidden")=="1"}
            info["col_widths_A_to_Q"]=[coldef.get(i) for i in range(1,18)]
            row3=next((r for r in root.iter(S+"row") if r.get("r")=="3"),None)
            info["row3"]={"height":row3.get("ht") if row3 is not None else None,
                          "customHeight":row3.get("customHeight") if row3 is not None else None,
                          "spans":row3.get("spans") if row3 is not None else None}
            headers=[]
            for k in range(1,18):
                addr=chr(64+k)+"3"
                c=cells.get(addr)
                if c is None:continue
                sid=int(c.get("s","0"));xf=styles[sid]
                aln=xf.find(S+"alignment");font=fonts[int(xf.get("fontId","0"))]
                fsize=font.find(S+"sz")
                v=cell_text(c,shared)
                headers.append({"address":addr,"label":v[:80],
                      "char_count":len(v),"col_width":coldef.get(k,{}).get("width"),
                      "wrap":aln.get("wrapText") if aln is not None else None,
                      "shrink":aln.get("shrinkToFit") if aln is not None else None,
                      "font_size":fsize.get("val") if fsize is not None else None})
            info["header_row3"]=headers
            page=root.find(S+"pageSetup");pageMargins=root.find(S+"pageMargins")
            printOpts=root.find(S+"printOptions")
            sheetPr=root.find(S+"sheetPr");ps=sheetPr.find(S+"pageSetUpPr") if sheetPr is not None else None
            info["page_setup"]=page.attrib if page is not None else None
            info["page_margins"]=pageMargins.attrib if pageMargins is not None else None
            info["print_options"]=printOpts.attrib if printOpts is not None else None
            info["page_set_up_pr"]=ps.attrib if ps is not None else None
            report.append(info)
        return {"sheets":report,"defined_print_areas":defined}
def main():
    assert not OUT.exists(),"NO_OVERWRITE"
    reports=[]
    for item in M["v2_candidates"]:
        p=ROOT/item["candidate"]
        reports.append({"file":p.name,"sha256":item["candidate_sha256"],**check(p,item["candidate_sha256"])})
    result={"schema":"NSP_P4_P7_V2_STATIC_PRINT_GEOMETRY_v1","timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "status":"PRINT_GEOMETRY_OBSERVED_NOT_NATIVE_PRINT_PASS",
            "files":reports,"native_office":"NOT_RUN",
            "note":"Some column headers may be wrapped or tiny when the sheet is scaled for A3; screen/print review still required."}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"files":len(reports),"summary":[{"file":f["file"],"sheet0":f["sheets"][0]["sheet"],
        "header":f["sheets"][0]["header_row3"],"page":f["sheets"][0]["page_setup"],"print_areas":len(f["defined_print_areas"])} for f in reports]},ensure_ascii=False))
if __name__=="__main__":main()
