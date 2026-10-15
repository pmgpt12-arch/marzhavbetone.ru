#!/usr/bin/env python3
"""Fail-closed exact-source checks for P3 buyer whitespace/link regressions."""
import hashlib, io, json, pathlib, re, subprocess, xml.etree.ElementTree as ET, zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
HEAD = "96f924dc5205590f96fec67dfb6a53cf9844be82"
P3 = "tools/candidates/p3-final-11-integration-20261015/P3-11-buyer-candidate-20261015.zip"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
TARGETS = {
    "02-reestr-prilozheniy.xlsx":"d2685f1606ff392cb3d7a23155f047fc11cce9b660541608d3058936a3887a9b",
    "06-zhurnal-peredachi.xlsx":"029b048be85fef8f38e2c48e14ddfec41cf208151b7c406ac4603886f676bffd"
}
TAGS = re.compile(rb"<f(?:\s[^>]*)?>.*?</f>", re.S)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def get_git_bytes(path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", HEAD + ":" + path])

def check_formulas(fname, formulas):
    assert len(formulas) == 50
    checks = 0
    for row in range(5,55):
        col = "I" if fname.startswith("02-") else "R"
        f = formulas[col+str(row)]
        if col == "I":
            assert f'LEN(TRIM(C{row}&""))=0' in f
            assert f'LEN(TRIM(G{row}&""))=0' in f
            checks += 2
        else:
            for inp in "CDEFIKQ":
                assert f'LEN(TRIM({inp}{row}&""))=0' in f
                checks += 1
            if row == 5:
                assert 'LEN(TRIM(O5&""))>0' in f
            else:
                assert f'COUNTIFS(A$5:A{row-1},O{row},C$5:C{row-1},C{row},D$5:D{row-1},D{row})=0' in f
                assert f'NOT(ISNUMBER(O{row}))' in f
            checks += 1
    return checks

def main():
    bundle = get_git_bytes(P3)
    result = {}
    with zipfile.ZipFile(io.BytesIO(bundle)) as old_bundle:
        assert old_bundle.testzip() is None
        for name, expected in TARGETS.items():
            original = old_bundle.read(name)
            fixed = (HERE/name).read_bytes()
            assert sha(fixed) == expected
            with zipfile.ZipFile(io.BytesIO(original)) as before, zipfile.ZipFile(io.BytesIO(fixed)) as after:
                assert before.testzip() is None and after.testzip() is None
                assert before.namelist() == after.namelist()
                changed = sorted(k for k in before.namelist() if before.read(k) != after.read(k))
                expect = ["xl/worksheets/sheet1.xml"]
                if name.startswith("06-"): expect += ["xl/sharedStrings.xml","xl/worksheets/sheet2.xml"]
                assert changed == sorted(expect), (name,changed)
                baseline = before.read("xl/worksheets/sheet1.xml")
                revised = after.read("xl/worksheets/sheet1.xml")
                assert TAGS.sub(b"<FORMULA>",baseline) == TAGS.sub(b"<FORMULA>",revised)
                root = ET.fromstring(revised)
                forms = {}
                for c in root.iter(NS+"c"):
                    f = c.find(NS+"f")
                    if f is not None:forms[c.get("r")] = f.text or ""
                n = check_formulas(name,forms)
                data_validation = list(root.iter(NS+"dataValidation"))
                expected_rules = 5 if name.startswith("02-") else 7
                assert len(data_validation)==expected_rules
                assert all(x.get("showErrorMessage") in ("1","true") and x.get("errorStyle")=="stop" for x in data_validation)
                if name.startswith("06-"):
                    before_sheet2=before.read("xl/worksheets/sheet2.xml")
                    after_sheet2=after.read("xl/worksheets/sheet2.xml")
                    for cell,oldidx,newidx in (("A8",1,5),("B8",10,9),("A9",1,5),("B9",10,9)):
                        oldtag=(f'<c r="{cell}" s="{oldidx}"').encode()
                        newtag=(f'<c r="{cell}" s="{newidx}"').encode()
                        assert before_sheet2.count(oldtag)==1
                        before_sheet2=before_sheet2.replace(oldtag,newtag,1)
                    assert before_sheet2==after_sheet2
                if name.startswith("06-"):
                    a=before.read("xl/sharedStrings.xml")
                    b=after.read("xl/sharedStrings.xml")
                    prior="номер прежней строки, дату или иной однозначный идентификатор".encode()
                    now="номер предыдущей строки из столбца «№»; программа проверяет соответствие КС-2/КС-3".encode()
                    assert a.count(prior)==1 and b==a.replace(prior,now,1)
                result[name]={"verdict":"PASS_EXACT_BYTE_PRESERVATION_AND_FORMULA_GATE","sha256":sha(fixed),"formula_rules":n,"data_validations":len(data_validation),"changed_zip_members":changed}
    # Negative fixtures test rejection of the very bug classes seen in native QA.
    bad = dict(forms)
    bad["R6"] = bad["R6"].replace('NOT(ISNUMBER(O6))',"FALSE()",1)
    try:check_formulas("06-zhurnal-peredachi.xlsx",bad)
    except AssertionError: negative = True
    else: negative = False
    assert negative
    print(json.dumps({"verdict":"PASS_STRUCTURAL_REGRESSION_ONLY","results":result,"negative_gate":True},ensure_ascii=False))

if __name__=="__main__":
    main()
