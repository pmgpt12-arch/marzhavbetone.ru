#!/usr/bin/env python3
import argparse
import copy
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

RECORD = (
    "tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami/"
    "p11-formal-nomination-candidate-v2-20261014.json"
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


def validate_files(root: Path, data: dict) -> int:
    nominated = data["nominated_buyer_set"]
    source = nominated["source_commit"]
    directory = nominated["directory"]
    files = nominated["files"]
    assert len(files) == 8
    assert len({item["name"] for item in files}) == 8

    raw_by_name = {}
    for item in files:
        path = f"{directory}/{item['name']}"
        raw = git(root, "show", f"{source}:{path}", binary=True)
        assert len(raw) == item["bytes"], path
        assert digest(raw) == item["sha256"], path
        assert git(root, "rev-parse", f"{source}:{path}") == item["git_blob"], path
        raw_by_name[item["name"]] = raw

    archive = nominated["archive"]
    archive_raw = git(root, "show", f"{source}:{archive['path']}", binary=True)
    assert len(archive_raw) == archive["bytes"]
    assert digest(archive_raw) == archive["sha256"]
    assert git(root, "rev-parse", f"{source}:{archive['path']}") == archive["git_blob"]

    with zipfile.ZipFile(io.BytesIO(archive_raw), "r") as bundle:
        names = bundle.namelist()
        assert len(names) == archive["root_members"] == 8
        assert len(set(names)) == 8
        assert names == [item["name"] for item in files]
        assert bundle.testzip() is None
        for name, expected in raw_by_name.items():
            assert bundle.read(name) == expected, name
    return len(files)


def validate_lineage(root: Path, data: dict) -> int:
    lineage = data["lineage"]
    raw = git(
        root,
        "show",
        f"{lineage['registry_commit']}:{lineage['registry_path']}",
        binary=True,
    )
    assert digest(raw) == lineage["registry_sha256"]
    assert (
        git(
            root,
            "rev-parse",
            f"{lineage['registry_commit']}:{lineage['registry_path']}",
        )
        == lineage["registry_blob"]
    )
    registry = json.loads(raw)
    expected = {
        (
            row["target_sku"],
            row["runtime_sku"],
            row["relative_root"],
            row["git_tree_sha"],
            row["file_count"],
            row["bytes"],
            row["role"],
            row["release_status"],
        )
        for row in lineage["sources"]
    }
    actual = {
        (
            row["target_sku"],
            row["runtime_sku"],
            row["relative_root"],
            row["git_tree_sha"],
            row["file_count"],
            row["bytes"],
            row["role"],
            row["release_status"],
        )
        for row in registry["product_sources"]
        if row["target_sku"] == "P11"
    }
    assert len(expected) == 2
    assert expected == actual
    return len(expected)


def validate_contract(data: dict) -> None:
    assert data["schema_version"] == 2
    assert data["record_status"] == "CANDIDATE_FOR_INDEPENDENT_REVIEW"
    assert data["product"]["target_code"] == "P11"
    assert data["supersedes"]["pull_request"] == 620
    assert data["supersedes"]["reuse_prohibited"] is True
    assert data["open_gates"]["F05"].startswith("OPEN_")
    assert data["open_gates"]["post_purchase_letter_runtime_t6"].startswith("BLOCKED_")
    assert data["open_gates"]["G1_G8"] == "0/13"
    assert data["prohibitions"] == {
        "source_replacement": False,
        "live_sku_price_payment_change": False,
        "deploy_or_publication": False,
        "release": "HOLD",
        "merge_authorization": False,
    }
    assert data["release"] == "HOLD"
    assert data["model_calls"] == 0
    assert data["no_paid_api"] is True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--record", default=RECORD)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    data = json.loads((root / args.record).read_text(encoding="utf-8"))

    validate_contract(data)
    files_checked = validate_files(root, data)
    lineage_checked = validate_lineage(root, data)

    bad_file = copy.deepcopy(data)
    bad_file["nominated_buyer_set"]["files"][0]["sha256"] = "0" * 64
    file_mutation_detected = expect_assertion(lambda: validate_files(root, bad_file))

    bad_lineage = copy.deepcopy(data)
    bad_lineage["lineage"]["sources"][0]["git_tree_sha"] = "0" * 40
    lineage_mutation_detected = expect_assertion(
        lambda: validate_lineage(root, bad_lineage)
    )

    print(
        json.dumps(
            {
                "status": "PASS",
                "record": args.record,
                "source_commit": data["nominated_buyer_set"]["source_commit"],
                "files_checked": files_checked,
                "archive_crc": "PASS",
                "archive_members_equal_git_objects": files_checked,
                "lineage_entries_checked": lineage_checked,
                "negative_mutations": {
                    "altered_file_hash": file_mutation_detected,
                    "altered_lineage": lineage_mutation_detected,
                },
                "release": "HOLD",
                "G1_G8": "0/13",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
