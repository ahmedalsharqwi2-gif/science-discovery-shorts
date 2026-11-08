import React from 'react';
import {AbsoluteFill, Easing, interpolate, interpolateColors, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Episode, Scene} from './types';

type Props={scene:Scene;episode:Episode};
type Contract='sunset_journey'|'prism_scattering'|'eye_light'|'earth_atmosphere'|'science_orbit'|'horror_mist'|'paper_story'|'cinematic_atmosphere';

/**
 * Visual Story Mode
 *
 * hybrid: keeps the editorial image visible and adds topic-specific animation.
 * motion_only: uses the same grammar as a fully illustrated explainer when no
 * trustworthy image asset exists. It never invents documentary facts or text.
 */
export const sceneContractFor=(scene:Scene,episode:Episode):Contract=>{
  if(scene.motion_contract) return scene.motion_contract as Contract;
  const text=[scene.label,scene.headline,scene.detail,scene.narration,scene.kicker,episode.title].filter(Boolean).join(' ');
  if(/منشور|طيف|انكسار|prism|spectrum|refraction/i.test(text)) return 'prism_scattering';
  if(/عين|بصر|رؤية|شبكية|eye|vision|retina/i.test(text)) return 'eye_light';
  if(/غلاف جوي|مسافة الضوء|نهار|غروب|شروق|شمس|سماء|طريق|رحلة|earth|atmosphere|sunset|sunrise|sun|sky|journey|road/i.test(text)) return 'earth_atmosphere';
  if(episode.profile==='science'||scene.kind==='science'||/فضاء|كوكب|ذرة|موجة|space|planet|atom|molecule/i.test(text)) return 'science_orbit';
  if(episode.profile==='horror') return 'horror_mist';
  if(episode.profile==='stickman'||scene.kind==='stickman'||scene.kind==='whatif') return 'paper_story';
  return 'cinematic_atmosphere';
};

const modeFor=(scene:Scene)=>scene.visual_mode||(scene.asset?'hybrid':'motion_only');
const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;

export const SceneContract=({scene,episode}:Props)=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const duration=Math.max(1,(scene.end-scene.start)*fps);
  const p=interpolate(frame,[0,duration],[0,1],{...clamp,easing:Easing.inOut(Easing.cubic)});
  const contract=sceneContractFor(scene,episode);
  const mode=modeFor(scene);
  const hasImage=Boolean(scene.asset);
  const accent=contract==='science_orbit'?'#72e9ff':contract==='horror_mist'?'#d37a9b':contract==='paper_story'?'#ffd2a5':'#ffe7a1';
  const skyTop=contract==='horror_mist'?'#15182a':contract==='science_orbit'?'#071c42':contract==='paper_story'?'#596b85':'#514b76';
  const skyBottom=contract==='horror_mist'?'#5e314e':contract==='science_orbit'?'#164b72':contract==='paper_story'?'#e9b18e':'#f49a78';
  const sunX=interpolate(p,[0,1],[790,505]);
  const sunY=interpolate(p,[0,1],[330,1060]);
  const cloudX=interpolate(frame,[0,duration],[-180,220],{...clamp});
  const contentOpacity=mode==='hybrid'&&hasImage?.9:1;
  const gradient=interpolateColors(p,[0,.58,1],[skyTop,skyBottom,'#17232e']);
  return <AbsoluteFill data-scene-contract={contract} data-visual-mode={mode} style={{pointerEvents:'none',opacity:contentOpacity}}>
    <svg viewBox="0 0 1080 1920" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" style={{position:'absolute',inset:0}}>
      <defs>
        <linearGradient id="vsm-sky" x1="0" y1="0" x2="0" y2="1"><stop stopColor={gradient}/><stop offset="1" stopColor="#17232e"/></linearGradient>
        <radialGradient id="vsm-glow"><stop stopColor={accent} stopOpacity=".86"/><stop offset=".38" stopColor={accent} stopOpacity=".22"/><stop offset="1" stopColor={accent} stopOpacity="0"/></radialGradient>
        <filter id="vsm-blur"><feGaussianBlur stdDeviation="18"/></filter>
      </defs>
      <rect width="1080" height="1920" fill="url(#vsm-sky)" opacity={mode==='motion_only'?'.96':'.38'}/>
      {(contract==='earth_atmosphere'||contract==='cinematic_atmosphere')&&<>
        <circle cx={sunX} cy={sunY} r={280+Math.sin(frame/18)*16} fill="url(#vsm-glow)" filter="url(#vsm-blur)"/>
        <circle cx={sunX} cy={sunY} r="54" fill={accent}/>
        <g opacity={.2+Math.sin(frame/23)*.05} transform={`translate(${sunX} ${sunY}) rotate(${interpolate(p,[0,1],[-18,16])})`}>
          {Array.from({length:14},(_,i)=>{const a=i*Math.PI/7;return <line key={i} x1={Math.cos(a)*90} y1={Math.sin(a)*90} x2={Math.cos(a)*420} y2={Math.sin(a)*420} stroke={accent} strokeWidth="9" strokeLinecap="round"/>;})}
        </g>
        <g opacity=".23" transform={`translate(${cloudX} 0)`}><path d="M60 610C130 545 210 555 260 615C310 555 420 565 462 640C380 680 170 690 60 660Z" fill="#f7dfda"/><path d="M620 460C710 400 790 430 820 490C890 440 1000 470 1040 545C930 585 745 575 620 530Z" fill="#f7dfda"/></g>
        <path d={`M${interpolate(p,[0,1],[540,505])} 1920 C${interpolate(p,[0,1],[530,530])} 1660 ${interpolate(p,[0,1],[620,545])} 1360 ${sunX} ${sunY+70}`} fill="none" stroke={accent} strokeWidth="7" strokeDasharray="22 24" opacity=".88"/>
      </>}
      <g transform={`translate(${interpolate(p,[0,1],[0,-34])} ${interpolate(p,[0,1],[0,18])})`}><path d="M0 1260Q220 1060 430 1240T830 1190T1080 1110V1920H0Z" fill={contract==='paper_story'?'#3f4a55':'#263a47'} opacity=".74"/></g>
      <g transform={`translate(${interpolate(p,[0,1],[0,-82])} ${interpolate(p,[0,1],[0,35])})`}><path d="M0 1430Q230 1230 470 1400T800 1320T1080 1260V1920H0Z" fill="#111d27" opacity=".92"/></g>
      {contract==='prism_scattering'&&<g transform={`translate(0 ${interpolate(p,[0,1],[50,-20])})`}>
        <path d="M350 1080L700 1080L525 700Z" fill="#ccecff22" stroke="#ecf8ff" strokeWidth="7"/>
        <path d="M80 960L400 960" stroke="#fff" strokeWidth="10" strokeDasharray="24 18" opacity=".9"/>
        {['#ef6b65','#f5bd5c','#79d88f','#6caeff','#c78cff'].map((c,i)=><path key={c} d={`M${650+i*22} 1010L1010 ${870+i*55}`} stroke={c} strokeWidth="9" strokeDasharray="22 14" opacity=".9"/>)}
      </g>}
      {contract==='eye_light'&&<g><path d="M230 1010Q540 720 850 1010Q540 1300 230 1010Z" fill="#173044" stroke="#dceeff" strokeWidth="8"/><ellipse cx="540" cy="1010" rx="90" ry="130" fill="#8ad4dd"/><circle cx="540" cy="1010" r="42" fill="#101827"/>{[-1,0,1].map(i=><path key={i} d={`M${100+i*80} ${700+i*70}L500 970`} stroke={accent} strokeWidth="6" strokeDasharray="18 16" opacity=".86"/>)}<path d="M580 1010L960 820" stroke="#fff" strokeWidth="6" strokeDasharray="18 16"/></g>}
      {contract==='science_orbit'&&<g fill="none" stroke="#7cecff" opacity=".7"><ellipse cx="540" cy="900" rx="320" ry="125" transform={`rotate(${interpolate(p,[0,1],[-18,18])} 540 900)`}/><ellipse cx="540" cy="900" rx="220" ry="82" transform={`rotate(${interpolate(p,[0,1],[22,-22])} 540 900)`}/><circle cx="540" cy="900" r="40" fill="#7cecff"/>{Array.from({length:8},(_,i)=><circle key={i} cx={540+Math.cos(i*Math.PI/4+frame/60)*320} cy={900+Math.sin(i*Math.PI/4+frame/60)*125} r="12" fill={i%2?'#ffe7a1':'#7cecff'}/>)}</g>}
      {contract==='horror_mist'&&<g fill="#d37a9b" opacity={.13+.07*Math.sin(frame/29)}><ellipse cx="180" cy="980" rx="360" ry="80"/><ellipse cx="900" cy="1120" rx="420" ry="95"/></g>}
      {contract==='earth_atmosphere'&&<g fill="none" stroke="#8be7ff" opacity=".48"><ellipse cx="540" cy="1180" rx="340" ry="100" transform={`rotate(${interpolate(p,[0,1],[-12,12])} 540 1180)`}/><path d="M170 1180Q540 920 910 1180" strokeDasharray="20 18" strokeWidth="8"/></g>}
    </svg>
  </AbsoluteFill>;
};
