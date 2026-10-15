#!/usr/bin/env python3
"""Freeze and verify the corrected P3 11-file buyer candidate, no canonical write."""
import hashlib, io, json, pathlib, subprocess, xml.etree.ElementTree as ET, zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
HEAD = "7b6204ef58cdee70ad8ea44f24f57e1f90d7f897"
OLD_MANIFEST = "tools/candidates/p3-final-11-integration-20261015/manifest.json"
PATH_02 = "tools/candidates/p3-buyer-negative-20261015/02-reestr-prilozheniy.xlsx"
PATH_06 = "tools/candidates/p3-buyer-negative-20261015/06-zhurnal-peredachi.xlsx"
SHA_02 = "d2685f1606ff392cb3d7a23155f047fc11cce9b660541608d3058936a3887a9b"
SHA_06 = "029b048be85fef8f38e2c48e14ddfec41cf208151b7c406ac4603886f676bffd"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def get(path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", HEAD+":"+path])

def build(files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for row,data in files:
            i=zipfile.ZipInfo(row["name"],date_time=(2026,10,15,0,0,0))
            i.compress_type=zipfile.ZIP_DEFLATED
            i.external_attr=0o100644<<16
            i.create_system=3
            z.writestr(i,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    return out.getvalue()

def main():
    original=json.loads(get(OLD_MANIFEST))
    assert original["composition"]=={"total":11,"docx":7,"xlsx":2,"pdf":1,"txt":1}
    inputs=[]
    for source in original["files"]:
        row=dict(source)
        name=row["name"]
        if name=="02-reestr-prilozheniy.xlsx":
            row["relative_source_path"],row["sha256"]=PATH_02,SHA_02
        if name=="06-zhurnal-peredachi.xlsx":
            row["relative_source_path"],row["sha256"]=PATH_06,SHA_06
        row["source_commit"]=HEAD
        data=get(row["relative_source_path"])
        assert sha(data)==row["sha256"],name
        row["bytes"]=len(data)
        inputs.append((row,data))
    assert len(inputs)==11 and len({r["name"] for r,_ in inputs})==11
    intro=next(d.decode("utf-8") for r,d in inputs if r["name"]=="00-START-HERE.txt")
    assert all(r["name"] in intro for r,_ in inputs if r["name"]!="00-START-HERE.txt")
    for row,data in inputs:
        if row["name"].endswith(".xlsx"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                assert z.testzip() is None
                sheet=ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
                n=sum(1 for _ in sheet.iter(NS+"f"))
                rules=list(sheet.iter(NS+"dataValidation"))
                assert n==50 and len(rules)==(5 if row["name"].startswith("02-") else 7)
                assert all(x.get("showErrorMessage") in ("1","true") and x.get("errorStyle")=="stop" for x in rules)
    archive=build(inputs)
    assert archive==build(inputs)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        assert z.testzip() is None and z.namelist()==[r["name"] for r,_ in inputs]
        assert all(sha(z.read(r["name"]))==r["sha256"] for r,_ in inputs)
    manifest={"schema_version":1,"source_head":HEAD,"role":"candidate_not_nominated",
              "base_pr":650,"composition":original["composition"],"archive_sha256":sha(archive),
              "files":[r for r,_ in inputs],
              "status":{"archive":"PASS_11_OF_11","formula_structural":"PASS",
                        "office_exact_open":"PASS_02_06","office_derived_scenarios":"PASS_12_OF_12",
                        "native_ui_typing_paste":"OPEN","independent_full_buyer":"OPEN",
                        "formal_nomination":"HOLD","release":"HOLD","G1_G8":"0/13"}}
    (HERE/"P3-11-buyer-revised-20261015.zip").write_bytes(archive)
    (HERE/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"verdict":"PASS_BOUNDED_REBUILD","archive_sha256":sha(archive),"members":len(inputs),"bytes":len(archive)},ensure_ascii=False))

if __name__=="__main__":
    main()
