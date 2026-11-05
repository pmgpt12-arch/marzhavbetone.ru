"""Read-only SHA-pinned comparison: main+From vs production PHP."""
import difflib, hashlib, json, os, pathlib, re, subprocess
M="f28c9564d97ac14ef55df590a42048c709c49fd2"
S={
"lead.php":("9a37f0cd34efddddcbbc16ede01789ceea54fcefbd50395995c1e7115b046c8e","44033788dffc232f8694074c6508f5c056834a3c05b0837b1ec0222771a0dcd9"),
"webhook.php":("c8d758c1234e47466b212dbe91ddd3466aa24b64f6d50ecd669a16bc6655cb2d","239b4433934b59647315ae8728b582cdc83a34d01a0be7dc85f513c163dc60d5"),
"products-config.php":("10739a7aff2a98e676c1e15b3499c64ad82703d0d6a3c6650b3dab751ce70551","12abc5750cc7f1d223cbeb002628338e2261e85e4bd4c3d6b8988cd7da295934")}
def run(cmd,timeout=30):
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.returncode: raise RuntimeError("READ_FAILED_"+cmd[0])
 return p.stdout
def sha(b):return hashlib.sha256(b).hexdigest()
run(["git","fetch","--depth=1","--no-tags","origin",M],35)
ssh=["ssh","-p",os.environ["PORT"],"-i",str(pathlib.Path.home()/".ssh/nsp_final_key"),"-o","IdentitiesOnly=yes","-o","BatchMode=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=12",os.environ["SSH_USER"]+"@"+os.environ["HOST"]]
rows={}
for n,(before,after) in S.items():
 src=run(["git","show",M+":"+n],12)
 assert sha(src)==before and src.count(b"From: site@marzhavbetone.ru")==1,n
 changed=src.replace(b"From: site@marzhavbetone.ru",b"From: site@nastoronepodryadchika.ru")
 cmd='f="$HOME/www/nastoronepodryadchika.ru/'+n+'"; test -f "$f" && test ! -L "$f" && cat "$f"'
 live=run(ssh+[cmd],35)
 assert sha(live)==after and live.count(b"From: site@nastoronepodryadchika.ru")==1,n
 delta="".join(difflib.unified_diff(changed.decode().splitlines(True),live.decode().splitlines(True),n=2))
 assert len(delta)<12000 and not re.search(r"(?i)(password|secret_key|private_key|bearer\s)",delta),n
 rows[n]={"main_sha":before,"live_sha":after,"main_after_from_sha":sha(changed),"matches":changed==live,"diff":delta}
p=pathlib.Path("/tmp/nsp-final-evidence/mail-source-live-diff.json");p.parent.mkdir(exist_ok=True)
p.write_text(json.dumps({"status":"PASS","read_only":True,"records":rows},ensure_ascii=False,indent=2))
print("NSP_SHA_DIFF_PASS",json.dumps({k:{"exact":v["matches"],"diff_lines":len(v["diff"].splitlines())} for k,v in rows.items()}))
