import {run} from './io.mjs';import {mkdir,cp,writeFile,readdir,rm} from 'node:fs/promises';import path from 'node:path';
// Uses checkout's scoped git authentication; never reads a token or embeds it in a URL.
const target=path.resolve('.cache/review-store');await mkdir('.cache',{recursive:true});
const exists=(await run('git',['ls-remote','--heads','origin','review-media'],{timeout:30000})).stdout.trim();
if(exists)await run('git',['fetch','origin','review-media'],{timeout:120000});
await rm(target,{recursive:true,force:true});
if(exists)await run('git',['worktree','add','--detach',target,'FETCH_HEAD']);
else {await run('git',['worktree','add','--detach',target,'HEAD']);await run('git',['checkout','--orphan','review-media-new'],{cwd:target});await run('git',['rm','-rf','.'],{cwd:target});}
try{
 await mkdir(target+'/reviews',{recursive:true});const directories=await readdir('out',{withFileTypes:true});for(const d of directories.filter(x=>x.isDirectory()))await cp('out/'+d.name,target+'/reviews/'+d.name,{recursive:true});
 await mkdir(target+'/state',{recursive:true});try{await cp('state/topics.json',target+'/state/topics.json');}catch(e){if(e.code!=='ENOENT')throw e;}
 await writeFile(target+'/README.md','# Review media only\n\nNo publication. Failed runs retain diagnostics. Videos require owner approval.\n');
 await run('git',['add','README.md','reviews','state'],{cwd:target});await run('git',['-c','user.name=Review Pipeline','-c','user.email=review@users.noreply.github.com','commit','-m','Retain review output and topic reservations'],{cwd:target});await run('git',['push','origin','HEAD:refs/heads/review-media'],{cwd:target,timeout:120000});
}finally{await run('git',['worktree','remove','--force',target]);}
