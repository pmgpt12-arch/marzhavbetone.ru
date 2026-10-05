import functools, json, os, signal, socket, socketserver, subprocess, tempfile, threading, time
from pathlib import Path
ROOT=Path("/home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical/pr283")
OUT=ROOT/"tools/candidates/PR283_VISUAL_2026-10-05"
source=(OUT/"render-diagnostic.py").read_text()
prefix=source.split("server=socketserver.TCPServer",1)[0]
namespace={}
exec(compile(prefix,"prior-diagnostic-serving-handler","exec"),namespace)
sources=["articles/ks-2-ks-3-podpisany-zakazchik-ne-oplachivaet.html","articles/index.html","assets/ks-2-ks-3-podpisany-zakazchik-ne-oplachivaet.jpg","styles.css","article.css","attribution.js"]
for p in sources:
    expected=subprocess.run(["git","-C",str(ROOT),"show","14c5a562c93ad7f7c28aa73588d9ca2d8b35fea3:"+p],capture_output=True,check=True,timeout=10).stdout
    assert (ROOT/p).read_bytes()==expected, "Source changed "+p
server=socketserver.TCPServer(("127.0.0.1",0),functools.partial(namespace["Handler"],directory=str(ROOT)))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base="http://127.0.0.1:"+str(server.server_address[1])
with socket.socket() as reserve:
    reserve.bind(("127.0.0.1",0));debug_port=reserve.getsockname()[1]
start=time.monotonic();chrome=None;result=None
try:
    with tempfile.TemporaryDirectory(prefix="pr283-cdp-profile-") as profile:
        chrome_log=OUT/"cdp-chrome.stderr.log"
        with chrome_log.open("w") as stderr:
            command=["/usr/bin/google-chrome","--headless=new","--no-sandbox","--disable-gpu","--hide-scrollbars","--disable-background-networking","--disable-component-update","--disable-sync","--disable-default-apps","--no-first-run","--metrics-recording-only","--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1","--user-data-dir="+profile,"--remote-debugging-address=127.0.0.1","--remote-debugging-port="+str(debug_port),"about:blank"]
            chrome=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=stderr,start_new_session=True)
            try:
                result=subprocess.run(["node",str(OUT/"cdp-render.mjs"),str(debug_port),base,str(OUT)],capture_output=True,text=True,timeout=90)
                (OUT/"cdp-node.stdout.log").write_text(result.stdout)
                (OUT/"cdp-node.stderr.log").write_text(result.stderr)
                print(result.stdout,flush=True);print(result.stderr,flush=True)
            finally:
                if chrome.poll() is None:
                    os.killpg(chrome.pid,signal.SIGTERM)
                    try:chrome.wait(timeout=3)
                    except subprocess.TimeoutExpired:os.killpg(chrome.pid,signal.SIGKILL);chrome.wait(timeout=3)
finally:
    server.shutdown();server.server_close();thread.join(timeout=2)
    receipt={"frozen_input_sha":"14c5a562c93ad7f7c28aa73588d9ca2d8b35fea3","source_inputs_equal_git":True,"http_base":base,"debug_address":"127.0.0.1","debug_port":debug_port,"chrome_command":command,"chrome_exit_code":chrome.poll() if chrome else None,"owned_chrome_process_stopped":chrome.poll() is not None if chrome else True,"server_closed":True,"temporary_profile_removed":True,"post_requests":sum(r["method"]=="POST" for r in namespace["requests"]),"http_requests":namespace["requests"],"node_exit_code":result.returncode if result else None,"elapsed_seconds":time.monotonic()-start}
    (OUT/"cdp-process-receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
if result is None or result.returncode:raise SystemExit(1)
