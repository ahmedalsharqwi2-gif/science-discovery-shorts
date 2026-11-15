import {XMLParser} from 'fast-xml-parser';
import {sourceSchema,normalized,digest,duplicate,assertEvidence} from './policy.mjs';
import {fetchSafe,retry,cached,json,save,probe,run} from './io.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const list=x=>Array.isArray(x)?x:x?[x]:[];
const strip=s=>String(s||'').replace(/<[^>]*>/g,' ').replace(/&[^;]+;/g,' ').replace(/\s+/g,' ').trim();
export async function sources(config){
 const now=Date.now(),out=[];const parser=new XMLParser({ignoreAttributes:false});
 for(const feed of config.feeds){try{const data=parser.parse(await(await retry(()=>fetchSafe(feed.url))).text());const items=list(data.rss?.channel?.item||data.feed?.entry);for(const item of items){const title=strip(item.title?.['#text']||item.title),raw=list(item.link).find(x=>typeof x==='object'&&x['@_rel']!=='self');const url=typeof item.link==='string'?item.link:raw?.['@_href']||item.guid?.['#text'];const text=strip(item['content:encoded']||item.description||item.summary?.['#text']||item.summary);const published=new Date(item.pubDate||item.published||item.updated).toISOString();if(now-new Date(published).getTime()>config.maxAgeHours*3600000||new Date(published).getTime()>now+3600000)continue;const v=sourceSchema.safeParse({id:digest(url||title).slice(0,12),title,url,text,published,official:feed.official});if(v.success)out.push(v.data);}}catch{ /* a failed feed does not remove other valid sources */ }}
 if(!out.length)throw Error('NO_CURRENT_VERIFIED_SOURCES');return out;
}
export async function trends(){try{const p=new XMLParser();const d=p.parse(await(await fetchSafe('https://trends.google.com/trending/rss?geo=EG')).text());return list(d.rss?.channel?.item).map(x=>strip(x.title));}catch{return [];}}
export async function selectTopic(config,history){const all=await sources(config);const trend=await trends();const candidates=all.filter(s=>!duplicate(s.url,history)&&!duplicate(s.title,history)).map(s=>({...s,score:(s.official?30:10)+Math.max(0,30-(Date.now()-new Date(s.published).getTime())/3600000)+trend.filter(t=>normalized(t).split(' ').some(w=>w.length>3&&normalized(s.title).includes(w))).length*10})).sort((a,b)=>b.score-a.score);if(!candidates.length)throw Error('NO_UNUSED_VERIFIED_TOPIC');return {selected:candidates[0],sources:all.filter(s=>s.id===candidates[0].id),trend,scoring:'official authority + freshness + observed Egypt Trends lexical overlap; no fabricated interest-volume metric'};}
async function gemini(body,key,model){if(!key)throw Error('MISSING_GEMINI_BINDING');return retry(async()=>{const r=await fetchSafe('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',{method:'POST',headers:{'Content-Type':'application/json','x-goog-api-key':key},body:JSON.stringify(body),timeout:180000});const d=await r.json();if(!d.candidates?.length)throw Error('PROVIDER_NO_CANDIDATES');return d;});}
export async function script(topic,config,history){
 const key=process.env.GEMINI_TEXT_API_KEY||process.env.GEMINI_API_KEY;
 const prompt=`Write original Egyptian Arabic white-dialect narration for ${config.name}. Return JSON only. 8-12 scenes, ONE sentence of 24-36 words per scene, total 250-360 Arabic words (90-180s narration). First sentence hook/question, last short CTA. Natural short clauses, no literal translation. Facts ONLY supported by supplied source text. Each scene has title (max 45 chars), text, summary(max 60), keyword, template(phenomenon/comparison/steps/journey/map/chart/cause), labels(2-5 Arabic terms, max 20 chars), values(0-100; ONLY actual sourced percentages, otherwise []), claim, sourceId, evidence(EXACT source quote), kind(fact/legend/illustration), expression(0-11), action(walk/run/jump/fall/point/turn/hang/sleep). For horror explicitly distinguish fact vs legend, no gore; for history acknowledge disputes and dates; news official sources only or two independent confirmations; stickman starts ماذا لو with comic escalation and ends with a real fact, use illustration kind for imaginary setups. topicKey stable semantic identity, not title hash; title,hook,cta,scenes. No made-up numbers. SOURCES: ${JSON.stringify(topic.sources)}. Forbidden previous identities: ${JSON.stringify(history.slice(-80))}`;
 const data=await gemini({contents:[{parts:[{text:prompt}]}],generationConfig:{responseMimeType:'application/json',temperature:.5}},key,process.env.GEMINI_TEXT_MODEL||'gemini-2.5-flash');
 const episode=JSON.parse(data.candidates[0].content.parts.filter(p=>p.text).map(p=>p.text).join(''));
 assertEvidence(episode,topic.sources,config.profile);if(duplicate(episode.topicKey,history))throw Error('DUPLICATE_TOPIC_IDENTITY');
 return episode;
}
export async function voice(episode,publicDir){
 const key=process.env.GEMINI_TTS_API_KEY||process.env.GEMINI_API_KEY;if(!key)throw Error('MISSING_GEMINI_TTS_BINDING');
 await mkdir(publicDir,{recursive:true});const segments=[];
 for(let i=0;i<episode.scenes.length;i++){
  const text=episode.scenes[i].text;
  const data=await cached('Charon:gemini-2.5-flash-preview-tts:'+text,()=>gemini({contents:[{parts:[{text:'اقرأ النص التالي فقط بصوت مصري طبيعي وواضح وهادي، من غير إضافة كلام، وبنفس الكلمات المكتوبة: '+text}]}],generationConfig:{responseModalities:['AUDIO'],speechConfig:{voiceConfig:{prebuiltVoiceConfig:{voiceName:'Charon'}}}}},key,'gemini-2.5-flash-preview-tts'));
  const audio=data.candidates[0].content.parts.find(p=>p.inlineData?.mimeType?.startsWith('audio/'))?.inlineData;if(!audio)throw Error('VOICE_RESPONSE_NO_AUDIO');
  const pcm=Buffer.from(audio.data,'base64'),file=publicDir+'/scene-'+i+'.wav';
  await writeFile(file+'.pcm',pcm);await run('ffmpeg',['-y','-v','error','-f','s16le','-ar','24000','-ac','1','-i',file+'.pcm',file],{timeout:30000});
  const p=await probe(file);segments.push({file,duration:Number(p.format.duration),text,sha256:digest(await readFile(file)),provider:'Gemini',voice:'Charon'});
 }
 return segments;
}
export async function backgrounds(episode,config,publicDir){
 if(config.profile!=='stickman')return [];
 const key=process.env.GEMINI_API_KEY||process.env.GEMINI_TEXT_API_KEY;
 const files=[];
 for(let i=0;i<episode.scenes.length;i++){
  const s=episode.scenes[i];const prompt=`Create an original cinematic realistic vertical environment background for an Egyptian Arabic scientific comedy animation, no people, no text, no logos, no watermark. Leave a clear foreground space for a separately animated character. Topic: ${s.title}. Scene: ${s.summary}. Warm editorial lighting, coherent environment, high quality.`;
  const data=await cached('background-v1:'+prompt,()=>gemini({contents:[{parts:[{text:prompt}]}],generationConfig:{responseModalities:['TEXT','IMAGE']}},key,process.env.GEMINI_IMAGE_MODEL||'gemini-2.5-flash-image'));
  const image=data.candidates[0].content.parts.find(p=>p.inlineData?.mimeType?.startsWith('image/'))?.inlineData;if(!image)throw Error('BACKGROUND_PROVIDER_NO_IMAGE');
  const ext=image.mimeType==='image/jpeg'?'.jpg':'.png',name='background-'+i+ext;await writeFile(publicDir+'/'+name,Buffer.from(image.data,'base64'));s.background='generated/'+publicDir.split('/').at(-1)+'/'+name;files.push({path:name,source:'Gemini original generation',license:'Provider terms apply; not asserted CC0'});
 }return files;
}
