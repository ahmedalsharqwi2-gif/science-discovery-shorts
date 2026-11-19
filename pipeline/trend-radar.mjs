import {XMLParser} from 'fast-xml-parser';
import {fetchFeed} from './feed-fetch.mjs';
const array=x=>Array.isArray(x)?x:x?[x]:[];
const strip=x=>(typeof x==='string'?x:typeof x?.['#text']==='string'?x['#text']:'').replace(/<[^>]*>/g,' ').replace(/&[^;]+;/g,' ').replace(/\s+/g,' ').trim();
const tokens=text=>[...new Set((text||'').toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(t=>t.length>2))];
const overlap=(a,b)=>{const set=new Set(b);return a.filter(t=>set.has(t)).length;};
async function googleTrends(geo,fetcher){
 const response=await fetcher(`https://trends.google.com/trending/rss?geo=${encodeURIComponent(geo)}`,{timeout:20000,cacheTtlMs:3600000});
 const data=new XMLParser({ignoreAttributes:false}).parse(await response.text());
 return array(data.rss?.channel?.item).map(item=>({term:strip(item.title),traffic:strip(item['ht:approx_traffic']),news:array(item['ht:news_item']).map(n=>strip(n['ht:news_item_title'])).filter(Boolean).slice(0,3)})).filter(t=>t.term);
}
async function autocomplete(seed,fetcher){
 const response=await fetcher(`https://suggestqueries.google.com/complete/search?client=youtube&hl=ar&ds=yt&q=${encodeURIComponent(seed)}`,{timeout:15000,cacheTtlMs:86400000});
 const parsed=JSON.parse(await response.text());
 return array(parsed[1]).map(entry=>({seed,text:strip(Array.isArray(entry)?entry[0]:entry)})).filter(s=>s.text);
}
async function competitorVideos(channelId,fetcher,now){
 const response=await fetcher(`https://www.youtube.com/feeds/videos.xml?channel_id=${encodeURIComponent(channelId)}`,{timeout:20000,cacheTtlMs:3600000});
 const data=new XMLParser({ignoreAttributes:false,removeNSPrefix:false}).parse(await response.text());
 return array(data.feed?.entry).map(entry=>{
  const stats=entry['media:group']?.['media:community']?.['media:statistics'];
  const views=Number(stats?.['@_views']);const published=strip(entry.published);
  const ageDays=Math.max(0.25,(now-Date.parse(published))/86400000);
  return Number.isFinite(views)&&Date.parse(published)?{channelId,title:strip(entry.title),views,published,viewsPerDay:Math.round(views/ageDays)}:null;
 }).filter(Boolean);
}
async function onThisDay(lang,fetcher,now){
 const d=new Date(now);const mm=String(d.getUTCMonth()+1).padStart(2,'0');const dd=String(d.getUTCDate()).padStart(2,'0');
 const response=await fetcher(`https://api.wikimedia.org/feed/v1/wikipedia/${lang}/onthisday/all/${mm}/${dd}`,{timeout:20000,cacheTtlMs:86400000});
 const data=JSON.parse(await response.text());
 return [...array(data.events),...array(data.birthdays),...array(data.deaths)].map(e=>({text:strip(e.text),year:e.year})).filter(e=>e.text).slice(0,40);
}
async function hackerNews(query,fetcher){
 const response=await fetcher(`https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage=20&query=${encodeURIComponent(query)}`,{timeout:20000,cacheTtlMs:3600000});
 const data=JSON.parse(await response.text());
 return array(data.hits).map(h=>({title:strip(h.title),points:Number(h.points)||0,url:h.url||''})).filter(h=>h.title);
}
async function redditTop(subreddit,fetcher){
 const response=await fetcher(`https://www.reddit.com/r/${encodeURIComponent(subreddit)}/top.json?t=week&limit=15`,{timeout:20000,cacheTtlMs:21600000});
 const data=JSON.parse(await response.text());
 return array(data.data?.children).map(c=>({title:strip(c.data?.title),score:Number(c.data?.score)||0})).filter(p=>p.title);
}
export async function fetchTrendSignals(config,{fetcher=fetchFeed,now=Date.now()}={}){
 const signals={trends:[],suggestions:[],competitorVideos:[],onThisDay:[],hackerNews:[],reddit:[]},diagnostics=[];
 const track=(name,promise)=>promise.then(items=>{signals[name].push(...items);diagnostics.push({source:name,status:'ok',items:items.length});}).catch(e=>{diagnostics.push({source:name,status:'unavailable',code:/\w+/.exec(e.message)?.[0]||'SIGNAL_UNAVAILABLE'});});
 const jobs=[];
 if(config.googleTrends?.geo)jobs.push(track('trends',googleTrends(config.googleTrends.geo,fetcher)));
 for(const seed of config.autocompleteSeeds||[])jobs.push(track('suggestions',autocomplete(seed,fetcher)));
 for(const id of config.competitorChannelIds||[])jobs.push(track('competitorVideos',competitorVideos(id,fetcher,now)));
 if(config.onThisDay?.enabled)jobs.push(track('onThisDay',onThisDay(config.onThisDay.lang||'ar',fetcher,now)));
 if(config.hackerNews?.enabled)jobs.push(track('hackerNews',hackerNews(config.hackerNews.query||'',fetcher)));
 for(const sub of config.redditSubreddits||[])jobs.push(track('reddit',redditTop(sub,fetcher)));
 await Promise.all(jobs);
 const empty=Object.values(signals).every(list=>!list.length);
 return {signals,diagnostics,degraded:empty};
}
export function demandScore(text,signals,config){
 const words=tokens(text);if(!words.length)return {demand:0,matches:[]};
 const matches=[];let demand=0;
 const add=(kind,label,weight)=>{demand+=weight;matches.push({kind,label,weight});};
 const maxVpd=Math.max(1,...signals.competitorVideos.map(v=>v.viewsPerDay));
 for(const t of signals.trends){const hit=overlap(words,tokens(t.term+' '+t.news.join(' ')));if(hit)add('google_trend',t.term,hit*2);}
 for(const s of signals.suggestions){const hit=overlap(words,tokens(s.text));if(hit>=2)add('search_suggestion',s.text,hit*0.75);}
 for(const v of signals.competitorVideos){const hit=overlap(words,tokens(v.title));if(hit>=2)add('competitor_video',v.title,hit*(v.viewsPerDay/maxVpd)*2);}
 for(const e of signals.onThisDay){const hit=overlap(words,tokens(e.text));if(hit>=2)add('on_this_day',e.text.slice(0,80),hit);}
 for(const h of signals.hackerNews){const hit=overlap(words,tokens(h.title));if(hit>=2)add('hacker_news',h.title,hit*0.75);}
 for(const p of signals.reddit){const hit=overlap(words,tokens(p.title));if(hit>=2)add('reddit',p.title,hit*0.5);}
 return {demand,matches};
}
export function rerankCandidates(candidates,signals,config,{now=Date.now()}={}){
 if(!candidates.length||!signals)return {candidates,decisions:[]};
 const weights={demand:1,recency:0.5,...(config.weights||{})};
 const excluded=(config.excludedTerms||[]).map(t=>t.toLowerCase());
 const decisions=candidates.map(candidate=>{
  const source=candidate.source||candidate;const text=source.title+' '+(source.text||'');
  const excludedTerm=excluded.find(term=>text.toLowerCase().includes(term));
  if(excludedTerm)return {id:source.id,excluded:true,excludedTerm,score:-Infinity};
  const {demand,matches}=demandScore(text,signals,config);
  const ageHours=Math.max(0,(now-Date.parse(source.published))/3600000);
  const recency=Math.exp(-ageHours/72);
  return {id:source.id,title:source.title,demand,recency:Number(recency.toFixed(3)),matches,score:demand*weights.demand+recency*weights.recency};
 });
 const order=new Map(decisions.map((d,i)=>[d.id,i]));
 const reranked=[...candidates].sort((a,b)=>{
  const da=decisions[order.get((a.source||a).id)],db=decisions[order.get((b.source||b).id)];
  return (db.score-da.score)||(Number((b.source||b).official)-Number((a.source||a).official))||(Date.parse((b.source||b).published)-Date.parse((a.source||a).published));
 });
 return {candidates:reranked,decisions};
}
