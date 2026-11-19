import {readFile,writeFile,mkdir,rename} from 'node:fs/promises';import path from 'node:path';import {createHash,randomUUID} from 'node:crypto';
const hash=s=>createHash('sha256').update(s).digest('hex');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
export function createFeedFetcher({fetcher=fetch,clock=Date.now,sleep=pause,cacheDir='.cache/feeds',minDelayMs=1000,userAgent='ChannelReviewPipeline/2.1 (+https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts; RSS research; cached)'}={}){
 let tail=Promise.resolve(),last=-Infinity;
 return async function fetchFeed(url,{timeout=25000,cacheTtlMs=1800000}={}){
  const parsed=new URL(url);if(parsed.protocol!=='https:')throw Error('FEED_HTTPS_REQUIRED');
  const file=path.join(cacheDir,hash(url)+'.json');
  try{const cached=JSON.parse(await readFile(file,'utf8'));if(cached.url===url&&cached.expiresAt>clock())return new Response(cached.body,{status:200,headers:{'content-type':cached.contentType,'x-pipeline-cache':'hit'}});}catch(e){if(e.code!=='ENOENT'&&!(e instanceof SyntaxError))throw e;}
  const prior=tail;let release;tail=new Promise(r=>{release=r;});await prior;
  try{
   const delay=Math.max(0,last+minDelayMs-clock());if(delay)await sleep(delay);last=clock();
   const response=await fetcher(url,{redirect:'follow',signal:AbortSignal.timeout(timeout),headers:{'User-Agent':userAgent,Accept:'application/rss+xml, application/atom+xml, application/xml;q=0.9'}});
   if(!response.ok){const error=Error('FEED_HTTP_'+response.status);error.permanent=response.status>=400&&response.status<500&&response.status!==429;throw error;}
   const body=await response.text();if(Buffer.byteLength(body)>5000000)throw Error('FEED_TOO_LARGE');
   const contentType=response.headers.get('content-type')||'application/xml';const record={url,fetchedAt:clock(),expiresAt:clock()+cacheTtlMs,contentType,body};await mkdir(cacheDir,{recursive:true});const temp=file+'.'+randomUUID()+'.tmp';await writeFile(temp,JSON.stringify(record));await rename(temp,file);
   return new Response(body,{status:200,headers:{'content-type':contentType,'x-pipeline-cache':'miss'}});
  }finally{release();}
 };
}
export const fetchFeed=createFeedFetcher();
