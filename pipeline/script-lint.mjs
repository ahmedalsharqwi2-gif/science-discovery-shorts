// Pre-TTS narration lint: catches the two recurring alignment-gate failure
// classes BEFORE voicing, so ASR gate failures never happen:
//   1. spelled-out years / long number runs ("ألفين وتسعة وعشرين")
//   2. dense transliterated foreign names in one sentence
// Applies to narration fields only (hook, cta, scene.text). claim/evidence
// must stay verbatim from sources and are never linted.
const NUMWORDS=new Set(['واحد','واحدة','اثنين','اتنين','اثنان','ثلاثة','تلاتة','تلات','ثلاث','أربعة','اربعة','أربع','اربع','خمسة','خمس','ستة','ست','سبعة','سبع','ثمانية','تمانية','ثماني','تماني','تسعة','تسع','عشرة','عشر','عشرين','ثلاثين','تلاتين','أربعين','اربعين','خمسين','ستين','سبعين','ثمانين','تمانين','تسعين','مائة','مئة','مية','مائتين','مئتين','ميتين','ألف','الف','ألفين','الفين','آلاف','الاف','مليون','ملايين','بليون','مليار']);
const THOUSAND=new Set(['ألف','الف','ألفين','الفين','آلاف','الاف']);
const TRANSLIT_NAMES=['ناسا','إل ثري','ال ثري','هاريس','نوفا سبيس','سبيس اكس','سبيس إكس','تسلا','جوجل','آبل','ابل','مايكروسوفت','ميتا','أمازون','امازون','أوبن ايه اي','اوبن ايه اي','أوبن أيه آي','تيك توك','انستجرام','إنستجرام','يوتيوب','فيسبوك','تويتر','واتساب','تليجرام','آيفون','ايفون','أندرويد','اندرويد','ويندوز','لينكس','سناب شات','بلاي ستيشن','اكس بوكس','نتفليكس','ديزني','نيفيديا','إنفيديا','انتل','إنتل'];
const stripW=w=>w.replace(/^و(?=\S)/,'');
const sentences=t=>String(t||'').split(/(?<=[.!؟?،؛:\n])/).map(s=>s.trim()).filter(Boolean);
function lintText(text,field,out){
 for(const sentence of sentences(text)){
  const tokens=sentence.split(/\s+/).map(stripW);
  let run=0,runStartThousand=false,maxRun=0,maxStartThousand=false;
  for(const tok of tokens){
   if(NUMWORDS.has(tok)){if(run===0)runStartThousand=THOUSAND.has(tok);run++;if(run>maxRun){maxRun=run;maxStartThousand=runStartThousand;}}
   else{run=0;runStartThousand=false;}
  }
  if(maxRun>=2&&maxStartThousand)out.push({field,kind:'spelled_out_year',detail:'year-like number words in: '+sentence.slice(0,120)});
  const latin=(sentence.match(/[A-Za-z][A-Za-z0-9.-]*/g)||[]).filter(w=>w.length>1);
  if(latin.length>=1)out.push({field,kind:'latin_names',detail:latin.length+' Latin-script token(s) ('+latin.slice(0,4).join(', ')+') in: '+sentence.slice(0,120)});
  const hits=new Set();
  for(const name of TRANSLIT_NAMES)if(sentence.includes(name))hits.add(name);
  if(hits.size>=2)out.push({field,kind:'dense_transliterated_names',detail:[...hits].join(' + ')+' in one sentence: '+sentence.slice(0,120)});
 }
}
export function lintNarration(episode){
 const out=[];
 if(!episode||typeof episode!=='object')return out;
 lintText(episode.title,'title',out);
 lintText(episode.hook,'hook',out);
 lintText(episode.cta,'cta',out);
 (episode.scenes||[]).forEach((s,i)=>lintText(s&&s.text,'scene['+i+'].text',out));
 return out;
}
