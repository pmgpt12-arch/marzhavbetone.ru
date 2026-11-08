#!/usr/bin/env python3
"""Deploy only the verified app.js cart cleanup, via existing SSH secrets."""
import os,hashlib,pathlib,subprocess,shlex,datetime,sys
site=os.environ["SITE_PATH"]
host=os.environ["HOST"]
user=os.environ["USER"]
port=os.environ["SSH_PORT"]
apply=os.getenv("APPLY")=="true"
source=pathlib.Path(__file__).resolve().parent.parent/"app.js"
payload=source.read_bytes()
expected_before="9924f5c20b4046f0eecabaea8be47c0342adaf67cb1d25c0155dc3d7b33bc6fc"
expected_after="cd63cc8a7a12a1bc37db330570ef4b6b488898646cecd7953c8ec1a053ffefbf"
assert hashlib.sha256(payload).hexdigest()==expected_after,"Unexpected candidate file"
assert b"window.location.pathname !== '/test-pokupka.html'" in payload
assert b"item.sku !== 'test1'" in payload
assert b"function saveCart()" in payload and b"fetch('/payment.php'" in payload
key=str(pathlib.Path.home()/".ssh/deploy_key")
ssh=["ssh","-o","BatchMode=yes","-o","IdentitiesOnly=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=12","-i",key,"-p",port,f"{user}@{host}"]
scp=["scp","-q","-o","BatchMode=yes","-o","IdentitiesOnly=yes","-o","StrictHostKeyChecking=yes","-i",key,"-P",port]
def remote(cmd,timeout=30):
    return subprocess.run(ssh+[cmd],check=True,capture_output=True,timeout=timeout).stdout
target=site+"/app.js"
before=remote("sha256sum "+shlex.quote(target)).decode().split()[0]
assert before==expected_before,("Unexpected production app.js; stop without writing",before)
print("CART_PREFLIGHT_PASS",before,expected_after,flush=True)
if not apply:
    print("CART_DRY_RUN_PASS",flush=True)
    sys.exit(0)
timestamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup="nsp-cart-test1-backup-"+timestamp
remote('mkdir -m 700 -p "$HOME/'+backup+'" && cp '+shlex.quote(target)+' "$HOME/'+backup+'/app.js"')
print("CART_BACKUP_PASS",backup,flush=True)
assert remote("sha256sum "+shlex.quote(target)).decode().split()[0]==expected_before, "Concurrent change detected before upload"
staged=target+".cart-test1-incoming"
subprocess.run(scp+[str(source),f"{user}@{host}:"+staged],check=True,capture_output=True,timeout=35)
assert remote("sha256sum "+shlex.quote(staged)).decode().split()[0]==expected_after,"Staged SHA mismatch"
assert remote("sha256sum "+shlex.quote(target)).decode().split()[0]==expected_before,"Concurrent change detected before replace"
remote("mv "+shlex.quote(staged)+" "+shlex.quote(target))
if remote("sha256sum "+shlex.quote(target)).decode().split()[0]!=expected_after:
    remote('cp "$HOME/'+backup+'/app.js" '+shlex.quote(target))
    raise RuntimeError("Production SHA mismatch; rollback completed")
print("CART_UPLOAD_PASS",expected_after,flush=True)
