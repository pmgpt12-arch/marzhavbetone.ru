// Real Chromium tests. All outbound traffic and all non-local writes are blocked.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),{spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'../..'), OUT=__dirname;
const results=[],network=[],errors=[];
const port=8092, origin=`http://127.0.0.1:${port}`;
const pages={home:'index.html',diagnostic:'diagnostika.html',money:'materialy/dengi.html',bankrupt:'materialy/bankrotstvo.html',advance:'materialy/avans.html',t2:'products/t2-peredacha-ispolnitelnoy-dokumentacii.html',p11:'products/p11-raschet-metrami.html',p3:'products/p3-shablony-ks2-ks3.html',p8:'products/p8-avans-po-dogovoru-subpodryada.html',catalog:'katalog.html',success:'success.html'};
async function test(id,label,fn){try{const actual=await fn();results.push({id,viewport:label,status:'PASS',actual});}catch(e){results.push({id,viewport:label,status:'FAIL',error:e.message});}}
(async()=>{
 const server=process.env.ROUTE_PHP
  ? spawn(process.env.ROUTE_PHP,['-S',`127.0.0.1:${port}`,'-t',ROOT],{stdio:'ignore'})
  : spawn('python3',[path.join(OUT,'staging_server.py'),ROOT,String(port)],{stdio:'ignore'});
 let browser;
 try{
  await new Promise(r=>setTimeout(r,400));
  browser=await chromium.launch({executablePath:process.env.ROUTE_CHROMIUM,headless:true,args:['--no-sandbox','--disable-gpu','--use-gl=angle','--use-angle=swiftshader']});
  for(const [label,viewport] of [['desktop',{width:1366,height:850}],['mobile',{width:390,height:844}]]){
   const context=await browser.newContext({viewport});
   let leadMode='success',leadPosts=[],paymentPosts=0;
   await context.route('**/*',async r=>{
    const req=r.request(),url=new URL(req.url());
    if(url.origin!==origin){network.push({method:req.method(),host:url.host,disposition:'external_blocked'});return r.fulfill({status:204,body:''});}
    if(req.method()==='POST'){
     if(url.pathname==='/lead.php'){
      leadPosts.push(req.postData());
      await new Promise(resolve=>setTimeout(resolve,60));
      return r.fulfill({status:leadMode==='error'?422:200,contentType:'application/json',body:JSON.stringify(leadMode==='error'?{ok:false,message:'Проверочная ошибка'}:{ok:true,download:leadMode==='unsafe'?'https://example.com/file.zip':'/downloads/dengi.zip',label:'Скачать проверочный материал'})});
     }
     if(url.pathname==='/payment.php')paymentPosts++;
     network.push({method:'POST',path:url.pathname,disposition:'blocked'});return r.fulfill({status:405,body:'blocked'});
    }
    if(url.pathname==='/check-payment.php')return r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,order:{status:'pending',items:[],total:0}})});
    if(url.pathname==='/downloads/dengi.zip')return r.fulfill({status:200,contentType:'application/zip',body:'synthetic fixture; not a buyer archive'});
    return r.continue();
   });
   const page=await context.newPage();page.on('pageerror',e=>errors.push({viewport:label,error:e.message}));
   const screens=path.join(OUT,'screens/after');fs.mkdirSync(screens,{recursive:true});
   async function go(id){await page.goto(origin+'/'+pages[id]);}
   async function shot(id,fullPage=true){await page.screenshot({path:path.join(screens,`${id}-${label}.png`),fullPage});const dom=path.join(OUT,'dom/after');fs.mkdirSync(dom,{recursive:true});fs.writeFileSync(path.join(dom,`${id}-${label}.html`),await page.content());return `screens/after/${id}-${label}.png`;}
   for(const id of Object.keys(pages)){
    await test('RENDER-'+id,label,async()=>{
     await go(id);assert.ok(await page.title());
     assert.ok(await page.locator('link[rel=canonical]').count());
     const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert.equal(overflow,false,id+' horizontal overflow');
     const screenshot=await shot(id);
     if(id==='p11'){const text=await page.locator('.kit-preview').innerText();assert.ok(!/<\/?w:|w:pPr|&lt;w:/.test(text));await page.locator('.kit-preview').screenshot({path:path.join(screens,`p11-preview-${label}.png`)});}
     return {screenshot};
    });
   }
   for(const [id,answers,expected] of [
    ['D01',{bankrot:'yes',procedure:'none'},'Есть признаки риска'],
    ['D02',{bankrot:'yes',procedure:'observation',publication:'yes',claim:'registry'},'Введено наблюдение: реестровое требование'],
    ['D03',{bankrot:'yes',procedure:'observation',publication:'yes',claim:'current'},'Введено наблюдение: текущий платёж'],
    ['D04',{bankrot:'yes',procedure:'unknown'},'Требуется уточнить'],
    ['D04-DATE',{bankrot:'yes',procedure:'observation',publication:'no'},'Требуется проверить даты'],
    ['D04-CLAIM',{bankrot:'yes',procedure:'other',publication:'yes',claim:'unknown'},'Требуется определить характер'],
    ['D04-ACCEPTED',{bankrot:'yes',procedure:'accepted'},'Заявление принято'],
    ['D05',{bankrot:'no'},null]
   ]){
    await test(id,label,async()=>{
     await go('diagnostic');for(const [q,a]of Object.entries(answers))await page.locator(`[data-q="${q}"] [data-a="${a}"]`).click();
     if(expected){assert.ok((await page.locator('#dresult').innerText()).includes(expected));assert.ok(await page.locator('#dresult a[href*="p9-"]').count());}
     else assert.ok(await page.locator('[data-q="signed"]').isVisible());
     return {answers,screenshot:await shot(id)};
    });
   }
   // Exhaust every branch through the actual live decision functions in Chromium.
   await test('D-ALL',label,async()=>{
    await go('diagnostic');const enumeration=await page.evaluate(()=>{
     let leaves=0,max=0;function walk(){max=Math.max(max,order.length);const hit=match(),next=nextUnanswered();if(hit||!next){leaves++;return;}
      const q=next.dataset.q;for(const button of next.querySelectorAll('[data-a]')){const a=button.dataset.a;answers[q]=a==='yes'?true:a==='no'?false:a;order.push(q);walk();order.pop();delete answers[q];}}
     walk();return {leaves,max};
    });assert.ok(enumeration.max<=8);return enumeration;
   });
   for(const [id,free,sku]of [['L01','money','p1'],['L02','bankrupt','p9'],['L03','advance','p8']])await test(id,label,async()=>{
    await go(free);const related=page.locator('section.related');assert.equal(await related.locator('.product-card').count(),1);
    assert.ok(!/990 ₽|t[145]-/.test(await related.innerHTML()));await related.locator('a').click();assert.ok(page.url().includes('/'+sku+'-'));return {url:page.url()};
   });
   await test('T01',label,async()=>{await go('t2');assert.ok(!(await page.locator('body').innerText()).includes('2 990'));const links=await page.locator('main a[href*="p4-"]').evaluateAll(els=>els.map(el=>({href:el.getAttribute('href'),text:el.textContent})));assert.ok(links.length>=3);assert.ok(links.every(el=>el.href.startsWith('p4-')));return {links,price:'24 900 ₽',t2:'9 900 ₽'};});
   await test('C01-C03-A01',label,async()=>{
    await page.evaluate(()=>localStorage.removeItem('marzhavbetone-cart'));await go('p8');await page.locator('.add-to-cart').first().click();
    assert.equal(await page.locator('#cart-count').innerText(),'1');assert.ok(/24\s*900/.test(await page.locator('#cart-total').innerText()));
    assert.equal(await page.locator('.add-to-cart').first().innerText(),'В корзине');
    await page.keyboard.press('Escape');assert.ok(await page.locator('#cart-panel').isHidden());assert.equal(await page.evaluate(()=>document.activeElement.classList.contains('add-to-cart')),true);
    await page.locator('#cart-toggle').click();await page.locator('#cart-checkout').click();assert.ok(await page.locator('#checkout-modal').isVisible());
    assert.equal(await page.locator('#checkout-form [name=email]').getAttribute('required'),'');assert.equal(await page.locator('#checkout-form [name=phone]').getAttribute('required'),null);
    await page.locator('#checkout-form button[type=submit]').click();assert.equal(paymentPosts,0);assert.equal(await page.locator('#checkout-form').evaluate(el=>el.checkValidity()),false);
    const screenshot=await shot('checkout',false);await page.keyboard.press('Escape');assert.ok(!(await page.locator('#checkout-modal').evaluate(el=>el.open)));assert.equal(await page.evaluate(()=>document.activeElement.id),'cart-checkout');return {screenshot,paymentPosts};
   });
   await test('CART-MIGRATION',label,async()=>{
    await page.evaluate(()=>localStorage.setItem('marzhavbetone-cart',JSON.stringify([{sku:'t1',name:'old',price:99000},{sku:'__proto__',name:'invalid',price:1},{sku:'p8',name:'old',price:1},{sku:'p8',name:'duplicate',price:1}])));await go('p8');await page.locator('#cart-toggle').click();
    const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('marzhavbetone-cart')));assert.equal(saved.length,1);assert.equal(saved[0].price,2490000);assert.ok((await page.locator('#cart-update-note').innerText()).includes('обновлена'));return saved;
   });
   await test('F01-F02-MOCK',label,async()=>{
    await go('money');await page.evaluate(()=>{window.routeGoals=[];window.mvbAttribution=()=>({last:{source:'synthetic',medium:'test',campaign:'route-qa'}});window.ym=(id,type,name,params)=>window.routeGoals.push({name,params});});
    const f=page.locator('#lead-form');await f.locator('button[type=submit]').click();assert.equal(leadPosts.length,0);
    await f.locator('[name=name]').fill('Synthetic');await f.locator('[name=contact]').fill('route@example.invalid');await f.locator('[name=additional_contact]').fill('@synthetic');await f.locator('[name=consent]').check();
    await f.evaluate(el=>{el.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));el.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));});
    await page.locator('[data-download-link]').waitFor();assert.equal(leadPosts.length,1);
    let goals=await page.evaluate(()=>window.routeGoals);assert.deepEqual(goals.map(g=>g.name),['lead_submit','lead_ready']);
    const download=page.waitForEvent('download');await page.locator('[data-download-link]').click();await download;
    await page.locator('[data-download-link]').dispatchEvent('click');goals=await page.evaluate(()=>window.routeGoals);
    assert.equal(goals.filter(g=>g.name==='download_click').length,1);assert.equal(goals[0].params.material,'dengi');assert.equal(goals[0].params.last.campaign,'route-qa');assert.ok(!JSON.stringify(goals).includes('example.invalid'));assert.ok(leadPosts[0].includes('@synthetic'));
    return {goals,screenshot:await shot('lead-ready'),server_served:'NOT_EXECUTED; local mocked response only'};
   });
   await test('F-ERROR',label,async()=>{
    leadMode='error';await go('money');await page.evaluate(()=>{window.routeGoals=[];window.ym=(id,type,name)=>window.routeGoals.push(name);});
    const f=page.locator('#lead-form');await f.locator('[name=name]').fill('Synthetic');await f.locator('[name=contact]').fill('route@example.invalid');await f.locator('[name=consent]').check();await f.locator('button[type=submit]').click();
    await page.getByText('Проверочная ошибка',{exact:true}).waitFor();assert.deepEqual(await page.evaluate(()=>window.routeGoals),['lead_submit']);leadMode='success';return {ready:0,click:0};
   });
   await test('E01',label,async()=>{await go('success');assert.ok(!(await page.locator('#error-content').innerText()).includes('заказ сохранён'));assert.ok(await page.locator('#success-content').isHidden());await page.goto(origin+'/success.html?order=synthetic&k=synthetic');assert.ok(await page.locator('#pending-content').isVisible());assert.ok(await page.locator('#success-content').isHidden());return {no_id:'unconfirmed',mock_status:'pending'};});
   await test('H03',label,async()=>{await go('home');const links=await page.locator('a[href*="katalog.html#"]').evaluateAll(els=>els.map(e=>e.getAttribute('href')));assert.ok(links.length>=3);for(const href of links){await page.goto(new URL(href,origin).href);const id=new URL(page.url()).hash.slice(1);assert.equal(await page.locator('[id="'+id+'"]').count(),1);}return {links};});
   if(label==='mobile')await test('MOBILE-MENU',label,async()=>{await go('money');await page.locator('.nav-toggle').click();assert.equal(await page.locator('.nav-toggle').getAttribute('aria-expanded'),'true');await page.keyboard.press('Escape');assert.equal(await page.locator('.nav-toggle').getAttribute('aria-expanded'),'false');return {closed:true};});
   if(label==='desktop')await test('CATALOG-FOLD',label,async()=>{await go('catalog');const top=await page.locator('.product-card').first().evaluate(el=>el.getBoundingClientRect().top);assert.ok(top<700,'First catalog card below fold: '+top);return {first_card_top:top};});
   await context.close();
  }
 }finally{if(browser)await browser.close();server.kill();fs.writeFileSync(path.join(OUT,'BROWSER_RESULTS.json'),JSON.stringify({results,errors,backend:process.env.ROUTE_PHP?'NATIVE_PHP':'READ_ONLY_STATIC_MIRROR',network_summary:{external_blocked:network.length,real_payment_posts:0,real_lead_posts:0},limits:'Free and status responses mocked. Payment POST blocked. Real paid E2E and download_served NOT_EXECUTED.'},null,2));}
 console.log(JSON.stringify({passed:results.filter(r=>r.status==='PASS').length,failed:results.filter(r=>r.status==='FAIL'),errors},null,2));if(results.some(r=>r.status==='FAIL')||errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
