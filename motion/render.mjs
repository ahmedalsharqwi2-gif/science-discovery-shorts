import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {spawn,spawnSync} from 'node:child_process';
import {once} from 'node:events';
import {validatePlan,drawFrame} from './engine.mjs';
const {createCanvas,GlobalFonts}=createRequire(import.meta.url)('@napi-rs/canvas');
const args=process.argv.slice(2),opt=(n,d)=>{const i=args.indexOf(n);return i<0?d:args[i+1];};
function probe(file){const r=spawnSync('ffprobe',['-v','error','-show_entries','format=duration','-of','csv=p=0',file],{encoding:'utf8'});if(r.status!==0)throw Error('Cannot probe supplied narration');return Number(r.stdout.trim());}
async function main(){
 const source=opt('--plan'),out=opt('--out'),audio=opt('--audio'),font=opt('--font'),still=opt('--frame');
 if(!source||!out||!font)throw Error('Required: --plan episode.json --out output.mp4 --font NotoSansArabic.ttf [--audio narration.wav | --frame seconds]');
 if(!fs.existsSync(font)||!GlobalFonts.registerFromPath(font,'Arabic'))throw Error('Arabic font could not be loaded');
 const p=JSON.parse(fs.readFileSync(source,'utf8'));
 if(still===undefined&&!audio)throw Error('A full render requires real narration; TTS is a separate stage');
 validatePlan(p,still===undefined?probe(audio):undefined);
 const w=Number(opt('--width','1080')),fps=Number(opt('--fps','30')),h=w*16/9;
 if(![360,720,1080].includes(w)||![24,30].includes(fps))throw Error('Unsupported export dimensions or frame rate');
 const canvas=createCanvas(w,h),ctx=canvas.getContext('2d');fs.mkdirSync(path.dirname(path.resolve(out)),{recursive:true});
 if(still!==undefined){drawFrame(ctx,p,Number(still),{width:w,height:h});fs.writeFileSync(out,canvas.toBuffer('image/png'));return;}
 const tmp=path.resolve(out)+'.partial.mp4';
 const ff=spawn('ffmpeg',['-v','error','-y','-f','rawvideo','-pix_fmt','rgba','-s',`${w}x${h}`,'-r',String(fps),'-i','pipe:0','-i',path.resolve(audio),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-b:a','160k','-movflags','+faststart',tmp],{stdio:['pipe','ignore','pipe']});
 let stderr='',failure;ff.stderr.on('data',d=>{stderr+=d.toString().slice(-4000);});ff.stdin.on('error',e=>{failure=e;});
 const exited=new Promise((resolve,reject)=>{ff.on('error',reject);ff.on('close',resolve);});
 try{
  for(let i=0;i<Math.ceil(p.duration*fps);i++){
   if(failure||ff.exitCode!==null)throw Error('Encoder stopped before all frames were rendered');
   drawFrame(ctx,p,i/fps,{width:w,height:h});const pixels=ctx.getImageData(0,0,w,h).data;
   if(!ff.stdin.write(Buffer.from(pixels.buffer,pixels.byteOffset,pixels.byteLength)))await Promise.race([once(ff.stdin,'drain'),exited.then(()=>{throw Error('Encoder exited');})]);
  }
  ff.stdin.end();if(await exited!==0)throw Error(stderr||'Encoder failed');
  if(Math.abs(probe(tmp)-p.duration)>Math.max(.15,2/fps))throw Error('Export duration differs from narration');
  fs.renameSync(tmp,out);
 }catch(e){ff.kill();fs.rmSync(tmp,{force:true});throw e;}
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
