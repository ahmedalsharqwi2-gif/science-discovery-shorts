import {test} from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,rm,writeFile,readFile} from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
import {GeminiClient,RateLimiter,retryAfterMs} from '../pipeline/gemini.mjs';import {VoiceStore,splitSpeech} from '../pipeline/voice-store.mjs';
const textResponse=()=>new Response(JSON.stringify({candidates:[{content:{parts:[{text:'{"ok":true}'}]}}]}),{status:200});
const audioResponse=()=>new Response(JSON.stringify({candidates:[{content:{parts:[{inlineData:{mimeType:'audio/L16;rate=24000',data:Buffer.alloc(128,1).toString('base64')}}]}}]}),{status:200});
const settings={voiceName:'Charon',style:'Egyptian Arabic',sampleRate:24000,chunking:{maxChars:420,maxSentences:2}};
function configuration(extra={}){return {rateLimit:{requestsPerMinute:60,minIntervalMs:0},retry:{maxAttemptsPerModel:3,maxTotalAttempts:6,timeoutMs:1000,maxElapsedMs:20000,baseDelayMs:100,maxDelayMs:1000,jitter:.5},models:{text:{ordered:['fixture-text-a','fixture-text-b']},voice:{ordered:['fixture-voice-a']},image:{ordered:['fixture-image-a']}},...extra};}
async function fixture(t,fetcher,config=configuration()){
 const root=await mkdtemp(path.join(os.tmpdir(),'gemini-tests-'));t.after(()=>rm(root,{recursive:true,force:true}));let now=0;const waits=[];const options={config,keyFor:()=> 'fixture-not-a-real-credential',fetcher,clock:()=>now,sleep:async ms=>{waits.push(ms);now+=ms;},random:()=>.5,cacheDir:path.join(root,'responses')};return {root,waits,options,client:new GeminiClient(options),now:()=>now};
}
test('429 Retry-After is honored and successful response is reused without another request',async t=>{
 let calls=0;const f=await fixture(t,async()=>++calls===1?new Response('',{status:429,headers:{'Retry-After':'2'}}):textResponse());
 const body={contents:[{parts:[{text:'fixture'}]}]};await f.client.generate('text',body);await new GeminiClient(f.options).generate('text',body);
 assert.equal(calls,2);assert.equal(f.waits[0],2000);assert(!JSON.stringify(f.client.events).includes('fixture-not-a-real-credential'));
});
test('503 retries use exponential backoff plus jitter and stop at the configured attempts',async t=>{
 let calls=0;const config=configuration();config.models.text.ordered=['only-fixture'];config.retry.maxAttemptsPerModel=3;
 const f=await fixture(t,async()=>{calls++;return new Response('',{status:503});},config);
 await assert.rejects(f.client.generate('text',{contents:[]}),/GEMINI_HTTP_503_EXHAUSTED/);assert.equal(calls,3);assert.deepEqual(f.waits,[125,250]);
});
test('fallback model still respects Retry-After set by the previous model',async t=>{
 const config=configuration();config.retry.maxAttemptsPerModel=1;const seen=[];
 const f=await fixture(t,async url=>{seen.push(url);return seen.length===1?new Response('',{status:429,headers:{'Retry-After':'3'}}):textResponse();},config);
 await f.client.generate('text',{contents:[]});assert.equal(seen.length,2);assert(f.waits.includes(3000));assert(seen[1].includes('fixture-text-b'));
});
test('404 falls back in configured order; authorization errors never cycle through models',async t=>{
 const seen=[];const f=await fixture(t,async url=>{seen.push(url);return seen.length===1?new Response('',{status:404}):textResponse();});await f.client.generate('text',{contents:[]});assert(seen[0].includes('fixture-text-a'));assert(seen[1].includes('fixture-text-b'));
 let calls=0;const denied=await fixture(t,async()=>{calls++;return new Response('',{status:403});});await assert.rejects(denied.client.generate('text',{}),/GEMINI_AUTHORIZATION_FAILED/);assert.equal(calls,1);
});
test('Retry-After beyond budget exhausts the key for rotation rather than sleeping',async t=>{
 const f=await fixture(t,async()=>new Response('',{status:429,headers:{'Retry-After':'3600'}}));await assert.rejects(f.client.generate('text',{}),/GEMINI_HTTP_429_EXHAUSTED/);assert.equal(f.waits.length,0);
 assert.equal(retryAfterMs('Wed, 21 Oct 2015 07:28:00 GMT',Date.parse('Wed, 21 Oct 2015 07:27:58 GMT')),2000);
});
test('limiter serializes starts and enforces the per-minute quota',async()=>{
 let now=0;const waits=[];const limiter=new RateLimiter({requestsPerMinute:2,minIntervalMs:0},()=>now,async ms=>{waits.push(ms);now+=ms;});await Promise.all([limiter.acquire(),limiter.acquire(),limiter.acquire()]);assert.equal(now,60000);assert.deepEqual(waits,[60000]);
});
test('resume keeps successful voice chunk after a later 503 and after a fresh client instance',async t=>{
 const config=configuration();config.retry.maxAttemptsPerModel=1;let failSecond=true,calls=0;
 const fetcher=async(_,options)=>{calls++;return JSON.parse(options.body).contents[0].parts[0].text.includes('second')&&failSecond?new Response('',{status:503}):audioResponse();};
 const f=await fixture(t,fetcher,config);const decoder=async(audio,target)=>writeFile(target,Buffer.from(audio.data,'base64'));const store=new VoiceStore({client:f.client,settings,cacheDir:path.join(f.root,'audio'),decoder});
 const first=await store.get('first sentence');await assert.rejects(store.get('second sentence'),/503/);const original=await readFile(first.file);failSecond=false;
 const resumed=new VoiceStore({client:new GeminiClient(f.options),settings,cacheDir:path.join(f.root,'audio'),decoder});const cached=await resumed.get('first sentence');await resumed.get('second sentence');assert.equal(calls,3);assert.equal(cached.reused,true);assert.deepEqual(await readFile(cached.file),original);
});
test('changing voice settings invalidates cache and long narration is split without losing words',async t=>{
 let calls=0;const f=await fixture(t,async()=>{calls++;return audioResponse();});const decoder=async(audio,target)=>writeFile(target,Buffer.from(audio.data,'base64'));
 const one=new VoiceStore({client:f.client,settings,cacheDir:path.join(f.root,'audio'),decoder});await one.get('same text');await new VoiceStore({client:f.client,settings:{...settings,style:'different approved style'},cacheDir:path.join(f.root,'audio'),decoder}).get('same text');assert.equal(calls,2);
 const text=Array.from({length:150},(_,i)=>'كلمة'+i).join(' ');const chunks=splitSpeech(text,{maxChars:120,maxSentences:2});assert.equal(chunks.join(' '),text);assert(chunks.every(x=>x.length<=120));
});
test('parallel requests for the same response share one request',async t=>{let calls=0;const f=await fixture(t,async()=>{calls++;return textResponse();});await Promise.all([f.client.generate('text',{same:1}),f.client.generate('text',{same:1})]);assert.equal(calls,1);});

test('model-discovery Retry-After also delays the following generation call',async t=>{
 const config=configuration();config.models.text.discover={include:'fixture-text',exclude:'tts'};let calls=0;
 const f=await fixture(t,async url=>{calls++;return url.includes('?pageSize=')?new Response('',{status:429,headers:{'Retry-After':'4'}}):textResponse();},config);
 await f.client.generate('text',{contents:[]});assert.equal(calls,2);assert(f.waits.includes(4000));
});
test('quota exhaustion rotates to the next key and cools the exhausted one',async t=>{
 const config=configuration();config.models.text.ordered=['only-fixture'];config.retry.maxAttemptsPerModel=1;config.retry.maxTotalAttempts=2;
 const seen=[],rotated=[];
 const f=await fixture(t,async(url,opts)=>{const key=opts.headers['x-goog-api-key']||'none';seen.push(key);return key==='key-b'?textResponse():new Response('',{status:429,headers:{'Retry-After':'0'}});},config);
 f.options.keysFor=()=>[{id:'a',key:'key-a'},{id:'b',key:'key-b'}];
 f.options.onKeyExhausted=(id)=>rotated.push(id);
 const client=new GeminiClient(f.options);
 await client.generate('text',{contents:[{parts:[{text:'fixture'}]}]});
 assert(seen.includes('key-a')&&seen.includes('key-b'));assert.deepEqual(rotated,['a']);
});
test('cooled-down keys are skipped; all cooled down reads as missing binding',async t=>{
 const f=await fixture(t,async()=>textResponse());
 f.options.keysFor=()=>[{id:'a',key:'key-a'}];f.options.cooledDown=()=>true;
 await assert.rejects(new GeminiClient(f.options).generate('text',{contents:[]}),/MISSING_GEMINI_BINDING/);
});
test('non-quota errors never rotate keys',async t=>{
 const config=configuration();config.models.text.ordered=['only-fixture'];config.retry.maxAttemptsPerModel=1;
 let calls=0;const rotated=[];
 const f=await fixture(t,async()=>{calls++;return new Response('',{status:503});},config);
 f.options.keysFor=()=>[{id:'a',key:'key-a'},{id:'b',key:'key-b'}];f.options.onKeyExhausted=id=>rotated.push(id);
 await assert.rejects(new GeminiClient(f.options).generate('text',{contents:[]}),/GEMINI_HTTP_503_EXHAUSTED/);
 assert.equal(rotated.length,0);
});
