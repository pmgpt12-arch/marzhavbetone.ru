// Read-only live DOM/screenshots. Third parties and every POST are blocked.
const {chromium}=require('playwright');const fs=require('fs'),path=require('path');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.ROUTE_CHROMIUM,headless:true,proxy:process.env.HTTPS_PROXY?{server:process.env.HTTPS_PROXY}:undefined,args:['--no-sandbox','--disable-gpu']});
 const out=path.join(__dirname,'screens/live-before');fs.mkdirSync(out,{recursive:true});const rows=[];
 try{for(const [label,viewport]of [['desktop',{width:1366,height:850}],['mobile',{width:390,height:844}]]){
  const context=await browser.newContext({viewport,ignoreHTTPSErrors:true});
  await context.route('**/*',r=>{const req=r.request(),url=new URL(req.url());return url.hostname==='nastoronepodryadchika.ru'&&req.method()==='GET'?r.continue():r.fulfill({status:204,body:''});});
  const page=await context.newPage();
  for(const [id,p]of [['diagnostic','diagnostika.html'],['money','materialy/dengi.html'],['bankrupt','materialy/bankrotstvo.html'],['advance','materialy/avans.html'],['t2','products/t2-peredacha-ispolnitelnoy-dokumentacii.html'],['p11','products/p11-raschet-metrami.html']]){
   const response=await page.goto('https://nastoronepodryadchika.ru/'+p,{timeout:25000});await page.screenshot({path:path.join(out,`${id}-${label}.png`),fullPage:true});
   let observation;if(id==='diagnostic'){await page.locator('[data-q="bankrot"] [data-a="yes"]').click();observation=await page.locator('#dresult').innerText();await page.screenshot({path:path.join(out,`diagnostic-risk-${label}.png`),fullPage:true});}
   else observation=(await page.locator('main').innerText()).slice(0,50000);
   rows.push({id,label,url:page.url(),status:response.status(),observation});
  }
  await context.close();
 }}finally{await browser.close();fs.writeFileSync(path.join(__dirname,'LIVE_DOM_BASELINE.json'),JSON.stringify({rows,real_post_requests:0,external_requests:'BLOCKED'},null,2));}
 console.log('Live baseline cases:',rows.length);
})().catch(e=>{console.error(e.message);process.exit(1)});
