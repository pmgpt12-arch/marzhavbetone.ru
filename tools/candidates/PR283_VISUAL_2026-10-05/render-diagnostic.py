import functools, hashlib, http.server, json, re, socketserver, subprocess, tempfile, threading, time
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from PIL import Image
ROOT=Path("/home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical/pr283")
OUT=ROOT/"tools/candidates/PR283_VISUAL_2026-10-05"
OUT.mkdir(exist_ok=True)
SLUG="ks-2-ks-3-podpisany-zakazchik-ne-oplachivaet"
requests=[]
SCRIPT=r"""<script>
window.addEventListener('load', () => { setTimeout(() => {
  const target = document.querySelector('a.showcase-card[href="ks-2-ks-3-podpisany-zakazchik-ne-oplachivaet.html"]');
  if (location.pathname.endsWith('/index.html') && target) target.scrollIntoView({block:'start'});
  const cover = document.querySelector('img.article-cover') || (target && target.querySelector('img'));
  if(cover) { cover.loading='eager'; }
  const read = el => { if(!el) return null; const b=el.getBoundingClientRect(); const c=getComputedStyle(el); return {x:b.x,y:b.y,width:b.width,height:b.height,objectFit:c.objectFit,naturalWidth:el.naturalWidth,naturalHeight:el.naturalHeight,display:c.display}; };
  const receipt={innerWidth,innerHeight,scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,scrollHeight:document.documentElement.scrollHeight,scrollY,cover:read(cover),target:read(target),navToggle:read(document.querySelector('.nav-toggle')),formCount:document.forms.length};
  const evidence=document.createElement('script'); evidence.type='application/json'; evidence.id='review-pr283-layout'; evidence.textContent=JSON.stringify(receipt); document.body.appendChild(evidence);
},700) });
</script>"""
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
    def end_headers(self):
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; form-action 'none'; frame-src 'none'; object-src 'none'")
        super().end_headers()
    def do_POST(self):
        requests.append({"method":"POST","path":self.path})
        self.send_error(403,"Review server blocks all submissions")
    def do_GET(self):
        path=urlsplit(self.path).path
        requests.append({"method":"GET","path":path})
        if path=="/attribution.js":
            raw=(ROOT/"attribution.js").read_text()
            assert raw.count("window.METRIKA_ID = 111149105;")==1
            data=raw.replace("window.METRIKA_ID = 111149105;","window.METRIKA_ID = 0;").encode()
            self.send_response(200);self.send_header("Content-Type","text/javascript");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data);return
        if path in ["/articles/"+SLUG+".html","/articles/index.html"]:
            raw=(ROOT/path.lstrip("/")).read_text()
            assert raw.count("</body>")==1
            html=raw.replace("</body>",SCRIPT+"\n</body>")
            original=BeautifulSoup(raw,"html.parser");render=BeautifulSoup(html,"html.parser")
            assert original.find("head").get_text()==render.find("head").get_text()
            assert [p.get_text() for p in original.find("main").find_all("p")]==[p.get_text() for p in render.find("main").find_all("p")]
            data=html.encode();self.send_response(200);self.send_header("Content-Type","text/html;charset=utf-8");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data);return
        super().do_GET()
server=socketserver.TCPServer(("127.0.0.1",0),functools.partial(Handler,directory=str(ROOT)))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
port=server.server_address[1]
base="http://127.0.0.1:"+str(port)
runs=[]
start=time.monotonic()
try:
    for kind,width,height,rel in [("article",390,4200,"articles/"+SLUG+".html"),("article",1440,2400,"articles/"+SLUG+".html"),("index-card",390,1100,"articles/index.html"),("index-card",1440,1100,"articles/index.html")]:
        png=OUT/(kind+"-"+str(width)+".png")
        with tempfile.TemporaryDirectory(prefix="pr283-chrome-") as profile:
            cmd=["/usr/bin/google-chrome","--headless=new","--no-sandbox","--disable-gpu","--disable-background-networking","--disable-component-update","--disable-sync","--disable-default-apps","--no-first-run","--no-default-browser-check","--metrics-recording-only","--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1","--user-data-dir="+profile,"--force-device-scale-factor=1","--window-size="+str(width)+","+str(height),"--virtual-time-budget=2200","--screenshot="+str(png),"--dump-dom",base+"/"+rel]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=25)
        (OUT/(kind+"-"+str(width)+".stderr.log")).write_text(result.stderr)
        assert result.returncode==0 and png.exists(), "Chrome diagnostic failed; no automatic retry"
        soup=BeautifulSoup(result.stdout,"html.parser")
        marker=soup.find("script",id="review-pr283-layout")
        assert marker and marker.string, "No bounded layout receipt"
        receipt=json.loads(marker.string)
        with Image.open(png) as image: dims=image.size;image.verify()
        item={"kind":kind,"requested_width":width,"requested_height":height,"image_dimensions":dims,"png":png.name,"png_sha256":hashlib.sha256(png.read_bytes()).hexdigest(),"exit_code":result.returncode,"layout":receipt,"command":cmd}
        runs.append(item)
        assert receipt["innerWidth"]==width and receipt["scrollWidth"]==width, "Unexpected viewport or horizontal overflow; no automatic retry"
        assert receipt["cover"] and receipt["cover"]["naturalWidth"]==1672 and receipt["cover"]["naturalHeight"]==941,"Cover did not decode"
        print(json.dumps(item,ensure_ascii=False),flush=True)
finally:
    server.shutdown();server.server_close();thread.join(timeout=2)
    receipt={"frozen_input_sha":"14c5a562c93ad7f7c28aa73588d9ca2d8b35fea3","route":"existing Google Chrome CLI; not Playwright test scripts","bound_address":"127.0.0.1","port":port,"server_closed":True,"serving_copy_only_changes":["attribution.js METRIKA_ID=0","append instrumentation: layout measurement and index target scrollIntoView"],"original_head_text_and_main_paragraphs_preserved":True,"blocked_by_csp":["all connect requests","all form actions","all external scripts/images/frames"],"requests":requests,"post_requests":sum(r["method"]=="POST" for r in requests),"runs":runs,"elapsed_seconds":time.monotonic()-start,"screenshots_created":len(runs),"dependencies_installed":False}
    (OUT/"chrome-render-receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
