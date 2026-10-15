#!/usr/bin/env python3
"""Exact-source regression gate for P3 DOCX №09 cross-document sheet reference."""
import hashlib, io, json, pathlib, subprocess, zipfile, xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
RECORD = json.loads((HERE / "manifest.json").read_text())
BEFORE = RECORD["replacement_before"].encode("utf-8")
AFTER = RECORD["replacement_after"].encode("utf-8")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    src = subprocess.check_output([
        "git", "-C", str(REPO), "show",
        RECORD["base_commit"] + ":" + RECORD["source_path"]
    ])
    dst = (HERE / "09-tipovye-oshibki.docx").read_bytes()
    assert sha(src) == RECORD["source_sha256"]
    assert sha(dst) == RECORD["candidate_sha256"]
    with zipfile.ZipFile(io.BytesIO(src)) as a, zipfile.ZipFile(io.BytesIO(dst)) as b:
        assert a.testzip() is None and b.testzip() is None
        assert a.namelist() == b.namelist()
        for part in a.namelist():
            original, modified = a.read(part), b.read(part)
            if part == "word/document.xml":
                assert original.count(BEFORE) == 1
                assert modified == original.replace(BEFORE, AFTER, 1)
                ET.fromstring(modified)
            else:
                assert original == modified, "Unexpected changed OOXML member: " + part
    print(json.dumps({
        "verdict": "PASS_EXACT_ONE_REFERENCE_CORRECTION_ONLY",
        "candidate_sha256": RECORD["candidate_sha256"],
        "other_ooxml_members_byte_identical": True,
        "native_word": RECORD["native_word"],
        "full_product_G1_G8": "HOLD"
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
