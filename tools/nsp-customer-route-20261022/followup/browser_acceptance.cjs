// Bounded native-PHP/browser checks; external traffic and payment POSTs blocked.
const {chromium}=require('playwright');
const fs=require('fs'),os=require('os'),path=require('path'),crypto=require('crypto');
const assert=require('node:assert/strict'),{spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'../../..'),OUT=__dirname;
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'nsp-route-followup-'));
const origin='http://127.0.0.1:8196',rows=[];
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
async function check(id,viewport,fn){try{rows.push({id,viewport,status:'PASS',actual:await fn()});}catch(e){rows.push({id,viewport,status:'FAIL',error:e.message});}}
async function ready(url){for(let i=0;i<30;i++){try{await fetch(url);return;}catch{await new Promise(r=>setTimeout(r,50));}}throw Error('server startup failed');}
(async()=>{
 const php=spawn(process.env.ROUTE_PHP||'php',['-d','sendmail_path=/bin/false','-S','127.0.0.1:8196','-t',ROOT],{stdio:'ignore',env:{...process.env,MVB_FUNNEL_OUTBOX:path.join(tmp,'outbox')}});
 const before=spawn('python3',[path.join(ROOT,'tools/nsp-customer-route-20261022/staging_server.py'),process.env.ROUTE_BEFORE,'8197'],{stdio:'ignore'});
 let browser;
 try{
  await Promise.all([ready(origin+'/index.html'),ready('http://127.0.0.1:8197/index.html')]);
  browser=await chromium.launch({executablePath:process.env.ROUTE_CHROMIUM,headless:true,args:['--no-sandbox','--disable-gpu']});
  for(const [label,viewport] of [['desktop',{width:1366,height:850}],['mobile',{width:390,height:844}]]){
   const context=await browser.newContext({viewport,acceptDownloads:true});
   let paymentPosts=0,status='pending';
   await context.addInitScript(()=>{window.qaGoals=[];window.ym=(id,type,name,params)=>{if(type==='reachGoal')window.qaGoals.push({name,params});};});
   await context.route('**/*',async r=>{
    const u=new URL(r.request().url());
    if(![origin,'http://127.0.0.1:8197'].includes(u.origin))return r.fulfill({status:204,body:''});
    if(u.pathname==='/payment.php'){
     paymentPosts++;await new Promise(r=>setTimeout(r,150));
     return r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({ok:false,message:'Synthetic payment failure'})});
    }
    if(u.pathname==='/check-payment.php')return r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,order:{status,items:[{sku:'p8',name:'Synthetic',price:2490000}],total:2490000}})});
    if(r.request().method()!=='GET'&&u.pathname!=='/lead.php')return r.fulfill({status:204,body:''});
    return r.continue();
   });
   const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
   await check('HOME-UNCHANGED-HERO',label,async()=>{
    const geometry=[];const pixels=[];
    for(const base of ['http://127.0.0.1:8197',origin]){
     await page.goto(base+'/index.html');await page.evaluate(()=>document.fonts.ready);
     geometry.push(await page.evaluate(()=>['.hero','#home-title','.hero-actions','.stage-solutions','#situations'].map(s=>{const e=document.querySelector(s),r=e.getBoundingClientRect(),c=getComputedStyle(e);return {s,x:r.x,y:r.y,width:r.width,height:r.height,font:c.font};})));
     const screenshot=await page.screenshot({animations:'disabled'});pixels.push(sha(screenshot));
     if(process.env.ROUTE_SCREEN_DIR){fs.mkdirSync(process.env.ROUTE_SCREEN_DIR,{recursive:true});fs.writeFileSync(path.join(process.env.ROUTE_SCREEN_DIR,label+'-'+(base===origin?'after':'before')+'.png'),screenshot);}
    }
    assert.deepEqual(geometry[0],geometry[1]);assert.equal(pixels[0],pixels[1]);
    return {geometry:geometry[1],viewport_pixel_sha256:pixels[1]};
   });
   await check('HOME-FORM-CONTRACT',label,async()=>{
    const f=page.locator('#lead-form'),email=f.locator('[name=contact]'),extra=f.locator('[name=additional_contact]');
    assert.equal(await email.getAttribute('type'),'email');assert.equal(await email.getAttribute('required'),'');assert.equal(await extra.getAttribute('required'),null);
    const e=await email.boundingBox(),x=await extra.boundingBox();assert.ok(x.y>=e.y+e.height);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await f.locator('[name=name]').fill('Synthetic QA');await email.fill('@synthetic');await f.locator('[name=consent]').check();
    assert.equal(await f.evaluate(f=>f.checkValidity()),false);
    return {email:e,optional_contact:x,invalid_email_rejected:true};
   });
   await check('HOME-NATIVE-LEAD-AND-PDF',label,async()=>{
    const f=page.locator('#lead-form');await f.locator('[name=contact]').fill('route-qa@example.invalid');
    await f.locator('[name=additional_contact]').fill('@synthetic');
    let posts=0;const listener=r=>{if(r.method()==='POST'&&r.url().endsWith('/lead.php'))posts++;};page.on('request',listener);
    await f.evaluate(f=>{f.dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}));f.dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}));});
    await page.locator('[data-download-link]').waitFor();assert.equal(posts,1);page.off('request',listener);
    const link=page.locator('[data-download-link]');assert.ok((await link.getAttribute('href')).endsWith('/downloads/checklist-zakrytiya-rabot.pdf'));
    const download=page.waitForEvent('download');await link.click();const d=await download;const bytes=fs.readFileSync(await d.path());
    assert.equal(sha(bytes),sha(fs.readFileSync(path.join(ROOT,'downloads/checklist-zakrytiya-rabot.pdf'))));assert.ok(bytes.subarray(0,5).equals(Buffer.from('%PDF-')));
    await link.dispatchEvent('click');
    const goals=await page.evaluate(()=>window.qaGoals.filter(g=>['lead_submit','lead_ready','download_click'].includes(g.name)));
    assert.deepEqual(goals.map(g=>g.name),['lead_submit','lead_ready','download_click']);
    assert.ok(!JSON.stringify(goals).includes('example.invalid'));assert.ok(!JSON.stringify(goals).includes('@synthetic'));
    return {native_php:true,mail_transport:'disabled',posts,bytes:bytes.length,sha256:sha(bytes),goals,download_served_event:'ABSENT'};
   });
   await check('CHECKOUT-DOUBLE-SUBMIT',label,async()=>{
    await page.goto(origin+'/products/p8-avans-po-dogovoru-subpodryada.html');await page.locator('.add-to-cart').first().click();await page.keyboard.press('Escape');await page.locator('.add-to-cart').first().click();
    assert.equal(await page.locator('#cart-count').innerText(),'1');await page.locator('#cart-checkout').click();
    const f=page.locator('#checkout-form');await f.locator('[name=email]').fill('route-qa@example.invalid');await f.locator('[name=consent]').check();
    await f.evaluate(f=>{f.dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}));f.dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}));});
    await page.getByText('Synthetic payment failure',{exact:true}).waitFor();assert.equal(paymentPosts,1);
    assert.equal((await page.evaluate(()=>window.qaGoals)).filter(g=>g.name==='add_to_cart').length,1);
    await f.locator('button[type=submit]').click();await page.getByText('Synthetic payment failure',{exact:true}).waitFor();assert.equal(paymentPosts,2);
    return {posts_for_double_submit:1,retry_after_failure:true,add_to_cart:1,external_payments:0};
   });
   await check('PURCHASE-PENDING-IS-NOT-SALE',label,async()=>{
    await page.goto(origin+'/success.html?order=synthetic_'+label+'&k=synthetic');await page.locator('#pending-content').waitFor({state:'visible'});
    assert.equal((await page.evaluate(()=>window.qaGoals)).filter(g=>g.name==='purchase').length,0);return {purchase:0};
   });
   await check('PURCHASE-PAID-RELOAD-DEDUPE',label,async()=>{
    status='paid';await page.reload();await page.locator('#success-content').waitFor({state:'visible'});
    const first=await page.evaluate(()=>({goals:window.qaGoals.filter(g=>g.name==='purchase'),ecommerce:window.dataLayer.filter(x=>x.ecommerce?.purchase)}));
    assert.equal(first.goals.length,1);assert.equal(first.ecommerce.length,1);assert.equal(first.goals[0].params.revenue,24900);
    await page.reload();await page.locator('#success-content').waitFor({state:'visible'});
    const repeat=await page.evaluate(()=>({goals:window.qaGoals.filter(g=>g.name==='purchase').length,ecommerce:window.dataLayer.filter(x=>x.ecommerce?.purchase).length}));assert.deepEqual(repeat,{goals:0,ecommerce:0});
    return {paid_status:'synthetic API response',first_purchase:1,first_ecommerce:1,repeat};
   });
   await check('NO-JS-ERRORS',label,async()=>{assert.deepEqual(errors,[]);return {errors};});
   await context.close();
  }
  await check('NATIVE-LEAD-OUTBOX','server',async()=>{
   const files=fs.readdirSync(path.join(tmp,'outbox')).filter(f=>f.endsWith('.jsonl'));
   const events=files.flatMap(f=>fs.readFileSync(path.join(tmp,'outbox',f),'utf8').trim().split('\n').filter(Boolean).map(JSON.parse));
   const delivered=events.filter(e=>e.event_type==='funnel.magnet_delivered');assert.equal(delivered.length,2);
   assert.ok(!JSON.stringify(events).includes('example.invalid'));assert.ok(!JSON.stringify(events).includes('@synthetic'));
   return {events:events.length,magnet_delivered:2,meaning:'link issued; not downloaded'};
  });
 }finally{
  if(browser)await browser.close();php.kill();before.kill();fs.rmSync(tmp,{recursive:true,force:true});
  fs.writeFileSync(path.join(OUT,'BROWSER_ACCEPTANCE.json'),JSON.stringify({scope:'isolated staging; no external payment or analytics',rows},null,2)+'\n');
 }
 console.log(JSON.stringify({pass:rows.filter(r=>r.status==='PASS').length,fail:rows.filter(r=>r.status==='FAIL')},null,2));
 if(rows.some(r=>r.status==='FAIL'))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
