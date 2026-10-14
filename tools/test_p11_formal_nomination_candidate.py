#!/usr/bin/env python3
import argparse, hashlib, json, subprocess
from pathlib import Path

def git(root, *args, binary=False):
    p=subprocess.run(["git",*args],cwd=root,capture_output=True,timeout=30)
    if p.returncode:
        raise AssertionError(p.stderr.decode("utf-8","replace"))
    return p.stdout if binary else p.stdout.decode().strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ns=ap.parse_args()
    root=Path(ns.root).resolve()
    rel="tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami/p11-formal-nomination-candidate-20261014.json"
    data=json.loads((root/rel).read_text(encoding="utf-8"))
    assert data["record_status"]=="CANDIDATE_FOR_INDEPENDENT_REVIEW"
    assert data["product"]["target_code"]=="P11"
    assert data["product"]["target_price_rub"]==24900
    assert data["prohibitions"]=={
      "source_replacement":False,
      "live_sku_price_payment_change":False,
      "deploy_or_publication":False,
      "release":"HOLD",
      "merge_authorization":False
    }
    files=data["nominated_buyer_set"]["files"]
    assert len(files)==7 and len({x["name"] for x in files})==7
    source=data["nominated_buyer_set"]["source_commit"]
    directory=data["nominated_buyer_set"]["directory"]
    checked=[]
    for item in files:
        path=f"{directory}/{item['name']}"
        raw=git(root,"show",f"{source}:{path}",binary=True)
        assert len(raw)==item["bytes"], path
        assert hashlib.sha256(raw).hexdigest()==item["sha256"], path
        assert git(root,"rev-parse",f"{source}:{path}")==item["git_blob"], path
        checked.append(path)
    lin=data["lineage"]
    registry_raw=git(root,"show",f"{lin['registry_commit']}:{lin['registry_path']}",binary=True)
    assert hashlib.sha256(registry_raw).hexdigest()==lin["registry_sha256"]
    assert git(root,"rev-parse",f"{lin['registry_commit']}:{lin['registry_path']}")==lin["registry_blob"]
    registry=json.loads(registry_raw)
    expected={(x["target_sku"],x["runtime_sku"],x["relative_root"],x["git_tree_sha"],x["file_count"],x["bytes"],x["role"],x["release_status"]) for x in lin["sources"]}
    actual={(x["target_sku"],x["runtime_sku"],x["relative_root"],x["git_tree_sha"],x["file_count"],x["bytes"],x["role"],x["release_status"]) for x in registry["product_sources"] if x["target_sku"]=="P11"}
    assert expected==actual
    gates=data["open_gates"]
    assert gates["F02"].startswith("OPEN_")
    assert gates["F03"].startswith("OPEN_")
    assert gates["F04"].startswith("OPEN_")
    assert gates["F05"].startswith("OPEN_")
    assert gates["post_purchase_letter_runtime_t6"].startswith("BLOCKED_")
    assert gates["G1_G8"]=="0/13"
    print(json.dumps({"status":"PASS","record":rel,"files_checked":len(checked),"lineage_entries_checked":len(expected),"release":"HOLD"},ensure_ascii=False))

if __name__=="__main__":
    main()
