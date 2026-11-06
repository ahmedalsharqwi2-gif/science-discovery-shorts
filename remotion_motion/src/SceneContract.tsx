import React from 'react';
import {AbsoluteFill, Easing, interpolate, interpolateColors, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Episode, Scene} from './types';

type Props={scene:Scene;episode:Episode};

/**
 * Scene Contract: every scene declares a visual motion grammar even when the
 * editorial JSON has no hand-authored motion yet. The renderer turns this
 * contract into deterministic keyframes instead of a static background.
 */
export const sceneContractFor=(scene:Scene, episode:Episode)=>{
  const text=[scene.label,scene.headline,scene.detail,scene.narration,scene.kicker,episode.title].filter(Boolean).join(' ');
  if(/غروب|شروق|شمس|سماء|طريق|رحلة|sunset|sunrise|sun|sky|journey|road/i.test(text)) return 'sunset_journey';
  if(episode.profile==='science'||scene.kind==='science'||/فضاء|كوكب|ذرة|موجة|space|planet|atom/i.test(text)) return 'science_orbit';
  if(episode.profile==='horror') return 'horror_mist';
  if(episode.profile==='stickman'||scene.kind==='stickman'||scene.kind==='whatif') return 'paper_story';
  return 'cinematic_atmosphere';
};

export const SceneContract=({scene,episode}:Props)=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const duration=Math.max(1,(scene.end-scene.start)*fps);
  const p=interpolate(frame,[0,duration],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.inOut(Easing.cubic)});
  const contract=sceneContractFor(scene,episode);
  const assetOpacity=scene.asset?.length?.toString()?0.44:1;
  const sunX=interpolate(p,[0,1],[790,505]);
  const sunY=interpolate(p,[0,1],[330,1060]);
  const sunScale=interpolate(p,[0,1],[.78,1.18]);
  const cloudX=interpolate(frame,[0,duration],[-160,180],{extrapolateRight:'extend'});
  const rayOpacity=.16+Math.sin(frame/23)*.06;
  const skyTop=contract==='horror_mist'?'#15182a':contract==='science_orbit'?'#071c42':contract==='paper_story'?'#596b85':'#514b76';
  const skyBottom=contract==='horror_mist'?'#5e314e':contract==='science_orbit'?'#164b72':contract==='paper_story'?'#e9b18e':'#f49a78';
  const accent=contract==='science_orbit'?'#72e9ff':contract==='horror_mist'?'#d37a9b':'#ffe7a1';
  return <AbsoluteFill style={{opacity:assetOpacity,pointerEvents:'none'}} data-scene-contract={contract}>
    <svg viewBox="0 0 1080 1920" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" style={{position:'absolute',inset:0}}>
      <defs>
        <linearGradient id="scene-contract-sky" x1="0" y1="0" x2="0" y2="1"><stop stopColor={skyTop}/><stop offset=".62" stopColor={skyBottom}/><stop offset="1" stopColor="#17232e"/></linearGradient>
        <radialGradient id="scene-contract-glow"><stop stopColor={accent} stopOpacity=".82"/><stop offset=".38" stopColor={accent} stopOpacity=".2"/><stop offset="1" stopColor={accent} stopOpacity="0"/></radialGradient>
        <filter id="scene-contract-blur"><feGaussianBlur stdDeviation="18"/></filter>
      </defs>
      <rect width="1080" height="1920" fill="url(#scene-contract-sky)" opacity=".72"/>
      <circle cx={sunX} cy={sunY} r={270*sunScale} fill="url(#scene-contract-glow)" filter="url(#scene-contract-blur)"/>
      <circle cx={sunX} cy={sunY} r={52*sunScale} fill={accent} opacity=".96"/>
      <g opacity={rayOpacity} transform={`translate(${sunX} ${sunY}) rotate(${interpolate(p,[0,1],[-18,16])})`}>
        {Array.from({length:14},(_,i)=>{const a=i*Math.PI/7;const x=Math.cos(a)*420;const y=Math.sin(a)*420;return <line key={i} x1={Math.cos(a)*90} y1={Math.sin(a)*90} x2={x} y2={y} stroke={accent} strokeWidth="9" strokeLinecap="round"/>;})}
      </g>
      <g opacity=".22" transform={`translate(${cloudX} 0)`}>
        <path d="M60 610 C130 545 210 555 260 615 C310 555 420 565 462 640 C380 680 170 690 60 660Z" fill="#f7dfda"/>
        <path d="M620 460 C710 400 790 430 820 490 C890 440 1000 470 1040 545 C930 585 745 575 620 530Z" fill="#f7dfda"/>
      </g>
      <g transform={`translate(${interpolate(p,[0,1],[0,-34])} ${interpolate(p,[0,1],[0,18])})`}>
        <path d="M0 1260 Q220 1060 430 1240 T830 1190 T1080 1110 V1920H0Z" fill={contract==='paper_story'?'#3f4a55':'#263a47'} opacity=".72"/>
      </g>
      <g transform={`translate(${interpolate(p,[0,1],[0,-82])} ${interpolate(p,[0,1],[0,35])})`}>
        <path d="M0 1430 Q230 1230 470 1400 T800 1320 T1080 1260 V1920H0Z" fill="#111d27" opacity=".9"/>
      </g>
      <path d={`M${interpolate(p,[0,1],[540,505])} 1920 C${interpolate(p,[0,1],[530,530])} 1660 ${interpolate(p,[0,1],[620,545])} 1360 ${sunX} ${sunY+70}`} fill="none" stroke={accent} strokeWidth="7" strokeDasharray="22 24" opacity=".86"/>
      {contract==='science_orbit'&&<g fill="none" stroke="#7cecff" opacity=".5"><ellipse cx="540" cy="900" rx="300" ry="120" transform={`rotate(${interpolate(p,[0,1],[-18,18])} 540 900)`}/><ellipse cx="540" cy="900" rx="210" ry="80" transform={`rotate(${interpolate(p,[0,1],[22,-22])} 540 900)`}/><circle cx="540" cy="900" r="34" fill="#7cecff"/></g>}
      {contract==='horror_mist'&&<g fill="#d37a9b" opacity={.12+.08*Math.sin(frame/29)}><ellipse cx="180" cy="980" rx="360" ry="80"/><ellipse cx="900" cy="1120" rx="420" ry="95"/></g>}
    </svg>
  </AbsoluteFill>;
};
