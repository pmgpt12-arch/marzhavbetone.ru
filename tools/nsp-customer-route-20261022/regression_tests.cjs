const{chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),{spawn}=require('child_process');
const ROOT=path.resolve(__dirname,'../..'),BEFORE=process.env.ROUTE_BEFORE,rows=[];
(async()=>{
 const server=spawn('python3',[path.join(__dirname,'staging_server.py'),ROOT,'8094'],{stdio:'ignore'}),before=spawn('python3',[path.join(__dirname,'staging_server.py'),BEFORE,'8095'],{stdio:'ignore'});
 const browser=await chromium.launch({executablePath:process.env.ROUTE_CHROMIUM,headless:true,args:['--no-sandbox','--disable-gpu']});
 try{
 await new Promise(r=>setTimeout(r,400));
 const catalog=JSON.parse(fs.readFileSync(path.join(ROOT,'app.js'),'utf8').match(/const CART_CATALOG = (.*);/)[1]);
 for(const [label,viewport]of [['desktop',{width:1366,height:850}],['mobile',{width:390,height:844}]]){
  const context=await browser.newContext({viewport});await context.route('**/*',r=>/^http:\/\/127\.0\.0\.1:809[45]\//.test(r.request().url())&&r.request().method()==='GET'?r.continue():r.fulfill({status:204,body:''}));const page=await context.newPage();
  const geometry=[];
  for(const port of [8095,8094]){
   await page.goto(`http://127.0.0.1:${port}/`);geometry.push(await page.evaluate(()=>['.hero','#home-title','.hero-actions','.stage-solutions','#situations'].map(s=>{const el=document.querySelector(s),r=el.getBoundingClientRect(),c=getComputedStyle(el);return {s,x:r.x,y:r.y,width:r.width,height:r.height,font:c.font,color:c.color,background:c.background};})));
  }
  assert.deepEqual(geometry[0],geometry[1]);if(label==='desktop')assert.ok(geometry[1][4].y<850);rows.push({id:label==='desktop'?'H01':'H02',status:'PASS',label,geometry:geometry[1]});
  for(const filename of fs.readdirSync(path.join(ROOT,'materialy'))){
   if(!filename.endsWith('.html')||!fs.readFileSync(path.join(ROOT,'materialy',filename),'utf8').includes('id="lead-form"'))continue;
   await page.goto('http://127.0.0.1:8094/materialy/'+filename);
   const field=await page.locator('#lead-form [type=email]').evaluate(el=>({width:el.getBoundingClientRect().width,labelWidth:el.parentElement.getBoundingClientRect().width,height:el.getBoundingClientRect().height}));
   assert.ok(field.width>=field.labelWidth-2);assert.ok(field.height>=44);rows.push({id:'FORM-STYLE-'+filename,label,status:'PASS',actual:field});
  }
  for(const [sku,expected]of Object.entries(catalog)){
   await page.evaluate(()=>localStorage.removeItem('marzhavbetone-cart'));const filename=fs.readdirSync(path.join(ROOT,'products')).find(p=>p.startsWith(sku+'-'));await page.goto('http://127.0.0.1:8094/products/'+filename);await page.locator('.add-to-cart').first().click();
   const actual=await page.evaluate(()=>JSON.parse(localStorage.getItem('marzhavbetone-cart')));assert.deepEqual(actual,[expected]);await page.keyboard.press('Escape');await page.locator('.add-to-cart').first().click();assert.equal(await page.locator('#cart-count').innerText(),'1');
   rows.push({id:'CART-'+sku,label,status:'PASS',actual});
  }
  for(const [sku,target]of [['t1','p1'],['t4','p9'],['t5','p8']]){
   const filename=fs.readdirSync(path.join(ROOT,'products')).find(p=>p.startsWith(sku+'-'));await page.goto('http://127.0.0.1:8094/products/'+filename);assert.equal(await page.locator('.add-to-cart').count(),0);await page.locator(`main a[href^="${target}-"]`).click();assert.ok(page.url().includes('/products/'+target+'-'));rows.push({id:'S01-'+sku,label,status:'PASS',url:page.url()});
  }
  await context.close();
 }
 }finally{await browser.close();server.kill();before.kill();fs.writeFileSync(path.join(__dirname,'REGRESSION_RESULTS.json'),JSON.stringify({rows},null,2));}
 console.log('Supplementary regression PASS:',rows.length);
})().catch(e=>{console.error(e);process.exit(1)});
