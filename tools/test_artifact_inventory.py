#!/usr/bin/env python3
import copy
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "artifact_inventory", Path(__file__).with_name("build_artifact_inventory.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
REGISTRY = json.loads((ROOT / "products-storage/ARTIFACT-REGISTRY.json").read_text(encoding="utf-8"))
BASE = json.loads((ROOT / "products-storage/ARTIFACT-INVENTORY.json").read_text(encoding="utf-8"))


class ArtifactInventoryTests(unittest.TestCase):
    def test_seed_shape_is_valid(self):
        MODULE.validate_inventory(copy.deepcopy(BASE), REGISTRY)
        MODULE.validate_registry_reference(REGISTRY, BASE, MODULE.serialized(BASE))

    def test_missing_file_fails(self):
        data = copy.deepcopy(BASE)
        data["files"].pop()
        with self.assertRaises(MODULE.InventoryError):
            MODULE.validate_inventory(data, REGISTRY)

    def test_extra_file_fails(self):
        data = copy.deepcopy(BASE)
        row = copy.deepcopy(data["files"][-1])
        row["relative_path"] += ".extra"
        row["registry_id"] += "-EXTRA"
        data["files"].append(row)
        with self.assertRaises(MODULE.InventoryError):
            MODULE.validate_inventory(data, REGISTRY)

    def test_duplicate_id_fails(self):
        data = copy.deepcopy(BASE)
        data["files"][1]["registry_id"] = data["files"][0]["registry_id"]
        with self.assertRaises(MODULE.InventoryError):
            MODULE.validate_inventory(data, REGISTRY)

    def test_duplicate_path_fails(self):
        data = copy.deepcopy(BASE)
        data["files"][1]["relative_path"] = data["files"][0]["relative_path"]
        with self.assertRaises(MODULE.InventoryError):
            MODULE.validate_inventory(data, REGISTRY)

    def test_root_escape_fails(self):
        data = copy.deepcopy(BASE)
        data["files"][0]["relative_path"] = "archive/old.docx"
        with self.assertRaises(MODULE.InventoryError):
            MODULE.validate_inventory(data, REGISTRY)

    def test_report_path_fails(self):
        data = copy.deepcopy(BASE)
        data["files"][0]["relative_path"] = "tools/reports/candidate.docx"
        with self.assertRaises(MODULE.InventoryError):
            MODULE.validate_inventory(data, REGISTRY)

    def test_unknown_role_fails(self):
        data = copy.deepcopy(BASE)
        data["files"][0]["role"] = "release_ready"
        with self.assertRaises(MODULE.InventoryError):
            MODULE.validate_inventory(data, REGISTRY)

    def test_hash_blob_and_bytes_drift_fail(self):
        expected = copy.deepcopy(BASE)
        for field, value in (
            ("sha256", "0" * 64),
            ("git_blob", "0" * 40),
            ("bytes", BASE["files"][0]["bytes"] + 1),
        ):
            data = copy.deepcopy(BASE)
            data["files"][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises(MODULE.InventoryError):
                    MODULE.ensure_matches(data, expected)

    def test_generation_is_byte_identical(self):
        self.assertEqual(MODULE.serialized(BASE), MODULE.serialized(copy.deepcopy(BASE)))

    def test_checkout_matches_inventory(self):
        try:
            subprocess.check_call(
                ["git", "-C", str(ROOT), "rev-parse", "--git-dir"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            self.skipTest("not running in a git checkout")
        expected = MODULE.build_inventory(REGISTRY, ROOT, BASE["source_commit"])
        MODULE.validate_inventory(expected, REGISTRY)
        MODULE.ensure_matches(BASE, expected)


if __name__ == "__main__":
    unittest.main()
