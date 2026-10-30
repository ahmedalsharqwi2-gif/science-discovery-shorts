// Editorial frame inspired by the supplied vertical reference. Geometry and
// measured speech remain owned by the existing production renderer.
import {drawCaption} from './caption_layout.js';
export const REFERENCE_STYLE = 'reference-editorial-v1';
const THEMES={science:['#67dce8','أسرار الكون','SCIENCE'],horror:['#9fc8be','ملفات غامضة','MYSTERIES'],history:['#e7bd7a','حكايات التاريخ','HISTORY'],news:['#67dce8','على السريع','AI NEWS']};
const clamp=x=>Math.max(0,Math.min(1,x));
export function wrapText(ctx,value,maxWidth){
 const rows=[''];for(const word of String(value||'').trim().split(/\s+/)){
  const n=rows.length-1,test=(rows[n]+' '+word).trim();
  if(rows[n]&&ctx.measureText(test).width>maxWidth)rows.push(word);else rows[n]=test;
 }return rows;
}
function text(ctx,value,x,y,size,color,align='center'){
 ctx.font=`700 ${size}px Noto, sans-serif`;ctx.fillStyle=color;ctx.textAlign=align;ctx.textBaseline='middle';ctx.direction='rtl';ctx.fillText(value,x,y);
}
function panel(ctx,x,y,w,h,fill,stroke,r=22){
 ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle=stroke;ctx.lineWidth=2;ctx.stroke();
}
export function drawReferenceLayout(ctx,{story,timing,index,time,local,duration,review=false,logo=false}){
 const [accent,name,tag]=THEMES[story.profile]||THEMES.science;
 const s=story.scenes[index],white='#eff5fa',muted='#93a7bd';
 ctx.save();ctx.clearRect(0,0,1080,1920);
 // Keep the moving subject visible between the title and caption zones.
 let g=ctx.createLinearGradient(0,0,0,700);g.addColorStop(0,'#071121');g.addColorStop(.65,'rgba(7,17,33,.97)');g.addColorStop(1,'rgba(7,17,33,0)');ctx.fillStyle=g;ctx.fillRect(0,0,1080,700);
 g=ctx.createLinearGradient(0,1270,0,1920);g.addColorStop(0,'rgba(7,17,33,0)');g.addColorStop(.35,'rgba(7,17,33,.94)');g.addColorStop(1,'#071121');ctx.fillStyle=g;ctx.fillRect(0,1270,1080,650);
 panel(ctx,54,38,972,174,'rgba(5,13,25,.92)',accent+'66');
 text(ctx,story.series||name,980,100,43,white,'right');
 text(ctx,review?'عينة مراجعة • القالب الجديد':'معلومة واضحة من المصدر',980,164,25,muted,'right');
 if(!logo){text(ctx,tag,92,114,22,accent,'left');}
 const source=typeof story.source==='object'?story.source:{};
 ctx.font='20px Plex';ctx.direction='ltr';ctx.textAlign='center';ctx.fillStyle=muted;
 ctx.fillText(`${tag}  /  ${String(index+1).padStart(2,'0')} — ${String(story.scenes.length).padStart(2,'0')}`,540,264);
 // Titles wrap rather than shrinking long Arabic into an unreadable line.
 let titleSize=64,rows;do{ctx.font=`700 ${titleSize}px Noto, sans-serif`;rows=wrapText(ctx,s.label,900);if(rows.length<=2)break;titleSize-=2;}while(titleSize>=32);
 if(rows.length>2)throw Error('Reference title exceeds the safe two-line area');
 const enter=1-Math.pow(1-clamp(local/.5),3);
 ctx.globalAlpha=enter;rows.forEach((row,i)=>text(ctx,row,540,352+i*84+(1-enter)*20,titleSize,white));ctx.globalAlpha=1;
 const barY=rows.length>1?488:426;
 panel(ctx,75,barY,930,62,'rgba(112,58,24,.86)','#bc874e',12);
 text(ctx,story.profile==='news'?'تصريحات المصدر تحتاج قراءة في سياقها':'رسوم توضيحية لفهم الفكرة',540,barY+32,27,'#ffe2b9');
 // Thin inset edges echo the reference without covering the actual scene.
 ctx.strokeStyle=accent+'55';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(70,700);ctx.lineTo(70,640);ctx.lineTo(130,640);ctx.moveTo(1010,700);ctx.lineTo(1010,640);ctx.lineTo(950,640);ctx.moveTo(70,1240);ctx.lineTo(70,1300);ctx.lineTo(130,1300);ctx.moveTo(1010,1240);ctx.lineTo(1010,1300);ctx.lineTo(950,1300);ctx.stroke();
 const group=timing?.caption_groups?.find(x=>time>=x.start&&time<x.end);
 if(group)drawCaption(ctx,group.text,white);
 else if(timing?.words){const k=timing.words.findIndex(w=>time>=w.start&&time<w.end+.08);if(k>=0){const a=Math.floor(k/6)*6;drawCaption(ctx,timing.words.slice(a,a+6).map(w=>w.text).join(' '),white);}}
 text(ctx,review?'مراجعة بصرية • لا تُنشر تلقائيًا':'رسوم توضيحية • تعليق عربي',480,1640,25,muted);
 if(story.profile==='news'&&source.published)text(ctx,'تاريخ المصدر: '+source.published.slice(0,10),480,1690,23,muted);
 let publisher=source.publisher;if(!publisher&&typeof story.source==='string'){try{publisher=new URL(story.source).hostname;}catch{}}publisher=publisher||'SOURCE / SEE STORY RECORD';
 ctx.font='19px Plex';ctx.direction='ltr';ctx.textAlign='center';ctx.fillStyle=muted;ctx.fillText(publisher.slice(0,60),480,1744);
 ctx.fillStyle='#22324a';ctx.fillRect(72,1792,816,8);ctx.fillStyle=accent;ctx.fillRect(72,1792,816*clamp(time/duration),8);
 ctx.restore();
}
