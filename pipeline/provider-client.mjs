import {readFile} from 'node:fs/promises';import {createHash} from 'node:crypto';import {GeminiClient} from './gemini.mjs';import {OpenAiCompatTextClient} from './fallback-text.mjs';
import {json,save} from './io.mjs';
let singleton;
const COOLDOWN_PATH='state/key-cooldowns.json';
const RESOLUTION_PATH='state/model-resolution.json';
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
 return spreadPoolOrder(list,(process.env.GITHUB_RUN_ID||'')+':'+(process.env.GITHUB_RUN_ATTEMPT||''));
}

// Concurrent runs across the channels share each Google Cloud project, and
// quota caps are per project. Starting every run on slot 1 concentrates
// minute-level bursts on one project; rotate the pool deterministically per
// CI run (randomly outside CI) so bursts spread across projects.
export function spreadPoolOrder(list,seed){
 if(list.length<2)return list.slice();
 const offset=(seed&&seed!==':'?createHash('sha256').update(String(seed)).digest()[0]:Math.floor(Math.random()*256))%list.length;
 return list.slice(offset).concat(list.slice(0,offset));
}

// Free-tier text fallback chain: used only when the whole Gemini pool is
// quota-exhausted or benched, and only for 'text' calls (topics/script/
// drawplan). Voice and image never fall back. All downstream gates (evidence,
// lint, schema validation) run unchanged, so a weaker fallback can only fail
// closed, never ship lower-quality output silently.
export class FallbackTextChain{
 constructor(primary,fallback){this.primary=primary;this.fallback=fallback?(Array.isArray(fallback)?fallback:[fallback]):[];}
 get config(){return this.primary.config;}
 get events(){return this.primary.events;}
 get resolved(){return this.primary.resolved;}
 async generate(kind,body,opts){
  try{return await this.primary.generate(kind,body,opts);}
  catch(e){
   const exhausted=e&&(e.code==='GEMINI_HTTP_429_EXHAUSTED'||e.code==='MISSING_GEMINI_BINDING');
   if(kind==='text'&&this.fallback.length&&exhausted){
    if(e.quotaMessage)console.error('gemini pool exhausted:',e.code,e.quotaMessage);
    let last;
    for(const fb of this.fallback){
     try{const out=await fb.generate(kind,body,opts);out._pipeline={...(out._pipeline||{}),fallback:true};return out;}
     catch(fe){last=fe;if(fe&&fe.snippet)console.error('fallback provider rejected:',fe.status||'?',fe.snippet);}
    }
    throw last;
   }
   throw e;
  }
 }
}
// Build the ordered fallback chain from config/fallback-text.json. Schema 2 is
// a providers array (tried in order); the schema-1 single-provider form still
// works. A provider whose env key is unset is skipped, so a repo missing one
// secret simply falls through to the next provider.
export function fallbackClientsFrom(fb,env){
 const defs=Array.isArray(fb.providers)&&fb.providers.length?fb.providers:[fb];
 return defs.filter(d=>d&&d.baseUrl&&d.model&&d.apiKeyEnv&&env[d.apiKeyEnv])
  .map(d=>new OpenAiCompatTextClient({baseUrl:d.baseUrl,model:d.model,apiKey:env[d.apiKeyEnv],jsonMode:d.jsonMode!==false}));
}
export async function provider(){if(!singleton){const config=JSON.parse(await readFile('config/gemini.json','utf8'));let cooldowns={};try{cooldowns=await json(COOLDOWN_PATH);}catch(e){if(e.code!=='ENOENT')throw e;}
 singleton=new GeminiClient({config,keysFor:kind=>poolFrom(process.env,kind),cooledDown:(id,kind)=>(cooldowns[kind+':'+id]||0)>Date.now(),onKeyExhausted:async(id,kind,quotaKind)=>{const until=quotaKind==='minute'?Date.now()+5*60*1000:nextPacificMidnight(Date.now());cooldowns[kind+':'+id]=until;await save(COOLDOWN_PATH,{schema:1,cooldowns});},onEvent:e=>{if(e.type==='models_resolved')(async()=>{let cur={schema:1,resolutions:{}};try{cur=await json(RESOLUTION_PATH);}catch(err){if(err.code!=='ENOENT')throw err;}cur.resolutions=cur.resolutions||{};cur.resolutions[e.kind]={at:Date.now(),models:e.models};await save(RESOLUTION_PATH,cur);})().catch(err=>console.error('model-resolution cache save failed:',err&&err.message));}});
 try{const res=await json(RESOLUTION_PATH);for(const [kind,row] of Object.entries(res.resolutions||{}))if(row&&Array.isArray(row.models)&&row.models.length&&Date.now()-row.at<12*60*60*1000)singleton.resolved.set(kind,row.models);}catch(e){if(e.code!=='ENOENT')throw e;}
 try{const fb=await json('config/fallback-text.json');if(fb.enabled){const clients=fallbackClientsFrom(fb,process.env);if(clients.length)singleton=new FallbackTextChain(singleton,clients);}}catch(e){if(e.code!=='ENOENT')throw e;}
 }return singleton;}
export function summarizeAttempts(events){const counts={};for(const e of events||[]){if(e.type==='attempt'){const k=e.kind+':'+e.model;counts[k]=(counts[k]||0)+1;}}return counts;}
export function providerDiagnostics(){return singleton?{events:singleton.events,resolvedModels:Object.fromEntries(singleton.resolved),modelAttempts:summarizeAttempts(singleton.events)}:{events:[],resolvedModels:{},modelAttempts:{}};}
