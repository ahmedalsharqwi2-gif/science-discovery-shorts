// OpenAI-compatible TEXT fallback (free tiers such as Groq or OpenRouter free
// models). Inert unless config/fallback-text.json exists with enabled:true and
// the named env var is set. Used only for 'text' generation when the Gemini
// pool is exhausted; voice and image stay on Gemini. Downstream gates are
// unchanged: JSON schema validation, evidence, lint and duplicate checks all
// still run on the fallback's output.
export class OpenAiCompatTextClient{
 constructor({baseUrl,model,apiKey,jsonMode=true,fetcher=fetch}){
  if(!baseUrl||!model||!apiKey)throw Error('FALLBACK_CONFIG_INCOMPLETE');
  this.baseUrl=baseUrl.replace(/\/+$/,'');this.model=model;this.apiKey=apiKey;this.jsonMode=jsonMode;this.fetcher=fetcher;
 }
 async generate(kind,body,opts={}){
  if(kind!=='text')throw Error('FALLBACK_TEXT_ONLY');
  const prompt=(body.contents||[]).map(c=>(c.parts||[]).map(p=>p.text||'').join('')).join('\n');
  const gc=body.generationConfig||{};
  const payload={model:this.model,messages:[{role:'user',content:prompt}],temperature:gc.temperature??0.3};
  if(this.jsonMode&&gc.responseMimeType==='application/json')payload.response_format={type:'json_object'};
  const response=await this.fetcher(this.baseUrl+'/chat/completions',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+this.apiKey},body:JSON.stringify(payload)});
  // Keep err.message a stable machine code (run.mjs pattern-matches it into
  // report codes); the provider's own reason rides along on .snippet and is
  // logged by FallbackTextChain so the CI log records WHY it rejected.
  if(!response.ok){let snippet='';try{snippet=(await response.text()).replace(/\s+/g,' ').trim().slice(0,300);}catch{}
   const err=Error('FALLBACK_HTTP_'+response.status);err.status=response.status;err.snippet=snippet;throw err;}
  const data=await response.json();
  const text=((data.choices||[])[0]&&data.choices[0].message&&data.choices[0].message.content)||'';
  if(!text)throw Error('FALLBACK_EMPTY_RESPONSE');
  return {candidates:[{content:{parts:[{text}]}}],_pipeline:{model:'fallback:'+this.model,cacheHit:false}};
 }
}
