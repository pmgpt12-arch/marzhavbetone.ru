#!/usr/bin/env python3
"""Unify NSP static HTML header on current production baseline, cart and mobile nav."""
import os,re,hashlib,subprocess,pathlib,datetime,shlex,io,tarfile,sys,collections
site=os.environ["SITE_PATH"];host=os.environ["HOST"];user=os.environ["USER"];port=os.environ["SSH_PORT"]
apply=os.environ.get("APPLY")=="true"
key=str(pathlib.Path.home()/".ssh/deploy_key")
ssh=["ssh","-o","BatchMode=yes","-o","IdentitiesOnly=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=12","-i",key,"-p",port,f"{user}@{host}"]
scp=["scp","-q","-o","BatchMode=yes","-o","IdentitiesOnly=yes","-o","StrictHostKeyChecking=yes","-i",key,"-P",port]
def remote(command,timeout=24):
    return subprocess.run(ssh+[command],timeout=timeout,check=True,capture_output=True).stdout
def upload(local,remote_path):
    subprocess.run(scp+[str(local),f"{user}@{host}:"+remote_path],check=True,timeout=40,capture_output=True)
NAV=[("Диагностика","/diagnostika.html"),("Каталог","/katalog.html"),("Шаблоны актов","/materialy/"),("Калькуляторы","/kalkulyator.html"),("Практика и судебные решения","/articles/"),("О проекте","/#author")]
HEADER_RE=re.compile(r'<header\s+class="topbar[^"]*"[^>]*>.*?</header>',re.S)
CART_RE=re.compile(r'\s*<aside class="cart-panel" id="cart-panel".*?</aside>\s*<div class="cart-backdrop" id="cart-backdrop" hidden></div>',re.S)
BASE=pathlib.Path(__file__).resolve().parent.parent
catalog=(BASE/"katalog.html").read_text(encoding="utf-8")
cart_match=CART_RE.search(catalog)
assert cart_match, "canonical cart UI not found"
CART_HTML=cart_match.group().strip()
assert all('id="'+id+'"' in CART_HTML for id in ("cart-panel","cart-close","cart-empty","cart-items","cart-total","cart-checkout","cart-backdrop"))
css=(BASE/"nsp-unified-header.css").read_bytes()
if os.environ.get("CSS_ONLY")=="true":
    target=site+"/nsp-unified-header.css"
    before=remote("cat "+shlex.quote(target),timeout=20)
    baseline=hashlib.sha256(before).hexdigest()
    assert baseline=="59847b051d76f7b708f23a18e678f8c3101066500b89393b9f08a03dfc659993",("unexpected live CSS baseline",baseline)
    assert hashlib.sha256(css).hexdigest()=="60ca6847a84e40729f3a3836bbcd2efcf1fc3f80fc1b6d24e08dc258e264ed4d", "new css checksum"
    print("HEADER_CSS_PREFLIGHT_PASS",baseline,flush=True)
    if not apply:
        print("HEADER_CSS_DRY_RUN_PASS",flush=True)
        sys.exit(0)
    backup="nsp-header-css-backup-"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    remote('mkdir -m 700 -p "$HOME/'+backup+'" && cp '+shlex.quote(target)+' "$HOME/'+backup+'/nsp-unified-header.css"')
    assert remote("sha256sum "+shlex.quote(target)).decode().split()[0]==baseline,"concurrent CSS update"
    local=pathlib.Path("/tmp/nsp-header-css-stage.css");local.write_bytes(css)
    temp=target+".incoming"
    upload(local,temp)
    assert remote("sha256sum "+shlex.quote(temp)).decode().split()[0]==hashlib.sha256(css).hexdigest(),"staged CSS mismatch"
    remote("mv "+shlex.quote(temp)+" "+shlex.quote(target))
    if remote("sha256sum "+shlex.quote(target)).decode().split()[0]!=hashlib.sha256(css).hexdigest():
        remote('cp "$HOME/'+backup+'/nsp-unified-header.css" '+shlex.quote(target))
        raise RuntimeError("CSS failed verification; rolled back")
    print("HEADER_CSS_UPLOAD_PASS",backup,flush=True)
    sys.exit(0)
def current(path):
    if path=="diagnostika.html":return "/diagnostika.html"
    if path=="katalog.html" or path.startswith("products/") or path.startswith("demo/"):return "/katalog.html"
    if path=="kalkulyator.html":return "/kalkulyator.html"
    if path.startswith("materialy/"):return "/materialy/"
    if path.startswith("articles/"):return "/articles/"
    return None
def header_for(path):
    active=current(path)
    links="".join('<a href="'+href+'"'+(' class="is-current" aria-current="page"' if href==active else '')+'>'+label+'</a>' for label,href in NAV)
    return ('<header class="topbar nsp-unified-header"><a class="brand" href="/" aria-label="На стороне подрядчика, на главную">'
            '<span class="brand-mark">Н</span><span>на стороне подрядчика</span></a>'
            '<nav aria-label="Основная навигация">'+links+'</nav>'
            '<button class="button button-small cart-toggle" id="cart-toggle" type="button" aria-controls="cart-panel" aria-expanded="false">'
            'Корзина · <span id="cart-count">0</span></button></header>')
def transform(path,old):
    match=HEADER_RE.search(old)
    if not match:return None
    if 'aria-label="Основная навигация"' not in match.group():raise RuntimeError("no primary nav: "+path)
    new=old[:match.start()]+header_for(path)+old[match.end():]
    if 'id="cart-panel"' not in new:
        h=HEADER_RE.search(new)
        new=new[:h.end()]+"\n  "+CART_HTML+"\n"+new[h.end():]
    else:
        for id in ["cart-toggle","cart-panel","cart-backdrop","cart-count","cart-items","cart-total","cart-checkout"]:
            assert new.count('id="'+id+'"')==1,(path,id)
    if '/nsp-unified-header.css' not in new:
        assert '</head>' in new
        new=new.replace('</head>','  <link rel="stylesheet" href="/nsp-unified-header.css?v=20261108b">\n</head>',1)
    if 'href="/cart.css' not in new and 'href="cart.css' not in new and 'href="../cart.css' not in new:
        new=new.replace('</head>','  <link rel="stylesheet" href="/cart.css?v=dbf0bfa0">\n</head>',1)
    if 'app-script.php' not in new:
        assert '</body>' in new
        new=new.replace('</body>','  <script type="module" src="/app-script.php?v=21"></script>\n</body>',1)
    # Exact six links, order and cart controls. No customer, product or payment anchors changed.
    h=HEADER_RE.search(new)
    assert h and [x[0] for x in NAV]==re.findall(r'<a href="[^"]+"(?: class="is-current" aria-current="page")?>([^<]+)</a>',h.group())
    assert new.count('id="cart-toggle"')==1 and new.count('id="cart-panel"')==1
    anchor_pat=r'<a\b[^>]*\bhref="([^"]+)"'
    old_body=old[:match.start()]+old[match.end():]
    new_header=HEADER_RE.search(new)
    new_body=new[:new_header.start()]+new[new_header.end():]
    assert collections.Counter(re.findall(anchor_pat,old_body))==collections.Counter(re.findall(anchor_pat,new_body)),("content anchors",path)
    for field in ("data-sku","data-price","data-product","data-product-id"):
        pat=field+r'="[^"]*"'
        assert re.findall(pat,old)==re.findall(pat,new),(path,field)
    return new
# One bounded read-only SSH snapshot rather than an SSH session per page.
archive=remote("cd "+shlex.quote(site)+" && find . -maxdepth 3 -type f -name '*.html' ! -path '*/rebrand-preview*' -print0 | tar --null -T - -czf -",timeout=90)
snapshot={}
with tarfile.open(fileobj=io.BytesIO(archive),mode="r:gz") as tar:
    for item in tar.getmembers():
        if not item.isfile():continue
        p=item.name.removeprefix("./")
        assert ".." not in pathlib.PurePosixPath(p).parts
        snapshot[p]=tar.extractfile(item).read()
assert 80<=len(snapshot)<220 and {"index.html","katalog.html","materialy/index.html","products/p1-oplata-po-ks2.html"}<=set(snapshot),len(snapshot)
original={};candidate={};untouched=[]
for path,b in sorted(snapshot.items()):
    try:old=b.decode("utf-8")
    except UnicodeDecodeError:raise RuntimeError("Invalid UTF-8: "+path)
    changed=transform(path,old)
    if changed is None:untouched.append(path);continue
    if changed!=old:
        original[path]=b;candidate[path]=changed.encode("utf-8")
assert len(candidate)>=80,(len(candidate),untouched)
assert "Шаблоны актов" in candidate["index.html"].decode()
assert "Корзина · " in candidate["materialy/index.html"].decode()
assert "nsp-unified-header" in candidate["katalog.html"].decode()
print("HEADER_PREFLIGHT_PASS",len(candidate),"HTML; navigation 6/6, cart, CSS, JS; excluded",untouched,flush=True)
if not apply:
    print("HEADER_DRY_RUN_PASS no production changes",flush=True)
    sys.exit(0)
# Publish as a single SSH transaction with verified originals, backup and rollback.
timestamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
stage="nsp-unified-stage-"+timestamp
backup="nsp-unified-backup-"+timestamp
work=pathlib.Path("/tmp/nsp-unified-release")
work.mkdir(exist_ok=True)
before=work/"before.sha256";after=work/"after.sha256";bundle=work/"new.tar.gz"
before.write_text("".join(hashlib.sha256(original[p]).hexdigest()+"  "+p+"\n" for p in sorted(original)),encoding="utf-8")
new_files=dict(candidate)
new_files["nsp-unified-header.css"]=css
after.write_text("".join(hashlib.sha256(new_files[p]).hexdigest()+"  "+p+"\n" for p in sorted(new_files)),encoding="utf-8")
with tarfile.open(bundle,"w:gz") as tar:
    for p in sorted(new_files):
        data=new_files[p]
        info=tarfile.TarInfo(p)
        info.size=len(data)
        info.mode=0o644
        tar.addfile(info,io.BytesIO(data))
remote('mkdir -m 700 -p "$HOME/'+stage+'"')
for file,name in ((before,"before.sha256"),(after,"after.sha256"),(bundle,"new.tar.gz")):
    upload(file,stage+"/"+name)
script='''set -eu
SITE="$HOME/'''+site+'''"
STAGE="$HOME/'''+stage+'''"
BACKUP="$HOME/'''+backup+'''"
cd "$SITE"
test ! -e nsp-unified-header.css
sha256sum -c "$STAGE/before.sha256" >/dev/null
mkdir -m 700 -p "$BACKUP"
awk '{print $2}' "$STAGE/before.sha256" > "$STAGE/paths.txt"
tar -czf "$BACKUP/originals.tar.gz" -T "$STAGE/paths.txt"
echo HEADER_BACKUP_PASS
if tar -xzf "$STAGE/new.tar.gz" -C "$SITE" && sha256sum -c "$STAGE/after.sha256" >/dev/null; then
  echo HEADER_UPLOAD_PASS
else
  tar -xzf "$BACKUP/originals.tar.gz" -C "$SITE"
  rm -f "$SITE/nsp-unified-header.css"
  sha256sum -c "$STAGE/before.sha256" >/dev/null
  echo HEADER_ROLLBACK_PASS
  exit 24
fi
'''
result=subprocess.run(ssh+["sh -s"],input=script,text=True,capture_output=True,timeout=120)
print(result.stdout,flush=True)
if result.returncode:
    print(result.stderr[-1800:],file=sys.stderr,flush=True)
    raise RuntimeError("HEADER_DEPLOY_FAILED "+str(result.returncode))
