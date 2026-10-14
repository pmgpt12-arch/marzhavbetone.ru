#!/usr/bin/env python3
"""Deterministic checks for the P11/T6 letter nomination and route policy."""
import argparse
import copy
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

RECORD = (
    "tools/candidates/portfolio-owner-pdf-20261013/"
    "19-kvartiry-vmesto-deneg/"
    "p11-t6-post-purchase-letter-formal-nomination-route-20261014.json"
)


def git(root: Path, *args: str, binary: bool = False):
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if process.returncode:
        raise AssertionError(process.stderr.decode("utf-8", "replace"))
    return process.stdout if binary else process.stdout.decode("utf-8").strip()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def expect_assertion(callable_):
    try:
        callable_()
    except AssertionError:
        return True
    raise AssertionError("negative mutation was not detected")


def validate_contract(data: dict) -> None:
    assert data["schema_version"] == 1
    assert data["record_status"] == "CANDIDATE_FOR_INDEPENDENT_REVIEW"
    assert data["scope"] == "FORMAL_NOMINATION_AND_DELIVERY_ROUTE_POLICY_ONLY"
    assert data["product"]["target_code"] == "P11"
    assert data["formal_letter_nomination"]["second_text_allowed"] is False
    route = data["delivery_route"]
    assert route["trigger_contract"] == "AFTER_SUCCESSFUL_PURCHASE_ONLY"
    assert route["channel_contract"] == (
        "SEPARATE_POST_PURCHASE_MESSAGE_OUTSIDE_BUYER_ZIP"
    )
    assert route["compatible_product"] == (
        "CONSOLIDATED_P11_T6_EIGHT_FILE_CANDIDATE_ONLY"
    )
    assert route["legacy_standalone_t6_allowed"] is False
    assert route["letter_in_buyer_zip"] is False
    assert route["implementation_status"] == "NOT_VERIFIED"
    assert route["live_configuration_changed"] is False
    assert route["delivery_execution_authorized"] is False
    assert route["message_sent"] is False
    assert data["open_gates"]["G1_G8"] == "0/13"
    assert data["open_gates"]["controlled_delivery_implementation"].startswith(
        "OPEN_"
    )
    assert data["prohibitions"] == {
        "source_replacement": False,
        "live_sku_price_payment_change": False,
        "live_delivery_change": False,
        "deploy_or_publication": False,
        "release": "HOLD",
    }
    assert data["model_calls"] == 0
    assert data["paid_api_calls"] == 0
    assert data["release"] == "HOLD"


def validate_inputs(root: Path, data: dict) -> dict:
    source = data["source_head"]
    letter = data["formal_letter_nomination"]
    letter_raw = git(root, "show", f"{source}:{letter['path']}", binary=True)
    assert len(letter_raw) == letter["bytes"]
    assert digest(letter_raw) == letter["sha256"]
    assert git(root, "rev-parse", f"{source}:{letter['path']}") == letter["git_blob"]

    prior = data["prior_nomination"]
    prior_raw = git(root, "show", f"{source}:{prior['path']}", binary=True)
    assert digest(prior_raw) == prior["sha256"]
    assert git(root, "rev-parse", f"{source}:{prior['path']}") == prior["git_blob"]
    prior_data = json.loads(prior_raw)

    archive = data["buyer_archive"]
    archive_raw = git(root, "show", f"{source}:{archive['path']}", binary=True)
    assert len(archive_raw) == archive["bytes"]
    assert digest(archive_raw) == archive["sha256"]
    assert git(root, "rev-parse", f"{source}:{archive['path']}") == archive["git_blob"]

    prior_set = prior_data["nominated_buyer_set"]
    prior_archive = prior_set["archive"]
    prior_names = [item["name"] for item in prior_set["files"]]
    assert archive["sha256"] == prior_archive["sha256"]
    assert archive["git_blob"] == prior_archive["git_blob"]
    assert archive["members"] == prior_names
    assert archive["member_count"] == prior_archive["root_members"] == 8

    with zipfile.ZipFile(io.BytesIO(archive_raw), "r") as bundle:
        names = bundle.namelist()
        assert bundle.testzip() is None
        assert names == archive["members"]
        assert len(names) == len(set(names)) == archive["member_count"]
        assert Path(letter["path"]).name not in names
        for item in prior_set["files"]:
            member_raw = bundle.read(item["name"])
            source_path = f"{prior_set['directory']}/{item['name']}"
            assert member_raw == git(
                root, "show", f"{source}:{source_path}", binary=True
            )
            assert digest(member_raw) == item["sha256"]

    assert archive["letter_is_member"] is False
    assert archive["archive_rebuilt_for_letter"] is False
    return {
        "letter_bytes": len(letter_raw),
        "archive_members": len(archive["members"]),
        "archive_crc": "PASS",
        "archive_members_equal_git_objects": len(archive["members"]),
    }


def validate(root: Path, data: dict) -> dict:
    validate_contract(data)
    return validate_inputs(root, data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--record", default=RECORD)
    args = parser.parse_args()
    root = args.root.resolve()
    data = json.loads((root / args.record).read_text(encoding="utf-8"))

    result = validate(root, data)

    bad_letter = copy.deepcopy(data)
    bad_letter["formal_letter_nomination"]["sha256"] = "0" * 64
    bad_members = copy.deepcopy(data)
    bad_members["buyer_archive"]["members"] = bad_members["buyer_archive"]["members"][:-1]
    bad_zip_route = copy.deepcopy(data)
    bad_zip_route["delivery_route"]["letter_in_buyer_zip"] = True
    bad_legacy_route = copy.deepcopy(data)
    bad_legacy_route["delivery_route"]["legacy_standalone_t6_allowed"] = True

    mutations = {
        "altered_letter_hash": expect_assertion(
            lambda: validate(root, bad_letter)
        ),
        "altered_archive_member_set": expect_assertion(
            lambda: validate(root, bad_members)
        ),
        "letter_in_zip_route": expect_assertion(
            lambda: validate(root, bad_zip_route)
        ),
        "legacy_standalone_t6_route": expect_assertion(
            lambda: validate(root, bad_legacy_route)
        ),
    }
    print(
        json.dumps(
            {
                "status": "PASS",
                "record": args.record,
                "source_head": data["source_head"],
                **result,
                "negative_mutations": mutations,
                "controlled_delivery_implementation": "OPEN",
                "release": "HOLD",
                "G1_G8": "0/13",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
