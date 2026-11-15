import {readFile,writeFile,mkdir,rename,copyFile} from 'node:fs/promises';import path from 'node:path';import {randomUUID,createHash} from 'node:crypto';
import {cacheIdentity} from './gemini.mjs';import {run,probe} from './io.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
export function splitSpeech(text,{maxChars=420,maxSentences=2}={}){
 const sentences=text.trim().split(/(?<=[.!?؟])\s+/u).filter(Boolean),chunks=[];let current='',count=0;
 const flush=()=>{if(current)chunks.push(current);current='';count=0;};
 for(const sentence of sentences){if(sentence.length>maxChars){flush();for(const word of sentence.split(/\s+/)){if(current&&current.length+word.length+1>maxChars)flush();current+=(current?' ':'')+word;}flush();continue;}
  if(current&&(count>=maxSentences||current.length+sentence.length+1>maxChars))flush();current+=(current?' ':'')+sentence;count++;
 }flush();if(!chunks.length)throw Error('VOICE_TEXT_EMPTY');return chunks;
}
export function voiceBody(text,settings){return {contents:[{parts:[{text:settings.style+'\nاقرأ النص التالي فقط بنفس كلماته، بدون إضافة مقدمة أو شرح:\n'+text}]}],generationConfig:{responseModalities:['AUDIO'],speechConfig:{voiceConfig:{prebuiltVoiceConfig:{voiceName:settings.voiceName}}}}};}
export async function decodeAudio(audio,target,settings){
 if(typeof audio.data!=='string'||audio.data.length>50000000||!/^[A-Za-z0-9+/=\s]+$/.test(audio.data))throw Error('VOICE_INVALID_BASE64');
 const bytes=Buffer.from(audio.data,'base64');if(bytes.length<100)throw Error('VOICE_INVALID_AUDIO');
 const raw=target+'.source';await writeFile(raw,bytes);
 if(bytes.toString('ascii',0,4)==='RIFF'&&bytes.toString('ascii',8,12)==='WAVE')await run('ffmpeg',['-y','-v','error','-i',raw,'-ar',String(settings.sampleRate),'-ac','1',target],{timeout:30000});
 else{if(!/^audio\/(L16|pcm|x-pcm)(;|$)/i.test(audio.mimeType||''))throw Error('VOICE_UNSUPPORTED_ENCODING');const rate=Number((audio.mimeType.match(/rate=(\d+)/)||[])[1]||settings.sampleRate);if(rate<8000||rate>48000)throw Error('VOICE_INVALID_SAMPLE_RATE');await run('ffmpeg',['-y','-v','error','-f','s16le','-ar',String(rate),'-ac','1','-i',raw,'-ar',String(settings.sampleRate),target],{timeout:30000});}
 const p=await probe(target);if(!p.streams.some(s=>s.codec_type==='audio')||Number(p.format.duration)<=0)throw Error('VOICE_DECODE_FAILED');
}
export class VoiceStore{
 constructor({client,settings,cacheDir='.cache/voice',decoder=decodeAudio}){this.client=client;this.settings=settings;this.cacheDir=cacheDir;this.decoder=decoder;}
 async get(text){
  const body=voiceBody(text,this.settings),id=cacheIdentity('voice',body,{settings:this.settings,models:this.client.config.models.voice});
  await mkdir(this.cacheDir,{recursive:true});const file=path.resolve(this.cacheDir,id+'.wav'),meta=file+'.json';
  try{const saved=JSON.parse(await readFile(meta,'utf8')),bytes=await readFile(file);if(saved.sha256===sha(bytes)&&saved.text_sha256===sha(text))return {...saved,file,reused:true};}catch(e){if(e.code!=='ENOENT'&&!(e instanceof SyntaxError))throw e;}
  const response=await this.client.generate('voice',body,{settings:this.settings});const audio=response.candidates?.[0]?.content?.parts?.find(p=>p.inlineData?.mimeType?.startsWith('audio/'))?.inlineData;
  if(!audio)throw Error('VOICE_RESPONSE_NO_AUDIO');const temp=file+'.'+randomUUID()+'.wav';await this.decoder(audio,temp,this.settings);const bytes=await readFile(temp);
  const saved={schema:1,cacheKey:id,sha256:sha(bytes),text_sha256:sha(text),voice:this.settings.voiceName,provider:'Gemini',model:response._pipeline?.model||'unknown',bytes:bytes.length};await rename(temp,file);await writeFile(meta+'.tmp',JSON.stringify(saved,null,2));await rename(meta+'.tmp',meta);return {...saved,file,reused:response._pipeline?.cacheHit||false};
 }
}
export async function produceVoice(episode,publicDir,{client,settings,progressPath,cacheDir='.cache/voice'}={}){
 const store=new VoiceStore({client,settings,cacheDir});await mkdir(publicDir,{recursive:true});const scenes=[],chunks=[];
 for(let i=0;i<episode.scenes.length;i++){
  const pieces=splitSpeech(episode.scenes[i].text,settings.chunking);const files=[];
  for(let j=0;j<pieces.length;j++){const chunk=await store.get(pieces[j]);files.push(chunk.file);chunks.push({scene:i,chunk:j,...chunk});if(progressPath)await writeFile(progressPath,JSON.stringify({complete:false,chunks},null,2));}
  const listFile=path.join(publicDir,'scene-'+i+'.concat.txt'),target=path.join(publicDir,'scene-'+i+'.wav');await writeFile(listFile,files.map(f=>"file '"+f.replaceAll("'","'\\''")+"'").join('\n'));
  await run('ffmpeg',['-y','-v','error','-f','concat','-safe','0','-i',listFile,'-c:a','pcm_s16le',target],{timeout:30000});
  const p=await probe(target);scenes.push({file:target,duration:Number(p.format.duration),text:episode.scenes[i].text,sha256:sha(await readFile(target)),provider:'Gemini',voice:settings.voiceName,chunks:chunks.filter(c=>c.scene===i).map(({file,...c})=>c)});
 }if(progressPath)await writeFile(progressPath,JSON.stringify({complete:true,chunks},null,2));return scenes;
}
