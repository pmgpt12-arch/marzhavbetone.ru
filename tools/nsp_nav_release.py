#!/usr/bin/env python3
"""Rename the public free-materials navigation label using current production files."""
import os, pathlib, subprocess, re, hashlib, datetime, shlex, sys
site=os.environ["SITE_PATH"]
host=os.environ["HOST"]
user=os.environ["USER"]
port=os.environ["SSH_PORT"]
apply=os.getenv("APPLY")=="true"
key=str(pathlib.Path.home()/".ssh/deploy_key")
ssh=["ssh","-o","BatchMode=yes","-o","IdentitiesOnly=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=12","-i",key,"-p",port,f"{user}@{host}"]
scp=["scp","-q","-o","BatchMode=yes","-o","IdentitiesOnly=yes","-o","StrictHostKeyChecking=yes","-i",key,"-P",port]
def remote(cmd,timeout=30):
    return subprocess.run(ssh+[cmd],check=True,capture_output=True,timeout=timeout).stdout
def run(cmd):
    subprocess.run(cmd,check=True,timeout=35,capture_output=True)
names=remote("cd "+shlex.quote(site)+" && find . -maxdepth 3 -type f -name '*.html' ! -path '*/rebrand-preview*' -print").decode().splitlines()
names=[n[2:] for n in names if n.startswith("./")]
assert 30<=len(names)<300 and {"index.html","katalog.html","materialy/index.html"}<=set(names),len(names)
nav=re.compile(r'(<a\b[^>]*\bhref="/materialy/"[^>]*>)\s*Бесплатно\s*(</a>)')
changes={}
original={}
matches=0
for name in names:
    b=remote("cat "+shlex.quote(site+"/"+name),timeout=20)
    try:old=b.decode("utf-8")
    except UnicodeDecodeError:continue
    new,num=nav.subn(lambda m:m.group(1)+"Шаблоны актов"+m.group(2),old)
    matches+=num
    if name=="index.html":
        practice_old='<a href="/articles/">Практика</a>'
        assert old.count(practice_old)==1, "main navigation practice link mismatch"
        new=new.replace(practice_old,'<a href="/articles/">Практика и судебные решения</a>',1)
        prior="<h3>Бесплатные документы для строительного подрядчика</h3>"
        assert prior in new
        new=new.replace(prior,"<h3>Шаблоны актов</h3>",1)
    if name=="materialy/index.html":
        oldh="<h1>Бесплатные документы для строительного подрядчика</h1>"
        assert oldh in new
        new=new.replace(oldh,"<h1>Шаблоны актов</h1>",1)
        new=new.replace("<title>Бесплатные документы для строительного подрядчика — На стороне подрядчика</title>","<title>Шаблоны актов — На стороне подрядчика</title>",1)
        new=new.replace('property="og:title" content="Бесплатные документы для строительного подрядчика"','property="og:title" content="Шаблоны актов"',1)
    if old!=new:
        for p in [r'data-sku="[^"]*"',r'data-price="[^"]*"',r'href="[^"]*"',r'src="[^"]*"']:
            assert re.findall(p,old)==re.findall(p,new),(name,p)
        original[name]=b
        changes[name]=new.encode("utf-8")
assert len(changes)>=20 and matches>=20,(len(changes),matches)
print("NAV_PREFLIGHT_PASS",len(changes),"files",matches,"menu links",flush=True)
if not apply:
    print("NAV_DRY_RUN_PASS",flush=True)
    sys.exit(0)
# Package a single guarded, reversible batch. Each file is read from the active production root.
import io, tarfile
import time
timestamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup="nsp-nav-backup-"+timestamp
archive=pathlib.Path("/tmp/nsp-nav-batch.tar.gz")
before_manifest=pathlib.Path("/tmp/nsp-nav-before.sha256")
after_manifest=pathlib.Path("/tmp/nsp-nav-after.sha256")
before_manifest.write_text("".join(hashlib.sha256(original[n]).hexdigest()+"  "+n+"\n" for n in sorted(changes)),encoding="utf-8")
after_manifest.write_text("".join(hashlib.sha256(changes[n]).hexdigest()+"  "+n+"\n" for n in sorted(changes)),encoding="utf-8")
with tarfile.open(archive,"w:gz") as tar:
    for n in sorted(changes):
        data=changes[n]
        info=tarfile.TarInfo(name=n)
        info.size=len(data)
        info.mode=0o644
        tar.addfile(info,io.BytesIO(data))
remote_dir="nsp-nav-stage-"+timestamp
remote('mkdir -m 700 -p "$HOME/'+remote_dir+'"')
for local,filename in [(archive,"candidate.tar.gz"),(before_manifest,"before.sha256"),(after_manifest,"after.sha256")]:
    run(scp+[str(local),f"{user}@{host}:"+remote_dir+"/"+filename])
# Perform full old-SHA check, backup, extraction, full new-SHA check and rollback inside a single SSH process.
script="""set -eu
SITE="$HOME/"""+site+""""
STAGE="$HOME/"""+remote_dir+""""
BACKUP="$HOME/"""+backup+""""
cd "$SITE"
sha256sum -c "$STAGE/before.sha256" >/dev/null
mkdir -m 700 -p "$BACKUP"
# Back up via manifest paths without any public webroot file deletion.
awk '{print $2}' "$STAGE/before.sha256" > "$STAGE/paths.txt"
tar -czf "$BACKUP/originals.tar.gz" -T "$STAGE/paths.txt"
echo NAV_BACKUP_PASS
if tar -xzf "$STAGE/candidate.tar.gz" -C "$SITE" && sha256sum -c "$STAGE/after.sha256" >/dev/null; then
  echo NAV_UPLOAD_PASS
else
  tar -xzf "$BACKUP/originals.tar.gz" -C "$SITE"
  sha256sum -c "$STAGE/before.sha256" >/dev/null
  echo NAV_ROLLBACK_PASS
  exit 21
fi
"""
result=subprocess.run(ssh+["sh -s"],input=script,text=True,capture_output=True,timeout=100)
print(result.stdout,flush=True)
if result.returncode:
    print(result.stderr[-1400:],file=sys.stderr,flush=True)
    raise RuntimeError("NAV_BATCH_FAILED "+str(result.returncode))
