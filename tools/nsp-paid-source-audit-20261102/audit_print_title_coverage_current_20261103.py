#!/usr/bin/env python3
"""Read-only acceptance check: printed region vs titled first rows of current NSP XLSX."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import json, re, hashlib, xml.etree.ElementTree as ET, collections
from datetime import datetime, timezone
SRC=Path("/mnt/server-data/nsp/product-library/accepted-current-20261102")
OUT=Path("/home/denis/projects/nsp-paid-source-audit-20261102/tools/nsp-paid-source-audit-20261102/ALL_CURRENT_XLSX_PRINT_TITLE_COVERAGE_R2_20261103.json")
NS="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
def sha(x):return hashlib.sha256(x).hexdigest()
def read_cells(z,path,shared):
    tree=ET.fromstring(z.read(path))
    output={}
    for c in tree.iter(NS+"c"):
        address=c.get("r","")
        if not re.fullmatch(r"[A-Z]{1,3}[12]",address):continue
        s="".join(t.text or "" for t in c.iter(NS+"t"))
        v=c.find(NS+"v")
        if c.get("t")=="s" and v is not None and v.text:
            idx=int(v.text)
            if idx<len(shared):s=shared[idx]
        if c.get("t")=="str" and v is not None:s=v.text or s
        if s.strip():output[address]=s.strip()[:170]
    return output
def audit_workbook(data):
    with ZipFile(BytesIO(data)) as z:
        assert z.testzip() is None
        paths=sorted((n for n in z.namelist() if re.fullmatch("xl/worksheets/sheet[0-9]+[.]xml",n)),
                     key=lambda n:int(re.search(r"sheet([0-9]+)",n).group(1)))
        main=ET.fromstring(z.read("xl/workbook.xml"))
        sheets=[n.get("name") for n in main.findall(NS+"sheets/"+NS+"sheet")]
        defs=list(main.iter(NS+"definedName"))
        shared=[]
        if "xl/sharedStrings.xml" in z.namelist():
            sharedroot=ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared=["".join(t.text or "" for t in si.iter(NS+"t")) for si in sharedroot.findall(NS+"si")]
        results=[]
        for index,path in enumerate(paths):
            sheet_name=sheets[index] if index<len(sheets) else path
            cells=read_cells(z,path,shared)
            area=[(dn.text or "") for dn in defs if dn.get("name")=="_xlnm.Print_Area" and (dn.get("localSheetId")==str(index))]
            titles=[(dn.text or "") for dn in defs if dn.get("name")=="_xlnm.Print_Titles" and (dn.get("localSheetId")==str(index))]
            row_starts=[]
            dynamic_print_area=any("(" in text or ")" in text for text in area)
            for text in area:
                if "(" in text or ")" in text:continue
                row_starts.extend(int(m.group(1)) for m in re.finditer(r"\$[A-Z]{1,3}\$(\d+)(?=:)",text))
            start=min(row_starts) if row_starts else None
            top_title=any(a.endswith("1") for a in cells)
            subtitle=any(a.endswith("2") for a in cells)
            printed_titles=" ".join(titles)
            print_titles_cover_row1=bool(re.search(r"\$1:\$[1-9][0-9]*",printed_titles))
            missing=bool(start is not None and start>1 and top_title and not print_titles_cover_row1)
            results.append({"sheet":sheet_name,"part":path,"print_area":area,"print_titles":titles,
                            "print_area_start_row":start,"dynamic_print_area":dynamic_print_area,
                            "row1_text":{k:v for k,v in cells.items() if k.endswith("1")},
                            "row2_text":{k:v for k,v in cells.items() if k.endswith("2")},
                            "print_title_omission_candidate":missing,
                            "missing_explicit_print_area":not area,
                            "print_title_row1_included_by_repeating_rows":print_titles_cover_row1,
                            "row2_present":subtitle})
        return results
def main():
    assert not OUT.exists(), "REPORT_EXISTS_NO_OVERWRITE"
    archives=sorted(SRC.glob("paid/*.zip"))+sorted(SRC.glob("free/*.zip"))
    assert len(archives)==21,len(archives)
    documents=[];archlist=[]
    for archive in archives:
        raw=archive.read_bytes()
        archlist.append({"name":archive.name,"group":archive.parent.name,"sha256":sha(raw)})
        with ZipFile(BytesIO(raw)) as outer:
            assert outer.testzip() is None,archive.name
            for member in outer.namelist():
                if not member.lower().endswith(".xlsx"):continue
                source=outer.read(member)
                documents.append({"archive":archive.name,"group":archive.parent.name,"member":member,
                                  "member_sha256":sha(source),"worksheets":audit_workbook(source)})
    summary={"workbooks":len(documents),"sheets":sum(len(d["worksheets"]) for d in documents),
             "missing_print_title_candidates":sum(s["print_title_omission_candidate"] for d in documents for s in d["worksheets"]),
             "books_with_print_title_candidate":len([d for d in documents if any(s["print_title_omission_candidate"] for s in d["worksheets"])]),
             "without_explicit_print_area":sum(s["missing_explicit_print_area"] for d in documents for s in d["worksheets"]),
             "dynamic_print_area_sheets":sum(s["dynamic_print_area"] for d in documents for s in d["worksheets"])}
    assert summary["workbooks"]==37,summary
    report={"schema":"NSP_CURRENT_XLSX_PRINT_TITLE_COVERAGE_v2",
            "datetime_utc":datetime.now(timezone.utc).isoformat(),
            "source":str(SRC),"archive_count":len(archives),"archives":archlist,
            "summary":summary,"documents":documents,
            "notes":["A candidate is a nonempty title in row 1 omitted by an explicit Print_Area starting after row 1",
                     "Repeat-row Print_Titles can include row 1 and are checked separately",
                     "Static area reasoning is not native Excel print approval",
                     "All protected source ZIP bytes untouched"]}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    reread=json.loads(OUT.read_text())
    assert reread["summary"]==summary
    cases=[{"sku":d["archive"],"file":d["member"],"sheet":s["sheet"],"area":s["print_area"],"title":s["row1_text"]}
           for d in documents for s in d["worksheets"] if s["print_title_omission_candidate"]]
    print(json.dumps({"summary":summary,"cases":cases[:30],"report":str(OUT)},ensure_ascii=False))
if __name__=="__main__":main()
