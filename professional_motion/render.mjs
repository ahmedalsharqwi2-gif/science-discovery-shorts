import {createHash} from 'node:crypto';
import {chromium} from 'playwright-core';
import {createServer} from 'node:http';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
import {once} from 'node:events';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.join(root,'professional_motion/output');await mkdir(output,{recursive:true});
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.ttf':'font/ttf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'};
const server=createServer(async(req,res)=>{
 try{const p=path.resolve(root,'.'+decodeURIComponent(req.url.split('?')[0]));if(!p.startsWith(root+path.sep))throw Error('path');const b=await readFile(p);res.writeHead(200,{'Content-Type':mime[path.extname(p)]||'application/octet-stream','Cache-Control':'no-store'});res.end(b);}catch{res.writeHead(404);res.end('Not found');}
});server.listen(0,'127.0.0.1');await once(server,'listening');
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':chromium.executablePath()),headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
const errors=[];page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('404')){errors.push(m.text());console.error(m.text());}});page.on('pageerror',e=>{errors.push(e.message);console.error(e.message)});
try{
 const styleIndex=process.argv.indexOf('--style'),style=styleIndex<0?'original':process.argv[styleIndex+1];
 if(!['original','reference'].includes(style))throw Error('Unknown visual style');
 const query=new URLSearchParams({style,review:String(process.argv.includes('--review'))});
 await page.goto(`http://127.0.0.1:${server.address().port}/professional_motion/index.html?${query}`);
 await page.waitForFunction(()=>window.ready===true,null,{timeout:60000});
 if(errors.length)throw Error('Renderer page errors');
 let timing;try{timing=JSON.parse(await readFile(path.join(root,'professional_motion/delivery/timing.json'),'utf8'));}catch{}
 const storyHash=createHash('sha256').update(await readFile(path.join(root,'professional_motion/delivery/story.json'))).digest('hex');
 if(timing&&timing.story_sha256!==storyHash)throw Error('Story changed after measured voice timing');
 const duration=timing?.duration||46.5;const fps=30;
 const flag=(key,fallback)=>{let i=process.argv.indexOf(key);return i<0?fallback:process.argv[i+1];};
 const splitting=process.argv.includes('--part'),part=Number(flag('--part',0)),parts=Number(flag('--parts',1));
 if(!Number.isInteger(part)||!Number.isInteger(parts)||parts<1||part<0||part>=parts)throw Error('Invalid frame partition');
 if(splitting&&(process.argv.includes('--from')||process.argv.includes('--to')))throw Error('Choose frame partitions or time intervals');
 const totalFrames=Math.ceil(duration*fps);
 const from=splitting?Math.floor(totalFrames*part/parts)/fps:Number(flag('--from',0)),to=splitting?Math.min(duration,Math.floor(totalFrames*(part+1)/parts)/fps):Number(flag('--to',duration));
 const startFrame=splitting?Math.floor(totalFrames*part/parts):Math.ceil(from*fps),endFrame=splitting?Math.floor(totalFrames*(part+1)/parts):Math.ceil(to*fps);
 if(!Number.isFinite(from)||!Number.isFinite(to)||from<0||to<=from||to>duration+.001)throw Error('Invalid render interval');
 const outputName=path.basename(flag('--output','visuals.mp4'));const partial=startFrame>0||endFrame<totalFrames;
 console.log(JSON.stringify({duration,originalVoice:!!timing,webgl:await page.evaluate(()=>document.querySelector('canvas:not(#text)').getContext('webgl2')?.getParameter(7937))}));
 const stills=process.argv.includes('--stills');
 if(stills){
  for(const [i,t] of [2.7,7,12,18,24,30,36.5,43].entries()){
   await page.evaluate(({t,d})=>window.renderAt(t,d),{t:t/46.5*duration,d:duration});
   const data=await page.evaluate(()=>window.captureFrame());await writeFile(path.join(output,`shot-${i+1}.jpg`),Buffer.from(data,'base64'));
  }
 }else{
  const ff=spawn('ffmpeg',['-y','-v','error','-f','image2pipe','-vcodec','mjpeg','-r',String(fps),'-i','-','-an','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',path.join(output,outputName)],{stdio:['pipe','inherit','inherit']});
  const completed=once(ff,'exit');ff.stdin.on('error',e=>console.error('Encoder input:',e.message));
  for(let i=startFrame;i<endFrame;i++){
   await page.evaluate(({t,d})=>window.renderAt(t,d),{t:i/fps,d:duration});
   const data=await page.evaluate(()=>window.captureFrame());
   if(!ff.stdin.write(Buffer.from(data,'base64')))await once(ff.stdin,'drain');
   if(i%90===0)console.log(`Rendered ${(i/fps).toFixed(0)} / ${duration.toFixed(1)} s`);
   if(errors.length)throw Error('Rendering failed');
  }
  ff.stdin.end();const [code]=await completed;if(code!==0)throw Error('FFmpeg failed');
 }
 await writeFile(path.join(output,partial?outputName+'.json':'render.json'),JSON.stringify({duration,from,to,start_frame:startFrame,end_frame:endFrame,total_frames:totalFrames,fps,width:1080,height:1920,originalVoice:!!timing,visual_style:style,review:process.argv.includes('--review'),story_sha256:storyHash,branding:await page.evaluate(()=>window.brandingStatus),errors},null,2));
}finally{await browser.close();server.close();}
