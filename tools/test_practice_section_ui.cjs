#!/usr/bin/env node
"use strict";
/** Browser regression for approved nav "Практика и решения" and unchanged /articles/ routes.
 * Run: node tools/test_practice_section_ui.cjs [report.json]
 * No external libraries; Node 22+ and Google Chrome; localhost only.
 */
const fs=require("node:fs"),path=require("node:path"),http=require("node:http"),
      os=require("node:os"),cp=require("node:child_process");
const ROOT=path.resolve(__dirname,"..");
const OUT=process.argv[2]||"/tmp/mb-practice-browser-qa.json";
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const MIME={".html":"text/html; charset=utf-8",".css":"text/css",".js":"text/javascript",
           ".svg":"image/svg+xml",".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".ico":"image/x-icon"};
const server=http.createServer((req,res)=>{
  const rel=decodeURIComponent((req.url||"/").split("?")[0])||"/";
  const file=path.resolve(ROOT,"."+rel);
  if(!file.startsWith(ROOT+path.sep)){res.writeHead(403).end();return;}
  fs.readFile(file,(err,data)=>{
    if(err){res.writeHead(404).end();return;}
    res.writeHead(200,{"Content-Type":MIME[path.extname(file)]||"text/plain"}).end(data);
  });
});
async function main(){
 await new Promise(r=>server.listen(0,"127.0.0.1",r));
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),"practice-nav-cdp-"));
 const chrome=cp.spawn(process.env.CHROME_BIN||"/usr/bin/google-chrome",
  ["--headless=new","--no-sandbox","--disable-dev-shm-usage","--disable-gpu",
   "--remote-allow-origins=*","--remote-debugging-port=0","--user-data-dir="+profile,"about:blank"],{stdio:"ignore"});
 let ws;
 try{
  let port=0;
  for(let i=0;i<150;i++){
   const f=path.join(profile,"DevToolsActivePort");
   if(fs.existsSync(f)){port=Number(fs.readFileSync(f,"utf8").split("\n")[0]);break;}
   await sleep(120);
  }
  if(!port)throw Error("Chrome remote debugging did not start within 18 seconds; process exit="+String(chrome.exitCode??"running"));
  const tabs=await(await fetch("http://127.0.0.1:"+port+"/json")).json();
  ws=new WebSocket(tabs.find(x=>x.type==="page").webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
  let seq=0;const inflight=new Map();
  ws.onmessage=msg=>{
   const data=JSON.parse(msg.data);
   if(inflight.has(data.id)){
    const [resolve,reject]=inflight.get(data.id);inflight.delete(data.id);
    data.error?reject(Error(data.error.message)):resolve(data.result);
   }
  };
  const call=(method,params={})=>new Promise((resolve,reject)=>{
   const id=++seq;inflight.set(id,[resolve,reject]);ws.send(JSON.stringify({id,method,params}));
  });
  await call("Page.enable");
  const rows=[];
  for(const width of [390,1024,1360,1440]){
   await call("Emulation.setDeviceMetricsOverride",{width,height:width===390?844:900,mobile:width===390,deviceScaleFactor:1});
   for(const rel of ["index.html","articles/index.html","articles/vozvrat-avansa-po-dogovoru-podryada.html"]){
    await call("Page.navigate",{url:"http://127.0.0.1:"+server.address().port+"/"+rel});
    await sleep(650);
    const value=await call("Runtime.evaluate",{expression:`JSON.stringify((()=>{
      const header=document.querySelector('.topbar');
      const nav=header?.querySelector('nav[aria-label="Основная навигация"]');
      const item=[...nav?.querySelectorAll('a')||[]].find(a=>a.getAttribute('href')==='/articles/');
      const cta=header?.querySelector('.nav-cta'),cart=header?.querySelector('.cart-toggle');
      const toggle=header?.querySelector('.nav-toggle');
      const rect=x=>x?.getBoundingClientRect();
      const visible=x=>!!x&&getComputedStyle(x).display!=='none'&&rect(x).width>0;
      let opened=null,closed=null;
      if(innerWidth===390&&toggle&&nav){
        toggle.click();opened=nav.classList.contains('is-open')&&toggle.getAttribute('aria-expanded')==='true';
        toggle.click();closed=!nav.classList.contains('is-open')&&toggle.getAttribute('aria-expanded')==='false';
      }
      return {width:innerWidth,clientWidth:document.documentElement.clientWidth,
        scrollWidth:document.documentElement.scrollWidth,
        href:item?.getAttribute('href'),label:item?.textContent.trim(),
        h1:document.querySelector('h1')?.textContent.trim(),
        title:document.title,
        navbarVisible:visible(nav),menuVisible:visible(toggle),opened,closed,
        navRight:rect(nav)?.right||0,ctaLeft:rect(cta)?.left||0,
        ctaVisible:visible(cta),cartVisible:visible(cart),
        breadcrumb:[...document.querySelectorAll('.breadcrumbs li')].map(e=>e.textContent.trim()),
        outliers:[...document.querySelectorAll('body *')].map(e=>{const r=e.getBoundingClientRect();return {tag:e.tagName,cls:String(e.className).slice(0,90),x:Math.round(r.x),right:Math.round(r.right),width:Math.round(r.width)};}).filter(e=>e.right>document.documentElement.clientWidth+1).sort((a,b)=>b.right-a.right).slice(0,12),
        jsonLdSection:document.querySelector('script[type="application/ld+json"]')?.textContent.includes('"name": "Практика и решения"')||false};
    })())`,returnByValue:true});
    const d=JSON.parse(value.result.value);
    const errors=[];
    if(d.width!==width)errors.push("VIEWPORT");
    if(d.scrollWidth>width+1)errors.push("HORIZONTAL_OVERFLOW");
    if(d.href!=="/articles/"||d.label!=="Практика и решения")errors.push("NAV_LABEL_OR_ROUTE");
    if(width===390){
      if(!d.menuVisible||!d.opened||!d.closed)errors.push("MOBILE_MENU");
    }else if(d.navbarVisible&&d.ctaVisible&&d.navRight>d.ctaLeft-1){
      errors.push("DESKTOP_NAV_CTA_OVERLAP");
    }
    if(rel==="articles/index.html"){
      if(d.h1!=="Практика: договоры, приёмка, оплата и споры")errors.push("HUB_H1");
      if(!d.title.includes("Практика и решения"))errors.push("HUB_TITLE");
      if(!d.breadcrumb.includes("Практика и решения")||!d.jsonLdSection)errors.push("HUB_SCHEMA_BREADCRUMB");
    }else if(rel.startsWith("articles/")&&!d.jsonLdSection)errors.push("ARTICLE_SCHEMA_BREADCRUMB");
    rows.push({path:rel,width,errors,...d});
    if(width===390||width===1360){
      if(rel==="articles/index.html"){
        const image=await call("Page.captureScreenshot",{format:"png"});
        fs.writeFileSync("/tmp/mb-practice-hub-"+width+".png",Buffer.from(image.data,"base64"));
      }
    }
   }
  }
  const result={gate:"PRACTICE_SECTION_BROWSER",scope:"NONCOMMERCE_NATIVE_UI",
                status:rows.every(r=>r.errors.length===0)?"PASS":"FAIL",pass:rows.every(r=>r.errors.length===0),rows};
  fs.writeFileSync(OUT,JSON.stringify(result,null,2)+"\n");
  console.log(JSON.stringify({pass:result.pass,checked:rows.length,issues:rows.filter(r=>r.errors.length>0).map(r=>({path:r.path,width:r.width,errors:r.errors,navRight:r.navRight,ctaLeft:r.ctaLeft}))},null,2));
  if(!result.pass)process.exitCode=1;
 }finally{
  ws?.close();chrome.kill("SIGTERM");server.close();
  await sleep(350);
  try{fs.rmSync(profile,{recursive:true,force:true,maxRetries:3,retryDelay:180});}
  catch(error){if(error.code!=="ENOTEMPTY"&&error.code!=="EBUSY")throw error;
    console.warn("CHROME_TEMP_CLEANUP_DEFERRED",error.code);}
 }
}
main().catch(e=>{server.close();console.error("BROWSER_QA_ERROR",e.stack||e);process.exitCode=2});
