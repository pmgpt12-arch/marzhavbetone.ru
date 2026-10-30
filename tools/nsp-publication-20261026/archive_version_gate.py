#!/usr/bin/env python3
"""NSP ARCHIVE_VERSION_GATE: read-only QA source verification, no release.
This gate never activates a buyer route or infers permission from QA_PASS.
"""
import argparse, hashlib, io, json, pathlib, subprocess, zipfile
from datetime import datetime, timezone
from p8_edition_binding import check_p8_edition

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git_bytes(reference, path):
    cmd = ["git", "-C", str(ROOT), "show", reference + ":" + path]
    response = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=50)
    if response.returncode:
        raise RuntimeError(response.stderr.decode("utf-8", "replace")[:180])
    return response.stdout

def source_manifest_sha(entry, name, manifest):
    if entry["SKU"] == "P8":
        matching = [x for x in manifest.get("paid", []) if x.get("sku") == "P8"]
        if len(matching) != 1: raise ValueError("P8_ACCEPTANCE_MANIFEST_MISSING")
        item = matching[0]
        return {v["name"]: v["sha256"] for v in item["members"]}.get(name)
    if entry["SKU"] == "FREE/checklist":
        return manifest.get("candidate_pdf_sha256")
    entries = manifest.get("entries", manifest.get("files", []))
    found = [v for v in entries if v.get("name") == name]
    if len(found) != 1: return None
    obj = found[0]
    return (obj.get("final_sha256") or obj.get("candidate_sha256") or
            obj.get("qa_sha256") or obj.get("sha256"))

def verify(entry):
    sku = entry["SKU"]
    out = {"SKU":sku, "status":"BLOCKED", "accepted_sha256":entry["accepted_archive_sha256"],
           "source_sha256":None, "member_shas":[], "origin":entry.get("qa_branch"),
           "qa_commit":entry.get("qa_commit"), "release_permission":"HOLD",
           "staging_delivery_sha256":None, "failures":[]}
    if entry.get("release_permission") != "HOLD":
        out["failures"].append("UNEXPECTED_RELEASE_PERMISSION")
    if not entry.get("qa_branch") or not entry.get("qa_commit"):
        out["failures"].append("EVIDENCE_MISSING_GIT_ORIGIN")
        return out
    ref = "origin/" + entry["qa_branch"]
    try:
        head = subprocess.run(["git","-C",str(ROOT),"rev-parse",ref],
                               capture_output=True,text=True,timeout=10)
        if head.returncode != 0 or head.stdout.strip() != entry["qa_commit"]:
            out["failures"].append("ACCEPTED_QA_COMMIT_NOT_AT_REMOTE_REF")
            return out
        prefix = entry["member_manifest"].rsplit("/",1)[0] + "/"
        source_path = entry["archive_source_name"]
        if not source_path.startswith("tools/"):
            source_path = prefix + source_path
        data = git_bytes(ref, source_path)
        out["source_sha256"] = sha(data)
        if out["source_sha256"] != entry["accepted_archive_sha256"]:
            out["failures"].append("ARCHIVE_SHA256_MISMATCH")
            return out
        man = json.loads(git_bytes(ref,entry["member_manifest"]))
        if entry["SKU"] == "FREE/checklist":
            members = [(source_path.split("/")[-1], data)]
        else:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if z.testzip() is not None: raise ValueError("ZIP_CRC_FAIL")
                members = [(n,z.read(n)) for n in z.namelist() if not n.endswith("/")]
        out["member_shas"] = [{"filename":n,"sha256":sha(b)} for n,b in members]
        if len(members) != entry["file_count"]:
            out["failures"].append("ARCHIVE_MEMBER_COUNT_MISMATCH")
        for name,raw in members:
            if source_manifest_sha(entry,name,man) != sha(raw):
                out["failures"].append("MEMBER_SHA_MISMATCH:"+name)
        # P8 technical CRC / own QA01 SHA is not the independent owner-approved edition.
        # Compare the complete candidate to the OWNER decision + accepted edition ID
        # + outer ZIP SHA + each MEMBER SHA, pinned to the original Git commit.
        if not out["failures"] and sku == "P8":
            out["technical_source_verified"] = True
            out["candidate_edition_id"] = "P8-QA01-20261023-READY_CANDIDATE"
            edition = check_p8_edition(data, out["candidate_edition_id"])
            out["accepted_edition_validation"] = edition
            if edition["status"] != "HISTORICAL_EDITION_ACCEPTED_HOLD":
                out["status"] = "SOURCE_VERIFIED_EDITION_BLOCKED"
                out["failures"].append(edition["status"])
            else:
                out["status"] = "SOURCE_VERIFIED_HISTORICAL_EDITION_HOLD"
        # SOURCE_VERIFIED does not confer a separate owner release permission.
        elif not out["failures"]:
            out["status"] = "SOURCE_VERIFIED_HOLD"
    except (RuntimeError,ValueError,KeyError,zipfile.BadZipFile,subprocess.TimeoutExpired) as e:
        out["failures"].append(type(e).__name__+":"+str(e)[:180])
    return out


def verify_p2_owner_edition(entry):
    """Read-only P2 owner/source binding. Success is not a deployment receipt."""
    expected = {'SKU': 'P2', 'edition_id': 'P2-v13', 'qa_commit': '46005303b5b0f4ca27d9742d23cb9456669034e5', 'approval_commit': '29a73bea7783c52924a3b85c4dfbeb563e3e550d', 'archive_source_name': 'tools/nsp-qa14-20261024/owner-review-v13-20261029/P2-NSP-v13-13-files-20261029.zip', 'member_manifest': 'tools/nsp-qa14-20261024/owner-review-v13-20261029/REVIEW_MANIFEST.json', 'approval_path': 'tools/nsp-qa14-20261024/owner-review-v13-20261029/OWNER_PUBLICATION_APPROVAL_20261029.json', 'accepted_archive_sha256': '42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da', 'member_manifest_sha256': '0b21feede98c5833cce447ac47c4e648cb51d8178199c2fe16ff6316bded3a96', 'approval_sha256': 'd251bdcc240bc6f25668de250be9e3c9a44c33e767e979d4de4a6bab68a89a95', 'file_count': 13, 'release_permission': 'ALLOW_EXACT_EDITION_ONLY'}
    out = {"SKU": "P2", "status": "BLOCKED", "failures": [],
           "owner_acceptance": "UNVERIFIED", "release_permission": "HOLD",
           "deployment_status": "NOT_DEPLOYED", "production_delivery_verified": False}
    try:
        if any(entry.get(k) != v for k,v in expected.items()):
            raise ValueError("P2_ACCEPTED_BINDING_MISMATCH")
        owner_raw = git_bytes(expected["approval_commit"], expected["approval_path"])
        manifest_raw = git_bytes(expected["qa_commit"], expected["member_manifest"])
        data = git_bytes(expected["qa_commit"], expected["archive_source_name"])
        if sha(owner_raw) != expected["approval_sha256"]:
            raise ValueError("P2_OWNER_EVIDENCE_SHA_MISMATCH")
        if sha(manifest_raw) != expected["member_manifest_sha256"]:
            raise ValueError("P2_MEMBER_MANIFEST_SHA_MISMATCH")
        if sha(data) != expected["accepted_archive_sha256"] or len(data) != 438989:
            raise ValueError("P2_ARCHIVE_SHA_OR_SIZE_MISMATCH")
        owner = json.loads(owner_raw); manifest = json.loads(manifest_raw)
        if (owner.get("sku") != "p2" or owner.get("edition_id") != "P2-v13"
                or owner.get("owner_product_acceptance") != "APPROVED"
                or owner.get("release_permission") != expected["release_permission"]
                or owner.get("archive_sha256") != sha(data)):
            raise ValueError("P2_OWNER_PERMISSION_MISMATCH")
        members = manifest.get("members", [])
        if len(members) != 13 or len({v["name"] for v in members}) != 13:
            raise ValueError("P2_MEMBER_MANIFEST_INVALID")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            if len(names) != 13 or len(set(names)) != 13 or z.testzip() is not None:
                raise ValueError("P2_ARCHIVE_STRUCTURE_INVALID")
            if set(names) != {v["name"] for v in members}:
                raise ValueError("P2_MEMBER_SET_MISMATCH")
            for v in members:
                b = z.read(v["name"])
                if len(b) != v["bytes"] or sha(b) != v["sha256"]:
                    raise ValueError("P2_MEMBER_SHA_MISMATCH:" + v["name"])
        out.update(status="SOURCE_VERIFIED_OWNER_APPROVED_NOT_DEPLOYED",
                   owner_acceptance="APPROVED", release_permission=expected["release_permission"],
                   source_sha256=sha(data), member_shas=members, file_count=13,
                   source_commit=expected["qa_commit"], approval_commit=expected["approval_commit"])
    except (RuntimeError,ValueError,KeyError,TypeError,OSError,zipfile.BadZipFile,subprocess.TimeoutExpired) as e:
        out["failures"].append(type(e).__name__+":"+str(e)[:180])
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",default=str(HERE/"ARCHIVE_VERSION_GATE_RECEIPT.json"))
    parser.add_argument("--require-edition-accepted",action="store_true",
                        help="strict nonzero exit when P8 edition is not the pinned owner-accepted whole ZIP")
    parser.add_argument("--p2-approved", action="store_true",
                        help="Only verify pinned owner-approved P2; no production action")
    args=parser.parse_args()
    if args.p2_approved:
        entry=json.loads((HERE/"p2-v13-20261029/materials/P2_RELEASE_BINDING.json").read_text())
        result=verify_p2_owner_edition(entry)
        # Never overwrite the unrelated default all-product receipt.
        output=HERE/"p2-v13-20261029/P2_SOURCE_APPROVAL_RECEIPT.json"
        pathlib.Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result["status"] == "SOURCE_VERIFIED_OWNER_APPROVED_NOT_DEPLOYED" else 2
    matrix=json.loads((HERE/"NSP_ACCEPTED_ARTIFACTS_MATRIX.json").read_text())
    rows = [verify(r) for r in matrix["rows"]]
    p8 = next(r for r in rows if r["SKU"] == "P8")
    source_technical_verified = sum(r["status"] in (
        "SOURCE_VERIFIED_HOLD", "SOURCE_VERIFIED_EDITION_BLOCKED",
        "SOURCE_VERIFIED_HISTORICAL_EDITION_HOLD") for r in rows)
    result = {"schema":"NSP_ARCHIVE_VERSION_GATE_V2_ACCEPTED_EDITION",
              "created_utc":datetime.now(timezone.utc).isoformat(),
              "total":len(rows),
              "source_verified":source_technical_verified,
              "technical_source_verified":source_technical_verified,
              "p8_edition_status":p8.get("accepted_edition_validation",{}).get("status","UNKNOWN"),
              "edition_not_accepted":sum(r["status"]=="SOURCE_VERIFIED_EDITION_BLOCKED" for r in rows),
              "release_allowed":0,
              "status":"BLOCKED_P8_EDITION_NOT_ACCEPTED_RELEASE_HOLD",
              "rows":rows}
    pathlib.Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("ARCHIVE_VERSION_GATE",result["source_verified"],"/",result["total"],
          "source verified; release_allowed=0; status="+result["status"])
    # Default mode is a nonrelease evidence collection, where HOLD is expected.
    # Strict mode is for readiness decisions: reject a *correctly hashed* QA01
    # with a nonzero exit instead of silently treating SOURCE_SHA_PASS as approval.
    if args.require_edition_accepted and result["p8_edition_status"] != "HISTORICAL_EDITION_ACCEPTED_HOLD":
        print("EDITION_NOT_ACCEPTED: P8 QA01 candidate SHA_PASS is not the pinned accepted whole owner edition")
        return 2
    # Even a historic accepted R3 SHA does not remove today's release HOLD.
    return 0

if __name__=="__main__":
    raise SystemExit(main())
