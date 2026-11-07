import React from 'react';
import {Img,staticFile,useCurrentFrame,useVideoConfig,interpolate,Easing} from 'remotion';
import type {Episode,Scene} from './types';

const C={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const M=(f:number,a:number,b:number,x=0,y=1)=>interpolate(f,[a,b],[x,y],C);
const SLOW=Easing.bezier(0.42,0,0.58,1);
const EASE_OUT=Easing.bezier(0.16,1,0.3,1);

const Grain:React.FC<{amount:number}> = ({amount}) => {
  const f=useCurrentFrame();
  return <div style={{position:'absolute',inset:0,opacity:amount,pointerEvents:'none',mixBlendMode:'overlay'}}>
    <svg width="100%" height="100%"><filter id="grainFilter"><feTurbulence type="fractalNoise" baseFrequency="0.82" numOctaves="3" seed={f%7}/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#grainFilter)"/></svg>
  </div>};

const Callouts:React.FC<{scene:Scene;accent:string;w:number;h:number}> = ({scene,accent,w,h}) => {
  const f=useCurrentFrame(); const {fps}=useVideoConfig();
  const list=scene.callouts||[];
  return <svg width={w} height={h} style={{position:'absolute',inset:0}}>
    {list.map((c,i)=>{
      const at=Math.round((c.at??0.35)*fps+24);
      const s=interpolate(f,[at,at+14],[0,1],{...C,easing:EASE_OUT});
      const px=c.x*w,py=c.y*h;const right=c.side!=='l';
      const lx=right?Math.min(w-24,px+150):Math.max(24,px-150); const ly=Math.max(40,py-118);
      return <g key={i} opacity={M(f,at,at+8)}>
        <path d={`M${c.x*w} ${py} L${(px+lx)/2} ${ly} L${lx} ${ly}`} fill="none" stroke="#ffffff" strokeWidth={2.4} strokeDasharray={260} strokeDashoffset={260*(1-s)} opacity={0.88}/>
        <circle cx={px} cy={py} r={8+s*9} fill="none" stroke={accent} strokeWidth={3} opacity={0.95}/>
        <circle cx={px} cy={py} r={3.4} fill={accent}/>
      </g>})}
  </svg>};

export const PhotoScene:React.FC<{scene:Scene;profile:Episode['profile']}> = ({scene,profile}) => {
  const f=useCurrentFrame(); const {fps}=useVideoConfig();
  const src=staticFile(scene.asset!);
  const dur=Math.max(1,(scene.end-scene.start)*fps);
  const p=Math.min(1,f/dur);
  const e=SLOW(p);
  const paper=profile==='stickman';
  const accent={history:'#e8bd78',horror:'#d07a61',science:'#76dfd1',news:'#f7ba64',stickman:'#c05a43'}[profile]||'#e8bd78';
  const PANEL={x:52,y:372,w:976,h:1012};
  const zoom=1.02+(profile==='stickman'?0.14:0.26)*e;
  const driftX=(e-0.5)*(profile==='stickman'?52:96);
  const driftY=(e-0.5)*(profile==='stickman'?34:58);
  const enter=interpolate(f,[0,16],[0,1],{...C,easing:EASE_OUT});
  const bs=1.26+p*0.12;
  const leak=Math.max(0,M(f,0,10)*M(f,20,40,1,0));
  return <div style={{position:'absolute',inset:0,overflow:'hidden'}}>
    {/* خلفية من نفس الصورة، مكبّرة ومموّهة، تتحرك أبطأ من اللوحة */}
    <div style={{position:'absolute',inset:-120,transform:`scale(${bs}) translate(${Math.sin(f/120)*18}px,${Math.cos(f/145)*14}px)`}}>
      <Img src={src} style={{width:'100%',height:'100%',objectFit:'cover',
        filter:`blur(52px) brightness(${paper?0.92:0.34}) saturate(${paper?0.8:profile==='horror'?0.5:0.72})`}}/>
    </div>
    <div style={{position:'absolute',inset:0,background:paper?'linear-gradient(180deg,#f7f1e7c9,#f7f1e74d 40%,#f7f1e7e6 86%,#f7f1e7)':'linear-gradient(180deg,#071019d9,#07101988 30%,#07101966 62%,#071019e8 88%,#071019)'}}/>
    {/* اللوحة المؤطَّرة: الصورة كاملة بلا قص */}
    <div style={{position:'absolute',left:PANEL.x,top:PANEL.y,width:PANEL.w,height:PANEL.h,
      borderRadius:paper?4:5,overflow:'hidden',
      border:`1px solid ${paper?'#1a2b3a26':'#ffffff24'}`,
      boxShadow:`0 46px 130px ${paper?'#6b5b441f':'#000000cc'}, 0 0 0 1px ${paper?'#00000012':'#000000a0'}`,
      background:paper?'#efe6d6':'#080c10',
      opacity:enter,transform:`translateY(${(1-enter)*30}px)`}}>
      <div style={{position:'absolute',inset:12,overflow:'hidden',background:paper?'#e9dfcc':'#05080b'}}>
        <Img src={src} style={{width:'100%',height:'100%',objectFit:'contain',
          transform:`scale(${zoom}) translate(${driftX}px,${driftY}px)`,
          filter:profile==='horror'?'sepia(.34) contrast(1.2) brightness(.9) saturate(.66)':profile==='history'?'sepia(.16) contrast(1.12) brightness(.94) saturate(.86)':'contrast(1.08) brightness(.97) saturate(.95)'}}/>
        <div style={{position:'absolute',inset:0,background:'radial-gradient(ellipse at 50% 42%,transparent 44%,#04070b99 100%)'}}/>
        <Callouts scene={scene} accent={accent} w={PANEL.w-24} h={PANEL.h-24}/>
        <div style={{position:'absolute',inset:0,background:`linear-gradient(105deg,transparent 34%,#fff3d933 47%,#ffffffb3 52%,#fff3d933 57%,transparent 68%)`,
          transform:`translateX(${interpolate(leak,[0,1],[-1100,1100])}px)`,mixBlendMode:'screen',opacity:leak*0.75}}/>
        <Grain amount={paper?0.05:0.085}/>
      </div>
      {/* علامات كادر أرشيفي */}
      <svg width={PANEL.w} height={PANEL.h} style={{position:'absolute',inset:0,pointerEvents:'none',opacity:0.55}}>
        <path d={`M6 28V6H28 M${PANEL.w-28} 6H${PANEL.w-6}V28 M6 ${PANEL.h-28}V${PANEL.h-6}H28 M${PANEL.w-28} ${PANEL.h-6}H${PANEL.w-6}V${PANEL.h-28}`}
          fill="none" stroke={paper?'#1a2b3a55':'#ffffff66'} strokeWidth={2}/>
      </svg>
    </div>
    {/* منسوب الصورة كملصق متحفي */}
    <div style={{position:'absolute',top:PANEL.y+PANEL.h-64,right:PANEL.x+14,left:PANEL.x+14,
      display:'flex',justifyContent:'space-between',alignItems:'flex-end',gap:20,
      opacity:M(f,18,40),direction:'rtl'}}>
      <span style={{fontSize:21,color:paper?'#4a3d2c':'#c8d2d0',background:paper?'#f7f1e7d9':'#05080cb3',
        padding:'7px 13px',borderRadius:2,maxWidth:'72%',lineHeight:1.45}}>{scene.asset_label||'صورة أرشيفية'}</span>
      <span style={{fontSize:17,color:accent,letterSpacing:0.2}}>ليست تصويرًا للحدث</span>
    </div>
  </div>};
