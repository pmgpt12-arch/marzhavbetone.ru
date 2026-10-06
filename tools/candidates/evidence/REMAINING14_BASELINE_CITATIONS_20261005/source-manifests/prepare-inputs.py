from pathlib import Path
import json,hashlib,subprocess,collections,shutil,datetime
ROOT=Path("/home/denis/.local/state/claude-dispatcher/recovery-20261005");R=ROOT/"catalog-baseline-citations-20261005";R.mkdir(exist_ok=True);assert not (R/"READY.json").exists()
REPO=Path("/home/denis/projects/marzhavbetone.ru");PIN="264d75a06d59de82602dc1bcef347913c44cc648"
h=lambda b:hashlib.sha256(b).hexdigest()
def save(n,d):(R/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
def git(*a):return subprocess.check_output(["git",*a],cwd=REPO,timeout=15)
parent=ROOT/"catalog-next-queue-20261005-recovery/module-input-hashes.json";ext=ROOT/"catalog-structural-extension-20261005/input-hashes.json"
assert h(parent.read_bytes())=="7ef66ed269183a671269c033d80b4c85f06eff53a452b4e4cd3a3a15b8b4e08e"
assert h(ext.read_bytes())=="7771bc15bfae652585622a9b166f3f125b3afbf24964a2aa1f398287f109197e"
D=json.loads(parent.read_text());X=json.loads(ext.read_text());assert D["source_sha"]==X["source_sha"]==PIN
assert h(git("show",PIN+":products-config.php"))==D["config_sha256"]
skus=["p4","p7","p8","p9","p10","p11","p12","p13","t1","t2","t3","t4","t5","t6"];mods=[m for m in D["modules"] if m["sku"] in skus];assert sorted(m["sku"] for m in mods)==sorted(skus)
bindings=[dict(f,sku=m["sku"]) for m in mods for f in m["members"]];assert len(bindings)==135
bykey={(f["sku"],f["path"]):f for f in bindings}
for m in X["modules"]:
 assert m["sku"] in skus
 for f in m["members"]:
  accepted=bykey[m["sku"],f["path"]];assert all(accepted[k]==f[k] for k in ["sha256","git_blob","size","source_sha"])
tree={l.split("\t",1)[1]:l.split()[2] for l in git("ls-tree","-r",PIN,"products-storage").decode().splitlines()}
unique={};verified=[]
for f in bindings:
 assert tree[f["path"]]==f["git_blob"]
 raw=git("show",PIN+":"+f["path"]);assert h(raw)==f["sha256"] and len(raw)==f["size"]
 suffix=Path(f["path"]).suffix;target=R/"unique-inputs"/(f["sha256"]+suffix);target.parent.mkdir(exist_ok=True)
 if f["sha256"] not in unique:target.write_bytes(raw);unique[f["sha256"]]={"sha256":f["sha256"],"suffix":suffix,"local_path":str(target),"size":len(raw),"bindings":[]}
 assert unique[f["sha256"]]["suffix"]==suffix;unique[f["sha256"]]["bindings"].append({"sku":f["sku"],"path":f["path"]});verified.append(dict(f,local_path=str(target)))
types=dict(collections.Counter(Path(f["path"]).suffix for f in bindings));assert types=={".txt":14,".docx":95,".xlsx":18,".pdf":8}
deps={}
for name,pin in [("Normative_Contract","cc7daf5d6515035576adb4854ce4523a4cd9b4b2ab95cebef63c4104d1fb99bb"),("Task_Setting_Protocol","337fe8864579a95dd4af53e44ad036016145a4be82aac5560e535a09fa56e686")]:
 p=Path("/home/denis/projects/ai-business-os/docs")/(name+".md");raw=p.read_bytes();assert h(raw)==pin;(R/(name+".md")).write_bytes(raw);deps[name]={"path":str(p),"sha256":h(raw),"bytes":len(raw)}
grammar=Path("/home/denis/.local/state/claude-dispatcher/recovery-20261004/p2-current-citation-inventory-20261005-recovery/extract.py");s=grammar.read_text();assert h(grammar.read_bytes())=="b1ca49a5940ce6d1c3fb47af60036f9baf45585b47d1d6b766f040db38dc0f47"
fragment=s[s.index("codes=r"):s.index("def add(")];compile(fragment,"lexical-grammar.py","exec");(R/"lexical-grammar.py").write_text(fragment)
save("input-hashes.json",{"source_sha":PIN,"source_status":"CACHED_CONFIGURED_BASELINE_NOT_ACCEPTED_DELIVERY","parent_manifest":{"path":str(parent),"sha256":h(parent.read_bytes())},"extension_manifest":{"path":str(ext),"sha256":h(ext.read_bytes())},"config_sha256":D["config_sha256"],"modules":mods,"bindings":verified,"unique_inputs":list(unique.values()),"types":types,"canonical_dependencies":deps})
save("passport.json",{"execution_pattern":"iterative","primary_result":"REMAINING14_cached_baseline_literal_source_index_for_future_lawyer","feedback_loop_required":True,"checkpoint_policy":"verified_only","source_sha":PIN,"source_status":"CACHED_CONFIGURED_BASELINE_NOT_ACCEPTED_CURRENT_REPACKAGING","skus":skus,"input_bindings":135,"unique_SHA256_inputs":125,"workers":4,"overall_subprocess_deadline_seconds":120,"scope":"native textual citation facts only; DOCX paragraphs/header/footer/footnotes/endnotes/comments/core titlefields; native XLSX storedformula/cache/cells/headerfooter/comments/validation/titlefields; uniquePDFtext-layer page/char/physical lines/image-limit flags; TXTphysical lines","acceptance":["135 fullSHA/Gitblob source bindings verified before and after","Exactly14module maps retaining separate modulepath bindings for sameSHA","Every article/standard/code/№/generic marker exactquote/span/native locator; no registryIDs","Identical fullSHA native text reused once only when type and native locator context same","Each uniquePDF pdftotext once; rawpages/metadata/limits retained","Root and independent broad source coverage acceptance before Git mutation"],"negative_cases":["Lists/ranges not expanded into normative IDs","Ambiguous fullcode/numeric names retained unresolved","Genericmarkers not defects; zeroarticlehits notlegalcomplete","PDF/images/layout/noOCR scope limits","Cachedmain acceptance/currentness unknown"],"prohibited":["Source/product changes","ZIP/PHP/Calc/formula/layout/generaltest/LLM/currentofficiallookup","Legal judgment/semantic guidance","Commit until root+independent accepted"],"grammar_reference":{"source_path":str(grammar),"sha256":h(grammar.read_bytes()),"fragment_sha256":h(fragment.encode()),"prior_module_review_scaffolding":"NOT_COPIED"}})
save("schema.json",{"schema_version":1,"input_binding":["sku","source_sha","path","git_blob","sha256"],"text_unit":["native_unit_index","location","text","content_sha256"],"module_occurrence":["occurrence_id","sku","document","file_sha256","unit_id","location","span","literal","short_quote","quote_span","code","code_binding","articles_as_written","ranges_or_variants","registry_norm_id:null","normative_verdict:NOT_VERIFIED"],"module_marker":["marker_id","same_exact_input_and_native_locator","raw_marker","classification","span","short_quote","quote_span","registry_norm_id:null"],"dedup_scope":"Unique input fullSHA/nativecontext reuse only; citations have independent perSKU/path IDs; module groups are lexical forms not norms","baseline_boundary":"Configured source eligibility inferred by priorinventory policy; NOactual PHPZIP/currentacceptedbuyer/currentness/legal/render/CalcPASS"})
save("preflight-receipt.json",{"status":"VERIFIED135_BASELINE_SOURCE_BINDINGS","source_sha":PIN,"modules":14,"bindings":135,"unique_inputs":125,"types":types,"dedup_reuses":10,"extension_parent_bindings_verified":sum(len(m["members"]) for m in X["modules"]),"source_writes":0,"at":datetime.datetime.now(datetime.timezone.utc).isoformat()})
print("PREFLIGHTPASS",14,135,125,types,"PASSPORT",R,flush=True)
