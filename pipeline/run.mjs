import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';import {readFile,writeFile,mkdir,open,rm,copyFile} from 'node:fs/promises';
import {assertReviewMode,assertTiming,assertMedia,dueInCairo,digest,episodeSchema,sourceSchema} from './policy.mjs';
import {json,save,run,probe} from './io.mjs';import {selectTopic,script,voice,backgrounds} from './providers.mjs';
import {preflight} from './preflight.mjs';import {providerDiagnostics} from './provider-client.mjs';import {renderEpisode,visualQA,partialReview} from './render.mjs';import {layoutQA} from './layout-qa.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
async function optionalJSON(p,fallback){try{return await json(p);}catch(e){if(e.code!=='ENOENT')throw e;return fallback;}}
export async function mix(segments,dir){
 const concat=dir+'/concat.txt';await writeFile(concat,segments.map(s=>`file '${path.resolve(s.file).replaceAll("'","'\\''")}'`).join('\n'));
 const duration=segments.reduce((n,s)=>n+s.duration,0);if(duration<90||duration>180)throw Error('NARRATION_DURATION_OUT_OF_RANGE');
 await run('ffmpeg',['-y','-v','error','-f','concat','-safe','0','-i',concat,'-c:a','pcm_s16le',dir+'/narration.wav'],{timeout:120000});
 await run('ffmpeg',['-y','-v','error','-i',dir+'/narration.wav','-f','lavfi','-i',`aevalsrc=0.015*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.5*t))+0.006*sin(2*PI*(280+80*sin(t))*t):s=24000:d=${duration}`,'-filter_complex','[0:a]asplit=2[voice][control];[1:a][control]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=300[duck];[voice][duck]amix=inputs=2:duration=first:normalize=0[mix]','-map','[mix]',dir+'/mix.wav'],{timeout:120000});
 const result=await run('ffmpeg',['-hide_banner','-i',dir+'/mix.wav','-af','loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json','-f','null','-'],{timeout:120000});const m=JSON.parse(result.stderr.slice(result.stderr.lastIndexOf('{')));
 if(!Number.isFinite(Number(m.input_i)))throw Error('SILENT_AUDIO');
 const filter=`loudnorm=I=-14:TP=-1.5:LRA=9:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true`;
 await run('ffmpeg',['-y','-v','error','-i',dir+'/mix.wav','-af',filter,'-ar','48000',dir+'/audio.wav'],{timeout:120000});return duration;
}
async function activeReview(){const active=await optionalJSON('state/active-review.json',null);if(!active)return null;if(active.schema!==1||!/^[0-9TZ-]+$/.test(active.id)||digest(JSON.stringify(active.episode))!==active.scriptSha256)throw Error('ACTIVE_REVIEW_INTEGRITY_FAILED');episodeSchema.parse(active.episode);for(const s of active.topic.sources)sourceSchema.parse(s);return active;}
export async function review({mode='review',scheduled=false,topicReservationPath}={}){
 process.chdir(ROOT);const config=await json('config/channel.json'),release=await json('config/release.json');const trendsConfig=await optionalJSON('config/trends.json',null);if(trendsConfig)config.trends=trendsConfig;if(scheduled&&!dueInCairo(new Date()))return {status:'outside_cairo_slot'};
 const attemptId=new Date().toISOString().replace(/[:.]/g,'-');let active=await activeReview();if(active&&active.profile!==config.profile)throw Error('ACTIVE_REVIEW_CHANNEL_MISMATCH');
 const id=active?.id||attemptId,out=path.resolve('out',id);await mkdir(out,{recursive:true});let stageName='preflight',lock,episode=active?structuredClone(active.episode):null,topic=active?.topic;
 const report={id,attemptId,mode:'review',published:false,status:'running',resumed:Boolean(active),stages:[],limitations:['Incomplete visual previews never pass narrated-film acceptance. Human pronunciation and art-direction approval are separate.']};
 const checkpoint=async()=>{await save(out+'/report.json',report);await save(out+'/provider-diagnostics.json',providerDiagnostics());};
 async function stage(name,fn){stageName=name;console.error('STAGE_START '+name);const started=Date.now();const value=await fn();report.stages.push({name,status:'pass',seconds:(Date.now()-started)/1000});await checkpoint();return value;}
 try{
  assertReviewMode(mode,release);lock=await open('.pipeline.lock','wx');
  await stage('preflight',async()=>{await preflight({root:ROOT,needText:!active});await run('ffmpeg',['-version'],{timeout:10000});await readFile('public/fonts/Arabic-Bold.ttf');});
  const legacy=await json('state/legacy-topic-index.json'),ledger=await optionalJSON('state/topics.json',[]);const history=[...legacy,...ledger];
  if(!active){
   topic=await stage('topics',async()=>{if(!topicReservationPath)return selectTopic(config,history);const reservation=await json(topicReservationPath);const chosen=reservation.pipelineTopic||reservation;for(const s of chosen.sources)sourceSchema.parse(s);if(!chosen.sources.length)throw Error('NO_CURRENT_VERIFIED_SOURCES');return chosen;});await save(out+'/sources.json',topic);if(topic.trendDiagnostics)await save(out+'/trend-diagnostics.json',topic.trendDiagnostics);
   episode=await stage('script',()=>script(topic,config,history));await save(out+'/script.json',episode);
   active={schema:1,id,profile:config.profile,episode:structuredClone(episode),topic,scriptSha256:digest(JSON.stringify(episode)),state:'reserved'};await save(path.resolve('state/active-review.json'),active);
  }else{report.stages.push({name:'topics',status:'resumed_from_saved_source_manifest'},{name:'script',status:'resumed_from_hash_verified_script'});await save(out+'/sources.json',topic);await save(out+'/script.json',episode);}
  for(const source of topic.sources)if(!ledger.some(r=>r.run===id&&r.value===source.url))ledger.push({topicKey:episode.topicKey,value:source.url,status:'reserved',run:id});await save(path.resolve('state/topics.json'),ledger);
  const pub=path.resolve('public/generated',id);await mkdir(pub,{recursive:true});
  const segments=await stage('voice',()=>voice(episode,pub,{progressPath:out+'/voice-progress.json'}));await save(out+'/segments.json',segments);
  // Retain real successful Charon parts even when alignment later fails.
  const audioDir=path.join(out,'audio');await mkdir(audioDir,{recursive:true});const audioIndex=[];
  for(let i=0;i<segments.length;i++){const name='scene-'+i+'.wav';await copyFile(segments[i].file,path.join(audioDir,name));audioIndex.push({...segments[i],file:'audio/'+name});}
  await save(out+'/audio-index.json',audioIndex);
  await stage('align',async()=>{try{await run(process.env.PYTHON||'python',['pipeline/align.py',out+'/segments.json',out+'/alignment.json'],{timeout:1800000,maxBuffer:2000000});}catch{const diagnostic=await optionalJSON(out+'/alignment-diagnostics.json',null);throw Error(diagnostic?.code||'ALIGNMENT_PROCESS_FAILED');}const aligned=await json(out+'/alignment.json');segments.forEach((s,i)=>assertTiming(aligned[i],s.duration,s.text));episode.scenes.forEach((s,i)=>{s.words=aligned[i];s.duration=segments[i].duration;});});
  await stage('assets',async()=>{for(const s of episode.scenes){const source=topic.sources.find(v=>v.id===s.sourceId);s.sourceUrl=source.url;s.sourceLabel=new URL(source.url).hostname;}const assets=await backgrounds(episode,config,pub);await save(out+'/assets.json',assets);await writeFile(out+'/ATTRIBUTIONS.md','# Asset rights\n\nOriginal vector motion and FFmpeg synthesized bed; immutable owner logo at config/logo.json with SHA256. Fonts and provider terms: docs/LICENSES.md. Individual generated image models and cache keys are recorded in assets.json. Research sources are in sources.json and are not blanket image licenses.\n');});
  const duration=await stage('mix',()=>mix(segments,pub));const props={...episode,audio:'generated/'+id+'/audio.wav',durationInFrames:Math.ceil(duration*30)};await save(out+'/props.json',props);
  await stage('layout-qa',()=>layoutQA(props,out));await stage('render',()=>renderEpisode(props,out));
  const qa=await stage('qa',async()=>{
   const p=await probe(out+'/review.mp4');assertMedia(p);const v=await visualQA(out,'review.mp4');const levels=await run('ffmpeg',['-hide_banner','-i',out+'/review.mp4','-af','loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json','-f','null','-'],{timeout:120000});const m=JSON.parse(levels.stderr.slice(levels.stderr.lastIndexOf('{')));
   if(Math.abs(Number(m.input_i)+14)>1.2||Number(m.input_tp)>-1)throw Error('AUDIO_LOUDNESS_FAILED');if(Number(p.format.duration)+.001<duration)throw Error('NARRATION_TAIL_CLIPPED');
   const checks={schema:1,passed:true,complete:true,published:false,video_sha256:digest(await readFile(out+'/review.mp4')),logo_sha256:v.logo.sha256,width:1080,height:1920,fps:30,duration:Number(p.format.duration),integratedLUFS:Number(m.input_i),truePeak:Number(m.input_tp),transcript:'original script, strict measured word timing',layout:'all caption cues and representative scene frames passed',watermark:v.watermark,manualArtReview:'pending'};await save(out+'/qa.json',checks);return checks;
  });
  await stage('package',()=>save(out+'/metadata.json',{title:episode.title,topicKey:episode.topicKey,voice:'Charon',provider:'Gemini',sources:topic.sources.map(({text,...s})=>s),editorialMode:topic.editorialMode,video_sha256:qa.video_sha256,reviewOnly:true,approved:false}));
  ledger.filter(r=>r.run===id).forEach(r=>{r.status='review';});await save(path.resolve('state/topics.json'),ledger);await rm(path.resolve('state/active-review.json'),{force:true});report.status='review_ready';await checkpoint();return {out,status:report.status,id,video:out+'/review.mp4',qa:out+'/qa.json',topicKey:episode.topicKey};
 }catch(e){
  report.status='failed';report.failedStage=stageName;report.errorCode=e.code==='EEXIST'?'REVIEW_ALREADY_RUNNING':/^[A-Z0-9_: -]{3,100}$/.test(e.message)?e.message:'STAGE_FAILED_SEE_RUNBOOK';
  if(e.missingBindings)report.missingRepositorySecretNames=e.missingBindings;if(e.sourceDiagnostics)report.sourceDiagnostics=e.sourceDiagnostics;
  if(active){active.state='failed';active.lastFailure={stage:stageName,code:report.errorCode};await save(path.resolve('state/active-review.json'),active);}
  await checkpoint();
  if(mode==='review'&&lock&&process.env.RENDER_PARTIAL!=='false'){
   try{const retained=await optionalJSON(out+'/audio-index.json',null);let narration=null;if(episode&&retained?.length===episode.scenes.length){for(let i=0;i<retained.length;i++){const row=retained[i];if(row.text!==episode.scenes[i].text||row.voice!=='Charon'||row.provider!=='Gemini'||digest(await readFile(path.resolve(out,row.file)))!==row.sha256)throw Error('PARTIAL_AUDIO_INDEX_INTEGRITY_FAILED');}const parts=retained.map(row=>({...row,file:path.resolve(out,row.file)}));const audioDirectory=path.resolve('public/generated',id);const duration=await mix(parts,audioDirectory);narration={segments:parts,duration,audio:'generated/'+id+'/audio.wav'};await copyFile(path.join(audioDirectory,'audio.wav'),path.join(out,'audio','narration-normalized.wav'));}const partialOut=path.join(out,narration?'incomplete-with-voice':'incomplete');await mkdir(partialOut,{recursive:true});const partialProps=episode?{...episode,scenes:episode.scenes.map(s=>({...s,duration:96/episode.scenes.length,words:[]})),durationInFrames:2880,incomplete:true}:null;
    const result=await partialReview(partialOut,config,{episode,reason:report.errorCode,narration,alignmentReady:report.stages.some(stage=>stage.name==='align'&&stage.status==='pass')});report.partial={status:'rendered',path:result.file,incomplete:true};
   }catch(partialError){report.partial={status:'failed',code:/^[A-Z_]{3,100}$/.test(partialError.message)?partialError.message:'PARTIAL_RENDER_FAILED'};}
  }
  await checkpoint();throw Error(`${stageName}: ${report.errorCode}`);
 }finally{await save(out+'/attempt-'+attemptId+'.json',report);if(lock){await lock.close();await rm('.pipeline.lock',{force:true});}}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){review({mode:process.env.MODE||'review',scheduled:process.env.SCHEDULED==='true',topicReservationPath:process.env.TOPIC_RESERVATION||undefined}).then(value=>console.log(JSON.stringify(value))).catch(e=>{console.error(e.message);process.exitCode=1;});}
