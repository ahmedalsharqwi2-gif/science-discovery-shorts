import {science} from './scenes/science.mjs';
import {history} from './scenes/history.mjs';
import {horror} from './scenes/horror.mjs';
export const renderers={science,history,horror};
const kinds={science:['cells','signal','layers'],history:['timeline','artifact','route'],horror:['corridor','shadow','reveal']};
const finite=n=>typeof n==='number'&&Number.isFinite(n);
export function validatePlan(p,audioDuration){
 if(!p||!kinds[p.channel])throw Error('Unknown channel');
 if(!finite(p.duration)||p.duration<=0||p.duration>180)throw Error('Duration must be in (0,180]');
 if(audioDuration!==undefined&&(!finite(audioDuration)||Math.abs(p.duration-audioDuration)>.12))throw Error('Plan/audio duration mismatch; regenerate timing, never trim or speed audio');
 if(typeof p.title!=='string'||!p.title.trim()||p.title.length>100)throw Error('A title of 1–100 characters is required');
 if(!Array.isArray(p.scenes)||!p.scenes.length||p.scenes.length>120)throw Error('Scenes are required (maximum 120)');
 let end=0;
 for(const s of p.scenes){
  if(!finite(s.start)||!finite(s.end)||s.start!==end||s.end<=s.start||s.end>p.duration)throw Error('Scenes must cover the timeline continuously without overlaps');
  if(!kinds[p.channel].includes(s.kind))throw Error('Scene kind does not belong to this channel');
  if(s.label!==undefined&&(typeof s.label!=='string'||s.label.length>100))throw Error('Invalid scene label');
  if(s.seed!==undefined&&(!finite(s.seed)||Math.abs(s.seed)>100000))throw Error('Invalid scene seed');
  if(s.kind==='timeline'&&(!Array.isArray(s.events)||!s.events.length||s.events.length>4||s.events.some(e=>!e||typeof e.label!=='string'||e.label.length>100||typeof e.date!=='string'||e.date.length>60)))throw Error('Timeline requires 1–4 explicit dates and labels');
  if(s.kind==='route'&&(!Array.isArray(s.points)||s.points.length<2||s.points.some(v=>!Array.isArray(v)||v.length!==2||v.some(n=>!finite(n)||n<0||n>1))))throw Error('Route requires explicit normalized coordinates');
  if(s.kind==='route'&&s.schematic!==true)throw Error('Route must explicitly declare schematic=true; no invented map geography');
  end=s.end;
 }
 if(end!==p.duration)throw Error('Scenes must cover the full audio duration');
 if(p.captions!==undefined&&(!Array.isArray(p.captions)||p.captions.length>500))throw Error('Invalid caption list');
 let captionEnd=0;
 for(const c of p.captions??[]){
  if(!finite(c.start)||!finite(c.end)||c.start<captionEnd||c.end<=c.start||c.end>p.duration||typeof c.text!=='string'||!c.text.trim())throw Error('Invalid or overlapping caption timing');
  captionEnd=c.end;
 }
 return p;
}
export function drawFrame(ctx,p,t,{width=1080,height=1920,font='Arabic'}={}){
 if(!finite(t)||t<0||t>=p.duration)throw Error('Frame time outside episode');
 ctx.save();ctx.scale(width/1080,height/1920);ctx.clearRect(0,0,1080,1920);
 const palette={science:['#08151b','#5acbbb'],history:['#171513','#d7ad6b'],horror:['#05090d','#ae5c49']}[p.channel];
 const g=ctx.createRadialGradient(540,780,80,540,800,1200);g.addColorStop(0,p.channel==='horror'?'#1b2527':'#283035');g.addColorStop(1,palette[0]);ctx.fillStyle=g;ctx.fillRect(0,0,1080,1920);
 const text=(value,x,y,size=44,color='#eee9df',weight=600,maxWidth=900)=>{
  ctx.save();ctx.font=`${weight} ${size}px "${font}"`;ctx.direction='rtl';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=color;
  const words=String(value).split(/\s+/);let lines=[''];
  for(const w of words){const candidate=(lines.at(-1)+' '+w).trim();if(ctx.measureText(candidate).width>maxWidth&&lines.at(-1))lines.push(w);else lines[lines.length-1]=candidate;}
  // Reflow and scale complete lines; never clip Arabic or truncate a fact.
  if(lines.length>3){ctx.restore();if(size<=20)throw Error('Text cannot fit safely');return text(value,x,y,size-4,color,weight,maxWidth);}
  lines.forEach((line,i)=>ctx.fillText(line,x,y+(i-(lines.length-1)/2)*size*1.6));ctx.restore();
 };
 const scene=p.scenes.find(s=>t>=s.start&&t<s.end);
 renderers[p.channel](ctx,scene,t-scene.start,{accent:palette[1],text});
 text(p.title,540,205,56,'#eee9df',700);if(scene.label)text(scene.label,540,365,34,palette[1],500);
 const c=(p.captions??[]).find(c=>t>=c.start&&t<c.end);
 if(c){const g=ctx.createLinearGradient(0,1450,0,1850);g.addColorStop(0,'#00000000');g.addColorStop(.5,'#000000df');g.addColorStop(1,'#000000df');ctx.fillStyle=g;ctx.fillRect(0,1450,1080,400);text(c.text,540,1640,48,'#eee9df',700);}
 ctx.fillStyle='#ffffff25';ctx.fillRect(90,1830,900,4);ctx.fillStyle=palette[1];ctx.fillRect(90,1830,900*t/p.duration,4);ctx.restore();
}
