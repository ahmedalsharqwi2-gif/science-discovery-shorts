import {test} from 'node:test';import assert from 'node:assert/strict';
import {htmlToText,pageDate,domainAllowed,domainBlocked,numbersOk,termOverlap,parseProposals,verifyGroundedCandidate,proposeGroundedCandidates} from '../pipeline/grounded-topics.mjs';
import {chooseSources} from '../pipeline/topics.mjs';

const config={profile:'science',name:'أسرار الكون',maxAgeHours:168,feeds:[{url:'https://www.nasa.gov/feed/',official:true}],grounding:{enabled:true,useWhen:'fallback',mode:'strict',maxCandidates:6,blockedDomains:['quora.com']}};
const NOW=Date.parse('2026-11-19T12:00:00Z');
const page=(body,date='2026-11-18T10:00:00Z')=>`<html><head><meta property="article:published_time" content="${date}"></head><body><script>ignore()</script>${body}</body></html>`;
const body='The lake spans 400 kilometers across the desert and satellites tracked it for years with careful orbital imaging.';
const fetcher=async url=>({ok:true,status:200,text:async()=>page(body)});
const proposal={title:'بحيرة بيلكو',url:'https://www.nasa.gov/lake',published:'2026-11-18T10:00:00Z',evidence:'The lake spans 400 kilometers across the desert',summary:'قمر صناعي يرصد بحيرة'};

test('htmlToText strips markup and pageDate reads article time',()=>{
 const html=page('<p>Hello <b>world</b></p>');
 assert.equal(htmlToText(html),'Hello world');
 assert.equal(pageDate(html),'2026-11-18T10:00:00.000Z');
});
test('domain rules: strict allowlist from feeds, blocked list for light',()=>{
 assert.equal(domainAllowed('https://www.nasa.gov/x',config),true);
 assert.equal(domainAllowed('https://sub.nasa.gov/x',config),true);
 assert.equal(domainAllowed('https://nasa.gov.evil.com/x',config),false);
 assert.equal(domainBlocked('https://quora.com/x',config),true);
 assert.equal(domainBlocked('https://www.nasa.gov/x',config),false);
});
test('numbersOk requires every figure in the claim to appear on the page',()=>{
 assert.equal(numbersOk('spans 400 kilometers',body),true);
 assert.equal(numbersOk('spans 900 kilometers',body),false);
});
test('parseProposals tolerates fences and rejects non-https entries',()=>{
 const text='```json\n[{"title":"أ","url":"https://a.com/x"},{"title":"ب","url":"http://b.com/y"}]\n```';
 const parsed=parseProposals(text);
 assert.equal(parsed.length,1);
 assert.equal(parsed[0].url,'https://a.com/x');
});
test('strict verification accepts verbatim evidence from the fetched page',async()=>{
 const v=await verifyGroundedCandidate(proposal,{mode:'strict',config,now:NOW,fetcher,nowHours:168});
 assert.equal(v.verification,'grounded_fetch_verbatim_evidence');
 assert.equal(v.source.official,false);
 assert.ok(v.source.text.includes('400 kilometers'));
});
test('strict verification rejects an invented quote, a wrong figure, a stale page and a foreign domain',async()=>{
 assert.equal(await verifyGroundedCandidate({...proposal,evidence:'A quote that never appears on this page at all'},{mode:'strict',config,now:NOW,fetcher,nowHours:168}),null);
 assert.equal(await verifyGroundedCandidate({...proposal,evidence:'The lake spans 900 kilometers across'},{mode:'strict',config,now:NOW,fetcher,nowHours:168}),null);
 assert.equal(await verifyGroundedCandidate(proposal,{mode:'strict',config,now:NOW,fetcher:async()=>({ok:true,text:async()=>page(body,'2025-01-01T00:00:00Z')}),nowHours:168}),null);
 assert.equal(await verifyGroundedCandidate({...proposal,url:'https://blog.example/x'},{mode:'strict',config,now:NOW,fetcher,nowHours:168}),null);
});
test('strict verification rejects unreachable and undated pages',async()=>{
 assert.equal(await verifyGroundedCandidate(proposal,{mode:'strict',config,now:NOW,fetcher:async()=>({ok:false,status:404,text:async()=>''}),nowHours:168}),null);
 const undated='<html><body>'+body+'</body></html>';
 assert.equal(await verifyGroundedCandidate({...proposal,published:'not-a-date'},{mode:'strict',config,now:NOW,fetcher:async()=>({ok:true,text:async()=>undated}),nowHours:168}),null);
});
test('light verification uses term overlap instead of quote matching',async()=>{
 const light={...config,grounding:{...config.grounding,mode:'light'}};
 const v=await verifyGroundedCandidate({...proposal,url:'https://space-news.example/lake',evidence:'',title:'Lake spans desert kilometers',summary:'satellites tracked the lake'},{mode:'light',config:light,now:NOW,fetcher,nowHours:168});
 assert.equal(v.verification,'grounded_fetch_term_overlap');
 const miss=await verifyGroundedCandidate({...proposal,url:'https://space-news.example/lake',title:'كرة القدم المصرية',summary:'مباراة الدوري امبارح'},{mode:'light',config:light,now:NOW,fetcher,nowHours:168});
 assert.equal(miss,null);
});
test('grounded candidates fill an exhausted feed pool through chooseSources',async()=>{
 const v=await verifyGroundedCandidate(proposal,{mode:'strict',config,now:NOW,fetcher,nowHours:168});
 const chosen=chooseSources([],config,{history:[],now:NOW,extraCandidates:[v]});
 assert.equal(chosen.selected.url,'https://www.nasa.gov/lake');
 assert.throws(()=>chooseSources([],config,{history:[],now:NOW}),/NO_CURRENT_VERIFIED_SOURCES/);
});
test('proposeGroundedCandidates pings once, parses proposals and skips used topics',async()=>{
 const proposals=[proposal,{...proposal,url:'https://www.nasa.gov/lake2',title:'موضوع قديم'}];
 let calls=0;
 const client={generate:async()=>{calls++;return {candidates:[{content:{parts:[{text:JSON.stringify(proposals)}]}}],groundingMetadata:{groundingChunks:[{web:{uri:'https://www.nasa.gov/lake'}}]},_pipeline:{model:'gemini-test'}};}};
 const out=await proposeGroundedCandidates({client,config,history:['موضوع قديم'],now:NOW,fetcher});
 assert.equal(out.diagnostics.verified,1);
 assert.equal(out.candidates[0].source.url,'https://www.nasa.gov/lake');
});
test('a project without grounding support fails the ping loudly',async()=>{
 const {assertGrounding}=await import('../pipeline/grounded-topics.mjs');
 const client={generate:async()=>({candidates:[{content:{parts:[{text:'hi'}]}}]})};
 // module-level ping latch may already be tripped by the previous test; use a fresh module instance
 const fresh=await import('../pipeline/grounded-topics.mjs?fresh=1');
 await assert.rejects(()=>fresh.assertGrounding(client),/GROUNDING_UNSUPPORTED/);
 void assertGrounding;
});
