"""Correction fixtures grant test-only acceptance; they do not approve production records."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import zipfile
import pytest
from openpyxl.workbook.defined_name import DefinedName
sys.path.insert(0, str(Path(__file__).resolve().parent))
import approved_s1_excel as layout
import build_s1_candidate as builder

FILES = ["02-proverka-i-kontrol-otveta.xlsx", "08-raschet-procentov-395.xlsx"]

@pytest.fixture
def accepted_fixture(tmp_path, monkeypatch):
    directory = tmp_path / "test-only-corrections"
    shutil.copytree(layout.CORRECTIONS, directory)
    report = directory / "TEST_ONLY_NOT_LEGAL_ACCEPTANCE.md"
    report.write_text("Test fixture only. No legal or owner approval.\n")
    records = json.loads((directory / "corrections.json").read_text())
    for record in records.values():
        record.update(independent_review="ACCEPT", review_report=str(report), review_report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
    (directory / "corrections.json").write_text(json.dumps(records))
    monkeypatch.setattr(layout, "CORRECTIONS", directory)
    return directory, records

def workbook_for(filename, tmp_path):
    captured = {}
    original = layout.write_approved_layout
    try:
        layout.write_approved_layout = lambda workbook, output: captured.update(workbook=workbook)
        {FILES[0]: builder.f02, FILES[1]: builder.f08}[filename](tmp_path)
    finally:
        layout.write_approved_layout = original
    return captured["workbook"]

@pytest.mark.parametrize("filename", FILES)
def test_pending_blocks_before_output(filename, tmp_path, accepted_fixture):
    directory, records = accepted_fixture
    records[filename]["independent_review"] = "PENDING"
    (directory / "corrections.json").write_text(json.dumps(records))
    output = tmp_path / filename
    output.write_bytes(b"previous")
    with pytest.raises(ValueError, match="review pending"):
        layout.write_approved_layout(None, output)
    assert output.read_bytes() == b"previous"
    assert not list(tmp_path.glob("*.tmp"))

@pytest.mark.parametrize("filename", FILES)
def test_test_only_accepted_overlay_has_exact_bytes(filename, tmp_path, accepted_fixture):
    directory, records = accepted_fixture
    output = tmp_path / filename
    layout.write_approved_layout(workbook_for(filename, tmp_path), output)
    assert output.read_bytes() == (directory / filename).read_bytes()
    owner = (layout.TEMPLATES / filename).read_bytes()
    assert hashlib.sha256(owner).hexdigest() == layout.APPROVED[filename] == records[filename]["owner_sha256"]

@pytest.mark.parametrize("attack,match", [("formula","semantic mismatch"),("old_text","semantic mismatch"),("dv","validation mismatch"),("global_name","defined-name mismatch"),("sheet_name","defined-name mismatch")])
def test_generator_divergences_block(attack, match, tmp_path, accepted_fixture):
    filename = FILES[0]
    workbook = workbook_for(filename, tmp_path)
    if attack == "formula": workbook["Карта рисков"]["E5"] = "=1"
    elif attack == "old_text": workbook["Карта рисков"]["F19"] = accepted_fixture[1][filename]["old_text"]
    elif attack == "dv": workbook["Карта рисков"].data_validations.dataValidation[0].formula1 = '"wrong"'
    elif attack == "global_name": workbook.defined_names.add(DefinedName("Injected", attr_text="1"))
    else: workbook["Карта рисков"].defined_names.add(DefinedName("Injected", attr_text="1"))
    output = tmp_path / filename
    output.write_bytes(b"previous")
    with pytest.raises(ValueError, match=match): layout.write_approved_layout(workbook, output)
    assert output.read_bytes() == b"previous"
    assert not list(tmp_path.glob("*.tmp"))

@pytest.mark.parametrize("attack,match", [("hash","artifact hash mismatch"),("report","review-report hash mismatch"),("owner","owner lineage mismatch"),("owner_approval","owner lineage mismatch"),("other_part","unexpected ZIP part"),("second_text","shared-string scope mismatch"),("wrong_target","target mismatch")])
def test_lineage_and_overlay_scope_fail_closed(attack, match, tmp_path, accepted_fixture):
    directory, records = accepted_fixture
    filename = FILES[0]
    record = records[filename]
    if attack == "hash": record["correction_sha256"] = "0"*64
    elif attack == "report": record["review_report_sha256"] = "0"*64
    elif attack == "owner": record["owner_sha256"] = "0"*64
    elif attack == "owner_approval": record["owner_approval_of_new_text"] = True
    elif attack == "wrong_target": record["cell"] = "F18"
    else:
        source = (directory / filename).read_bytes()
        buffer = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(source)) as old, zipfile.ZipFile(buffer,"w") as new:
            for info in old.infolist():
                data = old.read(info.filename)
                if info.filename == ("docProps/core.xml" if attack == "other_part" else "xl/sharedStrings.xml"):
                    data = data.replace(b"</", b" <!--unexpected--> </", 1)
                new.writestr(info, data)
        changed = buffer.getvalue()
        (directory / filename).write_bytes(changed)
        record["correction_sha256"] = hashlib.sha256(changed).hexdigest()
    (directory / "corrections.json").write_text(json.dumps(records))
    output = tmp_path / filename
    output.write_bytes(b"previous")
    with pytest.raises(ValueError, match=match): layout.write_approved_layout(None, output)
    assert output.read_bytes() == b"previous"
    assert not list(tmp_path.glob("*.tmp"))

@pytest.mark.parametrize("failure", ["write", "replace"])
def test_atomic_failures_preserve_output_and_clean_temp(failure, tmp_path, accepted_fixture, monkeypatch):
    filename = FILES[0]
    workbook = workbook_for(filename, tmp_path)
    output = tmp_path / filename
    output.write_bytes(b"previous")
    original_write, original_replace = Path.write_bytes, Path.replace
    def write(path, data):
        if path.name.endswith(".approved.tmp") and failure == "write":
            original_write(path,b"partial")
            raise OSError("injected write failure")
        return original_write(path,data)
    def replace(path, target):
        if path.name.endswith(".approved.tmp") and failure == "replace": raise OSError("injected replace failure")
        return original_replace(path,target)
    monkeypatch.setattr(Path,"write_bytes",write)
    monkeypatch.setattr(Path,"replace",replace)
    with pytest.raises(OSError, match="injected"): layout.write_approved_layout(workbook, output)
    assert output.read_bytes() == b"previous"
    assert not list(tmp_path.glob("*.tmp"))
