import {createHash,randomUUID} from 'node:crypto';
import {mkdir,readFile,writeFile,rename,unlink} from 'node:fs/promises';
import path from 'node:path';

const hash=x=>createHash('sha256').update(x).digest('hex');
const stable=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v);
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
export function retryAfterMs(value,now){if(!value)return 0;const number=Number(value);return Number.isFinite(number)?Math.max(0,number*1000):Math.max(0,Date.parse(value)-now)||0;}
export class GeminiError extends Error{
 constructor(code,diagnostics=[]){super(code);this.name='GeminiError';this.code=code;this.diagnostics=diagnostics;}
}
export class RateLimiter{
 constructor({requestsPerMinute=2,minIntervalMs=30000}={},clock=Date.now,sleep=pause){this.rpm=requestsPerMinute;this.interval=minIntervalMs;this.clock=clock;this.sleep=sleep;this.starts=[];this.last=-Infinity;this.tail=Promise.resolve();if(!Number.isInteger(this.rpm)||this.rpm<1||this.rpm>60||this.interval<0)throw Error('INVALID_RATE_LIMIT');}
 async acquire(deadline=Infinity){
  const previous=this.tail;let release;this.tail=new Promise(r=>{release=r;});await previous;
  try{while(true){const now=this.clock();this.starts=this.starts.filter(t=>t>now-60000);const wait=Math.max(0,this.last+this.interval-now,this.starts.length>=this.rpm?this.starts[0]+60000-now:0);if(now+wait>=deadline)throw new GeminiError('GEMINI_RATE_LIMIT_DEADLINE');if(!wait){this.starts.push(now);this.last=now;return;}await this.sleep(wait);}}finally{release();}
 }
}
export function cacheIdentity(kind,body,settings){return hash(stable({version:2,kind,body,settings}));}
export class GeminiClient{
 constructor({config,keyFor,fetcher=fetch,sleep=pause,clock=Date.now,random=Math.random,cacheDir='.cache/gemini',onEvent=()=>{}}){
  this.config=config;this.keyFor=keyFor;this.fetcher=fetcher;this.sleep=sleep;this.clock=clock;this.random=random;this.cacheDir=cacheDir;this.onEvent=onEvent;this.events=[];this.inflight=new Map();this.queue=Promise.resolve();this.resolved=new Map();this.limiter=new RateLimiter(config.rateLimit,clock,sleep);this.notBefore=0;
  const r=config.retry;if(!r||r.maxAttemptsPerModel<1||r.maxTotalAttempts<1||r.timeoutMs<1||r.maxElapsedMs<1)throw Error('INVALID_GEMINI_RETRY_CONFIG');
 }
 event(e){const safe={...e,at:this.clock()};this.events.push(safe);this.onEvent(safe);}
 async readCache(id){try{const row=JSON.parse(await readFile(path.join(this.cacheDir,id+'.json'),'utf8'));if(row.schema!==2||row.sha256!==hash(stable(row.data)))throw Error('CACHE_CORRUPT');this.event({type:'cache_hit',id,model:row.model});return {...row.data,_pipeline:{model:row.model,cacheHit:true,cacheKey:id}};}catch(e){if(e.code==='ENOENT')return null;await unlink(path.join(this.cacheDir,id+'.json')).catch(()=>{});this.event({type:'cache_rejected',id});return null;}}
 async saveCache(id,model,data){await mkdir(this.cacheDir,{recursive:true});const target=path.join(this.cacheDir,id+'.json'),temp=target+'.'+randomUUID()+'.tmp';await writeFile(temp,JSON.stringify({schema:2,model,sha256:hash(stable(data)),data}));await rename(temp,target);}
 async cooldown(deadline){const wait=Math.max(0,this.notBefore-this.clock());if(this.clock()+wait>=deadline)throw new GeminiError('GEMINI_RETRY_AFTER_EXCEEDS_BUDGET',this.events);if(wait)await this.sleep(wait);}
 async request(model,body,key,deadline){
  await this.cooldown(deadline);
  await this.limiter.acquire(deadline);const remaining=deadline-this.clock();if(remaining<=0)throw new GeminiError('GEMINI_TOTAL_TIMEOUT',this.events);
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),Math.min(remaining,this.config.retry.timeoutMs));
  try{
   const response=await this.fetcher('https://generativelanguage.googleapis.com/v1beta/models/'+encodeURIComponent(model)+':generateContent',{method:'POST',redirect:'error',signal:controller.signal,headers:{'Content-Type':'application/json','x-goog-api-key':key},body:JSON.stringify(body)});
   if(!response.ok){const retryAfter=retryAfterMs(response.headers.get('retry-after'),this.clock());this.notBefore=Math.max(this.notBefore,this.clock()+retryAfter);return {ok:false,status:response.status,retryAfter};}
   const data=await response.json();return {ok:true,data};
  }catch(e){if(e instanceof GeminiError)throw e;return {ok:false,status:0,timeout:controller.signal.aborted};}finally{clearTimeout(timer);}
 }
 async models(kind,key,deadline){
  if(this.resolved.has(kind))return this.resolved.get(kind);
  const group=this.config.models[kind];if(!group?.ordered?.length)throw new GeminiError('GEMINI_MODELS_NOT_CONFIGURED');
  const names=[...group.ordered];
  if(group.discover){
   await this.cooldown(deadline);await this.limiter.acquire(deadline);const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),Math.min(this.config.retry.timeoutMs,Math.max(1,deadline-this.clock())));
   try{const response=await this.fetcher('https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000',{redirect:'error',signal:controller.signal,headers:{'x-goog-api-key':key}});
    if(response.status===401||response.status===403)throw new GeminiError('GEMINI_AUTHORIZATION_FAILED',this.events);
    if(response.ok){const data=await response.json();const allowed=(data.models||[]).filter(m=>m.supportedGenerationMethods?.includes('generateContent')).map(m=>m.name.replace(/^models\//,''));const accept=new RegExp(group.discover.include),reject=new RegExp(group.discover.exclude||'a^');const discovered=allowed.filter(n=>accept.test(n)&&!reject.test(n)).sort((a,b)=>b.localeCompare(a,undefined,{numeric:true}));const available=new Set(allowed);names.splice(0,names.length,...names.filter(n=>available.has(n)),...discovered.filter(n=>!names.includes(n)));this.event({type:'models_resolved',kind,models:names});}
    else {const wait=retryAfterMs(response.headers.get('retry-after'),this.clock());this.notBefore=Math.max(this.notBefore,this.clock()+wait);this.event({type:'discovery_unavailable',kind,status:response.status,retryAfterMs:wait});}
   }catch(e){if(e instanceof GeminiError)throw e;this.event({type:'discovery_unavailable',kind,status:0});}finally{clearTimeout(timer);}
  }
  if(!names.length)throw new GeminiError('GEMINI_NO_AVAILABLE_CONFIGURED_MODEL',this.events);this.resolved.set(kind,names);return names;
 }
 valid(kind,data){const parts=data.candidates?.[0]?.content?.parts||[];return kind==='text'?parts.some(p=>typeof p.text==='string'&&p.text.trim()):parts.some(p=>p.inlineData?.data&&p.inlineData.mimeType?.startsWith(kind==='voice'?'audio/':'image/'));}
 async generate(kind,body,{settings={},useCache=true}={}){
  const id=cacheIdentity(kind,body,{settings,models:this.config.models[kind]});if(this.inflight.has(id))return this.inflight.get(id);
  const task=(async()=>{if(useCache){const cached=await this.readCache(id);if(cached&&this.valid(kind,cached))return cached;}
   // One request at a time across text, voice, images and callers in this client.
   const previous=this.queue;let release;this.queue=new Promise(r=>{release=r;});await previous;
   try{if(useCache){const cached=await this.readCache(id);if(cached&&this.valid(kind,cached))return cached;}
    const key=this.keyFor(kind);if(!key)throw new GeminiError(kind==='voice'?'MISSING_GEMINI_TTS_BINDING':'MISSING_GEMINI_BINDING',this.events);
    const deadline=this.clock()+this.config.retry.maxElapsedMs,models=await this.models(kind,key,deadline);let count=0,lastStatus=0;
    for(const model of models){for(let attempt=0;attempt<this.config.retry.maxAttemptsPerModel;attempt++){
     if(++count>this.config.retry.maxTotalAttempts)throw new GeminiError(lastStatus?'GEMINI_HTTP_'+lastStatus+'_EXHAUSTED':'GEMINI_ATTEMPTS_EXHAUSTED',this.events);
     const response=await this.request(model,body,key,deadline);lastStatus=response.status||0;
     this.event({type:'attempt',kind,model,attempt:attempt+1,totalAttempt:count,status:response.ok?200:lastStatus});
     if(response.ok&&this.valid(kind,response.data)){if(useCache)await this.saveCache(id,model,response.data);return {...response.data,_pipeline:{model,cacheKey:id,cacheHit:false}};}
     if(response.ok){this.event({type:'invalid_response',kind,model});break;}
     if(response.status===401||response.status===403)throw new GeminiError('GEMINI_AUTHORIZATION_FAILED',this.events);
     if([400,404,410,422].includes(response.status))break;
     if(response.status&&response.status!==429&&response.status<500)throw new GeminiError('GEMINI_HTTP_'+response.status,this.events);
     if(attempt===this.config.retry.maxAttemptsPerModel-1)break;
     const exponential=Math.min(this.config.retry.maxDelayMs,this.config.retry.baseDelayMs*2**attempt),jitter=exponential*this.config.retry.jitter*this.random();
     const wait=Math.max(response.retryAfter||0,exponential+jitter);
     if(this.clock()+wait>=deadline)throw new GeminiError(response.retryAfter?'GEMINI_RETRY_AFTER_EXCEEDS_BUDGET':'GEMINI_TOTAL_TIMEOUT',this.events);
     this.event({type:'backoff',kind,model,status:lastStatus,waitMs:wait,retryAfterMs:response.retryAfter||0});await this.sleep(wait);
    }}
    throw new GeminiError(lastStatus?'GEMINI_HTTP_'+lastStatus+'_EXHAUSTED':'GEMINI_NO_VALID_RESPONSE',this.events);
   }finally{release();}
  })();this.inflight.set(id,task);try{return await task;}finally{this.inflight.delete(id);}
 }
}
