import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';
import {readFile,writeFile,mkdir,open,rm,copyFile} from 'node:fs/promises';
import {bundle} from '@remotion/bundler';import {selectComposition,renderMedia} from '@remotion/renderer';
import {assertReviewMode,assertTiming,assertMedia,dueInCairo,digest} from './policy.mjs';
import {json,save,run,probe} from './io.mjs';import {selectTopic,script,voice,backgrounds} from './providers.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
async function mix(segments,dir){
 const concat=dir+'/concat.txt';await writeFile(concat,segments.map(s=>`file '${path.resolve(s.file).replaceAll("'","'\\''")}'`).join('\n'));
 const d=segments.reduce((n,s)=>n+s.duration,0);if(d<90||d>180)throw Error('NARRATION_DURATION_OUT_OF_RANGE');
 await run('ffmpeg',['-y','-v','error','-f','concat','-safe','0','-i',concat,'-c:a','pcm_s16le',dir+'/narration.wav'],{timeout:120000});
 // Original sine-pulse bed and sweep: generated in FFmpeg, no third-party recordings.
 await run('ffmpeg',['-y','-v','error','-i',dir+'/narration.wav','-f','lavfi','-i',`aevalsrc=0.015*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.5*t))+0.006*sin(2*PI*(280+80*sin(t))*t):s=24000:d=${d}`,'-filter_complex','[1:a]asplit=2[bed][unused];[unused]anullsink;[bed][0:a]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=300[duck];[duck][0:a]amix=inputs=2:duration=longest:normalize=0[mix]','-map','[mix]',dir+'/mix.wav'],{timeout:120000});
 const first=await run('ffmpeg',['-hide_banner','-i',dir+'/mix.wav','-af','loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json','-f','null','-'],{timeout:120000});
 const m=JSON.parse(first.stderr.slice(first.stderr.lastIndexOf('{')));
 if(!Number.isFinite(Number(m.input_i)))throw Error('SILENT_AUDIO');
 const filter=`loudnorm=I=-14:TP=-1.5:LRA=9:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true`;
 await run('ffmpeg',['-y','-v','error','-i',dir+'/mix.wav','-af',filter,'-ar','48000',dir+'/audio.wav'],{timeout:120000});return d;
}
export async function review({mode='review',scheduled=false}={}){
 process.chdir(ROOT);const release=await json('config/release.json'); 
 if(scheduled&&!dueInCairo(new Date()))return {status:'outside_cairo_slot'};
 const cfg=await json('config/channel.json');const id=new Date().toISOString().replace(/[:.]/g,'-');const out=path.resolve('out',id);await mkdir(out,{recursive:true});
 let current='preflight',lock;const report={id,mode:'review',published:false,stages:[],status:'running',limitations:['Visual semantics, pronunciation, watermark absence and copyright require human review; metrics are not proof.']};
 async function stage(name,fn){current=name;const started=Date.now();const result=await fn();report.stages.push({name,status:'pass',seconds:(Date.now()-started)/1000});await save(out+'/report.json',report);return result;}
 try{
  lock=await open('.pipeline.lock','wx');
  await stage('preflight',async()=>{assertReviewMode(mode,release);await run('ffmpeg',['-version'],{timeout:10000});await readFile('public/fonts/Arabic-Bold.ttf');if(!process.env.GEMINI_API_KEY&&!process.env.GEMINI_TEXT_API_KEY)throw Error('MISSING_GEMINI_BINDING');});
  const old=await json('state/legacy-topic-index.json');let ledger;try{ledger=await json('state/topics.json');}catch(e){if(e.code!=='ENOENT')throw e;ledger=[];}
  const history=[...old,...ledger];
  const topic=await stage('topics',()=>selectTopic(cfg,history));await save(out+'/sources.json',topic);
  const episode=await stage('script',()=>script(topic,cfg,history));await save(out+'/script.json',episode);
  // Reserve before TTS; failures stay reserved to prevent parallel and repeated productions.
  ledger.push({topicKey:episode.topicKey,value:topic.selected.url,status:'reserved',run:id});await save(path.resolve('state/topics.json'),ledger);
  const pub=path.resolve('public/generated',id);await mkdir(pub,{recursive:true});
  const segments=await stage('voice',()=>voice(episode,pub));await save(out+'/segments.json',segments);
  await stage('align',async()=>{await run(process.env.PYTHON||'python',['pipeline/align.py',out+'/segments.json',out+'/alignment.json'],{timeout:1800000,maxBuffer:2000000});const alignment=await json(out+'/alignment.json');segments.forEach((s,i)=>assertTiming(alignment[i],s.duration,s.text));segments.forEach((s,i)=>{episode.scenes[i].words=alignment[i];episode.scenes[i].duration=s.duration;});});
  await stage('assets',async()=>{
   for(const scene of episode.scenes){const source=topic.sources.find(s=>s.id===scene.sourceId);scene.sourceUrl=source.url;scene.sourceLabel=new URL(source.url).hostname;}
   const generated=await backgrounds(episode,cfg,pub);await save(out+'/assets.json',generated);
   await writeFile(out+'/ATTRIBUTIONS.md','# Asset rights\n\nOriginal frame-driven SVG and FFmpeg synthesized bed. Preserved channel font: see docs/LICENSES.md. RSS article text used for research only, not reproduced in full. No downloaded third-party image/music.\n');
  });
  const duration=await stage('mix',()=>mix(segments,pub));const frames=episode.scenes.reduce((n,s)=>n+Math.round(s.duration*30),0);const props={...episode,audio:'generated/'+id+'/audio.wav',durationInFrames:frames};await save(out+'/props.json',props);
  await stage('render',async()=>{const serveUrl=await bundle({entryPoint:path.resolve('src/index.tsx'),publicDir:path.resolve('public')});const chromiumOptions={gl:'swangle'};const browserExecutable=process.env.CHROME_PATH||undefined;const composition=await selectComposition({serveUrl,id:'Episode',inputProps:props,chromiumOptions,browserExecutable});await renderMedia({serveUrl,composition,inputProps:props,codec:'h264',outputLocation:out+'/review.mp4',concurrency:2,x264Preset:'veryfast',chromiumOptions,browserExecutable});});
  await stage('qa',async()=>{
   const p=await probe(out+'/review.mp4');assertMedia(p);
   const result=await run('ffmpeg',['-hide_banner','-i',out+'/review.mp4','-af','loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json','-f','null','-'],{timeout:120000});const m=JSON.parse(result.stderr.slice(result.stderr.lastIndexOf('{')));if(Math.abs(Number(m.input_i)+14)>1.2||Number(m.input_tp)>-1)throw Error('AUDIO_LOUDNESS_FAILED');
   const checks={dimensions:[1080,1920],fps:30,duration:Number(p.format.duration),integratedLUFS:m.input_i,truePeak:m.input_tp,alignment:'measured, source transcript preserved',visual:'manual review pending',audioListening:'pending',approved:false};await save(out+'/qa.json',checks);
   await run('ffmpeg',['-y','-v','error','-i',out+'/review.mp4','-vf','fps=1/3,scale=180:320,tile=6x10','-frames:v','1',out+'/contact-sheet.jpg'],{timeout:120000});
  });
  await stage('package',async()=>{await save(out+'/metadata.json',{title:episode.title,topicKey:episode.topicKey,voice:'Charon',provider:'Gemini',sources:topic.sources.map(({text,...s})=>s),video_sha256:digest(await readFile(out+'/review.mp4')),reviewOnly:true,approved:false});});
  ledger[ledger.length-1].status='review';await save(path.resolve('state/topics.json'),ledger);report.status='review_ready';await save(out+'/report.json',report);return {out,status:report.status};
 }catch(e){report.status='failed';report.failedStage=current;report.errorCode=/^[A-Z0-9_: -]{3,100}$/.test(e.message)?e.message:'STAGE_FAILED_SEE_RUNBOOK';await save(out+'/report.json',report);throw Error(`${current}: ${report.errorCode}`);}
 finally{if(lock){await lock.close();await rm('.pipeline.lock',{force:true});}}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){review({mode:process.env.MODE||'review',scheduled:process.env.SCHEDULED==='true'}).then(x=>console.log(JSON.stringify(x))).catch(e=>{console.error(e.message);process.exitCode=1;});}
