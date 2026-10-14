#!/usr/bin/env python3
"""Independent-reproducible gate for the current P11/T6 gold nomination record."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "tools/candidates/portfolio-owner-pdf-20261013/p11-t6-consolidated-gold-20261014/p11-t6-gold-formal-nomination-route-20261014.json"
MANIFEST = ROOT / "tools/candidates/portfolio-owner-pdf-20261013/p11-t6-consolidated-gold-20261014/candidate-manifest.json"
VERIFIER = ROOT / "tools/candidates/portfolio-owner-pdf-20261013/p11-t6-consolidated-gold-20261014/verify_candidate.py"
PRIOR = ROOT / "tools/candidates/portfolio-owner-pdf-20261013/19-kvartiry-vmesto-deneg/p11-t6-post-purchase-letter-formal-nomination-route-20261014.json"
LETTER = ROOT / "tools/candidates/portfolio-owner-pdf-20261013/19-kvartiry-vmesto-deneg/00-PISMO-POSLE-POKUPKI.txt"
HEAD = "65d51da1dea3fcdc60f857d066f6c1123e683976"
ARCHIVE_SHA = "f365039ef568dbbe9c661a6e1f553d21ddd0b086c9172f1e5a4340fb7dfe7f70"
PRE_GOLD_SHA = "6a07f3c81152a22c3f2a8f127862e8a4e1ea6cafd0f750095d1933a5c095f572"
LETTER_SHA = "c8f9d78cf2335f2acf52ab8d12258e4e3e799c9c87e3447edcc17c7f0f507ea5"
MANIFEST_SHA = "1bd932de3fbea4537a1ab7d4f1ad1d8a20d0472148fb7ad8a2f6fee412dc86e0"
PRIOR_SHA = "4bbc436d010a1a29f6720717448469c2f78b3667f89d11fca97f829dc09086f6"
EXPECTED_NAMES = [
    "00-START-HERE.txt",
    "50-slovar-poley-raschet-metrami.docx",
    "51-algoritm-raschet-metrami.pdf",
    "52-chek-list-raschet-metrami.docx",
    "53-zapros-status-obekta.docx",
    "54-zapros-sostoyanie-escrow.docx",
    "55-pamyatka-punkt-ustupki-escrow.pdf",
    "56-pervyy-den-do-podpisi.docx",
]
EXPECTED_MEMBER_IDENTITIES = {
    "00-START-HERE.txt": ("2f895a2f2b8ea5e166c8f18dd416465f2651b3562068551fc9f26841fd5dcf3a", "f83e4f7e7e364d5a66ddf85ded7817b80ef98611"),
    "50-slovar-poley-raschet-metrami.docx": ("c5de8ebe3b7518042b081894ef0205635f688e3b7160986a0415135e711b601a", "557536220f3d990d597e66934fce614ae64682ea"),
    "51-algoritm-raschet-metrami.pdf": ("2a4c98dc4a1b131dbccb787276f487a17a76a0c6643932c0ee0ca666601135d7", "2e417285fe0e48dc04a4f8ad83832d32791766ba"),
    "52-chek-list-raschet-metrami.docx": ("149ff5b2fcb1cfa214a0dfee64f0d6a003bfe3bbbafc60977030a67535b15b33", "afe0741d062c510774a56ae8193eeabb0f9211a9"),
    "53-zapros-status-obekta.docx": ("4746cd1086be16d55b636ad651370f032956bfda0dfe3f8b83f2f34487774a7a", "dbd80d7b4bd7cbe5b60b00757d5f3c9b526260df"),
    "54-zapros-sostoyanie-escrow.docx": ("bf32807bf9d1ec955cf151f3e5dd055fde47ebd85ce322b0376e0c873f52a319", "c42ae07d257a3a6a6dd5f0fc40f81f489bd6cb9a"),
    "55-pamyatka-punkt-ustupki-escrow.pdf": ("20f65a850db70836b2897dc747ed6478781641e3a4f5a537b094a7afec0814a2", "47c35f6555d1b5cc339c6b2326e8fbb60e0f8505"),
    "56-pervyy-den-do-podpisi.docx": ("9c40a96498037b53a68ecea6f3ee57129a9f2c236d1073d1818c603016260807", "14e0ab75f15109686f9360980541b0b5208af13c"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def record_contract(data: dict) -> None:
    require(data["source_head"] == HEAD, "source head")
    require(data["scope"] == "FORMAL_NOMINATION_CURRENT_GOLD_ARCHIVE_AND_ROUTE_ONLY", "scope")
    current = data["current_gold_selection"]
    require(current["archive_sha256"] == ARCHIVE_SHA, "current archive")
    require(current["archive_git_blob"] == "65efefebe600029bb8c239df0268dca976bff369", "archive blob")
    require(current["archive_bytes"] == 592882, "archive bytes")
    require(current["manifest_sha256"] == MANIFEST_SHA, "manifest SHA")
    require([item["name"] for item in current["members"]] == EXPECTED_NAMES, "ordered members")
    require(len({item["name"] for item in current["members"]}) == 8, "unique members")
    require(
        {item["name"]: (item["sha256"], item["git_blob"]) for item in current["members"]}
        == EXPECTED_MEMBER_IDENTITIES,
        "member identities",
    )
    require(current["archive_review"]["independent_verdict"] == "PASS_CANDIDATE_ARCHIVE_COMPOSITION_SCOPE_ONLY", "review")
    require(data["superseded_pre_gold_selection"]["archive_sha256"] == PRE_GOLD_SHA, "pre-gold anchor")
    require(data["superseded_pre_gold_selection"]["status"] == "SUPERSEDED_FOR_CURRENT_GOLD_SELECTION_ONLY_NOT_DELETED", "pre-gold status")
    require(data["prior_route_record"]["sha256"] == PRIOR_SHA, "prior record")
    require(data["separate_letter"]["sha256"] == LETTER_SHA, "letter SHA")
    require(data["separate_letter"]["in_buyer_archive"] is False, "letter membership")
    require(data["separate_letter"]["second_text_allowed"] is False, "second letter")
    route = data["delivery_route"]
    require(route["compatible_product"] == "CONSOLIDATED_P11_T6_CURRENT_GOLD_CANDIDATE_ONLY", "product route")
    require(route["legacy_standalone_t6_allowed"] is False, "legacy T6")
    require(route["letter_in_buyer_zip"] is False, "letter route")
    require(route["implementation_status"] == "NOT_VERIFIED", "implementation escalation")
    require(route["live_configuration_changed"] is False, "live escalation")
    require(route["delivery_execution_authorized"] is False, "execution escalation")
    require(data["open_gates"]["canonical_replacement"] == "NOT_AUTHORIZED", "canonical escalation")
    require(data["open_gates"]["full_product_acceptance"] == "NOT_GRANTED", "product escalation")
    require(data["open_gates"]["G1_G8"] == "0/13", "G1-G8 escalation")
    require(data["release"] == "HOLD" and data["prohibitions"]["release"] == "HOLD", "release escalation")


def run_current_archive_gate(record: dict) -> dict:
    manifest = json.loads(MANIFEST.read_text())
    require(sha(MANIFEST.read_bytes()) == MANIFEST_SHA, "manifest bytes")
    require(blob(MANIFEST.read_bytes()) == record["current_gold_selection"]["manifest_git_blob"], "manifest blob")
    require(sha(PRIOR.read_bytes()) == PRIOR_SHA, "prior record bytes")
    require(blob(PRIOR.read_bytes()) == record["prior_route_record"]["git_blob"], "prior record blob")
    require(sha(LETTER.read_bytes()) == LETTER_SHA, "letter bytes")
    require(blob(LETTER.read_bytes()) == record["separate_letter"]["git_blob"], "letter blob")
    spec = importlib.util.spec_from_file_location("gold_verify", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    source = manifest["source_commit"]
    archive_path = record["current_gold_selection"]["archive_path"]

    def read(path: str) -> bytes:
        if path == archive_path:
            return (ROOT / path).read_bytes()
        return subprocess.check_output(["git", "-C", str(ROOT), "show", source + ":" + path], timeout=10)

    actual_tree = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", source + "^{tree}"], timeout=10
    ).decode().strip()
    return module.verify(manifest, read, actual_tree)


def negative_checks(record: dict) -> dict[str, bool]:
    tests = {}

    def reject(name: str, mutant: dict) -> None:
        try:
            record_contract(mutant)
        except ValueError:
            tests[name] = True
        else:
            raise ValueError("undetected nomination mutation: " + name)

    old = copy.deepcopy(record)
    old["current_gold_selection"]["archive_sha256"] = PRE_GOLD_SHA
    reject("stale_pre_gold_archive", old)
    member = copy.deepcopy(record)
    member["current_gold_selection"]["members"][1]["sha256"] = "0" * 64
    reject("member_identity", member)
    standalone = copy.deepcopy(record)
    standalone["delivery_route"]["legacy_standalone_t6_allowed"] = True
    reject("legacy_standalone_t6", standalone)
    inside = copy.deepcopy(record)
    inside["separate_letter"]["in_buyer_archive"] = True
    reject("letter_in_archive", inside)
    implemented = copy.deepcopy(record)
    implemented["delivery_route"]["implementation_status"] = "VERIFIED"
    reject("implementation_escalation", implemented)
    canonical = copy.deepcopy(record)
    canonical["open_gates"]["canonical_replacement"] = "AUTHORIZED"
    reject("canonical_escalation", canonical)
    release = copy.deepcopy(record)
    release["release"] = "PASS"
    reject("release_escalation", release)
    require(len(tests) == 7 and all(tests.values()), "negative coverage")
    return tests


def main() -> None:
    record = json.loads(RECORD.read_text())
    record_contract(record)
    archive_result = run_current_archive_gate(record)
    mutations = negative_checks(record)
    print(json.dumps({
        "status": "PASS_CURRENT_GOLD_FORMAL_NOMINATION_ROUTE_ONLY",
        "archive_status": archive_result["status"],
        "members": 8,
        "letter_outside_archive": True,
        "negative_mutations_detected": mutations,
        "runtime_implementation": "NOT_VERIFIED",
        "canonical_replacement": "NOT_AUTHORIZED",
        "release": "HOLD",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
