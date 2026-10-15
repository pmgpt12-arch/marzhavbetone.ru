#!/usr/bin/env node
/**
 * Native Chromium layout and local interaction gate for the isolated "На стороне подрядчика" preview.
 * Usage: node tools/test_approved_brand_layout.cjs <static-html-root> [report.json]
 * Uses Node.js >= 22 (built-in WebSocket), Chrome/Chromium. No external packages.
 * ONLY serves local static files on 127.0.0.1; for test only, app-script.php serves app.js.
 * No payment, backend, email, webhook or buyer delivery test is performed.
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
    const filename=path.resolve(root,"."+ (urlPath==="/app-script.php" ? "/app.js" : urlPath));
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
  if(!fs.existsSync(path.join(root,"app.js")))throw Error("app.js required for functional checkout gate");
  if(!fs.existsSync(path.join(root,"attribution.js")))throw Error("attribution.js required for mobile navigation gate");
  const server=serve();
  await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
  const webPort=server.address().port;
  const chromeDir=fs.mkdtempSync(path.join(os.tmpdir(),"mb-rebrand-chrome-"));
  const chrome=spawn(process.env.CHROME_BIN||"google-chrome",[
    "--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage",
    "--remote-allow-origins=*","--remote-debugging-port=0",
    "--user-data-dir="+chromeDir,"about:blank"
  ],{stdio:"ignore"});
  const report={scope:"LOCAL_LAYOUT_AND_CART_INTERACTION_NO_BACKEND",variant:"Engineer Premium",screens:[],pass:false};
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
        condition(entry,info.innerWidth===width,"VIEWPORT_MISMATCH");
        condition(entry,info.viewport>=width-18 && info.viewport<=width,"CLIENT_VIEWPORT_OUT_OF_RANGE"); /* Desktop scrollbar consumes 15px */
        condition(entry,info.scrollWidth<=width+1,"HORIZONTAL_OVERFLOW");
        condition(entry,info.brandText?.toLowerCase()==="на стороне подрядчика","BRAND_LABEL");
        condition(entry,info.brandDisplay!=="none"&&info.brandWidth>=100,"BRAND_HIDDEN");
        condition(entry,info.bodyBg==="rgb(247, 246, 242)","APPROVED_PALETTE_MISSING");
        condition(entry,!!info.heading,"HEADING_MISSING");
        if(width===390){
          condition(entry,info.ctaDisplay==="none","MOBILE_EXTRA_CTA");
          condition(entry,info.cartDisplay!=="none","MOBILE_CART_HIDDEN");
        }

        // Functional browser gate. No payment endpoint is invoked.
        const f=await client.send("Runtime.evaluate",{
          expression:`JSON.stringify((()=>{
            const out={errors:[]},check=(ok,name)=>{if(!ok)out.errors.push(name)};
            const toggle=document.querySelector(".nav-toggle");
            const nav=document.querySelector(".topbar nav");
            if(window.innerWidth===390){
              check(!!toggle && !!nav,"MOBILE_MENU_MISSING");
              if(toggle&&nav){
                toggle.click();
                out.menuExpanded=toggle.getAttribute("aria-expanded");
                check(nav.classList.contains("is-open")&&out.menuExpanded==="true","MOBILE_MENU_OPEN");
                toggle.click();
                check(!nav.classList.contains("is-open")&&toggle.getAttribute("aria-expanded")==="false","MOBILE_MENU_CLOSE");
              }
            }
            const cartToggle=document.querySelector("#cart-toggle");
            const panel=document.querySelector("#cart-panel");
            const cartClose=document.querySelector("#cart-close");
            check(!!cartToggle&&!!panel&&!!cartClose,"CART_ELEMENTS_MISSING");
            if(cartToggle&&panel&&cartClose){
              cartToggle.click();
              check(!panel.hidden&&cartToggle.getAttribute("aria-expanded")==="true","CART_OPEN");
              cartClose.click();
              check(panel.hidden&&cartToggle.getAttribute("aria-expanded")==="false","CART_CLOSE");
            }
            const buttons=document.querySelectorAll(".add-to-cart");
            if(buttons.length && cartToggle && panel){
              const button=buttons[0],expectedPrice=Number(button.dataset.price);
              const expectedSku=button.dataset.sku;
              button.click();
              const count=document.querySelector("#cart-count");
              const cta=document.querySelector("#cart-checkout");
              const cartItems=document.querySelectorAll("#cart-items .cart-item");
              const total=document.querySelector("#cart-total")?.textContent||"";
              check(count?.textContent==="1","CART_COUNT");
              check(cartItems.length===1,"CART_ITEM");
              check(!cta?.disabled,"CHECKOUT_CTA_DISABLED");
              check(!panel.hidden,"CART_NOT_OPEN_AFTER_ADD");
              const stored=JSON.parse(localStorage.getItem("marzhavbetone-cart")||"[]");
              check(stored.length===1&&stored[0].sku===expectedSku&&stored[0].price===expectedPrice,"CART_STORAGE_OR_PRICE");
              check(total.includes(new Intl.NumberFormat("ru-RU").format(expectedPrice/100)),"CART_TOTAL");
              cta?.click();
              const modal=document.querySelector("#checkout-modal");
              check(!!modal?.classList.contains("active"),"CHECKOUT_MODAL_OPEN");
              check(!!modal?.querySelector('input[type="email"][required]'),"EMAIL_FIELD");
              check(!!modal?.querySelector('input[type="checkbox"][required]'),"CONSENT_FIELD");
              modal?.querySelector(".checkout-close")?.click();
              check(!modal?.classList.contains("active"),"CHECKOUT_MODAL_CLOSE");
              cartToggle.click();
              document.querySelector("#cart-items .cart-remove")?.click();
              check(document.querySelector("#cart-count")?.textContent==="0","CART_REMOVE");
              check(document.querySelector("#cart-checkout")?.disabled===true,"EMPTY_CART_DISABLED");
              check(JSON.parse(localStorage.getItem("marzhavbetone-cart")||"[]").length===0,"CART_CLEAR_STORAGE");
              cartClose.click();
              out.sku=expectedSku;out.priceKopecks=expectedPrice;
            }else if(!buttons.length){out.noSkuOnPage=true;}
            return out;
          })())`,
          returnByValue:true
        });
        const interaction=JSON.parse(f.result.value);
        entry.interaction=interaction;
        for(const err of interaction.errors)entry.failures.push(err);
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
