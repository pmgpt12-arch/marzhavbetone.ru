import fs from 'node:fs';
import path from 'node:path';
const [debugPort, base, out] = process.argv.slice(2);
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const runs = [], interceptions = [];
let socket, seq = 0;
const pending = new Map();
let websocketOpened = false;
function call(method, params = {}, sessionId) {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout ' + method)); }, 8000);
    pending.set(id, {resolve, reject, timer});
    socket.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
  });
}
let status = 'BLOCKED/RUNTIME_ERROR', error = null;
try {
  if (typeof WebSocket !== 'function') throw new Error('MISSING_BUILTIN_WEBSOCKET');
  let version;
  const startup = Date.now();
  while (Date.now() - startup < 5000) {
    try { const response = await fetch('http://127.0.0.1:' + debugPort + '/json/version', {signal:AbortSignal.timeout(500)}); version = await response.json(); break; }
    catch { await wait(100); }
  }
  if (!version?.webSocketDebuggerUrl) throw new Error('CHROME_DEBUG_STARTUP_UNAVAILABLE');
  socket = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('WEBSOCKET_OPEN_TIMEOUT')), 5000);
    socket.addEventListener('open', () => { clearTimeout(timer); websocketOpened = true; resolve(); }, {once:true});
    socket.addEventListener('error', () => { clearTimeout(timer); reject(new Error('WEBSOCKET_ERROR')); }, {once:true});
  });
  socket.addEventListener('message', event => {
    const msg = JSON.parse(String(event.data));
    if (msg.id) {
      const holder = pending.get(msg.id); if (!holder) return;
      pending.delete(msg.id); clearTimeout(holder.timer);
      if (msg.error) holder.reject(new Error(JSON.stringify(msg.error))); else holder.resolve(msg.result);
    } else if (msg.method === 'Fetch.requestPaused') {
      const request = msg.params.request;
      const local = request.url.startsWith(base + '/');
      const safe = ['GET','HEAD'].includes(request.method);
      interceptions.push({url:request.url, method:request.method, action:local && safe ? 'continue' : 'abort'});
      call(local && safe ? 'Fetch.continueRequest' : 'Fetch.failRequest',
           local && safe ? {requestId:msg.params.requestId} : {requestId:msg.params.requestId,errorReason:'BlockedByClient'},
           msg.sessionId).catch(e => { error = String(e); });
    }
  });
  for (const [kind, width, height, rel] of [
    ['article',390,900,'articles/ks-2-ks-3-podpisany-zakazchik-ne-oplachivaet.html'],
    ['article',1440,1000,'articles/ks-2-ks-3-podpisany-zakazchik-ne-oplachivaet.html'],
    ['index-card',390,900,'articles/index.html'],
    ['index-card',1440,1000,'articles/index.html'],
  ]) {
    const {targetId} = await call('Target.createTarget', {url:'about:blank'});
    const {sessionId} = await call('Target.attachToTarget', {targetId, flatten:true});
    await call('Page.enable',{},sessionId);
    await call('Runtime.enable',{},sessionId);
    await call('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]},sessionId);
    await call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false,screenWidth:width,screenHeight:height},sessionId);
    await call('Page.navigate',{url:base+'/'+rel},sessionId);
    let layout;
    const start=Date.now();
    while (Date.now()-start<8000) {
      await wait(150);
      const measured=await call('Runtime.evaluate',{expression:`(() => {
        const target=document.querySelector('a.showcase-card[href="ks-2-ks-3-podpisany-zakazchik-ne-oplachivaet.html"]');
        const cover=document.querySelector('img.article-cover')||(target&&target.querySelector('img'));
        if(cover)cover.loading='eager';
        const r=el=>{if(!el)return null;const b=el.getBoundingClientRect();const c=getComputedStyle(el);return{x:b.x,y:b.y,width:b.width,height:b.height,absoluteY:b.y+scrollY,naturalWidth:el.naturalWidth,naturalHeight:el.naturalHeight,objectFit:c.objectFit}};
        return {ready:document.readyState,innerWidth,innerHeight,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight,scrollY,cover:r(cover),target:r(target),navToggle:r(document.querySelector('.nav-toggle')),forms:document.forms.length};
      })()`,returnByValue:true},sessionId);
      layout=measured.result.value;
      if(layout.ready==='complete'&&layout.cover?.naturalWidth===1672&&Date.now()-start>950)break;
    }
    if(layout.innerWidth!==width||layout.clientWidth!==width||layout.scrollWidth!==width)throw new Error('VIEWPORT_MISMATCH '+JSON.stringify(layout));
    if(layout.innerHeight!==height||layout.cover?.naturalWidth!==1672||layout.cover?.naturalHeight!==941)throw new Error('LAYOUT_OR_COVER_NOT_READY');
    if(error)throw new Error(error);
    let clip;
    if(kind==='article')clip={x:0,y:0,width,height:layout.scrollHeight,scale:1};
    else {
      if(!layout.target)throw new Error('INDEX_TARGET_MISSING');
      clip={x:0,y:Math.max(0,layout.target.absoluteY-20),width,height:Math.ceil(layout.target.height+40),scale:1};
    }
    const screenshot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,fromSurface:true,clip},sessionId);
    const png=Buffer.from(screenshot.data,'base64');
    const name='cdp-'+kind+'-'+width+'.png';
    fs.writeFileSync(path.join(out,name),png);
    const pngWidth=png.readUInt32BE(16),pngHeight=png.readUInt32BE(20);
    if(pngWidth!==width)throw new Error('PNG_WIDTH_MISMATCH');
    runs.push({kind,requested_width:width,requested_height:height,layout,clip,png:name,png_width:pngWidth,png_height:pngHeight});
    await call('Target.closeTarget',{targetId});
    console.log(kind+' '+width+' viewport verified; '+name+' '+pngWidth+'x'+pngHeight);
  }
  status='RENDERED/PENDING_IMAGE_INSPECTION';
} catch (exc) { error=String(exc); console.error(error); process.exitCode=1; }
finally {
  if(socket&&websocketOpened)socket.close();
  const receipt={status,error,frozen_input_sha:'14c5a562c93ad7f7c28aa73588d9ca2d8b35fea3',route:'GoogleChrome CDP via Node22 built-in WebSocket',browser_runs:1,metrics_override_before_navigation:true,runs,interceptions,all_non_get_or_external_aborted:true,no_package_install:true,screenshot_inspected:false};
  fs.writeFileSync(path.join(out,'cdp-render-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
}
