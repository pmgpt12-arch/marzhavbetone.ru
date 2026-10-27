#!/usr/bin/env python3
"""NSP ARCHIVE_VERSION_GATE: read-only QA source verification, no release.
This gate never activates a buyer route or infers permission from QA_PASS.
"""
import argparse, hashlib, io, json, pathlib, subprocess, zipfile
from datetime import datetime, timezone

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
        # Status is SOURCE_VERIFIED only. Release requires separately authorized
        # owner approval and actual staging GET; no editable PASS can override this.
        if not out["failures"]:out["status"]="SOURCE_VERIFIED_HOLD"
    except (RuntimeError,ValueError,KeyError,zipfile.BadZipFile,subprocess.TimeoutExpired) as e:
        out["failures"].append(type(e).__name__+":"+str(e)[:180])
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",default=str(HERE/"ARCHIVE_VERSION_GATE_RECEIPT.json"))
    args=parser.parse_args()
    matrix=json.loads((HERE/"NSP_ACCEPTED_ARTIFACTS_MATRIX.json").read_text())
    rows = [verify(r) for r in matrix["rows"]]
    result = {"schema":"NSP_ARCHIVE_VERSION_GATE_V1",
              "created_utc":datetime.now(timezone.utc).isoformat(),
              "total":len(rows),
              "source_verified":sum(r["status"]=="SOURCE_VERIFIED_HOLD" for r in rows),
              "release_allowed":0,
              "status":"BLOCKED_PENDING_OWNER_RELEASE_AND_STAGING_GET",
              "rows":rows}
    pathlib.Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("ARCHIVE_VERSION_GATE",result["source_verified"],"/",result["total"],
          "source verified; release_allowed=0; status="+result["status"])
    # A missing Git receipt is a documented BLOCKED, not a false PASS.
    return 0

if __name__=="__main__":
    raise SystemExit(main())
