"""Bind historical SKU/defect IDs to immutable source rows; stdlib only."""
import contextlib
import copy
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "tools" / "candidates"
SOURCE_SHA = "fdd643e1cbc94a0ed975f2280433df4769647a71"
SOURCE_PATH = "tools/candidates/MB001_PRODUCT_REPACKAGING_MATRIX.md"

class SourceRowBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        document = (CANDIDATES / "MB001_PYTHON_EXTRACT_VERIFICATION.md").read_text()
        match = re.search(r"```python\n(.*?)\n```", document, re.S)
        if match is None:
            raise AssertionError("Missing embedded validator")
        raw = subprocess.run(
            ["git", "-C", str(ROOT), "show", SOURCE_SHA + ":" + SOURCE_PATH],
            capture_output=True, check=True, timeout=10,
        ).stdout
        cls.scratch = tempfile.TemporaryDirectory(prefix="mb001-source-binding-")
        cls.addClassCleanup(cls.scratch.cleanup)
        folder = Path(cls.scratch.name)
        (folder / "source.md").write_bytes(raw)
        scope = {"__file__": str(folder / "reproduce.py"), "__name__": "__main__"}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(match[1], str(folder / "reproduce.py"), "exec"), scope)
        cls.validate = staticmethod(scope["validate"])
        cls.records = json.loads((CANDIDATES / "MB001_BASELINE_QUOTED_DEFECTS.json").read_text())
        cls.generated = scope["records"]
        cls.proof = json.loads((folder / "MB001_BASELINE_QUOTED_DEFECTS_PROOF.json").read_text())

    def reject(self, mutation, record=0):
        data = copy.deepcopy(self.records)
        mutation(data[record])
        with self.assertRaises(AssertionError):
            self.validate(data)

    def test_unchanged_output_and_positive_proof(self):
        self.assertEqual(self.generated, self.records)
        self.assertEqual(len(self.records), 10)
        self.assertEqual(self.proof["source_commit"], SOURCE_SHA)
        self.assertEqual(self.proof["source_blob"], "2a12297c9ffeba6ff5aed3c9f8f711b8d8ab7c39")
        self.assertEqual(self.proof["checks"]["positive"], "PASS")
        self.assertEqual(self.proof["checks"]["eligible_sku_swap"], "REJECTED/PASS")
        self.validate(self.records)

    def test_changed_quote(self):
        self.reject(lambda r: r.update(exact_quote=r["exact_quote"] + "x"))

    def test_missing_source_line(self):
        self.reject(lambda r: r.update(start_line=9999, end_line=9999))

    def test_wrong_sha(self):
        self.reject(lambda r: r.update(source_sha="0" * 40))

    def test_ineligible_sku(self):
        self.reject(lambda r: r.update(sku="P5"))

    def test_eligible_sku_swap_p2_to_p7(self):
        self.assertEqual(self.records[0]["sku"], "P2")
        self.reject(lambda r: r.update(sku="P7"))

    def test_historical_false(self):
        self.reject(lambda r: r.update(historical=False))

    def test_source_defect_id_cannot_be_removed(self):
        self.assertEqual(self.records[4]["defect_id"], "D-4")
        self.reject(lambda r: r.update(defect_id=None), record=4)

if __name__ == "__main__":
    unittest.main()
