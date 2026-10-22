const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'../..'),OUT='/tmp/nsp-final-evidence/stage-links';
fs.mkdirSync(OUT,{recursive:true});
const expected=['/katalog.html#group-do-podpisaniya','/katalog.html#group-zakrytie-i-oplata','/katalog.html#selection-oplata'];
const server=http.createServer((req,res)=>{
  let p=decodeURIComponent(new URL(req.url,'http://local').pathname);
  if(p==='/before')p='/tools/nsp-stage-links-20261022/before-index.html';
  if(p==='/app-script.php')p='/app.js';if(p==='/')p='/index.html';
  const f=path.resolve(ROOT,'.'+p);if(!f.startsWith(ROOT+'/')){res.writeHead(403);return res.end()}
  try{res.setHeader('Content-Type',({'.html':'text/html','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml','.woff2':'font/woff2'})[path.extname(f)]||'application/octet-stream');res.end(fs.readFileSync(f))}catch{res.writeHead(404);res.end()}
});
(async()=>{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const local='http://127.0.0.1:'+server.address().port,base=process.env.NSP_LIVE==='1'?'https://nastoronepodryadchika.ru':local;
  const browser=await chromium.launch({executablePath:process.env.NSP_CHROMIUM||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
  const results=[];
  try{for(const [width,height] of [[360,800],[390,844],[1280,600],[1366,650],[1440,900],[1920,1080]]){
    const ctx=await browser.newContext({viewport:{width,height}}),p=await ctx.newPage();
    await p.route('**/*',r=>new URL(r.request().url()).origin===base&&r.request().method()==='GET'?r.continue():r.abort());
    await p.goto(base+'/',{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);
    const after=await p.screenshot({path:OUT+'/'+(process.env.NSP_LIVE?'live-':'after-')+width+'.png',fullPage:width<768});
    if(!process.env.NSP_LIVE){
      // Compare fresh pages before click/scroll/focus changes sticky-header rendering.
      const baseline=await ctx.newPage();
      await baseline.goto(local+'/before',{waitUntil:'networkidle'});await baseline.evaluate(()=>document.fonts.ready);
      const before=await baseline.screenshot({path:OUT+'/before-'+width+'.png',fullPage:width<768});
      assert(before.equals(after),'appearance changed at '+width);
      await baseline.close();await p.bringToFront();
    }
    assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow');
    await p.evaluate(()=>{window.stageClicks=[];document.addEventListener('click',e=>{const a=e.target.closest('a');if(a){e.preventDefault();window.stageClicks.push(a.getAttribute('href'))}},true)});
    for(let i=0;i<3;i++){
      const row=p.locator('.stage-grid article').nth(i),title=row.locator('h3 a');
      assert.equal(await title.getAttribute('href'),expected[i]);
      for(const selector of ['h3','p','svg']){
        await row.scrollIntoViewIfNeeded();const r=await row.locator(selector).boundingBox();
        await p.mouse.click(r.x+r.width/2,r.y+r.height/2);
        assert.equal(await p.evaluate(()=>window.stageClicks.pop()),expected[i],width+' '+i+' '+selector);
      }
      await row.scrollIntoViewIfNeeded();const r=await row.boundingBox();
      await p.mouse.click(r.x+r.width-3,r.y+3);
      assert.equal(await p.evaluate(()=>window.stageClicks.pop()),expected[i],'row whitespace');
      await title.focus();await p.keyboard.press('Enter');
      assert.equal(await p.evaluate(()=>window.stageClicks.pop()),expected[i],'keyboard Enter');
      const target=fs.readFileSync(path.join(ROOT,'katalog.html'),'utf8');assert(target.includes('id="'+expected[i].split('#')[1]+'"'));
    }
    results.push({width,height,title_description_icon_whitespace_keyboard:'PASS',appearance:process.env.NSP_LIVE?'published screenshot saved':'PIXEL_IDENTICAL'});
    await ctx.close();
  }}finally{await browser.close();server.close()}
  fs.writeFileSync(OUT+'/'+(process.env.NSP_LIVE?'live':'local')+'.json',JSON.stringify({status:'PASS',results},null,2));
  console.log(JSON.stringify({status:'PASS',viewports:results.length,click_checks:90,live:!!process.env.NSP_LIVE}));
})().catch(e=>{console.error(e);server.close();process.exit(1)});
