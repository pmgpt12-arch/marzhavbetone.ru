#!/usr/bin/env python3
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("artifact_registry", Path(__file__).with_name("build_artifact_registry.py"))
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
BASE = json.loads((ROOT / "products-storage/ARTIFACT-REGISTRY.json").read_text(encoding="utf-8"))


class RegistryShapeTests(unittest.TestCase):
    def test_seed_is_valid(self):
        MODULE.validate_shape(copy.deepcopy(BASE))

    def test_duplicate_registry_id_fails(self):
        data = copy.deepcopy(BASE)
        data["artifacts"].append(copy.deepcopy(data["artifacts"][0]))
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_missing_target_fails(self):
        data = copy.deepcopy(BASE)
        data["product_sources"] = [row for row in data["product_sources"] if row.get("target_sku") != "T3"]
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_report_cannot_be_canonical(self):
        data = copy.deepcopy(BASE)
        data["artifacts"][2]["role"] = "canonical_master"
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_non_nominated_report_is_blocked(self):
        data = copy.deepcopy(BASE)
        data["artifacts"][2]["release_status"] = "OPEN"
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_unknown_role_fails(self):
        data = copy.deepcopy(BASE)
        data["artifacts"][0]["role"] = "accepted_somewhere_else"
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)


if __name__ == "__main__":
    unittest.main()
