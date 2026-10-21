const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');
(async()=>{
 const raw=process.env.HTTPS_PROXY||process.env.HTTP_PROXY,proxy=raw?new URL(raw):null;
 const browser=await chromium.launch({executablePath:process.env.NSP_CHROMIUM||'/usr/bin/google-chrome',args:['--no-sandbox'],...(proxy?{proxy:{server:proxy.origin,...(proxy.username?{username:decodeURIComponent(proxy.username),password:decodeURIComponent(proxy.password)}:{})}}:{})});
 const context=await browser.newContext({viewport:{width:1366,height:900}}),page=await context.newPage();let blockedPosts=[];
 await page.route('**/*',route=>{const req=route.request();if(req.method()!=='GET'){blockedPosts.push({host:new URL(req.url()).hostname,path:new URL(req.url()).pathname});return route.abort();}return new URL(req.url()).hostname==='nastoronepodryadchika.ru'?route.continue():route.abort();});
 await page.goto('https://nastoronepodryadchika.ru/',{waitUntil:'networkidle'});
 assert.equal(await page.locator('#product').inputValue(),'Персональный разбор объекта');
 await page.locator('.quick-choice summary').click();assert.equal(await page.locator('.quick-choice a').count(),5);assert((await page.locator('.quick-choice a').first().textContent()).includes('24 900'));
 const header=await page.evaluate(()=>{const a=document.querySelector('.nav-cta').getBoundingClientRect(),b=document.querySelector('.cart-toggle').getBoundingClientRect();return {gap:b.left-a.right,viewport:innerWidth,scroll:document.documentElement.scrollWidth};});assert(header.gap>=8&&header.scroll<=header.viewport);
 await page.goto('https://nastoronepodryadchika.ru/diagnostika.html',{waitUntil:'networkidle'});
 for(let i=0;i<12&&!await page.locator('#dresult').isVisible();i++){const button=page.locator('.dq:not([hidden]) button').first();assert(await button.isVisible());await button.click();}
 assert(await page.locator('#dresult').isVisible());
 const gold=await page.locator('#dresult h2').evaluate(el=>getComputedStyle(el).color);assert.equal(gold,'rgb(210, 184, 139)');
 await page.goto('https://nastoronepodryadchika.ru/kalkulyator.html',{waitUntil:'networkidle'});assert.equal(await page.locator('#debt-result').evaluate(el=>getComputedStyle(el).color),'rgb(210, 184, 139)');
 const result={status:'PASS',date:new Date().toISOString(),scope:'Production home details and one diagnostic result branch',quick_choices:5,review_purpose:'EXPLICIT',header,diagnostic_result_gold:gold,calculator_gold:'PASS',production_posts_allowed:0,blocked_non_get_requests:blockedPosts};
 fs.writeFileSync(process.env.NSP_DETAILS_OUTPUT||'/tmp/nsp-ui-details.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
