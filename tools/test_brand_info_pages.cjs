#!/usr/bin/env node
/* Bounded Chromium smoke test for owner-approved marketing/support pages.
 * Requires Node >=22 and local Chrome. No backend/checkout/money operations. */
"use strict";
const fs=require("fs"),os=require("os"),path=require("path"),http=require("http"),{spawn}=require("child_process");
const root=path.resolve(process.argv[2]||process.cwd());
const output=process.argv[3];
const pages=["404.html","contacts.html","diagnostika.html","kalkulyator.html","offer.html","payment-delivery.html","privacy.html","refund.html"];
const wait=ms=>new Promise(r=>setTimeout(r,ms));
function serve(){
 return http.createServer((req,res)=>{
  const loc=decodeURIComponent(req.url.split("?")[0]);
  const target=path.resolve(root,"."+loc);
  if(!target.startsWith(root+path.sep))return res.writeHead(403).end();
  fs.readFile(target,(err,data)=>{
   if(err)return res.writeHead(404).end();
   const type=target.endsWith(".css")?"text/css":target.endsWith(".js")?"text/javascript":target.endsWith(".svg")?"image/svg+xml":"text/html; charset=utf-8";
   res.writeHead(200,{"Content-Type":type,"Cache-Control":"no-store"}).end(data);
  });
 });
}
async function main(){
 const srv=serve();await new Promise(r=>srv.listen(0,"127.0.0.1",r));
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),"mb-aux-web-"));
 const chrome=spawn(process.env.CHROME_BIN||"google-chrome",["--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage","--remote-allow-origins=*","--remote-debugging-port=0","--user-data-dir="+dir,"about:blank"],{stdio:"ignore"});
 const rows=[];let socket;
 try{
  let port;
  for(let i=0;i<50;i++){
   const fp=path.join(dir,"DevToolsActivePort");
   if(fs.existsSync(fp)){port=Number(fs.readFileSync(fp,"utf-8").split("\n")[0]);break;}
   await wait(100);
  }
  if(!port)throw Error("Chrome start timeout");
  const tabs=await(await fetch("http://127.0.0.1:"+port+"/json")).json();
  socket=new WebSocket(tabs.find(t=>t.type==="page").webSocketDebuggerUrl);
  await new Promise((yes,no)=>{socket.onopen=yes;socket.onerror=no});
  const pending=new Map();let next=0;
  socket.onmessage=e=>{const d=JSON.parse(e.data);const p=pending.get(d.id);if(!p)return;pending.delete(d.id);d.error?p[1](Error(d.error.message)):p[0](d.result)};
  const send=(method,params={})=>new Promise((yes,no)=>{const id=++next;pending.set(id,[yes,no]);socket.send(JSON.stringify({id,method,params}))});
  await send("Page.enable");
  for(const width of [390,1360]){
   await send("Emulation.setDeviceMetricsOverride",{width,height:width===390?844:900,mobile:width===390,deviceScaleFactor:1});
   for(const url of pages){
    await send("Page.navigate",{url:"http://127.0.0.1:"+srv.address().port+"/"+url});
    await wait(280);
    const v=await send("Runtime.evaluate",{returnByValue:true,expression:`JSON.stringify((()=>{
      const label=document.querySelector('.topbar .brand span:last-child');
      const cart=document.querySelector('#cart-toggle');
      return {title:document.title,brand:label?.textContent?.trim(),brandVisible:!!(label?.getBoundingClientRect().width),
        bodyBg:getComputedStyle(document.body).backgroundColor,screen:window.innerWidth,clientWidth:document.documentElement.clientWidth,
        scrollWidth:document.documentElement.scrollWidth,header:!!document.querySelector('.topbar'),
        menu:!!document.querySelector('.nav-toggle'),cart:!!cart,
        canonical:document.querySelector('link[rel="canonical"]')?.getAttribute("href")||null};
    })())`});
    const data=JSON.parse(v.result.value);
    const errors=[];
    if(!data.header)errors.push("HEADER");
    if(data.brand?.toLowerCase()!=="на стороне подрядчика"||!data.brandVisible)errors.push("BRAND");
    if(data.bodyBg!=="rgb(247, 246, 242)")errors.push("PALETTE");
    if(data.screen!==width)errors.push("SCREEN");
    if(data.scrollWidth>data.clientWidth+1)errors.push("OVERFLOW");
    if(width===390&&!data.menu)errors.push("MENU");
    if(data.cart)errors.push("UNEXPECTED_CART_ON_SUPPORT_PAGE");
    rows.push({url,width,...data,errors});
   }
  }
 } finally {socket?.close();chrome.kill("SIGTERM");srv.close();await Promise.race([new Promise(r=>chrome.once("exit",r)),wait(900)]);try{if(chrome.exitCode!==null)fs.rmSync(dir,{force:true,recursive:true});}catch(e){if(e.code==="ENOTEMPTY"||e.code==="EBUSY")console.warn("CHROME_PROFILE_CLEANUP_DEFERRED",dir,e.code);else throw e;}}
 const report={scope:"STATIC_PUBLIC_INFO_PAGES",pass:rows.length===pages.length*2&&rows.every(r=>r.errors.length===0),rows};
 if(output)fs.writeFileSync(output,JSON.stringify(report,null,2)+"\n");
 console.log(JSON.stringify({pass:report.pass,count:rows.length,failed:rows.filter(r=>r.errors.length).map(r=>({url:r.url,width:r.width,errors:r.errors}))}));
 if(!report.pass)process.exitCode=1;
}
main().catch(err=>{console.error(err);process.exitCode=2});
