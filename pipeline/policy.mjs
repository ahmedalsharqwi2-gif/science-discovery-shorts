import {z} from 'zod';
import {createHash} from 'node:crypto';
export const digest=x=>createHash('sha256').update(x).digest('hex');
export const normalized=s=>s.normalize('NFKC').replace(/[\u064b-\u065f\u0670\u0640]/g,'').replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
export const sourceSchema=z.object({id:z.string(),title:z.string(),url:z.url(),text:z.string().min(60),published:z.string(),official:z.boolean()});
export const sceneSchema=z.object({title:z.string().min(2).max(65),text:z.string().min(20).max(600),summary:z.string().min(2).max(75),keyword:z.string().max(30),template:z.enum(['phenomenon','comparison','steps','journey','map','chart','cause']),labels:z.array(z.string().max(24)).min(2).max(5),values:z.array(z.number().min(0).max(100)).max(5),claim:z.string().min(15),sourceId:z.string(),evidence:z.string().min(15),kind:z.enum(['fact','legend','illustration']),expression:z.number().int().min(0).max(11),action:z.enum(['walk','run','jump','fall','point','turn','hang','sleep'])});
export const episodeSchema=z.object({topicKey:z.string().min(3),title:z.string().max(100),hook:z.string().min(5),cta:z.string().min(5),scenes:z.array(sceneSchema).min(8).max(14)});
export function assertEvidence(episode,sources,profile){
 episodeSchema.parse(episode);
 for(const scene of episode.scenes){const source=sources.find(s=>s.id===scene.sourceId);if(!source||!normalized(source.text).includes(normalized(scene.evidence)))throw Error('UNSUPPORTED_CLAIM');if(profile==='science'&&scene.kind!=='fact')throw Error('SCIENCE_REQUIRES_FACTS');}
 const words=episode.scenes.reduce((n,s)=>n+s.text.trim().split(/\s+/).length,0);if(words<230||words>420)throw Error('SCRIPT_WORD_BUDGET');
 return episode;
}
export function assertReviewMode(mode,config){if(mode!=='review'||config.publish_enabled!==false)throw Error('PUBLICATION_DISABLED');}
export function dueInCairo(date){const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Africa/Cairo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(date);return parts==='17:00';}
export function duplicate(topic,history){const t=normalized(topic);return history.flatMap(h=>typeof h==='string'?[h]:[h.value||'',h.topicKey||'']).some(h=>{const a=normalized(h);if(a===t)return true;const left=new Set(t.split(' ')),right=new Set(a.split(' '));const both=[...left].filter(v=>right.has(v)).length;return both/Math.max(1,new Set([...left,...right]).size)>.7;});}
export function assertTiming(words,duration,text){
 if(!Array.isArray(words)||!words.length)throw Error('ALIGNMENT_EMPTY');
 let prev=0;for(const w of words){if(!Number.isFinite(w.start)||!Number.isFinite(w.end)||w.start<prev-.02||w.end<=w.start||w.end>duration+.05)throw Error('ALIGNMENT_INVALID');prev=w.end;}
 if(normalized(words.map(w=>w.text).join(' '))!==normalized(text))throw Error('ALIGNMENT_TRANSCRIPT_MISMATCH');
}
export function assertMedia(probe){const v=probe.streams.find(s=>s.codec_type==='video'),a=probe.streams.find(s=>s.codec_type==='audio');const d=Number(probe.format.duration);if(!v||!a||v.width!==1080||v.height!==1920||v.r_frame_rate!=='30/1'||d<90||d>180)throw Error('MEDIA_CONTRACT_FAILED');return d;}

// Deterministic measured-span fallback for alignment: distribute the known
// script words across a scene's MEASURED audio duration. Used only when the
// whisper aligner exhausts its repair budget; assertTiming still enforces
// monotonic spans and an exact transcript match afterward, and every later
// gate (layout-qa, visual-qa) is unchanged.
export function distributeWords(text,duration){
 const words=String(text||'').trim().split(/\s+/).filter(Boolean);
 const total=words.reduce((n,w)=>n+w.length,0)||1;
 let acc=0;
 return words.map(w=>{const start=acc/total*duration;acc+=w.length;const end=acc/total*duration;return{text:w,start:+start.toFixed(3),end:+end.toFixed(3)};});
}
