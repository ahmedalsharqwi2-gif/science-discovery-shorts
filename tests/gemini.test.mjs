import {test} from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,rm,writeFile,readFile} from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
import {GeminiClient,RateLimiter,retryAfterMs} from '../pipeline/gemini.mjs';import {VoiceStore,splitSpeech} from '../pipeline/voice-store.mjs';
const textResponse=()=>new Response(JSON.stringify({candidates:[{content:{parts:[{text:'{"ok":true}'}]}}]}),{status:200});
const audioResponse=()=>new Response(JSON.stringify({candidates:[{content:{parts:[{inlineData:{mimeType:'audio/L16;rate=24000',data:Buffer.alloc(128,1).toString('base64')}}]}}]}),{status:200});
const settings={voiceName:'Charon',style:'Egyptian Arabic',sampleRate:24000,chunking:{maxChars:420,maxSentences:2}};
function configuration(extra={}){return {rateLimit:{requestsPerMinute:60,minIntervalMs:0},retry:{maxAttemptsPerModel:3,maxTotalAttempts:6,timeoutMs:1000,maxElapsedMs:120000,baseDelayMs:100,maxDelayMs:1000,jitter:.5},models:{text:{ordered:['fixture-text-a','fixture-text-b']},voice:{ordered:['fixture-voice-a']},image:{ordered:['fixture-image-a']}},...extra};}
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
test('a 429 moves to the next model on the same key without a backoff sleep',async t=>{
 const seen=[];
 const f=await fixture(t,async url=>{seen.push(decodeURIComponent(String(url).match(/models\/([^:]+)/)[1]));return seen.length===1?new Response('',{status:429}):textResponse();});
 await f.client.generate('text',{contents:[]});
 assert.deepEqual(seen,['fixture-text-a','fixture-text-b']);assert.equal(f.waits.length,0);assert(!f.client.events.some(e=>e.type==='key_rotation'));
});
test('voice calls on the same key are paced at least 20 seconds apart',async t=>{
 let calls=0;const f=await fixture(t,async()=>{calls++;return audioResponse();});
 await f.client.generate('voice',{contents:[{parts:[{text:'one'}]}]});await f.client.generate('voice',{contents:[{parts:[{text:'two'}]}]});
 assert.equal(calls,2);assert(f.waits.includes(20000));assert(f.client.events.some(e=>e.type==='voice_key_pacing'&&e.waitMs===20000));
});
test('a 429 records the provider quota message and kind on the attempt event',async t=>{
 const seen=[];const quotaBody=JSON.stringify({error:{message:'Quota exceeded for metric: generate_requests_per_minute',details:[]}});
 const f=await fixture(t,async url=>{seen.push(url);return seen.length===1?new Response(quotaBody,{status:429}):textResponse();});
 await f.client.generate('text',{contents:[]});
 const failed=f.client.events.find(e=>e.type==='attempt'&&e.status===429);
 assert.equal(failed.quotaKind,'minute');assert.equal(failed.quotaMessage,'Quota exceeded for metric: generate_requests_per_minute');assert.equal(failed.keyId,'primary');
 assert(!JSON.stringify(f.client.events).includes('fixture-not-a-real-credential'));
});
test('a key pass that saw any 429 ends as 429_EXHAUSTED even when the last model 404s, so the text fallback still triggers',async t=>{
 const f=await fixture(t,async url=>String(url).includes('fixture-text-a')?new Response('',{status:429}):new Response('',{status:404}));
 await assert.rejects(f.client.generate('text',{contents:[]}),/GEMINI_HTTP_429_EXHAUSTED/);
});
test('a model that 404s is pruned for that key for the rest of the run',async t=>{
 const seen=[];const f=await fixture(t,async url=>{const m=decodeURIComponent(String(url).match(/models\/([^:]+)/)[1]);seen.push(m);return m==='fixture-text-a'?new Response('',{status:404}):textResponse();});
 await f.client.generate('text',{contents:[{parts:[{text:'one'}]}]});
 await f.client.generate('text',{contents:[{parts:[{text:'two'}]}]});
 assert.deepEqual(seen,['fixture-text-a','fixture-text-b','fixture-text-b']);
 assert(f.client.events.some(e=>e.type==='model_pruned'&&e.model==='fixture-text-a'&&e.keyId==='primary'));
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

test('a pinned voice model is the only model used; cache from another model is regenerated',async t=>{
 const config=configuration();config.models.voice={ordered:['fixture-voice-a','fixture-voice-b']};const modelsUsed=[];
 const fetcher=async url=>{const m=decodeURIComponent(String(url).match(/models\/([^:]+)/)[1]);modelsUsed.push(m);return audioResponse();};
 const f=await fixture(t,fetcher,config);const decoder=async(audio,target)=>writeFile(target,Buffer.from(audio.data,'base64'));
 const store=new VoiceStore({client:f.client,settings,cacheDir:path.join(f.root,'audio'),decoder});
 const first=await store.get('first sentence');assert.equal(first.model,'fixture-voice-a');
 f.client.pinModel('voice','fixture-voice-a');
 const second=await store.get('second sentence');assert.equal(second.model,'fixture-voice-a');
 assert.deepEqual(modelsUsed,['fixture-voice-a','fixture-voice-a']);
 const other=new VoiceStore({client:f.client,settings,cacheDir:path.join(f.root,'audio'),decoder});
 other.pinnedModel='fixture-voice-b';f.client.pinModel('voice','fixture-voice-b');
 const regen=await other.get('first sentence');
 assert.equal(regen.model,'fixture-voice-b');assert.equal(regen.reused,false);
 assert.deepEqual(modelsUsed,['fixture-voice-a','fixture-voice-a','fixture-voice-b']);
});
