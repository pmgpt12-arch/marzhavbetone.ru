#!/usr/bin/env node
/** Browser gate for ALL tracked brand pages, not just first-wave samples.
 * Bounded chunks: node tools/test_approved_brand_all_pages.cjs . 390 0 22 /tmp/report.json
 * Requires Node >=22 and Chrome; localhost-only. Never posts/charges money.
 */
"use strict";
const fs=require("node:fs"),os=require("node:os"),path=require("node:path"),
      http=require("node:http"),{spawn,spawnSync}=require("node:child_process");
const root=path.resolve(process.argv[2]||process.cwd());
const width=Number(process.argv[3]||390),offset=Number(process.argv[4]||0),
      limit=Number(process.argv[5]||22),dest=process.argv[6]||"";
if(![390,1360].includes(width)||!Number.isInteger(offset)||!Number.isInteger(limit)||limit<1||limit>30)
  throw Error("width=390|1360, offset integer >=0, 1<=limit<=30");
const all=spawnSync("git",["ls-files","--","*.html"],{cwd:root,encoding:"utf8",timeout:8000});
if(all.status!==0)throw Error("Unable to enumerate tracked HTML: "+all.stderr);
const paths=all.stdout.split("\n").filter(Boolean).sort();
const pages=paths.slice(offset,offset+limit);
if(!pages.length)throw Error("Invalid offset; no pages selected");
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function mime(p){
 if(p.endsWith(".css"))return "text/css";if(p.endsWith(".js")||p.endsWith(".php"))return "text/javascript";
 if(p.endsWith(".png"))return "image/png";if(p.endsWith(".jpg")||p.endsWith(".jpeg"))return "image/jpeg";
 if(p.endsWith(".svg"))return "image/svg+xml";return "text/html; charset=utf-8";
}
async function main(){
 const server=http.createServer((req,res)=>{
  let relative;try{relative=decodeURIComponent(req.url.split("?")[0]);}catch(e){res.writeHead(400).end();return;}
  if(relative==="/app-script.php")relative="/app.js";
  const target=path.resolve(root,"."+relative);
  if(!target.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  fs.readFile(target,(err,data)=>{
    if(err){res.writeHead(404).end();return;}
    res.writeHead(200,{"Content-Type":mime(target),"Cache-Control":"no-store"}).end(data);
  });
 });
 await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),"mb-all-pages-"));
 const browser=spawn(process.env.CHROME_BIN||"google-chrome",[
  "--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage",
  "--remote-allow-origins=*","--remote-debugging-port=0","--user-data-dir="+dir,"about:blank"
 ],{stdio:"ignore"});
 const rows=[];let ws;
 try{
  let port=0;
  for(let i=0;i<50;i++){
   const f=path.join(dir,"DevToolsActivePort");
   if(fs.existsSync(f)){port=Number(fs.readFileSync(f,"utf8").split("\n")[0]);break;}await sleep(100);
  }
  if(!port)throw Error("Chrome debug listener unavailable");
  const tabs=await(await fetch("http://127.0.0.1:"+port+"/json")).json();
  ws=new WebSocket(tabs.find(p=>p.type==="page").webSocketDebuggerUrl);
  await new Promise((yes,no)=>{ws.onopen=yes;ws.onerror=no});
  let n=0;const inflight=new Map();
  ws.onmessage=e=>{const msg=JSON.parse(e.data),p=inflight.get(msg.id);if(!p)return;inflight.delete(msg.id);msg.error?p[1](Error(msg.error.message)):p[0](msg.result)};
  const call=(method,params={})=>new Promise((yes,no)=>{const id=++n;inflight.set(id,[yes,no]);ws.send(JSON.stringify({id,method,params}))});
  await call("Page.enable");
  await call("Emulation.setDeviceMetricsOverride",{width,height:width===390?844:900,deviceScaleFactor:1,mobile:width===390});
  for(const name of pages){
   await call("Page.navigate",{url:"http://127.0.0.1:"+server.address().port+"/"+name});
   let data=null;
   for(let i=0;i<10;i++){
    await sleep(55);
    const val=await call("Runtime.evaluate",{returnByValue:true,expression:`JSON.stringify((()=>{
      const label=document.querySelector('.topbar .brand span:last-child, .result-page .brand span:last-child');
      const br=label?.getBoundingClientRect(),doc=document.documentElement;
      const header=document.querySelector('.topbar');
      const menu=document.querySelector('.nav-toggle');
      return {
       ready:document.readyState,title:document.title,
       h1:!!document.querySelector('h1'),
       bodyClass:document.body?.className||'',
       bodyColor:document.body?getComputedStyle(document.body).backgroundColor:'',
       brand:label?.textContent?.trim()||'',brandWidth:br?.width||0,
       outerWidth:window.innerWidth,clientWidth:doc.clientWidth,scrollWidth:doc.scrollWidth,
       header:!!header,hasMobileMenu:!!menu
      };
     })())`});
    if(val.result?.value){data=JSON.parse(val.result.value);if(data.ready!=="loading"&&data.brand)break;}
   }
   const errs=[];
   if(!data)errs.push("NO_DOCUMENT");
   else {
    if(data.outerWidth!==width)errs.push("VIEWPORT_MISMATCH");
    if(!data.bodyClass.split(/\s+/).includes("rebrand-approved"))errs.push("BODY_CLASS");
    if(data.bodyColor!=="rgb(247, 246, 242)")errs.push("PALETTE");
    if(data.brand.toLowerCase()!=="на стороне подрядчика"||data.brandWidth<90)errs.push("BRAND_HIDDEN");
    if(data.scrollWidth>data.clientWidth+1)errs.push("HORIZONTAL_OVERFLOW");
    if(!data.h1)errs.push("H1_MISSING");
    if(width===390&&data.header&&!data.hasMobileMenu)errs.push("MENU_MISSING");
   }
   if(errs.includes("HORIZONTAL_OVERFLOW")){
    const diag=await call("Runtime.evaluate",{returnByValue:true,expression:`JSON.stringify([...document.querySelectorAll("*")].map(e=>{
      const r=e.getBoundingClientRect();
      return {tag:e.tagName,cl:String(e.className).slice(0,70),x:Math.round(r.x),right:Math.round(r.right),width:Math.round(r.width)};
    }).filter(e=>e.right>document.documentElement.clientWidth+1||e.x< -1).sort((a,b)=>b.right-a.right).slice(0,12))`});
    if(diag.result?.value)data.overflowElements=JSON.parse(diag.result.value);
   }
   rows.push({name,width,...data,errors:errs});
  }
 }finally{
  ws?.close();browser.kill("SIGTERM");server.close();
  await Promise.race([new Promise(r=>browser.once("exit",r)),sleep(900)]);
  try{if(browser.exitCode!==null)fs.rmSync(dir,{recursive:true,force:true});}
  catch(e){if(!["ENOTEMPTY","EBUSY"].includes(e.code))throw e;}
 }
 const report={scope:"LOCAL_ALL_BRANDED_STATIC_HTML",totalTracked:paths.length,offset,limit,actual:rows.length,width,pass:rows.length===pages.length&&rows.every(r=>!r.errors.length),rows};
 if(dest)fs.writeFileSync(dest,JSON.stringify(report,null,2)+"\n");
 console.log(JSON.stringify({width,totalTracked:paths.length,offset,actual:rows.length,pass:report.pass,failures:rows.filter(r=>r.errors.length).map(r=>({name:r.name,errors:r.errors}))}));
 if(!report.pass)process.exitCode=1;
}
main().catch(e=>{console.error("CHROMIUM_GATE_FAILURE",e.message);process.exitCode=2;});
