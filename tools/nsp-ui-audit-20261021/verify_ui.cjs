const {chromium}=require('playwright');
const AxeBuilder=require('@axe-core/playwright').default;
const fs=require('fs');const assert=require('node:assert/strict');const path=require('node:path');const http=require('node:http');
const ROOT=path.resolve(__dirname,'../..');const OUT=process.env.NSP_TEST_OUTPUT||'/tmp/nsp-ui-evidence';fs.mkdirSync(OUT,{recursive:true});
const server=http.createServer((req,res)=>{let p=decodeURIComponent(new URL(req.url,'http://local').pathname);if(p==='/app-script.php')p='/app.js';if(p.endsWith('/'))p+='index.html';let file=path.resolve(ROOT,'.'+p);if(!file.startsWith(ROOT+path.sep)||p.endsWith('.php')){res.writeHead(404);return res.end();}try{const types={'.js':'text/javascript','.css':'text/css','.html':'text/html','.svg':'image/svg+xml'};res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));}catch{res.writeHead(404);res.end();}});
(async()=>{
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const BASE=process.env.NSP_LIVE==='1'?'https://nastoronepodryadchika.ru':'http://127.0.0.1:'+server.address().port;
const proxyValue=process.env.NSP_LIVE==='1'&&(process.env.HTTPS_PROXY||process.env.HTTP_PROXY);const proxy=proxyValue?new URL(proxyValue):null;
const browser=await chromium.launch({executablePath:process.env.NSP_CHROMIUM||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox'],...(proxy?{proxy:{server:proxy.origin,...(proxy.username?{username:decodeURIComponent(proxy.username),password:decodeURIComponent(proxy.password)}:{})}}:{})});
let results=[];
for(const width of process.env.NSP_ONLY==='checkout'?[]:process.env.NSP_LIVE==='1'?[390,1366]:[360,375,390,414,768,1366,1920]){
 const context=await browser.newContext({viewport:{width,height:900}});const page=await context.newPage();await page.route('**/*',route=>new URL(route.request().url()).hostname===new URL(BASE).hostname?route.continue():route.abort());
 for(const path of ['/','/products/p7-dogovor-podryada.html','/katalog.html','/kalkulyator.html','/diagnostika.html']){
  await page.goto(BASE+path,{waitUntil:'networkidle'});
  const overflow=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,offenders:[...document.querySelectorAll('body *')].filter(e=>{let b=e.getBoundingClientRect();return b.width>0&&(b.right>innerWidth+1||b.left< -1)&&getComputedStyle(e).position!=='fixed'}).slice(0,10).map(e=>({tag:e.tagName,cls:e.className,x:e.getBoundingClientRect().x,w:e.getBoundingClientRect().width}))}));
  const row={width,path,...overflow};assert(overflow.scroll<=width,'OVERFLOW '+path+' '+width);
  if((width===390||width===1366)){
   const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();row.axe=axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,data:n.any[0]?.data}))}));
   if(path==='/')await page.screenshot({path:OUT+'/home-'+width+'.png',fullPage:false});
  }results.push(row);
 }
 await context.close();
}
fs.writeFileSync(OUT+'/layout.json',JSON.stringify(results,null,2));assert(results.every(r=>!r.axe?.length),'AXE_VIOLATIONS: '+JSON.stringify(results.filter(r=>r.axe?.length)));

const checkout=[];

for(const width of [360,390,768,1366]){
 const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage();let payload;
 await page.route('**/*',async route=>{let u=new URL(route.request().url());if(u.pathname==='/payment.php'){payload=route.request().postDataJSON();return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:false,message:'Контрольный ответ без платежа'})});}return u.hostname===new URL(BASE).hostname?route.continue():route.abort();});
 await page.goto(BASE+'/products/p7-dogovor-podryada.html',{waitUntil:'networkidle'});
 await page.locator('button[data-sku="p7"]').first().click();
 if(width===390){await page.goto(BASE+'/products/p2-dopolnitelnye-raboty.html',{waitUntil:'networkidle'});await page.locator('button[data-sku="p2"]').first().click();}
 if(!await page.locator('#cart-panel').isVisible())await page.locator('#cart-toggle').click();
 await page.locator('#cart-checkout').click();await page.locator('#checkout-modal').waitFor({state:'visible'});
 assert.equal(await page.evaluate(()=>document.activeElement.name),'email');
 assert.equal(await page.locator('[name=phone]').getAttribute('required'),null);assert.equal(await page.locator('#checkout-modal input[type=checkbox]').count(),1);assert.equal(await page.locator('#checkout-modal [name=consent]').isChecked(),false);
 const escaped=[];for(let i=0;i<12;i++){await page.keyboard.press('Tab');escaped.push(await page.evaluate(()=>document.getElementById('checkout-modal').contains(document.activeElement)));}assert(escaped.every(Boolean),'TAB_ESCAPE');
 for(let i=0;i<12;i++){await page.keyboard.press('Shift+Tab');assert(await page.evaluate(()=>document.getElementById('checkout-modal').contains(document.activeElement)),'SHIFT_TAB_ESCAPE');}
 await page.locator('#checkout-modal [name=email]').fill('qa@example.invalid');await page.locator('#checkout-modal [name=consent]').check();await page.locator('.checkout-submit').click();await page.locator('#checkout-error').filter({hasText:'Контрольный'}).waitFor();assert(payload.email==='qa@example.invalid'&&payload.phone===''&&payload.items[0].sku==='p7');if(width===390)assert.equal(payload.items.length,2);
 const geometry=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,modalClient:document.querySelector('#checkout-modal').clientWidth,modalScroll:document.querySelector('#checkout-modal').scrollWidth,nowrap:getComputedStyle(document.querySelector('.checkout-item>span')).whiteSpace}));assert(geometry.scroll<=width&&geometry.modalScroll<=geometry.modalClient&&geometry.nowrap==='nowrap');
 if(width===390){const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();checkout.push({width,geometry,axe:axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,data:n.any[0]?.data}))}))});await page.screenshot({path:OUT+'/checkout-390.png'});}else checkout.push({width,geometry});
 await page.keyboard.press('Escape');await page.waitForFunction(()=>document.activeElement.id==='cart-checkout');assert(!await page.locator('#checkout-modal').isVisible());
 await page.locator('#cart-checkout').click();await page.locator('.checkout-close').click();assert(!await page.locator('#checkout-modal').isVisible());await context.close();
}

assert(checkout.every(r=>!r.axe?.length),'CHECKOUT_AXE');
fs.writeFileSync(OUT+'/checkout.json',JSON.stringify(checkout,null,2));

const calc=await browser.newPage();await calc.route('**/*',r=>new URL(r.request().url()).hostname===new URL(BASE).hostname?r.continue():r.abort());await calc.goto(BASE+'/kalkulyator.html');
assert.equal(await calc.locator('#debt-result').textContent(),'Укажите ставку');
for(const [value,expected] of [['10','69'],['0','0'],['-1','Ставка'],['101','Ставка']]){await calc.locator('#key-rate').fill(value);assert((await calc.locator('#debt-result').textContent()).startsWith(expected));}
await calc.locator('#key-rate').fill('10');assert.equal((await calc.locator('#debt-result').textContent()).replace(/[^0-9]/g,''),'69041');
await calc.locator('#debt-sum').fill('-1');assert((await calc.locator('#debt-result').textContent()).includes('вне диапазона'));
await calc.locator('#debt-sum').fill('10000000000000');assert((await calc.locator('#debt-result').textContent()).includes('вне диапазона'));
await calc.locator('#debt-sum').fill('0');assert.equal((await calc.locator('#debt-result').textContent()).replace(/[^0-9]/g,''),'0');
await calc.locator('#retention-tab').click();
assert.equal((await calc.locator('#retention-result').textContent()).replace(/[^0-9]/g,''),'900000');
await calc.locator('#money-rate').fill('');assert.equal(await calc.locator('#retention-result').textContent(),'Укажите ставку');
await calc.locator('#money-rate').fill('18.5');assert.equal((await calc.locator('#retention-result').textContent()).replace(/[^0-9]/g,''),'925000');
await calc.locator('#planned-profit').fill('0');assert((await calc.locator('#retention-share').textContent()).startsWith('Без учёта'));
await calc.close();
fs.writeFileSync(OUT+'/summary.json',JSON.stringify({status:'PASS',base_url:BASE,date:new Date().toISOString(),browser:browser.version(),layout_cases:results.length,axe_cases:results.filter(r=>r.axe).length,checkout_cases:checkout.length,calculator:'empty/zero/synthetic10/negative/huge PASS',payment_requests:'MOCKED',real_payments:0,emails_sent:0},null,2));
console.log(fs.readFileSync(OUT+'/summary.json','utf8'));await browser.close();server.close();

})().catch(e=>{console.error(e);server.close();process.exit(1)});
