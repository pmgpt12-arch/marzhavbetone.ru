from pathlib import Path
import subprocess,json,hashlib,datetime
R=Path("/home/denis/.local/state/claude-dispatcher/recovery-20261005/catalog-baseline-citations-20261005")
argv=["timeout","--kill-after=5s","120s","python3",str(R/"extract_catalog.py")]
p=subprocess.run(argv,capture_output=True,text=True,timeout=130)
row={"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"argv":argv,"exit":p.returncode,"stdout":p.stdout,"stderr":p.stderr};(R/"execution-output.json").write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n")
print("ACTUAL_EXIT",p.returncode,p.stdout[-10000:],p.stderr[-4000:],flush=True)
if p.returncode==0:
 h=lambda b:hashlib.sha256(b).hexdigest();files=sorted(f for f in R.rglob("*") if f.is_file() and f.name not in ["SHA256SUMS","READY.json"]);(R/"SHA256SUMS").write_text("\n".join(h(f.read_bytes())+"  "+str(f.relative_to(R)) for f in files)+"\n")
 ready=json.loads((R/"READY.json").read_text());ready["manifest_sha256"]=h((R/"SHA256SUMS").read_bytes());ready["execution_output_sha256"]=h((R/"execution-output.json").read_bytes());ready["freeze_after_execution_output"]=True;(R/"READY.json").write_text(json.dumps(ready,ensure_ascii=False,indent=2)+"\n")
 print("READY_HASH",h((R/"READY.json").read_bytes()),"AGGREGATE",ready["aggregate_sha256"],"SCRIPT",ready["script_sha256"],flush=True)
