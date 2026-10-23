from pathlib import Path
import subprocess,json,hashlib,fcntl,time,shutil,xml.etree.ElementTree as E
N=Path("/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011")
R=Path("/home/denis/projects/nsp-audit-fixes-20261021/qa/integration-20261022/repo")
O=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lock=(N/"diagnostics/office-access-20261021-222308/check.lock").open("a")
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
env={"__name__":"qa01_submitter"}
exec(compile(subprocess.check_output(["git","-C",str(R),"show","65c176aa554397c12652a86fe2393942faa546a7:tools/submit_office_review_job.py"],text=True,timeout=20),"qa01_submitter","exec"),env)
assert all(env["previous_is_complete"](N,c) for c in ["word","native"])
journal=subprocess.check_output(["journalctl","--user","-u","mb-excel-transport.service","--since","3 minutes ago","--no-pager"],text=True,timeout=10)
assert "192.168.1.140" in journal and "GET /word/" in journal,"No fresh Word polling"
(O/"transport-preflight.log").write_text(journal)
previous=(N/"word/current.xml").read_bytes()
jid="nsp-qa01-retention-fl10-20261023"
d=N/"word"/jid;assert not d.exists()
d.mkdir()
root=E.Element("job",id=jid,qa_only="true")
for key,tag in [("original","before"),("candidate","after")]:
 f=O/(key+".docx");shutil.copy2(f,d/f.name)
 E.SubElement(root,"file",name=f.name,tag=tag,sha256=sha(f))
E.ElementTree(root).write(d/"job.xml",encoding="utf-8",xml_declaration=True)
shutil.copy2(d/"job.xml",O/"job.xml")
assert (N/"word/current.xml").read_bytes()==previous
env["submit"](N,"word",d)
print("SUBMITTED",jid,flush=True)
rp=N/"results/word"/jid/"report.xml";deadline=time.monotonic()+240
while time.monotonic()<deadline:
 assert E.parse(N/"word/current.xml").getroot().get("id")==jid,"Foreign queue preserved; controller stops"
 if rp.exists():break
 time.sleep(3)
if not rp.exists():raise RuntimeError("NO_RECEIPT_240S; no retry and no pointer restoration")
rt=E.parse(rp).getroot();assert rt.get("job")==jid
shutil.copytree(rp.parent,O/"evidence")
assert E.parse(N/"word/current.xml").getroot().get("id")==jid
(N/"word/current.xml").write_bytes(previous)
rows=[]
for el in rt.findall("file"):
 tag=el.get("tag");name=el.get("name") or next(f.get("name")for f in root.findall("file")if f.get("tag")==tag)
 pdf=rp.parent/(tag+".pdf")
 row=dict(el.attrib)
 row["result"]=el.find("result").attrib if el.find("result")is not None else {}
 if pdf.exists():
  row["pdf_sha256_verified"]=sha(pdf)
  row["pdf_info"]=subprocess.check_output(["pdfinfo",str(pdf)],text=True,timeout=15)
  row["text"]=subprocess.check_output(["pdftotext","-layout",str(pdf),"-"],text=True,timeout=15)
  assert el.get("pdf_sha256")==sha(pdf)
 rows.append(row)
assert sha(O/"candidate.docx")=="5647f33e362ed59338ea3fc46783f2d61572093bd0378353e6b3e459b1337e60"
result=dict(job=jid,status=rt.get("status"),receipt_sha256=sha(rp),files=rows,queue_restored=True,visual_review="PENDING",publication=False)
(O/"RESULTS.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:result[k] for k in ["job","status","receipt_sha256","queue_restored"]}),flush=True)
