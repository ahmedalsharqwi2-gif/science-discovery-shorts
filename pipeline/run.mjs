import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';import {readFile,writeFile,mkdir,open,rm,copyFile} from 'node:fs/promises';
import {assertReviewMode,assertTiming,assertMedia,dueInCairo,digest,episodeSchema,sourceSchema} from './policy.mjs';
import {json,save,run,probe} from './io.mjs';import {selectTopic,script,voice,backgrounds} from './providers.mjs';
import {drawplan} from './drawplan.mjs';
import {preflight} from './preflight.mjs';import {providerDiagnostics} from './provider-client.mjs';import {renderEpisode,visualQA,partialReview} from './render.mjs';import {layoutQA} from './layout-qa.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
async function optionalJSON(p,fallback){try{return await json(p);}catch(e){if(e.code!=='ENOENT')throw e;return fallback;}}
async function mixInner(segments,dir){
 const concat=dir+'/concat.txt';await writeFile(concat,segments.map(s=>`file '${path.resolve(s.file).replaceAll("'","'\\''")}'`).join('\n'));
 const duration=segments.reduce((n,s)=>n+s.duration,0);if(duration<90||duration>180)throw Error('NARRATION_DURATION_OUT_OF_RANGE');
 await run('ffmpeg',['-y','-v','error','-f','concat','-safe','0','-i',concat,'-c:a','pcm_s16le',dir+'/narration.wav'],{timeout:120000});
 await run('ffmpeg',['-y','-v','error','-i',dir+'/narration.wav','-c:a','pcm_s16le',dir+'/mix.wav'],{timeout:120000}); // voice-only: synthetic drone bed removed (owner direction)
 const result=await run('ffmpeg',['-hide_banner','-i',dir+'/mix.wav','-af','loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json','-f','null','-'],{timeout:120000});const loudText=result.stderr.includes('{')?result.stderr:result.stdout;const loudSlice=loudText.slice(loudText.lastIndexOf('{'));const loudJson=loudSlice.slice(0,loudSlice.lastIndexOf('}')+1);if(!loudJson.includes('{'))throw Error('MIX_LOUDNORM_UNMEASURED');const m=JSON.parse(loudJson);
 if(!Number.isFinite(Number(m.input_i)))throw Error('SILENT_AUDIO');
 const filter=`loudnorm=I=-14:TP=-1.5:LRA=9:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true`;
 await run('ffmpeg',['-y','-v','error','-i',dir+'/mix.wav','-af',filter,'-ar','48000',dir+'/audio.wav'],{timeout:120000});return duration;
}
export async function mix(segments,dir,diagPath){try{return await mixInner(segments,dir);}catch(e){if(diagPath&&!/^[A-Z0-9_: -]{3,100}$/.test(String(e&&e.message||e))){try{await save(diagPath,{schema:1,message:String(e&&e.message||e).slice(0,600),stderr:String(e&&e.stderr||'').slice(-3000),stdout:String(e&&e.stdout||'').slice(-1000)});}catch{}}throw e;}}
async function activeReview(){const active=await optionalJSON('state/active-review.json',null);if(!active)return null;if(active.schema!==1||!/^[0-9TZ-]+$/.test(active.id)||digest(JSON.stringify(active.episode))!==active.scriptSha256)throw Error('ACTIVE_REVIEW_INTEGRITY_FAILED');episodeSchema.parse(active.episode);for(const s of active.topic.sources)sourceSchema.parse(s);return active;}
export async function review({mode='review',scheduled=false,topicReservationPath}={}){
 process.chdir(ROOT);const config=await json('config/channel.json'),release=await json('config/release.json');const trendsConfig=await optionalJSON('config/trends.json',null);if(trendsConfig)config.trends=trendsConfig;if(scheduled&&!dueInCairo(new Date()))return {status:'outside_cairo_slot'};
 const attemptId=new Date().toISOString().replace(/[:.]/g,'-');let active=await activeReview();if(active&&active.profile!==config.profile)throw Error('ACTIVE_REVIEW_CHANNEL_MISMATCH');
 let id=active?.id||attemptId,out=path.resolve('out',id);await mkdir(out,{recursive:true});let stageName='preflight',lock,episode=active?structuredClone(active.episode):null,topic=active?.topic;
 const report={id,attemptId,mode:'review',published:false,status:'running',resumed:Boolean(active),stages:[],limitations:['Incomplete visual previews never pass narrated-film acceptance. Human pronunciation and art-direction approval are separate.']};
 const checkpoint=async()=>{await save(out+'/report.json',report);await save(out+'/provider-diagnostics.json',providerDiagnostics());};
 async function stage(name,fn){stageName=name;console.error('STAGE_START '+name);const started=Date.now();const value=await fn();report.stages.push({name,status:'pass',seconds:(Date.now()-started)/1000});await checkpoint();return value;}
 const ROLLABLE=new Set(['topics','script','voice','align']);let rolls=0,rollingNow=false;
 while(true){try{
  assertReviewMode(mode,release);if(!lock)lock=await open('.pipeline.lock','wx');
  await stage('preflight',async()=>{await preflight({root:ROOT,needText:!active});await run('ffmpeg',['-version'],{timeout:10000});await readFile('public/fonts/Arabic-Bold.ttf');});
  const legacy=await json('state/legacy-topic-index.json'),ledger=await optionalJSON('state/topics.json',[]);const history=[...legacy,...ledger];
  if(active&&active.state==='failed'&&(active.lastFailure?.repeat||0)>=1){const retiredId=active.id;ledger.filter(x=>x.run===retiredId).forEach(x=>{x.status='retired';});await save(path.resolve('state/topics.json'),ledger);report.retiredEpisode={id:retiredId,stage:active.lastFailure.stage,code:active.lastFailure.code,reason:'Same stage and code failed on consecutive resumed attempts; retained audio and hash-locked script are immutable, so the deterministic failure cannot clear. Episode retired; a fresh episode is rolled through the same gates.'};await rm(path.resolve('state/active-review.json'),{force:true});active=null;episode=null;topic=null;id=attemptId;out=path.resolve('out',id);await mkdir(out,{recursive:true});report.id=attemptId;report.resumed=false;}
  if(!active){
   topic=await stage('topics',async()=>{if(!topicReservationPath)return selectTopic(config,history);const reservation=await json(topicReservationPath);const chosen=reservation.pipelineTopic||reservation;for(const s of chosen.sources)sourceSchema.parse(s);if(!chosen.sources.length)throw Error('NO_CURRENT_VERIFIED_SOURCES');return chosen;});await save(out+'/sources.json',topic);if(topic.trendDiagnostics)await save(out+'/trend-diagnostics.json',topic.trendDiagnostics);
   episode=await stage('script',()=>script(topic,config,history,{diagnosticsPath:out+'/script-diagnostics.json'}));await save(out+'/script.json',episode);
   active={schema:1,id,profile:config.profile,episode:structuredClone(episode),topic,scriptSha256:digest(JSON.stringify(episode)),state:'reserved'};await save(path.resolve('state/active-review.json'),active);
  }else{report.stages.push({name:'topics',status:'resumed_from_saved_source_manifest'},{name:'script',status:'resumed_from_hash_verified_script'});await save(out+'/sources.json',topic);await save(out+'/script.json',episode);}
  for(const source of topic.sources)if(!ledger.some(r=>r.run===id&&r.value===source.url))ledger.push({topicKey:episode.topicKey,value:source.url,status:'reserved',run:id});await save(path.resolve('state/topics.json'),ledger);
  const pub=path.resolve('public/generated',id);await mkdir(pub,{recursive:true});
  let segments=await stage('voice',()=>voice(episode,pub,{progressPath:out+'/voice-progress.json'}));await save(out+'/segments.json',segments);
  let alignedOk=false,alignErr=null;
  for(let repair=0;repair<2&&!alignedOk;repair++){
   if(repair>0){segments=await stage('voice-repair-'+repair,()=>voice(episode,pub,{progressPath:out+'/voice-progress.json',cacheDir:'.cache/voice-repair-'+repair}));await save(out+'/segments.json',segments);}
   // Retain real successful Charon parts even when alignment later fails.
   const audioDir=path.join(out,'audio');await mkdir(audioDir,{recursive:true});const audioIndex=[];
   for(let i=0;i<segments.length;i++){const name='scene-'+i+'.wav';await copyFile(segments[i].file,path.join(audioDir,name));audioIndex.push({...segments[i],file:'audio/'+name});}
   await save(out+'/audio-index.json',audioIndex);
   try{await stage(repair?'align-repair-'+repair:'align',async()=>{try{await run(process.env.PYTHON||'python',['pipeline/align.py',out+'/segments.json',out+'/alignment.json'],{timeout:1800000,maxBuffer:2000000});}catch{const diagnostic=await optionalJSON(out+'/alignment-diagnostics.json',null);throw Error(diagnostic?.code||'ALIGNMENT_PROCESS_FAILED');}const aligned=await json(out+'/alignment.json');segments.forEach((s,i)=>assertTiming(aligned[i],s.duration,s.text));episode.scenes.forEach((s,i)=>{s.words=aligned[i];s.duration=segments[i].duration;});});alignedOk=true;}
   catch(e){alignErr=e;report.limitations.push('align '+(repair?'repair failed':'failed')+' ('+String(e&&e.message||e)+')'+(repair?'; repair budget exhausted':'; re-narrating once with fresh synthesis'));}
  }
  if(!alignedOk)throw alignErr;
  await stage('assets',async()=>{for(const s of episode.scenes){const source=topic.sources.find(v=>v.id===s.sourceId);s.sourceUrl=source.url;s.sourceLabel=new URL(source.url).hostname;}const assets=await backgrounds(episode,config,pub);await save(out+'/assets.json',assets);await writeFile(out+'/ATTRIBUTIONS.md','# Asset rights\n\nOriginal vector motion and FFmpeg synthesized bed; immutable owner logo at config/logo.json with SHA256. Fonts and provider terms: docs/LICENSES.md. Individual generated image models and cache keys are recorded in assets.json. Research sources are in sources.json and are not blanket image licenses.\n');});
  let paperPlan=null;
  if(config.paper){const planned=await stage('drawplan',async()=>{const r=await drawplan(episode,config,{diagnosticsPath:out+'/drawplan-diagnostics.json'});await save(out+'/drawplan.json',{schema:1,plan:r.plan,drawModel:r.drawModel});return r.plan;});paperPlan=planned;} /* fail closed: a paper channel never renders the classic template; a drawplan failure fails the run with its DRAWPLAN_* code */
  const duration=await stage('mix',()=>mix(segments,pub,out+'/mix-diagnostics.json'));const props={...episode,channelName:config.name,mascot:config.mascot!==false,audio:'generated/'+id+'/audio.wav',durationInFrames:Math.ceil(duration*30),...(paperPlan?{paper:{plan:paperPlan}}:{})};await save(out+'/props.json',props);
  await stage('layout-qa',()=>layoutQA(props,out));await stage('render',()=>renderEpisode(props,out));
  const qa=await stage('qa',async()=>{
   const p=await probe(out+'/review.mp4');assertMedia(p);const v=await visualQA(out,'review.mp4',{paper:Boolean(paperPlan)});const levels=await run('ffmpeg',['-hide_banner','-i',out+'/review.mp4','-af','loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json','-f','null','-'],{timeout:120000});const qaLoud=levels.stderr.slice(levels.stderr.lastIndexOf('{'));const m=JSON.parse(qaLoud.slice(0,qaLoud.lastIndexOf('}')+1));
   if(Math.abs(Number(m.input_i)+14)>1.2||Number(m.input_tp)>-1)throw Error('AUDIO_LOUDNESS_FAILED');if(Number(p.format.duration)+.001<duration)throw Error('NARRATION_TAIL_CLIPPED');
   const checks={schema:1,passed:true,complete:true,published:false,video_sha256:digest(await readFile(out+'/review.mp4')),logo_sha256:v.logo.sha256,width:1080,height:1920,fps:30,duration:Number(p.format.duration),integratedLUFS:Number(m.input_i),truePeak:Number(m.input_tp),transcript:'original script, strict measured word timing',layout:'all caption cues and representative scene frames passed',watermark:v.watermark,manualArtReview:'pending'};await save(out+'/qa.json',checks);return checks;
  });
  await stage('package',()=>save(out+'/metadata.json',{title:episode.title,topicKey:episode.topicKey,voice:'Charon',provider:'Gemini',sources:topic.sources.map(({text,...s})=>s),editorialMode:topic.editorialMode,video_sha256:qa.video_sha256,reviewOnly:true,approved:false}));
  ledger.filter(r=>r.run===id).forEach(r=>{r.status='review';});await save(path.resolve('state/topics.json'),ledger);await rm(path.resolve('state/active-review.json'),{force:true});report.status='review_ready';await checkpoint();return {out,status:report.status,id,video:out+'/review.mp4',qa:out+'/qa.json',topicKey:episode.topicKey};
 }catch(e){
  const failCode=e.code==='EEXIST'?'REVIEW_ALREADY_RUNNING':/^[A-Z0-9_: -]{3,100}$/.test(e.message)?e.message:'STAGE_FAILED_SEE_RUNBOOK';
  // Recovery ladder: on a content-stage failure with a live episode, retire it
  // and roll a fresh topic in the SAME run (max 2 rolls), so a gate reject
  // never reads as a stall. Thresholds themselves are untouched.
  if(ROLLABLE.has(stageName.replace(/-repair-\d+$/,''))&&rolls<2&&mode==='review'&&failCode!=='REVIEW_ALREADY_RUNNING'){
   {const ledgerReject=await optionalJSON('state/topics.json',[]);let rejectChanged=false;
   if(topic&&Array.isArray(topic.sources))for(const s of topic.sources){if(s&&s.url&&!ledgerReject.some(r=>r.value===s.url)){ledgerReject.push({topicKey:e.topicKey||(episode&&episode.topicKey)||undefined,value:s.url,status:'rejected',reason:failCode,run:id});rejectChanged=true;}}
   if(e.topicKey&&!ledgerReject.some(r=>r.topicKey===e.topicKey)){ledgerReject.push({topicKey:e.topicKey,value:'identity:'+e.topicKey,status:'rejected',reason:failCode,run:id});rejectChanged=true;}
   if(rejectChanged)await save(path.resolve('state/topics.json'),ledgerReject);}
   rolls++;
   const ledgerNow=await optionalJSON('state/topics.json',[]);ledgerNow.filter(x=>x.run===id).forEach(x=>{x.status='retired';});await save(path.resolve('state/topics.json'),ledgerNow);
   await rm(path.resolve('state/active-review.json'),{force:true});
   (report.rolled=report.rolled||[]).push({id,stage:stageName,code:failCode,roll:rolls});
   active=null;episode=null;topic=null;
   id=new Date().toISOString().replace(/[:.]/g,'-');out=path.resolve('out',id);await mkdir(out,{recursive:true});
   report.id=id;report.resumed=false;report.stages.push({name:'roll',status:'rolled_fresh_topic',roll:rolls,fromStage:stageName,code:failCode});
   stageName='topics';rollingNow=true;continue;
  }
  report.status='failed';report.failedStage=stageName;report.errorCode=failCode;
  if(e.missingBindings)report.missingRepositorySecretNames=e.missingBindings;if(e.sourceDiagnostics)report.sourceDiagnostics=e.sourceDiagnostics;
  if(active){active.state='failed';const prev=active.lastFailure;active.lastFailure={stage:stageName,code:report.errorCode,repeat:prev&&prev.stage===stageName&&prev.code===report.errorCode?(prev.repeat||0)+1:0};await save(path.resolve('state/active-review.json'),active);}
  await checkpoint();
  if(mode==='review'&&lock&&process.env.RENDER_PARTIAL!=='false'){
   try{const retained=await optionalJSON(out+'/audio-index.json',null);let narration=null;if(episode&&retained?.length===episode.scenes.length){for(let i=0;i<retained.length;i++){const row=retained[i];if(row.text!==episode.scenes[i].text||row.voice!=='Charon'||row.provider!=='Gemini'||digest(await readFile(path.resolve(out,row.file)))!==row.sha256)throw Error('PARTIAL_AUDIO_INDEX_INTEGRITY_FAILED');}const parts=retained.map(row=>({...row,file:path.resolve(out,row.file)}));const audioDirectory=path.resolve('public/generated',id);const duration=await mix(parts,audioDirectory,out+'/mix-diagnostics.json');narration={segments:parts,duration,audio:'generated/'+id+'/audio.wav'};await copyFile(path.join(audioDirectory,'audio.wav'),path.join(out,'audio','narration-normalized.wav'));}const partialOut=path.join(out,narration?'incomplete-with-voice':'incomplete');await mkdir(partialOut,{recursive:true});const partialProps=episode?{...episode,scenes:episode.scenes.map(s=>({...s,duration:96/episode.scenes.length,words:[]})),durationInFrames:2880,incomplete:true}:null;
    const result=await partialReview(partialOut,config,{episode,reason:report.errorCode,narration,alignmentReady:report.stages.some(stage=>stage.name==='align'&&stage.status==='pass')});report.partial={status:'rendered',path:result.file,incomplete:true};
   }catch(partialError){report.partial={status:'failed',code:/^[A-Z_]{3,100}$/.test(partialError.message)?partialError.message:'PARTIAL_RENDER_FAILED'};}
  }
  await checkpoint();throw Error(`${stageName}: ${report.errorCode}`);
 }finally{await save(out+'/attempt-'+attemptId+'.json',report);if(rollingNow){rollingNow=false;}else if(lock){await lock.close();await rm('.pipeline.lock',{force:true});}}
}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){review({mode:process.env.MODE||'review',scheduled:process.env.SCHEDULED==='true',topicReservationPath:process.env.TOPIC_RESERVATION||undefined}).then(value=>console.log(JSON.stringify(value))).catch(e=>{console.error(e.message);process.exitCode=1;});}
