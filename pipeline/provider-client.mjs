import {readFile} from 'node:fs/promises';import {createHash} from 'node:crypto';import {GeminiClient} from './gemini.mjs';
import {json,save} from './io.mjs';
let singleton;
const COOLDOWN_PATH='state/key-cooldowns.json';
const kid=k=>createHash('sha256').update(k).digest('hex').slice(0,12);
// Quota is per Google Cloud project and resets midnight Pacific. An exhausted
// key cools down until the next Pacific midnight, then re-enters the pool.
function nextPacificMidnight(now){
 const la=new Date(now).toLocaleString('en-US',{timeZone:'America/Los_Angeles',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
 const laNow=new Date(la);const offsetMs=laNow.getTime()-new Date(now).getTime();
 const nextLaMidnight=new Date(laNow);nextLaMidnight.setHours(24,0,0,0);
 return nextLaMidnight.getTime()-offsetMs;
}
function poolFrom(env,kind){
 const list=[];
 const push=(k)=>{if(k&&!list.some(x=>x.key===k))list.push({id:kid(k),key:k});};
 if(kind==='voice'){push(env.GEMINI_TTS_API_KEY);push(env.GEMINI_API_KEY);push(env.GEMINI_TTS_API_KEY_2);push(env.GEMINI_API_KEY_2);push(env.GEMINI_TTS_API_KEY_3);push(env.GEMINI_API_KEY_3);}
 else if(kind==='image'){push(env.GEMINI_IMAGE_API_KEY);push(env.GEMINI_API_KEY);push(env.GEMINI_TEXT_API_KEY);push(env.GEMINI_IMAGE_API_KEY_2);push(env.GEMINI_API_KEY_2);push(env.GEMINI_IMAGE_API_KEY_3);push(env.GEMINI_API_KEY_3);}
 else{push(env.GEMINI_TEXT_API_KEY);push(env.GEMINI_API_KEY);push(env.GEMINI_TEXT_API_KEY_2);push(env.GEMINI_API_KEY_2);push(env.GEMINI_TEXT_API_KEY_3);push(env.GEMINI_API_KEY_3);}
 return list;
}
export async function provider(){if(!singleton){const config=JSON.parse(await readFile('config/gemini.json','utf8'));let cooldowns={};try{cooldowns=await json(COOLDOWN_PATH);}catch(e){if(e.code!=='ENOENT')throw e;}
 singleton=new GeminiClient({config,keysFor:kind=>poolFrom(process.env,kind),cooledDown:(id,kind)=>(cooldowns[kind+':'+id]||0)>Date.now(),onKeyExhausted:async(id,kind)=>{cooldowns[kind+':'+id]=nextPacificMidnight(Date.now());await save(COOLDOWN_PATH,{schema:1,cooldowns});}});}return singleton;}
export function providerDiagnostics(){return singleton?{events:singleton.events,resolvedModels:Object.fromEntries(singleton.resolved)}:{events:[],resolvedModels:{}};}
