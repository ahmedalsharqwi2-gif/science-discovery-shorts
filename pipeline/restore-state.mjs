import {run,save,json} from './io.mjs';import {writeFile,mkdir,readFile} from 'node:fs/promises';import path from 'node:path';import {digest,episodeSchema} from './policy.mjs';
const found=(await run('git',['ls-remote','--heads','origin','review-media'])).stdout.trim();
if(found){
 await run('git',['fetch','origin','review-media']);const read=async p=>{try{return JSON.parse((await run('git',['show','FETCH_HEAD:'+p],{maxBuffer:12000000})).stdout);}catch{return null;}};
 const state=await read('state/topics.json');if(state&&!Array.isArray(state))throw Error('INVALID_REMOTE_TOPIC_STATE');await mkdir('state',{recursive:true});if(state)await save(path.resolve('state/topics.json'),state);
 let active=await read('state/active-review.json');
 if(!active){const pending=state?.filter(r=>r.status==='reserved').at(-1);if(pending&&/^[0-9TZ-]+$/.test(pending.run)){const episode=await read('reviews/'+pending.run+'/script.json'),topic=await read('reviews/'+pending.run+'/sources.json');if(episode&&topic?.sources?.length){episodeSchema.parse(episode);const channel=await json('config/channel.json');active={schema:1,id:pending.run,profile:channel.profile,episode,topic,scriptSha256:digest(JSON.stringify(episode)),state:'reserved',migration:'Recovered original reserved script after the earlier provider failure; no new script or repeated source selection.'};}}}
 if(active)await save(path.resolve('state/active-review.json'),active);
}
