import {XMLParser} from 'fast-xml-parser';import {fetchTrendSignals,rerankCandidates} from './trend-radar.mjs';import {sourceSchema,normalized,digest,duplicate} from './policy.mjs';import {retry} from './io.mjs';import {fetchFeed} from './feed-fetch.mjs';
const array=x=>Array.isArray(x)?x:x?[x]:[];
const plain=x=>typeof x==='string'?x:typeof x?.['#text']==='string'?x['#text']:'';
const strip=x=>plain(x).replace(/<[^>]*>/g,' ').replace(/&[^;]+;/g,' ').replace(/\s+/g,' ').trim();
export function parseFeed(xml,feed,now=Date.now()){
 const data=new XMLParser({ignoreAttributes:false}).parse(xml),items=array(data.rss?.channel?.item||data.feed?.entry||data['rdf:RDF']?.item),sources=[];
 let invalid=0,future=0;
 for(const item of items){
  const link=array(item.link).find(x=>typeof x==='object'&&(!x['@_rel']||x['@_rel']==='alternate'));const url=typeof item.link==='string'?item.link:link?.['@_href']||plain(item.guid);
  const itemDate=plain(item.pubDate)||plain(item.published)||plain(item.updated)||plain(item['dc:date']);
  const announcementDate=feed.allowFeedAnnouncementDate?(plain(data.rss?.channel?.pubDate)||plain(data.feed?.updated)||plain(data['rdf:RDF']?.channel?.['dc:date'])):'';
  const date=itemDate||announcementDate;
  const stamp=Date.parse(date);if(!Number.isFinite(stamp)){invalid++;continue;}if(stamp>now+3600000){future++;continue;}
  const text=strip(item['content:encoded'])||strip(item.description)||strip(item.content)||strip(item.summary);const title=strip(item.title);
  const official=feed.official===true;const parsed=sourceSchema.safeParse({id:digest(url||title).slice(0,12),title,url,text,published:new Date(stamp).toISOString(),official});
  if(parsed.success)sources.push({...parsed.data,dateBasis:itemDate?'item_publication_or_update':'explicit_feed_announcement',publisher:feed.publisher||new URL(feed.url).hostname,primaryRefs:[...plain(item['content:encoded']||item.description||item.summary).matchAll(/https?:\/\/[^\s"<>]+/g)].map(m=>m[0].replace(/&amp;/g,'&'))});else invalid++;
 }
 return {sources,diagnostics:{url:feed.url,items:items.length,valid:sources.length,invalid,future}};
}
export async function collectSources(config,{fetcher=fetchFeed,now=Date.now()}={}){
 const all=[],diagnostics=[];
 for(const feed of config.feeds){try{const response=await retry(()=>fetcher(feed.url,{redirect:'follow',timeout:25000,cacheTtlMs:feed.cacheTtlMs||1800000}),2);const parsed=parseFeed(await response.text(),feed,now);all.push(...parsed.sources);diagnostics.push({...parsed.diagnostics,status:'ok',cache:response.headers.get('x-pipeline-cache')||'not_reported'});}catch(e){diagnostics.push({url:feed.url,status:'unavailable',code:/HTTP_\d{3}/.exec(e.message)?.[0]||'FEED_UNAVAILABLE'});}}
 return {sources:[...new Map(all.map(s=>[s.url,s])).values()],diagnostics};
}
function primaryReference(value){try{const u=new URL(value);if(!/^(export\.)?arxiv\.org$/.test(u.hostname)&&!/^doi\.org$/.test(u.hostname))return null;return u.hostname.replace('export.','')+u.pathname.replace(/v\d+$/,'');}catch{return null;}}
export function verifiedCandidates(sources,{history=[],maxAgeHours,now=Date.now()}={}){
 const recent=sources.filter(s=>now-Date.parse(s.published)<=maxAgeHours*3600000&&Date.parse(s.published)<=now+3600000&&!duplicate(s.url,history)&&!duplicate(s.title,history));
 return recent.map(source=>{if(source.official)return {source,corroboration:[source],verification:'official_primary_source'};
  const refs=new Set((source.primaryRefs||[]).map(primaryReference).filter(Boolean));const others=recent.filter(s=>s.publisher!==source.publisher&&(s.primaryRefs||[]).some(r=>refs.has(primaryReference(r))));
  return others.length?{source,corroboration:[source,others[0]],verification:'two_independent_publishers_same_primary_reference'}:null;
 }).filter(Boolean);
}
export function chooseSources(sources,config,{history=[],now=Date.now(),diagnostics=[],trendSignals=null}={}){
 const hours=config.profile==='news'?72:config.maxAgeHours;let candidates=verifiedCandidates(sources,{history,maxAgeHours:hours,now});let mode='daily',windowHours=hours;
 if(!candidates.length&&config.profile==='news'&&config.weeklyFallback?.enabled){candidates=verifiedCandidates(sources,{history,maxAgeHours:config.weeklyFallback.maxAgeHours,now});mode='weekly';windowHours=config.weeklyFallback.maxAgeHours;}
 candidates.sort((a,b)=>(Number(b.source.official)-Number(a.source.official))||Date.parse(b.source.published)-Date.parse(a.source.published));
 let trend=[];
 if(trendSignals){const ranked=rerankCandidates(candidates,trendSignals,config.trends||{},{now});candidates=ranked.candidates;trend=ranked.decisions;}
 if(!candidates.length){const e=Error('NO_CURRENT_VERIFIED_SOURCES');e.sourceDiagnostics={feeds:diagnostics,windowHours:hours,weeklyWindowHours:config.weeklyFallback?.maxAgeHours||null,parsed:sources.length,reasons:['No unused, dated, corroborated or official source inside the permitted windows.']};throw e;}
 const selected=mode==='weekly'?candidates.slice(0,config.weeklyFallback.maxStories||3):[candidates[0]],pool=[...new Map(selected.flatMap(c=>c.corroboration).map(s=>[s.id,s])).values()];
 return {selected:candidates[0].source,sources:pool,editorialMode:mode,editorialLabel:mode==='weekly'?'أهم أخبار الأسبوع':null,windowHours,verification:selected.map(c=>({id:c.source.id,basis:c.verification,sourceIds:c.corroboration.map(s=>s.id)})),diagnostics,trend,scoring:'Source authority, verified freshness and unused canonical source URL; no invented trend-volume metric.'};
}
export async function selectTopic(config,history,options={}){
 const collected=await collectSources(config,options);
 let trendSignals=null,trendDiagnostics=null;
 if(config.trends?.enabled){try{const radar=await fetchTrendSignals(config.trends,options);trendSignals=radar.degraded?null:radar.signals;trendDiagnostics={sources:radar.diagnostics,degraded:radar.degraded};}catch(e){trendDiagnostics={sources:[],degraded:true,code:/[A-Z_]+/.exec(e.message)?.[0]||'TREND_RADAR_UNAVAILABLE'};}}
 const chosen=chooseSources(collected.sources,config,{...options,history,diagnostics:collected.diagnostics,trendSignals});
 if(trendDiagnostics||chosen.trend?.length)chosen.trendDiagnostics={...(trendDiagnostics||{}),decisions:chosen.trend||[]};
 return chosen;
}
