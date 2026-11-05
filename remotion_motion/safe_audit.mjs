import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {renderStill} from '@remotion/renderer';
export async function audit({serveUrl,composition,inputProps,browserExecutable,chromiumOptions,output,video}){
 const dir=path.join(output,'audit');await fs.mkdir(dir,{recursive:true});
 const e=inputProps.episode;const frames=[...new Set([0,...Array.from({length:Math.ceil(e.duration/2)},(_,i)=>i*60),...e.caption_groups.map(c=>Math.ceil(c.start*30))])].filter(f=>f<Math.ceil(e.duration*30)).sort((a,b)=>a-b);const samples=[];
 for(const frame of frames){let layout=null;const image=`frame-${frame}.png`,mask=`mask-${frame}.png`;
 await renderStill({serveUrl,composition,inputProps,browserExecutable,chromiumOptions,frame,output:path.join(dir,image),overwrite:false,onBrowserLog:log=>{const p=log.text.indexOf('__SAFE_LAYOUT__');if(p>=0){const a=JSON.parse(log.text.slice(p+15));if(Math.abs(a.time-frame/30)<.034)layout=a;}}});
 if(!layout?.focal_bbox)throw Error('No projected focal measurement at frame '+frame);
 await renderStill({serveUrl,composition:{...composition,props:{...composition.props,episode:{...e,diagnostic_layer:'text'}}},inputProps:{episode:{...e,diagnostic_layer:'text'}},browserExecutable,chromiumOptions,frame,output:path.join(dir,mask),overwrite:false});
 const sample={frame,image,mask,focal_bbox:layout.focal_bbox,focal_scale_vs_reference:layout.focal_scale_vs_reference};await fs.writeFile(path.join(dir,`sample-${frame}.json`),JSON.stringify(sample),{flag:'wx'});samples.push(sample);
 }
 const sha=video?createHash('sha256').update(await fs.readFile(video)).digest('hex'):null;
 await fs.writeFile(path.join(dir,'manifest.json'),JSON.stringify({duration:e.duration,caption_groups:e.caption_groups,video_sha256:sha,samples},null,2),{flag:'wx'});
 return path.join(dir,'manifest.json');
}
