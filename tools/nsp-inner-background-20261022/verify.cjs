const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'../..'),OUT='/tmp/nsp-final-evidence/inner-background';fs.mkdirSync(OUT,{recursive:true});
const server=http.createServer((req,res)=>{let p=decodeURIComponent(new URL(req.url,'http://local').pathname);if(p==='/app-script.php')p='/app.js';if(p.endsWith('/'))p+='index.html';const f=path.resolve(ROOT,'.'+p);if(!f.startsWith(ROOT+'/')){res.writeHead(403);return res.end()}try{res.setHeader('Content-Type',({'.html':'text/html','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml','.webp':'image/webp','.woff2':'font/woff2'})[path.extname(f)]||'application/octet-stream');res.end(fs.readFileSync(f))}catch{res.writeHead(404);res.end()}});
(async()=>{
await new Promise(r=>server.listen(0,'127.0.0.1',r));const local='http://127.0.0.1:'+server.address().port,base=process.env.NSP_LIVE?'https://nastoronepodryadchika.ru':local;
const browser=await chromium.launch({executablePath:process.env.NSP_CHROMIUM||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});const results=[];
try{
 const pages=['katalog.html','products/p7-dogovor-podryada.html','materialy/dogovor.html','articles/index.html','articles/akt-osvidetelstvovaniya-skrytyh-rabot.html','privacy.html','diagnostika.html','kalkulyator.html','404.html'];
 for(const name of pages)for(const width of [390,1366]){
  const ctx=await browser.newContext({viewport:{width,height:900}}),p=await ctx.newPage();
  await p.route('**/*',r=>new URL(r.request().url()).origin===base&&r.request().method()==='GET'?r.continue():r.abort());
  const response=await p.goto(base+'/'+name,{waitUntil:'networkidle'});assert(response.ok());await p.evaluate(()=>document.fonts.ready);
  const metrics=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,background:getComputedStyle(document.body).backgroundImage,attachment:getComputedStyle(document.body).backgroundAttachment,oldCrane:getComputedStyle(document.body,'::before').display,assets:performance.getEntriesByType('resource').filter(x=>x.name.includes('nsp-background-documents')).map(x=>x.name)}));
  assert(!metrics.overflow,name+' '+width+' overflow');assert(metrics.background.includes('nsp-background-documents.webp'));assert.equal(metrics.oldCrane,'none');assert(metrics.attachment.split(',').every(x=>x.trim()==='scroll'));assert.equal(metrics.assets.length,1);
  await p.screenshot({path:OUT+'/'+name.replaceAll('/','_')+'-'+width+'.png'});
  if(name==='katalog.html'){await p.locator('#cart-toggle').click();const cart=p.locator('#cart-panel');assert(await cart.isVisible());assert.equal(await cart.evaluate(x=>getComputedStyle(x).backgroundImage),'none');}
  results.push({name,width,status:'PASS',...metrics});await ctx.close();
 }
 for(const width of [360,390,1280,1366,1440,1920]){
  const ctx=await browser.newContext({viewport:{width,height:900}}),p=await ctx.newPage();await p.goto(base+'/',{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);
  assert.equal(await p.evaluate(()=>performance.getEntriesByType('resource').filter(x=>x.name.includes('nsp-background-documents')).length),0,'homepage must not load interior image');
  if(!process.env.NSP_LIVE){const after=await p.screenshot();const b=await ctx.newPage();await b.route('**/brand-approved-2026.css*',r=>r.fulfill({contentType:'text/css',body:fs.readFileSync(path.join(__dirname,'before.css'))}));await b.goto(local+'/',{waitUntil:'networkidle'});await b.evaluate(()=>document.fonts.ready);assert(after.equals(await b.screenshot()),'homepage pixel change '+width);}
  results.push({name:'index.html',width,interior_image_requests:0,status:'PASS'});await ctx.close();
 }
}finally{await browser.close();server.close()}
fs.writeFileSync(OUT+'/'+(process.env.NSP_LIVE?'live':'local')+'.json',JSON.stringify({status:'PASS',results},null,2));console.log(JSON.stringify({status:'PASS',interior_cases:18,homepage_cases:6,live:!!process.env.NSP_LIVE}));
})().catch(e=>{console.error(e);server.close();process.exit(1)});
