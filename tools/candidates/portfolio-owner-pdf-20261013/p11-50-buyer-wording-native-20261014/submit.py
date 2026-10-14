#!/usr/bin/env python3
from pathlib import Path
from lxml import etree as ET
from datetime import datetime,timezone,timedelta
import hashlib,json,os,re,shutil,subprocess,time

ROOT=Path("/home/denis/projects/mb001-p11-registry-nomination-20261014")
C=ROOT/"tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami"
E=ROOT/"tools/candidates/portfolio-owner-pdf-20261013/p11-50-buyer-wording-native-20261014"
B=Path("/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011")
JOB="p11-50-buyer-wording-word-20261014-v1"
NAME="50-slovar-poley-raschet-metrami.docx"; TAG="50"
SHA="b0bd9d309115377c0e80c418d2dda1acdf3d33d4863feb2f15de69b70099427c"
HEAD="27573b16efc45508172e3f4dce33f1ad281ae62c"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def fsfile(p):
    with p.open("rb") as f: os.fsync(f.fileno())
def fsdir(p):
    fd=os.open(p,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
def atomic(p,b):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+".tmp")
    with t.open("wb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
    os.replace(t,p); fsdir(p.parent)
def aj(p,o): atomic(p,(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode())

def run():
    assert subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()==HEAD
    src=C/NAME; assert sha(src)==SHA
    D=B/"word"/JOB; R=B/"results/word"/JOB; current=B/"word/current.xml"
    assert not D.exists() and not R.exists()
    old=current.read_bytes(); prev=ET.fromstring(old).get("id"); assert (B/"results/word"/prev/"report.xml").exists()
    log=max(B.glob("transport*.log"),key=lambda p:p.stat().st_mtime)
    polls=[x for x in log.read_text(errors="replace").splitlines()[-160:] if "192.168.1.140" in x and "GET /word/current.xml HTTP/1.0\" 204" in x]
    assert polls
    stamp=re.search(r"\[(.*?)\]",polls[-1]).group(1)
    at=datetime.strptime(stamp,"%d/%b/%Y %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=7))).timestamp()
    age=time.time()-at; assert 0<=age<=90,age
    aj(E/"native-passport.json",{"schema_version":1,"id":"P11-50-BUYER-WORDING-NATIVE","status":"PREPARED","prepared_at_utc":datetime.now(timezone.utc).isoformat(),"input_head":HEAD,"job":JOB,"input":{NAME:SHA},"executor":{"path":str(Path(__file__).relative_to(ROOT)),"sha256":sha(Path(__file__))},"previous_job":prev,"idle_poll":polls[-1],"idle_age_seconds":round(age,1),"acceptance":["raw Word report input SHA PASS","Word PASS","2 A4 pages","all pages visually reviewed","replacement text visible without clipping/overlap","independent review pending"],"checkpoint_policy":"verified_only","release":"HOLD","model_calls":0})
    D.mkdir()
    dst=D/NAME; shutil.copy2(src,dst); fsfile(dst)
    job=ET.Element("job",id=JOB); ET.SubElement(job,"file",name=NAME,tag=TAG,sha256=SHA)
    xml=ET.tostring(job,encoding="utf-8",xml_declaration=True)
    atomic(D/"job.xml",xml)
    stage={"schema_version":1,"job":JOB,"status":"STAGED_NOT_SUBMITTED","previous_job":prev,"idle_poll":polls[-1],"input":{NAME:SHA},"release":"HOLD"}
    aj(D/"stage-receipt.json",stage); assert current.read_bytes()==old
    atomic(current,xml); stage["status"]="SUBMITTED_AWAITING_RESULT"; stage["submitted_at_utc"]=datetime.now(timezone.utc).isoformat(); aj(D/"stage-receipt.json",stage)
    start=time.monotonic()
    while not (R/"report.xml").exists() and time.monotonic()-start<150: time.sleep(4)
    if not (R/"report.xml").exists(): raise TimeoutError("No result; inspect late result, do not retry")
    rep=ET.parse(str(R/"report.xml")).getroot(); assert rep.get("job")==JOB
    N=E/"native"; N.mkdir()
    for p in R.iterdir():
        if p.is_file(): shutil.copy2(p,N/p.name); fsfile(N/p.name)
    for pdf in N.glob("*.pdf"):
        subprocess.run(["pdftoppm","-png","-r","140",str(pdf),str(N/pdf.stem)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=40)
    for p in N.glob("*.png"): fsfile(p)
    fsdir(N); outputs={p.name:sha(p) for p in sorted(N.iterdir()) if p.is_file()}
    aj(E/"native-receipt.json",{"schema_version":1,"job":JOB,"status":rep.get("status"),"input":{NAME:SHA},"outputs":outputs,"finished_at_utc":datetime.now(timezone.utc).isoformat(),"visual_review":"PENDING","release":"HOLD"})
    atomic(E/"native-exit.code",b"0\n" if rep.get("status")=="PASS" else b"1\n")
    print(json.dumps({"job":JOB,"status":rep.get("status"),"outputs":outputs},ensure_ascii=False,sort_keys=True))
    return 0 if rep.get("status")=="PASS" else 1

if __name__=="__main__":
    try: raise SystemExit(run())
    except Exception as e:
        aj(E/"native-failure.json",{"schema_version":1,"job":JOB,"status":"FAIL_OR_UNKNOWN","error_type":type(e).__name__,"error":str(e),"finished_at_utc":datetime.now(timezone.utc).isoformat(),"release":"HOLD"})
        atomic(E/"native-exit.code",b"1\n"); raise
