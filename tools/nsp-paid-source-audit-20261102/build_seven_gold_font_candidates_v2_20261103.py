#!/usr/bin/env python3
"""Addressed palette QA v2: one font-color hex token in 7 SHA-pinned v1 XLSX.
Read-only on v1 and accepted source archives. No native/production effects.
"""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from hashlib import sha256
from copy import copy
import json,re,datetime
from p4_p7_full_orange_palette_gate_20261103 import inspect

ROOT=Path("/home/denis/projects/nsp-paid-source-audit-20261102/tools/nsp-paid-source-audit-20261102")
DEST=Path("/mnt/server-data/nsp/operations/qa-style-candidates-v2-20261103")
SOURCE_1=ROOT/"p4-35a-visual-20261103/candidate/P4-35A-REESTR-GRAPHITE-QA-ONLY.xlsx"
ONE=json.loads(SOURCE_1.with_suffix(".json").read_text())
SIX=json.loads((ROOT/"palette-candidates-20261103/SIX_PALETTE_CANDIDATES_RECEIPT.json").read_text())
H=lambda b:sha256(b).hexdigest()
CHUNK=re.compile(rb'<(?:[A-Za-z_][\w.-]*:)?color\s+rgb="(?:00|FF)E85D22"\s*/>')
COLORMATCH=re.compile(rb'E85D22')
TARGET=b"8E6F32"
old_files=[(SOURCE_1,ONE["candidate_sha256"])]
old_files.extend((Path(entry["path"]),entry["candidate_sha256"]) for entry in SIX["candidates"])
assert len(old_files)==7
assert SIX["orange_cells_before"]==65
assert not DEST.exists(), "DESTINATION_ALREADY_EXISTS_INSPECT_NO_RETRY"
results=[]
pending=[]
for source,pinned_sha in old_files:
    raw=source.read_bytes()
    assert H(raw)==pinned_sha, "SOURCE_QA_SHA_MISMATCH:"+source.name
    found=inspect(raw)
    assert found==[{"sheet":"xl/worksheets/sheet2.xml","cell":"A1","type":"font"}], (source.name,found)
    with ZipFile(BytesIO(raw)) as origin:
        assert origin.testzip() is None, "SOURCE_BAD_CRC"
        names=origin.namelist()
        assert len(names)==len(set(names))
        assert "xl/styles.xml" in names
        original_parts={name:origin.read(name) for name in names}
        styles=original_parts["xl/styles.xml"]
        matches=list(CHUNK.finditer(styles))
        assert len(matches)==1,(source.name,"FONT_COLOR_PATTERN",len(matches))
        m=matches[0]; sub=styles[m.start():m.end()]
        assert sub.count(b"E85D22")==1
        pos=styles.index(b"E85D22",m.start(),m.end())
        new_style=styles[:pos]+TARGET+styles[pos+6:]
        assert len(new_style)==len(styles)
        assert new_style[:pos]==styles[:pos] and new_style[pos+6:]==styles[pos+6:]
        assert new_style.count(b"E85D22")==styles.count(b"E85D22")-1
        buffer=BytesIO()
        with ZipFile(buffer,mode="w") as zz:
            for item in origin.infolist():
                # ZipFile.writestr mutates ZipInfo CRC; copy metadata and cache inputs first.
                zz.writestr(copy(item),new_style if item.filename=="xl/styles.xml" else original_parts[item.filename])
        candidate=buffer.getvalue()
        with ZipFile(BytesIO(candidate)) as verified:
            assert verified.testzip() is None
            assert verified.namelist()==names
            delta=[name for name in names if original_parts[name]!=verified.read(name)]
            assert delta==["xl/styles.xml"], (source.name,delta)
            assert verified.read("xl/styles.xml")==new_style
            assert all(original_parts[x]==verified.read(x) for x in names if x!="xl/styles.xml")
    assert inspect(candidate)==[],(source.name,"ORANGE_APPLIED_AFTER",inspect(candidate))
    outname=source.stem+"-GOLD-FONT-V2.xlsx"
    rec={"source":source.name,"source_sha256":pinned_sha,"candidate":outname,
         "candidate_sha256":H(candidate),"size_bytes":len(candidate),
         "changed_parts":["xl/styles.xml"],
         "single_token_before":"E85D22","single_token_after":"8E6F32",
         "target_tag":"font/color rgb", "target_address":"Инструкция!A1",
         "source_applied_orange_count":1,"after_applied_orange_count":0,
         "all_non_style_zip_members_byte_identical":True,
         "formulas_values_validation_print_unchanged":True,
         "no_origin_or_production_mutations":True,
         "native_final_sha":"PENDING"}
    pending.append((outname,candidate))
    results.append(rec)
assert sum(x["source_applied_orange_count"] for x in results)==7
DEST.mkdir(parents=True,exist_ok=False)
for name,data in pending:
    p=DEST/name
    assert not p.exists()
    p.write_bytes(data)
    assert H(p.read_bytes())==next(x["candidate_sha256"] for x in results if x["candidate"]==name)
manifest={
  "schema":"NSP_P4_P7_GOLD_FONT_QA_V2_v1",
  "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "status":"SEVEN_V2_STATIC_COLOR_ONLY_PASS_NATIVE_PENDING",
  "scope":"7 existing v1 QA XLSX; font color A1 on instruction sheet only",
  "old_orange_fills_after_v1":0, "old_orange_fonts_after_v2":0,
  "v1_count":7,"v2_count":7,"v2_candidates":results,
  "staged_directory":str(DEST),
  "no_buyer_zip_or_published_changes":True,
  "release_allowed":False,"full_qa_pass":False,
  "acceptance_remaining":["independent verifier over v2 and original source edition",
                         "Microsoft Excel LTSC 2024 native open and print for final v2 SHA",
                         "P4-35A header wrap review and owner release decision"]
}
p=DEST/"V2_GOLD_FONT_CANDIDATES_MANIFEST.json"
p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
assert json.loads(p.read_text())["v2_count"]==7
print(json.dumps({"status":manifest["status"],"count":len(results),
                  "sha256":[{"file":x["candidate"],"sha256":x["candidate_sha256"]} for x in results],
                  "manifest":str(p)},ensure_ascii=False))
