#!/usr/bin/env node
/**
 * Native Chromium layout gate for the isolated "На стороне подрядчика" preview.
 * Usage: node tools/test_approved_brand_layout.cjs <static-html-root> [report.json]
 * Uses Node.js >= 22 (built-in WebSocket), Chrome/Chromium. No external packages.
 * ONLY serves local static files on 127.0.0.1; it cannot test payment/webhooks.
 */
"use strict";
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const http=require("node:http");
const {spawn}=require("node:child_process");
const root=path.resolve(process.argv[2]||process.cwd());
const reportPath=process.argv[3]||"";
const cases=[
  {url:"/index.html",name:"home"},
  {url:"/katalog.html",name:"catalog"},
  {url:"/products/p1-oplata-po-ks2.html",name:"product-p1"}
];
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function mime(filename){
  if(filename.endsWith(".css"))return "text/css";
  if(filename.endsWith(".js"))return "text/javascript";
  if(filename.endsWith(".svg"))return "image/svg+xml";
  if(filename.endsWith(".png"))return "image/png";
  return "text/html; charset=utf-8";
}
function serve(){
  const server=http.createServer((req,res)=>{
    let urlPath;
    try{urlPath=decodeURIComponent(req.url.split("?")[0]);}catch(e){res.writeHead(400).end();return;}
    const filename=path.resolve(root,"."+urlPath);
    if(filename!==root && !filename.startsWith(root+path.sep)){res.writeHead(403).end();return;}
    fs.readFile(filename,(err,body)=>{
      if(err){res.writeHead(404).end();return;}
      res.writeHead(200,{"Content-Type":mime(filename),"Cache-Control":"no-store"});
      res.end(body);
    });
  });
  return server;
}
async function connect(port){
  let tabs=[];
  for(let attempt=0;attempt<35;attempt++){
    try{tabs=await(await fetch("http://127.0.0.1:"+port+"/json",{signal:AbortSignal.timeout(600)})).json();if(tabs.length)break;}catch(e){}
    await sleep(130);
  }
  const page=tabs.find(p=>p.type==="page");
  if(!page)throw Error("Chromium debugging endpoint unavailable");
  const ws=new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
  let nextId=0;const waiting=new Map();
  ws.onmessage=ev=>{
    const data=JSON.parse(ev.data);
    if(!waiting.has(data.id))return;
    const [resolve,reject]=waiting.get(data.id);waiting.delete(data.id);
    data.error?reject(Error(data.error.message)):resolve(data.result);
  };
  const send=(method,params={})=>new Promise((resolve,reject)=>{
    const id=++nextId;waiting.set(id,[resolve,reject]);
    ws.send(JSON.stringify({id,method,params}));
  });
  return {ws,send};
}
function condition(entry,check,message){
  if(!check)entry.failures.push(message);
}
async function main(){
  for(const c of cases){
    if(!fs.existsSync(path.join(root,c.url)))throw Error("Missing page: "+c.url);
  }
  if(!fs.existsSync(path.join(root,"brand-approved-2026.css")))throw Error("Brand CSS missing");
  const server=serve();
  await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
  const webPort=server.address().port;
  const chromeDir=fs.mkdtempSync(path.join(os.tmpdir(),"mb-rebrand-chrome-"));
  const chrome=spawn(process.env.CHROME_BIN||"google-chrome",[
    "--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage",
    "--remote-allow-origins=*","--remote-debugging-port=0",
    "--user-data-dir="+chromeDir,"about:blank"
  ],{stdio:"ignore"});
  const report={scope:"STATIC_UI_ONLY",variant:"Engineer Premium",screens:[],pass:false};
  let client;
  try{
    let debugPort=0;
    for(let attempt=0;attempt<40;attempt++){
      const file=path.join(chromeDir,"DevToolsActivePort");
      if(fs.existsSync(file)){
        debugPort=Number(fs.readFileSync(file,"utf8").split("\n")[0]);break;
      }
      await sleep(140);
    }
    if(!debugPort)throw Error("DevToolsActivePort was not created");
    client=await connect(debugPort);
    await client.send("Page.enable");
    for(const width of [390,1360]){
      await client.send("Emulation.setDeviceMetricsOverride",{
        width,height:width===390?844:900,mobile:width===390,deviceScaleFactor:1
      });
      for(const target of cases){
        await client.send("Page.navigate",{url:"http://127.0.0.1:"+webPort+target.url});
        await sleep(420);
        const v=await client.send("Runtime.evaluate",{
          expression:`JSON.stringify((()=>{
            const a=document.querySelector('.topbar .brand'),
              label=a?.querySelector('span:last-child'),rect=label?.getBoundingClientRect(),
              cta=document.querySelector('.nav-cta'),
              cart=document.querySelector('.cart-toggle');
            return {viewport:document.documentElement.clientWidth,
              innerWidth:window.innerWidth,
              scrollWidth:document.documentElement.scrollWidth,
              brandText:label?.textContent?.trim(),
              brandDisplay:label?getComputedStyle(label).display:'missing',
              brandWidth:rect?.width||0,
              cartDisplay:cart?getComputedStyle(cart).display:'missing',
              ctaDisplay:cta?getComputedStyle(cta).display:'missing',
              bodyBg:getComputedStyle(document.body).backgroundColor,
              heading:document.querySelector('h1')?.textContent?.trim().slice(0,85)};
          })())`,
          returnByValue:true
        });
        const info=JSON.parse(v.result.value);
        const entry={name:target.name,width,...info,failures:[]};
        condition(entry,info.viewport===width,"VIEWPORT_MISMATCH");
        condition(entry,info.scrollWidth<=width+1,"HORIZONTAL_OVERFLOW");
        condition(entry,info.brandText?.toLowerCase()==="на стороне подрядчика","BRAND_LABEL");
        condition(entry,info.brandDisplay!=="none"&&info.brandWidth>=100,"BRAND_HIDDEN");
        condition(entry,info.bodyBg==="rgb(247, 246, 242)","APPROVED_PALETTE_MISSING");
        condition(entry,!!info.heading,"HEADING_MISSING");
        if(width===390){
          condition(entry,info.ctaDisplay==="none","MOBILE_EXTRA_CTA");
          condition(entry,info.cartDisplay!=="none","MOBILE_CART_HIDDEN");
        }
        report.screens.push(entry);
      }
    }
    report.pass=report.screens.every(x=>x.failures.length===0);
  }finally{
    if(client?.ws)client.ws.close();
    chrome.kill("SIGTERM");
    server.close();
    await sleep(180);
    fs.rmSync(chromeDir,{recursive:true,force:true});
  }
  if(reportPath)fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+"\n");
  console.log(JSON.stringify(report,null,2));
  if(!report.pass)process.exitCode=1;
}
main().catch(e=>{console.error("UI_GATE_ERROR",e.stack||e);process.exitCode=2;});
