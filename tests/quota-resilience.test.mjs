import {test} from 'node:test';import assert from 'node:assert/strict';
import {classifyQuota} from '../pipeline/gemini.mjs';
import {distributeWords,assertTiming} from '../pipeline/policy.mjs';
import {FallbackTextChain,fallbackClientsFrom,spreadPoolOrder,summarizeAttempts} from '../pipeline/provider-client.mjs';
import {OpenAiCompatTextClient} from '../pipeline/fallback-text.mjs';

test('summarizeAttempts counts attempts per kind and model',()=>{
 const counts=summarizeAttempts([{type:'attempt',kind:'text',model:'a'},{type:'attempt',kind:'text',model:'a'},{type:'attempt',kind:'voice',model:'b'},{type:'key_rotation',kind:'text'}]);
 assert.deepEqual(counts,{'text:a':2,'voice:b':1});
 assert.deepEqual(summarizeAttempts(undefined),{});
});

test('spreadPoolOrder rotates the key pool deterministically per run seed',()=>{
 const pool=[{id:'a'},{id:'b'},{id:'c'}];
 const first=spreadPoolOrder(pool,'44700732990:1');
 assert.deepEqual(first,spreadPoolOrder(pool,'44700732990:1'));
 assert.deepEqual([...first].sort((x,y)=>x.id.localeCompare(y.id)),pool);
 assert.deepEqual(spreadPoolOrder([{id:'a'}],'1:1'),[{id:'a'}]);
 const starters=new Set(['1:1','2:1','3:1','4:1','5:1','6:1'].map(s=>spreadPoolOrder(pool,s)[0].id));
 assert(starters.size>1);
});

test('classifyQuota distinguishes per-minute from per-day quota',()=>{
 assert.equal(classifyQuota({error:{message:'Quota exceeded for metric: generate_requests_per_minute',details:[]}}),'minute');
 assert.equal(classifyQuota({error:{message:'',details:[{violations:[{quotaMetric:'generate_requests_per_day'}]}]}}),'day');
 assert.equal(classifyQuota({error:{message:'Resource has been exhausted (e.g. check quota).'}}),'unknown');
 assert.equal(classifyQuota(null),'unknown');
 assert.equal(classifyQuota({}),'unknown');
});

test('distributeWords yields monotonic spans satisfying assertTiming',()=>{
 const text='\u0648\u0627\u062d\u062f \u0627\u062a\u0646\u064a\u0646 \u062a\u0644\u0627\u062a\u0629 \u0623\u0631\u0628\u0639\u0629 \u062e\u0645\u0633\u0629 \u0633\u062a\u0629 \u0633\u0628\u0639\u0629 \u062a\u0645\u0627\u0646\u064a\u0629';
 for(const dur of [1.5,12.34,187.9]){
  const words=distributeWords(text,dur);
  assertTiming(words,dur,text);
  assert.equal(words[0].start,0);
  assert.ok(words.at(-1).end<=dur+0.05);
 }
});

test('fallback rejection keeps a machine-code message and carries the provider body on .snippet',async()=>{
 const client=new OpenAiCompatTextClient({baseUrl:'https://fallback.example/v1',model:'m',apiKey:'k',fetcher:async()=>new Response('{"error":{"message":"rate limit exceeded, 50 requests per day"}}',{status:429})});
 const err=await client.generate('text',{contents:[{parts:[{text:'x'}]}]}).then(()=>null,e=>e);
 assert.equal(err.message,'FALLBACK_HTTP_429');assert.equal(err.status,429);assert(err.snippet.includes('50 requests per day'));
});

test('FallbackTextChain falls back only for text when the pool is exhausted',async()=>{
 const boom=Object.assign(new Error('boom'),{code:'GEMINI_HTTP_429_EXHAUSTED'});
 const primary={config:{voice:{}},generate:async()=>{throw boom;}};
 const fallback={generate:async()=>({candidates:[{content:{parts:[{text:'{}'}]}}],_pipeline:{model:'fallback:m'}})};
 const chain=new FallbackTextChain(primary,fallback);
 const out=await chain.generate('text',{},{});
 assert.equal(out._pipeline.model,'fallback:m');
 assert.equal(out._pipeline.fallback,true);
 await assert.rejects(()=>chain.generate('voice',{},{}),/boom/);
});

test('FallbackTextChain rethrows non-exhaustion errors',async()=>{
 const bad=Object.assign(new Error('boom'),{code:'SCRIPT_SCHEMA_INVALID'});
 const primary={config:{voice:{}},generate:async()=>{throw bad;}};
 const chain=new FallbackTextChain(primary,{generate:async()=>({})});
 await assert.rejects(()=>chain.generate('text',{},{}),/boom/);
});

test('fallback chain tries providers in order and returns the first success',async()=>{
 const calls=[];
 const primary={generate:async()=>{const e=Error('GEMINI_HTTP_429_EXHAUSTED');e.code='GEMINI_HTTP_429_EXHAUSTED';throw e;}};
 const first={generate:async()=>{calls.push('groq');const e=Error('FALLBACK_HTTP_429');e.status=429;e.snippet='rate limit';throw e;}};
 const second={generate:async()=>{calls.push('openrouter');return {candidates:[{content:{parts:[{text:'{}'}]}}],_pipeline:{model:'fallback:m2'}}}};
 const chain=new FallbackTextChain(primary,[first,second]);
 const out=await chain.generate('text',{contents:[]});
 assert.deepEqual(calls,['groq','openrouter']);
 assert.equal(out._pipeline.model,'fallback:m2');
 assert.equal(out._pipeline.fallback,true);
});
test('fallback chain throws the last provider error when every provider rejects',async()=>{
 const primary={generate:async()=>{const e=Error('GEMINI_HTTP_429_EXHAUSTED');e.code='GEMINI_HTTP_429_EXHAUSTED';throw e;}};
 const rejecting=status=>({generate:async()=>{const e=Error('FALLBACK_HTTP_'+status);e.status=status;throw e;}});
 const chain=new FallbackTextChain(primary,[rejecting(429),rejecting(503)]);
 const err=await chain.generate('text',{contents:[]}).then(()=>null,e=>e);
 assert.equal(err.message,'FALLBACK_HTTP_503');
});
test('fallbackClientsFrom skips providers without an env key, keeps order, reads the schema-1 form',()=>{
 const clients=fallbackClientsFrom({enabled:true,providers:[
  {baseUrl:'https://groq.test/v1',model:'m1',apiKeyEnv:'MISSING_KEY'},
  {baseUrl:'https://openrouter.test/v1/',model:'m2',apiKeyEnv:'PRESENT_KEY'}]},{PRESENT_KEY:'k'});
 assert.equal(clients.length,1);
 assert.equal(clients[0].model,'m2');
 const legacy=fallbackClientsFrom({enabled:true,baseUrl:'https://one.test/v1',model:'m0',apiKeyEnv:'PRESENT_KEY'},{PRESENT_KEY:'k'});
 assert.equal(legacy.length,1);
 assert.equal(legacy[0].model,'m0');
});
test('OpenAiCompatTextClient converts requests and rejects non-text kinds',async()=>{
 const calls=[];
 const client=new OpenAiCompatTextClient({baseUrl:'https://example.test/v1/',model:'m',apiKey:'k',fetcher:async(url,init)=>{calls.push({url,init});return new Response(JSON.stringify({choices:[{message:{content:'{"a":1}'}}]}),{status:200});}});
 const out=await client.generate('text',{contents:[{parts:[{text:'hi'}]}],generationConfig:{responseMimeType:'application/json',temperature:0.2}});
 assert.equal(out.candidates[0].content.parts[0].text,'{"a":1}');
 assert.equal(calls[0].url,'https://example.test/v1/chat/completions');
 const sent=JSON.parse(calls[0].init.body);
 assert.equal(sent.response_format.type,'json_object');
 assert.equal(sent.temperature,0.2);
 await assert.rejects(()=>client.generate('voice',{}),/FALLBACK_TEXT_ONLY/);
});
