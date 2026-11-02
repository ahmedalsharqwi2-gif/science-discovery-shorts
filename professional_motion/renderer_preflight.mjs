/** Exercise actual browser scenes before paid narration; never exports a publishable video. */
import {createServer} from 'node:http';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import path from 'node:path';
import {once} from 'node:events';
import {chromium} from 'playwright-core';
const root=path.resolve(process.cwd());
const delivery=path.join(root,'professional_motion/delivery');
const storyBytes=await readFile(path.join(delivery,'story.json'));
const story=JSON.parse(storyBytes);
if(story.scenes?.length!==8)throw Error('Eight authored scenes required');
const measured=process.argv.includes('--measured');
const timing=measured?JSON.parse(await readFile(path.join(delivery,'timing.json'))):{
 duration:40,scenes:story.scenes.map((s,i)=>({...s,start:i*5,end:(i+1)*5})),words:[],caption_groups:[],
 timing_method:'synthetic_non_publishable_renderer_preflight',publishable:false
};
const mime={'.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.html':'text/html','.ttf':'font/ttf','.png':'image/png'};
const server=createServer(async(req,res)=>{try{
 const route=decodeURIComponent(req.url.split('?')[0]);
 if(route==='/professional_motion/delivery/timing.json'){res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify(timing));return;}
 const file=path.resolve(root,'.'+route);if(!file.startsWith(root+path.sep))throw Error('Path escape');
 const bytes=await readFile(file);res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream'});res.end(bytes);
}catch{res.writeHead(404);res.end('Not found');}});
server.listen(0,'127.0.0.1');await once(server,'listening');
let browser;const errors=[];const samples=[];
try{
 browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':chromium.executablePath()),headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1080,height:1920}});
 page.on('pageerror',e=>{errors.push(e.stack||e.message);console.error(e.stack||e.message);});
 page.on('requestfailed',r=>console.error('Asset request failed:',r.url(),r.failure()?.errorText));
 page.on('response',r=>{if(r.status()>=400)console.error('Asset HTTP',r.status(),r.url());});
 await page.goto(`http://127.0.0.1:${server.address().port}/professional_motion/index.html?pipeline=v2&style=original&review=true`);
 await page.waitForFunction(()=>window.ready===true,null,{timeout:60000});
 for(let i=0;i<8;i++)for(const progress of [0,.25,.5,.75,.999]){
  const s=timing.scenes[i],t=s.start+Math.max(0,(s.end-s.start))*progress;
  const result=await page.evaluate(({t,d})=>{const result=window.renderAt(t,d);const frame=window.captureFrame();if(typeof frame!=='string'||frame.length<500)throw Error('Empty rendered frame');return result;},{t,d:timing.duration});
  if(result.scene!==i+1)throw Error('Scene selection differs at boundary '+i+' time '+t);
  if(errors.length)throw Error(errors.join('\n'));samples.push({scene:i+1,progress,time:t});
 }
 await mkdir(delivery,{recursive:true});
 await writeFile(path.join(delivery,measured?'measured-renderer-preflight.json':'renderer-preflight.json'),JSON.stringify({passed:true,publishable:false,measured_timing:measured,samples,errors},null,2));
 console.log('All eight actual browser scenes passed forty sampled poses; no publication or provider calls');
}finally{if(browser)await browser.close();server.close();}
