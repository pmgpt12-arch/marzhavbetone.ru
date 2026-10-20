#!/usr/bin/env python3
"""Validate or refresh the MB001 artifact registry from an exact git checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

EXPECTED_TARGETS = {"P1", "P2", "P3", "P4", "P5+P12", "P7", "P8", "P9", "P10", "P11", "P13", "T2", "T3"}
ALLOWED_ROLES = {"canonical_master", "nominated_candidate", "historical_mirror", "report_evidence_not_nominated"}


class RegistryError(ValueError):
    pass


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def root_facts(repo: Path, commit: str, rel: str) -> dict[str, object]:
    tree_sha = git(repo, "rev-parse", f"{commit}:{rel}")
    output = git(repo, "ls-tree", "-r", "--long", commit, "--", rel)
    rows = [line for line in output.splitlines() if line]
    sizes = []
    for row in rows:
        left, _path = row.split("\t", 1)
        size = left.split()[3]
        sizes.append(int(size) if size != "-" else 0)
    return {"git_tree_sha": tree_sha, "file_count": len(rows), "bytes": sum(sizes)}


def validate_shape(data: dict) -> None:
    if data.get("schema_version") != 1:
        raise RegistryError("unsupported schema_version")
    inventory = data.get("file_inventory", {})
    if set(inventory) != {"path", "source_commit", "sha256", "files", "bytes"}:
        raise RegistryError("missing or invalid file_inventory reference")
    if inventory.get("path") != "products-storage/ARTIFACT-INVENTORY.json":
        raise RegistryError("invalid file_inventory path")
    if not isinstance(inventory.get("sha256"), str) or len(inventory["sha256"]) != 64:
        raise RegistryError("invalid file_inventory sha256")
    if inventory.get("files") != 218 or inventory.get("bytes") != 5_097_868:
        raise RegistryError("file_inventory totals drift")
    validate_change_history(data)
    roles = set(data.get("allowed_roles", []))
    if roles != ALLOWED_ROLES:
        raise RegistryError("allowed_roles drift")
    targets = {row.get("target_sku") for row in data.get("product_sources", []) if row.get("target_sku")}
    if targets != EXPECTED_TARGETS:
        raise RegistryError(f"target coverage mismatch: {sorted(targets ^ EXPECTED_TARGETS)}")
    runtime = [row.get("runtime_sku") for row in data.get("product_sources", [])]
    if len(runtime) != 19:
        raise RegistryError(f"runtime root count mismatch: {len(runtime)} != 19")
    if len(runtime) != len(set(runtime)):
        raise RegistryError("duplicate runtime_sku")
    ids = [row.get("registry_id") for row in data.get("artifacts", [])]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise RegistryError("missing or duplicate registry_id")
    coverage = data.get("coverage", {})
    expected_coverage = {
        "target_skus": {"registered": len(targets), "expected": len(EXPECTED_TARGETS)},
        "runtime_roots": {"registered": len(runtime), "expected": 19},
        "root_files": {"registered": sum(int(row.get("file_count", 0)) for row in data.get("product_sources", []))},
        "file_sha256_records": {
            "registered": data["file_inventory"]["files"],
            "expected": data["file_inventory"]["files"],
            "percent": 100.0,
        },
        "nomination_artifact_records": {"registered": len(ids)},
    }
    for key, value in expected_coverage.items():
        if coverage.get(key) != value:
            raise RegistryError(f"coverage drift {key}: {coverage.get(key)} != {value}")
    for row in [*data.get("product_sources", []), *data.get("artifacts", [])]:
        if row.get("role") not in ALLOWED_ROLES:
            raise RegistryError(f"invalid role: {row.get('role')}")
    for artifact in data.get("artifacts", []):
        rel = artifact.get("relative_path", "")
        role = artifact.get("role")
        if role == "canonical_master" and not rel.startswith("products-storage/"):
            raise RegistryError(f"canonical artifact outside products-storage: {rel}")
        if rel.startswith("tools/reports/") and role not in {"nominated_candidate", "report_evidence_not_nominated"}:
            raise RegistryError(f"report artifact has executable role: {rel}")
        if role == "report_evidence_not_nominated":
            if artifact.get("release_status") != "BLOCKED" or artifact.get("content_status") != "NOT_NOMINATED":
                raise RegistryError(f"non-nominated report must fail closed: {rel}")


def reconcile(data: dict, repo: Path, check: bool) -> bool:
    changed = False
    checkout_ref = "HEAD"
    for source in data["product_sources"]:
        actual = root_facts(repo, checkout_ref, source["relative_root"])
        for key, value in actual.items():
            if source.get(key) != value:
                if check:
                    raise RegistryError(f"source drift {source['runtime_sku']} {key}: {source.get(key)} != {value}")
                source[key] = value
                changed = True
    for artifact in data["artifacts"]:
        verify_ref = checkout_ref if artifact["role"] == "canonical_master" else artifact["commit"]
        object_spec = f"{verify_ref}:{artifact['relative_path']}"
        try:
            blob = git(repo, "rev-parse", object_spec)
            payload = subprocess.check_output(["git", "-C", str(repo), "show", object_spec])
        except subprocess.CalledProcessError as exc:
            raise RegistryError(f"missing git object: {object_spec}") from exc
        actual = {
            "git_blob": blob,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        for key, value in actual.items():
            if artifact.get(key) != value:
                if check:
                    raise RegistryError(f"artifact drift {artifact['registry_id']} {key}: {artifact.get(key)} != {value}")
                artifact[key] = value
                changed = True
    expected_count = sum(int(row.get("file_count", 0)) for row in data["product_sources"])
    if data['coverage']['root_files'] != {'registered': expected_count}:
        if check:
            raise RegistryError('coverage drift root_files')
        data['coverage']['root_files'] = {'registered': expected_count}
        changed = True
    verify_history_files(data, repo)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="products-storage/ARTIFACT-REGISTRY.json")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--reuse-request", help="JSON current-input/contract/environment request; no job launch")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    registry = (repo / args.registry).resolve()
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
        repaired_coverage = False
        if not args.check:
            expected = {'registered': sum(int(row.get('file_count', 0)) for row in data['product_sources'])}
            repaired_coverage = data['coverage']['root_files'] != expected
            data['coverage']['root_files'] = expected
        validate_shape(data)
        changed = reconcile(data, repo, args.check) or repaired_coverage
        validate_shape(data)
        if args.reuse_request:
            request = json.loads(Path(args.reuse_request).read_text(encoding="utf-8"))
            print(json.dumps(plan_checkpoint_reuse(data, request, repo), ensure_ascii=False))
            return 0
        if changed:
            registry.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, RegistryError) as exc:
        print(f"ARTIFACT_REGISTRY_FAIL: {exc}", file=sys.stderr)
        return 1
    print("ARTIFACT_REGISTRY_PASS")
    return 0


# Additive extension for the existing tools/build_artifact_registry.py.
# It validates provenance and plans reuse; it never submits Office/model jobs.
def stable_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()



def registry_identity_sha256(data):
    """All accepted registry fields except the separately validated change_history log."""
    if not isinstance(data, dict):
        raise RegistryError("registry identity must be an object")
    return stable_digest({k: v for k, v in data.items() if k != "change_history"})


def change_record_digest(record):
    return stable_digest({k: v for k, v in record.items() if k != "record_sha256"})


def gate_fingerprint(record, gate):
    return stable_digest({
        "subject_sha256": record["output"]["sha256"],
        "gate_id": gate["gate_id"],
        "scope": gate["scope"],
        "contract_sha256": gate["contract_sha256"],
        "environment_fingerprint": gate["environment_fingerprint"],
        "dependency_fingerprint": gate["dependency_fingerprint"],
    })


def require_history(ok, message):
    if not ok:
        raise RegistryError("change_history: " + message)


def is_sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_change_history(data):
    history = data.get("change_history")
    if history is None:
        return  # Backward-compatible seed; no invented historical acceptance.
    require_history(history.get("schema_version") == 1, "unsupported schema")
    records = history.get("records")
    require_history(isinstance(records, list), "records must be a list")
    require_history(history.get("record_count") == len(records), "record count drift")
    require_history(history.get("append_only") is True, "history must be append-only")
    root_map = {(p["target_sku"], p["runtime_sku"]) for p in data["product_sources"]}
    previous = None
    ids, execution_keys = set(), set()
    for record in records:
        required = {"record_id", "registry_id", "parent_registry_id", "target_sku", "runtime_sku", "role", "recorded_at_utc", "origin", "input", "output", "delta", "execution", "evidence", "gates", "resume", "unknowns", "release_status", "previous_record_sha256", "record_sha256"}
        require_history(required <= set(record), "missing mandatory record section")
        rid = record["record_id"]
        require_history(isinstance(rid, str) and rid and rid not in ids, "duplicate/missing record ID")
        ids.add(rid)
        require_history((record["target_sku"], record["runtime_sku"]) in root_map, "unknown product binding")
        require_history(record["role"] in ALLOWED_ROLES, "unknown role")
        require_history(record["previous_record_sha256"] == previous, "history chain broken")
        require_history(record["record_sha256"] == change_record_digest(record), "record digest drift")
        previous = record["record_sha256"]
        require_history(record["release_status"] == "BLOCKED", "history cannot confer release approval")
        for slot in ("input", "output"):
            f = record[slot]
            require_history({"sha256", "bytes", "format", "actual_read_path", "archive_path", "git_blob_sha1", "snapshot"} <= set(f), "incomplete file identity")
            require_history(is_sha256(f["sha256"]), "invalid file hash")
            require_history(type(f["bytes"]) is int and f["bytes"] > 0, "invalid byte count")
            require_history(isinstance(f["git_blob_sha1"], str) and len(f["git_blob_sha1"]) == 40, "invalid git blob")
            p = Path(f["archive_path"])
            require_history(not p.is_absolute() and ".." not in p.parts and str(p).startswith("tools/candidates/registry-history-evidence/"), "archive path escape")
        evidence = record["evidence"]
        require_history(isinstance(evidence, list) and evidence, "missing evidence")
        ev_ids = [e["evidence_id"] for e in evidence]
        require_history(len(ev_ids) == len(set(ev_ids)), "duplicate evidence ID")
        for e in evidence:
            require_history({"sha256", "bytes", "archive_path", "actual_read_path", "kind"} <= set(e), "incomplete evidence identity")
            require_history(is_sha256(e["sha256"]) and type(e["bytes"]) is int and e["bytes"] > 0, "invalid evidence fingerprint")
            p = Path(e["archive_path"])
            require_history(not p.is_absolute() and ".." not in p.parts and str(p).startswith("tools/candidates/registry-history-evidence/"), "evidence path escape")
        gate_ids = set()
        for gate in record["gates"]:
            require_history(gate["gate_id"] not in gate_ids, "duplicate gate ID")
            gate_ids.add(gate["gate_id"])
            require_history(gate["status"] in {"PASS", "FAIL", "OPEN", "PENDING", "BLOCKED"}, "invalid gate status")
            require_history(gate["subject_sha256"] == record["output"]["sha256"], "gate refers to another version")
            require_history(gate["contract_sha256"] == stable_digest(gate["contract"]), "contract fingerprint drift")
            require_history(gate["environment_fingerprint"] == stable_digest(gate["environment"]), "environment fingerprint drift")
            require_history(gate["dependency_fingerprint"] == stable_digest(gate["dependencies"]), "dependency fingerprint drift")
            require_history(gate["fingerprint"] == gate_fingerprint(record, gate), "gate fingerprint drift")
            require_history(bool(gate["scope"]), "empty gate scope")
            require_history(set(gate["evidence_ids"]) <= set(ev_ids), "unknown gate evidence")
            if gate["status"] in {"PASS", "FAIL"}:
                require_history(bool(gate["evidence_ids"]), "terminal gate without evidence")
            if gate["status"] == "PASS":
                require_history(gate["accepted_scope_only"] is True, "unbounded PASS")
            job = gate.get("job_id")
            if job:
                key = (job, gate["fingerprint"])
                require_history(key not in execution_keys, "duplicate execution checkpoint")
                execution_keys.add(key)
        resume = record["resume"]
        require_history({"do_not_repeat_job_ids", "next_atomic_task", "invalidation_triggers", "open_findings", "g1_g8_status"} <= set(resume), "missing resume contract")
        require_history(resume["g1_g8_status"] != "PASS", "partial receipt promoted to product PASS")
    require_history(history.get("head_record_sha256") == previous, "history head drift")


def verify_history_files(data, repo):
    checked = set()
    for record in data.get("change_history", {}).get("records", []):
        for ref in [record["input"], record["output"], *record["evidence"]]:
            key = (ref["archive_path"], ref["sha256"], ref["bytes"])
            if key in checked:
                continue
            checked.add(key)
            p = (repo / ref["archive_path"]).resolve()
            require_history(repo.resolve() in p.parents and p.is_file(), "missing/escaped archive: " + ref["archive_path"])
            raw = p.read_bytes()
            require_history(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], "archived evidence/source drift: " + ref["archive_path"])
            if "git_blob_sha1" in ref:
                oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
                require_history(oid == ref["git_blob_sha1"], "archive git-blob drift")


    # A saved status cannot override the raw native report for the same SHA/job.
    for record in data.get("change_history", {}).get("records", []):
        for gate in record["gates"]:
            if gate["gate_id"] != "native_open_export" or gate["status"] not in {"PASS", "FAIL"}:
                continue
            import xml.etree.ElementTree as ET
            reports = [ET.fromstring((repo/e["archive_path"]).read_bytes()) for e in record["evidence"] if e["kind"] == "native-report"]
            reports = [r for r in reports if r.get("job") == gate["job_id"]]
            require_history(len(reports) == 1, "missing or ambiguous raw native report")
            require_history(reports[0].get("status") == gate["status"], "native verdict contradicts raw report")
            input_checks = [c for c in reports[0].findall("check") if c.get("name", "").endswith(":input_sha")]
            for c in input_checks:
                require_history(c.get("actual") == gate["subject_sha256"] and c.get("pass", "").lower() == "true", "native input SHA mismatch")


def append_change_record(data, record, expected_head):
    """Append once; exact duplicate is a no-op, a different duplicate is an error."""
    h = data.setdefault("change_history", {"schema_version": 1, "append_only": True, "record_count": 0, "head_record_sha256": None, "records": []})
    require_history(h["head_record_sha256"] == expected_head, "concurrent history update")
    for old in h["records"]:
        if old["record_id"] == record["record_id"]:
            require_history(old == record, "attempt to rewrite historical record")
            return False
    row = json.loads(json.dumps(record, ensure_ascii=False))
    row["previous_record_sha256"] = expected_head
    for gate in row["gates"]:
        gate["contract_sha256"] = stable_digest(gate["contract"])
        gate["environment_fingerprint"] = stable_digest(gate["environment"])
        gate["dependency_fingerprint"] = stable_digest(gate["dependencies"])
        gate["fingerprint"] = gate_fingerprint(row, gate)
    row["record_sha256"] = change_record_digest(row)
    h["records"].append(row)
    h["record_count"] = len(h["records"])
    h["head_record_sha256"] = row["record_sha256"]
    validate_change_history(data)
    return True


def plan_checkpoint_reuse(data, request, repo):
    """Return a bounded decision; no job submission, no inference, no Office call."""
    validate_change_history(data)
    verify_history_files(data, repo)
    records = data.get("change_history", {}).get("records", [])
    found = [r for r in records if r["record_id"] == request.get("record_id")]
    require_history(len(found) == 1, "unknown checkpoint")
    record = found[0]
    gates = [g for g in record["gates"] if g["gate_id"] == request.get("gate_id")]
    require_history(len(gates) == 1, "unknown gate")
    gate = gates[0]
    subject = Path(request["actual_input_path"])
    if not subject.is_absolute():
        subject = repo / subject
    require_history(subject.is_file(), "current input missing")
    observed = hashlib.sha256(subject.read_bytes()).hexdigest()
    changed = []
    if observed != gate["subject_sha256"]:
        changed.append("subject_sha256")
    for key in ("contract_sha256", "environment_fingerprint", "dependency_fingerprint"):
        require_history(is_sha256(request.get(key)), "current request missing " + key)
        if request[key] != gate[key]:
            changed.append(key)
    if changed:
        status = "DELTA_RECHECK_REQUIRED"
    else:
        status = {"PASS": "REUSE_VERIFIED_RESULT", "FAIL": "BLOCK_KNOWN_FAILURE", "PENDING": "WAIT_EXISTING_JOB", "BLOCKED": "RESOLVE_DEPENDENCY", "OPEN": "CHECK_REQUIRED"}[gate["status"]]
    return {"decision": status, "record_id": record["record_id"], "gate_id": gate["gate_id"], "actual_input_sha256": observed, "changed_dimensions": changed, "job_id": gate.get("job_id"), "do_not_launch_duplicate": status in {"REUSE_VERIFIED_RESULT", "BLOCK_KNOWN_FAILURE", "WAIT_EXISTING_JOB", "RESOLVE_DEPENDENCY"}, "accepted_scope": gate["scope"] if status == "REUSE_VERIFIED_RESULT" else None, "next_atomic_task": record["resume"]["next_atomic_task"], "g1_g8_status": record["resume"]["g1_g8_status"], "release_status": "BLOCKED"}


if __name__ == "__main__":
    raise SystemExit(main())
