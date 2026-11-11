#!/usr/bin/env python3
"""One-page guarded correction. Uses LIVE calculator as source, never stale GitHub HTML."""
import hashlib,io,json,os,pathlib,re,subprocess,sys,tarfile,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[2]
BEFORE="1fb2271e637aef494b082bddf8181a694f904cf42e8b11b8a81a68122a388b5f"
URL="https://nastoronepodryadchika.ru/kalkulyator.html"
OLD='<p class="calculator-note">Нужен только первый ход — <a href="/products/t1-pervyy-shag-pri-neoplate.html">«Первый шаг при неоплате»</a>. Проверить свои документы бесплатно — <a href="/materialy/dengi.html">семь проверок до обращения к юристу</a>.</p>'.encode()
NEW='<p class="calculator-note">Проверить документы перед требованием оплаты можно бесплатно: <a href="/materialy/dengi.html">семь проверок до обращения к юристу</a>. Полный комплект — <a href="/products/p1-oplata-po-ks2.html">«Получение оплаты за выполненные работы»</a>.</p>'.encode()
EVIDENCE=pathlib.Path("/tmp/nsp-calculator-evidence");EVIDENCE.mkdir(parents=True,exist_ok=True)
def sh(b):return hashlib.sha256(b).hexdigest()
def run(a,timeout=45):
 r=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if r.returncode:raise RuntimeError("COMMAND_FAILED "+str(r.returncode)+" "+r.stderr.decode(errors="replace")[-850:])
 return r.stdout.decode(errors="replace").strip()
def candidate():
 req=urllib.request.Request(URL,headers={"Accept-Encoding":"identity","Cache-Control":"no-cache","User-Agent":"NSP-single-page-release/1.0"})
 with urllib.request.urlopen(req,timeout=14) as response:
  assert response.status==200
  before=response.read(120000)
 assert sh(before)==BEFORE,"LIVE_PRECONDITION_DRIFT"
 assert before.count(OLD)==1,"EXACT_OLD_CTA_COUNT"
 after=before.replace(OLD,NEW)
 assert after.count(OLD)==0 and after.count(NEW)==1
 tx=ROOT/"tools/nsp-editorial/transaction.php"
 old_tx=(ROOT/"tools/nsp-final/transaction.php").read_text()
 expected=old_tx.replace("'p11'=>2490000,'p13'=>1790000,'t2'=>990000,'t3'=>1490000","'p11'=>2490000,'p13'=>1790000").replace("['t1','t4','t5','t6','p12']","['t1','t2','t3','t4','t5','t6','p12']").replace("// Bounded static-file transaction; all configuration, orders and masters are excluded.","// Bounded static-file transaction; all configuration, orders and masters are excluded.\n// EDITORIAL COPY: T2 and T3 were retired by owner; check as archived, not active.")
 # Exactly two legacy SKU rules and an explanatory comment are the only executor differences.
 assert tx.is_file() and tx.read_text()==expected,"TRANSACTION_UNRELATED_DRIFT"
 run(["php","-l",str(tx)])
 rows=[{"path":"kalkulyator.html","before":BEFORE,"after":sh(after)}]
 out=EVIDENCE/"calculator-candidate.tar"
 with tarfile.open(out,"w") as t:
  m=(json.dumps(rows,indent=2)+"\n").encode()
  item=tarfile.TarInfo("manifest.json");item.size=len(m);item.mode=0o600;t.addfile(item,io.BytesIO(m))
  item=tarfile.TarInfo("candidate/kalkulyator.html");item.size=len(after);item.mode=0o600;t.addfile(item,io.BytesIO(after))
  t.add(tx,arcname="transaction.php")
 (EVIDENCE/"candidate-receipt.json").write_text(json.dumps({"before":BEFORE,"after":sh(after),"bytes":len(after),"tar_sha256":sh(out.read_bytes()),"exact_replacements":1},indent=2))
 return out,sh(after)
def main():
 req=json.loads((ROOT/"tools/nsp-editorial/calculator-request.json").read_text())
 assert req=={"action":"publish","scope":"ONE_LIVE_CALCULATOR_CTA","base_sha256":BEFORE}
 tar,after=candidate()
 print(json.dumps({"status":"CANDIDATE_PASS","files":1,"after":after}),flush=True)
 host=os.environ["HOST"];user=os.environ["SSH_USER"];port=os.environ.get("PORT","22")
 assert re.fullmatch("[0-9]+",port)
 assert re.fullmatch("[A-Za-z0-9._-]+",host) and re.fullmatch("[A-Za-z0-9._-]+",user)
 key=str(pathlib.Path.home()/".ssh/nsp_final_key")
 opts=["-i",key,"-o","BatchMode=yes","-o","IdentitiesOnly=yes","-o","ConnectTimeout=12","-o","ServerAliveInterval=10","-o","ServerAliveCountMax=3"]
 ssh=["ssh","-p",port,*opts,user+"@"+host];scp=["scp","-P",port,*opts]
 rid=os.environ["GITHUB_RUN_ID"];attempt=os.environ.get("GITHUB_RUN_ATTEMPT","1")
 assert re.fullmatch("[0-9]+",rid) and re.fullmatch("[0-9]+",attempt)
 relative="nsp-migration-private/calc-cta-"+rid+"-"+attempt
 directory='"$HOME/'+relative+'"';site='"$HOME/www/nastoronepodryadchika.ru"'
 run(ssh+['umask 077; test -d "$HOME/nsp-migration-private" && test -d '+site+' && mkdir '+directory],timeout=38)
 run(scp+[str(tar),user+"@"+host+":"+relative+"/candidate.tar"],timeout=75)
 run(ssh+["umask 077; cd "+directory+" && tar -xf candidate.tar && chmod -R go-rwx ."],timeout=40)
 def tx(action):
  result=run(ssh+["php "+directory+"/transaction.php "+action+" "+site+" "+directory],timeout=100)
  row=json.loads(result.splitlines()[-1]);assert row["status"]=="PASS" and row["mode"]==action;return row
 dry=tx("dry-run");assert dry["files"]==1 and dry["writes_to_public"]==0
 (EVIDENCE/"hosting-dry-run.json").write_text(json.dumps(dry,indent=2))
 applied=False
 try:
  done=tx("apply");applied=True
  assert done["files"]==1 and done["protected_php"]=="UNCHANGED" and done["masters"]=="UNCHANGED"
  # Verify exact public content; no reliance on deploy-completed status alone.
  request=urllib.request.Request(URL,headers={"Accept-Encoding":"identity","Cache-Control":"no-cache","User-Agent":"NSP-single-page-postcheck/1.0"})
  with urllib.request.urlopen(request,timeout=15) as response:live=response.read(120000)
  assert sh(live)==after,"PUBLIC_SHA_MISMATCH"
  checked=tx("verify");assert checked["protected_php"]=="UNCHANGED" and checked["masters"]=="UNCHANGED"
  (EVIDENCE/"hosting-verify.json").write_text(json.dumps(checked,indent=2))
  print(json.dumps({"status":"VERIFIED_RELEASE","path":"kalkulyator.html","before_sha256":BEFORE,"after_sha256":after,"public_sha":"PASS","products":"UNCHANGED","php":"UNCHANGED"}))
  applied=False
 except BaseException:
  if applied:
   try:
    restored=tx("rollback");(EVIDENCE/"rollback.json").write_text(json.dumps(restored,indent=2))
    print("AUTO_ROLLBACK=PASS",file=sys.stderr)
   except BaseException as err:print("AUTO_ROLLBACK_FAILED="+str(err),file=sys.stderr)
  raise
if __name__=="__main__":main()
