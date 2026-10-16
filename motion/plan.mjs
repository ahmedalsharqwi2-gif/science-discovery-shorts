import {createHash} from 'node:crypto';
import {validatePlan} from './engine.mjs';
const normalize=s=>String(s).normalize('NFKC').replace(/[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06edـ]/gu,'').replace(/[أإآٱ]/gu,'ا').replace(/ى/gu,'ي').replace(/[^\p{L}\p{N}]+/gu,' ').trim().split(/\s+/).filter(Boolean);
export function parseSrt(source){
 const stamp=s=>{const m=s.match(/^(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})$/);if(!m||+m[2]>59||+m[3]>59)throw Error('Invalid subtitle timestamp');return +m[1]*3600 + +m[2]*60 + +m[3]+ +m[4]/1000;};
 return source.replace(/^\uFEFF/,'').trim().split(/\r?\n\s*\r?\n/).map(block=>{
  const lines=block.split(/\r?\n/);if(/^\d+$/.test(lines[0]))lines.shift();const times=lines.shift()?.split(/\s+-->\s+/);
  if(times?.length!==2)throw Error('Invalid SRT cue');return {start:stamp(times[0]),end:stamp(times[1]),text:lines.join(' ').trim()};
 });
}
export function buildPlan({channel,episode,timings,duration}){
 const narration=episode.narration??episode.narration_script;
 if(typeof narration!=='string'||!narration.trim())throw Error('Complete checked narration is required');
 if(!Array.isArray(timings)||!timings.length)throw Error('Real alignment or sentence timings are required');
 const units=timings.map(w=>({text:w.text??w.word,start:w.start??w.offset,end:w.end??((w.offset??NaN)+(w.duration??NaN))}));
 let last=0;
 for(const u of units){if(typeof u.text!=='string'||!u.text.trim()||!Number.isFinite(u.start)||!Number.isFinite(u.end)||u.start<last||u.end<=u.start||u.end>duration)throw Error('Invalid, overlapping or out-of-audio alignment');last=u.end;}
 if(normalize(units.map(x=>x.text).join(' ')).join(' ')!==normalize(narration).join(' '))throw Error('Alignment does not cover the supplied narration exactly');
 // Group only real word timings. Existing multiword sentence cues keep their timing.
 const captions=[];let group=[];
 const flush=()=>{if(group.length){captions.push({start:group[0].start,end:group.at(-1).end,text:group.map(x=>x.text).join(' ')});group=[];}};
 for(const u of units){if(normalize(u.text).length>1){flush();captions.push(u);continue;}if(group.length&&(group.length>=5||u.start-group.at(-1).end>.35))flush();group.push(u);}flush();
 const seed=parseInt(createHash('sha256').update(channel+'\0'+narration).digest('hex').slice(0,8),16)%100000;
 // Cut in real pauses, never in the middle of a spoken cue.
 const cuts=[0];for(const c of captions)if(c.start-cuts.at(-1)>=6&&duration-c.start>=2)cuts.push(c.start);cuts.push(duration);
 const scenes=cuts.slice(0,-1).map((start,i)=>{
  const end=cuts[i+1],text=captions.filter(c=>c.start>=start&&c.start<end).map(c=>c.text).join(' '),clean=normalize(text).join(' ');
  const s={start,end,seed:seed+i,label:''};
  if(channel==='science'){
   s.kind=/اخطبوط/.test(normalize(narration).join(' '))?'octopus':/عصب|اشار/.test(clean)?'signal':/طبقات|طبقه/.test(clean)?'layers':/خليه|خلايا/.test(clean)?'cells':'concept';
   s.terms=[...new Set(text.split(/\s+/).map(x=>x.replace(/[^\p{L}\p{N}]/gu,'')).filter(x=>normalize(x).join('').length>=4))].slice(0,5);
   s.visual_label='رسم توضيحي';
  }else if(channel==='history'){
   // Only use structured historical dates supplied by the checked episode.
   if(episode.historical_events&&i%2===1){s.kind='timeline';s.events=episode.historical_events;}
   else{s.kind='artifact';s.artifact_label='عرض توضيحي من نص الحلقة';}
  }else if(channel==='horror'){
   s.kind=i===0?'corridor':i===cuts.length-2?'reveal':'shadow';
   s.number=episode.door_number??'';
  }else throw Error('Unknown channel');
  return s;
 });
 return validatePlan({channel,title:episode.title??episode.topic,duration,scenes,captions},duration);
}
