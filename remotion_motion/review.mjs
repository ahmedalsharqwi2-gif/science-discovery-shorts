import {execFileSync} from 'node:child_process';
import {loadTemplate} from './visual_template.mjs';
/** Local, watermarked reviews only. No publisher is imported. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {selectComposition,renderMedia,renderStill} from '@remotion/renderer';
import {audit} from './safe_audit.mjs';
const project=path.dirname(fileURLToPath(import.meta.url));
execFileSync(process.env.PYTHON||'python3',['-m','remotion_factory.fonts'],{cwd:path.join(project,'..'),stdio:'pipe'});
const arg=n=>{const i=process.argv.indexOf(n);if(i<0||!process.argv[i+1])throw Error('Required '+n);return process.argv[i+1]};
const output=path.resolve(arg('--output-dir')),source=path.resolve(arg('--props'));const {episode}=JSON.parse(await fs.readFile(source));const t=await loadTemplate(project);
if(t.version!==1||!t.locked||episode.profile!==t.channel||episode.palette)throw Error('Locked identity mismatch');
if(!episode.hook_line||!episode.scenes[0].narration.startsWith(episode.hook_line)||episode.caption_groups[0]?.start!==0||episode.caption_groups[0]?.text!==episode.hook_line)throw Error('Exact first hook at frame zero required');
if(!(episode.duration>t.duration_seconds.min_exclusive&&episode.duration<t.duration_seconds.max_exclusive))throw Error('Review duration out of policy');
const silent=process.argv.includes('--silent-review'),stills=process.argv.includes('--diagnostic-stills');
if(silent&&episode.profile!=='stickman')throw Error('Silent full-review exception is only authorized for stickman');
if(!silent&&!episode.audio&&!stills)throw Error('Actual narration required; no synthetic or silent substitute');
await fs.mkdir(output,{recursive:false});episode.review_only=true;
const serveUrl=await bundle({entryPoint:path.join(project,'src/index.ts'),publicDir:path.join(project,'public')});const browserExecutable=process.env.CHROMIUM_PATH||undefined;const chromiumOptions={gl:'swangle'};const inputProps={episode};const composition=await selectComposition({serveUrl,id:'Documentary',inputProps,browserExecutable,chromiumOptions});
if(composition.width!==t.canvas.w||composition.height!==t.canvas.h||composition.fps!==t.canvas.fps||composition.width>=composition.height)throw Error('Wrong vertical canvas');
if(stills){for(let i=0;i<episode.scenes.length;i++)await renderStill({serveUrl,composition,inputProps,browserExecutable,chromiumOptions,frame:Math.round(episode.scenes[i].start*30),output:path.join(output,`shot-${i}.png`),overwrite:false,onBrowserLog:log=>{if(log.type==='error')console.error(log.text)}});}
else{
 const video=path.join(output,'review.mp4');await renderMedia({serveUrl,composition,inputProps,browserExecutable,chromiumOptions,codec:'h264',pixelFormat:'yuv420p',crf:19,muted:silent,concurrency:2,outputLocation:video,overwrite:false});
 await audit({serveUrl,composition,inputProps,browserExecutable,chromiumOptions,output,video});
}
await fs.writeFile(path.join(output,'review.json'),JSON.stringify({publishable:false,review_only:true,diagnostic_stills:stills,narration_present:!silent&&!!episode.audio,duration:episode.duration,hook_line:episode.hook_line,template_version:t.version,width:t.canvas.w,height:t.canvas.h,fps:t.canvas.fps,props_path:source},null,2),{flag:'wx'});
