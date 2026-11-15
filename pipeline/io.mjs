import {mkdir,readFile,writeFile,rename} from 'node:fs/promises';
import {execFile} from 'node:child_process';import {promisify} from 'node:util';
import {digest} from './policy.mjs';
export const run=promisify(execFile);
export const json=async p=>JSON.parse(await readFile(p,'utf8'));
export async function save(p,data){await mkdir(new URL('.',new URL('file://'+p)).pathname,{recursive:true});await writeFile(p+'.tmp',JSON.stringify(data,null,2)+'\n');await rename(p+'.tmp',p);}
export async function retry(fn,attempts=3){for(let i=0;i<attempts;i++){try{return await fn();}catch(e){if(i===attempts-1||e.permanent)throw e;await new Promise(r=>setTimeout(r,1000*2**i));}}}
export async function fetchSafe(url,options={}){const u=new URL(url);if(u.protocol!=='https:')throw Error('HTTPS_REQUIRED');const r=await fetch(url,{...options,redirect:'error',signal:AbortSignal.timeout(options.timeout||60000)});if(!r.ok){const e=Error('PROVIDER_HTTP_'+r.status);e.permanent=r.status>=400&&r.status<500&&r.status!==429;throw e;}return r;}
export async function cached(key,fn){const p='.cache/'+digest(key)+'.json';try{return await json(p);}catch(e){if(e.code!=='ENOENT')throw e;}const v=await fn();await mkdir('.cache',{recursive:true});await writeFile(p,JSON.stringify(v));return v;}
export async function probe(p){const r=await run('ffprobe',['-v','error','-show_streams','-show_format','-of','json',p],{timeout:30000,maxBuffer:2000000});return JSON.parse(r.stdout);}
