from pathlib import Path
import subprocess,hashlib,json,shutil
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';ROOT=Q.parents[1];listing=subprocess.check_output(['git','-C',str(R),'ls-tree','-r','HEAD','--','downloads'],text=True);rows=[]
for line in listing.splitlines():
 left,path=line.split('\t');blob=left.split()[2];t=R/path
 if t.exists():b=t.read_bytes()
 else:
  choices=[ROOT/path,ROOT/'qa/remaining-audit-20261022/free-sources'/path]
  p=next((p for p in choices if p.is_file()),None);b=p.read_bytes()if p else subprocess.check_output(['git','-C',str(R),'show','HEAD:'+path],timeout=12)
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob,(path,'SOURCE_DIVERGED');t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob;rows.append({'path':path,'git_blob':blob,'sha256':hashlib.sha256(b).hexdigest()})
(Q/'FREE_SOURCE_ARCHIVES.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print('DOWNLOAD_SOURCES',len(rows))
