import {chromium} from 'playwright-core';import {bundle} from '@remotion/bundler';import {ensureBrowser} from '@remotion/renderer';import http from 'node:http';import {readFile,stat} from 'node:fs/promises';import path from 'node:path';import {save} from './io.mjs';
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.ttf':'font/ttf','.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2'};
export async function layoutQA(props,out){
 const folder=await bundle({entryPoint:path.resolve('src/qa-entry.tsx'),ignoreRegisterRootWarning:true,publicDir:path.resolve('public')});
 const server=http.createServer(async(req,res)=>{try{const pathname=decodeURIComponent(new URL(req.url,'http://local').pathname),p=path.resolve(folder,'.'+pathname);if(!p.startsWith(path.resolve(folder)+path.sep)&&p!==path.resolve(folder))throw Error('PATH');const file=(await stat(p)).isDirectory()?path.join(p,'index.html'):p;res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.end(await readFile(file));}catch{res.writeHead(404);res.end();}});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 let browser;try{
  const status=await ensureBrowser({browserExecutable:process.env.CHROME_PATH||undefined});if(!('path'in status))throw Error('QA_BROWSER_UNAVAILABLE');
  browser=await chromium.launch({executablePath:status.path,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});await page.addInitScript(value=>{window.__qaProps=value;},props);
  await page.goto('http://127.0.0.1:'+server.address().port,{waitUntil:'networkidle'});await page.waitForFunction(()=>window.__qaReady===true);
  const frames=new Set([45,props.durationInFrames-2]);let at=0;
  for(const scene of props.scenes){for(const f of [15,60,120])frames.add(Math.min(props.durationInFrames-2,Math.max(0,Math.round(at*30)+f)));for(const word of scene.words||[])frames.add(Math.min(props.durationInFrames-2,Math.max(0,Math.round((at+(word.start+word.end)/2)*30))));at+=scene.duration;}
  const failures=[];let boxes=0;
  for(const frame of [...frames].sort((a,b)=>a-b)){
   await page.evaluate(async f=>window.__qaSeek(f),frame);
   const result=await page.evaluate(()=>[...document.querySelectorAll('[data-text-box], svg text')].filter(el=>getComputedStyle(el).visibility!=='hidden'&&el.textContent?.trim()).map(el=>{let rect=el.getBoundingClientRect();if(!(el instanceof SVGElement)){const range=document.createRange();range.selectNodeContents(el);rect=range.getBoundingClientRect();}return {text:el.textContent?.trim().slice(0,100),x:rect.x,y:rect.y,right:rect.right,bottom:rect.bottom};}));boxes+=result.length;
   for(const box of result)if(box.x<40||box.right>1040||box.y<150||box.bottom>1670)failures.push({frame,...box});
  }
  const result={passed:failures.length===0,framesChecked:frames.size,textBoxesChecked:boxes,forbiddenTop:150,forbiddenBottomFrom:1670,failures};await save(path.resolve(out,'layout-qa.json'),result);if(!result.passed)throw Error('TEXT_SAFE_AREA_QA_FAILED');return result;
 }finally{await browser?.close();await new Promise(r=>server.close(r));}
}
