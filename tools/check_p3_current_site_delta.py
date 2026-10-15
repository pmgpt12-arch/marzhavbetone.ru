#!/usr/bin/env python3
"""Separate current P3 route delta gate; keeps immutable 2026-10-12 snapshots intact."""
import hashlib, json, subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(["git","-C",str(root),*args],timeout=15)
def sha(path):
    return hashlib.sha256((root/path).read_bytes()).hexdigest()
expected={
 "download.php":"public_endpoint",
 "products-config.php":"non_route_module",
 "products/p3-shablony-ks2-ks3.html":"indexable_page",
 "tools/test_delivery_one_hour.php":"test_fixture"
}
base="03ce64f607c43bd6a1443ad2d1088c07697c22ba"
changed=set(git("diff","--name-only",base,"HEAD","--","*.php","*.html").decode().splitlines())
assert changed==set(expected),f"unexpected HTML/PHP delta: {sorted(changed^set(expected))}"
report=json.loads((root/"tools/reports/site-route-discovery-20261012/report.json").read_text())
classes={e["source_path"]:e["route_class"] for e in report["entries"]}
assert all(classes.get(p)==kind for p,kind in expected.items() if not p.startswith("tools/"))
from build_artifact_registry import registry_identity_sha256
baseline=json.loads(git("show",f"{base}:products-storage/ARTIFACT-REGISTRY.json"))
current=json.loads((root/"products-storage/ARTIFACT-REGISTRY.json").read_text())
assert registry_identity_sha256(baseline)!=registry_identity_sha256(current),"expected approved P3 tree delta missing"
roots={s["runtime_sku"]:s for s in current["product_sources"]}
assert roots["p3"]["git_tree_sha"]==git("rev-parse","HEAD:products-storage/05-ks-bez-vozvrata").decode().strip()
nom=json.loads((root/"tools/candidates/p3-owner-approval-nomination-20261015/nomination.json").read_text())
assert len(nom["member_artifacts"])==11
for x in nom["member_artifacts"]:
    assert sha("products-storage/05-ks-bez-vozvrata/"+x["member"])==x["sha256"],x["member"]
r={"verdict":"PASS_CURRENT_P3_SITE_DELTA_ONLY","head":git("rev-parse","HEAD").decode().strip(),
"historical_snapshot_preserved":True,"changed_php_html":{p:{"class":expected[p],"sha256":sha(p)} for p in sorted(expected)},
"candidate_11_of_11":True,"current_registry_p3_tree":roots["p3"]["git_tree_sha"],
"g4":"OPEN","g8":"HOLD","scope":"Current route/classification/content source delta, not historical snapshot renewal or release"}
print(json.dumps(r,ensure_ascii=False,indent=2))
