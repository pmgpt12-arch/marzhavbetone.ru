#!/usr/bin/env python3
"""Reproducible 11-member P3 candidate (no canonical replacement)."""
import hashlib, io, json, pathlib, subprocess, xml.etree.ElementTree as ET, zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
HEAD = "c5e23a35b8ee2ca52165406806e1ab62cf38f4a1"
P3 = "tools/candidates/p3-full-11-preflight-20261015/"
OLD_MANIFEST = P3 + "manifest.json"
NEW_06 = "tools/candidates/p3-validation-alerts-20261015/06-zhurnal-peredachi.xlsx"
NEW_09 = "tools/candidates/p3-doc09-sheet-reference-20261015/09-tipovye-oshibki.docx"
SHA_06 = "7efe0218defcad70921a87dcce04700a75fd8a5075a25be3874ccf9785c153a0"
SHA_09 = "d107fe9cf43acb7aec2b680736856637a22b422bd55698c237cb721e1dcffafa"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def sha(b):
    return hashlib.sha256(b).hexdigest()

def git_get(path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", HEAD + ":" + path])

def assemble(records):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for entry, data in records:
            info = zipfile.ZipInfo(entry["name"], date_time=(2026,10,15,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return output.getvalue()

def main():
    old = json.loads(git_get(OLD_MANIFEST))
    assert old["composition"] == {"total":11,"docx":7,"xlsx":2,"pdf":1,"txt":1}
    assert len(old["files"]) == 11
    records = []
    for item in old["files"]:
        name = pathlib.PurePosixPath(item["path"]).name
        path = P3 + item["path"]
        expected = item["sha256"]
        if name == "06-zhurnal-peredachi.xlsx":
            assert expected == "862daec8caad602c044f147f64768ed65cbb7497072d95c55df5d390acea14f3"
            path, expected = NEW_06, SHA_06
        if name == "09-tipovye-oshibki.docx":
            assert expected == "465935a45415804811ec167509520d414ffe5a0f19d4b37fea2465df24dafbcf"
            path, expected = NEW_09, SHA_09
        data = git_get(path)
        assert sha(data) == expected, "SOURCE_HASH_MISMATCH:" + name
        records.append(({"name":name, "relative_source_path":path,
                         "source_commit":HEAD, "sha256":expected, "bytes":len(data)},data))
    names = [row["name"] for row,_ in records]
    assert len(names) == len(set(names)) == 11
    intro = next(data.decode("utf-8") for row,data in records if row["name"]=="00-START-HERE.txt")
    assert all(name in intro for name in names if name != "00-START-HERE.txt"), "START-REFERENCE_MISSING"
    def member(n):
        return next(data for row,data in records if row["name"]==n)
    assert member("08-algoritm-proverki.pdf").startswith(b"%PDF-")
    for row,data in records:
        if row["name"].endswith((".xlsx",".docx")):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                assert z.testzip() is None
                if row["name"] == "02-reestr-prilozheniy.xlsx":
                    wb = ET.fromstring(z.read("xl/workbook.xml"))
                    assert "Реестр приложений" in [s.get("name") for s in wb.iter(NS+"sheet")]
                if row["name"] == "06-zhurnal-peredachi.xlsx":
                    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
                    rules = list(sheet.iter(NS+"dataValidation"))
                    assert len(list(sheet.iter(NS+"f"))) == 50
                    assert len(rules) == 7 and all(r.get("showErrorMessage") in ("true","1") and r.get("errorStyle")=="stop" for r in rules)
                if row["name"] == "09-tipovye-oshibki.docx":
                    doc = ET.fromstring(z.read("word/document.xml"))
                    txt = " ".join(t.text or "" for t in doc.iter(W+"t"))
                    assert "№02, лист «Реестр приложений»" in txt
                    assert "№02, лист «Реестр»" not in txt
    zipped = assemble(records)
    assert zipped == assemble(records), "NON_DETERMINISTIC"
    with zipfile.ZipFile(io.BytesIO(zipped)) as z:
        assert z.testzip() is None and z.namelist() == names
        assert all(sha(z.read(row["name"])) == row["sha256"] for row,_ in records)
    manifest = {
        "schema_version":1,"role":"candidate_not_nominated",
        "base_pr":648,"source_head":HEAD,"composition":old["composition"],
        "archive_sha256":sha(zipped),"files":[row for row,_ in records],
        "acceptance":{"archive":"PASS_11_OF_11","deterministic":"PASS",
                      "cross_document":"PASS_BASIC_REFERENCES",
                      "native_office":"PREVIOUS_EXACT_SHA_RECEIPTS_REUSED",
                      "independent_buyer":"OPEN","release":"HOLD","G1_G8":"0/13"}
    }
    (HERE/"P3-11-buyer-candidate-20261015.zip").write_bytes(zipped)
    (HERE/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"verdict":"PASS_DETERMINISTIC_INTEGRATION_ONLY",
                      "archive_sha256":sha(zipped),"members":len(names),
                      "bytes":len(zipped)},ensure_ascii=False))

if __name__ == "__main__":
    main()
