import pathlib,subprocess,json,hashlib,zipfile,re,datetime
R=pathlib.Path("/home/denis/.local/state/claude-dispatcher/recovery-20261004/next-packaging-qa-20261005/p2");R.mkdir(exist_ok=True);S="/home/denis/projects/marzhavbetone.ru"
E={"observed":datetime.datetime.now(datetime.timezone.utc).isoformat(),"commands":[],"status":"BLOCKED","execution_pattern":"one_shot","primary_result":"P2_CURRENT_PHP_ZIP_PAYLOAD","feedback_loop_required":False,"checkpoint_policy":"verified_only"}
def cmd(args,t=15):
 p=subprocess.run(args,capture_output=True,text=True,timeout=t);row={"argv":args,"exit":p.returncode,"stdout":p.stdout,"stderr":p.stderr};E["commands"].append(row);assert not p.returncode,row;return p.stdout
def sha(b):return hashlib.sha256(b).hexdigest()
try:
 head=json.loads(cmd(["gh","api","repos/pmgpt12-arch/marzhavbetone.ru/pulls/312"]))["head"]["sha"]
 pinned=cmd(["git","-C",S,"rev-parse","refs/task-inputs/p2p3-20261005/pr312"]).strip();assert head==pinned and len(head)==40,(head,pinned)
 E["source_sha"]=head;assert cmd(["git","-C",S,"cat-file","-t",head]).strip()=="commit"
 def get(path):return subprocess.check_output(["git","-C",S,"show",head+":"+path],timeout=5)
 config=get("products-config.php");(R/"products-config.php").write_bytes(config)
 directory=re.search(rb"'p2'\s*=>\s*\[.*?'dir'\s*=>\s*'([^']+)'",config,re.S).group(1).decode();assert directory=="02-dopraboty-bez-poter";E["catalog_dir"]=directory
 files=cmd(["git","-C",S,"ls-tree","-r","--name-only",head,"products-storage/"+directory]).splitlines()
 E["source_files"]={}
 for path in files:
  raw=get(path);dst=R/path;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
  E["source_files"][path]={"sha256":sha(raw),"blob":cmd(["git","-C",S,"rev-parse",head+":"+path]).strip()}
 service={".htaccess","MANIFEST.md","00-PISMO-POSLE-POKUPKI.txt"}
 expected={path.split(directory+"/",1)[1]:v["sha256"] for path,v in E["source_files"].items() if pathlib.Path(path).name not in service}
 old=json.loads(pathlib.Path("/home/denis/.local/state/claude-dispatcher/recovery-20261004/buyer-p2-p3-20261005/378/coordinator-actual-php/receipt.json").read_text())
 E["prior_receipt_source"]=old["exact_candidate"];E["prior_receipt_equivalent"]=old["member_hashes"]==expected;assert not E["prior_receipt_equivalent"],"duplicate: reuse previous exact payload"
 (R/"orders/delivery").mkdir(parents=True,exist_ok=True)
 (R/"build.php").write_text("<?php\ndefine('ORDERS_DIR',__DIR__.'/orders');define('PRODUCTS_DIR',__DIR__.'/products-storage');define('DELIVERY_DIR',__DIR__.'/orders/delivery');require __DIR__.'/products-config.php';if(!class_exists('ZipArchive')){exit(10);} $path=mvb_build_product_zip('p2');if(!$path){exit(11);}echo $path;")
 arc=pathlib.Path(cmd(["php",str(R/"build.php")],30).strip());assert arc.is_relative_to(R);E["archive"]=str(arc);E["archive_sha256"]=sha(arc.read_bytes())
 with zipfile.ZipFile(arc) as z:
  E["crc_failure_member"]=z.testzip();E["member_hashes"]={n:sha(z.read(n)) for n in z.namelist()};assert E["crc_failure_member"] is None and E["member_hashes"]==expected
 assert expected["00-INSTRUKCIYA.docx"]=="bc2c155984286409f429349fdab25d343dbc4aaae4b9aa32e91a3e4debc335c4"
 assert expected["00-INSTRUKCIYA.pdf"]=="b7af857d6674754f242e1b3400ffe51d212f39dbe979bdf6e80f6663989e44ce"
 E["source_immutable"]=all(get(p)==(R/p).read_bytes() for p in files);assert E["source_immutable"]
 E["count"]=len(expected);E["status"]="PASS_CURRENT_ACTUAL_PHP_ZIP"
except Exception as err:E["error"]=repr(err)
E["boundary"]="packaging only; no source/main/live/sku/payment/form/email/model changes; legal Word Excel release unchanged"
(R/"receipt.json").write_text(json.dumps(E,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:E.get(k) for k in ["status","source_sha","archive_sha256","count","prior_receipt_equivalent","source_immutable","error"]}))
