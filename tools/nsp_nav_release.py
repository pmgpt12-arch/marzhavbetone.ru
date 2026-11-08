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
for name,b in original.items():
    assert remote("sha256sum "+shlex.quote(site+"/"+name)).decode().split()[0]==hashlib.sha256(b).hexdigest(),("changed",name)
backup="nsp-nav-backup-"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
remote('mkdir -m 700 -p "$HOME/'+backup+'"')
for name in changes:
    parent=str(pathlib.PurePosixPath(name).parent)
    remote('mkdir -p "$HOME/'+backup+'/'+parent+'" && cp '+shlex.quote(site+"/"+name)+' "$HOME/'+backup+'/'+name+'"')
print("NAV_BACKUP_PASS",backup,len(changes),flush=True)
staged=pathlib.Path("/tmp/nsp-nav-stage")
done=[]
try:
    for name,b in changes.items():
        assert remote("sha256sum "+shlex.quote(site+"/"+name)).decode().split()[0]==hashlib.sha256(original[name]).hexdigest(),("race",name)
        f=staged/name
        f.parent.mkdir(parents=True,exist_ok=True)
        f.write_bytes(b)
        target=site+"/"+name
        temp=target+".nsp-nav-incoming"
        run(scp+[str(f),f"{user}@{host}:"+temp])
        assert remote("sha256sum "+shlex.quote(temp)).decode().split()[0]==hashlib.sha256(b).hexdigest()
        remote("mv "+shlex.quote(temp)+" "+shlex.quote(target))
        done.append(name)
    for name,b in changes.items():
        assert remote("sha256sum "+shlex.quote(site+"/"+name)).decode().split()[0]==hashlib.sha256(b).hexdigest(),name
    print("NAV_UPLOAD_PASS",len(done),flush=True)
except BaseException:
    print("NAV_FAILED_ROLLING_BACK",len(done),flush=True)
    for name in reversed(done):
        try:remote('cp "$HOME/'+backup+'/'+name+'" '+shlex.quote(site+"/"+name))
        except Exception as ex:print("ROLLBACK_FAILED",name,str(ex),flush=True)
    raise
