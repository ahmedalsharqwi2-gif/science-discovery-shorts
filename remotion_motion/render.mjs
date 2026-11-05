import {loadTemplate} from './visual_template.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {bundle} from '@remotion/bundler';
import {selectComposition,renderMedia,renderStill} from '@remotion/renderer';
const project=path.dirname(fileURLToPath(import.meta.url));
const option=(name,fallback)=>{const i=process.argv.indexOf(name);return i<0?fallback:process.argv[i+1];};
const delivery=path.resolve(option('--delivery',path.join(project,'../professional_motion/delivery')));const output=path.resolve(option('--output-dir',path.join(project,'../professional_motion/output')));await fs.mkdir(output,{recursive:true});
for(const name of ['visuals.mp4','render.json','remotion-props.json']){try{await fs.access(path.join(output,name));throw Error('Output already exists: choose a new review directory');}catch(e){if(e.code!=='ENOENT')throw e;}}
const hash=data=>createHash('sha256').update(data).digest('hex');
const template=await loadTemplate(project);
if(template.version!==1||!template.locked||!template.safe_zone)throw Error('Locked template unavailable');
const storyBytes=await fs.readFile(path.join(delivery,'story.json'));const story=JSON.parse(storyBytes);const timing=JSON.parse(await fs.readFile(path.join(delivery,'timing.json')));const voiceBytes=await fs.readFile(path.join(delivery,'narration.wav'));
if(hash(storyBytes)!==timing.story_sha256||hash(voiceBytes)!==timing.audio_sha256)throw Error('Original voice/story timing binding changed');
if(story.profile!==template.channel||'palette' in story||story.visual_template_version!==1||!story.hook_line||!story.title_accent_word)throw Error('New locked episode contract is required');
if(!story.scenes[0].narration.startsWith(story.hook_line)||timing.caption_groups[0]?.text!==story.hook_line||timing.caption_groups[0]?.start!==0||timing.caption_groups[0]?.end>template.hook.max_seconds)throw Error('Frame-zero measured hook differs');
const minimum=story.profile==='news'?60:90;
if(!(Number.isFinite(timing.duration)&&timing.duration>minimum&&timing.duration<180)||timing.coverage<.9||timing.diagnostic_only)throw Error('Measured duration or speech evidence is insufficient');
if(['history','horror'].includes(story.profile)&&(story.fiction||!story.documented||!story.source?.url))throw Error('History/horror require documented real events');
const kinds=new Set(['photo','map','science','timeline','metric','stability','temple','platform','stickman','explainer','adventure','whatif']);
const overrides=JSON.parse(await fs.readFile(path.join(project,'visual-overrides.json'),'utf8').catch(()=> '{}'));
const scenes=timing.scenes.map((s,i)=>{const base=story.scenes[i].visual;const override=overrides[story.profile]?.[s.id]||{};if(Object.keys(override).some(k=>!['kind','asset','asset_label','detail'].includes(k)))throw Error('Visual overrides cannot rewrite narration');const visual={...base,...override};if(!kinds.has(visual.kind)||s.id!==story.scenes[i].id||!(s.end>s.start))throw Error('Unimplemented or inconsistent authored shot');return {...s,...visual,title_accent_word:story.scenes[i].title_accent_word};});
await fs.mkdir(path.join(project,'public'),{recursive:true});
await fs.copyFile(path.join(delivery,'narration.wav'),path.join(project,'public/narration.wav'));
const publicationBytes=await fs.readFile(path.join(delivery,'publication.json')).catch(()=>null);
const publication=publicationBytes?JSON.parse(publicationBytes):null;
if(publication&&(publication.story_sha256!==hash(storyBytes)||publication.profile!==story.profile||publication.cover_frame!==6||publication.cover_offset_ms!==200||publication.opening_frames!==18||publication.fps!==30))throw Error('Publication package does not match the episode');
const identityBytes=await fs.readFile(path.join(project,'public/identity-plan.json')).catch(()=>null);const identityPlan=identityBytes?JSON.parse(identityBytes):null;
if(identityPlan&&(identityPlan.story_sha256!==hash(storyBytes)||identityPlan.audio_sha256!==hash(voiceBytes)||identityPlan.identity.profile!==story.profile))throw Error('Channel direction is not bound to this exact retained episode');
if(identityPlan&&story.profile==='news')scenes.forEach((s,i)=>{if(!s.labels?.length)s.labels=identityPlan.scenes[i].labels;});
const episode={hook_line:story.hook_line,title_accent_word:story.title_accent_word,source:{...story.source,host:story.source?.url?new URL(story.source.url).hostname:undefined},...(identityPlan?{identity_plan:identityPlan}:{}),cover_text:publication?.cover_text,publication_title:publication?.title,profile:story.profile,series:story.series,title:story.title,duration:timing.duration,scenes,caption_groups:timing.caption_groups,audio:'narration.wav',review_only:true,hashtags:(story.hashtags||[]).slice(0,5),source_date:story.source?.published?.slice(0,10)};
await fs.writeFile(path.join(output,'remotion-props.json'),JSON.stringify({episode},null,2));
const serveUrl=await bundle({entryPoint:path.join(project,'src/index.ts'),publicDir:path.join(project,'public'),onProgress:()=>{}});
const inputProps={episode};const chromiumOptions={gl:'swangle'};const browserExecutable=process.env.CHROMIUM_PATH||undefined;
const composition=await selectComposition({serveUrl,browserExecutable,id:'Documentary',inputProps,chromiumOptions});
if(composition.width!==1080||composition.height!==1920||composition.fps!==30||composition.durationInFrames!==Math.ceil(timing.duration*30))throw Error('Remotion full-film metadata differs from original timing');
const stills=process.argv.includes('--stills');
if(stills&&publication){await renderStill({serveUrl,browserExecutable,composition,inputProps,output:path.join(output,'cover.png'),frame:publication.cover_frame,chromiumOptions});await fs.writeFile(path.join(output,'publication.json'),publicationBytes);}
if(stills){for(let i=0;i<scenes.length;i++){const frame=Math.round((scenes[i].start+Math.min(2,(scenes[i].end-scenes[i].start)/2))*30);await renderStill({serveUrl,browserExecutable,composition,inputProps,output:path.join(output,`remotion-shot-${i+1}.png`),frame,chromiumOptions});}}
else await renderMedia({serveUrl,browserExecutable,composition,inputProps,codec:'h264',crf:17,muted:true,pixelFormat:'yuv420p',concurrency:2,outputLocation:path.join(output,'visuals.mp4'),chromiumOptions,onProgress:({progress})=>{if(Math.floor(progress*100)%10===0)process.stdout.write('Rendered '+Math.floor(progress*100)+'%\r');}});
const sourceNames=[...(await fs.readdir(path.join(project,'src'))).filter(n=>/\.tsx?$/.test(n)).sort().map(n=>'src/'+n),'render.mjs','package.json','package-lock.json','visual-overrides.json'];if(identityPlan)sourceNames.push('../professional_motion/procedural_story.js','../professional_motion/locked_identity_stage.js','../config/visual_template.json','../professional_motion/cinema.js','../professional_motion/science_shots.js');const sources={};for(const name of sourceNames)sources[name]=hash(await fs.readFile(path.join(project,name)));
const coverBytes=publication?await fs.readFile(path.join(output,'cover.png')).catch(()=>null):null;
if(publication&&coverBytes&&hash(await fs.readFile(path.join(output,'publication.json')))!==hash(publicationBytes))throw Error('Cover package changed between still and full render');
const report={publication_sha256:publicationBytes?hash(publicationBytes):undefined,cover_sha256:coverBytes?hash(coverBytes):undefined,pipeline:'remotion',renderer:'Remotion4.0.540',duration:timing.duration,fps:30,width:1080,height:1920,originalVoice:true,review:true,story_sha256:hash(storyBytes),audio_sha256:hash(voiceBytes),total_frames:composition.durationInFrames,rendered_frames:stills?scenes.length:composition.durationInFrames,render_mode:stills?'stills':'video',visual_style:identityPlan?.identity?.name||'remotion-documentary',identity_version:identityPlan?.version,identity_plan_sha256:identityBytes?hash(identityBytes):undefined,burned_hashtags:episode.hashtags,errors:[],renderer_sources:sources};
await fs.writeFile(path.join(output,stills?'remotion-stills.json':'render.json'),JSON.stringify(report,null,2)+'\n');
if(hash(await fs.readFile(path.join(delivery,'story.json')))!==report.story_sha256||hash(await fs.readFile(path.join(delivery,'narration.wav')))!==report.audio_sha256)throw Error('Source changed while rendering');
console.log(stills?'Eight real-timing scene images rendered':'Every original narration frame rendered');


if(!stills){const {audit}=await import('./safe_audit.mjs');await audit({serveUrl,composition,inputProps,browserExecutable,chromiumOptions,output,video:path.join(output,'visuals.mp4')});}
